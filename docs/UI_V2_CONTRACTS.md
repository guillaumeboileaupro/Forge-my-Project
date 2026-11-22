# Contrats UI v2 pour E15 et E16

Statut : contrat E14. Toute incompatibilité exige une décision documentée, des tests de migration et une mise à jour de `docs/CONTRACTS.md`.

## Frontière de confiance

La v2 remplace uniquement la présentation. Le navigateur reste non fiable et ne détient ni validation métier, ni autorisation d'écriture, ni construction de chemins. Le serveur Python conserve les contrats décrits dans `docs/CONTRACTS.md`; E15 et E16 ne dupliquent pas le moteur en JavaScript.

La configuration canonique est le schéma moteur v1 retourné/accepté par les API actuelles. Le magasin UI peut contenir des préférences de présentation séparées, mais ne les insère jamais dans une configuration exportée.

## Contrat d'état partagé

L'interface distingue obligatoirement :

- `answers` : saisie utilisateur normalisée par `/api/answers/validate`;
- `catalog` : copie en lecture seule de `/api/catalog`;
- `plan` : dernier résultat de `/api/plan`, associé à l'empreinte des réponses;
- `files.generated` et `files.edited` : ensembles de chemins strictement identiques;
- `validation` : `idle | running | valid | invalid | stale`;
- `network` : `offline | explicit-request | running | complete | failed`;
- `write` : `idle | comparing | review | applying | complete | failed | restored`;
- `layout` : préférences locales versionnées, sans donnée projet sensible.

Tout changement de réponse, technologie, agent, sécurité, skill approuvé ou MCP marque le plan et les fichiers `stale`, invalide le jeton d'écriture et désactive archive/écriture jusqu'à une nouvelle validation serveur.

## Contrat E15 — coque

E15 peut construire navigation, panneaux, onglets, palette et thèmes, mais ne modifie aucun endpoint ni flux métier. Les panneaux ont des identifiants stables (`navigation`, `configuration`, `preview`, `diagnostics`, `editor`), des bornes de taille, une commande de masquage/restauration et une commande « Réinitialiser la disposition ».

Les préférences locales utilisent une clé distincte, par exemple `forge-my-project.ui.v2`, avec `{schemaVersion, theme, density, panels, activePanel}`. Une valeur inconnue ou corrompue est ignorée sans toucher au brouillon v1. Le thème suit `prefers-color-scheme` par défaut; un choix explicite le remplace. Aucune requête réseau ne part au montage de la coque.

La palette expose seulement des commandes réellement disponibles, avec identifiant, libellé, raccourci affiché et prédicat d'activation. Elle n'exécute jamais une chaîne comme commande système.

## Contrat E16 — parcours et aperçu

E16 rend les questions à partir du catalogue et des règles existantes. Une question masquée par condition n'est pas silencieusement envoyée si sa valeur n'est plus valide. Le serveur reste l'autorité pour prérequis, conflits, versions et diagnostics.

Arbre, diagramme et éditeur partagent le même `selectedPath`. Une sélection valide synchronise les trois vues; une sélection inconnue est refusée. Le diagramme représente uniquement des éléments du plan réel, sans inventer de dépendance. Le focus n'est déplacé que sur action explicite.

Les appels asynchrones portent un identifiant de requête. Une réponse ancienne ne remplace jamais un état plus récent. L'annulation visuelle n'est pas présentée comme une annulation serveur si la requête est déjà partie.

## Diagnostics

Le modèle d'affichage minimal est `{id, severity, status, title, detail, path?, field?, source}`. Les valeurs serveur PASS, FAIL et NON VÉRIFIÉ restent inchangées. L'UI peut filtrer ou grouper, jamais promouvoir NON VÉRIFIÉ en PASS. Un diagnostic lié à un champ ou fichier offre une action de navigation, sans HTML fourni par le serveur.

Ordre : bloquants, erreurs, avertissements, informations; puis ordre stable d'arrivée. Les compteurs et filtres ont un nom accessible. Les mises à jour importantes utilisent une région `status` polie; les erreurs bloquantes utilisent `alert` sans répéter tout le journal.

## Édition et écriture

E14 ne spécifie pas un nouvel éditeur métier. E17 réutilise `/api/files/validate`, `/api/write/compare` et `/api/write/apply`. Aucun fichier ne peut être ajouté/supprimé depuis l'éditeur. Les décisions `keep`, `replace`, `auto`, `merge`, les jetons, bases fiables et confirmations NON VÉRIFIÉ conservent leur sens exact.

Les actions destructives indiquent cible et conséquence, demandent confirmation au point d'engagement et conservent le focus logique après fermeture. Le bouton primaire reflète l'étape courante; deux actions d'engagement concurrentes ne sont pas affichées comme primaires.

## Accessibilité et clavier

Ordre global : lien d'évitement, rail, navigation contextuelle, onglets, contenu, aperçu, diagnostics, barre d'action. Raccourcis proposés : `Ctrl+K` palette, `Ctrl+Shift+P` commandes, `Ctrl+1…6` vues, `F6` zone suivante, `Escape` ferme la surface temporaire. E15 vérifie les conflits navigateur/Firefox avant activation.

Onglets : modèle ARIA tabs avec flèches, Home/End et activation explicite. Arbres : modèle tree uniquement si toutes les interactions clavier sont implémentées; sinon liste imbriquée native. Splitters : rôle `separator`, orientation, valeurs min/max/now et contrôle au clavier. Les panneaux modaux piègent le focus et le restituent à l'élément déclencheur.

## Performance et sécurité

Sans dépendance ajoutée par défaut. Cibles E18 sur machine de référence à documenter : premier rendu utile < 1 s sur loopback, interaction locale < 100 ms, mise à jour d'aperçu différée sans bloquer la saisie, aucune ressource distante, aucune erreur console. Ce sont des budgets à mesurer, pas des résultats E14.

Tout texte non fiable est inséré via `textContent`/attributs validés. Pas de `innerHTML` avec données, pas de script inline si la CSP l'interdit, pas de persistance de jeton, contenu de fichier ou diagnostic sensible dans les préférences UI.

## Gates avant bascule

E15 et E16 restent derrière une route ou un point d'entrée distinct jusqu'à E18. L'ancienne interface demeure la référence fonctionnelle. La bascule exige : parité de parcours, tests serveur/JS, Firefox, clavier, deux thèmes, cinq résolutions, contrastes, budgets mesurés, captures approuvées, CI verte et absence de P0/P1.

## Implémentation E16 (préversion)

- Route `/v2/parcours`, fichiers `ui/v2/journey.{html,js,css}`, tokens servis depuis `docs/design-system/tokens.css`. Aucun appel réseau autre que `/api/catalog` (au chargement) et `/api/plan` (après saisie, différé de 350 ms) ; aucun stockage local.
- État : `answers` (réponses du parcours), `catalog`, `plan` (dernière réponse appliquée), `validation` (`idle | running | valid | invalid | stale`), `selectedPath`, `requestSeq`. Une réponse dont l'identifiant n'est pas le dernier est ignorée.
- Conditions d'affichage dérivées du catalogue : une technologie n'est proposée que si chaque groupe de prérequis est sélectionné ; versions seulement pour les technologies versionnées choisies ; serveurs MCP seulement pour le type de projet. Une réponse devenue invalide est retirée avant envoi et signalée.
- Le diagramme se construit uniquement depuis `graph` (`docs/CONTRACTS.md`). Arbre, diagramme et contenu partagent `selectedPath` ; un chemin absent du plan est refusé.
- E15 pourra intégrer ces vues dans ses panneaux (`configuration`, `preview`, `diagnostics`) sans changer ce contrat.
