package volumearchive

import (
	"archive/tar"
	"context"
	"errors"
	"io"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"
)

type Limits struct {
	Bytes int64
	Files int
	Depth int
}

func (l Limits) normalized() (Limits, error) {
	if l.Bytes == 0 {
		l.Bytes = 10 << 30
	}
	if l.Files == 0 {
		l.Files = 100000
	}
	if l.Depth == 0 {
		l.Depth = 64
	}
	if l.Bytes < 1 || l.Bytes > 1<<40 || l.Files < 1 || l.Files > 1000000 || l.Depth < 1 || l.Depth > 128 {
		return l, errors.New("VOLUME_ARCHIVE_LIMITS_INVALID")
	}
	return l, nil
}

type Result struct {
	Header Header `json:"header"`
	Bytes  int64  `json:"dataBytes"`
	Files  int    `json:"entries"`
}

// Export reads regular, single-link files from an already quiesced directory.
// Descriptor-relative O_NOFOLLOW traversal refuses symlinks, mounted devices,
// sockets and other special files. It never invokes tar or a shell.
func Export(ctx context.Context, dir string, dst io.Writer, key []byte, h Header, limits Limits) (Result, error) {
	var out Result
	l, e := limits.normalized()
	if e != nil {
		return out, e
	}
	fd, e := syscall.Open(dir, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if e != nil {
		return out, e
	}
	root := os.NewFile(uintptr(fd), dir)
	defer root.Close()
	st, e := root.Stat()
	if e != nil {
		return out, e
	}
	dev := st.Sys().(*syscall.Stat_t).Dev
	fw, h, e := newWriter(dst, key, h)
	if e != nil {
		return out, e
	}
	out.Header = h
	tw := tar.NewWriter(fw)
	discovered := 0
	var walk func(*os.File, string, int) error
	walk = func(parent *os.File, prefix string, depth int) error {
		if e := ctx.Err(); e != nil {
			return e
		}
		if depth > l.Depth {
			return errors.New("VOLUME_ARCHIVE_DEPTH_LIMIT")
		}
		entries := []os.DirEntry{}
		for {
			batch, e := parent.ReadDir(1024)
			discovered += len(batch)
			if discovered > l.Files {
				return errors.New("VOLUME_ARCHIVE_FILE_LIMIT")
			}
			entries = append(entries, batch...)
			if e == io.EOF {
				break
			}
			if e != nil {
				return e
			}
		}
		sort.Slice(entries, func(i, j int) bool { return entries[i].Name() < entries[j].Name() })
		for _, entry := range entries {
			if e := ctx.Err(); e != nil {
				return e
			}
			name := entry.Name()
			if !safeName(name) || strings.Contains(name, "/") {
				return errors.New("VOLUME_ARCHIVE_NAME_INVALID")
			}
			// NONBLOCK ensures a hostile FIFO cannot block before fstat rejects it.
			childFD, e := syscall.Openat(int(parent.Fd()), name, syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK|syscall.O_CLOEXEC, 0)
			if e != nil {
				return errors.New("VOLUME_ARCHIVE_ENTRY_UNSAFE")
			}
			child := os.NewFile(uintptr(childFD), name)
			e = func() error {
				defer child.Close()
				info, e := child.Stat()
				if e != nil {
					return e
				}
				stat := info.Sys().(*syscall.Stat_t)
				if stat.Dev != dev || (!info.IsDir() && !info.Mode().IsRegular()) || info.Mode().IsRegular() && stat.Nlink != 1 {
					return errors.New("VOLUME_ARCHIVE_SPECIAL_OR_LINKED_ENTRY")
				}
				out.Files++
				if out.Files > l.Files {
					return errors.New("VOLUME_ARCHIVE_FILE_LIMIT")
				}
				full := path.Join(prefix, name)
				if strings.Count(full, "/") >= l.Depth {
					return errors.New("VOLUME_ARCHIVE_DEPTH_LIMIT")
				}
				if len(full) > 4096 {
					return errors.New("VOLUME_ARCHIVE_PATH_LIMIT")
				}
				header, e := tar.FileInfoHeader(info, "")
				if e != nil {
					return e
				}
				header.Format = tar.FormatUSTAR
				header.ModTime = header.ModTime.Truncate(time.Second)
				header.AccessTime = time.Time{}
				header.ChangeTime = time.Time{}
				header.Name = full
				header.Uid = 0
				header.Gid = 0
				header.Uname = ""
				header.Gname = ""
				header.Mode = int64(info.Mode().Perm() & 0777)
				if info.IsDir() {
					header.Mode |= 0700
				} else {
					header.Mode |= 0600
				}
				if !info.IsDir() {
					if info.Size() > l.Bytes-out.Bytes {
						return errors.New("VOLUME_ARCHIVE_BYTE_LIMIT")
					}
					out.Bytes += info.Size()
				}
				if e = tw.WriteHeader(header); e != nil {
					return e
				}
				if info.IsDir() {
					return walk(child, full, depth+1)
				}
				if _, e = io.CopyN(tw, &contextReader{ctx, child}, info.Size()); e != nil {
					return e
				}
				after, e := child.Stat()
				if e != nil {
					return e
				}
				if after.Size() != info.Size() || !after.ModTime().Equal(info.ModTime()) {
					return errors.New("VOLUME_CHANGED_DURING_BACKUP")
				}
				return nil
			}()
			if e != nil {
				return e
			}
		}
		return nil
	}
	if e = walk(root, "", 0); e != nil {
		return out, e
	}
	if e = tw.Close(); e != nil {
		return out, e
	}
	if e = fw.Close(); e != nil {
		return out, e
	}
	return out, nil
}

type contextReader struct {
	ctx    context.Context
	reader io.Reader
}

func (r *contextReader) Read(p []byte) (int, error) {
	if e := r.ctx.Err(); e != nil {
		return 0, e
	}
	return r.reader.Read(p)
}
func safeName(name string) bool {
	if name == "" || len(name) > 4096 || path.IsAbs(name) || path.Clean(name) != name || name == "." || strings.HasPrefix(name, "../") || name == ".." || strings.ContainsAny(name, "\\\x00\r\n") {
		return false
	}
	for _, c := range name {
		if c < 32 || c == 127 {
			return false
		}
	}
	return true
}

// Extract creates a NEW destination. On any integrity, size or path failure it
// removes that destination. The caller must keep it inaccessible until success.
// UID/GID from an archive are never trusted: the target volume controls ownership.
func Extract(ctx context.Context, src io.Reader, key []byte, destination string, uid, gid int, limits Limits) (out Result, err error) {
	l, e := limits.normalized()
	if e != nil {
		return out, e
	}
	if uid < 1 || uid > 65534 || gid < 1 || gid > 65534 {
		return out, errors.New("VOLUME_TARGET_USER_INVALID")
	}
	fr, h, e := newReader(src, key)
	if e != nil {
		return out, e
	}
	out.Header = h
	if e = os.Mkdir(destination, 0700); e != nil {
		return out, e
	}
	success := false
	defer func() {
		if !success {
			os.RemoveAll(destination)
		}
	}()
	// The caller owns the parent; no attacker-controlled concurrent tree mutation is allowed.
	tr := tar.NewReader(&contextReader{ctx, fr})
	seen := map[string]bool{}
	for {
		header, e := tr.Next()
		if e == io.EOF {
			break
		}
		if e != nil {
			return out, e
		}
		if e = ctx.Err(); e != nil {
			return out, e
		}
		name := header.Name
		if !safeName(name) || seen[name] || strings.Count(name, "/") >= l.Depth || header.Size < 0 || (header.Typeflag != tar.TypeReg && header.Typeflag != tar.TypeDir) || len(header.PAXRecords) > 0 || header.Linkname != "" {
			return out, errors.New("VOLUME_ARCHIVE_TAR_ENTRY_INVALID")
		}
		seen[name] = true
		out.Files++
		if out.Files > l.Files || header.Size > l.Bytes-out.Bytes {
			return out, errors.New("VOLUME_ARCHIVE_LIMIT_EXCEEDED")
		}
		out.Bytes += header.Size
		parent := path.Dir(name)
		if parent != "." && !seen[parent] {
			return out, errors.New("VOLUME_ARCHIVE_PARENT_NOT_DECLARED")
		}
		dest := filepath.Join(destination, filepath.FromSlash(name))
		mode := os.FileMode(header.Mode) & 0777
		if header.Typeflag == tar.TypeDir {
			if header.Size != 0 {
				return out, errors.New("VOLUME_ARCHIVE_DIRECTORY_SIZE_INVALID")
			}
			if e = os.Mkdir(dest, mode|0700); e != nil {
				return out, e
			}
			continue
		}
		f, e := os.OpenFile(dest, os.O_WRONLY|os.O_CREATE|os.O_EXCL, mode|0600)
		if e != nil {
			return out, e
		}
		_, copyErr := io.CopyN(f, &contextReader{ctx, tr}, header.Size)
		syncErr := f.Sync()
		closeErr := f.Close()
		if copyErr != nil {
			return out, copyErr
		}
		if syncErr != nil {
			return out, syncErr
		}
		if closeErr != nil {
			return out, closeErr
		}
	}
	// tar's EOF alone is insufficient: authenticate the framing terminator and
	// reject any non-padding plaintext/trailing ciphertext after the tar stream.
	padding := make([]byte, 8192)
	remaining := 1 << 20
	for {
		n, e := fr.Read(padding)
		remaining -= n
		if remaining < 0 {
			return out, errors.New("VOLUME_ARCHIVE_PADDING_LIMIT")
		}
		for _, b := range padding[:n] {
			if b != 0 {
				return out, errors.New("VOLUME_ARCHIVE_TRAILING_PLAINTEXT")
			}
		}
		if e == io.EOF {
			break
		}
		if e != nil {
			return out, e
		}
	}
	if !fr.end {
		return out, errors.New("VOLUME_ARCHIVE_INCOMPLETE")
	}
	// All integrity checks passed. Ownership is assigned only to the new tree.
	e = filepath.WalkDir(destination, func(p string, d os.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if e = os.Chown(p, uid, gid); e != nil {
			return e
		}
		f, e := os.Open(p)
		if e != nil {
			return e
		}
		defer f.Close()
		return f.Sync()
	})
	if e != nil {
		return out, e
	}
	success = true
	return out, nil
}
