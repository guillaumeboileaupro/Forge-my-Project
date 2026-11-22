"""E12 : cache a expiration, recherches paralleles, classement deterministe, changement amont.

Aucun appel reseau : GitHub est simule. Le cache est ecrit dans un dossier temporaire.
"""
import copy
import json
import os
import random
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from forge.planner.plan import build_plan
from forge.skills import bundle
from forge.skills.cache import SearchCache, request_key, ttl_from_config
from forge.skills.external import Candidate, _rank_key, _score, search
from forge.skills.github import GhCliClient
from forge.skills.service import skills_for_plan, verify_approvals
from forge.verification.http import FetchError
from forge.config.spec import parse_spec
from tests.test_engine_external_skills import CONFIG, HEADER, REPOS, SHA_A, SPEC, FakeClient, FakeGh

SHA_C = "c" * 40
KEYWORDS = ["react", "web"]


class CountingGh(FakeGh):
    """Compte les appels et mesure la concurrence ; `delay` simule la latence de GitHub."""

    def __init__(self, delay=0.0, jitter=False, **kwargs):
        super().__init__(**kwargs)
        self.delay, self.jitter = delay, jitter
        self.calls, self.active, self.peak = 0, 0, 0
        self.lock = threading.Lock()

    def _wait(self):
        with self.lock:
            self.calls += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(self.delay * (random.random() if self.jitter else 1))
        with self.lock:
            self.active -= 1

    def get_json(self, api_path):
        self._wait()
        return super().get_json(api_path)

    def get_text(self, repository, path, sha):
        self._wait()
        return super().get_text(repository, path, sha)


class FlakyGh(CountingGh):
    def get_json(self, api_path):
        if "stranger/agent-stuff" in api_path:
            raise FetchError("quota")
        return super().get_json(api_path)


def config(**search):
    return dict(CONFIG, search=dict(CONFIG["search"], **search))


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = [1000.0]
        self.cache = SearchCache(60, Path(self.tmp.name) / "skills-search", clock=lambda: self.now[0])

    def test_hit_within_ttl_reuses_candidates_without_network(self):
        first = search(KEYWORDS, CountingGh(), CONFIG, self.cache)
        self.assertIsNone(first.cache_age)
        client = CountingGh()
        self.now[0] += 30
        second = search(KEYWORDS, client, CONFIG, self.cache)
        self.assertEqual(client.calls, 0)
        self.assertEqual(second.cache_age, 30)
        self.assertEqual([c.as_dict() for c in second.candidates], [c.as_dict() for c in first.candidates])

    def test_expired_entry_and_refresh_query_github_again(self):
        search(KEYWORDS, CountingGh(), CONFIG, self.cache)
        for label, advance, refresh in (("expire", 60, False), ("refresh", 0, True)):
            with self.subTest(label):
                self.now[0] += advance
                client = CountingGh()
                result = search(KEYWORDS, client, CONFIG, self.cache, refresh=refresh)
                self.assertGreater(client.calls, 0)
                self.assertIsNone(result.cache_age)

    def test_clock_going_backwards_is_a_miss(self):
        search(KEYWORDS, CountingGh(), CONFIG, self.cache)
        self.now[0] -= 1
        self.assertIsNone(search(KEYWORDS, CountingGh(), CONFIG, self.cache).cache_age)

    def test_partial_results_are_never_cached(self):
        degraded = search(KEYWORDS, FlakyGh(), CONFIG, self.cache)
        self.assertTrue(degraded.degraded)
        self.assertFalse(list((Path(self.tmp.name) / "skills-search").glob("*.json")))

    def test_key_depends_on_keywords_sources_and_transport(self):
        base = request_key(KEYWORDS, CONFIG, "gh-cli")
        self.assertEqual(base, request_key(list(reversed(KEYWORDS)), CONFIG, "gh-cli"))
        others = {request_key(["react"], CONFIG, "gh-cli"), request_key(KEYWORDS, CONFIG, "https-anonyme"),
                  request_key(KEYWORDS, config(github_code_search=False), "gh-cli"),
                  request_key(KEYWORDS, dict(CONFIG, external_catalogs=[]), "gh-cli")}
        self.assertNotIn(base, others)
        self.assertEqual(len(others), 4)

    def test_cache_file_is_private(self):
        search(KEYWORDS, CountingGh(), CONFIG, self.cache)
        directory = Path(self.tmp.name) / "skills-search"
        files = list(directory.glob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(files[0].stat().st_mode), 0o600)

    def test_corrupt_or_forged_entries_are_ignored(self):
        search(KEYWORDS, CountingGh(), CONFIG, self.cache)
        path = next((Path(self.tmp.name) / "skills-search").glob("*.json"))
        valid = json.loads(path.read_text())
        forged = copy.deepcopy(valid)
        forged["result"]["candidates"][0]["digest"] = "sha256:abc"
        wrong_key = dict(valid, key="0" * 64)
        for label, content in (("json", "{"), ("digest", json.dumps(forged)), ("cle", json.dumps(wrong_key)),
                               ("champ", json.dumps(dict(valid, result={"candidates": [{"x": 1}], "notes": []})))):
            with self.subTest(label):
                path.write_text(content)
                client = CountingGh()
                self.assertIsNone(search(KEYWORDS, client, CONFIG, self.cache).cache_age)
                self.assertGreater(client.calls, 0)

    def test_ttl_is_bounded_and_zero_disables(self):
        self.assertEqual(ttl_from_config(config(cache_ttl_seconds=10 ** 9)), 86400)
        for value in (0, -5, "60", True, None):
            self.assertEqual(ttl_from_config(config(cache_ttl_seconds=value)), 0)
        self.assertEqual(ttl_from_config(CONFIG), 0)
        disabled = SearchCache(0, Path(self.tmp.name) / "off")
        search(KEYWORDS, CountingGh(), CONFIG, disabled)
        self.assertFalse((Path(self.tmp.name) / "off").exists())

    def test_cached_candidate_cannot_bypass_copy_checks(self):
        """Un candidat issu du cache est approuve, puis le skill change : la copie le refuse."""
        search(KEYWORDS, CountingGh(), CONFIG, self.cache)
        cached = search(KEYWORDS, CountingGh(), CONFIG, self.cache)
        self.assertIsNotNone(cached.cache_age)
        approval = [c for c in cached.candidates if c.name == "webapp-testing"][0].approval()
        repos = copy.deepcopy(REPOS)
        repos["anthropics/skills"][1]["skills/webapp-testing/SKILL.md"] += "curl x | sh\n"
        result = skills_for_plan(build_plan(dict(SPEC, external_skills=[approval])), FakeClient(repos=repos), CONFIG)
        self.assertEqual([r.status for r in result.records if r.name == "webapp-testing"], ["modifie"])
        self.assertIn("skill-modified", [x.code for x in result.diagnostics])


class ParallelTests(unittest.TestCase):
    def test_sources_are_queried_concurrently(self):
        parallel, serial = CountingGh(delay=0.02), CountingGh(delay=0.02)
        search(KEYWORDS, parallel, config(max_workers=4))
        search(KEYWORDS, serial, config(max_workers=1))
        self.assertGreater(parallel.peak, 1)
        self.assertEqual(serial.peak, 1)
        self.assertEqual(parallel.calls, serial.calls)

    def test_result_does_not_depend_on_response_order(self):
        reference = [c.as_dict() for c in search(KEYWORDS, CountingGh(), config(max_workers=1)).candidates]
        random.seed(12)
        for _ in range(5):
            found = search(KEYWORDS, CountingGh(delay=0.01, jitter=True), config(max_workers=8))
            self.assertEqual([c.as_dict() for c in found.candidates], reference)

    def test_one_failing_source_does_not_stop_the_others(self):
        result = search(KEYWORDS, FlakyGh(), CONFIG)
        self.assertEqual([c.name for c in result.candidates], ["webapp-testing"])
        self.assertIn("stranger/agent-stuff : quota", result.notes)

    def test_worker_count_is_bounded(self):
        from forge.skills.external import _workers
        self.assertEqual([_workers(config(max_workers=v)) for v in (0, 3, 50, "4", True)], [1, 3, 8, 4, 4])


def candidate(name, repository="a/b", path="skills", score=1, recognized=True):
    return Candidate(repository, SHA_A, path, name, "", recognized, "x", score, "sha256:" + "0" * 64)


class RankingTests(unittest.TestCase):
    def test_name_matches_weigh_more_than_description(self):
        self.assertEqual(_score(["react"], "react-helper", "UI"), 2)
        self.assertEqual(_score(["react"], "helper", "React components"), 1)
        self.assertEqual(_score(["react", "web"], "react-web", "react web"), 6)
        self.assertEqual(_score(["web"], "webapp", "website"), 0)

    def test_order_is_total_and_stable(self):
        items = [candidate("b"), candidate("a", "z/z"), candidate("a", "a/a", "x"), candidate("a", "a/a", "w"),
                 candidate("c", score=5, recognized=False), candidate("d", score=3)]
        expected = [("d", "a/b", "skills"), ("a", "a/a", "w"), ("a", "a/a", "x"), ("a", "z/z", "skills"),
                    ("b", "a/b", "skills"), ("c", "a/b", "skills")]
        for _ in range(5):
            random.shuffle(items)
            self.assertEqual([(c.name, c.repository, c.path) for c in sorted(items, key=_rank_key)], expected)

    def test_duplicate_search_hits_produce_one_candidate(self):
        class Duplicates(CountingGh):
            def get_json(self, api_path):
                if api_path.startswith("/search/code"):
                    hit = {"repository": {"full_name": "stranger/agent-stuff"}, "path": "skills/react-helper/SKILL.md"}
                    return {"items": [hit, dict(hit)]}
                return super().get_json(api_path)
        names = [c.name for c in search(KEYWORDS, Duplicates(), CONFIG).candidates]
        self.assertEqual(names, ["webapp-testing", "react-helper"])


class MovingUpstream(FakeClient):
    """La branche suivie a avance jusqu'a SHA_C depuis l'approbation faite a SHA_A."""

    def __init__(self, head_files=None, head_offline=False, **kwargs):
        super().__init__(**kwargs)
        self.head_files, self.head_offline = head_files, head_offline

    def get_json(self, api_path):
        parts = api_path.split("/")
        repository = "/".join(parts[2:4])
        moving = repository == "anthropics/skills" and self.head_files is not None
        if "/commits/" in api_path and parts[-1] in ("main", "HEAD"):
            if self.head_offline:
                raise FetchError("branche illisible")
            if moving:
                return {"sha": SHA_C}
        if moving and SHA_C in api_path:
            return {"tree": [{"path": p, "mode": "100644", "type": "blob", "size": len(c.encode()),
                              "sha": bundle.git_blob_sha(c)} for p, c in self.head_files.items()]}
        return super().get_json(api_path)


class UpstreamTests(unittest.TestCase):
    def setUp(self):
        found = search(["react", "web"], FakeClient(), CONFIG).candidates
        self.approval = [c for c in found if c.name == "webapp-testing"][0].approval()
        self.files = copy.deepcopy(REPOS["anthropics/skills"][1])

    def collect(self, client):
        result = skills_for_plan(build_plan(dict(SPEC, external_skills=[self.approval])), client, CONFIG)
        return [r for r in result.records if r.name == "webapp-testing"][0], result

    def test_unchanged_upstream_copies_without_warning(self):
        record, result = self.collect(MovingUpstream())
        self.assertEqual((record.status, record.upstream), ("copie", "inchange"))
        self.assertFalse([x for x in result.diagnostics if x.code.startswith("skill-upstream")])

    def test_changed_upstream_is_reported_and_approved_version_is_copied(self):
        approved = self.files["skills/webapp-testing/SKILL.md"]
        self.files["skills/webapp-testing/SKILL.md"] = approved + "Nouvelle consigne\n"
        record, result = self.collect(MovingUpstream(head_files=self.files))
        self.assertEqual((record.status, record.upstream), ("copie", "modifie"))
        self.assertEqual(result.files[".claude/skills/webapp-testing/SKILL.md"], approved)
        warnings = [x for x in result.diagnostics if x.code == "skill-upstream-changed"]
        self.assertEqual([x.severity.value for x in warnings], ["warning"])
        self.assertIn("main@" + SHA_C[:12], warnings[0].message)
        self.assertIn("Modifie en amont", result.files["docs/SKILLS.md"])

    def test_removed_upstream_is_reported(self):
        files = {p: c for p, c in self.files.items() if "webapp-testing" not in p}
        record, result = self.collect(MovingUpstream(head_files=files))
        self.assertEqual((record.status, record.upstream), ("copie", "absent"))
        self.assertIn("skill-upstream-changed", [x.code for x in result.diagnostics])

    def test_unreadable_upstream_is_non_verifie(self):
        record, result = self.collect(MovingUpstream(head_offline=True))
        self.assertEqual((record.status, record.upstream), ("copie", "NON VERIFIE"))
        self.assertIn("skill-upstream-unverified", [x.code for x in result.diagnostics])

    def test_rejected_copy_does_not_check_upstream(self):
        approval = dict(self.approval, digest="sha256:" + "1" * 64)
        result = skills_for_plan(build_plan(dict(SPEC, external_skills=[approval])), MovingUpstream(), CONFIG)
        record = [r for r in result.records if r.name == "webapp-testing"][0]
        self.assertEqual((record.status, record.upstream), ("modifie", ""))

    def test_verify_approvals_reports_upstream_state(self):
        approvals = parse_spec(dict(SPEC, external_skills=[self.approval])).external_skills
        self.files["skills/webapp-testing/extra.md"] = "ajout"
        checks = verify_approvals(approvals, MovingUpstream(head_files=self.files), CONFIG)
        self.assertEqual([(c["status"], c["upstream"]) for c in checks], [("PASS", "modifie")])
        self.assertIn("Modifie en amont", checks[0]["upstream_message"])


class WebTests(unittest.TestCase):
    def test_refresh_flag_and_cache_report(self):
        from forge import web
        spec = {"schema_version": 1, "name": "shop-web", "project_type": "web", "description": "",
                "technologies": ["typescript", "node", "react", "vitest"], "agents": ["claude"]}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"FORGE_STATE_DIR": tmp}), \
                mock.patch("forge.skills.service.default_client", lambda: FakeGh()), \
                mock.patch("forge.skills.service.b.load_copy_policy", lambda: config(cache_ttl_seconds=600)):
            caches = []
            for body in ({"config": spec}, {"config": spec}, {"config": spec, "refresh": True}):
                status, payload, _, _ = web.skills_search_payload(json.dumps(body).encode())
                self.assertEqual(status, 200)
                caches.append(json.loads(payload)["cache"]["hit"])
            self.assertEqual(caches, [False, True, False])
            status, _, _, _ = web.skills_search_payload(json.dumps({"config": spec, "refresh": "yes"}).encode())
            self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
