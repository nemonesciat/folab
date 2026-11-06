// ---------- The quest board: a mod's quests, each with its stages as a flow ----------
// (api_quests.board reads; this draws.) A quest is a rail of stages, left to right. A move is what sets a stage (a line said,
// another stage's script, a quest's script): the next-stage move is written in the gap, one that skips stages arcs over
// them, one that can happen at any time sits in the band below. Stages nothing sets and stages nothing leads out of are flagged.
const QB = {only: null, boards: []};

(function qbStyle(){
  const st = document.createElement('style');
  st.textContent = `
.qb-quest{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:12px 0;padding:8px 14px 12px}
.qb-quest>h3{margin:2px 0 2px;font-size:14.5px;color:var(--gold2);font-weight:500;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.qb-quest>h3 small{color:var(--faint);font-size:12px;font-weight:400}.qb-quest>h3 .btn{margin-left:auto}
.qb-scroll{overflow-x:auto;padding-bottom:6px}
.qb-rail{position:relative}
.qb-rail svg{position:absolute;left:0;top:0;pointer-events:none;overflow:visible}
.qb-rail svg path{fill:none;stroke:var(--goldline);stroke-width:1.6}.qb-rail svg path.back{stroke:var(--amber);stroke-dasharray:5 4}
.qb-rail svg line{stroke:var(--goldline);stroke-width:2}.qb-rail svg line.gone{stroke:var(--red);stroke-dasharray:4 5}
.qb-node{position:absolute;width:168px;text-align:center;cursor:pointer}
.qb-node .dot{width:38px;height:38px;border-radius:50%;border:2px solid var(--gold);background:var(--bg2);margin:0 auto;line-height:34px;font-weight:600;font-size:13px;color:var(--gold2)}
.qb-node.fin .dot{background:var(--gold);color:var(--bg)}.qb-node.fail .dot{background:var(--red);border-color:var(--red);color:var(--bg)}
.qb-node.bad .dot{border-color:var(--red);color:var(--red)}.qb-node.dead .dot{border-color:var(--amber)}
.qb-node.start .dot{width:auto;display:inline-block;padding:0 12px;border-radius:19px;border-style:dashed;color:var(--muted);font-weight:500;line-height:34px}
.qb-node .txt{font-size:11.5px;color:var(--muted);margin-top:4px;line-height:1.3;max-height:45px;overflow:hidden;padding:0 4px}
.qb-node .flag{font-size:10.5px;color:var(--amber);margin-top:2px}.qb-node.bad .flag{color:var(--red)}
.qb-node:hover .dot{box-shadow:0 0 0 3px color-mix(in srgb,var(--gold) 35%,transparent)}
.qb-move{position:absolute;font-size:11.5px;line-height:17px;height:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;color:var(--text);padding:0 4px;border-radius:4px;text-align:center}
.qb-move:hover{background:var(--hover);overflow:visible;z-index:3;width:auto!important}
.qb-move .v{color:var(--gold2);font-weight:600}.qb-move.script .v,.qb-move.stage .v{color:var(--blue)}.qb-move.arc{background:var(--panel)}
.qb-band{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;border-top:1px dashed var(--line2);margin-top:8px;padding-top:6px;font-size:12px}
.qb-band .k{color:var(--faint);font-size:11px;letter-spacing:.06em;text-transform:uppercase}
.qb-band .qb-m{border:1px solid var(--line2);border-radius:9px;padding:0 7px;cursor:pointer;max-width:430px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qb-band .qb-m:hover{border-color:var(--gold)}.qb-band .qb-m.never{border-color:var(--red);color:var(--red)}`;
  document.head.appendChild(st);
})();

async function qbOpen(){
  const mine = await api('/api/quest/mine').catch(() => []);
  $('#qp-left').innerHTML = `<div class="h">Your quests</div><div class="list" id="qb-rows">
    <div class="row${QB.only ? '' : ' on'}" data-k=""><div>All of them<small>${mine.length} quest${mine.length === 1 ? '' : 's'}</small></div></div>
    ${mine.map(q => `<div class="row${QB.only === q.key ? ' on' : ''}" data-k="${esc(q.key)}"><div>${esc(q.name || q.edid)}<small>${esc(q.edid)}</small></div></div>`).join('')}</div>`;
  $('#qb-rows').onclick = e => { const r = e.target.closest('.row'); if (r){ QB.only = r.dataset.k || null; qbOpen(); } };
  const keys = QB.only ? [QB.only] : mine.map(q => q.key);
  const box = $('#qp-detail');
  if (!keys.length){
    box.innerHTML = `<div class="qp-empty">Your mod has no quests yet. Make one in the <b>Quests</b> tab, and its stages show here as a flow, with the lines and scripts that move it on.</div>`;
    return;
  }
  box.innerHTML = '<div class="note" style="padding:20px">Reading what moves each quest…</div>';
  try { QB.boards = await Promise.all(keys.map(k => api('/api/quest/board?key=' + encodeURIComponent(k)))); }
  catch (e){ box.innerHTML = ''; return fail(e); }
  if (QP.tab !== 'board') return;
  box.innerHTML = `<div class="bwtitle"><b>Board</b><small>Each quest's stages from left to right, and what moves it on. Click a stage or a move to go to it.</small></div>` + QB.boards.map(qbQuest).join('');
}

function qbMoveLabel(m){
  if (m.kind === 'line'){
    const who = m.who.length ? m.who.join(', ') : 'Someone';
    return `<span class="v">${esc(who)}</span>${m.topic ? ' on "' + esc(m.topic) + '"' : ''}`;
  }
  return `<span class="v">${esc(m.kind === 'stage' ? 'Stage script' : 'Script')}</span> ${esc(m.text)}`;
}
function qbMoveTitle(m){ return (m.text || '') + ' → stage ' + m.to; }

function qbQuest(b){
  const W = 210, H = 70, top = 54;
  const idx = b.stages.map(s => s.index);
  const col = {start: 0}; idx.forEach((n, i) => { col[n] = i + 1; });
  const x = c => 20 + c * W;
  // (what needs no stage and sets the first one simply starts the quest off)
  const moves = b.moves.map((m, i) => Object.assign({i}, m, m.from === 'any' && m.to === idx[0] ? {from: 'start'} : {}));
  const edges = moves.filter(m => m.from !== 'any' && m.from != null && col[m.from] !== undefined && col[m.to] !== undefined && m.from !== m.to);
  const nextEdges = edges.filter(m => col[m.to] === col[m.from] + 1), arcs = edges.filter(m => col[m.to] !== col[m.from] + 1);
  const band = moves.filter(m => !edges.includes(m));
  const width = x(idx.length) + 180;
  const gaps = {};
  for (const m of nextEdges) (gaps[col[m.from]] = gaps[col[m.from]] || []).push(m);
  const raise = 22;
  const arcH = arcs.length ? Math.min(160, 30 + arcs.length * raise) : 0;
  const nodeY = top + arcH + Math.max(0, ...Object.values(gaps).map(g => g.length - 1)) * 18;
  let svg = '';
  // the rail itself
  for (let c = 0; c < idx.length; c++) svg += `<line x1="${x(c) + 84}" y1="${nodeY + 19}" x2="${x(c + 1) + 84}" y2="${nodeY + 19}" class="${gaps[c] ? '' : 'gone'}"></line>`;
  arcs.forEach((m, n) => {
    const x1 = x(col[m.from]) + 84, x2 = x(col[m.to]) + 84, y = nodeY - 4, up = 26 + (n % 6) * raise;
    svg += `<path class="${col[m.to] < col[m.from] ? 'back' : ''}" d="M${x1} ${y} C ${x1} ${y - up}, ${x2} ${y - up}, ${x2} ${y}" marker-end="url(#qb-arrow)"></path>`;
  });
  let html = `<div class="qb-node start" style="left:${x(0)}px;top:${nodeY}px"><div class="dot">${b.start_enabled ? 'Game start' : 'Started'}</div>${!b.start_enabled && !b.started_by.length ? '<div class="flag" style="color:var(--red)">nothing starts it</div>' : ''}</div>`;
  for (const s of b.stages){
    const cls = [s.complete ? 'fin' : '', s.fail ? 'fail' : '', s.unset && s.index !== idx[0] ? 'bad' : s.unset ? 'dead' : '', s.dead && !s.unset ? 'dead' : ''].join(' ');
    const flag = s.unset ? 'nothing sets it' : s.dead ? 'nothing leads on' : s.complete ? 'completes the quest' : s.fail ? 'fails the quest' : '';
    html += `<div class="qb-node ${cls}" data-qbstage="${s.index}" data-qk="${esc(b.key)}" style="left:${x(col[s.index])}px;top:${nodeY}px" title="${esc(s.log || '')}"><div class="dot">${s.index}</div><div class="txt">${esc(s.log || '')}</div>${flag ? `<div class="flag">${flag}</div>` : ''}</div>`;
  }
  for (const c in gaps) gaps[c].forEach((m, n) => {
    html += `<div class="qb-move ${m.kind}" data-qbm="${m.i}" data-qk="${esc(b.key)}" title="${esc(qbMoveTitle(m))}" style="left:${x(+c) + 104}px;width:${W - 40}px;top:${nodeY - 2 - (n + 1) * 18}px">${qbMoveLabel(m)}</div>`;
  });
  arcs.forEach((m, n) => {
    const x1 = x(col[m.from]) + 84, x2 = x(col[m.to]) + 84, up = 26 + (n % 6) * raise, mid = (x1 + x2) / 2;
    html += `<div class="qb-move arc ${m.kind}" data-qbm="${m.i}" data-qk="${esc(b.key)}" title="${esc(qbMoveTitle(m))}" style="left:${mid - 85}px;width:170px;top:${nodeY - 4 - up * 0.75 - 10}px">${qbMoveLabel(m)}</div>`;
  });
  const bandHtml = (list, label, cls) => list.length ? `<div class="qb-band"><span class="k">${label}</span>${list.map(m => `<span class="qb-m ${cls || ''}" data-qbm="${m.i}" data-qk="${esc(b.key)}" title="${esc(qbMoveTitle(m))}">${qbMoveLabel(m)} → ${m.to}</span>`).join('')}</div>` : '';
  const anyTime = band.filter(m => m.from === 'any' || m.from === m.to), never = band.filter(m => m.from == null || (m.from !== 'any' && m.from !== m.to));
  return `<div class="qb-quest" data-board="${esc(b.key)}"><h3>${esc(b.name || b.edid)} <small>${esc(b.edid)}${b.state ? '' : ' · the game\'s'}</small>
      <button class="btn sm" data-qbopen="${esc(b.key)}">Open it</button></h3>
    ${b.stages.length ? `<div class="qb-scroll"><div class="qb-rail" style="width:${width}px;height:${nodeY + H + 40}px">
      <svg width="${width}" height="${nodeY + H + 40}"><defs><marker id="qb-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L8 4L0 8Z" fill="var(--goldline)" stroke="none"></path></marker></defs>${svg}</svg>${html}</div></div>`
      : '<div class="qp-note" style="padding:6px 0">No stages yet.</div>'}
    ${bandHtml(anyTime, 'Any time')}${bandHtml(never, 'Can\'t happen as written', 'never')}
    ${b.missing.length ? `<div class="qb-band"><span class="k">Sets a stage it hasn't got</span><span class="qb-m never">${b.missing.join(', ')}</span></div>` : ''}
    ${b.next_quests.length ? `<div class="qb-band"><span class="k">Leads to</span>${b.next_quests.map(n => `<span class="qb-m" data-qbopen="${esc(n.key)}">${esc(n.name)} (from stage ${n.stage})</span>`).join('')}</div>` : ''}</div>`;
}
$('#page-quests').addEventListener('click', e => {
  if (QP.tab !== 'board') return;
  const open = e.target.closest('[data-qbopen]');
  if (open){ QP.tab = 'quests'; qpDraw(); return qpOpen(open.dataset.qbopen); }
  const st = e.target.closest('[data-qbstage]');
  if (st){ QP.tab = 'quests'; qpDraw(); return qpOpen(st.dataset.qk, {stage: +st.dataset.qbstage}); }
  const mv = e.target.closest('[data-qbm]');
  if (mv){
    const b = QB.boards.find(x => x.key === mv.dataset.qk), m = b.moves[+mv.dataset.qbm];
    if (m.kind === 'line'){ DL.from = {quest: b.key, line: m.key}; QP.tab = 'dialogue'; return qpDraw(); }
    if (m.kind === 'stage'){ QP.tab = 'quests'; qpDraw(); return qpOpen(m.key); }
    toast(m.text);
  }
});
