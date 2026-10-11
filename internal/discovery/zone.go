// Package discovery produces a headless DNS zone for CoreDNS. It does not
// implement DNS parsing or pretend that DNS round-robin is a load balancer.
package discovery

import (
	"errors"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"net"
	"sort"
	"strings"
	"time"
)

const Zone = "svc.werft."

type Endpoint struct {
	Service string `json:"service"`
	ID      string `json:"id"`
	Address string `json:"address"`
	Port    int    `json:"port"`
	Routed  bool   `json:"routed"`
}
type Snapshot struct {
	ClusterID string     `json:"clusterId"`
	Revision  int64      `json:"revision"`
	At        time.Time  `json:"at"`
	Endpoints []Endpoint `json:"endpoints"`
}

func FromState(s *model.State, revision int64, now time.Time) Snapshot {
	out := Snapshot{ClusterID: s.ClusterID, Revision: revision, At: now, Endpoints: []Endpoint{}}
	for _, id := range model.SortedKeys(s.Allocations) {
		a := s.Allocations[id]
		n := s.Nodes[a.NodeID]
		if n == nil || !n.Ready(now) || a.Desired != "run" || a.Phase != "ready" || !model.FreshObservation(a.UpdatedAt, now) || a.Spec.Port == 0 {
			continue
		}
		ip, port, routed := n.Address, a.HostPort, false
		if a.ContainerIP != "" {
			_, cidr, e := net.ParseCIDR(n.PodCIDR)
			if e != nil || !cidr.Contains(net.ParseIP(a.ContainerIP)) {
				continue
			}
			ip, port, routed = a.ContainerIP, a.Spec.Port, true
		}
		out.Endpoints = append(out.Endpoints, Endpoint{a.Name, a.ID, ip, port, routed})
	}
	return out
}
func Render(s Snapshot, serial uint32) ([]byte, error) {
	if !model.ValidID(s.ClusterID) || len(s.Endpoints) > model.MaxAllocations {
		return nil, errors.New("DISCOVERY_INVALID")
	}
	var b strings.Builder
	fmt.Fprintf(&b, "$ORIGIN %s\n$TTL 5\n@ IN SOA ns.%s hostmaster.%s %d 5 5 30 5\n@ IN NS ns.%s\nns IN A 127.0.0.1\n", Zone, Zone, Zone, serial, Zone)
	es := append([]Endpoint{}, s.Endpoints...)
	sort.Slice(es, func(i, j int) bool {
		if es[i].Service != es[j].Service {
			return es[i].Service < es[j].Service
		}
		return es[i].ID < es[j].ID
	})
	seen := map[string]bool{}
	for _, e := range es {
		if !model.ValidName(e.Service) || !model.ValidID(e.ID) || !model.PrivateAddress(e.Address) || e.Port < 1024 || e.Port > 65535 || seen[e.ID] {
			return nil, errors.New("DISCOVERY_ENDPOINT_INVALID")
		}
		seen[e.ID] = true
		// A service may have different published ports. SRV preserves that fact.
		fmt.Fprintf(&b, "%s IN A %s\na-%s IN A %s\n_tcp.%s IN SRV 0 1 %d a-%s.%s\n", e.Service, e.Address, e.ID, e.Address, e.Service, e.Port, e.ID, Zone)
	}
	return []byte(b.String()), nil
}
