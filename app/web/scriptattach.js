// ---------- Scripts page: a script on a thing ----------
// The record's SCRI, from three places: What runs it (on the Scripts page), and a Script row on the Browse page, the Create page
// and the Selected panel. Each of those is drawn after the page's own, so the pages don't need to know of it.

// A search box for picking something: types are the record kinds it may be
function scrPick(input, tags, onPick){
  const list = document.createElement('div');
  list.className = 'sc-picks';
  input.parentNode.insertBefore(list, input.nextSibling);
  let token = 0, rows = [], at = 0;
  const close = () => { list.style.display = 'none'; rows = []; };
  const draw = () => {
    list.innerHTML = rows.map((h, n) => `<div class="${n === at ? 'on' : ''}" data-n="${n}"><span>${esc(h.edid)}</span><small>${esc(h.tag)}${h.name ? ' · ' + esc(h.name) : ''}</small></div>`).join('') || '<div class="none">Nothing has that name.</div>';
    list.style.display = 'block';
  };
  const pick = h => { close(); input.value = h.edid; onPick(h); };
  input.addEventListener('input', async e => {
    e.stopPropagation();          // (it isn't a change to the record on the page around it)
    const q = input.value.trim(), my = ++token;
    if (q.length < 2) return close();
    try {
      const got = await scrGet(`/api/scripts/complete?q=${encodeURIComponent(q)}&tags=${tags.join(',')}`);
      if (my === token){ rows = got; at = 0; draw(); }
    } catch (err) {}
  });
  input.addEventListener('keydown', e => {
    e.stopPropagation();
    if (!rows.length) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp'){ e.preventDefault(); at = (at + (e.key === 'ArrowDown' ? 1 : rows.length - 1)) % rows.length; draw(); }
    else if (e.key === 'Enter'){ e.preventDefault(); pick(rows[at]); }
    else if (e.key === 'Escape') close();
  });
  input.addEventListener('blur', () => setTimeout(close, 150));
  list.addEventListener('mousedown', e => { e.preventDefault(); const r = e.target.closest('[data-n]'); if (r) pick(rows[+r.dataset.n]); });
}

// ---------- on the Scripts page: what runs this script, and putting it on something ----------
const SCR_RUN_TAGS = () => SCR.kind === 'quest' ? ['QUST'] : SCR.info.carriers.filter(t => t !== 'QUST');
async function scrRunDraw(){
  const box = $('#sc-p-run'), key = SCR.key; if (!box) return;
  if (!key){ box.innerHTML = ''; return; }
  const d = SCR.data;
  await scrLoadInfo();
  const who = await scrGet('/api/scripts/who?key=' + encodeURIComponent(key));
  if (key !== SCR.key) return;
  const empty = SCR.kind === 'effect'
    ? 'An effect script runs from a base effect: pick it in that effect\'s record. Nothing has this one yet.'
    : 'Nothing runs it yet, so it does nothing in the game. Put it on something below.';
  box.innerHTML = `<div class="h">What runs it · ${who.total}</div>
    ${who.busy ? '<div class="note">Still reading the game: the game\'s own users show in a moment.</div>' : ''}
    ${who.rows.map(r => `<div class="row" data-rec="${esc(r.key)}"><div>${r.mine ? '<span class="dot moved" title="by your mod"></span>' : ''}${esc(r.label)}</div><button class="btn" data-off="${esc(r.key)}" title="Take the script off it">✕</button></div>`).join('') || `<div class="note">${empty}</div>`}
    ${SCR.kind === 'effect' ? '' : `<div class="h">Put it on something</div>
    <div class="note" style="padding-top:0">${SCR.kind === 'quest' ? 'A quest.' : 'A door, an item, a container, a character… It runs on every one of that thing in the game.'}</div>
    <div class="sc-pickbox"><input id="sc-puton" placeholder="Search by editor ID…" autocomplete="off"></div>
    ${scrDirty() ? '<div class="note">Save your changes first if the script\'s kind has changed.</div>' : ''}`}`;
  box.querySelectorAll('[data-off]').forEach(b => b.onclick = async e => {
    e.stopPropagation();
    await scrAttachDo(b.dataset.off, '');
    scrRunDraw();
  });
  box.querySelectorAll('[data-rec]').forEach(r => r.onclick = () => openRecord(r.dataset.rec));
  const inp = $('#sc-puton');
  if (inp) scrPick(inp, SCR_RUN_TAGS(), async h => { await scrAttachDo(h.key, key); inp.value = ''; scrRunDraw(); });
  return d;
}
async function scrAttachDo(target, script){
  try {
    const r = await post('/api/scripts/attach', {target, script});
    setState(r.state);
    if (typeof recCacheDrop === 'function') recCacheDrop(target);
    toast(script ? 'The script is on it now.' : 'The script is off it.');
    return r;
  } catch (e){ fail(e); return null; }
}

// ---------- a Script row, for the pages that show one record ----------
// after(): the page draws the record again; busy(): the page has changes it must keep first
async function scrOnRow(box, key, after, busy){
  let d;
  try { d = await scrGet('/api/scripts/on?key=' + encodeURIComponent(key)); } catch (e){ return; }
  if (!d.can || !box.isConnected) return;
  const s = d.script;
  box.className = 'sc-onrow';
  box.innerHTML = `<label>Script</label><span class="sc-onval">${s ? `<a href="#" data-sopen="${esc(s.key)}" title="Open it on the Scripts page">${esc(s.edid)}</a> <button class="btn" data-soff title="This thing goes without a script">Take it off</button>` : '<i>none</i>'}
      <span class="sc-pickbox"><input placeholder="${s ? 'Another script…' : 'Put a script on it…'}" autocomplete="off"></span>
      <button class="btn" data-snew title="Write a new script for this">＋ New</button></span>`;
  const put = async script => {
    if (busy && busy()) return toast('Save your changes to this first.', true);
    if (await scrAttachDo(key, script)) after();
  };
  box.querySelector('[data-snew]').onclick = () => { if (busy && busy()) return toast('Save your changes to this first.', true); page('scripts'); scrNewForm({attachTo: key, needs: d.needs, type: d.type}); };
  const off = box.querySelector('[data-soff]');
  if (off) off.onclick = () => put('');
  const a = box.querySelector('[data-sopen]');
  if (a) a.onclick = e => { e.preventDefault(); e.stopPropagation(); scrOpen(a.dataset.sopen); };
  scrPick(box.querySelector('input'), ['SCPT'], h => put(h.key));
}
function scrOnHolder(where, place){
  const box = document.createElement('div');
  if (place === 'after') where.parentNode.insertBefore(box, where.nextSibling);
  else if (place === 'before') where.parentNode.insertBefore(box, where);
  else where.appendChild(box);
  return box;
}

// ---------- drawn after the pages' own (when every page's code has loaded) ----------
addEventListener('load', () => {
  if (typeof bwDraw === 'function'){
    const was = bwDraw;
    bwDraw = function (){
      was();
      const used = $('#bw-used');
      if (used && BW.data.record.type !== 'SCPT') scrOnRow(scrOnHolder(used, 'before'), BW.key, () => bwOpen(BW.key, true), () => BW.dirty);
    };
  }
  if (typeof crDraw === 'function'){
    const was = crDraw;
    crDraw = function (){
      was();
      const grid = $('#cr-detail .crgrid');
      if (grid) scrOnRow(scrOnHolder(grid, 'after'), CR.key, () => crOpen(CR.key), () => CR.dirty);
    };
  }
  if (typeof selRecord === 'function'){
    const was = selRecord;
    selRecord = async function (t){
      await was(t);
      const host = $('#sel-rec');
      if (host && t.bkey && A.sel.length === 1 && A.sel[0] === t.key) scrOnRow(scrOnHolder(host), t.bkey, () => selRecord(t));
    };
  }
});
