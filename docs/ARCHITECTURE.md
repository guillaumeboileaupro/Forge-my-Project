# Architecture du generateur

## But
Formulaire local -> configuration validee -> plan de generation -> fichiers -> ZIP telechargeable.

## Composants
- index.html : interface et soumission JSON, aucune logique de confiance.
- server.py : serveur HTTP uniquement sur loopback, limite de requete, erreurs et telechargement.
- generator.py : validate() refuse les options inconnues, build() produit un dictionnaire chemin-contenu, generate() ecrit l'archive en memoire.
- tests/ : contrat des options, refus des chemins dangereux, fichiers generes, tests de securite de base.

## Frontieres de confiance
Le navigateur est non fiable. Le serveur ne doit jamais executer les donnees du formulaire en shell et ne doit jamais ecrire une entree archive hors du dossier racine du projet. Pas de communication GitHub ni d'installation depuis l'interface tant que des permissions explicites et une verification n'existent pas.

## Cible evolutive
1. Schema versionne et questionnaire conditionnel.
2. Catalogue de stacks et templates approuves (langage, base, deployeur, agents).
3. Resolver de dependances : registre officiel, versions, docs des imports/API, licences, advisory databases; echec ferme si hors ligne.
4. Assembleur de skills avec conventions Codex/Claude compatibles et profils utilisateurs.
5. Moteur de securite : politiques, hooks, analyse statique, secret scan, SCA, SBOM, attestations.
6. Adaptateurs CI/CD avec pipelines réellement executables, actions epinglees, permissions minimales.
7. Apercu/diff et rapport de validation avant telechargement ou push distant.

## Invariants
Aucun appel reseau en generation pure. Aucun token dans le ZIP. Pas de claim de securite sans preuve. Aucun deployement effectif depuis le simple formulaire.
