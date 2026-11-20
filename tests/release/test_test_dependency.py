import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "test_dependency", ROOT / "scripts/check-test-dependency.py"
)
DEPENDENCY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPENDENCY)


class TestDependencyMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = DEPENDENCY.parse_json((ROOT / "tests/runtime/etcd-tool.json").read_text())

    def test_repository_metadata_is_exact_and_bounded(self):
        self.assertEqual(DEPENDENCY.validate(self.metadata), [])

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            DEPENDENCY.parse_json('{"sha256":"one","sha256":"two"}')

    def test_non_object_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            DEPENDENCY.parse_json("[]")

    def test_version_architecture_and_digest_drift_are_rejected(self):
        changed = copy.deepcopy(self.metadata)
        changed["version"] = "v3.7.3"
        changed["architecture"] = "linux-arm64"
        changed["sha256"] = "0" * 64
        problems = DEPENDENCY.validate(changed)
        self.assertIn("VERSION_DRIFT", problems)
        self.assertIn("ARCHITECTURE_DRIFT", problems)
        self.assertIn("SHA256_DRIFT", problems)

    def test_metadata_file_cli_emits_only_url_and_digest(self):
        result = __import__("subprocess").run(
            ["python3", str(ROOT / "scripts/check-test-dependency.py"), str(ROOT / "tests/runtime/etcd-tool.json")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.splitlines(), [self.metadata["url"], self.metadata["sha256"]])

    def test_duplicate_file_fails_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "metadata.json"
            path.write_text('{"version":"v3.7.2","version":"v3.7.3"}')
            result = __import__("subprocess").run(
                ["python3", str(ROOT / "scripts/check-test-dependency.py"), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate JSON key", result.stderr)


if __name__ == "__main__":
    unittest.main()
