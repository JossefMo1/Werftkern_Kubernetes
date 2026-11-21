import importlib.util
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).parents[2] / "scripts" / "check-native-package-layout.py"
SPEC = importlib.util.spec_from_file_location("check_native_package_layout", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
POSTINST = pathlib.Path(__file__).parents[2] / "packaging" / "postinst"


class NativePackageLayoutTests(unittest.TestCase):
    def test_postinst_smokes_both_installed_entrypoints(self):
        content = POSTINST.read_text()
        self.assertIn("/usr/bin/werft --help", content)
        self.assertIn("/usr/bin/werft-ops --help", content)

    def test_accepts_required_files_and_executables(self):
        listing = [
            "-rwxr-xr-x root/root 123 2026-01-01 00:00 ./usr/bin/werft",
            "-rwxr-xr-x root/root 456 2026-01-01 00:00 ./usr/bin/werft-ops",
            "-rw-r--r-- root/root 789 2026-01-01 00:00 ./usr/lib/werftkern/ops/werftops/__main__.py",
        ]
        report = MODULE.validate_listing(listing)
        self.assertEqual(report["status"], "passed")

    def test_wrapper_runs_from_extracted_package_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            wrapper = root / "usr" / "bin" / "werft-ops"
            wrapper.parent.mkdir(parents=True)
            shutil.copyfile(pathlib.Path(__file__).parents[2] / "scripts" / "werft-ops", wrapper)
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
            package = root / "usr" / "lib" / "werftkern" / "ops" / "werftops"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("")
            (package / "__main__.py").write_text("print('package-wrapper-ok')\n")

            result = subprocess.run(
                [sys.executable, str(wrapper)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "package-wrapper-ok")

    def test_accepts_required_dependencies(self):
        report = MODULE.validate_dependencies(
            "ca-certificates, openssh-client (>= 1:9), python3, docker.io | docker-ce"
        )
        self.assertEqual(report["status"], "passed")

    def test_rejects_missing_ssh_dependency(self):
        with self.assertRaisesRegex(ValueError, "missing=openssh-client"):
            MODULE.validate_dependencies("ca-certificates, python3")

    def test_rejects_missing_wrapper(self):
        listing = [
            "-rwxr-xr-x root/root 123 2026-01-01 00:00 ./usr/bin/werft",
            "-rw-r--r-- root/root 789 2026-01-01 00:00 ./usr/lib/werftkern/ops/werftops/__main__.py",
        ]
        with self.assertRaisesRegex(ValueError, "missing=.*/usr/bin/werft-ops"):
            MODULE.validate_listing(listing)

    def test_rejects_non_executable_wrapper(self):
        listing = [
            "-rwxr-xr-x root/root 123 2026-01-01 00:00 ./usr/bin/werft",
            "-rw-r--r-- root/root 456 2026-01-01 00:00 ./usr/bin/werft-ops",
            "-rw-r--r-- root/root 789 2026-01-01 00:00 ./usr/lib/werftkern/ops/werftops/__main__.py",
        ]
        with self.assertRaisesRegex(ValueError, "not-executable=.*/usr/bin/werft-ops"):
            MODULE.validate_listing(listing)


if __name__ == "__main__":
    unittest.main()
