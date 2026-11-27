import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate-native-release-manifest.py"
SBOM_SCRIPT = ROOT / "scripts" / "generate-native-sbom.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"
COMMIT = "0123456789abcdef0123456789abcdef01234567"


class NativeReleaseManifestContractTests(unittest.TestCase):
    def test_script_documents_evidence_boundary(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("werftkern/native-release-manifest/v1", text)
        self.assertIn("Digest and source identity only", text)
        self.assertIn("production readiness", text)
        self.assertIn("signed", text)

    def test_ci_generates_and_hashes_manifest(self):
        text = CI.read_text(encoding="utf-8")
        self.assertIn("scripts/generate-native-release-manifest.py", text)
        self.assertIn("--sbom evidence/native-sbom.spdx.json", text)
        self.assertIn("evidence/native-release-manifest.json", text)
        self.assertIn("evidence/native-release-manifest.sha256", text)

    def test_manifest_binds_package_and_sbom_bytes(self):
        if shutil.which("dpkg-deb") is None:
            self.skipTest("dpkg-deb unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            package_root = root / "package"
            control_dir = package_root / "DEBIAN"
            control_dir.mkdir(parents=True)
            (control_dir / "control").write_text(
                "Package: werftkern\n"
                "Version: 0.2.0~dev4\n"
                "Architecture: amd64\n"
                "Maintainer: Werftkern test <test@example.invalid>\n"
                "Depends: ca-certificates, python3\n"
                "Description: fixture\n",
                encoding="utf-8",
            )
            package = root / "werftkern.deb"
            build = subprocess.run(
                ["dpkg-deb", "--build", str(package_root), str(package)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, build.stderr)

            modules = root / "modules.json"
            modules.write_text('{"Path":"example.test/root","Version":"v1.0.0"}\n', encoding="utf-8")
            sbom = root / "native-sbom.spdx.json"
            sbom_command = [
                sys.executable,
                str(SBOM_SCRIPT),
                "--package",
                str(package),
                "--modules",
                str(modules),
                "--source-commit",
                COMMIT,
                "--source-date-epoch",
                "1700000000",
                "--output",
                str(sbom),
            ]
            generated = subprocess.run(sbom_command, capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stderr)

            manifest = root / "native-release-manifest.json"
            command = [
                sys.executable,
                str(SCRIPT),
                "--package",
                str(package),
                "--sbom",
                str(sbom),
                "--source-commit",
                COMMIT,
                "--source-date-epoch",
                "1700000000",
                "--output",
                str(manifest),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            first_bytes = manifest.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_bytes, manifest.read_bytes())

            document = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(document["schema"], "werftkern/native-release-manifest/v1")
            self.assertEqual(document["sourceCommit"], COMMIT)
            self.assertEqual(document["sourceDateEpoch"], 1700000000)
            self.assertEqual(document["artifact"]["name"], "werftkern")
            self.assertEqual(document["artifact"]["version"], "0.2.0~dev4")
            self.assertEqual(document["artifact"]["architecture"], "amd64")
            self.assertEqual(document["sbom"]["format"], "SPDX-2.3")
            self.assertFalse(document["qualified"])
            self.assertFalse(document["signed"])


if __name__ == "__main__":
    unittest.main()
