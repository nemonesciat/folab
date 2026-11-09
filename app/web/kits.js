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
    <div class="note" style="padding:0 0 6px">Plans rooms and corridors with a main route, side branches and ways round, stairs and tall rooms where the kit has them, then builds them from the game's own pieces, each side joining what's beside it, and walks it from the first room to every square. Best in an empty place of your own (<b>+ New</b> under Places).</div>
    <label class="vt-row">Kit <select id="kit-pick">${d.kits.map(k => `<option value="${esc(k.name)}" ${k.name === was ? 'selected' : ''}>${esc(k.label)} (${k.tiles})</option>`).join('')}</select></label>
    <label class="vt-row">Size <input type="number" id="kit-w" min="3" max="80" value="${KIT.w || 24}" style="width:60px"> × <input type="number" id="kit-h" min="3" max="80" value="${KIT.h || 24}" style="width:60px"> squares</label>
    <div class="kit-go"><button class="btn primary" id="kit-make">Generate</button> <button class="btn" id="kit-again" ${KIT.last ? '' : 'disabled'} title="Replace that layout with another">Try another</button></div>
    <div class="note" id="kit-said" style="padding:6px 0">${KIT.said || ''}</div>
    <div class="note" style="padding:0">Generating again replaces the last layout here.</div>
    <div class="h" style="margin-top:10px">A vault in one click</div>
    <div class="note" style="padding:0 0 6px">An entrance, a two-storey atrium with balconies, living quarters with washrooms and a rec room, the overseer's office and a reactor, built close together as one building, each room furnished for what it's for from the game's own vaults; a few left wrecked.</div>
    <label class="vt-row">Size <input type="range" id="kit-vault-size" min="1" max="10" value="${KIT.vaultSize || 4}" style="flex:1"> <span id="kit-vault-n">${KIT.vaultSize || 4}</span></label>
    <label class="vt-row"><input type="checkbox" id="kit-vault-ruin" ${KIT.ruined ? 'checked' : ''}> Ruined, with rubble</label>
    <div class="kit-go"><button class="btn primary" id="kit-vault">Make a vault</button></div>
    <div class="h" style="margin-top:10px">Grow this place</div>
    <div class="note" style="padding:0 0 6px">Adds a new wing, keeping what's built: one wall piece becomes a doorway, a corridor and rooms go on beyond it. Works on places from the game too.</div>
    <label class="vt-row">About <input type="number" id="kit-grow-area" min="20" max="400" value="${KIT.growArea || 80}" style="width:70px"> more squares</label>
    <div class="kit-go"><button class="btn" id="kit-grow">Grow it</button></div>
    <div class="h" style="margin-top:10px">Navmesh</div>
    <div id="nav-box"></div>`;
  navDraw();
  box.querySelector('#kit-pick').onchange = e => { KIT.pick = e.target.value; };
  box.querySelector('#kit-make').onclick = () => kitMake();
  box.querySelector('#kit-again').onclick = async () => {
    kitMake();
  };
  box.querySelector('#kit-vault-size').oninput = e => { KIT.vaultSize = +e.target.value; $('#kit-vault-n').textContent = e.target.value; };
  box.querySelector('#kit-vault-ruin').onchange = e => { KIT.ruined = e.target.checked; };
  box.querySelector('#kit-vault').onclick = () => kitVault();
  box.querySelector('#kit-grow').onclick = () => kitGrow();
}

// (a whole place: the last one goes in the same step, as two on one spot flicker where their surfaces meet)
async function kitPut(made, label, replace){
  const said = $('#kit-said');
  if (!made) return (said.textContent = '');
  if (!made.ops){ KIT.said = said.textContent = made.note; return; }
  const old = replace ? (A.things || []).filter(t => t.gen).map(t => ({op: 'remove', cell: A.cellId, ref: t.key})) : [];
  const d = await edit(label, old.concat(made.ops.map(o => ({...o, cell: A.cellId}))));
  if (!d) return (said.textContent = '');
  KIT.last = label;
  KIT.said = made.said;
  W.cam.position.set(made.start[0], made.start[1], made.start[2] + 110);
  await kitTab();
  await navMake();
  if (made.people) await kitPeople(made.people);
}

// a generated vault's people: Populate, learnt from the game's places its story names, once there's a navmesh to stand on
async function kitPeople(who){
  const cell = A.cellId, seed = (KIT.seed || 0) + 17;
  const said = s => { KIT.said = (KIT.said || '') + ' ' + s; const el = $('#kit-said'); if (el) el.innerHTML = KIT.said; };
  const plan = await post('/api/char/populate/plan', {cell, like: who.like, who: who.who, busy: who.busy, skip: who.skip, seed}).catch(() => null);
  if (!plan || !plan.rows || !plan.rows.length || cell !== A.cellId) return said(`Nobody was put in: ${(plan && plan.notes && plan.notes[0]) || 'Populate found no one.'}`);
  const r = await post('/api/char/populate/apply', {cell, rows: plan.rows, live: !!who.live, levelled: false, seed, away: who.away, gen: true}).catch(() => null);
  if (!r || !r.placed) return said(`Nobody was put in: ${(r && r.note) || 'no room.'}`);
  setState(r.state);
  await resync();
  said(`${r.placed} of ${who.said} put in, like ${plan.model}: Populate on the Characters page changes who.`);
}

function kitSpot(){
  const z = A.things && A.things.some(t => !t.marker) ? Math.round(W.floorZ || 0) : 0;
  return [Math.round(W.cam.position.x / 256) * 256, Math.round(W.cam.position.y / 256) * 256, z];
}

async function kitVault(){
  if (!A.cellId || A.outside) return toast('Open a place first: a vault goes in a place inside.', true);
  KIT.seed = (KIT.seed || 0) + 1;
  $('#kit-said').textContent = 'Building a vault…';
  const size = +$('#kit-vault-size').value, ruined = $('#kit-vault-ruin').checked;
  const made = await post('/api/kit/vault', {size, ruined, seed: KIT.seed + (Date.now() % 100000), at: kitSpot()}).catch(e => { fail(e); return null; });
  await kitPut(made, ruined ? 'Make a ruined vault' : 'Make a vault', true);
}

async function kitGrow(){
  if (!A.cellId || A.outside) return toast('Open a place first.', true);
  KIT.growArea = +$('#kit-grow-area').value || 80;
  KIT.seed = (KIT.seed || 0) + 1;
  $('#kit-said').textContent = 'Growing…';
  const made = await post('/api/kit/grow', {cell: A.cellId, area: KIT.growArea, seed: KIT.seed + (Date.now() % 100000)}).catch(e => { fail(e); return null; });
  await kitPut(made, 'Grow this place', false);
}

async function kitMake(){
  if (!A.cellId || A.outside) return toast('Open a place first: layouts go in places inside.', true);
  const kit = $('#kit-pick').value, w = +$('#kit-w').value || 24, h = +$('#kit-h').value || 24;
  KIT.pick = kit; KIT.w = w; KIT.h = h;
  const info = KIT.list.find(k => k.name === kit), step = info.step;
  // (where you're standing, on the kit's grid, at the height of what you're looking at or the place's floor)
  const at = [Math.round(W.cam.position.x / step) * step - Math.floor(w / 2) * step, Math.round(W.cam.position.y / step) * step - Math.floor(h / 2) * step, A.things && A.things.some(t => !t.marker) ? Math.round(W.floorZ || 0) : 0];
  KIT.seed = (KIT.seed || 0) + 1;
  const said = $('#kit-said'); said.textContent = 'Building…';
  const made = await post('/api/kit/layout', {kit, w, h, seed: KIT.seed + (Date.now() % 100000), at}).catch(e => { fail(e); return null; });
  await kitPut(made, `Generate ${info.label}`, true);
}

// ---------- the place's navmesh: where characters can walk ----------
async function navDraw(){
  const box = $('#nav-box'); if (!box) return;
  if (!A.cellId || A.outside){ box.innerHTML = '<div class="note" style="padding:0">Open a place inside to make it a navmesh. Outside, it\'s under 🧭 World tools, on the map.</div>'; return; }
  const cell = A.cellId;
  const s = await api('/api/navmesh/status?cell=' + encodeURIComponent(cell)).catch(() => null);
  if (!s || cell !== A.cellId) return;
  const words = s.mine ? (s.current ? `Up to date, ${s.triangles} triangles.` : `<b>Out of date:</b> things have changed since it was made. Make it again.`)
    : s.game ? `This place has the game's navmesh${s.game > 1 ? 'es' : ''}${s.game > 1 ? ': yours would replace the first, the rest are retired' : ', which yours would replace'}.`
    : 'None: characters can\'t find their way here in game.';
  box.innerHTML = `<div class="note" style="padding:0 0 6px">${words}</div>
    <div class="kit-go"><button class="btn" id="nav-make" ${s.can ? '' : 'disabled'}>${s.mine ? 'Make it again' : 'Make navmesh'}</button>
    ${s.mine ? '<button class="btn" id="nav-off">Remove</button>' : ''}</div>
    <label class="vt-row" style="margin-top:6px"><input type="checkbox" id="nav-show" ${KIT.navShow ? 'checked' : ''}> Show it in the view</label>
    <div class="note" id="nav-said" style="padding:6px 0 0">${KIT.navSaid || ''}</div>`;
  box.querySelector('#nav-make').onclick = navMake;
  if (s.mine) box.querySelector('#nav-off').onclick = async () => { const d = await post('/api/navmesh/remove', {cell: A.cellId}).catch(fail); if (d){ setState(d.state); KIT.navSaid = ''; navDraw(); navOverlay(); } };
  box.querySelector('#nav-show').onchange = e => { KIT.navShow = e.target.checked; navOverlay(); };
  navOverlay();
}

async function navMake(){
  if (!A.cellId || A.outside) return;
  const said = $('#nav-said'); if (said) said.textContent = 'Making the navmesh…';
  const d = await post('/api/navmesh/make', {cell: A.cellId}).catch(e => { fail(e); return null; });
  if (!d) return;
  if (d.note){ KIT.navSaid = d.note; toast(d.note, true); return navDraw(); }
  setState(d.state);
  const r = d.report;
  KIT.navSaid = `Made in ${Math.round(r.seconds || 0)} s.` + (r.doors ? ` ${r.doors} door${r.doors > 1 ? 's' : ''} linked.` : '') + (r.doors_missed ? ` <b>${r.doors_missed} door${r.doors_missed > 1 ? 's' : ''} too far from any floor.</b>` : '') + (r.cut_off ? ` ${r.cut_off} cut-off area${r.cut_off > 1 ? 's' : ''} left out: nothing leads there.` : '');
  navDraw();
}

// green over where it can walk
async function navOverlay(){
  if (KIT.navMesh){ W.scene.remove(KIT.navMesh); KIT.navMesh.geometry.dispose(); KIT.navMesh = null; }
  if (!KIT.navShow || !A.cellId || A.outside) return;
  const cell = A.cellId;
  const d = await api('/api/navmesh?cell=' + encodeURIComponent(cell)).catch(() => null);
  if (!d || !d.tris.length || cell !== A.cellId || !KIT.navShow) return;
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(d.verts.map((v, i) => i % 3 === 2 ? v + 4 : v), 3));
  g.setIndex(d.tris);
  const m = new T.Mesh(g, new T.MeshBasicMaterial({color: 0x3df27a, wireframe: true, transparent: true, opacity: 0.8, depthTest: true}));
  m.raycast = () => {};
  KIT.navMesh = m; W.scene.add(m);
}
{ const was = openPlace; openPlace = async (...a) => { const r = await was(...a); if ($('#tab-kit').classList.contains('on')) kitTab(); else navOverlay(); return r; }; }

$('#right .tabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b && b.dataset.tab === 'kit') kitTab(); });

// (after the page's own handling of a selection)
{ const was = W.onSelect; W.onSelect = list => { was(list); kitSelected(list); }; }
