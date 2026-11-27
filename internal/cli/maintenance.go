package cli

import (
	"context"
	"errors"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
)

func maintenanceCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("maintenance on|off --id OPERATION_ID --reason NAME")
	}
	f := parser("maintenance")
	id := f.String("id", "", "Operation owner ID")
	reason := f.String("reason", "operator-maintenance", "Reason")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	if f.NArg() != 0 {
		return errors.New("MAINTENANCE_ARGUMENTS_INVALID")
	}
	if args[0] != "on" && args[0] != "off" {
		return errors.New("MAINTENANCE_ACTION_INVALID")
	}
	if !model.ValidID(*id) || !model.ValidName(*reason) {
		return errors.New("MAINTENANCE_REQUEST_INVALID")
	}
	c, e := client()
	if e != nil {
		return e
	}
	return c.Call(ctx, "POST", "/v1/maintenance", control.MaintenanceRequest{ID: *id, Enabled: args[0] == "on", Reason: *reason}, nil, *id)
}
