"""Recette progressive du parcours v2 (E18a) dans Firefox reel : clavier seul, ordre et visibilite du
focus, resolutions de reference, cibles, contrastes rendus dans les deux themes, budgets de performance
mesures et absence d'erreur JavaScript. Aucune bascule : l'interface actuelle reste la reference (E18).

Actif avec FORGE_E2E=1, geckodriver et firefox. Les mesures sont ecrites sur la sortie d'erreur
(lignes `E18A-BUDGET`) pour etre relues dans les journaux CI. Captures : FORGE_E2E_SCREENSHOTS=dossier.
"""
import os
import sys
import time
import unittest
import urllib.error

from tests import test_e2e_firefox as base
from tests import test_e2e_journey_firefox as journey

ENABLED = base.ENABLED
TAB, SHIFT, ENTER, ESCAPE, CTRL, DOWN = "", "", "", "", "", ""
BUDGET_READY_MS = 1000  # premier rendu utile sur loopback (docs/UI_V2_CONTRACTS.md)
BUDGET_INTERACTION_MS = 100  # interaction locale, rendu du cadre suivant compris
BUDGET_PLAN_MS = 1500  # apercu applique apres la saisie : 350 ms de report + calcul serveur
REGIONS = [".topbar", ".steps", ".step-panel", ".preview", ".editor-panel", "#diagnostics-panel", "#workflow"]

# Erreurs JavaScript et rejets non geres, captures des le chargement suivant.
ERROR_CAPTURE = """
window.__forgeErrors = [];
window.addEventListener('error', e => window.__forgeErrors.push('error: ' + e.message));
window.addEventListener('unhandledrejection', e => window.__forgeErrors.push('rejet: ' + e.reason));
document.addEventListener('securitypolicyviolation', e => window.__forgeErrors.push('csp: ' + e.violatedDirective + ' ' + e.blockedURI));
const original = console.error;
console.error = (...args) => { window.__forgeErrors.push('console: ' + args.join(' ')); original(...args); };
"""

# Indicateur de focus visible : contour d'au moins 2 px, ou trait du rectangle pour un noeud SVG.
FOCUS_INDICATOR = """
const el = document.activeElement;
if (!el || el === document.body) return 'aucun';
const style = getComputedStyle(el);
if (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) >= 2) return 'ok';
const rect = el.querySelector && el.querySelector('rect');
if (rect && parseFloat(getComputedStyle(rect).strokeWidth) >= 2) return 'ok';
return 'invisible: ' + el.tagName + '#' + el.id + '.' + el.className;
"""

# Cibles interactives visibles plus petites que le minimum. Le diagramme SVG est exclu : chaque noeud
# de fichier a un equivalent de taille conforme dans l'arborescence (exception WCAG 2.5.8 « equivalent »).
SMALL_TARGETS = """
const minimum = arguments[0];
const seen = new Set();
const small = [];
for (const node of document.querySelectorAll('button, a[href], input, select, textarea, summary')) {
  const target = node.matches('input[type="checkbox"], input[type="radio"]') ? (node.closest('label') || node) : node;
  if (seen.has(target) || target.closest('svg')) continue;
  seen.add(target);
  const rect = target.getBoundingClientRect();
  const style = getComputedStyle(target);
  if (!rect.width || !rect.height || style.visibility === 'hidden' || rect.bottom < 0) continue;  // masque ou hors champ
  if (rect.height < minimum - 0.5 || rect.width < minimum - 0.5) {
    small.push(`${target.tagName.toLowerCase()}${target.id ? '#' + target.id : ''}.${target.className} ${Math.round(rect.width)}x${Math.round(rect.height)}`);
  }
}
return small;
"""

# Contrastes du rendu reel : chaque texte visible contre son fond effectif (fonds semi-transparents composes).
CONTRAST = """
function parse(value) {
  const m = /rgba?\\(([^)]+)\\)/.exec(value || '');
  if (!m) return null;
  const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number);
  return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
}
function over(top, bottom) {
  const a = top[3];
  return [0, 1, 2].map(i => top[i] * a + bottom[i] * (1 - a)).concat(1);
}
function background(node) {
  const layers = [];
  for (let n = node; n && n.nodeType === 1; n = n.parentElement) {
    const color = parse(getComputedStyle(n).backgroundColor);
    if (color && color[3] > 0) { layers.push(color); if (color[3] === 1) break; }
  }
  let result = [255, 255, 255, 1];
  for (const layer of layers.reverse()) result = over(layer, result);
  return result;
}
function luminance(c) {
  const [r, g, b] = c.slice(0, 3).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function ratio(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}
const failures = [];
let checked = 0;
for (const el of document.querySelectorAll('body *')) {
  const text = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  if (!text || ['SCRIPT', 'STYLE', 'TITLE', 'TEXTAREA', 'OPTION'].includes(el.tagName)) continue;
  if (el.closest(':disabled, [hidden], .skip-link')) continue;  // composants inactifs exemptes (WCAG 1.4.3)
  const rect = el.getBoundingClientRect();
  const style = getComputedStyle(el);
  if (!rect.width || !rect.height || style.visibility === 'hidden') continue;
  let fg;
  let bg;
  if (el instanceof SVGElement) {
    fg = parse(style.fill);
    const box = el.parentNode.querySelector('rect');
    bg = box ? over(parse(getComputedStyle(box).fill), background(el.closest('div'))) : background(el.closest('div'));
  } else {
    bg = background(el);
    fg = parse(style.color);
  }
  if (!fg || fg[3] === 0) continue;
  fg = over(fg, bg);
  const size = parseFloat(style.fontSize);
  const large = size >= 24 || (size >= 18.66 && Number(style.fontWeight) >= 700);
  const value = ratio(fg, bg);
  checked += 1;
  if (value < (large ? 3 : 4.5) - 0.01) {
    failures.push(`${el.tagName.toLowerCase()}.${typeof el.className === 'string' ? el.className : ''} « ${el.textContent.trim().slice(0, 30)} » ${value.toFixed(2)}`);
  }
}
return {checked, failures};
"""

LAYOUT = """
const top = s => document.querySelector(s).getBoundingClientRect();
const [steps, panel, preview] = ['.steps', '.step-panel', '.preview'].map(top);
return {scroll: document.documentElement.scrollWidth - window.innerWidth, width: window.innerWidth,
        row: Math.abs(steps.top - panel.top) < 2 && Math.abs(panel.top - preview.top) < 2,
        twoColumns: Math.abs(steps.top - panel.top) < 2 && preview.top > panel.top,
        stacked: panel.top > steps.top && preview.top > panel.top,
        editor: document.querySelector('#editor .editor-body').getBoundingClientRect().width};
"""


def report(name, value):
    sys.stderr.write("E18A-BUDGET %s=%.1f ms\n" % (name, value))


class Common:
    """Aides partagees (session principale et session telephone)."""

    def keys(self, *sequence):
        actions = []
        for key in sequence:
            chord = key if isinstance(key, tuple) else (key,)
            actions += [{"type": "keyDown", "value": k} for k in chord]
            actions += [{"type": "keyUp", "value": k} for k in reversed(chord)]
        self.cmd("POST", "/actions", {"actions": [{"type": "key", "id": "clavier", "actions": actions}]})

    def type_text(self, text):
        self.keys(*text)

    def active(self, script):
        return self.js("const el = document.activeElement; return " + script)

    def load(self):
        self.cmd("POST", "/url", {"url": self.base + "/v2/parcours"})
        self.wait("return performance.getEntriesByName('forge-ready').length === 1")
        self.js(ERROR_CAPTURE)

    def assert_no_errors(self):
        self.assertEqual(self.js("return window.__forgeErrors || []"), [])
        # Une ressource bloquee par la CSP avant la capture ne leve aucune erreur : chaque image doit etre chargee.
        self.assertEqual(self.js("return [...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src)"), [])

    def capture(self, name):
        if os.environ.get("FORGE_E2E_SCREENSHOTS"):
            base.FirefoxFormTests.screenshot(self, name)

    def capture_states(self, prefix):
        """Questionnaire, apercu, atelier : une capture par zone (approbation par le proprietaire)."""
        if not os.environ.get("FORGE_E2E_SCREENSHOTS"):
            return
        for state, selector in (("questionnaire", ".topbar"), ("apercu", ".preview"), ("atelier", ".workbench")):
            self.js("document.querySelector(arguments[0]).scrollIntoView()", selector)
            self.capture("%s-%s" % (prefix, state))
        self.js("window.scrollTo(0, 0)")


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxAcceptanceTests(Common, unittest.TestCase):
    setUpClass = classmethod(base.FirefoxFormTests.setUpClass.__func__)
    tearDownClass = classmethod(base.FirefoxFormTests.tearDownClass.__func__)
    call = classmethod(base.FirefoxFormTests.call.__func__)

    def setUp(self):
        self.cmd("POST", "/window/rect", {"width": 1366, "height": 900})
        self.load()

    def tab_to(self, script, limit=150):
        """Tabulation jusqu'a l'element voulu ; chaque arret doit montrer un focus visible."""
        for _ in range(limit):
            self.keys(TAB)
            self.assertEqual(self.js(FOCUS_INDICATOR), "ok")
            if self.active(script):
                return
        self.fail("Element jamais atteint au clavier : " + script)

    # --- Clavier ---------------------------------------------------------------------
    def test_whole_journey_with_the_keyboard_only(self):
        """Questionnaire, apercu, editeur et ecriture sur disque sans souris ni script de saisie."""
        self.keys(TAB)
        self.assertTrue(self.active("el.classList.contains('skip-link')"))
        self.assertEqual(self.js(FOCUS_INDICATOR), "ok")
        self.keys(ENTER)  # lien d'evitement : le focus arrive sur le questionnaire
        self.assertEqual(self.active("el.id"), "step-panel")
        self.tab_to("el.id === 'q-name'")
        self.type_text("demo-clavier")
        self.tab_to("el.name === 'q-type'")
        self.keys(" ")
        for _ in range(10):
            if self.js("const c = document.querySelector('input[name=\"q-type\"]:checked'); return c && c.value === 'cli'"):
                break
            self.keys(DOWN)
        self.tab_to("el.id === 'next'")
        self.keys(ENTER)
        self.assertEqual(self.active("el.id"), "step-title")  # focus deplace sur action explicite
        self.tab_to("el.name === 'q-tech' && el.value === 'python'")
        self.keys(" ")
        self.tab_to("el.id === 'next'")
        self.keys(ENTER)
        for tool in ("pytest", "ruff"):
            self.tab_to("el.name === 'q-tech' && el.value === '%s'" % tool)
            self.keys(" ")
        self.tab_to("el.id === 'next'")
        self.keys(ENTER)  # versions (preferee deja choisie)
        self.tab_to("el.id === 'next'")
        self.keys(ENTER)  # agents
        self.tab_to("el.name === 'q-agent' && el.value === 'claude'")
        self.keys(" ")
        self.wait("return window.forgeJourney.state.validation === 'valid'")
        self.tab_to("el.dataset.path === 'pyproject.toml' && el.tagName === 'BUTTON'")
        self.keys(ENTER)
        self.assertEqual(self.js("return window.forgeJourney.editor.path()"), "pyproject.toml")
        self.tab_to("el.id === 'content'")
        self.keys((CTRL, "f"))
        self.assertTrue(self.active("el.classList.contains('editor-query')"))
        self.type_text("name")
        self.assertIn("sur", self.js("return document.querySelector('#editor .editor-count').textContent"))
        self.keys(ESCAPE)
        self.assertEqual(self.active("el.id"), "content")
        if self.js("return Boolean(document.querySelector('#wf-ack'))"):
            self.tab_to("el.id === 'wf-ack'")
            self.keys(" ")
        self.tab_to("el.id === 'wf-validate'")
        self.keys(ENTER)
        self.wait("return !document.querySelector('#wf-compare').disabled")
        target = os.path.join(self.write_root, "demo-clavier")
        self.tab_to("el.id === 'wf-destination'")
        self.keys((CTRL, "a"))
        self.type_text(target)
        self.tab_to("el.id === 'wf-compare'")
        self.keys(ENTER)
        self.wait("return !document.querySelector('#wf-comparison').hidden")
        self.tab_to("el.id === 'wf-confirm'")
        self.keys(" ")
        self.js("window.confirm = () => true")  # la boite native n'est pas pilotable au clavier via WebDriver
        self.tab_to("el.id === 'wf-write'")
        self.keys(ENTER)
        self.wait("return document.querySelectorAll('#wf-operations li').length > 0")
        self.assertTrue(os.path.isfile(os.path.join(target, "pyproject.toml")))
        self.assert_no_errors()

    def test_tab_order_follows_the_regions_and_never_traps(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.select_file("README.md")
        self.assertEqual(self.js("return [...document.querySelectorAll('[tabindex]')].filter(n => n.tabIndex > 0).length"), 0)
        self.js("window.scrollTo(0, 0); document.querySelector('.skip-link').focus()")  # point de depart du tour
        order = []
        for _ in range(400):
            self.keys(TAB)
            if order and self.active("el === document.body"):
                # Fin du document atteinte (le focus part vers le navigateur) : aucun piege en avant,
                # et Maj+Tab revient dans la derniere zone du document.
                self.keys((SHIFT, TAB))
                self.assertTrue(self.active("el !== document.body && Boolean(el.closest('#workflow'))"))
                break
            self.assertEqual(self.js(FOCUS_INDICATOR), "ok")
            order.append(self.js("const el = document.activeElement; return arguments[0].findIndex(s => el.closest(s))", REGIONS))
        else:
            self.fail("Le focus ne revient jamais au debut (piege possible)")
        visited = [region for region in order if region >= 0]
        self.assertEqual(visited, sorted(visited), "ordre de tabulation hors ordre des zones")
        self.assertEqual(sorted(set(visited)), list(range(len(REGIONS))))
        self.assert_no_errors()

    def select_file(self, path):
        self.click('#tree [data-path="%s"]' % path)
        self.wait("return window.forgeJourney.editor.path() === %r" % path)

    # --- Resolutions, cibles, themes ---------------------------------------------------
    def test_reference_resolutions_and_breakpoints(self):
        journey.FirefoxJourneyTests.ready_plan(self)
        self.select_file("pyproject.toml")
        # Tailles de reference E14 et chaque rupture juste avant/apres (360 : classe telephone ci-dessous).
        sizes = ((767, 1024, "stacked", 44), (768, 1024, "twoColumns", 36), (1199, 800, "twoColumns", 36),
                 (1200, 800, "row", 36), (1280, 800, "row", 36), (1440, 900, "row", 36), (1920, 1080, "row", 36))
        try:
            for width, height, layout, minimum in sizes:
                with self.subTest(width=width):
                    self.cmd("POST", "/window/rect", {"width": width, "height": height})
                    self.wait("return window.innerWidth <= %d" % width)
                    state = self.js(LAYOUT)
                    self.assertLessEqual(state["scroll"], 0)
                    self.assertTrue(state[layout], (layout, state))
                    self.assertGreater(state["editor"], 250)
                    self.assertEqual(self.js(SMALL_TARGETS, minimum), [])
                    for theme in ("light", "dark"):
                        self.js("document.documentElement.dataset.theme = arguments[0]", theme)
                        if width in (768, 1280, 1440, 1920):
                            self.capture_states("e18a-%d-%s" % (width, theme))
                    self.js("document.documentElement.dataset.theme = 'light'")
        finally:
            self.cmd("POST", "/window/rect", {"width": 1366, "height": 900})
        self.assert_no_errors()

    def test_rendered_text_contrast_in_both_themes(self):
        """Tous les textes visibles (etats courants : diagnostics, editeur colore, recherche, ecriture)."""
        journey.FirefoxJourneyTests.ready_plan(self)
        self.select_file("pyproject.toml")
        self.click("#editor .editor-search-toggle")
        self.js("const q = document.querySelector('#editor .editor-query'); q.value = 'name';"
                "q.dispatchEvent(new Event('input', {bubbles: true}))")
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                self.js("document.documentElement.dataset.theme = arguments[0]", theme)
                result = self.js(CONTRAST)
                self.assertGreater(result["checked"], 100)
                self.assertEqual(result["failures"], [])
        self.js("document.documentElement.dataset.theme = 'light'")
        self.assert_no_errors()

    # --- Performance -------------------------------------------------------------------
    def measure(self, script):
        """Duree (ms) d'une action synchrone jusqu'au cadre suivant rendu."""
        return self.cmd("POST", "/execute/async", {"args": [], "script": """
            const done = arguments[arguments.length - 1];
            const t0 = performance.now();
            (function () { %s })();
            requestAnimationFrame(() => setTimeout(() => done(performance.now() - t0), 0));""" % script})

    def test_performance_budgets(self):
        ready = self.js("return performance.getEntriesByName('forge-ready')[0].startTime")
        report("premier-rendu-utile", ready)
        self.assertLess(ready, BUDGET_READY_MS)
        journey.FirefoxJourneyTests.ready_plan(self)
        before = self.js("return performance.getEntriesByName('forge-plan').length")
        timings = {"case-technologie": "document.querySelector('input[name=\"q-tech\"][value=\"mypy\"]').click()"}
        plan_start = self.js("return performance.now()")
        timings_ms = {"case-technologie": self.measure(timings["case-technologie"])}
        self.wait("return performance.getEntriesByName('forge-plan').length > %d" % before)
        plan = self.js("return performance.getEntriesByName('forge-plan').slice(-1)[0].startTime") - plan_start
        report("apercu-applique-apres-saisie", plan)
        self.assertLess(plan, BUDGET_PLAN_MS)
        # Grand fichier (2 000 lignes) : saisie, recherche et remplacement restent sous le budget.
        big = "\n".join('key_%d = "valeur %d" # commentaire' % (i, i) for i in range(2000))
        self.select_file("pyproject.toml")
        self.js("const a = document.querySelector('#content'); a.value = arguments[0];"
                "a.dispatchEvent(new Event('input', {bubbles: true}))", big)
        actions = {
            "etape-suivante": "document.querySelector('#next').click()",
            "selection-arbre": "document.querySelector('#tree [data-path=\"README.md\"]').click()",
            "retour-grand-fichier": "document.querySelector('#tree [data-path=\"pyproject.toml\"]').click()",
            "frappe-grand-fichier": "const a = document.querySelector('#content'); a.value += 'x';"
                                    "a.dispatchEvent(new Event('input', {bubbles: true}))",
            "recherche-grand-fichier": "document.querySelector('#editor .editor-search-toggle').click();"
                                       "const q = document.querySelector('#editor .editor-query'); q.value = 'valeur';"
                                       "q.dispatchEvent(new Event('input', {bubbles: true}))",
            "tout-remplacer-grand-fichier": "document.querySelector('#editor .editor-replacement').value = 'v';"
                                            "document.querySelector('#editor .editor-replace-all').click()",
            "filtre-diagnostics": "document.querySelector('#diagnostics-panel .diag-toggle').click()",
        }
        repeated = {  # actions rejouables : mediane de 3 mesures (meme seuil, bruit de charge amorti)
            "retour-grand-fichier": "document.querySelector('#tree [data-path=\"README.md\"]').click()",
            "frappe-grand-fichier": None,
        }
        for name, script in actions.items():
            if name in repeated:
                samples = []
                for _ in range(3):
                    if repeated[name]:
                        self.js(repeated[name])
                    samples.append(self.measure(script))
                timings_ms[name] = sorted(samples)[1]
            else:
                timings_ms[name] = self.measure(script)
        for name, value in timings_ms.items():
            report(name, value)
            with self.subTest(action=name):
                self.assertLess(value, BUDGET_INTERACTION_MS)
        self.assertEqual(self.js("return document.querySelector('#content').value.split('\\n').length"), 2000)  # rien de perdu
        self.assertEqual(self.js("return [...performance.getEntriesByType('resource')].filter("
                                 "r => !r.name.startsWith(location.origin)).length"), 0)  # aucune ressource distante
        self.assert_no_errors()


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxPhoneDarkTests(Common, unittest.TestCase):
    """360 px en theme sombre systeme : zoom de 139 % d'une fenetre de 500 px (largeur minimale de Firefox)."""
    call = classmethod(base.FirefoxFormTests.call.__func__)
    tearDownClass = classmethod(base.FirefoxFormTests.tearDownClass.__func__)

    @classmethod
    def setUpClass(cls):
        base.FirefoxFormTests.setUpClass.__func__(cls)
        cls.call("DELETE", "/session/" + cls.session)
        # Acces au chrome reserve a cette session de test (zoom du navigateur) ; theme sombre du systeme simule.
        caps = {"capabilities": {"alwaysMatch": {"browserName": "firefox", "moz:firefoxOptions": {
            "args": ["-headless", "-remote-allow-system-access"],
            "prefs": {"ui.systemUsesDarkTheme": 1, "layout.css.prefers-color-scheme.content-override": 0}}}}}
        for attempt in range(2):  # la session precedente peut encore se fermer
            try:
                cls.session = cls.call("POST", "/session", caps)["sessionId"]
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:500]
                if attempt:
                    try:  # arrete geckodriver et le serveur ; la session supprimee ne peut plus l'etre
                        cls.tearDownClass()
                    except urllib.error.URLError:
                        pass
                    raise AssertionError("Session Firefox (zoom, theme sombre) refusee : " + detail) from exc
                time.sleep(2)

    def setUp(self):
        self.load()
        self.cmd("POST", "/moz/context", {"context": "chrome"})
        try:
            self.js("ZoomManager.setZoomForBrowser(gBrowser.selectedBrowser, 500 / 360)")
        finally:
            self.cmd("POST", "/moz/context", {"context": "content"})
        for width in range(500, 512):
            self.cmd("POST", "/window/rect", {"width": width, "height": 1112})
            if self.js("return window.innerWidth") >= 360:
                break
        self.assertEqual(self.js("return window.innerWidth"), 360)

    def test_phone_width_in_system_dark_theme(self):
        self.assertEqual(self.js("return document.documentElement.dataset.theme"), "dark")  # suit le systeme
        journey.FirefoxJourneyTests.ready_plan(self)
        self.click('#tree [data-path="README.md"]')
        state = self.js(LAYOUT)
        self.assertLessEqual(state["scroll"], 0)
        self.assertTrue(state["stacked"], state)
        self.assertGreater(state["editor"], 250)
        self.assertEqual(self.js("return getComputedStyle(document.querySelector('.step-actions')).position"), "sticky")
        self.assertEqual(self.js(SMALL_TARGETS, 44), [])
        # Barres de defilement aux couleurs du theme (sinon claires en sombre dans Firefox sans theme systeme).
        self.assertNotEqual(self.js("return getComputedStyle(document.querySelector('.tree')).scrollbarColor"), "auto")
        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                self.js("document.documentElement.dataset.theme = arguments[0]", theme)
                result = self.js(CONTRAST)
                self.assertEqual(result["failures"], [])
                self.capture_states("e18a-360-%s" % theme)
        self.assert_no_errors()


for _cls in (FirefoxAcceptanceTests, FirefoxPhoneDarkTests):
    for _name in ("cmd", "find", "js", "click", "wait"):
        setattr(_cls, _name, getattr(base.FirefoxFormTests, _name))
    for _name in ("type_name", "check", "fill_minimal"):
        setattr(_cls, _name, getattr(journey.FirefoxJourneyTests, _name))


if __name__ == "__main__":
    unittest.main()
