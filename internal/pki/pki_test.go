package pki

import (
	"crypto/tls"
	"crypto/x509"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestCertificateIdentityAndScope(t *testing.T) {
	ca, e := CA("test", time.Now())
	if e != nil {
		t.Fatal(e)
	}
	p, e := Issue(ca, "node:test", "cluster", nil, false, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	if e = ValidateIdentity(ca.Cert, p, "node:test", "cluster"); e != nil {
		t.Fatal(e)
	}
	if ValidateIdentity(ca.Cert, p, "admin", "cluster") == nil || ValidateIdentity(ca.Cert, p, "node:test", "other") == nil {
		t.Fatal("identity confusion")
	}
	foreign, _ := CA("foreign", time.Now())
	if ValidateIdentity(foreign.Cert, p, "node:test", "cluster") == nil {
		t.Fatal("foreign CA accepted")
	}
	oldCA, _ := CA("historic", time.Now().AddDate(-3, 0, 0))
	p, _ = Issue(oldCA, "admin", "cluster", nil, false, time.Now().AddDate(-2, 0, 0))
	if ValidateIdentity(oldCA.Cert, p, "admin", "cluster") == nil {
		t.Fatal("expired certificate accepted")
	}
}
func TestMutualTLSRequired(t *testing.T) {
	ca, _ := CA("test", time.Now())
	server, _ := Issue(ca, "control", "cluster", []string{"127.0.0.1"}, true, time.Now())
	cfg, _ := Server(ca.Cert, server)
	s := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("ok")) }))
	s.TLS = cfg
	s.StartTLS()
	defer s.Close()
	roots, _ := Pool(ca.Cert)
	noCert := &http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS13, RootCAs: roots}}}
	defer noCert.CloseIdleConnections()
	if r, e := noCert.Get(s.URL); e == nil {
		r.Body.Close()
		t.Fatal("client certificate not required")
	}
	user, _ := Issue(ca, "admin", "cluster", nil, false, time.Now())
	client, _ := Client(ca.Cert, user)
	defer client.CloseIdleConnections()
	r, e := client.Get(s.URL)
	if e != nil {
		t.Fatal(e)
	}
	r.Body.Close()
	if r.TLS.Version != tls.VersionTLS13 {
		t.Fatal("unexpected TLS version")
	}
}
func TestEtcdPeerCertificateCanServeAndConnect(t *testing.T) {
	ca, _ := CA("test", time.Now())
	p, _ := Issue(ca, "etcd-server", "cluster", []string{"127.0.0.1"}, true, time.Now())
	pair, _ := tls.X509KeyPair(p.Cert, p.Key)
	leaf, _ := x509.ParseCertificate(pair.Certificate[0])
	if len(leaf.ExtKeyUsage) != 2 {
		t.Fatal("peer missing mutual usage")
	}
}
func TestInvalidPEMRejected(t *testing.T) {
	if _, e := Pool([]byte("bad")); e == nil {
		t.Fatal("invalid CA")
	}
	if _, e := Client([]byte("bad"), Pair{}); e == nil {
		t.Fatal("invalid client")
	}
}
