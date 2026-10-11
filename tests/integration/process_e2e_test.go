// These tests launch REAL Linux child processes and use REAL TLS API requests.
// The process runtime and file-backed etcd protocol fixture are TEST DOUBLES.
// Passing this suite is NOT evidence of Docker, etcd/Raft or Ubuntu packaging E2E.
package integration

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/agent"
	"github.com/ClusterPilot-System/werftkern/internal/apiclient"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/control"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/store"
	"github.com/ClusterPilot-System/werftkern/internal/testutil"
)

func TestWorkloadProcess(t *testing.T) {
	if os.Getenv("CPR_PROCESS_FIXTURE") != "1" {
		return
	}
	h := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"pid": os.Getpid(), "fixture": "real-process-not-container"})
	})
	server := &http.Server{Addr: os.Getenv("CPR_PROCESS_ADDRESS"), Handler: h, ReadHeaderTimeout: time.Second}
	if e := server.ListenAndServe(); e != nil {
		os.Exit(1)
	}
}

type child struct {
	cmd     *exec.Cmd
	done    chan error
	address string
}
type processRuntime struct {
	children map[string]*child
	starts   int
}

func (p *processRuntime) Health(context.Context) error { return nil }
func (p *processRuntime) Owned(context.Context) ([]string, error) {
	ids := []string{}
	for id := range p.children {
		ids = append(ids, id)
	}
	return ids, nil
}
func (p *processRuntime) Stop(ctx context.Context, id string) error {
	c := p.children[id]
	if c == nil {
		return nil
	}
	c.cmd.Process.Kill()
	select {
	case <-c.done:
		delete(p.children, id)
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}
func (p *processRuntime) Ensure(ctx context.Context, a model.Allocation, ip string, allowed func() bool) (model.Report, error) {
	r := model.Report{ID: a.ID, Phase: "starting"}
	if !allowed() {
		return r, errors.New("stale")
	}
	c := p.children[a.ID]
	if c == nil {
		addr := net.JoinHostPort(ip, fmt.Sprint(a.HostPort))
		exe, e := os.Executable()
		if e != nil {
			return r, e
		}
		cmd := exec.Command(exe, "-test.run=^TestWorkloadProcess$")
		cmd.Env = append(os.Environ(), "CPR_PROCESS_FIXTURE=1", "CPR_PROCESS_ADDRESS="+addr)
		cmd.Stdout = io.Discard
		cmd.Stderr = io.Discard
		if e = cmd.Start(); e != nil {
			return r, e
		}
		c = &child{cmd: cmd, done: make(chan error, 1), address: addr}
		p.children[a.ID] = c
		p.starts++
		go func() { c.done <- cmd.Wait() }()
	}
	client := &http.Client{Timeout: 200 * time.Millisecond, Transport: &http.Transport{Proxy: nil, DisableKeepAlives: true}}
	defer client.CloseIdleConnections()
	for i := 0; i < 50; i++ {
		response, e := client.Get("http://" + c.address + "/healthz")
		if e == nil {
			response.Body.Close()
			if response.StatusCode == 200 {
				r.Phase = "ready"
				return r, nil
			}
		}
		select {
		case <-ctx.Done():
			return r, ctx.Err()
		case <-time.After(20 * time.Millisecond):
		}
	}
	return r, errors.New("PROCESS_PROBE_TIMEOUT")
}
func (p *processRuntime) close() {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	for id := range p.children {
		p.Stop(ctx, id)
	}
}

func TestProcessE2EDeployReplayRestartRolloutDrainDelete(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	dir := t.TempDir()
	cluster := model.ID()
	fixture := testutil.NewEtcd(t, filepath.Join(dir, "etcd-fixture.json"))
	state := store.NewEtcd(fixture.URL(), fixture.Server.Client(), cluster)
	if e := state.Initialize(ctx, model.NewState(cluster, "process-e2e", time.Now())); e != nil {
		t.Fatal(e)
	}
	api := &control.API{Store: state, ClusterID: cluster}
	transport := testutil.NewTLS(t, cluster, api.Handler())
	admin := &apiclient.Client{HTTP: transport.Client(t, "admin"), Base: transport.Server.URL, ClusterID: cluster}
	agents := []*agent.Agent{}
	runtimes := []*processRuntime{}
	for i := 0; i < 2; i++ {
		id := model.ID()
		addr := fmt.Sprintf("127.0.0.%d", i+2)
		name := fmt.Sprintf("worker-%d", i+1)
		if e := admin.Call(ctx, "POST", "/v1/nodes", control.NodeRegistration{ID: id, Name: name, Address: addr}, nil, ""); e != nil {
			t.Fatal(e)
		}
		c := config.Agent{Client: config.Client{ClusterID: cluster}, NodeID: id, InstanceID: model.ID(), Address: addr, Journal: filepath.Join(dir, name+".json")}
		client := &apiclient.Client{HTTP: transport.Client(t, "node:"+id), Base: transport.Server.URL, ClusterID: cluster}
		runtime := &processRuntime{children: map[string]*child{}}
		t.Cleanup(runtime.close)
		runtimes = append(runtimes, runtime)
		a, e := agent.New(c, client, runtime)
		if e != nil {
			t.Fatal(e)
		}
		agents = append(agents, a)
	}
	step := func() *model.State {
		t.Helper()
		for _, a := range agents {
			if e := a.HeartbeatOnce(ctx); e != nil {
				t.Fatal(e)
			}
		}
		if _, _, e := state.Update(ctx, func(s *model.State) error { return control.Reconcile(s, time.Now()) }); e != nil {
			t.Fatal(e)
		}
		for _, a := range agents {
			if e := a.HeartbeatOnce(ctx); e != nil {
				t.Fatal(e)
			}
			if e := a.ReconcileOnce(ctx); e != nil {
				t.Fatal(e)
			}
			if e := a.HeartbeatOnce(ctx); e != nil {
				t.Fatal(e)
			}
		}
		s, _, e := state.Update(ctx, func(s *model.State) error { return control.Reconcile(s, time.Now()) })
		if e != nil {
			t.Fatal(e)
		}
		return s
	}
	until := func(condition func(*model.State) bool) *model.State {
		t.Helper()
		for i := 0; i < 30; i++ {
			s := step()
			if condition(s) {
				return s
			}
		}
		s, _ := admin.State(ctx)
		b, _ := json.Marshal(s)
		t.Fatalf("did not converge: %s", b)
		return nil
	}
	ready := func(s *model.State) bool { return s.Workloads["demo"] != nil && s.Workloads["demo"].Phase == "ready" }
	req := model.ApplyRequest{APIVersion: model.APIVersion, Name: "demo", Spec: model.Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 2, CPUMilli: 100, MemoryMiB: 32, Port: 8080, ReadinessPath: "/healthz"}}
	key := model.ID()
	var original, replay model.Receipt
	if e := admin.Call(ctx, "POST", "/v1/workloads", req, &original, key); e != nil {
		t.Fatal(e)
	}
	s := until(ready)
	if runtimes[0].starts != 1 || runtimes[1].starts != 1 {
		t.Fatal("not spread across workers")
	}
	pids := map[string]int{}
	for _, runtime := range runtimes {
		for id, c := range runtime.children {
			response, e := http.Get("http://" + c.address + "/healthz")
			if e != nil {
				t.Fatal(e)
			}
			var out struct {
				PID int `json:"pid"`
			}
			json.NewDecoder(response.Body).Decode(&out)
			response.Body.Close()
			if out.PID != c.cmd.Process.Pid {
				t.Fatal("not a real child process response")
			}
			pids[id] = out.PID
		}
	}
	if e := admin.Call(ctx, "POST", "/v1/workloads", req, &replay, key); e != nil || model.Hash(original) != model.Hash(replay) {
		t.Fatal("replay failed", e)
	}
	step()
	for _, runtime := range runtimes {
		if runtime.starts != 1 {
			t.Fatal("replay duplicated process")
		}
	}
	// Reconstruct the actual production store client from the fixture's fsynced
	// data and replace the API transport. Both agents reload their durable journal.
	fixture.Server.Close()
	fixture = testutil.NewEtcd(t, fixture.Path)
	state = store.NewEtcd(fixture.URL(), fixture.Server.Client(), cluster)
	transport.Server.Close()
	api = &control.API{Store: state, ClusterID: cluster}
	transport = testutil.NewTLS(t, cluster, api.Handler())
	// Fresh TLS fixture credentials here; on real installs the existing PKI persists.
	admin = &apiclient.Client{HTTP: transport.Client(t, "admin"), Base: transport.Server.URL, ClusterID: cluster}
	for i, old := range agents {
		cl := &apiclient.Client{HTTP: transport.Client(t, "node:"+old.Config.NodeID), Base: transport.Server.URL, ClusterID: cluster}
		a, e := agent.New(old.Config, cl, runtimes[i])
		if e != nil {
			t.Fatal(e)
		}
		agents[i] = a
	}
	s = until(ready)
	for _, runtime := range runtimes {
		for id, c := range runtime.children {
			if pids[id] != c.cmd.Process.Pid {
				t.Fatal("restart duplicated process")
			}
		}
	}
	// Roll a new immutable revision, retain two ready endpoints throughout.
	req.ExpectedGeneration = s.Workloads["demo"].Generation
	req.Spec.CPUMilli = 200
	if e := admin.Call(ctx, "POST", "/v1/workloads", req, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	s = until(func(s *model.State) bool {
		readyCount := 0
		for _, a := range s.Allocations {
			if a.Desired == "run" && a.Phase == "ready" {
				readyCount++
			}
		}
		if readyCount < 2 {
			t.Fatalf("availability dropped to %d", readyCount)
		}
		return ready(s)
	})
	generation := s.Workloads["demo"].Generation
	if generation != 2 {
		t.Fatal(generation)
	}
	// Drain worker one. The second worker has enough surge capacity.
	if e := admin.Call(ctx, "POST", "/v1/nodes/"+agents[0].Config.NodeID, map[string]bool{"drain": true}, nil, ""); e != nil {
		t.Fatal(e)
	}
	until(func(s *model.State) bool {
		for _, a := range s.Allocations {
			if a.NodeID == agents[0].Config.NodeID {
				return false
			}
		}
		return ready(s)
	})
	if len(runtimes[0].children) != 0 {
		t.Fatal("drained node still running owned processes")
	}
	if e := admin.Call(ctx, "POST", "/v1/workloads/demo/delete", model.MutationRequest{ExpectedGeneration: generation}, nil, model.ID()); e != nil {
		t.Fatal(e)
	}
	until(func(s *model.State) bool { return s.Workloads["demo"] == nil && len(s.Allocations) == 0 })
	for _, runtime := range runtimes {
		if len(runtime.children) != 0 {
			t.Fatal("process leaked")
		}
	}
	t.Log("real subprocess HTTP, mTLS, durable fixture state, replay, agent/API reconstruction, surge rollout, drain and deletion passed; not a container/Ubuntu E2E")
}
