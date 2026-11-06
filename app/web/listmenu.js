// ---------- right-click on the lists: places, objects, worlds, things to place, and any other row ----------
// Edge's own menu only shows where it's some use: in a box you type in, or on text you've selected. Everywhere else a
// right-click is FOLab's. (The 3D view, the map and the toolbar's groups have their own, and say so with preventDefault.)
function cmList(e, head, rows){
  cmClose();
  const items = rows.filter(r => r !== '-');
  const el = CM.el = document.createElement('div');
  el.className = 'cmenu';
  const sep = rows.map((r, i) => r === '-' && (i === 0 || i === rows.length - 1 || rows[i - 1] === '-') ? null : r).filter(r => r !== null);
  el.innerHTML = (head ? `<div class="cmhead">${esc(head)}</div><div class="cmsep"></div>` : '') +
    sep.map(r => r === '-' ? '<div class="cmsep"></div>' : `<div class="cmi" data-i="${items.indexOf(r)}">${esc(r[0])}</div>`).join('');
  document.body.appendChild(el);
  const b = el.getBoundingClientRect();
  el.style.left = Math.min(e.clientX, innerWidth - b.width - 8) + 'px';
  el.style.top = Math.max(8, Math.min(e.clientY, innerHeight - b.height - 8)) + 'px';
  el.addEventListener('click', ev => { const i = ev.target.closest('.cmi'); if (i){ cmClose(); items[+i.dataset.i][1](); } });
}

async function lmCopy(text, what){
  try { await navigator.clipboard.writeText(text); toast(`Copied ${what || text}`); }
  catch (e){ toast('Windows wouldn\'t let FOLab use the clipboard just now.', true); }
}

// ---------- a place ----------
function placeRename(c){
  const box = document.createElement('div');
  box.className = 'owin'; box.style.cssText = 'left:50%;top:22%;transform:translateX(-50%);width:420px';
  box.innerHTML = `<div class="owtitle"><b>Rename ${esc(c.name || c.edid)}</b><button class="owx">✕</button></div>
    <div style="padding:10px 14px"><div class="fields" style="grid-template-columns:90px 1fr;padding:6px 0">
      <label>Name</label><input id="pr-name" value="${esc(c.name || '')}">
      <label>Editor ID</label><input id="pr-edid" value="${esc(c.edid)}">
    </div><p class="note" style="padding:0">The editor ID is what the console's <code>coc</code> uses. If it's taken, FOLab adds a number.</p></div>
    <div class="owfoot"><button class="btn primary" id="pr-go">Rename</button><button class="btn" id="pr-cancel">Cancel</button></div>`;
  document.body.appendChild(box);
  const close = () => box.remove(), name = box.querySelector('#pr-name'), edid = box.querySelector('#pr-edid');
  box.querySelector('.owx').onclick = close; box.querySelector('#pr-cancel').onclick = close;
  name.focus(); name.select();
  box.querySelector('#pr-go').onclick = async () => {
    const want = edid.value.replace(/[^A-Za-z0-9_]/g, '');
    if (!want) return toast('The editor ID needs letters or numbers.', true);
    try {
      const d = await post('/api/place/rename', {id: c.id, name: name.value.trim() || want, edid: want});
      close(); setState(d.state); await loadPlaces();
      if (A.cellId === c.id){ A.cellEdid = d.edid; $('#s-place').textContent = (name.value.trim() ? name.value.trim() + ' · ' : '') + d.edid; }
      toast(d.edid === want ? 'Renamed' : `Renamed. ${want} was taken, so its editor ID is ${d.edid}`);
    } catch (e){ fail(e); }
  };
}

async function placeTakeAway(c, url, ask){
  try {
    const k = await api('/api/place/check?id=' + encodeURIComponent(c.id)), bits = [];
    if (k.things) bits.push(`${k.things} thing${k.things === 1 ? '' : 's'} or change${k.things === 1 ? '' : 's'}`);
    if (k.navmesh) bits.push('its navmesh');
    if (k.doors) bits.push(`the link on ${k.doors} door${k.doors === 1 ? '' : 's'} elsewhere that lead${k.doors === 1 ? 's' : ''} here`);
    let q = ask(c.name || c.edid) + (bits.length ? `\n\nThis takes out ${bits.join(', ')}.` : '');
    if (k.used_by && k.used_by.length) q += `\n\nStill named by: ${k.used_by.slice(0, 5).join(', ')}${k.used_by.length > 5 ? '…' : ''}. The health check will point those out.`;
    if (!confirm(q + '\n\nUndo takes it all back.')) return;
    const d = await post(url, {id: c.id});
    setState(d.state);
    const was = A.cellId === c.id;
    await loadPlaces();
    if (!was) return resync();
    const next = A.places.find(p => p.id === c.id) || A.places.find(p => p.own) || A.places[0];
    if (next) await openPlace(next.id);
  } catch (e){ fail(e); }
}

async function placeNavmesh(c){
  toast(`Making the navmesh for ${c.name || c.edid}…`);
  try {
    const d = await post('/api/navmesh/make', {cell: c.id});
    if (d.note) return toast(d.note, true);
    setState(d.state);
    toast(`Navmesh made: ${d.report.triangles} triangles`);
    if (A.cellId === c.id && typeof navDraw === 'function'){ navDraw(); navOverlay(); }
  } catch (e){ fail(e); }
}

function placeMenu(e, c){
  const mod = A.state && A.state.project, here = A.cellId === c.id, pinned = PLACE_PINS.has(c.id);
  const rows = [];
  if (!here) rows.push(['Open', () => openPlace(c.id)]);
  rows.push([here ? 'Play here' : 'Open and play here', async () => { if (!here) await openPlace(c.id); playHere(); }]);
  rows.push('-');
  if (mod){
    rows.push(['Make a copy of your own…', () => newPlaceDialog(c.id)]);
    if (c.own) rows.push(['Rename…', () => placeRename(c)]);
    rows.push(['Make its navmesh', () => placeNavmesh(c)]);
  }
  rows.push(['Open its record', () => openRecord(c.id)]);
  rows.push('-');
  rows.push(['Copy the console line to come here', () => lmCopy('coc ' + c.edid)]);
  rows.push(['Copy its editor ID', () => lmCopy(c.edid)]);
  rows.push([pinned ? 'Unpin from the top' : 'Pin to the top', () => {
    pinned ? PLACE_PINS.delete(c.id) : PLACE_PINS.add(c.id);
    try { localStorage.setItem('folab-pins', JSON.stringify([...PLACE_PINS])); } catch (err) {}
    drawPlaces();
  }]);
  if (mod && c.own) rows.push('-', ['Delete this place…', () => placeTakeAway(c, '/api/place/delete', n => `Delete ${n} from your mod?`)]);
  else if (mod && c.mine) rows.push('-', ['Put back as the game has it…', () => placeTakeAway(c, '/api/place/putback', n => `Put ${n} back as the game has it?`)]);
  cmList(e, c.name || c.edid, rows);
}

// ---------- the rest ----------
function outsideMenu(e, r){
  const open = ['Open', () => r.click()];
  if (r.dataset.world){
    const w = OUT.worlds.find(x => x.id === r.dataset.world);
    return cmList(e, w ? w.name || w.edid : '', [open, ['Open its record', () => openRecord(r.dataset.world)], '-', ['Copy its editor ID', () => lmCopy(w.edid)]]);
  }
  if (r.dataset.mark){
    const m = OUT.info.markers[+r.dataset.mark], x = Math.floor(m.p[0] / CELL), y = Math.floor(m.p[1] / CELL);
    return cmList(e, m.name, [['Go there', () => r.click()], '-', ['Copy its name', () => lmCopy(m.name)], ['Copy its square', () => lmCopy(`${x}, ${y}`)],
      ['Copy the console line to come here', () => lmCopy(`cow ${OUT.info.edid} ${x} ${y}`)]]);
  }
  cmList(e, '', [open]);
}

function placeableMenu(e, r){
  const it = findItem(r.dataset.key);
  if (!it) return rowMenu(e, r);
  cmList(e, it.edid, [['Place it', () => r.click()], ['Open its record', () => openRecord(it.key)], '-', ['Copy its editor ID', () => lmCopy(it.edid)]]);
}

function rowMenu(e, r){
  const main = r.querySelector('div') || r, small = main.querySelector('small');
  const whole = main.textContent.trim(), sub = small ? small.textContent.trim() : '';
  const name = (sub && whole.endsWith(sub) ? whole.slice(0, -sub.length) : whole).trim(), id = sub.split(' · ')[0].trim();
  const rows = [['Open', () => r.click()]];
  if (name) rows.push('-', ['Copy its name', () => lmCopy(name)]);
  if (id && id !== name && /^[\w.:+-]+$/.test(id)) rows.push(['Copy ' + id, () => lmCopy(id)]);
  cmList(e, name, rows);
}

addEventListener('contextmenu', e => {
  if (e.defaultPrevented) return;
  const t = e.target;
  if (t.closest('textarea, [contenteditable="true"], input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=button])')) return;
  const picked = String(getSelection());
  if (picked.trim() && getSelection().containsNode(t, true)) return;
  e.preventDefault();
  if (t.closest('.cmenu')) return;
  if (t.closest('.brand')) return cmList(e, '', [['Home', () => page('home')], ['About FOLab…', helpAbout]]);
  const r = t.closest('.row');
  if (r && r.closest('#places')){ const c = A.places.find(p => p.id === r.dataset.id); return c ? placeMenu(e, c) : undefined; }
  if (r && r.closest('#objects')){
    const k = r.dataset.key;
    if (!A.sel.includes(k)) select([k]);
    return cmOpen(e, k, null);
  }
  if (r && r.closest('#outside')) return outsideMenu(e, r);
  if (r && r.closest('#found, #recent')) return placeableMenu(e, r);
  if (r && !r.closest('#tbmenu')) return rowMenu(e, r);
  if (t.closest('#tab-places') && A.state && A.state.project) return cmList(e, '', [['New place of your own…', newPlaceDialog]]);
});
