package cli

import (
	"context"
	"encoding/json"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestAllControllerHealthNeverUsesFailoverToHideBadPeer(t *testing.T) {
	ca, _ := pki.CA("test", time.Now())
	cert, _ := pki.Issue(ca, "control", "a", []string{"127.0.0.1"}, true, time.Now())
	cluster := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	makeServer := func(version string) *httptest.Server {
		s := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			json.NewEncoder(w).Encode(ControllerHealth{Status: "ready", ClusterID: cluster, Version: version, StateSchema: model.StateSchema})
		}))
		s.TLS, _ = pki.Server(ca.Cert, cert)
		s.StartTLS()
		t.Cleanup(s.Close)
		return s
	}
	one, two := makeServer(model.Version), makeServer("old-version")
	admin, _ := pki.Issue(ca, "admin", cluster, nil, false, time.Now())
	dir := t.TempDir()
	cf := filepath.Join(dir, "ca")
	cp := filepath.Join(dir, "cert")
	kp := filepath.Join(dir, "key")
	os.WriteFile(cf, ca.Cert, 0600)
	os.WriteFile(cp, admin.Cert, 0600)
	os.WriteFile(kp, admin.Key, 0600)
	c := config.Client{Server: one.URL, Servers: []string{one.URL, two.URL}, CA: cf, Cert: cp, Key: kp, ClusterID: cluster}
	if _, e := CheckControllers(context.Background(), c, model.Version); e == nil {
		t.Fatal("bad peer hidden")
	}
	c.Servers = []string{one.URL}
	result, e := CheckControllers(context.Background(), c, model.Version)
	if e != nil || len(result) != 1 {
		t.Fatal(result, e)
	}
	c.Servers = []string{one.URL, two.URL}
	two.Close()
	if _, e := CheckControllers(context.Background(), c, model.Version); e == nil {
		t.Fatal("unreachable peer hidden")
	}
}
