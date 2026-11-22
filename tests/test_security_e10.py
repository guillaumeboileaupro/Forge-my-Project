"""E10 : Semgrep et analyse d'image des projets generes ; anciens controles preserves (hors ligne)."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forge.pipeline import run
from forge.security.controls import SecurityCatalogError, _check_e10_tools, load_security_tools

ROOT = Path(__file__).resolve().parents[1]
IMAGE_GATE = ROOT / "templates" / "security" / "image_scan_gate.py.tmpl"
SEMGREP_GATE = ROOT / "templates" / "security" / "semgrep_gate.py.tmpl"
PROFILES = ("python-api-fastapi", "python-cli", "python-library", "python-web-django",
            "typescript-api-express", "typescript-web-react")
DOCKER = {"schema_version": 1, "name": "img-demo", "project_type": "api", "description": "Demo",
          "technologies": ["python", "fastapi", "pytest", "docker"], "agents": ["codex"]}


def profile(name):
    data = json.loads((ROOT / "catalogs" / "profiles" / (name + ".json")).read_text(encoding="utf-8"))
    return dict(data["answers"], name="demo-" + name[:30])


def trivy_report(*severities):
    vulns = [{"VulnerabilityID": "CVE-2026-%04d" % i, "PkgName": "libdemo", "InstalledVersion": "1.0",
              "FixedVersion": "", "Severity": severity} for i, severity in enumerate(severities)]
    return {"SchemaVersion": 2, "ArtifactName": "forge-image-scan:ci",
            "Results": [{"Target": "forge-image-scan:ci (debian 12)", "Vulnerabilities": vulns}]}


def semgrep_report(*severities, scanned=("src/app.py",), errors=()):
    results = [{"check_id": "forge.python.os-system", "path": "src/app.py", "start": {"line": i + 1},
                "extra": {"severity": severity, "message": "demo"}} for i, severity in enumerate(severities)]
    return {"results": results, "errors": list(errors), "paths": {"scanned": list(scanned)}, "version": "1.184.0"}


class GateHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="forge-e10-"))
        self.addCleanup(lambda: [p.unlink() for p in self.tmp.iterdir()] and None or self.tmp.rmdir())

    def gate(self, script, report, level):
        path = self.tmp / "report.json"
        if report is not None:
            path.write_text(report if isinstance(report, str) else json.dumps(report), encoding="utf-8")
        return subprocess.run([sys.executable, str(script), str(path), level], capture_output=True, text=True)


class ImageGateTests(GateHarness):
    def test_high_vulnerability_blocks(self):
        done = self.gate(IMAGE_GATE, trivy_report("LOW", "HIGH"), "high")
        self.assertEqual(done.returncode, 1)
        self.assertIn("BLOQUANT HIGH CVE-2026-0001", done.stdout)

    def test_critical_vulnerability_blocks(self):
        done = self.gate(IMAGE_GATE, trivy_report("CRITICAL"), "high")
        self.assertEqual(done.returncode, 1)
        self.assertIn("1 vulnerabilite(s) bloquante(s)", done.stderr)

    def test_below_threshold_passes_and_hardened_is_stricter(self):
        report = trivy_report("LOW", "MEDIUM")
        self.assertEqual(self.gate(IMAGE_GATE, report, "high").returncode, 0)
        self.assertEqual(self.gate(IMAGE_GATE, report, "medium").returncode, 1)

    def test_unfixed_vulnerability_is_never_ignored(self):
        report = trivy_report("CRITICAL")
        self.assertEqual(report["Results"][0]["Vulnerabilities"][0]["FixedVersion"], "")
        self.assertEqual(self.gate(IMAGE_GATE, report, "high").returncode, 1)

    def test_invalid_missing_or_empty_report_fails_closed(self):
        cases = {"illisible": "{", "absent": None, "schema": {"SchemaVersion": 1, "Results": []},
                 "sans resultat": {"SchemaVersion": 2, "Results": []}, "liste": "[]"}
        for label, report in cases.items():
            with self.subTest(label=label):
                (self.tmp / "report.json").unlink(missing_ok=True)
                done = self.gate(IMAGE_GATE, report, "high")
                self.assertEqual(done.returncode, 1, done.stdout)
                self.assertIn("refus", done.stderr)

    def test_clean_image_passes(self):
        done = self.gate(IMAGE_GATE, trivy_report(), "high")
        self.assertEqual(done.returncode, 0, done.stderr)


class SemgrepGateTests(GateHarness):
    def test_error_finding_blocks_and_warning_only_in_hardened(self):
        self.assertEqual(self.gate(SEMGREP_GATE, semgrep_report("ERROR"), "ERROR").returncode, 1)
        self.assertEqual(self.gate(SEMGREP_GATE, semgrep_report("WARNING"), "ERROR").returncode, 0)
        self.assertEqual(self.gate(SEMGREP_GATE, semgrep_report("WARNING"), "WARNING").returncode, 1)

    def test_success_requires_a_real_analysis(self):
        done = self.gate(SEMGREP_GATE, semgrep_report(scanned=()), "ERROR")
        self.assertEqual(done.returncode, 1)
        self.assertIn("aucune analyse reelle", done.stderr)
        self.assertEqual(self.gate(SEMGREP_GATE, semgrep_report(), "ERROR").returncode, 0)

    def test_incomplete_or_invalid_report_fails_closed(self):
        incomplete = semgrep_report(errors=[{"type": "Timeout", "message": "src/big.py"}])
        cases = {"incomplet": incomplete, "illisible": "{", "absent": None, "sans paths": {"results": [], "errors": []}}
        for label, report in cases.items():
            with self.subTest(label=label):
                (self.tmp / "report.json").unlink(missing_ok=True)
                done = self.gate(SEMGREP_GATE, report, "ERROR")
                self.assertEqual(done.returncode, 1)
                self.assertIn("refus", done.stderr)


class CatalogTests(unittest.TestCase):
    def test_tools_are_pinned_and_thresholds_cannot_be_weakened(self):
        tools = load_security_tools()
        self.assertEqual(tools["semgrep"]["version"], "1.184.0")
        self.assertEqual(tools["trivy"]["asset"], "trivy_0.76.2_Linux-64bit.tar.gz")
        for mutate in (lambda t: t["semgrep_severity"].update(strict="WARNING_ONLY"),
                       lambda t: t["image_severity"].update(strict="critical"),
                       lambda t: t["trivy"].update(sha256="0" * 63),
                       lambda t: t["trivy"].update(asset="trivy_9.9.9_Linux-64bit.tar.gz"),
                       lambda t: t["semgrep"].update(version="latest")):
            broken = copy.deepcopy(tools)
            mutate(broken)
            with self.assertRaises(SecurityCatalogError):
                _check_e10_tools(broken)

    def test_existing_thresholds_and_picomatch_exception_unchanged(self):
        tools = load_security_tools()
        self.assertEqual(tools["npm_audit_level"], {"strict": "high", "hardened": "moderate"})
        self.assertEqual(tools["sast_severity"], {"strict": "medium", "hardened": "low"})
        self.assertEqual([(e["id"], e["package"], e["expires"]) for e in tools["npm_audit_exceptions"]],
                         [("GHSA-fc5q-39xc-vjpf", "picomatch", "2026-12-17")])


class GenerationTests(unittest.TestCase):
    def test_six_profiles_run_semgrep_and_keep_previous_controls(self):
        for name in PROFILES:
            with self.subTest(profile=name):
                files = run(profile(name)).files
                workflow = files[".github/workflows/ci.yml"]
                self.assertIn('"semgrep==1.184.0"', workflow)
                self.assertIn("--config .semgrep/forge.yml --metrics=off", workflow)
                self.assertIn('semgrep_gate.py "$RUNNER_TEMP/semgrep.json" ERROR', workflow)
                self.assertNotIn("--config auto", workflow)  # aucune regle telechargee implicitement
                configs = [part.split()[0] for part in workflow.split("--config ")[1:]]
                self.assertEqual(configs, [".semgrep/forge.yml"])  # fichier local, jamais p/..., r/..., auto, URL
                self.assertEqual(files[".semgrep/forge.yml"], (ROOT / "templates/security/semgrep.yml.tmpl").read_text())
                self.assertIn("gitleaks", workflow)
                self.assertIn("  attribution:", workflow)
                if name.startswith("python"):
                    self.assertIn("bandit -r src", workflow)
                    self.assertIn("pip-audit --strict", workflow)
                    # Semgrep apres Bandit : les preuves existantes de detection Bandit restent valides.
                    self.assertLess(workflow.index("SAST Python (Bandit"), workflow.index("SAST multi-langage"))
                else:
                    self.assertIn("npm audit --audit-level=high", workflow)
                    self.assertIn("eslint-plugin-security", files["package.json"])
                for forbidden in ("continue-on-error", "|| true", "--exit-code 0", "set +e", "--audit-level=none",
                                  "--ignore-unfixed", "nosemgrep"):
                    self.assertNotIn(forbidden, workflow)
                self.assertNotIn("Dockerfile", files)
                self.assertNotIn("Analyse de l'image conteneur", workflow)  # pas de Docker : pas de scanner
                self.assertNotIn("scripts/security/image_scan_gate.py", files)

    def test_docker_project_scans_its_image_only_when_a_dockerfile_exists(self):
        files = run(DOCKER).files
        workflow = files[".github/workflows/ci.yml"]
        self.assertNotIn("Dockerfile", files)  # Forge n'invente pas de Dockerfile
        self.assertIn("scripts/security/image_scan_gate.py", files)
        self.assertIn("if [ -f Dockerfile ]; then", workflow)
        self.assertIn("sha256sum --check --strict", workflow.split("Analyse de l'image conteneur")[1])
        self.assertIn('image_scan_gate.py "$RUNNER_TEMP/trivy.json" high', workflow)
        image_step = workflow.split("Analyse de l'image conteneur")[1].split("\n      - name:")[0]
        for forbidden in ("--severity", "--ignore-unfixed", "--exit-code", "|| true"):  # aucun filtre ni contournement
            self.assertNotIn(forbidden, image_step)
        self.assertIn("::warning::Analyse d'image NON VERIFIE", workflow)
        security = files["SECURITY.md"]
        self.assertIn("NON VERIFIE tant qu'aucun Dockerfile n'existe", security)
        codes = [d.code for d in run(DOCKER).diagnostics]
        self.assertIn("security-image-unverified", codes)  # NON VERIFIE a confirmer (E06)

    def test_hardened_level_is_stricter(self):
        files = run(dict(DOCKER, security="hardened")).files
        workflow = files[".github/workflows/ci.yml"]
        self.assertIn('semgrep_gate.py "$RUNNER_TEMP/semgrep.json" WARNING', workflow)
        self.assertIn('image_scan_gate.py "$RUNNER_TEMP/trivy.json" medium', workflow)


if __name__ == "__main__":
    unittest.main()
