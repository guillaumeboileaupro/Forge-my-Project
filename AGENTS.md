# Forge-my-Project - instructions pour les agents

## Mission
Construire un generateur interactif, fiable et extensible qui produit des squelettes de projets avec architecture, regles agents, skills, hooks, securite, tests, CI/CD et documentation adaptes au questionnaire. Ne jamais presenter un squelette non operationnel comme securise ou deployable.

## Etat reel
- Serveur HTTP local: server.py; bind 127.0.0.1:8765.
- Formulaire web: ui/index.html (formulaire hybride du moteur) et ui/legacy.html (historique), assets ui/css et ui/js.
- Validation / creation ZIP: facade generator.py; implementation historique dans forge/config/legacy.py et forge/generator/legacy.py.
- Tests: tests/ (unitaires, API HTTP, recette Firefox headless activee par FORGE_E2E=1).
- Aucun package tiers requis pour le generateur.
- Moteur technique: forge/ (catalogs/, templates/), contrat dans docs/ENGINE.md; verification des registres uniquement sur demande explicite; formulaire hybride sur / (ui/index.html), formulaire historique sur /legacy. Aucun MCP n'est configure pour ce depot ; les projets generes recoivent une configuration MCP uniquement sur selection explicite (catalogs/mcp, T15).
- Apercu T16: `forge/filesystem/preview.py` revalide l'ensemble exact des fichiers edites et leur contenu (`forge/filesystem/content.py`) avant archive ou ecriture.
- Ecriture locale T17: `forge/filesystem/` (destination sous `FORGE_WRITE_ROOT` ou le dossier personnel, comparaison, jeton de validation, sauvegarde `.forge-backup/`, ecriture atomique et rollback); guide docs/LOCAL_WRITE.md. Les tests d'ecriture utilisent toujours un dossier temporaire.
- Formulaire historique (/legacy, generator.py): son pipeline est un modele volontairement bloquant. Le moteur (/) genere une CI operationnelle (.github/workflows/ci.yml), executee pour chaque profil predefini par le job `generated-projects` de ce depot.

## Architecture
Lire docs/ARCHITECTURE.md, docs/CONTRACTS.md et docs/DECISIONS/ avant de modifier les frontieres de modules.
Garder la validation de configuration independante de l'interface et des sorties.
Interdire les chemins arbitraires, les selections non autorisees et les operations reseau implicites.
Conserver la distinction entre generation de texte, verification et installation.

## Conventions
- Python 3.11+, stdlib par defaut; HTML/CSS/JS sans framework tant que cela suffit.
- Fonctions courtes, modules orientes responsabilite, entrees validees, erreurs explicites.
- Ne pas inventer de package, module, serveur MCP, action CI ni API. Verifier registre officiel, version, licence et documentation avant adoption.
- Codex et Claude Code peuvent developper en parallele, avec composants distincts, worktrees independants et petites PR rapidement fusionnables.
- Pas de modification de main sans demande explicite; ne jamais forcer un push.
- Eviter changements hors perimetre, commits de secrets et contournements des tests.
- Documentation en francais, commandes reproductibles.
- Regles detaillees de nommage, de PR et de fichiers generes: docs/CONVENTIONS.md.

## Commandes
```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q generator.py server.py tests
python3 server.py
git config core.hooksPath .githooks
```
Tester le formulaire sur http://127.0.0.1:8765 et les archives Python/JS avant de declarer un parcours valide.

## Pieges connus
- Formulaire historique (/legacy) uniquement : son mode TypeScript produit un squelette JavaScript ; le moteur (/) genere du TypeScript reel (tsconfig.json, sources .ts).
- Les projets generes ne contiennent pas de lockfile : la CI generee installe puis audite (pip-audit, npm audit) a chaque execution, sans reproductibilite exacte des versions transitives.
- Les hooks pre-commit, commit-msg et pre-push ne sont actifs qu'apres configuration du chemin Git.
- Le workflow du formulaire historique est intentionnellement rouge; celui du moteur doit rester vert: toute modification de catalogs/ci, templates/stack ou des commandes du catalogue se valide avec `python3 tests/smoke_generated.py --verify`.
- Security strict/hardened ne constitue pas une certification de securite.
- Des chemins ou descriptions fournis par l'utilisateur sont des donnees, jamais des commandes.

## Definition of Done
1. Le questionnaire et ses valeurs supportees sont documentes.
2. Tests positifs et negatifs, y compris archive ZIP et chemin de sortie; tests executes avec resultat trace.
3. Aucun package fictif ni API non documentee; tout ajout est verifie a la source officielle.
4. Pas de secrets, SAST/SCA/secrets et controle de provenance adaptes et operationnels ou limitations signalees.
5. Documentation et architecture mises a jour, comportement reproductible, retour utilisateur clair.
6. CI verte, revue de la PR et absence de severite haute/critique non resolue ni d'anomalie P0/P1 ouverte (docs/MAINTENANCE.md).
7. Le recapitulatif fournit tests effectifs, limites, fichiers modifies et risques residuels.

## Regles applicables au nouveau cycle de developpement

- Reference obligatoire: `docs/ROADMAP_2026.md` (34 decisions), `docs/SPECIFICATIONS.md`, `docs/DEVELOPMENT_PLAN.md` et la section E01-E18 de `TODO.md`.
- L'interface actuelle est consideree inadaptee; reconstruire son design et son ergonomie de zero tout en conservant le moteur et la totalite des fonctionnalites existantes. Validation visuelle, fonctionnelle, accessibilite et performances avant bascule.
- **Attribution Git reservee au proprietaire**: ne jamais ajouter `Co-Authored-By` pour Claude/Anthropic/Codex ou autres agents, ni utiliser un agent comme auteur ou committer. Verifier l'identite Git et les trailers avant commit et push. Des hooks locaux seuls ne constituent pas une garantie: renforcer via CI et protection de branche lorsque disponible. Outil: `scripts/attribution_guard.py` (commit-msg, pre-push, job CI `attribution`, installation dans les depots existants et futurs), voir docs/GIT_ATTRIBUTION.md.
- Plusieurs agents/PR en parallele mais taches courtes et fichiers non chevauchants. Pas de push force ni contournement des controles; synchroniser apres fusion et nettoyer de facon sure.
- Suivi **saisi manuellement** dans TODO: charge humaine estimee, execution IA mesuree, temps humain reel s'il est connu, ecart humain si calculable. Ne jamais presenter des minutes d'execution d'agent comme des heures de developpement humain; aucune conversion automatique de l'historique Git.
- Maintenance, anomalies (P0-P3), regressions et rollback: `docs/MAINTENANCE.md`. Toute PR qui change un comportement visible ajoute sa ligne dans `CHANGELOG.md` (`[Unreleased]`).
- Trois releases ciblees v1.0.0, v1.1.0, v2.0.0, criteres dans `docs/RELEASES.md`; seul le proprietaire publie une release. La piste extension VS Code dans `long-terme-ideas-project-liste.md` reste une idee, pas une tache active.
