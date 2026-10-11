package cli

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
)

func workerStatus(ctx context.Context, args []string) error {
	f := parser("worker-status")
	file := f.String("config", filepath.Join(config.Directory, "agent.json"), "Local node identity, never admin credentials")
	output := f.Bool("json", false, "Structured node-scoped status")
	if e := f.Parse(args); e != nil {
		return e
	}
	if f.NArg() != 0 || !*output {
		return errors.New("worker-status --json [--config AGENT_FILE]")
	}
	cfg, e := config.Load[config.Agent](*file)
	if e != nil {
		return e
	}
	c, e := apiclient.New(cfg.Client)
	if e != nil {
		return e
	}
	var x control.NodeState
	if e = c.Call(ctx, "GET", "/v1/node-state", nil, &x, ""); e != nil {
		return e
	}
	if x.ClusterID != cfg.Client.ClusterID || x.NodeID != cfg.NodeID || x.InstanceID != cfg.InstanceID || x.Address != cfg.Address {
		return errors.New("NODE_SCOPE_IDENTITY_MISMATCH")
	}
	return json.NewEncoder(os.Stdout).Encode(x)
}
func maintenanceNodeCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("maintenance-node drain|uncordon --node ID --id OPERATION_ID")
	}
	f := parser("maintenance-node")
	node := f.String("node", "", "Node ID")
	id := f.String("id", "", "Maintenance owner")
	version := f.String("expected-version", "", "Required agent version for uncordon")
	seq := f.Uint64("min-sequence", 0, "Observed successful heartbeat sequence")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	if f.NArg() != 0 || !model.ValidID(*node) || !model.ValidID(*id) || args[0] != "drain" && args[0] != "uncordon" {
		return errors.New("MAINTENANCE_NODE_ARGUMENTS_INVALID")
	}
	c, e := client()
	if e != nil {
		return e
	}
	var result control.NodeState
	e = c.Call(ctx, "POST", "/v1/maintenance/nodes/"+*node+"/"+args[0], control.MaintenanceNodeRequest{ID: *id, ExpectedVersion: *version, MinSequence: *seq}, &result, *id)
	if e != nil {
		return e
	}
	return json.NewEncoder(os.Stdout).Encode(result)
}
