import io
import json
import unittest
import zipfile
from generator import validate, build, generate

CONFIG = {"name": "test-projet", "description": "Example", "language": "python", "agent": "codex", "deployment": "none", "security": "strict"}
class Tests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(CONFIG)["name"], "test-projet")
    def test_reject_name(self):
        with self.assertRaises(ValueError):
            validate(dict(CONFIG, name="../danger"))
    def test_reject_option(self):
        with self.assertRaises(ValueError):
            validate(dict(CONFIG, language="unknown"))
    def test_agent_and_skills(self):
        data = build(CONFIG)
        self.assertIn("AGENTS.md", data)
        self.assertIn(".agents/skills/package-verification/SKILL.md", data)
    def test_javascript_package_uses_es_modules(self):
        data = build(dict(CONFIG, language="typescript"))
        self.assertEqual(json.loads(data["package.json"])["type"], "module")
    def test_zip(self):
        with zipfile.ZipFile(io.BytesIO(generate(CONFIG))) as z:
            self.assertIn("test-projet/AGENTS.md", z.namelist())

if __name__ == "__main__":
    unittest.main()
