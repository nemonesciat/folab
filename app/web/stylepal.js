// ---------- Suggested for this place, and the Style palette ----------
// Learnt from how the game dresses its own places (stylesurvey.py). In the Place panel: what the places most like this
// one hold that this one doesn't yet. In a window over the view: the game's things by style (a casino, a vault, a shack)
// and by what they're for, with the sets the game puts together, to click and place or drag into the view.
const SG = {token: 0, rows: [], style: null, styles: null, pal: null, q: '', goes: {}};
const sgThumb = (m, w) => m ? `/api/library/thumb?w=${w || 64}&path=${encodeURIComponent(m)}` : '';

(function sgMake(){
  const css = document.createElement('style');
  css.textContent = `
  .sg-row{gap:6px}.sg-row img{width:34px;height:34px;object-fit:contain;flex:none;background:var(--bg2);border-radius:4px}.sg-row>div{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
  .sg-head{display:flex;align-items:center;gap:6px;padding:10px 12px 2px}.sg-head b{font:600 11px Inter,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase;flex:1}
  .sg-head button{background:none;border:none;color:var(--muted);cursor:pointer;padding:0 3px}.sg-head button:hover{color:var(--gold2)}
  #sg-like{color:var(--faint);font-size:11.5px;padding:0 12px 3px}
  #sg-list{max-height:280px;overflow-y:auto;flex:none}
  #spwin{width:min(980px,calc(100vw - 40px));height:min(660px,calc(100vh - 110px));display:flex;flex-direction:column}
  .sp-body{flex:1;display:flex;min-height:0}.sp-tabs{width:190px;flex:none;overflow-y:auto;border-right:1px solid var(--line)}.sp-main{flex:1;min-width:0;overflow-y:auto;padding:8px 12px 20px}
  .sp-sec{margin:10px 0 4px;color:var(--gold2);font-size:14px}.sp-sec small{color:var(--faint);margin-left:8px;font-size:12px}
  .sp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(98px,1fr));gap:6px}
  .row.sp-tile{display:block;padding:3px;background:var(--panel2);border:1px solid var(--line);border-radius:7px;position:relative;cursor:grab}.row.sp-tile:hover{border-color:var(--goldline)}
  .sp-tile img{width:100%;aspect-ratio:1;object-fit:contain;background:var(--bg2);border-radius:4px;display:block}
  .sp-tile span{display:block;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}
  .sp-star{position:absolute;left:5px;top:5px;font-size:10px;padding:0 4px;border-radius:4px;background:var(--gold);color:var(--bg)}
  .sp-sets{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px}
  .sp-set{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:6px;cursor:pointer}.sp-set:hover{border-color:var(--goldline)}.sp-set img{width:64px;height:64px;object-fit:contain;float:left;margin-right:6px;background:var(--bg2);border-radius:4px}
  .sp-set b{font-weight:500;color:var(--text);font-size:12.5px}.sp-set small{display:block;color:var(--faint);font-size:11px}
  #sp-goes{border-top:1px solid var(--line);padding:5px 12px;font-size:12px;color:var(--muted);min-height:29px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}`;
  document.head.appendChild(css);
  const h = document.createElement('div');
  h.innerHTML = `<div class="sg-head" id="sg-head"><b>Suggested for this place</b><button id="sg-again" title="Look again, at what's here now">↻</button></div><div id="sg-like"></div><div id="sg-list"></div>`;
  const found = [...document.querySelectorAll('#tab-place .h')].find(x => x.textContent === 'Found');
  while (h.firstChild) found.before(h.firstChild);
  const note = $('#place-note');
  const pb = document.createElement('div');
  pb.style.cssText = 'padding:0 12px 4px';
  pb.innerHTML = '<button class="btn" id="sp-open" title="The game\'s things by style, and the sets it puts together: see what goes with what, then click or drag to place">🎨 Style palette…</button>';
  note.after(pb);
  $('#sp-open').onclick = spOpen;
  $('#sg-again').onclick = sgLook;
  const list = $('#sg-list');
  list.addEventListener('click', e => { const r = e.target.closest('[data-i]'); if (r){ sgFound(SG.rows[+r.dataset.i]); pickToPlace(e); } });
  list.addEventListener('dragstart', e => { const r = e.target.closest('[data-i]'); if (r){ sgFound(SG.rows[+r.dataset.i]); e.dataTransfer.setData('text/x-folab', r.dataset.key); e.dataTransfer.effectAllowed = 'copy'; } });
  // a Style button with the other buttons over the view
  const b = document.createElement('button');
  b.className = 'btn'; b.id = 't-style'; b.textContent = '🎨 Style'; b.title = 'The Style palette: the game\'s things by style, and sets';
  b.onclick = spOpen;
  document.querySelector('.tgrp[data-grp="edit"]').appendChild(b);
  // what's here changed: a new place
  const _op = openPlace;
  openPlace = (id, at) => { const r = _op(id, at); setTimeout(sgLook, 300); return r; };   // (A.cellId is set at once; a big place takes a while to draw)
  const _go = goOutside;
  goOutside = (info, at) => { const r = _go(info, at); setTimeout(sgLook, 5000); return r; };
})();

// (what the Place panel's own click and drag look up)
function sgFound(it){ if (!found.some(x => x.key === it.key)) found.push(it); }

function sgRow(it, i){ return `<div class="row sg-row" draggable="true" data-i="${i}" data-key="${esc(it.key)}" title="${esc(it.model)}${it.seen ? ' · as in ' + esc(it.seen) : ''} · click, then click where it goes, or drag it into the view"><img loading="lazy" src="${sgThumb(it.model)}" alt=""><div>${esc(it.edid)}<small>${esc(it.name || (it.seen ? 'as in ' + it.seen : ''))}</small></div></div>`; }

function sgHere(){
  if (!A.outside) return A.cellId ? [A.cellId] : [];
  // outside: the cells nearest the camera
  const c = W.cam.position, cells = [...OUT.cells.values()].filter(x => x.data && x.data.cell);
  cells.sort((a, b) => Math.hypot(a.x * 4096 + 2048 - c.x, a.y * 4096 + 2048 - c.y) - Math.hypot(b.x * 4096 + 2048 - c.x, b.y * 4096 + 2048 - c.y));
  return cells.slice(0, 9).map(x => x.data.cell);
}
async function sgLook(){
  const t = ++SG.token, cells = sgHere(), list = $('#sg-list');
  if (!cells.length){ list.innerHTML = '<div class="note">Open a place to see what fits it.</div>'; return; }
  const d = await api('/api/library/suggest?cells=' + encodeURIComponent(cells.join(';'))).catch(() => null);
  if (t !== SG.token || !d) return;
  if (d.building){ list.innerHTML = '<div class="note">Reading how the game dresses its places (only the first time)…</div>'; setTimeout(() => { if (t === SG.token) sgLook(); }, 3000); return; }
  if (d.error){ list.innerHTML = `<div class="note">${esc(d.error)}</div>`; return; }
  SG.rows = d.rows;
  $('#sg-like').textContent = d.like.length ? 'Like ' + d.like.slice(0, 3).map(l => l.name).join(', ') : d.empty ? 'Nothing here yet: what the game uses most.' : '';
  list.innerHTML = d.rows.map(sgRow).join('') || '<div class="note">Nothing more to suggest.</div>';
}

// ---------- the window ----------
async function spOpen(){
  let w = $('#spwin');
  if (w){ w.remove(); return; }
  w = document.createElement('div');
  w.className = 'owin'; w.id = 'spwin'; w.style.left = '40px'; w.style.top = '80px';
  w.innerHTML = `<div class="owtitle"><b>🎨 Style palette</b><input id="sp-q" placeholder="Filter…" style="margin-left:14px;width:200px" autocomplete="off"><button class="owx" title="Close">✕</button></div>
    <div class="sp-body"><div class="sp-tabs" id="sp-tabs"></div><div class="sp-main" id="sp-main"><div class="note">Reading how the game dresses its places…</div></div></div><div id="sp-goes">Rest the mouse on something to see what the game stands with it.</div>`;
  document.body.appendChild(w);
  w.querySelector('.owx').onclick = () => w.remove();
  w.addEventListener('keydown', e => e.stopPropagation());
  const title = w.querySelector('.owtitle');
  title.addEventListener('pointerdown', ev => {
    if (ev.target.closest('button, input')) return;
    const sx = ev.clientX - w.offsetLeft, sy = ev.clientY - w.offsetTop;
    const mv = m => { w.style.left = (m.clientX - sx) + 'px'; w.style.top = (m.clientY - sy) + 'px'; };
    const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); };
    addEventListener('pointermove', mv); addEventListener('pointerup', up);
  });
  w.querySelector('#sp-q').oninput = e => { SG.q = e.target.value.trim().toLowerCase(); spDraw(); };
  w.querySelector('#sp-tabs').onclick = e => { const r = e.target.closest('[data-st]'); if (r) spStyle(r.dataset.st); };
  const main = w.querySelector('#sp-main');
  main.addEventListener('click', e => {
    const s = e.target.closest('[data-set]');
    if (s) return spSet(SG.pal.sets[+s.dataset.set]);
    const t = e.target.closest('.sp-tile');
    if (t){ sgFound(spRow(t)); pickToPlace(e); }
  });
  main.addEventListener('dragstart', e => { const t = e.target.closest('.sp-tile'); if (t){ sgFound(spRow(t)); e.dataTransfer.setData('text/x-folab', t.dataset.key); e.dataTransfer.effectAllowed = 'copy'; } });
  main.addEventListener('mouseover', e => { const t = e.target.closest('.sp-tile'); if (t) spGoes(t.dataset.key); });
  await spStyles();
}
function spRow(t){ for (const s of SG.pal.sections){ const r = s.rows.find(x => x.key === t.dataset.key); if (r) return r; } }
async function spStyles(){
  const d = await api('/api/library/styles');
  if (d.building) return setTimeout(() => { if ($('#spwin')) spStyles(); }, 2500);
  if (d.error){ $('#sp-main').innerHTML = `<div class="note">${esc(d.error)}</div>`; return; }
  SG.styles = d.styles;
  const row = s => `<div class="row" data-st="${esc(s.name)}"><div>${esc(s.name)}</div><span class="n">${s.places || ''}</span></div>`;
  $('#sp-tabs').innerHTML = `<div class="h">Used everywhere</div><div class="row" data-st="*"><div>In every style</div></div><div class="h">Inside</div>${d.styles.filter(s => !s.out).map(row).join('')}<div class="h">Outside</div>${d.styles.filter(s => s.out).map(row).join('')}`;
  spStyle(SG.style || '*');
}
async function spStyle(name){
  SG.style = name;
  document.querySelectorAll('#sp-tabs .row').forEach(r => r.classList.toggle('on', r.dataset.st === name));
  SG.pal = await api('/api/library/palette?style=' + encodeURIComponent(name));
  spDraw();
}
function spDraw(){
  const p = SG.pal, box = $('#sp-main'); if (!p || !box) return;
  const hit = r => !SG.q || (r.edid + ' ' + r.name).toLowerCase().includes(SG.q);
  let h = `<div class="note" style="padding:0 0 4px">${p.style === '*' ? 'What the game uses in places of every kind.' : `From ${p.places} of the game's places: ${esc(p.examples.join(', '))}…`} Click, then click where it goes, or drag it into the view.</div>`;
  const sets = p.sets.map((s, i) => [s, i]).filter(([s]) => !SG.q || (s.name + ' ' + s.names.join(' ')).toLowerCase().includes(SG.q));
  if (sets.length) h += `<div class="sp-sec">Sets<small>What the game puts together, placed whole as one Undo</small></div><div class="sp-sets">${sets.map(([s, i]) => `<div class="sp-set" data-set="${i}" title="As in ${esc(s.from)}. The game has this ${s.uses} times."><img loading="lazy" src="${sgThumb(s.lead, 96)}" alt=""><b>${esc(s.name)}</b><small>${s.count} things, as in ${esc(s.from)}</small></div>`).join('')}</div>`;
  for (const s of p.sections){
    const rows = s.rows.filter(hit);
    if (rows.length) h += `<div class="sp-sec">${esc(s.label)}<small>${esc(s.about)}</small></div><div class="sp-grid">${rows.map(r => `<div class="row sp-tile" draggable="true" data-key="${esc(r.key)}" title="${esc(r.edid)}${r.name ? ' · ' + esc(r.name) : ''} · in ${Math.round((r.share || 0) * 100)}% of these places">${r.staple ? '<span class="sp-star">staple</span>' : ''}<img loading="lazy" src="${sgThumb(r.model, 96)}" alt=""><span>${esc(r.name || r.edid)}</span></div>`).join('')}</div>`;
  }
  box.innerHTML = h;
}
function spSet(s){
  if (!A.cellId) return toast('Open a place first.', true);
  startPlacing({prefab: s.name, items: s.items});
  W.ren.domElement.focus();
  const h = $('#hint'); h.textContent = `Click where ${s.name} goes · Esc or right-click stops`; h.style.display = 'block';
}
async function spGoes(key){
  if (SG.goesKey === key) return;
  SG.goesKey = key;
  const d = SG.goes[key] || (SG.goes[key] = await api('/api/library/goes?key=' + encodeURIComponent(key)));
  const box = $('#sp-goes');
  if (box && SG.goesKey === key) box.textContent = d.rows && d.rows.length ? 'The game stands with it: ' + d.rows.slice(0, 6).map(r => r.name || r.edid).join(', ') : 'Stands on its own in the game.';
}
