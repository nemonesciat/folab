"""Brokering (docs/waikiki-speech-science.md section J, system 4): you carry goods between the island's sides, again and
again, for goods and fame with both.

Three routes (`ROUTES`), each between people the island already has and on a trade it already has:
- **silk:** the Huang's silk from Lin Meihua to Linda Moreno, Waikiki's trader ("the silk trade goes through her":
  huangquests.py). Open once Silk for Waikiki is done.
- **reef:** the court's goods from Linda Moreno to the pirates' trader on the Kahala trade ground ("where the two sides
  meet and trade": piratedeal.py). Open once you've dealt with that trader.
- **gate:** the pirates' goods from the Koko Marina boatyard trader to Zhao Lei at the Makapuu gate (the Huang trade
  there: rumours.py). Open once you've dealt with the boatyard trader.

How a run goes (the quest FOLabBroker keeps each route's runs and days; no money, goods only, as decided):
- **The one who sends** has a topic for it. When a load is due, they give you sealed goods (a MISC of the mod's own). If it
  isn't due yet, they say to come back. While you still carry the last load, they say where it goes.
- **The one who receives** takes it and pays in goods (`PAY`, by side). It adds 1 fame with both sides (AddReputation),
  and the next load is due `EVERY` days on.
- **The stash:** after `STEADY` runs on a route, its receiver keeps your share put by (`CUT`), to collect every `EVERY`
  days ("Anything put by for me?").
- **[proposal]** The pay, the share and the words are this step's own.

Every line is voiced in the step (voicelines.py; Zhao Lei's in his broken English).

    plan(gd, pr)       (rows, skipped)
    apply(pr, gd, P)   one Undo: records, then the lines compiled against them
"""
import recordio

LABEL = 'Brokering between the sides'
QUEST, SCRIPT = 'FOLabBroker', 'FOLabBrokerScript'
VOICE = [QUEST]
EVERY, STEADY = 3, 3
PACKAGE_FROM = 'VRRCMisfitsDrugs'              # (a sealed box: huangquests' silk bundle is the same)
GETISID, GETITEMCOUNT, GETQUESTVARIABLE, GETQUESTCOMPLETED = 72, 47, 79, 546
# route: sender (NPC_ editor ID, or a ref's), receiver, the sender's side, the receiver's, what opens it, the package
ROUTES = {
    'silk': {'from': ('ref', 'FOLabHuangSilkGiverREF'), 'to': ('npc', 'FOLabWaikikiTrader'), 'sides': ('huang', 'court'),
             'opens': ('quest', 'FOLabHuangSilk'), 'package': ('FOLabBrokerSilk', 'Huang Silk (for Linda Moreno)')},
    'reef': {'from': ('npc', 'FOLabWaikikiTrader'), 'to': ('npc', 'FOLabPirateTraderKahala'), 'sides': ('court', 'pirates'),
             'opens': ('var', 'FOLabPirateDeals', 'dealkahala'), 'package': ('FOLabBrokerReef', 'Court Goods (for the Kahala trade ground)')},
    'gate': {'from': ('npc', 'FOLabPirateTraderMarina'), 'to': ('npc', 'FOLabMakapuuGuard'), 'sides': ('pirates', 'huang'),
             'opens': ('var', 'FOLabPirateDeals', 'dealmarina'), 'package': ('FOLabBrokerGate', 'Boatyard Goods (for the Makapuu gate)')},
}
REP = {'court': 'FOLabRepCourt', 'pirates': 'FOLabRepPirates', 'huang': 'FOLabRepHuang'}
PAY = {'court': [('Stimpak', 2)], 'pirates': [('AmmoMicroFusionCell', 8)], 'huang': [('NVHealingPowder', 2)]}
CUT = {'court': [('Stimpak', 1)], 'pirates': [('AmmoMicroFusionCell', 4)], 'huang': [('NVHealingPowder', 1)]}
TOPICS = {   # route: (the sender's topic, the receiver's, the stash's)
    'silk': ("Any silk to carry to Linda?", "I've brought silk from Lin Meihua.", "Anything put by for me?"),
    'reef': ("Anything for the Kahala trade ground?", "Goods from Linda Moreno.", "Anything put by for me?"),
    'gate': ("Anything for the Makapuu gate?", "Goods from the Koko Marina boatyard.", "Anything put by for me?"),
}
WORDS = {    # route: (given, not yet, still carrying, taken and paid, the share)
    'silk': ("Yes. The bolts are wrapped and sealed. Linda knows our seal. Take care on the road.",
             "Not yet. The looms are slow this week. Come back in a few days.",
             "You still have the last bolts. Linda is waiting for them.",
             "Silk from the courtyards. Good. Here's what it's worth, and the Huang will hear you're reliable.",
             "Your share's put by. Here. Keep it coming."),
    'reef': ("There's a crate for the trade ground. Sealed. Don't open it, and don't let anyone else.",
             "Nothing today. The court sends when it sends. Try me in a few days.",
             "You've still got the last crate. The trade ground's on the Kahala, past the land gate.",
             "From Linda? Then it's straight. Here's your cut. The crews'll know your face.",
             "Put your share aside. Here. Don't spend it all on one boat."),
    'gate': ("A load for the gate. The Huang pay at the gate, so that's where it goes. Sealed. Keep it that way.",
             "Nothing ready. Boats come in when they come in. A few days.",
             "Still got the last load? The gate's at Makapuu. Go.",
             "Boatyard goods. Seal good. You take this. The elders hear of you.",
             "Your share. I keep for you. Take."),
}


def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _person(pr, how):
    kind, edid = how
    if kind == 'npc':
        return _key(pr, edid, 'NPC_')
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            if r.get('edid') == edid and not r.get('removed'):
                return r.get('base')
    return None


def _game(gd, tag, edid):
    f = next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)
    if f is None:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return f


def plan(gd, pr):
    rows, skipped = [], []
    if _key(pr, QUEST, 'QUST'):
        return rows, [(QUEST, 'already in the mod (Undo first)')]
    for side, rep in REP.items():
        if not _key(pr, rep, 'REPU'):
            return rows, [(rep, 'not in the mod (piratedeal first)')]
    for name, R in ROUTES.items():
        a, b = _person(pr, R['from']), _person(pr, R['to'])
        opens = R['opens']
        o = _key(pr, opens[1], 'QUST')
        if not a or not b or not o:
            skipped.append((name, 'missing: %s' % ', '.join(w for w, k in ((R['from'][1], a), (R['to'][1], b), (opens[1], o)) if not k)))
            continue
        rows.append({'route': name, 'from': a, 'to': b, 'opens': o})
    return rows, skipped


def _cond(fn, op, value, p1=0, p2=0, run=0, glob=None):
    c = {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': ''}
    if glob:
        c['global'] = glob
    else:
        c['value'] = float(value)
    return c


def _var_index(srec):
    index, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            index[sub['value'].lower()] = last
    return index


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    from activity import _new_key
    from surffish import _copy
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    out, rep = [], {'made': [], 'routes': [r['route'] for r in rows], 'skipped': skipped}
    quest_key, script_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': script_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 50, 'delay': 5.0, 'stages': [], 'objectives': []})
    L = ['scn %s' % SCRIPT]
    for r in rows:
        L += ['short runs%s' % r['route'], 'float next%s' % r['route'], 'float cut%s' % r['route']]
    L += ['short started', '', 'Begin GameMode', '\tif started == 0', '\t\tset started to 1', '\tendif', 'End', '']
    sc = api_scripts.scripts()
    c = sc.compile('\n'.join(L), script_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the broker script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    index = _var_index(srec)
    out += [{'op': 'record', 'key': script_key, 'record': srec}, {'op': 'record', 'key': quest_key, 'record': quest}]
    rep['made'] += [QUEST, SCRIPT]
    days = gd.key(_game(gd, 'GLOB', 'GameDaysPassed'))
    deals = _key(pr, 'FOLabPirateDeals', 'QUST')
    deal_index = {}
    if deals:
        ds = pr.records.get(next((s['value'] for s in pr.records[deals]['subs'] if s['tag'] == 'SCRI'), ''))
        deal_index = _var_index(ds) if ds else {}
    lines = []

    def line(topic, who, words, conds, end):
        l = aq.new_line_plain(gd, pr, topic, quest_key, who, words, conditions=conds)
        if end:
            l['end'] = {'source': end, 'parts': None}
        lines.append(l)
    for r in rows:
        R, name = ROUTES[r['route']], r['route']
        pkg_edid, pkg_name = R['package']
        pkg_key = _new_key(pr)
        pkg = _copy(gd, 'MISC', PACKAGE_FROM, pkg_edid, pkg_name)
        for s in pkg['subs']:
            if s['tag'] == 'DATA':
                for f in s.get('fields') or ():
                    if f.get('name') == 'Value':
                        f['value'] = 0
        out.append({'op': 'record', 'key': pkg_key, 'record': pkg})
        rep['made'].append(pkg_edid)
        topics = {}
        for part, words in zip(('ask', 'deliver', 'cut'), TOPICS[name]):
            topics[part] = _new_key(pr)
            out.append({'op': 'record', 'key': topics[part], 'record': qr.topic_record({
                'edid': 'FOLabBroker%s%s' % (name.capitalize(), part.capitalize()), 'name': words, 'priority': 50.0, 'kind': 0,
                'flags': {'top_level': True}, 'quests': [{'quest': quest_key, 'links': []}]})})
        if R['opens'][0] == 'quest':
            opens = [_cond(GETQUESTCOMPLETED, '=', 1, r['opens'])]
        else:
            v = deal_index.get(R['opens'][2])
            if v is None:
                raise ValueError('%s has no variable %s' % (R['opens'][1], R['opens'][2]))
            opens = [_cond(GETQUESTVARIABLE, '=', 1, r['opens'], v)]
        none = _cond(GETITEMCOUNT, '=', 0, pkg_key, 0, 1)
        some = _cond(GETITEMCOUNT, '>=', 1, pkg_key, 0, 1)
        due = _cond(GETQUESTVARIABLE, '<=', 0, quest_key, index['next' + name], glob=days)
        later = _cond(GETQUESTVARIABLE, '>', 0, quest_key, index['next' + name], glob=days)
        given, wait, carrying, paid, share = WORDS[name]
        a_side, b_side = R['sides']
        line(topics['ask'], r['from'], given, opens + [none, due], 'player.AddItem %s 1' % pkg_edid)
        line(topics['ask'], r['from'], wait, opens + [none, later], '')
        line(topics['ask'], r['from'], carrying, opens + [some], '')
        pay = '\n'.join('player.AddItem %s %d' % (e, n) for e, n in PAY[b_side])
        line(topics['deliver'], r['to'], paid, opens + [some],
             '\n'.join(['player.RemoveItem %s 1' % pkg_edid, pay, 'AddReputation %s 1 1' % REP[a_side], 'AddReputation %s 1 1' % REP[b_side],
                        'set %s.runs%s to %s.runs%s + 1' % (QUEST, name, QUEST, name),
                        'set %s.next%s to GameDaysPassed + %d' % (QUEST, name, EVERY),
                        'set %s.cut%s to GameDaysPassed + %d' % (QUEST, name, EVERY)]))
        cut = '\n'.join('player.AddItem %s %d' % (e, n) for e, n in CUT[b_side])
        line(topics['cut'], r['to'], share, [_cond(GETQUESTVARIABLE, '>=', STEADY, quest_key, index['runs' + name]),
                                             _cond(GETQUESTVARIABLE, '<=', 0, quest_key, index['cut' + name], glob=days)],
             cut + '\nset %s.cut%s to GameDaysPassed + %d' % (QUEST, name, EVERY))
    rep['lines'] = len(lines)
    rep['keys'] = {'quest': quest_key, 'script': script_key}
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    return rep
