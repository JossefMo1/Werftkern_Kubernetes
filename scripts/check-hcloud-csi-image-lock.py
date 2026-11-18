#!/usr/bin/env python3
"""Validate the hcloud CSI image inventory and an optional Helm render."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

SHA256 = re.compile(r"sha256:[a-f0-9]{64}")
IMAGE_LINE = re.compile(r"^\s*image:\s*[\"']?([^\"'#\s]+)")
EXPECTED = {
    "csi-attacher": ("registry.k8s.io/sig-storage/csi-attacher", "v4.13.0", ["controller"]),
    "csi-node-driver-registrar": ("registry.k8s.io/sig-storage/csi-node-driver-registrar", "v2.18.0", ["node"]),
    "csi-provisioner": ("registry.k8s.io/sig-storage/csi-provisioner", "v6.3.0", ["controller"]),
    "csi-resizer": ("registry.k8s.io/sig-storage/csi-resizer", "v2.2.1", ["controller"]),
    "hcloud-csi-driver": ("docker.io/hetznercloud/hcloud-csi-driver", "v2.24.2", ["controller", "node"]),
    "liveness-probe": ("registry.k8s.io/sig-storage/livenessprobe", "v2.20.0", ["controller", "node"]),
}


def parse_json(text: str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def validate_lock(lock: dict) -> list[str]:
    problems: list[str] = []
    if lock.get("schema") != "werftkern/hcloud-csi-image-lock/v1":
        problems.append("SCHEMA_INVALID")
    if lock.get("productionReady") is not False or lock.get("chartVersion") != "2.24.2":
        problems.append("LOCK_BOUNDARY_INVALID")
    if lock.get("sourceValues") != {
        "repository": "hetznercloud/csi-driver",
        "ref": "v2.24.2",
        "path": "chart/values.yaml",
        "gitBlobSha": "0c38bd9e9889e29ba2d52d71368ea4f31d84174a",
        "inspectedAt": "2026-11-19",
    }:
        problems.append("SOURCE_VALUES_PROVENANCE_INVALID")
    images = lock.get("images")
    if not isinstance(images, dict) or set(images) != set(EXPECTED):
        return problems + ["IMAGE_INVENTORY_INVALID"]
    references = set()
    all_pinned = True
    for name, (repository, tag, consumers) in EXPECTED.items():
        item = images.get(name)
        if not isinstance(item, dict) or set(item) != {"repository", "tag", "digest", "consumers"}:
            problems.append("IMAGE_RECORD_INVALID:" + name)
            continue
        if item.get("repository") != repository or item.get("tag") != tag or item.get("consumers") != consumers:
            problems.append("IMAGE_SOURCE_DRIFT:" + name)
        reference = f"{item.get('repository')}:{item.get('tag')}"
        if reference in references:
            problems.append("DUPLICATE_IMAGE_REFERENCE:" + name)
        references.add(reference)
        digest = item.get("digest")
        if digest is None:
            all_pinned = False
        elif not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            problems.append("IMAGE_DIGEST_INVALID:" + name)
        if "latest" in reference.lower():
            problems.append("MUTABLE_IMAGE_TAG_FORBIDDEN:" + name)
    status = lock.get("status")
    if all_pinned and status != "digests-pinned-not-render-qualified":
        problems.append("DIGEST_STATUS_INVALID")
    if not all_pinned and status != "inventory-complete-digests-unresolved":
        problems.append("UNRESOLVED_STATUS_INVALID")
    render = lock.get("render")
    if not isinstance(render, dict) or set(render) != {"manifestSha256", "verified"}:
        problems.append("RENDER_STATE_INVALID")
    elif render.get("verified") is not False or render.get("manifestSha256") is not None:
        problems.append("UNEXECUTED_RENDER_MUST_REMAIN_FALSE")
    limitations = lock.get("limitations")
    if not isinstance(limitations, list) or not limitations or any(not isinstance(v, str) or not v for v in limitations):
        problems.append("LIMITATIONS_MISSING")
    if "latest" in json.dumps(lock).lower():
        problems.append("MUTABLE_LATEST_REFERENCE_FORBIDDEN")
    return problems


def extract_images(rendered: str) -> list[str]:
    return [match.group(1) for line in rendered.splitlines() if (match := IMAGE_LINE.match(line))]


def validate_render(rendered: str, lock: dict) -> list[str]:
    problems: list[str] = []
    images = extract_images(rendered)
    if not images:
        return ["RENDER_CONTAINS_NO_IMAGES"]
    expected: list[str] = []
    for name, item in lock.get("images", {}).items():
        digest = item.get("digest") if isinstance(item, dict) else None
        if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            problems.append("UNRESOLVED_IMAGE_DIGEST:" + name)
            continue
        expected.extend([f"{item['repository']}@{digest}"] * len(item["consumers"]))
    observed = set(images)
    for image in observed:
        if "@sha256:" not in image or not SHA256.fullmatch("sha256:" + image.rsplit("@sha256:", 1)[-1]):
            problems.append("TAG_OR_INVALID_DIGEST_IN_RENDER:" + image)
    if Counter(images) != Counter(expected):
        problems.append("RENDER_IMAGE_SET_MISMATCH")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=Path("release/hcloud-csi-image-lock.json"))
    parser.add_argument("--rendered", type=Path)
    args = parser.parse_args()
    try:
        if args.lock.stat().st_size > 1_000_000:
            raise ValueError("lock too large")
        lock = parse_json(args.lock.read_text())
        problems = validate_lock(lock)
        rendered_sha = None
        render_verified = False
        if args.rendered is not None:
            if args.rendered.stat().st_size > 10_000_000:
                raise ValueError("render too large")
            rendered = args.rendered.read_text()
            rendered_sha = hashlib.sha256(rendered.encode()).hexdigest()
            render_problems = validate_render(rendered, lock)
            problems.extend(render_problems)
            render_verified = not render_problems
    except (OSError, ValueError, TypeError, AttributeError):
        problems = ["IMAGE_LOCK_INPUT_INVALID"]
        lock = {}
        rendered_sha = None
        render_verified = False
    images = lock.get("images", {}) if isinstance(lock, dict) else {}
    all_pinned = bool(images) and all(isinstance(v, dict) and isinstance(v.get("digest"), str) for v in images.values())
    print(json.dumps({
        "inventoryValid": not [p for p in problems if not p.startswith("UNRESOLVED_IMAGE_DIGEST:")],
        "imageDigestsPinned": all_pinned,
        "renderVerified": render_verified,
        "renderedSha256": rendered_sha,
        "productionReady": False,
        "problems": problems,
        "notice": "Inventory validation and render policy are not signature, vulnerability or runtime qualification.",
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
