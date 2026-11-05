// ---------- The flat map: the place from above ----------
// Outside: the ground as pictures (maptiles.py), the map markers, cell lines and coordinates; close in, every thing
// loaded as its outline from above. Inside: the place's things from above. Drag empty ground to pan, the wheel zooms,
// click a thing to select it (Shift adds, Shift+drag selects with a box), drag what's selected to move it (outside its
// height follows the ground), double-click to look there in 3D, right-click for the menu.
const M = {on: false, cx: 0, cy: 0, z: 0.05, tiles: new Map(), loading: 0, want: [], drag: null, dirty: true, boxes: new Map()};
const MAP_TILE = 16 * 4096;
const MAP_COL = {STAT: '#8d8371', SCOL: '#8d8371', DOOR: '#e0a050', CONT: '#6aa0d8', NPC_: '#7fd07f', CREA: '#c8d070',
                 LIGH: '#f0d870', FURN: '#a88a6a', ACTI: '#c09ad8', TERM: '#7ad0c8', MSTT: '#9a8f7c'};

function mapInit(){
  const c = document.createElement('canvas');
  c.id = 'map2d'; c.tabIndex = 0;
  $('#view').appendChild(c);
  M.c = c; M.g = c.getContext('2d');
  new ResizeObserver(() => { mapSize(); M.dirty = true; }).observe($('#view'));
  mapSize();
  c.addEventListener('contextmenu', e => e.preventDefault());
  c.addEventListener('pointerdown', mapDown);
  c.addEventListener('pointermove', mapMove);
  c.addEventListener('pointerup', mapUp);
  c.addEventListener('dblclick', mapDbl);
  c.addEventListener('wheel', e => {
    e.preventDefault();
    const [wx, wy] = mapWorld(e.offsetX, e.offsetY), f = e.deltaY < 0 ? 1.25 : 0.8;
    M.z = Math.max(0.0006, Math.min(2, M.z * f));
    const [nx, ny] = mapWorld(e.offsetX, e.offsetY);
    M.cx += wx - nx; M.cy += wy - ny; M.dirty = true;
  }, {passive: false});
  const frame = () => { if (M.on && M.dirty){ M.dirty = false; mapDraw(); } requestAnimationFrame(frame); };
  requestAnimationFrame(frame);
}
function mapSize(){
  const r = $('#view').getBoundingClientRect(), d = window.devicePixelRatio || 1;
  M.w = r.width; M.h = r.height;
  M.c.width = Math.max(1, r.width * d); M.c.height = Math.max(1, r.height * d);
  M.c.style.width = r.width + 'px'; M.c.style.height = r.height + 'px';
  M.g.setTransform(d, 0, 0, d, 0, 0);
}
const mapScreen = (x, y) => [M.w / 2 + (x - M.cx) * M.z, M.h / 2 - (y - M.cy) * M.z];
const mapWorld = (sx, sy) => [M.cx + (sx - M.w / 2) / M.z, M.cy - (sy - M.h / 2) / M.z];

// ---------- switching ----------
function mapShow(on){
  if (!M.c) mapInit();
  M.on = on; W.paused = on;
  M.c.style.display = on ? 'block' : 'none';
  $('#t-map').classList.toggle('on', on); $('#t-3d').classList.toggle('on', !on);
  if (on){
    M.cx = W.cam.position.x; M.cy = W.cam.position.y;
    if (A.outside) M.z = Math.max(M.z, 0.002);
    else mapFit();
    M.c.focus();
  } else W.ren.domElement.focus();
  M.dirty = true;
}
function mapFit(){
  // inside: the whole place in view
  const b = new T.Box3();
  for (const g of W.group ? W.group.children : []) if (g.visible && !g.userData.thing.marker) b.expandByPoint(g.position);
  if (b.isEmpty()) return;
  M.cx = (b.min.x + b.max.x) / 2; M.cy = (b.min.y + b.max.y) / 2;
  M.z = Math.min(2, 0.85 * Math.min(M.w / Math.max(256, b.max.x - b.min.x), M.h / Math.max(256, b.max.y - b.min.y)));
}

// ---------- drawing ----------
function mapTile(tx, ty){
  const k = `${OUT.world}|${tx}|${ty}|${M.ver || 0}`;
  let t = M.tiles.get(k);
  if (!t){
    t = {img: null, k}; M.tiles.set(k, t);
    M.want.push([t, tx, ty]);
    mapFetch();
  }
  return t.img;
}
function mapFetch(){
  while (M.loading < 4 && M.want.length){
    // the tiles nearest the middle first
    M.want.sort((a, b) => Math.hypot(a[1] * MAP_TILE - M.cx, a[2] * MAP_TILE - M.cy) - Math.hypot(b[1] * MAP_TILE - M.cx, b[2] * MAP_TILE - M.cy));
    const [t, tx, ty] = M.want.shift();
    M.loading++;
    const img = new Image();
    img.onload = () => { t.img = img; M.loading--; M.dirty = true; mapFetch(); };
    img.onerror = () => { M.loading--; mapFetch(); };
    img.src = `/api/maptile?world=${encodeURIComponent(OUT.world)}&tx=${tx}&ty=${ty}&v=${M.ver || 0}`;
  }
}
// the ground changed (a stroke, an undo): its tiles are drawn afresh
function mapLandChanged(){
  M.ver = (M.ver || 0) + 1;
  for (const [k, t] of M.tiles) if (!t.img) M.tiles.delete(k);
  M.want = []; M.dirty = true;
}

function mapDraw(){
  const g = M.g;
  g.fillStyle = A.outside ? '#1a1712' : '#0e0c0a'; g.fillRect(0, 0, M.w, M.h);
  const [x0, y1] = mapWorld(0, 0), [x1, y0] = mapWorld(M.w, M.h);
  if (A.outside && OUT.world){
    const b = OUT.info && OUT.info.bounds;
    for (let tx = Math.floor(x0 / MAP_TILE); tx <= Math.floor(x1 / MAP_TILE); tx++)
      for (let ty = Math.floor(y0 / MAP_TILE); ty <= Math.floor(y1 / MAP_TILE); ty++){
        if (b && ((tx + 1) * 16 <= b[0] || tx * 16 > b[2] || (ty + 1) * 16 <= b[1] || ty * 16 > b[3])) continue;
        const img = (typeof lsTile === 'function' && lsTile(tx, ty)) || mapTile(tx, ty);   // (a land plan's preview over it)
        const [sx, sy] = mapScreen(tx * MAP_TILE, (ty + 1) * MAP_TILE), s = MAP_TILE * M.z;
        if (img){ g.imageSmoothingEnabled = s < 512; g.drawImage(img, sx, sy, s + 0.5, s + 0.5); }
      }
    // cell lines and their coordinates, close enough in
    const cs = 4096 * M.z;
    if (cs > 18){
      g.strokeStyle = 'rgba(240,205,135,0.18)'; g.lineWidth = 1; g.beginPath();
      for (let x = Math.floor(x0 / 4096) * 4096; x <= x1; x += 4096){ const [sx] = mapScreen(x, 0); g.moveTo(sx, 0); g.lineTo(sx, M.h); }
      for (let y = Math.floor(y0 / 4096) * 4096; y <= y1; y += 4096){ const [, sy] = mapScreen(0, y); g.moveTo(0, sy); g.lineTo(M.w, sy); }
      g.stroke();
      if (cs > 70){
        g.fillStyle = 'rgba(240,205,135,0.45)'; g.font = '10px Inter, sans-serif';
        for (let x = Math.floor(x0 / 4096); x <= x1 / 4096; x++) for (let y = Math.floor(y0 / 4096); y <= y1 / 4096; y++){
          const [sx, sy] = mapScreen(x * 4096, (y + 1) * 4096); g.fillText(`${x}, ${y}`, sx + 3, sy + 11);
        }
      }
    }
  }
  if (typeof lsDraw === 'function') lsDraw(g);
  if (cs3dThings()) mapThings(g);
  if (A.outside && OUT.info) mapMarkers(g);
  // where the 3D camera is, and which way it looks
  const [cx, cy] = mapScreen(W.cam.position.x, W.cam.position.y);
  g.save(); g.translate(cx, cy); g.rotate(-W.yaw);
  g.fillStyle = 'rgba(240,205,135,0.9)'; g.beginPath(); g.moveTo(12, 0); g.lineTo(-6, 6); g.lineTo(-3, 0); g.lineTo(-6, -6); g.closePath(); g.fill();
  g.restore();
  if (M.drag && M.drag.box){
    const d = M.drag; g.strokeStyle = '#d2a85a'; g.setLineDash([4, 3]);
    g.strokeRect(Math.min(d.x0, d.x), Math.min(d.y0, d.y), Math.abs(d.x - d.x0), Math.abs(d.y - d.y0)); g.setLineDash([]);
  }
  const [mx, my] = M.mouse ? mapWorld(M.mouse[0], M.mouse[1]) : [M.cx, M.cy];
  $('#s-load').textContent = (A.outside ? `cell ${Math.floor(mx / 4096)}, ${Math.floor(my / 4096)} · ` : '') + `${Math.round(mx)}, ${Math.round(my)}`;
}
function cs3dThings(){ return !A.outside || 4096 * M.z > 90; }

// a thing's outline from above: its shape's box, in the world (kept until it moves)
function mapBox(gr){
  const t = gr.userData.thing, k = t.p.join(',') + '|' + t.s + '|' + gr.children.length;
  const have = M.boxes.get(gr);
  if (have && have.k === k) return have.b;
  const b = new T.Box3().setFromObject(gr);
  if (b.isEmpty()) b.setFromCenterAndSize(gr.position, new T.Vector3(32, 32, 32));
  M.boxes.set(gr, {k, b});
  return b;
}
function mapThings(g){
  const sel = new Set(W.sel);
  const list = (W.group ? W.group.children : []).filter(gr => gr.visible && !gr.userData.thing.marker);
  // big things under small ones, so small ones can be clicked
  const items = list.map(gr => { const b = mapBox(gr); return [gr, b, (b.max.x - b.min.x) * (b.max.y - b.min.y)]; }).sort((a, b) => b[2] - a[2]);
  for (const [gr, b] of items){
    const t = gr.userData.thing;
    const [sx0, sy0] = mapScreen(b.min.x, b.max.y), [sx1, sy1] = mapScreen(b.max.x, b.min.y);
    if (sx1 < 0 || sy1 < 0 || sx0 > M.w || sy0 > M.h) continue;
    const w = Math.max(3, sx1 - sx0), h = Math.max(3, sy1 - sy0);
    if (t.actor){ g.fillStyle = MAP_COL[t.type] || '#7fd07f'; g.beginPath(); g.arc(sx0 + w / 2, sy0 + h / 2, Math.max(3, Math.min(w, h) / 2), 0, 7); g.fill(); }
    else {
      // (outside, the ground shows through: rocks and cliffs are drawn lightly, the very big ones as outlines only)
      const big = A.outside && (b.max.x - b.min.x > 2500 || b.max.y - b.min.y > 2500 || ['STAT', 'SCOL', 'MSTT'].includes(t.type));
      if (!big){
        g.fillStyle = (MAP_COL[t.type] || '#c8bca4') + (A.outside ? '55' : '99');
        g.fillRect(sx0, sy0, w, h);
      }
      g.strokeStyle = big ? 'rgba(240,225,190,0.28)' : A.outside ? 'rgba(240,225,190,0.45)' : 'rgba(0,0,0,0.45)';
      g.lineWidth = 1; g.strokeRect(sx0 + 0.5, sy0 + 0.5, w - 1, h - 1);
    }
    if (t.state){
      g.strokeStyle = t.state === 'new' ? '#6fd06f' : t.state === 'removed' ? '#e0705b' : '#e8b04a'; g.lineWidth = 2;
      g.strokeRect(sx0 - 1, sy0 - 1, w + 2, h + 2);
    }
    if (sel.has(gr)){ g.strokeStyle = '#f0cd87'; g.lineWidth = 2; g.strokeRect(sx0 - 3, sy0 - 3, w + 6, h + 6); }
  }
}
function mapMarkers(g){
  const close = 4096 * M.z;
  g.font = '12px Inter, sans-serif';
  for (const m of OUT.info.markers){
    const [sx, sy] = mapScreen(m.p[0], m.p[1]);
    if (sx < -100 || sy < -20 || sx > M.w + 100 || sy > M.h + 20) continue;
    g.fillStyle = '#f0cd87'; g.strokeStyle = '#1a1712'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(sx, sy - 6); g.lineTo(sx + 6, sy); g.lineTo(sx, sy + 6); g.lineTo(sx - 6, sy); g.closePath(); g.fill(); g.stroke();
    if (close > 4){ g.lineWidth = 3; g.strokeText(m.name, sx + 9, sy + 4); g.fillText(m.name, sx + 9, sy + 4); }
  }
}

// ---------- the mouse ----------
function mapHit(sx, sy){
  if (!cs3dThings()) return null;
  const [wx, wy] = mapWorld(sx, sy), pad = 4 / M.z;
  let best = null, area = Infinity;
  for (const gr of W.group ? W.group.children : []){
    if (!gr.visible || gr.userData.thing.marker) continue;
    const b = mapBox(gr);
    if (wx < b.min.x - pad || wx > b.max.x + pad || wy < b.min.y - pad || wy > b.max.y + pad) continue;
    const a = (b.max.x - b.min.x) * (b.max.y - b.min.y);
    if (a < area){ area = a; best = gr; }
  }
  return best;
}
function mapDown(e){
  M.c.focus();
  if (typeof lsMouse === 'function' && lsMouse('down', e)) return;
  try { M.c.setPointerCapture(e.pointerId); } catch (err) {}
  const gr = e.button === 0 ? mapHit(e.offsetX, e.offsetY) : null;
  M.drag = {b: e.button, x0: e.offsetX, y0: e.offsetY, x: e.offsetX, y: e.offsetY, moved: 0, shift: e.shiftKey, hit: gr,
            box: e.button === 0 && !gr && e.shiftKey};
  // dragging something selected moves the whole selection
  if (gr && W.sel.includes(gr) && !e.shiftKey) M.drag.move = W.sel.map(g => ({g, x: g.position.x, y: g.position.y, z: g.position.z}));
}
function mapMove(e){
  M.mouse = [e.offsetX, e.offsetY];
  if (typeof lsMouse === 'function' && lsMouse('move', e)) return;
  const d = M.drag;
  if (!d){ M.dirty = true; return; }
  const dx = e.offsetX - d.x, dy = e.offsetY - d.y;
  d.x = e.offsetX; d.y = e.offsetY; d.moved += Math.abs(dx) + Math.abs(dy);
  if (d.box){ M.dirty = true; return; }
  if (d.move && d.moved > 3){
    const ox = (d.x - d.x0) / M.z, oy = -(d.y - d.y0) / M.z;
    for (const m of d.move){
      m.g.position.x = m.x + ox; m.g.position.y = m.y + oy;
      // outside: on the ground as it is there (as high above or below it as the thing was)
      if (A.outside && typeof gbHeight === 'function'){
        const was = gbHeight(m.x, m.y), now = gbHeight(m.g.position.x, m.g.position.y);
        if (was !== null && now !== null) m.g.position.z = m.z + now - was;
      }
    }
    M.dirty = true; return;
  }
  if ((d.b === 0 && !d.hit) || d.b === 1 || d.b === 2){        // pan
    M.cx -= dx / M.z; M.cy += dy / M.z; M.dirty = true;
  }
}
function mapUp(e){
  if (typeof lsMouse === 'function' && lsMouse('up', e)){ M.drag = null; return; }
  const d = M.drag; M.drag = null; M.dirty = true;
  if (!d) return;
  if (d.box){
    if (d.moved < 4) return;
    const [ax, ay] = mapWorld(Math.min(d.x0, d.x), Math.max(d.y0, d.y)), [bx, by] = mapWorld(Math.max(d.x0, d.x), Math.min(d.y0, d.y));
    const keys = W.sel.map(g => g.userData.thing.key);
    for (const gr of W.group.children){
      if (!gr.visible || gr.userData.thing.marker) continue;
      const p = gr.position;
      if (p.x >= ax && p.x <= bx && p.y >= ay && p.y <= by && !keys.includes(gr.userData.thing.key)) keys.push(gr.userData.thing.key);
    }
    return select(keys);
  }
  if (d.move && d.moved > 3){
    // one Undo for the lot: each where it was dropped, its turn and size kept
    const moves = d.move.map(m => { const t = m.g.userData.thing; return [t, [m.g.position.x, m.g.position.y, m.g.position.z].map(v => Math.round(v * 100) / 100).concat(t.p.slice(3))]; });
    return sendMoves(moves, d.move.length > 1 ? `Move ${d.move.length}` : 'Move');
  }
  if (d.moved > 4) return;
  if (d.b === 2){
    const [wx, wy] = mapWorld(e.offsetX, e.offsetY), gr = mapHit(e.offsetX, e.offsetY);
    const key = gr ? gr.userData.thing.key : null;
    if (key && !W.sel.some(g => g.userData.thing.key === key)) select([key]);
    const z = A.outside && typeof gbHeight === 'function' ? gbHeight(wx, wy) : (W.floorZ || 0);
    return W.onContext(e, key, new T.Vector3(wx, wy, z ?? 0));
  }
  if (d.b !== 0) return;
  const key = d.hit ? d.hit.userData.thing.key : null;
  if (d.shift && key){
    const keys = W.sel.map(g => g.userData.thing.key);
    select(keys.includes(key) ? keys.filter(k => k !== key) : keys.concat(key));
  } else if (!d.shift) select(key ? [key] : []);
}
// double-click: look at that spot in 3D, from where you stand looking at it
function mapDbl(e){
  if (typeof lsMouse === 'function' && lsMouse('dbl', e)) return;
  const [wx, wy] = mapWorld(e.offsetX, e.offsetY);
  const z = A.outside && typeof gbHeight === 'function' ? gbHeight(wx, wy) : null;
  const back = 700;
  W.cam.position.set(wx - Math.cos(W.yaw) * back, wy - Math.sin(W.yaw) * back, (z ?? W.cam.position.z - 200) + 450);
  W.pitch = -0.45;
  mapShow(false);
}
// keep the map in step with what changes in the view (selection, moves from elsewhere)
setInterval(() => { if (M.on) M.dirty = true; }, 500);

$('#t-map').onclick = () => { page('world'); mapShow(true); };
$('#t-3d').onclick = () => mapShow(false);
addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k'){ e.preventDefault(); page('world'); $('#goto').focus(); $('#goto').select(); return; }
  if (typing(e) || e.ctrlKey || e.altKey || e.metaKey || !$('#view').offsetParent) return;
  if (e.key === 'm' || e.key === 'M') mapShow(!M.on);
});

// ---------- Go to a place: a name, a map marker, a cell's coordinates or a spot ----------
const GO = {rows: [], at: 0, timer: null};
$('#goto').addEventListener('input', () => { clearTimeout(GO.timer); GO.timer = setTimeout(gotoSearch, 180); });
$('#goto').addEventListener('keydown', e => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp'){ e.preventDefault(); GO.at = Math.max(0, Math.min(GO.rows.length - 1, GO.at + (e.key === 'ArrowDown' ? 1 : -1))); gotoDraw(); }
  if (e.key === 'Enter' && GO.rows.length){ e.preventDefault(); gotoPick(GO.rows[GO.at]); }
  if (e.key === 'Escape'){ $('#goto-list').style.display = 'none'; e.target.blur(); }
});
$('#goto').addEventListener('blur', () => setTimeout(() => { $('#goto-list').style.display = 'none'; }, 200));
$('#goto-list').addEventListener('mousedown', e => { const r = e.target.closest('[data-n]'); if (r){ e.preventDefault(); gotoPick(GO.rows[+r.dataset.n]); } });

async function gotoSearch(){
  const q = $('#goto').value.trim();
  if (!q){ $('#goto-list').style.display = 'none'; return; }
  GO.rows = await api(`/api/goto?q=${encodeURIComponent(q)}${OUT.world ? '&world=' + encodeURIComponent(OUT.world) : ''}`);
  GO.at = 0; gotoDraw();
}
function gotoDraw(){
  const box = $('#goto-list');
  const what = r => r.kind === 'place' ? 'inside · ' + r.edid : r.kind === 'marker' ? 'on the map · ' + r.world_name : r.kind === 'cell' ? 'a cell outside' : 'a spot outside';
  box.innerHTML = GO.rows.length ? GO.rows.map((r, n) => `<div class="row${n === GO.at ? ' on' : ''}" data-n="${n}"><div>${esc(r.name)}<small>${esc(what(r))}</small></div></div>`).join('')
    : '<div class="note" style="padding:8px 12px">Nothing by that name. A cell: -18, 0 · a spot: x y z</div>';
  box.style.display = 'block';
}
async function gotoPick(r){
  $('#goto-list').style.display = 'none'; $('#goto').blur();
  page('world');
  if (r.kind === 'place'){ tab('left', 'places'); return openPlace(r.id); }
  const info = OUT.info && OUT.info.id === r.world ? OUT.info : await api('/api/world?id=' + encodeURIComponent(r.world));
  OUT.info = info;
  tab('left', 'outside'); if (!OUT.worlds.length) await outsideTab(); else drawOutside();
  goOutside(info, {p: r.p, facing: r.kind === 'marker'});
  if (M.on){ M.cx = r.p[0]; M.cy = r.p[1]; M.z = Math.max(M.z, 0.03); M.dirty = true; }
}
