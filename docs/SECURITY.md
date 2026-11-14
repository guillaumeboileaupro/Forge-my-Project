# Modele de securite du generateur

## Risques
- Entree non fiable dans le nom du projet, contenu JSON et descriptions.
- ZIP Slip / sortie d'archive hors racine; verifier chaque chemin genere.
- Injection de commandes lors de hooks et de templates.
- Supply chain: typosquatting, imports inexistants, malwares de packages, versions vulnerables.
- MCP: fuite de secrets, capacites excessives, outils non approuves.
- GitHub Actions: scripts non eprouves, permissions excessives et actions non epinglees.

## Regles bloquantes
- Aucune execution arbitraire depuis les valeurs du formulaire.
- Pas de reseau ou installation de packages sans accord et verification.
- Pas de token ou secret en dur ni de journalisation de secrets.
- Minima de permissions GitHub Actions, revue des actions epinglees aux SHA.
- Verifications CI: tests, syntaxe, analyse des secrets, SAST et SCA lorsque la stack ajoute des dependances.
- CI non executee ou audit impossible => etat NON VERIFIE, jamais PASS.

## Vulnerabilites
Bloquer severites critiques/hautes quand des outils d'audit fiables sont configures. Les outils ne garantissent jamais zero vulnerabilite. Suivre les exceptions motivees et datees; ne pas masquer les alertes.
