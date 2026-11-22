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
