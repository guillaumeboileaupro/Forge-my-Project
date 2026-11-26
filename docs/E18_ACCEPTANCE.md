# Recette E18 — parcours v2 et bascule

Recette globale de `/v2/parcours` avec la coque (E15), l'atelier (E17) et la parité (E18b), avant la bascule. L'interface actuelle (`/`) reste la référence et l'entrée par défaut tant que le propriétaire n'a pas validé la bascule.

Statuts : **PASS** = vérifié par un test automatisé exécuté en CI ; **EN ATTENTE** = action ou décision du propriétaire ; **À FAIRE** = travail restant.

## Conditions de bascule (docs/UI_V2_CONTRACTS.md, « Gates avant bascule »)

| Condition | Preuve | Statut |
| --- | --- | --- |
| Parité de parcours | Matrice ci-dessous ; `tests/test_e2e_parity_firefox.py` (9 tests) | PASS |
| Tests serveur/JS | Suite `python3 -m unittest discover -s tests` (job `python`) ; contrats statiques `tests/test_journey_v2.py` | PASS |
| Firefox | Étape Firefox du job `python` : v1, parcours, éditeur, coque, atelier, recette, parité | PASS |
| Clavier | `test_whole_journey_with_the_keyboard_only`, ordre de tabulation, palette, onglets, séparateurs (E15, E17, E18a) | PASS |
| Deux thèmes | Thème forcé et thème système sombre, contrastes rendus (E18a) | PASS |
| Cinq résolutions | 360 (zoom), 768, 1280, 1440, 1920 et ruptures 767/1199/1200 (E18a, E15) | PASS |
| Contrastes | Chaque texte visible, deux thèmes, 4,5:1 ou 3:1 (E18a) | PASS |
| Budgets mesurés | Lignes `E18A-BUDGET` du journal CI ; dernières valeurs locales : premier rendu 144 ms, aperçu 404 ms, interactions ≤ 66 ms | PASS (machine de référence à fixer) |
| Captures approuvées | 30 captures, voir ci-dessous | EN ATTENTE |
| Lecteur d'écran | Checklist Orca ci-dessous | EN ATTENTE |
| CI verte | Dernières exécutions de `main` | PASS |
| Absence de P0/P1 | Revue indépendante non faite (auto-revues seulement) ; remarques P1 des revues automatiques traitées (PR #55) ou non applicables (commits inexistants ou historiques) | À FAIRE |

## Parité avec l'interface actuelle

| Fonction de `/` (ui/js/app.js) | Dans `/v2/parcours` | Preuve |
| --- | --- | --- |
| Questionnaire conditionnel, versions, agents, sécurité, MCP | Étapes 1 à 6 | `test_e2e_journey_firefox.py` |
| Brouillon automatique et restauration | Section « Réponses » (même clé, revalidé par le serveur) | `test_draft_is_saved_restored_reset_and_an_incompatible_one_ignored`, `test_unfinished_first_step_survives_a_reload` |
| Export et import JSON | Section « Réponses » | `test_export_then_import` |
| Réinitialisation | Section « Réponses » (confirmée) | `test_draft_is_saved_restored_reset_and_an_incompatible_one_ignored` |
| Profils prédéfinis et personnels | Section « Réponses » | `test_profiles_lifecycle` |
| Architecture manuelle et suggestion | Étape Projet | `test_manual_architecture_and_local_suggestion` |
| Skills externes (recherche, approbation, vérification) | Étape 7 | `test_external_skills_search_approval_verification_and_online_check` |
| Vérification en ligne (packages, skills) | « Vérifier en ligne » | même test ; `test_online_check_can_be_retried_after_a_failure` |
| Aperçu et édition des fichiers | Arborescence, diagramme, éditeur à onglets | `test_e2e_editor_firefox.py`, `test_e2e_workbench_firefox.py` |
| Contrôles NON VERIFIE à confirmer | Validation et écriture | `test_unverified_needs_confirmation_and_critical_blocks` |
| Archive ZIP | « Télécharger l'archive ZIP » | `test_archive_after_validation` |
| Écriture locale (comparaison, conflits, fusion) | Validation et écriture | `test_validate_compare_write_then_conflict_kept`, parcours clavier |
| Protection de branche GitHub | Section dédiée | `test_branch_protection_command_is_prepared_never_applied` |
| Formulaire historique `/legacy` | Lien conservé dans l'interface actuelle | inchangé |

Différence assumée : la v2 calcule l'aperçu automatiquement (hors ligne) et ne lance le réseau que sur « Vérifier en ligne » ; l'interface actuelle n'avait qu'un bouton « Vérifier la configuration ».

## Captures à approuver

30 captures générées le 26/11/2026 par la recette Firefox (5 largeurs × 2 thèmes × questionnaire, aperçu, atelier), coque, atelier et parité compris. Elles ne sont pas versionnées. Pour les régénérer dans un dossier ignoré du dépôt :

```
mkdir -p .tmp-shots/e18
FORGE_E2E=1 FORGE_E2E_SCREENSHOTS=$PWD/.tmp-shots/e18 python3 -m unittest \
  tests.test_e2e_acceptance_firefox.FirefoxAcceptanceTests.test_reference_resolutions_and_breakpoints \
  tests.test_e2e_acceptance_firefox.FirefoxPhoneDarkTests
```

Le propriétaire approuve ou liste les défauts visuels ; chaque défaut devient une correction testée avant la bascule.

## Checklist lecteur d'écran (Orca, Firefox)

Orca est installé sur le poste du propriétaire ; aucun lecteur d'écran n'est disponible en CI. Lancer `python3 server.py`, ouvrir `/v2/parcours` dans Firefox, activer Orca (`Super+Alt+S`) et cocher chaque point. Un point en échec est noté avec l'annonce entendue.

1. Le titre de la page et le lien « Aller au questionnaire » sont annoncés ; le lien amène au questionnaire.
2. Les boutons du rail annoncent leur nom (« Panneau Étapes »…) et leur état pressé.
3. La barre de progression annonce « n étape(s) complète(s) sur m ».
4. Chaque étape annonce son titre au changement d'étape ; les cases et boutons radio annoncent libellé et état.
5. Le retrait d'une réponse devenue invalide est annoncé (zone d'état de l'étape).
6. Les mises à jour de l'aperçu (« Aperçu à jour… », « Aperçu périmé… ») sont annoncées sans voler le focus.
7. Les onglets Plan/Résumé et les onglets de fichiers annoncent « onglet, sélectionné, n sur m » ; flèches et Entrée fonctionnent.
8. Les séparateurs annoncent leur valeur et la changent aux flèches.
9. La palette (`Ctrl+K`) annonce la liste et l'option active ; Échap rend le focus au déclencheur.
10. L'éditeur annonce le chemin du fichier et l'état modifié ; la recherche annonce le nombre de résultats.
11. Les diagnostics annoncent leur gravité ; « Aller à » amène au champ concerné.
12. La section « Réponses » annonce la sauvegarde automatique et les erreurs d'import (alerte).
13. Les skills annoncent « source reconnue / non reconnue » et la décision prise.
14. La validation, la comparaison et l'écriture annoncent chaque résultat ; la confirmation d'écriture est lisible avant validation.

## Bascule (après approbation uniquement)

Proposition, non appliquée : `/` sert le parcours v2 ; l'interface actuelle reste disponible sur une route dédiée pendant au moins une version mineure ; `/legacy` inchangé ; le brouillon est déjà partagé (même clé). La bascule est une PR distincte, ouverte seulement après l'approbation des captures et de la checklist, avec une entrée « Modifie » au changelog (v2.0.0, docs/RELEASES.md).
