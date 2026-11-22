import unittest
from unittest import mock

from forge.diagnostics import ForgeError, Status
from forge.generator.render import generate
from forge.pipeline import run
from forge.planner.plan import build_plan
from forge.generator.stack import load_ci_catalog
from forge.security.controls import load_security_tools
from forge.verification import checks, http
from forge.verification.http import FetchError, Response
from forge.verification.report import verify_plan

TODAY = "2026-11-14"
PYPI = {
    "https://pypi.org/pypi/fastapi/json": {"info": {"version": "1.2.0", "license_expression": "MIT"},
                                           "releases": {"1.1.0": [{"yanked": True}], "1.2.0": [{"yanked": False}]}},
    "https://pypi.org/pypi/pytest/json": {"info": {"version": "9.0.0", "license": "MIT\nlong text"},
                                          "releases": {"9.0.0": [{}]}},
}
NPM = {
    "https://registry.npmjs.org/@vitest%2Fcoverage-v8": {"dist-tags": {"latest": "5.0.0"},
                                                         "versions": {"5.0.0": {"license": "MIT"}, "4.0.0": {"deprecated": "x"}}},
}
ACTIONS = {
    "https://api.github.com/repos/%s/git/ref/tags/%s" % (a["repository"], a["tag"]): {"object": {"type": "commit", "sha": a["sha"]}}
    for a in load_ci_catalog()["actions"].values()
}
TOOLS = load_security_tools()
RELEASES = {
    "https://api.github.com/repos/gitleaks/gitleaks/releases/tags/v%s" % TOOLS["gitleaks"]["version"]: {
        "assets": [{"name": TOOLS["gitleaks"]["asset"], "digest": "sha256:" + TOOLS["gitleaks"]["sha256"]}]},
    "https://api.github.com/repos/aquasecurity/trivy/releases/tags/v%s" % TOOLS["trivy"]["version"]: {
        "assets": [{"name": TOOLS["trivy"]["asset"], "digest": "sha256:" + TOOLS["trivy"]["sha256"]}]},
}
PYPI["https://pypi.org/pypi/semgrep/json"] = {"info": {"version": TOOLS["semgrep"]["version"], "license": "LGPL-2.1-or-later"},
                                              "releases": {TOOLS["semgrep"]["version"]: [{}]}}
for _name, _version in TOOLS["pypi"].items():
    PYPI["https://pypi.org/pypi/%s/json" % _name] = {"info": {"version": _version, "license": "Apache-2.0"},
                                                     "releases": {_version: [{}]}}
EOL = {"https://endoflife.date/api/python.json": [{"cycle": "3.13", "eol": "2029-10-31"}, {"cycle": "3.11", "eol": "2026-01-01"}]}


class FakeRegistry:
    def __init__(self, vulns=None, offline=()):
        self.vulns = vulns or {}
        self.offline = set(offline)
        self.calls = []

    def __call__(self, url, payload=None):
        self.calls.append(url)
        if url in self.offline or "*" in self.offline:
            raise FetchError("hors ligne")
        if payload is not None:
            key = "%s@%s" % (payload["package"]["name"], payload["version"])
            return Response(200, {"vulns": self.vulns.get(key, [])})
        data = {**PYPI, **NPM, **EOL, **ACTIONS, **RELEASES}.get(url)
        return Response(404, None) if data is None else Response(200, data)


SPEC = {"name": "stock-api", "project_type": "api", "agents": ["codex"], "description": "API",
        "technologies": ["python", "fastapi", "pytest"]}


class PackageCheckTests(unittest.TestCase):
    def test_existing_package_latest_and_licence(self):
        result = checks.check_package("pypi", "FastAPI", fetch=FakeRegistry())
        self.assertEqual(result.status, Status.PASS)
        self.assertEqual(result.details, {"version": "1.2.0", "latest": "1.2.0", "license": "MIT"})
        self.assertEqual(checks.check_package("pypi", "pytest", fetch=FakeRegistry()).details["license"], "MIT")

    def test_fictional_package_and_versions_fail(self):
        registry = FakeRegistry()
        self.assertEqual(checks.check_package("pypi", "fastapi-magic-ai", fetch=registry).status, Status.FAIL)
        self.assertEqual(checks.check_package("pypi", "fastapi", "0.0.1", fetch=registry).status, Status.FAIL)
        self.assertIn("yanked", checks.check_package("pypi", "fastapi", "1.1.0", fetch=registry).message)
        self.assertEqual(checks.check_package("npm", "@vitest/coverage-v8", "4.0.0", fetch=registry).status, Status.FAIL)
        self.assertEqual(checks.check_package("npm", "@vitest/coverage-v8", fetch=registry).status, Status.PASS)

    def test_registry_unavailable_is_not_pass(self):
        result = checks.check_package("npm", "react", fetch=FakeRegistry(offline="*"))
        self.assertEqual(result.status, Status.NON_VERIFIE)

    def test_urls_are_normalised(self):
        self.assertEqual(checks.pypi_url("Zope.Interface_x"), "https://pypi.org/pypi/zope-interface-x/json")
        self.assertEqual(checks.npm_url("@scope/pkg"), "https://registry.npmjs.org/@scope%2Fpkg")


class VulnerabilityAndRuntimeTests(unittest.TestCase):
    def vuln(self, *severities):
        return {"fastapi@1.2.0": [{"id": "GHSA-%d" % i, "database_specific": {"severity": s}} for i, s in enumerate(severities)]}

    def test_severity_policy(self):
        def run(vulns):
            return checks.check_vulnerabilities("pypi", "fastapi", "1.2.0", FakeRegistry(vulns)).status
        self.assertEqual(run({}), Status.PASS)
        self.assertEqual(run(self.vuln("LOW", "MODERATE")), Status.PASS)
        self.assertEqual(run(self.vuln("LOW", "HIGH")), Status.FAIL)
        self.assertEqual(run(self.vuln("CRITICAL")), Status.FAIL)
        self.assertEqual(run({"fastapi@1.2.0": [{"id": "PYSEC-1"}]}), Status.NON_VERIFIE)

    def test_runtime_end_of_life(self):
        registry = FakeRegistry()
        self.assertEqual(checks.check_runtime("python", "3.13", TODAY, registry).status, Status.PASS)
        self.assertEqual(checks.check_runtime("python", "3.11", TODAY, registry).status, Status.FAIL)
        self.assertEqual(checks.check_runtime("python", "3.12", TODAY, registry).status, Status.FAIL)
        self.assertEqual(checks.check_runtime("python", "3.13", TODAY, FakeRegistry(offline="*")).status, Status.NON_VERIFIE)


class ReportTests(unittest.TestCase):
    def test_full_report_pass_and_document_statuses(self):
        registry = FakeRegistry()
        result = run(SPEC, verify=True, verifier=lambda p: verify_plan(p, registry, TODAY))
        plan, deps = result.plan, result.files["docs/DEPENDENCIES.md"]
        self.assertIn("| fastapi | pypi | execution | 1.2.0 | MIT | PASS |", deps)
        self.assertIn("| pytest | pypi | developpement | 9.0.0 | MIT | PASS |", deps)
        report = verify_plan(plan, registry, TODAY)
        self.assertTrue(report.ok)
        self.assertEqual({c.status for c in report.checks if c.kind == "api"}, {Status.NON_VERIFIE})

    def test_e10_tools_are_verified_online(self):
        registry = FakeRegistry()
        report = verify_plan(build_plan(dict(SPEC, technologies=SPEC["technologies"] + ["docker"])), registry, TODAY)
        subjects = {(c.kind, c.subject): c.status for c in report.checks}
        self.assertEqual(subjects[("package", "pypi:semgrep")], Status.PASS)
        self.assertEqual(subjects[("vulnerabilities", "pypi:semgrep@%s" % TOOLS["semgrep"]["version"])], Status.PASS)
        self.assertEqual(subjects[("tool", "aquasecurity/trivy v%s" % TOOLS["trivy"]["version"])], Status.PASS)
        # Empreinte Trivy differente sur GitHub : FAIL bloquant, jamais PASS.
        tampered = FakeRegistry()
        url = "https://api.github.com/repos/aquasecurity/trivy/releases/tags/v%s" % TOOLS["trivy"]["version"]
        with mock.patch.dict(RELEASES, {url: {"assets": [{"name": TOOLS["trivy"]["asset"], "digest": "sha256:" + "0" * 64}]}}):
            report = verify_plan(build_plan(dict(SPEC, technologies=SPEC["technologies"] + ["docker"])), tampered, TODAY)
        self.assertFalse(report.ok)

    def test_vulnerable_or_fictional_dependency_blocks_generation(self):
        registry = FakeRegistry({"fastapi@1.2.0": [{"id": "GHSA-x", "database_specific": {"severity": "CRITICAL"}}]})
        with self.assertRaises(ForgeError) as ctx:
            run(SPEC, verify=True, verifier=lambda p: verify_plan(p, registry, TODAY))
        self.assertIn("verification-vulnerabilities", {x.code for x in ctx.exception.diagnostics})
        chosen = dict(SPEC, versions={"fastapi": "0.0.1"})
        with self.assertRaises(ForgeError):
            run(chosen, verify=True, verifier=lambda p: verify_plan(p, FakeRegistry(), TODAY))

    def test_offline_registry_gives_warnings_not_pass(self):
        plan = build_plan(SPEC)
        report = verify_plan(plan, FakeRegistry(offline="*"), TODAY)
        self.assertTrue(report.ok)
        self.assertTrue(all(c.status is Status.NON_VERIFIE for c in report.checks))
        self.assertIn("unverified-package", {x.code for x in report.diagnostics})
        self.assertEqual(report.package_status("pypi", "fastapi")[0], Status.NON_VERIFIE)

    def test_no_network_without_explicit_verification(self):
        with mock.patch.object(http._OPENER, "open", side_effect=AssertionError("reseau interdit")):
            generate(SPEC)
            run(SPEC)


class ActionCheckTests(unittest.TestCase):
    def test_action_pin_policy(self):
        sha = "a" * 40
        url = "https://api.github.com/repos/actions/checkout/git/ref/tags/v1"

        def fake(data):
            return lambda u, payload=None: Response(200 if data else 404, data)

        self.assertEqual(checks.check_action("actions/checkout", "v1", sha, fake({"object": {"type": "commit", "sha": sha}})).status, Status.PASS)
        moved = checks.check_action("actions/checkout", "v1", sha, fake({"object": {"type": "commit", "sha": "b" * 40}}))
        self.assertEqual(moved.status, Status.FAIL)
        self.assertEqual(checks.check_action("actions/checkout", "v1", sha, fake(None)).status, Status.FAIL)
        annotated = {url: {"object": {"type": "tag", "url": "https://api.github.com/repos/actions/checkout/git/tags/x"}},
                     "https://api.github.com/repos/actions/checkout/git/tags/x": {"object": {"type": "commit", "sha": sha}}}
        self.assertEqual(checks.check_action("actions/checkout", "v1", sha, lambda u, payload=None: Response(200, annotated[u])).status, Status.PASS)
        self.assertEqual(checks.check_action("actions/checkout", "v1", sha, FakeRegistry(offline="*")).status, Status.NON_VERIFIE)

    def test_moved_action_tag_blocks_generation(self):
        registry = FakeRegistry()
        first = next(iter(ACTIONS))
        with mock.patch.dict(ACTIONS, {first: {"object": {"type": "commit", "sha": "c" * 40}}}):
            with self.assertRaises(ForgeError) as ctx:
                run(SPEC, verify=True, verifier=lambda p: verify_plan(p, registry, TODAY))
        self.assertIn("verification-action", {x.code for x in ctx.exception.diagnostics})


class SecurityToolCheckTests(unittest.TestCase):
    def test_release_asset_digest_policy(self):
        tool = TOOLS["gitleaks"]
        url = next(iter(RELEASES))

        def check(data):
            return checks.check_release_asset(tool["repository"], tool["version"], tool["asset"], tool["sha256"],
                                              lambda u, payload=None: Response(200 if data else 404, data))
        self.assertEqual(check(RELEASES[url]).status, Status.PASS)
        self.assertEqual(check({"assets": [{"name": tool["asset"], "digest": "sha256:" + "0" * 64}]}).status, Status.FAIL)
        self.assertEqual(check({"assets": []}).status, Status.FAIL)
        self.assertEqual(check({"assets": [{"name": tool["asset"]}]}).status, Status.NON_VERIFIE)
        self.assertEqual(check(None).status, Status.FAIL)

    def test_tampered_gitleaks_digest_blocks_generation(self):
        url = next(iter(RELEASES))
        tampered = {"assets": [{"name": TOOLS["gitleaks"]["asset"], "digest": "sha256:" + "f" * 64}]}
        with mock.patch.dict(RELEASES, {url: tampered}):
            with self.assertRaises(ForgeError) as ctx:
                run(SPEC, verify=True, verifier=lambda p: verify_plan(p, FakeRegistry(), TODAY))
        self.assertIn("verification-tool", {x.code for x in ctx.exception.diagnostics})


class HttpGuardTests(unittest.TestCase):
    def test_only_https_allowlisted_hosts(self):
        for url in ("http://pypi.org/x", "https://evil.example/x", "https://user@pypi.org/x", "https://pypi.org:444/x",
                    "file:///etc/passwd"):
            with self.assertRaises(FetchError, msg=url):
                http.fetch_json(url)


if __name__ == "__main__":
    unittest.main()
