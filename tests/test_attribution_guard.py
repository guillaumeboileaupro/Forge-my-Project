"""Garde d'attribution Git (E02) : tests fonctionnels sur de vrais depots Git.

Aucun agent IA ne doit apparaitre comme auteur, committer ou co-auteur ; une simple
mention documentaire d'un agent reste autorisee.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forge.pipeline import run

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "attribution_guard.py"
OWNER = {"GIT_AUTHOR_NAME": "Owner", "GIT_AUTHOR_EMAIL": "owner@example.invalid",
         "GIT_COMMITTER_NAME": "Owner", "GIT_COMMITTER_EMAIL": "owner@example.invalid"}
CLAUDE_TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"
CODEX_TRAILER = "Co-authored-by: Codex <codex@openai.com>"
DOC_MESSAGE = ("docs: documenter les hooks Claude Code et Codex\n\n"
               "Codex lit AGENTS.md et Claude Code lit CLAUDE.md. Les trailers\n"
               "Co-authored-by vers Claude sont refuses par le garde.\n")


def load_guard():
    spec = importlib.util.spec_from_loader("attribution_guard", loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(GUARD.read_text(encoding="utf-8"), str(GUARD), "exec"), module.__dict__)  # noqa: S102
    return module


guard = load_guard()


class SandboxMixin:
    """Depots temporaires avec configuration Git globale isolee (jamais celle de l'utilisateur)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="attribution-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        home = self.tmp / "home"
        home.mkdir()
        self.env = dict(os.environ, HOME=str(home), GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=str(home / ".gitconfig"), **OWNER)
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_TEMPLATE_DIR"):
            self.env.pop(key, None)

    def git(self, cwd, *args, check=True, env=None, stdin=None):
        return subprocess.run(["git", *args], cwd=cwd, env=env or self.env, input=stdin,
                              capture_output=True, text=True, check=check)

    def guard(self, *args, cwd=None, env=None, stdin=""):
        return subprocess.run([sys.executable, str(GUARD), *args], cwd=cwd or self.tmp,
                              env=env or self.env, input=stdin, capture_output=True, text=True)

    def new_repo(self, name="repo", template=None):
        path = self.tmp / name
        args = ["init", "-q", "-b", "main"] + (["--template", str(template)] if template else []) + [str(path)]
        self.git(self.tmp, *args)
        self.git(path, "config", "gc.auto", "0")
        self.git(path, "config", "maintenance.auto", "false")
        return path

    def commit(self, repo, message, *extra, env=None):
        (repo / "f.txt").write_text(message, encoding="utf-8")
        self.git(repo, "add", "-A")
        return self.git(repo, "commit", "-q", *extra, "-F", "-", check=False, env=env, stdin=message)

    def count(self, repo):
        done = self.git(repo, "rev-list", "--count", "HEAD", check=False)
        return int(done.stdout) if done.returncode == 0 else 0


class MessageRuleTests(unittest.TestCase):
    def test_attribution_trailers_and_footer_are_refused(self):
        for text in (CLAUDE_TRAILER, CODEX_TRAILER, "co-authored-by: GitHub Copilot <copilot@github.com>",
                     "Signed-off-by: claude <claude@anthropic.com>",
                     "Co-authored-by: copilot-swe-agent[bot] <198982749+Copilot@users.noreply.github.com>",
                     "Assisted-by: Gemini", "Co-authored-by: Cursor Agent <cursoragent@cursor.com>",
                     "\U0001f916 Generated with [Claude Code](https://claude.com/claude-code)"):
            with self.subTest(text=text):
                self.assertTrue(guard.message_problems("feat: x\n\n" + text))

    def test_documentary_mentions_are_allowed(self):
        for text in (DOC_MESSAGE, "fix: corriger le hook Codex", "docs: Claude, Codex et Copilot sont des outils",
                     "Co-authored-by: Alice <alice@example.org>", "Signed-off-by: Owner <owner@example.invalid>",
                     "# Co-Authored-By: Claude (commentaire retire par git)",
                     "docs: le texte genere with Claude n'est pas un trailer"):
            with self.subTest(text=text):
                self.assertEqual(guard.message_problems(text), [])

    def test_identities(self):
        for ident in ("Claude <noreply@anthropic.com>", "Owner <bot@anthropic.com>", "codex <x@example.org>",
                      "ChatGPT <x@example.org>", "gpt-5 <x@example.org>", "Copilot <x@github.com>"):
            self.assertTrue(guard.identity_problem("auteur", ident), ident)
        for ident in ("Owner <owner@example.invalid>", "GitHub <noreply@github.com>",
                      "guillaumeboileaupro <37927799+guillaumeboileaupro@users.noreply.github.com>",
                      "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"):
            self.assertIsNone(guard.identity_problem("auteur", ident), ident)


class InstalledRepositoryTests(SandboxMixin, unittest.TestCase):
    """Installation dans un depot existant (.git/hooks)."""

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo()
        done = self.guard("install", str(self.repo))
        self.assertEqual(done.returncode, 0, done.stderr)

    def assert_refused(self, done, before, needle):
        self.assertNotEqual(done.returncode, 0)
        self.assertIn(needle, done.stderr)
        self.assertEqual(self.count(self.repo), before)

    def test_normal_commit_and_documentary_mention_are_accepted(self):
        done = self.commit(self.repo, DOC_MESSAGE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.count(self.repo), 1)

    def test_co_authored_by_claude_is_refused(self):
        self.assert_refused(self.commit(self.repo, "feat: x\n\n" + CLAUDE_TRAILER + "\n"), 0, "trailer")

    def test_co_authored_by_codex_is_refused(self):
        self.assert_refused(self.commit(self.repo, "feat: x\n\n" + CODEX_TRAILER + "\n"), 0, "trailer")

    def test_claude_author_is_refused(self):
        done = self.commit(self.repo, "feat: x", "--author", "Claude <noreply@anthropic.com>")
        self.assert_refused(done, 0, "auteur designe un agent IA")

    def test_claude_committer_is_refused(self):
        env = dict(self.env, GIT_COMMITTER_NAME="Claude", GIT_COMMITTER_EMAIL="noreply@anthropic.com")
        self.assert_refused(self.commit(self.repo, "feat: x", env=env), 0, "committer designe un agent IA")

    def test_identity_from_git_config_is_checked(self):
        env = {k: v for k, v in self.env.items() if not k.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_"))}
        self.git(self.repo, "config", "user.name", "Codex", env=env)
        self.git(self.repo, "config", "user.email", "codex@openai.com", env=env)
        self.assert_refused(self.commit(self.repo, "feat: x", env=env), 0, "agent IA")

    def test_push_with_forbidden_attribution_is_refused(self):
        remote = self.tmp / "remote.git"
        self.git(self.tmp, "init", "-q", "--bare", str(remote))
        self.git(self.repo, "remote", "add", "origin", str(remote))
        self.assertEqual(self.commit(self.repo, "feat: base").returncode, 0)
        self.assertEqual(self.git(self.repo, "push", "-q", "origin", "main", check=False).returncode, 0)
        # Contournement local du commit-msg : seul pre-push peut encore l'arreter.
        bypass = self.commit(self.repo, "feat: y\n\n" + CLAUDE_TRAILER + "\n", "--no-verify")
        self.assertEqual(bypass.returncode, 0, bypass.stderr)
        pushed = self.git(self.repo, "push", "origin", "main", check=False)
        self.assertNotEqual(pushed.returncode, 0)
        self.assertIn("pre-push : attribution Git interdite", pushed.stderr)
        self.assertEqual(self.git(remote, "rev-list", "--count", "main").stdout.strip(), "1")
        branch = self.git(self.repo, "push", "origin", "HEAD:refs/heads/new-branch", check=False)
        self.assertNotEqual(branch.returncode, 0, "nouvelle branche distante : meme controle")
        author = self.commit(self.repo, "feat: z", "--no-verify", "--author", "Claude <noreply@anthropic.com>")
        self.assertEqual(author.returncode, 0)
        self.assertIn("auteur designe un agent IA", self.git(self.repo, "push", "origin", "main", check=False).stderr)

    def test_clean_push_and_branch_deletion_are_accepted(self):
        remote = self.tmp / "remote.git"
        self.git(self.tmp, "init", "-q", "--bare", str(remote))
        self.git(self.repo, "remote", "add", "origin", str(remote))
        self.commit(self.repo, "feat: base")
        self.assertEqual(self.git(self.repo, "push", "-q", "origin", "main", "main:topic", check=False).returncode, 0)
        self.commit(self.repo, DOC_MESSAGE)
        done = self.git(self.repo, "push", "-q", "origin", "main", check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        deleted = self.git(self.repo, "push", "-q", "origin", "--delete", "topic", check=False)
        self.assertEqual(deleted.returncode, 0, deleted.stderr)

    def test_install_is_idempotent(self):
        self.assertEqual(self.guard("install", str(self.repo)).returncode, 0)
        self.assertFalse((self.repo / ".git" / "hooks" / "commit-msg.local").exists())

    def test_ci_mode_detects_forbidden_attribution(self):
        self.commit(self.repo, "feat: base")
        base = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.commit(self.repo, "feat: y\n\n" + CODEX_TRAILER + "\n", "--no-verify")
        head = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()
        event = self.tmp / "event.json"

        def ci(name, payload):
            event.write_text(json.dumps(payload), encoding="utf-8")
            return self.guard("ci", cwd=self.repo, env=dict(self.env, GITHUB_EVENT_NAME=name,
                                                             GITHUB_EVENT_PATH=str(event)))

        push = ci("push", {"before": base, "after": head, "ref": "refs/heads/main",
                           "repository": {"default_branch": "main"}})
        self.assertEqual(push.returncode, 1)
        self.assertIn("trailer", push.stderr)
        clean = ci("push", {"before": base, "after": base, "ref": "refs/heads/main"})
        self.assertEqual(clean.returncode, 0, clean.stderr)
        pull = {"base": {"sha": base}, "head": {"sha": base}, "title": "docs: hooks Codex",
                "body": "Description mentionnant Claude.\n\n" + CLAUDE_TRAILER}
        refused = ci("pull_request", {"pull_request": pull})
        self.assertEqual(refused.returncode, 1)
        self.assertIn("description de la PR", refused.stderr)
        pull["body"] = "Description mentionnant Claude et Codex comme outils."
        self.assertEqual(ci("pull_request", {"pull_request": pull}).returncode, 0)
        pull["head"]["sha"] = head
        self.assertEqual(ci("pull_request", {"pull_request": pull}).returncode, 1)
        pull["base"]["sha"] = "f" * 40  # commits absents (checkout superficiel) : refus, jamais succes
        missing = ci("pull_request", {"pull_request": pull})
        self.assertEqual(missing.returncode, 1)
        self.assertIn("aucune plage de commits verifiable", missing.stderr)


class ExistingHooksTests(SandboxMixin, unittest.TestCase):
    def test_existing_hooks_are_preserved_and_still_run(self):
        repo = self.new_repo()
        hooks = repo / ".git" / "hooks"
        original_msg = "#!/bin/sh\necho ran >> \"$(git rev-parse --git-dir)/msg.log\"\n" \
                       "! grep -q WIP \"$1\" || { echo 'WIP refuse' >&2; exit 1; }\n"
        original_push = "#!/bin/sh\ncat > \"$(git rev-parse --git-dir)/push.log\"\n"
        (hooks / "commit-msg").write_text(original_msg, encoding="utf-8")
        (hooks / "pre-push").write_text(original_push, encoding="utf-8")
        for name in ("commit-msg", "pre-push"):
            (hooks / name).chmod(0o755)
        done = self.guard("install", str(repo))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((hooks / "commit-msg.local").read_text(encoding="utf-8"), original_msg)
        self.assertEqual(self.commit(repo, "feat: base").returncode, 0)
        self.assertTrue((repo / ".git" / "msg.log").exists(), "hook d'origine execute")
        self.assertIn("WIP refuse", self.commit(repo, "feat: WIP").stderr)
        self.assertIn("trailer", self.commit(repo, "feat: x\n\n" + CLAUDE_TRAILER).stderr)
        remote = self.tmp / "remote.git"
        self.git(self.tmp, "init", "-q", "--bare", str(remote))
        self.git(repo, "remote", "add", "origin", str(remote))
        self.assertEqual(self.git(repo, "push", "-q", "origin", "main", check=False).returncode, 0)
        head = self.git(repo, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual((repo / ".git" / "push.log").read_text(encoding="utf-8"),
                         "refs/heads/main %s refs/heads/main %s\n" % (head, "0" * 40),
                         "entree standard transmise intacte au pre-push d'origine")
        self.assertEqual(self.guard("uninstall", str(repo)).returncode, 0)
        self.assertEqual((hooks / "commit-msg").read_text(encoding="utf-8"), original_msg)
        self.assertFalse((hooks / "commit-msg.local").exists())
        self.assertFalse((hooks / "attribution_guard.py").exists())

    def test_tracked_hooks_path_is_not_modified_without_consent(self):
        repo = self.new_repo()
        (repo / ".githooks").mkdir()
        (repo / ".githooks" / "commit-msg").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.git(repo, "config", "core.hooksPath", ".githooks")
        done = self.guard("install", str(repo))
        self.assertEqual(done.returncode, 1)
        self.assertIn("hooks versionnes", done.stderr)
        self.assertEqual(sorted(p.name for p in (repo / ".githooks").iterdir()), ["commit-msg"])


class FutureRepositoryTests(SandboxMixin, unittest.TestCase):
    def global_template(self):
        return self.git(self.tmp, "config", "--global", "--get", "init.templateDir", check=False).stdout.strip()

    def test_global_config_requires_confirmation(self):
        target = self.tmp / "template"
        done = self.guard("install-template", "--dir", str(target))  # entree non interactive, pas de --yes
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("NON modifiee", done.stdout)
        self.assertEqual(self.global_template(), "")

    def test_new_repository_is_protected(self):
        target = self.tmp / "template"
        done = self.guard("install-template", "--dir", str(target), "--yes")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.global_template(), str(target))
        repo = self.new_repo("fresh")  # git init sans option : modele global
        self.assertIn("trailer", self.commit(repo, "feat: x\n\n" + CODEX_TRAILER).stderr)
        self.assertEqual(self.count(repo), 0)
        self.assertEqual(self.commit(repo, "feat: base").returncode, 0)
        clone = self.git(self.tmp, "clone", "-q", str(repo), str(self.tmp / "clone"), check=False)
        self.assertEqual(clone.returncode, 0, clone.stderr)
        self.assertTrue((self.tmp / "clone" / ".git" / "hooks" / "attribution_guard.py").exists())

    def test_existing_template_dir_is_reused_without_global_change(self):
        current = self.tmp / "existing-template"
        self.git(self.tmp, "config", "--global", "init.templateDir", str(current))
        done = self.guard("install-template")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((current / "hooks" / "commit-msg").exists())
        self.assertEqual(self.global_template(), str(current))


class GeneratedProjectTests(SandboxMixin, unittest.TestCase):
    def test_generated_project_is_protected(self):
        answers = {"name": "attr-demo", "project_type": "library", "agents": ["codex", "claude"],
                   "technologies": ["python", "unittest"]}
        files = run(answers).files
        self.assertIn("attribution_guard.py\" commit-msg", files[".githooks/commit-msg"])
        self.assertIn("attribution_guard.py\" pre-push", files[".githooks/pre-push"])
        self.assertIn("python3 scripts/hooks/attribution_guard.py ci", files[".github/workflows/ci.yml"])
        self.assertEqual(files["scripts/hooks/attribution_guard.py"], GUARD.read_text(encoding="utf-8"))
        settings = json.loads(files[".claude/settings.json"])
        self.assertFalse(settings["includeCoAuthoredBy"])
        self.assertEqual(settings["attribution"], {"commit": "", "pr": ""})
        repo = self.new_repo("generated")
        for path, content in files.items():
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            if path.startswith((".githooks/", "scripts/hooks/")):
                target.chmod(0o755)
        self.git(repo, "config", "core.hooksPath", ".githooks")
        self.git(repo, "add", "-A")
        refused = self.git(repo, "commit", "-q", "-m", "feat: init\n\n" + CLAUDE_TRAILER, check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("trailer", refused.stderr)
        author = self.git(repo, "commit", "-q", "--author", "Codex <codex@openai.com>", "-m", "feat: init",
                          check=False)
        self.assertIn("auteur designe un agent IA", author.stderr)
        accepted = self.git(repo, "commit", "-q", "-m", "docs: decrire les hooks Claude Code", check=False)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)


class RepositoryIntegrationTests(unittest.TestCase):
    def test_forge_repository_hooks_and_ci(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/attribution_guard.py ci", workflow)
        self.assertIn("attribution_guard.py\" commit-msg", (ROOT / ".githooks" / "commit-msg").read_text())
        self.assertIn("attribution_guard.py\" pre-push", (ROOT / ".githooks" / "pre-push").read_text())
        self.assertIn("python3 -m unittest discover", (ROOT / ".githooks" / "pre-commit").read_text(),
                      "hook pre-commit existant conserve")
        self.assertNotIn("{{", GUARD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
