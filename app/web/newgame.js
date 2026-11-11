// ---------- Your own new game (newgame.py): a card on My mod, and "Start a new game here" in the 3D view's menu ----------
// Every change is sent at once and is one Undo step; FOLab makes the marker, the quest and its script again from it.
const NG = {d: null};

function ngPost(body, said){
  return post('/api/newgame', body).then(d => {
    setState(d.state); NG.d = d.newgame; ngDraw();
    if (A.cellId && !A.outside) resync(); else if (A.outside && typeof outsideResync === 'function') outsideResync();
    if (said) toast(said);
    return d;
  }).catch(e => { fail(e); ngLoad(); });
}

async function ngLoad(){
  try { NG.d = await api('/api/newgame'); } catch (e){ NG.d = null; }
  ngDraw();
}

function ngSetStart(point){
  if (!A.state.project) return toast('Start a mod first.', true);
  if (!A.cellId) return toast('Open a place first.', true);
  const p = point || W.cam.position;
  const facing = Math.round((Math.PI / 2 - W.yaw) * 10000) / 10000;   // (the way the view looks: 0 is north, clockwise)
  ngPost({on: true, cell: A.cellId, p: [p.x, p.y, p.z + 4, facing]}, 'A new game of your mod starts here. My mod has the rest: the screens, the hour, the gear.');
}

function ngDraw(){
  const box = $('#ng-card'); if (!box) return;
  const d = NG.d;
  if (!d || d.none){ box.innerHTML = ''; return; }
  const s = d.settings, on = s.on;
  box.innerHTML = `<h3>Your own new game</h3>
    <p>${on ? `<b>On.</b> New Game in the main menu starts in <b>${esc(d.place || 'your start')}</b>, not at Doc Mitchell's.`
            : 'Off: New Game starts the Mojave as usual, at Doc Mitchell\'s house. Switch it on to start your game somewhere of your own.'}</p>
    <p><label><input type="checkbox" id="ng-on" ${on ? 'checked' : ''}> A new game starts in my mod</label>
       ${s.cell ? '<button class="btn" id="ng-go">Go to the start</button>' : ''}</p>
    <p class="note">Where you wake up: ${s.cell ? esc(d.place || s.cell) : '<i>not picked yet</i>'}. To pick it, right-click a spot in a place and choose
       <b>This place › Start a new game here</b>. You face the way the view looks.</p>
    <div class="${on ? '' : 'ng-off'}">
    <p><b>Screens before you play</b>, in this order (one left out: you start as the player's record has it):<br>
      ${d.steps.map(x => `<label style="margin-right:14px"><input type="checkbox" data-ngstep="${x.id}" ${s.steps.includes(x.id) ? 'checked' : ''}> ${esc(x.label)}</label>`).join('')}</p>
    <p><label>The hour you wake up <input type="number" id="ng-hour" min="0" max="23" value="${s.hour}" style="width:60px"></label>
       <label style="margin-left:18px"><input type="checkbox" id="ng-pipboy" ${s.pipboy ? 'checked' : ''}> Start with the Pip-Boy</label></p>
    <p><b>What you start with</b> (gear, S.P.E.C.I.A.L., skills, looks) is the player's own record. <button class="btn" id="ng-player">Edit the player</button>
       ${d.player_changed ? '<span class="note">Your mod changes it.</span>' : ''}</p>
    <p><b>The Mojave's own start, switched off:</b> Doc Mitchell's opening (and with it the main quest), always.<br>
      ${d.quiet.filter(q => q.found).map(q => `<label><input type="checkbox" data-ngquiet="${q.id}" ${s.quiet.includes(q.id) ? 'checked' : ''}> ${esc(q.label)}</label> <span class="note">${esc(q.note)}.</span>`).join('<br>')}</p>
    </div>
    <p class="note">To try it: <b>Put in game</b>, start New Vegas and choose <b>New</b>. A save that has met Doc Mitchell is left as it is, so Play here still works on your old saves.</p>`;
  const send = (body, said) => ngPost(body, said);
  $('#ng-on').onchange = e => send({on: e.target.checked}, e.target.checked ? 'New Game now starts in your mod.' : 'New Game starts the Mojave again.');
  const go = $('#ng-go'); if (go) go.onclick = async () => {
    const at = {p: [s.p[0], s.p[1], s.p[2] - 80, 0, 0, s.p[3]], facing: true};
    if (!d.world){ page('world'); return openPlace(s.cell, at); }
    const info = await api('/api/world?id=' + encodeURIComponent(d.world));
    OUT.info = info; tab('left', 'outside'); if (!OUT.worlds.length) await outsideTab(); else drawOutside();
    goOutside(info, at);
  };
  box.querySelectorAll('[data-ngstep]').forEach(c => c.onchange = () =>
    send({steps: [...box.querySelectorAll('[data-ngstep]')].filter(x => x.checked).map(x => x.dataset.ngstep)}));
  box.querySelectorAll('[data-ngquiet]').forEach(c => c.onchange = () =>
    send({quiet: [...box.querySelectorAll('[data-ngquiet]')].filter(x => x.checked).map(x => x.dataset.ngquiet)}));
  $('#ng-hour').onchange = e => send({hour: Math.max(0, Math.min(23, +e.target.value || 0))});
  $('#ng-pipboy').onchange = e => send({pipboy: e.target.checked});
  $('#ng-player').onclick = async () => { page('characters'); CH.kind = 'NPC_'; await chInit(); chOpen(d.player); };
}

(() => {
  const st = document.createElement('style');
  st.textContent = '.ng-off{opacity:.55}';
  document.head.appendChild(st);
  const _draw = drawModPage;
  drawModPage = () => {
    _draw();
    if (!A.state.project) return;
    const first = $('#page-mod .card');
    const card = document.createElement('div');
    card.className = 'card'; card.id = 'ng-card';
    if (first) first.after(card); else $('#page-mod').appendChild(card);
    if (NG.d) ngDraw();
    ngLoad();
  };
  const _entries = cmEntries;
  cmEntries = (key, point) => {
    const E = _entries(key, point);
    E.push({group: 'This place', label: 'Start a new game here', run: () => ngSetStart(point)});
    return E;
  };
})();
