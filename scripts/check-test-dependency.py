#!/usr/bin/env python3
"""Validate the immutable metadata for the disposable etcd test dependency."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

EXPECTED = {
    "version": "v3.7.2",
    "architecture": "linux-amd64",
    "url": "https://github.com/etcd-io/etcd/releases/download/v3.7.2/etcd-v3.7.2-linux-amd64.tar.gz",
    "sha256": "3a3679bc51a4ee9d30bccea1da7cd4fe62c6fc1d2ca1255068d2c53bf3026135",
}
SHA256 = re.compile(r"[0-9a-f]{64}")


def parse_json(text: str) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    return value


def validate(metadata: dict) -> list[str]:
    problems = []
    if set(metadata) != {"version", "architecture", "url", "sha256", "source", "verifiedMetadataAt", "scope"}:
        problems.append("METADATA_KEYS_INVALID")
    for key, expected in EXPECTED.items():
        if metadata.get(key) != expected:
            problems.append(f"{key.upper()}_DRIFT")
    digest = metadata.get("sha256")
    if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
        problems.append("SHA256_INVALID")
    if not isinstance(metadata.get("source"), str) or not metadata["source"].startswith("https://api.github.com/"):
        problems.append("SOURCE_INVALID")
    if not isinstance(metadata.get("verifiedMetadataAt"), str) or not re.fullmatch(r"2026-\d{2}-\d{2}", metadata["verifiedMetadataAt"]):
        problems.append("VERIFIED_DATE_INVALID")
    if metadata.get("scope") != "CI test dependency; not a completed product support qualification":
        problems.append("SCOPE_BOUNDARY_INVALID")
    return problems


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("tests/runtime/etcd-tool.json")
    try:
        if path.stat().st_size > 1_000_000:
            raise ValueError("metadata too large")
        metadata = parse_json(path.read_text())
        problems = validate(metadata)
        if problems:
            raise ValueError(",".join(problems))
        print(metadata["url"])
        print(metadata["sha256"])
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"test dependency metadata rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
