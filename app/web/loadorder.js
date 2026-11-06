// ---------- Load order: what the game loads, in what order, and who wins ----------
// Tick to switch a plugin on or off, drag (or the arrows) to reorder, then Save. Nothing is written until Save; a copy of
// the old order is kept first. Conflicts between switched-on mods are looked for when asked.
const LO = {d: null, order: [], on: new Set(), dirty: false, conf: null, confBusy: false, wins: null, drag: null};

async function loDraw(){
  try { LO.d = await api('/api/tools/loadorder'); } catch (e){ $('#tl-body').innerHTML = tlBox(e.message); return; }
  LO.order = LO.d.rows.filter(r => r.found).map(r => r.name);
  LO.on = new Set(LO.d.rows.filter(r => r.active).map(r => r.name));
  LO.dirty = false;
  loRender();
}

const loRow = n => LO.d.rows.find(r => r.name === n);
function loProblems(){
  // (as the list stands now, unsaved changes included)
  const on = LO.order.filter(n => LO.on.has(n)), at = new Map(on.map((n, i) => [n.toLowerCase(), i])), have = new Set(LO.order.map(n => n.toLowerCase()));
  const out = {};
  for (const n of LO.order){
    const r = loRow(n), bad = (out[n] = []);
    if (r.error) bad.push("FOLab can't read it: " + r.error);
    if (!LO.on.has(n)) continue;
    for (const m of r.masters){
      const low = m.toLowerCase();
      if (!have.has(low)) bad.push(`Needs ${m}, which isn't in Data. The game won't start with this on.`);
      else if (!at.has(low)) bad.push(`Needs ${m}, which is switched off. The game won't start with this on.`);
      else if (at.get(low) > at.get(n.toLowerCase())) bad.push(`Needs ${m}, which loads after it.`);
    }
  }
  return out;
}

function loRender(){
  if (TL.tab !== 'loadorder') return;
  const d = LO.d, bad = loProblems();
  const anyBad = Object.values(bad).some(b => b.length);
  const lost = d.rows.filter(r => !r.found);
  let slot = 0;
  $('#tl-body').innerHTML = `<h2>Load order</h2>
    <p class="note" style="padding:0">The plugins New Vegas loads, top to bottom. When two change the same thing, the lower one wins. The game goes by the files' dates, so reordering here gives files new dates: their contents aren't touched, and the game's own files keep theirs.</p>
    ${d.notes.map(n => `<p class="tl-prob">${esc(n)}</p>`).join('')}
    <div class="tl-bar">
      <button class="btn primary" id="lo-save" ${LO.dirty ? '' : 'disabled'}>Save load order</button>
      <button class="btn" id="lo-undo" ${LO.dirty ? '' : 'disabled'}>Forget my changes</button>
      <button class="btn" id="lo-sort" ${anyBad ? '' : 'disabled'} title="Each plugin after what it needs, and what it needs switched on">Fix masters</button>
      <button class="btn" id="lo-conf">Find conflicts</button>
      ${d.backups.length ? `<select id="lo-back"><option value="">Put back an earlier order…</option>${d.backups.map(b => `<option>${esc(b)}</option>`).join('')}</select>` : ''}
      <span class="note">${LO.dirty ? 'Not saved yet.' : `${d.on} on.`}</span></div>
    <table class="tl-table"><tr><th></th><th>On</th><th>#</th><th>Plugin</th><th>By</th><th></th></tr>
    ${LO.order.map((n, i) => {
      const r = loRow(n), on = LO.on.has(n), s = on ? (slot++).toString(16).toUpperCase().padStart(2, '0') : '';
      const fixed = r.official, base = n.toLowerCase() === 'falloutnv.esm';
      return `<tr class="${on ? '' : 'off'}" data-i="${i}" ${fixed ? '' : 'draggable="true"'}>
        <td class="tl-grab">${fixed ? '' : '⠿'}</td>
        <td><input type="checkbox" data-on="${esc(n)}" ${on ? 'checked' : ''} ${base ? 'disabled' : ''}></td>
        <td class="note" style="padding:4px 8px">${s}</td>
        <td>${esc(n)}${r.mine ? ' <span class="tl-sev ok">your mod</span>' : ''}${r.esm ? ' <span class="tl-sev">master</span>' : ''}${fixed ? ' <span class="tl-sev">the game</span>' : ''}${r.helper ? ' <span class="tl-sev">FOLab\'s test helper</span>' : ''}
          ${r.masters.length ? `<div class="note" style="padding:0;font-size:11.5px">needs ${r.masters.map(esc).join(', ')}</div>` : ''}
          ${bad[n].map(b => `<div class="tl-prob">⚠ ${esc(b)}</div>`).join('')}</td>
        <td class="note" style="padding:4px 8px">${esc(r.author || '')}</td>
        <td style="white-space:nowrap">${fixed ? '' : `<button class="btn" data-mv="${i},-1" title="Load earlier">↑</button> <button class="btn" data-mv="${i},1" title="Load later">↓</button> `}
          <button class="btn" data-look="${esc(n)}" title="A health check of this plugin, read only">Look</button></td></tr>`;
    }).join('')}</table>
    ${lost.length ? `<div class="card wide"><h3>On the game's list, with no file in Data: ${lost.filter(r => LO.on.has(r.name)).length}</h3>
      <p>The game skips these. A mod manager may have left them, or may add the files when it starts the game, so saving keeps them listed unless you take them off.</p>
      <p class="note" style="padding:0">${lost.map(r => esc(r.name)).join(', ')}</p>
      <p><button class="btn" id="lo-forget" ${lost.some(r => LO.on.has(r.name)) ? '' : 'disabled'}>Take them off the list</button></p></div>` : ''}
    <p class="note" style="padding:8px 0 0">List: <code>${esc(d.plugins_txt)}</code></p>
    <div id="lo-conflicts">${loConflicts()}</div>`;
  $('#lo-save').onclick = loSave;
  $('#lo-undo').onclick = loDraw;
  $('#lo-sort').onclick = async () => { try { const s = await post('/api/tools/loadorder/sorted', {order: LO.order, active: [...LO.on]}); LO.order = s.order; LO.on = new Set(s.active); LO.dirty = true; loRender(); } catch (e){ fail(e); } };
  $('#lo-conf').onclick = loFindConflicts;
  const forget = $('#lo-forget');
  if (forget) forget.onclick = () => { lost.forEach(r => LO.on.delete(r.name)); LO.dirty = true; loRender(); };
  const back = $('#lo-back');
  if (back) back.onchange = async () => {
    if (!back.value || !confirm(`Put back the load order from ${back.value}? (A copy of how it is now is kept.)`)) return (back.value = '');
    try { await post('/api/tools/loadorder/restore', {name: back.value}); toast('Load order put back.'); loDraw(); } catch (e){ fail(e); }
  };
  const tb = $('#tl-body').querySelector('.tl-table');
  tb.onchange = e => { const c = e.target.closest('[data-on]'); if (c){ c.checked ? LO.on.add(c.dataset.on) : LO.on.delete(c.dataset.on); LO.dirty = true; loRender(); } };
  tb.onclick = e => {
    const m = e.target.closest('[data-mv]');
    if (m){ const [i, d] = m.dataset.mv.split(',').map(Number); loMove(i, i + d); }
    const l = e.target.closest('[data-look]');
    if (l){ HC.file = LO.d.rows.find(r => r.name === l.dataset.look && r.mine) ? '' : l.dataset.look; HC.rep = null; toolsPage('health'); }
  };
  tb.ondragstart = e => { const tr = e.target.closest('tr[data-i]'); if (tr){ LO.drag = +tr.dataset.i; tr.classList.add('drag'); e.dataTransfer.effectAllowed = 'move'; } };
  tb.ondragover = e => { if (LO.drag !== null && e.target.closest('tr[data-i]')) e.preventDefault(); };
  tb.ondrop = e => { const tr = e.target.closest('tr[data-i]'); if (tr && LO.drag !== null){ e.preventDefault(); loMove(LO.drag, +tr.dataset.i); } LO.drag = null; };
  tb.ondragend = () => { LO.drag = null; };
  const cf = $('#lo-conflicts');
  cf.onclick = e => {
    const r = e.target.closest('[data-key]');
    if (r) loWins(r.dataset.key);
    const g = e.target.closest('[data-rec]');
    if (g) openRecord(g.dataset.rec);
  };
}

function loMove(from, to){
  // (the game's own stay at the top: nothing goes above them)
  const fixed = LO.order.filter(n => loRow(n).official).length;
  to = Math.max(fixed, Math.min(LO.order.length - 1, to));
  if (from === to || loRow(LO.order[from]).official) return;
  const [n] = LO.order.splice(from, 1);
  LO.order.splice(to, 0, n);
  LO.dirty = true; loRender();
}

async function loSave(){
  try {
    const d = await post('/api/tools/loadorder/save', {order: LO.order, active: [...LO.on]});
    toast(d.changed ? `Load order saved. ${d.moved.length} file${d.moved.length === 1 ? '' : 's'} given new dates; a copy of the old order is kept.` : 'Nothing to change.');
    LO.conf = null; LO.wins = null;
    if (d.state) setState(d.state);
    loDraw();
  } catch (e){ fail(e); }
}

async function loFindConflicts(){
  LO.confBusy = true; LO.conf = null; LO.wins = null; loRender();
  try { LO.conf = await api('/api/tools/loadorder/conflicts'); } catch (e){ fail(e); }
  LO.confBusy = false; loRender();
}

function loConflicts(){
  if (LO.confBusy) return tlBox('Reading every switched-on mod…');
  const c = LO.conf; if (!c) return '';
  if (!c.total) return '<div class="card"><h3>No conflicts</h3><p>No two switched-on mods say different things about the same thing.</p></div>';
  const real = c.rows.filter(r => !r.parent), parents = c.rows.filter(r => r.parent);
  const row = r => `<div class="tl-row"><div class="t">${esc(r.edid || r.key)} <span class="note" style="padding:0">${esc(r.type)}</span>
        <small>${r.mods.map(m => m === r.wins ? `<b style="color:var(--green)">${esc(m)} wins</b>` : esc(m)).join(' · ')}</small></div>
      <button class="btn" data-key="${esc(r.key)}">Compare</button></div>
      ${LO.wins && LO.wins.key === r.key ? loWinsHtml() : ''}`;
  return `<h3 style="color:var(--gold2);font-weight:500;margin:18px 0 4px">Conflicts: ${c.total}</h3>
    <p class="note" style="padding:0">The lowest in the load order wins. Move a mod lower to let it win.</p>
    <div class="tl-group" style="margin-top:8px">${real.map(row).join('') || '<div class="tl-row">Only places and worlds, below.</div>'}</div>
    ${parents.length ? `<details class="tl-group"><summary><b>Places, worlds and topics both change (${parents.length})</b></summary>${parents.map(row).join('')}</details>` : ''}
    ${c.total > c.rows.length ? `<div class="tl-more">…and ${c.total - c.rows.length} more.</div>` : ''}`;
}

async function loWins(key){
  try { LO.wins = LO.wins && LO.wins.key === key ? null : await api('/api/tools/loadorder/wins?key=' + encodeURIComponent(key)); loRender(); } catch (e){ fail(e); }
}
function loWinsHtml(){
  return LO.wins.copies.map(c => `<pre class="tl-diff"><b>${esc(c.plugin)}</b>${c.wins ? ' (wins)' : ''}${c.game ? ' (the game)' : ''}${c.deleted ? ' (deleted)' : ''}
${c.changes.map(mcDiffLine).join('\n') || (c.game ? '' : 'the same as the one before')}</pre>`).join('');
}
// one difference: what it was, what it is
function mcDiffLine(c){
  return `${esc(c.label)}: ${c.old !== null && c.old !== undefined ? `<del>${esc(c.old)}</del>` : ''}${c.old !== null && c.old !== undefined && c.new !== null && c.new !== undefined ? ' → ' : ''}${c.new !== null && c.new !== undefined ? `<ins>${esc(c.new)}</ins>` : '(gone)'}`;
}
