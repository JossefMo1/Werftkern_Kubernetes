package cli

import (
	"context"
	"errors"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/apiclient"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/discovery"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
	"time"
)

func discoveryCommand(ctx context.Context, args []string) error {
	f := parser("discovery")
	path := f.String("config", config.Directory+"/agent.json", "Node configuration")
	out := f.String("out", config.Data+"/dns/zone", "CoreDNS zone file")
	once := f.Bool("once", false, "One read only")
	if e := f.Parse(args); e != nil {
		return e
	}
	c, e := config.Load[config.Agent](*path)
	if e != nil {
		return e
	}
	cl, e := apiclient.New(c.Client)
	if e != nil {
		return e
	}
	serial := uint32(time.Now().Unix())
	lastSuccess := time.Time{}
	empty := discovery.Snapshot{ClusterID: c.Client.ClusterID}
	writeZone := func(s discovery.Snapshot) error {
		serial++
		b, e := discovery.Render(s, serial)
		if e != nil {
			return e
		}
		return safefile.Write(*out, b, 0644)
	}
	if e = writeZone(empty); e != nil {
		return e
	}
	t := time.NewTicker(3 * time.Second)
	defer t.Stop()
	for {
		var s discovery.Snapshot
		op, cancel := context.WithTimeout(ctx, 8*time.Second)
		e = cl.Call(op, "GET", "/v1/discovery", nil, &s, "")
		cancel()
		if e == nil && (s.ClusterID != c.Client.ClusterID || time.Since(s.At) > 30*time.Second || time.Until(s.At) > 5*time.Second) {
			e = errors.New("DISCOVERY_SCOPE_OR_FRESHNESS_INVALID")
		}
		if e == nil {
			if e = writeZone(s); e != nil {
				return e
			}
			lastSuccess = time.Now()
		} else if time.Since(lastSuccess) > 15*time.Second {
			if we := writeZone(empty); we != nil {
				return we
			}
		}
		if *once {
			if e == nil {
				fmt.Println("Headless DNS zone generated; server reachability is not yet verified.")
			}
			return e
		}
		select {
		case <-ctx.Done():
			return writeZone(empty)
		case <-t.C:
		}
	}
}
