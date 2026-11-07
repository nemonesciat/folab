"""What the game stands in its kit pieces: doors, lights, furniture, containers and clutter, read from every interior in
each piece's own frame. A generated place copies those patterns, each piece getting a whole set one real piece had (or
nothing, as often as the game leaves it bare), so lights and clutter sit where the mesh has room for them.

    survey(game, kits)                  {kit: Survey}, kept on disk per game files' hash by load()
    survey.sets[piece key]              [[item, ...], ...] one list for each real piece, empties included
    survey.doors[piece key]             [(door key, x, y, z, rot, count)] doors that stand in this piece, no destination
    survey.exits                        the same for doors that lead somewhere: [(host word, door key, pose, count)]

An item is (base key, x, y, z, rx, ry, rz, scale, what) in the piece's frame; what says if it's a light, furniture, a
container, a thing, or rubble, and tags (from words in its name) let a room's purpose choose among sets."""
import collections
import json
import math
import os
import random

import kitindex as K

COPY = {'LIGH': 'light', 'FURN': 'furn', 'CONT': 'cont', 'MISC': 'thing', 'ALCH': 'loot', 'AMMO': 'loot', 'BOOK': 'thing', 'WEAP': 'loot',
        'ARMO': 'loot', 'TERM': 'term', 'MSTT': 'stat', 'STAT': 'stat', 'ACTI': 'act', 'IDLM': 'stat', 'ADDN': 'stat'}
SKIP_WORDS = ('marker', 'xmarker', 'trigger', 'collision', 'fxlight', 'editor', 'roomportal', 'occlusion', 'cubemap', 'test', 'sound', 'door', 'teleport', 'dummy', 'aaa')
MAX_SETS = 120          # (of each piece: more than this adds nothing)
LOOT_KEPT = 0.25        # (weapons, ammo and aid: the game's rooms were balanced for its own places, not for a copy in every room)
MAX_ITEMS = 14          # (a set with more than this is a room's whole contents heaped on one piece: not copied)
VOID_KIND, ROOM_KIND = 'void', 'room'
RUBBLE_WORDS = ('rubble', 'debris', 'rock', 'wreck', 'pile', 'junk', 'trash', 'scrap', 'plank', 'collapsed', 'chunk', 'brick')
TAGS = {'sleep': ('bed', 'bunk', 'mattress', 'cot', 'pillow', 'sleep', 'locker', 'dresser', 'nightstand', 'wardrobe'),
        'desk': ('desk', 'terminal', 'computer', 'filing', 'file', 'paper', 'clipboard', 'typewriter', 'folder', 'office', 'chairswivel', 'chair'),
        'eat': ('table', 'food', 'plate', 'fork', 'knife', 'spoon', 'cup', 'mug', 'kitchen', 'stove', 'fridge', 'nuka', 'can', 'cooking', 'sink', 'tray'),
        'machine': ('machin', 'reactor', 'generator', 'pipe', 'console', 'control', 'panel', 'gauge', 'tank', 'conduit', 'turbine', 'valve', 'fuse', 'pump', 'tool', 'wrench'),
        'store': ('crate', 'shelf', 'shelves', 'box', 'barrel', 'cabinet', 'storage', 'ammo', 'chest', 'safe', 'rack'),
        'care': ('medical', 'doctor', 'stimpak', 'surgery', 'gurney', 'clinic', 'autodoc', 'bandage', 'bloodpack')}
PURPOSE_TAGS = {'quarters': ('sleep',), 'small room': ('sleep', 'store'), 'office': ('desk',), 'workroom': ('machine', 'desk'), 'reactor': ('machine',),
                'far end': ('machine', 'store'), 'long room': ('eat', 'store', 'care'), 'atrium': ('eat',), 'hall': ('eat', 'desk'), 'entrance': ('store', 'machine'),
                'store': ('store',), 'mess': ('eat',), 'clinic': ('care',), 'corridor': (),
                'under a balcony': ('store', 'eat'), 'over a balcony': ('desk', 'sleep')}


def tags_of(edid):
    e = edid.lower()
    return sorted(t for t, words in TAGS.items() if any(w in e for w in words))


class Survey:
    def __init__(self):
        self.sets = collections.defaultdict(list)       # piece -> [[item]]
        self.src = collections.defaultdict(list)        # piece -> [cell each set came from]
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
        for pl in placed:
            s = out.setdefault(pl['kit'], Survey())
            s.sets[pl['p'].key].append(pl['items'] if len(pl['items']) <= MAX_ITEMS else [])
            s.src[pl['p'].key].append(cell)
    rng = random.Random(1)
    for s in out.values():
        for k, v in s.sets.items():
            if len(v) > MAX_SETS:
                both = list(zip(v, s.src[k]))
                rng.shuffle(both)
                del both[MAX_SETS:]
                s.sets[k], s.src[k] = [b[0] for b in both], [b[1] for b in both]
    return out


def to_json(data):
    return {n: {'sets': s.sets, 'src': s.src, 'info': s.info, 'doors': {k: [list(p) + [c] for p, c in v.items()] for k, v in s.doors.items()},
                'exits': {k: [list(p) + [c] for p, c in v.items()] for k, v in s.exits.items()}} for n, s in data.items()}


def from_json(d):
    out = {}
    for n, v in d.items():
        s = out[n] = Survey()
        s.sets = collections.defaultdict(list, {k: [[tuple(i) for i in st] for st in sets] for k, sets in v['sets'].items()})
        s.src = collections.defaultdict(list, v['src'])
        s.info = {k: tuple(i) for k, i in v['info'].items()}
        s.doors = collections.defaultdict(collections.Counter, {k: collections.Counter({tuple(p[:5]): p[5] for p in rows}) for k, rows in v['doors'].items()})
        s.exits = collections.defaultdict(collections.Counter, {k: collections.Counter({tuple(p[:5]): p[5] for p in rows}) for k, rows in v['exits'].items()})
    return out


def load(game, kits, folder):
    """The survey for these game files: from folder if it was made before."""
    path = os.path.join(folder, 'dressing.json')
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
    __slots__ = ('key', 'p', 's', 'what', 'owner', 'piece')

    def __init__(self, key, p, s, what, owner, piece=None):
        self.key, self.p, self.s, self.what, self.owner, self.piece = key, p, s, what, owner, piece


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
        if VOID_KIND in (ka, kb) or ROOM_KIND not in (ka, kb) or rng.random() > share:
            continue
        # (from the room's side)
        c, n = (a, b) if ka == ROOM_KIND else (b, a)
        m = by.get(c)
        if not m:
            continue
        d = next(i for i in range(4) if (c[0] + K.DX[i][0], c[1] + K.DX[i][1]) == (n[0], n[1]))
        got = _door_in(ts, sv, table, m, d, rng)
        if got:
            # (one door style to a room's doors, as often as not)
            room = plan.cells[c]
            if room in style and any(style[room] == k[0] for k in table.get(_slot_width(ts, m, d) // 24, {})):
                got = (style[room], got[1])
            style.setdefault(room, got[0])
            out.append(Item(got[0], got[1], 1.0, 'door', plan.cells[c]))
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


def _theme(sv, pieces, wanted, unwanted, rng):
    """A real place for a room to take after: a place where these same pieces stood, with what the room is for in them.
    Everything in a room coming from one place is what makes it a room and not a heap."""
    scores = collections.defaultdict(float)
    for key in {m.key for m in pieces}:
        for cell, items in zip(sv.src.get(key, ()), sv.sets.get(key, ())):
            good = bad = 0
            for it in items:
                tags = set(sv.info.get(it[0], ('', ()))[1])
                good += bool(tags & wanted)
                bad += bool(tags & unwanted)
            scores[cell] += 1 + 4 * good - 1.5 * bad
    best = sorted(((v, c) for c, v in scores.items() if v > 0), reverse=True)[:6]
    if not best:
        return None
    return _pick([(c, v) for v, c in best], rng)


def dress(ts, sv, plan, made, rng, purposes=None, ruined=False):
    """Lights and things for every piece: each room takes after one real place, and each of its pieces gets what that piece
    had there (or nothing, as often as it had nothing). [Item]"""
    purposes = purposes or PURPOSE_TAGS
    out = []
    every = set(t for ws in PURPOSE_TAGS.values() for t in ws)
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    for o in plan.owners:
        if o['kind'] == VOID_KIND or not pieces[o['n']]:
            continue
        wanted = set(purposes.get(o.get('dress') or o['purpose'], ()))
        cell = _theme(sv, pieces[o['n']], wanted, every - wanted, rng)
        o['theme'] = cell
        for m in pieces[o['n']]:
            here = [st for c, st in zip(sv.src.get(m.key, ()), sv.sets.get(m.key, ())) if c == cell]
            if not here:
                continue
            for it in rng.choice(here):
                what = sv.info.get(it[0], ('thing',))[0]
                if what == 'rubble' and not ruined and rng.random() < 0.7 or what == 'loot' and rng.random() > LOOT_KEPT:
                    continue
                out.append(Item(it[0], _world(m, it[1], it[2], it[3], it[4], it[5], it[6]), it[7], what, m.owner, m))
    if ruined:
        _rubble(sv, plan, made, out, rng)
    _even_out_lights(ts, sv, plan, made, out, rng)
    return out


def _rubble(sv, plan, made, out, rng):
    """A ruin has more on the floor than any one room of the game's: heaps from its own sets, here and there in the rooms,
    never in a corridor or a doorway (clear_ways has the last word)."""
    heaps = sorted({it[0]: it for sets in sv.sets.values() for st in sets for it in st if sv.info.get(it[0], ('',))[0] == 'rubble' and abs(it[3]) < 32}.values())
    if not heaps:
        return
    for m in made:
        o = plan.owners[m.owner]
        if o['kind'] != ROOM_KIND or plan.need(m.cell).count('o') < 3 or 'p' in plan.need(m.cell) or rng.random() > RUBBLE_SHARE:
            continue
        it = rng.choice(heaps)
        spot = _world(m, rng.uniform(-70, 70), rng.uniform(-70, 70), it[3], it[4], it[5], rng.uniform(0, 6.28))
        out.append(Item(it[0], spot, it[7], 'rubble', m.owner, m))


def _even_out_lights(ts, sv, plan, made, items, rng):
    """Every room and corridor lit, none blazing: the game's lights from the game's sets for these same pieces."""
    per = collections.defaultdict(list)
    for it in items:
        if it.what == 'light':
            per[it.owner].append(it)
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    for o in plan.owners:
        if o['kind'] == VOID_KIND:
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
    solid in the pieces on the line between. Returns the walk."""
    w = None
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
        keep = []
        for it in items:
            if it.what in SOLID and it.piece is not None and any(c in near for c in it.piece.cells):
                continue
            keep.append(it)
        if len(keep) == len(items):
            keep = [it for it in items if it.what not in SOLID]
        items[:] = keep
    return w


def item_ops(items, origin=(0.0, 0.0, 0.0)):
    out = []
    for it in items:
        op = {'op': 'add', 'gen': True, 'base': it.key, 'p': [origin[0] + it.p[0], origin[1] + it.p[1], origin[2] + it.p[2], it.p[3], it.p[4], it.p[5]], 's': it.s}
        if it.what == 'exit':
            op['exit'] = True
        out.append(op)
    return out
