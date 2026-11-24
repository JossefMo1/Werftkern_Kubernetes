package cli

import (
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

