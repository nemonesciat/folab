// ---------- Distant hills: the land out to the horizon, outside ----------
// Past the cells loaded in full, the ground of the map tiles round you (16 x 16 cells each, 5 x 5 of them) as one
// coarse mesh each: a height every 512 units, coloured with the flat map's picture of it (already shaded). Where the
// full ground is loaded the far mesh leaves a hole, so the two never fight; the holes follow you as you fly.
const FAR = {tiles: new Map(), R: 2, at: null, busy: 0, world: null};
const FAR_TILE = 16 * 4096, FAR_N = 65, FAR_STEP = 1024;

function farTick(){
  if (!OUT.world || !W.lands){ farClear(); return; }
  if (FAR.world !== OUT.world){ farClear(); FAR.world = OUT.world; }
  const [cx, cy] = camCell(), tx = Math.floor(cx / 16), ty = Math.floor(cy / 16);
  const b = OUT.info && OUT.info.bounds;
  for (let dx = -FAR.R; dx <= FAR.R; dx++) for (let dy = -FAR.R; dy <= FAR.R; dy++){
    const x = tx + dx, y = ty + dy, k = x + ',' + y;
    if (b && ((x + 1) * 16 <= b[0] || x * 16 > b[2] || (y + 1) * 16 <= b[1] || y * 16 > b[3])) continue;
    if (!FAR.tiles.has(k) && FAR.busy < 3) farLoad(x, y);
  }
  for (const [k, t] of FAR.tiles){
    if (Math.max(Math.abs(t.x - tx), Math.abs(t.y - ty)) > FAR.R + 1){ farDrop(t); FAR.tiles.delete(k); }
  }
  // the hole where the full ground is: rebuilt when the camera's cell changes
  const at = cx + ',' + cy;
  if (at !== FAR.at){ FAR.at = at; for (const t of FAR.tiles.values()) if (t.mesh) farHoles(t, cx, cy); }
}

// (the far pictures come before the things close by: those are hundreds of downloads)
function farPending(){ for (const t of FAR.tiles.values()) if (!t.mesh || !t.mesh.material.map) return true; return false; }

async function farLoad(x, y){
  const t = {x, y, mesh: null, d: null, world: OUT.world};
  FAR.tiles.set(x + ',' + y, t);
  FAR.busy++;
  try { t.d = await api(`/api/farland?world=${encodeURIComponent(OUT.world)}&tx=${x}&ty=${y}`); } catch (e) {}
  FAR.busy--;
  if (!t.d || FAR.tiles.get(x + ',' + y) !== t || t.world !== OUT.world) return;
  farBuild(t);
}

function farBuild(t){
  const d = t.d, pos = [], uv = [], x0 = t.x * FAR_TILE, y0 = t.y * FAR_TILE;
  // (each point twice: on the ground, and 800 lower for the skirt that hangs from the hole's edge)
  for (const drop of [24, 800]) for (let j = 0; j < FAR_N; j++) for (let i = 0; i < FAR_N; i++){
    const h = d.h[j * FAR_N + i];
    pos.push(x0 + i * FAR_STEP, y0 + j * FAR_STEP, (h === null ? -8000 : h) - drop);
    uv.push(i / (FAR_N - 1), j / (FAR_N - 1));
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  const mat = new T.MeshBasicMaterial({color: 0x6e6352, side: T.DoubleSide});     // (earth-coloured until its picture comes)
  new T.TextureLoader().load(`/api/maptile?world=${encodeURIComponent(t.world)}&tx=${t.x}&ty=${t.y}&v=${typeof M !== 'undefined' ? M.ver || 0 : 0}`,
    tex => { mat.map = tex; mat.color.set(0xffffff); mat.needsUpdate = true; });
  t.mesh = new T.Mesh(geo, mat);
  t.mesh.userData.far = true;
  W.scene.add(t.mesh);
  const [cx, cy] = camCell();
  farHoles(t, cx, cy);
}

// the triangles to draw: every square with land, except those under the full ground round the camera
function farHoles(t, cx, cy){
  const d = t.d, idx = [], L = FAR_N * FAR_N;
  const near = (i, j) => {
    const gx = t.x * 16 + Math.floor(i / 4), gy = t.y * 16 + Math.floor(j / 4);
    const c = OUT.cells.get(gx + ',' + gy);
    return Math.max(Math.abs(gx - cx), Math.abs(gy - cy)) <= LAND_R && c && c.land;
  };
  for (let j = 0; j < FAR_N - 1; j++) for (let i = 0; i < FAR_N - 1; i++){
    const a = j * FAR_N + i, b = a + 1, e = a + FAR_N, f = e + 1;
    if (d.h[a] === null || d.h[b] === null || d.h[e] === null || d.h[f] === null || near(i, j)) continue;
    idx.push(a, b, f, a, f, e);
    // a skirt down from each side that borders the hole, so no sky shows through where the two grounds meet
    const side = (p, q) => idx.push(p, q, q + L, p, q + L, p + L);
    if (i > 0 && near(i - 1, j)) side(a, e);
    if (i < FAR_N - 2 && near(i + 1, j)) side(b, f);
    if (j > 0 && near(i, j - 1)) side(a, b);
    if (j < FAR_N - 2 && near(i, j + 1)) side(e, f);
  }
  t.mesh.geometry.setIndex(idx);
  t.mesh.geometry.computeVertexNormals();
  t.mesh.geometry.computeBoundingSphere();
}

function farDrop(t){
  if (!t.mesh) return;
  W.scene.remove(t.mesh); t.mesh.geometry.dispose();
  if (t.mesh.material.map) t.mesh.material.map.dispose();
  t.mesh.material.dispose();
}
function farClear(){
  for (const t of FAR.tiles.values()) farDrop(t);
  FAR.tiles.clear(); FAR.at = null; FAR.world = null;
}
// the ground changed (a stroke, an undo): the far tiles round it are made again
function farLandChanged(){
  for (const t of FAR.tiles.values()) farDrop(t);
  FAR.tiles.clear(); FAR.at = null;
}
setInterval(() => { if (OUT.world && !W.paused) farTick(); }, 400);
