// ---------- Land from real maps: a height file on the flat map, its scale and rectangle, then a new worldspace ----------
// The file's shaded picture lies on the flat map at the scale asked, in game units with its middle at the origin. Drag on it to choose a rectangle, right-drag to
// pan, the wheel zooms. The numbers come from the server (mapscale.py) before anything is made. The world is made as a job (api_maps.py), and Undo can take it away again.
// A tab in the World tools (Real map) lays OpenStreetMap over a world made this way.
const ML = {on: false, file: null, info: null, opts: {}, rep: null, img: null, imgKey: '', edges: null, rect: null, drag: null, timer: null, poll: null, busy: false};

(function mlStyle(){
  const s = document.createElement('style');
  s.textContent = `#ml{position:absolute;top:54px;right:10px;width:350px;max-height:calc(100% - 64px);overflow-y:auto;background:var(--panel);border:1px solid var(--line2);border-radius:10px;padding:8px 12px;z-index:6;font-size:13px}
  #ml h4{margin:10px 0 4px;font-size:12px;font-weight:600;opacity:.85}#ml .ml-row{display:flex;align-items:center;gap:6px;margin:4px 0}#ml .ml-row>span:first-child{flex:0 0 112px;opacity:.8}#ml .ml-row input,#ml .ml-row select{flex:1;min-width:0}
  #ml .ml-go{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0}#ml .ml-nums{background:var(--bg3);border-radius:7px;padding:6px 9px;margin:6px 0;line-height:1.5}#ml .ml-warn{color:#e8b860;margin:4px 0}#ml .ml-stop{color:#e0705b;margin:4px 0;font-weight:600}
  #ml .ml-bar{height:6px;background:var(--bg3);border-radius:3px;overflow:hidden;margin:4px 0}#ml .ml-bar>div{height:100%;background:var(--accent,#d2a85a);width:0}#ml-head{display:flex;align-items:center;justify-content:space-between}#ml-head button{background:none;border:none;color:inherit;cursor:pointer;font-size:14px}`;
  document.head.appendChild(s);
})();

function mlOpen(){
  if (!A.state.project) return toast('Start a mod first.', true);
  page('world');
  if (typeof WT !== 'undefined' && WT.on) wtToggle(false);
  if (typeof LS !== 'undefined' && LS.on) lsToggle();
  mapShow(true);
  ML.on = true; M.dirty = true;
  let box = $('#ml');
  if (!box){ box = document.createElement('div'); box.id = 'ml'; $('#view').appendChild(box); }
  box.style.display = 'block';
  mlPanel();
  if (ML.info) mlFit();
}
function mlClose(){
  ML.on = false; const box = $('#ml'); if (box) box.style.display = 'none';
  M.dirty = true;
  if (!A.outside) mapShow(false);
}

async function mlFiles(){ const d = await api('/api/maps/files').catch(() => ({files: []})); return d.files; }

async function mlPanel(){
  const box = $('#ml'); if (!box) return;
  const kept = await mlFiles();
  const R = ML.rep, I = ML.info, o = ML.opts;
  if (!OUT.worlds.length) OUT.worlds = await api('/api/worlds');
  const comp = (I && I.compressions) || [];
  box.innerHTML = `<div id="ml-head"><b>New land from a real map</b><button id="ml-x" title="Close">✕</button></div>
    <div class="note" style="padding:3px 0">Bring your own height file: GeoTIFF, SRTM .hgt or a 16-bit PNG. <a href="#" id="ml-help">Where to get one</a>.</div>
    <div class="ml-row"><span>File</span><input type="file" id="ml-pick" accept=".tif,.tiff,.hgt,.png,.zip,.gz"></div>
    ${kept.length ? `<div class="ml-row"><span>Or one you've used</span><select id="ml-kept"><option value=""></option>${kept.map(f => `<option value="${esc(f.name)}" ${f.name === ML.file ? 'selected' : ''}>${esc(f.name)} (${mlSize(f.size)})</option>`).join('')}</select></div>` : ''}
    <div id="ml-work"></div>
    <div id="ml-rest">${I ? `
      <div class="note" style="padding:3px 0">${esc(I.kind)}: ${I.w.toLocaleString()} × ${I.h.toLocaleString()} points${I.mpp ? `, ${I.mpp[0].toFixed(I.mpp[0] < 10 ? 2 : 0)} m each` : ''}${I.plain || I.folab ? '' : `, ${Math.round(I.low).toLocaleString()} to ${Math.round(I.high).toLocaleString()} m`}${I.where ? `, at ${esc(I.where)}` : ''}.</div>
      ${I.notes.map(n => `<div class="ml-warn">${esc(n)}</div>`).join('')}
      <h4>Scale</h4>
      ${!I.placed && !I.folab ? `<div class="ml-row"><span>A pixel is (m)</span><input id="ml-mpp" type="number" min="0.1" step="any" value="${o.mpp ?? 30}"></div>` : ''}
      ${I.plain ? `<div class="ml-row"><span>Black is (m)</span><input id="ml-low" type="number" step="any" value="${o.low_m ?? 0}"></div><div class="ml-row"><span>White is (m)</span><input id="ml-high" type="number" step="any" value="${o.high_m ?? 1000}"></div>` : ''}
      <div class="ml-row"><span>Size</span><select id="ml-comp">${comp.map(c => `<option value="${c}" ${c === (o.compress ?? (R && R.compress)) ? 'selected' : ''}>${c === 1 ? 'Real size' : '1 : ' + c} (a cell is ${mlDist(58.51 * c)})</option>`).join('')}</select></div>
      <div class="ml-row"><span>Height ×</span><input id="ml-exag" type="number" min="0.1" max="20" step="0.25" value="${o.exag ?? (R ? R.exag : 1)}" title="1 keeps the real slopes at this size; 2 doubles them"></div>
      <div class="ml-row"><span>Base level (m)</span><input id="ml-base" type="number" step="any" value="${o.base ?? (R ? R.base : 0)}" title="This height comes out at z 0, and the world's water stands there"></div>
      <h4>Which part</h4>
      <div class="note" style="padding:0">Drag on the map to choose a rectangle, drag inside it to move it. Right-drag pans, the wheel zooms.</div>
      <div class="ml-go"><button class="btn" id="ml-whole">The whole file</button><button class="btn" id="ml-seen">Fit to view</button></div>
      <div class="ml-nums" id="ml-nums"></div>
      <h4>Ground types (if you have a land-cover file)</h4>
      <div class="ml-row"><span>File</span><input type="file" id="ml-cpick" accept=".tif,.tiff,.png,.zip,.gz"></div>
      ${kept.length > 1 ? `<div class="ml-row"><span>Or one you've used</span><select id="ml-ckept"><option value=""></option>${kept.filter(f => f.name !== ML.file && !/\.osm/i.test(f.name)).map(f => `<option value="${esc(f.name)}" ${ML.cover && f.name === ML.cover.file ? 'selected' : ''}>${esc(f.name)}</option>`).join('')}</select></div>` : ''}
      <div id="ml-ctable">${mlCoverTable()}</div>
      <h4>The new worldspace</h4>
      <div class="ml-row"><span>Name</span><input id="ml-name" value="${esc(ML.name ?? I.name.replace(/\.[^.]*$/, ''))}"></div>
      <div class="ml-row"><span>Editor ID</span><input id="ml-edid" value="${esc(ML.edid ?? mlEdid(ML.name ?? I.name.replace(/\.[^.]*$/, '')))}"></div>
      <div class="ml-row"><span>Weather, paint like</span><select id="ml-tpl">${OUT.worlds.map(w => `<option value="${esc(w.id)}" ${(ML.tpl ? w.id === ML.tpl : w.edid === 'WastelandNV') ? 'selected' : ''}>${esc(w.name || w.edid)}</option>`).join('')}</select></div>
      <div class="ml-go"><button class="btn primary" id="ml-make">Make it</button></div>
      <div class="note" style="padding:0">FOLab saves your mod and opens it again with the new land in it. Undo takes the world away again until you change something in it; after that, World tools &gt; Real map can still go back.</div>
    ` : ''}</div>`;
  box.querySelector('#ml-x').onclick = mlClose;
  box.querySelector('#ml-help').onclick = e => { e.preventDefault(); helpDoc('real-maps'); };
  box.querySelector('#ml-pick').onchange = e => { if (e.target.files[0]) mlUpload(e.target.files[0]); };
  const k = box.querySelector('#ml-kept'); if (k) k.onchange = () => { if (k.value) mlOpenFile(k.value); };
  if (!I) return;
  box.querySelector('#ml-cpick').onchange = e => { if (e.target.files[0]) mlCoverUpload(e.target.files[0]); };
  const ck = box.querySelector('#ml-ckept'); if (ck) ck.onchange = () => { if (ck.value) mlCoverOpen(ck.value); else { ML.cover = null; mlPanel(); } };
  mlCoverEvents(box);
  for (const [id, key] of [['#ml-mpp', 'mpp'], ['#ml-low', 'low_m'], ['#ml-high', 'high_m'], ['#ml-comp', 'compress'], ['#ml-exag', 'exag'], ['#ml-base', 'base']]){
    const el = box.querySelector(id); if (!el) continue;
    el.onchange = () => {
      o[key] = el.value === '' ? null : +el.value;
      if (key === 'compress'){ delete o.exag; }                    // (the height's default follows the size)
      mlChanged(key === 'compress');
    };
  }
  box.querySelector('#ml-whole').onclick = () => { ML.rect = null; delete o.rect; mlChanged(); };
  box.querySelector('#ml-seen').onclick = mlFit;
  const nm = box.querySelector('#ml-name'), ed = box.querySelector('#ml-edid');
  nm.oninput = () => { ML.name = nm.value; ed.value = ML.edid = mlEdid(nm.value); };
  ed.oninput = () => { ML.edid = ed.value; };
  box.querySelector('#ml-tpl').onchange = e => { ML.tpl = e.target.value; };
  box.querySelector('#ml-make').onclick = mlMake;
  mlNumbers();
}
const mlEdid = s => (s.replace(/[^A-Za-z0-9]/g, '').replace(/^[0-9]+/, '') || 'MapLand').slice(0, 40) + 'World';
const mlSize = n => n > 1e9 ? (n / 1e9).toFixed(1) + ' GB' : n > 1e6 ? (n / 1e6).toFixed(0) + ' MB' : Math.ceil(n / 1e3) + ' KB';
const mlDist = m => m >= 1000 ? (m / 1000).toFixed(m >= 10000 ? 0 : 1) + ' km' : Math.round(m) + ' m';
const mlTime = s => s >= 90 ? Math.round(s / 60) + ' minutes' : Math.round(s) + ' seconds';

function mlNumbers(){
  const box = $('#ml-nums'), R = ML.rep; if (!box || !R) return;
  box.innerHTML = `<b>${R.cells_w} × ${R.cells_h} cells</b> (${R.cells.toLocaleString()}), about <b>${R.plugin_mb} MB</b> and ${mlTime(R.seconds)} to make.<br>
    Real ground ${R.km_w} × ${R.km_h} km; walks like ${R.game_km_w} × ${R.game_km_h} km. 1 km of it is ${R.cells_per_km} cells.<br>
    Heights ${R.z_low.toLocaleString()} to ${R.z_high.toLocaleString()} units${R.water ? '; water stands at 0' : '; all above the water'}.
    ${R.warnings.map(w => `<div class="ml-warn">${esc(w)}</div>`).join('')}${R.stop ? `<div class="ml-stop">${esc(R.stop)}</div>` : ''}`;
  const b = $('#ml-make'); if (b) b.disabled = !!R.stop || ML.busy;
  const c = $('#ml-exag'); if (c && ML.opts.exag == null) c.value = R.exag;
  const d = $('#ml-base'); if (d && ML.opts.base == null) d.value = R.base;
}

// ---------- files ----------
function mlWork(text, done, total){
  const box = $('#ml-work'); if (!box) return;
  box.innerHTML = text ? `<div class="note" style="padding:3px 0">${esc(text)}${total ? ` (${done.toLocaleString()} of ${total.toLocaleString()})` : '…'}</div>${total ? `<div class="ml-bar"><div style="width:${(100 * done / total).toFixed(1)}%"></div></div>` : ''}` : '';
}
async function mlUpload(file){
  mlWork(`Copying ${file.name} to FOLab (${mlSize(file.size)})`);
  try {
    const r = await fetch('/api/maps/upload?name=' + encodeURIComponent(file.name), {method: 'POST', body: file});
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || r.status);
    await mlOpenFile(d.file);
  } catch (e){ mlWork(''); fail(e); }
}
async function mlOpenFile(name){
  ML.file = null; ML.info = null; ML.rep = null; ML.img = null; ML.imgKey = ''; ML.rect = null; ML.opts = {}; ML.name = ML.edid = undefined; M.dirty = true;
  await mlJob(post('/api/maps/open', {file: name}), r => {
    ML.file = name; ML.info = r; ML.rep = r.plan; ML.edges = null;
    mlPanel(); mlChanged(); mlFit();
  });
}
function mlJob(start, done){
  return start.then(() => new Promise(resolve => {
    clearInterval(ML.poll);
    ML.busy = true;
    ML.poll = setInterval(async () => {
      const j = await api('/api/maps/job').catch(() => null);
      if (!j) return;
      mlWork(j.said, j.done, j.total);
      if (j.running) return;
      clearInterval(ML.poll); ML.busy = false; mlWork('');
      if (j.ok) await done(j.result); else toast(j.error, true);
      resolve();
    }, 400);
  })).catch(e => { ML.busy = false; mlWork(''); fail(e); });
}

// ---------- ground types: a land-cover file and which class gets what ----------
function mlCoverTable(){
  const C = ML.cover; if (!C) return '';
  return `<div class="note" style="padding:3px 0">${C.scheme ? 'Looks like <b>' + esc(C.scheme) + '</b>.' : 'FOLab doesn\'t know these numbers: say what each one gets.'} ${C.placed ? '' : 'It doesn\'t say where it is on Earth, so it will be stretched over the whole height file.'} Blank texture leaves it to the slope. Things are how many a cell.</div>
    <div style="max-height:210px;overflow-y:auto">${C.rows.map((r, i) => `<div class="ml-row" style="flex-wrap:wrap;border-top:1px solid var(--line2);padding-top:3px"><span style="flex:1 0 100%;opacity:1">${esc(r.label)} <small style="opacity:.65">${r.value}, ${(r.share * 100).toFixed(r.share < 0.1 ? 1 : 0)}%</small></span>
      <select data-c="${i}" data-f="tex" style="flex:2 1 120px;min-width:0"><option value="">(by slope)</option>${C.textures.map(t => `<option value="${esc(t.key)}" ${t.key === r.tex ? 'selected' : ''}>${esc(t.edid)}</option>`).join('')}</select>
      <select data-c="${i}" data-f="scatter" style="flex:1 1 70px;min-width:0">${C.sets.map(([k, l]) => `<option value="${k}" ${k === r.scatter ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select>
      <input data-c="${i}" data-f="density" type="number" min="0" max="100" step="1" value="${r.density}" style="flex:0 0 46px;min-width:0" title="How many a cell"></div>`).join('')}</div>
    <div class="ml-go"><button class="btn" id="ml-cclear">Leave out ground types</button></div>`;
}
function mlCoverEvents(box){
  const t = box.querySelector('#ml-ctable'); if (!t) return;
  t.onchange = e => {
    const el = e.target.closest('[data-c]'); if (!el || !ML.cover) return;
    ML.cover.rows[+el.dataset.c][el.dataset.f] = el.dataset.f === 'density' ? +el.value : el.value;
    try { localStorage.setItem('folab-cover-' + (ML.cover.scheme || 'other'), JSON.stringify(ML.cover.rows)); } catch (err) {}
  };
  t.onclick = e => { if (e.target.id === 'ml-cclear'){ ML.cover = null; mlPanel(); } };
}
async function mlCoverUpload(file){
  mlWork(`Copying ${file.name} to FOLab (${mlSize(file.size)})`);
  try {
    const r = await fetch('/api/maps/upload?name=' + encodeURIComponent(file.name), {method: 'POST', body: file});
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || r.status);
    await mlCoverOpen(d.file);
  } catch (e){ mlWork(''); fail(e); }
}
async function mlCoverOpen(name){
  await mlJob(post('/api/maps/cover/open', {file: name}), r => {
    ML.cover = r;
    // (what was chosen last time for this kind of file, by class)
    try {
      const was = JSON.parse(localStorage.getItem('folab-cover-' + (r.scheme || 'other')) || '[]');
      for (const row of r.rows){ const w = was.find(x => x.value === row.value); if (w) Object.assign(row, {tex: w.tex, scatter: w.scatter, density: w.density}); }
    } catch (e) {}
    mlPanel();
  });
}

// ---------- the numbers and the picture ----------
function mlBody(){
  const o = Object.assign({}, ML.opts);
  if (ML.rect) o.rect = ML.rect;
  return {file: ML.file, opts: o};
}
function mlChanged(soon){
  clearTimeout(ML.timer);
  ML.timer = setTimeout(async () => {
    if (!ML.file) return;
    try {
      ML.rep = await post('/api/maps/plan', mlBody());
      ML.edges = ML.rep.edges;
      if (soon) mlPanel(); else mlNumbers();
      mlPicture();
      M.dirty = true;
    } catch (e){ fail(e); }
  }, 150);
}
function mlPicture(){
  const o = ML.opts, q = new URLSearchParams({file: ML.file});
  q.set('base', ML.rep.base);
  if (o.low_m != null) q.set('low_m', o.low_m);
  if (o.high_m != null) q.set('high_m', o.high_m);
  if (o.mpp != null) q.set('mpp', o.mpp);
  const key = q.toString();
  if (key === ML.imgKey) return;
  ML.imgKey = key;
  const img = new Image();
  mlWork('Drawing the picture');
  img.onload = () => { if (ML.imgKey === key){ ML.img = img; M.dirty = true; if (!ML.busy) mlWork(''); } };
  img.src = '/api/maps/picture?' + key;
}
// (a pixel centre to map units: the middle of the file is the origin)
function mlXY(col, row){
  const I = ML.info, [ux, uy] = ML.rep.units_per_px;
  return [(col - (I.w - 1) / 2) * ux, -(row - (I.h - 1) / 2) * uy];
}
function mlPixel(x, y){
  const I = ML.info, [ux, uy] = ML.rep.units_per_px;
  return [x / ux + (I.w - 1) / 2, -y / uy + (I.h - 1) / 2];
}
function mlFit(){
  if (!ML.rep || !ML.info) return;
  const I = ML.info, [ux, uy] = ML.rep.units_per_px;
  const room = Math.max(M.w - 370, M.w * 0.4);                    // (the panel covers the right)
  M.z = Math.max(0.0002, Math.min(2, 0.9 * Math.min(room / (I.w * ux), M.h / (I.h * uy))));
  M.cx = (M.w - room) / 2 / M.z; M.cy = 0;
  M.dirty = true;
}
function mlDraw(g){
  const css = getComputedStyle(document.documentElement);
  g.fillStyle = css.getPropertyValue('--bg').trim() || '#0e0c0a'; g.fillRect(0, 0, M.w, M.h);
  if (!ML.rep || !ML.info){
    g.fillStyle = 'rgba(240,205,135,0.5)'; g.font = '15px Inter, sans-serif'; g.textAlign = 'center';
    g.fillText('Pick a height file: its picture will lie here.', (M.w - 360) / 2, M.h / 2); g.textAlign = 'left';
    return;
  }
  const R = ML.rep;
  if (ML.img && ML.edges){
    const [c0, r0, c1, r1] = ML.edges;
    const [ax, ay] = mapScreen(...mlXY(c0, r0)), [bx, by] = mapScreen(...mlXY(c1, r1));
    g.imageSmoothingEnabled = true;
    g.drawImage(ML.img, ax, ay, bx - ax, by - ay);
  }
  // the world that would be made: whole cells, the rest dimmed
  const [c0, r0, c1, r1] = R.rect;
  const [ax, ay] = mapScreen(...mlXY(c0, r0)), [bx, by] = mapScreen(...mlXY(c1, r1));
  g.fillStyle = 'rgba(0,0,0,0.42)'; g.beginPath(); g.rect(0, 0, M.w, M.h); g.rect(ax, ay, bx - ax, by - ay); g.fill('evenodd');
  const cw = (bx - ax) / R.cells_w, ch = (by - ay) / R.cells_h;
  if (cw > 7){
    g.strokeStyle = 'rgba(240,205,135,0.2)'; g.lineWidth = 1; g.beginPath();
    for (let i = 1; i < R.cells_w; i++){ g.moveTo(ax + i * cw, ay); g.lineTo(ax + i * cw, by); }
    for (let j = 1; j < R.cells_h; j++){ g.moveTo(ax, ay + j * ch); g.lineTo(bx, ay + j * ch); }
    g.stroke();
  }
  g.strokeStyle = R.stop ? '#e0705b' : '#f0cd87'; g.lineWidth = 2; g.strokeRect(ax, ay, bx - ax, by - ay);
  g.fillStyle = '#f0cd87'; g.font = '12px Inter, sans-serif'; g.fillText(`${R.cells_w} × ${R.cells_h} cells`, ax + 5, ay - 6 > 12 ? ay - 6 : ay + 15);
  if (ML.drag && ML.drag.pts){
    g.strokeStyle = '#fff'; g.setLineDash([4, 3]); g.lineWidth = 1;
    const [a, b] = ML.drag.pts; g.strokeRect(Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])); g.setLineDash([]);
  }
  // a scale bar in real distance
  const unit = 70 / R.compress, nice = [10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000];
  const m = nice.find(v => v * unit * M.z >= 70) || 100000, px = m * unit * M.z;
  g.strokeStyle = '#f0cd87'; g.lineWidth = 2; g.beginPath(); g.moveTo(14, M.h - 16); g.lineTo(14 + px, M.h - 16); g.stroke();
  g.fillStyle = '#f0cd87'; g.fillText(mlDist(m) + ' real', 14, M.h - 22);
}
function mlMouse(kind, e){
  if (!ML.rep) return false;
  if (kind === 'dbl') return true;
  if (kind === 'down'){
    if (e.button !== 0) return false;
    const [c0, r0, c1, r1] = ML.rep.rect;
    const [x, y] = mapWorld(e.offsetX, e.offsetY), [col, row] = mlPixel(x, y);
    try { M.c.setPointerCapture(e.pointerId); } catch (err) {}
    if (col >= c0 && col <= c1 && row >= r0 && row <= r1 && !(c0 === 0 && r0 === 0 && !ML.rect)){
      ML.drag = {move: true, col, row, from: [c0, r0, c1, r1]};
    } else {
      ML.drag = {pts: [[e.offsetX, e.offsetY], [e.offsetX, e.offsetY]]};
    }
    return true;
  }
  if (!ML.drag) return false;
  if (kind === 'move'){
    const [x, y] = mapWorld(e.offsetX, e.offsetY), [col, row] = mlPixel(x, y);
    if (ML.drag.move){
      const f = ML.drag.from, I = ML.info;
      const dc = Math.max(-f[0], Math.min(I.w - 1 - f[2], col - ML.drag.col)), dr = Math.max(-f[1], Math.min(I.h - 1 - f[3], row - ML.drag.row));
      ML.rect = [f[0] + dc, f[1] + dr, f[2] + dc, f[3] + dr];
      mlChanged();
    } else ML.drag.pts[1] = [e.offsetX, e.offsetY];
    M.dirty = true;
    return true;
  }
  if (kind === 'up'){
    const d = ML.drag; ML.drag = null;
    if (d.pts){
      const [a, b] = d.pts;
      if (Math.abs(a[0] - b[0]) > 6 && Math.abs(a[1] - b[1]) > 6){
        const [ca, ra] = mlPixel(...mapWorld(a[0], a[1])), [cb, rb] = mlPixel(...mapWorld(b[0], b[1]));
        const I = ML.info, cl = (v, n) => Math.max(0, Math.min(n - 1, v));
        ML.rect = [cl(Math.min(ca, cb), I.w), cl(Math.min(ra, rb), I.h), cl(Math.max(ca, cb), I.w), cl(Math.max(ra, rb), I.h)];
        mlChanged();
      }
    }
    M.dirty = true;
    return true;
  }
  return false;
}
// over the map's own drawing and mouse, through the land shaper's hooks
{ const was = lsDraw; lsDraw = g => { if (ML.on) return mlDraw(g); was(g); }; }
{ const was = lsMouse; lsMouse = (kind, e) => { if (ML.on) return mlMouse(kind, e); return was(kind, e); }; }
{ const was = cs3dThings; cs3dThings = () => !ML.on && was(); }
{ const was = mapMarkers; mapMarkers = g => { if (!ML.on) was(g); }; }

// ---------- making it ----------
async function mlMake(){
  const R = ML.rep; if (!R || R.stop || ML.busy) return;
  const body = Object.assign(mlBody(), {name: $('#ml-name').value.trim(), edid: $('#ml-edid').value.trim(), template: $('#ml-tpl').value});
  if (ML.cover) body.cover = {file: ML.cover.file, rows: ML.cover.rows};
  if (!body.edid) return toast('Give it an editor ID: letters and digits, no spaces.', true);
  $('#ml-make').disabled = true;
  await mlJob(post('/api/maps/make', body), async r => {
    setState(r.state);
    if (typeof BW !== 'undefined') BW.types = [];
    await loadPlaces();
    OUT.worlds = await api('/api/worlds');
    const info = await api('/api/world?id=' + encodeURIComponent(r.world));
    ML.on = false; const box = $('#ml'); if (box) box.style.display = 'none';
    OUT.info = info; tab('left', 'outside'); drawOutside();
    goOutside(info, {p: [...info.middle, 0]});
    const b = info.bounds;
    M.cx = (b[0] + b[2] + 1) * 2048; M.cy = (b[1] + b[3] + 1) * 2048;
    M.z = Math.max(0.0006, Math.min(2, 0.9 * Math.min(M.w / ((b[2] - b[0] + 1) * 4096), M.h / ((b[3] - b[1] + 1) * 4096))));
    M.dirty = true;
    if (typeof mlAfter === 'function') mlAfter(r);
    const s = r.report;
    toast(`${info.name || info.edid}: ${s.cells.toLocaleString()} cells, ${mlSize(s.size)}, heights ${s.z_low.toLocaleString()} to ${s.z_high.toLocaleString()}${s.things ? `, ${s.things.toLocaleString()} things scattered` : ''}${s.too_steep ? `. ${s.too_steep.toLocaleString()} land points came down, too steep for the game to store` : ''}${s.holes_sea ? `. ${s.holes_sea.toLocaleString()} points with no data became sea bed` : ''}${s.note ? '. ' + s.note : ''}.`);
  });
  const b = $('#ml-make'); if (b) b.disabled = false;
}
// Undo that takes a world away reopens the mod: the page starts over with it
{ const was = post; post = async (path, body) => {
    if (path === '/api/maps/restore' || (path === '/api/undo' && A.state && A.state.project && A.state.project.undo === 'New world from a map')) toast('Taking the world away and opening your mod again: a moment…');
    const d = await was(path, body);
    if (d && d.world_gone && (path === '/api/undo' || path === '/api/maps/restore')){ setTimeout(() => location.reload(), 300); }
    return d;
  }; }

// the way in: a button on the New worldspace window, as the window stands
{ const was = newWorldDialog;
  newWorldDialog = async function(){
    await was();
    const foot = $('#nw-go') && $('#nw-go').parentElement;
    if (!foot) return;
    const b = document.createElement('button');
    b.className = 'btn'; b.textContent = '🗺 From a real map…'; b.title = 'Land from a height file: GeoTIFF, SRTM or a 16-bit PNG';
    b.onclick = () => { const c = $('#nw-cancel'); if (c) c.click(); mlOpen(); };
    foot.appendChild(b);
  }; }

// ---------- World tools > Real map: OpenStreetMap over a world made from a height file, and the way back ----------
const MO = {world: null, side: null, file: null, read: null, layer: null, showLayer: true, insides: 0.35, want: {roads: ['major'], rivers: true, streams: false, lakes: true, buildings: true}, said: '', poll: null};
const MO_ROADS = [['major', 'Motorways to tertiary roads'], ['minor', 'Residential and service roads'], ['track', 'Tracks']];
async function moLoad(){
  if (MO.world === OUT.world) return;
  MO.world = OUT.world; MO.read = null; MO.layer = null; MO.said = '';
  const all = await api('/api/maps/worlds').catch(() => ({}));
  const edid = OUT.info && OUT.info.edid;
  MO.side = all[edid] || null;
  MO.layer = edid ? await api('/api/maps/layers?edid=' + encodeURIComponent(edid)).catch(() => null) : null;
  M.dirty = true;
}
async function moDraw(box){
  await moLoad();
  if (!MO.side){
    box.innerHTML = `<div class="note">This world wasn't made from a height file. Make one under Outside: ＋ New worldspace, 🗺 From a real map.</div>`;
    return;
  }
  const S = MO.side, kept = (await mlFiles()).filter(f => /\.osm(\.bz2|\.gz)?$/i.test(f.name)), R = MO.read;
  box.innerHTML = `<div class="note">From <b>${esc(S.file)}</b>, 1 : ${S.compress}, height × ${S.exag}, base level ${S.base} m.</div>
    <h4>OpenStreetMap</h4>
    <div class="note">Your own .osm file (or .osm.bz2, .gz) of the same place. <a href="#" id="mo-help">Where to get one</a>.</div>
    <div class="wt-row"><span>File</span><input type="file" id="mo-pick" accept=".osm,.bz2,.gz,.xml"></div>
    ${kept.length ? `<div class="wt-row"><span>Or one you've used</span><select id="mo-kept"><option value=""></option>${kept.map(f => `<option value="${esc(f.name)}" ${f.name === MO.file ? 'selected' : ''}>${esc(f.name)}</option>`).join('')}</select></div>` : ''}
    <div id="mo-work" class="note"></div>
    ${R ? moChoices(R) : ''}
    ${MO.layer && MO.layer.buildings ? `<h4>Marker layer</h4><label><input type="checkbox" id="mo-layer" ${MO.showLayer ? 'checked' : ''}> Show ${MO.layer.buildings.length} building outlines, ${MO.layer.places.length} places, ${MO.layer.bridges.length} bridges on the map</label>` : ''}
    ${MO.layer && MO.layer.buildings && MO.layer.buildings.some(b => b.pad) ? `<h4>Buildings</h4>
      <div class="note">The game's own buildings on the ${MO.layer.buildings.filter(b => b.pad).length.toLocaleString()} levelled plots: each the nearest fit for its plot and its kind (house, shop, block, works, hall), fronts to the nearest road.</div>
      <div class="wt-row"><span>Ways in</span><select id="mo-insides" title="A building that opens gets a copy of a place the game has behind that same building: furnished, with a navmesh, without its people or story">
        ${[[0, 'None: every door locked'], [0.2, 'A few buildings open'], [0.35, 'About a third open'], [0.7, 'Most open'], [1, 'Every one that can']].map(([v, l]) => `<option value="${v}" ${v === MO.insides ? 'selected' : ''}>${l}</option>`).join('')}
      </select></div>
      <div class="note">Plots that stand out (named, public buildings) always open when the game has a place behind that building. The rest stay locked.</div>
      <div class="wt-go"><button class="btn primary" id="mo-build">🏚 Put up buildings</button></div>
      <div class="note">One Undo. Plots that already have theirs are left as they are.</div>` : ''}
    <h4>Going back</h4>
    <div class="wt-go"><button class="btn" id="mo-back" title="The mod as it was before this world, everything since gone with it">Go back to before this world…</button></div>`;
  box.querySelector('#mo-help').onclick = e => { e.preventDefault(); helpDoc('real-maps'); };
  box.querySelector('#mo-pick').onchange = async e => {
    const f = e.target.files[0]; if (!f) return;
    moWork(`Copying ${f.name} to FOLab`);
    try {
      const r = await fetch('/api/maps/upload?name=' + encodeURIComponent(f.name), {method: 'POST', body: f});
      const d = await r.json();
      if (!r.ok || d.error) throw new Error(d.error || r.status);
      moRead(d.file);
    } catch (err){ moWork(''); fail(err); }
  };
  const k = box.querySelector('#mo-kept'); if (k) k.onchange = () => { if (k.value) moRead(k.value); };
  const lay = box.querySelector('#mo-layer'); if (lay) lay.onchange = () => { MO.showLayer = lay.checked; M.dirty = true; };
  const bld = box.querySelector('#mo-build'); if (bld) bld.onclick = moBuild;
  const ins = box.querySelector('#mo-insides'); if (ins) ins.onchange = () => { MO.insides = +ins.value; };
  box.querySelector('#mo-back').onclick = async () => {
    if (!confirm('Take this world out of your mod, and everything you have done since it was made? This can\'t be undone.')) return;
    try { await post('/api/maps/restore'); } catch (err){ fail(err); }
  };
  if (R) moChoiceEvents(box);
  moNote();
}
function moChoices(R){
  const W_ = MO.want, roads = R.roads || {}, riv = R.rivers || {};
  const tick = (id, on, label, disabled) => `<label style="display:block;margin:2px 0;${disabled ? 'opacity:.5' : ''}"><input type="checkbox" id="${id}" ${on && !disabled ? 'checked' : ''} ${disabled ? 'disabled' : ''}> ${label}</label>`;
  return `<h4>On this world</h4>
    ${MO_ROADS.map(([c, l]) => tick('mo-r-' + c, W_.roads.includes(c), `${l}: ${roads[c] ? roads[c].n.toLocaleString() + ' (about ' + roads[c].pieces.toLocaleString() + ' pieces)' : 'none'}`, !roads[c])).join('')}
    ${tick('mo-rivers', W_.rivers, `Rivers and canals: ${riv.river || 0}`, !riv.river)}
    ${tick('mo-streams', W_.streams, `Streams: ${riv.stream || 0}`, !riv.stream)}
    ${tick('mo-lakes', W_.lakes, `Lakes: ${R.lakes}`, !R.lakes)}
    ${tick('mo-pads', W_.buildings, `Flat pads for ${R.buildings.toLocaleString()} buildings`, !R.buildings)}
    <div class="note">${R.bridges ? `${R.bridges} bridge${R.bridges === 1 ? '' : 's'} left out and listed in the layer. ` : ''}${R.places ? `${R.places} place name${R.places === 1 ? '' : 's'} in the layer. ` : ''}${R.note ? esc(R.note) : ''}</div>
    <div class="wt-go"><button class="btn primary" id="mo-lay">Lay it</button></div>
    <div class="note">One Undo. Buildings go up afterwards, on the pads (Put up buildings).</div>`;
}
function moChoiceEvents(box){
  for (const [c] of MO_ROADS){
    const el = box.querySelector('#mo-r-' + c); if (!el) continue;
    el.onchange = () => { MO.want.roads = MO.want.roads.filter(x => x !== c); if (el.checked) MO.want.roads.push(c); M.dirty = true; };
  }
  for (const [id, key] of [['#mo-rivers', 'rivers'], ['#mo-streams', 'streams'], ['#mo-lakes', 'lakes'], ['#mo-pads', 'buildings']]){
    const el = box.querySelector(id); if (el) el.onchange = () => { MO.want[key] = el.checked; M.dirty = true; };
  }
  box.querySelector('#mo-lay').onclick = moLay;
}
function moNote(){ const b = $('#mo-work'); if (b) b.innerHTML = MO.said; }
function moWork(text){ MO.said = esc(text || ''); moNote(); }
function moJob(start, done){
  clearInterval(MO.poll);
  start.then(() => {
    MO.poll = setInterval(async () => {
      const j = await api('/api/maps/job').catch(() => null);
      if (!j) return;
      moWork(j.said + (j.total ? ` (${j.done.toLocaleString()} of ${j.total.toLocaleString()})` : '…'));
      if (j.running) return;
      clearInterval(MO.poll); MO.said = '';
      if (j.ok) await done(j.result); else { toast(j.error, true); MO.said = '<b>Could not:</b> ' + esc(j.error); }
      if (WT.on && WT.tab === 'realmap') wtDraw();
    }, 500);
  }).catch(e => { MO.said = ''; moNote(); fail(e); });
}
function moRead(file){
  MO.file = file; MO.read = null; moWork('Reading the file');
  moJob(post('/api/maps/osm/read', {file, world: OUT.world}), r => { MO.read = r; M.dirty = true; });
}
function moLay(){
  const b = $('#mo-lay'); if (b) b.disabled = true;
  moJob(post('/api/maps/osm/lay', {file: MO.file, world: OUT.world, want: MO.want}), async r => {
    if (r.state) setState(r.state);
    const t = r.report;
    MO.said = `Laid ${t.pieces.toLocaleString()} road pieces, ${t.rivers} river${t.rivers === 1 ? '' : 's'}, ${t.lakes} lake${t.lakes === 1 ? '' : 's'}, ${t.pads.toLocaleString()} pads${t.pads_too_small ? ` (${t.pads_too_small.toLocaleString()} buildings too small to show)` : ''}.${t.roads_skipped ? ` ${t.roads_skipped} road${t.roads_skipped === 1 ? '' : 's'} left out: off the land.` : ''} The ground changed in ${t.land_cells.toLocaleString()} cells.`;
    MO.layer = await api('/api/maps/layers?edid=' + encodeURIComponent(OUT.info.edid)).catch(() => null);
    MO.read = null;
    for (const c of OUT.cells.values()) (OUT.touched = OUT.touched || new Set()).add(c);
    await outsideResync();
    mapLandChanged(); if (typeof farLandChanged === 'function') farLandChanged();
    if (t.cell_xy && t.cell_xy.length && t.cell_xy.length <= 200) wnOffer(t.cell_xy);
  });
}
function moBuild(){
  const b = $('#mo-build'); if (b) b.disabled = true;
  moJob(post('/api/maps/buildings', {world: OUT.world, insides: MO.insides}), async r => {
    if (r.state) setState(r.state);
    const t = r.report, n = (v, one, many) => `${v.toLocaleString()} ${v === 1 ? one : many}`;
    const words = {house: ['house', 'houses'], shop: ['shop', 'shops'], civic: ['hall', 'halls'], industrial: ['works', 'works'], apartments: ['block', 'blocks']};
    const fam = Object.entries(t.families).sort((a, b) => b[1] - a[1]).map(([k, v]) => n(v, ...(words[k] || ['other', 'others']))).join(', ');
    const left = [t.nothing_fits && `${t.nothing_fits.toLocaleString()} too small for any of the game's`, t.blocked && `${t.blocked.toLocaleString()} tries in a road's or a building's way`, t.steep && `${t.steep.toLocaleString()} on ground too uneven`, t.had_one && `${t.had_one.toLocaleString()} already built`].filter(Boolean);
    MO.said = `Put up ${n(t.buildings, 'building', 'buildings')} on ${n(t.built, 'plot', 'plots')} (${fam}), with ${n(t.doors, 'door', 'doors')}.${t.landmarks ? ` ${n(t.landmarks, 'is a landmark', 'are landmarks')}, on plots that stand out.` : ''}${t.insides ? ` ${n(t.insides, 'building opens', 'buildings open')} into a place of its own (${t.inside_things.toLocaleString()} things in all, each with its navmesh${t.navmesh_missed ? `, ${t.navmesh_missed} without: make those in the Kit tab` : ''}); the other doors are locked.${t.insides_capped ? ' That\'s as many as FOLab makes in one go: press again for more.' : ''}` : ''}${left.length ? ' Left: ' + left.join('; ') + '.' : ''}${t.cleared ? ` ${n(t.cleared, 'small thing', 'small things')} cleared off the plots.` : ''}${t.roads_seen ? '' : ' No roads laid yet, so fronts face a long side.'}`;
    await outsideResync();
    // (a navmesh made before is under the new buildings: people would walk through their walls)
    if (t.cell_xy && t.cell_xy.length) wnOffer(t.cell_xy, `Buildings went up in ${n(t.cell_xy.length, 'cell', 'cells')}. Characters outside walk through them until the navmesh there is made again.`);
  });
}
function moPath(g, line, closed){
  g.beginPath();
  line.forEach((p, i) => { const [x, y] = mapScreen(p[0], p[1]); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
  if (closed) g.closePath();
}
function moMap(g){
  if (MO.world !== OUT.world){ moLoad(); return; }
  const D = MO.read && MO.read.draw, L = MO.layer;
  const color = {major: '#f0cd87', minor: '#c9b48a', track: '#927f5e'};
  if (D){
    g.lineWidth = 1.5;
    g.strokeStyle = '#4aa6e0';
    for (const r of D.lakes){ moPath(g, r, true); g.fillStyle = 'rgba(74,166,224,0.3)'; g.fill(); g.stroke(); }
    for (const r of D.rivers){ if (r.c === 'stream' && !MO.want.streams) continue; if (r.c === 'river' && !MO.want.rivers) continue; g.lineWidth = r.c === 'river' ? 2.5 : 1; moPath(g, r.l); g.stroke(); }
    for (const r of D.roads){ const on = MO.want.roads.includes(r.c); g.globalAlpha = on ? 1 : 0.3; g.lineWidth = on ? 2 : 1; g.strokeStyle = color[r.c]; moPath(g, r.l); g.stroke(); }
    g.globalAlpha = 1; g.strokeStyle = '#e0705b'; g.lineWidth = 2; for (const r of D.bridges){ moPath(g, r); g.stroke(); }
    if (4096 * M.z > 3){ g.strokeStyle = 'rgba(240,240,240,0.7)'; g.lineWidth = 1; for (const r of D.buildings){ moPath(g, r, true); g.stroke(); } }
    g.fillStyle = '#fff'; g.font = '12px Inter, sans-serif'; for (const p of D.places){ const [x, y] = mapScreen(p.p[0], p.p[1]); g.fillText(p.n, x + 4, y); }
  }
  if (L && L.buildings && MO.showLayer && !D){
    if (4096 * M.z > 3){ g.lineWidth = 1; for (const b of L.buildings){ g.strokeStyle = b.pad ? 'rgba(240,240,240,0.75)' : 'rgba(240,205,135,0.5)'; moPath(g, b.ring, true); g.stroke(); } }
    g.strokeStyle = '#e0705b'; g.lineWidth = 2; for (const b of L.bridges){ moPath(g, b.line); g.stroke(); }
    g.fillStyle = '#fff'; g.font = '12px Inter, sans-serif'; for (const p of L.places){ const [x, y] = mapScreen(p.p[0], p.p[1]); g.fillText(p.name, x + 4, y); }
  }
}
wtTab('realmap', 'Real map', {draw: moDraw, map: moMap});
