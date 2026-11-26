package apiclient

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/failover"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/strictjson"
)

const (
	maxResponseBytes      = 2 * model.MaxStateBytes
	maxErrorResponseBytes = 8192
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
		raw, readErr := io.ReadAll(io.LimitReader(resp.Body, maxErrorResponseBytes+1))
		if readErr != nil || len(raw) > maxErrorResponseBytes || strictjson.Validate(raw) != nil {
			return fmt.Errorf("CONTROL_PLANE_ERROR_RESPONSE_INVALID (HTTP %d)", resp.StatusCode)
		}
		var p struct {
			Code string `json:"code"`
		}
		if json.Unmarshal(raw, &p) != nil || p.Code == "" {
			p.Code = "UNEXPECTED_HTTP_STATUS"
		}
		return fmt.Errorf("%s (HTTP %d)", p.Code, resp.StatusCode)
	}
	if out == nil {
		io.Copy(io.Discard, io.LimitReader(resp.Body, 8192))
		return nil
	}
	raw, e := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes+1))
	if e != nil {
		return e
	}
	if len(raw) > maxResponseBytes {
		return errors.New("CONTROL_PLANE_RESPONSE_TOO_LARGE")
	}
	if e = strictjson.Validate(raw); e != nil {
		return e
	}
	return json.Unmarshal(raw, out)
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
