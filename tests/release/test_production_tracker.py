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

    def test_tracker_is_scoped_but_not_production_ready(self):
        self.assertEqual(TRACKER.validate(self.tracker), [])
        self.assertFalse(self.tracker["productionReady"])
        self.assertEqual(self.tracker["decision"]["scope"], "native-single-host-production")
        self.assertEqual(self.tracker["decision"]["status"], "no-go")

    def test_status_documents_current_candidate_handoff(self):
        status = (ROOT / "docs/STATUS.md").read_text()
        candidate = self.tracker["candidate"]["mainAfterCandidate"]
        self.assertIn(candidate["pullRequest"], status)
        self.assertIn(candidate["codeCommit"], status)
        self.assertIn(self.tracker["candidate"]["sourceCommit"], status)
        self.assertIn("production decision remains no-go", status)

    def test_main_handoff_commit_is_consistent(self):
        self.assertEqual(
            self.tracker["lastCompleted"]["commit"],
            self.tracker["candidate"]["mainAfterCandidate"]["commit"],
        )

    def test_main_handoff_commit_mismatch_is_rejected(self):
        changed = copy.deepcopy(self.tracker)
        changed["candidate"]["mainAfterCandidate"]["commit"] = "0" * 40
        self.assertIn("TRACKER_MAIN_HANDOFF_MISMATCH", TRACKER.validate(changed))

    def test_missing_no_go_decision_is_rejected(self):
        changed = copy.deepcopy(self.tracker)
        del changed["decision"]
        self.assertIn("TRACKER_DECISION_MISSING", TRACKER.validate(changed))

    def test_production_decision_cannot_be_changed_without_scoped_basis(self):
        changed = copy.deepcopy(self.tracker)
        changed["decision"]["status"] = "go"
        self.assertIn("TRACKER_DECISION_NOT_NO_GO", TRACKER.validate(changed))

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            TRACKER.parse('{"status":"one","status":"two"}')

    def test_production_claim_is_rejected(self):
        changed = copy.deepcopy(self.tracker)
        changed["productionReady"] = True
        self.assertIn("TRACKER_CANNOT_CLAIM_PRODUCTION", TRACKER.validate(changed))

    def test_deferred_workstream_requires_reason(self):
        changed = copy.deepcopy(self.tracker)
        stream = next(item for item in changed["workstreams"] if item["id"] == "E2E-H01")
        stream["status"] = "deferred-out-of-scope"
        stream["blockers"] = []
        self.assertIn("TRACKER_BLOCKERS_INVALID:E2E-H01", TRACKER.validate(changed))


if __name__ == "__main__":
    unittest.main()
