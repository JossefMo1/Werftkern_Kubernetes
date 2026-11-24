package cli

import (
	"context"
	"encoding/json"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/setup"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"os"
	"path/filepath"
)

// validateSchemaBackupOutput runs before loading the backup key or mutating
// source state. An existing destination must fail closed before migration.
func validateSchemaBackupOutput(keyPath, backup string) error {
	if keyPath == "" || backup == "" {
		return errors.New("SCHEMA_BACKUP_AND_EXPECTED_HASH_REQUIRED")
	}
	keyAbs, keyErr := filepath.Abs(keyPath)
	backupAbs, backupErr := filepath.Abs(backup)
	if keyErr == nil && backupErr == nil && keyAbs == backupAbs || filepath.Clean(keyPath) == filepath.Clean(backup) {
		return errors.New("SCHEMA_BACKUP_AND_EXPECTED_HASH_REQUIRED")
	}
	if _, e := os.Lstat(backup); !os.IsNotExist(e) {
		return errors.New("SCHEMA_BACKUP_OUTPUT_ALREADY_EXISTS")
	}
	return nil
}

func schemaCommand(ctx context.Context, args []string) error {
	if len(args) == 0 || args[0] != "inspect" && args[0] != "migrate" {
		return errors.New("schema inspect|migrate --maintenance-id ID [--source-sha256 HASH --backup FILE --key-file KEY]")
	}
	if e := setup.RequireRoot(); e != nil {
		return e
	}
	f := parser("schema " + args[0])
	owner := f.String("maintenance-id", "", "Maintenance already held by old CLI")
	expected := f.String("source-sha256", "", "Exact hash from inspect, after stopping all writers")
	backup := f.String("backup", "", "New encrypted source-state backup")
	keyPath := f.String("key-file", "", "Separate backup key")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	if f.NArg() != 0 {
		return errors.New("SCHEMA_ARGUMENTS_INVALID")
	}
	if args[0] == "migrate" {
		if *expected == "" {
			return errors.New("SCHEMA_BACKUP_AND_EXPECTED_HASH_REQUIRED")
		}
		if e := validateSchemaBackupOutput(*keyPath, *backup); e != nil {
			return e
		}
	}
	_, db, _, e := localStore()
	if e != nil {
		return e
	}
	if args[0] == "inspect" {
		out, e := db.PreviewMigration(ctx, *owner)
		if e != nil {
			return e
		}
		return json.NewEncoder(os.Stdout).Encode(out)
	}
	key, e := vault.LoadKey(*keyPath)
	if os.IsNotExist(e) {
		key, e = vault.CreateKey(*keyPath)
	}
	if e != nil {
		return e
	}
	v, e := vault.New(key)
	if e != nil {
		return e
	}
	out, e := db.MigrateSchema(ctx, *owner, *expected, func(raw []byte) error {
		aad := "werftkern/schema-migration/v1/" + db.ClusterID + "/" + *expected
		sealed, e := v.Seal(raw, aad)
		if e != nil {
			return e
		}
		body, e := json.Marshal(map[string]any{"format": "werftkern-schema-source/v1", "clusterId": db.ClusterID, "sourceSha256": *expected, "aad": aad, "sealed": sealed})
		if e != nil {
			return e
		}
		f, e := safefile.CreateExclusive(*backup, 0600)
		if e != nil {
			return e
		}
		ok := false
		defer func() {
			f.Close()
			if !ok {
				os.Remove(*backup)
			}
		}()
		if _, e = f.Write(body); e != nil {
			return e
		}
		if e = f.Sync(); e != nil {
			return e
		}
		if e = f.Close(); e != nil {
			return e
		}
		if e = syncDir(filepath.Dir(*backup)); e != nil {
			return e
		}
		ok = true
		return nil
	})
	if e != nil {
		return e
	}
	return json.NewEncoder(os.Stdout).Encode(out)
}
