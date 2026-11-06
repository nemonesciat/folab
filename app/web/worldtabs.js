// ---------- World tools: regions, zones, markers, cell details, roads and encounters, distant land ----------
const wtWorld = () => OUT.world;
const WC = {};                                       // lists to pick from, by type
async function wcList(types){ const k = types; if (!WC[k]) WC[k] = await api('/api/w/choices?types=' + encodeURIComponent(types)); return WC[k]; }
// a text box you type a name into, picking from a list; .dataset.key holds what was picked
function wcPicker(id, list, key, placeholder){
  const name = key ? (list.find(x => x.key === key) || {name: key}).name : '';
  if (!list.dl){            // (one list in the page for each kind, however many boxes use it: some have thousands)
    list.dl = 'wcdl' + (wcPicker.n = (wcPicker.n || 0) + 1);
    const d = document.createElement('datalist'); d.id = list.dl;
    d.innerHTML = list.map(x => `<option value="${esc(x.name)}">`).join('');
    document.body.appendChild(d);
  }
  return `<input id="${id}" list="${list.dl}" value="${esc(name)}" data-key="${esc(key || '')}" placeholder="${esc(placeholder || 'none')}">`;
}
function wcKey(el, list){ const v = el.value.trim(); if (!v) return ''; const r = list.find(x => x.name === v); return r ? r.key : null; }
const wtSave = (d) => { if (d && d.state) setState(d.state); return d; };
const wtPost = (path, body) => post(path, body).then(wtSave).catch(e => { fail(e); return null; });
const wtMouseSpot = e => { const [x, y] = mapWorld(e.offsetX, e.offsetY); return [x, y]; };

// ---------- Regions: paint on the map ----------
const RG = {list: [], sel: null, data: null, world: null, add: [], rem: []};
async function rgLoad(){
  if (!wtWorld()) return;
  const d = await api('/api/w/regions?world=' + encodeURIComponent(wtWorld())).catch(() => null);
  if (!d) return;
  RG.list = d.regions; RG.world = wtWorld(); M.dirty = true;
  if (WT.on && WT.tab === 'reg') rgListDraw();
}
function rgListDraw(){
  const box = $('#rg-list'); if (!box) return;
  box.innerHTML = RG.list.map(r => `<div class="row ${RG.sel === r.key ? 'on' : ''}" data-k="${esc(r.key)}"><span class="wt-key" style="background:${r.color}"></span><span>${esc(r.edid)}</span><small style="margin-left:auto">${r.cells.length}</small></div>`).join('') || '<div class="note" style="padding:4px 7px">No regions in this world.</div>';
}
function rgDraw(box){
  box.innerHTML = `<div class="note">A region gives its cells their weather, background sounds and, for the Scatter brush, a list of objects. Pick one, then drag on the map (Ctrl: take away).</div>
    <div class="wt-go"><button class="btn" id="rg-new">＋ New region</button></div>
    <div class="wt-list" id="rg-list"></div><div id="rg-form"></div>`;
  box.querySelector('#rg-new').onclick = () => rgOpen(null);
  box.querySelector('#rg-list').onclick = e => { const r = e.target.closest('[data-k]'); if (r) rgOpen(r.dataset.k); };
  rgListDraw(); rgForm(); rgLoad();
}
async function rgOpen(key){
  RG.sel = key;
  RG.data = key ? await api('/api/w/region?key=' + encodeURIComponent(key)).catch(e => { fail(e); return null; })
    : {edid: '', color: '#b08850', weathers: [], sounds: [], objects: [], priority: 50};
  rgListDraw(); rgForm(); M.dirty = true;
}
async function rgForm(){
  const box = $('#rg-form'); if (!box) return;
  const D = RG.data; if (!D){ box.innerHTML = ''; return; }
  const [wthr, soun] = await Promise.all([wcList('WTHR'), wcList('SOUN')]);
  const stats = await wcList('STAT,TREE,MSTT');
  const rows = (arr, cols, tag) => arr.map((w, i) => `<div class="row" style="cursor:default"><span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis" title="${esc(w.name)}">${esc(w.name)}</span>${cols(w, i)}<button data-del="${tag}:${i}" title="Take it off">✕</button></div>`).join('');
  box.innerHTML = `<h4>${RG.sel ? esc(D.edid) : 'A new region'}${D.mine ? '' : RG.sel ? ' <small>(the game\'s: saving changes it in your mod)</small>' : ''}</h4>
    <label class="wt-row"><span>Name</span><input id="rg-name" value="${esc(D.edid)}" placeholder="MyDustRegion"></label>
    <label class="wt-row"><span>Colour on the map</span><input type="color" id="rg-col" value="${D.color}"></label>
    <label class="wt-row"><span>Weather priority</span><input type="number" id="rg-pri" min="0" max="100" value="${D.priority}"></label>
    <h4>Weather (at most 8)</h4><div class="wt-list">${rows(D.weathers, (w, i) => `<input type="number" data-ch="w:${i}" min="0" max="100" value="${w.chance}" style="width:52px" title="Chance">`, 'w') || '<div class="note" style="padding:2px 7px">None: the world\'s climate.</div>'}</div>
    <div class="wt-row"><span>Add</span>${wcPicker('rg-aw', wthr, '', 'a weather…')}</div>
    <h4>Sounds</h4><div class="wt-list">${rows(D.sounds, (w, i) => `<input type="number" data-ch="s:${i}" min="0" max="100" value="${w.chance}" style="width:52px" title="Chance">`, 's') || '<div class="note" style="padding:2px 7px">None.</div>'}</div>
    <div class="wt-row"><span>Add</span>${wcPicker('rg-as', soun, '', 'a sound…')}</div>
    <h4>Objects, for the Scatter brush (at most 13)</h4><div class="wt-list">${rows(D.objects, (o, i) => `<input type="number" data-ch="o:${i}" min="0" max="100" step="0.5" value="${o.density}" style="width:52px" title="How many">`, 'o') || '<div class="note" style="padding:2px 7px">None.</div>'}</div>
    <div class="wt-row"><span>Add</span>${wcPicker('rg-ao', stats, '', 'a plant, rock…')}</div>
    <div class="wt-go"><button class="btn" id="rg-learn" title="What the game put round where the map's looking">Learn from the land here</button></div>
    <div class="wt-go"><button class="btn primary" id="rg-save">Save region</button><button class="btn" id="rg-clear" ${RG.sel ? '' : 'disabled'}>Stop painting</button></div>`;
  const list = {w: D.weathers, s: D.sounds, o: D.objects};
  box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => { const [t, i] = b.dataset.del.split(':'); list[t].splice(+i, 1); rgKeep(box); rgForm(); });
  box.querySelectorAll('[data-ch]').forEach(el => el.onchange = () => { const [t, i] = el.dataset.ch.split(':'); if (t === 'o') list.o[+i].density = +el.value; else list[t][+i].chance = +el.value; });
  const addFrom = (id, source, make) => { const el = box.querySelector(id); el.onchange = () => { const k = wcKey(el, source); if (!k) return; make(k, el.value.trim()); rgKeep(box); rgForm(); }; };
  addFrom('#rg-aw', wthr, (key, name) => { if (D.weathers.length < 8) D.weathers.push({key, name, chance: 30}); });
  addFrom('#rg-as', soun, (key, name) => D.sounds.push({key, name, flags: 0, chance: 30}));
  addFrom('#rg-ao', stats, (key, name) => { if (D.objects.length < 13) D.objects.push({key, name, density: 5, parent: 0, cluster: 0, slope_min: 0, slope_max: 45, flags: 0, parent_radius: 0, radius: 0, height_min: 0, height_max: 0, sink: 0, sink_var: 0, size_var: 0.2, ax: 0, ay: 0, az: 360}); });
  box.querySelector('#rg-learn').onclick = async () => {
    const d = await api(`/api/w/region/learn?world=${encodeURIComponent(wtWorld())}&x=${Math.floor(M.cx / 4096)}&y=${Math.floor(M.cy / 4096)}`).catch(e => { fail(e); return null; });
    if (d){ rgKeep(box); D.objects = d.objects; rgForm(); }
  };
  box.querySelector('#rg-clear').onclick = () => { RG.sel = null; RG.data = null; rgListDraw(); rgForm(); M.dirty = true; };
  box.querySelector('#rg-save').onclick = async () => {
    rgKeep(box);
    const d = await wtPost('/api/w/region/save', {world: wtWorld(), key: RG.sel, region: D});
    if (d){ RG.sel = d.key; toast('Region saved'); await rgLoad(); rgOpen(d.key); }
  };
}
function rgKeep(box){ const D = RG.data; if (!D) return; D.edid = box.querySelector('#rg-name').value.replace(/[^A-Za-z0-9_]/g, ''); D.color = box.querySelector('#rg-col').value; D.priority = +box.querySelector('#rg-pri').value; }
wtTab('reg', 'Regions', {
  draw: rgDraw,
  map(g){
    if (RG.world !== wtWorld()) rgLoad();
    if (4096 * M.z < 2) return;
    for (const r of RG.list){
      const on = r.key === RG.sel;
      if (RG.sel && !on) continue;
      if (!RG.sel && !r.cells.length) continue;
      const col = r.color + (on ? '70' : '30');
      for (const [x, y] of r.cells) wtFillCell(g, x, y, col, on ? r.color : null);
    }
    for (const [x, y] of RG.add) wtFillCell(g, x, y, 'rgba(255,255,255,0.3)');
    for (const [x, y] of RG.rem) wtFillCell(g, x, y, 'rgba(0,0,0,0.4)');
  },
  mouse(kind, e){
    if (!RG.sel) return false;
    RG.done = async () => {
      const add = RG.add, remove = RG.rem; RG.add = []; RG.rem = [];
      if (add.length || remove.length){ await wtPost('/api/w/region/paint', {world: wtWorld(), key: RG.sel, add, remove}); rgLoad(); }
    };
    return wtPaint(kind, e, RG, (c, on) => (on ? RG.add : RG.rem).push(c));
  },
});

// ---------- Encounter zones ----------
const ZN = {list: [], sel: null, world: null, add: [], rem: []};
async function znLoad(){
  if (!wtWorld()) return;
  const d = await api('/api/w/zones?world=' + encodeURIComponent(wtWorld())).catch(() => null);
  if (!d) return;
  ZN.list = d.zones; ZN.world = wtWorld(); M.dirty = true;
  if (WT.on && WT.tab === 'zone') znList();
}
const znCol = k => { let h = 0; for (const c of k) h = (h * 31 + c.charCodeAt(0)) % 360; return `hsl(${h},70%,55%)`; };
function znList(){
  const box = $('#zn-list'); if (!box) return;
  box.innerHTML = ZN.list.map(r => `<div class="row ${ZN.sel && ZN.sel.key === r.key ? 'on' : ''}" data-k="${esc(r.key)}"><span class="wt-key" style="background:${znCol(r.key)}"></span><span>${esc(r.edid)}</span><small style="margin-left:auto">level ${r.level}+ · ${(r.cells || []).length}</small></div>`).join('');
}
function znDraw(box){
  box.innerHTML = `<div class="note">A zone sets how tough what's there is, and whether it comes back. Pick one, then drag on the map (Ctrl: take away). <b>The game's zones only have a lowest level:</b> there's no highest one in its files.</div>
    <div class="wt-go"><button class="btn" id="zn-new">＋ New zone</button></div><div class="wt-list" id="zn-list"></div><div id="zn-form"></div>`;
  box.querySelector('#zn-new').onclick = () => { ZN.sel = {edid: '', level: 1, flags: 0, rank: 0, owner: '', fresh: true}; znForm(); znList(); };
  box.querySelector('#zn-list').onclick = e => { const r = e.target.closest('[data-k]'); if (r){ ZN.sel = ZN.list.find(z => z.key === r.dataset.k); znForm(); znList(); M.dirty = true; } };
  znList(); znForm(); znLoad();
}
async function znForm(){
  const box = $('#zn-form'); if (!box) return;
  const Z = ZN.sel; if (!Z){ box.innerHTML = ''; return; }
  const owners = await wcList('FACT');
  box.innerHTML = `<h4>${Z.fresh ? 'A new zone' : esc(Z.edid)}</h4>
    <label class="wt-row"><span>Name</span><input id="zn-name" value="${esc(Z.edid)}" placeholder="MyCanyonZone"></label>
    <label class="wt-row"><span>Lowest level</span><input type="number" id="zn-lvl" min="0" max="100" value="${Z.level}"></label>
    <label class="wt-row"><input type="checkbox" id="zn-never" ${Z.flags & 1 ? 'checked' : ''}> Never comes back: what's killed stays dead</label>
    <div class="wt-row"><span>Owned by</span>${wcPicker('zn-own', owners, Z.owner, 'nobody')}</div>
    <div class="wt-go"><button class="btn primary" id="zn-save">Save zone</button></div>`;
  box.querySelector('#zn-save').onclick = async () => {
    const owner = wcKey(box.querySelector('#zn-own'), owners);
    if (owner === null) return toast('No faction by that name.', true);
    const zone = {edid: box.querySelector('#zn-name').value.replace(/[^A-Za-z0-9_]/g, ''), level: +box.querySelector('#zn-lvl').value, flags: (Z.flags & ~1) | (box.querySelector('#zn-never').checked ? 1 : 0), rank: Z.rank || 0, owner};
    const d = await wtPost('/api/w/zone/save', {key: Z.fresh ? null : Z.key, zone});
    if (d){ toast('Zone saved'); await znLoad(); ZN.sel = ZN.list.find(z => z.key === d.key); WC.ECZN = null; znForm(); znList(); }
  };
}
wtTab('zone', 'Zones', {
  draw: znDraw,
  map(g){
    if (ZN.world !== wtWorld()) znLoad();
    for (const r of ZN.list){
      const on = ZN.sel && ZN.sel.key === r.key;
      if (ZN.sel && !on) continue;
      for (const [x, y] of r.cells || []) wtFillCell(g, x, y, znCol(r.key).replace('hsl', 'hsla').replace(')', on ? ',0.45)' : ',0.25)'), on ? znCol(r.key) : null);
    }
    for (const [x, y] of ZN.add) wtFillCell(g, x, y, 'rgba(255,255,255,0.3)');
    for (const [x, y] of ZN.rem) wtFillCell(g, x, y, 'rgba(0,0,0,0.4)');
  },
  mouse(kind, e){
    if (!ZN.sel || !ZN.sel.key) return false;
    ZN.done = async () => {
      const add = ZN.add, remove = ZN.rem; ZN.add = []; ZN.rem = [];
      if (add.length || remove.length){ await wtPost('/api/w/zone/paint', {world: wtWorld(), key: ZN.sel.key, add, remove}); znLoad(); }
    };
    return wtPaint(kind, e, ZN, (c, on) => (on ? ZN.add : ZN.rem).push(c));
  },
});

// ---------- Map markers ----------
const MK = {list: [], types: [], world: null, name: '', type: 3, show: true, travel: true};
async function mkLoad(){
  if (!wtWorld()) return;
  const d = await api('/api/w/markers?world=' + encodeURIComponent(wtWorld())).catch(() => null);
  if (!d) return;
  MK.list = d.markers; MK.types = d.types; MK.world = wtWorld(); M.dirty = true;
  if (WT.on && WT.tab === 'mark') mkRows();
}
function mkRows(){
  const box = $('#mk-rows'); if (!box) return;
  box.innerHTML = MK.list.map((m, i) => `<div class="row" data-i="${i}"><span>${esc(m.name)}</span><small>${esc(MK.types[m.type] || '')}</small><button data-del="${i}" title="Take it away">✕</button></div>`).join('') || '<div class="note" style="padding:4px 7px">None of yours in this world.</div>';
}
function mkDraw(box){
  box.innerHTML = `<div class="note">Fill these in, then click the map where it goes. It shows on the Pip-Boy's map, as the game's do, once you've found it or if you say it starts known.</div>
    <label class="wt-row"><span>Name</span><input id="mk-name" value="${esc(MK.name)}" placeholder="Dust Town"></label>
    <label class="wt-row"><span>Type</span><select id="mk-type">${(MK.types.length ? MK.types : ['None']).map((t, i) => `<option value="${i}" ${i === MK.type ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></label>
    <label class="wt-row"><input type="checkbox" id="mk-show" ${MK.show ? 'checked' : ''}> Known from the start</label>
    <label class="wt-row"><input type="checkbox" id="mk-trav" ${MK.travel ? 'checked' : ''}> Can fast travel to it</label>
    <h4>Yours in this world</h4><div class="wt-list" id="mk-rows"></div>`;
  const keep = () => { MK.name = box.querySelector('#mk-name').value; MK.type = +box.querySelector('#mk-type').value; MK.show = box.querySelector('#mk-show').checked; MK.travel = box.querySelector('#mk-trav').checked; };
  box.querySelectorAll('input,select').forEach(el => el.onchange = keep);
  box.querySelector('#mk-name').oninput = keep;
  box.querySelector('#mk-rows').onclick = async e => {
    const d = e.target.closest('[data-del]');
    if (d){ const m = MK.list[+d.dataset.del]; if (await wtPost('/api/w/marker/remove', {cell: m.cell, ref: m.ref})) mkLoad(); return; }
    const r = e.target.closest('[data-i]');
    if (r){ const m = MK.list[+r.dataset.i]; M.cx = m.p[0]; M.cy = m.p[1]; M.z = Math.max(M.z, 0.03); M.dirty = true; }
  };
  mkRows(); if (!MK.types.length) mkLoad().then(() => { if (WT.tab === 'mark') wtDraw(); }); else mkLoad();
}
wtTab('mark', 'Markers', {
  draw: mkDraw,
  map(g){
    if (MK.world !== wtWorld()) mkLoad();
    g.font = '12px Inter, sans-serif';
    for (const m of MK.list){
      if (!m.p) continue;
      const [sx, sy] = mapScreen(m.p[0], m.p[1]);
      g.fillStyle = '#6fd06f'; g.strokeStyle = '#1a1712'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(sx, sy - 7); g.lineTo(sx + 7, sy); g.lineTo(sx, sy + 7); g.lineTo(sx - 7, sy); g.closePath(); g.fill(); g.stroke();
      g.lineWidth = 3; g.strokeText(m.name, sx + 10, sy + 4); g.fillText(m.name, sx + 10, sy + 4);
    }
  },
  mouse(kind, e){
    if (kind === 'down' && e.button === 0){ MK.down = [e.offsetX, e.offsetY]; return false; }
    if (kind === 'up' && MK.down && e.button === 0 && Math.hypot(e.offsetX - MK.down[0], e.offsetY - MK.down[1]) < 4){
      MK.down = null;
      if (!MK.name.trim()){ toast('Give it a name first.', true); return false; }
      const [x, y] = wtMouseSpot(e);
      wtPost('/api/w/marker/add', {world: wtWorld(), p: [x, y], name: MK.name.trim(), type: MK.type, flags: (MK.show ? 1 : 0) | (MK.travel ? 2 : 0)}).then(d => { if (d){ toast('Marker placed: ' + MK.name); MK.name = ''; if ($('#mk-name')) $('#mk-name').value = ''; mkLoad(); if (typeof outsideResync === 'function') outsideResync(); } });
      return false;
    }
    return false;
  },
});

// ---------- A cell's details, plain fields (outside on the map; a place inside from the Kit tab) ----------
const CD = {cell: null, xy: null};
const CD_FIELDS = [['XCMO', 'Music', 'MUSC'], ['LTMP', 'Lighting template', 'LGTM'], ['XCCM', 'Climate', 'CLMT'], ['XCWT', 'Water', 'WATR'], ['XOWN', 'Owner', 'FACT,NPC_'], ['XEZN', 'Encounter zone', 'ECZN'], ['XCAS', 'Echo (acoustic space)', 'ASPC'], ['XCIM', 'Image space', 'IMGS']];
async function cdForm(box, ckey){
  const d = await api('/api/w/cell?cell=' + encodeURIComponent(ckey)).catch(e => { fail(e); return null; });
  if (!d || !box.isConnected) return;
  const lists = {}; for (const [, , t] of CD_FIELDS) lists[t] = await wcList(t);
  const L = d.info.XCLL;
  box.innerHTML = `${d.outside ? '' : `<label class="wt-row"><span>Name</span><input id="cd-full" value="${esc(d.info.FULL || '')}"></label>`}
    ${CD_FIELDS.map(([tag, label, t]) => (d.outside && tag === 'XCCM') ? '' : `<div class="wt-row"><span>${label}</span>${wcPicker('cd-' + tag, lists[t], d.info[tag], 'none')}</div>`).join('')}
    ${L ? `<h4>Its own light</h4><label class="wt-row"><span>Ambient</span><input type="color" id="cd-amb" value="${L.ambient}"></label><label class="wt-row"><span>Sun or lamp</span><input type="color" id="cd-sun" value="${L.sun}"></label>
    <label class="wt-row"><span>Fog</span><input type="color" id="cd-fog" value="${L.fog}"></label><label class="wt-row"><span>Fog from, to</span><input type="number" id="cd-near" value="${L.near}"><input type="number" id="cd-far" value="${L.far}"></label>` : ''}
    ${d.regions.length ? `<div class="note">In region${d.regions.length > 1 ? 's' : ''}: ${d.regions.map(r => esc(r.name)).join(', ')}.</div>` : ''}
    <div class="wt-go"><button class="btn primary" id="cd-save">Save details</button><button class="btn" id="cd-back" ${d.changed.length ? '' : 'disabled'} title="As the game has it">Back to the game's</button></div>`;
  box.querySelector('#cd-save').onclick = async () => {
    const set = {};
    for (const [tag, , t] of CD_FIELDS){
      const el = box.querySelector('#cd-' + tag); if (!el) continue;
      const k = wcKey(el, lists[t]);
      if (k === null) return toast('Nothing by the name ' + el.value, true);
      if ((k || '') !== (d.info[tag] || '')) set[tag] = k || null;
    }
    const full = box.querySelector('#cd-full');
    if (full && full.value !== (d.info.FULL || '')) set.FULL = full.value;
    if (L){
      const now = {ambient: box.querySelector('#cd-amb').value, sun: box.querySelector('#cd-sun').value, fog: box.querySelector('#cd-fog').value, near: +box.querySelector('#cd-near').value, far: +box.querySelector('#cd-far').value};
      if (JSON.stringify(now) !== JSON.stringify(L)) set.XCLL = now;
    }
    if (!Object.keys(set).length) return toast('Nothing changed.');
    if (await wtPost('/api/w/cell/set', {cell: ckey, set})){ toast('Details saved'); cdForm(box, ckey); }
  };
  box.querySelector('#cd-back').onclick = async () => { if (await wtPost('/api/w/cell/revert', {cell: ckey})){ cdForm(box, ckey); } };
}
wtTab('cell', 'Cell', {
  draw(box){
    box.innerHTML = `<div class="note">Click a cell on the map: its music, lighting, water, owner and zone.</div><div class="note"><b id="cd-at">${CD.xy ? CD.xy.join(', ') : ''}</b></div><div id="cd-form"></div>`;
    if (CD.cell) cdForm(box.querySelector('#cd-form'), CD.cell);
  },
  map(g){ if (CD.xy) wtFillCell(g, CD.xy[0], CD.xy[1], 'rgba(240,205,135,0.2)', '#f0cd87'); },
  mouse(kind, e){
    if (kind === 'down' && e.button === 0){ CD.down = [e.offsetX, e.offsetY]; return false; }
    if (kind === 'up' && CD.down && e.button === 0 && Math.hypot(e.offsetX - CD.down[0], e.offsetY - CD.down[1]) < 4){
      CD.down = null;
      const c = wxCell(e);
      api(`/api/w/cell/at?world=${encodeURIComponent(wtWorld())}&x=${c[0]}&y=${c[1]}`).then(d => {
        if (!d.cell) return toast('No cell there.', true);
        CD.cell = d.cell; CD.xy = c; M.dirty = true;
        if (WT.on && WT.tab === 'cell') wtDraw();
      });
    }
    return false;
  },
});
// inside: the same fields in the Kit tab
{ const was = navDraw; navDraw = async () => {
    await was();
    const box = $('#nav-box'); if (!box || !A.cellId || A.outside || $('#cd-in')) return;
    const h = document.createElement('div'); h.className = 'h'; h.style.marginTop = '10px'; h.textContent = 'This place';
    const f = document.createElement('div'); f.id = 'cd-in'; f.className = 'wt-in';
    box.parentNode.appendChild(h); box.parentNode.appendChild(f);
    if (!$('#wt-in-style')){ const s = document.createElement('style'); s.id = 'wt-in-style'; s.textContent = '.wt-in .wt-row{display:flex;align-items:center;gap:6px;margin:4px 0}.wt-in .wt-row>span:first-child{flex:0 0 96px;opacity:.8}.wt-in .wt-row input:not([type=checkbox]):not([type=color]){flex:1;min-width:0}.wt-in .wt-go{display:flex;gap:5px;margin:6px 0}.wt-in h4{margin:8px 0 3px;font-size:12px}'; document.head.appendChild(s); }
    cdForm(f, A.cellId);
  }; }

// ---------- Roads and encounters ----------
const RD = {mode: 'road', a: null, b: null, settle: true, seed: 1, points: [], wait: 5, base: '', zone: '', count: 3, name: '', line: null};
function rdDraw(box){
  const row = (m, label) => `<button class="btn ${RD.mode === m ? 'on' : ''}" data-m="${m}">${label}</button>`;
  box.innerHTML = `<div class="wt-go">${row('road', '🛣 Road')}${row('patrol', '🚶 Patrol')}${row('enc', '⚔ Encounter spot')}</div><div id="rd-body"></div>`;
  box.querySelectorAll('[data-m]').forEach(b => b.onclick = () => { RD.mode = b.dataset.m; RD.points = []; RD.a = RD.b = null; wtDraw(); M.dirty = true; });
  const body = box.querySelector('#rd-body');
  if (RD.mode === 'road'){
    body.innerHTML = `<div class="note">Click the start, then the end. The game's road pieces go between them, the gentlest way over the ground (dry land only, about 15 cells at a time).</div>
      <label class="wt-row"><input type="checkbox" id="rd-settle" ${RD.settle ? 'checked' : ''}> Settle the ground just under the road</label>
      <div class="note">${RD.a ? (RD.b ? 'Start and end are set.' : 'Now click the end.') : 'Click the start.'}</div>
      <div class="wt-go"><button class="btn primary" id="rd-go" ${RD.a && RD.b ? '' : 'disabled'}>Lay the road</button><button class="btn" id="rd-clr">Clear</button></div><div class="note" id="rd-said">${RD.said || ''}</div>`;
    body.querySelector('#rd-settle').onchange = e => { RD.settle = e.target.checked; };
    body.querySelector('#rd-clr').onclick = () => { RD.a = RD.b = null; RD.said = ''; wtDraw(); M.dirty = true; };
    body.querySelector('#rd-go').onclick = async () => {
      $('#rd-said').textContent = 'Finding the way…';
      RD.seed++;
      const d = await wtPost('/api/w/road/make', {world: wtWorld(), a: RD.a, b: RD.b, settle: RD.settle, seed: RD.seed});
      if (!d){ $('#rd-said').textContent = ''; return; }
      RD.said = `${d.report.pieces} pieces, ${Math.round(d.report.length / 4096 * 10) / 10} cells long.` + (d.report.cells.length ? ` Ground settled in ${d.report.cells.length} cells.` : '') + ' One Undo.';
      RD.line = d.report.line; RD.a = RD.b = null;
      wtDraw(); M.dirty = true;
      if (typeof outsideResync === 'function') outsideResync();
      if (d.report.cells.length){ mapLandChanged(); if (typeof farLandChanged === 'function') farLandChanged(); wnOffer(d.report.cell_xy); }
    };
  } else if (RD.mode === 'patrol'){
    wcList('NPC_,CREA').then(list => {
      body.innerHTML = `<div class="note">Click the points on the map in order: they join in a ring. Whoever you pick gets a copy of their record with a patrol of their own to walk.</div>
        <div class="wt-row"><span>Who</span>${wcPicker('rd-who', list, RD.base, 'a character or creature…')}</div>
        <label class="wt-row"><span>Name</span><input id="rd-name" value="${esc(RD.name)}" placeholder="DustPatrol"></label>
        <label class="wt-row"><span>Waits at each</span><input type="number" id="rd-wait" min="0" value="${RD.wait}"> s</label>
        <div class="note">${RD.points.length} points.</div>
        <div class="wt-go"><button class="btn primary" id="rd-go" ${RD.points.length >= 2 ? '' : 'disabled'}>Make the patrol</button><button class="btn" id="rd-clr">Clear</button></div><div class="note" id="rd-said">${RD.said || ''}</div>`;
      body.querySelector('#rd-clr').onclick = () => { RD.points = []; wtDraw(); M.dirty = true; };
      body.querySelector('#rd-wait').onchange = e => { RD.wait = +e.target.value; };
      body.querySelector('#rd-name').onchange = e => { RD.name = e.target.value; };
      const who = body.querySelector('#rd-who');
      who.onchange = () => { RD.base = wcKey(who, list) || ''; };
      body.querySelector('#rd-go').onclick = async () => {
        if (!RD.base) return toast('Pick who walks it.', true);
        const d = await wtPost('/api/w/patrol/make', {world: wtWorld(), points: RD.points, base: RD.base, name: RD.name, wait: RD.wait});
        if (d){ RD.said = `A patrol of ${RD.points.length} points. Its walker: ${esc(d.report.name)}.`; RD.points = []; wtDraw(); M.dirty = true; if (typeof outsideResync === 'function') outsideResync(); }
      };
    });
  } else {
    Promise.all([api('/api/w/encounter/choices'), wcList('ECZN')]).then(([list, zones]) => {
      body.innerHTML = `<div class="note">Click the map to put a group there. Those marked “varies” take their looks from a leveled list, so they differ with the player's level.</div>
        <div class="wt-row"><span>Who</span><input id="rd-who" list="rd-who-l" placeholder="a creature…"><datalist id="rd-who-l">${list.map(x => `<option value="${esc(x.name)}">${x.leveled ? 'varies' : ''}</option>`).join('')}</datalist></div>
        <label class="wt-row"><span>How many</span><input type="number" id="rd-n" min="1" max="12" value="${RD.count}"></label>
        <div class="wt-row"><span>Zone</span>${wcPicker('rd-zone', zones, RD.zone, 'the cell\'s')}</div><div class="note" id="rd-said">${RD.said || ''}</div>`;
      const who = body.querySelector('#rd-who');
      who.onchange = () => { const r = list.find(x => x.name === who.value.trim()); RD.base = r ? r.key : ''; };
      if (RD.base){ const r = list.find(x => x.key === RD.base); if (r) who.value = r.name; }
      body.querySelector('#rd-n').onchange = e => { RD.count = +e.target.value; };
      const zn = body.querySelector('#rd-zone');
      zn.onchange = () => { RD.zone = wcKey(zn, zones) || ''; };
    });
  }
}
wtTab('road', 'Roads & spots', {
  draw: rdDraw,
  map(g){
    const dot = (p, col) => { const [sx, sy] = mapScreen(p[0], p[1]); g.fillStyle = col; g.strokeStyle = '#1a1712'; g.lineWidth = 2; g.beginPath(); g.arc(sx, sy, 6, 0, 7); g.fill(); g.stroke(); };
    if (RD.line && RD.line.length > 1){ g.strokeStyle = '#f0cd87'; g.lineWidth = 2; g.beginPath(); RD.line.forEach((p, i) => { const [sx, sy] = mapScreen(p[0], p[1]); i ? g.lineTo(sx, sy) : g.moveTo(sx, sy); }); g.stroke(); }
    if (RD.a) dot(RD.a, '#6fd06f');
    if (RD.b) dot(RD.b, '#e0705b');
    if (RD.points.length){
      g.strokeStyle = '#7fb8f0'; g.lineWidth = 2; g.beginPath();
      RD.points.forEach((p, i) => { const [sx, sy] = mapScreen(p[0], p[1]); i ? g.lineTo(sx, sy) : g.moveTo(sx, sy); });
      if (RD.points.length > 2){ const [sx, sy] = mapScreen(RD.points[0][0], RD.points[0][1]); g.lineTo(sx, sy); }
      g.stroke();
      for (const p of RD.points) dot(p, '#7fb8f0');
    }
  },
  mouse(kind, e){
    if (kind === 'down' && e.button === 0){ RD.down = [e.offsetX, e.offsetY]; return false; }
    if (kind !== 'up' || !RD.down || e.button !== 0 || Math.hypot(e.offsetX - RD.down[0], e.offsetY - RD.down[1]) >= 4) return false;
    RD.down = null;
    const spot = wtMouseSpot(e);
    if (RD.mode === 'road'){ if (!RD.a) RD.a = spot; else RD.b = spot; RD.said = ''; wtDraw(); M.dirty = true; }
    else if (RD.mode === 'patrol'){ RD.points.push(spot); RD.said = ''; wtDraw(); M.dirty = true; }
    else {
      if (!RD.base){ toast('Pick who stands there first.', true); return false; }
      wtPost('/api/w/encounter/make', {world: wtWorld(), p: spot, base: RD.base, count: RD.count, zone: RD.zone}).then(d => { if (d){ RD.said = `${d.made} placed.`; if ($('#rd-said')) $('#rd-said').textContent = RD.said; if (typeof outsideResync === 'function') outsideResync(); } });
    }
    return false;
  },
});
