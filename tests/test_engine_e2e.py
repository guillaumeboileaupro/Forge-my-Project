"""E08 : socle de bout en bout des projets generes (temoins reels, sans reseau ni scenario metier)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forge.pipeline import run

ROOT = Path(__file__).resolve().parents[1]
PYTHON = {"schema_version": 1, "name": "e2e-demo", "project_type": "cli", "description": "Demo",
          "technologies": ["python", "pytest"], "agents": ["codex"]}
NODE_JS = {"schema_version": 1, "name": "e2e-node", "project_type": "cli", "description": "Demo",
           "technologies": ["javascript", "node", "node-test"], "agents": ["codex"]}
E2E_TOOLS = ("playwright", "cypress", "puppeteer", "selenium", "supertest", "webdriver", "httpx", "requests")


def profile(name):
    data = json.loads((ROOT / "catalogs" / "profiles" / (name + ".json")).read_text(encoding="utf-8"))
    return dict(data["answers"], name="demo-" + name[:30])


def write_project(files, root):
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


class PythonWitnessTests(unittest.TestCase):
    """Le temoin verifie le paquet installe : il echoue s'il n'est pas installe ou s'il l'est depuis src/."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="forge-e2e-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "project"
        write_project(run(PYTHON).files, self.project)
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(self.tmp / "venv")], check=True)
        self.python = self.tmp / "venv" / "bin" / "python"
        purelib = subprocess.run([str(self.python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
                                 capture_output=True, text=True, check=True).stdout.strip()
        self.site = Path(purelib)

    def install_metadata(self):
        info = self.site / "e2e_demo-0.1.0.dist-info"
        info.mkdir()
        (info / "METADATA").write_text("Metadata-Version: 2.1\nName: e2e-demo\nVersion: 0.1.0\n", encoding="utf-8")

    def witness(self):
        return subprocess.run([str(self.python), "-m", "unittest", "discover", "-s", "e2e", "-v"],
                              cwd=self.project, capture_output=True, text=True)

    def test_fails_when_distribution_is_not_installed(self):
        done = self.witness()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("ModuleNotFoundError", done.stderr)

    def test_fails_when_installed_in_editable_mode(self):
        self.install_metadata()
        (self.site / "e2e_demo.pth").write_text(str(self.project / "src") + "\n", encoding="utf-8")
        done = self.witness()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("installer le livrable sans -e", done.stderr)

    def test_sources_on_pythonpath_never_pass(self):
        self.install_metadata()
        done = subprocess.run([str(self.python), "-m", "unittest", "discover", "-s", "e2e", "-v"], cwd=self.project,
                              capture_output=True, text=True, env={"PYTHONPATH": str(self.project / "src")})
        self.assertNotEqual(done.returncode, 0)

    def test_passes_on_installed_distribution(self):
        self.install_metadata()
        shutil.copytree(self.project / "src" / "e2e_demo", self.site / "e2e_demo")
        done = self.witness()
        self.assertEqual(done.returncode, 0, done.stderr)


@unittest.skipUnless(shutil.which("node"), "node requis")
class NodeWitnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="forge-e2e-node-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.files = run(NODE_JS).files
        write_project(self.files, self.tmp)

    def e2e(self):
        script = json.loads(self.files["package.json"])["scripts"]["test:e2e"]
        return subprocess.run(script, shell=True, cwd=self.tmp, capture_output=True, text=True)  # noqa: S602

    def test_javascript_entrypoint_is_loaded(self):
        self.assertIn('import("../src/index.js")', self.files["e2e/entrypoint.e2e.mjs"])
        done = self.e2e()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_broken_entrypoint_fails(self):
        (self.tmp / "src" / "index.js").write_text("export const = ;\n", encoding="utf-8")
        self.assertNotEqual(self.e2e().returncode, 0)


class GenerationTests(unittest.TestCase):
    def test_six_profiles_get_an_e2e_job_and_documentation(self):
        for name in ("python-api-fastapi", "python-cli", "python-library", "python-web-django",
                     "typescript-api-express", "typescript-web-react"):
            with self.subTest(profile=name):
                files = run(profile(name)).files
                workflow = files[".github/workflows/ci.yml"]
                self.assertIn("  e2e:\n    name: Bout en bout (livrable)", workflow)
                self.assertNotIn("continue-on-error", workflow)
                testing = files["docs/TESTING.md"]
                self.assertIn("## Bout en bout (E2E)", testing)
                self.assertIn("NON APPLICABLE" if not name.endswith("library") else "sans objet", testing)
                if name.startswith("python"):
                    self.assertIn('python -m pytest e2e -o addopts=""', workflow)
                    self.assertIn('python -m pip install ".[dev]"', workflow)
                    self.assertIn('"e2e/**" = ["S101", "S603"]', files["pyproject.toml"])
                    if "[tool.mypy]" in files["pyproject.toml"]:  # mypy retenu : l'E2E est type aussi
                        self.assertIn('files = ["src", "tests", "e2e"]', files["pyproject.toml"])
                else:
                    scripts = json.loads(files["package.json"])["scripts"]
                    self.assertEqual(scripts["test:e2e"], "npm run build && node --test e2e/*.e2e.mjs")
                    self.assertIn('import("../dist/index.js")', files["e2e/entrypoint.e2e.mjs"])
                    self.assertIn("npm run test:e2e", workflow)
                self.assertIn("Bout en bout (E2E", files["AGENTS.md"])

    def test_no_e2e_dependency_is_added(self):
        for name in ("python-api-fastapi", "typescript-web-react", "typescript-api-express"):
            files = run(profile(name)).files
            manifest = files.get("package.json", "") + files.get("pyproject.toml", "")
            for tool in E2E_TOOLS:
                self.assertNotIn(tool, manifest.lower(), (name, tool))

    def test_without_test_runner_e2e_is_not_applicable(self):
        files = run(dict(PYTHON, technologies=["python"])).files
        self.assertNotIn("e2e/test_installed_package.py", files)
        self.assertNotIn("  e2e:", files[".github/workflows/ci.yml"])
        self.assertIn("Aucun socle E2E genere", files["docs/TESTING.md"])
        self.assertIn("NON APPLICABLE, aucun lanceur de tests retenu", files["docs/TESTING.md"])
        self.assertNotIn("Bout en bout (E2E", files["AGENTS.md"])
        self.assertNotIn("Bout en bout (livrable)", files["CONTRIBUTING.md"])

    def test_unit_runners_do_not_collect_e2e_tests(self):
        files = run(profile("python-api-fastapi")).files
        self.assertIn('testpaths = ["tests"]', files["pyproject.toml"])
        self.assertTrue(run(profile("typescript-web-react")).files["e2e/entrypoint.e2e.mjs"])
        # Vitest ne collecte que *.test.* / *.spec.* : le suffixe .e2e.mjs reste hors des tests unitaires.
        self.assertNotRegex("e2e/entrypoint.e2e.mjs", r"\.(test|spec)\.")


if __name__ == "__main__":
    unittest.main()
