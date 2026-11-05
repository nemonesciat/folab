// ---------- Land shaping: draw shapes on the flat map, see the land they make, then make it ----------
// Shapes (ridge, valley, plateau, flatten, hill, crater, mesa) mark the cells they reach, towns and busy places left
// out unless you say so; ✚ Mark adds or (Ctrl) takes away cells by hand. The map shows the plan's land half a second
// after any change; nothing in the mod changes until Shape the land, which is one Undo. Only marked cells change, and
// the shapes fade out toward their edge, so the land still meets every unmarked cell exactly.
const LS = {on: false, plan: null, marks: [], unmarks: [], settled: false, sel: -1, tool: null, draw: null, marked: [],
            skipped: [], preview: null, imgs: new Map(), timer: null, busy: false, drag: null, world: null};
const LS_KINDS = {
  ridge: {label: '⛰ Ridge', how: 'Click along the crest; double-click to finish.', line: true,
          fields: [['height', 'Crest height', 200, 6000, 100, 1500], ['width', 'Width to its foot', 500, 10000, 100, 2500], ['sharp', 'Sharp', 0, 1, 0.05, 0.4]]},
  valley: {label: '⌄ Valley', how: 'Click along the floor; double-click to finish.', line: true,
           fields: [['depth', 'Depth', 100, 4000, 50, 600], ['width', 'Width', 500, 10000, 100, 2500], ['v', 'U to V', 0, 1, 0.05, 0.3]]},
  plateau: {label: '▭ Plateau', how: 'Click round the top; double-click (or the first point) to close.', ring: true,
            fields: [['height', 'Top above its ground', -3000, 4000, 50, 800], ['cliff', 'Cliff', 64, 3000, 32, 256], ['terraces', 'Terraces', 0, 8, 1, 0]]},
  flatten: {label: '▬ Flatten', how: 'Click round the area; double-click (or the first point) to close.', ring: true,
            fields: [['fade', 'Fade in over', 64, 3000, 32, 512]]},
  hill: {label: '◉ Hill', how: 'One click where it stands.', point: true,
         fields: [['height', 'Height', -3000, 6000, 50, 1200], ['radius', 'Radius', 300, 12000, 100, 2500]]},
  crater: {label: '◎ Crater', how: 'One click at its middle.', point: true,
           fields: [['height', 'Depth', 100, 4000, 50, 800], ['radius', 'Radius', 300, 12000, 100, 2500]]},
  mesa: {label: '▣ Mesa', how: 'One click where it stands.', point: true,
         fields: [['height', 'Height', 100, 5000, 50, 1000], ['radius', 'Radius', 300, 12000, 100, 2000]]},
  lake: {label: '◍ Lake', how: 'Click round the shore; double-click (or the first point) to close. Its water stands just under the lowest point of its shore.', ring: true,
         fields: [['depth', 'Depth', 100, 3000, 50, 500], ['bank', 'Bank', 64, 3000, 32, 512], ['below', 'Water under the shore by', 0, 400, 8, 32]]},
  river: {label: '〰 River', how: 'Click from the source down to the mouth; double-click to finish. It runs downhill all the way; each cell gets one water level, so it steps down cell by cell.', line: true,
          fields: [['depth', 'Depth', 100, 2000, 25, 300], ['width', 'Width', 200, 6000, 50, 800]]},
};
const LS_PLAN = () => ({shapes: [], rough: 0.3, fade: 1024, seed: 1, hold: true, margin: 512, from_game: true, paint: true});

function lsLoad(){
  if (LS.world === OUT.world) return;
  LS.world = OUT.world;
  try { const d = JSON.parse(localStorage.getItem('folab-shape-' + OUT.world) || 'null');
        LS.plan = d ? d.plan : LS_PLAN(); LS.marks = d ? d.marks || [] : []; LS.unmarks = d ? d.unmarks || [] : []; }
  catch (e){ LS.plan = LS_PLAN(); LS.marks = []; LS.unmarks = []; }
  LS.sel = -1; LS.preview = null; LS.marked = []; LS.skipped = [];
}
function lsStore(){ try { localStorage.setItem('folab-shape-' + OUT.world, JSON.stringify({plan: LS.plan, marks: LS.marks, unmarks: LS.unmarks})); } catch (e) {} }

function lsToggle(){
  if (!A.outside) return toast('Land shaping works outside: open a worldspace first.', true);
  if (!M.on) mapShow(true);
  LS.on = !LS.on;
  $('#ls-btn').classList.toggle('on', LS.on);
  let box = $('#ls');
  if (!box){ box = document.createElement('div'); box.id = 'ls'; $('#view').appendChild(box); }
  box.style.display = LS.on ? 'block' : 'none';
  if (LS.on){ lsLoad(); lsPanel(); lsChanged(); }
  else { LS.tool = null; LS.draw = null; }
  M.dirty = true;
}

function lsClose(){
  if (!LS.on) return;
  LS.on = false; LS.tool = null; LS.draw = null;
  $('#ls-btn').classList.remove('on');
  if ($('#ls')) $('#ls').style.display = 'none';
  if (typeof M !== 'undefined') M.dirty = true;
}

// ---------- the panel ----------
function lsPanel(){
  const box = $('#ls'); if (!box || !LS.on) return;
  const P = LS.plan, s = P.shapes[LS.sel];
  const field = (o, [k, l, lo, hi, step, def], attr = 'lf') => `<label class="gb-row">${l} <input type="range" min="${lo}" max="${hi}" step="${step}" value="${o[k] ?? def}" data-${attr}="${k}"><b>${o[k] ?? def}</b></label>`;
  box.innerHTML = `<div class="gb-h"><b>Shape the land</b><button class="btn" data-ls="close">✕</button></div>
    <div class="gb-tools">${Object.entries(LS_KINDS).map(([k, d]) => `<button class="btn${LS.tool === k ? ' on' : ''}" data-draw="${k}">${d.label}</button>`).join('')}
      <button class="btn${LS.tool === 'mark' ? ' on' : ''}" data-draw="mark" title="Click or drag over cells to mark them; Ctrl: unmark">✚ Mark</button></div>
    ${LS.tool && LS.tool !== 'mark' ? `<div class="note" style="padding:2px 0">${LS_KINDS[LS.tool].how} Backspace takes back a point, Esc stops.</div>` : ''}
    ${LS.tool === 'mark' ? '<div class="note" style="padding:2px 0">Click or drag over cells to mark them; Ctrl unmarks. Esc stops.</div>' : ''}
    <div class="h" style="padding-left:0">Shapes · ${P.shapes.length}</div>
    <div class="list gb-list" style="max-height:140px">${P.shapes.map((sh, i) => `<div class="row${i === LS.sel ? ' on' : ''}" data-shape="${i}">
      <div><input type="checkbox" data-on="${i}" ${sh.on !== false ? 'checked' : ''}> ${LS_KINDS[sh.kind].label} <small>${sh.pts.length} point${sh.pts.length === 1 ? '' : 's'}</small></div>
      <span><button class="btn" data-up="${i}" title="Earlier: the ones after act on what it made">↑</button><button class="btn" data-del="${i}">✕</button></span></div>`).join('') || '<div class="note">Pick a shape above and draw it on the map.</div>'}</div>
    ${s ? `<div class="h" style="padding-left:0">${LS_KINDS[s.kind].label}</div>${LS_KINDS[s.kind].fields.map(f => field(s, f)).join('')}
      <div class="note" style="padding:0">Drag its points on the map to move them.</div>` : ''}
    <div class="h" style="padding-left:0">The land</div>
    ${field(P, ['rough', 'Rolling ground', 0, 1, 0.05, 0.3], 'lpf')}
    ${field(P, ['fade', 'Fades in from the edge over', 256, 8192, 128, 1024], 'lpf')}
    <label class="gb-row"><input type="checkbox" data-lp="hold" ${P.hold ? 'checked' : ''}> Keep the ground under buildings and doors</label>
    ${P.hold ? field(P, ['margin', '… fading back over', 64, 2048, 32, 512], 'lpf') : ''}
    <label class="gb-row"><input type="checkbox" data-lp="paint" ${P.paint !== false ? 'checked' : ''}> Paint the new ground by its slopes, as the land round it is painted (roads kept)</label>
    <label class="gb-row"><input type="checkbox" data-lp="from_game" ${P.from_game ? 'checked' : ''}> Start from the game's land (shaping again leaves no trace of the last time)</label>
    <label class="gb-row"><input type="checkbox" data-lp="settled" ${LS.settled ? 'checked' : ''}> Shape towns and busy places too</label>
    <div class="note" style="padding:2px 0">${LS.marked.length} cell${LS.marked.length === 1 ? '' : 's'} marked${LS.skipped.length ? ` · ${LS.skipped.length} busy place${LS.skipped.length === 1 ? '' : 's'} left out (red)` : ''}${LS.busy ? ' · working out the land…' : LS.preview ? ' · the map shows the plan' : ''}</div>
    <div class="gb-tools" style="grid-template-columns:1fr 1fr 1fr"><button class="btn" data-ls="reroll" title="The same shapes with other rolling ground">🎲 Re-roll</button>
      <button class="btn" data-ls="clear">Clear all</button><button class="btn primary" data-ls="apply" ${LS.marked.length && !LS.busy ? '' : 'disabled'}>Shape the land</button></div>
    <div class="note" style="padding:2px 0">Shape the land writes it into your mod as one Undo; things on the ground move with it. The game's distant view of it updates once you run xLODGen.</div>`;
}
document.addEventListener('click', async e => {
  if (!e.target.closest('#ls')) return;
  const t = e.target, P = LS.plan;
  const d = t.closest('[data-draw]');
  if (d){ LS.tool = LS.tool === d.dataset.draw ? null : d.dataset.draw; LS.draw = null; lsPanel(); M.dirty = true; return; }
  if (t.dataset.up !== undefined){ const i = +t.dataset.up; if (i > 0){ [P.shapes[i - 1], P.shapes[i]] = [P.shapes[i], P.shapes[i - 1]]; LS.sel = i - 1; lsChanged(); } return; }
  if (t.dataset.del !== undefined){ P.shapes.splice(+t.dataset.del, 1); LS.sel = -1; lsChanged(); return; }
  const row = t.closest('[data-shape]');
  if (row && t.type !== 'checkbox'){ LS.sel = +row.dataset.shape; lsPanel(); M.dirty = true; return; }
  const a = t.dataset.ls;
  if (a === 'close') return lsToggle();
  if (a === 'reroll'){ P.seed = (P.seed || 1) + 1; return lsChanged(); }
  if (a === 'clear'){ if (!confirm('Clear every shape and mark?')) return; LS.plan = LS_PLAN(); LS.marks = []; LS.unmarks = []; LS.sel = -1; return lsChanged(); }
  if (a === 'apply') return lsApply();
});
document.addEventListener('input', e => {
  if (!e.target.closest('#ls')) return;
  const t = e.target, P = LS.plan;
  if (t.dataset.lf || t.dataset.lpf){
    const o = t.dataset.lpf ? P : P.shapes[LS.sel], k = t.dataset.lpf || t.dataset.lf;
    o[k] = +t.value; t.nextElementSibling.textContent = t.value;
    lsChanged(false);
  }
  if (t.dataset.on !== undefined){ P.shapes[+t.dataset.on].on = t.checked; lsChanged(); }
  if (t.dataset.lp === 'settled'){ LS.settled = t.checked; lsChanged(); }
  else if (t.dataset.lp){ P[t.dataset.lp] = t.checked; lsChanged(); }
});

// ---------- working it out ----------
function lsChanged(redraw = true){
  lsStore();
  if (redraw) lsPanel();
  M.dirty = true;
  clearTimeout(LS.timer);
  LS.timer = setTimeout(lsPreview, 600);
}
async function lsPreview(){
  const body = {world: OUT.world, plan: LS.plan, marks: LS.marks, unmarks: LS.unmarks, settled: LS.settled};
  const token = LS.token = (LS.token || 0) + 1;
  try {
    const c = await post('/api/shape/cells', body);
    if (token !== LS.token) return;
    LS.marked = c.marked; LS.skipped = c.settled;
    if (!LS.marked.length){ LS.preview = null; lsPanel(); M.dirty = true; return; }
    LS.busy = true; lsPanel();
    const p = await post('/api/shape/preview', {world: OUT.world, plan: LS.plan, marked: LS.marked});
    if (token !== LS.token) return;
    LS.preview = {key: p.key, tiles: new Set(p.tiles.map(t => t.join(',')))};
    LS.imgs.clear();
  } catch (err){ fail(err); }
  LS.busy = false; lsPanel(); M.dirty = true;
}
// the plan's picture of a map tile, in place of the land as it is
function lsTile(tx, ty){
  if (!LS.on || !LS.preview || !LS.preview.tiles.has(tx + ',' + ty)) return null;
  const k = LS.preview.key + '|' + tx + ',' + ty;
  if (!LS.imgs.has(k)){
    const img = new Image(); LS.imgs.set(k, null);
    img.onload = () => { LS.imgs.set(k, img); M.dirty = true; };
    img.src = `/api/shape/tile?key=${LS.preview.key}&tx=${tx}&ty=${ty}`;
  }
  return LS.imgs.get(k) || null;
}
async function lsApply(){
  if (!A.state.project) return toast('Start a mod first.', true);
  LS.busy = true; lsPanel();
  toast(`Shaping ${LS.marked.length} cells…`);
  try {
    const d = await post('/api/shape/apply', {world: OUT.world, plan: LS.plan, marked: LS.marked, follow: true});
    setState(d.state);
    for (const c of OUT.cells.values()) (OUT.touched = OUT.touched || new Set()).add(c);
    await outsideResync();
    mapLandChanged(); if (typeof farLandChanged === 'function') farLandChanged();
    LS.preview = null;
    toast(`Shaped ${d.cells} cells (one Undo)`);
  } catch (err){ fail(err); }
  LS.busy = false; lsPanel(); M.dirty = true;
}

// ---------- on the map ----------
function lsDraw(g){
  if (!LS.on) return;
  const cs = 4096 * M.z;
  const rect = (k, fill) => { const [sx, sy] = mapScreen(k[0] * 4096, (k[1] + 1) * 4096); g.fillStyle = fill; g.fillRect(sx, sy, cs, cs); };
  for (const k of LS.marked) rect(k, 'rgba(240,205,135,0.10)');
  for (const k of LS.skipped) rect(k, 'rgba(224,112,91,0.28)');
  g.strokeStyle = 'rgba(240,205,135,0.5)'; g.lineWidth = 1;
  for (const k of LS.marked){ const [sx, sy] = mapScreen(k[0] * 4096, (k[1] + 1) * 4096); g.strokeRect(sx + 0.5, sy + 0.5, cs - 1, cs - 1); }
  const shapes = LS.plan.shapes.concat(LS.draw ? [LS.draw] : []);
  shapes.forEach((s, i) => {
    const sel = i === LS.sel || s === LS.draw, d = LS_KINDS[s.kind], pts = s.pts.map(p => mapScreen(p[0], p[1]));
    g.globalAlpha = s.on === false ? 0.35 : 1;
    // its reach, faint
    const r = (s.width || s.radius || 0) * M.z;
    if (r && (d.line || d.point)){
      g.strokeStyle = 'rgba(240,205,135,0.25)'; g.lineWidth = Math.max(1, r * 2); g.lineCap = 'round'; g.lineJoin = 'round';
      if (d.point){ g.lineWidth = 1.5; g.beginPath(); g.arc(pts[0][0], pts[0][1], r, 0, 7); g.stroke(); }
      else if (pts.length > 1){ g.beginPath(); pts.forEach((p, j) => j ? g.lineTo(...p) : g.moveTo(...p)); g.stroke(); }
    }
    g.strokeStyle = sel ? '#f0cd87' : '#d2a85a'; g.lineWidth = sel ? 2.5 : 1.5;
    g.beginPath(); pts.forEach((p, j) => j ? g.lineTo(...p) : g.moveTo(...p));
    if (d.ring && s !== LS.draw) g.closePath();
    g.stroke();
    if (sel || s === LS.draw) for (const p of pts){ g.fillStyle = '#f0cd87'; g.fillRect(p[0] - 4, p[1] - 4, 8, 8); }
    g.globalAlpha = 1;
  });
}

// the mouse on the map while the panel is open: drawing, dragging points, marking. true when it was ours.
function lsMouse(type, e){
  if (!LS.on) return false;
  const [x, y] = mapWorld(e.offsetX, e.offsetY);
  const P = LS.plan;
  if (LS.tool === 'mark'){
    if (type === 'down' && e.button === 0){ LS.drag = {mark: !e.ctrlKey}; lsMarkAt(x, y); return true; }
    if (type === 'move' && LS.drag && LS.drag.mark !== undefined){ lsMarkAt(x, y); return true; }
    if (type === 'up' && LS.drag){ LS.drag = null; lsChanged(); return true; }
    return false;
  }
  if (LS.tool && e.button === 0){
    const d = LS_KINDS[LS.tool];
    if (type === 'down'){
      if (d.point){ P.shapes.push(lsNewShape(LS.tool, [[x, y]])); LS.sel = P.shapes.length - 1; LS.tool = null; lsChanged(); return true; }
      if (!LS.draw) LS.draw = lsNewShape(LS.tool, []);
      const first = LS.draw.pts[0];
      if (d.ring && LS.draw.pts.length > 2 && first){
        const [fx, fy] = mapScreen(first[0], first[1]);
        if (Math.hypot(fx - e.offsetX, fy - e.offsetY) < 10){ lsFinish(); return true; }
      }
      LS.draw.pts.push([x, y]); M.dirty = true; return true;
    }
    if (type === 'dbl'){ lsFinish(); return true; }
    return type === 'up' || type === 'move' ? !!LS.draw && type === 'up' : false;
  }
  // no tool: drag a point of the picked shape
  const s = P.shapes[LS.sel];
  if (type === 'down' && e.button === 0 && s){
    const i = s.pts.findIndex(p => { const [sx, sy] = mapScreen(p[0], p[1]); return Math.hypot(sx - e.offsetX, sy - e.offsetY) < 9; });
    if (i >= 0){ LS.drag = {pt: i}; return true; }
  }
  if (type === 'move' && LS.drag && LS.drag.pt !== undefined){ s.pts[LS.drag.pt] = [x, y]; M.dirty = true; return true; }
  if (type === 'up' && LS.drag && LS.drag.pt !== undefined){ LS.drag = null; lsChanged(); return true; }
  return false;
}
function lsNewShape(kind, pts){
  const s = {kind, pts, on: true};
  for (const [k, , , , , def] of LS_KINDS[kind].fields) s[k] = def;
  return s;
}
function lsFinish(){
  const s = LS.draw; LS.draw = null;
  const d = LS_KINDS[s.kind];
  // (a double-click adds its point twice: once is enough)
  s.pts = s.pts.filter((p, i) => !i || Math.hypot(p[0] - s.pts[i - 1][0], p[1] - s.pts[i - 1][1]) > 1);
  if (s.pts.length < (d.ring ? 3 : 2)){ toast(d.ring ? 'A ring needs three points at least.' : 'A line needs two points at least.', true); M.dirty = true; return; }
  LS.plan.shapes.push(s); LS.sel = LS.plan.shapes.length - 1; LS.tool = null;
  lsChanged();
}
function lsMarkAt(x, y){
  const k = [Math.floor(x / 4096), Math.floor(y / 4096)], same = m => m[0] === k[0] && m[1] === k[1];
  if (LS.drag.mark){ if (!LS.marks.some(same)) LS.marks.push(k); LS.unmarks = LS.unmarks.filter(m => !same(m)); }
  else { if (!LS.unmarks.some(same)) LS.unmarks.push(k); LS.marks = LS.marks.filter(m => !same(m)); }
  if (LS.drag.mark && !LS.marked.some(same)) LS.marked.push(k);
  if (!LS.drag.mark) LS.marked = LS.marked.filter(m => !same(m));
  M.dirty = true;
}
addEventListener('keydown', e => {
  if (!LS.on || typing(e)) return;
  if (e.key === 'Escape' && (LS.tool || LS.draw)){ e.stopPropagation(); LS.tool = null; LS.draw = null; lsPanel(); M.dirty = true; }
  if (e.key === 'Backspace' && LS.draw && LS.draw.pts.length){ e.preventDefault(); LS.draw.pts.pop(); M.dirty = true; }
}, true);
$('#ls-btn').onclick = lsToggle;
