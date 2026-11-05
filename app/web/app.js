// ---------- FOLab: the editor around the 3D view ----------
// Places and Objects on the left, Place and Selected on the right, the mod's controls up top. Every change goes to
// the server as one undoable step; the view is then brought in line with what the server answers.
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const A = {state: null, places: [], cellId: null, sel: [], recent: [], clip: null};
try { A.recent = JSON.parse(localStorage.getItem('folab-recent') || '[]'); } catch (e) {}

async function post(path, body){
  const r = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})});
  const d = await r.json();
  if (!r.ok || d.error) throw new Error(d.error || r.status);
  return d;
}

let toastTimer;
function toast(msg, err){
  const t = $('#toast');
  t.textContent = msg; t.className = err ? 'err' : ''; t.style.display = 'block';
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.style.display = 'none'; }, err ? 6000 : 2500);
}
function fail(e){ toast(e.message || String(e), true); }

// ---------- the mod: state up top ----------
function setState(s){
  A.state = s;
  const p = s.project;
  $('#welcome').style.display = p ? 'none' : 'flex';
  $('#modpill').innerHTML = p ? `✎ <b>${esc(p.plugin)}</b> · ${p.changes} change${p.changes === 1 ? '' : 's'}` : 'No mod open';
  $('#b-undo').disabled = !(p && p.undo); $('#b-undo').title = p && p.undo ? `Undo ${p.undo} (Ctrl+Z)` : 'Nothing to undo';
  $('#b-redo').disabled = !(p && p.redo); $('#b-redo').title = p && p.redo ? `Redo ${p.redo} (Ctrl+Y)` : 'Nothing to redo';
  $('#b-save').disabled = $('#b-install').disabled = !p;
  const g = $('#gamepill'), i = s.installed;
  if (!p || !i){ g.style.display = 'none'; }
  else {
    g.style.display = '';
    if (i.installed && i.active && i.current && p.built){ g.className = 'pill ok'; g.textContent = '● In game'; }
    else if (i.installed){ g.className = 'pill warn'; g.textContent = '● In game, out of date'; }
    else { g.className = 'pill'; g.textContent = 'Not in game'; }
  }
  if ($('#page-mod').style.display === 'block') drawModPage();
}

async function refreshState(){ setState(await api('/api/state')); }

async function newMod(name){
  if (!name.trim()) return toast('Give your mod a name first.', true);
  try { setState(await post('/api/project/new', {name})); await loadPlaces(); if (A.cellId) openPlace(A.cellId); toast('Started ' + A.state.project.plugin); }
  catch (e){ fail(e); }
}
async function openMod(name){
  try { setState(await post('/api/project/open', {name})); if (typeof BW !== 'undefined') BW.types = []; await loadPlaces(); if (A.cellId) openPlace(A.cellId); }
  catch (e){ fail(e); }
}

async function save(){
  try { const d = await post('/api/save'); setState(d.state); toast(`Saved ${d.path.split(/[\\/]/).pop()} (${(d.bytes / 1024).toFixed(1)} KB)`); }
  catch (e){ fail(e); }
}
async function install(){
  try {
    const d = await post('/api/install'); setState(d.state);
    toast('In the game: start or load a save, open the console (~) and type  coc ' + (A.cellEdid || 'TheCellName'));
  } catch (e){ fail(e); }
}
async function undoRedo(which){
  try {
    const d = await post('/api/' + which);
    setState(d.state);
    if (d.label) toast((which === 'undo' ? 'Undid ' : 'Redid ') + d.label);
    await resync();
  } catch (e){ fail(e); }
}

// ---------- places ----------
async function loadPlaces(){ A.places = await api('/api/interiors'); drawPlaces(); }
function drawPlaces(){
  const f = $('#f-places').value.toLowerCase(), list = $('#places');
  const rows = A.places.filter(c => !f || (c.edid + ' ' + c.name).toLowerCase().includes(f));
  rows.sort((a, b) => (b.mine - a.mine) || a.edid.localeCompare(b.edid));
  list.innerHTML = rows.map(c => `<div class="row${c.id === A.cellId ? ' on' : ''}" data-id="${esc(c.id)}"><div>${c.mine ? '<span class="dot moved" title="Your mod changes this place"></span>' : ''}${esc(c.name || c.edid)}<small>${esc(c.edid)} · ${esc(c.plugin)}</small></div><span class="n">${c.refs}</span></div>`).join('');
}
$('#places').addEventListener('click', e => { const r = e.target.closest('.row'); if (r) openPlace(r.dataset.id); });
$('#f-places').addEventListener('input', drawPlaces);

async function openPlace(id, at){
  A.cellId = id;
  try { localStorage.setItem('folab-cell', id); } catch (e) {}
  drawPlaces();
  $('#s-load').textContent = 'loading…';
  const c = await api('/api/cell?id=' + encodeURIComponent(id));
  A.cellEdid = c.edid;
  const place = A.places.find(p => p.id === id);
  $('#s-place').textContent = (place && place.name ? place.name + ' · ' : '') + c.edid;
  A.things = c.things;
  drawObjects();
  await openCell(c, (n, of) => { $('#s-load').textContent = n < of ? `${n} / ${of} loaded` : `${of} things`; }, at);
}

async function resync(){
  if (!A.cellId) return;
  const c = await api('/api/cell?id=' + encodeURIComponent(A.cellId));
  A.things = c.things;
  syncCell(c.things);
  drawObjects();
  drawSelected(selThings());
  const p = A.places.find(p => p.id === A.cellId);
  if (p) { p.mine = A.things.some(t => t.state); drawPlaces(); }
}

// ---------- objects in this place ----------
function drawObjects(){
  const f = $('#f-objects').value.toLowerCase(), list = $('#objects');
  const rows = (A.things || []).filter(t => (!t.marker || W.show.markers) && (t.state !== 'removed' || W.show.removed || A.sel.includes(t.key)))
    .filter(t => !f || (t.base + ' ' + t.name + ' ' + t.type).toLowerCase().includes(f));
  rows.sort((a, b) => (!!b.state - !!a.state) || a.base.localeCompare(b.base));
  $('#objn').textContent = rows.length;
  list.innerHTML = rows.slice(0, 1500).map(t => `<div class="row${A.sel.includes(t.key) ? ' on' : ''}" data-key="${esc(t.key)}"><div>${t.state ? `<span class="dot ${t.state}" title="${t.state}"></span>` : ''}${esc(t.base)}<small>${esc(t.name || t.type)}</small></div><span class="n">${t.type}</span></div>`).join('');
}
$('#objects').addEventListener('click', e => {
  const r = e.target.closest('.row'); if (!r) return;
  const k = r.dataset.key;
  if (e.shiftKey) select(A.sel.includes(k) ? A.sel.filter(x => x !== k) : A.sel.concat(k));
  else { select([k]); focusSel(); }
});
$('#f-objects').addEventListener('input', drawObjects);

// ---------- selected ----------
const deg = r => Math.round(r * 180 / Math.PI * 100) / 100;
function drawSelected(list){
  const box = $('#selected');
  if (!list.length){ box.innerHTML = '<div class="note">Click a thing in the view or in Objects. Shift adds; drag on empty space to select with a box.</div>'; return; }
  if (list.length > 1){
    const kinds = {}; for (const t of list) kinds[t.type] = (kinds[t.type] || 0) + 1;
    box.innerHTML = `<div class="h">${list.length} selected</div>
      <div class="kv">${Object.entries(kinds).map(([k, n]) => `${n} ${esc(k)}`).join(' · ')}</div>
      <div class="acts"><button class="btn" data-a="drop">⤓ Drop down</button><button class="btn" data-a="dup">⧉ Duplicate</button>
      <button class="btn" data-a="del">✕ Remove</button><button class="btn" data-a="focus">Focus</button><button class="btn" data-a="hide">Hide</button></div>`;
    return;
  }
  const t = list[0];
  const what = {'': 'From the game', moved: 'Moved by your mod', new: 'Added by your mod', removed: 'Removed by your mod'}[t.state];
  box.innerHTML = `
    <div class="h">${esc(t.type)}</div>
    <div class="kv"><b>${esc(t.base)}</b>${t.name ? ' — ' + esc(t.name) : ''}</div>
    <div class="kv"><span>${what}</span></div>
    <div class="kv"><span>Ref</span> ${esc(t.key)}</div>
    <div class="kv" title="${esc(t.model)}"><span>Mesh</span> ${esc(t.model.split('\\').pop())}</div>
    <div class="fields">
      <label>Position</label><input data-i="0" value="${t.p[0].toFixed(1)}"><input data-i="1" value="${t.p[1].toFixed(1)}"><input data-i="2" value="${t.p[2].toFixed(1)}">
      <label>Turn °</label><input data-i="3" value="${deg(t.p[3])}"><input data-i="4" value="${deg(t.p[4])}"><input data-i="5" value="${deg(t.p[5])}">
      <label>Scale</label><input data-i="s" value="${(t.s || 1).toFixed(3)}"><span></span><span></span>
    </div>
    <div class="acts">
      ${t.state === 'removed' ? '<button class="btn" data-a="restore">Restore</button>' : `
      <button class="btn" data-a="drop">⤓ Drop down</button><button class="btn" data-a="dup">⧉ Duplicate</button>
      <button class="btn" data-a="del">✕ Remove</button>`}
      ${t.state === 'moved' ? '<button class="btn" data-a="revert" title="Put it back where the game has it">↺ As the game has it</button>' : ''}
      <button class="btn" data-a="focus">Focus</button>
      <button class="btn" data-a="record" title="Open ${esc(t.base)}'s record on the Browse page">Open its record</button>
    </div>
    <div id="sel-rec"></div>`;
  selRecord(t);
}

// ---------- the selected thing's record: its main values, editable here ----------
// (what each kind is most often changed for; the rest is on the Browse page)
const KEY_FIELDS = {
  WEAP: [['DATA', 'Damage'], ['DATA', 'Value'], ['DATA', 'Weight'], ['DATA', 'Health'], ['DATA', 'Clip size'], ['CRDT', 'Critical damage']],
  ARMO: [['DATA', 'Value'], ['DATA', 'Weight'], ['DATA', 'Health'], ['DNAM', 'DT'], ['DNAM', 'DR']],
  AMMO: [['DATA', 'Value'], ['DATA', 'Clip rounds']], ALCH: [['ENIT', 'Value'], ['DATA', 'Weight']],
  MISC: [['DATA', 'Value'], ['DATA', 'Weight']], KEYM: [['DATA', 'Value'], ['DATA', 'Weight']], BOOK: [['DATA', 'Value'], ['DATA', 'Weight']],
  CONT: [['DATA', 'Weight']],
  NPC_: [['ACBS', 'Level'], ['DATA', 'Health'], ['ACBS', 'Karma'], ['ACBS', 'Barter gold'], ['AIDT', 'Aggression'], ['AIDT', 'Confidence']],
  CREA: [['ACBS', 'Level'], ['DATA', 'Health'], ['DATA', 'Damage'], ['AIDT', 'Aggression'], ['AIDT', 'Confidence']],
  LIGH: [['DATA', 'Radius'], ['DATA', 'Red'], ['DATA', 'Green'], ['DATA', 'Blue'], ['DATA', 'Falloff exponent'], ['DATA', 'FOV']],
};
const REC_CACHE = {};
function recCacheDrop(key){ delete REC_CACHE[key]; }
async function selRecord(t){
  const want = KEY_FIELDS[t.type], box = $('#sel-rec');
  if (!box || !t.bkey) return;
  if (!REC_CACHE[t.bkey]) REC_CACHE[t.bkey] = api('/api/record?key=' + encodeURIComponent(t.bkey)).catch(() => null);
  const d = await REC_CACHE[t.bkey];
  if (!d || A.sel.length !== 1 || A.sel[0] !== t.key || !$('#sel-rec')) return;
  const rows = [];
  for (const [tag, name] of want || []){
    const si = d.record.subs.findIndex(s => s.tag === tag && s.kind === 'struct' && s.fields.some(f => f.name === name));
    if (si < 0) continue;
    const fi = d.record.subs[si].fields.findIndex(f => f.name === name), f = d.record.subs[si].fields[fi];
    // (a character set to level with the player keeps a multiplier there: 1000 is the player's own level)
    const pcMult = name === 'Level' && (d.record.subs[si].fields.find(x => x.name === 'Flags') || {}).value & 0x80;
    rows.push(`<label title="${pcMult ? 'Levels with the player: 1000 is the same level, 500 half' : ''}">${pcMult ? 'Level × player (1000 = same)' : esc(name)}</label><input data-rs="${si}" data-rf="${fi}" value="${f.code === 'f' ? +(+f.value).toPrecision(6) : f.value}" ${d.editable ? '' : 'disabled'}>`);
  }
  const what = d.state === 'changed' ? ' · changed by your mod' : d.state === 'new' ? ' · your own' : '';
  $('#sel-rec').innerHTML = `<div class="h">Record${what}</div>` + (rows.length ? `<div class="recgrid">${rows.join('')}</div>
    <div class="note">Changing these changes ${esc(t.base)} everywhere it's used.</div>` : `<div class="note">Its values are on the Browse page.</div>`);
}
$('#selected').addEventListener('change', async e => {
  const si = e.target.dataset.rs; if (si === undefined || W.sel.length !== 1) return;
  const t = W.sel[0].userData.thing, d = await REC_CACHE[t.bkey];
  const rec = JSON.parse(JSON.stringify(d.record)), f = rec.subs[+si].fields[+e.target.dataset.rf];
  const v = f.code === 'f' ? parseFloat(e.target.value) : parseInt(e.target.value, 10);
  if (isNaN(v)) return toast(`${f.name}: that isn't a number`, true);
  f.value = v;
  try {
    const r = await post('/api/record/save', {key: t.bkey, record: rec});
    setState(r.state); recCacheDrop(t.bkey); toast(`${t.base}: ${f.name} ${v}`);
    if (t.type === 'LIGH' && typeof lightsRefresh === 'function') lightsRefresh();
    selRecord(t);
  } catch (err){ fail(err); }
});
function openRecord(key){ page('browse'); browseInit().then(() => bwOpen(key)); }
$('#selected').addEventListener('change', e => {
  const i = e.target.dataset.i; if (i === undefined || W.sel.length !== 1) return;
  const t = W.sel[0].userData.thing, p = t.p.slice(), v = parseFloat(e.target.value);
  if (isNaN(v)) return drawSelected(selThings());
  if (i === 's') return sendMoves([[t, p, Math.max(0.01, Math.min(10, v))]], 'Scale');
  p[+i] = +i >= 3 ? v * Math.PI / 180 : v;
  sendMoves([[t, p]], +i >= 3 ? 'Turn' : 'Move');
});
$('#selected').addEventListener('click', e => {
  const a = e.target.dataset.a; if (!a) return;
  ({drop: dropSel, dup: dupSel, del: delSel, focus: focusSel, hide: hideSel, restore: revertSel, revert: revertSel,
    record: () => { const t = selThings()[0]; if (t) openRecord(t.bkey); }})[a]();
});

W.onSelect = list => {
  A.sel = list.map(t => t.key);
  drawSelected(list);
  if (list.length) tab('right', 'selected');
  document.querySelectorAll('#objects .row').forEach(r => r.classList.toggle('on', A.sel.includes(r.dataset.key)));
};

// ---------- edits ----------
async function edit(label, ops, selectNew){
  if (!A.state.project) return toast('Start a mod first.', true);
  try {
    const d = await post('/api/edit', {label, ops});
    setState(d.state);
    for (const t of d.things || []){
      const i = (A.things || []).findIndex(x => x.key === t.key);
      if (i >= 0) A.things[i] = t; else (A.things = A.things || []).push(t);
      await updateThing(t);
    }
    for (const o of ops) if (o.op === 'remove' && o.ref.startsWith('+')){ dropThing(o.ref); A.things = A.things.filter(t => t.key !== o.ref); }
    drawObjects();
    const p = A.places.find(p => p.id === A.cellId); if (p && !p.mine){ p.mine = true; drawPlaces(); }
    if (selectNew && d.made.length) select(d.made);
    else drawSelected(selThings());
    return d;
  } catch (e){ fail(e); resync(); }
}

// moves: [[thing, p, scale?]]: one undo step
function sendMoves(moves, label){
  return edit(label, moves.map(([t, p, s]) => {
    const op = {op: 'move', cell: A.cellId, ref: t.key, p};
    if (s !== undefined) op.s = s; else if (t.state === 'new' || t.s !== 1) op.s = t.s;
    return op;
  }));
}
W.onMove = (moves, label) => sendMoves(moves, label);

function needSel(){ if (!W.sel.length){ toast('Select something first.', true); return false; } return true; }
function dropSel(){
  if (!needSel()) return;
  const moves = [];
  for (const g of W.sel){ const z = dropDown(g); if (z !== null){ const t = g.userData.thing, p = t.p.slice(); p[2] = Math.round(z * 100) / 100; moves.push([t, p]); } }
  if (!moves.length) return toast('Nothing below to set it on.', true);
  sendMoves(moves, 'Drop down');
}
function dupSel(){
  if (!needSel()) return;
  const step = +$('#t-grid').value || 32;
  edit('Duplicate', selThings().map(t => { const p = t.p.slice(); p[0] += step; return {op: 'add', cell: A.cellId, base: t.bkey, p, s: t.s || 1}; }), true);
}
function delSel(){
  if (!needSel()) return;
  const keys = A.sel.slice(); select([]);
  edit(keys.length > 1 ? `Remove ${keys.length}` : 'Remove', keys.map(k => ({op: 'remove', cell: A.cellId, ref: k})));
}
function revertSel(){
  const keys = selThings().filter(t => t.state === 'moved' || t.state === 'removed').map(t => t.key);
  if (keys.length) edit('Put back', keys.map(k => ({op: 'revert', cell: A.cellId, ref: k})));
}
function hideSel(){ if (needSel()){ const n = A.sel.length; hideKeys(A.sel); toast(`Hidden ${n} (for now). Shift+H shows them again.`); } }

// copy and paste: the things' bases, turns and sizes, kept in their places relative to each other
function copySel(){
  if (!needSel()) return;
  A.clip = selThings().map(t => ({base: t.bkey, p: t.p.slice(), s: t.s || 1, name: t.base}));
  toast(`Copied ${A.clip.length}`);
}
function paste(){
  if (!A.clip || !A.clip.length) return toast('Copy something first (Ctrl+C).', true);
  const at = pointUnder(W.mouse), lo = Math.min(...A.clip.map(c => c.p[2]));
  const cx = A.clip.reduce((s, c) => s + c.p[0], 0) / A.clip.length, cy = A.clip.reduce((s, c) => s + c.p[1], 0) / A.clip.length;
  edit(A.clip.length > 1 ? `Paste ${A.clip.length}` : 'Paste ' + A.clip[0].name, A.clip.map(c => {
    const p = c.p.slice(); p[0] += at.x - cx; p[1] += at.y - cy; p[2] += at.z - lo;
    return {op: 'add', cell: A.cellId, base: c.base, p: p.map(v => Math.round(v * 100) / 100), s: c.s};
  }), true);
}

// ---------- placing ----------
function remember(item){
  A.recent = [item, ...A.recent.filter(r => r.key !== item.key)].slice(0, 12);
  try { localStorage.setItem('folab-recent', JSON.stringify(A.recent)); } catch (e) {}
  drawRecent();
}
function placeRow(it){ return `<div class="row" draggable="true" data-key="${esc(it.key)}" title="${esc(it.model)} · click, then click where it goes, or drag it into the view"><div>${esc(it.edid)}<small>${esc(it.name || '')}</small></div><span class="n">${esc(it.type)}</span></div>`; }
function drawRecent(){ $('#recent-h').style.display = A.recent.length ? '' : 'none'; $('#recent').innerHTML = A.recent.map(placeRow).join(''); }
let found = [], searchTimer;
async function searchPlace(){
  const q = $('#f-place').value.trim(), kind = $('#f-kind').value;
  if (!q && !kind){ $('#found').innerHTML = ''; found = []; return; }
  found = await api(`/api/search?q=${encodeURIComponent(q)}&kind=${kind}`);
  $('#found').innerHTML = found.length ? found.map(placeRow).join('') : '<div class="note">Nothing found.</div>';
}
$('#f-place').addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(searchPlace, 200); });
$('#f-kind').addEventListener('change', searchPlace);
const findItem = key => found.concat(A.recent).find(x => x.key === key);
function pickToPlace(e){
  const r = e.target.closest('.row'); if (!r) return;
  const it = findItem(r.dataset.key);
  if (!A.cellId) return toast('Open a place first.', true);
  if (A.swapping){
    const t = A.swapping; swapEnd(); remember(it);
    return edit(`Swap ${t.base} for ${it.edid}`, [{op: 'swap', cell: A.cellId, ref: t.key, base: it.key}]);
  }
  document.querySelectorAll('#tab-place .row').forEach(x => x.classList.toggle('on', x === r));
  startPlacing(it);
  W.ren.domElement.focus();
  const h = $('#hint'); h.textContent = `Click where ${it.edid} goes · Esc or right-click stops`; h.style.display = 'block';
}
for (const id of ['#found', '#recent']){
  $(id).addEventListener('click', pickToPlace);
  $(id).addEventListener('dragstart', e => { const r = e.target.closest('.row'); if (r){ e.dataTransfer.setData('text/x-folab', r.dataset.key); e.dataTransfer.effectAllowed = 'copy'; } });
}
W.onPlace = (item, p) => {
  if (!item){ $('#hint').style.display = 'none'; document.querySelectorAll('#tab-place .row.on').forEach(x => x.classList.remove('on')); return; }
  remember(item);
  edit('Place ' + item.edid, [{op: 'add', cell: A.cellId, base: item.key, p, s: 1}]);
};
W.onDropItem = async (key, e) => {
  const it = findItem(key); if (!it || !A.cellId) return;
  const at = pointUnder(e), lift = await modelLift(it.model, it), g = +$('#t-grid').value, s = v => g ? Math.round(v / g) * g : v;
  remember(it);
  edit('Place ' + it.edid, [{op: 'add', cell: A.cellId, base: it.key, p: [s(at.x), s(at.y), at.z + lift, 0, 0, 0].map(v => Math.round(v * 100) / 100), s: 1}], true);
};

// ---------- tools ----------
function setTool(m){ setMode(m); $('#t-move').classList.toggle('on', m === 'translate'); $('#t-turn').classList.toggle('on', m === 'rotate'); }
$('#t-move').onclick = () => setTool('translate');
$('#t-turn').onclick = () => setTool('rotate');
function snapNow(){ setSnap(+$('#t-grid').value, +$('#t-angle').value); try { localStorage.setItem('folab-snap', $('#t-grid').value + ',' + $('#t-angle').value); } catch (e) {} }
$('#t-grid').onchange = $('#t-angle').onchange = snapNow;
$('#t-drop').onclick = dropSel; $('#t-dup').onclick = dupSel; $('#t-del').onclick = delSel;
$('#t-markers').onchange = e => { setShow('markers', e.target.checked); drawObjects(); };
$('#t-removed').onchange = e => { setShow('removed', e.target.checked); drawObjects(); };
$('#t-light').onchange = e => { setGameLight(e.target.checked); try { localStorage.setItem('folab-light', e.target.checked ? '1' : '0'); } catch (err) {} };
function lightsRefresh(){ resync(); }
$('#t-help').onclick = () => { const h = $('#help3d'); h.style.display = h.style.display === 'block' ? 'none' : 'block'; };
$('#b-undo').onclick = () => undoRedo('undo'); $('#b-redo').onclick = () => undoRedo('redo');
$('#b-save').onclick = save; $('#b-install').onclick = install;
$('#b-play').onclick = () => play();

// Open in game, and Play here (at = {cell, p: [x, y, z, facing]}): the game starts; Continue or load a save there
async function play(at){
  if (!A.state.project) return toast('Start a mod first.', true);
  toast(at ? 'Starting New Vegas: load a save (or Continue) and you\'ll be moved here…' : 'Starting New Vegas…');
  try {
    const d = await post('/api/play', at || {});
    setState(d.state);
    const how = d.via === 'nvse' ? 'New Vegas is starting (with xNVSE)' : 'Steam is starting New Vegas: press Play in its launcher';
    toast(at ? how + '. Continue or load a save: you\'ll arrive here a moment after it loads.' : how + ', with your mod.');
  } catch (e){ fail(e); }
}
function playHere(point){
  if (!A.cellId) return toast('Open a place first.', true);
  const p = point || W.cam.position;
  // facing the way the view looks (the game's heading: 0 is north, turning clockwise)
  const facing = Math.round((Math.PI / 2 - W.yaw) * 10000) / 10000;
  play({cell: A.cellId, p: [p.x, p.y, p.z + 4, facing]});
}
$('#w-new').onclick = () => newMod($('#w-name').value);
$('#w-name').addEventListener('keydown', e => { if (e.key === 'Enter') newMod(e.target.value); });

addEventListener('keydown', e => {
  if (typing(e)) return;
  const k = e.key.toLowerCase(), ctrl = e.ctrlKey || e.metaKey, world = $('#page-world').style.display !== 'none';
  if (ctrl && k === 'z'){ e.preventDefault(); undoRedo('undo'); }
  else if (ctrl && (k === 'y' || (e.shiftKey && k === 'z'))){ e.preventDefault(); undoRedo('redo'); }
  else if (ctrl && k === 's'){ e.preventDefault(); save(); }
  else if (!world) return;
  else if (ctrl && k === 'd'){ e.preventDefault(); dupSel(); }
  else if (ctrl && k === 'c'){ e.preventDefault(); copySel(); }
  else if (ctrl && k === 'v'){ e.preventDefault(); paste(); }
  else if (ctrl && k === 'a'){ e.preventDefault(); select(visibleGroups().map(g => g.userData.thing.key)); }
  else if (e.key === 'Delete'){ delSel(); }
  else if (e.key === 'End'){ dropSel(); }
  else if (e.key === 'Escape'){ if (cmClose() || owClose()) return; if (A.swapping) swapEnd(); else if (W.placing) stopPlacing(); else select([]); }
  else if (ctrl || e.altKey) return;
  else if (k === 'g' || k === '1') setTool('translate');
  else if (k === 'r' || k === '2') setTool('rotate');
  else if (k === 'f') focusSel();
  else if (k === 'h' && e.shiftKey){ showHidden(); toast('Showing everything again'); }
  else if (k === 'h') hideSel();
});

// ---------- tabs and pages ----------
function tab(side, name){
  const root = side === 'left' ? $('#left') : $('#right');
  root.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
  root.querySelectorAll('.pane').forEach(p => p.classList.toggle('on', p.id === 'tab-' + name));
}
$('#left .tabs').onclick = e => { if (e.target.closest('button')) tab('left', e.target.closest('button').dataset.tab); };
$('#right .tabs').onclick = e => { if (e.target.closest('button')) tab('right', e.target.closest('button').dataset.tab); };

const PAGES = ['browse', 'world', 'mod'];
function page(name){
  for (const p of PAGES){
    const nav = $('#nav-' + p), el = $('#page-' + p);
    if (nav) nav.classList.toggle('on', p === name);
    if (el) el.style.display = p === name ? (p === 'mod' ? 'block' : 'flex') : 'none';
  }
  if (name === 'mod') drawModPage();
  if (typeof onPage === 'function') onPage(name);
}
for (const p of PAGES) $('#nav-' + p).onclick = () => page(p);
$('#modpill').onclick = () => page('mod');

function nvseCard(s){
  const n = s.nvse || {}, via = s.launch_via;
  return `<div class="card"><h3>Script extender (xNVSE)</h3>
    <p>${n.installed ? `Installed${n.version ? ' (' + esc(n.version) + (n.by_folab ? ', by FOLab' : '') + ')' : ''}.` : 'Not installed.'}
       Most New Vegas mods need it; FOLab can start the game through it.</p>
    <p>${n.installed ? '' : (n.downloaded || []).length ? `<button class="btn primary" id="m-nvse-install">Install xNVSE ${esc(n.downloaded.slice(-1)[0])}</button> ` : ''}
       <button class="btn" id="m-nvse-get">Download the newest from xNVSE's GitHub</button>
       ${n.by_folab ? '<button class="btn" id="m-nvse-out">Take it out of the game</button>' : ''}</p>
    <p><label><input type="radio" name="via" value="nvse" ${via === 'nvse' ? 'checked' : ''} ${n.loader ? '' : 'disabled'}> Start the game through xNVSE (no launcher window)</label><br>
       <label><input type="radio" name="via" value="steam" ${via !== 'nvse' || !n.loader ? 'checked' : ''}> Start it through Steam (the game's launcher opens: Play)</label></p></div>`;
}

function drawModPage(){
  const s = A.state, p = s.project, i = s.installed || {};
  const others = (s.projects || []).filter(x => !p || x.name !== p.name);
  const mine = A.places.filter(c => c.mine);
  $('#page-mod').innerHTML = `
    <h2>${p ? esc(p.name) : 'No mod open'}</h2>
    ${p ? `<div class="card"><h3>${esc(p.plugin)}</h3>
      <p>${p.changes} change${p.changes === 1 ? '' : 's'} in ${mine.length} place${mine.length === 1 ? '' : 's'}${mine.length ? ': ' + mine.map(c => esc(c.name || c.edid)).join(', ') : ''}.</p>
      <p>${p.built ? 'The saved plugin is up to date.' : 'Changes since the last save: <b>Save</b> writes the plugin.'}
         ${i.installed ? (i.current && p.built ? ' It is in the game and switched on.' : ' The game has an older copy: <b>Put in game</b> updates it.') : ' It is not in the game yet.'}</p>
      <p><button class="btn primary" id="m-save">Save</button> <button class="btn" id="m-install">Put in game</button>
         ${i.installed ? '<button class="btn" id="m-uninstall">Take out of game</button>' : ''}</p></div>
    <div class="card"><h3>Trying it in the game</h3>
      <p>After <b>Put in game</b>, start New Vegas and load a save. Open the console with <code>~</code> and type
         <code>coc ${esc(A.cellEdid || 'CellEditorID')}</code> to go to the place you're working on.</p>
      <p>Changes to a place you've already visited in that save can stay hidden until the place resets. A new save, or one from before you went there, shows them straight away.</p></div>` : ''}
    ${p ? `<div class="card"><h3>Plugin</h3>
      <p>${p.opened ? 'Opened from an existing plugin: saving keeps everything in it and lays your changes over it.' : 'A new mod of your own.'}</p>
      <p>Masters: ${(p.masters || []).map(m => `<code>${esc(m)}</code>`).join(' ') || 'none yet'}</p>
      <p><label><input type="checkbox" id="m-esm" ${p.esm ? 'checked' : ''}> Save as a master (other mods can build on it; the game loads it before plugins)</label></p></div>` : ''}
    ${nvseCard(s)}
    <div class="card"><h3>Open a plugin as your mod</h3>
      <p>Mods in the game's Data folder. FOLab works on a copy; <b>Put in game</b> writes it back over the original (the old one goes to backups first).</p>
      <div id="m-plugins"><div class="note">Looking…</div></div></div>
    <div class="card"><h3>Start another mod</h3>
      <p><input id="m-name" placeholder="Name" style="width:280px"> <button class="btn" id="m-new">Start</button></p>
      ${others.length ? '<p>Or open one:</p>' + others.map(x => `<div class="row" data-open="${esc(x.name)}">${esc(x.name)}<span class="n">${new Date(x.modified * 1000).toLocaleString()}</span></div>`).join('') : ''}</div>
    <div class="card"><h3>Where things are</h3>
      <p>Game: <code>${esc(s.game)}</code></p>
      ${i.plugins_txt ? `<p>Active plugins list: <code>${esc(i.plugins_txt)}</code></p>` : ''}
      <p>FOLab keeps a copy of anything it replaces in its <code>backups</code> folder.</p></div>`;
  const on = (id, f) => { const el = $(id); if (el) el.onclick = f; };
  on('#m-save', save); on('#m-install', install); on('#m-new', () => newMod($('#m-name').value));
  on('#m-uninstall', async () => { try { const d = await post('/api/uninstall'); setState(d.state); toast('Taken out of the game.'); } catch (e){ fail(e); } });
  $('#page-mod').querySelectorAll('[data-open]').forEach(r => r.onclick = () => { openMod(r.dataset.open); page('world'); });
  const on2 = (id, f) => { const el = $(id); if (el) el.onclick = f; };
  on2('#m-nvse-get', async () => {
    try {
      const r = await api('/api/nvse/latest');
      if (!confirm(`Download ${r.asset} (${(r.size / 1048576).toFixed(1)} MB, xNVSE ${r.version}) from github.com/xNVSE/NVSE?`)) return;
      toast('Downloading xNVSE ' + r.version + '…');
      const d = await post('/api/nvse/download'); setState(d.state); toast('Downloaded xNVSE ' + d.version + ': Install puts it in the game.');
    } catch (e){ fail(e); }
  });
  on2('#m-nvse-install', async () => {
    const v = A.state.nvse.downloaded.slice(-1)[0];
    if (!confirm(`Put xNVSE ${v} in the game folder? (Its .dll and .exe files go beside FalloutNV.exe; anything replaced is kept in backups.)`)) return;
    try { const d = await post('/api/nvse/install', {version: v}); setState(d.state); toast('xNVSE ' + v + ' is in the game.'); } catch (e){ fail(e); }
  });
  on2('#m-nvse-out', async () => {
    if (!confirm('Take xNVSE out of the game folder? (A copy goes to backups.)')) return;
    try { const d = await post('/api/nvse/uninstall'); setState(d.state); toast('xNVSE taken out.'); } catch (e){ fail(e); }
  });
  $('#page-mod').querySelectorAll('input[name="via"]').forEach(r => r.onchange = async () => { try { setState(await post('/api/launch_via', {via: r.value})); } catch (e){ fail(e); } });
  const esm = $('#m-esm');
  if (esm) esm.onchange = async () => { try { setState(await post('/api/project/esm', {on: esm.checked})); toast(esm.checked ? 'Will save as a master' : 'Will save as a plugin'); } catch (e){ fail(e); } };
  api('/api/plugins').then(list => {
    const box = $('#m-plugins'); if (!box) return;
    box.innerHTML = list.length ? list.map(x => `<div class="row" data-adopt="${esc(x.file)}"><div>${esc(x.file)}<small>${x.error ? esc(x.error) : `${x.records} records · needs ${x.masters.map(esc).join(', ') || 'nothing'}${x.author ? ' · by ' + esc(x.author) : ''}`}</small></div><span class="n">Open</span></div>`).join('')
      : '<div class="note">No mods in the Data folder yet (only the game\'s own files).</div>';
    box.querySelectorAll('[data-adopt]').forEach(r => r.onclick = async () => {
      toast('Opening ' + r.dataset.adopt + '… (loading it on top of the game takes a few seconds)');
      try { setState(await post('/api/project/adopt', {file: r.dataset.adopt})); await loadPlaces(); BW.types = []; page('world'); toast('Opened ' + r.dataset.adopt + ' as your mod'); }
      catch (e){ fail(e); }
    });
  });
}

// ---------- start ----------
async function start(){
  worldInit($('#view'));
  try { const [g, a] = (localStorage.getItem('folab-snap') || '128,15').split(','); $('#t-grid').value = g; $('#t-angle').value = a; } catch (e) {}
  snapNow();
  try { if (localStorage.getItem('folab-light') === '0'){ $('#t-light').checked = false; setGameLight(false); } } catch (e) {}
  await refreshState();
  for (const [k, v] of Object.entries(A.state.kinds)) $('#f-kind').insertAdjacentHTML('beforeend', `<option value="${k}">${esc(v)}</option>`);
  drawRecent();
  const recent = A.state.projects || [];
  $('#w-recent').innerHTML = recent.length ? '<p>Or open one:</p>' + recent.map(x => `<div class="row" data-open="${esc(x.name)}">${esc(x.name)}</div>`).join('') : '';
  $('#w-recent').onclick = e => { const r = e.target.closest('[data-open]'); if (r) openMod(r.dataset.open); };
  await loadPlaces();
  let want = new URLSearchParams(location.search).get('cell');
  try { want = want || localStorage.getItem('folab-cell'); } catch (e) {}
  const first = A.places.find(c => c.id === want || c.edid.toLowerCase() === (want || '').toLowerCase()) || A.places.find(c => c.edid === '2EOVault21');
  if (first) openPlace(first.id);
}
start();
