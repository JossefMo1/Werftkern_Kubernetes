package pki

import (
	"crypto/tls"
	"crypto/x509"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func bundle(t *testing.T, p Pair, path string) {
	t.Helper()
	if e := safefile.Write(path, append(append([]byte{}, p.Cert...), p.Key...), 0600); e != nil {
		t.Fatal(e)
	}
}
func issueForRotation(t *testing.T, cn string, server bool) (Pair, Pair) {
	t.Helper()
	ca, e := CA("rotation-test", time.Now().AddDate(0, 0, -4))
	if e != nil {
		t.Fatal(e)
	}
	p, e := Issue(ca, cn, "cluster-test", []string{"127.0.0.1"}, server, time.Now().AddDate(0, 0, -2))
	if e != nil {
		t.Fatal(e)
	}
	return ca, p
}
func TestReloaderRequiresStableIdentityAndIncreasingExpiry(t *testing.T) {
	ca, p := issueForRotation(t, "node:a", false)
	path := filepath.Join(t.TempDir(), "identity.pem")
	bundle(t, p, path)
	loader, e := NewReloader(ca.Cert, path, x509.ExtKeyUsageClientAuth)
	if e != nil {
		t.Fatal(e)
	}
	replacement, e := Renew(ca, p, 365, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	bundle(t, replacement, path)
	got, e := loader.Certificate()
	if e != nil {
		t.Fatal(e)
	}
	newLeaf, _ := leaf(replacement)
	if got.Leaf.SerialNumber.Cmp(newLeaf.SerialNumber) != 0 {
		t.Fatal("not renewed")
	}
	bundle(t, p, path)
	if _, e = loader.Certificate(); e == nil {
		t.Fatal("rollback accepted")
	}
	admin, e := Issue(ca, "admin", "cluster-test", nil, false, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	bundle(t, admin, path)
	if _, e = loader.Certificate(); e == nil {
		t.Fatal("role change accepted")
	}
}
func TestRotationOverRealTLSChangesServerAndClientCertificates(t *testing.T) {
	ca, server := issueForRotation(t, "control", true)
	client, e := Issue(ca, "node:a", "cluster-test", nil, false, time.Now().AddDate(0, 0, -2))
	if e != nil {
		t.Fatal(e)
	}
	dir := t.TempDir()
	sp, cp, cap := filepath.Join(dir, "server.pem"), filepath.Join(dir, "client.pem"), filepath.Join(dir, "ca.crt")
	bundle(t, server, sp)
	bundle(t, client, cp)
	os.WriteFile(cap, ca.Cert, 0600)
	cfg, e := ServerFiles(cap, sp, sp)
	if e != nil {
		t.Fatal(e)
	}
	listener, e := net.Listen("tcp", "127.0.0.1:0")
	if e != nil {
		t.Fatal(e)
	}
	srv := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, r.TLS.PeerCertificates[0].SerialNumber.String())
	}), TLSConfig: cfg}
	served := make(chan error, 1)
	go func() { served <- srv.Serve(tls.NewListener(listener, cfg)) }()
	defer func() { srv.Close(); <-served }()
	endpoint := "https://" + listener.Addr().String()
	c, e := ClientFiles(cap, cp, cp)
	if e != nil {
		t.Fatal(e)
	}
	defer c.CloseIdleConnections()
	get := func() (string, string) {
		t.Helper()
		res, e := c.Get(endpoint)
		if e != nil {
			t.Fatal(e)
		}
		defer res.Body.Close()
		b, _ := io.ReadAll(res.Body)
		return string(b), res.TLS.PeerCertificates[0].SerialNumber.String()
	}
	oldClient, oldServer := get()
	clientNew, e := Renew(ca, client, 365, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	serverNew, e := Renew(ca, server, 365, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	bundle(t, clientNew, cp)
	bundle(t, serverNew, sp)
	c.CloseIdleConnections()
	newClient, newServer := get()
	if oldClient == newClient || oldServer == newServer {
		t.Fatal("handshakes retained old leaf")
	}
	// No client-certificate fallback on a reused connection after file damage.
	os.WriteFile(cp, []byte("invalid"), 0600)
	if r, e := c.Get(endpoint); e == nil {
		r.Body.Close()
		t.Fatal("cached identity accepted damaged file")
	}
}
func TestReloaderRejectsUnsafePathExpiryAndForeignCA(t *testing.T) {
	ca, p := issueForRotation(t, "node:a", false)
	dir := t.TempDir()
	path := filepath.Join(dir, "pair.pem")
	bundle(t, p, path)
	loader, e := NewReloader(ca.Cert, path, x509.ExtKeyUsageClientAuth)
	if e != nil {
		t.Fatal(e)
	}
	os.Chmod(path, 0644)
	if _, e = loader.Certificate(); e == nil {
		t.Fatal("public key bundle accepted")
	}
	os.Chmod(path, 0600)
	link := filepath.Join(dir, "link")
	os.Symlink(path, link)
	if _, e = ReadBundle(link); e == nil {
		t.Fatal("symlink accepted")
	}
	loader.now = func() time.Time { return time.Now().AddDate(2, 0, 0) }
	if _, e = loader.Certificate(); e == nil {
		t.Fatal("expired accepted")
	}
	other, _ := CA("other", time.Now())
	if _, e = NewReloader(other.Cert, path, x509.ExtKeyUsageClientAuth); e == nil {
		t.Fatal("foreign trust")
	}
}
func TestAtomicRenewalInstallReplayAndConflict(t *testing.T) {
	ca, p := issueForRotation(t, "node:a", false)
	dir := t.TempDir()
	path, next := filepath.Join(dir, "identity"), filepath.Join(dir, "candidate")
	bundle(t, p, path)
	n, e := Renew(ca, p, 365, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	bundle(t, n, next)
	original, _ := leaf(p)
	if e = InstallRenewal(ca.Cert, path, next, strings.Repeat("0", 64)); e == nil {
		t.Fatal("mismatched expected fingerprint")
	}
	if e = InstallRenewal(ca.Cert, path, next, Fingerprint(original)); e != nil {
		t.Fatal(e)
	}
	if e = InstallRenewal(ca.Cert, path, next, Fingerprint(original)); e != nil {
		t.Fatal("lost ACK replay failed", e)
	}
	got, _ := ReadBundle(path)
	leafNew, _ := leaf(n)
	leafGot, _ := leaf(got)
	if Fingerprint(leafNew) != Fingerprint(leafGot) {
		t.Fatal("candidate not installed")
	}
	st, _ := os.Stat(path)
	if st.Mode().Perm() != 0600 {
		t.Fatal("bundle mode")
	}
}
func TestRenewalRefusesExpiredIssuerAndRoleChange(t *testing.T) {
	ca, p := issueForRotation(t, "node:a", false)
	if _, e := Renew(ca, p, 366, time.Now()); e == nil {
		t.Fatal("too long")
	}
	if _, e := Renew(ca, p, 1, time.Now()); e == nil {
		t.Fatal("shorter lifetime")
	}
	if _, e := Renew(ca, p, 365, time.Now().AddDate(11, 0, 0)); e == nil {
		t.Fatal("expired issuer")
	}
	other, _ := CA("other", time.Now())
	if _, e := Renew(other, p, 365, time.Now()); e == nil {
		t.Fatal("foreign issuer")
	}
	if _, e := Issue(Pair{}, "node", "cluster", nil, false, time.Now()); e == nil {
		t.Fatal("invalid issuer")
	}
}
func TestNewIssueCannotOutliveItsIssuer(t *testing.T) {
	start := time.Now().AddDate(-9, 0, 0).Add(-350 * 24 * time.Hour)
	ca, e := CA("near-end", start)
	if e != nil {
		t.Fatal(e)
	}
	p, e := Issue(ca, "admin", "cluster", nil, false, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	c, _ := leaf(p)
	kp, _ := tls.X509KeyPair(ca.Cert, ca.Key)
	issuer, _ := x509.ParseCertificate(kp.Certificate[0])
	if c.NotAfter.After(issuer.NotAfter) {
		t.Fatal("leaf outlives CA")
	}
	if _, e := Issue(ca, "admin", "cluster", nil, false, issuer.NotAfter.Add(time.Hour)); e == nil {
		t.Fatal("expired signer accepted")
	}
}
func TestInstallRefusesIdentityChange(t *testing.T) {
	ca, p := issueForRotation(t, "node:a", false)
	dir := t.TempDir()
	path, next := filepath.Join(dir, "old"), filepath.Join(dir, "new")
	bundle(t, p, path)
	admin, _ := Issue(ca, "admin", "cluster-test", nil, false, time.Now())
	bundle(t, admin, next)
	original, _ := leaf(p)
	e := InstallRenewal(ca.Cert, path, next, Fingerprint(original))
	if e == nil || !strings.Contains(e.Error(), "PROFILE") {
		t.Fatal("role change", e)
	}
}
