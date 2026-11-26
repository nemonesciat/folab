"""Repair's uses (docs/waikiki-speech-science.md K2, K5; the user, 25 Nov 2026: "uses for high barter and repair ... let's go
with all of those"). In the quest FOLabWorkRepair; each side pays in its own money (money.py).

- **Fixing jobs** (`JOBS`), each once: someone's broken thing, "[Repair N] ... I can fix that." With the skill and the parts,
  it's fixed: the parts used (Tinkerer: one fewer), paid (Tinker's Pay: double), +2 with that side. With the skill but not
  the parts, they say what it takes. Without the skill, a fail line (try again with more).
  - a Waikiki pier fisher's winch (Repair 25, Scrap Metal);
  - the court watchman's radio at Kahuna Palms (40, Scrap Electronics);
  - Liu Wei's jammed gate guns (55, two Scrap Metal);
  - the Tanks' water pump (70, two Scrap Metal and Scrap Electronics);
  - the Flotilla quartermaster's boat engine (85, a Fission Battery and two Scrap Electronics).
- **Guns mended for people** (`MENDERS`): "[Repair 40] Let me look at that gun." with the island's armed people we know by
  name, once a game day, a Scrap Metal: paid in their side's money, +1 with that side.
- **Boats** (a wreck mended into the ferry, a boat of your own): wait for the ferry (boatferry.py is not in the mod).
- **The Kilauea's arcade machines:** arcadeset.py's (another step's), playable through the game's slot machine menu; fixing
  and rigging them is that step's to add.

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo (VOICE)
"""
import recordio

LABEL = "Repair's uses: fixing jobs, guns mended"
QUEST, SCRIPT = 'FOLabWorkRepair', 'FOLabWorkRepairScript'
VOICE = [QUEST]
GETAV, GETITEMCOUNT, GETQUESTVAR = 14, 47, 79
REPAIR = 39
PER = {'court': ('Caps001', 1), 'huang': ('FOLabTongbao', 10), 'pirates': ('AmmoSmallEnergyCell', 4)}
# job: (key, who (npc/ref, editor ID), side, Repair, parts [(item, n)], pay in kala, prompt, done, need parts, fail)
JOBS = [
    ('winch', ('npc', 'FOLabPierFisher'), 'court', 25, [('SpareParts', 1)], 15,
     "Your winch is jammed. I can fix that.", "Turns again. Good. The fish don't wait. Here.",
     "Needs a bit of scrap metal, that.", "That's worse than before. Leave it."),
    ('radio', ('npc', 'FOLabKPWatchman'), 'court', 40, [('ScrapElectronics', 1)], 30,
     "Your radio's dead. I can fix that.", "...There's the court's channel. Good work. Take this.",
     "It wants a part. Scrap electronics.", "It's still dead. Don't touch it again."),
    ('gateguns', ('ref', 'FOLabHuangOilGiverREF'), 'huang', 55, [('SpareParts', 2)], 60,
     "Your gate guns jam. I can fix that.", "...Clean. They feed well now. Good. Take these.",
     "Need metal. Two pieces.", "Still jam. No more."),
    ('pump', ('npc', 'FOLabPowerTraderTheTanks'), 'court', 70, [('SpareParts', 2), ('ScrapElectronics', 1)], 100,
     "Your water pump's failing. I can fix that.", "Listen to it. Like new. The Tanks owe you, and the Tanks pay. Here.",
     "You'd need scrap metal, two, and some electronics.", "It's making a worse noise now. Stop."),
    ('engine', ('npc', 'FOLabFlotillaQuartermaster'), 'pirates', 85, [('FissionBattery', 1), ('ScrapElectronics', 2)], 200,
     "That boat engine of yours is dying. I can fix that.", "...She runs. Captain'll want to know your name. Cells, as promised.",
     "Needs a fission battery and electronics. Find them.", "You've made it worse. Get off my boat."),
]
MENDERS = [('FOLabMakapuuGuard', 'huang'), ('FOLabKPWatchman', 'court'), ('FOLabKahunaGuard01', 'court'),
           ('FOLabPirateTraderKahala', 'pirates'), ('FOLabPirateTraderMarina', 'pirates'), ('FOLabFlotillaPenGuard', 'pirates')]
MEND_SKILL, MEND_PAY, MEND_PART = 40, 12, ('SpareParts', 1)
WORDS = {'mend': "Let me look at that gun.", 'mend_yes': "...Smooth as new. Here, for your trouble.",
         'mend_no': "You'll break it. Leave it.", 'mend_parts': "You'd need a bit of scrap metal.", 'mend_later': "You did it already today."}


def _cond(fn, op, value, p1=0, p2=0, run=0, glob=None):
    c = {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': ''}
    if glob:
        c['global'] = glob
    else:
        c['value'] = float(value)
    return c


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _who(pr, who):
    import barterwork
    return barterwork._payer(pr, who)


def plan(gd, pr):
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % QUEST))
        return rep
    for j in JOBS:
        k = _who(pr, j[1])
        if k:
            rep['rows'].append({'what': 'job', 'key': j[0], 'who': k, 'side': j[2], 'repair': j[3]})
        else:
            rep['skipped'].append(('job ' + j[0], '%s not in the mod' % (j[1][1],)))
    for e, side in MENDERS:
        k = _mod_key(pr, e, 'NPC_')
        if k:
            rep['rows'].append({'what': 'mender', 'edid': e, 'who': k, 'side': side})
    rep['skipped'] += [('boats', 'wait for the ferry (boatferry.py is not in the mod)'),
                       ('arcade', "the Kilauea's machines are arcadeset.py's: fixing and rigging them is that step's")]
    return rep


def _money(side, kala):
    item, per = PER[side]
    return item, max(1, int(round(kala / float(per))))


def _item_key(gd, pr, edid):
    return _mod_key(pr, edid) or gd.key(next(f for f, (_i, r) in gd.forms.items() if gd.edid(f) == edid and r.tag in ('MISC', 'ALCH', 'AMMO')))


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    import repstanding as RS
    import skillcheck
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    rows = P['rows']
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped']), 'jobs': [], 'menders': []}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 40,
                             'delay': 60.0, 'stages': [], 'objectives': []})
    V = ['k', 'n'] + ['done%s' % r['key'] for r in rows if r['what'] == 'job'] + ['nextmend']
    src = '\n'.join(['scn %s' % SCRIPT] + ['%s %s' % ('float' if v == 'nextmend' else 'short', v) for v in V] + ['', 'Begin GameMode', 'End', ''])
    sc = api_scripts.scripts()
    c = sc.compile(src, qsk, 'quest', {qk: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the repair work script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    record(SCRIPT, srec, qsk)
    record(QUEST, quest, qk)
    vi, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            vi[sub['value'].lower()] = last
    qv = lambda var, op, v: _cond(GETQUESTVAR, op, v, qk, vi[var.lower()])
    days = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'GLOB' and gd.edid(f) == 'GameDaysPassed'))
    tinkerer = _mod_key(pr, 'FOLabPerkTinkerer', 'PERK')
    tinkpay = _mod_key(pr, 'FOLabPerkTinkersPay', 'PERK')
    lines = []
    tkeys = {}

    def topic(k, words):
        if k not in tkeys:
            tkeys[k] = record('FOLabWorkRepair%s' % k.capitalize(), qr.topic_record({
                'edid': 'FOLabWorkRepair%s' % k.capitalize(), 'name': words, 'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
                'quests': [{'quest': qk, 'links': []}]}))
        return tkeys[k]

    def line(t, who, words, conds, end='', skill=True):
        l = aq.new_line_plain(gd, pr, t, qk, who, words, conditions=list(conds))
        if end:
            l['end'] = {'source': end, 'parts': None}
        if skill:
            l['skill'] = skillcheck.skill_key(gd, 'Repair')
        lines.append(l)
    J = {j[0]: j for j in JOBS}
    for r in [r for r in rows if r['what'] == 'job']:
        key, _w, side, need, parts, pay, prompt, done, wants, fail = J[r['key']]
        t = topic(key, '[Repair %d] %s' % (need, prompt))
        open_ = qv('done' + key, '=', 0)
        skill_ok = _cond(GETAV, '>=', need, REPAIR, 0, 1)
        # the parts: the first part one fewer with Tinkerer (never under none)
        first, n0 = parts[0]
        has_all = [_cond(GETITEMCOUNT, '>=', n, _item_key(gd, pr, it), 0, 1) for it, n in parts]
        item, m = _money(side, pay)
        end = ['set %s.n to %d' % (QUEST, n0)]
        if tinkerer:
            end += ['if player.HasPerk FOLabPerkTinkerer', 'set %s.n to %d' % (QUEST, max(0, n0 - 1)), 'endif']
        end += ['if %s.n > 0' % QUEST, 'player.RemoveItem %s %s.n' % (first, QUEST), 'endif']
        end += ['player.RemoveItem %s %d' % (it, n) for it, n in parts[1:]]
        end += ['set %s.k to %d' % (QUEST, m)]
        if tinkpay:
            end += ['if player.HasPerk FOLabPerkTinkersPay', 'set %s.k to %s.k * 2' % (QUEST, QUEST), 'endif']
        end += ['player.AddItem %s %s.k' % (item, QUEST), 'set %s.done%s to 1' % (QUEST, key), RS.bump(side, 2), 'RewardXP %d' % (need // 2)]
        line(t, r['who'], '[SUCCEEDED] ' + done, [open_, skill_ok] + has_all, '\n'.join(end))
        if tinkerer and n0 >= 1:          # (with Tinkerer, one fewer of the first part is enough)
            fewer = [_cond(GETITEMCOUNT, '>=', max(0, n0 - 1), _item_key(gd, pr, first), 0, 1)] + has_all[1:]
            line(t, r['who'], '[SUCCEEDED] ' + done, [open_, skill_ok, _cond(449, '=', 1, tinkerer, 0, 1)] + fewer, '\n'.join(end))
        line(t, r['who'], wants, [open_, skill_ok], '', skill=False)
        line(t, r['who'], '[FAILED] ' + fail, [open_, _cond(GETAV, '<', need, REPAIR, 0, 1)])
        rep['jobs'].append({'job': key, 'repair': need, 'parts': parts, 'pay': '%d %s' % (m, item)})
    # guns mended for people
    tm = topic('mend', '[Repair %d] %s' % (MEND_SKILL, WORDS['mend']))
    part = _item_key(gd, pr, MEND_PART[0])
    for r in [r for r in rows if r['what'] == 'mender']:
        item, m = _money(r['side'], MEND_PAY)
        due = _cond(GETQUESTVAR, '<=', 0, qk, vi['nextmend'], glob=days)
        line(tm, r['who'], '[SUCCEEDED] ' + WORDS['mend_yes'], [due, _cond(GETAV, '>=', MEND_SKILL, REPAIR, 0, 1), _cond(GETITEMCOUNT, '>=', 1, part, 0, 1)],
             '\n'.join(['player.RemoveItem %s 1' % MEND_PART[0], 'player.AddItem %s %d' % (item, m),
                        'set %s.nextmend to GameDaysPassed + 1' % QUEST, RS.bump(r['side'], 1)]))
        line(tm, r['who'], WORDS['mend_parts'], [due, _cond(GETAV, '>=', MEND_SKILL, REPAIR, 0, 1)], '', skill=False)
        line(tm, r['who'], WORDS['mend_later'], [_cond(GETAV, '>=', MEND_SKILL, REPAIR, 0, 1)], '', skill=False)
        line(tm, r['who'], '[FAILED] ' + WORDS['mend_no'], [_cond(GETAV, '<', MEND_SKILL, REPAIR, 0, 1)])
        rep['menders'].append(r['edid'])
    rep['lines'] = len(lines)
    rep['keys'] = {'quest': qk}
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    return rep
