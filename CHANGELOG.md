# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/). Politique : docs/MAINTENANCE.md. Aucune version publiee a ce jour.

## [Unreleased]

### Ajoute
- Garde d'attribution Git (`scripts/attribution_guard.py`) : hooks commit-msg et pre-push, job CI `attribution`, installation dans les depots existants et futurs, integration aux projets generes (E02, PR #26).
- Audit des refs Git et archive des branches `docs/*` (E01, PR #27).
- Audit des fichiers du depot (E03, PR #28).
- Politique de maintenance, plan des releases et controle CI du changelog et des statuts (E05).
- Controles NON VERIFIE detailles (raison, risque, criticite) et confirmation explicite verifiee par le serveur, perimee si la configuration ou les controles changent ; blocage des NON VERIFIE critiques en niveau hardened (E06).
- Fusion automatique a trois voies de l'ecriture locale, proposee seulement avec une base fiable (contenu reellement ecrit par Forge, conserve hors du projet avec empreinte) et appliquee sur decision explicite ; conflits localises, resolution manuelle sinon, sauvegarde et rollback conserves (E07).

### Modifie
- Un fichier existant remplace ou fusionne garde ses permissions, y compris apres un rollback ; un script genere reste executable (E07).

### Corrige
- CI de main rouge depuis l'avis GHSA-fc5q-39xc-vjpf sur les profils TypeScript generes (PR #30).

### Securite
- Exception datee et ciblee de l'audit npm des projets generes pour GHSA-fc5q-39xc-vjpf (picomatch <= 4.0.7, aucune version corrigee), expiration le 2026-12-17 ; tout autre avis reste bloquant (PR #30).
- Aucun agent IA ne peut apparaitre comme auteur, committer ou co-auteur sans etre refuse localement et en CI (E02).
