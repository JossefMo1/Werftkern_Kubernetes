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


if __name__ == "__main__":
    unittest.main()
