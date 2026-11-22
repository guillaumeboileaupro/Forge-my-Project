# Design system v2 — Forge-my-Project

Statut : référence E14 à valider avant E15 et E16. Ces fichiers sont des maquettes statiques : ils ne remplacent pas l'interface actuelle et n'appellent aucune API.

## Identité de référence

La source officielle est [`assets/logo.svg`](../../assets/logo.svg), complétée par [`assets/favicon.svg`](../../assets/favicon.svg). Les trois couleurs de marque sont extraites telles quelles du SVG : fond parchemin `#F5F0E8`, encre anthracite `#292726` et cuivre `#D97757`. Le symbole associe un terminal à un document Markdown. Il exclut les cerveaux, étincelles IA, néons, dégradés et effets décoratifs.

Le logo complet est réservé à l'accueil et aux surfaces larges. Le favicon sert aux espaces compacts. Il ne faut ni recolorer le cuivre, ni redessiner le pictogramme, ni modifier ses proportions. Sur fond sombre, le logo conserve son fond clair : une future variante inversée exigerait une validation séparée.

## Principes

1. L'outil ressemble à un atelier Unix calme, pas à un tableau de bord marketing.
2. L'action courante, l'état de validation et la destination d'écriture dominent la hiérarchie.
3. Une surface, une responsabilité : les séparateurs et l'espacement précèdent les cartes et les ombres.
4. PASS, FAIL et NON VÉRIFIÉ combinent libellé, symbole et couleur.
5. Toute action souris a un équivalent clavier. Le focus est visible et les cibles tactiles font au moins 44 px.
6. La densité desktop reste productive; le mobile réordonne les fonctions au lieu de compresser trois panneaux.

## Artefacts

- [`tokens.css`](tokens.css) : couleurs, typographie, espacements, dimensions, rayons et mouvement.
- [`components.css`](components.css) : boutons, champs, onglets, panneaux, diagnostics et focus de référence.
- [`mockups/index.html`](mockups/index.html) : six écrans représentatifs, thèmes clair/sombre et largeurs adaptatives.
- [`../UI_V2_CONTRACTS.md`](../UI_V2_CONTRACTS.md) : frontières obligatoires pour E15 et E16.

## Typographie

La pile locale monospace reprend celle du SVG : `Liberation Mono`, `DejaVu Sans Mono`, `Courier New`, monospace. Elle sert à l'identité, aux chemins, commandes, diagnostics et éditeur. La pile UI système sert aux textes longs et aux formulaires. Aucun téléchargement de fonte ni dépendance réseau.

## Grille et densité

L'unité de base vaut 4 px. Les espacements exposés vont de 4 à 48 px. Les contrôles ont une hauteur minimale de 36 px en mode compact et 44 px sur surfaces tactiles. Les rayons restent sobres : 4 px pour les contrôles, 8 px pour les panneaux flottants, jamais de capsules décoratives.

Disposition desktop cible : rail 56 px, navigation 240–320 px, zone centrale flexible (minimum 520 px), aperçu 320–520 px et diagnostics bas 180–360 px. Les poignées visibles mesurent 8 px et leur cible interactive 16 px. E15 doit borner chaque redimensionnement et permettre de réinitialiser la disposition.

## Responsive

Les ruptures sont dictées par le contenu :

- `>= 1200 px` : trois zones simultanées, diagnostics en panneau inférieur;
- `768–1199 px` : deux zones, aperçu ou diagnostics dans un onglet secondaire;
- `< 768 px` : une seule zone, navigation et panneaux secondaires en tiroirs modaux, barre d'action persistante;
- `< 480 px` : labels courts, actions secondaires dans un menu, aucune édition en colonnes.

Tailles de référence E18 : 360×800, 768×1024, 1280×800, 1440×900 et 1920×1080, juste avant/après chaque rupture.

## États et mouvement

Chaque composant prévoit `default`, `hover`, `focus-visible`, `active`, `selected`, `disabled`, `loading`, `error` et, si pertinent, `unavailable`. Les transitions fonctionnelles durent 120–180 ms. `prefers-reduced-motion: reduce` les supprime. Aucun état important ne dépend d'une animation ou du survol.

## Icônes

Utiliser des SVG filaires de 16 ou 20 px, trait 1.5 px, extrémités arrondies, `currentColor`. Une icône seule reçoit un nom accessible et une cible de 44 px. Les symboles texte des maquettes (`+`, `×`, chevrons) sont des repères; E15 les remplace par les SVG communs. Aucun emoji comme icône produit.

## Validation E14

- Couleurs source comparées aux deux SVG officiels.
- Contrastes calculés automatiquement pour les couples de texte, focus et diagnostics essentiels.
- Parcours clavier des maquettes : lien d'évitement, sélecteur d'écran, thème, navigation, onglets et actions.
- Reflow prévu sans scroll horizontal de page aux largeurs de référence.
- Maquettes purement statiques : les écritures, téléchargements et validations restent désactivés ou explicitement simulés.

Une validation automatisée n'est pas une certification WCAG. E18 conserve la recette Firefox, le lecteur d'écran si disponible, les captures approuvées et la vérification manuelle aux résolutions cibles.
