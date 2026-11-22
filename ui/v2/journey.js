// Parcours v2 (E16) : questionnaire progressif et conditionnel, apercu du plan reel,
// arbre et diagramme synchronises par un meme `selectedPath`.
// Le serveur reste l'autorite (prerequis, conflits, versions, diagnostics) : ce script
// n'affiche que des choix et des relations fournis par /api/catalog et /api/plan.
'use strict';

const NAME = /^[a-z][a-z0-9-]{1,48}[a-z0-9]$/;
const DEBOUNCE_MS = 350;
const SEVERITY_ORDER = {error: 0, warning: 1, info: 2};

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
};

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
    const set = el('fieldset', {class: 'choices'}, el('legend', {text: `${category.label} (${category.min} à ${category.max})`}));
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
    showDiagnostics(payload.diagnostics || []);
    $('#alerts').textContent = payload.error || 'Configuration refusée par le serveur.';
    setValidation('invalid', 'Configuration incomplète ou invalide : voir le message.');
    return;
  }
  $('#alerts').textContent = '';
  applyPlan(payload);
}

function applyPlan(payload) {
  state.plan = payload;
  showDiagnostics(payload.diagnostics);
  renderTree();
  renderDiagram();
  if (state.selectedPath && !payload.graph.files.some(file => file.path === state.selectedPath)) {
    state.selectedPath = null;
    $('#step-notice').textContent = "Le fichier sélectionné n'existe plus dans ce plan.";
  }
  select(state.selectedPath, false);
  const errors = payload.diagnostics.filter(item => item.severity === 'error').length;
  setValidation(errors ? 'invalid' : 'valid',
    `Aperçu à jour : ${payload.graph.files.length} fichier(s), ${payload.graph.rules.length} règle(s)`
    + (errors ? `, ${errors} erreur(s) bloquante(s).` : '.'));
}

function showDiagnostics(items) {
  const ordered = items.map((item, index) => ({item, index}))
    .sort((a, b) => (SEVERITY_ORDER[a.item.severity] ?? 3) - (SEVERITY_ORDER[b.item.severity] ?? 3) || a.index - b.index)
    .map(entry => entry.item);
  $('#diagnostics').replaceChildren(...ordered.map(item => el('li', {class: `diag diag-${item.severity}`},
    el('span', {class: 'diag-level', text: item.severity}), ` ${item.message}`)));
  const errors = ordered.filter(item => item.severity === 'error').length;
  $('#diagnostics-count').textContent = `${ordered.length} (dont ${errors} bloquant(s))`;
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
  $('#selected-path').textContent = path ? `· ${path}${file && file.rule ? ` (règle ${file.rule})` : ''}` : '';
  $('#content').textContent = path ? state.plan.contents[path] : "Sélectionner un fichier dans l'arborescence ou le diagramme.";
  if (explicit && path) {
    const twin = document.querySelector(`#tree [data-path="${CSS.escape(path)}"]`);
    if (twin) twin.scrollIntoView({block: 'nearest'});
  }
  return true;
}

// --- Demarrage --------------------------------------------------------------------
function theme() {
  const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
}

async function init() {
  theme();
  try {
    const response = await fetch('/api/catalog');
    state.catalog = await response.json();
    if (!response.ok) throw new Error(state.catalog.error || 'catalogue refusé');
  } catch (error) {
    setValidation('invalid', `Catalogue indisponible : ${error.message}`);
    return;
  }
  state.answers.security = state.catalog.security_levels[0];
  $('#prev').addEventListener('click', () => move(-1));
  $('#next').addEventListener('click', () => move(1));
  renderStep();
  renderSteps();
}

window.forgeJourney = {state, select, config, prune}; // pilotage des tests E2E
document.addEventListener('DOMContentLoaded', init);
