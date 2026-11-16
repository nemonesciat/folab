"""The Waikiki set (waikikiset.py) stood over a world made from a map, where each kind of thing belongs: one Undo's ops.

Run it on a world already dressed and built (buildings, hotels, landmarks, the city's ways up and camps, plants): it
keeps off all of that by looking at every thing standing in the world, not only at what the map says.

  beach     on sand within reach of the sea: lifeguard towers looking out to sea, loungers in rows with a cabana
            behind, canoes drawn up near the water with racks, the odd volleyball net
  fishing   a few fishing camps on the sand well away from the hotels: a hale, a sampan pulled up, a net rack, crab
            pots, a torch
  hotels    round each of FOLab's own hotels (maps\\hotels.json): a tiki gate on its sea side, torches, lanai tables,
            a tiki bar, a hula stage, carvings, a planter, a string of lights, bamboo fencing
  streets   along the roads, on the ground beside them and facing them: bus shelters, lei stands, shave ice carts,
            fruit stalls, A-boards, motel signs (near buildings), street lamps, puffer fish lamps

Each thing's footprint (its bounds turned as it stands, with PAD round it) must fall clear of every other thing's
footprint in the world (`Taken`): buildings, hotels, landmark pieces, road pieces, ramps, camps, walkways, the carrier's
pier, and doors with DOOR_ROOM more in front of them. Small things and ground cover don't count (`soft`), and a tree
or palm counts by its trunk only. Nothing on a road square of the map, on ground under the water, or where the ground
under the footprint falls more than its STEP: it is let down to the lowest of nine heights over its footprint, so no
side hangs (the higher side is a little in the ground). Lights: the game's own, as waikikiset.LIGHTS says, none within
LIGHT_APART of another; a thing whose light would be too near stands unlit, which only street lamps may not do.

`plan` returns (ops, report); the ops start with the records the mod hasn't yet (each piece's files written into the
mod's own folder, as every set does). Nothing here writes anything else."""
import math
import random

import modelsets
import waikikiset

PAD = 60.0                 # what is kept clear round a thing's footprint, and round what it must miss
DOOR_ROOM = 260.0          # and in front of a door (both sides: a door's front is not known from its bounds)
STEP = {'hula_stage': 24.0, 'hale': 24.0, 'volleyball': 40.0, 'lifeguard_tower': 30.0, 'tiki_bar': 30.0,
        'bus_shelter': 30.0}  # how far the ground may fall under it; others STEP_ANY
STEP_ANY = 45.0
SOFT_HIGH = 24.0           # a thing lower than this doesn't count (pavement, rubble, litter, decals)
SOFT_WIDE = 48.0           # nor one this narrow every way
TRUNK = 45.0               # a tree or palm is in the way only this far round its foot
TREE_WORDS = ('tree', 'palm', 'banyan', 'bamboo', 'joshua', 'pine', 'stump')
COVER_WORDS = ('grass', 'fern', 'weed', 'shrub', 'bush', 'plant', 'floor', 'cover', 'undergrowth', 'thicket', 'taro',
               'heliconia', 'hibiscus', 'banana', 'rubble', 'debris', 'litter', 'leaves', 'rock', 'pebble')
SEA_NEAR = (220.0, 1500.0) # a beach thing's distance from the sea
CANOE_NEAR = (120.0, 520.0)
LIFEGUARD_APART = 3800.0
BEACH_APART = 1500.0       # between one beach group and the next
FISH_APART = 6000.0
FISH_FROM_HOTEL = 1800.0
ROAD_SIDE = (220.0, 560.0) # a street thing's distance from the nearest road square of the map
STREET_APART = 1300.0      # between street things of any kind
LAMP_APART = 1600.0
NEAR_BUILDING = 1600.0     # a motel sign, a stall, a shelter: in town, this near a building
LIMITS = {'beach': 260, 'fishing': 14, 'streets': 520, 'lamps': 700}
TRIES = 60                 # spots looked at in a cell for the streets
HOTEL_RING = (160.0, 1900.0)
# what must be clear of the road and of everything else, where it isn't the whole bounds: a street lamp's arm reaches
# out over the road
FOOT = {'street_lamp': (-30.0, -30.0, 0.0, 30.0, 30.0, 0.0)}
SAND_SHARE = 5             # of the nine spots under a beach thing, at least this many on sand (the middle always)
SAND_BIG = {'lifeguard_tower': 3, 'volleyball': 3, 'hale': 3, 'cabana_blue': 2, 'cabana_yellow': 2, 'sampan': 3, 'net_rack': 2}   # (big ones reach off a narrow beach)


def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def facing(ux, uy):
    """The turn that has a piece's front (-y) look along (ux, uy), as the game turns things."""
    return math.atan2(-ux, -uy) % math.tau


class Taken:
    """Every thing standing in a world, as turned rectangles in a grid of squares: is a footprint clear of them?"""
    SQ = 512.0

    def __init__(self, gd, pr, world):
        self.gd, self.pr = gd, pr
        self.by = {}
        self.rects = []
        self._box = {}
        for cell in gd.grid(world).values():
            c = pr.cells.get(gd.key(cell))
            refs = list(c['refs'].values()) if c else []
            try:        # (and what the world's own plugin stands there: a world FOLab made is game data to the mod)
                refs += [{'base': gd.key(r['base']), 'p': list(r['pos']) + list(r['rot'])} for r in gd.refs(cell) if r['base'] and r['pos'] and r['rot']]
            except Exception:
                pass
            for r in refs:
                p = r.get('p')
                if not p or r.get('removed') or not r.get('base'):
                    continue
                self.add_ref(r['base'], p, float(r.get('s') or 1.0))

    def kind_of(self, base):
        """(type, editor ID, bounds) of a base form, the mod's own or the game's."""
        if base in self._box:
            return self._box[base]
        got = (None, '', None)
        rec = self.pr.records.get(base) if isinstance(base, str) else None
        if rec is not None:
            ob = next((s for s in rec['subs'] if s['tag'] == 'OBND'), None)
            box = [f['value'] for f in ob['fields']] if ob and ob.get('fields') else None
            ed = next((s.get('value') for s in rec['subs'] if s['tag'] == 'EDID'), '') or ''
            got = (rec.get('type'), ed, box)
        else:
            try:
                fid = self.gd.from_key(base)
                if fid in self.gd.forms:
                    import townbuild
                    got = (self.gd.forms[fid][1].tag, self.gd.edid(fid) or '', townbuild.obnd(self.gd, base))
            except (ValueError, KeyError, TypeError):
                pass
        self._box[base] = got
        return got

    def add_ref(self, base, p, s=1.0):
        tag, edid, box = self.kind_of(base)
        if not box or tag in ('LIGH', 'NPC_', 'CREA', 'SOUN', 'IDLM', 'ACRE', 'ACHR'):
            return
        x0, y0, z0, x1, y1, z1 = [v * s for v in box]
        e = edid.lower()
        if any(w in e for w in TREE_WORDS):
            x0, y0, x1, y1 = -TRUNK * s, -TRUNK * s, TRUNK * s, TRUNK * s
        elif any(w in e for w in COVER_WORDS) or z1 - z0 < SOFT_HIGH or max(x1 - x0, y1 - y0) < SOFT_WIDE:
            return
        pad = DOOR_ROOM if tag == 'DOOR' else 0.0
        self.put(p[0], p[1], p[5] if len(p) > 5 else 0.0, (x0 - pad, y0 - pad, x1 + pad, y1 + pad))

    def put(self, x, y, rz, rect):
        n = len(self.rects)
        corners = [(x + a, y + b) for a, b in (_turn(u, v, rz) for u, v in ((rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3]), (rect[0], rect[3])))]
        self.rects.append(corners)
        xs, ys = [c[0] for c in corners], [c[1] for c in corners]
        for i in range(int(min(xs) // self.SQ), int(max(xs) // self.SQ) + 1):
            for j in range(int(min(ys) // self.SQ), int(max(ys) // self.SQ) + 1):
                self.by.setdefault((i, j), []).append(n)

    def clear(self, corners):
        xs, ys = [c[0] for c in corners], [c[1] for c in corners]
        seen = set()
        for i in range(int(min(xs) // self.SQ), int(max(xs) // self.SQ) + 1):
            for j in range(int(min(ys) // self.SQ), int(max(ys) // self.SQ) + 1):
                for n in self.by.get((i, j), ()):
                    if n not in seen:
                        seen.add(n)
                        if _overlap(corners, self.rects[n]):
                            return False
        return True


def _overlap(a, b):
    """Do two convex four-cornered shapes overlap (separating axes)?"""
    for poly in (a, b):
        for k in range(4):
            (x0, y0), (x1, y1) = poly[k], poly[(k + 1) % 4]
            nx, ny = y0 - y1, x1 - x0
            pa = [nx * x + ny * y for x, y in a]
            pb = [nx * x + ny * y for x, y in b]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return False
    return True


class Stander:
    """Puts pieces down: the checks, the seat, the lights, the counts."""

    def __init__(self, gd, pr, world, cover, taken, ground):
        import osmcover
        self.gd, self.pr, self.world, self.cover, self.taken, self.ground = gd, pr, world, cover, taken, ground
        self.grid = gd.grid(world)
        self.first, self.ops, self.keys, self.boxes = [], [], {}, {}
        self.by, self.lights, self.unlit = {}, [], 0
        self.road = osmcover.CODE['asphalt']
        self.sand = osmcover.CODE['sand']
        self.light_key = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items()
                          if r.tag == 'LIGH' and gd.edid(f) in {e for rows in waikikiset.LIGHTS.values() for e, *_r in rows}}
        self.lamps = []

    def kind(self, x, y):
        c = self.cover
        gx, gy = int(round(x / 128.0)) - c.gx0, int(round(y / 128.0)) - c.gy0
        return c.kind[gy * c.A + gx] if 0 <= gx < c.A and 0 <= gy < c.D else None

    def wet(self, x, y):
        """Is this spot under the water (or off the land)?"""
        z = self.ground.at(x, y)
        w = self.ground.water(x, y)
        return z is None or z < max(8.0, (w if w is not None and w > -1e8 else 0.0) + 8.0)

    def foot(self, piece):
        return FOOT.get(piece) or self.box(piece)

    def box(self, piece):
        if piece not in self.boxes:
            self.boxes[piece] = modelsets.build(piece)['box']
        return self.boxes[piece]

    def key(self, piece):
        if piece not in self.keys:
            got, info = modelsets.put(self.pr, piece)
            self.first.extend(got)
            self.keys[piece] = info['key'] or '$model_' + piece
        return self.keys[piece]

    def corners(self, piece, x, y, rz, pad=PAD):
        b = self.foot(piece)
        return [(x + a, y + c) for a, c in (_turn(u, v, rz) for u, v in ((b[0] - pad, b[1] - pad), (b[3] + pad, b[1] - pad), (b[3] + pad, b[4] + pad), (b[0] - pad, b[4] + pad)))]

    def fits(self, piece, x, y, rz, sand=False):
        """The height to stand it at, or None: clear of everything, on dry ground off the road, not too steep."""
        b = self.foot(piece)
        pts = [(x + a, y + c) for a, c in (_turn(b[0] + (b[3] - b[0]) * u / 2.0, b[1] + (b[4] - b[1]) * v / 2.0, rz) for u in range(3) for v in range(3))]
        if sand and self.kind(x, y) != self.sand:
            return None
        hs, on_sand = [], 0
        for px, py in pts:
            if self.wet(px, py):
                return None
            k = self.kind(px, py)
            if k == self.road:
                return None
            on_sand += k == self.sand
            hs.append(self.ground.at(px, py))
        if sand and on_sand < SAND_BIG.get(piece, SAND_SHARE):
            return None
        if max(hs) - min(hs) > STEP.get(piece, STEP_ANY):
            return None
        if not self.taken.clear(self.corners(piece, x, y, rz)):
            return None
        return min(hs)

    def stand(self, piece, x, y, rz, z, need_light=False):
        """Put it down (fits said where): its add op, its lights if none too near, and what it now takes."""
        rows = waikikiset.LIGHTS.get(piece, ())
        lit = []
        for edid, lx, ly, lz in rows:
            if edid not in self.light_key:
                continue
            tx, ty = _turn(lx, ly, rz)
            lit.append((self.light_key[edid], x + tx, y + ty, z + lz))
        if lit and any(math.hypot(lx - ox, ly - oy) < waikikiset.LIGHT_APART for _k, lx, ly, _z in lit for ox, oy in self.lights):
            if need_light:
                return False
            lit, self.unlit = [], self.unlit + 1
        cell = self.grid.get((int(x // 4096), int(y // 4096)))
        if cell is None:
            return False
        self.ops.append({'op': 'add', 'cell': self.gd.key(cell), 'base': self.key(piece), 's': 1.0,
                         'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)]})
        for k, lx, ly, lz in lit:
            lc = self.grid.get((int(lx // 4096), int(ly // 4096))) or cell
            self.ops.append({'op': 'add', 'cell': self.gd.key(lc), 'base': k, 's': 1.0, 'p': [round(lx, 1), round(ly, 1), round(lz, 1), 0.0, 0.0, 0.0]})
            self.lights.append((lx, ly))
        b = self.box(piece)
        self.taken.put(x, y, rz, (b[0], b[1], b[3], b[4]))
        self.by[piece] = self.by.get(piece, 0) + 1
        return True

    def try_put(self, piece, x, y, rz, sand=False, need_light=False):
        z = self.fits(piece, x, y, rz, sand)
        return z is not None and self.stand(piece, x, y, rz, z, need_light)

    def to(self, x, y, test, reach, rings=12, dirs=16):
        """The nearest spot in reach where test(x, y) holds: (distance, ux, uy) or None."""
        for k in range(1, rings + 1):
            d = reach * k / rings
            for n in range(dirs):
                a = math.tau * n / dirs
                ux, uy = math.cos(a), math.sin(a)
                if test(x + ux * d, y + uy * d):
                    return d, ux, uy
        return None


def plan(gd, pr, world, cover, seed=1, progress=None, hotels=None):
    """(ops, report): the Waikiki set over the world. hotels: [{'piece', 'x', 'y', 'turn'}] (maps\\hotels.json's
    entry for this world), else read from the mod."""
    import api_maps
    import roadgen
    rng = random.Random(seed * 6151 + 3)
    if progress:
        progress('Looking at what stands in the world')
    taken = Taken(gd, pr, world)
    ground = roadgen.Ground(gd, pr, world)
    S = Stander(gd, pr, world, cover, taken, ground)
    if hotels is None:
        hotels = api_maps._kept(pr, 'hotels.json').get(gd.edid(world)) or []
    grid = S.grid
    cover_cells = sorted({(gx // 32, gy // 32) for gx in range(cover.gx0, cover.gx0 + cover.A, 16) for gy in range(cover.gy0, cover.gy0 + cover.D, 16)} & set(grid))
    rng.shuffle(cover_cells)
    report = {'hotels': len(hotels), 'beach_groups': 0, 'fishing_camps': 0, 'street_things': 0, 'lamps': 0}
    sea = lambda x, y: S.wet(x, y)
    road = lambda x, y: S.kind(x, y) == S.road

    # --- round the hotels ---
    hotel_at = [(h['x'], h['y']) for h in hotels]
    for h in hotels:
        hx, hy = h['x'], h['y']
        to_sea = S.to(hx, hy, sea, 6000.0, rings=24)
        sx, sy = (to_sea[1], to_sea[2]) if to_sea else (0.0, -1.0)
        wants = [('tiki_gate', 1, 'sea'), ('tiki_torch_lit', 4, None), ('lanai_set', 4, 'sea'), ('tiki_bar', 1, 'sea'), ('hula_stage', 1, 'sea'),
                 ('tiki_tall', 2, 'out'), ('tiki_short', 2, 'out'), ('lava_planter', 2, None), ('string_lights', 1, 'sea'), ('bamboo_fence', 2, 'out'),
                 ('puffer_lamp', 1, 'sea')]
        for piece, n, face in wants:
            put = 0
            for _ in range(700):
                if put >= n:
                    break
                if piece == 'tiki_gate':
                    d = rng.uniform(HOTEL_RING[0] + 300, HOTEL_RING[0] + 1400)
                    a = math.atan2(sy, sx) + rng.uniform(-0.5, 0.5)
                else:
                    d = rng.uniform(HOTEL_RING[0] + 300, HOTEL_RING[1])
                    a = rng.uniform(0, math.tau)
                x, y = hx + math.cos(a) * d, hy + math.sin(a) * d
                if face == 'sea':
                    rz = facing(sx, sy) + rng.uniform(-0.3, 0.3)
                elif face == 'out':
                    rz = facing(math.cos(a), math.sin(a))
                else:
                    rz = rng.uniform(0, math.tau)
                if piece == 'tiki_gate':
                    rz = facing(-sx, -sy)          # (its front to the way in: you walk up from the sea through it)
                if S.try_put(piece, x, y, rz):
                    put += 1

    # --- the beach and the fishing camps ---
    beach_at, guards, camps = [], [], []
    # (the map's sand is a strip a few points wide along the shore: spots picked at random over the world hardly find it,
    # so every sand point is a spot, shuffled, each a little off its point)
    sand_pts = [((cover.gx0 + i % cover.A) * 128.0, (cover.gy0 + i // cover.A) * 128.0) for i, v in enumerate(cover.kind) if v == S.sand]
    rng.shuffle(sand_pts)
    for n, (sx0, sy0) in enumerate(sand_pts):
        if progress and n % 500 == 0:
            progress('The beach', n, len(sand_pts))
        if report['beach_groups'] >= LIMITS['beach'] and report['fishing_camps'] >= LIMITS['fishing']:
            break
        for _ in (0,):
            x, y = sx0 + rng.uniform(-64, 64), sy0 + rng.uniform(-64, 64)
            if S.kind(x, y) != S.sand or S.wet(x, y):
                continue
            if any(math.hypot(x - bx, y - by) < BEACH_APART for bx, by in beach_at):
                continue
            ts = S.to(x, y, sea, SEA_NEAR[1], rings=10)
            if not ts or ts[0] < SEA_NEAR[0]:
                continue
            d, ux, uy = ts
            look = facing(ux, uy)                       # (front to the sea)
            ax, ay = -uy, ux                            # along the shore
            far_from_hotels = all(math.hypot(x - hx, y - hy) > FISH_FROM_HOTEL for hx, hy in hotel_at)
            if (far_from_hotels and report['fishing_camps'] < LIMITS['fishing'] and all(math.hypot(x - fx, y - fy) > FISH_APART for fx, fy in camps)
                    and rng.random() < 0.6):
                if S.try_put('hale', x, y, look, sand=True):
                    camps.append((x, y))
                    beach_at.append((x, y))
                    report['fishing_camps'] += 1
                    for piece, off_a, off_s, turn in (('sampan', 0.0, min(d - 160, 420), 0.5), ('net_rack', 520.0, 80.0, 0.0), ('crab_pots', -480.0, 140.0, 0.3),
                                                      ('tiki_torch_lit', 330.0, -220.0, 0.0), ('outrigger', -620.0, min(d - 120, 380), 1.5)):
                        for _t in range(6):
                            jx, jy = rng.uniform(-60, 60), rng.uniform(-60, 60)
                            px, py = x + ax * off_a + ux * off_s + jx, y + ay * off_a + uy * off_s + jy
                            if S.try_put(piece, px, py, look + turn + rng.uniform(-0.25, 0.25), sand=piece != 'tiki_torch_lit'):
                                break
                    continue
            if report['beach_groups'] >= LIMITS['beach']:
                continue
            pick = rng.random()
            ok = False
            if pick < 0.3 and all(math.hypot(x - gx, y - gy) > LIFEGUARD_APART for gx, gy in guards) and d <= 900:
                ok = S.try_put('lifeguard_tower', x, y, look, sand=True)
                if ok:
                    guards.append((x, y))
                    S.try_put('board_surf', x + ax * 260 - ux * 120, y + ay * 260 - uy * 120, look + 0.2, sand=True)
            elif pick < 0.62:
                colour = rng.choice(('blue', 'yellow'))
                row = 0
                for k in range(rng.randint(2, 4)):
                    if S.try_put('lounger_' + colour, x + ax * 150 * k, y + ay * 150 * k, look + rng.uniform(-0.15, 0.15), sand=True):
                        row += 1
                if row:
                    ok = True
                    S.try_put('cabana_' + colour, x + ax * 150 * (row - 1) / 2 - ux * 380, y + ay * 150 * (row - 1) / 2 - uy * 380, look, sand=True)
            elif pick < 0.85:
                if CANOE_NEAR[0] <= d <= CANOE_NEAR[1] + 400:
                    ok = S.try_put('outrigger', x + ux * max(0, d - CANOE_NEAR[1]), y + uy * max(0, d - CANOE_NEAR[1]), look + math.pi / 2 + rng.uniform(-0.3, 0.3), sand=True)
                    if ok:
                        S.try_put(rng.choice(('outrigger_rack', 'board_rack')), x - ux * 420, y - uy * 420, look, sand=True)
            else:
                ok = S.try_put('volleyball', x - ux * 200, y - uy * 200, look + math.pi / 2, sand=True)
            if ok:
                beach_at.append((x, y))
                report['beach_groups'] += 1

    # --- the streets ---
    import osmdress
    import server
    try:
        import townbuild
        cat = townbuild.load(gd, server.kits_folder())
        homes = [(x, y) for _b, x, y, _z, _r in osmdress.standing(gd, pr, world, cat)]
    except Exception:
        homes = []
    near_home = {}
    for x, y in homes:
        near_home.setdefault((int(x // NEAR_BUILDING), int(y // NEAR_BUILDING)), []).append((x, y))

    def in_town(x, y):
        i, j = int(x // NEAR_BUILDING), int(y // NEAR_BUILDING)
        return any(math.hypot(x - hx, y - hy) < NEAR_BUILDING for a in (-1, 0, 1) for b in (-1, 0, 1) for hx, hy in near_home.get((i + a, j + b), ()))

    STREET = [('bus_shelter', 3), ('lei_stand', 3), ('shave_ice_cart', 3), ('fruit_stall', 3), ('board_surf', 2), ('board_poi', 2),
              ('motel_sign_0', 1), ('motel_sign_1', 1), ('motel_sign_2', 1), ('motel_sign_3', 1), ('puffer_lamp', 1), ('tiki_short', 1)]
    street_at = []
    for n, (cx, cy) in enumerate(cover_cells):
        if progress and n % 64 == 0:
            progress('The streets', n, len(cover_cells))
        if report['street_things'] >= LIMITS['streets'] and report['lamps'] >= LIMITS['lamps']:
            break
        for _ in range(TRIES):
            x, y = (cx + rng.random()) * 4096.0, (cy + rng.random()) * 4096.0
            if road(x, y) or S.wet(x, y):
                continue
            tr = S.to(x, y, road, ROAD_SIDE[1], rings=7, dirs=12)
            if not tr or tr[0] < ROAD_SIDE[0]:
                continue
            d, ux, uy = tr
            look = facing(ux, uy)                       # (front to the road)
            if report['lamps'] < LIMITS['lamps'] and all(math.hypot(x - lx, y - ly) > LAMP_APART for lx, ly in S.lamps) and rng.random() < 0.5:
                # (the lamp's arm reaches out over the road: its -x side; turned so -x looks at the road)
                if S.try_put('street_lamp', x, y, facing(-uy, ux), need_light=True):
                    S.lamps.append((x, y))
                    report['lamps'] += 1
                continue
            if report['street_things'] >= LIMITS['streets'] or not in_town(x, y):
                continue
            if any(math.hypot(x - sx, y - sy) < STREET_APART for sx, sy in street_at):
                continue
            pick = rng.random() * sum(w for _p, w in STREET)
            for piece, w in STREET:
                pick -= w
                if pick <= 0:
                    break
            if S.try_put(piece, x, y, look + rng.uniform(-0.12, 0.12)):
                street_at.append((x, y))
                report['street_things'] += 1
    report['by'] = {modelsets.PIECES[p]['label']: n for p, n in sorted(S.by.items())}
    report['things'] = sum(S.by.values())
    report['lights'] = len(S.lights)
    report['unlit'] = S.unlit
    report['records'] = len(S.first)
    return S.first + S.ops, report


def hanging(gd, pr, world):
    """Every piece of the set standing in the world, and those whose underside is over the ground by more than 2 units
    at one of nine spots of what stands on the ground (FOOT: a lamp's pole, not its arm out over the road):
    (how many stand, [(piece, x, y, most over)])."""
    import roadgen
    ground = roadgen.Ground(gd, pr, world)
    mine = {}
    for piece, what in modelsets.PIECES.items():
        if what['set'] == waikikiset.SET:
            k = modelsets.record_of(pr, piece)
            if k:
                mine[k] = (piece, FOOT.get(piece) or modelsets.build(piece)['box'])
    n, out = 0, []
    for cell in gd.grid(world).values():
        c = pr.cells.get(gd.key(cell))
        for r in (c['refs'].values() if c else ()):
            got = mine.get(r.get('base'))
            if not got or r.get('removed') or not r.get('p'):
                continue
            piece, b = got
            n += 1
            x, y, z, _rx, _ry, rz = r['p']
            hs = [ground.at(x + a, y + c_) for a, c_ in (_turn(b[0] + (b[3] - b[0]) * u / 2.0, b[1] + (b[4] - b[1]) * v / 2.0, rz) for u in range(3) for v in range(3))]
            over = max(z + b[2] - h for h in hs if h is not None)
            if over > 2.0:
                out.append((piece, round(x), round(y), round(over, 1)))
    return n, out
