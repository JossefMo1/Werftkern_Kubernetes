package engine

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type redirectTransport struct{ base string }

func (t redirectTransport) RoundTrip(r *http.Request) (*http.Response, error) {
	clone := r.Clone(r.Context())
	u := *r.URL
	clone.URL = &u
	clone.URL.Scheme = "http"
	clone.URL.Host = strings.TrimPrefix(t.base, "http://")
	return http.DefaultTransport.RoundTrip(clone)
}

func TestOfflineVolumeGuardIncludesForeignAndRootMounts(t *testing.T) {
	for _, tc := range []struct {
		name, source, policy      string
		running, restarting, deny bool
	}{
		{"foreign-running", "/var/lib/werftkern/volumes/v/data", "no", true, false, true},
		{"ancestor-root", "/", "no", true, false, true},
		{"ancestor", "/var/lib", "no", true, false, true},
		{"descendant", "/var/lib/werftkern/volumes/v/data/sub", "no", true, false, true},
		{"restartable", "/var/lib/werftkern/volumes/v/data", "always", false, false, true},
		{"restarting", "/var/lib/werftkern/volumes/v/data", "no", false, true, true},
		{"stopped-no-restart", "/var/lib/werftkern/volumes/v/data", "no", false, false, false},
		{"sibling", "/var/lib/werftkern/volumes/v/database", "always", true, false, false},
		{"tmpfs", "", "no", true, false, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			id := strings.Repeat("a", 64)
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.Method != "GET" {
					t.Errorf("guard performed mutation: %s", r.Method)
					w.WriteHeader(500)
					return
				}
				switch r.URL.Path {
				case "/version":
					json.NewEncoder(w).Encode(map[string]string{"ApiVersion": "1.51", "MinAPIVersion": "1.41"})
				case "/v1.51/containers/json":
					json.NewEncoder(w).Encode([]map[string]string{{"Id": id}})
				case "/v1.51/containers/" + id + "/json":
					json.NewEncoder(w).Encode(map[string]any{
						"Mounts": []map[string]string{{"Source": tc.source}}, "State": map[string]bool{"Running": tc.running, "Restarting": tc.restarting},
						"HostConfig": map[string]any{"RestartPolicy": map[string]string{"Name": tc.policy}},
					})
				default:
					w.WriteHeader(404)
				}
			}))
			defer server.Close()
			d := NewDocker("unused", strings.Repeat("b", 32))
			d.Client = &http.Client{Transport: redirectTransport{server.URL}}
			e := d.AssertVolumeOffline(context.Background(), "/var/lib/werftkern/volumes/v/data")
			if (e != nil) != tc.deny {
				t.Fatalf("denied=%t, expected=%t error=%v", e != nil, tc.deny, e)
			}
		})
	}
}
