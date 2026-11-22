"""E13 : piles Rust, Go, Java (Maven) et catalogue/regles personnels locaux.

Aucun reseau : Maven Central est simule. Les outils reels (cargo, go) sont executes sur le
squelette genere quand ils sont installes ; sinon le test est ignore (preuve en CI : smoke).
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forge import web
from forge.config import local
from forge.config.catalog import CatalogError, load_catalog
from forge.config.profiles import load_predefined
from forge.diagnostics import Status
from forge.generator.stack import JUNIT_RANGE
from forge.pipeline import run
from forge.planner.plan import build_plan
from forge.rules.engine import RuleError, load_rules
from forge.verification import checks
from forge.verification.http import FetchError, Response
from forge.verification.unverified import items

RUST = {"name": "demo-rust", "project_type": "cli", "agents": ["claude"], "technologies": ["rust"]}
GO = {"name": "demo-go", "project_type": "cli", "agents": ["claude"], "technologies": ["go"]}
JAVA = {"name": "demo-java", "project_type": "library", "agents": ["claude"], "technologies": ["java", "junit"]}
METADATA = """<?xml version="1.0"?><metadata><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId>
<versioning><latest>6.2.0-M1</latest><release>6.2.0-M1</release><versions>
<version>5.14.1</version><version>6.1.3</version><version>6.2.0-M1</version></versions></versioning></metadata>"""


def write(root, files):
    for path, content in files.items():
        target = Path(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


class StackTests(unittest.TestCase):
    def test_each_stack_produces_its_skeleton(self):
        expected = {
            "rust": (RUST, {"Cargo.toml", "src/lib.rs", "src/main.rs"}),
            "go": (GO, {"go.mod", "version.go", "version_test.go", "cmd/demo_go/main.go"}),
            "java": (JAVA, {"pom.xml", "src/main/java/demo_java/Version.java", "src/test/java/demo_java/VersionTest.java"}),
        }
        for label, (spec, paths) in expected.items():
            with self.subTest(label):
                result = run(spec)
                self.assertTrue(result.as_dict()["ok"], result.as_dict()["diagnostics"])
                self.assertLessEqual(paths, set(result.files))
                self.assertFalse({"pyproject.toml", "package.json"} & set(result.files))

    def test_libraries_have_no_entry_point(self):
        files = run(dict(RUST, project_type="library")).files
        self.assertIn("src/lib.rs", files)
        self.assertNotIn("src/main.rs", files)
        self.assertFalse([p for p in run(dict(GO, project_type="library")).files if p.startswith("cmd/")])

    def test_ci_installs_the_pinned_toolchains(self):
        rust = run(RUST).files[".github/workflows/ci.yml"]
        self.assertIn("rustup toolchain install 1.100 --profile minimal --component clippy,rustfmt", rust)
        self.assertIn("cargo clippy --all-targets -- -D warnings", rust)
        go = run(GO).files[".github/workflows/ci.yml"]
        self.assertRegex(go, r"actions/setup-go@[0-9a-f]{40} # v7\.0\.0")
        self.assertIn('go-version: "1.27"', go)
        self.assertIn('test -z "$(gofmt -l .)"', go)
        java = run(JAVA).files[".github/workflows/ci.yml"]
        self.assertRegex(java, r"actions/setup-java@[0-9a-f]{40} # v6\.2\.0")
        self.assertIn("mvn -B verify", java)

    def test_hooks_and_gitignore_follow_the_stack(self):
        files = run(RUST).files
        self.assertIn('command -v cargo >/dev/null 2>&1 || fail "cargo introuvable', files[".githooks/pre-commit"])
        self.assertIn("cargo test", files[".githooks/pre-push"])
        self.assertIn("target/", files[".gitignore"])
        self.assertNotIn("__pycache__", files[".gitignore"])

    def test_java_without_junit_has_no_test_and_says_so(self):
        result = run(dict(JAVA, technologies=["java"]))
        self.assertIn("unknown-command", [x.code for x in result.diagnostics])
        self.assertNotIn("src/test/java/demo_java/VersionTest.java", result.files)
        self.assertNotIn("junit", result.files["pom.xml"])

    def test_junit_version_is_exact_only_when_verified(self):
        self.assertIn("<version>%s</version>" % JUNIT_RANGE, run(JAVA).files["pom.xml"])

        class Verified:
            ok, diagnostics = True, ()

            def package_status(self, ecosystem, package):
                if (ecosystem, package) == ("maven", "org.junit.jupiter:junit-jupiter"):
                    return Status.PASS, {"version": "6.1.3"}
                return Status.NON_VERIFIE, {}

        from forge.generator.render import render_plan
        pom = render_plan(build_plan(JAVA), verification=Verified())["pom.xml"]
        self.assertIn("<version>6.1.3</version>", pom)

    def test_uncovered_stacks_are_non_verifie_and_block_hardened(self):
        for spec in (RUST, GO, JAVA):
            with self.subTest(spec["name"]):
                result = run(spec)
                codes = [x.code for x in result.diagnostics]
                self.assertIn("security-stack-unverified", codes)
                self.assertIn("Dependances et SAST", result.files["SECURITY.md"])
                strict = [i for i in items(result) if i.id.startswith("security-stack-unverified")]
                self.assertEqual([i.critical for i in strict], [False])
                hardened = items(run(dict(spec, security="hardened")))
                self.assertTrue([i for i in hardened if i.id.startswith("security-stack-unverified") and i.critical])
        self.assertNotIn("security-stack-unverified", [x.code for x in run(
            {"name": "demo-py", "project_type": "cli", "agents": ["claude"], "technologies": ["python", "pytest"]}).diagnostics])

    def test_new_profiles_generate(self):
        profiles = {p["id"]: p for p in load_predefined(load_catalog())}
        for pid in ("rust-cli", "go-cli", "java-library"):
            with self.subTest(pid):
                self.assertTrue(run(dict(profiles[pid]["answers"], name="smoke-" + pid)).as_dict()["ok"])

    @unittest.skipUnless(shutil.which("cargo"), "cargo absent : prouve en CI (smoke)")
    def test_rust_skeleton_passes_its_own_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, run(RUST).files)
            env = dict(os.environ, CARGO_TARGET_DIR=os.path.join(tmp, "target"))
            for command in (["cargo", "fmt", "--check"], ["cargo", "test", "--ignore-rust-version", "-q"]):
                done = subprocess.run(command, cwd=tmp, env=env, capture_output=True, text=True, check=False)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    @unittest.skipUnless(shutil.which("go"), "go absent : prouve en CI (smoke)")
    def test_go_skeleton_passes_its_own_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, run(GO).files)
            env = dict(os.environ, GOTOOLCHAIN="local", GOFLAGS="-mod=mod")
            for command in (["gofmt", "-l", "."], ["go", "vet", "./..."], ["go", "test", "./..."]):
                done = subprocess.run(command, cwd=tmp, env=env, capture_output=True, text=True, check=False)
                if "requires go >=" in done.stderr:
                    self.skipTest("Go local plus ancien que la version du profil")
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                if command[0] == "gofmt":
                    self.assertEqual(done.stdout, "")


class MavenTests(unittest.TestCase):
    NAME = "org.junit.jupiter:junit-jupiter"

    def check(self, response=None, wanted=None, error=None):
        def text_fetch(url):
            self.assertEqual(url, "https://repo1.maven.org/maven2/org/junit/jupiter/junit-jupiter/maven-metadata.xml")
            if error:
                raise error
            return response
        return checks.check_package("maven", self.NAME, wanted, text_fetch=text_fetch)

    def test_latest_stable_version_ignores_pre_releases(self):
        result = self.check(Response(200, METADATA))
        self.assertEqual((result.status, result.details["version"]), (Status.PASS, "6.1.3"))
        self.assertEqual(result.details["license"], "NON VERIFIE")

    def test_statuses(self):
        self.assertEqual(self.check(Response(200, METADATA), wanted="5.14.1").status, Status.PASS)
        self.assertEqual(self.check(Response(200, METADATA), wanted="9.9.9").status, Status.FAIL)
        self.assertEqual(self.check(Response(404, None)).status, Status.FAIL)
        self.assertEqual(self.check(error=FetchError("panne")).status, Status.NON_VERIFIE)
        self.assertEqual(self.check(Response(200, "<metadata/>")).status, Status.FAIL)
        self.assertEqual(checks.check_package("maven", self.NAME).status, Status.NON_VERIFIE)  # aucun lecteur texte

    def test_injected_verification_never_reaches_maven_central(self):
        from forge.verification.report import verify_plan

        def fetch(url, payload=None):
            self.assertNotIn("maven", url)
            raise FetchError("hors ligne")
        report = verify_plan(build_plan(JAVA), fetch=fetch, today="2026-11-22", fetch_bytes=lambda u: b"")
        maven = [c for c in report.checks if c.subject.startswith("maven:")]
        self.assertEqual([c.status for c in maven], [Status.NON_VERIFIE, Status.NON_VERIFIE])

    def test_catalog_validates_maven_coordinates(self):
        pattern = __import__("forge.config.catalog", fromlist=["PACKAGE_NAMES"]).PACKAGE_NAMES["maven"]
        for good in ("org.junit.jupiter:junit-jupiter", "com.example:a.b-c_d"):
            self.assertTrue(pattern.fullmatch(good))
        for bad in ("junit", "a:b:c", "../x:y", "a..b:c", ":x", "a b:c"):
            self.assertFalse(pattern.fullmatch(bad), bad)


TECH = {"schema_version": 1, "category": "quality", "technologies": [{
    "id": "my-lint", "name": "Mon lint", "description": "Lint maison.", "ecosystem": None,
    "requires": ["python"], "commands": {"lint": "touch PWNED"}, "docs": "https://example.org/lint"}]}
RULE = {"schema_version": 1, "id": "my-notes", "description": "Notes perso.", "priority": 60,
        "when": {"technologies_any": ["my-lint"]}, "files": [{"path": "docs/NOTES.md", "template": "notes.md.tmpl"}],
        "sections": {"conventions": ["Convention personnelle."]}}
PY = {"name": "demo-py", "project_type": "cli", "agents": ["claude"], "technologies": ["python", "pytest", "my-lint"]}


class LocalCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name, "catalogs")
        patch = mock.patch.dict(os.environ, {"FORGE_LOCAL_CATALOG_DIR": str(self.root)})
        patch.start()
        self.addCleanup(patch.stop)

    def put(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
        return target

    def full(self):
        self.put("technologies/mine.json", TECH)
        self.put("rules/mine.json", RULE)
        self.put("templates/notes.md.tmpl", "# Notes de {{ project.name }}\n")

    def test_absent_directory_adds_nothing(self):
        catalog = load_catalog()
        self.assertEqual(catalog.local["technologies"], [])
        self.assertFalse([r for r in load_rules(catalog) if r.source == "local"])

    def test_local_technology_and_rule_are_used_with_warnings(self):
        self.full()
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            result = run(PY)
        finally:
            os.chdir(cwd)
        self.assertTrue(result.as_dict()["ok"], result.as_dict()["diagnostics"])
        self.assertEqual(result.files["docs/NOTES.md"], "# Notes de demo-py\n")
        self.assertIn("touch PWNED", result.files[".github/workflows/ci.yml"])
        self.assertIn("Convention personnelle.", result.files["AGENTS.md"])
        codes = {x.code for x in result.diagnostics}
        self.assertLessEqual({"local-technology", "local-rule"}, codes)
        self.assertFalse(Path(self.tmp.name, "PWNED").exists())  # jamais execute par Forge

    def test_nothing_built_in_can_be_replaced(self):
        cases = {
            "technologie existante": ("technologies/x.json", dict(TECH, technologies=[dict(TECH["technologies"][0], id="pytest")])),
            "categorie inconnue": ("technologies/x.json", dict(TECH, category="magic")),
            "reference inconnue": ("technologies/x.json", dict(TECH, technologies=[dict(TECH["technologies"][0], requires=["cobol"])])),
        }
        for label, (path, content) in cases.items():
            with self.subTest(label):
                target = self.put(path, content)
                with self.assertRaises(CatalogError):
                    load_catalog()
                target.unlink()

    def test_local_rules_cannot_override_or_collide(self):
        self.put("technologies/mine.json", TECH)
        self.put("templates/notes.md.tmpl", "x\n")
        self.put("templates/ci.tmpl", "x\n")
        for label, rule in (("override", dict(RULE, files=[dict(RULE["files"][0], override=True)])),
                            ("id de Forge", dict(RULE, id="base")),
                            ("template hors dossier", dict(RULE, files=[{"path": "x.md", "template": "../../x.tmpl"}]))):
            with self.subTest(label):
                self.put("rules/mine.json", rule)
                with self.assertRaises(RuleError):
                    load_rules(load_catalog())
        self.put("rules/mine.json", dict(RULE, files=[{"path": ".github/workflows/ci.yml", "template": "ci.tmpl"}]))
        self.assertIn("file-conflict", [x.code for x in build_plan(PY).diagnostics])

    def test_bounds_and_links_are_enforced(self):
        self.put("technologies/big.json", " " * (local.MAX_JSON_BYTES + 1))
        with self.assertRaisesRegex(CatalogError, "depasse"):
            load_catalog()
        shutil.rmtree(self.root / "technologies")
        for index in range(local.MAX_FILES + 1):
            self.put("technologies/t%02d.json" % index, dict(TECH, technologies=[]))
        with self.assertRaisesRegex(CatalogError, "plus de"):
            load_catalog()
        shutil.rmtree(self.root / "technologies")
        outside = Path(self.tmp.name, "outside.json")
        outside.write_text(json.dumps(TECH))
        (self.root / "technologies").mkdir()
        os.symlink(outside, self.root / "technologies" / "link.json")
        with self.assertRaisesRegex(CatalogError, "lien"):
            load_catalog()
        shutil.rmtree(self.root / "technologies")
        os.symlink(Path(self.tmp.name), self.root / "technologies")
        with self.assertRaisesRegex(CatalogError, "lien"):
            load_catalog()

    def test_template_bounds(self):
        self.put("technologies/mine.json", TECH)
        self.put("rules/mine.json", RULE)
        self.put("templates/notes.md.tmpl", "x" * (local.MAX_TEMPLATE_BYTES + 1))
        with self.assertRaisesRegex(RuleError, "depasse"):
            load_rules(load_catalog())
        self.put("templates/notes.md.tmpl", "x\n")
        for index in range(local.MAX_TEMPLATES):
            self.put("templates/extra/%02d.tmpl" % index, "x\n")
        with self.assertRaisesRegex(RuleError, "templates locaux"):
            load_rules(load_catalog())

    def test_explicit_catalog_directory_ignores_local_files(self):
        self.full()
        from forge import CATALOGS_DIR
        self.assertNotIn("my-lint", load_catalog(CATALOGS_DIR / "technologies").technologies)
        self.assertIn("my-lint", load_catalog().technologies)

    def test_web_and_cli_report_the_local_catalog(self):
        self.full()
        status, body, _, _ = web.catalog_payload()
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["local"]["technologies"], ["my-lint"])
        self.assertEqual(data["local"]["rules"], ["my-notes"])
        self.assertEqual([t["source"] for t in data["technologies"] if t["id"] == "my-lint"], ["local"])
        from forge.__main__ import main
        with mock.patch("sys.stdout"):
            self.assertEqual(main(["local-catalog"]), 0)
        self.put("technologies/broken.json", "{")
        status, body, _, _ = web.catalog_payload()
        self.assertEqual(status, 422)
        self.assertIn("broken.json", json.loads(body)["error"])
        with mock.patch("sys.stdout"):
            self.assertEqual(main(["local-catalog"]), 2)


if __name__ == "__main__":
    unittest.main()
