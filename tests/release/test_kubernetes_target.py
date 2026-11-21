import contextlib
import copy
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("kubernetes_target", ROOT / "scripts/check-kubernetes-target.py")
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)

sys.path.insert(0, str(ROOT / "ops"))
from werftops import kube_main as KUBE_MAIN


class KubernetesTargetTests(unittest.TestCase):
    def _materialize_wrapper(self, root):
        wrapper = root / "usr/bin/werft-kube"
        wrapper.parent.mkdir(parents=True)
        content = (ROOT / "scripts/werft-kube").read_text().replace(
            "installed=/usr/lib/werftkern-kubernetes/ops",
            "installed=/werftkern-test-no-installed-modules",
        )
        wrapper.write_text(content)
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        return wrapper

    def _wrapper_env(self):
        return {
            "PATH": os.environ["PATH"],
            "PYTHONPATH": "",
            "PYTHONNOUSERSITE": "1",
        }

    def test_kubernetes_wrapper_runs_from_extracted_package_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            wrapper = self._materialize_wrapper(root)
            package = root / "usr/lib/werftkern-kubernetes/ops/werftops"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("")
            (package / "kube_main.py").write_text(
                "import sys\n"
                "print('wrapper-ok:' + ' '.join(sys.argv[1:]))\n"
            )
            result = subprocess.run(
                [str(wrapper), "version"],
                cwd=root,
                env=self._wrapper_env(),
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "wrapper-ok:version")

    def test_kubernetes_wrapper_fails_closed_when_modules_are_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            wrapper = self._materialize_wrapper(root)
            result = subprocess.run(
                [str(wrapper), "version"],
                cwd=root,
                env=self._wrapper_env(),
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 78)
        self.assertIn("werft-kube: Python modules not found", result.stderr)

    def test_kubernetes_wrapper_fails_closed_when_entrypoint_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            wrapper = self._materialize_wrapper(root)
            package = root / "usr/lib/werftkern-kubernetes/ops/werftops"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("")
            result = subprocess.run(
                [str(wrapper), "version"],
                cwd=root,
                env=self._wrapper_env(),
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 78)
        self.assertIn("werft-kube: Python modules not found", result.stderr)

    def test_recovery_services_keep_root_boundary_and_systemd_sandbox(self):
        required = (
            "User=root",
            "UMask=0077",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ProtectHome=true",
            "PrivateTmp=true",
            "PrivateDevices=true",
            "ProtectKernelTunables=true",
            "ProtectKernelModules=true",
            "ProtectControlGroups=true",
            "RestrictSUIDSGID=true",
            "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6",
            "CapabilityBoundingSet=",
            "ReadWritePaths=/var/lib/werftkern/kubernetes/%i",
        )
        for filename in (
            "werftkern-kube-repair@.service",
            "werftkern-kube-recovery@.service",
        ):
            content = (ROOT / "packaging/kubernetes" / filename).read_text()
            for directive in required:
                self.assertIn(directive, content, f"{filename} missing {directive}")
            self.assertIn("/usr/bin/werft-kube", content)
            self.assertIn("--assets /etc/werftkern/kubernetes/%i/assets.json", content)
            self.assertIn("--token-file /etc/werftkern/kubernetes/%i/provider-token", content)
            self.assertNotIn("ExecStart=/bin/sh", content)
            self.assertNotIn("ExecStart=/bin/bash", content)

    def test_plan_rejects_non_object_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            plan = pathlib.Path(temp) / "plan.json"
            plan.write_text("[1, 2, 3]")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = KUBE_MAIN.main(["plan", str(plan)])
        self.assertEqual(result, 2)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"productionReady": False, "reason": "KUBE_PLAN_OBJECT_REQUIRED", "state": "BLOCKED"},
        )
        self.assertNotIn("Traceback", stderr.getvalue())

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
        self.assertTrue(qualification["imageRuntimeConfigAudited"])
        self.assertFalse(qualification["podLevelRunAsNonRootSafe"])
        self.assertTrue(qualification["chartRendered"])
        self.assertTrue(qualification["staticSecurityAuditRecorded"])
        self.assertTrue(qualification["nodeServiceAccountTokenDisabled"])
        self.assertTrue(qualification["podSeccompRuntimeDefault"])
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
        changed["storageProfile"]["runtimeProfile"] = "release/approved.json"
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
        self.assertIn("serviceAccountName: werftkern-hcloud-csi-node", values)
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
        account = (ROOT / "examples/kubernetes/hcloud-csi-node-serviceaccount.yaml").read_text()
        self.assertIn("name: werftkern-hcloud-csi-node", account)
        self.assertIn("automountServiceAccountToken: false", account)

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
