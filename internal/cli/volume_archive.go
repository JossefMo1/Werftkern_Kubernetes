package cli

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/engine"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/setup"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/volumearchive"
)

type diskVolumeIdentity struct {
	ID        string `json:"id"`
	ClusterID string `json:"clusterId"`
	NodeID    string `json:"nodeId"`
	UID       int    `json:"uid"`
	GID       int    `json:"gid"`
}
type restoreDiskReceipt struct {
	OperationID string               `json:"operationId"`
	SHA256      string               `json:"sha256"`
	Identity    diskVolumeIdentity   `json:"identity"`
	Result      volumearchive.Result `json:"result"`
}

func volumeArchiveCommand(ctx context.Context, args []string) error {
	if e := setup.RequireRoot(); e != nil {
		return e
	}
	if len(args) < 2 {
		return errors.New("volume backup|restore NAME --key-file FILE --file ARCHIVE --maintenance-id ID [--operation-id ID]")
	}
	action, name := args[0], args[1]
	if !model.ValidName(name) {
		return errors.New("VOLUME_NAME_INVALID")
	}
	f := parser("volume " + action)
	agentPath := f.String("agent-config", config.Directory+"/agent.json", "This worker's node configuration")
	keyPath := f.String("key-file", "", "Separate 32-byte encryption key; auto-created for backup only")
	archive := f.String("file", "", "New backup, or input archive for restore")
	maintenance := f.String("maintenance-id", "", "Already held cluster maintenance ID")
	operation := f.String("operation-id", "", "Required stable restore operation ID; reuse when retrying")
	maxBytes := f.Int64("max-bytes", 10<<30, "Maximum unencrypted bytes (default 10 GiB)")
	if e := f.Parse(args[2:]); e != nil {
		return e
	}
	if f.NArg() != 0 || *keyPath == "" || *archive == "" || !model.ValidID(*maintenance) || (action == "restore" && !model.ValidID(*operation)) {
		return errors.New("VOLUME_ARCHIVE_ARGUMENTS_INVALID")
	}
	node, e := config.Load[config.Agent](*agentPath)
	if e != nil {
		return e
	}
	c, e := client()
	if e != nil {
		return e
	}
	root := node.VolumeRoot
	if root == "" {
		root = engine.DefaultVolumeRoot
	}
	root = filepath.Clean(root)
	if !filepath.IsAbs(root) {
		return errors.New("VOLUME_ROOT_NOT_ABSOLUTE")
	}
	for _, p := range []string{*keyPath, *archive} {
		abs, e := filepath.Abs(p)
		if e != nil {
			return e
		}
		parent, e := filepath.EvalSymlinks(filepath.Dir(abs))
		if e != nil {
			return e
		}
		abs = filepath.Join(parent, filepath.Base(abs))
		if abs == root || strings.HasPrefix(abs, root+"/") {
			return errors.New("BACKUP_AND_KEY_MUST_BE_OUTSIDE_VOLUME_ROOT")
		}
	}
	keyAbs, _ := filepath.Abs(*keyPath)
	archiveAbs, _ := filepath.Abs(*archive)
	if keyAbs == archiveAbs {
		return errors.New("SEPARATE_KEY_AND_ARCHIVE_REQUIRED")
	}
	ioLock, e := safefile.DirectoryLock(root, true)
	if e != nil {
		return e
	}
	defer ioLock.Close()
	s, e := c.State(ctx)
	if e != nil {
		return e
	}
	if s.ClusterID != node.Client.ClusterID {
		return errors.New("LOCAL_AND_ADMIN_CLUSTER_MISMATCH")
	}
	v, e := s.QuiescentVolume(name, node.NodeID, *maintenance)
	if e != nil {
		return e
	}
	target := filepath.Join(root, v.ID)
	data := filepath.Join(target, "data")
	docker := engine.NewDocker(node.Socket, s.ClusterID)
	if e = docker.AssertVolumeOffline(ctx, data); e != nil {
		return e
	}
	key, e := vault.LoadKey(*keyPath)
	if os.IsNotExist(e) && action == "backup" {
		key, e = vault.CreateKey(*keyPath)
	}
	if e != nil {
		return e
	}
	expected := diskVolumeIdentity{v.ID, s.ClusterID, v.NodeID, v.UID, v.GID}
	limits := volumearchive.Limits{Bytes: *maxBytes}
	if action == "backup" {
		if !v.Initialized || v.RestoreID != "" && !v.RestoreComplete {
			return errors.New("VOLUME_NOT_INITIALIZED_OR_RESTORE_PENDING")
		}
		var got diskVolumeIdentity
		if e = safefile.ReadJSON(filepath.Join(target, "identity.json"), &got); e != nil || got != expected {
			return errors.New("VOLUME_DISK_IDENTITY_MISMATCH")
		}
		out, e := os.OpenFile(*archive, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if e != nil {
			return e
		}
		complete := false
		defer func() {
			out.Close()
			if !complete {
				os.Remove(*archive)
			}
		}()
		hash := sha256.New()
		result, e := volumearchive.Export(ctx, data, io.MultiWriter(out, hash), key, volumearchive.Header{ClusterID: s.ClusterID, NodeID: v.NodeID, VolumeID: v.ID}, limits)
		if e != nil {
			return e
		}
		if e = out.Sync(); e != nil {
			return e
		}
		if e = out.Close(); e != nil {
			return e
		}
		if e = syncDir(filepath.Dir(archiveAbs)); e != nil {
			return e
		}
		complete = true
		return json.NewEncoder(os.Stdout).Encode(map[string]any{"result": result, "sha256": hex.EncodeToString(hash.Sum(nil)), "consistency": "offline-filesystem-copy-not-live-snapshot", "keyIncluded": false})
	}
	// Reserve the target before copying bytes. A crash now cannot cause the
	// runtime to initialize an empty replacement: Initialized is already true,
	// and RestoreComplete remains false until a durable receipt is acknowledged.
	in, e := os.OpenFile(*archive, os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if e != nil {
		return e
	}
	defer in.Close()
	st, e := in.Stat()
	if e != nil {
		return e
	}
	if !st.Mode().IsRegular() || st.Size() < 100 || st.Size() > *maxBytes+(256<<20) {
		return errors.New("VOLUME_ARCHIVE_FILE_SIZE_INVALID")
	}
	hash := sha256.New()
	if _, e = io.Copy(hash, in); e != nil {
		return e
	}
	digest := hex.EncodeToString(hash.Sum(nil))
	if _, e = in.Seek(0, io.SeekStart); e != nil {
		return e
	}
	q := control.VolumeRestoreRequest{ID: v.ID, MaintenanceID: *maintenance, OperationID: *operation, SHA256: digest}
	if e = c.Call(ctx, "POST", "/v1/volumes/"+name+"/restore", q, nil, *operation); e != nil {
		return e
	}
	var receipt restoreDiskReceipt
	if _, e = os.Lstat(target); e == nil {
		if e = safefile.ReadJSON(filepath.Join(target, "restore-receipt.json"), &receipt); e != nil || receipt.OperationID != *operation || receipt.SHA256 != digest || receipt.Identity != expected {
			return errors.New("RESTORE_TARGET_EXISTS_WITHOUT_MATCHING_RECEIPT")
		}
		var got diskVolumeIdentity
		if e = safefile.ReadJSON(filepath.Join(target, "identity.json"), &got); e != nil || got != expected {
			return errors.New("VOLUME_DISK_IDENTITY_MISMATCH")
		}
		ds, e := os.Lstat(data)
		if e != nil || !ds.IsDir() || ds.Mode()&os.ModeSymlink != 0 {
			return errors.New("RESTORED_DATA_MISSING")
		}
	} else if !os.IsNotExist(e) {
		return e
	} else {
		stage, e := os.MkdirTemp(root, ".restore-")
		if e != nil {
			return e
		}
		defer os.RemoveAll(stage)
		// Hash again while decrypting: an input modified between the first hash and
		// copy must not be acknowledged under the old archive identity.
		hash.Reset()
		result, e := volumearchive.Extract(ctx, io.TeeReader(in, hash), key, filepath.Join(stage, "data"), v.UID, v.GID, limits)
		if e != nil {
			return e
		}
		if hex.EncodeToString(hash.Sum(nil)) != digest {
			return errors.New("VOLUME_ARCHIVE_CHANGED_DURING_RESTORE")
		}
		receipt = restoreDiskReceipt{*operation, digest, expected, result}
		if e = safefile.JSON(filepath.Join(stage, "identity.json"), expected, 0600); e != nil {
			return e
		}
		if e = safefile.JSON(filepath.Join(stage, "restore-receipt.json"), receipt, 0600); e != nil {
			return e
		}
		// All cooperative engine/restore writers hold .io.lock; the parent is root
		// owned 0700. Never merge data into an existing destination.
		if _, e = os.Lstat(target); !os.IsNotExist(e) {
			return errors.New("RESTORE_TARGET_ALREADY_EXISTS")
		}
		if e = os.Rename(stage, target); e != nil {
			return e
		}
		if e = syncDir(root); e != nil {
			return e
		}
	}
	q.Complete = true
	if e = c.Call(ctx, "POST", "/v1/volumes/"+name+"/restore", q, nil, *operation); e != nil {
		return fmt.Errorf("DISK_RESTORED_API_ACK_PENDING_RETRY_SAME_OPERATION: %w", e)
	}
	return json.NewEncoder(os.Stdout).Encode(map[string]any{"operationId": *operation, "targetVolume": v.ID, "source": receipt.Result.Header, "sha256": digest, "applicationsRemainPaused": true})
}
func syncDir(p string) error {
	f, e := os.Open(p)
	if e != nil {
		return e
	}
	defer f.Close()
	return f.Sync()
}
