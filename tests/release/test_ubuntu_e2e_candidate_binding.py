from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class UbuntuE2ECandidateBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "tests/e2e/ubuntu-vm.sh").read_text()
        cls.workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    def test_script_requires_source_sha_and_matches_package_build_info(self):
        self.assertIn('WERFT_CANDIDATE_COMMIT must be a full source SHA', self.script)
        self.assertIn('rev-parse HEAD', self.script)
        self.assertIn('Package BUILD-INFO commit does not match candidate SHA', self.script)
        self.assertIn('info.get("qualified") is not False', self.script)
        self.assertIn('info.get("signed") is not False', self.script)

    def test_script_records_candidate_and_artifact_identity(self):
        for field in (
            'sourceCommit',
            'checkoutCommit',
            'workflowRunId',
            'workflow',
            'packageName',
            'packageSha256',
        ):
            self.assertIn(field, self.script)

    def test_workflow_passes_and_rechecks_exact_candidate_identity(self):
        for value in (
            'ref: ${{ github.sha }}',
            'WERFT_CANDIDATE_COMMIT="$GITHUB_SHA"',
            'WERFT_CANDIDATE_RUN_ID="$GITHUB_RUN_ID"',
            'WERFT_CANDIDATE_WORKFLOW="$GITHUB_WORKFLOW"',
            'candidate binding mismatch',
            'assert result["status"] == "passed"',
        ):
            self.assertIn(value, self.workflow)


if __name__ == "__main__":
    unittest.main()
