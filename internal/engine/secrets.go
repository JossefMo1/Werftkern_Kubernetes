package engine

import (
	"context"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"io"
	"os"
	"path/filepath"
	"strings"
	"syscall"
)

const DefaultSecretRoot = "/run/werftkern/secrets"

type SecretSource func(context.Context, model.Allocation) (map[string][]byte, error)

func (d *Docker) secretRoot() string {
	if d.SecretRoot == "" {
		return DefaultSecretRoot
	}
	return d.SecretRoot
}

func ensureSecretRoot(root string) error {
	if !filepath.IsAbs(root) || filepath.Clean(root) != root || strings.ContainsAny(root, ":\n\r") {
		return errors.New("SECRET_ROOT_INVALID")
	}
	if e := os.MkdirAll(root, 0700); e != nil {
		return e
	}
	// A private leaf is not sufficient: an operator-provided parent such as
	// /run/werftkern-link/secrets could otherwise redirect secret staging to an
	// unrelated tree. Re-check the complete chain after MkdirAll.
	if e := noSymlinkPath(root); e != nil {
		return errors.New("SECRET_ROOT_NOT_PRIVATE")
	}
	st, e := os.Lstat(root)
	if e != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 || st.Mode().Perm() != 0700 {
		return errors.New("SECRET_ROOT_NOT_PRIVATE")
	}
	return nil
}

// secretDirectory materializes ONLY explicitly referenced immutable versions in
// a host tmpfs, before container creation/start. No plaintext enters its journal,
// container environment or labels. Parent 0700 prevents host-user traversal.
func (d *Docker) secretDirectory(ctx context.Context, a model.Allocation) (string, error) {
	if len(a.Spec.Secrets) == 0 {
		return "", nil
	}
	root := d.secretRoot()
	if !model.ValidID(a.ID) {
		return "", errors.New("SECRET_ROOT_INVALID")
	}
	if e := ensureSecretRoot(root); e != nil {
		return "", e
	}
	if d.RequireSecretTmpfs {
		var fs syscall.Statfs_t
		if e = syscall.Statfs(root, &fs); e != nil || uint64(fs.Type) != 0x01021994 {
			return "", errors.New("SECRET_ROOT_MUST_BE_TMPFS")
		}
	}
	dir := filepath.Join(root, a.ID)
	// A matching completed directory can be reused offline. Interrupted staging
	// directories are not accepted as evidence of a fully materialized secret set.
	if st, e := os.Lstat(dir); e == nil {
		if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return "", errors.New("SECRET_DIRECTORY_UNSAFE")
		}
		expectedManifest := model.Hash(a.Spec)
		manifest, e := safefile.OpenRead(filepath.Join(dir, ".manifest"))
		if e != nil {
			return "", errors.New("SECRET_MATERIAL_IDENTITY_MISMATCH")
		}
		manifestInfo, statErr := manifest.Stat()
		if statErr != nil || manifestInfo.Mode().Perm() != 0400 || manifestInfo.Size() != int64(len(expectedManifest)) {
			manifest.Close()
			return "", errors.New("SECRET_MATERIAL_IDENTITY_MISMATCH")
		}
		b, readErr := io.ReadAll(io.LimitReader(manifest, int64(len(expectedManifest)+1)))
		manifest.Close()
		if readErr != nil || len(b) != len(expectedManifest) || string(b) != expectedManifest {
			return "", errors.New("SECRET_MATERIAL_IDENTITY_MISMATCH")
		}
		names, e := os.ReadDir(dir)
		if e != nil || len(names) != len(a.Spec.Secrets)+1 {
			return "", errors.New("SECRET_DIRECTORY_CONTENT_MISMATCH")
		}
		for _, ref := range a.Spec.Secrets {
			st, e := os.Lstat(filepath.Join(dir, ref.Name))
			if e != nil || !st.Mode().IsRegular() || st.Mode().Perm() != 0444 {
				return "", errors.New("SECRET_FILE_UNSAFE")
			}
		}
		return dir, nil
	} else if !os.IsNotExist(e) {
		return "", e
	}
	if d.Secrets == nil {
		return "", errors.New("SECRET_SOURCE_NOT_CONFIGURED")
	}
	values, e := d.Secrets(ctx, a)
	if e != nil {
		return "", errors.New("AUTHORIZED_SECRET_FETCH_FAILED")
	}
	if len(values) != len(a.Spec.Secrets) {
		return "", errors.New("SECRET_SET_MISMATCH")
	}
	tmp, e := os.MkdirTemp(root, ".stage-")
	if e != nil {
		return "", e
	}
	defer os.RemoveAll(tmp)
	for _, ref := range a.Spec.Secrets {
		b, ok := values[ref.Name]
		if !ok || len(b) == 0 || len(b) > 4096 {
			return "", errors.New("SECRET_VALUE_INVALID")
		}
		if e = safefile.Write(filepath.Join(tmp, ref.Name), b, 0444); e != nil {
			return "", e
		}
	}
	if e = safefile.Write(filepath.Join(tmp, ".manifest"), []byte(model.Hash(a.Spec)), 0400); e != nil {
		return "", e
	}
	if e = os.Chmod(tmp, 0755); e != nil {
		return "", e
	}
	if e = os.Rename(tmp, dir); e != nil {
		return "", e
	}
	return dir, nil
}
func (d *Docker) removeSecrets(id string) error {
	if !model.ValidID(id) {
		return errors.New("SECRET_ALLOCATION_ID_INVALID")
	}
	root := d.secretRoot()
	if _, e := os.Lstat(root); os.IsNotExist(e) {
		return nil
	} else if e != nil {
		return e
	}
	if e := ensureSecretRoot(root); e != nil {
		return e
	}
	return os.RemoveAll(filepath.Join(root, id))
}
