package ingress

import (
	"bytes"
	"context"
	"crypto/tls"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/discovery"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
)

func cfg() Config {
	return Config{Client: config.Client{Server: "https://127.0.0.1:7443", ClusterID: model.ID()}, GatewayID: model.ID(), Listen: "127.0.0.1:8443", AllowedCIDRs: []string{"127.0.0.0/8"}, UpstreamMode: "private-http", Routes: []Route{{"web.example.test", "web"}}}
}
func snapshot(c Config, server string) discovery.Snapshot {
	ip, p, _ := net.SplitHostPort(strings.TrimPrefix(server, "http://"))
	port, _ := strconv.Atoi(p)
	return discovery.Snapshot{ClusterID: c.Client.ClusterID, Revision: 1, At: time.Now(), Endpoints: []discovery.Endpoint{{Service: "web", ID: model.ID(), Address: ip, Port: port}}}
}
func edge(t *testing.T, g *Gateway) (*httptest.Server, *http.Client) {
	t.Helper()
	ca, e := pki.CA("edge-test", time.Now())
	if e != nil {
		t.Fatal(e)
	}
	pair, e := pki.Issue(ca, "edge", g.config.Client.ClusterID, []string{"web.example.test"}, true, time.Now())
	if e != nil {
		t.Fatal(e)
	}
	cert, e := tls.X509KeyPair(pair.Cert, pair.Key)
	if e != nil {
		t.Fatal(e)
	}
	s := httptest.NewUnstartedServer(g)
	s.TLS = &tls.Config{MinVersion: tls.VersionTLS13, Certificates: []tls.Certificate{cert}}
	s.StartTLS()
	t.Cleanup(s.Close)
	roots, e := pki.Pool(ca.Cert)
	if e != nil {
		t.Fatal(e)
	}
	transport := &http.Transport{TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS13, RootCAs: roots, ServerName: "web.example.test"}, Proxy: nil}
	t.Cleanup(transport.CloseIdleConnections)
	return s, &http.Client{Transport: transport, Timeout: 5 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
}
func TestRealTLSProxyForwardsApplicationNotSpoofedIdentity(t *testing.T) {
	var count atomic.Int64
	app := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count.Add(1)
		if r.Header.Get("Authorization") != "Bearer application-token" || r.Header.Get("Cookie") != "session=app" {
			t.Error("lost application credentials")
		}
		if strings.Contains(r.Header.Get("X-Forwarded-For"), "attacker") || r.Header.Get("X-Real-IP") != "" || r.Header.Get("Forwarded") != "" || r.Header.Get("Proxy-Authorization") != "" {
			t.Error("spoofed forwarding identity")
		}
		if r.Header.Get("X-Forwarded-Proto") != "https" || r.Host != "web.example.test" {
			t.Error("wrong route")
		}
		data, _ := io.ReadAll(r.Body)
		w.Write(data)
	}))
	defer app.Close()
	c := cfg()
	g, e := New(c)
	if e != nil {
		t.Fatal(e)
	}
	if e = g.Accept(snapshot(c, app.URL)); e != nil {
		t.Fatal(e)
	}
	srv, client := edge(t, g)
	r, _ := http.NewRequest("POST", srv.URL+"/checkout", bytes.NewBufferString("actual-request"))
	r.Host = "web.example.test"
	r.Header.Set("Authorization", "Bearer application-token")
	r.Header.Set("Cookie", "session=app")
	r.Header.Set("X-Forwarded-For", "attacker")
	r.Header.Set("X-Real-IP", "attacker")
	r.Header.Set("Forwarded", "for=attacker")
	r.Header.Set("Proxy-Authorization", "do-not-forward")
	response, e := client.Do(r)
	if e != nil {
		t.Fatal(e)
	}
	defer response.Body.Close()
	body, _ := io.ReadAll(response.Body)
	if response.StatusCode != 200 || string(body) != "actual-request" || count.Load() != 1 {
		t.Fatal(response.StatusCode, string(body), count.Load())
	}
}
func TestNoFreshEndpointSNIConfusionAndDeniedMethods(t *testing.T) {
	g, _ := New(cfg())
	s, c := edge(t, g)
	for _, tt := range []struct {
		method, host string
		status       int
	}{{"GET", "web.example.test", 503}, {"GET", "unknown.test", 404}, {"CONNECT", "web.example.test", 405}, {"TRACE", "web.example.test", 405}} {
		r, _ := http.NewRequest(tt.method, s.URL+"/", nil)
		r.Host = tt.host
		res, e := c.Do(r)
		if e != nil {
			t.Fatal(e)
		}
		res.Body.Close()
		if res.StatusCode != tt.status {
			t.Fatal(tt, res.StatusCode)
		}
	}
	req := httptest.NewRequest("GET", "https://web.example.test/", nil)
	req.URL.Scheme = ""
	req.URL.Host = ""
	req.TLS = &tls.ConnectionState{ServerName: "other.example.test"}
	w := httptest.NewRecorder()
	g.ServeHTTP(w, req)
	if w.Code != 421 {
		t.Fatal(w.Code)
	}
}
func TestSnapshotFreshnessReplayScopeAndCIDRValidation(t *testing.T) {
	c := cfg()
	g, _ := New(c)
	now := time.Now()
	g.now = func() time.Time { return now }
	s := snapshot(c, "http://127.0.0.2:22000")
	s.At = now
	if e := g.Accept(s); e != nil {
		t.Fatal(e)
	}
	bad := s
	bad.Revision = 0
	if g.Accept(bad) == nil {
		t.Fatal("invalid revision")
	}
	bad = s
	bad.ClusterID = model.ID()
	if g.Accept(bad) == nil {
		t.Fatal("foreign cluster")
	}
	bad = s
	bad.At = now.Add(-time.Minute)
	if g.Accept(bad) == nil {
		t.Fatal("stale snapshot")
	}
	bad = s
	bad.Endpoints = append([]discovery.Endpoint{}, s.Endpoints...)
	bad.Endpoints[0].Address = "10.20.0.1"
	if g.Accept(bad) == nil {
		t.Fatal("out of allowed CIDR")
	}
	bad = s
	bad.Endpoints = append([]discovery.Endpoint{}, s.Endpoints...)
	bad.Endpoints[0].Port = 7443
	bad.Endpoints[0].Address = "127.0.0.1"
	if g.Accept(bad) == nil {
		t.Fatal("control-plane proxy")
	}
	now = now.Add(16 * time.Second)
	if _, ok := g.selectEndpoint("web"); ok {
		t.Fatal("stale endpoint still selected")
	}
}
func TestSameRevisionMayExpireButNotIntroduceEndpoints(t *testing.T) {
	c := cfg()
	g, _ := New(c)
	s := snapshot(c, "http://127.0.0.2:22000")
	if e := g.Accept(s); e != nil {
		t.Fatal(e)
	}
	expired := s
	expired.Endpoints = nil
	expired.At = s.At.Add(time.Second)
	if e := g.Accept(expired); e != nil {
		t.Fatal(e)
	}
	s.At = expired.At.Add(time.Second)
	if g.Accept(s) == nil {
		t.Fatal("expired endpoint resurrected without state revision")
	}
}
func TestProxyDoesNotReplayFailedPOSTAndInvalidationStopsTraffic(t *testing.T) {
	var requests atomic.Int64
	app := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		conn, _, e := w.(http.Hijacker).Hijack()
		if e == nil {
			conn.Close()
		}
	}))
	defer app.Close()
	c := cfg()
	g, _ := New(c)
	g.Accept(snapshot(c, app.URL))
	s, client := edge(t, g)
	req, _ := http.NewRequest("POST", s.URL, strings.NewReader("mutation"))
	req.Host = "web.example.test"
	res, e := client.Do(req)
	if e != nil {
		t.Fatal(e)
	}
	res.Body.Close()
	if res.StatusCode != 502 || requests.Load() != 1 {
		t.Fatal(res.StatusCode, requests.Load())
	}
	g.Invalidate()
	req, _ = http.NewRequestWithContext(context.Background(), "GET", s.URL, nil)
	req.Host = "web.example.test"
	res, e = client.Do(req)
	if e != nil {
		t.Fatal(e)
	}
	res.Body.Close()
	if res.StatusCode != 503 || requests.Load() != 1 {
		t.Fatal("traffic continued", res.StatusCode)
	}
}
func TestIngressConfigRejectsPublicBindWithoutConsentAndInvalidRoutes(t *testing.T) {
	for _, edit := range []func(*Config){func(c *Config) { c.Listen = "0.0.0.0:8443" }, func(c *Config) { c.Routes[0].Host = "*.example.test" }, func(c *Config) { c.AllowedCIDRs = []string{"0.0.0.0/0"} }, func(c *Config) { c.UpstreamMode = "silently-unencrypted" }} {
		c := cfg()
		edit(&c)
		if c.Validate() == nil {
			t.Fatal("invalid config accepted", c)
		}
	}
}

func TestTransientDiscoveryFailureCanRecoverAtSameStateRevision(t *testing.T) {
	c := cfg()
	g, _ := New(c)
	s := snapshot(c, "http://127.0.0.2:22000")
	if e := g.Accept(s); e != nil {
		t.Fatal(e)
	}
	g.Invalidate()
	if _, ok := g.selectEndpoint("web"); ok {
		t.Fatal("invalidated snapshot routed")
	}
	s.At = s.At.Add(time.Second)
	if e := g.Accept(s); e != nil {
		t.Fatal("valid same-revision recovery rejected", e)
	}
	if _, ok := g.selectEndpoint("web"); !ok {
		t.Fatal("recovery still blocked")
	}
}
