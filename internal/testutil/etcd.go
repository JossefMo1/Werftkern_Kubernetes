// Package testutil contains protocol fixtures, never a production storage mode.
// This file-backed HTTP server is NOT etcd and cannot prove Raft/etcd correctness.
package testutil

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"net/http"
	"net/http/httptest"
	"os"
	"sync"
	"testing"
)

type KV struct {
	Revision int64  `json:"revision"`
	Value    string `json:"value"`
}
type EtcdFixture struct {
	Server      *httptest.Server
	mu          sync.Mutex
	Path        string
	kv          KV
	Requests    int
	Writes      int
	Reject      int
	Unavailable bool
}

func NewEtcd(t testing.TB, path string) *EtcdFixture {
	t.Helper()
	f := &EtcdFixture{Path: path}
	if e := safefile.ReadJSON(path, &f.kv); e != nil && !os.IsNotExist(e) {
		t.Fatal(e)
	}
	f.Server = httptest.NewServer(http.HandlerFunc(f.serve))
	t.Cleanup(f.Server.Close)
	return f
}
func (f *EtcdFixture) URL() string { return f.Server.URL }
func (f *EtcdFixture) Counts() (int, int) {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.Requests, f.Writes
}
func (f *EtcdFixture) SetReject(n int) { f.mu.Lock(); defer f.mu.Unlock(); f.Reject = n }
func (f *EtcdFixture) serve(w http.ResponseWriter, r *http.Request) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.Requests++
	w.Header().Set("Content-Type", "application/json")
	if f.Unavailable {
		http.Error(w, "unavailable", 503)
		return
	}
	var q map[string]json.RawMessage
	if json.NewDecoder(r.Body).Decode(&q) != nil {
		http.Error(w, "invalid", 400)
		return
	}
	header := func() map[string]string { return map[string]string{"revision": fmt.Sprint(f.kv.Revision)} }
	switch r.URL.Path {
	case "/v3/kv/range":
		if f.kv.Revision == 0 {
			json.NewEncoder(w).Encode(map[string]any{"header": header()})
			return
		}
		json.NewEncoder(w).Encode(map[string]any{"header": header(), "kvs": []any{map[string]string{"value": f.kv.Value, "mod_revision": fmt.Sprint(f.kv.Revision)}}})
	case "/v3/kv/txn":
		var compare []map[string]string
		var success []struct {
			Put struct{ Key, Value string } `json:"request_put"`
		}
		if json.Unmarshal(q["compare"], &compare) != nil || json.Unmarshal(q["success"], &success) != nil || len(compare) != 1 || len(success) != 1 {
			http.Error(w, "invalid transaction", 400)
			return
		}
		match := false
		if compare[0]["target"] == "VERSION" {
			match = f.kv.Revision == 0 && compare[0]["version"] == "0"
		} else if compare[0]["target"] == "MOD" {
			match = compare[0]["mod_revision"] == fmt.Sprint(f.kv.Revision)
		}
		if f.Reject > 0 {
			f.Reject--
			match = false
		}
		if match {
			if _, e := base64.StdEncoding.DecodeString(success[0].Put.Value); e != nil {
				http.Error(w, "bad value", 400)
				return
			}
			next := KV{Revision: f.kv.Revision + 1, Value: success[0].Put.Value}
			if e := safefile.JSON(f.Path, next, 0600); e != nil {
				http.Error(w, "fixture disk error", 500)
				return
			}
			f.kv = next
			f.Writes++
		}
		json.NewEncoder(w).Encode(map[string]any{"header": header(), "succeeded": match})
	default:
		http.NotFound(w, r)
	}
}
