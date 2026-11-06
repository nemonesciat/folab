// ---------- Scripts page, the comforts: colours, what the word under the cursor is, the list of commands, completing ----------
// Loaded after scripts.js. The language comes from the table made from the game's own program, plus FOLab's notes.

// colours: what each word is, from the game's table, this script's variables, and what the last good compile found
function scrKnown(){
  const vars = new Set(), refs = new Map();
  for (const m of SCR.text.matchAll(/^[ \t]*(?:short|int|long|float|ref|reference)[ \t]+([A-Za-z_]\w*)/gim)) vars.add(m[1].toLowerCase());
  for (const r of (SCR.lastGood || {refs: []}).refs) if (r.key) refs.set(r.name.toLowerCase(), r);
  return {vars, refs};
}
function scrColour(line, known){
  let out = '', i = 0, prev = '';
  const n = line.length, I = SCR.info;
  while (i < n){
    const c = line[i];
    if (c === ';'){ out += `<span class="c-com">${esc(line.slice(i))}</span>`; break; }
    if (c === '"'){
      const j = line.indexOf('"', i + 1), end = j < 0 ? n : j + 1;
      out += `<span class="c-str">${esc(line.slice(i, end))}</span>`; i = end; continue;
    }
    const m = /^[A-Za-z_]\w*/.exec(line.slice(i));
    if (m){
      const w = m[0], low = w.toLowerCase();
      const cls = !I ? '' : I.kw.has(low) ? 'c-kw' : prev === 'begin' && I.blk[low] ? 'c-blk' : known.vars.has(low) ? 'c-var' : known.refs.has(low) ? 'c-ref' : I.fn[low] ? 'c-fn' : '';
      out += cls ? `<span class="${cls}">${esc(w)}</span>` : esc(w);
      i += w.length; prev = low; continue;
    }
    const num = /^\d+(\.\d*)?/.exec(line.slice(i));
    if (num){ out += `<span class="c-num">${num[0]}</span>`; i += num[0].length; continue; }
    out += esc(c); i++;
  }
  return out;
}

async function scrLoadInfo(){
  if (SCR.info) return SCR.info;
  const d = await scrGet('/api/scripts/info');
  d.fn = {}; d.blk = {}; d.kw = new Set(d.keywords);
  for (const f of d.functions){ d.fn[f.name.toLowerCase()] = f; if (f.short) d.fn[f.short.toLowerCase()] = f; }
  for (const b of d.blocks) d.blk[b.name.toLowerCase()] = b;
  SCR.info = d;
  scrCommands();
  if (SCR.key && $('#sc-hl')) scrPaint();
  return d;
}
function scrSig(f, block){
  const ps = (f.params || []).map(p => p.opt ? `[${p.name}]` : p.name).join(' ');
  return `${block ? 'Begin ' : f.ref ? 'thing.' : ''}${f.name}${ps ? ' ' + ps : ''}`;
}
function scrWordAt(text, at){
  let a = at, b = at;
  while (a > 0 && /\w/.test(text[a - 1])) a--;
  while (b < text.length && /\w/.test(text[b])) b++;
  return text.slice(a, b);
}

// ---------- the list of commands ----------
function scrCommands(){
  const box = $('#sc-cmds'), I = SCR.info; if (!box || !I) return;
  const q = $('#sc-cq').value.trim().toLowerCase();
  const hit = x => !q || x.name.toLowerCase().includes(q) || (x.short || '').toLowerCase().includes(q) || (x.doc || '').toLowerCase().includes(q);
  const row = x => `<div class="row" data-cmd="${esc(x.name)}"><div>${esc(x.name)}${x.doc ? `<small>${esc(x.doc)}</small>` : ''}</div></div>`;
  const blocks = I.blocks.filter(hit), funcs = I.functions.filter(hit).sort((a, b) => !a.doc - !b.doc || a.name.localeCompare(b.name));
  box.innerHTML = (blocks.length ? `<div class="h">Blocks: when it runs</div>${blocks.map(row).join('')}` : '') +
    (funcs.length ? `<div class="h">Commands${q ? '' : ': the common ones first'}</div>${funcs.map(row).join('')}` : '') +
    (!blocks.length && !funcs.length ? '<div class="note">Nothing matches. xNVSE\'s commands aren\'t known here yet.</div>' : '');
}
let scrCqT;
$('#sc-cq').addEventListener('input', () => { clearTimeout(scrCqT); scrCqT = setTimeout(scrCommands, 150); });
$('#sc-cmds').addEventListener('click', e => { const r = e.target.closest('[data-cmd]'); if (r) scrHelpFor(r.dataset.cmd, true); });

// ---------- what the word under the cursor is ----------
const SCR_WORDS = {
  scn: 'The script\'s name: the first line of every script.', scriptname: 'The script\'s name: the first line of every script.',
  begin: 'Starts a block, saying when it runs. Every Begin has an End.', end: 'Ends a Begin block.',
  short: 'Declares a whole-number variable.', int: 'Declares a whole-number variable.', long: 'Declares a whole-number variable.',
  float: 'Declares a variable that can hold fractions.', ref: 'Declares a variable holding something in the world.',
  reference: 'Declares a variable holding something in the world.', set: 'Gives a variable a value: set n to n + 1', to: 'Part of set: set n to 1',
  if: 'Runs what follows only if this is true. Ends with endif.', elseif: 'Otherwise, if this is true.', else: 'Otherwise.', endif: 'Ends an if.',
  return: 'Stops the script here until its next run.',
};
let scrHereWord = '';
function scrHereSoon(){
  const ta = $('#sc-ta'); if (!ta) return;
  const w = scrWordAt(ta.value, ta.selectionStart);
  if (w && w !== scrHereWord){ scrHereWord = w; scrHelpFor(w); }
}
function scrHelpFor(word, fromList){
  const I = SCR.info, low = word.toLowerCase(), box = $('#sc-here'); if (!I || !box) return;
  const known = scrKnown(), r = known.refs.get(low), f = I.fn[low], b = I.blk[low];
  let html = '';
  if (known.vars.has(low) && !fromList) html = `<code>${esc(word)}</code><p>A variable of this script: it holds its value between runs and is kept in the player's save.</p>`;
  else if (I.kw.has(low)) html = `<code>${esc(word)}</code><p>${esc(SCR_WORDS[low] || '')}</p>`;
  else if (r && !fromList) html = `<code>${esc(word)}</code><p>A ${esc(r.tag)}, ${r.key.startsWith('+') ? 'your own' : 'from ' + esc(r.key.split(':')[0])}.</p><div class="acts"><button class="btn" data-open="${esc(r.key)}">Open its record</button></div>`;
  else if (f && (!b || fromList !== 'block')) html = `<code>${esc(scrSig(f))}</code>${f.short ? `<p>Short form: <code>${esc(f.short)}</code></p>` : ''}<p>${esc(f.doc || 'No notes for this one yet: see how the game\'s scripts use it.')}</p>${f.ref ? `<p>Works on this script's own thing, or on another: <code>player.${esc(f.name)}</code></p>` : ''}`;
  else if (b) html = `<code>${esc(scrSig(b, true))}</code><p>${esc(b.doc || 'A block: when what\'s in it runs.')}</p>`;
  else if (!fromList) html = `<code>${esc(word)}</code><p>Not a command or variable. It might be the editor ID of something.</p>`;
  if (!html) return;
  box.innerHTML = html + `<div class="acts">${fromList && SCR.key ? `<button class="btn" data-ins="${esc(word)}">Put it in the script</button>` : ''}<button class="btn" data-used="${esc(word)}" title="Every script that has this word">Where it's used</button></div><div id="sc-usedin"></div>`;
}
$('#sc-here').addEventListener('click', async e => {
  const t = e.target;
  if (t.dataset.open) return openRecord(t.dataset.open);
  if (t.dataset.ins) return scrInsert(t.dataset.ins + ' ');
  if (t.dataset.used){
    const box = $('#sc-usedin');
    box.innerHTML = '<div class="note" style="padding:4px 0">Looking through every script…</div>';
    try {
      const u = await scrGet('/api/scripts/usedin?word=' + encodeURIComponent(t.dataset.used));
      box.innerHTML = `<div class="h" style="padding:8px 0 3px">In ${u.total} script${u.total === 1 ? '' : 's'}</div>` + u.rows.map(r => `<div class="row" data-k="${esc(r.key)}" data-line="${r.line}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}"></span>` : ''}${esc(r.edid)}<small>${r.line}: ${esc(r.text)}</small></div></div>`).join('');
    } catch (err){ box.innerHTML = `<div class="note">${esc(err.message)}</div>`; }
    return;
  }
  const r = t.closest('[data-line]');
  if (r){ await scrOpen(r.dataset.k); scrGoLine(+r.dataset.line); }
});

// ---------- completing as you type: functions, blocks, this script's variables, editor IDs ----------
const SCRPOP = {items: [], at: 0, start: 0, token: 0};
function scrPopClose(){ const p = $('#sc-pop'); if (p) p.remove(); SCRPOP.items = []; SCRPOP.token++; }
function scrPopSoon(){
  const ta = $('#sc-ta'), I = SCR.info;
  scrPopClose();
  if (!ta || !I || ta.selectionStart !== ta.selectionEnd) return;
  const caret = ta.selectionStart, before = ta.value.slice(0, caret), line = before.slice(before.lastIndexOf('\n') + 1);
  if (line.includes(';') || (line.match(/"/g) || []).length % 2) return;     // (not inside a comment or quotes)
  const m = /[A-Za-z_]\w*$/.exec(line);
  if (!m || m[0].length < 2) return;
  const word = m[0], low = word.toLowerCase(), start = caret - word.length, head = line.slice(0, line.length - word.length);
  const afterDot = /\.$/.test(head), afterBegin = /^\s*begin\s+$/i.test(head);
  const items = [], seen = new Set();
  const add = (name, note, tail) => { const k = name.toLowerCase(); if (!seen.has(k) && k !== low){ seen.add(k); items.push({name, note, tail}); } };
  const starts = n => n.toLowerCase().startsWith(low), has = n => n.toLowerCase().includes(low);
  if (afterBegin){
    for (const b of I.blocks) if (has(b.name)) add(b.name, 'block', b.params.length ? ' ' : '');
  } else {
    if (!afterDot){
      for (const v of scrKnown().vars) if (starts(v)) add(v, 'variable', ' ');
      for (const k of I.keywords) if (starts(k)) add(k, 'keyword', ' ');
    }
    const fs = I.functions.filter(f => !afterDot || f.ref), note = f => f.params.map(p => p.opt ? `[${p.name}]` : p.name).join(' ') || 'command';
    for (const f of fs) if (starts(f.name) || (f.short && starts(f.short))) add(f.name, note(f), f.params.length ? ' ' : '');
    if (low.length >= 3) for (const f of fs) if (has(f.name)) add(f.name, note(f), f.params.length ? ' ' : '');
  }
  SCRPOP.start = start; SCRPOP.at = 0; SCRPOP.items = items.slice(0, 40);
  scrPopDraw();
  if (afterBegin || afterDot || low.length < 3) return;
  const token = SCRPOP.token;
  setTimeout(async () => {
    if (token !== SCRPOP.token) return;
    try {
      const hits = await scrGet('/api/scripts/complete?q=' + encodeURIComponent(word));
      if (token !== SCRPOP.token || $('#sc-ta') !== document.activeElement) return;
      for (const h of hits) add(h.edid, h.tag + (h.name ? ' · ' + h.name : ''), ' ');
      SCRPOP.items = items.slice(0, 60);
      scrPopDraw();
    } catch (e) {}
  }, 180);
}
function scrPopDraw(){
  let p = $('#sc-pop');
  if (!SCRPOP.items.length){ if (p) p.remove(); return; }
  const ta = $('#sc-ta');
  if (!p){
    p = document.createElement('div'); p.id = 'sc-pop'; ta.parentNode.appendChild(p);
    p.onmousedown = e => { e.preventDefault(); const r = e.target.closest('[data-n]'); if (r){ SCRPOP.at = +r.dataset.n; scrPopAccept(); } };
  }
  p.innerHTML = SCRPOP.items.map((it, n) => `<div data-n="${n}" class="${n === SCRPOP.at ? 'on' : ''}"><span>${esc(it.name)}</span><small>${esc(it.note || '')}</small></div>`).join('');
  // where the cursor is: lines are 20 px; a tab goes to the next 4 of the fixed-width font's letters
  const before = ta.value.slice(0, SCRPOP.start), line = before.split('\n').length - 1, text = before.slice(before.lastIndexOf('\n') + 1);
  const cv = scrPopDraw.cv || (scrPopDraw.cv = document.createElement('canvas').getContext('2d'));
  cv.font = getComputedStyle(ta).font;
  const ch = cv.measureText('0').width;
  let col = 0;
  for (const c of text) col = c === '\t' ? (Math.floor(col / 4) + 1) * 4 : col + 1;
  const top = line * 20 + 8 + 20 - ta.scrollTop, area = ta.parentNode;
  p.style.left = Math.max(2, Math.min(12 + col * ch - ta.scrollLeft, area.clientWidth - 280)) + 'px';
  p.style.top = (top + p.offsetHeight > area.clientHeight && top > p.offsetHeight + 20 ? top - 20 - p.offsetHeight : top) + 'px';
  const on = p.querySelector('.on'); if (on) on.scrollIntoView({block: 'nearest'});
}
function scrPopAccept(){
  const it = SCRPOP.items[SCRPOP.at], ta = $('#sc-ta'); if (!it) return;
  const end = ta.selectionStart;
  ta.focus(); ta.setSelectionRange(SCRPOP.start, end);
  scrPopClose();
  scrInsert(it.name + (it.tail || ''));
  scrPopClose();
}
function scrPopKey(e){
  if (!SCRPOP.items.length || !$('#sc-pop')) return false;
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp'){
    e.preventDefault();
    SCRPOP.at = (SCRPOP.at + (e.key === 'ArrowDown' ? 1 : SCRPOP.items.length - 1)) % SCRPOP.items.length;
    scrPopDraw();
    return true;
  }
  if (e.key === 'Enter' || e.key === 'Tab'){ e.preventDefault(); scrPopAccept(); return true; }
  if (e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); scrPopClose(); return true; }
  return false;
}
