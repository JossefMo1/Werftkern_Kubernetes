package engine

import (
	"context"
	"encoding/json"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// dockerFixture implements selected Engine HTTP endpoints, NOT container isolation.
type dockerFixture struct {
	d                               *Docker
	c                               *inspection
	creates, starts, stops, deletes int
	create                          map[string]any
	imageExists, volumes            bool
	api, min                        string
}

func dockerTest(t *testing.T) *dockerFixture {
	t.Helper()
	f := &dockerFixture{imageExists: true, api: "1.51", min: "1.41"}
	// Unix sockets have a platform-specific short pathname bound.
	dir, e := os.MkdirTemp("", "cpr-engine-")
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { os.RemoveAll(dir) })
	socket := filepath.Join(dir, "docker.sock")
	l, e := net.Listen("unix", socket)
	if e != nil {
		t.Fatal(e)
	}
	s := &http.Server{Handler: http.HandlerFunc(f.serve)}
	go s.Serve(l)
	t.Cleanup(func() { s.Close() })
	f.d = NewDocker(socket, strings.Repeat("a", 32))
	f.d.SecretRoot = t.TempDir()
	os.Chmod(f.d.SecretRoot, 0700)
	f.d.RequireSecretTmpfs = false
	return f
}
func (f *dockerFixture) serve(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.URL.Path == "/version" {
		json.NewEncoder(w).Encode(map[string]string{"ApiVersion": f.api, "MinAPIVersion": f.min})
		return
	}
	p := strings.TrimPrefix(r.URL.Path, "/v1.51")
	switch {
	case p == "/info":
		w.Write([]byte(`{}`))
	case strings.HasPrefix(p, "/images/") && strings.HasSuffix(p, "/json"):
		if !f.imageExists {
			http.NotFound(w, r)
			return
		}
		v := map[string]any{}
		if f.volumes {
			v["/data"] = map[string]any{}
		}
		json.NewEncoder(w).Encode(map[string]any{"Config": map[string]any{"Volumes": v}})
	case p == "/containers/create":
		f.creates++
		json.NewDecoder(r.Body).Decode(&f.create)
		f.c = &inspection{}
		b, _ := json.Marshal(f.create)
		json.Unmarshal(b, &f.c.Config)
		w.WriteHeader(201)
		w.Write([]byte(`{"Id":"fixture"}`))
	case strings.HasSuffix(p, "/json") && strings.HasPrefix(p, "/containers/cpr-"):
		if f.c == nil {
			http.NotFound(w, r)
			return
		}
		json.NewEncoder(w).Encode(f.c)
	case strings.HasSuffix(p, "/start"):
		f.starts++
		f.c.State.Running = true
		w.WriteHeader(204)
	case strings.HasSuffix(p, "/stop"):
		f.stops++
		f.c.State.Running = false
		w.WriteHeader(204)
	case r.Method == "DELETE":
		f.deletes++
		f.c = nil
		w.WriteHeader(204)
	case p == "/containers/json":
		if f.c == nil {
			w.Write([]byte(`[]`))
			return
		}
		json.NewEncoder(w).Encode([]any{map[string]any{"Labels": f.c.Config.Labels}})
	default:
		http.NotFound(w, r)
	}
}
func allocation() model.Allocation {
	return model.Allocation{ID: strings.Repeat("b", 32), Spec: model.Spec{Image: "sha256:" + strings.Repeat("c", 64), Replicas: 1, CPUMilli: 500, MemoryMiB: 64}}
}
func TestEngineCreatesConstrainedContainerAndReplays(t *testing.T) {
	f := dockerTest(t)
	a := allocation()
	ctx := context.Background()
	for i := 0; i < 2; i++ {
		r, e := f.d.Ensure(ctx, a, "127.0.0.1", func() bool { return true })
		if e != nil || r.Phase != "ready" {
			t.Fatal(r, e)
		}
	}
	if f.creates != 1 || f.starts != 1 {
		t.Fatal("duplicate container", f.creates, f.starts)
	}
	if f.create["User"] != "65532:65532" {
		t.Fatal(f.create)
	}
	h := f.create["HostConfig"].(map[string]any)
	if h["ReadonlyRootfs"] != true || h["Privileged"] != false || h["Memory"].(float64) != 64*1024*1024 || h["CpuQuota"].(float64) != 50000 {
		t.Fatal(h)
	}
	if h["CapDrop"].([]any)[0] != "ALL" || h["SecurityOpt"].([]any)[0] != "no-new-privileges:true" {
		t.Fatal(h)
	}
	if _, ok := h["Binds"]; ok {
		t.Fatal("host bind mounts")
	}
	ids, e := f.d.Owned(ctx)
	if e != nil || len(ids) != 1 || ids[0] != a.ID {
		t.Fatal(ids, e)
	}
	for i := 0; i < 2; i++ {
		if e = f.d.Stop(ctx, a.ID); e != nil {
			t.Fatal(e)
		}
	}
	if f.stops != 1 || f.deletes != 1 {
		t.Fatal("non-idempotent stop")
	}
}
func TestEngineOwnershipConflictNeverMutates(t *testing.T) {
	f := dockerTest(t)
	f.c = &inspection{}
	f.c.Config.Labels = map[string]string{clusterLabel: "foreign"}
	f.c.State.Running = true
	_, e := f.d.Ensure(context.Background(), allocation(), "127.0.0.1", func() bool { return true })
	if e == nil {
		t.Fatal("adopted foreign container")
	}
	if e = f.d.Stop(context.Background(), allocation().ID); e == nil {
		t.Fatal("stopped foreign container")
	}
	ids, _ := f.d.Owned(context.Background())
	if len(ids) != 0 || f.stops+f.starts+f.creates+f.deletes != 0 {
		t.Fatal("mutated foreign resources")
	}
}
func TestEngineDoesNotReplaceChangedSpecInPlace(t *testing.T) {
	f := dockerTest(t)
	a := allocation()
	f.d.Ensure(context.Background(), a, "127.0.0.1", func() bool { return true })
	a.Spec.CPUMilli = 600
	_, e := f.d.Ensure(context.Background(), a, "127.0.0.1", func() bool { return true })
	if e == nil || f.creates != 1 {
		t.Fatal(e)
	}
}
func TestEngineRejectsMissingLocalImageAndDeclaredVolumes(t *testing.T) {
	for _, name := range []string{"missing", "volumes"} {
		t.Run(name, func(t *testing.T) {
			f := dockerTest(t)
			f.imageExists = name != "missing"
			f.volumes = name == "volumes"
			_, e := f.d.Ensure(context.Background(), allocation(), "127.0.0.1", func() bool { return true })
			if e == nil || f.creates != 0 {
				t.Fatal(e)
			}
		})
	}
}
func TestEngineStopsStaleStart(t *testing.T) {
	f := dockerTest(t)
	_, e := f.d.Ensure(context.Background(), allocation(), "127.0.0.1", func() bool { return false })
	if !errors.Is(e, ErrStale) || f.creates != 0 {
		t.Fatal(e)
	}
}
func TestEngineRejectsInvalidAllocationPortAndPublicIP(t *testing.T) {
	f := dockerTest(t)
	a := allocation()
	a.Spec.Port = 8080
	a.Spec.ReadinessPath = "/healthz"
	a.HostPort = 80
	if _, e := f.d.Ensure(context.Background(), a, "127.0.0.1", func() bool { return true }); e == nil {
		t.Fatal("privileged host port accepted")
	}
	a = allocation()
	if _, e := f.d.Ensure(context.Background(), a, "8.8.8.8", func() bool { return true }); e == nil {
		t.Fatal("public node accepted")
	}
}
func TestEngineNegotiationRejectsIncompatibleAPI(t *testing.T) {
	f := dockerTest(t)
	f.api = "1.60"
	f.min = "1.55"
	if f.d.Health(context.Background()) == nil {
		t.Fatal("unsupported API accepted")
	}
}
func TestEngineReadinessAndPrivatePortBinding(t *testing.T) {
	f := dockerTest(t)
	var listener net.Listener
	var e error
	for p := 22800; p < 23000; p++ {
		listener, e = net.Listen("tcp", net.JoinHostPort("127.0.0.1", strconv.Itoa(p)))
		if e == nil {
			break
		}
	}
	if listener == nil {
		t.Fatal("no probe port available")
	}
	status := 200
	probe := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(status) }))
	probe.Listener = listener
	probe.Start()
	t.Cleanup(probe.Close)
	a := allocation()
	a.Spec.Port = 8080
	a.Spec.ReadinessPath = "/healthz"
	a.HostPort = listener.Addr().(*net.TCPAddr).Port
	for _, code := range []int{200, 503, 302} {
		status = code
		r, e := f.d.Ensure(context.Background(), a, "127.0.0.1", func() bool { return true })
		if e != nil {
			t.Fatal(e)
		}
		if (r.Phase == "ready") != (code == 200) {
			t.Fatal(code, r)
		}
	}
	h := f.create["HostConfig"].(map[string]any)
	binding := h["PortBindings"].(map[string]any)["8080/tcp"].([]any)[0].(map[string]any)
	if binding["HostIp"] != "127.0.0.1" || binding["HostPort"] != strconv.Itoa(a.HostPort) {
		t.Fatal(binding)
	}
}
