package model

import (
	"encoding/hex"
	"errors"
	"path"
	"strings"
)

type VolumeRef struct {
	Name      string `json:"name"`
	MountPath string `json:"mountPath"`
	ReadOnly  bool   `json:"readOnly,omitempty"`
}
type Volume struct {
	RestoreID       string `json:"restoreId,omitempty"`
	RestoreHash     string `json:"restoreHash,omitempty"`
	RestoreComplete bool   `json:"restoreComplete,omitempty"`
	ID              string `json:"id"`
	Name            string `json:"name"`
	NodeID          string `json:"nodeId"`
	UID             int    `json:"uid"`
	GID             int    `json:"gid"`
	Owner           string `json:"owner,omitempty"`
	Initialized     bool   `json:"initialized"`
}

func ValidSHA256(s string) bool {
	b, e := hex.DecodeString(s)
	return e == nil && len(b) == 32 && len(s) == 64 && strings.ToLower(s) == s
}
func (v Volume) Validate() error {
	if v.RestoreID != "" && (!ValidID(v.RestoreID) || !ValidSHA256(v.RestoreHash) || !v.Initialized) || v.RestoreID == "" && (v.RestoreHash != "" || v.RestoreComplete) {
		return errors.New("VOLUME_RESTORE_METADATA_INVALID")
	}

	if !ValidID(v.ID) || !ValidName(v.Name) || !ValidID(v.NodeID) || v.UID < 1 || v.UID > 65534 || v.GID < 1 || v.GID > 65534 || v.Owner != "" && !ValidID(v.Owner) {
		return errors.New("VOLUME_INVALID")
	}
	return nil
}
func (s Spec) User() (int, int) {
	if s.RunAsUID == 0 {
		return 65532, 65532
	}
	return s.RunAsUID, s.RunAsGID
}
func (s Spec) ValidateStorage() error {
	if len(s.Volumes) > 4 {
		return errors.New("VOLUME_LIMIT")
	}
	if s.RunAsUID != 0 && (s.RunAsUID < 1 || s.RunAsUID > 65534 || s.RunAsGID < 1 || s.RunAsGID > 65534) || s.RunAsUID == 0 && s.RunAsGID != 0 {
		return errors.New("NON_ROOT_USER_REQUIRED")
	}
	if s.Probe != "" && s.Probe != "tcp" && s.Probe != "postgres" {
		return errors.New("PROBE_INVALID")
	}
	if s.Probe != "" && (s.Port == 0 || s.ReadinessPath != "") {
		return errors.New("PROBE_CONFLICT")
	}
	if s.Profile != "" && s.Profile != "postgres17" {
		return errors.New("PROFILE_INVALID")
	}
	names := map[string]bool{}
	paths := []string{}
	for _, v := range s.Volumes {
		if !ValidName(v.Name) || names[v.Name] || !strings.HasPrefix(v.MountPath, "/data/") && v.MountPath != "/var/lib/postgresql/data" || path.Clean(v.MountPath) != v.MountPath || strings.ContainsAny(v.MountPath, ":\n\r\x00 ") {
			return errors.New("VOLUME_REFERENCE_INVALID")
		}
		for _, p := range paths {
			if strings.HasPrefix(v.MountPath, p+"/") || strings.HasPrefix(p, v.MountPath+"/") || p == v.MountPath {
				return errors.New("VOLUME_PATH_OVERLAP")
			}
		}
		names[v.Name] = true
		paths = append(paths, v.MountPath)
	}
	if len(s.Volumes) > 0 && (s.Replicas > 1 || !ValidID(s.Node)) {
		return errors.New("LOCAL_VOLUME_REQUIRES_SINGLE_REPLICA_AND_PINNED_NODE")
	}
	if s.Profile == "postgres17" {
		if len(s.Volumes) != 1 || s.Volumes[0].MountPath != "/var/lib/postgresql/data" || s.Volumes[0].ReadOnly || s.Probe != "postgres" || s.Port != 5432 || len(s.Command) != 0 {
			return errors.New("POSTGRES_PROFILE_INVALID")
		}
		found := false
		for _, ref := range s.Secrets {
			if ref.Name == "postgres-password" {
				found = true
			}
		}
		if !found {
			return errors.New("POSTGRES_PASSWORD_SECRET_REQUIRED")
		}
	}
	return nil
}
func (s *State) ValidateVolumeAvailability(spec Spec, owner string) error {
	return s.validateVolumeAvailability(spec, owner, true)
}
func (s *State) validateVolumeAvailability(spec Spec, owner string, ready bool) error {
	uid, gid := spec.User()
	for _, ref := range spec.Volumes {
		v := s.Volumes[ref.Name]
		if v == nil {
			return errors.New("VOLUME_NOT_FOUND")
		}
		if ready && v.RestoreID != "" && !v.RestoreComplete {
			return errors.New("VOLUME_RESTORE_PENDING")
		}
		if v.NodeID != spec.Node {
			return errors.New("VOLUME_NODE_MISMATCH")
		}
		if v.Owner != "" && v.Owner != owner {
			return errors.New("VOLUME_ALREADY_CLAIMED")
		}
		if !ref.ReadOnly && (v.UID != uid || v.GID != gid) {
			return errors.New("VOLUME_USER_MISMATCH")
		}
	}
	return nil
}

// Volumes retain ownership across application deletion; releasing them is a
// separate administrator decision, never a side effect of garbage collection.
func (s *State) VolumeInUse(name string) bool {
	for _, w := range s.Workloads {
		for _, v := range w.Spec.Volumes {
			if v.Name == name {
				return true
			}
		}
		for _, h := range w.History {
			for _, v := range h.Volumes {
				if v.Name == name {
					return true
				}
			}
		}
	}
	for _, a := range s.Allocations {
		if a.Phase != "stopped" {
			for _, v := range a.Spec.Volumes {
				if v.Name == name {
					return true
				}
			}
		}
	}
	return false
}

// QuiescentVolume checks control-plane intent, not disk consistency. The local
// maintenance command additionally takes the engine IO lock and checks Docker.
func (s *State) QuiescentVolume(name, nodeID, maintenanceID string) (*Volume, error) {
	if !ValidID(maintenanceID) || s.MaintenanceID != maintenanceID {
		return nil, errors.New("OWNED_MAINTENANCE_REQUIRED")
	}
	v := s.Volumes[name]
	if v == nil {
		return nil, ErrNotFound
	}
	if v.NodeID != nodeID {
		return nil, errors.New("VOLUME_NODE_MISMATCH")
	}
	if n := s.Nodes[nodeID]; n == nil || n.Revoked {
		return nil, errors.New("VOLUME_NODE_NOT_AUTHORIZED")
	}
	for _, a := range s.Allocations {
		for _, ref := range a.Spec.Volumes {
			if ref.Name == name && a.Phase != "stopped" {
				return nil, errors.New("VOLUME_HAS_UNCONFIRMED_EXECUTION")
			}
		}
	}
	for _, w := range s.Workloads {
		for _, ref := range w.Spec.Volumes {
			if ref.Name == name && !w.Paused {
				return nil, errors.New("VOLUME_WORKLOAD_MUST_BE_PAUSED")
			}
		}
	}
	return v, nil
}
