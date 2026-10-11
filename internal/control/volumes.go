package control

import (
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"net/http"
	"strings"
)

type VolumeCreate struct {
	Name   string `json:"name"`
	NodeID string `json:"nodeId"`
	UID    int    `json:"uid"`
	GID    int    `json:"gid"`
}

func (a *API) createVolume(w http.ResponseWriter, r *http.Request) {
	var q VolumeCreate
	if !decode(w, r, &q) {
		return
	}
	var out *model.Volume
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" {
			return errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
		}
		if s.Volumes == nil {
			s.Volumes = map[string]*model.Volume{}
		}
		if v := s.Volumes[q.Name]; v != nil {
			if v.NodeID != q.NodeID || v.UID != q.UID || v.GID != q.GID {
				return model.ErrConflict
			}
			out = v
			return nil
		}
		if n := s.Nodes[q.NodeID]; n == nil || n.Revoked {
			return errors.New("VOLUME_NODE_INVALID")
		}
		v := &model.Volume{ID: model.ID(), Name: q.Name, NodeID: q.NodeID, UID: q.UID, GID: q.GID}
		if e := v.Validate(); e != nil {
			return e
		}
		s.Volumes[q.Name] = v
		out = v
		s.Event("volume.registered", v.ID, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 201, out)
}
func (a *API) allocationVolumes(w http.ResponseWriter, r *http.Request) {
	identity := a.identity(r)
	s, _, e := a.Store.Read(r.Context())
	if e != nil {
		failError(w, e)
		return
	}
	al := s.Allocations[r.PathValue("id")]
	id := strings.TrimPrefix(identity, "node:")
	if !strings.HasPrefix(identity, "node:") || al == nil || al.NodeID != id || al.Desired != "run" || s.Nodes[id] == nil || s.Nodes[id].Revoked {
		failure(w, 403, "ALLOCATION_SCOPE_DENIED")
		return
	}
	out := []model.Volume{}
	for _, ref := range al.Spec.Volumes {
		v := s.Volumes[ref.Name]
		if v == nil || v.NodeID != id || v.Owner != al.WorkloadUID {
			failure(w, 409, "VOLUME_OWNERSHIP_CONFLICT")
			return
		}
		out = append(out, *v)
	}
	write(w, 200, out)
}
func (a *API) initializeVolume(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(a.identity(r), "node:")
	if !model.ValidID(id) {
		failure(w, 403, "NODE_IDENTITY_REQUIRED")
		return
	}
	var req struct {
		AllocationID string `json:"allocationId"`
	}
	if !decode(w, r, &req) {
		return
	}
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		n := s.Nodes[id]
		al := s.Allocations[req.AllocationID]
		v := s.Volumes[r.PathValue("name")]
		if n == nil || n.Revoked || al == nil || al.NodeID != id || al.Desired != "run" || v == nil || v.NodeID != id || v.Owner != al.WorkloadUID {
			return errors.New("VOLUME_SCOPE_DENIED")
		}
		found := false
		for _, ref := range al.Spec.Volumes {
			if ref.Name == v.Name {
				found = true
			}
		}
		if !found {
			return errors.New("VOLUME_SCOPE_DENIED")
		}
		if !v.Initialized {
			v.Initialized = true
			s.Event("volume.initialized", v.ID, a.now())
		}
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, map[string]bool{"initialized": true})
}
func (a *API) releaseVolume(w http.ResponseWriter, r *http.Request) {
	var q struct {
		ID string `json:"id"`
	}
	if !decode(w, r, &q) {
		return
	}
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" {
			return errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
		}
		v := s.Volumes[r.PathValue("name")]
		if v == nil {
			return model.ErrNotFound
		}
		if v.ID != q.ID {
			return model.ErrConflict
		}
		if s.VolumeInUse(v.Name) {
			return errors.New("VOLUME_STILL_REFERENCED")
		}
		v.Owner = ""
		s.Event("volume.released_data_retained", v.ID, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, map[string]string{"status": "released-data-retained"})
}

// VolumeRestoreRequest is an administrator's local disk-restore acknowledgement,
// not independent proof of restored bytes. Pending restore remains fail-closed.
type VolumeRestoreRequest struct {
	ID            string `json:"id"`
	MaintenanceID string `json:"maintenanceId"`
	OperationID   string `json:"operationId"`
	SHA256        string `json:"sha256"`
	Complete      bool   `json:"complete"`
}

func (a *API) restoreVolume(w http.ResponseWriter, r *http.Request) {
	var q VolumeRestoreRequest
	if !decode(w, r, &q) {
		return
	}
	if !model.ValidID(q.OperationID) || !model.ValidID(q.ID) || !model.ValidSHA256(q.SHA256) {
		failure(w, 400, "VOLUME_RESTORE_REQUEST_INVALID")
		return
	}
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		v := s.Volumes[r.PathValue("name")]
		if v == nil {
			return model.ErrNotFound
		}
		if v.ID != q.ID {
			return model.ErrConflict
		}
		if _, e := s.QuiescentVolume(v.Name, v.NodeID, q.MaintenanceID); e != nil {
			return e
		}
		if v.RestoreID != "" {
			if v.RestoreID != q.OperationID || v.RestoreHash != q.SHA256 {
				return model.ErrConflict
			}
		} else {
			if q.Complete || v.Initialized {
				return errors.New("NEW_UNINITIALIZED_RESTORE_TARGET_REQUIRED")
			}
			v.RestoreID = q.OperationID
			v.RestoreHash = q.SHA256
			v.Initialized = true
			s.Event("volume.restore_reserved", v.ID, a.now())
		}
		if q.Complete && !v.RestoreComplete {
			v.RestoreComplete = true
			s.Event("volume.restore_acknowledged_by_admin", v.ID, a.now())
		}
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, map[string]bool{"complete": q.Complete})
}
