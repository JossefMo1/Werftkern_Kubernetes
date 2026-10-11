package model

import (
	"strings"
	"testing"
	"time"
)

func storageSpec() Spec {
	return Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 64, Node: ID(), Volumes: []VolumeRef{{Name: "data", MountPath: "/data/app"}}}
}
func TestStorageSpecBoundaries(t *testing.T) {
	for _, test := range []string{"replicas", "unpinned", "root", "path", "overlap", "probe"} {
		t.Run(test, func(t *testing.T) {
			s := storageSpec()
			switch test {
			case "replicas":
				s.Replicas = 2
			case "unpinned":
				s.Node = ""
			case "root":
				s.RunAsUID = -1
			case "path":
				s.Volumes[0].MountPath = "/etc"
			case "overlap":
				s.Volumes = append(s.Volumes, VolumeRef{Name: "other", MountPath: "/data/app/nested"})
			case "probe":
				s.Probe = "shell"
			}
			if s.Validate() == nil {
				t.Fatal("invalid spec accepted")
			}
		})
	}
}
func TestVolumeClaimConflictsAcrossWorkloads(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "lab", now)
	spec := storageSpec()
	s.Volumes = map[string]*Volume{"data": {ID: ID(), Name: "data", NodeID: spec.Node, UID: 65532, GID: 65532}}
	q := ApplyRequest{APIVersion: APIVersion, Name: "one", Spec: spec}
	if _, e := Apply(s, q, ID(), now); e != nil {
		t.Fatal(e)
	}
	q.Name = "two"
	if _, e := Apply(s, q, ID(), now); e == nil {
		t.Fatal("second writer admitted")
	}
}
func TestPostgresRequiresOneVolumeAndSecret(t *testing.T) {
	s := storageSpec()
	s.Profile = "postgres17"
	s.Probe = "postgres"
	s.Port = 5432
	s.Volumes[0].MountPath = "/var/lib/postgresql/data"
	if s.Validate() == nil {
		t.Fatal("missing password")
	}
	s.Secrets = []SecretRef{{Name: "postgres-password", Version: 1}}
	if e := s.Validate(); e != nil {
		t.Fatal(e)
	}
}
