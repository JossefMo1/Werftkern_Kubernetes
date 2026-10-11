package cli

import (
	"context"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"strings"
	"testing"
)

type smokeFixture struct {
	created           bool
	startErr, stopErr bool
	ensured, stopped  int
}

func (f *smokeFixture) Health(context.Context) error { return nil }
func (f *smokeFixture) Owned(context.Context) ([]string, error) {
	if f.created {
		return []string{"owned"}, nil
	}
	return nil, nil
}
func (f *smokeFixture) Stop(context.Context, string) error {
	f.stopped++
	if f.stopErr {
		return errors.New("cleanup failed")
	}
	f.created = false
	return nil
}
func (f *smokeFixture) Ensure(_ context.Context, a model.Allocation, ip string, allowed func() bool) (model.Report, error) {
	f.ensured++
	if !allowed() {
		return model.Report{}, errors.New("not allowed")
	}
	f.created = true
	if f.startErr {
		return model.Report{}, errors.New("lost start ACK")
	}
	return model.Report{Phase: "ready", ID: a.ID}, nil
}
func TestWorkerSmokeRequiresScopedEmptyNodeAndAlwaysCleansUp(t *testing.T) {
	cfg := config.Agent{NodeID: model.ID(), InstanceID: model.ID(), Address: "127.0.0.1", Client: config.Client{ClusterID: model.ID()}}
	op := model.ID()
	for _, c := range []string{"ok", "foreign", "active", "unlock", "old", "start-failure", "cleanup-failure"} {
		t.Run(c, func(t *testing.T) {
			s := control.NodeState{NodeID: cfg.NodeID, InstanceID: cfg.InstanceID, Address: cfg.Address, ClusterID: cfg.Client.ClusterID, MaintenanceID: op, Drain: true, Healthy: true, Version: model.Version, ControllerVersion: model.Version}
			f := &smokeFixture{}
			switch c {
			case "foreign":
				s.NodeID = model.ID()
			case "active":
				s.UnconfirmedAllocations = 1
			case "unlock":
				s.MaintenanceID = ""
			case "old":
				s.Version = "0.2.0-dev.3"
			case "start-failure":
				f.startErr = true
			case "cleanup-failure":
				f.stopErr = true
			}
			out, e := CheckWorkerEngine(context.Background(), cfg, op, "sha256:"+strings.Repeat("a", 64), f, func(context.Context) (control.NodeState, error) { return s, nil })
			if c == "ok" {
				if e != nil || !out.HTTPReady || !out.CleanupConfirmed || f.created {
					t.Fatal(out, e)
				}
			} else if e == nil {
				t.Fatal("unexpected success")
			}
			if c == "start-failure" && (f.created || f.stopped == 0) {
				t.Fatal("failed start leaked process")
			}
			if c == "foreign" || c == "active" || c == "unlock" || c == "old" {
				if f.ensured != 0 {
					t.Fatal("unadmitted start")
				}
			}
		})
	}
}
