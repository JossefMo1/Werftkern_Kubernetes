package model

import (
	"strings"
	"testing"
	"time"
)

func TestRestorePendingPreventsResumeAndEmptyReplacement(t *testing.T) {
	s := NewState(ID(), "restore-test", time.Now())
	s.Volumes = map[string]*Volume{}
	n := ID()
	s.Nodes[n] = &Node{ID: n, Name: "worker", Address: "127.0.0.2", CPUMilli: 4000, MemoryMiB: 4096}
	v := &Volume{ID: ID(), Name: "data", NodeID: n, UID: 65532, GID: 65532, Initialized: true, RestoreID: ID(), RestoreHash: strings.Repeat("a", 64)}
	s.Volumes["data"] = v
	spec := Spec{Image: "sha256:" + strings.Repeat("b", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 64, Node: n, Volumes: []VolumeRef{{Name: "data", MountPath: "/data/app"}}}
	w := &Workload{UID: ID(), Name: "db", Generation: 1, Spec: spec, Paused: true}
	v.Owner = w.UID
	s.Workloads[w.Name] = w
	if e := s.ValidateInventory(); e != nil {
		t.Fatal("paused pending restore invalid", e)
	}
	if _, e := MutateWorkload(s, w.Name, "resume", ID(), 1, time.Now()); e == nil {
		t.Fatal("resume before data acknowledgement")
	}
	v.RestoreComplete = true
	if _, e := MutateWorkload(s, w.Name, "resume", ID(), 1, time.Now()); e != nil {
		t.Fatal(e)
	}
}
