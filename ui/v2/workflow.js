// Flux securises existants (E17a) : validation des contenus edites, comparaison avec la destination,
// decisions de conflit, confirmation NON VERIFIE, ecriture. Le navigateur n'a aucune autorite :
// chaque etape est repetee et revalidee par le serveur (/api/files/validate, /api/write/compare,
// /api/write/apply), avec les memes champs et le meme sens que l'interface actuelle (T17, E06, E07).
'use strict';

(function () {
  const STATUS_LABELS = {new: 'nouveau', identical: 'identique', conflict: 'conflit', blocked: 'bloqué'};
  const RESOLUTIONS = [['keep', 'Conserver le fichier local'], ['replace', 'Remplacer par la version générée'],
    ['auto', 'Fusion automatique (sans chevauchement)'], ['merge', 'Fusionner manuellement']];
  const RESOLUTION_LABELS = {keep: 'conservé', replace: 'remplacé', auto: 'fusion automatique', merge: 'fusionné manuellement'};
  const OPERATION_LABELS = {created: 'créé', replaced: 'remplacé', merged: 'fusionné', kept: 'conservé',
    identical: 'identique', 'rolled-back': 'annulé'};

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

  function create(root, options) {
    const state = {assessment: null, validated: null, comparison: null, resolutions: {}, conflictPath: null,
                   writeRoot: '', busy: false};

    const status = el('p', {class: 'wf-status', id: 'wf-status', role: 'status', 'aria-live': 'polite'});
    const unverified = el('div', {id: 'wf-unverified'});
    const validate = el('button', {type: 'button', id: 'wf-validate', class: 'primary', text: 'Valider les fichiers'});
    const validated = el('p', {id: 'wf-validated', class: 'muted'});

    const rootLabel = el('span', {id: 'wf-root', class: 'mono'});
    const destination = el('input', {type: 'text', id: 'wf-destination', autocomplete: 'off', 'aria-describedby': 'wf-destination-hint'});
    const browse = el('button', {type: 'button', id: 'wf-browse', text: 'Parcourir'});
    const up = el('button', {type: 'button', id: 'wf-up', text: 'Dossier parent', disabled: true});
    const dirs = el('ul', {id: 'wf-dirs', class: 'wf-dirs', 'aria-label': 'Sous-dossiers'});
    const compare = el('button', {type: 'button', id: 'wf-compare', text: 'Comparer avec la destination', disabled: true});

    const summary = el('p', {id: 'wf-summary'});
    const entries = el('ul', {id: 'wf-entries', class: 'wf-entries'});
    const conflictTitle = el('h4', {id: 'wf-conflict-title', class: 'mono'});
    const reason = el('p', {id: 'wf-conflict-reason', class: 'muted'});
    const diff = el('pre', {id: 'wf-diff', class: 'content diff', tabindex: '0', 'aria-label': 'Différences entre le fichier local et la version générée'});
    const choices = el('fieldset', {class: 'choices'}, el('legend', {text: 'Décision pour ce fichier'}));
    for (const [value, label] of RESOLUTIONS) {
      const input = el('input', {type: 'radio', name: 'wf-resolution', value});
      input.addEventListener('change', resolutionChanged);
      choices.append(el('label', {class: 'choice'}, input, ` ${label}`));
    }
    const merge = el('textarea', {id: 'wf-merge', class: 'content', rows: 10, spellcheck: 'false', wrap: 'off',
      'aria-label': 'Contenu fusionné manuellement'});
    const mergeBox = el('div', {id: 'wf-merge-box', hidden: true},
      el('label', {for: 'wf-merge', text: 'Contenu fusionné (écrit tel quel, après revalidation)'}), merge);
    const conflict = el('div', {id: 'wf-conflict', class: 'wf-conflict-panel', hidden: true}, conflictTitle, reason, diff, choices, mergeBox);
    const confirm = el('input', {type: 'checkbox', id: 'wf-confirm'});
    const write = el('button', {type: 'button', id: 'wf-write', class: 'primary', text: 'Écrire dans la destination', disabled: true});
    const comparison = el('div', {id: 'wf-comparison', hidden: true}, summary, entries, conflict,
      el('label', {class: 'choice', for: 'wf-confirm'}, confirm, " J'ai relu les décisions et je confirme l'écriture"), write);
    const report = el('div', {id: 'wf-report', role: 'region', 'aria-label': "Rapport d'écriture"});

    root.replaceChildren(
      unverified,
      el('div', {class: 'wf-row'}, validate, validated),
      el('div', {class: 'field'}, el('label', {for: 'wf-destination', text: 'Destination'}), destination,
        el('p', {class: 'muted hint', id: 'wf-destination-hint'}, 'Dossier sous la racine autorisée ', rootLabel, '.'),
        el('div', {class: 'wf-row'}, browse, up), dirs),
      compare, comparison, status, report);

    const setStatus = message => { status.textContent = message; };
    const key = snapshot => (snapshot ? JSON.stringify([snapshot.config, snapshot.files]) : null);
    const ackBox = () => root.querySelector('#wf-ack');
    const items = () => (state.assessment ? state.assessment.items : []);
    const blocking = () => Boolean(state.assessment && state.assessment.blocking.length);
    const acknowledged = () => !items().length || (!blocking() && Boolean(ackBox() && ackBox().checked));
    const acknowledgement = () => (items().length && acknowledged() ? state.assessment.token : undefined);
    const current = () => state.validated !== null && state.validated === key(options.snapshot());

    function renderUnverified() {
      unverified.replaceChildren();
      const assessment = state.assessment;
      if (!assessment || !assessment.items.length) return;
      unverified.append(el('h4', {text: `Contrôles à confirmer : ${assessment.counts.non_verifie} NON VERIFIE, ${assessment.counts.avertissements} avertissement(s)`}));
      const list = el('ul', {class: 'diagnostics', id: 'wf-unverified-list'});
      for (const item of assessment.items) {
        list.append(el('li', {class: `diag ${item.critical ? 'diag-error' : 'diag-warning'}`, 'data-unverified': item.id},
          el('span', {class: 'diag-level', text: `${item.status}${item.critical ? ' - CRITIQUE' : ''}`}),
          ` ${item.name} — raison : ${item.reason} — risque : ${item.risk}`));
      }
      unverified.append(list);
      if (assessment.blocking.length) {
        unverified.append(el('p', {class: 'wf-error', id: 'wf-blocking',
          text: `Opération bloquée : ${assessment.blocking.length} contrôle(s) critique(s) NON VERIFIE. Aucune confirmation ne peut les lever : lancer la vérification en ligne (interface actuelle) ou changer de niveau de sécurité.`}));
      } else {
        const box = el('input', {type: 'checkbox', id: 'wf-ack'});
        box.addEventListener('change', () => { invalidate(''); update(); });
        unverified.append(el('label', {class: 'choice', for: 'wf-ack'}, box,
          ` Je confirme avoir lu ces ${assessment.items.length} élément(s) : ils restent NON VERIFIE ou avertissement, la confirmation ne vaut pas réussite.`));
      }
    }

    function resetComparison() {
      state.comparison = null;
      state.resolutions = {};
      state.conflictPath = null;
      comparison.hidden = true;
      conflict.hidden = true;
      confirm.checked = false;
    }

    function update() {
      const usable = options.snapshot() !== null;
      validate.disabled = state.busy || !usable || blocking() || !acknowledged();
      compare.disabled = state.busy || !current();
      const c = state.comparison;
      const pending = c ? c.entries.filter(e => e.status === 'conflict' && !state.resolutions[e.path]).length : 0;
      write.disabled = state.busy || !c || !current() || pending > 0 || c.summary.blocked > 0 || !c.destination.writable || !confirm.checked;
      if (c && (pending || c.summary.blocked)) {
        write.title = c.summary.blocked ? 'Entrées non sûres dans la destination' : `${pending} conflit(s) sans décision`;
      } else {
        write.removeAttribute('title');
      }
      if (!usable) validated.textContent = 'Aperçu sans erreur bloquante requis avant validation.';
      else if (blocking()) validated.textContent = 'Validation impossible : contrôle critique NON VERIFIE.';
      else if (!acknowledged()) validated.textContent = 'Confirmer les contrôles NON VERIFIE avant de valider.';
      else if (!current()) validated.textContent = 'Contenus non validés.';
    }

    // Toute modification de configuration ou de contenu rend la validation et la comparaison perimees.
    function invalidate(message) {
      const had = state.validated !== null || state.comparison !== null;
      state.validated = null;
      resetComparison();
      if (had && message) setStatus(message);
      update();
    }

    async function run(label, action) {
      state.busy = true;
      update();
      setStatus(label);
      try {
        await action();
      } catch (error) {
        setStatus(`Erreur : ${error.message}`);
      } finally {
        state.busy = false;
        update();
      }
    }

    function refreshAssessment(assessment, message) {
      state.assessment = assessment;
      renderUnverified();
      invalidate('');
      setStatus(message);
    }

    validate.addEventListener('click', () => run('Validation des contenus par le serveur…', async () => {
      const snapshot = options.snapshot();
      const {response, payload} = await post('/api/files/validate', {config: snapshot.config, files: snapshot.files});
      if (!response.ok || !payload.ok) {
        state.validated = null;
        if (payload.diagnostics && payload.diagnostics.length) options.onDiagnostics(payload.diagnostics, 'validation');
        setStatus(`Validation refusée : ${payload.error || 'contenus refusés'}`);
        return;
      }
      if (key(options.snapshot()) !== key(snapshot)) { setStatus('Contenus modifiés pendant la validation : valider à nouveau.'); return; }
      state.validated = key(snapshot);
      validated.textContent = `${payload.files.length} fichier(s) validé(s), dont ${payload.modified.length} modifié(s)`
        + (payload.modified.length ? ` : ${payload.modified.join(', ')}.` : '.');
      setStatus('Contenus validés : comparer avec la destination avant toute écriture.');
    }));

    async function browseTo(path) {
      const {response, payload} = await post('/api/destination/browse', path ? {path} : {});
      if (!response.ok || !payload.ok) { setStatus(`Parcours refusé : ${payload.error || 'dossier refusé'}`); return; }
      state.writeRoot = payload.root;
      rootLabel.textContent = payload.root;
      destination.value = payload.path;
      up.disabled = payload.parent === null;
      up.dataset.parent = payload.parent || '';
      dirs.replaceChildren(...payload.directories.map(name => {
        const button = el('button', {type: 'button', 'data-dir': name, text: name});
        button.addEventListener('click', () => browseTo(`${payload.path}/${name}`));
        return el('li', {}, button);
      }));
      resetComparison();
      update();
    }

    browse.addEventListener('click', () => browseTo(destination.value.trim()));
    up.addEventListener('click', () => browseTo(up.dataset.parent));
    destination.addEventListener('input', () => { resetComparison(); update(); });

    function body(extra) {
      const snapshot = options.snapshot();
      return Object.assign({config: snapshot.config, files: snapshot.files, destination: destination.value.trim()}, extra);
    }

    compare.addEventListener('click', () => run('Comparaison avec la destination (aucune écriture)…', async () => {
      if (!current()) { invalidate('Contenus modifiés : valider à nouveau.'); return; }
      resetComparison();
      const name = options.snapshot().config.name;
      if (!destination.value.trim() && state.writeRoot) destination.value = `${state.writeRoot}/${name}`;
      const {response, payload} = await post('/api/write/compare', body({}));
      if (!response.ok || !payload.ok) {
        if (payload.diagnostics && payload.diagnostics.length) options.onDiagnostics(payload.diagnostics, 'comparaison');
        setStatus(`Comparaison refusée : ${payload.error || 'destination refusée'}`);
        return;
      }
      const previous = state.assessment;
      if (payload.unverified && (!previous || payload.unverified.token !== previous.token
          || payload.unverified.items.length !== previous.items.length)) {
        refreshAssessment(payload.unverified, 'Les contrôles régénérés ont changé : relire la liste et confirmer à nouveau.');
        return;
      }
      state.comparison = payload;
      renderComparison();
      setStatus('Comparaison terminée : aucune écriture effectuée.');
    }));

    function renderComparison() {
      const c = state.comparison;
      comparison.hidden = false;
      const s = c.summary;
      summary.textContent = `${c.destination.exists ? 'Dossier existant' : 'Nouveau dossier'}${c.destination.writable ? '' : ' (NON accessible en écriture)'} : `
        + `${s.new} nouveau(x), ${s.identical} identique(s), ${s.conflict} conflit(s), ${s.blocked} bloqué(s).`;
      entries.replaceChildren(...c.entries.map(entry => {
        const resolution = state.resolutions[entry.path];
        const label = entry.status === 'conflict'
          ? (resolution ? `conflit : ${RESOLUTION_LABELS[resolution.action]}` : 'conflit : à décider') : STATUS_LABELS[entry.status];
        const button = el('button', {type: 'button', class: 'mono', disabled: entry.status !== 'conflict',
          'aria-current': entry.path === state.conflictPath ? 'true' : null, text: entry.path});
        button.addEventListener('click', () => selectConflict(entry.path));
        return el('li', {'data-entry': entry.path, 'data-status': entry.status}, button,
          el('span', {class: `tag wf-${entry.status}`, text: label}));
      }));
      update();
    }

    function selectConflict(path) {
      const entry = state.comparison.entries.find(e => e.path === path);
      state.conflictPath = path;
      conflict.hidden = false;
      conflictTitle.textContent = path;
      reason.textContent = entry.reason || (entry.auto_merge !== null
        ? 'Une fusion automatique sans conflit est disponible. Relire le diff avant de la valider.'
        : entry.base_available ? 'Les changements se chevauchent : une résolution manuelle est requise.'
          : 'Aucune base commune fiable : conserver, remplacer ou fusionner manuellement.');
      const overlaps = (entry.merge_conflicts || []).map(c =>
        `Lignes ${c.base_start}-${Math.max(c.base_start, c.base_end)} de la base :\n  local    : ${c.current.trimEnd() || '(supprimé)'}\n  généré   : ${c.generated.trimEnd() || '(supprimé)'}`);
      diff.textContent = (overlaps.length ? `Conflits à résoudre manuellement :\n${overlaps.join('\n')}\n\n` : '')
        + (entry.diff || '(diff indisponible : contenu binaire ou trop volumineux)');
      choices.querySelector('input[value="merge"]').disabled = !entry.mergeable;
      choices.querySelector('input[value="auto"]').disabled = entry.auto_merge === null;
      const chosen = state.resolutions[path];
      choices.querySelectorAll('input').forEach(radio => { radio.checked = Boolean(chosen) && radio.value === chosen.action; });
      mergeBox.hidden = !chosen || chosen.action !== 'merge';
      merge.value = chosen && chosen.action === 'merge' ? chosen.content : (entry.existing || '');
      renderComparison();
      diff.focus();
    }

    function resolutionChanged() {
      const checked = choices.querySelector('input:checked');
      if (!state.conflictPath || !checked) return;
      state.resolutions[state.conflictPath] = checked.value === 'merge'
        ? {action: 'merge', content: merge.value} : {action: checked.value};
      mergeBox.hidden = checked.value !== 'merge';
      confirm.checked = false; // toute nouvelle decision doit etre reconfirmee
      renderComparison();
    }

    merge.addEventListener('input', () => {
      const chosen = state.resolutions[state.conflictPath];
      if (chosen && chosen.action === 'merge') { chosen.content = merge.value; confirm.checked = false; update(); }
    });
    confirm.addEventListener('change', update);

    function renderReport(data, title) {
      report.replaceChildren(el('p', {class: data.status === 'ok' ? 'wf-ok' : 'wf-error', text: title}));
      if (data.backup) report.append(el('p', {text: `Sauvegarde des fichiers remplacés : ${data.destination}/${data.backup} (voir MANIFEST.json pour restaurer).`}));
      if (data.merge_bases) report.append(el('p', {id: 'wf-merge-bases', text: `Bases de fusion à trois voies : ${data.merge_bases}.`}));
      if (data.summary) {
        const s = data.summary;
        report.append(el('p', {text: `${s.created} créé(s), ${s.replaced} remplacé(s), ${s.merged} fusionné(s), ${s.kept} conservé(s), ${s.identical} identique(s).`}));
      }
      report.append(el('ul', {id: 'wf-operations'}, ...(data.operations || []).map(op =>
        el('li', {'data-op': op.action, text: `${OPERATION_LABELS[op.action] || op.action} : ${op.path}`}))));
      const journal = data.journal || {};
      if (journal.non_verifie && journal.non_verifie.length) {
        report.append(el('p', {text: 'Avertissements (à relire, non bloquants) :'}),
          el('ul', {}, ...journal.non_verifie.map(message => el('li', {class: 'wf-warning', text: message}))));
      }
      if (journal.confirmations && journal.confirmations.length) {
        report.append(el('p', {text: 'Éléments acceptés en connaissance de cause (statut inchangé) :'}),
          el('ul', {id: 'wf-confirmations'}, ...journal.confirmations.map(item =>
            el('li', {class: 'wf-warning', text: `${item.status} (confirmé) : ${item.name} - ${item.reason}`}))));
      }
      for (const message of data.restore_errors || []) report.append(el('p', {class: 'wf-error', text: `Restauration incomplète : ${message}`}));
    }

    write.addEventListener('click', () => {
      if (!current() || !state.comparison) { invalidate('Contenus modifiés : valider à nouveau.'); return; }
      const {summary: s, destination: target} = state.comparison;
      const replaced = Object.values(state.resolutions).filter(r => r.action !== 'keep').length;
      if (!window.confirm(`Écrire dans ${target.path} : ${s.new} création(s), ${replaced} remplacement(s) ou fusion(s) sauvegardé(s) ? Cette action modifie le dossier.`)) return;
      run('Contrôles répétés par le serveur puis écriture…', async () => {
        const {response, payload} = await post('/api/write/apply', body({token: state.comparison.token,
          decisions: state.resolutions, confirm: true, acknowledge: acknowledgement()}));
        if (response.ok && payload.ok) {
          renderReport(payload.report, 'Écriture terminée.');
          resetComparison();
          setStatus(`Fichiers écrits dans ${target.path}.`);
          return;
        }
        if (response.status === 409 && payload.confirmation_required) {
          refreshAssessment(payload.unverified, payload.error);
          return;
        }
        resetComparison();
        if (payload.report) {
          renderReport(payload.report, response.status === 409 ? 'Écriture annulée, état précédent restauré.'
            : 'Écriture interrompue : modifications annulées.');
        }
        if (payload.diagnostics && payload.diagnostics.length) options.onDiagnostics(payload.diagnostics, 'écriture');
        setStatus(`${response.status === 409 ? 'Écriture refusée (périmée)' : 'Écriture refusée'} : ${payload.error || 'erreur inconnue'}`);
      });
    });

    browseTo('').catch(error => setStatus(`Racine d'écriture indisponible : ${error.message}`));
    update();

    return {
      // Nouveau plan : nouvelle evaluation NON VERIFIE ; une confirmation anterieure ne vaut plus.
      planChanged(plan) {
        const next = plan ? plan.unverified || null : null;
        const same = state.assessment && next && state.assessment.token === next.token
          && state.assessment.items.length === next.items.length;
        if (!same) { state.assessment = next; renderUnverified(); }
        invalidate('Configuration modifiée : valider à nouveau les contenus.');
      },
      invalidate,
      state,
    };
  }

  window.ForgeWorkflow = {create};
}());
