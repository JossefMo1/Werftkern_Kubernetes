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
func TestRollbackValidationFailureDoesNotMutateHistory(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	s.Secrets = map[string]SecretVersion{"db/1": {Name: "db", Version: 1, Sealed: "sealed"}}
	initial := validSpec()
	initial.Secrets = []SecretRef{{Name: "db", Version: 1}}
	q := ApplyRequest{APIVersion: APIVersion, Name: "demo", Spec: initial}
	if _, e := Apply(s, q, ID(), now); e != nil {
		t.Fatal(e)
	}
	q.ExpectedGeneration = 1
	q.Spec = validSpec()
	if _, e := Apply(s, q, ID(), now); e != nil {
		t.Fatal(e)
	}
	w := s.Workloads["demo"]
	before := append([]Spec(nil), w.History...)
	delete(s.Secrets, "db/1")
	if _, e := MutateWorkload(s, "demo", "rollback", ID(), 2, now); e == nil {
		t.Fatal("rollback with unavailable secret succeeded")
	}
	if len(w.History) != len(before) || Hash(w.History) != Hash(before) || w.Spec.Image != q.Spec.Image || w.Generation != 2 {
		t.Fatal("failed rollback mutated active state")
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
func TestNativeAllocationCapacityMatchesSingleHostScope(t *testing.T) {
	s := NewState(ID(), "test", time.Now())
	for i := 0; i <= MaxAllocations; i++ {
		id := ID()
		s.Allocations[id] = &Allocation{ID: id}
	}
	if !errors.Is(s.Validate(), ErrCapacity) {
		t.Fatalf("allocation inventory above native limit was accepted: %d", len(s.Allocations))
	}
	if MaxAllocations != 50 {
		t.Fatalf("native single-host allocation limit changed unexpectedly: %d", MaxAllocations)
	}
}

func TestNativeCapacityMatchesSingleHostScope(t *testing.T) {
	if NativeMaxNodes != 1 {
		t.Fatalf("native single-host node limit changed unexpectedly: %d", NativeMaxNodes)
	}
	if NativeMaxWorkloads != 20 {
		t.Fatalf("native single-host workload limit changed unexpectedly: %d", NativeMaxWorkloads)
	}
	if NativeMaxAllocations != 50 {
		t.Fatalf("native single-host allocation limit changed unexpectedly: %d", NativeMaxAllocations)
	}

	now := time.Now()
	s := NewState(ID(), "test", now)
	for i := 0; i < NativeMaxNodes+1; i++ {
		id := ID()
		s.Nodes[id] = &Node{ID: id}
	}
	if !errors.Is(s.ValidateNativeSingleHost(), ErrCapacity) {
		t.Fatalf("native node inventory above limit was accepted: %d", len(s.Nodes))
	}

	s = NewState(ID(), "test", now)
	for i := 0; i < NativeMaxWorkloads+1; i++ {
		name := "w" + strings.Repeat("a", i%10) + strings.Repeat("-", i/10)
		if !ValidName(name) {
			name = "w" + strings.Repeat("a", i%39) + "-" + string(rune('a'+i%26))
		}
		s.Workloads[name] = &Workload{Name: name}
	}
	if len(s.Workloads) <= NativeMaxWorkloads || !errors.Is(s.ValidateNativeSingleHost(), ErrCapacity) {
		t.Fatalf("native workload inventory above limit was accepted: %d", len(s.Workloads))
	}
}

func TestValidateNativeSingleHostRejectsMalformedPersistedState(t *testing.T) {
	s := NewState(ID(), "test", time.Now())
	s.Workloads["demo"] = &Workload{Name: "other"}
	if err := s.ValidateNativeSingleHost(); err == nil || err.Error() != "WORKLOAD_INDEX_INVALID" {
		t.Fatalf("malformed native state was accepted: %v", err)
	}
}

func TestExpiredReceiptKeyCanBeReused(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	key := ID()
	oldHash := strings.Repeat("a", 64)
	s.Receipts[key] = Receipt{ID: key, Hash: oldHash, WorkloadUID: ID(), Generation: 1, At: now}

	q := ApplyRequest{APIVersion: APIVersion, Name: "demo", Spec: validSpec()}
	r, err := Apply(s, q, key, now.Add(25*time.Hour))
	if err != nil {
		t.Fatal(err)
	}
	if r.ID != key || r.Hash == oldHash || s.Receipts[key].Hash != r.Hash {
		t.Fatalf("expired receipt was not replaced: %+v", r)
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

func TestStateRejectsIndexMismatches(t *testing.T) {
	cases := []struct {
		name   string
		change func(*State)
	}{
		{"gateway", func(s *State) {
			s.Gateways = map[string]*Gateway{ID(): {ID: ID()}}
		}},
		{"workload", func(s *State) {
			s.Workloads["demo"] = &Workload{Name: "other"}
		}},
		{"node", func(s *State) {
			s.Nodes[ID()] = &Node{ID: ID()}
		}},
		{"allocation", func(s *State) {
			s.Allocations[ID()] = &Allocation{ID: ID()}
		}},
		{"receipt", func(s *State) {
			s.Receipts[ID()] = Receipt{ID: ID()}
		}},
		{"event_limit", func(s *State) {
			s.Events = make([]Event, 161)
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := NewState(ID(), "test", time.Now())
			tc.change(s)
			if err := s.Validate(); err == nil {
				t.Fatal("malformed persisted index accepted")
			}
		})
	}
}

func TestStateRejectsMalformedReceipts(t *testing.T) {
	now := time.Now()
	cases := []struct {
		name   string
		change func(*Receipt)
	}{
		{"hash", func(r *Receipt) { r.Hash = "not-a-sha256" }},
		{"workload", func(r *Receipt) { r.WorkloadUID = "invalid" }},
		{"generation", func(r *Receipt) { r.Generation = 0 }},
		{"timestamp", func(r *Receipt) { r.At = time.Time{} }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := NewState(ID(), "test", now)
			key := ID()
			r := Receipt{ID: key, Hash: strings.Repeat("a", 64), WorkloadUID: ID(), Generation: 1, At: now}
			tc.change(&r)
			s.Receipts[key] = r
			if err := s.Validate(); err == nil {
				t.Fatal("malformed receipt accepted")
			}
		})
	}
}

func TestStateAcceptsSecretReceiptOwner(t *testing.T) {
	now := time.Now()
	s := NewState(ID(), "test", now)
	key := ID()
	s.Receipts[key] = Receipt{
		ID: key, Hash: strings.Repeat("a", 64), WorkloadUID: "secret:api/3", Generation: 3, At: now,
	}
	if err := s.Validate(); err != nil {
		t.Fatalf("secret receipt owner rejected: %v", err)
	}
}

func TestHashMapOrder(t *testing.T) {
	if Hash(map[string]int{"a": 1, "b": 2}) != Hash(map[string]int{"b": 2, "a": 1}) {
		t.Fatal("unstable hash")
	}
}

func TestStateRejectsAllocationCrossIndexMismatch(t *testing.T) {
	now := time.Now()
	nodeID, workloadID, allocationID := ID(), ID(), ID()
	s := NewState(ID(), "test", now)
	s.Nodes[nodeID] = &Node{ID: nodeID, Name: "node", Address: "10.0.0.1", CPUMilli: 1000, MemoryMiB: 512, LastSeen: now, Healthy: true}
	s.Workloads["demo"] = &Workload{UID: workloadID, Name: "demo", Generation: 1, Spec: validSpec(), Phase: "pending", CreatedAt: now}
	s.Allocations[allocationID] = &Allocation{ID: allocationID, WorkloadUID: workloadID, Name: "demo", Generation: 1, NodeID: nodeID, Spec: validSpec(), Desired: "run", Phase: "assigned", CreatedAt: now, UpdatedAt: now}
	if err := s.ValidateInventory(); err != nil {
		t.Fatalf("valid inventory rejected: %v", err)
	}
	for name, change := range map[string]func(*Allocation){
		"name":       func(a *Allocation) { a.Name = "other" },
		"generation": func(a *Allocation) { a.Generation = 2 },
	} {
		t.Run(name, func(t *testing.T) {
			copy := *s.Allocations[allocationID]
			change(&copy)
			s.Allocations[allocationID] = &copy
			if err := s.ValidateInventory(); err == nil {
				t.Fatal("cross-index allocation mismatch accepted")
			}
			s.Allocations[allocationID] = &copy
			copy.Name = "demo"
			copy.Generation = 1
		})
	}
}

func TestStateRejectsAllocationSpecCrossIndexMismatch(t *testing.T) {
	now := time.Now()
	nodeID, workloadID, allocationID := ID(), ID(), ID()
	s := NewState(ID(), "test", now)
	s.Nodes[nodeID] = &Node{ID: nodeID, Name: "node", Address: "10.0.0.1", CPUMilli: 1000, MemoryMiB: 512, LastSeen: now, Healthy: true}
	s.Workloads["demo"] = &Workload{UID: workloadID, Name: "demo", Generation: 1, Spec: validSpec(), Phase: "pending", CreatedAt: now}
	s.Allocations[allocationID] = &Allocation{ID: allocationID, WorkloadUID: workloadID, Name: "demo", Generation: 1, NodeID: nodeID, Spec: validSpec(), Desired: "run", Phase: "assigned", CreatedAt: now, UpdatedAt: now}
	if err := s.ValidateInventory(); err != nil {
		t.Fatalf("valid inventory rejected: %v", err)
	}
	copy := *s.Allocations[allocationID]
	copy.Spec.Image = "sha256:" + strings.Repeat("b", 64)
	s.Allocations[allocationID] = &copy
	if err := s.ValidateInventory(); err == nil {
		t.Fatal("allocation spec diverging from current workload accepted")
	}
}

func TestStateAcceptsKnownHistoricalAllocationSpec(t *testing.T) {
	now := time.Now()
	nodeID, workloadID, allocationID := ID(), ID(), ID()
	oldSpec, currentSpec := validSpec(), validSpec()
	oldSpec.Image = "sha256:" + strings.Repeat("b", 64)
	s := NewState(ID(), "test", now)
	s.Nodes[nodeID] = &Node{ID: nodeID, Name: "node", Address: "10.0.0.1", CPUMilli: 1000, MemoryMiB: 512, LastSeen: now, Healthy: true}
	s.Workloads["demo"] = &Workload{UID: workloadID, Name: "demo", Generation: 2, Spec: currentSpec, History: []Spec{oldSpec}, Phase: "updating", CreatedAt: now}
	s.Allocations[allocationID] = &Allocation{ID: allocationID, WorkloadUID: workloadID, Name: "demo", Generation: 1, NodeID: nodeID, Spec: oldSpec, Desired: "run", Phase: "ready", CreatedAt: now, UpdatedAt: now}
	if err := s.ValidateInventory(); err != nil {
		t.Fatalf("known historical allocation rejected: %v", err)
	}
	copy := *s.Allocations[allocationID]
	copy.Spec.Image = "sha256:" + strings.Repeat("c", 64)
	s.Allocations[allocationID] = &copy
	if err := s.ValidateInventory(); err == nil {
		t.Fatal("allocation spec absent from workload history accepted")
	}
}

func TestStateRejectsAllocationNodeSelectorMismatch(t *testing.T) {
	now := time.Now()
	nodeID, selectedID, workloadID, allocationID := ID(), ID(), ID(), ID()
	spec := validSpec()
	spec.Node = selectedID
	s := NewState(ID(), "test", now)
	s.Nodes[nodeID] = &Node{ID: nodeID, Name: "node", Address: "10.0.0.1", CPUMilli: 1000, MemoryMiB: 512, LastSeen: now, Healthy: true}
	s.Nodes[selectedID] = &Node{ID: selectedID, Name: "node-2", Address: "10.0.0.2", CPUMilli: 1000, MemoryMiB: 512, LastSeen: now, Healthy: true}
	s.Workloads["demo"] = &Workload{UID: workloadID, Name: "demo", Generation: 1, Spec: spec, Phase: "pending", CreatedAt: now}
	s.Allocations[allocationID] = &Allocation{ID: allocationID, WorkloadUID: workloadID, Name: "demo", Generation: 1, NodeID: selectedID, Spec: spec, Desired: "run", Phase: "assigned", CreatedAt: now, UpdatedAt: now}
	if err := s.ValidateInventory(); err != nil {
		t.Fatalf("valid pinned allocation rejected: %v", err)
	}
	copy := *s.Allocations[allocationID]
	copy.NodeID = nodeID
	s.Allocations[allocationID] = &copy
	if err := s.ValidateInventory(); err == nil {
		t.Fatal("allocation on a node different from its selector accepted")
	}
}

func TestStateRejectsUnknownAllocationPhase(t *testing.T) {
	now := time.Now()
	nodeID, workloadID, allocationID := ID(), ID(), ID()
	s := NewState(ID(), "test", now)
	s.Nodes[nodeID] = &Node{ID: nodeID, Name: "node", Address: "10.0.0.1", CPUMilli: 1000, MemoryMiB: 512, LastSeen: now, Healthy: true}
	s.Workloads["demo"] = &Workload{UID: workloadID, Name: "demo", Generation: 1, Spec: validSpec(), Phase: "pending", CreatedAt: now}
	for _, phase := range []string{"", "unknown", "running"} {
		t.Run("phase="+phase, func(t *testing.T) {
			s.Allocations[allocationID] = &Allocation{ID: allocationID, WorkloadUID: workloadID, Name: "demo", Generation: 1, NodeID: nodeID, Spec: validSpec(), Desired: "run", Phase: phase, CreatedAt: now, UpdatedAt: now}
			if err := s.ValidateInventory(); err == nil {
				t.Fatalf("unknown allocation phase %q was accepted", phase)
			}
			delete(s.Allocations, allocationID)
		})
	}
}

func TestStateRejectsInvalidPersistedAllocationEndpoints(t *testing.T) {
	now := time.Now()
	nodeID, workloadID, allocationID := ID(), ID(), ID()
	spec := validSpec()
	s := NewState(ID(), "test", now)
	s.Nodes[nodeID] = &Node{ID: nodeID, Name: "node", Address: "10.0.0.1", PodCIDR: "10.88.1.0/24", CPUMilli: 1000, MemoryMiB: 512, LastSeen: now, Healthy: true}
	s.Workloads["demo"] = &Workload{UID: workloadID, Name: "demo", Generation: 1, Spec: spec, Phase: "pending", CreatedAt: now}
	s.Allocations[allocationID] = &Allocation{ID: allocationID, WorkloadUID: workloadID, Name: "demo", Generation: 1, NodeID: nodeID, Spec: spec, HostPort: 22000, ContainerIP: "10.88.1.2", Desired: "run", Phase: "ready", CreatedAt: now, UpdatedAt: now}
	if err := s.ValidateInventory(); err != nil {
		t.Fatalf("valid endpoint rejected: %v", err)
	}
	base := *s.Allocations[allocationID]
	for _, port := range []int{80, 23000} {
		copy := base
		copy.HostPort = port
		s.Allocations[allocationID] = &copy
		if err := s.ValidateInventory(); err == nil {
			t.Fatalf("invalid host port %d accepted", port)
		}
	}
	copy := base
	copy.ContainerIP = "10.88.2.2"
	s.Allocations[allocationID] = &copy
	if err := s.ValidateInventory(); err == nil {
		t.Fatal("container IP outside PodCIDR accepted")
	}
}
