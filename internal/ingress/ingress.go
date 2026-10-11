// Package ingress implements an explicitly configured HTTPS application edge.
// It has no access to an administrator certificate, Docker, volumes or secrets.
// Read-only gateway identities obtain only their allowed service endpoints.
package ingress

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/discovery"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
)

type Route struct {
	Host    string `json:"host"`
	Service string `json:"service"`
}
type Config struct {
	Client       config.Client `json:"client"`
	GatewayID    string        `json:"gatewayId"`
	Listen       string        `json:"listen"`
	Public       bool          `json:"public"`
	Certificate  string        `json:"certificate"`
	PrivateKey   string        `json:"privateKey"`
	AllowedCIDRs []string      `json:"allowedCIDRs"`
	UpstreamMode string        `json:"upstreamMode"`
	Routes       []Route       `json:"routes"`
}

func hostName(s string) bool {
	if len(s) < 1 || len(s) > 253 || s != strings.ToLower(s) || strings.HasSuffix(s, ".") || strings.Contains(s, ":") {
		return false
	}
	for _, part := range strings.Split(s, ".") {
		if len(part) < 1 || len(part) > 63 || part[0] == '-' || part[len(part)-1] == '-' {
			return false
		}
		for _, c := range part {
			if c != '-' && (c < 'a' || c > 'z') && (c < '0' || c > '9') {
				return false
			}
		}
	}
	return true
}
func (c Config) Validate() error {
	if e := config.ValidateClient(c.Client); e != nil {
		return e
	}
	if !model.ValidID(c.GatewayID) || c.UpstreamMode != "private-http" || len(c.Routes) < 1 || len(c.Routes) > 50 || len(c.AllowedCIDRs) < 1 || len(c.AllowedCIDRs) > 64 {
		return errors.New("INGRESS_CONFIGURATION_INVALID")
	}
	ip, p, e := net.SplitHostPort(c.Listen)
	port, pe := strconv.Atoi(p)
	if e != nil || pe != nil || net.ParseIP(ip) == nil || port < 1024 || port > 65535 || !c.Public && !model.PrivateAddress(ip) {
		return errors.New("INGRESS_EXPLICIT_LISTEN_REQUIRED")
	}
	for _, cidr := range c.AllowedCIDRs {
		_, n, e := net.ParseCIDR(cidr)
		if e != nil || n.IP.To4() == nil || !model.PrivateAddress(n.IP.String()) {
			return errors.New("INGRESS_PRIVATE_UPSTREAM_CIDR_REQUIRED")
		}
		ones, _ := n.Mask.Size()
		if ones < 8 {
			return errors.New("INGRESS_UPSTREAM_CIDR_TOO_BROAD")
		}
	}
	seen := map[string]bool{}
	for _, r := range c.Routes {
		if !hostName(r.Host) || !model.ValidName(r.Service) || seen[r.Host] {
			return errors.New("INGRESS_ROUTE_INVALID")
		}
		seen[r.Host] = true
	}
	return nil
}

type Gateway struct {
	config    Config
	transport http.RoundTripper
	now       func() time.Time
	mu        sync.RWMutex
	snapshot  discovery.Snapshot
	routes    map[string]string
	seq       atomic.Uint64
	active    chan struct{}
	invalid   bool
}

func New(c Config) (*Gateway, error) {
	if e := c.Validate(); e != nil {
		return nil, e
	}
	g := &Gateway{config: c, now: time.Now, routes: map[string]string{}, active: make(chan struct{}, 256)}
	for _, r := range c.Routes {
		g.routes[r.Host] = r.Service
	}
	g.transport = &http.Transport{Proxy: nil, DialContext: (&net.Dialer{Timeout: 3 * time.Second, KeepAlive: 30 * time.Second}).DialContext, MaxIdleConns: 128, MaxIdleConnsPerHost: 16, MaxConnsPerHost: 64, IdleConnTimeout: 30 * time.Second, ResponseHeaderTimeout: 5 * time.Second, ExpectContinueTimeout: time.Second}
	return g, nil
}
func (g *Gateway) Accept(s discovery.Snapshot) error {
	now := g.now()
	if s.ClusterID != g.config.Client.ClusterID || s.Revision < 1 || s.At.IsZero() || now.Sub(s.At) > 15*time.Second || s.At.Sub(now) > 5*time.Second || len(s.Endpoints) > model.MaxAllocations {
		return errors.New("INGRESS_SNAPSHOT_INVALID_OR_STALE")
	}
	// Copy before sorting/storing; callers cannot mutate an accepted snapshot.
	s.Endpoints = append([]discovery.Endpoint{}, s.Endpoints...)
	seen := map[string]bool{}
	for _, e := range s.Endpoints {
		if !model.ValidName(e.Service) || !model.ValidID(e.ID) || !model.PrivateAddress(e.Address) || e.Port < 1024 || e.Port > 65535 || seen[e.ID] {
			return errors.New("INGRESS_ENDPOINT_INVALID")
		}
		seen[e.ID] = true
		if !g.allowedAddress(e.Address, e.Port) {
			return errors.New("INGRESS_ENDPOINT_OUTSIDE_ALLOWLIST")
		}
	}
	sort.Slice(s.Endpoints, func(i, j int) bool { return s.Endpoints[i].ID < s.Endpoints[j].ID })
	g.mu.Lock()
	defer g.mu.Unlock()
	if s.Revision < g.snapshot.Revision || !g.snapshot.At.IsZero() && s.At.Before(g.snapshot.At) {
		return errors.New("INGRESS_SNAPSHOT_REPLAY")
	}
	if s.Revision == g.snapshot.Revision {
		// Time-based readiness expiry can REMOVE endpoints without an etcd write.
		old := map[string]string{}
		for _, e := range g.snapshot.Endpoints {
			old[e.ID] = model.Hash(e)
		}
		for _, e := range s.Endpoints {
			if old[e.ID] != model.Hash(e) {
				return errors.New("INGRESS_REVISION_CONTENT_CONFLICT")
			}
		}
	}
	g.snapshot = s
	g.invalid = false
	return nil
}
func (g *Gateway) allowedAddress(ip string, port int) bool {
	target := net.JoinHostPort(ip, strconv.Itoa(port))
	if target == g.config.Listen {
		return false
	}
	servers := append([]string{g.config.Client.Server}, g.config.Client.Servers...)
	for _, server := range servers {
		u, e := url.Parse(server)
		if e == nil && u.Host == target {
			return false
		}
	}
	for _, raw := range g.config.AllowedCIDRs {
		_, cidr, _ := net.ParseCIDR(raw)
		if cidr.Contains(net.ParseIP(ip)) {
			return true
		}
	}
	return false
}
func (g *Gateway) Invalidate() {
	g.mu.Lock()
	g.invalid = true
	g.mu.Unlock()
}
func (g *Gateway) selectEndpoint(service string) (discovery.Endpoint, bool) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if g.invalid || g.snapshot.At.IsZero() || g.now().Sub(g.snapshot.At) > 15*time.Second {
		return discovery.Endpoint{}, false
	}
	options := []discovery.Endpoint{}
	for _, e := range g.snapshot.Endpoints {
		if e.Service == service {
			options = append(options, e)
		}
	}
	if len(options) == 0 {
		return discovery.Endpoint{}, false
	}
	return options[(g.seq.Add(1)-1)%uint64(len(options))], true
}
func (g *Gateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("X-Content-Type-Options", "nosniff")
	if r.Method == "CONNECT" || r.Method == "TRACE" || r.URL.IsAbs() || r.Header.Get("Upgrade") != "" {
		http.Error(w, "Unsupported request", 405)
		return
	}
	host := r.Host
	if strings.Contains(host, ":") {
		h, _, e := net.SplitHostPort(host)
		if e != nil {
			http.Error(w, "Invalid host", 400)
			return
		}
		host = h
	}
	host = strings.ToLower(host)
	service, ok := g.routes[host]
	if !ok || !hostName(host) {
		http.Error(w, "Unknown route", 404)
		return
	}
	if r.TLS == nil || !strings.EqualFold(r.TLS.ServerName, host) {
		http.Error(w, "TLS server name must match route", 421)
		return
	}
	if r.ContentLength < 0 {
		http.Error(w, "Content-Length required", 411)
		return
	}
	if r.ContentLength > 8<<20 {
		http.Error(w, "Request too large", 413)
		return
	}
	select {
	case g.active <- struct{}{}:
		defer func() { <-g.active }()
	default:
		http.Error(w, "Ingress busy", 503)
		return
	}
	endpoint, ok := g.selectEndpoint(service)
	if !ok {
		w.Header().Set("Retry-After", "3")
		http.Error(w, "No fresh ready endpoint", 503)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 8<<20)
	target := net.JoinHostPort(endpoint.Address, strconv.Itoa(endpoint.Port))
	proxy := httputil.ReverseProxy{Transport: g.transport, Rewrite: func(p *httputil.ProxyRequest) {
		p.Out.URL.Scheme = "http"
		p.Out.URL.Host = target
		p.Out.Host = host
		// ProxyRequest strips standard forwarding fields; remove alternate client
		// identity headers too. Application Authorization and Cookie remain intact.
		for _, key := range []string{"Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Real-Ip", "X-Original-Url", "X-Rewrite-Url", "Proxy-Authorization", "Proxy-Connection"} {
			p.Out.Header.Del(key)
		}
		p.SetXForwarded()
		p.Out.Header.Set("X-Forwarded-Proto", "https")
	}, ErrorLog: log.New(&discardLog{}, "", 0), ErrorHandler: func(w http.ResponseWriter, r *http.Request, e error) { http.Error(w, "Upstream unavailable", 502) }}
	proxy.ServeHTTP(w, r)
}

type discardLog struct{}

func (*discardLog) Write(p []byte) (int, error) { return len(p), nil }

// Serve does not terminate TLS verification for the control-plane client. Edge
// certificates must come from an operator-managed issuer; there is no ACME hack.
func (g *Gateway) Serve(ctx context.Context) error {
	cert, e := tls.LoadX509KeyPair(g.config.Certificate, g.config.PrivateKey)
	if e != nil {
		return errors.New("INGRESS_TLS_CERTIFICATE_UNAVAILABLE")
	}
	leaf, e := x509.ParseCertificate(cert.Certificate[0])
	if e != nil {
		return errors.New("INGRESS_TLS_CERTIFICATE_INVALID")
	}
	if time.Now().Before(leaf.NotBefore) || !time.Now().Before(leaf.NotAfter) {
		return errors.New("INGRESS_TLS_CERTIFICATE_EXPIRED_OR_NOT_YET_VALID")
	}
	for _, route := range g.config.Routes {
		if leaf.VerifyHostname(route.Host) != nil {
			return errors.New("INGRESS_TLS_ROUTE_HOSTNAME_MISMATCH")
		}
	}
	srv := &http.Server{Addr: g.config.Listen, Handler: g, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 30 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 << 10, TLSConfig: &tls.Config{MinVersion: tls.VersionTLS13, Certificates: []tls.Certificate{cert}}}
	done := make(chan struct{})
	defer close(done)
	go func() {
		select {
		case <-ctx.Done():
			deadline, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			_ = srv.Shutdown(deadline)
		case <-done:
		}
	}()
	e = srv.ListenAndServeTLS("", "")
	if e == http.ErrServerClosed {
		return nil
	}
	return fmt.Errorf("INGRESS_SERVE_FAILED: %w", e)
}
