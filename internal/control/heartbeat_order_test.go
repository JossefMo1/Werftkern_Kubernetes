package control_test

import (
	"context"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"strings"
	"testing"
	"time"
)

func TestHeartbeatReplaysDoNotRenewNodeLivenessOrRollbackReports(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	aid := model.ID()
	if _, _, err := h.s.Update(ctx, func(s *model.State) error { fixtureAllocation(s, aid, h.nodeID); return nil }); err != nil {
		t.Fatal(err)
	}
	first := hb(h)
	first.Sequence = 10
	first.Reports = []model.Report{{ID: aid, Phase: "ready", ObservedAt: time.Now()}}
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", first, nil, ""); e != nil {
		t.Fatal(e)
	}
	s, _, _ := h.s.Read(ctx)
	seen := s.Nodes[h.nodeID].LastSeen
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", first, nil, ""); e != nil {
		t.Fatal(e)
	}
	s, _, _ = h.s.Read(ctx)
	if !s.Nodes[h.nodeID].LastSeen.Equal(seen) {
		t.Fatal("replay refreshed liveness")
	}
	old := first
	old.Sequence = 9
	old.Reports = []model.Report{{ID: aid, Phase: "failed"}}
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", old, nil, ""); e != nil {
		t.Fatal(e)
	}
	s, _, _ = h.s.Read(ctx)
	if s.Allocations[aid].Phase != "ready" || !s.Nodes[h.nodeID].LastSeen.Equal(seen) {
		t.Fatal("late heartbeat rolled observations backwards")
	}
	old.Sequence = 10
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", old, nil, ""); e == nil || !strings.Contains(e.Error(), "HEARTBEAT_REPLAY_CONTENT_CONFLICT") {
		t.Fatal(e)
	}
	old.Sequence = 0
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", old, nil, ""); e == nil {
		t.Fatal("legacy unsequenced writer re-enabled")
	}
}
func TestStoppedAllocationCannotResurrectAndDuplicateReportsRejected(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	id := model.ID()
	if _, _, e := h.s.Update(ctx, func(s *model.State) error {
		fixtureAllocation(s, id, h.nodeID)
		s.Allocations[id].Desired = "stop"
		return nil
	}); e != nil {
		t.Fatal(e)
	}
	req := hb(h)
	req.Sequence = 1
	req.Reports = []model.Report{{ID: id, Phase: "stopped", ObservedAt: time.Now()}}
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", req, nil, ""); e != nil {
		t.Fatal(e)
	}
	req.Sequence++
	req.Reports[0].Phase = "ready"
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", req, nil, ""); e != nil {
		t.Fatal(e)
	}
	s, _, _ := h.s.Read(ctx)
	if s.Allocations[id].Phase != "stopped" {
		t.Fatal("terminal stop overwritten")
	}
	req.Sequence++
	req.Reports = append(req.Reports, req.Reports[0])
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", req, nil, ""); e == nil {
		t.Fatal("contradictory duplicate reports accepted")
	}
}

func TestUnsupportedAgentAndUnsequencedHeartbeatFailBeforeNodeMutation(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	bad := hb(h)
	bad.Version = "0.2.0-dev.1"
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", bad, nil, ""); e == nil {
		t.Fatal("old writer admitted to schema 2")
	}
	bad.Version = model.Version
	bad.Sequence = 0
	if e := h.node.Call(ctx, "POST", "/v1/heartbeat", bad, nil, ""); e == nil {
		t.Fatal("unsequenced writer admitted")
	}
	s, _, e := h.s.Read(ctx)
	if e != nil || !s.Nodes[h.nodeID].LastSeen.IsZero() {
		t.Fatal("unsupported writer refreshed liveness", e)
	}
}
