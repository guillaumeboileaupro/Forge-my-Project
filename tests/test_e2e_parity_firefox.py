"""Parite du parcours v2 avec l'interface actuelle (E18b) dans Firefox reel : brouillon, export/import JSON,
reinitialisation, profils, architecture manuelle, skills externes, controles en ligne, archive ZIP et
assistant de protection de branche. Memes endpoints et memes formats que ui/js/app.js ; GitHub remplace
par un faux client (aucun acces reseau), la protection de branche par une proposition fixe.

Actif avec FORGE_E2E=1, geckodriver et firefox. Chaque test part d'un navigateur sans brouillon.
"""
import json
import os
import unittest
from unittest import mock

from tests import test_e2e_firefox as base
from tests import test_e2e_journey_firefox as journey
from tests import test_e2e_acceptance_firefox as acceptance

ENABLED = base.ENABLED
DRAFT_KEY = journey.DRAFT_KEY
WEB_DRAFT = json.dumps({"format": "forge-my-project/answers", "schema_version": 1, "answers": {
    "name": "shop-web", "project_type": "web", "agents": ["claude"], "technologies": ["node", "typescript", "react", "vitest"]}})
CAPTURE_BLOBS = "window.__blobs = []; URL.createObjectURL = blob => { window.__blobs.push(blob); return 'blob:test'; };"
READ_BLOB = "arguments[0].length; window.__blobs[0].text().then(arguments[arguments.length - 1])"


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxParityTests(acceptance.Common, unittest.TestCase):
    setUpClass = classmethod(base.FirefoxFormTests.setUpClass.__func__)
    tearDownClass = classmethod(base.FirefoxFormTests.tearDownClass.__func__)
    call = classmethod(base.FirefoxFormTests.call.__func__)

    def setUp(self):
        self.cmd("POST", "/window/rect", {"width": 1366, "height": 900})
        type(self).skill_client = base.FakeGh()
        self.load()

    def text(self, css):
        return self.js("return document.querySelector(arguments[0]).textContent", css)

    def answers(self):
        return self.js("return window.forgeJourney.state.answers")

    def draft(self):
        raw = self.js("return localStorage.getItem(arguments[0])", DRAFT_KEY)
        return json.loads(raw)["answers"] if raw else None

    def reload_keeping_draft(self):
        self.cmd("POST", "/refresh", {})
        self.wait("return performance.getEntriesByName('forge-ready').length === 1")
        self.js(acceptance.ERROR_CAPTURE)

    def choose_profile(self, value):
        self.js("const s = document.querySelector('#profile-select'); s.value = arguments[0];"
                " s.dispatchEvent(new Event('change', {bubbles: true}))", value)

    def import_file(self, content):
        path = os.path.join(self.tmp, "import.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.cmd("POST", "/element/%s/value" % self.find("#answers-import"), {"text": path})

    def go_to(self, step):
        self.click('#step-list button[data-step="%s"]' % step)

    def validate(self):
        self.wait("return window.forgeJourney.state.validation === 'valid'")
        if self.js("return document.querySelector('#wf-ack') !== null && !document.querySelector('#wf-ack').checked"):
            self.click("#wf-ack")  # NON VERIFIE confirmes en connaissance de cause (statut inchange)
        self.wait("return !document.querySelector('#wf-validate').disabled")
        self.click("#wf-validate")
        self.wait("return document.querySelector('#wf-validated').textContent.includes('validé(s)')")

    # --- Brouillon et reinitialisation ----------------------------------------------------
    def test_draft_is_saved_restored_reset_and_an_incompatible_one_ignored(self):
        journey.FirefoxJourneyTests.fill_minimal(self, ("python",))
        self.wait("return (localStorage.getItem(arguments[0]) || '').includes('python')".replace("arguments[0]", repr(DRAFT_KEY)))
        self.assertIn("sauvegardées", self.text("#draft-status"))
        self.click("#next")
        self.check('input[name="q-tech"][value="pytest"]')
        self.reload_keeping_draft()  # rechargement immediat : sauvegarde a la fermeture
        self.assertIn("restaurées", self.text("#draft-status"))
        self.assertEqual(self.js("return document.querySelector('#q-name').value"), "demo-journey")
        self.assertEqual(self.answers()["technologies"], ["python", "pytest"])
        self.assertIn("python", self.answers()["versions"])  # version choisie conservee
        self.wait("return ['valid', 'invalid'].includes(window.forgeJourney.state.validation)")  # apercu recalcule
        self.js("window.confirm = () => true")
        self.click("#answers-reset")
        self.assertEqual(self.answers()["technologies"], [])
        self.assertEqual(self.answers()["name"], "")
        self.assertIsNone(self.js("return window.forgeJourney.state.plan"))
        self.assertEqual(self.js("return document.querySelectorAll('#tree [data-path]').length"), 0)
        self.assertEqual(self.active("el.id"), "step-title")
        self.js("return new Promise(r => setTimeout(r, 500))")
        self.assertIsNone(self.draft())  # aucune sauvegarde des reponses vides
        # Brouillon incompatible : ignore, signale et supprime, sans erreur JavaScript.
        journey.open_v2(self, json.dumps({"format": "forge-my-project/answers", "schema_version": 1,
                                          "answers": {"technologies": ["cobol"]}}))
        self.js(acceptance.ERROR_CAPTURE)
        self.wait("return document.querySelector('#answers-alert').textContent.includes('Brouillon précédent ignoré')")
        self.assertIsNone(self.draft())
        self.assertEqual(self.answers()["technologies"], [])
        self.assert_no_errors()

    # --- Export et import JSON ---------------------------------------------------------------
    def test_export_then_import(self):
        journey.FirefoxJourneyTests.fill_minimal(self, ("python",))
        self.click("#next")
        self.check('input[name="q-tech"][value="pytest"]')
        self.js(CAPTURE_BLOBS)
        self.click("#answers-export")
        self.wait("return window.__blobs.length === 1")
        exported = json.loads(self.cmd("POST", "/execute/async", {"script": READ_BLOB, "args": [[]]}))
        self.assertEqual(exported["format"], "forge-my-project/answers")
        self.assertEqual(exported["answers"]["technologies"], ["python", "pytest"])
        self.assertEqual(exported["answers"]["name"], "demo-journey")
        self.js("window.confirm = () => true")
        self.click("#answers-reset")
        self.import_file(json.dumps(exported))
        self.wait("return window.forgeJourney.state.answers.technologies.includes('pytest')")
        self.assertEqual(self.answers()["name"], "demo-journey")
        self.assertIn("importée", self.text("#step-notice"))
        for content, message in (("{pas du json", "pas un JSON valide"),
                                 (json.dumps({"technologies": ["python", "flask", "django"]}), "incompatible")):
            with self.subTest(message=message):
                self.import_file(content)
                self.wait("return document.querySelector('#answers-alert').textContent.includes(%s)" % json.dumps(message))
        self.assertIn("pytest", self.answers()["technologies"])  # un import refuse ne modifie rien
        self.assert_no_errors()

    # --- Profils ---------------------------------------------------------------------------------
    def test_profiles_lifecycle(self):
        self.wait("return document.querySelectorAll('#profile-select option').length > 1")
        self.assertTrue(self.js("return document.querySelector('#profile-load').disabled"))
        journey.FirefoxJourneyTests.type_name(self, "profil-demo")
        self.choose_profile("typescript-web-react")
        self.click("#profile-load")
        self.assertIn("react", self.answers()["technologies"])
        self.assertIn("node", self.answers()["versions"])
        self.assertEqual(self.answers()["name"], "profil-demo")  # le profil ne fixe pas le nom
        self.assertIn("chargé", self.text("#step-notice"))
        self.assertTrue(self.js("return document.querySelector('#profile-update').disabled"))  # profil predefini
        self.js("document.querySelector('#profile-manage').open = true")
        self.choose_profile("")
        self.js("const l = document.querySelector('#profile-label'); l.value = 'E2E perso';")
        self.click("#profile-create")
        self.wait("return document.querySelector('#profile-select').value === 'e2e-perso'")
        self.assertFalse(self.js("return document.querySelector('#profile-update').disabled"))
        self.js("document.querySelector('#profile-label').value = 'E2E perso v2'")
        self.click("#profile-update")
        self.wait("return [...document.querySelectorAll('#profile-select option')].some(o => o.textContent === 'E2E perso v2')")
        self.js("window.confirm = () => true")
        self.click("#profile-delete")
        self.wait("return ![...document.querySelectorAll('#profile-select option')].some(o => o.value === 'e2e-perso')")
        self.assertIn("supprimé", self.text("#step-notice"))
        self.assert_no_errors()

    # --- Architecture manuelle --------------------------------------------------------------
    def test_manual_architecture_and_local_suggestion(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.go_to("projet")
        self.assertFalse(self.js("return document.querySelector('#architecture-box').open"))
        self.js("document.querySelector('#architecture-box').open = true")
        self.click("#q-architecture-suggest")
        self.wait("return document.querySelector('#q-architecture').value.startsWith('- ')")
        suggested = self.js("return document.querySelector('#q-architecture').value")
        self.assertEqual(self.js("return window.forgeJourney.config().architecture"), suggested)
        self.assertIn("la relire", self.text("#step-notice"))
        # Une saisie manuelle n'est jamais remplacee sans confirmation.
        self.js("const a = document.querySelector('#q-architecture'); a.value = 'Couche unique.';"
                " a.dispatchEvent(new Event('input', {bubbles: true}))")
        self.js("window.confirm = () => false")
        self.click("#q-architecture-suggest")
        self.assertEqual(self.js("return window.forgeJourney.config().architecture"), "Couche unique.")
        self.wait("return window.forgeJourney.state.validation === 'valid'")
        self.click("#tab-summary")
        self.assertIn("définie manuellement", self.text("#summary"))
        self.assertIn("Couche unique.", self.js("return Object.values(window.forgeJourney.state.plan.contents).join('\\n')"))
        self.assert_no_errors()

    # --- Skills externes et controles en ligne -----------------------------------------------
    def test_external_skills_search_approval_verification_and_online_check(self):
        journey.open_v2(self, WEB_DRAFT)
        self.js(acceptance.ERROR_CAPTURE)
        self.go_to("skills")
        self.click("#skills-search")
        self.wait("return document.querySelectorAll('#skills-candidates [data-skill]').length === 2")
        card = self.text('[data-skill="webapp-testing"]')
        for expected in ("Test React web apps", "anthropics/skills/skills", "a" * 40, "source reconnue", "run.py"):
            self.assertIn(expected, card)
        self.assertEqual(self.js("return document.querySelector('[data-skill=\"webapp-testing\"] a').rel"), "noopener noreferrer")
        self.assertIn("source non reconnue", self.text('[data-skill="react-helper"]'))
        self.click('[data-skill="webapp-testing"] [data-action="approve"]')
        self.click('[data-skill="react-helper"] [data-action="refuse"]')
        self.assertIn("Refusé", self.text('[data-skill="react-helper"] .decision'))
        self.assertEqual([s["name"] for s in self.js("return window.forgeJourney.config().external_skills")], ["webapp-testing"])
        # Conservation dans le brouillon, puis verification (faux GitHub).
        self.wait("return (localStorage.getItem(%r) || '').includes('sha256:')" % DRAFT_KEY)
        self.reload_keeping_draft()
        self.go_to("skills")
        self.assertIn("webapp-testing", self.text("#skills-approved"))
        self.assertIn("non vérifiée depuis le chargement", self.text("#skills-approved"))
        self.click("#skills-verify")
        self.wait("return document.querySelector('#skills-approved [data-status]').dataset.status === 'PASS'")
        # Le skill change cote GitHub : verification en echec, puis controle en ligne bloquant.
        type(self).skill_client = base.FakeClient(repos=base.modified_repos("skills/webapp-testing/SKILL.md", "change"))
        self.click("#skills-verify")
        self.wait("return document.querySelector('#skills-approved [data-status]').dataset.status === 'FAIL'")
        self.wait("return window.forgeJourney.state.validation === 'valid'")
        self.assertIn("hors ligne", self.text("#wf-online-mode"))
        self.assertTrue(self.js("return document.querySelector('#wf-online').disabled"))  # aucune option cochee
        self.click("#wf-net-skills")
        self.click("#wf-online")
        self.wait("return window.forgeJourney.state.validation === 'invalid'")
        self.assertIn("modifie depuis son approbation", self.text("#diagnostics-panel"))
        self.assertTrue(self.js("return document.querySelector('#wf-validate').disabled"))
        # Retrait de l'approbation : plan hors ligne recalcule, puis controle en ligne reussi.
        self.click('#skills-approved button')
        self.assertFalse(self.js("return document.querySelector('#skills-empty').hidden"))
        self.wait("return window.forgeJourney.state.validation === 'valid' && window.forgeJourney.state.online === null")
        self.click("#wf-online")
        self.wait("return window.forgeJourney.state.online !== null && window.forgeJourney.state.validation === 'valid'")
        self.assertIn("vérifié en ligne (skills)", self.text("#wf-online-mode"))
        self.validate()
        # Toute modification ramene le plan hors ligne : la verification ne vaut que pour la configuration verifiee.
        self.go_to("projet")
        journey.FirefoxJourneyTests.type_name(self, "shop-web-2")
        self.wait("return window.forgeJourney.state.validation === 'valid'")
        self.assertIsNone(self.js("return window.forgeJourney.state.online"))
        self.assert_no_errors()

    # --- Archive ZIP ---------------------------------------------------------------------------
    def test_archive_after_validation(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.assertTrue(self.js("return document.querySelector('#wf-archive').disabled"))  # jamais avant validation
        self.assertIn("hors ligne", self.text("#wf-online-mode"))
        self.validate()
        self.assertFalse(self.js("return document.querySelector('#wf-archive').disabled"))
        self.js(CAPTURE_BLOBS + " window.__downloads = [];"
                " HTMLAnchorElement.prototype.click = function () { window.__downloads.push(this.download); };")
        self.click("#wf-archive")
        self.wait("return window.__blobs.length === 1")
        self.assertEqual(self.js("return window.__downloads"), ["demo-journey.zip"])
        self.assertEqual(self.js("return window.__blobs[0].type"), "application/zip")
        self.assertGreater(self.js("return window.__blobs[0].size"), 1000)
        self.assertIn("demo-journey.zip", self.text("#wf-status"))
        # Edition apres validation : archive refusee tant que les contenus ne sont pas revalides.
        self.click('#tree [data-path="README.md"]')
        self.js("const area = document.querySelector('#content'); area.value += '\\nAjout.';"
                " area.dispatchEvent(new Event('input', {bubbles: true}));")
        self.assertTrue(self.js("return document.querySelector('#wf-archive').disabled"))
        self.assert_no_errors()

    # --- Protection de branche -------------------------------------------------------------------
    def test_branch_protection_command_is_prepared_never_applied(self):
        proposal = {"repository": "owner/project", "branch": "main", "head_sha": "a" * 40,
                    "available_checks": ["python"], "required_checks": ["python"],
                    "permissions": {"admin": True, "maintain": True, "push": True},
                    "required_permission": "Administration: write", "can_apply": True, "protection_verified": True,
                    "protection_active": False, "warnings": ["Controle lint non propose."],
                    "command": "gh api --method PUT repos/owner/project/branches/main/protection --input -",
                    "manual_only": True}
        with mock.patch("forge.web.prepare_branch_protection", return_value=proposal) as prepared:
            self.js("document.querySelector('#protection-box').open = true")
            self.js("document.querySelector('#gh-repository').value = 'owner/project'")
            self.click("#gh-prepare")
            self.wait("return !document.querySelector('#gh-preview').hidden")
        prepared.assert_called_once_with("owner/project", "main")
        summary = self.text("#gh-summary")
        for expected in ("owner/project", "a" * 40, "Permission observée", "Protection actuelle : non observée",
                         "python", "Controle lint non propose.", "Aucune modification distante"):
            self.assertIn(expected, summary)
        self.assertEqual(self.js("return document.querySelector('#gh-command').value"), proposal["command"])
        self.assertTrue(self.js("return document.querySelector('#gh-command').readOnly"))
        self.js("window.__copied = []; navigator.clipboard.writeText = text => { window.__copied.push(text); return Promise.resolve(); };")
        self.click("#gh-copy")
        self.wait("return window.__copied.length === 1")
        self.assertIn("copiée", self.text("#gh-status"))
        # Refus du serveur (CLI absente) : message, aucune commande affichee.
        with mock.patch("forge.web.prepare_branch_protection", side_effect=ValueError("GitHub CLI absente")):
            self.click("#gh-prepare")
            self.wait("return document.querySelector('#gh-status').textContent.includes('GitHub CLI absente')")
        self.assertTrue(self.js("return document.querySelector('#gh-preview').hidden"))
        self.assert_no_errors()


for _name in ("cmd", "find", "js", "click", "wait"):
    setattr(FirefoxParityTests, _name, getattr(base.FirefoxFormTests, _name))
for _name in ("type_name", "check", "fill_minimal"):
    setattr(FirefoxParityTests, _name, getattr(journey.FirefoxJourneyTests, _name))
del _name

if __name__ == "__main__":
    unittest.main()
