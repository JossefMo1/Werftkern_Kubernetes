package recovery

import (
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"strings"
	"testing"
	"time"
)

func TestStatefulRestoreNeedsExplicitNewNodeAndVolume(t *testing.T) {
	now := time.Now()
	s := model.NewState(model.ID(), "old", now)
	oldNode, newNode := model.ID(), model.ID()
	oldUID := model.ID()
	spec := model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 64, Node: oldNode, Volumes: []model.VolumeRef{{Name: "old-data", MountPath: "/data/app"}}}
	s.Nodes[oldNode] = &model.Node{ID: oldNode, Name: "old-node", Address: "10.1.0.1"}
	s.Workloads["app"] = &model.Workload{UID: oldUID, Name: "app", Generation: 1, Spec: spec}
	s.Volumes = map[string]*model.Volume{"old-data": {ID: model.ID(), Name: "old-data", NodeID: oldNode, UID: 65532, GID: 65532, Owner: oldUID, Initialized: true}}
	sealed, e := Seal(s, 1, make([]byte, 32), make([]byte, 32), now)
	if e != nil {
		t.Fatal(e)
	}
	b, e := Open(sealed, make([]byte, 32))
	if e != nil {
		t.Fatal(e)
	}
	target := model.NewState(model.ID(), "new", now)
	target.Nodes[newNode] = &model.Node{ID: newNode, Name: "new-node", Address: "10.2.0.1"}
	target.Volumes = map[string]*model.Volume{"new-data": {ID: model.ID(), Name: "new-data", NodeID: newNode, UID: 65532, GID: 65532}}
	if _, e = PrepareRestore(b, target, make([]byte, 32), now); e == nil {
		t.Fatal("unmapped volume restored")
	}
	restored, e := PrepareRestoreMapped(b, target, make([]byte, 32), now, RestoreMapping{Nodes: map[string]string{oldNode: newNode}, Volumes: map[string]string{"old-data": "new-data"}})
	if e != nil {
		t.Fatal(e)
	}
	w := restored.Workloads["app"]
	if !w.Paused || w.UID == oldUID || w.Spec.Node != newNode || w.Spec.Volumes[0].Name != "new-data" || len(restored.Allocations) != 0 {
		t.Fatal("unsafe restore")
	}
	if restored.Volumes["new-data"].Owner != w.UID {
		t.Fatal("owner mapping")
	}
	if restored.Volumes["new-data"].Initialized {
		t.Fatal("pretended data restore")
	}
}
