package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/model"
)

// This checks the actual Go JSON encoder against the actual Python admission
// consumer. In particular, State omits an empty maintenance ID. No host or
// container command is invoked by the Python readiness function.
func TestActualStateJSONAcceptedByOperationsReadiness(t *testing.T) {
	now := time.Now().UTC()
	state := model.NewState("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "wire-test", now)
	id := "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	state.Nodes[id] = &model.Node{ID: id, Name: "worker", Address: "10.8.0.1", Version: model.Version, LastSeen: now, Healthy: true, HeartbeatSequence: 1}
	raw, err := json.Marshal(state)
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(raw, []byte(`"maintenanceId"`)) {
		t.Fatal("test must use actual omitted empty field")
	}
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	ops := filepath.Join(cwd, "..", "..", "ops")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	code := "import sys,json;sys.path.insert(0,sys.argv[1]);from werftops import readiness;s=json.load(sys.stdin);r=readiness.check(s,s['clusterId'],'',sys.argv[2],2);print(json.dumps(r))"
	cmd := exec.CommandContext(ctx, "python3", "-I", "-c", code, ops, model.Version)
	cmd.Stdin = bytes.NewReader(raw)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("actual Go-to-Python wire contract: %v\n%s", err, out)
	}
	var result map[string]uint64
	if err = json.Unmarshal(out, &result); err != nil || len(result) != 1 || result[id] != 1 {
		t.Fatalf("wrong observed sequence projection: %v %s", err, out)
	}
}
