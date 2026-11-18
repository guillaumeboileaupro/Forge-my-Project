"""E06 : controles PASS / FAIL / NON VERIFIE, confirmation explicite et revalidation avant ecriture.

Les cas d'usage reels de forge.web sont appeles avec un verificateur injecte (aucun reseau)
et une destination temporaire reelle (FORGE_WRITE_ROOT).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forge import web
from forge.diagnostics import Status
from forge.pipeline import run as real_run
from forge.security.controls import load_security_tools
from forge.verification import unverified
from forge.verification.checks import Check
from forge.verification.report import VerificationReport, _diagnostic

CONFIG = {
    "schema_version": 1, "name": "stock-api", "project_type": "api", "description": "API de stock",
    "technologies": ["python", "fastapi", "pytest"], "versions": {"python": "3.12"},
    "agents": ["codex", "claude"], "security": "strict", "options": {"mcp": False}, "architecture": "",
}
PASS = Check("package", "pypi:fastapi", Status.PASS, "Version verifiee sur PyPI")
FAIL = Check("vulnerabilities", "pypi:fastapi@0.1", Status.FAIL, "Vulnerabilite critique GHSA-test")
VULNS_UNKNOWN = Check("vulnerabilities", "pypi:fastapi", Status.NON_VERIFIE, "Base OSV indisponible : timeout")
RUNTIME_UNKNOWN = Check("runtime", "python@3.12", Status.NON_VERIFIE, "endoflife.date indisponible : timeout")


def report(*found):
    return VerificationReport(tuple(found), tuple(x for x in map(_diagnostic, found) if x is not None))


def decode(response):
    status, body, _, _ = response
    return status, (json.loads(body) if body[:1] in (b"{", b"[") else body)


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        patcher = mock.patch.dict(os.environ, {"FORGE_WRITE_ROOT": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.checks = (PASS,)
        patcher = mock.patch.object(web, "run", self.fake_run)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_run(self, data, verify=False, skills=False):
        return real_run(data, verify=verify, skills=skills, verifier=lambda plan: report(*self.checks))

    def call(self, function, payload):
        return decode(function(json.dumps(payload).encode("utf-8")))

    def plan(self, config=CONFIG, verify=True):
        status, payload = self.call(web.plan_payload, {"config": config, "verify": verify})
        self.assertEqual(status, 200, payload)
        return payload

    def write(self, config=CONFIG, verify=True, acknowledge=None, files=None, name="dest"):
        """Compare puis ecrit ; retourne (statut, corps) de l'ecriture et le dossier cible."""
        dest = self.root / name
        files = files or self.plan(config, verify)["contents"]
        request = {"config": config, "verify": verify, "files": files, "destination": str(dest)}
        status, comparison = self.call(web.write_compare_payload, request)
        self.assertEqual(status, 200, comparison)
        apply = dict(request, token=comparison["token"], decisions={}, confirm=True)
        if acknowledge is not None:
            apply["acknowledge"] = acknowledge
        return self.call(web.write_apply_payload, apply), dest


class StatusTests(Harness):
    def test_all_pass_needs_no_confirmation(self):
        assessment = self.plan()["unverified"]
        self.assertEqual((assessment["items"], assessment["blocking"], assessment["token"]), ([], [], None))
        (status, body), dest = self.write()
        self.assertEqual(status, 200, body)
        self.assertTrue((dest / "AGENTS.md").exists())
        self.assertEqual(body["report"]["journal"]["confirmations"], [])

    def test_fail_blocks_and_is_never_confirmable(self):
        self.checks = (FAIL,)
        for function in (web.plan_payload, web.archive_payload):
            status, payload = self.call(function, {"config": CONFIG, "verify": True})
            self.assertEqual(status, 422, payload)
            self.assertFalse(payload["ok"])
            self.assertNotIn("unverified", payload)  # un FAIL n'est jamais propose a la confirmation

    def test_unverified_is_listed_with_name_reason_and_risk(self):
        self.checks = (PASS, VULNS_UNKNOWN)
        assessment = self.plan()["unverified"]
        item = next(i for i in assessment["items"] if i["id"] == "vulnerabilities:pypi:fastapi")
        self.assertEqual(item["status"], "NON VERIFIE")
        self.assertEqual(item["reason"], "Base OSV indisponible : timeout")  # raison exacte conservee
        self.assertIn("vulnerable", item["risk"])
        self.assertFalse(item["critical"])
        self.assertTrue(assessment["token"])
        self.assertEqual(assessment["counts"]["non_verifie"], 1)


class ConfirmationTests(Harness):
    def setUp(self):
        super().setUp()
        self.checks = (PASS, VULNS_UNKNOWN)

    def test_accepted_confirmation_writes_and_keeps_non_verifie(self):
        token = self.plan()["unverified"]["token"]
        (status, body), dest = self.write(acknowledge=token)
        self.assertEqual(status, 200, body)
        journal = body["report"]["journal"]
        confirmed = {c["id"]: c for c in journal["confirmations"]}
        self.assertEqual(confirmed["vulnerabilities:pypi:fastapi"]["status"], "NON VERIFIE")  # jamais PASS
        self.assertTrue(confirmed["vulnerabilities:pypi:fastapi"]["confirmed"])
        self.assertTrue(any("Base OSV indisponible" in m for m in journal["non_verifie"]))

    def test_refused_confirmation_writes_nothing(self):
        for acknowledge in (None, "", "0" * 64, 42):
            with self.subTest(acknowledge=acknowledge):
                (status, body), dest = self.write(acknowledge=acknowledge, name="refus-%s" % acknowledge)
                self.assertEqual(status, 409, body)
                self.assertTrue(body["confirmation_required"])
                self.assertTrue(body["unverified"]["items"])
                self.assertFalse(dest.exists())

    def test_stale_confirmation_after_restart_is_refused(self):
        token = self.plan()["unverified"]["token"]
        with mock.patch.object(unverified, "_KEY", os.urandom(32)):  # redemarrage du serveur
            (status, body), dest = self.write(acknowledge=token)
        self.assertEqual(status, 409)
        self.assertIn("perimee", body["error"])
        self.assertFalse(dest.exists())

    def test_configuration_change_after_confirmation_is_refused(self):
        token = self.plan()["unverified"]["token"]
        changed = dict(CONFIG, description="API de stock modifiee")
        (status, body), dest = self.write(config=changed, acknowledge=token)
        self.assertEqual(status, 409)
        self.assertFalse(dest.exists())

    def test_new_unverified_check_after_confirmation_is_refused(self):
        token = self.plan()["unverified"]["token"]
        self.checks = (PASS, VULNS_UNKNOWN, RUNTIME_UNKNOWN)  # revalidation : un controle de plus
        (status, body), dest = self.write(acknowledge=token)
        self.assertEqual(status, 409)
        self.assertIn("runtime:python@3.12", [i["id"] for i in body["unverified"]["items"]])
        self.assertFalse(dest.exists())

    def test_verification_failing_just_before_write_blocks(self):
        token = self.plan()["unverified"]["token"]
        files = self.plan()["contents"]
        dest = self.root / "late-fail"
        request = {"config": CONFIG, "verify": True, "files": files, "destination": str(dest)}
        status, comparison = self.call(web.write_compare_payload, request)
        self.checks = (FAIL,)  # la verification repetee a l'ecriture echoue
        status, body = self.call(web.write_apply_payload, dict(request, token=comparison["token"], decisions={},
                                                                confirm=True, acknowledge=token))
        self.assertEqual(status, 422)
        self.assertFalse(dest.exists())


class CriticalTests(Harness):
    HARDENED = dict(CONFIG, security="hardened")

    def test_critical_unverified_blocks_archive_and_write(self):
        self.checks = (PASS, VULNS_UNKNOWN)
        assessment = self.plan(self.HARDENED)["unverified"]
        self.assertEqual(assessment["blocking"], ["vulnerabilities:pypi:fastapi"])
        self.assertIsNone(assessment["token"])  # aucune confirmation possible
        status, body = self.call(web.archive_payload, {"config": self.HARDENED, "verify": True})
        self.assertEqual(status, 422)
        self.assertIn("critique", body["error"])
        (status, body), dest = self.write(self.HARDENED, acknowledge="0" * 64)
        self.assertEqual(status, 422)
        self.assertFalse(dest.exists())

    def test_hardened_without_online_verification_is_blocked(self):
        assessment = self.plan(self.HARDENED, verify=False)["unverified"]
        self.assertEqual(assessment["blocking"], ["verification-not-run:"])

    def test_non_security_unverified_stays_confirmable_in_hardened(self):
        self.checks = (PASS, RUNTIME_UNKNOWN)
        assessment = self.plan(self.HARDENED)["unverified"]
        self.assertEqual(assessment["blocking"], [])
        (status, body), _ = self.write(self.HARDENED, acknowledge=assessment["token"])
        self.assertEqual(status, 200, body)


class SecurityPreservedTests(Harness):
    def test_secret_still_blocks_even_with_valid_confirmation(self):
        self.checks = (PASS, VULNS_UNKNOWN)
        payload = self.plan()
        files = dict(payload["contents"])
        files["README.md"] += "\nghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8" + "\n"
        dest = self.root / "secret"
        request = {"config": CONFIG, "verify": True, "files": files, "destination": str(dest)}
        status, body = self.call(web.write_compare_payload, request)
        self.assertEqual(status, 400)
        self.assertIn("jeton GitHub", body["error"])
        status, body = self.call(web.write_apply_payload, dict(request, token="0" * 64, decisions={}, confirm=True,
                                                                acknowledge=payload["unverified"]["token"]))
        self.assertEqual(status, 400)
        self.assertFalse(dest.exists())

    def test_security_thresholds_and_picomatch_exception_unchanged(self):
        tools = load_security_tools()
        self.assertEqual(tools["npm_audit_level"], {"strict": "high", "hardened": "moderate"})
        self.assertEqual(tools["sast_severity"], {"strict": "medium", "hardened": "low"})
        self.assertEqual([(e["id"], e["package"], e["expires"]) for e in tools["npm_audit_exceptions"]],
                         [("GHSA-fc5q-39xc-vjpf", "picomatch", "2026-12-17")])


if __name__ == "__main__":
    unittest.main()
