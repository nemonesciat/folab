// ---------- World tools: a panel over the map, for what's painted or marked on it, cell by cell ----------
// Navmesh (mark cells, make them, see what's out of date) and, on tabs of their own, whatever else is laid on the map.
// Each tab is {label, draw(box), map(g): draws on the flat map, mouse(kind, e): true if it used the mouse}.
const WT = {on: false, tab: 'nav', tabs: {}, order: []};
function wtTab(id, label, t){ WT.tabs[id] = Object.assign({label}, t); WT.order.push(id); }

(function wtStyle(){
  const s = document.createElement('style');
  s.textContent = `#wt{position:absolute;top:54px;right:10px;width:330px;max-height:calc(100% - 64px);overflow-y:auto;background:var(--panel);border:1px solid var(--line2);border-radius:10px;padding:8px 10px;z-index:5;display:none;font-size:13px}
  #wt .wt-tabs{display:flex;flex-wrap:wrap;gap:3px;margin:0 0 8px}#wt .wt-tabs button{flex:1 0 auto;background:none;border:1px solid var(--line2);border-radius:6px;color:inherit;padding:2px 7px;cursor:pointer;font:inherit;font-size:12px}
  #wt .wt-tabs button.on{background:var(--accent,#d2a85a);color:#1a1712;border-color:transparent}
  #wt .wt-row{display:flex;align-items:center;gap:6px;margin:4px 0}#wt .wt-row>span:first-child{flex:0 0 96px;opacity:.8}#wt .wt-row input:not([type=checkbox]):not([type=color]),#wt .wt-row select{flex:1;min-width:0}
  #wt .wt-key{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:4px;vertical-align:-1px}
  #wt .wt-go{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0}#wt .note{padding:3px 0}#wt h4{margin:9px 0 3px;font-size:12px;font-weight:600;opacity:.85}
  #wt .wt-list{max-height:170px;overflow-y:auto;border:1px solid var(--line2);border-radius:6px;margin:3px 0}#wt .wt-list .row{padding:2px 7px;cursor:pointer;display:flex;gap:6px;align-items:center}#wt .wt-list .row:hover{background:var(--bg3)}#wt .wt-list .row.on{background:var(--accent,#d2a85a);color:#1a1712}
  #wt .wt-list .row button{margin-left:auto;background:none;border:none;color:inherit;cursor:pointer}#wt .wt-offer{border:1px solid var(--accent,#d2a85a);border-radius:8px;padding:6px 8px;margin:0 0 8px}
  #wt-offer{position:absolute;left:50%;transform:translateX(-50%);bottom:40px;background:var(--panel);border:1px solid var(--accent,#d2a85a);border-radius:10px;padding:8px 12px;z-index:6;display:none;max-width:460px;font-size:13px}`;
  document.head.appendChild(s);
})();

function wtToggle(on){
  if (!A.outside && (on ?? !WT.on)) return toast('World tools work outside: open a worldspace from the Outside tab.', true);
  WT.on = on ?? !WT.on;
  const btn = $('#wt-btn'); if (btn) btn.classList.toggle('on', WT.on);
  let box = $('#wt');
  if (!box){ box = document.createElement('div'); box.id = 'wt'; $('#view').appendChild(box); }
  box.style.display = WT.on ? 'block' : 'none';
  if (WT.on){ if (!M.on) mapShow(true); if (typeof lsClose === 'function') lsClose(); wtDraw(); }
  M.dirty = true;
}
function wtDraw(){
  const box = $('#wt'); if (!box || !WT.on) return;
  box.innerHTML = `<div class="wt-tabs">${WT.order.map(id => `<button data-t="${id}" class="${id === WT.tab ? 'on' : ''}">${WT.tabs[id].label}</button>`).join('')}</div><div id="wt-body"></div>`;
  box.querySelector('.wt-tabs').onclick = e => { const b = e.target.closest('[data-t]'); if (b){ WT.tab = b.dataset.t; wtDraw(); M.dirty = true; } };
  WT.tabs[WT.tab].draw($('#wt-body'));
}
// over the map's own drawing and mouse, through the land shaper's hooks
{ const was = lsDraw; lsDraw = g => { was(g); if (WT.on && A.outside){ const t = WT.tabs[WT.tab]; if (t.map) t.map(g); } }; }
{ const was = lsMouse; lsMouse = (kind, e) => { if (WT.on && A.outside){ const t = WT.tabs[WT.tab]; if (t.mouse && t.mouse(kind, e)) return true; } return was(kind, e); }; }
const wxCell = e => { const [x, y] = mapWorld(e.offsetX, e.offsetY); return [Math.floor(x / 4096), Math.floor(y / 4096)]; };
function wtFillCell(g, x, y, fill, stroke){
  const [sx, sy] = mapScreen(x * 4096, (y + 1) * 4096), s = 4096 * M.z;
  if (sx > M.w || sy > M.h || sx + s < 0 || sy + s < 0) return;
  if (fill){ g.fillStyle = fill; g.fillRect(sx, sy, s, s); }
  if (stroke){ g.strokeStyle = stroke; g.lineWidth = 1.5; g.strokeRect(sx + 0.5, sy + 0.5, s - 1, s - 1); }
}
// a stroke of cells on the map: down, drag, up. Ctrl takes away.
function wtPaint(kind, e, S, apply){
  if (kind === 'down' && e.button === 0){ S.stroke = {take: e.ctrlKey, seen: new Set()}; try { M.c.setPointerCapture(e.pointerId); } catch (err) {} }
  if (!S.stroke) return kind === 'down' && e.button === 0;
  if (kind === 'down' || kind === 'move'){
    const c = wxCell(e), k = c.join(',');
    if (!S.stroke.seen.has(k)){ S.stroke.seen.add(k); apply(c, !S.stroke.take); M.dirty = true; }
    return true;
  }
  if (kind === 'up'){ const st = S.stroke; S.stroke = null; if (S.done) S.done(st); return true; }
  return false;
}

// ---------- Navmesh ----------
const WN = {marks: new Set(), status: {}, world: null, tool: true, poll: null};
const WN_COL = {made: ['rgba(61,242,122,0.26)', 'made here, up to date'], old: ['rgba(240,170,60,0.42)', 'made here, but the cell has changed since: make it again'],
                land: ['rgba(224,112,91,0.36)', 'ground changed: the game\'s mesh no longer fits'], joined: ['rgba(61,190,242,0.20)', 'the game\'s mesh, its links changed to meet yours']};
async function wnRefresh(){
  if (!OUT.world || !A.state.project) return;
  const d = await api('/api/w/nav/status?world=' + encodeURIComponent(OUT.world)).catch(() => null);
  if (!d) return;
  WN.status = d.cells; WN.world = OUT.world; M.dirty = true;
  if (d.job.running) wnPoll();
  if (WT.on && WT.tab === 'nav') wnPanelNumbers();
}
function wnPanelNumbers(){
  const box = $('#wn-key'); if (!box) return;
  const n = {}; for (const v of Object.values(WN.status)) n[v] = (n[v] || 0) + 1;
  box.innerHTML = Object.entries(WN_COL).filter(([k]) => n[k]).map(([k, [c, t]]) => `<div><span class="wt-key" style="background:${c}"></span>${n[k]} ${t}</div>`).join('') || 'Nothing made yet in this world.';
  const stale = $('#wn-stale'); if (stale) stale.disabled = !(n.old || n.land);
}
function wnDraw(box){
  const said = WN.said || '';
  box.innerHTML = `<div class="note">Characters find their way on the navmesh. Drag on the map to mark cells (Ctrl: unmark), then make them. Each joins the meshes next door, whose links are kept right in your mod.</div>
    <div class="note" id="wn-key"></div>
    <div class="note"><b>${WN.marks.size}</b> cells marked.</div>
    <div class="wt-go"><button class="btn primary" id="wn-make" ${WN.marks.size ? '' : 'disabled'}>Make for marked</button>
    <button class="btn" id="wn-stale" title="Mark every cell that's out of date or has new ground">Mark what's out of date</button>
    <button class="btn" id="wn-remove" ${WN.marks.size ? '' : 'disabled'} title="Back to the game's mesh; neighbours are put right">Remove from marked</button>
    <button class="btn" id="wn-clear" ${WN.marks.size ? '' : 'disabled'}>Clear marks</button></div>
    <div class="wt-go"><button class="btn" id="wn-edit" title="Look at the mesh in 3D and change it by hand">✎ Edit by hand in 3D</button></div>
    <div class="note" id="wn-said">${said}</div>`;
  box.querySelector('#wn-make').onclick = () => wnMake([...WN.marks].map(k => k.split(',').map(Number)));
  box.querySelector('#wn-clear').onclick = () => { WN.marks.clear(); wtDraw(); M.dirty = true; };
  box.querySelector('#wn-stale').onclick = () => { for (const [k, v] of Object.entries(WN.status)) if (v === 'old' || v === 'land') WN.marks.add(k); wtDraw(); M.dirty = true; };
  box.querySelector('#wn-remove').onclick = async () => {
    const d = await post('/api/w/nav/remove', {world: OUT.world, cells: [...WN.marks].map(k => k.split(',').map(Number))}).catch(e => { fail(e); return null; });
    if (d){ setState(d.state); WN.said = `Taken away: back to the game's. ${d.changed} meshes changed.`; WN.marks.clear(); wtDraw(); wnRefresh(); }
  };
  box.querySelector('#wn-edit').onclick = () => { if (typeof navToolOn === 'function') navToolOn(); };
  wnRefresh();
}
async function wnMake(cells){
  if (!cells.length) return;
  const d = await post('/api/w/nav/make', {world: OUT.world, cells}).catch(e => { fail(e); return null; });
  if (!d) return;
  WN.said = `Making ${cells.length} cell${cells.length > 1 ? 's' : ''}…`; if ($('#wn-said')) $('#wn-said').textContent = WN.said;
  wnPoll();
}
function wnPoll(){
  if (WN.poll) return;
  WN.poll = setInterval(async () => {
    const j = await api('/api/w/nav/job').catch(() => null);
    if (!j) return;
    if (j.running){ WN.said = `Making navmeshes: ${j.done} of ${j.total} cells (about 6 seconds each)…`; if ($('#wn-said')) $('#wn-said').textContent = WN.said; return; }
    clearInterval(WN.poll); WN.poll = null;
    if (j.ok === false){ WN.said = '<b>Could not make them:</b> ' + esc(j.error); toast(j.error, true); }
    else if (j.result){
      const r = j.result;
      if (j.state) setState(j.state);
      WN.said = `Made ${r.cells} cell${r.cells === 1 ? '' : 's'}, ${r.triangles} triangles, ${r.joined} joins.` + (r.neighbours ? ` ${r.neighbours} neighbouring cell${r.neighbours === 1 ? '' : 's'} kept in step.` : '') +
        (r.doors ? ` ${r.doors} door${r.doors === 1 ? '' : 's'} linked.` : '') + (r.doors_missed ? ` <b>${r.doors_missed} door${r.doors_missed === 1 ? '' : 's'} too far from anywhere to walk.</b>` : '') +
        (r.stubs ? ` ${r.stubs} of the game's extra meshes retired.` : '') + (r.empty.length ? ` <b>${r.empty.length} cell${r.empty.length === 1 ? ' has' : 's have'} nowhere to walk.</b>` : '');
      WN.marks.clear();
    }
    if (WT.on && WT.tab === 'nav') wtDraw();
    wnRefresh();
  }, 1000);
}
wtTab('nav', 'Navmesh', {
  draw: wnDraw,
  map(g){
    if (WN.world !== OUT.world){ WN.world = OUT.world; WN.status = {}; wnRefresh(); }
    for (const [k, v] of Object.entries(WN.status)){ const [x, y] = k.split(',').map(Number); wtFillCell(g, x, y, WN_COL[v][0]); }
    for (const k of WN.marks){ const [x, y] = k.split(',').map(Number); wtFillCell(g, x, y, 'rgba(240,205,135,0.25)', '#f0cd87'); }
  },
  mouse(kind, e){
    WN.done = () => wtDraw();
    return wtPaint(kind, e, WN, (c, on) => { const k = c.join(','); if (on) WN.marks.add(k); else WN.marks.delete(k); });
  },
});

// after shaping the land: offer a navmesh for what changed
function wnOffer(cells){
  let o = $('#wt-offer');
  if (!o){ o = document.createElement('div'); o.id = 'wt-offer'; $('#view').appendChild(o); }
  o.innerHTML = `<div>The ground changed in ${cells.length} cell${cells.length > 1 ? 's' : ''}. Characters still walk the old navmesh there.</div>
    <div class="wt-go"><button class="btn primary" id="wo-make">Make new navmeshes</button><button class="btn" id="wo-show">Show on the map</button><button class="btn" id="wo-no">Later</button></div>`;
  o.style.display = 'block';
  o.querySelector('#wo-no').onclick = () => { o.style.display = 'none'; };
  o.querySelector('#wo-show').onclick = () => { o.style.display = 'none'; for (const c of cells) WN.marks.add(c.join(',')); WT.tab = 'nav'; wtToggle(true); };
  o.querySelector('#wo-make').onclick = () => { o.style.display = 'none'; WT.tab = 'nav'; wtToggle(true); wnMake(cells); };
}
{ const was = post; post = async (path, body) => {
    const d = await was(path, body);
    if (path === '/api/shape/apply' && body.marked && body.marked.length) wnOffer(body.marked.map(c => c.slice(0, 2)));
    return d;
  }; }

// the toolbar button, beside Ground and Shape land
{ const b = document.createElement('button');
  b.className = 'btn'; b.id = 'wt-btn'; b.textContent = '🧭 World tools'; b.title = 'On the map: navmesh, regions, map markers, zones, roads';
  b.onclick = () => wtToggle();
  const g = $('#tg-outside'); if (g) g.appendChild(b); }
{ const was = lsToggle; lsToggle = () => { if (WT.on) wtToggle(false); was(); }; if ($('#ls-btn')) $('#ls-btn').onclick = lsToggle; }
