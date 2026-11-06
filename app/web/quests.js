// ---------- Quests: list, stages, objectives, targets, conditions, in plain fields ----------
// Three tabs share the page: Quests (here), Dialogue (dialogue.js) and Board (questboard.js). Behind them are the same
// records Browse shows; a result script is compiled as it's saved (api_quests.py), and a script that doesn't compile stops
// the save and says where. The form helpers here (bound fields, link pickers, the conditions editor) are shared.
const QP = {tab: 'quests', rows: [], key: null, view: null, q: null, dirty: false, fns: null, labels: {}, errors: [], check: null, focus: null, editing: null};

(function qpStyle(){
  const st = document.createElement('style');
  st.textContent = `
#page-quests{flex:1;min-height:0}
#qp-side{width:290px;border-right:1px solid var(--line)}
#qp-detail{flex:1;overflow-y:auto;padding:14px 22px 60px;min-width:0}
.qp-bar{display:flex;gap:6px;margin:10px 12px 6px}.qp-bar input{flex:1;min-width:0}
.qp-grid{display:grid;grid-template-columns:170px 1fr;gap:6px 12px;align-items:center;max-width:820px;margin:8px 0}
.qp-grid>label,.qp-lab{color:var(--muted);font-size:12.5px}
.qp-grid input[type=text],.qp-grid input:not([type]),.qp-grid input[type=number]{width:260px}
.qp-flags{display:flex;flex-wrap:wrap;gap:4px 16px;color:var(--muted);font-size:13px;align-items:center}.qp-flags label{display:inline-flex;gap:5px;align-items:center;cursor:pointer}
.qp-card{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:8px 12px;margin:8px 0;max-width:860px}
.qp-card.bad{border-color:var(--red)}.qp-card.hot{box-shadow:0 0 0 2px var(--gold)}
.qp-card h4{margin:0;font-size:13px;color:var(--gold2);font-weight:500;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.qp-card h4 input{width:74px}.qp-card .x{margin-left:auto}
.qp-entry{border-top:1px dashed var(--line2);margin-top:8px;padding-top:6px}
.qp-entry:first-of-type{border-top:0;margin-top:2px}
textarea.qp-text,textarea.qp-code{width:100%;background:var(--bg2);border:1px solid var(--line2);border-radius:6px;color:var(--text);padding:5px 8px;font:inherit;resize:vertical;display:block}
textarea.qp-code{font-family:var(--mono);font-size:12.5px}
textarea.qp-text:focus,textarea.qp-code:focus{outline:none;border-color:var(--gold)}
.qp-sub{color:var(--muted);font-size:12px;margin:6px 0 2px}
.qp-sec{display:flex;align-items:center;gap:10px;margin:18px 0 2px;max-width:860px}.qp-sec .h{padding:0}
.qp-err{color:#f3b2a5;font-size:12.5px;margin:3px 0}
.qp-note{color:var(--faint);font-size:12px}
.qp-cond{display:flex;gap:6px;align-items:baseline;padding:2px 0;font-size:13px}
.qp-cond .w{flex:1;min-width:0;cursor:pointer}.qp-cond .w:hover{color:var(--gold2)}.qp-cond .or{color:var(--amber);font-size:11.5px}
.qp-condedit{display:flex;flex-wrap:wrap;gap:6px;align-items:center;background:var(--bg2);border:1px solid var(--line2);border-radius:7px;padding:6px 8px;margin:3px 0 5px;font-size:12.5px}
.qp-condedit select,.qp-condedit input{padding:2px 5px;font-size:12.5px}.qp-condedit input[type=number]{width:74px}.qp-condedit select.fn{max-width:220px}
.btn.sm{padding:1px 7px;font-size:12px}
.qp-link{display:inline-flex;gap:6px;align-items:center;position:relative;min-width:0}.qp-link .now{color:var(--gold);max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qp-link input{width:150px}.qp-picks{position:absolute;left:0;top:100%;z-index:30;background:var(--panel2);border:1px solid var(--line2);border-radius:7px;max-height:260px;overflow-y:auto;min-width:320px;box-shadow:0 8px 24px #0008}
.qp-picks div{padding:3px 9px;cursor:pointer;font-size:12.5px;white-space:nowrap}.qp-picks div:hover{background:var(--hover);color:var(--gold2)}
.qp-check{background:var(--panel);border:1px solid var(--goldline);border-radius:9px;padding:8px 12px;margin:8px 0;max-width:860px}
.qp-check h4{margin:0 0 4px;color:var(--gold2);font-weight:500;font-size:13.5px;display:flex;gap:8px;align-items:center}.qp-check h4 button{margin-left:auto}
.qp-item{display:flex;gap:7px;padding:2px 3px;font-size:13px;border-radius:5px;cursor:pointer}.qp-item:hover{background:var(--hover)}
.qp-item b{flex:none;font-weight:600;width:14px;text-align:center}.qp-item.problem b{color:var(--red)}.qp-item.note b{color:var(--amber)}
.qp-empty{padding:30px 24px;color:var(--muted);max-width:640px;line-height:1.6}`;
  document.head.appendChild(st);
})();

// ---------- getting at a nested value by its path ----------
function qpGet(root, path){ return path.split('.').reduce((o, k) => (o == null ? o : o[k]), root); }
function qpSet(root, path, v){
  const ks = path.split('.'), last = ks.pop();
  const o = ks.reduce((x, k) => (x[k] == null ? (x[k] = {}) : x[k]), root);
  o[last] = v;
}
function qpVal(el){
  if (el.type === 'checkbox') return el.checked;
  if (el.type === 'number' || el.dataset.num !== undefined){ const n = parseFloat(el.value); return isNaN(n) ? 0 : n; }
  return el.value;
}
// every [data-b="path"] in a box writes to its place in root; a field marked data-redraw draws the form again
function qpBind(box, root, dirty, redraw){
  box.oninput = e => {
    const el = e.target.closest('[data-b]'); if (!el) return;
    qpSet(root(), el.dataset.b, qpVal(el)); dirty();
  };
  box.onchange = e => {
    const el = e.target.closest('[data-b]');
    if (el && el.dataset.redraw !== undefined){ qpSet(root(), el.dataset.b, qpVal(el)); dirty(); redraw(); }
  };
}

// ---------- a link to a form: its name, and an editor ID to change it ----------
function qpLabel(key){ return key ? (QP.labels[key] || key) : ''; }
function qpLink(path, key, types, opts){
  const o = opts || {};
  return `<span class="qp-link" data-link="${esc(path)}" data-types="${esc((types || []).join(' '))}">
    <span class="now" title="${esc(key || '')}">${key ? esc(qpLabel(key)) : '<i>none</i>'}</span>
    <input placeholder="${esc(o.hint || 'Editor ID…')}" autocomplete="off" title="Type part of an editor ID, then pick">
    ${key && !o.required ? `<button class="btn sm" data-unlink="${esc(path)}" title="Link nothing">✕</button>` : ''}</span>`;
}
let qpPickTimer;
function qpLinkEvents(box, root, dirty, redraw){
  box.addEventListener('input', e => {
    const wrap = e.target.closest('.qp-link'); if (!wrap || e.target.tagName !== 'INPUT') return;
    clearTimeout(qpPickTimer);
    qpPickTimer = setTimeout(async () => {
      const q = e.target.value.trim();
      wrap.querySelector('.qp-picks')?.remove();
      if (q.length < 2) return;
      const r = await api('/api/quest/pick?' + new URLSearchParams({q, types: wrap.dataset.types}));
      const hits = r.hits;
      const div = document.createElement('div'); div.className = 'qp-picks';
      div.innerHTML = hits.length ? hits.map(h => `<div data-k="${esc(h.key)}" data-l="${esc(h.label)}">${esc(h.label)}</div>`).join('')
        : `<div style="color:var(--faint);cursor:default">${r.busy ? 'Still reading the game: try again in a moment.' : 'Nothing with that editor ID.'}</div>`;
      wrap.appendChild(div);
    }, 180);
  });
  box.addEventListener('click', e => {
    const pick = e.target.closest('.qp-picks [data-k]');
    if (pick){
      const wrap = pick.closest('.qp-link');
      QP.labels[pick.dataset.k] = pick.dataset.l.replace(/ \(\w+\)$/, '');
      qpSet(root(), wrap.dataset.link, pick.dataset.k); dirty(); redraw();
      return;
    }
    const un = e.target.closest('[data-unlink]');
    if (un){ qpSet(root(), un.dataset.unlink, ''); dirty(); redraw(); }
  });
}
document.addEventListener('click', e => { if (!e.target.closest('.qp-link')) document.querySelectorAll('.qp-picks').forEach(p => p.remove()); });

// ---------- conditions: each in plain words; click to change it ----------
const QP_OPS = ['=', '!=', '>', '>=', '<', '<='];
const QP_OPWORD = {'=': 'is', '!=': 'is not', '>': 'is over', '>=': 'is at least', '<': 'is under', '<=': 'is at most'};
const QP_RUN = [[0, 'The speaker'], [1, 'The player'], [2, 'A chosen thing'], [3, 'Their combat target'], [4, 'Their linked ref']];
async function qpFns(){ if (!QP.fns) QP.fns = await api('/api/quest/functions'); return QP.fns; }

function qpConds(path, conds, title){
  const editing = QP.editing;
  const rows = (conds || []).map((c, i) => {
    const p = `${path}.${i}`;
    if (editing === p) return qpCondEdit(p, c);
    return `<div class="qp-cond"><span class="w" data-cedit="${esc(p)}" title="Click to change">${esc(c.words || '(new condition)')}</span>${c.or ? '<span class="or">or…</span>' : ''}<button class="btn sm" data-cdel="${esc(p)}" title="Take this condition away">✕</button></div>`;
  }).join('');
  return `<div class="qp-sub">${esc(title || 'Only when')} ${(conds || []).length ? '' : '<span class="qp-note">always</span>'} <button class="btn sm" data-cadd="${esc(path)}">＋ Condition</button></div>${rows}`;
}
function qpCondEdit(p, c){
  const fns = QP.fns || [], fn = fns.find(f => f.fn === c.fn) || {params: [], name: 'Function ' + c.fn, ref: true};
  const common = fns.filter(f => f.rank < 999), rest = fns.filter(f => f.rank >= 999);
  const opt = f => `<option value="${f.fn}"${f.fn === c.fn ? ' selected' : ''}>${esc(f.name)}</option>`;
  let params = '';
  fn.params.forEach((pr, n) => {
    const v = n ? c.p2 : c.p1, pp = `${p}.p${n + 1}`;
    if (pr.kind === 'form') params += `<span class="qp-lab">${esc(pr.label)}</span>${qpLink(pp, typeof v === 'string' ? v : '', pr.types, {required: true})}`;
    else if (pr.kind === 'list') params += `<span class="qp-lab">${esc(pr.label)}</span><select data-b="${esc(pp)}" data-num>${pr.options.map(([k, l]) => `<option value="${k}"${k === v ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>`;
    else params += `<span class="qp-lab">${esc(pr.label)}</span><input type="number" data-b="${esc(pp)}" value="${typeof v === 'number' ? v : 0}">`;
  });
  const isGlobal = 'global' in c;
  return `<div class="qp-condedit">
    ${fn.ref ? `<select data-b="${esc(p)}.run" data-num data-redraw>${QP_RUN.map(([k, l]) => `<option value="${k}"${k === (c.run || 0) ? ' selected' : ''}>${l}</option>`).join('')}</select>` : ''}
    ${(c.run || 0) === 2 && fn.ref ? qpLink(`${p}.ref`, c.ref, [], {required: true, hint: 'A thing with an editor ID…'}) : ''}
    <select class="fn" data-cfn="${esc(p)}"><optgroup label="Common">${common.map(opt).join('')}</optgroup><optgroup label="Every function">${rest.map(opt).join('')}</optgroup></select>
    ${params}
    <select data-b="${esc(p)}.op">${QP_OPS.map(o => `<option value="${o}"${o === c.op ? ' selected' : ''}>${QP_OPWORD[o]}</option>`).join('')}</select>
    ${isGlobal ? qpLink(`${p}.global`, c.global, ['GLOB'], {required: true}) : `<input type="number" step="any" data-b="${esc(p)}.value" value="${+(c.value || 0)}">`}
    <label title="Compare with a global variable instead of a number"><input type="checkbox" data-cglobal="${esc(p)}"${isGlobal ? ' checked' : ''}> a global</label>
    <label title="This condition or the next one is enough"><input type="checkbox" data-b="${esc(p)}.or"${c.or ? ' checked' : ''}> or the next</label>
    <button class="btn sm primary" data-cdone="${esc(p)}">Done</button></div>`;
}
function qpCondEvents(box, root, dirty, redraw){
  box.addEventListener('click', async e => {
    const t = e.target;
    if (t.dataset.cedit){ await qpFns(); QP.editing = t.dataset.cedit; return redraw(); }
    if (t.dataset.cadd){
      await qpFns();
      const list = qpGet(root(), t.dataset.cadd) || [];
      list.push({or: false, op: '=', fn: 58, p1: '', p2: 0, run: 0, ref: '', value: 10.0, words: ''});
      qpSet(root(), t.dataset.cadd, list);
      QP.editing = `${t.dataset.cadd}.${list.length - 1}`; dirty(); return redraw();
    }
    if (t.dataset.cdel){
      const ks = t.dataset.cdel.split('.'), i = +ks.pop(), list = qpGet(root(), ks.join('.'));
      list.splice(i, 1); QP.editing = null; dirty(); return redraw();
    }
    if (t.dataset.cdone){
      const c = qpGet(root(), t.dataset.cdone);
      const fn = (QP.fns || []).find(f => f.fn === c.fn);
      if (fn) for (let n = 0; n < fn.params.length; n++){
        if (fn.params[n].kind === 'form' && !(n ? c.p2 : c.p1)) return toast(`Pick the ${fn.params[n].label} first.`, true);
      }
      try { [c.words] = await post('/api/quest/words', {conditions: [c]}); } catch (err){ fail(err); }
      QP.editing = null; return redraw();
    }
  });
  box.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.cfn){
      const c = qpGet(root(), t.dataset.cfn), fn = QP.fns.find(f => f.fn === +t.value);
      c.fn = +t.value;
      c.p1 = fn.params[0] && fn.params[0].kind === 'form' ? '' : 0;
      c.p2 = fn.params[1] && fn.params[1].kind === 'form' ? '' : 0;
      dirty(); redraw();
    }
    if (t.dataset.cglobal){
      const c = qpGet(root(), t.dataset.cglobal);
      if (t.checked){ c.global = ''; c.value = 0; } else delete c.global;
      dirty(); redraw();
    }
  });
}
// (pointing at a result script's error by where it is)
function qpErrorsFor(list, where){ return (list || []).filter(e => e.where === where).map(e => `<div class="qp-err">✗ ${e.line ? 'Line ' + e.line + ': ' : ''}${esc(e.message)}</div>`).join(''); }

// ---------- the page ----------
function qpDraw(){
  const el = $('#page-quests');
  if (!$('#qp-side')){
    el.innerHTML = `<div class="side" id="qp-side"><div class="tabs" id="qp-tabs">
        <button data-qt="quests">Quests</button><button data-qt="dialogue">Dialogue</button><button data-qt="board">Board</button></div>
      <div id="qp-left" style="display:flex;flex-direction:column;flex:1;min-height:0"></div></div>
      <div id="qp-detail"></div>`;
    $('#qp-tabs').onclick = e => { const b = e.target.closest('button'); if (b) qpTab(b.dataset.qt); };
    const box = $('#qp-detail');
    qpBindDetail(box);
  }
  qpTab(QP.tab);
}
function qpLeaveOk(){
  if (QP.dirty && !confirm('Leave without saving your changes?')) return false;
  QP.dirty = false; return true;
}
function qpTab(t){
  if (t !== QP.tab && !qpLeaveOk()) return;
  QP.tab = t;
  document.querySelectorAll('#qp-tabs button').forEach(b => b.classList.toggle('on', b.dataset.qt === t));
  if (t === 'quests') qpLeft();
  if (t === 'dialogue') dlOpen();
  if (t === 'board') qbOpen();
}
function qpBindDetail(box){
  const root = () => QP.tab === 'dialogue' ? DL.edit : QP.q;
  const dirty = () => { QP.dirty = true; const b = $('#qp-detail [data-qa="save"]'); if (b) b.disabled = false; };
  const redraw = () => { if (QP.tab === 'dialogue') dlDrawEditor(); else qpDrawQuest(); };
  qpBind(box, root, dirty, redraw);
  qpLinkEvents(box, root, dirty, redraw);
  qpCondEvents(box, root, dirty, redraw);
  box.addEventListener('click', qpClick);
}

function qpLeft(){
  $('#qp-left').innerHTML = `<div class="qp-bar"><input id="qp-find" placeholder="Find a quest…"><button class="btn" id="qp-new" title="A quest of your own">＋ New</button></div><div class="list" id="qp-rows"></div>`;
  let timer;
  $('#qp-find').oninput = () => { clearTimeout(timer); timer = setTimeout(qpList, 200); };
  $('#qp-new').onclick = qpNew;
  $('#qp-rows').onclick = e => { const r = e.target.closest('.row[data-k]'); if (r) qpOpen(r.dataset.k); };
  qpList();
  if (QP.q) qpDrawQuest(); else $('#qp-detail').innerHTML = `<div class="qp-empty">Pick a quest, or make one with <b>＋ New</b>. A quest holds stages (each with its journal text and a script that runs when it's set), objectives with their map markers, and the dialogue that belongs to it.</div>`;
}
async function qpList(){
  const token = QP.token = (QP.token || 0) + 1;
  const f = $('#qp-find');
  const rows = await api('/api/quest/list?q=' + encodeURIComponent(f ? f.value : ''));
  if (token !== QP.token || !$('#qp-rows')) return;
  QP.rows = rows;
  const row = r => `<div class="row${r.key === QP.key ? ' on' : ''}" data-k="${esc(r.key)}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}" title="${r.state === 'new' ? 'your own' : 'changed by your mod'}"></span>` : ''}${esc(r.name || r.edid)}<small>${esc(r.edid)}</small></div></div>`;
  const mine = rows.filter(r => r.state);
  $('#qp-rows').innerHTML = (mine.length ? '<div class="h">Yours</div>' + mine.map(row).join('') + '<div class="h">The game\'s</div>' : '') + rows.filter(r => !r.state).map(row).join('');
}
async function qpNew(){
  if (!A.state.project) return toast('Start a mod first (My mod).', true);
  const name = prompt('The quest\'s name, as the journal shows it:', 'My Quest'); if (!name) return;
  if (!qpLeaveOk()) return;
  try { const r = await post('/api/quest/new', {name}); setState(r.state); await qpList(); qpOpen(r.made[0]); } catch (e){ fail(e); }
}
async function qpOpen(key, focus){
  if (key !== QP.key && !qpLeaveOk()) return;
  try {
    const d = await api('/api/quest/open?key=' + encodeURIComponent(key));
    QP.key = key; QP.view = d; QP.q = d.quest; QP.dirty = false; QP.errors = []; QP.editing = null; QP.check = null; QP.focus = focus || null;
    Object.assign(QP.labels, d.links);
    document.querySelectorAll('#qp-rows .row').forEach(r => r.classList.toggle('on', r.dataset.k === key));
    qpDrawQuest();
  } catch (e){ fail(e); }
}
function qpDrawQuest(){
  const q = QP.q, d = QP.view; if (!q || !d) return;
  const box = $('#qp-detail'), scroll = box.scrollTop;
  const state = {'': 'From ' + d.from + ': saving changes it in your mod', changed: 'Changed by your mod (from ' + d.from + ')', new: 'Your own quest'}[d.state];
  const errs = QP.errors || [];
  const stage = (st, si) => {
    const p = `stages.${si}`;
    const bad = errs.some(e => e.where === 'Stage ' + st.index || e.where.startsWith('Stage ' + st.index + ' '));
    return `<div class="qp-card${bad ? ' bad' : ''}${QP.focus && QP.focus.stage === st.index ? ' hot' : ''}" data-stage="${st.index}">
      <h4>Stage <input type="number" data-b="${p}.index" value="${st.index}" title="Its number: scripts set it with SetStage">
      ${(st.entries || []).length > 1 ? '' : qpEntryFlags(`${p}.entries.0`, (st.entries || [])[0])}
      <button class="btn sm x" data-qa="delstage" data-i="${si}" title="Take this stage away">✕</button></h4>
      ${(st.entries || []).map((e, ei) => qpEntry(`${p}.entries.${ei}`, e, st, ei)).join('')}
      <button class="btn sm" data-qa="addentry" data-i="${si}" title="Another journal text for this stage, chosen by its own conditions">＋ Another text</button></div>`;
  };
  const objective = (o, oi) => {
    const p = `objectives.${oi}`;
    return `<div class="qp-card${QP.focus && QP.focus.objective === o.index ? ' hot' : ''}" data-objective="${o.index}"><h4>Objective <input type="number" data-b="${p}.index" value="${o.index}">
      <button class="btn sm x" data-qa="delobj" data-i="${oi}">✕</button></h4>
      <input data-b="${p}.text" value="${esc(o.text || '')}" placeholder="What the Pip-Boy says to do" style="width:100%;margin-top:5px">
      <div class="qp-note" style="margin-top:4px">Shown and completed by scripts: <code>SetObjectiveDisplayed ${esc(q.edid)} ${o.index} 1</code>, <code>SetObjectiveCompleted ${esc(q.edid)} ${o.index} 1</code></div>
      <div class="qp-sub">Map markers <button class="btn sm" data-qa="addtarget" data-i="${oi}">＋ Target</button></div>
      ${(o.targets || []).map((t, ti) => `<div class="qp-entry"><div class="qp-flags">${qpLink(`${p}.targets.${ti}.target`, t.target, ['REFR', 'ACHR', 'ACRE'], {required: true, hint: 'A placed thing\'s editor ID…'})}
        <label title="The marker points the way through locked doors"><input type="checkbox" data-tflag="${p}.targets.${ti}"${t.flags & 1 ? ' checked' : ''}> ignores locks</label>
        <button class="btn sm" data-qa="deltarget" data-i="${oi}" data-j="${ti}">✕</button></div>
        ${qpConds(`${p}.targets.${ti}.conditions`, t.conditions, 'This marker only when')}</div>`).join('')}</div>`;
  };
  box.innerHTML = `<div class="bwtitle"><b>${esc(q.name || q.edid)}</b><small>QUST · ${esc(d.key)} · ${esc(state)}</small></div>
    <div class="acts" style="padding-left:0">
      <button class="btn primary" data-qa="save"${QP.dirty ? '' : ' disabled'}>Save</button>
      <button class="btn" data-qa="check" title="Stages nothing sets, objectives nothing completes, topics nobody can reach, scripts that don't compile">✓ Check this quest</button>
      <button class="btn" data-qa="board">Board</button>
      <button class="btn" data-qa="talk">Its dialogue</button>
      <button class="btn" data-qa="copy" title="A quest of your own with the same stages and objectives. Its dialogue stays with this one.">Make a copy</button>
      ${d.state === 'changed' ? '<button class="btn" data-qa="revert">Put back as the game has it</button>' : ''}
      ${d.state === 'new' ? '<button class="btn" data-qa="revert">Delete this quest</button>' : ''}
    </div>
    ${errs.length ? `<div class="qp-check" style="border-color:var(--red)"><h4>Not saved: a script doesn't compile</h4>${errs.map(e => `<div class="qp-err">${esc(e.where)}${e.line ? ', line ' + e.line : ''}: ${esc(e.message)}</div>`).join('')}</div>` : ''}
    ${qpCheckHtml()}
    <div class="qp-grid">
      <label>Name in the journal</label><input data-b="name" value="${esc(q.name || '')}" placeholder="No name: it stays out of the journal">
      <label>Editor ID</label><input data-b="edid" value="${esc(q.edid || '')}" title="How scripts name it: no spaces">
      <label>Quest script</label>${qpLink('script', q.script, ['SCPT'], {hint: 'A script\'s editor ID…'})}
      <label>Priority</label><input type="number" data-b="priority" value="${q.priority}" min="0" max="255" title="When two quests have a line for the same moment, the higher one speaks">
      <label>Script runs every (seconds)</label><input type="number" step="any" data-b="delay" value="${q.delay == null ? '' : q.delay}" title="How often the quest script runs">
      <label></label><div class="qp-flags">
        <label title="Running from the start of a game, and from the next load of an old save"><input type="checkbox" data-b="flags.start_enabled"${q.flags.start_enabled ? ' checked' : ''}> Starts with the game</label>
        <label><input type="checkbox" data-b="flags.repeat_topics"${q.flags.repeat_topics ? ' checked' : ''}> Topics can repeat</label>
        <label><input type="checkbox" data-b="flags.repeat_stages"${q.flags.repeat_stages ? ' checked' : ''}> Stages can be set again</label></div>
    </div>
    ${qpConds('conditions', q.conditions, 'Runs only when')}
    <div class="qp-sec"><div class="h">Stages · ${(q.stages || []).length}</div><button class="btn sm" data-qa="addstage">＋ Stage</button></div>
    ${(q.stages || []).map(stage).join('') || '<div class="qp-note">No stages yet. Stages are how a quest moves on: a line or a script says SetStage, and that stage\'s journal text and script happen.</div>'}
    <div class="qp-sec"><div class="h">Objectives · ${(q.objectives || []).length}</div><button class="btn sm" data-qa="addobj">＋ Objective</button></div>
    ${(q.objectives || []).map(objective).join('') || '<div class="qp-note">No objectives yet.</div>'}`;
  box.scrollTop = scroll;
  if (QP.focus){
    const t = box.querySelector(QP.focus.stage != null ? `[data-stage="${QP.focus.stage}"]` : `[data-objective="${QP.focus.objective}"]`);
    if (t) t.scrollIntoView({block: 'center'});
    QP.focus = null;
  }
}
function qpEntryFlags(p, e){
  if (!e) return '';
  return `<span class="qp-flags" style="font-weight:400"><label><input type="checkbox" data-b="${p}.flags.complete"${e.flags && e.flags.complete ? ' checked' : ''}> Completes the quest</label>
    <label><input type="checkbox" data-b="${p}.flags.fail"${e.flags && e.flags.fail ? ' checked' : ''}> Fails it</label></span>`;
}
function qpEntry(p, e, st, ei){
  const where = 'Stage ' + st.index + (ei ? ' entry ' + (ei + 1) : '');
  return `<div class="qp-entry">
    ${st.entries.length > 1 ? `<div class="qp-flags">${qpEntryFlags(p, e)}<button class="btn sm" data-qa="delentry" data-p="${esc(p)}">✕</button></div>` : ''}
    <div class="qp-sub">Journal text</div><textarea class="qp-text" rows="2" data-b="${p}.log" placeholder="What the Pip-Boy's quest log adds (none: nothing)">${esc(e.log || '')}</textarea>
    ${qpConds(`${p}.conditions`, e.conditions, 'This text only when')}
    <div class="qp-sub">Script when the stage is set</div><textarea class="qp-code" rows="${Math.min(10, Math.max(2, ((e.script && e.script.source) || '').split('\n').length + 1))}" data-b="${p}.script.source" spellcheck="false" placeholder="e.g. SetObjectiveDisplayed ${esc(QP.q.edid)} 10 1">${esc((e.script && e.script.source) || '')}</textarea>
    ${qpErrorsFor(QP.errors, where)}
    <div class="qp-flags" style="margin-top:4px"><span class="qp-lab">Next quest</span>${qpLink(`${p}.next`, e.next, ['QUST'], {hint: 'Only a few of the game\'s use this…'})}</div></div>`;
}
function qpCheckHtml(){
  const c = QP.check; if (!c) return '';
  return `<div class="qp-check"><h4>${c.problems ? c.problems + ' problem' + (c.problems === 1 ? '' : 's') : 'No problems found'}${c.notes ? ', ' + c.notes + ' to look at' : ''} <button class="btn sm" data-qa="uncheck">Close</button></h4>
    ${c.items.map((x, i) => `<div class="qp-item ${x.level}" data-qgo="${i}"><b>${x.level === 'problem' ? '✗' : '!'}</b><span>${esc(x.text)}</span></div>`).join('') || '<div class="qp-note">Nothing to report.</div>'}</div>`;
}

async function qpClick(e){
  const go = e.target.closest('[data-qgo]');
  if (go && QP.check && QP.tab === 'quests') return qpCheckGo(QP.check.items[+go.dataset.qgo].go);
  const tf = e.target.closest('[data-tflag]');
  if (tf){ const t = qpGet(QP.q, tf.dataset.tflag); t.flags = tf.checked ? (t.flags | 1) : (t.flags & ~1); QP.dirty = true; const b = $('#qp-detail [data-qa="save"]'); if (b) b.disabled = false; return; }
  const a = e.target.dataset ? e.target.dataset.qa : null;
  if (!a || QP.tab !== 'quests') return;
  const q = QP.q, i = +e.target.dataset.i, changed = () => { QP.dirty = true; qpDrawQuest(); };
  if (a === 'save') return qpSave();
  if (a === 'addstage'){
    const last = q.stages.length ? q.stages[q.stages.length - 1].index : 0;
    q.stages.push({index: last + 10, entries: [qpNewEntry()]}); return changed();
  }
  if (a === 'delstage'){ if (confirm('Take away stage ' + q.stages[i].index + '?')){ q.stages.splice(i, 1); changed(); } return; }
  if (a === 'addentry'){ q.stages[i].entries.push(qpNewEntry()); return changed(); }
  if (a === 'delentry'){ const ks = e.target.dataset.p.split('.'), n = +ks.pop(); qpGet(q, ks.join('.')).splice(n, 1); return changed(); }
  if (a === 'addobj'){ const last = q.objectives.length ? q.objectives[q.objectives.length - 1].index : 0; q.objectives.push({index: last + 10, text: '', targets: []}); return changed(); }
  if (a === 'delobj'){ q.objectives.splice(i, 1); return changed(); }
  if (a === 'addtarget'){ q.objectives[i].targets.push({target: '', flags: 0, conditions: []}); return changed(); }
  if (a === 'deltarget'){ q.objectives[i].targets.splice(+e.target.dataset.j, 1); return changed(); }
  if (a === 'check'){
    try { QP.check = await api('/api/quest/check?key=' + encodeURIComponent(QP.key)); qpDrawQuest(); $('#qp-detail').scrollTop = 0; } catch (err){ fail(err); }
    return;
  }
  if (a === 'uncheck'){ QP.check = null; return qpDrawQuest(); }
  if (a === 'board'){ QB.only = QP.key; return qpTab('board'); }
  if (a === 'talk'){ DL.from = {quest: QP.key}; return qpTab('dialogue'); }
  if (a === 'copy'){
    if (!qpLeaveOk()) return;
    try { const r = await post('/api/quest/copy', {key: QP.key}); setState(r.state); await qpList(); qpOpen(r.made[0]); toast('Made a copy: your own quest'); } catch (err){ fail(err); }
    return;
  }
  if (a === 'revert'){
    if (!confirm(QP.view.state === 'new' ? 'Delete this quest of yours?' : 'Put this quest back as the game has it?')) return;
    try {
      const r = await post('/api/quest/revert', {key: QP.key}); setState(r.state); QP.dirty = false; await qpList();
      if (QP.view.state === 'new'){ QP.key = QP.q = QP.view = null; $('#qp-detail').innerHTML = ''; } else qpOpen(QP.key);
    } catch (err){ fail(err); }
  }
}
function qpNewEntry(){ return {flags: {}, xflags: 0, conditions: [], log: '', next: '', script: {source: '', parts: []}}; }
function qpCheckGo(g){
  if (g.line || g.topic){ DL.from = {quest: QP.key, line: g.line, topic: g.topic}; return qpTab('dialogue'); }
  QP.focus = g; qpDrawQuest();
}
async function qpSave(){
  if (QP.editing) return toast('Finish the condition you are changing first (Done, or ✕).', true);
  try {
    const clean = JSON.parse(JSON.stringify(QP.q));
    for (const st of clean.stages || []) for (const e of st.entries || []) if (e.log === '') e.log = null;
    if (clean.name === '') clean.name = null;
    const r = await post('/api/quest/save', {key: QP.key, quest: clean});
    if (r.errors){ QP.errors = r.errors; qpDrawQuest(); $('#qp-detail').scrollTop = 0; return toast('Not saved: a script doesn\'t compile.', true); }
    setState(r.state); QP.dirty = false; QP.errors = []; toast('Saved in your mod');
    await qpList(); qpOpen(QP.key);
  } catch (e){ fail(e); }
}

$('#nav-quests').addEventListener('click', qpDraw);

// (Undo and Redo work on the whole mod: bring this page back in line with what they left)
function qpAfterUndo(){
  if (!$('#qp-side') || $('#page-quests').style.display === 'none') return;
  QP.dirty = false; QP.editing = null;
  setTimeout(async () => {
    if (QP.tab === 'quests'){
      await qpList();
      if (QP.key && (await api('/api/quest/open?key=' + encodeURIComponent(QP.key)).catch(() => null))) { const k = QP.key; QP.key = null; qpOpen(k); }
      else { QP.key = QP.q = QP.view = null; $('#qp-detail').innerHTML = ''; }
    } else if (QP.tab === 'dialogue' && DL.data) dlReload(DL.editKey);
    else if (QP.tab === 'board') qbOpen();
  }, 300);
}
const qpUndoRedo = undoRedo;
undoRedo = async which => { const r = await qpUndoRedo(which); qpAfterUndo(); return r; };
