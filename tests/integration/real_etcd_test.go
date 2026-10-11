//go:build real_etcd

package integration

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/pki"
	"github.com/ClusterPilot-System/werftkern/internal/store"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

// Run only in a dedicated qualification environment. This is a real local etcd
// process, not a VM, not a three-member quorum, not a production certificate.
func TestRealEtcdPersistenceCASAndFailClosed(t *testing.T) {
	binary, e := exec.LookPath("etcd")
	if e != nil {
		t.Fatal("real_etcd tag requires an installed etcd binary; no silent skip")
	}
	dir := t.TempDir()
	id := model.ID()
	ca, e := pki.CA("test-etcd", time.Now())
	if e != nil {
		t.Fatal(e)
	}
	server, _ := pki.Issue(ca, "etcd-server", id, []string{"127.0.0.1"}, true, time.Now())
	client, _ := pki.Issue(ca, "client", id, nil, false, time.Now())
	for n, b := range map[string][]byte{"ca.crt": ca.Cert, "server.crt": server.Cert, "server.key": server.Key} {
		if e = os.WriteFile(filepath.Join(dir, n), b, 0600); e != nil {
			t.Fatal(e)
		}
	}
	port := func() int {
		l, e := net.Listen("tcp", "127.0.0.1:0")
		if e != nil {
			t.Fatal(e)
		}
		p := l.Addr().(*net.TCPAddr).Port
		l.Close()
		return p
	}
	cport, pport := port(), port()
	url := fmt.Sprintf("https://127.0.0.1:%d", cport)
	peer := fmt.Sprintf("https://127.0.0.1:%d", pport)
	cfg := map[string]any{"name": "test", "data-dir": dir + "/data", "listen-client-urls": url, "advertise-client-urls": url, "listen-peer-urls": peer, "initial-advertise-peer-urls": peer, "initial-cluster": "test=" + peer, "initial-cluster-state": "new", "initial-cluster-token": id, "client-transport-security": map[string]any{"cert-file": dir + "/server.crt", "key-file": dir + "/server.key", "trusted-ca-file": dir + "/ca.crt", "client-cert-auth": true}, "peer-transport-security": map[string]any{"cert-file": dir + "/server.crt", "key-file": dir + "/server.key", "trusted-ca-file": dir + "/ca.crt", "client-cert-auth": true}}
	raw, _ := json.Marshal(cfg)
	os.WriteFile(dir+"/etcd.yaml", raw, 0600)
	start := func() *exec.Cmd {
		c := exec.Command(binary, "--config-file="+dir+"/etcd.yaml")
		if e := c.Start(); e != nil {
			t.Fatal(e)
		}
		t.Cleanup(func() { c.Process.Kill(); c.Wait() })
		return c
	}
	process := start()
	http, e := pki.Client(ca.Cert, client)
	if e != nil {
		t.Fatal(e)
	}
	db := store.NewEtcd(url, http, id)
	ctx, cancel := context.WithTimeout(context.Background(), 25*time.Second)
	defer cancel()
	for {
		e = db.Initialize(ctx, model.NewState(id, "real-etcd", time.Now()))
		if e == nil {
			break
		}
		if ctx.Err() != nil {
			t.Fatal(e)
		}
		time.Sleep(200 * time.Millisecond)
	}
	if _, _, e = db.Update(ctx, func(s *model.State) error { s.Name = "persisted"; return nil }); e != nil {
		t.Fatal(e)
	}
	process.Process.Kill()
	process.Wait()
	probe, cancelProbe := context.WithTimeout(context.Background(), time.Second)
	defer cancelProbe()
	if _, _, e = db.Read(probe); e == nil {
		t.Fatal("read succeeded without etcd")
	}
	start()
	deadline := time.Now().Add(15 * time.Second)
	for {
		s, _, e := db.Read(ctx)
		if e == nil {
			if s.Name != "persisted" {
				t.Fatal("lost state")
			}
			break
		}
		if time.Now().After(deadline) {
			t.Fatal(e)
		}
		time.Sleep(200 * time.Millisecond)
	}
}
