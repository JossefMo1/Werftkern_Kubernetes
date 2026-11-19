import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "harden_hcloud_csi_render",
    ROOT / "scripts/harden-hcloud-csi-render.py",
)
HARDENER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HARDENER)


class HcloudCsiPostRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "release/evidence/hcloud-csi-2.24.2-render.yaml").read_text()

    def current_or_original(self):
        documents = HARDENER.load_documents(self.raw)
        if HARDENER.already_hardened(documents):
            parts = self.raw.split("\n---\n")
            for index, part in enumerate(parts):
                document = yaml.safe_load(part)
                if not isinstance(document, dict):
                    continue
                key = HARDENER.identity(document)
                if key not in HARDENER.EXPECTED_WORKLOADS:
                    continue
                for name, context in HARDENER.EXPECTED_WORKLOADS[key].items():
                    if context is HARDENER.PRIVILEGED_NODE_CONTEXT:
                        parts[index] = parts[index].replace(
                            "          securityContext:\n"
                            "            privileged: true\n"
                            "            runAsUser: 0\n"
                            "            runAsNonRoot: false\n",
                            "          securityContext:\n            privileged: true\n",
                            1,
                        )
                    else:
                        marker = f"        - name: {name}\n"
                        block = HARDENER.insert_context("x\n" + marker, name, context, privileged=False)
                        addition = block.removeprefix("x\n").removeprefix(marker)
                        parts[index] = parts[index].replace(marker + addition, marker, 1)
            return "\n---\n".join(parts)
        return self.raw

    def harden_fixture(self, raw):
        return HARDENER.harden(raw, expected_input_sha256=hashlib.sha256(raw.encode()).hexdigest())

    def test_exact_render_gets_complete_contexts_and_is_idempotent(self):
        original = self.current_or_original()
        hardened = self.harden_fixture(original)
        HARDENER.validate_workloads(HARDENER.load_documents(hardened), hardened=True)
        self.assertEqual(HARDENER.harden(hardened), hardened)

    def test_non_privileged_and_privileged_boundaries_remain_distinct(self):
        hardened = self.harden_fixture(self.current_or_original())
        documents = HARDENER.load_documents(hardened)
        for document in documents:
            key = HARDENER.identity(document)
            if key not in HARDENER.EXPECTED_WORKLOADS:
                continue
            for container in HARDENER.workload_containers(document):
                context = container["securityContext"]
                if context.get("privileged") is True:
                    self.assertEqual(context, HARDENER.PRIVILEGED_NODE_CONTEXT)
                    self.assertNotIn("allowPrivilegeEscalation", context)
                else:
                    self.assertEqual(context, HARDENER.NON_PRIVILEGED_CONTEXT)
                    self.assertFalse(context["allowPrivilegeEscalation"])
                    self.assertEqual(context["capabilities"], {"drop": ["ALL"]})

    def test_changed_input_hash_is_rejected_before_rewrite(self):
        original = self.current_or_original().replace("replicas: 2", "replicas: 3", 1)
        with self.assertRaisesRegex(ValueError, "pre-hardening render SHA-256 drift"):
            HARDENER.harden(original)

    def test_changed_hardened_render_is_not_accepted_as_idempotent(self):
        hardened = self.harden_fixture(self.current_or_original())
        changed = hardened.replace("replicas: 2", "replicas: 3", 1)
        with self.assertRaisesRegex(ValueError, "hardened render SHA-256 drift"):
            HARDENER.harden(changed)

    def test_missing_workload_is_rejected(self):
        original = self.current_or_original().replace(
            "kind: Deployment\nmetadata:\n  name: werftkern-hcloud-csi-controller",
            "kind: Deployment\nmetadata:\n  name: unexpected-controller",
            1,
        )
        with self.assertRaisesRegex(ValueError, "workload identity drift"):
            self.harden_fixture(original)

    def test_extra_or_duplicate_container_is_rejected(self):
        original = self.current_or_original().replace(
            "        - name: csi-attacher\n",
            "        - name: unexpected-sidecar\n          image: example.invalid/test\n"
            "        - name: csi-attacher\n",
            1,
        )
        with self.assertRaisesRegex(ValueError, "container boundary drift"):
            self.harden_fixture(original)

    def test_conflicting_preexisting_context_is_rejected(self):
        original = self.current_or_original().replace(
            "        - name: csi-attacher\n",
            "        - name: csi-attacher\n"
            "          securityContext:\n"
            "            privileged: true\n",
            1,
        )
        with self.assertRaisesRegex(ValueError, "unexpected input securityContext"):
            self.harden_fixture(original)

    def test_privileged_node_driver_cannot_be_silently_changed(self):
        original = self.current_or_original().replace(
            "          securityContext:\n            privileged: true\n",
            "          securityContext:\n            privileged: false\n",
            1,
        )
        with self.assertRaisesRegex(ValueError, "unexpected input securityContext"):
            self.harden_fixture(original)

    def test_duplicate_yaml_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
            HARDENER.load_documents("kind: ConfigMap\nkind: Secret\n")


if __name__ == "__main__":
    unittest.main()
