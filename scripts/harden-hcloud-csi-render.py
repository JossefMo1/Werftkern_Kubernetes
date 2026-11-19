#!/usr/bin/env python3
"""Apply the reviewed hcloud CSI container security contexts fail-closed.

The upstream 2.24.2 chart has no per-container SecurityContext values. This
post-render step accepts only the exact reviewed pre-hardening render, applies
the narrow contexts below and then validates the complete workload/container
boundary. It does not claim that root identities or the privileged node driver
are production-qualified.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

import yaml


EXPECTED_INPUT_SHA256 = "1fb2e34ccb267064ee8c84084bab78fd2777afef906b2767b51722500caa6fbc"
EXPECTED_OUTPUT_SHA256 = "1a439e5735f2635904acc8379a55185e010abfe8e3466b1ff8ae75433da6e438"
NON_PRIVILEGED_CONTEXT = {
    "runAsUser": 0,
    "runAsNonRoot": False,
    "allowPrivilegeEscalation": False,
    "capabilities": {"drop": ["ALL"]},
    "seccompProfile": {"type": "RuntimeDefault"},
}
PRIVILEGED_NODE_CONTEXT = {
    "privileged": True,
    "runAsUser": 0,
    "runAsNonRoot": False,
}
EXPECTED_WORKLOADS = {
    ("Deployment", "kube-system", "werftkern-hcloud-csi-controller"): {
        "hcloud-csi-driver": NON_PRIVILEGED_CONTEXT,
        "csi-attacher": NON_PRIVILEGED_CONTEXT,
        "csi-resizer": NON_PRIVILEGED_CONTEXT,
        "csi-provisioner": NON_PRIVILEGED_CONTEXT,
        "liveness-probe": NON_PRIVILEGED_CONTEXT,
    },
    ("DaemonSet", "kube-system", "werftkern-hcloud-csi-node"): {
        "csi-node-driver-registrar": NON_PRIVILEGED_CONTEXT,
        "liveness-probe": NON_PRIVILEGED_CONTEXT,
        "hcloud-csi-driver": PRIVILEGED_NODE_CONTEXT,
    },
}


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def load_documents(raw: str) -> list[dict]:
    try:
        loaded = list(yaml.load_all(raw, Loader=UniqueKeyLoader))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML: {exc}") from exc
    if any(item is not None and not isinstance(item, dict) for item in loaded):
        raise ValueError("every non-empty YAML document must be an object")
    return [item for item in loaded if isinstance(item, dict)]


def identity(document: dict) -> tuple[str, str, str]:
    metadata = document.get("metadata", {})
    return (
        str(document.get("kind", "")),
        str(metadata.get("namespace", "")),
        str(metadata.get("name", "")),
    )


def workload_containers(document: dict) -> list[dict]:
    containers = document.get("spec", {}).get("template", {}).get("spec", {}).get("containers")
    if not isinstance(containers, list):
        raise ValueError(f"{identity(document)} has no container list")
    return containers


def validate_workloads(documents: list[dict], *, hardened: bool) -> None:
    found: dict[tuple[str, str, str], dict] = {}
    for document in documents:
        key = identity(document)
        if key in EXPECTED_WORKLOADS:
            if key in found:
                raise ValueError(f"duplicate workload identity: {key}")
            found[key] = document
    if set(found) != set(EXPECTED_WORKLOADS):
        raise ValueError(
            f"workload identity drift: expected {sorted(EXPECTED_WORKLOADS)}, got {sorted(found)}"
        )

    for key, expected in EXPECTED_WORKLOADS.items():
        containers = workload_containers(found[key])
        names = [str(item.get("name", "")) for item in containers]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError(
                f"container boundary drift for {key}: expected {sorted(expected)}, got {sorted(names)}"
            )
        for container in containers:
            name = str(container.get("name", ""))
            actual = container.get("securityContext")
            wanted = expected[name]
            if hardened:
                if actual != wanted:
                    raise ValueError(
                        f"securityContext drift for {key}/{name}: expected {wanted}, got {actual}"
                    )
            else:
                initial = {"privileged": True} if wanted is PRIVILEGED_NODE_CONTEXT else None
                if actual != initial:
                    raise ValueError(
                        f"unexpected input securityContext for {key}/{name}: {actual}"
                    )


def already_hardened(documents: list[dict]) -> bool:
    try:
        validate_workloads(documents, hardened=True)
    except ValueError:
        return False
    return True


def insert_context(part: str, name: str, context: dict, *, privileged: bool) -> str:
    if privileged:
        old = "          securityContext:\n            privileged: true\n"
        new = (
            "          securityContext:\n"
            "            privileged: true\n"
            "            runAsUser: 0\n"
            "            runAsNonRoot: false\n"
        )
        if part.count(old) != 1:
            raise ValueError("expected exactly one privileged node securityContext block")
        return part.replace(old, new, 1)

    marker = f"        - name: {name}\n"
    if part.count(marker) != 1:
        raise ValueError(f"expected exactly one container marker for {name}")
    rendered = (
        marker
        + "          securityContext:\n"
        + "            runAsUser: 0\n"
        + "            runAsNonRoot: false\n"
        + "            allowPrivilegeEscalation: false\n"
        + "            capabilities:\n"
        + "              drop:\n"
        + "                - ALL\n"
        + "            seccompProfile:\n"
        + "              type: RuntimeDefault\n"
    )
    return part.replace(marker, rendered, 1)


def harden(raw: str, *, expected_input_sha256: str = EXPECTED_INPUT_SHA256) -> str:
    documents = load_documents(raw)
    if already_hardened(documents):
        actual_sha = hashlib.sha256(raw.encode()).hexdigest()
        if actual_sha != EXPECTED_OUTPUT_SHA256:
            raise ValueError(
                f"hardened render SHA-256 drift: expected {EXPECTED_OUTPUT_SHA256}, got {actual_sha}"
            )
        return raw
    actual_sha = hashlib.sha256(raw.encode()).hexdigest()
    if actual_sha != expected_input_sha256:
        raise ValueError(
            f"pre-hardening render SHA-256 drift: expected {expected_input_sha256}, got {actual_sha}"
        )
    validate_workloads(documents, hardened=False)

    parts = raw.split("\n---\n")
    for index, part in enumerate(parts):
        document = yaml.load(part, Loader=UniqueKeyLoader)
        if not isinstance(document, dict):
            continue
        key = identity(document)
        if key not in EXPECTED_WORKLOADS:
            continue
        for name, context in EXPECTED_WORKLOADS[key].items():
            parts[index] = insert_context(
                parts[index],
                name,
                context,
                privileged=context is PRIVILEGED_NODE_CONTEXT,
            )

    result = "\n---\n".join(parts)
    validate_workloads(load_documents(result), hardened=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = args.input.read_text()
        result = harden(raw)
        args.output.write_text(result)
        print(hashlib.sha256(result.encode()).hexdigest())
        return 0
    except (OSError, ValueError) as exc:
        print(f"hcloud CSI hardening failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
