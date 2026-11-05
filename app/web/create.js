// ---------- Create: items in plain words ----------
// Kinds on the left, the items of one kind in the middle (yours first), the item on the right as a short form: name,
// damage, ammo, condition, value, weight, effects. A game item can be changed where it is (every copy in the game
// changes) or used to start a new one of your own. Behind it are the same records the Browse page edits.
const CR = {kind: 'WEAP', rows: [], key: null, data: null, rec: null, dirty: false, picks: {}};

const CR_KINDS = [
  ['WEAP', 'Weapons'], ['ARMO', 'Apparel'], ['ALCH', 'Aid'], ['AMMO', 'Ammo'],
  ['MISC', 'Misc items'], ['BOOK', 'Books'], ['NOTE', 'Notes'], ['KEYM', 'Keys'],
];
// [subrecord, field (null: the subrecord's own value), label, what it links to, note]
const CR_FIELDS = {
  WEAP: [['DATA', 'Damage', 'Damage', null, 'Per shot, before skill and condition'], ['DATA', 'Clip size', 'Rounds per clip'],
         ['NAM0', null, 'Ammo', 'AMMO'], ['DATA', 'Health', 'Condition', null, 'How much wear it takes before it breaks'],
         ['CRDT', 'Critical damage', 'Critical damage'], ['CRDT', 'Critical chance ×', 'Critical chance ×'],
         ['EITM', null, 'Effect on hit', 'ENCH']],
  ARMO: [['DNAM', 'DT', 'Damage threshold (DT)'], ['DNAM', 'DR', 'Damage resistance (DR)'],
         ['DATA', 'Health', 'Condition'], ['EITM', null, 'Effect while worn', 'ENCH']],
  ALCH: [['ENIT', 'Addiction chance', 'Addiction chance', null, '0 to 1'], ['ENIT', 'Withdrawal effect', 'Addiction', 'SPEL']],
  AMMO: [['ONAM', null, 'Short name'], ['DAT2', 'Projectiles per shot', 'Projectiles per shot']],
  BOOK: [['DESC', null, 'Text', null, '', 'long']],
  MISC: [], KEYM: [], NOTE: [],
};
const CR_VALUE = {WEAP: ['DATA', 'Value'], ARMO: ['DATA', 'Value'], ALCH: ['ENIT', 'Value'], AMMO: ['DATA', 'Value'],
                  MISC: ['DATA', 'Value'], KEYM: ['DATA', 'Value'], BOOK: ['DATA', 'Value']};
const CR_WEIGHT = {WEAP: ['DATA', 'Weight'], ARMO: ['DATA', 'Weight'], ALCH: ['DATA', 'Weight'], AMMO: ['DAT2', 'Weight'],
                   MISC: ['DATA', 'Weight'], KEYM: ['DATA', 'Weight'], BOOK: ['DATA', 'Weight']};

function crInit(){
  $('#cr-kinds').innerHTML = CR_KINDS.map(([t, l]) => `<div class="row${t === CR.kind ? ' on' : ''}" data-t="${t}"><div>${l}</div></div>`).join('');
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
  CR.rows = rows.filter(r => r.name || r.state);        // (things with no name never show in game; yours always do)
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
  const effects = t === 'ALCH' ? crEffects() : '';
  $('#cr-detail').innerHTML = `
    <div class="bwtitle"><b>${esc(crGet('FULL') || crGet('EDID') || d.key)}</b>
      <small>${esc(kind)} · ${mine ? 'your own' : d.state === 'changed' ? 'the game\'s, changed by your mod' : 'the game\'s (' + esc(d.from) + ')'}</small></div>
    <div class="acts">
      <button class="btn primary" data-a="save" disabled>${mine ? 'Save' : 'Save changes to this one'}</button>
      ${mine ? '' : '<button class="btn primary" data-a="copy" title="A new item of your own, starting as a copy of this one; the game\'s stays as it is">＋ New item from this</button>'}
      <button class="btn" data-a="give" title="Start the game, load your newest save and put it in your inventory">Give it to me in game</button>
      ${d.state === 'changed' ? '<button class="btn" data-a="revert">Put back as the game has it</button>' : ''}
      ${mine ? '<button class="btn" data-a="revert">Delete this item</button>' : ''}
      <button class="btn" data-a="browse" title="Every part of the record">Open in Browse</button>
    </div>
    ${mine ? '' : `<div class="note" style="padding:4px 0 8px">Changing a game item changes it everywhere it is in the game. To keep it and make another, use <b>New item from this</b>.</div>`}
    <div class="crgrid">
      ${f('FULL', null, 'Name')}
      ${f('EDID', null, 'Editor ID', null, 'The name scripts and the console use; no spaces')}
      ${(CR_FIELDS[t] || []).map(x => f(...x)).join('')}
      ${v ? f(v[0], v[1], 'Value (caps)') : ''}
      ${w ? f(w[0], w[1], 'Weight') : ''}
      ${crGet('MODL') !== undefined ? `<label>Model</label><span class="crmodel">${esc(crGet('MODL'))}</span>` : ''}
    </div>
    ${effects}`;
  crBind();
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
function crName(k){ const l = k ? CR.data.links[k] || '' : ''; return l.includes(' — ') ? l.split(' — ')[1].replace(/ \([A-Z_]{4}\)$/, '') : ''; }
function crConds(si){ let n = si + 1; while (CR.rec.subs[n] && CR.rec.subs[n].tag === 'EFIT') n++; return CR.rec.subs[n] && CR.rec.subs[n].tag === 'CTDA'; }

function crDirty(){ CR.dirty = true; const b = $('#cr-detail [data-a="save"]'); if (b) b.disabled = false; }

function crBind(){
  const box = $('#cr-detail');
  box.querySelectorAll('[data-in]').forEach(i => i.oninput = crDirty);
  box.querySelectorAll('[data-fxn]').forEach(i => i.oninput = crDirty);
  box.querySelectorAll('[data-pick],[data-fx]').forEach(i => {
    let timer;
    i.oninput = () => {
      crDirty(); i._touched = true;
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
  if (hit) return hit.key;
  const rows = await api(`/api/records?type=${i.dataset.type}&q=${encodeURIComponent(v)}`);
  const r = rows.find(r => r.edid.toLowerCase() === v.toLowerCase());
  if (r) return r.key;
  // (some links take other kinds too, as a weapon's ammo can be a list of ammo)
  const any = await api('/api/resolve?q=' + encodeURIComponent(v));
  const found = (any.hits || []).find(h => h.label.split(/[ (]/)[0].toLowerCase() === v.toLowerCase());
  if (!found) throw new Error(any.busy ? "FOLab is still reading the game's editor IDs: try again in a moment." : `Nothing has the editor ID "${v}"`);
  return found.key;
}

function crRead(){
  // the form's values into CR.rec (throws on a bad number or an unknown link)
  const box = $('#cr-detail');
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
  const a = e.target.dataset.a; if (!a) return;
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
