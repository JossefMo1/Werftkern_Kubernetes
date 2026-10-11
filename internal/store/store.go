// Package store persists small-cluster state in etcd using one compare-and-swap
// aggregate. This is an explicitly bounded alpha design, not a scalable database.
package store

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"io"
	"net/http"
	"strconv"
	"time"
)

var ErrUninitialized = errors.New("STORE_UNINITIALIZED_NO_AUTOMATIC_RECOVERY")
var ErrUnavailable = errors.New("STORE_UNAVAILABLE")

type Store interface {
	Read(context.Context) (*model.State, int64, error)
	Update(context.Context, func(*model.State) error) (*model.State, int64, error)
}
type Etcd struct {
	URL       string
	Client    *http.Client
	Key       string
	ClusterID string
}

func NewEtcd(url string, c *http.Client, id string) *Etcd {
	return &Etcd{URL: url, Client: c, Key: "/werftkern/runtime/v1/state", ClusterID: id}
}
func (e *Etcd) call(ctx context.Context, path string, in, out any) error {
	b, err := json.Marshal(in)
	if err != nil {
		return err
	}
	r, err := http.NewRequestWithContext(ctx, "POST", e.URL+path, bytes.NewReader(b))
	if err != nil {
		return err
	}
	r.Header.Set("Content-Type", "application/json")
	resp, err := e.Client.Do(r)
	if err != nil {
		return ErrUnavailable
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("%w: HTTP_%d", ErrUnavailable, resp.StatusCode)
	}
	if err = json.NewDecoder(io.LimitReader(resp.Body, 2*model.MaxStateBytes)).Decode(out); err != nil {
		return fmt.Errorf("%w: invalid response", ErrUnavailable)
	}
	return nil
}
func b64(b []byte) string { return base64.StdEncoding.EncodeToString(b) }
func (e *Etcd) readRaw(ctx context.Context) ([]byte, int64, error) {
	var out struct {
		Kvs []struct {
			Value       string `json:"value"`
			ModRevision string `json:"mod_revision"`
		} `json:"kvs"`
	}
	if err := e.call(ctx, "/v3/kv/range", map[string]any{"key": b64([]byte(e.Key)), "serializable": false}, &out); err != nil {
		return nil, 0, err
	}
	if len(out.Kvs) != 1 {
		return nil, 0, ErrUninitialized
	}
	b, err := base64.StdEncoding.DecodeString(out.Kvs[0].Value)
	if err != nil {
		return nil, 0, err
	}
	if len(b) > model.MaxStateBytes {
		return nil, 0, model.ErrCapacity
	}
	rev, err := strconv.ParseInt(out.Kvs[0].ModRevision, 10, 64)
	if err != nil || rev < 1 {
		return nil, 0, errors.New("STORE_REVISION_INVALID")
	}
	return b, rev, nil
}
func (e *Etcd) Read(ctx context.Context) (*model.State, int64, error) {
	b, rev, err := e.readRaw(ctx)
	if err != nil {
		return nil, 0, err
	}
	var s model.State
	if err = json.Unmarshal(b, &s); err != nil {
		return nil, 0, err
	}
	if err = s.ValidateInventory(); err != nil {
		return nil, 0, err
	}
	if s.ClusterID != e.ClusterID {
		return nil, 0, errors.New("CLUSTER_ID_MISMATCH")
	}
	return &s, rev, nil
}
func (e *Etcd) cas(ctx context.Context, s *model.State, revision int64) (bool, int64, error) {
	if err := s.ValidateInventory(); err != nil {
		return false, 0, err
	}
	b, err := json.Marshal(s)
	if err != nil {
		return false, 0, err
	}
	compare := map[string]any{"key": b64([]byte(e.Key)), "target": "MOD", "result": "EQUAL", "mod_revision": strconv.FormatInt(revision, 10)}
	if revision == 0 {
		compare = map[string]any{"key": b64([]byte(e.Key)), "target": "VERSION", "result": "EQUAL", "version": "0"}
	}
	in := map[string]any{"compare": []any{compare}, "success": []any{map[string]any{"request_put": map[string]any{"key": b64([]byte(e.Key)), "value": b64(b)}}}, "failure": []any{}}
	var out struct {
		Succeeded bool `json:"succeeded"`
		Header    struct {
			Revision string `json:"revision"`
		} `json:"header"`
	}
	if err = e.call(ctx, "/v3/kv/txn", in, &out); err != nil {
		return false, 0, err
	}
	r, err := strconv.ParseInt(out.Header.Revision, 10, 64)
	if err != nil {
		return false, 0, err
	}
	return out.Succeeded, r, nil
}
func (e *Etcd) Initialize(ctx context.Context, s *model.State) error {
	if s.ClusterID != e.ClusterID {
		return errors.New("CLUSTER_ID_MISMATCH")
	}
	ok, _, err := e.cas(ctx, s, 0)
	if err != nil {
		return err
	}
	if !ok {
		return model.ErrConflict
	}
	return nil
}
func (e *Etcd) Update(ctx context.Context, fn func(*model.State) error) (*model.State, int64, error) {
	for i := 0; i < 40; i++ {
		s, r, err := e.Read(ctx)
		if err != nil {
			return nil, 0, err
		}
		before := model.Hash(s)
		if err = fn(s); err != nil {
			return nil, 0, err
		}
		if model.Hash(s) == before {
			return s, r, nil
		}
		ok, next, err := e.cas(ctx, s, r)
		if err != nil {
			return nil, 0, err
		}
		if ok {
			return s, next, nil
		}
		select {
		case <-ctx.Done():
			return nil, 0, ctx.Err()
		case <-time.After(time.Duration(i%5+1) * time.Millisecond):
		}
	}
	return nil, 0, model.ErrConflict
}
