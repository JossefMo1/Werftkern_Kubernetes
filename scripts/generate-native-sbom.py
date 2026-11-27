#!/usr/bin/env python3
"""Create a deterministic, bounded SPDX document for a Native package.

The document deliberately records package metadata, declared runtime
dependencies and the Go module graph.  It is a supply-chain input for a
candidate release, not a claim that OS vulnerability scanning or signing has
completed; those gates remain separate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any


HEX_COMMIT = re.compile(r"^[0-9a-f]{7,64}$")
PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+.-]*$")


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"native-sbom: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    parser.add_argument("--modules", required=True, type=pathlib.Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-date-epoch", required=True, type=int)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    return parser.parse_args()


def sha256_file(path: pathlib.Path) -> str:
    """Return the content digest that binds the SBOM to the exact package bytes."""

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        fail(f"unable to hash package: {exc}")
    return digest.hexdigest()


def package_field(package: pathlib.Path, field: str) -> str:
    try:
        result = subprocess.run(
            ["dpkg-deb", "-f", str(package), field],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        fail(f"unable to read package field {field}: {exc}")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(f"unable to read package field {field}: {detail}")
    return result.stdout.strip()


def parse_module_stream(path: pathlib.Path) -> list[dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"unable to read Go module graph: {exc}")
    decoder = json.JSONDecoder()
    modules: list[dict[str, Any]] = []
    offset = 0
    while offset < len(raw):
        while offset < len(raw) and raw[offset].isspace():
            offset += 1
        if offset >= len(raw):
            break
        try:
            value, end = decoder.raw_decode(raw, offset)
        except json.JSONDecodeError as exc:
            fail(f"invalid Go module graph at offset {exc.pos}")
        if not isinstance(value, dict) or not isinstance(value.get("Path"), str):
            fail("Go module graph contains a malformed module")
        modules.append(value)
        offset = end
    if not modules:
        fail("Go module graph is empty")
    return modules


def dependency_names(depends: str) -> list[str]:
    names: set[str] = set()
    for clause in depends.split(","):
        for alternative in clause.split("|"):
            candidate = re.split(r"\s*[<(]", alternative.strip(), maxsplit=1)[0]
            candidate = candidate.strip()
            if candidate and PACKAGE_NAME.fullmatch(candidate):
                names.add(candidate)
    return sorted(names)


def spdx_id(kind: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"SPDXRef-{kind}-{digest}"


def package_entry(name: str, version: str, comment: str | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "SPDXID": spdx_id("Package", f"{name}@{version}"),
        "name": name,
        "versionInfo": version,
        "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False,
        "licenseConcluded": "NOASSERTION",
        "licenseDeclared": "NOASSERTION",
        "supplier": "NOASSERTION",
    }
    if comment:
        entry["packageComment"] = comment
    return entry


def main() -> int:
    args = parse_args()
    if args.source_date_epoch < 0:
        fail("source date epoch must be non-negative")
    if not HEX_COMMIT.fullmatch(args.source_commit):
        fail("source commit must be a lowercase hexadecimal Git object id")
    if not args.package.is_file():
        fail(f"package does not exist: {args.package}")
    modules = parse_module_stream(args.modules)
    package_sha256 = sha256_file(args.package)

    package_name = package_field(args.package, "Package")
    package_version = package_field(args.package, "Version")
    package_arch = package_field(args.package, "Architecture")
    package_depends = package_field(args.package, "Depends")
    if not package_name or not package_version or not package_arch:
        fail("package metadata is incomplete")

    packages: list[dict[str, Any]] = []
    root = package_entry(
        package_name,
        package_version,
        f"Native package architecture={package_arch}; sourceCommit={args.source_commit}; "
        f"packageSha256={package_sha256}. "
        "OS vulnerability scanning and signing are separate release gates.",
    )
    root["checksums"] = [{"algorithm": "SHA256", "checksumValue": package_sha256}]
    packages.append(root)
    seen = {package_name}
    for name in dependency_names(package_depends):
        if name not in seen:
            packages.append(package_entry(name, "NOASSERTION", "Declared Debian runtime dependency."))
            seen.add(name)

    module_packages: list[dict[str, Any]] = []
    for module in modules:
        name = module["Path"].strip()
        version = str(module.get("Version") or "NOASSERTION")
        if not name:
            fail("Go module path must not be empty")
        comment = "Go module graph entry"
        if isinstance(module.get("Sum"), str) and module["Sum"]:
            comment += f"; goSum={module['Sum']}"
        module_packages.append(package_entry(name, version, comment))
    packages.extend(module_packages)

    created = dt.datetime.fromtimestamp(args.source_date_epoch, dt.timezone.utc).replace(microsecond=0)
    root_id = root["SPDXID"]
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"werftkern-native-{package_version}-{args.source_commit[:12]}",
        "documentNamespace": f"https://werftkern.dev/spdx/native/{args.source_commit}",
        "creationInfo": {
            "created": created.isoformat().replace("+00:00", "Z"),
            "creators": ["Tool: werftkern-native-sbom/1.0"],
        },
        "documentComment": (
            "Bounded Native package SBOM generated from the exact source commit. "
            "It does not close OS vulnerability, signature, provenance or production gates."
        ),
        "packages": packages,
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": root_id,
            }
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    main()
