# Plan de finalisation - criteres de fin

## Definition de FINI
Forge-my-Project est termine pour le perimetre officiellement supporte lorsqu'un utilisateur peut remplir le questionnaire, voir un plan complet, generer un ZIP, executer les commandes documentees, passer les tests et la CI, et obtenir les controles de dependances et de securite avec preuves. Les options non fonctionnelles doivent etre retirees ou marquees experimentales.

## Carte des dependances
P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P8
                 P3 -> P7 -> P8
                 P4 -> P6
                 P5 -> P7

## Gates de recette
- [ ] G1: CI de Forge verte et tests du serveur, du formulaire et du ZIP passes.
- [ ] G2: Formulaire versionne, valide, conditionnel, accessible, avec retour utilisateur clair.
- [ ] G3: Tous les profils officiellement proposes generent un projet executable et documente.
- [ ] G4: Packages, versions et APIs prouves via sources fiables; dependances verrouillees.
- [ ] G5: AGENTS.md, architecture, skills et hooks utiles, adaptes et controles.
- [ ] G6: MCP reels et permissions minimales; pas de tokens dans les fichiers produits.
- [ ] G7: SAST, SCA, secret scan et SBOM executes si applicables; CI generee fonctionnelle.
- [ ] G8: ZIP et, si retenu, publication GitHub testes, sans effet distant implicite.
- [ ] G9: README, guides d'utilisation/extension, decisions et risques residuels documentes.
- [ ] G10: Aucune anomalie bloquante ou vulnerabilite critique/haute non resolue pour une livraison annoncée comme securisee.

## Recette E2E
1. Installation sur environnement neuf avec les prerequis annonces.
2. Creation projet Python sans dependance, extraction ZIP, execution des tests.
3. Creation projet JS/TS annonce, installation reproductible et execution tests.
4. Ajout package inexistant: erreur explicite, pas d'installation.
5. Simuler registre indisponible: NON VERIFIE, pas de faux PASS.
6. Selection d'agents/skills/hooks/MCP: fichiers exacts, pas de secrets, commandes valides.
7. Generation CI: run GitHub vert sur matrice supportee, echec detecte si test casse.
8. Cas negatifs: nom invalide, chemins traversants, contenu non fiable, requete trop grande.
9. Export et publication GitHub uniquement apres validation explicite.
10. Rapport final avec liens vers runs, tests, exceptions et limites.

## Statuts et preuves
Employer TODO, IN PROGRESS, BLOCKED, DONE. Une tache n'est DONE qu'avec preuve. Chaque gate est PASS, FAIL ou NON VERIFIE, avec commande ou lien de run. Aucun NON VERIFIE ne vaut PASS.

## Hors perimetre conditionnel
Les deployeurs S3NS et OUTSCALE necessitent un environnement autorise pour une verification reelle. Sans cela, livrer seulement les guides verifies et ne pas promettre de deploiement operationnel.
