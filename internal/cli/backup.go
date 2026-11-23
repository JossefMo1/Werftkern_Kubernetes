package cli

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/failover"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/pki"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/recovery"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/setup"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/store"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/vault"
)

func readBackupInput(path string) ([]byte, error) {
	f, e := safefile.OpenRead(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil {
		return nil, e
	}
	max := int64(3 * vault.MaxPlaintext)
	if st.Size() < 0 || st.Size() > max {
		return nil, errors.New("BACKUP_TOO_LARGE")
	}
	b, e := io.ReadAll(io.LimitReader(f, max+1))
	if e != nil {
		return nil, e
	}
	if int64(len(b)) > max {
		return nil, errors.New("BACKUP_TOO_LARGE")
	}
	return b, nil
}

func backupCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {