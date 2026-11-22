package config

import (
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"net"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const Directory = "/etc/werftkern"
const Data = "/var/lib/werftkern"

type Client struct {
	Servers   []string `json:"servers,omitempty"`
	Server    string   `json:"server"`
	CA        string   `json:"ca"`
	Cert      string   `json:"cert"`
	Key       string   `json:"key"`
	ClusterID string   `json:"clusterId"`
}
type Control struct {
	Client   Client `json:"client"`
	Listen   string `json:"listen"`
	Etcd     Client `json:"etcd"`
	DataDir  string `json:"dataDir"`
	VaultKey string `json:"vaultKey,omitempty"`
}
type Agent struct {
	Network     string   `json:"network,omitempty"`
	Client      Client   `json:"client"`
	NodeID      string   `json:"nodeId"`
	InstanceID  string   `json:"instanceId"`
	Address     string   `json:"address"`
	Journal     string   `json:"journal"`
	Socket      string   `json:"socket"`
	DNS         []string `json:"dns,omitempty"`
	VolumeRoot  string   `json:"volumeRoot,omitempty"`
	DemoArchive string   `json:"demoArchive,omitempty"`
}

func Load[T any](path string) (T, error) { var c T; e := safefile.ReadJSON(path, &c); return c, e }
func AdminPath() string {
	if p := os.Getenv("WERFT_CONFIG"); p != "" {
		return p
	}
	return filepath.Join(Directory, "admin.json")
}
func ValidateClient(c Client) error {
	if len(c.Servers) > 5 {
		return errors.New("TOO_MANY_ENDPOINTS")
	}
	for _, server := range c.Servers {
		other := c
		other.Servers = nil
		other.Server = server
		if e := ValidateClient(other); e != nil {
			return e
		}
	}
	u, e := url.Parse(c.Server)
	if e != nil || u.Scheme != "https" || u.Host == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || strings.Trim(u.Path, "/") != "" || !model.ValidID(c.ClusterID) {
		return errors.New("CLIENT_CONFIGURATION_INVALID")
	}
	if port := u.Port(); port != "" {
		n, e := strconv.Atoi(port)
		if e != nil || n < 1 || n > 65535 {
			return errors.New("CLIENT_CONFIGURATION_INVALID")
		}
	}
	return nil
}

// ValidateControl enforces the trust boundary for the native control process.
// The control endpoint and the separate etcd endpoint must both use HTTPS and
// the same cluster identity; the listener is restricted to a private IPv4/loopback
// address for the bounded single-host deployment.
func ValidateControl(c Control) error {
	if e := ValidateClient(c.Client); e != nil {
		return errors.New("CONTROL_CLIENT_CONFIGURATION_INVALID")
	}
	if e := ValidateClient(c.Etcd); e != nil {
		return errors.New("ETCD_CLIENT_CONFIGURATION_INVALID")
	}
	if c.Etcd.ClusterID != c.Client.ClusterID {
		return errors.New("ETCD_CLUSTER_ID_MISMATCH")
	}
	host, port, e := net.SplitHostPort(c.Listen)
	if e != nil || !model.PrivateAddress(host) {
		return errors.New("CONTROL_LISTEN_INVALID")
	}
	n, e := strconv.Atoi(port)
	if e != nil || n < 1 || n > 65535 {
		return errors.New("CONTROL_LISTEN_INVALID")
	}
	return nil
}
