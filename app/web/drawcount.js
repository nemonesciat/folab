// ---------- The draw count: how much the game has to draw where you are (drawcount.py, /api/draws) ----------
// A badge in the 3D view's corner, outside for the 5 x 5 cells the game keeps loaded round the camera, inside for the place.
// Waikiki's start drew 12,693 and ran at 12 fps; the game's own busiest spot draws about 2,200. Click it for what the
// draws are and the busiest spots in your mod.
const DC = {key: '', data: null, busy: false, open: false, busiest: null, timer: null};
const dcOff = () => typeof VT !== 'undefined' && VT.draws === false;

(function dcCss(){
  const c = document.createElement('style');
  c.textContent = `
  #dc-badge{position:absolute;left:10px;bottom:10px;z-index:5;font:12px var(--mono);padding:4px 9px;border-radius:8px;cursor:pointer;
    background:var(--panel);border:1px solid var(--line2);color:var(--muted);user-select:none}
  #dc-badge b{font-weight:600} #dc-badge.ok b{color:var(--green)} #dc-badge.heavy b{color:var(--amber)} #dc-badge.too.much b{color:var(--red)}
  #dc-pop{position:absolute;left:10px;bottom:42px;z-index:6;width:360px;max-height:60vh;overflow:auto;background:var(--panel);border:1px solid var(--line2);
    border-radius:10px;padding:10px 12px;font-size:12.5px;box-shadow:0 6px 24px rgba(0,0,0,.4)}
  #dc-pop h4{margin:0 0 4px;font:600 14px Oswald,'Arial Narrow',sans-serif;color:var(--gold)}
  #dc-pop table{width:100%;border-collapse:collapse;margin:6px 0} #dc-pop td{padding:2px 4px;border-bottom:1px solid var(--line)}
  #dc-pop td.n{text-align:right;font-family:var(--mono)} #dc-pop .m{color:var(--muted)}
  #dc-pop .spot{cursor:pointer} #dc-pop .spot:hover td{background:var(--sel)}`;
  document.head.appendChild(c);
})();

function dcWhere(){
  if (typeof OUT !== 'undefined' && OUT.world && A.outside){
    const x = (typeof M !== 'undefined' && M.on) ? M.cx : W.cam.position.x, y = (typeof M !== 'undefined' && M.on) ? M.cy : W.cam.position.y;
    const cx = Math.floor(x / 4096), cy = Math.floor(y / 4096);
    return {key: OUT.world + '|' + cx + ',' + cy, q: `world=${encodeURIComponent(OUT.world)}&x=${cx * 4096 + 2048}&y=${cy * 4096 + 2048}`, outside: true};
  }
  if (A.cellId && !A.outside) return {key: A.cellId, q: 'cell=' + encodeURIComponent(A.cellId), outside: false};
  return null;
}

function dcBadge(){
  let b = $('#dc-badge');
  if (!b){
    const view = $('#view');
    if (!view) return null;
    if (getComputedStyle(view).position === 'static') view.style.position = 'relative';
    b = document.createElement('div'); b.id = 'dc-badge';
    b.title = 'How much the game draws here (each shape of each thing): click for more';
    b.onclick = () => { DC.open = !DC.open; dcPop(); };
    view.appendChild(b);
  }
  return b;
}

async function dcTick(){
  const b = dcBadge();
  if (!b) return;
  const w = (A.state && A.state.project && !dcOff()) ? dcWhere() : null;
  b.style.display = w ? '' : 'none';
  if (!w){ if ($('#dc-pop')) $('#dc-pop').remove(); return; }
  const key = w.key + "|" + (A.state.project.changes || 0) + "|" + (A.state.project.undo || "");   // (and again after each change)
  if (key === DC.key || DC.busy) return;
  DC.busy = true;
  try {
    const d = await api('/api/draws?' + w.q);
    DC.key = key; DC.data = Object.assign(d, {outside: w.outside});
    b.className = d.band.replace(' ', ' ');
    b.innerHTML = `Draws: <b>${d.draws.toLocaleString()}</b>`;
    if (DC.open) dcPop();
  } catch (e) { b.innerHTML = 'Draws: ?'; }
  DC.busy = false;
}

function dcPop(){
  let p = $('#dc-pop');
  if (!DC.open || !DC.data){ if (p) p.remove(); return; }
  if (!p){ p = document.createElement('div'); p.id = 'dc-pop'; $('#view').appendChild(p); }
  const d = DC.data;
  const kinds = Object.entries(d.kinds).sort((a, b) => b[1][1] - a[1][1]);
  const bz = DC.busiest;
  p.innerHTML = `<h4>Draws ${d.outside ? 'round here' : 'in this place'}: ${d.draws.toLocaleString()}</h4>
    <div>${esc(d.words)}. ${d.outside ? `The game keeps the ${d.cells} cells round you loaded; each shape of each thing in them is one draw.` : 'Each shape of each thing here is one draw.'}
      The game's own busiest spot draws about ${d.game_busiest.toLocaleString()}; Waikiki's start drew 12,693 and ran at 12 fps.</div>
    <table>${kinds.map(([k, [n, dr]]) => `<tr><td>${esc(k)}</td><td class="n m">${n.toLocaleString()} things</td><td class="n">${dr.toLocaleString()}</td></tr>`).join('')}</table>
    <div class="m">The most drawn here:</div>
    <table>${d.top.slice(0, 8).map(([e, n, dr]) => `<tr><td>${esc(e)}</td><td class="n m">${n} × </td><td class="n">${dr.toLocaleString()}</td></tr>`).join('')}</table>
    ${d.outside ? `<div style="margin-top:6px"><button class="btn" id="dc-find"${bz && bz.running ? ' disabled' : ''}>${bz && bz.running ? `Counting… ${bz.done || 0} of ${bz.total || '?'} cells` : 'Find the busiest spots in your mod'}</button></div>
      ${bz && bz.spots ? `<table>${bz.spots.map((s, n) => `<tr class="spot" data-dcspot="${n}"><td>Cell ${s.at[0]}, ${s.at[1]}</td><td class="n">${s.draws.toLocaleString()}</td><td class="m">${s.band === 'ok' ? '' : esc(s.band)} · go</td></tr>`).join('')}</table>` : ''}
      ${bz && bz.error ? `<div class="tl-prob">${esc(bz.error)}</div>` : ''}` : ''}
    <div style="margin-top:6px"><a href="#" id="dc-hide" class="m">Hide the draw count</a> <span class="m">(the View tab shows it again)</span></div>`;
  const f = $('#dc-find');
  if (f) f.onclick = dcBusiest;
  $('#dc-hide').onclick = e => { e.preventDefault(); dcShow(false); };
  p.querySelectorAll('[data-dcspot]').forEach(r => r.onclick = async () => {
    const s = DC.busiest.spots[+r.dataset.dcspot];
    const rows = await api(`/api/goto?q=${encodeURIComponent(s.at[0] + ', ' + s.at[1])}&world=${encodeURIComponent(DC.busiest.world)}`).catch(() => []);
    if (rows.length) gotoPick(rows[0]);
  });
}

async function dcBusiest(){
  if (!OUT.world) return;
  DC.busiest = await api(`/api/draws/busiest?start=1&world=${encodeURIComponent(OUT.world)}`).catch(e => ({error: e.message}));
  dcPop();
  const poll = async () => {
    DC.busiest = await api('/api/draws/busiest').catch(e => ({error: e.message}));
    dcPop();
    if (DC.busiest.running) setTimeout(poll, 1500);
  };
  if (DC.busiest.running) setTimeout(poll, 1500);
}

function dcShow(on){
  if (typeof VT !== 'undefined'){ VT.draws = !!on; if (typeof vtSave === 'function') vtSave(); }
  const box = document.querySelector('#tab-view [data-v="draws"]');
  if (box) box.checked = !!on;
  DC.open = false; DC.key = '';
  dcPop(); dcTick();
}
document.addEventListener('input', e => { if (e.target.dataset && e.target.dataset.v === 'draws'){ DC.key = ''; DC.open = false; dcPop(); dcTick(); } });

DC.timer = setInterval(dcTick, 1500);
