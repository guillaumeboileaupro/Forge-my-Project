# E01 - Audit et nettoyage des refs Git (16 novembre 2026)

Reference `origin/main` = `140bdb28291d0a2f87faf434cc21247a19a8de6a` (fusion de la PR #26). Aucune reecriture d'historique, aucun push force. Aucun commit attribue a un agent IA.

## Methode

Pour chaque branche locale et distante :

1. `git merge-base --is-ancestor <ref> origin/main` : le dernier commit est-il dans main ?
2. `git rev-list --count origin/main..<ref>` et `git cherry origin/main <ref>` : commits absents de main, y compris par equivalence de patch (squash, cherry-pick).
3. Simulation de fusion dans un worktree jetable (`git merge --no-commit --no-ff <ref>` sur origin/main) : un index identique a main prouve que tout le contenu est deja integre, meme apres squash ou reecriture.
4. `scripts/attribution_guard.py check-range <ref>` sur tout l'historique de la branche.
5. Worktree associe : `git status --porcelain --untracked-files=all`, fichiers ignores hors `__pycache__`, stash.
6. PR associee (`gh pr list --state all`).

## Inventaire

| Branche | Dernier commit | Date | PR | Dans main | Commits hors main | Simulation de fusion | Attribution IA | Worktree | Decision |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| main | `140bdb2` (distant), `ea612bf` (local) | 2026-11-16 | - | - | 0 | - | aucune | Forge-my-Project, **modifie** (TODO.md) | conservee ; main local non avance pour ne pas toucher TODO.md non commite |
| feat/e04-linux-launcher | `f3a7e5b` | 2026-11-16 | #25 **ouverte** | non | 2+ | 8 fichiers apportes | aucune | Forge-my-Project-e04, **modifie** | conservee (PR active, worktree sale) |
| feat/e02-git-attribution-guard | `e2f16eb` | 2026-11-15 | #26 fusionnee | oui | 0 | aucun changement | aucune | Forge-my-Project-e02, propre | supprimee (locale, distante, worktree) |
| fix/no-ai-coauthor-attribution | `12d0d92` | 2026-11-15 | #23 fusionnee, #21 fermee | oui | 0 | aucun changement | aucune | - | supprimee (distante) |
| docs/development-roadmap-todo | `0a8fceb` | 2026-11-14 | #2 fusionnee | oui | 0 | aucun changement | aucune | - | archivee puis supprimee (distante) |
| docs/validated-project-specification | `180b111` | 2026-11-14 | #3 fusionnee | oui | 0 | aucun changement | aucune | - | archivee puis supprimee (distante) |
| docs/roadmap-34-decisions-2026 | `d1d3b58` | 2026-11-15 | #22 fusionnee | oui | 0 | aucun changement | aucune | - | archivee puis supprimee (distante) |
| claude/start-launcher | `f2f306e` | 2026-11-15 | #20 fusionnee | oui | 0 | aucun changement | aucune | .forge-start, propre | distante supprimee ; locale et worktree conserves (voir Reste a decider) |
| codex/file-preview | `b41c8df` | 2026-11-15 | #15 fusionnee | oui | 0 | aucun changement | aucune | Forge-my-Project-codex, propre (`.tmp-e2e/` vide) | distante supprimee ; locale et worktree conserves (voir Reste a decider) |

Aucun tag, aucun stash. `docs/complete-roadmap-acceptance` (PR #24) et son worktree `Forge-my-Project-planning-completion` avaient deja ete retires avant cet audit.

## Archive des branches docs/*

Chaque commit reste atteignable depuis main (ancetre direct) ; restauration : `git push origin <SHA>:refs/heads/<branche>`.

| Branche | SHA complet | PR |
| --- | --- | --- |
| docs/development-roadmap-todo | `0a8fceb22fb83b5cca9d7214d26b3266043e5e0e` | #2 |
| docs/validated-project-specification | `180b1117d8bdd13c28064cc99ab28b3f6503af97` | #3 |
| docs/roadmap-34-decisions-2026 | `d1d3b58e9158db2654e30cba6e7156ed12714853` | #22 |

Autres branches supprimees, meme restauration : fix/no-ai-coauthor-attribution `12d0d92d5f91f734023622d39e2f72ba40830ff4`, feat/e02-git-attribution-guard `e2f16eb44f267713194b86816591517ad7627c71`, claude/start-launcher `f2f306e7b4f2454bb32a2fdc7b3b4c3e927f0769`, codex/file-preview `b41c8df0671b850c9b394635e4b2d64e5c3b8e4e`.

## Anciennes attributions IA

- Branches, tags, stash et reflogs locaux : aucune attribution (`attribution_guard.py audit`).
- Les commits `11d0f4ca058da0f5f54fcd636c1e746c6a7280e5` (T10) et `e71a9507fe2ecddf85c0608cae00b5df0332665f` (T15), porteurs de `Co-Authored-By: Claude <noreply@anthropic.com>` (auteur et committer = proprietaire), ne sont atteignables depuis aucune branche. Localement, ce sont des objets orphelins, absents des reflogs.
- **Residuel GitHub** : clone miroir audite, ces deux commits restent references par les refs en lecture seule `refs/pull/14/head` a `refs/pull/19/head` et `refs/pull/21/head`. Ces refs sont gerees par GitHub et ne peuvent pas etre supprimees par un push. Seul le support GitHub peut les purger, a la demande du proprietaire. Aucune action automatique n'a ete tentee.

## Simulation (avant toute suppression)

```text
$ git push --dry-run origin --delete docs/development-roadmap-todo docs/roadmap-34-decisions-2026 docs/validated-project-specification fix/no-ai-coauthor-attribution feat/e02-git-attribution-guard claude/start-launcher codex/file-preview
 - [deleted]         claude/start-launcher
 - [deleted]         codex/file-preview
 - [deleted]         docs/development-roadmap-todo
 - [deleted]         docs/roadmap-34-decisions-2026
 - [deleted]         docs/validated-project-specification
 - [deleted]         feat/e02-git-attribution-guard
 - [deleted]         fix/no-ai-coauthor-attribution
$ git branch --merged origin/main            -> feat/e02-git-attribution-guard
$ git -C ../Forge-my-Project-e02 status --porcelain --untracked-files=all   -> (vide)
$ git rev-list --count origin/feat/e02-git-attribution-guard..feat/e02-git-attribution-guard   -> 0
```

## Execution

```text
$ git worktree remove ../Forge-my-Project-e02
OK
$ git branch -d feat/e02-git-attribution-guard
warning: suppression de la branche 'feat/e02-git-attribution-guard' qui a été fusionnée dans
         'refs/remotes/origin/feat/e02-git-attribution-guard', mais pas dans HEAD.
Branche feat/e02-git-attribution-guard supprimée (précédemment e2f16eb).
$ git push origin --delete <7 branches>
To github.com:guillaumeboileaupro/Forge-my-Project.git
 - [deleted]         claude/start-launcher
 - [deleted]         codex/file-preview
 - [deleted]         docs/development-roadmap-todo
 - [deleted]         docs/roadmap-34-decisions-2026
 - [deleted]         docs/validated-project-specification
 - [deleted]         feat/e02-git-attribution-guard
 - [deleted]         fix/no-ai-coauthor-attribution
$ git fetch --prune origin
$ git ls-remote --heads origin
f3a7e5b refs/heads/feat/e04-linux-launcher
140bdb2 refs/heads/main
$ git worktree list
/home/gboileau/Documents/Tools/Forge-my-Project        ea612bf [main]
/home/gboileau/Documents/Tools/.forge-start            f2f306e [claude/start-launcher]
/home/gboileau/Documents/Tools/Forge-my-Project-codex  b41c8df [codex/file-preview]
/home/gboileau/Documents/Tools/Forge-my-Project-e01    140bdb2 [docs/e01-refs-audit]
/home/gboileau/Documents/Tools/Forge-my-Project-e04    f3a7e5b [feat/e04-linux-launcher]
```

Resultat : 9 -> 2 branches distantes (main, feat/e04-linux-launcher) ; 5 -> 4 worktrees hors worktree documentaire E01 ; aucun worktree modifie supprime ; aucune branche de PR ouverte supprimee.

## Reste a decider (proprietaire)

- Worktrees `.forge-start` (claude/start-launcher) et `Forge-my-Project-codex` (codex/file-preview) : propres et integres a main, mais rattaches a d'autres sessions d'agents ; leur inutilite n'est pas demontree depuis cette session. Retrait sur de vrais besoins : `git worktree remove <chemin>` puis `git branch -d <branche>` (les deux refusent toute perte).
- Worktree principal : `TODO.md` non commite empeche l'avance rapide de main local (`git merge --ff-only origin/main` apres l'avoir commite ou mis de cote).
- Refs `refs/pull/*` contenant les anciens trailers : demande au support GitHub si leur purge est souhaitee.
