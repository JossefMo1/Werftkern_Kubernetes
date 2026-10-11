package config

import (
	"strings"
	"testing"
)

func TestHTTPSClientContract(t *testing.T) {
	for _, u := range []string{"http://127.0.0.1:7443", "https://" + "fixture-user:fixture-value" + "@host", "https://host/path", "https://host?q=secret", "https://host#x", "//host"} {
		if ValidateClient(Client{Server: u, ClusterID: strings.Repeat("a", 32)}) == nil {
			t.Fatal(u)
		}
	}
	if e := ValidateClient(Client{Server: "https://127.0.0.1:7443", ClusterID: strings.Repeat("a", 32)}); e != nil {
		t.Fatal(e)
	}
}
