# Politique de maintenance

Produit personnel, Linux uniquement, un proprietaire seul contributeur Git. Cette politique s'appuie sur les controles existants (CI, hooks, catalogues epingles) et ne cree aucun automatisme supplementaire. Le plan des versions est dans [RELEASES.md](RELEASES.md) et l'historique dans [../CHANGELOG.md](../CHANGELOG.md).

## 1. Anomalies

**Ou** : une issue GitHub par anomalie, avec le label `bug` et la priorite en tete du titre (`[P1] ...`). Sans issue, aucune correction n'est planifiee. Une anomalie trouvee pendant une tache est notee dans la PR, puis reportee en issue si elle n'est pas corrigee dans la PR.

**Contenu minimal** : version ou commit, commande ou parcours exact, resultat attendu, resultat obtenu, preuve (sortie, capture, run CI). Une anomalie non reproduite reste `NON VERIFIE` et n'est jamais classee P0.

| Priorite | Definition | Exemples | Traitement |
| --- | --- | --- | --- |
| P0 bloquante | perte ou ecrasement de donnees utilisateur, ecriture hors de la racine autorisee, secret expose, attribution Git a un agent IA, CI de main rouge | rollback d'ecriture incomplet, chemin non revalide | toute autre tache s'arrete ; correctif ou retour arriere avant toute fusion ; release impossible |
| P1 majeure | fonction documentee cassee sans contournement, controle de securite inoperant, projet genere qui ne passe pas sa propre CI | profil genere rouge, hook genere qui n'echoue pas | traitee dans la prochaine PR ; release impossible tant qu'elle est ouverte |
| P2 normale | fonction degradee avec contournement, documentation fausse | message d'erreur trompeur | planifiee dans TODO.md ; peut etre livree comme limite connue |
| P3 mineure | confort, presentation | libelle, alignement | regroupee avec une tache proche |

Une anomalie est **fermee** seulement avec un test qui echouait avant la correction et passe apres, une CI verte et le lien de la PR. `wontfix` ou `invalid` exigent une justification ecrite dans l'issue.

## 2. Controles reguliers

| Frequence | Controle | Commande ou source | Sortie attendue |
| --- | --- | --- | --- |
| Chaque push et PR (automatique, existant) | tests, E2E Firefox, 6 profils generes executes, secrets (Gitleaks, historique complet), SAST (Bandit), attribution Git | `.github/workflows/ci.yml` | 4 jobs verts |
| Mensuel, et avant chaque release | verification en ligne des versions et des actions epinglees | `python3 tests/smoke_generated.py --verify` | 6/6 profils PASS ; sinon PR de mise a jour |
| Mensuel | audit d'attribution de toutes les refs | `python3 scripts/attribution_guard.py audit` | aucune attribution interdite |
| Mensuel | dependances et epinglages (section 3) | catalogues `verified_at` | dates de moins de 90 jours |
| Avant chaque expiration d'exception d'audit | avis toujours sans correctif ? | registre de docs/SECURITY.md | exception retiree ou renouvelee par PR |
| Apres chaque fusion | worktrees secondaires propres et integres (simulation, puis execution sur accord du proprietaire) | `python3 scripts/worktree_cleanup.py` puis `--apply` | worktrees sales, verrouilles, actifs ou non integres conserves avec leur motif |
| A chaque avis de securite visant un outil epingle | remplacement de la version, de l'empreinte et des SHA d'actions | PR dediee `fix(security): ...` | CI verte avec la nouvelle version |

Un controle regulier non execute est note `NON VERIFIE` dans la PR ou la release concernee ; il n'est jamais presente comme reussi. Le resultat de chaque controle mensuel est consigne en une ligne dans TODO.md (date, commande, resultat).

## 3. Dependances

- **Forge-my-Project** n'a aucune dependance d'execution (bibliotheque standard Python 3.11+). Toute nouvelle dependance demande une verification du registre officiel (nom, version, licence, vulnerabilites) et une PR dediee.
- **Outils de CI epingles** : Gitleaks (version et empreinte SHA-256) et Bandit dans `catalogs/security/tools.json`, actions GitHub par SHA complet dans `catalogs/ci/actions.json`. `tests/test_repo_ci.py` verifie que le workflow utilise exactement ces valeurs.
- **Versions proposees aux projets generes** : catalogues `catalogs/technologies/*.json`, controles par la verification en ligne.
- **Revue d'une mise a jour** : changelog amont, compatibilite, empreinte, CI verte, entree `Securite` ou `Modifie` dans CHANGELOG.md. Pas de mise a jour groupee : un outil ou une famille par PR.
- Un epinglage verifie depuis plus de 90 jours est revu au controle mensuel suivant.
- **Avis sans version corrigee** : seule une exception datee et ciblee est admise (un avis GHSA, un paquet, une justification, 90 jours au plus), inscrite dans `catalogs/security/tools.json` et le registre de docs/SECURITY.md, sur decision du proprietaire. A son expiration la CI redevient rouge : retirer l'exception ou la renouveler par une PR justifiee.

## 4. Correction d'une regression

1. Ouvrir l'issue (section 1) et identifier le dernier commit sain (`git bisect` si necessaire).
2. Si la regression est P0 sur main : revenir d'abord en arriere (section 7), corriger ensuite.
3. Ecrire le test qui reproduit la regression et constater son echec.
4. Corriger au plus pres de la cause, dans une branche dediee (sans worktree par defaut, voir AGENTS.md), puis faire une PR `fix(<portee>): ...` qui lie l'issue.
5. Joindre la sortie du test avant et apres, et la CI verte. Ajouter une entree `Corrige` dans CHANGELOG.md.
6. Noter la cause et le test de non-regression dans TODO.md si la regression vient d'une tache E.

Interdits : desactiver, ignorer ou affaiblir un test pour obtenir une CI verte ; corriger sans test qui echoue d'abord.

## 5. Versions et changelog

- **SemVer** `MAJEUR.MINEUR.CORRECTIF` : MAJEUR pour un changement incompatible (format des profils, contrat API locale, structure des projets generes), MINEUR pour une fonction compatible, CORRECTIF pour une correction sans nouvelle fonction.
- **Source de verite** : le tag Git annote `vX.Y.Z` sur un commit de main, et la section correspondante de CHANGELOG.md. Le code ne porte pas de numero de version.
- **CHANGELOG.md** au format Keep a Changelog : section `[Unreleased]` en tete, puis `## [X.Y.Z] - AAAA-MM-JJ`, en ordre decroissant. Rubriques : Ajoute, Modifie, Deprecie, Supprime, Corrige, Securite. Chaque PR qui change un comportement visible ajoute sa ligne dans `[Unreleased]`.
- `tests/test_release_policy.py` (job CI `python`) verifie le format du changelog, l'absence de version datee dans le futur, la coherence des statuts entre TODO.md et ROADMAP_2026.md, et que la liste de controle des releases cite les vrais jobs CI.

## 6. Conditions d'une release

Une release n'est publiee que par le proprietaire, et seulement si chaque point est prouve :

1. Tous les criteres du jalon dans RELEASES.md sont satisfaits, avec le lien de chaque PR.
2. Les 4 jobs CI sont verts sur le commit de main a etiqueter : `python`, `CI generee des profils predefinis`, `Securite du depot (secrets, SAST)`, `Attribution Git (aucun agent IA auteur, committer ou co-auteur)`.
3. `python3 tests/smoke_generated.py --verify` reussit le jour de la release.
4. `python3 scripts/attribution_guard.py audit` ne signale rien.
5. Aucune issue P0 ou P1 ouverte.
6. La section `[X.Y.Z]` de CHANGELOG.md est datee, et les limites connues y sont ecrites.
7. Installation et demarrage Linux verifies depuis un clone propre, avec les scripts livres par E04.

Publication : `git tag -a vX.Y.Z -m "vX.Y.Z" <commit>` puis `git push origin vX.Y.Z`, et une release GitHub dont le texte reprend la section du changelog. Un tag publie n'est jamais deplace ni supprime : une erreur se corrige par une version CORRECTIF.

## 7. Retour arriere

- **Fusion fautive sur main** : `git revert -m 1 <commit de fusion>` dans une branche dediee, puis une PR et une CI verte. Jamais de reset ni de push force sur main.
- **Release fautive** : annoncer la version dans CHANGELOG.md (rubrique Corrige de la version suivante), publier une version CORRECTIF ; en attendant, l'utilisateur revient a la version precedente avec `git checkout vX.Y.(Z-1)` dans son clone.
- **Ecriture locale d'un projet genere** : les sauvegardes `.forge-backup/` et le rollback d'ecriture existants (docs/LOCAL_WRITE.md) restent la procedure ; toute anomalie du rollback est P0.
- Chaque retour arriere est trace par une issue, avec la cause et le test qui l'aurait evite.
