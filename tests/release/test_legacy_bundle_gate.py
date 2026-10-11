"""Fail-closed tests for the optional historical source bundle input."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "test-agent-compat.sh"


class HistoricalBundleGate(unittest.TestCase):
    def invoke(self, directory, bundle=None):
        root = pathlib.Path(directory)
        (root / "scripts").mkdir()
        shutil.copyfile(SCRIPT, root / "scripts" / "test-agent-compat.sh")
        env = os.environ.copy()
        env["WERFT_COMPAT_EVIDENCE"] = str(root / "evidence")
        env.pop("WERFT_PREVIOUS_BUNDLE", None)
        if bundle is not None:
            env["WERFT_PREVIOUS_BUNDLE"] = str(bundle)
        return subprocess.run(["bash", str(root / "scripts" / "test-agent-compat.sh")],
                              cwd=root, env=env, capture_output=True, text=True,
                              timeout=15, check=False)

    def test_missing_baseline_requires_explicit_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            process = self.invoke(directory)
            self.assertEqual(process.returncode, 3)
            self.assertIn("BLOCKED", process.stderr)

    def test_unapproved_bundle_sha_rejected_before_build(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = pathlib.Path(directory) / "legacy.bundle"
            bundle.write_bytes(b"not the verified historical bundle")
            process = self.invoke(directory, bundle)
            self.assertEqual(process.returncode, 3)
            self.assertIn("SHA256", process.stderr)
            self.assertFalse((pathlib.Path(directory) / "evidence" /
                              "werft-dev3").exists())


if __name__ == "__main__":
    unittest.main()
