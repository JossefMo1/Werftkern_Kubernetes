package volumearchive

import (
	"archive/tar"
	"bytes"
	"context"
	"encoding/binary"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"testing"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
)

func identity() Header {
	return Header{ClusterID: model.ID(), NodeID: model.ID(), VolumeID: model.ID()}
}
func owner() (int, int) {
	u, g := os.Getuid(), os.Getgid()
	if u == 0 {
		u, g = 65532, 65532
	}
	return u, g
}
func archiveFixture(t *testing.T) ([]byte, []byte, []byte) {
	t.Helper()
	root := t.TempDir()
	if e := os.Mkdir(filepath.Join(root, "database"), 0700); e != nil {
		t.Fatal(e)
	}
	data := bytes.Repeat([]byte("actual-volume-bytes\x00"), 200000)
	if e := os.WriteFile(filepath.Join(root, "database", "data.bin"), data, 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(root, "empty"), nil, 0600); e != nil {
		t.Fatal(e)
	}
	key := bytes.Repeat([]byte{42}, 32)
	var b bytes.Buffer
	result, e := Export(context.Background(), root, &b, key, identity(), Limits{})
	if e != nil {
		t.Fatal(e)
	}
	if result.Bytes != int64(len(data)) || result.Files != 3 {
		t.Fatal(result)
	}
	return b.Bytes(), key, data
}
func TestPhysicalBytesRoundTripAndFreshArchiveKeys(t *testing.T) {
	raw, key, want := archiveFixture(t)
	dest := filepath.Join(t.TempDir(), "restored")
	u, g := owner()
	got, e := Extract(context.Background(), bytes.NewReader(raw), key, dest, u, g, Limits{})
	if e != nil {
		t.Fatal(e)
	}
	data, e := os.ReadFile(filepath.Join(dest, "database", "data.bin"))
	if e != nil || !bytes.Equal(data, want) {
		t.Fatal("bytes mismatch", e)
	}
	if got.Bytes != int64(len(want)) {
		t.Fatal(got)
	}
	if bytes.Contains(raw, []byte("actual-volume-bytes")) {
		t.Fatal("plaintext leaked")
	}
	var second bytes.Buffer
	if _, e = Export(context.Background(), dest, &second, key, identity(), Limits{}); e != nil {
		t.Fatal(e)
	}
	if bytes.Equal(raw, second.Bytes()) {
		t.Fatal("encryption reused archive key/nonce")
	}
}
func TestTruncationWrongKeyTamperAndTrailingBytesRemovePartialDestination(t *testing.T) {
	raw, key, _ := archiveFixture(t)
	tests := map[string][]byte{"header-truncated": raw[:20], "last-byte": raw[:len(raw)-1], "no-end-marker": raw[:len(raw)-20], "mid-data": raw[:100000], "trailing": append(append([]byte{}, raw...), 1)}
	modified := append([]byte{}, raw...)
	modified[len(modified)/2] ^= 1
	tests["tamper"] = modified
	tests["wrong-key"] = raw
	for name, input := range tests {
		t.Run(name, func(t *testing.T) {
			k := key
			if name == "wrong-key" {
				k = bytes.Repeat([]byte{10}, 32)
			}
			dest := filepath.Join(t.TempDir(), "target")
			u, g := owner()
			if _, e := Extract(context.Background(), bytes.NewReader(input), k, dest, u, g, Limits{}); e == nil {
				t.Fatal("accepted invalid archive")
			}
			if _, e := os.Stat(dest); !os.IsNotExist(e) {
				t.Fatal("partial plaintext left", e)
			}
		})
	}
}
func TestRestoreCannotOverwriteExistingDirectory(t *testing.T) {
	raw, key, _ := archiveFixture(t)
	dest := t.TempDir()
	p := filepath.Join(dest, "keep")
	os.WriteFile(p, []byte("existing"), 0600)
	u, g := owner()
	if _, e := Extract(context.Background(), bytes.NewReader(raw), key, dest, u, g, Limits{}); e == nil {
		t.Fatal("overwrote directory")
	}
	b, e := os.ReadFile(p)
	if e != nil || string(b) != "existing" {
		t.Fatal("existing data changed")
	}
}
func TestRejectSymlinkHardlinkAndFIFOOnBackup(t *testing.T) {
	for _, kind := range []string{"symlink", "hardlink", "fifo"} {
		t.Run(kind, func(t *testing.T) {
			root := t.TempDir()
			source := filepath.Join(t.TempDir(), "external")
			os.WriteFile(source, []byte("outside"), 0600)
			var e error
			if kind == "symlink" {
				e = os.Symlink(source, filepath.Join(root, "unsafe"))
			} else if kind == "hardlink" {
				e = os.Link(source, filepath.Join(root, "unsafe"))
			} else {
				e = syscall.Mkfifo(filepath.Join(root, "unsafe"), 0600)
			}
			if e != nil {
				t.Fatal(e)
			}
			var b bytes.Buffer
			if _, e = Export(context.Background(), root, &b, bytes.Repeat([]byte{1}, 32), identity(), Limits{}); e == nil {
				t.Fatal("accepted link")
			}
		})
	}
}
func makeTar(t testing.TB, headers []*tar.Header, payload []byte) []byte {
	t.Helper()
	var b bytes.Buffer
	fw, _, e := newWriter(&b, bytes.Repeat([]byte{1}, 32), identity())
	if e != nil {
		t.Fatal(e)
	}
	tw := tar.NewWriter(fw)
	for _, h := range headers {
		if e = tw.WriteHeader(h); e != nil {
			t.Fatal(e)
		}
		if h.Size > 0 {
			if _, e = tw.Write(payload[:h.Size]); e != nil {
				t.Fatal(e)
			}
		}
	}
	if e = tw.Close(); e != nil {
		t.Fatal(e)
	}
	if e = fw.Close(); e != nil {
		t.Fatal(e)
	}
	return b.Bytes()
}
func TestAuthenticatedUnsafeTarRejected(t *testing.T) {
	cases := map[string][]*tar.Header{
		"traversal": {{Name: "../outside", Typeflag: tar.TypeReg}}, "absolute": {{Name: "/tmp/outside", Typeflag: tar.TypeReg}}, "symlink": {{Name: "link", Typeflag: tar.TypeSymlink, Linkname: "../outside"}}, "hardlink": {{Name: "link", Typeflag: tar.TypeLink, Linkname: "outside"}}, "duplicate": {{Name: "data", Typeflag: tar.TypeReg}, {Name: "data", Typeflag: tar.TypeReg}}, "missing-parent": {{Name: "absent/file", Typeflag: tar.TypeReg}}, "backslash": {{Name: "bad\\file", Typeflag: tar.TypeReg}},
	}
	for name, h := range cases {
		t.Run(name, func(t *testing.T) {
			raw := makeTar(t, h, nil)
			dest := filepath.Join(t.TempDir(), "target")
			u, g := owner()
			if _, e := Extract(context.Background(), bytes.NewReader(raw), bytes.Repeat([]byte{1}, 32), dest, u, g, Limits{}); e == nil {
				t.Fatal("unsafe tar accepted")
			}
			if _, e := os.Stat(dest); !os.IsNotExist(e) {
				t.Fatal("failed extraction retained")
			}
		})
	}
}
func TestLimitsAndCancellation(t *testing.T) {
	raw, key, _ := archiveFixture(t)
	for _, l := range []Limits{{Bytes: 1}, {Files: 1}, {Depth: 1}} {
		dest := filepath.Join(t.TempDir(), "target")
		u, g := owner()
		if _, e := Extract(context.Background(), bytes.NewReader(raw), key, dest, u, g, l); e == nil {
			t.Fatal("limit not enforced", l)
		}
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	var b bytes.Buffer
	if _, e := Export(ctx, t.TempDir(), &b, key, identity(), Limits{}); e != context.Canceled {
		t.Fatal(e)
	}
}
func TestFrameReorderingRejected(t *testing.T) {
	raw, key, _ := archiveFixture(t)
	start := len(magic) + 4 + int(binary.BigEndian.Uint32(raw[len(magic):]))
	size := 4 + int(binary.BigEndian.Uint32(raw[start:]))
	size2 := 4 + int(binary.BigEndian.Uint32(raw[start+size:]))
	tamper := append([]byte{}, raw[:start]...)
	tamper = append(tamper, raw[start+size:start+size+size2]...)
	tamper = append(tamper, raw[start:start+size]...)
	tamper = append(tamper, raw[start+size+size2:]...)
	u, g := owner()
	if _, e := Extract(context.Background(), bytes.NewReader(tamper), key, filepath.Join(t.TempDir(), "target"), u, g, Limits{}); e == nil {
		t.Fatal("reordered frame accepted")
	}
}
func FuzzVolumeArchiveRejectsMalformed(f *testing.F) {
	f.Add([]byte("not-an-archive"))
	f.Add([]byte(magic + strings.Repeat("\x00", 4)))
	f.Add(makeTar(f, []*tar.Header{{Name: "file", Typeflag: tar.TypeReg, Size: 4}}, []byte("seed")))
	f.Add(makeTar(f, []*tar.Header{{Name: "../unsafe", Typeflag: tar.TypeReg}}, nil))
	f.Fuzz(func(t *testing.T, raw []byte) {
		if len(raw) > 65536 {
			t.Skip()
		}
		u, g := owner()
		_, _ = Extract(context.Background(), bytes.NewReader(raw), bytes.Repeat([]byte{1}, 32), filepath.Join(t.TempDir(), "target"), u, g, Limits{Bytes: 65536, Files: 20, Depth: 8})
	})
}

func TestExportAndRestoreUseSameDepthBoundary(t *testing.T) {
	root := t.TempDir()
	if e := os.Mkdir(filepath.Join(root, "directory"), 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(root, "directory", "file"), []byte("data"), 0600); e != nil {
		t.Fatal(e)
	}
	key := bytes.Repeat([]byte{13}, 32)
	var buf bytes.Buffer
	if _, e := Export(context.Background(), root, &buf, key, identity(), Limits{Depth: 1}); e == nil {
		t.Fatal("created an archive the matching restore would reject")
	}
	buf.Reset()
	if _, e := Export(context.Background(), root, &buf, key, identity(), Limits{Depth: 2}); e != nil {
		t.Fatal(e)
	}
	u, g := owner()
	if _, e := Extract(context.Background(), &buf, key, filepath.Join(t.TempDir(), "destination"), u, g, Limits{Depth: 2}); e != nil {
		t.Fatal(e)
	}
}
