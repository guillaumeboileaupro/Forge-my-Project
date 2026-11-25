"""Nettoyage prudent des worktrees (Q15) : tests sur de vrais depots Git.

Les depots de test sont crees dans un dossier `.tmp-*` a l'interieur du depot
(ignore par Git), jamais hors de la racine du projet.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "worktree_cleanup.py"
IDENTITY = {"GIT_AUTHOR_NAME": "Owner", "GIT_AUTHOR_EMAIL": "owner@example.invalid",
            "GIT_COMMITTER_NAME": "Owner", "GIT_COMMITTER_EMAIL": "owner@example.invalid"}


class WorktreeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = Path(tempfile.mkdtemp(prefix=".tmp-worktree-cleanup-", dir=ROOT))
        self.addCleanup(shutil.rmtree, self.sandbox)
        (self.sandbox / "gitconfig").write_text("", encoding="utf-8")
        self.env = {**os.environ, **IDENTITY, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": str(self.sandbox / "gitconfig")}
        self.repo = self.sandbox / "repo"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        (self.repo / ".gitignore").write_text(".env\n", encoding="utf-8")
        self.commit(self.repo, "init")

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, cwd, message):
        (cwd / f"{message}.txt").write_text(message, encoding="utf-8")
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-q", "-m", message)

    def add_worktree(self, name, merged=True):
        path = self.sandbox / name
        self.git(self.repo, "worktree", "add", "-q", "-b", name, str(path))
        self.commit(path, name)
        if merged:
            self.git(self.repo, "merge", "-q", "--no-ff", "-m", f"merge {name}", name)
        return path

    def run_tool(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(TOOL), "--repo", str(self.repo),
                               "--base", "main", *args], cwd=cwd or self.repo,
                              env=self.env, capture_output=True, text=True)

    def branches(self):
        return self.git(self.repo, "branch", "--format=%(refname:short)").split()

    def assert_kept(self, path, reason):
        for args in ((), ("--apply",)):
            result = self.run_tool(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, rf"CONSERVE: {re.escape(str(path))} .*{reason}")
        self.assertTrue(path.is_dir())
        self.assertIn(path.name, self.branches())

    def test_simulation_by_default_then_apply_removes_merged_clean_worktree(self):
        path = self.add_worktree("feat-merged")
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SIMULATION", result.stdout)
        self.assertIn(f"A RETIRER: {path} [feat-merged]", result.stdout)
        self.assertRegex(result.stdout, r"CONSERVE: .*repo \[main\] - worktree principal")
        self.assertTrue(path.is_dir())
        self.assertIn("feat-merged", self.branches())

        result = self.run_tool("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("worktree retire; branche supprimee", result.stdout)
        self.assertFalse(path.exists())
        self.assertEqual(self.branches(), ["main"])

    def test_unmerged_commits_are_kept(self):
        path = self.add_worktree("feat-open", merged=False)
        self.assert_kept(path, "commits non integres a main")

    def test_modified_untracked_and_ignored_files_are_kept(self):
        for name, write in (("feat-modified", "feat-modified.txt"),
                            ("feat-untracked", "notes.txt"), ("feat-ignored", ".env")):
            with self.subTest(name):
                path = self.add_worktree(name)
                (path / write).write_text("unique", encoding="utf-8")
                self.assert_kept(path, r"1 fichier\(s\) modifie")

    def test_locked_worktree_is_kept(self):
        path = self.add_worktree("feat-locked")
        self.git(self.repo, "worktree", "lock", str(path))
        self.assert_kept(path, "verrouille")

    def test_worktree_running_the_tool_is_kept(self):
        path = self.add_worktree("feat-active")
        (path / "sub").mkdir()
        result = self.run_tool("--apply", cwd=path / "sub")
        self.assertRegex(result.stdout, r"CONSERVE: .*feat-active.* worktree actif")
        self.assertTrue(path.is_dir())

    def test_operation_in_progress_is_kept(self):
        path = self.add_worktree("feat-merging")
        marker = Path(self.git(path, "rev-parse", "--git-path", "MERGE_HEAD"))
        (marker if marker.is_absolute() else path / marker).write_text(
            self.git(path, "rev-parse", "HEAD") + "\n", encoding="utf-8")
        self.assert_kept(path, "operation en cours: MERGE_HEAD")

    def test_detached_merged_worktree_is_removed_without_branch_deletion(self):
        path = self.sandbox / "detached"
        self.git(self.repo, "worktree", "add", "-q", "--detach", str(path), "main")
        result = self.run_tool("--apply")
        self.assertIn("HEAD detache", result.stdout)
        self.assertIn("worktree retire", result.stdout)
        self.assertNotIn("branche", result.stdout.split("detached")[-1])
        self.assertFalse(path.exists())
        self.assertEqual(self.branches(), ["main"])

    def test_unknown_base_is_an_error_and_changes_nothing(self):
        path = self.add_worktree("feat-merged")
        result = self.run_tool("--apply", "--base", "origin/absent")
        self.assertEqual(result.returncode, 1)
        self.assertIn("erreur", result.stderr)
        self.assertTrue(path.is_dir())

    def test_tool_never_forces(self):
        source = TOOL.read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines()
                         if line.strip() and not line.lstrip().startswith("#"))
        code = code.split('"""', 2)[2]  # sans la docstring
        for forbidden in ('"--force"', '"-f"', '"-D"', '"push"', '"clean"', '"reset"',
                          "rmtree", "unlink", "rmdir"):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
