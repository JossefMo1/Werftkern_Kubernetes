package control

import (
	"context"
	"encoding/json"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/store"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/strictjson"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"io"
	"log"
	"mime"
	"net"
	"net/http"
	"strings"
	"time"
)

type API struct {
	Store     store.Store
	ClusterID string
	Vault     *vault.Vault
	Now       func() time.Time
}
type Problem struct {
	Type   string `json:"type"`
	Title  string `json:"title"`
	Status int    `json:"status"`
	Code   string `json:"code"`
}

func write(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
func failure(w http.ResponseWriter, status int, code string) {
	write(w, status, Problem{Type: "about:blank", Title: code, Status: status, Code: code})
}
func failError(w http.ResponseWriter, e error) {
	status := 400
	code := e.Error()
	switch {
	case errors.Is(e, model.ErrNotFound):
		status = 404
	case errors.Is(e, model.ErrConflict) || code == "IDEMPOTENCY_CONFLICT":
		status = 409
	case errors.Is(e, model.ErrCapacity):
		status = 429
	case errors.Is(e, store.ErrUnavailable) || errors.Is(e, store.ErrUninitialized):
		status = 503
		code = "STATE_UNAVAILABLE"
	}
	failure(w, status, code)
}
func decode(w http.ResponseWriter, r *http.Request, v any) bool {
	ct, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
	if err != nil || ct != "application/json" {
		failure(w, 415, "JSON_REQUIRED")
		return false
	}
	r.Body = http.MaxBytesReader(w, r.Body, 65536)
	raw, e := io.ReadAll(r.Body)
	if e != nil || strictjson.Unmarshal(raw, v) != nil {
		failure(w, 400, "INVALID_OR_OVERSIZED_JSON")
		return false
	}
	return true
}
func (a *API) now() time.Time {
	if a.Now != nil {
		return a.Now().UTC()
	}
	return time.Now().UTC()
}
func (a *API) identity(r *http.Request) string {
	if r.TLS == nil || len(r.TLS.VerifiedChains) == 0 || len(r.TLS.PeerCertificates) == 0 {
		return ""
	}
	c := r.TLS.PeerCertificates[0]
	if now := time.Now(); now.Before(c.NotBefore) || !now.Before(c.NotAfter) {
		return ""
	}
	if len(c.Subject.Organization) != 1 || c.Subject.Organization[0] != a.ClusterID {
		return ""
	}
	id := c.Subject.CommonName
	if strings.HasPrefix(id, "gateway:") && model.ValidID(strings.TrimPrefix(id, "gateway:")) {
		return id
	}
	if id == "admin" {
		return id
	}
	if strings.HasPrefix(id, "node:") && model.ValidID(strings.TrimPrefix(id, "node:")) {
		return id
	}
	return ""
}
func (a *API) admin(fn http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if a.identity(r) != "admin" {
			failure(w, 403, "ADMIN_IDENTITY_REQUIRED")
			return
		}
		fn(w, r)
	}
}
func (a *API) Handler() http.Handler {
	m := http.NewServeMux()
	m.HandleFunc("GET /v1/health", func(w http.ResponseWriter, r *http.Request) {
		if a.identity(r) == "" {
			failure(w, 403, "IDENTITY_REQUIRED")
			return
		}
		_, _, e := a.Store.Read(r.Context())
		if e != nil {
			failError(w, e)
			return
		}
		write(w, 200, map[string]any{"status": "ready", "clusterId": a.ClusterID, "version": model.Version, "stateSchema": model.StateSchema, "maturity": "experimental", "supportedAgentVersions": model.SupportedAgentVersions()})
	})
	m.HandleFunc("GET /v1/state", a.admin(func(w http.ResponseWriter, r *http.Request) {
		s, _, e := a.Store.Read(r.Context())
		if e != nil {
			failError(w, e)
			return
		}
		for k, v := range s.Secrets {
			v.Sealed = ""
			s.Secrets[k] = v
		}
		write(w, 200, s)
	}))
	m.HandleFunc("POST /v1/workloads", a.admin(a.apply))
	m.HandleFunc("POST /v1/workloads/{name}/{action}", a.admin(a.mutate))
	m.HandleFunc("POST /v1/nodes", a.admin(a.addNode))
	m.HandleFunc("POST /v1/gateways", a.admin(a.registerGateway))
	m.HandleFunc("POST /v1/gateways/{id}/revoke", a.admin(a.revokeGateway))
	m.HandleFunc("POST /v1/nodes/{id}", a.admin(a.nodeAction))
	m.HandleFunc("POST /v1/heartbeat", a.heartbeat)
	m.HandleFunc("PUT /v1/secrets/{name}", a.admin(a.putSecret))
	m.HandleFunc("DELETE /v1/secrets/{name}/{version}", a.admin(a.deleteSecret))
	m.HandleFunc("GET /v1/allocations/{id}/secrets", a.allocationSecrets)
	m.HandleFunc("POST /v1/volumes", a.admin(a.createVolume))
	m.HandleFunc("GET /v1/allocations/{id}/volumes", a.allocationVolumes)
	m.HandleFunc("POST /v1/volumes/{name}/initialized", a.initializeVolume)
	m.HandleFunc("POST /v1/volumes/{name}/release", a.admin(a.releaseVolume))
	m.HandleFunc("POST /v1/volumes/{name}/restore", a.admin(a.restoreVolume))
	m.HandleFunc("POST /v1/maintenance", a.admin(a.maintenance))
	m.HandleFunc("POST /v1/maintenance/nodes/{id}/{action}", a.admin(a.maintenanceNode))
	m.HandleFunc("GET /v1/node-state", a.nodeState)
	m.HandleFunc("GET /v1/discovery", a.discovery)
	m.HandleFunc("GET /v1/metrics", a.admin(a.metrics))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		if r.Header.Get("Origin") != "" {
			failure(w, 403, "DIRECT_BROWSER_ACCESS_DISABLED_USE_LOCAL_DASHBOARD")
			return
		}
		m.ServeHTTP(w, r)
	})
}
func (a *API) apply(w http.ResponseWriter, r *http.Request) {
	var req model.ApplyRequest
	if !decode(w, r, &req) {
		return
	}
	var receipt model.Receipt
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		var err error
		receipt, err = model.Apply(s, req, r.Header.Get("Idempotency-Key"), a.now())
		return err
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 202, receipt)
}
func (a *API) mutate(w http.ResponseWriter, r *http.Request) {
	var req model.MutationRequest
	if !decode(w, r, &req) {
		return
	}
	name, action := r.PathValue("name"), r.PathValue("action")
	if !model.ValidName(name) || action != "delete" && action != "rollback" && action != "pause" && action != "resume" {
		failure(w, 400, "ACTION_INVALID")
		return
	}
	var receipt model.Receipt
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		var err error
		receipt, err = model.MutateWorkload(s, name, action, r.Header.Get("Idempotency-Key"), req.ExpectedGeneration, a.now())
		return err
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 202, receipt)
}

type NodeRegistration struct {
	PodCIDR string `json:"podCidr,omitempty"`
	ID      string `json:"id"`
	Name    string `json:"name"`
	Address string `json:"address"`
}

func (a *API) addNode(w http.ResponseWriter, r *http.Request) {
	var req NodeRegistration
	if !decode(w, r, &req) {
		return
	}
	n := model.Node{PodCIDR: req.PodCIDR, ID: req.ID, Name: req.Name, Address: req.Address}
	if e := model.ValidateNode(n); e != nil {
		failError(w, e)
		return
	}
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" {
			return errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
		}
		if existing := s.Nodes[n.ID]; existing != nil {
			if existing.Name != n.Name || existing.Address != n.Address || existing.PodCIDR != n.PodCIDR {
				return model.ErrConflict
			}
			return nil
		}
		for _, existing := range s.Nodes {
			if existing.Name == n.Name || existing.Address == n.Address || model.SubnetsOverlap(existing.PodCIDR, n.PodCIDR) {
				return model.ErrConflict
			}
		}
		if len(s.Nodes) >= model.MaxNodes {
			return model.ErrCapacity
		}
		s.Nodes[n.ID] = &n
		s.Event("node.registered", n.Name, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 201, map[string]string{"id": n.ID})
}
func (a *API) nodeAction(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Drain   *bool `json:"drain,omitempty"`
		Revoked *bool `json:"revoked,omitempty"`
	}
	if !decode(w, r, &req) {
		return
	}
	if req.Drain == nil && req.Revoked == nil || req.Drain != nil && req.Revoked != nil {
		failure(w, 400, "EXACTLY_ONE_NODE_ACTION_REQUIRED")
		return
	}
	_, _, e := a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" {
			return errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
		}
		n := s.Nodes[r.PathValue("id")]
		if n == nil {
			return model.ErrNotFound
		}
		if req.Drain != nil {
			n.Drain = *req.Drain
		}
		if req.Revoked != nil {
			n.Revoked = *req.Revoked
		}
		s.Event("node.policy-changed", n.Name, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, map[string]string{"status": "accepted"})
}

var reportPhases = map[string]bool{"assigned": true, "starting": true, "ready": true, "failed": true, "stopped": true}

func (a *API) heartbeat(w http.ResponseWriter, r *http.Request) {
	identity := a.identity(r)
	if !strings.HasPrefix(identity, "node:") {
		failure(w, 403, "NODE_IDENTITY_REQUIRED")
		return
	}
	id := strings.TrimPrefix(identity, "node:")
	var req model.Heartbeat
	if !decode(w, r, &req) {
		return
	}
	if !model.SupportedAgentVersion(req.Version) {
		failure(w, 426, "AGENT_VERSION_NOT_SUPPORTED_BY_THIS_RELEASE")
		return
	}
	if req.Sequence == 0 {
		failure(w, 400, "HEARTBEAT_SEQUENCE_REQUIRED")
		return
	}
	if !model.ValidID(req.InstanceID) || req.CPUMilli < 100 || req.CPUMilli > 512000 || req.MemoryMiB < 64 || req.MemoryMiB > 2097152 || len(req.Reports) > model.MaxAllocations || len(req.Version) > 40 {
		failure(w, 400, "HEARTBEAT_INVALID")
		return
	}
	seenReports := map[string]bool{}
	for _, p := range req.Reports {
		if seenReports[p.ID] {
			failure(w, 400, "DUPLICATE_ALLOCATION_REPORT")
			return
		}
		seenReports[p.ID] = true
		if !model.ValidID(p.ID) || !reportPhases[p.Phase] || len(p.Reason) > 100 || strings.ContainsAny(p.Reason, "\n\r\t") {
			failure(w, 400, "REPORT_INVALID")
			return
		}
	}
	now := a.now()
	s, revision, e := a.Store.Update(r.Context(), func(s *model.State) error {
		n := s.Nodes[id]
		if n == nil || n.Revoked {
			return errors.New("NODE_NOT_AUTHORIZED")
		}
		if n.InstanceID != "" && n.InstanceID != req.InstanceID {
			return errors.New("NODE_ALREADY_CLAIMED")
		}
		if n.HeartbeatSequence > 0 {
			if req.Sequence == 0 {
				return errors.New("HEARTBEAT_SEQUENCE_REQUIRED_AFTER_UPGRADE")
			}
			if req.Sequence < n.HeartbeatSequence {
				return nil
			} // No observation rollback.
			if req.Sequence == n.HeartbeatSequence {
				if n.HeartbeatHash != model.Hash(req) {
					return errors.New("HEARTBEAT_REPLAY_CONTENT_CONFLICT")
				}
				return nil // Duplicate delivery must not refresh liveness.
			}
		}
		for _, p := range req.Reports {
			if p.ContainerIP != "" {
				_, cidr, err := net.ParseCIDR(n.PodCIDR)
				ip := net.ParseIP(p.ContainerIP)
				if err != nil || ip == nil || !cidr.Contains(ip) {
					return errors.New("CONTAINER_IP_OUTSIDE_ENROLLED_SUBNET")
				}
			}
			if allocation := s.Allocations[p.ID]; allocation != nil && allocation.NodeID != id {
				return errors.New("ALLOCATION_SCOPE_DENIED")
			}
		}
		n.HeartbeatSequence = req.Sequence
		n.HeartbeatHash = model.Hash(req)
		n.InstanceID = req.InstanceID
		n.CPUMilli = req.CPUMilli
		n.MemoryMiB = req.MemoryMiB
		n.LastSeen = now
		n.Healthy = req.Healthy
		n.Version = req.Version
		for _, p := range req.Reports {
			allocation := s.Allocations[p.ID]
			if allocation == nil {
				continue
			}
			if allocation.Phase == "stopped" {
				continue
			} // Terminal; late reports cannot resurrect it.
			if p.Phase == "stopped" && allocation.Desired != "stop" {
				continue
			}
			phase, reason := p.Phase, p.Reason
			// A fresh heartbeat cannot make a stale process observation ready.
			if phase == "ready" && (p.ObservedAt.IsZero() || p.ObservedAt.After(now.Add(5*time.Second)) || now.Sub(p.ObservedAt) > model.HeartbeatTimeout) {
				phase, reason = "starting", "READINESS_OBSERVATION_STALE"
			}
			if allocation.Phase != phase {
				s.Event("allocation."+phase, p.ID, now)
			}
			allocation.Phase, allocation.Reason = phase, reason
			allocation.ContainerIP = p.ContainerIP
			allocation.UpdatedAt = now
			if phase == "ready" {
				// Re-sending the same recent probe must not extend its validity.
				allocation.UpdatedAt = p.ObservedAt
			}
		}
		return nil
	})
	if e != nil {
		if e.Error() == "NODE_NOT_AUTHORIZED" || e.Error() == "NODE_ALREADY_CLAIMED" || e.Error() == "ALLOCATION_SCOPE_DENIED" {
			failure(w, 403, e.Error())
		} else {
			failError(w, e)
		}
		return
	}
	out := model.AssignmentSnapshot{ClusterID: a.ClusterID, Revision: revision, Allocations: []model.Allocation{}}
	for _, key := range model.SortedKeys(s.Allocations) {
		allocation := s.Allocations[key]
		if allocation.NodeID == id {
			out.Allocations = append(out.Allocations, *allocation)
		}
	}
	write(w, 200, out)
}
func (a *API) RunReconciler(ctx context.Context) {
	t := time.NewTicker(2 * time.Second)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			ctx2, cancel := context.WithTimeout(ctx, 10*time.Second)
			_, _, e := a.Store.Update(ctx2, func(s *model.State) error { return Reconcile(s, a.now()) })
			cancel()
			if e != nil {
				log.Printf("reconcile_failed code=%s", safeError(e))
			}
		}
	}
}
func safeError(e error) string {
	if errors.Is(e, model.ErrCapacity) {
		return "CAPACITY"
	}
	return "STATE_UNAVAILABLE"
}
