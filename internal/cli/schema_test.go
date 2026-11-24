package cli

import (
	"os"
	"path/filepath"
	"testing"
)

func TestValidateSchemaBackupOutput(t *testing.T) {
	root := t.TempDir()
	keyPath := filepath.Join(root, "backup.key")
	existing := filepath.Join(root, "existing.backup")
	if err := os.WriteFile(existing, []byte("existing"), 0600); err != nil {
		t.Fatal(err)
	}

	if err := validateSchemaBackupOutput(keyPath, ""); err == nil || err.Error() != "SCHEMA_BACKUP_AND_EXPECTED_HASH_REQUIRED" {
		t.Fatalf("missing backup path was accepted: %v", err)
	}
	if err := validateSchemaBackupOutput(keyPath, filepath.Join(root, ".", "backup.key")); err == nil || err.Error() != "SCHEMA_BACKUP_AND_EXPECTED_HASH_REQUIRED" {
		t.Fatalf("same key and backup path was accepted: %v", err)
	}
	if err := validateSchemaBackupOutput(keyPath, existing); err == nil || err.Error() != "SCHEMA_BACKUP_OUTPUT_ALREADY_EXISTS" {
		t.Fatalf("existing backup path was not rejected before migration: %v", err)
	}

	link := filepath.Join(root, "backup-link")
	if err := os.Symlink(existing, link); err != nil {
		t.Fatal(err)
	}
	if err := validateSchemaBackupOutput(keyPath, link); err == nil || err.Error() != "SCHEMA_BACKUP_OUTPUT_ALREADY_EXISTS" {
		t.Fatalf("symlinked backup path was not rejected before migration: %v", err)
	}

	if err := validateSchemaBackupOutput(keyPath, filepath.Join(root, "new.backup")); err != nil {
		t.Fatalf("new backup path was rejected: %v", err)
	}
}

func TestValidateSchemaBackupOutputRejectsUnsafeParents(t *testing.T) {
	root := t.TempDir()
	keyPath := filepath.Join(root, "backup.key")
	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if err := validateSchemaBackupOutput(keyPath, filepath.Join(parentLink, "new.backup")); err == nil || err.Error() != "SCHEMA_BACKUP_PARENT_UNSAFE_OR_MISSING" {
		t.Fatalf("symlinked schema backup parent was accepted: %v", err)
	}
	if err := validateSchemaBackupOutput(keyPath, filepath.Join(root, "missing", "new.backup")); err == nil || err.Error() != "SCHEMA_BACKUP_PARENT_UNSAFE_OR_MISSING" {
		t.Fatalf("missing schema backup parent was accepted: %v", err)
	}
}
