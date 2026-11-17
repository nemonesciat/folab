// ---------- The Place panel's lists fold away (a tester couldn't get past Suggested to the things found) ----------
// A click on a heading (Prefabs, Recently used, Suggested for this place) folds its list, ▸, or opens it again, ▾;
// remembered. While there's a search typed, Suggested and Recently used fold by themselves so the things found come
// straight up; clearing the search brings them back as you left them.
const PF = {shut: {}, searching: false};
try { PF.shut = JSON.parse(localStorage.getItem('folab-place-fold') || '{}'); } catch (e) {}
const PF_LISTS = [['prefabs', '#prefabs-h', ['#prefabs']], ['recent', '#recent-h', ['#recent']],
                  ['suggested', '#sg-head', ['#sg-like', '#sg-list']]];

function pfApply(){
  for (const [id, head, bodies] of PF_LISTS){
    const h = $(head); if (!h) continue;
    const shut = !!PF.shut[id] || (PF.searching && id !== 'prefabs');
    let mark = h.querySelector('.pf-mark');
    if (!mark){
      mark = document.createElement('span'); mark.className = 'pf-mark';
      mark.style.cssText = 'display:inline-block;width:1.1em;color:var(--gold);cursor:pointer';
      const b = h.querySelector('b'); (b || h).prepend(mark);
      h.style.cursor = 'pointer';
      h.title = 'Click to fold this list away, or open it again';
      h.addEventListener('click', e => {
        if (e.target.closest('button')) return;               // (Suggested's own ↻)
        PF.shut[id] = !(PF.shut[id] || (PF.searching && id !== 'prefabs'));
        if (PF.searching && id !== 'prefabs' && !PF.shut[id]) PF.searching = false;   // (opened by hand while searching: it stays open)
        try { localStorage.setItem('folab-place-fold', JSON.stringify(PF.shut)); } catch (err) {}
        pfApply();
      });
    }
    mark.textContent = shut ? '▸' : '▾';
    for (const b of bodies){ const el = $(b); if (el) el.style.display = shut ? 'none' : ''; }
  }
}
(() => {
  const f = $('#f-place');
  if (f) f.addEventListener('input', () => { const s = !!f.value.trim(); if (s !== PF.searching){ PF.searching = s; pfApply(); } });
  // (the lists are drawn again as places open: the folds kept)
  const _dr = drawRecent;
  drawRecent = () => { _dr(); pfApply(); };
  setTimeout(pfApply, 0);
  new MutationObserver(() => { for (const [id, , bodies] of PF_LISTS){ const shut = !!PF.shut[id] || (PF.searching && id !== 'prefabs');
    for (const b of bodies){ const el = $(b); if (el && shut && el.style.display !== 'none') el.style.display = 'none'; } } })
    .observe($('#tab-place'), {childList: true, subtree: true});
})();
