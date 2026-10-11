package model

import (
	"errors"
	"sort"
)

type Gateway struct {
	ID       string   `json:"id"`
	Name     string   `json:"name"`
	Services []string `json:"services"`
	Revoked  bool     `json:"revoked"`
}

func (g Gateway) Validate() error {
	if !ValidID(g.ID) || !ValidName(g.Name) || len(g.Services) < 1 || len(g.Services) > MaxWorkloads {
		return errors.New("GATEWAY_INVALID")
	}
	seen := map[string]bool{}
	for _, s := range g.Services {
		if !ValidName(s) || seen[s] {
			return errors.New("GATEWAY_SERVICE_INVALID")
		}
		seen[s] = true
	}
	return nil
}
func (g Gateway) Allows(service string) bool {
	for _, s := range g.Services {
		if s == service {
			return !g.Revoked
		}
	}
	return false
}
func (g *Gateway) Normalize() { sort.Strings(g.Services) }
