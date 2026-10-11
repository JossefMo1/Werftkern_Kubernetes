// Package model defines the versioned, Kubernetes-independent runtime contract.
package model

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/url"
	"regexp"
	"sort"
	"strings"
	"time"
)

const Version = "0.2.0-dev.4"
const StateSchema = 2
const APIVersion = "werftkern/v1alpha1"
const MaxStateBytes = 900000
const MaxNodes = 20
const MaxWorkloads = 50
const MaxAllocations = 200
const HeartbeatTimeout = 30 * time.Second

// Wire and state schema are unchanged for this explicitly bounded upgrade edge.
// This is not a promise that arbitrary older/newer versions interoperate.
func SupportedAgentVersion(v string) bool {
	return v == Version || v == "0.2.0-dev.3"
}
func SupportedAgentVersions() []string { return []string{Version, "0.2.0-dev.3"} }

func FreshObservation(at, now time.Time) bool {
	return !at.IsZero() && !at.After(now.Add(5*time.Second)) && now.Sub(at) < HeartbeatTimeout
}

var ErrConflict = errors.New("VERSION_CONFLICT")
var ErrNotFound = errors.New("NOT_FOUND")
var ErrCapacity = errors.New("STATE_CAPACITY_REACHED")
var nameRE = regexp.MustCompile(`^[a-z][a-z0-9-]{0,39}$`)
var digestRE = regexp.MustCompile(`^(?:[a-z0-9][a-z0-9._:/-]*@)?sha256:[a-f0-9]{64}$`)
var idRE = regexp.MustCompile(`^[a-f0-9]{32}$`)
var keyRE = regexp.MustCompile(`^[A-Za-z0-9_-]{16,100}$`)

func ID() string {
	b := make([]byte, 16)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return hex.EncodeToString(b)
}
func ValidID(s string) bool        { return idRE.MatchString(s) }
func ValidName(s string) bool      { return nameRE.MatchString(s) }
func ValidRequestID(s string) bool { return keyRE.MatchString(s) }
func Hash(v any) string {
	b, e := json.Marshal(v)
	if e != nil {
		panic(e)
	}
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}
func PrivateAddress(s string) bool {
	ip := net.ParseIP(s)
	return ip != nil && ip.To4() != nil && (ip.IsPrivate() || ip.IsLoopback())
}

// Spec allows only typed local-volume references, never arbitrary host mounts or privileged mode.
// Secrets are immutable, explicitly scoped file references, never inline values.
// Images must be immutable registry digests or locally preloaded content IDs.
type Spec struct {
	// Empty/retain never replaces a partitioned owner. duplicate-safe explicitly
	// permits simultaneous old/new executions and is forbidden with local storage.
	ReplacementPolicy string      `json:"replacementPolicy,omitempty"`
	Volumes           []VolumeRef `json:"volumes,omitempty"`
	RunAsUID          int         `json:"runAsUid,omitempty"`
	RunAsGID          int         `json:"runAsGid,omitempty"`
	Probe             string      `json:"probe,omitempty"`
	Profile           string      `json:"profile,omitempty"`
	Image             string      `json:"image"`
	Replicas          int         `json:"replicas"`
	CPUMilli          int64       `json:"cpuMilli"`
	MemoryMiB         int64       `json:"memoryMiB"`
	Port              int         `json:"port,omitempty"`
	ReadinessPath     string      `json:"readinessPath,omitempty"`
	Command           []string    `json:"command,omitempty"`
	Node              string      `json:"node,omitempty"`
	Secrets           []SecretRef `json:"secrets,omitempty"`
}

func (s Spec) Validate() error {
	if s.ReplacementPolicy != "" && s.ReplacementPolicy != "retain" && s.ReplacementPolicy != "duplicate-safe" {
		return errors.New("REPLACEMENT_POLICY_INVALID")
	}
	if s.ReplacementPolicy == "duplicate-safe" && (len(s.Volumes) > 0 || s.Profile != "") {
		return errors.New("STATEFUL_DUPLICATE_REPLACEMENT_FORBIDDEN")
	}
	if err := s.ValidateStorage(); err != nil {
		return err
	}
	if len(s.Image) > 300 || !digestRE.MatchString(s.Image) {
		return errors.New("IMAGE_DIGEST_REQUIRED")
	}
	if s.Replicas < 0 || s.Replicas > 20 {
		return errors.New("REPLICAS_OUT_OF_RANGE")
	}
	if s.CPUMilli < 100 || s.CPUMilli > 128000 {
		return errors.New("CPU_OUT_OF_RANGE")
	}
	if s.MemoryMiB < 32 || s.MemoryMiB > 262144 {
		return errors.New("MEMORY_OUT_OF_RANGE")
	}
	if s.Port != 0 && (s.Port < 1024 || s.Port > 65535) {
		return errors.New("UNPRIVILEGED_PORT_REQUIRED")
	}
	if s.Port > 0 && s.ReadinessPath == "" && s.Probe == "" {
		return errors.New("HTTP_READINESS_REQUIRED")
	}
	if s.ReadinessPath != "" {
		u, e := url.ParseRequestURI(s.ReadinessPath)
		if e != nil || s.Port == 0 || !strings.HasPrefix(s.ReadinessPath, "/") || strings.HasPrefix(s.ReadinessPath, "//") || u.IsAbs() || u.Host != "" || u.Fragment != "" || len(s.ReadinessPath) > 200 {
			return errors.New("READINESS_PATH_INVALID")
		}
	}
	if err := ValidateSecretRefs(s.Secrets); err != nil {
		return err
	}
	if s.Node != "" && !ValidID(s.Node) {
		return errors.New("NODE_SELECTOR_INVALID")
	}
	if len(s.Command) > 20 {
		return errors.New("COMMAND_TOO_LARGE")
	}
	for _, v := range s.Command {
		if len(v) > 512 || strings.ContainsRune(v, 0) {
			return errors.New("COMMAND_INVALID")
		}
	}
	return nil
}

type ApplyRequest struct {
	APIVersion         string `json:"apiVersion"`
	Name               string `json:"name"`
	ExpectedGeneration int64  `json:"expectedGeneration"`
	Spec               Spec   `json:"spec"`
}
type MutationRequest struct {
	ExpectedGeneration int64 `json:"expectedGeneration"`
}
type Workload struct {
	UID        string    `json:"uid"`
	Name       string    `json:"name"`
	Generation int64     `json:"generation"`
	Spec       Spec      `json:"spec"`
	History    []Spec    `json:"history,omitempty"`
	Deleting   bool      `json:"deleting"`
	Phase      string    `json:"phase"`
	Reason     string    `json:"reason,omitempty"`
	CreatedAt  time.Time `json:"createdAt"`
	Paused     bool      `json:"paused,omitempty"`
}
type Node struct {
	HeartbeatSequence uint64    `json:"heartbeatSequence,omitempty"`
	HeartbeatHash     string    `json:"heartbeatHash,omitempty"`
	PodCIDR           string    `json:"podCidr,omitempty"`
	ID                string    `json:"id"`
	Name              string    `json:"name"`
	Address           string    `json:"address"`
	CPUMilli          int64     `json:"cpuMilli"`
	MemoryMiB         int64     `json:"memoryMiB"`
	LastSeen          time.Time `json:"lastSeen"`
	Healthy           bool      `json:"healthy"`
	Drain             bool      `json:"drain"`
	Revoked           bool      `json:"revoked"`
	InstanceID        string    `json:"instanceId,omitempty"`
	Version           string    `json:"version,omitempty"`
}

func (n Node) Ready(now time.Time) bool {
	return !n.Revoked && n.Healthy && !n.LastSeen.IsZero() && now.Sub(n.LastSeen) >= -5*time.Second && now.Sub(n.LastSeen) < HeartbeatTimeout
}

type Allocation struct {
	ContainerIP string    `json:"containerIp,omitempty"`
	ID          string    `json:"id"`
	WorkloadUID string    `json:"workloadUid"`
	Name        string    `json:"name"`
	Generation  int64     `json:"generation"`
	NodeID      string    `json:"nodeId"`
	Spec        Spec      `json:"spec"`
	HostPort    int       `json:"hostPort,omitempty"`
	Desired     string    `json:"desired"`
	Phase       string    `json:"phase"`
	Reason      string    `json:"reason,omitempty"`
	CreatedAt   time.Time `json:"createdAt"`
	UpdatedAt   time.Time `json:"updatedAt"`
}
type Report struct {
	ContainerIP string    `json:"containerIp,omitempty"`
	ID          string    `json:"id"`
	Phase       string    `json:"phase"`
	Reason      string    `json:"reason,omitempty"`
	ObservedAt  time.Time `json:"observedAt,omitempty"`
}
type Heartbeat struct {
	Sequence   uint64   `json:"sequence,omitempty"`
	InstanceID string   `json:"instanceId"`
	CPUMilli   int64    `json:"cpuMilli"`
	MemoryMiB  int64    `json:"memoryMiB"`
	Healthy    bool     `json:"healthy"`
	Version    string   `json:"version"`
	Reports    []Report `json:"reports"`
}
type AssignmentSnapshot struct {
	ClusterID   string       `json:"clusterId"`
	Revision    int64        `json:"revision"`
	Allocations []Allocation `json:"allocations"`
}
type Event struct {
	ID     string    `json:"id"`
	At     time.Time `json:"at"`
	Action string    `json:"action"`
	Target string    `json:"target"`
}
type Receipt struct {
	ID          string    `json:"id"`
	Hash        string    `json:"hash"`
	WorkloadUID string    `json:"workloadUid"`
	Generation  int64     `json:"generation"`
	At          time.Time `json:"at"`
}
type State struct {
	MigrationSourceHash string                   `json:"migrationSourceHash,omitempty"`
	Gateways            map[string]*Gateway      `json:"gateways,omitempty"`
	MaintenanceID       string                   `json:"maintenanceId,omitempty"`
	Volumes             map[string]*Volume       `json:"volumes,omitempty"`
	Schema              int                      `json:"schema"`
	ClusterID           string                   `json:"clusterId"`
	Name                string                   `json:"name"`
	CreatedAt           time.Time                `json:"createdAt"`
	Workloads           map[string]*Workload     `json:"workloads"`
	Nodes               map[string]*Node         `json:"nodes"`
	Allocations         map[string]*Allocation   `json:"allocations"`
	Receipts            map[string]Receipt       `json:"receipts"`
	Events              []Event                  `json:"events"`
	Secrets             map[string]SecretVersion `json:"secrets,omitempty"`
}

func NewState(id, name string, now time.Time) *State {
	return &State{Schema: StateSchema, ClusterID: id, Name: name, CreatedAt: now, Workloads: map[string]*Workload{}, Nodes: map[string]*Node{}, Allocations: map[string]*Allocation{}, Receipts: map[string]Receipt{}, Events: []Event{}}
}
func (s *State) Validate() error {
	if s.MaintenanceID != "" && !ValidID(s.MaintenanceID) {
		return errors.New("MAINTENANCE_OWNER_INVALID")
	}
	if s.MigrationSourceHash != "" && !ValidSHA256(s.MigrationSourceHash) {
		return errors.New("STATE_MIGRATION_HASH_INVALID")
	}
	if s.Schema != StateSchema || !ValidID(s.ClusterID) || !ValidName(s.Name) || s.Nodes == nil || s.Workloads == nil || s.Allocations == nil || s.Receipts == nil {
		return errors.New("STATE_SCHEMA_INVALID")
	}
	if len(s.Volumes) > 64 {
		return ErrCapacity
	}
	for name, v := range s.Volumes {
		if v == nil || v.Name != name || v.Validate() != nil {
			return errors.New("VOLUME_INVENTORY_INVALID")
		}
	}
	if len(s.Nodes) > MaxNodes || len(s.Workloads) > MaxWorkloads || len(s.Allocations) > MaxAllocations || len(s.Receipts) > 256 {
		return ErrCapacity
	}
	b, e := json.Marshal(s)
	if e != nil {
		return e
	}
	if len(b) > MaxStateBytes {
		return ErrCapacity
	}
	return nil
}
func (s *State) Event(action, target string, now time.Time) {
	s.Events = append(s.Events, Event{ID: ID(), At: now, Action: action, Target: target})
	if len(s.Events) > 160 {
		s.Events = append([]Event{}, s.Events[len(s.Events)-160:]...)
	}
}
func (s *State) Request(id, hash string, now time.Time) (*Receipt, error) {
	if !ValidRequestID(id) {
		return nil, errors.New("IDEMPOTENCY_KEY_REQUIRED")
	}
	if r, ok := s.Receipts[id]; ok {
		if r.Hash != hash {
			return nil, errors.New("IDEMPOTENCY_CONFLICT")
		}
		return &r, nil
	}
	for k, r := range s.Receipts {
		if now.Sub(r.At) > 24*time.Hour {
			delete(s.Receipts, k)
		}
	}
	if len(s.Receipts) >= 256 {
		return nil, ErrCapacity
	}
	return nil, nil
}
func Apply(s *State, req ApplyRequest, requestID string, now time.Time) (Receipt, error) {
	if s.MaintenanceID != "" {
		return Receipt{}, errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
	}
	if req.APIVersion != APIVersion {
		return Receipt{}, errors.New("API_VERSION_UNSUPPORTED")
	}
	if !ValidName(req.Name) {
		return Receipt{}, errors.New("NAME_INVALID")
	}
	if e := req.Spec.Validate(); e != nil {
		return Receipt{}, e
	}
	if e := s.ValidateSecretAvailability(req.Spec); e != nil {
		return Receipt{}, e
	}
	hash := Hash(struct {
		Kind    string
		Request ApplyRequest
	}{"apply", req})
	if r, e := s.Request(requestID, hash, now); r != nil || e != nil {
		if r != nil {
			return *r, nil
		}
		return Receipt{}, e
	}
	w, exists := s.Workloads[req.Name]
	owner := ""
	if exists {
		owner = w.UID
	}
	if e := s.ValidateVolumeAvailability(req.Spec, owner); e != nil {
		return Receipt{}, e
	}
	if !exists {
		if req.ExpectedGeneration != 0 {
			return Receipt{}, ErrConflict
		}
		if len(s.Workloads) >= MaxWorkloads {
			return Receipt{}, ErrCapacity
		}
		w = &Workload{UID: ID(), Name: req.Name, CreatedAt: now, Phase: "pending"}
		s.Workloads[req.Name] = w
	} else {
		if w.Deleting || req.ExpectedGeneration != w.Generation {
			return Receipt{}, ErrConflict
		}
		w.History = append(w.History, w.Spec)
		if len(w.History) > 5 {
			w.History = w.History[len(w.History)-5:]
		}
	}
	for _, ref := range req.Spec.Volumes {
		s.Volumes[ref.Name].Owner = w.UID
	}
	w.Spec = req.Spec
	w.Generation++
	w.Phase = "pending"
	w.Reason = ""
	r := Receipt{ID: requestID, Hash: hash, WorkloadUID: w.UID, Generation: w.Generation, At: now}
	s.Receipts[requestID] = r
	s.Event("workload.accepted", w.Name, now)
	return r, nil
}
func MutateWorkload(s *State, name, kind, key string, expected int64, now time.Time) (Receipt, error) {
	if s.MaintenanceID != "" && kind != "pause" {
		return Receipt{}, errors.New("MAINTENANCE_BLOCKS_NEW_MUTATIONS")
	}
	hash := Hash(struct {
		Name, Kind string
		Generation int64
	}{name, kind, expected})
	if r, e := s.Request(key, hash, now); r != nil || e != nil {
		if r != nil {
			return *r, nil
		}
		return Receipt{}, e
	}
	w := s.Workloads[name]
	if w == nil {
		return Receipt{}, ErrNotFound
	}
	if w.Generation != expected || w.Deleting {
		return Receipt{}, ErrConflict
	}
	switch kind {
	case "pause":
		w.Paused = true
		w.Generation++
		w.Phase = "pausing"
	case "resume":
		if e := s.ValidateVolumeAvailability(w.Spec, w.UID); e != nil {
			return Receipt{}, e
		}
		w.Paused = false
		w.Generation++
		w.Phase = "pending"
	case "delete":
		w.Deleting = true
		w.Phase = "deleting"
	case "rollback":
		if len(w.History) == 0 {
			return Receipt{}, errors.New("NO_ROLLBACK_REVISION")
		}
		previous := w.History[len(w.History)-1]
		w.History = append(w.History[:len(w.History)-1], w.Spec)
		if err := s.ValidateSecretAvailability(previous); err != nil {
			return Receipt{}, err
		}
		if err := s.ValidateVolumeAvailability(previous, w.UID); err != nil {
			return Receipt{}, err
		}
		w.Spec = previous
		w.Generation++
		w.Phase = "pending"
	default:
		return Receipt{}, errors.New("ACTION_UNSUPPORTED")
	}
	r := Receipt{ID: key, Hash: hash, WorkloadUID: w.UID, Generation: w.Generation, At: now}
	s.Receipts[key] = r
	s.Event("workload."+kind, w.Name, now)
	return r, nil
}
func SortedKeys[T any](m map[string]T) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
func ValidateNode(n Node) error {
	if n.PodCIDR != "" && !ValidPodCIDR(n.PodCIDR) {
		return errors.New("POD_SUBNET_INVALID")
	}
	if !ValidID(n.ID) || !ValidName(n.Name) || !PrivateAddress(n.Address) {
		return fmt.Errorf("NODE_ID_NAME_OR_PRIVATE_IPV4_INVALID")
	}
	return nil
}
