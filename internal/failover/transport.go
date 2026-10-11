// Package failover retries only replay-safe requests against an explicit TLS
// endpoint set. It never follows redirects or downgrades certificate checks.
package failover

import (
	"context"
	"crypto/tls"
	"errors"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync/atomic"
	"time"
)

type Transport struct {
	Base      http.RoundTripper
	Endpoints []*url.URL
	current   atomic.Uint32
	Timeout   time.Duration
}
type cancelBody struct {
	io.ReadCloser
	cancel context.CancelFunc
}

func (b *cancelBody) Close() error { e := b.ReadCloser.Close(); b.cancel(); return e }

func New(base http.RoundTripper, endpoints []string) (*Transport, error) {
	if len(endpoints) < 1 || len(endpoints) > 5 {
		return nil, errors.New("ENDPOINT_COUNT_INVALID")
	}
	if base == nil {
		base = http.DefaultTransport
	}
	t := &Transport{Base: base, Timeout: 6 * time.Second}
	seen := map[string]bool{}
	for _, s := range endpoints {
		u, e := url.Parse(s)
		if e != nil || u.Scheme != "https" || u.Host == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || strings.Trim(u.Path, "/") != "" || seen[u.Host] {
			return nil, errors.New("ENDPOINT_INVALID")
		}
		seen[u.Host] = true
		t.Endpoints = append(t.Endpoints, u)
	}
	return t, nil
}
func replaySafe(r *http.Request) bool {
	return r.Method == "GET" || r.Method == "HEAD" || r.Header.Get("Idempotency-Key") != "" ||
		r.Method == "POST" && (r.URL.Path == "/v1/heartbeat" || r.URL.Path == "/v3/kv/range" || r.URL.Path == "/v3/kv/txn")
}
func (t *Transport) RoundTrip(r *http.Request) (*http.Response, error) {
	if r.Body != nil && r.GetBody != nil {
		defer r.Body.Close()
	}
	attempts := 1
	if replaySafe(r) && (r.Body == nil || r.GetBody != nil) {
		attempts = len(t.Endpoints)
	}
	start := int(t.current.Load()) % len(t.Endpoints)
	var last error
	for i := 0; i < attempts; i++ {
		idx := (start + i) % len(t.Endpoints)
		ctx, cancel := context.WithTimeout(r.Context(), t.Timeout)
		q := r.Clone(ctx)
		u := *r.URL
		u.Scheme = t.Endpoints[idx].Scheme
		u.Host = t.Endpoints[idx].Host
		q.URL = &u
		q.Host = ""
		if r.Body != nil && r.GetBody != nil {
			b, e := r.GetBody()
			if e != nil {
				cancel()
				return nil, e
			}
			q.Body = b
		}
		resp, e := t.Base.RoundTrip(q)
		if e != nil {
			cancel()
			last = e
			var ce *tls.CertificateVerificationError
			if errors.As(e, &ce) || r.Context().Err() != nil {
				return nil, e
			}
			continue
		}
		if (resp.StatusCode == 502 || resp.StatusCode == 503 || resp.StatusCode == 504) && i+1 < attempts {
			io.Copy(io.Discard, io.LimitReader(resp.Body, 8192))
			resp.Body.Close()
			cancel()
			continue
		}
		t.current.Store(uint32(idx))
		resp.Body = &cancelBody{resp.Body, cancel}
		return resp, nil
	}
	if last == nil {
		last = errors.New("NO_AVAILABLE_ENDPOINT")
	}
	return nil, last
}
