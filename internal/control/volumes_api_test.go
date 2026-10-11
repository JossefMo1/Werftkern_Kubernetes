package control_test

import (
	"context"
	"github.com/ClusterPilot-System/werftkern/internal/apiclient"
	"github.com/ClusterPilot-System/werftkern/internal/control"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"strings"
	"testing"
)

func TestVolumeAPIEnrollmentOwnershipReleaseAndRevocation(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	q := control.VolumeCreate{Name: "data", NodeID: h.nodeID, UID: 65532, GID: 65532}
	var v model.Volume
	if e := h.admin.Call(ctx, "POST", "/v1/volumes", q, &v, model.ID()); e != nil {
		t.Fatal(e)
	}
	req := model.ApplyRequest{APIVersion: model.APIVersion, Name: "web", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 64, Node: h.nodeID, Volumes: []model.VolumeRef{{Name: "data", MountPath: "/data/app"}}}}
	if e := h.admin.Call(ctx, "POST", "/v1/workloads", req, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	id := model.ID()
	h.s.Update(ctx, func(s *model.State) error {
		s.Allocations[id] = &model.Allocation{ID: id, NodeID: h.nodeID, Name: "web", WorkloadUID: s.Workloads["web"].UID, Spec: req.Spec, Generation: 1, Desired: "run"}
		return nil
	})
	var vs []model.Volume
	if e := h.node.Call(ctx, "GET", "/v1/allocations/"+id+"/volumes", nil, &vs, ""); e != nil || len(vs) != 1 {
		t.Fatal(vs, e)
	}
	other := &apiclient.Client{HTTP: h.tls.Client(t, "node:"+h.otherID), Base: h.tls.Server.URL, ClusterID: h.s.ClusterID}
	if e := other.Call(ctx, "GET", "/v1/allocations/"+id+"/volumes", nil, nil, ""); e == nil {
		t.Fatal("foreign volume access")
	}
	if e := h.node.Call(ctx, "POST", "/v1/volumes/data/initialized", map[string]string{"allocationId": id}, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	if e := h.admin.Call(ctx, "POST", "/v1/volumes/data/release", map[string]string{"id": v.ID}, nil, model.ID()); e == nil {
		t.Fatal("active release")
	}
	h.admin.Call(ctx, "POST", "/v1/nodes/"+h.nodeID, map[string]bool{"revoked": true}, nil, "")
	if e := h.node.Call(ctx, "GET", "/v1/allocations/"+id+"/volumes", nil, nil, ""); e == nil {
		t.Fatal("revoked access")
	}
}
func TestMaintenanceLockHasOneOwner(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	id := model.ID()
	q := control.MaintenanceRequest{ID: id, Enabled: true, Reason: "upgrade"}
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", q, nil, id); e != nil {
		t.Fatal(e)
	}
	q.ID = model.ID()
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", q, nil, q.ID); e == nil {
		t.Fatal("second owner")
	}
	q.Enabled = false
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", q, nil, q.ID); e == nil {
		t.Fatal("foreign release")
	}
	q.ID = id
	if e := h.admin.Call(ctx, "POST", "/v1/maintenance", q, nil, id); e != nil {
		t.Fatal(e)
	}
}
