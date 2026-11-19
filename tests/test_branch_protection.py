"""E09 : assistant de protection GitHub, sans mutation distante."""
import json
import unittest
from unittest import mock

from forge.github.branch_protection import ATTRIBUTION_CHECK, prepare
from forge.verification.http import FetchError
from forge import web


SHA = "a" * 40
REPOSITORY = "owner/project"


class FakeClient:
    def __init__(self, responses=None, authenticated=True):
        self.responses = responses or {}
        self.is_authenticated = authenticated
        self.calls = []

    def authenticated(self):
        return self.is_authenticated

    def get_json(self, path):
        self.calls.append(("GET", path))
        value = self.responses.get(path)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise AssertionError("appel GET inattendu : " + path)
        return value


def responses(checks=("python", ATTRIBUTION_CHECK), permissions=None, protected=False):
    base = "/repos/" + REPOSITORY
    data = {
        base: {"permissions": permissions or {"admin": True, "maintain": True, "push": True}},
        base + "/branches/main": {"commit": {"sha": SHA}},
        base + "/commits/%s/check-runs?per_page=100" % SHA: {"check_runs": [
            x if isinstance(x, dict) else {"name": x, "conclusion": "success"} for x in checks]},
        base + "/branches/main/protection": {"required_status_checks": {}},
    }
    if not protected:
        data[base + "/branches/main/protection"] = FetchError("gh api a echoue HTTP 404 (code 1)")
    return data


class BranchProtectionTest(unittest.TestCase):
    def test_valid_repository_generates_manual_command_from_real_checks(self):
        client = FakeClient(responses())
        result = prepare(REPOSITORY, "main", client)
        self.assertTrue(result["manual_only"])
        self.assertTrue(result["attribution_verified"])
        self.assertEqual(result["required_checks"], [ATTRIBUTION_CHECK, "python"])
        self.assertIn('gh api --method PUT "repos/owner/project/branches/main/protection"', result["command"])
        payload = json.loads(result["command"].split("<<'JSON'\n", 1)[1].rsplit("\nJSON", 1)[0])
        self.assertTrue(payload["required_status_checks"]["strict"])
        self.assertFalse(payload["allow_force_pushes"])
        self.assertFalse(payload["allow_deletions"])
        self.assertEqual([item["context"] for item in payload["required_status_checks"]["checks"]],
                         [ATTRIBUTION_CHECK, "python"])
        self.assertTrue(all(method == "GET" for method, _ in client.calls))

    def test_only_checks_passing_on_every_run_are_required(self):
        runs = ("python", ATTRIBUTION_CHECK, {"name": "lint", "conclusion": "failure"},
                {"name": "e2e", "conclusion": None}, {"name": "python", "conclusion": "skipped"})
        result = prepare(REPOSITORY, "main", FakeClient(responses(checks=runs)))
        self.assertEqual(result["required_checks"], [ATTRIBUTION_CHECK])
        self.assertEqual(result["check_conclusions"]["python"], ["skipped", "success"])
        for name in ("lint", "e2e", "python"):
            self.assertTrue(any(name in w for w in result["warnings"]), name)
        payload = json.loads(result["command"].split("<<'JSON'\n", 1)[1].rsplit("\nJSON", 1)[0])
        self.assertEqual([c["context"] for c in payload["required_status_checks"]["checks"]], [ATTRIBUTION_CHECK])

    def test_failing_attribution_check_generates_no_command(self):
        runs = ("python", {"name": ATTRIBUTION_CHECK, "conclusion": "failure"})
        result = prepare(REPOSITORY, "main", FakeClient(responses(checks=runs)))
        self.assertFalse(result["attribution_verified"])
        self.assertIsNone(result["command"])

    def test_check_names_cannot_escape_the_heredoc(self):
        hostile = 'x"\nJSON\nrm -rf ~\n'
        result = prepare(REPOSITORY, "main", FakeClient(responses(checks=(ATTRIBUTION_CHECK, hostile))))
        body = result["command"].split("<<'JSON'\n", 1)[1]
        self.assertEqual(body.count("\nJSON"), 1)  # un seul terminateur, en derniere ligne
        self.assertTrue(body.endswith("\nJSON"))
        self.assertNotIn("\nrm -rf", result["command"])

    def test_repository_absent_or_inaccessible(self):
        client = FakeClient({"/repos/owner/missing": FetchError("gh api a echoue HTTP 404 (code 1)")})
        with self.assertRaisesRegex(ValueError, "Depot absent ou inaccessible"):
            prepare("owner/missing", "main", client)

        client = FakeClient({"/repos/owner/private": FetchError("gh api a echoue HTTP 403 (code 1)")})
        with self.assertRaisesRegex(ValueError, "Depot absent ou inaccessible"):
            prepare("owner/private", "main", client)

    def test_branch_missing(self):
        data = responses()
        data["/repos/owner/project/branches/missing"] = FetchError("gh api a echoue HTTP 404 (code 1)")
        client = FakeClient(data)
        with self.assertRaisesRegex(ValueError, "Branche inexistante"):
            prepare(REPOSITORY, "missing", client)

    def test_ci_absent_does_not_generate_command(self):
        result = prepare(REPOSITORY, "main", FakeClient(responses(checks=())))
        self.assertEqual(result["available_checks"], [])
        self.assertIsNone(result["command"])
        self.assertTrue(any("Aucun controle CI" in item for item in result["warnings"]))
        self.assertFalse(result["attribution_verified"])

    def test_attribution_missing_does_not_claim_or_generate_protection(self):
        result = prepare(REPOSITORY, "main", FakeClient(responses(checks=("python",))))
        self.assertIsNone(result["command"])
        self.assertFalse(result["attribution_verified"])
        self.assertTrue(any("attribution Git" in item for item in result["warnings"]))

    def test_insufficient_permissions_are_explicit(self):
        permissions = {"admin": False, "maintain": True, "push": True}
        result = prepare(REPOSITORY, "main", FakeClient(responses(permissions=permissions)))
        self.assertFalse(result["can_apply"])
        self.assertEqual(result["required_permission"], "Administration: write")
        self.assertTrue(any("Permission insuffisante" in item for item in result["warnings"]))

    def test_unreadable_current_protection_is_not_claimed(self):
        data = responses()
        data["/repos/owner/project/branches/main/protection"] = FetchError("gh api a echoue HTTP 403 (code 1)")
        result = prepare(REPOSITORY, "main", FakeClient(data))
        self.assertIsNone(result["protection_active"])
        self.assertFalse(result["protection_verified"])
        self.assertTrue(any("NON VERIFIEE" in item for item in result["warnings"]))

    def test_invalid_inputs_and_unauthenticated_cli_are_rejected(self):
        for repository, branch in (("bad repository", "main"), (REPOSITORY, "../main"), (REPOSITORY, "")):
            with self.subTest(repository=repository, branch=branch):
                with self.assertRaises(ValueError):
                    prepare(repository, branch, FakeClient())
        with self.assertRaisesRegex(ValueError, "gh auth login"):
            prepare(REPOSITORY, "main", FakeClient(authenticated=False))

    def test_web_payload_never_executes_a_remote_mutation(self):
        proposal = {"repository": REPOSITORY, "branch": "main", "manual_only": True, "command": "gh api PUT"}
        with mock.patch("forge.web.prepare_branch_protection", return_value=proposal) as mocked:
            status, body, _, _ = web.branch_protection_payload(
                json.dumps({"repository": REPOSITORY, "branch": "main"}).encode())
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["manual_only"])
        mocked.assert_called_once_with(REPOSITORY, "main")

    def test_web_payload_rejects_extra_fields(self):
        status, body, _, _ = web.branch_protection_payload(
            json.dumps({"repository": REPOSITORY, "branch": "main", "token": "secret"}).encode())
        self.assertEqual(status, 400)
        self.assertNotIn("secret", body.decode())


if __name__ == "__main__":
    unittest.main()
