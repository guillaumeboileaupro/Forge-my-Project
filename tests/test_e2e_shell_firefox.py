"""Coque UI v2 (E15) dans Firefox reel : preferences versionnees, themes, densite, panneaux masquables,
deplacables et redimensionnables, onglets ARIA, palette de commandes au clavier.

Actif avec FORGE_E2E=1, geckodriver et firefox. Chaque test part de preferences vides (cle effacee).
"""
import json
import unittest

from tests import test_e2e_firefox as base
from tests import test_e2e_journey_firefox as journey
from tests import test_e2e_acceptance_firefox as acceptance

ENABLED = base.ENABLED
TAB, ENTER, ESCAPE, CTRL = acceptance.TAB, acceptance.ENTER, acceptance.ESCAPE, acceptance.CTRL
RIGHT, LEFT, HOME, END = "", "", "", ""
KEY = "forge-my-project.ui.v2"
DRAFT_KEY = "forge-my-project.draft.v1"
PREF_FIELDS = ["activePanel", "density", "panels", "schemaVersion", "theme"]
WIDTH = "return Math.round(document.querySelector(arguments[0]).getBoundingClientRect().width)"
LEFT_OF = "return Math.round(document.querySelector(arguments[0]).getBoundingClientRect().left)"


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxShellTests(acceptance.Common, unittest.TestCase):
    setUpClass = classmethod(base.FirefoxFormTests.setUpClass.__func__)
    tearDownClass = classmethod(base.FirefoxFormTests.tearDownClass.__func__)
    call = classmethod(base.FirefoxFormTests.call.__func__)

    def setUp(self):
        self.cmd("POST", "/window/rect", {"width": 1366, "height": 900})
        self.load()
        self.js("localStorage.removeItem(arguments[0])", KEY)
        self.load()

    def tearDown(self):
        self.js("localStorage.removeItem(arguments[0])", KEY)

    def stored(self):
        text = self.js("return localStorage.getItem(arguments[0])", KEY)
        return json.loads(text) if text else None

    def store(self, value):
        self.js("localStorage.setItem(arguments[0], arguments[1])", KEY, value)
        self.load()

    def prefs(self):
        return self.js("return window.forgeShell.prefs()")

    def commands(self):
        return self.js("return window.forgeShell.commands().map(c => c.id)")

    # --- Preferences ---------------------------------------------------------------------
    def test_corrupt_or_unknown_preferences_are_ignored_without_touching_the_v1_draft(self):
        self.js("localStorage.setItem(arguments[0], 'brouillon v1 intact')", DRAFT_KEY)
        defaults = self.prefs()
        self.assertEqual(defaults["theme"], "system")
        self.assertEqual(defaults["density"], "comfortable")
        self.assertEqual(self.js("return document.documentElement.dataset.themeChoice"), "system")
        for raw in ("{pas du json", "null", "[]", json.dumps({**defaults, "schemaVersion": 2, "theme": "dark"})):
            with self.subTest(raw=raw[:20]):
                self.store(raw)
                self.assertEqual(self.prefs(), defaults)
                self.assert_no_errors()
        # Champ par champ : valeurs inconnues, mal typees ou hors bornes ignorees, le reste conserve.
        self.store(json.dumps({"schemaVersion": 1, "theme": "neon", "density": "compact", "activePanel": "absent",
                               "panels": {"navigation": {"visible": "non", "size": 99999, "side": "left"},
                                          "preview": {"visible": False, "size": "grand", "side": "left"}}}))
        prefs = self.prefs()
        self.assertEqual((prefs["theme"], prefs["density"], prefs["activePanel"]), ("system", "compact", "configuration"))
        self.assertEqual(prefs["panels"]["navigation"], {"visible": True, "size": 440, "side": "left"})
        self.assertEqual(prefs["panels"]["preview"], {"visible": False, "size": None, "side": "right"})  # cotes en conflit
        self.assertTrue(self.js("return document.querySelector('.preview').hidden"))
        self.assertEqual(self.js("return localStorage.getItem(arguments[0])", DRAFT_KEY), "brouillon v1 intact")
        self.assert_no_errors()

    def test_theme_and_density_persist_and_an_explicit_choice_overrides_the_system(self):
        self.click("#shell-theme")
        self.assertEqual(self.js("return document.documentElement.dataset.theme"), "light")
        self.click("#shell-theme")
        self.assertEqual(self.js("return document.documentElement.dataset.theme"), "dark")
        self.assertEqual(self.find("#shell-theme") and self.js("return document.querySelector('#shell-theme').textContent"),
                         "Thème : sombre")
        self.click("#shell-density")
        self.load()  # rechargement : choix conserves
        self.assertEqual(self.js("return document.documentElement.dataset.theme"), "dark")
        self.assertEqual(self.js("return document.documentElement.dataset.density"), "compact")
        self.assertEqual(sorted(self.stored()), PREF_FIELDS)  # aucune donnee projet dans les preferences
        self.assertEqual(self.js("return getComputedStyle(document.querySelector('#next')).minHeight"), "36px")
        journey.FirefoxJourneyTests.ready_plan(self)
        self.assertEqual(self.js(acceptance.SMALL_TARGETS, 36), [])  # compact : cibles jamais sous 36 px
        self.assertEqual(self.js(acceptance.CONTRAST)["failures"], [])
        self.assertNotIn("demo-journey", json.dumps(self.stored()))
        self.capture("e15-compact-sombre")
        self.assertEqual(self.js("return window.forgeShell.run('theme.system')"), True)
        self.assertEqual(self.stored()["theme"], "system")
        self.assert_no_errors()

    # --- Panneaux ------------------------------------------------------------------------
    def test_panels_hide_restore_move_and_reset(self):
        self.js("document.querySelector('[data-hide=\"navigation\"]').focus()")
        self.keys(ENTER)
        self.assertTrue(self.js("return document.querySelector('.steps').hidden"))
        self.assertTrue(self.js("return document.querySelector('[data-splitter=\"navigation\"]').hidden"))
        # Focus logique : la commande du rail qui restaure le panneau.
        self.assertTrue(self.active("el.matches('.rail [data-toggle=\"navigation\"]')"))
        self.assertEqual(self.active("el.getAttribute('aria-pressed')"), "false")
        self.load()
        self.assertTrue(self.js("return document.querySelector('.steps').hidden"))
        self.click('.rail [data-toggle="navigation"]')
        self.assertFalse(self.js("return document.querySelector('.steps').hidden"))
        # Deplacement : l'ordre du DOM suit l'ordre visuel (lecture et tabulation coherentes).
        self.click('[data-move="navigation"]')
        order = self.js("return [...document.querySelector('#layout').children].map(n => n.dataset.panel || n.dataset.splitter && 'sep:' + n.dataset.splitter || n.className)")
        self.assertEqual(order[:5], ["preview", "sep:preview", "configuration", "sep:navigation", "navigation"])
        self.assertLess(self.js(LEFT_OF, ".preview"), self.js(LEFT_OF, ".step-panel"))
        self.assertLess(self.js(LEFT_OF, ".step-panel"), self.js(LEFT_OF, ".steps"))
        self.assertTrue(self.active("el.matches('[data-move=\"navigation\"]')"))  # focus conserve apres deplacement
        self.assertEqual(self.active("el.getAttribute('aria-label')"), "Déplacer le panneau Étapes à gauche")
        self.load()
        self.assertEqual(self.prefs()["panels"]["navigation"]["side"], "right")
        self.assertIn("layout.reset", self.commands())
        self.js("window.forgeShell.run('layout.reset')")
        self.assertLess(self.js(LEFT_OF, ".steps"), self.js(LEFT_OF, ".step-panel"))
        self.assertNotIn("layout.reset", self.commands())  # commande indisponible : absente de la palette
        self.assert_no_errors()

    def test_splitters_resize_with_keyboard_and_pointer_within_bounds(self):
        separator = '[data-splitter="navigation"]'
        attributes = self.js("const s = document.querySelector(arguments[0]); return ['role', 'aria-orientation',"
                             " 'aria-valuemin', 'aria-valuemax', 'aria-controls'].map(a => s.getAttribute(a))", separator)
        self.assertEqual(attributes, ["separator", "vertical", "200", "440", "steps-panel"])
        start = self.js(WIDTH, ".steps")
        self.js("document.querySelector(arguments[0]).focus()", separator)
        self.assertEqual(self.js(acceptance.FOCUS_INDICATOR), "ok")
        self.keys(RIGHT)
        self.assertEqual(self.js(WIDTH, ".steps"), start + 16)
        self.keys(END)
        self.assertEqual(self.js(WIDTH, ".steps"), 440)
        self.cmd("POST", "/window/rect", {"width": 1000, "height": 900})  # 40 % de la fenetre < 440
        self.wait("return document.querySelector('%s').getAttribute('aria-valuemax')"
                  " === String(Math.floor(window.innerWidth * 0.4))" % separator)
        self.assertEqual(self.js(WIDTH, ".steps"), self.js("return Math.floor(window.innerWidth * 0.4)"))
        self.cmd("POST", "/window/rect", {"width": 1366, "height": 900})
        self.keys(HOME)
        self.assertEqual(self.js(WIDTH, ".steps"), 200)
        self.assertEqual(self.js("return document.querySelector(arguments[0]).getAttribute('aria-valuenow')", separator), "200")
        self.keys(LEFT)
        self.assertEqual(self.js(WIDTH, ".steps"), 200)  # borne minimale
        # Panneau de droite : la fleche gauche l'elargit (vers le contenu central = plus etroit).
        self.js("document.querySelector('[data-splitter=\"preview\"]').focus()")
        self.keys(HOME)
        before = self.js(WIDTH, ".preview")
        self.assertEqual(before, 280)
        self.keys(LEFT)
        self.assertEqual(self.js(WIDTH, ".preview"), before + 16)
        # Pointeur : glisser le separateur de 60 px.
        box = self.js("const r = document.querySelector(arguments[0]).getBoundingClientRect();"
                      " return [Math.round(r.left + r.width / 2), Math.round(r.top + 40)]", separator)
        self.cmd("POST", "/actions", {"actions": [{"type": "pointer", "id": "souris", "parameters": {"pointerType": "mouse"},
                                                   "actions": [{"type": "pointerMove", "x": box[0], "y": box[1]},
                                                               {"type": "pointerDown", "button": 0},
                                                               {"type": "pointerMove", "x": box[0] + 60, "y": box[1], "duration": 100},
                                                               {"type": "pointerUp", "button": 0}]}]})
        self.cmd("DELETE", "/actions")
        self.assertAlmostEqual(self.js(WIDTH, ".steps"), 260, delta=2)
        self.load()
        self.assertAlmostEqual(self.js(WIDTH, ".steps"), 260, delta=2)  # taille conservee
        self.assertEqual(self.prefs()["panels"]["preview"]["size"], before + 16)
        self.assert_no_errors()

    def test_narrow_widths_stack_panels_without_splitters_or_horizontal_scroll(self):
        self.js("window.forgeShell.run('layout.swap')")
        for width in (767, 1024, 1200):
            with self.subTest(width=width):
                self.cmd("POST", "/window/rect", {"width": width, "height": 900})
                visible = self.js("return [...document.querySelectorAll('.splitter')].filter(s => s.getBoundingClientRect().width > 0).length")
                self.assertEqual(visible, {767: 0, 1024: 1, 1200: 2}[width])
                self.assertLessEqual(self.js("return document.documentElement.scrollWidth - window.innerWidth"), 0)
        self.assert_no_errors()

    # --- Onglets -------------------------------------------------------------------------
    def test_preview_tabs_follow_the_aria_model_with_explicit_activation(self):
        selected = "return [...document.querySelectorAll('#preview-tabs [role=tab]')].map(t => [t.dataset.tab, t.getAttribute('aria-selected'), t.tabIndex])"
        self.assertEqual(self.js(selected), [["plan", "true", 0], ["summary", "false", -1]])
        self.js("document.querySelector('#tab-plan').focus()")
        self.keys(RIGHT)
        self.assertEqual(self.active("el.id"), "tab-summary")
        self.assertEqual(self.js(selected)[0][1], "true")  # la fleche ne change pas l'onglet actif
        self.keys(ENTER)
        self.assertEqual(self.js(selected), [["plan", "false", -1], ["summary", "true", 0]])
        self.assertTrue(self.js("return document.querySelector('#view-plan').hidden"))
        self.keys(HOME)
        self.assertEqual(self.active("el.id"), "tab-plan")
        self.keys(END)
        self.assertEqual(self.active("el.id"), "tab-summary")
        self.keys(RIGHT)
        self.assertEqual(self.active("el.id"), "tab-plan")  # boucle
        journey.FirefoxJourneyTests.ready_plan(self)
        summary = self.js("return [...document.querySelectorAll('#summary dd')].map(d => d.textContent)")
        self.assertEqual(summary[0], "demo-journey")
        self.assertNotEqual(summary[-1], "—")  # nombre de fichiers du plan
        self.assert_no_errors()

    # --- Palette -------------------------------------------------------------------------
    def test_command_palette_with_the_keyboard(self):
        self.js("document.querySelector('#q-name').focus()")
        self.keys((CTRL, "k"))
        self.assertTrue(self.js("return document.querySelector('#palette').open"))
        self.assertEqual(self.active("el.id"), "palette-input")
        ids = self.commands()
        self.assertNotIn("journey.prev", ids)  # premiere etape : commande indisponible, non proposee
        self.assertNotIn("theme.system", ids)  # deja le theme courant
        self.assertIn("journey.next", ids)
        self.type_text("masquer apercu")  # sans accent : recherche insensible aux accents
        options = self.js("return [...document.querySelectorAll('#palette-list [role=option]')].map(o => o.textContent)")
        self.assertEqual(options, ["Masquer le panneau Aperçu"])
        self.keys(ENTER)
        self.assertFalse(self.js("return document.querySelector('#palette').open"))
        self.assertTrue(self.js("return document.querySelector('.preview').hidden"))
        self.assertEqual(self.active("el.id"), "q-name")  # focus rendu au declencheur
        # Piege du focus, navigation dans la liste, Echap.
        self.keys((CTRL, "k"))
        first = self.js("return document.querySelector('#palette-input').getAttribute('aria-activedescendant')")
        self.keys(TAB)
        self.assertEqual(self.active("el.id"), "palette-input")
        self.keys(acceptance.DOWN)
        second = self.js("return document.querySelector('#palette-input').getAttribute('aria-activedescendant')")
        self.assertNotEqual(first, second)
        self.assertEqual(self.js("return document.getElementById(arguments[0]).getAttribute('aria-selected')", second), "true")
        self.keys(ESCAPE)
        self.assertFalse(self.js("return document.querySelector('#palette').open"))
        self.assertEqual(self.active("el.id"), "q-name")
        # Bouton de la barre superieure, puis une commande qui deplace le focus vers sa zone.
        self.click("#shell-palette")
        self.type_text("aller diagnostics")
        self.keys(ENTER)
        self.assertEqual(self.active("el.id"), "diagnostics-title")
        self.keys((CTRL, "k"))
        self.type_text("aucune commande de ce nom")
        self.assertFalse(self.js("return document.querySelector('#palette-empty').hidden"))
        self.keys(ENTER)  # rien a executer
        self.keys(ESCAPE)
        # Une commande est un objet enregistre, jamais une chaine executee ; identifiants uniques.
        refused = self.js("const out = []; for (const c of [{id: 'Pas valide', run() {}}, {id: 'journey.next', run() {}},"
                          " {id: 'sans.action', run: 'alert(1)'}]) { try { window.forgeShell.register(c); out.push('accepte'); }"
                          " catch (e) { out.push('refuse'); } } return out;")
        self.assertEqual(refused, ["refuse", "refuse", "refuse"])
        self.assert_no_errors()

    def test_shell_sends_no_request_at_mount(self):
        requests = self.js("return performance.getEntriesByType('resource')"
                           ".filter(e => ['fetch', 'xmlhttprequest'].includes(e.initiatorType)).map(e => new URL(e.name).pathname)")
        # Parcours (catalogue) et atelier E17a (dossier par defaut) ; la coque n'appelle rien (test statique).
        self.assertEqual(sorted(requests), ["/api/catalog", "/api/destination/browse"])
        self.assert_no_errors()


for _name in ("cmd", "find", "js", "click", "wait"):
    setattr(FirefoxShellTests, _name, getattr(base.FirefoxFormTests, _name))
for _name in ("type_name", "check", "fill_minimal"):
    setattr(FirefoxShellTests, _name, getattr(journey.FirefoxJourneyTests, _name))


if __name__ == "__main__":
    unittest.main()
