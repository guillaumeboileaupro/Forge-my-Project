import json
import tempfile
import unittest
from pathlib import Path

from forge.pipeline import run
from forge.security.controls import SecurityCatalogError, load_security_tools

PYTHON = {"name": "secure-api", "project_type": "api", "agents": ["codex"],
          "technologies": ["python", "fastapi", "pytest"]}
NODE = {"name": "secure-web", "project_type": "web", "agents": ["codex"],
        "technologies": ["typescript", "node", "vitest", "eslint"]}


def security_job(files):
    return files[".github/workflows/ci.yml"].split("\n  security:\n")[1]


class SecurityJobTests(unittest.TestCase):
    def test_python_controls_are_pinned_and_blocking(self):
        result = run(PYTHON)
        job = security_job(result.files)
        tools = load_security_tools()
        self.assertIn("fetch-depth: 0", job)
        self.assertIn(tools["gitleaks"]["sha256"] + "  $RUNNER_TEMP/gitleaks.tar.gz\" | sha256sum --check --strict", job)
        self.assertIn("gitleaks\" git --redact --exit-code 1", job)
        for name, version in tools["pypi"].items():
            self.assertIn('"%s==%s"' % (name, version), job)
        self.assertIn("bandit -r src -q --severity-level medium", job)
        self.assertIn("pip-audit --strict --no-deps --disable-pip", job)
        self.assertIn("cyclonedx-py environment --of JSON -o sbom-python.cdx.json", job)
        self.assertIn("if-no-files-found: error", job)
        self.assertRegex(job, r"uses: actions/upload-artifact@[0-9a-f]{40} # v")

    def test_no_silent_bypass(self):
        for spec in (PYTHON, NODE, dict(NODE, technologies=["javascript", "node", "node-test"])):
            workflow = run(spec).files[".github/workflows/ci.yml"]
            for forbidden in ("continue-on-error", "|| true", "--exit-code 0", "set +e", "--audit-level=none"):
                self.assertNotIn(forbidden, workflow)

    def test_hardened_level_is_stricter(self):
        job = security_job(run(dict(PYTHON, security="hardened")).files)
        self.assertIn("--severity-level low", job)
        node_job = security_job(run(dict(NODE, security="hardened")).files)
        self.assertIn("npm audit --audit-level=moderate", node_job)

    def test_node_controls_and_eslint_security_plugin(self):
        files = run(NODE).files
        job = security_job(files)
        self.assertIn("npm audit --audit-level=high", job)
        self.assertIn("npm sbom --sbom-format cyclonedx > sbom-npm.cdx.json", job)
        self.assertIn("pluginSecurity.configs.recommended", files["eslint.config.js"])
        package = json.loads(files["package.json"])
        self.assertEqual(package["scripts"]["lint"], "eslint . --max-warnings 0")
        self.assertIn("eslint-plugin-security", package["devDependencies"])

    def test_unavailable_controls_are_non_verifie(self):
        result = run(dict(NODE, technologies=["javascript", "node", "node-test", "docker"]))
        codes = {x.code for x in result.diagnostics}
        self.assertTrue({"security-sast-unverified", "security-image-unverified"} <= codes)
        security_md = result.files["SECURITY.md"]
        self.assertIn("| SAST JavaScript/TypeScript | aucun | - | NON VERIFIE |", security_md)
        # E10 : scanner configure, mais NON VERIFIE tant qu'aucun Dockerfile n'existe (jamais PASS).
        self.assertIn("| Image conteneur | Trivy ", security_md)
        self.assertIn("| NON VERIFIE tant qu'aucun Dockerfile n'existe |", security_md)
        self.assertNotIn("PASS", security_md)

    def test_security_md_lists_configured_controls(self):
        security_md = run(PYTHON).files["SECURITY.md"]
        self.assertIn("| Secrets | Gitleaks", security_md)
        self.assertIn("| SAST Python | Bandit", security_md)
        self.assertIn("--ignore-vuln", security_md)


class SecurityCatalogTests(unittest.TestCase):
    def broken(self, mutate):
        data = load_security_tools()
        mutate(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "tools.json")
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(SecurityCatalogError):
                load_security_tools(path)

    def test_rejects_unpinned_or_inconsistent_tools(self):
        self.broken(lambda d: d["gitleaks"].update(sha256="abc"))
        self.broken(lambda d: d["gitleaks"].update(asset="gitleaks_latest_linux_x64.tar.gz"))
        self.broken(lambda d: d["pypi"].update(bandit="latest"))
        self.broken(lambda d: d["pypi"].pop("pip-audit"))


if __name__ == "__main__":
    unittest.main()
