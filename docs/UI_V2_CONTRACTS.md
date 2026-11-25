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

## Implémentation E15 (coque)

Réattribuée à Claude par le propriétaire le 25/11/2026. La coque enveloppe `/v2/parcours` (route distincte jusqu'à E18) ; aucun endpoint ni flux métier modifié.

- Fichiers : `ui/v2/shell.js` (`window.forgeShell`), `ui/v2/shell.css`, chargés avant les composants. La coque n'appelle aucune API et ignore l'état du parcours ; `journey.js` lui ajoute ses commandes (étape suivante/précédente, vues de l'aperçu).
- Préférences : clé `forge-my-project.ui.v2`, `{schemaVersion: 1, theme, density, panels: {navigation, preview: {visible, size, side}}, activePanel}`. JSON invalide, autre version ou valeur inconnue : ignoré champ par champ ; tailles bornées ; côtés en conflit remis par défaut. Le brouillon v1 n'est jamais lu ni modifié.
- Thème : `system` (suit `prefers-color-scheme`, y compris en direct), `light`, `dark`. Densité `compact` : espacements réduits, cibles 36 px (44 px sous 768 px ou pointeur grossier).
- Panneaux : `navigation` (Étapes) et `preview` (Aperçu) masquables (en-tête, rail, palette ; le focus va à la commande de restauration), déplaçables par échange de côtés (ordre DOM = ordre visuel, focus conservé), redimensionnables par séparateur `role="separator"` (`aria-valuemin/max/now`, flèches ±16 px, Début/Fin, pointeur). Bornes : Étapes 200–440 px, Aperçu 280–720 px, et au plus 40 % de la fenêtre. `configuration` reste au centre. Sous 1200 px le panneau de droite passe sous le contenu ; sous 768 px tout s'empile, sans séparateur.
- Onglets : aperçu « Plan » (arborescence et diagramme, toujours ensemble) et « Résumé » (réponses, texte seulement) ; modèle ARIA tabs, flèches et Début/Fin déplacent le focus, Entrée/Espace activent.
- Palette : `dialog` modal, `combobox` + `listbox`, filtre insensible aux accents, flèches, Entrée, Échap ; le focus reste dans la palette puis revient au déclencheur. Seules les commandes disponibles sont listées ; une commande est un objet enregistré (`id` unique, `run` fonction), jamais une chaîne exécutée.
- Raccourcis : `Ctrl+K` (palette) et Échap seulement. `Ctrl+Shift+P` (fenêtre privée), `Ctrl+1…8` (onglets) et `F6` (barre d'adresse) sont réservés par Firefox et non utilisés ; les zones sont atteintes par le rail et les commandes « Aller à ».
- E17 place l'éditeur et les diagnostics dans des panneaux `editor` et `diagnostics` de la coque (aujourd'hui dans l'atelier sous la grille).

## Recette E18a (sous-lot E18 sans la coque)

Recette automatisée de `/v2/parcours` et défauts corrigés : voir `docs/E18A_ACCEPTANCE.md`. Règles ajoutées, valables pour E15 et E17 :
- aucune image externe (la CSP n'a pas d'`img-src`) ; SVG inline ;
- `color-scheme` et `scrollbar-color` suivent le thème ;
- cibles d'au moins 36 px, et 44 px sous 768 px ou en pointeur grossier ;
- une barre collante réserve sa hauteur par `scroll-padding` ;
- l'éditeur ne peint que les lignes visibles ;
- les marques `performance` `forge-ready` et `forge-plan` servent aux mesures de budget.

## Implémentation E17a (sous-lot E17 sans la coque)

Découpage décidé par le propriétaire le 22/11/2026 : E15 n'étant pas commencée, E17a livre les composants dans `/v2/parcours` ; E17 (dépend de E15) les place dans les panneaux `editor` et `diagnostics` de la coque, sans changer ce contrat.

- Fichiers séparés, chargés avant `journey.js` : `ui/v2/editor.js` (`window.ForgeEditor`), `ui/v2/diagnostics.js` (`window.ForgeDiagnostics`), `ui/v2/workflow.js` (`window.ForgeWorkflow`). L'éditeur et le panneau n'appellent aucune API ; `workflow.js` n'appelle que `/api/files/validate`, `/api/destination/browse`, `/api/write/compare`, `/api/write/apply`.
- Éditeur : `textarea` natif (saisie, sélection, presse-papiers, lecteur d'écran) superposé à une couche colorée `aria-hidden` construite nœud par nœud ; numéros de ligne ; ligne/colonne/langage ; recherche (`Ctrl+F`, Entrée/Maj+Entrée, Échap), casse, remplacer, tout remplacer ; « Rétablir le fichier généré ». Coloration désactivée au-delà de 200 000 caractères. Aucun ajout ni suppression de fichier.
- Éditions : `edits[chemin]` seulement si le texte diffère du rendu généré. Si un nouveau plan change le rendu d'un fichier édité ou le retire, l'édition est retirée et signalée (jamais de fusion silencieuse). Toute modification de réponse ou de contenu rend la validation et la comparaison périmées.
- Diagnostics : ordre serveur stable par gravité, filtres par gravité (`aria-pressed`, compteurs toujours visibles) et par texte ; « Aller à » seulement si la cible se déduit du `code` et du `subject` du serveur (fichier du plan, version, technologie, catégorie, serveur MCP, description) ; sinon aucun lien.
- Écriture : mêmes champs et même sens que l'interface actuelle. Validation exigée avant comparaison, comparaison avant écriture ; conflits avec diff, décisions `keep`/`replace`/`auto`/`merge` (désactivées si le serveur ne les propose pas), toute décision à reconfirmer ; confirmation NON VÉRIFIÉ par jeton (`acknowledge`), contrôle critique bloquant sans confirmation possible ; rapport et journal du serveur affichés tels quels.
