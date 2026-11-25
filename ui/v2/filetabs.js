/* Onglets des fichiers ouverts dans l'editeur (E17). Presentation seulement : aucun appel reseau,
   aucune persistance ; la liste ne contient que des chemins du plan courant, fournis par le parcours.
   Modele ARIA tabs a activation explicite : fleches, Debut/Fin deplacent le focus, Entree/Espace
   activent, Suppr ferme l'onglet focalise. Un seul onglet a tabindex=0 (l'actif). */
(function () {
  'use strict';

  const MAX_TABS = 8;
  let sequence = 0;

  function create(list, {panel, onSelect, onClose}) {
    const state = {tabs: [], active: null}; // tabs : [{path, node}]

    const find = path => state.tabs.find(tab => tab.path === path);
    const name = path => path.split('/').pop();

    function render() {
      list.hidden = state.tabs.length === 0;
      for (const tab of state.tabs) {
        const on = tab.path === state.active;
        tab.node.setAttribute('aria-selected', String(on));
        tab.node.tabIndex = on ? 0 : -1;
      }
      const active = find(state.active);
      if (active) panel.setAttribute('aria-labelledby', active.node.id);
      else panel.removeAttribute('aria-labelledby');
    }

    function setModified(path, modified) {
      const tab = find(path);
      if (!tab) return;
      tab.node.classList.toggle('modified', modified);
      tab.node.setAttribute('aria-label', modified ? `${tab.path} (modifié)` : tab.path);
    }

    // Ouvre (ou reactive) l'onglet d'un chemin ; au-dela de MAX_TABS, le plus ancien inactif est ferme.
    function open(path) {
      if (!find(path)) {
        const node = document.createElement('button');
        node.type = 'button';
        node.id = `file-tab-${++sequence}`;
        node.className = 'file-tab';
        node.setAttribute('role', 'tab');
        node.setAttribute('aria-controls', panel.id);
        node.setAttribute('aria-label', path);
        node.title = path;
        node.textContent = name(path);
        node.dataset.path = path;
        node.addEventListener('click', () => onSelect(path));
        list.append(node);
        state.tabs.push({path, node});
        while (state.tabs.length > MAX_TABS) {
          const oldest = state.tabs.find(tab => tab.path !== path);
          remove(oldest.path);
        }
      }
      state.active = path;
      render();
    }

    function remove(path) {
      const tab = find(path);
      if (!tab) return;
      tab.node.remove();
      state.tabs = state.tabs.filter(item => item !== tab);
      if (state.active === path) state.active = null;
    }

    // Fermeture explicite : l'onglet voisin devient actif (focus logique), sinon plus aucune selection.
    function close(path) {
      const index = state.tabs.findIndex(tab => tab.path === path);
      if (index < 0) return null;
      const wasActive = state.active === path;
      const hadFocus = state.tabs[index].node === document.activeElement;
      remove(path);
      const neighbour = state.tabs[Math.min(index, state.tabs.length - 1)];
      render();
      if (wasActive) onClose(neighbour ? neighbour.path : null);
      if (hadFocus) {
        const target = find(state.active) || neighbour;
        if (target) target.node.focus();
        else panel.focus();
      }
      return neighbour ? neighbour.path : null;
    }

    // Apres un nouveau plan : seuls les chemins encore presents restent ouverts.
    function retain(paths) {
      const keep = new Set(paths);
      state.tabs.filter(tab => !keep.has(tab.path)).forEach(tab => remove(tab.path));
      render();
    }

    function deselect() {
      state.active = null;
      render();
    }

    function step(delta) {
      if (!state.tabs.length) return null;
      const index = state.tabs.findIndex(tab => tab.path === state.active);
      const next = state.tabs[(index + delta + state.tabs.length) % state.tabs.length];
      return next.path;
    }

    list.addEventListener('keydown', event => {
      const index = state.tabs.findIndex(tab => tab.node === document.activeElement);
      if (index < 0) return;
      const last = state.tabs.length - 1;
      let next;
      if (event.key === 'ArrowRight') next = index === last ? 0 : index + 1;
      else if (event.key === 'ArrowLeft') next = index === 0 ? last : index - 1;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = last;
      else if (event.key === 'Delete') {
        event.preventDefault();
        close(state.tabs[index].path);
        return;
      } else return;
      event.preventDefault();
      state.tabs[next].node.focus();
    });

    render();
    return {
      open, close, retain, deselect, setModified, step,
      paths: () => state.tabs.map(tab => tab.path),
      active: () => state.active,
    };
  }

  window.ForgeFileTabs = {create, MAX_TABS};
}());
