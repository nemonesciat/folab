"""Things in the sea (the user, 21 Nov 2026: "yes, all those please" to wrecks to dive to, loot worth the swim, harder further
out, and the odd sea creature in deeper water). Only the game's own: its sunken boats, barges and the B-29 it sank in Lake
Mead, its levelled containers (lootplace's `KINDS`), its lakelurks (the only creature of its own that lives in water).

A wreck site is chosen on the sea's floor by depth under the water (`DEPTHS`: easy, middling, hard), clear of anything
else in the sea (`CLEAR`: piers, the Missouri, the freighter, the flotilla, the harbours), away from the new game's start,
the sites `APART` from each other. The wreck lies as the game lays its own in Lake Mead: along the floor's slope with a
list (`LIST`), bedded into the floor by a share of its height (`BED`), its highest point well under the water (`UNDER`).
The finds stand on the floor beside it, seated by lootplace's `Seat` (with `wet`: under water will do), their backs to
the hull. Lakelurks keep the middling and hard wrecks (`KEEPERS`), and a few more wander alone in deep water
(`DEEP_ONES`), nothing hostile within `worldlife.SAFE` of the start.

    ops(gd, pr, world, seed)    (ops, report), nothing applied"""
import math
import random
import re

import lootplace
import roadgen
import townbuild

# by band: the game's wrecks, depth under the water (from, to), what goes beside, how many, the keepers
WRECKS = (['Boat02a', 'Boat02b', 'Boat02c', 'Boat02d', 'Boat02e'],
          ['Boat01a', 'Boat01b', 'Boat01d', 'dlc04boatwrecked01'],
          ['SunkenB29', 'dlc04bargeozymandias'])
DEPTHS = ((220.0, 450.0), (880.0, 1060.0), (1060.0, 1350.0))   # (the big hulls stand ~930 tall: Lake Mead's B-29 lies ~1,300 down)
SITES = (3, 3, 2)
FINDS = ((['bag', 'food'], 1), (['ammo', 'medicine', 'military'], 2), (['military', 'explosives', 'guns', 'safe'], 3))
KEEPERS = ([], [('VSpawnTier3LakelurkMed', 2)], [('VSpawnTier3LakelurkMed', 3)])
DEEP_ONES = 4                   # (lakelurks alone in deep water)
DEEP_FROM = 1200.0
APART = 7000.0                  # (wreck sites from each other)
CLEAR = 1800.0                  # (nothing else in the sea this near a wreck's middle: plants and rocks apart)
NOT_IN_SEA = re.compile(r'seaplant|underwaterrock|radiationmarker|kelp|coral', re.I)
START_CLEAR = 6000.0
LIST = 0.35                     # (a sunken hull lies over on its side by up to this, as the game's do)
BED = 0.15                      # (and is in the floor by this share of its height)
UNDER = 80.0                    # (its highest point at least this under the water)
STEEP = 0.3                     # (the floor under it slopes no more than this)
ROUGH = 140.0                   # (nor strays from a plane by more than this)
STEP = 1024.0                   # (sites looked for on a grid this fine)


def _key(gd, edid, tags=('STAT', 'CREA', 'LVLC', 'CONT')):
    best = None
    for f, (_i, r) in gd.forms.items():
        if r.tag in tags and gd.edid(f) == edid and (best is None or f >> 24 < best >> 24):
            best = f
    return gd.key(best) if best is not None else None


def _things(gd, pr, world, cells):
    """(x, y) of everything standing in these cells (grid keys) but plants and rocks of the sea."""
    import settleup
    out, names = [], {}

    def wanted(base):
        if base not in names:
            names[base] = not NOT_IN_SEA.search(settleup._edid(gd, pr, base) or '')
        return names[base]
    grid = gd.grid(world)
    for xy in cells:
        c = grid.get(xy)
        if c is None:
            continue
        ck = gd.key(c)
        ch = (pr.cells.get(ck) or {}).get('refs', {})
        for r in gd.refs(c):
            rk = gd.key(r['ref'])
            if rk in ch and ch[rk].get('removed'):
                continue
            p = (ch.get(rk) or {}).get('p') or r['pos']
            if p and r['base'] in gd.forms and wanted(gd.key(r['base'])):
                out.append((p[0], p[1]))
        for rk, r in ch.items():
            if rk.startswith('+') and r.get('p') and r.get('base') and not r.get('removed') and wanted(r['base']):
                out.append((r['p'][0], r['p'][1]))
    return out


class Sea:
    def __init__(self, gd, pr, world, seed=5):
        self.gd, self.pr, self.world = gd, pr, world
        self.rng = random.Random(seed)
        self.G = roadgen.Ground(gd, pr, world)
        self.grid = gd.grid(world)
        self.start = tuple((pr.newgame or {}).get('p', [0, 0])[:2])
        self.ops, self.report = [], {'sites': [], 'finds': 0, 'locked': 0, 'keepers': 0, 'deep ones': 0}
        self.boxes = {}
        self.wrecks = []            # (footprint corners, z0, z1)
        self.wet = {}

    def box(self, key):
        if key not in self.boxes:
            self.boxes[key] = townbuild.obnd(self.gd, key)
        return self.boxes[key]

    def water(self, x, y):
        k = (int(x // 4096), int(y // 4096))
        if k not in self.wet:
            self.wet[k] = self.G.water(x, y)
        return self.wet[k]

    def sea_cells(self):
        """Grid keys of cells with sea in them (a corner or the middle under the water)."""
        out = []
        for (cx, cy) in self.grid:
            for fx, fy in ((0.5, 0.5), (0.05, 0.05), (0.95, 0.05), (0.05, 0.95), (0.95, 0.95)):
                d = self.depth(cx * 4096 + fx * 4096, cy * 4096 + fy * 4096)[0]
                if d is not None and d > 0:
                    out.append((cx, cy))
                    break
        return out

    def depth(self, x, y):
        z, w = self.G.at(x, y), self.water(x, y)
        return (None, None, None) if z is None or w is None else (w - z, z, w)

    def candidates(self, things, cells):
        near = {}
        for x, y in things:
            near.setdefault((int(x // CLEAR), int(y // CLEAR)), []).append((x, y))

        def crowded(x, y):
            kx, ky = int(x // CLEAR), int(y // CLEAR)
            return any(math.hypot(a - x, b - y) < CLEAR for dx in (-1, 0, 1) for dy in (-1, 0, 1) for a, b in near.get((kx + dx, ky + dy), ()))
        out = ([], [], [])
        for (cx, cy) in cells:
            for i in range(int(4096 // STEP)):
                for j in range(int(4096 // STEP)):
                    x, y = cx * 4096 + (i + 0.5) * STEP, cy * 4096 + (j + 0.5) * STEP
                    d, _z, _w = self.depth(x, y)
                    if d is None or math.hypot(x - self.start[0], y - self.start[1]) < START_CLEAR:
                        continue
                    for b, (lo, hi) in enumerate(DEPTHS):
                        if lo <= d < hi and not crowded(x, y):
                            out[b].append((x, y))
        return out

    def lay(self, key, x, y):
        """[x, y, z, rx, ry, rz] for a wreck lying on the floor here, or None."""
        box = self.box(key)
        if not box:
            return None
        rz = self.rng.uniform(0, math.tau)
        hx, hy = (box[3] - box[0]) / 2 * 0.8, (box[4] - box[1]) / 2 * 0.8
        mx, my = (box[3] + box[0]) / 2, (box[4] + box[1]) / 2
        local, sup = [], []
        for fx in (-1, 0, 1):
            for fy in (-1, 0, 1):
                lx, ly = mx + fx * hx, my + fy * hy
                wx, wy = lootplace._turn(lx, ly, rz)
                g = self.G.at(x + wx, y + wy)
                if g is None:
                    return None
                local.append((lx, ly))
                sup.append(g)
        n = len(local)
        sx, sy, sz = sum(l[0] for l in local) / n, sum(l[1] for l in local) / n, sum(sup) / n
        vxx = sum((l[0] - sx) ** 2 for l in local) or 1.0
        vyy = sum((l[1] - sy) ** 2 for l in local) or 1.0
        ax = sum((l[0] - sx) * (z - sz) for l, z in zip(local, sup)) / vxx
        ay = sum((l[1] - sy) * (z - sz) for l, z in zip(local, sup)) / vyy
        if abs(ax) > STEEP or abs(ay) > STEEP:
            return None
        if max(abs(sz + ax * (l[0] - sx) + ay * (l[1] - sy) - z) for l, z in zip(local, sup)) > ROUGH:
            return None
        tall = box[5] - box[2]
        lean = self.rng.uniform(-LIST, LIST)
        ry, rx = math.atan(ax) + lean, -math.atan(ay)
        zc = sz + ax * (mx - sx) + ay * (my - sy)
        z = zc - box[2] - BED * tall
        import navgen
        m = navgen._turn(rx, ry, rz)
        corners = [(box[i], box[j], box[k]) for i in (0, 3) for j in (1, 4) for k in (2, 5)]
        top = max(z + m[2][0] * a + m[2][1] * b + m[2][2] * c for a, b, c in corners)
        w = self.water(x, y)
        if w is None or top > w - UNDER:
            return None
        # (no corner of its keel left hanging over the floor)
        for a, b, c in corners:
            if c != box[2]:
                continue
            cx = x + m[0][0] * a + m[0][1] * b + m[0][2] * c
            cy = y + m[1][0] * a + m[1][1] * b + m[1][2] * c
            cz = z + m[2][0] * a + m[2][1] * b + m[2][2] * c
            g = self.G.at(cx, cy)
            if g is None or cz > g + 24:
                return None
        return [round(x, 1), round(y, 1), round(z, 1), round(rx, 4), round(ry, 4), round(rz % math.tau, 4)]

    def cell(self, x, y):
        c = self.grid.get((int(x // 4096), int(y // 4096)))
        return self.gd.key(c) if c is not None else None

    def feet(self, fp):
        for corners, z0, z1 in self.wrecks:
            yield (None, None, corners, z0, z1)


def ops(gd, pr, world, seed=5):
    S = Sea(gd, pr, world, seed)
    sea = S.sea_cells()
    near = {(a + dx, b + dy) for a, b in sea for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    cands = S.candidates(_things(gd, pr, world, near), sea)
    S.report['sea cells'] = len(sea)
    P = lootplace.Plan(gd, pr, world, seed)
    seat = lootplace.Seat(gd, pr, world)
    seat.wet = True
    seat.feet = S.feet
    O = lootplace.Outside(P, None, seat, S.start)
    O.ok_spot = lambda x, y: True
    taken = []
    for band in (2, 1, 0):
        pool = cands[band][:]
        S.rng.shuffle(pool)
        got = 0
        for x, y in pool:
            if got >= SITES[band]:
                break
            if any(math.hypot(x - a, y - b) < APART for a, b in taken):
                continue
            names = WRECKS[band][:]
            S.rng.shuffle(names)
            used = [st['wreck'] for st in S.report['sites']]
            names = [n for n in names if n not in used] or names    # (each wreck once while there are others)
            name = names[0]
            if band == 2 and 'SunkenB29' not in used:
                name = 'SunkenB29'
            key = _key(gd, name, ('STAT',))
            p = None
            for _t in range(6):
                p = S.lay(key, x, y)
                if p:
                    break
            ck = S.cell(x, y)
            if not p or not ck:
                continue
            box = S.box(key)
            mark = (len(S.ops), len(P.ops), P.report['finds'], P.report['locked'])
            S.ops.append({'op': 'add', 'cell': ck, 'base': key, 'p': p, 's': 1.0})
            fp = [(p[0] + a, p[1] + b) for a, b in (lootplace._turn(lx, ly, p[5]) for lx, ly in ((box[0], box[1]), (box[3], box[1]), (box[3], box[4]), (box[0], box[4])))]
            S.wrecks.append((fp, p[2] + box[2] - 200, p[2] + box[5] + 200))
            taken.append((x, y))
            got += 1
            # finds on the floor round it, their backs to the hull
            kinds, n = FINDS[band]
            anchor = (p[0], p[1], p[2], p[5], 1.0, box)
            put = 0
            for k in range(n):
                kind = kinds[k % len(kinds)]
                if kind == 'safe':
                    edid = lootplace.KINDS['safe'][band][0][0]
                    lo, hi = lootplace.KINDS['safe'][band][0][2]
                    lock = P.rng.choice([v for v in (25, 50, 75, 100) if lo <= v <= hi])
                else:
                    edid, lock = P.choose(kind, band)
                fb = P.box(edid) if edid else None
                if not fb:
                    continue
                r = max(fb[3] - fb[0], fb[4] - fb[1]) / 2
                seat.load(p[0], p[1])
                for fx, fy, frz in O.beside(anchor, edid):
                    g = S.G.at(fx, fy)
                    if g is None or not seat.free(fx, fy, r):
                        continue
                    q = seat.at(fx, fy, frz, fb, g)
                    fck = S.cell(fx, fy)
                    if q is None or fck is None:
                        continue
                    P.add(fck, edid, q, lock=lock, spot='wreck %d' % band, band=band)
                    seat.take(fx, fy, r)
                    put += 1
                    break
            if not put:                     # (a wreck with nothing beside it isn't worth the swim: none here)
                del S.ops[mark[0]:], P.ops[mark[1]:]
                P.report['finds'], P.report['locked'] = mark[2], mark[3]
                S.wrecks.pop()
                taken.pop()
                got -= 1
                continue
            # who keeps it
            kept = 0
            for edid, count in KEEPERS[band]:
                ckey = _key(gd, edid, ('CREA', 'LVLC'))
                for _c in range(count):
                    for _t in range(8):
                        a = S.rng.uniform(0, math.tau)
                        d = max(box[3] - box[0], box[4] - box[1]) / 2 + S.rng.uniform(250, 600)
                        cx, cy = p[0] + math.sin(a) * d, p[1] + math.cos(a) * d
                        dd, z, w = S.depth(cx, cy)
                        cck = S.cell(cx, cy)
                        if dd is None or dd < 200 or cck is None:
                            continue
                        S.ops.append({'op': 'add', 'cell': cck, 'base': ckey, 'p': [round(cx, 1), round(cy, 1), round(z + 30, 1), 0.0, 0.0, round(S.rng.uniform(0, math.tau), 3)], 's': 1.0})
                        kept += 1
                        break
            S.report['keepers'] += kept
            S.report['sites'].append({'wreck': name, 'band': band, 'at': [round(p[0]), round(p[1])], 'depth': round(S.depth(x, y)[0]),
                                      'finds': put, 'keepers': kept})
    # the odd one alone in deep water
    import worldlife
    pool = []
    for (cx, cy) in sea:
        x, y = cx * 4096 + 2048, cy * 4096 + 2048
        d, z, w = S.depth(x, y)
        if d is not None and d > DEEP_FROM and math.hypot(x - S.start[0], y - S.start[1]) > worldlife.SAFE:
            pool.append((x, y, z))
    S.rng.shuffle(pool)
    ckey = _key(gd, 'VSpawnTier3LakelurkMed', ('CREA', 'LVLC'))
    alone = []
    for x, y, z in pool:
        if len(alone) >= DEEP_ONES:
            break
        if any(math.hypot(x - a, y - b) < APART for a, b in alone + taken):
            continue
        S.ops.append({'op': 'add', 'cell': S.cell(x, y), 'base': ckey, 'p': [round(x, 1), round(y, 1), round(z + 30, 1), 0.0, 0.0, round(S.rng.uniform(0, math.tau), 3)], 's': 1.0})
        alone.append((x, y))
    S.report['deep ones'] = len(alone)
    S.report['deep at'] = [[round(a), round(b)] for a, b in alone]
    S.report['finds'] = P.report['finds']
    S.report['locked'] = P.report['locked']
    return S.ops + P.ops, S.report
