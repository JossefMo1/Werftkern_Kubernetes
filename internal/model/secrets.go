package model

import (
	"errors"
	"fmt"
	"net"
	"strconv"
	"strings"
)

type SecretRef struct {
	Name    string `json:"name"`
	Version int    `json:"version"`
}
type SecretVersion struct {
	Name    string `json:"name"`
	Version int    `json:"version"`
	Sealed  string `json:"sealed,omitempty"`
}

func (s SecretRef) Key() string { return s.Name + "/" + strconv.Itoa(s.Version) }

// validReceiptWorkloadUID accepts either a workload UID or the explicit owner
// namespace used by secret mutation receipts.
func validReceiptWorkloadUID(uid string) bool {
	if ValidID(uid) {
		return true
	}
	if !strings.HasPrefix(uid, "secret:") {
		return false
	}
	parts := strings.Split(strings.TrimPrefix(uid, "secret:"), "/")
	if len(parts) != 2 {
		return false
	}
	version, err := strconv.Atoi(parts[1])
	return err == nil && ValidateSecretRefs([]SecretRef{{Name: parts[0], Version: version}}) == nil
}
func SecretAAD(cluster string, ref SecretRef) string {
	return "clusterpilot/secret/v1/" + cluster + "/" + ref.Key()
}
func ValidateSecretRefs(refs []SecretRef) error {
	if len(refs) > 8 {
		return errors.New("TOO_MANY_SECRET_REFERENCES")
	}
	seen := map[string]bool{}
	for _, r := range refs {
		if !ValidName(r.Name) || r.Version < 1 || r.Version > 1000 || seen[r.Name] {
			return errors.New("SECRET_REFERENCE_INVALID")
		}
		seen[r.Name] = true
	}
	return nil
}
func (s *State) ValidateSecretAvailability(spec Spec) error {
	for _, r := range spec.Secrets {
		if _, ok := s.Secrets[r.Key()]; !ok {
			return fmt.Errorf("SECRET_VERSION_NOT_FOUND")
		}
	}
	return nil
}
func (s *State) SecretReferenced(ref SecretRef) bool {
	has := func(spec Spec) bool {
		for _, r := range spec.Secrets {
			if r == ref {
				return true
			}
		}
		return false
	}
	for _, w := range s.Workloads {
		if has(w.Spec) {
			return true
		}
		for _, sp := range w.History {
			if has(sp) {
				return true
			}
		}
	}
	for _, a := range s.Allocations {
		if has(a.Spec) {
			return true
		}
	}
	return false
}

func allocationSpecMatchesWorkload(spec Spec, generation int64, w *Workload) bool {
	if w == nil {
		return false
	}
	if generation == w.Generation {
		return Hash(spec) == Hash(w.Spec)
	}
	if generation < w.Generation {
		for _, historical := range w.History {
			if Hash(spec) == Hash(historical) {
				return true
			}
		}
	}
	return false
}

// ValidatePublicInventory validates the redacted state projection returned by
// the admin API. Secret ciphertext is deliberately removed from that projection;
// an empty Sealed value is therefore valid there, while every other inventory
// invariant remains enforced.
func (s *State) ValidatePublicInventory() error {
	for _, sec := range s.Secrets {
		if sec.Sealed != "" {
			return errors.New("SECRET_RECORD_EXPOSED")
		}
	}
	projection := *s
	projection.Secrets = make(map[string]SecretVersion, len(s.Secrets))
	for key, sec := range s.Secrets {
		sec.Sealed = "redacted"
		projection.Secrets[key] = sec
	}
	return projection.ValidateInventory()
}

// ValidateInventory checks persisted inventory before reads/commits and backup
// import. Structural validity is not independent proof of an agent observation.
func (s *State) ValidateInventory() error {
	if len(s.Gateways) > 10 {
		return errors.New("GATEWAY_LIMIT")
	}
	gatewayNames := map[string]bool{}
	for id, g := range s.Gateways {
		if g == nil || g.ID != id || g.Validate() != nil || gatewayNames[g.Name] {
			return errors.New("GATEWAY_RECORD_INVALID")
		}
		gatewayNames[g.Name] = true
	}

	if e := s.Validate(); e != nil {
		return e
	}
	if len(s.Secrets) > 128 {
		return ErrCapacity
	}
	for key, sec := range s.Secrets {
		ref := SecretRef{sec.Name, sec.Version}
		if ValidateSecretRefs([]SecretRef{ref}) != nil || key != ref.Key() || len(sec.Sealed) > 8192 || sec.Sealed == "" {
			return errors.New("SECRET_RECORD_INVALID")
		}
	}
	uids := map[string]bool{}
	workloadByUID := map[string]*Workload{}
	names := map[string]bool{}
	addrs := map[string]bool{}
	for name, w := range s.Workloads {
		if w == nil || !ValidName(name) || name != w.Name || !ValidID(w.UID) || uids[w.UID] || w.Generation < 1 || len(w.History) > 5 {
			return errors.New("WORKLOAD_RECORD_INVALID")
		}
		if !ValidReason(w.Reason) {
			return errors.New("WORKLOAD_REASON_INVALID")
		}
		uids[w.UID] = true
		workloadByUID[w.UID] = w
		if e := w.Spec.Validate(); e != nil {
			return e
		}
		if e := s.validateVolumeAvailability(w.Spec, w.UID, !w.Paused); e != nil {
			return e
		}
		if e := s.ValidateSecretAvailability(w.Spec); e != nil {
			return e
		}
		for _, sp := range w.History {
			if e := sp.Validate(); e != nil {
				return e
			}
			if e := s.ValidateSecretAvailability(sp); e != nil {
				return e
			}
		}
	}
	podCIDRs := make([]string, 0, len(s.Nodes))
	for _, id := range SortedKeys(s.Nodes) {
		n := s.Nodes[id]
		if n == nil || id != n.ID || ValidateNode(*n) != nil || names[n.Name] || addrs[n.Address] {
			return errors.New("NODE_RECORD_INVALID")
		}
		names[n.Name] = true
		addrs[n.Address] = true
		if n.PodCIDR != "" {
			for _, existing := range podCIDRs {
				if SubnetsOverlap(existing, n.PodCIDR) {
					return errors.New("NODE_POD_CIDR_CONFLICT")
				}
			}
			podCIDRs = append(podCIDRs, n.PodCIDR)
		}
	}
	hostPortsByNode := map[string]map[int]string{}
	containerIPs := map[string]string{}
	for id, a := range s.Allocations {
		if a == nil {
			return errors.New("ALLOCATION_RECORD_INVALID")
		}
		if !ValidReason(a.Reason) {
			return errors.New("ALLOCATION_REASON_INVALID")
		}
		w := workloadByUID[a.WorkloadUID]
		if id != a.ID || !ValidID(id) || s.Nodes[a.NodeID] == nil || w == nil || a.Name != w.Name || a.Generation < 1 || a.Generation > w.Generation || (a.Desired != "run" && a.Desired != "stop") || !validAllocationPhase(a.Phase) || (a.Spec.Node != "" && a.Spec.Node != a.NodeID) || !allocationSpecMatchesWorkload(a.Spec, a.Generation, w) {
			return errors.New("ALLOCATION_RECORD_INVALID")
		}
		if e := a.Spec.Validate(); e != nil {
			return e
		}
		// A zero host port represents an unresolved legacy assignment and is
		// intentionally not published by discovery. Once persisted, non-zero
		// host ports must remain in the scheduler-owned range.
		if a.HostPort != 0 && (a.Spec.Port == 0 || a.HostPort < 22000 || a.HostPort >= 23000) {
			return errors.New("ALLOCATION_HOST_PORT_INVALID")
		}
		if a.HostPort != 0 {
			ports := hostPortsByNode[a.NodeID]
			if ports == nil {
				ports = map[int]string{}
				hostPortsByNode[a.NodeID] = ports
			}
			if previous, exists := ports[a.HostPort]; exists && previous != id {
				return errors.New("ALLOCATION_HOST_PORT_CONFLICT")
			}
			ports[a.HostPort] = id
		}
		if a.ContainerIP != "" {
			n := s.Nodes[a.NodeID]
			_, cidr, err := net.ParseCIDR(n.PodCIDR)
			ip := net.ParseIP(a.ContainerIP)
			if err != nil || ip == nil || !cidr.Contains(ip) {
				return errors.New("CONTAINER_IP_OUTSIDE_ENROLLED_SUBNET")
			}
			if previous, exists := containerIPs[a.ContainerIP]; exists && previous != id {
				return errors.New("CONTAINER_IP_CONFLICT")
			}
			containerIPs[a.ContainerIP] = id
		}
		if e := s.ValidateSecretAvailability(a.Spec); e != nil {
			return e
		}
	}
	return nil
}
