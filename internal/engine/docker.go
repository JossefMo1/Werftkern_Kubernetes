package engine

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

const clusterLabel = "org.werftkern.runtime.cluster"
const allocationLabel = "org.werftkern.runtime.allocation"
const specLabel = "org.werftkern.runtime.spec"

var ErrStale = errors.New("ALLOCATION_SUPERSEDED")

type Docker struct {
	Network            string
	Volumes            VolumeSource
	VolumeAck          VolumeAcknowledge
	VolumeRoot         string
	DNS                []string
	Client             *http.Client
	ClusterID          string
	Secrets            SecretSource
	SecretRoot         string
	RequireSecretTmpfs bool
	mu                 sync.Mutex
	api                string
}

func NewDocker(socket, cluster string) *Docker {
	tr := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{Timeout: 5 * time.Second}).DialContext(ctx, "unix", socket)
	}, MaxIdleConnsPerHost: 8, ResponseHeaderTimeout: 15 * time.Second}
	return &Docker{Client: &http.Client{Transport: tr, Timeout: 4 * time.Minute}, ClusterID: cluster, SecretRoot: DefaultSecretRoot, RequireSecretTmpfs: true}
}
func (d *Docker) name(id string) string { return "cpr-" + d.ClusterID[:8] + "-" + id }
func (d *Docker) raw(ctx context.Context, method, path string, body io.Reader) (*http.Response, error) {
	r, e := http.NewRequestWithContext(ctx, method, "http://docker"+path, body)
	if e != nil {
		return nil, e
	}
	r.Header.Set("Content-Type", "application/json")
	resp, e := d.Client.Do(r)
	if e != nil {
		return nil, errors.New("CONTAINER_ENGINE_UNREACHABLE")
	}
	return resp, nil
}
func apiNumber(v string) (int, error) {
	var major, minor int
	_, e := fmt.Sscanf(v, "%d.%d", &major, &minor)
	if e != nil || major != 1 {
		return 0, errors.New("ENGINE_API_UNSUPPORTED")
	}
	return minor, nil
}
func (d *Docker) version(ctx context.Context) (string, error) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.api != "" {
		return d.api, nil
	}
	r, e := d.raw(ctx, "GET", "/version", nil)
	if e != nil {
		return "", e
	}
	defer r.Body.Close()
	if r.StatusCode != 200 {
		return "", errors.New("ENGINE_VERSION_FAILED")
	}
	var v struct {
		APIVersion string `json:"ApiVersion"`
		Minimum    string `json:"MinAPIVersion"`
	}
	if e = json.NewDecoder(io.LimitReader(r.Body, 65536)).Decode(&v); e != nil {
		return "", e
	}
	max, e := apiNumber(v.APIVersion)
	if e != nil {
		return "", e
	}
	min := 12
	if v.Minimum != "" {
		min, e = apiNumber(v.Minimum)
		if e != nil {
			return "", e
		}
	}
	chosen := max
	if chosen > 51 {
		chosen = 51
	}
	if chosen < 41 || min > chosen {
		return "", errors.New("ENGINE_API_OUTSIDE_QUALIFICATION_RANGE")
	}
	d.api = "/v1." + strconv.Itoa(chosen)
	return d.api, nil
}
func (d *Docker) request(ctx context.Context, method, path string, in any, out any) (int, error) {
	v, e := d.version(ctx)
	if e != nil {
		return 0, e
	}
	var b io.Reader
	if in != nil {
		raw, e := json.Marshal(in)
		if e != nil {
			return 0, e
		}
		b = bytes.NewReader(raw)
	}
	r, e := d.raw(ctx, method, v+path, b)
	if e != nil {
		return 0, e
	}
	defer r.Body.Close()
	if r.StatusCode >= 400 {
		io.Copy(io.Discard, io.LimitReader(r.Body, 4096))
		return r.StatusCode, fmt.Errorf("ENGINE_HTTP_%d", r.StatusCode)
	}
	if out != nil {
		e = json.NewDecoder(io.LimitReader(r.Body, 4<<20)).Decode(out)
	} else {
		_, e = io.Copy(io.Discard, io.LimitReader(r.Body, 4096))
	}
	return r.StatusCode, e
}
func (d *Docker) Health(ctx context.Context) error {
	_, e := d.request(ctx, "GET", "/info", nil, nil)
	return e
}

type inspection struct {
	NetworkSettings struct {
		Networks map[string]struct {
			IPAddress string `json:"IPAddress"`
		} `json:"Networks"`
	} `json:"NetworkSettings"`
	ID     string `json:"Id"`
	Image  string `json:"Image"`
	Config struct {
		Image   string            `json:"Image"`
		Labels  map[string]string `json:"Labels"`
		Volumes map[string]any    `json:"Volumes"`
	} `json:"Config"`
	State struct {
		Running    bool   `json:"Running"`
		Restarting bool   `json:"Restarting"`
		Status     string `json:"Status"`
		ExitCode   int    `json:"ExitCode"`
	} `json:"State"`
}

func (d *Docker) inspect(ctx context.Context, id string) (inspection, int, error) {
	var c inspection
	status, e := d.request(ctx, "GET", "/containers/"+d.name(id)+"/json", nil, &c)
	return c, status, e
}
func (d *Docker) owned(c inspection, id string) bool {
	return c.Config.Labels[clusterLabel] == d.ClusterID && c.Config.Labels[allocationLabel] == id
}
func (d *Docker) image(ctx context.Context, image string, refs []model.VolumeRef) error {
	covered := func(volumes map[string]any) bool {
		for p := range volumes {
			found := false
			for _, v := range refs {
				if p == v.MountPath {
					found = true
				}
			}
			if !found {
				return false
			}
		}
		return true
	}
	var meta inspection
	status, e := d.request(ctx, "GET", "/images/"+url.PathEscape(image)+"/json", nil, &meta)
	if e == nil {
		if !covered(meta.Config.Volumes) {
			return errors.New("IMAGE_VOLUME_DECLARATIONS_UNSUPPORTED")
		}
		return nil
	}
	if status != 404 {
		return e
	}
	if strings.HasPrefix(image, "sha256:") {
		return errors.New("LOCAL_IMAGE_NOT_FOUND")
	}
	v, e := d.version(ctx)
	if e != nil {
		return e
	}
	r, e := d.raw(ctx, "POST", v+"/images/create?"+url.Values{"fromImage": {image}}.Encode(), nil)
	if e != nil {
		return e
	}
	defer r.Body.Close()
	if r.StatusCode != 200 {
		return errors.New("IMAGE_PULL_FAILED")
	}
	decoder := json.NewDecoder(io.LimitReader(r.Body, 8<<20))
	for {
		var x struct {
			Error string `json:"error"`
		}
		e = decoder.Decode(&x)
		if e == io.EOF {
			break
		}
		if e != nil {
			return errors.New("IMAGE_PULL_STREAM_INVALID")
		}
		if x.Error != "" {
			return errors.New("IMAGE_PULL_FAILED")
		}
	}
	_, e = d.request(ctx, "GET", "/images/"+url.PathEscape(image)+"/json", nil, &meta)
	if e != nil {
		return errors.New("IMAGE_PULL_VERIFICATION_FAILED")
	}
	if !covered(meta.Config.Volumes) {
		return errors.New("IMAGE_VOLUME_DECLARATIONS_UNSUPPORTED")
	}
	return nil
}
func (d *Docker) Ensure(ctx context.Context, a model.Allocation, address string, allowed func() bool) (model.Report, error) {
	report := model.Report{ID: a.ID, Phase: "starting"}
	if !model.ValidID(a.ID) || !model.PrivateAddress(address) || a.Spec.Port > 0 && (a.HostPort < 22000 || a.HostPort >= 23000) || a.Spec.Port == 0 && a.HostPort != 0 {
		return report, errors.New("ALLOCATION_INVALID")
	}
	if e := a.Spec.Validate(); e != nil {
		return report, e
	}
	if len(a.Spec.Volumes) > 0 {
		root := d.VolumeRoot
		if root == "" {
			root = DefaultVolumeRoot
		}
		lock, e := safefile.DirectoryLock(root, false)
		if e != nil {
			return report, e
		}
		defer lock.Close()
	}

	if !allowed() {
		return report, ErrStale
	}
	c, status, e := d.inspect(ctx, a.ID)
	if status == 404 {
		if e = d.image(ctx, a.Spec.Image, a.Spec.Volumes); e != nil {
			return report, e
		}
		if !allowed() {
			return report, ErrStale
		}
		volumeBinds, err := d.volumeBinds(ctx, a)
		if err != nil {
			return report, err
		}
		secretDir, err := d.secretDirectory(ctx, a)
		if err != nil {
			return report, err
		}
		body := map[string]any{"Image": a.Spec.Image, "User": userString(a.Spec), "Labels": map[string]string{clusterLabel: d.ClusterID, allocationLabel: a.ID, specLabel: model.Hash(a.Spec)}, "HostConfig": map[string]any{
			"ReadonlyRootfs": true, "CapDrop": []string{"ALL"}, "SecurityOpt": []string{"no-new-privileges:true"}, "Privileged": false, "NetworkMode": "bridge",
			"Memory": a.Spec.MemoryMiB * 1024 * 1024, "MemorySwap": a.Spec.MemoryMiB * 1024 * 1024, "CpuPeriod": 100000, "CpuQuota": a.Spec.CPUMilli * 100, "PidsLimit": 256,
			"RestartPolicy": map[string]any{"Name": "unless-stopped"}, "Tmpfs": map[string]string{"/tmp": "rw,noexec,nosuid,size=64m,uid=65532,gid=65532"},
			"LogConfig": map[string]any{"Type": "json-file", "Config": map[string]string{"max-size": "5m", "max-file": "2"}},
		}}
		if d.Network != "" {
			if d.Network != "werft" {
				return report, errors.New("NETWORK_NOT_ALLOWLISTED")
			}
			body["HostConfig"].(map[string]any)["NetworkMode"] = d.Network
		}
		if len(d.DNS) > 0 {
			for _, ip := range d.DNS {
				if !model.PrivateAddress(ip) {
					return report, errors.New("PRIVATE_DNS_ADDRESS_REQUIRED")
				}
			}
			body["HostConfig"].(map[string]any)["Dns"] = d.DNS
		}
		if len(volumeBinds) > 0 {
			body["HostConfig"].(map[string]any)["Binds"] = volumeBinds
			body["HostConfig"].(map[string]any)["RestartPolicy"] = map[string]any{"Name": "no"}
		}
		if a.Spec.Profile == "postgres17" {
			body["Env"] = []string{"POSTGRES_PASSWORD_FILE=/run/secrets/postgres-password", "PGDATA=/var/lib/postgresql/data/pgdata", "POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256"}
			u, g := a.Spec.User()
			body["HostConfig"].(map[string]any)["Tmpfs"].(map[string]string)["/var/run/postgresql"] = fmt.Sprintf("rw,nosuid,noexec,size=16m,uid=%d,gid=%d", u, g)
		}
		if secretDir != "" {
			body["HostConfig"].(map[string]any)["Binds"] = append(volumeBinds, secretDir+":/run/secrets:ro,rprivate")
			// After a host reboot tmpfs is empty. Only the agent may restart
			// secret-bearing containers, after re-materializing their files.
			body["HostConfig"].(map[string]any)["RestartPolicy"] = map[string]any{"Name": "no"}
		}
		if len(a.Spec.Command) > 0 {
			body["Entrypoint"] = a.Spec.Command
			body["Cmd"] = []string{}
		}
		if a.Spec.Port > 0 {
			p := strconv.Itoa(a.Spec.Port) + "/tcp"
			body["ExposedPorts"] = map[string]any{p: map[string]any{}}
			body["HostConfig"].(map[string]any)["PortBindings"] = map[string]any{p: []map[string]string{{"HostIp": address, "HostPort": strconv.Itoa(a.HostPort)}}}
		}
		_, e = d.request(ctx, "POST", "/containers/create?"+url.Values{"name": {d.name(a.ID)}}.Encode(), body, nil)
		if e != nil {
			c, status, e = d.inspect(ctx, a.ID)
			if e != nil {
				return report, errors.New("CONTAINER_CREATE_FAILED")
			}
		} else {
			c, status, e = d.inspect(ctx, a.ID)
		}
	}
	if e != nil {
		return report, e
	}
	if !d.owned(c, a.ID) || c.Config.Labels[specLabel] != model.Hash(a.Spec) {
		return report, errors.New("CONTAINER_OWNERSHIP_CONFLICT")
	}
	if !allowed() {
		return report, ErrStale
	}
	if !c.State.Running {
		if _, err := d.volumeBinds(ctx, a); err != nil {
			return report, err
		}
		if _, err := d.secretDirectory(ctx, a); err != nil {
			return report, err
		}
		if _, e = d.request(ctx, "POST", "/containers/"+d.name(a.ID)+"/start", nil, nil); e != nil {
			return report, errors.New("CONTAINER_START_FAILED")
		}
		c, _, e = d.inspect(ctx, a.ID)
		if e != nil {
			return report, e
		}
	}
	if !c.State.Running || c.State.Restarting {
		report.Reason = "PROCESS_NOT_RUNNING"
		return report, nil
	}
	if a.Spec.Probe == "tcp" {
		conn, e := net.DialTimeout("tcp", net.JoinHostPort(address, strconv.Itoa(a.HostPort)), 2*time.Second)
		if e != nil {
			report.Reason = "TCP_NOT_READY"
			return report, nil
		}
		conn.Close()
	}
	if a.Spec.Probe == "postgres" && !d.postgresReady(ctx, a.ID) {
		report.Reason = "POSTGRES_NOT_READY"
		return report, nil
	}
	if a.Spec.ReadinessPath != "" {
		checkCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
		defer cancel()
		r, e := http.NewRequestWithContext(checkCtx, "GET", "http://"+net.JoinHostPort(address, strconv.Itoa(a.HostPort))+a.Spec.ReadinessPath, nil)
		if e != nil {
			return report, e
		}
		h := &http.Client{Transport: &http.Transport{Proxy: nil, DialContext: (&net.Dialer{Timeout: time.Second}).DialContext, DisableKeepAlives: true}, Timeout: 2 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
		resp, e := h.Do(r)
		if e != nil {
			report.Reason = "READINESS_UNREACHABLE"
			return report, nil
		}
		io.Copy(io.Discard, io.LimitReader(resp.Body, 4096))
		resp.Body.Close()
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			report.Reason = "READINESS_NOT_SUCCESSFUL"
			return report, nil
		}
	}
	if d.Network != "" {
		ip := c.NetworkSettings.Networks[d.Network].IPAddress
		if !model.PrivateAddress(ip) {
			return report, errors.New("ROUTED_CONTAINER_IP_UNAVAILABLE")
		}
		report.ContainerIP = ip
	}
	report.Phase = "ready"
	if a.Spec.Port == 0 {
		report.Reason = "PROCESS_RUNNING_ONLY"
	}
	return report, nil
}
func (d *Docker) Stop(ctx context.Context, id string) error {
	if !model.ValidID(id) {
		return errors.New("ALLOCATION_ID_INVALID")
	}
	c, status, e := d.inspect(ctx, id)
	if status == 404 {
		return d.removeSecrets(id)
	}
	if e != nil {
		return e
	}
	if !d.owned(c, id) {
		return errors.New("CONTAINER_OWNERSHIP_CONFLICT")
	}
	if c.State.Running {
		status, e = d.request(ctx, "POST", "/containers/"+d.name(id)+"/stop?t=10", nil, nil)
		if e != nil && status != 304 && status != 404 {
			return e
		}
	}
	status, e = d.request(ctx, "DELETE", "/containers/"+d.name(id)+"?v=true", nil, nil)
	if status == 404 {
		return d.removeSecrets(id)
	}
	if e != nil {
		return e
	}
	return d.removeSecrets(id)
}
func (d *Docker) Owned(ctx context.Context) ([]string, error) {
	filters, _ := json.Marshal(map[string][]string{"label": {clusterLabel + "=" + d.ClusterID}})
	var out []struct {
		Labels map[string]string `json:"Labels"`
	}
	_, e := d.request(ctx, "GET", "/containers/json?all=true&"+url.Values{"filters": {string(filters)}}.Encode(), nil, &out)
	if e != nil {
		return nil, e
	}
	ids := []string{}
	for _, c := range out {
		id := c.Labels[allocationLabel]
		if c.Labels[clusterLabel] == d.ClusterID && model.ValidID(id) {
			ids = append(ids, id)
		}
	}
	return ids, nil
}
func (d *Docker) Load(ctx context.Context, path string) error {
	v, e := d.version(ctx)
	if e != nil {
		return e
	}
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	r, e := http.NewRequestWithContext(ctx, "POST", "http://docker"+v+"/images/load?quiet=true", f)
	if e != nil {
		return e
	}
	r.Header.Set("Content-Type", "application/x-tar")
	resp, e := d.Client.Do(r)
	if e != nil {
		return errors.New("DEMO_IMAGE_LOAD_FAILED")
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return errors.New("DEMO_IMAGE_LOAD_FAILED")
	}
	dec := json.NewDecoder(io.LimitReader(resp.Body, 1<<20))
	for {
		var m struct {
			Error string `json:"error"`
		}
		e := dec.Decode(&m)
		if e == io.EOF {
			return nil
		}
		if e != nil || m.Error != "" {
			return errors.New("DEMO_IMAGE_LOAD_FAILED")
		}
	}
}
func (d *Docker) Logs(ctx context.Context, id string) ([]byte, error) {
	c, _, e := d.inspect(ctx, id)
	if e != nil {
		return nil, e
	}
	if !d.owned(c, id) {
		return nil, errors.New("CONTAINER_OWNERSHIP_CONFLICT")
	}
	v, e := d.version(ctx)
	if e != nil {
		return nil, e
	}
	r, e := d.raw(ctx, "GET", v+"/containers/"+d.name(id)+"/logs?stdout=true&stderr=true&tail=100", nil)
	if e != nil {
		return nil, e
	}
	defer r.Body.Close()
	if r.StatusCode != 200 {
		return nil, errors.New("LOG_READ_FAILED")
	}
	return io.ReadAll(io.LimitReader(r.Body, 65536))
}
