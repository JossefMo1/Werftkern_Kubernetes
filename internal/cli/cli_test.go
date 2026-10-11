package cli

import (
	"context"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestManifestIsStrict(t *testing.T) {
	for _, raw := range []string{`{"name":"one","Name":"two"}`, `{"name":"one","name":"two"}`, `{} {}`, `{"unknown":true}`, strings.Repeat(" ", 65538) + `{}`} {
		p := filepath.Join(t.TempDir(), "input.json")
		os.WriteFile(p, []byte(raw), 0600)
		if _, e := readManifest(p); e == nil {
			t.Fatal("accepted invalid manifest")
		}
	}
}
func TestAgentProcessLock(t *testing.T) {
	p := filepath.Join(t.TempDir(), "lock")
	unlock, e := lock(p)
	if e != nil {
		t.Fatal(e)
	}
	defer unlock()
	if second, e := lock(p); e == nil {
		second()
		t.Fatal("second process admitted")
	}
}
func TestInvalidWaitDoesNotConnect(t *testing.T) {
	if Wait(context.Background(), nil, "bad/name", time.Second) == nil {
		t.Fatal("invalid name")
	}
	if Wait(context.Background(), nil, "valid", -time.Second) == nil {
		t.Fatal("invalid timeout")
	}
}
func TestEndpointsHideOfflineDrainingAndForeign(t *testing.T) {
	now := time.Now()
	s := model.NewState(model.ID(), "test", now)
	uid := model.ID()
	s.Workloads["demo"] = &model.Workload{UID: uid}
	node := model.ID()
	s.Nodes[node] = &model.Node{ID: node, Healthy: true, LastSeen: now, Address: "127.0.0.1"}
	s.Allocations[model.ID()] = &model.Allocation{WorkloadUID: uid, NodeID: node, Desired: "run", Phase: "ready", HostPort: 22000}
	if len(Endpoints(s, "demo")) != 1 {
		t.Fatal("missing endpoint")
	}
	s.Nodes[node].LastSeen = now.Add(-time.Minute)
	if len(Endpoints(s, "demo")) != 0 {
		t.Fatal("offline endpoint exposed")
	}
}
