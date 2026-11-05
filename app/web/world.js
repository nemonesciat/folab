// ---------- the 3D world view ----------
// One place the way the game lays it out (every thing's mesh at its position, turn and scale, textured from the
// game's archives), and the hands to change it: select, move, turn, drop down, place new things. Game units, Z up.
// It knows nothing of the server: app.js hands it things and listens for what the user did (W.on*).
const T = THREE;
const W = {scene: null, cam: null, ren: null, group: null, models: {}, mats: {}, tex: {}, yaw: 0, pitch: -0.3,
           keys: {}, byKey: new Map(), cell: null, token: 0, sel: null, box: null, gizmo: null, mode: 'translate',
           placing: null, show: {markers: false, removed: false},
           onSelect: () => {}, onMove: () => {}, onPlace: () => {}, onHover: () => {}};

function api(path){ return fetch(path).then(r => { if (!r.ok) throw new Error(path + ' ' + r.status); return r.json(); }); }

// ---------- textures (a few at a time; the same file is fetched once) ----------
const TQ = {active: 0, max: 8, waiting: []};
function texNext(){ while (TQ.active < TQ.max && TQ.waiting.length){ TQ.active++; TQ.waiting.shift()(); } }
function texture(path){
  if (W.tex[path]) return W.tex[path];
  W.tex[path] = new Promise(done => {
    TQ.waiting.push(() => new T.DDSLoader().load('/api/file?path=' + encodeURIComponent(path), tex => {
      // a DDS whose mip chain stops early draws black in WebGL: keep only the top level then
      const full = Math.floor(Math.log2(Math.max(tex.image.width || 1, tex.image.height || 1))) + 1;
      if (!tex.mipmaps || tex.mipmaps.length < full){ tex.minFilter = T.LinearFilter; tex.generateMipmaps = false; if (tex.mipmaps) tex.mipmaps = tex.mipmaps.slice(0, 1); }
      tex.wrapS = tex.wrapT = T.RepeatWrapping;
      TQ.active--; texNext(); done(tex);
    }, undefined, () => { TQ.active--; texNext(); done(null); }));
    texNext();
  });
  return W.tex[path];
}

function material(tex, alpha, double){
  const k = tex + '|' + alpha + '|' + double;
  if (W.mats[k]) return W.mats[k];
  // plain sand colour until the texture arrives (and for the few shapes that have none)
  const m = new T.MeshLambertMaterial({color: 0xb8a888, side: double || alpha === 'blend' ? T.DoubleSide : T.FrontSide});
  if (alpha === 'test') m.alphaTest = 0.5;
  if (alpha === 'blend'){ m.transparent = true; m.depthWrite = false; if (!tex) m.opacity = 0.25; }
  if (tex) texture(tex).then(t => { if (t){ m.map = t; m.color.set(0xffffff); m.needsUpdate = true; } });
  return W.mats[k] = m;
}

// ---------- meshes: built once per file, shared by every thing that uses it ----------
function model(path){
  if (!W.models[path]) W.models[path] = api('/api/mesh?path=' + encodeURIComponent(path)).then(d => {
    const parts = [];
    for (const s of d.shapes || []){
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.Float32BufferAttribute(s.p, 3));
      if (s.uv.length === s.p.length / 3 * 2) g.setAttribute('uv', new T.Float32BufferAttribute(s.uv, 2));
      g.setIndex(s.i);
      g.computeVertexNormals();
      g.computeBoundingBox();
      parts.push([g, material(s.tex, s.alpha, s.double), s.alpha === 'blend']);
    }
    return parts;
  }).catch(() => []);
  return W.models[path];
}

// ---------- scene ----------
function worldInit(box){
  W.box = box;
  W.ren = new T.WebGLRenderer({antialias: true});
  W.ren.setPixelRatio(window.devicePixelRatio);
  box.appendChild(W.ren.domElement);
  W.scene = new T.Scene();
  W.scene.background = new T.Color(0x0e0c0a);
  W.cam = new T.PerspectiveCamera(70, 1, 4, 60000);
  W.cam.up.set(0, 0, 1);
  W.scene.add(new T.HemisphereLight(0xfff1dd, 0x3a3428, 0.85));
  const sun = new T.DirectionalLight(0xffffff, 0.45); sun.position.set(0.4, -0.6, 1); W.scene.add(sun);
  W.lamp = new T.PointLight(0xffe2b0, 0.6, 3000); W.scene.add(W.lamp);
  W.outline = new T.Box3Helper(new T.Box3(), 0xf0cd87); W.outline.visible = false; W.scene.add(W.outline);
  W.gizmo = new T.TransformControls(W.cam, W.ren.domElement);
  W.gizmo.setSize(0.9);
  W.gizmo.addEventListener('dragging-changed', e => { W.dragging = e.value; if (!e.value) commitSelected('Move'); });
  W.gizmo.addEventListener('objectChange', () => outlineSel());
  W.scene.add(W.gizmo);
  const size = () => { const w = box.clientWidth, h = box.clientHeight; W.ren.setSize(w, h); W.cam.aspect = w / Math.max(1, h); W.cam.updateProjectionMatrix(); };
  new ResizeObserver(size).observe(box); size();
  controls(W.ren.domElement);
  let last = performance.now();
  const frame = now => {
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    move(dt);
    W.lamp.position.copy(W.cam.position);
    W.ren.render(W.scene, W.cam);
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

function look(){
  const d = new T.Vector3(Math.cos(W.pitch) * Math.cos(W.yaw), Math.cos(W.pitch) * Math.sin(W.yaw), Math.sin(W.pitch));
  W.cam.lookAt(W.cam.position.clone().add(d));
  return d;
}

function move(dt){
  const k = W.keys, speed = (k.Shift ? 2400 : 700) * dt;
  if (!k.Control){
    const f = new T.Vector3(Math.cos(W.yaw), Math.sin(W.yaw), 0), r = new T.Vector3(Math.sin(W.yaw), -Math.cos(W.yaw), 0);
    const p = W.cam.position;
    if (k.w) p.addScaledVector(f, speed); if (k.s) p.addScaledVector(f, -speed);
    if (k.d) p.addScaledVector(r, speed); if (k.a) p.addScaledVector(r, -speed);
    if (k.e) p.z += speed; if (k.q) p.z -= speed;
  }
  look();
}

function ray(e){
  const rect = W.ren.domElement.getBoundingClientRect(), r = new T.Raycaster();
  r.setFromCamera({x: (e.clientX - rect.left) / rect.width * 2 - 1, y: -(e.clientY - rect.top) / rect.height * 2 + 1}, W.cam);
  return r;
}

function visibleGroups(except){ return W.group ? W.group.children.filter(g => g.visible && g !== except) : []; }

function hitThing(e){
  const hit = ray(e).intersectObjects(visibleGroups(), true)[0];
  if (!hit) return null;
  let o = hit.object; while (o && !o.userData.thing) o = o.parent;
  return o ? {group: o, point: hit.point} : null;
}

function controls(el){
  let drag = null;
  el.addEventListener('pointerdown', e => {
    if (W.dragging) return;
    drag = {x: e.clientX, y: e.clientY, moved: 0, button: e.button};
    el.setPointerCapture(e.pointerId);
  });
  el.addEventListener('pointermove', e => {
    if (W.placing) placeGhost(e);
    if (!drag || W.dragging) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
    W.yaw -= dx * 0.005; W.pitch = Math.max(-1.55, Math.min(1.55, W.pitch - dy * 0.005));
  });
  el.addEventListener('pointerup', e => {
    const d = drag; drag = null;
    if (!d || d.moved > 4 || W.gizmoUsed){ W.gizmoUsed = false; return; }
    if (d.button === 2){ if (W.placing) stopPlacing(); return; }
    if (W.placing) return placeAt(e);
    const h = hitThing(e);
    select(h ? h.group.userData.thing.key : null);
  });
  el.addEventListener('contextmenu', e => e.preventDefault());
  el.addEventListener('wheel', e => { e.preventDefault(); W.cam.position.addScaledVector(look(), -Math.sign(e.deltaY) * (W.keys.Shift ? 800 : 200)); }, {passive: false});
  W.gizmo.addEventListener('mouseDown', () => { W.gizmoUsed = true; });
  addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox' || e.target.tagName === 'SELECT') return;
    W.keys[e.key.length === 1 ? e.key.toLowerCase() : e.key] = true;
  });
  addEventListener('keyup', e => { W.keys[e.key.length === 1 ? e.key.toLowerCase() : e.key] = false; });
  addEventListener('blur', () => { W.keys = {}; });
}

// ---------- things ----------
function setTransform(g, t){
  g.position.set(t.p[0], t.p[1], t.p[2]);
  g.rotation.set(-t.p[3], -t.p[4], -t.p[5], 'XYZ');      // the game turns the other way round each axis
  g.scale.setScalar(t.s || 1);
}

function thingVisible(t){ return (!t.marker || W.show.markers) && (t.state !== 'removed' || W.show.removed); }

async function addThing(t, token){
  const g = new T.Group();
  g.userData.thing = t;
  setTransform(g, t);
  g.visible = thingVisible(t);
  W.group.add(g);
  W.byKey.set(t.key, g);
  const parts = await model(t.model);
  if (token !== W.token || !g.parent) return g;
  for (const [geo, mat, blend] of parts){ const m = new T.Mesh(geo, mat); if (blend) m.renderOrder = 1; g.add(m); }
  if (t.state === 'removed') ghostly(g, true);
  if (W.sel === g) outlineSel();
  return g;
}

// a removed thing, when shown, is drawn see-through red
const REMOVED_MAT = new T.MeshBasicMaterial({color: 0xe0705b, transparent: true, opacity: 0.25, depthWrite: false});
function ghostly(g, on){
  g.traverse(m => { if (!m.isMesh) return; if (on){ m.userData.mat = m.userData.mat || m.material; m.material = REMOVED_MAT; } else if (m.userData.mat) m.material = m.userData.mat; });
}

function updateThing(t){
  const g = W.byKey.get(t.key);
  if (!g) return addThing(t, W.token);
  const was = g.userData.thing.state;
  g.userData.thing = t;
  setTransform(g, t);
  g.visible = thingVisible(t);
  if ((was === 'removed') !== (t.state === 'removed')) ghostly(g, t.state === 'removed');
  if (W.sel === g){ if (!g.visible) select(null); else outlineSel(); }
}

function dropThing(key){
  const g = W.byKey.get(key);
  if (!g) return;
  if (W.sel === g) select(null);
  W.group.remove(g); W.byKey.delete(key);
}

// ---------- a cell ----------
async function openCell(c, onProgress){
  const token = ++W.token;
  select(null);
  if (W.group) W.scene.remove(W.group);
  W.group = new T.Group(); W.scene.add(W.group);
  W.byKey = new Map();
  W.cell = c;
  // start where the game's console "coc" would put you (its arrival marker), else beside the thing nearest the
  // middle of the place, at eye height
  const arrive = ['COCMarkerHeading', 'XMarkerHeading'].map(b => c.things.find(t => t.base === b)).find(Boolean);
  let at = arrive;
  if (!at){
    const solid = c.things.filter(t => !t.marker && t.type === 'STAT');
    const mid = new T.Box3().setFromPoints(solid.map(t => new T.Vector3(t.p[0], t.p[1], t.p[2]))).getCenter(new T.Vector3());
    at = solid.reduce((b, t) => !b || mid.distanceToSquared(new T.Vector3(t.p[0], t.p[1], t.p[2])) < mid.distanceToSquared(new T.Vector3(b.p[0], b.p[1], b.p[2])) ? t : b, null);
  }
  if (at){ W.cam.position.set(at.p[0], at.p[1], at.p[2] + 120); W.yaw = Math.PI / 2 - (arrive ? at.p[5] : 0); W.pitch = -0.1; }
  let done = 0;
  await Promise.all(c.things.map(t => addThing(t, token).then(() => { done++; if (onProgress && token === W.token) onProgress(done, c.things.length); })));
}

// the cell again as the server now has it (after an undo, say): move, add and drop what differs
function syncCell(things){
  const seen = new Set();
  for (const t of things){ seen.add(t.key); const g = W.byKey.get(t.key); if (!g || JSON.stringify(g.userData.thing) !== JSON.stringify(t)) updateThing(t); }
  for (const k of [...W.byKey.keys()]) if (!seen.has(k)) dropThing(k);
}

function setShow(what, on){
  W.show[what] = on;
  for (const g of W.byKey.values()) g.visible = thingVisible(g.userData.thing);
  if (W.sel && !W.sel.visible) select(null);
}

// ---------- selection ----------
function outlineSel(){
  if (!W.sel){ W.outline.visible = false; return; }
  W.sel.updateMatrixWorld(true);
  const b = new T.Box3().setFromObject(W.sel);
  if (b.isEmpty()) b.setFromCenterAndSize(W.sel.position, new T.Vector3(16, 16, 16));
  W.outline.box.copy(b); W.outline.visible = true;
}

function select(key){
  const g = key ? W.byKey.get(key) : null;
  W.sel = g || null;
  if (g && g.visible) W.gizmo.attach(g); else W.gizmo.detach();
  outlineSel();
  W.onSelect(g ? g.userData.thing : null);
}

function setMode(m){ W.mode = m; W.gizmo.setMode(m); }
function setSnap(grid, angle){
  W.gizmo.setTranslationSnap(grid > 0 ? grid : null);
  W.gizmo.setRotationSnap(angle > 0 ? angle * Math.PI / 180 : null);
}

// the selected thing's position as the game writes it
function gameP(g){
  return [g.position.x, g.position.y, g.position.z, -g.rotation.x, -g.rotation.y, -g.rotation.z].map(v => Math.round(v * 10000) / 10000);
}

function commitSelected(label){
  const g = W.sel;
  if (!g) return;
  const t = g.userData.thing, p = gameP(g);
  if (p.every((v, i) => Math.abs(v - t.p[i]) < 1e-4)) return;
  W.onMove(t, p, label);
}

function focusSel(){
  if (!W.sel) return;
  const b = new T.Box3().setFromObject(W.sel), c = b.getCenter(new T.Vector3()), r = Math.max(120, b.getSize(new T.Vector3()).length());
  const d = look();
  W.cam.position.copy(c).addScaledVector(d, -r * 1.2);
}

// set g down on whatever is under it (or the floor of the first thing below its middle)
function dropDown(g){
  g.updateMatrixWorld(true);
  const b = new T.Box3().setFromObject(g);
  if (b.isEmpty()) return null;
  const c = b.getCenter(new T.Vector3());
  const r = new T.Raycaster(new T.Vector3(c.x, c.y, b.min.z + 1), new T.Vector3(0, 0, -1), 0, 20000);
  const hit = r.intersectObjects(visibleGroups(g), true)[0];
  if (!hit) return null;
  return g.position.z - (b.min.z - hit.point.z);
}

// ---------- placing new things ----------
async function startPlacing(item){
  W.placing = item;
  select(null);
  const parts = await model(item.model);
  if (W.placing !== item) return;
  if (W.ghost) W.scene.remove(W.ghost);
  const g = new T.Group();
  for (const [geo, mat] of parts) g.add(new T.Mesh(geo, mat));
  g.traverse(m => { if (m.isMesh) m.raycast = () => {}; });
  const b = new T.Box3().setFromObject(g);
  W.ghostLift = b.isEmpty() ? 0 : -b.min.z;          // sit its underside on the surface
  g.visible = false;
  W.ghost = g; W.scene.add(g);
}

function stopPlacing(){
  W.placing = null;
  if (W.ghost){ W.scene.remove(W.ghost); W.ghost = null; }
  W.onPlace(null);
}

function placeGhost(e){
  if (!W.ghost) return;
  const hit = ray(e).intersectObjects(visibleGroups(), true)[0];
  if (!hit){ W.ghost.visible = false; return; }
  const grid = W.gridSnap || 0, s = v => grid ? Math.round(v / grid) * grid : v;
  W.ghost.position.set(s(hit.point.x), s(hit.point.y), hit.point.z + (hit.face && hit.face.normal.z > 0.5 ? W.ghostLift : 0));
  W.ghost.visible = true;
}

function placeAt(e){
  placeGhost(e);
  if (!W.ghost || !W.ghost.visible) return;
  const p = W.ghost.position;
  W.onPlace(W.placing, [p.x, p.y, p.z, 0, 0, 0].map(v => Math.round(v * 100) / 100));
}
