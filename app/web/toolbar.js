// ---------- The buttons over the 3D view and the map, in groups you can drag about ----------
// Each group has a grip (⋮⋮): drag it anywhere over the view. A group you've put somewhere stays there, kept from the
// view's nearer edge so it stays on that side when the window or the side panels change size. Right-click a group:
// back in the row, arrange them all automatically, or lock them (the grips hidden). (After the Workshop's toolbar.js.)
const TB = (() => { let t = {}; try { t = JSON.parse(localStorage.getItem('folab-toolbar') || '{}') || {}; } catch (e) {} t.pos = t.pos || {}; return t; })();
const TB_PAD = 6;
function tbSave(){ try { localStorage.setItem('folab-toolbar', JSON.stringify(TB)); } catch (e) {} }
const tbArea = () => $('#view');
const tbGroups = () => [...document.querySelectorAll('#tools .tgrp')];

// a group at a spot in the view (x, y from its top left corner), kept inside it
function tbPut(g, x, y){
  const A = tbArea();
  g.classList.add('tb-placed');
  x = Math.max(TB_PAD, Math.min(A.clientWidth - g.offsetWidth - TB_PAD, x));
  y = Math.max(TB_PAD, Math.min(A.clientHeight - g.offsetHeight - TB_PAD, y));
  g.style.left = x + 'px'; g.style.top = y + 'px';
  return [x, y];
}
function tbApply(){
  const A = tbArea(); if (!A || !A.clientWidth) return;        // (another page showing: done when it's back)
  A.classList.toggle('tb-locked', !!TB.locked);
  for (const g of tbGroups()){
    const p = TB.pos[g.dataset.grp];
    if (p && g.offsetParent){
      g.classList.add('tb-placed');
      tbPut(g, p.ax === 'r' ? A.clientWidth - p.x - g.offsetWidth : p.x, p.ay === 'b' ? A.clientHeight - p.y - g.offsetHeight : p.y);
    } else if (!p){ g.classList.remove('tb-placed'); g.style.left = g.style.top = ''; }
    if (!g.dataset.tbBound){ g.dataset.tbBound = '1'; g.addEventListener('contextmenu', tbMenu); }
  }
}
function tbAuto(){ TB.pos = {}; tbSave(); tbApply(); toast('Buttons back in a row'); }

function tbMenu(e){
  if (e.target.closest('select, input')) return;
  e.preventDefault(); e.stopPropagation();
  const k = e.currentTarget.dataset.grp, items = [];
  if (TB.pos[k]) items.push(['Put these back in the row', () => { delete TB.pos[k]; tbSave(); tbApply(); }]);
  items.push(['Arrange all automatically', tbAuto]);
  items.push([TB.locked ? 'Unlock: show the grips to move them' : 'Lock them where they are (hide the grips)', () => { TB.locked = !TB.locked; tbSave(); tbApply(); }]);
  let m = $('#tbmenu');
  if (!m){ m = document.createElement('div'); m.id = 'tbmenu'; document.body.appendChild(m); }
  m.innerHTML = items.map(([l], i) => `<div class="row" data-i="${i}"><div>${esc(l)}</div></div>`).join('');
  m.style.left = Math.min(e.clientX, innerWidth - 280) + 'px'; m.style.top = e.clientY + 'px'; m.style.display = 'block';
  m.onclick = ev => { const r = ev.target.closest('[data-i]'); if (r){ m.style.display = 'none'; items[+r.dataset.i][1](); } };
  setTimeout(() => document.addEventListener('mousedown', function close(ev){ if (!m.contains(ev.target)){ m.style.display = 'none'; document.removeEventListener('mousedown', close); } }), 0);
}

// dragging a group by its grip
document.addEventListener('pointerdown', e => {
  const grip = e.button === 0 && e.target.closest && e.target.closest('.tb-grip'); if (!grip) return;
  const g = grip.closest('.tgrp'), A = tbArea(); if (!g) return;
  e.preventDefault(); e.stopPropagation();
  const ar = A.getBoundingClientRect(), gr = g.getBoundingClientRect();
  const D = {sx: e.clientX, sy: e.clientY, x: gr.left - ar.left, y: gr.top - ar.top, at: null};
  document.body.classList.add('tb-dragging');
  const move = ev => { D.at = tbPut(g, D.x + ev.clientX - D.sx, D.y + ev.clientY - D.sy); };
  const up = () => {
    removeEventListener('pointermove', move, true); removeEventListener('pointerup', up, true);
    document.body.classList.remove('tb-dragging');
    if (!D.at) return;
    // kept from the nearer edge, so it stays on that side when the view gets wider or narrower
    const [x, y] = D.at, w = g.offsetWidth, h = g.offsetHeight, W_ = A.clientWidth, H_ = A.clientHeight;
    const right = x + w / 2 > W_ / 2, bottom = y + h / 2 > H_ / 2;
    TB.pos[g.dataset.grp] = {ax: right ? 'r' : 'l', x: Math.max(0, Math.round(right ? W_ - x - w : x)),
                            ay: bottom ? 'b' : 't', y: Math.max(0, Math.round(bottom ? H_ - y - h : y))};
    tbSave();
  };
  addEventListener('pointermove', move, true); addEventListener('pointerup', up, true);
}, true);

// the view changing size (side panels, the window): the groups follow their edge and stay inside
(() => { let raf = 0; new ResizeObserver(() => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; tbApply(); }); }).observe(tbArea()); })();
tbApply();
