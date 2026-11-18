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

    def test_repository_inventory_is_complete_but_unresolved(self):
        self.assertEqual(LOCK.validate_lock(self.lock), [])
        self.assertEqual(set(self.lock["images"]), set(LOCK.EXPECTED))
        self.assertTrue(all(item["digest"] is None for item in self.lock["images"].values()))
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

    def test_render_is_blocked_while_digests_are_unresolved(self):
        rendered = "image: registry.k8s.io/sig-storage/csi-attacher:v4.13.0\n"
        problems = LOCK.validate_render(rendered, self.lock)
        self.assertIn("UNRESOLVED_IMAGE_DIGEST:csi-attacher", problems)
        self.assertIn("TAG_OR_INVALID_DIGEST_IN_RENDER:registry.k8s.io/sig-storage/csi-attacher:v4.13.0", problems)

    def test_only_exact_digest_locked_image_set_is_accepted(self):
        changed = copy.deepcopy(self.lock)
        changed["status"] = "digests-pinned-not-render-qualified"
        lines = []
        for index, item in enumerate(changed["images"].values(), start=1):
            item["digest"] = "sha256:" + f"{index:064x}"
            lines.extend(
                [f"image: {item['repository']}@{item['digest']}"] * len(item["consumers"])
            )
        self.assertEqual(LOCK.validate_lock(changed), [])
        self.assertEqual(LOCK.validate_render("\n".join(lines), changed), [])
        lines.append("image: example.invalid/unreviewed@sha256:" + "f" * 64)
        self.assertIn("RENDER_IMAGE_SET_MISMATCH", LOCK.validate_render("\n".join(lines), changed))

    def test_render_without_images_is_rejected(self):
        self.assertEqual(LOCK.validate_render("kind: ConfigMap\n", self.lock), ["RENDER_CONTAINS_NO_IMAGES"])


if __name__ == "__main__":
    unittest.main()
