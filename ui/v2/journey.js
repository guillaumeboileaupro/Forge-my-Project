// Parcours v2 (E16) : questionnaire progressif et conditionnel, apercu du plan reel,
// arbre et diagramme synchronises par un meme `selectedPath`.
// E17a : editeur (editor.js), panneau diagnostics (diagnostics.js) et flux securises (workflow.js).
// Le serveur reste l'autorite (prerequis, conflits, versions, diagnostics) : ce script
// n'affiche que des choix et des relations fournis par /api/catalog et /api/plan.
'use strict';

const NAME = /^[a-z][a-z0-9-]{1,48}[a-z0-9]$/;
const DEBOUNCE_MS = 350;

const state = {
  catalog: null,
  answers: {name: '', description: '', project_type: '', technologies: [], versions: {}, agents: [],
            security: 'strict', mcp_servers: []},
  step: 0,
  validation: 'idle', // idle | running | valid | invalid | stale
  requestSeq: 0,
  plan: null, // dernier /api/plan applique
  selectedPath: null,
  timer: null,
  edits: {}, // chemin -> texte edite (seulement s'il differe du rendu genere)
  editBase: {}, // chemin -> rendu genere au moment de l'edition
};

let editor = null;
let diagnostics = null;
let workflow = null;
let fileTabs = null; // onglets des fichiers ouverts (E17)

const $ = selector => document.querySelector(selector);

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

function svg(tag, attributes = {}) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  return node;
}

// --- Regles d'affichage (deduites du catalogue, jamais d'une supposition) ----------
function tech(id) {
  return state.catalog.technologies.find(item => item.id === id);
}

function selected(id) {
  return state.answers.technologies.includes(id);
}

// Une technologie est proposee si chaque groupe de prerequis est satisfait par la selection.
function available(item) {
  return item.requires.every(group => group.some(selected));
}

function conflictWith(item) {
  return state.answers.technologies.find(id => id !== item.id
    && (item.conflicts.includes(id) || (tech(id) && tech(id).conflicts.includes(item.id))));
}

function versioned() {
  return state.answers.technologies.map(tech).filter(item => item && item.versions.length);
}

function mcpChoices() {
  return state.catalog.mcp_servers.filter(server => server.project_types.includes(state.answers.project_type));
}

// Retire les reponses devenues invalides (question masquee) ; retourne les libelles retires.
function prune() {
  const removed = [];
  let changed = true;
  while (changed) {
    changed = false;
    for (const id of [...state.answers.technologies]) {
      const item = tech(id);
      if (!item || !available(item)) {
        state.answers.technologies = state.answers.technologies.filter(other => other !== id);
        removed.push(item ? item.name : id);
        changed = true;
      }
    }
  }
  for (const id of Object.keys(state.answers.versions)) {
    const item = tech(id);
    if (!selected(id) || !item || !item.versions.includes(state.answers.versions[id])) delete state.answers.versions[id];
  }
  for (const item of versioned()) {
    if (!state.answers.versions[item.id]) state.answers.versions[item.id] = item.preferred || item.versions[0];
  }
  const allowed = new Set(mcpChoices().map(server => server.id));
  const droppedMcp = state.answers.mcp_servers.filter(id => !allowed.has(id));
  state.answers.mcp_servers = state.answers.mcp_servers.filter(id => allowed.has(id));
  return removed.concat(droppedMcp.map(id => `serveur MCP ${id}`));
}

function config() {
  const answers = state.answers;
  return {
    schema_version: 1, name: answers.name, description: answers.description, project_type: answers.project_type,
    architecture: '', technologies: [...answers.technologies], versions: {...answers.versions},
    agents: [...answers.agents], security: answers.security, options: {mcp: answers.mcp_servers.length > 0},
    mcp_servers: [...answers.mcp_servers], external_skills: [],
  };
}

// --- Etapes ---------------------------------------------------------------------
const CATEGORY_STEPS = {langages: ['language', 'runtime'], outils: ['framework', 'testing', 'quality', 'security', 'deployment']};

const STEPS = [
  {id: 'projet', title: 'Projet', help: 'Nom, type et description du projet.',
   applicable: () => true,
   complete: () => NAME.test(state.answers.name) && Boolean(state.answers.project_type),
   render: renderProject},
  {id: 'langages', title: 'Langages et environnement', help: 'Au moins un langage.',
   applicable: () => true,
   complete: () => state.answers.technologies.some(id => tech(id) && tech(id).category === 'language'),
   render: () => renderCategories(CATEGORY_STEPS.langages)},
  {id: 'outils', title: 'Outils', help: 'Proposés selon les langages choisis ; le serveur confirme les compatibilités.',
   applicable: () => state.answers.technologies.length > 0,
   complete: () => true,
   render: () => renderCategories(CATEGORY_STEPS.outils)},
  {id: 'versions', title: 'Versions', help: 'Versions supportées par le catalogue pour les technologies choisies.',
   applicable: () => versioned().length > 0,
   complete: () => true,
   render: renderVersions},
  {id: 'agents', title: 'Agents et sécurité', help: 'Au moins un agent ; niveau de sécurité.',
   applicable: () => true,
   complete: () => state.answers.agents.length > 0,
   render: renderAgents},
  {id: 'mcp', title: 'Serveurs MCP', help: 'Optionnels, proposés selon le type de projet.',
   applicable: () => mcpChoices().length > 0,
   complete: () => true,
   render: renderMcp},
];

function stepStatus(step) {
  if (!step.applicable()) return 'skipped';
  return step.complete() ? 'complete' : 'incomplete';
}

const STATUS_LABEL = {complete: 'complète', incomplete: 'à compléter', skipped: 'sans objet'};

function renderSteps() {
  const list = $('#step-list');
  list.replaceChildren();
  STEPS.forEach((step, index) => {
    const status = stepStatus(step);
    const button = el('button', {type: 'button', 'data-step': step.id, 'aria-current': index === state.step ? 'step' : null,
                                 disabled: status === 'skipped'},
      el('span', {class: 'step-name', text: `${index + 1}. ${step.title}`}),
      el('span', {class: `step-state state-${status}`, text: STATUS_LABEL[status]}));
    button.addEventListener('click', () => goTo(index, true));
    list.append(el('li', {}, button));
  });
  const applicable = STEPS.filter(step => step.applicable());
  const done = applicable.filter(step => step.complete()).length;
  $('#progress').max = applicable.length;
  $('#progress').value = done;
  $('#progress-label').textContent = `${done} étape(s) complète(s) sur ${applicable.length} applicable(s)`;
  renderSummary();
}

// Onglet « Résumé » de l'apercu (E15) : reponses courantes, texte seulement.
function renderSummary() {
  const answers = state.answers;
  const names = (ids, list) => ids.map(id => (list.find(item => item.id === id) || {name: id}).name).join(', ') || '—';
  const type = state.catalog.project_types.find(option => option.id === answers.project_type);
  const rows = [
    ['Projet', answers.name || '—'],
    ['Type', type ? type.label : '—'],
    ['Technologies', names(answers.technologies, state.catalog.technologies)],
    ['Versions', Object.entries(answers.versions).map(([id, version]) => `${id} ${version}`).join(', ') || '—'],
    ['Agents', names(answers.agents, state.catalog.agents)],
    ['Sécurité', answers.security || '—'],
    ['Serveurs MCP', answers.mcp_servers.join(', ') || '—'],
    ['Fichiers du plan', state.plan ? String(state.plan.graph.files.length) : '—'],
  ];
  $('#summary').replaceChildren(...rows.flatMap(([term, value]) => [el('dt', {text: term}), el('dd', {text: value})]));
}

function goTo(index, focus) {
  if (index < 0 || index >= STEPS.length || !STEPS[index].applicable()) return;
  state.step = index;
  renderStep();
  renderSteps();
  if (focus) $('#step-title').focus(); // action explicite de l'utilisateur
}

function move(delta) {
  let index = state.step + delta;
  while (index >= 0 && index < STEPS.length && !STEPS[index].applicable()) index += delta;
  goTo(index, true);
}

function renderStep() {
  const step = STEPS[state.step];
  $('#step-title').textContent = `Étape ${state.step + 1} : ${step.title}`;
  $('#step-help').textContent = step.help;
  const body = $('#step-body');
  body.replaceChildren(step.render());
  let previous = state.step - 1;
  while (previous >= 0 && !STEPS[previous].applicable()) previous -= 1;
  let next = state.step + 1;
  while (next < STEPS.length && !STEPS[next].applicable()) next += 1;
  $('#prev').disabled = previous < 0;
  $('#next').disabled = next >= STEPS.length;
}

// Re-rendre une etape ne doit pas deplacer le focus : on le rend au meme controle.
function focusKey(node) {
  if (!node || !$('#step-body').contains(node)) return null;
  return node.id ? `#${CSS.escape(node.id)}` : `input[name="${CSS.escape(node.name || '')}"][value="${CSS.escape(node.value)}"]`;
}

function changed(rerender = true) {
  if (workflow) workflow.invalidate('Configuration modifiée : valider à nouveau les contenus.');
  const removed = prune();
  $('#step-notice').textContent = removed.length
    ? `Retiré car la condition n'est plus remplie : ${removed.join(', ')}.` : '';
  if (rerender) {
    const key = focusKey(document.activeElement);
    renderStep();
    const again = key && $('#step-body').querySelector(key);
    if (again) again.focus();
  }
  renderSteps();
  schedulePlan();
}

function field(label, control, hint) {
  const id = control.id;
  return el('div', {class: 'field'}, el('label', {for: id, text: label}), control,
    hint ? el('p', {class: 'muted hint', id: `${id}-hint`, text: hint}) : '');
}

function renderProject() {
  const name = el('input', {id: 'q-name', type: 'text', value: state.answers.name, autocomplete: 'off',
                            'aria-describedby': 'q-name-hint', required: true});
  name.addEventListener('input', () => { state.answers.name = name.value.trim(); changed(false); });
  const type = el('fieldset', {class: 'choices'}, el('legend', {text: 'Type de projet'}));
  for (const option of state.catalog.project_types) {
    const input = el('input', {type: 'radio', name: 'q-type', value: option.id, checked: state.answers.project_type === option.id});
    input.addEventListener('change', () => { state.answers.project_type = option.id; changed(); });
    type.append(el('label', {class: 'choice'}, input, ` ${option.label}`));
  }
  const description = el('textarea', {id: 'q-description', rows: 3});
  description.value = state.answers.description;
  description.addEventListener('input', () => { state.answers.description = description.value; changed(false); });
  return el('div', {},
    field('Nom du projet', name, '3 à 50 caractères : minuscules, chiffres et tirets, commence par une lettre.'),
    type, field('Description (facultative)', description));
}

function techChoice(item) {
  const conflict = conflictWith(item);
  const input = el('input', {type: 'checkbox', name: 'q-tech', value: item.id, checked: selected(item.id),
                             disabled: Boolean(conflict) && !selected(item.id)});
  input.addEventListener('change', () => {
    state.answers.technologies = input.checked
      ? [...state.answers.technologies, item.id] : state.answers.technologies.filter(id => id !== item.id);
    changed();
  });
  const label = el('label', {class: 'choice'}, input, ` ${item.name}`,
    item.source === 'local' ? el('span', {class: 'tag', text: 'catalogue personnel'}) : '');
  const notes = [];
  if (conflict && !selected(item.id)) notes.push(`incompatible avec ${tech(conflict).name}`);
  return el('div', {class: 'tech'}, label, el('p', {class: 'muted hint', text: [item.description, ...notes].join(' · ')}));
}

function renderCategories(categories) {
  const box = el('div', {});
  for (const id of categories) {
    const category = state.catalog.categories.find(item => item.id === id);
    const items = state.catalog.technologies.filter(item => item.category === id && available(item));
    if (!category || !items.length) continue; // question sans objet pour la selection courante
    const set = el('fieldset', {class: 'choices', 'data-category': id},
      el('legend', {text: `${category.label} (${category.min} à ${category.max})`}));
    items.forEach(item => set.append(techChoice(item)));
    box.append(set);
  }
  if (!box.children.length) box.append(el('p', {class: 'muted', text: 'Aucun choix disponible pour la sélection courante.'}));
  return box;
}

function renderVersions() {
  const box = el('div', {});
  for (const item of versioned()) {
    const select = el('select', {id: `q-version-${item.id}`});
    for (const version of item.versions) {
      select.append(el('option', {value: version, selected: state.answers.versions[item.id] === version,
                                  text: version + (version === item.preferred ? ' (recommandée)' : '')}));
    }
    select.addEventListener('change', () => { state.answers.versions[item.id] = select.value; changed(false); });
    box.append(field(item.name, select));
  }
  return box;
}

function renderAgents() {
  const agents = el('fieldset', {class: 'choices'}, el('legend', {text: 'Agents'}));
  for (const agent of state.catalog.agents) {
    const input = el('input', {type: 'checkbox', name: 'q-agent', value: agent.id, checked: state.answers.agents.includes(agent.id)});
    input.addEventListener('change', () => {
      state.answers.agents = input.checked ? [...state.answers.agents, agent.id]
        : state.answers.agents.filter(id => id !== agent.id);
      changed();
    });
    agents.append(el('label', {class: 'choice'}, input, ` ${agent.name}`));
  }
  const security = el('fieldset', {class: 'choices'}, el('legend', {text: 'Niveau de sécurité'}));
  for (const level of state.catalog.security_levels) {
    const input = el('input', {type: 'radio', name: 'q-security', value: level, checked: state.answers.security === level});
    input.addEventListener('change', () => { state.answers.security = level; changed(); });
    security.append(el('label', {class: 'choice'}, input, ` ${level}`));
  }
  return el('div', {}, agents, security);
}

function renderMcp() {
  const set = el('fieldset', {class: 'choices'}, el('legend', {text: 'Serveurs MCP (aucun par défaut)'}));
  for (const server of mcpChoices()) {
    const input = el('input', {type: 'checkbox', name: 'q-mcp', value: server.id, checked: state.answers.mcp_servers.includes(server.id)});
    input.addEventListener('change', () => {
      state.answers.mcp_servers = input.checked ? [...state.answers.mcp_servers, server.id]
        : state.answers.mcp_servers.filter(id => id !== server.id);
      changed();
    });
    set.append(el('div', {class: 'tech'}, el('label', {class: 'choice'}, input, ` ${server.name}`),
      el('p', {class: 'muted hint', text: `${server.need} · permissions : ${server.permissions.join(', ') || 'aucune'}`})));
  }
  return set;
}

// --- Apercu : requetes ordonnees, reponse ancienne ignoree --------------------------
function setValidation(status, message) {
  state.validation = status;
  const node = $('#validation');
  node.dataset.state = status;
  node.textContent = message;
}

function schedulePlan() {
  clearTimeout(state.timer);
  if (state.plan) setValidation('stale', 'Aperçu périmé : mise à jour après la saisie.');
  if (!NAME.test(state.answers.name)) {
    state.requestSeq += 1; // toute reponse en vol devient ancienne
    setValidation('idle', "Renseigner un nom de projet valide pour calculer l'aperçu.");
    return;
  }
  state.timer = setTimeout(requestPlan, DEBOUNCE_MS);
}

async function requestPlan() {
  const seq = ++state.requestSeq;
  setValidation('running', "Calcul de l'aperçu par le serveur…");
  let response;
  let payload;
  try {
    response = await fetch('/api/plan', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                         body: JSON.stringify({config: config()})});
    payload = await response.json();
  } catch (error) {
    if (seq === state.requestSeq) setValidation('invalid', `Aperçu indisponible : ${error.message}`);
    return;
  }
  if (seq !== state.requestSeq) return; // une saisie plus recente a deja relance le calcul
  if (!response.ok || !payload.graph) {
    diagnostics.update(payload.diagnostics || [], 'aperçu');
    $('#alerts').textContent = payload.error || 'Configuration refusée par le serveur.';
    setValidation('invalid', 'Configuration incomplète ou invalide : voir le message.');
    return;
  }
  $('#alerts').textContent = '';
  applyPlan(payload);
}

function applyPlan(payload) {
  state.plan = payload;
  // Une edition ne survit que si le rendu genere de ce fichier n'a pas change : jamais de fusion silencieuse.
  const dropped = Object.keys(state.edits).filter(path => payload.contents[path] !== state.editBase[path]);
  dropped.forEach(path => { delete state.edits[path]; delete state.editBase[path]; });
  diagnostics.update(payload.diagnostics, 'aperçu');
  renderTree();
  renderDiagram();
  const notices = [];
  if (dropped.length) notices.push(`Modification retirée, le fichier généré a changé : ${dropped.join(', ')}.`);
  if (state.selectedPath && !payload.graph.files.some(file => file.path === state.selectedPath)) {
    state.selectedPath = null;
    notices.push("Le fichier sélectionné n'existe plus dans ce plan.");
  }
  if (notices.length) $('#step-notice').textContent = notices.join(' ');
  fileTabs.retain(payload.graph.files.map(file => file.path)); // onglets limites au plan courant
  select(state.selectedPath, false);
  const errors = payload.diagnostics.filter(item => item.severity === 'error').length;
  setValidation(errors ? 'invalid' : 'valid',
    `Aperçu à jour : ${payload.graph.files.length} fichier(s), ${payload.graph.rules.length} règle(s)`
    + (errors ? `, ${errors} erreur(s) bloquante(s).` : '.'));
  workflow.planChanged(payload);
  renderSummary();
  performance.mark('forge-plan'); // E18a : apercu applique
}

// --- Fichiers edites ---------------------------------------------------------------
function currentFiles() {
  return state.plan ? Object.assign({}, state.plan.contents, state.edits) : {};
}

// Etat utilisable par les flux securises : apercu a jour et sans erreur bloquante.
function snapshot() {
  if (!state.plan || state.validation !== 'valid') return null;
  return {config: config(), files: currentFiles()};
}

function edited(path, value) {
  const generated = state.plan.contents[path];
  if (value === generated) { delete state.edits[path]; delete state.editBase[path]; } else {
    state.edits[path] = value;
    state.editBase[path] = generated;
  }
  markModified();
  workflow.invalidate('Fichier modifié : valider à nouveau les contenus.');
}

function markModified() {
  document.querySelectorAll('#tree [data-path]').forEach(button => {
    const changed = button.dataset.path in state.edits;
    button.classList.toggle('modified', changed);
    button.setAttribute('aria-label', changed ? `${button.dataset.path} (modifié)` : button.dataset.path);
  });
  if (fileTabs) fileTabs.paths().forEach(path => fileTabs.setModified(path, path in state.edits));
}

// --- Diagnostics : cible de navigation deduite du code et du sujet fournis par le serveur ----
function stepOf(category) {
  return Object.keys(CATEGORY_STEPS).find(step => CATEGORY_STEPS[step].includes(category));
}

function diagnosticTarget(item) {
  const subject = item.subject || '';
  const code = item.code || '';
  if (subject && state.plan && Object.prototype.hasOwnProperty.call(state.plan.contents, subject)) {
    return {path: subject, label: subject};
  }
  const technology = subject && state.catalog ? tech(subject) : null;
  if (technology && code.startsWith('version-')) {
    return {step: 'versions', selector: `#${CSS.escape(`q-version-${subject}`)}`, label: `version de ${technology.name}`};
  }
  if (technology && stepOf(technology.category)) {
    return {step: stepOf(technology.category), selector: `input[name="q-tech"][value="${CSS.escape(subject)}"]`, label: technology.name};
  }
  if (code.startsWith('mcp-') && subject) {
    return {step: 'mcp', selector: `input[name="q-mcp"][value="${CSS.escape(subject)}"]`, label: `serveur MCP ${subject}`};
  }
  const category = subject && state.catalog ? state.catalog.categories.find(entry => entry.id === subject) : null;
  if (category && stepOf(category.id)) {
    return {step: stepOf(category.id), selector: `fieldset[data-category="${CSS.escape(category.id)}"]`, label: category.label};
  }
  if (code === 'description-empty') return {step: 'projet', selector: '#q-description', label: 'description'};
  return null; // aucun champ associe : pas de lien invente
}

function navigate(target) {
  if (target.path) {
    if (select(target.path, true)) editor.focus();
    return;
  }
  const index = STEPS.findIndex(step => step.id === target.step);
  if (index < 0 || !STEPS[index].applicable()) {
    $('#step-notice').textContent = `Étape sans objet pour la sélection courante : ${target.label}.`;
    return;
  }
  goTo(index, false);
  const node = $('#step-body').querySelector(target.selector);
  if (!node) {
    $('#step-notice').textContent = `Champ indisponible pour la sélection courante : ${target.label}.`;
    $('#step-title').focus();
    return;
  }
  const control = node.matches('input, select, textarea') ? node : node.querySelector('input, select, textarea');
  (control || node).focus();
  node.scrollIntoView({block: 'center'});
}

// --- Arbre (liste imbriquee native) -----------------------------------------------
function renderTree() {
  const root = {dirs: new Map(), files: []};
  for (const file of state.plan.graph.files) {
    const parts = file.path.split('/');
    let node = root;
    for (const part of parts.slice(0, -1)) {
      if (!node.dirs.has(part)) node.dirs.set(part, {dirs: new Map(), files: []});
      node = node.dirs.get(part);
    }
    node.files.push({name: parts[parts.length - 1], path: file.path});
  }
  const build = node => {
    const list = el('ul', {});
    for (const [name, child] of [...node.dirs.entries()].sort(([a], [b]) => a.localeCompare(b))) {
      list.append(el('li', {}, el('details', {open: true}, el('summary', {class: 'mono', text: `${name}/`}), build(child))));
    }
    for (const file of node.files) {
      const button = el('button', {type: 'button', class: 'file mono', 'data-path': file.path, text: file.name});
      button.addEventListener('click', () => select(file.path, true));
      list.append(el('li', {}, button));
    }
    return list;
  };
  $('#tree').replaceChildren(build(root));
  markModified();
}

// --- Diagramme (elements du plan reel uniquement) ------------------------------
const ROW = 26;
const COLUMNS = [4, 136, 330];
const WIDTHS = [112, 170, 266];
const VIEW_WIDTH = 600;
const CHAR_WIDTH = 7.3; // police monospace de 12 px
const CONDITION_LABELS = {agents_any: 'agents', project_types: 'type', security: 'sécurité', options: 'options'};

function ruleLabel(rule) {
  if (rule.mandatory) return `${rule.id} · toujours`;
  const conditions = rule.conditions.map(key => CONDITION_LABELS[key] || key);
  return rule.technologies.length || !conditions.length ? rule.id : `${rule.id} · ${conditions.join(', ')}`;
}

function fit(label, width) {
  const max = Math.floor((width - 10) / CHAR_WIDTH);
  return label.length > max ? `…${label.slice(-(max - 1))}` : label;
}

function renderDiagram() {
  const graph = state.plan.graph;
  const rules = graph.rules.filter(rule => graph.files.some(file => file.rule === rule.id));
  const columns = [graph.technologies.map(item => ({key: `t:${item.id}`, label: item.name})),
                   rules.map(rule => ({key: `r:${rule.id}`, label: ruleLabel(rule)})),
                   graph.files.map(file => ({key: `f:${file.path}`, label: file.path, path: file.path}))];
  const height = Math.max(...columns.map(column => column.length), 1) * ROW + 40;
  const root = svg('svg', {viewBox: `0 0 ${VIEW_WIDTH} ${height}`, role: 'group',
                           'aria-label': 'Diagramme du plan : technologies, règles et fichiers'});
  const position = {};
  ['Technologies', 'Règles', 'Fichiers'].forEach((title, index) => {
    const text = svg('text', {x: COLUMNS[index], y: 16, class: 'col-title'});
    text.textContent = title;
    root.append(text);
  });
  columns.forEach((column, index) => column.forEach((node, row) => {
    position[node.key] = {x: COLUMNS[index], y: 30 + row * ROW, w: WIDTHS[index]};
  }));
  const edges = svg('g', {class: 'edges', 'aria-hidden': 'true'});
  const link = (from, to) => {
    const a = position[from];
    const b = position[to];
    if (!a || !b) return; // jamais d'arete vers un element absent du plan
    edges.append(svg('path', {d: `M${a.x + a.w} ${a.y + 10} C${a.x + a.w + 20} ${a.y + 10} ${b.x - 20} ${b.y + 10} ${b.x} ${b.y + 10}`,
                              'data-from': from, 'data-to': to}));
  };
  rules.forEach(rule => rule.technologies.forEach(id => link(`t:${id}`, `r:${rule.id}`)));
  graph.files.forEach(file => { if (file.rule) link(`r:${file.rule}`, `f:${file.path}`); });
  root.append(edges);
  columns.forEach(column => column.forEach(node => {
    const p = position[node.key];
    const group = svg('g', {class: node.path ? 'node file-node' : 'node', 'data-key': node.key});
    group.append(svg('rect', {x: p.x, y: p.y, width: p.w, height: 20, rx: 3}));
    const text = svg('text', {x: p.x + 5, y: p.y + 14});
    text.textContent = fit(node.label, p.w);
    const title = svg('title');
    title.textContent = node.label; // libelle complet au survol
    group.append(title, text);
    if (node.path) {
      group.setAttribute('tabindex', '0');
      group.setAttribute('role', 'button');
      group.setAttribute('aria-label', `Fichier ${node.path}`);
      group.dataset.path = node.path;
      group.addEventListener('click', () => select(node.path, true));
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(node.path, true); }
      });
    }
    root.append(group);
  }));
  $('#diagram').replaceChildren(root);
}

// --- Selection partagee -----------------------------------------------------------
function select(path, explicit) {
  const files = state.plan ? state.plan.graph.files : [];
  if (path !== null && !files.some(file => file.path === path)) {
    $('#step-notice').textContent = `Sélection refusée : ${path} ne fait pas partie du plan.`;
    return false;
  }
  state.selectedPath = path;
  document.querySelectorAll('#tree [data-path]').forEach(button => {
    const active = button.dataset.path === path;
    button.classList.toggle('selected', active);
    if (active) button.setAttribute('aria-current', 'true'); else button.removeAttribute('aria-current');
  });
  const file = files.find(item => item.path === path);
  const lit = new Set();
  if (file) {
    lit.add(`f:${file.path}`);
    if (file.rule) {
      lit.add(`r:${file.rule}`);
      const rule = state.plan.graph.rules.find(item => item.id === file.rule);
      (rule ? rule.technologies : []).forEach(id => lit.add(`t:${id}`));
    }
  }
  document.querySelectorAll('#diagram .node').forEach(node => {
    node.classList.toggle('lit', lit.has(node.dataset.key));
    if (node.dataset.path) node.setAttribute('aria-pressed', String(node.dataset.path === path));
  });
  document.querySelectorAll('#diagram .edges path').forEach(edge => {
    edge.classList.toggle('lit', lit.has(edge.dataset.from) && lit.has(edge.dataset.to));
  });
  $('#selected-path').textContent = path ? `${file && file.rule ? `règle ${file.rule}` : 'skill externe'}` : '';
  if (path) editor.setFile(path, currentFiles()[path], state.plan.contents[path]);
  else editor.setFile(null, '', '');
  if (path) fileTabs.open(path); else fileTabs.deselect();
  markModified();
  $('#close-tab').disabled = !fileTabs.active();
  if (explicit && path) {
    const twin = document.querySelector(`#tree [data-path="${CSS.escape(path)}"]`);
    if (twin) twin.scrollIntoView({block: 'nearest'});
  }
  return true;
}

// --- Demarrage --------------------------------------------------------------------
// Theme, densite et disposition : coque E15 (shell.js). Le parcours n'y ajoute que ses commandes.
function registerCommands(shell) {
  shell.register({id: 'journey.next', label: 'Étape suivante', enabled: () => !$('#next').disabled, run: () => move(1)});
  shell.register({id: 'journey.prev', label: 'Étape précédente', enabled: () => !$('#prev').disabled, run: () => move(-1)});
  const views = shell.tabs($('#preview-tabs'));
  shell.register({id: 'preview.plan', label: 'Aperçu : afficher le plan', enabled: () => views.active() !== 'plan',
                  run: () => views.select('plan')});
  shell.register({id: 'preview.summary', label: 'Aperçu : afficher le résumé', enabled: () => views.active() !== 'summary',
                  run: () => views.select('summary')});
  // Atelier (E17) : onglets de l'editeur et recherche ; raccourcis reels affiches (Ctrl+F est celui de l'editeur).
  const tabsOpen = () => fileTabs && fileTabs.paths().length;
  shell.register({id: 'editor.tab.next', label: 'Éditeur : onglet suivant', enabled: () => tabsOpen() > 1,
                  run: () => select(fileTabs.step(1), true)});
  shell.register({id: 'editor.tab.prev', label: 'Éditeur : onglet précédent', enabled: () => tabsOpen() > 1,
                  run: () => select(fileTabs.step(-1), true)});
  shell.register({id: 'editor.tab.close', label: "Éditeur : fermer l'onglet actif", enabled: () => Boolean(fileTabs && fileTabs.active()),
                  run: () => fileTabs.close(fileTabs.active())});
  shell.register({id: 'editor.search', label: 'Éditeur : rechercher dans le fichier', shortcut: 'Ctrl+F',
                  enabled: () => Boolean(editor && editor.path()),
                  run: () => { shell.goToZone('editor'); editor.openSearch(); }});
  return views;
}

async function init() {
  window.forgeJourney.views = registerCommands(window.forgeShell);
  try {
    const response = await fetch('/api/catalog');
    state.catalog = await response.json();
    if (!response.ok) throw new Error(state.catalog.error || 'catalogue refusé');
  } catch (error) {
    setValidation('invalid', `Catalogue indisponible : ${error.message}`);
    return;
  }
  state.answers.security = state.catalog.security_levels[0];
  editor = window.ForgeEditor.create($('#editor'), {id: 'content', label: 'Contenu du fichier sélectionné', onChange: edited,
    empty: "Sélectionner un fichier dans l'arborescence ou le diagramme."});
  diagnostics = window.ForgeDiagnostics.create($('#diagnostics-panel'), {resolve: diagnosticTarget, navigate});
  fileTabs = window.ForgeFileTabs.create($('#file-tabs'), {panel: $('#editor-tabpanel'),
    onSelect: path => select(path, true), onClose: path => select(path, false)});
  $('#close-tab').addEventListener('click', () => fileTabs.close(fileTabs.active()));
  window.forgeJourney.fileTabs = fileTabs;
  workflow = window.ForgeWorkflow.create($('#workflow'), {snapshot,
    onDiagnostics: (items, source) => diagnostics.update(items, source)});
  window.forgeJourney.editor = editor;
  window.forgeJourney.diagnostics = diagnostics;
  window.forgeJourney.workflow = workflow;
  $('#prev').addEventListener('click', () => move(-1));
  $('#next').addEventListener('click', () => move(1));
  renderStep();
  renderSteps();
  performance.mark('forge-ready'); // E18a : premier rendu utile mesure (budget < 1 s)
}

window.forgeJourney = {state, select, config, prune, files: currentFiles, diagnosticTarget, navigate}; // pilotage des tests E2E
document.addEventListener('DOMContentLoaded', init);
