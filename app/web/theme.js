// ---------- How FOLab looks: themes, text size, scanlines, calmer motion ----------
// Each theme is a set of the page's colours (the CSS variables on :root). Kept in this browser (localStorage
// "folab-theme") and put on by the small script at the top of index.html before the page shows, so there's no flash
// of the old colours. Help > Appearance.
const TH_THEMES = {
  mojave: {label: 'Mojave', about: 'Dusk over the desert: dark leather and gold', v: {}},
  pipboy: {label: 'Pip-Boy', about: 'Phosphor green on a black screen, terminal type', mono: true, v: {
    bg: '#050a06', panel: '#08110a', panel2: '#0c180f', line: '#163020', line2: '#1f4a2c', text: '#b7f5c4', muted: '#6fbf85', faint: '#5aa06f',
    gold: '#3df27a', gold2: '#8affac', goldline: '#1f7a3e', hover: '#0f2416', sel: '#123a1f', bg2: '#060d08', bg3: '#0a150c',
    'btn-primary': '#14522a', 'btn-primary-hover': '#1a6a36', red: '#ff7a5c', amber: '#e8f25a', green: '#6dff9a', blue: '#7ad7ff',
    mono: '"Share Tech Mono", ui-monospace, Consolas, monospace'}},
  vaulttec: {label: 'Vault-Tec', about: 'Vault blue and jumpsuit yellow', v: {
    bg: '#0b1424', panel: '#101c31', panel2: '#15243d', line: '#22365a', line2: '#2f4a78', text: '#e6edf8', muted: '#9fb1cf', faint: '#8597b8',
    gold: '#f2c230', gold2: '#ffe07a', goldline: '#8a6e1a', hover: '#182a47', sel: '#223a62', bg2: '#0d1729', bg3: '#122039',
    'btn-primary': '#5c4a10', 'btn-primary-hover': '#735c14'}},
  strip: {label: 'The Strip', about: 'Neon signs on a New Vegas night', v: {
    bg: '#0d0812', panel: '#150d1d', panel2: '#1d1228', line: '#33204a', line2: '#4a2e6a', text: '#f2e6ff', muted: '#b39ccf', faint: '#9c86b8',
    gold: '#ff4fa3', gold2: '#7af0ff', goldline: '#8a2f63', hover: '#24163a', sel: '#3a1d52', bg2: '#100a17', bg3: '#170e21',
    'btn-primary': '#6a1f4c', 'btn-primary-hover': '#82275e', amber: '#ffd35a', green: '#6dffc4'}},
  ncr: {label: 'NCR', about: 'Khaki, olive and the bear\'s red', v: {
    bg: '#16150f', panel: '#1f1e16', panel2: '#29271d', line: '#3b3829', line2: '#4f4b36', text: '#ece6d2', muted: '#a8a084', faint: '#948d73',
    gold: '#c95b3c', gold2: '#e8936f', goldline: '#7a3a27', hover: '#2d2b20', sel: '#3d2a1f', bg2: '#1a1912', bg3: '#211f17',
    'btn-primary': '#6a2f1f', 'btn-primary-hover': '#7e3a27', amber: '#d9b25a'}},
  legion: {label: 'Legion', about: 'Crimson and bone', v: {
    bg: '#120a0a', panel: '#1b0f0f', panel2: '#241313', line: '#3a1c1c', line2: '#522626', text: '#f0e4d8', muted: '#b39a8c', faint: '#9c8578',
    gold: '#e0c9a6', gold2: '#fff0d6', goldline: '#7a2a2a', hover: '#2a1515', sel: '#45181a', bg2: '#150c0c', bg3: '#1c1010',
    'btn-primary': '#7a1f22', 'btn-primary-hover': '#92262a', red: '#ff6a5c'}},
  daylight: {label: 'Daylight', about: 'Light, for bright rooms', light: true, v: {
    bg: '#efe8d8', panel: '#f8f3e8', panel2: '#fffaf0', line: '#dccfb4', line2: '#c9b893', text: '#2b2418', muted: '#6b5f4a', faint: '#7d7058',
    gold: '#9a6412', gold2: '#7a4c08', goldline: '#c9a361', hover: '#ece2cd', sel: '#e6d4ad', bg2: '#fffdf8', bg3: '#f4ecdb',
    'btn-primary': '#e3c27e', 'btn-primary-hover': '#d8b264', red: '#b8432e', amber: '#a87a10', green: '#4f8a3a', blue: '#3c6fa8'}},
};
const TH = {theme: 'mojave', size: 14, scan: false, calm: false};
try { Object.assign(TH, JSON.parse(localStorage.getItem('folab-theme') || '{}')); } catch (e) {}

function thApply(){
  const t = TH_THEMES[TH.theme] || TH_THEMES.mojave, root = document.documentElement;
  for (const k of new Set(Object.values(TH_THEMES).flatMap(x => Object.keys(x.v)))) root.style.removeProperty('--' + k);
  for (const [k, v] of Object.entries(t.v)) root.style.setProperty('--' + k, v);
  root.style.setProperty('--fs', TH.size + 'px');
  root.classList.toggle('th-mono', !!t.mono);
  root.classList.toggle('th-light', !!t.light);
  root.classList.toggle('th-scan', !!TH.scan);
  root.classList.toggle('th-calm', !!TH.calm);
  try { localStorage.setItem('folab-theme', JSON.stringify(TH)); } catch (e) {}
  // the 3D view's backdrop indoors follows the theme
  if (typeof W !== 'undefined' && W.scene && !A.outside) W.scene.background = new T.Color(thView3d());
  if (typeof M !== 'undefined') M.dirty = true;
}
function thView3d(){ const t = TH_THEMES[TH.theme] || {}; return t.light ? 0x6f6656 : t.v && t.v.bg ? parseInt(t.v.bg.slice(1), 16) : 0x0e0c0a; }

function thWindow(){
  const box = helpWindow('Appearance', `<div class="th-grid">${Object.entries(TH_THEMES).map(([k, t]) => `
      <button class="th-card${TH.theme === k ? ' on' : ''}" data-theme="${k}" style="--c-bg:${t.v.bg || '#13110d'};--c-panel:${t.v.panel2 || '#221e18'};--c-gold:${t.v.gold || '#d2a85a'};--c-text:${t.v.text || '#ebe2cf'}">
        <span class="th-sw"><i></i><i></i><i></i></span><b>${esc(t.label)}</b><small>${esc(t.about)}</small></button>`).join('')}</div>
    <h3>Reading</h3>
    <p><label>Text size <select id="th-size">${[13, 14, 15, 16, 17].map(n => `<option ${n === TH.size ? 'selected' : ''}>${n}</option>`).join('')}</select></label></p>
    <p><label><input type="checkbox" id="th-scan" ${TH.scan ? 'checked' : ''}> Pip-Boy screen lines over the page</label><br>
       <label><input type="checkbox" id="th-calm" ${TH.calm ? 'checked' : ''}> Calmer: no fades or slides</label></p>
    <p class="note" style="padding:0">Kept in this browser. The 3D view and the map follow the theme.</p>`, true);
  box.addEventListener('click', e => { const c = e.target.closest('[data-theme]'); if (!c) return; TH.theme = c.dataset.theme; thApply(); box.querySelectorAll('.th-card').forEach(x => x.classList.toggle('on', x === c)); });
  box.querySelector('#th-size').onchange = e => { TH.size = +e.target.value; thApply(); };
  box.querySelector('#th-scan').onchange = e => { TH.scan = e.target.checked; thApply(); };
  box.querySelector('#th-calm').onchange = e => { TH.calm = e.target.checked; thApply(); };
}
thApply();
