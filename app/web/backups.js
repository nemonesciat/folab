// ---------- Tools: Backups ----------
// FOLab's backups folder (backups.py): how big it is, what's in it by kind, what tidying would delete, and the rules.
// FOLab tidies its own automatic copies by itself; copies of a mod made before a big job go only on a click here.
const BK = {page: null, open: {}, busy: false};
TL_TABS.push(['backups', 'Backups', 'What FOLab kept before changing things, and keeping it from filling the drive', () => bkDraw()]);

(function bkCss(){
  const c = document.createElement('style');
  c.textContent = '#tl-body .muted{color:var(--muted)} #tl-body small.muted{display:block;margin-top:3px}';
  document.head.appendChild(c);
})();

const bkSize =n => n >= 1073741824 ? (n / 1073741824).toFixed(1) + ' GB' : n >= 1048576 ? Math.round(n / 1048576) + ' MB' : n ? Math.max(1, Math.round(n / 1024)) + ' KB' : 'nothing';
const bkWhen = t => t ? new Date(t * 1000).toLocaleString([], {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : 'kept for good';

function bkKindName(k){
  if (k.family === 'file') return `The old ${k.label}, each time FOLab put a new one in`;
  if (k.family === 'mod') return k.label.replace(/ before a big job$/, '') + ': the mod as it was before a big job';
  if (k.family === 'moved') return k.label + ' (moved out of the game)';
  if (k.family === 'other') return k.label + ' (never tidied: FOLab needs it to take things out again)';
  return k.label;
}

async function bkDraw(){
  try { BK.page = await api('/api/tools/backups'); }
  catch (e){ $('#tl-body').innerHTML = '<h2>Backups</h2>' + tlBox(e.message); return; }
  bkRender();
}

function bkRender(){
  const p = BK.page, r = p.rules, dr = p.drive;
  const low = dr && dr.free < 20 * 1073741824;
  const goes = p.kinds.flatMap(k => k.items.filter(i => i.goes).map(i => i.name));
  $('#tl-body').innerHTML = `<h2>Backups</h2>
    <p class="muted" style="max-width:820px">Before FOLab changes something it keeps a copy of how it was: the old plugin each time you put your mod in
      the game, MO2's lists, load orders, game settings, and the whole mod before a big job. These pile up: a big mod's copies are hundreds of MB each.</p>
    <div class="card" style="max-width:1040px">
      <div class="gt-counts"><span>In the backups folder: <b>${bkSize(p.total)}</b></span>
        ${dr ? `<span${low ? ' style="color:var(--red)"' : ''}>Free on its drive: <b>${bkSize(dr.free)}</b> of ${bkSize(dr.total)}</span>` : ''}
        <span>${p.would_delete ? `Tidying would free <b>${bkSize(p.would_free)}</b> (${p.would_delete} cop${p.would_delete === 1 ? 'y' : 'ies'})` : 'Nothing to tidy: every copy is within the rules'}</span></div>
      <div class="tl-bar">
        <button class="btn primary" id="bk-tidy"${goes.length && !BK.busy ? '' : ' disabled'}>${goes.length ? `Tidy up now: delete ${goes.length} old cop${goes.length === 1 ? 'y' : 'ies'}` : 'Tidy up now'}</button>
        <button class="btn" id="bk-folder">Open the folder</button>
      </div>
      <p class="muted" style="margin:4px 0 0;font-size:12.5px">Deleted copies can't be brought back. The newest of every kind always stays, and so does anything from the last hour.
        The ones that would go are marked <span class="tl-sev warn">goes</span> below.</p>
    </div>
    <div class="card" style="max-width:1040px">
      <b>The rules</b>
      <div class="tl-field" style="margin-top:8px">
        <label>Keep the newest</label><div><input id="bk-keep" type="number" min="1" max="99" style="width:70px" value="${r.keep}"> of each kind</div>
        <label>And one a day for</label><div><input id="bk-days" type="number" min="0" max="365" style="width:70px" value="${r.days}"> days</div>
        <label>Keep it under</label><div><input id="bk-cap" type="number" min="0.5" step="0.5" style="width:70px" value="${r.cap_gb}"> GB in all (the oldest go first)</div>
        <label>By itself</label><div><label style="color:inherit;padding-top:0;display:flex;align-items:flex-start"><input id="bk-auto" type="checkbox" style="width:auto;margin-right:6px"${r.auto ? ' checked' : ''}> Tidy FOLab's own automatic copies after each new one
          (old plugins, MO2's lists, load orders, game settings)</label>
          <small class="muted">Copies of a mod made before a big job, and old copies moved out of the game, only go when you click Tidy up.${p.auto_would_free ? ` By itself it would free ${bkSize(p.auto_would_free)} next time.` : ''}</small></div>
      </div>
      <div class="tl-bar"><button class="btn" id="bk-save">Save the rules</button></div>
    </div>
    ${p.kinds.length ? p.kinds.map(k => {
      const n = k.items.filter(i => i.goes).length;
      return `<details class="tl-group"${BK.open[k.kind] ? ' open' : ''} data-bk="${esc(k.kind)}"><summary><b>${esc(bkKindName(k))}</b><span class="sp"></span>
        <span class="muted">${k.items.length} · ${bkSize(k.size)}</span>${n ? ` <span class="tl-sev warn">${n} go${n === 1 ? 'es' : ''}</span>` : ''}</summary>
        ${k.items.map(i => `<div class="tl-row"><div class="t">${esc(i.name)}<small>${bkWhen(i.when)} · ${bkSize(i.size)}</small></div>
          ${i.goes ? '<span class="tl-sev warn">goes</span>' : ''}
          <button class="btn" data-bkdel="${esc(i.name)}" title="Delete this copy now">Delete</button></div>`).join('')}</details>`;
    }).join('') : '<p class="muted">The backups folder is empty.</p>'}`;
  $('#tl-body').querySelectorAll('details[data-bk]').forEach(d => d.addEventListener('toggle', () => { BK.open[d.dataset.bk] = d.open; }));
  $('#bk-folder').onclick = () => post('/api/tools/backups/folder').catch(fail);
  $('#bk-tidy').onclick = () => {
    if (!confirm(`Delete ${goes.length} old cop${goes.length === 1 ? 'y' : 'ies'} from FOLab's backups and free ${bkSize(p.would_free)}?\n\nThey can't be brought back.`)) return;
    bkDelete(goes);
  };
  $('#bk-save').onclick = async () => {
    try {
      BK.page = await post('/api/tools/backups/rules', {keep: +$('#bk-keep').value, days: +$('#bk-days').value, cap_gb: +$('#bk-cap').value, auto: $('#bk-auto').checked});
      bkRender(); toast('Rules saved.');
    } catch (e){ fail(e); }
  };
  $('#tl-body').querySelectorAll('[data-bkdel]').forEach(b => b.onclick = () => {
    if (confirm(`Delete "${b.dataset.bkdel}" from FOLab's backups? It can't be brought back.`)) bkDelete([b.dataset.bkdel]);
  });
}

async function bkDelete(names){
  BK.busy = true; bkRender();
  try {
    BK.page = await post('/api/tools/backups/delete', {names});
    toast(`Deleted ${names.length} cop${names.length === 1 ? 'y' : 'ies'}: ${bkSize(BK.page.freed)} freed.`);
  } catch (e){ fail(e); }
  BK.busy = false; bkRender();
}
