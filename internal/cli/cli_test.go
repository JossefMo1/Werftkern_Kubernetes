package cli

import (
	"context"
	"crypto/sha256"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
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
func TestAgentProcessLockRejectsSymlinkedPaths(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, "target")
	if err := os.WriteFile(target, []byte("target"), 0600); err != nil {
		t.Fatal(err)
	}
	finalLink := filepath.Join(dir, "final.lock")
	if err := os.Symlink(target, finalLink); err != nil {
		t.Fatal(err)
	}
	if unlock, err := lock(finalLink); err == nil {
		unlock()
		t.Fatal("accepted final lock symlink")
	}
	parentLink := filepath.Join(dir, "linked")
	if err := os.Symlink(dir, parentLink); err != nil {
		t.Fatal(err)
	}
	if unlock, err := lock(filepath.Join(parentLink, "nested.lock")); err == nil {
		unlock()
		t.Fatal("accepted parent lock symlink")
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

func TestNodePolicyBody(t *testing.T) {
	tests := map[string]map[string]bool{
		"drain":    map[string]bool{"drain": true},
		"uncordon": map[string]bool{"drain": false},
		"revoke":   map[string]bool{"revoked": true},
	}
	for action, want := range tests {
		got, err := nodePolicyBody(action)
		if err != nil {
			t.Fatalf("%s: unexpected error: %v", action, err)
		}
		if len(got) != len(want) {
			t.Fatalf("%s: got body %#v, want %#v", action, got, want)
		}
		for key, value := range want {
			if got[key] != value {
				t.Fatalf("%s: got body %#v, want %#v", action, got, want)
			}
		}
	}
	if got, err := nodePolicyBody("unknown"); err == nil || err.Error() != "NODE_ACTION_UNKNOWN" || got != nil {
		t.Fatalf("unknown action returned body=%#v, err=%v", got, err)
	}
}

func TestStatefulCLIRejectsUnknownActionsBeforeConfigAccess(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "missing-admin.json")
	t.Setenv("WERFT_CONFIG", missing)
	checks := []struct {
		name string
		call func() error
		want string
	}{
		{name: "volume", call: func() error { return volumeCommand(context.Background(), []string{"inspect"}) }, want: "VOLUME_ACTION_UNSUPPORTED"},
		{name: "secret", call: func() error { return secretCommand(context.Background(), []string{"inspect"}) }, want: "SECRET_ACTION_UNKNOWN"},
		{name: "gateway", call: func() error { return gatewayCommand(context.Background(), []string{"inspect"}) }, want: "GATEWAY_ACTION_UNSUPPORTED"},
	}
	for _, tc := range checks {
		t.Run(tc.name, func(t *testing.T) {
			if err := tc.call(); err == nil || err.Error() != tc.want {
				t.Fatalf("unexpected result: %v", err)
			}
		})
	}
}

func TestSecretCLIRejectsUnexpectedArgumentsBeforeConfigAccess(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "missing-admin.json")
	t.Setenv("WERFT_CONFIG", missing)
	if err := secretCommand(context.Background(), []string{"list", "unexpected"}); err == nil || err.Error() != "SECRET_LIST_TAKES_NO_ARGUMENTS" {
		t.Fatalf("list accepted unexpected arguments: %v", err)
	}
	if err := secretCommand(context.Background(), []string{"put", "db", "unexpected"}); err == nil || err.Error() != "UNEXPECTED_ARGUMENT" {
		t.Fatalf("put accepted unexpected arguments: %v", err)
	}
}

func TestDaemonCommandsRejectUnexpectedArgumentsBeforeConfigAccess(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "missing-daemon.json")
	t.Setenv("WERFT_CONFIG", missing)
	for _, tc := range []struct {
		name string
		call func() error
	}{
		{name: "control", call: func() error { return controlCommand(context.Background(), []string{"unexpected"}) }},
		{name: "agent", call: func() error { return agentCommand(context.Background(), []string{"unexpected"}) }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if err := tc.call(); err == nil || err.Error() != "UNEXPECTED_ARGUMENT" {
				t.Fatalf("unexpected positional argument was accepted: %v", err)
			}
		})
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

func TestReadPrivateSecretRejectsSymlinkedInputs(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "secret")
	if err := os.WriteFile(target, []byte("top-secret"), 0600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(root, "secret-link")
	if err := os.Symlink(target, link); err != nil {
		t.Fatal(err)
	}
	if _, err := readPrivateSecret(link); err == nil {
		t.Fatal("accepted final symlink for secret input")
	}

	targetDir := t.TempDir()
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(targetDir, parentLink); err != nil {
		t.Fatal(err)
	}
	parentPath := filepath.Join(parentLink, "secret")
	if err := os.WriteFile(filepath.Join(targetDir, "secret"), []byte("top-secret"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readPrivateSecret(parentPath); err == nil {
		t.Fatal("accepted symlinked parent for secret input")
	}
}


func TestManifestInputRejectsSymlinkedPaths(t *testing.T) {
	root := t.TempDir()
	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	manifest := filepath.Join(realDir, "manifest.json")
	if err := os.WriteFile(manifest, []byte("{}"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readManifest(manifest); err != nil {
		t.Fatalf("valid manifest rejected: %v", err)
	}
	finalLink := filepath.Join(root, "manifest-link.json")
	if err := os.Symlink(manifest, finalLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readManifest(finalLink); err == nil {
		t.Fatal("accepted final manifest symlink")
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readManifest(filepath.Join(parentLink, "manifest.json")); err == nil {
		t.Fatal("accepted parent manifest symlink")
	}
}

func TestAssessInputRejectsSymlinkedPaths(t *testing.T) {
	root := t.TempDir()
	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	inventory := filepath.Join(realDir, "inventory.json")
	if err := os.WriteFile(inventory, []byte(`{"kind":"List","items":[]}`), 0600); err != nil {
		t.Fatal(err)
	}
	if err := assessCommand([]string{inventory}); err != nil {
		t.Fatalf("valid inventory rejected: %v", err)
	}
	finalLink := filepath.Join(root, "inventory-link.json")
	if err := os.Symlink(inventory, finalLink); err != nil {
		t.Fatal(err)
	}
	if err := assessCommand([]string{finalLink}); err == nil {
		t.Fatal("accepted final inventory symlink")
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if err := assessCommand([]string{filepath.Join(parentLink, "inventory.json")}); err == nil {
		t.Fatal("accepted parent inventory symlink")
	}
}


func TestReadCertificateInputRejectsSymlinkedPaths(t *testing.T) {
	dir := t.TempDir()
	cert := filepath.Join(dir, "admin.crt")
	if err := os.WriteFile(cert, []byte("certificate"), 0600); err != nil {
		t.Fatal(err)
	}
	if got, err := readCertificateInput(cert); err != nil || string(got) != "certificate" {
		t.Fatalf("valid certificate rejected: %v", err)
	}
	finalLink := filepath.Join(dir, "final.crt")
	if err := os.Symlink(cert, finalLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readCertificateInput(finalLink); err == nil {
		t.Fatal("accepted final certificate symlink")
	}
	parentLink := filepath.Join(dir, "linked")
	if err := os.Symlink(dir, parentLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readCertificateInput(filepath.Join(parentLink, "admin.crt")); err == nil {
		t.Fatal("accepted parent certificate symlink")
	}
}

func TestVerifyDemoArchiveRejectsSymlinkedPaths(t *testing.T) {
	root := t.TempDir()
	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	archive := filepath.Join(realDir, "demo.tar")
	data := []byte("demo-archive")
	if err := os.WriteFile(archive, data, 0600); err != nil {
		t.Fatal(err)
	}
	digest := sha256.Sum256(data)
	metadata := fmt.Sprintf(`{"image":"example","archiveSha256":"%x","compiler":"test"}`, digest)
	if err := os.WriteFile(filepath.Join(realDir, "demo.json"), []byte(metadata), 0600); err != nil {
		t.Fatal(err)
	}
	if err := verifyDemoArchive(archive); err != nil {
		t.Fatalf("valid demo archive rejected: %v", err)
	}
	finalLink := filepath.Join(root, "demo-link.tar")
	if err := os.Symlink(archive, finalLink); err != nil {
		t.Fatal(err)
	}
	if err := verifyDemoArchive(finalLink); err == nil {
		t.Fatal("accepted final demo archive symlink")
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if err := verifyDemoArchive(filepath.Join(parentLink, "demo.tar")); err == nil {
		t.Fatal("accepted parent demo archive symlink")
	}
}
