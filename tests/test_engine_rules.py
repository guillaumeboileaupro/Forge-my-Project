import json
import shutil
import tempfile
import unittest
from pathlib import Path

from forge.config.catalog import load_catalog
from forge.config.spec import parse_spec
from forge.diagnostics import ForgeError
from forge.generator.paths import PathError, resolve_inside, safe_relative_path
from forge.generator.render import render_plan
from forge.generator.template import TemplateError, render
from forge.planner.plan import build_plan
from forge.rules.engine import RuleError, compose, load_rules, parse_rule

SPEC = {"name": "demo-api", "project_type": "api", "agents": ["codex"], "description": "Une API",
        "technologies": ["python", "fastapi", "pytest"]}


def rule(rule_id, **fields):
    return dict({"schema_version": 1, "id": rule_id, "description": "regle " + rule_id}, **fields)


class TemplateTests(unittest.TestCase):
    def test_variables_blocks_and_loops(self):
        source = "# {{ p.name }}\n{{#each items}}\n- {{ this.n }}\n{{/each}}\n{{#if flag}}\noui\n{{else}}\nnon\n{{/if}}\n"
        result = render(source, {"p": {"name": "x"}, "items": [{"n": 1}, {"n": 2}], "flag": False})
        self.assertEqual(result, "# x\n- 1\n- 2\nnon\n")

    def test_user_values_are_not_reinterpreted(self):
        self.assertEqual(render("{{ v }}", {"v": "{{ secret }} {{#each x}}"}), "{{ secret }} {{#each x}}\n")

    def test_errors(self):
        for source, context in (
            ("{{ missing }}", {}), ("{{#if a}}x", {"a": 1}), ("{{/if}}", {}), ("{{#each a}}{{/if}}", {"a": []}),
            ("{{ a.__class__ }}", {"a": {}}), ("{{ __import__('os') }}", {}), ("{{#loop a}}{{/loop}}", {"a": []}),
            ("{{ a }}", {"a": [1]}), ("{{#each a}}{{/each}}", {"a": "abc"}), ("{{else}}", {}),
        ):
            with self.assertRaises(TemplateError, msg=source):
                render(source, context)


class PathTests(unittest.TestCase):
    def test_safe_paths(self):
        self.assertEqual(safe_relative_path("docs/adr/0001-x.md"), "docs/adr/0001-x.md")
        for bad in ("../x", "/etc/passwd", "a/../b", "a\\b", "", "a//b", "./a", "a/", "a\x00", " a", None):
            with self.assertRaises(PathError, msg=repr(bad)):
                safe_relative_path(bad)

    def test_symlink_escape(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / "link").symlink_to("/etc")
        with self.assertRaises(PathError):
            resolve_inside(root, "link/passwd")


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()
        self.templates = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.templates)
        (self.templates / "a.md.tmpl").write_text("A {{ project.name }}\n", encoding="utf-8")
        (self.templates / "b.md.tmpl").write_text("B\n", encoding="utf-8")
        self.spec = parse_spec(SPEC)

    def parse(self, raw):
        return parse_rule(raw, self.catalog, self.templates)

    def test_invalid_rules(self):
        for raw in (
            rule("x", when={"language": ["python"]}),
            rule("x", when={"technologies_any": ["cobol"]}),
            rule("x", mandatory=True, when={"agents_any": ["codex"]}),
            rule("x", files=[{"path": "../out", "template": "a.md.tmpl"}]),
            rule("x", files=[{"path": "a.md", "template": "../../etc/passwd"}]),
            rule("x", files=[{"path": "a.md", "template": "missing.tmpl"}]),
            rule("x", sections={"unknown": ["a"]}),
            rule("x", sections={"conventions": ["a\nb"]}),
            rule("x", priority=101), rule("x", skills=["../evil"]), rule("x", run="echo"), rule("X"),
        ):
            with self.assertRaises(RuleError, msg=str(raw)):
                self.parse(raw)

    def test_composition_is_conditional_ordered_and_deduplicated(self):
        rules = sorted([
            self.parse(rule("base", mandatory=True, priority=0, files=[{"path": "A.md", "template": "a.md.tmpl"}],
                            sections={"conventions": ["commun"]})),
            self.parse(rule("py", priority=20, when={"technologies_any": ["python"]},
                            sections={"conventions": ["commun", "python"]}, skills=["python-project-quality"])),
            self.parse(rule("node", priority=20, when={"technologies_any": ["node"]}, sections={"conventions": ["node"]})),
            self.parse(rule("claude", priority=30, when={"agents_any": ["claude"]}, files=[{"path": "CLAUDE.md", "template": "b.md.tmpl"}])),
            self.parse(rule("over", priority=90, when={"project_types": ["api"]},
                            files=[{"path": "A.md", "template": "b.md.tmpl", "override": True}])),
        ], key=lambda r: (r.priority, r.id))
        result = compose(rules, self.spec, {"python", "fastapi", "pytest"})
        self.assertEqual(result.rules, ["base", "py", "over"])
        self.assertEqual(result.sections["conventions"], ["commun", "python"])
        self.assertEqual(result.files, {"A.md": ("b.md.tmpl", "over")})
        self.assertEqual(result.skills, ["python-project-quality"])
        self.assertEqual(result.diagnostics, [])

    def test_file_conflict_without_override(self):
        rules = [self.parse(rule("a", mandatory=True, files=[{"path": "A.md", "template": "a.md.tmpl"}])),
                 self.parse(rule("b", files=[{"path": "A.md", "template": "b.md.tmpl"}]))]
        result = compose(rules, self.spec, set())
        self.assertEqual([x.code for x in result.diagnostics], ["file-conflict"])

    def test_mandatory_rule_required(self):
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory)
        (directory / "x.json").write_text(json.dumps(rule("x")), encoding="utf-8")
        with self.assertRaisesRegex(RuleError, "obligatoire"):
            load_rules(self.catalog, directory, self.templates)

    def test_plan_and_render(self):
        rules = [self.parse(rule("base", mandatory=True, files=[{"path": "A.md", "template": "a.md.tmpl"}],
                                 sections={"architecture": ["couche api"]}))]
        plan = build_plan(SPEC, self.catalog, rules)
        self.assertTrue(plan.ok, plan.diagnostics)
        self.assertEqual(plan.architecture["source"], "suggested")
        self.assertEqual(render_plan(plan, self.templates), {"A.md": "A demo-api\n"})
        manual = build_plan(dict(SPEC, architecture="Hexagonale"), self.catalog, rules)
        self.assertEqual(manual.architecture["source"], "manual")
        empty = build_plan(SPEC, self.catalog, [self.parse(rule("base", mandatory=True))])
        self.assertIn("architecture-undefined", {x.code for x in empty.diagnostics})

    def test_render_refuses_blocking_errors(self):
        rules = [self.parse(rule("base", mandatory=True, files=[{"path": "A.md", "template": "a.md.tmpl"}]))]
        plan = build_plan(dict(SPEC, technologies=["python", "flask", "django"]), self.catalog, rules)
        self.assertFalse(plan.ok)
        with self.assertRaises(ForgeError) as ctx:
            render_plan(plan, self.templates)
        self.assertIn("conflict", {x.code for x in ctx.exception.diagnostics})


if __name__ == "__main__":
    unittest.main()
