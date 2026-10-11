package control_test

import (
	"context"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/control"
	"github.com/ClusterPilot-System/werftkern/internal/model"
)

func TestWorkerScopedStateNeverLeaksOtherNodesOrSpecs(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", hb(h), nil, ""); e != nil {
		t.Fatal(e)
	}
	code, body := rawRequest(t, h.node, "GET", "/v1/node-state", "", "")
	if code != http.StatusOK || !strings.Contains(body, h.nodeID) || strings.Contains(body, h.otherID) || strings.Contains(body, "workloads") || strings.Contains(body, "secrets") {
		t.Fatal(code, body)
	}
	code, _ = rawRequest(t, h.admin, "GET", "/v1/node-state", "", "")
	if code != 403 {
		t.Fatal("admin accepted as node")
	}
	h.s.Update(ctx, func(s *model.State) error { s.Nodes[h.nodeID].Revoked = true; return nil })
	code, _ = rawRequest(t, h.node, "GET", "/v1/node-state", "", "")
	if code != 403 {
		t.Fatal("revoked node read scope")
	}
}
func TestMaintainedNodeAPIRequiresOwnerTargetVersionAndSequence(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	op := model.ID()
	h.node.Call(ctx, "POST", "/v1/heartbeat", hb(h), nil, "")
	h.s.Update(ctx, func(s *model.State) error { s.MaintenanceID = op; return nil })
	route := "/v1/maintenance/nodes/" + h.nodeID
	q := control.MaintenanceNodeRequest{ID: op}
	if e := h.node.Call(ctx, "POST", route+"/drain", q, nil, ""); e == nil {
		t.Fatal("node mutated drain")
	}
	q.ID = model.ID()
	if e := h.admin.Call(ctx, "POST", route+"/drain", q, nil, ""); e == nil {
		t.Fatal("wrong lock")
	}
	q.ID = op
	var projection control.NodeState
	if e := h.admin.Call(ctx, "POST", route+"/drain", q, &projection, ""); e != nil {
		t.Fatal(e)
	}
	if projection.UnconfirmedAllocations != 0 || !projection.Drain {
		t.Fatal(projection)
	}
	q.ExpectedVersion = "0.2.0-dev.3"
	q.MinSequence = 1
	if e := h.admin.Call(ctx, "POST", route+"/uncordon", q, nil, ""); e == nil {
		t.Fatal("old version admitted")
	}
	q.ExpectedVersion = model.Version
	q.MinSequence = 100
	if e := h.admin.Call(ctx, "POST", route+"/uncordon", q, nil, ""); e == nil {
		t.Fatal("old sequence admitted")
	}
	q.MinSequence = 1
	if e := h.admin.Call(ctx, "POST", route+"/uncordon", q, nil, ""); e != nil {
		t.Fatal(e)
	}
	s, _, _ := h.s.Read(ctx)
	if s.MaintenanceID != op || s.Nodes[h.nodeID].Drain {
		t.Fatal("wrong lock/flag")
	}
}
func TestOnlyExplicitSameSchemaPreviousAgentVersionIsAdmitted(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	for _, version := range []string{"0.2.0-dev.2", "0.2.0-dev.3", model.Version, "0.2.0-dev.5"} {
		q := hb(h)
		q.Version = version
		e := h.node.Call(ctx, "POST", "/v1/heartbeat", q, nil, "")
		supported := version == model.Version || version == "0.2.0-dev.3"
		if (e == nil) != supported {
			t.Fatal(version, e)
		}
	}
}
func TestRepeatingOldProbeDoesNotRefreshAllocationTime(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	allocation := model.ID()
	h.s.Update(ctx, func(s *model.State) error { fixtureAllocation(s, allocation, h.nodeID); return nil })
	observed := time.Now().UTC().Add(-10 * time.Second)
	q := hb(h)
	q.Reports = []model.Report{{ID: allocation, Phase: "ready", ObservedAt: observed}}
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", q, nil, ""); e != nil {
		t.Fatal(e)
	}
	q = hb(h)
	q.Reports = []model.Report{{ID: allocation, Phase: "ready", ObservedAt: observed}}
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", q, nil, ""); e != nil {
		t.Fatal(e)
	}
	s, _, _ := h.s.Read(ctx)
	if !s.Allocations[allocation].UpdatedAt.Equal(observed) {
		t.Fatal("repeated probe gained freshness")
	}
}
