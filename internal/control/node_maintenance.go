package control

import (
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
)

// MaintenanceNodeRequest binds each mutation to the already held cluster lock.
// Heartbeats/stop acknowledgements keep flowing; unrelated scheduling stays frozen.
type MaintenanceNodeRequest struct {
	ID              string `json:"id"`
	ExpectedVersion string `json:"expectedVersion,omitempty"`
	MinSequence     uint64 `json:"minSequence,omitempty"`
}

type NodeState struct {
	ClusterID              string `json:"clusterId"`
	ControllerVersion      string `json:"controllerVersion"`
	StateSchema            int    `json:"stateSchema"`
	MaintenanceID          string `json:"maintenanceId"`
	NodeID                 string `json:"nodeId"`
	InstanceID             string `json:"instanceId"`
	Address                string `json:"address"`
	Drain                  bool   `json:"drain"`
	Healthy                bool   `json:"healthy"`
	Version                string `json:"version"`
	HeartbeatSequence      uint64 `json:"heartbeatSequence"`
	UnconfirmedAllocations int    `json:"unconfirmedAllocations"`
}

func nodeProjection(s *model.State, id string, now time.Time) (NodeState, error) {
	n := s.Nodes[id]
	if n == nil || n.Revoked {
		return NodeState{}, errors.New("NODE_NOT_AUTHORIZED")
	}
	x := NodeState{ClusterID: s.ClusterID, ControllerVersion: model.Version, StateSchema: s.Schema,
		MaintenanceID: s.MaintenanceID, NodeID: n.ID, InstanceID: n.InstanceID, Address: n.Address,
		Drain: n.Drain, Healthy: n.Ready(now), Version: n.Version, HeartbeatSequence: n.HeartbeatSequence}
	for _, a := range s.Allocations {
		if a.NodeID == id && !(a.Desired == "stop" && a.Phase == "stopped") {
			x.UnconfirmedAllocations++
		}
	}
	return x, nil
}

func (a *API) nodeState(w http.ResponseWriter, r *http.Request) {
	ident := a.identity(r)
	if !strings.HasPrefix(ident, "node:") {
		failure(w, 403, "NODE_IDENTITY_REQUIRED")
		return
	}
	s, _, e := a.Store.Read(r.Context())
	if e != nil {
		failError(w, e)
		return
	}
	x, e := nodeProjection(s, strings.TrimPrefix(ident, "node:"), a.now())
	if e != nil {
		failure(w, 403, "NODE_NOT_AUTHORIZED")
		return
	}
	write(w, 200, x)
}

// AdvanceNodeDrain is one idempotent transaction. No blanket cluster unfreeze,
// no force eviction, no timeout-based assumption that a remote process stopped.
func AdvanceNodeDrain(s *model.State, id, operation string, now time.Time) error {
	if !model.ValidID(operation) || s.MaintenanceID != operation {
		return errors.New("OWNED_MAINTENANCE_REQUIRED")
	}
	n := s.Nodes[id]
	if n == nil || n.Revoked || !n.Ready(now) {
		return errors.New("DRAIN_REQUIRES_LIVE_AUTHORIZED_NODE")
	}
	for other, v := range s.Nodes {
		if other != id && v.Drain && !v.Revoked {
			return errors.New("ONLY_ONE_MAINTENANCE_DRAIN_AT_A_TIME")
		}
	}
	scope := map[string]bool{}
	for _, w := range s.Workloads {
		if w.Spec.Node == id && !w.Paused && !w.Deleting && w.Spec.Replicas > 0 {
			return errors.New("PINNED_WORKLOAD_REQUIRES_OFFLINE_MAINTENANCE")
		}
	}
	for _, x := range s.Allocations {
		if x.NodeID != id || x.Phase == "stopped" && x.Desired == "stop" {
			continue
		}
		if len(x.Spec.Volumes) > 0 || x.Spec.Node != "" || x.Spec.Profile != "" {
			return errors.New("STATEFUL_OR_PINNED_EXECUTION_REQUIRES_OFFLINE_MAINTENANCE")
		}
		scope[x.WorkloadUID] = true
	}
	if !n.Drain {
		n.Drain = true
		s.Event("node.maintenance-drain", id, now)
	}
	return reconcileSelected(s, now, scope, true)
}

func (a *API) maintenanceNode(w http.ResponseWriter, r *http.Request) {
	var q MaintenanceNodeRequest
	if !decode(w, r, &q) {
		return
	}
	id, action := r.PathValue("id"), r.PathValue("action")
	if !model.ValidID(id) || !model.ValidID(q.ID) || action != "drain" && action != "uncordon" {
		failure(w, 400, "MAINTENANCE_NODE_REQUEST_INVALID")
		return
	}
	var result NodeState
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != q.ID {
			return errors.New("OWNED_MAINTENANCE_REQUIRED")
		}
		if action == "drain" {
			if q.ExpectedVersion != "" || q.MinSequence != 0 {
				return errors.New("DRAIN_REQUEST_FIELDS_INVALID")
			}
			if e := AdvanceNodeDrain(s, id, q.ID, a.now()); e != nil {
				return e
			}
		} else {
			n := s.Nodes[id]
			if n == nil || !n.Ready(a.now()) || q.ExpectedVersion != model.Version || n.Version != q.ExpectedVersion || q.MinSequence == 0 || n.HeartbeatSequence < q.MinSequence {
				return errors.New("CURRENT_TARGET_AGENT_OBSERVATION_REQUIRED")
			}
			x, e := nodeProjection(s, id, a.now())
			if e != nil {
				return e
			}
			if x.UnconfirmedAllocations != 0 {
				return errors.New("UNCONFIRMED_EXECUTIONS_BLOCK_UNCORDON")
			}
			if n.Drain {
				n.Drain = false
				s.Event("node.maintenance-uncordon", id, a.now())
			}
		}
		var e error
		result, e = nodeProjection(s, id, a.now())
		return e
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, result)
}
