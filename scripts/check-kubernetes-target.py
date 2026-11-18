#!/usr/bin/env python3
"""Validate the pinned Kubernetes candidate matrix without qualifying it."""
from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path
from urllib.parse import quote

SHA256 = re.compile(r"[a-f0-9]{64}")
K0S = re.compile(r"v(1\.\d+\.\d+)\+k0s\.\d+")
K0SCTL = re.compile(r"v0\.\d+\.\d+")


def parse_json(text: str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def digest(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def timestamp(value):
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except (ValueError, TypeError, AttributeError):
        return False


def validate(matrix: dict) -> list[str]:
    problems: list[str] = []
    if matrix.get("schema") != "werftkern/kubernetes-target-matrix/v1":
        problems.append("SCHEMA_INVALID")
    if matrix.get("status") != "candidate-not-qualified" or matrix.get("productionReady") is not False:
        problems.append("TARGET_MUST_REMAIN_UNQUALIFIED")
    try:
        datetime.date.fromisoformat(matrix.get("selectedAt"))
    except (ValueError, TypeError):
        problems.append("SELECTION_DATE_INVALID")
    if matrix.get("platform") != {
        "architecture": "linux-amd64",
        "managementHost": "ubuntu-24.04-lts-amd64",
        "targetHosts": "ubuntu-24.04-lts-amd64",
    }:
        problems.append("PLATFORM_INVALID")
    core = matrix.get("core")
    if not isinstance(core, dict) or set(core) != {"k0s", "k0sctl", "kubectl"}:
        return problems + ["CORE_INVENTORY_INVALID"]
    k0s, ctl, kubectl = core["k0s"], core["k0sctl"], core["kubectl"]
    match = K0S.fullmatch(k0s.get("version", "")) if isinstance(k0s, dict) else None
    if not match or k0s.get("kubernetesVersion") != "v" + match.group(1):
        problems.append("K0S_KUBERNETES_VERSION_MISMATCH")
    if not isinstance(ctl, dict) or K0SCTL.fullmatch(ctl.get("version", "")) is None:
        problems.append("K0SCTL_VERSION_INVALID")
    if not isinstance(kubectl, dict) or kubectl.get("version") != k0s.get("kubernetesVersion"):
        problems.append("KUBECTL_VERSION_MISMATCH")

    expected = [
        (k0s, "k0sproject/k0s"),
        (ctl, "k0sproject/k0sctl"),
        (kubectl, "kubernetes/kubernetes"),
    ]
    for component, repository in expected:
        if not isinstance(component, dict) or component.get("repository") != repository:
            problems.append("UPSTREAM_REPOSITORY_INVALID:" + repository)
            continue
        version = component.get("version", "")
        encoded = quote(version, safe=".")
        expected_release = f"https://github.com/{repository}/releases/tag/{encoded}"
        if component.get("releaseUrl") != expected_release or not timestamp(component.get("publishedAt")):
            problems.append("RELEASE_PROVENANCE_INVALID:" + repository)
        artifact = component.get("artifact")
        if not isinstance(artifact, dict) or not digest(artifact.get("sha256")):
            problems.append("ARTIFACT_DIGEST_INVALID:" + repository)
        if component.get("binaryDownloadedAndHashed") is not False:
            problems.append("UNEXECUTED_BINARY_MUST_REMAIN_FALSE:" + repository)

    k0s_prefix = f"https://github.com/k0sproject/k0s/releases/download/{quote(k0s.get('version', ''), safe='.')}/"
    k0s_name = f"k0s-{k0s.get('version', '')}-amd64"
    if (
        k0s.get("artifact", {}).get("name") != k0s_name
        or k0s.get("artifact", {}).get("url") != k0s_prefix + k0s_name
    ):
        problems.append("K0S_ARTIFACT_URL_INVALID")
    checksum = k0s.get("checksumManifest")
    if (
        not isinstance(checksum, dict)
        or checksum.get("url") != k0s_prefix + "sha256sums.txt"
        or not digest(checksum.get("sha256"))
        or checksum.get("entryMatchedReleaseApiDigest") is not True
    ):
        problems.append("K0S_EVIDENCE_INVALID:checksumManifest")
    signature = k0s.get("signature")
    if (
        not isinstance(signature, dict)
        or signature.get("url") != k0s_prefix + k0s_name + ".sig"
        or not digest(signature.get("sha256"))
    ):
        problems.append("K0S_EVIDENCE_INVALID:signature")
    sbom = k0s.get("sbom")
    if (
        not isinstance(sbom, dict)
        or sbom.get("url") != k0s_prefix + "spdx.json"
        or not digest(sbom.get("sha256"))
        or sbom.get("signatureUrl") != k0s_prefix + "spdx.json.sig"
    ):
        problems.append("K0S_EVIDENCE_INVALID:sbom")
    if k0s.get("signature", {}).get("verified") is not False or k0s.get("sbom", {}).get("verified") is not False:
        problems.append("UNVERIFIED_SIGNATURE_MUST_REMAIN_FALSE")
    if not digest(k0s.get("sbom", {}).get("signatureSha256")):
        problems.append("K0S_SBOM_SIGNATURE_DIGEST_INVALID")

    ctl_prefix = f"https://github.com/k0sproject/k0sctl/releases/download/{ctl.get('version', '')}/"
    ctl_name = "k0sctl-linux-amd64"
    if ctl.get("artifact", {}).get("name") != ctl_name or ctl.get("artifact", {}).get("url") != ctl_prefix + ctl_name:
        problems.append("K0SCTL_ARTIFACT_URL_INVALID")
    checksum = ctl.get("checksumManifest")
    if (
        not isinstance(checksum, dict)
        or checksum.get("url") != ctl_prefix + "checksums.txt"
        or not digest(checksum.get("sha256"))
        or checksum.get("entryMatchedReleaseApiDigest") is not True
    ):
        problems.append("K0SCTL_CHECKSUM_INVALID")
    if ctl.get("signatureAvailable") is not False:
        problems.append("K0SCTL_SIGNATURE_CLAIM_INVALID")

    kube_version = kubectl.get("version", "")
    kube_prefix = f"https://dl.k8s.io/release/{kube_version}/bin/linux/amd64/"
    kubectl_artifact = kubectl.get("artifact")
    if (
        not isinstance(kubectl_artifact, dict)
        or kubectl_artifact.get("url") != kube_prefix + "kubectl"
        or kubectl_artifact.get("sha256Url") != kube_prefix + "kubectl.sha256"
    ):
        problems.append("KUBECTL_ARTIFACT_URL_INVALID")

    compatibility = matrix.get("compatibility")
    if not isinstance(compatibility, dict) or compatibility != {
        "basis": "matching-kubernetes-patch-in-k0s-tag-only",
        "contractTestsPassed": False,
        "realClusterPassed": False,
        "upgradeSourceVersion": None,
        "upgradeEdgeQualified": False,
    }:
        problems.append("COMPATIBILITY_CLAIM_INVALID")
    unresolved = matrix.get("unresolved")
    if not isinstance(unresolved, dict) or set(unresolved) != {"storageProfile", "addonImagesAndCharts"}:
        problems.append("UNRESOLVED_INVENTORY_INVALID")
    elif any(not isinstance(value, str) or not value.strip() for value in unresolved.values()):
        problems.append("UNRESOLVED_REASON_MISSING")
    if "latest" in json.dumps(matrix).lower():
        problems.append("MUTABLE_LATEST_REFERENCE_FORBIDDEN")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=Path("release/kubernetes-target-matrix.json"))
    args = parser.parse_args()
    try:
        if args.matrix.stat().st_size > 1_000_000:
            raise ValueError("matrix too large")
        matrix = parse_json(args.matrix.read_text())
        problems = validate(matrix)
    except (OSError, ValueError, TypeError, AttributeError):
        problems = ["TARGET_INPUT_INVALID"]
    print(json.dumps({
        "targetValid": not problems,
        "productionReady": False,
        "status": "CANDIDATE_TARGET_VALID" if not problems else "TARGET_INVALID",
        "problems": problems,
        "notice": "Pin validation is not binary verification, compatibility proof or live qualification.",
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
