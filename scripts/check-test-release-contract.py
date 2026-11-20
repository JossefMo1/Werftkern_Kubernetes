#!/usr/bin/env python3
"""Validate the immutable test-release asset and documentation contract.

This check is deliberately narrow: it catches filename/checksum drift before a
new experimental release is published. It does not qualify Ubuntu, Kubernetes,
HA, recovery, security, or production readiness.
"""
from __future__ import annotations

import argparse
import json
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
WORKFLOW = Path(".github/workflows/test-release.yml")


def validate(root: Path) -> list[str]:
    problems: list[str] = []
    root = root.resolve()

    documents: dict[Path, str] = {}
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
            for fragment in RELEASE_DOWNLOAD_FRAGMENTS + NATIVE_AUTO_FRAGMENTS:
                if fragment not in content:
                    problems.append(f"DOCUMENT_INSTRUCTIONS_MISSING:{relative}:{fragment}")

    workflow_path = root / WORKFLOW
    try:
        workflow = workflow_path.read_text()
    except OSError:
        problems.append(f"WORKFLOW_MISSING:{WORKFLOW}")
        workflow = ""

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
