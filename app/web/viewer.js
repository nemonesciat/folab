// ---------- FOLab 3D viewer ----------
// Shows one interior the way the game lays it out: every placed thing's mesh at its position, turn and
// scale, textured from the game's archives. Game units, Z up.
const T = THREE;
const $ = s => document.querySelector(s);
const V = {scene: null, cam: null, ren: null, group: null, models: {}, mats: {}, tex: {}, yaw: 0, pitch: -0.3,
           keys: {}, things: [], cell: null, token: 0};

function api(path){ return fetch(path).then(r => { if (!r.ok) throw new Error(path + ' ' + r.status); return r.json(); }); }

// ---------- textures (a few at a time; the same file is fetched once) ----------
const TQ = {active: 0, max: 8, waiting: []};
function texNext(){ while (TQ.active < TQ.max && TQ.waiting.length){ TQ.active++; TQ.waiting.shift()(); } }
function texture(path){
  if (V.tex[path]) return V.tex[path];
  V.tex[path] = new Promise(done => {
    TQ.waiting.push(() => new T.DDSLoader().load('/api/file?path=' + encodeURIComponent(path), tex => {
      // a DDS whose mip chain stops early draws black in WebGL: keep only the top level then
      const full = Math.floor(Math.log2(Math.max(tex.image.width || 1, tex.image.height || 1))) + 1;
      if (!tex.mipmaps || tex.mipmaps.length < full){ tex.minFilter = T.LinearFilter; tex.generateMipmaps = false; if (tex.mipmaps) tex.mipmaps = tex.mipmaps.slice(0, 1); }
      tex.wrapS = tex.wrapT = T.RepeatWrapping;
      TQ.active--; texNext(); done(tex);
    }, undefined, () => { TQ.active--; texNext(); done(null); }));
    texNext();
  });
  return V.tex[path];
}

function material(tex, alpha, double){
  const k = tex + '|' + alpha + '|' + double;
  if (V.mats[k]) return V.mats[k];
  // plain sand colour until the texture arrives (and for the few shapes that have none)
  const m = new T.MeshLambertMaterial({color: tex ? 0xffffff : 0xb8a888, side: double || alpha === 'blend' ? T.DoubleSide : T.FrontSide});
  if (alpha === 'test') m.alphaTest = 0.5;
  if (alpha === 'blend'){ m.transparent = true; m.depthWrite = false; }
  if (tex){
    m.color.set(0xb8a888);
    texture(tex).then(t => { if (t){ m.map = t; m.color.set(0xffffff); m.needsUpdate = true; } });
  }
  return V.mats[k] = m;
}

// ---------- meshes: built once per file, shared by every thing that uses it ----------
function model(path){
  if (!V.models[path]) V.models[path] = api('/api/mesh?path=' + encodeURIComponent(path)).then(d => {
    const parts = [];
    for (const s of d.shapes || []){
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.Float32BufferAttribute(s.p, 3));
      if (s.uv.length === s.p.length / 3 * 2) g.setAttribute('uv', new T.Float32BufferAttribute(s.uv, 2));
      g.setIndex(s.i);
      g.computeVertexNormals();
      parts.push([g, material(s.tex, s.alpha, s.double), s.alpha === 'blend']);
    }
    return parts;
  }).catch(() => []);
  return V.models[path];
}

// ---------- scene ----------
function init(){
  const box = $('#view');
  V.ren = new T.WebGLRenderer({antialias: true});
  V.ren.setPixelRatio(window.devicePixelRatio);
  box.appendChild(V.ren.domElement);
  V.scene = new T.Scene();
  V.scene.background = new T.Color(0x0e0c0a);
  V.cam = new T.PerspectiveCamera(70, 1, 4, 60000);
  V.cam.up.set(0, 0, 1);
  V.scene.add(new T.HemisphereLight(0xfff1dd, 0x3a3428, 0.85));
  const sun = new T.DirectionalLight(0xffffff, 0.45); sun.position.set(0.4, -0.6, 1); V.scene.add(sun);
  V.lamp = new T.PointLight(0xffe2b0, 0.6, 3000); V.scene.add(V.lamp);
  const size = () => { const w = box.clientWidth, h = box.clientHeight; V.ren.setSize(w, h); V.cam.aspect = w / h; V.cam.updateProjectionMatrix(); };
  new ResizeObserver(size).observe(box); size();
  controls(V.ren.domElement);
  let last = performance.now();
  const frame = now => {
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    move(dt);
    V.lamp.position.copy(V.cam.position);
    V.ren.render(V.scene, V.cam);
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

function look(){
  const d = new T.Vector3(Math.cos(V.pitch) * Math.cos(V.yaw), Math.cos(V.pitch) * Math.sin(V.yaw), Math.sin(V.pitch));
  V.cam.lookAt(V.cam.position.clone().add(d));
  return d;
}

function move(dt){
  const k = V.keys, speed = (k.Shift ? 2400 : 700) * dt;
  const f = new T.Vector3(Math.cos(V.yaw), Math.sin(V.yaw), 0), r = new T.Vector3(Math.sin(V.yaw), -Math.cos(V.yaw), 0);
  const p = V.cam.position;
  if (k.w) p.addScaledVector(f, speed); if (k.s) p.addScaledVector(f, -speed);
  if (k.d) p.addScaledVector(r, speed); if (k.a) p.addScaledVector(r, -speed);
  if (k.e) p.z += speed; if (k.q) p.z -= speed;
  look();
}

function controls(el){
  let drag = null;
  el.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, moved: 0}; el.setPointerCapture(e.pointerId); });
  el.addEventListener('pointermove', e => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
    V.yaw -= dx * 0.005; V.pitch = Math.max(-1.55, Math.min(1.55, V.pitch - dy * 0.005));
  });
  el.addEventListener('pointerup', e => { if (drag && drag.moved < 4) pick(e); drag = null; });
  el.addEventListener('wheel', e => { e.preventDefault(); V.cam.position.addScaledVector(look(), -Math.sign(e.deltaY) * (V.keys.Shift ? 800 : 200)); }, {passive: false});
  addEventListener('keydown', e => { if (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') return; V.keys[e.key.length === 1 ? e.key.toLowerCase() : e.key] = true; });
  addEventListener('keyup', e => { V.keys[e.key.length === 1 ? e.key.toLowerCase() : e.key] = false; });
  addEventListener('blur', () => { V.keys = {}; });
}

function pick(e){
  const rect = V.ren.domElement.getBoundingClientRect();
  const ray = new T.Raycaster();
  ray.setFromCamera({x: (e.clientX - rect.left) / rect.width * 2 - 1, y: -(e.clientY - rect.top) / rect.height * 2 + 1}, V.cam);
  const hit = ray.intersectObjects(V.group ? V.group.children : [], true).find(h => h.object.visible);
  const box = $('#pick');
  if (!hit){ box.style.display = 'none'; return; }
  let o = hit.object; while (o && !o.userData.thing) o = o.parent;
  const t = o.userData.thing;
  box.style.display = 'block';
  box.textContent = `${t.type} ${t.base}${t.name ? ' — ' + t.name : ''} · ${t.model} · ref ${t.ref} · (${t.p.slice(0, 3).map(Math.round).join(', ')})`;
}

// ---------- a cell ----------
async function open(id){
  const token = ++V.token;
  document.querySelectorAll('.row').forEach(r => r.classList.toggle('on', r.dataset.id === id));
  $('#pick').style.display = 'none';
  $('#status').textContent = 'loading…';
  const c = await api('/api/cell?id=' + id);
  if (token !== V.token) return;
  if (V.group) V.scene.remove(V.group);
  V.group = new T.Group(); V.scene.add(V.group);
  V.cell = c; V.things = [];
  $('#title').textContent = c.edid;
  const showMarkers = $('#markers').checked;
  const bounds = new T.Box3();
  for (const t of c.things){ if (!t.marker) bounds.expandByPoint(new T.Vector3(t.p[0], t.p[1], t.p[2])); }
  // start at the middle of the place, a little above it, looking across
  const mid = bounds.getCenter(new T.Vector3()), sz = bounds.getSize(new T.Vector3());
  V.cam.position.set(mid.x - sz.x * 0.35, mid.y - sz.y * 0.35, mid.z + 300); V.yaw = Math.PI / 4; V.pitch = -0.35;
  let done = 0, failed = 0;
  const status = () => { if (token === V.token) $('#status').textContent = `${done} / ${c.things.length} things${failed ? ` · ${failed} meshes unreadable` : ''}`; };
  await Promise.all(c.things.map(async t => {
    const parts = await model(t.model);
    if (token !== V.token) return;
    done++; if (!parts.length) failed++;
    const g = new T.Group();
    g.position.set(t.p[0], t.p[1], t.p[2]);
    g.rotation.set(-t.p[3], -t.p[4], -t.p[5], 'XYZ');
    g.scale.setScalar(t.s);
    g.userData.thing = t;
    for (const [geo, mat, blend] of parts){ const m = new T.Mesh(geo, mat); if (blend) m.renderOrder = 1; g.add(m); }
    g.visible = !t.marker || showMarkers;
    V.group.add(g); V.things.push(g);
    if (done % 50 === 0 || done === c.things.length) status();
  }));
  status();
}

$('#markers').addEventListener('change', e => { for (const g of V.things) if (g.userData.thing.marker) g.visible = e.target.checked; });

// ---------- the list of interiors ----------
async function start(){
  init();
  const all = await api('/api/interiors');
  const list = $('#list');
  const draw = () => {
    const f = $('#filter').value.toLowerCase();
    list.innerHTML = '';
    for (const c of all){
      if (f && !(c.edid + ' ' + c.name).toLowerCase().includes(f)) continue;
      const row = document.createElement('div');
      row.className = 'row'; row.dataset.id = c.id;
      row.innerHTML = `<div>${c.name || c.edid}<small>${c.edid} · ${c.plugin}</small></div><span class="n">${c.refs}</span>`;
      row.onclick = () => open(c.id);
      list.appendChild(row);
    }
  };
  $('#filter').addEventListener('input', draw);
  draw();
  const want = new URLSearchParams(location.search).get('cell');
  const first = all.find(c => c.edid.toLowerCase() === (want || '2EOVault21').toLowerCase());
  if (first) open(first.id);
}
start();
