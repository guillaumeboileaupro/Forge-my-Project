"""E10 : regles Semgrep locales et passerelle, executees avec le vrai Semgrep.

Actif si Semgrep est disponible : FORGE_SEMGREP=/chemin/semgrep (job CI security) ou `semgrep`
dans le PATH. Le code vulnerable est ecrit dans un dossier temporaire : rien de dangereux
n'est versionne. Chaque regle doit se declencher sur le code vulnerable et rester muette
sur sa variante sure ; la passerelle doit echouer des qu'une vulnerabilite est introduite.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "templates" / "security" / "semgrep.yml.tmpl"
GATE = ROOT / "templates" / "security" / "semgrep_gate.py.tmpl"
SEMGREP = os.environ.get("FORGE_SEMGREP") or shutil.which("semgrep")

VULNERABLE = {
    "app/danger.py": (
        "import marshal, os, pickle, subprocess, tempfile, requests, yaml\n"
        "def f(data, cmd, url):\n"
        "    eval(data)\n"
        "    exec(cmd)\n"
        "    subprocess.run(cmd, shell=True)\n"
        "    os.system(cmd)\n"
        "    os.popen(cmd)\n"
        "    pickle.loads(data)\n"
        "    marshal.loads(data)\n"
        "    yaml.load(data)\n"
        "    yaml.unsafe_load(data)\n"
        "    requests.get(url, verify=False)\n"
        "    tempfile.mktemp()\n"
    ),
    "web/danger.ts": (
        'import * as cp from "node:child_process";\n'
        'import https from "node:https";\n'
        "export function f(input: string, el: HTMLElement) {\n"
        "  eval(input);\n"
        "  new Function(input);\n"
        "  cp.execSync(input);\n"
        '  cp.spawn("sh", ["-c", input], { shell: true });\n'
        "  el.innerHTML = input;\n"
        "  return new https.Agent({ rejectUnauthorized: false });\n"
        "}\n"
    ),
    "web/danger.jsx": "export const C = ({ html }) => <div dangerouslySetInnerHTML={{ __html: html }} />;\n",
}
SAFE = {
    "app/safe.py": (
        "import json, subprocess, tempfile, requests, yaml\n"
        "def f(data, cmd, url):\n"
        '    eval("1 + 1")\n'
        '    subprocess.run(["ls", cmd], check=True)\n'
        "    json.loads(data)\n"
        "    yaml.safe_load(data)\n"
        "    yaml.load(data, Loader=yaml.SafeLoader)\n"
        "    requests.get(url, timeout=5)\n"
        "    tempfile.mkstemp()\n"
    ),
    "web/safe.ts": (
        'import { execFile, spawn } from "node:child_process";\n'
        "export function f(input: string, el: HTMLElement) {\n"
        '  execFile("ls", [input]);\n'
        '  spawn("ls", [input]);\n'
        "  el.textContent = input;\n"
        '  el.innerHTML = "<b>fixe</b>";\n'
        "}\n"
    ),
}
EXPECTED = {  # regle -> nombre minimal de declenchements dans VULNERABLE
    "eval-exec": 2, "subprocess-shell": 1, "os-system": 2, "unsafe-deserialization": 2, "yaml-unsafe-load": 2,
    "tls-verify-disabled": 1, "tempfile-mktemp": 1, "eval": 2, "child-process-exec": 2,
    "inner-html-assignment": 1, "tls-reject-unauthorized": 1, "react-dangerously-set-inner-html": 1,
}


@unittest.skipUnless(SEMGREP, "Semgrep requis (FORGE_SEMGREP ou PATH) : execute dans le job CI security")
class SemgrepRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="forge-semgrep-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def scan(self, files):
        for path, content in files.items():
            target = self.tmp / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        report = self.tmp.parent / (self.tmp.name + ".json")
        self.addCleanup(lambda: report.unlink(missing_ok=True))
        done = subprocess.run([SEMGREP, "scan", "--config", str(RULES), "--metrics=off", "--disable-version-check",
                               "--json", "--output", str(report), "."], cwd=self.tmp, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        return report, json.loads(report.read_text(encoding="utf-8"))

    def gate(self, report, level="ERROR"):
        return subprocess.run([sys.executable, str(GATE), str(report), level], capture_output=True, text=True)

    def test_every_rule_detects_its_vulnerable_code(self):
        _, data = self.scan(VULNERABLE)
        self.assertEqual(data["errors"], [])
        counts = {}
        for result in data["results"]:
            name = result["check_id"].split(".")[-1]
            counts[name] = counts.get(name, 0) + 1
        for rule, minimum in EXPECTED.items():
            self.assertGreaterEqual(counts.get(rule, 0), minimum, (rule, counts))

    def test_safe_variants_raise_nothing_and_gate_passes(self):
        report, data = self.scan(SAFE)
        self.assertEqual(data["results"], [])
        done = self.gate(report)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("aucun resultat bloquant", done.stdout)

    def test_gate_fails_when_a_vulnerability_is_introduced(self):
        report, _ = self.scan(dict(SAFE, **{"app/new.py": "import os\ndef run(c):\n    return os.system(c)\n"}))
        done = self.gate(report)
        self.assertEqual(done.returncode, 1)
        self.assertIn("forge.python.os-system", done.stdout)

    def test_warning_blocks_only_at_hardened_level(self):
        report, _ = self.scan(dict(SAFE, **{"app/tmp.py": "import tempfile\nname = tempfile.mktemp()\n"}))
        self.assertEqual(self.gate(report, "ERROR").returncode, 0)
        self.assertEqual(self.gate(report, "WARNING").returncode, 1)

    def test_empty_target_is_never_a_pass(self):
        report, data = self.scan({"README.txt": "aucun code\n"})
        self.assertEqual(data["paths"]["scanned"], [])
        done = self.gate(report)
        self.assertEqual(done.returncode, 1)
        self.assertIn("aucune analyse reelle", done.stderr)


if __name__ == "__main__":
    unittest.main()
