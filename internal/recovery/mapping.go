package recovery

import (
	"errors"
	"github.com/ClusterPilot-System/werftkern/internal/model"
)

// RestoreMapping only remaps references. It NEVER claims that a target volume's
// bytes, database consistency, fencing or application traffic have been restored.
type RestoreMapping struct {
	Nodes   map[string]string `json:"nodes"`
	Volumes map[string]string `json:"volumes"`
}

func mapSpec(spec model.Spec, target *model.State, m RestoreMapping) (model.Spec, error) {
	if spec.Node != "" {
		if n, ok := m.Nodes[spec.Node]; ok {
			if target.Nodes[n] == nil {
				return spec, errors.New("RESTORE_TARGET_NODE_NOT_FOUND")
			}
			spec.Node = n
		} else if len(spec.Volumes) > 0 {
			return spec, errors.New("STATEFUL_RESTORE_REQUIRES_NODE_MAPPING")
		}
	}
	spec.Volumes = append([]model.VolumeRef{}, spec.Volumes...)
	for i, ref := range spec.Volumes {
		name, ok := m.Volumes[ref.Name]
		if !ok {
			return spec, errors.New("STATEFUL_RESTORE_REQUIRES_VOLUME_MAPPING")
		}
		v := target.Volumes[name]
		if v == nil || v.NodeID != spec.Node || v.Owner != "" {
			return spec, errors.New("RESTORE_VOLUME_NOT_FREE_OR_NODE_MISMATCH")
		}
		spec.Volumes[i].Name = name
	}
	return spec, spec.Validate()
}
