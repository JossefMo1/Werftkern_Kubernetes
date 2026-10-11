package cli

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/discovery"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/ingress"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/setup"
)

func ingressCommand(ctx context.Context, args []string) error {
	f := parser("ingress")
	file := f.String("config", "", "Ingress configuration with dedicated gateway credentials")
	if e := f.Parse(args); e != nil {
		return e
	}
	if *file == "" || f.NArg() != 0 {
		return errors.New("INGRESS_CONFIG_REQUIRED")
	}
	cfg, e := config.Load[ingress.Config](*file)
	if e != nil {
		return e
	}
	base, e := filepath.Abs(filepath.Dir(*file))
	if e != nil {
		return e
	}
	resolve := func(s string) string {
		if filepath.IsAbs(s) {
			return s
		}
		return filepath.Join(base, s)
	}
	cfg.Client.CA = resolve(cfg.Client.CA)
	cfg.Client.Cert = resolve(cfg.Client.Cert)
	cfg.Client.Key = resolve(cfg.Client.Key)
	cfg.Certificate = resolve(cfg.Certificate)
	cfg.PrivateKey = resolve(cfg.PrivateKey)
	ca, e := os.ReadFile(cfg.Client.CA)
	if e != nil {
		return e
	}
	cert, e := os.ReadFile(cfg.Client.Cert)
	if e != nil {
		return e
	}
	key, e := os.ReadFile(cfg.Client.Key)
	if e != nil {
		return e
	}
	if e = pki.ValidateIdentity(ca, pki.Pair{Cert: cert, Key: key}, "gateway:"+cfg.GatewayID, cfg.Client.ClusterID); e != nil {
		return errors.New("DEDICATED_GATEWAY_CERTIFICATE_REQUIRED")
	}
	client, e := apiclient.New(cfg.Client)
	if e != nil {
		return e
	}
	gw, e := ingress.New(cfg)
	if e != nil {
		return e
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	refresh := func() {
		var snap discovery.Snapshot
		call, done := context.WithTimeout(ctx, 5*time.Second)
		e := client.Call(call, "GET", "/v1/discovery", nil, &snap, "")
		done()
		if e == nil {
			e = gw.Accept(snap)
		}
		if e != nil {
			gw.Invalidate()
			log.Print("ingress.discovery_unavailable_or_rejected; routes fail closed")
		}
	}
	refresh()
	go func() {
		tick := time.NewTicker(3 * time.Second)
		defer tick.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-tick.C:
				refresh()
			}
		}
	}()
	return gw.Serve(ctx)
}
func gatewayCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("gateway list | enroll --name NAME --services web,api --out NEW_DIR | revoke ID")
	}
	c, e := client()
	if e != nil {
		return e
	}
	switch args[0] {
	case "list":
		s, e := c.State(ctx)
		if e != nil {
			return e
		}
		return json.NewEncoder(os.Stdout).Encode(s.Gateways)
	case "revoke":
		if len(args) != 2 || !model.ValidID(args[1]) {
			return errors.New("GATEWAY_ID_REQUIRED")
		}
		return c.Call(ctx, "POST", "/v1/gateways/"+args[1]+"/revoke", nil, nil, model.ID())
	case "enroll":
		if e = setup.RequireRoot(); e != nil {
			return e
		}
		f := parser("gateway enroll")
		name := f.String("name", "", "Gateway name")
		services := f.String("services", "", "Comma separated explicit service allowlist")
		out := f.String("out", "", "Private credentials directory")
		if e = f.Parse(args[1:]); e != nil {
			return e
		}
		if *out == "" || f.NArg() != 0 {
			return errors.New("GATEWAY_OUTPUT_REQUIRED")
		}
		dir, e := filepath.Abs(*out)
		if e != nil {
			return e
		}
		q := model.Gateway{ID: model.ID(), Name: *name, Services: strings.Split(*services, ",")}
		q.Normalize()
		if e = q.Validate(); e != nil {
			return e
		}
		if _, e = os.Lstat(dir); e == nil {
			var previous model.Gateway
			if e = safefile.ReadJSON(filepath.Join(dir, "gateway.json"), &previous); e != nil {
				return errors.New("INCOMPLETE_ENROLLMENT_DIRECTORY_REQUIRES_REVIEW")
			}
			q.ID = previous.ID
			if model.Hash(q) != model.Hash(previous) {
				return errors.New("EXISTING_GATEWAY_BUNDLE_CONFLICT")
			}
			ca, e := os.ReadFile(filepath.Join(dir, "ca.crt"))
			if e != nil {
				return e
			}
			cert, e := os.ReadFile(filepath.Join(dir, "gateway.crt"))
			if e != nil {
				return e
			}
			key, e := os.ReadFile(filepath.Join(dir, "gateway.key"))
			if e != nil {
				return e
			}
			if e = pki.ValidateIdentity(ca, pki.Pair{Cert: cert, Key: key}, "gateway:"+q.ID, c.ClusterID); e != nil {
				return e
			}
		} else if !os.IsNotExist(e) {
			return e
		} else {
			admin, e := config.Load[config.Client](config.AdminPath())
			if e != nil {
				return e
			}
			ca, e := os.ReadFile(config.Directory + "/authority/client.crt")
			if e != nil {
				return e
			}
			key, e := os.ReadFile(config.Directory + "/authority/client.key")
			if e != nil {
				return e
			}
			pair, e := pki.Issue(pki.Pair{Cert: ca, Key: key}, "gateway:"+q.ID, c.ClusterID, nil, false, time.Now())
			if e != nil {
				return e
			}
			if e = os.Mkdir(dir, 0700); e != nil {
				return e
			}
			for name, bytes := range map[string][]byte{"ca.crt": ca, "gateway.crt": pair.Cert, "gateway.key": pair.Key} {
				if e = safefile.Write(filepath.Join(dir, name), bytes, 0600); e != nil {
					return e
				}
			}
			admin.CA = "ca.crt"
			admin.Cert = "gateway.crt"
			admin.Key = "gateway.key"
			example := ingress.Config{Client: admin, GatewayID: q.ID, Listen: "127.0.0.1:8443", Certificate: "edge.crt", PrivateKey: "edge.key", AllowedCIDRs: []string{}, UpstreamMode: "private-http", Routes: []ingress.Route{}}
			state, e := c.State(ctx)
			if e != nil {
				return e
			}
			seen := map[string]bool{}
			for _, id := range model.SortedKeys(state.Nodes) {
				n := state.Nodes[id]
				for _, cidr := range []string{n.Address + "/32", n.PodCIDR} {
					if cidr != "" && !seen[cidr] {
						example.AllowedCIDRs = append(example.AllowedCIDRs, cidr)
						seen[cidr] = true
					}
				}
			}
			for _, service := range q.Services {
				example.Routes = append(example.Routes, ingress.Route{Host: service + ".example.invalid", Service: service})
			}
			if e = safefile.JSON(filepath.Join(dir, "ingress.example.json"), example, 0600); e != nil {
				return e
			}
			if e = safefile.JSON(filepath.Join(dir, "gateway.json"), q, 0600); e != nil {
				return e
			}
		}
		if e = c.Call(ctx, "POST", "/v1/gateways", q, nil, q.ID); e != nil {
			return fmt.Errorf("GATEWAY_REGISTRATION_PENDING_RETRY_SAME_DIRECTORY: %w", e)
		}
		fmt.Printf("Gateway %s registered. Credentials are private; copy via verified SSH only. Configure route DNS, edge TLS files, bind address and upstream CIDRs in ingress.example.json before starting.\n", q.ID)
		return nil
	default:
		return errors.New("GATEWAY_ACTION_UNSUPPORTED")
	}
}
