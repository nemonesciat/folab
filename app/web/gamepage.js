// ---------- The Game page: New Vegas's own settings (Fallout.ini and FalloutPrefs.ini) ----------
// The screen (fullscreen, window or borderless, which screen, what size) first, then the settings people change
// most, then every setting of both files to search. Nothing is written until Save; FOLab keeps a copy first.
const G = {d: null, changes: {}, mode: null, screen: 0, res: null};
const gsId = (sec, key) => (sec + '|' + key).toLowerCase();   // (one change, whichever list it was made in)

async function drawGamePage(){
  const el = $('#page-game');
  el.innerHTML = '<div class="note" style="padding:24px">Reading the game\'s settings…</div>';
  try { G.d = await api('/api/gamesettings'); } catch (e){ el.innerHTML = ''; return fail(e); }
  G.changes = {};
  const d = G.d, v = id => (d.settings.find(s => s.id === id) || {}).value;
  G.mode = d.borderless !== null && d.borderless !== undefined ? 'borderless' : v('fullscreen') === '1' ? 'full' : 'window';
  G.screen = G.mode === 'borderless' ? +d.borderless : Math.min(+(v('adapter') || 0), Math.max(d.screens.length - 1, 0));
  G.res = [+(v('width') || 1280), +(v('height') || 720)];
  drawGame();
}

function screenName(s, i){
  const where = s.primary ? 'Main screen' : s.x < 0 ? 'Screen on the left' : s.x > 0 ? 'Screen on the right' : 'Screen ' + (i + 1);
  return `${where} · ${s.w}×${s.h} · ${s.hz} Hz`;
}

function drawGame(){
  const d = G.d, sc = d.screens[G.screen] || {modes: []};
  const own = new Set(['fullscreen', 'width', 'height', 'adapter']);
  const groups = {};
  for (const s of d.settings) if (!own.has(s.id)) (groups[s.group] = groups[s.group] || []).push(s);
  const modes = sc.modes.some(m => m[0] === G.res[0] && m[1] === G.res[1]) ? sc.modes : [G.res].concat(sc.modes);
  $('#page-game').innerHTML = `
    <h2>Game settings</h2>
    <p class="note" style="padding:0">New Vegas's own settings, in ${esc(d.folder)} (${d.files.map(esc).join(' and ')}).
      FOLab changes only the lines you change and keeps a copy of both files first.${d.running ? ' <b style="color:var(--red)">The game is running: close it to save.</b>' : ''}</p>
    <div class="card"><h3>Screen</h3>
      <p class="gs-modes">
        <label><input type="radio" name="gs-mode" value="full" ${G.mode === 'full' ? 'checked' : ''}> Fullscreen</label>
        <label><input type="radio" name="gs-mode" value="borderless" ${G.mode === 'borderless' ? 'checked' : ''}> Borderless window</label>
        <label><input type="radio" name="gs-mode" value="window" ${G.mode === 'window' ? 'checked' : ''}> Window</label></p>
      <p>${G.mode === 'borderless' ? `The game has no borderless mode of its own: it runs as a window the screen's size, and FOLab takes the frame off when it starts the game (<b>Open in game</b> or <b>Play here</b>). Started any other way, it keeps its frame. Alt+Tab is instant and the other screen stays usable.`
         : G.mode === 'full' ? 'The game takes the screen over. Alt+Tab is slower, and the game may lose its sound or picture for a moment.'
         : 'A window with a frame, where Window left/top put it.'}</p>
      <div class="gs-grid">
        <label>Screen</label><select id="gs-screen">${d.screens.map((s, i) => `<option value="${i}" ${i === G.screen ? 'selected' : ''}>${esc(screenName(s, i))}</option>`).join('')}</select>
        ${G.mode === 'borderless' ? `<label>Size</label><span>${sc.w}×${sc.h} (the screen's)</span>`
          : `<label>Resolution</label><select id="gs-res">${modes.map(m => `<option value="${m[0]}x${m[1]}" ${m[0] === G.res[0] && m[1] === G.res[1] ? 'selected' : ''}>${m[0]}×${m[1]}</option>`).join('')}</select>`}
      </div>
      ${sc.w >= 3000 && G.res[0] >= 3000 ? '<p style="color:var(--red)">4K in New Vegas needs a lot of the 32-bit game; with the Discord overlay on it has crashed before.</p>' : ''}
    </div>
    ${Object.entries(groups).map(([g, rows]) => `<div class="card"><h3>${esc(g)}</h3><div class="gs-grid">${rows.map(settingRow).join('')}</div></div>`).join('')}
    <div class="card"><h3>Every setting</h3>
      <p>All ${d.all.length} settings of both files. Where both have one, FalloutPrefs.ini's is the one the game uses; a change here goes into both.</p>
      <input class="find" id="gs-find" placeholder="Search settings: fov, shadow, grass, audio…" style="margin:6px 0;width:100%">
      <div id="gs-all"></div></div>
    <div class="gs-save"><button class="btn primary" id="gs-save">Save settings</button>
      <button class="btn" id="gs-undo">Forget my changes</button> <span id="gs-n" class="note" style="padding:0"></span></div>`;
  document.querySelectorAll('input[name="gs-mode"]').forEach(r => r.onchange = () => { G.mode = r.value; drawGame(); countGame(); });
  $('#gs-screen').onchange = e => {
    G.screen = +e.target.value;
    const s = d.screens[G.screen];
    if (s && !s.modes.some(m => m[0] === G.res[0] && m[1] === G.res[1])) G.res = s.modes[0] || G.res;
    drawGame(); countGame();
  };
  if ($('#gs-res')) $('#gs-res').onchange = e => { G.res = e.target.value.split('x').map(Number); countGame(); };
  $('#page-game').querySelectorAll('[data-set]').forEach(bindSetting);
  $('#gs-find').oninput = drawAll;
  $('#gs-save').onclick = saveGame;
  $('#gs-undo').onclick = drawGamePage;
  drawAll(); countGame();
}

function settingRow(s){
  const ch = G.changes[gsId(s.section, s.key)], cur = ch ? ch[2] : s.value, k = esc(s.key), none = cur === null || cur === undefined;
  let input;
  if (s.kind === 'bool') input = `<label><input type="checkbox" data-set="${k}" ${+cur ? 'checked' : ''}> on</label>`;
  else if (s.kind === 'intro') input = `<label><input type="checkbox" data-set="${k}" ${cur ? 'checked' : ''}> play it</label>`;
  else if (s.kind === 'choice') input = `<select data-set="${k}">${(s.options.includes(+cur) || none ? s.options : [+cur].concat(s.options)).map(o => `<option ${+cur === o ? 'selected' : ''}>${o}</option>`).join('')}</select>`;
  else if (s.kind === 'float' && s.options) input = `<span class="gs-range"><input type="range" data-set="${k}" min="${s.options[0]}" max="${s.options[1]}" step="${s.options[1] - s.options[0] <= 1 ? 0.05 : 1}" value="${none ? s.options[0] : parseFloat(cur)}"><b>${none ? '—' : +parseFloat(cur).toFixed(2)}</b></span>`;
  else input = `<input data-set="${k}" value="${none ? '' : esc(cur)}" style="width:110px">`;
  return `<label title="[${esc(s.section)}] ${k}">${esc(s.label)}</label><span>${input}${s.note ? ` <small class="note" style="padding:0">${esc(s.note)}</small>` : ''}</span>`;
}

function bindSetting(el){
  const s = G.d.settings.find(x => x.key === el.dataset.set);
  const set = val => {
    if (String(val) === String(s.value ?? '')) delete G.changes[gsId(s.section, s.key)];
    else G.changes[gsId(s.section, s.key)] = [s.section, s.key, String(val)];
    countGame();
  };
  el.oninput = el.onchange = () => {
    if (s.kind === 'bool') set(el.checked ? 1 : 0);
    else if (s.kind === 'intro') set(el.checked ? G.d.intro : '');
    else if (el.type === 'range'){
      const n = (+el.value).toFixed(4);
      el.nextElementSibling.textContent = +(+el.value).toFixed(2);
      set(parseFloat(s.value) === +el.value ? s.value : n);
    } else set(el.value);
  };
}

function drawAll(){
  const q = ($('#gs-find').value || '').toLowerCase().trim();
  const rows = G.d.all.filter(r => !q || (r.section + ' ' + r.key).toLowerCase().includes(q));
  const shown = rows.slice(0, q ? 300 : 60);
  $('#gs-all').innerHTML = `<table class="gs-table">${shown.map((r, i) => {
    const id = gsId(r.section, r.key), ch = G.changes[id];
    const val = ch ? ch[2] : (r.files['FalloutPrefs.ini'] ?? r.files['Fallout.ini']);
    const both = Object.keys(r.files).length > 1 && r.files['FalloutPrefs.ini'] !== r.files['Fallout.ini'];
    return `<tr><td class="note" style="padding:0 8px 0 0">${esc(r.section)}</td><td>${esc(r.key)}</td>
      <td><input data-raw="${i}" value="${esc(val)}" ${ch ? 'class="changed"' : ''}></td>
      <td class="note" style="padding:0">${both ? `Fallout.ini has ${esc(r.files['Fallout.ini'])}` : Object.keys(r.files).length === 1 ? 'only in ' + esc(Object.keys(r.files)[0]) : ''}</td></tr>`;
  }).join('')}</table>${rows.length > shown.length ? `<p class="note" style="padding:0">${rows.length - shown.length} more: search to narrow it down.</p>` : ''}`;
  $('#gs-all').querySelectorAll('[data-raw]').forEach(inp => inp.oninput = () => {
    const r = shown[+inp.dataset.raw], id = gsId(r.section, r.key);
    const was = r.files['FalloutPrefs.ini'] ?? r.files['Fallout.ini'];
    if (inp.value === was) delete G.changes[id]; else G.changes[id] = [r.section, r.key, inp.value];
    inp.classList.toggle('changed', inp.value !== was);
    countGame();
  });
}

function screenChanges(){
  // what the Screen card asks for, as settings; borderless goes as its own setting (the server fills in the rest)
  const d = G.d, v = id => (d.settings.find(s => s.id === id) || {}).value, out = [];
  const want = x => (k, val) => { if (String(v(k)) !== String(val)) out.push(['Display', x(k), String(val)]); };
  const key = id => d.settings.find(s => s.id === id).key, put = want(key);
  if (G.mode === 'borderless') return {changes: out, borderless: G.screen};
  put('fullscreen', G.mode === 'full' ? 1 : 0);
  put('width', G.res[0]); put('height', G.res[1]);
  put('adapter', G.screen);
  return {changes: out, borderless: null};
}

function countGame(){
  const sc = screenChanges(), was = G.d.borderless ?? null;
  const n = Object.keys(G.changes).length + sc.changes.length + (sc.borderless !== was ? 1 : 0);
  $('#gs-n').textContent = n ? `${n} change${n === 1 ? '' : 's'} not saved yet` : 'Nothing changed';
  $('#gs-save').disabled = !n;
}

async function saveGame(){
  const sc = screenChanges(), body = {changes: Object.values(G.changes).concat(sc.changes)};
  if (sc.borderless !== (G.d.borderless ?? null)) body.borderless = sc.borderless;
  try {
    const d = await post('/api/gamesettings', body);
    toast('Game settings saved. A copy of the old files is in FOLab\'s backups.');
    G.d = d; drawGamePage();
  } catch (e){ fail(e); }
}
