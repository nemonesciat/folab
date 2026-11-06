// ---------- Characters: people and creatures in plain fields, their AI packages, factions, and Populate ----------
// Kinds on the left, the ones of that kind in the middle (yours first), one on the right as tabs over the same records
// Browse edits (the mod keeps them through /api/record/save). The inventory is the Create page's own editor; the 3D
// preview is its renderer. Page set up from here: a new page needs nothing in index.html but this script.
const CH = {kind: 'NPC_', rows: [], key: null, data: null, rec: null, dirty: false, tab: 'who', opts: null, tpl: null, ranks: {}, pop: {who: 'all', busy: 'usual', difficulty: 'auto', seed: 1, live: true, levelled: false}};

const CH_KINDS = [['NPC_', 'Characters'], ['CREA', 'Creatures'], ['PACK', 'AI packages'], ['FACT', 'Factions'],
                  ['-', 'Levelled lists'], ['@LVLN', 'Character lists'], ['@LVLC', 'Creature lists'],
                  ['-', 'Tools'], ['POP', 'Populate a place']];
const CH_SPECIAL = ['Strength', 'Perception', 'Endurance', 'Charisma', 'Intelligence', 'Agility', 'Luck'];
const CH_SKILLS = ['Barter', 'Energy Weapons', 'Explosives', 'Guns', 'Lockpick', 'Medicine', 'Melee Weapons', 'Repair', 'Science', 'Sneak', 'Speech', 'Survival', 'Unarmed'];
const CH_AGG = ['Unaggressive: never starts a fight', 'Aggressive: attacks enemies on sight', 'Very aggressive: attacks enemies and neutrals', 'Frenzied: attacks everyone'];
const CH_CONF = ['Cowardly: flees at once', 'Cautious', 'Average', 'Brave', 'Foolhardy: never flees'];
const CH_MOOD = ['Neutral', 'Afraid', 'Annoyed', 'Cocky', 'Drugged', 'Pleasant', 'Angry', 'Sad'];
const CH_ASSIST = ['Helps nobody', 'Helps allies', 'Helps friends and allies'];
const CH_CREATYPE = ['Animal', 'Mutated animal', 'Mutated insect', 'Abomination', 'Super mutant', 'Feral ghoul', 'Robot', 'Giant'];
const CH_TFLAGS = [[1, 'Traits', 'Race, sex, face, voice, height'], [2, 'Stats', 'S.P.E.C.I.A.L., skills, health, level'], [4, 'Factions', ''], [8, 'Abilities', ''],
                   [16, 'AI', 'Aggression, confidence, mood…'], [32, 'AI packages', ''], [64, 'Model and animation', ''], [128, 'Name and base data', ''], [256, 'Inventory', ''], [512, 'Script', '']];
const CH_NPCFLAGS = [[2, 'Essential', 'Falls unconscious instead of dying'], [8, 'Comes back after a while', 'Respawns'], [16, 'Stats worked out from class and level', 'S.P.E.C.I.A.L. and skills below are then ignored'],
                     [0x800000, 'Services worked out from class', ''], [0x200, 'Stops when you\'re far away', 'No low-level processing: does nothing unless near'], [0x4000000, 'Can\'t be knocked down', '']];
const CH_CREAFLAGS = [[2, 'Essential', ''], [8, 'Comes back after a while', 'Respawns'], [0x40, 'Walks', ''], [0x10, 'Swims', ''], [0x20, 'Flies', ''], [1, 'Stands on two legs', 'Biped'],
                      [0x200, 'Stops when you\'re far away', ''], [0x200000, 'Can be talked to', ''], [0x400000, 'Can\'t open doors', ''], [0x4000000, 'Can\'t be knocked down', ''], [0x80000000, 'Can\'t be hurt', '']];
const CH_PKTYPES = {0: 'Find', 1: 'Follow', 2: 'Escort', 3: 'Eat', 4: 'Sleep', 5: 'Wander', 6: 'Travel', 7: 'Accompany', 8: 'Use item', 9: 'Ambush', 10: 'Flee', 12: 'Sandbox', 13: 'Patrol', 14: 'Guard', 15: 'Talk', 16: 'Use weapon'};
const CH_PKFLAGS = [[0x2, 'Must reach the place', ''], [0x4, 'Must finish', ''], [0x400, 'Once a day', ''], [0x2000, 'Always runs', ''], [0x20000, 'Always sneaks', ''], [0x40000, 'May swim', ''],
                    [0x100000, 'No armour on', ''], [0x200000, 'Weapon put away', ''], [0x800000, 'Weapon out', ''], [0x1000, 'No fallout behaviour', 'Doesn\'t use the game\'s everyday animations'], [0x4000000, 'Carries on in a fight', ''], [0x2000000, 'Acts as if in a fight', '']];
const CH_SANDBOX = [[1, 'Eat'], [2, 'Sleep'], [4, 'Chat with others'], [8, 'Use idle markers'], [16, 'Use furniture'], [32, 'Wander']];
const CH_PLACE = {0: 'Near a thing placed in the world', 1: 'In a place', 2: 'Near where they are', 3: 'Near where they were placed', 6: 'Near their linked ref', 7: 'At the package\'s first location'};
const CH_TARGET = {0: 'A thing placed in the world', 1: 'A kind of thing', 2: 'Any of a type (number)', 3: 'Their linked ref'};
const CH_DAYS = ['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays'];
const CH_REACT = ['Neutral', 'Enemy', 'Ally', 'Friend'];
const CH_DIFF = ['Easy', 'Medium', 'Hard', 'Very hard'];

// ---------- the page ----------
(() => {
  const nav = document.createElement('button');
  nav.id = 'nav-characters'; nav.title = 'People and creatures: stats, what they wear, how they behave. AI packages, factions, and filling a place with them';
  nav.innerHTML = '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/></svg>Characters';
  $('#nav-create').after(nav);
  const main = document.createElement('main');
  main.id = 'page-characters'; main.style.display = 'none';
  main.innerHTML = `<div class="side" id="ch-side"><div class="h">Kinds</div><div class="list" id="ch-kinds"></div></div>
    <div class="side" id="ch-mid"><input class="find" id="ch-find" placeholder="Search names and editor IDs…"><div class="acts" id="ch-new"></div><div class="list" id="ch-rows"></div></div>
    <div id="ch-detail"><div class="note" style="padding:24px">Pick someone, or start a new one of your own.</div></div>`;
  $('#page-create').after(main);
  const css = document.createElement('style');
  css.textContent = `#ch-side{width:190px;border-right:1px solid var(--line)}#ch-mid{width:290px;border-right:1px solid var(--line)}
    #ch-detail{flex:1;overflow-y:auto;padding:14px 22px 40px;min-width:0}
    .ch-tabs{display:flex;gap:2px;border-bottom:1px solid var(--line);margin:8px 0 10px;max-width:980px}.ch-tabs button{background:none;border:none;border-bottom:2px solid transparent;padding:6px 12px;color:var(--muted);cursor:pointer}
    .ch-tabs button.on{color:var(--gold2);border-bottom-color:var(--gold)}
    .ch-body{display:flex;gap:22px;align-items:flex-start;max-width:980px}.ch-form{flex:1;min-width:0}.ch-side{width:280px;flex:none;position:sticky;top:0}
    #ch-view{width:280px;height:360px;background:var(--bg2);border:1px solid var(--line);border-radius:8px}
    .ch-grid{display:grid;grid-template-columns:190px 1fr;gap:6px 12px;align-items:center}.ch-grid>label{color:var(--muted);font-size:13px}.ch-grid input:not([type=checkbox]):not([type=color]),.ch-grid select{width:100%;max-width:300px}
    .ch-grid small{color:var(--faint);font-size:12px;display:block}.ch-nums{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:6px 10px}.ch-nums label{display:flex;flex-direction:column;color:var(--muted);font-size:12.5px;gap:2px}.ch-nums input{width:100%}
    .ch-flags{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:3px 10px;color:var(--muted);font-size:13px;margin:4px 0}
    .ch-warn{border:1px solid #7a6230;background:color-mix(in srgb,var(--amber) 9%,transparent);color:var(--text);border-radius:7px;padding:7px 10px;font-size:12.5px;margin:8px 0}
    .ch-worn{font-size:12.5px;color:var(--muted);padding:6px 2px}.ch-worn b{color:var(--text);font-weight:500}
    #ch-detail table{border-collapse:collapse}#ch-detail td,#ch-detail th{padding:2px 8px 2px 0;font-size:13px;text-align:left}#ch-detail th{color:var(--muted);font-weight:500}
    .ch-tpl{padding:7px 10px;border:1px solid var(--line);border-radius:7px;margin:4px 0;cursor:pointer;max-width:520px}.ch-tpl:hover{border-color:var(--gold)}.ch-tpl small{display:block;color:var(--faint)}
    .ch-off{opacity:.55}`;
  document.head.appendChild(css);
  PAGES.push('characters');
  nav.onclick = () => page('characters');
  const was = onPage;
  onPage = name => { was(name); if (name === 'characters') chInit(); };
  $('#ch-kinds').addEventListener('click', e => {
    const r = e.target.closest('.row'); if (!r) return;
    const t = r.dataset.t;
    if (t.startsWith('@')){ CR.kind = t.slice(1); page('create'); return; }   // (the Create page keeps levelled lists)
    if (!chLeave()) return;
    CH.kind = t; CH.key = null; CH.data = CH.rec = null;
    if (t !== 'POP') $('#ch-detail').innerHTML = '';
    chInit();
  });
  let timer;
  $('#ch-find').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(chList, 200); });
  $('#ch-rows').addEventListener('click', e => { const r = e.target.closest('.row[data-k]'); if (r) chOpen(r.dataset.k); });
  $('#ch-new').addEventListener('click', e => { const a = e.target.dataset.a; if (a) chNew(); });
  $('#ch-detail').addEventListener('input', chField);
  $('#ch-detail').addEventListener('change', chField);
  $('#ch-detail').addEventListener('click', chClick);
  const again = () => setTimeout(() => { if ($('#page-characters').style.display !== 'none'){ chList(); if (CH.key) { CH.dirty = false; chOpen(CH.key).catch(() => { CH.key = null; $('#ch-detail').innerHTML = ''; }); } } }, 250);
  $('#b-undo').addEventListener('click', again); $('#b-redo').addEventListener('click', again);
})();

function chLeave(){ if (CH.dirty && !confirm('Leave without saving your changes?')) return false; CH.dirty = false; return true; }

async function chInit(){
  $('#ch-kinds').innerHTML = CH_KINDS.map(([t, l]) => t === '-' ? `<div class="h">${l}</div>` : `<div class="row${t === CH.kind ? ' on' : ''}" data-t="${t}"><div>${l}</div></div>`).join('');
  const pop = CH.kind === 'POP';
  $('#ch-mid').style.display = pop ? 'none' : '';
  $('#ch-new').innerHTML = pop ? '' : `<button class="btn primary" data-a="new">＋ New ${{NPC_: 'character', CREA: 'creature', PACK: 'package', FACT: 'faction'}[CH.kind]}</button>`;
  if (!CH.opts){ try { CH.opts = await api('/api/char/options'); CH.tpl = await api('/api/char/templates'); } catch (e){ return fail(e); } }
  if (pop) return chPopulate();     // (each time: the place is whatever's open on the World page now)
  chList();
}

async function chList(){
  const token = CH.token = (CH.token || 0) + 1;
  const rows = await api(`/api/records?type=${CH.kind}&q=${encodeURIComponent($('#ch-find').value)}`);
  if (token !== CH.token) return;
  CH.rows = rows;
  const mine = rows.filter(r => r.state);
  const row = r => `<div class="row${r.key === CH.key ? ' on' : ''}" data-k="${esc(r.key)}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}" title="${r.state === 'new' ? 'your own' : 'changed by your mod'}"></span>` : ''}${esc(r.name || r.edid)}<small>${esc(r.edid)}</small></div></div>`;
  $('#ch-rows').innerHTML = (mine.length ? '<div class="h">Yours</div>' + mine.map(row).join('') + '<div class="h">The game\'s</div>' : '') +
    rows.filter(r => !r.state).map(row).join('');
}

async function chOpen(key, keepTab){
  if (CH.dirty && key !== CH.key && !chLeave()) return;
  const tok = CH.openTok = (CH.openTok || 0) + 1, before = CH.editN = CH.editN || 0;
  const d = await api('/api/char/info?key=' + encodeURIComponent(key));
  if (tok !== CH.openTok || (keepTab && CH.editN !== before)) return;      // (something newer asked for, or edits made while this came)
  CH.key = key; CH.data = d; CH.rec = JSON.parse(JSON.stringify(d.record)); CH.dirty = false;
  if (!keepTab) CH.tab = d.record.type === 'FACT' || d.record.type === 'PACK' ? 'main' : 'who';
  document.querySelectorAll('#ch-rows .row').forEach(r => r.classList.toggle('on', r.dataset.k === key));
  chDraw();
}

// ---------- reading and writing a record's fields ----------
const chSub = tag => CH.rec.subs.find(s => s.tag === tag);
const chSubs = tag => CH.rec.subs.filter(s => s.tag === tag);
function chVal(tag, name){
  const s = chSub(tag); if (!s) return undefined;
  if (!name) return s.value;
  const f = (s.fields || []).find(f => f.name === name);
  return f ? f.value : undefined;
}
function chPut(tag, name, v){ const s = chSub(tag); if (!s) return; if (!name) s.value = v; else { const f = s.fields.find(f => f.name === name); if (f) f.value = v; } }
function chInsert(sub){
  // (where the game's records have it: after the last of what comes before it)
  const order = CH.opts.order[CH.rec.type] || [];
  const at = order.includes(sub.tag) ? order.indexOf(sub.tag) : order.length;
  let n = 0;
  CH.rec.subs.forEach((s, k) => { const o = order.indexOf(s.tag); if (o >= 0 && o <= at) n = k + 1; });
  CH.rec.subs.splice(n, 0, sub);
  return sub;
}
function chDirty(){ CH.dirty = true; CH.editN = (CH.editN || 0) + 1; const b = $('#ch-detail [data-a="save"]'); if (b) b.disabled = false; }
const CH_RANGE = {b: [-128, 127], B: [0, 255], h: [-32768, 32767], H: [0, 65535], i: [-2147483648, 2147483647], I: [0, 4294967295]};
function chField(e){
  const i = e.target;
  if (i.dataset.f && (e.type === 'input' || i.tagName === 'SELECT' || i.type === 'checkbox')){
    const [tag, name] = i.dataset.f.split('|');
    const s = chSub(tag), f = s && name ? s.fields.find(f => f.name === name) : null;
    if (i.dataset.bit){
      const bit = +i.dataset.bit, cur = chVal(tag, name) >>> 0;
      chPut(tag, name, (i.checked !== !!i.dataset.inv ? cur | bit : cur & ~bit) >>> 0);
    } else if (f && f.code !== 'F' && f.code !== 'z'){
      const v = f.code === 'f' ? parseFloat(i.value) : parseInt(i.value, 10);
      i.style.borderColor = isNaN(v) ? 'var(--red)' : '';
      if (isNaN(v)) return;
      const r = CH_RANGE[f.code];
      f.value = r ? Math.max(r[0], Math.min(r[1], v)) : v;
    } else chPut(tag, name, i.value);
    chDirty();
    if (i.dataset.redraw) chDraw();
    return;
  }
  if (i.dataset.link && e.type === 'change') return chLinkField(i);
  if (i.dataset.linkfind && e.type === 'input') return chLinkFind(i);
  if (i.dataset.sel !== undefined && e.type === 'change'){    // a link chosen from a list: '' takes the subrecord out
    const tag = i.dataset.sel, label = i.dataset.label;
    if (!i.value){ CH.rec.subs = CH.rec.subs.filter(s => s.tag !== tag); }
    else if (chSub(tag)) chSub(tag).value = i.value;
    else chInsert({tag, label, kind: 'F', value: i.value});
    CH.data.links[i.value] = i.selectedOptions[0].textContent;
    chDirty();
    if (i.dataset.redraw) chDraw();
    return;
  }
  if (i.dataset.xnum && (e.type === 'input')) return;     // (read when saving)
  if (e.type === 'input' && !i.dataset.f && i.closest('[data-table]')) chDirty();
  if (i.dataset.rankof !== undefined && e.type === 'change'){
    const s = chSubs('SNAM')[+i.dataset.rankof];
    s.fields.find(f => f.name === 'Rank').value = +i.value; chDirty();
  }
  if (i.dataset.nam && e.type === 'input'){
    const s = CH.rec.subs[+i.dataset.nam]; const f = s.fields.find(f => f.name === i.dataset.name);
    const v = f.code === 'f' ? parseFloat(i.value) : parseInt(i.value, 10);
    if (!isNaN(v)){ f.value = v; chDirty(); }
  }
  if (i.dataset.zat && e.type === 'input'){ CH.rec.subs[+i.dataset.zat].value = i.value; chDirty(); }
  if (i.dataset.opt && e.type === 'change'){ CH.pop[i.dataset.opt] = i.type === 'checkbox' ? i.checked : i.value; }
}

// fields of a form
function chNum(tag, name, label, note, attrs){
  const v = chVal(tag, name); if (v === undefined) return '';
  const code = (chSub(tag).fields.find(f => f.name === name) || {}).code;
  return `<label>${esc(label)}<input data-f="${tag}|${esc(name)}" value="${esc(code === 'f' ? +(+v).toPrecision(6) : v)}" ${attrs || ''} title="${esc(note || '')}"></label>`;
}
function chRow(label, html, note){ return `<label>${esc(label)}</label><span>${html}${note ? `<small>${esc(note)}</small>` : ''}</span>`; }
function chText(tag, label, note){ const v = chVal(tag); return v === undefined ? '' : chRow(label, `<input data-f="${tag}" value="${esc(v)}">`, note); }
function chPick(tag, name, label, list, note, attrs){
  const v = chVal(tag, name); if (v === undefined) return '';
  return chRow(label, `<select data-f="${tag}|${esc(name)}" ${attrs || ''}>${list.map((l, n) => `<option value="${n}" ${n === v ? 'selected' : ''}>${esc(l)}</option>`).join('')}${v >= list.length ? `<option selected value="${v}">${v}</option>` : ''}</select>`, note);
}
function chFlags(tag, name, list, inv){
  const v = chVal(tag, name) >>> 0;
  return `<div class="ch-flags">${list.map(([b, l, tip]) => `<label title="${esc(tip || '')}"><input type="checkbox" data-f="${tag}|${esc(name)}" data-bit="${b}" ${inv ? 'data-inv="1"' : ''} ${(!!(v & b) !== !!inv) ? 'checked' : ''}> ${esc(l)}</label>`).join('')}</div>`;
}
const chOptName = x => x.name ? `${x.name} (${x.edid})` : x.edid;
function chSelect(tag, label, list, none, note, redraw, only){
  const v = chVal(tag) || '';
  const shown = only ? list.filter(x => only.includes(x.key) || x.key === v) : list;
  const has = shown.some(x => x.key === v);
  return chRow(label, `<select data-sel="${tag}" data-label="${esc(label)}" ${redraw ? 'data-redraw="1"' : ''}>${none ? `<option value="">${esc(none)}</option>` : ''}${!has && v ? `<option value="${esc(v)}" selected>${esc(CH.data.links[v] || v)}</option>` : ''}${shown.map(x => `<option value="${esc(x.key)}" ${x.key === v ? 'selected' : ''}>${esc(chOptName(x))}</option>`).join('')}</select>`, note);
}
// a link typed by editor ID, with suggestions from the records of the kinds given (data-link: tag|name, or data-link-at: a subrecord's index)
function chLink(where, value, type, width){
  const id = 'ch-dl-' + (CH.dlN = (CH.dlN || 0) + 1);
  return `<input data-link="${esc(where)}" data-linkfind="1" data-type="${type}" data-key="${esc(value || '')}" value="${esc(chEdid(value))}" placeholder="none" list="${id}" autocomplete="off" style="${width ? 'width:' + width + 'px' : ''}"><datalist id="${id}"></datalist><small style="margin-left:6px;color:var(--faint)">${esc(chName(value))}</small>`;
}
function chEdid(k){ return k ? (CH.data.links[k] || k).split(' (')[0].split(' — ')[0] : ''; }
function chName(k){ const l = k ? CH.data.links[k] || '' : ''; return l.includes(' — ') ? l.split(' — ')[1].replace(/ \([A-Z_]{4}\)$/, '') : ''; }
let chFindTimer;
function chLinkFind(i){
  clearTimeout(chFindTimer);
  chFindTimer = setTimeout(async () => {
    const rows = (await Promise.all(i.dataset.type.split(' ').map(t => api(`/api/records?type=${t}&q=${encodeURIComponent(i.value)}`)))).flat();
    i._hits = rows.slice(0, 60);
    i.nextElementSibling.innerHTML = i._hits.map(r => `<option value="${esc(r.edid)}">${esc(r.name)}</option>`).join('');
  }, 180);
}
async function chLinkField(i){
  const v = i.value.trim();
  let key = '', label = '';
  if (v){
    const rows = i._hits && i._hits.length ? i._hits : (await Promise.all(i.dataset.type.split(' ').map(t => api(`/api/records?type=${t}&q=${encodeURIComponent(v)}`)))).flat();
    let hit = rows.find(r => r.edid.toLowerCase() === v.toLowerCase());
    if (!hit && v.toLowerCase() === 'player' ) hit = {key: 'FalloutNV.esm:000014', edid: 'Player', name: ''};
    if (!hit){ i.style.borderColor = 'var(--red)'; return toast(`Nothing has the editor ID "${v}"`, true); }
    key = hit.key; label = hit.name ? `${hit.edid} — ${hit.name}` : hit.edid;
    CH.data.links[key] = label;
  }
  i.style.borderColor = ''; i.dataset.key = key;
  const small = i.nextElementSibling.nextElementSibling; if (small) small.textContent = key ? chName(key) : '';
  const [kind, a, b] = i.dataset.link.split('|');
  if (kind === 'sub'){                    // a subrecord that is just this link: empty takes it out
    if (!key) CH.rec.subs = CH.rec.subs.filter(s => s.tag !== a);
    else if (chSub(a)) chSub(a).value = key;
    else chInsert({tag: a, label: b || a, kind: 'F', value: key});
  } else if (kind === 'at'){              // one subrecord by its place in the record
    const s = CH.rec.subs[+a];
    if (s.kind === 'F') s.value = key; else s.fields.find(f => f.code === 'F').value = key;
  } else if (kind === 'union') chUnion(a, chVal(a, 'Type'), key);
  chDirty();
  if (i.dataset.redraw) chDraw();
}

// ---------- the inventory: the Create page's editor, over this page's record ----------
function chWithCR(fn){
  const r = CR.rec, d = CR.data; CR.rec = CH.rec; CR.data = CH.data;
  try { return fn(); } finally { CR.rec = r; CR.data = d; }
}
async function chInvRead(){
  const box = $('#ch-inv'); if (!box) return;
  const r = CR.rec, d = CR.data; CR.rec = CH.rec; CR.data = CH.data;
  try { await crRead(box); } finally { CR.rec = r; CR.data = d; }
}

// ---------- one record ----------
function chDraw(){
  const t = CH.rec.type;
  if (t === 'PACK') return chDrawPackage();
  if (t === 'FACT') return chDrawFaction();
  return chDrawActor();
}
function chTitle(kind){
  const d = CH.data, mine = d.state === 'new';
  return `<div class="bwtitle"><b>${esc(chVal('FULL') || chVal('EDID') || d.key)}</b>
      <small>${esc(kind)} · ${mine ? 'your own' : d.state === 'changed' ? 'the game\'s, changed by your mod' : 'the game\'s (' + esc(d.from) + ')'}</small></div>
    <div class="acts" style="padding-left:0">
      <button class="btn primary" data-a="save" ${CH.dirty ? '' : 'disabled'}>${mine ? 'Save' : 'Save changes to this one'}</button>
      ${mine ? '' : `<button class="btn primary" data-a="copy" title="A new one of your own, a copy of this one; the game's stays as it is">＋ New one from this</button>`}
      ${d.state === 'changed' ? '<button class="btn" data-a="revert">Put back as the game has it</button>' : ''}
      ${mine ? '<button class="btn" data-a="revert">Delete this one</button>' : ''}
      ${t2place(CH.rec.type) ? '<button class="btn" data-a="place" title="Go to the World page and click where they stand">Place it</button>' : ''}
      <button class="btn" data-a="browse" title="Every part of the record">Open in Browse</button>
    </div>
    ${mine ? '' : `<div class="note" style="padding:0 0 6px">Changes here change the game's own: every place that uses it gets them. A new one of your own is only used where you put it.</div>`}`;
}
const t2place = t => t === 'NPC_' || t === 'CREA';

function chDrawActor(){
  const npc = CH.rec.type === 'NPC_';
  const tabs = npc ? [['who', 'Who'], ['stats', 'Stats and skills'], ['ai', 'Behaviour'], ['carry', 'Carries'], ['look', 'Looks']]
                   : [['who', 'What'], ['stats', 'Stats'], ['ai', 'Behaviour'], ['carry', 'Carries']];
  if (!tabs.some(t => t[0] === CH.tab)) CH.tab = 'who';
  const body = {who: chWho, stats: chStats, ai: chAI, carry: chCarry, look: chLooks}[CH.tab]();
  $('#ch-detail').innerHTML = `${chTitle(npc ? 'Character' : 'Creature')}
    <div class="ch-tabs">${tabs.map(([k, l]) => `<button data-tab="${k}" class="${k === CH.tab ? 'on' : ''}">${l}</button>`).join('')}</div>
    <div class="ch-body"><div class="ch-form">${body}</div>
      <div class="ch-side"><div id="ch-view" title="How FOLab draws them (the race's plain head: not the face)"></div>
        <div id="ch-worn" class="ch-worn"></div></div></div>`;
  const inv = $('#ch-inv'); if (inv) crBind(inv, chDirty);
  chPreview();
}
function chUsesTemplate(bit){ return !!(chVal('TPLT') && (chVal('ACBS', 'Template flags') & bit)); }
function chFromTemplate(bit, what){
  return chUsesTemplate(bit) ? `<div class="ch-warn">${esc(what)} come${what.endsWith('s') ? '' : 's'} from the template (${esc(chEdid(chVal('TPLT')))}), so what's set here doesn't show in game. Untick it under Template on the first tab to set it here.</div>` : '';
}
function chLevelRow(){
  const flags = chVal('ACBS', 'Flags') >>> 0, on = !!(flags & 0x80), v = chVal('ACBS', 'Level');
  return chRow('Level', `<label style="color:var(--muted)"><input type="checkbox" data-a2="levelmult" ${on ? 'checked' : ''}> Follows the player's level</label>
    ${on ? `<div style="margin-top:4px;display:flex;gap:8px;align-items:center"><input data-a3="levelx" value="${+(v / 1000).toFixed(2)}" style="width:80px"> × the player's level, between
       <input data-f="ACBS|Calc min level" value="${chVal('ACBS', 'Calc min level')}" style="width:60px"> and <input data-f="ACBS|Calc max level" value="${chVal('ACBS', 'Calc max level')}" style="width:60px"><small>(0: no limit)</small></div>`
         : `<input data-f="ACBS|Level" value="${v}" style="width:80px;margin-top:4px">`}`);
}
function chWho(){
  const o = CH.opts, npc = CH.rec.type === 'NPC_', tp = chVal('TPLT');
  const flags = chVal('ACBS', 'Flags') >>> 0;
  return `<div class="ch-grid">
    ${chText('FULL', 'Name') || chRow('Name', `<button class="btn" data-a="addname">Give a name</button>`, 'None: it shows the name of its template, or nothing')}
    ${chText('EDID', 'Editor ID', 'The name scripts and the console use; no spaces')}
    ${npc ? chRow('Sex', `<label style="color:var(--muted)"><input type="checkbox" data-f="ACBS|Flags" data-bit="1" data-redraw="1" ${flags & 1 ? 'checked' : ''}> Female</label>`) : chPick('DATA', 'Type', 'Kind', CH_CREATYPE)}
    ${npc ? chSelect('RNAM', 'Race', o.races, null, '', true) : ''}
    ${npc ? chSelect('CNAM', 'Class', o.classes, null, 'Sets the stats when they\'re worked out, and what they\'re trained in') : ''}
    ${chSelect('VTCK', 'Voice', o.voices, 'None', 'Which recorded lines they use')}
    ${chLevelRow()}
    ${chSelect('ZNAM', 'Fights like', o.combat, 'As the game decides', 'Combat style')}
    ${npc ? chRow('Karma', `<input data-f="ACBS|Karma" value="${esc(+chVal('ACBS', 'Karma').toFixed(1))}" style="width:90px">`) : ''}
    ${chRow('Likes the player', `<input data-f="ACBS|Disposition" value="${chVal('ACBS', 'Disposition')}" style="width:90px">`, 'How much, at the start (disposition)')}
    ${chRow('Sells for', `<input data-f="ACBS|Barter gold" value="${chVal('ACBS', 'Barter gold')}" style="width:90px"> caps`, 'Barter caps')}
    ${chRow('Dropped when killed', chLink('sub|INAM|Death item', chVal('INAM'), 'LVLI', 220))}
    </div>
    <div class="h" style="padding-left:0;margin-top:14px">How it works</div>
    ${chFlags('ACBS', 'Flags', npc ? CH_NPCFLAGS : CH_CREAFLAGS)}
    <div class="h" style="padding-left:0;margin-top:14px">Template</div>
    <div class="ch-grid">${chRow('Takes from', chLink('sub|TPLT|Template', tp, npc ? 'NPC_ LVLN' : 'CREA LVLC', 240), 'A character or a levelled list. With a list, each one placed is picked by the player\'s level: that is how the game does levelled people and creatures')}</div>
    ${tp ? chFlags('ACBS', 'Template flags', CH_TFLAGS) : ''}
    ${(CH.data.warnings || []).filter(w => w.startsWith('Race, sex')).map(w => `<div class="ch-warn">${esc(w)}</div>`).join('')}`;
}
function chStats(){
  const npc = CH.rec.type === 'NPC_';
  const auto = npc && (chVal('ACBS', 'Flags') & 16);
  return `${chFromTemplate(2, 'Stats')}
    ${auto ? '<div class="ch-warn">Stats are worked out from the class and level (the box on the first tab): these numbers aren\'t used in game.</div>' : ''}
    <div class="h" style="padding-left:0">S.P.E.C.I.A.L.</div>
    <div class="ch-nums">${CH_SPECIAL.map(s => chNum('DATA', s, s)).join('')}</div>
    <div class="h" style="padding-left:0;margin-top:12px">${npc ? 'Health and speed' : 'Health, damage and speed'}</div>
    <div class="ch-nums">${chNum('DATA', 'Health', npc ? 'Base health' : 'Health')}${npc ? '' : chNum('DATA', 'Damage', 'Attack damage')}
      ${chNum('ACBS', 'Fatigue', 'Fatigue')}${chNum('ACBS', 'Speed ×', 'Speed (100: normal)')}
      ${npc ? '' : chNum('RNAM', 'Reach', 'Attack reach') + chNum('TNAM', 'Speed', 'Turning speed') + chNum('BNAM', 'Scale', 'Size') + chNum('WNAM', 'Weight', 'Foot weight')}</div>
    ${npc ? `<div class="h" style="padding-left:0;margin-top:12px">Skills</div><div class="ch-nums">${CH_SKILLS.map(s => chNum('DNAM', s, s)).join('')}</div>`
          : `<div class="h" style="padding-left:0;margin-top:12px">Skills</div><div class="ch-nums">${chNum('DATA', 'Combat skill', 'Combat')}${chNum('DATA', 'Magic skill', 'Other')}${chNum('DATA', 'Stealth skill', 'Stealth')}</div>`}`;
}
function chAI(){
  const packs = CH.rec.subs.map((s, i) => [s, i]).filter(([s]) => s.tag === 'PKID');
  const facts = chSubs('SNAM');
  return `${chFromTemplate(16, 'How they behave')}
    <div class="ch-grid">
    ${chPick('AIDT', 'Aggression', 'Aggression', CH_AGG)}
    ${chPick('AIDT', 'Confidence', 'Confidence', CH_CONF)}
    ${chPick('AIDT', 'Assistance', 'Helps others', CH_ASSIST)}
    ${chPick('AIDT', 'Mood', 'Mood', CH_MOOD)}
    ${chRow('Energy', `<input data-f="AIDT|Energy" value="${chVal('AIDT', 'Energy')}" style="width:80px">`, 'How often they move about (0 to 100)')}
    ${chRow('Responsibility', `<input data-f="AIDT|Responsibility" value="${chVal('AIDT', 'Responsibility')}" style="width:80px">`, 'How much they care about crime (0 to 100; 0 will steal)')}
    </div>
    <div class="h" style="padding-left:0;margin-top:14px">What they do · top first</div>
    ${chFromTemplate(32, 'AI packages')}
    <table>${packs.map(([s, i], n) => `<tr><td>${chLink('at|' + i, s.value, 'PACK', 260)}</td>
      <td><button class="btn" data-pkup="${i}" ${n ? '' : 'disabled'} title="Before the one above">↑</button> <button class="btn" data-open="${esc(s.value)}" title="See this package">Open</button> <button class="btn" data-del="${i}" title="Take this off">✕</button></td></tr>`).join('')}</table>
    <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">
      <button class="btn" data-a="pkadd">＋ A package the game has</button>
      <select data-a4="pknew"><option value="">＋ A new one…</option>${CH.tpl.packages.map(p => `<option value="${esc(p.id)}" title="${esc(p.note)}">${esc(p.label)}</option>`).join('')}</select></div>
    ${packs.length ? '' : '<p class="note" style="padding:6px 0">With no packages they stand where they\'re placed.</p>'}
    <div class="h" style="padding-left:0;margin-top:14px">Factions</div>
    ${chFromTemplate(4, 'Factions')}
    <table><tr><th>Faction</th><th>Rank</th><th></th></tr>${facts.map((s, n) => {
      const k = s.fields.find(f => f.code === 'F').value, r = s.fields.find(f => f.name === 'Rank').value;
      return `<tr><td>${chLink('at|' + CH.rec.subs.indexOf(s), k, 'FACT', 240)}</td><td><select data-rankof="${n}" data-faction="${esc(k)}"><option value="${r}" selected>${r}</option></select></td>
        <td><button class="btn" data-del="${CH.rec.subs.indexOf(s)}" title="Take them out of it">✕</button></td></tr>`;
    }).join('')}</table>
    <button class="btn" data-a="factadd" style="margin-top:6px">＋ Add a faction</button>`;
}
function chCarry(){
  const uses = chUsesTemplate(256);
  return `${uses ? `<div class="ch-warn">The inventory comes from the template: this is what they get.</div><table>${(CH.data.inherited || []).map(i => `<tr><td>${esc(i.name)}</td><td>× ${i.count}</td></tr>`).join('')}</table>` : ''}
    <div id="ch-inv" class="${uses ? 'ch-off' : ''}">${chWithCR(crEntries)}</div>
    <p class="note" style="padding:8px 0">They wear the best of the apparel they carry that fits; the box on the right shows what FOLab reckons they'd have on. Weapons, ammo and aid they keep in their pack and use as needed.</p>`;
}
function chLooks(){
  const o = CH.opts, race = o.races.find(r => r.key === chVal('RNAM'));
  const female = !!(chVal('ACBS', 'Flags') & 1);
  const presets = o.presets.filter(p => p.female === female).sort((a, b) => (b.race === chVal('RNAM')) - (a.race === chVal('RNAM')));
  const col = chSub('HCLR');
  const hex = col ? '#' + ['Red', 'Green', 'Blue'].map(c => (+chVal('HCLR', c)).toString(16).padStart(2, '0')).join('') : '#000000';
  return `${chFromTemplate(1, 'Race, sex and face')}
    ${(CH.data.warnings || []).filter(w => !w.startsWith('Race, sex')).map(w => `<div class="ch-warn">${esc(w)}</div>`).join('')}
    <div class="h" style="padding-left:0">Face</div>
    <div class="ch-grid">
      ${chRow('A preset', `<select data-a4="preset"><option value="">Pick a face…</option>${presets.map(p => `<option value="${esc(p.key)}">${esc(p.label)}${p.race === chVal('RNAM') ? '' : ' (another race)'}</option>`).join('')}</select>`, 'The faces the game offers when you make your character')}
      ${chRow('Copy from someone', `<input data-copyface="1" data-linkfind="1" data-type="NPC_" placeholder="Editor ID…" list="ch-dl-face" autocomplete="off"><datalist id="ch-dl-face"></datalist> <button class="btn" data-a="faceget">Copy their face</button>`, 'Their face numbers exactly, with their hair and eyes')}
    </div>
    <p class="note" style="padding:6px 0">FOLab copies a face as it is; it can't shape one yet. The preview on the right shows the race's plain head, not this face.</p>
    <div class="h" style="padding-left:0;margin-top:10px">Hair and eyes</div>
    <div class="ch-grid">
      ${chSelect('HNAM', 'Hair', o.hairs, 'None', race && race.hairs.length ? '' : 'Every hair is listed: this race names none of its own', true, race && race.hairs.length ? race.hairs : null)}
      ${chSelect('ENAM', 'Eyes', o.eyes, 'None', '', false, race && race.eyes.length ? race.eyes : null)}
      ${chRow('Hair colour', `<input type="color" data-haircol="1" value="${hex}">`)}
      ${chRow('Hair length', `<input data-f="LNAM|Length" value="${esc(chVal('LNAM', 'Length') === undefined ? '' : +(+chVal('LNAM', 'Length')).toFixed(3))}" style="width:80px" ${chSub('LNAM') ? '' : 'disabled'}>`)}
    </div>
    <div class="h" style="padding-left:0;margin-top:10px">Body</div>
    <div class="ch-grid">
      ${chRow('Height', `<input data-f="NAM6|Height" value="${esc(+(+chVal('NAM6', 'Height')).toFixed(3))}" style="width:80px">`, '0 or 1: the race\'s usual')}
    </div>`;
}

// the preview: every part of them, turning (the Create page's renderer)
async function chPreview(){
  const el = $('#ch-view'); if (!el) return;
  let d;
  try { d = await post('/api/char/look', {key: CH.key, record: CH.rec}); } catch (e){ return; }
  const worn = $('#ch-worn');
  if (worn) worn.innerHTML = CH.rec.type === 'NPC_' ? ((d.wearing || []).length ? '<b>Wearing</b><br>' + d.wearing.map(w => esc(w.name)).join('<br>') : 'Wearing nothing they carry: their body as the race has it.') : '';
  mpInit();
  const c = MP.ren.domElement, w = el.clientWidth || 280, h = el.clientHeight || 360;
  if (c.parentNode !== el){ el.innerHTML = ''; el.appendChild(c); }
  MP.ren.setSize(w, h);
  MP.cam.aspect = w / h; MP.cam.updateProjectionMatrix();
  const token = ++MP.token;
  if (MP.obj){ MP.scene.remove(MP.obj); MP.obj = null; }
  const lists = await Promise.all((d.parts || []).map(p => model(p.model, p.tex)));
  if (token !== MP.token) return;
  const g = new T.Group();
  for (const [geo, mat] of lists.flat()) g.add(new T.Mesh(geo, mat));
  const box = new T.Box3().setFromObject(g);
  if (box.isEmpty()){ if (el.contains(c)) el.removeChild(c); el.innerHTML = '<div class="note" style="padding:20px">Nothing FOLab can draw</div>'; return; }
  const mid = box.getCenter(new T.Vector3()), size = box.getSize(new T.Vector3());
  const inner = new T.Group(); g.position.sub(mid); inner.add(g);
  MP.obj = inner; MP.scene.add(inner);
  const r = Math.max(size.length() / 2, 1), dist = r / Math.sin(MP.cam.fov * Math.PI / 360) * 1.02;
  MP.cam.position.set(dist * 0.25, -dist * 0.95, dist * 0.12);
  MP.cam.lookAt(0, 0, 0);
  MP.cam.near = dist / 100; MP.cam.far = dist * 10; MP.cam.updateProjectionMatrix();
}

// ---------- AI packages ----------
function chUnion(tag, kind, target, third){
  // where a package happens or what it aims at: the kind decides whether its second number is a link (the schema's unions)
  const place = tag === 'PLDT' || tag === 'PLD2';
  const link = place ? [0, 1, 4].includes(kind) : [0, 1].includes(kind);
  let s = chSub(tag);
  if (!s) s = chInsert({tag, label: place ? 'Location' : 'Target', kind: 'struct', fields: []});
  const old = s.fields || [];
  const thirdName = place ? 'Radius' : 'Count or distance';
  const was = old.find(f => f.name === thirdName);
  const val = third !== undefined ? third : was ? was.value : 0;
  const cur = old.find(f => f.code === 'F' || f.name === 'Value');
  const tg = target !== undefined ? target : cur && cur.code === 'F' && link ? cur.value : link ? '' : 0;
  s.fields = [{name: 'Type', code: 'i', value: kind}, link ? {name: 'Target', code: 'F', value: tg} : {name: 'Value', code: 'I', value: tg || 0},
              {name: thirdName, code: 'i', value: val}].concat(place ? [] : [old.find(f => f.pad !== undefined) || {pad: '00000000'}]);
  s.kind = 'struct'; delete s.value;
}
function chDrawPackage(){
  const v = chVal('PKDT', 'Type'), pl = chSub('PLDT'), tg = chSub('PTDT');
  const pk = chVal('PLDT', 'Type'), tk = chVal('PTDT', 'Type');
  const time = chVal('PSDT', 'Time'), dur = chVal('PSDT', 'Duration'), dow = chVal('PSDT', 'Day of week');
  const conds = chSubs('CTDA').length, scripts = chSubs('SCDA').length;
  $('#ch-detail').innerHTML = `${chTitle('AI package')}
    <div class="ch-form" style="max-width:760px">
    <div class="ch-grid" style="margin-top:6px">
      ${chText('EDID', 'Editor ID')}
      ${chRow('What they do', `<select data-f="PKDT|Type" data-redraw="1">${Object.entries(CH_PKTYPES).map(([k, l]) => `<option value="${k}" ${+k === v ? 'selected' : ''}>${l}</option>`).join('')}</select>`,
        {12: 'Stays round the place doing everyday things', 13: 'Walks a path of patrol markers, from their linked ref on: FOLab can\'t make those links yet', 14: 'Stays put and sees off anyone who comes near', 1: 'Keeps close to the target'}[v] || '')}
    </div>
    <div class="h" style="padding-left:0;margin-top:14px">Where</div>
    <div class="ch-grid">
      ${chRow('Place', `<select data-a4="pkplace"><option value="" ${pl ? '' : 'selected'}>Anywhere (no place set)</option>${Object.entries(CH_PLACE).map(([k, l]) => `<option value="${k}" ${pl && +k === pk ? 'selected' : ''}>${l}</option>`).join('')}${pl && !(pk in CH_PLACE) ? `<option selected value="${pk}">${pk}</option>` : ''}</select>`)}
      ${pl && [0, 1, 4].includes(pk) ? chRow(pk === 1 ? 'Which place' : 'Which', chLink('union|PLDT', chVal('PLDT', 'Target'), pk === 1 ? 'CELL' : 'REFR ACHR ACRE', 240), pk === 1 ? '' : 'Things placed in the world aren\'t listed here: type "player", or use Browse') : ''}
      ${pl ? chRow('Within', `<input data-f="PLDT|Radius" value="${chVal('PLDT', 'Radius')}" style="width:90px"> units`, '64 is about a person\'s stride and a half; 512 a big room') : ''}
    </div>
    <div class="h" style="padding-left:0;margin-top:14px">Aimed at</div>
    <div class="ch-grid">
      ${chRow('Target', `<select data-a4="pktarget"><option value="" ${tg ? '' : 'selected'}>Nothing</option>${Object.entries(CH_TARGET).map(([k, l]) => `<option value="${k}" ${tg && +k === tk ? 'selected' : ''}>${l}</option>`).join('')}</select>`, 'What they follow, eat, guard or shoot at')}
      ${tg && [0, 1].includes(tk) ? chRow('Which', chLink('union|PTDT', chVal('PTDT', 'Target'), tk === 1 ? 'NPC_ CREA WEAP ARMO ALCH MISC FURN FLST FACT' : 'REFR ACHR ACRE', 240), tk === 0 ? 'Type "player" for the player' : '') : ''}
      ${tg ? chRow('Distance or count', `<input data-f="PTDT|Count or distance" value="${chVal('PTDT', 'Count or distance')}" style="width:90px">`) : ''}
    </div>
    <div class="h" style="padding-left:0;margin-top:14px">When</div>
    <div class="ch-grid">
      ${chRow('From', `<select data-f="PSDT|Time"><option value="-1" ${time < 0 ? 'selected' : ''}>Any time</option>${[...Array(24).keys()].map(h => `<option value="${h}" ${h === time ? 'selected' : ''}>${String(h).padStart(2, '0')}:00</option>`).join('')}</select>`)}
      ${chRow('For', `<input data-f="PSDT|Duration" value="${dur}" style="width:70px"> hours`, '0: as long as it applies')}
      ${chRow('On', `<select data-f="PSDT|Day of week"><option value="-1" ${dow < 0 ? 'selected' : ''}>Every day</option>${CH_DAYS.map((d, n) => `<option value="${n}" ${n === dow ? 'selected' : ''}>${d}</option>`).join('')}</select>`)}
    </div>
    <div class="h" style="padding-left:0;margin-top:14px">How</div>
    ${chFlags('PKDT', 'Flags', CH_PKFLAGS)}
    ${v === 12 && chVal('PKDT', 'Type flags') !== undefined ? '<div class="h" style="padding-left:0;margin-top:10px">Sandbox: they may</div>' + chFlags('PKDT', 'Type flags', CH_SANDBOX, true) : ''}
    ${conds || scripts ? `<p class="note" style="padding:8px 0 0">${conds ? conds + ' condition' + (conds === 1 ? '' : 's') : ''}${conds && scripts ? ' and ' : ''}${scripts ? scripts + ' script' + (scripts === 1 ? '' : 's') : ''} kept as the game has them. See them in Browse.</p>` : ''}
    <div class="h" style="padding-left:0;margin-top:14px">Used by</div><div id="ch-used" class="note" style="padding:0">…</div>
    </div>`;
  chUsed();
}
async function chUsed(){
  const box = $('#ch-used'); if (!box) return;
  if (CH.key.startsWith('+')){ const rows = CH.rows; box.textContent = 'Your own: put it on someone on their Behaviour tab.'; return; }
  const u = await api('/api/used?key=' + encodeURIComponent(CH.key));
  if (u.busy){ box.textContent = 'Still reading the game: a moment.'; return; }
  box.innerHTML = (u.rows || []).slice(0, 30).map(r => esc(r.label)).join('<br>') + (u.total > 30 ? `<br>and ${u.total - 30} more` : '') || 'Nothing the game has.';
}

// ---------- factions ----------
function chRankGroups(){
  // each rank: its number, then any titles after it
  const out = [];
  CH.rec.subs.forEach((s, i) => {
    if (s.tag === 'RNAM') out.push({at: i, parts: {RNAM: i}});
    else if (out.length && ['MNAM', 'FNAM', 'INAM'].includes(s.tag)) out[out.length - 1].parts[s.tag] = i;
  });
  return out;
}
function chDrawFaction(){
  const rel = CH.rec.subs.map((s, i) => [s, i]).filter(([s]) => s.tag === 'XNAM');
  const ranks = chRankGroups();
  const zin = (i, ph) => i === undefined ? `<span class="note" style="padding:0">none</span>` : `<input data-zat="${i}" value="${esc(CH.rec.subs[i].value)}" placeholder="${esc(ph)}">`;
  $('#ch-detail').innerHTML = `${chTitle('Faction')}
    <div class="ch-form" style="max-width:780px">
    <div class="ch-grid" style="margin-top:6px">
      ${chText('FULL', 'Name') || chRow('Name', `<button class="btn" data-a="addname">Give a name</button>`)}
      ${chText('EDID', 'Editor ID')}
      ${chRow('Reputation', chLink('sub|WMI1|Reputation', chVal('WMI1'), 'REPU', 220), 'The reputation that joining and hurting it moves')}
    </div>
    ${chFlags('DATA', 'Flags', [[1, 'Hidden from the player', ''], [2, 'Evil', 'Killing its members is no bad deed'], [4, 'Special combat', 'Its members fight only those named below']])}
    <div class="h" style="padding-left:0;margin-top:14px">How it gets on with others</div>
    <table data-table="1"><tr><th>Faction</th><th>Liking</th><th>In a fight</th><th></th></tr>
    ${rel.map(([s, i]) => `<tr><td>${chLink('at|' + i, s.fields.find(f => f.code === 'F').value, 'FACT', 240)}</td>
      <td><input data-nam="${i}" data-name="Modifier" value="${s.fields.find(f => f.name === 'Modifier').value}" style="width:60px"></td>
      <td><select data-nam="${i}" data-name="Group combat reaction" data-reaction="1">${CH_REACT.map((l, n) => `<option value="${n}" ${n === s.fields.find(f => f.name === 'Group combat reaction').value ? 'selected' : ''}>${l}</option>`).join('')}</select></td>
      <td><button class="btn" data-del="${i}">✕</button></td></tr>`).join('')}</table>
    <button class="btn" data-a="reladd" style="margin-top:6px">＋ Add</button>
    <div class="h" style="padding-left:0;margin-top:14px">Ranks</div>
    <table data-table="1"><tr><th>Number</th><th>Title (male)</th><th>Title (female)</th><th></th></tr>
    ${ranks.map(g => `<tr><td><input data-nam="${g.parts.RNAM}" data-name="Number" value="${CH.rec.subs[g.parts.RNAM].fields[0].value}" style="width:60px"></td>
      <td>${zin(g.parts.MNAM, 'Title')}</td><td>${zin(g.parts.FNAM, 'Title')}</td><td><button class="btn" data-rankdel="${g.at}">✕</button></td></tr>`).join('')}</table>
    <button class="btn" data-a="rankadd" style="margin-top:6px">＋ Add a rank</button>
    <div class="h" style="padding-left:0;margin-top:14px">Who's in it</div><div id="ch-members" class="note" style="padding:0">…</div>
    </div>`;
  chMembers();
}
async function chMembers(){
  const box = $('#ch-members'); if (!box) return;
  if (CH.key.startsWith('+')){ box.textContent = 'Your own: add someone on their Behaviour tab.'; return; }
  const m = await api('/api/char/members?key=' + encodeURIComponent(CH.key));
  if (m.busy){ box.textContent = 'Still reading the game: a moment.'; return; }
  box.innerHTML = m.rows.map(r => `<a href="#" data-open="${esc(r.key)}" style="color:var(--gold)">${esc(r.label.replace(/ \(.{4}\)$/, ''))}</a>`).join(', ') + (m.total > m.rows.length ? `, and ${m.total - m.rows.length} more` : '') || 'Nobody the game has.';
}

async function chRanks(sel){
  // a faction's ranks into a Rank box, when it opens
  const k = sel.dataset.faction; if (!k) return;
  if (!CH.ranks[k]) CH.ranks[k] = (async () => {
    const d = await api('/api/record?key=' + encodeURIComponent(k));
    const out = []; let cur = null;
    for (const s of d.record.subs){
      if (s.tag === 'RNAM'){ cur = {n: s.fields[0].value, t: ''}; out.push(cur); }
      else if (cur && (s.tag === 'MNAM' || s.tag === 'FNAM') && !cur.t) cur.t = s.value;
    }
    return out;
  })();
  const r = await CH.ranks[k], v = +sel.value;
  sel.innerHTML = (r.some(x => x.n === v) ? '' : `<option value="${v}">${v}</option>`) + r.map(x => `<option value="${x.n}" ${x.n === v ? 'selected' : ''}>${x.n}${x.t ? ': ' + esc(x.t) : ''}</option>`).join('');
}
$('#ch-detail').addEventListener('focusin', e => { if (e.target.dataset && e.target.dataset.rankof !== undefined) chRanks(e.target); });

// ---------- buttons ----------
async function chClick(e){
  const t = e.target;
  if (t.dataset.tab){ try { await chInvRead(); } catch (err){ return fail(err); } CH.tab = t.dataset.tab; return chDraw(); }
  if (t.dataset.open){ e.preventDefault(); const k = t.dataset.open; const ty = (CH.data.links[k] || '').match(/\(([A-Z_]{4})\)$/); if (CH.dirty && !chLeave()) return; CH.kind = ty ? ty[1] : t.closest('#ch-members') ? 'NPC_' : 'PACK'; await chInit(); return chOpen(k); }
  if (t.dataset.pkup){ const i = +t.dataset.pkup, s = CH.rec.subs, prev = s.slice(0, i).map(x => x.tag).lastIndexOf('PKID'); [s[prev], s[i]] = [s[i], s[prev]]; chDirty(); return chDraw(); }
  if (t.dataset.del){ try { await chInvRead(); } catch (err){ return fail(err); } CH.rec.subs.splice(+t.dataset.del, 1); chDirty(); return chDraw(); }
  if (t.dataset.rankdel){ const g = chRankGroups().find(x => x.at === +t.dataset.rankdel); const del = new Set(Object.values(g.parts)); CH.rec.subs = CH.rec.subs.filter((s, i) => !del.has(i)); chDirty(); return chDraw(); }
  if (t.dataset.entdel !== undefined && t.closest('#ch-inv')){
    try { await chInvRead(); } catch (err){ return fail(err); }
    chWithCR(() => { const at = crEntryGroups()[+t.dataset.entdel]; CH.rec.subs.splice(at, crGroupEnd(at) - at); });
    chDirty(); return chDraw();
  }
  const a = t.dataset.a; if (!a) return;
  try {
    if (a === 'entadd'){
      await chInvRead();
      chWithCR(() => { const g = crEntryGroups(), before = CR_ENTRIES[CH.rec.type][1]; let at = g.length ? crGroupEnd(g[g.length - 1]) : CH.rec.subs.findIndex(s => before.includes(s.tag)); if (at < 0) at = CH.rec.subs.length; CH.rec.subs.splice(at, 0, crNewEntry()); });
      chDirty(); chDraw();
      const boxes = document.querySelectorAll('#ch-inv [data-ent]'); if (boxes.length) boxes[boxes.length - 1].focus();
      return;
    }
    if (a === 'pkadd'){ chInsert({tag: 'PKID', label: 'AI package', kind: 'F', value: ''}); chDirty(); chDraw(); const b = document.querySelectorAll('[data-link^="at|"]'); return; }
    if (a === 'factadd'){ chInsert({tag: 'SNAM', label: 'Faction', kind: 'struct', fields: [{name: 'Faction', code: 'F', value: ''}, {name: 'Rank', code: 'b', value: 0}, {pad: '000000'}]}); chDirty(); return chDraw(); }
    if (a === 'reladd'){ chInsert({tag: 'XNAM', label: 'Relation', kind: 'struct', fields: [{name: 'Faction', code: 'F', value: ''}, {name: 'Modifier', code: 'i', value: 0}, {name: 'Group combat reaction', code: 'I', value: 0}]}); chDirty(); return chDraw(); }
    if (a === 'rankadd'){
      const gs = chRankGroups(), n = gs.length ? Math.max(...gs.map(g => CH.rec.subs[g.parts.RNAM].fields[0].value)) + 1 : 0;
      let at = CH.rec.subs.findIndex(s => s.tag === 'WMI1'); if (at < 0) at = CH.rec.subs.length;
      CH.rec.subs.splice(at, 0, {tag: 'RNAM', label: 'Rank', kind: 'struct', fields: [{name: 'Number', code: 'i', value: n}]},
        {tag: 'MNAM', label: 'Male title', kind: 'z', value: ''}, {tag: 'FNAM', label: 'Female title', kind: 'z', value: ''});
      chDirty(); return chDraw();
    }
    if (a === 'addname'){ chInsert({tag: 'FULL', label: 'Name', kind: 'z', value: chVal('EDID') || ''}); chDirty(); return chDraw(); }
    if (a === 'faceget'){
      const i = $('[data-copyface]'), v = i.value.trim(); if (!v) return toast('Type the editor ID of someone to copy', true);
      const rows = await api(`/api/records?type=NPC_&q=${encodeURIComponent(v)}`);
      const hit = rows.find(r => r.edid.toLowerCase() === v.toLowerCase());
      if (!hit) return toast(`Nothing has the editor ID "${v}"`, true);
      return chSetFace(hit.key);
    }
    if (a === 'save') return chSave();
    if (a === 'copy'){
      if (CH.dirty && !confirm('Your changes here aren\'t kept in the new one. Go on?')) return;
      CH.dirty = false;
      const r = await post('/api/record/copy', {key: CH.key});
      setState(r.state); await chList(); await chOpen(r.made[0]);
      return toast('A new one of your own: give it a name');
    }
    if (a === 'revert'){
      const mine = CH.data.state === 'new';
      if (!confirm(mine ? 'Delete this one of yours?' : 'Put this back as the game has it?')) return;
      const r = await post('/api/record/revert', {key: CH.key});
      setState(r.state); CH.dirty = false; await chList();
      if (mine){ CH.key = null; $('#ch-detail').innerHTML = ''; } else chOpen(CH.key);
      return;
    }
    if (a === 'browse'){ if (CH.dirty && !chLeave()) return; page('browse'); await browseInit(); return bwOpen(CH.key); }
    if (a === 'place'){
      if (CH.dirty) return toast('Save your changes first', true);
      const it = {key: CH.key, type: CH.rec.type, edid: chVal('EDID'), name: chVal('FULL') || '', model: ''};
      page('world'); startPlacing(it);
      const h = $('#hint'); h.textContent = `Click where ${it.edid} goes · Esc or right-click stops`; h.style.display = 'block';
      return;
    }
    if (a === 'popgo') return chPopPlan();
    if (a === 'popagain'){ CH.pop.seed = (CH.pop.seed || 1) + 1; return chPopPlan(); }
    if (a === 'popapply') return chPopApply();
    if (a === 'poprefresh') return chPopulate();
  } catch (err){ fail(err); }
}
// the level as a multiple, and the other boxes that aren't one field
$('#ch-detail').addEventListener('change', async e => {
  const i = e.target;
  try {
    if (i.dataset.a2 === 'levelmult'){
      const on = i.checked, f = chVal('ACBS', 'Flags') >>> 0;
      chPut('ACBS', 'Flags', (on ? f | 0x80 : f & ~0x80) >>> 0);
      chPut('ACBS', 'Level', on ? 1000 : 1);
      chDirty(); return chDraw();
    }
    if (i.dataset.a3 === 'levelx'){
      const v = parseFloat(i.value);
      if (isNaN(v) || v <= 0) return toast('A multiple of the player\'s level above 0, like 1 or 0.75', true);
      chPut('ACBS', 'Level', Math.round(v * 1000)); return chDirty();
    }
    if (i.dataset.haircol){
      const c = i.value;
      if (!chSub('HCLR')) chInsert({tag: 'HCLR', label: 'Hair colour', kind: 'struct', fields: [{name: 'Red', code: 'B', value: 0}, {name: 'Green', code: 'B', value: 0}, {name: 'Blue', code: 'B', value: 0}, {pad: '00'}]});
      ['Red', 'Green', 'Blue'].forEach((n, k) => chPut('HCLR', n, parseInt(c.slice(1 + k * 2, 3 + k * 2), 16)));
      return chDirty();
    }
    if (i.dataset.reaction){ CH.rec.subs[+i.dataset.nam].fields.find(f => f.name === 'Group combat reaction').value = +i.value; return chDirty(); }
    if (i.dataset.a4 === 'pknew' && i.value){
      const p = CH.tpl.packages.find(x => x.id === i.value);
      const r = await post('/api/char/package/new', {template: p.id, name: (chVal('EDID') || '').replace(/^FOLab/, '') + ' ' + p.label});
      setState(r.state);
      CH.data.links[r.made[0]] = p.label;
      const d = await api('/api/record?key=' + encodeURIComponent(r.made[0]));
      CH.data.links[r.made[0]] = Object.keys(d.record.subs).length ? d.record.subs[0].value : p.label;
      // (above the rest if it only applies some of the time)
      const sub = {tag: 'PKID', label: 'AI package', kind: 'F', value: r.made[0]};
      const first = CH.rec.subs.findIndex(s => s.tag === 'PKID');
      if (first >= 0 && p.id === 'sleep') CH.rec.subs.splice(first, 0, sub); else chInsert(sub);
      chDirty(); toast('Made ' + p.label + ': press Open beside it to change where and when'); return chDraw();
    }
    if (i.dataset.a4 === 'preset' && i.value) return chSetFace(i.value);
    if (i.dataset.a4 === 'pkplace'){
      if (i.value === '') CH.rec.subs = CH.rec.subs.filter(s => s.tag !== 'PLDT');
      else chUnion('PLDT', +i.value, undefined, chVal('PLDT', 'Radius') === undefined ? 512 : undefined);
      chDirty(); return chDraw();
    }
    if (i.dataset.a4 === 'pktarget'){
      if (i.value === '') CH.rec.subs = CH.rec.subs.filter(s => s.tag !== 'PTDT');
      else chUnion('PTDT', +i.value);
      chDirty(); return chDraw();
    }
  } catch (err){ fail(err); }
});
async function chSetFace(from){
  const d = await post('/api/char/face', {key: CH.key, record: CH.rec, from});
  CH.rec = d.record; Object.assign(CH.data.links, d.links); CH.data.warnings = d.warnings;
  chDirty(); chDraw();
  toast('Their face is copied: save to keep it');
}
async function chSave(){
  await chInvRead();
  const edid = chVal('EDID');
  if (!/^[A-Za-z0-9_]+$/.test(edid || '')) throw new Error('Editor ID: letters, digits and _ only');
  // links left empty (rows added, nothing picked)
  for (const tag of ['PKID', 'SNAM', 'XNAM']){
    const empty = chSubs(tag).some(s => s.kind === 'F' ? !s.value : !s.fields.find(f => f.code === 'F').value);
    if (empty) throw new Error('A row has nothing in it: pick something, or take it out with ✕');
  }
  for (const [tag, what] of [['PLDT', 'Where'], ['PTDT', 'Aimed at']]){
    const f = chSub(tag) && chSub(tag).fields.find(f => f.code === 'F');
    // (the game's own leave no links empty here; a new one means nothing with none)
    if (f && !f.value) throw new Error(`${what}: pick which, or choose another kind`);
  }
  const d = await post('/api/record/save', {key: CH.key, record: CH.rec});
  setState(d.state); CH.dirty = false;
  if (typeof ACTOR_Q !== 'undefined') delete ACTOR_Q[CH.key];
  if (typeof recCacheDrop === 'function') recCacheDrop(CH.key);
  if (CH.rec.type === 'FACT') CH.opts = null, await chInit();
  toast('Saved in your mod'); await chList(); return chOpen(CH.key, true);
}

// new ones: a character or creature from a template, a package from one of the game's, an empty faction
function chNew(){
  if (!chLeave()) return;
  CH.key = null; CH.data = CH.rec = null;
  document.querySelectorAll('#ch-rows .row').forEach(r => r.classList.remove('on'));
  const k = CH.kind, tpl = k === 'PACK' ? CH.tpl.packages : k === 'FACT' ? null : CH.tpl.actors[k];
  $('#ch-detail').innerHTML = `<div class="bwtitle"><b>New ${{NPC_: 'character', CREA: 'creature', PACK: 'package', FACT: 'faction'}[k]}</b></div>
    <div class="ch-grid" style="max-width:520px;margin:8px 0"><label>Name</label><span><input id="ch-newname" placeholder="${k === 'PACK' ? 'e.g. Rosa at the bar' : k === 'FACT' ? 'e.g. The Dust Devils' : 'e.g. Rosa Vance'}"></span></div>
    ${tpl ? `<div class="h" style="padding-left:0">Start from</div>${tpl.map(t => `<div class="ch-tpl" data-new="${esc(t.key || t.id)}"><b>${esc(t.label)}</b>${t.note ? `<small>${esc(t.note)}</small>` : ''}</div>`).join('')}
      ${k === 'PACK' ? '' : '<p class="note" style="padding:8px 0">Or open anyone the game has and press <b>New one from this</b>.</p>'}` : '<button class="btn primary" data-newfact="1">Make it</button>'}`;
  $('#ch-newname').focus();
  $('#ch-detail').querySelectorAll('[data-new]').forEach(r => r.onclick = () => chMake(r.dataset.new));
  const nf = $('[data-newfact]'); if (nf) nf.onclick = () => chMake(null);
}
async function chMake(from){
  try {
    const name = $('#ch-newname').value.trim();
    const r = CH.kind === 'PACK' ? await post('/api/char/package/new', {template: from, name})
      : CH.kind === 'FACT' ? await post('/api/char/faction/new', {name}) : await post('/api/char/new', {from, name});
    setState(r.state);
    if (CH.kind === 'FACT') CH.opts = null, await chInit();
    await chList(); await chOpen(r.made[0]);
  } catch (e){ fail(e); }
}

// ---------- Populate ----------
async function chPopulate(){
  const here = {};
  const box = $('#ch-detail');
  const o = CH.pop;
  // the place: what's open on the World page, unless one was picked here
  let info = null;
  try {
    if (A.cellId && !A.outside) info = await api('/api/char/populate/place?cell=' + encodeURIComponent(A.cellId));
    else if (A.outside && typeof camCell === 'function'){ const [x, y] = camCell(); info = await api(`/api/char/populate/place?world=${encodeURIComponent(A.outside.id)}&x=${x}&y=${y}`); if (info.none) info = null; }
  } catch (e){}
  CH.popPlace = info;
  box.innerHTML = `<div class="bwtitle"><b>Populate a place</b><small>People and creatures, learnt from who the game puts in places like this one. Nothing changes until you press Place them.</small></div>
    ${info ? `<div class="ch-grid" style="max-width:640px;margin-top:10px">
      ${chRow('The place', `<b style="color:var(--gold2);font-weight:500">${esc(info.name)}</b> <button class="btn" data-a="poprefresh" title="Use what's open on the World page now">↻</button>`,
        (info.zone ? `Encounter zone ${info.zone.name}${info.zone.min ? ', level ' + info.zone.min + ' and up' : ''}. ` : '') + 'Open another on the World page to change it')}
      ${chRow('Who', `<select data-opt="who">${[['all', 'Both, as the game has it'], ['people', 'People only'], ['creatures', 'Creatures only']].map(([v, l]) => `<option value="${v}" ${o.who === v ? 'selected' : ''}>${l}</option>`).join('')}</select>`)}
      ${chRow('How many', `<select data-opt="busy">${[['few', 'A few'], ['usual', 'As the game would'], ['many', 'Crowded']].map(([v, l]) => `<option value="${v}" ${o.busy === v ? 'selected' : ''}>${l}</option>`).join('')}</select>`)}
      ${chRow('How hard', `<select data-opt="difficulty"><option value="auto" ${o.difficulty === 'auto' ? 'selected' : ''}>As the game has them</option>${CH_DIFF.map((d, n) => `<option value="${n}" ${String(o.difficulty) === String(n) ? 'selected' : ''}>${d}</option>`).join('')}</select>`, 'For levelled ones: how far up their list they go')}
      ${chRow('Highest level', `<input data-opt="max_level" value="${esc(o.max_level || '')}" placeholder="any" style="width:70px">`, 'Leaves out anyone fixed above this level; levelled ones follow the player')}
      ${chRow('', `<label title="Makes a list of everyone with a fixed level, and one of them to stand for it: the game picks by the player's level"><input type="checkbox" data-opt="levelled" ${o.levelled ? 'checked' : ''}> Levelled: make the fixed ones a levelled list</label>`)}
      ${chRow('', `<label title="A copy of each person of your own, with a Sandbox package here, and sleeping at night where there's a bed"><input type="checkbox" data-opt="live" ${o.live ? 'checked' : ''}> People live here: their own packages to stay and sleep here</label>`)}
    </div>
    <div class="acts" style="padding-left:0"><button class="btn primary" data-a="popgo">Suggest who</button></div>
    <div id="ch-plan"></div>`
    : `<p class="note" style="padding:16px 0">Open a place on the World page first (inside, or look at a square outside), then come back here.</p><button class="btn" data-a="poprefresh">Look again</button>`}`;
  box.querySelectorAll('[data-opt]').forEach(i => { if (i.tagName === 'INPUT' && i.type !== 'checkbox') i.oninput = () => { o[i.dataset.opt] = i.value; }; });
}
async function chPopPlan(){
  const o = CH.pop, p = CH.popPlace;
  const box = $('#ch-plan');
  box.innerHTML = '<div class="note" style="padding:10px 0">Reading the game\'s places…</div>';
  const d = await post('/api/char/populate/plan', {cell: p.cell, who: o.who, busy: o.busy, difficulty: o.difficulty, seed: o.seed, max_level: o.max_level || null});
  CH.plan = d;
  const lv = r => r.levelled ? 'Levelled' : r.mult ? `${r.level} × player` : 'Level ' + r.level;
  box.innerHTML = `${(d.notes || []).map(n => `<div class="ch-warn">${esc(n)}</div>`).join('')}
    ${d.rows.length ? `<div class="h" style="padding-left:0;margin-top:10px">Like ${esc(d.model)}</div>
    <p class="note" style="padding:0 0 6px">Learnt from ${d.learnt_n} place${d.learnt_n === 1 ? '' : 's'} like this: ${esc(d.learnt.join(', '))}${d.learnt_n > d.learnt.length ? '…' : ''}${d.area ? `. This one has about ${d.area} squares of floor.` : '.'}</p>
    <table><tr><th>How many</th><th>Who</th><th>Level</th><th>How hard</th><th></th></tr>${d.rows.map((r, n) => `<tr><td><input data-pc="${n}" value="${r.count}" style="width:60px"></td>
      <td>${esc(r.name)}<small style="display:block;color:var(--faint)">${esc(r.edid)}</small></td><td>${esc(lv(r))}</td>
      <td>${r.levelled ? `<select data-px="${n}"><option value="">As it is</option>${CH_DIFF.map((l, k) => `<option value="${k}" ${r.xlcm === k ? 'selected' : ''}>${l}</option>`).join('')}</select>` : ''}</td>
      <td class="note" style="padding:0">${r.kind === 'creature' ? 'creature' : r.aggression ? 'person, fights' : 'person'}</td></tr>`).join('')}</table>
    <div class="acts" style="padding-left:0;margin-top:8px"><button class="btn primary" data-a="popapply">Place them</button><button class="btn" data-a="popagain">Try another group</button></div>
    <p class="note" style="padding:0">Placing is one step: Undo takes it all back.${d.bed ? ' There\'s a bed here, so people who live here sleep at night.' : ''}</p>` : ''}`;
  box.querySelectorAll('[data-pc]').forEach(i => i.oninput = () => { const v = parseInt(i.value, 10); d.rows[+i.dataset.pc].count = isNaN(v) ? 0 : Math.max(0, Math.min(30, v)); });
  box.querySelectorAll('[data-px]').forEach(i => i.onchange = () => { d.rows[+i.dataset.px].xlcm = i.value === '' ? null : +i.value; });
}
async function chPopApply(){
  const o = CH.pop, d = CH.plan;
  const r = await post('/api/char/populate/apply', {cell: d.cell, rows: d.rows, live: o.live, levelled: o.levelled, difficulty: o.difficulty, seed: o.seed});
  if (r.note && !r.placed) return toast(r.note, true);
  setState(r.state);
  toast(`Placed ${r.placed}${r.note ? ': ' + r.note : ''}`);
  page('world');
  // (outside, the cell open is just the square under the view: go back out rather than open it as a place)
  if (A.outside){ const at = W.cam.position; goOutside(A.outside, {p: [at.x, at.y, at.z - 200]}); }
  else if (A.cellId === d.cell) openPlace(d.cell);
}
