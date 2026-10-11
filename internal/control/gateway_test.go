package control_test

import (
	"context"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/discovery"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"testing"
	"time"
)

func TestGatewayCertificateOnlyReadsExplicitServicesAndRevocationBlocks(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	g := model.Gateway{ID: model.ID(), Name: "edge", Services: []string{"web"}}
	if e := h.admin.Call(ctx, "POST", "/v1/gateways", g, nil, g.ID); e != nil {
		t.Fatal(e)
	}
	if _, _, e := h.s.Update(ctx, func(s *model.State) error {
		for i, name := range []string{"web", "private-db"} {
			id := model.ID()
			fixtureAllocation(s, id, h.nodeID)
			a := s.Allocations[id]
			old := s.Workloads[a.Name]
			delete(s.Workloads, a.Name)
			a.Name = name
			old.Name = name
			s.Workloads[name] = old
			a.Phase = "ready"
			a.Spec.Port = 8080
			a.Spec.ReadinessPath = "/ready"
			old.Spec = a.Spec
			a.HostPort = 22000 + i
			a.UpdatedAt = time.Now()
		}
		s.Nodes[h.nodeID].LastSeen = time.Now()
		s.Nodes[h.nodeID].Healthy = true
		return nil
	}); e != nil {
		t.Fatal(e)
	}
	c := &apiclient.Client{HTTP: h.tls.Client(t, "gateway:"+g.ID), Base: h.tls.Server.URL, ClusterID: h.s.ClusterID}
	var snap discovery.Snapshot
	if e := c.Call(ctx, "GET", "/v1/discovery", nil, &snap, ""); e != nil {
		t.Fatal(e)
	}
	if len(snap.Endpoints) != 1 || snap.Endpoints[0].Service != "web" {
		t.Fatal(snap)
	}
	if _, e := c.State(ctx); e == nil {
		t.Fatal("gateway obtained administrator state")
	}
	if e := c.Call(ctx, "POST", "/v1/heartbeat", hb(h), nil, ""); e == nil {
		t.Fatal("gateway impersonated node")
	}
	if e := c.Call(ctx, "POST", "/v1/gateways", g, nil, g.ID); e == nil {
		t.Fatal("gateway expanded rights")
	}
	if e := h.admin.Call(ctx, "POST", "/v1/gateways/"+g.ID+"/revoke", nil, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	if e := c.Call(ctx, "GET", "/v1/discovery", nil, &snap, ""); e == nil {
		t.Fatal("revoked gateway still authorized")
	}
}
