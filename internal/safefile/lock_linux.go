package safefile

import (
	"errors"
	"os"
	"path/filepath"
	"syscall"
)

// DirectoryLock coordinates container starts and offline volume maintenance.
// The protected directory is private and owned by this service identity. A host
// administrator remains trusted; flock is not a defense against malicious root.
func DirectoryLock(dir string, exclusive bool) (*os.File, error) {
	if !filepath.IsAbs(dir) {
		return nil, errors.New("LOCK_DIRECTORY_MUST_BE_ABSOLUTE")
	}
	if e := os.MkdirAll(dir, 0700); e != nil {
		return nil, e
	}
	for p := filepath.Clean(dir); ; p = filepath.Dir(p) {
		st, e := os.Lstat(p)
		if e != nil {
			return nil, e
		}
		if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return nil, errors.New("LOCK_DIRECTORY_SYMLINK")
		}
		if p == "/" {
			break
		}
	}
	st, e := os.Stat(dir)
	if e != nil {
		return nil, e
	}
	if st.Mode().Perm() != 0700 || st.Sys().(*syscall.Stat_t).Uid != uint32(os.Geteuid()) {
		return nil, errors.New("LOCK_DIRECTORY_NOT_PRIVATE")
	}
	f, e := os.OpenFile(filepath.Join(dir, ".io.lock"), os.O_RDWR|os.O_CREATE|syscall.O_NOFOLLOW, 0600)
	if e != nil {
		return nil, e
	}
	fail := func(e error) (*os.File, error) { f.Close(); return nil, e }
	st, e = f.Stat()
	if e != nil {
		return fail(e)
	}
	if !st.Mode().IsRegular() || st.Mode().Perm() != 0600 || st.Sys().(*syscall.Stat_t).Uid != uint32(os.Geteuid()) {
		return fail(errors.New("LOCK_FILE_UNSAFE"))
	}
	op := syscall.LOCK_SH
	if exclusive {
		op = syscall.LOCK_EX
	}
	if e = syscall.Flock(int(f.Fd()), op|syscall.LOCK_NB); e != nil {
		return fail(errors.New("VOLUME_IO_BUSY"))
	}
	return f, nil
}
