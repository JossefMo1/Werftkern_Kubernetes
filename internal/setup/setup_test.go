package setup

import (
	"bytes"
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

func TestReadJoinBundleRejectsSymlinkedInput(t *testing.T) {
	d := t.TempDir()
	input := filepath.Join(d, "join.json")
	if err := os.WriteFile(input, []byte("{}\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readJoinBundle(input); err != nil {
		t.Fatalf("valid join bundle rejected: %v", err)
	}
	link := filepath.Join(d, "join-link.json")
	if err := os.Symlink(input, link); err != nil {
		t.Fatal(err)
	}
	if _, err := readJoinBundle(link); err == nil {
		t.Fatal("followed join bundle symlink")
	}
	parentLink := filepath.Join(d, "parent-link")
	if err := os.Symlink(d, parentLink); err != nil {
		t.Fatal(err)
	}
	if _, err := readJoinBundle(filepath.Join(parentLink, "join.json")); err == nil {
		t.Fatal("followed join bundle parent symlink")
	}
	if err := os.Chmod(input, 0640); err != nil {
		t.Fatal(err)
	}
	if _, err := readJoinBundle(input); err == nil {
		t.Fatal("accepted join bundle with group permissions")
	}
}

func TestReadJoinBundleRejectsOversizedInput(t *testing.T) {
	d := t.TempDir()
	path := filepath.Join(d, "join.json")
	if err := os.WriteFile(path, bytes.Repeat([]byte("x"), 32769), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readJoinBundle(path); err == nil {
		t.Fatal("accepted oversized join bundle")
	}
}

func TestReadJoinBundleAcceptsExactSizeLimit(t *testing.T) {
	d := t.TempDir()
	path := filepath.Join(d, "join.json")
	raw := append([]byte("{}"), bytes.Repeat([]byte(" "), 32766)...)
	if len(raw) != 32768 {
		t.Fatalf("test fixture has unexpected size: %d", len(raw))
	}
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readJoinBundle(path); err != nil {
		t.Fatalf("rejected exact-size join bundle: %v", err)
	}
}
