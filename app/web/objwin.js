// ---------- the object window (the Workshop's objwin.js) ----------
// Double-click something (or "Open its window" on its right-click menu) and a window opens over the view: the record
// on one side (ID, name, model, where it comes from) and the placed object on the other (where it stands, its turn
// and size, who owns it, its lock and key, where a door leads, what enables it). Save keeps the edits as one Undo
// step, Cancel drops them, Esc closes. It can be dragged by its title, and remembers where it was left.
const OW = {el: null, key: null, data: null, pos: null};
try { OW.pos = JSON.parse(sessionStorage.getItem('folab-ow-pos') || 'null'); } catch (e) {}

function owClose(){ if (!OW.el) return false; OW.el.remove(); OW.el = null; OW.key = null; return true; }

async function owOpen(key){
  const d = await api(`/api/ref?cell=${encodeURIComponent(A.cellId)}&key=${encodeURIComponent(key)}`);
  owClose();
  OW.key = key; OW.data = d;
  const t = d.thing, b = d.base, r = d.ref || {}, dg = v => Math.round(v * 180 / Math.PI * 100) / 100;
  // (a row only for what the thing has; text is escaped here, html passed in as {html})
  const kv = (k, v) => v === undefined || v === null || v === '' ? '' : `<div class="kv"><span>${k}</span> ${v.html !== undefined ? v.html : esc(v)}</div>`;
  const door = r.door;
  const el = OW.el = document.createElement('div');
  el.className = 'owin';
  el.innerHTML = `
    <div class="owtitle"><b>${esc(b.edid)}</b>${b.name ? ' — ' + esc(b.name) : ''}<button class="owx" title="Close (Esc)">✕</button></div>
    <div class="owbody">
      <div class="owcol"><div class="h">Record · ${esc(b.type)}</div>
        ${kv('Editor ID', b.edid)}${kv('Name', b.name)}${kv('Model', b.model)}${kv('From', b.from)}
        <div class="note">Editing the record itself comes with the Browse page.</div></div>
      <div class="owcol"><div class="h">Placed here · ${esc(t.key)}</div>
        <div class="fields">
          <label>Position</label><input data-i="0" value="${t.p[0].toFixed(1)}"><input data-i="1" value="${t.p[1].toFixed(1)}"><input data-i="2" value="${t.p[2].toFixed(1)}">
          <label>Turn °</label><input data-i="3" value="${dg(t.p[3])}"><input data-i="4" value="${dg(t.p[4])}"><input data-i="5" value="${dg(t.p[5])}">
          <label>Scale</label><input data-i="s" value="${(t.s || 1).toFixed(3)}"><span></span><span></span>
        </div>
        ${kv('Ref ID', r.edid)}${kv('Owner', r.owner)}${kv('Lock', r.lock)}${kv('Key', r.lock_key)}
        ${kv('Enabled by', r.enable_parent ? r.enable_parent + (r.enable_opposite ? ' (the opposite)' : '') : '')}
        ${kv('Linked to', r.linked)}${kv('Count', r.count)}
        ${door ? kv('Leads to', {html: `${esc(door.cell_name || door.cell_edid || 'somewhere not loaded')} <a href="#" data-a="go">Go there</a>`}) : ''}
        ${kv('Comes from', r.from || 'your mod')}${r.persistent ? kv('Persistent', 'yes') : ''}${r.disabled ? kv('Starts disabled', 'yes') : ''}
      </div>
    </div>
    <div class="owfoot"><button class="btn primary" data-a="save">Save</button><button class="btn" data-a="cancel">Cancel</button></div>`;
  document.body.appendChild(el);
  const r0 = el.getBoundingClientRect();
  const p = OW.pos || {x: innerWidth - r0.width - 330, y: 120};
  el.style.left = Math.max(8, Math.min(p.x, innerWidth - r0.width - 8)) + 'px';
  el.style.top = Math.max(8, Math.min(p.y, innerHeight - r0.height - 8)) + 'px';
  el.querySelector('.owx').onclick = owClose;
  el.addEventListener('click', ev => {
    const a = ev.target.dataset.a; if (!a) return;
    ev.preventDefault();
    if (a === 'cancel') owClose();
    else if (a === 'save') owSave();
    else if (a === 'go'){ const th = W.byKey.get(OW.key); owClose(); if (th) goThroughDoor(th.userData.thing); }
  });
  el.addEventListener('keydown', ev => { if (ev.key === 'Escape') owClose(); if (ev.key === 'Enter' && ev.target.tagName === 'INPUT') owSave(); ev.stopPropagation(); });
  // drag by the title
  const title = el.querySelector('.owtitle');
  title.addEventListener('pointerdown', ev => {
    if (ev.target.closest('button')) return;
    const sx = ev.clientX - el.offsetLeft, sy = ev.clientY - el.offsetTop;
    const mv = m => { el.style.left = (m.clientX - sx) + 'px'; el.style.top = (m.clientY - sy) + 'px'; };
    const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up);
      OW.pos = {x: el.offsetLeft, y: el.offsetTop}; try { sessionStorage.setItem('folab-ow-pos', JSON.stringify(OW.pos)); } catch (e) {} };
    addEventListener('pointermove', mv); addEventListener('pointerup', up);
  });
}

function owSave(){
  if (!OW.el) return;
  const t = OW.data.thing, p = t.p.slice();
  let s;
  for (const inp of OW.el.querySelectorAll('input[data-i]')){
    const v = parseFloat(inp.value), i = inp.dataset.i;
    if (isNaN(v)) return toast('That isn\'t a number: ' + inp.value, true);
    if (i === 's') s = Math.max(0.01, Math.min(10, v));
    else p[+i] = +i >= 3 ? v * Math.PI / 180 : v;
  }
  const same = p.every((v, i) => Math.abs(v - t.p[i]) < 1e-4) && Math.abs((s || 1) - (t.s || 1)) < 1e-6;
  owClose();
  if (!same) sendMoves([[t, p.map(v => Math.round(v * 10000) / 10000), s]], 'Edit in its window');
}

W.onOpen = key => owOpen(key);
