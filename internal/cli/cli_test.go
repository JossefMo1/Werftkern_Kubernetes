package cli

import (
	"context"
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
