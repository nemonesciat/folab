"""A city you can climb: ways up to the roofs, camps on them, walkways from roof to roof, lookout towers in the streets.

What makes a ruined city in this game its own is that every roof is somewhere to be: a ramp of planks up a wall, a
mattress and a fire barrel behind sandbags, a chair facing the street, a box of rounds, a walkway to the next roof.
This plans that over the buildings a map-made world already has (the game's own, stood by townbuild):

  a roof is measured from the building's collision (`roof_of`): the highest level with enough flat floor to stand on,
      its outline, and how high the wall round it stands over it (a parapet). Pitched roofs have none and are left;
  a way up is a ramp tower (citypieces) made to the roof's height, stood against a wall where the ground is level and
      nothing else stands, its top reaching over the wall, with a last ramp down behind a parapet;
  a camp is the game's own things on the roof's floor: sandbags along the edge that looks at the nearest road, behind
      them a chair, bedding, a fire, a box of something to find;
  a walkway joins two roofs near enough in height and distance, when both have a way up or a camp;
  a lookout tower stands by itself on open paved ground.

Nothing here is on a navmesh yet: the player walks all of it, nobody else does. One Undo. `plan` gives the ops."""
import math
import random

import citypieces
import hkshape
import landmarks
import modelsets
import townbuild

FLOOR = 0.86                # a triangle this near level is floor
LEVEL = 32.0                # roof floor is looked for in bands this thick
ENOUGH = 0.3                # of a building's footprint must be floor at a level for it to be the roof
LOW = 280.0                 # a roof lower than this isn't worth a tower
HIGH = 1700.0               # nor one higher than this a ramp (a dozen flights)
PARAPET_MOST = 160.0
SHARE = 0.55                # of the buildings with a roof to stand on get a way up
GROUND_UP, GROUND_DOWN = 100.0, 220.0     # round where the first ramp starts, the ground under a tower may stand this much higher, or lower
GROUND_STEP = 110.0         # (a lookout's ground)
BRIDGE = (180.0, 1000.0)    # a walkway spans between this little and this much
BRIDGE_SLOPE = 0.5          # and climbs no more than this for each unit it spans: a roof to a higher roof
ALONG = (0.0, -0.3, 0.3, -0.42, 0.42)     # where along a wall to try, as parts of its length from its middle
LIMIT = 600                 # ways up in one world
PITCH_SIGN = 1.0            # a placed thing turned about its own y by a positive angle has its +x end up (navgen._turn; tested)
# the game's own things for a camp (editor IDs; what the game hasn't is left out)
SANDBAG = 'SandbagStraight'
CAMP = [('BedMattress01Static', 0.7), ('NVBedrollL', 0.5), ('Barrel02Fire256', 0.5), ('CampfireCrafting03', 0.25), ('CrateGenericNV', 0.5),
        ('NellisCrateSTATIC', 0.5), ('MilkCrate01', 0.6), ('Barrel01', 0.4)]
LOOT = ['LootAmmoBox556mm', 'LootAmmoBox5mm', 'LootAmmoBox308', 'LootAmmoBox9mm', 'LootAmmoBox10mm', 'LootAmmoBoxShotgunShells', 'Footlocker01MilitaryNV',
        'FootlockerLegionRecruit', 'LootAmmoBoxMicroFusionCells']
CHAIRS = ['dlc04lawnchair01', 'ChairFolding01', 'NVChairFolding01', 'ChairMetal01']

# a raider camp's own: what rings it, what stands in it (editor IDs; what the game hasn't is left out)
JUNK = ['JunkWall01', 'JunkWall02']
YARD = [('Barrel02Fire512', 2), ('NVBedrollL', 3), ('BedMattress01Static', 2), ('GorePile01', 2), ('RamshacklePoleSht01', 3), ('CrateGenericNV', 3),
        ('Barrel01', 3), ('MilkCrate01', 3), ('Footlocker01MilitaryNV', 1), ('GoreBagContainer02', 1), ('TentSideALTNV', 1), ('ShackHangingLight02', 2)]
HANG = 'RaiderCorpseDressingChain'
CAMP_RING = 1250.0          # how far out a raider camp's wall of junk stands
CAMPS = 10                  # raider camps in one world
CAMPS_APART = 9000.0
LEANTO_SHARE = 0.4          # of roof camps get a lean-to

_roofs = {}
_tops = {}
CELL = 32.0                 # the roof is looked at in squares this size
OPEN_ROOF = 0.4             # of a roof's outline that must be clear floor at its height: under that it is a ceiling inside a
#                             pitched roof (a ranch house's, an old west store's), and a ramp to it would end in the attic
FLAT = 12.0                 # a square whose top is within this of the roof's floor is clear floor
ROUND = 96.0                # room left all round a lean-to: a body's width and a hand, so one walks round it and in
LEANTO = (360.0, 300.0)     # a lean-to's footprint (citypieces.describe_leanto)


class RoofFloor:
    """A building's roof seen from above, in its own frame: which squares of it are clear floor at the roof's height
    (not a vent, a tank, a parapet), and so where a camp's things can stand and whether one can walk between them."""

    def __init__(self, gd, model, roof):
        x0, y0, x1, y1 = roof['rect']
        self.x0, self.y0, self.z = x0, y0, roof['z']
        self.nx, self.ny = max(1, int((x1 - x0) / CELL)), max(1, int((y1 - y0) / CELL))
        top = [None] * (self.nx * self.ny)
        try:
            shapes = hkshape.collision_shapes(gd.read_file('meshes\\' + model.lower()))
        except Exception:
            shapes = []
        for sh in shapes:
            v, idx = sh['v'], sh['i']
            for k in range(0, len(idx) - 2, 3):
                a, b, c = (v[3 * idx[k + j]:3 * idx[k + j] + 3] for j in range(3))
                hi = max(a[2], b[2], c[2])
                if hi < self.z - FLAT:
                    continue                                    # (under the roof)
                i0 = max(0, int((min(a[0], b[0], c[0]) - x0) / CELL))
                i1 = min(self.nx - 1, int((max(a[0], b[0], c[0]) - x0) / CELL))
                j0 = max(0, int((min(a[1], b[1], c[1]) - y0) / CELL))
                j1 = min(self.ny - 1, int((max(a[1], b[1], c[1]) - y0) / CELL))
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        x, y = x0 + (i + 0.5) * CELL, y0 + (j + 0.5) * CELL
                        if not (min(a[0], b[0], c[0]) - CELL / 2 <= x <= max(a[0], b[0], c[0]) + CELL / 2):
                            continue
                        n = j * self.nx + i
                        if top[n] is None or hi > top[n]:
                            top[n] = hi
        self.clear = [t is not None and abs(t - self.z) <= FLAT for t in top]
        self.used = [False] * len(self.clear)
        self.kept = [False] * len(self.clear)                   # (kept clear for walking: nothing stands there, one walks on it)

    def cell(self, x, y):
        i, j = int((x - self.x0) / CELL), int((y - self.y0) / CELL)
        return j * self.nx + i if 0 <= i < self.nx and 0 <= j < self.ny else None

    def free(self, x, y, r):
        """Is every square within r of (x, y) clear floor, not used, and r in from the roof's edge?"""
        for dy in range(-int(r // CELL), int(r // CELL) + 1):
            for dx in range(-int(r // CELL), int(r // CELL) + 1):
                n = self.cell(x + dx * CELL, y + dy * CELL)
                if n is None or not self.clear[n] or self.used[n] or self.kept[n]:
                    return False
        return True

    def keep(self, x, y, r):
        for dy in range(-int(r // CELL), int(r // CELL) + 1):
            for dx in range(-int(r // CELL), int(r // CELL) + 1):
                n = self.cell(x + dx * CELL, y + dy * CELL)
                if n is not None:
                    self.kept[n] = True

    def take(self, x, y, r):
        for dy in range(-int(r // CELL), int(r // CELL) + 1):
            for dx in range(-int(r // CELL), int(r // CELL) + 1):
                n = self.cell(x + dx * CELL, y + dy * CELL)
                if n is not None:
                    self.used[n] = True

    def reach(self, start, goals):
        """Can a body (two squares wide) walk on clear, unused floor from start to every one of goals?"""
        s0 = self.cell(*start)
        if s0 is None:
            return False
        ok = lambda n: n is not None and self.clear[n] and not self.used[n]
        seen, todo = {s0}, [s0]
        while todo:
            n = todo.pop()
            i, j = n % self.nx, n // self.nx
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= i + di < self.nx and 0 <= j + dj < self.ny:
                    m = (j + dj) * self.nx + i + di
                    # (a body is two squares wide: the square beside, one way or the other across the way it goes, must be clear too)
                    side = [self.cell(self.x0 + (i + di + sg * dj + 0.5) * CELL, self.y0 + (j + dj + sg * di + 0.5) * CELL) for sg in (1, -1)]
                    if m not in seen and ok(m) and (ok(side[0]) or ok(side[1])):
                        seen.add(m)
                        todo.append(m)
        def near(g):                                            # (a thing's own squares are taken: one gets to it if one gets beside it)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    if self.cell(g[0] + dx * CELL, g[1] + dy * CELL) in seen:
                        return True
            return False
        return all(near(g) for g in goals)


def roof_floor(gd, model, roof):
    key = model.lower()
    if key not in _tops:
        _tops[key] = RoofFloor(gd, model, roof)
    rf = _tops[key]
    rf.used = [False] * len(rf.clear)                           # (a fresh roof for each building standing)
    rf.kept = [False] * len(rf.clear)
    return rf


def roof_of(gd, model, box):
    """{'z': the roof floor's height in the building's own frame, 'rect': (x0, y0, x1, y1) of that floor, 'parapet':
    how far the walls stand over it} or None when it has no flat roof to stand on. box: its bounds (the catalogue's)."""
    low = model.lower()
    if low in _roofs:
        return _roofs[low]
    got = None
    try:
        shapes = hkshape.collision_shapes(gd.read_file('meshes\\' + low))
    except Exception:
        shapes = []
    bands = {}
    for sh in shapes:
        v, idx = sh['v'], sh['i']
        for k in range(0, len(idx) - 2, 3):
            a, b, c = (v[3 * idx[k + j]:3 * idx[k + j] + 3] for j in range(3))
            e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
            if ln < 1e-6 or abs(n[2]) / ln < FLOOR:          # (a soup's triangles face either way: level is level)
                continue
            z = (a[2] + b[2] + c[2]) / 3
            band = bands.setdefault(int(z // LEVEL), [0.0, 1e9, 1e9, -1e9, -1e9, 0.0])
            area = ln / 2
            band[0] += area
            band[5] += z * area
            for p in (a, b, c):
                band[1], band[2], band[3], band[4] = min(band[1], p[0]), min(band[2], p[1]), max(band[3], p[0]), max(band[4], p[1])
    foot = max(1.0, (box[3] - box[0]) * (box[4] - box[1]))
    for key in sorted(bands, reverse=True):                  # from the top down: the first level with floor enough
        area, x0, y0, x1, y1, zsum = bands[key]
        if area >= ENOUGH * foot:
            z = zsum / area
            if z >= LOW and (x1 - x0) >= 300 and (y1 - y0) >= 300:
                got = {'z': z, 'rect': (max(x0, box[0]), max(y0, box[1]), min(x1, box[3]), min(y1, box[4])), 'parapet': max(0.0, min(PARAPET_MOST, box[5] - z))}
            break
    _roofs[low] = got
    return got


def _camp(gd, b, p, s, roof, side, along, drop, rng, edid_key, kind, road, put, piece):
    """A camp on a roof a ramp reaches, laid out to be used. In the building's own frame: the ramp lands at the middle of
    one side (`side`: that side's middle, which way is out) moved `along` it; from there one walks onto the roof. Then:
    sandbags along the edge that looks at the most road, a chair behind them; a lean-to with ROUND of floor all round
    it, its open side to the roof's middle, bedding under it; a fire barrel before its open side; crates and a box of
    something in a corner; all on clear floor (RoofFloor), and every one of them still walked to from where the ramp
    lands. What finds no clear floor is left out. Returns counts."""
    rf = roof_floor(gd, b['model'], roof)
    x0, y0, x1, y1 = roof['rect']
    mx, my, ox, oy = side
    ux, uy = -ox, -oy                                           # into the roof
    vx, vy = -oy, ox                                            # along the side the ramp is on
    reach = (citypieces.REACH - 24 + max(140.0, drop * 2.1) + 60) / s if drop > 4 else (citypieces.REACH + 60) / s
    land = (mx + vx * along / s + ux * reach, my + vy * along / s + uy * reach)
    if not rf.free(land[0], land[1], 32):
        return {'camps_no_floor': 1}
    rf.keep(land[0], land[1], 64)                               # (where one steps off the ramp stays clear)
    mid = ((x0 + x1) / 2, (y0 + y1) / 2)
    z = p[2] + roof['z'] * s + 1
    rz0 = p[5] if len(p) > 5 else 0.0
    out = {'camps': 1}
    placed = []

    def world(lx, ly):
        return _world(p, s, lx, ly)

    def turn(dx, dy):
        """The turn that brings a thing's front (its -y) to face along (dx, dy) of the building's frame."""
        wx, wy = landmarks._turn(dx, dy, rz0)
        return math.atan2(-wx, -wy)

    def place(base, lx, ly, r, rz):
        if base is None:
            return False
        if not rf.free(lx, ly, r):
            out['no_floor_for_things'] = out.get('no_floor_for_things', 0) + 1
            return False
        before = list(rf.used)
        rf.take(lx, ly, r)
        if not rf.reach(land, [q for q, _r in placed] + [(lx, ly)]):
            rf.used = before                                    # (it would cut something off from the way up: left out)
            out['cut_off'] = out.get('cut_off', 0) + 1
            return False
        wx, wy = world(lx, ly)
        put(base, wx, wy, z, rz)
        placed.append(((lx, ly), r))
        return True
    # the edge to watch from: the side with most road beyond it
    sides = [((x0 + x1) / 2, y0, 0, -1, x1 - x0), ((x0 + x1) / 2, y1, 0, 1, x1 - x0), (x0, (y0 + y1) / 2, -1, 0, y1 - y0), (x1, (y0 + y1) / 2, 1, 0, y1 - y0)]

    def roads(sd):
        ex, ey, nx, ny, ln = sd
        tx, ty = -ny, nx
        return sum(1 for t in (-0.4, -0.2, 0.0, 0.2, 0.4) for d in (300.0, 700.0, 1200.0)
                   if kind(*world(ex + tx * ln * t + nx * d / s, ey + ty * ln * t + ny * d / s)) == road)
    watch = max(sides, key=lambda sd: (roads(sd), (sd[2], sd[3]) != (ox, oy)))
    ex, ey, nx, ny, ln = watch
    tx, ty = -ny, nx
    if SANDBAG in edid_key:
        bags = 0
        half, deep = _half_size(gd, edid_key[SANDBAG], s)
        for t in (-0.25, 0.0, 0.25):
            bx, by = ex + tx * ln * t - nx * (90 / s), ey + ty * ln * t - ny * (90 / s)
            # (all along its length, not just its middle: a wall of bags is a car long, and its ends hung off the roof)
            along_free = all(rf.free(bx + tx * d, by + ty * d, deep) for d in _steps(half))
            if along_free and abs(bx - land[0]) + abs(by - land[1]) > 300 / s:
                rf.take(bx, by, 40)
                wx, wy = world(bx, by)
                put(edid_key[SANDBAG], wx, wy, z, turn(tx, ty) + math.pi / 2)      # (its length along the edge)
                bags += 1
        out['sandbags'] = bags
        have = [e for e in CHAIRS if e in edid_key]
        if have and bags:
            cx, cy = ex - nx * (210 / s), ey - ny * (210 / s)
            if place(edid_key[rng.choice(have)], cx, cy, 40, turn(nx, ny)):        # (looking out over the sandbags)
                out['chairs'] = 1
    # the lean-to: as far from the ramp as the roof allows, with room all round, open towards the middle
    wl, dl = LEANTO[0] / s, LEANTO[1] / s
    need = (max(wl, dl) / 2 + ROUND / s)
    best = None
    for j in range(rf.ny):
        for i in range(rf.nx):
            cx, cy = rf.x0 + (i + 0.5) * CELL, rf.y0 + (j + 0.5) * CELL
            if not rf.free(cx, cy, need):
                continue
            d = math.hypot(cx - land[0], cy - land[1])
            if best is None or d > best[0]:
                best = (d, cx, cy)
    if best:
        _d, cx, cy = best
        dx, dy = mid[0] - cx, mid[1] - cy
        if math.hypot(dx, dy) < 1:
            dx, dy = land[0] - cx, land[1] - cy
        ln_ = math.hypot(dx, dy) or 1.0
        dx, dy = dx / ln_, dy / ln_
        before = list(rf.used)
        rf.take(cx, cy, max(wl, dl) / 2)
        front = (cx + dx * (dl / 2 + 60 / s), cy + dy * (dl / 2 + 60 / s))      # (where one stands to go in)
        if not rf.reach(land, [q for q, _r in placed] + [front]):
            rf.used = before
            best = None
    if best:
        _d, cx, cy = best
        wx, wy = world(cx, cy)
        put(piece(citypieces.leanto(rng.randrange(1, 4))), wx, wy, z, turn(dx, dy))
        placed.append(((cx + dx * (dl / 2 + 60 / s), cy + dy * (dl / 2 + 60 / s)), 0))
        rf.keep(cx + dx * (dl / 2 + 70 / s), cy + dy * (dl / 2 + 70 / s), 64)     # (the way in stays clear)
        out['leantos'] = 1
        bed = 'BedMattress01Static' if rng.random() < 0.5 else 'NVBedrollL'
        if bed in edid_key:                                     # (under it, its head to the back)
            wbx, wby = world(cx - dx * 30 / s, cy - dy * 30 / s)
            put(edid_key[bed], wbx, wby, z, turn(dx, dy))
            out['beds'] = 1
        fire = edid_key.get('Barrel02Fire256')
        # (before the open side and to one side of the way in, so it warms whoever sits there and blocks nobody)
        fx, fy = cx + dx * (LEANTO[1] / 2 + 150) / s + dy * 170 / s, cy + dy * (LEANTO[1] / 2 + 150) / s - dx * 170 / s
        if place(fire, fx, fy, 40, 0.0):
            out['fires'] = 1
    # crates and a box of something: in a corner, out of the way
    corners = sorted(((x0 + 190 / s, y0 + 190 / s), (x1 - 190 / s, y0 + 190 / s), (x0 + 190 / s, y1 - 190 / s), (x1 - 190 / s, y1 - 190 / s)),
                     key=lambda q: -math.hypot(q[0] - land[0], q[1] - land[1]))
    for qx, qy in corners:
        stack = [e for e in ('CrateGenericNV', 'NellisCrateSTATIC', 'MilkCrate01') if e in edid_key]
        if stack and rf.free(qx, qy, 70):
            place(edid_key[rng.choice(stack)], qx, qy, 70, rng.uniform(0, math.tau))
            loot = [e for e in LOOT if e in edid_key]
            lx2, ly2 = qx + (mid[0] - qx) * 0.18, qy + (mid[1] - qy) * 0.18
            if loot and place(edid_key[rng.choice(loot)], lx2, ly2, 32, turn(mid[0] - qx, mid[1] - qy)):
                out['loot'] = 1
            break
    out['walked'] = int(rf.reach(land, [q for q, _r in placed]))
    return out


def _half_size(gd, key, s=1.0):
    """(half its length, half its depth) of a thing's footprint, in a building's frame scaled s."""
    o = townbuild.obnd(gd, key) or [-40, -40, 0, 40, 40, 0]
    a, b = (o[3] - o[0]) / 2.0, (o[4] - o[1]) / 2.0
    return max(a, b) / s, max(8.0, min(a, b)) / s


def _steps(half, step=CELL):
    n = max(1, int(half // step))
    return [half * k / n for k in range(-n, n + 1)]


def _foot(gd, key, lx, ly, turn_local, s):
    """Spots under a thing's footprint (its bounds, turned), in the building's frame scaled s."""
    o = townbuild.obnd(gd, key) or [-20, -20, 0, 20, 20, 0]
    c, sn = math.cos(turn_local), math.sin(turn_local)
    out = []
    for fx in (0.05, 0.5, 0.95):
        for fy in (0.05, 0.5, 0.95):
            ax, ay = o[0] + (o[3] - o[0]) * fx, o[1] + (o[4] - o[1]) * fy
            out.append((lx + (ax * c + ay * sn) / s, ly + (-ax * sn + ay * c) / s))
    return out


TIDY_REACH = 320.0          # how far in a thing hanging off a roof may be moved, in the building's own units
TIDY_STEP = 16.0


def tidy(gd, pr, world, cat, progress=None):
    """(ops, report): what stands on a roof (its underside at the roof's floor, its middle over it) with any of its
    footprint off the roof's clear floor (hanging over the edge, or into the parapet) moved in toward the roof's middle
    until it all stands on floor, or taken out if no spot within TIDY_REACH has room."""
    grid = gd.grid(world)
    by_key = {b['key']: b for b in cat}
    stands, things = [], {}
    for cell in grid.values():
        ck = gd.key(cell)
        c = pr.cells.get(ck)
        for rk, r in (c['refs'].items() if c else ()):
            p = r.get('p')
            if not p or r.get('removed') or not r.get('base'):
                continue
            b = by_key.get(r['base'])
            if b and rk.startswith('+'):
                roof = roof_of(gd, b['model'], b['box'])
                if roof:
                    stands.append((b, p, float(r.get('s') or 1.0), roof))
            elif rk.startswith('+') and abs(p[3]) < 0.05 and abs(p[4]) < 0.05:
                things.setdefault((int(p[0] // 2048), int(p[1] // 2048)), []).append((ck, rk, r))
    ops, report = [], {'roofs': len(stands), 'moved': 0, 'removed': 0, 'fine': 0}
    for n, (b, p, s, roof) in enumerate(stands):
        if progress and n % 200 == 0:
            progress('Tidying the roofs', n, len(stands))
        rf = roof_floor(gd, b['model'], roof)
        zf = p[2] + roof['z'] * s
        rz0 = p[5] if len(p) > 5 else 0.0
        x0, y0, x1, y1 = roof['rect']
        mid = ((x0 + x1) / 2, (y0 + y1) / 2)
        reach = max(abs(v) for v in b['box']) * s + 400
        for gx in range(int((p[0] - reach) // 2048), int((p[0] + reach) // 2048) + 1):
            for gy in range(int((p[1] - reach) // 2048), int((p[1] + reach) // 2048) + 1):
                for ck, rk, r in things.get((gx, gy), ()):
                    q = r['p']
                    o = townbuild.obnd(gd, r['base'])
                    if not o or abs(q[2] + o[2] * float(r.get('s') or 1.0) - zf) > 12:
                        continue
                    lx, ly = landmarks._turn(q[0] - p[0], q[1] - p[1], -rz0)
                    lx, ly = lx / s, ly / s
                    if not (x0 <= lx <= x1 and y0 <= ly <= y1):
                        continue
                    tl = (q[5] if len(q) > 5 else 0.0) - rz0

                    def on_floor(ax, ay):
                        for sx, sy in _foot(gd, r['base'], ax, ay, tl, s / float(r.get('s') or 1.0)):
                            k = rf.cell(sx, sy)
                            if k is None or not rf.clear[k]:
                                return False
                        return True
                    if on_floor(lx, ly):
                        report['fine'] += 1
                        continue
                    dx, dy = mid[0] - lx, mid[1] - ly
                    d = math.hypot(dx, dy) or 1.0
                    dx, dy = dx / d, dy / d
                    got = None
                    k = TIDY_STEP
                    while k <= min(TIDY_REACH, d) + 1e-6:
                        if on_floor(lx + dx * k / s, ly + dy * k / s):
                            got = (lx + dx * k / s, ly + dy * k / s)
                            break
                        k += TIDY_STEP
                    if got is None:
                        ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                        report['removed'] += 1
                        continue
                    wx, wy = _world(p, s, got[0], got[1])
                    ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [round(wx, 1), round(wy, 1)] + list(q[2:])})
                    report['moved'] += 1
    return ops, report


def _world(p, s, lx, ly):
    """A building's own (lx, ly) where the building stands (p: its place and turn, s: its size)."""
    tx, ty = landmarks._turn(lx * s, ly * s, p[5] if len(p) > 5 else 0.0)
    return p[0] + tx, p[1] + ty


def plan(gd, pr, world, cover, cat, seed=1, progress=None, share=SHARE):
    """(ops, report): ways up, camps, walkways and lookouts for a world's buildings. cover: osmcover.MapCover (for where
    the roads are); cat: townbuild's catalogue."""
    import osmcover
    import roadgen
    rng = random.Random(seed * 104729 + 7)
    grid = gd.grid(world)
    ground = roadgen.Ground(gd, pr, world)
    by_key = {b['key']: b for b in cat}
    edid_key = {}
    want = {SANDBAG} | {e for e, _c in CAMP} | set(LOOT) | set(CHAIRS) | set(JUNK) | {e for e, _n in YARD} | {HANG}
    for f, (_i, r) in gd.forms.items():
        if r.tag in ('STAT', 'FURN', 'CONT', 'LIGH', 'ACTI', 'MSTT') and gd.edid(f) in want:
            edid_key[gd.edid(f)] = gd.key(f)
    A, D, gx0, gy0 = cover.A, cover.D, cover.gx0, cover.gy0
    road = osmcover.CODE['asphalt']

    def kind(x, y):
        gx, gy = int(round(x / 128.0)) - gx0, int(round(y / 128.0)) - gy0
        return cover.kind[gy * A + gx] if 0 <= gx < A and 0 <= gy < D else None

    # every building standing, with its roof if it has one
    stands = []
    for cell in grid.values():
        ck = gd.key(cell)
        c = pr.cells.get(ck)
        for rk, r in (c['refs'].items() if c else ()):
            b = by_key.get(r.get('base'))
            p = r.get('p')
            if not b or not p or r.get('removed') or not rk.startswith('+'):
                continue
            s = float(r.get('s') or 1.0)
            roof = roof_of(gd, b['model'], b['box'])
            stands.append({'b': b, 'p': p, 's': s, 'roof': roof, 'ck': ck, 'rk': rk})

    def taken(x, y, pad=40.0):
        """Does a spot fall inside some building's footprint?"""
        for st in stands:
            bx = st['b']['box']
            if abs(x - st['p'][0]) > 2600 or abs(y - st['p'][1]) > 2600:
                continue
            lx, ly = landmarks._turn(x - st['p'][0], y - st['p'][1], -(st['p'][5] if len(st['p']) > 5 else 0.0))
            lx, ly = lx / st['s'], ly / st['s']
            if bx[0] - pad <= lx <= bx[3] + pad and bx[1] - pad <= ly <= bx[4] + pad:
                return True
        return False

    def add(ops, base, x, y, z, rz, s=1.0, rx=0.0, ry=0.0):
        cell = grid.get((int(x // 4096), int(y // 4096)))
        if cell is None:
            return False
        ops.append({'op': 'add', 'cell': gd.key(cell), 'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), round(rx, 4), round(ry, 4), round(rz % math.tau, 4)], 's': round(s, 3)})
        return True

    first, ops, keys = [], [], {}

    def piece(name):
        if name not in keys:
            got, info = modelsets.put(pr, name)
            first.extend(got)
            keys[name] = info['key'] or '$model_' + name
        return keys[name]

    report = {'buildings': len(stands), 'roofs': 0, 'ways_up': 0, 'camps': 0, 'walkways': 0, 'lookouts': 0, 'no_room': 0}
    roofed = [st for st in stands if st['roof'] and st['roof']['z'] * st['s'] <= HIGH
              and sum(roof_floor(gd, st['b']['model'], st['roof']).clear) >= OPEN_ROOF * len(roof_floor(gd, st['b']['model'], st['roof']).clear)]
    report['roofs'] = len(roofed)
    rng.shuffle(roofed)
    climbed = []
    for n, st in enumerate(roofed):
        if progress and n % 20 == 0:
            progress('Ways up to the roofs', n, len(roofed))
        if rng.random() > share or report['ways_up'] >= LIMIT:
            continue
        b, p, s, roof = st['b'], st['p'], st['s'], st['roof']
        rz = p[5] if len(p) > 5 else 0.0
        x0, y0, x1, y1 = roof['rect']
        top = p[2] + (roof['z'] + roof['parapet']) * s        # what the ramp must reach: the top of the wall
        # each side of the building: the middle of the wall, which way is out, which way along
        sides = [((x0 + x1) / 2, b['box'][1], 0, -1), ((x0 + x1) / 2, b['box'][4], 0, 1), (b['box'][0], (y0 + y1) / 2, -1, 0), (b['box'][3], (y0 + y1) / 2, 1, 0)]
        rng.shuffle(sides)
        found = None
        for tight in (False, True):                            # the full tower if a wall has room for it, else the tight one
            wide, depth, (foot_a, foot_d) = citypieces.tower_size(tight)
            for mx, my, ox, oy in sides:
                along = ((x1 - x0) if ox == 0 else (y1 - y0)) * s
                for part in ALONG:
                    if abs(part) * along + wide > along / 2 + 120:
                        continue                               # (it would hang past the end of the wall)
                    ax, ay = (part * along / s, 0.0) if ox == 0 else (0.0, part * along / s)
                    wx, wy = _world(p, s, mx + ax + ox * 24 / s, my + ay + oy * 24 / s)    # the tower's face, a hand off the wall
                    ux, uy = landmarks._turn(-ox, -oy, rz)                                  # towards the building
                    vx, vy = uy, -ux                                                        # the tower's own x, along the wall
                    pts = [(wx + vx * a - ux * d, wy + vy * a - uy * d) for a in (-wide, 0, wide) for d in (20, depth / 2, depth)]
                    foot = (wx + vx * foot_a - ux * foot_d, wy + vy * foot_a - uy * foot_d)
                    hs = [ground.at(*q) for q in pts]
                    gf = ground.at(*foot)
                    if None in hs or gf is None or min(hs) < 8 or max(hs) > gf + GROUND_UP or min(hs) < gf - GROUND_DOWN:
                        continue
                    if any(taken(*q) for q in pts) or any(kind(*q) == road for q in pts):
                        continue
                    found = (tight, wx, wy, ux, uy, vx, vy, gf, (mx + ax, my + ay, ox, oy))
                    break
                if found:
                    break
            if found:
                break
        if not found:
            report['no_room'] += 1
            continue
        tight, wx, wy, ux, uy, vx, vy, gf, (lmx, lmy, ox, oy) = found
        name, real = citypieces.ramp_tower(top - gf, roof['parapet'] * s, tight)      # (to the ground where the first ramp starts)
        trz = math.atan2(ux, uy)                                                      # the tower's +y towards the building
        if not add(ops, piece(name), wx, wy, top - real, trz):
            continue
        report['tight'] = report.get('tight', 0) + bool(tight)
        n_fl = max(1, int(math.ceil((top - gf) / (citypieces.RISE_TIGHT if tight else citypieces.RISE))))
        half = (citypieces.RUN_TIGHT if tight else citypieces.RUN) / 2
        top_side = 1 if (n_fl - 1) % 2 == 0 else -1
        made = _camp(gd, b, p, s, roof, (lmx, lmy, ox, oy), top_side * (half + citypieces.LAND / 2), roof['parapet'] * s,
                     rng, edid_key, kind, road, lambda base, x, y, z, rz: add(ops, base, x, y, z, rz), piece)
        for k_, v_ in made.items():
            report[k_] = report.get(k_, 0) + v_
        report['ways_up'] += 1
        climbed.append(st)
    # walkways: from a roof someone can reach to a neighbour's
    joined = set()
    for st in climbed:
        b, p, s, roof = st['b'], st['p'], st['s'], st['roof']
        x0, y0, x1, y1 = roof['rect']
        ca = _world(p, s, (x0 + x1) / 2, (y0 + y1) / 2)
        za = p[2] + roof['z'] * s
        best = None
        for ot in roofed:
            if ot is st or (id(st), id(ot)) in joined or (id(ot), id(st)) in joined:
                continue
            q, r2 = ot['p'], ot['roof']
            cb = _world(q, ot['s'], (r2['rect'][0] + r2['rect'][2]) / 2, (r2['rect'][1] + r2['rect'][3]) / 2)
            zb = q[2] + r2['z'] * ot['s']
            d = math.hypot(cb[0] - ca[0], cb[1] - ca[1])
            if d > 3200:
                continue
            # the gap between the two roofs along the line joining their middles
            ux, uy = (cb[0] - ca[0]) / d, (cb[1] - ca[1]) / d

            def edge(sx, rect, pp, ss, cx, cy, sign):
                t = 0.0
                while t < d:
                    lx, ly = landmarks._turn(cx + sign * ux * t - pp[0], cy + sign * uy * t - pp[1], -(pp[5] if len(pp) > 5 else 0.0))
                    if not (rect[0] <= lx / ss <= rect[2] and rect[1] <= ly / ss <= rect[3]):
                        return t
                    t += 24.0
                return d
            ea = edge(None, roof['rect'], p, s, ca[0], ca[1], 1)
            eb = edge(None, r2['rect'], q, ot['s'], cb[0], cb[1], -1)
            gap = d - ea - eb
            ha, hb = za + roof['parapet'] * s + 10, zb + r2['parapet'] * ot['s'] + 10        # the top of each wall
            if BRIDGE[0] <= gap <= BRIDGE[1] and abs(hb - ha) <= BRIDGE_SLOPE * gap and (best is None or gap < best[0]):
                best = (gap, ot, ea, ux, uy, ha, hb)
        if best:
            gap, ot, ea, ux, uy, ha, hb = best
            span = math.hypot(gap + 220, hb - ha)                           # (each end well onto its roof)
            name, real = citypieces.bridge(span)
            mx, my = ca[0] + ux * (ea + gap / 2), ca[1] + uy * (ea + gap / 2)
            if not any(taken(mx + ux * t, my + uy * t, pad=-60.0) for t in (-gap / 2 + 80, 0, gap / 2 - 80)):
                # its length along the line between them, tipped up towards the higher roof
                if add(ops, piece(name), mx, my, (ha + hb) / 2, math.atan2(-uy, ux), ry=PITCH_SIGN * math.atan2(hb - ha, gap + 220)):
                    joined.add((id(st), id(ot)))
                    report['walkways'] += 1
                    report['climbing'] = report.get('climbing', 0) + (abs(hb - ha) > 60)
    # lookouts: on open paved ground, a tower on its own legs
    paved = osmcover.CODE['paved']
    spots = [((gx0 + gx) * 128.0, (gy0 + gy) * 128.0) for gy in range(12, D - 12, 12) for gx in range(12, A - 12, 12) if cover.kind[gy * A + gx] == paved]
    rng.shuffle(spots)
    towers = []
    for x, y in spots:
        if len(towers) >= max(4, report['ways_up'] // 6):
            break
        if any(math.hypot(x - tx, y - ty) < 5000 for tx, ty in towers):
            continue
        pts = [(x + dx, y + dy) for dx in (-380, 0, 700) for dy in (-400, -120, 160)]
        hs = [ground.at(*q) for q in pts]
        if None in hs or min(hs) < 8 or max(hs) - min(hs) > GROUND_STEP or any(taken(*q, pad=80.0) for q in pts) or any(kind(*q) == road for q in pts):
            continue
        name, _real = citypieces.lookout(rng.choice((640.0, 768.0, 896.0)))
        if add(ops, piece(name), x, y, min(hs), rng.choice((0.0, math.pi / 2, math.pi, 3 * math.pi / 2))):
            towers.append((x, y))
            report['lookouts'] += 1
    # raider camps: stacked shanties behind a wall of junk, on open level ground away from everything
    try:
        keep_off = [(mx, my, math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1))) + CAMP_RING) for mx, my, _r, x0, y0, x1, y1 in
                    landmarks.standing(gd, pr, world) + modelsets.footprints(pr, gd, world)]
        import api_maps
        kept = api_maps._kept(pr, 'landmarks.json').get(gd.edid(world)) or {}
        keep_off += [(float(m['x']), float(m['y']), 2600.0 + CAMP_RING) for m in (kept.get('stood') if isinstance(kept, dict) else kept) or [] if 'x' in m]
    except Exception:
        keep_off = []
    open_kinds = {osmcover.CODE['paved'], osmcover.CODE['yard'], osmcover.CODE['grass'], 0}
    spots = [((gx0 + gx) * 128.0, (gy0 + gy) * 128.0) for gy in range(16, D - 16, 6) for gx in range(16, A - 16, 6) if cover.kind[gy * A + gx] in open_kinds]
    rng.shuffle(spots)
    camps = []
    for x, y in spots:
        if len(camps) >= CAMPS:
            break
        if any(math.hypot(x - cx, y - cy) < CAMPS_APART for cx, cy in camps) or any(math.hypot(x - mx, y - my) < mr for mx, my, mr in keep_off):
            continue
        ring = [(x + math.cos(a) * r, y + math.sin(a) * r) for r in (0, CAMP_RING * 0.5, CAMP_RING) for a in (k * math.tau / 10 for k in range(10))]
        hs = [ground.at(*q) for q in ring]
        if None in hs or min(hs) < 16 or max(hs) - min(hs) > 140 or any(taken(*q, pad=120.0) for q in ring) or sum(1 for q in ring if kind(*q) == road) > 2:
            continue
        camps.append((x, y))
        face = rng.uniform(0, math.tau)                             # which way the stacks' fronts look
        ax, ay = landmarks._turn(1.0, 0.0, face)                    # the line the two stacks stand on
        n_a, n_b = rng.choice((2, 3)), rng.choice((3, 4))
        (pa, reach, up), (pb, _r, _u) = citypieces.shanty(n_a, rng.randrange(1, 4)), citypieces.shanty(n_b, rng.randrange(4, 7))
        half = reach + 400
        for pc, sign in ((pa, -1), (pb, 1)):
            add(ops, piece(pc), x + ax * sign * half, y + ay * sign * half, ground.at(x + ax * sign * half, y + ay * sign * half) or min(hs), face)
        za = (ground.at(x - ax * half, y - ay * half) or min(hs)) + 2 * up
        zb = (ground.at(x + ax * half, y + ay * half) or min(hs)) + 2 * up
        bname, _ln = citypieces.bridge(2 * 400 + 150)               # from one stack's second floor to the other's
        # (across the front half of the floors, clear of the rooms' side walls, which stand on the back half)
        bx, by = landmarks._turn(0.0, 110.0, face)
        add(ops, piece(bname), x + bx, y + by, (za + zb) / 2 + 4, face, ry=PITCH_SIGN * math.atan2(zb - za, 2 * 400))
        junk = [e for e in JUNK if e in edid_key]
        gate = rng.randrange(16)
        for k in range(16 if junk else 0):
            if k in (gate, (gate + 1) % 16):
                continue                                            # (the way in)
            a = k * math.tau / 16
            wx, wy = x + math.cos(a) * CAMP_RING, y + math.sin(a) * CAMP_RING
            g = ground.at(wx, wy)
            if g is not None and not taken(wx, wy):
                add(ops, edid_key[rng.choice(junk)], wx, wy, g - 6, math.atan2(-math.sin(a), math.cos(a)))     # (its length along the ring)
        for e, many in YARD:
            for _ in range(many if e in edid_key else 0):
                a, d = rng.uniform(0, math.tau), rng.uniform(250, CAMP_RING - 200)
                px, py = x + math.cos(a) * d, y + math.sin(a) * d
                if abs((px - x) * ax + (py - y) * ay) < half + reach and -300 < -(px - x) * ay + (py - y) * ax < citypieces.DEEP + 60:
                    continue                                        # (not under the stacks)
                g = ground.at(px, py)
                if g is not None:
                    add(ops, edid_key[e], px, py, g, rng.uniform(0, math.tau))
                    if e == 'RamshacklePoleSht01' and HANG in edid_key and rng.random() < 0.6:
                        add(ops, edid_key[HANG], px + 10, py, g + 250, rng.uniform(0, math.tau))
        name, _real = citypieces.lookout(896.0)
        ga = gate * math.tau / 16 + math.tau / 32
        lx, ly = x + math.cos(ga) * (CAMP_RING - 420), y + math.sin(ga) * (CAMP_RING - 420)
        g = ground.at(lx, ly)
        if g is not None:
            add(ops, piece(name), lx, ly, g, rng.uniform(0, math.tau))
    report['raider_camps'] = len(camps)
    report['camp_sites'] = [(round(cx), round(cy)) for cx, cy in camps]
    report['things'] = sum(1 for o in ops if o['op'] == 'add')
    report['pieces'] = len(keys)
    return first + ops, report
