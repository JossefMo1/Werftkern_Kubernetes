package setup

import (
	"net"
	"os"
	"path/filepath"
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

func TestReadSetupCredentialRefusesSymlinkAndInvalidPrivateKey(t *testing.T) {
	d := t.TempDir()
	ca := filepath.Join(d, "client.crt")
	key := filepath.Join(d, "client.key")
	if err := os.WriteFile(ca, []byte("ca"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(key, []byte("key"), 0600); err != nil {
		t.Fatal(err)
	}
	if got, err := readSetupCredential(ca, 1<<20, false); err != nil || string(got) != "ca" {
		t.Fatalf("valid certificate rejected: %v", err)
	}
	if got, err := readSetupCredential(key, 64<<10, true); err != nil || string(got) != "key" {
		t.Fatalf("valid private key rejected: %v", err)
	}
	link := filepath.Join(d, "client-link.crt")
	if err := os.Symlink(ca, link); err != nil {
		t.Fatal(err)
	}
	if _, err := readSetupCredential(link, 1<<20, false); err == nil {
		t.Fatal("followed certificate symlink")
	}
	parentLink := filepath.Join(d, "parent-link")
	if err := os.Symlink(d, parentLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readSetupCredential(filepath.Join(parentLink, "client.crt"), 1<<20, false); err == nil {
		t.Fatal("followed certificate parent symlink")
	}
	if err := os.Chmod(key, 0640); err != nil {
		t.Fatal(err)
	}
	if _, err := readSetupCredential(key, 64<<10, true); err == nil {
		t.Fatal("accepted private key with group permissions")
	}
	oversized := filepath.Join(d, "oversized.crt")
	if err := os.WriteFile(oversized, []byte("0123456789"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readSetupCredential(oversized, 4, false); err == nil {
		t.Fatal("accepted oversized credential")
	}
}
