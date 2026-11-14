import io
import json
import itertools
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
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

    def test_reject_unknown_field(self):
        with self.assertRaisesRegex(ValueError, "Champ inconnu"):
            validate(dict(CONFIG, unexpected="value"))

    def test_reject_invalid_boolean(self):
        with self.assertRaisesRegex(ValueError, "one_pr"):
            validate(dict(CONFIG, one_pr="false"))

    def test_normalize_description_whitespace(self):
        config = validate(dict(CONFIG, description="  line one\r\n\tline two  "))
        self.assertEqual(config["description"], "line one line two")

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
            self.assertEqual(len(z.namelist()), len(set(z.namelist())))
            for name in z.namelist():
                path = PurePosixPath(name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertEqual(path.parts[0], CONFIG["name"])

    def test_all_supported_options_generate_safe_archives(self):
        options = {
            "language": ("python", "typescript"),
            "agent": ("codex", "claude", "copilot", "agnostic"),
            "deployment": ("none", "docker", "s3ns", "outscale"),
            "security": ("strict", "hardened"),
        }
        for values in itertools.product(*options.values()):
            config = dict(CONFIG, **dict(zip(options, values)))
            with self.subTest(**config), zipfile.ZipFile(io.BytesIO(generate(config))) as archive:
                self.assertTrue(archive.testzip() is None)
                self.assertTrue(all(name.startswith("test-projet/") for name in archive.namelist()))

    def test_generated_python_tests_run(self):
        self._run_generated_tests(CONFIG, ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"])

    def test_generated_javascript_tests_run(self):
        self._run_generated_tests(dict(CONFIG, language="typescript"), ["npm", "test"])

    def _run_generated_tests(self, config, command):
        with tempfile.TemporaryDirectory() as directory:
            with zipfile.ZipFile(io.BytesIO(generate(config))) as archive:
                archive.extractall(directory)
            result = subprocess.run(
                command,
                cwd=Path(directory) / config["name"],
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
