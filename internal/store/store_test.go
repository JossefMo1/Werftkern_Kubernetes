package store

import (
	"context"
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/testutil"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func fixture(t *testing.T) (*Etcd, *testutil.EtcdFixture) {
	t.Helper()
	f := testutil.NewEtcd(t, filepath.Join(t.TempDir(), "state.json"))
	e := NewEtcd(f.URL(), f.Server.Client(), model.ID())
	return e, f
}
func TestEtcdInitializeAndRestart(t *testing.T) {
	e, f := fixture(t)
	ctx := context.Background()
	if _, _, err := e.Read(ctx); !errors.Is(err, ErrUninitialized) {
		t.Fatal(err)
	}
	s := model.NewState(e.ClusterID, "test", time.Now())
	if err := e.Initialize(ctx, s); err != nil {
		t.Fatal(err)
	}
	if err := e.Initialize(ctx, s); !errors.Is(err, model.ErrConflict) {
		t.Fatal(err)
	}
	f2 := testutil.NewEtcd(t, f.Path)
	e2 := NewEtcd(f2.URL(), f2.Server.Client(), e.ClusterID)
	out, rev, err := e2.Read(ctx)
	if err != nil || rev != 1 || out.Name != "test" {
		t.Fatal(out, rev, err)
	}
}
func TestMissingStoreNeverAutomaticallyCreated(t *testing.T) {
	e, f := fixture(t)
	_, _, err := e.Update(context.Background(), func(s *model.State) error { s.Name = "other"; return nil })
	if !errors.Is(err, ErrUninitialized) {
		t.Fatal(err)
	}
	_, writes := f.Counts()
	if writes != 0 {
		t.Fatal("silent initialization")
	}
}
func TestWrongClusterIdentityRejected(t *testing.T) {
	e, _ := fixture(t)
	e.Initialize(context.Background(), model.NewState(e.ClusterID, "test", time.Now()))
	e.ClusterID = model.ID()
	if _, _, err := e.Read(context.Background()); err == nil {
		t.Fatal("wrong cluster allowed")
	}
}
func TestCASRetriesConflicts(t *testing.T) {
	e, f := fixture(t)
	e.Initialize(context.Background(), model.NewState(e.ClusterID, "test", time.Now()))
	f.SetReject(3)
	calls := 0
	s, _, err := e.Update(context.Background(), func(s *model.State) error { calls++; s.Name = "renamed"; return nil })
	if err != nil || calls != 4 || s.Name != "renamed" {
		t.Fatal(calls, err)
	}
}
func TestNoopDoesNotWrite(t *testing.T) {
	e, f := fixture(t)
	e.Initialize(context.Background(), model.NewState(e.ClusterID, "test", time.Now()))
	_, _, err := e.Update(context.Background(), func(*model.State) error { return nil })
	_, writes := f.Counts()
	if err != nil || writes != 1 {
		t.Fatal(writes, err)
	}
}
func TestFailedMutationDoesNotCommit(t *testing.T) {
	e, _ := fixture(t)
	e.Initialize(context.Background(), model.NewState(e.ClusterID, "test", time.Now()))
	_, _, err := e.Update(context.Background(), func(s *model.State) error { s.Name = "changed"; return model.ErrConflict })
	if !errors.Is(err, model.ErrConflict) {
		t.Fatal(err)
	}
	s, _, _ := e.Read(context.Background())
	if s.Name != "test" {
		t.Fatal("partial write")
	}
}
func TestConcurrentTransactionsDoNotLoseUpdates(t *testing.T) {
	e, _ := fixture(t)
	state := model.NewState(e.ClusterID, "test", time.Now())
	nodeID := model.ID()
	state.Nodes[nodeID] = &model.Node{ID: nodeID, Name: "worker", Address: "127.0.0.2", MemoryMiB: 64}
	e.Initialize(context.Background(), state)
	var wg sync.WaitGroup
	errs := make(chan error, 12)
	for i := 0; i < 12; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 4; j++ {
				_, _, err := e.Update(context.Background(), func(s *model.State) error { s.Nodes[nodeID].MemoryMiB++; return nil })
				if err != nil {
					errs <- err
					return
				}
			}
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Error(err)
	}
	s, _, err := e.Read(context.Background())
	if err != nil || s.Nodes[nodeID].MemoryMiB != 112 {
		t.Fatal(s, err)
	}
}
func TestStateLimitRejectedBeforeEtcdWrite(t *testing.T) {
	e, _ := fixture(t)
	s := model.NewState(e.ClusterID, "test", time.Now())
	s.Schema = 99
	if err := e.Initialize(context.Background(), s); err == nil {
		t.Fatal("invalid state accepted")
	}
}
