/* Coque UI v2 (E15) : themes, densite, panneaux masquables, deplacables et redimensionnables,
   rail, onglets et palette de commandes. Presentation seulement (docs/UI_V2_CONTRACTS.md, contrat E15) :
   aucun appel reseau, aucun endpoint ni flux metier ; les preferences locales ne contiennent aucune
   donnee projet. Les tailles passent par le CSSOM : la CSP interdit les attributs style. */
(function () {
  'use strict';

  const KEY = 'forge-my-project.ui.v2';
  const SCHEMA = 1;
  const THEMES = ['system', 'light', 'dark'];
  const THEME_LABEL = {system: 'système', light: 'clair', dark: 'sombre'};
  const DENSITIES = ['comfortable', 'compact'];
  const DENSITY_LABEL = {comfortable: 'confortable', compact: 'compacte'};
  const SIDES = ['left', 'right'];
  const IDS = ['navigation', 'configuration', 'preview', 'diagnostics', 'editor'];
  const STEP_PX = 16;
  // Panneaux lateraux : bornes de taille en px ; `auto` est la colonne par defaut (taille non choisie).
  const PANELS = {
    navigation: {label: 'Étapes', side: 'left', min: 200, max: 440, auto: 'var(--nav-width)'},
    preview: {label: 'Aperçu', side: 'right', min: 280, max: 720, auto: 'minmax(var(--preview-width), 1.1fr)'},
  };
  // Zones atteignables (rail, palette) : cible de focus explicite.
  const ZONES = {
    navigation: {label: 'Étapes', target: '#steps-title'},
    configuration: {label: 'Questionnaire', target: '#step-title'},
    preview: {label: 'Aperçu', target: '#preview-title'},
    editor: {label: 'Éditeur', target: '#editor-title'},
    diagnostics: {label: 'Diagnostics', target: '#diagnostics-title'},
    workflow: {label: 'Validation et écriture', target: '#workflow-title'},
  };

  const root = document.documentElement;
  const $ = selector => document.querySelector(selector);
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  // --- Preferences locales versionnees -------------------------------------------------
  function defaults() {
    return {
      schemaVersion: SCHEMA, theme: 'system', density: 'comfortable', activePanel: 'configuration',
      panels: {navigation: {visible: true, size: null, side: 'left'}, preview: {visible: true, size: null, side: 'right'}},
    };
  }

  // Toute valeur inconnue, mal typee ou hors bornes est ignoree champ par champ.
  function sanitize(raw) {
    const prefs = defaults();
    if (!raw || typeof raw !== 'object' || raw.schemaVersion !== SCHEMA) return prefs;
    if (THEMES.includes(raw.theme)) prefs.theme = raw.theme;
    if (DENSITIES.includes(raw.density)) prefs.density = raw.density;
    if (IDS.includes(raw.activePanel)) prefs.activePanel = raw.activePanel;
    const panels = raw.panels && typeof raw.panels === 'object' ? raw.panels : {};
    for (const [id, spec] of Object.entries(PANELS)) {
      const value = panels[id];
      if (!value || typeof value !== 'object') continue;
      if (typeof value.visible === 'boolean') prefs.panels[id].visible = value.visible;
      if (Number.isFinite(value.size)) prefs.panels[id].size = clamp(Math.round(value.size), spec.min, spec.max);
      if (SIDES.includes(value.side)) prefs.panels[id].side = value.side;
    }
    if (prefs.panels.navigation.side === prefs.panels.preview.side) {
      prefs.panels.navigation.side = 'left';
      prefs.panels.preview.side = 'right';
    }
    return prefs;
  }

  function load() {
    try {
      const text = window.localStorage.getItem(KEY);
      return sanitize(text ? JSON.parse(text) : null);
    } catch (error) {
      return defaults(); // stockage indisponible ou valeur corrompue : jamais bloquant
    }
  }

  let prefs = load();

  function save() {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(prefs));
    } catch (error) {
      // Stockage indisponible : les preferences restent valables pour cette page.
    }
  }

  // --- Theme et densite -----------------------------------------------------------------
  function applyTheme() {
    const dark = prefs.theme === 'dark' || (prefs.theme === 'system' && Boolean(media && media.matches));
    root.dataset.theme = dark ? 'dark' : 'light';
    root.dataset.themeChoice = prefs.theme;
    const button = $('#shell-theme');
    if (button) button.textContent = `Thème : ${THEME_LABEL[prefs.theme]}`;
  }

  function setTheme(theme) {
    if (!THEMES.includes(theme)) return;
    prefs.theme = theme;
    applyTheme();
    save();
  }

  function applyDensity() {
    root.dataset.density = prefs.density;
    const button = $('#shell-density');
    if (button) {
      button.textContent = `Densité : ${DENSITY_LABEL[prefs.density]}`;
      button.setAttribute('aria-pressed', String(prefs.density === 'compact'));
    }
  }

  function setDensity(density) {
    if (!DENSITIES.includes(density)) return;
    prefs.density = density;
    applyDensity();
    save();
  }

  // --- Disposition des panneaux -----------------------------------------------------------
  const panel = id => document.querySelector(`[data-panel="${id}"]`);
  const splitter = id => document.querySelector(`[data-splitter="${id}"]`);

  function sideOf(side) {
    return Object.keys(PANELS).find(id => prefs.panels[id].side === side);
  }

  function width(id) {
    const node = panel(id);
    return node && !node.hidden ? Math.round(node.getBoundingClientRect().width) : 0;
  }

  // Borne effective : la colonne est aussi limitee a 40 % de la fenetre (voir applyLayout).
  function maxWidth(id) {
    return Math.max(PANELS[id].min, Math.min(PANELS[id].max, Math.floor(window.innerWidth * 0.4)));
  }

  function updateSplitter(id) {
    const node = splitter(id);
    if (!node) return;
    const spec = PANELS[id];
    const now = clamp(width(id) || spec.min, spec.min, maxWidth(id));
    node.setAttribute('aria-valuemin', String(spec.min));
    node.setAttribute('aria-valuemax', String(maxWidth(id)));
    node.setAttribute('aria-valuenow', String(now));
    node.setAttribute('aria-valuetext', `${now} pixels`);
  }

  function updateControls() {
    for (const [id, spec] of Object.entries(PANELS)) {
      const state = prefs.panels[id];
      for (const toggle of document.querySelectorAll(`[data-toggle="${id}"]`)) {
        toggle.setAttribute('aria-pressed', String(state.visible));
        toggle.title = `${state.visible ? 'Masquer' : 'Afficher'} le panneau ${spec.label}`;
      }
      const target = state.side === 'left' ? 'droite' : 'gauche';
      for (const mover of document.querySelectorAll(`[data-move="${id}"]`)) {
        mover.setAttribute('aria-label', `Déplacer le panneau ${spec.label} à ${target}`);
        mover.title = mover.getAttribute('aria-label');
        mover.textContent = state.side === 'left' ? '→' : '←';
      }
    }
  }

  // Ordre DOM = ordre visuel (lecture et tabulation coherentes) : gauche, separateur, contenu, separateur, droite.
  function applyLayout() {
    const layout = $('#layout');
    const content = panel('configuration');
    if (!layout || !content) return;
    const focused = document.activeElement;
    const left = sideOf('left');
    const right = sideOf('right');
    const order = [panel(left), splitter(left), content, splitter(right), panel(right)];
    // Reinserer un noeud lui retire le focus et la capture du pointeur : seulement si l'ordre change.
    if (order.some((node, index) => index && node.previousElementSibling !== order[index - 1])) {
      layout.insertBefore(panel(left), content);
      layout.insertBefore(splitter(left), content);
      content.after(splitter(right), panel(right));
    }
    for (const [id, spec] of Object.entries(PANELS)) {
      const state = prefs.panels[id];
      const node = panel(id);
      const separator = splitter(id);
      node.hidden = !state.visible;
      separator.hidden = !state.visible;
      node.dataset.slot = state.side;
      separator.dataset.slot = `${state.side}-split`;
      const column = state.size ? `min(${state.size}px, 40vw)` : spec.auto;
      layout.style.setProperty(`--${state.side}-col`, state.visible ? column : '0px');
      layout.style.setProperty(`--${state.side}-split`, state.visible ? 'var(--split-width)' : '0px');
    }
    if (focused && focused !== document.activeElement && focused.isConnected && !focused.closest('[hidden]')) {
      focused.focus({preventScroll: true}); // un noeud deplace perd le focus : il lui est rendu
    }
    updateControls();
    Object.keys(PANELS).forEach(updateSplitter);
  }

  function setVisible(id, visible) {
    if (!PANELS[id]) return;
    const node = panel(id);
    const hadFocus = node && node.contains(document.activeElement);
    prefs.panels[id].visible = visible;
    applyLayout();
    save();
    if (!visible && hadFocus) {
      const toggle = document.querySelector(`.rail [data-toggle="${id}"]`);
      if (toggle) toggle.focus(); // focus logique : la commande qui restaure le panneau
    }
  }

  function swapSides() {
    for (const id of Object.keys(PANELS)) {
      prefs.panels[id].side = prefs.panels[id].side === 'left' ? 'right' : 'left';
    }
    applyLayout();
    save();
  }

  function resize(id, size, persist = true) {
    const spec = PANELS[id];
    if (!spec || !Number.isFinite(size)) return;
    prefs.panels[id].size = clamp(Math.round(size), spec.min, maxWidth(id));
    applyLayout();
    if (persist) save();
  }

  function resetLayout() {
    prefs.panels = defaults().panels;
    applyLayout();
    save();
  }

  function isDefaultLayout() {
    return JSON.stringify(prefs.panels) === JSON.stringify(defaults().panels);
  }

  function bindSplitter(id) {
    const node = splitter(id);
    // Fleche vers le contenu central = panneau plus etroit, quel que soit le cote du panneau.
    const grow = () => (prefs.panels[id].side === 'left' ? 1 : -1);
    node.addEventListener('keydown', event => {
      const spec = PANELS[id];
      const current = width(id);
      let size;
      if (event.key === 'ArrowRight') size = current + STEP_PX * grow();
      else if (event.key === 'ArrowLeft') size = current - STEP_PX * grow();
      else if (event.key === 'Home') size = spec.min;
      else if (event.key === 'End') size = maxWidth(id);
      else return;
      event.preventDefault();
      resize(id, size);
    });
    node.addEventListener('pointerdown', event => {
      if (event.button !== 0) return;
      event.preventDefault();
      node.focus({preventScroll: true});
      node.setPointerCapture(event.pointerId);
      const startX = event.clientX;
      const start = width(id);
      const direction = grow();
      const moved = move => resize(id, start + (move.clientX - startX) * direction, false);
      const done = () => {
        node.removeEventListener('pointermove', moved);
        node.removeEventListener('pointerup', done);
        node.removeEventListener('pointercancel', done);
        save();
      };
      node.addEventListener('pointermove', moved);
      node.addEventListener('pointerup', done);
      node.addEventListener('pointercancel', done);
    });
  }

  function goToZone(id) {
    const zone = ZONES[id];
    if (!zone) return false;
    if (PANELS[id] && !prefs.panels[id].visible) setVisible(id, true);
    const target = $(zone.target);
    if (!target) return false;
    if (target.tabIndex < 0 && !target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
    target.focus();
    target.scrollIntoView({block: 'nearest'});
    return true;
  }

  // --- Onglets (modele ARIA tabs, activation explicite) ------------------------------------
  function tabs(list, onChange) {
    const items = [...list.querySelectorAll('[role="tab"]')];
    function activate(tab) {
      for (const item of items) {
        const on = item === tab;
        item.setAttribute('aria-selected', String(on));
        item.tabIndex = on ? 0 : -1;
        document.getElementById(item.getAttribute('aria-controls')).hidden = !on;
      }
      if (onChange) onChange(tab.dataset.tab);
    }
    items.forEach(item => item.addEventListener('click', () => activate(item)));
    list.addEventListener('keydown', event => {
      const index = items.indexOf(document.activeElement);
      if (index < 0) return;
      const last = items.length - 1;
      let next;
      if (event.key === 'ArrowRight') next = index === last ? 0 : index + 1;
      else if (event.key === 'ArrowLeft') next = index === 0 ? last : index - 1;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = last;
      else return; // Entree et Espace : clic natif du bouton, donc activation explicite
      event.preventDefault();
      items[next].focus(); // la fleche deplace le focus sans activer
    });
    activate(items.find(item => item.getAttribute('aria-selected') === 'true') || items[0]);
    return {
      select: name => {
        const tab = items.find(item => item.dataset.tab === name);
        if (tab) activate(tab);
        return Boolean(tab);
      },
      active: () => (items.find(item => item.getAttribute('aria-selected') === 'true') || {}).dataset.tab,
    };
  }

  // --- Commandes et palette ----------------------------------------------------------------
  const commands = new Map();

  // Une commande est un objet {id, label, shortcut?, enabled?, run} : jamais une chaine executee.
  function register(command) {
    if (!command || !/^[a-z][a-z0-9.-]*$/.test(command.id) || commands.has(command.id)
        || typeof command.run !== 'function') {
      throw new Error(`Commande refusée : ${command && command.id}`);
    }
    commands.set(command.id, command);
  }

  function label(command) {
    return typeof command.label === 'function' ? command.label() : command.label;
  }

  function availableCommands() {
    return [...commands.values()].filter(command => !command.enabled || command.enabled())
      .map(command => ({id: command.id, label: label(command), shortcut: command.shortcut || ''}));
  }

  function run(id) {
    const command = commands.get(id);
    if (!command || (command.enabled && !command.enabled())) return false;
    command.run();
    return true;
  }

  const fold = text => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const palette = {opener: null, items: [], index: 0};

  function renderPalette() {
    const input = $('#palette-input');
    const list = $('#palette-list');
    const words = fold(input.value).split(/\s+/).filter(Boolean);
    palette.items = availableCommands().filter(command => words.every(word => fold(command.label).includes(word)));
    palette.index = clamp(palette.index, 0, Math.max(0, palette.items.length - 1));
    list.replaceChildren(...palette.items.map((command, index) => {
      const option = document.createElement('li');
      option.id = `cmd-${command.id.replace(/\./g, '-')}`;
      option.className = 'palette-option';
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', String(index === palette.index));
      option.dataset.command = command.id;
      const text = document.createElement('span');
      text.textContent = command.label;
      option.append(text);
      if (command.shortcut) {
        const kbd = document.createElement('kbd');
        kbd.textContent = command.shortcut;
        option.append(kbd);
      }
      option.addEventListener('click', () => execute(command.id));
      return option;
    }));
    $('#palette-empty').hidden = palette.items.length > 0;
    const active = palette.items[palette.index];
    input.setAttribute('aria-activedescendant', active ? `cmd-${active.id.replace(/\./g, '-')}` : '');
    const option = active && document.getElementById(`cmd-${active.id.replace(/\./g, '-')}`);
    if (option) option.scrollIntoView({block: 'nearest'});
  }

  function openPalette() {
    const dialog = $('#palette');
    if (dialog.open) return;
    palette.opener = document.activeElement;
    palette.index = 0;
    $('#palette-input').value = '';
    dialog.showModal();
    renderPalette();
    $('#palette-input').focus();
  }

  function closePalette() {
    const dialog = $('#palette');
    if (!dialog.open) return;
    dialog.close();
    const opener = palette.opener;
    palette.opener = null;
    if (opener && opener.isConnected && opener !== document.body && !opener.closest('[hidden]')) opener.focus();
    else $('#step-panel').focus();
  }

  // La palette se ferme et rend le focus avant l'execution : une commande peut ensuite le deplacer.
  function execute(id) {
    closePalette();
    run(id);
  }

  function bindPalette() {
    const dialog = $('#palette');
    const input = $('#palette-input');
    input.addEventListener('input', () => {
      palette.index = 0;
      renderPalette();
    });
    dialog.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        const count = palette.items.length;
        if (count) palette.index = (palette.index + (event.key === 'ArrowDown' ? 1 : count - 1)) % count;
        renderPalette();
      } else if (event.key === 'Enter') {
        event.preventDefault();
        const command = palette.items[palette.index];
        if (command) execute(command.id);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        closePalette();
      } else if (event.key === 'Tab') {
        event.preventDefault(); // surface modale : le focus reste sur la recherche
      }
    });
    dialog.addEventListener('cancel', event => {
      event.preventDefault();
      closePalette();
    });
    dialog.addEventListener('click', event => {
      if (event.target === dialog) closePalette(); // clic sur le fond
    });
    $('#shell-palette').addEventListener('click', openPalette);
    // Ctrl+K : seul raccourci global. Ctrl+Shift+P (fenetre privee), Ctrl+1..8 (onglets) et F6
    // (barre d'adresse) sont reserves par Firefox et ne sont pas utilises (contrat E15).
    document.addEventListener('keydown', event => {
      if (event.ctrlKey && !event.shiftKey && !event.altKey && !event.metaKey && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if ($('#palette').open) closePalette();
        else openPalette();
      }
    });
  }

  function registerShellCommands() {
    for (const [id, spec] of Object.entries(PANELS)) {
      register({
        id: `view.${id}.toggle`,
        label: () => `${prefs.panels[id].visible ? 'Masquer' : 'Afficher'} le panneau ${spec.label}`,
        run: () => setVisible(id, !prefs.panels[id].visible),
      });
    }
    register({
      id: 'layout.swap',
      label: () => (prefs.panels.navigation.side === 'left'
        ? "Déplacer les étapes à droite et l'aperçu à gauche" : "Remettre les étapes à gauche et l'aperçu à droite"),
      run: swapSides,
    });
    register({id: 'layout.reset', label: 'Réinitialiser la disposition', enabled: () => !isDefaultLayout(), run: resetLayout});
    for (const theme of THEMES) {
      register({
        id: `theme.${theme}`,
        label: theme === 'system' ? 'Thème : suivre le système' : `Thème : ${THEME_LABEL[theme]}`,
        enabled: () => prefs.theme !== theme,
        run: () => setTheme(theme),
      });
    }
    for (const density of DENSITIES) {
      register({
        id: `density.${density}`,
        label: `Densité : ${DENSITY_LABEL[density]}`,
        enabled: () => prefs.density !== density,
        run: () => setDensity(density),
      });
    }
    for (const [id, zone] of Object.entries(ZONES)) {
      register({id: `go.${id}`, label: `Aller à : ${zone.label}`, run: () => goToZone(id)});
    }
  }

  function bindControls() {
    for (const button of document.querySelectorAll('[data-toggle]')) {
      button.addEventListener('click', () => setVisible(button.dataset.toggle, !prefs.panels[button.dataset.toggle].visible));
    }
    for (const button of document.querySelectorAll('[data-hide]')) {
      button.addEventListener('click', () => setVisible(button.dataset.hide, false));
    }
    for (const button of document.querySelectorAll('[data-move]')) {
      button.addEventListener('click', swapSides);
    }
    for (const button of document.querySelectorAll('[data-goto]')) {
      button.addEventListener('click', () => goToZone(button.dataset.goto));
    }
    $('#shell-theme').addEventListener('click', () => setTheme(THEMES[(THEMES.indexOf(prefs.theme) + 1) % THEMES.length]));
    $('#shell-density').addEventListener('click', () => setDensity(prefs.density === 'compact' ? 'comfortable' : 'compact'));
    Object.keys(PANELS).forEach(bindSplitter);
    if (media && media.addEventListener) media.addEventListener('change', () => { if (prefs.theme === 'system') applyTheme(); });
    window.addEventListener('resize', () => Object.keys(PANELS).forEach(updateSplitter));
    // Panneau actif : simple repere visuel memorise, le focus n'est jamais deplace au chargement.
    document.addEventListener('focusin', event => {
      const node = event.target.closest && event.target.closest('[data-panel]');
      const id = node && node.dataset.panel;
      if (!id || id === prefs.activePanel) return;
      prefs.activePanel = id;
      markActive();
      save();
    });
  }

  function markActive() {
    for (const node of document.querySelectorAll('[data-panel]')) {
      node.classList.toggle('panel-active', node.dataset.panel === prefs.activePanel);
    }
  }

  function mount() {
    applyTheme();
    applyDensity();
    applyLayout();
    markActive();
    bindControls();
    bindPalette();
    registerShellCommands();
  }

  applyTheme(); // au plus tot : evite un rendu dans le mauvais theme
  document.addEventListener('DOMContentLoaded', mount);

  window.forgeShell = {
    KEY, register, run, tabs, openPalette, closePalette, goToZone,
    commands: availableCommands,
    prefs: () => JSON.parse(JSON.stringify(prefs)),
    reload: () => { prefs = load(); applyTheme(); applyDensity(); applyLayout(); markActive(); },
  };
}());
