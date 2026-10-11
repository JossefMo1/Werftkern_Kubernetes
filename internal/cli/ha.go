package cli

import (
	"context"
	"errors"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/ha"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
	"time"
)

func haCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("ha prepare --topology FILE --out NEW_DIR | ha install --kit FILE --confirm-host NAME | ha init")
	}
	f := parser("ha")
	top := f.String("topology", "", "Topology")
	out := f.String("out", "", "Private kit directory")
	kit := f.String("kit", "", "Private host kit")
	confirm := f.String("confirm-host", "", "Exact target name")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	switch args[0] {
	case "prepare":
		var t ha.Topology
		if e := safefile.ReadJSON(*top, &t); e != nil {
			return e
		}
		ks, e := ha.Prepare(t, time.Now().UTC())
		if e != nil {
			return e
		}
		if e = ha.WriteKits(*out, ks); e != nil {
			return e
		}
		fmt.Println("Private per-host kits written. They contain keys: transfer through verified SSH only; never publish.")
		return nil
	case "install":
		return ha.Install(ctx, *kit, *confirm)
	case "init":
		return ha.Initialize(ctx)
	default:
		return errors.New("HA_ACTION_UNSUPPORTED")
	}
}
