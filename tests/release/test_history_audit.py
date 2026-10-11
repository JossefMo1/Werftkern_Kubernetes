import importlib.util
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("audit_git_history", ROOT / "scripts/audit-git-history.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class HistoryPublicationAuditTests(unittest.TestCase):
    def command(self, root, *args):
        return subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True).stdout

    def run_audit(self, root, require_noreply=False):
        def local_git(*args):
            return self.command(root, *args)
        with patch.object(AUDIT, "git", local_git):
            return AUDIT.scan(require_noreply=require_noreply)

    def make_repo(self, root):
        self.command(root, "init", "-q")
        self.command(root, "config", "user.name", "Test Maintainer")
        self.command(root, "config", "user.email", "12345+test@users.noreply.github.com")

    def commit(self, root, file_name, data):
        p = root / file_name
        p.write_bytes(data)
        self.command(root, "add", file_name)
        self.command(root, "commit", "-qm", "fixture")

    def test_clean_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            self.commit(root, "README.md", b"experimental source")
            report = self.run_audit(root, require_noreply=True)
            self.assertEqual(report["status"], "PASS")

    def test_removed_private_key_still_blocks_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            secret = b"-----BEGIN " + b"PRIVATE KEY-----\nNOT-REAL-SECRET\n"
            self.commit(root, "unsafe.txt", secret)
            self.commit(root, "unsafe.txt", b"removed from working tree")
            report = self.run_audit(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(any(f["reason"] == "private-key" for f in report["findings"]))
            self.assertNotIn("NOT-REAL-SECRET", str(report))

    def test_historical_sensitive_filename_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            self.commit(root, ".env", b"PLACEHOLDER=example")
            self.command(root, "rm", "-q", ".env")
            self.command(root, "commit", "-qm", "delete")
            report = self.run_audit(root)
            self.assertTrue(any(f["reason"] == "sensitive-filename" for f in report["findings"]))

    def test_one_time_email_privacy_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            self.command(root, "config", "user.email", "example@example.org")
            self.commit(root, "README.md", b"test")
            self.assertEqual(self.run_audit(root)["status"], "PASS")
            self.assertEqual(self.run_audit(root, require_noreply=True)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
