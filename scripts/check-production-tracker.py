#!/usr/bin/env python3
"""Fail closed on a production tracker that could overstate release readiness."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "release/production-tracker.json"
ALLOWED = {"not-started", "prepared", "in-progress", "blocked-external", "failed", "passed"}
REQUIRED_STREAMS = {"E2E-00", "E2E-K01", "E2E-N01", "E2E-H01", "E2E-P01", "E2E-R01"}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse(raw: str) -> dict:
    value = json.loads(raw, object_pairs_hook=unique_pairs)
    if not isinstance(value, dict):
        raise ValueError("tracker must be an object")
    return value


def validate(tracker: dict) -> list[str]:
    problems: list[str] = []
    if tracker.get("schema") != "werftkern/production-tracker/v1":
        problems.append("TRACKER_SCHEMA_INVALID")
    if tracker.get("status") != "active-not-production-ready" or tracker.get("productionReady") is not False:
        problems.append("TRACKER_CANNOT_CLAIM_PRODUCTION")
    sources = tracker.get("sources")
    if sources != {
        "productionScope": "release/production-scope.json",
        "nativeQualification": "release/qualification.json",
        "kubernetesReadiness": "release/kubernetes-readiness.json",
        "e2ePlan": "docs/PRODUCTION-E2E-PLAN-DE.md",
    }:
        problems.append("TRACKER_SOURCES_INVALID")
    next_action = tracker.get("nextAction")
    if not isinstance(next_action, dict) or next_action.get("id") != "E2E-K01-PREFLIGHT":
        problems.append("TRACKER_NEXT_ACTION_INVALID")
    elif (
        next_action.get("priority") != "P0"
        or next_action.get("status") != "blocked-external"
        or not all(isinstance(value, str) and value for value in next_action.get("blockers", []))
        or not all(isinstance(value, str) and value for value in next_action.get("successCriteria", []))
        or not isinstance(next_action.get("safeRollback"), str)
    ):
        problems.append("TRACKER_NEXT_ACTION_EVIDENCE_INVALID")
    streams = tracker.get("workstreams")
    if not isinstance(streams, list):
        return problems + ["TRACKER_WORKSTREAMS_INVALID"]
    ids = [item.get("id") for item in streams if isinstance(item, dict)]
    if set(ids) != REQUIRED_STREAMS or len(ids) != len(set(ids)):
        problems.append("TRACKER_WORKSTREAM_SET_INVALID")
    for item in streams:
        if not isinstance(item, dict):
            problems.append("TRACKER_WORKSTREAM_INVALID")
            continue
        if item.get("status") not in ALLOWED:
            problems.append("TRACKER_WORKSTREAM_STATUS_INVALID:" + str(item.get("id")))
        if not all(isinstance(value, str) and value for value in item.get("requiredGateFamilies", [])):
            problems.append("TRACKER_GATE_FAMILIES_INVALID:" + str(item.get("id")))
        if item.get("status") == "passed":
            problems.append("TRACKER_CANNOT_CLOSE_E2E_WITHOUT_RELEASE_EVIDENCE:" + str(item.get("id")))
        if item.get("status") == "blocked-external" and not item.get("blockers"):
            problems.append("TRACKER_BLOCKER_MISSING:" + str(item.get("id")))
    return problems


def main() -> int:
    try:
        problems = validate(parse(TRACKER.read_text()))
        print(json.dumps({"valid": not problems, "productionReady": False, "problems": problems}, indent=2))
        return 0 if not problems else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "productionReady": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
