# Architecture cible - Forge-my-Project

## Etat actuel
Prototype en Python standard library: server.py expose un formulaire local index.html; generator.py valide une configuration limitee, produit une arborescence et l'export ZIP. Le prototype ne satisfait pas encore les specifications. Conserver son fonctionnement pendant la migration et ne pas annoncer les modules cibles comme implementes.

## Flux cible
```text
UI locale (Firefox) -> questionnaire conditionnel / profils
  -> schema versionne / validation
  -> planificateur de regles et compatibilites
  -> catalogues et templates externes versionnes
  -> selection skills / verification packages, versions et MCP optionnels
  -> rendu deterministe des documents, hooks, workflows
  -> audit des fichiers / apercu arbre + edition + diff
  -> validation explicite / sauvegarde + ecriture atomique dans dossier choisi
  -> rapport et logs expurges
```

## Arborescence cible (a creer progressivement)
```text
Forge-my-Project/
  AGENTS.md
  README.md
  TODO.md
  docs/
    SPECIFICATIONS.md
    ARCHITECTURE.md
    DEVELOPMENT_PLAN.md
    FINALIZATION_PLAN.md
    SECURITY.md
    TESTING.md
    DECISIONS/
  forge/
    config/
    rules/
    planner/
    generator/
    skills/
    verification/
    security/
    filesystem/
  ui/
    index.html
    css/
    js/
  templates/
    agents/
    documentation/
    architecture/
    skills/
    hooks/
    ci/
  catalogs/
    technologies/
    security/
    profiles/
  tests/
  .agents/skills/
  .github/workflows/
  .githooks/
```

## Contrats
- config: normalise et valide les informations de l'utilisateur; schema versionne.
- rules/planner: propose une architecture et une liste de fichiers; signale conflits et lacunes; aucune IA.
- templates/catalogs: donnees externes versionnees, validees avant utilisation, jamais executees comme commandes.
- skills: recuperation depuis my-skills par Git/gh, source authentifiee et verification; externes soumis a approbation.
- verification/security: controle des dependances, API, licences, vulnérabilites, CI et hooks; etat PASS/FAIL/NON VERIFIE.
- filesystem: simulation/diff, protection contre sorties de repertoire, sauvegarde et ecriture controlee, jamais de remplacement implicite.
- UI: ne detient pas la logique de confiance; toute requete est revalidee cote serveur.

## Frontieres de securite
Serveur borne a 127.0.0.1. Les champs, modeles, depots distants et fichiers existants sont non fiables. Refuser la traversee de chemins, l'injection de commandes, les scripts non approuves et la divulgation d'identifiants. Les acces reseau aux registres, skills et MCP sont explicites, journalises et soumis aux regles d'autorisation. Aucun acces distant aux dossiers utilisateur sans validation.

## Decisions
- Aucun LLM integre, ni hebergement.
- Aucune creation ni push du depot du projet cible.
- Python et UI web legere retenus pour le moteur.
- Evolution progressive des scripts existants avec tests de non-regression.
