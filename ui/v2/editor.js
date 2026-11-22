// Editeur leger (E17a) : textarea natif superpose a une couche coloree, numeros de ligne,
// recherche/remplacement. Aucun HTML injecte : la coloration est construite noeud par noeud.
// Le texte edite n'a aucune autorite : le serveur revalide chemins, tailles et contenu.
'use strict';

(function () {
  const MAX_HIGHLIGHT = 200000; // caracteres ; au-dela, texte brut (budget de rendu)
  const MAX_MATCHES = 5000;

  const STRING = String.raw`"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'`;
  const NUMBER = String.raw`\b\d+(?:\.\d+)*\b`;
  const HASH_COMMENT = String.raw`(?:^|(?<=\s))#[^\n]*`;
  const words = list => String.raw`\b(?:${list.join('|')})\b`;

  // Chaque regle : [classe, expression sans groupe capturant]. La premiere qui correspond gagne.
  const LANGUAGES = {
    python: [['comment', '#[^\\n]*'], ['string', `"""[\\s\\S]*?"""|'''[\\s\\S]*?'''|${STRING}`],
      ['keyword', words(['def', 'class', 'return', 'import', 'from', 'as', 'if', 'elif', 'else', 'for', 'while', 'in',
        'not', 'and', 'or', 'is', 'None', 'True', 'False', 'with', 'try', 'except', 'finally', 'raise', 'pass',
        'lambda', 'yield', 'async', 'await'])], ['number', NUMBER]],
    shell: [['comment', HASH_COMMENT], ['string', STRING], ['variable', String.raw`\$\{?[A-Za-z_][A-Za-z0-9_]*\}?`],
      ['keyword', words(['if', 'then', 'else', 'elif', 'fi', 'for', 'do', 'done', 'while', 'case', 'esac', 'function',
        'export', 'set', 'local', 'return', 'exit'])]],
    toml: [['comment', '#[^\\n]*'], ['section', String.raw`^[ \t]*\[\[?[^\]\n]+\]\]?`],
      ['key', String.raw`^[ \t]*[A-Za-z0-9_.\-"]+(?=[ \t]*=)`], ['string', `"""[\\s\\S]*?"""|${STRING}`],
      ['literal', words(['true', 'false'])], ['number', NUMBER]],
    yaml: [['comment', HASH_COMMENT], ['key', String.raw`^[ \t]*(?:- )?[A-Za-z0-9_.\-"']+(?=:(?:\s|$))`],
      ['string', STRING], ['literal', words(['true', 'false', 'null'])], ['number', NUMBER]],
    json: [['key', String.raw`"(?:\\.|[^"\\\n])*"(?=\s*:)`], ['string', STRING],
      ['literal', words(['true', 'false', 'null'])], ['number', String.raw`-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b`]],
    markdown: [['keyword', '^```[^\\n]*'], ['section', '^#{1,6} [^\\n]*'], ['string', '`[^`\\n]+`'],
      ['variable', String.raw`\[[^\]\n]+\]\([^)\n]+\)`], ['literal', String.raw`^[ \t]*(?:[-*+]|\d+\.)(?= )`]],
    clike: [['comment', String.raw`//[^\n]*|/\*[\s\S]*?\*/`], ['string', `\`(?:\\\\.|[^\`\\\\])*\`|${STRING}`],
      ['keyword', words(['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'import', 'export',
        'from', 'class', 'new', 'async', 'await', 'fn', 'pub', 'use', 'mod', 'impl', 'struct', 'enum', 'match',
        'package', 'func', 'type', 'interface', 'public', 'private', 'static', 'void', 'true', 'false', 'null'])],
      ['number', NUMBER]],
    docker: [['comment', '^[ \\t]*#[^\\n]*'], ['keyword', String.raw`^[ \t]*(?:FROM|RUN|COPY|ADD|WORKDIR|ENV|ARG|USER|EXPOSE|CMD|ENTRYPOINT|LABEL|HEALTHCHECK|VOLUME)\b`],
      ['string', STRING], ['variable', String.raw`\$\{?[A-Za-z_][A-Za-z0-9_]*\}?`]],
    conf: [['comment', '^[ \\t]*#[^\\n]*']],
    plain: [],
  };
  const COMPILED = {};

  const EXTENSIONS = {py: 'python', sh: 'shell', bash: 'shell', toml: 'toml', ini: 'toml', cfg: 'toml', yml: 'yaml',
    yaml: 'yaml', json: 'json', md: 'markdown', js: 'clike', mjs: 'clike', ts: 'clike', tsx: 'clike', jsx: 'clike',
    rs: 'clike', go: 'clike', java: 'clike', css: 'clike'};
  const LABELS = {python: 'Python', shell: 'Shell', toml: 'TOML', yaml: 'YAML', json: 'JSON', markdown: 'Markdown',
    clike: 'Code', docker: 'Dockerfile', conf: 'Configuration', plain: 'Texte'};

  function language(path) {
    const name = (path || '').split('/').pop();
    if (/^Dockerfile/.test(name)) return 'docker';
    if (/^\.(gitignore|dockerignore|editorconfig|gitattributes)$|^CODEOWNERS$/.test(name)) return 'conf';
    if (name === 'Makefile') return 'shell';
    const extension = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
    return EXTENSIONS[extension] || 'plain';
  }

  // Jetons non chevauchants, ordonnes : [{start, end, cls}].
  function tokenize(text, lang) {
    const rules = LANGUAGES[lang] || [];
    if (!rules.length || text.length > MAX_HIGHLIGHT) return [];
    if (!COMPILED[lang]) COMPILED[lang] = new RegExp(rules.map(rule => `(${rule[1]})`).join('|'), 'gm');
    const pattern = COMPILED[lang];
    pattern.lastIndex = 0;
    const tokens = [];
    let match;
    while ((match = pattern.exec(text)) !== null) {
      if (match[0] === '') { pattern.lastIndex += 1; continue; }
      const group = match.findIndex((value, index) => index > 0 && value !== undefined);
      tokens.push({start: match.index, end: match.index + match[0].length, cls: rules[group - 1][0]});
    }
    return tokens;
  }

  function findAll(text, query, caseSensitive) {
    if (!query) return [];
    const haystack = caseSensitive ? text : text.toLowerCase();
    const needle = caseSensitive ? query : query.toLowerCase();
    const matches = [];
    let index = haystack.indexOf(needle);
    while (index !== -1 && matches.length < MAX_MATCHES) {
      matches.push({start: index, end: index + needle.length});
      index = haystack.indexOf(needle, index + needle.length);
    }
    return matches;
  }

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

  // Segments colores : coupure a chaque bord de jeton ou d'occurrence.
  function paint(target, text, tokens, matches, current) {
    const cuts = new Set([0, text.length]);
    for (const range of tokens.concat(matches)) { cuts.add(range.start); cuts.add(range.end); }
    const points = [...cuts].sort((a, b) => a - b);
    const fragment = document.createDocumentFragment();
    let t = 0;
    let m = 0;
    for (let i = 0; i < points.length - 1; i += 1) {
      const start = points[i];
      const end = points[i + 1];
      while (t < tokens.length && tokens[t].end <= start) t += 1;
      while (m < matches.length && matches[m].end <= start) m += 1;
      const classes = [];
      if (t < tokens.length && tokens[t].start <= start) classes.push(`tok-${tokens[t].cls}`);
      if (m < matches.length && matches[m].start <= start) classes.push(m === current ? 'match current' : 'match');
      const piece = text.slice(start, end);
      fragment.append(classes.length ? el('span', {class: classes.join(' '), text: piece}) : document.createTextNode(piece));
    }
    fragment.append(document.createTextNode('\n')); // hauteur identique au textarea si le texte finit par \n
    target.replaceChildren(fragment);
  }

  let instances = 0;

  function create(root, options = {}) {
    instances += 1;
    const id = `editor-${instances}`;
    const label = options.label || 'Contenu du fichier';
    const state = {path: null, original: '', matches: [], current: -1, frame: 0, lang: 'plain'};

    const title = el('span', {class: 'editor-path mono', id: `${id}-path`, text: options.empty || 'Aucun fichier sélectionné'});
    const badge = el('span', {class: 'tag editor-modified', hidden: true, text: 'modifié'});
    const searchToggle = el('button', {type: 'button', class: 'editor-search-toggle', 'aria-expanded': 'false',
      'aria-controls': `${id}-search`, 'aria-keyshortcuts': 'Control+F', text: 'Rechercher'});
    const revert = el('button', {type: 'button', class: 'editor-revert', disabled: true, text: 'Rétablir le fichier généré'});
    const toolbar = el('div', {class: 'editor-toolbar'}, title, badge, el('span', {class: 'editor-spacer'}), searchToggle, revert);

    const query = el('input', {type: 'search', id: `${id}-query`, class: 'editor-query', autocomplete: 'off',
      'aria-label': 'Texte recherché', placeholder: 'Rechercher'});
    const replacement = el('input', {type: 'text', id: `${id}-replacement`, class: 'editor-replacement', autocomplete: 'off',
      'aria-label': 'Texte de remplacement', placeholder: 'Remplacer par'});
    const caseBox = el('input', {type: 'checkbox', id: `${id}-case`, class: 'editor-case'});
    const prev = el('button', {type: 'button', class: 'editor-prev', 'aria-label': 'Occurrence précédente', text: '↑'});
    const next = el('button', {type: 'button', class: 'editor-next', 'aria-label': 'Occurrence suivante', text: '↓'});
    const replaceOne = el('button', {type: 'button', class: 'editor-replace', text: 'Remplacer'});
    const replaceAll = el('button', {type: 'button', class: 'editor-replace-all', text: 'Tout remplacer'});
    const count = el('span', {class: 'editor-count muted', role: 'status', 'aria-live': 'polite'});
    const search = el('div', {class: 'editor-search', id: `${id}-search`, role: 'search', hidden: true},
      query, prev, next, el('label', {class: 'choice', for: `${id}-case`}, caseBox, ' Respecter la casse'),
      replacement, replaceOne, replaceAll, count);

    const gutter = el('pre', {class: 'editor-gutter', 'aria-hidden': 'true'});
    const layer = el('pre', {class: 'editor-layer', 'aria-hidden': 'true'});
    const area = el('textarea', {class: 'editor-input', id: options.id || `${id}-input`, wrap: 'off', spellcheck: 'false',
      autocomplete: 'off', autocapitalize: 'off', disabled: true, 'aria-label': label,
      'aria-describedby': `${id}-path ${id}-status`});
    const body = el('div', {class: 'editor-body'}, gutter, el('div', {class: 'editor-code'}, layer, area));
    const status = el('p', {class: 'editor-status muted', id: `${id}-status`});
    root.replaceChildren(el('div', {class: 'editor'}, toolbar, search, body, status));

    function render() {
      state.frame = 0;
      const text = area.value;
      paint(layer, text, tokenize(text, state.lang), state.matches, state.current);
      const lines = text.split('\n').length;
      gutter.textContent = Array.from({length: lines}, (_, index) => String(index + 1)).join('\n') + '\n';
      sync();
    }

    function schedule() {
      if (!state.frame) state.frame = requestAnimationFrame(render);
    }

    function sync() {
      layer.scrollTop = area.scrollTop;
      layer.scrollLeft = area.scrollLeft;
      gutter.scrollTop = area.scrollTop;
    }

    function caret() {
      if (state.path === null) { status.textContent = ''; return; }
      const before = area.value.slice(0, area.selectionStart);
      const line = before.split('\n').length;
      const column = before.length - before.lastIndexOf('\n');
      const total = area.value.split('\n').length;
      const plain = area.value.length > MAX_HIGHLIGHT ? ' · coloration désactivée (fichier volumineux)' : '';
      status.textContent = `Ligne ${line}, colonne ${column} · ${total} ligne(s) · ${LABELS[state.lang]}${plain}`;
    }

    function modified() {
      const changed = state.path !== null && area.value !== state.original;
      badge.hidden = !changed;
      revert.disabled = !changed;
      return changed;
    }

    function showCount() {
      const capped = state.matches.length >= MAX_MATCHES ? '+' : '';
      count.textContent = !query.value ? '' : state.matches.length
        ? `${state.current + 1} sur ${state.matches.length}${capped}` : 'Aucune occurrence';
      const none = !state.matches.length || area.disabled;
      [prev, next, replaceOne, replaceAll].forEach(button => { button.disabled = none; });
      schedule();
    }

    // Recalcule les occurrences ; l'occurrence courante reste la premiere a partir de `from`.
    function refreshMatches(from = 0) {
      state.matches = search.hidden ? [] : findAll(area.value, query.value, caseBox.checked);
      const index = state.matches.findIndex(m => m.start >= from);
      state.current = state.matches.length ? (index === -1 ? 0 : index) : -1;
      showCount();
    }

    function currentStart() {
      const match = state.matches[state.current];
      return match ? match.start : 0;
    }

    function reveal(index) {
      const target = state.matches[index];
      if (!target) return;
      area.setSelectionRange(target.start, target.end); // selection prete si l'utilisateur revient au texte
      const line = area.value.slice(0, target.start).split('\n').length - 1;
      const height = parseFloat(getComputedStyle(area).lineHeight) || 18;
      const top = line * height;
      if (top < area.scrollTop || top > area.scrollTop + area.clientHeight - height * 2) {
        area.scrollTop = Math.max(0, top - area.clientHeight / 3);
      }
      sync();
    }

    function step(delta) {
      if (!state.matches.length) return;
      state.current = (state.current + delta + state.matches.length) % state.matches.length;
      showCount();
      reveal(state.current);
    }

    function emit() {
      modified();
      caret();
      if (options.onChange && state.path !== null) options.onChange(state.path, area.value);
    }

    function replaceCurrent() {
      const target = state.matches[state.current];
      if (!target) return;
      area.value = area.value.slice(0, target.start) + replacement.value + area.value.slice(target.end);
      refreshMatches(target.start + replacement.value.length);
      emit();
      reveal(state.current);
    }

    function replaceEvery() {
      const matches = findAll(area.value, query.value, caseBox.checked);
      if (!matches.length) return;
      let text = area.value;
      for (let i = matches.length - 1; i >= 0; i -= 1) {
        text = text.slice(0, matches[i].start) + replacement.value + text.slice(matches[i].end);
      }
      area.value = text;
      refreshMatches(0);
      count.textContent = `${matches.length} remplacement(s)` + (state.matches.length ? ` · ${state.matches.length} restante(s)` : '');
      emit();
    }

    function openSearch() {
      search.hidden = false;
      searchToggle.setAttribute('aria-expanded', 'true');
      const selection = area.value.slice(area.selectionStart, area.selectionEnd);
      if (selection && !selection.includes('\n')) query.value = selection;
      refreshMatches(area.selectionStart);
      query.focus();
      query.select();
    }

    function closeSearch() {
      search.hidden = true;
      searchToggle.setAttribute('aria-expanded', 'false');
      refreshMatches(0);
      area.focus();
    }

    area.addEventListener('input', () => { refreshMatches(currentStart()); emit(); });
    area.addEventListener('scroll', sync);
    ['keyup', 'click', 'select'].forEach(type => area.addEventListener(type, caret));
    area.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') { event.preventDefault(); openSearch(); }
    });
    search.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); closeSearch(); }
    });
    query.addEventListener('input', () => { refreshMatches(area.selectionStart); reveal(state.current); });
    query.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); step(event.shiftKey ? -1 : 1); }
    });
    caseBox.addEventListener('change', () => refreshMatches(currentStart()));
    prev.addEventListener('click', () => step(-1));
    next.addEventListener('click', () => step(1));
    replaceOne.addEventListener('click', replaceCurrent);
    replaceAll.addEventListener('click', replaceEvery);
    searchToggle.addEventListener('click', () => (search.hidden ? openSearch() : closeSearch()));
    revert.addEventListener('click', () => {
      area.value = state.original;
      refreshMatches(0);
      emit();
      area.focus();
    });

    const api = {
      // Meme fichier et meme texte : rien ne bouge (curseur et defilement conserves).
      setFile(path, content, original) {
        if (path === state.path && content === area.value && original === state.original) return;
        const same = path === state.path;
        state.path = path;
        state.original = original === undefined ? content : original;
        state.lang = language(path);
        area.disabled = path === null;
        area.value = path === null ? '' : content;
        title.textContent = path === null ? (options.empty || 'Aucun fichier sélectionné') : path;
        if (!same) { area.scrollTop = 0; area.scrollLeft = 0; area.setSelectionRange(0, 0); }
        modified();
        caret();
        refreshMatches(same ? currentStart() : 0);
        render();
      },
      value: () => area.value,
      path: () => state.path,
      focus: () => area.focus(),
      openSearch,
      matches: () => state.matches.map(m => ({...m})),
      current: () => state.current,
      textarea: area,
    };
    return api;
  }

  window.ForgeEditor = {create, tokenize, findAll, language};
}());
