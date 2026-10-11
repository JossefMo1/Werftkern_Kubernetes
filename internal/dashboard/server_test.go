package dashboard

import (
	"bytes"
	"encoding/json"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func request(s *Server, method, path, origin, auth, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, "http://"+s.Host+path, strings.NewReader(body))
	r.Host = s.Host
	if origin != "" {
		r.Header.Set("Origin", origin)
	}
	if auth != "" {
		r.Header.Set("Authorization", auth)
	}
	w := httptest.NewRecorder()
	s.Handler().ServeHTTP(w, r)
	return w
}
func TestDashboardOriginHostAndAuthentication(t *testing.T) {
	s := New(nil, "127.0.0.1:8787")
	if r := request(s, "GET", "/api/state", "", "", ""); r.Code != 401 {
		t.Fatal(r.Code)
	}
	for _, origin := range []string{"http://evil.invalid", "http://127.0.0.1:8088"} {
		if r := request(s, "POST", "/session", origin, "", `{}`); r.Code != 403 {
			t.Fatal("cross-origin accepted")
		}
	}
	r := httptest.NewRequest("GET", "http://evil.invalid/", nil)
	w := httptest.NewRecorder()
	s.Handler().ServeHTTP(w, r)
	if w.Code != 403 {
		t.Fatal("host injection")
	}
	if r := request(s, "POST", "/session", "", "", `{}`); r.Code != 403 {
		t.Fatal("missing origin allowed")
	}
}
func TestDashboardLoginNoCookieAndBoundedRouteProxy(t *testing.T) {
	var calls int
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		if r.Header.Get("Origin") != "" || r.Header.Get("Cookie") != "" || r.Header.Get("Authorization") != "" {
			t.Error("browser credential forwarded")
		}
		w.Write([]byte(`{"nodes":{}}`))
	}))
	defer upstream.Close()
	s := New(&apiclient.Client{Base: upstream.URL, HTTP: upstream.Client()}, "127.0.0.1:8787")
	body, _ := json.Marshal(map[string]string{"code": s.Code})
	login := request(s, "POST", "/session", "http://"+s.Host, "", string(body))
	if login.Code != 200 || len(login.Result().Cookies()) != 0 {
		t.Fatal(login.Code)
	}
	var token map[string]string
	json.NewDecoder(login.Body).Decode(&token)
	auth := "Bearer " + token["token"]
	if r := request(s, "GET", "/api/state", "", auth, ""); r.Code != 200 {
		t.Fatal(r.Code)
	}
	for _, path := range []string{"/api/state?url=http://evil.invalid", "/api/containers/json", "/api/workloads/shop/exec"} {
		if r := request(s, "GET", path, "", auth, ""); r.Code != 404 {
			t.Fatal(path, r.Code)
		}
	}
	if calls != 1 {
		t.Fatal("arbitrary proxy executed")
	}
}
func TestDashboardBruteForceIsBounded(t *testing.T) {
	s := New(nil, "127.0.0.1:8787")
	for i := 0; i < 10; i++ {
		request(s, "POST", "/session", "http://"+s.Host, "", `{"code":"wrong"}`)
	}
	r := request(s, "POST", "/session", "http://"+s.Host, "", `{"code":"wrong"}`)
	if r.Code != 429 {
		t.Fatal(r.Code)
	}
}
func TestDashboardEmbedsOfflineAssetsWithoutSecrets(t *testing.T) {
	s := New(nil, "127.0.0.1:8787")
	for _, path := range []string{"/", "/style.css", "/app.js"} {
		r := request(s, "GET", path, "", "", "")
		b, _ := io.ReadAll(r.Body)
		if r.Code != 200 || len(b) < 100 || bytes.Contains(b, []byte(s.token)) || bytes.Contains(b, []byte(s.Code)) {
			t.Fatal(path, r.Code)
		}
		if r.Header().Get("Content-Security-Policy") == "" {
			t.Fatal("CSP missing")
		}
	}
}

func TestDashboardPauseResumeAllowlist(t *testing.T) {
	paths := []string{}
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.URL.Path)
		w.Write([]byte(`{"accepted":true}`))
	}))
	defer upstream.Close()
	s := New(&apiclient.Client{Base: upstream.URL, HTTP: upstream.Client()}, "127.0.0.1:8787")
	for _, action := range []string{"pause", "resume"} {
		resp := request(s, "POST", "/api/workloads/web/"+action, "http://"+s.Host, "Bearer "+s.token, `{"expectedGeneration":1}`)
		if resp.Code != 200 {
			t.Fatal(resp.Code)
		}
	}
	if len(paths) != 2 || paths[0] != "/v1/workloads/web/pause" || paths[1] != "/v1/workloads/web/resume" {
		t.Fatal(paths)
	}
}
