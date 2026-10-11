package apiclient

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/failover"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"io"
	"net/http"
	"strings"
)

type Client struct {
	HTTP      *http.Client
	Base      string
	ClusterID string
}

func New(c config.Client) (*Client, error) {
	if e := config.ValidateClient(c); e != nil {
		return nil, e
	}
	h, e := pki.ClientFiles(c.CA, c.Cert, c.Key)
	if e != nil {
		return nil, e
	}
	if len(c.Servers) > 0 {
		t, e := failover.New(h.Transport, c.Servers)
		if e != nil {
			return nil, e
		}
		h.Transport = t
	}
	return &Client{h, strings.TrimRight(c.Server, "/"), c.ClusterID}, nil
}
func (c *Client) Call(ctx context.Context, method, path string, in, out any, key string) error {
	var body io.Reader
	if in != nil {
		b, e := json.Marshal(in)
		if e != nil {
			return e
		}
		body = bytes.NewReader(b)
	}
	r, e := http.NewRequestWithContext(ctx, method, c.Base+path, body)
	if e != nil {
		return e
	}
	r.Header.Set("Content-Type", "application/json")
	if key != "" {
		r.Header.Set("Idempotency-Key", key)
	}
	resp, e := c.HTTP.Do(r)
	if e != nil {
		return fmt.Errorf("CONTROL_PLANE_UNREACHABLE: %w", e)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		var p struct {
			Code string `json:"code"`
		}
		json.NewDecoder(io.LimitReader(resp.Body, 8192)).Decode(&p)
		if p.Code == "" {
			p.Code = "UNEXPECTED_HTTP_STATUS"
		}
		return fmt.Errorf("%s (HTTP %d)", p.Code, resp.StatusCode)
	}
	if out == nil {
		io.Copy(io.Discard, io.LimitReader(resp.Body, 8192))
		return nil
	}
	return json.NewDecoder(io.LimitReader(resp.Body, 2*model.MaxStateBytes)).Decode(out)
}
func (c *Client) State(ctx context.Context) (*model.State, error) {
	var s model.State
	e := c.Call(ctx, "GET", "/v1/state", nil, &s, "")
	if e != nil {
		return nil, e
	}
	if s.ClusterID != c.ClusterID {
		return nil, fmt.Errorf("CLUSTER_ID_MISMATCH")
	}
	return &s, s.Validate()
}
