// ---------- The grid: a floor of lines you put somewhere, as Blender has, after Morrowind Workshop's ----------
// View tab > Grid. Lines at the toolbar's Grid step, faint, every fourth bright, reaching as far as the view does. It is
// a plane you put down and it stays there (a grid that hopped to whatever the view looked at was no use for lining up
// pavement, a tester's own words): first where the selection stands or where you look, then where you put it: at the
// selection's base, turned to it, or by right-clicking a floor ("Put the grid here"). Level and unturned, its lines
// fall on the world's own multiples of the step, the same as the handles' Grid snapping. Through walls: drawn over
// everything. Cell borders outside are the View tab's own switch (viewtools.js).
// Tilt (a tester building a city on hills): the grid can lie on a slope, rising by its Tilt in degrees towards the way
// its lines are turned, or be fitted to the ground where you right-click ("Fit the grid to the ground here").
const GV = {group: null, plane: null, at: null, sig: '', t: 0};
if (VT.grid === undefined) VT.grid = false;
if (VT.gridThrough === undefined) VT.gridThrough = false;

function gvStep(){ return W.gridSnap > 0 ? W.gridSnap : 128; }
function gvPlace(p, yaw, tilt){
  GV.at = {p: [p.x, p.y, p.z], yaw: yaw || 0, tilt: tilt || 0, place: gvPlaceKey()};
  GV.sig = '';
  if (!VT.grid){ VT.grid = true; vtSave(); if ($('#tab-view') && $('#tab-view').classList.contains('on')) vtDraw(); }
}
function gvPlaceKey(){ return (A.outside && A.outside.id) || A.cellId || ''; }
function gvSelBase(){
  if (!W.sel || !W.sel.length) return null;
  const b = new T.Box3();
  for (const g of W.sel){ g.updateMatrixWorld(true); b.expandByObject(g); }
  if (b.isEmpty()) return null;
  return new T.Vector3((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, b.min.z);
}
function gvToSel(turn){
  const at = gvSelBase();
  if (!at) return toast('Select something first.');
  const t = W.sel[0].userData.thing;
  gvPlace(at, turn && t && t.p ? -(t.p[5] || 0) : (GV.at && GV.at.yaw) || 0, GV.at && GV.at.tilt || 0);
  toast(turn ? 'The grid lies at its base, turned to it.' : 'The grid lies at its base. It stays there until you put it somewhere else.');
}
function gvMake(step, through, reach){
  const mk = (size, div, op) => {
    const g = new T.GridHelper(size, div, 0xf0cd87, 0xf0cd87);
    for (const m of Array.isArray(g.material) ? g.material : [g.material]){ m.depthTest = !through; m.transparent = true; m.opacity = op; m.fog = false; }
    g.renderOrder = 5; g.rotation.x = Math.PI / 2;               // (GridHelper lies in its x-z plane; up here is z)
    g.userData.noPick = true;
    return g;
  };
  const plane = new T.Group();
  plane.add(mk(step * 64, 64, 0.16));                              // (the step's lines, near you)
  plane.add(mk(step * 4 * reach, reach, 0.45));                    // (every fourth, as far as the view reaches)
  plane.userData.noPick = true;
  return plane;
}
function gvTick(){
  const want = VT.grid && W.scene && W.cam && $('#view') && $('#view').offsetParent;
  if (!want){ if (GV.group) GV.group.visible = false; return; }
  if (!GV.group){ GV.group = new T.Group(); GV.group.userData.noPick = true; }
  if (GV.group.parent !== W.scene) W.scene.add(GV.group);
  const step = gvStep(), big = step * 4;
  if (!GV.at || GV.at.place !== gvPlaceKey() || GV.at.guess){
    // (first shown in a place: where the selection stands, else the ground or floor the view looks at; a guess under
    // the camera while nothing has loaded yet, tried again until something is there)
    let at = gvSelBase(), guess = false;
    if (!at){
      const r = new T.Raycaster(); r.setFromCamera(new T.Vector2(0, 0), W.cam);
      const targets = [...(W.lands || [])].concat(W.group ? [W.group] : []);
      let h = r.intersectObjects(targets, true)[0];
      if (!h){ r.set(W.cam.position, new T.Vector3(0, 0, -1)); h = r.intersectObjects(targets, true)[0]; }
      guess = !h;
      at = h ? h.point : W.cam.position.clone().add(new T.Vector3(0, 0, -200));
    }
    if (!GV.at || GV.at.place !== gvPlaceKey() || !guess)
      GV.at = {p: [at.x, at.y, at.z], yaw: 0, tilt: 0, place: gvPlaceKey(), guess};
  }
  const reach = Math.min(400, 2 * Math.ceil((W.cam.far || 40000) / big));
  const sig = [step, VT.gridThrough, reach].join('|');
  if (GV.sig !== sig){
    GV.sig = sig;
    if (GV.plane){ GV.group.remove(GV.plane); GV.plane.traverse(o => o.geometry && o.geometry.dispose()); }
    GV.plane = gvMake(step, VT.gridThrough, reach);
    GV.group.add(GV.plane);
  }
  // (it reaches out along its own lines to under the camera, a whole number of bright lines at a time: it never moves)
  const G = GV.at, c = Math.cos(G.yaw), s = Math.sin(G.yaw), cam = W.cam.position;
  const ct = Math.cos(G.tilt || 0), st = Math.sin(G.tilt || 0);
  // (its own two directions: U along the level lines, V up the slope)
  const U = [c, s, 0], V = [-s * ct, c * ct, st];
  let px = G.p[0], py = G.p[1], pz = G.p[2];
  if (!G.yaw && !G.tilt){ px = Math.round(px / step) * step; py = Math.round(py / step) * step; }
  const d = [cam.x - px, cam.y - py, cam.z - pz];
  const du = d[0] * U[0] + d[1] * U[1], dv = d[0] * V[0] + d[1] * V[1] + d[2] * V[2];
  const ou = Math.round(du / big) * big, ov = Math.round(dv / big) * big;
  GV.plane.position.set(px + ou * U[0] + ov * V[0], py + ou * U[1] + ov * V[1], pz + ov * V[2] + 1);
  GV.plane.rotation.set(G.tilt || 0, 0, G.yaw, 'ZXY');
  GV.group.visible = true;
}
setInterval(gvTick, 120);

// the View tab: the switch, through walls, and where to put it
const _gvDraw = vtDraw;
vtDraw = () => {
  _gvDraw();
  const box = $('#tab-view'); if (!box) return;
  const row = [...box.querySelectorAll('.vt-row')].find(r => r.querySelector('[data-v="borders"]'));
  const html = `<label class="vt-row" title="Lines at the toolbar's Grid step (${gvStep()}), every fourth bright"><input type="checkbox" data-v="grid" ${VT.grid ? 'checked' : ''}> Grid <small>${gvStep()}, bright every ${gvStep() * 4}</small></label>
    <div class="vt-row gv-row" style="display:${VT.grid ? 'flex' : 'none'};gap:4px;flex-wrap:wrap;margin-left:18px">
      <button class="btn sm" data-gv="sel" title="The grid level at the selection's base">📍 At the selection</button>
      <button class="btn sm" data-gv="turn" title="The grid at the selection, its lines turned to match it">⟲ Turned to it</button>
      <label style="width:100%" title="Drawn over walls and floors"><input type="checkbox" data-v="gridThrough" ${VT.gridThrough ? 'checked' : ''}> through walls</label>
      <label title="How steeply the grid rises (0: level)">Tilt <input type="number" data-gvn="tilt" min="-60" max="60" step="1" style="width:4.5em" value="${Math.round((GV.at && GV.at.tilt || 0) * 1800 / Math.PI) / 10}">°</label>
      <label title="Which way its lines run, and so which way it rises: 0 rises north, 90 east">Facing <input type="number" data-gvn="yaw" min="-360" max="360" step="5" style="width:4.5em" value="${Math.round(-(GV.at && GV.at.yaw || 0) * 1800 / Math.PI) / 10}">°</label>
      <button class="btn sm" data-gv="level" title="Back to level and unturned">Level</button>
      <span class="note" style="width:100%">Or right-click a floor or the ground: Put the grid here, or Fit the grid to the ground here (it tilts to the slope).</span></div>`;
  if (row) row.insertAdjacentHTML('afterend', html); else box.insertAdjacentHTML('beforeend', html);
};
document.addEventListener('click', e => {
  const b = e.target.closest('[data-gv]'); if (!b) return;
  if (b.dataset.gv === 'level'){
    if (GV.at){ GV.at.tilt = 0; GV.at.yaw = 0; }
    vtDraw(); return;
  }
  gvToSel(b.dataset.gv === 'turn');
});
document.addEventListener('input', e => {
  const t = e.target;
  if (t.dataset.gvn && GV.at){
    const v = (+t.value || 0) * Math.PI / 180;
    if (t.dataset.gvn === 'tilt') GV.at.tilt = Math.max(-1.05, Math.min(1.05, v)); else GV.at.yaw = -v;
    return;
  }
  if (!t.closest('#tab-view') || (t.dataset.v !== 'grid' && t.dataset.v !== 'gridThrough')) return;
  GV.sig = '';
  const row = $('#tab-view .gv-row'); if (row) row.style.display = VT.grid ? 'flex' : 'none';
});
// the right-click menu: put it where you clicked
(() => {
  const _entries = cmEntries;
  cmEntries = (key, point) => {
    const E = _entries(key, point);
    if (point){
      const at = point instanceof T.Vector3 ? point.clone() : new T.Vector3(point.x, point.y, point.z);
      E.push({group: 'View', label: 'Put the grid here', run: () => {
        gvPlace(at, GV.at && GV.at.yaw || 0, GV.at && GV.at.tilt || 0);
        toast('The grid lies at that height. It stays there until you put it somewhere else.');
      }});
      E.push({group: 'View', label: 'Fit the grid to the ground here', run: () => gvFitGround(at)});
    }
    if (key) E.push({group: 'View', label: 'Put the grid at its base', run: () => gvToSel(false)});
    return E;
  };
})();

// the slope of the ground (or a floor) under a point: the grid tilted to it, its lines running level across it
function gvFitGround(at){
  const r = new T.Raycaster(new T.Vector3(at.x, at.y, at.z + 2000), new T.Vector3(0, 0, -1));
  const targets = [...(W.lands || [])].concat(W.group ? [W.group] : []);
  const h = r.intersectObjects(targets, true).find(x => x.face);
  if (!h) return toast('No ground there to fit the grid to.', true);
  const n = h.face.normal.clone().transformDirection(h.object.matrixWorld).normalize();
  if (n.z < 0) n.negate();
  const tilt = Math.acos(Math.min(1, n.z));
  // (it rises against the normal's lean: V, up the slope, is the normal's level part reversed)
  const yaw = tilt > 0.002 ? Math.atan2(n.x, -n.y) : (GV.at && GV.at.yaw || 0);
  gvPlace(h.point, yaw, tilt);
  toast('The grid lies on the slope there: ' + Math.round(tilt * 180 / Math.PI) + '°.');
  if ($('#tab-view') && $('#tab-view').classList.contains('on')) vtDraw();
}
