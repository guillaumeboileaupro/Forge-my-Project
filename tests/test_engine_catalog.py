import json
import shutil
import tempfile
import unittest
from pathlib import Path

from forge import CATALOGS_DIR
from forge.config import versions
from forge.config.catalog import CatalogError, load_catalog
from forge.config.spec import SpecError, parse_spec
from forge.rules.compatibility import resolve

BASE = {"name": "demo-api", "project_type": "api", "agents": ["codex"]}


def spec(**overrides):
    data = dict(BASE, technologies=["python", "pytest"])
    data.update(overrides)
    return parse_spec(data)


def codes(resolution):
    return {diag.code for diag in resolution.diagnostics}


class VersionTests(unittest.TestCase):
    def test_satisfies(self):
        self.assertTrue(versions.satisfies("3.12", ">=3.10"))
        self.assertTrue(versions.satisfies("3.12.1", ">=3.12,<3.13"))
        self.assertFalse(versions.satisfies("3.9", ">=3.10"))
        self.assertTrue(versions.satisfies("22", "==22.0"))

    def test_invalid(self):
        for bad in ("3.x", "", "1.0rc1", None):
            with self.assertRaises(ValueError):
                versions.parse(bad)
        with self.assertRaises(ValueError):
            versions.parse_constraint("~=3.1")


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_repository_catalog_is_valid(self):
        self.assertIn("python", self.catalog.technologies)
        self.assertEqual(self.catalog.get("python").category, "language")
        for tech in self.catalog.technologies.values():
            self.assertTrue(tech.docs.startswith("https://"))
            if tech.ecosystem:
                self.assertTrue(tech.package)

    def _broken_catalog(self, mutate):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        target = tmp / "technologies"
        shutil.copytree(CATALOGS_DIR / "technologies", target)
        path = target / "frameworks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data["technologies"][0])
        path.write_text(json.dumps(data), encoding="utf-8")
        return target

    def test_rejects_unknown_reference(self):
        directory = self._broken_catalog(lambda t: t.update(requires=["cobol"]))
        with self.assertRaisesRegex(CatalogError, "reference inconnue"):
            load_catalog(directory)

    def test_rejects_invalid_package_and_fields(self):
        for mutate in (
            lambda t: t.update(package="bad name"),
            lambda t: t.update(run="rm -rf /"),
            lambda t: t.update(docs="http://insecure.example"),
            lambda t: t.update(commands={"deploy": "x"}),
            lambda t: t.update(constraints={"python": "~=3"}),
        ):
            with self.assertRaises(CatalogError):
                load_catalog(self._broken_catalog(mutate))


class SpecTests(unittest.TestCase):
    def test_valid_spec_is_normalised(self):
        result = parse_spec(dict(BASE, technologies=["python"], agents=["claude", "codex"], description="  Une API\x07 "))
        self.assertEqual(result.agents, ("codex", "claude"))
        self.assertEqual(result.description, "Une API")
        self.assertEqual(result.security, "strict")
        self.assertFalse(result.options["mcp"])

    def test_rejects_invalid_values(self):
        bad_values = [
            {"name": "../x"}, {"agents": []}, {"agents": ["gpt"]}, {"technologies": []},
            {"technologies": ["Python"]}, {"project_type": "game"}, {"versions": {"python": "latest"}},
            {"options": {"shell": True}}, {"unknown": 1}, {"technologies": ["python", "python"]},
        ]
        for override in bad_values:
            data = dict(BASE, technologies=["python"])
            data.update(override)
            with self.assertRaises(SpecError, msg=str(override)):
                parse_spec(data)


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_valid_python_selection(self):
        result = resolve(spec(technologies=["python", "fastapi", "pytest", "ruff"]), self.catalog)
        self.assertTrue(result.ok, result.diagnostics)
        self.assertEqual(result.versions, {"python": "3.13"})
        self.assertEqual(result.commands["test"], ["python -m pytest"])
        self.assertIn("ruff check .", result.commands["lint"])

    def test_unknown_technology_blocks(self):
        result = resolve(spec(technologies=["python", "leftpadx"]), self.catalog)
        self.assertFalse(result.ok)
        self.assertIn("unknown-technology", codes(result))

    def test_missing_requirement_is_reported_not_added(self):
        result = resolve(spec(technologies=["typescript", "vitest"]), self.catalog)
        self.assertIn("missing-requirement", codes(result))
        self.assertNotIn("node", result.ids())

    def test_conflict(self):
        result = resolve(spec(technologies=["python", "flask", "django"]), self.catalog)
        self.assertIn("conflict", codes(result))
        self.assertIn("category-min", codes(resolve(spec(technologies=["node", "node-test"]), self.catalog)))

    def test_one_way_conflict_is_detected(self):
        catalog = load_catalog()
        object.__setattr__(catalog.get("ruff"), "conflicts", ("mypy",))
        object.__setattr__(catalog.get("mypy"), "conflicts", ())
        result = resolve(spec(technologies=["python", "ruff", "mypy"]), catalog)
        self.assertEqual([x.code for x in result.diagnostics if x.code == "conflict"], ["conflict"])

    def test_versions(self):
        unsupported = resolve(spec(versions={"python": "3.9"}), self.catalog)
        self.assertIn("version-unsupported", codes(unsupported))
        stray = resolve(spec(versions={"node": "22"}), self.catalog)
        self.assertIn("version-unselected", codes(stray))
        chosen = resolve(spec(technologies=["typescript", "node", "vitest"], versions={"node": "22"}), self.catalog)
        self.assertTrue(chosen.ok, chosen.diagnostics)
        self.assertEqual(chosen.versions["node"], "22")

    def test_version_constraint(self):
        catalog = load_catalog()
        python = catalog.get("python")
        object.__setattr__(python, "supported_versions", python.supported_versions + ("3.9",))
        result = resolve(spec(technologies=["python", "django"], versions={"python": "3.9"}), catalog)
        self.assertIn("version-constraint", codes(result))

    def test_unknown_test_command_is_signalled(self):
        result = resolve(spec(technologies=["python"]), self.catalog)
        self.assertTrue(result.ok)
        self.assertIn("unknown-command", codes(result))


if __name__ == "__main__":
    unittest.main()
