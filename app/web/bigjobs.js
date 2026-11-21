// ---------- Tools: Big jobs ----------
// The one-click steps a whole world needs (bigjobs.py): pick a world and a job; it copies the mod into backups first,
// runs with a progress bar, lands as one Undo, and says what changed and what to run next.
const BJ = {page: null, world: null, timer: null, last: null, nav: ''};
TL_TABS.splice(1, 0, ['bigjobs', 'Big jobs', 'Whole-world steps in one click: things back on the ground, plants, Pip-Boy map, guard towers', () => bjDraw()]);

(function bjCss(){
  const c = document.createElement('style');
  c.textContent = `
  .bj-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;max-width:1040px;margin-top:10px}
  .bj-job{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:8px}
  .bj-job b{color:var(--gold2);font-weight:500}
  .bj-job p{margin:0;color:var(--muted);font-size:12.5px;flex:1}
  .bj-job .btn{align-self:flex-start}
  .bj-run{border:1px solid var(--gold2);border-radius:10px;padding:12px 14px;margin:10px 0;max-width:1040px;background:var(--panel)}
  .bj-bar{height:8px;background:var(--bg2);border-radius:4px;overflow:hidden;margin:8px 0}
  .bj-bar>div{height:100%;background:var(--gold2);transition:width .4s}
  .bj-bar.unknown>div{width:30%;animation:bjslide 1.4s linear infinite}
  @keyframes bjslide{from{margin-left:-30%}to{margin-left:100%}}
  .bj-counts{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:13px;margin:6px 0}
  .bj-counts b{color:var(--gold2);font-weight:500}
  .bj-rep{font:12px var(--mono);color:var(--muted);white-space:pre-wrap;margin:6px 0 0}
  #tl-body .bj-muted{color:var(--muted)}`;
  document.head.appendChild(c);
})();

async function bjDraw(){
  try { BJ.page = await api('/api/jobs'); }
  catch (e){ $('#tl-body').innerHTML = '<h2>Big jobs</h2>' + tlBox(e.message); return; }
  const ws = BJ.page.worlds;
  if (!BJ.world || !ws.some(w => w.id === BJ.world)) BJ.world = ws.length ? ws[0].id : null;
  BJ.last = BJ.page.job;
  bjRender();
  if (BJ.last && BJ.last.running) bjPoll();
}

const bjTitle = k => (BJ.page.jobs.find(j => j.key === k) || {}).title || k;
const bjTime = s => s >= 90 ? Math.round(s / 60) + ' minutes' : s + ' seconds';

function bjResult(j){
  if (!j || !j.key) return '';
  if (j.running){
    const pct = j.total ? Math.min(100, Math.round(100 * j.done / j.total)) : 0;
    const secs = Math.round(Date.now() / 1000 - j.started);
    return `<div class="bj-run"><b>${esc(j.title)}</b> <span class="bj-muted">running for ${bjTime(secs)}</span>
      <div class="bj-bar${j.total ? '' : ' unknown'}"><div style="width:${pct}%"></div></div>
      <div class="bj-muted">${esc(j.said || '')}${j.total ? ` (${j.done.toLocaleString()} of ${j.total.toLocaleString()})` : ''}</div>
      <small class="bj-muted">You can keep using the rest of FOLab's pages; edits wait until this is done.</small></div>`;
  }
  const counts = Object.entries(j.counts || {}).map(([k, v]) => `<span><b>${v.toLocaleString()}</b> ${esc(k)}</span>`).join('');
  const rep = (j.report || []).map(r => Object.entries(r).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join('   ')).filter(Boolean).join('\n');
  const then = (j.then || []).map(k => `<button class="btn" data-bjrun="${esc(k)}">Next: ${esc(bjTitle(k))}</button>`).join('');
  const nav = (j.navmesh || []).length;
  return `<div class="bj-run"><b>${esc(j.title)}</b> <span class="bj-muted">${j.ok ? 'done' : 'stopped'}${j.took != null ? ' in ' + bjTime(j.took) : ''}</span>
    ${j.ok === false ? `<div class="tl-prob" style="margin:6px 0">${esc(j.error)}${j.changed ? ' What it had done by then is one step you can undo.' : ' Nothing was changed.'}</div>` : ''}
    ${j.ok && !j.changed ? '<div style="margin:6px 0">Nothing needed changing.</div>' : ''}
    ${counts ? `<div class="bj-counts">${counts}</div>` : ''}
    ${rep ? `<details><summary class="bj-muted" style="cursor:pointer">The details</summary><pre class="bj-rep">${esc(rep)}</pre></details>` : ''}
    ${j.backup ? `<div class="bj-muted" style="font-size:12px;margin-top:6px">The mod as it was before is kept in backups as "${esc(j.backup)}".</div>` : ''}
    ${j.undone ? '<div style="margin-top:6px">Undone.</div>' : ''}
    ${nav ? `<div style="margin-top:8px">${nav} cell${nav === 1 ? '' : 's'} now need${nav === 1 ? 's' : ''} its navmesh made again, or people will walk through what changed.
      <button class="btn" id="bj-nav">Make ${nav === 1 ? 'it' : 'them'} now</button> <span class="bj-muted" id="bj-navsaid">${esc(BJ.nav)}</span></div>` : ''}
    <div class="tl-bar">${j.undo ? '<button class="btn" id="bj-undo">Undo this job</button>' : ''}${j.ok ? then : ''}</div></div>`;
}

function bjRender(){
  const p = BJ.page;
  if (!p.mod){ $('#tl-body').innerHTML = '<h2>Big jobs</h2>' + tlBox('Open or start a mod first.'); return; }
  const running = BJ.last && BJ.last.running;
  $('#tl-body').innerHTML = `<h2>Big jobs</h2>
    <p class="bj-muted" style="max-width:820px">Steps that go over a whole world at once. Each one first copies your mod into backups, then shows
      how far it has got, and lands as <b>one</b> Undo however much it changes. Close the game first: FOLab won't change a mod the game has loaded.</p>
    <div class="tl-bar"><label class="bj-muted">World</label>
      <select id="bj-world">${p.worlds.map(w => `<option value="${esc(w.id)}"${w.id === BJ.world ? ' selected' : ''}>${esc(w.name || w.edid)} (${w.cells.toLocaleString()} cells${w.mine ? ', changed by your mod' : ''})</option>`).join('')}</select></div>
    <div id="bj-result">${bjResult(BJ.last)}</div>
    <div class="bj-grid">${p.jobs.map(j => `<div class="bj-job"><b>${esc(j.title)}</b><p>${esc(j.about)}</p>
      <button class="btn primary" data-bjrun="${esc(j.key)}"${running ? ' disabled' : ''}>Run it</button></div>`).join('')}</div>`;
  $('#bj-world').onchange = e => { BJ.world = e.target.value; };
  bjWire();
}

function bjWire(){
  $('#tl-body').querySelectorAll('[data-bjrun]').forEach(b => b.onclick = () => bjStart(b.dataset.bjrun));
  const u = $('#bj-undo');
  if (u) u.onclick = async () => {
    try { const d = await post('/api/jobs/undo'); setState(d.state); BJ.last = d.job; bjRender(); toast('Undone.'); } catch (e){ fail(e); }
  };
  const n = $('#bj-nav');
  if (n) n.onclick = () => bjNav(BJ.last.navmesh, BJ.last.world);
}

async function bjStart(key){
  const job = BJ.page.jobs.find(j => j.key === key);
  if (!job) return;
  const w = BJ.page.worlds.find(x => x.id === BJ.world);
  if (job.world && !w){ toast('Pick a world first.', true); return; }
  if (!confirm(`Run "${job.title}"${job.world ? ' on ' + (w.name || w.edid) : ''}?\n\nYour mod is copied into backups first, and the whole job is one Undo.`)) return;
  try {
    const d = await post('/api/jobs/start', {job: key, world: BJ.world});
    BJ.last = d.job; BJ.nav = ''; bjRender(); bjPoll();
  } catch (e){ fail(e); }
}

function bjPoll(){
  clearTimeout(BJ.timer);
  BJ.timer = setTimeout(async () => {
    const d = await api('/api/jobs/status').catch(() => null);
    if (!d) { bjPoll(); return; }
    BJ.last = d.job;
    const here = TL.tab === 'bigjobs' && $('#page-tools').style.display !== 'none';
    if (here && $('#bj-result')){ $('#bj-result').innerHTML = bjResult(BJ.last); bjWire(); }
    if (BJ.last.running){ bjPoll(); return; }
    if (BJ.last.changed){ try { setState((await post('/api/jobs/state')).state); } catch (e){} }
    if (here) bjRender();
    toast(BJ.last.ok ? `${BJ.last.title}: done.` : `${BJ.last.title}: ${BJ.last.error}`, !BJ.last.ok);
  }, 1000);
}

async function bjNav(cells, world){
  try { await post('/api/w/nav/make', {world, cells}); } catch (e){ fail(e); return; }
  const tick = async () => {
    const j = await api('/api/w/nav/job').catch(() => null);
    if (!j) return;
    if (j.running){ BJ.nav = `Making navmeshes: ${j.done} of ${j.total} cells (about 5 seconds each)…`; }
    else {
      BJ.nav = j.ok === false ? 'Could not make them: ' + j.error : `Made ${j.result ? j.result.cells : cells.length} navmeshes.`;
      if (j.state) setState(j.state);
      if (j.ok !== false) BJ.last.navmesh = [];
    }
    if ($('#bj-result')){ $('#bj-result').innerHTML = bjResult(BJ.last); bjWire(); }
    if (j.running) setTimeout(tick, 1500);
  };
  tick();
}
