# Attribution Git - regle obligatoire

Ce depot appartient a son proprietaire, seul contributeur Git a crediter. Codex, Claude Code et les autres assistants sont des outils, pas des contributeurs a crediter dans Git ou GitHub.

- Auteur et committer des commits : uniquement l'identite Git choisie par le proprietaire.
- Interdit dans les messages de commit, descriptions de PR et squash merges : trailer d'attribution (`Co-authored-by`, `Signed-off-by`, `Co-developed-by`, `Assisted-by`...) designant Claude, Anthropic, Codex, Copilot ou un autre agent ; pied automatique `Generated with [Claude Code](...)`.
- Autorise : les noms d'agents dans le texte d'un commit, d'une PR ou de la documentation (configuration, hooks, agents compatibles). Seules les attributions Git sont controlees.
- `.claude/settings.json` desactive l'attribution automatique de Claude Code (`includeCoAuthoredBy: false`, `attribution` vide). Les projets generes avec l'agent Claude recoivent le meme reglage.

## Protection en couches

Un seul outil, `scripts/attribution_guard.py` (bibliotheque standard, Python 3.7+, Git 2.31+). Source unique : `templates/hooks/attribution_guard.py.tmpl` ; le script du depot est un lien symbolique vers elle et les projets generes en recoivent une copie a `scripts/hooks/attribution_guard.py`.

| Couche | Moment | Controle | Contournable ? |
| --- | --- | --- | --- |
| `commit-msg` | `git commit` | identite auteur/committer effective (`git var` : `--author`, `-c user.name`, variables `GIT_*` compris), trailers, pied automatique | oui (`--no-verify`, hooks non actives) |
| `pre-push` | `git push` | chaque commit publie et absent du distant (`<ancien>..<nouveau>`, ou `<nouveau> --not --remotes=<distant>` pour une nouvelle branche) | oui (`--no-verify`) |
| CI `attribution` | push et PR GitHub | commits de l'evenement + titre et description de la PR (texte des squash merges) | non, **si** le job est exige par la protection de branche |
| Agents (PreToolUse) | avant une commande d'agent | refuse `--no-verify`, `commit -n`, changement de `core.hooksPath` | protege les hooks contre les agents |

Un hook local ne garantit jamais l'integrite du depot distant : seule une CI exigee par la protection de branche (ou un ruleset) bloque une fusion. Sans protection, la CI signale sans empecher. Les rebases et cherry-picks n'executent pas `commit-msg` : `pre-push` et la CI les controlent.

## Installation

### Ce depot (Forge-my-Project)

```bash
git config core.hooksPath .githooks          # pre-commit (existant, inchange), commit-msg, pre-push
python3 scripts/attribution_guard.py audit   # toutes les refs locales et de suivi distantes
```

Le job CI `Attribution Git (aucun agent IA auteur, committer ou co-auteur)` s'execute sur chaque push et PR. Au 15 novembre 2026, `main` n'a ni protection de branche ni ruleset : le job n'est donc pas encore bloquant. Le proprietaire l'impose (droits administrateur, action manuelle) :

```bash
gh api --method PUT "repos/{owner}/{repo}/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "checks": [
    { "context": "python" }, { "context": "CI generee des profils predefinis" },
    { "context": "Securite du depot (secrets, SAST)" },
    { "context": "Attribution Git (aucun agent IA auteur, committer ou co-auteur)" } ] },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

### Depots Git existants

```bash
python3 scripts/attribution_guard.py install ~/chemin/depot1 ~/chemin/depot2
# depots sous un dossier (relire la liste avant) :
find ~/Documents -name .git -type d -prune -printf '%h\n'
find ~/Documents -name .git -type d -prune -printf '%h\n' | xargs -r python3 scripts/attribution_guard.py install
```

- Installe `commit-msg`, `pre-push` et une copie du garde dans le dossier de hooks du depot (`git rev-parse --git-path hooks`, partage par tous ses worktrees).
- Un hook existant est conserve dans `<hook>.local` et execute apres le garde, avec les memes arguments et la meme entree standard. Reinstaller met a jour le garde sans autre effet.
- Si `core.hooksPath` pointe vers des hooks versionnes dans l'arbre de travail (`.githooks`, `.husky`...), rien n'est modifie : ajouter dans ces hooks `python3 <chemin>/attribution_guard.py commit-msg "$1"` et `... pre-push "$@"`, ou relancer avec `--allow-tracked` puis commiter le resultat.
- Retrait : `python3 scripts/attribution_guard.py uninstall <depot>` restaure les hooks d'origine.
- Historique existant : `python3 scripts/attribution_guard.py audit` dans le depot. L'outil ne reecrit jamais l'historique.

### Futurs depots (`git init`, `git clone`)

```bash
python3 scripts/attribution_guard.py install-template          # demande confirmation
python3 scripts/attribution_guard.py install-template --yes    # confirmation explicite, non interactive
```

- Installe le garde dans le modele Git (`init.templateDir` existant, sinon `~/.config/git/template`).
- `init.templateDir` global n'est modifie qu'apres confirmation (`o` ou `--yes`). Sans terminal ni `--yes`, il n'est pas modifie et la commande a executer est affichee. Une valeur existante est reutilisee, jamais remplacee.
- Limite : un `core.hooksPath` global fait ignorer les hooks du modele (avertissement affiche).

### Projets generes par Forge-my-Project

Chaque projet genere contient `scripts/hooks/attribution_guard.py`, l'appel du garde dans `.githooks/commit-msg` et `.githooks/pre-push`, le job CI `attribution` dans `.github/workflows/ci.yml`, la regle dans `AGENTS.md`, et le contexte de ce job dans la commande de protection de branche de `CONTRIBUTING.md`. Le garde respecte le lint et le formatage Ruff des projets Python generes.

## Maintenance

- Nouvel agent ou nouvelle identite de bot IA : completer `AI_AGENT` (ou `ATTRIBUTION_TRAILER` pour une nouvelle cle) dans `templates/hooks/attribution_guard.py.tmpl`, avec un cas refuse et un cas documentaire autorise dans `tests/test_attribution_guard.py`. Detection par mots entiers ; eviter les mots ambigus (prenoms comme Jules).
- Apres modification du garde : `python3 tests/smoke_generated.py` (Ruff des projets generes) et `python3 -m unittest tests.test_attribution_guard -v`. Ne pas introduire `{{` ni `}}` (moteur de templates).
- Depots deja installes : relancer `install` et `install-template` pour copier la nouvelle version ; les projets generes la recoivent a la generation suivante.
- Faux positif (personne reelle nommee comme un agent) : la regle fait du proprietaire le seul contributeur ; corriger l'identite plutot qu'affaiblir le motif.

## Historique

Audit du 15 novembre 2026 (`attribution_guard.py audit` et `git log --all` sur toutes les refs locales et de suivi distantes) : aucune attribution interdite. Les commits `11d0f4ca058da0f5f54fcd636c1e746c6a7280e5` (T10) et `e71a9507fe2ecddf85c0608cae00b5df0332665f` (T15), qui portaient `Co-Authored-By: Claude <noreply@anthropic.com>`, existent encore comme objets locaux mais ne sont atteignables depuis aucune branche ni aucun tag. E02 n'a reecrit aucun historique ni fait de push force.

Audit brut : `git log --all -i --format='%H %an <%ae> %cn <%ce>%n%B' | grep -i -E 'co-authored-by|noreply@anthropic.com'`.
