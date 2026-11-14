# TODO - Forge-my-Project

Reference: docs/SPECIFICATIONS.md et docs/DEVELOPMENT_PLAN.md.
Statuts: TODO, IN PROGRESS, BLOCKED, DONE. Les durees sont des estimations indicatives. Le temps reel et l'ecart restent a renseigner pendant le developpement.

## Cartographie
```text
T01 -> T02 -> T03 -> T04
        |      +-> T05
        +-> T06 -> T07 -> T08 -> T10 -> T14 -> T18
                        |      +-> T09 -> T10 -> T15 -> T18
                        |      +-> T11 -> T12 -> T13 -> T18
                        |      +-> T16 -> T17 -> T18
```
Le graphe est indicatif: la colonne Depend de fait foi.

## Taches
| ID | Phase | Travail | Depend de | Estime | Reel | Ecart | Statut | Critere de fin |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| T01 | P1 | Auditer le prototype et corriger ses defauts | - | 1 j | 0 h 05 | -7 h 55 (base 8 h/j) | DONE | Tests serveur/ZIP et JS reproductibles |
| T02 | P1 | Reorganiser modules et modeles externes sans casser l'existant | T01 | 1 j | - | - | DONE | Contrats clairs, tests verts |
| T03 | P2 | Formulaire hybride, navigation et progression | T02 | 2 j | en cours | - | IN PROGRESS | Parcours UI valides |
| T04 | P2 | Questions conditionnelles et validation | T03 | 1 j | en cours | - | IN PROGRESS | Questions coherentes selon reponses |
| T05 | P2 | Profils, autosauvegarde et import/export JSON | T03 | 1 j | 0 h 09 | -7 h 51 (base 8 h/j) | DONE | Reprise et import fiable |
| T06 | P3 | Catalogue technologies et compatibilites | T02 | 2 j | 0 h 13 | -15 h 47 (base 8 h/j) | DONE | Configs incompatibles detectees |
| T07 | P3 | Moteur de regles et composition des templates | T06 | 2 j | 0 h 02 | -15 h 58 (base 8 h/j) | DONE | Rendu deterministe et coherent |
| T08 | P3 | AGENTS.md et documentation complete personnalisee | T07 | 2 j | 0 h 03 | -15 h 57 (base 8 h/j) | DONE | Aucun contenu fictif cache |
| T09 | P4 | Recuperer et selectionner les skills du depot my-skills | T07 | 1 j | 0 h 03 | -7 h 57 (base 8 h/j) | DONE | Skills pertinents copies sans execution |
| T10 | P4 | Recherche et validation de skills externes | T09 | 2 j | 0 h 03 | - | IN PROGRESS | Sources verifiees, accord utilisateur |
| T11 | P4 | Verifier packages, versions, compatibilites, API | T06 | 2 j | 0 h 03 | -15 h 57 (base 8 h/j) | DONE | Packages inconnus rejetes |
| T12 | P5 | GitHub Actions generees et verifiees | T07,T11 | 2 j | - | - | TODO | Pipelines reels pour stacks supportees |
| T13 | P5 | Controles securite stricts et rapports | T11,T12 | 2 j | - | - | TODO | Scans applicables et blocage fiable |
| T14 | P5 | Hooks Git et agents suivant leurs capacites | T07 | 1 j | - | - | TODO | Hooks activables et executes |
| T15 | P5 | MCP optionnels verifies et valides | T10 | 1 j | - | - | TODO | Aucun MCP fictif ni secret |
| T16 | P6 | Explorateur, apercu et edition des fichiers | T08 | 2 j | - | - | TODO | Modifications visibles avant ecriture |
| T17 | P6 | Diff, fusion assistee, sauvegarde, ecriture locale | T16 | 2 j | - | - | TODO | Conflits et rollback testes |
| T18 | P7 | Tests finaux, corrections, docs et rapport | T01-T17 | 3 j | - | - | TODO | Critères de finalisation valides |
| **Total** | | | | **30 j** | **-** | **-** | | |

## Ordre de travail
Commencer par T01. Une seule PR ouverte et un seul agent de developpement a la fois. Actualiser les colonnes Reel/Ecart apres chaque tache et noter les preuves CI dans la PR.

## Etat existant
Le serveur local, le formulaire initial, le ZIP, AGENTS.md, une bibliotheque initiale de skills, des docs et une CI du depot existent. Les fonctions cible non implementees ne doivent pas etre marquees DONE.

## Notes de suivi
Pour chaque tache terminee: commande et resultat des tests, lien du run CI, impact securite, fichiers modifies, temps reel, blocages et risque residuel. Aucune tache DONE sans preuve.

### T01 - 14 novembre 2026
- Temps reel mesure: 0 h 05, de la creation de la branche dediee a la premiere CI de PR verte.
- Tests: `python3 -m unittest discover -s tests -v` PASS, 20 tests; `python3 -m compileall -q generator.py server.py tests` PASS.
- Archives: 64 combinaisons supportees controlees, chemins ZIP bornes a la racine, tests generes Python et `npm test` executes avec succes.
- Serveur et formulaire: integration HTTP loopback PASS; rendu Firefox headless PASS; contrat des champs et options PASS.
- Securite: validation stricte des champs, de `Host` et du type JSON; en-tetes navigateur durcis; recherche ciblee de secrets sans correspondance.
- CI: [push PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43583433146) et [PR PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43583453284).
- NON VERIFIE: Bandit, Semgrep et Gitleaks absents. `pip check` signale des incoherences de l'environnement Anaconda global, sans dependance tierce du projet.
- Risques restants hors T01: profil nomme TypeScript mais base JavaScript, workflow genere volontairement bloquant, absence de lockfiles et fonctions T02-T18 non implementees.

### T02 - 14 novembre 2026 (Codex, PR #5)
- Fusionnee apres CI verte (runs 43584707105 et 43584848078). Temps reel non renseigne par Codex.

### T06-T11 - 14 novembre 2026 (Claude Code, PR #6)
- Temps reels mesures sur l'historique Git: branche creee a 10 h 54; commits T06 11 h 07, T07 11 h 09, T08 11 h 12, T11 11 h 15, T09 11 h 18, T10 11 h 21; fusion 11 h 28 (total 0 h 34).
- Tests: `python3 -m unittest discover -s tests` PASS, 90 tests apres synchronisation avec T02; pyflakes sans alerte.
- CI: [push PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43585339901) et [PR PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43585342252) (Python 3.11).
- Verifications reelles: package fictif rejete; django 3.0.0 et lodash 4.17.15 bloques (GHSA haute/critique); Node 20 et Python 3.9 bloques (fin de vie); 6 skills my-skills copies au commit 16cddc53, scripts ignores.
- T10 reste IN PROGRESS: recherche et approbation disponibles dans le moteur et la CLI, pas encore dans l'interface.
- NON VERIFIE: API des packages (pas d'installation); licence PyPI = derniere version publiee.

### Integration moteur/formulaire - 14 novembre 2026 (Claude Code, PR #8)
- Formulaire hybride sur `/`, API locale `/api/catalog|plan|archive`, formulaire historique sur `/legacy`; recette Firefox headless en CI.
- Temps reel: 11 h 28 (fusion PR #6) -> 11 h 35 (CI verte), fusion par l'utilisateur a 11 h 43.
- T03/T04 restent IN PROGRESS: la liste des 40 choix valides n'est pas dans le depot, couverture complete non verifiable.

### T05 - 14 novembre 2026 (Claude Code)
- Temps reel: 11 h 44 -> 11 h 53 (0 h 09) jusqu'a la PR; CI et fusion notees dans la PR.
- Profils predefinis (6, chacun genere un plan valide), profils personnels CRUD dans un fichier local 0600 a ecriture atomique, sauvegarde automatique (`localStorage`, ecriture immediate a la fermeture) revalidee avant restauration, import/export JSON valide par le serveur.
- Tests: unitaires et HTTP (`tests/test_profiles.py`), recette Firefox (`FORGE_E2E=1`): restauration des choix conditionnels, brouillon incompatible ignore, cycle de vie des profils, export puis import, JSON invalide et configuration incompatible refuses. Recette executee 3 fois de suite sans echec.
- Defaut corrige pendant la recette: une modification suivie d'un rechargement en moins de 300 ms etait perdue; sauvegarde forcee sur `pagehide`.
- Limites: les approbations de skills externes importees ne sont pas conservees par l'interface (avertissement affiche); le brouillon est propre au navigateur.

