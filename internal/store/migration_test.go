package store

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/testutil"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func legacyStore(t *testing.T) (*Etcd, string) {
	t.Helper()
	id, owner := model.ID(), model.ID()
	fixture := testutil.NewEtcd(t, filepath.Join(t.TempDir(), "state.json"))
	db := NewEtcd(fixture.URL(), fixture.Server.Client(), id)
	s := model.NewState(id, "migration", time.Now())
	s.Schema = 1
	s.MaintenanceID = owner
	raw, _ := json.Marshal(s)
	var result any
	e := db.call(context.Background(), "/v3/kv/txn", map[string]any{"compare": []any{map[string]any{"key": b64([]byte(db.Key)), "target": "VERSION", "result": "EQUAL", "version": "0"}}, "success": []any{map[string]any{"request_put": map[string]any{"key": b64([]byte(db.Key)), "value": base64.StdEncoding.EncodeToString(raw)}}}, "failure": []any{}}, &result)
	if e != nil {
		t.Fatal(e)
	}
	return db, owner
}
func TestOfflineSchemaMigrationRequiresBackupHashAndPreservesMaintenance(t *testing.T) {
	db, owner := legacyStore(t)
	ctx := context.Background()
	if _, _, e := db.Read(ctx); e == nil {
		t.Fatal("legacy schema permitted new writers")
	}
	preview, e := db.PreviewMigration(ctx, owner)
	if e != nil {
		t.Fatal(e)
	}
	calls := 0
	backup := func(raw []byte) error {
		calls++
		var s model.State
		if e := json.Unmarshal(raw, &s); e != nil || s.Schema != 1 {
			t.Fatal("backup not source", e)
		}
		return nil
	}
	if _, e = db.MigrateSchema(ctx, owner, strings.Repeat("b", 64), backup); e == nil || calls != 0 {
		t.Fatal("wrong hash consumed backup", e)
	}
	if _, e = db.MigrateSchema(ctx, owner, preview.SourceSHA256, func([]byte) error { return errors.New("backup failed") }); e == nil {
		t.Fatal("ignored backup failure")
	}
	if _, _, e = db.Read(ctx); e == nil {
		t.Fatal("mutated before backup")
	}
	if _, e = db.MigrateSchema(ctx, owner, preview.SourceSHA256, backup); e != nil {
		t.Fatal(e)
	}
	s, _, e := db.Read(ctx)
	if e != nil || s.Schema != model.StateSchema || s.MaintenanceID != owner || s.MigrationSourceHash != preview.SourceSHA256 {
		t.Fatal(e, s)
	}
	if _, e = db.MigrateSchema(ctx, owner, preview.SourceSHA256, backup); e != nil || calls != 1 {
		t.Fatal("retry did not deduplicate", e, calls)
	}
}
func TestOfflineSchemaMigrationAbortsWhenAnotherWriterChangesState(t *testing.T) {
	db, owner := legacyStore(t)
	ctx := context.Background()
	p, e := db.PreviewMigration(ctx, owner)
	if e != nil {
		t.Fatal(e)
	}
	_, e = db.MigrateSchema(ctx, owner, p.SourceSHA256, func(raw []byte) error {
		var s model.State
		json.Unmarshal(raw, &s)
		s.Schema = model.StateSchema
		s.Name = "competing-writer"
		ok, _, e := db.cas(ctx, &s, p.Revision)
		if !ok || e != nil {
			t.Fatal(ok, e)
		}
		return nil
	})
	if !errors.Is(e, model.ErrConflict) {
		t.Fatal(e)
	}
	s, _, e := db.Read(ctx)
	if e != nil || s.Name != "competing-writer" {
		t.Fatal("concurrent update overwritten", e)
	}
}
func TestMigrationRefusesLiveWorkloadsAndAllocations(t *testing.T) {
	id, owner := model.ID(), model.ID()
	s := model.NewState(id, "migration", time.Now())
	s.Schema = 1
	s.MaintenanceID = owner
	s.Workloads["app"] = &model.Workload{Name: "app", UID: model.ID(), Generation: 1}
	raw, _ := json.Marshal(s)
	if _, _, e := prepareMigration(raw, id, owner); e == nil {
		t.Fatal("live workload migrated")
	}
	delete(s.Workloads, "app")
	s.Allocations[model.ID()] = &model.Allocation{Phase: "stopped"}
	raw, _ = json.Marshal(s)
	if _, _, e := prepareMigration(raw, id, owner); e == nil {
		t.Fatal("unclean allocations migrated")
	}
}
