import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "hcloud_csi_image_lock", ROOT / "scripts/check-hcloud-csi-image-lock.py"
)
LOCK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOCK)


class HcloudCsiImageLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = LOCK.parse_json((ROOT / "release/hcloud-csi-image-lock.json").read_text())

    def test_repository_inventory_is_complete_and_digest_pinned(self):
        self.assertEqual(LOCK.validate_lock(self.lock), [])
        self.assertEqual(set(self.lock["images"]), set(LOCK.EXPECTED))
        self.assertTrue(all(item["digest"].startswith("sha256:") for item in self.lock["images"].values()))
        self.assertFalse(self.lock["productionReady"])

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            LOCK.parse_json('{"status":"one","status":"two"}')

    def test_source_and_image_drift_are_rejected(self):
        changed = copy.deepcopy(self.lock)
        changed["sourceValues"]["gitBlobSha"] = "mutable"
        self.assertIn("SOURCE_VALUES_PROVENANCE_INVALID", LOCK.validate_lock(changed))
        changed = copy.deepcopy(self.lock)
        changed["images"]["csi-attacher"]["tag"] = "latest"
        self.assertIn("IMAGE_SOURCE_DRIFT:csi-attacher", LOCK.validate_lock(changed))
        self.assertIn("MUTABLE_IMAGE_TAG_FORBIDDEN:csi-attacher", LOCK.validate_lock(changed))

    def test_tag_only_render_is_blocked_after_digests_are_pinned(self):
        rendered = "image: registry.k8s.io/sig-storage/csi-attacher:v4.13.0\n"
        problems = LOCK.validate_render(rendered, self.lock)
        self.assertIn("TAG_OR_INVALID_DIGEST_IN_RENDER:registry.k8s.io/sig-storage/csi-attacher:v4.13.0", problems)

    def test_only_exact_digest_locked_image_set_is_accepted(self):
        rendered = (ROOT / self.lock["render"]["manifestPath"]).read_text()
        self.assertEqual(LOCK.validate_render(rendered, self.lock), [])
        rendered += "image: example.invalid/unreviewed@sha256:" + "f" * 64 + "\n"
        self.assertIn("RENDER_IMAGE_SET_MISMATCH", LOCK.validate_render(rendered, self.lock))

    def test_committed_render_hash_and_conservative_markers_are_bound(self):
        rendered = (ROOT / self.lock["render"]["manifestPath"]).read_text()
        self.assertEqual(
            LOCK.hashlib.sha256(rendered.encode()).hexdigest(),
            self.lock["render"]["manifestSha256"],
        )
        self.assertNotIn("kind: Secret\n", rendered)
        node_account = ROOT / self.lock["render"]["nodeServiceAccount"]["path"]
        self.assertEqual(
            LOCK.hashlib.sha256(node_account.read_bytes()).hexdigest(),
            self.lock["render"]["nodeServiceAccount"]["sha256"],
        )
        changed = copy.deepcopy(self.lock)
        changed["render"]["manifestSha256"] = "0" * 64
        self.assertIn("RENDER_STATE_INVALID", LOCK.validate_lock(changed))

    def test_render_rejects_secret_and_weakened_storage_policy(self):
        rendered = (ROOT / self.lock["render"]["manifestPath"]).read_text()
        weakened = rendered.replace('reclaimPolicy: "Retain"', 'reclaimPolicy: "Delete"')
        weakened_lock = copy.deepcopy(self.lock)
        weakened_lock["render"]["manifestSha256"] = LOCK.hashlib.sha256(weakened.encode()).hexdigest()
        self.assertIn(
            'RENDER_REQUIRED_MARKER_MISSING:reclaimPolicy: "Retain"',
            LOCK.validate_render(weakened, weakened_lock),
        )
        with_secret = rendered + "---\napiVersion: v1\nkind: Secret\nmetadata:\n  name: forbidden\n"
        secret_lock = copy.deepcopy(self.lock)
        secret_lock["render"]["manifestSha256"] = LOCK.hashlib.sha256(with_secret.encode()).hexdigest()
        secret_lock["render"]["documentCount"] += 1
        self.assertIn("RENDER_MUST_NOT_CREATE_SECRET", LOCK.validate_render(with_secret, secret_lock))

    def test_static_digest_and_registry_evidence_drift_are_rejected(self):
        changed = copy.deepcopy(self.lock)
        changed["images"]["csi-attacher"]["digest"] = "sha256:" + "0" * 64
        self.assertIn("IMAGE_DIGEST_DRIFT:csi-attacher", LOCK.validate_lock(changed))
        changed = copy.deepcopy(self.lock)
        changed["images"]["csi-attacher"]["registryEvidence"]["dockerContentDigestMatchedBody"] = False
        self.assertIn("REGISTRY_EVIDENCE_INVALID:csi-attacher", LOCK.validate_lock(changed))

    def test_online_verifier_detects_tag_drift_and_header_mismatch(self):
        expected = self.lock["images"]["csi-attacher"]
        def fetcher(repository, tag):
            self.assertEqual(repository, expected["repository"])
            self.assertEqual(tag, expected["tag"])
            return {
                "digest": "sha256:" + "0" * 64,
                "computedDigest": "sha256:" + "1" * 64,
                "mediaType": expected["registryEvidence"]["mediaType"],
                "manifestCount": expected["registryEvidence"]["manifestCount"],
                "linuxAmd64Present": True,
            }
        one = copy.deepcopy(self.lock)
        one["images"] = {"csi-attacher": expected}
        problems = LOCK.verify_registry(one, fetcher)
        self.assertIn("REGISTRY_HEADER_BODY_MISMATCH:csi-attacher", problems)
        self.assertIn("REGISTRY_TAG_DIGEST_DRIFT:csi-attacher", problems)

    def test_render_without_images_is_rejected(self):
        self.assertEqual(LOCK.validate_render("kind: ConfigMap\n", self.lock), ["RENDER_CONTAINS_NO_IMAGES"])


if __name__ == "__main__":
    unittest.main()
