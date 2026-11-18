package apiclient

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type testResponse struct {
	Value string `json:"value"`
}

func callTestResponse(t *testing.T, payload string) (testResponse, error) {
	t.Helper()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(payload))
	}))
	t.Cleanup(server.Close)

	client := &Client{HTTP: server.Client(), Base: server.URL}
	var out testResponse
	err := client.Call(context.Background(), http.MethodGet, "/response", nil, &out, "")
	return out, err
}

func TestCallRejectsAmbiguousControlPlaneResponses(t *testing.T) {
	tests := []struct {
		name    string
		payload string
		code    string
	}{
		{
			name:    "case-fold duplicate member",
			payload: `{"value":"first","Value":"second"}`,
			code:    "JSON_DUPLICATE_MEMBER",
		},
		{
			name:    "trailing object",
			payload: `{"value":"first"}{"value":"second"}`,
			code:    "JSON_TRAILING_DATA",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err := callTestResponse(t, test.payload)
			if err == nil || !strings.Contains(err.Error(), test.code) {
				t.Fatalf("Call() error = %v, want %s", err, test.code)
			}
		})
	}
}

func TestCallPreservesForwardCompatibleUnknownFields(t *testing.T) {
	out, err := callTestResponse(t, `{"value":"ready","futureField":true}`)
	if err != nil {
		t.Fatalf("Call() error = %v", err)
	}
	if out.Value != "ready" {
		t.Fatalf("Call() value = %q, want ready", out.Value)
	}
}

func TestCallRejectsOversizedControlPlaneResponse(t *testing.T) {
	_, err := callTestResponse(t, strings.Repeat(" ", maxResponseBytes+1))
	if err == nil || !strings.Contains(err.Error(), "CONTROL_PLANE_RESPONSE_TOO_LARGE") {
		t.Fatalf("Call() error = %v, want CONTROL_PLANE_RESPONSE_TOO_LARGE", err)
	}
}
