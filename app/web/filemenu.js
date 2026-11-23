// ---------- File: Open, Save, Save As, as a program does ----------
// (23 Nov 2026, the user: "the file management system should be more like a real program. you Open it ... and can save,
// save as, open, etc.") Changes stay unsaved until Save (project.py's working copy); the header shows "Waikiki *".
// Before anything that would leave unsaved changes behind, FOLab asks Save / Don't save / Cancel. A FOLab that closed
// with unsaved changes left them beside the mod: the next open offers them back.
const FM = {asked: null, reloadedSeen: null};

// A small window of choices; resolves to the key of the button pressed, or null for Cancel / ✕ / Esc.
function fmAsk(title, html, buttons){
  return new Promise(done => {
    const old = $('#fmask'); if (old) old.remove();
    const box = document.createElement('div');
    box.id = 'fmask'; box.className = 'owin'; box.style.cssText = 'left:50%;top:18%;transform:translateX(-50%);width:480px;max-width:94vw';
    box.innerHTML = `<div class="owtitle"><b>${esc(title)}</b><button class="owx">✕</button></div>
      <div style="padding:12px 14px">${html}</div>
      <div class="owfoot">${buttons.map(([k, l, primary]) => `<button class="btn${primary ? ' primary' : ''}" data-k="${k}">${esc(l)}</button>`).join('')}</div>`;
    document.body.appendChild(box);
    const end = k => { FM.values = {}; box.querySelectorAll('input[id]').forEach(i => { FM.values[i.id] = i.value; }); box.remove(); removeEventListener('keydown', key, true); done(k); };
    const key = e => { if (e.key === 'Escape'){ e.stopImmediatePropagation(); end(null); } };
    addEventListener('keydown', key, true);
    box.querySelector('.owx').onclick = () => end(null);
    box.querySelectorAll('[data-k]').forEach(b => b.onclick = () => end(b.dataset.k === 'cancel' ? null : b.dataset.k));
    const input = box.querySelector('input'), first = box.querySelector('.btn.primary');
    if (input){ input.focus(); input.select(); input.addEventListener('keydown', e => { if (e.key === 'Enter' && first){ e.preventDefault(); end(first.dataset.k); } }); }
    else if (first) first.focus();
  });
}

// Unsaved changes before leaving this mod: 'save' (saved now), 'discard', or null (stay).
async function fmLeave(what){
  const p = A.state && A.state.project;
  if (!p || !p.unsaved) return 'none';
  const k = await fmAsk('Save your changes?', `<p>${esc(p.name)} has ${p.unsaved_edits} change${p.unsaved_edits === 1 ? '' : 's'} you haven't saved. Save them before ${esc(what)}?</p>`,
    [['save', 'Save', true], ['discard', 'Don’t save'], ['cancel', 'Cancel']]);
  if (k === 'save'){ await save(); return A.state.project && A.state.project.unsaved ? null : 'save'; }
  return k;
}

async function fmOpenMod(name){
  const how = await fmLeave('opening ' + name);
  if (!how) return;
  busyStart('Opening ' + name);
  try {
    setState(await post('/api/project/open', {name, then: how === 'discard' ? 'discard' : undefined}));
    busyEnd('Opened ' + name, true);
    if (typeof BW !== 'undefined') BW.types = [];
    await loadPlaces(); if (A.cellId) openPlace(A.cellId);
    toast('Opened ' + name);
  } catch (e){ busyEnd('Opening ' + name, false); fail(e); }
}
openMod = fmOpenMod;            // (every Open in FOLab asks first)

const _fmNewMod = newMod;
newMod = async name => { const how = await fmLeave('starting ' + name); if (!how) return; if (how === 'discard') await post('/api/project/discard'); return _fmNewMod(name); };

function fmOpenWindow(){
  const s = A.state || {}, cur = s.project && s.project.name;
  const mods = (s.projects || []).slice().sort((a, b) => (b.name === cur) - (a.name === cur) || b.modified - a.modified);
  const box = document.createElement('div');
  box.id = 'fmopen'; box.className = 'owin'; box.style.cssText = 'left:50%;top:10%;transform:translateX(-50%);width:520px;max-width:94vw;max-height:80vh;display:flex;flex-direction:column';
  box.innerHTML = `<div class="owtitle"><b>Open</b><button class="owx">✕</button></div>
    <div style="padding:8px 14px;overflow:auto">
      <div class="h" style="margin:4px 0">Your mods</div>
      <div class="list">${mods.map(m => `<div class="row${m.name === cur ? ' on' : ''}" data-m="${esc(m.name)}"><div>${esc(m.name)}<small>${m.name === cur ? 'open now · ' : ''}changed ${esc(clock(m.modified))}</small></div><span class="n">Open</span></div>`).join('') || '<p class="note">None yet.</p>'}</div>
      <div class="h" style="margin:12px 0 4px">A plugin</div>
      <div class="list" id="fmplugins"><p class="note">Looking…</p></div>
    </div>`;
  const old = $('#fmopen'); if (old) old.remove();
  document.body.appendChild(box);
  box.querySelector('.owx').onclick = () => box.remove();
  box.querySelectorAll('[data-m]').forEach(r => r.onclick = () => { box.remove(); if (r.dataset.m !== cur) fmOpenMod(r.dataset.m); });
  api('/api/plugins').then(list => {
    const el = box.querySelector('#fmplugins');
    el.innerHTML = list.length ? list.map(x => `<div class="row" data-p="${esc(x.file)}"><div>${esc(x.file)}<small>${x.error ? esc(x.error) : `opened as a mod of its own`}</small></div><span class="n">Open</span></div>`).join('') : '<p class="note">No plugins found.</p>';
    el.querySelectorAll('[data-p]').forEach(r => r.onclick = async () => {
      box.remove();
      const how = await fmLeave('opening ' + r.dataset.p); if (!how) return;
      toast('Opening ' + r.dataset.p + '… (loading it on top of the game takes a few seconds)');
      try { setState(await post('/api/project/adopt', {file: r.dataset.p, then: how === 'discard' ? 'discard' : undefined})); await loadPlaces(); if (typeof BW !== 'undefined') BW.types = []; page('world'); toast('Opened ' + r.dataset.p); }
      catch (e){ fail(e); }
    });
  }).catch(() => { box.querySelector('#fmplugins').innerHTML = '<p class="note">Couldn’t list plugins.</p>'; });
}

async function fmSaveAs(){
  const p = A.state && A.state.project; if (!p) return;
  const shared = p.files_of || p.name;
  const k = await fmAsk('Save As', `<p>A copy of ${esc(p.name)} as it is now, under a new name; FOLab then carries on in the copy, and ${esc(p.name)} stays as you last saved it.</p>
    <div class="fields" style="grid-template-columns:90px 1fr;padding:6px 0"><label>New name</label><input id="fm-name" value="${esc(p.name)} copy"></div>
    <p class="note" style="padding:4px 0 0">Models and pictures are shared with ${esc(shared)}, not copied. Voiced lines are made for ${esc(p.plugin)}: voice them again in the copy.</p>`,
    [['go', 'Save As', true], ['cancel', 'Cancel']]);
  const name = k === 'go' ? (FM.values['fm-name'] || '').trim() : null;      // (read as the box closed)
  if (!name) return;
  busyStart('Saving a copy');
  try { const d = await post('/api/project/saveas', {name}); busyEnd('Saved as ' + d.project.name, true); setState(d); await loadPlaces(); toast('Saved as ' + d.project.name + '. You are working in the copy now.'); }
  catch (e){ busyEnd('Save As', false); fail(e); }
}

async function fmThrowAway(){
  const p = A.state && A.state.project; if (!p || !p.unsaved) return toast('Nothing unsaved.');
  const k = await fmAsk('Throw away your changes?', `<p>${esc(p.name)} goes back to how you last saved it. The ${p.unsaved_edits} unsaved change${p.unsaved_edits === 1 ? '' : 's'} can't be got back.</p>`,
    [['go', 'Throw them away'], ['cancel', 'Cancel', true]]);
  if (k !== 'go') return;
  try { setState(await post('/api/project/discard')); await loadPlaces(); if (A.cellId) await openPlace(A.cellId); toast('Back to how you last saved it.'); }
  catch (e){ fail(e); }
}

// the header's File menu
(() => {
  const save = $('#b-save'); if (!save) return;
  const b = document.createElement('button');
  b.className = 'btn'; b.id = 'b-file'; b.textContent = 'File ▾'; b.title = 'Open, Save, Save As';
  const m = document.createElement('div');
  m.id = 'filemenu'; m.style.cssText = 'display:none;position:absolute;z-index:30;background:var(--panel);border:1px solid var(--line2);border-radius:8px;padding:4px 0;min-width:240px;box-shadow:0 8px 28px #0008';
  const items = [['open', 'Open…', 'Ctrl+O'], ['save', 'Save', 'Ctrl+S'], ['saveas', 'Save As…', ''], ['throw', 'Throw away unsaved changes…', '']];
  m.innerHTML = items.map(([k, l, key]) => `<div class="row" data-f="${k}"><div>${l}</div><span class="n">${key}</span></div>`).join('');
  save.parentNode.insertBefore(b, save);
  document.body.appendChild(m);
  b.onclick = e => {
    e.stopPropagation();
    if (m.style.display === 'block'){ m.style.display = 'none'; return; }
    const r = b.getBoundingClientRect(); m.style.display = 'block'; m.style.top = (r.bottom + 4) + 'px';
    m.style.left = Math.max(8, Math.min(r.left, innerWidth - m.offsetWidth - 8)) + 'px';      // (kept on screen at the window's edge)
  };
  document.addEventListener('click', e => { if (!e.target.closest('#filemenu')) m.style.display = 'none'; });
  m.onclick = e => {
    const r = e.target.closest('[data-f]'); if (!r) return;
    m.style.display = 'none';
    ({open: fmOpenWindow, save: () => window.save(), saveas: fmSaveAs, throw: fmThrowAway})[r.dataset.f]();
  };
  addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'o' && !typing(e)){ e.preventDefault(); fmOpenWindow(); }
  });
})();

// Put in game, Open in game and Play here save first: asked when there are unsaved changes.
for (const id of ['#b-install', '#b-play', '#b-playhere']){
  const b = $(id); if (!b) continue;
  b.addEventListener('click', async e => {
    const p = A.state && A.state.project;
    if (!p || !p.unsaved || FM.passing) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const k = await fmAsk('Save your changes first?', `<p>${esc(p.name)} has ${p.unsaved_edits} unsaved change${p.unsaved_edits === 1 ? '' : 's'}. The game gets your mod as it's saved, so FOLab saves first.</p>`,
      [['save', 'Save, then go on', true], ['cancel', 'Cancel']]);
    if (k !== 'save') return;
    await save();
    if (A.state.project && A.state.project.unsaved) return;
    FM.passing = true; try { b.click(); } finally { FM.passing = false; }
  }, true);
}

// After every state: unsaved edits left by a FOLab that closed first, and the mod opened again because it changed outside.
const _fmSetState = setState;
setState = s => { try { _fmSetState(s); } finally { fmCheck(s); } };
function fmCheck(s){
  const p = s && s.project;
  if (!p) return;
  if (p.reloaded && p.reloaded !== FM.reloadedSeen){
    if (FM.reloadedSeen !== null) toast(`${p.name} was changed by another program, so FOLab opened it again before your change. Undo starts afresh from here.`);
    FM.reloadedSeen = p.reloaded;
  } else if (FM.reloadedSeen === null) FM.reloadedSeen = p.reloaded || 0;
  if (p.recovery && FM.asked !== p.name + p.recovery.when){
    FM.asked = p.name + p.recovery.when;
    const r = p.recovery;
    fmAsk('Get your unsaved changes back?', `<p>FOLab closed before ${r.edits} change${r.edits === 1 ? '' : 's'} to ${esc(p.name)} ${r.edits === 1 ? 'was' : 'were'} saved (last one ${esc(clock(r.when))}). They were kept.</p>
      ${r.fits ? '' : `<p class="note" style="padding:0">${esc(p.name)} was changed by another program since: getting them back lays them on top of that.</p>`}`,
      [['keep', 'Get them back', true], ['throw', 'Throw them away']]).then(async k => {
      if (!k) return;
      try { const d = await post('/api/project/recover', {keep: k === 'keep'}); setState(d); await loadPlaces(); if (A.cellId) await openPlace(A.cellId); toast(k === 'keep' ? `Got back ${d.recovered} change${d.recovered === 1 ? '' : 's'}: not saved yet.` : 'Thrown away.'); }
      catch (e){ fail(e); }
    });
  }
}
// (the first state can come before this script: the page's later scripts load while it's asked for)
(function fmFirst(n){
  if (A.state && A.state.project) return fmCheck(A.state);
  if (n < 240) setTimeout(() => fmFirst(n + 1), 500);
})(0);
