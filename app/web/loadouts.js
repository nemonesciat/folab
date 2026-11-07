// ---------- Tools: MO2 loadout ----------
// Mod Organizer 2's profiles on this computer, read from its own files (loadout.py). "Work in this loadout" makes one what the lab
// loads: its plugins, its order, every mod's files. A new patch is a mod made on top of that; Put in MO2 (mo2write.py) adds it.
const LDO = {page: null, look: null, folder: '', profile: '', busy: ''};
TL_TABS.splice(2, 0, ['loadout', 'MO2 loadout', 'Work inside a Mod Organizer 2 profile: its mods, plugins and order', () => ldoDraw()]);

async function ldoDraw(){
  try {
    LDO.page = await api('/api/tools/loadout');
  } catch (e){ $('#tl-body').innerHTML = '<h2>MO2 loadout</h2>' + tlBox(e.message); return; }
  const nv = LDO.page.instances.filter(i => i.new_vegas);
  if (!nv.some(i => i.folder === LDO.folder)){
    const cur = LDO.page.current;
    const first = cur ? nv.find(i => i.folder === cur.folder) : nv[0];
    LDO.folder = first ? first.folder : '';
    LDO.profile = cur && first ? cur.profile : first ? (first.profiles.includes(first.selected) ? first.selected : first.profiles[0] || '') : '';
    LDO.look = null;
  }
  if (LDO.folder && LDO.profile && !LDO.look) await ldoLook();
  ldoRender();
}

async function ldoLook(){
  try { LDO.look = await post('/api/tools/loadout/look', {folder: LDO.folder, profile: LDO.profile}); }
  catch (e){ LDO.look = null; fail(e); }
}

function ldoRender(){
  if (TL.tab !== 'loadout') return;
  const p = LDO.page, nv = p.instances.filter(i => i.new_vegas), inst = nv.find(i => i.folder === LDO.folder);
  const other = p.instances.filter(i => !i.new_vegas);
  const here = p.from_mo2 && p.current ? `<b>Started from MO2:</b> you're working in ${esc(p.current.title)}, ${p.plugins} plugins loaded. Change the profile in MO2.` : p.current ? `You're working in <b>${esc(p.current.title)}</b>: ${p.plugins} plugins loaded.` : `You're working in the plain game: ${p.plugins} plugins loaded, no mods.`;
  $('#tl-body').innerHTML = `<h2>MO2 loadout</h2>
    <p class="note" style="padding:0">Work inside a Mod Organizer 2 profile: its plugins in its order, and each mod's meshes and textures, as the game would see them started from MO2. Choosing one changes nothing in MO2.</p>
    <div class="tl-group" style="padding:10px 14px"><div class="tl-bar" style="margin:0"><span style="flex:1">${here}</span>
      ${p.current && !p.from_mo2 ? '<button class="btn" data-ldo="plain">Back to the plain game</button>' : ''}</div></div>
    ${p.note ? tlBox(p.note) : ''}
    ${p.current ? `<div class="card wide"><h3>Make a patch for this loadout</h3>
      <p class="note" style="padding:0 0 6px">A new mod of your own on top of everything here. The mods you change stay as they are: your patch loads last and its changes win. Edit anything in Browse, then <b>Put in MO2</b> adds it to this profile as its own mod, with a copy of the profile's lists kept first.</p>
      <div class="tl-bar" style="margin:0"><input type="text" id="ldo-patch" placeholder="Name your patch" style="width:300px"><button class="btn primary" data-ldo="patch">New patch</button></div></div>` : ''}
    ${p.left_out.length ? `<details class="tl-group"><summary><b>${p.left_out.length} plugins are on but couldn't be loaded</b><span class="sp"></span></summary><p class="tl-why">Their links would point at the wrong files, so the lab leaves them out.</p>${p.left_out.map(l => `<div class="tl-row"><div class="t">${esc(l.name)}<small>${esc(l.why)}</small></div></div>`).join('')}</details>` : ''}
    ${inst && p.exe && !p.from_mo2 ? `<div class="card wide"><h3>Start FOLab from MO2</h3>${inst.folab_listed ? `<p class="note" style="padding:0">FOLab is on this instance's list. Close FOLab first, then in MO2 choose <b>FOLab</b> in the list above the Run button and press <b>Run</b>. It opens in the profile MO2 has on, and <b>Open in game</b> starts the game with your mods.</p>` :
      `<p class="note" style="padding:0 0 6px">Add FOLab to the list above MO2's Run button, so you can start it from there. It opens in the profile MO2 has on, and can start the game with your mods. MO2 has to be closed for this.</p><button class="btn" data-ldo="runlist">Add FOLab to MO2's list</button>`}</div>` : ''}
    ${p.from_mo2 ? '' : nv.length ? `<div class="tl-bar"><label>Instance <select id="ldo-inst">${nv.map(i => `<option value="${esc(i.folder)}" ${i.folder === LDO.folder ? 'selected' : ''}>${esc(i.name)}</option>`).join('')}</select></label>
      <label>Profile <select id="ldo-prof">${(inst ? inst.profiles : []).map(n => `<option ${n === LDO.profile ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
      ${p.current && p.current.folder === LDO.folder && p.current.profile === LDO.profile ? '<span class="tl-sev ok">Working in this one</span>' : `<button class="btn primary" data-ldo="use" ${LDO.look ? '' : 'disabled'}>Work in this loadout</button>`}</div>` : ldoNone(p)}
    ${LDO.busy ? tlBox(LDO.busy) : ''}
    ${LDO.look ? ldoLookBox(LDO.look) : ''}
    <div class="tl-bar"><label>Somewhere else? <input type="text" id="ldo-folder" placeholder="The folder with ModOrganizer.ini in it" style="width:340px"></label><button class="btn" data-ldo="add">Add</button></div>
    ${other.length ? `<p class="note" style="padding:0">Also found, for other games: ${other.map(i => esc(i.name + ' (' + i.game + ')')).join(', ')}.</p>` : ''}`;
  $('#tl-body').onclick = ldoClick;
  $('#tl-body').onchange = async e => {
    if (e.target.id === 'ldo-inst'){
      LDO.folder = e.target.value;
      const i = LDO.page.instances.find(x => x.folder === LDO.folder);
      LDO.profile = i.profiles.includes(i.selected) ? i.selected : i.profiles[0] || '';
    } else if (e.target.id === 'ldo-prof') LDO.profile = e.target.value;
    else return;
    LDO.look = null; await ldoLook(); ldoRender();
  };
}

function ldoNone(p){
  if (p.programs.length) return tlBox(`MO2 is at ${esc(p.programs[0])}, but no New Vegas instance was found. Open MO2, create an instance for New Vegas, and come back here.`);
  return tlBox('No Mod Organizer 2 instance for New Vegas was found. If you have one somewhere unusual, give its folder below.');
}

function ldoLookBox(l){
  const mods = l.mods.filter(m => !m.separator);
  return `<div class="card wide"><h3>${esc(l.title)}</h3>
    <div class="tl-bar" style="margin:4px 0;gap:6px 18px"><span>Mods on: <b>${l.mods_on}</b> of ${l.mods_all}</span><span>Plugins on: <b>${l.plugins_on}</b></span><span>Files: <b>${l.files}</b></span><span>Files replaced by a later mod: <b>${l.overrides}</b></span></div>
    <p class="note" style="padding:2px 0">Game folder: ${esc(l.data || 'none named')}</p>
    ${l.notes.map(n => `<p class="note" style="padding:2px 0">${esc(n)}</p>`).join('')}
    ${l.missing_mods.length ? `<p class="tl-prob">On in the profile, but their folders are gone: ${l.missing_mods.map(esc).join(', ')}</p>` : ''}
    ${l.left_out.length ? `<p class="tl-prob">${l.left_out.length} plugins that are on couldn't be loaded: ${l.left_out.slice(0, 6).map(x => esc(x.name)).join(', ')}${l.left_out.length > 6 ? '…' : ''}</p>` : ''}</div>
    <details class="tl-group"><summary><b>Mods, highest priority first</b><span class="sp"></span><span class="tl-sev">${mods.length}</span></summary>
      ${l.mods.slice(0, 600).map(m => m.separator ? `<div class="tl-row"><div class="t"><b>${esc(m.name)}</b></div></div>` : `<div class="tl-row"${m.on ? '' : ' style="opacity:.55"'}><div class="t">${esc(m.name)}${m.version ? ' <small style="display:inline">' + esc(m.version) + '</small>' : ''}
        <small>${m.unmanaged ? 'In the game\'s own Data folder' : !m.on ? 'Off' : m.missing ? 'Its folder is gone' : `${m.files} ${m.files === 1 ? 'file' : 'files'} in use${m.overridden ? ', ' + m.overridden + ' replaced by a later mod' : ''}`}${m.plugins.length ? ' · ' + m.plugins.map(esc).join(', ') : ''}</small></div></div>`).join('')}
    </details>`;
}

async function ldoClick(e){
  const b = e.target.closest('[data-ldo]');
  if (!b) return;
  const act = b.dataset.ldo;
  try {
    if (act === 'runlist'){
      const d = await post('/api/tools/loadout/runlist', {folder: LDO.folder});
      LDO.page = d.page; ldoRender();
      return toast('FOLab is on MO2\'s list. Close FOLab, then choose it above the Run button in MO2.');
    }
    if (act === 'patch'){
      const name = $('#ldo-patch').value.trim();
      if (!name) return toast('Give your patch a name first.', true);
      await newMod(name);
      if (A.state.project && A.state.project.name === name && typeof page === 'function') page('browse');
      return;
    }
    if (act === 'add'){
      LDO.page = await post('/api/tools/loadout/add', {folder: $('#ldo-folder').value});
      LDO.folder = '';
      return ldoDraw();
    }
    LDO.busy = act === 'use' ? 'Loading its plugins and looking through its mods. A big setup takes a while…' : 'Going back to the plain game…';
    ldoRender();
    const d = await post('/api/tools/loadout/use', act === 'use' ? {folder: LDO.folder, profile: LDO.profile} : {});
    LDO.busy = '';
    setState(d.state);
    if (typeof loadPlaces === 'function') loadPlaces();
    LDO.page = d.page;
    ldoRender();
    toast(act === 'use' ? 'The lab is working in ' + d.page.current.title + '.' : 'Back to the plain game.');
  } catch (err){ LDO.busy = ''; ldoRender(); fail(err); }
}
