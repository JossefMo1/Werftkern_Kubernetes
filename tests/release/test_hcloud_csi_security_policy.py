import copy
import importlib.util
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_hcloud_csi_security_policy",
    ROOT / "scripts/check-hcloud-csi-security-policy.py",
)
POLICY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(POLICY)


class HcloudCsiSecurityPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = POLICY.parse_json(
            (ROOT / "release/hcloud-csi-security-policy.json").read_text()
        )
        cls.raw = (ROOT / cls.policy["manifest"]["path"]).read_text()

    def render(self, mutation):
        documents = list(yaml.safe_load_all(self.raw))
        mutation(documents)
        return "\n---\n".join(yaml.safe_dump(item, sort_keys=False).rstrip() for item in documents) + "\n"

    def test_exact_manifest_has_a_valid_blocked_audit(self):
        self.assertEqual(POLICY.validate_policy(self.policy), [])
        self.assertEqual(POLICY.validate_manifest(self.policy, self.raw), [])
        self.assertFalse(self.policy["hardeningPassed"])
        self.assertFalse(self.policy["productionReady"])
        self.assertEqual(self.policy["observedHardeningGaps"], POLICY.EXPECTED_GAPS)

    def test_duplicate_policy_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            POLICY.parse_json('{"status":"one","status":"two"}')

    def test_policy_cannot_relax_rbac_or_claim_readiness(self):
        changed = copy.deepcopy(self.policy)
        changed["productionReady"] = True
        changed["hardeningPassed"] = True
        changed["rbac"]["wildcardsAllowed"] = True
        problems = POLICY.validate_policy(changed)
        self.assertIn("POLICY_CANNOT_CLAIM_READINESS", problems)
        self.assertIn("POLICY_RBAC_BOUNDARY_INVALID", problems)

    def test_wildcard_and_secret_rbac_are_rejected(self):
        def mutate(documents):
            role = next(item for item in documents if item["kind"] == "ClusterRole")
            role["rules"][0]["verbs"].append("*")
            role["rules"].append({"apiGroups": [""], "resources": ["secrets"], "verbs": ["get"]})

        problems = POLICY.validate_manifest(self.policy, self.render(mutate))
        self.assertIn("MANIFEST_SHA256_MISMATCH", problems)
        self.assertIn("RBAC_RULESET_DRIFT", problems)
        self.assertIn("RBAC_WILDCARD_FORBIDDEN", problems)
        self.assertIn("RBAC_SECRET_ACCESS_FORBIDDEN", problems)

    def test_host_path_and_privileged_container_drift_are_rejected(self):
        def mutate(documents):
            node = next(item for item in documents if item["kind"] == "DaemonSet")
            spec = node["spec"]["template"]["spec"]
            spec["volumes"][0]["hostPath"]["path"] = "/"
            spec["containers"][0]["securityContext"] = {"privileged": True}

        problems = POLICY.validate_manifest(self.policy, self.render(mutate))
        self.assertIn("NODE_HOST_PATH_BOUNDARY_DRIFT", problems)
        self.assertIn("NODE_PRIVILEGED_BOUNDARY_DRIFT", problems)

    def test_node_token_change_requires_policy_review(self):
        def mutate(documents):
            node = next(item for item in documents if item["kind"] == "DaemonSet")
            node["spec"]["template"]["spec"]["automountServiceAccountToken"] = False

        problems = POLICY.validate_manifest(self.policy, self.render(mutate))
        self.assertIn("NODE_TOKEN_MODE_DRIFT_REQUIRES_REVIEW", problems)
        self.assertIn("OBSERVED_HARDENING_GAPS_DRIFT", problems)

    def test_external_metrics_exposure_is_rejected(self):
        def mutate(documents):
            service = next(item for item in documents if item["kind"] == "Service")
            service["spec"]["type"] = "LoadBalancer"

        self.assertIn(
            "METRICS_SERVICE_EXPOSURE_DRIFT",
            POLICY.validate_manifest(self.policy, self.render(mutate)),
        )


if __name__ == "__main__":
    unittest.main()
