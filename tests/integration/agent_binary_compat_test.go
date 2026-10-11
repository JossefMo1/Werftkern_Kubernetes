//go:build compat_agent

package integration_test

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/control"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/pki"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
	"github.com/ClusterPilot-System/werftkern/internal/store"
	"github.com/ClusterPilot-System/werftkern/internal/testutil"
)

// This launches the ACTUAL previous Git revision executable, not a current
// Agent pretending to be old. TLS, journals and OS processes are real. Docker
// responses and etcd are explicit test adapters; no container/Raft qualification.
func TestPreviousAgentBinaryUpgradeRetainsJournalAndAllocation(t *testing.T) {
	previous, current := os.Getenv("WERFT_PREVIOUS_BINARY"), os.Getenv("WERFT_CURRENT_BINARY")
	for path, want := range map[string]string{previous: "0.2.0-dev.3", current: model.Version} {
		if path == "" {
			t.Fatal("both actual binary paths required; test was not executed")
		}
		b, e := exec.Command(path, "version").Output()
		if e != nil || !strings.HasPrefix(string(b), "Werftkern "+want+"\n") {
			t.Fatalf("wrong binary: %s %v", path, e)
		}
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	dir, e := os.MkdirTemp("", "wk-compat-")
	if e != nil {
		t.Fatal(e)
	}
	defer os.RemoveAll(dir)
	cluster, node, instance := model.ID(), model.ID(), model.ID()
	state := model.NewState(cluster, "compat", time.Now())
	state.Nodes[node] = &model.Node{ID: node, Name: "worker", Address: "127.0.0.1"}
	spec := model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 100, MemoryMiB: 64}
	if _, e = model.Apply(state, model.ApplyRequest{APIVersion: model.APIVersion, Name: "web", Spec: spec}, model.ID(), time.Now()); e != nil {
		t.Fatal(e)
	}
	etcd := testutil.NewEtcd(t, filepath.Join(dir, "state.json"))
	db := store.NewEtcd(etcd.URL(), etcd.Server.Client(), cluster)
	if e = db.Initialize(ctx, state); e != nil {
		t.Fatal(e)
	}
	api := &control.API{Store: db, ClusterID: cluster}
	tls := testutil.NewTLS(t, cluster, api.Handler())
	pair, e := pki.Issue(tls.CA, "node:"+node, cluster, nil, false, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	for name, b := range map[string][]byte{"ca": tls.CA.Cert, "cert": pair.Cert, "key": pair.Key} {
		if e = os.WriteFile(filepath.Join(dir, name), b, 0600); e != nil {
			t.Fatal(e)
		}
	}
	socket := filepath.Join(dir, "docker.sock")
	var mu sync.Mutex
	var container map[string]any
	created, started, deleted := 0, 0, 0
	fixture := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		path := strings.TrimPrefix(r.URL.Path, "/v1.51")
		switch {
		case path == "/version":
			fmt.Fprint(w, `{"ApiVersion":"1.51","MinAPIVersion":"1.41"}`)
		case path == "/info":
			fmt.Fprint(w, `{}`)
		case strings.HasPrefix(path, "/images/"):
			fmt.Fprint(w, `{"Config":{"Volumes":{}}}`)
		case path == "/containers/create":
			if container != nil {
				http.Error(w, "duplicate", 409)
				return
			}
			var body map[string]any
			if json.NewDecoder(r.Body).Decode(&body) != nil {
				http.Error(w, "bad body", 400)
				return
			}
			container = map[string]any{"Id": "test-adapter", "Config": map[string]any{"Labels": body["Labels"]}, "State": map[string]any{"Running": false}}
			created++
			w.WriteHeader(201)
			fmt.Fprint(w, `{"Id":"test-adapter"}`)
		case path == "/containers/json":
			if container == nil {
				fmt.Fprint(w, `[]`)
			} else {
				json.NewEncoder(w).Encode([]any{container["Config"]})
			}
		case strings.HasSuffix(path, "/json"):
			if container == nil {
				http.NotFound(w, r)
			} else {
				json.NewEncoder(w).Encode(container)
			}
		case strings.HasSuffix(path, "/start"):
			if container == nil {
				http.NotFound(w, r)
				return
			}
			container["State"].(map[string]any)["Running"] = true
			started++
			w.WriteHeader(204)
		case strings.HasSuffix(path, "/stop"):
			if container != nil {
				container["State"].(map[string]any)["Running"] = false
			}
			w.WriteHeader(204)
		case r.Method == "DELETE":
			container = nil
			deleted++
			w.WriteHeader(204)
		default:
			http.NotFound(w, r)
		}
	})}
	listener, e := net.Listen("unix", socket)
	if e != nil {
		t.Fatal(e)
	}
	go fixture.Serve(listener)
	defer fixture.Close()
	cfg := config.Agent{Client: config.Client{Server: tls.Server.URL, CA: dir + "/ca", Cert: dir + "/cert", Key: dir + "/key", ClusterID: cluster}, NodeID: node, InstanceID: instance, Address: "127.0.0.1", Socket: socket, Journal: dir + "/journal.json"}
	if e = safefile.JSON(dir+"/agent.json", cfg, 0600); e != nil {
		t.Fatal(e)
	}
	go api.RunReconciler(ctx)
	var running *exec.Cmd
	stop := func() {
		if running != nil {
			running.Process.Kill()
			running.Wait()
			running = nil
		}
	}
	defer stop()
	start := func(path string) {
		running = exec.Command(path, "agent", "--config", dir+"/agent.json")
		log, e := os.OpenFile(dir+"/agent.log", os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
		if e != nil {
			t.Fatal(e)
		}
		running.Stdout = log
		running.Stderr = log
		if e = running.Start(); e != nil {
			log.Close()
			t.Fatal(e)
		}
		log.Close()
	}
	wait := func(check func(*model.State) bool) *model.State {
		deadline := time.Now().Add(35 * time.Second)
		for time.Now().Before(deadline) {
			s, _, e := db.Read(ctx)
			if e == nil && check(s) {
				return s
			}
			time.Sleep(100 * time.Millisecond)
		}
		b, _ := os.ReadFile(dir + "/agent.log")
		t.Fatalf("protocol condition failed; child log: %s", b)
		return nil
	}
	start(previous)
	first := wait(func(s *model.State) bool {
		if s.Nodes[node].Version != "0.2.0-dev.3" {
			return false
		}
		for _, a := range s.Allocations {
			if a.Phase == "ready" {
				return true
			}
		}
		return false
	})
	sequence := first.Nodes[node].HeartbeatSequence
	allocationID := model.SortedKeys(first.Allocations)[0]
	stop()
	start(current)
	latest := wait(func(s *model.State) bool {
		return s.Nodes[node].Version == model.Version && s.Nodes[node].HeartbeatSequence > sequence && s.Allocations[allocationID] != nil && s.Allocations[allocationID].Phase == "ready"
	})
	if latest.Nodes[node].InstanceID != instance {
		t.Fatal("node identity changed")
	}
	mu.Lock()
	c, st := created, started
	mu.Unlock()
	if c != 1 || st != 1 {
		t.Fatalf("duplicate create/start %d/%d", c, st)
	}
	_, _, e = db.Update(ctx, func(s *model.State) error {
		_, e := model.MutateWorkload(s, "web", "delete", model.ID(), 1, time.Now())
		return e
	})
	if e != nil {
		t.Fatal(e)
	}
	wait(func(s *model.State) bool { return len(s.Allocations) == 0 && len(s.Workloads) == 0 })
	mu.Lock()
	gone, count := container == nil, deleted
	mu.Unlock()
	if !gone || count != 1 {
		t.Fatal("container cleanup not acknowledged")
	}
	t.Log("Actual dev.3 -> dev.4 agent executables, real mTLS/journal; Docker and etcd TEST ADAPTERS. Allocation retained; exactly one create/start/delete in fixture.")
}
