#!/usr/bin/env python3
"""Create a deterministic, digest-bound Native candidate manifest.

This manifest binds the exact source commit, reproducible build timestamp,
Debian package bytes and SPDX document bytes. It is release evidence input
only: qualification, signing, provenance and maintainer approval remain
separate gates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
from typing import Any, NoReturn


COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"native-release-manifest: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    parser.add_argument("--sbom", required=True, type=pathlib.Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-date-epoch", required=True, type=int)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    return parser.parse_args()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        fail(f"unable to hash {path}: {exc}")
    return digest.hexdigest()


def package_field(package: pathlib.Path, field: str) -> str:
    import subprocess

    result = subprocess.run(
        ["dpkg-deb", "-f", str(package), field],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(f"unable to read package field {field}: {detail}")
    return result.stdout.strip()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"JSON root must be an object: {path}")
    return value


def main() -> int:
    args = parse_args()
    if not COMMIT_RE.fullmatch(args.source_commit):
        fail("source commit must be a 40-character lowercase Git SHA")
    if args.source_date_epoch < 0:
        fail("source date epoch must be non-negative")
    if not args.package.is_file() or args.package.is_symlink():
        fail("package must be a regular file")
    if not args.sbom.is_file() or args.sbom.is_symlink():
        fail("SBOM must be a regular file")

    package_sha256 = sha256_file(args.package)
    sbom_sha256 = sha256_file(args.sbom)
    package_name = package_field(args.package, "Package")
    package_version = package_field(args.package, "Version")
    package_architecture = package_field(args.package, "Architecture")
    if not package_name or not package_version or not package_architecture:
        fail("Debian package metadata is incomplete")

    sbom = load_json(args.sbom)
    expected_namespace = f"https://werftkern.dev/spdx/native/{args.source_commit}"
    if sbom.get("spdxVersion") != "SPDX-2.3":
        fail("SBOM must use SPDX-2.3")
    if sbom.get("documentNamespace") != expected_namespace:
        fail("SBOM source commit namespace mismatch")
    created = dt.datetime.fromtimestamp(args.source_date_epoch, dt.timezone.utc)
    expected_created = created.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if sbom.get("creationInfo", {}).get("created") != expected_created:
        fail("SBOM creation timestamp mismatch")

    packages = sbom.get("packages")
    if not isinstance(packages, list):
        fail("SBOM packages must be a list")
    roots = [
        item
        for item in packages
        if isinstance(item, dict)
        and item.get("name") == package_name
        and item.get("versionInfo") == package_version
    ]
    if len(roots) != 1:
        fail("SBOM must contain exactly one root package entry")
    checksums = roots[0].get("checksums")
    if not isinstance(checksums, list) or {
        item.get("checksumValue")
        for item in checksums
        if isinstance(item, dict) and item.get("algorithm") == "SHA256"
    } != {package_sha256}:
        fail("SBOM package checksum does not match package bytes")

    manifest = {
        "schema": "werftkern/native-release-manifest/v1",
        "sourceCommit": args.source_commit,
        "sourceDateEpoch": args.source_date_epoch,
        "artifact": {
            "kind": "debian-package",
            "name": package_name,
            "version": package_version,
            "architecture": package_architecture,
            "fileName": args.package.name,
            "sha256": package_sha256,
        },
        "sbom": {
            "format": "SPDX-2.3",
            "fileName": args.sbom.name,
            "sha256": sbom_sha256,
            "documentNamespace": expected_namespace,
        },
        "reproducibleBuild": True,
        "qualified": False,
        "signed": False,
        "evidenceBoundary": (
            "Digest and source identity only. This does not claim Ubuntu VM "
            "qualification, vulnerability clearance, signing, provenance, "
            "production readiness or maintainer approval."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
