package control

import (
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"strings"
	"testing"
	"time"
)

func id(i int) string { return fmt.Sprintf("%032x", i) }
func base(t *testing.T, nodes, replicas int) (*model.State, time.Time) {
	t.Helper()
	now := time.Now().UTC()
	s := model.NewState(id(999), "test", now)
	for i := 1; i <= nodes; i++ {
		s.Nodes[id(i)] = &model.Node{ID: id(i), Name: fmt.Sprintf("node-%d", i), Address: fmt.Sprintf("127.0.0.%d", i), CPUMilli: 4000, MemoryMiB: 4096, Healthy: true, LastSeen: now}
	}
	_, e := model.Apply(s, model.ApplyRequest{APIVersion: model.APIVersion, Name: "demo", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: replicas, CPUMilli: 250, MemoryMiB: 128, Port: 8080, ReadinessPath: "/healthz"}}, model.ID(), now)
	if e != nil {
		t.Fatal(e)
	}
	return s, now
}
func settle(t *testing.T, s *model.State, now time.Time, n int) {
	t.Helper()
	for i := 0; i < n; i++ {
		for _, a := range s.Allocations {
			if a.Desired == "stop" {
				a.Phase = "stopped"
			} else {
				a.Phase = "ready"
			}
		}
		if e := Reconcile(s, now); e != nil {
			t.Fatal(e)
		}
	}
}
func TestSchedulerSpreadsAndReservesPorts(t *testing.T) {
	s, now := base(t, 2, 3)
	settle(t, s, now, 6)
	if s.Workloads["demo"].Phase != "ready" || len(s.Allocations) != 3 {
		t.Fatalf("not ready: %+v", s.Workloads["demo"])
	}
	counts := map[string]int{}
	ports := map[string]bool{}
	for _, a := range s.Allocations {
		counts[a.NodeID]++
		k := fmt.Sprintf("%s:%d", a.NodeID, a.HostPort)
		if ports[k] {
			t.Fatal("port reused")
		}
		ports[k] = true
	}
	if counts[id(1)] != 2 || counts[id(2)] != 1 {
		t.Fatal(counts)
	}
}
func TestSchedulerNoNodes(t *testing.T) {
	s, now := base(t, 0, 1)
	Reconcile(s, now)
	if len(s.Allocations) != 0 || s.Workloads["demo"].Phase != "blocked" {
		t.Fatal(s.Workloads)
	}
}
func TestOfflineNodeNotReplaced(t *testing.T) {
	s, now := base(t, 2, 1)
	settle(t, s, now, 3)
	original := model.SortedKeys(s.Allocations)[0]
	later := now.Add(time.Minute)
	s.Nodes[id(2)].LastSeen = later
	Reconcile(s, later)
	if len(s.Allocations) != 1 || s.Allocations[original] == nil || s.Workloads["demo"].Reason != "NODE_UNKNOWN_RESERVATION_RETAINED" {
		t.Fatal("unsafe replacement")
	}
}
func TestRollingUpdatePreservesAvailability(t *testing.T) {
	s, now := base(t, 2, 2)
	settle(t, s, now, 5)
	w := s.Workloads["demo"]
	q := model.ApplyRequest{APIVersion: model.APIVersion, Name: w.Name, ExpectedGeneration: w.Generation, Spec: w.Spec}
	q.Spec.Image = "sha256:" + strings.Repeat("b", 64)
	model.Apply(s, q, model.ID(), now)
	for i := 0; i < 15; i++ {
		if e := Reconcile(s, now); e != nil {
			t.Fatal(e)
		}
		ready := 0
		running := 0
		for _, a := range s.Allocations {
			if isReady(s, a, now) {
				ready++
			}
			if a.Desired == "run" {
				running++
			}
		}
		if ready < 2 {
			t.Fatalf("availability dropped at step %d: %d", i, ready)
		}
		if running > 3 {
			t.Fatal("surge exceeded")
		}
		for _, a := range s.Allocations {
			if a.Desired == "stop" {
				a.Phase = "stopped"
			} else {
				a.Phase = "ready"
			}
		}
	}
	if w.Phase != "ready" {
		t.Fatal(w.Phase)
	}
}
func TestRolloutBlocksWithoutSurgeCapacity(t *testing.T) {
	s, now := base(t, 1, 1)
	s.Nodes[id(1)].MemoryMiB = 128
	settle(t, s, now, 4)
	old := model.SortedKeys(s.Allocations)[0]
	w := s.Workloads["demo"]
	q := model.ApplyRequest{APIVersion: model.APIVersion, Name: w.Name, ExpectedGeneration: w.Generation, Spec: w.Spec}
	q.Spec.Image = "sha256:" + strings.Repeat("b", 64)
	model.Apply(s, q, model.ID(), now)
	Reconcile(s, now)
	if s.Allocations[old].Desired != "run" || w.Phase != "blocked" {
		t.Fatal("old revision killed")
	}
}
func TestDrainMovesOnlyAfterReplacementReady(t *testing.T) {
	s, now := base(t, 2, 2)
	settle(t, s, now, 5)
	s.Nodes[id(1)].Drain = true
	Reconcile(s, now)
	for _, a := range s.Allocations {
		if a.NodeID == id(1) && a.Desired != "run" {
			t.Fatal("drained before replacement")
		}
	}
	settle(t, s, now, 10)
	for _, a := range s.Allocations {
		if a.NodeID == id(1) {
			t.Fatal("drain incomplete")
		}
	}
	if s.Workloads["demo"].Phase != "ready" {
		t.Fatal("not ready")
	}
}
func TestStopRetainsCapacityUntilAcknowledged(t *testing.T) {
	s, now := base(t, 1, 1)
	s.Nodes[id(1)].MemoryMiB = 128
	settle(t, s, now, 4)
	for _, a := range s.Allocations {
		a.Desired = "stop"
	}
	Reconcile(s, now)
	if len(s.Allocations) != 1 {
		t.Fatal("stopping reservation reused")
	}
	settle(t, s, now, 5)
	if s.Workloads["demo"].Phase != "ready" {
		t.Fatal("failed to reconcile after ack")
	}
}
func TestDeleteWaitsForStopAndRecreationHasNewUID(t *testing.T) {
	s, now := base(t, 1, 1)
	settle(t, s, now, 3)
	oldUID := s.Workloads["demo"].UID
	spec := s.Workloads["demo"].Spec
	model.MutateWorkload(s, "demo", "delete", model.ID(), 1, now)
	Reconcile(s, now)
	if s.Workloads["demo"] == nil {
		t.Fatal("deleted before stop")
	}
	settle(t, s, now, 3)
	if len(s.Allocations) != 0 || s.Workloads["demo"] != nil {
		t.Fatal("cleanup incomplete")
	}
	model.Apply(s, model.ApplyRequest{APIVersion: model.APIVersion, Name: "demo", Spec: spec}, model.ID(), now)
	if s.Workloads["demo"].UID == oldUID {
		t.Fatal("uid reused")
	}
}
func TestScaleZeroAndBack(t *testing.T) {
	s, now := base(t, 1, 1)
	settle(t, s, now, 3)
	w := s.Workloads["demo"]
	q := model.ApplyRequest{APIVersion: model.APIVersion, Name: w.Name, ExpectedGeneration: w.Generation, Spec: w.Spec}
	q.Spec.Replicas = 0
	model.Apply(s, q, model.ID(), now)
	settle(t, s, now, 5)
	if len(s.Allocations) != 0 || w.Phase != "scaled-down" {
		t.Fatal(w.Phase)
	}
	q.ExpectedGeneration = w.Generation
	q.Spec.Replicas = 1
	model.Apply(s, q, model.ID(), now)
	settle(t, s, now, 5)
	if w.Phase != "ready" {
		t.Fatal(w.Phase)
	}
}
func TestNodeSelectorAndCPUAdmission(t *testing.T) {
	s, now := base(t, 2, 1)
	s.Workloads["demo"].Spec.Node = id(2)
	s.Nodes[id(2)].CPUMilli = 200
	Reconcile(s, now)
	if len(s.Allocations) != 0 {
		t.Fatal("selector/capacity ignored")
	}
	s.Nodes[id(2)].CPUMilli = 4000
	settle(t, s, now, 4)
	for _, a := range s.Allocations {
		if a.NodeID != id(2) {
			t.Fatal("wrong node")
		}
	}
}

func TestPauseStopsAndWaitsForAcknowledgementBeforePaused(t *testing.T) {
	now := time.Now().UTC()
	s := model.NewState(model.ID(), "pause-test", now)
	node := &model.Node{ID: model.ID(), Name: "worker", Address: "127.0.0.1", CPUMilli: 1000, MemoryMiB: 1024, Healthy: true, LastSeen: now}
	s.Nodes[node.ID] = node
	req := model.ApplyRequest{APIVersion: model.APIVersion, Name: "web", Spec: model.Spec{Image: "sha256:" + strings.Repeat("b", 64), CPUMilli: 100, MemoryMiB: 32, Replicas: 1}}
	if _, e := model.Apply(s, req, model.ID(), now); e != nil {
		t.Fatal(e)
	}
	if e := Reconcile(s, now); e != nil {
		t.Fatal(e)
	}
	old := ""
	for id, a := range s.Allocations {
		old = id
		a.Phase = "ready"
	}
	if _, e := model.MutateWorkload(s, "web", "pause", model.ID(), 1, now); e != nil {
		t.Fatal(e)
	}
	if e := Reconcile(s, now); e != nil {
		t.Fatal(e)
	}
	if s.Workloads["web"].Phase != "pausing" || s.Allocations[old].Desired != "stop" {
		t.Fatal("pause didn't wait")
	}
	if _, e := model.MutateWorkload(s, "web", "resume", model.ID(), 1, now); e == nil {
		t.Fatal("stale generation accepted")
	}
	s.Allocations[old].Phase = "stopped"
	if e := Reconcile(s, now); e != nil {
		t.Fatal(e)
	}
	if s.Workloads["web"].Phase != "paused" || len(s.Allocations) != 0 {
		t.Fatal("paused state")
	}
	if _, e := model.MutateWorkload(s, "web", "resume", model.ID(), 2, now); e != nil {
		t.Fatal(e)
	}
	if e := Reconcile(s, now); e != nil {
		t.Fatal(e)
	}
	if len(s.Allocations) != 1 || s.Allocations[old] != nil {
		t.Fatal("reused stopped allocation")
	}
}
