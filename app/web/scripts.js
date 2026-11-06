// ---------- Scripts: read the game's scripts, write your own (the Workshop's Scripts page, for New Vegas's language) ----------
// The list on the left (your mod's first, then the game's), the script in the middle.
const SCR = {rows: [], key: null, data: null, text: '', orig: ''};

async function scrGet(path){
  const d = await api(path);
  if (d.error) throw new Error(d.error);
  return d;
}

(function scrStyle(){
  const st = document.createElement('style');
  st.textContent = `
#sc-side{border-right:1px solid var(--line)}
#sc-side .find{margin:10px 12px 6px}
#sc-inside{display:flex;align-items:center;gap:6px;padding:0 12px 6px;color:var(--muted);font-size:12.5px}
#sc-main{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--bg)}
#sc-head{padding:10px 14px;border-bottom:1px solid var(--line);background:var(--panel)}
#sc-head b{font-size:16px;color:var(--gold2)}#sc-head small{color:var(--muted);margin-left:8px}
#sc-read{flex:1;overflow:auto;margin:0;padding:10px 14px;font:13px/1.5 var(--mono);white-space:pre;tab-size:4}
`;
  document.head.appendChild(st);
})();

$('#page-scripts').innerHTML = `
  <div class="side" id="sc-side">
    <input class="find" id="sc-find" placeholder="Find a script…">
    <label id="sc-inside"><input type="checkbox" id="sc-deep"> Search inside the scripts too</label>
    <div class="h" id="sc-count"></div>
    <div class="list" id="sc-rows"></div>
  </div>
  <div id="sc-main"><div class="note" style="padding:24px">Scripts make things happen in the game. Pick one to read it.</div></div>`;

PAGES.push('scripts');
$('#nav-scripts').onclick = () => page('scripts');
const scrOnPagePrev = onPage;
onPage = function (name){ scrOnPagePrev(name); if (name === 'scripts') scrList(); };

let scrTimer;
$('#sc-find').addEventListener('input', () => { clearTimeout(scrTimer); scrTimer = setTimeout(scrList, 200); });
$('#sc-deep').addEventListener('change', scrList);
$('#sc-rows').addEventListener('click', e => { const r = e.target.closest('.row'); if (r) scrOpen(r.dataset.k); });

async function scrList(){
  const token = SCR.listToken = (SCR.listToken || 0) + 1;
  const d = await scrGet(`/api/scripts?q=${encodeURIComponent($('#sc-find').value)}&inside=${$('#sc-deep').checked ? 1 : 0}`);
  if (token !== SCR.listToken) return;
  SCR.rows = d.rows;
  $('#sc-count').textContent = `${d.rows.length + d.more} script${d.rows.length + d.more === 1 ? '' : 's'}`;
  $('#sc-rows').innerHTML = d.rows.map(r => `<div class="row${r.key === SCR.key ? ' on' : ''}" data-k="${esc(r.key)}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}" title="${r.state === 'new' ? 'your own' : 'changed by your mod'}"></span>` : ''}${esc(r.edid)}<small>${{object: 'on a thing', quest: 'on a quest', effect: 'an effect'}[r.kind]}</small></div></div>`).join('') +
    (d.more ? `<div class="note">…and ${d.more} more: search to narrow it down.</div>` : '');
}

async function scrOpen(key){
  if ($('#page-scripts').style.display === 'none') page('scripts');
  try { SCR.data = await scrGet('/api/scripts/one?key=' + encodeURIComponent(key)); } catch (e){ return fail(e); }
  SCR.key = key; SCR.text = SCR.orig = SCR.data.text;
  document.querySelectorAll('#sc-rows .row').forEach(r => r.classList.toggle('on', r.dataset.k === key));
  const d = SCR.data;
  $('#sc-main').innerHTML = `<div id="sc-head"><b>${esc(d.edid)}</b><small>from ${esc(d.from)}</small></div><pre id="sc-read">${esc(d.text)}</pre>`;
}
