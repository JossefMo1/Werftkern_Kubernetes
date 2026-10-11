package migrate

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestNoSecretLeakOrSilentOperatorSupport(t *testing.T) {
	b := []byte(`{"kind":"List","items":[{"kind":"Secret","metadata":{"name":"db"},"data":{"password":"NEVER-OUTPUT-ME"}},{"kind":"FancyDatabase","metadata":{"name":"db-cluster"}},{"kind":"Deployment","metadata":{"name":"web"},"spec":{"template":{"spec":{"containers":[{"name":"web","image":"example@sha256:abcd"}],"volumes":[{}]}}}}]}`)
	r, e := Assess(b)
	if e != nil || r.Blocked != 3 {
		t.Fatal(r, e)
	}
	out, _ := json.Marshal(r)
	if strings.Contains(string(out), "NEVER-OUTPUT-ME") || !r.ReadOnly {
		t.Fatal("data leaked")
	}
}
func TestBoundedAndStrictInput(t *testing.T) {
	for _, s := range []string{"{} {}", "kind: Deployment", `{"kind":"List"}`, strings.Repeat("x", (2<<20)+1)} {
		if _, e := Assess([]byte(s)); e == nil {
			t.Fatal("invalid accepted")
		}
	}
}
func FuzzAssess(f *testing.F) {
	f.Add([]byte(`{"kind":"List","items":[]}`))
	f.Fuzz(func(t *testing.T, b []byte) {
		if len(b) < 100000 {
			Assess(b)
		}
	})
}
