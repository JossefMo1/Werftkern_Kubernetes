package cli

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"syscall"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/pki"
)

// These are offline administrative operations, not an online signing service.
// The CA key is never copied to workers or placed into emitted public metadata.
func certificateCommand(args []string) error {
	if len(args) == 0 {
		return errors.New("certificate inspect|bundle|renew|install; see CERTIFICATE-ROTATION.md")
	}
	f := parser("certificate " + args[0])
	caPath := f.String("ca", "", "Trusted CA certificate file")
	bundle := f.String("bundle", "", "Current combined PEM (mode 0600)")
	cert := f.String("cert", "", "Existing leaf certificate for bundle creation")
	key := f.String("key", "", "Existing private key for bundle creation")
	caKey := f.String("ca-key", "", "Offline issuing CA private key")
	out := f.String("out", "", "New candidate PEM path; never overwritten")
	candidate := f.String("candidate", "", "Candidate combined PEM")
	expected := f.String("expect-cert", "", "SHA256 of current leaf DER")
	identity := f.String("confirm-identity", "", "Exact current certificate CN")
	days := f.Int("days", 365, "Validity, 1..365 days and capped by issuer expiry")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	if f.NArg() != 0 {
		return errors.New("UNEXPECTED_CERTIFICATE_ARGUMENT")
	}
	if args[0] == "inspect" {
		p, e := pki.ReadBundle(*bundle)
		if e != nil {
			return e
		}
		return certificateSummary(p)
	}
	ca, e := os.ReadFile(*caPath)
	if e != nil {
		return errors.New("CA_CERTIFICATE_UNAVAILABLE")
	}
	switch args[0] {
	case "bundle":
		cb, e := os.ReadFile(*cert)
		if e != nil {
			return e
		}
		kb, e := privateCertificateInput(*key)
		if e != nil {
			return e
		}
		pair := pki.Pair{Cert: cb, Key: kb}
		kp, e := tls.X509KeyPair(cb, kb)
		if e != nil || len(kp.Certificate) != 1 {
			return errors.New("ONE_LEAF_KEYPAIR_REQUIRED")
		}
		c, e := x509.ParseCertificate(kp.Certificate[0])
		if e != nil || c.IsCA {
			return errors.New("LEAF_CERTIFICATE_REQUIRED")
		}
		roots, e := pki.Pool(ca)
		if e != nil {
			return e
		}
		if _, e = c.Verify(x509.VerifyOptions{Roots: roots, KeyUsages: []x509.ExtKeyUsage{x509.ExtKeyUsageAny}}); e != nil {
			return errors.New("CURRENTLY_VALID_LEAF_REQUIRED")
		}
		if e = exclusiveCertificateOutput(*out, append(append([]byte{}, cb...), kb...)); e != nil {
			return e
		}
		return certificateSummary(pair)
	case "renew":
		old, e := pki.ReadBundle(*bundle)
		if e != nil {
			return e
		}
		pair, e := tls.X509KeyPair(old.Cert, old.Key)
		if e != nil {
			return e
		}
		c, e := x509.ParseCertificate(pair.Certificate[0])
		if e != nil {
			return e
		}
		if *identity != c.Subject.CommonName {
			return errors.New("EXACT_CERTIFICATE_IDENTITY_CONFIRMATION_REQUIRED")
		}
		authority, e := privateCertificateInput(*caKey)
		if e != nil {
			return e
		}
		next, e := pki.Renew(pki.Pair{Cert: ca, Key: authority}, old, *days, time.Now())
		if e != nil {
			return e
		}
		if e = exclusiveCertificateOutput(*out, append(append([]byte{}, next.Cert...), next.Key...)); e != nil {
			return e
		}
		return certificateSummary(next)
	case "install":
		if len(*expected) != 64 {
			return errors.New("CURRENT_CERTIFICATE_SHA256_REQUIRED")
		}
		if e = pki.InstallRenewal(ca, *bundle, *candidate, *expected); e != nil {
			return e
		}
		p, e := pki.ReadBundle(*bundle)
		if e != nil {
			return e
		}
		return certificateSummary(p)
	default:
		return errors.New("UNKNOWN_CERTIFICATE_OPERATION")
	}
}
func privateCertificateInput(path string) ([]byte, error) {
	if e := certificateParents(path); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if e != nil {
		return nil, errors.New("PRIVATE_CERTIFICATE_KEY_UNAVAILABLE")
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil || !st.Mode().IsRegular() || st.Mode().Perm() != 0600 || st.Size() > 64<<10 {
		return nil, errors.New("PRIVATE_REGULAR_KEY_FILE_REQUIRED")
	}
	uid := st.Sys().(*syscall.Stat_t).Uid
	if os.Geteuid() != 0 && uid != uint32(os.Geteuid()) {
		return nil, errors.New("PRIVATE_KEY_OWNER_MISMATCH")
	}
	b, e := io.ReadAll(io.LimitReader(f, (64<<10)+1))
	if e != nil || len(b) > 64<<10 {
		return nil, errors.New("PRIVATE_KEY_READ_FAILED")
	}
	return b, nil
}
func exclusiveCertificateOutput(path string, raw []byte) error {
	if e := certificateParents(path); e != nil {
		return e
	}
	if !filepath.IsAbs(path) {
		return errors.New("NEW_ABSOLUTE_CERTIFICATE_PATH_REQUIRED")
	}
	// Atomic no-replace, never truncate an existing candidate or symlink.
	dir := filepath.Dir(path)
	s, e := os.Lstat(dir)
	if e != nil || !s.IsDir() || s.Mode()&os.ModeSymlink != 0 {
		return errors.New("TRUSTED_EXISTING_OUTPUT_DIRECTORY_REQUIRED")
	}
	f, e := os.CreateTemp(dir, ".certificate-*")
	if e != nil {
		return e
	}
	tmp := f.Name()
	defer os.Remove(tmp)
	fail := func(e error) error { f.Close(); return e }
	if e = f.Chmod(0600); e != nil {
		return fail(e)
	}
	if _, e = f.Write(raw); e != nil {
		return fail(e)
	}
	if e = f.Sync(); e != nil {
		return fail(e)
	}
	if e = f.Close(); e != nil {
		return e
	}
	if e = os.Link(tmp, path); e != nil {
		return fmt.Errorf("CERTIFICATE_OUTPUT_EXISTS_OR_UNAVAILABLE: %w", e)
	}
	d, e := os.Open(dir)
	if e != nil {
		return e
	}
	defer d.Close()
	return d.Sync()
}
func certificateSummary(p pki.Pair) error {
	pair, e := tls.X509KeyPair(p.Cert, p.Key)
	if e != nil {
		return e
	}
	c, e := x509.ParseCertificate(pair.Certificate[0])
	if e != nil {
		return e
	}
	return json.NewEncoder(os.Stdout).Encode(map[string]any{
		"identity": c.Subject.CommonName, "organization": c.Subject.Organization, "certificateSHA256": pki.Fingerprint(c),
		"notBefore": c.NotBefore, "notAfter": c.NotAfter, "expired": !time.Now().Before(c.NotAfter), "caRotated": false,
		"note": "leaf only; existing TLS connections and CA trust are unchanged",
	})
}

func certificateParents(path string) error {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return errors.New("CLEAN_ABSOLUTE_CERTIFICATE_PATH_REQUIRED")
	}
	for dir := filepath.Dir(path); ; dir = filepath.Dir(dir) {
		st, e := os.Lstat(dir)
		if e != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return errors.New("CERTIFICATE_PARENT_DIRECTORY_UNSAFE")
		}
		if dir == "/" {
			return nil
		}
	}
}
