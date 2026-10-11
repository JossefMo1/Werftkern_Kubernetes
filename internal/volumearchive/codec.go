// Package volumearchive encrypts bounded, quiescent local-volume archives.
// It deliberately does not claim to snapshot a running application or implement
// storage replication. Each frame and the mandatory end marker are authenticated.
package volumearchive

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"

	"github.com/ClusterPilot-System/werftkern/internal/model"
)

const magic = "WERFTVOL1\n"
const chunkSize = 64 * 1024

// Header contains no plaintext application data. The entire header is AAD.
type Header struct {
	Version   int       `json:"version"`
	BackupID  string    `json:"backupId"`
	ClusterID string    `json:"clusterId"`
	VolumeID  string    `json:"volumeId"`
	NodeID    string    `json:"nodeId"`
	CreatedAt time.Time `json:"createdAt"`
	Salt      []byte    `json:"salt"`
}

func (h Header) validate() error {
	if h.Version != 1 || !model.ValidID(h.BackupID) || !model.ValidID(h.ClusterID) || !model.ValidID(h.VolumeID) || !model.ValidID(h.NodeID) || len(h.Salt) != 32 || h.CreatedAt.IsZero() {
		return errors.New("VOLUME_ARCHIVE_HEADER_INVALID")
	}
	return nil
}
func aead(key, salt []byte) (cipher.AEAD, error) {
	if len(key) != 32 {
		return nil, errors.New("VOLUME_BACKUP_KEY_MUST_BE_32_BYTES")
	}
	// A unique random salt derives a separate encryption key for every archive.
	extract := hmac.New(sha256.New, salt)
	extract.Write(key)
	expand := hmac.New(sha256.New, extract.Sum(nil))
	expand.Write([]byte("werftkern-volume-v1\x01"))
	block, e := aes.NewCipher(expand.Sum(nil))
	if e != nil {
		return nil, e
	}
	return cipher.NewGCM(block)
}
func nonceAndAAD(hash [32]byte, sequence uint64) ([]byte, []byte) {
	nonce := make([]byte, 12)
	binary.BigEndian.PutUint64(nonce[4:], sequence)
	aad := make([]byte, 40)
	copy(aad, hash[:])
	binary.BigEndian.PutUint64(aad[32:], sequence)
	return nonce, aad
}

type frameWriter struct {
	dst    io.Writer
	cipher cipher.AEAD
	hash   [32]byte
	seq    uint64
	buf    []byte
	closed bool
	err    error
}

func newWriter(dst io.Writer, key []byte, h Header) (*frameWriter, Header, error) {
	h.Version = 1
	h.BackupID = model.ID()
	h.CreatedAt = time.Now().UTC()
	h.Salt = make([]byte, 32)
	if _, e := rand.Read(h.Salt); e != nil {
		return nil, h, e
	}
	if e := h.validate(); e != nil {
		return nil, h, e
	}
	c, e := aead(key, h.Salt)
	if e != nil {
		return nil, h, e
	}
	raw, e := json.Marshal(h)
	if e != nil {
		return nil, h, e
	}
	if _, e = io.WriteString(dst, magic); e != nil {
		return nil, h, e
	}
	if e = binary.Write(dst, binary.BigEndian, uint32(len(raw))); e != nil {
		return nil, h, e
	}
	if _, e = dst.Write(raw); e != nil {
		return nil, h, e
	}
	return &frameWriter{dst: dst, cipher: c, hash: sha256.Sum256(raw), buf: make([]byte, 0, chunkSize)}, h, nil
}
func (w *frameWriter) frame(data []byte) error {
	if w.seq == ^uint64(0) {
		return errors.New("VOLUME_ARCHIVE_TOO_MANY_FRAMES")
	}
	nonce, aad := nonceAndAAD(w.hash, w.seq)
	w.seq++
	encrypted := w.cipher.Seal(nil, nonce, data, aad)
	if e := binary.Write(w.dst, binary.BigEndian, uint32(len(encrypted))); e != nil {
		return e
	}
	n, e := w.dst.Write(encrypted)
	if e == nil && n != len(encrypted) {
		e = io.ErrShortWrite
	}
	return e
}
func (w *frameWriter) Write(p []byte) (int, error) {
	if w.closed {
		return 0, errors.New("VOLUME_ARCHIVE_CLOSED")
	}
	if w.err != nil {
		return 0, w.err
	}
	total := 0
	for len(p) > 0 {
		n := chunkSize - len(w.buf)
		if n > len(p) {
			n = len(p)
		}
		w.buf = append(w.buf, p[:n]...)
		p = p[n:]
		total += n
		if len(w.buf) == chunkSize {
			if w.err = w.frame(w.buf); w.err != nil {
				return total, w.err
			}
			w.buf = w.buf[:0]
		}
	}
	return total, nil
}
func (w *frameWriter) Close() error {
	if w.closed {
		return errors.New("VOLUME_ARCHIVE_ALREADY_CLOSED")
	}
	w.closed = true
	if w.err != nil {
		return w.err
	}
	if len(w.buf) > 0 {
		if e := w.frame(w.buf); e != nil {
			return e
		}
	}
	return w.frame(nil) // Mandatory authenticated terminator, not unauthenticated EOF.
}

type frameReader struct {
	src    io.Reader
	cipher cipher.AEAD
	hash   [32]byte
	seq    uint64
	buf    []byte
	end    bool
}

func newReader(src io.Reader, key []byte) (*frameReader, Header, error) {
	var h Header
	b := make([]byte, len(magic))
	if _, e := io.ReadFull(src, b); e != nil {
		return nil, h, e
	}
	if string(b) != magic {
		return nil, h, errors.New("VOLUME_ARCHIVE_MAGIC_INVALID")
	}
	var length uint32
	if e := binary.Read(src, binary.BigEndian, &length); e != nil {
		return nil, h, e
	}
	if length < 2 || length > 4096 {
		return nil, h, errors.New("VOLUME_ARCHIVE_HEADER_SIZE_INVALID")
	}
	raw := make([]byte, length)
	if _, e := io.ReadFull(src, raw); e != nil {
		return nil, h, e
	}
	if e := json.Unmarshal(raw, &h); e != nil {
		return nil, h, e
	}
	if e := h.validate(); e != nil {
		return nil, h, e
	}
	c, e := aead(key, h.Salt)
	if e != nil {
		return nil, h, e
	}
	return &frameReader{src: src, cipher: c, hash: sha256.Sum256(raw)}, h, nil
}
func (r *frameReader) Read(p []byte) (int, error) {
	if len(p) == 0 {
		return 0, nil
	}
	if len(r.buf) > 0 {
		n := copy(p, r.buf)
		r.buf = r.buf[n:]
		return n, nil
	}
	if r.end {
		return 0, io.EOF
	}
	var length uint32
	if e := binary.Read(r.src, binary.BigEndian, &length); e != nil {
		return 0, fmt.Errorf("VOLUME_ARCHIVE_TERMINATOR_MISSING: %w", e)
	}
	if length < uint32(r.cipher.Overhead()) || length > chunkSize+uint32(r.cipher.Overhead()) || r.seq == ^uint64(0) {
		return 0, errors.New("VOLUME_ARCHIVE_FRAME_INVALID")
	}
	encrypted := make([]byte, length)
	if _, e := io.ReadFull(r.src, encrypted); e != nil {
		return 0, e
	}
	nonce, aad := nonceAndAAD(r.hash, r.seq)
	r.seq++
	plain, e := r.cipher.Open(nil, nonce, encrypted, aad)
	if e != nil {
		return 0, errors.New("VOLUME_ARCHIVE_AUTHENTICATION_FAILED")
	}
	if len(plain) == 0 {
		r.end = true
		var tail [1]byte
		n, e := r.src.Read(tail[:])
		if n != 0 || e != io.EOF {
			return 0, errors.New("VOLUME_ARCHIVE_TRAILING_DATA")
		}
		return 0, io.EOF
	}
	n := copy(p, plain)
	r.buf = plain[n:]
	return n, nil
}
