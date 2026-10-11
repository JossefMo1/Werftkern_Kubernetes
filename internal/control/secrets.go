package control

import (
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"net/http"
	"strconv"
	"strings"
)

type SecretInput struct {
	Value           []byte `json:"value"`
	ExpectedVersion int    `json:"expectedVersion"`
}

func (a *API) putSecret(w http.ResponseWriter, r *http.Request) {
	if a.Vault == nil {
		failure(w, 503, "SECRET_VAULT_NOT_CONFIGURED")
		return
	}
	name := r.PathValue("name")
	var req SecretInput
	if !decode(w, r, &req) {
		return
	}
	if !model.ValidName(name) || len(req.Value) < 1 || len(req.Value) > 4096 || req.ExpectedVersion < 0 || req.ExpectedVersion >= 1000 {
		failure(w, 400, "SECRET_INPUT_INVALID")
		return
	}
	key := r.Header.Get("Idempotency-Key")
	ref := model.SecretRef{Name: name, Version: req.ExpectedVersion + 1}
	// The receipt stores a hash of keyed authenticated ciphertext, NOT a hash of
	// low-entropy plaintext. Request replay is checked by decrypting exact version.
	sealed, e := a.Vault.Seal(req.Value, model.SecretAAD(a.ClusterID, ref))
	if e != nil {
		failure(w, 500, "SECRET_ENCRYPTION_FAILED")
		return
	}
	_, _, e = a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" {
			return errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
		}
		if !model.ValidRequestID(key) {
			return errors.New("IDEMPOTENCY_KEY_REQUIRED")
		}
		if receipt, ok := s.Receipts[key]; ok {
			target, exists := s.Secrets[ref.Key()]
			if !exists || receipt.WorkloadUID != "secret:"+ref.Key() {
				return errors.New("IDEMPOTENCY_CONFLICT")
			}
			old, err := a.Vault.Open(target.Sealed, model.SecretAAD(a.ClusterID, ref))
			if err != nil || string(old) != string(req.Value) {
				return errors.New("IDEMPOTENCY_CONFLICT")
			}
			return nil
		}
		if _, err := s.Request(key, "", a.now()); err != nil {
			return err
		}
		max := 0
		for _, v := range s.Secrets {
			if v.Name == name && v.Version > max {
				max = v.Version
			}
		}
		if max != req.ExpectedVersion {
			return model.ErrConflict
		}
		if len(s.Secrets) >= 128 {
			return model.ErrCapacity
		}
		if s.Secrets == nil {
			s.Secrets = map[string]model.SecretVersion{}
		}
		s.Secrets[ref.Key()] = model.SecretVersion{Name: name, Version: ref.Version, Sealed: sealed}
		s.Receipts[key] = model.Receipt{ID: key, Hash: model.Hash(sealed), WorkloadUID: "secret:" + ref.Key(), Generation: int64(ref.Version), At: a.now()}
		s.Event("secret.version-created", name, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 201, ref)
}
func (a *API) deleteSecret(w http.ResponseWriter, r *http.Request) {
	v, e := strconv.Atoi(r.PathValue("version"))
	ref := model.SecretRef{Name: r.PathValue("name"), Version: v}
	if e != nil || model.ValidateSecretRefs([]model.SecretRef{ref}) != nil {
		failure(w, 400, "SECRET_REFERENCE_INVALID")
		return
	}
	_, _, e = a.Store.Update(r.Context(), func(s *model.State) error {
		if s.MaintenanceID != "" {
			return errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
		}
		if s.SecretReferenced(ref) {
			return errors.New("SECRET_VERSION_STILL_REFERENCED")
		}
		// Keep the highest immutable version as the generation floor to prevent ABA.
		target, ok := s.Secrets[ref.Key()]
		if !ok {
			return nil
		}
		max := 0
		for _, x := range s.Secrets {
			if x.Name == ref.Name && x.Version > max {
				max = x.Version
			}
		}
		if target.Version == max {
			return errors.New("LATEST_SECRET_VERSION_RETAINED_FOR_VERSION_SAFETY")
		}
		delete(s.Secrets, ref.Key())
		s.Event("secret.version-deleted", ref.Name, a.now())
		return nil
	})
	if e != nil {
		failError(w, e)
		return
	}
	write(w, 200, map[string]string{"status": "deleted"})
}
func (a *API) allocationSecrets(w http.ResponseWriter, r *http.Request) {
	identity := a.identity(r)
	if !strings.HasPrefix(identity, "node:") {
		failure(w, 403, "NODE_IDENTITY_REQUIRED")
		return
	}
	s, _, e := a.Store.Read(r.Context())
	if e != nil {
		failError(w, e)
		return
	}
	node := strings.TrimPrefix(identity, "node:")
	n := s.Nodes[node]
	alloc := s.Allocations[r.PathValue("id")]
	if n == nil || n.Revoked || alloc == nil || alloc.NodeID != node || alloc.Desired != "run" {
		failure(w, 403, "ALLOCATION_SCOPE_DENIED")
		return
	}
	if a.Vault == nil {
		failure(w, 503, "SECRET_VAULT_NOT_CONFIGURED")
		return
	}
	out := map[string][]byte{}
	for _, ref := range alloc.Spec.Secrets {
		sec, ok := s.Secrets[ref.Key()]
		if !ok {
			failure(w, 503, "SECRET_VERSION_UNAVAILABLE")
			return
		}
		b, e := a.Vault.Open(sec.Sealed, model.SecretAAD(a.ClusterID, ref))
		if e != nil {
			failure(w, 503, "SECRET_DECRYPTION_FAILED")
			return
		}
		out[ref.Name] = b
	}
	write(w, 200, out)
}
