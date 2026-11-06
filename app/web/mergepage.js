// ---------- Merge a plugin into the mod ----------
// Pick one, see what it would do and where the two disagree, choose per disagreement (yours unless you say), merge.
// Afterwards the merged plugin is the mod, opened as any plugin is: a copy is kept first, and can be put back.
const MG = {d: null, item: null, pv: null, theirs: new Set(), busy: ''};

async function mergeDraw(){
  if (!A.state.project){ $('#tl-body').innerHTML = '<h2>Merge a plugin</h2>' + tlBox('Start a mod first: the other plugin is merged into it.'); return; }
  try { MG.d = await api('/api/tools/merge'); } catch (e){ $('#tl-body').innerHTML = '<h2>Merge a plugin</h2>' + tlBox(e.message); return; }
  mergeRender();
}

function mergeRender(){
  if (TL.tab !== 'merge') return;
  const d = MG.d, p = MG.pv;
  $('#tl-body').innerHTML = `<h2>Merge a plugin</h2>
    <p class="note" style="padding:0">Brings another plugin into ${esc(d.plugin)}: its records, its places, what it changes. Every link keeps pointing at the same thing, and its masters become yours. The other plugin is only read.</p>
    ${MG.busy ? tlBox(MG.busy) : ''}
    <div class="tl-group">${d.candidates.map((c, i) => `<div class="tl-row"><div class="t">${esc(c.file)}<small>${c.where === 'build' ? 'another FOLab mod' : 'in Data'} · ${c.records} records · needs ${c.masters.map(esc).join(', ') || 'nothing'}${c.author ? ' · by ' + esc(c.author) : ''}</small></div>
        <button class="btn" data-pick="${i}">See what it would do</button></div>`).join('') || '<div class="tl-row">No other plugins: nothing in Data but the game\'s own, and no other FOLab mods saved.</div>'}</div>
    ${p ? mergePreview(p) : ''}
    ${d.backups.length ? `<div class="card wide"><h3>Copies kept</h3><p>How the mod was before a merge.</p>${d.backups.map(b => `<div class="tl-row" style="padding:2px 0;border:0"><div class="t">${esc(b)}</div><button class="btn" data-restore="${esc(b)}">Put back</button></div>`).join('')}</div>` : ''}`;
  $('#tl-body').onclick = mergeClick;
  $('#tl-body').onchange = e => {
    const c = e.target.closest('[data-th]');
    if (c){ c.checked ? MG.theirs.add(c.dataset.th) : MG.theirs.delete(c.dataset.th); }
    if (e.target.id === 'mg-all'){ MG.theirs = new Set(e.target.checked ? MG.pv.conflicts.map(x => x.id) : []); mergeRender(); }
  };
}

function mergePreview(p){
  const bad = p.missing.length;
  return `<div class="card wide"><h3>${esc(p.file)} into ${esc(p.plugin)}</h3>
    <p>${p.new} new record${p.new === 1 ? '' : 's'}, ${p.changes} change${p.changes === 1 ? '' : 's'} to other files' records, ${p.same} you both already say alike.</p>
    ${p.masters_added.length ? `<p>Your mod will also need: ${p.masters_added.map(m => `<code>${esc(m)}</code>`).join(' ')}.</p>` : ''}
    ${p.renumbered ? `<p>${p.renumbered} of its records get new object IDs, because you use theirs already. Saves that knew those things as part of ${esc(p.file)} won't recognise them.</p>` : ''}
    ${bad ? `<p class="tl-prob">It needs ${p.missing.map(esc).join(', ')}, not in the game's Data folder. It can't be merged without.</p>` : ''}
    ${p.unknown.length ? `<p class="tl-prob">It has kinds of record FOLab doesn't know (${p.unknown.map(esc).join(', ')}). They come across, but links inside them aren't re-pointed and may end up wrong.</p>` : ''}
    ${p.conflict_count ? `<h3 style="margin-top:10px">Where you disagree: ${p.conflict_count}</h3>
      <p>Your copy is kept unless you tick theirs. <label><input type="checkbox" id="mg-all" ${MG.theirs.size === p.conflicts.length && p.conflicts.length ? 'checked' : ''}> Take theirs for all</label></p>
      ${p.conflicts.map(c => `<div class="tl-row" style="padding:2px 0"><div class="t">${esc(c.edid || c.id)} <span class="note" style="padding:0">${esc(c.word)}</span></div>
        <label><input type="checkbox" data-th="${esc(c.id)}" ${MG.theirs.has(c.id) ? 'checked' : ''}> Take theirs</label></div>`).join('')}` : ''}
    <p class="note" style="padding:8px 0 0">Afterwards the merged plugin is your mod, as if you had opened it: your changes so far become part of it, and the Undo list starts afresh (${p.undo_lost} step${p.undo_lost === 1 ? '' : 's'} now). A copy of how things are is kept first, and can be put back here.</p>
    <p><button class="btn primary" id="mg-go" ${bad ? 'disabled' : ''}>Merge it</button></p></div>`;
}

async function mergeClick(e){
  const pick = e.target.closest('[data-pick]');
  if (pick){
    MG.item = MG.d.candidates[+pick.dataset.pick]; MG.pv = null; MG.theirs = new Set();
    MG.busy = 'Reading both plugins…'; mergeRender();
    try { MG.pv = await post('/api/tools/merge/preview', MG.item); } catch (err){ fail(err); }
    MG.busy = ''; return mergeRender();
  }
  if (e.target.id === 'mg-go'){
    MG.busy = 'Merging… then loading the result on top of the game.'; mergeRender();
    try {
      const d = await post('/api/tools/merge/go', Object.assign({}, MG.item, {prefer: {theirs: [...MG.theirs]}}));
      setState(d.state); await loadPlaces(); if (typeof BW !== 'undefined') BW.types = [];
      toast(`Merged ${d.file}: ${d.added} records added.`);
      MG.pv = null; MG.item = null; MG.busy = '';
      return mergeDraw();
    } catch (err){ fail(err); }
    MG.busy = ''; return mergeRender();
  }
  const r = e.target.closest('[data-restore]');
  if (r){
    if (!confirm(`Put the mod back as it was in "${r.dataset.restore}"? A copy of how it is now is kept.`)) return;
    try { setState(await post('/api/tools/merge/restore', {name: r.dataset.restore})); await loadPlaces(); if (typeof BW !== 'undefined') BW.types = []; toast('Put back.'); mergeDraw(); }
    catch (err){ fail(err); }
  }
}
