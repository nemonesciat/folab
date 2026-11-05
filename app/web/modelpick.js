// ---------- Models: a turning preview, and a picker over every mesh the game has ----------
// One small renderer, moved to wherever a preview is wanted (the Create page's item, or the picker). Meshes come
// through the 3D view's own loader (world.js model()), so a mesh drawn once is drawn from memory after that.
const MP = {ren: null, scene: null, cam: null, obj: null, token: 0, spin: 0, last: 0, bounds: null, box: null};

function mpInit(){
  if (MP.ren) return;
  MP.ren = new T.WebGLRenderer({antialias: true, alpha: true});
  MP.ren.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  MP.scene = new T.Scene();
  MP.cam = new T.PerspectiveCamera(32, 1, 0.5, 50000);
  MP.cam.up.set(0, 0, 1);                                  // (the game's up is z)
  MP.scene.add(new T.HemisphereLight(0xfff2dc, 0x3a3226, 1.0));
  const sun = new T.DirectionalLight(0xffffff, 0.7);
  sun.position.set(1, -2, 3);
  MP.scene.add(sun);
  const frame = t => {
    requestAnimationFrame(frame);
    const c = MP.ren.domElement;
    if (!c.isConnected || !MP.obj) return;
    MP.spin += Math.min(t - MP.last, 50) * 0.0005; MP.last = t;
    MP.obj.rotation.z = MP.spin;
    MP.ren.render(MP.scene, MP.cam);
  };
  requestAnimationFrame(frame);
}

// Show meshes\<path> in el (a sized box). Resolves to the mesh's bounds [x1, y1, z1, x2, y2, z2], or null if it has
// nothing to draw.
async function mpShow(el, path){
  mpInit();
  const c = MP.ren.domElement, w = el.clientWidth || 240, h = el.clientHeight || 240;
  if (c.parentNode !== el){ el.innerHTML = ''; el.appendChild(c); }
  MP.ren.setSize(w, h);
  MP.cam.aspect = w / h; MP.cam.updateProjectionMatrix();
  const token = ++MP.token;
  if (MP.obj){ MP.scene.remove(MP.obj); MP.obj = null; }
  MP.bounds = null;
  if (!path) return null;
  const parts = await model('meshes\\' + path);
  if (token !== MP.token) return null;
  const g = new T.Group();
  for (const [geo, mat] of parts) g.add(new T.Mesh(geo, mat));
  const box = new T.Box3().setFromObject(g);
  if (box.isEmpty()){ el.dataset.empty = '1'; return null; }
  delete el.dataset.empty;
  const mid = box.getCenter(new T.Vector3()), size = box.getSize(new T.Vector3());
  const inner = new T.Group();                              // (turns about its own middle)
  g.position.sub(mid);
  inner.add(g);
  MP.obj = inner; MP.scene.add(inner);
  const r = Math.max(size.length() / 2, 1);
  const dist = r / Math.sin(MP.cam.fov * Math.PI / 360) * 1.05;
  MP.cam.position.set(dist * 0.55, -dist * 0.75, dist * 0.35);
  MP.cam.lookAt(0, 0, 0);
  MP.cam.near = dist / 100; MP.cam.far = dist * 10; MP.cam.updateProjectionMatrix();
  return MP.bounds = [box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z].map((v, i) => i < 3 ? Math.floor(v) : Math.ceil(v));
}

// The picker: search every mesh, click one to see it, Use this to take it. onPick(path, bounds).
function mpPick(current, onPick){
  const folder = (current || '').split('\\').slice(0, -1).join('\\');
  const box = document.createElement('div');
  box.id = 'mp-pick';
  box.innerHTML = `<div class="mp-card">
    <div class="mp-head"><b>Pick a model</b><button class="btn" data-mp="close">✕</button></div>
    <div class="mp-body">
      <div class="mp-left"><input class="find" id="mp-q" placeholder="Search: folder or name, e.g. weapons pistol" value="${esc(folder)}" style="margin:0 0 6px;width:100%">
        <div class="note" id="mp-n" style="padding:0 0 4px"></div><div class="list" id="mp-list"></div></div>
      <div class="mp-right"><div id="mp-view"></div><div class="note" id="mp-path" style="padding:6px 0;word-break:break-all"></div>
        <button class="btn primary" data-mp="use" disabled>Use this</button></div>
    </div></div>`;
  document.body.appendChild(box);
  let chosen = null, timer, token = 0;
  const list = async () => {
    const t = ++token, d = await api('/api/meshes?q=' + encodeURIComponent(box.querySelector('#mp-q').value));
    if (t !== token) return;
    box.querySelector('#mp-n').textContent = `${d.total} mesh${d.total === 1 ? '' : 'es'}${d.total > d.paths.length ? ', the first ' + d.paths.length + ' shown' : ''}`;
    box.querySelector('#mp-list').innerHTML = d.paths.map(p => `<div class="row${p === chosen ? ' on' : ''}" data-p="${esc(p)}"><div>${esc(p.split('\\').pop())}<small>${esc(p.split('\\').slice(0, -1).join('\\'))}</small></div></div>`).join('');
  };
  const show = async p => {
    chosen = p;
    box.querySelectorAll('#mp-list .row').forEach(r => r.classList.toggle('on', r.dataset.p === p));
    box.querySelector('#mp-path').textContent = p;
    const b = await mpShow(box.querySelector('#mp-view'), p);
    box.querySelector('[data-mp="use"]').disabled = !b;
    if (!b) box.querySelector('#mp-path').textContent = p + ' (nothing FOLab can draw in it)';
  };
  const close = () => { box.remove(); document.removeEventListener('keydown', key, true); };
  const key = e => { if (e.key === 'Escape'){ e.stopPropagation(); close(); } };
  document.addEventListener('keydown', key, true);
  box.querySelector('#mp-q').oninput = () => { clearTimeout(timer); timer = setTimeout(list, 200); };
  box.querySelector('#mp-list').onclick = e => { const r = e.target.closest('[data-p]'); if (r) show(r.dataset.p); };
  box.onclick = e => {
    const a = e.target.dataset.mp;
    if (a === 'close' || e.target === box) close();
    if (a === 'use' && chosen){ const b = MP.bounds; close(); onPick(chosen, b); }
  };
  list();
  if (current) show(current.toLowerCase());
  box.querySelector('#mp-q').focus();
}
