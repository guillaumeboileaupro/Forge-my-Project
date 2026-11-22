"""E11 : verification statique des API (Python, JavaScript/TypeScript), sans reseau.

Les archives npm (.tgz + integrite SHA-512) et les roues PyPI (.whl + SHA-256) sont construites
en memoire : chaque statut PASS / FAIL / NON VERIFIE est prouve sur un vrai contenu publie.
"""
import base64
import hashlib
import io
import json
import tarfile
import unittest
import zipfile
from pathlib import Path

from forge.diagnostics import ForgeError, Status
from forge.pipeline import run
from forge.planner.plan import build_plan
from forge.verification import api
from forge.verification.checks import npm_url, pypi_url
from forge.verification.http import FetchError, Response
from forge.verification.report import verify_plan

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("python-api-fastapi", "python-cli", "python-library", "python-web-django",
            "typescript-api-express", "typescript-web-react")


def profile(name):
    data = json.loads((ROOT / "catalogs" / "profiles" / (name + ".json")).read_text(encoding="utf-8"))
    return dict(data["answers"], name="demo-" + name[:30])


def npm_tarball(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo("package/" + path)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def wheel(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


class Registry:
    """Registres npm et PyPI factices servant de vraies archives."""

    def __init__(self):
        self.json, self.blobs = {}, {}

    def npm(self, name, version, files, integrity=None):
        blob = npm_tarball(dict({"package.json": json.dumps({"name": name, "version": version, **files.pop("@manifest", {})})},
                                **files))
        url = "https://registry.npmjs.org/%s/-/x-%s.tgz" % (name, version)
        digest = "sha512-" + base64.b64encode(hashlib.sha512(blob).digest()).decode()
        self.blobs[url] = blob
        self.json[npm_url(name)] = {"dist-tags": {"latest": version},
                                    "versions": {version: {"dist": {"tarball": url, "integrity": integrity or digest}}}}

    def pypi(self, name, version, files, wheel_files=True, sha=None):
        blob = wheel(files)
        url = "https://files.pythonhosted.org/packages/x/%s-%s-py3-none-any.whl" % (name, version)
        self.blobs[url] = blob
        release = [{"packagetype": "bdist_wheel" if wheel_files else "sdist", "filename": url.rsplit("/", 1)[1],
                    "url": url, "digests": {"sha256": sha or hashlib.sha256(blob).hexdigest()}}]
        self.json[pypi_url(name)] = {"info": {"version": version}, "releases": {version: release}}

    def fetch(self, url, payload=None):
        return Response(200, self.json[url]) if url in self.json else Response(404, None)

    def fetch_bytes(self, url):
        if url not in self.blobs:
            raise FetchError("introuvable")
        return self.blobs[url]


def js_files(source, deps=("demo",)):
    manifest = {"name": "app", "devDependencies": {name: "1.0.0" for name in deps}}
    return {"package.json": json.dumps(manifest), "src/app.ts": source}


class StaticTests(unittest.TestCase):
    def test_six_profiles_have_no_static_failure_and_expose_contracts(self):
        for name in PROFILES:
            with self.subTest(profile=name):
                result = run(profile(name))
                statuses = {c["status"] for c in result.as_dict()["api"]}
                self.assertNotIn("FAIL", statuses)
                self.assertNotIn("api-static", {d.code for d in result.diagnostics})
                contracts = result.as_dict()["api"]
                by_subject = {c["subject"]: c for c in contracts}
                if name.startswith("typescript"):
                    self.assertEqual(by_subject["javascript:node:test {test}"]["status"], "PASS")
                    built = next(c for c in contracts if "dist/index.js" in c["subject"])  # sortie de build -> source
                    self.assertEqual(built["message"], "Fichier du projet : src/index.ts")
                    third_party = [c for c in contracts if c["subject"].startswith(
                        ("javascript:vitest", "javascript:typescript-eslint", "javascript:eslint", "javascript:@eslint"))]
                else:
                    third_party = [c for c in contracts if c["evidence"].startswith("catalogue:")]
                self.assertTrue(third_party)
                # Hors ligne, aucune API tierce n'est declaree PASS sans preuve.
                self.assertTrue(all(c["status"] == "NON VERIFIE" for c in third_party), third_party)

    def test_undeclared_or_unknown_imports_fail_offline(self):
        plan = build_plan(profile("typescript-api-express"))
        files = dict(run(profile("typescript-api-express")).files)
        cases = {
            'import leftPad from "left-pad";\n': "non declare dans package.json",
            'import { x } from "node:nope";\n': "Module integre Node.js inconnu",
            'import { y } from "./absent.js";\n': "Fichier local introuvable",
        }
        for source, message in cases.items():
            with self.subTest(source=source):
                checks = api.static_checks(plan, dict(files, **{"src/extra.ts": source}))
                failed = [c for c in checks if c.status is Status.FAIL]
                self.assertEqual(len(failed), 1)
                self.assertIn(message, failed[0].message)
                self.assertEqual(failed[0].evidence, "src/extra.ts:1")
        python_plan = build_plan(profile("python-api-fastapi"))
        python_files = dict(run(profile("python-api-fastapi")).files, **{"src/extra.py": "import requests\n"})
        failed = [c for c in api.static_checks(python_plan, python_files) if c.status is Status.FAIL]
        self.assertEqual([c.subject for c in failed], ["python:requests"])

    def test_undeclared_import_blocks_generation_diagnostics(self):
        result = run(profile("python-api-fastapi"))
        result.api_checks = api.static_checks(result.plan, dict(result.files, **{"src/x.py": "import yaml\n"}))
        self.assertIn("api-static", {d.code for d in result.diagnostics})
        self.assertFalse(result.as_dict()["ok"])


class NpmTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan(profile("typescript-api-express"))
        self.registry = Registry()

    def verify(self, source, deps=("demo",)):
        checks = api.verify_contracts(self.plan, js_files(source, deps), self.registry.fetch, self.registry.fetch_bytes)
        return [c for c in checks if c.subject.startswith("javascript:demo") or c.subject.startswith("javascript:other")][0]

    def test_named_export_found_directly_and_through_reexports(self):
        self.registry.npm("demo", "1.0.0", {"@manifest": {"types": "index.d.ts"},
                                             "index.d.ts": 'export declare function direct(): void;\nexport * from "./more";\n',
                                             "more.d.ts": "export { viaChain };\ndeclare const viaChain: number;\n"})
        check = self.verify('import { direct, viaChain } from "demo";\n')
        self.assertEqual(check.status, Status.PASS, check.message)
        self.assertIn("demo@1.0.0 (index.d.ts)", check.message)

    def test_missing_export_is_fail_when_declarations_are_complete(self):
        self.registry.npm("demo", "1.0.0", {"@manifest": {"types": "index.d.ts"}, "index.d.ts": "export declare const real: 1;\n"})
        check = self.verify('import { imaginary } from "demo";\n')
        self.assertEqual(check.status, Status.FAIL)
        self.assertIn("export absent : imaginary", check.message)

    def test_external_reexport_keeps_it_non_verifie(self):
        self.registry.npm("demo", "1.0.0", {"@manifest": {"types": "index.d.ts"}, "index.d.ts": 'export * from "other-pkg";\n'})
        self.assertEqual(self.verify('import { maybe } from "demo";\n').status, Status.NON_VERIFIE)

    def test_subpath_must_be_exported(self):
        self.registry.npm("demo", "1.0.0", {"@manifest": {"exports": {".": {"types": "./index.d.ts"},
                                                                       "./config": {"types": "./config.d.ts"}}},
                                             "index.d.ts": "export {};\n", "config.d.ts": "export declare function defineConfig(): void;\n"})
        self.assertEqual(self.verify('import { defineConfig } from "demo/config";\n').status, Status.PASS)
        check = self.verify('import { defineConfig } from "demo/nope";\n')
        self.assertEqual(check.status, Status.FAIL)
        self.assertIn("sous-chemin non exporte", check.message)

    def test_default_import_and_members(self):
        self.registry.npm("demo", "1.0.0", {"@manifest": {"types": "index.d.ts"},
                                             "index.d.ts": "declare const plugin: { configs: { recommended: object } };\nexport default plugin;\n"})
        self.assertEqual(self.verify('import p from "demo";\nexport default [p.configs.recommended];\n').status, Status.PASS)
        check = self.verify('import p from "demo";\nexport default [p.rules.strict];\n')
        self.assertEqual(check.status, Status.NON_VERIFIE)
        self.assertIn("rules.strict", check.message)

    def test_no_types_tampered_archive_or_unknown_package(self):
        self.registry.npm("demo", "1.0.0", {"index.js": "module.exports = {}\n"})
        self.assertEqual(self.verify('import { a } from "demo";\n').status, Status.NON_VERIFIE)
        self.registry.npm("demo", "1.0.0", {"@manifest": {"types": "i.d.ts"}, "i.d.ts": "export const a: 1;\n"},
                          integrity="sha512-" + base64.b64encode(b"0" * 64).decode())
        tampered = self.verify('import { a } from "demo";\n')
        self.assertEqual(tampered.status, Status.NON_VERIFIE)
        self.assertIn("integrite", tampered.message)
        unknown = self.verify('import { a } from "other";\n', deps=("other",))
        self.assertEqual(unknown.status, Status.FAIL)
        self.assertIn("introuvable", unknown.message)


class PypiTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan(profile("python-api-fastapi"))
        self.files = run(profile("python-api-fastapi")).files
        self.registry = Registry()

    def checks(self):
        found = api.verify_contracts(self.plan, self.files, self.registry.fetch, self.registry.fetch_bytes)
        return {c.subject: c for c in found if c.subject in ("python:fastapi", "python:pytest")}

    def test_module_present_absent_sdist_and_tampered(self):
        self.registry.pypi("fastapi", "1.0.0", {"fastapi/__init__.py": "", "fastapi-1.0.0.dist-info/RECORD": ""})
        self.registry.pypi("pytest", "9.0.0", {"_pytest/__init__.py": "", "py.py": ""})
        checks = self.checks()
        self.assertEqual(checks["python:fastapi"].status, Status.PASS)
        self.assertIn("fastapi-1.0.0-py3-none-any.whl", checks["python:fastapi"].message)
        self.assertEqual(checks["python:pytest"].status, Status.FAIL)  # module pytest absent de la roue
        self.registry.pypi("fastapi", "1.0.0", {"fastapi/__init__.py": ""}, wheel_files=False)
        self.assertEqual(self.checks()["python:fastapi"].status, Status.NON_VERIFIE)
        self.registry.pypi("fastapi", "1.0.0", {"fastapi/__init__.py": ""}, sha="0" * 64)
        self.assertIn("SHA-256", self.checks()["python:fastapi"].message)


class ReportIntegrationTests(unittest.TestCase):
    def test_injected_registry_without_archives_never_passes_third_party_api(self):
        from tests.test_engine_verification import FakeRegistry, SPEC, TODAY
        report = verify_plan(build_plan(SPEC), FakeRegistry(), TODAY)
        api_checks = {c.subject: c.status for c in report.checks if c.kind == "api"}
        self.assertEqual(api_checks["python:fastapi"], Status.NON_VERIFIE)

    def test_api_fail_blocks_generation(self):
        from tests.test_engine_verification import FakeRegistry, SPEC, TODAY
        fake = FakeRegistry()
        with self.assertRaises(ForgeError) as caught:
            run(SPEC, verify=True, verifier=lambda plan: _with_api_fail(verify_plan(plan, fake, TODAY)))
        self.assertIn("verification-api", {d.code for d in caught.exception.diagnostics})


def _with_api_fail(report):
    """Rapport ou un contrat d'API echoue : la generation doit etre bloquee (FAIL = erreur)."""
    from forge.verification.checks import Check
    from forge.verification.report import VerificationReport, _diagnostic
    failing = Check("api", "python:fastapi", Status.FAIL, "Module fastapi absent de la roue", "test")
    checks = report.checks + (failing,)
    return VerificationReport(checks, tuple(x for x in map(_diagnostic, checks) if x is not None))


if __name__ == "__main__":
    unittest.main()
