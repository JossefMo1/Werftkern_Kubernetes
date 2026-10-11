package control

import (
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"net/http"
)

func (a *API) registerGateway(w http.ResponseWriter, r *http.Request) {
	var q model.Gateway
	if !decode(w, r, &q) {
		return
	}
	q.Normalize()
	if e := q.Validate(); e != nil {
		failError(w, e)
		return
	}
	if q.Revoked {
		failure(w, 400, "NEW_GATEWAY_CANNOT_BE_REVOKED")
		return
	}
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" {
			return errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
		}
		if s.Gateways == nil {
			s.Gateways = map[string]*model.Gateway{}
		}
		if old := s.Gateways[q.ID]; old != nil {
			if model.Hash(old) != model.Hash(q) {
				return model.ErrConflict
			}
			return nil
		}
		for _, g := range s.Gateways {
			if g.Name == q.Name {
				return model.ErrConflict
			}
		}
		if len(s.Gateways) >= 10 {
			return model.ErrCapacity
		}
		g := q
		s.Gateways[g.ID] = &g
		s.Event("gateway.registered", g.ID, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 201, q)
}
func (a *API) revokeGateway(w http.ResponseWriter, r *http.Request) {
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		g := s.Gateways[r.PathValue("id")]
		if g == nil {
			return model.ErrNotFound
		}
		g.Revoked = true
		s.Event("gateway.revoked", g.ID, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, map[string]bool{"revoked": true})
}
