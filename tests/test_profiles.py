import http.client
import json
import os
import shutil
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from forge.config.answers import FORMAT, AnswersError, envelope, parse_answers, unwrap
from forge.config.catalog import load_catalog
from forge.config.profiles import (MAX_PROFILES, ProfileError, ProfileNotFound, ProfileStore, default_path,
                                   load_predefined)
from forge.pipeline import run
from server import Handler, ThreadingHTTPServer

CATALOG = load_catalog()
ANSWERS = {
    "name": "stock-api", "description": "API de stock", "project_type": "api", "architecture": "",
    "technologies": ["python", "fastapi", "pytest"], "versions": {"python": "3.12"},
    "agents": ["codex"], "security": "strict", "options": {"mcp": False},
}


class AnswersTests(unittest.TestCase):
    def test_partial_answers_are_accepted_and_normalised(self):
        result = parse_answers({"name": "mon-", "technologies": [], "agents": []}, CATALOG)
        self.assertEqual(result["name"], "mon-")
        self.assertEqual(result["project_type"], "library")
        self.assertEqual(result["security"], "strict")
        self.assertEqual(result["external_skills"], [])
        full = parse_answers(dict(ANSWERS, agents=["claude", "codex"]), CATALOG)
        self.assertEqual(full["agents"], ["codex", "claude"])

    def test_envelope_round_trip(self):
        exported = envelope(parse_answers(ANSWERS, CATALOG))
        self.assertEqual(exported["format"], FORMAT)
        text = json.dumps(exported)
        self.assertEqual(parse_answers(unwrap(json.loads(text)), CATALOG), parse_answers(ANSWERS, CATALOG))
        self.assertEqual(unwrap(dict(ANSWERS, schema_version=1))["name"], "stock-api")

    def test_invalid_documents_are_rejected_with_clear_messages(self):
        cases = {
            "Format de fichier inconnu": {"format": "autre", "schema_version": 1, "answers": ANSWERS},
            "Version de schema": {"format": FORMAT, "schema_version": 2, "answers": ANSWERS},
            "Champ inconnu dans l'enveloppe": {"format": FORMAT, "schema_version": 1, "answers": ANSWERS, "run": "x"},
        }
        for message, document in cases.items():
            with self.assertRaisesRegex(AnswersError, message):
                unwrap(document)
        with self.assertRaises(AnswersError):
            unwrap([ANSWERS])

    def test_incompatible_answers_are_rejected(self):
        cases = [
            ({"shell": "rm -rf /"}, "Champ inconnu"),
            ({"name": "Mon Projet"}, "Nom de projet invalide"),
            ({"technologies": ["python", "cobol"]}, "absente du catalogue"),
            ({"technologies": ["python", "flask", "django"]}, "incompatible"),
            ({"technologies": ["vitest"]}, "requiert"),
            ({"versions": {"python": "2.7"}}, "non supporte"),
            ({"agents": ["gpt"]}, "Agent inconnu"),
            ({"project_type": "jeu"}, "project_type"),
            ({"options": {"mcp": "oui"}}, "booleennes"),
            ({"technologies": "python"}, "liste"),
            ({"description": "x" * 2001}, "description"),
        ]
        for override, message in cases:
            with self.assertRaisesRegex(AnswersError, message, msg=str(override)):
                parse_answers(dict(ANSWERS, **override), CATALOG)

    def test_text_is_data_only(self):
        result = parse_answers(dict(ANSWERS, description="{{ secret }} <script>alert(1)</script>"), CATALOG)
        self.assertEqual(result["description"], "{{ secret }} <script>alert(1)</script>")


class PredefinedProfilesTests(unittest.TestCase):
    def test_each_predefined_profile_generates_a_valid_plan(self):
        profiles = load_predefined(CATALOG)
        self.assertGreaterEqual(len(profiles), 6)
        ids = {p["id"] for p in profiles}
        self.assertTrue({"python-api-fastapi", "typescript-web-react"} <= ids)
        for profile in profiles:
            self.assertNotIn("name", profile["answers"])
            result = run(dict(profile["answers"], name="demo-profile"))
            self.assertTrue(result.as_dict()["ok"], profile["id"])

    def test_invalid_predefined_profile_is_rejected(self):
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory)
        (directory / "bad.json").write_text(json.dumps({"schema_version": 1, "id": "bad", "label": "x",
                                                        "answers": {"technologies": ["cobol"]}}), encoding="utf-8")
        with self.assertRaises(ProfileError):
            load_predefined(CATALOG, directory)


class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.path = self.dir / "config" / "profiles.json"
        self.store = ProfileStore(CATALOG, self.path, reserved={"python-cli"})

    def profile(self, **override):
        return dict({"label": "Mon API", "description": "Pour mes services", "answers": ANSWERS}, **override)

    def test_create_update_delete(self):
        created = self.store.create(self.profile())
        self.assertEqual(created["id"], "mon-api")
        self.assertNotIn("name", created["answers"])
        self.assertNotIn("description", created["answers"])
        second = self.store.create(self.profile())
        self.assertEqual(second["id"], "mon-api-2")
        updated = self.store.update("mon-api", self.profile(label="Mon API v2", answers=dict(ANSWERS, security="hardened")))
        self.assertEqual(updated["answers"]["security"], "hardened")
        self.assertEqual([p["label"] for p in self.store.list()], ["Mon API v2", "Mon API"])
        self.store.delete("mon-api")
        self.assertEqual([p["id"] for p in self.store.list()], ["mon-api-2"])

    def test_file_is_private_and_written_atomically(self):
        self.store.create(self.profile())
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["profiles.json"])
        self.assertEqual(json.loads(self.path.read_text())["schema_version"], 1)

    def test_errors(self):
        with self.assertRaises(ProfileNotFound):
            self.store.update("absent", self.profile())
        with self.assertRaises(ProfileNotFound):
            self.store.delete("absent")
        with self.assertRaisesRegex(ProfileError, "predefinis"):
            self.store.delete("python-cli")
        reserved = self.store.create(self.profile(label="python cli"))
        self.assertEqual(reserved["id"], "python-cli-2")
        for bad in (self.profile(label=""), self.profile(label="x" * 61), self.profile(answers={"technologies": ["cobol"]}),
                    self.profile(extra=1), {"label": "x"}):
            with self.assertRaises(ProfileError, msg=str(bad)):
                self.store.create(bad)

    def test_corrupted_or_unsafe_file_is_never_overwritten(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{pas du json", encoding="utf-8")
        with self.assertRaisesRegex(ProfileError, "illisible"):
            self.store.create(self.profile())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{pas du json")
        self.path.unlink()
        target = self.dir / "elsewhere.json"
        target.write_text(json.dumps({"schema_version": 1, "profiles": []}), encoding="utf-8")
        self.path.symlink_to(target)
        with self.assertRaisesRegex(ProfileError, "lien"):
            self.store.list()

    def test_limit(self):
        with mock.patch("forge.config.profiles.MAX_PROFILES", 2):
            self.store.create(self.profile())
            self.store.create(self.profile())
            with self.assertRaisesRegex(ProfileError, "maximal"):
                self.store.create(self.profile())
        self.assertGreater(MAX_PROFILES, 2)

    def test_default_path_respects_environment(self):
        with mock.patch.dict(os.environ, {"FORGE_PROFILES_FILE": "/tmp/x.json"}):
            self.assertEqual(default_path(), Path("/tmp/x.json"))
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/cfg"}, clear=True):
            self.assertEqual(default_path(), Path("/cfg/forge-my-project/profiles.json"))


class ProfileApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.env = mock.patch.dict(os.environ, {"FORGE_PROFILES_FILE": os.path.join(cls.dir, "profiles.json")})
        cls.env.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.env.stop()
        shutil.rmtree(cls.dir)

    def request(self, method, path, payload=None, headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        body = None if payload is None else json.dumps(payload)
        base = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=body, headers=dict(base, **(headers or {})))
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, json.loads(data) if data.startswith(b"{") else data

    def test_crud_over_http(self):
        status, data = self.request("GET", "/api/profiles")
        self.assertEqual(status, 200)
        self.assertTrue(data["predefined"])
        self.assertTrue(data["storage"].endswith("profiles.json"))
        profile = {"label": "Equipe data", "description": "", "answers": ANSWERS}
        status, data = self.request("POST", "/api/profiles", profile)
        self.assertEqual(status, 201)
        profile_id = data["profile"]["id"]
        status, data = self.request("PUT", "/api/profiles/" + profile_id, dict(profile, label="Equipe data v2"))
        self.assertEqual((status, data["profile"]["label"]), (200, "Equipe data v2"))
        self.assertEqual(self.request("GET", "/api/profiles")[1]["custom"][0]["label"], "Equipe data v2")
        status, _ = self.request("DELETE", "/api/profiles/" + profile_id, headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.request("DELETE", "/api/profiles/" + profile_id)[0], 200)
        self.assertEqual(self.request("DELETE", "/api/profiles/" + profile_id)[0], 404)
        self.assertEqual(self.request("PUT", "/api/profiles/python-cli", profile)[0], 400)
        self.assertEqual(self.request("DELETE", "/api/profiles/../etc")[0], 404)
        self.assertEqual(self.request("GET", "/api/profiles", headers={"Host": "evil.example"})[0], 403)

    def test_invalid_profile_payloads(self):
        for payload in ({"label": "x"}, {"label": "x", "description": "", "answers": {"technologies": ["cobol"]}}):
            status, data = self.request("POST", "/api/profiles", payload)
            self.assertEqual(status, 400)
            self.assertFalse(data["ok"])

    def test_validate_endpoint(self):
        status, data = self.request("POST", "/api/answers/validate", {"document": envelope(ANSWERS)})
        self.assertEqual(status, 200)
        self.assertEqual(data["answers"]["technologies"], ["python", "fastapi", "pytest"])
        self.assertEqual(data["export"]["format"], FORMAT)
        status, data = self.request("POST", "/api/answers/validate", {"document": dict(ANSWERS, technologies=["cobol"])})
        self.assertEqual(status, 400)
        self.assertIn("cobol", data["error"])
        self.assertEqual(self.request("POST", "/api/answers/validate", {"document": ANSWERS, "x": 1})[0], 400)

    def test_imported_answers_still_generate_with_the_engine(self):
        _, data = self.request("POST", "/api/answers/validate", {"document": envelope(ANSWERS)})
        status, plan = self.request("POST", "/api/plan", {"config": dict(data["answers"], schema_version=1)})
        self.assertEqual(status, 200)
        self.assertIn("AGENTS.md", plan["contents"])


if __name__ == "__main__":
    unittest.main()
