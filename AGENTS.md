# Forge-my-Project - instructions pour les agents

## Mission
Construire un generateur interactif, fiable et extensible qui produit des squelettes de projets avec architecture, regles agents, skills, hooks, securite, tests, CI/CD et documentation adaptes au questionnaire. Ne jamais presenter un squelette non operationnel comme securise ou deployable.

## Etat reel
- Serveur HTTP local: server.py; bind 127.0.0.1:8765.
- Formulaire web: ui/index.html, avec assets ui/css et ui/js.
- Validation / creation ZIP: facade generator.py; implementation historique dans forge/config/legacy.py et forge/generator/legacy.py.
- Tests: tests/test_generator.py.
- Aucun package tiers requis pour le generateur.
- Le moteur ne verifie pas encore les registres de packages en direct et ne configure pas des MCP operationnels.
- Le pipeline inclus dans les ZIP generes est un modele volontairement bloquant: ne pas le confondre avec la CI de ce depot.

## Architecture
Lire docs/ARCHITECTURE.md, docs/CONTRACTS.md et docs/DECISIONS/ avant de modifier les frontieres de modules.
Garder la validation de configuration independante de l'interface et des sorties.
Interdire les chemins arbitraires, les selections non autorisees et les operations reseau implicites.
Conserver la distinction entre generation de texte, verification et installation.

## Conventions
- Python 3.11+, stdlib par defaut; HTML/CSS/JS sans framework tant que cela suffit.
- Fonctions courtes, modules orientes responsabilite, entrees validees, erreurs explicites.
- Ne pas inventer de package, module, serveur MCP, action CI ni API. Verifier registre officiel, version, licence et documentation avant adoption.
- Un seul agent developpeur et une seule PR ouverte pour les changements proposes.
- Pas de modification de main sans demande explicite; ne jamais forcer un push.
- Eviter changements hors perimetre, commits de secrets et contournements des tests.
- Documentation en francais, commandes reproductibles.

## Commandes
```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q generator.py server.py tests
python3 server.py
git config core.hooksPath .githooks
```
Tester le formulaire sur http://127.0.0.1:8765 et les archives Python/JS avant de declarer un parcours valide.

## Pieges connus
- Le mode affiche TypeScript mais produit actuellement un squelette JavaScript; ne pas le qualifier de TypeScript valide.
- Les ZIP ne contiennent pas de lockfile, donc pas d'audit reproductible des dependances.
- Le hook pre-commit n'est actif qu'apres configuration du chemin Git.
- Le workflow genere est intentionnellement rouge et doit etre remplace par un pipeline valide.
- Security strict/hardened ne constitue pas une certification de securite.
- Des chemins ou descriptions fournis par l'utilisateur sont des donnees, jamais des commandes.

## Definition of Done
1. Le questionnaire et ses valeurs supportees sont documentes.
2. Tests positifs et negatifs, y compris archive ZIP et chemin de sortie; tests executes avec resultat trace.
3. Aucun package fictif ni API non documentee; tout ajout est verifie a la source officielle.
4. Pas de secrets, SAST/SCA/secrets et controle de provenance adaptes et operationnels ou limitations signalees.
5. Documentation et architecture mises a jour, comportement reproductible, retour utilisateur clair.
6. CI verte, revue de la PR et absence de severite haute/critique non resolue.
7. Le recapitulatif fournit tests effectifs, limites, fichiers modifies et risques residuels.
