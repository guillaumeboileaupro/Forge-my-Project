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
| Q01 | A | Linux uniquement, sans promesse Windows/macOS | E04, v1.0.0 | TODO |
| Q02 | B, recadree Linux | Ecriture directe dans les dossiers Linux; ne pas developper Windows | E04, E07 | TODO |
| Q03 | A + B | GitHub Actions et tests manuels Linux | E05, E18 | PARTIEL (E05: controles reguliers definis dans docs/MAINTENANCE.md; recette manuelle E18 a faire) |
| Q04 | B | `installer.sh` et `start.sh`; examiner la PR existante de `start.py` avant doublon | E04 | TODO |
| Q05 | Reportee | MCP GitHub authentifie NON VERIFIE; conserver dans les pistes futures sans PR maintenant | Backlog long terme | REPORTE |
| Q06 | A puis B puis C | Maintenir GitHub/Playwright, puis MCP officiels, enfin recherche libre verifiee | Backlog MCP progressif | FUTUR |
| Q07 | Tout (A+B+C+D) | Maintenir les scans existants, ajouter analyse Docker et Semgrep, bloquer sev. haute/critique | E10 | TODO |
| Q08 | B | Expliquer et faire confirmer explicitement chaque NON VERIFIE, trace et revalidation | E06 | IN PROGRESS (E06, PR #31) |
| Q09 | B | Fusion trois voies seulement avec base fiable; garder diff, fusion manuelle et rollback | E07, v1.1.0 | TODO |
| Q10 | A + B | TESTING.md et infrastructure E2E cible prete a completer sans tests metier inventes | E08, v1.1.0 | TODO |
| Q11 | B | Assistant qui prepare les commandes de protection GitHub, sans les executer | E09, v1.1.0 | TODO |
| Q12 | B avec PR courtes | Agents et PR en parallele; taches petites, CI verte et fusion rapide | E05, AGENTS.md | TODO |
| Q13 | C (correction de A) | Archiver inventaire noms/SHA des branches docs/* avant suppression sur preuve de fusion | E01 | DONE |
| Q14 | A | Supprimer codex/file-preview apres verification d'integration et absence de travail local | E01 | PARTIEL (E01: branche distante supprimee; branche locale et worktree Codex conserves) |
| Q15 | C | Nettoyage automatise worktrees apres fusion, mode simulation, refus si sale ou actif | E01 | TODO (non construit: E01 a nettoye manuellement, sans outil automatise) |
| Q16 | B | Audit fichiers obsoletes, temporaires, doublons, configurations; suppression seulement sur preuve | E03 | DONE (PR #28 fusionnee; aucun fichier suivi inutile demontre) |
| Q17 | B | Verifier statiquement APIs Python, JS/TS quand possible, afficher PASS/FAIL/NON VERIFIE | E11 | TODO |
| Q18 | C | Skills: cache expire, recherches paralleles, classement et reverification avant copie | E12 | TODO |
| Q19 | B + C, usage personnel | Stacks Python/JS/Rust/Go/Java et catalogue/regles personnels editables localement | E13 | TODO |
| Q20 | A | Temps manuels uniquement; conserver estime/reel/ecart sans chronometre ni mesure Git | Toutes E, pas de fonctionnalite nouvelle | REGLE |
| Q21 | B puis C puis D | Trois releases: v1.0.0 nettoyage; v1.1.0 PARTIEL; v2.0.0 ameliorations+refonte | E05, E07-E09, E18 | TODO (plan pret: docs/RELEASES.md; aucune release publiee) |
| Q22 | C | Codex et Claude en parallele, composants et worktrees distincts | E05, E14-E18 | REGLE |
| Q23 | B + C | Releases, bugs, mises a jour securite, controles reguliers dependances et regression | E05 | DONE (E05, PR #29: docs/MAINTENANCE.md, docs/RELEASES.md, CHANGELOG.md) |
| Q24 | A+B+C+D | Plan detaille, missions agents, petites PR progressives et execution avec tests/CI | E05 + plan | REGLE |

### 10 decisions de refonte UI - remplacement complet, pas un relooking

| Question | Reponse validee | Decision et critere verifiable | Taches | Etat |
| --- | --- | --- | --- | --- |
| UI-01 | A+B | Interface de type VS Code ET design moderne; repartir de zero sur l'UI en gardant le moteur | E14, E15 | TODO |
| UI-02 | A | Panneaux gauche/centre/droite deplacables, masquables, redimensionnables et persistants | E15 | TODO |
| UI-03 | A+D | Minimalisme pro, themes sombre/clair, couleurs, densites et accessibilite | E14, E15, E18 | TODO |
| UI-04 | D | Barre laterale permanente, onglets, palette Ctrl+Shift+P, raccourcis | E15 | TODO |
| UI-05 | A+C | Questionnaire progressif et conditionnel avec barre de progression et apercu interactif | E16 | TODO |
| UI-06 | C | Arborescence et diagramme d'architecture interactifs, synchronises dans les deux sens | E16 | TODO |
| UI-07 | B | Panneau diagnostics central, gravites, filtres, clic vers le champ concerne | E17 | TODO |
| UI-08 | A | Editeur leger avec coloration syntaxique, numeros, recherche/remplacement; diff T17 conserve | E17 | TODO |
| UI-09 | C | Codex et Claude developpent en parallele par composants, design system commun, petites PR | E14-E18 | REGLE |
| UI-10 | C+D | Tests visuels+fonctionnels progressifs, Firefox, accessibilite, performance, resolutions; ancien UI garde jusqu'a validation | E18 | TODO |

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
| E06 | Confirmation explicite pour controles NON VERIFIE, journalisation et revalidation avant ecriture | Claude | - | 1 j | 0 h 17 (Claude) | non renseigne | non calculable | IN PROGRESS | PR #31 (DONE a sa fusion); docs/ENGINE.md section E06 |
| E07 | Fusion automatique a trois voies quand une base fiable existe, sinon resolution manuelle, sauvegarde et rollback | Codex | - | 2 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E08 | Infrastructure E2E des projets generes, adaptee a la stack, sans scenarios metier inventes | Claude | - | 2 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E09 | Assistant de protection de branche GitHub: preparer les commandes, ne pas appliquer automatiquement | Claude | - | 1 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E10 | Scanner d'images Docker et SAST complementaire dont Semgrep, sans retrait des controles actuels | Claude | - | 2 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E11 | Verification statique des API Python/JS/TS lorsque possible; PASS/FAIL/NON VERIFIE | Claude | - | 2 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E12 | Recherche des skills: cache expire, parallelisme, classement, reverification avant copie | Claude | - | 2 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E13 | Enrichir les stacks Python/JS/Rust/Go/Java et permettre les catalogues/regles personnalises localement | Claude | - | 4 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E14 | Definir le design system et les contrats de la nouvelle UI avant de coder | Codex + Claude | - | 2 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E15 | Nouvelle coque UI: look professionnel minimal, themes clair/sombre, densite, panneaux deplacables et redimensionnables, onglets, navigation, palette | Codex | E14 | 4 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E16 | Parcours questionnaire progressif et conditionnel avec apercu dynamique, arbre et diagramme synchronises | Claude | E14 | 4 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E17 | Editeur leger coloration/lignes/recherche/remplacement, panneau diagnostics et integration des flux securises existants | Codex + Claude (fichiers separes) | E15,E16 | 3 j | - | - | - | TODO | Voir ROADMAP_2026.md |
| E18 | Validation visuelle et fonctionnelle progressive, accessibilite, performances, resolutions, recette globale; migration finale apres validation | Codex + Claude | E15,E16,E17 | 3 j | - | - | - | TODO | Voir ROADMAP_2026.md |

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
