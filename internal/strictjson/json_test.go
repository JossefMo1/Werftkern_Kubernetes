package strictjson

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestRejectsDuplicateMembersIncludingEscapedNames(t *testing.T) {
	for _, raw := range []string{`{"name":"first","Name":"second"}`, `{"K":1,"\u212a":2}`, `{"a":1,"a":2}`, `{"a":1,"\u0061":2}`, `{"a":{"b":1,"b":2}}`, `[{"a":1,"a":2}]`, `{} {}`, `{"a":NaN}`, `{"a":Infinity}`, `{"a":1`, strings.Repeat("[", 66) + "0" + strings.Repeat("]", 66)} {
		t.Run(raw[:min(24, len(raw))], func(t *testing.T) {
			var v any
			if Unmarshal([]byte(raw), &v) == nil {
				t.Fatal("invalid object accepted")
			}
		})
	}
}
func TestValidDisjointObjectNamesAndIntegerPrecision(t *testing.T) {
	var target struct {
		ID    uint64 `json:"id"`
		Items []struct {
			A int `json:"a"`
		} `json:"items"`
	}
	if e := Unmarshal([]byte(`{"id":7500000000000000001,"items":[{"a":1},{"a":2}]}`), &target); e != nil || target.ID != 7500000000000000001 {
		t.Fatal(target, e)
	}
	if e := Unmarshal([]byte(`{"other":1}`), &target); e == nil {
		t.Fatal("unknown field")
	}
}
func FuzzStrictJSON(f *testing.F) {
	for _, s := range []string{`{}`, `{"a":1,"a":2}`, `[null,true,"str",1]`, strings.Repeat("[", 65) + "0" + strings.Repeat("]", 65)} {
		f.Add([]byte(s))
	}
	f.Fuzz(func(t *testing.T, b []byte) {
		if len(b) > 65536 {
			return
		}
		var v any
		if Unmarshal(b, &v) == nil && !json.Valid(b) {
			t.Fatal("accepted invalid JSON")
		}
	})
}
