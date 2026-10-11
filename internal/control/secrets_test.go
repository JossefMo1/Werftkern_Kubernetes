package control_test

import (
	"context"
	"encoding/json"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"strings"
	"testing"
	"time"
)

func TestVaultAPIVersionReplayAndNoReadback(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	key := model.ID()
	in := control.SecretInput{Value: []byte("never-in-state-or-events")}
	var ref model.SecretRef
	for i := 0; i < 2; i++ {
		if e := h.admin.Call(ctx, "PUT", "/v1/secrets/db", in, &ref, key); e != nil {
			t.Fatal(e)
		}
	}
	if ref.Version != 1 {
		t.Fatal(ref)
	}
	in.Value = []byte("different")
	if e := h.admin.Call(ctx, "PUT", "/v1/secrets/db", in, nil, key); e == nil {
		t.Fatal("collision")
	}
	if e := h.admin.Call(ctx, "PUT", "/v1/secrets/db", in, nil, model.ID()); e == nil {
		t.Fatal("version conflict")
	}
	in.ExpectedVersion = 1
	if e := h.admin.Call(ctx, "PUT", "/v1/secrets/db", in, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	state, e := h.admin.State(ctx)
	if e != nil {
		t.Fatal(e)
	}
	for _, s := range state.Secrets {
		if s.Sealed != "" {
			t.Fatal("ciphertext in state projection")
		}
	}
	raw, _, _ := h.s.Read(ctx)
	b, _ := json.Marshal(raw)
	if strings.Contains(string(b), "never-in-state-or-events") || raw.Secrets["db/1"].Sealed == "" {
		t.Fatal("plaintext persisted or not stored")
	}
	if e = h.node.Call(ctx, "PUT", "/v1/secrets/db", in, nil, model.ID()); e == nil {
		t.Fatal("node write allowed")
	}
}
func TestVaultPerAllocationAuthorizationAndReferenceProtection(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	secret := control.SecretInput{Value: []byte("secret-bytes")}
	if e := h.admin.Call(ctx, "PUT", "/v1/secrets/db", secret, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	spec := model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 32, Secrets: []model.SecretRef{{Name: "db", Version: 1}}}
	req := model.ApplyRequest{APIVersion: model.APIVersion, Name: "web", Spec: spec}
	if e := h.admin.Call(ctx, "POST", "/v1/workloads", req, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	id := model.ID()
	h.s.Update(ctx, func(s *model.State) error {
		s.Allocations[id] = &model.Allocation{ID: id, NodeID: h.nodeID, Name: "web", WorkloadUID: s.Workloads["web"].UID, Spec: spec, Generation: 1, Desired: "run"}
		return nil
	})
	var values map[string][]byte
	if e := h.node.Call(ctx, "GET", "/v1/allocations/"+id+"/secrets", nil, &values, ""); e != nil || string(values["db"]) != "secret-bytes" {
		t.Fatal(values, e)
	}
	other := &apiclient.Client{HTTP: h.tls.Client(t, "node:"+h.otherID), Base: h.tls.Server.URL, ClusterID: h.s.ClusterID}
	for _, c := range []*apiclient.Client{h.admin, other} {
		if e := c.Call(ctx, "GET", "/v1/allocations/"+id+"/secrets", nil, nil, ""); e == nil {
			t.Fatal("unassigned identity read secret")
		}
	}
	if e := h.admin.Call(ctx, "DELETE", "/v1/secrets/db/1", nil, nil, ""); e == nil {
		t.Fatal("referenced secret deleted")
	}
	h.admin.Call(ctx, "POST", "/v1/nodes/"+h.nodeID, map[string]bool{"revoked": true}, nil, "")
	if e := h.node.Call(ctx, "GET", "/v1/allocations/"+id+"/secrets", nil, nil, ""); e == nil {
		t.Fatal("revoked identity read")
	}
}
func TestApplyMissingSecretRejected(t *testing.T) {
	h := makeHarness(t)
	r := model.ApplyRequest{APIVersion: model.APIVersion, Name: "web", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 32, Secrets: []model.SecretRef{{Name: "missing", Version: 1}}}}
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads", r, nil, model.ID()); e == nil {
		t.Fatal("missing secret admitted")
	}
}
func TestStaleReadinessNotRefreshedByHeartbeat(t *testing.T) {
	h := makeHarness(t)
	ctx := context.Background()
	id := model.ID()
	h.s.Update(ctx, func(s *model.State) error {
		fixtureAllocation(s, id, h.nodeID)
		return nil
	})
	for _, tc := range []struct {
		at    time.Time
		ready bool
	}{{time.Time{}, false}, {time.Now().Add(-time.Hour), false}, {time.Now().Add(time.Hour), false}, {time.Now(), true}} {
		req := hb(h)
		req.Reports = []model.Report{{ID: id, Phase: "ready", ObservedAt: tc.at}}
		if e := h.node.Call(ctx, "POST", "/v1/heartbeat", req, nil, ""); e != nil {
			t.Fatal(e)
		}
		s, _, _ := h.s.Read(ctx)
		if (s.Allocations[id].Phase == "ready") != tc.ready {
			t.Fatal("stale observation accepted")
		}
	}
}
func TestMetricsNoIdentitiesOrSecrets(t *testing.T) {
	h := makeHarness(t)
	code, b := rawRequest(t, h.admin, "GET", "/v1/metrics", "", "")
	if code != 200 || strings.Contains(b, h.nodeID) || !strings.Contains(b, "werftkern_nodes ") {
		t.Fatal(b)
	}
	code, _ = rawRequest(t, h.node, "GET", "/v1/metrics", "", "")
	if code != 403 {
		t.Fatal("node sees cluster metrics")
	}
}
