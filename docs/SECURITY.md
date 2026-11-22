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

### Registre des exceptions d'audit des projets generes

Source unique : `catalogs/security/tools.json`, cle `npm_audit_exceptions`. Chaque exception vise un avis GHSA et un paquet exacts, porte une justification et expire au plus 90 jours apres son ajout (valide au chargement du catalogue). Les projets Node generes l'appliquent par `scripts/security/npm_audit_gate.py`, appele seulement si `npm audit` echoue. Tout autre avis, une exception expiree ou un rapport illisible restent bloquants, et l'exception est affichee dans leur SECURITY.md.

| Avis | Paquet | Ajout | Expiration | Justification |
| --- | --- | --- | --- | --- |
| GHSA-fc5q-39xc-vjpf (ReDoS, high) | picomatch <= 4.0.7 | 2026-11-17 | 2026-12-17 | aucune version corrigee publiee (4.0.7 est la derniere) ; dependance de developpement transitive (eslint, vite, vitest) des profils TypeScript ; a retirer des qu'une version corrigee existe |

A l'expiration, la CI redevient rouge : verifier l'avis, puis retirer l'exception (version corrigee disponible) ou la renouveler par une PR justifiee.

## Controles NON VERIFIE (E06)
- Un controle impossible a etablir reste NON VERIFIE. Une confirmation ne le transforme jamais en PASS, ni dans l'interface ni dans le journal.
- Au niveau hardened, les controles de securite (vulnerabilites, outils de securite, actions epinglees, serveurs MCP) doivent reussir. NON VERIFIE ou verification en ligne absente bloquent l'archive et l'ecriture.
- La confirmation est verifiee par le serveur, jamais par le seul navigateur. Elle est liee a la configuration et aux controles exacts, et elle est perimee au redemarrage ou a tout changement.
- Seuils inchanges : npm audit `high` ou `moderate`, Bandit `medium` ou `low`. L'exception datee GHSA-fc5q-39xc-vjpf (picomatch, 2026-12-17) n'est ni elargie ni confirmable autrement.

## Verification statique des API (E11)
- Les archives npm et les roues PyPI sont telechargees seulement si une verification en ligne est demandee, depuis des hotes en liste fermee (`registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`), avec une limite de 20 Mo.
- Chaque archive est verifiee par l'integrite SHA-512 publiee par npm, ou par le SHA-256 publie par PyPI. Une archive non confirmee donne NON VERIFIE, jamais PASS.
- Les archives sont lues en memoire comme du texte : jamais extraites sur disque, jamais installees ni executees. La lecture est bornee a 5 000 entrees.

## Bases de fusion (E07)
- Le dossier d'etat local (0700, fichiers 0600) contient le contenu genere ecrit dans chaque destination, y compris les editions faites dans l'apercu. Ce sont des donnees locales de l'utilisateur, jamais transmises.
- Une base n'est utilisee que si son empreinte SHA-256 et sa destination concordent. Le jeton de comparaison couvre les bases : une base changee entre la comparaison et l'ecriture rend la validation perimee (409).
- Une fusion automatique ne peut ni introduire de secret ni modifier un fichier protege : memes controles que la fusion manuelle.

## Donnees locales du questionnaire (T05)
- Brouillon: `localStorage` du navigateur (cle `forge-my-project.draft.v1`), revalide par le serveur avant restauration; un brouillon incompatible est supprime, jamais applique.
- Profils personnels: `$FORGE_PROFILES_FILE`, sinon `$XDG_CONFIG_HOME/forge-my-project/profiles.json`, sinon `~/.config/forge-my-project/profiles.json`; dossier 0700, fichier 0600, ecriture atomique, liens symboliques et fichiers illisibles refuses sans ecrasement. Aucun nom ni description de projet n'y est stocke.
- Import JSON: 64 Kio maximum, `JSON.parse` uniquement, validation serveur integrale avant application; affichage par `textContent`.
- Ne pas stocker de secret dans les reponses: elles sont enregistrees en clair.

## Skills externes (T10)
- Aucun skill externe n'est copie sans approbation explicite dans l'interface (confirmation supplementaire pour une source non reconnue).
- L'approbation epingle depot, commit et empreinte SHA-256 de l'arborescence du skill ; tout changement depuis l'approbation est une erreur bloquante, et chaque fichier telecharge est compare au SHA de son blob Git.
- Seuls des fichiers texte (.md, .yaml, .yml, .json, .txt) sont copies ; scripts, binaires, liens et executables sont ignores, jamais telecharges ni executes.
- Les approbations importees (JSON, profil, brouillon) sont revalidees par le serveur et peuvent etre controlees en ligne avant generation.
- E13 : piles Rust, Go et Java sans outil d'audit des dependances ni regles SAST : controle NON VERIFIE (`security-stack-unverified`) a confirmer en strict, bloquant en hardened. Gitleaks et Semgrep restent actifs.
- E13 : le catalogue personnel (technologies, regles, templates) est lu comme une donnee bornee (16 fichiers JSON de 64 Kio par dossier, 32 technologies, 32 regles, 32 templates de 64 Kio), sans lien symbolique ; il ne peut ni remplacer un element de Forge ni utiliser `override`. Ses commandes ne sont jamais executees par Forge ; elles sont ecrites dans la CI et les hooks generes et signalees (`local-technology`, `local-rule`).
- E12 : le cache de recherche ne contient que des candidats (dossier d'etat 0700, fichiers 0600, entree invalide ignoree) ; il ne peut rien faire copier, car la copie relit toujours GitHub au commit approuve et controle l'empreinte. Avant copie, la branche suivie est relue : un skill modifie ou retire en amont depuis l'approbation est signale, et seule la version approuvee est copiee.

## Serveurs MCP des projets generes (T15)
- Aucun serveur sans selection explicite ; uniquement des serveurs du catalogue verifie et pertinents pour la configuration.
- Aucun secret genere : references a des variables d'environnement uniquement ; lecture seule et ensembles d'outils limites pour GitHub ; version epinglee et profil isole pour Playwright.
- Provenance controlee dans le registre MCP officiel (actif, depot, transport) lors de la verification en ligne ; un ecart bloque la generation.

## Controles de ce depot (T13)
- Job CI `security`: Gitleaks sur tout l'historique et Bandit (severite >= medium) sur forge/, server.py et generator.py, avec les memes versions epinglees que les projets generes (alignement verifie par tests/test_repo_ci.py).
- Job CI `generated-projects`: CI generee des profils predefinis executee, puis preuve de detection des controles de securite (tests/smoke_security.py).
- E10 : Semgrep 1.184.0 (PyPI officiel, publie le 2026-11-05, sans vulnerabilite OSV le 2026-11-22) analyse le depot avec les regles locales `.semgrep/forge.yml`, sans regle telechargee ni telemetrie. La passerelle `scripts/semgrep_gate.py` bloque les resultats ERROR et refuse un rapport illisible, une analyse incomplete ou sans fichier analyse. `tests/test_semgrep_rules.py` prouve dans le job `security`, avec le vrai Semgrep, que chaque regle detecte du code reellement vulnerable. Forge n'a pas d'image conteneur : aucune analyse d'image n'est faite pour ce depot.

## Semgrep et images des projets generes (E10)
- **Semgrep** dans tous les projets generes, apres Bandit, Gitleaks, pip-audit et npm audit, qui sont conserves.
  - Regles locales `.semgrep/forge.yml`, revues et versionnees : `eval`/`exec`, shell, deserialisation non sure, `yaml.load`, TLS desactive, `mktemp`, `child_process`, `dangerouslySetInnerHTML`, `innerHTML`.
  - Seuils : ERROR bloque en `strict` ; ERROR et WARNING bloquent en `hardened`.
  - Exception seulement par `# nosemgrep: <id>`, justifiee dans la PR.
- **Image conteneur**, uniquement pour un projet qui a choisi Docker. Forge ne genere pas de Dockerfile.
  - Des qu'un `Dockerfile` existe, le job `security` construit l'image et l'analyse avec Trivy 0.76.2 : release officielle `aquasecurity/trivy`, empreinte SHA-256 verifiee avec `sha256sum --check --strict`, base de vulnerabilites telechargee par Trivy depuis ses sources officielles.
  - La passerelle `scripts/security/image_scan_gate.py` bloque toute vulnerabilite `high` ou `critical` en `strict`, et des `medium` en `hardened`, corrigee ou non (pas d'`--ignore-unfixed`).
  - Un rapport illisible, vide ou d'un autre format est refuse ; un scanner indisponible (telechargement ou empreinte en echec) fait echouer l'etape.
  - Sans Dockerfile : avertissement CI et ligne SECURITY.md `NON VERIFIE`, jamais PASS ; le diagnostic `security-image-unverified` reste a confirmer (E06).
- Seuils existants inchanges : npm audit `high` ou `moderate`, Bandit `medium` ou `low`. L'exception picomatch (GHSA-fc5q-39xc-vjpf, 2026-12-17) n'est pas elargie. Le catalogue refuse tout assouplissement des seuils Semgrep et image.
- La verification en ligne controle Semgrep (PyPI et OSV) et, pour les projets Docker, l'archive Trivy (release et empreinte).


## Ecriture locale (T17)
- Destination limitee aux sous-dossiers de `FORGE_WRITE_ROOT` (sinon le dossier personnel), hors dossier de Forge-my-Project; chemins absolus normalises uniquement; chaque composant ouvert par descripteur avec O_NOFOLLOW (liens symboliques refuses, y compris s'ils apparaissent apres la verification).
- Aucune ecriture sans comparaison, decision explicite pour chaque conflit et confirmation; jeton HMAC (cle propre au processus) liant destination, contenus et etat des cibles : toute validation perimee est refusee.
- Sauvegarde des fichiers remplaces avant modification (`.forge-backup/`, 0600), ecriture atomique, reverification de chaque cible, rollback automatique sur echec.
- Contenu edite ou fusionne : motifs de secrets bloquants, configurations MCP et hooks d'agents figees (mise en forme seule), scripts de hooks non modifiables, nom de skill conserve, chemins sensibles interdits. Aucun fichier ecrit n'est execute.
