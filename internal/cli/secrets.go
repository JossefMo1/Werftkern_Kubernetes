package cli

import (
	"context"
	"errors"
	"fmt"
	"io"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"strconv"
)

func readPrivateSecret(path string) ([]byte, error) {
	f, e := safefile.OpenRead(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil || !st.Mode().IsRegular() || st.Mode().Perm()&0077 != 0 || st.Size() < 1 || st.Size() > 4096 {
		return nil, errors.New("SECRET_INPUT_FILE_MUST_BE_PRIVATE_AND_AT_MOST_4096_BYTES")
	}
	b, e := io.ReadAll(io.LimitReader(f, 4097))
	if e != nil {
		return nil, e
	}
	if len(b) > 4096 {
		return nil, errors.New("SECRET_INPUT_FILE_MUST_BE_PRIVATE_AND_AT_MOST_4096_BYTES")
	}
	return b, nil
}

func secretCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("secret put NAME --file FILE [--expected-version N] | list | delete NAME VERSION")
	}
	if args[0] != "list" && args[0] != "put" && args[0] != "delete" {
		return errors.New("SECRET_ACTION_UNKNOWN")
	}
	c, e := client()
	if e != nil {
		return e
	}
	switch args[0] {
	case "list":
		s, e := c.State(ctx)
		if e != nil {
			return e
		}
		for _, k := range model.SortedKeys(s.Secrets) {
			v := s.Secrets[k]
			fmt.Printf("%s version=%d\n", v.Name, v.Version)
		}
		return nil
	case "put":
		if len(args) < 2 || !model.ValidName(args[1]) {
			return errors.New("SECRET_NAME_REQUIRED")
		}
		f := parser("secret put")
		path := f.String("file", "", "Private input file")
		expected := f.Int("expected-version", 0, "Previous version")
		if e = f.Parse(args[2:]); e != nil {
			return e
		}
		b, e := readPrivateSecret(*path)
		if e != nil {
			return e
		}
		var ref model.SecretRef
		if e = c.Call(ctx, "PUT", "/v1/secrets/"+args[1], control.SecretInput{Value: b, ExpectedVersion: *expected}, &ref, model.ID()); e != nil {
			return e
		}
		fmt.Printf("Stored immutable secret %s version %d. No plaintext readback.\n", ref.Name, ref.Version)
		return nil
	case "delete":
		if len(args) != 3 {
			return errors.New("secret delete NAME VERSION")
		}
		v, e := strconv.Atoi(args[2])
		if e != nil || model.ValidateSecretRefs([]model.SecretRef{{Name: args[1], Version: v}}) != nil {
			return errors.New("SECRET_REFERENCE_INVALID")
		}
		return c.Call(ctx, "DELETE", "/v1/secrets/"+args[1]+"/"+args[2], nil, nil, "")
	}
	return errors.New("SECRET_ACTION_UNKNOWN")
}
