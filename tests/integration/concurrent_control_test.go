package integration

import (
	"context"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/control"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/store"
	"github.com/ClusterPilot-System/werftkern/internal/testutil"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

// Three independent store clients and reconcilers share one atomic fixture.
// This tests optimistic concurrency, NOT actual etcd quorum availability.
func TestThreeConcurrentControllersDoNotDoubleAllocate(t *testing.T) {
	f := testutil.NewEtcd(t, filepath.Join(t.TempDir(), "state.json"))
	id := model.ID()
	now := time.Now()
	s := model.NewState(id, "ha-lab", now)
	for i := 1; i <= 3; i++ {
		n := model.ID()
		s.Nodes[n] = &model.Node{ID: n, Name: fmt.Sprintf("node-%d", i), Address: fmt.Sprintf("10.10.0.%d", i), CPUMilli: 4000, MemoryMiB: 4096, Healthy: true, LastSeen: now}
	}
	q := model.ApplyRequest{APIVersion: model.APIVersion, Name: "web", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 9, CPUMilli: 100, MemoryMiB: 32}}
	model.Apply(s, q, model.ID(), now)
	first := store.NewEtcd(f.URL(), f.Server.Client(), id)
	if e := first.Initialize(context.Background(), s); e != nil {
		t.Fatal(e)
	}
	var wg sync.WaitGroup
	errs := make(chan error, 3)
	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			db := store.NewEtcd(f.URL(), f.Server.Client(), id)
			for j := 0; j < 12; j++ {
				if _, _, e := db.Update(context.Background(), func(s *model.State) error { return control.Reconcile(s, now) }); e != nil {
					errs <- e
					return
				}
			}
		}()
	}
	wg.Wait()
	close(errs)
	for e := range errs {
		t.Fatal(e)
	}
	out, _, e := first.Read(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	if len(out.Allocations) != 9 {
		t.Fatalf("allocations=%d", len(out.Allocations))
	}
	sums := map[string]int64{}
	for _, a := range out.Allocations {
		sums[a.NodeID] += a.Spec.CPUMilli
	}
	for node, cpu := range sums {
		if cpu > out.Nodes[node].CPUMilli {
			t.Fatal("overallocated")
		}
	}
}
