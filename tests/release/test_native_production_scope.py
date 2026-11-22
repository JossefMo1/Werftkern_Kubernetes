import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "native_production_scope", ROOT / "scripts/check-native-production-scope.py"
)
SCOPE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SCOPE)


class NativeProductionScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = json.loads(
            (ROOT / "release/native-production-scope.json").read_text()
        )

    def test_scope_is_valid_production_target_but_not_qualified(self):
        self.assertEqual(SCOPE.validate(self.scope), [])
        self.assertTrue(self.scope["productionTarget"])
        self.assertFalse(self.scope["productionReady"])
        self.assertEqual(self.scope["releaseProfile"], "native-single-host-production")

    def test_scope_cannot_claim_readiness(self):
        changed = copy.deepcopy(self.scope)
        changed["productionReady"] = True
        self.assertIn("SCOPE_MUST_REMAIN_UNQUALIFIED", SCOPE.validate(changed))

    def test_scope_keeps_kubernetes_experimental(self):
        changed = copy.deepcopy(self.scope)
        changed["paths"]["kubernetes"]["productionIncluded"] = True
        self.assertIn("KUBERNETES_MUST_REMAIN_EXPERIMENTAL", SCOPE.validate(changed))

    def test_scope_requires_all_single_host_gates(self):
        changed = copy.deepcopy(self.scope)
        changed["paths"]["native"]["qualificationGates"].pop()
        self.assertIn("NATIVE_GATE_INVENTORY_INVALID", SCOPE.validate(changed))

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            SCOPE.parse_json('{"productionReady":false,"productionReady":true}')


if __name__ == "__main__":
    unittest.main()
