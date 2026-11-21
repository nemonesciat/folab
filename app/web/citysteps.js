// ---------- Real map: the city's steps after the buildings (api_maps' landmarks, dress, coast, hotels, green, plants, life) ----------
// Waikiki got each of these from a script; here they're buttons on the Real map panel, in the order that worked: landmarks
// before buildings (buildings keep off them), then things on the ground (roads bedded, ground eased, lying things seated),
// the coast and its hotels, the ground and plants, and last who lives there. Each is one Undo, with the OpenStreetMap file
// picked above.
const CS = {sets: null, sites: [], placing: null, harbour: true, plants: '', more: 'jungle', thick: 1, hotels: 4, settlement: '', port: ''};

(function csCss(){
  const c = document.createElement('style');
  c.textContent = `.cs-site{display:flex;gap:6px;align-items:center;font-size:12px;margin:2px 0} .cs-site input{width:52px}
  .cs-step{border-top:1px solid var(--line);padding-top:6px;margin-top:6px}`;
  document.head.appendChild(c);
})();

{ const t = WT.tabs.realmap, was = t.draw; t.draw = async function(box){ await was(box); try { await csAdd(box); } catch (e){ console.error(e); } }; }   // (the tab holds moDraw itself)

async function csAdd(box){
  if (!MO.side) return;
  if (!CS.sets) CS.sets = await api('/api/maps/sets').catch(() => ({landmarks: [], plants: []}));
  const grow = [...box.querySelectorAll('h4')].find(h => /Grow this map/.test(h.textContent));
  const sec = document.createElement('div');
  const label = k => (CS.sets.landmarks.find(s => s.key === k) || {}).label || k;
  sec.innerHTML = `<h4>Build the city, step by step</h4>
    <div class="note">Each step is one Undo and uses the OpenStreetMap file picked above. In this order: landmarks before the buildings, then the rest after.</div>
    <div class="cs-step"><b>Landmarks</b>
      <div class="note">Great buildings stood where you click on the map: the game's (the Lucky 38, the Tops…) or FOLab's own. Each levels its ground and keeps off the roads.</div>
      <div class="wt-row"><span>Which</span><select id="cs-set">${CS.sets.landmarks.map(s => `<option value="${esc(s.key)}">${esc(s.label)}</option>`).join('')}</select>
        <button class="btn${CS.placing ? ' on' : ''}" id="cs-place">${CS.placing ? 'Click the map…' : 'Put one on the map'}</button></div>
      ${CS.sites.map((s, n) => `<div class="cs-site">${esc(label(s.set))} at ${Math.round(s.x)}, ${Math.round(s.y)}
        <span>facing</span><input data-csturn="${n}" placeholder="best" value="${s.deg == null ? '' : s.deg}">°
        <button class="btn" data-csdel="${n}">✕</button></div>`).join('')}
      <label style="display:block"><input type="checkbox" id="cs-harbour" ${CS.harbour ? 'checked' : ''}> and piers and boats where the map has piers over water</label>
      <div class="wt-go"><button class="btn primary" id="cs-land"${CS.sites.length || CS.harbour ? '' : ' disabled'}>Stand them</button></div></div>
    <div class="cs-step"><b>Things on the ground</b>
      <div class="note">By what the map says each place is, along the roads, round each building, on empty plots; camps and roadblocks. Then the roads bedded into the ground, the ground eased beside them, and what lies on it seated.</div>
      <div class="wt-row"><span>Plants</span><select id="cs-plants">
        ${[['', "The game's own"], ['beach', "The game's, and FOLab's palms and banana plants too"], ['beach instead', "FOLab's in place of the game's"]].map(([v, l]) => `<option value="${v}" ${v === CS.plants ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
      <div class="wt-go"><button class="btn primary" id="cs-dress">Dress the city</button></div></div>
    <div class="cs-step"><b>The coast</b>
      <div class="note">What the map has by the sea (a lighthouse, an aquarium, masts, groynes, wrecks), and hotels along the shore.</div>
      <div class="wt-go"><button class="btn" id="cs-coast">The coast's things</button>
        <span>Hotels</span> <input id="cs-hotels" type="number" min="1" max="12" style="width:50px" value="${CS.hotels}"> <button class="btn" id="cs-hotel-go">Stand hotels</button></div></div>
    <div class="cs-step"><b>Ground and plants</b>
      <div class="note">The desert's bare brown painted green on wild ground, then FOLab's own plants over what already grows. Afterwards, Big jobs' plants job keeps them to what the game can draw.</div>
      <div class="wt-go"><button class="btn" id="cs-green">Paint the wild ground green</button></div>
      <div class="wt-row"><span>Plants</span><select id="cs-more">${CS.sets.plants.map(p => `<option ${p === CS.more ? 'selected' : ''}>${esc(p)}</option>`).join('')}</select>
        <span>thickness</span><input id="cs-thick" type="number" min="0.2" max="3" step="0.1" style="width:55px" value="${CS.thick}">
        <button class="btn" id="cs-plant">Plant</button></div></div>
    <div class="cs-step"><b>Who lives there</b>
      <div class="note">Zones that get harder away from where the game starts (set that first: Mod page, your own new game), names on the map, people at the camps the dressing made, animals by the ground, a settlement.</div>
      <div class="wt-row"><span>Settlement</span><input id="cs-settle" placeholder="(none)" value="${esc(CS.settlement)}"></div>
      <div class="wt-row"><span>Harbour's name</span><input id="cs-port" placeholder="(none)" value="${esc(CS.port)}"></div>
      <div class="wt-go"><button class="btn primary" id="cs-life">Bring it to life</button></div></div>`;
  if (grow) box.insertBefore(sec, grow); else box.appendChild(sec);
  const q = s => sec.querySelector(s);
  const need = () => {
    if (!MO.file){            // (back another day: the one map file used before, if there's only one)
      const k = box.querySelector('#mo-kept'), opts = k ? [...k.options].filter(o => o.value) : [];
      if (opts.length === 1) MO.file = opts[0].value;
    }
    if (!MO.file){ toast('Pick the OpenStreetMap file of this world first (above).', true); return false; }
    return true;
  };
  q('#cs-place').onclick = () => { CS.placing = CS.placing ? null : q('#cs-set').value; wtDraw(); M.dirty = true; };
  q('#cs-harbour').onchange = e => { CS.harbour = e.target.checked; };
  sec.querySelectorAll('[data-csdel]').forEach(b => b.onclick = () => { CS.sites.splice(+b.dataset.csdel, 1); wtDraw(); M.dirty = true; });
  sec.querySelectorAll('[data-csturn]').forEach(i => i.onchange = () => { const v = i.value.trim(); CS.sites[+i.dataset.csturn].deg = v === '' ? null : +v; });
  q('#cs-plants').onchange = e => { CS.plants = e.target.value; };
  q('#cs-more').onchange = e => { CS.more = e.target.value; };
  q('#cs-thick').onchange = e => { CS.thick = +e.target.value || 1; };
  q('#cs-hotels').onchange = e => { CS.hotels = +e.target.value || 4; };
  q('#cs-settle').onchange = e => { CS.settlement = e.target.value.trim(); };
  q('#cs-port').onchange = e => { CS.port = e.target.value.trim(); };
  q('#cs-land').onclick = () => need() && csRun('/api/maps/landmarks', {
    sites: CS.sites.map(s => ({set: s.set, x: s.x, y: s.y, turn: s.deg == null ? null : s.deg * Math.PI / 180})), harbour: CS.harbour},
    'Landmarks', () => { CS.sites = []; });
  q('#cs-dress').onclick = () => need() && csRun('/api/maps/dress', {plants: CS.plants || undefined}, 'Things on the ground');
  q('#cs-coast').onclick = () => need() && csRun('/api/maps/coast', {}, 'The coast');
  q('#cs-hotel-go').onclick = () => need() && csRun('/api/maps/hotels', {count: CS.hotels}, 'Hotels');
  q('#cs-green').onclick = () => need() && csRun('/api/maps/green', {}, 'Green ground');
  q('#cs-plant').onclick = () => need() && csRun('/api/maps/plants', {set: CS.more, thick: CS.thick}, 'Plants');
  q('#cs-life').onclick = () => need() && csRun('/api/maps/life', {settlement: CS.settlement || undefined, harbour: CS.port || undefined}, 'Life');
}

function csSay(title, rep){
  // (each step's report in a line: its numbers, and the lengths of its lists)
  const bits = [];
  for (const [k, v] of Object.entries(rep || {})){
    if (typeof v === 'number' && v) bits.push(`${v.toLocaleString()} ${k.replace(/_/g, ' ')}`);
    else if (Array.isArray(v) && v.length && k !== 'cell_xy') bits.push(`${v.length.toLocaleString()} ${k.replace(/_/g, ' ')}`);
  }
  return `<b>${esc(title)}: done.</b> ${esc(bits.slice(0, 10).join(', '))}${bits.length ? '.' : ''}`;
}

function csRun(path, body, title, after){
  if (!confirm(`${title}: run it on this world? It's one Undo.`)) return;
  moJob(post(path, Object.assign({world: OUT.world, file: MO.file}, body)), async r => {
    if (r.state) setState(r.state);
    MO.said = csSay(title, r.report);
    if (after) after();
    await outsideResync();
    if (typeof mapLandChanged === 'function') mapLandChanged();
    if (r.report && r.report.cell_xy && r.report.cell_xy.length) wnOffer(r.report.cell_xy);
  });
}

// placing landmark sites on the map, and drawing them
{ const t = WT.tabs.realmap;
  const draw = t.map, mouse = t.mouse;
  t.map = g => {
    if (draw) draw(g);
    g.lineWidth = 2; g.strokeStyle = '#f0cd87'; g.fillStyle = 'rgba(240,205,135,0.25)';
    for (const s of CS.sites){ const [x, y] = mapScreen(s.x, s.y); g.beginPath(); g.arc(x, y, 10, 0, Math.PI * 2); g.fill(); g.stroke(); }
  };
  t.mouse = (kind, e) => {
    if (CS.placing && kind === 'down' && e.button === 0){
      const [x, y] = mapWorld(e.offsetX, e.offsetY);
      CS.sites.push({set: CS.placing, x, y, deg: null}); CS.placing = null;
      wtDraw(); M.dirty = true;
      return true;
    }
    return mouse ? mouse(kind, e) : false;
  };
}
