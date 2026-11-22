package pki

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"errors"
	"io"
	"math/big"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"syscall"
	"time"
)

type Pair struct {
	Cert []byte `json:"cert"`
	Key  []byte `json:"key"`
}

func serial() (*big.Int, error) { return rand.Int(rand.Reader, new(big.Int).Lsh(big.NewInt(1), 128)) }
func encode(c []byte, k *ecdsa.PrivateKey) (Pair, error) {
	b, e := x509.MarshalPKCS8PrivateKey(k)
	if e != nil {
		return Pair{}, e
	}
	return Pair{pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: c}), pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: b})}, nil
}
func CA(name string, now time.Time) (Pair, error) {
	key, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if e != nil {
		return Pair{}, e
	}
	s, e := serial()
	if e != nil {
		return Pair{}, e
	}
	c := &x509.Certificate{SerialNumber: s, Subject: pkix.Name{CommonName: name}, NotBefore: now.Add(-5 * time.Minute), NotAfter: now.AddDate(10, 0, 0), KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageCRLSign, BasicConstraintsValid: true, IsCA: true, MaxPathLenZero: true}
	der, e := x509.CreateCertificate(rand.Reader, c, c, &key.PublicKey, key)
	if e != nil {
		return Pair{}, e
	}
	return encode(der, key)
}
func Issue(ca Pair, cn, clusterID string, hosts []string, server bool, now time.Time) (Pair, error) {
	p, e := tls.X509KeyPair(ca.Cert, ca.Key)
	if e != nil {
		return Pair{}, e
	}
	issuer, e := x509.ParseCertificate(p.Certificate[0])
	if e != nil {
		return Pair{}, e
	}
	if !issuer.IsCA || issuer.KeyUsage&x509.KeyUsageCertSign == 0 || now.Before(issuer.NotBefore) || !now.Before(issuer.NotAfter) {
		return Pair{}, errors.New("SIGNING_CA_NOT_VALID")
	}
	key, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if e != nil {
		return Pair{}, e
	}
	s, e := serial()
	if e != nil {
		return Pair{}, e
	}
	c := &x509.Certificate{SerialNumber: s, Subject: pkix.Name{CommonName: cn, Organization: []string{clusterID}}, NotBefore: now.Add(-5 * time.Minute), NotAfter: now.AddDate(1, 0, 0), KeyUsage: x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth}}
	if server {
		c.ExtKeyUsage = []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}
		if cn == "etcd-server" {
			c.ExtKeyUsage = append(c.ExtKeyUsage, x509.ExtKeyUsageClientAuth)
		}
		for _, h := range hosts {
			if ip := net.ParseIP(h); ip != nil {
				c.IPAddresses = append(c.IPAddresses, ip)
			} else {
				c.DNSNames = append(c.DNSNames, h)
			}
		}
	}
	if c.NotAfter.After(issuer.NotAfter) {
		c.NotAfter = issuer.NotAfter
	}
	if c.NotBefore.Before(issuer.NotBefore) {
		c.NotBefore = issuer.NotBefore
	}
	der, e := x509.CreateCertificate(rand.Reader, c, issuer, &key.PublicKey, p.PrivateKey)
	if e != nil {
		return Pair{}, e
	}
	return encode(der, key)
}
func Pool(ca []byte) (*x509.CertPool, error) {
	p := x509.NewCertPool()
	if !p.AppendCertsFromPEM(ca) {
		return nil, errors.New("CA_INVALID")
	}
	return p, nil
}
func Client(ca []byte, pair Pair) (*http.Client, error) {
	roots, e := Pool(ca)
	if e != nil {
		return nil, e
	}
	cert, e := tls.X509KeyPair(pair.Cert, pair.Key)
	if e != nil {
		return nil, e
	}
	t := &http.Transport{TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS13, RootCAs: roots, Certificates: []tls.Certificate{cert}}, ResponseHeaderTimeout: 10 * time.Second, MaxIdleConns: 16, MaxIdleConnsPerHost: 8, IdleConnTimeout: 30 * time.Second}
	return &http.Client{Transport: t, Timeout: 20 * time.Second, CheckRedirect: func(r *http.Request, via []*http.Request) error { return http.ErrUseLastResponse }}, nil
}
// readCredential reads PEM material through a no-follow, regular-file handle.
 // Private keys must be owner-only (0600) and owned by the effective user unless
 // the caller is root. Parent directories must not be writable by group/others.
func readCredential(path string, private bool) ([]byte, error) {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return nil, errors.New("CREDENTIAL_ABSOLUTE_PATH_REQUIRED")
	}
	for dir := filepath.Dir(path); ; dir = filepath.Dir(dir) {
		st, e := os.Lstat(dir)
		if e != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 || st.Mode().Perm()&0022 != 0 {
			return nil, errors.New("CREDENTIAL_PARENT_DIRECTORY_UNSAFE")
		}
		if dir == "/" {
			break
		}
	}
	f, e := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if e != nil {
		return nil, errors.New("CREDENTIAL_FILE_UNAVAILABLE")
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil || !st.Mode().IsRegular() || st.Size() > 64<<10 {
		return nil, errors.New("REGULAR_CREDENTIAL_FILE_REQUIRED")
	}
	if private {
		if st.Mode().Perm() != 0600 {
			return nil, errors.New("PRIVATE_KEY_MODE_0600_REQUIRED")
		}
		owner, ok := st.Sys().(*syscall.Stat_t)
		if !ok || (os.Geteuid() != 0 && owner.Uid != uint32(os.Geteuid())) {
			return nil, errors.New("PRIVATE_KEY_OWNER_MISMATCH")
		}
	} else if st.Mode().Perm()&0022 != 0 {
		return nil, errors.New("CREDENTIAL_FILE_MUST_NOT_BE_WRITABLE")
	}
	b, e := io.ReadAll(io.LimitReader(f, (64<<10)+1))
	if e != nil || len(b) > 64<<10 {
		return nil, errors.New("CREDENTIAL_FILE_READ_FAILED")
	}
	return b, nil
}

func ClientFiles(ca, cert, key string) (*http.Client, error) {
	c, e := readCredential(ca, false)
	if e != nil {
		return nil, e
	}
	if cert == key {
		return ClientBundle(c, cert)
	}
	b, e := readCredential(cert, false)
	if e != nil {
		return nil, e
	}
	k, e := readCredential(key, true)
	if e != nil {
		return nil, e
	}
	return Client(c, Pair{b, k})
}
func Server(ca []byte, pair Pair) (*tls.Config, error) {
	roots, e := Pool(ca)
	if e != nil {
		return nil, e
	}
	cert, e := tls.X509KeyPair(pair.Cert, pair.Key)
	if e != nil {
		return nil, e
	}
	return &tls.Config{MinVersion: tls.VersionTLS13, Certificates: []tls.Certificate{cert}, ClientCAs: roots, ClientAuth: tls.RequireAndVerifyClientCert, SessionTicketsDisabled: true}, nil
}
func ValidateIdentity(ca []byte, p Pair, cn, cluster string) error {
	roots, e := Pool(ca)
	if e != nil {
		return e
	}
	cert, e := tls.X509KeyPair(p.Cert, p.Key)
	if e != nil {
		return e
	}
	leaf, e := x509.ParseCertificate(cert.Certificate[0])
	if e != nil {
		return e
	}
	if _, e = leaf.Verify(x509.VerifyOptions{Roots: roots, KeyUsages: []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth}}); e != nil {
		return e
	}
	if leaf.Subject.CommonName != cn || len(leaf.Subject.Organization) != 1 || leaf.Subject.Organization[0] != cluster {
		return errors.New("CERTIFICATE_IDENTITY_MISMATCH")
	}
	return nil
}
