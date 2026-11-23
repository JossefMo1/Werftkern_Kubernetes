package cli

import (
	"os"
	"path/filepath"
	"testing"
)

func TestReadReleaseInputRejectsSymlinkedInputs(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "manifest")
	if err := os.WriteFile(target, []byte("signed-manifest"), 0600); err != nil {
		t.Fatal(err)
	}
	finalLink := filepath.Join(root, "manifest-link")
	if err := os.Symlink(target, finalLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readReleaseInput(finalLink, 1024); err == nil {
		t.Fatal("accepted final symlink for release input")
	}

	targetDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(targetDir, "manifest"), []byte("signed-manifest"), 0600); err != nil {
		t.Fatal(err)
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(targetDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readReleaseInput(filepath.Join(parentLink, "manifest"), 1024); err == nil {
		t.Fatal("accepted symlinked parent for release input")
	}
}

func TestReadReleaseInputEnforcesSizeAfterOpen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "input")
	if err := os.WriteFile(path, []byte("12345"), 0600); err != nil {
		t.Fatal(err)
	}
	got, err := readReleaseInput(path, 5)
	if err != nil || string(got) != "12345" {
		t.Fatalf("read exact limit: got %q, err %v", got, err)
	}
	if _, err := readReleaseInput(path, 4); err == nil {
		t.Fatal("accepted oversized release input")
	}
}
