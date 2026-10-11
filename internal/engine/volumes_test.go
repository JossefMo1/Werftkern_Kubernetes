package engine

import (
	"context"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func volumeFixture(t *testing.T) (*Docker, model.Allocation, *model.Volume) {
	t.Helper()
	a := allocation()
	a.NodeID = model.ID()
	a.WorkloadUID = model.ID()
	u, g := os.Getuid(), os.Getgid()
	if u == 0 {
		u, g = 65532, 65532
	}
	a.Spec.Node = a.NodeID
	a.Spec.RunAsUID = u
	a.Spec.RunAsGID = g
	a.Spec.Volumes = []model.VolumeRef{{Name: "data", MountPath: "/data/app"}}
	v := &model.Volume{ID: model.ID(), Name: "data", NodeID: a.NodeID, UID: u, GID: g, Owner: a.WorkloadUID}
	d := NewDocker("unused", model.ID())
	d.VolumeRoot = t.TempDir()
	os.Chmod(d.VolumeRoot, 0700)
	d.Volumes = func(context.Context, model.Allocation) ([]model.Volume, error) { return []model.Volume{*v}, nil }
	d.VolumeAck = func(context.Context, model.Allocation, string) error { v.Initialized = true; return nil }
	return d, a, v
}
func TestVolumeDurableDirectoryReused(t *testing.T) {
	d, a, v := volumeFixture(t)
	b, e := d.volumeBinds(context.Background(), a)
	if e != nil {
		t.Fatal(e)
	}
	if !v.Initialized || len(b) != 1 {
		t.Fatal("not acknowledged")
	}
	data := filepath.Join(d.VolumeRoot, v.ID, "data")
	if e = os.WriteFile(filepath.Join(data, "sentinel"), []byte("saved"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e = d.volumeBinds(context.Background(), a); e != nil {
		t.Fatal(e)
	}
	if got, _ := os.ReadFile(filepath.Join(data, "sentinel")); string(got) != "saved" {
		t.Fatal("data loss")
	}
}
func TestInitializedVolumeMissingBlocksInsteadOfEmptyDatabase(t *testing.T) {
	d, a, v := volumeFixture(t)
	v.Initialized = true
	if _, e := d.volumeBinds(context.Background(), a); e == nil || !strings.Contains(e.Error(), "REFUSING_EMPTY") {
		t.Fatal(e)
	}
}
func TestVolumeForeignOwnerAndSymlinkRejected(t *testing.T) {
	d, a, v := volumeFixture(t)
	v.Owner = model.ID()
	if _, e := d.volumeBinds(context.Background(), a); e == nil {
		t.Fatal("foreign owner")
	}
	v.Owner = a.WorkloadUID
	if e := os.Symlink(t.TempDir(), filepath.Join(d.VolumeRoot, v.ID)); e != nil {
		t.Fatal(e)
	}
	if _, e := d.volumeBinds(context.Background(), a); e == nil {
		t.Fatal("symlink")
	}
}
func TestVolumeIdentityMismatchDoesNotRewrite(t *testing.T) {
	d, a, _ := volumeFixture(t)
	if _, e := d.volumeBinds(context.Background(), a); e != nil {
		t.Fatal(e)
	}
	d.ClusterID = model.ID()
	if _, e := d.volumeBinds(context.Background(), a); e == nil {
		t.Fatal("foreign cluster adopted volume")
	}
}
func TestPersistentContainerDisablesDaemonRestartAndKeepsData(t *testing.T) {
	f := dockerTest(t)
	d, a, v := volumeFixture(t)
	f.d.VolumeRoot = d.VolumeRoot
	f.d.Volumes = d.Volumes
	f.d.VolumeAck = d.VolumeAck
	if _, e := f.d.Ensure(context.Background(), a, "127.0.0.1", func() bool { return true }); e != nil {
		t.Fatal(e)
	}
	h := f.create["HostConfig"].(map[string]any)
	if h["RestartPolicy"].(map[string]any)["Name"] != "no" {
		t.Fatal("unsafe independent restart")
	}
	if e := f.d.Stop(context.Background(), a.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := os.Stat(filepath.Join(d.VolumeRoot, v.ID, "data")); e != nil {
		t.Fatal("stop deleted persistent data")
	}
}
