---
name: mcp-selection
description: Choisir des serveurs MCP reels et minimiser leurs permissions selon les outils demandes.
---

# Choix des MCP
1. Lister les besoins concrets (GitHub, navigateur, fichiers, base, cloud).
2. Verifier existence, provenance, version, documentation et schema du serveur.
3. Ne pas generer de faux package ou de faux serveur.
4. Ne jamais ecrire de credential; fournir uniquement des noms de variables d'environnement.
5. Permissions lecture seule par defaut, approbation explicite pour toute mutation et tout deploiement.
