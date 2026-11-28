import hashlib
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
                hashlib.sha256(b"werftkern-package-bytes").hexdigest(),
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
            with mock.patch.object(MODULE, "package_field", side_effect=lambda _package, field: fields[field]), mock.patch.object(
                sys, "argv", argv
            ):
                self.assertEqual(MODULE.main(), 0)
            document = json.loads(output.read_text(encoding="utf-8"))
            root_package = next(item for item in document["packages"] if item["name"] == "werftkern")
            expected_sha256 = hashlib.sha256(b"exact-package").hexdigest()
            self.assertEqual(
                root_package["checksums"],
                [{"algorithm": "SHA256", "checksumValue": expected_sha256}],
            )
            self.assertIn(f"packageSha256={expected_sha256}", root_package["packageComment"])


    def test_rejects_short_source_commit_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            package = root / "package.deb"
            package.write_bytes(b"package")
            modules = root / "modules.jsonl"
            modules.write_text('{"Path":"example/module","Version":"v1.2.3"}\n', encoding="utf-8")
            output = root / "sbom.json"
            argv = [
                "generate-native-sbom.py",
                "--package", str(package),
                "--modules", str(modules),
                "--source-commit", "abc1234",
                "--source-date-epoch", "1700000000",
                "--output", str(output),
            ]
            with mock.patch.object(sys, "argv", argv), self.assertRaisesRegex(
                SystemExit, "40-character lowercase Git object id"
            ):
                MODULE.main()

    def test_rejects_symlinked_package_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            package = root / "package.deb"
            package.write_bytes(b"package")
            alias = root / "package-alias.deb"
            alias.symlink_to(package)
            modules = root / "modules.jsonl"
            modules.write_text('{"Path":"example/module","Version":"v1.2.3"}\n', encoding="utf-8")
            output = root / "sbom.json"
            argv = [
                "generate-native-sbom.py",
                "--package", str(alias),
                "--modules", str(modules),
                "--source-commit", "a" * 40,
                "--source-date-epoch", "1700000000",
                "--output", str(output),
            ]
            with mock.patch.object(sys, "argv", argv), self.assertRaisesRegex(
                SystemExit, "package must be a regular file"
            ):
                MODULE.main()

if __name__ == "__main__":
    unittest.main()
