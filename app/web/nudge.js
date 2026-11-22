// ---------- nudging what's selected with the keys ----------
// Arrow keys move it a little along the ground, as you look: ↑ away from you, ↓ towards you, ← and → to the sides
// (each along whichever of the world's directions is nearest, so it never drifts). Page Up / Page Down lift and lower
// it. Ctrl+← / Ctrl+→ turn it. A step is 1 unit (or the Move step, when that's on); hold Shift for 16 times as much.
// Turning is 1° a press (or the Turn step); Shift 15°. A run of presses is one Undo step, kept a moment after the last.
const NUDGE = {timer: null, hintTimer: null, moved: 0};

function nudgeStep(shift){
  const step = +$('#t-grid').value || 1;
  return shift ? step * 16 : step;
}
function nudgeTurnStep(shift){
  const step = +$('#t-angle').value || 1;
  return shift ? Math.max(15, step) : step;
}
// the world direction (x or y, either way) nearest the way the camera looks
function nudgeAxes(){
  const d = new T.Vector3(); W.cam.getWorldDirection(d);
  const fwd = Math.abs(d.x) > Math.abs(d.y) ? new T.Vector3(Math.sign(d.x), 0, 0) : new T.Vector3(0, Math.sign(d.y) || 1, 0);
  const right = new T.Vector3(fwd.y, -fwd.x, 0);
  return {fwd, right};
}
function nudgeHint(words){
  const h = $('#hint');
  h.innerHTML = `${esc(words)}<br><small><kbd>←</kbd><kbd>→</kbd><kbd>↑</kbd><kbd>↓</kbd> move ${nudgeStep(false)} · <kbd>Shift</kbd> ${nudgeStep(true)} · <kbd>Page Up</kbd>/<kbd>Page Down</kbd> up and down · <kbd>Ctrl+←</kbd>/<kbd>Ctrl+→</kbd> turn ${nudgeTurnStep(false)}°</small>`;
  h.style.display = 'block';
  clearTimeout(NUDGE.hintTimer);
  NUDGE.hintTimer = setTimeout(() => { if (!W.placing && !A.linking) h.style.display = 'none'; }, 2500);
}
function nudgeKeep(){
  clearTimeout(NUDGE.timer);
  NUDGE.timer = setTimeout(() => {
    NUDGE.timer = null;
    const mode = W.mode; W.mode = 'translate';        // (only where it is and how it's turned: never its size)
    try { commitSelected('Nudge'); } finally { W.mode = mode; }
  }, 450);
}
function nudgeKey(e){
  if (typing(e) || !W.sel.length || W.placing || W.dragging || W.grabbing || !W.box.offsetParent) return false;
  if ($('#page-world').style.display === 'none') return false;
  const k = e.key;
  if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'PageUp', 'PageDown'].includes(k)) return false;
  if (e.altKey || e.metaKey) return false;
  if (e.ctrlKey){
    if (k !== 'ArrowLeft' && k !== 'ArrowRight') return false;
    const deg = nudgeTurnStep(e.shiftKey) * (k === 'ArrowLeft' ? 1 : -1);
    const up = new T.Vector3(0, 0, 1);
    for (const g of W.sel) g.rotateOnWorldAxis(up, deg * Math.PI / 180);     // (each about its own origin, upright)
    refreshSel(); nudgeKeep();
    nudgeHint(`Turned ${Math.abs(deg)}° ${deg > 0 ? 'left' : 'right'}`);
    return true;
  }
  const s = nudgeStep(e.shiftKey), {fwd, right} = nudgeAxes(), v = new T.Vector3();
  if (k === 'ArrowUp') v.copy(fwd);
  else if (k === 'ArrowDown') v.copy(fwd).negate();
  else if (k === 'ArrowRight') v.copy(right);
  else if (k === 'ArrowLeft') v.copy(right).negate();
  else v.set(0, 0, k === 'PageUp' ? 1 : -1);
  v.multiplyScalar(s);
  for (const g of W.sel) g.position.add(v);
  if (W.sel.length > 1) W.pivot.position.add(v);
  refreshSel(); nudgeKeep();
  const which = {ArrowUp: 'away', ArrowDown: 'nearer', ArrowLeft: 'left', ArrowRight: 'right', PageUp: 'up', PageDown: 'down'}[k];
  nudgeHint(`Moved ${s} unit${s === 1 ? '' : 's'} ${which}`);
  return true;
}
addEventListener('keydown', e => { if (nudgeKey(e)){ e.preventDefault(); e.stopPropagation(); } }, true);
