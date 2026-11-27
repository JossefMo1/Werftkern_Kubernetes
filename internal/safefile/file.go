// Package safefile provides crash-safe writes. The directory must be trusted.
package safefile

import (
	"encoding/json"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/strictjson"
	"io"
	"os"
	"path/filepath"
	"syscall"
)

func validateParentChain(path string) error {
	for current := filepath.Clean(path); ; current = filepath.Dir(current) {
		info, err := os.Lstat(current)
		if err != nil {
			if !errors.Is(err, os.ErrNotExist) {
				return err
			}
			parent := filepath.Dir(current)
			if parent == current {
				return err
			}
			continue
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return errors.New("REFUSING_SYMLINK_PARENT")
		}
		if !info.IsDir() {
			return errors.New("PARENT_NOT_DIRECTORY")
		}
		parent := filepath.Dir(current)
		if parent == current {
			return nil
		}
	}
}

// ValidateCreateParent checks that an existing destination parent is a trusted directory.
// It performs no creation; CreateExclusive remains the race-safe final guard.
func ValidateCreateParent(path string) error {
	if path == "" {
		return errors.New("PATH_REQUIRED")
	}
	parent := filepath.Dir(path)
	info, err := os.Lstat(parent)
	if err != nil {
		return err
	}
	if !info.IsDir() {
		return errors.New("PARENT_NOT_DIRECTORY")
	}
	return validateParentChain(parent)
}

func openTrusted(path string) (*os.File, error) {
	if err := validateParentChain(filepath.Dir(path)); err != nil {
		return nil, err
	}
	fd, err := syscall.Open(path, syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if err != nil {
		return nil, err
	}
	f := os.NewFile(uintptr(fd), path)
	if f == nil {
		syscall.Close(fd)
		return nil, errors.New("FILE_OPEN_FAILED")
	}
	st, err := f.Stat()
	if err != nil {
		f.Close()
		return nil, err
	}
	if !st.Mode().IsRegular() {
		f.Close()
		return nil, errors.New("FILE_NOT_REGULAR")
	}
	return f, nil
}

// OpenRead opens a trusted regular file without following a final symlink. Parent components are validated as non-symlinks.
func OpenRead(path string) (*os.File, error) {
	return openTrusted(path)
}

// CreateExclusive creates a new regular file without following a final symlink.
// Existing parent components are checked for symlinks before the exclusive open.
// The caller owns the returned file and must close it.
func CreateExclusive(path string, mode os.FileMode) (*os.File, error) {
	if err := validateParentChain(filepath.Dir(path)); err != nil && !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	fd, err := syscall.Open(path, syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_CLOEXEC|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, uint32(mode.Perm()))
	if err != nil {
		return nil, err
	}
	f := os.NewFile(uintptr(fd), path)
	if f == nil {
		syscall.Close(fd)
		return nil, errors.New("FILE_OPEN_FAILED")
	}
	st, err := f.Stat()
	if err != nil {
		f.Close()
		return nil, err
	}
	if !st.Mode().IsRegular() {
		f.Close()
		return nil, errors.New("FILE_NOT_REGULAR")
	}
	if err := f.Chmod(mode); err != nil {
		f.Close()
		return nil, err
	}
	return f, nil
}

func Write(path string, b []byte, mode os.FileMode) error {
	d := filepath.Dir(path)
	// Check existing components before creating directories so a symlinked
	// parent cannot redirect the write into another tree.
	if err := validateParentChain(d); err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	if err := os.MkdirAll(d, 0700); err != nil {
		return err
	}
	// Re-check after MkdirAll so newly-created components are covered too.
	if err := validateParentChain(d); err != nil {
		return err
	}
	if i, e := os.Lstat(path); e == nil && i.Mode()&os.ModeSymlink != 0 {
		return errors.New("REFUSING_SYMLINK")
	}
	f, e := os.CreateTemp(d, ".write-*")
	if e != nil {
		return e
	}
	tmp := f.Name()
	defer os.Remove(tmp)
	if e = f.Chmod(mode); e != nil {
		f.Close()
		return e
	}
	if _, e = f.Write(b); e != nil {
		f.Close()
		return e
	}
	if e = f.Sync(); e != nil {
		f.Close()
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	if e = os.Rename(tmp, path); e != nil {
		return e
	}
	dir, e := os.Open(d)
	if e != nil {
		return e
	}
	defer dir.Close()
	return dir.Sync()
}
func JSON(path string, v any, mode os.FileMode) error {
	b, e := json.MarshalIndent(v, "", "  ")
	if e != nil {
		return e
	}
	return Write(path, append(b, '\n'), mode)
}
// JSONExclusive creates a private JSON file without replacing an existing destination.
// It is intended for credentials and other first-write-only artifacts.
func JSONExclusive(path string, v any, mode os.FileMode) (err error) {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	d := filepath.Dir(path)
	if err = validateParentChain(d); err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	if err = os.MkdirAll(d, 0700); err != nil {
		return err
	}
	if err = validateParentChain(d); err != nil {
		return err
	}
	f, err := CreateExclusive(path, mode)
	if err != nil {
		return err
	}
	closed := false
	cleanup := true
	defer func() {
		if cleanup {
			if !closed {
				_ = f.Close()
			}
			_ = os.Remove(path)
		}
	}()
	if _, err = f.Write(append(b, '\n')); err != nil {
		return err
	}
	if err = f.Sync(); err != nil {
		return err
	}
	if err = f.Close(); err != nil {
		closed = true
		return err
	}
	closed = true
	dir, err := os.Open(d)
	if err != nil {
		return err
	}
	if err = dir.Sync(); err != nil {
		_ = dir.Close()
		return err
	}
	if err = dir.Close(); err != nil {
		return err
	}
	cleanup = false
	return nil
}

func ReadJSON(path string, v any) error {
	f, e := openTrusted(path)
	if e != nil {
		return e
	}
	defer f.Close()
	raw, e := io.ReadAll(io.LimitReader(f, (4<<20)+1))
	if e != nil {
		return e
	}
	if len(raw) > 4<<20 {
		return errors.New("JSON_FILE_TOO_LARGE")
	}
	return strictjson.Unmarshal(raw, v)
}
