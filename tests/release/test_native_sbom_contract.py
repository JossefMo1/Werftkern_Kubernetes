import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate-native-sbom.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"


class NativeSbomContractTests(unittest.TestCase):
    def test_script_uses_exact_candidate_and_deterministic_timestamp(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("SPDX-2.3", text)
        self.assertIn("documentNamespace", text)
        self.assertIn("source_commit", text)
        self.assertIn("source_date_epoch", text)
        self.assertIn("OS vulnerability scanning and signing are separate release gates", text)

    def test_ci_generates_and_uploads_bounded_native_sbom(self):
        text = CI.read_text(encoding="utf-8")
        self.assertIn("go list -m -json all > evidence/go-modules.json", text)
        self.assertIn("scripts/generate-native-sbom.py", text)
        self.assertIn("--source-commit \"$GITHUB_SHA\"", text)
        self.assertIn("--source-date-epoch \"$epoch\"", text)
        self.assertIn("evidence/native-sbom.spdx.json", text)

    def test_generator_emits_stable_spdx_for_fixture_package(self):
        if shutil.which("dpkg-deb") is None:
            self.skipTest("dpkg-deb unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            control = root / "control"
            control.write_text(
                "Package: werftkern\nVersion: 0.2.0~dev4\nArchitecture: amd64\n"
                "Maintainer: Werftkern test <test@example.invalid>\n"
                "Depends: ca-certificates, python3\nDescription: fixture\n",
                encoding="utf-8",
            )
            package_root = root / "pkg"
            (package_root / "DEBIAN").mkdir(parents=True, mode=0o755)
            package_root.chmod(0o755)
            (package_root / "DEBIAN").chmod(0o755)
            (package_root / "DEBIAN" / "control").write_text(control.read_text(encoding="utf-8"), encoding="utf-8")
            package = root / "fixture.deb"
            package_build = subprocess.run(
                ["dpkg-deb", "--build", str(package_root), str(package)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(package_build.returncode, 0, package_build.stderr)
            modules = root / "modules.json"
            modules.write_text('{"Path":"example.test/root","Version":"v1.0.0"}\n', encoding="utf-8")
            output = root / "sbom.json"
            command = [
                sys.executable,
                str(SCRIPT),
                "--package",
                str(package),
                "--modules",
                str(modules),
                "--source-commit",
                "0123456789abcdef0123456789abcdef01234567",
                "--source-date-epoch",
                "1700000000",
                "--output",
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            first_bytes = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_bytes, output.read_bytes())
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(document["spdxVersion"], "SPDX-2.3")
            self.assertEqual(document["creationInfo"]["created"], "2023-11-14T22:13:20Z")
            names = {entry["name"] for entry in document["packages"]}
            self.assertTrue({"werftkern", "ca-certificates", "python3", "example.test/root"} <= names)


if __name__ == "__main__":
    unittest.main()
