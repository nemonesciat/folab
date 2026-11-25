"""Barter's uses beyond the barter window (docs/waikiki-speech-science.md K2, K5; the user, 25 Nov 2026: "uses for high barter
... let's go with all of those"). All in the quest FOLabWorkBarter, each side paying in its own money (money.py).

- **Haggled pay** (`HAGGLE`): "[Barter 40] About my pay..." with whoever pays for a job, once a job: 70 and over gets half
  as much again, 40 and over a quarter, under 40 a shrug and a little face lost with that side. The doctor's and the gate
  guard's errands and the Huáng's three quests (while you're on the way back: stage 20), the brokering routes (while you
  carry the goods: the bonus with the pay).
- **Trade contracts** (`CONTRACTS`): a standing order from Linda Moreno (the court), Kailua's Shangren (the Huáng) and the
  Kāhala's Pirate Trader (the pirates), offered once that side thinks well enough of you (its band 2 or more). Deliver every
  `CONTRACT_DAYS` days; Barter 55 raises the pay, Contract Hand a quarter more.
- **Exchange rates** (`RATES`): the pirate traders take cells at five with Barter 55 (money's 'cells5' mode, for good);
  Linda Moreno takes tongbao at nine kala with Barter 40.
- **Smuggling** (`SMUGGLE`): Koko Marina's Boatyard Trader has sealed crates of cells for Linda Moreno, in the court's own
  Waikiki where pirate goods aren't welcome (pirates' band 2 or more). Each run pays more, up to the third. Carried on the
  island, each hour a court patrol may search you (Sneak lowers the chance; Smuggler's Purse or Shadow Trader: never): the
  crate taken, court -5 and infamy.
- **Passage:** waits for the ferry (boatferry.py is not in the mod).

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo (VOICE, VOICE_ONLY)
"""
import json

import recordio

LABEL = "Barter's uses: haggling, contracts, rates, smuggling"
QUEST, SCRIPT = 'FOLabWorkBarter', 'FOLabWorkBarterScript'
VOICE = [QUEST]
VOICE_ONLY = None
GETAV, GETISID, GETITEMCOUNT, GETQUESTVAR, GETSTAGE, HASPERK = 14, 72, 47, 79, 58, 449
BARTER = 32
PER = {'court': ('Caps001', 1), 'huang': ('FOLabTongbao', 10), 'pirates': ('AmmoSmallEnergyCell', 4)}   # (money, kala a piece)
# job: (quest, the payer by NPC editor ID or by ref editor ID, its side, worth in kala (what the job pays), when: 'stage' or the brokering route)
HAGGLE = [
    ('doctor', 'FOLabDoctorsStock', ('npc', 'FOLabWaikikiDoctor'), 'court', 60, 'stage'),
    ('gate', 'FOLabMakapuuGate', ('npc', 'FOLabMakapuuGuard'), 'huang', 50, 'stage'),
    ('silk', 'FOLabHuangSilk', ('ref', 'FOLabHuangSilkGiverREF'), 'huang', 50, 'stage'),
    ('pests', 'FOLabHuangPests', ('ref', 'FOLabHuangPestsGiverREF'), 'huang', 50, 'stage'),
    ('oil', 'FOLabHuangOil', ('ref', 'FOLabHuangOilGiverREF'), 'huang', 50, 'stage'),
    ('bsilk', 'FOLabBroker', ('npc', 'FOLabWaikikiTrader'), 'court', 20, 'FOLabBrokerSilk'),
    ('breef', 'FOLabBroker', ('npc', 'FOLabPirateTraderKahala'), 'pirates', 32, 'FOLabBrokerReef'),
    ('bgate', 'FOLabBroker', ('npc', 'FOLabMakapuuGuard'), 'huang', 20, 'FOLabBrokerGate'),
]
HAGGLE_TIERS = ((70, 0.5), (40, 0.25))
HAGGLE_FACE = 2
# contract: (who, side, wanted (item, count), pay in kala before Barter, more at Barter 55, words)
CONTRACTS = [
    ('linda', 'FOLabWaikikiTrader', 'court', ('FOLabRawReefFish', 4), 40, 15),
    ('shangren', 'FOLabHuangTraderKailua', 'huang', ('ScrapElectronics', 3), 50, 20),
    ('kahala', 'FOLabPirateTraderKahala', 'pirates', ('Stimpak', 3), 100, 32),
]
CONTRACT_DAYS, CONTRACT_BAND = 3, 2
CELLS_BARTER, TONG_BARTER, TONG_RATE = 55, 40, 9
SMUGGLE = {'from': 'FOLabPirateTraderMarina', 'to': 'FOLabWaikikiTrader', 'crate': ('FOLabSmuggledCells', 'Sealed Cell Crate'),
           'pay': (60, 80, 100), 'every': 3, 'search': 15, 'band': 2}
WORDS = {
    'haggle': "About my pay...",
    'h70': "...You drive a hard bargain. All right. Half again, and don't tell anyone.",
    'h40': "Fine. A little more. Don't make a habit of it.",
    'hno': "The pay is the pay.",
    'h70_zh': "...Hard bargain. Good. Half again more.", 'h40_zh': "Fine. A little more.", 'hno_zh': "Pay is pay. No more.",
    'work': "Got any standing work?",
    'linda_offer': "Steady work? Bring me four reef fish every few days and I'll pay forty kala, more if you can talk a price. Deal?",
    'shangren_offer': "Work. Three scrap electronics, every three days. I pay tongbao. Good tongbao.",
    'kahala_offer': "You're not stray now. Three stimpaks, every few days, and I pay in cells. Good cells.",
    'deliver': "Here's this delivery.",
    'paid': "That's the lot. Here's your pay. Same again in a few days.",
    'paid_zh': "Good. Here. Again in three days.",
    'notyet': "Not yet. Come back in a few days.",
    'notyet_zh': "Not yet. Three days.",
    'stranger': "I don't give steady work to people I don't know.",
    'stranger_zh': "No work for strangers.",
    'cells': "Five kala a cell, or I trade them elsewhere.",
    'cells_yes': "...Five. Fine. You've got a head for this.",
    'cells_no': "Four, and be glad of it.",
    'cells_agreed': "Five a cell, as agreed. Show me.",
    'tong': "Will you take tongbao?",
    'tong_yes': "Huang coin? ...All right, nine kala a coin. The court won't hear it from me.",
    'tong_no': "I deal in kala. Take that to the Huang.",
    'tong10': "Change ten tongbao. (90 Kala)",
    'tong10_yes': "Ninety kala. Count it.",
    'smuggle': "Any cargo that needs moving quietly?",
    'smuggle_yes': "Sealed crate of cells for Linda Moreno, in Waikiki. The court doesn't like our goods there, so don't get searched. She pays on delivery.",
    'smuggle_wait': "Not now. Come back in a few days.",
    'smuggle_no': "Not for strays.",
    'smuggled': "I have a crate for you. From the marina.",
    'smuggled_yes': "...Quietly, then. Here. Tell them the same again.",
    'searched': "A court patrol searches your pack and takes the sealed crate. They'll remember your face.",
}


def _cond(fn, op, value, p1=0, p2=0, run=0, glob=None, orr=False):
    c = {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': ''}
    if glob:
        c['global'] = glob
    else:
        c['value'] = float(value)
    return c


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _ref_base(pr, edid):
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            if r.get('edid') == edid and not r.get('removed'):
                return r.get('base')
    return None


def _payer(pr, who):
    kind, e = who
    return _mod_key(pr, e, 'NPC_') if kind == 'npc' else _ref_base(pr, e)


def plan(gd, pr):
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % QUEST))
        return rep
    if not _mod_key(pr, 'FOLabMoney', 'QUST'):
        rep['skipped'].append(('all', 'the money step is not in the mod'))
        return rep
    for key, quest, who, side, worth, when in HAGGLE:
        payer = _payer(pr, who)
        if not _mod_key(pr, quest, 'QUST') or not payer:
            rep['skipped'].append(('haggle ' + key, 'its quest or payer is not in the mod'))
            continue
        rep['rows'].append({'what': 'haggle', 'key': key, 'quest': quest, 'payer': payer, 'side': side, 'worth': worth, 'when': when})
    for key, who, side, want, pay, more in CONTRACTS:
        k = _mod_key(pr, who, 'NPC_')
        if not k:
            rep['skipped'].append(('contract ' + key, '%s not in the mod' % who))
            continue
        rep['rows'].append({'what': 'contract', 'key': key, 'who': k, 'side': side, 'want': want, 'pay': pay, 'more': more})
    for e in (SMUGGLE['from'], SMUGGLE['to']):
        if not _mod_key(pr, e, 'NPC_'):
            rep['skipped'].append(('smuggling', '%s not in the mod' % e))
    rep['skipped'].append(('passage', 'waits for the ferry (boatferry.py is not in the mod)'))
    return rep


def _money(side, kala):
    item, per = PER[side]
    return item, max(1, int(round(kala / float(per))))


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import money
    import questrec as qr
    import repstanding as RS
    import skillcheck
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    rows = P['rows']
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped']), 'ways': {}}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    huang_fac = _mod_key(pr, 'FOLabHuangFaction', 'FACT')
    is_huang = lambda npc: bool(huang_fac) and any(s['tag'] == 'SNAM' and huang_fac in json.dumps(s) for s in (pr.records.get(npc) or {}).get('subs', []))
    # the smuggled crate
    crate = None
    if _mod_key(pr, SMUGGLE['from'], 'NPC_') and _mod_key(pr, SMUGGLE['to'], 'NPC_'):
        rec = json.loads(json.dumps(recordio.load(gd, next(f for f, (_i, r) in gd.forms.items() if r.tag == 'MISC' and gd.edid(f) == 'VMS16bMedicalSupplies'))))
        rec['src'] = ''
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SCRI', 'MODT')]
        recordio.set_field(rec, 'EDID', SMUGGLE['crate'][0], label='Editor ID')
        recordio.set_field(rec, 'FULL', SMUGGLE['crate'][1])
        crate = record(SMUGGLE['crate'][0], rec)
    import generators
    record('FOLabSmuggleSearchedMsg', generators._message('FOLabSmuggleSearchedMsg', WORDS['searched']))
    # the quest and its script
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 40,
                             'delay': 5.0, 'stages': [], 'objectives': []})
    V = ['k', 'cellsbetter', 'lindatong', 'runs', 'carrying', 'lasthour', 'roll'] + ['h%s' % r['key'] for r in rows if r['what'] == 'haggle'] + \
        ['con%s' % r['key'] for r in rows if r['what'] == 'contract'] + ['due%s' % r['key'] for r in rows if r['what'] == 'contract'] + ['nextrun']
    L = ['scn %s' % SCRIPT] + ['%s %s' % ('float' if v.startswith('due') or v in ('nextrun', 'lasthour') else 'short', v) for v in V] + [
        '', 'Begin GameMode']
    if crate:
        perks = [p for p in ('FOLabPerkSmugglersPurse', 'FOLabPerkShadowTrader') if _mod_key(pr, p, 'PERK')]
        safe = ' && '.join('player.HasPerk %s == 0' % p for p in perks) or '1'
        L += ['\tif player.GetItemCount %s > 0' % SMUGGLE['crate'][0],
              '\t\tif GameDaysPassed * 24 >= lasthour + 1', '\t\t\tset lasthour to GameDaysPassed * 24',
              '\t\t\tif player.GetInWorldspace FOLabWaikiki && %s' % safe,
              '\t\t\t\tset roll to %d - player.GetActorValue Sneak / 10' % SMUGGLE['search'], '\t\t\t\tif roll < 3', '\t\t\t\t\tset roll to 3', '\t\t\t\tendif',
              '\t\t\t\tif GetRandomPercent < roll', '\t\t\t\t\tplayer.RemoveItem %s 1' % SMUGGLE['crate'][0], '\t\t\t\t\tShowMessage FOLabSmuggleSearchedMsg',
              '\t\t\t\t\t' + RS.bump('court', -5), '\t\t\t\t\tAddReputation FOLabRepCourt 0 1', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif']
    L += ['End', '']
    sc = api_scripts.scripts()
    c = sc.compile('\n'.join(L), qsk, 'quest', dict(extra, **{qk: quest}))
    if not hasattr(c, 'subrecords'):
        raise ValueError('the barter work script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    record(SCRIPT, srec, qsk)
    record(QUEST, quest, qk)
    vi, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            vi[sub['value'].lower()] = last
    topics = {}

    def topic(k, words):
        if k not in topics:
            topics[k] = record('FOLabWork%s' % k.capitalize(), qr.topic_record({
                'edid': 'FOLabWorkBarter%s' % k.capitalize(), 'name': words, 'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
                'quests': [{'quest': qk, 'links': []}]}))
        return topics[k]
    days = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'GLOB' and gd.edid(f) == 'GameDaysPassed'))
    qv = lambda var, op, v: _cond(GETQUESTVAR, op, v, qk, vi[var.lower()])
    lines = []

    def line(t, who, words, conds=(), end='', skill=None, need=None):
        l = aq.new_line_plain(gd, pr, t, qk, who, words, conditions=list(conds))
        if end:
            l['end'] = {'source': end, 'parts': None}
        if skill:
            l['skill'] = skillcheck.skill_key(gd, skill)
        lines.append(l)
    say = lambda who, k: WORDS[k + '_zh'] if is_huang(who) and (k + '_zh') in WORDS else WORDS[k]
    # 1. haggling
    for r in [r for r in rows if r['what'] == 'haggle']:
        t = topic('haggle', '[Barter 40] ' + WORDS['haggle'])
        h = 'h' + r['key']
        if r['when'] == 'stage':
            qkey = _mod_key(pr, r['quest'], 'QUST')
            when = [_cond(GETSTAGE, '=', 20, qkey)]
        else:
            pkg = _mod_key(pr, r['when'], 'MISC')
            when = [_cond(GETITEMCOUNT, '>=', 1, pkg, 0, 1)] if pkg else []
        base = when + [qv(h, '=', 0)]
        for need, share in HAGGLE_TIERS:
            item, n = _money(r['side'], r['worth'] * share)
            line(t, r['payer'], '[SUCCEEDED] ' + say(r['payer'], 'h70' if need == 70 else 'h40'),
                 base + [_cond(GETAV, '>=', need, BARTER, 0, 1)], 'set %s.%s to 1\nplayer.AddItem %s %d' % (QUEST, h, item, n), 'Barter')
        line(t, r['payer'], '[FAILED] ' + say(r['payer'], 'hno'), base + [_cond(GETAV, '<', HAGGLE_TIERS[-1][0], BARTER, 0, 1)],
             'set %s.%s to 1\n%s' % (QUEST, h, RS.bump(r['side'], -HAGGLE_FACE)), 'Barter')
        rep['ways'].setdefault('haggle', []).append(r['key'])
    # 2. contracts
    bands = {'court': 'bandcourt', 'huang': 'bandhuang', 'pirates': 'bandpirates'}
    nkey, nv = money._var_index(pr, 'FOLabNameOnWater')
    ch = _mod_key(pr, 'FOLabPerkContractHand', 'PERK')
    for r in [r for r in rows if r['what'] == 'contract']:
        tw, td = topic('work', WORDS['work']), topic('deliver', WORDS['deliver'])
        con, due = 'con' + r['key'], 'due' + r['key']
        band = _cond(GETQUESTVAR, '>=', CONTRACT_BAND, nkey, nv[bands[r['side']]]) if nkey and bands[r['side']] in nv else None
        lowband = _cond(GETQUESTVAR, '<', CONTRACT_BAND, nkey, nv[bands[r['side']]]) if band else None
        item, cnt = r['want']
        ikey = _mod_key(pr, item) or gd.key(next(f for f, (_i, x) in gd.forms.items() if gd.edid(f) == item and x.tag in ('ALCH', 'MISC', 'AMMO')))
        line(tw, r['who'], WORDS[r['key'] + '_offer'], [qv(con, '=', 0)] + ([band] if band else []),
             'set %s.%s to 1\nset %s.%s to GameDaysPassed' % (QUEST, con, QUEST, due))
        if lowband:
            line(tw, r['who'], say(r['who'], 'stranger'), [qv(con, '=', 0), lowband])
        mitem, _per = PER[r['side']]
        m_base, m_more = _money(r['side'], r['pay'])[1], _money(r['side'], r['pay'] + r['more'])[1]
        pay = ['set %s.k to %d' % (QUEST, m_base), 'if player.GetActorValue Barter >= 55', 'set %s.k to %d' % (QUEST, m_more), 'endif']
        if ch:
            pay += ['if player.HasPerk FOLabPerkContractHand', 'set %s.k to %s.k * 5 / 4' % (QUEST, QUEST), 'endif']
        pay += ['player.RemoveItem %s %d' % (item, cnt), 'player.AddItem %s %s.k' % (mitem, QUEST),
                'set %s.%s to GameDaysPassed + %d' % (QUEST, due, CONTRACT_DAYS), RS.bump(r['side'], 1)]
        line(td, r['who'], say(r['who'], 'paid'), [qv(con, '=', 1), _cond(GETQUESTVAR, '<=', 0, qk, vi[due], glob=days),
                                                    _cond(GETITEMCOUNT, '>=', cnt, ikey, 0, 1)], '\n'.join(pay))
        line(td, r['who'], say(r['who'], 'notyet'), [qv(con, '=', 1)])
        rep['ways'].setdefault('contracts', []).append(r['key'])
    # 3. rates
    dq, dvars = money._var_index(pr, 'FOLabPirateDeals')
    cell_topic = _mod_key(pr, 'FOLabMoneyCells', 'DIAL')
    cell = gd.key(money._game(gd, money.CELL, ('AMMO',)))
    for e, v in money.PIRATE_TRADERS:
        nk = _mod_key(pr, e, 'NPC_')
        if nk and dq and v in dvars:
            t = topic('cellrate', '[Barter %d] %s' % (CELLS_BARTER, WORDS['cells']))
            dealt = _cond(GETQUESTVAR, '=', 1, dq, dvars[v])
            line(t, nk, '[SUCCEEDED] ' + WORDS['cells_yes'], [dealt, qv('cellsbetter', '=', 0), _cond(GETAV, '>=', CELLS_BARTER, BARTER, 0, 1)],
                 'set %s.cellsbetter to 1' % QUEST, 'Barter')
            line(t, nk, '[FAILED] ' + WORDS['cells_no'], [dealt, qv('cellsbetter', '=', 0), _cond(GETAV, '<', CELLS_BARTER, BARTER, 0, 1)], '', 'Barter')
            if cell_topic:
                line(cell_topic, nk, WORDS['cells_agreed'],
                     [dealt, qv('cellsbetter', '=', 1), _cond(GETITEMCOUNT, '>=', 1, cell, 0, 1)], money.trade_in('cells5'))
    linda = _mod_key(pr, 'FOLabWaikikiTrader', 'NPC_')
    tong = _mod_key(pr, money.TONGBAO[0], 'MISC')
    if linda and tong:
        t = topic('tong', '[Barter %d] %s' % (TONG_BARTER, WORDS['tong']))
        line(t, linda, '[SUCCEEDED] ' + WORDS['tong_yes'], [qv('lindatong', '=', 0), _cond(GETAV, '>=', TONG_BARTER, BARTER, 0, 1)],
             'set %s.lindatong to 1' % QUEST, 'Barter')
        line(t, linda, '[FAILED] ' + WORDS['tong_no'], [qv('lindatong', '=', 0), _cond(GETAV, '<', TONG_BARTER, BARTER, 0, 1)], '', 'Barter')
        t10 = topic('tong10', WORDS['tong10'])
        line(t10, linda, WORDS['tong10_yes'], [qv('lindatong', '=', 1), _cond(GETITEMCOUNT, '>=', 10, tong, 0, 1)],
             'player.RemoveItem %s 10\nplayer.AddItem Caps001 %d' % (money.TONGBAO[0], 10 * TONG_RATE))
        rep['ways']['rates'] = ['cells at 5 (Barter %d)' % CELLS_BARTER, 'tongbao at Linda (Barter %d)' % TONG_BARTER]
    # 4. smuggling
    if crate:
        src, dst = _mod_key(pr, SMUGGLE['from'], 'NPC_'), _mod_key(pr, SMUGGLE['to'], 'NPC_')
        ts, tg = topic('smuggle', WORDS['smuggle']), topic('smuggled', WORDS['smuggled'])
        band = _cond(GETQUESTVAR, '>=', SMUGGLE['band'], nkey, nv['bandpirates']) if nkey and 'bandpirates' in nv else None
        has = _cond(GETITEMCOUNT, '>=', 1, crate, 0, 1)
        none = _cond(GETITEMCOUNT, '=', 0, crate, 0, 1)
        line(ts, src, WORDS['smuggle_yes'], [none, _cond(GETQUESTVAR, '<=', 0, qk, vi['nextrun'], glob=days)] + ([band] if band else []),
             'player.AddItem %s 1' % SMUGGLE['crate'][0])
        line(ts, src, WORDS['smuggle_wait'], [none] + ([band] if band else []))
        if band:
            line(ts, src, WORDS['smuggle_no'], [_cond(GETQUESTVAR, '<', SMUGGLE['band'], nkey, nv['bandpirates'])])
        pays = SMUGGLE['pay']
        pay = ['player.RemoveItem %s 1' % SMUGGLE['crate'][0], 'set %s.k to %d' % (QUEST, pays[-1])]
        for n, p in enumerate(pays[:-1]):
            pay += ['if %s.runs == %d' % (QUEST, n), 'set %s.k to %d' % (QUEST, p), 'endif']
        pay += ['player.AddItem Caps001 %s.k' % QUEST, 'set %s.runs to %s.runs + 1' % (QUEST, QUEST),
                'set %s.nextrun to GameDaysPassed + %d' % (QUEST, SMUGGLE['every']), RS.bump('pirates', 2)]
        line(tg, dst, WORDS['smuggled_yes'], [has], '\n'.join(pay))
        rep['ways']['smuggling'] = 'runs pay %s kala' % (pays,)
    rep['lines'] = len(lines)
    rep['keys'] = {'quest': qk}
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    return rep
