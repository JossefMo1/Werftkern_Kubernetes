#!/usr/bin/env python3
"""Validate the bounded production-scope proposal without granting readiness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NATIVE_GATES = {
    "unit-race", "static-analysis", "source-audit", "supported-toolchain-security",
    "ubuntu-install-e2e", "real-engine-etcd", "multi-node-network", "ha-partition",
    "restore-new-host", "upgrade-rollback", "load-soak", "independent-security",
    "maintainer-approval",
}
KUBERNETES_REQUIREMENTS = {
    "controller-replacement", "stateful-self-healing", "full-pv-database-recovery",
    "ubuntu-k0s-e2e", "ha-chaos", "cloud-e2e", "keycloak-login-negative-rbac",
    "cert-manager-acme", "sonobuoy-certified-conformance", "cncf-submission-acceptance",
    "real-upgrade-rollback", "load-soak-faults", "signed-supply-chain",
    "independent-security",
}
CROSS_PATH_GATES = {
    "reproducible-clean-build", "artifact-commit-digest-identity",
    "unit-race-contract-integration-package-source-vulnerability",
    "sbom-dependency-supply-chain", "signed-artifacts-and-provenance",
    "install-uninstall-reinstall", "upgrade-and-rollback",
    "backup-restore-and-new-host-restore", "multi-host-ha-partition-and-restart",
    "negative-authorization-and-secure-defaults", "load-soak-and-fault-limits",
    "operator-runbooks", "published-rc-and-user-feedback",
    "independent-review-where-required", "final-go-no-go",
}
REQUIRED_PINS = {"k0s", "k0sctl", "kubernetes", "storageProfile", "addonImagesAndCharts"}


def parse_json(text: str):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=unique_object)


def _set(value):
    return set(value) if isinstance(value, list) and all(isinstance(v, str) for v in value) else set()


def _unique_strings(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value) and len(value) == len(set(value))


def validate(scope: dict, qualification: dict, kubernetes: dict) -> list[str]:
    problems: list[str] = []
    if scope.get("schema") != "werftkern/production-scope/v1":
        problems.append("SCHEMA_INVALID")
    if scope.get("status") != "candidate-not-qualified" or scope.get("productionReady") is not False:
        problems.append("SCOPE_MUST_REMAIN_UNQUALIFIED")
    if scope.get("exactCandidateRequired") is not True:
        problems.append("EXACT_CANDIDATE_REQUIRED")
    if (
        qualification.get("scope") != "full-masterplan"
        or qualification.get("productionReady") is not False
        or kubernetes.get("productionReady") is not False
        or kubernetes.get("fullMasterplanComplete") is not False
        or kubernetes.get("cncfCertified") is not False
    ):
        problems.append("UPSTREAM_READINESS_CONTRACT_INVALID")

    paths = scope.get("paths")
    if not isinstance(paths, dict) or set(paths) != {"native", "kubernetes"}:
        return problems + ["PATH_INVENTORY_INVALID"]
    native, kube = paths["native"], paths["kubernetes"]
    if (
        not isinstance(native, dict)
        or native.get("componentVersion") != "0.2.0-dev.4"
        or native.get("engine") != "docker-engine"
        or native.get("stateSchema") != 2
        or native.get("operatingSystem") != "ubuntu-24.04-lts-amd64"
        or native.get("topology") != "exactly-three-controllers-and-at-least-three-workers"
        or native.get("trustBoundary") != "single-trusted-administrator-and-trusted-workloads"
        or native.get("installation") != "fresh-hosts-only"
        or native.get("upgradePath") != "dev3-workers-to-dev4-after-all-controllers-run-dev4"
        or native.get("requiredDependencies") != ["systemd", "cgroup-v2", "docker-engine", "etcd"]
    ):
        problems.append("NATIVE_BOUNDARY_INVALID")
    if (
        not isinstance(kube, dict)
        or kube.get("componentVersion") != "0.1.0-dev.3"
        or kube.get("engine") != "k0s-kubernetes"
        or "stateSchema" in kube
        or kube.get("managementHost") != "ubuntu-24.04-lts-amd64-python-3.10-or-newer"
        or kube.get("targetHosts") != "ubuntu-24.04-lts-amd64"
        or kube.get("topology") != "exactly-three-controllers-and-at-least-three-workers-with-external-ha-api-endpoint"
        or kube.get("trustBoundary") != "single-trusted-administrator-and-one-cluster"
        or kube.get("installation") != "fresh-target-hosts-only"
        or kube.get("upgradePath") != "one-adjacent-qualified-kubernetes-minor-edge-to-be-pinned"
    ):
        problems.append("KUBERNETES_BOUNDARY_INVALID")

    manifest_gates = set(qualification.get("gates", {}))
    if (
        not _unique_strings(native.get("qualificationGates"))
        or _set(native.get("qualificationGates")) != NATIVE_GATES
        or manifest_gates != NATIVE_GATES
    ):
        problems.append("NATIVE_GATE_INVENTORY_MISMATCH")
    readiness_ids = {
        item.get("id") for item in kubernetes.get("requirements", []) if isinstance(item, dict)
    }
    if (
        not _unique_strings(kube.get("qualificationRequirements"))
        or _set(kube.get("qualificationRequirements")) != KUBERNETES_REQUIREMENTS
        or readiness_ids != KUBERNETES_REQUIREMENTS
    ):
        problems.append("KUBERNETES_REQUIREMENT_INVENTORY_MISMATCH")
    if not _unique_strings(scope.get("crossPathReleaseGates")) or _set(scope.get("crossPathReleaseGates")) != CROSS_PATH_GATES:
        problems.append("CROSS_PATH_GATE_INVENTORY_MISMATCH")

    pins = kube.get("requiredPinnings")
    if not isinstance(pins, dict) or set(pins) != REQUIRED_PINS:
        problems.append("PIN_INVENTORY_INVALID")
    else:
        matrix = "release/kubernetes-target-matrix.json"
        for key in ("k0s", "k0sctl", "kubernetes"):
            if pins.get(key) != {"status": "pinned", "targetMatrix": matrix}:
                problems.append("CORE_PIN_REFERENCE_INVALID:" + key)
        for key in ("storageProfile", "addonImagesAndCharts"):
            if pins.get(key) != {"status": "unresolved"}:
                problems.append("UNRESOLVED_PIN_STATE_INVALID:" + key)

    plan = scope.get("fullMasterplan")
    features = set(qualification.get("features", {}))
    in_scope = _set(plan.get("inCandidateScope")) if isinstance(plan, dict) else set()
    deferred = plan.get("deferred", {}) if isinstance(plan, dict) else {}
    deferred_ids = set(deferred) if isinstance(deferred, dict) else set()
    if not isinstance(plan, dict) or plan.get("currentQualificationContract") != "full-masterplan-all-52-remain-blocking":
        problems.append("MASTERPLAN_QUALIFICATION_CONTRACT_INVALID")
    if not _unique_strings(plan.get("inCandidateScope") if isinstance(plan, dict) else None):
        problems.append("MASTERPLAN_IN_SCOPE_INVALID")
    if in_scope & deferred_ids:
        problems.append("MASTERPLAN_CLASSIFICATION_OVERLAP")
    if in_scope | deferred_ids != features or features != {f"K20-{i:03d}" for i in range(1, 53)}:
        problems.append("MASTERPLAN_CLASSIFICATION_INCOMPLETE")
    if not isinstance(deferred, dict) or any(not isinstance(v, str) or not v.strip() for v in deferred.values()):
        problems.append("MASTERPLAN_DEFERRAL_REASON_MISSING")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        scope = parse_json((root / "release/production-scope.json").read_text())
        qualification = parse_json((root / "release/qualification.json").read_text())
        kubernetes = parse_json((root / "release/kubernetes-readiness.json").read_text())
        problems = validate(scope, qualification, kubernetes)
    except (OSError, ValueError, TypeError, AttributeError):
        problems = ["SCOPE_INPUT_INVALID"]
    print(json.dumps({
        "scopeValid": not problems,
        "productionReady": False,
        "status": "CANDIDATE_SCOPE_VALID" if not problems else "SCOPE_INVALID",
        "problems": problems,
        "notice": "Scope validation is not release qualification or production approval.",
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
