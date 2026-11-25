"""Integration de l'editeur et des diagnostics a la coque (E17) dans Firefox reel : panneaux `editor`
et `diagnostics` masquables et redimensionnables, onglets des fichiers ouverts (modele ARIA tabs,
fermeture), commandes de l'atelier. Les contrats E17a (editeur, diagnostics, ecriture) sont verifies
par tests/test_e2e_editor_firefox.py, inchange.

Actif avec FORGE_E2E=1, geckodriver et firefox. Chaque test part de preferences vides.
"""
import unittest

from tests import test_e2e_firefox as base
from tests import test_e2e_journey_firefox as journey
from tests import test_e2e_acceptance_firefox as acceptance
from tests import test_e2e_shell_firefox as shell

ENABLED = base.ENABLED
ENTER, CTRL = acceptance.ENTER, acceptance.CTRL
RIGHT, LEFT, HOME, END = shell.RIGHT, shell.LEFT, shell.HOME, shell.END
DELETE = ""
TABS = "return [...document.querySelectorAll('#file-tabs [role=tab]')].map(t => [t.dataset.path, t.getAttribute('aria-selected'), t.tabIndex])"


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxWorkbenchTests(shell.FirefoxShellTests):
    # Les tests de la coque ne sont pas rejoues ici : seule leur preparation est heritee.
    for _name in [n for n in dir(shell.FirefoxShellTests) if n.startswith("test_")]:
        locals()[_name] = None
    del _name

    def open_files(self, *paths):
        for path in paths:
            self.click('#tree [data-path="%s"]' % path)
            self.wait("return window.forgeJourney.editor.path() === %r" % path)

    def tab(self, path):
        return '#file-tabs [data-path="%s"]' % path

    # --- Onglets des fichiers ouverts --------------------------------------------------
    def test_open_files_become_tabs_with_explicit_activation(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.assertTrue(self.js("return document.querySelector('#file-tabs').hidden"))  # aucun fichier ouvert
        self.assertTrue(self.js("return document.querySelector('#close-tab').disabled"))
        self.open_files("README.md", "pyproject.toml", "AGENTS.md")
        self.assertEqual(self.js(TABS), [["README.md", "false", -1], ["pyproject.toml", "false", -1], ["AGENTS.md", "true", 0]])
        self.assertEqual(self.js("return document.querySelector('#editor-tabpanel').getAttribute('aria-labelledby')"),
                         self.js("return document.querySelector(arguments[0]).id", self.tab("AGENTS.md")))
        # Clic sur un onglet : selection partagee avec l'arborescence et l'editeur.
        self.click(self.tab("README.md"))
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "README.md")
        self.assertEqual(self.js("return document.querySelector('#tree .selected').dataset.path"), "README.md")
        # Clavier : la fleche deplace le focus sans activer ; Entree active ; Debut/Fin ; boucle.
        self.js("document.querySelector(arguments[0]).focus()", self.tab("README.md"))
        self.keys(RIGHT)
        self.assertEqual(self.active("el.dataset.path"), "pyproject.toml")
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "README.md")
        self.keys(ENTER)
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "pyproject.toml")
        self.keys(END)
        self.assertEqual(self.active("el.dataset.path"), "AGENTS.md")
        self.keys(RIGHT)
        self.assertEqual(self.active("el.dataset.path"), "README.md")
        self.keys(HOME, LEFT)
        self.assertEqual(self.active("el.dataset.path"), "AGENTS.md")
        # Un fichier modifie est signale sur son onglet.
        self.js("const area = document.querySelector('#content'); area.value += '\\n# ajout';"
                " area.dispatchEvent(new Event('input', {bubbles: true}));")
        self.assertTrue(self.js("return document.querySelector(arguments[0]).classList.contains('modified')", self.tab("pyproject.toml")))
        self.assertEqual(self.js("return document.querySelector(arguments[0]).getAttribute('aria-label')", self.tab("pyproject.toml")),
                         "pyproject.toml (modifié)")
        self.assert_no_errors()

    def test_closing_tabs_moves_to_the_neighbour_and_keeps_the_focus(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.open_files("README.md", "pyproject.toml", "AGENTS.md")
        self.click(self.tab("pyproject.toml"))
        self.js("document.querySelector(arguments[0]).focus()", self.tab("pyproject.toml"))
        self.keys(DELETE)  # Suppr ferme l'onglet focalise ; le voisin devient actif et recoit le focus
        self.assertEqual([t[0] for t in self.js(TABS)], ["README.md", "AGENTS.md"])
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "AGENTS.md")
        self.assertEqual(self.active("el.dataset.path"), "AGENTS.md")
        self.click("#close-tab")
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "README.md")
        self.click("#close-tab")
        self.assertEqual(self.js(TABS), [])
        self.assertIsNone(self.js("return window.forgeJourney.editor.path()"))
        self.assertIsNone(self.js("return window.forgeJourney.state.selectedPath"))
        self.assertTrue(self.js("return document.querySelector('#close-tab').disabled"))
        self.assertEqual(self.js("return document.querySelectorAll('#tree .selected').length"), 0)
        # Au plus MAX_TABS onglets : le plus ancien est ferme.
        files = self.js("return window.forgeJourney.state.plan.graph.files.map(f => f.path)")
        limit = self.js("return window.ForgeFileTabs.MAX_TABS")
        self.assertGreater(len(files), limit)
        for path in files[:limit + 1]:
            self.js("window.forgeJourney.select(arguments[0], true)", path)
        self.assertEqual([t[0] for t in self.js(TABS)], files[1:limit + 1])
        self.assert_no_errors()

    def test_tabs_are_limited_to_files_of_the_current_plan(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.open_files("README.md", "CLAUDE.md")
        self.click('#step-list button[data-step="agents"]')
        self.check('input[name="q-agent"][value="codex"]')
        self.check('input[name="q-agent"][value="claude"]')
        self.wait("return !window.forgeJourney.state.plan.graph.files.some(f => f.path === 'CLAUDE.md')"
                  " && window.forgeJourney.state.validation === 'valid'")
        self.assertEqual([t[0] for t in self.js(TABS)], ["README.md"])
        self.assertIsNone(self.js("return window.forgeJourney.editor.path()"))
        self.assert_no_errors()

    # --- Panneaux de l'atelier ------------------------------------------------------------
    def test_editor_and_diagnostics_panels_hide_restore_and_resize(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.open_files("README.md")
        bench = "return Math.round(document.querySelector(arguments[0]).getBoundingClientRect().width)"
        full = self.js(bench, ".workbench")
        self.js("document.querySelector('[data-hide=\"editor\"]').focus()")
        self.keys(ENTER)
        self.assertTrue(self.js("return document.querySelector('#editor-panel').hidden"))
        self.assertTrue(self.active("el.matches('.rail [data-toggle=\"editor\"]')"))  # commande de restauration
        self.assertAlmostEqual(self.js(bench, ".workbench .side"), full, delta=2)  # colonne de droite pleine largeur
        self.load()
        self.assertTrue(self.js("return document.querySelector('#editor-panel').hidden"))  # disposition conservee
        self.assertEqual(self.prefs()["panels"]["editor"], {"visible": False})
        self.click('.rail [data-toggle="editor"]')
        self.assertFalse(self.js("return document.querySelector('#editor-panel').hidden"))
        self.click('[data-hide="diagnostics"]')
        self.assertTrue(self.js("return document.querySelector('#diagnostics-section').hidden"))
        self.assertFalse(self.js("return document.querySelector('#workflow').closest('[hidden]') !== null"))  # validation et ecriture restent
        self.js("window.forgeShell.run('go.diagnostics')")  # « Aller a » restaure le panneau masque
        self.assertFalse(self.js("return document.querySelector('#diagnostics-section').hidden"))
        self.assertEqual(self.active("el.id"), "diagnostics-title")
        # Separateur de l'atelier : la fleche gauche elargit la colonne de droite, bornes 280-640.
        separator = '[data-splitter="diagnostics"]'
        self.assertEqual(self.js("return document.querySelector(arguments[0]).getAttribute('aria-controls')", separator), "workbench-side")
        self.js("document.querySelector(arguments[0]).focus()", separator)
        self.keys(HOME)
        self.assertEqual(self.js(bench, ".workbench .side"), 280)
        self.keys(LEFT)
        self.assertEqual(self.js(bench, ".workbench .side"), 296)
        self.keys(END)
        self.assertEqual(self.js(bench, ".workbench .side"), 546)  # 40 % de 1366 px < 640
        self.load()
        self.assertEqual(self.js(bench, ".workbench .side"), 546)
        self.js("window.forgeShell.run('layout.reset')")
        self.assertEqual(self.prefs()["panels"]["diagnostics"], {"visible": True, "size": None})
        self.assert_no_errors()

    # --- Commandes de l'atelier ---------------------------------------------------------
    def test_workbench_commands_in_the_palette(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        for command in ("editor.tab.next", "editor.tab.close", "editor.search"):
            self.assertNotIn(command, self.commands())  # aucun fichier ouvert : commandes absentes
        self.open_files("README.md", "pyproject.toml")
        self.assertTrue({"editor.tab.next", "editor.tab.prev", "editor.tab.close", "editor.search"} <= set(self.commands()))
        self.keys((CTRL, "k"))
        self.type_text("rechercher fichier")
        shortcut = self.js("return document.querySelector('#palette-list [role=option] kbd').textContent")
        self.assertEqual(shortcut, "Ctrl+F")  # raccourci reel de l'editeur
        self.keys(ENTER)
        self.assertTrue(self.active("el.classList.contains('editor-query')"))
        self.js("window.forgeShell.run('editor.tab.next')")
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "README.md")
        self.js("window.forgeShell.run('editor.tab.prev')")
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "pyproject.toml")
        self.js("window.forgeShell.run('editor.tab.close')")
        self.assertEqual([t[0] for t in self.js(TABS)], ["README.md"])
        self.assertNotIn("editor.tab.next", self.commands())  # un seul onglet
        # Editeur masque : la recherche le rend visible avant d'ouvrir le champ.
        self.js("window.forgeShell.run('view.editor.toggle')")
        self.js("window.forgeShell.run('editor.search')")
        self.assertFalse(self.js("return document.querySelector('#editor-panel').hidden"))
        self.assertTrue(self.active("el.classList.contains('editor-query')"))
        self.assert_no_errors()


if __name__ == "__main__":
    unittest.main()
