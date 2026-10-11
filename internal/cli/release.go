package cli

import (
	"context"
	"encoding/json"
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/releaseverify"
	"os"
)

func releaseCommand(ctx context.Context, args []string) error {
	if len(args) == 0 || args[0] != "verify" {
		return errors.New("release verify --manifest FILE --signature FILE --public-key FILE --package FILE")
	}
	f := parser("release verify")
	manifest := f.String("manifest", "", "Signed manifest")
	sig := f.String("signature", "", "Detached raw signature")
	key := f.String("public-key", "", "Trusted PEM Ed25519 public key")
	pkg := f.String("package", "", "Debian package")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	read := func(path string, max int64) ([]byte, error) {
		st, e := os.Lstat(path)
		if e != nil {
			return nil, e
		}
		if !st.Mode().IsRegular() || st.Size() > max {
			return nil, errors.New("RELEASE_INPUT_INVALID")
		}
		return os.ReadFile(path)
	}
	raw, e := read(*manifest, 65536)
	if e != nil {
		return e
	}
	signature, e := read(*sig, 128)
	if e != nil {
		return e
	}
	pub, e := read(*key, 16384)
	if e != nil {
		return e
	}
	m, e := releaseverify.Verify(raw, signature, pub, *pkg)
	if e != nil {
		return e
	}
	return json.NewEncoder(os.Stdout).Encode(m)
}
