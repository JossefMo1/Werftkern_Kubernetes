// Package dashboard serves only the management UI. Workload HTML is never
// reverse-proxied into this privileged origin.
package dashboard

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/apiclient"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"io"
	"io/fs"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
)

//go:embed assets/*
var assets embed.FS

func random() string {
	b := make([]byte, 24)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return hex.EncodeToString(b)
}

type Server struct {
	Client   *apiclient.Client
	Code     string
	token    string
	Host     string
	mu       sync.Mutex
	attempts int
	window   time.Time
}

func New(c *apiclient.Client, host string) *Server {
	return &Server{Client: c, Code: random(), token: random(), Host: host}
}
func (s *Server) Handler() http.Handler {
	static, _ := fs.Sub(assets, "assets")
	m := http.NewServeMux()
	m.Handle("/", http.FileServer(http.FS(static)))
	m.HandleFunc("POST /session", s.login)
	m.HandleFunc("/api/", s.proxy)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("Cache-Control", "no-store")
		if r.Host != s.Host {
			http.Error(w, "HOST_NOT_ALLOWED", 403)
			return
		}
		if origin := r.Header.Get("Origin"); origin != "" && origin != "http://"+s.Host {
			http.Error(w, "ORIGIN_NOT_ALLOWED", 403)
			return
		}
		if r.Method != "GET" && r.Method != "HEAD" && r.Header.Get("Origin") != "http://"+s.Host {
			http.Error(w, "ORIGIN_REQUIRED", 403)
			return
		}
		m.ServeHTTP(w, r)
	})
}
func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if time.Since(s.window) > time.Minute {
		s.window = time.Now()
		s.attempts = 0
	}
	s.attempts++
	if s.attempts > 10 {
		http.Error(w, "LOGIN_RATE_LIMIT", 429)
		return
	}
	var in struct {
		Code string `json:"code"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 2048)
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	if d.Decode(&in) != nil || subtle.ConstantTimeCompare([]byte(in.Code), []byte(s.Code)) != 1 {
		http.Error(w, "LOGIN_FAILED", 403)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"token": s.token})
}
func (s *Server) proxy(w http.ResponseWriter, r *http.Request) {
	if subtle.ConstantTimeCompare([]byte(r.Header.Get("Authorization")), []byte("Bearer "+s.token)) != 1 {
		http.Error(w, "LOGIN_REQUIRED", 401)
		return
	}
	target := ""
	switch {
	case r.Method == "GET" && r.URL.Path == "/api/state":
		target = "/v1/state"
	case r.Method == "POST" && r.URL.Path == "/api/workloads":
		target = "/v1/workloads"
	case r.Method == "POST" && strings.HasPrefix(r.URL.Path, "/api/workloads/"):
		pieces := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/workloads/"), "/")
		if len(pieces) == 2 && model.ValidName(pieces[0]) && (pieces[1] == "delete" || pieces[1] == "rollback" || pieces[1] == "pause" || pieces[1] == "resume") {
			target = "/v1/workloads/" + pieces[0] + "/" + pieces[1]
		}
	case r.Method == "POST" && strings.HasPrefix(r.URL.Path, "/api/nodes/"):
		id := strings.TrimPrefix(r.URL.Path, "/api/nodes/")
		if model.ValidID(id) {
			target = "/v1/nodes/" + id
		}
	}
	if target == "" || r.URL.RawQuery != "" {
		http.Error(w, "ROUTE_NOT_ALLOWED", 404)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 65536)
	req, e := http.NewRequestWithContext(r.Context(), r.Method, s.Client.Base+target, r.Body)
	if e != nil {
		http.Error(w, "PROXY_REQUEST_FAILED", 500)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Idempotency-Key", r.Header.Get("Idempotency-Key"))
	response, e := s.Client.HTTP.Do(req)
	if e != nil {
		http.Error(w, "CONTROL_PLANE_UNREACHABLE", 503)
		return
	}
	defer response.Body.Close()
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(response.StatusCode)
	io.Copy(w, io.LimitReader(response.Body, 2*model.MaxStateBytes))
}
func Serve(ctx context.Context, c *apiclient.Client, address string) error {
	host, _, e := net.SplitHostPort(address)
	if e != nil || host != "127.0.0.1" {
		return errors.New("DASHBOARD_MUST_BIND_127.0.0.1")
	}
	listener, e := net.Listen("tcp", address)
	if e != nil {
		return e
	}
	s := New(c, listener.Addr().String())
	fmt.Printf("Lokale Oberfläche: http://%s\nAnmeldecode (nur für diesen Prozess): %s\nDer Code wird weder in einer URL noch im Browser-Speicher abgelegt.\n", s.Host, s.Code)
	srv := &http.Server{Handler: s.Handler(), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 25 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 << 10}
	go func() {
		<-ctx.Done()
		stop, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		srv.Shutdown(stop)
	}()
	e = srv.Serve(listener)
	if e == http.ErrServerClosed {
		return nil
	}
	return e
}
