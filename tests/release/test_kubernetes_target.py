import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("kubernetes_target", ROOT / "scripts/check-kubernetes-target.py")
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)


class KubernetesTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = TARGET.parse_json((ROOT / "release/kubernetes-target-matrix.json").read_text())

    def test_repository_target_is_valid_but_unqualified(self):
        self.assertEqual(TARGET.validate(self.matrix), [])
        self.assertFalse(self.matrix["productionReady"])
        self.assertFalse(self.matrix["compatibility"]["realClusterPassed"])

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            TARGET.parse_json('{"productionReady":false,"productionReady":true}')

    def test_versions_must_match_k0s_kubernetes_and_kubectl(self):
        changed = copy.deepcopy(self.matrix)
        changed["core"]["kubectl"]["version"] = "v1.36.0"
        self.assertIn("KUBECTL_VERSION_MISMATCH", TARGET.validate(changed))
        changed = copy.deepcopy(self.matrix)
        changed["core"]["k0s"]["kubernetesVersion"] = "v1.36.0"
        self.assertIn("K0S_KUBERNETES_VERSION_MISMATCH", TARGET.validate(changed))

    def test_digest_and_provenance_drift_are_rejected(self):
        changed = copy.deepcopy(self.matrix)
        changed["core"]["k0sctl"]["artifact"]["sha256"] = "not-a-digest"
        self.assertIn("ARTIFACT_DIGEST_INVALID:k0sproject/k0sctl", TARGET.validate(changed))
        changed = copy.deepcopy(self.matrix)
        changed["core"]["k0s"]["releaseUrl"] = "https://example.invalid/release"
        self.assertIn("RELEASE_PROVENANCE_INVALID:k0sproject/k0s", TARGET.validate(changed))

    def test_execution_and_signature_claims_cannot_be_invented(self):
        changed = copy.deepcopy(self.matrix)
        changed["core"]["k0s"]["signature"]["verified"] = True
        self.assertIn("UNVERIFIED_SIGNATURE_MUST_REMAIN_FALSE", TARGET.validate(changed))
        changed = copy.deepcopy(self.matrix)
        changed["compatibility"]["realClusterPassed"] = True
        self.assertIn("COMPATIBILITY_CLAIM_INVALID", TARGET.validate(changed))

    def test_unresolved_storage_and_addons_remain_explicit(self):
        changed = copy.deepcopy(self.matrix)
        changed["unresolved"].pop("storageQualification")
        self.assertIn("UNRESOLVED_INVENTORY_INVALID", TARGET.validate(changed))

    def test_storage_image_digests_are_pinned_without_live_qualification(self):
        qualification = self.matrix["storageProfile"]["qualification"]
        self.assertTrue(qualification["imageDigestsPinned"])
        self.assertTrue(qualification["chartRendered"])
        self.assertTrue(qualification["staticSecurityAuditRecorded"])
        self.assertFalse(qualification["staticSecurityHardeningPassed"])
        self.assertFalse(qualification["realProvisionAttachMount"])

    def test_storage_selection_and_unexecuted_gates_are_fail_closed(self):
        changed = copy.deepcopy(self.matrix)
        changed["storageProfile"]["storageClass"]["reclaimPolicy"] = "Delete"
        self.assertIn("STORAGE_CLASS_BOUNDARY_INVALID", TARGET.validate(changed))
        changed = copy.deepcopy(self.matrix)
        changed["storageProfile"]["qualification"]["realProvisionAttachMount"] = True
        self.assertIn("STORAGE_PROFILE_INVALID", TARGET.validate(changed))
        changed = copy.deepcopy(self.matrix)
        changed["storageProfile"]["imageLock"] = "release/latest.json"
        self.assertIn("STORAGE_PROFILE_INVALID", TARGET.validate(changed))
        changed = copy.deepcopy(self.matrix)
        changed["storageProfile"]["securityPolicy"] = "release/approved.json"
        self.assertIn("STORAGE_PROFILE_INVALID", TARGET.validate(changed))
        changed = copy.deepcopy(self.matrix)
        changed["storageProfile"]["qualification"]["staticSecurityHardeningPassed"] = True
        self.assertIn("STORAGE_PROFILE_INVALID", TARGET.validate(changed))

    def test_public_asset_example_matches_selected_storage_chart(self):
        assets = TARGET.parse_json((ROOT / "examples/kubernetes/assets.example.json").read_text())
        chart = self.matrix["storageProfile"]["driver"]["chart"]
        self.assertEqual(assets["charts"]["hcloud-csi"], {
            "path": "/opt/werftkern/reviewed/charts/hcloud-csi.tgz",
            "sha256": chart["sha256"],
            "version": "2.24.2",
        })
        values = (ROOT / "examples/kubernetes/hcloud-csi-values.example.yaml").read_text()
        self.assertIn("kubeletDir: /var/lib/k0s/kubelet", values)
        self.assertIn("name: werftkern-hcloud-retain", values)
        self.assertIn("defaultStorageClass: false", values)
        self.assertIn("reclaimPolicy: Retain", values)
        image_lock = TARGET.parse_json((ROOT / "release/hcloud-csi-image-lock.json").read_text())
        for image in image_lock["images"].values():
            self.assertEqual(
                values.count(f"{image['repository']}@{image['digest']}"),
                len(image["consumers"]),
            )
        self.assertEqual(values.count('tag: ""'), 8)
        self.assertNotIn("token:", values)

    def test_public_asset_example_matches_core_target(self):
        assets = TARGET.parse_json((ROOT / "examples/kubernetes/assets.example.json").read_text())
        k0s = self.matrix["core"]["k0s"]
        ctl = self.matrix["core"]["k0sctl"]
        kubectl = self.matrix["core"]["kubectl"]
        self.assertEqual(assets["k0s"], {
            k0s["version"]: {
                "path": "/opt/werftkern/reviewed/k0s",
                "sha256": k0s["artifact"]["sha256"],
                "version": k0s["version"],
            }
        })
        self.assertEqual(assets["tools"]["k0sctl"]["version"], ctl["version"])
        self.assertEqual(assets["tools"]["k0sctl"]["sha256"], ctl["artifact"]["sha256"])
        self.assertEqual(assets["tools"]["kubectl"]["version"], kubectl["version"])
        self.assertEqual(assets["tools"]["kubectl"]["sha256"], kubectl["artifact"]["sha256"])
        self.assertIn("conformance:" + kubectl["version"], assets["images"])


if __name__ == "__main__":
    unittest.main()
