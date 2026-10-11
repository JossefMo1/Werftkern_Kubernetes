// Package engine isolates the native scheduler from the local container runtime.
// The alpha implements the documented Docker Engine HTTP API over a Unix socket.
package engine

import (
	"context"
	"github.com/ClusterPilot-System/werftkern/internal/model"
)

type Runtime interface {
	Health(context.Context) error
	Ensure(context.Context, model.Allocation, string, func() bool) (model.Report, error)
	Stop(context.Context, string) error
	Owned(context.Context) ([]string, error)
}
