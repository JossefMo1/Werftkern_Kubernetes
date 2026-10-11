package vault

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAuthenticatedEncryption(t *testing.T) {
	k, _ := GenerateKey()
	v, _ := New(k)
	a, _ := v.Seal([]byte("sensitive"), "cluster/name/1")
	b, _ := v.Seal([]byte("sensitive"), "cluster/name/1")
	if a == b || strings.Contains(a, "sensitive") {
		t.Fatal("nonce reuse or plaintext")
	}
	got, e := v.Open(a, "cluster/name/1")
	if e != nil || string(got) != "sensitive" {
		t.Fatal(e)
	}
	for _, aad := range []string{"other/name/1", "cluster/name/2", ""} {
		if _, e := v.Open(a, aad); e == nil {
			t.Fatal("AAD bypass")
		}
	}
	k2, _ := GenerateKey()
	v2, _ := New(k2)
	if _, e := v2.Open(a, "cluster/name/1"); e == nil {
		t.Fatal("wrong key")
	}
	for _, bad := range []string{"", a[:len(a)-4], "AAAA" + a[4:], strings.Repeat("x", 3*MaxPlaintext+1)} {
		if _, e := v.Open(bad, "cluster/name/1"); e == nil {
			t.Fatal("bad ciphertext")
		}
	}
}
func TestKeys(t *testing.T) {
	p := filepath.Join(t.TempDir(), "key")
	k, e := CreateKey(p)
	if e != nil || len(k) != 32 {
		t.Fatal(e)
	}
	if _, e = CreateKey(p); e == nil {
		t.Fatal("overwritten")
	}
	if _, e = LoadKey(p); e != nil {
		t.Fatal(e)
	}
	link := filepath.Join(filepath.Dir(p), "link")
	if e = os.Symlink(p, link); e != nil {
		t.Fatal(e)
	}
	if _, e = LoadKey(link); e == nil {
		t.Fatal("symlink accepted")
	}
	os.Chmod(p, 0644)
	if _, e = LoadKey(p); e == nil {
		t.Fatal("public key material")
	}
	if _, e = New([]byte("password")); e == nil {
		t.Fatal("weak key")
	}
}
func FuzzOpen(f *testing.F) {
	f.Add("AAAA")
	v, _ := New(make([]byte, 32))
	f.Fuzz(func(t *testing.T, s string) {
		if len(s) < 10000 {
			v.Open(s, "context")
		}
	})
}
