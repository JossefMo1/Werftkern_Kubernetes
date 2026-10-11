package control

import (
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"sort"
	"time"
)

func allocated(s *model.State, w *model.Workload) []*model.Allocation {
	out := []*model.Allocation{}
	for _, id := range model.SortedKeys(s.Allocations) {
		a := s.Allocations[id]
		if a.WorkloadUID == w.UID && a.Phase != "stopped" {
			out = append(out, a)
		}
	}
	return out
}
func isReady(s *model.State, a *model.Allocation, now time.Time) bool {
	n := s.Nodes[a.NodeID]
	return n != nil && n.Ready(now) && a.Desired == "run" && a.Phase == "ready" && model.FreshObservation(a.UpdatedAt, now)
}
func stop(s *model.State, a *model.Allocation, now time.Time) {
	if a.Desired != "stop" {
		a.Desired = "stop"
		a.UpdatedAt = now
		s.Event("allocation.stop", a.ID, now)
	}
}

// Reconcile uses the same persisted transaction as admissions and heartbeats.
// Offline nodes retain reservations. No partition can silently move a workload.
func Reconcile(s *model.State, now time.Time) error {
	return reconcileSelected(s, now, nil, false)
}

// A non-nil scope permits only explicitly selected workload reconciliation.
// Used by the authenticated maintenance drain transaction, never by a worker.
func reconcileSelected(s *model.State, now time.Time, scope map[string]bool, maintenanceDrain bool) error {
	for id, a := range s.Allocations {
		if a.Desired == "stop" && a.Phase == "stopped" {
			delete(s.Allocations, id)
		}
	}
	for _, name := range model.SortedKeys(s.Workloads) {
		w := s.Workloads[name]
		if scope != nil && !scope[w.UID] {
			continue
		}
		all := allocated(s, w)
		if w.Deleting || w.Spec.Replicas == 0 {
			for _, a := range all {
				stop(s, a, now)
			}
			if len(all) == 0 {
				if w.Deleting {
					delete(s.Workloads, name)
					s.Event("workload.deleted", name, now)
				} else {
					w.Phase = "scaled-down"
					w.Reason = ""
				}
			}
			continue
		}
		if w.Paused {
			for _, a := range all {
				stop(s, a, now)
			}
			w.Phase = "pausing"
			w.Reason = "WAITING_FOR_OWNERS_TO_CONFIRM_STOP_NOT_A_FENCING_GUARANTEE"
			if len(all) == 0 {
				w.Phase = "paused"
				w.Reason = ""
			}
			continue
		}
		// Revocation and loss of contact are not fencing. Never start a replacement
		// unless the application explicitly tolerates concurrent executions. Keep
		// every old allocation/reservation until the original owner confirms stop.
		unknownOwner := false
		for _, allocation := range all {
			n := s.Nodes[allocation.NodeID]
			if n == nil || !n.Ready(now) {
				if w.Spec.ReplacementPolicy == "duplicate-safe" && len(allocation.Spec.Volumes) == 0 && allocation.Spec.Profile == "" {
					stop(s, allocation, now)
				} else {
					unknownOwner = true
				}
			}
		}
		if unknownOwner {
			w.Phase, w.Reason = "blocked", "NODE_UNKNOWN_RESERVATION_RETAINED"
			continue
		}
		// Exclusive local storage uses stop-then-start, never a surge writer.
		if s.MaintenanceID != "" && !maintenanceDrain {
			continue
		} // Existing processes continue; no new binding during host changes.
		hasStorage := len(w.Spec.Volumes) > 0
		for _, a := range all {
			if len(a.Spec.Volumes) > 0 {
				hasStorage = true
			}
		}
		if hasStorage {
			retiring := false
			for _, a := range all {
				if a.Generation != w.Generation || a.Desired == "stop" {
					stop(s, a, now)
					retiring = true
				}
			}
			if retiring {
				w.Phase = "updating"
				w.Reason = "VOLUME_WAITING_FOR_CONFIRMED_STOP"
				continue
			}
			if n := s.Nodes[w.Spec.Node]; n != nil && n.Drain {
				w.Phase = "blocked"
				w.Reason = "LOCAL_VOLUME_DRAIN_REQUIRES_PAUSE_BACKUP_OR_MIGRATION"
				continue
			}
		}
		cur, old := []*model.Allocation{}, []*model.Allocation{}
		ready := 0
		running := 0
		for _, a := range all {
			if isReady(s, a, now) {
				ready++
			}
			if a.Desired != "run" {
				continue
			}
			running++
			n := s.Nodes[a.NodeID]
			if a.Generation == w.Generation && n != nil && !n.Drain && !n.Revoked {
				cur = append(cur, a)
			} else {
				old = append(old, a)
			}
		}
		if len(cur) > w.Spec.Replicas {
			for _, a := range cur[w.Spec.Replicas:] {
				stop(s, a, now)
			}
			cur = cur[:w.Spec.Replicas]
		}
		w.Reason = ""
		w.Phase = "pending"
		// One extra allocation is the fixed surge budget. Stopping allocations still
		// reserve CPU, memory and ports until acknowledged stopped by their owner.
		if len(cur) < w.Spec.Replicas && running < w.Spec.Replicas+1 {
			if len(s.Allocations) >= model.MaxAllocations {
				w.Phase = "blocked"
				w.Reason = "ALLOCATION_LIMIT"
			} else if n, port := choose(s, w, now); n != nil {
				a := &model.Allocation{ID: model.ID(), WorkloadUID: w.UID, Name: w.Name, Generation: w.Generation, NodeID: n.ID, Spec: w.Spec, HostPort: port, Desired: "run", Phase: "assigned", CreatedAt: now, UpdatedAt: now}
				s.Allocations[a.ID] = a
				cur = append(cur, a)
				s.Event("allocation.assigned", a.ID, now)
			} else {
				w.Phase = "blocked"
				w.Reason = "NO_HEALTHY_NODE_WITH_CAPACITY_OR_SURGE_SPACE"
			}
		}
		// Retire an old revision/draining node only when target availability survives.
		for _, a := range old {
			remaining := ready
			if isReady(s, a, now) {
				remaining--
			}
			if remaining >= w.Spec.Replicas {
				stop(s, a, now)
				break
			}
		}
		currentReady := 0
		for _, a := range cur {
			if isReady(s, a, now) {
				currentReady++
			}
		}
		if currentReady >= w.Spec.Replicas && len(old) == 0 {
			w.Phase = "ready"
			w.Reason = ""
		} else if w.Phase != "blocked" && len(old) > 0 {
			w.Phase = "updating"
		}
		for _, a := range cur {
			n := s.Nodes[a.NodeID]
			if n == nil || !n.Ready(now) {
				w.Phase = "blocked"
				w.Reason = "NODE_UNKNOWN_RESERVATION_RETAINED"
				break
			}
			if a.Phase == "failed" {
				w.Phase = "degraded"
				w.Reason = a.Reason
			}
		}
	}
	return s.Validate()
}
func choose(s *model.State, w *model.Workload, now time.Time) (*model.Node, int) {
	type candidate struct {
		n           *model.Node
		port, count int
		cpu         int64
	}
	cs := []candidate{}
	for _, id := range model.SortedKeys(s.Nodes) {
		n := s.Nodes[id]
		if !n.Ready(now) || n.Drain || w.Spec.Node != "" && w.Spec.Node != id {
			continue
		}
		var cpu, mem int64
		count := 0
		ports := map[int]bool{}
		for _, a := range s.Allocations {
			if a.NodeID == id && a.Phase != "stopped" {
				cpu += a.Spec.CPUMilli
				mem += a.Spec.MemoryMiB
				ports[a.HostPort] = true
				if a.WorkloadUID == w.UID {
					count++
				}
			}
		}
		if cpu+w.Spec.CPUMilli > n.CPUMilli || mem+w.Spec.MemoryMiB > n.MemoryMiB {
			continue
		}
		port := 0
		if w.Spec.Port > 0 {
			for p := 22000; p < 23000; p++ {
				if !ports[p] {
					port = p
					break
				}
			}
			if port == 0 {
				continue
			}
		}
		cs = append(cs, candidate{n, port, count, cpu})
	}
	sort.Slice(cs, func(i, j int) bool {
		a, b := cs[i], cs[j]
		if a.count != b.count {
			return a.count < b.count
		}
		if a.cpu != b.cpu {
			return a.cpu < b.cpu
		}
		return a.n.ID < b.n.ID
	})
	if len(cs) == 0 {
		return nil, 0
	}
	return cs[0].n, cs[0].port
}
