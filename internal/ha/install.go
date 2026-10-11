package ha

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/failover"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/pki"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
	"github.com/ClusterPilot-System/werftkern/internal/setup"
	"github.com/ClusterPilot-System/werftkern/internal/store"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"strconv"
	"strings"
)

// WriteKits refuses existing output. These archives contain keys: never commit them.
func WriteKits(dir string, kits []Kit) error {
	if _, e := os.Lstat(dir); !os.IsNotExist(e) {
		return errors.New("OUTPUT_DIRECTORY_MUST_NOT_EXIST")
	}
	if e := os.Mkdir(dir, 0700); e != nil {
		return e
	}
	for _, k := range kits {
		if e := ValidateKit(k); e != nil {
			return e
		}
		if e := safefile.JSON(filepath.Join(dir, k.Host.Name+".kit.json"), k, 0600); e != nil {
			return e
		}
	}
	return nil
}
func run(ctx context.Context, args ...string) error {
	c := exec.CommandContext(ctx, args[0], args[1:]...)
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	return c.Run()
}
func Install(ctx context.Context, path, confirm string) error {
	if e := setup.Preflight(); e != nil {
		return e
	}
	st, e := os.Lstat(path)
	if e != nil {
		return e
	}
	if !st.Mode().IsRegular() || st.Mode().Perm()&0077 != 0 {
		return errors.New("KIT_MUST_BE_A_PRIVATE_REGULAR_FILE")
	}
	var k Kit
	if e = safefile.ReadJSON(path, &k); e != nil {
		return e
	}
	if e = ValidateKit(k); e != nil {
		return e
	}
	if confirm != k.Host.Name || !setup.LocalAddress(k.Host.Address) {
		return errors.New("HOST_NAME_CONFIRMATION_AND_LOCAL_ADDRESS_REQUIRED")
	}
	// Never import over another cluster or overwrite an interrupted installation.
	entries, e := os.ReadDir(config.Directory)
	if e != nil && !os.IsNotExist(e) {
		return e
	}
	if len(entries) != 0 {
		return errors.New("CONFIGURATION_EXISTS_INSPECT_BEFORE_RETRY")
	}
	for _, p := range []string{config.Data + "/etcd/member", config.Data + "/agent/journal.json"} {
		if _, e := os.Lstat(p); !os.IsNotExist(e) {
			return errors.New("EXISTING_CLUSTER_DATA_BLOCKS_INITIAL_INSTALL")
		}
	}
	u, e := user.Lookup("wk-runtime")
	if e != nil {
		return e
	}
	uid, _ := strconv.Atoi(u.Uid)
	gid, _ := strconv.Atoi(u.Gid)
	if e = os.MkdirAll(config.Directory, 0750); e != nil {
		return e
	}
	if e = os.Chown(config.Directory, 0, gid); e != nil {
		return e
	}
	if e = os.Chmod(config.Directory, 0750); e != nil {
		return e
	}
	// Explicit incomplete marker keeps partially copied trust material from being reused.
	if e = safefile.JSON(config.Directory+"/ha-installing.json", map[string]string{"clusterId": k.ClusterID, "host": k.Host.Name}, 0600); e != nil {
		return e
	}
	for _, name := range model.SortedKeys(k.Files) {
		full := filepath.Join(config.Directory, name)
		if e = safefile.Write(full, k.Files[name], 0600); e != nil {
			return e
		}
		service := strings.HasPrefix(name, "control-pki/") || strings.HasPrefix(name, "etcd-pki/") || strings.HasPrefix(name, "etcd-client-pki/") || name == "control.json"
		if service {
			if e = os.Chown(full, uid, gid); e != nil {
				return e
			}
			if filepath.Dir(full) != config.Directory {
				if e = os.Chown(filepath.Dir(full), uid, gid); e != nil {
					return e
				}
			}
		}
	}
	for _, d := range []string{"etcd", "control", "agent", "volumes", "dns"} {
		p := config.Data + "/" + d
		if e = os.MkdirAll(p, 0700); e != nil {
			return e
		}
		if d == "etcd" || d == "control" {
			if e = os.Chown(p, uid, gid); e != nil {
				return e
			}
		}
	}
	if k.Host.Controller {
		b, e := EtcdConfig(k)
		if e != nil {
			return e
		}
		p := config.Directory + "/etcd-ha.yaml"
		if e = safefile.Write(p, b, 0600); e != nil {
			return e
		}
		if e = os.Chown(p, uid, gid); e != nil {
			return e
		}
		override := "[Service]\nExecStart=\nExecStart=/usr/bin/etcd --config-file=/etc/werftkern/etcd-ha.yaml\n"
		if e = safefile.Write("/etc/systemd/system/werftkern-etcd.service.d/ha.conf", []byte(override), 0644); e != nil {
			return e
		}
	}
	if k.Seed != nil {
		if e = safefile.JSON(config.Directory+"/ha-seed.json", k.Seed, 0600); e != nil {
			return e
		}
	}
	if e = safefile.JSON(config.Directory+"/ha-host.json", map[string]any{"clusterId": k.ClusterID, "host": k.Host}, 0600); e != nil {
		return e
	}
	if e = run(ctx, "systemctl", "daemon-reload"); e != nil {
		return e
	}
	if k.Host.Controller {
		if e = run(ctx, "systemctl", "enable", "--now", "werftkern-etcd.service"); e != nil {
			return e
		}
		if e = run(ctx, "systemctl", "enable", "--now", "werftkern-control.service"); e != nil {
			return e
		}
	}
	if k.Host.Worker {
		if e = run(ctx, "systemctl", "enable", "--now", "werftkern-agent.service"); e != nil {
			return e
		}
	}
	if e = os.Remove(config.Directory + "/ha-installing.json"); e != nil {
		return e
	}
	fmt.Println("HA host staged. Install all three controllers, then run werft ha init on the seed controller. No readiness is asserted by this message.")
	return nil
}
func Initialize(ctx context.Context) error {
	if e := setup.RequireRoot(); e != nil {
		return e
	}
	if _, e := os.Stat(config.Directory + "/ha-installing.json"); !os.IsNotExist(e) {
		return errors.New("HA_INSTALLATION_INCOMPLETE")
	}
	var seed model.State
	if e := safefile.ReadJSON(config.Directory+"/ha-seed.json", &seed); e != nil {
		return e
	}
	var cc config.Control
	if e := safefile.ReadJSON(config.Directory+"/control.json", &cc); e != nil {
		return e
	}
	if seed.ClusterID != cc.Client.ClusterID {
		return errors.New("SEED_CLUSTER_MISMATCH")
	}
	c, e := pki.ClientFiles(cc.Etcd.CA, cc.Etcd.Cert, cc.Etcd.Key)
	if e != nil {
		return e
	}
	tr, e := failover.New(c.Transport, cc.Etcd.Servers)
	if e != nil {
		return e
	}
	c.Transport = tr
	db := store.NewEtcd(cc.Etcd.Server, c, seed.ClusterID)
	if _, _, e = db.Read(ctx); e == nil {
		if e = safefile.JSON(config.Directory+"/ha-initialized.json", map[string]string{"clusterId": seed.ClusterID}, 0600); e != nil {
			return e
		}
		fmt.Println("State already initialized; not overwritten.")
		return nil
	} else if !errors.Is(e, store.ErrUninitialized) {
		return e
	}
	// A missing key after previous initialization is data loss, NOT first installation.
	if _, e := os.Stat(config.Directory + "/ha-initialized.json"); !os.IsNotExist(e) {
		return errors.New("STATE_LOST_RECOVERY_REQUIRED")
	}
	if _, e := os.Stat(config.Directory + "/ha-init-attempt.json"); !os.IsNotExist(e) {
		return errors.New("INITIALIZATION_OUTCOME_UNKNOWN_REVIEW_REQUIRED")
	}
	if e = safefile.JSON(config.Directory+"/ha-init-attempt.json", map[string]string{"clusterId": seed.ClusterID}, 0600); e != nil {
		return e
	}
	if e = db.Initialize(ctx, &seed); e != nil {
		return e
	}
	if e = safefile.JSON(config.Directory+"/ha-initialized.json", map[string]string{"clusterId": seed.ClusterID}, 0600); e != nil {
		return e
	}
	fmt.Println("Initial state committed by etcd. Verify every controller and worker with werft status.")
	return nil
}

// Configuration paths are fixed; input kits are NOT arbitrary host file writers.
func validateConfigurations(k Kit) error {
	required := []string{}
	if k.Host.Controller {
		required = append(required, "control.json", "admin.json", "control-pki/vault.key", "etcd-pki/client.crt", "etcd-pki/client.key", "etcd-pki/ca.crt")
	}
	if k.Host.Worker {
		required = append(required, "agent.json")
	}
	for _, r := range required {
		if len(k.Files[r]) == 0 {
			return errors.New("KIT_REQUIRED_FILE_MISSING")
		}
	}
	check := func(c config.Client, dir string) error {
		if c.ClusterID != k.ClusterID || c.CA != config.Directory+"/"+dir+"/ca.crt" || c.Cert != config.Directory+"/"+dir+"/client.crt" || c.Key != config.Directory+"/"+dir+"/client.key" {
			return errors.New("KIT_CLIENT_PATH_OR_SCOPE_INVALID")
		}
		if e := config.ValidateClient(c); e != nil {
			return e
		}
		for _, p := range []string{"ca.crt", "client.crt", "client.key"} {
			if len(k.Files[dir+"/"+p]) == 0 {
				return errors.New("KIT_KEY_MISSING")
			}
		}
		return nil
	}
	if k.Host.Controller {
		var c config.Control
		if e := json.Unmarshal(k.Files["control.json"], &c); e != nil {
			return e
		}
		if c.Listen != k.Host.Address+":7443" || c.DataDir != config.Data+"/control" || c.VaultKey != config.Directory+"/control-pki/vault.key" || len(k.Files["control-pki/vault.key"]) != 32 {
			return errors.New("KIT_CONTROL_PATH_INVALID")
		}
		if e := check(c.Client, "control-pki"); e != nil {
			return e
		}
		if e := check(c.Etcd, "etcd-client-pki"); e != nil {
			return e
		}
	}
	if k.Host.Worker {
		var c config.Agent
		if e := json.Unmarshal(k.Files["agent.json"], &c); e != nil {
			return e
		}
		if c.Address != k.Host.Address || c.Journal != config.Data+"/agent/journal.json" || c.Socket != "/var/run/docker.sock" || !model.ValidID(c.NodeID) || !model.ValidID(c.InstanceID) {
			return errors.New("KIT_AGENT_PATH_INVALID")
		}
		if e := check(c.Client, "agent-pki"); e != nil {
			return e
		}
	}
	return nil
}
