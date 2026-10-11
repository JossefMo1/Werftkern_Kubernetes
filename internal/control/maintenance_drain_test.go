package control

import (
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"testing"
)

func TestMaintenanceDrainMovesOnlySelectedWorkloadsAndRetainsLock(t *testing.T) {
	s, now := base(t, 3, 2)
	settle(t, s, now, 5)
	spec := s.Workloads["demo"].Spec
	if _, e := model.Apply(s, model.ApplyRequest{APIVersion: model.APIVersion, Name: "other", Spec: spec}, model.ID(), now); e != nil {
		t.Fatal(e)
	}
	other := s.Workloads["other"].UID
	op := model.ID()
	s.MaintenanceID = op
	for i := 0; i < 12; i++ {
		if e := AdvanceNodeDrain(s, id(1), op, now); e != nil {
			t.Fatal(e)
		}
		if s.MaintenanceID != op {
			t.Fatal("drain unlocked cluster")
		}
		for _, a := range s.Allocations {
			if a.WorkloadUID == other {
				t.Fatal("unrelated workload scheduled during maintenance")
			}
			if a.Desired == "stop" {
				a.Phase = "stopped"
			} else {
				a.Phase = "ready"
			}
			a.UpdatedAt = now
		}
	}
	for _, a := range s.Allocations {
		if a.NodeID == id(1) {
			t.Fatal("target not empty")
		}
	}
	if !s.Nodes[id(1)].Drain {
		t.Fatal("drain flag lost")
	}
}
func TestMaintenanceDrainKeepsHealthyOldReplicaWithoutCapacity(t *testing.T) {
	s, now := base(t, 1, 1)
	settle(t, s, now, 3)
	s.MaintenanceID = model.ID()
	if e := AdvanceNodeDrain(s, id(1), s.MaintenanceID, now); e != nil {
		t.Fatal(e)
	}
	for _, a := range s.Allocations {
		if a.Desired != "run" {
			t.Fatal("forced eviction")
		}
	}
}
func TestMaintenanceDrainRefusesWrongOwnerPinnedOrConcurrentNodes(t *testing.T) {
	for _, which := range []string{"owner", "pinned", "other-drain", "revoked"} {
		t.Run(which, func(t *testing.T) {
			s, now := base(t, 2, 1)
			settle(t, s, now, 3)
			op := model.ID()
			s.MaintenanceID = op
			switch which {
			case "owner":
				op = model.ID()
			case "pinned":
				s.Workloads["demo"].Spec.Node = id(1)
			case "other-drain":
				s.Nodes[id(2)].Drain = true
			case "revoked":
				s.Nodes[id(1)].Revoked = true
			}
			before := model.Hash(s)
			if e := AdvanceNodeDrain(s, id(1), op, now); e == nil {
				t.Fatal("unsafe drain accepted")
			}
			if model.Hash(s) != before {
				t.Fatal("rejected drain mutated state")
			}
		})
	}
}
