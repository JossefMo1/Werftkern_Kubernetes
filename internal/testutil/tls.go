package testutil

import (
	"github.com/ClusterPilot-System/werftkern/internal/pki"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

// TLSFixture is a real TLS 1.3 transport with fresh test-only certificates.
type TLSFixture struct {
	Server  *httptest.Server
	CA      pki.Pair
	Cluster string
}

func NewTLS(t testing.TB, cluster string, handler http.Handler) *TLSFixture {
	t.Helper()
	ca, e := pki.CA("test-only-ca", time.Now())
	if e != nil {
		t.Fatal(e)
	}
	server, e := pki.Issue(ca, "control", cluster, []string{"127.0.0.1"}, true, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	cfg, e := pki.Server(ca.Cert, server)
	if e != nil {
		t.Fatal(e)
	}
	s := httptest.NewUnstartedServer(handler)
	s.TLS = cfg
	s.StartTLS()
	t.Cleanup(s.Close)
	return &TLSFixture{s, ca, cluster}
}
func (f *TLSFixture) Client(t testing.TB, identity string) *http.Client {
	t.Helper()
	p, e := pki.Issue(f.CA, identity, f.Cluster, nil, false, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	c, e := pki.Client(f.CA.Cert, p)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(c.CloseIdleConnections)
	return c
}
