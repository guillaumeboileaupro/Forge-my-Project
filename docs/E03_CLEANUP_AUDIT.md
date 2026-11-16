# E03 - Audit des fichiers temporaires, doublons, configurations et scripts (16 novembre 2026)

Reference : `origin/main` = `5bb1200` (fusion de la PR #27). Perimetre : les 214 fichiers suivis par Git, plus les fichiers ignores et temporaires des worktrees et de `/tmp`. Regle (Q16) : supprimer uniquement sur preuve.

## Controles et resultats

| Controle | Commande ou methode | Resultat |
| --- | --- | --- |
| Temporaires et sauvegardes suivis | `git ls-files` filtre sur `.bak .orig .rej .swp ~ .log .old copy backup .DS_Store .pyc` | aucun (les seules correspondances sont des extensions `.tmpl`) |
| Doublons exacts | empreintes de blobs `git ls-files -s`, puis inspection des liens symboliques | aucun blob independant duplique ; `scripts/attribution_guard.py` est le lien symbolique actif vers la source unique `templates/hooks/attribution_guard.py.tmpl`, donc conserve |
| Fichiers orphelins | chemin, nom et module de chaque fichier recherches ailleurs (`git grep`) | catalogues JSON : charges par `glob("*.json")` (`forge/config/catalog.py`, `forge/rules/engine.py`), donc utilises ; modules `versions`, `bundle`, `npm_peers`, `semver` : importes ; seul orphelin reel : `docs/CONVENTIONS.md` |
| Templates | chaque `templates/**` reference par un catalogue ou par le code | tous references |
| Scripts | `generator.py`, `server.py`, `start.py`, `scripts/attribution_guard.py`, `tests/smoke_*.py`, `tests/acceptance_t18.py` | tous utilises (CI, README ou TODO) |
| Formulaire historique | `ui/legacy.*`, `templates/legacy/`, `forge/*/legacy.py` | fonction documentee (`/legacy`) ; retrait prevu avec la migration UI (E18), pas avant |
| Configurations | `.gitignore`, `.editorconfig`, `.claude/settings.json`, `.github/*`, `.agents/skills/*` | toutes en usage ; `.gitignore` couvre `__pycache__`, `.venv`, `.env`, `*.zip`, `.tmp-*/` |
| References perimees | branches et worktrees supprimes en E01, recherches dans la doc | uniquement des traces historiques datees (TODO.md, ROADMAP, TRACEABILITY) : conservees |
| Fichiers ignores des worktrees | `git status --ignored` | uniquement `__pycache__` (1,2 Mo dans le worktree principal, regenere a chaque test) et `.tmp-e2e/` vide dans `Forge-my-Project-codex` |
| Temporaires des tests dans `/tmp` | `find /tmp -maxdepth 1 -user <moi> -name 'forge-*' -o -name 'attribution-*'` | un dossier `forge-smoke-*` du 16/11, d'une autre session (peut-etre en cours) : non touche |

## Decisions

- **Aucune suppression** : aucun fichier suivi n'est a la fois inutilise et sans contenu propre.
- `docs/CONVENTIONS.md` : recoupe en partie AGENTS.md et README, mais contient des regles absentes ailleurs (snake_case, tests des fichiers generes, CI alignee sur la documentation). Il est conserve et desormais reference depuis AGENTS.md.
- `__pycache__` du worktree E03 : ignores, regeneres et supprimes apres les tests. Les caches et `.tmp-e2e/` des autres worktrees ne sont pas touches.
- Recherche de code mort par outil tiers (vulture) : non executee, car l'execution d'un outil telecharge non verifie a ete refusee ; l'analyse des references remplace cet outil.

## Non-regression

- `python3.12 -m unittest discover -s tests -v` : 265 tests PASS, 12 ignores avec les sockets loopback autorisees. Le premier passage confine a echoue uniquement sur huit creations de sockets interdites par le bac a sable.
- `python3.12 tests/smoke_generated.py` : les quatre profils Python PASS. Le premier profil TypeScript s'arrete pendant `npm install` sur l'erreur interne `Cannot read properties of null (reading 'edgesOut')`, reproduite par une relance ciblee avant toute modification applicative. La CI l'a tranchee (ci-dessous).
- La suite standard couvre la generation et l'execution des projets Python et JavaScript. Aucun fichier applicatif n'est modifie par E03.

- CI de la PR #28 (runs 43964140186 push et 43964178570 pull_request) : verte, generation et execution des 6 profils PASS, dont les deux profils TypeScript. La limite npm est donc propre a l'environnement local.

Temps reel : voir TODO.md (part Claude mesuree, part Codex non mesuree).
