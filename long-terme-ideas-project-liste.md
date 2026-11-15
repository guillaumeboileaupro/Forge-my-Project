# Idees de projet a long terme - Forge-my-Project

Statut: **IDEE / BACKLOG LONG TERME**. Aucune implementation autorisee par ce document. Ne fait pas partie des taches actives E01-E18 ni des engagements v1.0.0, v1.1.0 ou v2.0.0.

## LT-01 - Extension Visual Studio Code

### Opportunite

Fournir Forge-my-Project dans VS Code pour initialiser directement un workspace, sans ouvrir le navigateur autonome, tout en conservant l'application Linux.

**Perimetre confirme de l'idee** : nouvelle interface d'acces, pas de nouveau moteur ni de code metier genere. Utilisation personnelle sur Linux dans un premier temps. Pas de publication Marketplace decidee.

### Proposition d'architecture (a valider avant toute implementation)

- Conserver le moteur Python, ses catalogues, regles, verification et securite comme **source de verite unique**.
- Definir une interface stable et versionnee du moteur (protocole local/CLI ou processus enfant) plutot que de dupliquer sa logique en TypeScript.
- Extension VS Code TypeScript: commandes, panneau lateral, configuration du workspace et ouverture des documents.
- Webview uniquement lorsque l'interface native VS Code ne suffit pas (questionnaire riche, visualisation d'architecture, comparaison).
- Installation/decouverte de Python 3.11+, gestion du processus, diagnostics explicites et arret propre.
- Reutiliser les validations avant ecriture: selection du workspace, diff, accord explicite, backups, rollback, controle des chemins et de la provenance.
- Aucune connexion externe implicite, aucun secret en clair, pas de generation de code metier.
- Hooks et CI: aucun agent IA credite comme auteur, committer ou co-auteur.

### TODO envisage - non actif

| ID | Travail | Depend de | Estime | Reel | Ecart | Validation |
| --- | --- | --- | ---: | ---: | ---: | --- |
| LT01-01 | Cadrage: UX dans VS Code, cas d'usage, limites, risques, specifications | Refonte UI stabilisee | 2 j | - | - | Cahier de tests et decisions valides |
| LT01-02 | Contrat stable du moteur Python (CLI/API locale versionnee), compatibilite et tests | LT01-01 | 3 j | - | - | Contrats et tests d'integration PASS |
| LT01-03 | Squelette extension TypeScript, activation, commandes, packaging VSIX | LT01-02 | 3 j | - | - | Extension installable en local |
| LT01-04 | Interface VS Code: vue laterale, questionnaire, etat, diagnostics, preferences | LT01-03 | 4 j | - | - | Parcours de configuration fonctionnel |
| LT01-05 | Integration workspace: apercu, diff, confirmation et ecriture securisee | LT01-04 | 4 j | - | - | Tests de conflits, backups et rollback PASS |
| LT01-06 | Skills/MCP/catalogues, verification et interactions Git/agents | LT01-04 | 3 j | - | - | Parite avec le moteur existant |
| LT01-07 | E2E extension, securite Webview, accessibilite, performances, tests Linux | LT01-05, LT01-06 | 3 j | - | - | Recette VS Code sans regression |
| LT01-08 | Documentation, installation, build VSIX, support et revue finale | LT01-07 | 2 j | - | - | Livraison locale testee |
| **TOTAL** | **Estimation initiale, pas une promesse de delai** | | **24 j** | **-** | **-** | |

Hypothese: **1 jour = 8 heures de developpement**, soit **192 heures-personne** estimees. Prevoir une reserve de risque de 20 a 30 % (environ 5 a 7 j), donc **29 a 31 jours-personne** pour le cadrage budgetaire. Ce ne sont pas des jours calendaires: Codex et Claude Code peuvent travailler en parallele sur des composants distincts, mais les integrations et validations restent sequentielles.

### Repartition proposee (non validee)

- **Codex** : extension TypeScript, commandes, navigation, Webview et experience utilisateur.
- **Claude Code** : contrats moteur Python, integration verification/skills/MCP, tests et securite.
- Deux worktrees independants; petites PR vite fusionnables; auteurs et co-auteurs Git exclusivement attribues au proprietaire; temps reels saisis manuellement.

### Conditions avant activation

1. Stabiliser l'interface Linux v2.0.0 et son contrat moteur.
2. Faire un prototype minimal dans VS Code et valider qu'un seul moteur peut servir les deux interfaces.
3. Valider le champ exact: extension privee ou publication Marketplace; plateforme Linux uniquement ou autres OS.
4. Confirmer les charges, les criteres de recette et la version cible.
5. Transferer ces lignes vers un TODO actif **uniquement sur decision explicite**.

### Plan de suivi du temps

Pour chaque sous-tache: date de debut et fin, charge estimee, **temps reel saisi manuellement**, ecart = reel - estime, lien PR, tests effectues, statut (TODO/IN PROGRESS/BLOCKED/DONE), limites. Ne jamais utiliser automatiquement la duree entre deux commits comme temps de developpement.
