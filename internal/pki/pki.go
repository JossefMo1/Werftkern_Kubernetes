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
	"math/big"
	"net"
	"net/http"
	"os"
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
func ClientFiles(ca, cert, key string) (*http.Client, error) {
	c, e := os.ReadFile(ca)
	if e != nil {
		return nil, e
	}
	if cert == key {
		return ClientBundle(c, cert)
	}
	b, e := os.ReadFile(cert)
	if e != nil {
		return nil, e
	}
	k, e := os.ReadFile(key)
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
