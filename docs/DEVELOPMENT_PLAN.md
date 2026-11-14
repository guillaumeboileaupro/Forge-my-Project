# Plan de developpement

## Priorites
1. Faire tourner la CI du depot, verifier le formulaire et les tests sur Python et JS.
2. Corriger la generation JavaScript et ajouter un vrai profil TypeScript si propose.
3. Remplacer les pipelines rouges generes par une CI valable pour chaque stack et ajouter lockfiles.
4. Ajouter catalogue des stacks versionne et schema de formulaire conditionnel.
5. Ajouter verification des packages, imports et versions sur registres officiels, avec resultat PASS/FAIL/UNVERIFIED.
6. Adapter les skills, MCP et hooks selon les outils du projet, avec permission explicite.
7. Brancher audit secrets/SAST/SCA/SBOM et controles de mise en production.
8. Apercu du plan, checks en local, tests de bout en bout, et export GitHub sous controle.

## Regle de livraison
Chaque etape doit avoir une issue ou des criteres testables et passer la Definition of Done d'AGENTS.md. Une PR ouverte maximum.
