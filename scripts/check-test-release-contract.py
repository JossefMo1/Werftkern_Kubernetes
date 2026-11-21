#!/usr/bin/env python3
"""Validate the immutable test-release asset and documentation contract.

This check is deliberately narrow: it catches filename/checksum drift before a
new experimental release is published. It does not qualify Ubuntu, Kubernetes,
HA, recovery, security, or production readiness.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED_ASSETS = (
    "werftkern_0.2.0.dev4_amd64.deb",
    "werftkern-kubernetes_0.1.0.dev3_all.deb",
)
LEGACY_ASSETS = (
    "werftkern_0.2.0~dev4_amd64.deb",
    "werftkern-kubernetes_0.1.0~dev3_all.deb",
)
DOCUMENTS = (
    Path("docs/TEST-RELEASE-DE.md"),
    Path("docs/kubernetes/README-DE.md"),
)
DOCUMENT_ASSETS = {
    Path("docs/TEST-RELEASE-DE.md"): EXPECTED_ASSETS,
    Path("docs/kubernetes/README-DE.md"): ("werftkern-kubernetes_0.1.0.dev3_all.deb",),
}
RELEASE_DOWNLOAD_FRAGMENTS = (
    'BASE="https://github.com/JossefMo1/Werftkern_Kubernetes/releases/download/${TAG}"',
    "wget \\\n",
    '"${BASE}/release-manifest.json"',
    '"${BASE}/SHA256SUMS"',
    'tar -xzf "werftkern-test-kit-${TAG}.tar.gz"',
)
NATIVE_AUTO_FRAGMENTS = (
    "test -x /usr/bin/werft-ops || {",
    "dpkg-query -W -f='Status: ${Status}\\n' werftkern",
    "--auto-discover",
    "--inventory examples/native-inventory-3m-3w.json",
    "--journal /root/werft-native-bootstrap.json --check-only",
)
NATIVE_PACKAGE_LIFECYCLE_FRAGMENTS = (
    "sudo apt-get remove -y werftkern",
    "dpkg-query -W -f='Status: ${Status}\\n' werftkern 2>/dev/null || true",
    "hash -r",
    "! command -v werft-ops",
    "! command -v werft",
    "sudo apt-get install --reinstall ./werftkern_0.2.0.dev4_amd64.deb",
)
KUBERNETES_INSTALL_FRAGMENTS = (
    "sudo apt-get install --reinstall ./werftkern-kubernetes_0.1.0.dev3_all.deb",
    "dpkg-query -W -f='Status: ${Status}\\n' werftkern-kubernetes",
    "command -v werft-kube",
    "werft-kube version",
    "sudo apt-get remove -y werftkern-kubernetes",
    "hash -r",
    "! command -v werft-kube",
)
WORKFLOW = Path(".github/workflows/test-release.yml")
NATIVE_WORKFLOW = Path(".github/workflows/ci.yml")
KUBERNETES_WORKFLOW = Path(".github/workflows/kubernetes-backend.yml")
TRACKER = Path("release/production-tracker.json")
RUNBOOK_TAG = re.compile(r"(?m)^TAG=(v[^\n]+)$")


def validate(root: Path) -> list[str]:
    problems: list[str] = []
    root = root.resolve()

    documents: dict[Path, str] = {}
    tracker_path = root / TRACKER
    try:
        tracker = json.loads(tracker_path.read_text())
        tracker_tag = tracker.get("candidate", {}).get("tag")
        if not isinstance(tracker_tag, str) or not tracker_tag:
            problems.append(f"TRACKER_CANDIDATE_TAG_INVALID:{TRACKER}")
            tracker_tag = None
    except (OSError, json.JSONDecodeError, AttributeError):
        problems.append(f"TRACKER_MISSING:{TRACKER}")
        tracker_tag = None
    for relative in DOCUMENTS:
        path = root / relative
        try:
            content = path.read_text()
        except OSError:
            problems.append(f"DOCUMENT_MISSING:{relative}")
            continue
        documents[relative] = content
        for asset in DOCUMENT_ASSETS[relative]:
            if asset not in content:
                problems.append(f"DOCUMENT_ASSET_MISSING:{relative}:{asset}")
        for asset in LEGACY_ASSETS:
            if asset in content:
                problems.append(f"LEGACY_ASSET_NAME:{relative}:{asset}")
        if relative == Path("docs/TEST-RELEASE-DE.md"):
            for fragment in RELEASE_DOWNLOAD_FRAGMENTS + NATIVE_AUTO_FRAGMENTS + NATIVE_PACKAGE_LIFECYCLE_FRAGMENTS + KUBERNETES_INSTALL_FRAGMENTS:
                if fragment not in content:
                    problems.append(f"DOCUMENT_INSTRUCTIONS_MISSING:{relative}:{fragment}")

    runbook = documents.get(Path("docs/TEST-RELEASE-DE.md"), "")
    if tracker_tag:
        match = RUNBOOK_TAG.search(runbook)
        if not match:
            problems.append("DOCUMENT_TAG_MISSING:docs/TEST-RELEASE-DE.md")
        elif match.group(1) != tracker_tag:
            problems.append(
                "DOCUMENT_TAG_MISMATCH:docs/TEST-RELEASE-DE.md:"
                + match.group(1)
                + "!="
                + tracker_tag
            )

    workflow_path = root / WORKFLOW
    try:
        workflow = workflow_path.read_text()
    except OSError:
        problems.append(f"WORKFLOW_MISSING:{WORKFLOW}")
        workflow = ""

    native_workflow_path = root / NATIVE_WORKFLOW
    try:
        native_workflow = native_workflow_path.read_text()
    except OSError:
        problems.append(f"WORKFLOW_MISSING:{NATIVE_WORKFLOW}")
        native_workflow = ""

    kubernetes_workflow_path = root / KUBERNETES_WORKFLOW
    try:
        kubernetes_workflow = kubernetes_workflow_path.read_text()
    except OSError:
        problems.append(f"WORKFLOW_MISSING:{KUBERNETES_WORKFLOW}")
        kubernetes_workflow = ""

    required_native_workflow_fragments = (
        'package="$GITHUB_WORKSPACE/dist/werftkern_0.2.0~dev4_amd64.deb"',
        'sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$package"',
        'test "$(dpkg-query -W -f='\'${Status}\'' werftkern)" = "install ok installed"',
        'test "$(command -v werft-ops)" = "/usr/bin/werft-ops"',
        'test "$(command -v werft)" = "/usr/bin/werft"',
        "werft-ops --help >",
        'grep -q -- "native-bootstrap"',
        "werft --help >",
        "sudo apt-get remove -y werftkern >/dev/null",
        "sudo apt-get remove -y werftkern >/dev/null",
        "test \"$(dpkg-query -W -f='${Status}' werftkern 2>/dev/null || true)\" != \"install ok installed\"",
        "hash -r",
        "! command -v werft-ops",
        "! command -v werft",
    )
    for fragment in required_native_workflow_fragments:
        if fragment not in native_workflow:
            problems.append(f"NATIVE_WORKFLOW_CONTRACT_MISSING:{fragment}")
    required_kubernetes_workflow_fragments = (
        'package="$GITHUB_WORKSPACE/dist/werftkern-kubernetes_0.1.0~dev3_all.deb"',
        'sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$package"',
        'test "$(command -v werft-kube)" = "/usr/bin/werft-kube"',
        "werft-kube version >",
        'grep -q \'"productionReady": false\'',
        'sudo apt-get remove -y werftkern-kubernetes >/dev/null',
        "test \"$(dpkg-query -W -f='${Status}' werftkern-kubernetes 2>/dev/null || true)\" != \"install ok installed\"",
        "hash -r",
        "! command -v werft-kube",
    )
    for fragment in required_kubernetes_workflow_fragments:
        if fragment not in kubernetes_workflow:
            problems.append(f"KUBERNETES_WORKFLOW_CONTRACT_MISSING:{fragment}")

    required_workflow_fragments = (
        'native_release_name="$(basename "$native" | tr \'~\' \'.\')"',
        'manager_release_name="$(basename "$manager" | tr \'~\' \'.\')"',
        "sha256sum *.deb *.tar.gz release-manifest.json > SHA256SUMS",
        "release-assets/*.deb release-assets/*.tar.gz release-assets/release-manifest.json release-assets/SHA256SUMS",
        'release_notes="$PWD/.test-release-notes.md"',
        'docs/TEST-RELEASE-DE.md > "$release_notes"',
        'install -D -m 0644 "$release_notes" "$kit/README-DE.md"',
        "--notes-file .test-release-notes.md",
    )
    for fragment in required_workflow_fragments:
        if fragment not in workflow:
            problems.append(f"WORKFLOW_CONTRACT_MISSING:{fragment}")

    if "sha256sum release-assets/*.deb" in workflow:
        problems.append("CHECKSUMS_MUST_USE_BASENAMES")
    if "dist/*.tar.gz" in workflow:
        problems.append("PUBLISH_MUST_NOT_USE_DIST_TARBALL_GLOB")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        problems = validate(args.root)
    except (OSError, ValueError, TypeError) as exc:
        problems = [f"CONTRACT_INPUT_INVALID:{exc}"]
    result = {
        "testReleaseContractValid": not problems,
        "productionReady": False,
        "status": "TEST_RELEASE_CONTRACT_VALID" if not problems else "TEST_RELEASE_CONTRACT_INVALID",
        "problems": problems,
        "notice": "Filename/checksum consistency only; no live qualification or production approval.",
    }
    print(json.dumps(result, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
