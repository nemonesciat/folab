// ---------- The navmesh by hand, in 3D ----------
// The mesh lies over the ground, a colour for what each triangle is. Click a corner or a triangle to select it (Shift adds),
// drag a corner to move it (Alt: up and down), click an edge (with Edges on) to pick it for Join and Cut. Each change goes
// to the server, which checks the mesh is still sound and refuses if not. Each change is one Undo.
const NT = {on: false, cells: new Map(), obj: null, mode: 'pick', sel: {corners: [], tris: [], edges: []}, drag: null, addPts: [], said: ''};
const NT_COL = {plain: [0.24, 0.95, 0.48], preferred: [0.95, 0.8, 0.3], water: [0.3, 0.6, 0.95], door: [0.95, 0.55, 0.2], cover: [0.75, 0.45, 0.9], sel: [1, 1, 1], game: [0.6, 0.75, 0.6]};

function ntMyCells(){
  if (!A.outside) return A.cellId ? [A.cellId] : [];
  const out = [];
  const cx = Math.floor(W.cam.position.x / 4096), cy = Math.floor(W.cam.position.y / 4096);
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++){
    const c = OUT.cells.get((cx + dx) + ',' + (cy + dy));
    if (c && c.data && c.data.cell) out.push(c.data.cell);
  }
  return out;
}
async function ntLoad(){
  const keys = ntMyCells();
  if (!keys.length){ NT.cells.clear(); return ntRedraw(); }
  const d = await api('/api/w/nav/meshes?cells=' + encodeURIComponent(keys.join('|'))).catch(e => { fail(e); return null; });
  if (!d) return;
  NT.cells.clear();
  for (const c of d.cells) NT.cells.set(c.cell, c);
  ntRedraw();
}
function ntClearSel(){ NT.sel = {corners: [], tris: [], edges: []}; NT.addPts = []; }

function ntRedraw(){
  if (NT.obj){ W.scene.remove(NT.obj); for (const c of NT.obj.children) c.geometry.dispose(); NT.obj = null; }
  if (!NT.on) return;
  const P = [], C = [], L = [], LC = [];
  const pick = [];            // triangle number in the drawing -> [cell, mesh, tri]
  const selTri = new Set(NT.sel.tris.map(s => s.join('|')));
  const selEdge = new Set(NT.sel.edges.map(s => s.join('|')));
  for (const c of NT.cells.values()){
    c.meshes.forEach((m, mi) => {
      if (m.stub) return;
      const doors = new Set(m.doors.map(d => d[1]));
      m.tris.forEach((t, ti) => {
        const a = m.verts[t[0]], b = m.verts[t[1]], cc = m.verts[t[2]];
        const col = selTri.has([c.cell, mi, ti].join('|')) ? NT_COL.sel : doors.has(ti) ? NT_COL.door : t[7] ? NT_COL.cover : t[6] & 0x200 ? NT_COL.water : t[6] & 0x40 ? NT_COL.preferred : c.source === 'mod' ? NT_COL.plain : NT_COL.game;
        for (const v of [a, b, cc]){ P.push(v[0], v[1], v[2] + 5); C.push(col[0], col[1], col[2]); }
        pick.push([c.cell, mi, ti]);
        for (let i = 0; i < 3; i++){
          const u = m.verts[t[i]], w = m.verts[t[(i + 1) % 3]];
          const linked = t[6] >> i & 1, open = !linked && t[3 + i] === 0xFFFF;
          // (each inner edge is drawn from both sides: once will do)
          if (!linked && !open && t[i] > t[(i + 1) % 3]) continue;
          const on = selEdge.has([c.cell, mi, ti, i].join('|'));
          const e = on ? [1, 1, 1] : linked ? [0.3, 0.7, 1] : open ? [1, 0.3, 0.25] : [0.1, 0.5, 0.25];
          L.push(u[0], u[1], u[2] + 7, w[0], w[1], w[2] + 7);
          LC.push(...e, ...e);
        }
      });
    });
  }
  const g = new T.Group();
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(P, 3));
  geo.setAttribute('color', new T.Float32BufferAttribute(C, 3));
  const mesh = new T.Mesh(geo, new T.MeshBasicMaterial({vertexColors: true, transparent: true, opacity: 0.32, side: T.DoubleSide, depthWrite: false}));
  mesh.userData.pick = pick;
  const lgeo = new T.BufferGeometry();
  lgeo.setAttribute('position', new T.Float32BufferAttribute(L, 3));
  lgeo.setAttribute('color', new T.Float32BufferAttribute(LC, 3));
  const lines = new T.LineSegments(lgeo, new T.LineBasicMaterial({vertexColors: true}));
  lines.raycast = () => {};
  g.add(mesh); g.add(lines);
  // the selected corners
  if (NT.sel.corners.length){
    const pg = new T.BufferGeometry(), pts = [];
    for (const [ck, mi, v] of NT.sel.corners){ const m = ntMesh(ck, mi); if (m && m.verts[v]) pts.push(m.verts[v][0], m.verts[v][1], m.verts[v][2] + 8); }
    pg.setAttribute('position', new T.Float32BufferAttribute(pts, 3));
    const dots = new T.Points(pg, new T.PointsMaterial({color: 0xffffff, size: 9, sizeAttenuation: false}));
    dots.raycast = () => {};
    g.add(dots);
  }
  NT.obj = g; NT.pickMesh = mesh;
  W.scene.add(g);
}
const ntMesh = (ck, mi) => { const c = NT.cells.get(ck); return c && c.meshes[mi]; };

// ---------- picking ----------
function ntRay(e){
  const r = W.ren.domElement.getBoundingClientRect();
  const ray = new T.Raycaster();
  ray.setFromCamera(new T.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), W.cam);
  return ray;
}
function ntScreen(v){
  const r = W.ren.domElement.getBoundingClientRect();
  const p = new T.Vector3(v[0], v[1], v[2]).project(W.cam);
  return p.z > 1 ? null : [(p.x + 1) / 2 * r.width + r.left, (1 - p.y) / 2 * r.height + r.top];
}
function ntPick(e){
  // what's under the mouse: a triangle, the nearest of its corners and edges
  if (!NT.pickMesh) return null;
  const hit = ntRay(e).intersectObject(NT.pickMesh)[0];
  if (!hit) return null;
  const [ck, mi, ti] = NT.pickMesh.userData.pick[hit.faceIndex];
  const m = ntMesh(ck, mi), t = m.tris[ti];
  let corner = null, bd = 13;
  for (const v of t.slice(0, 3)){
    const s = ntScreen(m.verts[v]); if (!s) continue;
    const d = Math.hypot(s[0] - e.clientX, s[1] - e.clientY);
    if (d < bd){ bd = d; corner = v; }
  }
  let edge = 0, be = 1e9;
  for (let i = 0; i < 3; i++){
    const a = ntScreen(m.verts[t[i]]), b = ntScreen(m.verts[t[(i + 1) % 3]]); if (!a || !b) continue;
    const dx = b[0] - a[0], dy = b[1] - a[1], f = Math.max(0, Math.min(1, ((e.clientX - a[0]) * dx + (e.clientY - a[1]) * dy) / (dx * dx + dy * dy || 1)));
    const d = Math.hypot(a[0] + f * dx - e.clientX, a[1] + f * dy - e.clientY);
    if (d < be){ be = d; edge = i; }
  }
  return {ck, mi, ti, corner, edge, point: hit.point};
}
// a spot on the plane through the height z, under the mouse
function ntPlane(e, z){
  const ray = ntRay(e).ray;
  if (Math.abs(ray.direction.z) < 1e-4) return null;
  const f = (z - ray.origin.z) / ray.direction.z;
  return f > 0 ? [ray.origin.x + ray.direction.x * f, ray.origin.y + ray.direction.y * f] : null;
}

// a spot on the ground under the mouse (or, inside, the floor; or level with the corners already clicked)
function ntGround(e){
  const had = NT.addSpots && NT.addSpots[0];
  const out = A.outside && typeof gbHeight === 'function';
  let z = had ? had[2] : out ? (gbHeight(W.cam.position.x, W.cam.position.y) ?? 0) : (W.floorZ || 0);
  let p = ntPlane(e, z);
  if (!p) return null;
  if (out && !had){ const g = gbHeight(p[0], p[1]); if (g !== null && g !== undefined){ z = g; p = ntPlane(e, z) || p; } }
  return [p[0], p[1], z];
}

// ---------- the tool ----------
const NAV_TOOL = {
  down(e){
    const h = ntPick(e);
    if (NT.mode === 'add'){
      if (h && h.corner !== null && (!NT.addAt || (NT.addAt[0] === h.ck && NT.addAt[1] === h.mi))){
        NT.addAt = [h.ck, h.mi];
        NT.addPts.push(h.corner);
        NT.addSpots = (NT.addSpots || []).concat([ntMesh(h.ck, h.mi).verts[h.corner]]);
      } else {
        const spot = h ? [h.point.x, h.point.y, h.point.z - 5] : ntGround(e);
        if (!spot) return true;
        if (!NT.addAt){
          const key = A.outside ? ntCellAt(spot) : A.cellId;
          if (!key) return true;
          NT.addAt = [key, 0];
        }
        NT.addPts.push(spot);
        NT.addSpots = (NT.addSpots || []).concat([spot]);
      }
      if (NT.addPts.length === 3){
        const pts = NT.addPts, at = NT.addAt;
        NT.addPts = []; NT.addSpots = []; NT.addAt = null;
        ntDo({do: 'add', cell: at[0], mesh: at[1], pts});
      }
      ntPanel();
      return true;
    }
    if (!h){ if (!e.shiftKey){ ntClearSel(); ntRedraw(); ntPanel(); } return false; }
    const sel = NT.sel;
    if (NT.mode === 'edge'){
      const k = [h.ck, h.mi, h.ti, h.edge];
      const i = sel.edges.findIndex(x => x.join('|') === k.join('|'));
      if (i >= 0) sel.edges.splice(i, 1); else { if (sel.edges.length >= 2) sel.edges.shift(); sel.edges.push(k); }
    } else if (h.corner !== null){
      const k = [h.ck, h.mi, h.corner];
      if (!e.shiftKey){ sel.corners = []; sel.tris = []; }
      if (!sel.corners.some(x => x.join('|') === k.join('|'))) sel.corners.push(k);
      const m = ntMesh(h.ck, h.mi);
      NT.drag = {start: sel.corners.map(([c, mi, v]) => ({c, mi, v, from: [...ntMesh(c, mi).verts[v]]})), y0: e.clientY, z: m.verts[h.corner][2], at: ntPlane(e, m.verts[h.corner][2]), alt: e.altKey, moved: false};
    } else {
      const k = [h.ck, h.mi, h.ti];
      if (!e.shiftKey){ sel.corners = []; sel.tris = []; }
      const i = sel.tris.findIndex(x => x.join('|') === k.join('|'));
      if (i >= 0) sel.tris.splice(i, 1); else sel.tris.push(k);
    }
    ntRedraw(); ntPanel();
    return true;
  },
  move(e){
    const d = NT.drag; if (!d) return;
    if (d.alt){
      const up = (d.y0 - e.clientY) * (W.cam.position.distanceTo(new T.Vector3(...d.start[0].from)) / 500);
      for (const s of d.start) ntMesh(s.c, s.mi).verts[s.v] = [s.from[0], s.from[1], s.from[2] + up];
      d.moved = Math.abs(up) > 1;
    } else {
      const p = ntPlane(e, d.z); if (!p || !d.at) return;
      const ox = p[0] - d.at[0], oy = p[1] - d.at[1];
      for (const s of d.start) ntMesh(s.c, s.mi).verts[s.v] = [s.from[0] + ox, s.from[1] + oy, s.from[2]];
      d.moved = Math.hypot(ox, oy) > 1;
    }
    ntRedraw();
  },
  up(){
    const d = NT.drag; NT.drag = null; if (!d || !d.moved) return;
    const moves = {};
    for (const s of d.start) (moves[s.c + '|' + s.mi] = moves[s.c + '|' + s.mi] || {})[s.v] = ntMesh(s.c, s.mi).verts[s.v].map(v => Math.round(v * 100) / 100);
    const k = Object.keys(moves)[0], [cell, mesh] = k.split('|');
    ntDo({do: 'move', cell, mesh: +mesh, moves: moves[k]});
  },
  hover(){},
};
function ntCellAt(p){
  const c = OUT.cells.get(Math.floor(p[0] / 4096) + ',' + Math.floor(p[1] / 4096));
  return c && c.data ? c.data.cell : null;
}
async function ntDo(a){
  const d = await post('/api/w/nav/edit', a).catch(e => { fail(e); ntLoad(); return null; });
  if (!d) return null;
  setState(d.state);
  NT.said = '';
  if (a.do !== 'move' && a.do !== 'mark' && a.do !== 'cover') ntClearSel();
  await ntLoad();
  ntPanel();
  return d;
}

// ---------- the panel ----------
function navToolOn(){
  if (NT.on) return;
  if (typeof M !== 'undefined' && M.on) mapShow(false);
  if (typeof wtToggle === 'function' && WT.on) wtToggle(false);
  NT.on = true; NT.prevTool = W.tool; W.tool = NAV_TOOL; ntClearSel();
  let box = $('#nt');
  if (!box){ box = document.createElement('div'); box.id = 'nt'; box.style.cssText = 'position:absolute;top:54px;right:10px;width:270px;background:var(--panel);border:1px solid var(--line2);border-radius:10px;padding:8px 10px;z-index:5;font-size:13px'; $('#view').appendChild(box); }
  box.style.display = 'block';
  ntPanel(); ntLoad();
  NT.timer = setInterval(() => { const k = ntMyCells().join('|'); if (k !== NT.lastKeys){ NT.lastKeys = k; if (!NT.drag) ntLoad(); } }, 1500);
}
function navToolOff(){
  NT.on = false; clearInterval(NT.timer);
  if (W.tool === NAV_TOOL) W.tool = NT.prevTool || null;
  const box = $('#nt'); if (box) box.style.display = 'none';
  ntRedraw();
}
function ntTrisByMesh(){
  const by = {};
  for (const [c, mi, ti] of NT.sel.tris) (by[c + '|' + mi] = by[c + '|' + mi] || []).push(ti);
  return Object.entries(by).map(([k, tris]) => { const [cell, mesh] = k.split('|'); return {cell, mesh: +mesh, tris}; });
}
function ntPanel(){
  const box = $('#nt'); if (!box || !NT.on) return;
  const S = NT.sel, multi = [...NT.cells.values()].some(c => c.meshes.length > 1);
  const mineAny = [...NT.cells.values()].some(c => c.source === 'mod');
  box.innerHTML = `<div style="display:flex;align-items:center;gap:6px"><b>Navmesh by hand</b><button class="btn" id="nt-x" style="margin-left:auto">Done</button></div>
    <div class="seg" style="margin:6px 0"><button class="btn ${NT.mode === 'pick' ? 'on' : ''}" data-m="pick" title="Click a corner or a triangle; drag a corner (Alt: up and down)">Corners &amp; triangles</button><button class="btn ${NT.mode === 'edge' ? 'on' : ''}" data-m="edge" title="Click edges, for Join and Cut">Edges</button><button class="btn ${NT.mode === 'add' ? 'on' : ''}" data-m="add" title="Click three spots, or corners">Add</button></div>
    <div class="note" style="padding:2px 0">${NT.mode === 'add' ? `Click three corners or spots: ${NT.addPts.length} of 3.` : `${S.corners.length} corners, ${S.tris.length} triangles, ${S.edges.length} edges picked.`}</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;margin:6px 0">
      <button class="btn" id="nt-del" ${S.tris.length ? '' : 'disabled'} title="Delete the picked triangles">✕ Delete</button>
      <button class="btn" id="nt-join" ${S.edges.length === 2 ? '' : 'disabled'} title="Two free edges become joined">⛓ Join</button>
      <button class="btn" id="nt-cut" ${S.edges.length ? '' : 'disabled'} title="Whatever's across this edge stops being joined">✂ Cut</button>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;margin:6px 0">
      <button class="btn" id="nt-pref" ${S.tris.length ? '' : 'disabled'} title="Characters choose these first: paths, roads">★ Preferred</button>
      <button class="btn" id="nt-wat" ${S.tris.length ? '' : 'disabled'} title="Marked as in water">≈ Water</button>
      <button class="btn" id="nt-cov" ${S.tris.length ? '' : 'disabled'} title="Characters can use this as cover in a fight">▣ Cover</button>
    </div>
    <div class="note" style="padding:2px 0"><span style="color:#3df27a">■</span> the mod's <span style="color:#9fbf9f">■</span> the game's <span style="color:#f2cc4d">■</span> preferred <span style="color:#4d99f2">■</span> water <span style="color:#f28c33">■</span> by a door <span style="color:#bf73e6">■</span> cover<br>Edges: <span style="color:#ff4d40">■</span> open <span style="color:#4db3ff">■</span> joined to another mesh or a ledge.${multi ? '<br>Some cells here have several meshes.' : ''}</div>
    ${mineAny ? '<div class="note" style="padding:2px 0">Generating a cell again replaces what you\'ve done by hand there.</div>' : ''}`;
  box.querySelectorAll('[data-m]').forEach(b => b.onclick = () => { NT.mode = b.dataset.m; ntClearSel(); NT.addSpots = []; NT.addAt = null; ntRedraw(); ntPanel(); });
  box.querySelector('#nt-x').onclick = navToolOff;
  box.querySelector('#nt-del').onclick = async () => { for (const g of ntTrisByMesh()) await ntDo({do: 'delete', ...g}); };
  box.querySelector('#nt-join').onclick = () => ntDo({do: 'join', cell: S.edges[0][0], a: S.edges[0], b: S.edges[1]});
  box.querySelector('#nt-cut').onclick = async () => { for (const [cell, mesh, tri, edge] of S.edges) await ntDo({do: 'cut', cell, mesh, tri, edge}); };
  const mark = flag => async () => {
    for (const g of ntTrisByMesh()){
      const m = ntMesh(g.cell, g.mesh), bit = flag === 'water' ? 0x200 : 0x40, on = !g.tris.every(t => m.tris[t][6] & bit);
      await ntDo({do: 'mark', ...g, flag, on});
    }
  };
  box.querySelector('#nt-pref').onclick = mark('preferred');
  box.querySelector('#nt-wat').onclick = mark('water');
  box.querySelector('#nt-cov').onclick = async () => {
    for (const g of ntTrisByMesh()){
      const m = ntMesh(g.cell, g.mesh);
      for (const tri of g.tris) await ntDo({do: 'cover', cell: g.cell, mesh: g.mesh, tri, value: m.tris[tri][7] ? 0 : 31});
    }
  };
}
addEventListener('keydown', e => {
  if (!NT.on || typing(e)) return;
  if (e.key === 'Escape'){ if (NT.addPts.length || NT.sel.tris.length || NT.sel.corners.length || NT.sel.edges.length){ ntClearSel(); NT.addSpots = []; NT.addAt = null; ntRedraw(); ntPanel(); } else navToolOff(); e.stopPropagation(); }
  if (e.key === 'Delete' && NT.sel.tris.length){ e.stopPropagation(); e.preventDefault(); $('#nt-del').click(); }
}, true);
// (after an undo, the mesh on the server is another one)
{ const was = setState; setState = s => { was(s); if (NT.on && !NT.drag){ const k = s && s.project && s.project.undo; if (k !== NT.lastUndo){ NT.lastUndo = k; ntLoad(); } } }; }
// the Kit tab's place: a button of its own
{ const was = navDraw; navDraw = async () => { await was(); const box = $('#nav-box'); if (box && A.cellId && !A.outside && !$('#nav-hand')){ const b = document.createElement('button'); b.className = 'btn'; b.id = 'nav-hand'; b.textContent = '✎ Edit by hand'; b.style.marginTop = '6px'; b.onclick = navToolOn; box.appendChild(b); } }; }
