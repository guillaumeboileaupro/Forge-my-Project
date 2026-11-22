'use strict';

const root = document.documentElement;
const screenSelect = document.querySelector('#screen');
const themeButton = document.querySelector('#theme');
const screens = [...document.querySelectorAll('[data-screen]')];

function showScreen(id) {
  for (const screen of screens) screen.hidden = screen.dataset.screen !== id;
  history.replaceState(null, '', `#${id}`);
  document.querySelector('#workspace').focus();
}

function setTheme(dark) {
  root.dataset.theme = dark ? 'dark' : 'light';
  themeButton.setAttribute('aria-pressed', String(dark));
  themeButton.textContent = dark ? 'Thème clair' : 'Thème sombre';
}

screenSelect.addEventListener('change', () => showScreen(screenSelect.value));
themeButton.addEventListener('click', () => setTheme(root.dataset.theme !== 'dark'));

const requested = location.hash.slice(1);
if (screens.some(screen => screen.dataset.screen === requested)) screenSelect.value = requested;
showScreen(screenSelect.value);
const requestedTheme = new URLSearchParams(location.search).get('theme');
setTheme(requestedTheme === 'dark' || (requestedTheme !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches));
