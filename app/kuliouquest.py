"""Waikiki's second quest, "The First Place on the Way" (docs/waikiki-story-plan.md: the main quest's step 3, "What you see in
Kuliouou", and who has Pip-Boys; asked for 20 Nov 2026, built only from what the user decided there).

After "What the Sea Brought In" (castawayquest.py) sends you up the coast road, Kuliouou's people are there waiting:
- on the road into the camp, catchers take a stranger nobody will miss before tribute day, and lead him off up the road;
- on the beach a father sells his son to a pirate whose boat is drawn up on the sand: they can't pay both sides this time,
  and he talks of it as ordinary; the son and the pirate go down to the boat;
- by the fire a woman sees the Pip-Boy, takes you for a captain's kin (so nobody sells you), doesn't believe "it was just
  given to me", says who Kuliouou pays and points you up the coast road to Waikiki. Done then.

How it moves: the recipe (docs/waikiki-quest-recipe.md). The quest's own script does every step; no line carries a script.
The people are placed off (initially disabled) and switched on once the first quest has sent you here (its stage 30), so a
player who wanders in early sees nobody. Talks are started by the script and heard by MenuMode 1009; those led away walk on
a travel package (a copy of the game's own, to a marker of the quest's) and are switched off once you are well away or after
a while. If anyone in a scene is dead the scene is passed over, so nothing sticks. All lines silent.

You can do nothing about the sale but watch (the user, 20 Nov 2026). Still a plain default: the people have role names
(Catcher, Stranger, Father, Son, Pirate, Woman by the Fire)."""
import json
import math

import api_quests as aq
import questrec as qr
import recordio
from castawayquest import _game_form, _named, _ref_by_edid

QUEST = 'FOLabFirstPlace'
QUEST_NAME = 'The First Place on the Way'
SCRIPT = 'FOLabFirstPlaceScript'
BEFORE = 'FOLabSeaBroughtIn'            # (castawayquest.QUEST: at its stage 30 you're sent here)
BEFORE_STAGE = 30
KULIOUOU = "Kuliouou Squatters' Camp"   # (the map marker of the camp)
MARKER_BASE = 'XMarkerHeading'
TRAVEL_FROM = 'VHDYesManDamEndTravelPackage'    # (the game's: travel to near a reference, no conditions, no script)
MALE, FEMALE = 'NVProspectorMale', 'NVProspectorFemale'
BOATS = ('Boat01a', 'Boat01b', 'Boat03a', 'Boat03b')    # (the smallest of these is drawn up on the beach)

# who: (key name, editor ID, name, template)
PEOPLE = [('catcher', 'FOLabKuliCatcher', 'Catcher', MALE),
          ('catcher2', 'FOLabKuliCatcher2', 'Catcher', MALE),
          ('stranger', 'FOLabKuliStranger', 'Stranger', MALE),
          ('father', 'FOLabKuliFather', 'Father', MALE),
          ('son', 'FOLabKuliSon', 'Son', MALE),
          ('pirate', 'FOLabKuliPirate', 'Pirate', MALE),
          ('woman', 'FOLabKuliWoman', 'Woman by the Fire', FEMALE)]
REF = {k: e + 'REF' for k, e, _n, _t in PEOPLE}
TAKEN_TO, BOAT_REF, BOAT_TO = 'FOLabKuliTakenTo', 'FOLabKuliBoatREF', 'FOLabKuliBoatTo'
PACKS = {'take': 'FOLabKuliTakeAway', 'boat': 'FOLabKuliToTheBoat'}

WORDS = {
    'catch': "Keep walking. This one's nobody's: no family, no valley, nobody to miss him. Tribute day's coming.",
    'sale': "Don't look at me like that. We can't pay both this time, the boats and the Kahuna's men. The boat takes him "
            "and we keep the roof. Everyone here's done it, or will.",
    'pip': "That on your arm. Nobody sells you, then. Whose are you? A captain's?",
    'given_prompt': "It was just given to me.",
    'given': "Course it was. Keep your secrets. This is Kuliouou. We pay both: the pirates at the marina and the Kahuna's men "
             "from Waikiki. Waikiki's up the coast road, past Niu. The Kahuna keeps it safe, for those worth something. Go on "
             "there.",
}
TOPICS = {'catch': 'FOLabKuli1Catch', 'sale': 'FOLabKuli2Sale', 'pip': 'FOLabKuli3Pip', 'given': 'FOLabKuli3Given'}
SAYS = {'catch': 'catcher', 'sale': 'father', 'pip': 'woman', 'given': 'woman'}
STAGES = [
    (10, "On the road into Kuliouou, catchers took a stranger: nobody would miss him, and tribute day is coming.", False),
    (20, "On the beach a family sold their son to a pirate boat. They couldn't pay both sides this time. Nobody thought it "
         "strange.", False),
    (30, "A woman by the fire saw the Pip-Boy and took me for a captain's kin. She didn't believe it was just given to me.", False),
    (100, "Kuliouou pays both the pirates and the Kahuna's men. The woman by the fire sent me up the coast road, past Niu, "
          "to Waikiki.", True),
]
OBJECTIVES = [(10, "Look round Kuliouou", 'father'), (20, "Talk to the woman by the fire", 'woman')]
CATCH_NEAR, SALE_NEAR, WOMAN_NEAR = 1500, 900, 350   # (units: each talk starts when you're this near its speaker)
GONE_FAR, GONE_AFTER, BOARD_AFTER = 2500, 120, 25    # (those led away go once you're this far, or after this many seconds;
                                                     #  the son and the pirate once this long has passed: aboard)
RETRY, TRIES = 6, 3


def script_source():
    """The quest's own script. `state`: 0 waiting for the first quest, 1 here, 9 done. Each scene has its own: `catchstep` the
    catchers (0 waiting, 1 talk, 2 leading away, 3 gone), `salestep` the sale (likewise), `womanstep` the woman (0 waiting, 1 talk, 2 done).
    `asked` names the talk asked for (1 catch, 2 sale, 3 woman), `talked` it was shown (set in MenuMode)."""
    Q = QUEST
    o = lambda n: 'SetObjectiveDisplayed %s %d 1' % (Q, n)
    done = lambda n: 'SetObjectiveCompleted %s %d 1' % (Q, n)
    R = REF
    L = ['scn ' + SCRIPT, '',
         "; Made by FOLab (kuliouquest.py): Waikiki's second quest. See its notes.",
         'short state', 'short catchstep', 'short salestep', 'short womanstep', 'short asked', 'short talked', 'short tries',
         'float since', 'float catchtime', 'float saletime', '',
         'begin GameMode', '',
         '\tif state == 9',
         '\t\treturn',
         '\tendif',
         '\tif state == 0',
         '\t\tif GetStage %s < %d\t; (not sent here yet)' % (BEFORE, BEFORE_STAGE),
         '\t\t\treturn',
         '\t\tendif']
    L += ['\t\t%s.Enable' % R[k] for k, _e, _n, _t in PEOPLE]
    L += ['\t\t%s.Enable' % BOAT_REF,
          '\t\tset state to 1',
          '\t\treturn',
          '\tendif', '',
          # (a talk asked for: shown and shut (GameMode runs again only once the dialogue has shut), or not come in time)
          '\tif asked > 0',
          '\t\tif talked == 1',
          '\t\t\tif asked == 1',
          '\t\t\t\tset catchstep to 2',
          '\t\t\telseif asked == 2',
          '\t\t\t\tset salestep to 2',
          '\t\t\telse',
          '\t\t\t\tset womanstep to 2',
          '\t\t\tendif',
          '\t\t\tset asked to 0',
          '\t\t\tset tries to 0',
          '\t\telse',
          '\t\t\tset since to since + GetSecondsPassed',
          '\t\t\tif since > %d' % RETRY,
          '\t\t\t\tset asked to 0',
          '\t\t\tendif',
          '\t\t\treturn',
          '\t\tendif',
          '\tendif', '',
          # the catchers, on the road in
          '\tif catchstep == 0 && player.GetDistance %s < %d' % (R['catcher'], CATCH_NEAR),
          '\t\tSetStage %s 10' % Q,
          '\t\t' + o(10),
          '\t\tset catchstep to 1',
          '\tendif',
          '\tif catchstep == 1',
          '\t\tif %s.GetDead || %s.GetDead || tries >= %d || player.GetDistance %s > %d' % (R['catcher'], R['stranger'], TRIES, R['catcher'], CATCH_NEAR + 500),
          '\t\t\tset catchstep to 2',
          '\t\t\tset tries to 0',
          '\t\telseif asked == 0',
          '\t\t\tset asked to 1',
          '\t\t\tset talked to 0',
          '\t\t\tset since to 0',
          '\t\t\tset tries to tries + 1',
          '\t\t\t%s.StartConversation PlayerREF %s' % (R['catcher'], TOPICS['catch']),
          '\t\t\treturn',
          '\t\tendif',
          '\tendif',
          '\tif catchstep == 2',
          '\t\tif catchtime == 0']
    L += ['\t\t\t%s.AddScriptPackage %s' % (R[k], PACKS['take']) for k in ('catcher', 'catcher2', 'stranger')]
    L += ['\t\tendif',
          '\t\tset catchtime to catchtime + GetSecondsPassed',
          '\t\tif catchtime > %d || player.GetDistance %s > %d' % (GONE_AFTER, R['stranger'], GONE_FAR)]
    L += ['\t\t\t%s.Disable' % R[k] for k in ('catcher', 'catcher2', 'stranger')]
    L += ['\t\t\tset catchstep to 3',
          '\t\tendif',
          '\tendif', '',
          # the sale, on the beach
          '\tif salestep == 0 && player.GetDistance %s < %d' % (R['father'], SALE_NEAR),
          '\t\tSetStage %s 20' % Q,
          '\t\tset salestep to 1',
          '\tendif',
          '\tif salestep == 1 && asked == 0',
          '\t\tif %s.GetDead || %s.GetDead || tries >= %d || player.GetDistance %s > %d' % (R['father'], R['son'], TRIES, R['father'], SALE_NEAR + 500),
          '\t\t\tset salestep to 2',
          '\t\t\tset tries to 0',
          '\t\telse',
          '\t\t\tset asked to 2',
          '\t\t\tset talked to 0',
          '\t\t\tset since to 0',
          '\t\t\tset tries to tries + 1',
          '\t\t\t%s.StartConversation PlayerREF %s' % (R['father'], TOPICS['sale']),
          '\t\t\treturn',
          '\t\tendif',
          '\tendif',
          '\tif salestep == 2',
          '\t\tif saletime == 0',
          '\t\t\t' + done(10),
          '\t\t\t' + o(20),
          '\t\t\t%s.AddScriptPackage %s' % (R['son'], PACKS['boat']),
          '\t\t\t%s.AddScriptPackage %s' % (R['pirate'], PACKS['boat']),
          '\t\tendif',
          '\t\tset saletime to saletime + GetSecondsPassed',
          '\t\tif saletime > %d' % BOARD_AFTER,
          '\t\t\t%s.Disable' % R['son'],
          '\t\t\t%s.Disable' % R['pirate'],
          '\t\t\tset salestep to 3',
          '\t\tendif',
          '\tendif', '',
          # the woman by the fire (once the sale is seen, or passed over)
          '\tif womanstep == 0 && salestep >= 2 && player.GetDistance %s < %d' % (R['woman'], WOMAN_NEAR),
          '\t\tset womanstep to 1',
          '\tendif',
          '\tif womanstep == 1 && asked == 0',
          '\t\tif %s.GetDead || tries >= %d' % (R['woman'], TRIES),
          '\t\t\tset womanstep to 2',
          '\t\telseif player.GetDistance %s < %d' % (R['woman'], WOMAN_NEAR + 200),
          '\t\t\tset asked to 3',
          '\t\t\tset talked to 0',
          '\t\t\tset since to 0',
          '\t\t\tset tries to tries + 1',
          '\t\t\t%s.StartConversation PlayerREF %s' % (R['woman'], TOPICS['pip']),
          '\t\t\treturn',
          '\t\telse',
          '\t\t\tset womanstep to 0',
          '\t\tendif',
          '\tendif',
          '\tif womanstep == 2',
          '\t\tSetStage %s 30' % Q,
          '\t\t' + done(10),
          '\t\t' + done(20),
          '\t\tSetStage %s 100' % Q,
          '\t\tset state to 9',
          '\t\tCompleteQuest %s' % Q,
          '\tendif',
          '', 'end', '',
          'begin MenuMode', '',
          '\tif MenuMode 1009 && asked > 0\t; (the dialogue: the talk asked for is on screen)',
          '\t\tset talked to 1',
          '\tendif', '', 'end', '']
    return '\r\n'.join(L)


def _edid_of(gd, pr, base):
    return recordio.field(pr.records[base], 'EDID') if base.startswith('+') else gd.edid(gd.from_key(base)) or ''


def _person(gd, pr, edid, name, template):
    import api_characters as ac
    import castawaytalk
    try:
        f = _game_form(gd, template, 'NPC_')
    except ValueError:
        f = _game_form(gd, MALE, 'NPC_')
    tmpl = gd.key(f)
    npc = json.loads(json.dumps(ac.get_record(gd, pr, tmpl)))
    recordio.set_field(npc, 'EDID', edid, label='Editor ID')
    full = ac.one(npc, 'FULL')
    if full:
        full['value'] = name
    else:
        ac.insert(npc, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    npc['subs'] = [s for s in npc['subs'] if s['tag'] not in ('SCRI', 'PKID')]
    ac.insert(npc, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(ac._find(gd, 'PACK', castawaytalk.STAY))})
    ac.set_num(npc, 'ACBS', 'Flags', ac.num(npc, 'ACBS', 'Flags') & ~0x2)
    npc['src'] = ''
    npc['copied_from'] = tmpl
    return npc


def _travel(gd, edid, target):
    import api_characters as ac
    rec = recordio.load(gd, _game_form(gd, TRAVEL_FROM, 'PACK'))
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('CTDA', 'SCDA', 'SCTX', 'SCRO', 'SLSD', 'SCVR')]
    ac.set_place(rec, 0, target, 128)
    rec['src'] = ''
    return rec


def spots(gd, pr):
    """Where everyone stands, from the camp's map marker: the catchers on the road in from the coast (nearest `WAY_IN` from the camp toward
    its lowest ground), led off to the road piece farthest from the camp within reach; the sale where the ground first comes down to the
    beach toward the lowest ground round the camp, the boat beyond it; the woman by the camp. {name: (cell, p)} + 'world'."""
    import roadgen
    mk = mcell = None
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if (r.get('marker') or {}).get('name') == KULIOUOU and not r.get('removed'):
                mk, mcell = r['p'], ck
    if mk is None:
        raise ValueError('no map marker %r' % KULIOUOU)
    world = gd.ext_cells[gd.from_key(mcell)]
    grid = gd.grid(world)
    G = roadgen.Ground(gd, pr, world)
    cx, cy = mk[0], mk[1]
    ground = lambda x, y: G.at(x, y) if G.at(x, y) is not None else mk[2]
    cell_of = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    face = lambda x, y, tx, ty: math.atan2(tx - x, ty - y)      # (the game's heading: 0 faces +y, turning toward +x)

    def at(x, y, rz=0.0):
        return (cell_of(x, y), [round(x, 1), round(y, 1), round(ground(x, y), 1), 0.0, 0.0, round(rz, 4)])

    roads = []
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            p = r.get('p')
            if p and not r.get('removed') and math.hypot(p[0] - cx, p[1] - cy) < 6000 and 'Road' in _edid_of(gd, pr, r['base']):
                roads.append(p)
    if not roads:
        raise ValueError('no road near %s' % KULIOUOU)
    # (the way in is from the coast: toward the lowest ground round the camp)
    low = min(range(16), key=lambda k: ground(cx + 2500 * math.sin(k * math.pi / 8), cy + 2500 * math.cos(k * math.pi / 8)))
    dx, dy = math.sin(low * math.pi / 8), math.cos(low * math.pi / 8)
    wx0, wy0 = cx + dx * WAY_IN, cy + dy * WAY_IN
    rd = min((p for p in roads if math.hypot(p[0] - cx, p[1] - cy) >= ROAD_OFF), key=lambda p: math.hypot(p[0] - wx0, p[1] - wy0), default=None)
    if rd is None:
        raise ValueError('no road near %s' % KULIOUOU)
    away = max((p for p in roads if math.hypot(p[0] - rd[0], p[1] - rd[1]) < 4500), key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
    # (the catchers on the road, the stranger between them, all facing the camp)
    side = (rd[1] - cy, -(rd[0] - cx))
    n = math.hypot(*side) or 1.0
    sx, sy = side[0] / n * 90, side[1] / n * 90
    out = {'catcher': at(rd[0], rd[1], face(rd[0], rd[1], cx, cy)),
           'stranger': at(rd[0] + sx, rd[1] + sy, face(rd[0], rd[1], cx, cy)),
           'catcher2': at(rd[0] + 2 * sx, rd[1] + 2 * sy, face(rd[0], rd[1], cx, cy)),
           'taken_to': at(away[0], away[1])}
    for k in ('catcher', 'stranger', 'catcher2'):       # (on the road piece's top, not the land under it)
        out[k][1][2] = round(max(out[k][1][2], rd[2]), 1)
    # (the beach: toward the lowest ground round the camp, the first spot under BEACH_Z, then on a little)
    d = 200
    while d < 4000 and ground(cx + dx * d, cy + dy * d) > BEACH_Z:
        d += 64
    d += 150
    fx, fy = cx + dx * d, cy + dy * d
    out['father'] = at(fx, fy, face(fx, fy, cx, cy))
    out['son'] = at(fx + dy * 90, fy - dx * 90, face(fx, fy, cx, cy))
    bx, by = fx + dx * 450, fy + dy * 450
    out['pirate'] = at(fx + dx * 150, fy + dy * 150, face(fx + dx * 150, fy + dy * 150, fx, fy))
    out['boat'] = at(bx, by, math.atan2(dy, dx))
    out['boat_to'] = at(bx - dx * 120, by - dy * 120)
    # (the woman a step from the marker, facing the road in)
    wx, wy = cx + (rd[0] - cx) / max(1.0, math.hypot(rd[0] - cx, rd[1] - cy)) * 150, cy + (rd[1] - cy) / max(1.0, math.hypot(rd[0] - cx, rd[1] - cy)) * 150
    out['woman'] = at(wx, wy, face(wx, wy, rd[0], rd[1]))
    out['world'] = world
    return out


ROAD_OFF = 800      # (the catchers stand on a road piece at least this far from the camp,
WAY_IN = 1800       #  the nearest to this far from it toward the coast: the way in)
BEACH_Z = 40        # (ground under this, toward the sea, is the beach)


def _boat(gd):
    import townbuild
    best = None
    for e in BOATS:
        try:
            k = gd.key(_game_form(gd, e, 'STAT'))
        except ValueError:
            continue
        b = townbuild.obnd(gd, k)
        size = (b[3] - b[0]) * (b[4] - b[1]) if b else 1e12
        if best is None or size < best[0]:
            best = (size, k)
    if best is None:
        raise ValueError('the game has none of the boats %s' % (BOATS,))
    return best[1]


KEY_ORDER = [k for k, _e, _n, _t in PEOPLE] + ['take', 'boat_pack', 'script', 'quest'] + list(TOPICS) + \
    ['ref_' + k for k, _e, _n, _t in PEOPLE] + ['boat_ref', 'taken_to', 'boat_to']


def ops(gd, pr, where):
    """(ops, report): every record and thing of the quest, in one list for one Undo. Nothing is changed here."""
    import api_scripts
    import newgame
    quests = {recordio.field(r, 'EDID') for r in pr.records.values() if r.get('type') == 'QUST'}
    if BEFORE not in quests:
        raise ValueError('the mod has no %s for this quest to follow' % BEFORE)
    if QUEST in quests:
        raise ValueError('the mod already has %s' % QUEST)
    keys = dict(zip(KEY_ORDER, aq._reserve(pr, len(KEY_ORDER))))
    people = [_person(gd, pr, e, n, t) for _k, e, n, t in PEOPLE]
    take = _travel(gd, PACKS['take'], keys['taken_to'])
    board = _travel(gd, PACKS['boat'], keys['boat_to'])
    target = {k: keys['ref_' + k] for k, _e, _n, _t in PEOPLE}
    quest = qr.quest_record({'edid': QUEST, 'script': keys['script'], 'name': QUEST_NAME, 'flags': {'start_enabled': True},
                             'priority': 55, 'delay': 0.5,
                             'stages': [{'index': n, 'entries': [{'flags': {'complete': fin}, 'conditions': [], 'log': log, 'next': ''}]}
                                        for n, log, fin in STAGES],
                             'objectives': [{'index': n, 'text': text, 'targets': [{'target': target[t], 'flags': 0, 'conditions': []}]}
                                            for n, text, t in OBJECTIVES]})
    topic = lambda edid, name: qr.topic_record({'edid': edid, 'name': name, 'priority': 50.0, 'kind': 0,
                                               'quests': [{'quest': keys['quest'], 'links': []}]})
    topics = {k: topic(TOPICS[k], WORDS['given_prompt'] if k == 'given' else '') for k in TOPICS}
    persistent = lambda edid: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]}
    before = next(k for k, r in pr.records.items() if r.get('type') == 'QUST' and recordio.field(r, 'EDID') == BEFORE)
    extra = {keys['quest']: quest, keys['take']: take, keys['boat_pack']: board, keys['boat_ref']: persistent(BOAT_REF)}
    extra.update({keys[k]: topics[k] for k in TOPICS})
    extra.update({keys['ref_' + k]: persistent(REF[k]) for k, _e, _n, _t in PEOPLE})
    sc = api_scripts.scripts()
    c = sc.compile(script_source(), keys['script'], 'quest', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the quest script does not compile: %s' % (c,))
    script = sc._record_of(c, SCRIPT)
    out = [{'op': 'record_new', 'record': r} for r in people]
    out += [{'op': 'record_new', 'record': take}, {'op': 'record_new', 'record': board},
            {'op': 'record_new', 'record': script}, {'op': 'record_new', 'record': quest}]
    out += [{'op': 'record_new', 'record': topics[k]} for k in TOPICS]
    off = {'disabled': True}
    for k, _e, _n, _t in PEOPLE:
        cell, p = where[k]
        out.append({'op': 'add', 'cell': cell, 'base': keys[k], 'p': p, 's': 1.0, 'extra': {'persistent': True, 'edid': REF[k], 'props': dict(off)}})
    marker = gd.key(_game_form(gd, MARKER_BASE, 'STAT'))
    cell, p = where['boat']
    out.append({'op': 'add', 'cell': cell, 'base': _boat(gd), 'p': p, 's': 1.0, 'extra': {'persistent': True, 'edid': BOAT_REF, 'props': dict(off)}})
    for name, edid in (('taken_to', TAKEN_TO), ('boat_to', BOAT_TO)):
        cell, p = where[name]
        out.append({'op': 'add', 'cell': cell, 'base': marker, 'p': p, 's': 1.0, 'extra': {'persistent': True, 'edid': edid}})
    # the lines: silent, each said by its one speaker; the woman's first offers the one answer
    lines = []
    for k in TOPICS:
        if k == 'given':
            continue
        l = aq.new_line_plain(gd, pr, keys[k], keys['quest'], keys[SAYS[k]], WORDS[k], goodbye=(k != 'pip'))
        if k == 'pip':
            l['choices'] = [keys['given']]
        lines.append(l)
    lines.append(aq.new_line_plain(gd, pr, keys['given'], keys['quest'], keys['woman'], WORDS['given'], goodbye=True))
    out += [{'op': 'record_new', 'record': qr.info_record(dict(l, begin=None, end=None))} for l in lines]
    rep = {'keys': keys, 'lines': len(lines), 'before': before,
           'spots': {k: v for k, v in where.items() if k != 'world'}}
    return out, rep


def build(server):
    """The quest put into the open mod as one Undo. Returns the report."""
    gd, pr = server.GD, server.PR
    where = spots(gd, pr)
    o, rep = ops(gd, pr, where)
    made = server.edit("Waikiki's second quest: The First Place on the Way", o)['made']
    want = [rep['keys'][k] for k in KEY_ORDER]
    assert made[:len(want)] == want, ('keys not as reserved', made[:len(want)], want)
    return rep
