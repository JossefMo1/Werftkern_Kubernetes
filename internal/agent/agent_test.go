package agent

import (
	"context"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"path/filepath"
	"strings"
	"testing"
)

type fakeEngine struct {
	items         map[string]bool
	starts, stops int
}

func (f *fakeEngine) Health(context.Context) error { return nil }
func (f *fakeEngine) Owned(context.Context) ([]string, error) {
	r := []string{}
	for id := range f.items {
		r = append(r, id)
	}
	return r, nil
}
func (f *fakeEngine) Stop(_ context.Context, id string) error {
	if f.items[id] {
		delete(f.items, id)
		f.stops++
	}
	return nil
}
func (f *fakeEngine) Ensure(_ context.Context, a model.Allocation, _ string, allowed func() bool) (model.Report, error) {
	if !allowed() {
		return model.Report{}, errors.New("stale")
	}
	if !f.items[a.ID] {
		f.items[a.ID] = true
		f.starts++
	}
	return model.Report{ID: a.ID, Phase: "ready"}, nil
}
func makeAgent(t *testing.T) (*Agent, *fakeEngine, model.AssignmentSnapshot) {
	t.Helper()
	f := &fakeEngine{items: map[string]bool{}}
	c := config.Agent{Client: config.Client{ClusterID: model.ID()}, NodeID: model.ID(), InstanceID: model.ID(), Address: "127.0.0.1", Journal: filepath.Join(t.TempDir(), "journal.json")}
	a, e := New(c, nil, f)
	if e != nil {
		t.Fatal(e)
	}
	s := model.AssignmentSnapshot{ClusterID: c.Client.ClusterID, Revision: 5, Allocations: []model.Allocation{{ID: model.ID(), NodeID: c.NodeID, Generation: 1, Desired: "run", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 32}}}}
	return a, f, s
}
func TestAgentReplaysAndRecoversDurableJournal(t *testing.T) {
	a, f, s := makeAgent(t)
	if e := a.Accept(s); e != nil {
		t.Fatal(e)
	}
	for i := 0; i < 2; i++ {
		if e := a.ReconcileOnce(context.Background()); e != nil {
			t.Fatal(e)
		}
	}
	restarted, e := New(a.Config, nil, f)
	if e != nil {
		t.Fatal(e)
	}
	if e = restarted.ReconcileOnce(context.Background()); e != nil {
		t.Fatal(e)
	}
	if f.starts != 1 || len(f.items) != 1 {
		t.Fatal("duplicated local workload")
	}
}
func TestJournalFailurePreventsNewExecution(t *testing.T) {
	a, f, s := makeAgent(t)
	a.Persist = func(Journal) error { return errors.New("disk full") }
	if a.Accept(s) == nil {
		t.Fatal("accepted nondurable intent")
	}
	a.ReconcileOnce(context.Background())
	if f.starts != 0 {
		t.Fatal("ran unjournaled work")
	}
}
func TestAgentRefusesScopeRollbackDuplicatesAndPorts(t *testing.T) {
	for _, kind := range []string{"cluster", "node", "revision", "duplicate", "port", "image"} {
		t.Run(kind, func(t *testing.T) {
			a, _, s := makeAgent(t)
			a.Accept(s)
			switch kind {
			case "cluster":
				s.ClusterID = model.ID()
			case "node":
				s.Allocations[0].NodeID = model.ID()
			case "revision":
				s.Revision--
			case "duplicate":
				s.Allocations = append(s.Allocations, s.Allocations[0])
			case "port":
				s.Allocations[0].Spec.Port = 8080
				s.Allocations[0].Spec.ReadinessPath = "/"
				s.Allocations[0].HostPort = 80
			case "image":
				s.Allocations[0].Spec.Image = "nginx:latest"
			}
			if a.Accept(s) == nil {
				t.Fatal("invalid assignment accepted")
			}
		})
	}
}
func TestAgentNeverGarbageCollectsBeforeTrustedSnapshot(t *testing.T) {
	a, f, s := makeAgent(t)
	f.items[s.Allocations[0].ID] = true
	a.ReconcileOnce(context.Background())
	if f.stops != 0 {
		t.Fatal("premature cleanup")
	}
}
func TestAgentStopsOwnedOrphansAndAcknowledgesStop(t *testing.T) {
	a, f, s := makeAgent(t)
	orphan := model.ID()
	f.items[orphan] = true
	a.Accept(s)
	a.ReconcileOnce(context.Background())
	if f.items[orphan] || f.starts != 1 {
		t.Fatal("orphan remains")
	}
	s.Revision++
	s.Allocations[0].Desired = "stop"
	a.Accept(s)
	a.ReconcileOnce(context.Background())
	if len(f.items) != 0 || a.reports[s.Allocations[0].ID].Phase != "stopped" {
		t.Fatal("stop not reported")
	}
}
func TestAgentOfflineUsesLastAcceptedSnapshot(t *testing.T) {
	a, f, s := makeAgent(t)
	a.Accept(s)
	a.ReconcileOnce(context.Background())
	delete(f.items, s.Allocations[0].ID)
	a.ReconcileOnce(context.Background())
	if f.starts != 2 {
		t.Fatal("last known state not reconciled")
	}
}
func TestAgentWrongClusterJournalRejected(t *testing.T) {
	a, f, s := makeAgent(t)
	a.Accept(s)
	c := a.Config
	c.Client.ClusterID = model.ID()
	if _, e := New(c, nil, f); e == nil {
		t.Fatal("foreign journal used")
	}
}

func TestAgentSameRevisionContentAndAllocationIdentityImmutable(t *testing.T) {
	for _, change := range []string{"revision-content", "generation", "spec", "stop-resurrection"} {
		t.Run(change, func(t *testing.T) {
			a, _, snap := makeAgent(t)
			if change == "stop-resurrection" {
				snap.Allocations[0].Desired = "stop"
			}
			if e := a.Accept(snap); e != nil {
				t.Fatal(e)
			}
			switch change {
			case "revision-content":
				snap.Allocations[0].Desired = "stop"
			case "generation":
				snap.Revision++
				snap.Allocations[0].Generation++
			case "spec":
				snap.Revision++
				snap.Allocations[0].Spec.CPUMilli++
			case "stop-resurrection":
				snap.Revision++
				snap.Allocations[0].Desired = "run"
			}
			if e := a.Accept(snap); e == nil {
				t.Fatal("identity/revision replay bypass")
			}
		})
	}
}
