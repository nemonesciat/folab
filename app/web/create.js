// ---------- Create: items in plain words ----------
// Kinds on the left, the items of one kind in the middle (yours first), the item on the right as a short form: name,
// damage, ammo, condition, value, weight, effects. A game item can be changed where it is (every copy in the game
// changes) or used to start a new one of your own. Behind it are the same records the Browse page edits.
const CR = {kind: 'WEAP', rows: [], key: null, data: null, rec: null, dirty: false, picks: {}};

const CR_KINDS = [
  ['WEAP', 'Weapons'], ['ARMO', 'Apparel'], ['ALCH', 'Aid'], ['AMMO', 'Ammo'],
  ['MISC', 'Misc items'], ['BOOK', 'Books'], ['NOTE', 'Notes'], ['KEYM', 'Keys'],
  ['-', 'What they carry'], ['CONT', 'Containers'], ['NPC_', 'Characters'], ['CREA', 'Creatures'],
  ['-', 'Levelled lists'], ['LVLI', 'Item lists'], ['LVLN', 'Character lists'], ['LVLC', 'Creature lists'],
];
const CR_ITEMS = new Set(['WEAP', 'ARMO', 'ALCH', 'AMMO', 'MISC', 'BOOK', 'NOTE', 'KEYM']);
// what an entry holds, and where a first entry goes (before the first of these subrecords; else at the end)
const CR_ENTRIES = {CONT: ['CNTO', ['DATA']], NPC_: ['CNTO', ['AIDT']], CREA: ['CNTO', ['AIDT']],
                    LVLI: ['LVLO', []], LVLN: ['LVLO', []], LVLC: ['LVLO', []]};
// what an entry can be, by the kind of record it's in
const CR_ENTRY_TYPES = {LVLN: 'NPC_ LVLN', LVLC: 'CREA LVLC'};
const CR_ITEM_TYPES = 'WEAP ARMO AMMO ALCH MISC BOOK NOTE KEYM LVLI';
const CR_LVLF = [[1, "Count every level up to the player's", "Pick from all entries at or below the player's level, not only the highest"],
                 [2, 'Each item in the count', 'With a count above 1, pick again for each one'], [4, 'Use all', 'Give every entry, not one of them']];
// [subrecord, field (null: the subrecord's own value), label, what it links to, note]
const CR_FIELDS = {
  WEAP: [['DATA', 'Damage', 'Damage', null, 'Per shot, before skill and condition'], ['DATA', 'Clip size', 'Rounds per clip'],
         ['NAM0', null, 'Ammo', 'AMMO'], ['DATA', 'Health', 'Condition', null, 'How much wear it takes before it breaks'],
         ['CRDT', 'Critical damage', 'Critical damage'], ['CRDT', 'Critical chance ×', 'Critical chance ×'],
         ['EITM', null, 'Effect on hit', 'ENCH'], ['WNAM', null, 'In your hands', 'STAT', 'The 1st-person model is a static of its own']],
  ARMO: [['DNAM', 'DT', 'Damage threshold (DT)'], ['DNAM', 'DR', 'Damage resistance (DR)'],
         ['DATA', 'Health', 'Condition'], ['EITM', null, 'Effect while worn', 'ENCH']],
  ALCH: [['ENIT', 'Addiction chance', 'Addiction chance', null, '0 to 1'], ['ENIT', 'Withdrawal effect', 'Addiction', 'SPEL']],
  AMMO: [['ONAM', null, 'Short name'], ['DAT2', 'Projectiles per shot', 'Projectiles per shot']],
  BOOK: [['DESC', null, 'Text', null, '', 'long']],
  MISC: [], KEYM: [], NOTE: [],
  LVLI: [['LVLD', 'Percent', 'Chance of nothing (%)', null, 'How often the list gives nothing at all']],
  LVLN: [['LVLD', 'Percent', 'Chance of nothing (%)']], LVLC: [['LVLD', 'Percent', 'Chance of nothing (%)']],
};
const CR_VALUE = {WEAP: ['DATA', 'Value'], ARMO: ['DATA', 'Value'], ALCH: ['ENIT', 'Value'], AMMO: ['DATA', 'Value'],
                  MISC: ['DATA', 'Value'], KEYM: ['DATA', 'Value'], BOOK: ['DATA', 'Value']};
const CR_WEIGHT = {WEAP: ['DATA', 'Weight'], ARMO: ['DATA', 'Weight'], ALCH: ['DATA', 'Weight'], AMMO: ['DAT2', 'Weight'],
                   MISC: ['DATA', 'Weight'], KEYM: ['DATA', 'Weight'], BOOK: ['DATA', 'Weight']};

function crInit(){
  $('#cr-kinds').innerHTML = CR_KINDS.map(([t, l]) => t === '-' ? `<div class="h">${l}</div>` : `<div class="row${t === CR.kind ? ' on' : ''}" data-t="${t}"><div>${l}</div></div>`).join('');
  crList();
}
$('#cr-kinds').addEventListener('click', e => {
  const r = e.target.closest('.row'); if (!r) return;
  if (CR.dirty && !confirm('Leave this item without saving your changes?')) return;
  CR.kind = r.dataset.t; CR.dirty = false; crInit();
});
let crTimer;
$('#cr-find').addEventListener('input', () => { clearTimeout(crTimer); crTimer = setTimeout(crList, 200); });

async function crList(){
  const token = CR.token = (CR.token || 0) + 1;
  const rows = await api(`/api/records?type=${CR.kind}&q=${encodeURIComponent($('#cr-find').value)}`);
  if (token !== CR.token) return;
  // (items with no name never show in game, so they're left out; lists never have names)
  CR.rows = CR_ITEMS.has(CR.kind) ? rows.filter(r => r.name || r.state) : rows;
  const mine = CR.rows.filter(r => r.state);
  const row = r => `<div class="row${r.key === CR.key ? ' on' : ''}" data-k="${esc(r.key)}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}" title="${r.state === 'new' ? 'your own' : 'changed by your mod'}"></span>` : ''}${esc(r.name || r.edid)}<small>${esc(r.edid)}</small></div></div>`;
  $('#cr-rows').innerHTML = (mine.length ? '<div class="h">Yours</div>' + mine.map(row).join('') + '<div class="h">The game\'s</div>' : '') +
    CR.rows.filter(r => !r.state).map(row).join('');
}
$('#cr-rows').addEventListener('click', e => { const r = e.target.closest('.row[data-k]'); if (r) crOpen(r.dataset.k); });

async function crOpen(key){
  if (CR.dirty && key !== CR.key && !confirm('Leave this item without saving your changes?')) return;
  const d = await api('/api/record?key=' + encodeURIComponent(key));
  CR.key = key; CR.data = d; CR.rec = JSON.parse(JSON.stringify(d.record)); CR.dirty = false; CR.picks = {};
  document.querySelectorAll('#cr-rows .row').forEach(r => r.classList.toggle('on', r.dataset.k === key));
  crDraw();
}

// ---------- reading and writing one field of the record ----------
function crSub(tag){ return CR.rec.subs.find(s => s.tag === tag); }
function crGet(tag, name){
  const s = crSub(tag); if (!s) return undefined;
  if (!name) return s.value;
  const f = (s.fields || []).find(f => f.name === name);
  return f ? f.value : undefined;
}
function crSet(tag, name, v){
  const s = crSub(tag); if (!s) return;
  if (!name) s.value = v; else s.fields.find(f => f.name === name).value = v;
}
function crCode(tag, name){
  const s = crSub(tag); if (!s) return null;
  if (!name) return s.kind;
  return ((s.fields || []).find(f => f.name === name) || {}).code;
}
const crNum = (v, code) => code === 'f' ? +(+v).toPrecision(6) : v;

function crInput(id, tag, name, label, link, note, long){
  const v = crGet(tag, name);
  if (v === undefined) return '';
  let input;
  if (link) input = `<input data-pick="${id}" data-type="${link}" data-key="${esc(v || '')}" value="${esc(crEdid(v))}" placeholder="none" list="cr-dl-${id}" autocomplete="off"><datalist id="cr-dl-${id}"></datalist><small>${esc(crName(v))}</small>`;
  else if (long) input = `<textarea data-in="${id}" rows="6">${esc(v)}</textarea>`;
  else input = `<input data-in="${id}" value="${esc(crNum(v, crCode(tag, name)))}">`;
  CR.picks[id] = {tag, name, link, label, code: crCode(tag, name)};
  return `<label>${esc(label)}</label><span>${input}${note ? `<small>${esc(note)}</small>` : ''}</span>`;
}

function crDraw(){
  const d = CR.data, rec = CR.rec, t = rec.type, mine = d.state === 'new';
  const kind = (CR_KINDS.find(k => k[0] === t) || [t, t])[1];
  let n = 0;
  const f = (tag, name, label, link, note, long) => crInput(n++, tag, name, label, link, note, long);
  const v = CR_VALUE[t], w = CR_WEIGHT[t];
  const effects = t === 'ALCH' ? crEffects() : CR_ENTRIES[t] ? crEntries() : '';
  const item = CR_ITEMS.has(t);
  $('#cr-detail').innerHTML = `
    <div class="bwtitle"><b>${esc(crGet('FULL') || crGet('EDID') || d.key)}</b>
      <small>${esc(kind)} · ${mine ? 'your own' : d.state === 'changed' ? 'the game\'s, changed by your mod' : 'the game\'s (' + esc(d.from) + ')'}</small></div>
    <div class="acts">
      <button class="btn primary" data-a="save" disabled>${mine ? 'Save' : 'Save changes to this one'}</button>
      ${mine ? '' : `<button class="btn primary" data-a="copy" title="A new one of your own, starting as a copy of this one; the game's stays as it is">＋ New ${item ? 'item' : 'one'} from this</button>`}
      ${item ? '<button class="btn" data-a="give" title="Start the game, load your newest save and put it in your inventory">Give it to me in game</button>' : ''}
      ${d.state === 'changed' ? '<button class="btn" data-a="revert">Put back as the game has it</button>' : ''}
      ${mine ? '<button class="btn" data-a="revert">Delete this item</button>' : ''}
      <button class="btn" data-a="browse" title="Every part of the record">Open in Browse</button>
    </div>
    ${mine ? '' : item ? `<div class="note" style="padding:4px 0 8px">Changing a game item changes it everywhere it is in the game. To keep it and make another, use <b>New item from this</b>.</div>`
      : `<div class="note" style="padding:4px 0 8px">Changes here change the game's own: everything that uses it gets them. A new one of your own is only used where you put it.</div>`}
    <div class="crgrid">
      ${f('FULL', null, 'Name')}
      ${f('EDID', null, 'Editor ID', null, 'The name scripts and the console use; no spaces')}
      ${(CR_FIELDS[t] || []).map(x => f(...x)).join('')}
      ${v ? f(v[0], v[1], 'Value (caps)') : ''}
      ${w ? f(w[0], w[1], 'Weight') : ''}

    </div>
    ${item ? crModels() : ''}
    ${effects}`;
  crBind();
  if (item) crPreview();
}

// ---------- aid effects: each is an effect (EFID), then its numbers (EFIT), then any conditions ----------
function crEffectGroups(){
  const out = [];
  CR.rec.subs.forEach((s, i) => { if (s.tag === 'EFID') out.push(i); });
  return out;
}
function crEffects(){
  const g = crEffectGroups();
  return `<div class="h" style="padding-left:0;margin-top:14px">Effects</div>
    <table class="crfx"><tr><th>Effect</th><th>Strength</th><th>Seconds</th><th></th></tr>
    ${g.map((si, n) => {
      const s = CR.rec.subs[si], it = CR.rec.subs[si + 1] && CR.rec.subs[si + 1].tag === 'EFIT' ? CR.rec.subs[si + 1] : null;
      const val = name => it ? it.fields.find(f => f.name === name).value : '';
      return `<tr><td><input data-fx="${si}" data-type="MGEF" data-key="${esc(s.value || '')}" value="${esc(crEdid(s.value))}" title="${esc(crName(s.value))}" list="cr-dl-fx${si}" autocomplete="off"><datalist id="cr-dl-fx${si}"></datalist>${crConds(si) ? ' <small class="note" title="The game&#39;s conditions on this effect are kept as they are">only sometimes</small>' : ''}</td>
        <td><input data-fxn="${si + 1}" data-name="Magnitude" value="${val('Magnitude')}" style="width:70px"></td>
        <td><input data-fxn="${si + 1}" data-name="Duration" value="${val('Duration')}" style="width:70px"></td>
        <td><button class="btn" data-fxdel="${n}" title="Take this effect off">✕</button></td></tr>`;
    }).join('')}</table>
    ${g.length ? '<button class="btn" data-a="fxadd" style="margin-top:6px">＋ Add an effect</button>' : ''}`;
}

// a link's label is 'EditorID — Name (TYPE)'
function crEdid(k){ return k ? (CR.data.links[k] || k).split(' (')[0].split(' — ')[0] : ''; }
const CR_KINDNAME = {LVLI: 'a levelled item list', LVLN: 'a levelled character list', LVLC: 'a levelled creature list', FLST: 'a list of forms', STAT: 'a static'};
function crName(k){
  const l = k ? CR.data.links[k] || '' : '';
  if (l.includes(' — ')) return l.split(' — ')[1].replace(/ \([A-Z_]{4}\)$/, '');
  const t = (l.match(/\(([A-Z_]{4})\)$/) || [])[1];
  return t ? CR_KINDNAME[t] || t : '';
}
function crConds(si){ let n = si + 1; while (CR.rec.subs[n] && CR.rec.subs[n].tag === 'EFIT') n++; return CR.rec.subs[n] && CR.rec.subs[n].tag === 'CTDA'; }

// ---------- inventories and levelled lists: entries (CNTO or LVLO), each maybe followed by COED (owner, condition) ----------
function crEntryGroups(){
  const tag = CR_ENTRIES[CR.rec.type][0], out = [];
  CR.rec.subs.forEach((s, i) => { if (s.tag === tag) out.push(i); });
  return out;
}
function crGroupEnd(at){ let e = at + 1; while (CR.rec.subs[e] && CR.rec.subs[e].tag === 'COED') e++; return e; }
function crEntries(){
  const t = CR.rec.type, lv = t.startsWith('LVL'), g = crEntryGroups();
  const fv = (s, n) => (s.fields.find(f => f.name === n) || {}).value;
  const flags = lv ? crGet('LVLF', 'Flags') : undefined;
  return `${flags !== undefined ? `<div class="crflags">${CR_LVLF.map(([b, l, tip]) => `<label title="${esc(tip)}"><input type="checkbox" data-flag="${b}" ${flags & b ? 'checked' : ''}> ${esc(l)}</label>`).join('')}</div>` : ''}
    <div class="h" style="padding-left:0;margin-top:14px">${lv ? 'Entries' : 'Carries'} · ${g.length}</div>
    <table class="crfx"><tr>${lv ? '<th>From level</th>' : ''}<th>Editor ID</th><th></th><th>How many</th><th></th></tr>
    ${g.map((si, n) => {
      const s = CR.rec.subs[si], k = s.fields.find(f => f.code === 'F').value, extra = crGroupEnd(si) > si + 1;
      return `<tr>${lv ? `<td><input data-entn="${si}" data-name="Level" value="${fv(s, 'Level')}" style="width:60px"></td>` : ''}
        <td><input data-ent="${si}" data-type="${CR_ENTRY_TYPES[t] || CR_ITEM_TYPES}" data-key="${esc(k || '')}" value="${esc(crEdid(k))}" list="cr-dl-e${si}" autocomplete="off" style="width:240px"><datalist id="cr-dl-e${si}"></datalist></td>
        <td class="note" style="padding:0 8px 0 0;max-width:260px">${esc(crName(k))}${extra ? ' <small title="Its owner or condition, kept as the game has it">· with owner/condition</small>' : ''}</td>
        <td><input data-entn="${si}" data-name="Count" value="${fv(s, 'Count')}" style="width:60px"></td>
        <td><button class="btn" data-entdel="${n}" title="Take this out">✕</button></td></tr>`;
    }).join('')}</table>
    <button class="btn" data-a="entadd" style="margin-top:6px">＋ Add</button>
    ${lv ? `<p class="note" style="padding:6px 0 0">The game picks among the entries whose level is at or below the player's; FOLab keeps them in level order.</p>` : ''}`;
}
function crNewEntry(){
  const t = CR.rec.type, lv = t.startsWith('LVL'), g = crEntryGroups();
  if (g.length){
    const e = JSON.parse(JSON.stringify(CR.rec.subs[g[g.length - 1]]));
    e.fields.forEach(f => { if (f.code === 'F') f.value = ''; if (f.name === 'Count') f.value = 1; if (f.pad !== undefined) f.pad = f.pad.replace(/./g, '0'); });
    return e;
  }
  const item = {LVLI: 'Item', LVLN: 'Character', LVLC: 'Creature'}[t];
  return lv ? {tag: 'LVLO', label: 'Entry', kind: 'struct', fields: [{name: 'Level', code: 'h', value: 1}, {pad: '0000'},
                {name: item, code: 'F', value: ''}, {name: 'Count', code: 'h', value: 1}, {pad: '0000'}]}
            : {tag: 'CNTO', label: 'Item', kind: 'struct', fields: [{name: 'Item', code: 'F', value: ''}, {name: 'Count', code: 'i', value: 1}]};
}
function crSortLevels(){
  // levelled list entries in level order (each with its COED), in the place the first one was
  if (!CR.rec.type.startsWith('LVL')) return;
  const g = crEntryGroups(); if (!g.length) return;
  const inGroup = i => g.some(at => i >= at && i < crGroupEnd(at));
  const groups = g.map(at => CR.rec.subs.slice(at, crGroupEnd(at)));
  groups.sort((a, b) => a[0].fields[0].value - b[0].fields[0].value);
  const keep = CR.rec.subs.filter((s, i) => !inGroup(i));
  const first = g[0] - CR.rec.subs.slice(0, g[0]).filter((s, i) => inGroup(i)).length;
  keep.splice(first, 0, ...groups.flat());
  CR.rec.subs = keep;
}

// ---------- models: each slot a path under meshes\, previewed turning; Change… opens the picker ----------
// (a model's texture list (MODT and kin) and alternate textures (MODS) describe that one mesh, so they go with it)
const CR_MODELS = {ARMO: [['MOD2', 'On the ground'], ['MODL', 'Worn (male)'], ['MOD4', 'On the ground (female)'], ['MOD3', 'Worn (female)']]};
const CR_MODEL_DATA = {MODL: ['MODT', 'MODS'], MOD2: ['MO2T', 'MO2S'], MOD3: ['MO3T', 'MO3S'], MOD4: ['MO4T', 'MO4S']};
function crModelSlots(){ return (CR_MODELS[CR.rec.type] || [['MODL', 'In the world']]).filter(([t]) => crSub(t)); }
function crModels(){
  const slots = crModelSlots();
  if (!slots.length) return '';
  CR.shown = slots.some(([t]) => t === CR.shown) ? CR.shown : slots[0][0];
  return `<div class="h" style="padding-left:0;margin-top:14px">Model</div>
    <div class="crmodels"><div id="cr-view" title="The model, turning"></div>
      <div class="crslots">${slots.map(([t, l]) => `<div class="crslot${t === CR.shown ? ' on' : ''}" data-slot="${t}">
        <label>${esc(l)}</label><span class="crmodel">${esc(crGet(t) || 'none')}</span>
        <button class="btn" data-change="${t}">Change…</button></div>`).join('')}
        <p class="note" style="padding:6px 0 0">The first one also sets the size the game gives it in the world.</p></div></div>`;
}
async function crPreview(){
  const el = $('#cr-view'); if (!el) return;
  await mpShow(el, crGet(CR.shown));
  if (el.dataset.empty) el.innerHTML = '<div class="note" style="padding:20px">Nothing to draw</div>';
}
function crSetModel(tag, path, bounds){
  const s = crSub(tag), at = CR.rec.subs.indexOf(s);
  s.value = path;
  let n = at + 1;
  while (CR.rec.subs[n] && CR_MODEL_DATA[tag].includes(CR.rec.subs[n].tag)) CR.rec.subs.splice(n, 1);
  // the world model's size is the item's bounds (what the game uses to place and pick it up)
  const ob = crSub('OBND');
  if (bounds && ob && tag === crModelSlots()[0][0])
    ['X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'].forEach((k, i) => { ob.fields.find(f => f.name === k).value = Math.max(-32768, Math.min(32767, bounds[i])); });
}

function crDirty(){ CR.dirty = true; const b = $('#cr-detail [data-a="save"]'); if (b) b.disabled = false; }

// (the Characters page uses the inventory editor too: its own box, its own idea of what's unsaved)
function crBind(box = $('#cr-detail'), dirty = crDirty){
  box.querySelectorAll('[data-in]').forEach(i => i.oninput = dirty);
  box.querySelectorAll('[data-fxn]').forEach(i => i.oninput = dirty);
  box.querySelectorAll('[data-entn]').forEach(i => i.oninput = dirty);
  box.querySelectorAll('[data-flag]').forEach(i => i.onchange = dirty);
  box.querySelectorAll('[data-ent]').forEach(i => {
    let timer;
    i.oninput = () => {
      dirty(); i._touched = true;
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const r = await api('/api/resolve?q=' + encodeURIComponent(i.value));
        i._hits = (r.hits || []).map(h => ({key: h.key, edid: h.label.split(/[ (]/)[0], name: h.label}));
        i.nextElementSibling.innerHTML = i._hits.map(h => `<option value="${esc(h.edid)}">${esc(h.name)}</option>`).join('');
      }, 180);
    };
  });
  box.querySelectorAll('[data-pick],[data-fx]').forEach(i => {
    let timer;
    i.oninput = () => {
      dirty(); i._touched = true;
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const rows = await api(`/api/records?type=${i.dataset.type}&q=${encodeURIComponent(i.value)}`);
        i._hits = rows.slice(0, 40);
        i.nextElementSibling.innerHTML = i._hits.map(r => `<option value="${esc(r.edid)}">${esc(r.name)}</option>`).join('');
      }, 180);
    };
  });
}

async function crResolve(i){
  // an editor ID typed or picked in a link box, as a form key ('' for none); a box nobody touched keeps its link
  if (!i._touched) return i.dataset.key;
  const v = i.value.trim();
  if (!v) return '';
  const hit = (i._hits || []).find(r => r.edid.toLowerCase() === v.toLowerCase());
  if (hit){ if (!CR.data.links[hit.key]) CR.data.links[hit.key] = hit.name && hit.name.includes(" — ") ? hit.name : hit.name ? `${hit.edid} — ${hit.name}` : hit.edid; return hit.key; }
  // (each kind it can be, asked at once; these lists don't wait for the editor ID index)
  const rows = (await Promise.all(i.dataset.type.split(' ').map(t => api(`/api/records?type=${t}&q=${encodeURIComponent(v)}`)))).flat();
  const r = rows.find(r => r.edid.toLowerCase() === v.toLowerCase());
  if (r){ CR.data.links[r.key] = r.name ? `${r.edid} — ${r.name}` : r.edid; return r.key; }
  // (some links take other kinds too, as a weapon's ammo can be a list of ammo)
  const any = await api('/api/resolve?q=' + encodeURIComponent(v));
  const found = (any.hits || []).find(h => h.label.split(/[ (]/)[0].toLowerCase() === v.toLowerCase());
  if (!found) throw new Error(any.busy ? "FOLab is still reading the game's editor IDs: try again in a moment." : `Nothing has the editor ID "${v}"`);
  CR.data.links[found.key] = found.label;
  return found.key;
}

function crRead(box = $('#cr-detail')){
  // the form's values into CR.rec (throws on a bad number or an unknown link)
  return (async () => {
    for (const i of box.querySelectorAll('[data-in]')){
      const p = CR.picks[i.dataset.in], raw = i.value;
      if (p.code === 'z' || p.code === undefined || p.code === null){ crSet(p.tag, p.name, raw); continue; }
      const num = p.code === 'f' ? parseFloat(raw) : parseInt(raw, 10);
      if (isNaN(num)) throw new Error(`${p.label}: "${raw}" isn't a number`);
      crSet(p.tag, p.name, num);
    }
    for (const i of box.querySelectorAll('[data-pick]')){
      const p = CR.picks[i.dataset.pick];
      crSet(p.tag, p.name, await crResolve(i));
    }
    for (const i of box.querySelectorAll('[data-fx]')) CR.rec.subs[+i.dataset.fx].value = await crResolve(i);
    for (const i of box.querySelectorAll('[data-fxn]')){
      const n = parseInt(i.value, 10);
      if (isNaN(n) || n < 0) throw new Error(`${i.dataset.name}: "${i.value}" isn't a whole number`);
      CR.rec.subs[+i.dataset.fxn].fields.find(f => f.name === i.dataset.name).value = n;
    }
    for (const i of box.querySelectorAll('[data-ent]')){
      const f = CR.rec.subs[+i.dataset.ent].fields.find(f => f.code === 'F');
      f.value = await crResolve(i);
      if (!f.value) throw new Error('An entry has nothing in it: pick something, or take it out with ✕');
    }
    for (const i of box.querySelectorAll('[data-entn]')){
      const n = parseInt(i.value, 10), lo = i.dataset.name === 'Count' ? 1 : 0;
      if (isNaN(n) || n < lo || n > 32767) throw new Error(`${i.dataset.name}: "${i.value}" isn't a whole number from ${lo} up`);
      CR.rec.subs[+i.dataset.entn].fields.find(f => f.name === i.dataset.name).value = n;
    }
    const fl = box.querySelectorAll('[data-flag]');
    if (fl.length){ let v = crGet('LVLF', 'Flags') & ~7; fl.forEach(c => { if (c.checked) v |= +c.dataset.flag; }); crSet('LVLF', 'Flags', v); }
    const edid = crGet('EDID');
    if (!/^[A-Za-z0-9_]+$/.test(edid || '')) throw new Error('Editor ID: letters, digits and _ only');
  })();
}

$('#cr-detail').addEventListener('click', async e => {
  const del = e.target.closest('[data-fxdel]');
  if (del){
    try { await crRead(); } catch (err){ return fail(err); }      // (keep what was typed: the form is drawn again)
    const g = crEffectGroups(), at = g[+del.dataset.fxdel];
    if (g.length < 2) return toast('Aid needs at least one effect', true);
    let end = at + 1;
    while (end < CR.rec.subs.length && ['EFIT', 'CTDA'].includes(CR.rec.subs[end].tag)) end++;
    CR.rec.subs.splice(at, end - at);
    crDraw(); crDirty(); return;
  }
  const edel = e.target.closest('[data-entdel]');
  if (edel){
    try { await crRead(); } catch (err){ return fail(err); }
    const at = crEntryGroups()[+edel.dataset.entdel];
    CR.rec.subs.splice(at, crGroupEnd(at) - at);
    crDraw(); crDirty(); return;
  }
  const slot = e.target.closest('[data-slot]'), change = e.target.closest('[data-change]');
  if (change){
    const tag = change.dataset.change;
    mpPick(crGet(tag), async (path, bounds) => {
      try { await crRead(); } catch (err){ return fail(err); }
      crSetModel(tag, path, bounds); CR.shown = tag;
      crDraw(); crDirty();
    });
    return;
  }
  if (slot && slot.dataset.slot !== CR.shown){
    CR.shown = slot.dataset.slot;
    document.querySelectorAll('.crslot').forEach(r => r.classList.toggle('on', r.dataset.slot === CR.shown));
    return crPreview();
  }
  const a = e.target.dataset.a; if (!a) return;
  if (a === 'entadd'){
    try { await crRead(); } catch (err){ return fail(err); }
    const g = crEntryGroups(), before = CR_ENTRIES[CR.rec.type][1];
    let at = g.length ? crGroupEnd(g[g.length - 1]) : CR.rec.subs.findIndex(s => before.includes(s.tag));
    if (at < 0) at = CR.rec.subs.length;
    CR.rec.subs.splice(at, 0, crNewEntry());
    crDraw(); crDirty();
    const box = document.querySelector(`#cr-detail [data-ent="${at}"]`);
    if (box) box.focus();
    return;
  }
  try {
    if (a === 'fxadd'){
      await crRead();
      // a copy of the last effect (without its conditions), after it
      const g = crEffectGroups(), at = g[g.length - 1];
      let end = at + 1;
      while (end < CR.rec.subs.length && ['EFIT', 'CTDA'].includes(CR.rec.subs[end].tag)) end++;
      const add = JSON.parse(JSON.stringify(CR.rec.subs.slice(at, at + 2).filter(s => s.tag !== 'CTDA')));
      CR.rec.subs.splice(end, 0, ...add);
      crDraw(); crDirty(); return;
    }
    if (a === 'save'){
      await crRead();
      crSortLevels();
      const d = await post('/api/record/save', {key: CR.key, record: CR.rec});
      setState(d.state); CR.dirty = false;
      if (typeof recCacheDrop === 'function') recCacheDrop(CR.key);
      toast('Saved in your mod'); await crList(); return crOpen(CR.key);
    }
    if (a === 'copy'){
      if (CR.dirty && !confirm('Your changes here go into the new item, and this one stays as the game has it. Go on?')) return;
      if (CR.dirty) await crRead();
      const r = await post('/api/record/copy', {key: CR.key});
      const key = r.made[0];
      if (CR.dirty){
        // the copy, with the changes made here (keeping the copy's own editor ID unless one was typed)
        const made = await api('/api/record?key=' + encodeURIComponent(key));
        if (crGet('EDID') === (CR.data.record.subs.find(s => s.tag === 'EDID') || {}).value)
          crSet('EDID', null, made.record.subs.find(s => s.tag === 'EDID').value);
        const s = await post('/api/record/save', {key, record: CR.rec});
        setState(s.state);
      } else setState(r.state);
      CR.dirty = false; await crList(); await crOpen(key);
      toast('A new item of your own: give it a name');
      const name = $('#cr-detail [data-in="0"]'); if (name){ name.focus(); name.select(); }
      return;
    }
    if (a === 'revert'){
      const mine = CR.data.state === 'new';
      if (!confirm(mine ? 'Delete this item of yours?' : 'Put this item back as the game has it?')) return;
      const r = await post('/api/record/revert', {key: CR.key});
      setState(r.state); CR.dirty = false; await crList();
      if (mine){ CR.key = null; $('#cr-detail').innerHTML = ''; } else crOpen(CR.key);
      return;
    }
    if (a === 'browse'){ page('browse'); await browseInit(); return bwOpen(CR.key); }
    if (a === 'give') return crGive();
  } catch (err){ fail(err); }
});

async function crGive(){
  if (CR.dirty) return toast('Save your changes first', true);
  const n = prompt('How many?', CR.rec.type === 'AMMO' ? '100' : '1');
  if (n === null) return;
  const count = parseInt(n, 10);
  if (!(count > 0)) return toast('A number above 0, please', true);
  const r = await post('/api/give', {key: CR.key, count});
  setState(r.state);
  toast(r.message || 'Starting New Vegas: it will be in your inventory once your save loads');
}
