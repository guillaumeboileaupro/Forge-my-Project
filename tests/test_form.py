from html.parser import HTMLParser
from pathlib import Path
import unittest

from generator import OPTIONS


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.controls = {}
        self.labels = set()
        self.current_select = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "label" and "for" in attributes:
            self.labels.add(attributes["for"])
        if tag in {"input", "select", "textarea"} and "name" in attributes:
            self.controls[attributes["name"]] = {"attributes": attributes, "values": set()}
        if tag == "select":
            self.current_select = attributes.get("name")
        if tag == "option" and self.current_select and "value" in attributes:
            self.controls[self.current_select]["values"].add(attributes["value"])

    def handle_endtag(self, tag):
        if tag == "select":
            self.current_select = None


class FormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = FormParser()
        cls.source = Path("ui/index.html").read_text(encoding="utf-8")
        parser.feed(cls.source)
        cls.form = parser

    def test_form_fields_have_unique_matching_ids(self):
        expected = {"name", "description", "one_pr", *OPTIONS}
        self.assertEqual(set(self.form.controls), expected)
        ids = [control["attributes"].get("id") for control in self.form.controls.values()]
        self.assertNotIn(None, ids)
        self.assertEqual(len(ids), len(set(ids)))
        for name in expected - {"one_pr"}:
            self.assertIn(self.form.controls[name]["attributes"]["id"], self.form.labels)

    def test_select_values_match_server_contract(self):
        for name, allowed in OPTIONS.items():
            self.assertEqual(self.form.controls[name]["values"], allowed)

    def test_ui_uses_external_assets(self):
        self.assertIn('href="/css/app.css"', self.source)
        self.assertIn('src="/js/app.js"', self.source)
        self.assertNotIn("<style", self.source)
        self.assertNotIn("<script>", self.source)
        self.assertNotIn(" style=", self.source)


if __name__ == "__main__":
    unittest.main()
