# Moteur technique (forge/)

Taches T06-T11. Bibliotheque standard Python 3.11+, aucun modele d'IA, aucune generation de code metier, aucune ecriture disque : le moteur produit un apercu `{chemin: contenu}` que l'interface (T16/T17) affiche, fait modifier et ecrit apres validation.

## Point d'entree

```python
from forge.pipeline import run

result = run(config, verify=False, skills=False)  # aucune requete reseau
result.files        # {chemin relatif: contenu}
result.diagnostics  # Diagnostic(code, severity error|warning|info, message, subject)
result.as_dict()    # rapport JSON (ok, regles, fichiers, diagnostics, verification, skills)
```

- `verify=True` : verification en ligne des packages, versions, vulnerabilites et runtimes (T11).
- `skills=True` : recuperation des skills my-skills et des skills externes approuves (T09/T10).
- Une erreur bloquante leve `forge.diagnostics.ForgeError` avec ses diagnostics.
- Recherche de skills externes (candidats, aucune copie) : `forge.skills.service.search_for_plan(plan)`.

CLI equivalente (apercu uniquement) :

```bash
python -m forge plan spec.json [--verify] [--skills]
python -m forge show spec.json AGENTS.md
python -m forge skills-search spec.json
```

## Configuration d'entree (schema_version 1)

| Champ | Type | Regle |
| --- | --- | --- |
| name | texte | 3-50 caracteres, minuscules, chiffres, tirets |
| description | texte | 2000 caracteres max, optionnel (sinon avertissement) |
| project_type | choix | library, cli, api, web |
| technologies | liste | identifiants du catalogue (au moins une) |
| versions | objet | id -> version (`"3.12"`), sinon version preferee du catalogue |
| agents | liste | codex, claude, copilot (au moins un) |
| security | choix | strict (defaut), hardened |
| architecture | texte | 4000 caracteres max ; prioritaire sur la suggestion |
| options | objet | `{"mcp": false}` |
| external_skills | liste | approbations `{repository, commit (SHA complet), path, name}` |

Les textes libres sont des donnees : jamais reinterpretes comme modele ni commande.

## Donnees externes (editables, validees avant usage)

- `catalogs/technologies/` : categories (bornes min/max, commandes requises) et technologies (`requires`, alternatives `[[a, b]]`, `conflicts`, `constraints` de version, `commands`, package du registre, versions supportees, documentation officielle https).
- `catalogs/rules/` : regles declaratives. `base` est obligatoire ; les autres s'appliquent selon `when` (`technologies_all/any`, `agents_any`, `project_types`, `security`, `options`). Elles ajoutent des fichiers (template -> chemin), des phrases par section et des skills recommandes. Ordre deterministe (priorite, id) ; deux regles produisant le meme fichier sans `override` = erreur.
- `templates/` : modeles de documents (`{{ var }}`, `{{#if}}`, `{{#each}}`, `{{else}}`, `{{! commentaire }}`) ; aucune evaluation de code, variable inconnue = erreur.
- `catalogs/skills/sources.json` : depot my-skills, catalogues externes reconnus, politique de copie.

Ajouter une technologie : une entree JSON dans le bon fichier de categorie, puis `python3 -m unittest discover -s tests`.

## Etats et blocages

| Situation | Resultat |
| --- | --- |
| Technologie inconnue, dependance manquante, conflit, version non supportee ou hors contrainte | erreur bloquante |
| Package inexistant, version absente/retiree, vulnerabilite haute ou critique, runtime en fin de vie | erreur bloquante (avec `verify`) |
| Registre ou service injoignable, severite inconnue, API d'un package | NON VERIFIE (avertissement), jamais PASS |
| Commande de test inconnue, description vide, architecture non definie | avertissement ; rendu `NON DEFINI` |
| Skill absent, rejete, indisponible ou contenant une commande a risque | avertissement |

## Reseau

Uniquement sur demande (`verify`, `skills`, `skills-search`), en HTTPS vers une liste fermee : pypi.org, registry.npmjs.org, api.osv.dev, endoflife.date, api.github.com, raw.githubusercontent.com (redirections controlees). Pour GitHub, la CLI `gh` authentifiee est reutilisee si presente (le jeton reste gere par gh), sinon acces anonyme aux depots publics.

## Skills

- Selection : skills recommandes par les regles appliquees.
- Lecture a un commit epingle ; copie des seuls fichiers texte (.md, .yaml, .yml, .json, .txt) dans `.agents/skills/` (Codex) et `.claude/skills/` (Claude Code). Scripts, executables, liens et binaires ne sont jamais telecharges et sont listes dans `docs/SKILLS.md`.
- Skills externes : candidats de catalogues reconnus (et recherche GitHub si gh est authentifie, marques « source non reconnue ») ; copie uniquement apres approbation explicite enregistree dans `external_skills`, au commit approuve.

## Limites connues

- Les API des packages ne sont pas verifiees automatiquement (etat NON VERIFIE explicite).
- La licence PyPI est celle de la derniere version publiee.
- La recherche de skills externes lit chaque SKILL.md des catalogues reconnus : plusieurs dizaines de secondes.
- Le catalogue couvre Python et Node.js/TypeScript ; toute autre pile est refusee comme inconnue.
- Le moteur est branche sur le formulaire hybride (`/`, API `/api/*`, voir docs/CONTRACTS.md) ; `generator.py` et `/legacy` restent l'ancien parcours, inchange.
- L'interface ne propose pas encore la recherche/approbation des skills externes (CLI uniquement), ni l'edition des fichiers avant ecriture (T16) ni l'ecriture locale (T17) : la sortie est un ZIP.
