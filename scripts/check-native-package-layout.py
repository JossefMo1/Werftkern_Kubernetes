#!/usr/bin/env python3
"""Validate the command paths shipped in the native Ubuntu package.

This is intentionally a package-level contract: the native bootstrap entry point
must be available after apt/dpkg installation, otherwise the release cannot be
used for the documented E2E flow.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Iterable

REQUIRED_FILES = (
    "/usr/bin/werft",
    "/usr/bin/werft-ops",
    "/usr/lib/werftkern/ops/werftops/__main__.py",
)
REQUIRED_EXECUTABLES = (
    "/usr/bin/werft",
    "/usr/bin/werft-ops",
)


def _normalise_path(raw: str) -> str:
    path = raw.strip()
    if path.startswith("./"):
        path = path[1:]
    elif not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/")


def parse_listing(lines: Iterable[str]) -> dict[str, str]:
    """Return dpkg-deb mode bits for the paths in the package listing."""

    entries: dict[str, str] = {}
    for line in lines:
        fields = line.split()
        if len(fields) < 5:
            continue
        path = _normalise_path(fields[-1])
        if path in REQUIRED_FILES:
            entries[path] = fields[0]
    return entries


def validate_listing(lines: Iterable[str]) -> dict[str, object]:
    entries = parse_listing(lines)
    missing = [path for path in REQUIRED_FILES if path not in entries]
    non_executable = [
        path
        for path in REQUIRED_EXECUTABLES
        if path in entries
        and (not entries[path].startswith("-") or "x" not in entries[path][1:])
    ]
    if missing or non_executable:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if non_executable:
            details.append("not-executable=" + ",".join(non_executable))
        raise ValueError("native package layout invalid: " + "; ".join(details))
    return {
        "status": "passed",
        "requiredFiles": list(REQUIRED_FILES),
        "executables": list(REQUIRED_EXECUTABLES),
    }


def check_package(package: pathlib.Path) -> dict[str, object]:
    if not package.is_file():
        raise ValueError(f"package does not exist: {package}")
    result = subprocess.run(
        ["dpkg-deb", "--contents", str(package)],
        check=True,
        capture_output=True,
        text=True,
    )
    return validate_listing(result.stdout.splitlines())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the native package command/layout contract."
    )
    parser.add_argument("package", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        report = check_package(args.package)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"native package layout check failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
