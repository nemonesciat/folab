// ---------- Dialogue: a character's or a quest's conversation, to read, follow and write ----------
// The greeting first; pick a choice to follow it to the next topic's lines, the way the game would offer them. Each line
// says who says it and when, in plain words, what it does (the quest stage it sets), and which choices it offers. Lines are
// silent unless you add voice files: the game shows the words for a time that goes by their length.
const DL = {rows: [], mode: 'who', who: null, quest: null, data: null, path: [], edit: null, editKey: null, editView: null, errors: [], from: null, stages: {}};
const DL_EMOTIONS = ['Neutral', 'Anger', 'Disgust', 'Fear', 'Sad', 'Happy', 'Surprise', 'Pained'];

(function dlStyle(){
  const st = document.createElement('style');
  st.textContent = `
.dl-wrap{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(320px,1fr);gap:16px;align-items:start}
@media (max-width:1100px){.dl-wrap{grid-template-columns:1fr}}
.dl-topic{border:1px solid var(--line);border-radius:10px;background:var(--panel);margin:10px 0;overflow:hidden}
.dl-topic>h4{margin:0;padding:6px 12px;background:var(--panel2);border-bottom:1px solid var(--line);font-weight:500;font-size:13px;color:var(--gold2);display:flex;gap:8px;align-items:center}
.dl-topic>h4 small{color:var(--faint);font-weight:400}.dl-topic>h4 .btn{margin-left:auto}
.dl-line{padding:7px 12px 9px;border-bottom:1px solid var(--line);cursor:pointer;border-left:3px solid transparent}.dl-line:last-child{border-bottom:0}
.dl-line:hover{background:var(--hover)}.dl-line.on{background:var(--sel);border-left-color:var(--gold)}.dl-line.mine{border-left-color:var(--green)}.dl-line.on.mine{border-left-color:var(--gold)}
.dl-who{font-size:11.5px;color:var(--muted);margin-bottom:1px}
.dl-words{line-height:1.45}.dl-resp+.dl-resp{margin-top:3px}
.dl-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.dl-chips span{font-size:11px;border:1px solid var(--line2);border-radius:9px;padding:0 7px;color:var(--muted)}
.dl-chips .when{border-color:#4d6a40;color:var(--green)}.dl-chips .or{border-color:var(--amber);color:var(--amber)}.dl-chips .does{border-color:var(--goldline);color:var(--gold2)}.dl-chips .bye{border-color:var(--red);color:var(--red)}
.dl-choices{display:flex;flex-direction:column;align-items:flex-start;gap:2px;margin-top:6px}
.dl-choice{background:none;border:0;padding:0 2px;color:var(--blue);cursor:pointer;font:inherit;font-size:13.5px;text-align:left}
.dl-choice:hover{color:var(--gold2)}.dl-choice.now{color:var(--gold2);font-weight:600}.dl-choice::before{content:"▸ ";color:var(--faint)}
.dl-choice.empty{color:var(--amber)}
.dl-edit{position:sticky;top:0;background:var(--panel);border:1px solid var(--goldline);border-radius:10px;padding:10px 12px;max-height:calc(100vh - 110px);overflow-y:auto}
.dl-edit h4{margin:0 0 6px;font-weight:500;color:var(--gold2);display:flex;gap:6px;align-items:center}
.dl-resp-edit{display:grid;grid-template-columns:1fr auto;gap:4px;margin-bottom:6px}.dl-resp-edit select{font-size:12px;padding:1px 4px}
.dl-others{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}.dl-others button{font-size:12px;padding:1px 8px;background:var(--panel2);border:1px solid var(--line2);border-radius:10px;color:var(--muted);cursor:pointer}
.dl-others button:hover{border-color:var(--gold);color:var(--gold2)}`;
  document.head.appendChild(st);
})();

function dlOpen(){
  $('#qp-left').innerHTML = `<div class="qp-bar"><input id="dl-find" placeholder="Find a character…"></div>
    <div class="list" id="dl-rows"></div>`;
  let timer;
  $('#dl-find').oninput = () => { clearTimeout(timer); timer = setTimeout(dlList, 220); };
  $('#dl-rows').onclick = e => { const r = e.target.closest('.row[data-k]'); if (r) dlPick({who: r.dataset.k}); };
  dlList();
  if (DL.from){ const f = DL.from; DL.from = null; return dlPick(f); }
  if (DL.data) dlDraw();
  else $('#qp-detail').innerHTML = `<div class="qp-empty">Pick a character on the left to read what they say. Yours come first. Pick one with nothing to say to write them a greeting.<br><br>From a quest, <b>Its dialogue</b> shows that quest's lines instead.</div>`;
}
async function dlList(){
  const token = DL.token = (DL.token || 0) + 1;
  const f = $('#dl-find');
  $('#dl-rows').innerHTML = '<div class="note">Reading who says what… (the first time takes a few seconds)</div>';
  const rows = await api('/api/dlg/characters?q=' + encodeURIComponent(f ? f.value : ''));
  if (token !== DL.token || !$('#dl-rows')) return;
  DL.rows = rows;
  const row = r => `<div class="row${r.key === DL.who ? ' on' : ''}" data-k="${esc(r.key)}"><div>${r.state ? `<span class="dot ${r.state === 'new' ? 'new' : 'moved'}"></span>` : ''}${esc(r.name || r.edid)}<small>${esc(r.edid)}</small></div>${r.lines + r.mine ? `<span class="n">${r.lines + r.mine}</span>` : ''}</div>`;
  const mine = rows.filter(r => r.state || r.mine), rest = rows.filter(r => !r.state && !r.mine);
  $('#dl-rows').innerHTML = (mine.length ? '<div class="h">Yours</div>' + mine.map(row).join('') + '<div class="h">The game\'s</div>' : '') + rest.map(row).join('');
}
async function dlPick(o){
  if (!qpLeaveOk()) return;
  DL.who = o.who || null; DL.quest = o.quest || null; DL.path = []; DL.edit = DL.editKey = null; DL.errors = [];
  document.querySelectorAll('#dl-rows .row').forEach(r => r.classList.toggle('on', r.dataset.k === DL.who));
  await dlLoad();
  if (o.topic && dlTopic(o.topic)){ DL.path = [o.topic]; }
  if (o.line) { const l = dlFindLine(o.line); if (l){ if (!DL.path.includes(l.topic)) DL.path = [l.topic]; dlEdit(o.line); } }
  dlDraw();
}
async function dlLoad(){
  const box = $('#qp-detail');
  if (!DL.data) box.innerHTML = '<div class="note" style="padding:24px">Reading what they say…</div>';
  const params = new URLSearchParams(); if (DL.who) params.set('who', DL.who); if (DL.quest) params.set('quest', DL.quest);
  DL.data = await api('/api/dlg/convo?' + params);
  DL.quests = await api('/api/quest/mine');
  if (!DL.path.length){
    if (DL.data.greeting) DL.path = [DL.data.greeting];
    else if (DL.data.topics.length) DL.path = [DL.data.topics[0].key];
  }
}
function dlTopic(k){ return (DL.data.topics || []).find(t => t.key === k); }
function dlFindLine(k){
  for (const t of DL.data.topics) for (const l of t.lines) if (l.key === k) return {line: l, topic: t.key};
  return null;
}

function dlLineHtml(l, step){
  const whoName = DL.data.who ? DL.data.who.name : null;
  const said = l.who.map(w => w.name).join(', ') || 'Anyone';
  const when = l.when.map((w, i) => ({w, or: l.ors[i]})).filter(x => !(whoName && x.w === 'The speaker is ' + whoName));
  const next = DL.path[step + 1];
  return `<div class="dl-line${l.key === DL.editKey ? ' on' : ''}${l.state ? ' mine' : ''}" data-line="${esc(l.key)}">
    <div class="dl-who">${esc(said)} says${l.state === 'changed' ? ' (changed by your mod)' : ''}:</div>
    <div class="dl-words">${l.line.responses.map(r => `<div class="dl-resp">${esc(r.text) || '<i>(no words)</i>'}</div>`).join('') || '<i>(says nothing)</i>'}</div>
    <div class="dl-chips">${when.map(x => `<span class="${x.or ? 'or' : 'when'}" title="Only said when this holds">${esc(x.w)}${x.or ? ' or…' : ''}</span>`).join('')}
      ${l.does.map(d => `<span class="does">${esc(d.text)}</span>`).join('')}
      ${l.line.flags.say_once ? '<span>once only</span>' : ''}${l.line.flags.random ? '<span>picked at random</span>' : ''}
      ${l.goodbye ? '<span class="bye">ends the conversation</span>' : ''}
      ${l.adds.map(a => `<span title="Adds this topic to what you can ask">adds "${esc(a.prompt)}"</span>`).join('')}</div>
    ${l.choices.length ? `<div class="dl-choices">${l.choices.map(c => {
      const t = dlTopic(c.key), empty = t && !t.lines.length;
      return `<button class="dl-choice${c.key === next ? ' now' : ''}${empty ? ' empty' : ''}" data-follow="${esc(c.key)}" data-step="${step}" title="${empty ? 'Nothing here answers this for them yet' : 'Follow this choice'}">${esc(c.prompt)}</button>`;
    }).join('')}</div>` : ''}
  </div>`;
}
function dlDraw(){
  const d = DL.data, box = $('#qp-detail');
  if (!d || QP.tab !== 'dialogue') return;
  const title = d.who ? d.who.name : d.quest ? d.quest.name : '';
  const follow = DL.path.map((k, step) => {
    const t = dlTopic(k); if (!t) return '';
    const isGreeting = k === d.greeting;
    return `<div class="dl-topic"><h4>${isGreeting ? 'They greet you' : esc('You: "' + (t.name || t.edid) + '"')}${t.state === 'new' ? ' <small>your topic</small>' : ''}
      ${!isGreeting && t.state === 'new' ? `<button class="btn sm" data-dla="topic" data-k="${esc(k)}">Change the words</button>` : ''}</h4>
      ${t.lines.map(l => dlLineHtml(l, step)).join('') || '<div class="qp-note" style="padding:8px 12px">Nothing here answers this for them yet.</div>'}
      ${d.who || d.quest ? `<div style="padding:5px 12px"><button class="btn sm" data-dla="another" data-k="${esc(k)}" title="Something else they might say here, under other conditions">＋ Another line here</button></div>` : ''}</div>`;
  }).join('');
  const shown = new Set(DL.path);
  const others = d.topics.filter(t => !shown.has(t.key) && t.lines.length);
  const hasGreeting = !!d.greeting;
  const quests = DL.quests || [];
  const questOptions = quests.map(q => `<option value="${esc(q.key)}">${esc(q.name || q.edid)}</option>`).join('');
  box.innerHTML = `<div class="bwtitle"><b>${esc(title || 'Dialogue')}</b><small>${d.who ? 'Everything written for this character' : 'Everything in this quest'}: read it, follow the choices, click a line to change it. Lines are silent unless you add voice files.</small></div>
    ${d.who && !hasGreeting ? `<div class="qp-check"><h4>Write them a greeting</h4>
      <div class="qp-flags" style="margin:4px 0"><span class="qp-lab">In which quest?</span><select id="dl-sq"><option value="">A new quest for them</option>${questOptions}</select></div>
      <textarea class="qp-text" id="dl-st" rows="2" placeholder="What they say when you talk to them"></textarea>
      <div style="margin-top:6px"><button class="btn primary" data-dla="start">Start the conversation</button></div>
      <div class="qp-note" style="margin-top:4px">A quest has to be running for its lines to be said: a new one starts with the game.</div></div>` : ''}
    <div class="dl-wrap"><div>
      ${follow || '<div class="qp-note" style="padding:12px 0">Nothing written for them.</div>'}
      ${others.length ? `<div class="h" style="padding-left:0">Other topics they talk about</div><div class="dl-others">${others.map(t => `<button data-jump="${esc(t.key)}">${t.key === d.greeting ? 'Their greeting' : esc(t.name || t.edid)}</button>`).join('')}</div>` : ''}
    </div><div id="dl-editor"></div></div>`;
  dlDrawEditor();
}

// ---------- changing a line ----------
function dlEdit(key){
  const hit = dlFindLine(key); if (!hit) return;
  DL.editKey = key; DL.editView = hit.line; DL.edit = JSON.parse(JSON.stringify(hit.line.line)); DL.errors = []; QP.editing = null; QP.dirty = false;
  for (const c of [...hit.line.choices, ...hit.line.adds]) QP.labels[c.key] = c.prompt;
}
function dlDrawEditor(){
  const box = $('#dl-editor'); if (!box) return;
  const l = DL.edit, v = DL.editView;
  if (!l || !v){ box.innerHTML = '<div class="qp-note" style="padding:10px">Click a line to change it.</div>'; return; }
  const scroll = (box.querySelector('.dl-edit') || {}).scrollTop;
  const stages = DL.stages[l.quest] || [];
  const lists = [...(DL.quests || [])];
  if (l.quest && !lists.some(q => q.key === l.quest)) lists.unshift({key: l.quest, name: v.quest_name, edid: v.quest_name});
  const flag = (n, label, tip) => `<label title="${esc(tip || '')}"><input type="checkbox" data-b="flags.${n}"${l.flags[n] ? ' checked' : ''}> ${label}</label>`;
  box.innerHTML = `<div class="dl-edit"><h4>This line <span style="margin-left:auto;display:flex;gap:4px">
      ${v.state === 'new' ? `<button class="btn sm" data-dla="up" title="Earlier: the first line that fits is the one said">↑</button><button class="btn sm" data-dla="down" title="Later">↓</button>` : ''}
      <button class="btn primary sm" data-qa="save" data-dla="save"${QP.dirty ? '' : ' disabled'}>Save</button>
      ${v.state === 'new' ? '<button class="btn sm" data-dla="delete">Delete</button>' : ''}${v.state === 'changed' ? '<button class="btn sm" data-dla="delete">Put back</button>' : ''}
      <button class="btn sm" data-dla="close">✕</button></span></h4>
    ${DL.errors.length ? DL.errors.map(e => `<div class="qp-err">${esc(e.where)}${e.line ? ', line ' + e.line : ''}: ${esc(e.message)} (not saved)</div>`).join('') : ''}
    <div class="qp-sub">What they say <span class="qp-note">each part becomes a subtitle of its own; keep them short</span></div>
    ${l.responses.map((r, i) => `<div class="dl-resp-edit"><textarea class="qp-text" rows="2" data-b="responses.${i}.text">${esc(r.text)}</textarea>
      <div style="display:flex;flex-direction:column;gap:3px"><select data-b="responses.${i}.emotion" data-num title="How they look saying it">${DL_EMOTIONS.map((e, n) => `<option value="${n}"${n === r.emotion ? ' selected' : ''}>${e}</option>`).join('')}</select>
      ${l.responses.length > 1 ? `<button class="btn sm" data-dla="delresp" data-i="${i}">✕</button>` : ''}</div></div>`).join('')}
    <button class="btn sm" data-dla="addresp">＋ More words</button>
    <div class="qp-flags" style="margin-top:8px">${flag('goodbye', 'Ends the conversation', 'The dialogue closes after this line')}${flag('say_once', 'Once only')}${flag('random', 'Picked at random', 'With others marked the same, one is picked')}${flag('run_immediately', 'Runs its script at once', 'The script starts when the line starts, not at its end')}</div>
    <div class="qp-flags" style="margin-top:6px"><span class="qp-lab">Quest</span><select data-b="quest" data-redraw>${lists.map(q => `<option value="${esc(q.key)}"${q.key === l.quest ? ' selected' : ''}>${esc(q.name || q.edid)}</option>`).join('')}</select>
      <span class="qp-lab">Who says it</span>${qpLink('speaker', l.speaker, ['NPC_', 'CREA', 'TACT'], {hint: 'Anyone meeting the conditions'})}</div>
    ${qpConds('conditions', l.conditions, 'Said only when')}
    <div class="qp-sub">The player's choices after it</div>
    ${v.choices.map((c, i) => `<div class="qp-cond"><span class="w">${esc(c.prompt)}</span><button class="btn sm" data-dla="delchoice" data-i="${i}">✕</button></div>`).join('')}
    <div style="display:grid;gap:4px;margin:4px 0"><input id="dl-cp" placeholder="New choice: what the player says"><textarea class="qp-text" id="dl-ct" rows="2" placeholder="What they answer"></textarea>
      <div class="qp-flags"><label><input type="checkbox" id="dl-cb"> That answer ends the conversation</label><button class="btn sm" data-dla="choice">＋ Add this choice</button>
      ${DL.data.topics.length > 1 ? `<select id="dl-cl" style="max-width:200px"><option value="">…or link a topic here</option>${DL.data.topics.filter(t => t.key !== DL.data.greeting && !l.choices.includes(t.key)).map(t => `<option value="${esc(t.key)}">${esc(t.name || t.edid)}</option>`).join('')}</select>` : ''}</div></div>
    <div class="qp-sub">Script after it's said <span class="qp-note">e.g. the stage it sets</span></div>
    <textarea class="qp-code" rows="${Math.max(2, ((l.end && l.end.source) || '').split('\n').length + 1)}" data-b="end.source" spellcheck="false" id="dl-end">${esc((l.end && l.end.source) || '')}</textarea>
    ${stages.length ? `<div class="qp-flags" style="margin-top:3px"><span class="qp-lab">Set a stage:</span><span class="dl-others" style="margin:0">${stages.map(s => `<button data-dla="setstage" data-n="${s.index}" title="${esc(s.log || '')}">${s.index}</button>`).join('')}</span></div>` : ''}
    <div class="qp-sub">Script before it's said</div>
    <textarea class="qp-code" rows="2" data-b="begin.source" spellcheck="false">${esc((l.begin && l.begin.source) || '')}</textarea>
    <div class="qp-sub">Instead of the topic's words, the player's button says</div><input data-b="prompt" value="${esc(l.prompt || '')}" style="width:100%" placeholder="(the topic's own words)"></div>`;
  const e2 = box.querySelector('.dl-edit'); if (scroll) e2.scrollTop = scroll;
  if (l.quest && !DL.stages[l.quest]) dlStagesOf(l.quest);
}
async function dlStagesOf(key){
  try { const d = await api('/api/quest/open?key=' + encodeURIComponent(key)); DL.stages[key] = d.quest.stages.map(s => ({index: s.index, log: (s.entries.find(e => e.log) || {}).log})); DL.stagesEdid = DL.stagesEdid || {}; DL.stagesEdid[key] = d.quest.edid; dlDrawEditor(); } catch (e){}
}
async function dlReload(keep){
  await dlLoad();
  if (keep && dlFindLine(keep)) dlEdit(keep); else { DL.edit = DL.editKey = DL.editView = null; QP.dirty = false; }
  DL.path = DL.path.filter(k => dlTopic(k));
  if (!DL.path.length && DL.data.greeting) DL.path = [DL.data.greeting];
  dlDraw();
  dlList();
}
$('#page-quests').addEventListener('click', async e => {
  if (QP.tab !== 'dialogue') return;
  const follow = e.target.closest('[data-follow]');
  if (follow){
    e.stopPropagation();
    DL.path = DL.path.slice(0, +follow.dataset.step + 1).concat(follow.dataset.follow);
    return dlDraw();
  }
  const jump = e.target.closest('[data-jump]');
  if (jump){ DL.path = (DL.data.greeting ? [DL.data.greeting] : []).concat(jump.dataset.jump); return dlDraw(); }
  const act = e.target.closest('[data-dla]');
  if (act) return dlAct(act);
  const ln = e.target.closest('[data-line]');
  if (ln && ln.closest('#qp-detail')){
    if (ln.dataset.line === DL.editKey) return;
    if (!qpLeaveOk()) return;
    dlEdit(ln.dataset.line); dlDraw();
  }
});
async function dlAct(el){
  const a = el.dataset.dla, l = DL.edit;
  const redraw = () => { QP.dirty = true; dlDrawEditor(); };
  try {
    if (a === 'start'){
      if (!A.state.project) return toast('Start a mod first (My mod).', true);
      const r = await post('/api/dlg/start', {who: DL.who, quest: $('#dl-sq').value || null, text: $('#dl-st').value.trim() || 'Hello there.'});
      setState(r.state); DL.path = []; QP.dirty = false; await dlLoad(); dlEdit(r.made[r.made.length - 1]); dlDraw(); dlList();
      return toast('A greeting, in your mod');
    }
    if (a === 'close'){ if (!qpLeaveOk()) return; DL.edit = DL.editKey = null; return dlDraw(); }
    if (a === 'save'){
      if (QP.editing) return toast('Finish the condition you are changing first (Done, or ✕).', true);
      const clean = JSON.parse(JSON.stringify(l));
      if (clean.prompt === '') clean.prompt = null;
      const r = await post('/api/dlg/line/save', {key: DL.editKey, line: clean});
      if (r.errors){ DL.errors = r.errors; dlDrawEditor(); return toast('Not saved: a script doesn\'t compile.', true); }
      setState(r.state); QP.dirty = false; toast('Saved in your mod');
      return dlReload(DL.editKey);
    }
    if (a === 'addresp'){ l.responses.push({emotion: 0, strength: 50, number: l.responses.length + 1, sound: '', anim: 0, text: ''}); return redraw(); }
    if (a === 'delresp'){ l.responses.splice(+el.dataset.i, 1); return redraw(); }
    if (a === 'setstage'){
      const q = DL.stagesEdid && DL.stagesEdid[l.quest];
      l.end = l.end || {source: '', parts: []};
      l.end.source = (l.end.source.trim() ? l.end.source.trim() + '\n' : '') + `SetStage ${q} ${el.dataset.n}\n`;
      return redraw();
    }
    if (a === 'delchoice'){
      const i = +el.dataset.i; l.choices.splice(i, 1); DL.editView = Object.assign({}, DL.editView, {choices: DL.editView.choices.filter((_, n) => n !== i)});
      return redraw();
    }
    if (a === 'choice'){
      if (QP.dirty && !confirm('This saves your other changes to this line too. Go on?')) return;
      if (QP.dirty){ const s = await post('/api/dlg/line/save', {key: DL.editKey, line: JSON.parse(JSON.stringify(l))}); if (s.errors){ DL.errors = s.errors; return dlDrawEditor(); } QP.dirty = false; }
      const linked = $('#dl-cl') ? $('#dl-cl').value : '';
      const r = await post('/api/dlg/choice', linked ? {line: DL.editKey, topic: linked} : {line: DL.editKey, prompt: $('#dl-cp').value, text: $('#dl-ct').value, goodbye: $('#dl-cb').checked});
      setState(r.state);
      const step = DL.path.indexOf((dlFindLine(DL.editKey) || {}).topic);
      if (step >= 0) DL.path = DL.path.slice(0, step + 1).concat(r.topic);
      return dlReload(DL.editKey);
    }
    if (a === 'delete'){
      if (!confirm(DL.editView.state === 'new' ? 'Delete this line?' : 'Put this line back as the game has it?')) return;
      const r = await post('/api/dlg/line/delete', {key: DL.editKey});
      setState(r.state); QP.dirty = false;
      return dlReload(DL.editView.state === 'changed' ? DL.editKey : null);
    }
    if (a === 'up' || a === 'down'){
      if (!qpLeaveOk()) return;
      const r = await post('/api/dlg/line/move', {key: DL.editKey, way: a === 'up' ? -1 : 1});
      setState(r.state); return dlReload(DL.editKey);
    }
    if (a === 'another'){
      const t = dlTopic(el.dataset.k), first = t.lines[0];
      const quest = (first && first.line.quest) || (DL.quest) || (DL.quests[0] || {}).key;
      if (!quest) return toast('Make a quest for it first (Quests tab).', true);
      if (!qpLeaveOk()) return;
      const r = await post('/api/dlg/line/new', {topic: el.dataset.k, quest, who: DL.who || (first && first.who[0] && first.who[0].key) || null, text: '...'});
      setState(r.state);
      return dlReload(r.made[0]);
    }
    if (a === 'topic'){
      const t = dlTopic(el.dataset.k), v = prompt('What the player says:', t.name || ''); if (v == null) return;
      const r = await post('/api/dlg/topic/save', {key: el.dataset.k, name: v});
      setState(r.state); return dlReload(DL.editKey);
    }
  } catch (err){ fail(err); }
}
