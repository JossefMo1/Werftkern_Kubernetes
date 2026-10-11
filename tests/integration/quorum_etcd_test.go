//go:build real_etcd

package integration

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/store"
)

// This is intentionally three REAL processes/data directories/peer sockets on
// ONE host. It is not evidence of three VMs, network partition or disk recovery.
func TestRealEtcdThreeMemberLeaderLossQuorumAndRestart(t *testing.T) {
	binary, e := exec.LookPath("etcd")
	if e != nil {
		t.Fatal("BLOCKED: etcd binary required; this test never substitutes a fixture")
	}
	version, e := exec.Command(binary, "--version").Output()
	if e != nil {
		t.Fatal(e)
	}
	t.Logf("real binary identity:\n%s", version)
	dir := t.TempDir()
	cluster := model.ID()
	ca, e := pki.CA("real-etcd-quorum-test", time.Now())
	if e != nil {
		t.Fatal(e)
	}
	clientPair, e := pki.Issue(ca, "quorum-client", cluster, nil, false, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	client, e := pki.Client(ca.Cert, clientPair)
	if e != nil {
		t.Fatal(e)
	}
	defer client.CloseIdleConnections()
	usedPorts := map[int]bool{}
	free := func() int {
		for attempt := 0; attempt < 100; attempt++ {
			l, e := net.Listen("tcp", "127.0.0.1:0")
			if e != nil {
				t.Fatal(e)
			}
			port := l.Addr().(*net.TCPAddr).Port
			l.Close()
			if !usedPorts[port] {
				usedPorts[port] = true
				return port
			}
		}
		t.Fatal("could not allocate distinct local ports")
		return 0
	}
	type member struct {
		name, url, peer, file, log string
		cmd                        *exec.Cmd
		logfile                    *os.File
		db                         *store.Etcd
	}
	members := make([]*member, 3)
	initial := []string{}
	for i := range members {
		m := &member{name: fmt.Sprintf("member-%d", i), url: fmt.Sprintf("https://127.0.0.1:%d", free()), peer: fmt.Sprintf("https://127.0.0.1:%d", free())}
		m.db = store.NewEtcd(m.url, client, cluster)
		members[i] = m
		initial = append(initial, m.name+"="+m.peer)
	}
	stop := func(m *member) {
		if m.cmd != nil {
			if m.cmd.Process != nil {
				_ = m.cmd.Process.Kill()
				_ = m.cmd.Wait()
			}
			m.cmd = nil
		}
		if m.logfile != nil {
			m.logfile.Close()
			m.logfile = nil
		}
	}
	t.Cleanup(func() {
		for _, m := range members {
			stop(m)
			if t.Failed() {
				data, _ := os.ReadFile(m.log)
				if len(data) > 16000 {
					data = data[len(data)-16000:]
				}
				t.Logf("%s real process log tail:\n%s", m.name, data)
			}
		}
	})
	start := func(m *member) {
		f, e := os.OpenFile(m.log, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
		if e != nil {
			t.Fatal(e)
		}
		m.logfile = f
		m.cmd = exec.Command(binary, "--config-file="+m.file)
		m.cmd.Stdout = f
		m.cmd.Stderr = f
		if e = m.cmd.Start(); e != nil {
			t.Fatal(e)
		}
	}
	for _, m := range members {
		root := filepath.Join(dir, m.name)
		if e = os.Mkdir(root, 0700); e != nil {
			t.Fatal(e)
		}
		m.file = root + "/etcd.json"
		m.log = root + "/process.log"
		cert, e := pki.Issue(ca, "etcd-server", cluster, []string{"127.0.0.1"}, true, time.Now())
		if e != nil {
			t.Fatal(e)
		}
		for name, bytes := range map[string][]byte{"ca.crt": ca.Cert, "server.crt": cert.Cert, "server.key": cert.Key} {
			if e = os.WriteFile(root+"/"+name, bytes, 0600); e != nil {
				t.Fatal(e)
			}
		}
		secure := map[string]any{"cert-file": root + "/server.crt", "key-file": root + "/server.key", "trusted-ca-file": root + "/ca.crt", "client-cert-auth": true}
		cfg := map[string]any{"name": m.name, "data-dir": root + "/data", "listen-client-urls": m.url, "advertise-client-urls": m.url, "listen-peer-urls": m.peer, "initial-advertise-peer-urls": m.peer, "initial-cluster": strings.Join(initial, ","), "initial-cluster-state": "new", "initial-cluster-token": cluster, "client-transport-security": secure, "peer-transport-security": secure}
		raw, e := json.Marshal(cfg)
		if e != nil {
			t.Fatal(e)
		}
		if e = os.WriteFile(m.file, raw, 0600); e != nil {
			t.Fatal(e)
		}
		start(m)
	}
	retry := func(label string, fn func(context.Context) error) {
		t.Helper()
		end := time.Now().Add(40 * time.Second)
		var last error
		for time.Now().Before(end) {
			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
			last = fn(ctx)
			cancel()
			if last == nil {
				return
			}
			time.Sleep(200 * time.Millisecond)
		}
		t.Fatalf("%s: %v", label, last)
	}
	retry("initial real quorum", func(ctx context.Context) error {
		return members[0].db.Initialize(ctx, model.NewState(cluster, "counter-0", time.Now()))
	})
	for _, m := range members {
		retry("member linearizable read", func(ctx context.Context) error { _, _, e := m.db.Read(ctx); return e })
	}
	var wg sync.WaitGroup
	errs := make(chan error, 3)
	for _, m := range members {
		wg.Add(1)
		go func(m *member) {
			defer wg.Done()
			for n := 0; n < 20; n++ {
				ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
				_, _, e := m.db.Update(ctx, func(s *model.State) error {
					v, e := strconv.Atoi(strings.TrimPrefix(s.Name, "counter-"))
					if e != nil {
						return e
					}
					s.Name = fmt.Sprintf("counter-%d", v+1)
					return nil
				})
				cancel()
				if e != nil {
					errs <- e
					return
				}
			}
		}(m)
	}
	wg.Wait()
	close(errs)
	for e := range errs {
		t.Fatal("concurrent real CAS", e)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	state, _, e := members[0].db.Read(ctx)
	cancel()
	if e != nil || state.Name != "counter-60" {
		t.Fatal("lost concurrent update", e, state)
	}
	// Identify, then actually kill, the elected leader rather than assuming node 0.
	type status struct {
		Header struct {
			MemberID string `json:"member_id"`
		} `json:"header"`
		Leader string `json:"leader"`
	}
	leader := -1
	for i, m := range members {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		r, _ := http.NewRequestWithContext(ctx, "POST", m.url+"/v3/maintenance/status", strings.NewReader("{}"))
		r.Header.Set("Content-Type", "application/json")
		response, e := client.Do(r)
		if e != nil {
			cancel()
			t.Fatal(e)
		}
		var result status
		e = json.NewDecoder(io.LimitReader(response.Body, 65536)).Decode(&result)
		response.Body.Close()
		cancel()
		if e != nil {
			t.Fatal(e)
		}
		if result.Header.MemberID != "" && result.Leader != "0" && result.Header.MemberID == result.Leader {
			leader = i
		}
	}
	if leader < 0 {
		t.Fatal("real elected leader not observed")
	}
	t.Logf("killing real elected leader index=%d", leader)
	stop(members[leader])
	survivor := (leader + 1) % 3
	other := (leader + 2) % 3
	retry("leader loss retains majority", func(ctx context.Context) error {
		_, _, e := members[survivor].db.Update(ctx, func(s *model.State) error { s.Name = "majority-survives"; return nil })
		return e
	})
	stop(members[other])
	ctx, cancel = context.WithTimeout(context.Background(), 2*time.Second)
	_, _, e = members[survivor].db.Read(ctx)
	cancel()
	if e == nil {
		t.Fatal("linearizable read unexpectedly succeeded without quorum")
	}
	ctx, cancel = context.WithTimeout(context.Background(), 2*time.Second)
	_, _, e = members[survivor].db.Update(ctx, func(s *model.State) error { s.Name = "unsafe-write"; return nil })
	cancel()
	if e == nil {
		t.Fatal("write unexpectedly succeeded without quorum")
	}
	start(members[other])
	retry("quorum restored with previous data", func(ctx context.Context) error {
		s, _, e := members[survivor].db.Read(ctx)
		if e != nil {
			return e
		}
		if s.Name != "majority-survives" {
			return fmt.Errorf("state lost or unauthorized write: %s", s.Name)
		}
		return nil
	})
	retry("write after restored quorum", func(ctx context.Context) error {
		_, _, e := members[survivor].db.Update(ctx, func(s *model.State) error { s.Name = "quorum-restored"; return nil })
		return e
	})
	start(members[leader])
	for _, m := range members {
		retry("all real members converge", func(ctx context.Context) error {
			s, _, e := m.db.Read(ctx)
			if e != nil {
				return e
			}
			if s.Name != "quorum-restored" {
				return fmt.Errorf("divergent state %s", s.Name)
			}
			return nil
		})
	}
	t.Log("PASS scope: real single-host etcd processes, mTLS, concurrent CAS, elected leader termination, quorum loss, restart, persisted convergence; no VM or partition qualification")
}
