# Recette progressive E18a — parcours v2 (`/v2/parcours`)

Sous-lot de E18 décidé par le propriétaire le 22/11/2026 : E15 (coque) n'étant pas commencée, E18a recette ce qui existe (E16, E17a) sans bascule. L'interface actuelle reste la référence fonctionnelle. E18 refera la recette sur la coque E15 et décidera la bascule.

Statuts : **PASS** = vérifié par un test automatisé exécuté ; **NON VÉRIFIÉ** = non couvert ici ; **EN ATTENTE** = décision du propriétaire.

## Ce qui est vérifié et comment

Toutes les vérifications ci-dessous sont dans `tests/test_e2e_acceptance_firefox.py`, exécuté par la CI (étape Firefox du job `python`) avec un vrai Firefox headless et le vrai serveur local.

| Critère (docs/UI_V2_CONTRACTS.md, docs/design-system/README.md) | Vérification | Statut |
| --- | --- | --- |
| Parcours complet au clavier seul | Questionnaire, aperçu, éditeur (`Ctrl+F`, Échap), validation, comparaison, confirmation et écriture sur disque, uniquement par touches WebDriver. Seule la boîte native `window.confirm` est simulée : WebDriver ne la pilote pas au clavier. | PASS |
| Focus visible à chaque arrêt | Contour d'au moins 2 px (ou trait du nœud SVG) contrôlé à chaque tabulation. | PASS |
| Ordre de tabulation par zones, aucun piège | Ordre croissant barre → étapes → questionnaire → aperçu → éditeur → diagnostics → écriture ; aucun `tabindex` positif. La tabulation atteint la fin du document, et Maj+Tab revient dans la dernière zone. | PASS |
| Résolutions de référence et ruptures | 360×800, 767, 768×1024, 1199, 1200, 1280×800, 1440×900, 1920×1080 : aucun défilement horizontal de page, disposition attendue (1 / 2 / 3 colonnes), éditeur utilisable. | PASS |
| 360 px | Firefox refuse une fenêtre de moins de 500 px. Une session dédiée applique un zoom navigateur de 139 % : la page voit un viewport de 360 px CSS et les media queries mobiles s'appliquent. | PASS (zoom, pas un vrai téléphone) |
| Cibles | 36 px minimum (mode compact) dès 768 px, 44 px sous 768 px ou en pointeur grossier, en hauteur et en largeur. Le diagramme SVG est exclu : chaque nœud de fichier a un équivalent conforme dans l'arborescence (exception « équivalent » de WCAG 2.5.8). | PASS |
| Deux thèmes | Le thème suit le système : session en thème sombre système, plus thème forcé par `data-theme` pour chaque résolution. | PASS |
| Contrastes du rendu réel | Chaque texte visible contre son fond effectif (fonds semi-transparents composés), dans les deux thèmes : 4,5:1, ou 3:1 pour les grands textes. Les composants inactifs sont exemptés (WCAG 1.4.3). Plus de 100 textes contrôlés par thème. | PASS |
| Aucune erreur JavaScript, aucune ressource bloquée | Erreurs, rejets non gérés, `console.error` et violations CSP capturés après le chargement ; chaque image doit être chargée ; aucune ressource hors origine. | PASS |
| Budgets de performance | Voir ci-dessous. Les seuils du contrat sont appliqués tels quels. | PASS |
| Lecteur d'écran | Non testé (aucun lecteur d'écran dans la CI). | NON VÉRIFIÉ |
| Captures | 30 captures (5 largeurs × 2 thèmes × questionnaire/aperçu/atelier) soumises au propriétaire (PR #45). | EN ATTENTE |

## Budgets mesurés

Les mesures sont prises dans la page, jusqu'au cadre suivant rendu, avec la marque `performance` posée par le parcours. Le grand fichier compte 2 000 lignes (environ 70 Kio). Pour les deux actions rejouables, la valeur retenue est la médiane de 3 mesures. Chaque exécution CI écrit ses valeurs dans le journal (lignes `E18A-BUDGET`).

| Mesure | Seuil | Local (Firefox 158, poste de développement, quatre modules E2E enchaînés) |
| --- | --- | --- |
| Premier rendu utile | < 1 000 ms | 98 ms |
| Aperçu appliqué après la saisie (350 ms de report compris) | < 1 500 ms | 390 ms |
| Case de technologie | < 100 ms | 6 ms |
| Étape suivante | < 100 ms | 37 ms |
| Sélection dans l'arborescence | < 100 ms | 15 ms |
| Retour sur le grand fichier | < 100 ms | 56 ms (143 ms avant correction) |
| Frappe dans le grand fichier | < 100 ms | 26 ms |
| Recherche dans le grand fichier | < 100 ms | 16 ms (103 ms avant correction) |
| Tout remplacer (2 000 occurrences) | < 100 ms | 30 ms (145 ms avant correction) |
| Filtre de diagnostics | < 100 ms | 2 ms |

La machine de référence reste à fixer par le propriétaire ; ces valeurs ne sont pas des garanties sur un autre poste.

## Défauts trouvés par la recette et corrigés dans E18a

1. **Logo invisible (depuis E16).** La CSP (`default-src 'none'`, sans `img-src`) bloquait `<img src="/favicon.svg">`. Le logo est désormais en SVG inline, identique à l'actif. La CSP est inchangée. Un test interdit toute image externe dans la v2.
2. **Contraste insuffisant en thème sombre (depuis E16).** Le sous-titre de la barre était à 2,03:1. Il utilise maintenant le papier du logo.
3. **Barres de défilement claires en thème sombre.** Ajout de `color-scheme` et de `scrollbar-color` aux couleurs des tokens.
4. **Barre d'actions collante masquant le champ focalisé à 360 px (WCAG 2.4.11).** Ajout de `scroll-padding-bottom` à la hauteur de la barre.
5. **Cibles de 32 px (E17a).** Relevées à 36 px en mode compact et 44 px sur écran étroit ou tactile.
6. **Éditeur au-delà du budget sur un grand fichier (E17a).**
   - Seules les lignes visibles sont peintes ; deux espaces conservent la hauteur, donc le défilement natif est inchangé.
   - Jetons et débuts de ligne sont mis en cache.
   - « Tout remplacer » passe en une seule copie, au lieu de copies répétées à chaque occurrence.
   - La position du curseur se calcule par recherche dichotomique.

Chaque défaut a d'abord fait échouer un test de la recette, puis le test est passé après la correction. Pour le logo, j'ai restauré temporairement l'ancien HTML : la vérification des images échoue avec lui.

## Ce qui reste pour E18 (après E15 et E17)

- Refaire cette recette sur la coque E15 : panneaux, onglets, palette, raccourcis (`F6`, `Ctrl+K`, `Ctrl+Shift+P`), modèle ARIA des onglets et des séparateurs, choix du thème et de la densité.
- Établir la parité de parcours avec l'interface actuelle (archive, profils, import/export, skills, vérification en ligne), absente de la v2. Portée par le sous-lot E18b (25/11/2026, `tests/test_e2e_parity_firefox.py`).
- Passer une recette avec un lecteur d'écran (Orca) et une recette manuelle sur un vrai téléphone.
- Faire approuver les captures de la coque, vérifier l'absence de P0/P1, puis décider de la bascule.
