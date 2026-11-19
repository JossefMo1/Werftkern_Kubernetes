#!/usr/bin/env python3
"""Validate immutable hcloud-csi linux/amd64 image runtime metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
ACCEPT = ", ".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])


def parse_json(text: str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def _sha(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def validate(profile: dict, lock: dict) -> list[str]:
    problems: list[str] = []
    if profile.get("schema") != "werftkern/hcloud-csi-runtime-profile/v1":
        problems.append("SCHEMA_INVALID")
    if (
        profile.get("status") != "audited-root-defaults-container-security-context-required"
        or profile.get("productionReady") is not False
        or profile.get("runAsNonRootSafeAtPodLevel") is not False
        or profile.get("platform") != "linux-amd64"
        or profile.get("sourceImageLock") != "release/hcloud-csi-image-lock.json"
    ):
        problems.append("RUNTIME_BOUNDARY_INVALID")
    images = profile.get("images")
    locked = lock.get("images")
    if not isinstance(images, dict) or not isinstance(locked, dict) or set(images) != set(locked):
        return problems + ["IMAGE_INVENTORY_MISMATCH"]
    for name, item in images.items():
        if not isinstance(item, dict) or set(item) != {
            "indexDigest", "platformManifestDigest", "configDigest", "configuredUser", "entrypoint"
        }:
            problems.append("IMAGE_PROFILE_INVALID:" + name)
            continue
        if item.get("indexDigest") != locked[name].get("digest"):
            problems.append("INDEX_DIGEST_MISMATCH:" + name)
        if not DIGEST.fullmatch(item.get("platformManifestDigest", "")):
            problems.append("PLATFORM_DIGEST_INVALID:" + name)
        if not DIGEST.fullmatch(item.get("configDigest", "")):
            problems.append("CONFIG_DIGEST_INVALID:" + name)
        if item.get("configuredUser") not in ("", "0", "root"):
            problems.append("UNPROVEN_NONROOT_USER:" + name)
        entrypoint = item.get("entrypoint")
        if not isinstance(entrypoint, list) or not entrypoint or any(not isinstance(v, str) or not v for v in entrypoint):
            problems.append("ENTRYPOINT_INVALID:" + name)
    limitations = profile.get("limitations")
    if not isinstance(limitations, list) or len(limitations) < 5 or any(not isinstance(v, str) or not v for v in limitations):
        problems.append("LIMITATIONS_INCOMPLETE")
    return problems


def _request(url: str, token: str | None = None, accept: str | None = None):
    headers = {"User-Agent": "werftkern-runtime-profile/1"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if accept:
        headers["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return response.read(), response.headers


def _docker_token(repository: str) -> str:
    query = urllib.parse.urlencode({"service": "registry.docker.io", "scope": f"repository:{repository}:pull"})
    body, _ = _request("https://auth.docker.io/token?" + query)
    document = parse_json(body.decode("utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("token"), str):
        raise ValueError("registry token response must be an object with a string token")
    return document["token"]


def verify_registry(profile: dict, lock: dict) -> list[str]:
    problems: list[str] = []
    for name, expected in profile["images"].items():
        repository = lock["images"][name]["repository"]
        digest = expected["indexDigest"]
        if repository.startswith("docker.io/"):
            path = repository.removeprefix("docker.io/")
            base = "https://registry-1.docker.io/v2/" + path
            token = _docker_token(path)
        elif repository.startswith("registry.k8s.io/"):
            path = repository.removeprefix("registry.k8s.io/")
            base = "https://registry.k8s.io/v2/" + path
            token = None
        else:
            problems.append("REGISTRY_UNSUPPORTED:" + name)
            continue
        body, headers = _request(base + "/manifests/" + digest, token, ACCEPT)
        if _sha(body) != digest or headers.get("Docker-Content-Digest", digest) != digest:
            problems.append("INDEX_BODY_DIGEST_MISMATCH:" + name)
            continue
        index = parse_json(body.decode())
        if not isinstance(index, dict):
            raise ValueError("registry index must be an object")
        candidates = [m for m in index.get("manifests", []) if m.get("platform", {}).get("os") == "linux"
                      and m.get("platform", {}).get("architecture") == "amd64"
                      and not m.get("platform", {}).get("variant")]
        if len(candidates) != 1 or candidates[0].get("digest") != expected["platformManifestDigest"]:
            problems.append("PLATFORM_MANIFEST_MISMATCH:" + name)
            continue
        manifest_digest = candidates[0]["digest"]
        body, headers = _request(base + "/manifests/" + manifest_digest, token, ACCEPT)
        if _sha(body) != manifest_digest or headers.get("Docker-Content-Digest", manifest_digest) != manifest_digest:
            problems.append("PLATFORM_BODY_DIGEST_MISMATCH:" + name)
            continue
        manifest = parse_json(body.decode())
        if not isinstance(manifest, dict):
            raise ValueError("registry manifest must be an object")
        config_digest = manifest.get("config", {}).get("digest")
        if config_digest != expected["configDigest"]:
            problems.append("CONFIG_DESCRIPTOR_MISMATCH:" + name)
            continue
        body, _ = _request(base + "/blobs/" + config_digest, token)
        if _sha(body) != config_digest:
            problems.append("CONFIG_BODY_DIGEST_MISMATCH:" + name)
            continue
        config_document = parse_json(body.decode())
        if not isinstance(config_document, dict):
            raise ValueError("registry config must be an object")
        config = config_document.get("config", {})
        if not isinstance(config, dict):
            raise ValueError("registry config field must be an object")
        if config.get("User", "") != expected["configuredUser"]:
            problems.append("CONFIG_USER_MISMATCH:" + name)
        if config.get("Entrypoint") != expected["entrypoint"]:
            problems.append("CONFIG_ENTRYPOINT_MISMATCH:" + name)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=Path("release/hcloud-csi-runtime-profile.json"))
    parser.add_argument("--lock", type=Path, default=Path("release/hcloud-csi-image-lock.json"))
    parser.add_argument("--verify-registry", action="store_true")
    args = parser.parse_args()
    registry_verified = False
    try:
        if args.profile.stat().st_size > 1_000_000 or args.lock.stat().st_size > 1_000_000:
            raise ValueError("input too large")
        profile = parse_json(args.profile.read_text())
        lock = parse_json(args.lock.read_text())
        problems = validate(profile, lock)
        if args.verify_registry and not problems:
            problems.extend(verify_registry(profile, lock))
            registry_verified = not problems
    except (OSError, ValueError, TypeError, AttributeError, urllib.error.URLError, json.JSONDecodeError):
        problems = ["RUNTIME_PROFILE_INPUT_INVALID"]
    print(json.dumps({
        "profileValid": not problems,
        "registryVerifiedNow": registry_verified,
        "runAsNonRootSafeAtPodLevel": False,
        "productionReady": False,
        "problems": problems,
        "notice": "Immutable config metadata is not runtime, vulnerability, signature or production qualification.",
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
