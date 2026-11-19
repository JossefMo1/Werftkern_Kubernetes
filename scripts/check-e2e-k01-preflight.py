#!/usr/bin/env python3
"""Fail closed before the real Kubernetes E2E runner can mutate a lab."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ATTESTATION = "WERFTKERN-DISPOSABLE-K0S-ONLY"
BLOCKED_ROOTS = {Path("/"), Path("/etc"), Path("/home"), Path("/root"), Path("/usr"), Path("/var"), Path("/opt")}


def _path(value: str | None, name: str, problems: list[str], directory: bool = False) -> Path | None:
    if not value:
        problems.append(f"{name}_MISSING")
        return None
    path = Path(value)
    if not path.is_absolute():
        problems.append(f"{name}_MUST_BE_ABSOLUTE")
        return None
    if path.is_symlink():
        problems.append(f"{name}_SYMLINK_FORBIDDEN")
        return None
    if directory and not path.is_dir():
        problems.append(f"{name}_DIRECTORY_MISSING")
    elif not directory and not path.is_file():
        problems.append(f"{name}_FILE_MISSING")
    return path


def validate(*, assets: str | None, plan: str | None, root: str | None, attestation: str | None) -> list[str]:
    problems: list[str] = []
    if attestation != ATTESTATION:
        problems.append("DISPOSABLE_LAB_ATTESTATION_REQUIRED")
    assets_path = _path(assets, "ASSETS", problems)
    plan_path = _path(plan, "PLAN", problems)
    root_path = _path(root, "ROOT", problems, directory=True)
    if root_path is not None:
        resolved = root_path.resolve()
        if resolved in BLOCKED_ROOTS:
            problems.append("ROOT_TOO_BROAD")
    if assets_path is not None and assets_path.stat().st_size > 16 * 1024 * 1024:
        problems.append("ASSETS_TOO_LARGE")
    if plan_path is not None and plan_path.stat().st_size > 1 * 1024 * 1024:
        problems.append("PLAN_TOO_LARGE")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", default=os.environ.get("WERFT_KUBE_ASSETS"))
    parser.add_argument("--plan", default=os.environ.get("WERFT_KUBE_PLAN"))
    parser.add_argument("--root", default=os.environ.get("WERFT_KUBE_ROOT"))
    parser.add_argument("--attestation", default=os.environ.get("WERFT_DISPOSABLE_CLUSTER_ATTESTATION"))
    args = parser.parse_args()
    problems = validate(assets=args.assets, plan=args.plan, root=args.root, attestation=args.attestation)
    result = {
        "status": "READY" if not problems else "BLOCKED",
        "productionReady": False,
        "checks": [
            "explicit disposable k0s attestation",
            "absolute non-symlink assets and plan files",
            "existing non-broad management root",
            "bounded input sizes",
        ],
        "problems": problems,
    }
    print(json.dumps(result, indent=2))
    return 0 if not problems else 3


if __name__ == "__main__":
    raise SystemExit(main())
