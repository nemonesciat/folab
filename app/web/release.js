// ---------- Get ready to share: clean it, see what it needs, gather its files, write a readme, make a zip ----------
// Nothing is uploaded anywhere: the zip goes into FOLab's own releases folder.
const RL = {d: null, busy: '', tab: 'readme', last: null, replacing: true};

async function relDraw(){
  if (!A.state.project){ $('#tl-body').innerHTML = '<h2>Get ready to share</h2>' + tlBox('Start a mod first.'); return; }
  RL.busy = 'Reading your mod…'; relRender();
  try { RL.d = await api('/api/tools/release'); } catch (e){ RL.busy = ''; $('#tl-body').innerHTML = '<h2>Get ready to share</h2>' + tlBox(e.message); return; }
  RL.busy = ''; relRender();
}

function relRender(){
  if (TL.tab !== 'share') return;
  if (RL.busy && !RL.d){ $('#tl-body').innerHTML = '<h2>Get ready to share</h2>' + tlBox(RL.busy); return; }
  const d = RL.d, r = d.release, s = d.summary, a = d.assets, c = d.cleanable;
  const replacing = a.files.filter(f => f.replaces);
  const kb = n => n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
  $('#tl-body').innerHTML = `<h2>Get ready to share: ${esc(d.name)}</h2>
    <p class="note" style="padding:0">Check it, clean it, describe it, then make a zip. The zip stays on this computer: nothing is uploaded.</p>
    ${RL.busy ? tlBox(RL.busy) : ''}
    <div class="card wide"><h3>1. Check</h3>
      <p>${s.error ? `<span class="tl-sev error">${s.error} will cause trouble</span> ` : '<span class="tl-sev ok">Nothing that will cause trouble</span> '}${s.warn ? `<span class="tl-sev warn">${s.warn} to look at</span> ` : ''}${s.info ? `<span class="tl-sev">${s.info} to know</span>` : ''}
        <button class="btn" id="rl-health">Open the Health check</button></p></div>
    <div class="card wide"><h3>2. Clean</h3>
      <p>${c.same} record${c.same === 1 ? '' : 's'} saying just what the game says, ${c.deleted} deleted thing${c.deleted === 1 ? '' : 's'}.
        ${c.fixes ? 'Cleaning takes out the first and makes the second safe (disabled and sunk). Undo takes it back.' : 'Nothing to clean.'}
        <button class="btn" id="rl-clean" ${c.fixes ? '' : 'disabled'}>Clean it (${c.fixes})</button></p></div>
    <div class="card wide"><h3>3. What players need</h3>
      ${d.masters.map(m => `<div class="tl-row" style="border:0;padding:2px 0"><div class="t"><code>${esc(m.name)}</code> <span class="note" style="padding:0">${esc(m.friendly)}</span>
        ${m.unused ? '<span class="tl-sev warn">nothing uses it</span>' : ''}</div></div>`).join('') || '<p>Nothing besides the game.</p>'}
      ${d.opened && d.masters.some(m => m.unused) ? '<p><button class="btn" id="rl-trim">Remove the masters nothing uses</button> <span class="note" style="padding:0">Rewrites the plugin. A copy is kept first; Undo starts afresh.</span></p>' : ''}
      ${d.masters.some(m => !m.official) ? '<p>Players need those other mods too. Say where to get them in your description.</p>' : ''}</div>
    <div class="card wide"><h3>4. Its own files</h3>
      <p>${a.files.length} file${a.files.length === 1 ? '' : 's'}${a.archives.length ? ` and ${a.archives.length} archive${a.archives.length === 1 ? '' : 's'}` : ''} besides the plugin. Anything your records don't name, like music, goes in <code>${esc(d.extra_dir)}</code>, laid out like Data.</p>
      ${a.missing.length ? `<p class="tl-prob">Missing, so players won't have them either: ${a.missing.slice(0, 12).map(esc).join(', ')}${a.missing.length > 12 ? '…' : ''}</p>` : ''}
      ${replacing.length ? `<p class="tl-prob">${replacing.length} of them replace the game's own files, for everyone, everywhere the game uses them.</p>
        <p><label><input type="checkbox" id="rl-replacing" ${RL.replacing ? 'checked' : ''}> Include the files that replace the game's</label></p>` : ''}
      ${a.files.length || a.archives.length ? `<details><summary class="note" style="padding:4px 0;cursor:pointer">The list</summary><div class="tl-readme">${a.archives.map(esc).concat(a.files.map(f => esc(f.rel) + (f.replaces ? '  (replaces the game\'s)' : ''))).join('\n')}</div></details>` : ''}</div>
    <div class="card wide"><h3>5. Describe it</h3>
      <div class="tl-field">
        <label>Author</label><input id="rl-author" value="${esc(d.author)}">
        <label>Description</label><textarea id="rl-desc" rows="2" placeholder="One or two sentences: what the mod is about">${esc(d.description)}</textarea>
        <label>Version</label><input id="rl-ver" value="${esc(r.version)}" style="max-width:120px">
        <label>What's new</label><input id="rl-notes" value="${esc(r.notes)}" placeholder="${r.changelog.length ? 'e.g. Fixed the door in the basement' : 'First release'}">
        <label>Where to start</label><textarea id="rl-start" rows="2" placeholder="How players find your things. Empty: the console's coc for your new places">${esc(r.start)}</textarea>
        <label>Credits</label><input id="rl-credits" value="${esc(r.credits)}" placeholder="Anyone whose work or help you used">
        <label>Permissions</label><select id="rl-perm">${d.permissions.map(p => `<option ${p === r.permissions ? 'selected' : ''}>${esc(p)}</option>`).join('')}</select>
      </div>
      <p><button class="btn" id="rl-saveinfo">Save and update the readme</button></p>
      <div class="tabs" style="max-width:320px"><button data-rt="readme" class="${RL.tab === 'readme' ? 'on' : ''}">Readme</button><button data-rt="nexus" class="${RL.tab === 'nexus' ? 'on' : ''}">For a mod page</button></div>
      <div class="tl-readme" id="rl-text">${esc(RL.tab === 'readme' ? d.readme : d.nexus)}</div>
      <p><button class="btn" id="rl-copy">Copy it</button></p></div>
    <div class="card wide"><h3>6. Make the zip</h3>
      <p>Saves your plugin, then makes a zip laid out the way mod managers expect, in FOLab's own <code>${esc(d.releases_dir)}</code>.</p>
      <p><button class="btn primary" id="rl-pack">Make the zip</button> <button class="btn" id="rl-folder">Show the folder</button></p>
      ${RL.last ? `<p style="color:var(--green)">Made ${esc(RL.last.file)} (${kb(RL.last.size)}), ${RL.last.names.length} files.</p>
        ${RL.last.missing.length ? `<p class="tl-prob">${RL.last.missing.length} file${RL.last.missing.length === 1 ? '' : 's'} it needs couldn't be found.</p>` : ''}` : ''}
      ${d.releases.length ? d.releases.map(z => `<div class="tl-row" style="border:0;padding:2px 0"><div class="t">${esc(z.file)}</div><span class="note">${kb(z.size)} · ${new Date(z.when * 1000).toLocaleString()}</span></div>`).join('') : ''}</div>`;
  const on = (id, f) => { const el = $(id); if (el) el.onclick = f; };
  on('#rl-health', () => { HC.file = ''; toolsPage('health'); });
  on('#rl-clean', relClean);
  on('#rl-trim', relTrim);
  on('#rl-saveinfo', relSaveInfo);
  on('#rl-pack', relPack);
  on('#rl-folder', () => post('/api/tools/release/folder').catch(fail));
  on('#rl-copy', () => navigator.clipboard.writeText(RL.tab === 'readme' ? d.readme : d.nexus).then(() => toast('Copied.'), fail));
  const rep = $('#rl-replacing');
  if (rep) rep.onchange = () => { RL.replacing = rep.checked; };
  $('#tl-body').querySelectorAll('[data-rt]').forEach(b => b.onclick = () => { RL.tab = b.dataset.rt; relRender(); });
}

function relFields(){
  return {author: $('#rl-author').value, description: $('#rl-desc').value, version: $('#rl-ver').value.trim() || '1.0', notes: $('#rl-notes').value,
          start: $('#rl-start').value, credits: $('#rl-credits').value, permissions: $('#rl-perm').value};
}
async function relSaveInfo(){
  try { RL.d = await post('/api/tools/release/info', relFields()); toast('Saved.'); relRender(); } catch (e){ fail(e); }
}
async function relClean(){
  try {
    const d = await post('/api/tools/release/clean');
    if (d.state && d.state.project) setState(d.state);
    RL.d = d.info;
    toast(`Cleaned ${d.fixed}.${d.failed.length ? ' ' + d.failed[0] : ' Undo takes it back.'}`, d.failed.length);
    relRender();
  } catch (e){ fail(e); }
}
async function relTrim(){
  if (!confirm('Rewrite the plugin without the masters nothing uses? A copy is kept first, and Undo starts afresh.')) return;
  try {
    toast('Rewriting…');
    const d = await post('/api/tools/merge/trim');
    setState(d.state); await loadPlaces();
    toast('Removed: ' + (d.removed.join(', ') || 'nothing'));
    relDraw();
  } catch (e){ fail(e); }
}
async function relPack(){
  try {
    await post('/api/tools/release/info', relFields());
    RL.busy = 'Making the zip…'; relRender();
    RL.last = await post('/api/tools/release/pack', {replacing: RL.replacing});
    if (RL.last.state) setState(RL.last.state);
    toast('Made ' + RL.last.file);
  } catch (e){ fail(e); }
  RL.busy = ''; relDraw();
}
