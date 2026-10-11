// Package safefile provides crash-safe writes. The directory must be trusted.
package safefile

import (
	"encoding/json"
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/strictjson"
	"io"
	"os"
	"path/filepath"
)

func Write(path string, b []byte, mode os.FileMode) error {
	d := filepath.Dir(path)
	if err := os.MkdirAll(d, 0700); err != nil {
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
func ReadJSON(path string, v any) error {
	f, e := os.Open(path)
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
