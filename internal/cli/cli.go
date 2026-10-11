package cli

import (
	"bufio"
	"context"
	"crypto/sha256"
	"crypto/x509"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/agent"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/dashboard"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/engine"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/failover"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/setup"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/store"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/strictjson"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync/atomic"
	"syscall"
	"text/tabwriter"
	"time"
)

var BuildCommit = "uncommitted"
var BuildTime = "unrecorded"

func parser(name string) *flag.FlagSet {
	f := flag.NewFlagSet(name, flag.ContinueOnError)
	f.SetOutput(os.Stderr)
	return f
}
func client() (*apiclient.Client, error) {
	c, e := config.Load[config.Client](config.AdminPath())
	if e != nil {
		return nil, fmt.Errorf("ADMIN_CONFIGURATION_UNAVAILABLE: %w", e)
	}
	return apiclient.New(c)
}
func Help() {
	fmt.Print(`Werftkern — 0.2.0-dev.4 (experimentell, kein offizielles Kubernetes)

Installation auf Ubuntu 24.04 LTS amd64:
  sudo apt install ./werftkern_0.2.0~dev4_amd64.deb
  sudo werft setup

Befehle:
  ha prepare --topology FILE --out NEW_DIR   Drei-Controller-Kits generieren
  ha install --kit FILE --confirm-host NAME
  ha init                                  Einmaliger etcd-Seed-Commit
  certificate inspect|bundle|renew|install  Atomare Leaf-Erneuerung; siehe CERTIFICATE-ROTATION.md
  schema inspect|migrate --maintenance-id ID   Offline-Schema1→2; siehe SCHEMA-MIGRATION.md
  gateway list|enroll|revoke                  Separate, beschränkte Ingress-Identität
  ingress --config FILE                     TLS-Ingress, explizite Routen/Trust
  volume list | create NAME --node ID --uid UID --gid GID
  volume backup NAME --file FILE --key-file KEY --maintenance-id ID
  volume restore NAME --file FILE --key-file KEY --maintenance-id ID --operation-id ID
  database manifest NAME --image DIGEST --node ID --volume NAME
  discovery [--once]                        Headless-DNS-Zone für CoreDNS
  worker-check --operation ID --json         Echter lokaler Container-/HTTP-Smoke
  worker-status --json                       Eigene Workeridentität und Drain-Zustand
  maintenance-node drain|uncordon --node ID --id ID
  maintenance on|off --id ID --reason NAME  Clusterweiter Update-Lock
  release verify --manifest FILE --signature FILE --public-key FILE --package FILE
  werft-ops --help                          Netzwerk, Cloud, PostgreSQL, Updates
  setup [--name clusterpilot] [--address IP] [--controller-only]
  setup --join /pfad/worker.join.json
  health --all --json                  Jeden Controller ohne Failover einzeln prüfen
  status [--json]                       Cluster- und Anwendungszustand
  demo [--replicas 2] [--wait]           Mitgelieferte Offline-Testanwendung
  apply DATEI.json                     Manifest annehmen (oder - für stdin)
  scale NAME ANZAHL                    Neue Revision mit anderer Replikazahl
  rollback NAME                       Vorige Spezifikation als neue Revision
  delete NAME                         Geordnete Löschung einschließlich Container
  wait NAME [--timeout 120s]            Auf beobachtete Readiness warten
  endpoints NAME                      Private Node-Endpoints anzeigen
  tunnel NAME [--listen 127.0.0.1:8088] Separate lokale Anwendungsweiterleitung
  node bundle --name NAME --address IP --out DATEI.join.json
  node drain NAME | node uncordon NAME | node revoke NAME
  dashboard [--listen 127.0.0.1:8787]   Lokale Verwaltungsoberfläche
  logs ALLOCATION_ID                   Lokale Node-Logs (nicht zentral aggregiert)
  export DATEI.json                    Metadatenexport; kein vollständiges Backup
  pause NAME | resume NAME            Kontrolliert stoppen/neu starten
  secret put NAME --file DATEI [--expected-version 0]
  secret list                         Metadaten, niemals Secret-Werte
  backup create --out DATEI --key-file SCHLUESSEL
  backup inspect --file DATEI --key-file SCHLUESSEL
  backup restore --file DATEI --key-file SCHLUESSEL --target-cluster ID
  assess DATEI.json                   Kubernetes-JSON nur lesend prüfen
  doctor                              Voraussetzungen, Identität und Ablauf prüfen
  version                             Buildinformationen

Die API ist mTLS-geschützt. Private Node-Adressen müssen erreichbar sein.
WERFT_CONFIG kann einen anderen Admin-Client-Konfigurationspfad setzen.
HA-/Storage-/Datenbankpfade sind experimentell. Keine Produktionsfreigabe oder Kubernetes-/Helm-Kompatibilität.
`)
}
func Run(ctx context.Context, args []string) error {
	if len(args) == 0 {
		Help()
		return nil
	}
	switch args[0] {
	case "worker-check":
		return workerCheck(ctx, args[1:])
	case "worker-status":
		return workerStatus(ctx, args[1:])
	case "maintenance-node":
		return maintenanceNodeCommand(ctx, args[1:])
	case "help", "--help", "-h":
		Help()
		return nil
	case "version":
		fmt.Printf("Werftkern %s\ncommit=%s\nbuildTime=%s\ncompiler=%s\nplatform=%s/%s\nmaturity=experimental\n", model.Version, BuildCommit, BuildTime, runtime.Version(), runtime.GOOS, runtime.GOARCH)
		return nil
	case "certificate":
		return certificateCommand(args[1:])
	case "schema":
		return schemaCommand(ctx, args[1:])
	case "ingress":
		return ingressCommand(ctx, args[1:])
	case "gateway":
		return gatewayCommand(ctx, args[1:])
	case "discovery":
		return discoveryCommand(ctx, args[1:])
	case "maintenance":
		return maintenanceCommand(ctx, args[1:])
	case "release":
		return releaseCommand(ctx, args[1:])
	case "ha":
		return haCommand(ctx, args[1:])
	case "setup":
		return setupCommand(ctx, args[1:])
	case "control":
		return controlCommand(ctx, args[1:])
	case "agent":
		return agentCommand(ctx, args[1:])
	case "health":
		return healthCommand(ctx, args[1:])
	case "status":
		return statusCommand(ctx, args[1:])
	case "apply":
		return applyCommand(ctx, args[1:])
	case "scale":
		return scaleCommand(ctx, args[1:])
	case "volume":
		return volumeCommand(ctx, args[1:])
	case "database":
		return databaseCommand(ctx, args[1:])
	case "secret":
		return secretCommand(ctx, args[1:])
	case "backup":
		return backupCommand(ctx, args[1:])
	case "assess":
		return assessCommand(args[1:])
	case "delete", "rollback", "pause", "resume":
		return mutateCommand(ctx, args[0], args[1:])
	case "wait":
		if len(args) < 2 {
			return errors.New("wait NAME [--timeout 120s]")
		}
		f := parser("wait")
		duration := f.Duration("timeout", 120*time.Second, "Deadline")
		if e := f.Parse(args[2:]); e != nil {
			return e
		}
		c, e := client()
		if e != nil {
			return e
		}
		return Wait(ctx, c, args[1], *duration)
	case "endpoints":
		return endpointsCommand(ctx, args[1:])
	case "tunnel":
		return tunnelCommand(ctx, args[1:])
	case "node":
		return nodeCommand(ctx, args[1:])
	case "demo":
		return demoCommand(ctx, args[1:])
	case "dashboard":
		f := parser("dashboard")
		listen := f.String("listen", "127.0.0.1:8787", "Loopback")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		c, e := client()
		if e != nil {
			return e
		}
		return dashboard.Serve(ctx, c, *listen)
	case "doctor":
		return doctor(ctx)
	case "logs":
		return logsCommand(ctx, args[1:])
	case "export":
		if len(args) != 2 {
			return errors.New("export DATEI.json")
		}
		c, e := client()
		if e != nil {
			return e
		}
		s, e := c.State(ctx)
		if e != nil {
			return e
		}
		if e = safefile.JSON(args[1], s, 0600); e != nil {
			return e
		}
		fmt.Println("Metadaten exportiert. Private Schlüssel und Runtime-Daten sind NICHT enthalten; kein Disaster-Recovery-Backup.")
		return nil
	default:
		return fmt.Errorf("Unbekannter Befehl: %s; werft help", args[0])
	}
}
func setupCommand(ctx context.Context, args []string) error {
	f := parser("setup")
	name := f.String("name", "clusterpilot", "Clustername")
	address := f.String("address", "", "Private lokale IPv4")
	join := f.String("join", "", "Geschützte Beitrittsdatei")
	only := f.Bool("controller-only", false, "Kein lokaler Worker")
	if e := f.Parse(args); e != nil {
		return e
	}
	if f.NArg() != 0 {
		return errors.New("UNEXPECTED_ARGUMENT")
	}
	if *join != "" {
		return setup.Join(ctx, *join)
	}
	if _, e := os.Stat(config.Directory + "/setup.json"); e == nil {
		return setup.Resume(ctx)
	}
	if e := setup.Preflight(); e != nil {
		return e
	}
	fmt.Println("Werftkern — experimentelle Native-Alpha.\nNur auf einer dedizierten Test-VM verwenden. Netzwerk und Paketquellen müssen vertrauenswürdig sein.")
	if *address == "" {
		reader := bufio.NewReader(os.Stdin)
		fmt.Print("[1] Neuen Cluster starten  [2] Diesen Host als Worker verbinden [1]: ")
		choice, e := reader.ReadString('\n')
		if e != nil {
			return errors.New("INTERACTIVE_INPUT_REQUIRED; alternativ --address IP oder --join DATEI")
		}
		if strings.TrimSpace(choice) == "2" {
			fmt.Print("Pfad zur geschützten Beitrittsdatei: ")
			p, e := reader.ReadString('\n')
			if e != nil {
				return e
			}
			return setup.Join(ctx, strings.TrimSpace(p))
		}
		if strings.TrimSpace(choice) != "" && strings.TrimSpace(choice) != "1" {
			return errors.New("INVALID_CHOICE")
		}
		suggestion := setup.SuggestedIP()
		fmt.Printf("Private IPv4 dieses Hosts [%s]: ", suggestion)
		ip, e := reader.ReadString('\n')
		if e != nil {
			return e
		}
		*address = strings.TrimSpace(ip)
		if *address == "" {
			*address = suggestion
		}
	}
	fmt.Printf("Ziel: %s · %s · lokaler Worker: %t\n", *name, *address, !*only)
	return setup.Init(ctx, *name, *address, !*only)
}
func lock(path string) (func(), error) {
	if e := os.MkdirAll(filepath.Dir(path), 0700); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	if e = syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		f.Close()
		return nil, errors.New("ANOTHER_INSTANCE_HOLDS_THE_LOCAL_LOCK")
	}
	return func() { syscall.Flock(int(f.Fd()), syscall.LOCK_UN); f.Close() }, nil
}
func controlCommand(ctx context.Context, args []string) error {
	f := parser("control")
	path := f.String("config", config.Directory+"/control.json", "Config")
	if e := f.Parse(args); e != nil {
		return e
	}
	c, e := config.Load[config.Control](*path)
	if e != nil {
		return e
	}
	if e = config.ValidateClient(c.Client); e != nil {
		return e
	}
	unlock, e := lock(c.DataDir + "/controller.lock")
	if e != nil {
		return e
	}
	defer unlock()
	ec, e := pki.ClientFiles(c.Etcd.CA, c.Etcd.Cert, c.Etcd.Key)
	if e != nil {
		return e
	}
	if len(c.Etcd.Servers) > 0 {
		tr, err := failover.New(ec.Transport, c.Etcd.Servers)
		if err != nil {
			return err
		}
		ec.Transport = tr
	}
	db := store.NewEtcd(c.Etcd.Server, ec, c.Client.ClusterID)
	if _, _, e = db.Read(ctx); e != nil {
		return e
	}
	tlsConfig, e := pki.ServerFiles(c.Client.CA, c.Client.Cert, c.Client.Key)
	if e != nil {
		return e
	}
	if c.VaultKey == "" {
		c.VaultKey = c.DataDir + "/vault.key"
	}
	master, e := vault.LoadKey(c.VaultKey)
	if e != nil {
		return errors.New("VAULT_KEY_UNAVAILABLE; never generate a replacement for a cluster containing secrets")
	}
	v, e := vault.New(master)
	if e != nil {
		return e
	}
	api := &control.API{Store: db, ClusterID: c.Client.ClusterID, Vault: v}
	local, cancel := context.WithCancel(ctx)
	defer cancel()
	go api.RunReconciler(local)
	srv := &http.Server{Addr: c.Listen, Handler: api.Handler(), TLSConfig: tlsConfig, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 20 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 << 10}
	go func() {
		<-local.Done()
		shutdown, c := context.WithTimeout(context.Background(), 5*time.Second)
		defer c()
		srv.Shutdown(shutdown)
	}()
	log.Printf("control_listening address=%s maturity=experimental", c.Listen)
	e = srv.ListenAndServeTLS("", "")
	if e == http.ErrServerClosed {
		return nil
	}
	return e
}
func agentCommand(ctx context.Context, args []string) error {
	f := parser("agent")
	path := f.String("config", config.Directory+"/agent.json", "Config")
	if e := f.Parse(args); e != nil {
		return e
	}
	c, e := config.Load[config.Agent](*path)
	if e != nil {
		return e
	}
	unlock, e := lock(filepath.Dir(c.Journal) + "/agent.lock")
	if e != nil {
		return e
	}
	defer unlock()
	cl, e := apiclient.New(c.Client)
	if e != nil {
		return e
	}
	d := engine.NewDocker(c.Socket, c.Client.ClusterID)
	d.VolumeRoot = c.VolumeRoot
	d.DNS = c.DNS
	d.Network = c.Network
	d.Volumes = func(ctx context.Context, a model.Allocation) ([]model.Volume, error) {
		var out []model.Volume
		e := cl.Call(ctx, "GET", "/v1/allocations/"+a.ID+"/volumes", nil, &out, "")
		return out, e
	}
	d.VolumeAck = func(ctx context.Context, a model.Allocation, name string) error {
		return cl.Call(ctx, "POST", "/v1/volumes/"+name+"/initialized", map[string]string{"allocationId": a.ID}, nil, model.Hash(a.ID+name))
	}
	d.Secrets = func(ctx context.Context, a model.Allocation) (map[string][]byte, error) {
		var out map[string][]byte
		e := cl.Call(ctx, "GET", "/v1/allocations/"+a.ID+"/secrets", nil, &out, "")
		return out, e
	}
	if c.DemoArchive != "" {
		if _, e = os.Stat(c.DemoArchive); e == nil {
			if e = verifyDemoArchive(c.DemoArchive); e != nil {
				return e
			}
			log.Print("loading_packaged_demo_image")
			if e = d.Load(ctx, c.DemoArchive); e != nil {
				return e
			}
		}
	}
	a, e := agent.New(c, cl, d)
	if e != nil {
		return e
	}
	return a.Run(ctx)
}

type DemoMetadata struct {
	Image         string `json:"image"`
	ArchiveSHA256 string `json:"archiveSha256"`
	Compiler      string `json:"compiler"`
}

func verifyDemoArchive(path string) error {
	m, e := config.Load[DemoMetadata](filepath.Join(filepath.Dir(path), "demo.json"))
	if e != nil {
		return e
	}
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	h := sha256.New()
	if _, e = io.Copy(h, f); e != nil {
		return e
	}
	if hex.EncodeToString(h.Sum(nil)) != m.ArchiveSHA256 {
		return errors.New("PACKAGED_DEMO_CHECKSUM_MISMATCH")
	}
	return nil
}
func statusCommand(ctx context.Context, args []string) error {
	f := parser("status")
	raw := f.Bool("json", false, "JSON")
	if e := f.Parse(args); e != nil {
		return e
	}
	c, e := client()
	if e != nil {
		return e
	}
	s, e := c.State(ctx)
	if e != nil {
		return e
	}
	if *raw {
		b, e := json.MarshalIndent(s, "", "  ")
		if e != nil {
			return e
		}
		fmt.Println(string(b))
		return nil
	}
	fmt.Printf("Cluster: %s (%s) · experimental\n", s.Name, s.ClusterID)
	w := tabwriter.NewWriter(os.Stdout, 0, 4, 2, ' ', 0)
	fmt.Fprintln(w, "NODE\tSTATUS\tPRIVATE IP\tCPU m\tRAM MiB")
	for _, id := range model.SortedKeys(s.Nodes) {
		n := s.Nodes[id]
		phase := "Unknown"
		if n.Ready(time.Now()) {
			phase = "Ready"
		}
		if n.Drain {
			phase += "/Drain"
		}
		if n.Revoked {
			phase = "Revoked"
		}
		fmt.Fprintf(w, "%s\t%s\t%s\t%d\t%d\n", n.Name, phase, n.Address, n.CPUMilli, n.MemoryMiB)
	}
	w.Flush()
	fmt.Println()
	w = tabwriter.NewWriter(os.Stdout, 0, 4, 2, ' ', 0)
	fmt.Fprintln(w, "ANWENDUNG\tSTATUS\tSOLL\tREVISION\tGRUND")
	for _, name := range model.SortedKeys(s.Workloads) {
		a := s.Workloads[name]
		fmt.Fprintf(w, "%s\t%s\t%d\tr%d\t%s\n", name, a.Phase, a.Spec.Replicas, a.Generation, a.Reason)
	}
	return w.Flush()
}
func readManifest(path string) (model.ApplyRequest, error) {
	var req model.ApplyRequest
	var r io.Reader = os.Stdin
	if path != "-" {
		f, e := os.Open(path)
		if e != nil {
			return req, e
		}
		defer f.Close()
		r = f
	}
	raw, e := io.ReadAll(io.LimitReader(r, 65537))
	if e != nil {
		return req, e
	}
	if len(raw) > 65536 {
		return req, errors.New("MANIFEST_TOO_LARGE")
	}
	if e := strictjson.Unmarshal(raw, &req); e != nil {
		return req, e
	}
	return req, nil
}
func apply(ctx context.Context, c *apiclient.Client, req model.ApplyRequest) error {
	if req.APIVersion == "" {
		req.APIVersion = model.APIVersion
	}
	s, e := c.State(ctx)
	if e != nil {
		return e
	}
	if w := s.Workloads[req.Name]; w != nil && req.ExpectedGeneration == 0 {
		req.ExpectedGeneration = w.Generation
	}
	var receipt model.Receipt
	key := model.ID()
	if e = c.Call(ctx, "POST", "/v1/workloads", req, &receipt, key); e != nil {
		return fmt.Errorf("%w; requestId=%s (bei unklarem Ausgang erst status prüfen)", e, key)
	}
	fmt.Printf("Angenommen: %s · Revision %d · Request %s\n", req.Name, receipt.Generation, receipt.ID)
	return nil
}
func applyCommand(ctx context.Context, args []string) error {
	if len(args) != 1 {
		return errors.New("apply DATEI.json")
	}
	req, e := readManifest(args[0])
	if e != nil {
		return e
	}
	c, e := client()
	if e != nil {
		return e
	}
	return apply(ctx, c, req)
}
func scaleCommand(ctx context.Context, args []string) error {
	if len(args) != 2 {
		return errors.New("scale NAME ANZAHL")
	}
	n, e := strconv.Atoi(args[1])
	if e != nil {
		return e
	}
	c, e := client()
	if e != nil {
		return e
	}
	s, e := c.State(ctx)
	if e != nil {
		return e
	}
	w := s.Workloads[args[0]]
	if w == nil {
		return model.ErrNotFound
	}
	spec := w.Spec
	spec.Replicas = n
	return apply(ctx, c, model.ApplyRequest{APIVersion: model.APIVersion, Name: w.Name, ExpectedGeneration: w.Generation, Spec: spec})
}
func mutateCommand(ctx context.Context, kind string, args []string) error {
	if len(args) != 1 || !model.ValidName(args[0]) {
		return errors.New(kind + " NAME")
	}
	c, e := client()
	if e != nil {
		return e
	}
	s, e := c.State(ctx)
	if e != nil {
		return e
	}
	w := s.Workloads[args[0]]
	if w == nil {
		return model.ErrNotFound
	}
	var receipt model.Receipt
	e = c.Call(ctx, "POST", "/v1/workloads/"+w.Name+"/"+kind, model.MutationRequest{ExpectedGeneration: w.Generation}, &receipt, model.ID())
	if e == nil {
		fmt.Printf("%s angenommen für %s. Fortschritt: werft status\n", kind, w.Name)
	}
	return e
}
func Wait(ctx context.Context, c *apiclient.Client, name string, duration time.Duration) error {
	if !model.ValidName(name) || duration <= 0 || duration > 30*time.Minute {
		return errors.New("WAIT_ARGUMENT_INVALID")
	}
	timeout, cancel := context.WithTimeout(ctx, duration)
	defer cancel()
	t := time.NewTicker(time.Second)
	defer t.Stop()
	reason := "not-observed"
	for {
		s, e := c.State(timeout)
		if e == nil {
			w := s.Workloads[name]
			if w == nil {
				return model.ErrNotFound
			}
			reason = w.Phase + " " + w.Reason
			if w.Phase == "ready" {
				fmt.Printf("Bereit: %s (vom Agenten beobachtet)\n", name)
				return nil
			}
		}
		select {
		case <-timeout.Done():
			return fmt.Errorf("WAIT_TIMEOUT: %s", reason)
		case <-t.C:
		}
	}
}
func Endpoints(s *model.State, name string) []string {
	out := []string{}
	w := s.Workloads[name]
	if w == nil {
		return out
	}
	for _, id := range model.SortedKeys(s.Allocations) {
		a := s.Allocations[id]
		n := s.Nodes[a.NodeID]
		if a.WorkloadUID == w.UID && a.Desired == "run" && a.Phase == "ready" && a.HostPort > 0 && n != nil && n.Ready(time.Now()) {
			out = append(out, "http://"+net.JoinHostPort(n.Address, strconv.Itoa(a.HostPort)))
		}
	}
	return out
}
func endpointsCommand(ctx context.Context, args []string) error {
	if len(args) != 1 {
		return errors.New("endpoints NAME")
	}
	c, e := client()
	if e != nil {
		return e
	}
	s, e := c.State(ctx)
	if e != nil {
		return e
	}
	eps := Endpoints(s, args[0])
	if len(eps) == 0 {
		return errors.New("NO_READY_HTTP_ENDPOINT")
	}
	for _, u := range eps {
		fmt.Println(u)
	}
	return nil
}
func tunnelCommand(ctx context.Context, args []string) error {
	if len(args) == 0 || !model.ValidName(args[0]) {
		return errors.New("tunnel NAME [--listen 127.0.0.1:8088]")
	}
	name := args[0]
	f := parser("tunnel")
	listen := f.String("listen", "127.0.0.1:8088", "Loopback")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	host, _, e := net.SplitHostPort(*listen)
	if e != nil || host != "127.0.0.1" {
		return errors.New("TUNNEL_LOOPBACK_REQUIRED")
	}
	c, e := client()
	if e != nil {
		return e
	}
	var next atomic.Uint64
	h := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Host != *listen {
			http.Error(w, "HOST_NOT_ALLOWED", 403)
			return
		}
		s, e := c.State(r.Context())
		if e != nil {
			http.Error(w, "CONTROL_PLANE_UNAVAILABLE", 503)
			return
		}
		eps := Endpoints(s, name)
		if len(eps) == 0 {
			http.Error(w, "NO_READY_ENDPOINT", 503)
			return
		}
		target, _ := url.Parse(eps[int(next.Add(1)-1)%len(eps)])
		proxy := httputil.NewSingleHostReverseProxy(target)
		original := proxy.Director
		proxy.Director = func(r *http.Request) {
			original(r)
			r.Host = target.Host
			r.Header.Del("Cookie")
			r.Header.Del("Authorization")
			r.Header.Del("Forwarded")
		}
		proxy.ModifyResponse = func(r *http.Response) error { r.Header.Del("Set-Cookie"); return nil }
		proxy.ServeHTTP(w, r)
	})
	srv := &http.Server{Addr: *listen, Handler: h, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 30 * time.Second, WriteTimeout: 30 * time.Second}
	go func() {
		<-ctx.Done()
		stop, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		srv.Shutdown(stop)
	}()
	fmt.Printf("Anwendungs-Tunnel (getrennt vom Admin-Ursprung): http://%s\n", *listen)
	e = srv.ListenAndServe()
	if e == http.ErrServerClosed {
		return nil
	}
	return e
}
func nodeCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("node bundle|drain|uncordon|revoke")
	}
	if args[0] == "bundle" {
		f := parser("node bundle")
		name := f.String("name", "", "Node name")
		address := f.String("address", "", "Private IP")
		out := f.String("out", "", "Datei")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		if *out == "" {
			return errors.New("--out required")
		}
		return setup.CreateBundle(ctx, *name, *address, *out)
	}
	if len(args) != 2 {
		return errors.New("node drain|uncordon|revoke NAME")
	}
	c, e := client()
	if e != nil {
		return e
	}
	s, e := c.State(ctx)
	if e != nil {
		return e
	}
	id := ""
	for _, n := range s.Nodes {
		if n.Name == args[1] || n.ID == args[1] {
			id = n.ID
			break
		}
	}
	if id == "" {
		return model.ErrNotFound
	}
	body := map[string]bool{}
	switch args[0] {
	case "drain":
		body["drain"] = true
	case "uncordon":
		body["drain"] = false
	case "revoke":
		body["revoked"] = true
	default:
		return errors.New("NODE_ACTION_UNKNOWN")
	}
	if e = c.Call(ctx, "POST", "/v1/nodes/"+id, body, nil, ""); e != nil {
		return e
	}
	fmt.Println("Node-Policy aktualisiert. Drain kann auf Reservekapazität warten. Revocation stoppt KEINE bereits laufenden Container.")
	return nil
}
func demoCommand(ctx context.Context, args []string) error {
	f := parser("demo")
	replicas := f.Int("replicas", 2, "Replicas")
	wait := f.Bool("wait", false, "Warten")
	if e := f.Parse(args); e != nil {
		return e
	}
	m, e := config.Load[DemoMetadata]("/usr/share/werftkern/demo.json")
	if e != nil {
		return e
	}
	c, e := client()
	if e != nil {
		return e
	}
	req := model.ApplyRequest{APIVersion: model.APIVersion, Name: "demo", Spec: model.Spec{Image: m.Image, Replicas: *replicas, CPUMilli: 100, MemoryMiB: 32, Port: 8080, ReadinessPath: "/healthz"}}
	if e = apply(ctx, c, req); e != nil {
		return e
	}
	if *wait {
		return Wait(ctx, c, "demo", 120*time.Second)
	}
	return nil
}
func doctor(ctx context.Context) error {
	fmt.Printf("Plattform: %s/%s; Compiler: %s\n", runtime.GOOS, runtime.GOARCH, runtime.Version())
	if e := setup.Preflight(); e != nil {
		fmt.Printf("Host-Preflight: %s\n", e)
	} else {
		fmt.Println("Host-Preflight: erfüllt (kein Ersatz für einen VM-E2E-Test)")
	}
	c, e := config.Load[config.Client](config.AdminPath())
	if e != nil {
		return e
	}
	b, e := os.ReadFile(c.Cert)
	if e != nil {
		return e
	}
	block, _ := pem.Decode(b)
	if block == nil {
		return errors.New("CERTIFICATE_INVALID")
	}
	cert, e := x509.ParseCertificate(block.Bytes)
	if e != nil {
		return e
	}
	fmt.Printf("Admin-Zertifikat gültig bis: %s\n", cert.NotAfter.Format(time.RFC3339))
	if time.Until(cert.NotAfter) < 30*24*time.Hour {
		fmt.Println("WARNUNG: Zertifikatserneuerung planen; automatische Rotation ist noch nicht implementiert.")
	}
	api, e := apiclient.New(c)
	if e != nil {
		return e
	}
	s, e := api.State(ctx)
	if e != nil {
		return e
	}
	fmt.Printf("mTLS und persistenter Cluster-State erreichbar: %s\n", s.Name)
	return nil
}
func logsCommand(ctx context.Context, args []string) error {
	if len(args) != 1 || !model.ValidID(args[0]) {
		return errors.New("logs ALLOCATION_ID — auf dem zugewiesenen Worker ausführen")
	}
	c, e := config.Load[config.Agent](config.Directory + "/agent.json")
	if e != nil {
		return e
	}
	d := engine.NewDocker(c.Socket, c.Client.ClusterID)
	b, e := d.Logs(ctx, args[0])
	if e != nil {
		return e
	}
	for len(b) >= 8 {
		n := int(binary.BigEndian.Uint32(b[4:8]))
		b = b[8:]
		if n < 0 || n > len(b) {
			break
		}
		for _, c := range string(b[:n]) {
			if c == '\n' || c == '\t' || c >= 32 && c != 127 {
				fmt.Printf("%c", c)
			}
		}
		b = b[n:]
	}
	return nil
}
