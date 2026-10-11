package model

import (
	"errors"
	"fmt"
	"strconv"
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
	names := map[string]bool{}
	addrs := map[string]bool{}
	for name, w := range s.Workloads {
		if w == nil || !ValidName(name) || name != w.Name || !ValidID(w.UID) || uids[w.UID] || w.Generation < 1 || len(w.History) > 5 {
			return errors.New("WORKLOAD_RECORD_INVALID")
		}
		uids[w.UID] = true
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
	for id, n := range s.Nodes {
		if n == nil || id != n.ID || ValidateNode(*n) != nil || names[n.Name] || addrs[n.Address] {
			return errors.New("NODE_RECORD_INVALID")
		}
		names[n.Name] = true
		addrs[n.Address] = true
	}
	for id, a := range s.Allocations {
		if a == nil || id != a.ID || !ValidID(id) || s.Nodes[a.NodeID] == nil || !uids[a.WorkloadUID] || a.Generation < 1 || (a.Desired != "run" && a.Desired != "stop") {
			return errors.New("ALLOCATION_RECORD_INVALID")
		}
		if e := a.Spec.Validate(); e != nil {
			return e
		}
		if e := s.ValidateSecretAvailability(a.Spec); e != nil {
			return e
		}
	}
	return nil
}
