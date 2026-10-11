package control_test

import (
	"bytes"
	"context"
	"encoding/json"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/store"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/testutil"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"io"
	"net/http"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

type harness struct {
	sequence                  atomic.Uint64
	s                         *store.Etcd
	tls                       *testutil.TLSFixture
	admin                     *apiclient.Client
	node                      *apiclient.Client
	nodeID, otherID, instance string
}

func makeHarness(t *testing.T) *harness {
	t.Helper()
	id := model.ID()
	f := testutil.NewEtcd(t, filepath.Join(t.TempDir(), "etcd.json"))
	s := store.NewEtcd(f.URL(), f.Server.Client(), id)
	if e := s.Initialize(context.Background(), model.NewState(id, "test", time.Now())); e != nil {
		t.Fatal(e)
	}
	key, _ := vault.GenerateKey()
	v, _ := vault.New(key)
	api := &control.API{Store: s, ClusterID: id, Vault: v}
	tls := testutil.NewTLS(t, id, api.Handler())
	admin := &apiclient.Client{HTTP: tls.Client(t, "admin"), Base: tls.Server.URL, ClusterID: id}
	nodeID, otherID := model.ID(), model.ID()
	for i, node := range []string{nodeID, otherID} {
		r := control.NodeRegistration{ID: node, Name: []string{"node-a", "node-b"}[i], Address: []string{"127.0.0.2", "127.0.0.3"}[i]}
		if e := admin.Call(context.Background(), "POST", "/v1/nodes", r, nil, ""); e != nil {
			t.Fatal(e)
		}
	}
	return &harness{s: s, tls: tls, admin: admin, node: &apiclient.Client{HTTP: tls.Client(t, "node:"+nodeID), Base: tls.Server.URL, ClusterID: id}, nodeID: nodeID, otherID: otherID, instance: model.ID()}
}
func rawRequest(t *testing.T, c *apiclient.Client, method, path, body, origin string) (int, string) {
	t.Helper()
	r, _ := http.NewRequest(method, c.Base+path, strings.NewReader(body))
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Idempotency-Key", model.ID())
	if origin != "" {
		r.Header.Set("Origin", origin)
	}
	response, e := c.HTTP.Do(r)
	if e != nil {
		t.Fatal(e)
	}
	defer response.Body.Close()
	b, _ := io.ReadAll(response.Body)
	return response.StatusCode, string(b)
}
func hb(h *harness) model.Heartbeat {
	return model.Heartbeat{Sequence: h.sequence.Add(1), InstanceID: h.instance, CPUMilli: 2000, MemoryMiB: 2048, Healthy: true, Version: model.Version}
}
func TestAPIAdminVersusNodeAuthorization(t *testing.T) {
	h := makeHarness(t)
	if _, e := h.admin.State(context.Background()); e != nil {
		t.Fatal(e)
	}
	if _, e := h.node.State(context.Background()); e == nil {
		t.Fatal("node read privileged state")
	}
	r := control.NodeRegistration{ID: model.ID(), Name: "illegal", Address: "127.0.0.4"}
	if e := h.node.Call(context.Background(), "POST", "/v1/nodes", r, nil, ""); e == nil {
		t.Fatal("node created node")
	}
	if e := h.admin.Call(context.Background(), "POST", "/v1/heartbeat", hb(h), nil, ""); e == nil {
		t.Fatal("admin can impersonate node")
	}
}
func TestAPIHeartbeatClaimsNodeAndRejectsClone(t *testing.T) {
	h := makeHarness(t)
	var snap model.AssignmentSnapshot
	if e := h.node.Call(context.Background(), "POST", "/v1/heartbeat", hb(h), &snap, ""); e != nil {
		t.Fatal(e)
	}
	if snap.ClusterID != h.s.ClusterID || snap.Revision < 1 {
		t.Fatal(snap)
	}
	clone := hb(h)
	clone.InstanceID = model.ID()
	if e := h.node.Call(context.Background(), "POST", "/v1/heartbeat", clone, nil, ""); e == nil || !strings.Contains(e.Error(), "NODE_ALREADY_CLAIMED") {
		t.Fatal(e)
	}
}
func TestAPINodeCannotAcknowledgeForeignAllocation(t *testing.T) {
	h := makeHarness(t)
	id := model.ID()
	h.s.Update(context.Background(), func(s *model.State) error {
		fixtureAllocation(s, id, h.otherID)
		return nil
	})
	r := hb(h)
	r.Reports = []model.Report{{ID: id, Phase: "ready"}}
	if e := h.node.Call(context.Background(), "POST", "/v1/heartbeat", r, nil, ""); e == nil || !strings.Contains(e.Error(), "ALLOCATION_SCOPE_DENIED") {
		t.Fatal(e)
	}
}
func TestAPIRevokedNodeCannotHeartbeat(t *testing.T) {
	h := makeHarness(t)
	if e := h.admin.Call(context.Background(), "POST", "/v1/nodes/"+h.nodeID, map[string]bool{"revoked": true}, nil, ""); e != nil {
		t.Fatal(e)
	}
	if e := h.node.Call(context.Background(), "POST", "/v1/heartbeat", hb(h), nil, ""); e == nil {
		t.Fatal("revoked node still admitted")
	}
}
func TestAPIBrowserAndMalformedJSONRejected(t *testing.T) {
	h := makeHarness(t)
	for _, tc := range []struct {
		name, body, origin string
		status             int
	}{{"origin", `{}`, "https://evil.invalid", 403}, {"unknown", `{"surprise":true}`, "", 400}, {"trailing", `{} {}`, "", 400}, {"oversized", `{"x":"` + strings.Repeat("A", 65536) + `"}`, "", 400}} {
		t.Run(tc.name, func(t *testing.T) {
			status, _ := rawRequest(t, h.admin, "POST", "/v1/workloads", tc.body, tc.origin)
			if status != tc.status {
				t.Fatal(status)
			}
		})
	}
}
func TestAPIApplyReplayCASAndDeletion(t *testing.T) {
	h := makeHarness(t)
	r := model.ApplyRequest{APIVersion: model.APIVersion, Name: "shop", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 32}}
	key := model.ID()
	var first, again model.Receipt
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads", r, &first, key); e != nil {
		t.Fatal(e)
	}
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads", r, &again, key); e != nil || model.Hash(first) != model.Hash(again) {
		t.Fatal(first, again, e)
	}
	r.Spec.Replicas = 2
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads", r, nil, key); e == nil {
		t.Fatal("idempotency collision")
	}
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads", r, nil, model.ID()); e == nil {
		t.Fatal("missing expected generation")
	}
	r.ExpectedGeneration = 1
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads", r, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads/shop/delete", model.MutationRequest{ExpectedGeneration: 1}, nil, model.ID()); e == nil {
		t.Fatal("stale delete")
	}
	if e := h.admin.Call(context.Background(), "POST", "/v1/workloads/shop/delete", model.MutationRequest{ExpectedGeneration: 2}, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	s, _, _ := h.s.Read(context.Background())
	if !s.Workloads["shop"].Deleting {
		t.Fatal("delete not persisted")
	}
}
func TestAPIAllocationResponsesAreNodeScoped(t *testing.T) {
	h := makeHarness(t)
	h.s.Update(context.Background(), func(s *model.State) error {
		for _, n := range []string{h.nodeID, h.otherID} {
			id := model.ID()
			fixtureAllocation(s, id, n)
		}
		return nil
	})
	var s model.AssignmentSnapshot
	if e := h.node.Call(context.Background(), "POST", "/v1/heartbeat", hb(h), &s, ""); e != nil {
		t.Fatal(e)
	}
	b, _ := json.Marshal(s)
	if len(s.Allocations) != 1 || bytes.Contains(b, []byte(h.otherID)) {
		t.Fatal("foreign assignment leaked")
	}
}

// Persist only valid aggregates: authorization fixtures must not bypass the same
// inventory validator used after an actual controller restart.
func fixtureAllocation(s *model.State, id, node string) {
	name := "w" + id
	spec := model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 32}
	uid := model.ID()
	s.Workloads[name] = &model.Workload{UID: uid, Name: name, Generation: 1, Spec: spec, Phase: "pending", CreatedAt: time.Now()}
	s.Allocations[id] = &model.Allocation{ID: id, Name: name, NodeID: node, WorkloadUID: uid, Generation: 1, Spec: spec, Desired: "run", Phase: "assigned", CreatedAt: time.Now(), UpdatedAt: time.Now()}
}
