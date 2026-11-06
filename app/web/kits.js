// ---------- Building from the game's kits ----------
// Select a building piece: Selected shows its open sides (green panels in the view too); pick a side and it lists what
// the game's pieces can join there, the joins the game itself built first. Hover shows it in place, click puts it there
// and selects it, so a corridor grows piece by piece. The Kit tab fills an area with a whole layout.
const KIT = {piece: null, side: null, marks: null, ghost: null, ghostFor: null, list: null, last: null, token: 0};
const KIT_DIRS = ['East', 'North', 'West', 'South'];

// ---------- one piece: its sides and what joins them ----------
function kitDrop(){
  kitGhostOff();
  if (KIT.marks){ W.scene.remove(KIT.marks); KIT.marks = null; }
  KIT.piece = KIT.side = null;
  const box = $('#kit-joins'); if (box) box.innerHTML = '';
}

async function kitSelected(list){
  const token = ++KIT.token;
  if (list.length !== 1 || !A.cellId || A.outside){ kitDrop(); return; }
  const t = list[0];
  if (KIT.piece && KIT.piece.thing === t.key && KIT.piece.at === t.p.join()) return;
  let d;
  try { d = await api(`/api/kit/piece?cell=${encodeURIComponent(A.cellId)}&key=${encodeURIComponent(t.key)}`); }
  catch (e){ return; }
  if (token !== KIT.token) return;
  kitDrop();
  if (!d.kit) return;
  KIT.piece = {...d, thing: t.key, at: t.p.join()};
  kitMarks();
  kitDraw();
}

function kitDraw(){
  const box = $('#kit-joins'), P = KIT.piece; if (!box || !P) return;
  const free = P.sides.filter(s => !s.taken);
  box.innerHTML = `<div class="h">Joins <small style="text-transform:none;letter-spacing:0">${esc(P.label)} kit</small></div>
    ${P.turned ? '<div class="note">It isn\'t turned square, so nothing lines up with it. Turn it to a quarter turn to join on to it.</div>' : !free.length
      ? `<div class="note">${P.sides.length ? 'Every way through has something joined to it.' : 'No way through: nothing joins this side on.'}</div>`
      : `<div class="kit-sides">${P.sides.map((s, i) => `<button data-side="${i}" class="${KIT.side === i ? 'on' : ''}" ${s.taken ? 'disabled title="Something is already joined here"' : ''}>${KIT_DIRS[s.face]}${P.sides.filter(x => x.face === s.face).length > 1 ? ' ' + (1 + P.sides.filter(x => x.face === s.face).indexOf(s)) : ''}<small>${s.taken ? 'joined' : s.fits.length}</small></button>`).join('')}</div>
         ${KIT.side === null ? '<div class="note">Pick a side (or click a green panel in the view).</div>' : ''}
         <div id="kit-fits"></div>`}`;
  if (KIT.side !== null) kitFits();
}

function kitFits(){
  const s = KIT.piece.sides[KIT.side], box = $('#kit-fits'); if (!box || !s) return;
  const line = (o, i) => `<div class="row kit-fit" data-fit="${i}"><span class="r1">${esc(o.edid)}</span><small>${o.times ? `the game: ${o.times} ×` : 'same shape'}${o.ways <= 1 ? ' · closes it off' : o.ways > 2 ? ` · ${o.ways - 1} ways on` : ''}</small></div>`;
  box.innerHTML = s.fits.length ? s.fits.map(line).join('') : '<div class="note">Nothing in this kit fits this side.</div>';
}

$('#right').addEventListener('click', e => {
  const b = e.target.closest('[data-side]');
  if (b && !b.disabled){ KIT.side = +b.dataset.side; kitMarks(); kitDraw(); return; }
  const f = e.target.closest('[data-fit]');
  if (f) kitPlace(KIT.piece.sides[KIT.side].fits[+f.dataset.fit]);
});
$('#right').addEventListener('mouseover', e => {
  const f = e.target.closest('[data-fit]');
  if (f && KIT.piece && KIT.side !== null) kitGhost(KIT.piece.sides[KIT.side].fits[+f.dataset.fit]);
});
$('#right').addEventListener('mouseout', e => { if (e.target.closest('[data-fit]')) kitGhostOff(); });

async function kitPlace(o){
  kitGhostOff();
  KIT.side = null;
  await edit('Join ' + o.edid, [{op: 'add', cell: A.cellId, base: o.key, p: o.p, s: 1}], true);
}

async function kitGhost(o){
  if (KIT.ghostFor === o) return;
  kitGhostOff();
  KIT.ghostFor = o;
  const {parts, scale} = await thingParts({bkey: o.key, key: o.key, type: 'STAT', model: o.model});
  if (KIT.ghostFor !== o) return;
  const g = new T.Group();
  for (const [geo, mat] of parts){ const m = new T.Mesh(geo, mat); m.raycast = () => {}; g.add(m); }
  g.position.set(o.p[0], o.p[1], o.p[2]); g.rotation.set(0, 0, -o.p[5], 'XYZ'); g.scale.setScalar(scale);
  KIT.ghost = g; W.scene.add(g);
}
function kitGhostOff(){
  KIT.ghostFor = null;
  if (KIT.ghost){ W.scene.remove(KIT.ghost); KIT.ghost = null; }
}

// the green panels: one in each way through with nothing joined to it
function kitMarks(){
  if (KIT.marks){ W.scene.remove(KIT.marks); KIT.marks = null; }
  const P = KIT.piece; if (!P) return;
  const g = new T.Group();
  P.sides.forEach((s, i) => {
    if (s.taken) return;
    const on = KIT.side === i;
    const m = new T.Mesh(new T.PlaneGeometry(Math.max(32, s.width), 150),
      new T.MeshBasicMaterial({color: on ? 0x8affac : 0x3df27a, transparent: true, opacity: on ? 0.55 : 0.28, side: T.DoubleSide, depthWrite: false}));
    m.position.set(s.at[0], s.at[1], s.at[2] + 75);
    // (the plane starts flat, facing up: stand it up, then face it the way the side faces)
    m.rotation.set(Math.PI / 2, 0, 0); m.rotateY((s.face % 2 ? 0 : Math.PI / 2));
    m.userData.side = i;
    g.add(m);
  });
  KIT.marks = g; W.scene.add(g);
}

// a click on a green panel picks that side, and nothing else happens to the click
function kitMarkAt(e){
  if (!KIT.marks || !KIT.marks.children.length) return null;
  const r = W.ren.domElement.getBoundingClientRect();
  const ray = new T.Raycaster();
  ray.setFromCamera(new T.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), W.cam);
  const hit = ray.intersectObjects(KIT.marks.children)[0];
  return hit ? hit.object.userData.side : null;
}
let kitSwallow = false;
$('#view').addEventListener('pointerdown', e => {
  if (e.button !== 0 || e.target !== W.ren.domElement) return;
  const i = kitMarkAt(e);
  if (i === null) return;
  kitSwallow = true;
  e.stopPropagation();
  KIT.side = i; kitMarks(); kitDraw();
}, true);
$('#view').addEventListener('pointerup', e => { if (kitSwallow){ kitSwallow = false; e.stopPropagation(); } }, true);

// ---------- the Kit tab: a whole layout ----------
async function kitTab(){
  const box = $('#tab-kit'); if (!box) return;
  let d;
  try { d = await api('/api/kits'); } catch (e){ box.innerHTML = '<div class="note">Could not read the kits.</div>'; return; }
  if (d.building){
    box.innerHTML = '<div class="note">Reading the game\'s building kits, about a minute the first time…</div>';
    setTimeout(() => { if ($('#tab-kit').classList.contains('on')) kitTab(); }, 3000);
    return;
  }
  if (d.error){ box.innerHTML = `<div class="note">Could not read the kits: ${esc(d.error)}</div>`; return; }
  KIT.list = d.kits;
  const was = KIT.pick || (d.kits.find(k => k.name === 'dungeons\\vault') || d.kits[0] || {}).name;
  box.innerHTML = `<div class="h">Generate a layout</div>
    <div class="note" style="padding:0 0 6px">Fills an area with the game's own pieces, each side joining what's beside it, every way out closed off. Best in an empty place of your own (<b>+ New</b> under Places).</div>
    <label class="vt-row">Kit <select id="kit-pick">${d.kits.map(k => `<option value="${esc(k.name)}" ${k.name === was ? 'selected' : ''}>${esc(k.label)} (${k.tiles})</option>`).join('')}</select></label>
    <label class="vt-row">Size <input type="number" id="kit-w" min="2" max="40" value="${KIT.w || 10}" style="width:60px"> × <input type="number" id="kit-h" min="2" max="40" value="${KIT.h || 10}" style="width:60px"> squares</label>
    <div class="kit-go"><button class="primary" id="kit-make">Generate</button> <button id="kit-again" ${KIT.last ? '' : 'disabled'} title="Undo that layout and try another">Try another</button></div>
    <div class="note" id="kit-said" style="padding:6px 0">${KIT.said || ''}</div>
    <div class="note" style="padding:0">Not there yet: stairs and big pieces, lights and furnishings, and a navmesh, so characters can't walk it in game yet.</div>`;
  box.querySelector('#kit-pick').onchange = e => { KIT.pick = e.target.value; };
  box.querySelector('#kit-make').onclick = () => kitMake();
  box.querySelector('#kit-again').onclick = async () => {
    if (KIT.last && A.state.project && A.state.project.undo === KIT.last) await undoRedo('undo');
    kitMake();
  };
}

async function kitMake(){
  if (!A.cellId || A.outside) return toast('Open a place first: layouts go in places inside.', true);
  const kit = $('#kit-pick').value, w = +$('#kit-w').value || 10, h = +$('#kit-h').value || 10;
  KIT.pick = kit; KIT.w = w; KIT.h = h;
  const info = KIT.list.find(k => k.name === kit), step = info.step;
  // (where you're standing, on the kit's grid, at the height of what you're looking at or the place's floor)
  const at = [Math.round(W.cam.position.x / step) * step - Math.floor(w / 2) * step, Math.round(W.cam.position.y / step) * step - Math.floor(h / 2) * step, A.things && A.things.some(t => !t.marker) ? Math.round(W.floorZ || 0) : 0];
  KIT.seed = (KIT.seed || 0) + 1;
  const said = $('#kit-said'); said.textContent = 'Building…';
  const made = await post('/api/kit/layout', {kit, w, h, seed: KIT.seed + (Date.now() % 100000), at}).catch(e => { fail(e); return null; });
  if (!made) return (said.textContent = '');
  if (!made.ops){ KIT.said = said.textContent = made.note; return; }
  const label = `Generate ${info.label}`;
  const d = await edit(label, made.ops.map(o => ({...o, cell: A.cellId})));
  if (!d) return (said.textContent = '');
  KIT.last = label;
  KIT.said = `${made.ops.length} pieces. A walker starting inside couldn't get out.`;
  W.cam.position.set(made.start[0], made.start[1], made.start[2] + 110);
  await kitTab();
}

$('#right .tabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b && b.dataset.tab === 'kit') kitTab(); });

// (after the page's own handling of a selection)
{ const was = W.onSelect; W.onSelect = list => { was(list); kitSelected(list); }; }
