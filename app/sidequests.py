"""Waikiki's first side quests (the user's pick, 21 Nov 2026: "Doctor and Makapu'u"; docs/waikiki-quests-next.md).

Both are one shape: someone asks you for something, you do it, you come back to them, they give you something.
- **The Doctor's Stock** (`DOCTOR`): Waikiki's doctor (waikikilife's storekeeper; her ref is given an editor ID here) buys
  her stimpaks through the Kahuna's men and would rather not. A trunk of medical supplies lies by the coast road between
  Kuliouou and the Kahala; bring them to her. Reward: five stimpaks and two goes of the first aid box's healing list.
- **Through Makapu'u Gate** (`GATE`): the settlers' guard at Makapu'u Gate stops outsiders; the Pip-Boy (their "mandate of
  heaven") gets you leave to walk their road of gates as far as the ship and back. Come back and he gives you a guest's
  gift (FOLab's dao), and says it doesn't make you one of them. A guard of the quest's own in the Lamellar Armor.

How it moves (docs/waikiki-quest-recipe.md): no line carries a script. The quest's own script starts each talk
(StartConversation when you come near, asked again if it doesn't come), hears it was shown (MenuMode 1009), watches for
the item in your pack (GetItemCount) or you at the place (GetDistance to a marker of its own), shows and completes the
objectives and gives the reward. Silent lines; no caps. Each quest is one Undo: `ops(gd, pr, spec, where)` changes
nothing, `spots(gd, pr, spec)` finds where things go in Waikiki, `build(server, spec)` applies it."""
import json
import math

import api_quests as aq
import questrec as qr
import recordio
from castawayquest import _game_form, _named, _ref_by_edid
from kuliouquest import _person

MARKER_BASE = 'XMarkerHeading'
ASK_NEAR, BACK_NEAR, GOAL_NEAR = 300, 300, 700      # (units: the giver talks this near; you've got there this near)
RETRY, TRIES = 6, 3                                 # (seconds of play a talk has to come; tries before waiting for you to come back)
FAR = 1500                                          # (gone this far, the tries start again)

DOCTOR = {
    'quest': 'FOLabDoctorsStock', 'name': "The Doctor's Stock", 'script': 'FOLabDoctorsStockScript',
    'topics': {'ask': 'FOLabDoctor1Ask', 'back': 'FOLabDoctor2Back'},
    'giver_npc': 'FOLabWaikikiDoctor', 'giver_ref': 'FOLabWaikikiDoctorREF',
    'item': ('FOLabMedicalSupplies', 'Medical Supplies', 'VMS16bMedicalSupplies'),
    'box': ('FOLabSupplyTrunk', 'Supply Trunk', 'VLootTrunkGen01'), 'box_ref': 'FOLabSupplyTrunkREF',
    'between': ("Kuliouou Squatters' Camp", 'Kahala Reef'),      # (map markers: the trunk by the road halfway)
    'reward': [('Stimpak', 5), ('LootChemsNVHealing75', 2)],     # (sure stimpaks, then the first aid box's healing list)
    'words': {
        'ask': "You're new. Listen. Every stimpak I sell comes to me through the Kahuna's men, and I'd rather not need them. "
               "A trunk of medical supplies washed up by the coast road, between Kuliouou and the Kahala. Bring them to me "
               "and I'll make it worth your while.",
        'back': "That's them. Good: that's a few less I have to buy. Here, from my own stock, for your trouble.",
    },
    'stages': [
        (10, "Waikiki's doctor buys her stimpaks through the Kahuna's men and would rather not. A trunk of medical supplies "
             "washed up by the coast road between Kuliouou and the Kahala: she wants them brought to her.", False),
        (20, "I found the medical supplies in the trunk by the coast road.", False),
        (100, "I brought the medical supplies to Waikiki's doctor. She paid me from her own stock.", True),
    ],
    'objectives': [(10, "Find the supply trunk by the coast road", 'box'),
                   (20, "Bring the medical supplies to the doctor", 'giver')],
}

GATE = {
    'quest': 'FOLabMakapuuGate', 'name': "Through Makapu'u Gate", 'script': 'FOLabMakapuuGateScript',
    'topics': {'ask': 'FOLabGate1Ask', 'back': 'FOLabGate2Back'},
    'guard': ('FOLabMakapuuGuard', 'Gate Guard', 'NVProspectorMale'), 'giver_ref': 'FOLabMakapuuGuardREF',
    'wears': ['FOLabHuangLamellar', 'FOLabWeapDao'],
    'gate': ('settler_gate_3', (123180.0, 30000.0)),     # (settlers.py: Makapu'u Gate's piece, near MAKAPUU)
    'goal': ('settler_gate_5', 'FOLabMakapuuGoal'),      # (the last and grandest gate, by the ship's ramp)
    'reward': [('FOLabWeapDao', 1)],
    'words': {
        'ask': "Stop there. Outsiders don't come through this gate, only trade, and you carry none. ... That on your wrist. "
               "Then you're no common stranger. You may walk our road as far as the ship, and back. Touch nothing, take "
               "nothing, and don't stay.",
        'back': "You walked our road and touched nothing. Good. A guest doesn't leave with empty hands: take this. "
                "Don't think it makes you one of us.",
    },
    'stages': [
        (10, "The settlers' guard at Makapu'u Gate stopped me. The Pip-Boy on my wrist got me leave to walk their road of "
             "gates as far as their ship, and back.", False),
        (20, "I walked the settlers' road of gates to their ship.", False),
        (100, "I came back through Makapu'u Gate. The guard gave me a guest's gift, and said it doesn't make me one of them.", True),
    ],
    'objectives': [(10, "Walk the settlers' road of gates to their ship", 'goal'),
                   (20, "Go back to the guard at Makapu'u Gate", 'giver')],
}

SPECS = {'doctor': DOCTOR, 'gate': GATE}


def key_order(spec):
    if 'item' in spec:
        return ['item', 'box', 'script', 'quest', 'ask', 'back', 'box_ref']
    return ['guard', 'script', 'quest', 'ask', 'back', 'giver_ref', 'goal_ref']


def script_source(spec, reward):
    """`state`: 0 waiting for you to come near the giver, 2 doing it, 3 back to the giver, 9 done. `asked` a talk asked
    for, `talked` it was shown (set in MenuMode)."""
    q, giver, t = spec['quest'], spec['giver_ref'], spec['topics']
    item = spec['item'][0] if 'item' in spec else None
    got = 'player.GetItemCount %s > 0' % item if item else 'player.GetDistance %s < %d' % (spec['goal'][1], GOAL_NEAR)
    o = lambda n: 'SetObjectiveDisplayed %s %d 1' % (q, n)
    done = lambda n: 'SetObjectiveCompleted %s %d 1' % (q, n)

    def talk(topic, near, then):
        return ['\t\tif asked == 1 && talked == 1'] + ['\t\t\t' + x for x in then] + [
            '\t\telseif asked == 1',
            '\t\t\tset since to since + GetSecondsPassed',
            '\t\t\tif since > %d' % RETRY,
            '\t\t\t\tset asked to 0',
            '\t\t\tendif',
            '\t\telseif player.GetDistance %s > %d' % (giver, FAR),
            '\t\t\tset tries to 0',
            '\t\telseif tries < %d && %s' % (TRIES, near),
            '\t\t\tset asked to 1',
            '\t\t\tset talked to 0',
            '\t\t\tset since to 0',
            '\t\t\tset tries to tries + 1',
            '\t\t\t%s.StartConversation PlayerREF %s' % (giver, topic),
            '\t\tendif']

    L = ['scn ' + spec['script'], '',
         "; Made by FOLab (sidequests.py): a side quest of Waikiki's. See its notes.",
         'short state', 'short asked', 'short talked', 'short tries', 'float since', '',
         'begin GameMode', '',
         '\tif state == 9',
         '\t\treturn',
         '\tendif',
         '\tif %s.GetDead' % giver,
         '\t\tset state to 9\t; (nobody left to ask or come back to)',
         '\t\treturn',
         '\tendif',
         '\tif state == 0']
    L += talk(t['ask'], 'player.GetDistance %s < %d' % (giver, ASK_NEAR),
              ['SetStage %s 10' % q, o(10), 'set state to 2', 'set asked to 0', 'set tries to 0'])
    L += ['\tendif', '',
          '\tif state == 2 && ' + got,
          '\t\tSetStage %s 20' % q,
          '\t\t' + done(10),
          '\t\t' + o(20),
          '\t\tset state to 3',
          '\t\treturn',
          '\tendif', '',
          '\tif state == 3']
    near = 'player.GetDistance %s < %d' % (giver, BACK_NEAR) + (' && player.GetItemCount %s > 0' % item if item else '')
    then = (['player.RemoveItem %s 1 1' % item] if item else []) + ['player.AddItem %s %d' % (e, n) for e, n in reward] + \
        [done(20), 'SetStage %s 100' % q, 'set state to 9', 'CompleteQuest %s' % q]
    L += talk(t['back'], near, then)
    L += ['\tendif', '', 'end', '',
          'begin MenuMode', '',
          '\tif MenuMode 1009 && asked == 1\t; (the dialogue: the talk asked for is on screen)',
          '\t\tset talked to 1',
          '\tendif', '', 'end', '']
    return '\r\n'.join(L)


def _marker(pr, name):
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if (r.get('marker') or {}).get('name') == name and not r.get('removed'):
                return r['p'], ck
    raise ValueError('no map marker %r' % name)


def _own_stat(pr, piece):
    """The key of the mod's own STAT made from a modelsets piece (its editor ID ends with the piece's name, any case)."""
    want = piece.replace('_', '').lower()
    for k, r in pr.records.items():
        if r.get('type') == 'STAT' and (recordio.field(r, 'EDID') or '').lower().replace('_', '').endswith(want):
            return k
    raise ValueError('the mod has no piece %s' % piece)


def _refs_of(pr, base):
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if r.get('base') == base and r.get('p') and not r.get('removed'):
                yield ck, rk, r['p']


def spots(gd, pr, spec):
    """Where the quest's things go in Waikiki."""
    import waikikilife as wl
    grid_of = lambda world: gd.grid(world)
    cell_at = lambda world, x, y: gd.key(grid_of(world)[(int(x // 4096), int(y // 4096))])
    if 'item' in spec:
        npc = next((k for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'EDID') == spec['giver_npc']), None)
        if npc is None:
            raise ValueError('the mod has no %s: waikikilife.build first' % spec['giver_npc'])
        found = list(_refs_of(pr, npc))
        if not found:
            raise ValueError('%s is not placed' % spec['giver_npc'])
        gcell, gref, _gp = found[0]
        (a, acell), (b, _bc) = _marker(pr, spec['between'][0]), _marker(pr, spec['between'][1])
        world = gd.ext_cells[gd.from_key(acell)]
        # (the road from the start to Waikiki, as waikikilife finds it; the trunk halfway between where it passes the two)
        sck, srk = _ref_by_edid(pr, wl.START_REF)
        if not srk:
            raise ValueError('no start (%s)' % wl.START_REF)
        hot, mid = wl.middle(pr)
        road = wl.Way(wl.way(gd, pr, pr.cells[sck]['refs'][srk]['p'][:2], hot.get('royal_hawaiian', mid)))
        sp = wl.Spots(gd, pr, world)
        nearest = lambda q: min(range(len(road.pts)), key=lambda i: math.hypot(road.pts[i][0] - q[0], road.pts[i][1] - q[1]))
        n = (nearest(a) + nearest(b)) // 2
        x, y = road.pts[n]
        (x0, y0), (x1, y1) = road.pts[max(0, n - 1)], road.pts[min(len(road.pts) - 1, n + 1)]
        d = math.hypot(x1 - x0, y1 - y0) or 1.0
        px, py = -(y1 - y0) / d, (x1 - x0) / d
        for k in range(0, 40):                       # (beside the road, a little further along each try)
            m = min(len(road.pts) - 1, n + k // 6)
            x, y = road.pts[m]
            side = (1, -1, 1.5, -1.5, 2, -2)[k % 6]
            bx, by = x + px * 350 * side, y + py * 350 * side
            z = sp.stand(bx, by, apart=0)
            if z is not None:
                rz = math.atan2(x - bx, y - by)
                return {'world': world, 'giver': (gcell, gref), 'box': (cell_at(world, bx, by), [round(bx, 1), round(by, 1), round(z, 1), 0.0, 0.0, round(rz, 4)])}
        raise ValueError('no open ground by the road for the trunk')
    piece, near = spec['gate']
    gates = sorted(_refs_of(pr, _own_stat(pr, piece)), key=lambda t: math.hypot(t[2][0] - near[0], t[2][1] - near[1]))
    if not gates:
        raise ValueError("no Makapu'u Gate")
    gcell, _gr, gp = gates[0]
    world = gd.ext_cells[gd.from_key(gcell)]
    goals = sorted(_refs_of(pr, _own_stat(pr, spec['goal'][0])), key=lambda t: math.hypot(t[2][0] - gp[0], t[2][1] - gp[1]))
    if not goals:
        raise ValueError('no last gate by the ship')
    _c, _r, lp = goals[0]
    sp = wl.Spots(gd, pr, world)
    # (the guard on the gate's outer side, toward the coast road from Hanauma: the side away from the last gate)
    away = math.atan2(gp[0] - lp[0], gp[1] - lp[1])
    for r in (420, 520, 640, 780):
        for k in range(12):
            a = away + (k // 2 + 1) * 0.35 * (1 if k % 2 else -1) if k else away
            x, y = gp[0] + r * math.sin(a), gp[1] + r * math.cos(a)
            z = sp.stand(x, y, apart=0)
            if z is not None:
                rz = math.atan2(gp[0] - x, gp[1] - y) + math.pi    # (his back to the gate, facing whoever comes)
                return {'world': world, 'guard': (cell_at(world, x, y), [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)]),
                        'goal': (cell_at(world, lp[0], lp[1]), [round(lp[0], 1), round(lp[1], 1), round(lp[2], 1), 0.0, 0.0, 0.0])}
    raise ValueError("no ground to stand the guard on by Makapu'u Gate")


def _reward(gd, spec):
    if 'reward' in spec:
        return spec['reward']
    rec = recordio.load(gd, _game_form(gd, spec['reward_from'], 'CONT'))
    out = []
    for s in rec['subs']:
        if s['tag'] == 'CNTO':
            f = {x['name']: x['value'] for x in s['fields']}
            out.append((gd.edid(gd.from_key(f['Item'])), int(f['Count'])))     # (by editor ID: the script names them)
    return out


def _key_by_edid(pr, edid):
    k = next((k for k, r in pr.records.items() if recordio.field(r, 'EDID') == edid), None)
    if k is None:
        raise ValueError('the mod has no %s' % edid)
    return k


def _cnto(gd, item, count=1):
    """A CNTO in the game's own layout (copied from the duffle bag's, as castawayquest does), naming `item`."""
    duffle = recordio.load(gd, _game_form(gd, 'NVDuffleBagRandomLoot', 'CONT'))
    c = json.loads(json.dumps(next(s for s in duffle['subs'] if s['tag'] == 'CNTO')))
    for f in c['fields']:
        if f.get('name') == 'Item':
            f['value'] = item
        elif f.get('name') == 'Count':
            f['value'] = count
    return c


def _with_items(gd, npc, items):
    """An NPC_ carrying these (its own inventory, not the template's: 0x100 cleared)."""
    import api_characters as ac
    ac.set_num(npc, 'ACBS', 'Template flags', ac.num(npc, 'ACBS', 'Template flags') & ~0x100)
    at = max((i for i, s in enumerate(npc['subs']) if s['tag'] in ('CNTO', 'COED')), default=None)
    if at is None:
        at = next(i for i, s in enumerate(npc['subs']) if s['tag'] in ('AIDT', 'PKID', 'CNAM'))
        at -= 1
    for k in reversed(items):
        npc['subs'].insert(at + 1, _cnto(gd, k))
    return npc


def ops(gd, pr, spec, where):
    """(ops, report) for one quest, one Undo. Nothing is changed here."""
    import api_scripts
    import newgame
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == spec['quest'] for r in pr.records.values()):
        raise ValueError('the mod already has %s' % spec['quest'])
    order = key_order(spec)
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    reward = _reward(gd, spec)
    persistent = lambda edid: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]}
    topic = lambda edid: qr.topic_record({'edid': edid, 'name': '', 'priority': 50.0, 'kind': 0,
                                         'quests': [{'quest': keys['quest'], 'links': []}]})
    records, things, extra = [], [], {}
    if 'item' in spec:
        gcell, gref = where['giver']
        giver_ref, giver_npc = gref, pr.cells[gcell]['refs'][gref]['base']
        item = _named(recordio.load(gd, _game_form(gd, spec['item'][2], 'MISC')), spec['item'][0], spec['item'][1])
        box = _named(recordio.load(gd, _game_form(gd, spec['box'][2], 'CONT')), spec['box'][0], spec['box'][1])
        box['subs'] = [s for s in box['subs'] if s['tag'] not in ('CNTO', 'COED')]
        at = next(i for i, s in enumerate(box['subs']) if s['tag'] == 'DATA')
        box['subs'].insert(at, _cnto(gd, keys['item']))
        records += [item, box]
        extra.update({keys['item']: item, keys['box_ref']: persistent(spec['box_ref']), giver_ref: persistent(spec['giver_ref'])})
        target = {'box': keys['box_ref'], 'giver': giver_ref}
        bcell, bp = where['box']
        things.append({'op': 'add', 'cell': bcell, 'base': keys['box'], 'p': bp, 's': 1.0, 'extra': {'persistent': True, 'edid': spec['box_ref']}})
        named = [{'op': 'ref_set', 'cell': gcell, 'ref': gref, 'set': {'edid': spec['giver_ref']}}]
    else:
        e, n, tmpl = spec['guard']
        guard = _with_items(gd, _person(gd, pr, e, n, tmpl), [_key_by_edid(pr, w) for w in spec['wears']])
        records.append(guard)
        giver_ref, giver_npc = keys['giver_ref'], keys['guard']
        extra.update({keys['giver_ref']: persistent(spec['giver_ref']), keys['goal_ref']: persistent(spec['goal'][1])})
        target = {'goal': keys['goal_ref'], 'giver': keys['giver_ref']}
        for w, _c in reward:
            _key_by_edid(pr, w)                      # (the mod has it: the script names it by editor ID)
        gcell, gp = where['guard']
        lcell, lp = where['goal']
        things += [{'op': 'add', 'cell': gcell, 'base': keys['guard'], 'p': gp, 's': 1.0, 'extra': {'persistent': True, 'edid': spec['giver_ref']}},
                   {'op': 'add', 'cell': lcell, 'base': gd.key(_game_form(gd, MARKER_BASE, 'STAT')), 'p': lp, 's': 1.0,
                    'extra': {'persistent': True, 'edid': spec['goal'][1]}}]
        named = []
    quest = qr.quest_record({'edid': spec['quest'], 'script': keys['script'], 'name': spec['name'], 'flags': {'start_enabled': True},
                             'priority': 50, 'delay': 0.5,
                             'stages': [{'index': n, 'entries': [{'flags': {'complete': fin}, 'conditions': [], 'log': log, 'next': ''}]}
                                        for n, log, fin in spec['stages']],
                             'objectives': [{'index': n, 'text': text, 'targets': [{'target': target[t], 'flags': 0, 'conditions': []}]}
                                            for n, text, t in spec['objectives']]})
    topics = {k: topic(spec['topics'][k]) for k in ('ask', 'back')}
    extra.update({keys['quest']: quest, keys['ask']: topics['ask'], keys['back']: topics['back']})
    sc = api_scripts.scripts()
    c = sc.compile(script_source(spec, reward), keys['script'], 'quest', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the quest script does not compile: %s' % (c,))
    script = sc._record_of(c, spec['script'])
    out = [{'op': 'record_new', 'record': r} for r in records]
    out += [{'op': 'record_new', 'record': script}, {'op': 'record_new', 'record': quest},
            {'op': 'record_new', 'record': topics['ask']}, {'op': 'record_new', 'record': topics['back']}]
    out += things + named
    lines = [aq.new_line_plain(gd, pr, keys[k], keys['quest'], giver_npc, spec['words'][k], goodbye=True) for k in ('ask', 'back')]
    out += [{'op': 'record_new', 'record': qr.info_record(dict(l, begin=None, end=None))} for l in lines]
    return out, {'keys': keys, 'reward': reward, 'lines': len(lines), 'spots': {k: v for k, v in where.items() if k != 'world'}}


def build(server, spec):
    """One quest put into the open mod as one Undo. Returns the report."""
    if isinstance(spec, str):
        spec = SPECS[spec]
    gd, pr = server.GD, server.PR
    where = spots(gd, pr, spec)
    o, rep = ops(gd, pr, spec, where)
    made = server.edit("Waikiki's side quest: " + spec['name'], o)['made']
    want = [rep['keys'][k] for k in key_order(spec)]
    assert made[:len(want)] == want, ('keys not as reserved', made[:len(want)], want)
    return rep
