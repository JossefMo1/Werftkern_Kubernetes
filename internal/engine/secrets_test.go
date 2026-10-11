package engine

import (
	"context"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSecretsStagedBeforeCreateAndRemovedOnStop(t *testing.T) {
	f := dockerTest(t)
	a := allocation()
	a.Spec.Secrets = []model.SecretRef{{Name: "db", Version: 1}}
	calls := 0
	f.d.Secrets = func(context.Context, model.Allocation) (map[string][]byte, error) {
		calls++
		return map[string][]byte{"db": []byte("secret-value")}, nil
	}
	for i := 0; i < 2; i++ {
		if _, e := f.d.Ensure(context.Background(), a, "127.0.0.1", func() bool { return true }); e != nil {
			t.Fatal(e)
		}
	}
	if calls != 1 || f.creates != 1 {
		t.Fatal("repeated fetch/create")
	}
	h := f.create["HostConfig"].(map[string]any)
	if h["RestartPolicy"].(map[string]any)["Name"] != "no" {
		t.Fatal("daemon could restart before tmpfs secrets are restored")
	}
	bind := h["Binds"].([]any)[0].(string)
	if !strings.HasSuffix(bind, ":/run/secrets:ro,rprivate") {
		t.Fatal(bind)
	}
	path := filepath.Join(f.d.SecretRoot, a.ID, "db")
	b, e := os.ReadFile(path)
	if e != nil || string(b) != "secret-value" {
		t.Fatal(e)
	}
	st, _ := os.Stat(path)
	if st.Mode().Perm() != 0444 {
		t.Fatal("mode")
	}
	if e = f.d.Stop(context.Background(), a.ID); e != nil {
		t.Fatal(e)
	}
	if _, e = os.Stat(path); !os.IsNotExist(e) {
		t.Fatal("secret retained")
	}
}
func TestMissingSecretNeverStartsContainer(t *testing.T) {
	f := dockerTest(t)
	a := allocation()
	a.Spec.Secrets = []model.SecretRef{{Name: "db", Version: 1}}
	if _, e := f.d.Ensure(context.Background(), a, "127.0.0.1", func() bool { return true }); e == nil {
		t.Fatal("missing secret accepted")
	}
	if f.creates != 0 || f.starts != 0 {
		t.Fatal("started without secret")
	}
}
func TestSecretScopeMismatchAndSymlinkRejected(t *testing.T) {
	f := dockerTest(t)
	a := allocation()
	a.Spec.Secrets = []model.SecretRef{{Name: "db", Version: 1}}
	f.d.Secrets = func(context.Context, model.Allocation) (map[string][]byte, error) {
		return map[string][]byte{"foreign": []byte("x")}, nil
	}
	if _, e := f.d.secretDirectory(context.Background(), a); e == nil {
		t.Fatal("foreign set")
	}
	os.Symlink(t.TempDir(), filepath.Join(f.d.SecretRoot, a.ID))
	if _, e := f.d.secretDirectory(context.Background(), a); e == nil {
		t.Fatal("symlink")
	}
}
func TestSecretProductionModeRejectsDiskFilesystem(t *testing.T) {
	f := dockerTest(t)
	f.d.RequireSecretTmpfs = true
	a := allocation()
	a.Spec.Secrets = []model.SecretRef{{Name: "db", Version: 1}}
	if _, e := f.d.secretDirectory(context.Background(), a); e == nil {
		t.Fatal("disk accepted as tmpfs")
	}
}
