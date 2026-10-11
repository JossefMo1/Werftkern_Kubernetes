package cli

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/control"
	"github.com/JossefMo1/Werftkern_Kubernetes/internal/model"
	"os"
)

func volumeCommand(ctx context.Context, args []string) error {
	if len(args) < 1 {
		return errors.New("volume list | create NAME --node ID --uid 999 --gid 999 | release NAME --id ID")
	}
	if args[0] == "backup" || args[0] == "restore" {
		return volumeArchiveCommand(ctx, args)
	}
	c, e := client()
	if e != nil {
		return e
	}
	switch args[0] {
	case "list":
		s, e := c.State(ctx)
		if e != nil {
			return e
		}
		return json.NewEncoder(os.Stdout).Encode(s.Volumes)
	case "create":
		if len(args) < 2 {
			return errors.New("VOLUME_NAME_REQUIRED")
		}
		f := parser("volume create")
		node := f.String("node", "", "Node ID")
		uid := f.Int("uid", 65532, "Container UID")
		gid := f.Int("gid", 65532, "Container GID")
		if e = f.Parse(args[2:]); e != nil {
			return e
		}
		var out model.Volume
		e = c.Call(ctx, "POST", "/v1/volumes", control.VolumeCreate{Name: args[1], NodeID: *node, UID: *uid, GID: *gid}, &out, model.ID())
		if e != nil {
			return e
		}
		return json.NewEncoder(os.Stdout).Encode(out)
	case "release":
		if len(args) < 2 {
			return errors.New("VOLUME_NAME_REQUIRED")
		}
		f := parser("volume release")
		id := f.String("id", "", "Volume identity confirmation")
		if e = f.Parse(args[2:]); e != nil {
			return e
		}
		return c.Call(ctx, "POST", "/v1/volumes/"+args[1]+"/release", map[string]string{"id": *id}, nil, model.ID())
	}
	return errors.New("VOLUME_ACTION_UNSUPPORTED")
}
func databaseCommand(ctx context.Context, args []string) error {
	if len(args) < 2 || args[0] != "manifest" {
		return errors.New("database manifest NAME --image DIGEST --node ID --volume NAME --password-version N; backup/restore: werft-ops postgres")
	}
	f := parser("database manifest")
	image := f.String("image", "", "PostgreSQL 17 image digest")
	node := f.String("node", "", "Node ID")
	vol := f.String("volume", "", "Registered local volume")
	ver := f.Int("password-version", 1, "postgres-password secret version")
	uid := f.Int("uid", 999, "Verified image UID/GID")
	if e := f.Parse(args[2:]); e != nil {
		return e
	}
	q := model.ApplyRequest{APIVersion: model.APIVersion, Name: args[1], Spec: model.Spec{Image: *image, Replicas: 1, CPUMilli: 1000, MemoryMiB: 1024, Node: *node, Port: 5432, Probe: "postgres", Profile: "postgres17", RunAsUID: *uid, RunAsGID: *uid, Volumes: []model.VolumeRef{{Name: *vol, MountPath: "/var/lib/postgresql/data"}}, Secrets: []model.SecretRef{{Name: "postgres-password", Version: *ver}}}}
	if !model.ValidName(q.Name) {
		return errors.New("NAME_INVALID")
	}
	if e := q.Spec.Validate(); e != nil {
		return e
	}
	fmt.Fprintln(os.Stderr, "Single-primary, node-bound profile. No database HA or automatic volume migration. Verify image major version and UID before applying.")
	return json.NewEncoder(os.Stdout).Encode(q)
}
