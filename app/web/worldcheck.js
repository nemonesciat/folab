// ---------- Health: Your worlds (worldcheck.py) ----------
// Under the health check of the mod: what every world the mod made or changed outside needs (a Pip-Boy map, a far view,
// edges that meet, no water in the air, a draw count the game can carry), checked on a click, each with where and what to do.
const WC = {job: null, timer: null};

(function wcWrap(){
  const was = healthRender;
  healthRender = function(){ was(); wcDraw(); };
})();

function wcDraw(){
  if (TL.tab !== 'health' || HC.file || !A.state.project) return;
  const list = $('#hc-list');
  if (!list) return;
  let box = $('#wc-box');
  if (!box){ box = document.createElement('div'); box.id = 'wc-box'; list.after(box); }
  const j = WC.job;
  const lv = {error: ['trouble', 'error'], warn: ['to look at', 'warn'], info: ['fine', 'ok']};
  let body = '';
  if (j && j.running) body = `<div class="tl-why">Checking… ${esc(j.said || '')}${j.total ? ` (${j.done} of ${j.total})` : ''}</div>`;
  else if (j && j.ok === false) body = `<div class="tl-why tl-prob">${esc(j.error)}</div>`;
  else if (j && j.worlds){
    body = j.worlds.length ? j.worlds.map(w => `<div class="tl-row" style="background:var(--bg2)"><div class="t"><b style="color:var(--gold2);font-weight:500">${esc(w.name)}</b>
        <small>${w.own ? 'a world of your own' : 'the game\'s world'} · ${w.cells.toLocaleString()} cell${w.cells === 1 ? '' : 's'} changed</small></div></div>` +
      w.findings.map((f, n) => `<div class="tl-row"><span class="tl-sev ${lv[f.level][1]}">${lv[f.level][0]}</span><div class="t">${esc(f.text)}
        ${f.cells.length ? `<small>${f.cells.slice(0, 12).map((c, i) => `<a href="#" data-wcgo="${esc(w.world)}|${c[0]}|${c[1]}">${c[0]}, ${c[1]}</a>`).join(' · ')}${f.cells.length > 12 ? ` and ${f.cells.length - 12} more` : ''}</small>` : ''}</div>
        ${f.fix && f.level !== 'info' ? `<button class="btn" data-wcfix="${esc(f.fix)}">Big jobs…</button>` : ''}</div>`).join('')).join('')
      : '<div class="tl-why">Your mod changes nothing outside.</div>';
  }
  box.innerHTML = `<div class="tl-group" style="max-width:1040px"><div style="padding:10px 14px;display:flex;align-items:center;gap:10px">
      <b style="color:var(--gold2);font-weight:500;flex:1">Your worlds: what a world needs</b>
      <button class="btn" id="wc-run"${j && j.running ? ' disabled' : ''}>${j && j.worlds ? 'Check again' : 'Check my worlds'}</button></div>
    <p class="tl-why">A Pip-Boy map, a far view, cell edges that meet, no water hanging in the air, and not more to draw than the game can carry.
      It counts what's drawn round every cell you changed, so a big world takes a minute.</p>${body}</div>`;
  $('#wc-run').onclick = wcRun;
  box.querySelectorAll('[data-wcfix]').forEach(b => b.onclick = () => toolsPage('bigjobs'));
  box.querySelectorAll('[data-wcgo]').forEach(a => a.onclick = async e => {
    e.preventDefault();
    const [world, x, y] = a.dataset.wcgo.split('|');
    const rows = await api(`/api/goto?q=${encodeURIComponent(x + ', ' + y)}&world=${encodeURIComponent(world)}`).catch(() => []);
    if (rows.length) gotoPick(rows[0]);
  });
}

async function wcRun(){
  try { WC.job = await api('/api/tools/worldcheck?start=1'); } catch (e){ fail(e); return; }
  wcDraw();
  const poll = async () => {
    WC.job = await api('/api/tools/worldcheck').catch(e => ({ok: false, error: e.message}));
    wcDraw();
    if (WC.job.running) WC.timer = setTimeout(poll, 1200);
  };
  clearTimeout(WC.timer);
  if (WC.job.running) WC.timer = setTimeout(poll, 1200);
}
