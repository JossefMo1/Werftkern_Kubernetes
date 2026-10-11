package recovery

import (
	"bytes"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"strings"
	"testing"
	"time"
)

func snapshot(t *testing.T) (*model.State, []byte, []byte, []byte) {
	t.Helper()
	master, _ := vault.GenerateKey()
	key, _ := vault.GenerateKey()
	v, _ := vault.New(master)
	s := model.NewState(model.ID(), "source", time.Now())
	ref := model.SecretRef{Name: "db", Version: 1}
	sealed, _ := v.Seal([]byte("top-secret"), model.SecretAAD(s.ClusterID, ref))
	s.Secrets = map[string]model.SecretVersion{"db/1": {Name: "db", Version: 1, Sealed: sealed}}
	_, e := model.Apply(s, model.ApplyRequest{APIVersion: model.APIVersion, Name: "web", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 32, Secrets: []model.SecretRef{ref}}}, model.ID(), time.Now())
	if e != nil {
		t.Fatal(e)
	}
	b, e := Seal(s, 3, master, key, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	return s, master, key, b
}
func TestEncryptedBackupRestoreIsPausedAndRekeys(t *testing.T) {
	s, _, key, b := snapshot(t)
	if bytes.Contains(b, []byte("top-secret")) || bytes.Contains(b, []byte("vaultKey")) {
		t.Fatal("unencrypted backup")
	}
	snap, e := Open(b, key)
	if e != nil {
		t.Fatal(e)
	}
	target := model.NewState(model.ID(), "destination", time.Now())
	newKey, _ := vault.GenerateKey()
	out, e := PrepareRestore(snap, target, newKey, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	if len(out.Nodes) != 0 || len(out.Allocations) != 0 || len(out.Receipts) != 0 || !out.Workloads["web"].Paused || out.Workloads["web"].UID == s.Workloads["web"].UID {
		t.Fatal("unsafe identity restore")
	}
	if e = control.Reconcile(out, time.Now()); e != nil || len(out.Allocations) != 0 {
		t.Fatal("restore started workload")
	}
	v, _ := vault.New(newKey)
	sec := out.Secrets["db/1"]
	plain, e := v.Open(sec.Sealed, model.SecretAAD(out.ClusterID, model.SecretRef{Name: "db", Version: 1}))
	if e != nil || string(plain) != "top-secret" {
		t.Fatal(e)
	}
	if out.Secrets["db/1"].Sealed == s.Secrets["db/1"].Sealed {
		t.Fatal("not reencrypted")
	}
	if _, e = PrepareRestore(snap, s, newKey, time.Now()); e == nil {
		t.Fatal("restored same cluster")
	}
	if _, e = PrepareRestore(snap, out, newKey, time.Now()); e == nil {
		t.Fatal("overwrote populated target")
	}
}
func TestBackupRejectsWrongKeysCorruptionAndBadInventory(t *testing.T) {
	s, master, key, b := snapshot(t)
	wrong, _ := vault.GenerateKey()
	if _, e := Open(b, wrong); e == nil {
		t.Fatal("wrong key")
	}
	for _, bad := range [][]byte{b[:len(b)/2], append(b, []byte(" {}")...), []byte(`{"format":"other","sealed":""}`)} {
		if _, e := Open(bad, key); e == nil {
			t.Fatal("corrupt accepted")
		}
	}
	s.Workloads["web"].Spec.Image = "mutable:latest"
	if _, e := Seal(s, 1, master, key, time.Now()); e == nil {
		t.Fatal("invalid spec archived")
	}
}
func FuzzBackupOpen(f *testing.F) {
	f.Add([]byte(`{}`))
	f.Fuzz(func(t *testing.T, b []byte) {
		if len(b) < 100000 {
			Open(b, make([]byte, 32))
		}
	})
}
