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
| T02 | P1 | Reorganiser modules et modeles externes sans casser l'existant | T01 | 1 j | - | - | TODO | Contrats clairs, tests verts |
| T03 | P2 | Formulaire hybride, navigation et progression | T02 | 2 j | - | - | TODO | Parcours UI valides |
| T04 | P2 | Questions conditionnelles et validation | T03 | 1 j | - | - | TODO | Questions coherentes selon reponses |
| T05 | P2 | Profils, autosauvegarde et import/export JSON | T03 | 1 j | - | - | TODO | Reprise et import fiable |
| T06 | P3 | Catalogue technologies et compatibilites | T02 | 2 j | - | - | TODO | Configs incompatibles detectees |
| T07 | P3 | Moteur de regles et composition des templates | T06 | 2 j | - | - | TODO | Rendu deterministe et coherent |
| T08 | P3 | AGENTS.md et documentation complete personnalisee | T07 | 2 j | - | - | TODO | Aucun contenu fictif cache |
| T09 | P4 | Recuperer et selectionner les skills du depot my-skills | T07 | 1 j | - | - | TODO | Skills pertinents copies sans execution |
| T10 | P4 | Recherche et validation de skills externes | T09 | 2 j | - | - | TODO | Sources verifiees, accord utilisateur |
| T11 | P4 | Verifier packages, versions, compatibilites, API | T06 | 2 j | - | - | TODO | Packages inconnus rejetes |
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
