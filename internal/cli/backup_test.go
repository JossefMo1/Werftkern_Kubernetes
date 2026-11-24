package cli

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestReadBackupInputRejectsSymlinkedInputs(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "backup")
	if err := os.WriteFile(target, []byte("encrypted-backup"), 0600); err != nil {
		t.Fatal(err)
	}
	finalLink := filepath.Join(root, "backup-link")
	if err := os.Symlink(target, finalLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readBackupInput(finalLink); err == nil {
		t.Fatal("accepted final symlink for backup input")
	}

	targetDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(targetDir, "backup"), []byte("encrypted-backup"), 0600); err != nil {
		t.Fatal(err)
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(targetDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readBackupInput(filepath.Join(parentLink, "backup")); err == nil {
		t.Fatal("accepted symlinked parent for backup input")
	}
}

func TestReadBackupInputReadsRegularFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "backup")
	want := []byte("encrypted-backup")
	if err := os.WriteFile(path, want, 0600); err != nil {
		t.Fatal(err)
	}
	got, err := readBackupInput(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(want) {
		t.Fatalf("read %q, want %q", got, want)
	}
}
func TestBackupCLIRejectsUnexpectedArgumentsBeforeStateAccess(t *testing.T) {
	if os.Geteuid() != 0 {
		t.Skip("CLI root boundary requires explicit privileged test host")
	}
	missing := filepath.Join(t.TempDir(), "missing-admin.json")
	t.Setenv("WERFT_CONFIG", missing)
	key := filepath.Join(t.TempDir(), "backup.key")
	out := filepath.Join(t.TempDir(), "backup.json")
	if err := backupCommand(context.Background(), []string{"create", "--key-file", key, "--out", out, "unexpected"}); err == nil || err.Error() != "BACKUP_ARGUMENTS_INVALID" {
		t.Fatalf("unexpected positional argument was accepted: %v", err)
	}
}

func TestValidateBackupCreateOutput(t *testing.T) {
	root := t.TempDir()
	keyPath := filepath.Join(root, "backup.key")
	existing := filepath.Join(root, "existing.backup")
	if err := os.WriteFile(existing, []byte("existing"), 0600); err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name string
		out  string
		want string
	}{
		{name: "missing output", out: "", want: "DISTINCT_OUTPUT_AND_KEY_PATH_REQUIRED"},
		{name: "same as key", out: keyPath, want: "DISTINCT_OUTPUT_AND_KEY_PATH_REQUIRED"},
		{name: "existing output", out: existing, want: "BACKUP_OUTPUT_ALREADY_EXISTS"},
		{name: "new output", out: filepath.Join(root, "new.backup")},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateBackupCreateOutput(keyPath, tt.out)
			if tt.want == "" {
				if err != nil {
					t.Fatalf("validateBackupCreateOutput() error = %v", err)
				}
				return
			}
			if err == nil || err.Error() != tt.want {
				t.Fatalf("validateBackupCreateOutput() error = %v, want %s", err, tt.want)
			}
		})
	}
}


func TestValidateBackupCreateOutputRejectsUnsafeParentsAndAbsoluteCollisions(t *testing.T) {
	root := t.TempDir()
	keyPath := filepath.Join(root, "backup.key")
	absoluteKey, err := filepath.Abs(keyPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := validateBackupCreateOutput(keyPath, absoluteKey); err == nil || err.Error() != "DISTINCT_OUTPUT_AND_KEY_PATH_REQUIRED" {
		t.Fatalf("absolute key/output collision was accepted: %v", err)
	}

	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if err := validateBackupCreateOutput(keyPath, filepath.Join(parentLink, "new.backup")); err == nil || err.Error() != "BACKUP_OUTPUT_PARENT_UNSAFE_OR_MISSING" {
		t.Fatalf("symlinked backup parent was accepted: %v", err)
	}
	if err := validateBackupCreateOutput(keyPath, filepath.Join(root, "missing", "new.backup")); err == nil || err.Error() != "BACKUP_OUTPUT_PARENT_UNSAFE_OR_MISSING" {
		t.Fatalf("missing backup parent was accepted: %v", err)
	}
}
