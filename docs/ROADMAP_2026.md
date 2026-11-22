# Feuille de route validee - 34 decisions (15 novembre 2026)

## Statut et regles

Source: questionnaire utilisateur termine: 24 decisions de finalisation + 10 decisions UI. Ce document complete les 18 taches historiques terminees; il ne les remet pas a zero.
Produit personnel, **Linux uniquement**. Python 3.11+ requis. Conserver le moteur et toutes les fonctions validees.

Regle incontournable: aucun agent IA (Claude, Anthropic, Codex ou autre) ne doit apparaitre comme auteur, committer ou co-auteur Git. Refuser les trailers d'attribution automatique; analyser l'historique des branches et des PR avant de declarer le nettoyage termine. Ne jamais inventer de contributeur. Les mecanismes CI ne sont efficaces que si leur reussite est imposee sur la branche de destination; les hooks locaux seuls sont contournables.

Codex et Claude Code developpent **en parallele** sur des fichiers distincts, avec des worktrees independants, des petites PR a fusionner rapidement, des tests et une revue avant fusion. Charge humaine estimee, execution IA mesuree, temps humain reel et ecart humain: saisie **manuelle**, definitions dans TODO.md (regle de suivi). Les minutes d'execution d'un agent ne sont jamais presentees comme des heures de developpement humain. Pas de chronometre ou de calcul Git automatique.

## Releases et dependances

- **v1.0.0** apres audit/nettoyage securise des branches, worktrees et fichiers et validation du lancement Linux.
- **v1.1.0** apres resolution des trois exigences partielles: fusion a trois voies lorsque possible, infrastructure E2E vide prete a completer, assistant de protection de branche produisant des commandes manuelles.
- **v2.0.0** apres refonte complete de l'interface et toutes les ameliorations retenues.
- Chaque release: tests verts, controle de securite, changelog, limites explicites et absence de bug bloquant. Les numéros sont cibles, a ajuster si necessaire. Plan et criteres: [RELEASES.md](RELEASES.md); politique: [MAINTENANCE.md](MAINTENANCE.md).

## Lots de travail (nouveaux identifiants E01-E18)

| ID | Travail | Priorite | Agent propose | Depend de | Charge humaine estimee | Execution IA mesuree | Ecart humain | Statut | Critere d'acceptation verifiable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | Auditer les refs Git, archiver liste des branches docs/*, supprimer les branches exclusivement integrees, sans toucher aux worktrees sales | P1 | Claude | - | 0,5 j | 0 h 04 (Claude) | non calculable | DONE | Inventaire nom/SHA archive; simulation puis nettoyage sans branche non fusionnee ni worktree sale supprime |
| E02 | Installer une protection d'attribution Git pour les depots actuels et futurs, tester commit-msg/pre-push et CI, auditer les refs anciennes | P1 | Claude | - | 1 j | 0 h 40 (Claude, attente CI comprise) | non calculable | DONE | Commits auteur/committer/trailer IA refuses localement et en CI; audit des refs publie |
| E03 | Auditer et nettoyer fichiers temporaires, doublons, anciennes configurations et scripts obsoletes avec preuve de non-regression | P2 | Claude | E01 | 1 j | 0 h 12 (Claude) ; Codex non mesure | non calculable | DONE | Inventaire justifie; suppressions revues; suite complete et generation des profils sans regression |
| E04 | Verifier les scripts d'installation existants et la PR de lanceur avant de creer installer.sh/start.sh sous Linux | P1 | Codex | - | 8 h | 0 h 19 (Codex, reprises cumulees) | non calculable | DONE | Installation et demarrage sur Linux propre testes; aucun lanceur concurrent ou promesse multi-OS |
| E05 | Politique de releases, anomalies, changelog, maintenance securite et tests reguliers | P1 | Claude | E01 | 1 j | 0 h 32 (Claude, dont anomalie P0 PR #30; hors attente CI finale) | non calculable | DONE | Regles de version, changelog, triage et cadence de maintenance documentes et controles par CI |
| E06 | Confirmation explicite pour controles NON VERIFIE, journalisation et revalidation avant ecriture | P1 | Claude | - | 1 j | 0 h 17 (Claude) | non calculable | DONE | Tout NON VERIFIE est explique, confirme et journalise; changement ou refus bloque l'ecriture |
| E07 | Fusion automatique a trois voies quand une base fiable existe, sinon resolution manuelle, sauvegarde et rollback | P2 | Codex | - | 2 j (16 h) | Codex non mesure ; Claude 0 h 07 (reprise) | non calculable | DONE | Fusion propre et conflit testes avec base fiable; sans base, mode manuel; rollback restaure les octets initiaux |
| E08 | Infrastructure E2E des projets generes, adaptee a la stack, sans scenarios metier inventes | P2 | Claude | - | 2 j | 0 h 13 (Claude) | non calculable | DONE | TESTING.md et harnais E2E generes par stack; commande temoin passe sans scenario metier fictif |
| E09 | Assistant de protection de branche GitHub: preparer les commandes, ne pas appliquer automatiquement | P2 | Codex | - | 1 j | Codex non mesure ; Claude 0 h 05 (reprise) | non calculable | DONE | Commandes conformes aux checks reels, affichables et testees; aucune mutation GitHub sans execution utilisateur |
| E10 | Scanner d'images Docker et SAST complementaire dont Semgrep, sans retrait des controles actuels | P1 | Claude | - | 2 j | - | - | TODO | Images applicables et code scannes; fixtures haute/critique bloquent; scans existants restent actifs |
| E11 | Verification statique des API Python/JS/TS lorsque possible; PASS/FAIL/NON VERIFIE | P2 | Claude | - | 2 j | - | - | TODO | Contrats valides, invalides et invérifiables classes PASS/FAIL/NON VERIFIE avec preuves par langage |
| E12 | Recherche des skills: cache expire, parallelisme, classement, reverification avant copie | P2 | Claude | - | 2 j | - | - | TODO | Expiration, recherches paralleles, classement deterministe et changement amont avant copie testes |
| E13 | Enrichir les stacks Python/JS/Rust/Go/Java et permettre les catalogues/regles personnalises localement | P2 | Claude | - | 4 j | - | - | TODO | Chaque stack produit un squelette testable; catalogue local valide, borne et sans execution implicite |
| E14 | Definir le design system et les contrats de la nouvelle UI avant de coder | P1 | Codex + Claude | - | 2 j | en cours | non calculable | IN PROGRESS | Tokens, composants, etats, accessibilite, responsive et contrats moteur/UI documentes et revus |
| E15 | Nouvelle coque UI: look professionnel minimal, themes clair/sombre, densite, panneaux deplacables et redimensionnables, onglets, navigation, palette | P1 | Codex | E14 | 4 j | - | - | TODO | Coque utilisable au clavier; dispositions persistantes; themes, densites, panneaux, onglets et palette testes |
| E16 | Parcours questionnaire progressif et conditionnel avec apercu dynamique, arbre et diagramme synchronises | P1 | Claude | E14 | 4 j | - | - | TODO | Parcours conditionnel complet; progression et apercu coherents; arbre et diagramme synchronises dans les deux sens |
| E17 | Editeur leger coloration/lignes/recherche/remplacement, panneau diagnostics et integration des flux securises existants | P1 | Codex + Claude (fichiers separes) | E15,E16 | 3 j | - | - | TODO | Edition, recherche/remplacement et diagnostics navigables testes sans regression du diff, de la validation ni de l'ecriture |
| E18 | Validation visuelle et fonctionnelle progressive, accessibilite, performances, resolutions, recette globale; migration finale apres validation | P1 | Codex + Claude | E15,E16,E17 | 3 j | - | - | TODO | Captures approuvees; Firefox, clavier, accessibilite, budgets performance et resolutions passent avant bascule |
| **Total** |  |  |  |  | **36,5 j** | **-** | **-** |  |  |

Les charges sont indicatives et doivent etre confirmees avant ouverture des taches. Une PR courte et independante par lot ou sous-lot, sans gros chantier monolithique.

## Contrat de la refonte UI - decisions UI-1 a UI-10

- UI-1 A+B: experience inspiree de VS Code, avec design d'application moderne.
- UI-2 A: panneaux gauche/centre/droite deplacables, redimensionnables et masquables, disposition persistante.
- UI-3 A+D: minimalisme professionnel, themes clair/sombre, couleurs et densite personnalisables.
- UI-4 D: barre laterale, onglets, palette de commandes et raccourcis.
- UI-5 A+C: questionnaire progressif et conditionnel, apercu reactif.
- UI-6 C: arborescence et diagramme d'architecture synchronises.
- UI-7 B: panneau central de diagnostics, filtres et navigation vers l'erreur.
- UI-8 A: editeur simple avec coloration, lignes et recherche/remplacement; conserver le diff/fusion existant.
- UI-9 C: design system partage, composants distincts, deux agents et petites PR.
- UI-10 C+D: validation progressive ET complete, screenshots, Firefox, accessibilite, performance, plusieurs resolutions; ancienne UI conservee avant acceptation de la nouvelle.
- **Pas de simple relooking**: reconstruction de zero de l'interface seulement; conserver le moteur et les garanties fonctionnelles.

## Autres decisions importantes (Q1-Q24)

- Q1 Linux uniquement; Q2 support de l'ecriture locale sur Linux, sans developpement Windows; Q3 tests GitHub Actions et manuels; Q4 scripts installer.sh et start.sh, verifier l'existant/PR avant doublon.
- Q5 tests MCP GitHub authentifies reportes dans pistes futures, statut NON VERIFIE conserve; Q6 catalogue MCP actuel, puis ajouts officiels, ensuite recherche libre controlee.
- Q7 conserver les scans et ajouter Docker + Semgrep; Q8 confirmation explicite NON VERIFIE.
- Q9 fusion a trois voies; Q10 docs TESTING.md et infrastructure E2E; Q11 assistant de commandes de protection de branche.
- Q12 plusieurs agents/PR courtes; Q13 inventorier et archiver docs/* avant suppression; Q14 supprimer codex/file-preview apres controle; Q15 nettoyage worktrees automatise mais prudent; Q16 audit complet des fichiers.
- Q17 verification API statique lorsque possible; Q18 cache/parallelisme/classement skills; Q19 grandes stacks et catalogues personnels; Q20 temps manuels.
- Q21 trois releases apres nettoyage / resolution partiels / ameliorations; Q22 agents en parallele; Q23 politique de releases+anomalies+dependances+tests; Q24 plan+instructions+execution progressive+CI.

## Gates de validation

1. Aucun auteur/committer/co-auteur agent IA dans les refs cible et aucun contenu de projet perdu.
2. Pour tout nettoyage, inventaire, sauvegarde, simulation et controle des worktrees; ne pas effacer un worktree actif.
3. Pour chaque fonctionnalite, tests unitaires+integration+securite et recette Firefox si UI.
4. Pour l'UI, valider captures d'ecran, ergonomie, navigation clavier, themes et resolutions, puis parcours complet avant bascule.
5. Aucun controle NON VERIFIE presente comme PASS.
6. Contrats entre Codex et Claude et integration CI verte avant fusion.

## Pistes futures hors perimetre immediat

- Tests d'authentification reelle du serveur MCP GitHub, avec compte de test et consentement.
- Expansion du catalogue MCP par etapes selon Q6.
- macOS/Windows non cibles.
