package cli

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"sort"

	"github.com/ClusterPilot-System/werftkern/internal/apiclient"
	"github.com/ClusterPilot-System/werftkern/internal/config"
	"github.com/ClusterPilot-System/werftkern/internal/model"
)

type ControllerHealth struct {
	SupportedAgentVersions []string `json:"supportedAgentVersions"`
	Endpoint               string   `json:"endpoint"`
	Status                 string   `json:"status"`
	ClusterID              string   `json:"clusterId"`
	Version                string   `json:"version"`
	StateSchema            int      `json:"stateSchema"`
	Maturity               string   `json:"maturity"`
}

// Every configured endpoint is contacted directly: failover to a healthy peer
// must not hide a broken or old controller during update qualification.
func CheckControllers(ctx context.Context, c config.Client, expected string) ([]ControllerHealth, error) {
	if e := config.ValidateClient(c); e != nil {
		return nil, e
	}
	unique := map[string]bool{c.Server: true}
	for _, s := range c.Servers {
		unique[s] = true
	}
	endpoints := make([]string, 0, len(unique))
	for s := range unique {
		endpoints = append(endpoints, s)
	}
	sort.Strings(endpoints)
	result := make([]ControllerHealth, 0, len(endpoints))
	for _, server := range endpoints {
		single := c
		single.Server = server
		single.Servers = nil
		client, e := apiclient.New(single)
		if e != nil {
			return nil, e
		}
		var observed ControllerHealth
		e = client.Call(ctx, "GET", "/v1/health", nil, &observed, "")
		client.HTTP.CloseIdleConnections()
		if e != nil {
			return nil, errors.New("CONTROLLER_ENDPOINT_NOT_HEALTHY")
		}
		if observed.Status != "ready" || observed.ClusterID != c.ClusterID || observed.Version != expected || observed.StateSchema != model.StateSchema {
			return nil, errors.New("CONTROLLER_IDENTITY_VERSION_OR_SCHEMA_MISMATCH")
		}
		observed.Endpoint = server
		result = append(result, observed)
	}
	return result, nil
}
func healthCommand(ctx context.Context, args []string) error {
	f := parser("health")
	all := f.Bool("all", false, "Check every configured endpoint directly")
	expected := f.String("expected-version", model.Version, "Required version at every endpoint")
	jsonOutput := f.Bool("json", false, "Structured output")
	if e := f.Parse(args); e != nil {
		return e
	}
	if f.NArg() != 0 || !*all || !*jsonOutput {
		return errors.New("health --all --json [--expected-version VERSION]")
	}
	c, e := config.Load[config.Client](config.AdminPath())
	if e != nil {
		return e
	}
	h, e := CheckControllers(ctx, c, *expected)
	if e != nil {
		return e
	}
	return json.NewEncoder(os.Stdout).Encode(map[string]any{"clusterId": c.ClusterID, "controllers": h, "productionQualified": false})
}
