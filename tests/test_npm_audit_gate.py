"""Passerelle d'audit npm des projets generes : exceptions datees, ciblees, fail-closed."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forge.pipeline import run
from forge.security.controls import SecurityCatalogError, _check_npm_exception, load_security_tools

NODE = {"name": "gate-demo", "project_type": "api", "agents": ["codex"],
        "technologies": ["typescript", "node", "express", "vitest", "eslint", "npm-audit"]}
GHSA = "GHSA-fc5q-39xc-vjpf"
VALID = {"id": GHSA, "package": "picomatch", "added": "2026-11-17", "expires": "2026-12-17",
         "reason": "ReDoS sans version corrigee; dependance de developpement transitive."}


def advisory(name, ghsa, severity):
    return {"source": 1, "name": name, "dependency": name, "title": "t", "severity": severity,
            "url": "https://github.com/advisories/" + ghsa, "range": "<=9"}


def report(*advisories):
    vulns = {}
    for adv in advisories:
        vulns[adv["name"]] = {"name": adv["name"], "severity": adv["severity"], "via": [adv]}
    if advisories and advisories[0]["name"] == "picomatch":  # chaine transitive reelle de l'avis
        vulns["fdir"] = {"name": "fdir", "severity": "high", "via": ["picomatch"]}
        vulns["tinyglobby"] = {"name": "tinyglobby", "severity": "high", "via": ["fdir", "picomatch"]}
    return {"auditReportVersion": 2, "vulnerabilities": vulns}


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = run(NODE).files
        cls.tmp = Path(tempfile.mkdtemp(prefix="npm-gate-"))
        cls.gate = cls.tmp / "gate.py"
        cls.gate.write_text(cls.files["scripts/security/npm_audit_gate.py"], encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def decide(self, data, level="high", gate=None):
        path = self.tmp / "report.json"
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return subprocess.run([sys.executable, str(gate or self.gate), str(path), level],
                              capture_output=True, text=True)

    def test_generated_ci_calls_gate_only_after_audit_failure(self):
        workflow = self.files[".github/workflows/ci.yml"]
        self.assertIn('npm audit --audit-level=high --json > "$RUNNER_TEMP/npm-audit.json" '
                      '|| python3 scripts/security/npm_audit_gate.py "$RUNNER_TEMP/npm-audit.json" high', workflow)
        self.assertIn(GHSA, self.files["SECURITY.md"])
        self.assertIn("expire le 2026-12-17", self.files["SECURITY.md"])

    def test_python_projects_do_not_get_the_gate(self):
        files = run({"name": "py-demo", "project_type": "library", "agents": ["codex"],
                     "technologies": ["python", "unittest"]}).files
        self.assertNotIn("scripts/security/npm_audit_gate.py", files)

    def test_listed_unexpired_advisory_passes_with_visible_notice(self):
        done = self.decide(report(advisory("picomatch", GHSA, "high")))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("EXCEPTION picomatch", done.stdout)

    def test_any_other_advisory_still_blocks(self):
        done = self.decide(report(advisory("picomatch", GHSA, "high"),
                                  advisory("lodash", "GHSA-xxxx-xxxx-xxxx", "critical")))
        self.assertEqual(done.returncode, 1)
        self.assertIn("lodash", done.stderr)

    def test_same_advisory_on_another_package_blocks(self):
        self.assertEqual(self.decide(report(advisory("micromatch", GHSA, "high"))).returncode, 1)

    def test_expired_exception_blocks(self):
        expired = self.tmp / "expired.py"
        expired.write_text(self.gate.read_text(encoding="utf-8").replace("2026-12-17", "2000-01-01"), encoding="utf-8")
        done = self.decide(report(advisory("picomatch", GHSA, "high")), gate=expired)
        self.assertEqual(done.returncode, 1)
        self.assertIn("exception expiree", done.stderr)

    def test_level_is_respected(self):
        moderate = report(advisory("left-pad", "GHSA-2222-3333-4444", "moderate"))
        self.assertEqual(self.decide(moderate, "high").returncode, 0)
        self.assertEqual(self.decide(moderate, "moderate").returncode, 1)

    def test_unreadable_or_error_reports_fail_closed(self):
        for data in ("{", {"error": {"code": "ENOTFOUND"}}, {"vulnerabilities": {"x": {"via": ["y"]}}}):
            with self.subTest(data=data):
                self.assertEqual(self.decide(data).returncode, 1)
        self.assertEqual(self.decide(report(), "bogus").returncode, 1)


class CatalogTests(unittest.TestCase):
    def test_catalog_exception_is_valid_and_bounded(self):
        items = load_security_tools()["npm_audit_exceptions"]
        self.assertEqual([i["id"] for i in items], [GHSA])

    def test_invalid_exceptions_are_rejected(self):
        bad = [dict(VALID, id="CVE-2026-1"), dict(VALID, package="Bad Name"),
               dict(VALID, reason='injection" + x'), dict(VALID, reason="court"),
               dict(VALID, expires="2027-06-01"), dict(VALID, expires="2026-11-17"),
               dict(VALID, expires="demain"), {k: v for k, v in VALID.items() if k != "reason"},
               dict(VALID, extra="x")]
        for item in bad:
            with self.subTest(item=item):
                with self.assertRaises(SecurityCatalogError):
                    _check_npm_exception(copy.deepcopy(item))
        _check_npm_exception(dict(VALID))


if __name__ == "__main__":
    unittest.main()
