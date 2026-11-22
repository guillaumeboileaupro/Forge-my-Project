"""Editeur, panneau diagnostics et flux securises du parcours v2 (E17a) dans Firefox reel.

Actif avec FORGE_E2E=1, geckodriver et firefox (comme tests/test_e2e_firefox.py) ; serveur local
reel, ecriture dans une racine temporaire (FORGE_WRITE_ROOT), aucun acces reseau externe.
"""
import os
import unittest

from tests import test_e2e_firefox as base
from tests import test_e2e_journey_firefox as journey

ENABLED = base.ENABLED
CTRL, RELEASE = "", ""


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxEditorTests(unittest.TestCase):
    setUpClass = classmethod(base.FirefoxFormTests.setUpClass.__func__)
    tearDownClass = classmethod(base.FirefoxFormTests.tearDownClass.__func__)
    call = classmethod(base.FirefoxFormTests.call.__func__)

    def type_keys(self, css, text):
        self.cmd("POST", "/element/%s/value" % self.find(css), {"text": text})

    def set_value(self, css, value):
        self.js("const n = document.querySelector(arguments[0]); n.value = arguments[1];"
                "n.dispatchEvent(new Event('input', {bubbles: true}));", css, value)

    def text(self, css):
        return self.js("return document.querySelector(arguments[0]).textContent", css)

    def open_file(self, path):
        self.click('#tree [data-path="%s"]' % path)
        self.wait("return window.forgeJourney.editor.path() === %r" % path)

    def acknowledge(self):
        if self.js("const box = document.querySelector('#wf-ack'); return Boolean(box) && !box.checked"):
            self.click("#wf-ack")

    def validate(self):
        self.acknowledge()
        self.wait("return !document.querySelector('#wf-validate').disabled")
        self.click("#wf-validate")
        self.wait("return !document.querySelector('#wf-compare').disabled")

    # --- Editeur -----------------------------------------------------------------
    def test_editor_highlights_numbers_lines_and_keeps_layers_aligned(self):
        self.ready_plan()
        self.open_file("pyproject.toml")
        value = self.js("return document.querySelector('#content').value")
        self.assertIn("[project]", value)
        gutter = self.js("return document.querySelector('#editor .editor-gutter').textContent")
        self.assertEqual(gutter.strip().split("\n")[-1], str(len(value.split("\n"))))
        self.assertIn("[project]", self.js("return [...document.querySelectorAll('#editor .tok-section')].map(n => n.textContent)"))
        self.assertTrue(self.js("return document.querySelectorAll('#editor .tok-key').length > 0"))
        self.assertIn("TOML", self.text("#editor .editor-status"))
        # La couche coloree reproduit exactement le texte (aucune perte, aucun ajout hors \\n final).
        self.assertEqual(self.js("return document.querySelector('#editor .editor-layer').textContent"), value + "\n")
        self.js("const a = document.querySelector('#content'); a.scrollTop = 60; a.dispatchEvent(new Event('scroll'));")
        area, layer, gutter = self.js("return ['#content', '#editor .editor-layer', '#editor .editor-gutter']"
                                      ".map(s => document.querySelector(s).scrollTop)")
        self.assertGreater(area, 0)
        self.assertEqual([layer, gutter], [area, area])  # texte, coloration et numeros restent alignes
        self.js("document.querySelector('.workbench').scrollIntoView()")
        base.FirefoxFormTests.screenshot(self, "e17a-editor")

    def test_search_replace_marks_the_file_modified_and_revert_restores(self):
        self.ready_plan()
        self.open_file("README.md")
        original = self.js("return document.querySelector('#content').value")
        self.type_keys("#content", CTRL + "f" + RELEASE)  # raccourci reel, intercepte par l'editeur
        self.wait("return !document.querySelector('#editor .editor-search').hidden")
        self.assertEqual(self.js("return document.activeElement.classList.contains('editor-query')"), True)
        self.assertEqual(self.js("return document.querySelector('#content').value"), original)  # rien de tape
        self.set_value("#content", "alpha Beta ALPHA\nalpha gamma\n" + original)
        occurrences = 3 + original.lower().count("alpha")
        self.set_value("#editor .editor-query", "Alpha")
        self.assertEqual(self.text("#editor .editor-count"), "1 sur %d" % occurrences)
        self.click("#editor .editor-case")  # respecter la casse : « Alpha » n'apparait pas
        self.assertEqual(self.text("#editor .editor-count"), "Aucune occurrence")
        self.click("#editor .editor-case")
        self.click("#editor .editor-next")
        self.assertEqual(self.text("#editor .editor-count"), "2 sur %d" % occurrences)
        self.assertEqual(self.js("return document.querySelectorAll('#editor .match').length"), occurrences)
        self.assertEqual(self.js("return document.querySelectorAll('#editor .match.current').length"), 1)
        self.set_value("#editor .editor-replacement", "omega")
        self.click("#editor .editor-replace")  # remplace l'occurrence courante (la 2e) seulement
        self.assertTrue(self.js("return document.querySelector('#content').value").startswith("alpha Beta omega\n"))
        self.click("#editor .editor-replace-all")
        edited = self.js("return document.querySelector('#content').value")
        self.assertNotIn("alpha", edited.lower())
        self.assertEqual(edited.count("omega"), occurrences)
        self.assertIn("%d remplacement(s)" % (occurrences - 1), self.text("#editor .editor-count"))
        self.js("document.querySelector('.workbench').scrollIntoView()")
        base.FirefoxFormTests.screenshot(self, "e17a-search")
        self.assertEqual(self.js("return window.forgeJourney.files()['README.md']"), edited)
        self.assertEqual(self.js("return window.forgeJourney.config().name"), "demo-journey")  # configuration intacte
        self.assertTrue(self.js("return document.querySelector('#tree [data-path=\"README.md\"]').classList.contains('modified')"))
        self.assertFalse(self.js("return document.querySelector('#editor .editor-modified').hidden"))
        # Changer de fichier puis revenir conserve l'edition.
        self.open_file("pyproject.toml")
        self.open_file("README.md")
        self.assertEqual(self.js("return document.querySelector('#content').value"), edited)
        self.click("#editor .editor-revert")
        self.assertEqual(self.js("return document.querySelector('#content').value"), original)
        self.assertNotIn("README.md", self.js("return Object.keys(window.forgeJourney.state.edits)"))
        self.assertFalse(self.js("return document.querySelector('#tree [data-path=\"README.md\"]').classList.contains('modified')"))
        self.type_keys("#editor .editor-query", "")  # Echap ferme la recherche et rend le focus au texte
        self.assertTrue(self.js("return document.querySelector('#editor .editor-search').hidden"))
        self.assertEqual(self.js("return document.activeElement.id"), "content")

    # --- Diagnostics ---------------------------------------------------------------
    def test_diagnostics_filters_and_navigation_to_the_field(self):
        self.ready_plan()  # description vide : avertissement description-empty du serveur
        self.wait("return Boolean(document.querySelector('#diagnostics-panel [data-code=\"description-empty\"]'))")
        total = self.js("return document.querySelectorAll('#diagnostics-panel li.diag').length")
        self.click('#diagnostics-panel .diag-toggle[data-severity="warning"]')
        self.assertEqual(self.js("return document.querySelector('#diagnostics-panel .diag-toggle[data-severity=\"warning\"]').getAttribute('aria-pressed')"), "false")
        self.assertFalse(self.js("return Boolean(document.querySelector('#diagnostics-panel [data-code=\"description-empty\"]'))"))
        self.assertIn("sur %d" % total, self.text("#diagnostics-panel .diag-summary"))
        self.click('#diagnostics-panel .diag-toggle[data-severity="warning"]')
        self.set_value("#diagnostics-panel .diag-search", "description")
        self.assertEqual(self.js("return [...document.querySelectorAll('#diagnostics-panel li.diag')].map(n => n.dataset.code)"),
                         ["description-empty"])
        self.click('#diagnostics-panel [data-code="description-empty"] .diag-go')
        self.assertEqual(self.js("return document.querySelector('#step-list [aria-current=\"step\"]').dataset.step"), "projet")
        self.assertEqual(self.js("return document.activeElement.id"), "q-description")
        self.js("document.querySelector('#diagnostics-panel').scrollIntoView()")
        base.FirefoxFormTests.screenshot(self, "e17a-diagnostics")

    def test_diagnostic_targets_follow_code_and_subject_only(self):
        """Resolution des cibles avec des diagnostics injectes (codes et sujets reels du moteur)."""
        self.ready_plan()
        self.set_value("#diagnostics-panel .diag-search", "")
        self.js("window.forgeJourney.diagnostics.update(["
                "{code: 'version-unsupported', severity: 'error', message: 'Python 2 non supporte', subject: 'python'},"
                "{code: 'conflict', severity: 'error', message: 'pytest incompatible', subject: 'pytest'},"
                "{code: 'unknown-command', severity: 'warning', message: 'Aucune commande lint', subject: 'lint'},"
                "{code: 'api-static', severity: 'info', message: 'README.md : lien', subject: 'README.md'}], 'test')")
        go = "document.querySelector('#diagnostics-panel [data-code=\"%s\"] .diag-go')"
        self.assertFalse(self.js("return Boolean(%s)" % (go % "unknown-command")))  # aucun lien invente
        self.js("%s.click()" % (go % "version-unsupported"))
        self.assertEqual(self.js("return document.activeElement.id"), "q-version-python")
        self.js("%s.click()" % (go % "conflict"))
        self.assertEqual(self.js("return [document.activeElement.name, document.activeElement.value]"), ["q-tech", "pytest"])
        self.js("%s.click()" % (go % "api-static"))
        self.assertEqual(self.js("return [document.activeElement.id, window.forgeJourney.state.selectedPath]"), ["content", "README.md"])
        # Ordre : erreurs puis avertissements puis informations, ordre du serveur conserve a gravite egale.
        self.assertEqual(self.js("return [...document.querySelectorAll('#diagnostics-panel li.diag')].map(n => n.dataset.code)"),
                         ["version-unsupported", "conflict", "unknown-command", "api-static"])

    # --- Flux securises ---------------------------------------------------------------
    def test_validate_compare_write_then_conflict_kept(self):
        self.ready_plan()
        self.assertTrue(self.js("return document.querySelector('#wf-compare').disabled"))  # jamais avant validation
        self.open_file("README.md")
        edited = self.js("return document.querySelector('#content').value") + "\nLigne ajoutee par E17a.\n"
        self.set_value("#content", edited)
        self.validate()
        self.assertIn("dont 1 modifié(s) : README.md", self.text("#wf-validated"))
        target = os.path.join(self.write_root, "e17a-demo")
        self.set_value("#wf-destination", target)
        self.click("#wf-compare")
        self.wait("return !document.querySelector('#wf-comparison').hidden")
        self.assertIn("Nouveau dossier", self.text("#wf-summary"))
        self.assertTrue(self.js("return document.querySelector('#wf-write').disabled"))  # confirmation requise
        self.click("#wf-confirm")
        self.js("window.confirm = () => true")
        self.click("#wf-write")
        self.wait("return document.querySelectorAll('#wf-operations li').length > 0")
        self.assertIn("Écriture terminée.", self.text("#wf-report"))
        with open(os.path.join(target, "README.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), edited)
        # Modification locale, nouvelle comparaison : conflit, diff T17, decision « conserver ».
        local = edited + "Note locale.\n"
        with open(os.path.join(target, "README.md"), "w", encoding="utf-8") as handle:
            handle.write(local)
        self.click("#wf-compare")
        self.wait("return Boolean(document.querySelector('#wf-entries [data-entry=\"README.md\"][data-status=\"conflict\"]'))")
        self.click("#wf-confirm")
        self.assertTrue(self.js("return document.querySelector('#wf-write').disabled"))  # conflit sans decision
        self.click('#wf-entries [data-entry="README.md"] button')
        self.assertIn("Note locale.", self.text("#wf-diff"))
        self.click('input[name="wf-resolution"][value="keep"]')
        self.assertFalse(self.js("return document.querySelector('#wf-confirm').checked"))  # decision a reconfirmer
        self.click("#wf-confirm")
        base.FirefoxFormTests.screenshot(self, "e17a-conflict")
        self.click("#wf-write")
        self.wait("return Boolean(document.querySelector('#wf-operations [data-op=\"kept\"]'))")
        with open(os.path.join(target, "README.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), local)

    def test_any_change_makes_validation_stale(self):
        self.ready_plan()
        self.validate()
        self.open_file("README.md")
        self.set_value("#content", "Contenu remplace\n")
        self.assertTrue(self.js("return document.querySelector('#wf-compare').disabled"))
        self.assertIn("Fichier modifié", self.text("#wf-status"))
        self.validate()
        self.check('input[name="q-tech"][value="mypy"]')  # configuration modifiee
        self.assertTrue(self.js("return document.querySelector('#wf-compare').disabled"))
        self.wait("return window.forgeJourney.state.validation === 'valid'")
        self.assertTrue(self.js("return document.querySelector('#wf-compare').disabled"))

    def test_unverified_needs_confirmation_and_critical_blocks(self):
        self.ready_plan()
        self.wait("return Boolean(document.querySelector('#wf-ack'))")  # sans verification en ligne : NON VERIFIE
        self.assertTrue(self.js("return document.querySelector('#wf-validate').disabled"))
        self.click("#wf-ack")
        self.assertFalse(self.js("return document.querySelector('#wf-validate').disabled"))
        self.click('#step-list [data-step="agents"]')
        self.click('input[name="q-security"][value="hardened"]')
        self.wait("return Boolean(document.querySelector('#wf-blocking'))")
        self.assertTrue(self.js("return document.querySelector('#wf-validate').disabled"))
        self.assertFalse(self.js("return Boolean(document.querySelector('#wf-ack'))"))


for _name in ("cmd", "find", "js", "click", "wait"):
    setattr(FirefoxEditorTests, _name, getattr(base.FirefoxFormTests, _name))
for _name in ("setUp", "type_name", "check", "fill_minimal", "ready_plan"):
    setattr(FirefoxEditorTests, _name, getattr(journey.FirefoxJourneyTests, _name))


if __name__ == "__main__":
    unittest.main()
