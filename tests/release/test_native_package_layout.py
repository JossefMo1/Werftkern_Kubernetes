import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).parents[2] / "scripts" / "check-native-package-layout.py"
SPEC = importlib.util.spec_from_file_location("check_native_package_layout", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NativePackageLayoutTests(unittest.TestCase):
    def test_accepts_required_files_and_executables(self):
        listing = [
            "-rwxr-xr-x root/root 123 2026-01-01 00:00 ./usr/bin/werft",
            "-rwxr-xr-x root/root 456 2026-01-01 00:00 ./usr/bin/werft-ops",
            "-rw-r--r-- root/root 789 2026-01-01 00:00 ./usr/lib/werftkern/ops/werftops/__main__.py",
        ]
        report = MODULE.validate_listing(listing)
        self.assertEqual(report["status"], "passed")

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
