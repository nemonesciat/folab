// nv-rs's folders of mods, as OpenMW's launcher lists data folders: each folder holds what would go in Data, a lower one
// in the list wins, and the plugins they have are ticked on and put in order. Play puts them in nv-rs's mods folder
// (nvrs.put_in), FOLab's own mod on top. Wraps engineCard and drawModPage (app.js); routes /api/nvrs/setup, /profiles, /play.
(function(){
  const NF = {setup: null, profiles: null};
  const card = engineCard;
  engineCard = function(s){
    const html = card(s);
    if (!(s.nvrs || {}).found) return html;
    return html.replace(/<\/div>$/, '<div id="m-nvrs-folders"><div class="note">Looking at nv-rs\'s folders…</div></div></div>');
  };
  const draw = drawModPage;
  drawModPage = function(){
    draw.apply(this, arguments);
    if (!$('#m-nvrs-folders')) return;
    if (NF.setup) nfDraw();
    nfLoad();
  };

  async function nfLoad(){
    try {
      const [setup, profiles] = await Promise.all([api('/api/nvrs/setup'), NF.profiles ? NF.profiles : api('/api/nvrs/profiles')]);
      NF.setup = setup; NF.profiles = profiles; nfDraw();
    } catch (e){ const b = $('#m-nvrs-folders'); if (b) b.innerHTML = `<p class="note">${esc(e.message || e)}</p>`; }
  }

  async function nfSave(change){
    const s = NF.setup;
    change(s);
    try {
      NF.setup = await post('/api/nvrs/setup', {folders: s.folders.map(f => ({path: f.path, on: f.on})),
                                                plugins: s.plugins.map(p => ({name: p.name, on: p.on})), keep_from: true});
      nfDraw();
    } catch (e){ fail(e); nfLoad(); }
  }

  const move = (list, i, by) => { const j = i + by; if (j < 0 || j >= list.length) return; [list[i], list[j]] = [list[j], list[i]]; };

  function nfDraw(){
    const box = $('#m-nvrs-folders'), s = NF.setup;
    if (!box || !s) return;
    const on = s.folders.filter(f => f.on).length, pon = s.plugins.filter(p => p.on).length;
    box.innerHTML = `<h4 style="margin:14px 0 4px">Folders of mods for nv-rs</h4>
      <p>As in OpenMW's launcher: each folder holds what would go in the game's Data folder (a mod's .esp, .bsa, meshes, textures).
         A folder lower in the list wins where two have the same file; your own mod goes on top of them all.
         Play puts them in nv-rs's <code>mods</code> folder as links (no copies, no space), and takes out again only what FOLab put there.</p>
      ${(NF.profiles || []).length ? `<p>Fill from a Mod Organizer profile: <select id="nf-mo2">${NF.profiles.map((p, i) =>
          `<option value="${i}" ${s.from === p.title ? 'selected' : ''}>${esc(p.title)}</option>`).join('')}</select>
          <button class="btn" id="nf-mo2-use">Use its mods</button>
          ${s.from ? `<span class="note">Filled from ${esc(s.from)}.</span>` : ''}</p>` : ''}
      ${s.note ? `<p class="note">${esc(s.note)}</p>` : ''}
      <div style="max-height:260px;overflow:auto;border:1px solid var(--line, #444);padding:4px">${s.folders.length ? s.folders.map((f, i) => `
        <div class="nf-row" style="display:flex;gap:6px;align-items:center">
          <input type="checkbox" data-fon="${i}" ${f.on ? 'checked' : ''}>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(f.path)}">${esc(f.path)}</span>
          ${f.found ? (f.far ? '<span class="note" title="On another drive than nv-rs: its files are copied each time they change.">copied</span>' : '') : '<span class="note">not found</span>'}
          <button class="btn" data-fup="${i}" title="Lower: loses to the ones under it">↑</button><button class="btn" data-fdown="${i}" title="Higher: wins over the ones above it">↓</button><button class="btn" data-fdel="${i}" title="Take it off the list (the folder stays as it is)">✕</button>
        </div>`).join('') : '<p class="note">No folders yet.</p>'}</div>
      <p><input id="nf-path" placeholder="A folder of a mod, e.g. C:\\Modding\\MO2\\mods\\Some Mod" style="width:360px"> <button class="btn" id="nf-add">Add folder</button></p>
      ${s.plugins.length ? `<p>Plugins in them, in load order (masters load first whatever the order):</p>
      <div style="max-height:260px;overflow:auto;border:1px solid var(--line, #444);padding:4px">${s.plugins.map((p, i) => `
        <div style="display:flex;gap:6px;align-items:center">
          <input type="checkbox" data-pon="${i}" ${p.on ? 'checked' : ''}>
          <span style="flex:1">${esc(p.name)}${p.on && p.needs.length ? ` <span class="note">needs ${p.needs.map(esc).join(', ')}, not on above it</span>` : ''}</span>
          <button class="btn" data-pup="${i}">↑</button><button class="btn" data-pdown="${i}">↓</button>
        </div>`).join('')}</div>` : ''}
      <p>${on} folder${on === 1 ? '' : 's'} and ${pon} plugin${pon === 1 ? '' : 's'} on. Mods that need xNVSE or JIP won't work in nv-rs yet.
         ${on ? '<button class="btn" id="nf-play">Play these in nv-rs</button> <span class="note">(without your mod; Play here and Open in game bring them along too)</span>' : ''}</p>`;
    const all = (sel, f) => box.querySelectorAll(sel).forEach(el => f(el));
    all('[data-fon]', el => el.onchange = () => nfSave(s => { s.folders[+el.dataset.fon].on = el.checked; }));
    all('[data-fup]', el => el.onclick = () => nfSave(s => move(s.folders, +el.dataset.fup, -1)));
    all('[data-fdown]', el => el.onclick = () => nfSave(s => move(s.folders, +el.dataset.fdown, 1)));
    all('[data-fdel]', el => el.onclick = () => nfSave(s => { s.folders.splice(+el.dataset.fdel, 1); }));
    all('[data-pon]', el => el.onchange = () => nfSave(s => { s.plugins[+el.dataset.pon].on = el.checked; }));
    all('[data-pup]', el => el.onclick = () => nfSave(s => move(s.plugins, +el.dataset.pup, -1)));
    all('[data-pdown]', el => el.onclick = () => nfSave(s => move(s.plugins, +el.dataset.pdown, 1)));
    const add = $('#nf-add');
    if (add) add.onclick = () => {
      const path = $('#nf-path').value.trim().replace(/^"|"$/g, '');
      if (path) nfSave(s => { s.folders.push({path, on: true}); });
    };
    const use = $('#nf-mo2-use');
    if (use) use.onclick = async () => {
      const p = NF.profiles[+$('#nf-mo2').value];
      if (s.folders.length && !confirm(`Replace nv-rs's list with the mods on in ${p.title}?`)) return;
      try { NF.setup = await post('/api/nvrs/setup', {mo2: {folder: p.folder, profile: p.profile}}); nfDraw(); toast('nv-rs\'s folders are now ' + p.title + '\'s mods.'); }
      catch (e){ fail(e); }
    };
    const play = $('#nf-play');
    if (play) play.onclick = async () => {
      try {
        toast('Putting the folders in nv-rs…');
        const d = await post('/api/nvrs/play'); setState(d.state);
        const i = d.install;
        toast(`Starting nv-rs with ${i.plugins.length} plugin${i.plugins.length === 1 ? '' : 's'} (${i.linked} files linked${i.copied ? ', ' + i.copied + ' copied' : ''}).` +
              (i.nvse ? ' Some mods have xNVSE plugins, which nv-rs doesn\'t use yet.' : ''));
      } catch (e){ fail(e); }
    };
  }
})();
