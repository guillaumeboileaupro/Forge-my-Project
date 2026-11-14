# Forge-my-Project

Generateur interactif de projets GitHub - version initiale.

## Demarrage

Python 3.11+ uniquement, sans dependances externes.

```bash
python3 server.py
```

Ouvrir http://127.0.0.1:8765, repondre au formulaire et telecharger l'archive ZIP du projet.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Portee de cette version

Genere un AGENTS.md, des skills, de la documentation d'architecture, des regles de securite et un squelette de CI en fonction du langage, de l'agent et du deploiement. Les packages et integrations MCP sont des recommandations a valider et ne sont pas installes automatiquement. Ne garantit pas qu'un projet genere est exempt de vulnerabilites.

## Regles

- Une seule PR ouverte pour le developpement dirige par agent.
- Ne jamais inventer de package ou d'API.
- Bloquer l'utilisation de secrets en clair.
- Ne pas fusionner sans tests, verification des dependances et revue de securite.
