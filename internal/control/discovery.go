package control

import (
	"github.com/ClusterPilot-System/werftkern/internal/discovery"
	"net/http"
	"strings"
)

func (a *API) discovery(w http.ResponseWriter, r *http.Request) {
	id := a.identity(r)
	if id == "" {
		failure(w, 403, "IDENTITY_REQUIRED")
		return
	}
	s, rev, e := a.Store.Read(r.Context())
	if e != nil {
		failError(w, e)
		return
	}

	snapshot := discovery.FromState(s, rev, a.now())
	if strings.HasPrefix(id, "gateway:") {
		g := s.Gateways[strings.TrimPrefix(id, "gateway:")]
		if g == nil || g.Revoked {
			failure(w, 403, "GATEWAY_NOT_AUTHORIZED")
			return
		}
		filtered := make([]discovery.Endpoint, 0)
		for _, e := range snapshot.Endpoints {
			if g.Allows(e.Service) {
				filtered = append(filtered, e)
			}
		}
		snapshot.Endpoints = filtered
	} else if id != "admin" {
		n := s.Nodes[strings.TrimPrefix(id, "node:")]
		if n == nil || n.Revoked {
			failure(w, 403, "NODE_NOT_AUTHORIZED")
			return
		}
	}
	write(w, 200, snapshot)
}
