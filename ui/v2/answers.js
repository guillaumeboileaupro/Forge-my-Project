// Reponses du parcours v2 (E18b) : brouillon automatique, export et import JSON, reinitialisation,
// profils predefinis et personnels. Memes endpoints, memes formats et meme cle de brouillon que
// l'interface actuelle (T05) : le serveur valide et normalise tout document avant son application.
// Le navigateur ne conserve que le brouillon des reponses (jamais de fichier, de jeton ni de secret).
'use strict';

(function () {
  const DRAFT_KEY = 'forge-my-project.draft.v1'; // partage avec l'interface actuelle
  const ANSWERS_FORMAT = 'forge-my-project/answers';
  const MAX_IMPORT_BYTES = 65536;
  const SAVE_DELAY_MS = 300;

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

  async function call(path, method, body) {
    const init = body === undefined ? {method}
      : {method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
    const response = await fetch(path, init);
    let payload = {};
    try { payload = await response.json(); } catch (error) { payload = {ok: false, error: 'réponse illisible'}; }
    if (!response.ok || payload.ok === false) throw new Error(payload.error || `refus du serveur (${response.status})`);
    return payload;
  }

  function storage() {
    try { return window.localStorage; } catch (error) { return null; }
  }

  function download(name, text) {
    const url = URL.createObjectURL(new Blob([text], {type: 'application/json'}));
    el('a', {href: url, download: name}).click();
    URL.revokeObjectURL(url);
  }

  // options : collect() -> reponses courantes ; apply(reponses normalisees) ; reset() ; status(message).
  function create(root, options) {
    const state = {profiles: {}, timer: null, ready: false};

    const draft = el('p', {id: 'draft-status', class: 'muted hint', role: 'status'}, 'Sauvegarde automatique dans ce navigateur.');
    const select = el('select', {id: 'profile-select'});
    const info = el('p', {id: 'profile-info', class: 'muted hint'});
    const load = el('button', {type: 'button', id: 'profile-load', text: 'Charger le profil', disabled: true});
    const label = el('input', {id: 'profile-label', type: 'text', maxlength: 60, autocomplete: 'off'});
    const description = el('input', {id: 'profile-description', type: 'text', maxlength: 200, autocomplete: 'off'});
    const createButton = el('button', {type: 'button', id: 'profile-create', text: 'Enregistrer comme nouveau profil'});
    const update = el('button', {type: 'button', id: 'profile-update', text: 'Mettre à jour le profil', disabled: true});
    const remove = el('button', {type: 'button', id: 'profile-delete', text: 'Supprimer le profil', disabled: true});
    const where = el('p', {id: 'profile-storage', class: 'muted hint'});
    const exportButton = el('button', {type: 'button', id: 'answers-export', text: 'Exporter (JSON)'});
    const importInput = el('input', {type: 'file', id: 'answers-import', accept: 'application/json,.json', class: 'file-input'});
    const reset = el('button', {type: 'button', id: 'answers-reset', text: 'Réinitialiser'});
    const alert = el('p', {id: 'answers-alert', class: 'wf-error', role: 'alert'});

    root.replaceChildren(
      el('h3', {class: 'box-title', id: 'answers-title', text: 'Réponses'}),
      draft,
      el('div', {class: 'field'}, el('label', {for: 'profile-select', text: 'Profil'}), select, info),
      load,
      el('details', {id: 'profile-manage'}, el('summary', {text: 'Profils personnels'}),
        el('div', {class: 'field'}, el('label', {for: 'profile-label', text: 'Libellé du profil'}), label),
        el('div', {class: 'field'}, el('label', {for: 'profile-description', text: 'Description du profil'}), description),
        el('div', {class: 'answers-actions'}, createButton, update, remove), where),
      el('div', {class: 'answers-actions'}, exportButton,
        el('label', {for: 'answers-import', class: 'file-label', text: 'Importer (JSON)'}), importInput, reset),
      alert);

    const showAlert = message => { alert.textContent = message; };
    const document_ = () => ({format: ANSWERS_FORMAT, schema_version: 1, answers: options.collect()});
    const validate = value => call('/api/answers/validate', 'POST', {document: value});
    // Un document sans type de projet (premiere etape inachevee) le laisse non choisi au lieu du type par defaut.
    const unchosen = (source, answers) => {
      const raw = source && typeof source === 'object' && source.answers && typeof source.answers === 'object' ? source.answers : source;
      return raw && typeof raw === 'object' && !('project_type' in raw) ? Object.assign({}, answers, {project_type: ''}) : answers;
    };

    // --- Brouillon --------------------------------------------------------------
    function save() {
      state.timer = null;
      if (!state.ready) return;
      const store = storage();
      if (!store) { draft.textContent = 'Sauvegarde automatique indisponible dans ce navigateur.'; return; }
      try {
        store.setItem(DRAFT_KEY, JSON.stringify(document_()));
        draft.textContent = `Réponses sauvegardées automatiquement à ${new Date().toLocaleTimeString('fr-FR')}.`;
      } catch (error) {
        draft.textContent = 'Sauvegarde automatique indisponible dans ce navigateur.';
      }
    }

    function changed() {
      clearTimeout(state.timer);
      state.timer = setTimeout(save, SAVE_DELAY_MS);
    }

    async function restore() {
      const store = storage();
      let raw = null;
      try { raw = store && store.getItem(DRAFT_KEY); } catch (error) { raw = null; }
      if (raw) {
        try {
          const saved = JSON.parse(raw);
          const payload = await validate(saved);
          options.apply(unchosen(saved, payload.answers));
          draft.textContent = 'Réponses précédentes restaurées.';
        } catch (error) {
          try { store.removeItem(DRAFT_KEY); } catch (ignored) { /* stockage indisponible */ }
          showAlert(`Brouillon précédent ignoré car incompatible : ${error.message}`);
        }
      }
      state.ready = true;
    }

    // --- Export, import, reinitialisation ---------------------------------------
    exportButton.addEventListener('click', async () => {
      showAlert('');
      try {
        const payload = await validate(document_());
        download(`${payload.answers.name || 'reponses'}.forge.json`, `${JSON.stringify(payload.export, null, 2)}\n`);
        options.status('Réponses exportées.');
      } catch (error) {
        showAlert(`Export impossible : ${error.message}`);
      }
    });

    importInput.addEventListener('change', async () => {
      const file = importInput.files[0];
      importInput.value = '';
      if (!file) return;
      showAlert('');
      if (file.size > MAX_IMPORT_BYTES) { showAlert('Import refusé : fichier trop volumineux (64 Kio maximum).'); return; }
      let parsed;
      try { parsed = JSON.parse(await file.text()); } catch (error) {
        showAlert("Import refusé : le fichier n'est pas un JSON valide.");
        return;
      }
      try {
        const payload = await validate(parsed);
        options.apply(unchosen(parsed, payload.answers));
        save();
        options.status(`Configuration importée depuis ${file.name}.`);
      } catch (error) {
        showAlert(`Import refusé : ${error.message}`);
      }
    });

    reset.addEventListener('click', () => {
      if (!window.confirm('Réinitialiser le questionnaire ? Les réponses et les modifications non écrites sont perdues.')) return;
      showAlert('');
      const store = storage();
      try { if (store) store.removeItem(DRAFT_KEY); } catch (error) { /* stockage indisponible */ }
      state.ready = false;
      options.reset();
      clearTimeout(state.timer); // aucune sauvegarde des reponses vides : le brouillon reste efface
      state.timer = null;
      state.ready = true;
      draft.textContent = 'Questionnaire réinitialisé.';
    });

    // --- Profils ----------------------------------------------------------------
    function selectedProfile() {
      return state.profiles[select.value] || null;
    }

    function profileSelected() {
      const profile = selectedProfile();
      const custom = Boolean(profile) && profile.kind === 'personnalise';
      load.disabled = !profile;
      update.disabled = !custom;
      remove.disabled = !custom;
      info.textContent = profile ? profile.description : '';
      if (custom) {
        label.value = profile.label;
        description.value = profile.description;
      }
    }

    async function refresh(selectId = '') {
      try {
        const payload = await call('/api/profiles', 'GET');
        state.profiles = {};
        select.replaceChildren(el('option', {value: '', text: 'Choisir un profil…'}));
        for (const [title, list] of [['Profils prédéfinis', payload.predefined], ['Profils personnels', payload.custom]]) {
          if (!list.length) continue;
          const group = el('optgroup', {label: title});
          for (const profile of list) {
            state.profiles[profile.id] = profile;
            group.append(el('option', {value: profile.id, text: profile.label}));
          }
          select.append(group);
        }
        select.value = selectId in state.profiles ? selectId : '';
        where.textContent = `Profils personnels enregistrés localement dans ${payload.storage}.`;
      } catch (error) {
        showAlert(`Profils indisponibles : ${error.message}`);
      }
      profileSelected();
    }

    select.addEventListener('change', profileSelected);
    // Fermeture ou rechargement pendant le delai de sauvegarde : rien n'est perdu (comme l'interface actuelle).
    window.addEventListener('pagehide', () => { if (state.timer) { clearTimeout(state.timer); save(); } });

    load.addEventListener('click', () => {
      const profile = selectedProfile();
      if (!profile) return;
      showAlert('');
      options.apply(profile.answers);
      save();
      options.status(`Profil « ${profile.label} » chargé : les réponses restent modifiables.`);
    });

    async function saveProfile(method) {
      showAlert('');
      const id = select.value;
      const path = method === 'PUT' ? `/api/profiles/${encodeURIComponent(id)}` : '/api/profiles';
      try {
        const payload = await call(path, method, {label: label.value, description: description.value, answers: options.collect()});
        await refresh(payload.profile.id);
        options.status(`Profil « ${payload.profile.label} » enregistré.`);
      } catch (error) {
        showAlert(`Profil non enregistré : ${error.message}`);
      }
    }

    createButton.addEventListener('click', () => saveProfile('POST'));
    update.addEventListener('click', () => saveProfile('PUT'));
    remove.addEventListener('click', async () => {
      const profile = selectedProfile();
      if (!profile || !window.confirm(`Supprimer le profil « ${profile.label} » ?`)) return;
      showAlert('');
      try {
        await call(`/api/profiles/${encodeURIComponent(profile.id)}`, 'DELETE');
        label.value = '';
        description.value = '';
        await refresh();
        options.status(`Profil « ${profile.label} » supprimé.`);
      } catch (error) {
        showAlert(`Suppression impossible : ${error.message}`);
      }
    });

    return {changed, restore, refresh, save};
  }

  window.ForgeAnswers = {create, DRAFT_KEY};
}());
