"""E16 : route distincte du parcours v2 et graphe du plan reel (sans navigateur)."""
import http.client
import json
import re
import threading
import unittest
from pathlib import Path

from forge import web
from forge.pipeline import run
from forge.planner.graph import plan_graph
import server
from server import Handler, ThreadingHTTPServer
from tests.test_engine_external_skills import CONFIG as SKILL_CONFIG, FakeClient, approval_for
from forge.skills.service import skills_for_plan

ROOT = Path(__file__).resolve().parent.parent
SPEC = {"name": "demo-journey", "project_type": "cli", "agents": ["claude"],
        "technologies": ["python", "pytest", "ruff"]}


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read().decode("utf-8")

    def test_v2_journey_is_served_on_its_own_route(self):
        status, headers, body = self.get("/v2/parcours")
        self.assertEqual(status, 200)
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        for asset in re.findall(r'(?:href|src)="(/v2/[^"]+)"', body):
            self.assertEqual(self.get(asset)[0], 200, asset)
        self.assertEqual(self.get("/v2/tokens.css")[2],
                         (ROOT / "docs" / "design-system" / "tokens.css").read_text(encoding="utf-8"))

    def test_no_external_image_that_the_csp_would_block(self):
        """La CSP n'autorise aucune image (default-src 'none') : le logo est inline et identique a l'actif."""
        html = (ROOT / "ui" / "v2" / "journey.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"<img\b|url\(")
        logo = (ROOT / "assets" / "favicon.svg").read_text(encoding="utf-8")
        for shape in re.findall(r'<(?:path|circle|rect)[^>]+>', logo):
            self.assertIn(shape, html)

    def test_current_interface_is_unchanged(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertNotIn("/v2/", body)


class ScriptContractTests(unittest.TestCase):
    """Contrats E14 : aucun HTML injecte, aucune ressource distante, aucun stockage de donnees projet."""
    SCRIPTS = ("journey.js", "editor.js", "diagnostics.js", "workflow.js")
    # Chaque composant n'appelle que ses endpoints ; l'editeur et le panneau n'appellent rien.
    FETCHES = {"journey.js": {"/api/catalog", "/api/plan"}, "editor.js": set(), "diagnostics.js": set(),
               "workflow.js": {"/api/files/validate", "/api/destination/browse", "/api/write/compare", "/api/write/apply"}}

    def test_no_html_injection_remote_resource_or_storage(self):
        for name in self.SCRIPTS + ("journey.html", "journey.css"):
            text = (ROOT / "ui" / "v2" / name).read_text(encoding="utf-8")
            with self.subTest(name):
                self.assertNotRegex(text, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|new Function")
                self.assertNotRegex(text, r"https?://(?!www\.w3\.org/2000/svg)")
                self.assertNotRegex(text, r"localStorage|sessionStorage|indexedDB")

    def test_each_component_only_calls_its_endpoints(self):
        for name, expected in self.FETCHES.items():
            script = (ROOT / "ui" / "v2" / name).read_text(encoding="utf-8")
            with self.subTest(name):
                calls = set(re.findall(r"fetch\('([^']+)'", script)) | set(re.findall(r"post\('([^']+)'", script))
                self.assertEqual(calls, expected)
                for path in calls:
                    self.assertTrue(path in server.API_POST or path == "/api/catalog", path)  # route reelle du serveur

    def test_workflow_sends_the_existing_contract_fields(self):
        """Memes champs que l'interface actuelle : jeton, decisions, confirm, acknowledge (T17, E06, E07)."""
        script = (ROOT / "ui" / "v2" / "workflow.js").read_text(encoding="utf-8")
        self.assertIn("token: state.comparison.token", script)
        self.assertIn("decisions: state.resolutions, confirm: true, acknowledge: acknowledgement()", script)
        for action in ("keep", "replace", "auto", "merge"):
            self.assertIn("['%s'," % action, script)

    def test_scripts_load_in_dependency_order(self):
        html = (ROOT / "ui" / "v2" / "journey.html").read_text(encoding="utf-8")
        order = re.findall(r'<script src="/v2/([a-z]+\.js)" defer>', html)
        self.assertEqual(order, ["editor.js", "diagnostics.js", "workflow.js", "journey.js"])


class GraphTests(unittest.TestCase):
    def test_graph_lists_each_file_once_with_its_real_rule(self):
        result = run(SPEC)
        graph = plan_graph(result)
        self.assertEqual([f["path"] for f in graph["files"]], sorted(result.files))
        rules = {r["id"]: r for r in graph["rules"]}
        self.assertEqual(list(rules), list(result.plan.composition.rules))
        for file in graph["files"]:
            self.assertIn(file["rule"], rules)
            self.assertEqual(file["origin"], "rule")
        self.assertEqual({f["rule"] for f in graph["files"] if f["path"] == "pyproject.toml"}, {"scaffold-python"})
        selected = {t["id"] for t in graph["technologies"]}
        self.assertEqual(selected, {"python", "pytest", "ruff"})
        for rule in graph["rules"]:
            self.assertLessEqual(set(rule["technologies"]), selected)  # jamais de dependance inventee
        self.assertTrue(rules["base"]["mandatory"])
        self.assertEqual(rules["agent-claude"]["conditions"], ["agents_any"])
        self.assertEqual(rules["scaffold-python"]["technologies"], ["python"])

    def test_package_placeholder_and_skill_files(self):
        spec = dict(SPEC, external_skills=[approval_for("webapp-testing")])
        result = run(spec, skills=True, skill_collector=lambda plan: skills_for_plan(plan, FakeClient(), SKILL_CONFIG))
        files = {f["path"]: f for f in plan_graph(result)["files"]}
        self.assertEqual(files["src/demo_journey/__init__.py"]["rule"], "scaffold-python")
        self.assertEqual(files[".claude/skills/webapp-testing/SKILL.md"], {
            "path": ".claude/skills/webapp-testing/SKILL.md", "rule": None, "origin": "skills"})

    def test_plan_payload_exposes_the_graph(self):
        status, body, _, _ = web.plan_payload(json.dumps({"config": SPEC}).encode())
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual([f["path"] for f in payload["graph"]["files"]], payload["files"])


if __name__ == "__main__":
    unittest.main()
