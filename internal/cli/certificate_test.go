package cli

import (
	"crypto/tls"
	"crypto/x509"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/pki"
)

func TestCertificateCommandsRoundTripAndNoOverwrite(t *testing.T) {
	dir := t.TempDir()
	now := time.Now()
	ca, e := pki.CA("offline-test", now.Add(-48*time.Hour))
	if e != nil {
		t.Fatal(e)
	}
	old, e := pki.Issue(ca, "node:test", "cluster-test", nil, false, now.Add(-24*time.Hour))
	if e != nil {
		t.Fatal(e)
	}
	files := map[string][]byte{"ca.crt": ca.Cert, "ca.key": ca.Key, "old.crt": old.Cert, "old.key": old.Key}
	for name, raw := range files {
		if e = os.WriteFile(filepath.Join(dir, name), raw, 0600); e != nil {
			t.Fatal(e)
		}
	}
	bundle := filepath.Join(dir, "current.pem")
	candidate := filepath.Join(dir, "next.pem")
	create := []string{"bundle", "--ca", filepath.Join(dir, "ca.crt"), "--cert", filepath.Join(dir, "old.crt"), "--key", filepath.Join(dir, "old.key"), "--out", bundle}
	if e = certificateCommand(create); e != nil {
		t.Fatal(e)
	}
	if e = certificateCommand(create); e == nil {
		t.Fatal("overwrote private bundle")
	}
	pair, _ := tls.X509KeyPair(old.Cert, old.Key)
	leaf, _ := x509.ParseCertificate(pair.Certificate[0])
	fp := pki.Fingerprint(leaf)
	renew := []string{"renew", "--ca", filepath.Join(dir, "ca.crt"), "--ca-key", filepath.Join(dir, "ca.key"), "--bundle", bundle, "--out", candidate, "--days", "365", "--confirm-identity", "node:test"}
	if e = certificateCommand(renew); e != nil {
		t.Fatal(e)
	}
	install := []string{"install", "--ca", filepath.Join(dir, "ca.crt"), "--bundle", bundle, "--candidate", candidate, "--expect-cert", fp}
	if e = certificateCommand(install); e != nil {
		t.Fatal(e)
	}
	if e = certificateCommand(install); e != nil {
		t.Fatal("replay", e)
	}
	if e = certificateCommand([]string{"inspect", "--bundle", bundle}); e != nil {
		t.Fatal(e)
	}
}
func TestCertificatePrivateParentsAndConfirmation(t *testing.T) {
	dir := t.TempDir()
	real := filepath.Join(dir, "real")
	if e := os.Mkdir(real, 0700); e != nil {
		t.Fatal(e)
	}
	link := filepath.Join(dir, "linked")
	if e := os.Symlink(real, link); e != nil {
		t.Fatal(e)
	}
	if e := exclusiveCertificateOutput(filepath.Join(link, "output.pem"), []byte("must-not-write")); e == nil {
		t.Fatal("symlink parent allowed")
	}
	if _, e := os.Stat(filepath.Join(real, "output.pem")); !os.IsNotExist(e) {
		t.Fatal("wrote through symlink")
	}
	if _, e := privateCertificateInput(filepath.Join(link, "key")); e == nil {
		t.Fatal("read symlink parent")
	}
	if e := exclusiveCertificateOutput("relative.pem", []byte("no")); e == nil {
		t.Fatal("relative path")
	}
}
