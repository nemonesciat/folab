// ---------- the Kit tab: other places in one click, one room at a time, and a floor plan drawn by hand ----------
// Adds to the tab from its own file, wrapping kitTab: kits.js only draws the sections it always did.
const KR = {plan: null, room: null, rows: null, purposes: null, drawing: {rooms: [], links: []}, picked: null, dragging: null, what: 'tunnels', size: 4, level: 0, cols: 26, rowsN: 20};
const KR_CELL = 12;

function krPut(made){
  if (made && made.plan) KR.plan = made.plan;
  return made;
}

// (every way of making a place ends in kitPut: its answer's plan is what this tab shows)
{ const was = kitPut; kitPut = async (made, label, replace) => { krPut(made); return was(made, label, replace); }; }
{ const was = kitTab; kitTab = async (...a) => { const r = await was(...a); krDraw(); return r; }; }

function krDraw(){
  const nav = document.querySelector('#tab-kit #nav-box');
  if (!nav || document.querySelector('#kr-box')) return;
  const head = nav.previousElementSibling, box = document.createElement('div');
  box.id = 'kr-box';
  head.parentNode.insertBefore(box, head);
  box.innerHTML = `<div class="h" style="margin-top:10px">Other places in one click</div>
    <div class="note" style="padding:0 0 6px">Planned for what the kit is good at, from the game's own pieces, walked before you see it.</div>
    <label class="vt-row">Kind <select id="kr-what"></select></label>
    <label class="vt-row">Size <input type="range" id="kr-size" min="1" max="10" value="${KR.size}" style="flex:1"> <span id="kr-size-n">${KR.size}</span></label>
    <div class="kit-go"><button class="btn" id="kr-click">Make it</button></div>
    <div class="h" style="margin-top:10px">This place, one room at a time</div>
    <div id="kr-rooms"></div>
    <div class="h" style="margin-top:10px">Draw a floor plan</div>
    <div class="note" style="padding:0 0 6px">Drag on the grid for a room. Drag from one room to another to link them: a door if they touch, a corridor if not, with stairs if they're on different levels. The first room is where you come in. Click a room to pick it.</div>
    <canvas id="kr-canvas" width="${KR.cols * KR_CELL}" height="${KR.rowsN * KR_CELL}" style="display:block;background:var(--bg2,#0a120c);border:1px solid var(--line,#274);cursor:crosshair;max-width:100%"></canvas>
    <label class="vt-row" style="margin-top:6px">New rooms on level <input type="number" id="kr-level" min="-4" max="4" value="${KR.level}" style="width:50px"></label>
    <div id="kr-pick-box"></div>
    <div class="kit-go"><button class="btn primary" id="kr-build">Build this plan</button> <button class="btn" id="kr-clear">Clear</button></div>`;
  api('/api/kits').then(() => post('/api/kit/oneclicks', {})).then(d => {
    const sel = box.querySelector('#kr-what');
    sel.innerHTML = (d.kinds || []).map(k => `<option value="${esc(k.id)}" ${k.id === KR.what ? 'selected' : ''}>${esc(k.label)}</option>`).join('');
  }).catch(() => {});
  box.querySelector('#kr-what').onchange = e => { KR.what = e.target.value; };
  box.querySelector('#kr-size').oninput = e => { KR.size = +e.target.value; box.querySelector('#kr-size-n').textContent = e.target.value; };
  box.querySelector('#kr-click').onclick = krMake;
  box.querySelector('#kr-level').onchange = e => { KR.level = +e.target.value || 0; };
  box.querySelector('#kr-build').onclick = krBuild;
  box.querySelector('#kr-clear').onclick = () => { KR.drawing = {rooms: [], links: []}; KR.picked = null; krPaint(); krPickBox(); };
  krCanvas(box.querySelector('#kr-canvas'));
  krPaint();
  krPickBox();
  krRooms();
}

async function krMake(){
  if (!A.cellId || A.outside) return toast('Open a place first.', true);
  KIT.seed = (KIT.seed || 0) + 1;
  $('#kit-said').textContent = 'Building…';
  const made = await post('/api/kit/click', {what: KR.what, size: KR.size, seed: KIT.seed + (Date.now() % 100000), at: kitSpot()}).catch(e => { fail(e); return null; });
  await kitPut(made, 'Make ' + (($('#kr-what').selectedOptions[0] || {}).textContent || 'a place'), true);
}

// ---------- one room at a time ----------
function krRooms(){
  const box = $('#kr-rooms'); if (!box) return;
  const P = KR.plan;
  if (!P){ box.innerHTML = '<div class="note" style="padding:0">Generate a place, and its rooms are listed here: choose what one is for, which real place it copies, or re-roll it without touching the rest.</div>'; return; }
  box.innerHTML = `<div class="note" style="padding:0 0 4px">${P.rooms.length} rooms${P.loops ? `, ${P.loops} way${P.loops > 1 ? 's' : ''} round` : ''}${P.flights.length ? `, ${P.flights.length} flight${P.flights.length > 1 ? 's' : ''} of stairs` : ''}.</div>
    <select id="kr-room" size="${Math.min(7, P.rooms.length)}" style="width:100%">${P.rooms.map(r => `<option value="${r.n}" ${KR.room === r.n ? 'selected' : ''}>${esc(r.purpose)}${r.tall ? ' (two storeys)' : r.whole ? ' (one piece)' : ''}, ${r.squares} squares${r.levels.length ? ', level ' + r.levels.join(' and ') : ''}</option>`).join('')}</select>
    <div id="kr-room-box"></div>`;
  box.querySelector('#kr-room').onchange = e => { KR.room = +e.target.value; krRoomBox(); };
  if (KR.room !== null) krRoomBox();
}

async function krRoomBox(){
  const box = $('#kr-room-box'); if (!box || KR.room === null) return;
  const P = KR.plan, r = P.rooms.find(x => x.n === KR.room); if (!r) return;
  const d = await post('/api/kit/themes', {n: r.n}).catch(() => null);
  if (!d || KR.room !== r.n) return;
  box.innerHTML = `<label class="vt-row" style="margin-top:6px">For <select id="kr-purpose">${(d.purposes || []).concat(d.purposes && d.purposes.includes(r.purpose) ? [] : [r.purpose]).map(p => `<option ${p === r.purpose ? 'selected' : ''}>${esc(p)}</option>`).join('')}</select></label>
    <label class="vt-row">Copies <select id="kr-theme">${(d.rows || []).map(t => `<option value="${esc(t.cell)}" ${t.cell === d.theme ? 'selected' : ''}>${esc(t.name)}</option>`).join('')}</select></label>
    <div class="kit-go"><button class="btn" id="kr-reroll" ${r.fixed ? 'disabled title="This room is built whole"' : ''}>Re-roll this room</button></div>`;
  box.querySelector('#kr-purpose').onchange = e => krChange({purpose: e.target.value});
  box.querySelector('#kr-theme').onchange = e => krChange({theme: e.target.value});
  box.querySelector('#kr-reroll').onclick = () => krChange({reroll: true});
}

async function krChange(what){
  if (!A.cellId || A.outside) return toast('Open the place first.', true);
  KIT.seed = (KIT.seed || 0) + 1;
  $('#kit-said').textContent = 'Changing the room…';
  const made = await post('/api/kit/room', {n: KR.room, seed: KIT.seed + (Date.now() % 100000), ...what}).catch(e => { fail(e); return null; });
  await kitPut(made, 'Change a room', true);
}

// ---------- a floor plan drawn by hand ----------
function krAt(c, e){
  const r = c.getBoundingClientRect(), f = c.width / r.width;
  return [Math.floor((e.clientX - r.left) * f / KR_CELL), KR.rowsN - 1 - Math.floor((e.clientY - r.top) * f / KR_CELL)];
}

function krRoomAt(x, y){
  const rooms = KR.drawing.rooms;
  for (let i = rooms.length - 1; i >= 0; i--){
    const r = rooms[i];
    if (x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h) return i;
  }
  return -1;
}

function krCanvas(c){
  c.onpointerdown = e => {
    const [x, y] = krAt(c, e), i = krRoomAt(x, y);
    KR.dragging = {from: [x, y], to: [x, y], room: i};
    c.setPointerCapture(e.pointerId);
  };
  c.onpointermove = e => {
    if (!KR.dragging) return;
    KR.dragging.to = krAt(c, e);
    krPaint();
  };
  c.onpointerup = () => {
    const d = KR.dragging; KR.dragging = null;
    if (!d) return;
    const [x0, y0] = d.from, [x1, y1] = d.to;
    if (d.room >= 0){
      const j = krRoomAt(x1, y1);
      if (j === d.room) KR.picked = j;
      else if (j >= 0){
        const has = KR.drawing.links.findIndex(l => (l[0] === d.room && l[1] === j) || (l[0] === j && l[1] === d.room));
        if (has >= 0) KR.drawing.links.splice(has, 1); else KR.drawing.links.push([d.room, j]);
      }
    } else {
      const r = {x: Math.min(x0, x1), y: Math.min(y0, y1), w: Math.abs(x1 - x0) + 1, h: Math.abs(y1 - y0) + 1, level: KR.level, purpose: KR.drawing.rooms.length ? 'workroom' : 'entrance'};
      if (r.w >= 2 && r.h >= 2 && !KR.drawing.rooms.some(o => o.level === r.level && o.x < r.x + r.w && r.x < o.x + o.w && o.y < r.y + r.h && r.y < o.y + o.h)){
        KR.drawing.rooms.push(r);
        KR.picked = KR.drawing.rooms.length - 1;
      }
    }
    krPaint(); krPickBox();
  };
}

function krPaint(){
  const c = $('#kr-canvas'); if (!c) return;
  const g = c.getContext('2d'), n = KR_CELL, H = KR.rowsN;
  const css = getComputedStyle(document.documentElement), ink = css.getPropertyValue('--ink').trim() || '#8affac', dim = css.getPropertyValue('--line').trim() || '#274';
  g.clearRect(0, 0, c.width, c.height);
  g.strokeStyle = dim; g.globalAlpha = 0.35; g.lineWidth = 1;
  for (let i = 0; i <= KR.cols; i++){ g.beginPath(); g.moveTo(i * n + 0.5, 0); g.lineTo(i * n + 0.5, c.height); g.stroke(); }
  for (let j = 0; j <= H; j++){ g.beginPath(); g.moveTo(0, j * n + 0.5); g.lineTo(c.width, j * n + 0.5); g.stroke(); }
  g.globalAlpha = 1;
  const mid = r => [(r.x + r.w / 2) * n, (H - r.y - r.h / 2) * n];
  KR.drawing.rooms.forEach((r, i) => {
    const same = r.level === KR.level;
    g.globalAlpha = same ? 0.32 : 0.12;
    g.fillStyle = i === KR.picked ? '#ffd27a' : ink;
    g.fillRect(r.x * n + 1, (H - r.y - r.h) * n + 1, r.w * n - 2, r.h * n - 2);
    g.globalAlpha = same ? 1 : 0.4;
    g.strokeStyle = i === KR.picked ? '#ffd27a' : ink;
    g.strokeRect(r.x * n + 1.5, (H - r.y - r.h) * n + 1.5, r.w * n - 3, r.h * n - 3);
    g.fillStyle = ink; g.font = '10px monospace'; g.textAlign = 'center';
    g.fillText(String(i + 1) + (r.level ? ` L${r.level}` : ''), mid(r)[0], mid(r)[1] + 3);
    g.globalAlpha = 1;
  });
  g.strokeStyle = '#ffd27a'; g.lineWidth = 2;
  for (const [a, b] of KR.drawing.links){
    const p = mid(KR.drawing.rooms[a]), q = mid(KR.drawing.rooms[b]);
    g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(q[0], q[1]); g.stroke();
  }
  const d = KR.dragging;
  if (d){
    g.strokeStyle = '#ffd27a'; g.lineWidth = 1;
    if (d.room >= 0){
      const p = mid(KR.drawing.rooms[d.room]);
      g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo((d.to[0] + 0.5) * n, (H - d.to[1] - 0.5) * n); g.stroke();
    } else {
      const x = Math.min(d.from[0], d.to[0]), y = Math.min(d.from[1], d.to[1]), w = Math.abs(d.from[0] - d.to[0]) + 1, h = Math.abs(d.from[1] - d.to[1]) + 1;
      g.strokeRect(x * n + 0.5, (H - y - h) * n + 0.5, w * n, h * n);
    }
  }
  g.lineWidth = 1;
}

async function krPickBox(){
  const box = $('#kr-pick-box'); if (!box) return;
  const r = KR.drawing.rooms[KR.picked];
  if (!r){ box.innerHTML = ''; return; }
  if (!KR.purposes){
    const d = await post('/api/kit/oneclicks', {}).catch(() => null);
    KR.purposes = d ? d.purposes : ['workroom'];
    if (KR.drawing.rooms[KR.picked] !== r) return;
  }
  box.innerHTML = `<label class="vt-row">Room ${KR.picked + 1} is for <select id="kr-pick-for">${KR.purposes.map(p => `<option ${p === r.purpose ? 'selected' : ''}>${esc(p)}</option>`).join('')}</select></label>
    <label class="vt-row">On level <input type="number" id="kr-pick-level" min="-4" max="4" value="${r.level}" style="width:50px"> <button class="btn" id="kr-pick-del" style="margin-left:auto">Take it away</button></label>`;
  box.querySelector('#kr-pick-for').onchange = e => { r.purpose = e.target.value; };
  box.querySelector('#kr-pick-level').onchange = e => { r.level = +e.target.value || 0; krPaint(); };
  box.querySelector('#kr-pick-del').onclick = () => {
    const i = KR.picked;
    KR.drawing.rooms.splice(i, 1);
    KR.drawing.links = KR.drawing.links.filter(l => l[0] !== i && l[1] !== i).map(l => l.map(x => x > i ? x - 1 : x));
    KR.picked = null; krPaint(); krPickBox();
  };
}

async function krBuild(){
  if (!A.cellId || A.outside) return toast('Open a place first.', true);
  if (!KR.drawing.rooms.length) return toast('Draw a room first: drag on the grid.', true);
  const kit = $('#kit-pick').value;
  KIT.seed = (KIT.seed || 0) + 1;
  $('#kit-said').textContent = 'Building your plan…';
  const made = await post('/api/kit/drawn', {kit, rooms: KR.drawing.rooms, links: KR.drawing.links, seed: KIT.seed + (Date.now() % 100000), at: kitSpot()}).catch(e => { fail(e); return null; });
  await kitPut(made, 'Build a drawn plan', true);
}
