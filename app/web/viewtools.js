// ---------- The View panel, and the 3D view's smaller tools ----------
// View: which kinds of things show, kinds locked against clicks in the view, only your mod's changes, cell borders
// and the minimap, the field of view, and (outside) how far the ground and things load. Then: Scale (3) and world /
// own axes for the handles, Back (Alt+Left) to where you were, the minimap in the view's corner, and Replace every
// one here.
const VT_KINDS = [['buildings', 'Buildings & pieces'], ['scenery', 'Rocks, plants & trees'], ['doors', 'Doors'],
                  ['containers', 'Containers'], ['furniture', 'Furniture & switches'], ['lights', 'Lights'],
                  ['items', 'Items'], ['people', 'People'], ['creatures', 'Creatures']];
const VT = {kinds: {}, locked: [], onlyMine: false, borders: false, mini: true, fov: 70, landR: 3, thingR: 2, far: true};
try { Object.assign(VT, JSON.parse(localStorage.getItem('folab-view') || '{}')); } catch (e) {}
function vtSave(){ try { localStorage.setItem('folab-view', JSON.stringify(VT)); } catch (e) {} }

function vtApply(){
  if (!W.cam) return setTimeout(vtApply, 200);           // (the 3D view not made yet)
  W.show.kinds = VT.kinds; W.show.onlyMine = VT.onlyMine;
  W.locked = new Set(VT.locked);
  W.cam.fov = VT.fov; W.cam.updateProjectionMatrix();
  LAND_R = VT.landR; THING_R = Math.min(VT.thingR, VT.landR);
  FAR.R = VT.far ? 2 : -1;
  restyle();
  if (W.locked.size) select(W.sel.filter(g => !W.locked.has(thingKind(g.userData.thing))).map(g => g.userData.thing.key));
  if (typeof drawObjects === 'function') drawObjects();
  if (typeof M !== 'undefined') M.dirty = true;
}

function vtDraw(){
  const box = $('#tab-view'); if (!box) return;
  const n = {};
  for (const g of W.group ? W.group.children : []){ const k = thingKind(g.userData.thing); n[k] = (n[k] || 0) + 1; }
  box.innerHTML = `<div class="h">Show</div>
    <div class="vt-grid">${VT_KINDS.map(([k, l]) => `<label><input type="checkbox" data-vk="${k}" ${VT.kinds[k] !== false ? 'checked' : ''}> ${l} <small>${n[k] || 0}</small></label>
      <label title="Can't be clicked in the view (pick it from Objects instead)"><input type="checkbox" data-vl="${k}" ${VT.locked.includes(k) ? 'checked' : ''}> 🔒</label>`).join('')}</div>
    <label class="vt-row"><input type="checkbox" data-v="onlyMine" ${VT.onlyMine ? 'checked' : ''}> Only what your mod changed</label>
    <div class="note" style="padding:2px 0 6px">🔒 locks a kind against clicks in the view, so you don't move a wall by accident. Hiding changes only what you see, never the game.</div>
    <div class="h">The view</div>
    <label class="vt-row">Field of view <input type="range" min="40" max="110" value="${VT.fov}" data-v="fov"><b>${VT.fov}°</b></label>
    <label class="vt-row"><input type="checkbox" data-v="mini" ${VT.mini ? 'checked' : ''}> Minimap in the corner</label>
    <label class="vt-row"><input type="checkbox" data-v="borders" ${VT.borders ? 'checked' : ''}> Cell borders (outside)</label>
    <div class="h">Outside</div>
    <label class="vt-row">Ground round you <input type="range" min="1" max="5" value="${VT.landR}" data-v="landR"><b>${VT.landR * 2 + 1} × ${VT.landR * 2 + 1}</b></label>
    <label class="vt-row">Things round you <input type="range" min="1" max="4" value="${VT.thingR}" data-v="thingR"><b>${VT.thingR * 2 + 1} × ${VT.thingR * 2 + 1}</b></label>
    <label class="vt-row"><input type="checkbox" data-v="far" ${VT.far ? 'checked' : ''}> Distant hills</label>
    <div class="note" style="padding:2px 0">More cells round you show more but load slower.</div>`;
}
document.addEventListener('input', e => {
  if (!e.target.closest('#tab-view')) return;
  const t = e.target;
  if (t.dataset.vk){ VT.kinds[t.dataset.vk] = t.checked; }
  if (t.dataset.vl){ VT.locked = VT.locked.filter(k => k !== t.dataset.vl).concat(t.checked ? [t.dataset.vl] : []); }
  if (t.dataset.v){
    const k = t.dataset.v;
    VT[k] = t.type === 'checkbox' ? t.checked : +t.value;
    if (t.type === 'range') t.nextElementSibling.textContent = k === 'fov' ? VT.fov + '°' : (VT[k] * 2 + 1) + ' × ' + (VT[k] * 2 + 1);
    if (k === 'far' && !VT.far && typeof farClear === 'function') farClear();
  }
  vtSave(); vtApply();
});

// ---------- handles: Scale, world or own axes ----------
$('#t-scale').onclick = () => setTool('scale');
$('#t-space').onclick = () => {
  const own = W.gizmo.space !== 'local';
  W.gizmo.setSpace(own ? 'local' : 'world');
  $('#t-space').textContent = own ? '⟀ Own axes' : '✛ World axes';
  $('#t-space').title = own ? 'The handles follow the thing\'s own turn (click: the world\'s directions)' : 'The handles point the world\'s directions (click: the thing\'s own)';
};
const _setTool = setTool;
setTool = m => { _setTool(m); $('#t-scale').classList.toggle('on', m === 'scale'); };
addEventListener('keydown', e => {
  if (typing(e) || e.ctrlKey || e.metaKey || !$('#view').offsetParent) return;
  if (e.key === '3' && !e.altKey) setTool('scale');
  if (e.altKey && e.key === 'ArrowLeft'){ e.preventDefault(); vtBack(); }
});

// ---------- Back: where you were before the last place you opened ----------
const VT_HIST = [];
let vtGoingBack = false;
function vtHere(){
  const c = W.cam.position;
  return A.outside ? {outside: A.outside, p: [c.x, c.y, c.z], yaw: W.yaw, pitch: W.pitch}
       : A.cellId ? {place: A.cellId, p: [c.x, c.y, c.z], yaw: W.yaw, pitch: W.pitch} : null;
}
function vtPush(){ if (vtGoingBack) return; const h = vtHere(); if (h){ VT_HIST.push(h); if (VT_HIST.length > 50) VT_HIST.shift(); } }
const _openPlace = openPlace, _goOutside = goOutside;
openPlace = async (id, at) => { vtPush(); return _openPlace(id, at); };
goOutside = (info, at) => { vtPush(); return _goOutside(info, at); };
async function vtBack(){
  const h = VT_HIST.pop();
  if (!h) return toast('Nowhere to go back to.', true);
  vtGoingBack = true;
  try {
    if (h.outside){ OUT.info = h.outside; goOutside(h.outside, {p: h.p}); OUT.settle = false; }
    else { tab('left', 'places'); await openPlace(h.place); }
    W.cam.position.set(...h.p); W.yaw = h.yaw; W.pitch = h.pitch;
    toast('Back');
  } finally { vtGoingBack = false; }
}

// ---------- the minimap: the place round you from above, in a frame of its own ----------
// Drag it by its title bar anywhere over the view; let go near a corner and it docks there. ◱ makes it bigger or smaller,
// + and − zoom, ✕ hides it (the View tab brings it back). Where it is, its size and zoom are remembered. Click the map:
// go there.
const MINI_SIZES = [160, 220, 300];
const MINI_DOCK = 70;                       // (let go this near a corner: docked in it)
function miniSize(){ return MINI_SIZES[VT.miniSize ?? 1] || 220; }
function miniZoom(){ return VT.miniZoom || 1; }

function vtMiniBox(){
  let box = $('#minibox');
  if (box) return box;
  box = document.createElement('div'); box.id = 'minibox';
  box.innerHTML = `<div class="mm-bar" title="Drag to move; let go near a corner to dock it there">
      <span class="tb-grip">⋮⋮</span><b>Map</b><span class="mm-where"></span>
      <button data-mm="out" title="Show more">−</button><button data-mm="in" title="Show less, closer">+</button>
      <button data-mm="size" title="Bigger or smaller">◱</button><button data-mm="hide" title="Hide (the View tab brings it back)">✕</button></div>
    <canvas id="minimap" title="Click: go there"></canvas>`;
  $('#view').appendChild(box);
  const c = box.querySelector('canvas');
  c.addEventListener('click', e => {
    const r = c.getBoundingClientRect(), n = miniSize();
    const [x, y] = vtMiniWorld((e.clientX - r.left) / r.width * n, (e.clientY - r.top) / r.height * n);
    W.cam.position.x = x; W.cam.position.y = y;
    if (A.outside && typeof gbHeight === 'function'){ const z = gbHeight(x, y); if (z !== null) W.cam.position.z = z + 300; }
  });
  box.querySelector('.mm-bar').addEventListener('click', e => {
    const a = e.target.dataset.mm; if (!a) return;
    if (a === 'hide'){ VT.mini = false; vtSave(); box.style.display = 'none'; toast('Map hidden: the View tab brings it back'); if ($('#tab-view').classList.contains('on')) vtDraw(); }
    if (a === 'size'){ VT.miniSize = ((VT.miniSize ?? 1) + 1) % MINI_SIZES.length; vtSave(); vtMiniPlace(); }
    if (a === 'in'){ VT.miniZoom = Math.min(8, miniZoom() * 1.5); vtSave(); }
    if (a === 'out'){ VT.miniZoom = Math.max(0.15, miniZoom() / 1.5); vtSave(); }
  });
  // dragging it by its bar
  box.querySelector('.mm-bar').addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.target.closest('button')) return;
    e.preventDefault();
    const A_ = $('#view').getBoundingClientRect(), b = box.getBoundingClientRect();
    const D = {sx: e.clientX, sy: e.clientY, x: b.left - A_.left, y: b.top - A_.top};
    document.body.classList.add('tb-dragging');
    const move = ev => miniPut(D.x + ev.clientX - D.sx, D.y + ev.clientY - D.sy);
    const up = () => {
      removeEventListener('pointermove', move, true); removeEventListener('pointerup', up, true);
      document.body.classList.remove('tb-dragging');
      const V = $('#view'), x = box.offsetLeft, y = box.offsetTop, w = box.offsetWidth, h = box.offsetHeight;
      const right = x + w / 2 > V.clientWidth / 2, bottom = y + h / 2 > V.clientHeight / 2;
      const dx = right ? V.clientWidth - x - w : x, dy = bottom ? V.clientHeight - y - h : y;
      // near a corner: docked in it (snug, the top ones under the buttons); else just where it was let go
      VT.miniPos = dx < MINI_DOCK && dy < MINI_DOCK ? {dock: (bottom ? 'b' : 't') + (right ? 'r' : 'l')}
                                                   : {ax: right ? 'r' : 'l', x: Math.round(dx), ay: bottom ? 'b' : 't', y: Math.round(dy)};
      vtSave(); vtMiniPlace();
    };
    addEventListener('pointermove', move, true); addEventListener('pointerup', up, true);
  });
  new ResizeObserver(() => vtMiniPlace()).observe($('#view'));
  return box;
}
function miniPut(x, y){
  const V = $('#view'), box = $('#minibox');
  box.style.left = Math.max(4, Math.min(V.clientWidth - box.offsetWidth - 4, x)) + 'px';
  box.style.top = Math.max(4, Math.min(V.clientHeight - box.offsetHeight - 4, y)) + 'px';
}
function vtMiniPlace(){
  const box = $('#minibox'); if (!box) return;
  const n = miniSize(), c = box.querySelector('canvas');
  if (c.width !== n * 2){ c.width = c.height = n * 2; c.style.width = c.style.height = n + 'px'; }
  const V = $('#view'), p = VT.miniPos || {dock: 'bl'}, w = box.offsetWidth, h = box.offsetHeight;
  if (!V.clientWidth) return;
  if (p.dock){
    const pad = 10, top = 56;
    miniPut(p.dock[1] === 'r' ? V.clientWidth - w - pad : pad, p.dock[0] === 'b' ? V.clientHeight - h - pad : top);
  } else miniPut(p.ax === 'r' ? V.clientWidth - p.x - w : p.x, p.ay === 'b' ? V.clientHeight - p.y - h : p.y);
}

function vtMini(){
  const on = VT.mini && !(typeof M !== 'undefined' && M.on) && $('#page-world').style.display !== 'none' && (A.outside || A.cellId);
  const old = $('#minibox');
  if (!on){ if (old) old.style.display = 'none'; return; }
  const box = vtMiniBox();
  if (box.style.display !== 'block'){ box.style.display = 'block'; vtMiniPlace(); }
  const n = miniSize(), half = n / 2, c = box.querySelector('canvas');
  const css = getComputedStyle(document.documentElement), col = v => css.getPropertyValue(v).trim();
  const g = c.getContext('2d'); g.setTransform(2, 0, 0, 2, 0, 0);
  g.fillStyle = col('--bg2') || '#14110d'; g.fillRect(0, 0, n, n);
  const S = vtMiniScale() * n / 180;
  const scr = (x, y) => [half + (x - W.cam.position.x) * S, half - (y - W.cam.position.y) * S];
  box.querySelector('.mm-where').textContent = A.outside ? `${Math.floor(W.cam.position.x / 4096)}, ${Math.floor(W.cam.position.y / 4096)}` : '';
  if (A.outside && OUT.world && typeof mapTile === 'function'){
    const span = half / S, x0 = W.cam.position.x - span, x1 = W.cam.position.x + span, y0 = W.cam.position.y - span, y1 = W.cam.position.y + span;
    for (let tx = Math.floor(x0 / MAP_TILE); tx <= Math.floor(x1 / MAP_TILE); tx++)
      for (let ty = Math.floor(y0 / MAP_TILE); ty <= Math.floor(y1 / MAP_TILE); ty++){
        const img = mapTile(tx, ty); if (!img) continue;
        const [sx, sy] = scr(tx * MAP_TILE, (ty + 1) * MAP_TILE);
        g.drawImage(img, sx, sy, MAP_TILE * S + 0.5, MAP_TILE * S + 0.5);
      }
    if (OUT.info){
      g.font = '10px Inter, sans-serif';
      for (const m of OUT.info.markers){
        const [sx, sy] = scr(m.p[0], m.p[1]);
        if (sx < -40 || sy < -10 || sx > n + 40 || sy > n + 10) continue;
        g.fillStyle = col('--gold2') || '#f0cd87'; g.fillRect(sx - 2, sy - 2, 4, 4);
        g.lineWidth = 3; g.strokeStyle = col('--bg2') || '#14110d'; g.strokeText(m.name, sx + 5, sy + 3); g.fillText(m.name, sx + 5, sy + 3);
      }
    }
  } else if (W.group){
    for (const gr of W.group.children){
      if (!gr.visible || gr.userData.thing.marker || typeof mapBox !== 'function') continue;
      const b = mapBox(gr), [sx0, sy0] = scr(b.min.x, b.max.y), [sx1, sy1] = scr(b.max.x, b.min.y);
      if (sx1 < 0 || sy1 < 0 || sx0 > n || sy0 > n) continue;
      g.fillStyle = (MAP_COL[gr.userData.thing.type] || '#c8bca4') + '99';
      g.fillRect(sx0, sy0, Math.max(1, sx1 - sx0), Math.max(1, sy1 - sy0));
    }
  }
  // you: where the camera stands and which way it looks, with the field of view
  g.save(); g.translate(half, half); g.rotate(-W.yaw);
  g.globalAlpha = 0.2; g.fillStyle = col('--gold2') || '#f0cd87'; g.beginPath(); g.moveTo(0, 0);
  const fov = W.cam.fov * Math.PI / 360 * W.cam.aspect;
  g.arc(0, 0, half * 0.66, -fov, fov); g.closePath(); g.fill();
  g.globalAlpha = 1; g.beginPath(); g.moveTo(9, 0); g.lineTo(-5, 5); g.lineTo(-2, 0); g.lineTo(-5, -5); g.closePath(); g.fill();
  g.restore();
}
function vtMiniScale(){ return (A.outside ? 90 / (4096 * 2.5) : 90 / 2500) * miniZoom(); }
function vtMiniWorld(sx, sy){ const n = miniSize(), S = vtMiniScale() * n / 180; return [W.cam.position.x + (sx - n / 2) / S, W.cam.position.y - (sy - n / 2) / S]; }
setInterval(vtMini, 250);

// ---------- cell borders, outside: lines along the cells' edges, on the ground ----------
const VT_B = {lines: null, key: ''};
function vtBorders(){
  const want = VT.borders && A.outside && W.lands;
  const key = want ? [...OUT.cells.values()].filter(c => c.land).map(c => c.x + ',' + c.y).sort().join(';') : '';
  if (key === VT_B.key) return;
  VT_B.key = key;
  if (VT_B.lines){ W.scene.remove(VT_B.lines); VT_B.lines.geometry.dispose(); VT_B.lines = null; }
  if (!want) return;
  const pts = [];
  for (const c of OUT.cells.values()){
    if (!c.land || !c.data.land) continue;
    const h = c.data.land.h, x0 = c.x * 4096, y0 = c.y * 4096;
    // the south and west edges of each cell (the next cells draw the rest)
    for (let k = 0; k < 32; k++){
      pts.push(x0 + k * 128, y0, h[k] + 6, x0 + (k + 1) * 128, y0, h[k + 1] + 6);
      pts.push(x0, y0 + k * 128, h[k * 33] + 6, x0, y0 + (k + 1) * 128, h[(k + 1) * 33] + 6);
    }
  }
  const geo = new T.BufferGeometry(); geo.setAttribute('position', new T.Float32BufferAttribute(pts, 3));
  VT_B.lines = new T.LineSegments(geo, new T.LineBasicMaterial({color: 0xf0cd87, transparent: true, opacity: 0.7, depthTest: true}));
  W.scene.add(VT_B.lines);
}
setInterval(vtBorders, 700);

// ---------- Replace every one here ----------
function swapAllStart(t){ swapStart(t); A.swapping = Object.assign({}, t, {all: true});
  $('#place-note').innerHTML = `<b>Pick what to put in place of every ${esc(t.base)} here.</b> <a href="#" id="swap-cancel">Cancel</a>`;
  $('#swap-cancel').onclick = ev => { ev.preventDefault(); swapEnd(); };
}

// the panel's tab
document.querySelector('#right .tabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b && b.dataset.tab === 'view') vtDraw(); });
vtApply();
