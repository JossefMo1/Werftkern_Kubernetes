#!/usr/bin/env python3
"""Fail-closed static security audit for the exact hcloud CSI render.

Passing this checker means the documented privilege boundary and open hardening
gaps still match the reviewed manifest. It never turns those gaps into a
production or runtime security claim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "release/hcloud-csi-security-policy.json"
EXPECTED_MANIFEST_SHA = "09d55e336a2cfa5de96ab46af8cc588e6af43dee8f9d4782801bf60bf01526bf"
EXPECTED_RBAC_SHA = "900eee9afc2761185fe4e5346cd16c3efc0b4d1dad0b4a6024b0f862d18597e3"
EXPECTED_GAPS = [
    "CONTAINER_SECURITY_CONTEXTS_NOT_ENFORCED",
    "RESOURCE_REQUESTS_AND_LIMITS_EMPTY",
]
EXPECTED_POD_SECCOMP_PROFILE = {"type": "RuntimeDefault"}
EXPECTED_HOST_PATHS = [
    {"name": "kubelet-dir", "path": "/var/lib/k0s/kubelet", "type": "Directory"},
    {
        "name": "plugin-dir",
        "path": "/var/lib/k0s/kubelet/plugins/csi.hetzner.cloud/",
        "type": "DirectoryOrCreate",
    },
    {
        "name": "registration-dir",
        "path": "/var/lib/k0s/kubelet/plugins_registry/",
        "type": "Directory",
    },
    {"name": "device-dir", "path": "/dev", "type": "Directory"},
]


def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    value: dict = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = item
    return value


def parse_json(raw: str) -> dict:
    value = json.loads(raw, object_pairs_hook=no_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError("top-level policy must be an object")
    return value


def canonical_sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def resource_key(document: dict) -> tuple[str, str, str]:
    metadata = document.get("metadata", {})
    return (
        str(document.get("kind", "")),
        str(metadata.get("namespace", "")),
        str(metadata.get("name", "")),
    )


def find_one(documents: list[dict], kind: str, name: str) -> dict:
    found = [
        item
        for item in documents
        if item.get("kind") == kind and item.get("metadata", {}).get("name") == name
    ]
    if len(found) != 1:
        raise ValueError(f"expected exactly one {kind}/{name}, found {len(found)}")
    return found[0]


def pod_spec(workload: dict) -> dict:
    return workload.get("spec", {}).get("template", {}).get("spec", {})


def host_paths(spec: dict) -> list[dict]:
    result = []
    for volume in spec.get("volumes", []):
        if "hostPath" not in volume:
            continue
        source = volume["hostPath"]
        result.append(
            {"name": volume.get("name"), "path": source.get("path"), "type": source.get("type")}
        )
    return result


def privileged_containers(spec: dict) -> list[str]:
    return sorted(
        item.get("name", "")
        for item in (spec.get("containers") or []) + (spec.get("initContainers") or [])
        if item.get("securityContext", {}).get("privileged") is True
    )


def bidirectional_mounts(spec: dict) -> list[str]:
    result = []
    for container in (spec.get("containers") or []) + (spec.get("initContainers") or []):
        for mount in container.get("volumeMounts", []):
            if mount.get("mountPropagation") == "Bidirectional":
                result.append(
                    f"{container.get('name')}:{mount.get('name')}:{mount.get('mountPath')}"
                )
    return sorted(result)


def secret_refs(spec: dict) -> list[str]:
    result = []
    for container in (spec.get("containers") or []) + (spec.get("initContainers") or []):
        for env in container.get("env", []):
            ref = env.get("valueFrom", {}).get("secretKeyRef")
            if isinstance(ref, dict):
                result.append(f"{ref.get('name')}/{ref.get('key')}")
    return sorted(result)


def validate_policy(policy: dict) -> list[str]:
    problems: list[str] = []
    if policy.get("schema") != "werftkern/hcloud-csi-static-security-policy/v1":
        problems.append("POLICY_SCHEMA_INVALID")
    if (
        policy.get("status")
        != "audited-blocked-container-and-resource-hardening-required"
    ):
        problems.append("POLICY_STATUS_MUST_REMAIN_BLOCKED")
    if policy.get("productionReady") is not False or policy.get("hardeningPassed") is not False:
        problems.append("POLICY_CANNOT_CLAIM_READINESS")
    if policy.get("manifest") != {
        "path": "release/evidence/hcloud-csi-2.24.2-render.yaml",
        "sha256": EXPECTED_MANIFEST_SHA,
    }:
        problems.append("POLICY_MANIFEST_IDENTITY_INVALID")
    rbac = policy.get("rbac", {})
    expected_rbac = {
        "clusterRole": "werftkern-hcloud-csi-controller",
        "ruleCount": 16,
        "canonicalRulesSha256": EXPECTED_RBAC_SHA,
        "wildcardsAllowed": False,
        "nonResourceUrlsAllowed": False,
        "secretResourceAccessAllowed": False,
        "binding": {
            "name": "werftkern-hcloud-csi-controller",
            "serviceAccount": "werftkern-hcloud-csi-controller",
            "namespace": "kube-system",
        },
    }
    if rbac != expected_rbac:
        problems.append("POLICY_RBAC_BOUNDARY_INVALID")
    workloads = policy.get("workloads", {})
    controller = workloads.get("controller", {})
    if controller != {
        "kind": "Deployment",
        "name": "werftkern-hcloud-csi-controller",
        "namespace": "kube-system",
        "serviceAccount": "werftkern-hcloud-csi-controller",
        "serviceAccountTokenMode": "service-account-explicit-true",
        "podSeccompProfile": EXPECTED_POD_SECCOMP_PROFILE,
        "hostNamespaces": False,
        "hostPaths": [],
        "privilegedContainers": [],
        "bidirectionalMounts": [],
        "secretRefs": ["hcloud/token"],
    }:
        problems.append("POLICY_CONTROLLER_BOUNDARY_INVALID")
    node = workloads.get("node", {})
    if node != {
        "kind": "DaemonSet",
        "name": "werftkern-hcloud-csi-node",
        "namespace": "kube-system",
        "serviceAccount": "werftkern-hcloud-csi-node",
        "serviceAccountTokenMode": "service-account-explicit-false",
        "podSeccompProfile": EXPECTED_POD_SECCOMP_PROFILE,
        "hostNamespaces": False,
        "hostPaths": EXPECTED_HOST_PATHS,
        "privilegedContainers": ["hcloud-csi-driver"],
        "bidirectionalMounts": ["hcloud-csi-driver:kubelet-dir:/var/lib/k0s/kubelet"],
    }:
        problems.append("POLICY_NODE_BOUNDARY_INVALID")
    if policy.get("observedHardeningGaps") != EXPECTED_GAPS:
        problems.append("POLICY_GAPS_INVALID")
    limitations = policy.get("limitations")
    if not isinstance(limitations, list) or len(limitations) < 5 or any(not item for item in limitations):
        problems.append("POLICY_LIMITATIONS_MISSING")
    return problems


def validate_manifest(policy: dict, raw: str) -> list[str]:
    problems: list[str] = []
    if hashlib.sha256(raw.encode()).hexdigest() != EXPECTED_MANIFEST_SHA:
        problems.append("MANIFEST_SHA256_MISMATCH")
    try:
        loaded = list(yaml.safe_load_all(raw))
    except yaml.YAMLError:
        return problems + ["MANIFEST_YAML_INVALID"]
    documents = [item for item in loaded if isinstance(item, dict)]
    keys = [resource_key(item) for item in documents]
    if len(keys) != len(set(keys)):
        problems.append("DUPLICATE_RESOURCE_IDENTITY")
    if any(item.get("kind") == "Secret" for item in documents):
        problems.append("MANIFEST_MUST_NOT_CREATE_SECRET")
    try:
        role = find_one(documents, "ClusterRole", policy["rbac"]["clusterRole"])
        binding = find_one(documents, "ClusterRoleBinding", policy["rbac"]["binding"]["name"])
        account = find_one(documents, "ServiceAccount", "werftkern-hcloud-csi-controller")
        node_account = find_one(documents, "ServiceAccount", "werftkern-hcloud-csi-node")
        controller = find_one(documents, "Deployment", "werftkern-hcloud-csi-controller")
        node = find_one(documents, "DaemonSet", "werftkern-hcloud-csi-node")
    except ValueError as exc:
        return problems + ["RESOURCE_CARDINALITY_INVALID:" + str(exc)]

    roles = [item for item in documents if item.get("kind") in {"Role", "ClusterRole"}]
    bindings = [
        item for item in documents if item.get("kind") in {"RoleBinding", "ClusterRoleBinding"}
    ]
    if len(roles) != 1 or len(bindings) != 1:
        problems.append("UNEXPECTED_RBAC_OBJECT")
    rules = role.get("rules", [])
    if len(rules) != policy["rbac"]["ruleCount"] or canonical_sha(rules) != EXPECTED_RBAC_SHA:
        problems.append("RBAC_RULESET_DRIFT")
    for rule in rules:
        if "nonResourceURLs" in rule:
            problems.append("RBAC_NON_RESOURCE_URL_FORBIDDEN")
        for key in ("apiGroups", "resources", "verbs"):
            if "*" in rule.get(key, []):
                problems.append("RBAC_WILDCARD_FORBIDDEN")
        if any(resource == "secrets" or resource.startswith("secrets/") for resource in rule.get("resources", [])):
            problems.append("RBAC_SECRET_ACCESS_FORBIDDEN")
    expected_binding = policy["rbac"]["binding"]
    if binding.get("roleRef") != {
        "apiGroup": "rbac.authorization.k8s.io",
        "kind": "ClusterRole",
        "name": expected_binding["name"],
    }:
        problems.append("RBAC_BINDING_ROLE_INVALID")
    if binding.get("subjects") != [
        {
            "kind": "ServiceAccount",
            "name": expected_binding["serviceAccount"],
            "namespace": expected_binding["namespace"],
        }
    ]:
        problems.append("RBAC_BINDING_SUBJECT_INVALID")
    if account.get("automountServiceAccountToken") is not True:
        problems.append("CONTROLLER_SERVICE_ACCOUNT_TOKEN_MODE_DRIFT")
    if node_account.get("automountServiceAccountToken") is not False:
        problems.append("NODE_SERVICE_ACCOUNT_TOKEN_MODE_DRIFT")

    controller_spec = pod_spec(controller)
    node_spec = pod_spec(node)
    for label, spec in (("CONTROLLER", controller_spec), ("NODE", node_spec)):
        if any(spec.get(field, False) is not False for field in ("hostNetwork", "hostPID", "hostIPC")):
            problems.append(label + "_HOST_NAMESPACE_FORBIDDEN")
        if any("hostPort" in port for item in spec.get("containers", []) for port in item.get("ports", [])):
            problems.append(label + "_HOST_PORT_FORBIDDEN")
    if controller_spec.get("serviceAccountName") != "werftkern-hcloud-csi-controller":
        problems.append("CONTROLLER_SERVICE_ACCOUNT_INVALID")
    if (
        controller_spec.get("securityContext", {}).get("seccompProfile")
        != EXPECTED_POD_SECCOMP_PROFILE
    ):
        problems.append("CONTROLLER_POD_SECCOMP_PROFILE_DRIFT")
    if controller_spec.get("automountServiceAccountToken") is not None:
        problems.append("CONTROLLER_POD_TOKEN_OVERRIDE_DRIFT")
    if host_paths(controller_spec):
        problems.append("CONTROLLER_HOST_PATH_FORBIDDEN")
    if privileged_containers(controller_spec):
        problems.append("CONTROLLER_PRIVILEGED_CONTAINER_FORBIDDEN")
    if bidirectional_mounts(controller_spec):
        problems.append("CONTROLLER_BIDIRECTIONAL_MOUNT_FORBIDDEN")
    if secret_refs(controller_spec) != ["hcloud/token"]:
        problems.append("CONTROLLER_SECRET_REFERENCE_DRIFT")

    if node_spec.get("serviceAccountName") != "werftkern-hcloud-csi-node":
        problems.append("NODE_SERVICE_ACCOUNT_DRIFT")
    if (
        node_spec.get("securityContext", {}).get("seccompProfile")
        != EXPECTED_POD_SECCOMP_PROFILE
    ):
        problems.append("NODE_POD_SECCOMP_PROFILE_DRIFT")
    if "automountServiceAccountToken" in node_spec:
        problems.append("NODE_TOKEN_MODE_DRIFT_REQUIRES_REVIEW")
    if host_paths(node_spec) != EXPECTED_HOST_PATHS:
        problems.append("NODE_HOST_PATH_BOUNDARY_DRIFT")
    if privileged_containers(node_spec) != ["hcloud-csi-driver"]:
        problems.append("NODE_PRIVILEGED_BOUNDARY_DRIFT")
    if bidirectional_mounts(node_spec) != [
        "hcloud-csi-driver:kubelet-dir:/var/lib/k0s/kubelet"
    ]:
        problems.append("NODE_BIDIRECTIONAL_MOUNT_BOUNDARY_DRIFT")
    if secret_refs(node_spec):
        problems.append("NODE_SECRET_REFERENCE_FORBIDDEN")

    workloads = [controller_spec, node_spec]
    containers = [item for spec in workloads for item in spec.get("containers", [])]
    observed_gaps: list[str] = []
    if (
        node_spec.get("automountServiceAccountToken") is True
        or node_account.get("automountServiceAccountToken") is not False
    ):
        observed_gaps.append("NODE_DEFAULT_SERVICE_ACCOUNT_TOKEN_IMPLICITLY_MOUNTED")
    if any(
        not item.get("securityContext")
        for item in containers
        if item.get("securityContext", {}).get("privileged") is not True
    ):
        observed_gaps.append("CONTAINER_SECURITY_CONTEXTS_NOT_ENFORCED")
    if any(
        spec.get("securityContext", {}).get("seccompProfile") != EXPECTED_POD_SECCOMP_PROFILE
        for spec in workloads
    ):
        observed_gaps.append("SECCOMP_PROFILE_NOT_ENFORCED")
    if any(
        item.get("resources", {}).get("requests", {}) == {}
        or item.get("resources", {}).get("limits", {}) == {}
        for item in containers
    ):
        observed_gaps.append("RESOURCE_REQUESTS_AND_LIMITS_EMPTY")
    if observed_gaps != EXPECTED_GAPS:
        problems.append("OBSERVED_HARDENING_GAPS_DRIFT")

    services = [item for item in documents if item.get("kind") == "Service"]
    if len(services) != 2 or any(
        item.get("spec", {}).get("type", "ClusterIP") != "ClusterIP"
        or item.get("spec", {}).get("externalIPs")
        or item.get("spec", {}).get("loadBalancerIP")
        for item in services
    ):
        problems.append("METRICS_SERVICE_EXPOSURE_DRIFT")
    return problems


def main() -> int:
    try:
        policy = parse_json(POLICY_PATH.read_text())
        manifest_path = ROOT / policy.get("manifest", {}).get("path", "")
        raw = manifest_path.read_text()
        problems = validate_policy(policy) + validate_manifest(policy, raw)
        result = {
            "policyValid": not problems,
            "staticAuditRecorded": not problems,
            "hardeningPassed": False,
            "productionReady": False,
            "observedHardeningGaps": EXPECTED_GAPS,
            "problems": problems,
            "notice": "Static manifest auditing is not admission, runtime or production security qualification.",
        }
        print(json.dumps(result, indent=2))
        return 0 if not problems else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"policyValid": False, "productionReady": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
