package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/store"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/testutil"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/volumearchive"
)

func TestVolumeArchiveCLIPhysicalRestoreAfterLostAcknowledgment(t *testing.T) {
	if os.Geteuid() != 0 {
		t.Skip("CLI root boundary requires explicit privileged test host; archive/lock/API tests run unprivileged")
	}
	ctx := context.Background()
	base := t.TempDir()
	cluster, sourceNode, targetNode, maintenance := model.ID(), model.ID(), model.ID(), model.ID()
	state := model.NewState(cluster, "volume-cli", time.Now())
	state.MaintenanceID = maintenance
	state.Nodes[sourceNode] = &model.Node{ID: sourceNode, Name: "source", Address: "127.0.0.2"}
	state.Nodes[targetNode] = &model.Node{ID: targetNode, Name: "target", Address: "127.0.0.3"}
	source := &model.Volume{ID: model.ID(), Name: "source-data", NodeID: sourceNode, UID: 65532, GID: 65532, Initialized: true}
	target := &model.Volume{ID: model.ID(), Name: "target-data", NodeID: targetNode, UID: 65532, GID: 65532}
	state.Volumes = map[string]*model.Volume{source.Name: source, target.Name: target}
	fixture := testutil.NewEtcd(t, filepath.Join(base, "etcd.json"))
	db := store.NewEtcd(fixture.URL(), fixture.Server.Client(), cluster)
	if e := db.Initialize(ctx, state); e != nil {
		t.Fatal(e)
	}
	api := (&control.API{Store: db, ClusterID: cluster}).Handler()
	var failedACK atomic.Bool
	tls := testutil.NewTLS(t, cluster, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" && r.URL.Path == "/v1/volumes/target-data/restore" {
			raw, _ := io.ReadAll(r.Body)
			r.Body = io.NopCloser(bytes.NewReader(raw))
			var q control.VolumeRestoreRequest
			json.Unmarshal(raw, &q)
			if q.Complete && failedACK.CompareAndSwap(false, true) {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(503)
				io.WriteString(w, `{"code":"INJECTED_ACK_LOSS"}`)
				return
			}
		}
		api.ServeHTTP(w, r)
	}))
	pair, e := pki.Issue(tls.CA, "admin", cluster, nil, false, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	for name, b := range map[string][]byte{"ca.crt": tls.CA.Cert, "client.crt": pair.Cert, "client.key": pair.Key} {
		if e = os.WriteFile(filepath.Join(base, name), b, 0600); e != nil {
			t.Fatal(e)
		}
	}
	cc := config.Client{Server: tls.Server.URL, ClusterID: cluster, CA: base + "/ca.crt", Cert: base + "/client.crt", Key: base + "/client.key"}
	admin := base + "/admin.json"
	if e = safefile.JSON(admin, cc, 0600); e != nil {
		t.Fatal(e)
	}
	t.Setenv("WERFT_CONFIG", admin)
	// Real UNIX socket transport, but explicitly a Docker API TEST ADAPTER.
	socket := filepath.Join(base, "docker.sock")
	l, e := net.Listen("unix", socket)
	if e != nil {
		t.Fatal(e)
	}
	docker := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/version":
			io.WriteString(w, `{"ApiVersion":"1.41"}`)
		case "/v1.41/containers/json":
			io.WriteString(w, `[]`)
		default:
			http.Error(w, "unexpected Docker request", 404)
		}
	})}
	go docker.Serve(l)
	t.Cleanup(func() { docker.Close() })
	sourceRoot, targetRoot := base+"/source-root", base+"/target-root"
	sourceDir := filepath.Join(sourceRoot, source.ID)
	if e = os.MkdirAll(sourceDir+"/data", 0700); e != nil {
		t.Fatal(e)
	}
	expected := bytes.Repeat([]byte("persistent-data-not-fixture-ack\x00"), 10000)
	if e = os.WriteFile(sourceDir+"/data/database.bin", expected, 0600); e != nil {
		t.Fatal(e)
	}
	if e = safefile.JSON(sourceDir+"/identity.json", diskVolumeIdentity{source.ID, cluster, sourceNode, 65532, 65532}, 0600); e != nil {
		t.Fatal(e)
	}
	agentFile := base + "/agent.json"
	ac := config.Agent{Client: cc, NodeID: sourceNode, Socket: socket, VolumeRoot: sourceRoot}
	if e = safefile.JSON(agentFile, ac, 0600); e != nil {
		t.Fatal(e)
	}
	archive, key := base+"/volume.wva", base+"/backup.key"
	if e = volumeArchiveCommand(ctx, []string{"backup", source.Name, "--agent-config", agentFile, "--file", archive, "--key-file", key, "--maintenance-id", maintenance}); e != nil {
		t.Fatal(e)
	}
	ac.NodeID = targetNode
	ac.VolumeRoot = targetRoot
	if e = safefile.JSON(agentFile, ac, 0600); e != nil {
		t.Fatal(e)
	}
	op := model.ID()
	args := []string{"restore", target.Name, "--agent-config", agentFile, "--file", archive, "--key-file", key, "--maintenance-id", maintenance, "--operation-id", op}
	if e = volumeArchiveCommand(ctx, args); e == nil || !strings.Contains(e.Error(), "ACK_PENDING") {
		t.Fatal("injected lost acknowledgment not observed", e)
	}
	s, _, e := db.Read(ctx)
	if e != nil {
		t.Fatal(e)
	}
	if !s.Volumes[target.Name].Initialized || s.Volumes[target.Name].RestoreComplete {
		t.Fatal("failed ack allowed empty initialization")
	}
	data := filepath.Join(targetRoot, target.ID, "data", "database.bin")
	got, e := os.ReadFile(data)
	if e != nil || !bytes.Equal(got, expected) {
		t.Fatal("physical data not restored", e)
	}
	// A lost-ACK retry must fail closed when the staged tree was modified.
	sentinel := filepath.Join(targetRoot, target.ID, "data", "sentinel")
	if e = os.WriteFile(sentinel, []byte("keep"), 0600); e != nil {
		t.Fatal(e)
	}
	if e = volumeArchiveCommand(ctx, args); e == nil || !strings.Contains(e.Error(), "DATA_INTEGRITY") {
		t.Fatalf("modified restore tree was acknowledged: %v", e)
	}
	s, _, e = db.Read(ctx)
	if e != nil || s.Volumes[target.Name].RestoreComplete {
		t.Fatal("failed integrity check acknowledged restore", e)
	}
	if e = os.Remove(sentinel); e != nil {
		t.Fatal(e)
	}
	if e = volumeArchiveCommand(ctx, args); e != nil {
		t.Fatal("retry failed after restoring the tree", e)
	}
	s, _, e = db.Read(ctx)
	if e != nil || !s.Volumes[target.Name].RestoreComplete {
		t.Fatal("restore not acknowledged", e)
	}
	// Even after completion, a replay never replaces data and rejects drift.
	if e = os.WriteFile(sentinel, []byte("keep"), 0600); e != nil {
		t.Fatal(e)
	}
	if e = volumeArchiveCommand(ctx, args); e == nil || !strings.Contains(e.Error(), "DATA_INTEGRITY") {
		t.Fatalf("completed replay accepted modified data: %v", e)
	}
	if _, e = os.Stat(sentinel); e != nil {
		t.Fatal("replay replaced tree")
	}
	t.Log("Executed real CLI, files, encryption, mTLS and UNIX HTTP with injected ACK failure; etcd/Docker remained explicit adapters, not live services.")
}


func TestOpenVolumeArchiveRejectsParentSymlink(t *testing.T) {
	root := t.TempDir()
	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	archive := filepath.Join(realDir, "backup.wva")
	if err := os.WriteFile(archive, []byte("archive"), 0600); err != nil {
		t.Fatal(err)
	}
	f, err := openVolumeArchive(archive)
	if err != nil {
		t.Fatalf("valid archive rejected: %v", err)
	}
	if err := f.Close(); err != nil {
		t.Fatal(err)
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if f, err := openVolumeArchive(filepath.Join(parentLink, "backup.wva")); err == nil {
		f.Close()
		t.Fatal("followed archive parent symlink")
	}
}

func TestVolumeArchiveRejectsUnknownActionBeforePrivilegeOrStateAccess(t *testing.T) {
	if err := volumeArchiveCommand(context.Background(), []string{"inspect", "data"}); err == nil || err.Error() != "VOLUME_ARCHIVE_ACTION_INVALID" {
		t.Fatalf("unexpected unknown-action result: %v", err)
	}
}


func TestValidateVolumeArchiveBackupOutput(t *testing.T) {
	root := t.TempDir()
	existing := filepath.Join(root, "existing.wva")
	if err := os.WriteFile(existing, []byte("existing"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := validateVolumeArchiveBackupOutput(existing); err == nil || err.Error() != "VOLUME_ARCHIVE_OUTPUT_ALREADY_EXISTS" {
		t.Fatalf("existing archive was not rejected before key creation: %v", err)
	}
	link := filepath.Join(root, "archive-link.wva")
	if err := os.Symlink(existing, link); err != nil {
		t.Fatal(err)
	}
	if err := validateVolumeArchiveBackupOutput(link); err == nil || err.Error() != "VOLUME_ARCHIVE_OUTPUT_ALREADY_EXISTS" {
		t.Fatalf("archive symlink was not rejected before key creation: %v", err)
	}
	missing := filepath.Join(root, "new.wva")
	if err := validateVolumeArchiveBackupOutput(missing); err != nil {
		t.Fatalf("new archive path rejected: %v", err)
	}
	missingParent := filepath.Join(root, "missing", "new.wva")
	if err := validateVolumeArchiveBackupOutput(missingParent); err == nil || err.Error() != "VOLUME_ARCHIVE_OUTPUT_PARENT_UNSAFE_OR_MISSING" {
		t.Fatalf("missing archive parent was not rejected before key creation: %v", err)
	}
	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	unsafeParent := filepath.Join(parentLink, "new.wva")
	if err := validateVolumeArchiveBackupOutput(unsafeParent); err == nil || err.Error() != "VOLUME_ARCHIVE_OUTPUT_PARENT_UNSAFE_OR_MISSING" {
		t.Fatalf("symlinked archive parent was not rejected before key creation: %v", err)
	}
}


func TestRestoreTreeDigestHonorsArchiveLimits(t *testing.T) {
	root := filepath.Join(t.TempDir(), "data")
	if err := os.MkdirAll(root, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "payload"), []byte("0123456789"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := restoreTreeDigest(root, volumearchive.Limits{Bytes: 9}); err == nil || err.Error() != "RESTORE_DATA_LIMIT_EXCEEDED" {
		t.Fatalf("oversized existing restore tree was accepted: %v", err)
	}
}
