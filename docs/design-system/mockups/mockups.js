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

// Palette de commandes (E14, reprise) : dialog modal, combobox + listbox, aria-activedescendant.
const palette = document.querySelector('#palette');
const paletteInput = document.querySelector('#palette-input');
const paletteEmpty = document.querySelector('#palette-empty');
const options = [...document.querySelectorAll('#palette-list [role="option"]')];
const openButton = document.querySelector('#open-palette');
let returnFocus = null;

function visibleOptions() {
  return options.filter(option => !option.hidden);
}

function setActive(option) {
  for (const item of options) item.setAttribute('aria-selected', String(item === option));
  paletteInput.setAttribute('aria-activedescendant', option ? option.id : '');
  if (option) option.scrollIntoView({block: 'nearest'});
}

function filterOptions() {
  const query = paletteInput.value.trim().toLowerCase();
  for (const option of options) option.hidden = !option.textContent.toLowerCase().includes(query);
  const visible = visibleOptions();
  paletteEmpty.hidden = visible.length > 0;
  setActive(visible.find(option => option.getAttribute('aria-disabled') !== 'true') || null);
}

function openPalette() {
  returnFocus = document.activeElement;
  palette.hidden = false;
  paletteInput.value = '';
  filterOptions();
  paletteInput.focus();
}

function closePalette() {
  palette.hidden = true;
  if (returnFocus && returnFocus.focus) returnFocus.focus();
}

function run(option) {
  if (!option || option.getAttribute('aria-disabled') === 'true') return;
  closePalette();
  if (option.dataset.screenTarget) {
    screenSelect.value = option.dataset.screenTarget;
    showScreen(option.dataset.screenTarget);
  } else if (option.dataset.action === 'theme') {
    setTheme(root.dataset.theme !== 'dark');
  }
}

function move(step) {
  const visible = visibleOptions().filter(option => option.getAttribute('aria-disabled') !== 'true');
  if (!visible.length) return;
  const current = visible.findIndex(option => option.getAttribute('aria-selected') === 'true');
  setActive(visible[(current + step + visible.length) % visible.length]);
}

openButton.addEventListener('click', openPalette);
paletteInput.addEventListener('input', filterOptions);
paletteInput.addEventListener('keydown', event => {
  if (event.key === 'ArrowDown') { event.preventDefault(); move(1); }
  else if (event.key === 'ArrowUp') { event.preventDefault(); move(-1); }
  else if (event.key === 'Enter') { event.preventDefault(); run(options.find(o => o.getAttribute('aria-selected') === 'true')); }
  else if (event.key === 'Escape') { event.preventDefault(); closePalette(); }
  else if (event.key === 'Tab') { event.preventDefault(); }  // focus maintenu dans la boite modale
});
for (const option of options) {
  option.addEventListener('mousemove', () => { if (option.getAttribute('aria-disabled') !== 'true') setActive(option); });
  option.addEventListener('click', () => run(option));
}
palette.addEventListener('click', event => { if (event.target === palette) closePalette(); });
document.addEventListener('keydown', event => {
  const key = event.key.toLowerCase();
  if (event.ctrlKey && (key === 'k' || (event.shiftKey && key === 'p'))) {
    event.preventDefault();
    if (palette.hidden) openPalette(); else closePalette();
  } else if (event.ctrlKey && /^[1-6]$/.test(event.key) && palette.hidden) {
    event.preventDefault();
    const target = screens[Number(event.key) - 1];
    screenSelect.value = target.dataset.screen;
    showScreen(target.dataset.screen);
  }
});

