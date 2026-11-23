package cli

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/releaseverify"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
)

func readReleaseInput(path string, max int64) ([]byte, error) {
	f, e := safefile.OpenRead(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil {
		return nil, e
	}
	if st.Size() < 0 || st.Size() > max {
		return nil, errors.New("RELEASE_INPUT_INVALID")
	}
	raw, e := io.ReadAll(io.LimitReader(f, max+1))
	if e != nil {
		return nil, e
	}
	if int64(len(raw)) > max {
		return nil, errors.New("RELEASE_INPUT_INVALID")
	}
	return raw, nil
}

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
	raw, e := readReleaseInput(*manifest, 65536)
	if e != nil {
		return e
	}
	signature, e := readReleaseInput(*sig, 128)
	if e != nil {
		return e
	}
	pub, e := readReleaseInput(*key, 16384)
	if e != nil {
		return e
	}
	m, e := releaseverify.Verify(raw, signature, pub, *pkg)
	if e != nil {
		return e
	}
	return json.NewEncoder(os.Stdout).Encode(m)
}
