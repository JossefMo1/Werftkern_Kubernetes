#!/usr/bin/env python3
"""Validate the hcloud CSI image inventory and an optional Helm render."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import urllib.parse
import urllib.request

SHA256 = re.compile(r"sha256:[a-f0-9]{64}")
IMAGE_LINE = re.compile(r"^\s*image:\s*[\"']?([^\"'#\s]+)")
EXPECTED = {
    "csi-attacher": ("registry.k8s.io/sig-storage/csi-attacher", "v4.13.0", ["controller"], "sha256:d1a26170efed45491074ca4545c81844eee2b9043fb885ac01fb4aed6f8b72d2", "registry.k8s.io", "application/vnd.docker.distribution.manifest.list.v2+json", 6),
    "csi-node-driver-registrar": ("registry.k8s.io/sig-storage/csi-node-driver-registrar", "v2.18.0", ["node"], "sha256:b7fefd08651f00ac4df1a196ed4c621c2451fbb899297fe9fad9e36c667af0c0", "registry.k8s.io", "application/vnd.docker.distribution.manifest.list.v2+json", 8),
    "csi-provisioner": ("registry.k8s.io/sig-storage/csi-provisioner", "v6.3.0", ["controller"], "sha256:a4b0b1a37605b7b04a293e136edf7006ec1786a8eb3f4e5a945f81d667dcc371", "registry.k8s.io", "application/vnd.docker.distribution.manifest.list.v2+json", 6),
    "csi-resizer": ("registry.k8s.io/sig-storage/csi-resizer", "v2.2.1", ["controller"], "sha256:ea1d25e23479000c7e8eeb92d827df66258df4e482ca054c5e7ce3fc0f5c41a5", "registry.k8s.io", "application/vnd.docker.distribution.manifest.list.v2+json", 6),
    "hcloud-csi-driver": ("docker.io/hetznercloud/hcloud-csi-driver", "v2.24.2", ["controller", "node"], "sha256:c231060c9d24d485c8ac25eeb3dd445994ce1abb7417c5a49b88301931a9fe29", "registry-1.docker.io", "application/vnd.oci.image.index.v1+json", 3),
    "liveness-probe": ("registry.k8s.io/sig-storage/livenessprobe", "v2.20.0", ["controller", "node"], "sha256:19f2cf2f40e1987c7943945deca5f65cd4e4bf5cc0657fc78a5df131861578e8", "registry.k8s.io", "application/vnd.docker.distribution.manifest.list.v2+json", 8),
}
ACCEPT_MEDIA_TYPES = [
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
]


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
    for name, (repository, tag, consumers, expected_digest, registry_host, media_type, manifest_count) in EXPECTED.items():
        item = images.get(name)
        if not isinstance(item, dict) or set(item) != {"repository", "tag", "digest", "consumers", "registryEvidence"}:
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
        elif digest != expected_digest:
            problems.append("IMAGE_DIGEST_DRIFT:" + name)
        evidence = item.get("registryEvidence")
        if not isinstance(evidence, dict) or evidence != {
            "registryHost": registry_host,
            "resolvedAt": "2026-11-19T00:53:35Z",
            "mediaType": media_type,
            "manifestCount": manifest_count,
            "linuxAmd64Present": True,
            "dockerContentDigestMatchedBody": True,
        }:
            problems.append("REGISTRY_EVIDENCE_INVALID:" + name)
        if "latest" in reference.lower():
            problems.append("MUTABLE_IMAGE_TAG_FORBIDDEN:" + name)
    status = lock.get("status")
    if all_pinned and status != "render-verified-not-runtime-qualified":
        problems.append("DIGEST_STATUS_INVALID")
    if not all_pinned and status != "inventory-complete-digests-unresolved":
        problems.append("UNRESOLVED_STATUS_INVALID")
    render = lock.get("render")
    if not isinstance(render, dict) or render != {
        "manifestPath": "release/evidence/hcloud-csi-2.24.2-render.yaml",
        "manifestSha256": "1fb2e34ccb267064ee8c84084bab78fd2777afef906b2767b51722500caa6fbc",
        "verified": True,
        "renderedAt": "2026-11-19T15:58:28Z",
        "releaseName": "werftkern-hcloud-csi",
        "namespace": "kube-system",
        "kubernetesVersion": "1.37.2",
        "documentCount": 11,
        "imageReferenceCount": 8,
        "chart": {
            "url": "https://github.com/hetznercloud/csi-driver/releases/download/v2.24.2/hcloud-csi-2.24.2.tgz",
            "sha256": "1f4ebe7d2a8b06e95559a5315ecf125e158ccdadc8a6aae885c7ecd33a7fb4f6",
        },
        "values": {
            "path": "examples/kubernetes/hcloud-csi-values.example.yaml",
            "sha256": "360dbe6dfd68a20a600e90683c142438fbcf80fba7fb57411ad0f6dc0554a9f1",
        },
        "nodeServiceAccount": {
            "path": "examples/kubernetes/hcloud-csi-node-serviceaccount.yaml",
            "sha256": "494c760af35dd6a4307f17a7d5fd840b1c70e6de3a39bdde8568374421c66b7b",
        },
        "helm": {
            "version": "v3.22.1",
            "archiveUrl": "https://get.helm.sh/helm-v3.22.1-linux-amd64.tar.gz",
            "archiveSha256": "896cf63684a42a723d61c980369d6e588330927deb13676ca0d85006dd6da0ea",
            "binarySha256": "46aeab5e043f62d01f7c168823b392cabc1cea3807b67906296290483791be43",
            "signatureVerified": False,
        },
    }:
        problems.append("RENDER_STATE_INVALID")
    limitations = lock.get("limitations")
    if not isinstance(limitations, list) or not limitations or any(not isinstance(v, str) or not v for v in limitations):
        problems.append("LIMITATIONS_MISSING")
    if "latest" in json.dumps(lock).lower():
        problems.append("MUTABLE_LATEST_REFERENCE_FORBIDDEN")
    return problems


def fetch_manifest(repository: str, tag: str) -> dict:
    if repository.startswith("registry.k8s.io/"):
        registry_host = "registry.k8s.io"
        registry_path = repository.removeprefix("registry.k8s.io/")
        headers = {}
    elif repository.startswith("docker.io/"):
        registry_host = "registry-1.docker.io"
        registry_path = repository.removeprefix("docker.io/")
        query = urllib.parse.urlencode({
            "service": "registry.docker.io",
            "scope": f"repository:{registry_path}:pull",
        })
        with urllib.request.urlopen("https://auth.docker.io/token?" + query, timeout=30) as response:
            token = json.load(response)["token"]
        headers = {"Authorization": "Bearer " + token}
    else:
        raise ValueError("unsupported registry")
    headers.update({
        "Accept": ", ".join(ACCEPT_MEDIA_TYPES),
        "User-Agent": "werftkern-production-qualification/1",
    })
    url = f"https://{registry_host}/v2/{registry_path}/manifests/{tag}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        body = response.read(5_000_001)
        if len(body) > 5_000_000:
            raise ValueError("manifest too large")
        digest_header = response.headers.get("Docker-Content-Digest")
        media_type = response.headers.get_content_type()
    document = json.loads(body)
    manifests = document.get("manifests", [])
    return {
        "digest": digest_header,
        "computedDigest": "sha256:" + hashlib.sha256(body).hexdigest(),
        "mediaType": media_type,
        "manifestCount": len(manifests),
        "linuxAmd64Present": any(
            manifest.get("platform", {}).get("os") == "linux"
            and manifest.get("platform", {}).get("architecture") == "amd64"
            for manifest in manifests if isinstance(manifest, dict)
        ),
    }


def verify_registry(lock: dict, fetcher=fetch_manifest) -> list[str]:
    problems: list[str] = []
    for name, item in lock.get("images", {}).items():
        if not isinstance(item, dict):
            problems.append("REGISTRY_LOOKUP_FAILED:" + name)
            continue
        try:
            observed = fetcher(item["repository"], item["tag"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            problems.append("REGISTRY_LOOKUP_FAILED:" + name)
            continue
        evidence = item.get("registryEvidence", {})
        if observed.get("digest") != observed.get("computedDigest"):
            problems.append("REGISTRY_HEADER_BODY_MISMATCH:" + name)
        if observed.get("digest") != item.get("digest"):
            problems.append("REGISTRY_TAG_DIGEST_DRIFT:" + name)
        if observed.get("mediaType") != evidence.get("mediaType"):
            problems.append("REGISTRY_MEDIA_TYPE_DRIFT:" + name)
        if observed.get("manifestCount") != evidence.get("manifestCount"):
            problems.append("REGISTRY_MANIFEST_COUNT_DRIFT:" + name)
        if observed.get("linuxAmd64Present") is not True:
            problems.append("REGISTRY_LINUX_AMD64_MISSING:" + name)
    return problems


def extract_images(rendered: str) -> list[str]:
    return [match.group(1) for line in rendered.splitlines() if (match := IMAGE_LINE.match(line))]


def validate_render(rendered: str, lock: dict) -> list[str]:
    problems: list[str] = []
    images = extract_images(rendered)
    if not images:
        return ["RENDER_CONTAINS_NO_IMAGES"]
    render = lock.get("render", {})
    if hashlib.sha256(rendered.encode()).hexdigest() != render.get("manifestSha256"):
        problems.append("RENDER_SHA256_MISMATCH")
    if sum(line == "---" for line in rendered.splitlines()) != render.get("documentCount"):
        problems.append("RENDER_DOCUMENT_COUNT_MISMATCH")
    if len(images) != render.get("imageReferenceCount"):
        problems.append("RENDER_IMAGE_COUNT_MISMATCH")
    required = [
        "kind: StorageClass",
        "name: werftkern-hcloud-retain",
        'storageclass.kubernetes.io/is-default-class: "false"',
        "volumeBindingMode: WaitForFirstConsumer",
        "allowVolumeExpansion: true",
        'reclaimPolicy: "Retain"',
        "replicas: 2",
        "/var/lib/k0s/kubelet",
        "name: werftkern-hcloud-csi-node",
        "automountServiceAccountToken: false",
        "serviceAccountName: werftkern-hcloud-csi-node",
        "seccompProfile:",
        "type: RuntimeDefault",
    ]
    for marker in required:
        if marker not in rendered:
            problems.append("RENDER_REQUIRED_MARKER_MISSING:" + marker)
    if re.search(r"(?m)^kind:\s*Secret\s*$", rendered):
        problems.append("RENDER_MUST_NOT_CREATE_SECRET")
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
    parser.add_argument("--verify-registry", action="store_true")
    args = parser.parse_args()
    try:
        if args.lock.stat().st_size > 1_000_000:
            raise ValueError("lock too large")
        lock = parse_json(args.lock.read_text())
        problems = validate_lock(lock)
        registry_verified = False
        if args.verify_registry:
            registry_problems = verify_registry(lock)
            problems.extend(registry_problems)
            registry_verified = not registry_problems
        rendered_sha = None
        render_verified = False
        rendered_path = args.rendered
        if rendered_path is None and lock.get("render", {}).get("verified") is True:
            rendered_path = Path(lock["render"]["manifestPath"])
        if rendered_path is not None:
            if rendered_path.stat().st_size > 10_000_000:
                raise ValueError("render too large")
            rendered = rendered_path.read_text()
            rendered_sha = hashlib.sha256(rendered.encode()).hexdigest()
            render_problems = validate_render(rendered, lock)
            problems.extend(render_problems)
            render_verified = not render_problems
    except (OSError, ValueError, TypeError, AttributeError):
        problems = ["IMAGE_LOCK_INPUT_INVALID"]
        lock = {}
        rendered_sha = None
        render_verified = False
        registry_verified = False
    images = lock.get("images", {}) if isinstance(lock, dict) else {}
    all_pinned = bool(images) and all(isinstance(v, dict) and isinstance(v.get("digest"), str) for v in images.values())
    print(json.dumps({
        "inventoryValid": not [p for p in problems if not p.startswith("UNRESOLVED_IMAGE_DIGEST:")],
        "imageDigestsPinned": all_pinned,
        "registryVerifiedNow": registry_verified,
        "renderVerified": render_verified,
        "renderedSha256": rendered_sha,
        "productionReady": False,
        "problems": problems,
        "notice": "Inventory validation and render policy are not signature, vulnerability or runtime qualification.",
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
