package setup

import (
	"net"
	"os"
	"strings"
	"testing"
)

func TestLocalAddressRejectsForeignAndPublic(t *testing.T) {
	for _, s := range []string{"8.8.8.8", "169.254.169.254", "not-an-ip", "::1"} {
		if LocalAddress(s) {
			t.Fatal("accepted", s)
		}
	}
	if !LocalAddress("127.0.0.1") {
		t.Fatal("expected assigned loopback")
	}
}
func TestSuggestedAddressIsLocal(t *testing.T) {
	s := SuggestedIP()
	if net.ParseIP(s) == nil || !LocalAddress(s) {
		t.Fatal(s)
	}
}
func TestPreflightDoesNotMutateUnsupportedSystem(t *testing.T) {
	b, e := os.ReadFile("/etc/os-release")
	if e != nil {
		t.Fatal(e)
	}
	if !strings.Contains(string(b), "ID=ubuntu") {
		if Preflight() == nil {
			t.Fatal("unsupported system admitted")
		}
	}
}
