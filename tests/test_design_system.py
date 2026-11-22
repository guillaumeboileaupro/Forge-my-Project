"""Contrats statiques des artefacts E14, sans dépendance tierce."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "design-system"


def rgb(hex_color):
    value = hex_color.removeprefix("#")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def luminance(hex_color):
    channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                for value in rgb(hex_color)]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class MarkupInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.references = []
        self.screens = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])
        for name in ("for", "aria-labelledby", "aria-describedby"):
            if values.get(name):
                self.references.extend(values[name].split())
        if values.get("data-screen"):
            self.screens.append(values["data-screen"])
        if tag == "img":
            self.images.append(values)


class DesignSystemTests(unittest.TestCase):
    def setUp(self):
        self.tokens = (DESIGN / "tokens.css").read_text(encoding="utf-8")
        self.html_path = DESIGN / "mockups" / "index.html"
        self.markup = MarkupInspector()
        self.markup.feed(self.html_path.read_text(encoding="utf-8"))

    def token(self, name, dark=False):
        source = self.tokens.split('[data-theme="dark"]', 1)[1] if dark else self.tokens.split('[data-theme="dark"]', 1)[0]
        match = re.search(rf"--{re.escape(name)}:\s*(#[0-9a-f]{{6}})", source)
        self.assertIsNotNone(match, name)
        return match.group(1)

    def test_brand_colors_are_exactly_the_svg_colors(self):
        svg = (ROOT / "assets" / "logo.svg").read_text(encoding="utf-8").lower()
        for token in ("brand-paper", "brand-ink", "brand-copper"):
            self.assertIn(self.token(token), svg)

    def test_required_mockups_are_present_once(self):
        self.assertEqual(self.markup.screens, [
            "welcome", "questionnaire", "technologies", "explorer", "editor", "diagnostics"
        ])
        html = self.html_path.read_text(encoding="utf-8")
        self.assertNotIn('role="tab"', html)
        self.assertNotIn('role="tablist"', html)

    def test_hidden_screens_stay_hidden_at_every_breakpoint(self):
        components = (DESIGN / "components.css").read_text(encoding="utf-8")
        responsive = (DESIGN / "mockups" / "mockups.css").read_text(encoding="utf-8")
        self.assertIn("[hidden] { display: none !important; }", components)
        self.assertNotRegex(responsive, r"\.screen\s*\{[^}]*display\s*:")

    def test_accessibility_references_resolve(self):
        self.assertEqual(sorted(set(self.markup.references) - self.markup.ids), [])
        for image in self.markup.images:
            self.assertIn("alt", image)

    def test_essential_light_contrasts_meet_wcag_aa(self):
        pairs = [
            ("text-primary", "surface-canvas", 4.5),
            ("text-secondary", "surface-panel", 4.5),
            ("accent-default", "surface-panel", 4.5),
            ("accent-default", "accent-soft", 4.5),
            ("focus-ring", "surface-panel", 3.0),
            ("status-pass", "surface-panel", 4.5),
            ("status-warn", "surface-panel", 4.5),
            ("status-fail", "surface-panel", 4.5),
        ]
        for foreground, background, minimum in pairs:
            with self.subTest(foreground=foreground):
                self.assertGreaterEqual(contrast(self.token(foreground), self.token(background)), minimum)

    def test_essential_dark_contrasts_meet_wcag_aa(self):
        pairs = [
            ("text-primary", "surface-canvas", 4.5),
            ("text-secondary", "surface-panel", 4.5),
            ("accent-default", "surface-panel", 4.5),
            ("accent-default", "accent-soft", 4.5),
            ("focus-ring", "surface-panel", 3.0),
            ("status-pass", "surface-panel", 4.5),
            ("status-warn", "surface-panel", 4.5),
            ("status-fail", "surface-panel", 4.5),
        ]
        for foreground, background, minimum in pairs:
            with self.subTest(foreground=foreground):
                self.assertGreaterEqual(contrast(self.token(foreground, dark=True), self.token(background, dark=True)), minimum)

    def test_no_remote_assets_or_forbidden_ai_motifs(self):
        visual_files = [DESIGN / "tokens.css", DESIGN / "components.css",
                        *sorted((DESIGN / "mockups").glob("*.*"))]
        sources = "\n".join(path.read_text(encoding="utf-8") for path in visual_files)
        self.assertNotRegex(sources, r'https?://')
        self.assertNotRegex(sources.lower(), r"cerveau|brain|néon|neon|sparkle")



class DesignSystemCompletionTests(unittest.TestCase):
    """Reprise E14 : cuivre fidele au logo, composants de reference, palette de commandes."""

    setUp = DesignSystemTests.setUp
    token = DesignSystemTests.token

    LIGHT_SURFACES = ("surface-canvas", "surface-panel", "surface-raised", "surface-subtle")

    def hls(self, hex_color):
        import colorsys
        return colorsys.rgb_to_hls(*rgb(hex_color))

    def test_copper_family_keeps_the_logo_hue_and_saturation(self):
        brand_h, _, brand_s = self.hls(self.token("brand-copper"))
        for dark in (False, True):
            self.assertEqual(self.token("accent-fill", dark), self.token("brand-copper"))  # remplissage = cuivre exact
            for name in ("accent-default", "accent-hover", "accent-indicator"):
                with self.subTest(name=name, dark=dark):
                    hue, _, saturation = self.hls(self.token(name, dark))
                    self.assertAlmostEqual(hue * 360, brand_h * 360, delta=2)
                    self.assertAlmostEqual(saturation, brand_s, delta=0.05)

    def test_copper_contrasts_on_every_surface(self):
        for dark in (False, True):
            surfaces = [self.token(name, dark) for name in self.LIGHT_SURFACES]
            checks = [("accent-default", 4.5), ("accent-hover", 4.5), ("focus-ring", 3.0), ("accent-indicator", 3.0)]
            for name, minimum in checks:
                for surface in surfaces:
                    with self.subTest(name=name, surface=surface, dark=dark):
                        self.assertGreaterEqual(contrast(self.token(name, dark), surface), minimum)
            self.assertGreaterEqual(contrast(self.token("on-accent", dark), self.token("accent-fill", dark)), 4.5)
            self.assertGreaterEqual(contrast(self.token("on-accent", dark), self.token("accent-fill-hover", dark)), 4.5)
            self.assertGreaterEqual(contrast(self.token("text-primary", dark), self.token("accent-soft", dark)), 4.5)

    def test_reference_page_covers_every_component(self):
        page = (DESIGN / "components.html").read_text(encoding="utf-8")
        for heading in ("Palette", "Typographie", "Boutons", "Champs", "Rail et navigation latérale", "Onglets",
                        "Panneaux modulaires et poignée", "Diagnostics", "États de contenu", "Palette de commandes"):
            self.assertIn(">%s</h2>" % heading, page)
        inspector = MarkupInspector()
        inspector.feed(page)
        self.assertEqual(sorted(set(inspector.references) - inspector.ids), [])
        for state in ('disabled', 'aria-invalid="true"', 'aria-busy="true"', 'is-hover', 'is-focus', 'aria-current'):
            self.assertIn(state, page)
        for controls in re.findall(r'aria-controls="([^"]+)"', page):
            self.assertIn('id="%s"' % controls, page)
        self.assertRegex(page, r'role="separator"[^>]*aria-valuemin="\d+"[^>]*aria-valuemax="\d+"[^>]*aria-valuenow="\d+"')
        css = (DESIGN / "components.css").read_text(encoding="utf-8")
        for selector in (".rail", ".nav-item", '[role="tab"]', ".splitter", ".command-palette", ".palette-option",
                         ".drawer", ".state", ".kbd", "accent-color"):
            self.assertIn(selector, css)

    def test_command_palette_follows_the_combobox_pattern(self):
        html = self.html_path.read_text(encoding="utf-8")
        self.assertRegex(html, r'role="dialog" aria-modal="true" aria-labelledby="palette-title"')
        self.assertRegex(html, r'role="combobox"[^>]*aria-controls="palette-list"')
        self.assertIn('id="palette-list" role="listbox"', html)
        options = re.findall(r'<li class="palette-option" role="option" id="([^"]+)"', html)
        self.assertGreaterEqual(len(options), 7)
        self.assertIn('aria-disabled="true"', html)  # commande indisponible : visible mais non executable
        self.assertIn('aria-keyshortcuts="Control+K Control+Shift+P"', html)
        script = (DESIGN / "mockups" / "mockups.js").read_text(encoding="utf-8")
        for key in ("ArrowDown", "ArrowUp", "Enter", "Escape", "aria-activedescendant", "returnFocus"):
            self.assertIn(key, script)

    def test_reference_assets_stay_local_and_scripts_parse(self):
        files = [DESIGN / "components.html", DESIGN / "reference.css", DESIGN / "components.js"]
        self.assertNotRegex("\n".join(path.read_text(encoding="utf-8") for path in files), r"https?://")
        node = __import__("shutil").which("node")
        if node:
            for script in (DESIGN / "components.js", DESIGN / "mockups" / "mockups.js"):
                done = __import__("subprocess").run([node, "--check", str(script)], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
