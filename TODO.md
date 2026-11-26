# TODO - Forge-my-Project

Reference: docs/SPECIFICATIONS.md et docs/DEVELOPMENT_PLAN.md.
Statuts: TODO, IN PROGRESS, BLOCKED, DONE. Les durees sont des estimations indicatives. Le temps reel et l'ecart restent a renseigner pendant le developpement.

## Cartographie
```text
T01 -> T02 -> T03 -> T04
        |      +-> T05
        +-> T06 -> T07 -> T08 -> T10 -> T14 -> T18
                        |      +-> T09 -> T10 -> T15 -> T18
                        |      +-> T11 -> T12 -> T13 -> T18
                        |      +-> T16 -> T17 -> T18
```
Le graphe est indicatif: la colonne Depend de fait foi.

## Taches
| ID | Phase | Travail | Depend de | Estime | Reel | Ecart | Statut | Critere de fin |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| T01 | P1 | Auditer le prototype et corriger ses defauts | - | 1 j | 0 h 05 | -7 h 55 (base 8 h/j) | DONE | Tests serveur/ZIP et JS reproductibles |
| T02 | P1 | Reorganiser modules et modeles externes sans casser l'existant | T01 | 1 j | 0 h 06 | -7 h 54 (base 8 h/j) | DONE | Contrats clairs, tests verts |
| T03 | P2 | Formulaire hybride, navigation et progression | T02 | 2 j | 0 h 03 | -15 h 57 (base 8 h/j) | DONE | Parcours UI valides |
| T04 | P2 | Questions conditionnelles et validation | T03 | 1 j | 0 h 02 | -7 h 58 (base 8 h/j) | DONE | Questions coherentes selon reponses |
| T05 | P2 | Profils, autosauvegarde et import/export JSON | T03 | 1 j | 0 h 09 | -7 h 51 (base 8 h/j) | DONE | Reprise et import fiable |
| T06 | P3 | Catalogue technologies et compatibilites | T02 | 2 j | 0 h 13 | -15 h 47 (base 8 h/j) | DONE | Configs incompatibles detectees |
| T07 | P3 | Moteur de regles et composition des templates | T06 | 2 j | 0 h 02 | -15 h 58 (base 8 h/j) | DONE | Rendu deterministe et coherent |
| T08 | P3 | AGENTS.md et documentation complete personnalisee | T07 | 2 j | 0 h 03 | -15 h 57 (base 8 h/j) | DONE | Aucun contenu fictif cache |
| T09 | P4 | Recuperer et selectionner les skills du depot my-skills | T07 | 1 j | 0 h 03 | -7 h 57 (base 8 h/j) | DONE | Skills pertinents copies sans execution |
| T10 | P4 | Recherche et validation de skills externes | T09 | 2 j | 0 h 14 | -15 h 46 (base 8 h/j) | DONE | Sources verifiees, accord utilisateur |
| T11 | P4 | Verifier packages, versions, compatibilites, API | T06 | 2 j | 0 h 03 | -15 h 57 (base 8 h/j) | DONE | Packages inconnus rejetes |
| T12 | P5 | GitHub Actions generees et verifiees | T07,T11 | 2 j | 0 h 16 | -15 h 44 (base 8 h/j) | DONE | Pipelines reels pour stacks supportees |
| T13 | P5 | Controles securite stricts et rapports | T11,T12 | 2 j | 0 h 12 | -15 h 48 (base 8 h/j) | DONE | Scans applicables et blocage fiable |
| T14 | P5 | Hooks Git et agents suivant leurs capacites | T07 | 1 j | 0 h 11 | -7 h 49 (base 8 h/j) | DONE | Hooks activables et executes |
| T15 | P5 | MCP optionnels verifies et valides | T10 | 1 j | 0 h 12 | -7 h 48 (base 8 h/j) | DONE | Aucun MCP fictif ni secret |
| T16 | P6 | Explorateur, apercu et edition des fichiers | T08 | 2 j | 0 h 15 | -15 h 45 (base 8 h/j) | DONE | Modifications visibles avant ecriture |
| T17 | P6 | Diff, fusion assistee, sauvegarde, ecriture locale | T16 | 2 j | 0 h 12 | -15 h 48 (base 8 h/j) | DONE | Conflits et rollback testes |
| T18 | P7 | Tests finaux, corrections, docs et rapport | T01-T17 | 3 j | 1 h 36 | -22 h 24 (base 8 h/j) | DONE | Critères de finalisation valides |
| **Total** | | | | **30 j** | **3 h 57** | **-236 h 03** (base 8 h/j) | | 18 taches DONE |

Lecture des donnees historiques T01-T18 (conservees telles quelles) : la colonne Reel contient le temps d'execution de l'agent IA, pas du temps de developpement humain ; l'Ecart compare donc des minutes d'agent a une charge humaine en jours et ne mesure pas une productivite humaine. Le cycle E01-E18 separe ces grandeurs (voir plus bas).

## Ordre de travail
T01-T18 sont terminees. Pour E01-E18, plusieurs petites PR sont autorisees en parallele avec worktrees independants, revue et CI verte. Actualiser les colonnes Reel/Ecart apres chaque tache et noter les preuves CI dans la PR.

## Etat existant
Le serveur local, le formulaire initial, le ZIP, AGENTS.md, une bibliotheque initiale de skills, des docs et une CI du depot existent. Les fonctions cible non implementees ne doivent pas etre marquees DONE.

## Notes de suivi
Pour chaque tache terminee: commande et resultat des tests, lien du run CI, impact securite, fichiers modifies, temps reel, blocages et risque residuel. Aucune tache DONE sans preuve.

### T01 - 14 novembre 2026
- Temps reel mesure: 0 h 05, de la creation de la branche dediee a la premiere CI de PR verte.
- Tests: `python3 -m unittest discover -s tests -v` PASS, 20 tests; `python3 -m compileall -q generator.py server.py tests` PASS.
- Archives: 64 combinaisons supportees controlees, chemins ZIP bornes a la racine, tests generes Python et `npm test` executes avec succes.
- Serveur et formulaire: integration HTTP loopback PASS; rendu Firefox headless PASS; contrat des champs et options PASS.
- Securite: validation stricte des champs, de `Host` et du type JSON; en-tetes navigateur durcis; recherche ciblee de secrets sans correspondance.
- CI: [push PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43583433146) et [PR PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43583453284).
- NON VERIFIE: Bandit, Semgrep et Gitleaks absents. `pip check` signale des incoherences de l'environnement Anaconda global, sans dependance tierce du projet.
- Risques restants hors T01: profil nomme TypeScript mais base JavaScript, workflow genere volontairement bloquant, absence de lockfiles et fonctions T02-T18 non implementees.

### T02 - 14 novembre 2026 (Codex, PR #5)
- Temps reel mesure: 0 h 06, de la creation de la branche dediee a la premiere CI push verte.
- Tests locaux: 24 tests PASS; compilation Python PASS; 64 configurations avec sorties `build()` octet pour octet identiques a T01; projets generes Python et JavaScript executes avec succes.
- Recette: serveur HTTP local PASS; formulaire et assets externes rendus dans Firefox headless PASS; regression du checkbox sous CSP detectee puis corrigee avant livraison.
- Securite: templates rendus en un passage, traversee `..` refusee, assets servis par liste fermee et CSP sans `unsafe-inline`.
- CI et integration: [push PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43584707105), [PR PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43584848078), fusion `6506dd0` dans `main`.

### T06-T11 - 14 novembre 2026 (Claude Code, PR #6)
- Temps reels mesures sur l'historique Git: branche creee a 10 h 54; commits T06 11 h 07, T07 11 h 09, T08 11 h 12, T11 11 h 15, T09 11 h 18, T10 11 h 21; fusion 11 h 28 (total 0 h 34).
- Tests: `python3 -m unittest discover -s tests` PASS, 90 tests apres synchronisation avec T02; pyflakes sans alerte.
- CI: [push PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43585339901) et [PR PASS](https://github.com/guillaumeboileaupro/Forge-my-Project/actions/runs/43585342252) (Python 3.11).
- Verifications reelles: package fictif rejete; django 3.0.0 et lodash 4.17.15 bloques (GHSA haute/critique); Node 20 et Python 3.9 bloques (fin de vie); 6 skills my-skills copies au commit 16cddc53, scripts ignores.
- T10 reste IN PROGRESS: recherche et approbation disponibles dans le moteur et la CLI, pas encore dans l'interface.
- NON VERIFIE: API des packages (pas d'installation); licence PyPI = derniere version publiee.

### Integration moteur/formulaire - 14 novembre 2026 (Claude Code, PR #8)
- Formulaire hybride sur `/`, API locale `/api/catalog|plan|archive`, formulaire historique sur `/legacy`; recette Firefox headless en CI.
- Temps reel: 11 h 28 (fusion PR #6) -> 11 h 35 (CI verte), fusion par l'utilisateur a 11 h 43.
- T03/T04 restent IN PROGRESS: la liste des 40 choix valides n'est pas dans le depot, couverture complete non verifiable.

### T05 - 14 novembre 2026 (Claude Code)
- Temps reel: 11 h 44 -> 11 h 53 (0 h 09) jusqu'a la PR; CI et fusion notees dans la PR.
- Profils predefinis (6, chacun genere un plan valide), profils personnels CRUD dans un fichier local 0600 a ecriture atomique, sauvegarde automatique (`localStorage`, ecriture immediate a la fermeture) revalidee avant restauration, import/export JSON valide par le serveur.
- Tests: unitaires et HTTP (`tests/test_profiles.py`), recette Firefox (`FORGE_E2E=1`): restauration des choix conditionnels, brouillon incompatible ignore, cycle de vie des profils, export puis import, JSON invalide et configuration incompatible refuses. Recette executee 3 fois de suite sans echec.
- Defaut corrige pendant la recette: une modification suivie d'un rechargement en moins de 300 ms etait perdue; sauvegarde forcee sur `pagehide`.
- Limites: les approbations de skills externes importees ne sont pas conservees par l'interface (avertissement affiche); le brouillon est propre au navigateur.

### T12 - 14 novembre 2026 (Claude Code)
- Temps reel: 11 h 57 -> 12 h 13 (0 h 16) jusqu'a la PR; CI et fusion notees dans la PR.
- CI generee par le moteur: actions officielles epinglees par SHA (checkout v7.0.1, setup-python v7.1.0, setup-node v7.1.0, verifiees via l'API GitHub), permissions en lecture, une etape par commande du catalogue, seuil de couverture 80 %; manifestes et configurations d'outils minimaux sans code metier.
- Preuve: `tests/smoke_generated.py --verify` execute la CI generee des 6 profils predefinis: PASS localement (Python 3.12, Node 24) et dans le job `generated-projects`.
- Defaut reel detecte et corrige: typescript-eslint 8.72.2 n'accepte pas TypeScript 7 (ERESOLVE). Ajout de la resolution des peerDependencies npm (T11): TypeScript ajuste a 6.0.3 avec trace.
- NON VERIFIE: pas de lockfile genere; Django sans squelette manage.py; seuils de couverture appliques a un code vide (100 %) jusqu'aux premiers modules.

### T13 - 14 novembre 2026 (Claude Code)
- Temps reel: 12 h 19 -> 12 h 31 (0 h 12) jusqu'a la PR; CI et fusion notees dans la PR.
- Outils verifies sur leurs sources officielles le 14 novembre 2026: Gitleaks 8.30.1 (empreinte SHA-256 identique dans le fichier de sommes publie et le digest GitHub), Bandit 1.9.4, pip-audit 2.10.1, cyclonedx-bom 8.0.1 (PyPI), eslint-plugin-security 4.2.1 (npm), actions/upload-artifact v7.0.2 (SHA via l'API GitHub).
- Preuves: `tests/smoke_security.py` (secret, injection shell, urllib3 1.24.1, lodash 4.17.15, eval) -> chaque controle echoue comme attendu, temoins PASS; `tests/smoke_generated.py --verify` -> 6/6 profils PASS sur les jobs quality et security.
- Ce depot: Gitleaks (historique) et Bandit sans alerte; jobs CI `security` et preuve de detection ajoutes.
- Limites: pip-audit ne filtre pas par severite (toute vulnerabilite connue bloque); pas de scanner d'image conteneur (NON VERIFIE); Semgrep non retenu (regles telechargees a l'execution), SAST JS limite a eslint-plugin-security.

### T13 - suivi
- PR #11 fusionnee le 14 novembre 2026 a 12 h 40 apres CI verte (6 jobs, dont generated-projects : 6/6 profils et 5/5 problemes injectes detectes sur les runners GitHub).

### T14 - 14 novembre 2026 (Claude Code)
- Temps reel: 12 h 40 -> 12 h 51 (0 h 11) jusqu'a la PR; CI et fusion notees dans la PR.
- Capacites des agents verifiees dans leur documentation officielle: Claude Code (hooks PreToolUse, code 2 bloquant), Codex (learn.chatgpt.com/docs/hooks et source openai/codex: `.codex/hooks.json`, PreToolUse sur Bash/apply_patch, code 2 + stderr, revue `/hooks` requise), GitHub Copilot (docs.github.com hooks-configuration: `.github/hooks/*.json`, version 1, preToolUse, code 2 = refus, fail-closed).
- Tests: `tests/test_engine_hooks.py` (garde-fou sur les 3 formats d'evenements, configurations, droits 0755, commits reels: message non conforme, `.env` force, motif de secret, outil absent, pre-push tests OK/KO, branche gitleaks); `tests/smoke_generated.py`: hooks pre-commit et pre-push generes executes avec les outils reels, 6/6 profils PASS.
- Defaut detecte et corrige: le garde-fou genere ne respectait pas `ruff format`/`ruff check` du projet cible.
- Limites: le garde-fou exige Python 3 (y compris pour les projets Node); detection par motifs (pas d'analyse complete du shell); les hooks Codex doivent etre approuves via `/hooks`; activation des hooks Git manuelle (`core.hooksPath`), aucun hook n'est installe automatiquement.

### T10 - 15 novembre 2026 (Claude Code)
- Temps reel: 0 h 03 (moteur et CLI, PR #6) + 11 h 23 -> 11 h 34 (0 h 11) pour l'integration au formulaire et l'integrite des approbations, jusqu'a la PR; CI et fusion notees dans la PR.
- Formulaire: section « Skills externes » (recherche explicite, fiche nom/description/provenance/commit/empreinte/fichiers copies et ignores, Approuver/Refuser, confirmation pour une source non reconnue, verification en ligne PASS/FAIL/NON VERIFIE). API `POST /api/skills/search` et `POST /api/skills/verify`.
- Integrite: approbation = depot + commit + empreinte SHA-256 de l'arborescence complete du skill; skill modifie depuis l'approbation ou contenu telecharge different du blob = erreur bloquante `skill-modified`. Approbations sans empreinte refusees a l'import avec un message explicite; un meme nom de skill ne peut etre approuve qu'une fois.
- Conservation: approbations dans le brouillon, les profils et l'export/import JSON, revalidees par le serveur.
- Tests: `tests/test_engine_external_skills.py` (empreinte, contenu modifie/ajoute/script modifie, telechargement falsifie, verification), `tests/test_skills_api.py` (5 tests HTTP: recherche, refus, verification, export/import/profil, generation bloquee), recette Firefox `test_external_skills_approval` (recherche, approbation, refus, rechargement, verification PASS puis FAIL, generation bloquee puis debloquee). 181 tests unitaires OK (7 ignores sans FORGE_E2E), recette Firefox 6/6.
- Verification reelle (GitHub, `gh` et HTTPS anonyme): 8 candidats pour un projet web React; copie de `webapp-testing` avec controle des blobs OK, scripts `examples/*.py` ignores; empreinte falsifiee = FAIL.
- Defaut corrige: la barre laterale fixe depassait la hauteur de fenetre (bouton Reinitialiser inaccessible); elle defile desormais.
- Limites: refus conserves uniquement pendant la session; l'empreinte repose sur les SHA-1 de blobs Git fournis par GitHub; la recherche de code GitHub exige la CLI gh authentifiee; la decision de confiance reste humaine.

### T15 - 15 novembre 2026 (Claude Code)
- Temps reel: 11 h 35 -> 11 h 47 (0 h 12), recherche documentaire pendant la CI de T10 puis branche dediee apres fusion de T10; CI et fusion notees dans la PR.
- Catalogue `catalogs/mcp/servers.json` verifie a la source: registre MCP officiel (`io.github.github/github-mcp-server` 2.1.0, `io.github.microsoft/playwright-mcp` 0.0.85, statut actif), depots GitHub actifs, licences MIT et Apache-2.0, npm `@playwright/mcp` 0.0.85.
- Formats d'agents verifies dans la documentation officielle: `.mcp.json` (Claude Code; destination native de Copilot dans VS Code, `${VAR}` dans les en-tetes), `.codex/config.toml` (`bearer_token_env_var`, `http_headers`, projets approuves uniquement).
- Section « Skills et MCP » du formulaire: serveurs pertinents seulement, aucun coche par defaut, provenance, permissions et variable du jeton affichees; selection retiree si le type de projet la rend non pertinente.
- Tests: `tests/test_engine_mcp.py` (11: catalogue strict, aucune sortie sans selection, fichiers par agent, JSON/TOML relus, absence de secret, pertinence, registre PASS/FAIL/NON VERIFIE, provenance fausse bloquante), API `test_mcp_servers_are_opt_in_and_revalidated`, recette Firefox `test_mcp_selection`. 194 tests unitaires OK (8 ignores: 7 parcours Firefox sans FORGE_E2E, branche gitleaks sans outil), recette Firefox 7/7.
- Verification reelle: registre MCP, npm et OSV PASS pour les deux serveurs; Gitleaks 8.30.1 (empreinte verifiee) sur un projet genere avec MCP: aucune fuite; Bandit: aucune alerte.
- Limites: deux serveurs au catalogue; l'agent cloud Copilot se configure dans les parametres du depot; le serveur GitHub distant exige un jeton fourni par l'utilisateur; Playwright MCP n'est pas une frontiere de securite (documentation officielle); la phrase Codex sur le chargement reserve aux projets approuves provient de la page MCP (« trusted projects only »).

### T16 - 15 novembre 2026 (Codex)
- Temps reel mesure: 0 h 06, de la creation du worktree a la premiere recette Firefox complete verte.
- Interface: explorateur hierarchique, navigation precedent/suivant, apercu editable, marqueur par fichier, compteur global et restauration du contenu genere.
- Validation: `POST /api/files/validate` regenere le plan et exige l'ensemble exact des chemins; l'archive repete ce controle et contient les editions validees.
- Securite: ajout/suppression/traversee de chemin, texte non UTF-8 ou avec NUL, fichier > 256 Kio et ensemble > 2 Mio refuses; aucune ecriture locale dans T16.
- Tests locaux: 187 PASS, 7 ignores dans la suite standard; compilation Python et `node --check` PASS; recette Firefox headless 6/6 PASS.
- T17 reste a faire: destination, diff, fusion, sauvegarde, confirmation, ecriture et rollback.

### T16 - reprise et integration - 15 novembre 2026 (Claude Code, PR #15)
- Codex indisponible: reprise de la branche `codex/file-preview` depuis un worktree independant (worktree personnel de Codex non modifie), fusion de `origin/main` (T10, T15) sans reecriture d'historique ni push force.
- Temps reel de la reprise: 13 h 06 -> 13 h 15 (0 h 09), en plus des 0 h 06 de Codex; total T16 0 h 15.
- Conflits resolus en conservant les deux apports: `forge/web.py` (validation de l'apercu + `_mcp_payload`), `ui/js/app.js` (invalidation de l'apercu + `updateMcp`), `docs/CONTRACTS.md`, `AGENTS.md`, `README.md`, `TODO.md`.
- Correction d'interaction: approuver ou retirer un skill invalide desormais l'apercu valide (`approvalsChanged` appelait seulement `disabled`, la validation restait acquise); recette MCP adaptee au parcours valider-puis-telecharger.
- Tests ajoutes: API `tests/test_skills_api.py` (skill approuve et MCP edites presents dans le ZIP, scripts jamais copies; editions refusees si MCP, approbations ou agents changent; skill modifie bloquant meme avec editions; injection de `.mcp.json`, `.codex/config.toml` ou d'un skill non approuve refusee), `test_preview_routes_never_write_to_disk` (apercu, validation et archive sans aucune ouverture en ecriture), Firefox `test_editor_and_skill_approval_interact` et extension de `test_mcp_selection` (archive capturee dans la page, sans ecriture du telechargement par Firefox, contenant l'edition).
- Resultats locaux: 205 tests OK (9 ignores: 8 parcours Firefox sans FORGE_E2E, branche gitleaks sans outil); recette Firefox headless 8/8; compilation Python et `node --check` PASS; CI generee des six profils predefinis PASS 6/6 en local avec `--verify` (python-api-fastapi, python-cli, python-library, python-web-django, typescript-api-express, typescript-web-react; Gitleaks inclus).
- Securite: Bandit 1.9.4 aucune alerte au seuil CI (3 LOW preexistantes, identiques a `main`); Gitleaks 8.30.1 sur l'historique de la branche et sur forge/ui/tests: aucune fuite; seules ecritures du code applicatif: magasin de profils (`forge/config/profiles.py`), aucune dans un projet cible.
- CI: premier run push en echec sur `test_engine_hooks` (T14, course `maintenance.lock` entre la maintenance Git detachee et la suppression du depot temporaire, sans lien avec T16); correction: `gc.auto=0` et `maintenance.auto=false` dans le depot de test.
- Limites: le contenu edite n'est pas rescanne pour les secrets avant l'archive (la CI generee lance Gitleaks); une edition de `.mcp.json` ou d'un skill n'est pas revalidee semantiquement (seuls chemins, encodage et tailles); les editions sont perdues si la configuration change.

### T17 - 15 novembre 2026 (Claude Code, a la place de Codex indisponible)
- Temps reel: 13 h 33 -> 13 h 45 (0 h 12), de la synchronisation de `main` a la recette Firefox complete verte; CI et fusion notees dans la PR.
- Destination: saisie ou parcours des sous-dossiers de la racine autorisee (`FORGE_WRITE_ROOT`, sinon dossier personnel), dossier nouveau ou existant, droits verifies; chemins relatifs, `..`, racine, dossier de Forge-my-Project et liens symboliques refuses (parcours par descripteurs O_NOFOLLOW).
- Comparaison: nouveau, identique, conflit (diff unifie), bloque (lien, fichier special); decision obligatoire pour chaque conflit (conserver, remplacer, fusion manuelle); aucune ecriture pendant la comparaison.
- Ecriture: confirmation explicite, jeton HMAC de validation (etat des cibles, contenus, destination), reverification de chaque cible, sauvegarde `.forge-backup/<horodatage>/` avec MANIFEST.json, ecriture atomique (temporaire, fsync, rename), rollback automatique, rapport final (operations, sauvegarde, avertissements).
- Limites T16 corrigees: contenu edite et fusionne controle a la validation, a l'archive et a l'ecriture (secrets, `.mcp.json`/`.codex/config.toml`/hooks d'agents figes hors mise en forme, scripts de hooks non modifiables, nom de skill conserve, chemins sensibles interdits); validation perimee bloquee cote interface et serveur.
- Tests: `tests/test_filesystem_write.py` (21: destinations dangereuses, liens symboliques sur le chemin, la cible et un sous-dossier, FIFO, dossier nouveau/existant, identique/different, conserver/remplacer/fusionner, refus d'ecrasement sans decision, confirmation, modification concurrente avant et pendant l'ecriture, echec d'ecriture avec restauration et suppression des dossiers crees, secrets, MCP/hooks/skills, chemins sensibles), API (parcours compare/confirm/409/sauvegarde, secret bloque sur validate/archive/compare), skills et MCP approuves ecrits a l'identique et skill modifie bloquant, recette Firefox `test_local_write_journey`.
- Resultats locaux: 230 tests OK (10 ignores: 9 parcours Firefox sans FORGE_E2E, branche gitleaks sans outil); recette Firefox headless 9/9; compilation Python et `node --check` PASS; Bandit 1.9.4 aucune alerte au seuil CI; Gitleaks 8.30.1 aucune fuite.
- Documentation: docs/LOCAL_WRITE.md (parcours, garanties, sauvegarde, restauration manuelle), CONTRACTS, SECURITY, ARCHITECTURE, README, AGENTS.
- Limites: Linux et macOS uniquement (ZIP ailleurs); fusion manuelle sans fusion a trois voies; fichier existant binaire ou > 256 Kio: conserver ou remplacer; configurations MCP/hooks existantes non fusionnables; detection de secrets par motifs (Gitleaks reste la reference); `.forge-backup/` a exclure du depot par l'utilisateur; jeton invalide apres redemarrage du serveur.

### T03/T04 - cloture - 15 novembre 2026 (Claude Code)
- Temps reel: 14 h 20 -> 14 h 25 (5 min pour la cloture commune, repartis T03 3 min / T04 2 min); le travail anterieur sur le formulaire (T01-T02, T05, T10, T15-T17) n'avait pas ete chronometre au titre de T03/T04 et n'est pas compte.
- Matrice exigences -> implementation -> tests: docs/TRACEABILITY.md (45 exigences de SPECIFICATIONS.md; noms de tests verifies automatiquement).
- Les « 40 choix confirmes » ne sont dans aucun fichier, commit, branche ni PR du depot (seule leur synthese SPECIFICATIONS.md existe): non retracables individuellement, non reconstitues.
- Ecarts corriges: recherche des technologies (U5), suggestion d'architecture reprise et modifiable dans le formulaire (U3), confirmation explicite des avertissements avant validation (V4), journal final complet genere/ignore/non verifie/echec (V5), commande de protection de branche verifiee dans l'API REST GitHub et alignee sur les jobs CI (W2), preuve que le journal du serveur n'expose jamais le corps des requetes (U11).
- Dependances, incompatibilites et cascades: retrait en cascade des prerequis (Firefox), conflits uni/bidirectionnels et prerequis manquants (test_engine_catalog), brouillon/profil incompatible refuse (test_profiles, Firefox), MCP non pertinent retire au changement de type (Firefox test_mcp_selection), editions perimees apres changement de selection (test_skills_api).
- Tests: 234 tests unitaires OK (11 ignores: 10 parcours Firefox sans FORGE_E2E, branche gitleaks sans outil); recette Firefox 10/10 dont `test_questionnaire_search_suggestion_and_warning_confirmation`.
- Restent PARTIEL (voir matrice): U9 fusion manuelle sans trois voies, S7 pas de harnais E2E genere, W2 protection de branche a executer par le proprietaire du depot.

### T18 - 15 novembre 2026 (Claude Code)
- Temps reel: 14 h 25 -> 16 h 01 (1 h 36), de la fin de T03/T04 a la recette sur clone propre verte et au rapport; CI et fusion notees dans la PR.
- Recette sur installation propre (clone neuf, HOME vierge, reseau reel): 26/26 PASS (`tests/acceptance_t18.py`), dont skills GitHub reels, verification en ligne, ecriture avec fusion, sauvegarde et restauration manuelle, CI du projet ecrit et 10 refus.
- Tests: 236 unitaires OK (12 ignores sans FORGE_E2E ou gitleaks); Firefox 11/11; six profils `smoke_generated.py --verify` 6/6; `smoke_security.py` detections bloquantes; Gitleaks historique complet sans fuite; Bandit 0 medium/high; MCP Playwright genere demarre (25 outils).
- Anomalies corrigees: requete longue interrompue par Firefox headless (relance unique des lectures, jamais des ecritures); refus opaque quand une source en ligne change entre verification et validation; documentation perimee (README, AGENTS, LOCAL_WRITE).
- NON VERIFIE: macOS et Windows (aucun environnement), execution du MCP GitHub distant (gh 2.4.0 sans `auth token`).
- Rapport: docs/ACCEPTANCE.md; gates G01-G12 cochees dans docs/FINALIZATION_PLAN.md.


## Matrice des 34 reponses validees - suivi question par question

**Source de verite:** questionnaire utilisateur de 24 questions + 10 questions UI. La colonne "Etat" indique le statut de mise en oeuvre de la **nouvelle decision**, pas le statut des anciennes taches T01-T18. "Hors perimetre" signifie aucune nouvelle implementation demandee. Chaque ligne pointe vers une tache E ou un suivi documentaire; aucune reponse n'est perdue.

### 24 decisions de finalisation

| Question | Reponse validee | Decision et critere verifiable | Taches / jalon | Etat |
| --- | --- | --- | --- | --- |
| Q01 | A | Linux uniquement, sans promesse Windows/macOS | E04, v1.0.0 | DONE (README: scripts Linux, macOS/Windows non pris en charge; v1.0.0 publiee le 19/11) |
| Q02 | B, recadree Linux | Ecriture directe dans les dossiers Linux; ne pas developper Windows | E04, E07 | DONE (E07, PR #32: ecriture locale Linux; ecriture refusee sous Windows, ZIP conserve) |
| Q03 | A + B | GitHub Actions et tests manuels Linux | E05, E18 | PARTIEL (E05: controles reguliers definis dans docs/MAINTENANCE.md; recette manuelle E18 a faire) |
| Q04 | B | `installer.sh` et `start.sh`; examiner la PR existante de `start.py` avant doublon | E04 | DONE (E04, PR #25: installer.sh et start.sh, start.py conserve) |
| Q05 | Reportee | MCP GitHub authentifie NON VERIFIE; conserver dans les pistes futures sans PR maintenant | Backlog long terme | REPORTE |
| Q06 | A puis B puis C | Maintenir GitHub/Playwright, puis MCP officiels, enfin recherche libre verifiee | Backlog MCP progressif | FUTUR |
| Q07 | Tout (A+B+C+D) | Maintenir les scans existants, ajouter analyse Docker et Semgrep, bloquer sev. haute/critique | E10 | DONE (E10, PR #38 fusionnee) |
| Q08 | B | Expliquer et faire confirmer explicitement chaque NON VERIFIE, trace et revalidation | E06 | DONE (E06, PR #31) |
| Q09 | B | Fusion trois voies seulement avec base fiable; garder diff, fusion manuelle et rollback | E07, v1.1.0 | DONE (E07, PR #32 fusionnee) |
| Q10 | A + B | TESTING.md et infrastructure E2E cible prete a completer sans tests metier inventes | E08, v1.1.0 | DONE (E08, PR #35 fusionnee) |
| Q11 | B | Assistant qui prepare les commandes de protection GitHub, sans les executer | E09, v1.1.0 | DONE (E09, PR #36) |
| Q12 | B avec PR courtes | Agents et PR en parallele; taches petites, CI verte et fusion rapide | E05, AGENTS.md | REGLE (AGENTS.md: petites PR en parallele sur composants distincts) |
| Q13 | C (correction de A) | Archiver inventaire noms/SHA des branches docs/* avant suppression sur preuve de fusion | E01 | DONE |
| Q14 | A | Supprimer codex/file-preview apres verification d'integration et absence de travail local | E01 | DONE (25/11: branche locale et worktree retires apres verification d'integration; seul main subsiste) |
| Q15 | C | Nettoyage automatise worktrees apres fusion, mode simulation, refus si sale ou actif | E01 | DONE (`scripts/worktree_cleanup.py`, simulation par defaut, refus si sale, actif, verrouille ou non integre) |
| Q16 | B | Audit fichiers obsoletes, temporaires, doublons, configurations; suppression seulement sur preuve | E03 | DONE (PR #28 fusionnee; aucun fichier suivi inutile demontre) |
| Q17 | B | Verifier statiquement APIs Python, JS/TS quand possible, afficher PASS/FAIL/NON VERIFIE | E11 | DONE (E11, PR #40) |
| Q18 | C | Skills: cache expire, recherches paralleles, classement et reverification avant copie | E12 | DONE (E12, PR #41) |
| Q19 | B + C, usage personnel | Stacks Python/JS/Rust/Go/Java et catalogue/regles personnels editables localement | E13 | DONE (E13, PR #42) |
| Q20 | A | Temps manuels uniquement; conserver estime/reel/ecart sans chronometre ni mesure Git | Toutes E, pas de fonctionnalite nouvelle | REGLE |
| Q21 | B puis C puis D | Trois releases: v1.0.0 nettoyage; v1.1.0 PARTIEL; v2.0.0 ameliorations+refonte | E05, E07-E09, E18 | PARTIEL (v1.0.0 et v1.1.0 publiees le 19/11 ; v2.0.0 a venir) |
| Q22 | C | Codex et Claude en parallele, composants et worktrees distincts | E05, E14-E18 | REGLE |
| Q23 | B + C | Releases, bugs, mises a jour securite, controles reguliers dependances et regression | E05 | DONE (E05, PR #29: docs/MAINTENANCE.md, docs/RELEASES.md, CHANGELOG.md) |
| Q24 | A+B+C+D | Plan detaille, missions agents, petites PR progressives et execution avec tests/CI | E05 + plan | REGLE |

### 10 decisions de refonte UI - remplacement complet, pas un relooking

| Question | Reponse validee | Decision et critere verifiable | Taches | Etat |
| --- | --- | --- | --- | --- |
| UI-01 | A+B | Interface de type VS Code ET design moderne; repartir de zero sur l'UI en gardant le moteur | E14, E15 | IN PROGRESS (E14 et E15 DONE ; bascule apres recette E18) |
| UI-02 | A | Panneaux gauche/centre/droite deplacables, masquables, redimensionnables et persistants | E15 | DONE (E15, PR #49) |
| UI-03 | A+D | Minimalisme pro, themes sombre/clair, couleurs, densites et accessibilite | E14, E15, E18 | IN PROGRESS (E14 et E15 DONE ; recette accessibilite E18) |
| UI-04 | D | Barre laterale permanente, onglets, palette Ctrl+Shift+P, raccourcis | E15 | DONE (E15, PR #49 : palette Ctrl+K, Ctrl+Shift+P reserve par Firefox ; raccourcis des panneaux editeur/diagnostics en E17) |
| UI-05 | A+C | Questionnaire progressif et conditionnel avec barre de progression et apercu interactif | E16 | DONE (E16, PR #43) |
| UI-06 | C | Arborescence et diagramme d'architecture interactifs, synchronises dans les deux sens | E16 | DONE (E16, PR #43) |
| UI-07 | B | Panneau diagnostics central, gravites, filtres, clic vers le champ concerne | E17a, E17 | DONE (E17a PR #44, E17 PR #51) |
| UI-08 | A | Editeur leger avec coloration syntaxique, numeros, recherche/remplacement; diff T17 conserve | E17a, E17 | DONE (E17a PR #44, E17 PR #51) |
| UI-09 | C | Codex et Claude developpent en parallele par composants, design system commun, petites PR | E14-E18 | REGLE |
| UI-10 | C+D | Tests visuels+fonctionnels progressifs, Firefox, accessibilite, performance, resolutions; ancien UI garde jusqu'a validation | E18a, E18b, E18 | IN PROGRESS (E18a et E18b DONE ; recette de la coque et bascule en E18) |

### Cadence, livraisons et suivi

1. **v1.0.0** : E01-E05 pertinents, scripts Linux verifies, audit/archivage/nettoyage, attribution Git securisee et maintenance documentee.
2. **v1.1.0** : E07-E09, trois exigences PARTIEL levees avec preuves.
3. **v2.0.0** : E06, E10-E18 et refonte UI validee visuellement/fonctionnellement; sous-lots independants, petites PR.
4. **Hors releases actives** : Q05 tests MCP GitHub reportes; Q06 extension progressive MCP; LT01 extension VS Code dans `long-terme-ideas-project-liste.md`.

**Controle de couverture :** Q01-Q24 = 24 lignes; UI-01 a UI-10 = 10 lignes; total **34/34 decisions**. Les temps affiches dans E01-E18 sont des estimations, non des durees promises. Les temps reels sont saisis manuellement. Un DONE demande tests, CI, revue et preuve de conformite.


## Cycle d'evolutions E01-E18 - en cours

Les 34 decisions et les criteres de recette sont dans [docs/ROADMAP_2026.md](docs/ROADMAP_2026.md). Le tableau de suivi des nouvelles taches (E01-E18) est maintenu ci-dessous; les 18 taches T01-T18 ci-dessus restent intactes et terminees.

| ID | Travail | Responsable | Depend de | Charge humaine estimee | Execution IA mesuree | Temps humain reel | Ecart humain | Statut | Validation |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| E01 | Auditer les refs Git, archiver liste des branches docs/*, supprimer les branches exclusivement integrees, sans toucher aux worktrees sales | Claude | - | 0,5 j | 0 h 04 (Claude) | non renseigne | non calculable | DONE | PR #27 fusionnee; docs/E01_REFS_AUDIT.md |
| E02 | Installer une protection d'attribution Git pour les depots actuels et futurs, tester commit-msg/pre-push et CI, auditer les refs anciennes | Claude | - | 1 j | 0 h 40 (Claude, attente CI comprise) | non renseigne | non calculable | DONE | PR #26 fusionnee (140bdb2); docs/GIT_ATTRIBUTION.md |
| E03 | Auditer et nettoyer fichiers temporaires, doublons, anciennes configurations et scripts obsoletes avec preuve de non-regression | Claude | E01 | 1 j | 0 h 12 (Claude) ; Codex non mesure | non renseigne | non calculable | DONE | PR #28 fusionnee (e7ce436); CI 6/6 profils; docs/E03_CLEANUP_AUDIT.md |
| E04 | Verifier les scripts d'installation existants et la PR de lanceur avant de creer installer.sh/start.sh sous Linux | Codex | - | 8 h | 0 h 19 (Codex, reprises cumulees) | inconnu | non calculable | DONE | PR #25: 289 tests, 12 ignores; CI push/PR 8/8 verte; revue independante APPROVED |
| E05 | Politique de releases, anomalies, changelog, maintenance securite et tests reguliers | Claude | E01 | 1 j | 0 h 32 (Claude, dont anomalie P0 PR #30; hors attente CI finale) | non renseigne | non calculable | DONE | PR #29 (statut effectif a sa fusion); docs/MAINTENANCE.md, docs/RELEASES.md, CHANGELOG.md |
| E06 | Confirmation explicite pour controles NON VERIFIE, journalisation et revalidation avant ecriture | Claude | - | 1 j | 0 h 17 (Claude) | non renseigne | non calculable | DONE | PR #31 (statut effectif a sa fusion); CI 8/8, 12/12 recettes Firefox; docs/ENGINE.md section E06 |
| E07 | Fusion automatique a trois voies quand une base fiable existe, sinon resolution manuelle, sauvegarde et rollback | Codex | - | 2 j (16 h) | Codex non mesure ; Claude 0 h 07 (reprise) | inconnu | non calculable | DONE | PR #32 fusionnee (c8483d4, 18/11); docs/LOCAL_WRITE.md section E07 |
| E08 | Infrastructure E2E des projets generes, adaptee a la stack, sans scenarios metier inventes | Claude | - | 2 j | 0 h 13 (Claude) | non renseigne | non calculable | DONE | PR #35 fusionnee (f88e5cf, 19/11); docs/TESTING.md genere, docs/ENGINE.md section E08 |
| E09 | Assistant de protection de branche GitHub: preparer les commandes, ne pas appliquer automatiquement | Codex | - | 1 j | Codex non mesure ; Claude 0 h 05 (reprise) | inconnu | non calculable | DONE | PR #36 (statut effectif a sa fusion); docs/BRANCH_PROTECTION.md |
| E10 | Scanner d'images Docker et SAST complementaire dont Semgrep, sans retrait des controles actuels | Claude | - | 2 j | 0 h 19 (Claude) | non renseigne | non calculable | DONE | PR #38 fusionnee (f248571, 22/11); docs/SECURITY.md section E10 |
| E11 | Verification statique des API Python/JS/TS lorsque possible; PASS/FAIL/NON VERIFIE | Claude | - | 2 j | 0 h 14 (Claude) | non renseigne | non calculable | DONE | PR #40 fusionnee (3743064); docs/ENGINE.md section E11 |
| E12 | Recherche des skills: cache expire, parallelisme, classement, reverification avant copie | Claude | - | 2 j | 0 h 11 (Claude) | non renseigne | non calculable | DONE | PR #41 fusionnee (8e8f01b); docs/ENGINE.md section E12 |
| E13 | Enrichir les stacks Python/JS/Rust/Go/Java et permettre les catalogues/regles personnalises localement | Claude | - | 4 j | 0 h 24 (Claude) | non renseigne | non calculable | DONE | PR #42 fusionnee (c058acd); docs/ENGINE.md section E13 |
| E14 | Definir le design system et les contrats de la nouvelle UI avant de coder | Codex + Claude | - | 2 j (16 h) | 0 h 15 (Codex, declare par Codex) + 0 h 10 (Claude, reprise) | non renseigne | non calculable | DONE | PR #39 fusionnee (e8d6643, 22/11); docs/design-system/ |
| E15 | Nouvelle coque UI: look professionnel minimal, themes clair/sombre, densite, panneaux deplacables et redimensionnables, onglets, navigation, palette | Claude (reattribuee par le proprietaire le 25/11) | E14 | 4 j | 0 h 27 (Claude) | non renseigne | non calculable | DONE | PR #49 fusionnee (1970629) ; docs/UI_V2_CONTRACTS.md section E15 |
| E16 | Parcours questionnaire progressif et conditionnel avec apercu dynamique, arbre et diagramme synchronises | Claude | E14 | 4 j | 0 h 14 (Claude) | non renseigne | non calculable | DONE | PR #43 fusionnee (022f932); route /v2/parcours, docs/UI_V2_CONTRACTS.md section E16 |
| E17 | Integration de l'editeur et du panneau diagnostics E17a dans la coque E15 (panneaux `editor` et `diagnostics`, onglets, raccourcis) | Codex + Claude (fichiers separes) | E15,E16 | 1 j | 0 h 11 (Claude ; Codex non intervenu) | non renseigne | non calculable | DONE | PR #51 fusionnee (037f64e) ; docs/UI_V2_CONTRACTS.md section E17 ; sous-lot E17a |
| E17a | Sous-lot E17 sans la coque : editeur leger (coloration, lignes, recherche/remplacement), panneau diagnostics filtrable et navigable, flux securises validation/comparaison/ecriture dans /v2/parcours | Claude | E16 | 2 j | 0 h 21 (Claude) | non renseigne | non calculable | DONE | Decoupage decide par le proprietaire le 22/11 (E15 non commencee) ; PR #44 fusionnee (67a55de) |
| E18 | Recette globale apres la coque E15 et l'integration E17 (parite de parcours avec l'interface actuelle, lecteur d'ecran, captures de la coque approuvees), puis bascule apres validation | Codex + Claude | E15,E16,E17 | 1 j | 0 h 02 (Claude, preparation) | non renseigne | non calculable | IN PROGRESS | Rapport docs/E18_ACCEPTANCE.md ; captures et lecteur d'ecran en attente du proprietaire ; sous-lots E18a, E18b |
| E18a | Sous-lot E18 sans la coque : recette progressive de /v2/parcours (clavier seul, ordre et visibilite du focus, cibles, resolutions de reference dont 360 px, contrastes rendus des deux themes, budgets de performance mesures, aucune erreur JS ni ressource bloquee), defauts corriges, captures soumises a approbation ; aucune bascule | Claude | E16,E17a | 2 j | 0 h 18 (Claude) | non renseigne | non calculable | DONE | Decoupage decide par le proprietaire le 22/11 (E15 non commencee) ; PR #45 fusionnee (9bc72d6) ; rapport docs/E18A_ACCEPTANCE.md |
| E18b | Sous-lot E18 : parite du parcours v2 avec l'interface actuelle (brouillon, export/import JSON, reinitialisation, profils, architecture manuelle, skills externes, controles en ligne, archive ZIP, protection de branche) ; aucune bascule | Claude | E16,E17 | 3 j | 0 h 33 (Claude) | non renseigne | non calculable | DONE | Decoupage decide par le proprietaire le 25/11 (6 fonctions absentes de la v2) ; PR #53 fusionnee (a74294e) ; docs/UI_V2_CONTRACTS.md section E18b |

### E14 - reprise - 22 novembre 2026 (Claude Code, Codex indisponible)
- Charge humaine estimee: 2 j (16 h). Execution IA mesuree (horloge, pas du temps humain): Codex 0 h 15 tel que declare par Codex (non remesure); Claude 11 h 43 -> 11 h 53 (0 h 10), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Audit avant reprise: branche `feat/e14-design-system` (6 commits de Codex, 10 h 47 -> 10 h 59, pousses, PR #39 brouillon), worktree `.tmp-e14-worktree` avec 2 fichiers non commites (TODO.md, ROADMAP : temps 0 h 10 -> 0 h 15), inactif depuis 11 h 00; worktree de relecture `/tmp/forge-e14-review.../review-final2` propre. Aucun des deux modifie : travail repris dans `Forge-my-Project-e14-claude` (modifications non commitees de Codex reportees a l'identique), statut repasse de DONE a IN PROGRESS (PR non validee).
- Conserve de Codex: identite (trois couleurs exactes du SVG), typographie du logo, grille 4 px, tokens clair/sombre, composants de base, six maquettes, contrats UI v2, 7 tests.
- Termine pendant la reprise: cuivre du logo `#D97757` en remplissage (texte encre 4.76:1) et cuivres derives a la meme teinte et saturation (texte clair `#AB4727` 4.71:1, indicateur `#D25D37` 3.22:1, texte sombre `#E09075` 4.72:1) au lieu de `#963B20` (brun) et `#F0A78E` (rose); correction d'un contraste sombre en echec (texte cuivre sur fond selectionne 4.26:1 -> 4.70:1); composants manquants (rail, navigation, onglets ARIA fonctionnels, poignee `separator`, palette de commandes, tiroir, etats chargement/vide/indisponible/erreur, raccourcis); page `docs/design-system/components.html`; palette de commandes interactive dans les maquettes (Ctrl+K / Ctrl+Shift+P, combobox + listbox, Echap, retour du focus, commande indisponible non executable); controles natifs cuivre; champs desactives distincts.
- Verifications: 12 tests design system (7 Codex + 5 reprise: teinte et saturation du cuivre, contrastes sur chaque surface et theme, couverture des composants, modele ARIA de la palette, ressources locales et syntaxe JS); captures Firefox headless reellement inspectees (reference clair/sombre 1440, maquettes clair/sombre 1440, questionnaire 360 sans defilement horizontal).

### E14 - 22 novembre 2026 (Codex, PR #39)
- Charge humaine estimee : 2 j (16 h). Execution IA mesuree manuellement : 10 h 45 -> 11 h 00 (0 h 15), hors attente CI. Temps humain reel : non renseigne. Ecart humain : non calculable.
- Identite : `assets/logo.svg` confirme comme master et `assets/favicon.svg` comme variante compacte; couleurs exactes `#F5F0E8`, `#292726`, `#D97757`, sans redessiner les assets.
- Livre : tokens CSS clair/sombre, composants de reference, six maquettes statiques consultables, règles responsive/accessibilite, et contrats d'etat/frontiere pour E15 et E16. L'interface de production, le moteur et les endpoints ne sont pas modifies; E15 n'est pas commence.
- Verifications locales : 7 tests E14 (couleurs SVG, six écrans, references accessibles, contrastes essentiels clair/sombre, visibilité et semantique statique), syntaxe JavaScript, rendu Firefox headless 1440x900 clair/sombre et 360x800 avec correction du reflow mobile. Suite complete locale NON VERIFIEE : seul Python 3.10 est disponible (le projet exige 3.11+, `tomllib` absent) et le bac a sable refuse les sockets; CI et revue independante : voir PR #39.

### E02 - 15 novembre 2026 (Claude Code, branche feat/e02-git-attribution-guard)
- Execution IA mesuree (horloge, pas du temps humain): 22 h 09 -> 22 h 49 (0 h 40, attente CI comprise), worktree dedie `Forge-my-Project-e02` depuis origin/main 1d7116e (PR #22 fusionnee).
- Audit initial: PR #23 n'avait livre que `.claude/settings.json` et la documentation; aucun hook ni job CI ne controlait l'attribution. `main` sans protection de branche ni ruleset (API GitHub 404 / liste vide): la CI n'y est pas encore obligatoire.
- Livre: `templates/hooks/attribution_guard.py.tmpl` (source unique, stdlib, Python 3.7+; lien `scripts/attribution_guard.py`): commit-msg (identite effective via `git var`, trailers, pied automatique), pre-push, check-range, audit, ci (plage de l'evenement + titre/description de PR), install/uninstall (hooks existants conserves en `.local`, refus sur hooks versionnes sans `--allow-tracked`), install-template (`init.templateDir` global modifie seulement apres confirmation).
- Forge-my-Project: `.githooks/commit-msg` et `.githooks/pre-push` ajoutes, `.githooks/pre-commit` inchange; job CI `attribution`. Projets generes: garde copie, commit-msg/pre-push, job CI, regle AGENTS.md, contexte de protection CONTRIBUTING.md, attribution Claude desactivee.
- Tests: `tests/test_attribution_guard.py` (20, depots Git reels): commit normal et mention documentaire acceptes; Co-Authored-By Claude et Codex, auteur Claude, committer Claude, identite `user.name` Codex refuses; push refuse (main et nouvelle branche) vers un distant nu apres `--no-verify`; push propre et suppression de branche acceptes; hooks existants executes avec stdin intact puis restaures; nouveau depot et clone proteges via modele; projet genere protege; mode CI push/PR refuse puis accepte. Mutation du garde: 6, 14 et 1 echecs detectes.
- Resultats locaux: 265 tests OK (12 ignores); `smoke_generated.py` 4/4 profils Python PASS avec le job attribution; profils TypeScript en echec local a `npm install` (`edgesOut`), reproduit a l'identique sur origin/main (npm 10.8.2/Node 20 local); Ruff check/format du garde OK; audit de toutes les refs: aucune attribution interdite (les 2 commits T10/T15 a trailer ne sont plus atteignables).
- CI PR #26: run 43764427826 rouge (job genere `attribution` du smoke heritait de `GITHUB_EVENT_PATH` de la PR Forge: SHA absents, refus fail-closed attendu); correction du harnais `tests/smoke_generated.py` + test du refus; run 43764652363 vert: python, securite, attribution (`ci : attribution conforme`, 20 tests du garde), CI generee 6/6 profils PASS dont TypeScript. Apres fusion de main: runs 43765231637 (push) et 43765237805 (pull_request, plage de la PR + titre et description controles) verts, PR MERGEABLE. Aucun run `pull_request` tant que la PR etait en conflit avec main (PR #24): `origin/main` fusionne dans la branche, sans rebase ni push force.
- Limites: hooks locaux contournables (`--no-verify`); job CI bloquant seulement apres protection de branche par le proprietaire (commande dans docs/GIT_ATTRIBUTION.md); detection par liste d'agents a maintenir; titre/description de PR controles aux evenements opened/synchronize/reopened seulement; installation dans les autres depots et modele global non executes sur la machine (commandes fournies).

### E01 - 16 novembre 2026 (Claude Code, branche docs/e01-refs-audit)
- Execution IA mesuree (horloge, pas du temps humain): 22 h 32 -> 22 h 36 (0 h 04, hors attente CI), worktree dedie `Forge-my-Project-e01` depuis origin/main 140bdb2 (PR #26 fusionnee).
- Rapport complet: [docs/E01_REFS_AUDIT.md](docs/E01_REFS_AUDIT.md) (inventaire, methode, archive nom/SHA des branches docs/*, simulation, execution).

- Preuves: chaque branche testee par ascendance, `git cherry`, simulation de fusion dans un worktree jetable (detecte squash et reecritures) et `attribution_guard.py check-range`; worktrees controles (modifications, non suivis, ignores, stash). 7 branches distantes integrees supprimees apres `push --dry-run` (docs/development-roadmap-todo, docs/validated-project-specification, docs/roadmap-34-decisions-2026, fix/no-ai-coauthor-attribution, feat/e02-git-attribution-guard, claude/start-launcher, codex/file-preview); branche locale et worktree E02 retires (`worktree remove` sans force, `branch -d`). Distant: 9 -> 2 branches (main, feat/e04-linux-launcher).
- Conserve: feat/e04-linux-launcher (PR #25 ouverte, worktree modifie), worktree principal (TODO.md non commite: main local non avance), worktrees propres `.forge-start` et `Forge-my-Project-codex` rattaches a d'autres sessions (inutilite non demontree).
- Attributions IA: aucune sur branches, tags, stash ou reflogs. Residuel: les commits T10/T15 a trailer Claude restent references par les refs GitHub en lecture seule `refs/pull/14-19/head` et `refs/pull/21/head` (clone miroir); purge possible uniquement par le support GitHub, a la demande du proprietaire.
- Limites: aucune reecriture, aucun push force; restauration d'une branche supprimee: `git push origin <SHA>:refs/heads/<branche>` (SHA archives dans le rapport).

### E03 - 16 novembre 2026
- Audit complet: [docs/E03_CLEANUP_AUDIT.md](docs/E03_CLEANUP_AUDIT.md).
- Aucun fichier suivi supprime: aucun candidat n'etait demonstrablement obsolete; les composants historiques, preuves T18, configurations actives et scripts references sont conserves.
- Caches Python ignores produits par les tests supprimes uniquement dans le worktree E03; aucun autre worktree touche.
- Tests locaux: 265 PASS, 12 ignores; quatre profils Python PASS; profil TypeScript bloque localement a `npm install` (`edgesOut`, npm 10.8.2/Node 20), sans lien avec E03.
- CI PR #28 (0e62860): runs 43964140186 (push) et 43964178570 (pull_request) verts; CI generee 6/6 profils PASS, dont typescript-api-express et typescript-web-react: la limite npm est locale.
- Execution IA mesuree (horloge, pas du temps humain): Claude 22 h 47 -> 22 h 53 puis 22 h 54 -> 23 h 00 (0 h 12); partie Codex (commit 0e62860, PR #28) non mesuree, donc ecart partiel.
- Corrections de la reprise: Q15 remis a TODO (nettoyage automatise des worktrees non construit), Q14 PARTIEL; doublon de lien vers docs/CONVENTIONS.md retire d'AGENTS.md.

### E05 - 17 novembre 2026 (Claude Code, branche docs/e05-maintenance-releases)
- Charge humaine estimee: 1 j (8 h). Execution IA mesuree (horloge, pas du temps humain): 19 h 36 -> 20 h 07 (0 h 32), dont 19 h 47 -> 20 h 06 pour l'anomalie P0 (PR #30); attente de la CI finale non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Livre: [docs/MAINTENANCE.md](docs/MAINTENANCE.md) (anomalies P0-P3 en issues GitHub, controles reguliers, dependances et epinglages, regressions, SemVer et changelog, conditions de release, rollback), [docs/RELEASES.md](docs/RELEASES.md) (v1.0.0, v1.1.0, v2.0.0 avec taches et preuves), [CHANGELOG.md](CHANGELOG.md) (`[Unreleased]`, aucune version publiee). Aucun mecanisme automatique ajoute hors un test.
- Controle CI: `tests/test_release_policy.py` (8 tests, job `python`): format du changelog, statuts E01-E18 identiques dans TODO.md et ROADMAP, dependances respectees, aucune execution IA dans la colonne de temps humain, chaque tache rattachee a un jalon, liste de controle des releases alignee sur les jobs CI reels. 7 mutations injectees, toutes detectees.
- Suivi: colonnes E01-E18 remplacees par charge humaine estimee / execution IA mesuree / temps humain reel / ecart humain; donnees T01-T18 inchangees avec note de lecture; libelles des notes E01-E03 precises. Statuts corriges sur preuve: ROADMAP E03 DONE (PR #28) et E04 IN PROGRESS (PR #25 ouverte); Q03 PARTIEL, Q21 TODO (plan pret), Q23 DONE a la fusion.
- Verifications: tests locaux OK apres fusion de main (283, 12 ignores); `attribution_guard.py audit` conforme; aucune release, aucun tag.
- Anomalie P0 rencontree: premiere CI de la PR #29 rouge (`CI generee des profils predefinis`), reproduite sur main (relance du run 43966479454, tentative 2: rouge) car GHSA-fc5q-39xc-vjpf (picomatch <= 4.0.7, high, aucune version corrigee) bloque l'audit npm des profils TypeScript. Decision du proprietaire: exception datee et ciblee. PR #30 fusionnee (2995c81): passerelle `scripts/security/npm_audit_gate.py`, exception jusqu'au 2026-12-17, registre dans docs/SECURITY.md; CI verte, 6/6 profils, dependance vulnerable injectee toujours bloquee. Branche et worktree du correctif nettoyes.
- Coordination Codex: la PR #25 etait deja en conflit avec main sur TODO.md (ligne E04 modifiee par ab23081). Resolution attendue cote E04: garder les colonnes E05 et le texte E04 de Codex. Branche et worktree de Codex non modifies.

### E06 - 17 novembre 2026 (Claude Code, branche feat/e06-unverified-confirmation)
- Charge humaine estimee: 1 j (8 h). Execution IA mesuree (horloge, pas du temps humain): 20 h 45 -> 21 h 02 (0 h 17), attente CI comprise sauf la derniere. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Constat initial: confirmation des avertissements uniquement dans le navigateur (case comptant N avertissements); serveur sans controle de confirmation, aucun NON VERIFIE bloquant, aucune peremption.
- Livre: `forge/verification/unverified.py` (inventaire nom/statut/raison exacte/risque/criticite, jeton HMAC lie a la configuration, aux options reseau et aux controles exacts); API: `unverified` dans plan et comparaison, `acknowledge` exige a l'ecriture (409 si absent ou perime, 422 si critique), archive bloquee si critique, journal `confirmations` avec statut inchange. Critiques: controles de securite NON VERIFIE (vulnerabilites, outils, actions, MCP) et absence de verification en ligne au niveau hardened. Interface: liste detaillee, blocage affiche, reconfirmation apres refus serveur ou controles changes.
- Tests: `tests/test_unverified_confirmation.py` (14: tout PASS, FAIL, NON VERIFIE, confirmation acceptee, refusee, perimee apres redemarrage, configuration modifiee, nouveau controle, echec de verification juste avant ecriture, critique hardened, hardened hors ligne, non critique confirmable, secret toujours bloque, seuils et exception picomatch inchanges); 3 mutations du module detectees; recette Firefox E06 ajoutee (`test_unverified_checks_confirmation_and_critical_block`). Suite locale: 298 tests OK, 13 ignores.
- Recette Firefox locale: NON VERIFIE (geckodriver ne lance pas Firefox snap dans ce bac a sable, erreur 500 a la creation de session); executee par la CI (job `python`, FORGE_E2E=1): 12/12 recettes OK dont E06 (run 44163471254, pull_request). CI PR #31: push 44163461864 et pull_request 44163471254 verts, 8/8 jobs, 6/6 profils generes.
- Securite preservee: seuils npm audit et Bandit, exception picomatch, detection de secrets, validation des skills et MCP, sauvegardes et rollback inchanges (tests existants verts).

### E07 - 18 novembre 2026 (Codex, repris par Claude Code)
- Charge humaine estimee: 2 j (16 h). Execution IA mesuree (horloge, pas du temps humain): Codex non mesure (commits de 15 h 08 a 15 h 14, aucune duree deduite de Git); Claude 15 h 26 -> 15 h 33 (0 h 07), reprise sur demande du proprietaire dans un worktree distinct (`Forge-my-Project-e07-claude`), le worktree de Codex n'a pas ete modifie. Temps humain reel: inconnu. Ecart humain: non calculable.
- Livre par Codex: `forge/filesystem/merge.py` (fusion a trois voies conservatrice), entrees `base_available`/`auto_merge`/`merge_conflicts`, action `auto` sur decision explicite avec controles de contenu, jeton couvrant les bases, interface et tests (9).
- Corrections de la reprise: (1) une modification identique des deux cotes etait appliquee deux fois (ligne dupliquee); (2) bases seulement en memoire du serveur, perdues a chaque redemarrage: magasin persistant `forge/filesystem/bases.py` hors du projet (0700/0600, empreinte SHA-256, base alteree ou etrangere ignoree, enregistrement uniquement apres ecriture reussie); (3) un fichier remplace ou fusionne passait en 0644 (0600 utilisateur perdu), y compris au rollback: mode existant conserve, bit d'execution ajoute aux scripts generes; (4) le test d'echec d'ecriture n'exercait pas le rollback (echec des la sauvegarde): nouveau test d'echec partiel. Interface: detail des conflits et etat des bases dans le rapport. Tests isoles du dossier personnel (`FORGE_STATE_DIR`).
- Tests: `tests/test_filesystem_merge.py` 21 (sans conflit, conflits localises, sans base, base alteree ou etrangere, redemarrage, modification concurrente, echec d'ecriture, restauration octets et mode apres ecriture partielle, permissions utilisateur et scripts, bases privees, base inchangee apres echec ou conservation, secret fusionne refuse); 4 mutations detectees (dont le rollback apres correction du test). Suite locale complete OK (13 ignores: recettes Firefox, executees en CI).

### E08 - 19 novembre 2026 (Claude Code, branche feat/e08-generated-e2e)
- Charge humaine estimee: 2 j (16 h). Execution IA mesuree (horloge, pas du temps humain): 21 h 40 -> 21 h 52 (0 h 13), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Constat: les six squelettes n'ont aucun code metier (pas d'application FastAPI/Django/Express, pas d'interface React); un E2E HTTP ou navigateur n'aurait rien a tester sans inventer de scenario.
- Livre (aucune dependance ajoutee): Python, temoin `e2e/test_installed_package.py` (format unittest, lance par pytest ou unittest) qui installe le livrable sans `-e` et verifie, dans un processus isole hors des sources, l'import depuis le site-packages et la version; Node, temoin `e2e/entrypoint.e2e.mjs` (lanceur integre `node --test`) qui charge `dist/index.js` apres build (ou `src/index.js` en JavaScript), script `npm run test:e2e`; job CI `Bout en bout (livrable)` distinct et bloquant, ajoute a la commande de protection de CONTRIBUTING.md; section E2E de TESTING.md (commandes, environnement dedie, non-applicabilite navigateur/HTTP/CLI, ajout d'un outil seulement apres verification du registre); commande dans AGENTS.md; Ruff et mypy couvrent `e2e/`. Sans lanceur de tests Python: aucun job, NON APPLICABLE documente.
- Tests: `tests/test_engine_e2e.py` (10: temoin Python en echec sans installation, en echec en mode editable, jamais vert via PYTHONPATH=src, vert sur paquet installe; temoin Node vert puis en echec sur point d'entree casse; six profils; aucune dependance E2E ajoutee; non applicable; separation des tests unitaires). Mutation du controle d'emplacement detectee; l'isolation `-I` est une defense supplementaire (le controle decisif est l'emplacement). Smoke local: 4 profils Python PASS (job e2e, Ruff, mypy, hooks); profils TypeScript: limite npm locale connue, verifies en CI.
- Corrections de suivi sur preuve: E07 et Q09 DONE (PR #32 fusionnee, c8483d4).
- Revue: auto-revue de l'auteur (non independante); revue independante a faire par Codex ou le proprietaire.

### E09 - 19 novembre 2026 (Codex, repris par Claude Code)
- Charge humaine estimee: 1 j (8 h). Execution IA mesuree (horloge, pas du temps humain): Codex non mesure (travail non commite, derniere modification 21 h 44); Claude 21 h 59 -> 22 h 04 (0 h 05), reprise sur demande du proprietaire par copie du travail non commite dans un worktree distinct (`Forge-my-Project-e09-claude`); le worktree de Codex n'a pas ete modifie. Temps humain reel: inconnu. Ecart humain: non calculable.
- Livre par Codex: `forge/github/branch_protection.py` (inspection GET uniquement: depot, branche, commit de tete, check-runs, permissions, protection actuelle; commande `gh api --method PUT` rendue en texte, jamais executee), route `/api/github/protection/prepare`, interface, `docs/BRANCH_PROTECTION.md`, 10 tests.
- Corrections de la reprise: seuls les checks reussis a chaque execution sur le commit de tete sont proposes (un check en echec, annule, ignore ou en cours aurait ete rendu obligatoire); commande generee seulement si le check d'attribution a reussi; test d'echappement du heredoc par un nom de check hostile; analyse des erreurs `gh` tolerante a un stderr absent (test existant en erreur).
- Validation reelle (lecture seule) sur ce depot: protection de main confirmee absente, droits administrateur observes, 2 checks en cours exclus avec avertissement, commande proposee affichee et non executee.
- Tests: `tests/test_branch_protection.py` 13; suite locale complete OK.

### Releases v1.0.0 et v1.1.0 - 19 novembre 2026 (Claude Code, a la demande du proprietaire)
- Decision du proprietaire : v1.0.0 sur `9effa1d` (fusion de la PR #25 : E01 a E05, sans E06), puis v1.1.0 sur le commit de release de main (E06 a E09). Aucun tag ni release n'existait avant.
- Conditions (docs/MAINTENANCE.md section 6), v1.0.0 :
  - (1) criteres du jalon faits avec PR ;
  - (2)(3) CI de 9effa1d relancee le jour de la release (run 44320746923, tentative 2) : 4 jobs verts, dont la CI generee avec `--verify` ;
  - (4) `attribution_guard.py audit` sans attribution interdite ;
  - (5) aucune issue ouverte ;
  - (6) section datee et limites dans CHANGELOG.md ;
  - (7) `installer.sh` puis `start.sh` executes depuis un clone propre de 9effa1d (page et API en HTTP 200).
- v1.1.0 : memes conditions, verifiees sur le commit de release apres fusion et avant le tag (preuves dans la release GitHub).
- Tags annotes `vX.Y.Z`, jamais deplaces ; releases GitHub reprenant les sections du CHANGELOG.

### E10 - 22 novembre 2026 (Claude Code, branche feat/e10-semgrep-image-scan)
- Charge humaine estimee: 2 j (16 h). Execution IA mesuree (horloge, pas du temps humain): 10 h 46 -> 11 h 04 (0 h 19), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Outils verifies a la source: Semgrep 1.184.0 (PyPI, LGPL-2.1, publie le 2026-11-05, choisi plutot que 1.186.0 du 2026-11-18 pour son anciennete) et Trivy v0.76.2 (release officielle du 2026-11-05, Apache-2.0, empreinte SHA-256 du fichier de sommes publie); aucune vulnerabilite OSV pour ces versions le 2026-11-22.
- Livre: regles Semgrep locales (12 regles Python/JS/TS), passerelles Semgrep et image (fail-closed), etape Semgrep pour tous les projets generes (apres Bandit), etape Trivy pour les projets Docker des qu'un Dockerfile existe (NON VERIFIE sinon, aucun Dockerfile invente), Semgrep sur Forge en CI, verification en ligne de Semgrep et Trivy, seuils non assouplissables au chargement du catalogue.
- Tests: `tests/test_semgrep_rules.py` (5, vrai Semgrep: chaque regle declenchee sur du code vulnerable, aucune sur les variantes sures, passerelle en echec des qu'une vulnerabilite est introduite, WARNING bloquant en hardened, analyse vide refusee) executes localement et en CI; `tests/test_security_e10.py` (14: image haute et critique bloquees, seuils, non corrige non ignore, rapport invalide/absent/vide refuse, Semgrep incomplet/vide refuse, catalogue, six profils, anciens controles, aucun contournement, Docker seulement si Dockerfile, hardened); verification en ligne (empreinte Trivy alteree = FAIL); smoke de securite Python local 5/5 (dont script dangereux hors src detecte par Semgrep).
- Limites: Trivy n'a pas pu etre execute localement (telechargement et execution du binaire refuses par le controle de permissions) : son execution reelle et la detection sur image vulnerable sont prouvees en CI uniquement; Semgrep recupere les erreurs de syntaxe sans les signaler (detectees par Ruff/tsc du job qualite); dossiers de tests exclus par defaut par Semgrep; une image Debian recente peut porter des vulnerabilites hautes non corrigees et faire echouer la CI d'un projet Docker (politique bloquante assumee).
- Revue: auto-revue de l'auteur (non independante).

### E11 - 22 novembre 2026 (Claude Code, branche feat/e11-static-api-verification)
- Charge humaine estimee: 2 j (16 h). Execution IA mesuree (horloge, pas du temps humain): 12 h 14 -> 12 h 27 (0 h 14), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Constat: le controle `api` etait un NON VERIFIE generique par paquet. Les contrats reels sont les imports des fichiers generes (plugins ESLint, Vitest, modules Node integres, bibliotheque standard Python) et le module importable des bibliotheques Python.
- Livre: `forge/verification/api.py` (extraction `ast` / declarations `import` / imports dynamiques litteraux / proprietes sur import par defaut; classement hors ligne; preuve en ligne par archive npm SHA-512 et roue PyPI SHA-256, lues sans extraction ni execution), champ catalogue `module`, `fetch_bytes` borne et hote `files.pythonhosted.org`, diagnostic bloquant `api-static`, champ `api` de la reponse du plan et affichage hors ligne dans l'interface; ancien `api_unverified` supprime.
- Validation reelle en ligne: six profils, 12 a 17 contrats chacun, tous PASS avec preuve (ex. `vitest/config` -> `defineConfig` dans `config.d.ts` de vitest 5.1.1; module `fastapi` dans `fastapi-0.165.0-py3-none-any.whl`).
- Tests: `tests/test_api_verification.py` (12, archives .tgz et .whl reelles construites en memoire: export direct et via reexports PASS, export absent FAIL, reexport externe NON VERIFIE, sous-chemin non exporte FAIL, export par defaut et proprietes, paquet sans types et archive alteree NON VERIFIE, paquet inconnu FAIL, module present/absent/sdist/empreinte alteree, imports non declares/integres inconnus/fichier local absent FAIL hors ligne, FAIL bloquant la generation); 3 mutations detectees; 2 tests anciens mis a jour (stdlib desormais PASS hors ligne, API tierces toujours NON VERIFIE sans archive). Suite locale: 393 tests OK.
- Limites: analyse par motifs des declarations TypeScript (pas de compilateur): un reexport externe ou un export calcule reste NON VERIFIE; proprietes sur import par defaut = preuve plus faible; imports dynamiques calcules ignores; la verification en ligne telecharge les archives (20 Mo maximum).
- Revue: auto-revue de l'auteur (non independante).

### E12 - 22 novembre 2026 (Claude Code, branche feat/e12-skills-search)
- Charge humaine estimee: 2 j (16 h). Execution IA mesuree (horloge, pas du temps humain): 14 h 07 -> 14 h 18 (0 h 11), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Constat: chaque recherche relisait tous les catalogues et depots en serie (un appel par SKILL.md); egalites de score departagees par depot puis nom, sans le chemin; la copie relisait le commit approuve mais ignorait l'etat actuel de la branche suivie.
- Livre: `forge/skills/cache.py` (candidats seulement, cle SHA-256 de la requete, duree `search.cache_ttl_seconds` = 3600 bornee a 86 400, 0 = desactive, dossier d'etat 0700 / fichiers 0600, entree perimee, alteree, mal formee ou horloge revenue en arriere ignoree, resultat partiel jamais mis en cache, option `refresh`); recherche en trois phases paralleles (`search.max_workers` = 4, borne 1-8) dont l'ordre ne depend pas des reponses; score nom x2 + description et ordre total (source reconnue, score, nom, depot, chemin), doublons retires; reverification amont avant copie (avertissements `skill-upstream-changed` / `skill-upstream-unverified`, la version approuvee reste la seule copiee) et champ `upstream` de `/api/skills/verify`; bouton « Relancer sans le cache » et age du cache dans l'interface; `skills-search --refresh` en CLI.
- Tests: `tests/test_skills_search_cache.py` (23: cache touche sans reseau, expiration, refresh, horloge, resultat partiel, cle, permissions, entrees corrompues ou forgees, TTL borne, candidat du cache refuse a la copie si le skill a change; concurrence mesuree > 1 et = 1 en serie, meme resultat sur 5 ordres de reponse aleatoires, source en echec isolee, bornes des workers; score, ordre total, doublons; amont inchange, modifie (version approuvee copiee), retire, illisible, copie refusee sans controle amont, verification; API web `refresh` et `cache`). Suite locale: 416 tests OK (18 ignores). Bandit OK.
- Validation reelle GitHub (gh authentifie, profil web React): 8 candidats identiques en serie et en parallele; 1 fil 29,6 s, 4 fils 7,8 s; deuxieme recherche servie par le cache en 0,9 s (contre 10,5 s).
- Limites: Semgrep non execute localement (binaire `semgrep-core` absent du paquet installe) : CI uniquement; le cache est local a la machine; l'etat amont ajoute deux appels GitHub par skill approuve; un changement amont n'est qu'un avertissement (choix: la version examinee et epinglee reste copiee).
- Revue: auto-revue de l'auteur (non independante).

### E13 - 22 novembre 2026 (Claude Code, branche feat/e13-stacks-local-catalogs)
- Charge humaine estimee: 4 j (32 h). Execution IA mesuree (horloge, pas du temps humain): 14 h 23 -> 14 h 47 (0 h 24), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Constat: seules les piles Python et Node existaient; aucune extension du catalogue sans modifier le depot.
- Livre: technologies `rust` (1.100), `go` (1.26/1.27), `java` (Temurin 21/25) et `junit` (ecosysteme `maven` nouveau: coordonnees validees, metadonnees officielles repo1.maven.org lues par motif, version stable, OSV Maven); squelettes testables (Cargo.toml + lib.rs [+ main.rs], go.mod + paquet + test [+ cmd/], pom.xml + classe [+ test JUnit]); version JUnit exacte si verifiee, sinon intervalle `[6,7)`; actions `setup-go` v7.0.0 et `setup-java` v6.2.0 epinglees (SHA verifies, versions de plus de deux semaines); toolchain Rust par rustup; `.gitignore`, hooks et regles par pile; profils `rust-cli`, `go-cli`, `java-library` executes par le job `generated-projects`; controle `security-stack-unverified`. Catalogue personnel `forge/config/local.py` (technologies, regles, templates; bornes, aucun lien, aucun remplacement ni `override`, avertissements `local-technology`/`local-rule`), champ `source` et `local` de `/api/catalog`, mention dans l'interface, CLI `local-catalog`.
- Validation reelle: verification en ligne des trois profils, 18 a 20 controles chacun, tous PASS (runtimes rust 1.100, go 1.27, eclipse-temurin 25; JUnit 6.1.3 sur Maven Central et OSV; setup-go et setup-java). Squelette Rust genere: rustfmt, Clippy -D warnings, cargo test (1 test) et execution PASS avec cargo 1.98 local (`--ignore-rust-version`).
- Tests: `tests/test_stacks_local_catalog.py` (22: squelettes, bibliotheques sans point d'entree, CI et toolchains epinglees, hooks/.gitignore, Java sans JUnit signale, version JUnit verifiee ou intervalle, NON VERIFIE strict/bloquant hardened, profils, squelettes Rust et Go reels si outil present; Maven: version stable, statuts, aucun acces sans lecteur, coordonnees; catalogue local: absent, technologie et regle utilisees avec avertissements et commande jamais executee, aucun remplacement, override/collision/chemin hors dossier refuses, conflit de fichier, bornes et liens, templates bornes, dossier explicite isole, API et CLI). 4 mutations detectees. Suite locale: 438 tests OK (19 ignores). Bandit OK.
- Limites: Go et Maven absents localement: squelettes Go et Java prouves en CI uniquement (job `generated-projects`); aucun audit de dependances ni SAST Rust/Go/Java (NON VERIFIE, bloquant en hardened); pas de seuil de couverture ni de socle E2E pour ces piles; Rust ne supporte que la version courante (cycle de six semaines: le catalogue devra suivre); pas d'API statique (E11) pour Rust/Go/Java; les piles Python/JS existantes ne sont pas enrichies dans cette PR; le catalogue personnel est edite a la main (JSON), sans editeur dans l'interface.
- Revue: auto-revue de l'auteur (non independante).

### E16 - 22 novembre 2026 (Claude Code, branche feat/e16-progressive-questionnaire)
- Charge humaine estimee: 4 j (32 h). Execution IA mesuree (horloge, pas du temps humain): 15 h 59 -> 16 h 13 (0 h 14), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Livre: route distincte `/v2/parcours` (`ui/v2/journey.{html,js,css}`, tokens E14 servis depuis `docs/design-system/tokens.css`), interface actuelle inchangee; six etapes rendues depuis `/api/catalog` (projet, langages, outils, versions, agents et securite, MCP) avec etat complete / a completer / sans objet, barre de progression et etapes sans objet sautees; technologies proposees seulement si leurs prerequis sont selectionnes, incompatibilites signalees, reponses devenues invalides retirees (jamais envoyees) avec message; apercu `/api/plan` differe (350 ms) a identifiant de requete, reponse ancienne ignoree; diagnostics ordonnes (erreurs, avertissements, informations); arborescence en listes imbriquees natives; diagramme SVG technologies -> regles -> fichiers construit uniquement a partir du champ `graph` du plan (nouveau, en lecture seule); `selectedPath` partage arbre/diagramme/contenu, selection inconnue refusee; focus conserve lors d'un nouveau rendu et deplace seulement sur action explicite; theme clair/sombre selon le systeme.
- Tests: `tests/test_journey_v2.py` (6: route et ressources servies sous CSP, interface actuelle inchangee, aucun HTML injecte ni ressource distante ni stockage, seules API appelees, graphe complet et sans dependance inventee, fichiers de skills, champ `graph`); `tests/test_e2e_journey_firefox.py` (6, Firefox reel: etapes conditionnelles et focus, reponses masquees retirees, synchronisation arbre/diagramme dans les deux sens et refus d'un chemin inconnu, diagramme limite au plan, largeurs 500/768/1280/1920 sans defilement horizontal, reponse ancienne ignoree). Suite locale: 450 tests OK (25 ignores sans E2E); avec Firefox, 1 erreur intermittente de `test_linux_scripts` (port occupe sous charge, passe seule, fichier non modifie).
- Limites: preversion sans archive, ecriture, profils, import/export, skills ni verification en ligne (l'interface actuelle reste la reference jusqu'a E18); pas de coque E15 (panneaux, onglets, palette, choix du theme); arbre en listes natives (pas de modele ARIA tree); le diagramme ne montre que les regles produisant des fichiers; 360 px non atteignable par redimensionnement Firefox (a valider en E18); captures non approuvees.
- Revue: auto-revue de l'auteur (non independante).

### E18 - preparation - 26 novembre 2026 (Claude Code, branche feat/e18-acceptance-prep)
- Execution IA mesuree (horloge, pas du temps humain): 20 h 24 -> 20:26 (0 h 02), attente CI non comptee. Temps humain reel: non renseigne.
- Livre: `docs/E18_ACCEPTANCE.md` (etat de chaque condition de bascule avec sa preuve, matrice de parite v1 -> v2, checklist Orca en 14 points, procedure de regeneration des captures, proposition de bascule non appliquee) ; heure du brouillon au format francais (24 h).
- Captures: 30 regenerees le 26/11 (coque, atelier et parite compris), non versionnees, soumises au proprietaire.
- En attente du proprietaire: approbation des captures, passage de la checklist Orca (Orca installe sur le poste), decision de bascule. A faire: revue independante (absence de P0/P1).
- Revues automatiques des PR #54 et #55: P1 d'attribution sur `4c4ee4f` et `adaf437`, commits absents du depot (verifie par `git cat-file`) ; `attribution_guard.py check-range a74294e..main` passe. Faux positifs.

### Revues automatiques non traitees - 26 novembre 2026 (Claude Code, branche fix/review-findings)
- Origine: commentaires de relecture laisses sur des PR deja fusionnees, relus le 26/11 : #47 (2 P1, `scripts/worktree_cleanup.py`), #53 (2 P2, parcours v2), #45 (1 P2, editeur). Le P1 d'attribution de #45 porte sur un commit Codex deja integre : non corrigeable sans reecrire l'historique (interdit), signale.
- Execution IA mesuree (horloge, pas du temps humain): 20 h 01 -> 20:10 (0 h 09), attente CI non comptee. Temps humain reel: non renseigne.
- Corrige: worktree exterieur a la racine conserve sauf `--allow-external CHEMIN` exact ; reinspection de chaque candidat juste avant `git worktree remove` (HEAD, branche, verrou, operation, fichiers ignores, integration) ; brouillon v2 sans type de projet restaurable (type omis du document, laisse non choisi a la restauration) ; « Vérifier en ligne » possible apres un echec (configuration envoyable, l'archive et l'ecriture exigent toujours un plan valide) ; largeur du document entier portee par la couche virtualisee de l'editeur.
- Tests: `tests/test_worktree_cleanup.py` (12, dont worktree exterieur, changement apres inspection, course pendant `--apply`) ; `tests/test_e2e_parity_firefox.py` (+2) ; `tests/test_e2e_editor_firefox.py` (+1). 8 mutations injectees, toutes detectees. Suite locale OK (62 ignores sans E2E) ; Firefox v2 local 41/43, les 2 echecs etant l'ecriture locale refusee (dossier temporaire dans le depot), a confirmer par la CI. Budgets E18a respectes (max 404 ms pour l'apercu, 66 ms pour une interaction).
- Limite: une modification entre la reinspection et `git worktree remove` reste possible (fenetre de quelques millisecondes, sans verrou de fichiers).
- Revue: auto-revue de l'auteur (non independante).

### E18b - 25 novembre 2026 (Claude Code, branche feat/e18b-v2-parity)
- Decoupage: E18 exige la parite de parcours ; 6 fonctions de l'interface actuelle manquaient dans la v2. Sur decision du proprietaire le 25/11, E18b (Claude, depend de E16 et E17, 3 j) les porte ; E18 garde lecteur d'ecran, captures et bascule. Total 36,5 j -> 39,5 j.
- Charge humaine estimee: 3 j (24 h). Execution IA mesuree (horloge, pas du temps humain): 20 h 23 -> 20:56 (0 h 33), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Livre: `ui/v2/answers.js` (brouillon sous la cle v1 `forge-my-project.draft.v1`, revalide par `/api/answers/validate` avant application, sauvegarde a la fermeture ; export/import JSON 64 Kio ; reinitialisation confirmee ; profils predefinis et personnels), `ui/v2/skills.js` (recherche, approbation apres examen, refus, verification), `ui/v2/protection.js` (commande preparee, jamais executee), architecture manuelle et suggestion des regles locales dans l'etape Projet, nouvelle etape « Skills externes », controles en ligne explicites (verify, skills) transmis a chaque requete suivante et retires a tout recalcul, rapport de verification ou contrats d'API, archive ZIP apres validation. Aucun endpoint modifie.
- Tests: `tests/test_e2e_parity_firefox.py` (7, Firefox reel, faux GitHub, protection de branche simulee) ; `tests/test_journey_v2.py` (endpoints par composant, brouillon limite a sa cle, lien d'examen GitHub seul autorise, ordre de chargement) ; tests v2 existants adaptes (7 etapes, brouillon efface entre tests, profils au montage). 10 mutations injectees : 9 detectees, la 10e etait une ligne redondante, retiree. Suite locale 500 OK (59 ignores sans E2E). Firefox local : 48/52 ; les 4 echecs (2 v1 inchanges, 2 v2) sont l'ecriture locale refusee parce que le dossier temporaire est dans le depot (`/tmp` interdit sur ce poste) : a confirmer par la CI.
- Limites: verification en ligne `verify` (PyPI, npm, OSV, registre MCP) non rejouee en E2E (reseau) ; telechargements simules (blob intercepte) ; pas de lecteur d'ecran ; captures non approuvees.
- Fusion: PR #53 (a74294e) apres CI verte (8/8, dont les tests d'ecriture echoues en local) ; statuts suivis par une PR distincte.
- Revue: auto-revue de l'auteur (non independante).

### E17 - 25 novembre 2026 (Claude Code, branche feat/e17-shell-integration)
- Realisation: Claude seul (responsabilite partagee Codex + Claude ; Codex non intervenu). Nouveau fichier `ui/v2/filetabs.js` ; `shell.js`, `journey.*` adaptes ; contrats E17a inchanges (`editor.js`, `diagnostics.js`, `workflow.js` non modifies).
- Charge humaine estimee: 1 j (inchangee). Execution IA mesuree (horloge, pas du temps humain): 16 h 35 -> 16:46 (0 h 11), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Livre: panneaux `editor` et `diagnostics` de la coque (masquables par en-tete, rail et palette ; editeur masque : colonne diagnostics + validation pleine largeur ; separateur de l'atelier 280-640 px et 40 % de la fenetre, persistant) ; onglets des fichiers ouverts (modele ARIA tabs a activation explicite, Suppr et bouton « Fermer l'onglet », voisin actif et focus conserve, 8 onglets au plus, marque de modification, limites au plan courant) ; commandes onglet suivant/precedent, fermer, rechercher (`Ctrl+F` affiche, editeur rendu visible). La validation et l'ecriture restent toujours visibles.
- Tests: `tests/test_e2e_workbench_firefox.py` (5, Firefox reel) ; `tests/test_journey_v2.py` (onglets sans `fetch`, ordre de chargement) ; test de ruptures E15 adapte (3e separateur). 9 mutations injectees, toutes detectees. Firefox: 45 OK (12 + 6 + 7 + 7 + 8 + 5) ; suite locale 492 OK (52 ignores sans E2E).
- Limites: onglets non persistants (aucune donnee projet dans les preferences) ; pas de glisser-deposer d'onglet ; pas de lecteur d'ecran ; captures non approuvees.
- Fusion: PR #51 (037f64e) apres CI verte sur la PR (4/4 ; run push de la branche absent) ; statuts suivis par une PR distincte.
- Revue: auto-revue de l'auteur (non independante).

### E15 - 25 novembre 2026 (Claude Code, branche feat/e15-shell)
- Reattribution: E15 (Codex, non commencee) confiee a Claude par le proprietaire le 25/11 ; seule tache debloquant E17 et E18.
- Charge humaine estimee: 4 j (inchangee). Execution IA mesuree (horloge, pas du temps humain): 15 h 33 -> 16:00 (0 h 27), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Livre: coque integree a `/v2/parcours` (`ui/v2/shell.{js,css}`) : rail, panneaux `navigation`/`configuration`/`preview` masquables, deplacables (echange gauche/droite, ordre DOM = ordre visuel) et redimensionnables (separateurs `separator` au clavier et au pointeur, bornes), theme systeme/clair/sombre, densite confortable/compacte, onglets ARIA Plan/Resume de l'apercu (activation explicite), palette de commandes `Ctrl+K` (filtre insensible aux accents, commandes indisponibles absentes, focus piege puis rendu), « Reinitialiser la disposition ». Preferences `forge-my-project.ui.v2` versionnees, validees champ par champ, sans donnee projet. Aucun endpoint modifie, aucune requete de la coque.
- Tests: `tests/test_e2e_shell_firefox.py` (8, Firefox reel) ; `tests/test_journey_v2.py` (11 : coque sans `fetch`, stockage limite a sa cle, ordre de chargement). 9 mutations injectees, toutes detectees. Firefox: 40 OK (12 + 6 + 7 + 7 + 8) ; suite locale 487 OK (47 ignores sans E2E).
- Defaut trouve par la recette: le glisser d'un separateur s'arretait apres le premier deplacement (reinsertion DOM a chaque rendu, capture du pointeur perdue) ; corrige en ne reordonnant que si l'ordre change.
- Limites: raccourcis limites a `Ctrl+K` et Echap (Ctrl+Shift+P, Ctrl+1..8 et F6 reserves par Firefox) ; deplacement par echange de cotes, pas de glisser-deposer de panneau ; panneaux `editor` et `diagnostics` hors coque jusqu'a E17 ; pas de lecteur d'ecran ; captures non approuvees.
- Fusion: PR #49 (1970629) apres CI verte (8/8) ; statuts suivis par une PR distincte.
- Revue: auto-revue de l'auteur (non independante).

### E18a - 22 novembre 2026 (Claude Code, branche feat/e18a-progressive-acceptance)
- Decoupage: E18 dependait de E15 et E17 (non commencees). Sur decision du proprietaire, E18a (Claude, depend de E16 et E17a, 2 j) recette ce qui existe sans bascule; E18 (1 j) garde la recette de la coque, la parite et la bascule. Total inchange (36,5 j). E17a passe DONE (PR #44, 67a55de).
- Charge humaine estimee: 2 j (16 h). Execution IA mesuree (horloge, pas du temps humain): 18 h 53 -> 19:11 (0 h 18), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Livre: `tests/test_e2e_acceptance_firefox.py` (clavier seul jusqu'a l'ecriture sur disque, focus visible et ordre par zones sans piege, resolutions 360 a 1920 px et ruptures, cibles 36/44 px, contrastes du rendu reel dans les deux themes, budgets mesures, aucune erreur JS ni ressource bloquee, captures) ; session 360 px par zoom navigateur en theme sombre systeme; rapport `docs/E18A_ACCEPTANCE.md`; marques `performance` dans le parcours.
- Defauts trouves par la recette puis corriges: logo bloque par la CSP depuis E16 (SVG inline, CSP inchangee), contraste 2,03:1 en sombre, barres de defilement claires en sombre, champ masque par la barre collante a 360 px, cibles 32 px, editeur hors budget sur 2 000 lignes (143/145 ms -> 56/30 ms). Chaque defaut a d'abord fait echouer la recette.
- Tests: Firefox 32 OK (12 + 6 + 7 + 7), suite unitaire OK; `tests/test_journey_v2.py` + interdiction d'image externe.
- Limites: 360 px par zoom (pas un vrai telephone); pas de lecteur d'ecran; machine de reference des budgets non fixee; `window.confirm` simule dans le parcours clavier; captures en attente d'approbation; aucune bascule (E18).
- Fusion: PR #45 (9bc72d6) apres deux correctifs CI (session 360 px refusee par geckodriver 0.37 / Firefox 160 : acces chrome passe a geckodriver via `--allow-system-access`, sessions par defaut inchangees). Temps de ces correctifs non mesure, non inclus dans les 0 h 18. Captures publiees pour approbation, decision du proprietaire en attente.
- Revue: auto-revue de l'auteur (non independante).

### E17a - 22 novembre 2026 (Claude Code, branche feat/e17a-editor-diagnostics)
- Decoupage: E17 dependait de E15 (Codex, non commencee) et `tests/test_release_policy.py` interdit de la demarrer avant. Sur decision du proprietaire, E17 est decoupee: E17a (Claude, depend de E16) livre les composants dans `/v2/parcours`; E17 (1 j, depend de E15) les integre a la coque. Le controle de dependances est etendu aux sous-lots (memes regles, plus: un sous-lot ne depend pas de sa parente, une parente n'est pas DONE avant ses sous-lots); 4 mutations injectees, toutes detectees.
- Charge humaine estimee: 2 j (16 h) sur les 3 j de E17 (total inchange 36,5 j). Execution IA mesuree (horloge, pas du temps humain): 18 h 12 -> 18:33 (0 h 21), attente CI non comptee. Temps humain reel: non renseigne. Ecart humain: non calculable.
- Livre: `ui/v2/editor.js` (textarea natif sous couche coloree sans HTML injecte, numeros de ligne, ligne/colonne/langage, recherche Ctrl+F avec casse, suivante/precedente, remplacer/tout remplacer, retablir le fichier genere; coloration Python, Shell, TOML, YAML, JSON, Markdown, code C-like, Dockerfile, desactivee au-dela de 200 000 caracteres); `ui/v2/diagnostics.js` (filtres par gravite et texte, compteurs, navigation « Aller a » deduite du code et du sujet serveur, aucun lien invente); `ui/v2/workflow.js` (validation `/api/files/validate`, parcours de destination, comparaison, diff et decisions keep/replace/auto/merge, confirmation NON VERIFIE par jeton et blocage critique, confirmation d'ecriture, rapport et journal). Editions conservees par fichier, marquees dans l'arbre, retirees avec message si le rendu genere change; toute modification perime validation et comparaison. Aucun endpoint modifie; interface actuelle inchangee.
- Tests: `tests/test_journey_v2.py` (9: + chaque composant n'appelle que ses endpoints, routes reelles, champs du contrat d'ecriture, ordre de chargement); `tests/test_e2e_editor_firefox.py` (7, Firefox reel: coloration/numeros/alignement des couches, Ctrl+F reel, recherche/casse/remplacement/retablissement, filtres et navigation vers le champ, cibles de navigation sur diagnostics injectes, validation -> comparaison -> ecriture puis conflit conserve sur disque, peremption apres edition ou changement de configuration, confirmation NON VERIFIE et blocage hardened); test E16 adapte (`#content` devient le textarea). Suite locale: 461 tests OK (32 ignores sans E2E); Firefox: 25 OK (12 + 6 + 7).
- Limites: pas de coque E15 (panneaux, onglets, palette: E17); annulation native perdue apres un remplacement (le bouton « Retablir » reste disponible); coloration par expressions regulieres, sans analyse syntaxique; une edition est perdue si le rendu genere du fichier change (signale); pas d'archive, profils, skills ni verification en ligne dans la v2; panneau diagnostics en region `status` (les refus de configuration restent en `alert`); 360 px a valider en E18; captures non approuvees.
- Revue: auto-revue de l'auteur (non independante).

Les priorites et les criteres d'acceptation propres a chaque ligne sont maintenus dans [docs/ROADMAP_2026.md](docs/ROADMAP_2026.md); cette reference fait partie du contrat de la tache, pas d'un critere generique. Charge totale estimee: **36,5 j**. Regle de suivi (E01-E18) : la charge humaine estimee est en jours (1 j = 8 h de travail humain). L'execution IA mesuree est le temps horloge d'une session d'agent, releve manuellement a partir des heures de debut et de fin ; elle n'est jamais convertie en charge humaine. Le temps humain reel n'est renseigne que s'il est connu du proprietaire. L'ecart humain (temps humain reel ou charge reestimee moins charge estimee) n'est calcule que lorsque ces donnees existent ; sinon `non calculable`. Toute PR renseigne preuve CI, revue, tests et limites. Ne pas marquer DONE avant verification.

### E04 - 16 novembre 2026

- PR #25: scripts Linux sans privilege, paquet ni acces reseau, reutilisant `start.py` de la PR #20.
- Tests locaux initiaux: 250 PASS, 12 SKIP; tests E04 cibles 14 PASS; syntaxe shell et compilation Python PASS.
- CI initiale avant synchronisation: six checks PASS (push et pull request); revue independante APPROVED sans constat P0-P2.
- Temps: charge humaine estimee 8 h; temps humain reel inconnu et non invente; temps d'execution IA de la reprise mesure ci-dessous. L'ecart humain reste non calculable.
- Limites: ShellCheck non execute car absent; Ubuntu valide par CI, autres distributions Linux non executees dans cette mission.
- Reprise du 17 novembre 2026: conflit avec `main` resolu sans rebase; recherche Python dans `$HOME/.local/bin` restauree apres revue; 15 tests cibles PASS, suite complete 271 PASS et 12 ignores; revue independante du SHA `d30c2f3` APPROVED.
- Temps d'execution IA mesure cumule pour les reprises: 0 h 19. Temps humain reel toujours inconnu; ecart humain non calculable.
- Validation finale du 18 novembre 2026 au SHA `3f3be42`: 33 tests cibles et 289 tests complets PASS, 12 E2E Firefox ignores; syntaxe shell, compilation Python et attribution conformes; revue independante APPROVED sans constat P0-P3; CI push et pull request 8/8 verte.
- Blocage CI historique resolu par la PR #30: l'exception fail-closed reste limitee a GHSA-fc5q-39xc-vjpf, au paquet `picomatch` et au 17 decembre 2026; tout autre avis, paquet, rapport invalide ou exception expiree bloque.

## Idees hors suivi actif

- Extension VS Code: [long-terme-ideas-project-liste.md](long-terme-ideas-project-liste.md), LT01-01 a LT01-08, estimation initiale 24 j. Ne pas lancer sans decision explicite.
