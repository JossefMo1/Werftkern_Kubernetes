package model

import (
	"errors"
	"strings"
	"testing"
	"time"
)

func validSpec() Spec {
	return Spec{Image: "sha256:" + strings.Repeat("a", 64), Replicas: 1, CPUMilli: 250, MemoryMiB: 128, Port: 8080, ReadinessPath: "/healthz"}
}
func TestSpecValidation(t *testing.T) {
	cases := []struct {
		name   string
		change func(*Spec)
		valid  bool
	}{
		{"valid", func(*Spec) {}, true}, {"registry_digest", func(s *Spec) { s.Image = "ghcr.io/example/api@sha256:" + strings.Repeat("a", 64) }, true},
		{"mutable_tag", func(s *Spec) { s.Image = "nginx:latest" }, false}, {"empty_image", func(s *Spec) { s.Image = "" }, false}, {"short_digest", func(s *Spec) { s.Image = "sha256:abc" }, false},
		{"uppercase_digest", func(s *Spec) { s.Image = "sha256:" + strings.Repeat("F", 64) }, false}, {"negative_replicas", func(s *Spec) { s.Replicas = -1 }, false}, {"too_many_replicas", func(s *Spec) { s.Replicas = 21 }, false},
		{"zero_replicas", func(s *Spec) { s.Replicas = 0 }, true}, {"zero_cpu", func(s *Spec) { s.CPUMilli = 0 }, false}, {"excess_cpu", func(s *Spec) { s.CPUMilli = 128001 }, false}, {"too_little_memory", func(s *Spec) { s.MemoryMiB = 31 }, false},
		{"privileged_port", func(s *Spec) { s.Port = 80 }, false}, {"invalid_port", func(s *Spec) { s.Port = 65536 }, false}, {"missing_probe", func(s *Spec) { s.ReadinessPath = "" }, false},
		{"ssrf_probe", func(s *Spec) { s.ReadinessPath = "http://169.254.169.254/" }, false}, {"network_probe", func(s *Spec) { s.ReadinessPath = "//evil.example/" }, false},
		{"probe_without_port", func(s *Spec) { s.Port = 0 }, false}, {"background_process", func(s *Spec) { s.Port = 0; s.ReadinessPath = "" }, true},
		{"bad_selector", func(s *Spec) { s.Node = "../node" }, false}, {"null_command", func(s *Spec) { s.Command = []string{"a\x00b"} }, false}, {"huge_command", func(s *Spec) { s.Command = []string{strings.Repeat("a", 513)} }, false},
		{"too_many_arguments", func(s *Spec) { s.Command = make([]string, 21) }, false}, {"container_command", func(s *Spec) { s.Command = []string{"/server", "--port", "8080"} }, true},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			s := validSpec()
			c.change(&s)
			if got := s.Validate() == nil; got != c.valid {
				t.Fatalf("valid=%v want %v, error=%v", got, c.valid, s.Validate())
			}
		})
	}
}
func TestIdentityValidation(t *testing.T) {
	for _, v := range []string{"a", "worker-01", "clusterpilot"} {
		if !ValidName(v) {
			t.Fatal(v)
		}
	}
	for _, v := range []string{"", "../escape", "A", "a b", "a/b", strings.Repeat("a", 41)} {
		if ValidName(v) {
			t.Fatal(v)
		}
	}
	if !ValidID(ID()) || ValidID("abc") {
		t.Fatal("id")
	}
	if !ValidRequestID(ID()) || ValidRequestID("short") {
		t.Fatal("key")
	}
}
func TestPrivateIPv4(t *testing.T) {
	for _, ip := range []string{"10.0.0.1", "192.168.1.2", "172.16.0.2", "127.0.0.1"} {
		if !PrivateAddress(ip) {
			t.Fatal(ip)
		}
	}
	for _, ip := range []string{"8.8.8.8", "169.254.169.254", "0.0.0.0", "::1", "host.example"} {
		if PrivateAddress(ip) {
			t.Fatal(ip)
		}
	}
}
func TestApplyIdempotenceAndConflict(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	q := ApplyRequest{APIVersion: APIVersion, Name: "demo", Spec: validSpec()}
	key := ID()
	r, e := Apply(s, q, key, now)
	if e != nil {
		t.Fatal(e)
	}
	again, e := Apply(s, q, key, now)
	if e != nil || r != again || len(s.Events) != 1 {
		t.Fatal("duplicate changed state", e)
	}
	q.Spec.Replicas = 2
	if _, e = Apply(s, q, key, now); e == nil || e.Error() != "IDEMPOTENCY_CONFLICT" {
		t.Fatal(e)
	}
	if _, e = Apply(s, q, ID(), now); !errors.Is(e, ErrConflict) {
		t.Fatal(e)
	}
}
func TestRollbackCreatesNewGeneration(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	q := ApplyRequest{APIVersion: APIVersion, Name: "demo", Spec: validSpec()}
	if _, e := Apply(s, q, ID(), now); e != nil {
		t.Fatal(e)
	}
	q.ExpectedGeneration = 1
	q.Spec.Image = "sha256:" + strings.Repeat("b", 64)
	if _, e := Apply(s, q, ID(), now); e != nil {
		t.Fatal(e)
	}
	r, e := MutateWorkload(s, "demo", "rollback", ID(), 2, now)
	if e != nil || r.Generation != 3 || s.Workloads["demo"].Spec.Image != validSpec().Image {
		t.Fatal(r, e)
	}
}
func TestNoRollbackHistory(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	Apply(s, ApplyRequest{APIVersion: APIVersion, Name: "demo", Spec: validSpec()}, ID(), now)
	if _, e := MutateWorkload(s, "demo", "rollback", ID(), 1, now); e == nil {
		t.Fatal("expected error")
	}
}
func TestDeletePreventsMutationUntilFinalized(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	q := ApplyRequest{APIVersion: APIVersion, Name: "demo", Spec: validSpec()}
	Apply(s, q, ID(), now)
	r, e := MutateWorkload(s, "demo", "delete", ID(), 1, now)
	if e != nil || r.Generation != 1 {
		t.Fatal(e)
	}
	q.ExpectedGeneration = 1
	if _, e := Apply(s, q, ID(), now); !errors.Is(e, ErrConflict) {
		t.Fatal(e)
	}
}
func TestReceiptRetentionAndCapacity(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	for i := 0; i < 256; i++ {
		s.Receipts[ID()] = Receipt{At: now}
	}
	if _, e := s.Request(ID(), "hash", now); !errors.Is(e, ErrCapacity) {
		t.Fatal(e)
	}
	if _, e := s.Request(ID(), "hash", now.Add(25*time.Hour)); e != nil {
		t.Fatal(e)
	}
}
func TestBoundedEventsAndState(t *testing.T) {
	s := NewState(ID(), "test", time.Now())
	for i := 0; i < 1000; i++ {
		s.Event("test", "target", time.Now())
	}
	if len(s.Events) != 160 {
		t.Fatal(len(s.Events))
	}
	if e := s.Validate(); e != nil {
		t.Fatal(e)
	}
	s.Schema = StateSchema + 1
	if s.Validate() == nil {
		t.Fatal("unsupported schema accepted")
	}
}
func TestHashMapOrder(t *testing.T) {
	if Hash(map[string]int{"a": 1, "b": 2}) != Hash(map[string]int{"b": 2, "a": 1}) {
		t.Fatal("unstable hash")
	}
}
