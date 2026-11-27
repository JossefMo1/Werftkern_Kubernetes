package safefile

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAtomicPrivateWrite(t *testing.T) {
	p := filepath.Join(t.TempDir(), "sub", "file")
	if e := Write(p, []byte("first"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := Write(p, []byte("second"), 0600); e != nil {
		t.Fatal(e)
	}
	b, _ := os.ReadFile(p)
	i, _ := os.Stat(p)
	if string(b) != "second" || i.Mode().Perm() != 0600 {
		t.Fatal(string(b), i.Mode())
	}
	files, _ := os.ReadDir(filepath.Dir(p))
	if len(files) != 1 {
		t.Fatal("left staging file")
	}
}
func TestRefusesDestinationSymlink(t *testing.T) {
	d := t.TempDir()
	target := filepath.Join(d, "target")
	os.WriteFile(target, []byte("untouched"), 0600)
	link := filepath.Join(d, "link")
	os.Symlink(target, link)
	if Write(link, []byte("bad"), 0600) == nil {
		t.Fatal("followed link")
	}
	b, _ := os.ReadFile(target)
	if string(b) != "untouched" {
		t.Fatal("target changed")
	}
}
func TestRefusesParentSymlink(t *testing.T) {
	d := t.TempDir()
	real := filepath.Join(d, "real")
	if err := os.Mkdir(real, 0700); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(d, "link")
	if err := os.Symlink(real, link); err != nil {
		t.Fatal(err)
	}
	if err := Write(filepath.Join(link, "file"), []byte("bad"), 0600); err == nil {
		t.Fatal("followed parent symlink")
	}
	if _, err := os.Stat(filepath.Join(real, "file")); !os.IsNotExist(err) {
		t.Fatal("real target changed")
	}
}
func TestReadJSONRefusesSymlinkedPaths(t *testing.T) {
	d := t.TempDir()
	real := filepath.Join(d, "real")
	if err := os.Mkdir(real, 0700); err != nil {
		t.Fatal(err)
	}
	file := filepath.Join(real, "config.json")
	if err := os.WriteFile(file, []byte(`{"value":1}`), 0600); err != nil {
		t.Fatal(err)
	}
	type config struct {
		Value int `json:"value"`
	}
	var got config
	if err := ReadJSON(file, &got); err != nil || got.Value != 1 {
		t.Fatalf("valid file rejected: %v", err)
	}
	link := filepath.Join(d, "config-link.json")
	if err := os.Symlink(file, link); err != nil {
		t.Fatal(err)
	}
	if err := ReadJSON(link, &got); err == nil {
		t.Fatal("followed destination symlink")
	}
	parentLink := filepath.Join(d, "parent-link")
	if err := os.Symlink(real, parentLink); err != nil {
		t.Fatal(err)
	}
	if err := ReadJSON(filepath.Join(parentLink, "config.json"), &got); err == nil {
		t.Fatal("followed parent symlink")
	}
}
func TestStrictJSON(t *testing.T) {
	for _, raw := range []string{`{"value":1,"unknown":1}`, `{"value":1} {}`, `{"value":`, strings.Repeat(" ", 4<<20) + `{}`} {
		p := filepath.Join(t.TempDir(), "a")
		os.WriteFile(p, []byte(raw), 0600)
		var v struct {
			Value int `json:"value"`
		}
		if ReadJSON(p, &v) == nil {
			t.Fatal("invalid JSON accepted")
		}
	}
}

func TestExclusiveCreateRefusesSymlinks(t *testing.T) {
	d := t.TempDir()
	path := filepath.Join(d, "key")
	f, err := CreateExclusive(path, 0600)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = f.Write([]byte("key")); err != nil {
		t.Fatal(err)
	}
	if err = f.Close(); err != nil {
		t.Fatal(err)
	}
	st, err := os.Stat(path)
	if err != nil || st.Mode().Perm() != 0600 {
		t.Fatalf("created file invalid: %v %v", err, st)
	}
	if _, err = CreateExclusive(path, 0600); err == nil {
		t.Fatal("overwrote existing file")
	}
	target := filepath.Join(d, "target")
	if err = os.WriteFile(target, []byte("untouched"), 0600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(d, "link")
	if err = os.Symlink(target, link); err != nil {
		t.Fatal(err)
	}
	if _, err = CreateExclusive(link, 0600); err == nil {
		t.Fatal("followed destination symlink")
	}
	real := filepath.Join(d, "real")
	if err = os.Mkdir(real, 0700); err != nil {
		t.Fatal(err)
	}
	parentLink := filepath.Join(d, "parent-link")
	if err = os.Symlink(real, parentLink); err != nil {
		t.Fatal(err)
	}
	if _, err = CreateExclusive(filepath.Join(parentLink, "nested"), 0600); err == nil {
		t.Fatal("followed parent symlink")
	}
}

func TestValidateCreateParent(t *testing.T) {
	root := t.TempDir()
	realDir := filepath.Join(root, "real")
	if err := os.Mkdir(realDir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := ValidateCreateParent(filepath.Join(realDir, "new")); err != nil {
		t.Fatalf("trusted parent rejected: %v", err)
	}
	if err := ValidateCreateParent(filepath.Join(root, "missing", "new")); !os.IsNotExist(err) {
		t.Fatalf("missing parent error = %v, want os.ErrNotExist", err)
	}
	parentLink := filepath.Join(root, "parent-link")
	if err := os.Symlink(realDir, parentLink); err != nil {
		t.Fatal(err)
	}
	if err := ValidateCreateParent(filepath.Join(parentLink, "new")); err == nil {
		t.Fatal("accepted symlinked parent")
	}
}

func TestJSONExclusiveDoesNotReplaceExistingDestination(t *testing.T) {
	d := t.TempDir()
	path := filepath.Join(d, "nested", "bundle.json")
	if err := JSONExclusive(path, map[string]string{"value": "first"}, 0600); err != nil {
		t.Fatal(err)
	}
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil || info.Mode().Perm() != 0600 {
		t.Fatalf("exclusive JSON file invalid: %v", err)
	}
	if err := JSONExclusive(path, map[string]string{"value": "second"}, 0600); err == nil {
		t.Fatal("replaced existing destination")
	}
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(after) != string(before) {
		t.Fatal("existing destination changed")
	}
	link := filepath.Join(d, "bundle-link.json")
	if err := os.Symlink(path, link); err != nil {
		t.Fatal(err)
	}
	if err := JSONExclusive(link, map[string]string{"value": "link"}, 0600); err == nil {
		t.Fatal("followed destination symlink")
	}
}
