// Package strictjson rejects ambiguous objects before decoding typed contracts.
// Size limits belong at each ingress boundary; depth and duplicate members are
// enforced here. Werftkern additionally rejects case-fold collisions because Go
// typed decoding accepts case-insensitive aliases. This restriction also applies
// to dynamic maps; it is a protocol constraint, not a general JSON implementation.
// Typed schema validation and authorization remain independent checks.
package strictjson

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"unicode"
)

const MaxDepth = 64

func Unmarshal(raw []byte, target any) error {
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	if e := value(d, 0); e != nil {
		return e
	}
	if _, e := d.Token(); e != io.EOF {
		return errors.New("JSON_TRAILING_DATA")
	}
	d = json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	return d.Decode(target)
}
func value(d *json.Decoder, depth int) error {
	if depth > MaxDepth {
		return errors.New("JSON_NESTING_LIMIT")
	}
	token, e := d.Token()
	if e != nil {
		return errors.New("JSON_SYNTAX_INVALID")
	}
	delim, is := token.(json.Delim)
	if !is {
		return nil
	}
	switch delim {
	case '{':
		keys := map[string]bool{}
		for d.More() {
			key, e := d.Token()
			if e != nil {
				return errors.New("JSON_MEMBER_INVALID")
			}
			text, ok := key.(string)
			if !ok || keys[fold(text)] {
				return errors.New("JSON_DUPLICATE_MEMBER")
			}
			keys[fold(text)] = true
			if e = value(d, depth+1); e != nil {
				return e
			}
		}
		end, e := d.Token()
		if e != nil || end != json.Delim('}') {
			return errors.New("JSON_OBJECT_UNCLOSED")
		}
	case '[':
		for d.More() {
			if e = value(d, depth+1); e != nil {
				return e
			}
		}
		end, e := d.Token()
		if e != nil || end != json.Delim(']') {
			return errors.New("JSON_ARRAY_UNCLOSED")
		}
	default:
		return errors.New("JSON_DELIMITER_INVALID")
	}
	return nil
}

// Canonical representative of each Unicode simple-fold orbit, matching the
// equality semantics of encoding/json's insensitive fallback (including Kelvin K).
func fold(s string) string {
	out := make([]rune, 0, len(s))
	for _, r := range s {
		minimum := r
		for n := unicode.SimpleFold(r); n != r; n = unicode.SimpleFold(n) {
			if n < minimum {
				minimum = n
			}
		}
		out = append(out, minimum)
	}
	return string(out)
}
