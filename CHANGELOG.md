# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/). Politique : docs/MAINTENANCE.md. Aucune version publiee a ce jour.

## [Unreleased]

### Ajoute
- Garde d'attribution Git (`scripts/attribution_guard.py`) : hooks commit-msg et pre-push, job CI `attribution`, installation dans les depots existants et futurs, integration aux projets generes (E02, PR #26).
- Audit des refs Git et archive des branches `docs/*` (E01, PR #27).
- Audit des fichiers du depot (E03, PR #28).
- Politique de maintenance, plan des releases et controle CI du changelog et des statuts (E05).

### Securite
- Aucun agent IA ne peut apparaitre comme auteur, committer ou co-auteur sans etre refuse localement et en CI (E02).
