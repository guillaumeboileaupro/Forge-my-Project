# Specifications fonctionnelles - Forge-my-Project

Statut: VALIDE PAR L'UTILISATEUR, 14 novembre 2026. Reference pour le developpement.

## Mission et limites
Outil local, avec UI dans Firefox, utilise une seule fois pour initialiser l'environnement de developpement d'un projet. Il ecrit uniquement dans un dossier local choisi, apres confirmation. Ne genere pas le code metier, ne cree pas le depot GitHub et ne pousse pas les fichiers. Le developpement du projet cible est repris par l'utilisateur avec Codex ou Claude Code dans VS Code. Forge-my-Project peut, lui, etre ameliore en continu.

## Experience utilisateur
- Questionnaire hybride: navigation par sections, questions progressives et conditionnelles, retour arriere.
- Description libre du projet + champs structures; architecture definie manuellement ou suggeree a partir de regles locales et de modeles, toujours modifiable.
- Aucun LLM, service IA ni hebergement integre. Contenus prepares separement par Codex/Claude Code colles dans le formulaire.
- Interface moderne et legere, navigation laterale, recherche, progression, indicateurs d'erreur.
- Profils predefinis et personnalises; sauvegarde automatique locale et import/export JSON valide.
- Apercu arbre + contenu, edition des fichiers avant ecriture, comparaison et fusion assistee avec sauvegarde et validation explicite.
- Nouveau dossier ou dossier existant, destination choisie; aucune modification hors destination.
- Diagnostics lisibles, logs techniques locaux rediges sans secrets, rapport de generation.

## Sorties obligatoires
- AGENTS.md tres detaille: mission, architecture, conventions, commandes pertinentes, agents, responsabilites, skills, securite, erreurs frequentes, workflow Git et Definition of Done precise.
- Skills utiles au projet et adaptes aux agents.
- ARCHITECTURE.md, DEVELOPMENT_PLAN.md et TODO.md avec cartographie, taches, priorites, dependances, charges estimees, temps reels et ecarts.
- README.md, SECURITY.md, CONTRIBUTING.md, TESTING.md, DEPENDENCIES.md, ADRs et DEPLOYMENT.md si applicable.
- Hooks Git + hooks d'agents dans la mesure des capacites reelles de ces agents.
- GitHub Actions operationnelles, controles de qualite, tests unitaires, integration, E2E/recette quand applicables, non-regression, couverture et seuils.
- Securite stricte par defaut: secrets, SAST, SCA, supply chain, audit dependances et SBOM lorsque applicables. Echec bloquant sur problemes critiques connus. Aucune promesse de zero vulnerabilite.

## Sorties optionnelles
MCP uniquement si necessaires, avec recherche, verification, permissions minimales et validation de l'utilisateur. Deploiement uniquement si pertinent.

## Sources et templates
- Bibliotheque de modeles dans des fichiers externes versionnes avec Git, editable par Codex/Claude Code.
- Regles de base obligatoires + regles specifiques a la stack et aux agents.
- Catalogue extensible des technologies, versions stables preferees, versions choisies possibles, compatibilite verifiee.
- Selection automatique des skills du depot GitHub my-skills, en utilisant l'authentification Git/gh disponible dans VS Code si presente; ne pas supposer qu'une session VS Code autorise automatiquement le serveur local.
- Skills externes recherches sur GitHub et catalogues reconnus, provenance et contenu controles, validation utilisateur obligatoire.
- Jamais d'execution de scripts distants non approuves ou de packages inventes.

## Workflow genere
Plusieurs agents developpeurs et PR peuvent etre actifs en parallele sur des worktrees independants, avec petites taches et PR rapidement fusionnables, branche dediee, pas de commit direct sur main, tests et audits avant fusion, CI verte, mise a jour des temps et nettoyage apres fusion. Les permissions GitHub et les regles de branche doivent etre effectivement configurees pour imposer ces contraintes a distance.

## Verification et erreurs
- Bouton "Verifier la configuration" et controles critiques repetes juste avant ecriture.
- Versions, existence des packages et API, provenance, licence et vulnérabilites: preuves explicites; impossible a verifier = NON VERIFIE, jamais PASS.
- Erreur critique (compatibilite, securite, package inexistant) = blocage. Element optionnel absent = avertissement et confirmation.
- Aucune ecriture sans validation finale. Journal final: genere, ignore, non verifie, echec.

## Non-objectifs
- Pas de generation de code metier.
- Pas d'IA embarquee.
- Pas de publication/deploiement automatique.
- Pas de synchronisation ou maintenance des projets cibles apres initialisation.

## Evolutions validees le 15 novembre 2026

La reference detaillee est [ROADMAP_2026.md](ROADMAP_2026.md) : 24 decisions de finalisation et 10 decisions de refonte UI, soit 34 decisions approuvees.

- Linux uniquement; installer.sh et start.sh a verifier par rapport au lanceur existant, sans doublon.
- Securite: maintien des scans, scanner Docker, Semgrep, confirmation explicite des NON VERIFIE et controles bloques sur FAIL critiques.
- Fusion automatique a trois voies uniquement avec base fiable; E2E a completer dans les projets cibles; assistant des commandes de protection de branches sans execution implicite.
- API statiques Python/JS/TS verifiees lorsque possible; skills avec cache et recherche parallele; catalogues personnels extensibles Rust/Go/Java/Python/JS.
- Refonte complete de l'interface (pas du moteur) avec panneaux modulables, themes, onglets, palette de commandes, questionnaire progressif et apercu, diagramme et arborescence synchronises, diagnostics centralises et editeur leger.
- Validation progressive + finale: Firefox, accessibilite, performances, captures et plusieurs resolutions avant remplacement de l'ancienne UI.
- Releases ciblees v1.0.0 (nettoyage), v1.1.0 (trois PARTIEL), v2.0.0 (nouvelle UI et ameliorations).
- Agents IA utilises comme outils: **aucune attribution Git comme auteur, committer ou co-auteur**. Controler les commits et les branches.
- Piste VS Code uniquement long terme: voir `long-terme-ideas-project-liste.md`.
