package discovery

import (
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"strings"
	"testing"
	"time"
)

func TestRenderDeterministicAndPorts(t *testing.T) {
	s := Snapshot{ClusterID: model.ID(), Endpoints: []Endpoint{{"web", strings.Repeat("a", 32), "10.87.0.1", 22000, false}, {"web", strings.Repeat("b", 32), "10.88.1.2", 8080, true}}}
	b, e := Render(s, 42)
	if e != nil {
		t.Fatal(e)
	}
	if !strings.Contains(string(b), "_tcp.web IN SRV 0 1 22000") || !strings.Contains(string(b), "web IN A 10.88.1.2") {
		t.Fatal(string(b))
	}
	s.Endpoints[0], s.Endpoints[1] = s.Endpoints[1], s.Endpoints[0]
	b2, _ := Render(s, 42)
	if string(b) != string(b2) {
		t.Fatal("nondeterministic")
	}
}
func TestZoneInjectionRejected(t *testing.T) {
	s := Snapshot{ClusterID: model.ID(), Endpoints: []Endpoint{{"web\n@ IN A 8.8.8.8", model.ID(), "10.1.2.3", 8080, true}}}
	if _, e := Render(s, 1); e == nil {
		t.Fatal("injected")
	}
}
func TestNoStaleRevokedOrForeignSubnetEndpoints(t *testing.T) {
	now := time.Now()
	s := model.NewState(model.ID(), "lab", now)
	node := model.ID()
	s.Nodes[node] = &model.Node{ID: node, Address: "10.87.0.1", PodCIDR: "10.88.1.0/24", Healthy: true, LastSeen: now}
	id := model.ID()
	s.Allocations[id] = &model.Allocation{ID: id, Name: "web", NodeID: node, Desired: "run", Phase: "ready", UpdatedAt: now, ContainerIP: "10.88.1.2", Spec: model.Spec{Port: 8080}}
	if len(FromState(s, 1, now).Endpoints) != 1 {
		t.Fatal("missing")
	}
	s.Allocations[id].ContainerIP = "10.88.2.2"
	if len(FromState(s, 1, now).Endpoints) != 0 {
		t.Fatal("foreign")
	}
	s.Allocations[id].ContainerIP = "10.88.1.2"
	s.Nodes[node].Revoked = true
	if len(FromState(s, 1, now).Endpoints) != 0 {
		t.Fatal("revoked")
	}
	s.Nodes[node].Revoked = false
	if len(FromState(s, 1, now.Add(time.Minute)).Endpoints) != 0 {
		t.Fatal("stale")
	}
}
