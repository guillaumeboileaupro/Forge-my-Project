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

    def test_accessibility_references_resolve(self):
        self.assertEqual(sorted(set(self.markup.references) - self.markup.ids), [])
        for image in self.markup.images:
            self.assertIn("alt", image)

    def test_essential_light_contrasts_meet_wcag_aa(self):
        pairs = [
            ("text-primary", "surface-canvas", 4.5),
            ("text-secondary", "surface-panel", 4.5),
            ("accent-default", "surface-panel", 4.5),
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


if __name__ == "__main__":
    unittest.main()
