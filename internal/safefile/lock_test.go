package safefile

import (
	"os"
	"path/filepath"
	"testing"
)

func TestVolumeIOLockExcludesMaintenanceAndStart(t *testing.T) {
	p := t.TempDir()
	os.Chmod(p, 0700)
	a, e := DirectoryLock(p, false)
	if e != nil {
		t.Fatal(e)
	}
	b, e := DirectoryLock(p, false)
	if e != nil {
		t.Fatal(e)
	}
	if c, e := DirectoryLock(p, true); e == nil {
		c.Close()
		t.Fatal("exclusive lock ignored readers")
	}
	a.Close()
	b.Close()
	c, e := DirectoryLock(p, true)
	if e != nil {
		t.Fatal(e)
	}
	defer c.Close()
	if d, e := DirectoryLock(p, false); e == nil {
		d.Close()
		t.Fatal("start allowed during maintenance")
	}
}
func TestVolumeIOLockRejectsSymlinkAndPublicRoot(t *testing.T) {
	p := t.TempDir()
	os.Chmod(p, 0755)
	if f, e := DirectoryLock(p, true); e == nil {
		f.Close()
		t.Fatal("public root")
	}
	os.Chmod(p, 0700)
	os.Symlink(filepath.Join(t.TempDir(), "target"), filepath.Join(p, ".io.lock"))
	if f, e := DirectoryLock(p, true); e == nil {
		f.Close()
		t.Fatal("lock symlink")
	}
}
