"""What the game stands in its kit pieces: doors, lights, furniture, containers and clutter, read from every interior in
each piece's own frame. A generated place copies those patterns, each piece getting a whole set one real piece had (or
nothing, as often as the game leaves it bare), so lights and clutter sit where the mesh has room for them. A room takes after
one real ROOM (survey.room: pieces standing open to each other), since one real place holds bathrooms and bedrooms alike.

    survey(game, kits)                  {kit: Survey}, kept on disk per game files' hash by load()
    survey.sets[piece key]              [[item, ...], ...] one list for each real piece, empties included
    survey.src[piece key], .room[piece key]     beside each of those: the real place it came from, and the real room in it
    survey.doors[piece key]             [(door key, x, y, z, rot, count)] doors that stand in this piece, no destination
    survey.exits                        the same for doors that lead somewhere: [(host word, door key, pose, count)]

An item is (base key, x, y, z, rx, ry, rz, scale, what) in the piece's frame; what says if it's a light, furniture, a
container, a thing, or rubble, and tags (from words in its name) let a room's purpose choose among sets."""
import collections
import json
import math
import os
import random
import re

import kitindex as K

COPY = {'LIGH': 'light', 'FURN': 'furn', 'CONT': 'cont', 'MISC': 'thing', 'ALCH': 'loot', 'AMMO': 'loot', 'BOOK': 'thing', 'WEAP': 'loot',
        'ARMO': 'loot', 'TERM': 'term', 'MSTT': 'stat', 'STAT': 'stat', 'ACTI': 'act', 'IDLM': 'stat', 'ADDN': 'stat'}
SKIP_WORDS = ('marker', 'xmarker', 'trigger', 'collision', 'fxlight', 'editor', 'roomportal', 'occlusion', 'cubemap', 'test', 'sound', 'door', 'teleport', 'dummy', 'aaa')
MAX_SETS = 120          # (of each piece: more than this adds nothing)
LOOT_KEPT = 0.25        # (weapons, ammo and aid: the game's rooms were balanced for its own places, not for a copy in every room)
MAX_ITEMS = 14          # (a set with more than this is a room's whole contents heaped on one piece: not copied)
VOID_KIND, ROOM_KIND = 'void', 'room'
RUBBLE_WORDS = ('rubble', 'debris', 'rock', 'wreck', 'pile', 'junk', 'trash', 'scrap', 'plank', 'collapsed', 'chunk', 'brick')
# (whole words of an editor ID: "can" is a tin, not the middle of "scanner"; a chair says nothing about what a room is for)
TAGS = {'sleep': ('bed', 'bunk', 'mattress', 'cot', 'pillow', 'sleep', 'dresser', 'nightstand', 'wardrobe', 'bedroll', 'footlocker'),
        'desk': ('desk', 'terminal', 'computer', 'filing', 'file', 'paper', 'papers', 'clipboard', 'typewriter', 'folder', 'office', 'swivel'),
        'eat': ('food', 'plate', 'fork', 'knife', 'spoon', 'cup', 'mug', 'kitchen', 'stove', 'fridge', 'nuka', 'cola', 'can', 'cans', 'cooking', 'sink', 'tray', 'diner', 'cafeteria', 'lunch', 'oven'),
        'machine': ('machine', 'machinery', 'reactor', 'generator', 'pipe', 'console', 'panel', 'gauge', 'tank', 'conduit', 'turbine', 'valve', 'fuse', 'pump', 'wrench', 'toolbox', 'workbench'),
        'store': ('crate', 'crates', 'shelf', 'shelves', 'box', 'boxes', 'barrel', 'barrels', 'cabinet', 'storage', 'chest', 'safe', 'rack', 'ammo', 'locker'),
        'care': ('medical', 'doctor', 'stimpak', 'surgery', 'surgical', 'syringe', 'morphine', 'anesthesia', 'gurney', 'clinic', 'autodoc', 'bandage', 'bloodpack', 'firstaid', 'hospital'),
        'play': ('pool', 'billiard', 'cue', 'chessboard', 'chess', 'couch', 'sofa', 'jukebox', 'pinball', 'dart', 'hamradio', 'radio', 'toy', 'teddy', 'piano', 'television', 'arcade'),
        'wash': ('toilet', 'stall', 'bathtub', 'shower', 'urinal', 'sink', 'tub'),
        'learn': ('chalkboard', 'blackboard', 'school', 'classroom', 'book', 'books', 'lectern', 'globe')}
WORD_RE = re.compile('[A-Z]+(?![a-z])|[A-Z]?[a-z]+')
SAME_THING = 6          # (of one big thing, one for this many squares of a room: a room isn't a showroom)
SAME_SMALL = 3          # (of one small thing, one for this many squares, and never fewer than this many allowed)
FOR_IT_PER = 8          # (a room wants one big thing that says what it's for, for this many squares...)
FOR_IT_MAX = 5          # (...up to this many)
WRECK_SHARE = 0.12      # (of the rooms off the main route, this many left wrecked on purpose: a vault's seen things)
WRECK_KEPT = 0.35       # (what's left in one of what it had)
WRECK_RUBBLE = 0.6      # (of its squares, how many get a heap)
WIDE_OPEN = 0.6         # (a side open this much of a square's width is the same room carrying on, not a doorway)
CLASH = 44              # (two big things with their middles nearer than this stand in each other)
# (a thing a room has one of, whatever else the game did: words of its name, and two kinds of pool table are still two pool tables)
ONE_TO_A_ROOM = ('pool', 'piano', 'jukebox', 'pinball', 'chalkboard', 'bathtub', 'overseer', 'reactor')
WRECK_HEAPS = 2         # (a wrecked room has at least this many, however small)
# (things named as fittings or marks on the wall say nothing about a room, however large)
FITTING_WORDS = ('light', 'lights', 'lamp', 'fan', 'vent', 'conduit', 'klaxon', 'graf', 'graff', 'graffiti', 'stain', 'blood', 'decal', 'poster', 'drape', 'fog', 'mist',
                 'dust', 'glow', 'litter', 'fx', 'arc', 'leak', 'intercom', 'speakers', 'pole', 'mat', 'wall', 'panel', 'cable', 'securiton', 'camera',
                 'skeleton', 'protectron', 'corpse', 'body')
BIG_KINDS = ('furn', 'cont', 'stat', 'term', 'act')
DOOR_FRONT = 150        # (how far into a room from a doorway stays clear...)
DOOR_SIDE = 96          # (...and how far to each side of its middle)
HUNG = 150              # (something this far above the floor is overhead: no one walks into it)
PURPOSE_TAGS = {'quarters': ('sleep',), 'small room': ('sleep', 'store'), 'office': ('desk',), 'workroom': ('machine', 'desk'), 'reactor': ('machine',),
                'far end': ('machine', 'store'), 'long room': ('eat', 'store', 'care'), 'atrium': ('eat',), 'hall': ('eat', 'desk'), 'entrance': ('store', 'machine'),
                'store': ('store',), 'mess': ('eat',), 'clinic': ('care',), 'rec room': ('play',), 'washroom': ('wash',), 'classroom': ('learn', 'desk'), 'corridor': (),
                'under a balcony': ('store', 'eat'), 'over a balcony': ('desk', 'sleep'), 'over the hall': ('desk',)}


def words_of(edid):
    """An editor ID's words: 'NVVaultFoodCan01' -> nv, vault, food, can."""
    return [w.lower() for w in WORD_RE.findall(edid)]


def tags_of(edid):
    """What a thing says about what a room is for. A word of six letters or more may also be part of a longer one (they're
    not always written with capitals); a short one must be a word in itself."""
    words = words_of(edid)
    plain = (edid or '').lower()
    return sorted(t for t, ws in TAGS.items() if any(w in words or (len(w) >= 6 and w in plain) for w in ws))


class Survey:
    def __init__(self):
        self.sets = collections.defaultdict(list)       # piece -> [[item]]
        self.src = collections.defaultdict(list)        # piece -> [cell each set came from]
        self.room = collections.defaultdict(list)       # piece -> [real room each set came from: 'cell/number']
        self.doors = collections.defaultdict(collections.Counter)   # piece -> Counter((door, x, y, z, rz))
        self.exits = collections.defaultdict(collections.Counter)   # piece -> Counter((door, x, y, z, rz))
        self.info = {}                                  # base -> (what, tags, edid, blocks)


def _usable(game, r, cache):
    """What kind of thing a ref's base is for copying, or None."""
    b = r['base']
    if b in cache:
        return cache[b]
    out = None
    entry = game.forms.get(b)
    if entry is not None:
        tag = entry[1].tag
        kind = COPY.get(tag)
        if kind:
            _t, edid, _n, model = game.describe(b)
            low = (edid or '').lower()
            if (model or kind == 'light') and not any(w in low for w in SKIP_WORDS):
                if kind == 'act' and 'SCRI' in game.fields(b):
                    kind = None
                if kind:
                    if kind == 'stat' and any(w in low for w in RUBBLE_WORDS):
                        kind = 'rubble'
                    out = (kind, tags_of(edid or ''), edid)
    cache[b] = out
    return out


def _door_base(game, r):
    entry = game.forms.get(r['base'])
    return entry is not None and entry[1].tag == 'DOOR'


def survey(game, kits, only=None):
    """{kit name: Survey}: which real things stood on which real piece. A thing belongs to the smallest piece whose
    footprint it's over, at the floor nearest below it."""
    out = {}
    hosts = {}
    for name, k in kits.items():
        if only and name not in only:
            continue
        for key, p in k.pieces.items():
            if p.foot and p.slots:
                hosts[key] = (name, p)
    use = {}
    keys = {}

    def key_of(fid):
        got = keys.get(fid)
        if got is None:
            got = keys[fid] = game.key(fid)
        return got
    for cell in game.interiors:
        rows = [r for r in game.refs(cell) if r['base'] and r['pos'] and r['base'] in game.forms]
        placed = []
        for r in rows:
            h = hosts.get(key_of(r['base']))
            if h:
                t = K.quarter(r['rot'][2])
                if t is not None and abs(r['rot'][0]) < 0.01 and abs(r['rot'][1]) < 0.01 and abs(r['scale'] - 1) < 0.001:
                    placed.append({'r': r, 't': t, 'p': h[1], 'kit': h[0], 'box': K._footprint_world(h[1], r['pos'][0], r['pos'][1], t), 'items': []})
        if not placed:
            continue
        grid = collections.defaultdict(list)
        for pl in placed:
            b = pl['box']
            for i in range(int(b[0] // 256), int(b[2] // 256) + 1):
                for j in range(int(b[1] // 256), int(b[3] // 256) + 1):
                    grid[(i, j)].append(pl)
        is_host = {id(pl['r']) for pl in placed}
        for r in rows:
            if id(r) in is_host:
                continue
            door = _door_base(game, r)
            info = None if door else _usable(game, r, use)
            if not door and not info:
                continue
            entry = game.forms.get(r['ref'])
            if entry is not None and entry[1].flags & 0x800:
                continue            # (starts disabled: something a quest turns on)
            x, y, z = r['pos']
            best, bk = None, None
            for pl in grid[(int(x // 256), int(y // 256))]:
                b = pl['box']
                if b[0] <= x <= b[2] and b[1] <= y <= b[3]:
                    fz = pl['r']['pos'][2] + pl['p'].box[2]
                    top = pl['r']['pos'][2] + pl['p'].box[5]
                    if fz - 16 <= z <= top + 16:
                        area = (b[2] - b[0]) * (b[3] - b[1])
                        k = (area, abs(z - fz))
                        if bk is None or k < bk:
                            best, bk = pl, k
            if not best:
                continue
            t = best['t']
            dx, dy = K.unturn_xy(x - best['r']['pos'][0], y - best['r']['pos'][1], t)
            dz = z - best['r']['pos'][2]
            rz = (r['rot'][2] - t * math.pi / 2) % (2 * math.pi)
            s = out.setdefault(best['kit'], Survey())
            pkey = best['p'].key
            if door:
                pose = (key_of(r['base']), round(dx), round(dy), round(dz), round(rz, 3))
                (s.exits if r['leads'] else s.doors)[pkey][pose] += 1
            else:
                bk2 = key_of(r['base'])
                s.info[bk2] = (info[0], info[1], info[2])
                best['items'].append((bk2, round(dx, 1), round(dy, 1), round(dz, 1), round(r['rot'][0], 3), round(r['rot'][1], 3), round(rz, 3), round(r['scale'], 3)))
        _join_rooms(placed, grid, kits)
        for pl in placed:
            s = out.setdefault(pl['kit'], Survey())
            # (a piece that's a whole room may hold a whole room's things)
            foot = pl['p'].foot
            squares = max(1, int((foot[2] - foot[0]) * (foot[3] - foot[1]) / (k_step(kits, pl['kit']) ** 2)))
            s.sets[pl['p'].key].append(pl['items'] if len(pl['items']) <= MAX_ITEMS * squares else [])
            s.src[pl['p'].key].append(cell)
            s.room[pl['p'].key].append('%s/%d' % (cell, pl['room']))
    rng = random.Random(1)
    for s in out.values():
        for k, v in s.sets.items():
            if len(v) > MAX_SETS:
                both = list(zip(v, s.src[k], s.room[k]))
                rng.shuffle(both)
                del both[MAX_SETS:]
                s.sets[k], s.src[k], s.room[k] = [b[0] for b in both], [b[1] for b in both], [b[2] for b in both]
    return out


def _join_rooms(placed, grid, kits):
    """Which real pieces make one real room: those standing open to each other, wider than a doorway. Sets each one's 'room'."""
    up = list(range(len(placed)))
    index = {id(pl): n for n, pl in enumerate(placed)}

    def top(n):
        while up[n] != n:
            up[n] = up[up[n]]
            n = up[n]
        return n
    for pl in placed:
        p, t = pl['p'], pl['t']
        wide = WIDE_OPEN * k_step(kits, pl['kit'])
        for s in p.slots:
            if not s['open'] or s['width'] < wide:
                continue
            lx, ly = {0: (p.foot[2] + 32, s['u']), 1: (s['u'], p.foot[3] + 32), 2: (p.foot[0] - 32, s['u']), 3: (s['u'], p.foot[1] - 32)}[s['side']]
            ax, ay = K.turn_xy(lx, ly, t)
            x, y = pl['r']['pos'][0] + ax, pl['r']['pos'][1] + ay
            for other in grid.get((int(x // 256), int(y // 256)), ()):
                b = other['box']
                if other is not pl and b[0] <= x <= b[2] and b[1] <= y <= b[3] and abs(other['r']['pos'][2] + other['p'].box[2] - pl['r']['pos'][2] - p.box[2]) < 64:
                    up[top(index[id(pl)])] = top(index[id(other)])
    for n, pl in enumerate(placed):
        pl['room'] = top(n)


def k_step(kits, name):
    return kits[name].step


def to_json(data):
    return {n: {'sets': s.sets, 'src': s.src, 'room': s.room, 'info': s.info, 'doors': {k: [list(p) + [c] for p, c in v.items()] for k, v in s.doors.items()},
                'exits': {k: [list(p) + [c] for p, c in v.items()] for k, v in s.exits.items()}} for n, s in data.items()}


def from_json(d):
    out = {}
    for n, v in d.items():
        s = out[n] = Survey()
        s.sets = collections.defaultdict(list, {k: [[tuple(i) for i in st] for st in sets] for k, sets in v['sets'].items()})
        s.src = collections.defaultdict(list, v['src'])
        s.room = collections.defaultdict(list, v['room'])
        # (what a thing is for is worked out afresh: its words may be read better than when this was made)
        s.info = {k: (i[0], tags_of(i[2] or ''), i[2]) for k, i in v['info'].items()}
        s.doors = collections.defaultdict(collections.Counter, {k: collections.Counter({tuple(p[:5]): p[5] for p in rows}) for k, rows in v['doors'].items()})
        s.exits = collections.defaultdict(collections.Counter, {k: collections.Counter({tuple(p[:5]): p[5] for p in rows}) for k, rows in v['exits'].items()})
    return out


def load(game, kits, folder):
    """The survey for these game files: from folder if it was made before."""
    path = os.path.join(folder, 'dressing3.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return from_json(json.load(f))
    data = survey(game, kits)
    os.makedirs(folder, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(to_json(data), f, separators=(',', ':'))
    os.replace(path + '.tmp', path)
    return data


# ---------- doors ----------

class Item:
    """Something standing in a generated place, not a building piece."""
    __slots__ = ('key', 'p', 's', 'what', 'owner', 'piece', 'link', 'extra')

    def __init__(self, key, p, s, what, owner, piece=None, link=None, extra=None):
        self.key, self.p, self.s, self.what, self.owner, self.piece = key, p, s, what, owner, piece
        self.link = link            # (a door: the two squares of the doorway it hangs in)
        self.extra = extra          # (what the ref carries beside where it stands: its lock, say)


def _world(m, dx, dy, dz, rx, ry, rz):
    x, y = K.turn_xy(dx, dy, m.turn)
    return [m.x + x, m.y + y, m.z + dz, rx, ry, (rz + m.turn * math.pi / 2) % (2 * math.pi)]


def door_table(kit, sv):
    """Which doors the game hangs in openings of each width: {width bucket: Counter((door, rotation against the way it faces))}.
    Rotation here doesn't change with the piece's turn, so it can go in any opening of that width."""
    got = getattr(sv, '_table', None)
    if got is not None:
        return got
    got = sv._table = collections.defaultdict(collections.Counter)
    for key, poses in sv.doors.items():
        p = kit.pieces.get(key)
        if not p:
            continue
        for (door, x, y, z, rz), n in poses.items():
            s = _near_slot(p, x, y)
            if s is not None and abs(z) < 16:
                got[s['width'] // 24][(door, round((rz + s['side'] * math.pi / 2) % math.pi, 2))] += n
    return got


def _near_slot(p, x, y):
    """The opening a door at this spot in a piece stands in, or None."""
    for s in p.slots:
        if not s['open']:
            continue
        sx, sy = {0: (p.foot[2], s['u']), 1: (s['u'], p.foot[3]), 2: (p.foot[0], s['u']), 3: (s['u'], p.foot[1])}[s['side']]
        if abs(sx - x) < 48 and abs(sy - y) < 48:
            return s
    return None


def _door_in(ts, sv, table, m, d, rng):
    """A door for the way out of placed piece m on world side d: (door key, world pose) or None."""
    p = ts.kit.pieces[m.key]
    side = (d + m.turn) % 4
    slot = next((s for s in p.slots if s['side'] == side and s['open']), None)
    if slot is None:
        return None
    options = []
    for (door, x, y, z, rz), n in sv.doors.get(m.key, {}).items():
        if _near_slot(p, x, y) is slot:
            options.append(((door, x, y, z, rz), n))
    if options:
        (door, x, y, z, rz) = _pick(options, rng)
        return door, _world(m, x, y, z, 0.0, 0.0, rz)
    kinds = table.get(slot['width'] // 24)
    if not kinds:
        return None
    door, inv = _pick(list(kinds.items()), rng)
    sx, sy = {0: (p.foot[2], slot['u']), 1: (slot['u'], p.foot[3]), 2: (p.foot[0], slot['u']), 3: (slot['u'], p.foot[1])}[side]
    return door, _world(m, sx, sy, 0.0, 0.0, 0.0, (inv - side * math.pi / 2) % (2 * math.pi))


def _pick(options, rng):
    total = sum(n for _o, n in options)
    x = rng.uniform(0, total)
    for o, n in options:
        x -= n
        if x <= 0:
            return o
    return options[-1][0]


def place_doors(ts, sv, plan, made, rng, share=0.8):
    """Real doors in the doorways: wherever a room meets anything else and the game hangs a door in an opening that wide."""
    table = door_table(ts.kit, sv)
    by = {}
    for m in made:
        if len(m.cells) == 1:
            by[m.cell] = m
    out = []
    style = {}
    for link in plan.links:
        a, b = tuple(link)
        oa, ob = plan.cells.get(a), plan.cells.get(b)
        if oa == ob or oa is None or ob is None:
            continue
        ka, kb = plan.owners[oa]['kind'], plan.owners[ob]['kind']
        if VOID_KIND in (ka, kb) or ROOM_KIND not in (ka, kb):
            continue
        # (a room in one piece always has its door: the overseer's office is locked)
        if rng.random() > share and not plan.owners[oa if ka == ROOM_KIND else ob].get('whole'):
            continue
        # (from the room's side)
        c, n = (a, b) if ka == ROOM_KIND else (b, a)
        m = by.get(c)
        d = next(i for i in range(4) if (c[0] + K.DX[i][0], c[1] + K.DX[i][1]) == (n[0], n[1]))
        if not m:
            # (a room in one piece, the overseer's office: the door hangs in the doorway from the other side)
            m, d = by.get(n), (d + 2) % 4
            if not m:
                continue
        got = _door_in(ts, sv, table, m, d, rng)
        if got:
            # (one door style to a room's doors, as often as not)
            room = plan.cells[c]
            if room in style and any(style[room] == k[0] for k in table.get(_slot_width(ts, m, d) // 24, {})):
                got = (style[room], got[1])
            style.setdefault(room, got[0])
            out.append(Item(got[0], got[1], 1.0, 'door', plan.cells[c], link=link))
    if plan.exit:
        c, d = plan.exit
        m = by.get(c)
        if m:
            got = _exit_in(ts, sv, table, m, d, rng)
            if got:
                out.append(Item(got[0], got[1], 1.0, 'exit', plan.cells[c]))
    return out


def _slot_width(ts, m, d):
    side = (d + m.turn) % 4
    return next((s['width'] for s in ts.kit.pieces[m.key].slots if s['side'] == side), 0)


def _exit_in(ts, sv, table, m, d, rng):
    """The door out of the place: one the game itself uses to lead somewhere, in an opening that wide if it can."""
    p = ts.kit.pieces[m.key]
    side = (d + m.turn) % 4
    slot = next((s for s in p.slots if s['side'] == side and s['open']), None)
    if slot is None:
        return None
    options = []
    for (door, x, y, z, rz), n in sv.exits.get(m.key, {}).items():
        if _near_slot(p, x, y) is slot:
            options.append(((door, x, y, z, rz), n))
    if options:
        (door, x, y, z, rz) = _pick(options, rng)
        return door, _world(m, x, y, z, 0.0, 0.0, rz)
    return _door_in(ts, sv, table, m, d, rng)


# ---------- lights and things ----------

SOLID = ('furn', 'cont', 'stat', 'rubble', 'act', 'term')
RUBBLE_SHARE = 0.3      # (of a ruined room's squares, how many get a heap)
LIGHTS_PER = 7          # (a room gets at least a light for this many squares...)
LIGHTS_MAX = 5          # (...and no more than one for this many: overlapping lights flicker in the game)


def theme_scores(sv, pieces, wanted, unwanted):
    """How well each real place suits a room, judged as a room: how many of the room's kinds of piece it has things for, how
    much of what's there is what this room is for, and how little of it is for something else. [(score, cell)], best first."""
    kinds = {m.key for m in pieces}
    seen = collections.defaultdict(set)
    good, bad, total = collections.Counter(), collections.Counter(), collections.Counter()
    for key in kinds:
        for cell, items in zip(sv.src.get(key, ()), sv.sets.get(key, ())):
            seen[cell].add(key)
            for it in items:
                tags = set(sv.info.get(it[0], ('', ()))[1])
                total[cell] += 1
                good[cell] += bool(tags & wanted)
                bad[cell] += bool(tags & unwanted)
    out = []
    for cell, have in seen.items():
        cover = len(have) / max(1, len(kinds))
        fit = (good[cell] - 0.5 * bad[cell]) / max(4, total[cell])
        # (somewhere with nothing in it isn't much to take after, and if the room's for something, what's for it counts most)
        out.append((cover + (3 * fit if wanted else 0) + 0.2 * min(1, total[cell] / 6), cell))
    out.sort(key=lambda r: (-r[0], r[1]))
    return out


def _theme(sv, pieces, wanted, unwanted, rng):
    """A real place for a room to take after: a place where these same pieces stood, with what the room is for in them.
    Everything in a room coming from one place is what makes it a room and not a heap."""
    best = [r for r in theme_scores(sv, pieces, wanted, unwanted) if r[0] > 0][:6]
    if not best:
        return None
    return _pick([(c, v * v) for v, c in best], rng)


def is_furnishing(info):
    """Is this something a room is furnished with, not a fitting or a mark on the wall? (info: an entry of Survey.info)"""
    return info[0] in BIG_KINDS and not set(words_of(info[2] or '')) & set(FITTING_WORDS)


def real_rooms(sv):
    """{real room: {'cell', 'sets': {piece: [sets]}, 'tags': how many things for each purpose, 'big': the same for furnishings,
    'total': things in all}} and {thing: how many of it a real room usually has, where it has any}, from the survey."""
    got = getattr(sv, '_rooms', None)
    if got is not None:
        return got
    rooms = {}
    counts = collections.defaultdict(collections.Counter)
    for key, sets in sv.sets.items():
        for st, cell, room in zip(sets, sv.src.get(key, ()), sv.room.get(key, ())):
            r = rooms.setdefault(room, {'cell': cell, 'sets': collections.defaultdict(list), 'tags': collections.Counter(), 'big': collections.Counter(), 'total': 0})
            r['sets'][key].append(st)
            for it in st:
                info = sv.info.get(it[0], ('thing', (), ''))
                if info[0] == 'light':
                    continue
                r['total'] += 1
                counts[it[0]][room] += 1
                for t in info[1]:
                    r['tags'][t] += 1
                    if is_furnishing(info):
                        r['big'][t] += 1
    usual = {k: sorted(c.values())[len(c) // 2] for k, c in counts.items()}
    sv._rooms = (rooms, usual)
    return sv._rooms


def room_scores(sv, pieces, wanted, unwanted):
    """How well each real room suits a room: what's in it is for this, little is for anything else, and it stands on the same
    kinds of piece. [(score, real room)], best first; only rooms with something for what this one's for."""
    kinds = {m.key for m in pieces}
    rooms, _usual = real_rooms(sv)
    out = []
    for name, r in rooms.items():
        good = sum(r['tags'][t] for t in wanted) + 2 * sum(r['big'][t] for t in wanted)
        bad = sum(r['big'][t] for t in unwanted)
        if not sum(r['big'][t] for t in wanted):
            continue
        cover = len(kinds & set(r['sets'])) / max(1, len(kinds))
        out.append((3 * (good - 2 * bad) / max(6, r['total']) + cover, name))
    out.sort(key=lambda q: (-q[0], q[1]))
    return out


def _fits(sv, st, unwanted, ruined=False):
    """A set with no furnishing for some other purpose (no bath in a bedroom), nor anything ruined in a room that isn't."""
    for it in st:
        info = sv.info.get(it[0], ('thing', (), ''))
        if is_furnishing(info) and set(info[1]) & unwanted and not set(info[1]) - unwanted:
            return False
        if not ruined and 'ruin' in (info[2] or '').lower():
            return False
    return True


def _open_floors(ts, sv):
    """Pieces that are floor with no wall on any side, by how high their floor is: what stands on one can stand on any of them."""
    got = getattr(sv, '_floors', None)
    if got is None:
        got = sv._floors = collections.defaultdict(list)
        for key in sv.sets:
            p = ts.kit.pieces.get(key)
            if p and p.foot and p.slots and len(p.slots) >= 4 and all(s['open'] and s['width'] >= 0.9 * ts.step for s in p.slots) and not any(w in (p.edid or '').lower() for w in ('rail', 'screen', 'cor', 'stair', 'sunken')):
                got[round(p.box[2] / 8)].append(key)
    return got


def _for_it(sv, st, wanted):
    """How many furnishings in this set say what the room's for."""
    n = 0
    for it in st:
        info = sv.info.get(it[0], ('thing', (), ''))
        n += is_furnishing(info) and bool(set(info[1]) & wanted)
    return n


def _put_set(sv, st, m, ruined, rng, out, keep=1.0):
    for it in st:
        what = sv.info.get(it[0], ('thing',))[0]
        if what == 'rubble' and not ruined and rng.random() < 0.7 or what == 'loot' and rng.random() > LOOT_KEPT or rng.random() > keep:
            continue
        out.append(Item(it[0], _world(m, it[1], it[2], it[3], it[4], it[5], it[6]), it[7], what, m.owner, m))


def _furnish(ts, sv, o, pieces, squares, wanted, unwanted, ruined, rng, out):
    """A room that's for something: what one real room like it had, piece by piece, and then, while it still doesn't say what
    it's for, what other real rooms like it had on these same kinds of piece, or on any open floor. False if the game has no
    such room."""
    rows = room_scores(sv, pieces, wanted, unwanted)
    if not rows:
        return False
    rooms, _usual = real_rooms(sv)
    first = _pick([(n, max(v, 0.05) ** 2) for v, n in rows[:5]], rng)
    o['theme'] = rooms[first]['cell']
    empty = []
    have = 0
    order = list(pieces)
    rng.shuffle(order)
    for m in order:
        here = [st for st in rooms[first]['sets'].get(m.key, ()) if _fits(sv, st, unwanted, ruined)]
        st = rng.choice(here) if here else []
        if _for_it(sv, st, wanted) == 0:
            empty.append((m, st))
            continue
        have += _for_it(sv, st, wanted)
        _put_set(sv, st, m, ruined, rng, out)
    want = max(1, min(FOR_IT_MAX, squares // FOR_IT_PER))
    donors = [n for _v, n in rows]
    bare = []
    for m, st in empty:
        if have < want:
            better = [q for n in donors for q in rooms[n]['sets'].get(m.key, ()) if _for_it(sv, q, wanted) and _fits(sv, q, unwanted, ruined)]
            if better:
                st = rng.choice(better)
                have += _for_it(sv, st, wanted)
        if st:
            _put_set(sv, st, m, ruined, rng, out)
        else:
            bare.append(m)
    floors = _open_floors(ts, sv)
    for m in bare:
        if have >= want:
            break
        p = ts.kit.pieces.get(m.key)
        if not p or not p.foot or m.key not in floors.get(round(p.box[2] / 8), ()):
            continue
        better = [q for n in donors for key in floors[round(p.box[2] / 8)] for q in rooms[n]['sets'].get(key, ()) if _for_it(sv, q, wanted) and _fits(sv, q, unwanted, ruined)]
        if not better:
            # (nothing the game stood on open floor says what this room's for: then tables and benches, not bare floor)
            better = [q for n in rooms for key in floors[round(p.box[2] / 8)] for q in rooms[n]['sets'].get(key, ())
                      if any(is_furnishing(sv.info.get(i[0], ('thing', (), ''))) for i in q) and _fits(sv, q, unwanted, ruined)]
        if better:
            st = rng.choice(better)
            have += max(1, _for_it(sv, st, wanted))
            _put_set(sv, st, m, ruined, rng, out)
    return True


def wreck_some(plan, rng):
    """A few rooms off the main route are left wrecked on purpose. Asked again, it leaves those it chose."""
    rooms = [o for o in plan.owners if o['kind'] == ROOM_KIND]
    if any('wrecked' in o for o in rooms):
        return
    # (of what the place has several of: its one rec room is what makes it a place people lived)
    kinds = collections.Counter(o['purpose'] for o in rooms)
    can = [o for o in rooms if not o.get('main') and not o.get('tall') and not o.get('whole') and not o.get('part_of') and kinds[o['purpose']] > 1]
    n = max(1, round(len(can) * WRECK_SHARE)) if len(can) >= 3 else 0
    for o in rooms:
        o['wrecked'] = False
    for o in rng.sample(can, min(len(can), n)):
        o['wrecked'] = True


def dress(ts, sv, plan, made, rng, purposes=None, ruined=False, only=None):
    """Lights and things for every piece: each room takes after one real room for the same purpose, and each of its pieces gets
    what that piece had there (or nothing, as often as it had nothing), with more from rooms like it if that doesn't say what the
    room's for. A few are left wrecked. Then the room is looked at as a whole: not too many of one thing, and nothing solid in a
    doorway or in front of it. [Item]. only: just this owner. An owner's 'pick' is a real place chosen for it by hand."""
    purposes = purposes or PURPOSE_TAGS
    out = []
    every = set(t for ws in PURPOSE_TAGS.values() for t in ws)
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    if only is None:
        wreck_some(plan, rng)
    wrecks = set()
    for o in plan.owners:
        if o['kind'] == VOID_KIND or not pieces[o['n']] or (only is not None and o['n'] != only):
            continue
        wanted = set(purposes.get(o.get('dress') or o['purpose'], ()))
        squares = sum(1 for c in o['cells'] if c not in plan.air)
        wrecked = o.get('wrecked') and not o.get('pick')
        if o.get('whole') and not o.get('pick'):
            # (a room made in one piece has what the game stood in it: that is the room)
            for m in pieces[o['n']]:
                if sv.sets.get(m.key):
                    _put_set(sv, rng.choice(sv.sets[m.key]), m, ruined, rng, out)
            o['theme'] = next((c for m in pieces[o['n']] for c in sv.src.get(m.key, ())), None)
            continue
        if wanted and not wrecked and not o.get('pick') and _furnish(ts, sv, o, pieces[o['n']], squares, wanted, every - wanted, ruined, rng, out):
            continue
        cell = o.get('pick') or _theme(sv, pieces[o['n']], wanted, every - wanted, rng)
        o['theme'] = cell
        for m in pieces[o['n']]:
            here = [st for c, st in zip(sv.src.get(m.key, ()), sv.sets.get(m.key, ())) if c == cell]
            if here:
                _put_set(sv, rng.choice(here), m, ruined or wrecked, rng, out, WRECK_KEPT if wrecked else 1.0)
        if wrecked:
            wrecks.add(o['n'])
    if ruined:
        _rubble(sv, plan, made, out, rng)
    if wrecks:
        _rubble(sv, plan, [m for m in made if m.owner in wrecks], out, rng, WRECK_RUBBLE, WRECK_HEAPS)
    _even_out_lights(ts, sv, plan, made, out, rng, only)
    _not_a_showroom(ts, sv, plan, out, rng)
    _no_clashes(sv, out)
    keep_fronts(ts, plan, out)
    return out


def _drop(items, gone):
    """Takes these out, and the small things standing on them: a cup doesn't stay in the air when its table goes."""
    if not gone:
        return
    out = [it for it in items if id(it) in gone]
    keep = []
    for it in items:
        if id(it) in gone:
            continue
        if it.what not in BIG_KINDS and it.what not in ('light', 'door', 'exit') and any(
                it.owner == g.owner and abs(it.p[0] - g.p[0]) < 64 and abs(it.p[1] - g.p[1]) < 64 and 0 < it.p[2] - g.p[2] < 120 for g in out if g.what in BIG_KINDS):
            continue
        keep.append(it)
    items[:] = keep


def _not_a_showroom(ts, sv, plan, items, rng):
    """The same thing on every square looks like a mistake: a real room's one pool table stood on each piece that was like the
    one it stood on. Of any furnishing, no more than a real room usually has and no more than the room has squares for; of small
    things, not a heap of them."""
    _rooms, usual = real_rooms(sv)
    per = collections.defaultdict(list)
    for it in items:
        if it.owner is not None and it.what not in ('light', 'door', 'exit', 'rubble'):
            one = set(words_of(sv.info.get(it.key, ('', (), ''))[2] or '')) & set(ONE_TO_A_ROOM) if it.what in BIG_KINDS else None
            per[(it.owner, sorted(one)[0] if one else it.key)].append(it)
    gone = set()
    for (owner, key), rows in per.items():
        squares = sum(1 for c in plan.owners[owner]['cells'] if c not in plan.air)
        if key in ONE_TO_A_ROOM:
            most = 1
        elif rows[0].what in BIG_KINDS:
            most = max(1, squares // SAME_THING)
            info = sv.info.get(key, ('thing', (), ''))
            if is_furnishing(info):
                most = min(most, max(1, usual.get(key, 1)))
        else:
            most = max(SAME_SMALL, squares // SAME_SMALL)
        if len(rows) > most:
            rng.shuffle(rows)
            gone |= {id(it) for it in rows[most:]}
    _drop(items, gone)


def _no_clashes(sv, items):
    """Sets from different real rooms may reach over a piece's edge into each other: the first one stays."""
    seen = collections.defaultdict(list)
    gone = set()
    for it in items:
        if it.what not in ('furn', 'cont', 'term') and not (it.what in BIG_KINDS and is_furnishing(sv.info.get(it.key, ('thing', (), '')))):
            continue
        cell = (int(it.p[0] // 128), int(it.p[1] // 128), int(it.p[2] // 128))
        hit = False
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for q in seen.get((cell[0] + a, cell[1] + b, cell[2]), ()):
                    if q.piece is not it.piece and abs(q.p[0] - it.p[0]) < CLASH and abs(q.p[1] - it.p[1]) < CLASH:
                        hit = True
        if hit:
            gone.add(id(it))
        else:
            seen[cell].append(it)
    _drop(items, gone)


def keep_fronts(ts, plan, items):
    """Nothing solid in a doorway or just inside one: the way into a room is what it's judged by, and it's what a follower
    gets stuck on. Things overhead are no trouble."""
    step = ts.step
    zones = []
    for link in plan.links:
        a, b = tuple(link)
        x, y = plan.cells.get(a), plan.cells.get(b)
        if x == y or x is None or y is None or a[2] != b[2]:
            continue
        for c, n in ((a, b), (b, a)):
            dx, dy = n[0] - c[0], n[1] - c[1]
            mx, my = (c[0] + dx * 0.5) * step, (c[1] + dy * 0.5) * step
            zones.append((mx, my, dx, dy, c[2] * plan.rise + ts.floor))
    if not zones:
        return
    gone = set()
    for it in items:
        hit = False
        if it.what in SOLID:
            for mx, my, dx, dy, floor in zones:
                if it.p[2] - floor >= HUNG or it.p[2] < floor - 64:
                    continue
                ahead = (mx - it.p[0]) * dx + (my - it.p[1]) * dy     # (how far back from the doorway, into the room)
                side = abs((it.p[0] - mx) * dy) + abs((it.p[1] - my) * dx)
                if -32 <= ahead <= DOOR_FRONT and side <= DOOR_SIDE:
                    hit = True
                    break
        if hit:
            gone.add(id(it))
    _drop(items, gone)


def _rubble(sv, plan, made, out, rng, share=RUBBLE_SHARE, least=0):
    """A ruin has more on the floor than any one room of the game's: heaps from its own sets, here and there in the rooms,
    never in a corridor or a doorway (clear_ways has the last word)."""
    heaps = sorted({it[0]: it for sets in sv.sets.values() for st in sets for it in st if sv.info.get(it[0], ('',))[0] == 'rubble' and abs(it[3]) < 32}.values())
    if not heaps:
        return
    done = collections.Counter()
    tiles = list(made)
    rng.shuffle(tiles)
    for m in tiles:
        o = plan.owners[m.owner]
        if o['kind'] != ROOM_KIND or plan.need(m.cell).count('o') < (2 if least else 3) or 'p' in plan.need(m.cell) or (done[m.owner] >= least and rng.random() > share):
            continue
        it = rng.choice(heaps)
        spot = _world(m, rng.uniform(-70, 70), rng.uniform(-70, 70), it[3], it[4], it[5], rng.uniform(0, 6.28))
        out.append(Item(it[0], spot, it[7], 'rubble', m.owner, m))
        done[m.owner] += 1


def _even_out_lights(ts, sv, plan, made, items, rng, only=None):
    """Every room and corridor lit, none blazing: the game's lights from the game's sets for these same pieces."""
    per = collections.defaultdict(list)
    for it in items:
        if it.what == 'light':
            per[it.owner].append(it)
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    for o in plan.owners:
        if o['kind'] == VOID_KIND or (only is not None and o['n'] != only):
            continue
        n = sum(1 for c in o['cells'] if c not in plan.air)
        least, most = max(1, n // LIGHTS_PER), max(1, n // LIGHTS_MAX)
        have = per[o['n']]
        while len(have) > most:
            drop = have.pop(rng.randrange(len(have)))
            items.remove(drop)
        tiles = list(pieces[o['n']])
        rng.shuffle(tiles)
        for m in tiles:
            if len(have) >= least:
                break
            got = [s for s in sv.sets.get(m.key, ()) if any(sv.info.get(i[0], ('',))[0] == 'light' for i in s)]
            if not got:
                continue
            s = rng.choice(got)
            for it in s:
                info = sv.info.get(it[0], ('thing',))
                # (the light with what holds it up: things hung high)
                if info[0] == 'light' or (info[0] == 'stat' and it[3] > 96):
                    made_item = Item(it[0], _world(m, it[1], it[2], it[3], it[4], it[5], it[6]), it[7], info[0], o['n'], m)
                    items.append(made_item)
                    if info[0] == 'light':
                        have.append(made_item)


def item_refs(game, items):
    """Items in the form navgen reads. Doors are left out: they open."""
    out = []
    for n, it in enumerate(items):
        if it.what in SOLID:
            out.append({'ref': 100000 + n, 'type': 'REFR', 'base': game.from_key(it.key), 'pos': tuple(it.p[:3]), 'rot': tuple(it.p[3:6]), 'scale': it.s, 'leads': False, 'bkey': it.key})
    return out


def clear_ways(game, ts, plan, made, items, walk_check, cache=None, rounds=6):
    """Whatever stands in the way comes out: walk it with everything in place, and if part can't be reached, take out what's
    solid on those squares; only if that's nothing, what's solid on the squares beside them, and at the last all of it. A machine
    filling a square costs that machine, not the room's whole contents. Returns the walk."""
    w = None
    step = ts.step

    def on(it, squares):
        c = it.piece.cells[0]
        return (int(math.floor(it.p[0] / step + 0.5)), int(math.floor(it.p[1] / step + 0.5)), c[2]) in squares
    for _ in range(rounds):
        w = walk_check(game, ts, plan, made, cache, item_refs(game, items))
        if not w['missing'] and not w['escaped']:
            return w
        lost = set(w['missing'])
        near = set()
        for c in lost:
            for d in range(4):
                near.add((c[0] + K.DX[d][0], c[1] + K.DX[d][1], c[2]))
        near |= lost
        solid = [it for it in items if it.what in SOLID and it.piece is not None]
        gone = {id(it) for it in solid if on(it, lost)} or {id(it) for it in solid if on(it, near)} or {id(it) for it in items if it.what in SOLID}
        _drop(items, gone)
    return w


def item_ops(items, origin=(0.0, 0.0, 0.0)):
    out = []
    for it in items:
        op = {'op': 'add', 'gen': True, 'base': it.key, 'p': [origin[0] + it.p[0], origin[1] + it.p[1], origin[2] + it.p[2], it.p[3], it.p[4], it.p[5]], 's': it.s}
        if it.what == 'exit':
            op['exit'] = True
        if it.extra:
            op['extra'] = it.extra
        out.append(op)
    return out
