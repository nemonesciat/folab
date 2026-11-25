"""The milestone perks' hooks into uses already in the mod (milestones.py; docs/waikiki-speech-science.md K5).

- **Copies first in their topics, for those with the perk** (perks.py's way, voices copied from the originals):
  - Kahuna's Voice: every Speech check the court's people ask (FOLabKahunaCourtFaction) 15 easier;
  - Silver Tongue: every Speech 95 check asked at 85 (none in the mod yet: later ones get theirs when this is run again);
  - Cage Breaker: the catchers' and collectors' cages open without the Lockpick check.
- **New lines** (voiced):
  - Tongbao Baron: the money changer at ten kala a tongbao both ways;
  - Cell Merchant: the pirate traders take cells at five kala (money's trading mode 'cells5');
  - Talk Story: one more rumour from Waikiki's locals.
- **Scripts made again from their own source, with the perk asked:**
  - Tinkerer: the generators need one Scrap Electronics, not two;
  - Vault Charge: drained cells charged one and a half for one without Science 75;
  - Salvage King: the robots always leave a Sensor Module;
  - Ghost of Waikiki: the catchers never hail you;
  - money's settling script, with the 'cells5' mode.
- **A quest of its own** (FOLabMilestoneHooks): Word on the Water (each side's score moves half again: the quest adds half of
  every change it sees), Signal Man (huangradio's decoded numbers note, the moment you have the perk: by ear, without the Radar Dome).
The rest of the hooks come with the K2 uses they boost.

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo (VOICE, VOICE_ONLY: the new lines)
"""
import json
import re

import recordio

LABEL = "The milestone perks' hooks"
QUEST, SCRIPT = 'FOLabMilestoneHooks', 'FOLabMilestoneHooksScript'
VOICE = ['FOLabMoney', 'FOLabPirateDeals', 'FOLabRumours']
VOICE_ONLY = set()
COURT = 'FOLabKahunaCourtFaction'
EASIER = 15
SILVER = (95, 85)
CAGE_QUESTS = ('FOLabCatchers', 'FOLabTributeDay')
GETAV, HASPERK, GETISID, GETQUESTVAR, GETITEMCOUNT = 14, 449, 72, 79, 47
SPEECH, LOCKPICK = 43, 36
P_ = lambda tail: 'FOLabPerk' + tail
SIDES = ('pirates', 'court', 'huang')
WORDS = {
    'sell10': "Ten tongbao. One hundred kala. For you, the fair rate.",
    'sellall': "All. Ten kala each. You know the price of things.",
    'buy10': "Ten tongbao, one hundred kala. A baron's rate.",
    'cells5': "Your cells? Five kala a cell. You've earned that rate.",
    'rumour': "The freighter's hold? The Huang keep one man on it. He eats at noon and at six, regular as the tide. Everyone knows that.",
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _source(rec):
    s = next((s for s in rec['subs'] if s['tag'] == 'SCTX'), None)
    return bytes.fromhex(s['value']).decode('cp1252').replace('\r\n', '\n') if s else ''      # (saved with Windows line ends)


def _members(pr, faction):
    """NPC_ of the mod's own in a faction (their own SNAM)."""
    out = set()
    for k, r in pr.records.items():
        if r.get('type') == 'NPC_' and r.get('subs'):
            for s in r['subs']:
                if s['tag'] == 'SNAM' and json.dumps(s).find(faction) >= 0:
                    out.add(k)
    return out


def plan(gd, pr):
    import questrec as qr
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % QUEST))
        return rep
    if not _mod_key(pr, P_('MarketDay'), 'PERK'):
        rep['skipped'].append(('all', 'the milestone perks are not in the mod'))
        return rep
    fac = _mod_key(pr, COURT, 'FACT')
    court = set()
    if fac:
        for k, r in pr.records.items():
            if r.get('type') == 'NPC_' and r.get('subs') and any(s['tag'] == 'SNAM' and fac in json.dumps(s) for s in r['subs']):
                court.add(k)
    quests = {k: recordio.field(r, 'EDID') for k, r in pr.records.items() if r.get('type') == 'QUST' and r.get('subs')}
    copies = []
    for k, rec in sorted(pr.records.items()):
        if rec.get('type') != 'INFO':
            continue
        l = qr.info_plain(rec)
        who = {c['p1'] for c in l['conditions'] if int(c['fn']) == GETISID and c['op'] == '='}
        speech = [c for c in l['conditions'] if int(c['fn']) == GETAV and c['p1'] == SPEECH and c['op'] in ('>=', '<')]
        lock = [c for c in l['conditions'] if int(c['fn']) == GETAV and c['p1'] == LOCKPICK and c['op'] == '>=']
        if speech and who & court:
            copies.append({'line': k, 'set': 'voice', 'perk': P_('KahunasVoice')})
        if speech and any(float(c['value']) >= SILVER[0] for c in speech):
            copies.append({'line': k, 'set': 'silver', 'perk': P_('SilverTongue')})
        if lock and quests.get(l['quest']) in CAGE_QUESTS:
            copies.append({'line': k, 'set': 'cage', 'perk': P_('CageBreaker')})
    for c in copies:
        rep['rows'].append(dict(c, what='copy'))
    for e in ('FOLabGenerators', 'FOLabSalvagerScript', 'FOLabMoneyScript', 'FOLabRumours', 'FOLabNameOnWaterScript', 'FOLabHoldWatch'):
        if not _mod_key(pr, e):
            rep['skipped'].append((e, 'not in the mod: its hook waits'))
    gens = sorted(recordio.field(r, 'EDID') for r in pr.records.values() if r.get('type') == 'SCPT' and r.get('subs')
                  and re.match(r'FOLabGenerator\w+Script$', recordio.field(r, 'EDID') or '') and recordio.field(r, 'EDID') != 'FOLabGeneratorsScript')
    catchers = sorted(recordio.field(r, 'EDID') for r in pr.records.values() if r.get('type') == 'SCPT' and r.get('subs')
                      and re.match(r'FOLabCatcher\d+Script$', recordio.field(r, 'EDID') or ''))
    rep['rows'].append({'what': 'scripts', 'generators': gens, 'catchers': catchers})
    return rep


def _patched(src, edits):
    """src with each (pattern, replacement) applied; every one must change something."""
    for pat, rep in edits:
        new, n = re.subn(pat, rep, src, flags=re.M)
        if not n:
            raise ValueError('a script no longer has what its hook changes: %s' % pat)
        src = new
    return src


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import money
    import questrec as qr
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    out, rep, extra = [], {'made': [], 'skipped': list(P['skipped']), 'copies': [], 'scripts': []}, {}
    sc = api_scripts.scripts()
    perk = {t: _mod_key(pr, P_(t), 'PERK') for t in ('KahunasVoice', 'SilverTongue', 'CageBreaker', 'TongbaoBaron', 'CellMerchant',
                                                       'TalkStory', 'Tinkerer', 'VaultCharge', 'SalvageKing', 'GhostOfWaikiki',
                                                       'WordOnTheWater', 'SignalMan')}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k

    refs = {}
    for c_ in pr.cells.values():
        for rk_, r_ in (c_.get('refs') or {}).items():
            if r_.get('edid'):
                refs[r_['edid'].lower()] = rk_

    def remade(edid, edits, kind='object'):
        k = _mod_key(pr, edid, 'SCPT')
        if not k:
            rep['skipped'].append((edid, 'not in the mod'))
            return
        src = _patched(_source(pr.records[k]), edits)
        named = dict(extra)
        for name in set(re.findall(r'\b(\w+)\b', src)):
            if name.lower() in refs:                                    # (a named ref the script names: a stand-in, as its maker had)
                rk = refs[name.lower()]
                named[rk] = {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': name}]}
        c = sc.compile(src, k, kind, named)
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s again: %s' % (edid, c))
        record(edid, sc._record_of(c, edid), k)
        rep['scripts'].append(edid)
    # 1. copies first in their topics
    for row in [r for r in P['rows'] if r['what'] == 'copy']:
        rec = pr.records[row['line']]
        l = qr.info_plain(json.loads(json.dumps(rec)))
        l['topic'] = rec['topic']
        for c in l['conditions']:
            if int(c['fn']) == GETAV and c['p1'] == SPEECH and row['set'] == 'voice':
                c['value'] = max(0.0, float(c['value']) - EASIER)
            if int(c['fn']) == GETAV and c['p1'] == SPEECH and row['set'] == 'silver' and float(c['value']) >= SILVER[0]:
                c['value'] = float(SILVER[1])
        if row['set'] == 'cage':
            l['conditions'] = [c for c in l['conditions'] if not (int(c['fn']) == GETAV and c['p1'] == LOCKPICK)]
            l['skill'] = ''
        l['conditions'].append(_cond(HASPERK, '=', 1, perk[{'voice': 'KahunasVoice', 'silver': 'SilverTongue', 'cage': 'CageBreaker'}[row['set']]], 0, 1))
        new = aq._compiled_line(gd, pr, l)
        new['topic'] = rec['topic']
        new['seq'] = qr.line_seq(row['line'], rec) - 0.2
        nk = _new_key(pr)
        out.append({'op': 'record', 'key': nk, 'record': new})
        rep['copies'].append({'of': row['line'], 'key': nk, 'set': row['set']})
    # 2. scripts made again with the perk asked
    S = [r for r in P['rows'] if r['what'] == 'scripts'][0]
    tk, vk = P_('Tinkerer'), P_('VaultCharge')
    for g in S['generators']:
        remade(g, [
            (r'^(\t+)if player\.GetActorValue Science >= (\d+) && player\.GetItemCount (\w+) >= (\d+)$',
             r'\1set n to \4\n\1if player.HasPerk %s\n\1\tset n to \4 - 1\n\1endif\n\1if player.GetActorValue Science >= \2 && player.GetItemCount \3 >= n' % tk),
            (r'^(\t+)player\.RemoveItem (ScrapElectronics) (\d+)$', r'\1player.RemoveItem \2 n'),
            (r'^(\t+)if player\.GetActorValue Science >= (\d+)$', r'\1if player.GetActorValue Science >= \2 || player.HasPerk %s' % vk)])
    remade('FOLabSalvagerScript', [(r'^End$', '\tif player.HasPerk %s\n\t\tAddItem SensorModule 1\n\tendif\nEnd' % P_('SalvageKing'))])
    for c in S['catchers']:
        remade(c, [(r'^(\t+)if night == 1$', r'\1if night == 1 && player.HasPerk %s == 0' % P_('GhostOfWaikiki'))])
    # money's settling script with the 'cells5' mode (as money.quest_source now has it)
    mk = _mod_key(pr, money.SCRIPT, 'SCPT')
    if mk:
        mq = _mod_key(pr, money.QUEST, 'QUST')
        c = sc.compile(money.quest_source(), mk, 'quest', dict(extra, **{mq: pr.records[mq]}))
        if not hasattr(c, 'subrecords'):
            raise ValueError('the money script again: %s' % (c,))
        record(money.SCRIPT, sc._record_of(c, money.SCRIPT), mk)
        rep['scripts'].append(money.SCRIPT)
    # 3. the hooks' own quest: Word on the Water, Signal Man
    import huangradio
    note = huangradio.NOTE[0]          # (the numbers as decoded at the Radar Dome: Signal Man has them by ear)
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 30,
                             'delay': 1.0, 'stages': [], 'objectives': []})
    L = ['scn %s' % SCRIPT, 'short noted', 'short talk'] + ['short was%s' % s for s in SIDES] + ['short d', 'short started', '',
         'Begin GameMode',
         '\tif started == 0', '\t\tset started to 1'] + ['\t\tset was%s to FOLabNameOnWater.%s' % (s, s) for s in SIDES] + ['\tendif']
    for s in SIDES:
        L += ['\tset d to FOLabNameOnWater.%s - was%s' % (s, s),
              '\tif d != 0 && player.HasPerk %s' % P_('WordOnTheWater'), '\t\tset FOLabNameOnWater.%s to FOLabNameOnWater.%s + d / 2' % (s, s),
              '\tendif', '\tset was%s to FOLabNameOnWater.%s' % (s, s)]
    L += ['\tif noted == 0 && player.HasPerk %s' % P_('SignalMan'), '\t\tset noted to 1', '\t\tAddNote %s' % note, '\tendif', 'End', '']
    c = sc.compile('\n'.join(L), qsk, 'quest', dict(extra, **{qk: quest}))
    if not hasattr(c, 'subrecords'):
        raise ValueError('the hooks quest\'s script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    record(SCRIPT, srec, qsk)
    record(QUEST, quest, qk)
    hv = {}
    last = None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            hv[sub['value'].lower()] = last
    # 4. new lines (compiled after: they name the records above)
    lines = []
    mq = _mod_key(pr, money.QUEST, 'QUST')
    changer = _mod_key(pr, money.CHANGER[0], 'NPC_')
    tong = _mod_key(pr, money.TONGBAO[0], 'MISC')
    caps = gd.key(money.CAPS)
    has = lambda item, n: _cond(GETITEMCOUNT, '>=', n, item, 0, 1)
    baron = _cond(HASPERK, '=', 1, perk['TongbaoBaron'], 0, 1)
    topics = {k: _mod_key(pr, 'FOLabMoney%s' % k.capitalize(), 'DIAL') for k in ('sell10', 'sellall', 'buy10', 'cells')}

    def first_of(topic):
        seqs = [qr.line_seq(k, r) for k, r in pr.records.items() if r.get('type') == 'INFO' and r.get('topic') == topic]
        return (min(seqs) - 1.0) if seqs else None

    def line(topic, who, words, conds, end, seq=None):
        l = aq.new_line_plain(gd, pr, topic, mq if topic in topics.values() else rq, who, words, conditions=list(conds))
        if end:
            l['end'] = {'source': end, 'parts': None}
        lines.append((l, topic, seq if seq is not None else first_of(topic)))
    rq = _mod_key(pr, 'FOLabRumours', 'QUST')
    if changer and all(topics[k] for k in ('sell10', 'sellall', 'buy10')):
        line(topics['sell10'], changer, WORDS['sell10'], [has(tong, 10), baron],
             'player.RemoveItem %s 10\nplayer.AddItem Caps001 100' % money.TONGBAO[0])
        line(topics['sellall'], changer, WORDS['sellall'], [has(tong, 1), baron],
             '\n'.join(['set %s.n to player.GetItemCount %s' % (money.QUEST, money.TONGBAO[0]),
                        'player.RemoveItem %s %s.n' % (money.TONGBAO[0], money.QUEST),
                        'set %s.k to %s.n * 10' % (money.QUEST, money.QUEST), 'player.AddItem Caps001 %s.k' % money.QUEST]))
        line(topics['buy10'], changer, WORDS['buy10'], [has(caps, 100), baron],
             'player.RemoveItem Caps001 100\nplayer.AddItem %s 10' % money.TONGBAO[0])
    cell = gd.key(money._game(gd, money.CELL, ('AMMO',)))
    dq, dvars = money._var_index(pr, 'FOLabPirateDeals')
    if topics['cells'] and dq:
        for e, v in money.PIRATE_TRADERS:
            nk2 = _mod_key(pr, e, 'NPC_')
            if nk2 and v in dvars:
                line(topics['cells'], nk2, WORDS['cells5'], [_cond(GETQUESTVAR, '=', 1, dq, dvars[v]), has(cell, 1),
                                                             _cond(HASPERK, '=', 1, perk['CellMerchant'], 0, 1)], money.trade_in('cells5'))
    rt = _mod_key(pr, 'FOLabRumoursAsk', 'DIAL')
    if rt and rq:
        import rumours
        tellers = [k for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'EDID') in rumours.TELLERS]
        who = [dict(_cond(GETISID, '=', 1, k), **{'or': n < len(tellers) - 1}) for n, k in enumerate(tellers)]
        nothing = [(qr.line_seq(k, r), k) for k, r in pr.records.items() if r.get('type') == 'INFO' and r.get('topic') == rt
                   and any(x['text'] == rumours.NOTHING for x in qr.info_plain(r)['responses'])]
        seq = (min(nothing)[0] - 0.5) if nothing else None
        line(rt, None, WORDS['rumour'], who + [_cond(HASPERK, '=', 1, perk['TalkStory'], 0, 1), _cond(GETQUESTVAR, '=', 0, qk, hv['talk'])],
             'set %s.talk to 1' % QUEST, seq)
    rep['lines'] = len(lines)
    rep['keys'] = {'quest': qk}
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    import perks
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    later, made = [], []
    from activity import _new_key
    for l, topic, seq in lines:
        rec = aq._compiled_line(gd, pr, l)
        rec['topic'] = topic
        if seq is not None:
            rec['seq'] = seq
        k = _new_key(pr)
        later.append({'op': 'record', 'key': k, 'record': rec})
        made.append(k)
    pr.apply(LABEL, later, merge=True)
    rep['voice_copies'] = perks.voice_copies(gd, pr, rep['copies'])
    VOICE_ONLY.clear()
    VOICE_ONLY.update(made)
    # (a copy whose original has no voice files is voiced afresh, so no line is left silent)
    import questrec as qr
    bare = set(rep['voice_copies']['lines_without_files'])
    for c in rep['copies']:
        if c['of'] in bare:
            VOICE_ONLY.add(c['key'])
            q = recordio.field(pr.records.get(qr.info_plain(pr.records[c['key']])['quest']) or {'subs': []}, 'EDID')
            if q and q not in VOICE:
                VOICE.append(q)
    rep['voice_lines'] = len(VOICE_ONLY)
    rep['copies'] = len(rep['copies'])
    return rep
