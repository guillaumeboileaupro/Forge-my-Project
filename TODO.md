# TODO - Cartographie et suivi de Forge-my-Project

Mise a jour: 2026-11-14. Etat base sur le code du depot, pas une execution de recette exhaustive.

## Legende
- [ ] TODO - a faire
- [x] DONE - implemente dans le depot (ne signifie pas validation complete)
- Priorites P0 (bloquant), P1 (important), P2 (amelioration).
- Charges en journees de developpement estimees, hors delais externes.
- Toujours renseigner preuve et resultat avant de cocher.

## Carte des modules
```text
[UI index.html]
       |
       v
[server.py] -> [config/validation] -> [planner] -> [templates]
                                           |          |
                                           v          v
                                     [packages]   [code + docs]
                                     [MCP]        [agents + skills]
                                           \        /
                                            [audit / tests]
                                                  |
                                         [preview + ZIP]
                                                  |
                                         [GitHub opt-in]
```
Aujourd'hui: UI, serveur, validation et ZIP sont dans index.html/server.py/generator.py. Les blocs planner/packages/MCP/audit sont cibles, pas encore implementes.

## Taches ordonnees et dependances

| ID | Priorite | Tache | Depend de | Charge | Etat | Critere de fin |
| --- | --- | --- | --- | ---: | --- | --- |
| T01 | P0 | Tester serveur, generation ZIP, chemins/erreurs | - | 0.5 j | TODO | Tests automatises PASS |
| T02 | P0 | Corriger profil JS/TypeScript et script npm | T01 | 1 j | TODO | npm test passe dans le ZIP |
| T03 | P0 | Valider la CI du depot et ses preuves | T01 | 0.5 j | TODO | Run CI vert |
| T04 | P0 | Definir schema JSON versionne | T01 | 1 j | TODO | Validation de tous les champs |
| T05 | P0 | Formulaire guide conditionnel et recapitulatif | T04 | 2 j | TODO | Scenarios UI PASS |
| T06 | P0 | Planner et matrice des stacks | T04 | 2 j | TODO | Choix incompatibles refuses |
| T07 | P0 | Catalogue templates et code de base reel | T02,T06 | 3 j | TODO | Smoke tests sur toutes les stacks |
| T08 | P0 | Verifier noms PyPI/npm, versions et API | T06 | 3 j | TODO | Package fictif rejete |
| T09 | P0 | Lockfiles, licences et advisories | T08 | 2 j | TODO | Install reproductible + audit |
| T10 | P0 | AGENTS.md, conventions et Definition of Done adaptes | T07 | 1 j | TODO | Contrat et commandes valides |
| T11 | P0 | Skills conditionnels et hooks actives/valides | T10 | 1.5 j | TODO | Test des hooks et skills |
| T12 | P0 | Catalogue MCP valide et permissions minimales | T08,T10 | 1.5 j | TODO | Aucun serveur invente ni token |
| T13 | P0 | CI generee operationnelle pour chaque profil | T07,T09 | 2 j | TODO | Runs verts, echec sur regression |
| T14 | P0 | Scans SAST/SCA/secrets, SBOM, rapport | T09,T13 | 3 j | TODO | Rapports et controles bloquants |
| T15 | P1 | Apercu arbre/diff et export config | T05,T07 | 1.5 j | TODO | Recap et ZIP conformes |
| T16 | P1 | Export GitHub explicite, branche/PR | T15,T14 | 2 j | TODO | Confirmation obligatoire |
| T17 | P1 | Documentation Docker/S3NS/OUTSCALE verifiee | T13 | 2 j | TODO | Profils prouves ou NON VERIFIE |
| T18 | P0 | Recette e2e, docs, bilan des risques | T11-T17 | 3 j | TODO | Gates G1-G10 satisfaites |
| **TOTAL** | | **Charge indicative des taches** | | **30 j** | | **A reestimer selon choix** |

## Existant (a ne pas confondre avec fini)
- [x] Serveur HTTP local et formulaire HTML initial.
- [x] generateur ZIP basique et validation de certaines options.
- [x] AGENTS.md du depot et six skills de developpement.
- [x] Docs initiales architecture, securite et conventions.
- [x] CI Python definie dans le depot.
- [ ] Verifier resultat CI reel avant affirmation de PASS.
- [ ] Verifier que tous les squelettes generes fonctionnent.

## Prochain travail autorise
Commencer T01, puis T02 et T03. Conserver une seule PR de developpement ouverte. Ne pas attaquer les MCP ou le cloud avant la validation du socle.

## Bilan par changement
A chaque PR, ajouter: ID des taches, temps passe, commandes et resultats, liens CI, fichiers modifies, risques, gates PASS/FAIL/NON VERIFIE. Si une tache est bloquee, renseigner la cause et la condition de reprise.
