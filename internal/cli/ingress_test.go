
package cli

import (
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/JossefMo1/Werftkern_Kubernetes/internal/config"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/ingress"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
)

func TestGatewayIngressExampleIsDeterministicAndScoped(t *testing.T) {
	cluster := model.ID()
	state := model.NewState(cluster, "gateway-test", time.Unix(0, 0))
	first, second := strings.Repeat("1", 32), strings.Repeat("2", 32)
	state.Nodes[first] = &model.Node{ID: first, Address: "127.0.0.1", PodCIDR: "10.0.0.0/24"}
	state.Nodes[second] = &model.Node{ID: second, Address: "127.0.0.1", PodCIDR: "10.0.1.0/24"}
	q := model.Gateway{ID: model.ID(), Services: []string{"api", "web"}}
	admin := config.Client{ClusterID: cluster, CA: "ca.crt", Cert: "gateway.crt", Key: "gateway.key"}

	got := gatewayIngressExample(q, admin, state)
	wantCIDRs := []string{"127.0.0.1/32", "10.0.0.0/24", "10.0.1.0/24"}
	if !reflect.DeepEqual(got.AllowedCIDRs, wantCIDRs) {
		t.Fatalf("allowed CIDRs = %#v, want %#v", got.AllowedCIDRs, wantCIDRs)
	}
	wantRoutes := []ingress.Route{{Host: "api.example.invalid", Service: "api"}, {Host: "web.example.invalid", Service: "web"}}
	if !reflect.DeepEqual(got.Routes, wantRoutes) {
		t.Fatalf("routes = %#v, want %#v", got.Routes, wantRoutes)
	}
	if got.GatewayID != q.ID || !reflect.DeepEqual(got.Client, admin) {
		t.Fatalf("gateway identity/client changed: %#v", got)
	}
}
