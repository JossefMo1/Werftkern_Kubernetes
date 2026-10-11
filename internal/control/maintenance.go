package control

import (
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"net/http"
)

type MaintenanceRequest struct {
	ID      string `json:"id"`
	Enabled bool   `json:"enabled"`
	Reason  string `json:"reason"`
}

func (a *API) maintenance(w http.ResponseWriter, r *http.Request) {
	var q MaintenanceRequest
	if !decode(w, r, &q) {
		return
	}
	if !model.ValidID(q.ID) || !model.ValidName(q.Reason) {
		failure(w, 400, "MAINTENANCE_REQUEST_INVALID")
		return
	}
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" && s.MaintenanceID != q.ID {
			return errors.New("MAINTENANCE_OWNED_BY_ANOTHER_OPERATION")
		}
		if q.Enabled {
			s.MaintenanceID = q.ID
		} else {
			s.MaintenanceID = ""
		}
		s.Event("maintenance.changed", q.Reason, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, map[string]any{"enabled": q.Enabled, "id": q.ID})
}
