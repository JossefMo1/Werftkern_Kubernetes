package cli

import (
	"encoding/json"
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/migrate"
	"io"
	"os"
)

func assessCommand(args []string) error {
	if len(args) != 1 {
		return errors.New("assess KUBERNETES-INVENTORY.json")
	}
	f, e := os.Open(args[0])
	if e != nil {
		return e
	}
	defer f.Close()
	b, e := io.ReadAll(io.LimitReader(f, (2<<20)+1))
	if e != nil {
		return e
	}
	report, e := migrate.Assess(b)
	if e != nil {
		return e
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(report)
}
