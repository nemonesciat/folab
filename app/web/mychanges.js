// ---------- My changes: every change the mod makes, by place and kind ----------
// Go there, put one back (an undo step like any other), see the difference from the game.
const CH = {d: null, find: '', plug: null, open: new Set(), diffs: {}};
const CH_WORD = {new: 'new', moved: 'moved', turned: 'turned', resized: 'resized', swapped: 'swapped', removed: 'removed', door: 'door link', changed: 'changed',
                 ground: 'ground', water: 'water', navmesh: 'navmesh', 'left out': 'left out'};

async function chDraw(){
  if (!A.state.project){ $('#tl-body').innerHTML = '<h2>My changes</h2>' + tlBox('Start a mod first.'); return; }
  $('#tl-body').innerHTML = '<h2>My changes</h2>' + tlBox('Listing them…');
  try { CH.d = await api('/api/tools/changes'); CH.plug = CH.d.opened ? await api('/api/tools/changes/plugin') : null; }
  catch (e){ $('#tl-body').innerHTML = '<h2>My changes</h2>' + tlBox(e.message); return; }
  chRender();
}

function chMatch(r){
  const f = CH.find.toLowerCase();
  return !f || (r.name + ' ' + (r.edid || '') + ' ' + r.kinds.join(' ') + ' ' + r.key).toLowerCase().includes(f);
}

function chRowHtml(r, id){
  const open = CH.diffs[id];
  const inline = r.diff && r.diff.length;
  return `<div class="tl-row"><div class="t">${esc(r.name)} ${r.kinds.map(k => `<span class="tl-sev ${k === 'removed' ? 'warn' : k === 'new' ? 'ok' : ''}">${esc(CH_WORD[k] || k)}</span>`).join(' ')}
      ${r.edid && r.edid !== r.name ? `<small>${esc(r.edid)}</small>` : ''}</div>
    ${r.can_diff ? `<button class="btn" data-diff="${esc(r.key)}" data-id="${esc(id)}">Difference</button>` : ''}
    ${r.go ? `<button class="btn" data-go="${esc(id)}">Go there</button>` : ''}
    <button class="btn" data-undo="${esc(id)}" title="${r.kinds.includes('new') ? 'Take it out of your mod' : 'Back as the game has it'}">${r.kinds.includes('new') ? 'Take out' : 'Put back'}</button></div>
    ${inline ? `<pre class="tl-diff">${r.diff.map(chDiffLine).join('\n')}</pre>` : ''}
    ${open ? `<pre class="tl-diff">${open.length ? open.map(chDiffLine).join('\n') : 'No difference: this says what the game says.'}</pre>` : ''}`;
}

function chRender(){
  if (TL.tab !== 'changes') return;
  const d = CH.d;
  CH.rows = {};
  const group = (title, sub, rows, count, gid, extra) => {
    const show = rows.filter(chMatch);
    if (!show.length) return '';
    show.forEach((r, i) => { CH.rows[gid + '/' + i] = r; });
    const open = CH.find || CH.open.has(gid) || count <= 12;
    return `<details class="tl-group" data-gid="${esc(gid)}" ${open ? 'open' : ''}><summary><span class="tl-sev">${count}</span><b>${esc(title)}</b>
        <span class="note" style="padding:0">${esc(sub)}</span><span class="sp"></span>${extra || ''}
        <button class="btn" data-undoall="${esc(gid)}">Put all back</button></summary>
      ${show.map((r, i) => chRowHtml(r, gid + '/' + i)).join('')}
      ${count > rows.length ? `<div class="tl-more">…and ${count - rows.length} more.</div>` : ''}</details>`;
  };
  const places = d.places.map((p, n) => group(p.title, Object.entries(p.tally).map(([k, v]) => `${v} ${CH_WORD[k] || k}`).join(' · '), p.rows, p.count, 'p' + n,
    `<button class="btn" data-goplace="${n}">Go there</button>`)).join('');
  const recs = d.records.map((g, n) => group(g.title, '', g.rows, g.count, 'r' + n)).join('');
  const dropped = d.dropped.length ? group('Left out of the plugin', 'copies the plugin had that said just what the game says', d.dropped, d.dropped.length, 'd') : '';
  $('#tl-body').innerHTML = `<h2>My changes</h2>
    <p class="note" style="padding:0">Every change ${esc(d.plugin)} makes. Putting one back is an undo step like any other.</p>
    <div class="tl-bar"><input type="text" id="ch-find" placeholder="Find: a name, moved, removed…" value="${esc(CH.find)}"><span class="note">${d.total} change${d.total === 1 ? '' : 's'}</span></div>
    ${places ? '<div class="h" style="padding-left:0">By place</div>' + places : ''}
    ${recs ? '<div class="h" style="padding-left:0">By kind</div>' + recs : ''}
    ${dropped}
    ${!places && !recs && !dropped ? tlBox(d.opened ? 'No changes to it yet.' : 'No changes yet.') : ''}
    ${CH.plug && CH.plug.kinds.length ? chPluginHtml() : ''}`;
  const f = $('#ch-find');
  f.oninput = () => { const at = f.selectionStart; CH.find = f.value; chRender(); const g = $('#ch-find'); g.focus(); g.setSelectionRange(at, at); };
  const body = $('#tl-body');
  body.querySelectorAll('details[data-gid]').forEach(el => el.addEventListener('toggle', () => { el.open ? CH.open.add(el.dataset.gid) : CH.open.delete(el.dataset.gid); }));
  body.onclick = chClick;
}

async function chClick(e){
  const t = s => e.target.closest(s);
  let b;
  if ((b = t('[data-go]'))) return toolGo(CH.rows[b.dataset.go].go);
  if ((b = t('[data-goplace]'))){ e.preventDefault(); return toolGo(CH.d.places[+b.dataset.goplace].go); }
  if ((b = t('[data-undo]'))) return chUndo([CH.rows[b.dataset.undo]], 'Put back ' + CH.rows[b.dataset.undo].name);
  if ((b = t('[data-undoall]'))){
    e.preventDefault();
    const rows = Object.entries(CH.rows).filter(([k]) => k.split('/')[0] === b.dataset.undoall).map(([, r]) => r);
    if (rows.length > 1 && !confirm(`Put back all ${rows.length}? (Undo takes it back.)`)) return;
    return chUndo(rows, `Put back ${rows.length} changes`);
  }
  if ((b = t('[data-diff]'))){
    const id = b.dataset.id;
    if (CH.diffs[id]){ delete CH.diffs[id]; return chRender(); }
    try { CH.diffs[id] = (await api('/api/tools/changes/diff?key=' + encodeURIComponent(b.dataset.diff))).changes; chRender(); } catch (err){ fail(err); }
    return;
  }
  if ((b = t('[data-pdiff]'))){
    const k = b.dataset.pdiff;
    if (CH.diffs[k]){ delete CH.diffs[k]; return chRender(); }
    try { CH.diffs[k] = (await api('/api/tools/changes/plugindiff?key=' + encodeURIComponent(k))).changes; chRender(); } catch (err){ fail(err); }
    return;
  }
  if ((b = t('[data-pgo]'))) return openRecord(b.dataset.pgo);
}

async function chUndo(rows, label){
  try {
    const d = await post('/api/edit', {label, ops: rows.map(r => r.undo)});
    setState(d.state); CH.diffs = {};
    toast(label + '. Undo takes it back.');
    await resync();
    chDraw();
  } catch (e){ fail(e); }
}

// what an opened plugin already was, before any edits here
function chPluginHtml(){
  const f = CH.find.toLowerCase();
  return `<div class="h" style="padding-left:0">What the plugin already has</div>
    <p class="note" style="padding:0">This came with the plugin you opened. It stays as it is unless you change it.</p>` + CH.plug.kinds.map(k => {
    const rows = k.rows.filter(r => !f || (r.edid + ' ' + r.key).toLowerCase().includes(f));
    return `<details class="tl-group"><summary><b>${esc(k.title)}</b><span class="note" style="padding:0">${k.new} of its own · ${k.changed} of the game's changed</span></summary>
      ${rows.map(r => `<div class="tl-row"><div class="t">${esc(r.edid || r.key)}${r.edid ? `<small>${esc(r.key)}</small>` : ''}</div>
        ${r.new ? '<span class="tl-sev ok">its own</span>' : `<button class="btn" data-pdiff="${esc(r.key)}">Difference</button>`}
        ${k.type !== 'REFR' && k.type !== 'ACHR' && k.type !== 'ACRE' && k.type !== 'CELL' && k.type !== 'WRLD' ? `<button class="btn" data-pgo="${esc(r.key)}">Go there</button>` : ''}</div>
        ${CH.diffs[r.key] ? `<pre class="tl-diff">${CH.diffs[r.key].length ? CH.diffs[r.key].map(chDiffLine).join('\n') : 'No difference: this says what the game says.'}</pre>` : ''}`).join('')}
      ${k.new + k.changed > k.rows.length ? `<div class="tl-more">The first ${k.rows.length} of ${k.new + k.changed}.</div>` : ''}</details>`;
  }).join('');
}
