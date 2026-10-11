package store

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
)

type MigrationPreview struct {
	ClusterID    string `json:"clusterId"`
	From         int    `json:"from"`
	To           int    `json:"to"`
	Revision     int64  `json:"revision"`
	SourceSHA256 string `json:"sourceSha256"`
	Workloads    int    `json:"workloads"`
	Nodes        int    `json:"nodes"`
	Volumes      int    `json:"volumes"`
}

func prepareMigration(raw []byte, cluster, owner string) (*model.State, MigrationPreview, error) {
	var s model.State
	var out MigrationPreview
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if e := d.Decode(&s); e != nil {
		return nil, out, e
	}
	var extra any
	if d.Decode(&extra) != io.EOF {
		return nil, out, errors.New("MIGRATION_TRAILING_STATE")
	}
	if s.ClusterID != cluster || !model.ValidID(owner) || s.MaintenanceID != owner {
		return nil, out, errors.New("MIGRATION_SCOPE_OR_MAINTENANCE_MISMATCH")
	}
	if s.Schema != 1 {
		return nil, out, errors.New("MIGRATION_SOURCE_SCHEMA_MUST_BE_1")
	}
	if len(s.Allocations) != 0 {
		return nil, out, errors.New("MIGRATION_REQUIRES_NO_ALLOCATIONS")
	}
	for _, w := range s.Workloads {
		if w == nil || !w.Paused {
			return nil, out, errors.New("MIGRATION_REQUIRES_ALL_WORKLOADS_PAUSED")
		}
	}
	hash := sha256.Sum256(raw)
	out = MigrationPreview{ClusterID: cluster, From: 1, To: model.StateSchema, SourceSHA256: hex.EncodeToString(hash[:]), Workloads: len(s.Workloads), Nodes: len(s.Nodes), Volumes: len(s.Volumes)}
	s.Schema = model.StateSchema
	s.MigrationSourceHash = out.SourceSHA256
	if e := s.ValidateInventory(); e != nil {
		return nil, out, e
	}
	return &s, out, nil
}
func (e *Etcd) PreviewMigration(ctx context.Context, owner string) (MigrationPreview, error) {
	raw, revision, err := e.readRaw(ctx)
	if err != nil {
		return MigrationPreview{}, err
	}
	_, out, err := prepareMigration(raw, e.ClusterID, owner)
	out.Revision = revision
	return out, err
}

// MigrateSchema is an offline, one-CAS schema transition. persistBackup must
// durably save the EXACT source bytes before the write. A competing writer
// aborts rather than retrying against a changed, unbacked-up source.
func (e *Etcd) MigrateSchema(ctx context.Context, owner, expectedSHA string, persistBackup func([]byte) error) (MigrationPreview, error) {
	raw, revision, err := e.readRaw(ctx)
	if err != nil {
		return MigrationPreview{}, err
	}
	var prior model.State
	if json.Unmarshal(raw, &prior) == nil && prior.Schema == model.StateSchema && prior.MigrationSourceHash == expectedSHA && model.ValidSHA256(expectedSHA) && prior.ClusterID == e.ClusterID && prior.MaintenanceID == owner {
		if err = prior.ValidateInventory(); err != nil {
			return MigrationPreview{}, err
		}
		return MigrationPreview{ClusterID: e.ClusterID, From: 1, To: model.StateSchema, SourceSHA256: expectedSHA, Revision: revision}, nil
	}
	next, preview, err := prepareMigration(raw, e.ClusterID, owner)
	if err != nil {
		return preview, err
	}
	preview.Revision = revision
	if expectedSHA != preview.SourceSHA256 || persistBackup == nil {
		return preview, errors.New("MIGRATION_SOURCE_HASH_AND_BACKUP_REQUIRED")
	}
	if err = persistBackup(append([]byte{}, raw...)); err != nil {
		return preview, err
	}
	next.Event("schema.migrated_offline", expectedSHA, time.Now().UTC())
	ok, newRevision, err := e.cas(ctx, next, revision)
	if err != nil {
		return preview, err
	}
	if !ok {
		return preview, model.ErrConflict
	}
	preview.Revision = newRevision
	return preview, nil
}
