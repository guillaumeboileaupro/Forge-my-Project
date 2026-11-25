// Skills externes du parcours v2 (E18b), meme contrat que l'interface actuelle (T10) : recherche
// explicite sur GitHub, decision d'approbation ou de refus apres examen, verification des approbations.
// Le navigateur ne decide pas de la confiance : il transmet les approbations (depot, commit, empreinte),
// que le serveur revalide et recontrole a la copie. Aucun skill n'est copie ni execute ici.
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

  const key = item => [item.repository, item.path, item.name, item.commit].join('|');
  const TAG = {PASS: 'ok', FAIL: 'error'};

  // Lien d'examen du contenu au commit exact (navigation seulement, jamais une ressource chargee).
  function reviewLink(item) {
    const path = [item.path, item.name].filter(part => part && part !== '.').join('/');
    const href = `https://github.com/${encodeURI(item.repository)}/tree/${encodeURIComponent(item.commit)}/${encodeURI(path)}`;
    return el('a', {href, target: '_blank', rel: 'noopener noreferrer', text: `Examiner « ${item.name} » sur GitHub`});
  }

  function facts(rows) {
    return el('dl', {class: 'summary'}, ...rows.flatMap(([term, value]) => [el('dt', {text: term}), el('dd', {text: value})]));
  }

  // options : config() -> configuration courante ; onChange(approbations) ; status(message).
  function create(root, options) {
    const state = {approvals: [], candidates: [], decisions: {}, checks: {}, busy: false};

    const search = el('button', {type: 'button', id: 'skills-search', text: 'Rechercher des skills (réseau)'});
    const refresh = el('button', {type: 'button', id: 'skills-refresh', text: 'Relancer sans le cache'});
    const notes = el('ul', {id: 'skills-notes', class: 'hints'});
    const candidates = el('ul', {id: 'skills-candidates', class: 'skill-list', 'aria-label': 'Skills candidats'});
    const empty = el('p', {id: 'skills-empty', class: 'muted', text: 'Aucun skill externe approuvé.'});
    const approved = el('ul', {id: 'skills-approved', class: 'skill-list', 'aria-labelledby': 'skills-approved-title'});
    const verify = el('button', {type: 'button', id: 'skills-verify', text: 'Vérifier les approbations (réseau)', disabled: true});
    const status = el('p', {id: 'skills-status', class: 'muted', role: 'status'});

    root.replaceChildren(
      el('p', {class: 'muted hint', text: "Recherche explicite sur GitHub (catalogues reconnus, recherche de code si la CLI gh est connectée). "
        + "Aucun skill n'est copié sans votre approbation ; scripts, binaires et exécutables ne sont jamais copiés ni exécutés."}),
      el('div', {class: 'answers-actions'}, search, refresh), notes, candidates,
      el('h3', {class: 'box-title', id: 'skills-approved-title', text: 'Skills approuvés'}), empty, approved, verify,
      el('p', {class: 'muted hint', text: "Les approbations (dépôt, commit et empreinte) sont conservées dans le brouillon, les profils et l'export JSON. "
        + 'Un skill modifié depuis son approbation est refusé à la génération.'}),
      status);

    const setStatus = message => { status.textContent = message; options.status(message); };

    function changed() {
      render();
      options.onChange(state.approvals.map(item => Object.assign({}, item)));
    }

    function decide(candidate, decision) {
      const id = key(candidate);
      if (decision === 'approved') {
        const clash = state.approvals.find(item => item.name === candidate.name && key(item) !== id);
        if (clash) {
          setStatus(`Un skill nommé « ${candidate.name} » est déjà approuvé (${clash.repository}) : retirer d'abord cette approbation.`);
          return;
        }
        if (!candidate.recognized && !window.confirm(`Source non reconnue (${candidate.repository}). Avez-vous examiné tout le contenu de « ${candidate.name} » ?`)) return;
        state.approvals.push(Object.assign({}, candidate.approval));
        state.checks[id] = {status: 'approuvé', message: 'Approuvé après examen dans cette session'};
        setStatus(`Skill « ${candidate.name} » approuvé au commit ${candidate.commit.slice(0, 12)}.`);
      } else {
        state.approvals = state.approvals.filter(item => key(item) !== id);
        delete state.checks[id];
        setStatus(`Skill « ${candidate.name} » refusé : il ne sera pas copié.`);
      }
      state.decisions[id] = decision;
      changed();
    }

    function renderCandidates() {
      candidates.replaceChildren(...state.candidates.map(candidate => {
        const id = key(candidate);
        const decision = state.approvals.some(item => key(item) === id) ? 'approved' : state.decisions[id];
        const approve = el('button', {type: 'button', 'data-action': 'approve', 'aria-label': `Approuver ${candidate.name}`,
                                      text: 'Approuver', disabled: decision === 'approved'});
        const refuse = el('button', {type: 'button', 'data-action': 'refuse', 'aria-label': `Refuser ${candidate.name}`,
                                     text: 'Refuser', disabled: decision === 'refused'});
        approve.addEventListener('click', () => decide(candidate, 'approved'));
        refuse.addEventListener('click', () => decide(candidate, 'refused'));
        const rows = [['Description', candidate.description || '(aucune)'],
          ['Provenance', `${candidate.source} : ${candidate.repository}/${candidate.path}`], ['Commit', candidate.commit],
          ['Empreinte', candidate.digest], ['Fichiers copiés', candidate.copied_files.join(', ') || '(aucun)'],
          ['Fichiers ignorés', candidate.ignored_files.join(', ') || '(aucun)']];
        if (candidate.notes.length) rows.push(['À relire', candidate.notes.join(' ; ')]);
        const label = decision === 'approved' ? 'Approuvé' : decision === 'refused' ? 'Refusé' : 'En attente de décision';
        return el('li', {class: `skill ${decision || ''}`.trim(), 'data-skill': candidate.name},
          el('p', {class: 'skill-title'}, el('strong', {text: candidate.name}), ' ',
            el('span', {class: `tag ${candidate.recognized ? 'ok' : 'warning'}`,
                        text: candidate.recognized ? 'source reconnue' : 'source non reconnue'})),
          facts(rows), reviewLink(candidate), el('div', {class: 'answers-actions'}, approve, refuse),
          el('p', {class: 'muted decision', text: label}));
      }));
    }

    function renderApprovals() {
      approved.replaceChildren(...state.approvals.map(approval => {
        const check = state.checks[key(approval)] || {status: 'non vérifiée', message: ''};
        const rows = [['Dépôt', `${approval.repository}/${approval.path}`], ['Commit', approval.commit], ['Empreinte', approval.digest]];
        if (check.message) rows.push(['Contrôle', check.message]);
        const withdraw = el('button', {type: 'button', 'aria-label': `Retirer l'approbation de ${approval.name}`, text: "Retirer l'approbation"});
        withdraw.addEventListener('click', () => decide(approval, 'refused'));
        return el('li', {class: 'skill', 'data-approved': approval.name},
          el('p', {class: 'skill-title'}, el('strong', {text: approval.name}), ' ',
            el('span', {class: `tag ${TAG[check.status] || 'warning'}`, 'data-status': check.status, text: check.status})),
          facts(rows), reviewLink(approval), withdraw);
      }));
      empty.hidden = state.approvals.length > 0;
      verify.disabled = state.busy || state.approvals.length === 0;
    }

    function render() {
      search.disabled = state.busy;
      refresh.disabled = state.busy;
      renderCandidates();
      renderApprovals();
    }

    async function run(label, action) {
      state.busy = true;
      render();
      setStatus(label);
      try {
        await action();
      } catch (error) {
        setStatus(`Erreur : ${error.message}`);
      } finally {
        state.busy = false;
        render();
      }
    }

    async function find(again) {
      await run('Recherche de skills en cours (GitHub)…', async () => {
        const config = Object.assign(options.config(), {external_skills: []});
        const {response, payload} = await post('/api/skills/search', {config, refresh: again});
        if (!response.ok || !payload.ok) { setStatus(`Recherche impossible : ${payload.error || 'recherche refusée'}`); return; }
        state.candidates = payload.candidates;
        const cache = payload.cache || {};
        const cached = cache.hit ? [`Résultats du cache (recherche faite il y a ${Math.round(cache.age_seconds / 60)} min) : `
          + '« Relancer sans le cache » pour interroger GitHub. La copie relit toujours GitHub au commit approuvé.'] : [];
        notes.replaceChildren(...cached.concat(payload.notes).map(note => el('li', {text: note})));
        setStatus(`${payload.candidates.length} skill(s) candidat(s) : examiner puis approuver ou refuser.`);
      });
    }

    search.addEventListener('click', () => find(false));
    refresh.addEventListener('click', () => find(true));
    verify.addEventListener('click', () => run('Vérification des approbations (GitHub)…', async () => {
      const {response, payload} = await post('/api/skills/verify', {approvals: state.approvals});
      if (!response.ok) { setStatus(`Vérification impossible : ${payload.error || 'vérification refusée'}`); return; }
      for (const check of payload.checks) {
        state.checks[key(check)] = {status: check.status,
          message: check.upstream_message ? `${check.message}. ${check.upstream_message}` : check.message};
      }
      setStatus(payload.ok ? 'Approbations vérifiées : contenus inchangés.'
        : "Au moins une approbation n'est pas vérifiée ou le skill a changé : retirer ou examiner à nouveau.");
    }));

    render();
    return {
      node: root,
      // Approbations chargees (brouillon, import, profil) : non verifiees depuis le chargement.
      setApprovals(approvals) {
        state.approvals = approvals.map(item => Object.assign({}, item));
        state.checks = {};
        for (const item of state.approvals) state.checks[key(item)] = {status: 'non vérifiée depuis le chargement', message: ''};
        render();
      },
      reset() {
        state.candidates = [];
        state.decisions = {};
        notes.replaceChildren();
        status.textContent = '';
        this.setApprovals([]);
      },
    };
  }

  window.ForgeSkills = {create};
}());
