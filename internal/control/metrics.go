package control

import (
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"net/http"
)

// Intentionally bounded metric names and labels: no IDs, user input or secrets.
func (a *API) metrics(w http.ResponseWriter, r *http.Request) {
	s, _, e := a.Store.Read(r.Context())
	if e != nil {
		failError(w, e)
		return
	}
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	w.Header().Set("Cache-Control", "no-store")
	ready := 0
	for _, n := range s.Nodes {
		if n.Ready(a.now()) {
			ready++
		}
	}
	fmt.Fprintf(w, "# TYPE werftkern_nodes gauge\nwerftkern_nodes %d\n# TYPE werftkern_nodes_ready gauge\nwerftkern_nodes_ready %d\n", len(s.Nodes), ready)
	fmt.Fprintf(w, "# TYPE werftkern_workloads gauge\nwerftkern_workloads %d\n# TYPE werftkern_allocations gauge\nwerftkern_allocations %d\n", len(s.Workloads), len(s.Allocations))
	for _, phase := range []string{"assigned", "starting", "ready", "failed", "stopped", "unknown"} {
		n := 0
		for _, x := range s.Allocations {
			p := x.Phase
			if node := s.Nodes[x.NodeID]; node == nil || !node.Ready(a.now()) {
				p = "unknown"
			}
			if p == phase {
				n++
			}
		}
		fmt.Fprintf(w, "werftkern_allocation_phase{phase=%q} %d\n", phase, n)
	}
	fmt.Fprintf(w, "werftkern_state_limit_bytes %d\n", model.MaxStateBytes)
}
