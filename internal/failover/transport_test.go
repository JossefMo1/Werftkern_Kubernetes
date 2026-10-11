package failover

import (
	"context"
	"errors"
	"io"
	"net/http"
	"strings"
	"sync/atomic"
	"testing"
)

type rt func(*http.Request) (*http.Response, error)

func (f rt) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }
func TestFailoverReplayAndSticky(t *testing.T) {
	var calls atomic.Int32
	tr, _ := New(rt(func(r *http.Request) (*http.Response, error) {
		calls.Add(1)
		if r.URL.Host == "a:7443" {
			return nil, errors.New("dial")
		}
		b, _ := io.ReadAll(r.Body)
		if string(b) != "payload" {
			t.Fatal(string(b))
		}
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader("ok"))}, nil
	}), []string{"https://a:7443", "https://b:7443"})
	for i := 0; i < 2; i++ {
		r, _ := http.NewRequestWithContext(context.Background(), "POST", "https://a:7443/v1/workloads", strings.NewReader("payload"))
		r.Header.Set("Idempotency-Key", "same-id")
		out, e := tr.RoundTrip(r)
		if e != nil {
			t.Fatal(e)
		}
		out.Body.Close()
	}
	if calls.Load() != 3 {
		t.Fatal(calls.Load())
	}
}
func TestNoAmbiguousMutationReplay(t *testing.T) {
	n := 0
	tr, _ := New(rt(func(r *http.Request) (*http.Response, error) { n++; return nil, errors.New("lost ack") }), []string{"https://a", "https://b"})
	r, _ := http.NewRequest("POST", "https://a/unrecognized", strings.NewReader("body"))
	tr.RoundTrip(r)
	if n != 1 {
		t.Fatal(n)
	}
}
func TestRejectUnsafeEndpoints(t *testing.T) {
	for _, s := range []string{"http://a", "https://" + "u:p@a", "https://a/path", "https://a?secret=x"} {
		if _, e := New(nil, []string{s}); e == nil {
			t.Fatal(s)
		}
	}
}
func TestForbiddenDoesNotFailOver(t *testing.T) {
	n := 0
	tr, _ := New(rt(func(*http.Request) (*http.Response, error) {
		n++
		return &http.Response{StatusCode: 403, Body: io.NopCloser(strings.NewReader("no"))}, nil
	}), []string{"https://a", "https://b"})
	r, _ := http.NewRequest("GET", "https://a/v1/state", nil)
	out, e := tr.RoundTrip(r)
	if e != nil || out.StatusCode != 403 || n != 1 {
		t.Fatal(n, e)
	}
	out.Body.Close()
}
