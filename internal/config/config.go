package config

import (
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/model"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
	"net/url"
	"os"
	"path/filepath"
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
	return nil
}
