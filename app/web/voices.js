// ---------- Voices: speak a line in its character's voice, with the lip file that moves their face ----------
// Adds a Voice part to the dialogue editor's line (dialogue.js) and "Voice every line" for a character. The voice maker is
// Kokoro (api_voices.py, voicegen.py); its model is the user's own download, which FOLab finds in Downloads.
const VO = {status: null, line: null, lineKey: null, busy: false, audio: null};

(function voStyle(){
  const st = document.createElement('style');
  st.textContent = `
.vo-box{border:1px solid var(--line2);border-radius:8px;padding:6px 8px;margin:8px 0;background:var(--panel2)}
.vo-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:3px 0}
.vo-row select{max-width:220px}.vo-row input[type=range]{width:90px}
.vo-resp{display:flex;gap:6px;align-items:center;font-size:12px;color:var(--muted);margin:2px 0}
.vo-resp .st{border:1px solid var(--line2);border-radius:9px;padding:0 7px}
.vo-resp .st.done{border-color:#4d6a40;color:var(--green)}.vo-resp .st.old{border-color:var(--amber);color:var(--amber)}
.vo-play{background:none;border:0;color:var(--blue);cursor:pointer;font:inherit;padding:0 2px}.vo-play:hover{color:var(--gold2)}`;
  document.head.appendChild(st);
})();

async function voStatus(){
  if (!VO.status) VO.status = await api('/api/voice/status');
  return VO.status;
}
function voPlay(url){
  if (VO.audio) VO.audio.pause();
  VO.audio = new Audio(url);
  VO.audio.play().catch(e => toast('Could not play it: ' + e.message, true));
}
function voVoiceOptions(sel, none){
  return (none ? `<option value=""${sel ? '' : ' selected'}>nobody</option>` : '') +
    VO.status.voices.map(([k, n]) => `<option value="${esc(k)}"${k === sel ? ' selected' : ''}>${esc(n)}</option>`).join('');
}
// a voice is one of Kokoro's or a blend 'a*0.7+b*0.3' (voicegen.blend): shown as a voice, another mixed in, and how much
function voParts(v){
  const parts = String(v || '').split('+').map(p => { const [n, w] = p.split('*'); return [n.trim(), w == null ? 1 : +w]; })
    .filter(p => p[0]).sort((a, b) => b[1] - a[1]);
  const total = parts.reduce((s, p) => s + p[1], 0) || 1;
  return {main: (parts[0] || [''])[0], mix: (parts[1] || [''])[0], amount: parts[1] ? Math.round(parts[1][1] / total * 100) : 30};
}
function voChoiceHtml(c, forName){
  const p = voParts(c.voice), lively = c.lively == null ? 1.3 : +c.lively;
  return `<div class="vo-row"><span class="qp-lab">Voice</span><select id="vo-voice">${voVoiceOptions(p.main)}</select>
      <span class="qp-lab" title="Two voices mixed sound like neither: a voice of their own">Mix with</span><select id="vo-mix">${voVoiceOptions(p.mix, true)}</select>
      <input type="range" id="vo-amount" min="10" max="50" step="5" value="${p.amount}" title="How much of the second voice"><small id="vo-amount-n">${p.amount}%</small></div>
    <div class="vo-row"><span class="qp-lab">Speed</span><input type="range" id="vo-speed" min="0.7" max="1.4" step="0.05" value="${c.speed}"><small id="vo-speed-n">${(+c.speed).toFixed(2)}</small>
      <span class="qp-lab">Pitch</span><input type="range" id="vo-pitch" min="-4" max="4" step="0.5" value="${c.pitch}"><small id="vo-pitch-n">${(+c.pitch).toFixed(1)}</small>
      <span class="qp-lab" title="How much the voice rises and falls: under 1 flat and tired, over 1 lively">Lively</span><input type="range" id="vo-lively" min="0.6" max="2" step="0.1" value="${lively}"><small id="vo-lively-n">${lively.toFixed(1)}</small></div>
    <div class="vo-row"><button class="btn sm" data-voa="sample">▶ Hear this voice</button>
      <button class="btn sm" data-voa="keep" title="Every line of ${esc(forName)} is spoken in it">Use it for ${esc(forName)}</button>
      ${c.own ? '<small class="qp-note">' + esc(forName) + '\'s own voice</small>' : '<small class="qp-note">not chosen yet: a mix made for them</small>'}</div>`;
}
function voPicked(){
  const main = $('#vo-voice').value, mix = $('#vo-mix').value, amt = +$('#vo-amount').value / 100;
  const voice = mix && mix !== main ? `${main}*${(1 - amt).toFixed(2)}+${mix}*${amt.toFixed(2)}` : main;
  return {voice, speed: +$('#vo-speed').value, pitch: +$('#vo-pitch').value, lively: +$('#vo-lively').value,
          engine: VO.line && VO.line.engine};
}

// No voice pack (voicepack.py): it's a download of its own. Install when it's in Downloads, else where to get it.
function voPackBox(box, p){
  box.innerHTML = `<div class="qp-sub">Voice</div><div class="qp-note">${esc(p.why)}</div>
    <div style="display:flex;gap:6px;margin-top:4px">
      ${p.zip ? '<button class="btn" id="vo-pack">Install the voice pack</button>' : ''}
      <button class="btn" id="vo-pack-look">${p.zip ? 'Look again' : 'I’ve downloaded it: look again'}</button>
      <a class="btn" href="${esc(p.page)}" target="_blank" rel="noopener">FOLab’s downloads</a></div>`;
  const again = () => { VO.status = null; voDrawLine(); };
  box.querySelector('#vo-pack-look').onclick = again;
  const b = box.querySelector('#vo-pack');
  if (b) b.onclick = async () => {
    b.disabled = true; b.textContent = 'Installing…';
    try {
      const r = await post('/api/voice/pack/install', {});
      toast(r.ready ? 'Voice pack in: you can voice lines now.' : r.why, !r.ready);
    } catch (e){ fail(e); }
    again();
  };
}

async function voDrawLine(){
  const box = $('#vo-box'); if (!box) return;
  const key = DL.editKey;
  const st = await voStatus();
  if (!st.engine && st.pack){ voPackBox(box, st.pack); return; }
  if (!st.engine){ box.innerHTML = `<div class="qp-sub">Voice</div><div class="qp-note">${esc(st.why)}</div>`; return; }
  if (!st.model){ box.innerHTML = `<div class="qp-sub">Voice</div><div class="qp-note">${esc(st.why)}</div>`; return; }
  let info;
  try { info = await api('/api/voice/line?key=' + encodeURIComponent(key)); } catch (e){ box.innerHTML = '<div class="qp-note">' + esc(e.message) + '</div>'; return; }
  if (key !== DL.editKey || !$('#vo-box')) return;
  VO.line = info; VO.lineKey = key;
  const name = (DL.editView.who[0] || {}).name || 'them';
  const label = {done: 'voiced', old: 'changed since: voice it again', none: 'not voiced'};
  box.innerHTML = `<div class="qp-sub">Voice <span class="qp-note">spoken by ${esc(name)}${info.voice_type_edid ? ', voice type ' + esc(info.voice_type_edid) : ''}</span></div>
    ${info.problem ? `<div class="qp-note">${esc(info.problem)}</div>` : `
    ${st.chatterbox ? `<div class="vo-row"><span class="qp-lab">Voice maker</span><select id="vo-engine">
        <option value="chatterbox"${info.engine === 'chatterbox' ? ' selected' : ''}>Chatterbox: acts it out, more human</option>
        <option value="kokoro"${info.engine === 'kokoro' ? ' selected' : ''}>Kokoro: quicker, plainer</option></select>
        <small class="qp-note">for every line of this mod</small></div>` : ''}
    ${voChoiceHtml(info.choice, name)}
    ${info.engine === 'chatterbox' ? '<div class="qp-note" style="margin:2px 0 4px">Chatterbox copies this voice and acts each line in it, at its own pace; the emotion beside the words sets how much feeling goes in.</div>' : ''}
    <div class="qp-note" style="margin:2px 0 4px${info.engine === 'chatterbox' ? ';display:none' : ''}">The voice follows each part's emotion (the menu beside its words, which also sets the face): sad is slower, lower and flatter; afraid is quicker and higher; angry and happy rise and fall more.</div>
    ${info.responses.map((r, i) => { const e = (DL.edit.responses[i] || r); const emo = +e.emotion || 0; const str = e.strength == null ? 50 : +e.strength;
      return `<div class="vo-resp"><span class="st ${r.state}">${label[r.state]}</span>
      ${r.state !== 'none' ? `<button class="vo-play" data-voa="play" data-n="${r.number}">▶ Play</button>` : ''}
      <span title="Set by the emotion menu beside the words">${esc(DL_EMOTIONS[emo] || 'Neutral')}</span>
      ${emo ? `<select data-vostr="${i}" title="How strongly it shows, in the face and the voice">${[[25, 'a little'], [50, 'clearly'], [75, 'strongly'], [100, 'very strongly']].map(([v, n]) => `<option value="${v}"${Math.abs(v - str) < 13 ? ' selected' : ''}>${n}</option>`).join('')}</select>` : ''}
      <span>${esc(r.text.slice(0, 50))}${r.text.length > 50 ? '…' : ''}</span></div>`; }).join('')}
    <div class="vo-row"><button class="btn primary sm" data-voa="line"${QP.dirty ? ' disabled title="Save the line first"' : ''}>${info.responses.some(r => r.state !== 'none') ? 'Voice this line again' : 'Voice this line'}</button>
      ${DL.who ? `<button class="btn sm" data-voa="all">Voice every line for ${esc(name)}</button>` : ''}
      ${QP.dirty ? '<small class="qp-note">Save the line first</small>' : ''}</div>`}`;
  box.className = 'vo-box';
  const show = (id, n, d) => { const el = $('#' + id); if (el) el.oninput = () => { $('#' + n).textContent = (+el.value).toFixed(d); }; };
  show('vo-speed', 'vo-speed-n', 2); show('vo-pitch', 'vo-pitch-n', 1); show('vo-lively', 'vo-lively-n', 1);
  const am = $('#vo-amount'); if (am) am.oninput = () => { $('#vo-amount-n').textContent = am.value + '%'; };
}

// the line editor gets a Voice part under the words; the character's title a button for all their lines
const voDrawEditorWas = dlDrawEditor;
dlDrawEditor = function(){
  voDrawEditorWas();
  const ed = document.querySelector('#dl-editor .dl-edit');
  if (!ed || !DL.edit) return;
  const more = ed.querySelector('[data-dla="addresp"]');
  const div = document.createElement('div'); div.id = 'vo-box';
  if (more) more.after(div); else ed.appendChild(div);
  voDrawLine();
};

async function voAct(el){
  const a = el.dataset.voa;
  if (VO.busy) return toast('Still speaking the last one…', true);
  try {
    if (a === 'play') return voPlay('/api/voice/file?key=' + encodeURIComponent(VO.lineKey) + '&n=' + el.dataset.n + '&t=' + Date.now());
    if (a === 'sample'){
      VO.busy = true; el.disabled = true;
      const r = await fetch('/api/voice/sample', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(voPicked())});
      if (!r.ok){ const d = await r.json().catch(() => ({})); throw new Error(d.error || r.status); }
      return voPlay(URL.createObjectURL(await r.blob()));
    }
    if (a === 'keep'){
      if (!VO.line || !VO.line.who) return;
      await post('/api/voice/choice', Object.assign({key: VO.line.who}, voPicked()));
      toast('That voice is theirs now'); return voDrawLine();
    }
    if (a === 'line'){
      VO.busy = true; el.disabled = true; el.textContent = 'Speaking…';
      if (VO.line && VO.line.who) await post('/api/voice/choice', Object.assign({key: VO.line.who}, voPicked()));
      const info = await post('/api/voice/line', {key: VO.lineKey});
      toast('Voiced, with the lip file: in your mod\'s files');
      await voDrawLine();
      const first = info.responses.find(r => r.state === 'done');
      if (first) voPlay('/api/voice/file?key=' + encodeURIComponent(VO.lineKey) + '&n=' + first.number + '&t=' + Date.now());
      return;
    }
    if (a === 'all'){
      if (!confirm('Speak every one of their lines in this voice? Lines voiced before are spoken again.')) return;
      VO.busy = true; el.disabled = true; el.textContent = 'Speaking every line…';
      if (VO.line && VO.line.who) await post('/api/voice/choice', Object.assign({key: VO.line.who}, voPicked()));
      const r = await post('/api/voice/character', {who: DL.who});
      toast(`${r.voiced} of ${r.lines} lines voiced` + (r.problems.length ? ': ' + r.problems.join(' ') : ''), !!r.problems.length);
      return voDrawLine();
    }
  } catch (err){ fail(err); }
  finally { VO.busy = false; }
}
$('#page-quests').addEventListener('click', e => {
  const b = e.target.closest('[data-voa]');
  if (b && QP.tab === 'dialogue'){ e.stopPropagation(); voAct(b); }
}, true);
// how strongly a part's emotion shows: the response's strength (TRDT), saved with the line like its other changes
$('#page-quests').addEventListener('change', e => {
  if (e.target.matches && e.target.matches('[data-b$=".emotion"]')) return setTimeout(voDrawLine, 0);   // (after quests.js keeps it)
  if (e.target.id === 'vo-engine'){
    e.stopPropagation();
    return post('/api/voice/engine', {engine: e.target.value}).then(voDrawLine).catch(fail);
  }
  const s = e.target.closest('[data-vostr]');
  if (!s || QP.tab !== 'dialogue' || !DL.edit) return;
  e.stopPropagation();
  const r = DL.edit.responses[+s.dataset.vostr]; if (!r) return;
  r.strength = +s.value; QP.dirty = true; dlDrawEditor();
}, true);
