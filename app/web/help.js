// ---------- Help: the guides, the controls, Report a problem, About ----------
// The guides are Markdown files in web/docs, shown in a window over the page. Getting started opens by itself the
// first time FOLab runs in this browser.
const HELP_DOCS = [['getting-started', 'Getting started'], ['the-world', 'The World page: moving, selecting, placing'],
                   ['outside', 'Outside: land, water, worldspaces'], ['items-and-records', 'Items and records'],
                   ['playing-and-your-mod', 'Playing, and your mod']];

$('#b-help').onclick = e => {
  e.stopPropagation();
  const m = $('#helpmenu');
  m.style.display = m.style.display === 'block' ? 'none' : 'block';
};
document.addEventListener('click', e => { if (!e.target.closest('#helpmenu')) $('#helpmenu').style.display = 'none'; });
$('#helpmenu').innerHTML = HELP_DOCS.map(([k, l]) => `<div class="row" data-doc="${k}"><div>${esc(l)}</div></div>`).join('') +
  `<div class="sep"></div><div class="row" data-help="keys"><div>3D controls</div></div>
   <div class="row" data-help="look"><div>Appearance: themes, text size…</div></div>
   <div class="row" data-help="report"><div>Report a problem…</div></div><div class="row" data-help="about"><div>About FOLab</div></div>`;
$('#helpmenu').addEventListener('click', e => {
  const r = e.target.closest('.row'); if (!r) return;
  $('#helpmenu').style.display = 'none';
  if (r.dataset.doc) return helpDoc(r.dataset.doc);
  if (r.dataset.help === 'keys'){ page('world'); $('#help3d').style.display = 'block'; return; }
  if (r.dataset.help === 'report') return helpReport();
  if (r.dataset.help === 'look') return thWindow();
  if (r.dataset.help === 'about') return helpAbout();
});

function helpWindow(title, html, wide){
  let box = $('#helpwin');
  if (!box){ box = document.createElement('div'); box.id = 'helpwin'; box.className = 'owin'; document.body.appendChild(box); }
  box.style.cssText = `left:50%;top:7%;transform:translateX(-50%);width:${wide ? 760 : 520}px;max-width:94vw;max-height:84vh;display:flex;flex-direction:column`;
  box.innerHTML = `<div class="owtitle"><b>${esc(title)}</b><button class="owx">✕</button></div><div class="helpbody">${html}</div>`;
  box.querySelector('.owx').onclick = () => box.remove();
  const key = e => { if (e.key === 'Escape'){ box.remove(); removeEventListener('keydown', key, true); } };
  addEventListener('keydown', key, true);
  box.addEventListener('click', e => { const a = e.target.closest('[data-doc]'); if (a){ e.preventDefault(); helpDoc(a.dataset.doc); } });
  return box;
}

async function helpDoc(name){
  const r = await fetch('/api/doc?name=' + encodeURIComponent(name));
  const md = r.ok ? await r.text() : '# Not found';
  const title = (md.match(/^# (.+)$/m) || [0, 'Help'])[1];
  const others = HELP_DOCS.filter(([k]) => k !== name).map(([k, l]) => `<a href="#" data-doc="${k}">${esc(l)}</a>`).join(' · ');
  helpWindow(title, mdHtml(md.replace(/^# .+\n/, '')) + `<p class="note" style="padding:12px 0 0">More: ${others}</p>`, true);
}

// a small Markdown: headings, paragraphs, lists, tables, **bold**, *italic*, `code`
function mdHtml(md){
  const inline = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\*([^*]+)\*/g, '<i>$1</i>');
  const out = [], lines = md.split('\n');
  for (let i = 0; i < lines.length; i++){
    const l = lines[i];
    if (/^#{2,3} /.test(l)){ const n = l.match(/^#+/)[0].length; out.push(`<h${n + 1}>${inline(l.slice(n + 1))}</h${n + 1}>`); continue; }
    if (/^\s*\|/.test(l)){
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      i--;
      const cells = r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      const body = rows.filter(r => !/^\s*\|[\s:|-]+\|\s*$/.test(r));
      out.push('<table>' + body.map((r, n) => `<tr>${cells(r).map(c => n ? `<td>${inline(c)}</td>` : `<th>${inline(c)}</th>`).join('')}</tr>`).join('') + '</table>');
      continue;
    }
    if (/^\s*([-*]|\d+\.) /.test(l)){
      const ordered = /^\s*\d+\./.test(l), items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.) /.test(lines[i])){
        let item = lines[i++].replace(/^\s*([-*]|\d+\.) /, '');
        while (i < lines.length && /^ {2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.) /.test(lines[i])) item += ' ' + lines[i++].trim();
        items.push(`<li>${inline(item)}</li>`);
      }
      i--;
      out.push(`<${ordered ? 'ol' : 'ul'}>${items.join('')}</${ordered ? 'ol' : 'ul'}>`);
      continue;
    }
    if (!l.trim()) continue;
    let para = l;
    while (i + 1 < lines.length && lines[i + 1].trim() && !/^(#|\s*\||\s*([-*]|\d+\.) )/.test(lines[i + 1])) para += ' ' + lines[++i];
    out.push(`<p>${inline(para)}</p>`);
  }
  return out.join('\n');
}

async function helpReport(){
  const text = await (await fetch('/api/report')).text();
  const box = helpWindow('Report a problem', `<p>Say what you did and what happened (a screenshot helps), and paste this under it. It has FOLab's version,
    the game's files, your mod's state and the last errors; nothing else of yours.</p>
    <textarea id="rep-text" readonly style="width:100%;height:260px;font:12px Consolas,monospace">${esc(text)}</textarea>
    <p><button class="btn primary" id="rep-copy">Copy it</button> <span class="note" style="padding:0">The full log: <code>logs\\folab.log</code> in FOLab's folder.</span></p>`, true);
  box.querySelector('#rep-copy').onclick = async () => {
    const t = box.querySelector('#rep-text');
    try { await navigator.clipboard.writeText(t.value); } catch (e){ t.select(); document.execCommand('copy'); }
    toast('Copied: paste it into your message');
  };
}

async function helpAbout(){
  const a = await api('/api/about');
  helpWindow('About FOLab', `<p><b>FOLab ${esc(a.version)}</b>, a New Vegas editor. Your changes become a plugin the game loads; the game's own files are never changed.</p>
    <table><tr><th>Game</th><td>${esc(a.game || 'not found')}</td></tr><tr><th>Loaded</th><td>${esc(a.plugins.join(', '))}</td></tr>
    <tr><th>FOLab's folder</th><td>${esc(a.home)}</td></tr><tr><th>Python</th><td>${esc(a.python)} · ${esc(a.system)}</td></tr></table>
    <h3>Made with</h3><p>three.js (MIT licence) for the 3D view, its DDS loader and transform handles; Oswald, Share Tech Mono, Cinzel and Inter fonts (SIL Open Font Licence).
    xNVSE and JIP LN NVSE are their makers' own, downloaded from their pages when you ask.</p>
    <p class="note" style="padding:0">Fallout: New Vegas is Bethesda Softworks' and Obsidian Entertainment's. FOLab isn't made or endorsed by them.</p>`);
}

// the first time FOLab runs in this browser: Getting started (once the page has started)
function helpFirstRun(){
  let seen = true;
  try { seen = !!localStorage.getItem('folab-seen-guide'); } catch (e) {}
  if (seen) return;
  helpDoc('getting-started').then(() => { try { localStorage.setItem('folab-seen-guide', '1'); } catch (e) {} })
    .catch(e => console.error('Getting started', e));
}

// (whatever happens while the page starts, the loading screen goes after 20 s)
setTimeout(() => { const l = $('#loading'); if (l){ l.classList.add('gone'); setTimeout(() => l.remove(), 500); } }, 20000);
