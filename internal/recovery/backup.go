// Package recovery implements encrypted logical configuration backups. It does
// NOT snapshot disks or restore running allocations, member keys or host PKI.
package recovery

import (
	"encoding/json"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/strictjson"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"time"
)

const Format = "clusterpilot-config-backup/v1"
const aad = "clusterpilot/encrypted-configuration-backup/v1"

type Snapshot struct {
	Format    string       `json:"format"`
	CreatedAt time.Time    `json:"createdAt"`
	Revision  int64        `json:"revision"`
	State     *model.State `json:"state"`
	VaultKey  []byte       `json:"vaultKey"`
}
type envelope struct {
	Format string `json:"format"`
	Sealed string `json:"sealed"`
}

func strict(b []byte, v any) error {
	return strictjson.Unmarshal(b, v)
}
func Seal(s *model.State, revision int64, master, key []byte, now time.Time) ([]byte, error) {
	if revision < 1 {
		return nil, errors.New("BACKUP_REVISION_INVALID")
	}
	if e := s.ValidateInventory(); e != nil {
		return nil, e
	}
	if _, e := vault.New(master); e != nil {
		return nil, e
	}
	v, e := vault.New(key)
	if e != nil {
		return nil, e
	}
	b, e := json.Marshal(Snapshot{Format, now.UTC(), revision, s, master})
	if e != nil {
		return nil, e
	}
	sealed, e := v.Seal(b, aad)
	if e != nil {
		return nil, e
	}
	return json.Marshal(envelope{Format, sealed})
}
func Open(b, key []byte) (Snapshot, error) {
	var out Snapshot
	var env envelope
	if len(b) > 3*vault.MaxPlaintext {
		return out, errors.New("BACKUP_TOO_LARGE")
	}
	if e := strict(b, &env); e != nil || env.Format != Format {
		return out, errors.New("BACKUP_FORMAT_INVALID")
	}
	v, e := vault.New(key)
	if e != nil {
		return out, e
	}
	raw, e := v.Open(env.Sealed, aad)
	if e != nil {
		return out, e
	}
	if e = strict(raw, &out); e != nil || out.Format != Format || out.State == nil || out.Revision < 1 || out.CreatedAt.IsZero() {
		return Snapshot{}, errors.New("BACKUP_PAYLOAD_INVALID")
	}
	if e = out.State.ValidateInventory(); e != nil {
		return Snapshot{}, e
	}
	source, e := vault.New(out.VaultKey)
	if e != nil {
		return Snapshot{}, e
	}
	for _, sec := range out.State.Secrets {
		ref := model.SecretRef{Name: sec.Name, Version: sec.Version}
		if _, e = source.Open(sec.Sealed, model.SecretAAD(out.State.ClusterID, ref)); e != nil {
			return Snapshot{}, errors.New("BACKUP_SECRET_INTEGRITY_FAILED")
		}
	}
	return out, nil
}

// PrepareRestore creates new workload identities and PAUSES every restored spec.
// Nodes/allocations/receipts from the source are NEVER reactivated. A different
// target cluster identity and empty workload namespace are mandatory.
func PrepareRestore(b Snapshot, target *model.State, targetKey []byte, now time.Time) (*model.State, error) {
	return PrepareRestoreMapped(b, target, targetKey, now, RestoreMapping{})
}
func PrepareRestoreMapped(b Snapshot, target *model.State, targetKey []byte, now time.Time, mapping RestoreMapping) (*model.State, error) {
	if b.Format != Format || b.Revision < 1 || b.CreatedAt.IsZero() || target == nil || b.State == nil {
		return nil, errors.New("RESTORE_SNAPSHOT_INVALID")
	}
	if e := target.ValidateInventory(); e != nil {
		return nil, e
	}
	if b.State.ClusterID == target.ClusterID {
		return nil, errors.New("RESTORE_REQUIRES_A_NEW_CLUSTER_IDENTITY")
	}
	if len(target.Workloads) > 0 || len(target.Allocations) > 0 || len(target.Secrets) > 0 {
		return nil, errors.New("RESTORE_TARGET_NOT_EMPTY")
	}
	if e := b.State.ValidateInventory(); e != nil {
		return nil, e
	}
	from, e := vault.New(b.VaultKey)
	if e != nil {
		return nil, e
	}
	to, e := vault.New(targetKey)
	if e != nil {
		return nil, e
	}
	raw, _ := json.Marshal(target)
	var restored model.State
	if e = json.Unmarshal(raw, &restored); e != nil {
		return nil, e
	}
	restored.Secrets = map[string]model.SecretVersion{}
	for key, sec := range b.State.Secrets {
		ref := model.SecretRef{Name: sec.Name, Version: sec.Version}
		plain, e := from.Open(sec.Sealed, model.SecretAAD(b.State.ClusterID, ref))
		if e != nil {
			return nil, e
		}
		sec.Sealed, e = to.Seal(plain, model.SecretAAD(target.ClusterID, ref))
		if e != nil {
			return nil, e
		}
		restored.Secrets[key] = sec
	}
	for name, w := range b.State.Workloads {
		if w.Deleting {
			continue
		}
		rw := *w
		rw.Spec, e = mapSpec(w.Spec, &restored, mapping)
		if e != nil {
			return nil, e
		}
		rw.History = nil // Old storage/node mappings are not silently resurrected by rollback.
		rw.UID = model.ID()
		for _, ref := range rw.Spec.Volumes {
			restored.Volumes[ref.Name].Owner = rw.UID
		}
		rw.Generation = 1
		rw.Paused = true
		rw.Phase = "paused"
		rw.Reason = "RESTORED_PAUSED_REVIEW_SOURCE_FENCING_AND_NODE_SELECTORS"
		rw.CreatedAt = now
		restored.Workloads[name] = &rw
	}
	restored.Event("configuration.restored-paused", b.State.ClusterID, now)
	return &restored, restored.ValidateInventory()
}
