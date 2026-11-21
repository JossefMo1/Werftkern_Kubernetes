import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "test_release_contract", ROOT / "scripts/check-test-release-contract.py"
)
CONTRACT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CONTRACT)


class TestReleaseContract(unittest.TestCase):
    def test_repository_contract_is_valid(self):
        self.assertEqual(CONTRACT.validate(ROOT), [])

    def make_fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for relative in CONTRACT.DOCUMENTS + (CONTRACT.WORKFLOW, CONTRACT.NATIVE_WORKFLOW, CONTRACT.KUBERNETES_WORKFLOW, CONTRACT.TRACKER):
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        self.addCleanup(temp.cleanup)
        return root

    def test_legacy_tilde_names_are_rejected(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        content = path.read_text().replace(
            "werftkern_0.2.0.dev4_amd64.deb",
            "werftkern_0.2.0~dev4_amd64.deb",
        )
        path.write_text(content)
        problems = CONTRACT.validate(root)
        self.assertIn(
            "LEGACY_ASSET_NAME:docs/TEST-RELEASE-DE.md:werftkern_0.2.0~dev4_amd64.deb",
            problems,
        )

    def test_checksum_command_must_hash_release_basenames(self):
        root = self.make_fixture()
        path = root / CONTRACT.WORKFLOW
        content = path.read_text().replace(
            "sha256sum *.deb *.tar.gz release-manifest.json > SHA256SUMS",
            "sha256sum release-assets/*.deb *.tar.gz release-manifest.json > SHA256SUMS",
        )
        path.write_text(content)
        self.assertIn("CHECKSUMS_MUST_USE_BASENAMES", CONTRACT.validate(root))

    def test_download_instructions_require_manifest(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        content = path.read_text().replace(
            '  "${BASE}/release-manifest.json" \\\n',
            "",
        )
        path.write_text(content)
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_native_instructions_require_auto_discovery(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        path.write_text(path.read_text().replace("--auto-discover", "--inventory"))
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_native_instructions_require_installed_cli_check(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        path.write_text(path.read_text().replace("test -x /usr/bin/werft-ops || {", "command -v werft-ops"))
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_kubernetes_instructions_require_installed_cli_check(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        path.write_text(path.read_text().replace("command -v werft-kube", "command -v missing-cli"))
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_kubernetes_workflow_requires_apt_install_smoke(self):
        root = self.make_fixture()
        path = root / CONTRACT.KUBERNETES_WORKFLOW
        content = path.read_text().replace(
            "test \"$(command -v werft-kube)\" = \"/usr/bin/werft-kube\"",
            "test \"$(command -v werft-kube-missing)\" = \"/usr/bin/werft-kube\"",
        )
        path.write_text(content)
        self.assertIn(
            "KUBERNETES_WORKFLOW_CONTRACT_MISSING:test \"$(command -v werft-kube)\" = \"/usr/bin/werft-kube\"",
            CONTRACT.validate(root),
        )

    def test_native_instructions_require_uninstall_check(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        path.write_text(
            path.read_text().replace(
                "sudo apt-get remove -y werftkern",
                "sudo apt-get purge -y werftkern",
            )
        )
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_native_instructions_require_hash_reset(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        path.write_text(path.read_text().replace("hash -r", "hash -s"))
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_native_workflow_requires_package_install_path(self):
        root = self.make_fixture()
        path = root / CONTRACT.NATIVE_WORKFLOW
        path.write_text(
            path.read_text().replace(
                'package="$GITHUB_WORKSPACE/dist/werftkern_0.2.0~dev4_amd64.deb"',
                'package="$GITHUB_WORKSPACE/dist/missing.deb"',
            )
        )
        self.assertIn(
            'NATIVE_WORKFLOW_CONTRACT_MISSING:package="$GITHUB_WORKSPACE/dist/werftkern_0.2.0~dev4_amd64.deb"',
            CONTRACT.validate(root),
        )

    def test_native_workflow_requires_installed_cli_checks(self):
        root = self.make_fixture()
        path = root / CONTRACT.NATIVE_WORKFLOW
        path.write_text(
            path.read_text().replace(
                'test "$(command -v werft-ops)" = "/usr/bin/werft-ops"',
                'test "$(command -v missing-cli)" = "/usr/bin/werft-ops"',
            )
        )
        self.assertIn(
            'NATIVE_WORKFLOW_CONTRACT_MISSING:test "$(command -v werft-ops)" = "/usr/bin/werft-ops"',
            CONTRACT.validate(root),
        )

    def test_native_workflow_requires_uninstall_cleanup(self):
        root = self.make_fixture()
        path = root / CONTRACT.NATIVE_WORKFLOW
        path.write_text(
            path.read_text().replace(
                "sudo apt-get remove -y werftkern >/dev/null",
                "sudo apt-get purge -y werftkern >/dev/null",
            )
        )
        self.assertIn(
            "NATIVE_WORKFLOW_CONTRACT_MISSING:sudo apt-get remove -y werftkern >/dev/null",
            CONTRACT.validate(root),
        )

    def test_native_workflow_requires_hash_reset(self):
        root = self.make_fixture()
        path = root / CONTRACT.NATIVE_WORKFLOW
        path.write_text(path.read_text().replace("hash -r", "hash -s"))
        self.assertIn(
            "NATIVE_WORKFLOW_CONTRACT_MISSING:hash -r",
            CONTRACT.validate(root),
        )

    def test_kubernetes_instructions_require_uninstall_check(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        path.write_text(
            path.read_text().replace(
                "sudo apt-get remove -y werftkern-kubernetes",
                "sudo apt-get purge -y werftkern-kubernetes",
            )
        )
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_kubernetes_workflow_requires_uninstall_cleanup(self):
        root = self.make_fixture()
        path = root / CONTRACT.KUBERNETES_WORKFLOW
        path.write_text(
            path.read_text().replace(
                "sudo apt-get remove -y werftkern-kubernetes >/dev/null",
                "sudo apt-get purge -y werftkern-kubernetes >/dev/null",
            )
        )
        self.assertIn(
            "KUBERNETES_WORKFLOW_CONTRACT_MISSING:sudo apt-get remove -y werftkern-kubernetes >/dev/null",
            CONTRACT.validate(root),
        )

    def test_kubernetes_instructions_require_hash_reset(self):
        root = self.make_fixture()
        path = root / CONTRACT.DOCUMENTS[0]
        path.write_text(path.read_text().replace("hash -r", "hash -s"))
        self.assertTrue(
            any(problem.startswith("DOCUMENT_INSTRUCTIONS_MISSING:") for problem in CONTRACT.validate(root))
        )

    def test_kubernetes_workflow_requires_hash_reset(self):
        root = self.make_fixture()
        path = root / CONTRACT.KUBERNETES_WORKFLOW
        path.write_text(path.read_text().replace("hash -r", "hash -s"))
        self.assertIn(
            "KUBERNETES_WORKFLOW_CONTRACT_MISSING:hash -r",
            CONTRACT.validate(root),
        )

    def test_release_notes_must_be_normalized_to_actual_tag(self):
        root = self.make_fixture()
        path = root / CONTRACT.WORKFLOW
        content = path.read_text().replace(
            'release_notes="$PWD/.test-release-notes.md"',
            'release_notes="$PWD/notes.md"',
        )
        path.write_text(content)
        self.assertIn(
            'WORKFLOW_CONTRACT_MISSING:release_notes="$PWD/.test-release-notes.md"',
            CONTRACT.validate(root),
        )

    def test_publish_glob_must_not_use_dist_tarballs(self):
        root = self.make_fixture()
        path = root / CONTRACT.WORKFLOW
        path.write_text(path.read_text().replace(
            "release-assets/*.deb release-assets/*.tar.gz",
            "dist/*.deb dist/*.tar.gz",
        ))
        self.assertIn("PUBLISH_MUST_NOT_USE_DIST_TARBALL_GLOB", CONTRACT.validate(root))

    def test_runbook_tag_must_match_tracker_candidate(self):
        root = self.make_fixture()
        tracker = root / CONTRACT.TRACKER
        content = tracker.read_text().replace(
            '"tag": "v0.2.0-dev.4-test.17"',
            '"tag": "v0.2.0-dev.4-test.14"',
        )
        tracker.write_text(content)
        self.assertIn(
            "DOCUMENT_TAG_MISMATCH:docs/TEST-RELEASE-DE.md:v0.2.0-dev.4-test.17!=v0.2.0-dev.4-test.14",
            CONTRACT.validate(root),
        )

    def test_runbook_tag_parser_is_line_bounded(self):
        match = CONTRACT.RUNBOOK_TAG.search(
            "TAG=v0.2.0-dev.4-test.15\nNEXT=value"
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "v0.2.0-dev.4-test.15")


if __name__ == "__main__":
    unittest.main()
