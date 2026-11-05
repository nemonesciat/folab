// ---------- Outside: worldspaces, their ground, and the cells round you loaded as you fly ----------
// Pick a worldspace, then a place on its map (its map markers). The cells within a few squares of the camera are
// loaded (ground, then the things in them) and the far ones let go, so the whole Mojave can be flown across.
// Looking only for now: the server refuses changes to outside cells.
const OUT = {worlds: [], world: null, info: null, cells: new Map(), queue: [], busy: 0, token: 0, timer: null};
const CELL = 4096, QUAD_UV = 2048 / 6;                   // (a ground texture repeats 6 times a quarter)
let LAND_R = 3, THING_R = 2;                              // (how far the ground and the things load: the View panel)
const SKY = 0xc7b9a0;

async function outsideTab(){
  if (!OUT.worlds.length) OUT.worlds = await api('/api/worlds');
  drawOutside();
}
function drawOutside(){
  const f = ($('#f-outside').value || '').toLowerCase(), list = $('#outside');
  if (!OUT.info){
    list.innerHTML = '<div class="row" data-newworld="1"><div>＋ New worldspace…<small>land of your own to shape and build on</small></div></div>' + OUT.worlds.filter(w => !f || (w.edid + ' ' + w.name).toLowerCase().includes(f)).map(w =>
      `<div class="row" data-world="${esc(w.id)}"><div>${esc(w.name || w.edid)}<small>${esc(w.edid)} · ${esc(w.plugin)}</small></div><span class="n">${w.cells}</span></div>`).join('');
    return;
  }
  const i = OUT.info;
  list.innerHTML = `<div class="row" data-back="1"><div>← All worldspaces<small>${esc(i.name || i.edid)}</small></div></div>
    <div class="row" data-middle="1"><div>The middle of it<small>${esc(i.edid)}</small></div></div>` +
    i.markers.filter(m => !f || m.name.toLowerCase().includes(f)).map((m, n) =>
      `<div class="row" data-mark="${i.markers.indexOf(m)}"><div>${esc(m.name)}<small>${Math.floor(m.p[0] / CELL)}, ${Math.floor(m.p[1] / CELL)}</small></div></div>`).join('');
}
$('#outside').addEventListener('click', async e => {
  const r = e.target.closest('.row'); if (!r) return;
  if (r.dataset.newworld) return newWorldDialog();
  if (r.dataset.world){
    OUT.info = await api('/api/world?id=' + encodeURIComponent(r.dataset.world));
    $('#f-outside').value = ''; drawOutside();
    if (!OUT.info.markers.length) goOutside(OUT.info, {p: [...OUT.info.middle, 0]});
    return;
  }
  if (r.dataset.back){ OUT.info = null; $('#f-outside').value = ''; return drawOutside(); }
  if (r.dataset.middle) return goOutside(OUT.info, {p: [...OUT.info.middle, 0]});
  if (r.dataset.mark) return goOutside(OUT.info, {p: OUT.info.markers[+r.dataset.mark].p, facing: true});
});
$('#f-outside').addEventListener('input', drawOutside);

// ---------- going outside, and back in ----------
function leaveOutside(){
  if (!OUT.world) return;
  OUT.world = null; OUT.token++;
  clearInterval(OUT.timer);
  for (const c of OUT.cells.values()) if (c.land) W.scene.remove(c.land);
  W.lands = null;
  if (typeof groundOff === 'function') groundOff();
  if (typeof farClear === 'function') farClear();
  OUT.cells.clear(); OUT.queue = [];
  W.scene.fog = null; W.scene.background = new T.Color(thView3d());
  W.outdoors = false; assignLights();
  $('#t-ground').style.display = 'none'; $('#ls-btn').style.display = 'none';
  if (typeof lsClose === 'function') lsClose();
  W.cam.near = 4; W.cam.far = 60000; W.cam.updateProjectionMatrix();
}

function goOutside(info, at){
  leaveOutside();
  page('world');
  W.token++;
  select([]);
  if (W.group) W.scene.remove(W.group);
  W.group = new T.Group(); W.scene.add(W.group);
  W.byKey = new Map(); W.hidden = new Set();
  if (W.grid){ W.scene.remove(W.grid); W.grid = null; }
  W.cell = {things: []};
  OUT.world = info.id; OUT.token++;
  OUT.since = performance.now();
  if (typeof M !== 'undefined'){ M.tiles.clear(); M.want = []; M.dirty = true; }
  W.lands = new Set();
  $('#t-ground').style.display = ''; $('#ls-btn').style.display = '';
  A.cellId = null; A.things = []; A.outside = info;
  W.scene.background = new T.Color(SKY);
  // (the distant hills reach about 40 cells: the haze thickens out to there)
  W.scene.fog = new T.Fog(SKY, CELL * 3, CELL * 40);
  W.outdoors = true; assignLights();                         // (the desert sun)
  // (outside the view reaches 40 cells: a nearest distance of 24 keeps the depth fine enough to tell water 32 under the ground)
  W.cam.near = 24; W.cam.far = CELL * 44; W.cam.updateProjectionMatrix();
  // stand above the spot (the ground's height isn't known yet: the camera settles onto it once the cell is in)
  W.cam.position.set(at.p[0], at.p[1], (at.p[2] || 0) + 200);
  W.yaw = Math.PI / 2 - (at.facing ? at.p[5] || 0 : 0); W.pitch = -0.15;
  OUT.settle = !at.p[2];
  drawPlaces(); drawObjects();
  $('#s-place').textContent = (info.name || info.edid) + ' · outside';
  OUT.timer = setInterval(outsideTick, 300);
  outsideTick();
}

// ---------- which cells to have ----------
// (on the flat map, the cells round the map's middle)
function camCell(){ const x = M.on ? M.cx : W.cam.position.x, y = M.on ? M.cy : W.cam.position.y; return [Math.floor(x / CELL), Math.floor(y / CELL)]; }
function outsideTick(){
  if (!OUT.world) return;
  const [cx, cy] = camCell();
  const want = [];
  for (let dy = -LAND_R; dy <= LAND_R; dy++) for (let dx = -LAND_R; dx <= LAND_R; dx++) want.push([cx + dx, cy + dy, Math.max(Math.abs(dx), Math.abs(dy))]);
  want.sort((a, b) => a[2] - b[2]);
  OUT.queue = want.filter(([x, y]) => !OUT.cells.has(x + ',' + y)).map(([x, y]) => [x, y]);
  for (const [k, c] of OUT.cells){
    const d = Math.max(Math.abs(c.x - cx), Math.abs(c.y - cy));
    if (d > LAND_R + 1){ cellDrop(c); OUT.cells.delete(k); continue; }
    // (things once the ground round you is in: their many mesh downloads would otherwise hold the ground back)
    if (c.data && d <= THING_R && !c.shown && !landPending(cx, cy) && !(M.on && (!cs3dThings() || M.loading || M.want.length)) && !(FAR.tiles.size && farPending() && performance.now() - OUT.since < 20000)) cellThings(c);   // (the map, zoomed out, shows none)
    if (c.shown && d > THING_R + 1) cellThingsOff(c);
  }
  while (OUT.busy < 2 && OUT.queue.length) cellLoad(OUT.queue.splice(0, 9));
  const here = OUT.cells.get(cx + ',' + cy);
  $('#s-load').textContent = `cell ${cx}, ${cy}` + (OUT.busy ? ' · loading…' : '');
  if (!(A.sel && A.sel.length)) A.cellId = here && here.data && here.data.cell || null;   // (the selected thing's cell, else the one you're over)
}

function landPending(cx, cy){
  for (let dy = -THING_R; dy <= THING_R; dy++) for (let dx = -THING_R; dx <= THING_R; dx++){
    const c = OUT.cells.get((cx + dx) + ',' + (cy + dy));
    if (!c || !c.data) return true;
  }
  return false;
}

async function cellLoad(list){
  const token = OUT.token, cells = list.map(([x, y]) => ({x, y, data: null, land: null, shown: false, keys: []}));
  for (const c of cells) OUT.cells.set(c.x + ',' + c.y, c);
  OUT.busy++;
  let got;
  try {
    got = await api(`/api/outside?world=${encodeURIComponent(OUT.world)}&xy=${list.map(xy => xy.join(',')).join(';')}`);
  } catch (e){ got = []; }
  OUT.busy--;
  if (token !== OUT.token) return;
  cells.forEach((c, n) => {
    if (OUT.cells.get(c.x + ',' + c.y) !== c) return;
    c.data = got[n] || {land: null, things: []};
    if (c.data.land){ c.land = landMesh(c.data.land, c.x, c.y); c.land.userData.cell = c; W.scene.add(c.land); W.lands.add(c.land); FAR.at = null; }
    waterRebuild(c);
    if (OUT.settle && c.data.land){
      const [cx, cy] = camCell();
      if (cx === c.x && cy === c.y){ W.cam.position.z = groundAt(c.data.land, c.x, c.y, W.cam.position.x, W.cam.position.y) + 220; OUT.settle = false; }
    }
  });
  outsideTick();
}

function cellThings(c){
  c.shown = true;
  for (const t of c.data.things){
    if (W.byKey.has(t.key)) continue;
    t.cell = c.data.cell;
    c.keys.push(t.key);
    addThing(t, W.token);
  }
  A.things = [].concat(...[...OUT.cells.values()].filter(x => x.shown).map(x => x.data.things));
  clearTimeout(OUT.objTimer); OUT.objTimer = setTimeout(drawObjects, 400);
}
function cellThingsOff(c){
  c.shown = false;
  for (const k of c.keys) dropThing(k);
  c.keys = [];
  A.things = [].concat(...[...OUT.cells.values()].filter(x => x.shown).map(x => x.data.things));
  clearTimeout(OUT.objTimer); OUT.objTimer = setTimeout(drawObjects, 400);
}
function cellDrop(c){
  if (c.shown) cellThingsOff(c);
  if (c.water){ W.scene.remove(c.water); c.water = null; }
  if (c.land){
    W.lands.delete(c.land);
    W.scene.remove(c.land);
    c.land.traverse(m => { if (m.isMesh){ m.geometry.dispose(); } });
  }
}

// ---------- the ground ----------
function groundAt(d, x, y, px, py){
  const c = Math.min(32, Math.max(0, Math.round((px - x * CELL) / 128))), r = Math.min(32, Math.max(0, Math.round((py - y * CELL) / 128)));
  return d.h[r * 33 + c];
}

const LAND_MATS = {};
function landMaterial(tex, layer){
  const k = tex + '|' + layer;
  if (LAND_MATS[k]) return LAND_MATS[k];
  const m = new T.MeshLambertMaterial({color: 0xb8a888, vertexColors: true});
  if (layer){
    // a painted layer: over the ground, showing as strongly as its points say
    m.transparent = true; m.depthWrite = false;
    m.polygonOffset = true; m.polygonOffsetFactor = -1 - layer; m.polygonOffsetUnits = -1 - layer;
  }
  texture(tex).then(t => {
    if (!t) return;
    t.wrapS = t.wrapT = T.RepeatWrapping; t.needsUpdate = true;
    m.map = t; m.color.set(0xffffff); m.needsUpdate = true;
  });
  return LAND_MATS[k] = m;
}

function landMesh(d, x, y){
  const grp = new T.Group(), x0 = x * CELL, y0 = y * CELL;
  const rgb = n => d.c ? [0, 1, 2].map(i => parseInt(d.c.substr((n * 3 + i) * 2, 2), 16) / 255) : [1, 1, 1];
  for (let q = 0; q < 4; q++){
    const qx = q & 1, qy = q >> 1, pos = [], uv = [], col = [], idx = [];
    for (let r = 0; r < 17; r++) for (let c = 0; c < 17; c++){
      const gr = qy * 16 + r, gc = qx * 16 + c, px = x0 + gc * 128, py = y0 + gr * 128;
      pos.push(px, py, d.h[gr * 33 + gc]);
      uv.push(px / QUAD_UV, py / QUAD_UV);
      col.push(...rgb(gr * 33 + gc));
    }
    for (let r = 0; r < 16; r++) for (let c = 0; c < 16; c++){
      const a = r * 17 + c, b = a + 1, e = a + 17, f = e + 1;
      idx.push(a, b, f, a, f, e);
    }
    const geo = new T.BufferGeometry();
    geo.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
    geo.setAttribute('color', new T.Float32BufferAttribute(col, 3));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    const quarter = d.q[q];
    grp.add(new T.Mesh(geo, landMaterial(quarter.base, 0)));
    quarter.layers.forEach((l, n) => {
      const g2 = new T.BufferGeometry();
      g2.setAttribute('position', geo.getAttribute('position'));
      g2.setAttribute('uv', geo.getAttribute('uv'));
      g2.setAttribute('normal', geo.getAttribute('normal'));
      const c4 = [];
      for (let v = 0; v < 289; v++) c4.push(col[v * 3], col[v * 3 + 1], col[v * 3 + 2], l.a[v]);
      g2.setAttribute('color', new T.Float32BufferAttribute(c4, 4));
      g2.setIndex(idx);
      const m = new T.Mesh(g2, landMaterial(l.tex, n + 1));
      m.renderOrder = n + 1;
      grp.add(m);
    });
  }
  grp.userData.land = true;
  return grp;
}

// ---------- after an undo, a redo or a refused change: every cell on show again as the server has it ----------
async function outsideResync(){
  const shown = [...OUT.cells.values()].filter(c => c.data && c.data.cell && (c.shown || c.data.changed_land || c.data.changed_water || OUT.touched && OUT.touched.has(c)));
  if (!shown.length) return;
  const token = OUT.token;
  const got = [];
  for (let i = 0; i < shown.length; i += 9){
    const part = shown.slice(i, i + 9);
    got.push(...await api(`/api/outside?world=${encodeURIComponent(OUT.world)}&xy=${part.map(c => c.x + ',' + c.y).join(';')}`));
  }
  if (token !== OUT.token) return;
  shown.forEach((c, n) => {
    const fresh = got[n].things, keys = new Set(fresh.map(t => t.key));
    c.data.things = fresh;
    if (got[n].water !== c.data.water){ c.data.water = got[n].water; c.data.changed_water = got[n].changed_water; waterRebuild(c); if (typeof mapLandChanged === 'function') mapLandChanged(); }
    if (got[n].land && JSON.stringify(got[n].land.h) + got[n].land.c + JSON.stringify(got[n].land.q) !==
        JSON.stringify(c.data.land.h) + c.data.land.c + JSON.stringify(c.data.land.q)){
      c.data.land = got[n].land; c.data.changed_land = got[n].changed_land; landRebuild(c);
      waterRebuild(c);
      if (typeof mapLandChanged === 'function') mapLandChanged();
      if (typeof farLandChanged === 'function') farLandChanged();
    }
    if (!c.shown) return;
    for (const k of c.keys) if (!keys.has(k)) dropThing(k);
    c.keys = [];
    for (const t of fresh){
      c.keys.push(t.key);
      const g = W.byKey.get(t.key);
      if (!g || JSON.stringify(g.userData.thing) !== JSON.stringify(t)) updateThing(t);
    }
  });
  A.things = [].concat(...[...OUT.cells.values()].filter(x => x.shown).map(x => x.data.things));
  drawObjects(); drawSelected(selThings());
}

// a thing an edit sent back: kept with its cell, so it goes when the cell does
function outsideAdopt(t){
  for (const c of OUT.cells.values()){
    if (!c.data || c.data.cell !== t.cell) continue;
    const i = c.data.things.findIndex(x => x.key === t.key);
    if (i >= 0) c.data.things[i] = t; else c.data.things.push(t);
    if (!c.keys.includes(t.key)) c.keys.push(t.key);
  }
}


// a cell's ground drawn again from its data (the Ground brush changed it)
function landRebuild(c){
  if (!c.data || !c.data.land) return;
  const old = c.land;
  c.land = landMesh(c.data.land, c.x, c.y); c.land.userData.cell = c;
  W.scene.add(c.land); W.lands.add(c.land);
  if (old){
    W.lands.delete(old); W.scene.remove(old);
    old.traverse(m => { if (m.isMesh) m.geometry.dispose(); });
  }
}


// ---------- water: one level a cell, as the game has it; drawn where it stands above the ground ----------
const WATER_MAT = new T.MeshLambertMaterial({color: 0x3f6670, transparent: true, opacity: 0.78, depthWrite: false,
                                             polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 8});   // (the ground wins a tie)
const WATER_GEO = new T.PlaneGeometry(CELL, CELL).translate(CELL / 2, CELL / 2, 0);
function waterRebuild(c){
  if (c.water){ W.scene.remove(c.water); c.water = null; }
  const d = c.data, h = d && d.water;
  if (h === null || h === undefined || !d.land || h <= Math.min(...d.land.h)) return;
  c.water = new T.Mesh(WATER_GEO, WATER_MAT);
  c.water.position.set(c.x * CELL, c.y * CELL, h);
  c.water.renderOrder = 2;
  W.scene.add(c.water);
}

// ---------- a new worldspace of your own ----------
async function newWorldDialog(){
  if (!A.state.project) return toast('Start a mod first.', true);
  if (!OUT.worlds.length) OUT.worlds = await api('/api/worlds');
  const tex = await api('/api/landtex');
  const box = document.createElement('div');
  box.className = 'owin'; box.style.cssText = 'left:50%;top:14%;transform:translateX(-50%);width:480px';
  box.innerHTML = `<div class="owtitle"><b>New worldspace</b><button class="owx">✕</button></div>
    <div style="padding:10px 14px">
      <p class="note" style="padding:0">Land of your own: a square of flat ground to shape, paint and build on with every tool outside.</p>
      <div class="fields" style="grid-template-columns:130px 1fr;padding:6px 0">
        <label>Name</label><input id="nw-name" value="My Land">
        <label>Editor ID</label><input id="nw-edid" value="MyLandWorld">
        <label>Size</label><select id="nw-size">${[4, 8, 16, 32].map(n => `<option value="${n}" ${n === 8 ? 'selected' : ''}>${n} × ${n} cells (${(n * 4096 * 0.01428).toFixed(0)} m across)</option>`).join('')}</select>
        <label>Ground height</label><input id="nw-h" type="number" value="4000">
        <label>Ground</label><select id="nw-tex">${tex.map(t => `<option value="${esc(t.key)}" ${t.edid === 'DirtBarrenWastes01' ? 'selected' : ''}>${esc(t.edid)}</option>`).join('')}</select>
        <label>Weather and water like</label><select id="nw-tpl">${OUT.worlds.map(w => `<option value="${esc(w.id)}" ${w.edid === 'WastelandNV' ? 'selected' : ''}>${esc(w.name || w.edid)}</option>`).join('')}</select>
      </div>
      <p class="note" style="padding:0">FOLab saves your mod and opens it again with the new land in it: your mod stays as it is, but Undo starts afresh from here.
        Reach it in game with a door, or the console: <code>coc</code> to a cell of it, or <code>cow &lt;editor ID&gt; 0 0</code>.</p>
    </div>
    <div class="owfoot"><button class="btn primary" id="nw-go">Make it</button><button class="btn" id="nw-cancel">Cancel</button></div>`;
  document.body.appendChild(box);
  const close = () => box.remove();
  box.querySelector('.owx').onclick = close; box.querySelector('#nw-cancel').onclick = close;
  const name = box.querySelector('#nw-name'), edid = box.querySelector('#nw-edid');
  name.oninput = () => { edid.value = (name.value.replace(/[^A-Za-z0-9]/g, '') || 'MyLand') + 'World'; };
  name.focus(); name.select();
  box.querySelector('#nw-go').onclick = async () => {
    const btn = box.querySelector('#nw-go'); btn.disabled = true; btn.textContent = 'Making it…';
    try {
      const d = await post('/api/world/new', {name: name.value.trim(), edid: edid.value.trim(), size: +box.querySelector('#nw-size').value,
                                             height: +box.querySelector('#nw-h').value, ltex: box.querySelector('#nw-tex').value,
                                             template: box.querySelector('#nw-tpl').value});
      close(); setState(d); if (typeof BW !== 'undefined') BW.types = [];
      await loadPlaces();
      OUT.worlds = await api('/api/worlds');
      const info = await api('/api/world?id=' + encodeURIComponent(d.world));
      OUT.info = info; tab('left', 'outside'); drawOutside();
      goOutside(info, {p: [...info.middle, 0]});
      toast(`${info.name || info.edid}: yours to shape. Open the map (M) and Shape land, or the Ground brush.`);
    } catch (e){ fail(e); btn.disabled = false; btn.textContent = 'Make it'; }
  };
}
