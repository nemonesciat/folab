// ---------- Home: where the logo goes. Your mod, the ways in, where you were lately, the guides ----------
// (After the Workshop's Home.) FOLab opens here unless you untick the box; a right-click on the logo is About (listmenu.js).
const HM_CARDS = [
  ['vault', '🏗', 'Build', 'Make a vault', 'Plan and build a place from the game\'s own pieces, then walk it in game.'],
  ['world', '🧭', 'Build', 'The world', 'Fly round any place or the Mojave. Move, add and link things, and shape the land.'],
  ['create', '🔧', 'Make', 'Items', 'Weapons, apparel, aid and ammo in plain fields.'],
  ['characters', '👤', 'Make', 'Characters', 'People and creatures, what they do all day, and filling a place with them.'],
  ['quests', '📜', 'Tell', 'Quests and dialogue', 'Stages, objectives and conversations, and a board of how a quest moves on.'],
  ['scripts', '⌨', 'Tell', 'Scripts', 'Read and write the game\'s scripts, checked as you type.'],
  ['library', '🖼', 'Look up', 'Library', 'Every mesh, texture and sound, and your own files.'],
  ['browse', '🔍', 'Look up', 'Browse', 'Every record in the game, linked to each other.'],
  ['tools', '🩺', 'Finish', 'Tools', 'Health check, load order, your changes, and a zip ready to share.'],
];
const HM_LATELY = 'folab-lately', HM_START = 'folab-start';
const hmStore = {
  get(k, d){ try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
};

(() => {
  const css = document.createElement('style');
  css.textContent = `
  #page-home{flex:1;min-height:0;overflow-y:auto;background:var(--bg)}
  .hm-in{width:min(1040px,100%);margin:0 auto;padding:26px 28px 34px}
  .hm-hero{display:flex;gap:22px;align-items:center;margin-bottom:18px}
  .hm-logo{flex:none;height:112px;color:var(--gold)}.hm-logo svg{height:100%;width:auto;display:block}
  .hm-hero h1{font:600 30px Oswald,'Arial Narrow',sans-serif;color:var(--gold);margin:0 0 2px;letter-spacing:.02em}
  .th-font .hm-hero h1{font-family:var(--ui-font)}
  .hm-hero p{margin:0 0 10px;color:var(--muted)}
  .hm-mod{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.hm-mod b{color:var(--gold2);font-weight:500}.hm-mod input{min-width:260px}
  .hm-others{margin-top:6px;color:var(--muted);font-size:12.5px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  .hm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin:6px 0 20px}
  .hm-card{display:grid;grid-template-columns:auto 1fr;column-gap:10px;align-items:baseline;text-align:left;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;cursor:pointer;color:var(--muted);transition:border-color .15s,background .15s}
  .hm-card:hover{border-color:var(--gold);background:var(--hover)}
  .hm-card .ic{grid-row:1 / 4;font-size:21px;line-height:1.2}
  .hm-card .kick{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--faint)}
  .hm-card b{color:var(--gold2);font-size:15px;font-weight:600}.hm-card .tx{font-size:12.5px;line-height:1.4;margin-top:2px}
  #page-home h2{font-size:13px;color:var(--gold);margin:0 0 7px;font-weight:600}
  .hm-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px}
  .hm-start{color:var(--muted);font-size:12.5px;display:flex;gap:7px;align-items:center}`;
  document.head.appendChild(css);
  const main = document.createElement('main');
  main.id = 'page-home'; main.style.display = 'none';
  $('#page-create').after(main);
  PAGES.push('home');
})();

function homeDraw(){
  const box = $('#page-home'); if (!box) return;
  const s = A.state || {}, p = s.project, others = (s.projects || []).filter(x => !p || x.name !== p.name);
  const places = hmStore.get(HM_LATELY, []).map(id => (A.places || []).find(c => c.id === id)).filter(Boolean).slice(0, 6);
  const mark = document.querySelector('.brand svg.mark');
  const docs = typeof HELP_DOCS !== 'undefined' ? HELP_DOCS : [];
  const word = p ? `${p.changes} change${p.changes === 1 ? '' : 's'}` : '';
  box.innerHTML = `<div class="hm-in">
    <div class="hm-hero"><div class="hm-logo">${mark ? mark.outerHTML : ''}</div><div style="flex:1;min-width:0">
      <h1>FOLab</h1><p>A New Vegas editor. Your changes become a plugin the game loads; the game's own files are never touched.</p>
      <div class="hm-mod">${p
        ? `<span>Working on <b>${esc(p.name)}</b> · ${word}</span><button class="btn" data-hm="mod">My mod</button><button class="btn primary" data-hm="world">Carry on</button>`
        : `<input id="hm-name" placeholder="Name, e.g. My Vault Home"><button class="btn primary" id="hm-new">Start a mod</button>`}</div>
      ${others.length ? `<div class="hm-others">${p ? 'Or open another:' : 'Or open one:'} ${others.slice(0, 8).map(x => `<button class="btn" data-hmopen="${esc(x.name)}">${esc(x.name)}</button>`).join('')}</div>` : ''}
    </div></div>
    <div class="hm-grid">${HM_CARDS.map(([k, ic, kick, title, text]) => `<button class="hm-card" data-hm="${k}"><span class="ic">${ic}</span><span class="kick">${kick}</span><b>${title}</b><span class="tx">${text}</span></button>`).join('')}</div>
    ${places.length ? `<h2>Where you were lately</h2><div class="hm-chips">${places.map(c => `<button class="btn" data-hmplace="${esc(c.id)}">${esc(c.name || c.edid)}</button>`).join('')}</div>` : ''}
    <h2>Guides</h2><div class="hm-chips">${docs.map(([k, label]) => `<button class="btn" data-hmdoc="${esc(k)}">${esc(label.split(':')[0])}</button>`).join('')}<button class="btn" data-hm="keys">The controls</button></div>
    <label class="hm-start"><input type="checkbox" id="hm-onstart" ${hmStore.get(HM_START, true) ? 'checked' : ''}> Open on this page when FOLab starts</label>
  </div>`;
  const hmv = box.querySelector('.hm-logo svg'); if (hmv) hmv.removeAttribute('aria-hidden');
  const name = $('#hm-name');
  if (name){
    const go = () => newMod(name.value);
    $('#hm-new').onclick = go;
    name.addEventListener('keydown', e => { if (e.key === 'Enter') go(); e.stopPropagation(); });
  }
  $('#hm-onstart').onchange = e => hmStore.set(HM_START, e.target.checked);
}

async function homeGo(k){
  if (k === 'keys'){ page('world'); $('#help3d').style.display = 'block'; return; }
  if (k !== 'vault') return page(k);
  if (!A.state.project){ toast('Start a mod first: give it a name above.', true); const n = $('#hm-name'); if (n) n.focus(); return; }
  page('world');
  tab('left', 'places'); tab('right', 'kit'); kitTab();
  const here = (A.places || []).find(c => c.id === A.cellId);
  if (!here || !here.own) newPlaceDialog();                // (a vault goes in a place of your own)
}

$('#page-home').addEventListener('click', e => {
  const t = e.target.closest('[data-hm],[data-hmplace],[data-hmdoc],[data-hmopen]'); if (!t) return;
  if (t.dataset.hm) return homeGo(t.dataset.hm);
  if (t.dataset.hmplace){ page('world'); tab('left', 'places'); return openPlace(t.dataset.hmplace); }
  if (t.dataset.hmdoc) return helpDoc(t.dataset.hmdoc);
  if (t.dataset.hmopen) openMod(t.dataset.hmopen);
});

// the logo goes Home
$('.brand').addEventListener('click', () => page('home'));

// Home is drawn fresh each time it's shown, and when the mod changes while it's showing
{ const was = page; page = name => { was(name); if (name === 'home') homeDraw(); }; }
{ const was = setState; setState = s => { was(s); const h = $('#page-home'); if (h && h.style.display !== 'none' && !h.contains(document.activeElement)) homeDraw(); }; }
{ const was = loadPlaces; loadPlaces = async () => { await was(); const h = $('#page-home'); if (h && h.style.display !== 'none' && !h.contains(document.activeElement)) homeDraw(); }; }
// where you were lately: the newest first, kept in this browser
{ const was = openPlace; openPlace = async (id, ...more) => { hmStore.set(HM_LATELY, [id, ...hmStore.get(HM_LATELY, []).filter(x => x !== id)].slice(0, 12)); return was(id, ...more); }; }

function homeOnStart(){ if (hmStore.get(HM_START, true)) page('home'); }
