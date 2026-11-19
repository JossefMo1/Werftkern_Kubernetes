import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "e2e_k01_preflight", ROOT / "scripts/check-e2e-k01-preflight.py"
)
CHECKER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CHECKER)


class E2EK01PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "lab-root"
        self.root.mkdir()
        self.assets = Path(self.temp.name) / "assets.json"
        self.plan = Path(self.temp.name) / "plan.json"
        self.assets.write_text("{}")
        self.plan.write_text("{}")

    def tearDown(self):
        self.temp.cleanup()

    def kwargs(self):
        return {
            "assets": str(self.assets),
            "plan": str(self.plan),
            "root": str(self.root),
            "attestation": CHECKER.ATTESTATION,
        }

    def test_valid_disposable_lab_inputs_are_ready(self):
        self.assertEqual(CHECKER.validate(**self.kwargs()), [])

    def test_missing_attestation_blocks_without_infrastructure_changes(self):
        values = self.kwargs()
        values["attestation"] = None
        self.assertIn("DISPOSABLE_LAB_ATTESTATION_REQUIRED", CHECKER.validate(**values))

    def test_relative_or_symlinked_inputs_block(self):
        values = self.kwargs()
        values["plan"] = "plan.json"
        self.assertIn("PLAN_MUST_BE_ABSOLUTE", CHECKER.validate(**values))
        link = Path(self.temp.name) / "plan-link.json"
        link.symlink_to(self.plan)
        values["plan"] = str(link)
        self.assertIn("PLAN_SYMLINK_FORBIDDEN", CHECKER.validate(**values))

    def test_broad_management_root_blocks(self):
        values = self.kwargs()
        values["root"] = "/"
        self.assertIn("ROOT_TOO_BROAD", CHECKER.validate(**values))


if __name__ == "__main__":
    unittest.main()
