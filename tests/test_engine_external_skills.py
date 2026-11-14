import unittest

from forge.config.spec import SpecError, parse_spec
from forge.pipeline import run
from forge.planner.plan import build_plan
from forge.skills import bundle
from forge.skills.external import keywords_for_plan, search
from forge.skills.github import GhCliClient
from forge.skills.service import skills_for_plan
from forge.verification.http import FetchError

SHA_A, SHA_B = "a" * 40, "b" * 40
HEADER = "---\nname: {name}\ndescription: {description}\n---\n"
REPOS = {
    "anthropics/skills": (SHA_A, {
        "skills/webapp-testing/SKILL.md": HEADER.format(name="webapp-testing", description="Test React web apps"),
        "skills/webapp-testing/run.py": "print()",
        "skills/pdf/SKILL.md": HEADER.format(name="pdf", description="PDF files"),
    }),
    "stranger/agent-stuff": (SHA_B, {
        "skills/react-helper/SKILL.md": HEADER.format(name="react-helper", description="React components"),
    }),
    "owner/my-skills": (SHA_A, {}),
}
CONFIG = {
    "my_skills": {"repository": "owner/my-skills", "ref": "main", "path": "skills"},
    "copy": bundle.load_copy_policy()["copy"],
    "external_catalogs": [{"label": "Anthropic", "repository": "anthropics/skills", "ref": "main", "path": "skills"}],
    "search": {"github_code_search": True, "max_candidates": 20},
}
SPEC = {"name": "shop-web", "project_type": "web", "agents": ["claude"],
        "technologies": ["typescript", "node", "react", "vitest"]}


class FakeClient:
    def __init__(self, offline=()):
        self.offline = set(offline)

    def get_json(self, api_path):
        if api_path.startswith("/search/code"):
            return {"items": [{"repository": {"full_name": "stranger/agent-stuff"}, "path": "skills/react-helper/SKILL.md"},
                              {"repository": {"full_name": "root/skill"}, "path": "SKILL.md"}]}
        repository = "/".join(api_path.split("/")[2:4])
        if repository in self.offline or repository not in REPOS:
            raise FetchError("indisponible")
        sha, files = REPOS[repository]
        if "/commits/" in api_path:
            return {"sha": sha}
        return {"tree": [{"path": p, "mode": "100644", "type": "blob", "size": len(c)} for p, c in files.items()]}

    def get_text(self, repository, path, sha):
        return REPOS[repository][1][path]


class FakeGh(FakeClient, GhCliClient):
    pass


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan(SPEC)

    def test_keywords_come_from_the_configuration(self):
        self.assertEqual(keywords_for_plan(self.plan), ["node", "react", "typescript", "vitest", "web"])

    def test_recognized_catalog_candidates_only_without_gh(self):
        result = search(keywords_for_plan(self.plan), FakeClient(), CONFIG)
        self.assertEqual([c.name for c in result.candidates], ["webapp-testing"])
        candidate = result.candidates[0]
        self.assertTrue(candidate.recognized)
        self.assertEqual(candidate.approval(), {"repository": "anthropics/skills", "commit": SHA_A,
                                                "path": "skills", "name": "webapp-testing"})
        self.assertIn("run.py", candidate.ignored_files[0])
        self.assertIn("NON VERIFIEE", " ".join(result.notes))

    def test_github_search_marks_unrecognized_sources(self):
        result = search(keywords_for_plan(self.plan), FakeGh(), CONFIG)
        names = [(c.name, c.recognized) for c in result.candidates]
        self.assertEqual(names, [("webapp-testing", True), ("react-helper", False)])
        self.assertIn("Source non reconnue", result.candidates[1].notes[0])

    def test_unavailable_catalog_is_reported(self):
        result = search(["react"], FakeClient(offline={"anthropics/skills"}), CONFIG)
        self.assertEqual(result.candidates, [])
        self.assertIn("anthropics/skills NON VERIFIE", " ".join(result.notes))


class ApprovalTests(unittest.TestCase):
    def collect(self, approvals):
        plan = build_plan(dict(SPEC, external_skills=approvals))
        return skills_for_plan(plan, FakeClient(), CONFIG)

    def test_nothing_external_is_copied_without_approval(self):
        result = self.collect([])
        self.assertFalse([p for p in result.files if p.startswith(".claude/skills/")])

    def test_approved_skill_is_copied_with_provenance(self):
        approval = {"repository": "stranger/agent-stuff", "commit": SHA_B, "path": "skills", "name": "react-helper"}
        result = self.collect([approval])
        self.assertIn(".claude/skills/react-helper/SKILL.md", result.files)
        self.assertIn("source non reconnue", result.files["docs/SKILLS.md"])

    def test_commit_mismatch_is_not_copied(self):
        approval = {"repository": "stranger/agent-stuff", "commit": SHA_A, "path": "skills", "name": "react-helper"}
        result = self.collect([approval])
        record = [r for r in result.records if r.name == "react-helper"][0]
        self.assertEqual(record.status, "NON VERIFIE")
        self.assertNotIn(".claude/skills/react-helper/SKILL.md", result.files)

    def test_approvals_are_validated_in_the_spec(self):
        good = {"repository": "o/r", "commit": SHA_A, "path": "skills", "name": "x-skill"}
        self.assertEqual(parse_spec(dict(SPEC, external_skills=[good])).external_skills, (("o/r", SHA_A, "skills", "x-skill"),))
        for bad in (dict(good, commit="main"), dict(good, repository="o/r/x"), dict(good, path="../x"),
                    dict(good, name="../x"), {"repository": "o/r"}, dict(good, extra=1)):
            with self.assertRaises(SpecError, msg=str(bad)):
                parse_spec(dict(SPEC, external_skills=[bad]))
        with self.assertRaises(SpecError):
            parse_spec(dict(SPEC, external_skills=[good, good]))

    def test_pipeline_uses_approvals(self):
        approval = {"repository": "anthropics/skills", "commit": SHA_A, "path": "skills", "name": "webapp-testing"}
        result = run(dict(SPEC, external_skills=[approval]), skills=True,
                     skill_collector=lambda plan: skills_for_plan(plan, FakeClient(), CONFIG))
        self.assertIn(".claude/skills/webapp-testing/SKILL.md", result.files)
        self.assertNotIn(".claude/skills/webapp-testing/run.py", result.files)


if __name__ == "__main__":
    unittest.main()
