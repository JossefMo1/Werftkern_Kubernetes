import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "scripts" / "build-deb.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


class ReproducibleBuildContractTests(unittest.TestCase):
    def test_build_script_accepts_and_validates_source_date_epoch(self):
        content = BUILD_SCRIPT.read_text()
        self.assertIn('SOURCE_DATE_EPOCH', content)
        self.assertIn('source_epoch="$SOURCE_DATE_EPOCH"', content)
        self.assertIn('SOURCE_DATE_EPOCH must be an integer Unix timestamp', content)
        self.assertIn('date -u -d "@$source_epoch"', content)

    def test_go_build_disables_implicit_vcs_metadata(self):
        content = BUILD_SCRIPT.read_text()
        self.assertIn('build_flags=(-trimpath -buildvcs=false)', content)
        self.assertIn('go build "${build_flags[@]}"', content)

    def test_package_inputs_and_dpkg_use_same_epoch(self):
        content = BUILD_SCRIPT.read_text()
        self.assertIn('find "$stage" -exec touch -d "@$source_epoch" {} +', content)
        self.assertIn('SOURCE_DATE_EPOCH="$source_epoch" dpkg-deb', content)

    def test_ci_derives_epoch_from_exact_candidate_and_compares_hashes(self):
        content = WORKFLOW.read_text()
        self.assertIn('epoch="$(git show -s --format=%ct "$GITHUB_SHA")"', content)
        self.assertIn('SOURCE_DATE_EPOCH="$epoch" bash scripts/build-deb.sh', content)
        self.assertIn('first_sha="$(sha256sum dist/werftkern_0.2.0~dev4_amd64.deb', content)
        self.assertIn('second_sha="$(sha256sum dist/werftkern_0.2.0~dev4_amd64.deb', content)
        self.assertIn('test "$first_sha" = "$second_sha"', content)
        self.assertIn('reproducible-build.json', content)


if __name__ == "__main__":
    unittest.main()
