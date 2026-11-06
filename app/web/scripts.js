// ---------- Scripts: read the game's scripts, write your own (the Workshop's Scripts page, for New Vegas's language) ----------
// The list on the left (your mod's first, then the game's), the script in the middle. What you type is checked by the real
// compiler as you go; Save compiles it and keeps it in your mod, and a script with a mistake is never kept: the mistake
// shows at its line and your text stays in the editor (and in this browser, in case the window closes).
const SCR = {rows: [], key: null, data: null, text: '', orig: '', kind: 'object', check: null, info: null};
const SCR_KINDS = {object: 'On a thing', quest: 'On a quest', effect: 'An effect'};

async function scrGet(path){
  const d = await api(path);
  if (d.error) throw new Error(d.error);
  return d;
}

(function scrStyle(){
  const st = document.createElement('style');
  st.textContent = `
#sc-side{border-right:1px solid var(--line)}
#sc-side .find{margin:6px 12px}
#sc-side .acts{padding:10px 12px 0;display:flex;gap:6px}
#sc-inside{display:flex;align-items:center;gap:6px;padding:0 12px 6px;color:var(--muted);font-size:12.5px}
#sc-rows{overflow-x:hidden}#sc-rows .row>div{min-width:0;overflow:hidden;text-overflow:ellipsis}
#sc-main{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--bg)}
#sc-head{padding:8px 14px;border-bottom:1px solid var(--line);background:var(--panel);display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}
#sc-head b{font-size:16px;color:var(--gold2)}#sc-head small{color:var(--muted);display:block;font-size:12px}
#sc-head .sp{flex:1 1 auto}
.sc-ed{flex:1;display:flex;min-height:0;position:relative;font:13px/20px var(--mono);tab-size:4}
.sc-gut{flex:none;width:48px;overflow:hidden;padding:8px 8px 8px 0;text-align:right;color:var(--faint);background:var(--bg2);border-right:1px solid var(--line);user-select:none}
.sc-gut div.err{background:var(--red);color:#000;border-radius:0 3px 3px 0}
.sc-gut div.warn{color:var(--amber);font-weight:600}
.sc-area{flex:1;position:relative;min-width:0}
.sc-hl,#sc-ta{position:absolute;inset:0;margin:0;padding:8px 12px;font:inherit;tab-size:4;white-space:pre;overflow:auto;border:0;box-sizing:border-box}
.sc-hl{pointer-events:none;color:var(--text);overflow:hidden}
.sc-hl div{min-height:20px}.sc-hl div.err{background:color-mix(in srgb,var(--red) 22%,transparent)}.sc-hl div.warn{background:color-mix(in srgb,var(--amber) 13%,transparent)}
#sc-ta{background:transparent;color:transparent;caret-color:var(--gold2);resize:none;outline:none}
#sc-ta::selection{background:color-mix(in srgb,var(--gold) 34%,transparent);color:transparent}
#sc-ta[readonly]{caret-color:transparent}
#sc-prob{flex:none;border-top:1px solid var(--line);background:var(--panel);padding:6px 14px;font-size:13px;max-height:100px;overflow:auto}
#sc-prob .row{padding:2px 4px;justify-content:flex-start}
#sc-prob .ok{color:var(--green)}#sc-prob .bad{color:var(--red)}#sc-prob .wrn{color:var(--amber)}
#sc-prob .ln{color:var(--muted);flex:none;width:58px}
.sc-welcome{padding:26px;max-width:720px;overflow:auto}.sc-welcome h2{color:var(--gold2);margin:0 0 8px;font:600 20px Oswald,'Arial Narrow',sans-serif;letter-spacing:.04em}
.sc-welcome p{color:var(--muted)}
.sc-form{display:grid;grid-template-columns:150px minmax(0,1fr);gap:8px 12px;align-items:center;max-width:620px;margin:10px 0}
.sc-form label{color:var(--muted);font-size:13px}.sc-form .hint{grid-column:2;color:var(--faint);font-size:12px;margin-top:-5px}
.sc-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px;margin:10px 0 14px}
.sc-card{background:var(--panel);border:1px solid var(--line2);border-radius:8px;padding:9px 11px;cursor:pointer;text-align:left;color:var(--text)}
.sc-card:hover{border-color:var(--gold)}.sc-card.on{border-color:var(--gold);background:var(--sel)}
.sc-card b{display:block;margin-bottom:3px;color:var(--gold2);font-weight:500}.sc-card span{color:var(--muted);font-size:12.5px;line-height:1.35;display:block}
.sc-pickbox{position:relative;display:inline-block;min-width:170px}.sc-pickbox input{width:100%}
#sc-p-run .sc-pickbox{display:block;margin:4px 12px}#sc-p-run .row .btn{padding:1px 7px}
.sc-picks{display:none;position:absolute;z-index:20;left:0;top:100%;min-width:100%;width:max-content;max-width:380px;max-height:240px;overflow:auto;background:var(--panel2);border:1px solid var(--line2);border-radius:6px;box-shadow:0 8px 24px #0009;font-size:13px}
.sc-picks div{padding:3px 8px;cursor:pointer}.sc-picks div.on,.sc-picks div:hover{background:var(--sel)}.sc-picks small{color:var(--faint);margin-left:10px}.sc-picks .none{color:var(--muted);cursor:default}
.sc-onrow{display:flex;gap:10px;align-items:center;margin:8px 0;padding:6px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);font-size:13px}
.sc-onrow>label{color:var(--muted);flex:none}.sc-onval{display:flex;flex-wrap:wrap;gap:6px;align-items:center;min-width:0}.sc-onval a{color:var(--gold2)}.sc-onval .btn{padding:2px 8px}
#sel-rec .sc-onrow{margin:8px 12px}
#sc-help{border-left:1px solid var(--line);width:310px}
#sc-here{flex:none;border-bottom:1px solid var(--line);padding:8px 12px;max-height:48%;overflow:auto;font-size:13px}
#sc-here code,.sc-sig{font:12.5px/1.45 var(--mono);color:var(--gold2);word-break:break-word}
#sc-here p{margin:5px 0;color:var(--muted)}
#sc-here .acts{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}
#sc-here .row{padding:3px 4px}#sc-here .row small{font:11px var(--mono)}
#sc-cq{margin:8px 12px;flex:none}
#sc-cmds{flex:1;overflow:auto}#sc-cmds .row{padding:3px 12px}#sc-cmds .row>div{min-width:0}#sc-cmds .row small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:270px}
.c-kw{color:var(--gold2);font-weight:600}.c-blk{color:var(--gold)}.c-fn{color:var(--blue)}.c-str{color:var(--green)}.c-num{color:var(--amber)}
.c-com{color:var(--faint);font-style:italic}.c-var{color:color-mix(in srgb,var(--text) 60%,var(--red))}.c-ref{text-decoration:underline dotted;text-underline-offset:3px;color:var(--gold)}
#sc-pop{position:absolute;z-index:9;background:var(--panel2);border:1px solid var(--line2);border-radius:6px;box-shadow:0 8px 24px #0009;min-width:260px;max-width:440px;max-height:220px;overflow:auto;font:12.5px/1.3 var(--mono)}
#sc-pop div{padding:3px 8px;cursor:pointer;display:flex;justify-content:space-between;gap:14px;white-space:nowrap}
#sc-pop div.on,#sc-pop div:hover{background:var(--sel)}#sc-pop small{color:var(--faint);overflow:hidden;text-overflow:ellipsis}
`;
  document.head.appendChild(st);
})();

$('#page-scripts').innerHTML = `
  <div class="side" id="sc-side">
    <div class="acts"><button class="btn primary" id="sc-new" style="flex:1">＋ New script</button></div>
    <input class="find" id="sc-find" placeholder="Find a script…">
    <label id="sc-inside"><input type="checkbox" id="sc-deep"> Search inside the scripts too</label>
    <div class="h" id="sc-count"></div>
    <div class="list" id="sc-rows"></div>
  </div>
  <div id="sc-main"></div>
  <div class="side" id="sc-help">
    <div class="tabs"><button data-sct="help" class="on">Help</button><button data-sct="run">What runs it</button></div>
    <div class="pane on" id="sc-p-help">
      <div id="sc-here"><span class="note" style="padding:0">Put the cursor on a word to see what it is.</span></div>
      <input class="find" id="sc-cq" placeholder="Search commands… (item, door, quest)">
      <div id="sc-cmds"></div>
    </div>
    <div class="pane" id="sc-p-run"></div>
  </div>`;
function scrPanel(name){
  document.querySelectorAll('#sc-help .tabs button').forEach(x => x.classList.toggle('on', x.dataset.sct === name));
  document.querySelectorAll('#sc-help .pane').forEach(p => p.classList.toggle('on', p.id === 'sc-p-' + name));
}
$('#sc-help .tabs').onclick = e => { const b = e.target.closest('button'); if (b) scrPanel(b.dataset.sct); };

PAGES.push('scripts');
$('#nav-scripts').onclick = () => page('scripts');
const scrOnPagePrev = onPage;
onPage = function (name){ scrOnPagePrev(name); if (name === 'scripts'){ scrList(); scrLoadInfo(); if (!SCR.key && !SCR.making) scrWelcome(); } };
// (Undo and Redo may have changed what's in the editor)
const scrUndoRedoPrev = undoRedo;
undoRedo = async function (which){ await scrUndoRedoPrev(which); if ($('#page-scripts').style.display !== 'none') scrAfterUndo(); };

async function scrAfterUndo(){
  await scrList();
  if (!SCR.key || scrDirty()) return;
  try { await scrGet('/api/scripts/one?key=' + encodeURIComponent(SCR.key)); await scrOpen(SCR.key, true); }
  catch (e){ SCR.key = null; scrWelcome(); }
}

let scrTimer;
$('#sc-find').addEventListener('input', () => { clearTimeout(scrTimer); scrTimer = setTimeout(scrList, 200); });
$('#sc-deep').addEventListener('change', scrList);
$('#sc-rows').addEventListener('click', e => { const r = e.target.closest('.row'); if (r) scrOpen(r.dataset.k); });
$('#sc-new').addEventListener('click', () => scrNewForm());

async function scrList(){
  const token = SCR.listToken = (SCR.listToken || 0) + 1;
  const d = await scrGet(`/api/scripts?q=${encodeURIComponent($('#sc-find').value)}&inside=${$('#sc-deep').checked ? 1 : 0}`);
  if (token !== SCR.listToken) return;
  SCR.rows = d.rows;
  const n = d.rows.length + d.more;
  $('#sc-count').textContent = `${n} script${n === 1 ? '' : 's'}`;
  $('#sc-rows').innerHTML = d.rows.map(r => `<div class="row${r.key === SCR.key ? ' on' : ''}" data-k="${esc(r.key)}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}" title="${r.state === 'new' ? 'your own' : 'changed by your mod'}"></span>` : ''}${esc(r.edid)}<small>${esc(SCR_KINDS[r.kind])}</small></div></div>`).join('') +
    (d.more ? `<div class="note">…and ${d.more} more: search to narrow it down.</div>` : '');
}

function scrWelcome(){
  $('#sc-main').innerHTML = `<div class="sc-welcome"><h2>Scripts</h2>
    <p>Scripts make things happen in the game: a door that wants a key, a note that moves a quest on, a trigger that says something when you walk in.</p>
    <p>Pick one of the game's on the left to see how it does things, or start your own with <b>＋ New script</b>. Every mistake is shown at its line as you type, by the same rules the game's own scripts were built by.</p></div>`;
}

// ---------- one script ----------
function scrDirty(){ return SCR.key && (SCR.text !== SCR.orig || SCR.kind !== SCR.data.kind); }
function scrDraftKey(key){ return 'folab-script-draft:' + key; }
function scrLeaveOk(key){
  if (!scrDirty() || key === SCR.key) return true;
  if (!confirm(`Leave ${SCR.data.edid} without saving your changes?`)) return false;
  try { localStorage.removeItem(scrDraftKey(SCR.key)); } catch (e) {}
  return true;
}

async function scrOpen(key, fresh){
  if (!scrLeaveOk(key)) return;
  if ($('#page-scripts').style.display === 'none') page('scripts');
  let d;
  try { d = await scrGet('/api/scripts/one?key=' + encodeURIComponent(key)); } catch (e){ return fail(e); }
  SCR.making = false;
  SCR.key = key; SCR.data = d; SCR.text = SCR.orig = d.text; SCR.kind = d.kind; SCR.check = d.check; SCR.lastGood = d.check.ok ? d.check : null;
  document.querySelectorAll('#sc-rows .row').forEach(r => r.classList.toggle('on', r.dataset.k === key));
  let draft = null;
  try { draft = localStorage.getItem(scrDraftKey(key)); } catch (e) {}
  if (draft !== null && draft !== d.text && !fresh) { SCR.text = draft; }
  else if (draft !== null) { try { localStorage.removeItem(scrDraftKey(key)); } catch (e) {} }
  scrDraw();
  if (SCR.text !== SCR.orig){ scrCheckNow(); toast('Your unsaved changes to this script are back.'); }
}

function scrDraw(){
  const d = SCR.data, mine = d.state === 'new';
  const whose = mine ? 'Your own script' : d.state === 'changed' ? `The game's, changed by your mod (${esc(d.from)})` : `From ${esc(d.from)}: saving keeps your changed version in your mod`;
  $('#sc-main').innerHTML = `<div id="sc-head">
      <div><b>${esc(d.edid)}</b><small>${whose}</small></div><span class="sp"></span>
      <select id="sc-kind" title="What the script runs on">${Object.entries(SCR_KINDS).map(([k, l]) => `<option value="${k}" ${k === SCR.kind ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <button class="btn primary" id="sc-save" disabled>Saved</button>
      <button class="btn" id="sc-revert" title="Back to the last saved text" style="display:none">↺ Undo my typing</button>
      <button class="btn" id="sc-copy" title="A script of your own, starting as a copy of this one">Make a copy</button>
      ${d.state === 'changed' ? '<button class="btn" id="sc-remove">Put back as the game has it</button>' : ''}
      ${mine ? '<button class="btn" id="sc-remove">Delete this script</button>' : ''}
    </div>
    <div class="sc-ed"><div class="sc-gut" id="sc-gut"></div><div class="sc-area"><pre class="sc-hl" id="sc-hl" aria-hidden="true"></pre>
      <textarea id="sc-ta" spellcheck="false" autocapitalize="off" autocomplete="off" wrap="off"></textarea></div></div>
    <div id="sc-prob"></div>`;
  const ta = $('#sc-ta');
  ta.value = SCR.text;
  ta.oninput = e => { SCR.text = ta.value; scrPaint(); scrDirtyShow(); scrCheckSoon(); scrKeepDraft(); if (e.inputType === 'insertText') scrPopSoon(); else scrPopClose(); scrHereSoon(); };
  ta.onscroll = () => { scrSyncScroll(); scrPopClose(); };
  ta.onkeydown = scrKey;
  ta.onkeyup = e => { if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) scrHereSoon(); };
  ta.onclick = e => {
    scrPopClose(); scrHereSoon();
    // (Ctrl+click on the name of something opens its record)
    if (e.ctrlKey || e.metaKey){ const r = scrKnown().refs.get(scrWordAt(ta.value, ta.selectionStart).toLowerCase()); if (r) openRecord(r.key); }
  };
  ta.onblur = () => setTimeout(() => { if (document.activeElement !== ta) scrPopClose(); }, 100);
  $('#sc-kind').onchange = e => { SCR.kind = e.target.value; scrDirtyShow(); scrCheckNow(); scrRunDraw(); };
  $('#sc-save').onclick = scrSave;
  $('#sc-revert').onclick = () => { SCR.text = SCR.orig; SCR.kind = d.kind; $('#sc-kind').value = d.kind; ta.value = SCR.text; scrPaint(); scrDirtyShow(); scrCheckNow(); scrKeepDraft(); };
  $('#sc-copy').onclick = () => scrCopyForm();
  const rm = $('#sc-remove');
  if (rm) rm.onclick = scrRemove;
  scrPaint(); scrProblems(); scrDirtyShow(); scrRunDraw();
}
function scrSyncScroll(){
  const ta = $('#sc-ta');
  $('#sc-hl').scrollTop = ta.scrollTop; $('#sc-hl').scrollLeft = ta.scrollLeft; $('#sc-gut').scrollTop = ta.scrollTop;
}
function scrKeepDraft(){
  try { if (SCR.text !== SCR.orig) localStorage.setItem(scrDraftKey(SCR.key), SCR.text); else localStorage.removeItem(scrDraftKey(SCR.key)); } catch (e) {}
}
function scrDirtyShow(){
  const b = $('#sc-save'); if (!b) return;
  const dirty = scrDirty();
  b.disabled = !dirty; b.textContent = dirty ? 'Save' : 'Saved';
  $('#sc-revert').style.display = dirty ? '' : 'none';
}

function scrPaint(){
  const lines = SCR.text.split('\n'), c = SCR.check || {}, bad = {};
  for (const w of c.warnings || []) bad[w.line] = 'warn';
  if (c.problem && c.problem.line) bad[c.problem.line] = 'err';
  const known = scrKnown();
  $('#sc-hl').innerHTML = lines.map((l, n) => `<div${bad[n + 1] ? ` class="${bad[n + 1]}"` : ''}>${scrColour(l, known) || ' '}</div>`).join('') + '<div> </div>';
  $('#sc-gut').innerHTML = lines.map((_, n) => `<div${bad[n + 1] ? ` class="${bad[n + 1]}"` : ''}>${n + 1}</div>`).join('') + '<div> </div>';
  scrSyncScroll();
}

let scrCheckT = null, scrCheckSeq = 0;
function scrCheckSoon(){ clearTimeout(scrCheckT); scrCheckT = setTimeout(scrCheckNow, 300); }
async function scrCheckNow(){
  const my = ++scrCheckSeq, key = SCR.key;
  try {
    const r = await post('/api/scripts/check', {key, text: SCR.text, kind: SCR.kind});
    if (my !== scrCheckSeq || key !== SCR.key || !$('#sc-prob')) return;
    SCR.check = r; if (r.ok) SCR.lastGood = r; scrPaint(); scrProblems();
  } catch (e) {}
}
function scrProblems(){
  const box = $('#sc-prob'), c = SCR.check; if (!box || !c) return;
  const row = (line, cls, msg) => `<div class="row" ${line ? `data-go="${line}"` : ''}><span class="ln">${line ? 'line ' + line : ''}</span><span class="${cls}">${esc(msg)}</span></div>`;
  box.innerHTML = (c.ok ? `<div class="ok">✓ No mistakes. ${c.size} bytes, ${c.vars.length} variable${c.vars.length === 1 ? '' : 's'}, ${c.refs.length} thing${c.refs.length === 1 ? '' : 's'} named.</div>` : row(c.problem.line, 'bad', c.problem.message)) +
    (c.warnings || []).map(w => row(w.line, 'wrn', w.message)).join('');
  box.querySelectorAll('[data-go]').forEach(r => r.onclick = () => scrGoLine(+r.dataset.go));
}
function scrGoLine(n){
  const ta = $('#sc-ta'), lines = SCR.text.split('\n');
  let pos = 0;
  for (let k = 0; k < n - 1 && k < lines.length; k++) pos += lines[k].length + 1;
  ta.focus(); ta.setSelectionRange(pos, pos + (lines[n - 1] || '').length);
  ta.scrollTop = Math.max(0, (n - 5) * 20);
}

function scrInsert(text){
  const ta = $('#sc-ta');
  ta.focus();
  // (this way Ctrl+Z in the editor can take it back)
  if (!document.execCommand('insertText', false, text)){
    ta.setRangeText(text, ta.selectionStart, ta.selectionEnd, 'end');
    ta.dispatchEvent(new Event('input'));
  }
}
function scrKey(e){
  const ta = e.target, ctrl = e.ctrlKey || e.metaKey;
  if (scrPopKey(e)) return;
  if (ctrl && e.key.toLowerCase() === 's'){ e.preventDefault(); e.stopPropagation(); scrSave(); return; }
  if (e.key === 'Tab'){ e.preventDefault(); scrInsert('\t'); return; }
  if (e.key === 'Enter'){
    e.preventDefault();
    const line = ta.value.slice(0, ta.selectionStart).split('\n').pop(), ind = line.match(/^\s*/)[0];
    scrInsert('\n' + ind + (/^\s*(if|elseif|else|begin)\b/i.test(line) ? '\t' : ''));
  }
}

async function scrSave(){
  if (!scrDirty()) return;
  const b = $('#sc-save');
  if (b){ b.disabled = true; b.textContent = 'Saving…'; }
  try {
    const r = await post('/api/scripts/save', {key: SCR.key, text: SCR.text, kind: SCR.kind});
    if (r.state) setState(r.state);
    if (!r.ok){
      SCR.check = {ok: false, problem: r.problem, warnings: []}; scrPaint(); scrProblems(); scrDirtyShow();
      if (r.problem.line) scrGoLine(r.problem.line);
      return toast(`Not saved: ${r.problem.line ? 'line ' + r.problem.line + ': ' : ''}${r.problem.message}`, true);
    }
    try { localStorage.removeItem(scrDraftKey(SCR.key)); } catch (e) {}
    const caret = $('#sc-ta').selectionStart, top = $('#sc-ta').scrollTop;
    SCR.data = r.script; SCR.text = SCR.orig = r.script.text; SCR.kind = r.script.kind; SCR.check = r.script.check; if (r.script.check.ok) SCR.lastGood = r.script.check;
    if (typeof recCacheDrop === 'function') recCacheDrop(SCR.key);
    scrDraw();
    const ta = $('#sc-ta'); ta.focus(); ta.setSelectionRange(caret, caret); ta.scrollTop = top; scrSyncScroll();
    toast('Saved in your mod');
    scrList();
  } catch (e){ fail(e); scrDirtyShow(); }
}

async function scrRemove(){
  const mine = SCR.data.state === 'new';
  if (!confirm(mine ? `Delete ${SCR.data.edid} from your mod? Anything it's on loses it.` : `Put ${SCR.data.edid} back as the game has it?`)) return;
  try {
    const r = await post('/api/scripts/remove', {key: SCR.key});
    setState(r.state);
    try { localStorage.removeItem(scrDraftKey(SCR.key)); } catch (e) {}
    const k = SCR.key;
    SCR.key = null;
    await scrList();
    if (mine) scrWelcome(); else scrOpen(k, true);
    toast(mine ? 'Deleted' : 'Back as the game has it');
  } catch (e){ fail(e); }
}

// ---------- a new script, a copy ----------
function scrSuggestName(base){
  const mod = ((A.state && A.state.project && A.state.project.name) || 'My').replace(/[^A-Za-z0-9]/g, '').slice(0, 10) || 'My';
  return mod + (base || 'NewScript');
}
// opts: {attachTo: a record's key, type, needs}: made from that record's Script row, and put straight on it
async function scrNewForm(opts){
  if (!scrLeaveOk(null)) return;
  opts = opts || {};
  await scrLoadInfo();
  SCR.key = null; SCR.making = true;
  document.querySelectorAll('#sc-rows .row.on').forEach(r => r.classList.remove('on'));
  $('#sc-p-run').innerHTML = '';
  const fits = t => !opts.attachTo || t.on.includes(opts.type);
  const starters = SCR.info.templates.filter(fits);
  let pick = '';
  $('#sc-main').innerHTML = `<div class="sc-welcome"><h2>A new script</h2>
    ${opts.attachTo ? `<p>It goes on ${esc(opts.edid || opts.attachTo)} as soon as it's made.</p>` : ''}
    <div class="sc-form"><label>Its name</label><input id="sn-name" value="${esc(scrSuggestName())}" maxlength="60">
      <div class="hint">Letters, numbers and _ only. Players never see it.</div></div>
    <div class="h" style="padding-left:0">Start from</div>
    <div class="sc-cards">
      <button class="sc-card on" data-tpl=""><b>Nothing: a blank script</b><span>Just the first lines, for you to fill in.</span></button>
      ${starters.map(t => `<button class="sc-card" data-tpl="${esc(t.id)}"><b>${esc(t.title)}</b><span>${esc(t.desc)}</span></button>`).join('')}
    </div>
    <div class="sc-form" id="sn-fields"></div>
    <div class="acts"><button class="btn primary" id="sn-go">Make it</button> <span class="note" id="sn-msg"></span></div></div>`;
  const nm = $('#sn-name'); nm.focus(); nm.select();
  const drawFields = () => {
    const t = SCR.info.templates.find(x => x.id === pick), box = $('#sn-fields');
    if (!t){
      box.innerHTML = opts.attachTo ? '' : `<label>What it runs on</label><select id="sn-kind">${Object.entries(SCR_KINDS).map(([k, l]) => `<option value="${k}">${l}</option>`).join('')}</select>`;
      if (opts.needs === 'quest') { const k = $('#sn-kind'); if (k) k.value = 'quest'; }
      return;
    }
    box.innerHTML = t.fields.map(f => `<label>${esc(f.label)}</label>${f.kind === 'form'
      ? `<span class="sc-pickbox" style="display:block"><input data-sf="${esc(f.id)}" value="${esc(f.default || '')}" placeholder="Search by editor ID…" autocomplete="off"></span>`
      : f.kind === 'number' ? `<input data-sf="${esc(f.id)}" value="${esc(f.default || '')}" inputmode="numeric" style="max-width:100px">` : `<input data-sf="${esc(f.id)}" value="${esc(f.default || '')}">`}`).join('') +
      `<div class="hint" style="grid-column:1/3;margin:0">Goes on ${esc(t.on_label)}. You can change all of it afterwards: it's an ordinary script.</div>`;
    t.fields.filter(f => f.kind === 'form').forEach(f => scrPick(box.querySelector(`[data-sf="${f.id}"]`), f.tags, () => {}));
  };
  $('#sc-main').querySelectorAll('[data-tpl]').forEach(b => b.onclick = () => {
    pick = b.dataset.tpl;
    $('#sc-main').querySelectorAll('[data-tpl]').forEach(x => x.classList.toggle('on', x === b));
    drawFields();
  });
  drawFields();
  $('#sn-go').onclick = async () => {
    const msg = $('#sn-msg'), fields = {};
    document.querySelectorAll('#sn-fields [data-sf]').forEach(i => fields[i.dataset.sf] = i.value);
    const kind = (document.querySelector('#sn-kind') || {}).value || (opts.needs === 'quest' ? 'quest' : 'object');
    msg.textContent = '';
    try {
      const r = await post('/api/scripts/new', {name: nm.value, kind, template: pick || null, fields});
      setState(r.state); SCR.making = false;
      if (opts.attachTo) await scrAttachDo(opts.attachTo, r.key);
      await scrList(); await scrOpen(r.key, true);
      if (r.note && !opts.attachTo){ toast(r.note); scrPanel('run'); }
      else toast('Made ' + nm.value);
    } catch (e){ msg.textContent = e.message; msg.style.color = 'var(--red)'; }
  };
}
function scrCopyForm(){
  if (!scrLeaveOk(null)) return;
  const from = SCR.key, edid = SCR.data.edid;
  SCR.key = null; SCR.making = true;
  $('#sc-main').innerHTML = `<div class="sc-welcome"><h2>A copy of ${esc(edid)}</h2><p>It becomes a script of your own. The game's stays as it is, and nothing runs your copy until you put it on something.</p>
    <div class="sc-form"><label>Its name</label><input id="sn-name" value="${esc(scrSuggestName(edid))}" maxlength="60"></div>
    <div class="acts"><button class="btn primary" id="sn-go">Make the copy</button> <button class="btn" id="sn-back">Back</button> <span class="note" id="sn-msg"></span></div></div>`;
  const nm = $('#sn-name'); nm.focus(); nm.select();
  $('#sn-back').onclick = () => { SCR.key = null; scrOpen(from, true); };
  $('#sn-go').onclick = async () => {
    try {
      const r = await post('/api/scripts/copy', {key: from, name: nm.value});
      setState(r.state); SCR.making = false; await scrList(); await scrOpen(r.key, true); toast('Made ' + nm.value);
    } catch (e){ $('#sn-msg').textContent = e.message; $('#sn-msg').style.color = 'var(--red)'; }
  };
}
