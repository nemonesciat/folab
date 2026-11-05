// ---------- the right-click menu: search, a few quick actions, then fixed groups (the Workshop's ctxmenu.js) ----------
// Every entry belongs to one group, always in the same order with the same name; a group opens its list beside the
// menu when the mouse is over it, and a group of one entry shows that entry itself. Typing (the box has the keys as
// soon as the menu opens) lists every matching entry with its group's name; Enter runs the first. The quick actions
// are the two or three a kind of thing is right-clicked for most.
const CM_GROUPS = [['This door', '🚪'], ['Look and open', '👁'], ['Edit', '✎'], ['Move and place', '⟳'],
                   ['Replace and select', '⇄'], ['This place', '🏠'], ['View', '▤']];
const CM_QUICK = {DOOR: ['Go where it leads', 'Open its window'], NPC_: ['Open its record', 'Open its window'],
                  CREA: ['Open its record', 'Open its window'], '': ['Open its window', 'Open its record'], none: ['Play here']};
const CM = {el: null, items: [], recent: []};
try { CM.recent = JSON.parse(localStorage.getItem('folab-cm-recent') || '[]'); } catch (e) {}

function cmClose(){ if (!CM.el) return false; CM.el.remove(); CM.el = null; return true; }

// what the menu offers for what was right-clicked
function cmEntries(key, point){
  const sel = selThings(), one = sel.length === 1 ? sel[0] : null, n = sel.length, E = [];
  const add = (group, label, run, opt) => E.push(Object.assign({group, label, run}, opt || {}));
  if (key){
    if (one && one.door) add('This door', 'Go where it leads', () => goThroughDoor(one));
    if (one && one.type === 'DOOR') add('This door', one.door ? 'Link it to another door instead…' : 'Link it to another door…', () => linkStart(one));
    if (one && one.door && one.state) add('This door', 'Unlink it', () => unlinkDoor(one));
    if (one){ add('Look and open', 'Open its window', () => owOpen(one.key)); add('Look and open', 'Open its record', () => openRecord(one.bkey)); }
    add('Look and open', 'Look at it', focusSel);
    add('Edit', n > 1 ? `Copy ${n}` : 'Copy', copySel);
    if (A.clip) add('Edit', 'Paste here', () => { W.mouse = CM.at; paste(); });
    add('Edit', 'Duplicate', dupSel);
    if (sel.some(t => t.state === 'moved' || t.state === 'removed')) add('Edit', 'Put back as the game has it', revertSel);
    if (sel.every(t => t.state === 'removed')) add('Edit', 'Restore', revertSel);
    else add('Edit', n > 1 ? `Remove ${n}` : 'Remove', delSel);
    add('Move and place', 'Turn 90°', () => turnSel(1));
    add('Move and place', 'Turn 90° the other way', () => turnSel(-1));
    add('Move and place', 'Set it down on what\'s below', dropSel);
    add('Move and place', 'Align to the grid', alignSel);
    if (one) add('Replace and select', 'Swap for…', () => swapStart(one));
    if (one) add('Replace and select', `Select all the ${one.base} here`, () => select(visibleGroups().filter(g => g.userData.thing.bkey === one.bkey).map(g => g.userData.thing.key)));
    add('View', n > 1 ? `Hide them` : 'Hide it', hideSel);
    add('View', 'Hide everything else', () => { const keep = new Set(A.sel); hideKeys(W.group.children.map(g => g.userData.thing.key).filter(k => !keep.has(k))); });
  } else if (A.clip) add('Edit', 'Paste here', () => { W.mouse = CM.at; paste(); });
  add('This place', 'Play here', () => playHere(point));
  add('This place', 'New place of your own…', newPlaceDialog);
  add('This place', 'Select everything you can see', () => select(visibleGroups().map(g => g.userData.thing.key)));
  add('This place', 'Put my mod in the game and go here…', install);
  add('This place', 'Copy the console line to come here', () => { navigator.clipboard.writeText('coc ' + A.cellEdid); toast('Copied: coc ' + A.cellEdid); });
  if (W.hidden.size) add('View', `Show the ${W.hidden.size} hidden`, showHidden);
  add('View', 'The 3D view\'s controls', () => { $('#help3d').style.display = 'block'; });
  return E;
}

function cmRun(it){
  cmClose();
  CM.recent = [it.label, ...CM.recent.filter(l => l !== it.label)].slice(0, 3);
  try { localStorage.setItem('folab-cm-recent', JSON.stringify(CM.recent)); } catch (e) {}
  it.run();
}

function cmOpen(e, key, point){
  cmClose();
  CM.at = {clientX: e.clientX, clientY: e.clientY};
  const items = CM.items = cmEntries(key, point), sel = selThings();
  const head = key && sel.length === 1 ? `${sel[0].base}${sel[0].name ? ' — ' + sel[0].name : ''}` : key ? `${sel.length} selected` : A.cellEdid || '';
  const quickNames = (sel.length === 1 && CM_QUICK[sel[0].type]) || (key ? CM_QUICK[''] : CM_QUICK.none);
  const quick = quickNames.map(l => items.find(i => i.label === l)).filter(Boolean);
  const recent = CM.recent.map(l => items.find(i => i.label === l)).filter(i => i && !quick.includes(i));
  const el = CM.el = document.createElement('div');
  el.className = 'cmenu';
  const row = (it, sub) => `<div class="cmi" data-i="${items.indexOf(it)}">${esc(it.label)}${sub ? `<small>${esc(sub)}</small>` : ''}</div>`;
  // (a group of one entry shows the entry itself, unless it's already a quick or recent one above)
  const groups = CM_GROUPS.map(([g, icon]) => [g, icon, items.filter(i => i.group === g)])
    .filter(([, , l]) => l.length && !(l.length === 1 && (quick.includes(l[0]) || recent.includes(l[0]))));
  el.innerHTML = `<div class="cmhead">${esc(head)}</div><input class="cmfind" placeholder="Search…">
    <div class="cmbody">${quick.map(i => row(i)).join('')}${recent.length ? '<div class="cmsep"></div>' + recent.map(i => row(i)).join('') : ''}
    <div class="cmsep"></div>${groups.map(([g, icon, l]) => l.length === 1 ? row(l[0]) : `<div class="cmg" data-g="${esc(g)}"><span>${icon}</span>${esc(g)}<b>›</b></div>`).join('')}</div>`;
  document.body.appendChild(el);
  const r = el.getBoundingClientRect();
  el.style.left = Math.min(e.clientX, innerWidth - r.width - 8) + 'px';
  el.style.top = Math.min(e.clientY, innerHeight - r.height - 8) + 'px';
  const body = el.querySelector('.cmbody'), find = el.querySelector('.cmfind');
  let sub = null;
  const closeSub = () => { if (sub){ sub.remove(); sub = null; } };
  el.addEventListener('mouseover', ev => {
    const g = ev.target.closest('.cmg');
    if (!g){ if (ev.target.closest('.cmi') && !ev.target.closest('.cmsub')) closeSub(); return; }
    if (sub && sub.dataset.g === g.dataset.g) return;
    closeSub();
    sub = document.createElement('div'); sub.className = 'cmenu cmsub'; sub.dataset.g = g.dataset.g;
    sub.innerHTML = items.filter(i => i.group === g.dataset.g).map(i => row(i)).join('');
    el.appendChild(sub);
    const gr = g.getBoundingClientRect(), sr = sub.getBoundingClientRect();
    const left = gr.right + sr.width > innerWidth ? gr.left - sr.width : gr.right;
    sub.style.left = (left - el.getBoundingClientRect().left) + 'px';
    sub.style.top = (Math.min(gr.top, innerHeight - sr.height - 8) - el.getBoundingClientRect().top) + 'px';
  });
  el.addEventListener('click', ev => { const i = ev.target.closest('.cmi'); if (i) cmRun(items[+i.dataset.i]); });
  find.addEventListener('input', () => {
    const q = find.value.trim().toLowerCase();
    closeSub();
    if (!q){ cmOpen(e, key, point); return; }
    const hits = items.filter(i => (i.label + ' ' + i.group).toLowerCase().includes(q));
    body.innerHTML = hits.length ? hits.map(i => row(i, i.group)).join('') : '<div class="note">Nothing matches.</div>';
  });
  find.addEventListener('keydown', ev => {
    if (ev.key === 'Enter'){ const f = body.querySelector('.cmi'); if (f) cmRun(items[+f.dataset.i]); }
    if (ev.key === 'Escape') cmClose();
    ev.stopPropagation();
  });
  setTimeout(() => find.focus(), 0);
}
addEventListener('mousedown', e => { if (CM.el && !CM.el.contains(e.target)) cmClose(); }, true);
W.onContext = (e, key, point) => cmOpen(e, key, point);

// ---------- what the menu does that the toolbar doesn't ----------
function turnSel(sign){
  sendMoves(selThings().map(t => { const p = t.p.slice(); p[5] = Math.round((p[5] + sign * Math.PI / 2) * 10000) / 10000; return [t, p]; }), 'Turn 90°');
}
function alignSel(){
  const g = +$('#t-grid').value || 16;
  sendMoves(selThings().map(t => { const p = t.p.slice(); p[0] = Math.round(p[0] / g) * g; p[1] = Math.round(p[1] / g) * g; return [t, p]; }), 'Align to the grid');
}

// Swap for…: the Place panel picks what goes there instead
function swapStart(t){
  A.swapping = t;
  tab('right', 'place');
  $('#place-note').innerHTML = `<b>Pick what to swap ${esc(t.base)} for.</b> <a href="#" id="swap-cancel">Cancel</a>`;
  $('#swap-cancel').onclick = ev => { ev.preventDefault(); swapEnd(); };
  $('#f-place').focus();
}
function swapEnd(){ A.swapping = null; $('#place-note').textContent = 'Click a thing, then click where it goes. Esc stops.'; }

async function goThroughDoor(t){
  const d = await api('/api/door?key=' + encodeURIComponent(t.key));
  if (!d) return toast('This door doesn\'t lead anywhere (it may open in place).', true);
  if (!d.cell) return toast('It leads to a place that isn\'t loaded.', true);
  if (!d.interior) return toast(`It leads outside${d.cell_name ? ' (' + d.cell_name + ')' : ''}: FOLab can't show outdoor places yet.`, true);
  await openPlace(d.cell, {p: d.p, facing: true});
  const other = W.byKey.get(d.door);
  if (other){
    // face out into the room: from the door to where you arrive (the arrival point is always on the room's side)
    const dx = d.p[0] - other.position.x, dy = d.p[1] - other.position.y;
    if (Math.hypot(dx, dy) > 1){ W.yaw = Math.atan2(dy, dx); W.pitch = -0.1; }
    select([d.door]);
  }
  toast('Through to ' + (d.cell_name || d.cell_edid));
}
