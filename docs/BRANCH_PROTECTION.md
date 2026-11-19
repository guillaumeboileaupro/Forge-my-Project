# Assistant de protection de branche GitHub (E09)

L'assistant prepare une protection de branche sans jamais l'appliquer. Il faut relire, copier puis executer manuellement la commande proposee.

## Prerequis

- installer et authentifier la CLI GitHub : `gh auth status` doit reussir ;
- pouvoir lire le depot et la branche ;
- pour executer ensuite la commande, disposer de la permission GitHub **Administration: write** sur le depot ;
- avoir deja execute la CI sur le commit de tete de la branche, afin que GitHub expose ses check-runs.

Aucun jeton n'est demande, lu ou affiche par Forge. La CLI `gh` gere elle-meme son authentification.

## Utilisation

1. Demarrer Forge et ouvrir l'etape **Verification et apercu**.
2. Dans **Assistant de protection de branche GitHub**, saisir `owner/repository` et la branche.
3. Choisir **Verifier et preparer la commande**. Cette action effectue uniquement des requetes GitHub `GET`.
4. Relire le SHA, la protection actuelle, les permissions et chaque check propose comme obligatoire.
5. Si le check `Attribution Git (aucun agent IA auteur, committer ou co-auteur)` a reellement ete observe, copier la commande.
6. Valider son contenu puis l'executer soi-meme dans un terminal. Forge ne peut pas faire cette derniere etape.

La commande utilise l'endpoint officiel `PUT /repos/{owner}/{repo}/branches/{branch}/protection`. Elle exige les checks observes sur le commit de tete, impose leur actualisation avec la branche, applique les regles aux administrateurs et interdit force-push et suppression. Elle ne configure ni revue obligatoire ni restriction d'equipe (`null`) : relire ces choix avant execution si le depot exige une politique differente.

## Erreurs et limites

- **Depot absent ou inaccessible** : verifier le nom et les droits du compte `gh`.
- **Branche inexistante ou inaccessible** : verifier le nom exact, y compris les `/` eventuels.
- **Aucun check CI observe** : lancer la CI sur la branche puis recommencer. Aucun controle n'est presente comme actif.
- **Check d'attribution absent** : aucune commande n'est generee, pour eviter une protection incomplete.
- **Permission insuffisante** : l'apercu reste consultable, mais GitHub refusera l'execution manuelle.
- Un check observe prouve seulement son existence sur le commit de tete, pas qu'il est deja obligatoire. `protection_active` indique uniquement si une protection de branche a pu etre lue.

Reference API : [GitHub REST - Update branch protection](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection).
