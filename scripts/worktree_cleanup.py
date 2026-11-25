#!/usr/bin/env python3
"""Nettoyage prudent des worktrees Git apres fusion (decision Q15).

Simulation par defaut : n'execute rien sans --apply. Un worktree secondaire n'est
retire que s'il remplit toutes les conditions suivantes :
- ce n'est ni le worktree principal ni celui depuis lequel l'outil est lance ;
- il n'est pas verrouille (`git worktree lock`) et son dossier existe ;
- aucune operation en cours (fusion, rebase, cherry-pick, revert, bisect) ;
- aucun fichier modifie, non suivi ou ignore (un fichier ignore peut etre unique,
  par exemple un .env, et `git worktree remove` le supprimerait sans prevenir) ;
- son HEAD est entierement integre a la reference de base (ancetre de --base).

Actions, uniquement avec --apply : `git worktree remove` (jamais --force), puis
`git branch -d` (jamais -D) pour la branche du worktree. Aucune branche distante,
aucun stash et aucun fichier hors des commandes Git ci-dessus ne sont touches.

Usage : worktree_cleanup.py [--repo DEPOT] [--base REF] [--apply]
Codes de sortie : 0 sans erreur (y compris si des worktrees sont conserves), 1 erreur.
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

IN_PROGRESS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG",
               "rebase-merge", "rebase-apply")


@dataclass
class Worktree:
    path: Path
    head: str = ""
    branch: str = ""  # nom court, vide si HEAD detache
    locked: bool = False
    prunable: bool = False
    main: bool = False


@dataclass
class Decision:
    worktree: Worktree
    remove: bool
    reasons: list = field(default_factory=list)


def git(repo, *args, check=True):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                            check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result


def list_worktrees(repo):
    worktrees, current = [], None
    for line in git(repo, "worktree", "list", "--porcelain").stdout.splitlines():
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = Worktree(Path(value), main=not worktrees)
            worktrees.append(current)
        elif current is None:
            continue
        elif key == "HEAD":
            current.head = value
        elif key == "branch":
            current.branch = value.removeprefix("refs/heads/")
        elif key == "locked":
            current.locked = True
        elif key == "prunable":
            current.prunable = True
    return worktrees


def operation_in_progress(path):
    found = []
    for name in IN_PROGRESS:
        marker = git(path, "rev-parse", "--git-path", name).stdout.strip()
        if (path / marker).exists():
            found.append(name)
    return found


def decide(repo, worktree, base, invoking):
    reasons = []
    if worktree.main:
        reasons.append("worktree principal")
    path = worktree.path.resolve()
    if invoking == path or path in invoking.parents:
        reasons.append("worktree actif (outil lance depuis ce dossier)")
    if worktree.locked:
        reasons.append("verrouille")
    if worktree.prunable or not worktree.path.is_dir():
        reasons.append("dossier absent (voir git worktree prune -n)")
    if reasons:
        return Decision(worktree, False, reasons)
    operations = operation_in_progress(worktree.path)
    if operations:
        reasons.append("operation en cours: " + ", ".join(operations))
    status = git(worktree.path, "status", "--porcelain", "--ignored",
                 "--untracked-files=all").stdout.splitlines()
    if status:
        reasons.append(f"{len(status)} fichier(s) modifie(s), non suivi(s) ou ignore(s)")
    merged = git(repo, "merge-base", "--is-ancestor", worktree.head, base, check=False)
    if merged.returncode == 1:
        reasons.append(f"commits non integres a {base}")
    elif merged.returncode != 0:
        reasons.append(f"integration non verifiable: {merged.stderr.strip()}")
    return Decision(worktree, not reasons, reasons or [f"propre et integre a {base}"])


def apply(repo, decision):
    worktree = decision.worktree
    git(repo, "worktree", "remove", str(worktree.path))
    done = ["worktree retire"]
    if worktree.branch:
        # git branch -d verifie l'integration par rapport a HEAD ou a l'amont :
        # s'il refuse, la branche est conservee et le refus est rapporte.
        deleted = git(repo, "branch", "-d", worktree.branch, check=False)
        done.append("branche supprimee" if deleted.returncode == 0
                    else "branche conservee: " + deleted.stderr.strip())
    return done


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="depot Git (defaut: dossier courant)")
    parser.add_argument("--base", default="origin/main", help="reference d'integration")
    parser.add_argument("--apply", action="store_true", help="executer (sinon simulation)")
    args = parser.parse_args(argv)
    repo, invoking = Path(args.repo), Path.cwd().resolve()
    try:
        git(repo, "rev-parse", "--verify", "--quiet", args.base + "^{commit}")
        decisions = [decide(repo, wt, args.base, invoking) for wt in list_worktrees(repo)]
    except RuntimeError as error:
        print(f"erreur: {error}", file=sys.stderr)
        return 1
    mode = "EXECUTION" if args.apply else "SIMULATION (aucune modification; --apply pour executer)"
    print(f"Mode: {mode}\nBase: {args.base}")
    failed = False
    for decision in decisions:
        worktree = decision.worktree
        label = f"{worktree.path} [{worktree.branch or 'HEAD detache ' + worktree.head[:7]}]"
        verdict = "A RETIRER" if decision.remove else "CONSERVE"
        print(f"- {verdict}: {label} - {'; '.join(decision.reasons)}")
        if decision.remove and args.apply:
            try:
                print("  -> " + "; ".join(apply(repo, decision)))
            except RuntimeError as error:
                failed = True
                print(f"  -> refus: {error}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
