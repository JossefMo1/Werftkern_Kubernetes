import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "production_tracker", ROOT / "scripts/check-production-tracker.py"
)
TRACKER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(TRACKER)


class ProductionTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracker = TRACKER.parse((ROOT / "release/production-tracker.json").read_text())

    def test_tracker_is_actionable_but_cannot_claim_production(self):
        self.assertEqual(TRACKER.validate(self.tracker), [])
        self.assertFalse(self.tracker["productionReady"])
        self.assertEqual(self.tracker["nextAction"]["status"], "blocked-external")
        self.assertTrue(self.tracker["nextAction"]["blockers"])
        self.assertEqual(self.tracker["decision"]["status"], "no-go")
        self.assertEqual(self.tracker["decision"]["reasonCode"], "NO_REAL_LINUX_TEST_AUTHORIZED")

    def test_status_documents_current_candidate_handoff(self):
        status = (ROOT / "docs/STATUS.md").read_text()
        candidate = self.tracker["candidate"]["mainAfterCandidate"]
        self.assertIn(candidate["pullRequest"], status)
        self.assertIn(candidate["codeCommit"], status)
        self.assertIn(self.tracker["candidate"]["sourceCommit"], status)
        self.assertIn("production decision remains no-go", status)

    def test_missing_no_go_decision_is_rejected(self):
        changed = copy.deepcopy(self.tracker)
        del changed["decision"]
        self.assertIn("TRACKER_DECISION_MISSING", TRACKER.validate(changed))

    def test_production_decision_cannot_be_changed_without_live_basis(self):
        changed = copy.deepcopy(self.tracker)
        changed["decision"]["status"] = "go"
        self.assertIn("TRACKER_DECISION_NOT_NO_GO", TRACKER.validate(changed))

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            TRACKER.parse('{"status":"one","status":"two"}')

    def test_production_claim_and_unbacked_pass_are_rejected(self):
        changed = copy.deepcopy(self.tracker)
        changed["productionReady"] = True
        changed["workstreams"][0]["status"] = "passed"
        problems = TRACKER.validate(changed)
        self.assertIn("TRACKER_CANNOT_CLAIM_PRODUCTION", problems)
        self.assertIn("TRACKER_CANNOT_CLOSE_E2E_WITHOUT_RELEASE_EVIDENCE:E2E-00", problems)

    def test_blocked_workstream_requires_a_concrete_blocker(self):
        changed = copy.deepcopy(self.tracker)
        stream = next(item for item in changed["workstreams"] if item["id"] == "E2E-K01")
        stream["blockers"] = []
        self.assertIn("TRACKER_BLOCKER_MISSING:E2E-K01", TRACKER.validate(changed))

    def test_blocked_workstream_rejects_non_string_blockers(self):
        changed = copy.deepcopy(self.tracker)
        stream = next(item for item in changed["workstreams"] if item["id"] == "E2E-K01")
        stream["blockers"] = "missing lab"
        self.assertIn("TRACKER_BLOCKERS_INVALID:E2E-K01", TRACKER.validate(changed))

    def test_decision_requires_nonempty_evidence_lists(self):
        changed = copy.deepcopy(self.tracker)
        changed["decision"]["basis"] = []
        changed["decision"]["blockingGates"] = ["  "]
        problems = TRACKER.validate(changed)
        self.assertIn("TRACKER_DECISION_BASIS_INVALID", problems)
        self.assertIn("TRACKER_DECISION_GATES_INVALID", problems)

    def test_next_action_requires_nonempty_evidence_contract(self):
        changed = copy.deepcopy(self.tracker)
        changed["nextAction"]["blockers"] = []
        changed["nextAction"]["successCriteria"] = []
        self.assertIn("TRACKER_NEXT_ACTION_EVIDENCE_INVALID", TRACKER.validate(changed))

    def test_next_action_requires_nonempty_safe_rollback(self):
        changed = copy.deepcopy(self.tracker)
        changed["nextAction"]["safeRollback"] = "  "
        self.assertIn("TRACKER_NEXT_ACTION_EVIDENCE_INVALID", TRACKER.validate(changed))

    def test_workstream_requires_nonempty_gate_families(self):
        changed = copy.deepcopy(self.tracker)
        stream = next(item for item in changed["workstreams"] if item["id"] == "E2E-K01")
        stream["requiredGateFamilies"] = []
        self.assertIn("TRACKER_GATE_FAMILIES_INVALID:E2E-K01", TRACKER.validate(changed))


if __name__ == "__main__":
    unittest.main()
