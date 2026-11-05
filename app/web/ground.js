// ---------- The Ground brush: shape, paint and tint the ground outside ----------
// Drag on the ground in 3D. Raise and lower (Ctrl: the other way), smooth, flatten to where the stroke began, paint a
// ground texture, tint the ground's own colour. The ground changes as you drag; letting go saves the stroke (every
// cell it touched, and the things standing on the ground moved with it) as one Undo.
// Heights are kept per cell, 33 x 33 points 128 apart, a cell's edge points shared with the cell next door: a change
// works out every point first and then writes them, so both copies of an edge point always agree.
const GB = {on: false, tool: 'raise', size: 768, strength: 4, follow: true, tex: null, color: '#8a6b4a',
            ring: null, stroke: null, texes: null};
try { Object.assign(GB, JSON.parse(localStorage.getItem('folab-ground') || '{}'), {on: false, stroke: null, ring: null, texes: null}); } catch (e) {}
const GB_TOOLS = [['raise', '▲ Raise'], ['lower', '▼ Lower'], ['smooth', '≈ Smooth'], ['flatten', '▬ Flatten'],
                  ['paint', '🖌 Paint'], ['tint', '🎨 Tint'], ['scatter', '🌿 Scatter']];
// the Scatter brush: what the game itself put round here (scatter.py), the set being scattered, what's left out
const SC = {found: null, sets: [], at: null, set: 'plants', off: new Set(), density: 5, remove: false, temp: 0};
function gbSave(){ try { localStorage.setItem('folab-ground', JSON.stringify({tool: GB.tool, size: GB.size, strength: GB.strength, follow: GB.follow, tex: GB.tex, color: GB.color})); } catch (e) {} }

// ---------- the panel ----------
function groundToggle(){ GB.on ? groundOff() : groundOn(); }
async function groundOn(){
  if (!A.outside) return toast('The Ground brush works outside: open a worldspace from the Outside tab.', true);
  if (!A.state.project) return toast('Start a mod first.', true);
  GB.on = true; W.tool = GROUND_TOOL;
  $('#t-ground').classList.add('on');
  let box = $('#gb');
  if (!box){ box = document.createElement('div'); box.id = 'gb'; $('#view').appendChild(box); }
  box.style.display = 'block';
  gbDraw();
  if (!GB.texes) GB.texes = await api('/api/landtex');
  gbDraw();
}
function groundOff(){
  GB.on = false; if (W.tool === GROUND_TOOL) W.tool = null;
  const b = $('#t-ground'); if (b) b.classList.remove('on');
  if ($('#gb')) $('#gb').style.display = 'none';
  if (GB.ring){ W.scene.remove(GB.ring); GB.ring = null; }
}

function gbDraw(){
  const box = $('#gb'); if (!box) return;
  const tex = (GB.texes || []).find(t => t.key === GB.tex);
  box.innerHTML = `<div class="gb-h"><b>Ground</b><span class="note" style="padding:0">drag on the ground</span><button class="btn" data-gb="close">✕</button></div>
    <div class="gb-tools">${GB_TOOLS.map(([k, l]) => `<button class="btn${GB.tool === k ? ' on' : ''}" data-tool="${k}">${l}</button>`).join('')}</div>
    <label class="gb-row">Size <input type="range" min="128" max="4096" step="64" value="${GB.size}" data-gb="size"><input type="number" value="${GB.size}" data-gb="sizen" style="width:64px"></label>
    ${GB.tool === 'paint' || GB.tool === 'tint' || GB.tool === 'raise' || GB.tool === 'lower' || GB.tool === 'smooth' || GB.tool === 'flatten' ? `<label class="gb-row">Strength <input type="range" min="1" max="10" value="${GB.strength}" data-gb="strength"><b>${GB.strength}</b></label>` : ''}
    ${GB.tool === 'paint' ? `<div class="gb-row"><span>Texture</span><b class="gb-tex" title="${esc(tex ? tex.tex : '')}">${esc(tex ? tex.edid : 'none: pick one')}</b></div>
      <input class="find" data-gb="find" placeholder="Search ground textures… (Shift+click the ground: take its)" style="margin:2px 0 4px;width:100%">
      <div class="list gb-list">${(GB.texes || []).filter(t => !GB.q || (t.edid + ' ' + t.tex).toLowerCase().includes(GB.q)).slice(0, 200).map(t =>
        `<div class="row${t.key === GB.tex ? ' on' : ''}" data-tex="${esc(t.key)}"><div>${esc(t.edid)}<small>${esc(t.tex.split('\\').pop())}</small></div></div>`).join('') || '<div class="note">Loading…</div>'}</div>` : ''}
    ${GB.tool === 'scatter' ? scHtml() : ''}
    ${GB.tool === 'tint' ? `<label class="gb-row">Colour <input type="color" value="${GB.color}" data-gb="color"> <span class="note" style="padding:0">Ctrl: back to plain · Shift+click: take the ground's</span></label>` : ''}
    ${GB.tool === 'raise' || GB.tool === 'lower' ? '<div class="note" style="padding:2px 0">Ctrl: the other way</div>' : ''}
    <label class="gb-row"><input type="checkbox" data-gb="follow" ${GB.follow ? 'checked' : ''}> Things on the ground move with it</label>
    <div class="note" style="padding:2px 0">[ and ] size · each stroke is one Undo</div>
    ${hmHtml()}
    ${wtHtml()}`;
  if ($('[data-gb="find"]') && GB.q) $('[data-gb="find"]').value = GB.q;
}
document.addEventListener('click', e => {
  const box = e.target.closest('#gb'); if (!box) return;
  const t = e.target.closest('[data-tool]'), x = e.target.closest('[data-tex]');
  if (t){ GB.tool = t.dataset.tool; gbSave(); gbDraw(); if (GB.tool === 'scatter') scLearn(); }
  const set = e.target.closest('[data-scset]');
  if (set){ SC.set = set.dataset.scset; gbDraw(); }
  if (e.target.dataset.gb === 'relearn'){ SC.at = null; scLearn(); }
  if (x){ GB.tex = x.dataset.tex; gbSave(); gbDraw(); }
  if (e.target.dataset.gb === 'close') groundOff();
  if (e.target.dataset.gb === 'hmload') $('#hm-file').click();
  if (e.target.dataset.gb === 'wtset') wtSet(+$('[data-gb="wth"]').value);
  if (e.target.dataset.gb === 'wtoff') wtSet(null);
  if (e.target.dataset.gb === 'wtgame') wtSet(undefined);
});
document.addEventListener('input', e => {
  if (!e.target.closest('#gb')) return;
  const k = e.target.dataset.gb;
  if (k === 'size' || k === 'sizen'){ GB.size = Math.max(64, Math.min(8192, +e.target.value || 64)); gbSave(); const o = $(`[data-gb="${k === 'size' ? 'sizen' : 'size'}"]`); if (o) o.value = GB.size; }
  if (k === 'strength'){ GB.strength = +e.target.value; e.target.nextElementSibling.textContent = GB.strength; gbSave(); }
  if (k === 'color'){ GB.color = e.target.value; gbSave(); }
  if (k === 'follow'){ GB.follow = e.target.checked; gbSave(); }
  if (k === 'scoff'){ e.target.checked ? SC.off.delete(e.target.value) : SC.off.add(e.target.value); }
  if (k === 'density'){ SC.density = +e.target.value; e.target.nextElementSibling.textContent = SC.density; }
  if (k === 'remove'){ SC.remove = e.target.checked; }
  if (k === 'hmsize'){ HM.size = +e.target.value; gbDraw(); }
  if (k === 'find'){ GB.q = e.target.value.toLowerCase(); const pos = e.target.selectionStart; gbDraw(); const f = $('[data-gb="find"]'); f.focus(); f.setSelectionRange(pos, pos); }
});
addEventListener('keydown', e => {
  if (!GB.on || typing(e)) return;
  if (e.key === '[' || e.key === ']'){
    GB.size = Math.max(64, Math.min(8192, Math.round(GB.size * (e.key === ']' ? 1.25 : 0.8) / 64) * 64));
    gbSave(); gbDraw();
  }
});

// ---------- the ground's points, across cells ----------
function gbCells(){ return [...OUT.cells.values()].filter(c => c.data && c.data.land && c.data.own_land !== false); }
function gbCellAt(x, y){ return OUT.cells.get(Math.floor(x / CELL) + ',' + Math.floor(y / CELL)); }
function gbHeight(x, y){
  // the ground's height at a spot, between its four points
  const c = gbCellAt(x, y); if (!c || !c.data || !c.data.land) return null;
  const h = c.data.land.h, fx = (x - c.x * CELL) / 128, fy = (y - c.y * CELL) / 128;
  const c0 = Math.min(31, Math.floor(fx)), r0 = Math.min(31, Math.floor(fy)), tx = fx - c0, ty = fy - r0;
  const p = (r, cc) => h[r * 33 + cc];
  return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty;
}
// every point within reach: [cell, index, world x, world y, how strongly (1 in the middle, 0 at the edge)]
function gbPoints(px, py, R, side, step){
  const out = [];
  for (const c of gbCells()){
    const x0 = c.x * CELL, y0 = c.y * CELL;
    if (px + R < x0 || px - R > x0 + CELL || py + R < y0 || py - R > y0 + CELL) continue;
    for (let r = 0; r < side; r++) for (let k = 0; k < side; k++){
      const x = x0 + k * step, y = y0 + r * step, d = Math.hypot(x - px, y - py);
      if (d > R) continue;
      const f = 1 - d / R;
      out.push([c, r * side + k, x, y, f * f * (3 - 2 * f)]);
    }
  }
  return out;
}

// ---------- strokes ----------
const GROUND_TOOL = {
  down(e){
    const h = hitThing(e); if (!h || !h.land) return false;
    const c = gbCellAt(h.point.x, h.point.y);
    if (c && c.data && c.data.own_land === false){ toast('This cell borrows its ground from another worldspace: shape it there.', true); return true; }
    if (e.shiftKey && (GB.tool === 'paint' || GB.tool === 'tint')){ gbPick(h.point); return true; }
    if (GB.tool === 'scatter'){
      if (!SC.found) return true;
      GB.stroke = {scatter: true, ctrl: e.ctrlKey, last: 0, placed: [], removed: new Map()};
      scApply(h.point);
      return true;
    }
    if (GB.tool === 'paint' && !GB.tex){ toast('Pick a texture first (or Shift+click the ground to take its).', true); return true; }
    GB.stroke = {cells: new Map(), level: gbHeight(h.point.x, h.point.y), ctrl: e.ctrlKey, last: 0, before: new Map()};
    gbApply(h.point);
    return true;
  },
  move(e){
    if (!GB.stroke) return;
    const now = performance.now(); if (now - GB.stroke.last < 40) return;
    GB.stroke.last = now;
    const h = hitThing(e); if (h && h.land) gbApply(h.point);
  },
  up(){ if (GB.stroke) gbCommit(); },
  hover(e, dragging){ if (!dragging || !GB.stroke) gbRing(e); else gbRing(e); },
};

function gbTouch(c){
  const s = GB.stroke;
  if (!s.cells.has(c)) s.cells.set(c, true);
  if (!s.before.has(c)) s.before.set(c, c.data.land.h.slice());
  (OUT.touched = OUT.touched || new Set()).add(c);
}

function gbApply(at){
  const R = GB.size, s = GB.stroke, k = GB.strength / 10;
  const touched = new Set();
  if (s.scatter) return scApply(at);
  if (['raise', 'lower', 'smooth', 'flatten'].includes(GB.tool)){
    const pts = gbPoints(at.x, at.y, R, 33, 128);
    const sign = (GB.tool === 'raise') !== s.ctrl ? 1 : -1;
    // every new height worked out from the ground as it is, then all written (edge points shared by two cells agree)
    const next = pts.map(([c, i, x, y, f]) => {
      const h = c.data.land.h[i];
      if (GB.tool === 'raise' || GB.tool === 'lower') return h + sign * f * k * 40;
      if (GB.tool === 'flatten') return h + (s.level - h) * f * k * 0.5;
      const n = [[128, 0], [-128, 0], [0, 128], [0, -128]].map(([dx, dy]) => gbHeight(x + dx, y + dy)).filter(v => v !== null);
      return n.length ? h + (n.reduce((a, b) => a + b, 0) / n.length - h) * f * k : h;
    });
    pts.forEach(([c, i], n) => { if (!touched.has(c)){ touched.add(c); gbTouch(c); } c.data.land.h[i] = Math.round(next[n] * 100) / 100; });
  } else if (GB.tool === 'paint'){
    const tex = GB.texes.find(t => t.key === GB.tex);
    for (const c of gbCells()) for (let q = 0; q < 4; q++){
      const qx = q & 1, qy = q >> 1;
      for (const [cc, i, x, y, f] of gbPointsQuarter(c, q, at.x, at.y, R)){
        if (!touched.has(cc)){ touched.add(cc); gbTouch(cc); }
        gbPaintPoint(cc.data.land.q[q], i, tex, f * k * 0.6);
      }
    }
  } else if (GB.tool === 'tint'){
    const want = s.ctrl ? [255, 255, 255] : [1, 3, 5].map(o => parseInt(GB.color.substr(o, 2), 16));
    for (const [c, i, , , f] of gbPoints(at.x, at.y, R, 33, 128)){
      if (!touched.has(c)){ touched.add(c); gbTouch(c); }
      const L = c.data.land;
      if (!L.c) L.c = 'ff'.repeat(33 * 33 * 3);
      let hex = '';
      const cur = [0, 1, 2].map(j => parseInt(L.c.substr((i * 3 + j) * 2, 2), 16));
      for (let j = 0; j < 3; j++) hex += Math.round(cur[j] + (want[j] - cur[j]) * f * k * 0.5).toString(16).padStart(2, '0');
      L.c = L.c.slice(0, i * 6) + hex + L.c.slice(i * 6 + 6);
    }
  }
  for (const c of touched) landRebuild(c);
}

function gbPointsQuarter(c, q, px, py, R){
  const out = [], x0 = c.x * CELL + (q & 1) * 2048, y0 = c.y * CELL + (q >> 1) * 2048;
  if (px + R < x0 || px - R > x0 + 2048 || py + R < y0 || py - R > y0 + 2048) return out;
  for (let r = 0; r < 17; r++) for (let k = 0; k < 17; k++){
    const x = x0 + k * 128, y = y0 + r * 128, d = Math.hypot(x - px, y - py);
    if (d > R) continue;
    const f = 1 - d / R;
    out.push([c, r * 17 + k, x, y, f * f * (3 - 2 * f)]);
  }
  return out;
}

// paint one point of a quarter: the texture shows more there, the layers over it less
function gbPaintPoint(quarter, i, tex, a){
  if (a <= 0) return;
  if (quarter.bkey === tex.key){
    for (const l of quarter.layers) l.a[i] *= (1 - a);
  } else {
    let at = quarter.layers.findIndex(l => l.key === tex.key);
    if (at < 0){
      // a new layer on top; at the most a quarter can have, the one showing least makes way
      quarter.layers = quarter.layers.filter(l => l.a.some(v => v > 0.0005));
      if (quarter.layers.length >= 6){
        const sums = quarter.layers.map(l => l.a.reduce((x, y) => x + y, 0));
        quarter.layers.splice(sums.indexOf(Math.min(...sums)), 1);
      }
      quarter.layers.push({tex: tex.tex, key: tex.key, a: new Array(289).fill(0)});
      at = quarter.layers.length - 1;
    }
    const l = quarter.layers[at];
    l.a[i] = Math.min(1, l.a[i] + a * (1 - l.a[i]));
    for (let j = at + 1; j < quarter.layers.length; j++) quarter.layers[j].a[i] *= (1 - a);
  }
  for (const l of quarter.layers) l.a[i] = Math.round(l.a[i] * 1000) / 1000;
}

// Shift+click: take the texture (the top one showing) or the colour under the brush
function gbPick(at){
  const c = gbCellAt(at.x, at.y); if (!c || !c.data.land) return;
  const lx = at.x - c.x * CELL, ly = at.y - c.y * CELL;
  if (GB.tool === 'tint'){
    const i = Math.round(ly / 128) * 33 + Math.round(lx / 128), L = c.data.land;
    GB.color = L.c ? '#' + L.c.substr(i * 6, 6) : '#ffffff';
  } else {
    const q = (lx >= 2048 ? 1 : 0) + (ly >= 2048 ? 2 : 0), quarter = c.data.land.q[q];
    const i = Math.round((ly - (q >> 1) * 2048) / 128) * 17 + Math.round((lx - (q & 1) * 2048) / 128);
    const top = [...quarter.layers].reverse().find(l => l.a[i] > 0.5);
    GB.tex = top ? top.key : quarter.bkey;
    if (GB.tex && GB.texes && !GB.texes.some(t => t.key === GB.tex)) GB.texes.push({key: GB.tex, edid: GB.tex, tex: top ? top.tex : quarter.base});
  }
  gbSave(); gbDraw();
}

async function gbCommit(){
  const s = GB.stroke; GB.stroke = null;
  if (s.scatter) return scCommit(s);
  const cells = [...s.cells.keys()];
  if (!cells.length) return;
  const ops = cells.map(c => ({op: 'land', cell: c.data.cell, land: c.data.land}));
  // things standing on the ground go up and down with it
  if (GB.follow && ['raise', 'lower', 'smooth', 'flatten'].includes(GB.tool)){
    const before = (c, x, y) => {
      const h = s.before.get(c); if (!h) return null;
      const fx = (x - c.x * CELL) / 128, fy = (y - c.y * CELL) / 128, c0 = Math.min(31, Math.floor(fx)), r0 = Math.min(31, Math.floor(fy)), tx = fx - c0, ty = fy - r0;
      const p = (r, k) => h[r * 33 + k];
      return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty;
    };
    for (const c of cells) for (const t of (c.data.things || [])){
      if (t.state === 'removed') continue;
      const tc = gbCellAt(t.p[0], t.p[1]); if (!tc || !s.before.has(tc)) continue;
      const was = before(tc, t.p[0], t.p[1]), now = gbHeight(t.p[0], t.p[1]);
      if (was === null || now === null || Math.abs(now - was) < 0.5 || Math.abs(t.p[2] - was) > 200) continue;
      const p = t.p.slice(); p[2] = Math.round((p[2] + now - was) * 100) / 100;
      ops.push({op: 'move', cell: t.cell, ref: t.key, p});
    }
  }
  const label = {raise: 'Raise the ground', lower: 'Lower the ground', smooth: 'Smooth the ground', flatten: 'Flatten the ground',
                 paint: 'Paint the ground', tint: 'Tint the ground'}[s.ctrl && GB.tool === 'raise' ? 'lower' : s.ctrl && GB.tool === 'lower' ? 'raise' : GB.tool];
  const d = await edit(label, ops);
  if (d) for (const c of cells) c.data.changed_land = true;
  if (d && typeof mapLandChanged === 'function') mapLandChanged();
  if (d && typeof farLandChanged === 'function') farLandChanged();
}

// the brush's reach, drawn on the ground
function gbRing(e){
  if (!GB.on) return;
  const h = hitThing(e);
  if (!GB.ring){
    GB.ring = new T.LineLoop(new T.BufferGeometry(), new T.LineBasicMaterial({color: 0xf0cd87, depthTest: false, transparent: true, opacity: 0.9}));
    GB.ring.renderOrder = 10; W.scene.add(GB.ring);
  }
  if (!h || !h.land){ GB.ring.visible = false; return; }
  const pts = [];
  for (let i = 0; i < 64; i++){
    const a = i / 64 * Math.PI * 2, x = h.point.x + Math.cos(a) * GB.size, y = h.point.y + Math.sin(a) * GB.size;
    pts.push(x, y, (gbHeight(x, y) ?? h.point.z) + 8);
  }
  GB.ring.geometry.setAttribute('position', new T.Float32BufferAttribute(pts, 3));
  GB.ring.geometry.computeBoundingSphere();
  GB.ring.visible = true;
}


// ---------- Scatter ----------
async function scLearn(){
  const [cx, cy] = camCell(), k = cx + ',' + cy;
  if (SC.at && Math.max(Math.abs(cx - SC.at[0]), Math.abs(cy - SC.at[1])) < 3 && SC.found) return;
  SC.at = [cx, cy];
  const d = await api(`/api/scatter?world=${encodeURIComponent(OUT.world)}&x=${cx}&y=${cy}`);
  SC.found = d.found; SC.sets = d.sets;
  if (!SC.found[SC.set].length) SC.set = (SC.sets.find(([k]) => SC.found[k].length) || [SC.set])[0];
  if (GB.tool === 'scatter') gbDraw();
}
function scHtml(){
  if (!SC.found) return '<div class="note" style="padding:4px 0">Learning what grows round here…</div>';
  const list = SC.found[SC.set] || [], tot = list.reduce((a, b) => a + b.n, 0) || 1;
  return `<div class="gb-tools" style="grid-template-columns:1fr 1fr">${SC.sets.map(([k, l]) =>
      `<button class="btn${SC.set === k ? ' on' : ''}" data-scset="${k}" ${SC.found[k].length ? '' : 'disabled'}>${esc(l)} <small>${SC.found[k].length}</small></button>`).join('')}</div>
    <div class="list gb-list">${list.map(b => `<label class="row" title="${esc(b.model)}"><div><input type="checkbox" data-gb="scoff" value="${esc(b.key)}" ${SC.off.has(b.key) ? '' : 'checked'}> ${esc(b.edid)}
      <small>${Math.round(b.n / tot * 100)}% · size ${b.smin}–${b.smax}${b.tilt > 0.05 ? ' · leans' : ''}</small></div></label>`).join('') || '<div class="note">None of these round here.</div>'}</div>
    <label class="gb-row">Thickness <input type="range" min="1" max="10" value="${SC.density}" data-gb="density"><b>${SC.density}</b></label>
    <label class="gb-row"><input type="checkbox" data-gb="remove" ${SC.remove ? 'checked' : ''}> ✕ Remove (or hold Ctrl): takes back only what the brush put down</label>
    <div class="note" style="padding:2px 0">Learnt from what the game placed within 3 cells. <a href="#" data-gb="relearn">Learn here again</a></div>`;
}

// one dab of the brush: put things down round the spot, kept apart, on the ground; or take scattered ones back
function scApply(at){
  const s = GB.stroke, R = GB.size;
  const list = (SC.found[SC.set] || []).filter(b => !SC.off.has(b.key));
  if (s.ctrl || SC.remove){
    const keys = new Set(list.map(b => b.key));
    for (const g of W.group.children){
      const t = g.userData.thing;
      if (!t.sc || !g.visible || s.removed.has(t.key) || !keys.has(t.bkey)) continue;
      if (Math.hypot(g.position.x - at.x, g.position.y - at.y) > R) continue;
      g.visible = false; s.removed.set(t.key, t);
    }
    return;
  }
  if (!list.length || s.placed.length >= 400) return;
  const tot = list.reduce((a, b) => a + b.n, 0);
  const pick = () => { let r = Math.random() * tot; for (const b of list){ r -= b.n; if (r <= 0) return b; } return list[0]; };
  const apart = 1500 / (SC.density + 1);
  const want = Math.max(1, Math.round(SC.density * R * R / 1.5e6));
  // what's already there, of these kinds, keeps its room
  const near = [];
  const keys = new Set(list.map(b => b.key));
  for (const g of W.group.children){
    const t = g.userData.thing;
    if (g.visible && keys.has(t.bkey) && Math.hypot(g.position.x - at.x, g.position.y - at.y) < R + apart) near.push([g.position.x, g.position.y]);
  }
  for (const t of s.placed) near.push([t.p[0], t.p[1]]);
  let made = 0;
  for (let tries = 0; tries < want * 8 && made < want && s.placed.length < 400; tries++){
    const a = Math.random() * Math.PI * 2, d = Math.sqrt(Math.random()) * R;
    const x = at.x + Math.cos(a) * d, y = at.y + Math.sin(a) * d;
    if (near.some(([px, py]) => Math.hypot(px - x, py - y) < apart)) continue;
    const z = gbHeight(x, y); if (z === null) continue;
    const b = pick();
    const tilt = b.tilt > 0.05 ? b.tilt : 0;
    const p = [x, y, z + Math.min(b.dz, 4), (Math.random() * 2 - 1) * tilt, (Math.random() * 2 - 1) * tilt, Math.random() * Math.PI * 2]
      .map(v => Math.round(v * 1000) / 1000);
    const t = {key: '~sc' + (++SC.temp), bkey: b.key, base: b.edid, type: b.type, name: '', model: b.tree ? '' : b.model, tree: b.tree || undefined, p,
               s: Math.round((b.smin + Math.random() * (b.smax - b.smin)) * 100) / 100, marker: false, state: 'new', sc: true};
    addThing(t, W.token);
    s.placed.push(t); near.push([x, y]); made++;
  }
}

async function scCommit(s){
  const ops = s.placed.map(t => ({op: 'add', cell: A.cellId || (gbCellAt(t.p[0], t.p[1]) || {data: {}}).data.cell, base: t.bkey, p: t.p, s: t.s, sc: true}));
  for (const [k, t] of s.removed) ops.push({op: 'remove', cell: t.cell, ref: k});
  for (const t of s.placed) dropThing(t.key);
  if (!ops.length) return;
  const kindName = (SC.sets.find(([k]) => k === SC.set) || [0, 'things'])[1].toLowerCase();
  const d = await edit(s.placed.length ? `Scatter ${s.placed.length} ${kindName}` : `Take back ${s.removed.size} ${kindName}`, ops);
  if (!d){ for (const [k] of s.removed){ const g = W.byKey.get(k); if (g) g.visible = true; } return; }
  // (a stroke across more cells than the answer covers: every cell on show again)
  if (s.placed.length && !(d.things || []).some(t => t.key.startsWith('+'))) outsideResync();
}


// ---------- Height maps: an area of the ground out as a 16-bit greyscale PNG, and back ----------
const HM = {size: 5};
function hmArea(){
  const [cx, cy] = camCell(), n = HM.size, h = Math.floor((n - 1) / 2);
  return {x: cx - h, y: cy - h, w: n, h: n};
}
function hmHtml(){
  const a = hmArea();
  const url = `/api/heightmap?world=${encodeURIComponent(OUT.world || '')}&x=${a.x}&y=${a.y}&w=${a.w}&h=${a.h}`;
  return `<div class="h" style="padding-left:0;margin-top:8px">Height map</div>
    <label class="gb-row">Area <select data-gb="hmsize">${[1, 3, 5, 9, 16, 32].map(n => `<option value="${n}" ${n === HM.size ? 'selected' : ''}>${n} × ${n} cells</option>`).join('')}</select></label>
    <div class="note" style="padding:0 0 4px">Round the camera: cells ${a.x} to ${a.x + a.w - 1}, ${a.y} to ${a.y + a.h - 1} (${a.w * 32 + 1} pixels across)</div>
    <div class="gb-tools" style="grid-template-columns:1fr 1fr"><a class="btn" href="${url}" download title="A 16-bit greyscale PNG: black the lowest, white the highest. It remembers where it came from.">⤓ Save as PNG</a>
      <button class="btn" data-gb="hmload" title="A height map back: one saved here goes back where it came from">⤒ Load a PNG…</button></div>
    <div class="note" style="padding:0">Work on it in GIMP, Krita, World Machine or Gaea and load it back. The area's edge keeps its heights so it meets the land round it; things on the ground move with it (the tick above). One Undo.</div>
    <input type="file" id="hm-file" accept=".png,image/png" style="display:none">`;
}
document.addEventListener('change', async e => {
  if (e.target.id !== 'hm-file' || !e.target.files.length) return;
  const file = e.target.files[0]; e.target.value = '';
  const buf = new Uint8Array(await file.arrayBuffer());
  let bin = ''; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
  const a = hmArea(), body = {world: OUT.world, data: btoa(bin), follow: GB.follow, x: a.x, y: a.y, w: a.w, h: a.h};
  // (a picture made elsewhere says nothing of its heights: ask what black and white stand for)
  const text = new TextDecoder('latin1').decode(buf.subarray(0, Math.min(buf.length, 4096)));
  if (!text.includes('FOLab\0')){
    const lo = prompt(`This picture didn't come from FOLab: it goes on the area round the camera (${a.w} × ${a.h} cells).\nHow high is black? (game units; Goodsprings is about 8,000)`, '6000');
    if (lo === null) return;
    const hi = prompt('And white?', String(+lo + 4000));
    if (hi === null) return;
    body.low = +lo; body.high = +hi;
  }
  toast('Loading the height map…');
  try {
    const d = await post('/api/heightmap/import', body);
    setState(d.state);
    for (const c of OUT.cells.values()) (OUT.touched = OUT.touched || new Set()).add(c);   // (its area may be anywhere loaded)
    await outsideResync();
    if (typeof mapLandChanged === 'function') mapLandChanged();
    if (typeof farLandChanged === 'function') farLandChanged();
    toast(`Height map loaded: ${d.cells} cell${d.cells === 1 ? '' : 's'} (one Undo)`);
  } catch (err){ fail(err); }
});


// ---------- Water: the cell under the camera's water level ----------
function wtCell(){ const [cx, cy] = camCell(); return OUT.cells.get(cx + ',' + cy); }
function wtHtml(){
  const c = wtCell(); if (!c || !c.data || !c.data.cell) return '';
  const h = c.data.water, low = c.data.land ? Math.round(Math.min(...c.data.land.h)) : 0, shows = h !== null && h > low;
  return `<div class="h" style="padding-left:0;margin-top:8px">Water · cell ${c.x}, ${c.y}</div>
    <div class="note" style="padding:0 0 4px">${shows ? `Water stands at ${Math.round(h)} here.` : 'No water shows here.'} The ground's lowest point is ${low}. The game has one water level a cell: everything in the cell lower than it is under water.</div>
    <label class="gb-row">Level <input type="number" data-gb="wth" value="${Math.round(shows ? h : low + 200)}" style="width:90px"> <button class="btn" data-gb="wtset">Set</button></label>
    <div class="gb-tools" style="grid-template-columns:1fr 1fr"><button class="btn" data-gb="wtoff" title="Back to the world's own level, below all the land">No water</button>
      ${c.data.changed_water ? '<button class="btn" data-gb="wtgame">As the game has it</button>' : ''}</div>`;
}
async function wtSet(h){
  const c = wtCell(); if (!c) return;
  const op = h === undefined ? {op: 'water_revert', cell: c.data.cell} : {op: 'water', cell: c.data.cell, h};
  const d = await edit(h === undefined ? 'Water as the game has it' : h === null ? 'Take the water away' : 'Water at ' + Math.round(h), [op]);
  if (!d) return;
  (OUT.touched = OUT.touched || new Set()).add(c);
  await outsideResync(); gbDraw();
}
// (the Water section follows the cell you're over)
setInterval(() => {
  if (!GB.on || !OUT.world) return;
  const k = camCell().join(',');
  if (k !== GB.cellAt && !(document.activeElement && document.activeElement.closest && document.activeElement.closest('#gb'))){ GB.cellAt = k; gbDraw(); }
}, 700);
