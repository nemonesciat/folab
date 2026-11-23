"""Boat travel round Waikiki's coast (the user, 21 Nov 2026: "having rideable boats would make this a next level mod";
the plan: docs/waikiki-boats-plan.md, step one).

A boat lies at the shore by each stop (`STOPS`). Use it ("Sail Boat") and a message asks where to: the other stops, or
stay ashore. The screen fades out, you are put ashore beside the boat at the other stop, a few hours have gone by
(`hours`), and the screen fades back. Nothing moves on the water: that is what makes it work the same in the original
game and in nv-rs, which runs no script extender. Only the game's own script commands, in the game's own pattern for a
move during a fade (General Oliver's punch-out: the quick extended fade, the move two seconds in, controls back after).

Records: one activator (`FOLabFerryBoat`, the game's small boat Boat03a's model, prompt "Sail"), its script (works out
which stop it is at from the arrival markers and starts the trip quest), one message per stop (`FOLabFerryMenu<n>`, the
other stops in `STOPS` order, then "Stay ashore"), a refusal (`FOLabFerryNotNow`: not while enemies are on you), the trip
quest (not start-enabled: it runs only during a trip and stops itself) and its script. Refs: a boat in the water and a
persistent XMarkerHeading ashore (`FOLabFerryLand<n>`) per stop, the marker facing inland.

`spots(gd, pr)` finds each boat's water and arrival ground near the stop's map marker (changes nothing), `ops(gd, pr,
where)` the ops for one Undo (changes nothing), `build(server)` applies them. No fare: the user hasn't said what Waikiki's
money is. Not yet seen in either game."""
import json
import math

import api_quests as aq
import questrec as qr
import recordio
from castawayquest import _game_form

# (key, the name on the button, the map marker it's by). Plain letters: the game's fonts have no okina or macron.
STOPS = [
    ('waikiki', 'Waikiki', 'Ala Wai Boat Harbor'),
    ('flotilla', 'The Flotilla', 'The Flotilla'),
    ('hawaiikai', "Hawai'i Kai (Koko Marina)", 'Koko Marina'),
    ('waimanalo', 'Waimanalo (Blue Lagoon)', 'Blue Lagoon'),       # (by the settlers' ship: the user to say if that's right)
    ('hanauma', 'Hanauma Bay', 'Hanauma Bay'),
]
BOAT_MODEL_FROM = 'Boat03a'     # (the game's small open boat; landmarks.MOORED floats it 12 over the water)
BOAT_LIFT = 12.0
BOAT_NAME, BOAT_PROMPT = 'Boat', 'Sail'
QUESTION = 'Where do you want to sail?'
STAY = 'Stay ashore'
NOT_NOW = "You can't sail while enemies are close."
FADE = 'FadeToBlackAndBackQuickExtendedISFX'
MOVE_AT, BACK_AT = 2.0, 3.0     # (seconds into the fade: moved while black; controls back once it lifts)
UNITS_AN_HOUR = 60000.0         # (a ride's game hours: one per this much straight distance, at least one)
NEAR = 3000.0                   # (a boat this near an arrival marker is that stop's)
DRAFT, DEEP_MOST = 60.0, 900.0  # (water under the boat: at least this deep, not past this: a boat by the shore)
REACH = 6000                    # (how far from the marker the shore is looked for)
ASHORE = (250, 350, 450, 550, 700)
EDIDS = {'boat': 'FOLabFerryBoat', 'boat_script': 'FOLabFerryBoatScript', 'quest': 'FOLabFerry',
         'quest_script': 'FOLabFerryScript', 'not_now': 'FOLabFerryNotNow'}


def menu_edid(n):
    return 'FOLabFerryMenu%d' % n


def land_edid(n):
    return 'FOLabFerryLand%d' % n


def others(i):
    """The stops a boat at stop i (1-based) offers, in order: [(button index, stop number)]."""
    return [(b, j) for b, j in enumerate(j for j in range(1, len(STOPS) + 1) if j != i)]


def hours(where, i, j):
    (_c, a), (_d, b) = where['land'][i - 1], where['land'][j - 1]
    return max(1, int(round(math.hypot(b[0] - a[0], b[1] - a[1]) / UNITS_AN_HOUR)))


# ---------- scripts ----------

def boat_source():
    L = ['scn ' + EDIDS['boat_script'], '',
         "; Made by FOLab (boatferry.py): a boat of Waikiki's boat travel. It finds which stop it's at and starts the trip.",
         '', 'begin OnActivate', '',
         '\tif IsActionRef player == 0',
         '\t\treturn',
         '\tendif',
         '\tif GetQuestRunning %s' % EDIDS['quest'],
         '\t\treturn',
         '\tendif',
         '\tset %s.here to 0' % EDIDS['quest']]
    for n in range(1, len(STOPS) + 1):
        L += ['\t%sif GetDistance %s < %d' % ('' if n == 1 else 'else', land_edid(n), NEAR),
              '\t\tset %s.here to %d' % (EDIDS['quest'], n)]
    L += ['\tendif',
          '\tif %s.here' % EDIDS['quest'],
          '\t\tStartQuest %s' % EDIDS['quest'],
          '\tendif', '', 'end', '']
    return '\r\n'.join(L)


def quest_source(where):
    """`step` 0 asking, 1 waiting for a button, 2 fading (moved at MOVE_AT), 3 arrived (controls back at BACK_AT)."""
    q = EDIDS['quest']
    L = ['scn ' + EDIDS['quest_script'], '',
         "; Made by FOLab (boatferry.py): Waikiki's boat travel. Runs only during a trip; the boat starts it.",
         'short here', 'short dest', 'short step', 'short button', 'float timer', '',
         'begin GameMode', '',
         '\tif step == 0',
         '\t\tif player.IsInCombat',
         '\t\t\tShowMessage %s' % EDIDS['not_now'],
         '\t\t\tset here to 0',
         '\t\t\tStopQuest %s' % q,
         '\t\t\treturn',
         '\t\tendif']
    for n in range(1, len(STOPS) + 1):
        L += ['\t\t%sif here == %d' % ('' if n == 1 else 'else', n), '\t\t\tShowMessage %s' % menu_edid(n)]
    L += ['\t\telse',
          '\t\t\tStopQuest %s' % q,
          '\t\t\treturn',
          '\t\tendif',
          '\t\tset dest to 0',
          '\t\tset step to 1',
          '\t\treturn',
          '\tendif', '',
          '\tif step == 1',
          '\t\tset button to GetButtonPressed',
          '\t\tif button < 0',
          '\t\t\treturn',
          '\t\tendif']
    first = True
    for n in range(1, len(STOPS) + 1):
        for b, j in others(n):
            L += ['\t\t%sif here == %d && button == %d' % ('' if first else 'else', n, b), '\t\t\tset dest to %d' % j]
            first = False
    L += ['\t\tendif',
          '\t\tif dest == 0\t; (stay ashore)',
          '\t\t\tset here to 0',
          '\t\t\tset step to 0',
          '\t\t\tStopQuest %s' % q,
          '\t\t\treturn',
          '\t\tendif',
          '\t\tApplyImageSpaceModifier %s' % FADE,
          '\t\tDisablePlayerControls',
          '\t\tset timer to 0',
          '\t\tset step to 2',
          '\t\treturn',
          '\tendif', '',
          '\tset timer to timer + GetSecondsPassed',
          '\tif step == 2 && timer > %.1f' % MOVE_AT]
    for n in range(1, len(STOPS) + 1):
        L += ['\t\t%sif dest == %d' % ('' if n == 1 else 'else', n), '\t\t\tplayer.MoveTo %s' % land_edid(n)]
    L += ['\t\tendif']
    first = True
    for i in range(1, len(STOPS) + 1):
        for _b, j in others(i):
            L += ['\t\t%sif here == %d && dest == %d' % ('' if first else 'else', i, j),
                  '\t\t\tset GameHour to GameHour + %d' % hours(where, i, j)]
            first = False
    L += ['\t\tendif',
          '\t\tset timer to 0',
          '\t\tset step to 3',
          '\telseif step == 3 && timer > %.1f' % BACK_AT,
          '\t\tEnablePlayerControls',
          '\t\tset here to 0',
          '\t\tset dest to 0',
          '\t\tset step to 0',
          '\t\tStopQuest %s' % q,
          '\tendif', '', 'end', '']
    return '\r\n'.join(L)


# ---------- records ----------

def _message(edid, words, buttons=()):
    """A message box laid out as the game's (VEFR01NCREmergencyRadioMSG: DESC, FULL, INAM, DNAM 1, then ITXT per button)."""
    subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
            {'tag': 'DESC', 'label': 'Description', 'kind': 'z', 'value': words}]
    if buttons:
        subs.append({'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': BOAT_NAME})
    subs += [{'tag': 'INAM', 'label': 'Icon', 'kind': 'F', 'value': ''},
             {'tag': 'DNAM', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'I', 'value': 1}]}]
    subs += [{'tag': 'ITXT', 'label': 'Button text', 'kind': 'z', 'value': b} for b in buttons]
    return {'type': 'MESG', 'flags': 0, 'src': '', 'subs': subs}


def boat_record(gd, script_key):
    """The game's Boat03a as an activator: its bounds and model (and the model's hash) kept, a name, the script, the prompt."""
    stat = recordio.load(gd, _game_form(gd, BOAT_MODEL_FROM, 'STAT'))
    keep = {s['tag']: s for s in stat['subs']}
    subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': EDIDS['boat']}, keep['OBND'],
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': BOAT_NAME}, keep['MODL']]
    if 'MODT' in keep:
        subs.append(keep['MODT'])
    subs += [{'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script_key},
             {'tag': 'XATO', 'label': 'Activation prompt', 'kind': 'z', 'value': BOAT_PROMPT}]
    return json.loads(json.dumps({'type': 'ACTI', 'flags': 0, 'src': '', 'subs': subs}))


def boat_half(gd):
    """(half width, half length) of the boat from its bounds."""
    import struct
    o = gd.fields(_game_form(gd, BOAT_MODEL_FROM, 'STAT')).get('OBND')
    x0, y0, _z0, x1, y1, _z1 = struct.unpack_from('<6h', o)
    return (x1 - x0) / 2.0, (y1 - y0) / 2.0


# ---------- where ----------

def _markers(pr):
    out = {}
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            m = r.get('marker')
            if m and not r.get('removed') and m.get('name'):
                out.setdefault(m['name'], (ck, r['p']))
    return out


def _water(gd, pr, world, ck):
    """The water height in a cell: the mod's own for it, else the world's."""
    import struct
    w = (getattr(pr, 'water', None) or {}).get(ck, 'none')
    if w not in ('none', None):
        return float(w)
    d = gd.fields(world).get('DNAM')
    return struct.unpack_from('<ff', d)[1] if d and len(d) >= 8 else 0.0


def spots(gd, pr):
    """{'world', 'boat': [(cell, p)], 'land': [(cell, p)]} in STOPS order: for each stop the nearest water to its map
    marker that is deep enough for the boat along its length, clear of anything built over it, with standing ground
    ashore within a few steps; the boat lies along the shore, the arrival marker faces inland."""
    import waikikilife as wl
    marks = _markers(pr)
    missing = [m for _k, _n, m in STOPS if m not in marks]
    if missing:
        raise ValueError('no map marker %s' % ', '.join(missing))
    world = gd.ext_cells[gd.from_key(marks[STOPS[0][2]][0])]
    grid = gd.grid(world)
    cell_at = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    sp = wl.Spots(gd, pr, world)
    G, S = sp.G, sp.S
    hw, hl = boat_half(gd)
    out = {'world': world, 'boat': [], 'land': [], 'from_marker': []}
    for key, _name, mark in STOPS:
        mck, mp = marks[mark]
        found = None
        for r in range(0, REACH + 1, 150):
            turns = max(1, int(2 * math.pi * r / 300))
            for t in range(turns):
                a = 2 * math.pi * t / turns
                x, y = mp[0] + r * math.sin(a), mp[1] + r * math.cos(a)
                g = G.at(x, y)
                if g is None:
                    continue
                level = _water(gd, pr, world, cell_at(x, y))
                if not (level - DEEP_MOST < g < level - DRAFT):
                    continue
                ashore = None
                for k in range(16):
                    b = 2 * math.pi * k / 16
                    for d in ASHORE:
                        if ashore and d >= ashore[0]:
                            break
                        lx, ly = x + d * math.sin(b), y + d * math.cos(b)
                        z = sp.stand(lx, ly, apart=0)
                        if z is not None:
                            ashore = (d, lx, ly, z, b)
                            break
                if not ashore:
                    continue
                d, lx, ly, lz, b = ashore
                yaw = (b + math.pi / 2) % math.tau          # (along the shore)
                ux, uy = math.sin(yaw), math.cos(yaw)
                vx, vy = math.cos(yaw), -math.sin(yaw)
                ok = True
                S.load(x, y)
                for along in (-hl, 0.0, hl):
                    for side in (-hw, 0.0, hw):
                        px, py = x + ux * along + vx * side, y + uy * along + vy * side
                        gp = G.at(px, py)
                        if gp is None or gp > level - DRAFT / 2:
                            ok = False                      # (aground at the bow, stern or a side)
                        if any(level - 40 < z < level + 600 for z, _r in S.solids.tops(px, py)):
                            ok = False                      # (a pier, another boat, anything over the water)
                if not ok:
                    continue
                inland = math.atan2(lx - x, ly - y) % math.tau
                found = ((cell_at(x, y), [round(x, 1), round(y, 1), round(level + BOAT_LIFT, 1), 0.0, 0.0, round(yaw, 4)]),
                         (cell_at(lx, ly), [round(lx, 1), round(ly, 1), round(lz, 1), 0.0, 0.0, round(inland, 4)]), r)
                break
            if found:
                break
        if not found:
            raise ValueError('no shore for a boat within %d of %s' % (REACH, mark))
        out['boat'].append(found[0])
        out['land'].append(found[1])
        out['from_marker'].append(found[2])
    return out


# ---------- ops ----------

def key_order():
    return (['boat', 'boat_script', 'quest_script', 'quest', 'not_now'] + ['menu%d' % n for n in range(1, len(STOPS) + 1)]
            + ['land%d' % n for n in range(1, len(STOPS) + 1)])


def ops(gd, pr, where):
    """(ops, report) for boat travel, one Undo. Nothing is changed here."""
    import api_scripts
    import newgame
    if any(recordio.field(r, 'EDID') == EDIDS['quest'] for r in pr.records.values()):
        raise ValueError('the mod already has its boat travel')
    order = key_order()
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    persistent = lambda edid: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]}
    n = len(STOPS)
    menus = {'menu%d' % i: _message(menu_edid(i), QUESTION, [STOPS[j - 1][1] for _b, j in others(i)] + [STAY]) for i in range(1, n + 1)}
    not_now = _message(EDIDS['not_now'], NOT_NOW)
    quest = qr.quest_record({'edid': EDIDS['quest'], 'script': keys['quest_script'], 'name': '', 'flags': {},
                             'priority': 0, 'delay': 0.1, 'stages': [], 'objectives': []})
    extra = {keys[k]: m for k, m in menus.items()}
    extra.update({keys['not_now']: not_now, keys['quest']: quest})
    extra.update({keys['land%d' % i]: persistent(land_edid(i)) for i in range(1, n + 1)})
    sc = api_scripts.scripts()
    qc = sc.compile(quest_source(where), keys['quest_script'], 'quest', extra)
    if not hasattr(qc, 'subrecords'):
        raise ValueError('the trip script does not compile: %s' % (qc,))
    qscript = sc._record_of(qc, EDIDS['quest_script'])
    extra[keys['quest_script']] = qscript
    bc = sc.compile(boat_source(), keys['boat_script'], 'object', extra)
    if not hasattr(bc, 'subrecords'):
        raise ValueError('the boat script does not compile: %s' % (bc,))
    bscript = sc._record_of(bc, EDIDS['boat_script'])
    boat = boat_record(gd, keys['boat_script'])
    by_key = {'boat': boat, 'boat_script': bscript, 'quest_script': qscript, 'quest': quest, 'not_now': not_now}
    by_key.update(menus)
    out = [{'op': 'record_new', 'record': by_key[k]} for k in order if not k.startswith('land')]
    marker = gd.key(_game_form(gd, 'XMarkerHeading', 'STAT'))
    for i, (cell, p) in enumerate(where['land'], 1):
        out.append({'op': 'add', 'cell': cell, 'base': marker, 'p': p, 's': 1.0, 'extra': {'persistent': True, 'edid': land_edid(i)}})
    for cell, p in where['boat']:
        out.append({'op': 'add', 'cell': cell, 'base': keys['boat'], 'p': p, 's': 1.0})
    rides = {'%s-%s' % (STOPS[i - 1][0], STOPS[j - 1][0]): hours(where, i, j) for i in range(1, n + 1) for _b, j in others(i)}
    return out, {'keys': keys, 'rides': rides, 'quest_bytes': len(qc.data), 'boat_bytes': len(bc.data),
                 'stops': [(STOPS[i][0], where['boat'][i], where['land'][i]) for i in range(n)]}


def build(server):
    """Boat travel put into the open mod as one Undo. Returns the report."""
    gd, pr = server.GD, server.PR
    where = spots(gd, pr)
    o, rep = ops(gd, pr, where)
    made = server.edit("Waikiki's boat travel", o)['made']
    want = [rep['keys'][k] for k in key_order()]
    assert made[:len(want)] == want, ('keys not as reserved', made[:len(want)], want)
    return rep
