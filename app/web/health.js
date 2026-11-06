// ---------- The Health check: a plugin's problems in plain words, a click to go there, a fix where one is safe ----------
const HC = {file: '', rep: null, plugins: null, busy: false};
const HC_SEV = {error: 'Will cause trouble', warn: 'Worth a look', info: 'Good to know'};

async function healthDraw(){
  if (!HC.plugins){ try { HC.plugins = await api('/api/tools/plugins'); } catch (e){ HC.plugins = {plugins: []}; } }
  healthRender();
  if (HC.file || A.state.project) healthRun();     // (always afresh: the mod may have changed since)
}

async function healthRun(){
  HC.busy = true; HC.rep = null; healthRender();
  try { HC.rep = await api('/api/tools/health' + (HC.file ? '?file=' + encodeURIComponent(HC.file) : '')); }
  catch (e){ fail(e); }
  HC.busy = false; healthRender();
}

function healthRender(){
  if (TL.tab !== 'health') return;
  const r = HC.rep, mod = A.state.project;
  const list = (HC.plugins && HC.plugins.plugins) || [];
  const opts = (mod ? `<option value="">My mod: ${esc(mod.plugin)}</option>` : '<option value="">(no mod open)</option>') +
    list.filter(p => !p.error).map(p => `<option value="${esc(p.file)}" ${HC.file === p.file ? 'selected' : ''}>A look at ${esc(p.file)}</option>`).join('');
  const fixable = r ? r.groups.reduce((n, g) => n + g.fixable, 0) : 0;
  $('#tl-body').innerHTML = `<h2>Health check</h2>
    <p class="note" style="padding:0">What's wrong, in plain words. Nothing changes unless you press a fix, and each fix can be undone.</p>
    <div class="tl-bar"><select id="hc-file">${opts}</select>
      <button class="btn" id="hc-again">Check again</button>
      ${r && r.mine && fixable ? `<button class="btn primary" id="hc-all">Fix everything safe (${fixable})</button>` : ''}
      ${r && !r.mine ? `<button class="btn" id="hc-open">Open it as my mod</button>` : ''}
      ${r ? `<span class="tl-sev error">${r.summary.error} trouble</span><span class="tl-sev warn">${r.summary.warn} to look at</span><span class="tl-sev">${r.summary.info} to know</span>` : ''}</div>
    ${r && !r.mine ? `<p class="note" style="padding:0 0 8px">A read-only look: FOLab only reads ${esc(r.plugin)}, so there are no fixes here. Open it as your mod to fix things in a copy.</p>` : ''}
    <div id="hc-list">${HC.busy ? tlBox('Checking every record… a big plugin takes a little while.') : !r ? tlBox(mod ? '' : 'Start a mod, or pick a plugin above to look at.') :
      !r.groups.length ? '<div class="card"><h3>No problems found</h3><p>Nothing here FOLab knows to look for. The game itself is the final test.</p></div>' : r.groups.map(healthGroup).join('')}</div>`;
  $('#hc-file').onchange = e => { HC.file = e.target.value; healthRun(); };
  $('#hc-again').onclick = healthRun;
  const all = $('#hc-all');
  if (all) all.onclick = () => healthFix(r.groups.flatMap(g => g.rows.filter(x => x.fix && !x.fix.one).map(x => x.fix)));
  const op = $('#hc-open');
  if (op) op.onclick = async () => {
    toast('Opening ' + r.plugin + '… (loading it on top of the game takes a few seconds)');
    try { setState(await post('/api/project/adopt', {file: r.plugin})); await loadPlaces(); if (typeof BW !== 'undefined') BW.types = []; HC.file = ''; healthRun(); }
    catch (e){ fail(e); }
  };
  const box = $('#hc-list');
  box.onclick = e => {
    const g = e.target.closest('[data-go]');
    if (g) return toolGo(HC.rep.groups[+g.dataset.g].rows[+g.dataset.go].go);
    const f = e.target.closest('[data-fix]');
    if (f) return healthFix([HC.rep.groups[+f.dataset.g].rows[+f.dataset.fix].fix]);
    const a = e.target.closest('[data-fixall]');
    if (a){ e.preventDefault(); return healthFix(HC.rep.groups[+a.dataset.fixall].rows.filter(x => x.fix && !x.fix.one).map(x => x.fix)); }
  };
}

function healthGroup(g, n){
  return `<details class="tl-group" ${g.sev === 'info' ? '' : 'open'}><summary><span class="tl-sev ${g.sev}" title="${esc(HC_SEV[g.sev])}">${g.count}</span><b>${esc(g.title)}</b><span class="sp"></span>
      ${g.fixable > 1 ? `<button class="btn" data-fixall="${n}">Fix all ${g.fixable}</button>` : ''}</summary>
    <p class="tl-why">${esc(g.why)}</p>
    ${g.rows.map((r, i) => `<div class="tl-row"><div class="t">${esc(r.text)}${r.sub ? `<small>${r.sub.map(esc).join(', ')}</small>` : ''}</div>
      ${r.go ? `<button class="btn" data-g="${n}" data-go="${i}">Go there</button>` : ''}
      ${r.fix ? `<button class="btn primary" data-g="${n}" data-fix="${i}">${esc(r.fix.label)}</button>` : ''}</div>`).join('')}
    ${g.count > g.rows.length ? `<div class="tl-more">…and ${g.count - g.rows.length} more. Fix these and check again to see them.</div>` : ''}</details>`;
}

async function healthFix(fixes){
  if (!fixes.length) return;
  try {
    const d = await post('/api/tools/health/fix', {fixes});
    if (d.state && d.state.project) setState(d.state);
    toast(`${d.fixed} fixed${d.failed && d.failed.length ? ', ' + d.failed.length + ' couldn\'t be: ' + d.failed[0] : ''}. Undo takes it back.`, d.failed && d.failed.length);
    await resync();
    healthRun();
  } catch (e){ fail(e); }
}
