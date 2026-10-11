// Package releaseverify authenticates exact release bytes using an operator-
// trusted Ed25519 key. It is not a software security or production certificate.
package releaseverify

import (
	"crypto/ed25519"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/pem"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/strictjson"
	"io"
	"os"
	"regexp"
)

type Manifest struct {
	Format         string   `json:"format"`
	Version        string   `json:"version"`
	PackageSHA256  string   `json:"packageSha256"`
	PackageVersion string   `json:"packageVersion"`
	StateSchema    int      `json:"stateSchema"`
	Sources        []string `json:"sources"`
	Architecture   string   `json:"architecture"`
}

func Verify(raw, sig, key []byte, packagePath string) (Manifest, error) {
	var m Manifest
	if len(raw) > 65536 || len(sig) != ed25519.SignatureSize {
		return m, errors.New("RELEASE_ENVELOPE_INVALID")
	}
	p, _ := pem.Decode(key)
	if p == nil || p.Type != "PUBLIC KEY" {
		return m, errors.New("TRUSTED_ED25519_PUBLIC_KEY_REQUIRED")
	}
	v, e := x509.ParsePKIXPublicKey(p.Bytes)
	if e != nil {
		return m, e
	}
	pub, ok := v.(ed25519.PublicKey)
	if !ok || !ed25519.Verify(pub, raw, sig) {
		return m, errors.New("RELEASE_SIGNATURE_INVALID")
	}
	if e = strictjson.Unmarshal(raw, &m); e != nil {
		return m, e
	}
	version := regexp.MustCompile(`^[0-9]+\.[0-9]+\.[0-9]+(?:[-~][a-z0-9.]+)?$`)
	if m.Format != "werftkern-release/v1" || !version.MatchString(m.Version) || !version.MatchString(m.PackageVersion) || m.StateSchema != model.StateSchema || m.Architecture != "amd64" || len(m.Sources) == 0 || len(m.Sources) > 20 {
		return m, errors.New("RELEASE_CONTRACT_UNSUPPORTED")
	}
	for _, s := range m.Sources {
		if !version.MatchString(s) {
			return m, errors.New("SOURCE_VERSION_INVALID")
		}
	}
	f, e := os.Open(packagePath)
	if e != nil {
		return m, e
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil || !st.Mode().IsRegular() {
		return m, errors.New("PACKAGE_NOT_REGULAR")
	}
	h := sha256.New()
	if _, e = io.Copy(h, f); e != nil {
		return m, e
	}
	if hex.EncodeToString(h.Sum(nil)) != m.PackageSHA256 {
		return m, errors.New("PACKAGE_DIGEST_MISMATCH")
	}
	return m, nil
}
