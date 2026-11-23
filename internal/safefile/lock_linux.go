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
	if !filepath.IsAbs(dir) || filepath.Clean(dir) != dir {
		return nil, errors.New("LOCK_DIRECTORY_MUST_BE_ABSOLUTE_AND_CLEAN")
	}
	// Validate existing parents before creation and again afterwards. This
	// prevents pre-existing symlink components from redirecting MkdirAll and
	// ensures newly-created components are checked before the lock is opened.
	if e := validateParentChain(filepath.Dir(dir)); e != nil && !errors.Is(e, os.ErrNotExist) {
		return nil, e
	}
	if e := os.MkdirAll(dir, 0700); e != nil {
		return nil, e
	}
	if e := validateParentChain(dir); e != nil {
		return nil, e
	}
	st, e := os.Lstat(dir)
	if e != nil {
		return nil, e
	}
	owner, ok := st.Sys().(*syscall.Stat_t)
	if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 || !ok {
		return nil, errors.New("LOCK_DIRECTORY_SYMLINK")
	}
	if st.Mode().Perm() != 0700 || owner.Uid != uint32(os.Geteuid()) {
		return nil, errors.New("LOCK_DIRECTORY_NOT_PRIVATE")
	}
	// Re-check parents immediately before opening the lock file and use
	// no-follow/close-on-exec for the final lock component.
	if e := validateParentChain(dir); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(filepath.Join(dir, ".io.lock"), os.O_RDWR|os.O_CREATE|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0600)
	if e != nil {
		return nil, e
	}
	fail := func(e error) (*os.File, error) { f.Close(); return nil, e }
	st, e = f.Stat()
	if e != nil {
		return fail(e)
	}
	lockOwner, ok := st.Sys().(*syscall.Stat_t)
	if !st.Mode().IsRegular() || st.Mode().Perm() != 0600 || !ok || lockOwner.Uid != uint32(os.Geteuid()) {
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
