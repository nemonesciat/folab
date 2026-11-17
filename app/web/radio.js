// ---------- Radio: stations of the mod's own, from the user's audio files (radio.py) ----------
// A station is a name and a list of songs. The page adds itself (nav button, main) like Library does; everything it
// shows is read back from the mod's records, so Undo anywhere else is seen here the next time the list is drawn.
const RAD = {list: null, key: null, making: false, busy: false, where: {everywhere: true, range: 20000, static: 10}};
const RAD_BATCH = 40 * 1048576;          // what one request carries (a song and its _mono copy always travel together)

(function radSetup(){
  const css = document.createElement('style');
  css.textContent = `
  #page-radio{flex:1;min-height:0}
  #rad-side{width:280px;border-right:1px solid var(--line)}
  #rad-main{flex:1;overflow-y:auto;padding:16px 24px 60px;min-width:0}
  #rad-main h2{margin:0 0 4px;font-weight:500;color:var(--gold2);font-size:19px}
  .rad-card{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:12px 14px;margin:12px 0;max-width:860px}
  .rad-card h4{margin:0 0 8px;font-size:13px;color:var(--gold2);font-weight:500}
  .rad-grid{display:grid;grid-template-columns:150px 1fr;gap:8px 12px;align-items:center}
  .rad-grid>label{color:var(--muted);font-size:12.5px}
  .rad-grid input[type=text]{width:300px}.rad-grid input[type=number]{width:100px}
  .rad-opt{display:flex;gap:8px;align-items:baseline;margin:3px 0;cursor:pointer}.rad-opt small{color:var(--faint)}
  .rad-spot{margin:6px 0 2px 24px;color:var(--muted);font-size:12.5px;line-height:1.9}
  .rad-tracks{width:100%;border-collapse:collapse;font-size:13px}
  .rad-tracks td{padding:5px 8px;border-top:1px solid var(--line);vertical-align:middle}.rad-tracks tr:first-child td{border-top:0}
  .rad-tracks .n{color:var(--faint);width:28px;text-align:right}.rad-tracks .t small{display:block;color:var(--faint);font-size:11.5px}
  .rad-tracks audio{height:28px;width:210px;vertical-align:middle}
  .rad-tag{font-size:11.5px;border:1px solid var(--line2);border-radius:10px;padding:1px 8px;white-space:nowrap;color:var(--muted)}
  .rad-tag.warn{color:var(--amber);border-color:var(--amber)}.rad-tag.bad{color:var(--red);border-color:var(--red)}
  .rad-picked{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.6}
  .rad-small{color:var(--faint);font-size:12px;line-height:1.55;max-width:820px}
  .rad-left{color:#f3b2a5;font-size:12.5px;margin:6px 0;line-height:1.5}
  .rad-empty{padding:30px 0;color:var(--muted);max-width:640px;line-height:1.6}
  #rad-main.rad-over{outline:2px dashed var(--gold);outline-offset:-8px}`;
  document.head.appendChild(css);
  const main = document.createElement('main');
  main.id = 'page-radio'; main.style.display = 'none';
  main.innerHTML = `<div class="side" id="rad-side"><div style="padding:10px 12px 4px"><button class="btn primary" id="rad-new" style="width:100%">＋ New station</button></div>
      <div class="h">Your stations</div><div class="list" id="rad-rows"></div></div>
    <div id="rad-main"></div><input type="file" id="rad-files" multiple accept=".mp3,.wav,.ogg" style="display:none">`;
  $('#page-create').after(main);
  const nav = document.createElement('button');
  nav.id = 'nav-radio'; nav.title = 'Radio stations of your own, from your own music files';
  nav.innerHTML = '<svg viewBox="0 0 24 24"><rect x="3" y="9" width="18" height="11" rx="2"/><path d="M7 9l9-5"/><circle cx="8.500" cy="14.500" r="2.500"/><path d="M14 13h4M14 16h4"/></svg>Radio';
  ($('#nav-quests') || $('#nav-world')).after(nav);
  PAGES.push('radio');
  nav.onclick = () => { page('radio'); radLoad(); };
  $('#rad-new').onclick = () => { RAD.making = true; RAD.key = null; RAD.picked = []; radDraw(); };
  $('#rad-rows').onclick = e => { const r = e.target.closest('[data-k]'); if (r){ RAD.key = r.dataset.k; RAD.making = false; RAD.left = null; radDraw(); } };
  $('#rad-files').onchange = e => { const fs = [...e.target.files]; e.target.value = ''; radPicked(fs); };
  const m = $('#rad-main');
  m.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('Files')){ e.preventDefault(); m.classList.add('rad-over'); } });
  m.addEventListener('dragleave', e => { if (!m.contains(e.relatedTarget)) m.classList.remove('rad-over'); });
  m.addEventListener('drop', e => { e.preventDefault(); m.classList.remove('rad-over'); radPicked([...e.dataTransfer.files]); });
  m.addEventListener('click', radClick);
  m.addEventListener('change', radChange);
})();

// (Undo and Redo may have changed the stations)
(function(){
  if (typeof undoRedo !== 'function') return;
  const prev = undoRedo;
  undoRedo = async function (which){ await prev(which); if ($('#page-radio').style.display !== 'none') radLoad(); };
})();

function radTime(s){ if (s == null) return ''; s = Math.round(s); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
function radSize(n){ return n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'; }
function radStation(){ return RAD.list && RAD.list.stations.find(s => s.key === RAD.key); }

async function radLoad(){
  if (!A.state || !A.state.project){ RAD.list = {stations: [], unused: []}; return radDraw(); }
  try { radTake(await api('/api/radio/list')); } catch (e){ fail(e); }
}
function radTake(d){
  RAD.list = d;
  if (RAD.key && !radStation()) RAD.key = null;
  if (!RAD.key && !RAD.making && d.stations.length) RAD.key = d.stations[0].key;
  radDraw();
}

// ---------- drawing ----------
function radDraw(){
  const L = RAD.list || {stations: [], unused: []};
  $('#rad-rows').innerHTML = L.stations.map(s => `<div class="row${s.key === RAD.key ? ' on' : ''}" data-k="${esc(s.key)}"><div>${esc(s.name)}<small>${s.tracks.length} song${s.tracks.length === 1 ? '' : 's'} · ${s.where ? (s.where.everywhere ? 'everywhere' : 'around a spot') : 'heard nowhere'}</small></div></div>`).join('')
    || '<div class="note">None yet.</div>';
  const m = $('#rad-main');
  if (!A.state || !A.state.project){ m.innerHTML = '<div class="rad-empty"><h2>Radio</h2>Open or start a mod first: a station is kept in your mod, and its songs go in the game with it.</div>'; return; }
  const st = radStation();
  if (RAD.making || !st) return radDrawNew(m, L);
  radDrawStation(m, st, L);
}

function radWhereHtml(w, id){
  const here = radHere();
  return `<label class="rad-opt"><input type="radio" name="${id}" value="all" ${w.everywhere ? 'checked' : ''}> Heard everywhere <small>like Radio New Vegas</small></label>
    <label class="rad-opt"><input type="radio" name="${id}" value="spot" ${w.everywhere ? '' : 'checked'}> Around a spot, as far as its range <small>like Black Mountain Radio</small></label>
    <div class="rad-spot" style="display:${w.everywhere ? 'none' : 'block'}">
      The spot: ${w.place && !w.everywhere && !RAD.moveSpot ? `<b>${esc(w.place)}</b> (${w.p.slice(0, 3).map(v => Math.round(v)).join(', ')}) <button class="btn sm" data-act="spot-here">Move it to where the 3D view is</button>`
        : here ? `where the 3D view is now, <b>${esc(here.label)}</b>` : '<span style="color:var(--amber)">open a place in World and look at the spot first</span>'}<br>
      Range <input type="number" id="${id}-range" min="500" step="500" value="${Math.round(w.range || 20000)}"> units <small>(an outdoor cell is 4,096 across; Black Mountain Radio reaches 50,000)</small><br>
      Static over the outer <input type="number" id="${id}-static" min="0" max="100" step="5" value="${Math.round(w.static || 0)}" style="width:70px"> % of it</div>`;
}
function radHere(){
  if (typeof W === 'undefined' || !W.cam) return null;
  const c = W.cam.position, p = [c.x, c.y, c.z].map(v => Math.round(v * 10) / 10);
  if (A.outside) return {world: typeof OUT !== 'undefined' ? OUT.world : null, cell: null, p, label: `${A.outside.name || A.outside.edid || 'outdoors'}, cell ${Math.floor(c.x / 4096)}, ${Math.floor(c.y / 4096)}`};
  if (A.cellId) return {cell: A.cellId, p, label: ($('#s-place') && $('#s-place').textContent) || A.cellEdid || A.cellId};
  return null;
}
function radReadWhere(id, old){
  const all = document.querySelector(`input[name="${id}"][value="all"]`).checked;
  if (all) return {everywhere: true};
  const w = {everywhere: false, range: parseFloat($('#' + id + '-range').value) || 0, static: parseFloat($('#' + id + '-static').value) || 0};
  if (old && old.cell && !old.everywhere && !RAD.moveSpot) return Object.assign(w, {cell: old.cell, p: old.p});
  const here = radHere();
  if (!here){ toast('Open a place in World and look at the spot first.', true); return null; }
  return Object.assign(w, {cell: here.cell, world: here.world, p: here.p});
}

function radFormats(L){
  return `<div class="rad-small">${esc(L.formats || '')}<br>${esc(L.mono || '')}</div>`;
}
function radPickedHtml(){
  const fs = RAD.picked || [];
  if (!fs.length) return '<div class="rad-picked">No songs picked yet. You can also drop files anywhere here.</div>';
  const total = fs.reduce((s, f) => s + f.size, 0);
  return `<div class="rad-picked">${fs.length} file${fs.length === 1 ? '' : 's'}, ${radSize(total)}: ${fs.slice(0, 12).map(f => esc(f.name)).join(', ')}${fs.length > 12 ? '…' : ''} <button class="btn sm" data-act="unpick">Clear</button></div>`;
}
function radLeft(){
  return RAD.left && RAD.left.length ? `<div class="rad-card" style="border-color:var(--red)"><h4>Left out</h4>${RAD.left.map(x => `<div class="rad-left">${esc(x)}</div>`).join('')}</div>` : '';
}

function radDrawNew(m, L){
  m.innerHTML = `<h2>New radio station</h2>
    <div class="rad-small">A name and your own music files: FOLab makes everything the game needs, the way its own Mojave Music Radio is made, and puts the songs in with your mod. It plays them at random and never one of the last three again.</div>
    ${radLeft()}
    <div class="rad-card"><div class="rad-grid">
      <label>Name on the Pip-Boy</label><div><input type="text" id="rad-name" maxlength="60" placeholder="Radio Waikiki" value="${esc(RAD.newName || '')}"></div>
      <label>Songs</label><div><button class="btn" data-act="pick">Pick music files…</button> <span class="rad-small">.mp3 or .wav</span>${radPickedHtml()}</div>
      <label>Where it's heard</label><div>${radWhereHtml(RAD.where, 'rad-w')}</div>
    </div>
    <div style="margin-top:12px"><button class="btn primary" data-act="make" ${RAD.busy ? 'disabled' : ''}>${RAD.busy ? esc(RAD.busy) : 'Make the station'}</button></div></div>
    ${radFormats(L)}`;
}

function radTrackRow(t){
  const i = t.info || {};
  const tag = i.missing ? '<span class="rad-tag bad" title="Its file is gone from your mod\'s files: take the song off, or add it again">file missing</span>'
    : i.mono ? '<span class="rad-tag" title="It has the one-channel copy that radios standing in the world play">Pip-Boy and radios</span>'
    : '<span class="rad-tag warn" title="No one-channel copy: add the song again together with a file named like it with _mono on the end">Pip-Boy only</span>';
  const about = i.missing ? '' : [radTime(i.seconds), (i.kind || '').toUpperCase(), i.rate ? (i.rate / 1000) + ' kHz' : '', i.channels === 1 ? 'mono' : i.channels === 2 ? 'stereo' : '', radSize(i.size || 0)].filter(Boolean).join(' · ')
    + ((i.notes || []).length ? ` · <span style="color:var(--amber)">${esc(i.notes.join('; '))}</span>` : '');
  return `<tr><td class="n">${t.n}</td><td class="t">${esc(t.title)}<small>${about}</small></td><td>${tag}</td>
    <td>${i.missing ? '' : `<audio controls preload="none" src="/api/radio/file?path=${encodeURIComponent(t.file)}"></audio>`}</td>
    <td style="text-align:right"><button class="btn sm" data-act="untrack" data-t="${esc(t.key)}" title="Take this song off the station">✕</button></td></tr>`;
}

function radDrawStation(m, st, L){
  const w = st.where || {everywhere: true};
  m.innerHTML = `<h2>${esc(st.name)}</h2><div class="rad-small">${esc(st.edid)} · songs in ${esc(st.folder)}</div>
    ${radLeft()}
    <div class="rad-card"><h4>Songs (${st.tracks.length})</h4>
      ${st.tracks.length ? `<table class="rad-tracks">${st.tracks.map(radTrackRow).join('')}</table>` : '<div class="note" style="padding-left:0">No songs: the station will be silent.</div>'}
      <div style="margin-top:10px"><button class="btn primary" data-act="add" ${RAD.busy ? 'disabled' : ''}>${RAD.busy ? esc(RAD.busy) : '＋ Add songs…'}</button>
        <span class="rad-small">${st.tracks.length < 4 ? 'With fewer than four songs it repeats sooner: it only bars as many of the last-played as leaves something to play.' : ''}</span></div></div>
    <div class="rad-card"><h4>Name on the Pip-Boy</h4><input type="text" id="rad-rename" maxlength="60" value="${esc(st.name)}" style="width:300px"> <button class="btn" data-act="rename">Rename</button></div>
    <div class="rad-card"><h4>Where it's heard</h4>${radWhereHtml(w, 'rad-e')}<div style="margin-top:8px"><button class="btn" data-act="where">Change</button></div></div>
    ${L.unused && L.unused.length ? `<div class="rad-card"><h4>Files no station plays</h4><div class="rad-small">${L.unused.length} song file${L.unused.length === 1 ? '' : 's'} left from songs you took off. They still go in the game with your mod, and Undo can still bring their songs back.</div>
      <div style="margin-top:8px"><button class="btn" data-act="tidy">Clear them out</button></div></div>` : ''}
    <div class="rad-card"><h4>Remove</h4><button class="btn" data-act="remove">Remove this station</button> <span class="rad-small">Undo brings it back.</span></div>
    ${radFormats(L)}`;
}

// ---------- doing ----------
function radChange(e){
  const r = e.target.closest('input[type=radio]');
  if (r){ const spot = r.closest('div').querySelector('.rad-spot') || r.parentElement.parentElement.querySelector('.rad-spot'); if (spot) spot.style.display = r.value === 'spot' && r.checked ? 'block' : 'none'; if (r.name === 'rad-w') RAD.where.everywhere = r.value === 'all'; }
  if (e.target.id === 'rad-name') RAD.newName = e.target.value;
  if (e.target.id === 'rad-w-range') RAD.where.range = parseFloat(e.target.value) || 0;
  if (e.target.id === 'rad-w-static') RAD.where.static = parseFloat(e.target.value) || 0;
}

function radPicked(files){
  files = files.filter(f => f.size);
  if (!files.length) return;
  if (!A.state.project) return toast('Open or start a mod first.', true);
  if (RAD.making || !radStation()){
    if ($('#rad-name')) RAD.newName = $('#rad-name').value;
    RAD.making = true; RAD.picked = (RAD.picked || []).concat(files); radDraw();
  } else radSend('/api/radio/add', {station: RAD.key}, files);
}

async function radEncode(files){
  const out = [];
  for (const f of files){
    const bytes = new Uint8Array(await f.arrayBuffer());
    let s = '';
    for (let i = 0; i < bytes.length; i += 32768) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
    out.push({name: f.name, data: btoa(s)});
  }
  return out;
}
// songs in batches a request can carry, each song with its _mono copy
function radBatches(files){
  const stem = n => n.replace(/\.[^.]*$/, '').replace(/_mono$/i, '').toLowerCase();
  const groups = new Map();
  for (const f of files){ const k = stem(f.name); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(f); }
  const out = [[]]; let size = 0;
  for (const g of groups.values()){
    const n = g.reduce((s, f) => s + f.size, 0);
    if (size && size + n > RAD_BATCH){ out.push([]); size = 0; }
    out[out.length - 1].push(...g); size += n;
  }
  return out;
}
// make a station or add to one; a new station's later batches are added to it
async function radSend(path, body, files){
  if (RAD.busy) return;
  const batches = radBatches(files), left = [];
  let done = 0, d = null;
  try {
    for (const b of batches){
      RAD.busy = `Bringing in songs… ${done} of ${files.length}`; radDraw();
      d = await post(path, Object.assign({}, body, {files: await radEncode(b)}));
      if (d.problem){ left.push(d.problem); if (path === '/api/radio/new') break; }
      else {
        left.push(...(d.left_out || []));
        if (path === '/api/radio/new'){ path = '/api/radio/add'; body = {station: d.station}; RAD.key = d.station; RAD.making = false; RAD.picked = []; RAD.newName = ''; }
      }
      done += b.length;
      if (d.state) setState(d.state);
    }
  } catch (e){ fail(e); }
  RAD.busy = false; RAD.left = left;
  if (d && d.stations) radTake(d); else radLoad();
  if (!left.length && d && !d.problem) toast('Done: the songs go in the game with your mod.');
}

async function radDo(path, body, said){
  try {
    const d = await post(path, body);
    if (d.problem) return toast(d.problem, true);
    if (d.state) setState(d.state);
    RAD.left = null; RAD.moveSpot = false;
    radTake(d);
    if (said) toast(said);
  } catch (e){ fail(e); }
}

function radClick(e){
  const b = e.target.closest('[data-act]'); if (!b) return;
  const act = b.dataset.act, st = radStation();
  if (act === 'pick' || act === 'add') return $('#rad-files').click();
  if (act === 'unpick'){ RAD.picked = []; return radDraw(); }
  if (act === 'spot-here'){ RAD.moveSpot = true; return radDraw(); }
  if (act === 'make'){
    const name = $('#rad-name').value.trim();
    if (!name) return toast('Give the station a name: it\'s what the Pip-Boy lists.', true);
    if (!(RAD.picked || []).length) return toast('Pick its songs first.', true);
    const where = radReadWhere('rad-w'); if (!where) return;
    return radSend('/api/radio/new', {name, where}, RAD.picked);
  }
  if (!st) return;
  if (act === 'untrack') return radDo('/api/radio/remove_track', {station: st.key, track: b.dataset.t}, 'Taken off. Undo brings it back.');
  if (act === 'rename') return radDo('/api/radio/rename', {station: st.key, name: $('#rad-rename').value}, 'Renamed.');
  if (act === 'where'){ const where = radReadWhere('rad-e', st.where); if (where) radDo('/api/radio/where', {station: st.key, where}, 'Changed where it\'s heard.'); return; }
  if (act === 'tidy') return radDo('/api/radio/tidy', {}, 'Cleared.');
  if (act === 'remove'){ if (confirm(`Remove ${st.name}? Its songs' files stay until you clear them out; Undo brings the station back.`)) radDo('/api/radio/remove', {station: st.key}, 'Removed.'); }
}
