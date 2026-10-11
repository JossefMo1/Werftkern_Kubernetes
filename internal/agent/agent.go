package agent

import (
	"context"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/engine"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"log"
	"os"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Journal struct {
	HeartbeatSequence uint64                      `json:"heartbeatSequence,omitempty"`
	ClusterID         string                      `json:"clusterId"`
	Revision          int64                       `json:"revision"`
	Allocations       map[string]model.Allocation `json:"allocations"`
}
type failure struct {
	Count int
	Until time.Time
}
type Agent struct {
	Config   config.Agent
	Client   *apiclient.Client
	Engine   engine.Runtime
	mu       sync.Mutex
	journal  Journal
	reports  map[string]model.Report
	failures map[string]failure
	Persist  func(Journal) error
}

func New(c config.Agent, cl *apiclient.Client, eng engine.Runtime) (*Agent, error) {
	a := &Agent{Config: c, Client: cl, Engine: eng, reports: map[string]model.Report{}, failures: map[string]failure{}, journal: Journal{ClusterID: c.Client.ClusterID, Allocations: map[string]model.Allocation{}}}
	if !model.ValidID(c.NodeID) || !model.ValidID(c.InstanceID) || !model.PrivateAddress(c.Address) {
		return nil, errors.New("AGENT_CONFIGURATION_INVALID")
	}
	if e := safefile.ReadJSON(c.Journal, &a.journal); e != nil && !os.IsNotExist(e) {
		return nil, e
	}
	if a.journal.ClusterID != c.Client.ClusterID || a.journal.Allocations == nil {
		return nil, errors.New("JOURNAL_CLUSTER_MISMATCH")
	}
	a.Persist = func(j Journal) error { return safefile.JSON(c.Journal, j, 0600) }
	return a, nil
}
func Capacity() (int64, int64) {
	cpu := int64(runtime.NumCPU())*1000 - 250
	if cpu < 100 {
		cpu = 100
	}
	mem := int64(512)
	b, e := os.ReadFile("/proc/meminfo")
	if e == nil {
		for _, l := range strings.Split(string(b), "\n") {
			if strings.HasPrefix(l, "MemTotal:") {
				f := strings.Fields(l)
				if len(f) >= 2 {
					kb, _ := strconv.ParseInt(f[1], 10, 64)
					mem = kb/1024 - 512
				}
			}
		}
	}
	if mem < 64 {
		mem = 64
	}
	return cpu, mem
}
func (a *Agent) Accept(snapshot model.AssignmentSnapshot) error {
	a.mu.Lock()
	defer a.mu.Unlock()
	if snapshot.ClusterID != a.journal.ClusterID {
		return errors.New("ASSIGNMENT_CLUSTER_MISMATCH")
	}
	if snapshot.Revision < a.journal.Revision {
		return errors.New("ASSIGNMENT_REVISION_ROLLBACK_BLOCKED")
	}
	if len(snapshot.Allocations) > model.MaxAllocations {
		return errors.New("ASSIGNMENT_LIMIT")
	}
	j := Journal{HeartbeatSequence: a.journal.HeartbeatSequence, ClusterID: snapshot.ClusterID, Revision: snapshot.Revision, Allocations: map[string]model.Allocation{}}
	for _, x := range snapshot.Allocations {
		if x.NodeID != a.Config.NodeID || !model.ValidID(x.ID) || (x.Desired != "run" && x.Desired != "stop") {
			return errors.New("ASSIGNMENT_SCOPE_INVALID")
		}
		if x.Spec.Port > 0 && (x.HostPort < 22000 || x.HostPort >= 23000) || x.Spec.Port == 0 && x.HostPort != 0 {
			return errors.New("ASSIGNMENT_PORT_INVALID")
		}
		if err := x.Spec.Validate(); err != nil {
			return err
		}
		if _, exists := j.Allocations[x.ID]; exists {
			return errors.New("DUPLICATE_ALLOCATION")
		}
		j.Allocations[x.ID] = x
	}
	if j.Revision == a.journal.Revision && model.Hash(j) != model.Hash(a.journal) {
		return errors.New("ASSIGNMENT_SAME_REVISION_DIFFERENT_CONTENT")
	}
	for id, x := range j.Allocations {
		if old, ok := a.journal.Allocations[id]; ok {
			if old.Generation != x.Generation || old.WorkloadUID != x.WorkloadUID || model.Hash(old.Spec) != model.Hash(x.Spec) || old.Desired == "stop" && x.Desired == "run" {
				return errors.New("ALLOCATION_IDENTITY_REUSE_BLOCKED")
			}
		}
	}
	// Intention must be durable before the executor can observe a new assignment.
	if err := a.Persist(j); err != nil {
		return errors.New("JOURNAL_WRITE_FAILED")
	}
	a.journal = j
	for id := range a.reports {
		if _, ok := j.Allocations[id]; !ok {
			delete(a.reports, id)
			delete(a.failures, id)
		}
	}
	return nil
}
func (a *Agent) HeartbeatOnce(ctx context.Context) error {
	cpu, mem := Capacity()
	healthy := a.Engine.Health(ctx) == nil
	a.mu.Lock()
	// The durable sequence survives process/host restart; a failed write prevents
	// sending a heartbeat that could reuse an already acknowledged sequence.
	next := a.journal
	if next.HeartbeatSequence == ^uint64(0) {
		a.mu.Unlock()
		return errors.New("HEARTBEAT_SEQUENCE_EXHAUSTED")
	}
	next.HeartbeatSequence++
	if err := a.Persist(next); err != nil {
		a.mu.Unlock()
		return errors.New("JOURNAL_WRITE_FAILED")
	}
	a.journal = next
	sequence := next.HeartbeatSequence
	reports := make([]model.Report, 0, len(a.reports))
	for _, r := range a.reports {
		reports = append(reports, r)
	}
	a.mu.Unlock()
	req := model.Heartbeat{Sequence: sequence, InstanceID: a.Config.InstanceID, CPUMilli: cpu, MemoryMiB: mem, Healthy: healthy, Version: model.Version, Reports: reports}
	var out model.AssignmentSnapshot
	if err := a.Client.Call(ctx, "POST", "/v1/heartbeat", req, &out, ""); err != nil {
		return err
	}
	return a.Accept(out)
}
func (a *Agent) desired(x model.Allocation) bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	current, ok := a.journal.Allocations[x.ID]
	return ok && current.Desired == "run" && model.Hash(current.Spec) == model.Hash(x.Spec) && current.Generation == x.Generation
}
func (a *Agent) record(r model.Report, e error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if e != nil {
		r.Phase = "failed"
		r.Reason = "ENGINE_OPERATION_FAILED"
		if e == engine.ErrStale {
			r.Reason = "ALLOCATION_SUPERSEDED"
		}
		f := a.failures[r.ID]
		f.Count++
		seconds := 1 << min(f.Count, 8)
		f.Until = time.Now().Add(time.Duration(seconds) * time.Second)
		a.failures[r.ID] = f
	} else {
		delete(a.failures, r.ID)
	}
	r.ObservedAt = time.Now().UTC()
	a.reports[r.ID] = r
}
func (a *Agent) ReconcileOnce(ctx context.Context) error {
	a.mu.Lock()
	j := a.journal
	items := make([]model.Allocation, 0, len(j.Allocations))
	for _, id := range model.SortedKeys(j.Allocations) {
		items = append(items, j.Allocations[id])
	}
	a.mu.Unlock()
	if j.Revision == 0 {
		return nil
	} // Never garbage-collect before one trusted snapshot.
	ids, err := a.Engine.Owned(ctx)
	if err != nil {
		return err
	}
	for _, id := range ids {
		a.mu.Lock()
		x, exists := a.journal.Allocations[id]
		remove := !exists || x.Desired == "stop"
		a.mu.Unlock()
		if remove {
			op, cancel := context.WithTimeout(ctx, 30*time.Second)
			err := a.Engine.Stop(op, id)
			cancel()
			if exists {
				r := model.Report{ID: id, Phase: "stopped"}
				a.record(r, err)
			}
			if err != nil {
				return err
			}
		}
	}
	for _, x := range items {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		if x.Desired == "stop" {
			op, cancel := context.WithTimeout(ctx, 30*time.Second)
			e := a.Engine.Stop(op, x.ID)
			cancel()
			a.record(model.Report{ID: x.ID, Phase: "stopped"}, e)
			continue
		}
		a.mu.Lock()
		f := a.failures[x.ID]
		a.mu.Unlock()
		if time.Now().Before(f.Until) {
			continue
		}
		if !a.desired(x) {
			continue
		}
		op, cancel := context.WithTimeout(ctx, 3*time.Minute)
		r, e := a.Engine.Ensure(op, x, a.Config.Address, func() bool { return a.desired(x) })
		cancel()
		a.record(r, e)
	}
	return nil
}
func (a *Agent) Run(ctx context.Context) error {
	// Heartbeats run independently from slow image pulls; a pull cannot make a
	// healthy node disappear. The single executor serializes local mutations.
	done := make(chan struct{})
	go func() {
		defer close(done)
		t := time.NewTicker(3 * time.Second)
		defer t.Stop()
		for {
			if e := a.HeartbeatOnce(ctx); e != nil && ctx.Err() == nil {
				log.Print("heartbeat_failed; keeping last durable desired state")
			}
			select {
			case <-ctx.Done():
				return
			case <-t.C:
			}
		}
	}()
	t := time.NewTicker(2 * time.Second)
	defer t.Stop()
	for {
		if e := a.ReconcileOnce(ctx); e != nil && ctx.Err() == nil {
			log.Print("agent_reconcile_failed; inspect local daemon and journal")
		}
		select {
		case <-ctx.Done():
			<-done
			return nil
		case <-t.C:
		}
	}
}
