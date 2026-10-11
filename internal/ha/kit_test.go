package ha

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func topology() Topology {
	return Topology{Name: "lab", Hosts: []Host{{Name: "one", Address: "10.77.0.1", Controller: true, Worker: true, PodCIDR: "10.88.1.0/24"}, {Name: "two", Address: "10.77.0.2", Controller: true, Worker: true, PodCIDR: "10.88.2.0/24"}, {Name: "three", Address: "10.77.0.3", Controller: true, Worker: true, PodCIDR: "10.88.3.0/24"}}}
}
func TestKitsIndependentIdentitiesSharedCluster(t *testing.T) {
	ks, e := Prepare(topology(), time.Now())
	if e != nil {
		t.Fatal(e)
	}
	if len(ks) != 3 {
		t.Fatal(len(ks))
	}
	seeds := 0
	keys := map[string]bool{}
	for _, k := range ks {
		if e := ValidateKit(k); e != nil {
			t.Fatal(e)
		}
		if k.ClusterID != ks[0].ClusterID {
			t.Fatal("scope")
		}
		if k.Seed != nil {
			seeds++
			if len(k.Seed.Nodes) != 3 {
				t.Fatal("seed")
			}
		}
		key := string(k.Files["control-pki/client.key"])
		if keys[key] {
			t.Fatal("shared server key")
		}
		keys[key] = true
		pair, e := tls.X509KeyPair(k.Files["control-pki/client.crt"], k.Files["control-pki/client.key"])
		if e != nil {
			t.Fatal(e)
		}
		leaf, _ := x509.ParseCertificate(pair.Certificate[0])
		if e = leaf.VerifyHostname(k.Host.Address); e != nil {
			t.Fatal(e)
		}
		var c config.Control
		json.Unmarshal(k.Files["control.json"], &c)
		if len(c.Client.Servers) != 3 || len(c.Etcd.Servers) != 3 {
			t.Fatal("single endpoint")
		}
		b, e := EtcdConfig(k)
		if e != nil {
			t.Fatal(e)
		}
		var raw map[string]any
		json.Unmarshal(b, &raw)
		if raw["initial-cluster-token"] != k.ClusterID {
			t.Fatal("wrong cluster token")
		}
	}
	if seeds != 1 {
		t.Fatal("multiple seeds")
	}
}
func TestBadTopologies(t *testing.T) {
	for _, kind := range []string{"two", "overlap", "duplicate", "public", "unsafe-subnet"} {
		t.Run(kind, func(t *testing.T) {
			x := topology()
			switch kind {
			case "two":
				x.Hosts = x.Hosts[:2]
			case "overlap":
				x.Hosts[1].PodCIDR = x.Hosts[0].PodCIDR
			case "duplicate":
				x.Hosts[1].Address = x.Hosts[0].Address
			case "public":
				x.Hosts[0].Address = "8.8.8.8"
			case "unsafe-subnet":
				x.Hosts[0].PodCIDR = "0.0.0.0/0"
			}
			if Validate(x) == nil {
				t.Fatal("accepted")
			}
		})
	}
}
func TestKitsPrivateAndRefuseOverwrite(t *testing.T) {
	ks, e := Prepare(topology(), time.Now())
	if e != nil {
		t.Fatal(e)
	}
	p := filepath.Join(t.TempDir(), "kits")
	if e = WriteKits(p, ks); e != nil {
		t.Fatal(e)
	}
	if WriteKits(p, ks) == nil {
		t.Fatal("overwritten")
	}
	st, _ := os.Stat(filepath.Join(p, ks[0].Host.Name+".kit.json"))
	if st.Mode().Perm() != 0600 {
		t.Fatal("public keys")
	}
	ks[0].Files["../../etc/shadow"] = []byte("x")
	if ValidateKit(ks[0]) == nil {
		t.Fatal("traversal")
	}
}
func TestKitCannotPointAgentAtArbitraryHostSocket(t *testing.T) {
	ks, _ := Prepare(topology(), time.Now())
	var c config.Agent
	json.Unmarshal(ks[0].Files["agent.json"], &c)
	c.Socket = "/tmp/attacker.sock"
	ks[0].Files["agent.json"], _ = json.Marshal(c)
	if ValidateKit(ks[0]) == nil {
		t.Fatal("socket injection")
	}
}
