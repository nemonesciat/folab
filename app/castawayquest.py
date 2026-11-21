"""Waikiki's first quest, "What the Sea Brought In" (the user's yes, 20 Nov 2026; docs/waikiki-story-plan.md, the main quest's
step 2, "Someone wanted you drowned", and the coast road from Hanauma in "The first place on the way").

Once the opening on the beach is over (castawaytalk.py), the beachcomber has one more thing: the captain's trunk is still out
on the wreck on the reef. You swim out (the wreck lies all but under the water, the trunk on her highest point), take the
captain's lockbox out of it and see her planking split outward under it: she was cut open from the inside. You bring the
lockbox back; he gives you your half (the game's own levelled duffle-bag lists, the loot work's easy band for bags), hears
how she lies, and sends you up the coast road, past the pirates' marina, to Kuliouou. Done when you get there.

How it moves (what the opening taught, 19 Nov 2026: the lines' own result scripts never took effect in the game): nothing
hangs on a line's script. The quest's own script does every step: it waits for the opening's `step` to be 9, starts each
talk (StartConversation, asked again if it doesn't come), hears it was shown (MenuMode 1009) and acts once it shuts; it sees
the lockbox in your pack (GetItemCount) and you near the camp at Kuliouou (GetDistance to a marker of the quest's own).
Stages carry the log entries only; objectives are shown and completed by the script. All lines silent (TRDT sound 0, the
words in NAM1). Voice files would go under sound\\voice\\Waikiki.esp\\<voice type>\\ named by topic and line, with a .lip
beside each: none made (docs/waikiki-quest-recipe.md).

Made here, all in one Undo: the lockbox (MISC, the Lunchbox's model), the captain's trunk (CONT, the game's empty trunk with
the lockbox in it) stood on the wreck, a message box, a marker at Kuliouou, the quest with its stages, objectives and
targets, its script, three topics and their lines. `ops(gd, pr, spots)` returns (ops, report) without changing anything;
`spots(gd, pr)` finds where things go in Waikiki; `build(server)` applies it."""
import json
import math

import api_quests as aq
import questrec as qr
import recordio
import tes4

QUEST = 'FOLabSeaBroughtIn'
QUEST_NAME = 'What the Sea Brought In'
SCRIPT = 'FOLabSeaBroughtInScript'
LOCKBOX, LOCKBOX_NAME, LOCKBOX_FROM = 'FOLabCaptainsLockbox', "Captain's Lockbox", 'Lunchbox'
TRUNK, TRUNK_NAME, TRUNK_FROM = 'FOLabCaptainsTrunk', "Captain's Trunk", 'VLootTrunkGen01'
TRUNK_REF = 'FOLabCaptainsTrunkREF'
MESSAGE = 'FOLabSeaCutMessage'
ARRIVE = 'FOLabKuliououArrive'
OPENING = 'FOLabCastawayOpening'            # (castawaytalk.QUEST: its `step` is 9 once the opening is over, every way)
COMBER_REF = 'FOLabBeachcomberREF'
MARKER_BASE = 'XMarkerHeading'
KULIOUOU = "Kuliouou Squatters' Camp"       # (the map marker the walk ends at)
WRECK = 'Boat02a'
REEF = (99300.0, -37600.0)                  # (castaway.REEF: where the wreck lies)
REWARD = [('LootDuffleBag100', 1), ('LootDuffleBag25', 3)]     # (the game's duffle bag's own lists: lootplace's 'bag', easy band)

WORDS = {
    'ask': "One more thing. The captain's trunk is still out on the wreck. You came off her, you can swim out to her. "
           "Bring me what's in it and we'll split it.",
    'back': "That's his lockbox. Hand it here. So. How's she lying out there?",
    'cut_prompt': "Her hull's cut open. From the inside.",
    'cut': "Then she didn't sink. She was sunk, with all of you chained in her. Here's your half. You want to know who, "
           "go where people talk. Up the road, past the marina. Keep clear of the boats there. Kuliouou.",
    'message': "Under the trunk the planking is split open, the splinters bent outward. Someone cut her open from the inside.",
}
TOPICS = {'ask': 'FOLabSea1Ask', 'back': 'FOLabSea2Back', 'cut': 'FOLabSea2Cut'}
STAGES = [
    (10, "A beachcomber woke me on the sand at Hanauma Bay. The captain's trunk is still out on the wreck on the reef: if I "
         "swim out and bring back what's in it, we split it.", False),
    (20, "In the captain's trunk on the wreck was his lockbox. Under the trunk her planking was split open, the splinters bent "
         "outward: someone cut her open from the inside.", False),
    (30, "The beachcomber gave me my half. The boat didn't sink: she was sunk, with all of us chained in her. If I want to know "
         "who, he says to go where people talk: Kuliouou, up the coast road past the marina.", False),
    (100, "I followed the coast road to Kuliouou.", True),
]
OBJECTIVES = [(10, "Swim out to the wreck and find the captain's trunk", 'trunk'),
              (20, "Bring the captain's lockbox to the beachcomber", 'comber'),
              (30, "Follow the coast road to Kuliouou", 'arrive')]
NEAR_COMBER, ASK_NEAR, ARRIVED = 300, 600, 2000     # (units: he talks when you're this near; you've arrived this near the camp)
RETRY, TRIES = 6, 3                                 # (seconds of play a talk has to come; tries at the ask before going on)


def script_source():
    """The quest's own script. `state`: 0 waiting for the opening, 1 the ask, 2 out to the wreck, 3 back to the beachcomber,
    4 on the road, 9 done. `asked` a talk asked for, `talked` it was shown (set in MenuMode)."""
    o = lambda n: 'SetObjectiveDisplayed %s %d 1' % (QUEST, n)
    done = lambda n: 'SetObjectiveCompleted %s %d 1' % (QUEST, n)
    L = ['scn ' + SCRIPT, '',
         "; Made by FOLab (castawayquest.py): Waikiki's first quest. See its notes.",
         'short state', 'short asked', 'short talked', 'short tries', 'short told', 'float pause', 'float since', '',
         'begin GameMode', '',
         '\tif state == 9',
         '\t\treturn',
         '\tendif',
         '\tif state == 0',
         '\t\tif %s.step != 9\t; (the opening on the beach not over yet)' % OPENING,
         '\t\t\treturn',
         '\t\tendif',
         '\t\tSetStage %s 10' % QUEST,
         '\t\t' + o(10),
         '\t\tset state to 1',
         '\t\tset pause to 1.5',
         '\tendif',
         '\tif pause > 0',
         '\t\tset pause to pause - GetSecondsPassed',
         '\t\treturn',
         '\tendif',
         '',
         # (the ask: once the opening's last line has shut, if you're still by him; a few tries, then on without it)
         '\tif state == 1',
         '\t\tif asked == 1 && talked == 1',
         '\t\t\tset state to 2',
         '\t\telseif asked == 1',
         '\t\t\tset since to since + GetSecondsPassed',
         '\t\t\tif since > %d' % RETRY,
         '\t\t\t\tset asked to 0',
         '\t\t\tendif',
         '\t\telseif tries >= %d || player.GetDistance %s > %d' % (TRIES, COMBER_REF, ASK_NEAR),
         '\t\t\tset state to 2',
         '\t\telse',
         '\t\t\tset asked to 1',
         '\t\t\tset talked to 0',
         '\t\t\tset since to 0',
         '\t\t\tset tries to tries + 1',
         '\t\t\t%s.StartConversation PlayerREF %s' % (COMBER_REF, TOPICS['ask']),
         '\t\tendif',
         '\tendif',
         '',
         # (the lockbox in your pack, however it got there: the trunk found)
         '\tif state >= 1 && state <= 2 && player.GetItemCount %s > 0' % LOCKBOX,
         '\t\tSetStage %s 20' % QUEST,
         '\t\t' + done(10),
         '\t\t' + o(20),
         '\t\tset state to 3',
         '\t\tset asked to 0',
         '\t\tset talked to 0',
         '\t\tif told == 0',
         '\t\t\tset told to 1',
         '\t\t\tShowMessage %s' % MESSAGE,
         '\t\tendif',
         '\t\treturn',
         '\tendif',
         '',
         # (back on the beach: he asks for it when you come up to him with it; once that talk has shut, your half)
         '\tif state == 3',
         '\t\tif asked == 1 && talked == 1',
         '\t\t\tplayer.RemoveItem %s 1 1' % LOCKBOX]
    L += ['\t\t\tplayer.AddItem %s %d' % (e, n) for e, n in REWARD]
    L += ['\t\t\tSetStage %s 30' % QUEST,
          '\t\t\t' + done(20),
          '\t\t\t' + o(30),
          '\t\t\tset state to 4',
          '\t\telseif asked == 1',
          '\t\t\tset since to since + GetSecondsPassed',
          '\t\t\tif since > %d' % RETRY,
          '\t\t\t\tset asked to 0',
          '\t\t\tendif',
          '\t\telseif player.GetDistance %s < %d && player.GetItemCount %s > 0' % (COMBER_REF, NEAR_COMBER, LOCKBOX),
          '\t\t\tset asked to 1',
          '\t\t\tset talked to 0',
          '\t\t\tset since to 0',
          '\t\t\t%s.StartConversation PlayerREF %s' % (COMBER_REF, TOPICS['back']),
          '\t\tendif',
          '\tendif',
          '',
          '\tif state == 4 && player.GetDistance %s < %d' % (ARRIVE, ARRIVED),
          '\t\t' + done(30),
          '\t\tSetStage %s 100' % QUEST,
          '\t\tset state to 9',
          '\t\tCompleteQuest %s' % QUEST,
          '\tendif',
          '', 'end', '',
          'begin MenuMode', '',
          '\tif MenuMode 1009 && asked == 1\t; (the dialogue: the talk asked for is on screen)',
          '\t\tset talked to 1',
          '\tendif', '', 'end', '']
    return '\r\n'.join(L)


def _game_form(gd, edid, tag):
    for f, (_i, r) in gd.forms.items():
        if r.tag == tag and (f >> 24) == 0 and tes4.zstr(gd.fields(f).get('EDID', b'')) == edid:
            return f
    for f, (_i, r) in gd.forms.items():
        if r.tag == tag and tes4.zstr(gd.fields(f).get('EDID', b'')) == edid:
            return f
    raise ValueError('the game has no %s %s' % (tag, edid))


def _named(rec, edid, name):
    rec = json.loads(json.dumps(rec))
    rec['src'] = ''
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = name
    return rec


def _ref_by_edid(pr, edid):
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if r.get('edid') == edid and not r.get('removed'):
                return ck, rk
    return None, None


def spots(gd, pr):
    """Where things go in Waikiki: {'trunk': (cell, p), 'arrive': (cell, p), 'comber': ref key, 'world': world form}."""
    import lootplace
    import townbuild
    cell, comber = _ref_by_edid(pr, COMBER_REF)
    if not comber:
        raise ValueError('the mod has no beachcomber (%s): castawaytalk.build first' % COMBER_REF)
    world = gd.ext_cells[gd.from_key(cell)]
    grid = gd.grid(world)
    wreck = gd.key(_game_form(gd, WRECK, 'STAT'))
    best = None
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            p = r.get('p')
            if r.get('base') == wreck and p and not r.get('removed'):
                d = math.hypot(p[0] - REEF[0], p[1] - REEF[1])
                if best is None or d < best[0]:
                    best = (d, p)
    if best is None or best[0] > 2000:
        raise ValueError('no wreck on the reef at Hanauma')
    wp = best[1]
    S = lootplace.Seat(gd, pr, world)
    S.load(wp[0], wp[1])
    box = townbuild.obnd(gd, gd.key(_game_form(gd, TRUNK_FROM, 'CONT')))
    # (the trunk on the wreck's highest point, turned with her: the spot whose footprint's lowest surface is highest)
    rz = wp[5]
    choice = None
    for dx in range(-320, 321, 16):
        for dy in range(-320, 321, 16):
            x, y = wp[0] + dx, wp[1] + dy
            under = []
            for fx in (-0.4, 0.0, 0.4):
                for fy in (-0.4, 0.0, 0.4):
                    lx, ly = fx * (box[3] - box[0]), fy * (box[4] - box[1])
                    px = x + lx * math.cos(rz) + ly * math.sin(rz)
                    py = y - lx * math.sin(rz) + ly * math.cos(rz)
                    tops = [z for z, ref in S.solids.tops(px, py) if z < 200]
                    under.append(max(tops) if tops else None)
            if None in under:
                continue
            score = min(under)
            if choice is None or score > choice[0]:
                choice = (score, x, y, max(under))
    if choice is None:
        raise ValueError('no room for the trunk on the wreck')
    _s, tx, ty, tz = choice
    tcell = gd.key(grid[(int(tx // 4096), int(ty // 4096))])
    mk = None
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if (r.get('marker') or {}).get('name') == KULIOUOU and not r.get('removed'):
                mk = r['p']
    if mk is None:
        raise ValueError('no map marker %r' % KULIOUOU)
    acell = gd.key(grid[(int(mk[0] // 4096), int(mk[1] // 4096))])
    return {'trunk': (tcell, [round(tx, 1), round(ty, 1), round(tz - 4.0, 1), 0.0, 0.0, round(rz, 4)]),
            'arrive': (acell, [mk[0], mk[1], mk[2], 0.0, 0.0, 0.0]), 'comber': comber, 'comber_cell': cell,
            'trunk_top_over_water': round(tz - 4.0 + box[5], 1), 'world': world}


def ops(gd, pr, where):
    """(ops, report): every record and thing of the quest, in one list for one Undo. Nothing is changed here."""
    import api_scripts
    import newgame
    if not any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == OPENING for r in pr.records.values()):
        raise ValueError('the mod has no opening (%s) for the quest to follow' % OPENING)
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        raise ValueError('the mod already has %s' % QUEST)
    comber_npc = pr.cells[where['comber_cell']]['refs'][where['comber']]['base']
    # the keys every record_new and add below will get, in this order
    order = ['lockbox', 'trunk', 'message', 'script', 'quest', 'ask', 'back', 'cut', 'trunk_ref', 'arrive_ref']
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    marker = gd.key(_game_form(gd, MARKER_BASE, 'STAT'))
    # the lockbox and the trunk it's in
    lockbox = _named(recordio.load(gd, _game_form(gd, LOCKBOX_FROM, 'MISC')), LOCKBOX, LOCKBOX_NAME)
    trunk = _named(recordio.load(gd, _game_form(gd, TRUNK_FROM, 'CONT')), TRUNK, TRUNK_NAME)
    duffle = recordio.load(gd, _game_form(gd, 'NVDuffleBagRandomLoot', 'CONT'))
    cnto = json.loads(json.dumps(next(s for s in duffle['subs'] if s['tag'] == 'CNTO')))
    for f in cnto['fields']:
        if f.get('name') == 'Item':
            f['value'] = keys['lockbox']
        elif f.get('name') == 'Count':
            f['value'] = 1
    trunk['subs'] = [s for s in trunk['subs'] if s['tag'] not in ('CNTO', 'COED')]
    at = next(i for i, s in enumerate(trunk['subs']) if s['tag'] == 'DATA')
    trunk['subs'].insert(at, cnto)
    message = newgame._message_record(MESSAGE, WORDS['message'])
    # the quest, its stages, objectives and their targets
    target = {'trunk': keys['trunk_ref'], 'comber': where['comber'], 'arrive': keys['arrive_ref']}
    quest = qr.quest_record({'edid': QUEST, 'script': keys['script'], 'name': QUEST_NAME, 'flags': {'start_enabled': True},
                             'priority': 55, 'delay': 0.5,
                             'stages': [{'index': n, 'entries': [{'flags': {'complete': fin}, 'conditions': [], 'log': log, 'next': ''}]}
                                        for n, log, fin in STAGES],
                             'objectives': [{'index': n, 'text': text, 'targets': [{'target': target[t], 'flags': 0, 'conditions': []}]}
                                            for n, text, t in OBJECTIVES]})
    topic = lambda edid, name: qr.topic_record({'edid': edid, 'name': name, 'priority': 50.0, 'kind': 0,
                                               'quests': [{'quest': keys['quest'], 'links': []}]})
    # the script, compiled against what these ops will make (named in `extra` until they exist)
    persistent = lambda edid: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]}
    extra = {keys['quest']: quest, keys['lockbox']: lockbox, keys['message']: message, keys['ask']: topic(TOPICS['ask'], ''),
             keys['back']: topic(TOPICS['back'], ''), keys['trunk_ref']: persistent(TRUNK_REF), keys['arrive_ref']: persistent(ARRIVE),
             where['comber']: persistent(COMBER_REF)}
    sc = api_scripts.scripts()
    c = sc.compile(script_source(), keys['script'], 'quest', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the quest script does not compile: %s' % (c,))
    script = sc._record_of(c, SCRIPT)
    # the lines: silent, said by the beachcomber
    ask = aq.new_line_plain(gd, pr, keys['ask'], keys['quest'], comber_npc, WORDS['ask'], goodbye=True)
    back = aq.new_line_plain(gd, pr, keys['back'], keys['quest'], comber_npc, WORDS['back'], goodbye=False)
    back['choices'] = [keys['cut']]
    cut = aq.new_line_plain(gd, pr, keys['cut'], keys['quest'], comber_npc, WORDS['cut'], goodbye=True)
    lines = [qr.info_record(dict(l, begin=None, end=None)) for l in (ask, back, cut)]
    out = [{'op': 'record_new', 'record': lockbox}, {'op': 'record_new', 'record': trunk}, {'op': 'record_new', 'record': message},
           {'op': 'record_new', 'record': script}, {'op': 'record_new', 'record': quest},
           {'op': 'record_new', 'record': topic(TOPICS['ask'], '')}, {'op': 'record_new', 'record': topic(TOPICS['back'], '')},
           {'op': 'record_new', 'record': topic(TOPICS['cut'], WORDS['cut_prompt'])}]
    tcell, tp = where['trunk']
    acell, ap = where['arrive']
    out.append({'op': 'add', 'cell': tcell, 'base': keys['trunk'], 'p': tp, 's': 1.0, 'extra': {'persistent': True, 'edid': TRUNK_REF}})
    out.append({'op': 'add', 'cell': acell, 'base': marker, 'p': ap, 's': 1.0, 'extra': {'persistent': True, 'edid': ARRIVE}})
    out += [{'op': 'record_new', 'record': l} for l in lines]
    rep = {'keys': keys, 'trunk': where['trunk'], 'arrive': where['arrive'], 'lines': len(lines), 'script_bytes': len(c.code) if hasattr(c, 'code') else None}
    return out, rep


def build(server):
    """The quest put into the open mod as one Undo. Returns the report."""
    gd, pr = server.GD, server.PR
    where = spots(gd, pr)
    o, rep = ops(gd, pr, where)
    made = server.edit("Waikiki's first quest: What the Sea Brought In", o)['made']
    want = [rep['keys'][k] for k in ('lockbox', 'trunk', 'message', 'script', 'quest', 'ask', 'back', 'cut', 'trunk_ref', 'arrive_ref')]
    assert made[:len(want)] == want, ('keys not as reserved', made[:len(want)], want)
    rep['top_over_water'] = where['trunk_top_over_water']
    return rep
