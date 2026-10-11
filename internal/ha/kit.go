// Package ha generates independent controller identities for a three-member
// etcd topology. Shared CAS state, not local leader flags, fences concurrent work.
package ha

import (
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/pki"
	"github.com/ClusterPilot-System/werftkern/internal/vault"
	"net"
	"sort"
	"time"
)

type Host struct {
	Name       string `json:"name"`
	Address    string `json:"address"`
	Controller bool   `json:"controller"`
	Worker     bool   `json:"worker"`
	PodCIDR    string `json:"podCidr,omitempty"`
}
type Topology struct {
	Name  string `json:"name"`
	Hosts []Host `json:"hosts"`
}
type Kit struct {
	Format      string            `json:"format"`
	ClusterID   string            `json:"clusterId"`
	Host        Host              `json:"host"`
	Controllers []Host            `json:"controllers"`
	Files       map[string][]byte `json:"files"`
	Seed        *model.State      `json:"seed,omitempty"`
}

func Validate(t Topology) error {
	if !model.ValidName(t.Name) || len(t.Hosts) > 20 {
		return errors.New("TOPOLOGY_INVALID")
	}
	n := 0
	names := map[string]bool{}
	ips := map[string]bool{}
	for _, h := range t.Hosts {
		if !model.ValidName(h.Name) || !model.PrivateAddress(h.Address) || net.ParseIP(h.Address).IsLoopback() || names[h.Name] || ips[h.Address] || !h.Worker && !h.Controller {
			return errors.New("HOST_INVALID_OR_DUPLICATE")
		}
		names[h.Name] = true
		ips[h.Address] = true
		if h.Controller {
			n++
		}
		for _, other := range t.Hosts {
			if other.Name != h.Name && model.SubnetsOverlap(h.PodCIDR, other.PodCIDR) {
				return errors.New("POD_SUBNET_OVERLAP")
			}
		}
		if h.PodCIDR != "" {
			if !model.ValidPodCIDR(h.PodCIDR) {
				return errors.New("POD_SUBNET_INVALID")
			}
			_, sub, e := net.ParseCIDR(h.PodCIDR)
			if e != nil || !sub.IP.IsPrivate() || sub.IP.To4() == nil {
				return errors.New("POD_SUBNET_INVALID")
			}
		}
	}
	if n != 3 {
		return errors.New("EXACTLY_THREE_CONTROLLERS_REQUIRED")
	}
	return nil
}
func Prepare(t Topology, now time.Time) ([]Kit, error) {
	if e := Validate(t); e != nil {
		return nil, e
	}
	sort.Slice(t.Hosts, func(i, j int) bool { return t.Hosts[i].Name < t.Hosts[j].Name })
	id := model.ID()
	ca, e := pki.CA("Werftkern "+id, now)
	if e != nil {
		return nil, e
	}
	eca, e := pki.CA("Werftkern etcd "+id, now)
	if e != nil {
		return nil, e
	}
	master, e := vault.GenerateKey()
	if e != nil {
		return nil, e
	}
	controllers := []Host{}
	urls := []string{}
	etcdURLs := []string{}
	for _, h := range t.Hosts {
		if h.Controller {
			controllers = append(controllers, h)
			urls = append(urls, "https://"+h.Address+":7443")
			etcdURLs = append(etcdURLs, "https://"+h.Address+":23791")
		}
	}
	seed := model.NewState(id, t.Name, now)
	nodeIDs := map[string]string{}
	for _, h := range t.Hosts {
		if h.Worker {
			nid := model.ID()
			nodeIDs[h.Name] = nid
			seed.Nodes[nid] = &model.Node{ID: nid, Name: h.Name, Address: h.Address, PodCIDR: h.PodCIDR}
		}
	}
	kits := []Kit{}
	for _, h := range t.Hosts {
		k := Kit{Format: "werftkern-ha-kit/v1", ClusterID: id, Host: h, Controllers: controllers, Files: map[string][]byte{}}
		put := func(path string, value any) { b, _ := json.MarshalIndent(value, "", "  "); k.Files[path] = b }
		pair := func(dir string, p pki.Pair, ca []byte) {
			k.Files[dir+"/client.crt"] = p.Cert
			k.Files[dir+"/client.key"] = p.Key
			k.Files[dir+"/ca.crt"] = ca
		}
		client := func(dir string, server string, endpoints []string) config.Client {
			return config.Client{Server: server, Servers: endpoints, CA: config.Directory + "/" + dir + "/ca.crt", Cert: config.Directory + "/" + dir + "/client.crt", Key: config.Directory + "/" + dir + "/client.key", ClusterID: id}
		}
		if h.Controller {
			s, e := pki.Issue(ca, "server", id, []string{h.Address}, true, now)
			if e != nil {
				return nil, e
			}
			pair("control-pki", s, ca.Cert)
			es, e := pki.Issue(eca, "etcd-server", id, []string{h.Address, "127.0.0.1"}, true, now)
			if e != nil {
				return nil, e
			}
			pair("etcd-pki", es, eca.Cert)
			ec, e := pki.Issue(eca, "etcd-client", id, nil, false, now)
			if e != nil {
				return nil, e
			}
			pair("etcd-client-pki", ec, eca.Cert)
			k.Files["control-pki/vault.key"] = master
			put("control.json", config.Control{Client: client("control-pki", "https://"+h.Address+":7443", urls), Listen: h.Address + ":7443", Etcd: client("etcd-client-pki", etcdURLs[0], etcdURLs), DataDir: config.Data + "/control", VaultKey: config.Directory + "/control-pki/vault.key"})
			admin, e := pki.Issue(ca, "admin", id, nil, false, now)
			if e != nil {
				return nil, e
			}
			pair("admin-pki", admin, ca.Cert)
			put("admin.json", client("admin-pki", urls[0], urls))
			if h.Name == controllers[0].Name {
				k.Seed = seed
				pair("authority", ca, ca.Cert)
				pair("etcd-authority", eca, eca.Cert)
			}
		}
		if h.Worker {
			ag, e := pki.Issue(ca, "node:"+nodeIDs[h.Name], id, nil, false, now)
			if e != nil {
				return nil, e
			}
			pair("agent-pki", ag, ca.Cert)
			put("agent.json", config.Agent{Client: client("agent-pki", urls[0], urls), NodeID: nodeIDs[h.Name], InstanceID: model.ID(), Address: h.Address, Journal: config.Data + "/agent/journal.json", Socket: "/var/run/docker.sock", DemoArchive: "/usr/share/werftkern/demo-image.tar"})
		}
		kits = append(kits, k)
	}
	return kits, nil
}
func EtcdConfig(k Kit) ([]byte, error) {
	if !k.Host.Controller || !model.ValidID(k.ClusterID) {
		return nil, errors.New("CONTROLLER_REQUIRED")
	}
	initial := ""
	for i, h := range k.Controllers {
		if i > 0 {
			initial += ","
		}
		initial += h.Name + "=https://" + h.Address + ":23801"
	}
	transport := map[string]any{"cert-file": config.Directory + "/etcd-pki/client.crt", "key-file": config.Directory + "/etcd-pki/client.key", "trusted-ca-file": config.Directory + "/etcd-pki/ca.crt", "client-cert-auth": true}
	// JSON is accepted by etcd's YAML configuration parser.
	return json.MarshalIndent(map[string]any{"name": k.Host.Name, "data-dir": config.Data + "/etcd", "listen-client-urls": "https://" + k.Host.Address + ":23791,https://127.0.0.1:23791", "advertise-client-urls": "https://" + k.Host.Address + ":23791", "listen-peer-urls": "https://" + k.Host.Address + ":23801", "initial-advertise-peer-urls": "https://" + k.Host.Address + ":23801", "initial-cluster": initial, "initial-cluster-state": "new", "initial-cluster-token": k.ClusterID, "client-transport-security": transport, "peer-transport-security": transport, "auto-compaction-mode": "periodic", "auto-compaction-retention": "1h", "quota-backend-bytes": 268435456}, "", "  ")
}
func AllowedFile(name string) bool {
	switch name {
	case "control.json", "admin.json", "agent.json":
		return true
	}
	for _, d := range []string{"authority", "etcd-authority", "control-pki", "etcd-pki", "etcd-client-pki", "admin-pki", "agent-pki"} {
		for _, f := range []string{"client.crt", "client.key", "ca.crt"} {
			if name == d+"/"+f {
				return true
			}
		}
	}
	return name == "control-pki/vault.key"
}
func ValidateKit(k Kit) error {
	if k.Format != "werftkern-ha-kit/v1" || !model.ValidID(k.ClusterID) || len(k.Files) > 32 {
		return errors.New("KIT_INVALID")
	}
	hs := append([]Host{}, k.Controllers...)
	found := false
	for _, h := range hs {
		if h == k.Host {
			found = true
		}
	}
	if !found {
		hs = append(hs, k.Host)
	}
	if e := Validate(Topology{Name: "kit", Hosts: hs}); e != nil {
		return e
	}
	for path, b := range k.Files {
		if !AllowedFile(path) || len(b) > 65536 {
			return fmt.Errorf("KIT_FILE_NOT_ALLOWED")
		}
	}
	return validateConfigurations(k)
}
