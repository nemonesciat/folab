// ---------- The 3D view's comforts ----------
// Line things up and space them out; Settle (let things fall and come to rest on what's under them); groups that select
// together; a placed thing's owner, lock and enable parent; hiding every one of a kind; a second window onto the same
// mod, the two kept in step. Everything goes through the same edits as the rest, as one Undo each.
const CF = {groups: [], one: false, parentFor: null, channel: null, second: new URLSearchParams(location.search).get('win') === '2', open: false};

(function cfMake(){
  const css = document.createElement('style');
  css.textContent = `
  .cf-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;padding:2px 12px 6px}.cf-grid .btn{padding:3px 4px;font-size:12px;white-space:normal}
  .cf-props{padding:2px 12px 8px;display:flex;flex-direction:column;gap:5px}.cf-props label{display:flex;flex-direction:column;gap:2px;color:var(--muted);font-size:12.5px}
  .cf-props label.inl{flex-direction:row;align-items:center;gap:6px}.cf-props small{color:var(--faint);font-size:11.5px}
  .cf-pick{position:relative}.cf-pick input{width:100%}.cf-list{position:absolute;z-index:12;left:0;right:0;top:100%;max-height:190px;overflow-y:auto;background:var(--panel2);border:1px solid var(--line2);border-radius:6px;box-shadow:0 8px 24px #0008}
  .cf-now{color:var(--gold);font-size:12px;overflow-wrap:anywhere}.cf-now a{color:var(--muted);margin-left:6px;cursor:pointer}`;
  document.head.appendChild(css);
  const edit = document.querySelector('.tgrp[data-grp="edit"]');
  const settle = document.createElement('button');
  settle.className = 'btn'; settle.id = 't-settle'; settle.textContent = '🪂 Settle';
  settle.title = 'Let what\'s selected fall and come to rest on what\'s under it, small things leaning with it (Shift+End)';
  settle.onclick = () => settleSel(true);
  $('#t-drop').after(settle);
  const view = document.querySelector('.tgrp[data-grp="view"]');
  const two = document.createElement('button');
  two.className = 'btn'; two.id = 't-2win'; two.textContent = '↗ Second window'; two.title = 'This place in another window, looking where you look now. Both show the same mod, and each sees what the other changes';
  two.onclick = () => cfSecondWindow();
  if (!CF.second) view.appendChild(two);
  // the right-click menu
  CM_GROUPS.splice(CM_GROUPS.findIndex(g => g[0] === 'Move and place') + 1, 0, ['Line them up', '⇹']);
  CM_GROUPS.splice(CM_GROUPS.findIndex(g => g[0] === 'Replace and select') + 1, 0, ['Looks', '🎨']);
  const _entries = cmEntries;
  cmEntries = (key, point) => {
    const E = _entries(key, point), add = (group, label, run) => E.push({group, label, run});
    const sel = selThings(), one = sel.length === 1 ? sel[0] : null, n = sel.length;
    if (key){
      add('Move and place', n > 1 ? `Settle them` : 'Settle it', () => settleSel(true));
      add('Move and place', n > 1 ? 'Scale them…' : 'Scale…', cfScale);
      if (n > 1) for (const [label, f] of CF_LINES) add('Line them up', label, f);
      if (one && one.model){
        add('Looks', 'Retexture…', () => cfRetexture(one));
        add('Looks', 'Its mesh in the Library', () => cfToLibrary(one));
      }
      if (one) add('Look and open', 'Owner, lock, what enables it…', () => { CF.open = true; tab('right', 'selected'); drawSelected(selThings()); });
      if (one) add('Look and open', 'Where it\'s used', () => openRecord(one.bkey));
      add('Replace and select', 'Select it with everything on it', cfSelectOnTop);
      if (n > 1) add('Replace and select', `Group these ${n}`, cfGroup);
      if (cfGroupOf(sel.map(t => t.key)).length) add('Replace and select', 'Ungroup', cfUngroup);
      if (one) add('View', `Hide every ${thingKindName(one)}`, () => cfHideKind(thingKind(one)));
    }
    if (Object.values(VT.kinds).includes(false)) add('View', 'Show every kind again', () => { VT.kinds = {}; vtSave(); vtApply(); });
    add('View', 'Open a second window here', () => cfSecondWindow());
    return E;
  };
  // the Selected panel
  const _draw = drawSelected;
  drawSelected = list => { _draw(list); cfSelected(list); };
  // groups: a click on one selects them all (Ctrl+click: just that one)
  $('#view').addEventListener('pointerdown', e => { CF.one = e.ctrlKey || e.metaKey; }, true);
  const _select = select;
  select = keys => {
    if (!Array.isArray(keys)) keys = keys ? [keys] : [];
    if (!CF.one && CF.groups.length && keys.length){
      const all = new Set(keys);
      for (const g of cfGroupOf(keys)) for (const k of g.keys) if (W.byKey.has(k)) all.add(k);
      keys = [...all];
    }
    return _select(keys);
  };
  addEventListener('keydown', e => {
    if (typing(e) || !$('#view').offsetParent) return;
    if (e.key === 'Escape' && CF.parentFor){ CF.parentFor = null; $('#hint').style.display = 'none'; e.stopImmediatePropagation(); return; }
    if (e.key === 'End' && e.shiftKey){ e.preventDefault(); e.stopImmediatePropagation(); settleSel(true); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'g'){ e.preventDefault(); e.shiftKey ? cfUngroup() : cfGroup(); }
  }, true);
  // the two windows, in step: whichever makes a change tells the other
  const _post = post;
  post = async (path, body) => {
    const d = await _post(path, body);
    if (CF.channel && !/\/(save|quit)$/.test(path)) CF.channel.postMessage({changed: path, from: CF.me});
    return d;
  };
  CF.me = Math.random().toString(36).slice(2);
  try {
    CF.channel = new BroadcastChannel('folab-windows');
    let timer;
    CF.channel.onmessage = e => {
      if (e.data.from === CF.me || !e.data.changed) return;
      clearTimeout(timer);
      timer = setTimeout(async () => { await refreshState(); await resync(); if (typeof loadPlaces === 'function') loadPlaces(); }, 200);
    };
  } catch (e) { CF.channel = null; }
  if (CF.second){
    // arriving: where the first window looked; closing when FOLab does
    const fails = {n: 0};
    setInterval(() => fetch('/api/about').then(() => { fails.n = 0; }).catch(() => { if (++fails.n > 2) window.close(); }), 5000);
    setTimeout(cfArrive, 1500);
  }
  cfGroupsLoad();
  const _setState = setState;
  let last = null;
  setState = s => { _setState(s); const n = s.project && s.project.name; if (n !== last){ last = n; cfGroupsLoad(); } };
})();

const thingKindName = t => ({buildings: 'building piece', scenery: 'rock and plant', doors: 'door', containers: 'container', furniture: 'piece of furniture', lights: 'light', items: 'item', people: 'person', creatures: 'creature', markers: 'marker'})[thingKind(t)] || 'thing like it';
function cfHideKind(k){ VT.kinds[k] = false; vtSave(); vtApply(); toast('Hidden for now. The View tab, or right-click, brings them back.'); }

// ---------- lining up ----------
// the box each selected thing fills
function cfBoxes(){
  return W.sel.map(g => { g.updateMatrixWorld(true); const b = new T.Box3().setFromObject(g); return b.isEmpty() ? new T.Box3().setFromCenterAndSize(g.position, new T.Vector3(16, 16, 16)) : b; });
}
function cfMove(deltas, label){
  const moves = [];
  W.sel.forEach((g, i) => {
    const d = deltas[i]; if (!d || !(d.x || d.y || d.z)) return;
    const t = g.userData.thing, p = t.p.slice();
    p[0] = Math.round((p[0] + d.x) * 100) / 100; p[1] = Math.round((p[1] + d.y) * 100) / 100; p[2] = Math.round((p[2] + d.z) * 100) / 100;
    moves.push([t, p]);
  });
  if (moves.length) sendMoves(moves, label); else toast('They\'re already lined up.');
}
// all to one edge or the middle: 'min', 'max', 'mid' of the whole selection on an axis
function cfLine(axis, how, label){
  if (W.sel.length < 2) return toast('Select two or more first.', true);
  const bs = cfBoxes(), v = b => how === 'min' ? b.min[axis] : how === 'max' ? b.max[axis] : (b.min[axis] + b.max[axis]) / 2;
  const all = bs.map(v), to = how === 'min' ? Math.min(...all) : how === 'max' ? Math.max(...all) : all.reduce((s, x) => s + x, 0) / all.length;
  cfMove(bs.map(b => Object.assign({x: 0, y: 0, z: 0}, {[axis]: to - v(b)})), label);
}
// the same gap between each and the next, the two at the ends staying put
function cfSpace(axis, label){
  if (W.sel.length < 3) return toast('Select three or more first.', true);
  const bs = cfBoxes(), order = bs.map((b, i) => i).sort((a, c) => bs[a].min[axis] - bs[c].min[axis]);
  const size = b => b.max[axis] - b.min[axis], lo = bs[order[0]].min[axis], hi = bs[order[order.length - 1]].max[axis];
  const gap = (hi - lo - bs.reduce((s, b) => s + size(b), 0)) / (bs.length - 1);
  const d = bs.map(() => ({x: 0, y: 0, z: 0}));
  let at = lo;
  for (const i of order){ d[i][axis] = at - bs[i].min[axis]; at += size(bs[i]) + gap; }
  cfMove(d, label);
}
const CF_LINES = [['West sides in line', () => cfLine('x', 'min', 'Line up')], ['East sides in line', () => cfLine('x', 'max', 'Line up')],
                  ['South sides in line', () => cfLine('y', 'min', 'Line up')], ['North sides in line', () => cfLine('y', 'max', 'Line up')],
                  ['Bottoms level', () => cfLine('z', 'min', 'Level')], ['Tops level', () => cfLine('z', 'max', 'Level')],
                  ['Middles in line east to west', () => cfLine('y', 'mid', 'Line up')], ['Middles in line north to south', () => cfLine('x', 'mid', 'Line up')],
                  ['Space evenly east to west', () => cfSpace('x', 'Space evenly')], ['Space evenly north to south', () => cfSpace('y', 'Space evenly')],
                  ['Space evenly upwards', () => cfSpace('z', 'Space evenly')]];

// ---------- Settle: fall, come to rest ----------
// Not a physics engine: each thing falls until what's under its middle and corners stops it, the lowest first, so a
// stack lands on itself. A small thing with its middle over nothing tips off the edge; on a slope it leans with the
// ground. It shows the fall, then keeps the result as one Undo.
const CF_SMALL = 150;
function cfUnder(x, y, z, except, max){
  const r = new T.Raycaster(new T.Vector3(x, y, z), new T.Vector3(0, 0, -1), 0, max);
  return r.intersectObjects(visibleGroups(except).concat(W.lands ? [...W.lands] : []), true)[0] || null;
}
function cfRest(g){
  g.updateMatrixWorld(true);
  const b = new T.Box3().setFromObject(g); if (b.isEmpty()) return null;
  const c = b.getCenter(new T.Vector3()), size = b.getSize(new T.Vector3()), small = Math.max(size.x, size.y, size.z) < CF_SMALL;
  const inset = 0.85, hx = size.x / 2 * inset, hy = size.y / 2 * inset, from = b.min.z + 1;
  const points = [[0, 0], [hx, hy], [hx, -hy], [-hx, hy], [-hx, -hy]];
  const hits = points.map(([dx, dy]) => cfUnder(c.x + dx, c.y + dy, from, g, 20000));
  if (!hits.some(Boolean)) return null;
  const out = {x: g.position.x, y: g.position.y, z: g.position.z, q: g.quaternion.clone()};
  const tops = hits.filter(Boolean).map(h => h.point.z), top = Math.max(...tops);
  if (small && hits[0] && top - hits[0].point.z > Math.max(10, size.z)){
    // its middle is over a drop: it goes over the edge, off the side away from what held it
    const held = hits.findIndex(h => h && h.point.z === top), [dx, dy] = points[held], ln = Math.hypot(dx, dy) || 1;
    const nudge = Math.max(size.x, size.y) * 0.7;
    out.x -= dx / ln * nudge; out.y -= dy / ln * nudge;
    const below = cfUnder(c.x - dx / ln * nudge, c.y - dy / ln * nudge, from, g, 20000);
    out.z = g.position.z - (b.min.z - (below ? below.point.z : hits[0].point.z));
    return out;
  }
  out.z = g.position.z - (b.min.z - top);
  // leaning: small things on what's sloped under them, by the corners' heights
  if (small && hits.slice(1).every(Boolean)){
    const hA = (hits[1].point.z + hits[2].point.z) / 2, hB = (hits[3].point.z + hits[4].point.z) / 2;
    const hC = (hits[1].point.z + hits[3].point.z) / 2, hD = (hits[2].point.z + hits[4].point.z) / 2;
    const sx = hx ? (hA - hB) / (2 * hx) : 0, sy = hy ? (hC - hD) / (2 * hy) : 0;
    if ((Math.abs(sx) > 0.02 || Math.abs(sy) > 0.02) && Math.abs(sx) < 0.7 && Math.abs(sy) < 0.7){
      const n = new T.Vector3(-sx, -sy, 1).normalize();
      out.q = new T.Quaternion().setFromUnitVectors(new T.Vector3(0, 0, 1), n).multiply(g.quaternion);
      out.z = g.position.z - (b.min.z - (hits.slice(1).reduce((s, h) => s + h.point.z, 0) / 4));
    }
  }
  return out;
}
async function settleSel(show){
  if (!needSel()) return;
  await Promise.all(W.sel.map(g => g.userData.ready));
  const list = W.sel.slice().sort((a, b) => a.position.z - b.position.z), moves = [], starts = [];
  // lowest first: each lands where the last one came to rest, so they're moved as they go
  for (const g of list){
    const r = cfRest(g);
    if (!r) continue;
    starts.push({g, z: g.position.z, x: g.position.x, y: g.position.y, q: g.quaternion.clone(), r});
    g.position.set(r.x, r.y, r.z); g.quaternion.copy(r.q); g.updateMatrixWorld(true);
  }
  if (!starts.length) return toast('Nothing below to come to rest on.', true);
  if (show) await cfFall(starts);
  for (const s of starts){
    const t = s.g.userData.thing, p = gameP(s.g);
    if (!p.every((v, i) => Math.abs(v - t.p[i]) < 0.01)) moves.push([t, p]);
  }
  refreshSel();
  if (!moves.length) return toast('Already at rest.');
  sendMoves(moves, 'Settle');
}
// the fall, drawn: gravity from where each was to where it rests, with a small bounce
function cfFall(list){
  const G = 2400, began = performance.now();
  for (const s of list){ s.tz = s.r.z; s.tx = s.r.x; s.ty = s.r.y; s.tq = s.r.q; s.drop = Math.max(0, s.z - s.tz); s.time = Math.sqrt(2 * s.drop / G); s.g.position.set(s.x, s.y, s.z); s.g.quaternion.copy(s.q); }
  const longest = Math.max(...list.map(s => s.time)) + 0.14;
  return new Promise(done => {
    const step = now => {
      const t = (now - began) / 1000;
      for (const s of list){
        const f = s.time ? Math.min(1, t / s.time) : 1, g = s.g;
        g.position.x = s.x + (s.tx - s.x) * f; g.position.y = s.y + (s.ty - s.y) * f;
        const after = t - s.time, hop = after > 0 && after < 0.14 ? Math.sin(after / 0.14 * Math.PI) * Math.min(6, s.drop * 0.05) : 0;
        g.position.z = (f < 1 ? s.z - 0.5 * G * t * t : s.tz) + hop;
        g.quaternion.copy(s.q).slerp(s.tq, f);
      }
      refreshSel();
      if (t < longest) requestAnimationFrame(step);
      else { for (const s of list){ s.g.position.set(s.tx, s.ty, s.tz); s.g.quaternion.copy(s.tq); s.g.updateMatrixWorld(true); } done(); }
    };
    requestAnimationFrame(step);
  });
}

// ---------- more on the menu ----------
function cfScale(){
  if (!needSel()) return;
  const v = parseFloat(prompt('Make them this many times the size they are (0.5: half, 2: double):', '1.25'));
  if (!v || v <= 0) return;
  const c = selCenter();
  sendMoves(selThings().map(t => {
    const p = t.p.slice();
    p[0] = Math.round((c.x + (p[0] - c.x) * v) * 100) / 100; p[1] = Math.round((c.y + (p[1] - c.y) * v) * 100) / 100; p[2] = Math.round((c.z + (p[2] - c.z) * v) * 100) / 100;
    return [t, p, Math.max(0.01, Math.min(10, Math.round((t.s || 1) * v * 1000) / 1000))];
  }), 'Scale');
}
function cfSelectOnTop(){
  if (!needSel()) return;
  const keys = new Set(A.sel), boxes = cfBoxes();
  for (const g of visibleGroups()){
    if (W.sel.includes(g) || g.userData.thing.marker) continue;
    const b = new T.Box3().setFromObject(g); if (b.isEmpty()) continue;
    const c = b.getCenter(new T.Vector3());
    if (boxes.some(s => c.x >= s.min.x && c.x <= s.max.x && c.y >= s.min.y && c.y <= s.max.y && b.min.z >= s.max.z - 8 && b.min.z <= s.max.z + 40)) keys.add(g.userData.thing.key);
  }
  select([...keys]);
  toast(`${keys.size} selected`);
}
function cfToLibrary(t){
  page('library');
  LB.kind = 'mesh'; LB.q = ''; $('#lb-q').value = '';
  LB.folder = t.model.toLowerCase().split('\\').slice(0, -1).join('\\');
  lbDrawKinds(); lbList().then(() => lbChoose(t.model.toLowerCase())); lbCounts();
}
function cfRetexture(t){ lbRetexture({model: t.model, key: t.bkey, ref: t.key, cell: t.cell || A.cellId}); }

// ---------- groups ----------
async function cfGroupsLoad(){ try { CF.groups = (await api('/api/library/groups')).groups || []; } catch (e){ CF.groups = []; } }
function cfGroupsSave(){ return post('/api/library/groups', {groups: CF.groups}).catch(fail); }
function cfGroupOf(keys){ return CF.groups.filter(g => g.keys.some(k => keys.includes(k))); }
function cfGroup(){
  if (W.sel.length < 2) return toast('Select two or more to group them.', true);
  if (!A.state.project) return toast('Start a mod first.', true);
  const keys = A.sel.slice();
  CF.groups = CF.groups.map(g => ({keys: g.keys.filter(k => !keys.includes(k))})).filter(g => g.keys.length > 1);
  CF.groups.push({keys});
  cfGroupsSave(); drawSelected(selThings());
  toast(`Grouped ${keys.length}: a click selects them together, Ctrl+click just one.`);
}
function cfUngroup(){
  const n = cfGroupOf(A.sel).length; if (!n) return toast('They aren\'t in a group.', true);
  CF.groups = CF.groups.filter(g => !g.keys.some(k => A.sel.includes(k)));
  cfGroupsSave(); drawSelected(selThings()); toast('Ungrouped.');
}

// ---------- what the Selected panel adds ----------
function cfSelected(list){
  const box = $('#selected'); if (!box || !list.length) return;
  if (list.length > 1){
    const g = cfGroupOf(list.map(t => t.key));
    box.insertAdjacentHTML('beforeend', `<div class="h">Line them up</div><div class="cf-grid">${CF_LINES.map(([l], i) => `<button class="btn" data-cfl="${i}">${esc(l)}</button>`).join('')}</div>
      <div class="acts"><button class="btn" data-cfa="settle">🪂 Settle</button><button class="btn" data-cfa="${g.length ? 'ungroup' : 'group'}">${g.length ? 'Ungroup' : 'Group them'}</button></div>`);
  } else {
    const t = list[0], g = cfGroupOf([t.key]);
    const acts = box.querySelector('.acts');
    if (acts && t.state !== 'removed'){
      acts.insertAdjacentHTML('beforeend', `<button class="btn" data-cfa="settle">🪂 Settle</button>${t.model ? '<button class="btn" data-cfa="retex">🎨 Retexture…</button>' : ''}`);
      if (g.length) acts.insertAdjacentHTML('beforeend', `<button class="btn" data-cfa="ungroup">Ungroup (${g[0].keys.length})</button>`);
    }
    if (t.state !== 'removed' && !['NPC_', 'CREA'].includes(t.type)){
      const rec = $('#sel-rec');
      const div = document.createElement('div'); div.id = 'cf-props';
      rec.before(div);
      cfPropsDraw(t);
    }
  }
}
document.addEventListener('click', e => {
  const l = e.target.closest('[data-cfl]');
  if (l) return CF_LINES[+l.dataset.cfl][1]();
  const a = e.target.closest('[data-cfa]'); if (!a) return;
  const t = selThings()[0];
  ({settle: () => settleSel(true), group: cfGroup, ungroup: cfUngroup, retex: () => cfRetexture(t)})[a.dataset.cfa]();
});

// ---------- owner, lock, what enables it ----------
async function cfPropsDraw(t){
  const box = $('#cf-props'); if (!box) return;
  if (!CF.open){
    box.innerHTML = `<div class="acts" style="padding-top:0"><button class="btn" id="cf-open" title="Who owns it, its lock and key, what switches it on">🔒 Owner, lock, what enables it…</button></div>`;
    box.querySelector('#cf-open').onclick = () => { CF.open = true; cfPropsDraw(t); };
    return;
  }
  const u = new URLSearchParams({cell: t.cell || A.cellId, ref: t.key});
  const d = await api('/api/library/props?' + u).catch(() => null);
  if (!d || !$('#cf-props') || !A.sel.includes(t.key)) return;
  const p = d.props, lk = p.lock, lockable = ['DOOR', 'CONT', 'TERM'].includes(t.type);
  CF.edit = {t, owner: p.owner || '', rank: p.rank, key: (lk && lk.key) || '', parent: p.parent ? p.parent.ref : '', names: {owner: d.owner_name, key: d.key_name, parent: d.parent_name}, faction: d.owner_is_faction};
  box.innerHTML = `<div class="h">Owner, lock, what enables it <a href="#" id="cf-close" style="float:right;color:var(--muted)">✕</a></div><div class="cf-props">
    <label>Belongs to<div class="cf-now" id="cf-owner-now"></div><div class="cf-pick"><input id="cf-owner" placeholder="Search a character or faction…" autocomplete="off"><div class="cf-list" id="cf-owner-l" style="display:none"></div></div>
      <small>Taking it counts as stealing from them.</small></label>
    <label id="cf-rankrow" style="display:${d.owner_is_faction ? 'flex' : 'none'}">Free to use from this faction rank<input id="cf-rank" type="number" min="0" value="${p.rank === undefined || p.rank === null ? '' : p.rank}" placeholder="(any member)"></label>
    ${lockable ? `<label>Lock<select id="cf-lock"><option value="-1">Not locked</option>${d.levels.map(([v, l]) => `<option value="${v}" ${lk && lk.level === v ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select></label>
      <label>Key<div class="cf-now" id="cf-key-now"></div><div class="cf-pick"><input id="cf-key" placeholder="Search a key…" autocomplete="off"><div class="cf-list" id="cf-key-l" style="display:none"></div></div></label>
      <label class="inl"><input type="checkbox" id="cf-leveled" ${lk && lk.leveled ? 'checked' : ''}> The lock gets harder with the player's level</label>` : ''}
    <label>Enabled by<div class="cf-now" id="cf-parent-now"></div></label>
    <div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn" id="cf-parent-pick" title="Then click the thing in the view: this one appears and disappears with it">Pick it in the view…</button></div>
    <label class="inl"><input type="checkbox" id="cf-opp" ${p.parent && p.parent.opposite ? 'checked' : ''}> It shows when that one doesn't (the opposite)</label>
    <label class="inl"><input type="checkbox" id="cf-off" ${p.disabled ? 'checked' : ''}> It starts switched off (a script or its parent brings it)</label>
    <div class="acts" style="padding:2px 0 0"><button class="btn primary" id="cf-save">Save</button></div></div>`;
  box.querySelector('#cf-close').onclick = ev => { ev.preventDefault(); CF.open = false; cfPropsDraw(t); };
  cfNow('owner'); cfNow('key'); cfNow('parent');
  cfPick('owner', ['NPC_', 'FACT']); if (lockable) cfPick('key', ['KEYM']);
  box.querySelector('#cf-parent-pick').onclick = () => {
    CF.parentFor = t; const h = $('#hint'); h.textContent = `Click the thing that enables ${t.base} · Esc stops`; h.style.display = 'block';
  };
  box.querySelector('#cf-save').onclick = () => cfPropsSave(lockable);
}
function cfNow(f){
  const el = $(`#cf-${f}-now`); if (!el) return;
  const e = CF.edit, v = e[f];
  el.innerHTML = v ? `${esc(e.names[f] || v)}<a data-cfclear="${f}" title="Clear">✕</a>` : '<span style="color:var(--faint)">No one</span>';
  if (!v && f !== 'owner') el.innerHTML = '<span style="color:var(--faint)">Nothing</span>';
  const c = el.querySelector('[data-cfclear]');
  if (c) c.onclick = () => { e[f] = ''; e.names[f] = ''; cfNow(f); };
}
function cfPick(f, types){
  const inp = $(`#cf-${f}`), list = $(`#cf-${f}-l`); if (!inp) return;
  let timer;
  inp.oninput = () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = inp.value.trim(); if (!q){ list.style.display = 'none'; return; }
      const res = await Promise.all(types.map(ty => api(`/api/records?type=${ty}&q=${encodeURIComponent(q)}`).then(r => (r.rows || r).map(x => Object.assign(x, {ty}))).catch(() => [])));
      const rows = res.flat().slice(0, 40);
      list.innerHTML = rows.length ? rows.map(r => `<div class="row" data-k="${esc(r.key)}" data-ty="${r.ty}" data-n="${esc(r.edid + (r.name ? ' (' + r.name + ')' : ''))}"><div>${esc(r.edid)}<small>${esc(r.name || '')}</small></div><span class="n">${r.ty === 'FACT' ? 'faction' : ''}</span></div>`).join('') : '<div class="note">Nothing found.</div>';
      list.style.display = 'block';
    }, 200);
  };
  list.onclick = e => {
    const r = e.target.closest('[data-k]'); if (!r) return;
    CF.edit[f] = r.dataset.k; CF.edit.names[f] = r.dataset.n; inp.value = ''; list.style.display = 'none'; cfNow(f);
    if (f === 'owner'){ CF.edit.faction = r.dataset.ty === 'FACT'; const row = $('#cf-rankrow'); if (row) row.style.display = CF.edit.faction ? 'flex' : 'none'; }
  };
}
const _cfOnSelect = W.onSelect;
W.onSelect = list => {
  if (CF.parentFor && list.length === 1 && list[0].key !== CF.parentFor.key){
    const t = CF.parentFor, chosen = list[0]; CF.parentFor = null; $('#hint').style.display = 'none';
    CF.pending = {ref: chosen.key, name: chosen.base};
    return select([t.key]);
  }
  _cfOnSelect(list);
  if (CF.pending && $('#cf-props')){
    const pick = CF.pending; CF.pending = null;
    setTimeout(() => { if (CF.edit){ CF.edit.parent = pick.ref; CF.edit.names.parent = pick.name; cfNow('parent'); } }, 250);
  }
};
async function cfPropsSave(lockable){
  const e = CF.edit, t = e.t, props = {owner: e.owner, disabled: $('#cf-off').checked};
  props.rank = e.faction && $('#cf-rank').value !== '' ? +$('#cf-rank').value : null;
  if (lockable){
    const lv = +$('#cf-lock').value;
    if (lv < 0 && e.key) return toast('A key needs a lock: pick how hard it is.', true);
    props.lock = lv < 0 ? null : {level: lv, key: e.key, leveled: $('#cf-leveled').checked};
  }
  props.parent = e.parent ? {ref: e.parent, opposite: $('#cf-opp').checked} : null;
  try {
    const d = await post('/api/library/props', {cell: t.cell || A.cellId, ref: t.key, props});
    setState(d.state); toast(`Kept: ${t.base}'s settings${e.parent ? ' (what enables it now stays loaded)' : ''}.`);
    await resync();
  } catch (err){ fail(err); }
}

// ---------- a second window ----------
function cfSecondWindow(){
  const c = W.cam.position, cam = [c.x, c.y, c.z, W.yaw, W.pitch].map(v => Math.round(v * 1000) / 1000).join(',');
  const u = new URLSearchParams({win: '2', cam});
  if (A.outside) u.set('world', A.outside.id); else if (A.cellId) u.set('cell', A.cellId);
  window.open('/?' + u, 'folab2-' + Date.now(), 'popup,width=' + Math.round(screen.availWidth * 0.6) + ',height=' + Math.round(screen.availHeight * 0.8));
}
// (the page's own start opens the place in the link; here: the camera, and outside)
async function cfArrive(){
  const q = new URLSearchParams(location.search), cam = (q.get('cam') || '').split(',').map(Number);
  const look = () => { if (cam.length === 5){ W.cam.position.set(cam[0], cam[1], cam[2]); W.yaw = cam[3]; W.pitch = cam[4]; } };
  if (q.get('world')){
    const info = await api('/api/world?id=' + encodeURIComponent(q.get('world')));
    OUT.info = info; tab('left', 'outside');
    if (!OUT.worlds.length) await outsideTab();
    goOutside(info, {p: [cam[0], cam[1], cam[2] - 120, 0, 0, 0]});
    OUT.settle = false;
    look();
  } else {
    for (let i = 0; i < 40 && W.cell === null; i++) await new Promise(r => setTimeout(r, 250));
    look();
  }
  document.title = 'FOLab: ' + ($('#s-place').textContent || 'second window');
}
