package control

import (
	"testing"
	"time"
)

// A fresh node heartbeat is not fresh application health. A failed/paused
// executor can keep heartbeating while its last successful probe ages out.
func TestReadinessExpiresEvenWhenNodeStillHeartbeats(t *testing.T) {
	s, now := base(t, 2, 1)
	settle(t, s, now, 3)
	var allocationID string
	for id := range s.Allocations {
		allocationID = id
	}
	later := now.Add(31 * time.Second)
	for _, n := range s.Nodes {
		n.LastSeen = later
	}
	if isReady(s, s.Allocations[allocationID], later) {
		t.Fatal("stale probe counted as ready despite healthy node")
	}
}

func TestStaleSurgeCannotRetireHealthyOldReplica(t *testing.T) {
	s, now := base(t, 2, 1)
	settle(t, s, now, 3)
	w := s.Workloads["demo"]
	var oldID string
	for id := range s.Allocations {
		oldID = id
	}
	w.Generation++
	if e := Reconcile(s, now); e != nil {
		t.Fatal(e)
	}
	later := now.Add(31 * time.Second)
	for _, n := range s.Nodes {
		n.LastSeen = later
	}
	s.Allocations[oldID].UpdatedAt = later
	for id, a := range s.Allocations {
		if id != oldID {
			a.Phase = "ready"
			a.UpdatedAt = now
		}
	}
	if e := Reconcile(s, later); e != nil {
		t.Fatal(e)
	}
	if s.Allocations[oldID].Desired != "run" {
		t.Fatal("stale surge caused healthy old replica to stop")
	}
}
