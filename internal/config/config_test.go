package config

import (
	"strings"
	"testing"
)

func TestHTTPSClientContract(t *testing.T) {
	for _, u := range []string{"http://127.0.0.1:7443", "https://" + "fixture-user:fixture-value" + "@host", "https://host/path", "https://host?q=secret", "https://host#x", "https://host:0", "https://host:65536", "https://host:99999", "//host"} {
		if ValidateClient(Client{Server: u, ClusterID: strings.Repeat("a", 32)}) == nil {
			t.Fatal(u)
		}
	}
	if e := ValidateClient(Client{Server: "https://127.0.0.1:7443", ClusterID: strings.Repeat("a", 32)}); e != nil {
		t.Fatal(e)
	}
}

func TestControlValidationProtectsEtcdAndListenerBoundaries(t *testing.T) {
	cluster := strings.Repeat("a", 32)
	valid := Control{
		Client: Client{Server: "https://127.0.0.1:7443", ClusterID: cluster},
		Etcd:   Client{Server: "https://127.0.0.1:23791", ClusterID: cluster},
		Listen: "127.0.0.1:7443",
	}
	if e := ValidateControl(valid); e != nil {
		t.Fatal(e)
	}
	cases := []struct {
		name  string
		mutate func(*Control)
		want  string
	}{
		{"etcd-http", func(c *Control) { c.Etcd.Server = "http://127.0.0.1:23791" }, "ETCD_CLIENT_CONFIGURATION_INVALID"},
		{"etcd-cluster-mismatch", func(c *Control) { c.Etcd.ClusterID = strings.Repeat("b", 32) }, "ETCD_CLUSTER_ID_MISMATCH"},
		{"public-listener", func(c *Control) { c.Listen = "0.0.0.0:7443" }, "CONTROL_LISTEN_INVALID"},
		{"listener-without-port", func(c *Control) { c.Listen = "127.0.0.1" }, "CONTROL_LISTEN_INVALID"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			candidate := valid
			tc.mutate(&candidate)
			if e := ValidateControl(candidate); e == nil || e.Error() != tc.want {
				t.Fatalf("error=%v want=%s", e, tc.want)
			}
		})
	}
}
