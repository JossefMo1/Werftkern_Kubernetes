package cli

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/apiclient"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/control"
	"github.com/ClusterPilot-System/werftkern/internal/engine"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
)

type WorkerSmokeResult struct {
	ClusterID        string    `json:"clusterId"`
	NodeID           string    `json:"nodeId"`
	OperationID      string    `json:"operationId"`
	Version          string    `json:"version"`
	HTTPReady        bool      `json:"httpReady"`
	CleanupConfirmed bool      `json:"cleanupConfirmed"`
	CheckedAt        time.Time `json:"checkedAt"`
}

// CheckWorkerEngine uses the SAME engine path as normal applications with a
// distinct owned container namespace. It does not create a scheduler allocation
// or claim to verify DNS, multi-host routing, application data or business logic.
// The deterministic ID makes an interrupted smoke recoverable on retry.
func CheckWorkerEngine(ctx context.Context, cfg config.Agent, operation, image string, runtime engine.Runtime, scope func(context.Context) (control.NodeState, error)) (out WorkerSmokeResult, err error) {
	if !model.ValidID(operation) {
		return out, errors.New("MAINTENANCE_ID_REQUIRED")
	}
	verify := func(ctx context.Context) error {
		s, e := scope(ctx)
		if e != nil {
			return e
		}
		return validateSmokeScope(cfg, operation, s)
	}
	if e := verify(ctx); e != nil {
		return out, e
	}
	allocation := model.Allocation{ID: model.Hash([]string{"worker-smoke", operation, cfg.NodeID})[:32], NodeID: cfg.NodeID,
		WorkloadUID: model.Hash([]string{"worker-smoke-workload", operation, cfg.NodeID})[:32], Name: "node-smoke", Generation: 1,
		Desired: "run", HostPort: 22999, Spec: model.Spec{Image: image, Replicas: 1, CPUMilli: 100, MemoryMiB: 64, Port: 8080, ReadinessPath: "/healthz"}}
	if e := allocation.Spec.Validate(); e != nil {
		return out, e
	}
	defer func() {
		// Cancellation of the main context must not skip cleanup.
		cleanup, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if e := runtime.Stop(cleanup, allocation.ID); e != nil {
			err = errors.New("WORKER_SMOKE_CLEANUP_UNCONFIRMED")
			out.CleanupConfirmed = false
			return
		}
		ids, e := runtime.Owned(cleanup)
		if e != nil || len(ids) != 0 {
			err = errors.New("WORKER_SMOKE_RESOURCES_REMAIN")
			out.CleanupConfirmed = false
			return
		}
		out.CleanupConfirmed = true
	}()
	for {
		if e := verify(ctx); e != nil {
			return out, e
		}
		report, e := runtime.Ensure(ctx, allocation, cfg.Address, func() bool { return verify(ctx) == nil })
		if e != nil {
			return out, e
		}
		if report.Phase == "ready" {
			if e = verify(ctx); e != nil {
				return out, e
			}
			out = WorkerSmokeResult{ClusterID: cfg.Client.ClusterID, NodeID: cfg.NodeID, OperationID: operation, Version: model.Version, HTTPReady: true, CheckedAt: time.Now().UTC()}
			return out, nil
		}
		select {
		case <-ctx.Done():
			return out, ctx.Err()
		case <-time.After(time.Second):
		}
	}
}

func validateSmokeScope(cfg config.Agent, operation string, s control.NodeState) error {
	if s.ClusterID != cfg.Client.ClusterID || s.NodeID != cfg.NodeID || s.InstanceID != cfg.InstanceID || s.Address != cfg.Address || s.MaintenanceID != operation || !s.Drain || !s.Healthy || s.Version != model.Version || s.ControllerVersion != model.Version || s.UnconfirmedAllocations != 0 {
		return errors.New("SMOKE_REQUIRES_OWNED_EMPTY_DRAINED_TARGET_WORKER")
	}
	return nil
}

func workerCheck(ctx context.Context, args []string) error {
	f := parser("worker-check")
	op := f.String("operation", "", "Existing maintenance owner")
	js := f.Bool("json", false, "Structured smoke receipt")
	if e := f.Parse(args); e != nil {
		return e
	}
	if f.NArg() != 0 || !*js || !model.ValidID(*op) || os.Geteuid() != 0 {
		return errors.New("worker-check --operation ID --json (root required)")
	}
	cfg, e := config.Load[config.Agent](filepath.Join(config.Directory, "agent.json"))
	if e != nil {
		return e
	}
	if _, e = os.Stat(filepath.Join(config.Directory, "control.json")); !os.IsNotExist(e) {
		return errors.New("WORKER_ONLY_HOST_REQUIRED")
	}
	guard, e := safefile.DirectoryLock(filepath.Join(config.Data, "worker-check"), true)
	if e != nil {
		return e
	}
	defer guard.Close()
	client, e := apiclient.New(cfg.Client)
	if e != nil {
		return e
	}
	scope := func(ctx context.Context) (control.NodeState, error) {
		var s control.NodeState
		e := client.Call(ctx, "GET", "/v1/node-state", nil, &s, "")
		return s, e
	}
	// Separately labelled namespace prevents the normal agent's garbage collector
	// from adopting/deleting this bounded qualification process.
	namespace := model.Hash([]string{"worker-smoke-namespace", cfg.Client.ClusterID, cfg.NodeID, *op})[:32]
	d := engine.NewDocker(cfg.Socket, namespace)
	d.Network = cfg.Network
	d.DNS = cfg.DNS
	path := cfg.DemoArchive
	if path == "" {
		path = "/usr/share/werftkern/demo-image.tar"
	}
	if e = verifyDemoArchive(path); e != nil {
		return e
	}
	meta, e := config.Load[DemoMetadata](filepath.Join(filepath.Dir(path), "demo.json"))
	if e != nil {
		return e
	}
	admission, e := scope(ctx)
	if e != nil {
		return e
	}
	if e = validateSmokeScope(cfg, *op, admission); e != nil {
		return e
	}
	if e = d.Load(ctx, path); e != nil {
		return e
	}
	bounded, cancel := context.WithTimeout(ctx, 90*time.Second)
	defer cancel()
	out, e := CheckWorkerEngine(bounded, cfg, *op, meta.Image, d, scope)
	if e != nil {
		return e
	}
	return json.NewEncoder(os.Stdout).Encode(out)
}
