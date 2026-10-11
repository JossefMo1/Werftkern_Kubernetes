package cli

import (
	"context"
	"errors"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/failover"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/pki"
	"github.com/ClusterPilot-System/werftkern/internal/recovery"
	"github.com/ClusterPilot-System/werftkern/internal/setup"
	"github.com/ClusterPilot-System/werftkern/internal/store"
	"github.com/ClusterPilot-System/werftkern/internal/vault"
	"os"
	"path/filepath"
	"time"
)

func backupCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("backup create|inspect|restore --key-file KEY --out FILE / --file FILE")
	}
	if e := setup.RequireRoot(); e != nil {
		return e
	}
	f := parser("backup")
	keyPath := f.String("key-file", "", "Separate random key file")
	out := f.String("out", "", "New encrypted backup")
	in := f.String("file", "", "Encrypted backup")
	mappingPath := f.String("mapping", "", "Explicit node and volume mapping for stateful restore")
	target := f.String("target-cluster", "", "Explicit new target identity")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	if *keyPath == "" {
		return errors.New("SEPARATE_KEY_FILE_REQUIRED")
	}
	if args[0] != "create" && args[0] != "inspect" && args[0] != "restore" {
		return errors.New("BACKUP_ACTION_INVALID")
	}
	key, e := vault.LoadKey(*keyPath)
	if os.IsNotExist(e) && args[0] == "create" {
		key, e = vault.CreateKey(*keyPath)
	}
	if e != nil {
		return e
	}
	if args[0] == "inspect" || args[0] == "restore" {
		st, e := os.Stat(*in)
		if e != nil {
			return e
		}
		if !st.Mode().IsRegular() || st.Size() > 3*vault.MaxPlaintext {
			return errors.New("BACKUP_TOO_LARGE")
		}
		b, e := os.ReadFile(*in)
		if e != nil {
			return e
		}
		snap, e := recovery.Open(b, key)
		if e != nil {
			return e
		}
		if args[0] == "inspect" {
			fmt.Printf("sourceCluster=%s revision=%d createdAt=%s workloads=%d secretVersions=%d\n", snap.State.ClusterID, snap.Revision, snap.CreatedAt.Format(time.RFC3339), len(snap.State.Workloads), len(snap.State.Secrets))
			return nil
		}
		cc, db, master, e := localStore()
		if e != nil {
			return e
		}
		if *target != cc.Client.ClusterID {
			return errors.New("EXPLICIT_TARGET_CLUSTER_CONFIRMATION_REQUIRED")
		}
		// Snapshot mappings once; concurrent CAS retries must not re-read a changing file.
		var mapping recovery.RestoreMapping
		if *mappingPath != "" {
			mapping, e = config.Load[recovery.RestoreMapping](*mappingPath)
			if e != nil {
				return e
			}
		}
		_, _, e = db.Update(ctx, func(s *model.State) error {
			next, e := recovery.PrepareRestoreMapped(snap, s, master, time.Now().UTC(), mapping)
			if e != nil {
				return e
			}
			*s = *next
			return nil
		})
		if e == nil {
			fmt.Println("Configuration restored PAUSED. Old nodes, allocations and certificates were not restored. Review source fencing and node selectors before werft resume NAME.")
		}
		return e
	}
	if *out == "" || filepath.Clean(*out) == filepath.Clean(*keyPath) {
		return errors.New("DISTINCT_OUTPUT_AND_KEY_PATH_REQUIRED")
	}
	if _, e = os.Lstat(*out); !os.IsNotExist(e) {
		return errors.New("BACKUP_OUTPUT_ALREADY_EXISTS")
	}
	_, db, master, e := localStore()
	if e != nil {
		return e
	}
	s, rev, e := db.Read(ctx)
	if e != nil {
		return e
	}
	b, e := recovery.Seal(s, rev, master, key, time.Now().UTC())
	if e != nil {
		return e
	}
	// Exclusive output creation; never overwrite a prior backup.
	h, e := os.OpenFile(*out, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		return e
	}
	ok := false
	defer func() {
		h.Close()
		if !ok {
			os.Remove(*out)
		}
	}()
	if _, e = h.Write(b); e != nil {
		return e
	}
	if e = h.Sync(); e != nil {
		return e
	}
	ok = true
	fmt.Println("Encrypted logical configuration backup created. Keep its key separately. Does NOT include host PKI, images or application data.")
	return nil
}
func localStore() (config.Control, *store.Etcd, []byte, error) {
	cc, e := config.Load[config.Control](config.Directory + "/control.json")
	if e != nil {
		return cc, nil, nil, e
	}
	if cc.VaultKey == "" {
		cc.VaultKey = cc.DataDir + "/vault.key"
	}
	key, e := vault.LoadKey(cc.VaultKey)
	if e != nil {
		return cc, nil, nil, e
	}
	c, e := pki.ClientFiles(cc.Etcd.CA, cc.Etcd.Cert, cc.Etcd.Key)
	if e != nil {
		return cc, nil, nil, e
	}
	if len(cc.Etcd.Servers) > 0 {
		tr, err := failover.New(c.Transport, cc.Etcd.Servers)
		if err != nil {
			return cc, nil, nil, err
		}
		c.Transport = tr
	}
	return cc, store.NewEtcd(cc.Etcd.Server, c, cc.Client.ClusterID), key, nil
}
