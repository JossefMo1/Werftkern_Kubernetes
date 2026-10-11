package control

import (
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"strings"
	"testing"
)

func TestVolumeRecreateNeverSurgesWriters(t *testing.T) {
	s, now := base(t, 2, 1)
	w := s.Workloads["demo"]
	s.Volumes = map[string]*model.Volume{"data": {ID: model.ID(), Name: "data", NodeID: id(1), UID: 65532, GID: 65532, Owner: w.UID}}
	w.Spec.Node = id(1)
	w.Spec.Volumes = []model.VolumeRef{{Name: "data", MountPath: "/data/app"}}
	settle(t, s, now, 4)
	old := model.SortedKeys(s.Allocations)[0]
	q := model.ApplyRequest{APIVersion: model.APIVersion, Name: "demo", ExpectedGeneration: w.Generation, Spec: w.Spec}
	q.Spec.Image = "sha256:" + strings.Repeat("b", 64)
	if _, e := model.Apply(s, q, model.ID(), now); e != nil {
		t.Fatal(e)
	}
	for i := 0; i < 5; i++ {
		Reconcile(s, now)
		if len(s.Allocations) != 1 || s.Allocations[old].Desired != "stop" {
			t.Fatal("writer overlap")
		}
	}
	s.Allocations[old].Phase = "stopped"
	Reconcile(s, now)
	if len(s.Allocations) != 1 || s.Allocations[old] != nil {
		t.Fatal("no safe successor")
	}
}
func TestVolumeOfflineNodeNotMovedAndDrainBlocked(t *testing.T) {
	s, now := base(t, 2, 1)
	w := s.Workloads["demo"]
	w.Spec.Node = id(1)
	w.Spec.Volumes = []model.VolumeRef{{Name: "data", MountPath: "/data/app"}}
	s.Volumes = map[string]*model.Volume{"data": {ID: model.ID(), Name: "data", NodeID: id(1), UID: 65532, GID: 65532, Owner: w.UID}}
	settle(t, s, now, 3)
	s.Nodes[id(1)].Drain = true
	Reconcile(s, now)
	if w.Phase != "blocked" || len(s.Allocations) != 1 {
		t.Fatal("unsafe drain")
	}
}
func TestMaintenanceBlocksBindingButPermitsPause(t *testing.T) {
	s, now := base(t, 1, 1)
	s.MaintenanceID = model.ID()
	Reconcile(s, now)
	if len(s.Allocations) != 0 {
		t.Fatal("scheduled while frozen")
	}
	s.MaintenanceID = ""
	settle(t, s, now, 3)
	s.MaintenanceID = model.ID()
	w := s.Workloads["demo"]
	if _, e := model.MutateWorkload(s, w.Name, "pause", model.ID(), w.Generation, now); e != nil {
		t.Fatal(e)
	}
	settle(t, s, now, 3)
	if len(s.Allocations) != 0 {
		t.Fatal("pause blocked")
	}
	if _, e := model.MutateWorkload(s, w.Name, "resume", model.ID(), w.Generation, now); e == nil {
		t.Fatal("resumed during maintenance")
	}
}
