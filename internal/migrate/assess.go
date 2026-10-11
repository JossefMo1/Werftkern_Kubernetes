// Package migrate performs bounded offline inspection, never mutation or a
// promise of Kubernetes semantic compatibility. It deliberately omits values.
package migrate

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"regexp"
	"sort"
	"strings"
)

var digestImage = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[a-f0-9]{64}$`)

type Finding struct {
	Kind        string   `json:"kind"`
	Name        string   `json:"name"`
	Namespace   string   `json:"namespace"`
	Disposition string   `json:"disposition"`
	Reasons     []string `json:"reasons"`
}
type Report struct {
	Format   string    `json:"format"`
	ReadOnly bool      `json:"readOnly"`
	Findings []Finding `json:"findings"`
	Blocked  int       `json:"blocked"`
}

func obj(v any) map[string]any { m, _ := v.(map[string]any); return m }
func text(v any) string {
	s, _ := v.(string)
	if len(s) > 128 {
		return "<name-too-long>"
	}
	return strings.Map(func(r rune) rune {
		if r < 32 || r == 127 {
			return -1
		}
		return r
	}, s)
}
func Assess(b []byte) (Report, error) {
	out := Report{Format: "clusterpilot/migration-assessment/v1", ReadOnly: true, Findings: []Finding{}}
	if len(b) > 2<<20 {
		return out, errors.New("INVENTORY_TOO_LARGE")
	}
	d := json.NewDecoder(bytes.NewReader(b))
	var root map[string]any
	if e := d.Decode(&root); e != nil {
		return out, errors.New("KUBERNETES_JSON_REQUIRED")
	}
	var extra any
	if d.Decode(&extra) != io.EOF {
		return out, errors.New("TRAILING_JSON")
	}
	items := []any{root}
	if root["kind"] == "List" {
		var ok bool
		items, ok = root["items"].([]any)
		if !ok {
			return out, errors.New("LIST_ITEMS_REQUIRED")
		}
	}
	if len(items) > 1000 {
		return out, errors.New("INVENTORY_RESOURCE_LIMIT")
	}
	for _, item := range items {
		o := obj(item)
		meta := obj(o["metadata"])
		f := Finding{Kind: text(o["kind"]), Name: text(meta["name"]), Namespace: text(meta["namespace"]), Disposition: "blocked", Reasons: []string{}}
		switch f.Kind {
		case "Deployment":
			f.Disposition = "candidate-manual-review"
			spec := obj(obj(obj(o["spec"])["template"])["spec"])
			containers, _ := spec["containers"].([]any)
			if len(containers) != 1 {
				f.Reasons = append(f.Reasons, "ONE_CONTAINER_REQUIRED")
			}
			for key := range spec {
				switch key {
				case "containers", "restartPolicy", "terminationGracePeriodSeconds":
				default:
					f.Reasons = append(f.Reasons, "POD_FIELD_REQUIRES_REVIEW:"+text(key))
				}
			}
			if len(containers) == 1 {
				c := obj(containers[0])
				image, _ := c["image"].(string)
				if !digestImage.MatchString(image) {
					f.Reasons = append(f.Reasons, "IMMUTABLE_IMAGE_DIGEST_REQUIRED")
				}
				for key := range c {
					switch key {
					case "name", "image", "resources", "ports", "readinessProbe", "command", "args":
					default:
						f.Reasons = append(f.Reasons, "CONTAINER_FIELD_REQUIRES_REVIEW:"+text(key))
					}
				}
			}
			if len(f.Reasons) > 0 {
				f.Disposition = "blocked"
			} else {
				f.Reasons = append(f.Reasons, "MANUAL_SECURITY_RESOURCE_HEALTH_AND_ROUTING_REVIEW_REQUIRED")
			}
		case "Secret":
			f.Reasons = append(f.Reasons, "IMPORT_TO_VERSIONED_VAULT_MANUALLY_VALUES_NOT_INCLUDED")
		case "Service", "Ingress", "ConfigMap":
			f.Reasons = append(f.Reasons, "NETWORK_OR_CONFIGURATION_MAPPING_NOT_AUTOMATIC")
		default:
			f.Reasons = append(f.Reasons, "RESOURCE_KIND_UNSUPPORTED")
		}
		sort.Strings(f.Reasons)
		if f.Disposition == "blocked" {
			out.Blocked++
		}
		out.Findings = append(out.Findings, f)
	}
	sort.SliceStable(out.Findings, func(i, j int) bool {
		a, b := out.Findings[i], out.Findings[j]
		return a.Namespace+"/"+a.Kind+"/"+a.Name < b.Namespace+"/"+b.Kind+"/"+b.Name
	})
	return out, nil
}
