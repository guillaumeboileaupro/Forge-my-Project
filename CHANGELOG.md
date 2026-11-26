# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/). Politique : docs/MAINTENANCE.md. Tags : `vX.Y.Z` annotes sur main, jamais deplaces.

## [Unreleased]

### Ajoute
- Parite du parcours v2 avec l'interface actuelle : brouillon automatique partage avec l'interface actuelle et revalide par le serveur, export/import JSON, reinitialisation, profils predefinis et personnels, architecture manuelle et suggestion locale, etape Skills externes (recherche, approbation, verification), controles en ligne explicites, archive ZIP et assistant de protection de branche ; memes endpoints et formats (E18b).
- Atelier du parcours v2 integre a la coque : panneaux Editeur et Diagnostics masquables et redimensionnables, onglets des fichiers ouverts (clavier, fermeture, marque de modification) et commandes de l'editeur dans la palette (E17).
- Coque du parcours v2 : rail, panneaux Etapes et Apercu masquables, deplacables et redimensionnables au clavier et a la souris, theme systeme/clair/sombre, densite compacte, onglets Plan/Resume, palette de commandes `Ctrl+K` et reinitialisation de la disposition ; preferences locales versionnees sans donnee projet (E15).
- Outil de nettoyage prudent des worktrees apres fusion `scripts/worktree_cleanup.py` : simulation par defaut, `--apply` pour executer ; refuse le worktree principal ou actif, verrouille, absent, avec operation en cours, fichier modifie, non suivi ou ignore, ou commits non integres ; `git worktree remove` et `git branch -d` uniquement, jamais de force ni de branche distante (Q15).
- Verification statique des API utilisees par les projets generes : imports Python et JavaScript/TypeScript, sous-chemins, exports nommes et par defaut, modules des bibliotheques Python ; PASS prouve, FAIL demontre (bloquant) ou NON VERIFIE, hors ligne et en ligne a partir des archives officielles verifiees par empreinte (E11).
- Recette progressive automatisee du parcours v2 dans Firefox : clavier seul, ordre et visibilite du focus, cibles, resolutions de reference (360 a 1920 px), contrastes rendus des deux themes, budgets de performance mesures, aucune erreur JavaScript ni ressource bloquee ; rapport docs/E18A_ACCEPTANCE.md (E18a).
- Parcours v2 : editeur leger (coloration, numeros de ligne, recherche/remplacement, retablissement), panneau diagnostics filtrable avec navigation vers le champ ou le fichier, et flux securises existants (validation, comparaison, conflits, confirmation NON VERIFIE, ecriture) ; aucun endpoint modifie (E17a).
- Preversion du parcours v2 sur `/v2/parcours` : questionnaire progressif et conditionnel issu du catalogue, apercu differe du plan, arborescence et diagramme technologies -> regles -> fichiers synchronises ; champ `graph` de `/api/plan`. L'interface actuelle est inchangee (E16).
- Piles Rust (Cargo, rustfmt, Clippy), Go (go test, go vet, gofmt) et Java (Maven, JUnit Jupiter, ecosysteme Maven verifie sur Maven Central), avec actions setup-go et setup-java epinglees et trois profils predefinis executes par la CI ; catalogue et regles personnels locaux, valides, bornes et jamais executes (E13).
- Recherche de skills : cache a expiration des candidats (1 h par defaut, option « Relancer sans le cache »), recherches paralleles a ordre deterministe, classement total (nom prioritaire sur la description) et reverification de la branche amont avant copie, signalee par avertissement (E12).

### Ajoute
- Design system de l'interface v2 : identité issue du logo officiel, tokens clair/sombre, composants accessibles, six maquettes statiques consultables et contrats UI/moteur pour E15 et E16 (E14, PR #39).
- Reprise E14 : cuivre exact du logo en remplissage (texte encre 4.76:1) et cuivres derives de meme teinte pour le texte et les indicateurs, page de composants de reference (rail, navigation, onglets ARIA, poignee, palette de commandes, tiroir, etats) et palette de commandes interactive dans les maquettes.

### Securite
- Semgrep 1.184.0 avec regles locales versionnees pour Forge et les projets generes (aucune regle telechargee, aucune telemetrie), et passerelle qui refuse un resultat bloquant, un rapport invalide ou une analyse incomplete ou vide (E10).
- Analyse de l'image conteneur avec Trivy 0.76.2 (empreinte verifiee) des projets Docker des qu'un Dockerfile existe, bloquante en `high`/`critical` (`medium` en hardened), sans ignorer les vulnerabilites non corrigees ; NON VERIFIE sans Dockerfile (E10).

### Corrige
- Nettoyage des worktrees : un worktree hors de la racine du depot n'est retire que si son chemin exact est autorise (`--allow-external`), et chaque candidat est reinspecte juste avant sa suppression (HEAD, branche, verrou, operation, fichiers y compris ignores) ; un fichier `.env` cree apres l'inspection n'est plus supprime (revue de la PR #47).
- Parcours v2 : un brouillon sans type de projet choisi n'est plus rejete au rechargement ; la verification en ligne peut etre relancee apres un echec ; la couche coloree de l'editeur garde la largeur du document entier, le texte reste sous le curseur apres un defilement horizontal (revues des PR #53 et #45).
- Parcours v2 : logo invisible (image bloquee par la CSP, desormais en SVG inline), contraste du sous-titre en theme sombre, barres de defilement claires en theme sombre, champ focalise masque par la barre d'actions collante a 360 px, cibles de 32 px relevees a 36/44 px, et editeur sous le budget de 100 ms sur un fichier de 2 000 lignes (rendu des seules lignes visibles, remplacement en une copie) (E18a).

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
