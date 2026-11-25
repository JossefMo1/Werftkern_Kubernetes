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
PRERM = pathlib.Path(__file__).parents[2] / "packaging" / "prerm"
POSTRM = pathlib.Path(__file__).parents[2] / "packaging" / "postrm"
NATIVE_SERVICES = (
    "werftkern-dns.service",
    "werftkern-discovery.service",
    "werftkern-agent.service",
    "werftkern-control.service",
    "werftkern-etcd.service",
)
SYSTEMD_HARDENING = (
    "ProtectKernelTunables=true",
    "ProtectKernelModules=true",
    "ProtectControlGroups=true",
    "ProtectKernelLogs=true",
    "ProtectClock=true",
    "LockPersonality=true",
    "RestrictSUIDSGID=true",
    "RestrictRealtime=true",
    "SystemCallArchitectures=native",
)


class NativePackageLayoutTests(unittest.TestCase):
    def test_postinst_smokes_both_installed_entrypoints(self):
        content = POSTINST.read_text()
        self.assertIn("/usr/bin/werft --help", content)
        self.assertIn("/usr/bin/werft-ops --help", content)

    def test_prerm_stops_and_disables_every_native_service(self):
        content = PRERM.read_text()
        self.assertIn("systemctl stop", content)
        self.assertIn("systemctl disable", content)
        self.assertIn("|| true", content)
        for service in NATIVE_SERVICES:
            self.assertIn(service, content)
        self.assertIn("Managed containers and all persisted keys/data are retained", content)

    def test_native_services_keep_kernel_and_privilege_hardening(self):
        root = pathlib.Path(__file__).parents[2] / "packaging" / "systemd"
        for service in NATIVE_SERVICES:
            content = (root / service).read_text()
            for directive in SYSTEMD_HARDENING:
                with self.subTest(service=service, directive=directive):
                    self.assertIn(directive, content)

    def test_remove_scripts_never_delete_persisted_state_or_workloads(self):
        for script in (PRERM, POSTRM):
            content = script.read_text()
            self.assertNotRegex(
                content,
                r"(?im)\\b(?:rm|shred)\\b[^\\n]*(?:/var/lib/werftkern|/etc/werftkern|/var/lib/docker)",
            )
            self.assertNotIn("find /var/lib/werftkern -delete", content)
        self.assertIn("Never automatically delete identities, state or customer workloads", POSTRM.read_text())

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

    def test_wrapper_fails_closed_when_entrypoint_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            wrapper = root / "usr" / "bin" / "werft-ops"
            wrapper.parent.mkdir(parents=True)
            shutil.copyfile(pathlib.Path(__file__).parents[2] / "scripts" / "werft-ops", wrapper)
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
            package = root / "usr" / "lib" / "werftkern" / "ops" / "werftops"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("")

            result = subprocess.run(
                [sys.executable, str(wrapper)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 78)
        self.assertIn("werft-ops: Python modules not found", result.stderr)

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
