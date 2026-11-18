import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("production_scope", ROOT / "scripts/check-production-scope.py")
SCOPE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCOPE)


class ProductionScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = json.loads((ROOT / "release/production-scope.json").read_text())
        cls.qualification = json.loads((ROOT / "release/qualification.json").read_text())
        cls.kubernetes = json.loads((ROOT / "release/kubernetes-readiness.json").read_text())

    def validate(self, scope):
        return SCOPE.validate(scope, self.qualification, self.kubernetes)

    def test_repository_scope_is_complete_but_not_qualified(self):
        self.assertEqual(self.validate(self.scope), [])
        self.assertFalse(self.scope["productionReady"])
        self.assertEqual(self.scope["status"], "candidate-not-qualified")

    def test_missing_or_overlapping_masterplan_item_is_rejected(self):
        changed = copy.deepcopy(self.scope)
        changed["fullMasterplan"]["inCandidateScope"].remove("K20-001")
        self.assertIn("MASTERPLAN_CLASSIFICATION_INCOMPLETE", self.validate(changed))
        changed["fullMasterplan"]["deferred"]["K20-002"] = "duplicate"
        self.assertIn("MASTERPLAN_CLASSIFICATION_OVERLAP", self.validate(changed))

    def test_native_and_kubernetes_boundaries_cannot_be_mixed(self):
        changed = copy.deepcopy(self.scope)
        changed["paths"]["kubernetes"]["stateSchema"] = 2
        self.assertIn("KUBERNETES_BOUNDARY_INVALID", self.validate(changed))
        changed = copy.deepcopy(self.scope)
        changed["paths"]["native"]["engine"] = "k0s-kubernetes"
        self.assertIn("NATIVE_BOUNDARY_INVALID", self.validate(changed))
        changed = copy.deepcopy(self.scope)
        changed["paths"]["native"]["upgradePath"] = "any-version"
        self.assertIn("NATIVE_BOUNDARY_INVALID", self.validate(changed))

    def test_gate_and_dependency_drift_is_rejected(self):
        changed = copy.deepcopy(self.scope)
        changed["paths"]["native"]["qualificationGates"].pop()
        self.assertIn("NATIVE_GATE_INVENTORY_MISMATCH", self.validate(changed))
        changed = copy.deepcopy(self.scope)
        changed["paths"]["kubernetes"]["requiredPinnings"].pop("storageProfile")
        self.assertIn("PIN_INVENTORY_INVALID", self.validate(changed))
        changed = copy.deepcopy(self.scope)
        changed["paths"]["kubernetes"]["requiredPinnings"]["k0s"]["targetMatrix"] = "latest"
        self.assertIn("CORE_PIN_REFERENCE_INVALID:k0s", self.validate(changed))
        changed = copy.deepcopy(self.scope)
        changed["paths"]["kubernetes"]["requiredPinnings"]["storageProfile"]["status"] = "pinned"
        self.assertIn("STORAGE_SELECTION_REFERENCE_INVALID", self.validate(changed))
        changed = copy.deepcopy(self.scope)
        changed["crossPathReleaseGates"].append(changed["crossPathReleaseGates"][0])
        self.assertIn("CROSS_PATH_GATE_INVENTORY_MISMATCH", self.validate(changed))

    def test_scope_cannot_claim_production_readiness(self):
        changed = copy.deepcopy(self.scope)
        changed["productionReady"] = True
        self.assertIn("SCOPE_MUST_REMAIN_UNQUALIFIED", self.validate(changed))

    def test_ambiguous_json_and_upstream_readiness_are_rejected(self):
        with self.assertRaises(ValueError):
            SCOPE.parse_json('{"productionReady":false,"productionReady":true}')
        qualification = copy.deepcopy(self.qualification)
        qualification["productionReady"] = True
        self.assertIn(
            "UPSTREAM_READINESS_CONTRACT_INVALID",
            SCOPE.validate(self.scope, qualification, self.kubernetes),
        )


if __name__ == "__main__":
    unittest.main()
