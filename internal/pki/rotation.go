package pki

// Leaf rotation deliberately does not rotate CAs or change identity/roles.
// A combined PEM makes certificate and private-key replacement a single atomic
// operation. The parent directory is an operator-controlled trust boundary.

import (
	"bytes"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/hex"
	"errors"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"reflect"
	"sync"
	"syscall"
	"time"
)

func Fingerprint(c *x509.Certificate) string {
	h := sha256.Sum256(c.Raw)
	return hex.EncodeToString(h[:])
}

func ReadBundle(path string) (Pair, error) {
	if !filepath.IsAbs(path) {
		return Pair{}, errors.New("CERTIFICATE_ABSOLUTE_PATH_REQUIRED")
	}
	for d := filepath.Dir(path); ; d = filepath.Dir(d) {
		s, e := os.Lstat(d)
		if e != nil || !s.IsDir() || s.Mode()&os.ModeSymlink != 0 {
			return Pair{}, errors.New("CERTIFICATE_DIRECTORY_UNSAFE")
		}
		if d == "/" {
			break
		}
	}
	f, e := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if e != nil {
		return Pair{}, errors.New("CERTIFICATE_BUNDLE_UNAVAILABLE")
	}
	defer f.Close()
	s, e := f.Stat()
	if e != nil || !s.Mode().IsRegular() || s.Mode().Perm() != 0600 || s.Size() > 64<<10 {
		return Pair{}, errors.New("PRIVATE_REGULAR_CERTIFICATE_BUNDLE_REQUIRED")
	}
	uid := s.Sys().(*syscall.Stat_t).Uid
	if os.Geteuid() != 0 && uid != uint32(os.Geteuid()) {
		return Pair{}, errors.New("CERTIFICATE_BUNDLE_OWNER_MISMATCH")
	}
	b, e := io.ReadAll(io.LimitReader(f, (64<<10)+1))
	if e != nil || len(b) > 64<<10 {
		return Pair{}, errors.New("CERTIFICATE_BUNDLE_READ_FAILED")
	}
	p := Pair{Cert: b, Key: b}
	if _, e = leaf(p); e != nil {
		return Pair{}, e
	}
	return p, nil
}

func leaf(p Pair) (*x509.Certificate, error) {
	c, e := tls.X509KeyPair(p.Cert, p.Key)
	if e != nil || len(c.Certificate) != 1 {
		return nil, errors.New("ONE_MATCHING_LEAF_KEYPAIR_REQUIRED")
	}
	v, e := x509.ParseCertificate(c.Certificate[0])
	if e != nil || v.IsCA {
		return nil, errors.New("LEAF_CERTIFICATE_REQUIRED")
	}
	return v, nil
}

func sameProfile(a, b *x509.Certificate) bool {
	return bytes.Equal(a.RawSubject, b.RawSubject) && bytes.Equal(a.RawIssuer, b.RawIssuer) &&
		a.KeyUsage == b.KeyUsage && reflect.DeepEqual(a.ExtKeyUsage, b.ExtKeyUsage) &&
		reflect.DeepEqual(a.UnknownExtKeyUsage, b.UnknownExtKeyUsage) &&
		reflect.DeepEqual(a.DNSNames, b.DNSNames) && reflect.DeepEqual(a.IPAddresses, b.IPAddresses) &&
		reflect.DeepEqual(a.EmailAddresses, b.EmailAddresses) && reflect.DeepEqual(a.URIs, b.URIs)
}

func verified(ca []byte, p Pair, usage x509.ExtKeyUsage, now time.Time) (*x509.Certificate, error) {
	c, e := leaf(p)
	if e != nil {
		return nil, e
	}
	pool, e := Pool(ca)
	if e != nil {
		return nil, e
	}
	if _, e = c.Verify(x509.VerifyOptions{Roots: pool, KeyUsages: []x509.ExtKeyUsage{usage}, CurrentTime: now}); e != nil {
		return nil, errors.New("LEAF_NOT_CURRENTLY_TRUSTED")
	}
	return c, nil
}

// Reloader pins identity, SANs, usages and issuer on process startup. A changed
// credential must extend the expiry and never move NotBefore backwards. There is
// no fallback to cached keys on a malformed/expired/replaced file. Existing TLS
// connections keep their original identity; this is not immediate revocation.
// Anti-rollback is process-local; operators must not restore obsolete PEM files.
type Reloader struct {
	mu      sync.Mutex
	ca      []byte
	path    string
	usage   x509.ExtKeyUsage
	current *x509.Certificate
	now     func() time.Time
}

func NewReloader(ca []byte, path string, usage x509.ExtKeyUsage) (*Reloader, error) {
	p, e := ReadBundle(path)
	if e != nil {
		return nil, e
	}
	c, e := verified(ca, p, usage, time.Now())
	if e != nil {
		return nil, e
	}
	return &Reloader{ca: append([]byte(nil), ca...), path: path, usage: usage, current: c, now: time.Now}, nil
}
func (r *Reloader) Certificate() (*tls.Certificate, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	p, e := ReadBundle(r.path)
	if e != nil {
		return nil, e
	}
	c, e := verified(r.ca, p, r.usage, r.now())
	if e != nil {
		return nil, e
	}
	if !sameProfile(r.current, c) {
		return nil, errors.New("CERTIFICATE_ROTATION_IDENTITY_CHANGE_FORBIDDEN")
	}
	if !bytes.Equal(r.current.Raw, c.Raw) && (c.NotBefore.Before(r.current.NotBefore) || !c.NotAfter.After(r.current.NotAfter) || c.SerialNumber.Cmp(r.current.SerialNumber) == 0) {
		return nil, errors.New("CERTIFICATE_ROTATION_ROLLBACK_OR_SERIAL_REUSE")
	}
	pair, e := tls.X509KeyPair(p.Cert, p.Key)
	if e != nil {
		return nil, e
	}
	pair.Leaf = c
	r.current = c
	return &pair, nil
}

type checkedTransport struct {
	base   *http.Transport
	loader *Reloader
}

func (t *checkedTransport) RoundTrip(r *http.Request) (*http.Response, error) {
	// Validate even for requests reusing an idle TLS connection.
	if _, e := t.loader.Certificate(); e != nil {
		return nil, e
	}
	return t.base.RoundTrip(r)
}
func (t *checkedTransport) CloseIdleConnections() { t.base.CloseIdleConnections() }

func ClientBundle(ca []byte, path string) (*http.Client, error) {
	roots, e := Pool(ca)
	if e != nil {
		return nil, e
	}
	loader, e := NewReloader(ca, path, x509.ExtKeyUsageClientAuth)
	if e != nil {
		return nil, e
	}
	cfg := &tls.Config{MinVersion: tls.VersionTLS13, RootCAs: roots, GetClientCertificate: func(*tls.CertificateRequestInfo) (*tls.Certificate, error) { return loader.Certificate() }}
	tr := &http.Transport{Proxy: nil, TLSClientConfig: cfg, ResponseHeaderTimeout: 10 * time.Second, MaxIdleConns: 16, MaxIdleConnsPerHost: 8, IdleConnTimeout: 30 * time.Second}
	return &http.Client{Transport: &checkedTransport{tr, loader}, Timeout: 20 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}, nil
}
func ServerFiles(caFile, certFile, keyFile string) (*tls.Config, error) {
	ca, e := os.ReadFile(caFile)
	if e != nil {
		return nil, e
	}
	if certFile != keyFile {
		cert, e := os.ReadFile(certFile)
		if e != nil {
			return nil, e
		}
		key, e := os.ReadFile(keyFile)
		if e != nil {
			return nil, e
		}
		return Server(ca, Pair{Cert: cert, Key: key})
	}
	roots, e := Pool(ca)
	if e != nil {
		return nil, e
	}
	loader, e := NewReloader(ca, certFile, x509.ExtKeyUsageServerAuth)
	if e != nil {
		return nil, e
	}
	return &tls.Config{MinVersion: tls.VersionTLS13, ClientCAs: roots, ClientAuth: tls.RequireAndVerifyClientCert, SessionTicketsDisabled: true,
		GetCertificate: func(*tls.ClientHelloInfo) (*tls.Certificate, error) { return loader.Certificate() }}, nil
}

// Renew generates a new leaf key, keeping the existing identity and roles. The
// CA key is an OFFLINE authority input. Possession of a leaf alone cannot renew
// or elevate it. An expired leaf can be recovered only by this CA-owning command.
func Renew(ca Pair, old Pair, days int, now time.Time) (Pair, error) {
	if days < 1 || days > 365 {
		return Pair{}, errors.New("LEAF_VALIDITY_OUTSIDE_1_TO_365_DAYS")
	}
	c, e := leaf(old)
	if e != nil {
		return Pair{}, e
	}
	authority, e := tls.X509KeyPair(ca.Cert, ca.Key)
	if e != nil {
		return Pair{}, errors.New("SIGNING_CA_INVALID")
	}
	issuer, e := x509.ParseCertificate(authority.Certificate[0])
	if e != nil {
		return Pair{}, e
	}
	if !issuer.IsCA || issuer.KeyUsage&x509.KeyUsageCertSign == 0 || now.Before(issuer.NotBefore) || !now.Before(issuer.NotAfter) {
		return Pair{}, errors.New("SIGNING_CA_NOT_VALID")
	}
	if e = c.CheckSignatureFrom(issuer); e != nil {
		return Pair{}, errors.New("LEAF_ISSUER_MISMATCH")
	}
	if c.NotBefore.After(now) || len(c.UnhandledCriticalExtensions) > 0 || len(c.UnknownExtKeyUsage) > 0 || c.KeyUsage != x509.KeyUsageDigitalSignature {
		return Pair{}, errors.New("LEAF_PROFILE_UNSUPPORTED")
	}
	expiry := now.Add(time.Duration(days) * 24 * time.Hour)
	if expiry.After(issuer.NotAfter) {
		expiry = issuer.NotAfter
	}
	if !expiry.After(c.NotAfter) {
		return Pair{}, errors.New("RENEWAL_MUST_EXTEND_EXPIRY_WITHIN_CA_VALIDITY")
	}
	key, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if e != nil {
		return Pair{}, e
	}
	s, e := serial()
	if e != nil {
		return Pair{}, e
	}
	before := now.Add(-5 * time.Minute)
	if before.Before(c.NotBefore) {
		before = c.NotBefore
	}
	template := &x509.Certificate{SerialNumber: s, Subject: c.Subject, NotBefore: before, NotAfter: expiry, KeyUsage: c.KeyUsage, ExtKeyUsage: c.ExtKeyUsage,
		DNSNames: c.DNSNames, IPAddresses: c.IPAddresses, EmailAddresses: c.EmailAddresses, URIs: c.URIs}
	der, e := x509.CreateCertificate(rand.Reader, template, issuer, &key.PublicKey, authority.PrivateKey)
	if e != nil {
		return Pair{}, e
	}
	return encode(der, key)
}

// InstallRenewal is compare-and-swap against the current leaf fingerprint. It
// preserves the service account ownership of an existing bundle when run as root.
// There are no shell calls, no CA changes, and no automatic service restarts.
func InstallRenewal(ca []byte, current, candidate, expected string) error {
	if current == candidate {
		return errors.New("RENEWAL_CANDIDATE_MUST_BE_SEPARATE")
	}
	fd, e := os.OpenFile(current+".renew.lock", os.O_CREATE|os.O_RDWR|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0600)
	if e != nil {
		return e
	}
	defer fd.Close()
	st, e := fd.Stat()
	if e != nil || !st.Mode().IsRegular() || st.Mode().Perm() != 0600 {
		return errors.New("RENEWAL_LOCK_UNSAFE")
	}
	if e = syscall.Flock(int(fd.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		return errors.New("RENEWAL_ALREADY_IN_PROGRESS")
	}
	old, e := ReadBundle(current)
	if e != nil {
		return e
	}
	previous, e := leaf(old)
	if e != nil {
		return e
	}
	next, e := ReadBundle(candidate)
	if e != nil {
		return e
	}
	newLeaf, e := verified(ca, next, x509.ExtKeyUsageAny, time.Now())
	if e != nil {
		return e
	}
	if Fingerprint(previous) == Fingerprint(newLeaf) {
		return nil
	} // lost atomic-install ACK
	if Fingerprint(previous) != expected {
		return errors.New("CURRENT_CERTIFICATE_CHANGED")
	}
	if !sameProfile(previous, newLeaf) || !newLeaf.NotAfter.After(previous.NotAfter) || newLeaf.NotBefore.Before(previous.NotBefore) || newLeaf.SerialNumber.Cmp(previous.SerialNumber) == 0 {
		return errors.New("RENEWAL_PROFILE_OR_VALIDITY_INVALID")
	}
	roots, e := Pool(ca)
	if e != nil {
		return e
	}
	// Signature trust of the old leaf remains required even if it has expired.
	when := previous.NotBefore.Add(time.Second)
	if _, e = previous.Verify(x509.VerifyOptions{Roots: roots, CurrentTime: when, KeyUsages: []x509.ExtKeyUsage{x509.ExtKeyUsageAny}}); e != nil {
		return errors.New("PREVIOUS_LEAF_NOT_TRUSTED")
	}
	info, e := os.Lstat(current)
	if e != nil {
		return e
	}
	owner := info.Sys().(*syscall.Stat_t)
	f, e := os.CreateTemp(filepath.Dir(current), ".leaf-renew-*")
	if e != nil {
		return e
	}
	temp := f.Name()
	defer os.Remove(temp)
	fail := func(e error) error { f.Close(); return e }
	if e = f.Chmod(0600); e != nil {
		return fail(e)
	}
	if os.Geteuid() == 0 {
		if e = f.Chown(int(owner.Uid), int(owner.Gid)); e != nil {
			return fail(e)
		}
	}
	if _, e = f.Write(next.Cert); e != nil {
		return fail(e)
	}
	if e = f.Sync(); e != nil {
		return fail(e)
	}
	if e = f.Close(); e != nil {
		return e
	}
	// Recheck the expected current leaf after staging, before mutation.
	last, e := ReadBundle(current)
	if e != nil {
		return e
	}
	lastLeaf, _ := leaf(last)
	if Fingerprint(lastLeaf) != expected {
		return errors.New("CURRENT_CERTIFICATE_CHANGED")
	}
	if e = os.Rename(temp, current); e != nil {
		return e
	}
	dir, e := os.Open(filepath.Dir(current))
	if e != nil {
		return e
	}
	defer dir.Close()
	return dir.Sync()
}
