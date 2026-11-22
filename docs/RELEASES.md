# Plan des releases

Versions publiees : **v1.0.0** (tag sur `9effa1d`) et **v1.1.0** (tag sur le commit de release de main), le 19 novembre 2026. Notes : CHANGELOG.md. Les conditions communes de publication et la procedure de retour arriere sont dans [MAINTENANCE.md](MAINTENANCE.md), sections 6 et 7. Chaque critere ci-dessous se coche avec la preuve (PR, run CI, commande et resultat), jamais sur declaration.

Statuts des taches : [../TODO.md](../TODO.md). Criteres d'acceptation detailles : [ROADMAP_2026.md](ROADMAP_2026.md).

## v1.0.0 - depot propre et installable sous Linux

| Critere | Taches | Preuve attendue | Etat |
| --- | --- | --- | --- |
| Refs Git auditees et nettoyees, sans perte | E01 | docs/E01_REFS_AUDIT.md, PR #27 | fait |
| Attribution Git reservee au proprietaire, controlee en local et en CI | E02 | docs/GIT_ATTRIBUTION.md, PR #26 | fait |
| Fichiers du depot audites, aucune suppression sans preuve | E03 | docs/E03_CLEANUP_AUDIT.md, PR #28 | fait |
| Installation et demarrage Linux valides depuis un clone propre | E04 | `installer.sh` / `start.sh` testes, PR #25 | fait : PR #25 ; `installer.sh` puis `start.sh` executes depuis un clone propre de 9effa1d le 19/11 (page et API en HTTP 200) |
| Maintenance, anomalies, changelog et plan de releases documentes et controles par CI | E05 | docs/MAINTENANCE.md, CHANGELOG.md, `tests/test_release_policy.py`, PR #29 | fait (PR #29) |
| Tests et CI verts sur le commit etiquete | - | 4 jobs CI verts, `smoke_generated.py --verify` | fait : CI de 9effa1d relancee le 19/11 (run 44320746923, tentative 2) : 4 jobs verts, dont la CI generee avec `--verify` |
| Aucune anomalie bloquante | - | aucune issue P0/P1 ouverte | fait : aucune issue ouverte le 19/11 |

Limites a reporter dans le changelog de v1.0.0 : exceptions d'audit actives (registre de docs/SECURITY.md, actuellement GHSA-fc5q-39xc-vjpf jusqu'au 2026-12-17) ; la protection de branche de main n'est pas configuree (le job attribution n'est donc pas obligatoire) ; Q14 partiel et Q15 non construit (nettoyage automatise des worktrees) ; refs GitHub `refs/pull/*` contenant d'anciens trailers.

## v1.1.0 - lever les trois exigences partielles

| Critere | Taches | Preuve attendue | Etat |
| --- | --- | --- | --- |
| Fusion automatique a trois voies avec base fiable, fusion manuelle sinon, sauvegarde et rollback conserves | E07 | tests fusion propre, conflit, sans base, concurrence, echec d'ecriture, restauration | fait (PR #32) |
| Infrastructure E2E des projets generes, sans scenario metier invente | E08 | TESTING.md et harnais generes par stack, commande temoin verte | fait (PR #35) |
| Assistant de protection de branche : commandes preparees, jamais appliquees automatiquement | E09 | commandes conformes aux jobs reels, testees | fait (PR #36) |
| Conditions communes de release | - | MAINTENANCE.md section 6 | fait : voir TODO.md (release du 19/11) |

## v2.0.0 - nouvelle interface et ameliorations

| Critere | Taches | Preuve attendue | Etat |
| --- | --- | --- | --- |
| Reconstruction complete de l'interface (pas un relooking), ancienne UI conservee jusqu'a validation | E14, E15, E16, E17 (sous-lot E17a) | design system revu, coque, parcours, editeur et diagnostics testes | a faire |
| Ameliorations de securite | E06, E10, E11 | NON VERIFIE confirme et journalise ; Docker et Semgrep bloquants ; verification statique des API | E06 fait (PR #31) ; E10 et E11 a faire |
| Enrichissement des catalogues et des stacks | E12, E13 | skills et stacks testes, catalogue local borne | a faire |
| Validation fonctionnelle et visuelle complete | E18 (sous-lot E18a) | captures approuvees, Firefox, clavier, accessibilite, performances, resolutions | a faire |
| Conditions communes de release | - | MAINTENANCE.md section 6 | a verifier a la release |

v2.0.0 est MAJEUR parce que l'interface et les parcours changent pour l'utilisateur. Une incompatibilite des formats (profils, API locale) devra etre listee dans la rubrique Modifie du changelog avec sa migration.
