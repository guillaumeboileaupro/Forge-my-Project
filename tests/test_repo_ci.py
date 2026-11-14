"""La CI de ce depot utilise les memes versions d'outils que les projets generes."""
import unittest
from pathlib import Path

from forge.generator.stack import load_ci_catalog
from forge.security.controls import load_security_tools

WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


class RepositoryCiTests(unittest.TestCase):
    def test_security_tools_are_aligned_with_catalog(self):
        tools = load_security_tools()
        self.assertIn(tools["gitleaks"]["sha256"], WORKFLOW)
        self.assertIn("download/v%s/%s" % (tools["gitleaks"]["version"], tools["gitleaks"]["asset"]), WORKFLOW)
        self.assertIn('"bandit==%s"' % tools["pypi"]["bandit"], WORKFLOW)

    def test_new_jobs_use_catalog_action_pins(self):
        for action in load_ci_catalog()["actions"].values():
            if action["repository"] != "actions/upload-artifact":
                self.assertIn("%s@%s" % (action["repository"], action["sha"]), WORKFLOW)

    def test_detection_proof_runs_in_ci(self):
        self.assertIn("python3 tests/smoke_security.py", WORKFLOW)
        self.assertNotIn("continue-on-error", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
