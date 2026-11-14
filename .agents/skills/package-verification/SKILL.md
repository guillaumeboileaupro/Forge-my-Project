---
name: package-verification
description: Verifier noms de packages, versions, imports reels et avis de securite.
---

# Verification des packages
1. Ne jamais deduire un nom de package uniquement de son nom d'import.
2. Chercher sur PyPI/npm et documentation officielle, verifier versions et statut de maintenance.
3. Recouper l'API utilisee avec documentation de la version selectionnee.
4. Fixer les versions et generer un lockfile valide si une dependance externe est retenue.
5. Rechercher avis de securite et licences; privilegier la standard library.
6. Si acces externe impossible: marquer NON VERIFIE et ne pas livrer comme valide.
