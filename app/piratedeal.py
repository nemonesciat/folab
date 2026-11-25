"""Pirates who deal, the court's toll, and the island's three reputations (docs/waikiki-speech-science.md pick 4; the user,
25 Nov 2026: "some pirates can deal, rep shown in pipboy").

- **Reputations** (`REPS`): REPU records for the Kahuna's Court, the Pirates and the Huang, the game's way. They show on
  the Pip-Boy's Stats page once you have fame or infamy with them; scripts add fame with AddReputation. The pictures
  are the game's for now (The Strip, the Powder Gangers, the Boomers); FOLab's own come later.
- **Pirates who deal** (the concept map: pirates on the coast, the Kāhala and Hawaiʻi Kai, never in the city).
  - Who changes: every pirate of the mod's own standing within `KAHALA_R` of the Kāhala Reef hotel (its trade ground
    and compound, decided as "where the two sides meet and trade") or within `MARINA_R` of Koko Marina's marker.
  - How: each is swapped to a copy of its record in the faction FOLabPirateTraders: neutral to you, allied to the
    Fiends' faction the other pirates are in, helping nobody. So they don't join a fight against you, and the others
    don't fight them.
  - Pirates everywhere else stay hostile.
- **Two pirate traders**, one at the trade ground outside the Kāhala's land gate and one at Koko Marina's boatyard:
  - each sells from a buried merchant chest (waikikilife's storekeepers' way);
  - "Let's deal." asks Speech 40 the first time. A pass opens the barter window (ShowBarterMenu in the line's end script,
    as Waikiki's "Let's trade.") and adds 1 fame with the Pirates. After that, "Let's trade." always works;
  - a fail can be tried again once your Speech is higher.
- **The court's toll post**: the court fighters by the post (factionfolk's, on the deck and round it) ask for the toll.
  - "[Speech 40] I'm the Kahuna's guest." A pass is waved through, with 1 fame with the Court.
  - Or "Pay the toll. (1 Stimpak)" while you carry one: goods, since money is undecided.
  - Once a game day, either way.

    plan(gd, pr)    {'rows': [...], 'skipped': [...], ...} what changes and where the traders stand
    ops(gd, pr, P)  (ops, report): one Undo
"""
import math

import recordio

LABEL = 'Pirates who deal, the toll post, and the reputations'
REPS = {'court': ('FOLabRepCourt', "The Kahuna's Court", 'RepNVTheStrip'),
        'pirates': ('FOLabRepPirates', 'The Pirates', 'RepNVPowderGanger'),
        'huang': ('FOLabRepHuang', 'The Huang', 'RepNVBoomer')}
FACTION = ('FOLabPirateTraders', 'Pirate Traders')
FIENDS = 'FiendsFactionNV'
KAHALA, KAHALA_R = 'FOLabHotelKahalaReef', 3000.0
MARINA, MARINA_R = 'Koko Marina', 5000.0
TRADE_PIECE = 'Table02'                     # (pirates.py's trade ground: tables outside the land gate)
QUEST, SCRIPT = 'FOLabPirateDeals', 'FOLabPirateDealsScript'
DEAL_SPEECH, TOLL_SPEECH = 40, 40
TRADERS = [('kahala', 'FOLabPirateTraderKahala', 'Pirate Trader', 'VendorContainerChet',
            "Trade ground. Nobody fights here. That's the rule. What do you want?"),
           ('marina', 'FOLabPirateTraderMarina', 'Boatyard Trader', 'VendorContainerGunRunnerHQ',
            "Boatyard. You're not crew. So you're buying.")]
TRADER_FROM = 'FOLabPirateDockhand'          # (the look and gear of the marina's own dockhands)
TOLL_FIGHTERS_R = 3000.0
WORDS = {
    'deal': "Let's deal.", 'trade': "Let's trade.",
    'deal_yes': "[SUCCEEDED] Huh. You talk like a captain. Fine. Show me what you've got.",
    'deal_no': "[FAILED] I don't deal with strays. Come back when you can talk.",
    'trade_yes': "Show me.",
    'guest': "I'm the Kahuna's guest.", 'pay': "Pay the toll. (1 Stimpak)",
    'guest_yes': "[SUCCEEDED] ...Go on, then. Give the court my regards.",
    'guest_no': "[FAILED] Everyone's the Kahuna's guest. Toll's a stimpak.",
    'paid': "Toll paid. Go on.",
    'toll_hello': "Toll post. The road to Waikiki is the Kahuna's road.",
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _game(gd, edid, tag):
    from castawayquest import _game_form
    return _game_form(gd, edid, tag)


def _ed(gd, pr, base):
    if base.startswith('+'):
        return recordio.field(pr.records[base], 'EDID') if base in pr.records else ''
    try:
        return gd.edid(gd.from_key(base)) or ''
    except (KeyError, ValueError):
        return ''


def plan(gd, pr):
    import factionfolk as ff
    import robots
    import waikikilife as WL
    mk = ff._markers(pr)
    hotel = ff._refs_of(pr, ff._mod_key(pr, KAHALA, 'STAT'))
    rows, skipped = [], []
    if not hotel or MARINA not in mk:
        return {'rows': [], 'skipped': [('all', 'no Kahala Reef hotel or Koko Marina marker')]}
    hx, hy = hotel[0][1][:2]
    mx, my = mk[MARINA][1][:2]
    world = gd.ext_cells[gd.from_key(hotel[0][0])]
    # pirates who change sides at the two places
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in (c.get('refs') or {}).items():
            b = r.get('base', '')
            if r.get('removed') or not r.get('p') or not b.startswith('+') or (pr.records.get(b) or {}).get('type') != 'NPC_':
                continue
            if 'Pirate' not in _ed(gd, pr, b):
                continue
            where = 'kahala' if math.hypot(r['p'][0] - hx, r['p'][1] - hy) < KAHALA_R else \
                'marina' if math.hypot(r['p'][0] - mx, r['p'][1] - my) < MARINA_R else None
            if where:
                rows.append({'what': 'deal', 'at': where, 'cell': ck, 'ref': rk, 'base': b, 'edid': _ed(gd, pr, b)})
    # where the traders stand: by the trade ground's tables, by the marina's marker
    tables = [p for _ck, p in ff._refs_of(pr, gd.key(_game(gd, TRADE_PIECE, 'STAT')))
              if math.hypot(p[0] - hx, p[1] - hy) < KAHALA_R + 2000]
    tx, ty = (sum(p[0] for p in tables) / len(tables), sum(p[1] for p in tables) / len(tables)) if tables else (hx, hy)
    sp = WL.Spots(gd, pr, world)
    sp.taken = ff._standing(gd, pr)
    sp.gd, sp.pr, sp.grid = gd, pr, gd.grid(world)
    doors = robots._outside_doors(gd, pr, sp.grid, {'k': (tx, ty), 'm': (mx, my)})
    for key, edid, name, chest, hello in TRADERS:
        x0, y0 = (tx, ty) if key == 'kahala' else (mx, my)
        got = [s for s in ff._near(sp, x0, y0, 6, radii=(200, 350, 500, 700, 900, 1200), turns=16)
               if min((math.hypot(s[0] - d[0], s[1] - d[1]) for d in doors), default=1e9) >= robots.DOOR_CLEAR]
        if not got:
            skipped.append((key, 'no open spot on a navmesh'))
            continue
        x, y, z, rz = got[0]
        rows.append({'what': 'trader', 'at': key, 'p': (round(x, 1), round(y, 1), round(z + 4, 1), round(rz + math.pi, 4)),
                     'from_ground': round(math.hypot(x - x0, y - y0)),
                     'door': round(min((math.hypot(x - d[0], y - d[1]) for d in doors), default=1e9))})
    # the toll post's fighters (factionfolk's, each a record of its own)
    sec = ff._toll_section(gd, pr)
    fighters = set()
    if sec:
        for ck, c in pr.cells.items():
            if ck.startswith('+'):
                continue
            for rk, r in (c.get('refs') or {}).items():
                b = r.get('base', '')
                if b.startswith('+') and 'CourtFighter' in _ed(gd, pr, b) and r.get('p') and \
                        math.hypot(r['p'][0] - sec[0], r['p'][1] - sec[1]) < TOLL_FIGHTERS_R:
                    fighters.add(b)
    rows.append({'what': 'toll', 'fighters': sorted(fighters)})
    if not fighters:
        skipped.append(('toll', 'no court fighters by the toll post'))
    return {'rows': rows, 'skipped': skipped, 'world': gd.key(world)}


def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _rep_record(gd, edid, name, like):
    rec = recordio.load(gd, _game(gd, like, 'REPU'))
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', name)
    return rec


def _trader_faction(gd):
    import factionfolk as ff
    rec = ff._faction(gd, *FACTION)
    rel = {'tag': 'XNAM', 'label': 'Relation', 'kind': 'struct', 'fields': [
        {'name': 'Faction', 'code': 'F', 'value': gd.key(_game(gd, FIENDS, 'FACT'))}, {'name': 'Modifier', 'code': 'i', 'value': 0},
        {'name': 'Group combat reaction', 'code': 'I', 'value': 2}]}            # (allies: neither side fights the other)
    rec['subs'].insert(2, rel)
    return rec


def _dealing(gd, pr, base, faction):
    """A pirate's record copied into the traders' faction: its own faction list (not its template's), helping nobody."""
    import api_characters as ac
    import factionfolk as ff
    rec = recordio.load(gd, gd.from_key(base)) if not base.startswith('+') else __import__('json').loads(__import__('json').dumps(pr.records[base]))
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', _ed(gd, pr, base) + 'Deals', label='Editor ID')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SNAM']
    ff._set_num(rec, 'ACBS', 'Template flags', ff._num(rec, 'ACBS', 'Template flags') & ~0x04)    # (not the template's factions)
    ac.insert(rec, ff._set_link(ff._sub('NPC_', 'SNAM', __import__('struct').pack('<IB3s', 0, 0, b'\0\0\0')), faction))
    ff._set_num(rec, 'AIDT', 'Assistance', 0)
    ff._set_num(rec, 'AIDT', 'Aggression', min(1, ff._num(rec, 'AIDT', 'Aggression')))
    return rec


def ops(gd, pr, P=None):
    import json
    import api_characters as ac
    import api_quests as aq
    import api_scripts
    import questrec as qr
    import scriptc
    import waikikilife as WL
    from activity import _new_key
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    P = P or plan(gd, pr)
    grid = gd.grid(gd.from_key(P['world'])) if P.get('world') else None
    cell = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    rep = {'made': [], 'swapped': {}, 'traders': {}, 'toll': [], 'skipped': P['skipped'], 'reputations': {}}
    out = []

    def record(rec):
        k = _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k
    reps = {k: record(_rep_record(gd, e, n, like)) for k, (e, n, like) in REPS.items()}
    rep['reputations'] = {k: REPS[k][0] for k in reps}
    fac = record(_trader_faction(gd))
    # the pirates at the two places
    copies = {}
    for r in P['rows']:
        if r['what'] == 'deal':
            if r['base'] not in copies:
                copies[r['base']] = record(_dealing(gd, pr, r['base'], fac))
            out.append({'op': 'swap', 'cell': r['cell'], 'ref': r['ref'], 'base': copies[r['base']]})
            rep['swapped'][r['edid']] = rep['swapped'].get(r['edid'], 0) + 1
    # the traders and their chests
    services = ac.num(recordio.load(gd, _game(gd, WL.SERVICES_FROM, 'NPC_')), 'AIDT', 'Services')
    traders = {}
    stay = gd.key(ac._find(gd, 'PACK', WL.STAY))
    from_key = _mod_key(pr, TRADER_FROM, 'NPC_')
    for key, edid, name, chest, hello in TRADERS:
        row = next((r for r in P['rows'] if r['what'] == 'trader' and r['at'] == key), None)
        if not row or not from_key:
            continue
        npc = _dealing(gd, pr, from_key, fac)
        recordio.set_field(npc, 'EDID', edid, label='Editor ID')
        recordio.set_field(npc, 'FULL', name)
        npc['subs'] = [s for s in npc['subs'] if s['tag'] != 'PKID']
        ac.insert(npc, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': stay})
        ac.set_num(npc, 'AIDT', 'Services', services)
        ac.set_num(npc, 'ACBS', 'Barter gold', WL.BARTER_GOLD)
        nk = record(npc)
        crec = recordio.load(gd, _game(gd, chest, 'CONT'))
        recordio.set_field(crec, 'EDID', edid + 'Chest', label='Editor ID')
        crec['src'] = ''
        ckey = record(crec)
        x, y, z, rz = row['p']
        chest_ref = _new_key(pr)
        out.append({'op': 'place', 'cell': cell(x, y), 'key': chest_ref, 'ref': {'base': ckey, 'p': [x, y, z - 400, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True}})
        out.append({'op': 'place', 'cell': cell(x, y), 'key': _new_key(pr), 'ref': {'base': nk, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0,
                                                                                     'persistent': True, 'merchant': chest_ref}})
        traders[key] = (nk, hello)
        rep['traders'][key] = {'p': row['p'], 'from_ground': row['from_ground'], 'door': row['door']}
    fighters = next((r['fighters'] for r in P['rows'] if r['what'] == 'toll'), [])
    rep['toll'] = fighters
    # the quest, its script, the topics
    quest_key, script_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': script_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 55, 'delay': 5.0, 'stages': [], 'objectives': []})
    src = '\n'.join(['scn %s' % SCRIPT, 'short dealkahala', 'short dealmarina', 'short tolled', 'short tollday', '',
                     'Begin GameMode', '\tif tolled && GameDaysPassed > tollday', '\t\tset tolled to 0', '\tendif', 'End', ''])
    sc = api_scripts.scripts()
    c = sc.compile(src, script_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the deals\' script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    out.append({'op': 'record', 'key': script_key, 'record': srec})
    out.append({'op': 'record', 'key': quest_key, 'record': quest})
    index, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            index[sub['value'].lower()] = last
    topics = {}
    for k in ('deal', 'trade', 'guest', 'pay'):
        topics[k] = _new_key(pr)
        out.append({'op': 'record', 'key': topics[k], 'record': qr.topic_record({
            'edid': 'FOLabPirateDeals%s' % k.capitalize(), 'name': WORDS[k], 'priority': 50.0, 'kind': 0,
            'flags': {'top_level': True}, 'quests': [{'quest': quest_key, 'links': []}]})})
    rep['keys'] = {'quest': quest_key, 'script': script_key, 'topics': topics, 'reputations': reps, 'faction': fac}
    # the lines (compiled once the records above are in the mod: build() does it in a second, merged apply)
    speech = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == 'AVSpeech'))
    greeting = gd.key(_game(gd, 'GREETING', 'DIAL'))
    lines = []
    # (no line here says goodbye: a closing line's script may not run, as Waikiki's "Let's trade." taught, 23 Nov)

    def line(topic, who, words, conds=(), end='', skill=False, bye=False):
        l = aq.new_line_plain(gd, pr, topic, quest_key, who, words, goodbye=bye, conditions=list(conds))
        if skill:
            l['skill'] = speech
        if end:
            l['end'] = {'source': end, 'parts': None}
        lines.append(l)
    for key, (nk, hello) in traders.items():
        v = 'deal' + key
        line(greeting, nk, hello)
        line(topics['deal'], nk, WORDS['deal_yes'], [_cond(79, '=', 0, quest_key, index[v]), _cond(14, '>=', DEAL_SPEECH, 43, 0, 1)],
             'ShowBarterMenu\nset %s.%s to 1\nAddReputation %s 1 1' % (QUEST, v, REPS['pirates'][0]), skill=True)
        line(topics['deal'], nk, WORDS['deal_no'], [_cond(79, '=', 0, quest_key, index[v]), _cond(14, '<', DEAL_SPEECH, 43, 0, 1)], skill=True)
        line(topics['trade'], nk, WORDS['trade_yes'], [_cond(79, '=', 1, quest_key, index[v])], 'ShowBarterMenu')
    for fk in fighters:
        line(greeting, fk, WORDS['toll_hello'])
        line(topics['guest'], fk, WORDS['guest_yes'], [_cond(79, '=', 0, quest_key, index['tolled']), _cond(14, '>=', TOLL_SPEECH, 43, 0, 1)],
             'set %s.tolled to 1\nset %s.tollday to GameDaysPassed\nAddReputation %s 1 1' % (QUEST, QUEST, REPS['court'][0]), skill=True)
        line(topics['guest'], fk, WORDS['guest_no'], [_cond(79, '=', 0, quest_key, index['tolled']), _cond(14, '<', TOLL_SPEECH, 43, 0, 1)], skill=True)
        line(topics['pay'], fk, WORDS['paid'], [_cond(79, '=', 0, quest_key, index['tolled']),
                                               _cond(47, '>=', 1, gd.key(_game(gd, 'Stimpak', 'ALCH')), 0, 1)],
             'player.RemoveItem Stimpak 1\nset %s.tolled to 1\nset %s.tollday to GameDaysPassed' % (QUEST, QUEST))
    rep['lines'] = len(lines)
    return out, rep, lines


def line_ops(gd, pr, lines):
    import api_quests as aq
    return [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines]


def apply(pr, gd, P=None):
    """Both parts as one Undo: the records and places, then the lines compiled against them."""
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, line_ops(gd, pr, lines), merge=True)
    return rep
