// Package setup owns explicit host installation. No setup runs from package
// maintainer scripts; no network command is piped into a privileged shell.
package setup

import (
	"context"
	"errors"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/apiclient"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/store"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
	"net"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"
)

type Progress struct {
	Role      string `json:"role"`
	ClusterID string `json:"clusterId"`
	Name      string `json:"name"`
	Address   string `json:"address"`
	NodeID    string `json:"nodeId"`
	Stage     string `json:"stage"`
	Worker    bool   `json:"worker"`
}

const progressPath = config.Directory + "/setup.json"

func RequireRoot() error {
	if os.Geteuid() != 0 {
		return errors.New("Bitte mit sudo ausführen.")
	}
	return nil
}
func Preflight() error {
	if e := RequireRoot(); e != nil {
		return e
	}
	b, e := os.ReadFile("/etc/os-release")
	if e != nil {
		return e
	}
	m := map[string]string{}
	for _, l := range strings.Split(string(b), "\n") {
		if k, v, ok := strings.Cut(l, "="); ok {
			m[k] = strings.Trim(v, "\"")
		}
	}
	if m["ID"] != "ubuntu" || m["VERSION_ID"] != "24.04" || runtime.GOARCH != "amd64" {
		return errors.New("Dieses Alpha-Paket zielt auf Ubuntu 24.04 LTS amd64. Andere Systeme werden nicht automatisch verändert.")
	}
	if _, e = os.Stat("/run/systemd/system"); e != nil {
		return errors.New("SYSTEMD_HOST_REQUIRED; keine Installation in einem normalen Container")
	}
	if _, e = os.Stat("/sys/fs/cgroup/cgroup.controllers"); e != nil {
		return errors.New("CGROUP_V2_REQUIRED")
	}
	for _, c := range []string{"systemctl", "etcd", "docker"} {
		if _, e := exec.LookPath(c); e != nil {
			return fmt.Errorf("DEPENDENCY_MISSING: %s; zuerst das .deb mit apt installieren", c)
		}
	}
	if _, e = user.Lookup("wk-runtime"); e != nil {
		return errors.New("PACKAGE_SERVICE_USER_MISSING")
	}
	return nil
}
func SuggestedIP() string {
	ifs, _ := net.Interfaces()
	for _, i := range ifs {
		if i.Flags&net.FlagUp == 0 || i.Flags&net.FlagLoopback != 0 {
			continue
		}
		as, _ := i.Addrs()
		for _, a := range as {
			ip, _, e := net.ParseCIDR(a.String())
			if e == nil && ip.To4() != nil && ip.IsPrivate() {
				return ip.String()
			}
		}
	}
	return "127.0.0.1"
}
func LocalAddress(address string) bool {
	if !model.PrivateAddress(address) {
		return false
	}
	as, _ := net.InterfaceAddrs()
	for _, a := range as {
		ip, _, e := net.ParseCIDR(a.String())
		if e == nil && ip.Equal(net.ParseIP(address)) {
			return true
		}
	}
	return false
}
func command(ctx context.Context, name string, args ...string) error {
	c := exec.CommandContext(ctx, name, args...)
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	c.Stdin = nil
	return c.Run()
}
func owned(path string, service bool) error {
	if !service {
		return nil
	}
	u, e := user.Lookup("wk-runtime")
	if e != nil {
		return e
	}
	uid, e := strconv.Atoi(u.Uid)
	if e != nil {
		return e
	}
	gid, e := strconv.Atoi(u.Gid)
	if e != nil {
		return e
	}
	return os.Chown(path, uid, gid)
}
func write(path string, b []byte, service bool) error {
	if e := safefile.Write(path, b, 0600); e != nil {
		return e
	}
	return owned(path, service)
}
func jsonFile(path string, v any, service bool) error {
	if e := safefile.JSON(path, v, 0600); e != nil {
		return e
	}
	return owned(path, service)
}
func pairFiles(dir string, p pki.Pair, service bool) error {
	if e := os.MkdirAll(dir, 0700); e != nil {
		return e
	}
	if e := owned(dir, service); e != nil {
		return e
	}
	if e := write(filepath.Join(dir, "client.crt"), p.Cert, service); e != nil {
		return e
	}
	return write(filepath.Join(dir, "client.key"), p.Key, service)
}
func material(p Progress) error {
	// This function is only called before setup.json exists. Persisted installations
	// are resumed, never silently assigned a fresh cluster identity or CA.
	if e := os.MkdirAll(config.Directory, 0750); e != nil {
		return e
	}
	u, e := user.Lookup("wk-runtime")
	if e != nil {
		return e
	}
	gid, _ := strconv.Atoi(u.Gid)
	if e = os.Chown(config.Directory, 0, gid); e != nil {
		return e
	}
	if e = os.Chmod(config.Directory, 0750); e != nil {
		return e
	}
	now := time.Now().UTC()
	ca, e := pki.CA("Werftkern "+p.ClusterID, now)
	if e != nil {
		return e
	}
	if e = pairFiles(config.Directory+"/authority", ca, false); e != nil {
		return e
	}
	server, e := pki.Issue(ca, "server", p.ClusterID, []string{p.Address, "127.0.0.1", "localhost"}, true, now)
	if e != nil {
		return e
	}
	if e = pairFiles(config.Directory+"/control-pki", server, true); e != nil {
		return e
	}
	if e = write(config.Directory+"/control-pki/ca.crt", ca.Cert, true); e != nil {
		return e
	}
	admin, e := pki.Issue(ca, "admin", p.ClusterID, nil, false, now)
	if e != nil {
		return e
	}
	if e = pairFiles(config.Directory+"/admin-pki", admin, false); e != nil {
		return e
	}
	if e = write(config.Directory+"/admin-pki/ca.crt", ca.Cert, false); e != nil {
		return e
	}
	url := "https://" + net.JoinHostPort(p.Address, "7443")
	ac := config.Client{Server: url, CA: config.Directory + "/admin-pki/ca.crt", Cert: config.Directory + "/admin-pki/client.crt", Key: config.Directory + "/admin-pki/client.key", ClusterID: p.ClusterID}
	if e = jsonFile(config.Directory+"/admin.json", ac, false); e != nil {
		return e
	}
	// A separate CA and identity protect the loopback etcd endpoint. Loopback alone
	// would still allow unprivileged local users to modify the database.
	eca, e := pki.CA("ClusterPilot etcd "+p.ClusterID, now)
	if e != nil {
		return e
	}
	if e = pairFiles(config.Directory+"/etcd-authority", eca, false); e != nil {
		return e
	}
	es, e := pki.Issue(eca, "etcd-server", p.ClusterID, []string{"127.0.0.1", "localhost"}, true, now)
	if e != nil {
		return e
	}
	if e = pairFiles(config.Directory+"/etcd-pki", es, true); e != nil {
		return e
	}
	if e = write(config.Directory+"/etcd-pki/ca.crt", eca.Cert, true); e != nil {
		return e
	}
	ec, e := pki.Issue(eca, "etcd-client", p.ClusterID, nil, false, now)
	if e != nil {
		return e
	}
	if e = pairFiles(config.Directory+"/etcd-client-pki", ec, true); e != nil {
		return e
	}
	if e = write(config.Directory+"/etcd-client-pki/ca.crt", eca.Cert, true); e != nil {
		return e
	}
	controlClient := config.Client{Server: url, CA: config.Directory + "/control-pki/ca.crt", Cert: config.Directory + "/control-pki/client.crt", Key: config.Directory + "/control-pki/client.key", ClusterID: p.ClusterID}
	etcdClient := config.Client{Server: "https://127.0.0.1:23791", CA: config.Directory + "/etcd-client-pki/ca.crt", Cert: config.Directory + "/etcd-client-pki/client.crt", Key: config.Directory + "/etcd-client-pki/client.key", ClusterID: p.ClusterID}
	cc := config.Control{Client: controlClient, Listen: net.JoinHostPort(p.Address, "7443"), Etcd: etcdClient, DataDir: config.Data + "/control", VaultKey: config.Data + "/control/vault.key"}
	if e = jsonFile(config.Directory+"/control.json", cc, true); e != nil {
		return e
	}
	for _, dir := range []string{config.Data + "/control", config.Data + "/etcd"} {
		if e = os.MkdirAll(dir, 0700); e != nil {
			return e
		}
		if e = owned(dir, true); e != nil {
			return e
		}
	}
	if _, e = vault.CreateKey(cc.VaultKey); e != nil {
		return e
	}
	if e = owned(cc.VaultKey, true); e != nil {
		return e
	}
	if p.Worker {
		agentPair, e := pki.Issue(ca, "node:"+p.NodeID, p.ClusterID, nil, false, now)
		if e != nil {
			return e
		}
		if e = saveAgent(ac.Server, p.ClusterID, p.NodeID, p.Address, ca.Cert, agentPair); e != nil {
			return e
		}
	}
	return nil
}
func saveAgent(server, cluster, id, address string, ca []byte, pair pki.Pair) error {
	dir := config.Directory + "/agent-pki"
	if e := pairFiles(dir, pair, false); e != nil {
		return e
	}
	if e := write(dir+"/ca.crt", ca, false); e != nil {
		return e
	}
	c := config.Agent{Client: config.Client{Server: server, ClusterID: cluster, CA: dir + "/ca.crt", Cert: dir + "/client.crt", Key: dir + "/client.key"}, NodeID: id, InstanceID: model.ID(), Address: address, Journal: config.Data + "/agent/journal.json", Socket: "/var/run/docker.sock", DemoArchive: "/usr/share/werftkern/demo-image.tar"}
	if e := os.MkdirAll(config.Data+"/agent", 0700); e != nil {
		return e
	}
	return jsonFile(config.Directory+"/agent.json", c, false)
}
func Init(ctx context.Context, name, address string, worker bool) error {
	if e := Preflight(); e != nil {
		return e
	}
	if _, e := os.Stat(progressPath); e == nil {
		return Resume(ctx)
	}
	if !model.ValidName(name) || !LocalAddress(address) {
		return errors.New("VALID_NAME_AND_LOCAL_PRIVATE_IPV4_REQUIRED")
	}
	// Refuse unexplained partial material: recovering it requires inspection, not a
	// new CA. No existing host installation is ever overwritten by initialization.
	if _, e := os.Stat(config.Directory + "/authority"); e == nil {
		return errors.New("PARTIAL_INSTALLATION_MATERIAL_PRESENT; inspect before recovery")
	}
	p := Progress{Role: "controller", ClusterID: model.ID(), Name: name, Address: address, NodeID: model.ID(), Stage: "configured", Worker: worker}
	if e := material(p); e != nil {
		return e
	}
	if e := safefile.JSON(progressPath, p, 0600); e != nil {
		return e
	}
	return Resume(ctx)
}
func Resume(ctx context.Context) error {
	if e := Preflight(); e != nil {
		return e
	}
	p, e := config.Load[Progress](progressPath)
	if e != nil {
		return e
	}
	if p.Role == "worker" {
		if e = command(ctx, "systemctl", "enable", "--now", "docker.service", "werftkern-agent.service"); e != nil {
			return e
		}
		return waitNode(ctx, p, false)
	}
	cc, e := config.Load[config.Control](config.Directory + "/control.json")
	if e != nil {
		return e
	}
	if e = command(ctx, "systemctl", "daemon-reload"); e != nil {
		return e
	}
	if e = command(ctx, "systemctl", "enable", "--now", "werftkern-etcd.service"); e != nil {
		return e
	}
	client, e := pki.ClientFiles(cc.Etcd.CA, cc.Etcd.Cert, cc.Etcd.Key)
	if e != nil {
		return e
	}
	db := store.NewEtcd(cc.Etcd.Server, client, p.ClusterID)
	fmt.Println("Prüfe persistente Zustandsablage …")
	deadline := time.Now().Add(60 * time.Second)
	for {
		_, _, e = db.Read(ctx)
		if e == nil || errors.Is(e, store.ErrUninitialized) {
			break
		}
		if time.Now().After(deadline) {
			return e
		}
		if e = sleep(ctx, time.Second); e != nil {
			return e
		}
	}
	if errors.Is(e, store.ErrUninitialized) {
		if p.Stage != "configured" {
			return errors.New("PERSISTED_STATE_MISSING; refusing to recreate an existing cluster")
		}
		if e = db.Initialize(ctx, model.NewState(p.ClusterID, p.Name, time.Now().UTC())); e != nil {
			return e
		}
	}
	p.Stage = "seeded"
	if e = safefile.JSON(progressPath, p, 0600); e != nil {
		return e
	}
	if e = command(ctx, "systemctl", "enable", "--now", "werftkern-control.service"); e != nil {
		return e
	}
	adminCfg, e := config.Load[config.Client](config.Directory + "/admin.json")
	if e != nil {
		return e
	}
	api, e := apiclient.New(adminCfg)
	if e != nil {
		return e
	}
	fmt.Println("Prüfe verschlüsselte Control-Plane-Verbindung …")
	deadline = time.Now().Add(60 * time.Second)
	for {
		if _, e = api.State(ctx); e == nil {
			break
		}
		if time.Now().After(deadline) {
			return e
		}
		if e = sleep(ctx, time.Second); e != nil {
			return e
		}
	}
	if p.Worker {
		if e = api.Call(ctx, "POST", "/v1/nodes", control.NodeRegistration{ID: p.NodeID, Name: "node-1", Address: p.Address}, nil, ""); e != nil {
			return e
		}
		if e = command(ctx, "systemctl", "enable", "--now", "docker.service", "werftkern-agent.service"); e != nil {
			return e
		}
		if e = waitNode(ctx, p, true); e != nil {
			return e
		}
	}
	p.Stage = "complete"
	if e = safefile.JSON(progressPath, p, 0600); e != nil {
		return e
	}
	fmt.Println("Cluster eingerichtet. Anwendungstest: sudo werft demo --wait\nStatus: sudo werft status\nLokale Oberfläche: sudo werft dashboard")
	return nil
}
func sleep(ctx context.Context, d time.Duration) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(d):
		return nil
	}
}
func waitNode(ctx context.Context, p Progress, admin bool) error {
	path := config.Directory + "/agent.json"
	var c config.Client
	if admin {
		var e error
		c, e = config.Load[config.Client](config.Directory + "/admin.json")
		if e != nil {
			return e
		}
	} else {
		ag, e := config.Load[config.Agent](path)
		if e != nil {
			return e
		}
		c = ag.Client
	}
	api, e := apiclient.New(c)
	if e != nil {
		return e
	}
	deadline := time.Now().Add(60 * time.Second)
	for {
		if admin {
			s, err := api.State(ctx)
			if err == nil {
				n := s.Nodes[p.NodeID]
				if n != nil && n.Ready(time.Now()) {
					fmt.Println("Node hat sich authentifiziert und ist bereit.")
					return nil
				}
			}
		} else {
			j := struct {
				ClusterID   string                      `json:"clusterId"`
				Revision    int64                       `json:"revision"`
				Allocations map[string]model.Allocation `json:"allocations"`
			}{}
			if err := safefile.ReadJSON(config.Data+"/agent/journal.json", &j); err == nil && j.ClusterID == p.ClusterID && j.Revision > 0 {
				fmt.Println("Worker hat einen authentifizierten Cluster-Snapshot empfangen.")
				return nil
			}
		}
		if time.Now().After(deadline) {
			return errors.New("NODE_NOT_READY: journalctl -u werftkern-agent; setup kann wiederholt werden")
		}
		if e = sleep(ctx, time.Second); e != nil {
			return e
		}
	}
}

type Bundle struct {
	Servers    []string  `json:"servers,omitempty"`
	APIVersion string    `json:"apiVersion"`
	Server     string    `json:"server"`
	ClusterID  string    `json:"clusterId"`
	NodeID     string    `json:"nodeId"`
	NodeName   string    `json:"nodeName"`
	Address    string    `json:"address"`
	CA         []byte    `json:"ca"`
	Identity   pki.Pair  `json:"identity"`
	ExpiresAt  time.Time `json:"expiresAt"`
}

func CreateBundle(ctx context.Context, name, address, out string) error {
	if e := RequireRoot(); e != nil {
		return e
	}
	if !model.ValidName(name) || !model.PrivateAddress(address) || net.ParseIP(address).IsLoopback() {
		return errors.New("WORKER_NAME_AND_PRIVATE_IPV4_REQUIRED")
	}
	if _, e := os.Stat(out); !os.IsNotExist(e) {
		return errors.New("OUTPUT_FILE_ALREADY_EXISTS")
	}
	c, e := config.Load[config.Client](config.AdminPath())
	if e != nil {
		return e
	}
	api, e := apiclient.New(c)
	if e != nil {
		return e
	}
	caCert, e := os.ReadFile(config.Directory + "/authority/client.crt")
	if e != nil {
		return e
	}
	caKey, e := os.ReadFile(config.Directory + "/authority/client.key")
	if e != nil {
		return e
	}
	id := model.ID()
	cert, e := pki.Issue(pki.Pair{Cert: caCert, Key: caKey}, "node:"+id, c.ClusterID, nil, false, time.Now())
	if e != nil {
		return e
	}
	b := Bundle{Servers: c.Servers, APIVersion: model.APIVersion, Server: c.Server, ClusterID: c.ClusterID, NodeID: id, NodeName: name, Address: address, CA: caCert, Identity: cert, ExpiresAt: time.Now().Add(24 * time.Hour)}
	if e = api.Call(ctx, "POST", "/v1/nodes", control.NodeRegistration{ID: id, Name: name, Address: address}, nil, ""); e != nil {
		return e
	}
	if e = safefile.JSON(out, b, 0600); e != nil {
		return e
	}
	fmt.Printf("Beitrittsdatei geschrieben: %s\nEnthält einen privaten Node-Schlüssel. Über einen sicheren Kanal übertragen.\nAuf Worker: sudo werft setup --join /pfad/zur/datei\n", out)
	return nil
}
func Join(ctx context.Context, path string) error {
	if e := Preflight(); e != nil {
		return e
	}
	if _, e := os.Stat(progressPath); e == nil {
		return errors.New("HOST_ALREADY_CONFIGURED; use werft setup to resume, never overwrite identity")
	}
	stat, e := os.Stat(path)
	if e != nil {
		return e
	}
	if stat.Mode().Perm()&0077 != 0 {
		return errors.New("JOIN_FILE_MUST_HAVE_MODE_0600")
	}
	if stat.Size() > 32768 {
		return errors.New("JOIN_FILE_TOO_LARGE")
	}
	b, e := config.Load[Bundle](path)
	if e != nil {
		return e
	}
	if b.APIVersion != model.APIVersion || !model.ValidID(b.ClusterID) || !model.ValidID(b.NodeID) || !model.ValidName(b.NodeName) || !LocalAddress(b.Address) || !time.Now().Before(b.ExpiresAt) {
		return errors.New("JOIN_BUNDLE_INVALID_OR_EXPIRED")
	}
	if e = pki.ValidateIdentity(b.CA, b.Identity, "node:"+b.NodeID, b.ClusterID); e != nil {
		return e
	}
	if e = config.ValidateClient(config.Client{Server: b.Server, ClusterID: b.ClusterID}); e != nil {
		return e
	}
	// Verify remote ownership before persisting a new local installation.
	httpClient, e := pki.Client(b.CA, b.Identity)
	if e != nil {
		return e
	}
	c := apiclient.Client{HTTP: httpClient, Base: b.Server, ClusterID: b.ClusterID}
	var health struct {
		ClusterID string `json:"clusterId"`
	}
	if e = c.Call(ctx, "GET", "/v1/health", nil, &health, ""); e != nil {
		return e
	}
	if health.ClusterID != b.ClusterID {
		return errors.New("JOIN_CLUSTER_ID_MISMATCH")
	}
	if e = saveAgent(b.Server, b.ClusterID, b.NodeID, b.Address, b.CA, b.Identity); e != nil {
		return e
	}
	ag, err := config.Load[config.Agent](config.Directory + "/agent.json")
	if err != nil {
		return err
	}
	ag.Client.Servers = b.Servers
	if err = safefile.JSON(config.Directory+"/agent.json", ag, 0600); err != nil {
		return err
	}
	p := Progress{Role: "worker", ClusterID: b.ClusterID, Name: b.NodeName, Address: b.Address, NodeID: b.NodeID, Stage: "configured", Worker: true}
	if e = safefile.JSON(progressPath, p, 0600); e != nil {
		return e
	}
	return Resume(ctx)
}
