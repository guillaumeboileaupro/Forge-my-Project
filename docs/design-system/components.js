'use strict';

// Theme clair / sombre (meme comportement que les maquettes).
const root = document.documentElement;
const themeButton = document.querySelector('#theme');
function setTheme(dark) {
  root.dataset.theme = dark ? 'dark' : 'light';
  themeButton.setAttribute('aria-pressed', String(dark));
  themeButton.textContent = dark ? 'Thème clair' : 'Thème sombre';
}
themeButton.addEventListener('click', () => setTheme(root.dataset.theme !== 'dark'));
const requestedTheme = new URLSearchParams(location.search).get('theme');
setTheme(requestedTheme === 'dark' || (requestedTheme !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches));

// Onglets ARIA : fleches, Home/End, activation explicite (Entree / Espace / clic).
for (const list of document.querySelectorAll('[role="tablist"]')) {
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const select = tab => {
    for (const item of tabs) {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
    }
  };
  for (const tab of tabs) {
    tab.addEventListener('click', () => select(tab));
    tab.addEventListener('keydown', event => {
      const index = tabs.indexOf(tab);
      const target = {ArrowRight: tabs[(index + 1) % tabs.length], ArrowLeft: tabs[(index - 1 + tabs.length) % tabs.length],
        Home: tabs[0], End: tabs[tabs.length - 1]}[event.key];
      if (target) { event.preventDefault(); target.focus(); }
    });
  }
}

// Poignee : flèches = 16 px dans les bornes declarees (aria-valuemin/max).
for (const handle of document.querySelectorAll('[role="separator"]')) {
  handle.addEventListener('keydown', event => {
    const step = {ArrowLeft: -16, ArrowRight: 16}[event.key];
    if (!step) return;
    event.preventDefault();
    const min = Number(handle.getAttribute('aria-valuemin')), max = Number(handle.getAttribute('aria-valuemax'));
    const value = Math.min(max, Math.max(min, Number(handle.getAttribute('aria-valuenow')) + step));
    handle.setAttribute('aria-valuenow', String(value));
    const badge = handle.parentElement.querySelector('.badge');
    if (badge) badge.textContent = value + ' px';
  });
}
