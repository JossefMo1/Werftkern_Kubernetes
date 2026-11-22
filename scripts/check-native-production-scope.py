#!/usr/bin/env python3
"""Validate the first production target without granting production readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_GATES = {
    "unit-race",
    "static-analysis",
    "source-audit",
    "supported-toolchain-security",
    "ubuntu-install-e2e",
    "real-engine-etcd",
    "single-host-restart-and-workload-recovery",
    "single-host-backup-restore",
    "single-host-upgrade-rollback",
    "single-host-load-soak",
    "negative-authorization-and-secure-defaults",
    "signed-artifacts-and-provenance",
    "maintainer-approval",
}

CROSS_PATH_GATES = {
    "reproducible-clean-build",
    "artifact-commit-digest-identity",
    "unit-race-contract-integration-package-source-vulnerability",
    "sbom-dependency-supply-chain",
    "signed-artifacts-and-provenance",
    "install-uninstall-reinstall",
    "operator-runbooks",
    "published-rc-and-user-feedback",
    "final-go-no-go",
}


def parse_json(text: str):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=unique_object)


def _strings(value):
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def validate(scope: dict) -> list[str]:
    problems = []
    if scope.get("schema") != "werftkern/native-production-scope/v1":
        problems.append("SCHEMA_INVALID")
    if scope.get("status") != "production-target-not-qualified":
        problems.append("STATUS_INVALID")
    if scope.get("productionTarget") is not True:
        problems.append("PRODUCTION_TARGET_REQUIRED")
    if scope.get("productionReady") is not False:
        problems.append("SCOPE_MUST_REMAIN_UNQUALIFIED")
    if scope.get("exactCandidateRequired") is not True:
        problems.append("EXACT_CANDIDATE_REQUIRED")
    if scope.get("releaseProfile") != "native-single-host-production":
        problems.append("RELEASE_PROFILE_INVALID")
    if scope.get("primaryProductionSurface") != "native-runtime":
        problems.append("PRIMARY_SURFACE_INVALID")

    paths = scope.get("paths")
    if not isinstance(paths, dict) or set(paths) != {"native", "kubernetes"}:
        return problems + ["PATH_INVENTORY_INVALID"]

    native = paths["native"]
    expected = {
        "supportLevel": "production-with-explicit-boundaries",
        "componentVersion": "0.2.0-dev.4",
        "stateSchema": 2,
        "engine": "docker-engine",
        "operatingSystem": "ubuntu-24.04-lts-amd64",
        "topology": "one-controller-and-one-worker-on-one-host",
        "trustBoundary": "single-trusted-administrator-and-trusted-workloads",
        "installation": "fresh-host-only",
        "upgradePath": "candidate-specific-same-schema-package-upgrade-after-backup",
        "rollback": "candidate-specific-single-host-package-rollback-must-pass-live-qualification",
        "requiredDependencies": ["systemd", "cgroup-v2", "docker-engine", "etcd"],
    }
    if not isinstance(native, dict):
        problems.append("NATIVE_PATH_INVALID")
    else:
        for key, value in expected.items():
            if native.get(key) != value:
                problems.append(f"NATIVE_BOUNDARY_INVALID:{key}")
        gates = native.get("qualificationGates")
        if not _strings(gates) or set(gates) != REQUIRED_GATES or len(gates) != len(REQUIRED_GATES):
            problems.append("NATIVE_GATE_INVENTORY_INVALID")

    kubernetes = paths["kubernetes"]
    if (
        not isinstance(kubernetes, dict)
        or kubernetes.get("productionIncluded") is not False
        or kubernetes.get("supportLevel") != "experimental-not-production"
    ):
        problems.append("KUBERNETES_MUST_REMAIN_EXPERIMENTAL")

    cross = scope.get("crossPathReleaseGates")
    if not _strings(cross) or set(cross) != CROSS_PATH_GATES or len(cross) != len(CROSS_PATH_GATES):
        problems.append("CROSS_PATH_GATE_INVENTORY_INVALID")

    deferred = scope.get("deferredProductionScopes")
    if not _strings(deferred) or len(deferred) != len(set(deferred)):
        problems.append("DEFERRED_SCOPE_INVENTORY_INVALID")

    promotion = scope.get("promotion")
    if (
        not isinstance(promotion, dict)
        or promotion.get("deferredGatesMustRemainExplicit") is not True
        or not _strings(promotion.get("neverClaim"))
        or not isinstance(promotion.get("productionReadyMayBecomeTrueOnlyWhen"), str)
        or not promotion["productionReadyMayBecomeTrueOnlyWhen"].strip()
    ):
        problems.append("PROMOTION_RULE_INVALID")

    reference = scope.get("fullScopeReference")
    if (
        not isinstance(reference, dict)
        or reference.get("path") != "release/production-scope.json"
        or not isinstance(reference.get("meaning"), str)
        or not reference["meaning"].strip()
    ):
        problems.append("FULL_SCOPE_REFERENCE_INVALID")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, default=Path("release/native-production-scope.json"))
    args = parser.parse_args()
    try:
        scope = parse_json(args.scope.read_text())
        problems = validate(scope)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        problems = ["SCOPE_INPUT_INVALID"]
    result = {
        "scopeValid": not problems,
        "productionTarget": True,
        "productionReady": False,
        "status": "PRODUCTION_TARGET_VALID" if not problems else "SCOPE_INVALID",
        "problems": problems,
        "notice": "This validates the declared boundary only; it does not qualify a release.",
    }
    print(json.dumps(result, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
