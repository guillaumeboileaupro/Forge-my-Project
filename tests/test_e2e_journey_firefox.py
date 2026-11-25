"""Parcours v2 (E16) dans Firefox reel : progression, conditions, apercu, arbre et diagramme.

Actif avec FORGE_E2E=1, geckodriver et firefox (comme tests/test_e2e_firefox.py) ; serveur
local reel, aucun acces reseau externe (le parcours n'appelle que /api/catalog et /api/plan).
"""
import unittest

from tests import test_e2e_firefox as base

ENABLED = base.ENABLED

BORROWED = ("call", "cmd", "find", "js", "click", "wait", "screenshot")
DRAFT_KEY = "forge-my-project.draft.v1"


def open_v2(test, draft=None):
    """Ouvre le parcours v2 sans brouillon (E18b : brouillon partage avec l'interface actuelle), ou avec celui fourni.
    Le stockage est prepare depuis une ressource du meme domaine, sans l'application."""
    test.cmd("POST", "/url", {"url": test.base + "/v2/tokens.css"})
    test.js("localStorage.removeItem(arguments[0]); if (arguments[1]) localStorage.setItem(arguments[0], arguments[1]);",
            DRAFT_KEY, draft)
    test.cmd("POST", "/url", {"url": test.base + "/v2/parcours"})
    test.wait("return performance.getEntriesByName('forge-ready').length === 1")


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxJourneyTests(unittest.TestCase):
    setUpClass = classmethod(base.FirefoxFormTests.setUpClass.__func__)
    tearDownClass = classmethod(base.FirefoxFormTests.tearDownClass.__func__)
    call = classmethod(base.FirefoxFormTests.call.__func__)

    def setUp(self):
        open_v2(self)
        self.wait("return document.querySelectorAll('#step-list button').length === 7")

    def type_name(self, value):
        self.js("const n = document.querySelector('#q-name'); n.value = arguments[0];"
                "n.dispatchEvent(new Event('input', {bubbles: true}));", value)

    def check(self, css):
        self.click(css)

    def fill_minimal(self, technologies=("python",)):
        self.type_name("demo-journey")
        self.check('input[name="q-type"][value="cli"]')
        self.click("#next")
        for tech in technologies:
            self.check('input[name="q-tech"][value="%s"]' % tech)

    def states(self):
        return self.js("return [...document.querySelectorAll('#step-list .step-state')].map(e => e.textContent)")

    def test_progressive_and_conditional_steps(self):
        self.assertEqual(self.states()[3], "sans objet")  # aucune technologie : pas de version a choisir
        self.assertTrue(self.js("return document.querySelector('#step-list [data-step=\"versions\"]').disabled"))
        self.fill_minimal()
        self.assertEqual(self.js("return document.activeElement.value"), "python")  # focus conserve
        self.assertEqual(self.states()[1], "complète")
        self.click("#next")
        tools = self.js("return [...document.querySelectorAll('input[name=\"q-tech\"]')].map(e => e.value)")
        self.assertIn("pytest", tools)
        self.assertNotIn("vitest", tools)  # prerequis node absent : question masquee
        self.assertNotEqual(self.states()[3], "sans objet")
        self.screenshot("e16-journey-tools")

    def test_hidden_answers_are_pruned_and_never_sent(self):
        self.fill_minimal()
        self.click("#next")
        self.check('input[name="q-tech"][value="pytest"]')
        self.click("#prev")
        self.check('input[name="q-tech"][value="python"]')  # decocher python
        config = self.js("return window.forgeJourney.config()")
        self.assertNotIn("pytest", config["technologies"])
        self.assertNotIn("python", config["versions"])
        self.assertIn("Pytest".lower(), self.js("return document.querySelector('#step-notice').textContent").lower())

    def ready_plan(self):
        self.fill_minimal(("python",))
        self.click("#next")
        self.check('input[name="q-tech"][value="pytest"]')
        self.js("window.forgeJourney.state.answers.agents = ['claude'];")
        self.check('input[name="q-tech"][value="ruff"]')
        self.wait("return window.forgeJourney.state.validation === 'valid'")

    def test_tree_and_diagram_share_the_selection(self):
        self.ready_plan()
        self.assertTrue(self.js("return document.querySelectorAll('#tree [data-path]').length > 10"))
        self.click('#tree [data-path="pyproject.toml"]')
        self.assertEqual(self.js("return document.querySelector('#diagram .node.lit[data-path]').dataset.path"), "pyproject.toml")
        lit = self.js("return [...document.querySelectorAll('#diagram .node.lit')].map(n => n.dataset.key)")
        self.assertIn("r:scaffold-python", lit)
        self.assertIn("t:python", lit)
        self.assertIn("[project]", self.js("return document.querySelector('#content').value"))
        self.js("document.querySelector('#diagram [data-path=\"README.md\"]')"
                ".dispatchEvent(new MouseEvent('click', {bubbles: true}))")
        self.assertEqual(self.js("return document.querySelector('#tree .selected').dataset.path"), "README.md")
        self.assertEqual(self.js("return document.querySelector('#tree [aria-current]').dataset.path"), "README.md")
        self.assertFalse(self.js("return window.forgeJourney.select('inconnu.txt', true)"))
        self.assertEqual(self.js("return window.forgeJourney.state.selectedPath"), "README.md")
        self.js("document.querySelector('#diagram').scrollIntoView()")
        self.screenshot("e16-journey-preview")

    def test_diagram_only_shows_real_plan_elements(self):
        self.ready_plan()
        graph = self.js("return window.forgeJourney.state.plan.graph")
        keys = set(self.js("return [...document.querySelectorAll('#diagram .node')].map(n => n.dataset.key)"))
        expected = {"t:" + t["id"] for t in graph["technologies"]} | {"f:" + f["path"] for f in graph["files"]}
        self.assertLessEqual(expected, keys)
        rules = {k[2:] for k in keys if k.startswith("r:")}
        self.assertLessEqual(rules, {r["id"] for r in graph["rules"]})
        edges = self.js("return [...document.querySelectorAll('#diagram .edges path')].map(p => [p.dataset.from, p.dataset.to])")
        self.assertTrue(edges)
        for source, target in edges:
            self.assertIn(source, keys)
            self.assertIn(target, keys)

    def test_reference_widths_have_no_horizontal_page_scroll(self):
        self.ready_plan()
        try:
            # Firefox impose une largeur minimale de fenetre : 360 px reste a valider en E18 (mode adaptatif).
            for width, height in ((500, 800), (768, 1024), (1280, 800), (1920, 1080)):
                with self.subTest(width=width):
                    self.cmd("POST", "/window/rect", {"width": width, "height": height})
                    self.wait("return window.innerWidth <= %d" % width)
                    self.assertLessEqual(self.js("return document.documentElement.scrollWidth - window.innerWidth"), 0)
                    self.screenshot("e16-journey-%d" % width)
        finally:
            self.cmd("POST", "/window/rect", {"width": 1366, "height": 768})

    def test_older_response_never_replaces_a_newer_state(self):
        self.ready_plan()
        # La premiere requete suivante est retardee : la seconde, plus recente, doit gagner.
        self.js("""
            const original = window.fetch; let calls = 0;
            window.fetch = (url, options) => {
              if (url === '/api/plan' && calls++ === 0) {
                return new Promise(resolve => setTimeout(() => resolve(original(url, options)), 1500));
              }
              return original(url, options);
            };""")
        self.check('input[name="q-tech"][value="mypy"]')
        self.wait("return window.forgeJourney.state.validation === 'running'")
        self.check('input[name="q-tech"][value="mypy"]')  # retire mypy : etat final sans mypy
        self.wait("return window.forgeJourney.state.validation === 'valid'")
        self.js("return new Promise(r => setTimeout(r, 1800))")
        ids = self.js("return window.forgeJourney.state.plan.graph.technologies.map(t => t.id)")
        self.assertNotIn("mypy", ids)


for _name in BORROWED[1:]:
    setattr(FirefoxJourneyTests, _name, getattr(base.FirefoxFormTests, _name))


if __name__ == "__main__":
    unittest.main()
