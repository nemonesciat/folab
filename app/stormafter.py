"""What a big storm leaves, and who hides from it (the user, 21 Nov 2026: "yes, all those please"; stormsched.py runs it).

Wrack (`wrack_ops`): after a big storm the beaches carry what the sea threw up, the game's own driftwood logs, branch
piles, beams, planks, pallets, tyres, barrels, broken crates and now and then a small boat (`WRACK`), in clusters along the
wet sand (`shore_points`: sand ground, low, with the sea within `SEA_NEAR`), and now and then something worth opening
(`LOOT`: copies of the game's duffle bag, suitcase and damaged shipping crates that refill when their cell resets, so each
storm can bring new finds). Every piece has one persistent parent marker (`PARENT`, off at the start); the storm script
switches it on when the storm's second half begins and off a day or two after it ends, when you are not out on the island
(stormsched.WRACK_*). Lying things follow the sand's slope (osmdress.lie); nothing on roads, in buildings or landmarks,
or within `CLEAR` of anything already standing.

Shelter (`shelter_ops`): the island's ordinary people (`WHO`: surfers, locals, the Huang's farmers, three storekeepers)
each get a link to a marker just inside the nearest building with a way in (an unlocked door linked to a place of the
mod's own with a navmesh, within `REACH`, at most `ROOM` people a place), and one package first in their list: the game's
sandbox round a linked marker, only while the global `FLAG` is 1, which the storm script raises from the building step to
the storm's end. Guards, fighters, pirates and the quests' people stay where they are.

    ops(gd, pr)    (ops, report): all of it as one Undo, the storm script recompiled with both (the mod must have its storms)"""
import json
import math
import random
import re

import recordio

WORLD = 'FOLabWaikiki'
PARENT = 'FOLabStormWrack'
FLAG = 'FOLabStormShelter'
PACKAGE = 'FOLabStormShelterPackage'
PACKAGE_FROM = ('DefaultSandboxLinkedMarker512', 'DefaultSandboxLinkedMarker512NoSleepNoWanderNoChat')

# (editor ID, weight, smallest, biggest, sunk by)
WRACK = [
    ('TreeWastelandHardwoodLog01', 6, 0.7, 1.2, 6), ('CampLog01', 5, 0.8, 1.3, 3), ('CampLog02', 4, 0.8, 1.3, 3),
    ('CampLog03', 4, 0.8, 1.3, 3), ('TreeWastelandBranchPile01', 5, 0.6, 1.0, 4), ('TreeWastelandBranchPile02', 4, 0.6, 1.0, 4),
    ('WoodBeam01', 3, 0.8, 1.0, 2), ('WoodBeam02', 2, 0.8, 1.0, 2), ('WoodPlanks01NV', 5, 0.9, 1.1, 1),
    ('WoodPlanks02NV', 4, 0.9, 1.1, 1), ('WoodPaletteNV', 3, 0.9, 1.0, 2), ('Tire01Static', 3, 1.0, 1.0, 4),
    ('Tire02Static', 2, 1.0, 1.0, 4), ('Barrel03static', 2, 1.0, 1.0, 6), ('NVDLC04MilitaryCrateBroken01', 2, 0.9, 1.0, 4),
    ('NVDLC04MilitaryCrateBroken02', 2, 0.9, 1.0, 4), ('NVDLC04BurntCrate', 1, 0.9, 1.0, 4), ('NVWoodSpool', 1, 0.9, 1.0, 4),
    ('GroundLitterPile01', 3, 0.8, 1.2, 1),
]
BOATS = ['Boat01a', 'Boat02a', 'Boat03a']      # (one in BOAT_EVERY clusters, alone)
# washed-up finds: (game container, weight); each copied as a container of the mod's own that refills (respawn flag)
LOOT = [('NVDuffleBagRandomLoot', 4), ('NVDLC02SuitcasezGen01', 2), ('NVDLC02SuitcasezGen02', 2),
        ('NVDLC04LootCrateShippingDamaged01', 2), ('NVDLC04LootCrateShippingDamaged03', 2), ('NVDLC04LootCrateShippingDamaged05', 1)]
RESPAWN = 0x02

SEA_NEAR = 512.0        # (sand this near the sea: the wrack line)
LOW = (8.0, 200.0)      # (sand this high over the sea, no higher)
STEEP = 0.35
APART = 650.0           # (clusters this far apart)
CLUSTER = (2, 6)        # (pieces in a cluster)
SPREAD = 260.0          # (how far round its middle a cluster's pieces lie)
CLEAR = 140.0           # (kept this far from anything already standing)
LOOT_EVERY = 6          # (a find in one cluster in this many)
BOAT_EVERY = 25
MOST = 650              # (pieces in all, the finds and boats among them)

WHO = re.compile(r'^FOLabSurfer|^FOLabWaikikiLocal|^FOLabHuangFolk|^FOLabWaikiki(Gunsmith|Grocer|Trader)$')
REACH = 7500.0          # (a shelter's door this near, no further: about 100 m, a walk in a storm)
ROOM = 14               # (people a place takes)
INSIDE = 96.0           # (the marker this far in from the arrival point, away from the door)


class Keys:
    """The keys record_new and add ops will get, in the order they are made (both take the mod's next id)."""

    def __init__(self, pr):
        self.n = pr.next_id

    def take(self):
        k = '+%06X' % self.n
        self.n += 1
        return k


def _game_forms(gd, tag, names):
    want, got = {n.lower(): n for n in names}, {}
    for f, (_i, r) in gd.forms.items():
        if r.tag == tag:
            e = gd.edid(f)
            if e and e.lower() in want:
                got.setdefault(want[e.lower()], f)
    return got


def _sub(tag, label, kind, value):
    return {'tag': tag, 'label': label, 'kind': kind, 'value': value}


def _num_sub(tag, label, name, code, value):
    return {'tag': tag, 'label': label, 'kind': 'struct', 'fields': [{'name': name, 'code': code, 'value': value}]}


# ---------- wrack ----------

def shore_points(gd, pr, world, step=128):
    """[(x, y, z)]: points of sand a little over the sea with the sea near, as the game draws the ground."""
    import land
    import understory
    grid = gd.grid(world)
    tex_class, cache, out = {}, {}, []
    near = int(SEA_NEAR // 128)
    for xy, c in grid.items():
        ck = gd.key(c)
        form = pr.land.get(ck)
        if not form:
            e = gd.land_at(world, *xy)
            form = land.decode(gd, e, cache) if e else None
        if not form or not form.get('h'):
            continue
        h = form['h']
        if min(h) >= 8 or max(h) < LOW[0]:
            continue                        # (no sea in this cell, or nothing above it)
        for q, quarter in enumerate(form['q']):
            qx, qy = (q % 2) * 16, (q // 2) * 16
            for pj in range(0, 16, step // 128):
                for pi in range(0, 16, step // 128):
                    gi, gj = qx + pi, qy + pj
                    z = h[gj * 33 + gi]
                    if not LOW[0] <= z <= LOW[1]:
                        continue
                    if not any(h[b * 33 + a] < 8 for a in range(max(0, gi - near), min(33, gi + near + 1))
                               for b in range(max(0, gj - near), min(33, gj + near + 1))):
                        continue
                    t = understory._top(quarter, pi, pj)
                    if t not in tex_class:
                        try:
                            e = recordio.field(pr.records[t], 'EDID') if t and t.startswith('+') and t in pr.records else (gd.edid(gd.from_key(t)) if t else 'default')
                        except Exception:
                            e = ''
                        tex_class[t] = understory.class_of(e)
                    if tex_class[t] != 'sand':
                        continue
                    out.append((xy[0] * 4096 + gi * 128, xy[1] * 4096 + gj * 128, float(z)))
    return out


class _Taken:
    """Where things stand already (the mod's and the game's), by 512-unit square."""

    def __init__(self, gd, pr, world):
        import understory
        self.g = understory._Grid()
        grid = gd.grid(world)
        keys = {gd.key(c) for c in grid.values()}
        removed = set()
        for ck in keys:
            for rk, r in pr.cells.get(ck, {}).get('refs', {}).items():
                if r.get('removed'):
                    removed.add(rk)
                elif r.get('p'):
                    self.g.add(r['p'][0], r['p'][1])
        self.grid, self.removed = grid, removed

    def look(self, gd, xy):
        c = self.grid.get(xy)
        if c is None:
            return
        try:
            refs = gd.refs(c)
        except Exception:
            refs = ()
        for r in refs:
            if r.get('pos') and gd.key(r['ref']) not in self.removed:
                self.g.add(r['pos'][0], r['pos'][1])


def loot_record(gd, f):
    """A copy of a game container that refills when its cell resets."""
    rec = json.loads(json.dumps(recordio.load(gd, f)))
    e = recordio.field(rec, 'EDID')
    recordio.set_field(rec, 'EDID', 'FOLabWrack' + e, label='Editor ID')
    for s in rec['subs']:
        if s['tag'] == 'DATA':
            for fl in s['fields']:
                if fl.get('name') == 'Flags':
                    fl['value'] = int(fl['value']) | RESPAWN
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
    rec['src'] = ''
    rec['flags'] = 0
    return rec


def wrack_ops(gd, pr, keys, world=WORLD, seed=7, cat=None, progress=None):
    """(ops, report, parent key). keys: a Keys, shared with whatever ops come before and after."""
    import landmarks
    import osmdress
    import roadgen
    import understory
    rng = random.Random(seed)
    forms = _game_forms(gd, 'STAT', [e for e, *_r in WRACK] + BOATS)
    pieces = [row for row in WRACK if row[0] in forms]
    boats = [b for b in BOATS if b in forms]
    loot_forms = _game_forms(gd, 'CONT', [e for e, _w in LOOT])
    out = []
    loot_keys = []
    for e, w in LOOT:
        if e in loot_forms:
            k = keys.take()
            out.append({'op': 'record_new', 'record': loot_record(gd, loot_forms[e])})
            loot_keys.append((k, w, e))
    if progress:
        progress('Finding the wet sand', 0, 1)
    pts = shore_points(gd, pr, world)
    rng.shuffle(pts)
    grid = gd.grid(world)
    on_road = understory._roads(gd, pr, world, {gd.key(c) for c in grid.values()})
    if cat is None:
        import server
        import townbuild
        cat = townbuild.load(gd, server.kits_folder())
    built = osmdress._Stands(osmdress.standing(gd, pr, world, cat), margin=80.0)
    in_mark = understory._in_boxes(list(landmarks.standing(gd, pr, world)))
    ground = roadgen.Ground(gd, pr, world)
    taken = _Taken(gd, pr, world)
    looked = set()
    marker = gd.key(_game_forms(gd, 'STAT', ['XMarker'])['XMarker'])
    parent = keys.take()
    adds, mids, n_loot, n_boat = [], [], 0, 0
    why = {'near a cluster': 0, 'road': 0, 'built': 0, 'taken': 0, 'steep': 0}

    def ok(x, y):
        xy = (int(x // 4096), int(y // 4096))
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                if (xy[0] + a, xy[1] + b) not in looked:
                    looked.add((xy[0] + a, xy[1] + b))
                    taken.look(gd, (xy[0] + a, xy[1] + b))
        if on_road(x, y):
            why['road'] += 1
            return None
        if built.hit(x, y) or in_mark(x, y):
            why['built'] += 1
            return None
        if taken.g.near(x, y, CLEAR):
            why['taken'] += 1
            return None
        z = ground.at(x, y)
        if z is None or z < LOW[0]:
            return None
        zs = [ground.at(x + dx, y + dy) for dx, dy in ((96, 0), (-96, 0), (0, 96), (0, -96))]
        if None in zs or max(abs(zs[0] - zs[1]), abs(zs[2] - zs[3])) / 192.0 > STEEP:
            why['steep'] += 1
            return None
        return z

    for n, (x, y, _z) in enumerate(pts):
        if len(adds) >= MOST:
            break
        if any((x - a) ** 2 + (y - b) ** 2 < APART * APART for a, b in mids):
            why['near a cluster'] += 1
            continue
        if ok(x, y) is None:
            continue
        mids.append((x, y))
        cluster = len(mids)
        if boats and cluster % BOAT_EVERY == 0:
            todo = [('boat', rng.choice(boats))]
        else:
            todo = [('piece', None) for _k in range(rng.randint(*CLUSTER))]
            if loot_keys and cluster % LOOT_EVERY == 0:
                todo[0] = ('loot', None)
        for m, (kind, what) in enumerate(todo):
            px, py = x, y
            if m:
                a, d = rng.uniform(0, math.tau), rng.uniform(40.0, SPREAD)
                px, py = x + math.cos(a) * d, y + math.sin(a) * d
            z = ok(px, py)
            if z is None:
                continue
            yaw = rng.uniform(0, math.tau)
            if kind == 'loot':
                pick = rng.random() * sum(w for _k, w, _e in loot_keys)
                for base, w, e in loot_keys:
                    pick -= w
                    if pick <= 0:
                        break
                rx, ry, rz = 0.0, 0.0, yaw
                s, sink = 1.0, 2.0
                n_loot += 1
            elif kind == 'boat':
                base, e = gd.key(forms[what]), what
                rx, ry, rz = osmdress.lie(ground, 'pile', px, py, yaw, 3.0)
                s, sink = 1.0, 10.0
                n_boat += 1
            else:
                pick = rng.random() * sum(row[1] for row in pieces)
                for e, w, smin, smax, sink in pieces:
                    pick -= w
                    if pick <= 0:
                        break
                base = gd.key(forms[e])
                s = rng.uniform(smin, smax)
                rx, ry, rz = osmdress.lie(ground, e, px, py, yaw, s)
                sink *= s
            cell = grid.get((int(px // 4096), int(py // 4096)))
            if cell is None:
                continue
            adds.append({'op': 'add', 'cell': gd.key(cell), 'base': base, 's': round(s, 3),
                         'p': [round(px, 1), round(py, 1), round(z - sink, 1), round(rx, 4), round(ry, 4), round(rz, 4)],
                         'extra': {'props': {'parent': {'ref': parent, 'opposite': False, 'popin': False}}}, '_what': e, '_kind': kind})
            taken.g.add(px, py)
    if not adds:
        keys.n -= 1                             # (the parent's key, not used after all)
        return out, {'pieces': 0, 'clusters': 0, 'shore points': len(pts), 'passed': why}, None
    x0, y0 = mids[0]
    out.append({'op': 'add', 'cell': adds[0]['cell'], 'base': marker,
                'p': [x0, y0, (ground.at(x0, y0) or 0.0) - 200.0, 0.0, 0.0, 0.0], 's': 1.0,
                'extra': {'persistent': True, 'edid': PARENT, 'props': {'disabled': True}}})
    by, spots = {}, []
    for o in adds:
        by[o['_what']] = by.get(o['_what'], 0) + 1
        spots.append((o['p'][0], o['p'][1], o.pop('_kind')))
        o.pop('_what')
        keys.take()
    out += adds
    return out, {'pieces': len(adds), 'clusters': len(mids), 'finds': n_loot, 'boats': n_boat, 'shore points': len(pts),
                 'by': by, 'passed': why, 'spots': spots}, parent


# ---------- shelter ----------

def _interior(pr, ck):
    rec = pr.records.get(ck)
    if not rec or rec.get('type') != 'CELL':
        return False
    for s in rec['subs']:
        if s['tag'] == 'DATA':
            v = s.get('fields', [{}])[0].get('value', 0) if s.get('kind') == 'struct' else 0
            return bool(int(v or 0) & 1)
    return False


def _locked(r):
    lock = (r.get('props') or {}).get('lock')
    return bool(lock) and int(lock.get('level', 0) or 0) > 0


def shelters(gd, pr, world=WORLD):
    """[(x, y, place key, (ax, ay, az, rz))]: outside doors of the island that lead, unlocked both ways, into a place of
    the mod's own with a navmesh; the arrival point inside."""
    grid = gd.grid(world)
    outside = {gd.key(c) for c in grid.values()}
    where = {}
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            for rk in c.get('refs', {}):
                where[rk] = ck
    out = []
    for ck in outside:
        for rk, r in pr.cells.get(ck, {}).get('refs', {}).items():
            t = r.get('tel')
            if not t or not r.get('p') or r.get('removed') or _locked(r):
                continue
            inside = where.get(t.get('door'))
            if not inside or not _interior(pr, inside) or inside not in pr.navmesh:
                continue
            if _locked(pr.cells[inside]['refs'].get(t['door'], {})):
                continue
            ap = t['p']
            out.append((r['p'][0], r['p'][1], inside, (ap[0], ap[1], ap[2], ap[5] if len(ap) > 5 else 0.0)))
    return out


def package_record(gd, flag_key):
    """The game's sandbox round a linked marker, only while the shelter flag is 1."""
    import questrec
    got = _game_forms(gd, 'PACK', PACKAGE_FROM)
    src = next(got[n] for n in PACKAGE_FROM if n in got)
    rec = json.loads(json.dumps(recordio.load(gd, src)))
    recordio.set_field(rec, 'EDID', PACKAGE, label='Editor ID')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'CTDA']
    cond = questrec.condition_sub({'op': '=', 'fn': 74, 'p1': flag_key, 'p2': 0, 'run': 0, 'ref': '', 'value': 1.0})
    at = next((i for i, s in enumerate(rec['subs']) if s['tag'] in ('PKDD', 'PKE2', 'PKPT', 'PKED', 'CNAM', 'IDLF', 'POBA')), len(rec['subs']))
    rec['subs'].insert(at, cond)
    rec['src'] = ''
    rec['flags'] = 0
    return rec, gd.edid(src)


def flag_record():
    return {'type': 'GLOB', 'flags': 0, 'src': '', 'subs': [
        _sub('EDID', 'Editor ID', 'z', FLAG), _num_sub('FNAM', 'Type', 'Type', 'B', ord('s')),
        _num_sub('FLTV', 'Value', 'Value', 'f', 0.0)]}


def shelter_ops(gd, pr, keys, flag_key, world=WORLD):
    """(ops, report): the package (first in each sheltering person's list), a marker in each place used, the links."""
    import api_characters as ac
    out = []
    pack_key = keys.take()
    pack, pack_from = package_record(gd, flag_key)
    out.append({'op': 'record_new', 'record': pack})
    bases = {k for k, r in pr.records.items() if r.get('type') == 'NPC_' and WHO.search(recordio.field(r, 'EDID') or '')}
    for k in sorted(bases):
        rec = json.loads(json.dumps(pr.records[k]))
        rec['subs'] = [s for s in rec['subs'] if not (s['tag'] == 'PKID' and s.get('value') == pack_key)]
        first = next((i for i, s in enumerate(rec['subs']) if s['tag'] == 'PKID'), None)
        sub = {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': pack_key}
        if first is None:
            ac.insert(rec, sub)
        else:
            rec['subs'].insert(first, sub)
        out.append({'op': 'record', 'key': k, 'record': rec})
    grid = gd.grid(world)
    outside = {gd.key(c) for c in grid.values()}
    people = [(ck, rk, r['p']) for ck in outside for rk, r in pr.cells.get(ck, {}).get('refs', {}).items()
              if r.get('base') in bases and r.get('p') and not r.get('removed') and not r.get('link')]
    doors = shelters(gd, pr, world)
    by_sq = {}
    for d in doors:
        by_sq.setdefault((int(d[0] // 2048), int(d[1] // 2048)), []).append(d)
    marker = gd.key(_game_forms(gd, 'STAT', ['XMarker'])['XMarker'])
    used, marks, links, alone, pairs = {}, {}, [], 0, []
    for ck, rk, p in people:
        near = []
        i, j = int(p[0] // 2048), int(p[1] // 2048)
        for a in range(i - 2, i + 3):
            for b in range(j - 2, j + 3):
                for d in by_sq.get((a, b), ()):
                    dist = math.hypot(d[0] - p[0], d[1] - p[1])
                    if dist <= REACH:
                        near.append((dist, d))
        near.sort(key=lambda v: v[0])
        pick = next((d for _dist, d in near if used.get(d[2], 0) < ROOM), None)
        if pick is None:
            alone += 1
            continue
        place = pick[2]
        used[place] = used.get(place, 0) + 1
        if place not in marks:
            ax, ay, az, rz = pick[3]
            mk = keys.take()
            marks[place] = mk
            out.append({'op': 'add', 'cell': place, 'base': marker, 's': 1.0,
                        'p': [round(ax + math.sin(rz) * INSIDE, 1), round(ay + math.cos(rz) * INSIDE, 1), round(az, 1), 0.0, 0.0, round(rz, 4)],
                        'extra': {'persistent': True}})
        links.append({'op': 'ref_set', 'cell': ck, 'ref': rk, 'set': {'link': marks[place]}})
        pairs.append((round(p[0]), round(p[1]), round(pick[0]), round(pick[1])))
    out += links
    return out, {'package': pack_key, 'package from': pack_from, 'people': len(people), 'sheltered': len(links),
                 'no shelter near': alone, 'places': len(marks), 'doors': len(doors), 'kinds': len(bases), 'pairs': pairs}


# ---------- both ----------

def ops(gd, pr, world=WORLD, seed=7, cat=None, progress=None, L=None):
    """(ops, report): the shelter flag, wrack, shelter, and the storm script recompiled to drive them. One Undo."""
    import api_scripts
    import stormsched as S
    L = L or S.REAL
    if isinstance(world, str):
        world = S._world(gd, world)
    sk = next((k for k, r in pr.records.items() if r.get('type') == 'SCPT' and recordio.field(r, 'EDID') == 'FOLabStormScript'), None)
    if sk is None:
        raise ValueError('the mod has no storms yet (stormsched.ops first)')
    if any(r.get('type') == 'GLOB' and recordio.field(r, 'EDID') == FLAG for r in pr.records.values()):
        raise ValueError('the mod already has what the storms leave (%s)' % FLAG)
    keys = Keys(pr)
    flag_key = keys.take()
    out = [{'op': 'record_new', 'record': flag_record()}]
    w_ops, w_rep, parent = wrack_ops(gd, pr, keys, world, seed, cat, progress)
    out += w_ops
    s_ops, s_rep = shelter_ops(gd, pr, keys, flag_key, world)
    out += s_ops
    extra = {flag_key: out[0]['record']}
    if parent:
        extra[parent] = {'type': 'REFR', 'flags': 0x400, 'subs': [_sub('EDID', 'Editor ID', 'z', PARENT)]}
    view = None
    for c in pr.cells.values():                 # (refs placed in cells are not records: the compiler is told of it)
        for rk, r in c.get('refs', {}).items():
            if r.get('edid') == 'FOLabStormViewRain':
                view = 'FOLabStormViewRain'
                extra[rk] = {'type': 'REFR', 'flags': 0x400, 'subs': [_sub('EDID', 'Editor ID', 'z', view)]}
    text = S.script_source(L, view_parent=view, wrack=PARENT if parent else None, shelter=FLAG)
    c = api_scripts.scripts().compile(text, sk, 'quest', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the storm script does not compile: %s' % (c,))
    rec = api_scripts.scripts()._record_of(c, 'FOLabStormScript')
    out.append({'op': 'record', 'key': sk, 'record': rec})
    return out, {'wrack': w_rep, 'shelter': s_rep, 'script_bytes': len(c.data), 'script': sk, 'flag': flag_key, 'parent': parent}
