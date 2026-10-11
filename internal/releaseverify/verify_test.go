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
