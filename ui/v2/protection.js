// Assistant de protection de branche GitHub du parcours v2 (E18b), meme contrat que l'interface
// actuelle (E09) : inspection en lecture seule par la CLI gh cote serveur, puis affichage d'une
// commande que l'utilisateur relit, copie et execute lui-meme. Rien n'est jamais applique ici.
'use strict';

(function () {
  function el(tag, attributes = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attributes)) {
      if (value === false || value === null || value === undefined) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else node.setAttribute(key, value === true ? '' : String(value));
    }
    for (const child of children) node.append(child);
    return node;
  }

  async function post(path, body) {
    const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    let payload = {};
    try { payload = await response.json(); } catch (error) { payload = {ok: false, error: 'réponse illisible'}; }
    return {response, payload};
  }

  function create(root) {
    const repository = el('input', {id: 'gh-repository', type: 'text', autocomplete: 'off', spellcheck: 'false',
                                    placeholder: 'organisation/projet'});
    const branch = el('input', {id: 'gh-branch', type: 'text', autocomplete: 'off', spellcheck: 'false', value: 'main'});
    const prepare = el('button', {type: 'button', id: 'gh-prepare', text: 'Vérifier et préparer la commande'});
    const summary = el('div', {id: 'gh-summary'});
    const command = el('textarea', {id: 'gh-command', class: 'content', rows: 12, readonly: true, spellcheck: 'false', wrap: 'off'});
    const copy = el('button', {type: 'button', id: 'gh-copy', text: 'Copier la commande', disabled: true});
    const preview = el('div', {id: 'gh-preview', hidden: true}, summary,
      el('label', {for: 'gh-command', text: 'Commande à relire puis exécuter manuellement'}), command, copy);
    const status = el('p', {id: 'gh-status', class: 'muted', role: 'status'});

    root.replaceChildren(
      el('p', {class: 'muted hint', text: 'Inspection en lecture seule via la CLI gh. Forge prépare une commande mais ne modifie jamais '
        + 'les protections GitHub : relire, copier puis exécuter vous-même la commande.'}),
      el('div', {class: 'field'}, el('label', {for: 'gh-repository', text: 'Dépôt GitHub (owner/repository)'}), repository),
      el('div', {class: 'field'}, el('label', {for: 'gh-branch', text: 'Branche'}), branch),
      prepare, preview, status);

    prepare.addEventListener('click', async () => {
      preview.hidden = true;
      command.value = '';
      copy.disabled = true;
      prepare.disabled = true;
      status.textContent = 'Inspection GitHub en lecture seule…';
      try {
        const {response, payload} = await post('/api/github/protection/prepare',
          {repository: repository.value.trim(), branch: branch.value.trim()});
        if (!response.ok || !payload.ok) { status.textContent = `Protection de branche non préparée : ${payload.error || 'inspection impossible'}`; return; }
        const protection = !payload.protection_verified ? 'NON VÉRIFIÉE' : payload.protection_active ? 'observée' : 'non observée';
        summary.replaceChildren(
          el('p', {text: `Dépôt : ${payload.repository} — branche : ${payload.branch} — tête : ${payload.head_sha}`}),
          el('p', {class: payload.can_apply ? 'wf-ok' : 'wf-warning',
                   text: `Permission requise : ${payload.required_permission}. ${payload.can_apply ? 'Permission observée.'
                     : 'Permission non observée : exécution impossible avec ce compte.'}`}),
          el('p', {text: `Protection actuelle : ${protection}.`}),
          el('p', {text: `Contrôles obligatoires proposés (${payload.required_checks.length}) : ${payload.required_checks.join(', ') || 'aucun'}.`}),
          ...payload.warnings.map(text => el('p', {class: 'wf-warning', text})),
          el('p', {class: 'wf-warning', text: "Aucune modification distante n'a été appliquée. Relire la commande avant toute exécution manuelle."}));
        command.value = payload.command || '';
        command.hidden = !payload.command;
        copy.disabled = !payload.command;
        preview.hidden = false;
        status.textContent = payload.command ? 'Commande préparée, non exécutée.'
          : 'Inspection terminée ; commande non générée tant que les contrôles requis ne sont pas vérifiés.';
      } catch (error) {
        status.textContent = `Protection de branche non préparée : ${error.message}`;
      } finally {
        prepare.disabled = false;
      }
    });

    copy.addEventListener('click', async () => {
      if (!command.value) return;
      try {
        await navigator.clipboard.writeText(command.value);
        status.textContent = 'Commande copiée. Elle reste à relire et à exécuter manuellement.';
      } catch (error) {
        command.focus();
        command.select();
        status.textContent = 'Copie automatique indisponible : le texte est sélectionné pour une copie manuelle.';
      }
    });
  }

  window.ForgeProtection = {create};
}());
