// ---------- Tools: Test in game ----------
// Does this place really work in the game? gametest.py plans what to check; a run starts the real game only behind the words
// typed here (it's never been run yet: see the help page). The report reads back what the game wrote, worst first.
const GT = {cell: null, status: null, plan: null, report: null, reportOf: null, busy: '', timer: null, showRead: false};
TL_TABS.push(['gametest', 'Test in game', 'Let the game walk a place and write down what goes wrong', () => gtDraw()]);

(function gtCss(){
  const c = document.createElement('style');
  c.textContent = `
  .gt-counts{display:flex;flex-wrap:wrap;gap:6px 18px;margin:6px 0;font-size:13px}
  .gt-counts b{color:var(--gold2);font-weight:500}
  .gt-check{display:flex;gap:8px;font-size:13px;padding:2px 0}
  .gt-check .y{color:var(--green)} .gt-check .n{color:var(--red)} .gt-check .i{color:var(--faint)}
  .gt-lock{border:1px solid var(--amber);border-radius:10px;padding:12px 14px;margin:10px 0;max-width:1040px}
  .gt-lock input{width:220px} .gt-lock a{color:var(--gold2)}
  .gt-verdict{font:600 16px Oswald,'Arial Narrow',sans-serif;margin:4px 0}
  .gt-verdict.works{color:var(--green)} .gt-verdict.problems,.gt-verdict.never{color:var(--red)} .gt-verdict.incomplete{color:var(--amber)}
  #gt-text{width:100%;box-sizing:border-box;height:110px;font:12px var(--mono)}`;
  document.head.appendChild(c);
})();

async function gtDraw(){
  try {
    GT.status = await api('/api/tools/gametest/status');
  } catch (e){ $('#tl-body').innerHTML = '<h2>Test in game</h2>' + tlBox(e.message); return; }
  const s = GT.status;
  if (!GT.cell && s.places.length) GT.cell = s.places[0].key;
  gtRender();
  clearTimeout(GT.timer);
  if (s.running) GT.timer = setTimeout(() => { if (TL.tab === 'gametest' && $('#page-tools').style.display !== 'none') gtDraw(); }, 2000);
}

function gtRender(){
  if (TL.tab !== 'gametest') return;
  const s = GT.status;
  const rec = s.recovery || {};
  const words = {'game still running': `The game from an earlier test run is still running (process ${rec.pid}). Your files go back when it closes.`,
                 restored: 'An earlier test run was cut off. Your files have been put back; its report is below.',
                 'could not restore': 'An earlier test run was cut off, and some of your files couldn\'t be put back yet: ' + (rec.problems || []).join('; ')}[rec.state];
  $('#tl-body').innerHTML = `<h2>Test in game</h2>
    <p class="note" style="padding:0">The game walks a place by itself: it stands on every piece of floor, goes through every door, looks under what should rest on something, and writes what it finds. The report comes from that.</p>
    ${words ? `<div class="gt-lock"><b>${esc(words)}</b> ${rec.earlier ? '<button class="btn" data-gt="dismiss">OK</button>' : ''}</div>` : ''}
    ${s.mod ? '' : tlBox('Start or open a mod first.')}
    ${s.places.length ? `<div class="tl-bar"><label>Place <select id="gt-cell">${s.places.map(p => `<option value="${esc(p.key)}" ${p.key === GT.cell ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}</select></label>
      <button class="btn" data-gt="plan">See what it would check</button>
      <button class="btn" data-gt="read">Read a result file…</button></div>` : (s.mod ? tlBox('Your mod has no places yet: nothing to test.') : '')}
    ${GT.busy ? tlBox(GT.busy) : ''}
    ${s.running ? `<div class="gt-lock"><b>A run is going: ${esc(s.state)}.</b> <button class="btn" data-gt="stop">Stop it</button></div>` : ''}
    ${s.error ? `<p class="tl-prob">${esc(s.error)}</p>` : ''}
    ${GT.showRead ? gtReadBox() : ''}
    ${GT.plan ? gtPlanBox() : ''}
    ${GT.report ? gtReportBox(GT.report) : ''}
    ${s.runs.length ? `<div class="tl-group"><div class="tl-row"><div class="t"><b>Earlier runs</b></div></div>${s.runs.map(r => `<div class="tl-row"><div class="t">${esc(r.run)}: ${esc(r.name || '')}<small>${esc(r.verdict || '')}</small></div>
      <button class="btn" data-gt-run="${esc(r.run)}">Open</button></div>`).join('')}</div>` : ''}`;
  $('#tl-body').onclick = gtClick;
  $('#tl-body').onchange = e => { if (e.target.id === 'gt-cell'){ GT.cell = e.target.value; GT.plan = null; gtRender(); } };
}

function gtPlanBox(){
  const {plan: p, preflight} = GT.plan;
  const blocked = preflight.some(r => !r.ok);
  const c = p.counts;
  return `<div class="card wide"><h3>${esc(p.name || p.edid)}</h3>
    <div class="gt-counts"><span>Floor points: <b>${c.points}</b></span><span>Doors: <b>${c.doors}</b></span><span>Things to rest: <b>${c.things}</b></span><span>Characters: <b>${c.actors}</b></span><span>Walks to follow: <b>${c.walks}</b></span>
      <span>Floor from <b>${esc(p.mesh.source)}</b></span><span>About <b>${Math.ceil(p.estimate / 60)}</b> minutes</span></div>
    ${p.notes.map(n => `<p class="note" style="padding:2px 0">${esc(n)}</p>`).join('')}
    ${p.offline.length ? `<h3 style="margin-top:8px">Seen already, without the game</h3>${p.offline.map(o => `<div class="gt-check"><span class="tl-sev ${o.sev === 'warn' ? 'warn' : 'error'}">${esc(o.sev)}</span><span>${esc(o.text)}</span></div>`).join('')}` : ''}
    <h3 style="margin-top:8px">Before it can start</h3>
    ${preflight.map(r => `<div class="gt-check"><span class="${r.note ? 'i' : r.ok ? 'y' : 'n'}">${r.note ? 'note' : r.ok ? 'yes' : 'NO'}</span><span>${esc(r.text)}</span></div>`).join('')}
    <div class="gt-lock"><p style="margin:0 0 6px"><b>This starts your real game.</b> It has never yet been run for real. While it runs FOLab changes your settings and plugin list for the run, keeps your saves apart, and puts everything back afterwards, or when it next starts if it crashes. <a href="#" data-doc="game-test">What it does, and what isn't known yet</a>.</p>
      <p style="margin:0">To start, type <code>${esc(GT.status.confirm)}</code> <input type="text" id="gt-words" autocomplete="off"> <button class="btn" data-gt="start" ${blocked || GT.status.running ? 'disabled' : ''}>Start the game</button></p></div></div>`;
}

function gtReadBox(){
  return `<div class="card wide"><h3>Read a result file</h3><p>Paste what a run wrote, to see its report for the place above. The game isn't involved.</p>
    <textarea id="gt-text" spellcheck="false" placeholder="boot|gr|...&#10;go|1&#10;..."></textarea>
    <p><button class="btn" data-gt="readgo">Read it</button></p></div>`;
}

function gtReportBox(r){
  const cls = {'never started': 'never', incomplete: 'incomplete', problems: 'problems', works: 'works'}[r.verdict];
  const row = (l, k) => `<span>${l}: <b>${r.done[k]}</b> of ${r.totals[k]}</span>`;
  const max = 300;
  return `<div class="card wide"><h3>${esc(r.name || '')}${GT.reportOf ? ': run of ' + esc(GT.reportOf) : ''}</h3>
    <div class="gt-verdict ${cls}">${esc(r.said)}</div>
    ${r.ending_said ? `<p style="margin:2px 0">${esc(r.ending_said)}</p>` : ''}
    <div class="gt-counts">${row('Floor points', 'points')}${row('Doors', 'doors')}${row('Things', 'things')}${row('Characters', 'actors')}${row('Walks', 'walks')}${r.seconds != null ? `<span><b>${r.seconds}</b> seconds</span>` : ''}</div>
    ${r.advice ? `<p class="tl-prob" style="margin:6px 0">${esc(r.advice.text)} <small>(${esc(r.advice.doc)})</small></p>` : ''}
    ${r.rays && !r.rays.ok && r.last_line ? `<p class="note" style="padding:2px 0">${esc(r.rays.why)}</p>` : ''}</div>
    <div class="tl-group">${r.findings.slice(0, max).map(f => `<div class="tl-row"><span class="tl-sev ${f.sev === 'info' ? '' : f.sev === 'warn' ? 'warn' : 'error'}">${esc(f.sev)}</span>
      <div class="t">${esc(f.text)}<small>${esc(f.kind)}${f.p ? ' · ' + f.p.map(v => Math.round(v)).join(', ') : ''}</small></div>
      ${f.go && f.go.cell && (f.p || f.go.ref) ? `<button class="btn" data-gt-go="${esc(JSON.stringify(f.go))}">Go there</button>` : ''}</div>`).join('') || '<div class="tl-row">Nothing to report.</div>'}
      ${r.findings.length > max ? `<div class="tl-more">And ${r.findings.length - max} more.</div>` : ''}</div>`;
}

async function gtClick(e){
  const go = e.target.closest('[data-gt-go]');
  if (go) return toolGo(JSON.parse(go.dataset.gtGo));
  const open = e.target.closest('[data-gt-run]');
  if (open){
    try { GT.report = await api('/api/tools/gametest/report?run=' + encodeURIComponent(open.dataset.gtRun)); GT.reportOf = open.dataset.gtRun; gtRender(); } catch (err){ fail(err); }
    return;
  }
  const b = e.target.closest('[data-gt]');
  if (!b) return;
  try {
    const act = b.dataset.gt;
    if (act === 'plan'){
      GT.busy = 'Working out what to check…'; GT.plan = null; gtRender();
      GT.plan = await api('/api/tools/gametest/plan?cell=' + encodeURIComponent(GT.cell));
      GT.busy = ''; gtRender();
    } else if (act === 'read'){
      GT.showRead = !GT.showRead; gtRender();
    } else if (act === 'readgo'){
      GT.report = await post('/api/tools/gametest/read', {cell: GT.cell, text: $('#gt-text').value}); GT.reportOf = null; GT.showRead = false; gtRender();
    } else if (act === 'start'){
      await post('/api/tools/gametest/start', {cell: GT.cell, confirmation: $('#gt-words').value});
      GT.plan = null; GT.report = null; await gtDraw();
    } else if (act === 'stop'){
      await post('/api/tools/gametest/stop', {}); await gtDraw();
    } else if (act === 'dismiss'){
      await post('/api/tools/gametest/dismiss', {}); await gtDraw();
    }
  } catch (err){ GT.busy = ''; gtRender(); fail(err); }
}
