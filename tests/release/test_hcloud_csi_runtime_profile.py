import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "hcloud_runtime", ROOT / "scripts/check-hcloud-csi-runtime-profile.py"
)
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class HcloudCsiRuntimeProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = RUNTIME.parse_json((ROOT / "release/hcloud-csi-runtime-profile.json").read_text())
        cls.lock = RUNTIME.parse_json((ROOT / "release/hcloud-csi-image-lock.json").read_text())

    def test_repository_profile_is_valid_and_fail_closed(self):
        self.assertEqual(RUNTIME.validate(self.profile, self.lock), [])
        self.assertFalse(self.profile["productionReady"])
        self.assertFalse(self.profile["runAsNonRootSafeAtPodLevel"])
        self.assertTrue(all(i["configuredUser"] in ("", "0", "root") for i in self.profile["images"].values()))

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            RUNTIME.parse_json('{"productionReady":false,"productionReady":true}')

    def test_image_lock_drift_is_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["images"]["csi-attacher"]["indexDigest"] = "sha256:" + "a" * 64
        self.assertIn("INDEX_DIGEST_MISMATCH:csi-attacher", RUNTIME.validate(changed, self.lock))

    def test_digest_and_entrypoint_drift_are_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["images"]["csi-resizer"]["configDigest"] = "not-a-digest"
        self.assertIn("CONFIG_DIGEST_INVALID:csi-resizer", RUNTIME.validate(changed, self.lock))
        changed = copy.deepcopy(self.profile)
        changed["images"]["liveness-probe"]["entrypoint"] = []
        self.assertIn("ENTRYPOINT_INVALID:liveness-probe", RUNTIME.validate(changed, self.lock))

    def test_nonroot_and_readiness_claims_are_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["runAsNonRootSafeAtPodLevel"] = True
        self.assertIn("RUNTIME_BOUNDARY_INVALID", RUNTIME.validate(changed, self.lock))
        changed = copy.deepcopy(self.profile)
        changed["images"]["csi-provisioner"]["configuredUser"] = "65532"
        self.assertIn("UNPROVEN_NONROOT_USER:csi-provisioner", RUNTIME.validate(changed, self.lock))


if __name__ == "__main__":
    unittest.main()
