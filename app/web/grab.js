// ---------- G and R as Blender has them, after Morrowind Workshop's (with Blender's controls chosen in the View tab) ----------
// With something selected and the mouse over the view, G picks it up: it follows the mouse along the ground until a
// click (or Enter) sets it down; Esc or the right button puts it back. R turns it as the mouse goes round it, about
// the up axis. X, Y, Z keep it to that axis (for R: turn about it); Shift+X, Y, Z to the other two; the same key again
// frees it. Typing a number moves (or turns, in degrees) exactly that much along the axis kept to, X if none; Backspace
// takes a digit back. The toolbar's Grid and Angle steps and Snap pieces apply as they do to the handles, and so does
// Land on what's below; several selected move together and turn about the Pivot (pivot.js). One Undo, as a drag.
// With FOLab's own controls G and R pick the handles' Move and Turn, as before; 1 and 2 do that with either.
const GRB = {on: null, over: false};

function grbTarget(){ return W.sel.length > 1 ? W.pivot : W.sel[0]; }
function grbAxisVec(a){ return new T.Vector3(a === 'x' ? 1 : 0, a === 'y' ? 1 : 0, a === 'z' ? 1 : 0); }
// where the mouse's ray meets the plane through p with normal n (null when it runs along it, or behind)
function grbOnPlane(m, n, p){
  const r = ray(m).ray, den = r.direction.dot(n);
  if (Math.abs(den) < 0.02) return null;
  const t = p.clone().sub(r.origin).dot(n) / den;
  if (t <= 0 || t > 60000) return null;
  return r.origin.clone().addScaledVector(r.direction, t);
}
function grbScreen(p){
  const v = p.clone().project(W.cam), rect = W.ren.domElement.getBoundingClientRect();
  return {x: rect.left + (v.x + 1) / 2 * rect.width, y: rect.top + (1 - v.y) / 2 * rect.height};
}
function grbStart(kind){
  if (!W.sel.length || !GRB.over || !W.mouse || W.dragging || W.placing || W.tool || GRB.on) return false;
  setTool(kind === 'turn' ? 'rotate' : 'translate');
  W.dragging = true; W.grabbing = true;
  gizmoStart();
  const t = grbTarget();
  GRB.on = {kind, axis: null, others: false, num: '', m0: {clientX: W.mouse.clientX, clientY: W.mouse.clientY},
           p0: t.position.clone(), q0: t.quaternion.clone()};
  grbNote();
  return true;
}
function grbNote(){
  const G = GRB.on; if (!G) return;
  const ax = G.axis ? (G.others ? 'not ' : '') + G.axis.toUpperCase() : (G.kind === 'turn' ? 'about Z' : 'along the ground');
  if (W.onNote) W.onNote((G.kind === 'turn' ? 'Turning ' : 'Moving ') + ax + (G.num ? ': ' + G.num + (G.kind === 'turn' ? '°' : '') : '') +
    ' · click or Enter sets it, Esc or right-click puts it back · X Y Z keep to an axis, Shift+X Y Z the other two, or type a number');
}
function grbUpdate(){
  const G = GRB.on; if (!G) return;
  const t = grbTarget(), m = W.mouse || G.m0;
  const num = G.num && G.num !== '-' && G.num !== '.' ? parseFloat(G.num) : null;
  if (G.kind === 'move'){
    let d = new T.Vector3();
    if (num !== null && !isNaN(num)){
      d = grbAxisVec(G.axis && !G.others ? G.axis : 'x').multiplyScalar(num);
    } else if (G.axis && !G.others){
      // (along one axis: on the plane through it that faces the camera most)
      const a = grbAxisVec(G.axis), cd = dir(), n = cd.clone().sub(a.clone().multiplyScalar(cd.dot(a)));
      if (n.lengthSq() < 1e-6) return;
      n.normalize();
      const p1 = grbOnPlane(m, n, G.p0), p0 = grbOnPlane(G.m0, n, G.p0);
      if (!p1 || !p0) return;
      d = a.multiplyScalar(p1.sub(p0).dot(a));
    } else {
      // (on a plane: the ground's unless Shift+axis said which one to keep out)
      const n = grbAxisVec(G.others ? G.axis : 'z');
      const p1 = grbOnPlane(m, n, G.p0), p0 = grbOnPlane(G.m0, n, G.p0);
      if (!p1 || !p0) return;
      d = p1.sub(p0);
    }
    const step = num === null && W.gridSnap > 0 ? W.gridSnap : 0;
    if (step) d.set(Math.round(d.x / step) * step, Math.round(d.y / step) * step, Math.round(d.z / step) * step);
    t.position.copy(G.p0).add(d);
    t.quaternion.copy(G.q0);
    W.dragAxis = G.axis === 'z' && !G.others ? 'Z' : null;
  } else {
    const a = grbAxisVec(G.axis || 'z');
    let ang;
    if (num !== null && !isNaN(num)) ang = num * Math.PI / 180;
    else {
      const c = grbScreen(G.p0);
      const a0 = Math.atan2(G.m0.clientY - c.y, G.m0.clientX - c.x), a1 = Math.atan2(m.clientY - c.y, m.clientX - c.x);
      // (the screen's angle grows clockwise: the turn goes the way the mouse goes round it, from whichever side)
      ang = (a1 - a0) * (dir().dot(a) < 0 ? -1 : 1);
      const snap = +($('#t-angle') && $('#t-angle').value) || 0;
      if (snap > 0){ const s = snap * Math.PI / 180; ang = Math.round(ang / s) * s; }
    }
    t.position.copy(G.p0);
    t.quaternion.copy(new T.Quaternion().setFromAxisAngle(a, ang)).multiply(G.q0);
  }
  t.updateMatrixWorld(true);
  gizmoFollow();
}
function grbEnd(keep){
  const G = GRB.on; if (!G) return;
  GRB.on = null; W.grabbing = false;
  if (keep){
    if (G.kind === 'move' && W.landAfter && W.dragAxis !== 'Z') landSelected();
    W.dragging = false;
    commitSelected(G.kind === 'turn' ? 'Turn' : 'Move');
  } else {
    const s = new T.Vector3();
    W.sel.forEach((g, i) => { if (W.dragFrom && W.dragFrom.each[i]) W.dragFrom.each[i].decompose(g.position, g.quaternion, s); });
    if (W.sel.length > 1 && W.dragFrom) W.dragFrom.pivot.decompose(W.pivot.position, W.pivot.quaternion, s);
    W.dragging = false;
    refreshSel();
    if (W.onNote) W.onNote('Put back.');
  }
  W.dragFrom = null; W.snapBoxes = null;
}
// (only with the mouse over the 3D view: G typed elsewhere is just a letter)
(() => {
  const v = $('#view');
  if (v){ v.addEventListener('mouseenter', () => { GRB.over = true; }); v.addEventListener('mouseleave', () => { GRB.over = false; }); }
})();
addEventListener('keydown', e => {
  if (typing(e)) return;
  const k = (e.key || '').toLowerCase();
  const stop = () => { e.preventDefault(); e.stopImmediatePropagation(); };
  if (GRB.on){
    const G = GRB.on;
    if (e.key === 'Escape'){ stop(); grbEnd(false); return; }
    if (e.key === 'Enter'){ stop(); grbUpdate(); grbEnd(true); return; }
    if (k === 'x' || k === 'y' || k === 'z'){
      stop();
      if (G.axis === k && G.others === e.shiftKey){ G.axis = null; G.others = false; } else { G.axis = k; G.others = e.shiftKey; }
      grbNote(); grbUpdate(); return;
    }
    if (/^[0-9]$/.test(e.key) || e.key === '.' || (e.key === '-' && !G.num)){ stop(); G.num += e.key; grbNote(); grbUpdate(); return; }
    if (e.key === 'Backspace'){ stop(); G.num = G.num.slice(0, -1); grbNote(); grbUpdate(); return; }
    if (k === 'g' || k === 'r'){ stop(); return; }
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey || !(W.blenderMouse && W.blenderMouse())) return;
  if ((k === 'g' || k === 'r') && $('#page-world') && $('#page-world').style.display !== 'none'){
    if (grbStart(k === 'r' ? 'turn' : 'move')) stop();
  }
}, true);
addEventListener('pointermove', () => { if (GRB.on) grbUpdate(); });
// a click sets it down, the right button puts it back (before the view's own handling, which would select or look)
addEventListener('pointerdown', e => {
  if (!GRB.on) return;
  e.preventDefault(); e.stopImmediatePropagation();
  if (e.button === 0){ grbUpdate(); grbEnd(true); } else grbEnd(false);
}, true);
