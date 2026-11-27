import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).parents[2] / "scripts" / "generate-native-sbom.py"
SPEC = importlib.util.spec_from_file_location("generate_native_sbom", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NativeSbomTests(unittest.TestCase):
    def test_sha256_file_is_stable_and_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            package = pathlib.Path(temp) / "package.deb"
            package.write_bytes(b"werftkern-package-bytes")
            self.assertEqual(
                MODULE.sha256_file(package),
                "1aee6c005e3c8c1b1e7e9955f4c58c984d26af5a94e84f7ca3d2d5a5f7adfcce",
            )

    def test_root_package_contains_exact_spdx_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            package = root / "package.deb"
            package.write_bytes(b"exact-package")
            modules = root / "modules.jsonl"
            modules.write_text('{"Path":"example/module","Version":"v1.2.3"}\n', encoding="utf-8")
            output = root / "sbom.json"
            fields = {
                "Package": "werftkern",
                "Version": "0.2.0~dev4",
                "Architecture": "amd64",
                "Depends": "python3",
            }
            argv = [
                "generate-native-sbom.py",
                "--package", str(package),
                "--modules", str(modules),
                "--source-commit", "a" * 40,
                "--source-date-epoch", "1700000000",
                "--output", str(output),
            ]
            with mock.patch.object(MODULE, "package_field", side_effect=fields.__getitem__), mock.patch.object(
                sys, "argv", argv
            ):
                self.assertEqual(MODULE.main(), 0)
            document = json.loads(output.read_text(encoding="utf-8"))
            root_package = next(item for item in document["packages"] if item["name"] == "werftkern")
            self.assertEqual(
                root_package["checksums"],
                [{"algorithm": "SHA256", "checksumValue": "48f0f5f2f5cdd8de0f0d9fdbf2ac6d7a28d2f6b573bb3b1a2f4d724b4a4a7d32"}],
            )
            self.assertIn("packageSha256=48f0f5f2f5cdd8de0f0d9fdbf2ac6d7a28d2f6b573bb3b1a2f4d724b4a4a7d32", root_package["packageComment"])


if __name__ == "__main__":
    unittest.main()
