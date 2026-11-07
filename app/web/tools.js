// ---------- The Tools page: looking after a mod and sharing it ----------
// A column of tools on the left (Health check, Load order, Mod conflicts, My changes, Get ready to share, Merge), each drawn by its
// own file into #tl-body. Everything talks to /api/tools/... (modtools.py).
const TL = {tab: 'health'};
const TL_TABS = [['health', 'Health check', 'What\'s wrong with a plugin, and the safe fixes', () => healthDraw()],
                 ['loadorder', 'Load order', 'The plugins the game loads: on, off, in what order, who wins', () => loDraw()],
                 ['changes', 'My changes', 'Every change your mod makes, by place and kind', () => mcDraw()],
                 ['share', 'Get ready to share', 'Clean it, gather its files, write a readme, make a zip', () => relDraw()],
                 ['merge', 'Merge a plugin', 'Bring another plugin into your mod', () => mergeDraw()]];

(function tlCss(){
  const c = document.createElement('style');
  c.textContent = `
  #page-tools{flex:1;min-height:0;display:none}
  #tl-side{width:220px;flex:none;border-right:1px solid var(--line);background:var(--panel);overflow-y:auto;padding-top:8px}
  #tl-side .row small{white-space:normal}
  #tl-body{flex:1;overflow-y:auto;padding:22px 30px;min-width:0}
  #tl-body h2{font:600 20px Oswald,'Arial Narrow',sans-serif;color:var(--gold);margin:0 0 4px}
  #tl-body>.card,#tl-body .wide{max-width:1040px}
  .tl-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:10px 0}
  .tl-bar select,.tl-bar input[type=text]{max-width:340px}
  .tl-group{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 0;max-width:1040px}
  .tl-group>summary{list-style:none;cursor:pointer;padding:10px 14px;display:flex;align-items:center;gap:10px}
  .tl-group>summary::-webkit-details-marker{display:none}
  .tl-group>summary::before{content:'▸';color:var(--muted)}
  .tl-group[open]>summary::before{content:'▾'}
  .tl-group>summary b{font-weight:500;color:var(--gold2)}
  .tl-group>summary .sp{flex:1}
  .tl-why{color:var(--muted);padding:0 14px 8px;margin:0;font-size:12.5px}
  .tl-row{display:flex;gap:10px;align-items:center;padding:5px 14px;border-top:1px solid var(--line);font-size:13px}
  .tl-row>.t{flex:1;min-width:0;overflow-wrap:anywhere}
  .tl-row small{display:block;color:var(--faint);font-size:11.5px}
  .tl-row .btn{padding:2px 8px;font-size:12px}
  .tl-sev{font-size:11px;padding:1px 7px;border-radius:9px;white-space:nowrap;border:1px solid var(--line2);color:var(--muted)}
  .tl-sev.error{color:var(--red);border-color:var(--red)} .tl-sev.warn{color:var(--amber);border-color:var(--amber)} .tl-sev.ok{color:var(--green);border-color:var(--green)}
  .tl-more{color:var(--faint);padding:6px 14px;font-size:12px;border-top:1px solid var(--line)}
  .tl-diff{font:12px var(--mono);margin:0;padding:6px 14px 10px;color:var(--muted);white-space:pre-wrap;overflow-wrap:anywhere;border-top:1px solid var(--line)}
  .tl-diff del{color:var(--red);text-decoration:none} .tl-diff ins{color:var(--green);text-decoration:none}
  .tl-table{border-collapse:collapse;width:100%;max-width:1040px;font-size:13px}
  .tl-table th{text-align:left;color:var(--muted);font-weight:500;padding:4px 8px;border-bottom:1px solid var(--line2)}
  .tl-table td{padding:4px 8px;border-bottom:1px solid var(--line);vertical-align:top}
  .tl-table tr.off td{color:var(--faint)} .tl-table tr.drag td{background:var(--sel)}
  .tl-prob{color:var(--red);font-size:12px} .tl-grab{cursor:grab;color:var(--faint);user-select:none}
  .tl-field{display:grid;grid-template-columns:130px 1fr;gap:6px 10px;align-items:start;max-width:720px}
  .tl-field label{color:var(--muted);padding-top:5px}
  .tl-field input,.tl-field textarea,.tl-field select{width:100%;box-sizing:border-box;font:inherit}
  .tl-readme{white-space:pre-wrap;font:12.5px var(--mono);background:var(--bg2);padding:10px 12px;border-radius:8px;max-height:320px;overflow:auto;margin:8px 0}`;
  document.head.appendChild(c);
})();

function toolsPage(tab){
  if (tab) TL.tab = tab;
  const el = $('#page-tools');
  if (!$('#tl-side')){
    el.innerHTML = '<div id="tl-side"></div><div id="tl-body"></div>';
    $('#tl-side').onclick = e => { const r = e.target.closest('[data-tl]'); if (r) toolsPage(r.dataset.tl); };
  }
  $('#tl-side').innerHTML = '<div class="h">Your mod</div>' + TL_TABS.map(([k, l, d]) =>
    `<div class="row${k === TL.tab ? ' on' : ''}" data-tl="${k}" title="${esc(d)}"><div>${esc(l)}<small>${esc(d)}</small></div></div>`).join('');
  TL_TABS.find(t => t[0] === TL.tab)[3]();
}
function toolsOpen(tab){ page('tools'); toolsPage(tab); }

// a click from a tool: the record's page, or the place (and the thing in it) in the view
async function toolGo(go){
  if (!go) return;
  try {
    if (go.record) return openRecord(go.record);
    if (go.world && go.p) await gotoPick({kind: 'spot', world: go.world, name: '', p: go.p});
    else if (go.cell){ page('world'); tab('left', 'places'); await openPlace(go.cell); }
    else return;
    if (go.ref && typeof select === 'function'){ select([go.ref]); if (W.sel && W.sel.length) focusSel(); }
  } catch (e){ fail(e); }
}
const tlBox = (text) => `<div class="note" style="padding:24px 0">${esc(text)}</div>`;
