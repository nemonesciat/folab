// ---------- Distant buildings: what stands far off, outside ----------
// Past the cells whose things are loaded in full, every placed thing the game ships a far model for is drawn with that
// model (the game's own stand-in for it at a distance), by map tile: the tile you're over and the ones round it. A thing
// in a cell that is shown in full isn't drawn twice: its far copy hides while the real one is there. One draw per model
// and tile, however many of it stand there.
const FT = {tiles: new Map(), R: 1, busy: 0, world: null, sig: '', on: true};
const FT_TILE = 16;

function ftTick(){
  if (!OUT.world || !W.lands || !FT.on){ ftClear(); return; }
  if (FT.world !== OUT.world){ ftClear(); FT.world = OUT.world; }
  const [cx, cy] = camCell(), tx = Math.floor(cx / FT_TILE), ty = Math.floor(cy / FT_TILE);
  const b = OUT.info && OUT.info.bounds;
  for (let dx = -FT.R; dx <= FT.R; dx++) for (let dy = -FT.R; dy <= FT.R; dy++){
    const x = tx + dx, y = ty + dy, k = x + ',' + y;
    if (b && ((x + 1) * FT_TILE <= b[0] || x * FT_TILE > b[2] || (y + 1) * FT_TILE <= b[1] || y * FT_TILE > b[3])) continue;
    // (after the ground round you and the far hills: those are what you steer by)
    if (!FT.tiles.has(k) && FT.busy < 1 && !landPending(cx, cy)) ftLoad(x, y);
  }
  for (const [k, t] of FT.tiles){
    if (Math.max(Math.abs(t.x - tx), Math.abs(t.y - ty)) > FT.R + 1){ ftDrop(t); FT.tiles.delete(k); }
  }
  // which cells show their things in full has changed: the far copies there hide, the others come back
  let sig = '';
  for (const c of OUT.cells.values()) if (c.shown) sig += c.x + ',' + c.y + ';';
  if (sig !== FT.sig){ FT.sig = sig; for (const t of FT.tiles.values()) ftShow(t); }
}

async function ftLoad(x, y){
  const t = {x, y, world: OUT.world, sets: [], ready: false};
  FT.tiles.set(x + ',' + y, t);
  FT.busy++;
  let d = null;
  try { d = await api(`/api/farthings?world=${encodeURIComponent(OUT.world)}&tx=${x}&ty=${y}`); } catch (e) {}
  FT.busy--;
  const mine = () => FT.tiles.get(x + ',' + y) === t && t.world === OUT.world;
  if (!d || !mine()) return;
  const by = d.models.map(() => []);
  for (const th of d.things) by[th[0]].push(th);
  for (let m = 0; m < d.models.length; m++){
    if (!by[m].length) continue;
    const parts = await model(d.models[m]);
    if (!mine()) return;
    for (const [geo, mat, blend] of parts){
      const im = new T.InstancedMesh(geo, mat, by[m].length);
      im.userData.far = true;
      im.frustumCulled = false;             // (its bounds are the model's alone, not where the copies stand)
      im.count = 0;
      if (blend) im.renderOrder = 1;
      W.scene.add(im);
      t.sets.push({im, things: by[m]});
    }
  }
  t.ready = true;
  ftShow(t);
}

const FT_M = new T.Matrix4(), FT_Q = new T.Quaternion(), FT_E = new T.Euler(), FT_P = new T.Vector3(), FT_S = new T.Vector3();
function ftShow(t){
  if (!t.ready) return;
  for (const s of t.sets){
    let n = 0;
    for (const th of s.things){
      const c = OUT.cells.get(Math.floor(th[1] / CELL) + ',' + Math.floor(th[2] / CELL));
      if (c && c.shown) continue;
      FT_E.set(0, 0, -th[4]);               // (the game turns the other way)
      FT_Q.setFromEuler(FT_E);
      FT_P.set(th[1], th[2], th[3]); FT_S.setScalar(th[5]);
      s.im.setMatrixAt(n++, FT_M.compose(FT_P, FT_Q, FT_S));
    }
    s.im.count = n;
    s.im.instanceMatrix.needsUpdate = true;
  }
}

function ftDrop(t){
  for (const s of t.sets){ W.scene.remove(s.im); s.im.dispose(); }     // (the model's shapes are shared: kept)
  t.sets = [];
}
function ftClear(){
  for (const t of FT.tiles.values()) ftDrop(t);
  FT.tiles.clear(); FT.world = null; FT.sig = '';
}
// what stands there changed (a thing put down, moved, an undo): the tiles are asked for again
function farThingsChanged(){
  for (const t of FT.tiles.values()) ftDrop(t);
  FT.tiles.clear(); FT.sig = '';
}
setInterval(() => { if (OUT.world && !W.paused) ftTick(); else if (!OUT.world && FT.tiles.size) ftClear(); }, 500);
