package engine

import (
	"context"
	"errors"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/safefile"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const DefaultVolumeRoot = "/var/lib/werftkern/volumes"

type VolumeSource func(context.Context, model.Allocation) ([]model.Volume, error)
type VolumeAcknowledge func(context.Context, model.Allocation, string) error
type volumeIdentity struct {
	ID        string `json:"id"`
	ClusterID string `json:"clusterId"`
	NodeID    string `json:"nodeId"`
	UID       int    `json:"uid"`
	GID       int    `json:"gid"`
}

func noSymlinkPath(path string) error {
	p := filepath.Clean(path)
	for {
		st, e := os.Lstat(p)
		if e != nil {
			return e
		}
		if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return errors.New("VOLUME_PATH_UNSAFE")
		}
		next := filepath.Dir(p)
		if next == p {
			break
		}
		p = next
	}
	return nil
}
func (d *Docker) volumeBinds(ctx context.Context, a model.Allocation) ([]string, error) {
	if len(a.Spec.Volumes) == 0 {
		return nil, nil
	}
	if d.Volumes == nil || d.VolumeAck == nil {
		return nil, errors.New("VOLUME_PROVIDER_UNAVAILABLE")
	}
	volumes, e := d.Volumes(ctx, a)
	if e != nil {
		return nil, e
	}
	if len(volumes) != len(a.Spec.Volumes) {
		return nil, errors.New("VOLUME_SET_MISMATCH")
	}
	root := d.VolumeRoot
	if root == "" {
		root = DefaultVolumeRoot
	}
	if !filepath.IsAbs(root) || strings.ContainsAny(root, ":\n\r") {
		return nil, errors.New("VOLUME_ROOT_INVALID")
	}
	if e = os.MkdirAll(root, 0700); e != nil {
		return nil, e
	}
	if e = noSymlinkPath(root); e != nil {
		return nil, e
	}
	st, e := os.Stat(root)
	if e != nil || st.Mode().Perm() != 0700 {
		return nil, errors.New("VOLUME_ROOT_NOT_PRIVATE")
	}
	out := []string{}
	for _, ref := range a.Spec.Volumes {
		var found *model.Volume
		for i := range volumes {
			if volumes[i].Name == ref.Name {
				found = &volumes[i]
			}
		}
		if found == nil || found.Validate() != nil || found.NodeID != a.NodeID || found.Owner != a.WorkloadUID {
			return nil, errors.New("VOLUME_SCOPE_DENIED")
		}
		v := *found
		if v.RestoreID != "" && !v.RestoreComplete {
			return nil, errors.New("VOLUME_RESTORE_PENDING")
		}
		expected := volumeIdentity{v.ID, d.ClusterID, v.NodeID, v.UID, v.GID}
		dir := filepath.Join(root, v.ID)
		data := filepath.Join(dir, "data")
		if _, e = os.Lstat(dir); os.IsNotExist(e) {
			if v.Initialized {
				return nil, errors.New("INITIALIZED_VOLUME_MISSING_REFUSING_EMPTY_REPLACEMENT")
			}
			stage, e := os.MkdirTemp(root, ".volume-")
			if e != nil {
				return nil, e
			}
			e = func() error {
				defer os.RemoveAll(stage)
				if e := os.Mkdir(filepath.Join(stage, "data"), 0700); e != nil {
					return e
				}
				if e := os.Chown(filepath.Join(stage, "data"), v.UID, v.GID); e != nil {
					return e
				}
				if e := safefile.JSON(filepath.Join(stage, "identity.json"), expected, 0600); e != nil {
					return e
				}
				if e := os.Rename(stage, dir); e != nil {
					return e
				}
				f, e := os.Open(root)
				if e != nil {
					return e
				}
				defer f.Close()
				return f.Sync()
			}()
			if e != nil {
				return nil, e
			}
		} else if e != nil {
			return nil, e
		}
		if e = noSymlinkPath(data); e != nil {
			return nil, errors.New("VOLUME_DATA_UNAVAILABLE_OR_SYMLINK")
		}
		var got volumeIdentity
		if e = safefile.ReadJSON(filepath.Join(dir, "identity.json"), &got); e != nil || got != expected {
			return nil, errors.New("VOLUME_IDENTITY_MISMATCH")
		}
		if !v.Initialized {
			if e = d.VolumeAck(ctx, a, v.Name); e != nil {
				return nil, e
			}
		}
		mode := "rw"
		if ref.ReadOnly {
			mode = "ro"
		}
		out = append(out, data+":"+ref.MountPath+":"+mode+",rprivate")
	}
	return out, nil
}
func (d *Docker) postgresReady(ctx context.Context, id string) bool {
	var result struct {
		ID string `json:"Id"`
	}
	_, e := d.request(ctx, "POST", "/containers/"+d.name(id)+"/exec", map[string]any{"AttachStdout": false, "AttachStderr": false, "Cmd": []string{"pg_isready", "-q", "-h", "127.0.0.1", "-p", "5432", "-U", "postgres"}}, &result)
	if e != nil || result.ID == "" {
		return false
	}
	// Docker exec IDs must never be interpreted as paths.
	if strings.ContainsAny(result.ID, "/?#\n\r") {
		return false
	}
	if _, e = d.request(ctx, "POST", "/exec/"+result.ID+"/start", map[string]any{"Detach": false, "Tty": false}, nil); e != nil {
		return false
	}
	var st struct {
		Running  bool `json:"Running"`
		ExitCode int  `json:"ExitCode"`
	}
	_, e = d.request(ctx, "GET", "/exec/"+result.ID+"/json", nil, &st)
	return e == nil && !st.Running && st.ExitCode == 0
}
func userString(s model.Spec) string {
	u, g := s.User()
	return strconv.Itoa(u) + ":" + strconv.Itoa(g)
}

// AssertVolumeOffline inspects all containers, including foreign ones. A running
// or restartable mount overlapping this data tree blocks maintenance. No stop or
// delete is performed on a foreign resource.
func (d *Docker) AssertVolumeOffline(ctx context.Context, data string) error {
	var list []struct {
		ID string `json:"Id"`
	}
	if _, e := d.request(ctx, "GET", "/containers/json?all=1", nil, &list); e != nil {
		return e
	}
	data = filepath.Clean(data)
	if !filepath.IsAbs(data) {
		return errors.New("VOLUME_DATA_PATH_MUST_BE_ABSOLUTE")
	}
	for _, item := range list {
		if !model.ValidSHA256(item.ID) {
			return errors.New("ENGINE_CONTAINER_ID_INVALID")
		}
		var info struct {
			Mounts []struct {
				Source string `json:"Source"`
			} `json:"Mounts"`
			State struct {
				Running    bool `json:"Running"`
				Restarting bool `json:"Restarting"`
			} `json:"State"`
			HostConfig struct {
				RestartPolicy struct {
					Name string `json:"Name"`
				} `json:"RestartPolicy"`
			} `json:"HostConfig"`
		}
		if _, e := d.request(ctx, "GET", "/containers/"+item.ID+"/json", nil, &info); e != nil {
			return e
		}
		if !info.State.Running && !info.State.Restarting && (info.HostConfig.RestartPolicy.Name == "no" || info.HostConfig.RestartPolicy.Name == "") {
			continue
		}
		for _, m := range info.Mounts {
			if m.Source == "" {
				continue
			} // tmpfs has no source tree on the host.
			p := filepath.Clean(m.Source)
			if !filepath.IsAbs(p) {
				return errors.New("VOLUME_MOUNT_SOURCE_UNRESOLVED")
			}
			if canonical, e := filepath.EvalSymlinks(p); e == nil {
				p = canonical
			}
			if overlappingPaths(p, data) {
				return errors.New("VOLUME_MOUNTED_BY_RUNNING_OR_RESTARTABLE_CONTAINER")
			}
		}
	}
	return nil
}

// filepath.Rel handles a mount of / correctly; a naive prefix + "/" does not.
func overlappingPaths(a, b string) bool {
	within := func(parent, child string) bool {
		r, e := filepath.Rel(parent, child)
		return e == nil && r != ".." && !strings.HasPrefix(r, ".."+string(filepath.Separator))
	}
	return within(a, b) || within(b, a)
}
