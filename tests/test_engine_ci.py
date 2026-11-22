import json
import unittest

from forge.config.catalog import load_catalog
from forge.config.spec import parse_spec
from forge.diagnostics import Status
from forge.generator.stack import CiCatalogError, load_ci_catalog
from forge.pipeline import run
from forge.rules.engine import RuleError, load_rules, matches, parse_rule
from forge.verification import npm_peers, semver
from forge.verification.http import FetchError, Response

TS = {"name": "shop-web", "project_type": "web", "agents": ["codex"],
      "technologies": ["typescript", "node", "vitest", "eslint", "npm-audit"]}


class SemverTests(unittest.TestCase):
    def test_ranges(self):
        cases = [
            ("6.0.3", ">=4.8.4 <6.1.0", True), ("7.0.2", ">=4.8.4 <6.1.0", False),
            ("10.1.0", "^8.57.0 || ^9.0.0 || ^10.0.0", True), ("0.2.9", "^0.2.3", True), ("0.3.0", "^0.2.3", False),
            ("1.2.9", "~1.2.3", True), ("1.3.0", "~1.2.3", False), ("4.1.0", "4.x", True), ("5.0.0", "4.x", False),
            ("2.0.0", "1.2.3 - 2.3.4", True), ("2.4.0", "1.2.3 - 2.3.4", False), ("1.0.0", "*", True),
            ("5.1.0", "^5.0.0-0", True), ("19.2.0", "19.2.0", True), ("19.2.1", "19.2.0", False),
            ("1.0.0-beta.1", "*", False),
        ]
        for version, range_text, expected in cases:
            self.assertEqual(semver.satisfies(version, range_text), expected, (version, range_text))

    def test_unknown_range_is_an_error(self):
        with self.assertRaises(ValueError):
            semver.satisfies("1.0.0", "latest")

    def test_stable_versions_skip_prereleases_and_deprecated(self):
        meta = {"versions": {"1.0.0": {}, "2.0.0-rc.1": {}, "1.5.0": {"deprecated": "x"}, "1.2.0": {}}}
        self.assertEqual(semver.stable_versions(meta), ["1.2.0", "1.0.0"])


def registry(packages):
    """packages : {nom: {version: peerDependencies}} ; la plus haute version est 'latest'."""
    def fetch(url, payload=None):
        name = url.split("registry.npmjs.org/", 1)[1].replace("%2F", "/")
        if name == "offline":
            raise FetchError("hors ligne")
        if name not in packages:
            return Response(404, None)
        versions = {v: {"peerDependencies": peers} for v, peers in packages[name].items()}
        latest = max(versions, key=semver.parse_stable)
        return Response(200, {"dist-tags": {"latest": latest}, "versions": versions})
    return fetch


class PeerResolutionTests(unittest.TestCase):
    def test_downgrades_peer_to_satisfy_dependent(self):
        fetch = registry({
            "typescript": {"7.0.2": {}, "6.0.3": {}, "5.9.0": {}},
            "typescript-eslint": {"8.72.2": {"typescript": ">=4.8.4 <6.1.0"}},
        })
        chosen, check = npm_peers.resolve([("typescript", None), ("typescript-eslint", None)], fetch)
        self.assertEqual(chosen, {"typescript": "6.0.3", "typescript-eslint": "8.72.2"})
        self.assertEqual(check.status, Status.PASS)
        self.assertIn("typescript 6.0.3 (derniere : 7.0.2)", check.message)

    def test_unsatisfiable_or_unreadable_constraints(self):
        fetch = registry({"a": {"1.0.0": {"b": "^2.0.0"}}, "b": {"1.0.0": {}}})
        self.assertEqual(npm_peers.resolve([("a", None), ("b", None)], fetch)[1].status, Status.FAIL)
        self.assertEqual(npm_peers.resolve([("a", None), ("b", "1.0.0")], fetch)[1].status, Status.FAIL)
        odd = registry({"a": {"1.0.0": {"b": "workspace:*"}}, "b": {"1.0.0": {}}})
        self.assertEqual(npm_peers.resolve([("a", None), ("b", None)], odd)[1].status, Status.NON_VERIFIE)

    def test_missing_packages_are_left_to_registry_checks(self):
        chosen, check = npm_peers.resolve([("offline", None), ("ghost", None)], registry({}))
        self.assertEqual((chosen, check), ({}, None))


class RuleExtensionTests(unittest.TestCase):
    def test_technologies_none_and_package_placeholder(self):
        catalog = load_catalog()
        rules = {r.id: r for r in load_rules(catalog)}
        spec = parse_spec(TS)
        self.assertTrue(matches(rules["scaffold-typescript"], spec, {"typescript", "node"}))
        self.assertFalse(matches(rules["scaffold-node"], spec, {"typescript", "node"}))
        self.assertTrue(matches(rules["scaffold-node"], spec, {"javascript", "node"}))
        for bad_path in ("src/{package}/../x.py", "{other}/x", "src/{package"):
            raw = {"schema_version": 1, "id": "x", "description": "x",
                   "files": [{"path": bad_path, "template": "stack/gitignore.tmpl"}]}
            with self.assertRaises(RuleError, msg=bad_path):
                parse_rule(raw, catalog)

    def test_package_placeholder_is_rendered(self):
        files = run({"name": "my-lib", "project_type": "library", "agents": ["codex"],
                     "technologies": ["python", "unittest"]}).files
        self.assertIn("src/my_lib/__init__.py", files)
        self.assertIn('import_module("my_lib")', files["tests/test_smoke.py"])


class CiCatalogTests(unittest.TestCase):
    def test_repository_catalog_is_pinned(self):
        actions = load_ci_catalog()["actions"]
        self.assertEqual(set(actions), {"checkout", "setup_python", "setup_node", "setup_go", "setup_java", "upload_artifact"})

    def test_rejects_unpinned_actions(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "actions.json")
            data = load_ci_catalog()
            data["actions"]["checkout"]["sha"] = "v4"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CiCatalogError):
                load_ci_catalog(path)


if __name__ == "__main__":
    unittest.main()
