"""Guard the canonical public Go module identity used by builds and imports."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
NEW = "github.com/JossefMo1/Werftkern_Kubernetes"
OLD = "github.com/ClusterPilot-System/werftkern"


class GoModuleIdentityTests(unittest.TestCase):
    def test_go_module_matches_repository(self):
        module = (ROOT / "go.mod").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(module, "module " + NEW)

    def test_no_obsolete_go_source_imports(self):
        stale = [
            str(p.relative_to(ROOT))
            for p in ROOT.rglob("*.go")
            if OLD in p.read_text(encoding="utf-8")
        ]
        self.assertEqual(stale, [], "Go imports still refer to the old repository path")

    def test_build_linker_flags_match_module(self):
        build = (ROOT / "scripts/build-deb.sh").read_text(encoding="utf-8")
        self.assertNotIn(OLD, build)
        self.assertIn(NEW + "/internal/cli.BuildCommit", build)
        self.assertIn(NEW + "/internal/cli.BuildTime", build)


if __name__ == "__main__":
    unittest.main()
