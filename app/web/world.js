// ---------- the 3D world view ----------
// One place the way the game lays it out (every thing's mesh at its position, turn and scale, textured from the
// game's archives), and the hands to change it, with the Workshop's controls: right-drag to look, WASD to fly,
// click to select (Shift adds, drag a box on empty space), the handles to move and turn one thing or several.
// Game units, Z up. It knows nothing of the server: app.js hands it things and listens for what the user did (W.on*).
const T = THREE;
const W = {scene: null, cam: null, ren: null, group: null, models: {}, mats: {}, tex: {}, yaw: 0, pitch: -0.3,
           keys: {}, byKey: new Map(), cell: null, token: 0, sel: [], gizmo: null, pivot: null, mode: 'translate',
           placing: null, show: {markers: false, removed: false}, hidden: new Set(), mouse: null, sprint: null,
           onSelect: () => {}, onMove: () => {}, onPlace: () => {}, onContext: () => {}, onOpen: () => {}};

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
  if (!tex && alpha === 'skin') return W.mats[k] = W.mats[k] || new T.MeshLambertMaterial({color: 0xc8a888});
  if (W.mats[k]) return W.mats[k];
  // plain sand colour until the texture arrives (and for the few shapes that have none)
  const m = new T.MeshLambertMaterial({color: 0xb8a888, side: double || alpha === 'blend' ? T.DoubleSide : T.FrontSide});
  if (alpha === 'test') m.alphaTest = 0.5;
  if (alpha === 'blend'){ m.transparent = true; m.depthWrite = false; if (!tex) m.opacity = 0.25; }
  if (tex) texture(tex).then(t => { if (t){ m.map = t; m.color.set(0xffffff); m.needsUpdate = true; } });
  return W.mats[k] = m;
}

// ---------- meshes: built once per file, shared by every thing that uses it ----------
// (tex: a texture to use instead of the mesh's own, for a race's skin)
function model(path, tex){
  const key = path + (tex ? '|' + tex : '');
  if (!W.models[key]) W.models[key] = api('/api/mesh?path=' + encodeURIComponent(path)).then(d => {
    const parts = [];
    for (const s of d.shapes || []){
      if (tex) s.tex = tex;
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
  return W.models[key];
}

// a character or creature: every part of it (body, head, hair, apparel...), and how much bigger or smaller it is
const ACTOR_Q = {};
async function actorModel(bkey){
  if (!ACTOR_Q[bkey]) ACTOR_Q[bkey] = api('/api/actor?key=' + encodeURIComponent(bkey)).then(async d => {
    const lists = await Promise.all((d.parts || []).map(p => model(p.model, p.tex)));
    return {parts: lists.flat(), scale: d.scale || 1};
  }).catch(() => ({parts: [], scale: 1}));
  return ACTOR_Q[bkey];
}
// what stands in for a thing with nothing to draw: a post as tall as a person, so it can still be found and moved
const STANDIN = new T.CylinderGeometry(14, 14, 128, 10).rotateX(Math.PI / 2).translate(0, 0, 64);
const STANDIN_MAT = new T.MeshLambertMaterial({color: 0x7fa7d6, transparent: true, opacity: 0.55});
// a light with nothing of its own to draw: a small glowing bulb (the game shows nothing there, only its light)
const BULB = new T.SphereGeometry(7, 10, 8);
// a SpeedTree tree: two crossed planes with the picture the game shows of it from afar
const TREE_STANDIN = {};
function treeParts(tr){
  const k = tr.tex + '|' + tr.w + '|' + tr.h;
  if (!TREE_STANDIN[k]){
    const a = new T.PlaneGeometry(tr.w, tr.h).rotateX(Math.PI / 2).translate(0, 0, tr.h / 2);
    const b = a.clone().rotateZ(Math.PI / 2);
    for (const g of [a, b]) g.computeBoundingBox();
    const m = tr.tex ? material(tr.tex, 'test', true) : new T.MeshLambertMaterial({color: 0x6f7a4a, side: T.DoubleSide});
    TREE_STANDIN[k] = [[a, m, false], [b, m, false]];
  }
  return TREE_STANDIN[k];
}
async function thingParts(t){
  if (t.tree) return {parts: treeParts(t.tree), scale: 1};
  if (t.type === 'LIGH' && !t.model){
    const c = t.light ? t.light.color : [255, 230, 180];
    return {parts: [[BULB, new T.MeshBasicMaterial({color: new T.Color(c[0] / 255, c[1] / 255, c[2] / 255)}), false]], scale: 1};
  }
  if (t.actor || A_ACTORS.has(t.type)){
    const a = await actorModel(t.bkey || t.key);
    return {parts: a.parts.length ? a.parts : [[STANDIN, STANDIN_MAT, false]], scale: a.scale};
  }
  return {parts: await model(t.model), scale: 1};
}
const A_ACTORS = new Set(['NPC_', 'CREA']);

// how far a model's underside is below its origin, so it can be stood on a surface
async function modelLift(path, item){
  if (item && A_ACTORS.has(item.type)) return 0;          // (characters and creatures: feet at 0)
  const parts = await model(path), b = new T.Box3();
  for (const [g] of parts) b.union(g.boundingBox);
  return b.isEmpty() ? 0 : -b.min.z;
}

// ---------- scene ----------
function worldInit(box){
  W.box = box;
  W.ren = new T.WebGLRenderer({antialias: true});
  W.ren.setPixelRatio(window.devicePixelRatio);
  W.ren.domElement.tabIndex = 0;              // (so the view can hold the keyboard: WASD while a search box was last used)
  W.ren.domElement.style.outline = 'none';
  box.appendChild(W.ren.domElement);
  W.scene = new T.Scene();
  W.scene.background = new T.Color(0x0e0c0a);
  W.cam = new T.PerspectiveCamera(70, 1, 4, 60000);
  W.cam.up.set(0, 0, 1);
  W.scene.add(new T.HemisphereLight(0xfff1dd, 0x3a3428, 0.85));
  const sun = new T.DirectionalLight(0xffffff, 0.45); sun.position.set(0.4, -0.6, 1); W.scene.add(sun);
  W.lamp = new T.PointLight(0xffe2b0, 0.6, 3000); W.scene.add(W.lamp);
  W.hemi = W.scene.children.find(o => o.isHemisphereLight); W.sun = sun;
  // the game's lights: a fixed handful of point lights, given each moment to the lights nearest the camera (a fixed
  // number, so the shaders never have to be rebuilt; hundreds of live lights would bring the view to a crawl)
  W.pool = [];
  for (let i = 0; i < 12; i++){ const l = new T.PointLight(0xffffff, 0, 1, 2); W.scene.add(l); W.pool.push(l); }
  W.gameLight = true;
  W.outline = new T.Box3Helper(new T.Box3(), 0xf0cd87); W.outline.visible = false; W.scene.add(W.outline);
  W.pivot = new T.Object3D(); W.scene.add(W.pivot);
  W.gizmo = new T.TransformControls(W.cam, W.ren.domElement);
  W.gizmo.setSize(0.9);
  W.gizmo.addEventListener('mouseDown', gizmoStart);
  W.gizmo.addEventListener('dragging-changed', e => { W.dragging = e.value; if (!e.value) commitSelected(W.mode === 'rotate' ? 'Turn' : W.mode === 'scale' ? 'Scale' : 'Move'); });
  W.gizmo.addEventListener('objectChange', gizmoFollow);
  W.scene.add(W.gizmo);
  W.boxEl = document.createElement('div');
  W.boxEl.style.cssText = 'position:absolute;border:1px dashed #d2a85a;background:#d2a85a1c;pointer-events:none;display:none;z-index:3';
  box.appendChild(W.boxEl);
  const size = () => { const w = box.clientWidth, h = box.clientHeight; W.ren.setSize(w, h); W.cam.aspect = w / Math.max(1, h); W.cam.updateProjectionMatrix(); };
  new ResizeObserver(size).observe(box); size();
  controls(W.ren.domElement);
  let last = performance.now();
  const frame = now => {
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    move(dt);
    W.lamp.position.copy(W.cam.position);
    if (now - (W.lightsAt || 0) > 300){ W.lightsAt = now; assignLights(); }
    if (!W.paused) W.ren.render(W.scene, W.cam);           // (resting while the flat map shows)
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

function dir(){ return new T.Vector3(Math.cos(W.pitch) * Math.cos(W.yaw), Math.cos(W.pitch) * Math.sin(W.yaw), Math.sin(W.pitch)); }
function look(){ const d = dir(); W.cam.lookAt(W.cam.position.clone().add(d)); return d; }

function move(dt){
  const k = W.keys;
  let speed = (k.shift ? 2400 : 700) * dt;
  if (W.sprint && k[W.sprint]) speed *= 4;
  // (W and S go the way the view looks, up and down too, as the Workshop flies; A and D slide level)
  const f = dir(), r = new T.Vector3(Math.sin(W.yaw), -Math.cos(W.yaw), 0);
  const p = W.cam.position;
  if (k.w) p.addScaledVector(f, speed); if (k.s) p.addScaledVector(f, -speed);
  if (k.d) p.addScaledVector(r, speed); if (k.a) p.addScaledVector(r, -speed);
  if (k.e) p.z += speed; if (k.q) p.z -= speed;
  look();
}

function ray(e){
  const rect = W.ren.domElement.getBoundingClientRect(), r = new T.Raycaster();
  r.setFromCamera({x: (e.clientX - rect.left) / rect.width * 2 - 1, y: -(e.clientY - rect.top) / rect.height * 2 + 1}, W.cam);
  return r;
}

function visibleGroups(except){
  const skip = new Set([].concat(except || []));
  return W.group ? W.group.children.filter(g => g.visible && !skip.has(g)) : [];
}

// (locked kinds can't be clicked in the view: they're picked from the Objects list instead)
function pickable(except){ return visibleGroups(except).filter(g => !(W.locked && W.locked.has(thingKind(g.userData.thing)))); }
function hitThing(e, except){
  const r = ray(e), lands = W.lands ? [...W.lands] : [];
  const hit = r.intersectObjects(pickable(except).concat(lands), true)[0];
  if (hit && lands.length){
    // (outside: the ground itself, to stand things on or to pick a spot)
    let o = hit.object; while (o && !o.userData.land) o = o.parent;
    if (o) return {group: null, point: hit.point, normal: hit.face ? hit.face.normal.clone().transformDirection(hit.object.matrixWorld) : new T.Vector3(0, 0, 1), floor: true, land: true};
  }
  if (!hit){
    // nothing there: the floor plane of the place (its lowest floor, or 0 in an empty one)
    const at = new T.Vector3();
    if (r.ray.intersectPlane(new T.Plane(new T.Vector3(0, 0, 1), -(W.floorZ || 0)), at) && at.distanceTo(W.cam.position) < 20000)
      return {group: null, point: at, normal: new T.Vector3(0, 0, 1), floor: true};
    return null;
  }
  let o = hit.object; while (o && !o.userData.thing) o = o.parent;
  return {group: o || null, point: hit.point, normal: hit.face ? hit.face.normal.clone().transformDirection(hit.object.matrixWorld) : null};
}

function typing(e){ const t = e.target; return t && (t.tagName === 'INPUT' && t.type !== 'checkbox' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable); }

// which way a key moves the camera: by where it sits on the keyboard, so it works in any layout
function moveKey(e){
  const c = {KeyW: 'w', KeyA: 'a', KeyS: 's', KeyD: 'd', KeyQ: 'q', KeyE: 'e'}[e.code];
  if (c) return c;
  const k = (e.key || '').toLowerCase();
  return k.length === 1 && 'wasdqe'.includes(k) ? k : null;
}

function selCenter(){
  const b = new T.Box3();
  for (const g of W.sel){ g.updateMatrixWorld(true); b.expandByObject(g); }
  if (b.isEmpty()) for (const g of W.sel) b.expandByPoint(g.position);
  return b.getCenter(new T.Vector3());
}

function controls(el){
  let drag = null;
  el.addEventListener('contextmenu', e => e.preventDefault());
  el.addEventListener('auxclick', e => { if (e.button === 1) e.preventDefault(); });
  el.addEventListener('pointerdown', e => {
    el.focus();
    if (e.button === 1) e.preventDefault();
    if (e.button === 0 && (W.dragging || W.gizmo.axis)) return;           // using the handles
    if (e.button === 0 && !e.altKey && W.tool && W.tool.down(e)){          // a tool working on the ground (the Ground brush)
      drag = {b: 0, tool: true, x: e.clientX, y: e.clientY, moved: 0};
      try { el.setPointerCapture(e.pointerId); } catch (err) {}
      return;
    }
    drag = {b: e.button, x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, moved: 0, alt: e.altKey, shift: e.shiftKey};
    if (e.button === 0 && e.altKey){
      drag.pivot = W.sel.length ? selCenter() : (hitThing(e) || {}).point || W.cam.position.clone().addScaledVector(dir(), 600);
      drag.dist = W.cam.position.distanceTo(drag.pivot);
    } else if (e.button === 0 && !W.placing){
      const h = hitThing(e);
      drag.hit = h && h.group;
      if (!drag.hit || e.shiftKey) drag.box = true;                   // empty space (or Shift): a box to select with
    }
    try { el.setPointerCapture(e.pointerId); } catch (err) {}
  });
  el.addEventListener('pointermove', e => {
    W.mouse = {clientX: e.clientX, clientY: e.clientY};
    if (W.placing) placeGhost(e);
    if (W.tool && W.tool.hover) W.tool.hover(e, !!(drag && drag.tool));
    if (drag && drag.tool){ W.tool.move(e); return; }
    if (!drag || W.dragging) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
    if (drag.b === 2){                                                  // right-drag: look around
      W.yaw -= dx * 0.005; W.pitch = Math.max(-1.55, Math.min(1.55, W.pitch - dy * 0.005));
    } else if (drag.b === 1){                                           // middle-drag: slide
      const s = (W.keys.shift ? 6 : 2), r = new T.Vector3(Math.sin(W.yaw), -Math.cos(W.yaw), 0), u = new T.Vector3().crossVectors(r, dir());
      W.cam.position.addScaledVector(r, -dx * s).addScaledVector(u, dy * s);
    } else if (drag.pivot){                                             // Alt+drag: circle what's selected
      W.yaw -= dx * 0.005; W.pitch = Math.max(-1.5, Math.min(1.5, W.pitch - dy * 0.005));
      W.cam.position.copy(drag.pivot).addScaledVector(dir(), -drag.dist);
    } else if (drag.box && drag.moved > 4){
      const r = W.box.getBoundingClientRect(), x = Math.min(drag.x0, e.clientX) - r.left, y = Math.min(drag.y0, e.clientY) - r.top;
      Object.assign(W.boxEl.style, {display: 'block', left: x + 'px', top: y + 'px', width: Math.abs(e.clientX - drag.x0) + 'px', height: Math.abs(e.clientY - drag.y0) + 'px'});
    }
  });
  el.addEventListener('pointerup', e => {
    const d = drag; drag = null;
    W.boxEl.style.display = 'none';
    if (!d) return;
    if (d.tool){ if (W.tool) W.tool.up(e); return; }
    if (d.b === 2 && d.moved <= 10){                      // (a right-click that wanders a little is still a click, not a look)
      if (W.placing) return stopPlacing();
      const h = hitThing(e);
      const key = h && h.group ? h.group.userData.thing.key : null;
      if (key && !W.sel.some(g => g.userData.thing.key === key)) select([key]);
      return W.onContext(e, key, h && h.point);
    }
    if (d.b !== 0 || d.pivot) return;
    if (d.box && d.moved > 4) return boxSelect(d.x0, d.y0, e.clientX, e.clientY, d.shift);
    if (d.moved > 4) return;
    if (W.placing) return placeAt(e);
    const key = d.hit ? d.hit.userData.thing.key : null;
    if (d.shift && key){
      const keys = W.sel.map(g => g.userData.thing.key);
      select(keys.includes(key) ? keys.filter(k => k !== key) : keys.concat(key));
    } else if (!d.shift) select(key ? [key] : []);
  });
  el.addEventListener('dblclick', e => { const h = hitThing(e); if (h && h.group) W.onOpen(h.group.userData.thing.key); });
  el.addEventListener('wheel', e => { e.preventDefault(); W.cam.position.addScaledVector(dir(), -Math.sign(e.deltaY) * (W.keys.shift ? 800 : 200)); }, {passive: false});
  // things dragged in from the Place panel land where they're dropped
  el.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('text/x-folab')) e.preventDefault(); });
  el.addEventListener('drop', async e => {
    const key = e.dataTransfer.getData('text/x-folab'); if (!key) return;
    e.preventDefault(); el.focus();
    W.onDropItem(key, e);
  });
  addEventListener('keydown', e => {
    if (typing(e) || !W.box.offsetParent) return;
    const mv = moveKey(e);
    if (mv && !e.ctrlKey && !e.altKey && !e.metaKey){
      // a move key tapped twice and held: sprint until it's let go
      if (!e.repeat && !W.keys[mv] && performance.now() - ((W.upAt || {})[mv] || 0) < 320) W.sprint = mv;
      W.keys[mv] = true; e.preventDefault();
    }
    if (e.key === 'Shift') W.keys.shift = true;
    if (e.key === 'Escape') W.keys = {};
  });
  // letting go of a key always stops it (heard first, before anything else can swallow it)
  addEventListener('keyup', e => {
    const mv = moveKey(e);
    if (mv){ W.keys[mv] = false; if (W.sprint === mv) W.sprint = null; (W.upAt = W.upAt || {})[mv] = performance.now(); }
    if (e.key === 'Shift') W.keys.shift = false;
    if (e.key === 'Meta' || e.key === 'OS') W.keys = {};
  }, true);
  const stop = () => { W.keys = {}; W.sprint = null; };
  addEventListener('blur', stop);
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  addEventListener('mousemove', e => { if (W.keys.shift && !e.shiftKey) W.keys.shift = false; }, true);
}

function boxSelect(x0, y0, x1, y1, add){
  const r = W.ren.domElement.getBoundingClientRect();
  const lo = [Math.min(x0, x1), Math.min(y0, y1)], hi = [Math.max(x0, x1), Math.max(y0, y1)];
  const keys = add ? W.sel.map(g => g.userData.thing.key) : [];
  const v = new T.Vector3();
  for (const g of visibleGroups()){
    const b = new T.Box3().setFromObject(g);
    (b.isEmpty() ? v.copy(g.position) : b.getCenter(v)).project(W.cam);
    if (v.z > 1) continue;                                        // behind the camera
    const sx = r.left + (v.x + 1) / 2 * r.width, sy = r.top + (1 - v.y) / 2 * r.height;
    if (sx >= lo[0] && sx <= hi[0] && sy >= lo[1] && sy <= hi[1]){
      const k = g.userData.thing.key; if (!keys.includes(k)) keys.push(k);
    }
  }
  select(keys);
}

// ---------- the game's lights ----------
function assignLights(){
  const on = W.gameLight, cam = W.cam.position, list = [];
  if (on && W.group) for (const g of W.group.children){
    const t = g.userData.thing, L = t.light;
    if (!L || L.off || L.negative || !L.radius || t.state === 'removed') continue;
    const d = g.position.distanceTo(cam) - L.radius;
    list.push([d, g, L]);
  }
  list.sort((a, b) => a[0] - b[0]);
  W.pool.forEach((l, i) => {
    const e = list[i];
    if (!e){ l.intensity = 0; return; }
    const [, g, L] = e;
    l.position.copy(g.position);
    l.color.setRGB(L.color[0] / 255, L.color[1] / 255, L.color[2] / 255);
    l.distance = L.radius * 1.2; l.decay = 1.2; l.intensity = 1.6;
  });
  // with the game's light on, the room is lit mostly by its own lights
  // (outside, the sun lights everything)
  if (W.outdoors){ W.hemi.intensity = 0.62; W.sun.intensity = 0.85; W.lamp.intensity = 0; return; }
  W.hemi.intensity = on ? 0.35 : 0.85; W.sun.intensity = on ? 0.15 : 0.45; W.lamp.intensity = on ? 0.15 : 0.6;
}
function setGameLight(on){ W.gameLight = on; assignLights(); }

// ---------- things ----------
function setTransform(g, t){
  g.position.set(t.p[0], t.p[1], t.p[2]);
  g.rotation.set(-t.p[3], -t.p[4], -t.p[5], 'XYZ');      // the game turns the other way round each axis
  g.scale.setScalar((t.s || 1) * (g.userData.bodyScale || 1));
}

// what kind of thing it is, for the View panel's switches
function thingKind(t){
  if (t.marker) return 'markers';
  if (t.tree) return 'scenery';
  const m = (t.model || '').toLowerCase();
  if (t.type === 'NPC_') return 'people';
  if (t.type === 'CREA') return 'creatures';
  if (t.type === 'DOOR') return 'doors';
  if (t.type === 'CONT') return 'containers';
  if (t.type === 'LIGH') return 'lights';
  if (['WEAP', 'ARMO', 'MISC', 'ALCH', 'AMMO', 'BOOK', 'NOTE', 'KEYM', 'CHIP', 'CMNY', 'IMOD', 'CCRD'].includes(t.type)) return 'items';
  if (['FURN', 'ACTI', 'TERM', 'TACT'].includes(t.type)) return 'furniture';
  if (m.includes('\\landscape\\') || m.includes('\\trees\\') || m.includes('\\plants\\') || /bush|shrub|rock|tumbleweed|yucca|cactus/.test(m)) return 'scenery';
  return 'buildings';
}
function thingVisible(t){
  if (W.show.kinds && W.show.kinds[thingKind(t)] === false && thingKind(t) !== 'markers') return false;
  if (W.show.onlyMine && !t.state) return false;
  return (!t.marker || W.show.markers) && (t.state !== 'removed' || W.show.removed) && !W.hidden.has(t.key);
}

async function addThing(t, token){
  const g = new T.Group();
  g.userData.thing = t;
  setTransform(g, t);
  g.visible = thingVisible(t);
  W.group.add(g);
  W.byKey.set(t.key, g);
  // (ready once its meshes are in: what measures it, like Drop down, waits for that)
  let ready; g.userData.ready = new Promise(r => { ready = r; });
  const {parts, scale} = await thingParts(t);
  if (token !== W.token || !g.parent){ ready(); return g; }
  if (scale !== 1){ g.userData.bodyScale = scale; setTransform(g, t); }
  for (const [geo, mat, blend] of parts){ const m = new T.Mesh(geo, mat); if (blend) m.renderOrder = 1; g.add(m); }
  ready();
  if (t.state === 'removed') ghostly(g, true);
  if (W.sel.includes(g)) refreshSel();
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
  if (g.userData.thing.bkey !== t.bkey){
    // swapped for another thing: drawn again from its own model, still selected if it was
    const wasSel = W.sel.includes(g), keys = W.sel.map(x => x.userData.thing.key);
    W.group.remove(g); W.byKey.delete(t.key);
    return addThing(t, W.token).then(n => { if (wasSel) select(keys); return n; });
  }
  const was = g.userData.thing.state;
  g.userData.thing = t;
  setTransform(g, t);
  g.visible = thingVisible(t);
  if ((was === 'removed') !== (t.state === 'removed')) ghostly(g, t.state === 'removed');
  if (W.sel.includes(g)){ if (!g.visible) select(W.sel.filter(x => x !== g).map(x => x.userData.thing.key)); else refreshSel(); }
}

function dropThing(key){
  const g = W.byKey.get(key);
  if (!g) return;
  if (W.sel.includes(g)) select(W.sel.filter(x => x !== g).map(x => x.userData.thing.key));
  W.group.remove(g); W.byKey.delete(key);
}

// ---------- a cell ----------
async function openCell(c, onProgress, at){
  const token = ++W.token;
  select([]);
  if (W.group) W.scene.remove(W.group);
  W.group = new T.Group(); W.scene.add(W.group);
  W.byKey = new Map();
  W.hidden = new Set();
  W.cell = c;
  const zs = c.things.filter(t => !t.marker).map(t => t.p[2]);
  W.floorZ = zs.length ? Math.min(...zs) : 0;
  if (W.grid) W.scene.remove(W.grid);
  // (a grid on the floor where there's little to stand on: a new, empty place)
  if (c.things.filter(t => !t.marker).length < 8){
    W.grid = new T.GridHelper(4096, 32, 0x8a6a35, 0x463c2e); W.grid.rotation.x = Math.PI / 2; W.grid.position.z = W.floorZ;
    W.scene.add(W.grid);
  } else W.grid = null;
  standAt(at || arrival(c));
  let done = 0;
  await Promise.all(c.things.map(t => addThing(t, token).then(() => { done++; if (onProgress && token === W.token) onProgress(done, c.things.length); })));
}

// where to stand on opening a place: where the game's console "coc" would put you (its arrival marker), else beside
// the thing nearest the middle of the place
function arrival(c){
  const a = ['COCMarkerHeading', 'XMarkerHeading'].map(b => c.things.find(t => t.base === b)).find(Boolean);
  if (a) return {p: a.p, facing: true};
  const solid = c.things.filter(t => !t.marker && t.type === 'STAT');
  if (!solid.length) return null;
  const mid = new T.Box3().setFromPoints(solid.map(t => new T.Vector3(t.p[0], t.p[1], t.p[2]))).getCenter(new T.Vector3());
  const d = t => mid.distanceToSquared(new T.Vector3(t.p[0], t.p[1], t.p[2]));
  return {p: solid.reduce((b, t) => d(t) < d(b) ? t : b).p};
}
function standAt(at){
  if (!at){ W.cam.position.set(-600, -600, 400); W.yaw = Math.PI / 4; W.pitch = -0.4; return; }
  W.cam.position.set(at.p[0], at.p[1], at.p[2] + 120);
  W.yaw = Math.PI / 2 - (at.facing ? at.p[5] : 0); W.pitch = -0.1;
}

// the cell again as the server now has it (after an undo, say): move, add and drop what differs
function syncCell(things){
  const seen = new Set();
  for (const t of things){ seen.add(t.key); const g = W.byKey.get(t.key); if (!g || JSON.stringify(g.userData.thing) !== JSON.stringify(t)) updateThing(t); }
  for (const k of [...W.byKey.keys()]) if (!seen.has(k)) dropThing(k);
}

function setShow(what, on){
  W.show[what] = on;
  restyle();
}
function restyle(){
  for (const g of W.byKey.values()) g.visible = thingVisible(g.userData.thing);
  const keep = W.sel.filter(g => g.visible);
  if (keep.length !== W.sel.length) select(keep.map(g => g.userData.thing.key));
}
function hideKeys(keys){ for (const k of keys) W.hidden.add(k); restyle(); }
function showHidden(){ W.hidden.clear(); restyle(); }

// ---------- selection ----------
function selThings(){ return W.sel.map(g => g.userData.thing); }

function refreshSel(){
  if (!W.sel.length){ W.outline.visible = false; return; }
  const b = new T.Box3();
  for (const g of W.sel){ g.updateMatrixWorld(true); const gb = new T.Box3().setFromObject(g); b.union(gb.isEmpty() ? new T.Box3().setFromCenterAndSize(g.position, new T.Vector3(16, 16, 16)) : gb); }
  W.outline.box.copy(b); W.outline.visible = true;
}

function select(keys){
  if (!Array.isArray(keys)) keys = keys ? [keys] : [];
  W.sel = keys.map(k => W.byKey.get(k)).filter(g => g && g.visible);
  W.gizmo.detach();
  if (W.sel.length === 1) W.gizmo.attach(W.sel[0]);
  else if (W.sel.length > 1){
    // several: one set of handles in their middle
    W.pivot.position.copy(selCenter()); W.pivot.rotation.set(0, 0, 0); W.pivot.updateMatrixWorld(true);
    W.gizmo.attach(W.pivot);
  }
  refreshSel();
  W.onSelect(selThings());
}

function gizmoStart(){
  W.pivot.updateMatrixWorld(true);
  snapPrepare();
  W.dragFrom = {pivot: W.pivot.matrixWorld.clone(), each: W.sel.map(g => { g.updateMatrixWorld(true); return g.matrixWorld.clone(); })};
}

// ---------- snapping pieces together ----------
// While something is dragged, it slides the last few units into place against the pieces round it: edge to edge,
// sides lined up, standing on top or level at the bottom (the boxes the meshes fill, as they turn). The nearest of
// those within SNAP units wins on each axis.
const SNAP = 24;
// a piece's kit: its mesh's folder below meshes\ (Dungeons\Vault\HallSmall, Architecture\Strip\..., ...)
function kitOf(model){ const parts = (model || '').toLowerCase().split('\\'); parts.pop(); return parts.slice(1, 3).join('\\'); }
function snapPrepare(){
  W.snapBoxes = null;
  if (!W.snapPieces || W.mode !== 'translate' || !W.sel.length) return;
  const sel = new T.Box3(); for (const g of W.sel){ g.updateMatrixWorld(true); sel.union(new T.Box3().setFromObject(g)); }
  if (sel.isEmpty()) return;
  const near = sel.clone().expandByScalar(1024), mine = new Set(W.sel);
  W.snapBoxes = []; W.snapKin = [];
  const turn = g => ((g.rotation.z % (Math.PI / 2)) + Math.PI / 2) % (Math.PI / 2);
  const myTurn = turn(W.sel[0]), myKit = W.sel[0].userData.thing.type === 'STAT' ? kitOf(W.sel[0].userData.thing.model) : null;
  for (const g of visibleGroups()){
    if (mine.has(g) || g.userData.thing.marker || g.userData.thing.actor) continue;
    const b = new T.Box3().setFromObject(g);
    if (!b.isEmpty() && b.intersectsBox(near)){
      W.snapBoxes.push(b);
      // (a piece of the same kit, turned the same way: its mesh in the same folder, and kit-piece size; kit pieces join
      // on a 128-unit step from each other. Furniture and clutter stand anywhere, so they don't count)
      const t = g.userData.thing, sz = b.getSize(new T.Vector3());
      if (t.type === 'STAT' && kitOf(t.model) === myKit && Math.max(sz.x, sz.y) >= KIT_STEP && Math.abs(turn(g) - myTurn) < 0.01)
        W.snapKin.push(g.position.clone());
    }
  }
}
const KIT_STEP = 128;
function snapOffset(sel){
  const best = {x: null, y: null, z: null};
  const consider = (axis, d) => { if (Math.abs(d) <= SNAP && (best[axis] === null || Math.abs(d) < Math.abs(best[axis]))) best[axis] = d; };
  // first: a whole kit step from a piece turned the same way (where kit pieces join), on each axis
  const p = (W.sel.length > 1 ? W.pivot : W.sel[0]).position;
  for (const k of W.snapKin || []){
    for (const axis of ['x', 'y']){
      const d = p[axis] - k[axis], step = Math.round(d / KIT_STEP) * KIT_STEP;
      consider(axis, step - d);
    }
    if (Math.abs(p.z - k.z) <= SNAP) consider('z', k.z - p.z);
  }
  if (best.x !== null || best.y !== null) return best;
  const lap = (b, a1, a2) => b.min[a1] < sel.max[a1] + SNAP && b.max[a1] > sel.min[a1] - SNAP && b.min[a2] < sel.max[a2] + SNAP && b.max[a2] > sel.min[a2] - SNAP;
  for (const b of W.snapBoxes){
    for (const [axis, o1, o2] of [['x', 'y', 'z'], ['y', 'x', 'z'], ['z', 'x', 'y']]){
      if (!lap(b, o1, o2)) continue;                 // (only pieces beside it on that axis)
      consider(axis, b.max[axis] - sel.min[axis]);    // against its far side
      consider(axis, b.min[axis] - sel.max[axis]);    // against its near side
      consider(axis, b.min[axis] - sel.min[axis]);    // sides level
      consider(axis, b.max[axis] - sel.max[axis]);
    }
  }
  return best;
}
function snapApply(){
  if (!W.snapBoxes || !W.snapBoxes.length || !W.dragging) return;
  const sel = new T.Box3(); for (const g of W.sel){ g.updateMatrixWorld(true); sel.union(new T.Box3().setFromObject(g)); }
  const o = snapOffset(sel), d = new T.Vector3(o.x || 0, o.y || 0, o.z || 0);
  if (!d.lengthSq()) return;
  const target = W.sel.length > 1 ? W.pivot : W.sel[0];
  target.position.add(d);
  if (W.sel.length > 1){ W.pivot.updateMatrixWorld(true); }
  W.snapped = true;
}

// several selected: each follows the handles, turning round their middle
function gizmoFollow(){
  if (W.mode === 'scale' && W.sel.length === 1){
    // the game sizes a thing evenly: whichever handle was pulled, all three follow it
    const g = W.sel[0], b = g.userData.bodyScale || 1, was = (g.userData.thing.s || 1) * b;
    const v = [g.scale.x, g.scale.y, g.scale.z].reduce((m, x) => Math.abs(x - was) > Math.abs(m - was) ? x : m, was);
    g.scale.setScalar(Math.max(0.01 * b, Math.min(10 * b, v)));
    refreshSel(); return;
  }
  if (W.sel.length === 1 && W.snapBoxes) snapApply();
  if (W.sel.length > 1 && W.snapBoxes && W.dragFrom) snapApply();
  if (W.sel.length > 1 && W.dragFrom){
    W.pivot.updateMatrixWorld(true);
    const delta = W.pivot.matrixWorld.clone().multiply(new T.Matrix4().copy(W.dragFrom.pivot).invert()), s = new T.Vector3();
    W.sel.forEach((g, i) => { new T.Matrix4().multiplyMatrices(delta, W.dragFrom.each[i]).decompose(g.position, g.quaternion, s); });
  }
  refreshSel();
}

function setMode(m){
  W.mode = m; W.gizmo.setMode(m);
  // (scaling several at once isn't something a ref can hold together: one at a time)
  if (m === 'scale' && W.sel.length > 1) select([W.sel[0].userData.thing.key]);
}
function setSnap(grid, angle){
  W.gridSnap = grid;
  W.gizmo.setTranslationSnap(grid > 0 ? grid : null);
  W.gizmo.setRotationSnap(angle > 0 ? angle * Math.PI / 180 : null);
}

// a thing's position as the game writes it
function gameP(g){
  return [g.position.x, g.position.y, g.position.z, -g.rotation.x, -g.rotation.y, -g.rotation.z].map(v => Math.round(v * 10000) / 10000);
}

function commitSelected(label){
  const moves = [];
  for (const g of W.sel){
    const t = g.userData.thing, p = gameP(g);
    const s = Math.round(g.scale.x / (g.userData.bodyScale || 1) * 1000) / 1000;
    if (W.mode === 'scale' && Math.abs(s - (t.s || 1)) > 1e-3) moves.push([t, p, s]);
    else if (!p.every((v, i) => Math.abs(v - t.p[i]) < 1e-4)) moves.push([t, p]);
  }
  if (W.sel.length > 1){ W.pivot.position.copy(selCenter()); W.pivot.rotation.set(0, 0, 0); }
  if (moves.length) W.onMove(moves, label);
}

function focusSel(){
  if (!W.sel.length) return;
  const b = new T.Box3(); for (const g of W.sel) b.expandByObject(g);
  const c = b.getCenter(new T.Vector3()), r = Math.max(120, b.getSize(new T.Vector3()).length());
  W.cam.position.copy(c).addScaledVector(dir(), -r * 1.1);
}

// where g would sit if set down on whatever is under it; null when there's nothing below
function dropDown(g){
  g.updateMatrixWorld(true);
  const b = new T.Box3().setFromObject(g);
  if (b.isEmpty()) return null;
  const c = b.getCenter(new T.Vector3());
  const r = new T.Raycaster(new T.Vector3(c.x, c.y, b.min.z + 1), new T.Vector3(0, 0, -1), 0, 20000);
  const hit = r.intersectObjects(visibleGroups(W.sel), true)[0];
  if (!hit) return null;
  return g.position.z - (b.min.z - hit.point.z);
}

// the surface under the mouse (or the middle of the view): for pasting and dropping things in
function pointUnder(e){
  const h = e ? hitThing(e, W.sel) : null;
  if (h) return h.point;
  const r = new T.Raycaster(W.cam.position, dir()), hit = r.intersectObjects(visibleGroups(), true)[0];
  return hit ? hit.point : W.cam.position.clone().addScaledVector(dir(), 300);
}

// ---------- doors: where you arrive ----------
// The game puts a door's arrival point in front of it on the room's side (every door that leads somewhere, a few
// steps out, facing into the room). Tried both ways out of the door's thin side: the one with floor below and nothing
// in the way, and the more open of the two when both are.
function arrivalFor(g){
  g.updateMatrixWorld(true);
  const b = new T.Box3().setFromObject(g), c = b.getCenter(new T.Vector3()), size = b.getSize(new T.Vector3());
  const n = size.x < size.y ? new T.Vector3(1, 0, 0) : new T.Vector3(0, 1, 0);
  const others = visibleGroups(g), mid = new T.Vector3(c.x, c.y, b.min.z + 60);
  let best = null;
  for (const sign of [1, -1]){
    const d = n.clone().multiplyScalar(sign), spot = mid.clone().addScaledVector(d, 80);
    const blocked = new T.Raycaster(mid, d, 0, 80).intersectObjects(others, true)[0];
    const floor = new T.Raycaster(spot, new T.Vector3(0, 0, -1), 0, 200).intersectObjects(others, true)[0];
    const open = (new T.Raycaster(mid, d, 0, 600).intersectObjects(others, true)[0] || {distance: 600}).distance;
    const score = (blocked ? 0 : 2) + (floor ? 2 : 0) + open / 600;
    if (!best || score > best.score) best = {score, d, z: floor ? floor.point.z : b.min.z, spot};
  }
  const heading = Math.atan2(best.d.x, best.d.y);                 // the game's: 0 is north, turning clockwise
  return [best.spot.x, best.spot.y, best.z, 0, 0, Math.round(heading * 10000) / 10000].map(v => Math.round(v * 10000) / 10000);
}

// ---------- placing new things ----------
// (item: one thing to place; or a prefab, {prefab: name, items: [{base, p (from the group's middle), s, model, type}]})
async function startPlacing(item){
  W.placing = item;
  select([]);
  if (W.ghost) W.scene.remove(W.ghost);
  const g = new T.Group();
  if (item.items){
    for (const it of item.items){
      const {parts, scale} = await thingParts({...it, bkey: it.base, key: it.base});
      const sub = new T.Group();
      for (const [geo, mat] of parts) sub.add(new T.Mesh(geo, mat));
      sub.position.set(it.p[0], it.p[1], it.p[2]); sub.rotation.set(-it.p[3], -it.p[4], -it.p[5], 'XYZ'); sub.scale.setScalar((it.s || 1) * scale);
      g.add(sub);
    }
    W.ghostLift = 0;                                // (a prefab keeps its lowest point at its origin)
  } else {
    const {parts, scale} = await thingParts(item);
    for (const [geo, mat] of parts) g.add(new T.Mesh(geo, mat));
    g.scale.setScalar(scale);
    W.ghostLift = await modelLift(item.model, item);
  }
  if (W.placing !== item) return;
  g.traverse(m => { if (m.isMesh) m.raycast = () => {}; });
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
  const hit = hitThing(e);
  if (!hit){ W.ghost.visible = false; return; }
  const grid = W.gridSnap || 0, s = v => grid ? Math.round(v / grid) * grid : v;
  W.ghost.position.set(s(hit.point.x), s(hit.point.y), hit.point.z + (hit.normal && hit.normal.z > 0.5 ? W.ghostLift : 0));
  W.ghost.visible = true;
}

function placeAt(e){
  placeGhost(e);
  if (!W.ghost || !W.ghost.visible) return;
  const p = W.ghost.position;
  W.onPlace(W.placing, [p.x, p.y, p.z, 0, 0, 0].map(v => Math.round(v * 100) / 100));
}
