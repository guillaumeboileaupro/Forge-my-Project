# Plan de developpement - Forge-my-Project

## Objectif
Un questionnaire interactif produit un projet pret a developper: arborescence, code de base fonctionnel, AGENTS.md, skills adaptes, architecture, conventions, hooks, MCP verifies, dependances reelles, tests, securite, CI/CD et documentation. Chaque choix doit avoir un impact explicite sur les fichiers produits.

## Architecture cible
Formulaire -> SchemaConfig versionne -> Validation -> ProjectPlan -> Catalogue de templates -> Verification packages/MCP -> Generation deterministe -> Verification technique/securite -> Apercu -> ZIP ou publication GitHub explicite.

Modules envisages (a creer progressivement, sans refactor massif):
- ui: questionnaire conditionnel, sauvegarde/import, recapitulatif.
- core/config: schema, validation, profils.
- core/planner: compatibilites et composition du plan.
- templates: manifestes de stacks et renderers.
- verification: existence des packages, version, documentation des imports et API, licences, advisories.
- agents: AGENTS.md, skills, conventions et hooks suivant la stack.
- integrations: MCP verifiables, GitHub, CI/CD, Docker/cloud.
- audit: tests des archives, SAST/SCA/secrets, rapports PASS/FAIL/NON VERIFIE.

## Phases et objectifs testables
| ID | Travaux | Charge indicative | Condition de sortie |
| --- | --- | ---: | --- |
| P1 | Stabiliser MVP, tests HTTP/ZIP, corriger JS/TS, CI du depot | 1-2 j | CI verte et deux squelettes executes |
| P2 | Schema versionne, formulaire dynamique, choix conditionnels, import/export | 2-4 j | Configurations valides et invalides testees |
| P3 | Planificateur, catalogue de templates, architecture/code/documentation | 3-6 j | Arbres generes reproductibles; smoke tests |
| P4 | Verification PyPI/npm, modules/API, versions/licences, lockfiles, avis securite | 3-6 j | Faux packages rejetes; evidences tracees |
| P5 | AGENTS.md riche, skills, hooks pre-commit/pre-push, choix agents et MCP | 3-5 j | Fichiers adaptes et config MCP sans secrets |
| P6 | CI/CD generees executables, SAST/SCA/secrets/SBOM, controles bloquants | 3-6 j | Pipelines verts et cas d'echec detectes |
| P7 | Apercu/diff, export GitHub sur confirmation, profils Docker/S3NS/OUTSCALE | 2-5 j | Publication testee; cloud non verifie signale |
| P8 | Recette globale, docs, correction des defauts, version candidate | 2-4 j | Toutes les portes de sortie satisfaites |
| **Total** | **Estimation de travail, non delai garanti** | **19-38 j** | |

## Regles de travail
- Une seule PR ouverte et un seul agent de developpement a la fois.
- Une phase peut etre realisee en plusieurs PR successives, jamais paralleles.
- Ne jamais inventer packages, modules, actions GitHub ou serveurs MCP. Exiger preuves officielles.
- Ne pas affirmer que la securite est garantie; une verification non executee vaut NON VERIFIE.
- A chaque PR: objectif, fichiers touches, tests reellement executes, limite, impact securite et mise a jour du TODO.
- Un profil ne peut etre affiche comme supporte que si la generation et les tests du projet genere passent.

## Prochaine action
Commencer P1: corriger le squelette JS/TS, executer des tests sur les fichiers extraits des ZIP, renforcer les tests serveur, verifier CI. Voir TODO.md pour les sous-taches et dependances.
