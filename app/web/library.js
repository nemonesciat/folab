// ---------- The Library: every mesh, texture and sound the game has, and your own ----------
// Kinds on the left with the folders, a grid of pictures in the middle (search anywhere in a path), the chosen file on
// the right: turning in 3D, a picture, or playing. Your own files come in by the button or by dropping them on the
// page, are kept with your mod and go into the game with it; a mesh becomes a thing to place in one click.
const LB = {kind: 'mesh', folder: '', q: '', rows: [], folders: [], total: 0, chosen: null, info: null, token: 0, counts: null, kinds: {}, pickFn: null};
const LB_KINDS = [['mesh', 'Meshes', '🧱'], ['texture', 'Textures', '🎨'], ['sound', 'Sounds', '🔊'], ['mine', 'Your own', '⭐']];
const lbThumb = (p, w) => `/api/library/thumb?w=${w || 128}&path=${encodeURIComponent(p)}`;
const lbName = p => p.split('\\').pop();
const lbBytes = n => n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n >= 1024 ? Math.round(n / 1024) + ' KB' : n + ' bytes';

(function lbMake(){
  const css = document.createElement('style');
  css.textContent = `
  #lb-side{width:230px;border-right:1px solid var(--line)}
  #lb-mid{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--panel)}
  #lb-detail{width:360px;flex:none;overflow-y:auto;border-left:1px solid var(--line);background:var(--panel);padding:10px 14px 30px}
  #lb-bar{display:flex;gap:6px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--line);flex-wrap:wrap}
  #lb-bar input{flex:1;min-width:160px}
  #lb-crumbs{padding:6px 12px;color:var(--muted);font-size:12.5px;overflow-wrap:anywhere}#lb-crumbs a{color:var(--gold);cursor:pointer}
  #lb-grid{flex:1;overflow-y:auto;padding:0 10px 10px;display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:8px;align-content:start}
  .lb-tile{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:4px;cursor:pointer;min-width:0;display:flex;flex-direction:column;gap:2px}
  .lb-tile:hover{border-color:var(--goldline)}.lb-tile.on{border-color:var(--gold);background:var(--sel)}
  .lb-tile .pic{height:104px;display:flex;align-items:center;justify-content:center;background:var(--bg2);border-radius:5px;overflow:hidden;color:var(--faint);font-size:26px}
  .lb-tile .pic img{max-width:100%;max-height:100%}
  .lb-tile span{font-size:11.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.lb-tile small{color:var(--faint);font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .lb-tile.folder .pic{font-size:40px;color:var(--goldline)}
  #lb-more{grid-column:1/-1;text-align:center;padding:8px}
  #lb-view{height:280px;background:var(--bg2);border:1px solid var(--line);border-radius:8px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;overflow:hidden}
  #lb-view img{max-width:100%;max-height:100%}#lb-view audio{width:92%}
  #lb-detail h3{margin:6px 0 2px;font-size:14px;color:var(--gold2);font-weight:500;overflow-wrap:anywhere}
  .lb-path{color:var(--muted);font-size:12px;overflow-wrap:anywhere;margin-bottom:6px}
  .lb-kv{font-size:12.5px;color:var(--muted);margin:2px 0}.lb-kv b{color:var(--text);font-weight:500}
  .lb-acts{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
  .lb-tex{display:flex;gap:8px;align-items:center;padding:3px 0;border-top:1px solid var(--line);min-width:0;cursor:pointer}.lb-tex:hover{background:var(--hover)}
  .lb-tex img{width:40px;height:40px;object-fit:contain;background:var(--bg2);border-radius:4px;flex:none}
  .lb-tex div{min-width:0;font-size:12px;overflow-wrap:anywhere}.lb-tex small{color:var(--faint);display:block}.lb-tex .gone{color:var(--red)}
  .lb-drop-over::after{content:'Drop meshes and pictures here: they go in your mod';position:fixed;inset:12px;border:2px dashed var(--gold);border-radius:12px;background:#0009;color:var(--gold2);display:flex;align-items:center;justify-content:center;font-size:20px;z-index:40;pointer-events:none}
  #lb-rt{position:fixed;z-index:45;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center}
  .lb-rtcard{background:var(--panel);border:1px solid var(--line2);border-radius:10px;width:min(980px,96vw);height:min(660px,92vh);display:flex;flex-direction:column}
  .lb-rtbody{flex:1;display:flex;gap:14px;min-height:0;padding:12px 14px}.lb-rtl{width:400px;overflow-y:auto;flex:none}.lb-rtr{flex:1;display:flex;flex-direction:column;min-width:0}
  .lb-slot{display:flex;gap:8px;align-items:center;padding:5px;border:1px solid var(--line);border-radius:7px;margin-bottom:6px;cursor:pointer}.lb-slot.on{border-color:var(--gold);background:var(--sel)}
  .lb-slot img{width:48px;height:48px;object-fit:contain;background:var(--bg2);border-radius:4px;flex:none}.lb-slot div{min-width:0;font-size:12px;overflow-wrap:anywhere}.lb-slot small{display:block;color:var(--faint)}.lb-slot b{color:var(--gold2);font-weight:500}
  .lb-pickgrid{flex:1;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:6px;align-content:start;margin-top:6px}`;
  document.head.appendChild(css);
  const main = document.createElement('main');
  main.id = 'page-library'; main.style.display = 'none';
  main.innerHTML = `<div class="side" id="lb-side"><div class="h">Kinds</div><div id="lb-kinds"></div><div class="h">Folders</div><div class="list" id="lb-folders"></div></div>
    <div id="lb-mid"><div id="lb-bar"><input id="lb-q" placeholder="Search names and folders: chair, vault door, pistol fire…" autocomplete="off">
        <button class="btn primary" id="lb-add" title="Bring in meshes, pictures or sounds from anywhere on your computer">＋ Bring in…</button><input type="file" id="lb-files" multiple style="display:none" accept=".nif,.dds,.png,.tga,.bmp,.wav,.ogg,.mp3"></div>
      <div id="lb-crumbs"></div><div id="lb-grid"></div></div>
    <div id="lb-detail"><div class="note" style="padding:24px 0">Pick something to see it here.</div></div>`;
  $('#page-create').after(main);
  const nav = document.createElement('button');
  nav.id = 'nav-library'; nav.title = 'Every mesh, texture and sound the game has, and your own files';
  nav.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 4h4v16H4zM10 4h4v16h-4z"/><path d="M16.5 5l3.8 1-3.8 14.5-3.8-1z" transform="translate(0 0)"/></svg>Library';
  $('#nav-world').after(nav);
  PAGES.push('library');
  nav.onclick = () => { page('library'); lbOpen(); };
  $('#lb-q').addEventListener('input', () => { clearTimeout(LB.timer); LB.timer = setTimeout(() => { LB.q = $('#lb-q').value.trim(); lbList(); }, 220); });
  $('#lb-add').onclick = () => $('#lb-files').click();
  $('#lb-files').onchange = e => { lbBring([...e.target.files]); e.target.value = ''; };
  main.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('Files')){ e.preventDefault(); main.classList.add('lb-drop-over'); } });
  main.addEventListener('dragleave', e => { if (e.target === main || !main.contains(e.relatedTarget)) main.classList.remove('lb-drop-over'); });
  main.addEventListener('drop', e => { e.preventDefault(); main.classList.remove('lb-drop-over'); lbBring([...e.dataTransfer.files]); });
  $('#lb-kinds').onclick = e => { const r = e.target.closest('[data-k]'); if (r){ LB.kind = r.dataset.k; LB.folder = ''; lbList(); lbDrawKinds(); } };
  $('#lb-folders').onclick = e => { const r = e.target.closest('[data-f]'); if (r){ LB.folder = r.dataset.f; LB.q = ''; $('#lb-q').value = ''; lbList(); } };
  $('#lb-crumbs').onclick = e => { const a = e.target.closest('[data-f]'); if (a){ LB.folder = a.dataset.f; lbList(); } };
  $('#lb-grid').onclick = e => {
    const t = e.target.closest('.lb-tile'); if (t){ if (t.dataset.f !== undefined){ LB.folder = t.dataset.f; lbList(); } else lbChoose(t.dataset.p); return; }
    if (e.target.id === 'lb-morebtn') lbList(true);
  };
})();

async function lbOpen(){
  if (!LB.rows.length && !LB.folders.length) await lbList();
  lbCounts();
}
async function lbCounts(){
  try { LB.counts = await api('/api/library/counts'); LB.kinds = LB.counts.kinds; lbDrawKinds(); } catch (e){}
}
function lbDrawKinds(){
  const c = LB.counts || {};
  $('#lb-kinds').innerHTML = LB_KINDS.map(([k, l, i]) => `<div class="row${LB.kind === k ? ' on' : ''}" data-k="${k}"><div>${i} ${l}</div><span class="n">${c[k] === undefined ? '' : c[k].toLocaleString()}</span></div>`).join('');
}
async function lbList(more){
  const t = ++LB.token;
  const u = new URLSearchParams({kind: LB.kind, folder: LB.folder, q: LB.q, offset: more ? LB.rows.length : 0, limit: 120});
  const d = await api('/api/library/list?' + u);
  if (t !== LB.token) return;
  if (more) LB.rows = LB.rows.concat(d.rows);
  else { LB.rows = d.rows; LB.folders = d.folders; $('#lb-grid').scrollTop = 0; }
  LB.total = d.total;
  lbDraw(more);
}
function lbTile(r){
  const k = /\.nif$/.test(r.path) ? 'mesh' : /\.(dds|tga|bmp)$/.test(r.path) ? 'texture' : 'sound';
  const pic = k === 'sound' ? '🔊' : `<img loading="lazy" src="${lbThumb(r.path)}" alt="" onerror="this.replaceWith('?')">`;
  return `<div class="lb-tile${LB.chosen === r.path ? ' on' : ''}" data-p="${esc(r.path)}" title="${esc(r.path)}"><div class="pic">${pic}</div><span>${esc(lbName(r.path))}</span>${LB.q || r.own ? `<small>${esc(r.path.split('\\').slice(0, -1).join('\\'))}</small>` : ''}</div>`;
}
function lbDraw(more){
  const grid = $('#lb-grid');
  const parts = LB.folder ? LB.folder.split('\\') : [];
  $('#lb-crumbs').innerHTML = LB.q ? `${LB.total.toLocaleString()} found${LB.folder ? ' in ' + esc(LB.folder) : ''}` :
    LB.kind === 'mine' ? `${LB.total} of your own: kept with your mod, in the game with it. Bring in more with the button, or drop them here.` :
    [`<a data-f="">All ${LB.kind === 'mesh' ? 'meshes' : LB.kind + 's'}</a>`].concat(parts.map((p, i) => `<a data-f="${esc(parts.slice(0, i + 1).join('\\'))}">${esc(p)}</a>`)).join(' › ');
  const folderTiles = LB.q ? '' : LB.folders.map(f => `<div class="lb-tile folder" data-f="${esc(f.path)}" title="${f.n} files"><div class="pic">📁</div><span>${esc(f.name)}</span><small>${f.n.toLocaleString()}</small></div>`).join('');
  const moreBtn = LB.rows.length < LB.total ? `<div id="lb-more"><button class="btn" id="lb-morebtn">Show more (${(LB.total - LB.rows.length).toLocaleString()} left)</button></div>` : '';
  const none = !LB.rows.length && !LB.folders.length ? `<div class="note" style="grid-column:1/-1;padding:24px">${LB.kind === 'mine' ? 'Nothing of your own yet. ＋ Bring in… takes .nif meshes, pictures (.dds .png .tga .bmp) and sounds from anywhere on your computer.' : 'Nothing found.'}</div>` : '';
  grid.innerHTML = folderTiles + LB.rows.map(lbTile).join('') + moreBtn + none;
  $('#lb-folders').innerHTML = LB.folders.length ? LB.folders.map(f => `<div class="row" data-f="${esc(f.path)}"><div>${esc(f.name)}</div><span class="n">${f.n.toLocaleString()}</span></div>`).join('') : '<div class="note">No folders below this one.</div>';
}
async function lbChoose(p){
  LB.chosen = p;
  document.querySelectorAll('#lb-grid .lb-tile').forEach(x => x.classList.toggle('on', x.dataset.p === p));
  const t = ++LB.infoToken || (LB.infoToken = 1), box = $('#lb-detail');
  box.innerHTML = `<div id="lb-view"></div><h3>${esc(lbName(p))}</h3><div class="lb-path">${esc(p)}</div><div id="lb-info"><div class="note" style="padding:0">Looking…</div></div>`;
  const view = $('#lb-view'), ext = p.split('.').pop();
  if (ext === 'nif') mpShow(view, p.replace(/^meshes\\/, '')).then(b => { if (!b && view.isConnected && t === LB.infoToken) view.innerHTML = '<div class="note">Nothing FOLab can draw in it.</div>'; });
  else if (['wav', 'ogg', 'mp3'].includes(ext)) view.innerHTML = `<audio controls autoplay src="/api/library/file?path=${encodeURIComponent(p)}"></audio>`;
  else view.innerHTML = `<img src="${lbThumb(p, 512)}" alt="">`;
  let d;
  try { d = await api('/api/library/info?path=' + encodeURIComponent(p)); } catch (e){ $('#lb-info').innerHTML = `<div class="note">${esc(e.message)}</div>`; return; }
  if (t !== LB.infoToken) return;
  LB.info = d;
  const kv = (k, v) => v === undefined || v === '' ? '' : `<div class="lb-kv">${k}: <b>${esc(v)}</b></div>`;
  let h = kv('From', d.from) + kv('Size on disk', lbBytes(d.bytes));
  if (d.kind === 'mesh'){
    h += d.error ? `<div class="note" style="padding:0">${esc(d.error)}</div>` : kv('Shapes', d.shapes) + kv('Triangles', (d.tris || 0).toLocaleString()) + (d.size ? kv('How big', d.size.join(' × ') + ' units (a person is about 128 tall)') : '');
    h += `<div class="lb-acts"><button class="btn primary" data-lb="make" title="A record of your mod's own, drawn with this mesh">Make a thing from it…</button>${d.textures && d.textures.length ? '<button class="btn" data-lb="retex" title="A copy of this mesh with other pictures, kept with your mod">🎨 Retexture…</button>' : ''}${d.own ? '<button class="btn" data-lb="rm">✕ Take it out</button>' : ''}</div>`;
    if (d.things && d.things.length) h += `<div class="h" style="padding-left:0">Things drawn with it</div>` + d.things.slice(0, 12).map((x, i) => `<div class="lb-tex" data-th="${i}" title="Place it"><div>${esc(x.edid)}<small>${esc(x.name || x.type)}${x.own ? ' · your own' : ''}</small></div></div>`).join('');
    if (d.textures && d.textures.length) h += `<div class="h" style="padding-left:0">Textures</div>` + d.textures.map(x => `<div class="lb-tex" data-tx="${esc(x.path)}"><img loading="lazy" src="${lbThumb(x.path.toLowerCase().startsWith('textures') ? x.path : 'textures\\' + x.path, 64)}" alt=""><div>${esc(x.path)}<small class="${x.found ? '' : 'gone'}">${esc(x.label)}${x.found ? '' : ' · not found: the game would draw it purple'}</small></div></div>`).join('');
  } else if (d.kind === 'texture'){
    h += kv('Picture', d.w ? `${d.w} × ${d.h}, ${d.format}, ${d.mips} level${d.mips === 1 ? '' : 's'}` : '');
    h += `<div class="lb-acts"><button class="btn" data-lb="txst" title="A texture set record of your mod's own, naming this picture">Make a texture set</button>${d.own ? '<button class="btn" data-lb="rm">✕ Take it out</button>' : ''}</div>
      <div class="note" style="padding:0">To put it on something: right-click the thing in 3D, Retexture, or pick a mesh here and press Retexture.</div>`;
  } else {
    h += kv('Format', d.format) + kv('Channels', d.channels) + kv('Rate', d.rate ? d.rate + ' Hz' : '') + kv('Length', d.seconds !== undefined ? d.seconds + ' s' : '');
    if (d.own) h += '<div class="lb-acts"><button class="btn" data-lb="rm">✕ Take it out</button></div>';
  }
  $('#lb-info').innerHTML = h;
}
$('#lb-detail').addEventListener('click', async e => {
  const d = LB.info; if (!d) return;
  const th = e.target.closest('[data-th]');
  if (th) return lbPlace(d.things[+th.dataset.th]);
  const tx = e.target.closest('[data-tx]');
  if (tx){ const p = tx.dataset.tx.toLowerCase(); LB.kind = 'texture'; LB.folder = (p.startsWith('textures') ? p : 'textures\\' + p).split('\\').slice(0, -1).join('\\'); LB.q = ''; $('#lb-q').value = ''; lbDrawKinds(); await lbList(); return lbChoose(p.startsWith('textures') ? p : 'textures\\' + p); }
  const a = e.target.dataset.lb; if (!a) return;
  if (a === 'make') return lbMakeThing(d);
  if (a === 'retex') return lbRetexture({model: d.path, textures: d.textures});
  try {
    if (a === 'txst'){ const r = await post('/api/library/texture_set', {path: d.path}); setState(r.state); toast('Made the texture set ' + r.edid + ': it\'s on the Browse page.'); }
    if (a === 'rm'){ const r = await post('/api/library/remove', {path: d.path}); setState(r.state); LB.chosen = null; $('#lb-detail').innerHTML = ''; lbList(); lbCounts(); toast('Taken out of your mod.'); }
  } catch (err){ fail(err); }
});

// a thing from a mesh: what kind, then it's ready to place
function lbMakeThing(d){
  const stem = lbName(d.path).replace(/\.nif$/, ''), id = 'FOLab' + stem.split(/[^a-z0-9]+/i).filter(Boolean).map(w => w[0].toUpperCase() + w.slice(1)).join('');
  const box = document.createElement('div');
  box.className = 'owin'; box.style.cssText = 'left:50%;top:22%;transform:translateX(-50%);width:460px';
  box.innerHTML = `<div class="owtitle"><b>Make a thing from ${esc(stem)}</b><button class="owx">✕</button></div>
    <div style="padding:10px 14px">
      <div class="fields" style="grid-template-columns:90px 1fr;padding:6px 0"><label>Name</label><input id="lm-name" value="${esc(stem.replace(/_/g, ' '))}"><label>Editor ID</label><input id="lm-edid" value="${esc(id)}"></div>
      ${Object.entries(LB.kinds).map(([k, v], i) => `<label style="display:block;margin:3px 0"><input type="radio" name="lm-k" value="${k}" ${i ? '' : 'checked'}> ${esc(v)}</label>`).join('')}
    </div><div class="owfoot"><button class="btn primary" id="lm-go">Make it, and place it</button><button class="btn" id="lm-only">Just make it</button><button class="btn" id="lm-no">Cancel</button></div>`;
  document.body.appendChild(box);
  const close = () => box.remove();
  box.querySelector('.owx').onclick = box.querySelector('#lm-no').onclick = close;
  const go = async place => {
    try {
      const r = await post('/api/library/make', {path: d.path, type: box.querySelector('input[name="lm-k"]:checked').value, edid: box.querySelector('#lm-edid').value, name: box.querySelector('#lm-name').value});
      close(); setState(r.state); remember(r.item);
      toast(`${r.item.edid} is yours: it's in Place, under Recently used.`);
      if (place) lbPlace(r.item); else lbChoose(d.path);
    } catch (e){ fail(e); }
  };
  box.querySelector('#lm-go').onclick = () => go(true);
  box.querySelector('#lm-only').onclick = () => go(false);
}
function lbPlace(it){
  page('world');
  if (!A.cellId) return toast('Open a place first.', true);
  remember(it); startPlacing(it); W.ren.domElement.focus();
  const h = $('#hint'); h.textContent = `Click where ${it.edid} goes · Esc or right-click stops`; h.style.display = 'block';
}

// ---------- bringing files in ----------
async function lbBring(files){
  files = files.filter(f => f.size);
  if (!files.length) return;
  if (!A.state.project) return toast('Start a mod first: what you bring in is kept with it.', true);
  const total = files.reduce((s, f) => s + f.size, 0);
  if (total > 300 * 1048576) return toast('That\'s more than 300 MB at once: bring them in a few at a time.', true);
  toast(`Bringing in ${files.length} file${files.length === 1 ? '' : 's'} (${lbBytes(total)})…`);
  try {
    const list = [];
    for (const f of files){
      const bytes = new Uint8Array(await f.arrayBuffer());
      let s = '';
      for (let i = 0; i < bytes.length; i += 32768) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
      list.push({name: f.name, data: btoa(s)});
    }
    const d = await post('/api/library/bring', {files: list});
    setState(d.state);
    LB.kind = 'mine'; LB.folder = ''; LB.q = ''; $('#lb-q').value = '';
    page('library'); lbDrawKinds(); await lbList(); lbCounts();
    if (d.made.length) lbChoose(d.made[d.made.length - 1].path);
    toast(d.warnings.length ? d.warnings.join(' ') : `${d.made.length} brought in: they go in the game with your mod.`, d.warnings.length > 0);
  } catch (e){ fail(e); }
}

// ---------- Retexture: pick other pictures for a mesh's textures ----------
// what: {model, textures: [{path, label}], key (a record to copy), ref + cell (a placed thing to swap)}
async function lbRetexture(what){
  if (!A.state.project) return toast('Start a mod first.', true);
  if (!what.textures){
    const d = await api('/api/library/info?path=' + encodeURIComponent(what.model));
    what.textures = d.textures || [];
  }
  if (!what.textures.length) return toast('That mesh names no textures.', true);
  if (!what.key){
    const things = (LB.info && LB.info.things) || [];
    if (things.length) what.key = things[0].key;
  }
  const seen = new Set(), slots = what.textures.filter(t => { const k = t.path.toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true; }).map(t => ({path: t.path, label: t.label, to: null}));
  let cur = slots.findIndex(s => s.label === 'Picture'); if (cur < 0) cur = 0;
  const box = document.createElement('div');
  box.id = 'lb-rt';
  box.innerHTML = `<div class="lb-rtcard"><div class="mp-head"><b>Retexture ${esc(lbName(what.model))}</b><button class="btn" data-rt="close">✕</button></div>
    <div class="lb-rtbody"><div class="lb-rtl"><div class="note" style="padding:0 0 6px">Pick a texture of the mesh, then the picture to put in its place. The game's mesh isn't touched: you get a copy, kept with your mod.</div><div id="rt-slots"></div>
        <label style="display:block;margin:8px 0 4px;color:var(--muted);font-size:12.5px">Editor ID of the new thing<input id="rt-edid" style="width:100%;margin-top:3px" placeholder="(made from the old one)"></label>
        <button class="btn primary" data-rt="go" disabled>${what.ref ? 'Make it and swap this one for it' : what.key ? 'Make it' : 'Make the mesh'}</button> <span class="note" id="rt-note"></span></div>
      <div class="lb-rtr"><input id="rt-q" class="find" style="margin:0" placeholder="Search textures: rust, wood, your own first…"><div class="note" id="rt-n" style="padding:4px 0 0"></div><div class="lb-pickgrid" id="rt-grid"></div></div></div></div>`;
  document.body.appendChild(box);
  const q = box.querySelector('#rt-q');
  const texThumb = p => lbThumb(p.toLowerCase().startsWith('textures') ? p : 'textures\\' + p, 64);
  const draw = () => {
    box.querySelector('#rt-slots').innerHTML = slots.map((s, i) => `<div class="lb-slot${i === cur ? ' on' : ''}" data-i="${i}"><img src="${texThumb(s.to || s.path)}" alt=""><div><b>${esc(s.label)}</b><small>${esc(s.path)}</small>${s.to ? `→ ${esc(s.to)}` : ''}</div></div>`).join('');
    box.querySelector('[data-rt="go"]').disabled = !slots.some(s => s.to);
  };
  let tk = 0;
  const list = async () => {
    const t = ++tk, words = q.value.trim();
    const [own, d] = await Promise.all([api('/api/library/list?' + new URLSearchParams({kind: 'mine', q: words, limit: 60})),
      words ? api('/api/library/list?' + new URLSearchParams({kind: 'texture', q: words, limit: 200})) : Promise.resolve({rows: [], total: 0})]);
    if (t !== tk) return;
    const rows = own.rows.filter(r => /\.dds$/.test(r.path)).concat(d.rows.filter(r => !r.own));
    box.querySelector('#rt-n').textContent = words ? `${d.total.toLocaleString()} found` : 'Your own pictures show here. Type to search the game\'s.';
    box.querySelector('#rt-grid').innerHTML = rows.map(r => `<div class="lb-tile" data-p="${esc(r.path)}" title="${esc(r.path)}"><div class="pic" style="height:78px"><img loading="lazy" src="${lbThumb(r.path, 64)}" alt=""></div><span>${esc(lbName(r.path))}</span></div>`).join('');
  };
  let timer;
  q.oninput = () => { clearTimeout(timer); timer = setTimeout(list, 220); };
  box.addEventListener('click', async e => {
    const s = e.target.closest('.lb-slot'); if (s){ cur = +s.dataset.i; draw(); return; }
    const t = e.target.closest('.lb-tile'); if (t){ slots[cur].to = t.dataset.p; draw(); return; }
    const a = e.target.dataset.rt;
    if (a === 'close' || e.target === box) return box.remove();
    if (a === 'go'){
      const changes = {}; for (const x of slots) if (x.to) changes[x.path] = x.to;
      try {
        const body = {model: what.model, changes, name: lbName(what.model).replace(/\.nif$/, '') + '_retex', edid: box.querySelector('#rt-edid').value.trim() || undefined};
        if (what.key){
          const r = await post('/api/library/retexture', Object.assign(body, {key: what.key, ref: what.ref, cell: what.cell}));
          setState(r.state); box.remove(); if (what.ref){ await resync(); const g = W.byKey.get(what.ref); if (g && g.userData.ready) await g.userData.ready; select([what.ref]); }
          toast(`${r.edid}: its own mesh, kept with your mod${what.ref ? ', and swapped in here' : ''}.`);
        } else {
          const r = await post('/api/library/retexture_file', body);
          setState(r.state); box.remove(); toast('A new mesh among your own: ' + lbName(r.model));
          LB.kind = 'mine'; lbDrawKinds(); lbList(); lbChoose(r.model);
        }
      } catch (err){ fail(err); }
    }
  });
  draw(); list(); q.focus();
}
