"""The places at the top of Waikiki's ridge roads (docs/waikiki-story-plan.md, "The ridge roads"): six settlements and
four small stops, so that no road up a finger of the Koʻolau ends in nothing. Each is a recipe of the game's pieces laid
round the flattest free ground near where its road ends highest (`SITES`: that point as the street map has it).

    who holds it    the court's places are orderly (sandbags, the McCarran wall at Alewa Fort, tents in rows), the
                    Holdouts walled and self-sufficient, Loa Gate a shanty town with a pen, the Crow's Nest a pirate
                    camp of boats and a fuselage, the Heights ghouls' tended gardens among the mansions already there.
    buildings       townbuild's catalogue (shacks, a ranch house), stood by `townbuild._put`: each with its doors (locked:
                    no places behind them yet) and what shuts a doorway, only where the ground lies right and nothing big
                    is in the way.
    things          by editor ID, each on the ground where it stands, kept off buildings and off each other.
    walls           junk walls (490 long) or the McCarran wall's short pieces round a place, a gap toward its road.
    a map marker    for every place, shown once found (flags 2), named as the plan names it.

`ops(gd, pr, world, side)` gives one Undo's ops, a report and the cells touched. Nobody lives in them yet: people
come after the navmesh run (the plan's build order)."""
import math
import random

import roadgen
import townbuild

# (name, the road's top as (lat, lon), kind, marker type: 2 settlement, 3 encampment, 4 landmark, 8 military)
SITES = {
    'alewa': ('Alewa Fort', (21.3430, -157.8464), 'fort', 8),
    'beacon': ('Pacific Heights Beacon', (21.3290, -157.8369), 'beacon', 4),
    'heights': ('The Heights', (21.3308, -157.8140), 'heights', 2),
    'watcher': ("Watcher's Hut", (21.3010, -157.8011), 'watcher', 3),
    'tanks': ('The Tanks', (21.2973, -157.7871), 'tanks', 2),
    'holdouts': ('The Holdouts', (21.2985, -157.7752), 'holdouts', 2),
    'radar': ('Radar Dome', (21.2985, -157.7626), 'radar', 8),
    'loagate': ('Loa Gate', (21.2975, -157.7460), 'loagate', 2),
    'crowsnest': ("Crow's Nest", (21.3046, -157.7015), 'crowsnest', 3),
    'watchtower': ("Settlers' Watchtower", (21.3070, -157.6790), 'watchtower', 8),
}
SEEK = 1400.0                 # (how far from the road's top a place's middle may move to find flatter ground)
FLAT_REACH = 700.0
APART = 90.0                  # (things keep this far apart, edge to edge, roughly)
EASE = 650.0                  # (a terrace's edge eased back into the hill over this)
PLAZA = 700.0                 # (half the side of the level yard at a settlement's middle)
STEP = 8.0                    # (land heights in whole steps of this)
TERRACED = ('fort', 'tanks', 'holdouts', 'loagate', 'crowsnest', 'beacon', 'watcher', 'watchtower', 'radar')

SHACKS = ('WoodShack01', 'WoodShack02', 'WoodShack01ALT', 'WoodShack02ALT', 'NVShackVictor')
CAMP = [('CampfireCrafting03', 1), ('NVBedrollL', 2), ('NVBedrollR', 1), ('CrateGenericNV', 3), ('Barrel01', 2)]

RECIPES = {
    # each: [(what, args)] laid in order; 'ring' and 'fort' first so the rest keep inside
    'fort': [('fort', {'half': 1300.0}), ('one', ('NVGuardTower01', 0.0, 0.0, 'out')),
             ('row', ('CLSoldiersTent01', 4, 700.0, -600.0, 650.0)), ('ring_of', ('SandbagStraight', 6, 900.0)),
             ('scatter', [('CampfireCrafting03', 1), ('CrateLarge01', 2), ('CrateGenericNV', 4), ('Barrel01', 3),
                          ('Flagpole01', 1), ('NVBedrollL', 2)])],
    'beacon': [('one', ('RamshacklePoleReg03', 0.0, 0.0, 'any')), ('one', ('CampfireCrafting03', 160.0, 0.0, 'any')),
               ('buildings', (('WoodShack01',), 1, 500.0, 1100.0)),
               ('scatter', [('CrateGenericNV', 3), ('Barrel01', 2), ('NVBedrollL', 1), ('dlc04lawnchair01', 1)])],
    'heights': [('scatter', [('GardenLantern', 10), ('dlc04lawnchair01', 3), ('MakeshiftPlanter01', 3), ('MakeshiftPlanter02', 3),
                             ('CementPlanterRd01Bush', 4), ('Flagpole01', 1)])],
    'watcher': [('buildings', (('WoodShack02',), 1, 0.0, 500.0)),
                ('scatter', [('dlc04lawnchair01', 1), ('CampfireCrafting03', 1), ('NVBedrollL', 1), ('CrateGenericNV', 2), ('Barrel01', 1)])],
    'tanks': [('row', ('NVWaterTank', 3, 700.0, 0.0, 0.0)), ('one', ('ExteriorWaterTank01', -900.0, 600.0, 'any')),
              ('one', ('ExteriorWaterTank01', 900.0, 600.0, 'any')), ('one', ('GenericWaterPump', 0.0, 550.0, 'any')),
              ('one', ('WindmillSpinningNV', -1300.0, -400.0, 'any')), ('one', ('WindmillSpinningNV', 1300.0, -400.0, 'any')),
              ('buildings', (SHACKS, 5, 900.0, 2200.0)),
              ('scatter', [('CampfireCrafting03', 1), ('VBitterSpringsClotheslineShort', 2), ('MakeshiftPlanter01', 3),
                           ('cropFurrowNV', 3), ('Barrel01', 4), ('CrateGenericNV', 3), ('NVBedrollL', 2)])],
    'holdouts': [('ring', {'radius': 1900.0, 'piece': 'junk'}), ('one', ('NVGuardTower01', 0.0, 0.0, 'out')),
                 ('buildings', (SHACKS, 6, 600.0, 1500.0)),
                 ('scatter', [('CampfireCrafting03', 1), ('cropFurrowNV', 4), ('MakeshiftPlanter02', 3), ('Barrel01', 4),
                              ('CrateGenericNV', 3), ('SandbagStraight', 4), ('VBitterSpringsClotheslineShort', 1)])],
    'radar': [('one', ('NVSatelliteDishTripod', 0.0, 0.0, 'any')), ('wreck', ('NVNavarroVertibirdSTATIC', 900.0, 300.0)),
              ('scatter', [('SWSingleRubble', 4), ('SkeletonWholeBodyClothes', 2), ('CrateLarge01', 1), ('Tire02Static', 1)])],
    'loagate': [('across', ('JerseyBarricade01', 4)), ('ring', {'radius': 1700.0, 'piece': 'junk', 'part': 0.55}),
                ('one', ('NVSlavePenWall01', -600.0, 900.0, 'any')), ('buildings', (SHACKS, 4, 700.0, 1600.0)),
                ('scatter', [('NVBSRefugeeTent', 5), ('CampfireCrafting03', 2), ('CrateGenericNV', 5), ('Barrel01', 3),
                             ('VBitterSpringsClotheslineShort', 2), ('ShoppingCart01', 1), ('BedMattress01Static', 3)])],
    'crowsnest': [('one', ('NVGuardTower01', 0.0, 0.0, 'out')), ('one', ('RamshackleFuselagMid01', -700.0, -400.0, 'any')),
                  ('upturned', ('Boat01a', 2, 1100.0)), ('one', ('Flagpole01', 300.0, 250.0, 'any')),
                  ('scatter', [('CLSoldiersTent01', 3), ('CampfireCrafting03', 2), ('CrateGenericNV', 5), ('CrateLarge01', 2),
                               ('Barrel01', 4), ('NVBedrollL', 3), ('Tire01Static', 2)])],
    'watchtower': [('one', ('NVGuardTower01', 0.0, 0.0, 'out')), ('ring_of', ('SandbagStraight', 4, 500.0)),
                   ('scatter', [('CrateGenericNV', 2), ('Flagpole01', 1), ('CampfireCrafting03', 1)])],
}


def _names():
    out = set(SHACKS)
    for steps in RECIPES.values():
        for what, a in steps:
            if what in ('one', 'row', 'ring_of', 'wreck', 'upturned', 'across'):
                out.add(a[0])
            elif what == 'scatter':
                out |= {e for e, _n in a}
            elif what == 'buildings':
                out |= set(a[0])
    return out | {'NVJunkWall03', 'NVJunkWall04', 'NVMcCarranWallReg01', 'NVMcCarranWall02', 'SandbagStraight'}


class Place:
    """One place being laid: its middle, its road's way down, the ground, what it has stood so far."""

    def __init__(self, P, key, x, y, downhill):
        self.P, self.key, self.x, self.y, self.down = P, key, x, y, downhill
        self.taken = []                  # (x, y, radius)
        self.inner = None                # (inside a wall: how far from the middle things may go)
        self.n = 0

    def free(self, x, y, r):
        if any(math.hypot(x - a, y - b) < r + c + APART for a, b, c in self.taken):
            return False
        fp = [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
        blocked, clear = self.P.blocking(fp)
        if blocked:
            return False
        if r >= 100:
            self.P.take_out(clear)
        return True

    def put(self, edid, x, y, yaw, r=None, sink=0.0, tilt=(0.0, 0.0), check=True):
        P = self.P
        box = P.box(edid)
        if box is None:
            P.rep['missing'].add(edid)
            return False
        r = r if r is not None else max(box[3] - box[0], box[4] - box[1]) / 2
        if check and not self.free(x, y, r):
            return False
        g = P.ground.at(x, y)
        ck = P.w.cell_at(x, y)
        if g is None or ck is None or g < 4.0:
            return False
        # (on its lowest ground, so nothing hangs; the box's bottom at it)
        lows = [P.ground.at(x + dx, y + dy) for dx in (-r * .7, 0, r * .7) for dy in (-r * .7, 0, r * .7)]
        lows = [v for v in lows if v is not None]
        z = min(lows) - box[2] - sink if lows else g - box[2]
        P.ops.append({'op': 'add', 'cell': ck, 'base': P.key_of[edid], 'p': [round(x, 1), round(y, 1), round(z, 1), round(tilt[0], 4),
                      round(tilt[1], 4), round(yaw % math.tau, 4)], 's': 1})
        P.cells.add(ck)
        self.taken.append((x, y, r))
        self.n += 1
        return True


class Builder:
    def __init__(self, gd, pr, world, side, cat, seed=5):
        import osmplace
        self.gd, self.pr, self.world = gd, pr, world
        self.geo = osmplace.Georef(side)
        self.ground = roadgen.Ground(gd, pr, world)
        self.orig = roadgen.Ground(gd, pr, world)      # (the ground before any terrace)
        self.ground0 = {}
        self.cat = cat
        self.by_edid = {b['edid']: b for b in cat}
        self.w = townbuild.World(gd, pr, world, cat)
        self.w.ground = self.ground                    # (one ground for all: terraces show at once)
        self._clear_cache = {}
        self.gone = set()                              # ((cell, ref) taken out for a building or a thing)
        self.rnd = random.Random(seed)
        self.ops, self.cells = [], set()
        self.rep = {'places': {}, 'missing': set(), 'buildings': 0}
        import shipinside
        want = _names()
        found = shipinside._forms(gd, want)
        self.key_of = {e: gd.key(f) for e, f in found.items()}
        self.boxes = {}
        self.forms = {}                  # (cell xy -> the land form being changed; Ground reads the same h lists)
        self.moved = {}                  # ((cell, ref) -> its new p, for things already there on changed ground)

    # ----- terraces -----

    def _form(self, k):
        if k not in self.forms:
            import land
            cell = self.w.grid.get(k)
            if cell is None:
                return None
            mine = self.pr.land.get(self.gd.key(cell))
            e = self.gd.land_at(self.world, *k)
            if not mine and not e:
                return None
            f = dict(mine) if mine else land.decode(self.gd, e, {})
            f['h'] = [float(v) for v in f['h']]
            self.forms[k] = f
            self.ground.h[k] = f['h']
        return self.forms[k]

    def clearable(self, ck, rk):
        """What grows or lies about (plants, trees, rubble, rocks): taken out where a place is laid, never in its way."""
        if (ck, rk) in self.gone:
            return True
        if rk.startswith('(new'):
            return False
        r = self.pr.cells.get(ck, {}).get('refs', {}).get(rk)
        b = r.get('base') if r else None
        if not b:
            return False
        if b not in self._clear_cache:
            import natcompound
            e = natcompound._named(self.gd, self.pr, b)
            self._clear_cache[b] = (any(w.lower() in e.lower() for w in natcompound.GROWS + natcompound.LIES + ('Rock', 'Boulder', 'Jungle', 'Understory'))
                                    and not any(w in e for w in ('Road', 'Door', 'Marker', 'Highway', 'Overpass')))
        return self._clear_cache[b]

    def blocking(self, fp):
        """(blocked, the clearable things overlapping fp)."""
        clear = []
        for ck, rk, ofp, big, _o in self.w.near(fp):
            if (ck, rk) in self.gone or not townbuild.overlap(fp, ofp):
                continue
            if self.clearable(ck, rk):
                clear.append((ck, rk))
            elif big:
                return True, []
        return False, clear

    def take_out(self, clear):
        for ck, rk in clear:
            if (ck, rk) not in self.gone:
                self.gone.add((ck, rk))
                self.ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                self.moved.pop((ck, rk), None)

    def _held(self, x, y):
        fp = [(x - 40, y - 40), (x + 40, y - 40), (x + 40, y + 40), (x - 40, y + 40)]
        return any(big and townbuild.overlap(fp, ofp) and not self.clearable(ck, rk) for ck, rk, ofp, big, _o in self.w.near(fp))

    def terrace(self, x, y, rz, hx, hy, z=None, ease=EASE):
        """The ground in a box (half sides hx, hy, turned rz at x, y) brought level, eased back over ease; ground under big
        things already there is held. Returns the level, or None off the land."""
        c, sn = math.cos(rz), math.sin(rz)
        if z is None:
            hs = []
            for fx in (-1, -.5, 0, .5, 1):
                for fy in (-1, -.5, 0, .5, 1):
                    lx, ly = fx * hx, fy * hy
                    g = self.ground.at(x + lx * c + ly * sn, y - lx * sn + ly * c)
                    if g is not None:
                        hs.append(g)
            if not hs:
                return None
            z = sorted(hs)[len(hs) // 2]
        z = round(z / STEP) * STEP
        rad = math.hypot(hx, hy) + ease
        for gy in range(int((y - rad) // 128), int((y + rad) // 128) + 2):
            for gx in range(int((x - rad) // 128), int((x + rad) // 128) + 2):
                wx, wy = gx * 128.0, gy * 128.0
                dx, dy = wx - x, wy - y
                lx, ly = dx * c - dy * sn, dx * sn + dy * c
                d = math.hypot(max(abs(lx) - hx, 0.0), max(abs(ly) - hy, 0.0))
                if d >= ease or self._held(wx, wy):
                    continue
                u = d / ease
                u = u * u * (3 - 2 * u)
                for cx in ({gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}):
                    for cy in ({gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}):
                        f = self._form((cx, cy))
                        if not f:
                            continue
                        k = (gy - cy * 32) * 33 + (gx - cx * 32)
                        old = f['h'][k]
                        if old < 4.0:
                            continue                      # (the sea stays)
                        f['h'][k] = round((z + (old - z) * u) / STEP) * STEP
        self._reseat(x, y, rad)
        return z

    def _reseat(self, x, y, rad):
        """Things already standing on ground a terrace moved go up or down with it."""
        for cx in range(int((x - rad) // 4096), int((x + rad) // 4096) + 1):
            for cy in range(int((y - rad) // 4096), int((y + rad) // 4096) + 1):
                cell = self.w.grid.get((cx, cy))
                ck = self.gd.key(cell) if cell is not None else None
                c = self.pr.cells.get(ck) if ck else None
                for rk, r in (c['refs'].items() if c else ()):
                    p = r.get('p')
                    if not p or r.get('removed') or (ck, rk) in self.gone or math.hypot(p[0] - x, p[1] - y) > rad or self._held(p[0], p[1]):
                        continue
                    key = (ck, rk)
                    if key not in self.ground0:
                        self.ground0[key] = self.orig.at(p[0], p[1])
                    g0, g1 = self.ground0[key], self.ground.at(p[0], p[1])
                    if g0 is None or g1 is None:
                        continue
                    np_ = list(p)
                    np_[2] = round(p[2] + (g1 - g0), 1)
                    if abs(np_[2] - p[2]) >= 2.0:
                        self.moved[key] = np_
                    else:
                        self.moved.pop(key, None)

    def box(self, edid):
        if edid not in self.key_of:
            return None
        if edid not in self.boxes:
            self.boxes[edid] = townbuild.obnd(self.gd, self.key_of[edid])
        return self.boxes[edid]

    def slope(self, x, y, reach=FLAT_REACH):
        g = self.ground
        hs = [g.at(x + reach * math.cos(a), y + reach * math.sin(a)) for a in [k * math.pi / 4 for k in range(8)]]
        c = g.at(x, y)
        if c is None or any(h is None for h in hs):
            return 9.0
        return max(abs(h - c) for h in hs) / reach

    def middle(self, x, y):
        """The flattest free spot within SEEK of the road's top, and which way is down from it (toward the road)."""
        best = (self.slope(x, y), x, y)
        for r in (350.0, 700.0, 1050.0, SEEK):
            for k in range(12):
                a = k * math.pi / 6 + r / 1000.0
                px, py = x + r * math.cos(a), y + r * math.sin(a)
                s = self.slope(px, py)
                fp = [(px - 300, py - 300), (px + 300, py - 300), (px + 300, py + 300), (px - 300, py + 300)]
                if any(big for _c, _r, ofp, big, _o in self.w.near(fp) if townbuild.overlap(fp, ofp)):
                    continue
                if s < best[0] - 0.02:
                    best = (s, px, py)
        _s, mx, my = best
        # (downhill: the lowest of eight points round it; the road comes up from there)
        g = self.ground
        low = min(((g.at(mx + 1500 * math.cos(a), my + 1500 * math.sin(a)) or 1e9), a) for a in [k * math.pi / 4 for k in range(8)])
        return mx, my, low[1], best[0]

    def lay(self, key):
        name, ll, kind, mtype = SITES[key]
        x, y = self.geo.xy(ll)
        mx, my, down, s = self.middle(x, y)
        pl = Place(self, key, mx, my, down)
        before = len(self.ops)
        if kind in TERRACED:
            half = 1350.0 if kind == 'fort' else (650.0 if kind == 'radar' else (450.0 if kind in ('beacon', 'watcher', 'watchtower') else PLAZA))
            self.terrace(mx, my, -down, half, half)
        order = {'buildings': 0, 'fort': 1, 'ring': 2}
        for what, a in sorted(RECIPES[kind], key=lambda st: order.get(st[0], 3)):
            getattr(self, '_' + what)(pl, a)
        g = self.ground.at(mx, my)
        if g is not None:
            import worldrec
            o = worldrec.marker_op(self.gd, self.world, [round(mx, 1), round(my, 1), round(g + 60, 1)], name, mtype, flags=2)
            self.ops.append(o)
            self.cells.add(o['cell'])
        self.rep['places'][key] = {'name': name, 'at': [round(mx), round(my), round(g or 0)], 'cell': [int(mx // 4096), int(my // 4096)],
                                   'slope': round(s, 3), 'moved': round(math.hypot(mx - x, my - y)), 'things': len(self.ops) - before}

    # ----- the recipe's steps -----

    def _local(self, pl, lx, ly):
        """A point in the place's frame: +y up the hill (away from its road), +x to the right of that."""
        uy = (-math.cos(pl.down), -math.sin(pl.down))
        ux = (uy[1], -uy[0])
        return pl.x + ux[0] * lx + uy[0] * ly, pl.y + ux[1] * lx + uy[1] * ly

    def _one(self, pl, a):
        edid, lx, ly, face = a
        x, y = self._local(pl, lx, ly)
        yaw = (pl.down + math.pi / 2) if face == 'out' else self.rnd.uniform(0, math.tau)
        for k in range(24):
            r, a_ = 140.0 * k, k * 2.4
            px, py = x + r * math.cos(a_), y + r * math.sin(a_)
            if pl.inner is not None and math.hypot(px - pl.x, py - pl.y) > pl.inner:
                continue
            if pl.put(edid, px, py, yaw):
                return
        self.rep.setdefault('not_placed', []).append([pl.key, edid])

    def _row(self, pl, a):
        edid, n, step, lx0, ly = a
        for i in range(n):
            lx = lx0 + (i - (n - 1) / 2) * step if lx0 == 0.0 else lx0 + i * step
            x, y = self._local(pl, lx, ly)
            pl.put(edid, x, y, -pl.down + math.pi / 2)

    def _ring_of(self, pl, a):
        edid, n, r = a
        for i in range(n):
            t = i * math.tau / n
            x, y = pl.x + r * math.cos(t), pl.y + r * math.sin(t)
            pl.put(edid, x, y, math.atan2(-math.sin(t), math.cos(t)) + math.pi / 2)

    def _scatter(self, pl, items):
        for edid, n in items:
            for _i in range(n):
                for _try in range(14):
                    a = self.rnd.uniform(0, math.tau)
                    d = self.rnd.uniform(250.0, 1400.0)
                    if pl.put(edid, pl.x + d * math.cos(a), pl.y + d * math.sin(a), self.rnd.uniform(0, math.tau)):
                        break

    def _wreck(self, pl, a):
        edid, lx, ly = a
        x, y = self._local(pl, lx, ly)
        for k in range(24):
            r, a_ = 160.0 * k, k * 2.4
            if pl.put(edid, x + r * math.cos(a_), y + r * math.sin(a_), self.rnd.uniform(0, math.tau), sink=80.0, tilt=(0.22, -0.12)):
                return
        self.rep.setdefault('not_placed', []).append([pl.key, edid])

    def _upturned(self, pl, a):
        edid, n, r = a
        for i in range(n):
            t = pl.down + math.pi + (i - (n - 1) / 2) * 0.9
            x, y = pl.x + r * math.cos(t), pl.y + r * math.sin(t)
            box = self.box(edid)
            if box and pl.free(x, y, max(box[3] - box[0], box[4] - box[1]) / 2):
                # (a hull turned over as a roof: its deck on the ground)
                pl.put(edid, x, y, t, sink=-box[2] - box[5] + 40.0, tilt=(math.pi, 0.0), check=False)

    def _across(self, pl, a):
        """A row of barricades across the road where it comes up, a gap in its middle."""
        edid, n = a
        dx, dy = math.cos(pl.down), math.sin(pl.down)
        cx, cy = pl.x + dx * 1500, pl.y + dy * 1500
        for i in range(n):
            off = (i - (n - 1) / 2) * 260 + (200 if i >= n / 2 else -200)
            pl.put(edid, cx - dy * off, cy + dx * off, math.atan2(dx, dy) + math.pi / 2, check=False)

    def _buildings(self, pl, a):
        names, n, r0, r1 = a
        fits = [townbuild.Fit(self.by_edid[e]) for e in names if e in self.by_edid]
        if not fits:
            self.rep['missing'] |= set(names)
            return
        gone = self.gone
        brep = {'blocked': 0, 'steep': 0, 'buildings': 0, 'doors': 0}
        made = 0
        for _try in range(n * 60):
            if made >= n:
                break
            f = self.rnd.choice(fits)
            ang = self.rnd.uniform(0, math.tau)
            d = self.rnd.uniform(r0, r1 + 15.0 * _try)
            mx, my = pl.x + d * math.cos(ang), pl.y + d * math.sin(ang)
            rz = f.turn_for(pl.x - mx, pl.y - my)                # (its front to the place's middle)
            ox, oy, fp = f.placed(mx, my, rz)
            if any(math.hypot(mx - a_, my - b_) < c + max(f.width, f.depth) / 2 + APART for a_, b_, c in pl.taken):
                self.rep['crowded'] = self.rep.get('crowded', 0) + 1
                continue
            hs = [self.ground.at(px, py) for px, py in fp]
            blocked, clear = self.blocking(fp)
            if any(h is None for h in hs) or blocked:
                self.rep['big_in_way'] = self.rep.get('big_in_way', 0) + 1
                continue
            self.take_out(clear)
            bx = f.b['box']
            level = self.terrace(mx, my, rz, (bx[3] - bx[0]) / 2 + 120, (bx[4] - bx[1]) / 2 + 120, ease=500.0)
            if level is None:
                continue
            if townbuild._put(f, self.w, ox, oy, rz, fp, level, self.ops, gone, brep):
                pl.taken.append((mx, my, max(f.width, f.depth) / 2))
                made += 1
                for px, py in fp:
                    c = self.w.cell_at(px, py)
                    if c:
                        self.cells.add(c)
        self.rep['buildings'] += made
        for k_, v_ in brep.items():
            self.rep.setdefault('why', {})[k_] = self.rep.get('why', {}).get(k_, 0) + v_
        self.rep.setdefault('tries', 0)
        self.rep['tries'] += _try + 1

    def _wall_line(self, pl, pts, piece, gap_dir=None, gap=700.0):
        """Wall pieces along a closed or open line of points; none in the gap toward the road."""
        if piece == 'junk':
            names, plen = ('NVJunkWall03', 'NVJunkWall04'), 490.0
        else:
            names, plen = ('NVMcCarranWallReg01',), 500.0
        k = 0
        for a, b in zip(pts, pts[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            for i in range(int(L // plen)):
                mx, my = a[0] + ux * (i + 0.5) * plen, a[1] + uy * (i + 0.5) * plen
                if gap_dir is not None:
                    gx, gy = pl.x + math.cos(gap_dir) * 1e4, pl.y + math.sin(gap_dir) * 1e4
                    # (the piece nearest the line to the road is left out, and those within gap/2 of it)
                    ang = math.atan2(my - pl.y, mx - pl.x)
                    if abs((ang - gap_dir + math.pi) % math.tau - math.pi) * math.hypot(mx - pl.x, my - pl.y) < gap / 2:
                        continue
                if any(c > 250.0 and math.hypot(mx - a_, my - b_) < c + plen / 2 for a_, b_, c in pl.taken):
                    self.rep['wall_skipped'] = self.rep.get('wall_skipped', 0) + 1
                    continue
                e = names[k % len(names)]
                k += 1
                if piece == 'junk':
                    yaw = math.atan2(ux, uy)            # (junk walls lie along their y)
                else:
                    yaw = math.atan2(-uy, ux)           # (the McCarran wall along its x)
                pl.put(e, mx, my, yaw, r=plen / 2, sink=30.0, check=False)
                pl.taken.append((mx, my, 120.0))

    def _ring(self, pl, a):
        r = a['radius']
        if a.get('part', 1.0) >= 1.0:
            pl.inner = r - 500.0
        part = a.get('part', 1.0)
        n = max(8, int(math.tau * r * part // 490))
        start = pl.down + math.pi * part if part < 1.0 else 0.0
        if part < 1.0:
            # (an arc on the road's side only, centred on it)
            pts = [(pl.x + r * math.cos(pl.down + (i / n - 0.5) * math.tau * part), pl.y + r * math.sin(pl.down + (i / n - 0.5) * math.tau * part))
                   for i in range(n + 1)]
        else:
            pts = [(pl.x + r * math.cos(start + i * math.tau / n), pl.y + r * math.sin(start + i * math.tau / n)) for i in range(n + 1)]
        self._wall_line(pl, pts, a['piece'], gap_dir=pl.down)

    def _fort(self, pl, a):
        h = a['half']
        pl.inner = h - 420.0
        corners = [self._local(pl, sx * h, sy * h) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]
        self._wall_line(pl, corners, 'mccarran', gap_dir=pl.down, gap=650.0)
        for i, (cx, cy) in enumerate(corners[:4]):
            pl.put(('NVMcCarranWall02',)[0], cx, cy, pl.down, check=False)
            pl.taken.append((cx, cy, 340.0))
        # (sandbags either side of the way in)
        dx, dy = math.cos(pl.down), math.sin(pl.down)
        for k in (-1, 1):
            x, y = pl.x + dx * (h + 260) - dy * k * 420, pl.y + dy * (h + 260) + dx * k * 420
            pl.put('SandbagStraight', x, y, -pl.down, check=False)


def ops(gd, pr, world, side, cat=None, only=None, seed=5):
    """(ops, report, cells) for every place in SITES (or only those keys)."""
    cat = cat if cat is not None else townbuild.load(gd, __import__('server').kits_folder())
    B = Builder(gd, pr, world, side, cat, seed)
    for key in SITES:
        if only and key not in only:
            continue
        B.lay(key)
    B.rep['missing'] = sorted(B.rep['missing'])
    lands = []
    for k, f in sorted(B.forms.items()):
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': f})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items())]
    B.rep['land_cells'], B.rep['moved'] = len(lands), len(moves)
    return lands + moves + B.ops, B.rep, sorted(B.cells)
