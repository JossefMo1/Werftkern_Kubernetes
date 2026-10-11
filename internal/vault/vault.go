// Package vault encrypts bounded secret payloads. Keys are random 256-bit values,
// not passwords; AAD binds ciphertext to its intended cluster/resource/version.
package vault

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/safefile"
	"io"
	"os"
	"path/filepath"
	"syscall"
)

const MaxPlaintext = 2 << 20

var ErrInvalid = errors.New("ENCRYPTED_DATA_INVALID_OR_WRONG_KEY")

type Vault struct{ aead cipher.AEAD }

func New(key []byte) (*Vault, error) {
	if len(key) != 32 {
		return nil, errors.New("RANDOM_256_BIT_KEY_REQUIRED")
	}
	c, e := aes.NewCipher(key)
	if e != nil {
		return nil, e
	}
	a, e := cipher.NewGCM(c)
	if e != nil {
		return nil, e
	}
	return &Vault{a}, nil
}
func GenerateKey() ([]byte, error) {
	b := make([]byte, 32)
	_, e := io.ReadFull(rand.Reader, b)
	return b, e
}
func LoadKey(path string) ([]byte, error) {
	fd, e := syscall.Open(path, syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if e != nil {
		return nil, e
	}
	f := os.NewFile(uintptr(fd), path)
	defer f.Close()
	st, e := f.Stat()
	if e != nil {
		return nil, e
	}
	if !st.Mode().IsRegular() || st.Mode().Perm()&0077 != 0 || st.Size() != 32 {
		return nil, errors.New("KEY_FILE_MUST_BE_32_BYTES_AND_PRIVATE")
	}
	return io.ReadAll(io.LimitReader(f, 33))
}
func CreateKey(path string) ([]byte, error) {
	if _, e := os.Lstat(path); !os.IsNotExist(e) {
		return nil, errors.New("KEY_ALREADY_EXISTS_OR_PATH_UNAVAILABLE")
	}
	k, e := GenerateKey()
	if e != nil {
		return nil, e
	}
	// Exclusive creation prevents concurrent setup from replacing a trust root.
	f, e := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		return nil, e
	}
	ok := false
	defer func() {
		f.Close()
		if !ok {
			os.Remove(path)
		}
	}()
	if _, e = f.Write(k); e != nil {
		return nil, e
	}
	if e = f.Sync(); e != nil {
		return nil, e
	}
	if e = f.Close(); e != nil {
		return nil, e
	}
	parent, e := os.Open(filepath.Dir(path))
	if e != nil {
		return nil, e
	}
	e = parent.Sync()
	parent.Close()
	if e != nil {
		return nil, e
	}
	ok = true
	return k, nil
}
func (v *Vault) Seal(b []byte, aad string) (string, error) {
	if len(b) > MaxPlaintext || aad == "" {
		return "", ErrInvalid
	}
	n := make([]byte, v.aead.NonceSize())
	if _, e := io.ReadFull(rand.Reader, n); e != nil {
		return "", e
	}
	out := v.aead.Seal(n, n, b, []byte(aad))
	return base64.StdEncoding.EncodeToString(out), nil
}
func (v *Vault) Open(s, aad string) ([]byte, error) {
	if len(s) > 3*MaxPlaintext || aad == "" {
		return nil, ErrInvalid
	}
	b, e := base64.StdEncoding.DecodeString(s)
	if e != nil || len(b) < v.aead.NonceSize()+v.aead.Overhead() {
		return nil, ErrInvalid
	}
	n := v.aead.NonceSize()
	b, e = v.aead.Open(nil, b[:n], b[n:], []byte(aad))
	if e != nil {
		return nil, ErrInvalid
	}
	return b, nil
}
func WriteKey(path string, key []byte) error {
	if len(key) != 32 {
		return ErrInvalid
	}
	return safefile.Write(path, key, 0600)
}
