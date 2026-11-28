package control_test

import (
	"context"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"strings"
	"testing"
)

func TestVolumeRestoreReservationIsDurableAndReplayBound(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	var v model.Volume
	if e := h.admin.Call(ctx, "POST", "/v1/volumes", control.VolumeCreate{Name: "data", NodeID: h.nodeID, UID: 65532, GID: 65532}, &v, model.ID()); e != nil {
		t.Fatal(e)
	}
	q := control.VolumeRestoreRequest{ID: v.ID, MaintenanceID: model.ID(), OperationID: model.ID(), SHA256: strings.Repeat("a", 64)}
	if e := h.admin.Call(ctx, "POST", "/v1/volumes/data/restore", q, nil, q.OperationID); e == nil {
		t.Fatal("restore without owned maintenance")
	}
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", control.MaintenanceRequest{ID: q.MaintenanceID, Enabled: true, Reason: "restore-test"}, nil, q.MaintenanceID); e != nil {
		t.Fatal(e)
	}
	if e := h.admin.Call(ctx, "POST", "/v1/volumes/data/restore", q, nil, q.OperationID); e != nil {
		t.Fatal(e)
	}
	s, _, _ := h.s.Read(ctx)
	got := s.Volumes["data"]
	if !got.Initialized || got.RestoreComplete || got.RestoreID != q.OperationID || got.RestoreMaintenanceID != q.MaintenanceID {
		t.Fatal("unsafe reservation", got)
	}
	// A new maintenance lease must not be able to acknowledge an old disk
	// restore reservation, even when it replays the same operation and digest.
	nextMaintenance := model.ID()
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", control.MaintenanceRequest{ID: q.MaintenanceID, Enabled: false, Reason: "handover"}, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", control.MaintenanceRequest{ID: nextMaintenance, Enabled: true, Reason: "handover"}, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	handover := q
	handover.MaintenanceID = nextMaintenance
	if e := h.admin.Call(ctx, "POST", "/v1/volumes/data/restore", handover, nil, q.OperationID); e == nil {
		t.Fatal("maintenance handover acknowledged old restore")
	}
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", control.MaintenanceRequest{ID: nextMaintenance, Enabled: false, Reason: "handover"}, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", control.MaintenanceRequest{ID: q.MaintenanceID, Enabled: true, Reason: "restore-test"}, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	other := q
	other.SHA256 = strings.Repeat("b", 64)
	if e := h.admin.Call(ctx, "POST", "/v1/volumes/data/restore", other, nil, q.OperationID); e == nil {
		t.Fatal("different archive accepted")
	}
	q.Complete = true
	if e := h.node.Call(ctx, "POST", "/v1/volumes/data/restore", q, nil, q.OperationID); e == nil {
		t.Fatal("node self-authorized restore")
	}
	if e := h.admin.Call(ctx, "POST", "/v1/volumes/data/restore", q, nil, q.OperationID); e != nil {
		t.Fatal(e)
	}
	if e := h.admin.Call(ctx, "POST", "/v1/volumes/data/restore", q, nil, q.OperationID); e != nil {
		t.Fatal("replayed acknowledgment failed", e)
	}
}
