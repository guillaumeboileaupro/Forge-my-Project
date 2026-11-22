# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/). Politique : docs/MAINTENANCE.md. Tags : `vX.Y.Z` annotes sur main, jamais deplaces.

## [Unreleased]

### Securite
- Semgrep 1.184.0 avec regles locales versionnees pour Forge et les projets generes (aucune regle telechargee, aucune telemetrie), et passerelle qui refuse un resultat bloquant, un rapport invalide ou une analyse incomplete ou vide (E10).
- Analyse de l'image conteneur avec Trivy 0.76.2 (empreinte verifiee) des projets Docker des qu'un Dockerfile existe, bloquante en `high`/`critical` (`medium` en hardened), sans ignorer les vulnerabilites non corrigees ; NON VERIFIE sans Dockerfile (E10).

## [1.1.0] - 2026-11-19

Tag `v1.1.0` sur le commit de release de main. Jalon v1.1.0 de docs/RELEASES.md (E07, E08, E09), avec E06 en plus.

### Ajoute
- Controles NON VERIFIE detailles (raison, risque, criticite) et confirmation explicite verifiee par le serveur, perimee si la configuration ou les controles changent ; blocage des NON VERIFIE critiques en niveau hardened (E06, PR #31).
- Fusion automatique a trois voies de l'ecriture locale, proposee seulement avec une base fiable (contenu reellement ecrit par Forge, conserve hors du projet avec empreinte) et appliquee sur decision explicite ; conflits localises, resolution manuelle sinon, sauvegarde et rollback conserves (E07, PR #32).
- Socle de bout en bout des projets generes, sans dependance ajoutee ni scenario metier : temoin du paquet Python installe ou du livrable Node, job CI `Bout en bout (livrable)`, section E2E de TESTING.md avec les cas non applicables (E08, PR #35).
- Assistant de protection de branche GitHub : inspection en lecture seule du depot, de la branche, des checks CI et des permissions, puis commande `gh api` preparee et jamais executee. Seuls les controles reussis sont proposes, et le controle d'attribution est exige (E09, PR #36).
- Logo et favicon dans le README et l'interface web (PR #34).

### Modifie
- Un fichier existant remplace ou fusionne garde ses permissions, y compris apres un rollback ; un script genere reste executable (E07).
- Le niveau de securite hardened exige la verification en ligne : sans elle, l'archive et l'ecriture sont bloquees (E06).

Limites connues : protection de branche de main toujours a appliquer par le proprietaire (commande preparee par l'assistant E09) ; exception d'audit npm GHSA-fc5q-39xc-vjpf jusqu'au 2026-12-17 ; temoins E2E sans parcours metier ; seule la premiere page (100) de check-runs est lue par l'assistant E09 ; bases de fusion conservees localement, editions de l'apercu comprises ; recette Firefox executee en CI uniquement ; `tests/test_linux_scripts.py` instable sous forte charge ; Linux uniquement.

## [1.0.0] - 2026-11-19

Tag `v1.0.0` sur `9effa1d` (fusion de la PR #25) : jalon v1.0.0 de docs/RELEASES.md (E01 a E05), sans E06 ni les suivantes.

### Ajoute
- Scripts Linux `installer.sh` et `start.sh` : sans paquet, sans reseau ni privilege, reutilisant `start.py` (E04, PR #25).
- Garde d'attribution Git (`scripts/attribution_guard.py`) : hooks commit-msg et pre-push, job CI `attribution`, installation dans les depots existants et futurs, integration aux projets generes (E02, PR #26).
- Audit des refs Git et archive des branches `docs/*` (E01, PR #27).
- Audit des fichiers du depot (E03, PR #28).
- Politique de maintenance, plan des releases et controle CI du changelog et des statuts (E05, PR #29).

### Corrige
- CI de main rouge depuis l'avis GHSA-fc5q-39xc-vjpf sur les profils TypeScript generes (PR #30).

### Securite
- Exception datee et ciblee de l'audit npm des projets generes pour GHSA-fc5q-39xc-vjpf (picomatch <= 4.0.7, aucune version corrigee), expiration le 2026-12-17 ; tout autre avis reste bloquant (PR #30).
- Aucun agent IA ne peut apparaitre comme auteur, committer ou co-auteur sans etre refuse localement et en CI (E02).

Limites connues : protection de branche de main non configuree (le job CI d'attribution n'est pas obligatoire) ; exception d'audit npm jusqu'au 2026-12-17 ; Q14 partiel et Q15 (nettoyage automatise des worktrees) non construit ; anciens trailers d'attribution encore references par des refs GitHub `refs/pull/*` en lecture seule ; Linux uniquement.
