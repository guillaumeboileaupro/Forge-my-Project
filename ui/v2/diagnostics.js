// Panneau diagnostics (E17a) : gravites, filtres, navigation vers le champ ou le fichier concerne.
// Les diagnostics viennent du serveur ; le panneau ne les modifie, ne les masque ni ne les reclasse
// (un filtre retire seulement l'affichage, le compteur total reste visible).
'use strict';

(function () {
  const SEVERITIES = [['error', 'Erreurs'], ['warning', 'Avertissements'], ['info', 'Informations']];
  const ORDER = {error: 0, warning: 1, info: 2};
  const LEVEL = {error: 'erreur', warning: 'avertissement', info: 'info'};

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

  // Tri stable : gravite puis ordre du serveur.
  function ordered(items) {
    return items.map((item, index) => ({item, index}))
      .sort((a, b) => (ORDER[a.item.severity] ?? 3) - (ORDER[b.item.severity] ?? 3) || a.index - b.index)
      .map(entry => entry.item);
  }

  function create(root, options = {}) {
    const state = {items: [], hidden: new Set(), text: '', source: ''};
    const filters = el('div', {class: 'diag-filters', role: 'group', 'aria-label': 'Filtrer par gravité'});
    const toggles = {};
    for (const [severity, label] of SEVERITIES) {
      const button = el('button', {type: 'button', class: `diag-toggle diag-${severity}`, 'data-severity': severity,
        'aria-pressed': 'true'});
      button.addEventListener('click', () => {
        if (state.hidden.has(severity)) state.hidden.delete(severity); else state.hidden.add(severity);
        render();
      });
      toggles[severity] = {button, label};
      filters.append(button);
    }
    const search = el('input', {type: 'search', class: 'diag-search', autocomplete: 'off',
      'aria-label': 'Filtrer les diagnostics par texte', placeholder: 'Filtrer (message, code, sujet)'});
    search.addEventListener('input', () => { state.text = search.value.trim().toLowerCase(); render(); });
    const summary = el('p', {class: 'diag-summary muted', role: 'status', 'aria-live': 'polite'});
    const list = el('ul', {class: 'diagnostics', 'aria-label': 'Diagnostics'});
    root.replaceChildren(el('div', {class: 'diag-toolbar'}, filters, search), summary, list);

    function visible(item) {
      if (state.hidden.has(item.severity)) return false;
      if (!state.text) return true;
      return [item.message, item.code, item.subject].some(value => (value || '').toLowerCase().includes(state.text));
    }

    function entry(item) {
      const target = options.resolve ? options.resolve(item) : null;
      const node = el('li', {class: `diag diag-${item.severity}`, 'data-code': item.code || ''},
        el('span', {class: 'diag-level', text: LEVEL[item.severity] || item.severity}), ` ${item.message}`);
      const meta = [item.code, item.subject && item.subject !== item.code ? item.subject : ''].filter(Boolean).join(' · ');
      if (meta) node.append(el('span', {class: 'diag-meta mono muted', text: ` ${meta}`}));
      if (target) {
        const go = el('button', {type: 'button', class: 'diag-go', text: `Aller à : ${target.label}`});
        go.addEventListener('click', () => options.navigate(target));
        node.append(' ', go);
      }
      return node;
    }

    function render() {
      const counts = {error: 0, warning: 0, info: 0};
      state.items.forEach(item => { if (item.severity in counts) counts[item.severity] += 1; });
      for (const [severity, {button, label}] of Object.entries(toggles)) {
        button.textContent = `${label} ${counts[severity]}`;
        button.setAttribute('aria-pressed', String(!state.hidden.has(severity)));
      }
      const shown = ordered(state.items).filter(visible);
      list.replaceChildren(...shown.map(entry));
      const total = state.items.length;
      const origin = state.source ? ` (${state.source})` : '';
      summary.textContent = !total ? `Aucun diagnostic${origin}.`
        : shown.length === total ? `${total} diagnostic(s)${origin}, dont ${counts.error} bloquant(s).`
          : `${shown.length} affiché(s) sur ${total}${origin}, dont ${counts.error} bloquant(s) au total.`;
      if (total && !shown.length) list.append(el('li', {class: 'muted', text: 'Aucun diagnostic ne correspond aux filtres.'}));
      if (options.onCount) options.onCount(counts, total);
    }

    render();
    return {
      update(items, source = '') {
        state.items = Array.isArray(items) ? items.slice() : [];
        state.source = source;
        render();
      },
      items: () => state.items.slice(),
    };
  }

  window.ForgeDiagnostics = {create, ordered};
}());
