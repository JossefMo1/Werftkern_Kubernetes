package releaseverify

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSignedReleaseExactBytesAndSchema(t *testing.T) {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	der, _ := x509.MarshalPKIXPublicKey(pub)
	key := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der})
	path := filepath.Join(t.TempDir(), "pkg")
	os.WriteFile(path, []byte("package fixture"), 0600)
	h := sha256.Sum256([]byte("package fixture"))
	m := Manifest{Format: "werftkern-release/v1", Version: "0.2.0-dev.2", PackageVersion: "0.2.0~dev2", PackageSHA256: hex.EncodeToString(h[:]), StateSchema: 2, Sources: []string{"0.2.0~dev2"}, Architecture: "amd64"}
	raw, _ := json.Marshal(m)
	sig := ed25519.Sign(priv, raw)
	if _, e := Verify(raw, sig, key, path); e != nil {
		t.Fatal(e)
	}
	finalLink := filepath.Join(filepath.Dir(path), "pkg-link")
	if err := os.Symlink(path, finalLink); err != nil {
		t.Fatal(err)
	}
	if _, e := Verify(raw, sig, key, finalLink); e == nil {
		t.Fatal("followed final package symlink")
	}
	parentLink := filepath.Join(filepath.Dir(path), "parent-link")
	if err := os.Symlink(filepath.Dir(path), parentLink); err != nil {
		t.Fatal(err)
	}
	if _, e := Verify(raw, sig, key, filepath.Join(parentLink, "pkg")); e == nil {
		t.Fatal("followed package parent symlink")
	}
	raw[0] = ' '
	if _, e := Verify(raw, sig, key, path); e == nil {
		t.Fatal("tampered manifest")
	}
	raw, _ = json.Marshal(m)
	os.WriteFile(path, []byte("changed"), 0600)
	if _, e := Verify(raw, sig, key, path); e == nil {
		t.Fatal("tampered package")
	}
	if _, e := Verify(raw, nil, key, path); e == nil {
		t.Fatal("unsigned")
	}
}

func TestVerifyRejectsOversizedPackageBeforeHashing(t *testing.T) {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	der, _ := x509.MarshalPKIXPublicKey(pub)
	key := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der})
	path := filepath.Join(t.TempDir(), "oversized-package")
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	if err = f.Truncate(maxPackageBytes + 1); err != nil {
		f.Close()
		t.Fatal(err)
	}
	if err = f.Close(); err != nil {
		t.Fatal(err)
	}
	m := Manifest{
		Format: "werftkern-release/v1", Version: "0.2.0-dev.2", PackageVersion: "0.2.0~dev2",
		PackageSHA256: strings.Repeat("0", sha256.Size*2), StateSchema: 2,
		Sources: []string{"0.2.0~dev2"}, Architecture: "amd64",
	}
	raw, _ := json.Marshal(m)
	sig := ed25519.Sign(priv, raw)
	if _, err = Verify(raw, sig, key, path); err == nil || err.Error() != "PACKAGE_TOO_LARGE" {
		t.Fatalf("expected bounded package rejection, got %v", err)
	}
}
