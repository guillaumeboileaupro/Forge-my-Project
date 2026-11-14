# ADR-0002 - Facade compatible et templates externes

Statut: accepte pour T02.

## Contexte
Le prototype regroupait validation, rendu de textes et creation ZIP dans generator.py. Claude Code developpe en parallele les composants T06-T11 dans forge/config, rules, planner, generator, catalogs et templates. Une extraction directe vers ses noms de modules creerait des conflits et rendrait les appels historiques instables.

## Decision
- Conserver generator.py comme facade publique sans logique metier.
- Isoler le contrat actuel dans forge/config/legacy.py et forge/generator/legacy.py, sans fichiers `__init__.py` concurrents.
- Externaliser les textes actuels sous templates/legacy/ et utiliser uniquement un remplacement de marqueurs en un passage, sans dependance.
- Deplacer l'interface sous ui/ et servir une liste fermee d'assets statiques.
- Ne creer les autres dossiers cibles qu'avec leur premiere implementation concrete.

## Consequences
Les imports, le serveur et les ZIP actuels restent compatibles. Claude peut ajouter ses `__init__.py` et modules sans conflit de nom avec les fichiers `legacy`. Une migration future devra adapter la facade et prouver l'equivalence ou documenter les changements. La bibliotheque legacy est temporaire mais reste testee tant que le formulaire historique est supporte.
