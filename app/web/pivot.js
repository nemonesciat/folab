// ---------- Pivot point and Blender's mouse, after Morrowind Workshop's (Blender's own names) ----------
// Pivot (on the toolbar beside Grid and Angle): what several selected things turn and tilt about with the handles.
//   Median point        about the middle of the group, at its lowest: they keep their places to each other (a set,
//                       the pieces of a building)
//   Individual origins  each turns where it stands: nothing swings round (rocks and trees on the land)
//   Active element      about the one clicked last: it stays and the others go round it
// Moving is the same in all three. world.js asks W.pivotAt (where the handles go) and W.pivotEach (turn each in place).
// Controls (View tab): as FOLab has it (the middle button slides the view), or as Blender has it (the middle button
// circles what's selected, or what's under the mouse; Shift+middle slides; Ctrl+middle moves in and out; G and R
// pick a thing up to move or turn with the mouse: grab.js).
const PIVOTS = [['group', 'Median point', 'About the middle of the group: they keep their places to each other. For a set, or the pieces of a building.'],
  ['each', 'Individual origins', 'Each turns where it stands: nothing swings round. For rocks and trees on the land.'],
  ['active', 'Active element', 'About the one clicked last: it stays where it is and the others go round it.']];
const PV = {active: null};
if (!PIVOTS.some(p => p[0] === VT.pivot)) VT.pivot = 'group';
if (VT.mouse !== 'blender') VT.mouse = '';

W.pivotEach = () => VT.pivot === 'each';
W.blenderMouse = () => VT.mouse === 'blender';
W.pivotAt = () => {
  if (VT.pivot === 'active' && PV.active){
    const g = W.sel.find(x => x.userData.thing.key === PV.active);
    if (g) return g.position.clone();
  }
  const b = new T.Box3();
  for (const g of W.sel){ g.updateMatrixWorld(true); b.expandByObject(g); }
  if (b.isEmpty()) for (const g of W.sel) b.expandByPoint(g.position);
  const c = b.getCenter(new T.Vector3());
  return VT.pivot === 'group' ? new T.Vector3(c.x, c.y, b.min.z) : c;
};
// (the active one: the thing a click added last, or the only one)
(() => {
  const _select = select;
  select = keys => {
    const before = new Set(W.sel.map(g => g.userData.thing.key));
    const list = Array.isArray(keys) ? keys : keys ? [keys] : [];
    const added = list.filter(k => !before.has(k));
    if (added.length === 1 || list.length === 1) PV.active = added.length === 1 ? added[0] : list[0];
    else if (!list.includes(PV.active)) PV.active = list[list.length - 1] || null;
    return _select(keys);
  };
})();
function pvSet(m){
  VT.pivot = m; vtSave();
  // (the handles go where the new pivot is at once)
  if (W.sel.length > 1){ W.pivot.position.copy(W.pivotAt()); W.pivot.rotation.set(0, 0, 0); W.pivot.updateMatrixWorld(true); }
  const s = $('#t-pivot'); if (s && s.value !== m) s.value = m;
}
// the toolbar: beside Grid and Angle
(() => {
  const grp = document.querySelector('.tgrp[data-grp="snap"]');
  if (!grp) return;
  const span = document.createElement('span');
  span.className = 'grp';
  span.title = 'Pivot point: what several selected things turn and tilt about';
  span.innerHTML = `Pivot <select id="t-pivot">${PIVOTS.map(([k, l, tip]) => `<option value="${k}" title="${tip}" ${k === VT.pivot ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
  const angle = $('#t-angle');
  const after = angle && angle.closest('.grp');
  if (after && after.nextSibling) grp.insertBefore(span, after.nextSibling); else grp.appendChild(span);
  $('#t-pivot').onchange = e => pvSet(e.target.value);
})();
// the View tab: the mouse
(() => {
  const _draw = vtDraw;
  vtDraw = () => {
    _draw();
    const box = $('#tab-view'); if (!box) return;
    const at = [...box.querySelectorAll('.h')].find(h => h.textContent === 'The view');
    const html = `<div class="vt-row" title="What the middle mouse button, G and R do in the 3D view">Controls
      <label><input type="radio" name="vt-mouse" data-pvm="" ${VT.mouse !== 'blender' ? 'checked' : ''}> FOLab's</label>
      <label><input type="radio" name="vt-mouse" data-pvm="blender" ${VT.mouse === 'blender' ? 'checked' : ''}> Blender's</label></div>
      <div class="note" style="padding:0 0 4px">Blender's: middle-drag circles what's selected (or what's under the mouse), Shift+middle slides, Ctrl+middle moves in and out.
      <b>G</b> picks up what's selected to move with the mouse, <b>R</b> turns it: X Y Z keep to an axis (Shift: the other two), type a number for an exact amount, click or Enter sets it, Esc puts it back. 1 and 2 still pick the handles.</div>`;
    if (at) at.insertAdjacentHTML('afterend', html); else box.insertAdjacentHTML('beforeend', html);
  };
  document.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset && 'pvm' in t.dataset){ VT.mouse = t.dataset.pvm; vtSave(); }
  });
})();
// the right-click menu, with several selected: the pivot there too
(() => {
  const _entries = cmEntries;
  cmEntries = (key, point) => {
    const E = _entries(key, point);
    if (W.sel.length > 1) for (const [k, l] of PIVOTS) if (k !== VT.pivot) E.push({group: 'Move and place', label: 'Pivot: ' + l, run: () => { pvSet(k); toast('Pivot: ' + l + '.'); }});
    return E;
  };
})();
