// ---------- Browse: the game's records by kind, and an editor for one (the Workshop's Browse page) ----------
// Categories on the left, the records of one kind in the middle (search by editor ID or name), the record on the right:
// every part the layouts read as fields, links underlined (click to go to that record), the parts FOLab doesn't read
// yet kept exactly as they are. Save keeps the record in your mod (one Undo step); Make a copy starts a record of your
// own from it; Place it hands it to the World page.
const BW = {types: [], type: null, rows: [], key: null, data: null, dirty: false, back: []};

async function browseInit(){
  if (BW.types.length) return;
  BW.types = await api('/api/types');
  drawBrowseTypes();
  bwType(localStorageGet('folab-bw-type') || 'WEAP');
}
function localStorageGet(k){ try { return localStorage.getItem(k); } catch (e){ return null; } }

function drawBrowseTypes(){
  $('#bw-types').innerHTML = BW.types.map(t => `<div class="row${t.type === BW.type ? ' on' : ''}" data-t="${t.type}"><div>${esc(t.label)}<small>${t.type}${t.editable ? '' : ' · read only'}</small></div><span class="n">${t.count}</span></div>`).join('');
}
$('#bw-types').addEventListener('click', e => { const r = e.target.closest('.row'); if (r) bwType(r.dataset.t); });

async function bwType(t){
  BW.type = t;
  try { localStorage.setItem('folab-bw-type', t); } catch (e) {}
  drawBrowseTypes();
  await bwList();
}
let bwTimer;
$('#bw-find').addEventListener('input', () => { clearTimeout(bwTimer); bwTimer = setTimeout(bwList, 200); });
async function bwList(){
  if (!BW.type) return;
  const token = BW.listToken = (BW.listToken || 0) + 1;      // (only the newest search's answer is shown)
  const rows = await api(`/api/records?type=${BW.type}&q=${encodeURIComponent($('#bw-find').value)}`);
  if (token !== BW.listToken) return;
  BW.rows = rows;
  const label = (BW.types.find(x => x.type === BW.type) || {}).label || BW.type;
  $('#bw-head').textContent = `${label} · ${BW.rows.length}${BW.rows.length >= 1500 ? '+' : ''}`;
  $('#bw-rows').innerHTML = BW.rows.map(r => `<div class="row${r.key === BW.key ? ' on' : ''}" data-k="${esc(r.key)}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}" title="${r.state === 'new' ? 'your own' : 'changed by your mod'}"></span>` : ''}${esc(r.edid || r.key)}<small>${esc(r.name)}</small></div></div>`).join('');
}
$('#bw-rows').addEventListener('click', e => { const r = e.target.closest('.row'); if (r) bwOpen(r.dataset.k); });

// ---------- one record ----------
async function bwOpen(key, noHistory){
  if (BW.dirty && !confirm('Leave this record without saving your changes?')) return;
  if (BW.key && !noHistory && BW.key !== key) BW.back.push(BW.key);
  const d = await api('/api/record?key=' + encodeURIComponent(key));
  BW.key = key; BW.data = d; BW.dirty = false;
  if (d.record.type !== BW.type){ BW.type = d.record.type; drawBrowseTypes(); bwList(); }
  document.querySelectorAll('#bw-rows .row').forEach(r => r.classList.toggle('on', r.dataset.k === key));
  bwDraw();
}

function bwField(si, fi, f){
  const id = `${si}.${fi}`;
  if (f.code === 'F') return `<label>${esc(f.name)}</label>${bwLink(id, f.value)}`;
  return `<label>${esc(f.name)}</label><input data-f="${id}" value="${f.code === 'f' ? +(+f.value).toPrecision(7) : f.value}">`;
}
function bwLink(id, key){
  const lab = key ? (BW.data.links[key] || key) : '';
  return `<span class="bwlink">${key ? `<a href="#" data-go="${esc(key)}" title="${esc(key)}">${esc(lab)}</a>` : '<i>none</i>'}
    <input data-l="${id}" placeholder="Editor ID…" value="" title="Type an editor ID to link something else (blank keeps it)"></span>`;
}

function bwDraw(){
  const d = BW.data, rec = d.record, ed = d.editable && rec.type !== 'SCPT';   // (a script is edited on its own page)
  const raw = rec.subs.filter(s => s.kind === 'raw').length;
  const state = {'': 'From ' + d.from, changed: 'Changed by your mod (from ' + d.from + ')', new: 'Your own record'}[d.state];
  const edid = (rec.subs.find(s => s.tag === 'EDID') || {}).value || d.key, name = (rec.subs.find(s => s.tag === 'FULL') || {}).value || '';
  const placeable = d.model && A.state.kinds[rec.type];
  let html = `<div class="bwtitle"><b>${esc(edid)}</b>${name ? ' — ' + esc(name) : ''}<small>${rec.type} · ${esc(d.key)} · ${esc(state)}</small></div>
    <div class="acts">
      ${ed ? '<button class="btn primary" data-a="save" disabled>Save</button>' : ''}
      ${ed ? '<button class="btn" data-a="copy" title="Start a record of your own from this one">Make a copy</button>' : ''}
      ${d.state === 'changed' ? '<button class="btn" data-a="revert">Put back as the game has it</button>' : ''}
      ${d.state === 'new' && rec.type !== 'SCPT' ? '<button class="btn" data-a="revert">Delete this record</button>' : ''}
      ${placeable ? '<button class="btn" data-a="place">Place it</button>' : ''}
      ${rec.type === 'SCPT' ? '<button class="btn primary" data-a="script">Open in Scripts</button>' : ''}
      <button class="btn" data-a="used">Where it's used</button>
      ${BW.back.length ? '<button class="btn" data-a="back">← Back</button>' : ''}
    </div>
    ${!ed ? '<div class="note">Read only for now.</div>' : ''}
    ${d.raw_note ? '<div class="note">This record comes from a DLC and has parts FOLab doesn\'t read yet: they\'re kept as they are, but links inside them are not re-checked.</div>' : ''}
    <div id="bw-used"></div>`;
  rec.subs.forEach((s, si) => {
    if (s.kind === 'raw') return;
    if (s.kind === 'z') html += `<div class="bwsub"><label>${esc(s.label)}</label><input data-z="${si}" value="${esc(s.value)}" class="wide"></div>`;
    else if (s.kind === 'F') html += `<div class="bwsub">${bwField(si, 'v', {name: s.label, code: 'F', value: s.value})}</div>`;
    else if (s.kind === 'F*') html += `<div class="bwsub"><label>${esc(s.label)}</label><span>${s.value.map(k => k ? `<a href="#" data-go="${esc(k)}">${esc(d.links[k] || k)}</a>` : '').join(', ')}</span></div>`;
    else html += `<div class="bwgrp"><div class="h">${esc(s.label)}</div><div class="bwgrid">${s.fields.map((f, fi) => f.pad !== undefined ? '' : bwField(si, fi, f)).join('')}</div></div>`;
  });
  if (raw) html += `<div class="note">${raw} part${raw === 1 ? '' : 's'} FOLab doesn't read yet (${[...new Set(rec.subs.filter(s => s.kind === 'raw').map(s => s.tag))].join(' ')}): kept exactly as they are.</div>`;
  const box = $('#bw-detail');
  box.innerHTML = html;
  if (!ed) box.querySelectorAll('input').forEach(i => i.disabled = true);
}

$('#bw-detail').addEventListener('input', () => { BW.dirty = true; const b = $('#bw-detail [data-a="save"]'); if (b) b.disabled = false; });
$('#bw-detail').addEventListener('click', async e => {
  const go = e.target.closest('[data-go]');
  if (go){ e.preventDefault(); return bwOpen(go.dataset.go); }
  const a = e.target.dataset.a; if (!a) return;
  if (a === 'save') return bwSave();
  if (a === 'script') return scrOpen(BW.key);
  if (a === 'back'){ BW.dirty = false; return bwOpen(BW.back.pop(), true); }
  if (a === 'copy'){ try { const r = await post('/api/record/copy', {key: BW.key}); setState(r.state); await bwList(); BW.dirty = false; bwOpen(r.made[0]); toast('Made a copy: your own record'); } catch (err){ fail(err); } return; }
  if (a === 'revert'){
    if (!confirm(BW.data.state === 'new' ? 'Delete this record of yours?' : 'Put this record back as the game has it?')) return;
    try { const r = await post('/api/record/revert', {key: BW.key}); setState(r.state); BW.dirty = false; await bwList(); if (BW.data.state === 'new') { BW.key = null; $('#bw-detail').innerHTML = ''; } else bwOpen(BW.key, true); } catch (err){ fail(err); }
    return;
  }
  if (a === 'place'){
    const rec = BW.data.record, f = t => (rec.subs.find(s => s.tag === t) || {}).value || '';
    const it = {key: BW.key, type: rec.type, edid: f('EDID'), name: f('FULL'), model: 'meshes\\' + f('MODL')};
    page('world');
    if (!A.cellId) return toast('Open a place first, then Place it again.', true);
    remember(it); found = [it].concat(found);
    startPlacing(it);
    const h = $('#hint'); h.textContent = `Click where ${it.edid} goes · Esc or right-click stops`; h.style.display = 'block';
    return;
  }
  if (a === 'used'){
    const u = await api('/api/used?key=' + encodeURIComponent(BW.key));
    const box = $('#bw-used');
    if (u.busy){ box.innerHTML = '<div class="note">Still reading the game to answer that: try again in a moment.</div>'; return; }
    box.innerHTML = `<div class="h">Where it's used · ${u.total}</div>` + (u.rows.length ? u.rows.map(r => `<div class="row" data-${r.kind === 'placed' ? 'place' : 'go'}="${esc(r.key)}"><div>${esc(r.label)}<small>${r.kind === 'placed' ? 'placed here' : 'named by this record'}</small></div></div>`).join('') : '<div class="note">Nowhere FOLab can see.</div>');
    box.querySelectorAll('[data-place]').forEach(r => r.onclick = () => { page('world'); openPlace(r.dataset.place).then(() => { const g = [...W.byKey.values()].find(g => g.userData.thing.bkey === BW.key); if (g){ select([g.userData.thing.key]); focusSel(); } }); });
  }
});

async function bwSave(){
  const rec = JSON.parse(JSON.stringify(BW.data.record)), box = $('#bw-detail');
  for (const i of box.querySelectorAll('input[data-z]')) rec.subs[+i.dataset.z].value = i.value;
  for (const i of box.querySelectorAll('input[data-f]')){
    const [si, fi] = i.dataset.f.split('.'), f = rec.subs[+si].fields[+fi], v = i.value.trim();
    const num = f.code === 'f' ? parseFloat(v) : parseInt(v, 10);
    if (isNaN(num)) return toast(`${f.name}: "${v}" isn't a number`, true);
    f.value = num;
  }
  for (const i of box.querySelectorAll('input[data-l]')){
    const v = i.value.trim(); if (!v) continue;
    const r = await api('/api/resolve?q=' + encodeURIComponent(v));
    if (r.busy) return toast('FOLab is still reading the game\'s editor IDs: try again in a moment.', true);
    const hit = r.hits.find(h => h.label.toLowerCase().startsWith(v.toLowerCase() + ' ') || h.label.toLowerCase() === v.toLowerCase() || h.label.split(' ')[0].toLowerCase() === v.toLowerCase());
    if (!hit) return toast(`No form with the editor ID "${v}"`, true);
    const [si, fi] = i.dataset.l.split('.');
    if (fi === 'v') rec.subs[+si].value = hit.key; else rec.subs[+si].fields[+fi].value = hit.key;
  }
  try {
    const d = await post('/api/record/save', {key: BW.key, record: rec});
    setState(d.state); BW.dirty = false;
    if (typeof recCacheDrop === 'function') recCacheDrop(BW.key);
    toast('Saved in your mod');
    await bwList(); bwOpen(BW.key, true);
  } catch (e){ fail(e); }
}

function onPage(name){ if (name === 'browse') browseInit(); }
