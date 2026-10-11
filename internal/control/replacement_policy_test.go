package control

import (
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"testing"
	"time"
)

func TestRevokedNodeIsNotFencing(t *testing.T) {
	s, now := base(t, 2, 1)
	settle(t, s, now, 3)
	original := model.SortedKeys(s.Allocations)[0]
	s.Nodes[s.Allocations[original].NodeID].Revoked = true
	for i := 0; i < 10; i++ {
		if e := Reconcile(s, now); e != nil {
			t.Fatal(e)
		}
	}
	if len(s.Allocations) != 1 || s.Allocations[original].Desired != "run" || s.Workloads["demo"].Reason != "NODE_UNKNOWN_RESERVATION_RETAINED" {
		t.Fatal("revocation started an unfenced duplicate")
	}
}
func TestExplicitDuplicateSafeReplacementRetainsOldReservation(t *testing.T) {
	s, now := base(t, 2, 1)
	s.Workloads["demo"].Spec.ReplacementPolicy = "duplicate-safe"
	settle(t, s, now, 3)
	original := model.SortedKeys(s.Allocations)[0]
	old := s.Allocations[original]
	later := now.Add(time.Minute)
	for id, n := range s.Nodes {
		if id != old.NodeID {
			n.LastSeen = later
		}
	}
	for i := 0; i < 3; i++ {
		if e := Reconcile(s, later); e != nil {
			t.Fatal(e)
		}
	}
	if len(s.Allocations) != 2 || old.Desired != "stop" || old.Phase == "stopped" {
		t.Fatal("lost reservation or failed to replace")
	}
	newCount := 0
	for _, a := range s.Allocations {
		if a.Desired == "run" {
			newCount++
			if a.NodeID == old.NodeID {
				t.Fatal("used failed owner")
			}
		}
	}
	if newCount != 1 {
		t.Fatal(newCount)
	}
}
func TestDuplicatePolicyCannotPermitStatefulSurge(t *testing.T) {
	s, _ := base(t, 1, 1)
	sp := s.Workloads["demo"].Spec
	sp.ReplacementPolicy = "duplicate-safe"
	sp.Node = id(1)
	sp.Volumes = []model.VolumeRef{{Name: "data", MountPath: "/data/app"}}
	if sp.Validate() == nil {
		t.Fatal("stateful duplicate policy accepted")
	}
}
