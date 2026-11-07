// ---------- Mod conflicts: where a plugin clashes with the rest of the load order ----------
// A tab on the Tools page, added from here: runs conflicts.py on the server's own thread and asks how far it has got.
// Only reads, until a Move button is pressed (which goes through loadorder.py's backup). Also adds a short line to the
// Health check and a step to Get ready to share. All of it talks to /api/tools/conflicts/... (modtools.py).
const MCF = {file: '', rep: null, st: null, timer: 0, err: '', side: null, plugins: null};
const MCF_STAGES = {starting: 'Writing your mod as it would be saved…', reading: 'Reading the load order', finding: 'Finding who else has your records…', comparing: 'Comparing, field by field'};
const MCF_HARMLESS = {same: 'Byte for byte the same as yours', other_fields: 'Differ only in fields you left alone', no_change: 'Your copy changes nothing, and another wins', keeps_theirs: 'You win, and what they changed is in your copy too'};

TL_TABS.splice(2, 0, ['conflicts', 'Mod conflicts', 'Where your mod clashes with the rest of your load order', () => mcfDraw()]);

(function mcfCss(){
  const c = document.createElement('style');
  c.textContent = `
  .mcf-bar{height:8px;border-radius:4px;background:var(--line);max-width:520px;overflow:hidden;margin:8px 0}
  .mcf-bar>i{display:block;height:100%;background:var(--gold2);transition:width .2s}
  .mcf-issue{display:flex;gap:10px;align-items:baseline;padding:5px 14px;border-top:1px solid var(--line);font-size:13px}
  .mcf-issue:first-child{border-top:0}
  .mcf-issue>.t{flex:1;min-width:0}
  .mcf-issue small{display:block;color:var(--muted);font-size:12px}
  .mcf-row{padding:8px 14px;border-top:1px solid var(--line);font-size:13px}
  .mcf-row>.t{overflow-wrap:anywhere}
  .mcf-row .mcf-say{color:var(--muted);font-size:12.5px;margin-top:2px}
  .mcf-row .mcf-do{color:var(--muted);font-size:12.5px;margin-top:2px}
  .mcf-row .mcf-do b{font-weight:500;color:var(--gold2)}
  .mcf-row .mcf-chain{color:var(--faint);font-size:11.5px;margin-top:2px;overflow-wrap:anywhere}
  .mcf-row .mcf-btns{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
  .mcf-row .btn{padding:2px 8px;font-size:12px}
  .mcf-wrapx{overflow-x:auto;margin-top:8px}
  .mcf-side{border-collapse:collapse;font-size:12px;min-width:100%}
  .mcf-side th,.mcf-side td{border:1px solid var(--line);padding:3px 7px;text-align:left;vertical-align:top;overflow-wrap:anywhere;max-width:280px}
  .mcf-side th{color:var(--muted);font-weight:500;background:var(--bg2)}
  .mcf-side th.wins{color:var(--green)} .mcf-side th.mine{color:var(--gold2)}
  .mcf-side tr.differs td{background:var(--sel)}
  .mcf-side td.none{color:var(--faint)}`;
  document.head.appendChild(c);
})();

async function mcfDraw(){
  if (!MCF.plugins){ try { MCF.plugins = await api('/api/tools/plugins'); } catch (e){ MCF.plugins = {plugins: []}; } }
  if (!MCF.rep && !MCF.timer){
    try {
      const st = await api('/api/tools/conflicts/status');
      if (st.running) mcfFollow();
      else if (st.result && (!!MCF.file === !st.result.mine_open)) MCF.rep = st.result;
    } catch (e){ MCF.err = e.message; }
  }
  mcfRender();
  if (!MCF.rep && !MCF.timer && (MCF.file || A.state.project)) mcfStart();
}

async function mcfStart(){
  MCF.err = ''; MCF.side = null; MCF.rep = null;
  if (MCF.timer || (MCF.st && MCF.st.running)){ MCF.again = true; return mcfRender(); }    // (one at a time: this one when that's done)
  try {
    MCF.st = await post('/api/tools/conflicts/start', {file: MCF.file});
    if (MCF.st.error){ MCF.err = MCF.st.error; MCF.st = null; }
    else mcfFollow();
  } catch (e){ MCF.err = e.message; }
  mcfRender();
}

function mcfFollow(){
  clearTimeout(MCF.timer);
  MCF.timer = setTimeout(async () => {
    MCF.timer = 0;
    try {
      const st = await api('/api/tools/conflicts/status');
      MCF.st = st;
      if (st.running){ mcfFollow(); mcfProgress(); return; }
      if (MCF.again){ MCF.again = false; MCF.st = null; return mcfStart(); }
      if (st.error) MCF.err = st.error;
      else if (st.result){ MCF.rep = st.result; if (st.result.mine_open && typeof HC !== 'undefined' && HC.rep) HC.rep.conflicts = mcfShort(st.result); }
      MCF.st = null;
      mcfRender();
      if (TL.tab === 'share' && typeof relRender === 'function' && RL.d) relRender();
      if (TL.tab === 'health' && typeof healthRender === 'function') healthRender();
    } catch (e){ MCF.err = e.message; MCF.st = null; mcfRender(); }
  }, 300);
}

function mcfProgressHtml(){
  const s = MCF.st || {};
  const pct = s.total ? Math.round(100 * s.done / s.total) : 0;
  const what = MCF_STAGES[s.stage] || 'Starting…';
  const of = s.stage === 'reading' && s.total ? ` ${s.done + 1} of ${s.total}: ${s.file}` : s.stage === 'comparing' && s.total ? ` ${s.done} of ${s.total} records${s.file ? ', then ' + s.file : ''}` : '';
  return `<div class="card wide"><h3>Checking…</h3><p>${esc(what)}${esc(of)}</p><div class="mcf-bar"><i style="width:${pct}%"></i></div>
    <p class="note" style="padding:0">The first run reads every plugin's record headers and keeps them. After that only a changed file is read again.</p></div>`;
}
function mcfProgress(){
  const b = $('#mcf-progress');
  if (b) b.innerHTML = mcfProgressHtml();
  const r = $('#mcf-share');
  if (r) r.innerHTML = mcfShareBody();
}

function mcfRender(){
  if (TL.tab !== 'conflicts') return;
  const mod = A.state.project, list = (MCF.plugins && MCF.plugins.plugins) || [], r = MCF.rep;
  const opts = (mod ? `<option value="">My mod: ${esc(mod.plugin)}</option>` : '<option value="">(no mod open)</option>') +
    list.filter(p => !p.error).map(p => `<option value="${esc(p.file)}" ${MCF.file === p.file ? 'selected' : ''}>A look at ${esc(p.file)}</option>`).join('');
  const s = r && r.summary;
  $('#tl-body').innerHTML = `<h2>Mod conflicts</h2>
    <p class="note" style="padding:0">For every record your mod touches: who else changes it, who wins by load order, and whether what you changed survives. Only reads: nothing changes unless you press Move.</p>
    <div class="tl-bar"><select id="mcf-file">${opts}</select>
      <button class="btn" id="mcf-again">Check against my load order</button>
      ${s ? `<span class="tl-sev error">${s.error} will go wrong</span><span class="tl-sev warn">${s.warn} to look at</span><span class="tl-sev">${s.info} to know</span><span class="tl-sev ok">${s.harmless} harmless</span>` : ''}</div>
    ${MCF.err ? `<p class="tl-prob">${esc(MCF.err)}</p>` : ''}
    <div id="mcf-progress">${MCF.timer || (MCF.st && MCF.st.running) ? mcfProgressHtml() : ''}</div>
    <div id="mcf-list">${r ? mcfReport(r) : !(MCF.timer || MCF.st) && !MCF.err ? tlBox(mod ? '' : 'Start a mod, or pick a plugin above to look at.') : ''}</div>`;
  $('#mcf-file').onchange = e => { MCF.file = e.target.value; mcfStart(); };
  $('#mcf-again').onclick = mcfStart;
  const box = $('#mcf-list');
  box.onclick = mcfClick;
}

function mcfReport(r){
  const notes = (r.notes || []).map(n => `<p class="tl-prob">${esc(n)}</p>`).join('');
  const where = r.installed ? `It loads ${r.place}${r.place === 1 ? 'st' : ''} of ${r.of}${r.was_on ? '' : ' (it\'s switched off: checked as if on)'}.` :
    `It isn't in Data yet: checked as if installed, where it would load last.`;
  const head = `<p class="note" style="padding:0 0 6px">${esc(where)} It has ${r.touched} record${r.touched === 1 ? '' : 's'}; ${r.contested} ${r.contested === 1 ? 'is' : 'are'} also in other plugins.${r.seconds !== undefined ? ` Took ${r.seconds} s.` : ''}</p>${notes}`;
  if (!r.issues.length){
    return head + `<div class="card wide"><h3>No clashes</h3><p>Nothing your mod changes is lost to another plugin, and it doesn't undo anyone else's change.${r.summary.harmless ? ` ${r.summary.harmless} record${r.summary.harmless === 1 ? ' is' : 's are'} also in other plugins, harmlessly.` : ''}</p></div>` + mcfHarmless(r);
  }
  return head +
    `<div class="tl-group" style="padding:6px 0">${r.issues.map(i => `<div class="mcf-issue"><span class="tl-sev ${i.sev}">${i.count}</span><div class="t">${esc(i.title)}<small>${esc(i.why)}</small></div></div>`).join('')}</div>` +
    mcfMods(r) +
    r.groups.map((g, n) => `<details class="tl-group" ${g.sev === 'info' || r.groups.reduce((a, x) => a + x.count, 0) > 200 ? '' : 'open'}><summary><span class="tl-sev ${g.sev}">${g.count}</span><b>${esc(g.title)}</b></summary>
      <p class="tl-why">${esc(g.why)}</p>
      ${g.rows.map((x, i) => mcfRow(x, n, i)).join('')}
      ${g.count > g.rows.length ? `<div class="tl-more">…and ${g.count - g.rows.length} more of these. Settle what's above and check again.</div>` : ''}</details>`).join('') +
    mcfHarmless(r);
}

function mcfRow(x, n, i){
  const side = MCF.side && MCF.side.g === n && MCF.side.i === i;
  const chain = x.chain ? x.chain.map(p => p === x.wins ? `<b style="color:var(--green);font-weight:500">${esc(p)} wins</b>` : esc(p)).join(' · ') : '';
  return `<div class="mcf-row" data-g="${n}" data-i="${i}"><div class="t"><span class="tl-sev ${x.sev}">${esc(mcfWord(x.issue))}</span> ${esc(x.text)}</div>
    ${x.notice ? `<div class="mcf-say">${esc(x.notice)}</div>` : ''}
    ${x.advice ? `<div class="mcf-do"><b>What to do:</b> ${esc(x.advice)}</div>` : ''}
    ${chain ? `<div class="mcf-chain">Load order: ${chain}</div>` : ''}
    <div class="mcf-btns">
      ${x.key ? `<button class="btn" data-mcf="side">${side ? 'Hide' : 'Side by side'}</button>` : ''}
      ${x.move ? `<button class="btn primary" data-mcf="move">Load ${esc(x.move.plugin)} after ${esc(x.move.after)}</button>` : ''}
      ${x.fix ? `<button class="btn primary" data-mcf="fix">${esc(x.fix.label)}</button>` : ''}
      ${x.tool ? `<button class="btn" data-mcf="tool">Open the Load order</button>` : ''}
      ${x.go ? `<button class="btn" data-mcf="go">Go there</button>` : ''}
    </div>${side ? mcfSide() : ''}</div>`;
}
const mcfWord = i => ({master: 'Masters', deleted: 'Deleted', overwritten: 'Overwritten', navmesh: 'Navmesh', door: 'Door', land_seam: 'Seam', land: 'Ground', topic: 'Topic', cell_header: 'Place settings', you_overwrite: 'You undo them', patched: 'Patch'}[i] || i);

function mcfSide(){
  const d = MCF.side.d;
  if (!d) return '<div class="note">Reading each copy…</div>';
  if (!d.columns.length) return '<div class="note">FOLab can\'t find a copy of that record now.</div>';
  const top = d.columns.map(c => `<th class="${c.wins ? 'wins' : c.mine ? 'mine' : ''}">${esc(c.plugin)}${c.mine ? ' (yours)' : ''}${c.wins ? ' (wins)' : ''}${c.deleted ? ' (deleted)' : ''}</th>`).join('');
  return `<div class="mcf-wrapx"><table class="mcf-side"><tr><th></th>${top}</tr>
    ${d.rows.map(r => `<tr class="${r.differs ? 'differs' : ''}"><th>${esc(r.label)}</th>${r.values.map(v => v === null ? '<td class="none">not there</td>' : `<td>${esc(v)}</td>`).join('')}</tr>`).join('')}
  </table></div>`;
}

function mcfMods(r){
  const rows = r.mods.filter(m => m.beats || m.beaten);
  if (!rows.length) return '';
  return `<details class="tl-group" ${rows.length < 12 ? 'open' : ''}><summary><b>By plugin</b> <span class="note" style="padding:0">(${rows.length})</span></summary>
    <p class="tl-why">Who you clash with most. Moving a plugin settles all of its rows one way, so read what it would give up.</p>
    <table class="tl-table"><tr><th>Plugin</th><th>Beats you</th><th>You beat</th><th>Harmless</th><th></th></tr>
    ${rows.map((m, i) => `<tr><td>${esc(m.name)}</td><td>${m.beats}</td><td>${m.beaten}</td><td>${m.harmless}</td>
      <td>${m.move ? `<button class="btn" data-mcfmod="${i}">Load mine after it</button>` : m.why ? `<small class="note" style="padding:0">${esc(m.why)}</small>` : ''}</td></tr>`).join('')}</table></details>`;
}

function mcfHarmless(r){
  const keys = Object.keys(r.harmless || {}).filter(k => r.harmless[k]);
  if (!keys.length) return '';
  return `<details class="tl-group"><summary><span class="tl-sev ok">${r.summary.harmless}</span><b>Harmless</b></summary>
    <p class="tl-why">Other plugins have these too, but nothing you meant is lost.</p>
    ${keys.map(k => `<div class="tl-row"><div class="t">${esc(MCF_HARMLESS[k] || k)}</div><span class="note">${r.harmless[k]}</span></div>`).join('')}
    ${(r.harmless_rows || []).slice(0, 20).map(x => `<div class="tl-row"><div class="t">${esc(x.what)}<small>${esc(MCF_HARMLESS[x.why] || x.why)}: ${esc(x.who)}</small></div></div>`).join('')}</details>`;
}

async function mcfClick(e){
  const m = e.target.closest('[data-mcfmod]');
  if (m) return mcfMove(MCF.rep.mods.filter(x => x.beats || x.beaten)[+m.dataset.mcfmod].move);
  const b = e.target.closest('[data-mcf]');
  if (!b) return;
  const row = b.closest('.mcf-row'), g = +row.dataset.g, i = +row.dataset.i, x = MCF.rep.groups[g].rows[i], a = b.dataset.mcf;
  if (a === 'go') return toolGo(x.go);
  if (a === 'tool') return toolsPage('loadorder');
  if (a === 'move') return mcfMove(x.move);
  if (a === 'fix'){
    try {
      const d = await post('/api/tools/health/fix', {fixes: [x.fix]});
      if (d.state && d.state.project) setState(d.state);
      toast('Taken out. Undo takes it back.');
      if (typeof resync === 'function') await resync();
      mcfStart();
    } catch (err){ fail(err); }
    return;
  }
  if (a === 'side'){
    // (this row only: the page keeps its scroll, and what's open stays open)
    const was = MCF.side;
    const redraw = (gg, ii) => { const el = document.querySelector(`.mcf-row[data-g="${gg}"][data-i="${ii}"]`); if (el) el.outerHTML = mcfRow(MCF.rep.groups[gg].rows[ii], gg, ii); };
    MCF.side = was && was.g === g && was.i === i ? null : {g, i, d: null};
    if (was) redraw(was.g, was.i);
    if (!MCF.side) return;
    redraw(g, i);
    try { const d = await api('/api/tools/conflicts/compare?key=' + encodeURIComponent(x.key)); if (MCF.side && MCF.side.g === g && MCF.side.i === i) MCF.side.d = d; }
    catch (err){ fail(err); MCF.side = null; }
    redraw(g, i);
  }
}

async function mcfMove(mv){
  if (!mv) return;
  if (!confirm(`Load ${mv.plugin} after ${mv.after}?\n\nThis gives files new dates, as a mod manager does. Their contents aren't touched, and a copy of the old order is kept: Put back an earlier order on the Load order page restores it.`)) return;
  try {
    toast('Moving…');
    const d = await post('/api/tools/conflicts/move', mv);
    if (d.state && d.state.project) setState(d.state);
    toast(d.changed ? `Moved. ${d.moved.length} file${d.moved.length === 1 ? '' : 's'} given new dates; a copy of the old order is kept.` : 'Nothing to change.');
    if (typeof LO !== 'undefined') { LO.conf = null; LO.wins = null; }
    mcfStart();
  } catch (err){ fail(err); }
}

function mcfShort(r){
  const s = r.summary, parts = [];
  if (s.error) parts.push(`${s.error} clash${s.error === 1 ? '' : 'es'} that will go wrong`);
  if (s.warn) parts.push(`${s.warn} worth a look`);
  return {plugin: r.plugin, text: parts.join(', ') || 'No clashes with your load order.', sev: s.error ? 'error' : s.warn ? 'warn' : 'ok', harmless: s.harmless, mine: !!r.mine_open};
}

// ---------- a short line on the Health check ----------
const mcfHealthRender = healthRender;
healthRender = function(){
  mcfHealthRender();
  const list = $('#hc-list');
  if (TL.tab !== 'health' || !list || HC.file || !A.state.project || HC.busy) return;
  const s = HC.rep && HC.rep.conflicts;
  const line = s && s.mine ? `<span class="tl-sev ${s.sev}">${esc(s.sev === 'ok' ? 'clean' : s.sev === 'error' ? 'clashes' : 'to look at')}</span> ${esc(s.text)}` : 'Not checked against your load order yet.';
  const el = document.createElement('div');
  el.className = 'tl-row';
  el.style.cssText = 'background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 0;max-width:1040px;box-sizing:border-box';
  el.innerHTML = `<div class="t">${line}</div><button class="btn" id="mcf-hc">${s && s.mine ? 'Open it' : 'Check against my load order'}</button>`;
  list.parentNode.insertBefore(el, list);
  $('#mcf-hc').onclick = () => toolsPage('conflicts');
};

// ---------- a step in Get ready to share ----------
const mcfRelRender = relRender;
relRender = function(){
  mcfRelRender();
  if (TL.tab !== 'share' || !RL.d) return;
  const first = $('#tl-body').querySelector('.card');
  if (!first) return;
  const el = document.createElement('div');
  el.className = 'card wide';
  el.id = 'mcf-share';
  el.innerHTML = mcfShareBody();
  first.after(el);
  el.onclick = e => {
    if (e.target.closest('#mcf-share-go')){ MCF.file = ''; mcfStart().then(() => { const c = $('#mcf-share'); if (c) c.innerHTML = mcfShareBody(); }); }
    if (e.target.closest('#mcf-share-see')) toolsPage('conflicts');
  };
};
function mcfShareBody(){
  const r = MCF.rep && MCF.rep.mine_open ? mcfShort(MCF.rep) : null;
  const busy = MCF.timer || (MCF.st && MCF.st.running);
  return `<h3>Check against my load order</h3>
    <p>${busy ? 'Checking…' : r ? `<span class="tl-sev ${r.sev}">${esc(r.text)}</span> ` : 'See where your mod clashes with what you have installed. Players with other mods may meet the same.'}
      <button class="btn" id="mcf-share-go" ${busy ? 'disabled' : ''}>${r ? 'Check again' : 'Check against my load order'}</button>
      ${r ? '<button class="btn" id="mcf-share-see">Open it</button>' : ''}</p>`;
}
