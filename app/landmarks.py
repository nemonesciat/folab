"""Landmarks and a harbour for a world made from a real map.

A landmark is one of the game's own great buildings, taken as the game stands it: every piece of it found where the game
placed them (the Lucky 38 is a base, a tower, two overhangs...), their places kept against each other, and the whole stood
somewhere else, turned and sized as asked. The ground under it is levelled, what the mod had there is cleared, and it is
moved a little off the spot if that keeps it out of a road or the sea. Some are put together here from single things
(`extra`), each seated as the game usually seats it.

A harbour is the map's piers (OpenStreetMap's man_made=pier) built of the game's dock pieces over the water, as high over
it as the game has them, with boats moored along them, some sunk, a barge or two.

Nothing here is copied into the mod but placements: the pieces are the game's records."""
import math
import random
import re
import struct

import roadgen

# set: what it's called, the world the game has it in, which things are its pieces (editor IDs, lower case), and things
# added round it: (editor ID, east, north of its middle, turn)
SETS = {
    # (its casino at the tower's foot is made to be seen from the Strip, half a round building: stood four times about the
    # tower it is a whole one. The tower's own shaft is open on one side too: the game's all-round tower, the one seen
    # from the desert, stands inside it, a wall wherever the shaft has none. From 58 parts in 100 wall at worst to 98)
    'lucky38': {'label': 'Lucky 38', 'world': 'TheStripWorldNew', 'match': r'^lucky38(b|base|top|overhang0[12]|stairlights)?$',
                'round': (r'^lucky38b?$', 4), 'inside': ('Lucky38WL', r'^lucky38top$', 133.0)},
    # (the game's own all-round Tops, the one seen from Freeside: whole from every side and solid to walk into. Its pieces
    # on the Strip are street fronts round a hollow, the hotel blocks on stilts where the casino isn't under them)
    'tops': {'label': 'The Tops', 'extra': [('TheTopsWL', 742, 1120, 0.0, -688.0)]},
    'tops_strip': {'label': 'The Tops (as on the Strip)', 'world': 'TheStripWorldNew', 'match': r'^thetops(casino|hotel)\d\d$'},
    # (a grand hotel of buildings that are whole from every side: the Ultra-Luxe and Gomorrah are fronts, open behind)
    'grandhotel': {'label': 'Grand hotel', 'extra': [('CasinoBoarded01', 0, 0, 0.0), ('ApartmentPre01', -2230, 0, 0.0), ('ApartmentPre01', 2230, 0, 3.1416),
                                                    ('HotelFountain01', 0, -2150, 0.0), ('FlagPole', -700, -1750, 0.0), ('FlagPole', 700, -1750, 0.0),
                                                    ('NVQueenPalm01', -1250, -1750, 0.0), ('NVQueenPalm01', 1250, -1750, 0.0),
                                                    ('NVQueenPalm01', -3300, -1300, 0.0), ('NVQueenPalm01', 3300, -1300, 0.0)]},
    'ultraluxe': {'label': 'Ultra-Luxe', 'world': 'TheStripWorldNew', 'match': r'^ultralux(hotelfront|dome)$'},
    'gomorrah': {'label': 'Gomorrah', 'world': 'TheStripWorldNew', 'match': r'^gamorrah01$'},
    'battery': {'label': 'Gun battery', 'world': 'NVDLC03BigMT', 'match': r'^nvdlc03gunbatterystatic$',
                'extra': [('HVBunkerNV', -2600, 600, 0.0), ('HVBunkerNV2', 2600, 400, 3.1), ('dlc04sandbagbunkerroundtower', -1500, -1900, 0.0),
                          ('dlc04sandbagbunkerroundtower', 1500, -1900, 0.0), ('truckarmy02Static', -600, -2300, 1.2), ('truckarmy02Static', 700, -2500, 1.9),
                          ('NVGuardTower01', 0, -3000, 0.0), ('FlagPole', 300, -2100, 0.0)]},
    'pool': {'label': 'Swimming baths', 'extra': [('TheTopsPool', 0, 0, 0.0, 18.0), ('NVMojOutpostStatue01', 0, 2100, 3.14), ('FlagPole', -1500, 1700, 0.0),
                                                  ('FlagPole', 1500, 1700, 0.0), ('umbrellaNV', -2500, 300, 0.0), ('umbrellaNV', 2500, -200, 0.0),
                                                  ('dlc04lawnchair01', -2500, -300, 1.0), ('dlc04lawnchair01', 2550, 400, 4.0)]},
    'lookout': {'label': 'Lookout station', 'extra': [('RadioTower01', 0, 0, 0.0), ('HVBunkerNV3', 1500, -300, 1.6), ('HVBunkerNV', -1500, 300, 4.7),
                                                      ('NVGuardTower01', 300, 1500, 0.0), ('truckarmy02Static', -500, -1300, 0.7),
                                                      ('SandbagStraight', 900, 900, 0.8), ('SandbagStraight', -900, 900, 5.5), ('CampfireCrafting03', 200, -500, 0.0)]},
}
MARGIN = 256.0          # (ground levelled this far round a landmark)
FAR = 2.5               # (each 400 units off its place costs a landmark as much as this many hundredths of it on a road)
NUDGE = 3500.0          # (how far off the spot asked for it may be moved to stay out of roads and water)
ROAD_HALF = 330.0
DOCK = 'PotDockBg4way01'
DOCK_STEP = 256.0
DOCK_UP = 104.0         # (a dock piece over the water, and a pylon under it, as the game has them at Lake Mead)
PYLON = ('PotDockPylon01', -296.0)
PIER_APART = 760.0      # (a real marina's fingers are a boat apart; squeezed, most of them go)
PIER_LONG = 1792.0      # (and the ones kept are built at least this long, or a squeezed pier is two steps of planking)
DOCK_LIMIT = 1400
MOORED = [('Boat02a', -60.0, 3), ('Boat02b', -60.0, 3), ('Boat02c', -60.0, 3), ('Boat02d', -60.0, 2), ('Boat02e', -60.0, 2), ('Boat03a', -12.0, 2),
          ('Boat03b', -12.0, 2), ('Boat03e', -12.0, 2), ('Barge', -8.0, 1)]
SUNK = ['Boat01a', 'Boat01b', 'Boat01d', 'dlc04boatwrecked01', 'Boat02c']
CRANE = ('CraneStatic02', 900.0)

ONLY_HERE = {'Lucky38WL', 'TheTopsWL', 'TheTopsPool', 'RadioTower01', 'HVBunkerNV', 'HVBunkerNV2', 'HVBunkerNV3', 'NVGuardTower01', 'NVMojOutpostStatue01'}
_found = {}


def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def _obnd(gd, fid):
    o = gd.fields(fid).get('OBND')
    return list(struct.unpack_from('<6h', o)) if o and len(o) >= 12 else None


def _scan(gd):
    """Every outdoor placement in the game of the things the sets name: {editor ID lowered: [(world's editor ID, form, x, y, z, rx, ry, rz, scale)]}."""
    if id(gd) in _found:
        return _found[id(gd)]
    pats = [re.compile(s['match']) for s in SETS.values() if s.get('match')]
    extra = {e[0].lower() for s in SETS.values() for e in s.get('extra', ()) if len(e) < 5}
    want, out = {}, {}
    for cell, refs in gd.cell_refs.items():
        if cell not in gd.ext_cells:
            continue
        world = None
        for _rf, (i, rec) in refs.items():
            if rec.tag != 'REFR':
                continue
            fl = gd.plugins[i].fields(rec)
            try:
                base = gd.to_global(i, struct.unpack('<I', fl['NAME'])[0])
            except (KeyError, struct.error):
                continue
            e = want.get(base)
            if e is None:
                e = gd.edid(base).lower() if base in gd.forms else ''
                e = want[base] = e if (e in extra or any(p.search(e) for p in pats)) else ''
            if not e or 'DATA' not in fl:
                continue
            if world is None:
                world = gd.edid(gd.ext_cells[cell])
            d = struct.unpack('<6f', fl['DATA'][:24])
            out.setdefault(e, []).append((world, base) + d + (struct.unpack('<f', fl['XSCL'])[0] if 'XSCL' in fl else 1.0,))
    _found[id(gd)] = out
    return out


def _base(gd, edid):
    low = edid.lower()
    for f, (_i, r) in gd.forms.items():
        if r.tag in ('STAT', 'MSTT', 'SCOL', 'ACTI', 'FURN', 'TREE', 'CONT') and gd.edid(f).lower() == low:
            return f
    return None


def lift(gd, name):
    """A set as pieces round its own middle: {'label', 'pieces': [(form key, east, north, up from the ground, rx, ry, rz, scale)],
    'box': (x0, y0, x1, y1)} or None if the game hasn't got it."""
    spec = SETS[name]
    found = _scan(gd)
    grounds = {}

    def ground(world, x, y):
        if world not in grounds:
            w = next((w for w in gd.worlds() if gd.edid(w) == world), None)
            grounds[world] = roadgen.Ground(gd, None, w) if w is not None else None
        return grounds[world].at(x, y) if grounds[world] else None

    pieces = []
    if spec.get('match'):
        pat = re.compile(spec['match'])
        rows = [r for e, rr in found.items() if pat.search(e) for r in rr if r[0] == spec['world']]
        if not rows:
            return None
        mx = (min(r[2] for r in rows) + max(r[2] for r in rows)) / 2
        my = (min(r[3] for r in rows) + max(r[3] for r in rows)) / 2
        g = ground(spec['world'], mx, my)
        if g is None:
            g = min(r[4] for r in rows) - 30.0
        # (the game's own ground is rarely just under a piece's origin: what the set's lowest piece stands at is nearer)
        for _w, base, x, y, z, rx, ry, rz, sc in rows:
            pieces.append((gd.key(base), x - mx, y - my, z - g, rx, ry, rz, sc))
    if spec.get('round') and pieces:
        # (some of its pieces again, turned about its middle: each a hair smaller than the last, so no two faces lie in one another)
        pat, times = re.compile(spec['round'][0]), spec['round'][1]
        again = [p for p in pieces if pat.search(gd.edid(gd.from_key(p[0])).lower())]
        for k in range(1, times):
            a = math.tau * k / times
            c, s = math.cos(a), math.sin(a)
            pieces += [(key, dx * c + dy * s, -dx * s + dy * c, dz, rx, ry, rz + a, sc * (1 - 0.004 * k)) for key, dx, dy, dz, rx, ry, rz, sc in again]
    if spec.get('inside') and pieces:
        edid, of, up = spec['inside']
        inner = _base(gd, edid)
        host = next((p for p in pieces if re.search(of, gd.edid(gd.from_key(p[0])).lower())), None)
        if inner is not None and host:
            pieces.append((gd.key(inner), host[1], host[2], host[3] + up * host[7], 0.0, 0.0, host[6], host[7]))
    for edid, dx, dy, rz, *given in spec.get('extra', ()):
        base = _base(gd, edid)
        if base is None:
            continue
        if given:                               # (how high its origin goes is said outright: a model made for far off has its own)
            pieces.append((gd.key(base), float(dx), float(dy), float(given[0]), 0.0, 0.0, rz, 1.0))
            continue
        # (its own underside on the ground. How high the game usually has one says nothing: the game stands palms on roofs
        # and flagpoles on platforms, and a hotel's palms once flew at seven thousand units)
        o = _obnd(gd, base)
        up = -float(o[2]) - BEDDED if o else 0.0
        pieces.append((gd.key(base), float(dx), float(dy), up, 0.0, 0.0, rz, 1.0))
    if not pieces:
        return None
    if spec.get('match'):
        # (a set lifted from the game: the lowest of its pieces' undersides goes to the ground, if the game's own ground
        # under it was no guide)
        low = min(dz + (_obnd(gd, gd.from_key(key)) or [0] * 6)[2] * sc for key, _dx, _dy, dz, _rx, _ry, _rz, sc in pieces)
        if low > 48 or low < -160:
            pieces = [(key, dx, dy, dz - low - BEDDED, rx, ry, rz, sc) for key, dx, dy, dz, rx, ry, rz, sc in pieces]
    key_ = (id(gd), name)
    if key_ in _lifted:
        return _lifted[key_]

    def box_of(pieces):
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        for key, dx, dy, _dz, _rx, _ry, rz, sc in pieces:
            b = _obnd(gd, gd.from_key(key)) or [-64, -64, 0, 64, 64, 64]
            for cx, cy in ((b[0], b[1]), (b[3], b[1]), (b[3], b[4]), (b[0], b[4])):
                tx, ty = _turn(cx * sc, cy * sc, rz)
                x0, y0, x1, y1 = min(x0, dx + tx), min(y0, dy + ty), max(x1, dx + tx), max(y1, dy + ty)
        return x0, y0, x1, y1

    # a casino on the Strip is made to be seen from the street: behind, one looks straight through it. Where a set is open
    # on one side, a second one stands against it there, turned about: two fronts and no back
    sides = closed_sides(_shapes(gd, pieces))
    doubled = False
    worst = min(range(4), key=lambda k: sides[k])
    if spec.get('match') and sides[worst] < OPEN and sorted(sides)[1] >= OPEN:
        x0, y0, x1, y1 = _mesh_box(_shapes(gd, pieces))
        # (the edge it's open at, a little inside it so the two bite into each other and leave no gap)
        ax = {0: x1 - SEAM, 1: x0 + SEAM}.get(worst)
        ay = {2: y1 - SEAM, 3: y0 + SEAM}.get(worst)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        px, py = (ax, my) if ax is not None else (mx, ay)
        pieces = pieces + [(key, 2 * px - dx, 2 * py - dy, dz, rx, ry, rz + math.pi, sc) for key, dx, dy, dz, rx, ry, rz, sc in pieces]
        # (and its middle is the middle of the two)
        pieces = [(key, dx - px, dy - py, dz, rx, ry, rz, sc) for key, dx, dy, dz, rx, ry, rz, sc in pieces]
        doubled = True
        after = closed_sides(_shapes(gd, pieces))
    else:
        after = sides
    _lifted[key_] = {'label': spec['label'], 'pieces': pieces, 'box': box_of(pieces), 'sides': [round(v, 2) for v in after], 'doubled': doubled}
    return _lifted[key_]


BEDDED = 6.0            # (a thing's underside goes this far into the ground, so no light shows under it)
OPEN = 0.5              # (a side showing less wall than this of what's seen from it is open)
SEAM = 96.0
_lifted = {}


def _shapes(gd, pieces):
    """The pieces' models as one, in the set's frame."""
    import nif
    out = []
    for key, dx, dy, dz, _rx, _ry, rz, sc in pieces:
        try:
            model = gd.describe(gd.from_key(key))[3]
            shapes = nif.mesh_from_nif(gd.read_file('meshes' + chr(92) + model))
        except Exception:
            continue
        c, s = math.cos(rz), math.sin(rz)
        for sh in shapes:
            p, q = sh['p'], []
            for k in range(0, len(p), 3):
                x, y, z = p[k] * sc, p[k + 1] * sc, p[k + 2] * sc
                q += [dx + x * c + y * s, dy - x * s + y * c, dz + z]
            out.append(dict(sh, p=q))
    return out


def _mesh_box(shapes):
    xs = [v for sh in shapes for v in sh['p'][0::3]]
    ys = [v for sh in shapes for v in sh['p'][1::3]]
    return min(xs), min(ys), max(xs), max(ys)


class Batch:
    """Landmarks and harbour for one world, as ops for one Undo."""

    def __init__(self, gd, pr, world, roads=(), seed=1):
        import land
        self.land = land
        self.gd, self.pr, self.world = gd, pr, world
        self.grid = gd.grid(world)
        self.ground = roadgen.Ground(gd, pr, world)
        self.rng = random.Random(seed * 2654435761 % (2 ** 31) + 11)
        self.forms, self.cache = {}, {}
        self.ops, self.gone, self.keep, self.made = [], set(), [], []
        # every 128-unit square a road covers (a road is narrower than a landmark's box is sampled, unless it's sampled this finely)
        self.roads = set()
        reach = int(ROAD_HALF // 128) + 1
        for road in roads:
            for (ax, ay), (bx, by) in zip(road['line'], road['line'][1:]):
                L = math.hypot(bx - ax, by - ay)
                for k in range(int(L // 100) + 1):
                    t = min(1.0, k * 100 / L) if L else 0.0
                    x, y = ax + (bx - ax) * t, ay + (by - ay) * t
                    i, j = int(x // 128), int(y // 128)
                    for di in range(-reach, reach + 1):
                        for dj in range(-reach, reach + 1):
                            if ((i + di + 0.5) * 128 - x) ** 2 + ((j + dj + 0.5) * 128 - y) ** 2 <= ROAD_HALF ** 2:
                                self.roads.add((i + di, j + dj))

    # ----- the ground -----

    def on_road(self, x, y):
        return (int(x // 128), int(y // 128)) in self.roads

    def height(self, x, y):
        k = (int(x // 4096), int(y // 4096))
        f = self.forms.get(k)
        if f is None:
            return self.ground.at(x, y)
        fx, fy = (x - k[0] * 4096) / 128, (y - k[1] * 4096) / 128
        c, r = min(31, int(fx)), min(31, int(fy))
        tx, ty = fx - c, fy - r
        h = f['h']
        return (h[r * 33 + c] * (1 - tx) + h[r * 33 + c + 1] * tx) * (1 - ty) + (h[(r + 1) * 33 + c] * (1 - tx) + h[(r + 1) * 33 + c + 1] * tx) * ty

    def _form(self, k):
        if k not in self.forms:
            cell = self.grid.get(k)
            if cell is None:
                return None
            mine = self.pr.land.get(self.gd.key(cell))
            e = self.gd.land_at(self.world, *k)
            if not mine and not e:
                return None
            f = dict(mine) if mine else self.land.decode(self.gd, e, self.cache)
            f['h'] = list(f['h'])
            self.forms[k] = f
        return self.forms[k]

    def level(self, x, y, rz, box, z, margin=MARGIN):
        """The ground inside a box (in a frame turned rz at x, y) brought to z."""
        x0, y0, x1, y1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
        rad = math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1)))
        for gy in range(int((y - rad) // 128), int((y + rad) // 128) + 2):
            for gx in range(int((x - rad) // 128), int((x + rad) // 128) + 2):
                lx, ly = _turn(gx * 128.0 - x, gy * 128.0 - y, -rz)
                if not (x0 <= lx <= x1 and y0 <= ly <= y1):
                    continue
                # (a point on a cell's edge is in both cells)
                for cx in {gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}:
                    for cy in {gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}:
                        f = self._form((cx, cy))
                        if f:
                            f['h'][(gy - cy * 32) * 33 + (gx - cx * 32)] = float(z)

    def clear(self, x, y, rz, box):
        """What the mod has standing inside a box goes."""
        rad = math.hypot(max(abs(box[0]), abs(box[2])), max(abs(box[1]), abs(box[3])))
        for cx in range(int((x - rad) // 4096), int((x + rad) // 4096) + 1):
            for cy in range(int((y - rad) // 4096), int((y + rad) // 4096) + 1):
                cell = self.grid.get((cx, cy))
                c = self.pr.cells.get(self.gd.key(cell)) if cell is not None else None
                for rk, r in (c['refs'].items() if c else ()):
                    p = r.get('p')
                    if not rk.startswith('+') or not p or (self.gd.key(cell), rk) in self.gone:
                        continue
                    lx, ly = _turn(p[0] - x, p[1] - y, -rz)
                    if box[0] <= lx <= box[2] and box[1] <= ly <= box[3]:
                        self.gone.add((self.gd.key(cell), rk))
                        self.ops.append({'op': 'remove', 'cell': self.gd.key(cell), 'ref': rk})

    def add(self, key, x, y, z, rx, ry, rz, scale):
        cell = self.grid.get((int(x // 4096), int(y // 4096)))
        if cell is None:
            return False
        self.ops.append({'op': 'add', 'cell': self.gd.key(cell), 'base': key,
                         'p': [round(x, 1), round(y, 1), round(z, 1), round(rx, 4), round(ry, 4), round(rz % math.tau, 4)], 's': round(scale, 3)})
        return True

    # ----- a landmark -----

    def _score(self, x, y, rz, box):
        bad = 0
        na, nb = max(2, int((box[2] - box[0]) // 200) + 1), max(2, int((box[3] - box[1]) // 200) + 1)
        for a in range(na + 1):
            for b in range(nb + 1):
                lx, ly = box[0] + (box[2] - box[0]) * a / na, box[1] + (box[3] - box[1]) * b / nb
                tx, ty = _turn(lx, ly, rz)
                g = self.ground.at(x + tx, y + ty)
                if g is None:
                    return None
                bad += 6 * (g < 8) + self.on_road(x + tx, y + ty)
        # (as a share of its footprint, in hundredths: a town has roads everywhere, and a landmark a block wide takes the
        # stretch of side street under it; what it mustn't do is stand in the sea or wander far from its place)
        bad = bad * 100.0 / ((na + 1) * (nb + 1))
        for kx, ky, krz, kb in self.made:
            if math.hypot(kx - x, ky - y) < (math.hypot(kb[2] - kb[0], kb[3] - kb[1]) + math.hypot(box[2] - box[0], box[3] - box[1])) / 2:
                bad += 500
        return bad

    def stand(self, name, x, y, turn=None, scale=1.0, nudge=NUDGE, level=True):
        """Stand a set at x, y (or near it). Returns what was done, in words' worth: {'label', 'x', 'y', 'turn', 'moved', 'pieces'} or None."""
        got = lift(self.gd, name)
        if not got:
            return None
        box = tuple(v * scale for v in got['box'])
        best = None
        turns = [turn] if turn is not None else [k * math.pi / 4 for k in range(8)]
        step = 400.0
        for ring in range(int(nudge // step) + 1):
            spots = [(x, y)] if ring == 0 else [(x + math.sin(a) * ring * step, y + math.cos(a) * ring * step) for a in (k * math.tau / (6 * ring) for k in range(6 * ring))]
            for sx, sy in spots:
                for rz in turns:
                    s = self._score(sx, sy, rz, box)
                    if s is not None and (best is None or s + ring * FAR < best[0]):
                        best = (s + ring * FAR, sx, sy, rz, ring)
            if best and best[0] <= (ring + 1) * FAR:
                break                           # (nothing further out can do better)
        if best is None:
            return None
        _s, sx, sy, rz, ring = best
        hs = sorted(h for a in range(5) for b in range(5)
                    for h in (self.height(sx + _turn(box[0] + (box[2] - box[0]) * a / 4, box[1] + (box[3] - box[1]) * b / 4, rz)[0],
                                          sy + _turn(box[0] + (box[2] - box[0]) * a / 4, box[1] + (box[3] - box[1]) * b / 4, rz)[1]),) if h is not None)
        z = max(24.0, round(hs[len(hs) // 2] / 8) * 8.0) if hs else 24.0
        self.clear(sx, sy, rz, box)
        if level:
            self.level(sx, sy, rz, box, z)
        n = 0
        for key, dx, dy, dz, rx, ry, prz, sc in got['pieces']:
            tx, ty = _turn(dx * scale, dy * scale, rz)
            base_z = z if level else (self.height(sx + tx, sy + ty) or z)
            n += self.add(key, sx + tx, sy + ty, base_z + dz * scale, rx, ry, prz + rz, sc * scale)
        self.made.append((sx, sy, rz, box))
        self.keep.append((sx, sy, rz, box[0], box[1], box[2], box[3]))
        return {'set': name, 'label': got['label'], 'x': round(sx), 'y': round(sy), 'turn': round(rz, 3), 'moved': round(ring * step), 'pieces': n, 'level': z}

    # ----- a harbour -----

    def harbour(self, piers):
        """piers: lines of (x, y) in game units. Returns {'piers', 'dock', 'boats', 'sunk'}."""
        gd = self.gd
        dock, pylon = _base(gd, DOCK), _base(gd, PYLON[0])
        rep = {'piers': 0, 'dock': 0, 'boats': 0, 'aground': 0, 'sunk': 0, 'crane': 0}
        moored = []
        if dock is None:
            return rep
        dock, pylon = gd.key(dock), gd.key(pylon) if pylon is not None else None
        boats = [(gd.key(f), up, w) for f, up, w in ((_base(gd, e), up, w) for e, up, w in MOORED) if f is not None]
        laid, mids, wet = [], [], []
        lines = sorted(piers, key=lambda l: -sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(l, l[1:])))
        for line in lines:
            if rep['dock'] >= DOCK_LIMIT:
                break
            L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(line, line[1:]))
            mx, my = (line[0][0] + line[-1][0]) / 2, (line[0][1] + line[-1][1]) / 2
            if L < 48 or any(math.hypot(mx - a, my - b) < PIER_APART for a, b in mids):
                continue
            if L < PIER_LONG:
                # (straight through its middle the way it runs, as long as a pier needs to be: only what's over water is built)
                ux, uy = line[-1][0] - line[0][0], line[-1][1] - line[0][1]
                d = math.hypot(ux, uy)
                if d < 24:
                    continue
                ux, uy = ux / d * PIER_LONG / 2, uy / d * PIER_LONG / 2
                line = [(mx - ux, my - uy), (mx + ux, my + uy)]
            n0 = len(laid)
            for (ax, ay), (bx, by) in zip(line, line[1:]):
                S = math.hypot(bx - ax, by - ay)
                if S < DOCK_STEP / 2:
                    continue
                yaw = math.atan2(bx - ax, by - ay)
                for k in range(int(S // DOCK_STEP) + 1):
                    t = min(1.0, (k + 0.5) * DOCK_STEP / S)
                    x, y = ax + (bx - ax) * t, ay + (by - ay) * t
                    g, w = self.ground.at(x, y), self.ground.water(x, y)
                    if g is None or w is None or g > w - 24 or any(math.hypot(x - a, y - b) < DOCK_STEP * 0.8 for a, b, _y in laid[-40:]):
                        continue
                    if self.add(dock, x, y, w + DOCK_UP, 0.0, 0.0, yaw, 1.0):
                        laid.append((x, y, yaw))
                        rep['dock'] += 1
                        if pylon and k % 2 == 0:
                            self.add(pylon, x, y, w + PYLON[1], 0.0, 0.0, yaw, 1.0)
                        wet.append((x, y, yaw, w, g))
            if len(laid) > n0:
                rep['piers'] += 1
                mids.append((mx, my))
        # boats along them
        rng = self.rng
        for n, (x, y, yaw, w, g) in enumerate(wet):
            if not boats:
                continue
            side = rng.choice((-1.0, 1.0))
            ox, oy = _turn(side * 330.0, 0.0, yaw)
            bx, by = x + ox, y + oy
            bg = self.ground.at(bx, by)
            if bg is None or bg > w - 16 or any(math.hypot(bx - a, by - b) < 300 for a, b, _y in laid) \
                    or any(math.hypot(bx - a, by - b) < 420 for a, b in moored):
                continue
            moored.append((bx, by))
            pick = rng.random() * sum(b[2] for b in boats)
            for key, up, wt in boats:
                pick -= wt
                if pick <= 0:
                    break
            if bg > w - 70:
                # (too shallow to float: aground and heeled over)
                rep['aground'] += self.add(key, bx, by, bg + 70.0, rng.uniform(-0.12, 0.12), rng.choice((-1, 1)) * rng.uniform(0.2, 0.4), yaw + rng.uniform(-0.3, 0.3), 1.0)
            elif rng.random() < 0.22:
                rep['sunk'] += self.add(key, bx, by, bg + 40.0, rng.uniform(-0.5, 0.5), rng.uniform(-0.4, 0.4), yaw + rng.uniform(-0.6, 0.6), 1.0)
            else:
                rep['boats'] += self.add(key, bx, by, w + up, rng.uniform(-0.05, 0.05), rng.uniform(-0.04, 0.04), yaw + rng.choice((0.0, math.pi)) + rng.uniform(-0.08, 0.08), 1.0)
        # a few big ones gone down in the open water between
        big = [gd.key(f) for f in (_base(gd, e) for e in SUNK) if f is not None]
        if mids:
            rep['at'] = [round(sum(m[0] for m in mids) / len(mids)), round(sum(m[1] for m in mids) / len(mids))]
        if mids and big:
            cx, cy = sum(m[0] for m in mids) / len(mids), sum(m[1] for m in mids) / len(mids)
            reach = max(1500.0, max(math.hypot(m[0] - cx, m[1] - cy) for m in mids))
            for _ in range(60):
                if rep['sunk'] >= 6 + len(mids) // 6:
                    break
                a, d = rng.uniform(0, math.tau), rng.uniform(0.2, 1.3) * reach
                x, y = cx + math.sin(a) * d, cy + math.cos(a) * d
                g, w = self.ground.at(x, y), self.ground.water(x, y)
                if g is None or w is None or g > w - 200 or any(math.hypot(x - p, y - q) < 900 for p, q, _y in laid):
                    continue
                rep['sunk'] += self.add(rng.choice(big), x, y, g + rng.uniform(60, 200), rng.uniform(-0.6, 0.6), rng.uniform(-0.5, 0.5), rng.uniform(0, math.tau), 1.0)
            # and a crane on the quay nearest them
            crane = _base(gd, CRANE[0])
            if crane is not None:
                for ring in range(1, 14):
                    spots = [(cx + math.sin(k * math.tau / 16) * ring * 500, cy + math.cos(k * math.tau / 16) * ring * 500) for k in range(16)]
                    ok = [(x, y) for x, y in spots if (self.ground.at(x, y) or -1) > 16 and not self.on_road(x, y)
                          and all((self.ground.at(x + dx, y + dy) or -1) > 16 for dx in (-1500, 1500) for dy in (-900, 900))]
                    if ok:
                        x, y = ok[0]
                        box = (-2100.0, -1000.0, 2100.0, 1000.0)
                        z = round((self.height(x, y) or 24.0) / 8) * 8.0
                        self.clear(x, y, 0.0, box)
                        self.level(x, y, 0.0, box, z)
                        rep['crane'] += self.add(gd.key(crane), x, y, z + CRANE[1], 0.0, 0.0, 0.0, 1.0)
                        self.made.append((x, y, 0.0, box))
                        self.keep.append((x, y, 0.0) + box)
                        break
        return rep

    def done(self):
        """Every op: what goes, the ground, then what's stood."""
        lands = [{'op': 'land', 'cell': self.gd.key(self.grid[k]), 'land': f} for k, f in sorted(self.forms.items())]
        return [o for o in self.ops if o['op'] == 'remove'] + lands + [o for o in self.ops if o['op'] == 'add']


def clear_of(ops, boxes):
    """The add ops that don't fall inside any of these boxes ((x, y, turn, x0, y0, x1, y1), as standing gives them)."""
    def inside(p):
        for x, y, rz, x0, y0, x1, y1 in boxes:
            lx, ly = _turn(p[0] - x, p[1] - y, -rz)
            if x0 <= lx <= x1 and y0 <= ly <= y1:
                return True
        return False
    return [o for o in ops if o.get('op') != 'add' or not inside(o['p'])]


def standing(gd, pr, world):
    """Where landmarks' pieces stand in a world (for landsoft's keep): each big piece as (x, y, turn, x0, y0, x1, y1)."""
    keys = {}
    for name, spec in SETS.items():
        got = lift(gd, name)
        # (a set's own pieces, and of what's added round one only what is found nowhere else: a truck is a truck anywhere)
        own = re.compile(spec['match']) if spec.get('match') else None
        for key, *_r in (got['pieces'] if got else ()):
            if key not in keys:
                fid = gd.from_key(key)
                b = _obnd(gd, fid)
                if b and max(b[3] - b[0], b[4] - b[1]) >= 600 and ((own and own.search(gd.edid(fid).lower())) or gd.edid(fid) in ONLY_HERE):
                    keys[key] = b
    crane = _base(gd, CRANE[0])
    if crane is not None:
        keys[gd.key(crane)] = _obnd(gd, crane)
    out = []
    for cell in gd.grid(world).values():
        c = pr.cells.get(gd.key(cell))
        for rk, r in (c['refs'].items() if c else ()):
            b = keys.get(r.get('base'))
            p = r.get('p')
            if b and p and rk.startswith('+'):
                s = float(r.get('s') or 1.0)
                out.append((p[0], p[1], p[5], b[0] * s, b[1] * s, b[3] * s, b[4] * s))
    return out


SIDE_GRID = 40


def closed_sides(shapes):
    """From each of four sides (east, west, north, south of the model), how much of what a person sees of its outline is
    wall facing them: 1 for a whole building; less where the model was made to be seen from the street only and its back
    is open (the game draws no wall from behind, so there one looks straight through)."""
    lo, hi = [1e18] * 3, [-1e18] * 3
    for sh in shapes:
        p = sh['p']
        for k in range(0, len(p), 3):
            for a in range(3):
                lo[a] = min(lo[a], p[k + a])
                hi[a] = max(hi[a], p[k + a])
    if hi[0] <= lo[0] or hi[1] <= lo[1] or hi[2] <= lo[2]:
        return [0.0] * 4
    G = SIDE_GRID
    out = []
    for axis, sign in ((0, 1), (0, -1), (1, 1), (1, -1)):
        other = 1 - axis
        # nearest surface in each square from this side, and whether it faces the viewer
        depth = [None] * (G * G)
        faces = bytearray(G * G)
        for sh in shapes:
            if sh.get('alpha') == 'blend':
                continue
            p, idx, both = sh['p'], sh['i'], sh.get('double')
            for k in range(0, len(idx) - 2, 3):
                a, b, c = (p[3 * idx[k]:3 * idx[k] + 3], p[3 * idx[k + 1]:3 * idx[k + 1] + 3], p[3 * idx[k + 2]:3 * idx[k + 2] + 3])
                u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
                n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2])[axis]
                if n == 0:
                    continue
                front = both or n * sign > 0
                pts = [((q[other] - lo[other]) / (hi[other] - lo[other]) * G, (q[2] - lo[2]) / (hi[2] - lo[2]) * G, q[axis] * sign) for q in (a, b, c)]
                x0, x1 = max(0, int(min(q[0] for q in pts))), min(G - 1, int(max(q[0] for q in pts)))
                y0, y1 = max(0, int(min(q[1] for q in pts))), min(G - 1, int(max(q[1] for q in pts)))
                d = (pts[1][1] - pts[2][1]) * (pts[0][0] - pts[2][0]) + (pts[2][0] - pts[1][0]) * (pts[0][1] - pts[2][1])
                if abs(d) < 1e-9:
                    continue
                for gy in range(y0, y1 + 1):
                    for gx in range(x0, x1 + 1):
                        px, py = gx + 0.5, gy + 0.5
                        w0 = ((pts[1][1] - pts[2][1]) * (px - pts[2][0]) + (pts[2][0] - pts[1][0]) * (py - pts[2][1])) / d
                        w1 = ((pts[2][1] - pts[0][1]) * (px - pts[2][0]) + (pts[0][0] - pts[2][0]) * (py - pts[2][1])) / d
                        if w0 < -0.02 or w1 < -0.02 or w0 + w1 > 1.02:
                            continue
                        z = w0 * pts[0][2] + w1 * pts[1][2] + (1 - w0 - w1) * pts[2][2]      # (bigger is nearer the viewer)
                        s = gy * G + gx
                        if depth[s] is None or z > depth[s]:
                            depth[s] = z
                            faces[s] = 1 if front else 0
        seen = sum(1 for v in depth if v is not None)
        out.append(sum(faces) / float(seen) if seen else 0.0)
    return out
