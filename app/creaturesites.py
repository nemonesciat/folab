"""Where Waikiki's island animals live (sharklurk.py, islandbeasts.py; the user's decisions, 23 Nov 2026), and the one Undo that
puts them in. Placed the story session's standing way (its placement check, 23 Nov 2026): every animal on purpose, in its
own kind of ground, clear of what people walk to, in the pacing plan's areas (docs/waikiki-pacing-plan.md):

  sharklurk     the south shore's reef edges: shallow water near the shore, at the Missouri's beach and Hanauma Bay
                (`SHARK_AT`), never Waikiki's own surf (`SURF`) or a fishing village's beach
  coconut crab  rocky shores and beaches, just above the waterline, away from towns
  mongoose      low dry scrub and town edges (outside a settlement, not in it)
  cane toad     wet valley floors: low ground by water, and by the taro

A `Lay` is what the choice needs from the mod, read once (heights on a grid, the sea's level, what to keep off with how
far and why, roads, buildings, taro): `Lay.of(gd, pr, world)`, kept with `save`/`load` so sites can be tried again
without loading a 250 MB mod. `sites(lay, kind)` is pure: [(x, y, z, group size)]. Groups are small and spaced
(`GROUPS`, `APART`), breadcrumbs, not scatter.

Each animal stands as a ref of the mod's own creature with the game's respawn flag (`RESPAWN`, as the Vespids).
"""
import math
import random

STEP = 256.0                    # (the height grid's spacing)
RESPAWN = 0x8                   # (ACBS flag: comes back, as the game's own wildlife)

# what each kind keeps off: (kind of spot, how far); a spot's kind is keep_off's first word
KEEP = {
    'sharklurk': {'marker': 4000.0, 'door': 2500.0, 'arrival': 2500.0, 'named': 2500.0, 'way': 1500.0, 'Crest': 0.0},
    'crab': {'marker': 2500.0, 'door': 1200.0, 'arrival': 1200.0, 'named': 1500.0, 'way': 600.0, 'Crest': 600.0},
    'mongoose': {'marker': 2500.0, 'door': 1200.0, 'arrival': 1200.0, 'named': 1500.0, 'way': 600.0, 'Crest': 600.0},
    'toad': {'marker': 2500.0, 'door': 1200.0, 'arrival': 1200.0, 'named': 1500.0, 'way': 600.0, 'Crest': 600.0},
}
SETTLED = 5500.0                # (a settlement's marker: mongooses at its edge, between this and its KEEP)
ROAD_OFF = 350.0                # (not on a road: beside one is fine, breadcrumbs along the ways people walk)
BUILT_OFF = 250.0               # (past a building's own reach)
START_OFF = 5200.0              # (worldlife.SAFE: nothing hostile this near the new game's start)
SURF = 9000.0                   # (from Waikiki's middle: its own surf, never a sharklurk)
GROUPS = {'sharklurk': (8, (1, 2)), 'crab': (10, (2, 3)), 'mongoose': (10, (2, 3)), 'toad': (10, (2, 4))}   # (groups, size)
APART = {'sharklurk': 5000.0, 'crab': 7000.0, 'mongoose': 7000.0, 'toad': 6000.0}
SHARK_AT = ('Natatorium', 'Hanauma')   # (marker names, by their start: the shores the user named)
SHARK_REACH = 14000.0           # (along the shore from those)
SEED = 29


class Lay:
    """What sites need from the mod (plain numbers: pickles)."""

    def __init__(self):
        self.x0 = self.y0 = 0.0
        self.h = None               # (numpy rows y, columns x: height or nan)
        self.sea = 0.0
        self.spots = []             # [(x, y, what)]
        self.markers = []           # [(name, x, y, z)]
        self.roads = []
        self.built = []             # [(x, y, reach)]
        self.taro = []
        self.hives = []             # [(x, y)] of the Vespids' hives
        self.wet = []               # [(x, y)] under a cell's own water (streams, ponds), not the sea
        self.start = None
        self.middle = None
        self.cells = {}             # {(cx, cy): cell key}

    # ---------- reading the mod ----------

    @classmethod
    def of(cls, gd, pr, world, progress=print):
        import numpy as np
        import roadgen
        import vespidhives as VH
        lay = cls()
        grid = gd.grid(world)
        lay.cells = {k: gd.key(c) for k, c in grid.items()}
        xs = [k[0] for k in grid]
        ys = [k[1] for k in grid]
        lay.x0, lay.y0 = min(xs) * 4096.0, min(ys) * 4096.0
        nx = int((max(xs) + 1 - min(xs)) * 4096 / STEP) + 1
        ny = int((max(ys) + 1 - min(ys)) * 4096 / STEP) + 1
        g = roadgen.Ground(gd, pr, world)
        h = np.full((ny, nx), np.nan, np.float32)
        for j in range(ny):
            for i in range(nx):
                v = g.at(lay.x0 + i * STEP, lay.y0 + j * STEP)
                if v is not None:
                    h[j, i] = v
        lay.h = h
        progress('heights %d x %d' % (nx, ny))
        lay.sea = sea_level(gd, pr, world)
        lay.spots = [(x, y, what) for x, y, _d, what in VH.keep_off(gd, pr, world, why=True)]
        lay.markers = VH._markers(pr)
        lay.roads = VH._roads(gd, pr, world)
        lay.hives = []
        lay.built, lay.taro = _built_and_taro(gd, pr, world, lay.hives)
        lay.wet = _wet(gd, pr, world, lay)
        lay.start = start_of(gd, pr, world)
        try:
            import waikikilife
            lay.middle = waikikilife.middle(pr)[1]
        except Exception:
            lay.middle = None
        progress('spots %d, roads %d, buildings %d, taro %d' % (len(lay.spots), len(lay.roads), len(lay.built), len(lay.taro)))
        return lay

    def save(self, path):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump(self.__dict__, f)

    @classmethod
    def load(cls, path):
        import pickle
        lay = cls()
        with open(path, 'rb') as f:
            lay.__dict__.update(pickle.load(f))
        return lay

    # ---------- asking ----------

    def at(self, x, y):
        """The height at a spot (nearest grid point's bilinear), or None."""
        import numpy as np
        fx, fy = (x - self.x0) / STEP, (y - self.y0) / STEP
        i, j = int(fx), int(fy)
        if not (0 <= i < self.h.shape[1] - 1 and 0 <= j < self.h.shape[0] - 1):
            return None
        q = self.h[j:j + 2, i:i + 2]
        if np.isnan(q).any():
            return None
        tx, ty = fx - i, fy - j
        return float((q[0, 0] * (1 - tx) + q[0, 1] * tx) * (1 - ty) + (q[1, 0] * (1 - tx) + q[1, 1] * tx) * ty)

    def slope(self, x, y, r=256.0):
        """The most the ground rises over r round the spot (units per unit)."""
        z = self.at(x, y)
        if z is None:
            return None
        most = 0.0
        for k in range(8):
            a = math.tau * k / 8
            q = self.at(x + r * math.cos(a), y + r * math.sin(a))
            if q is None:
                return None
            most = max(most, abs(q - z) / r)
        return most

    def shore_dist(self, x, y, reach=2000.0):
        """How far to the nearest point where land meets the sea (searching rings out to reach), or None."""
        z = self.at(x, y)
        if z is None:
            return None
        wet = z < self.sea
        for r in range(128, int(reach) + 1, 128):
            n = max(8, int(math.tau * r / 128))
            for k in range(n):
                a = math.tau * k / n
                q = self.at(x + r * math.cos(a), y + r * math.sin(a))
                if q is not None and (q < self.sea) != wet:
                    return float(r)
        return None

    def nearest(self, x, y):
        """{kind of spot: (what, distance)} nearest a site, for the hand-over."""
        best = {}
        for a, b, what in self.spots:
            k = what.split(' ')[0]
            k = {'marker': 'settlement or marker', 'Crest': 'trail', 'way': 'trail sign or climb'}.get(k, k)
            d = math.hypot(x - a, y - b)
            if k not in best or d < best[k][1]:
                best[k] = (what, round(d))
        if self.roads:
            best['road'] = ('road piece', round(min(math.hypot(x - a, y - b) for a, b in self.roads)))
        if self.built:
            best['building'] = ('building', round(min(math.hypot(x - a, y - b) - r for a, b, r in self.built)))
        if getattr(self, 'hives', None):
            best['hive'] = ('Vespid hive', round(min(math.hypot(x - a, y - b) for a, b in self.hives)))
        if self.start:
            best['start'] = ('the new game start', round(math.hypot(x - self.start[0], y - self.start[1])))
        if self.middle:
            best['waikiki'] = ("Waikiki's middle", round(math.hypot(x - self.middle[0], y - self.middle[1])))
        return best


def sea_level(gd, pr, world):
    """The world's sea (its DNAM's second float), 0 when it has none."""
    import struct
    import recordio
    rec = pr.records.get(gd.key(world)) or recordio.load(gd, world)
    for s in rec['subs']:
        if s['tag'] == 'DNAM' and s.get('kind') == 'raw':
            raw = bytes.fromhex(s['value'])
            if len(raw) >= 8:
                return struct.unpack_from('<f', raw, 4)[0]
    return 0.0


def start_of(gd, pr, world=None):
    """(x, y) of the mod's own new game's start when it is outside in `world`, else None."""
    ng = getattr(pr, 'newgame', None) or {}
    p, cell = ng.get('p'), ng.get('cell')
    if not p or not cell:
        return None
    if world is not None and cell not in {gd.key(c) for c in gd.grid(world).values()}:
        return None
    return float(p[0]), float(p[1])


BUILT_WORDS = ('house', 'bldg', 'building', 'shack', 'store', 'motel', 'hotel', 'church', 'school', 'station', 'wall',
               'hut', 'tower', 'trailer', 'mobilehome', 'casino', 'shop', 'warehouse', 'office', 'barn', 'garage')


BIG = (300.0, 120.0)        # (a placed model this wide and tall is something to keep out of, whoever made it)
SOLID_TAGS = ('STAT', 'SCOL', 'ACTI', 'CONT', 'FURN', 'DOOR', 'MSTT')
HIVE_OFF = 4000.0           # (the Vespids' hives: their own swarm round them)


def _built_and_taro(gd, pr, world, hives=None):
    """([(x, y, reach)] of every big model placed in the world's cells, the mod's own or the game's (wider than BIG[0],
    taller than BIG[1] by its bounds: buildings, walls, the mod's own pieces and landmarks; reach half its widest),
    [(x, y)] of the taro). hives: a list to fill with [(x, y)] of the Vespids' hives (editor ID with 'hive')."""
    import birds
    import waikikilife
    cells = {gd.key(c) for c in gd.grid(world).values()}
    seen, built, taro = {}, [], []
    for ck, c in pr.cells.items():
        if ck not in cells:
            continue
        for r in c.get('refs', {}).values():
            b, p = r.get('base'), r.get('p')
            if not b or not p or r.get('removed'):
                continue
            if b not in seen:
                e = birds._edid(gd, pr, b).lower()
                kind = 'taro' if 'taro' in e else None
                if kind is None and 'hive' in e and 'heart' not in e:
                    kind = 'hive'
                if kind is None and waikikilife._tag(gd, pr, b) in SOLID_TAGS:
                    box = _bounds(gd, pr, b)
                    if box and max(box[3] - box[0], box[4] - box[1]) > BIG[0] and box[5] - box[2] > BIG[1]:
                        kind = ('built', 0.5 * max(box[3] - box[0], box[4] - box[1]))
                seen[b] = kind
            k = seen[b]
            sc = float(r.get('s', 1.0) or 1.0)
            if k == 'taro':
                taro.append((p[0], p[1]))
            elif k == 'hive':
                if hives is not None:
                    hives.append((p[0], p[1]))
            elif k and k[1] * sc * 2 > BIG[0]:
                built.append((p[0], p[1], k[1] * sc))
    return built, taro


def _wet(gd, pr, world, lay, step=256.0):
    """[(x, y)] of land under a cell's own water (project.water: a cell's height that isn't the world's sea), a point a
    step."""
    out = []
    keys = {gd.key(c): k for k, c in gd.grid(world).items()}
    for ck, level in (getattr(pr, 'water', None) or {}).items():
        if level is None or ck not in keys or abs(level - lay.sea) < 1.0:
            continue
        cx, cy = keys[ck]
        for j in range(16):
            for i in range(16):
                x, y = cx * 4096.0 + (i + 0.5) * step, cy * 4096.0 + (j + 0.5) * step
                z = lay.at(x, y)
                if z is not None and z < level:
                    out.append((x, y))
    return out


def _bounds(gd, pr, base):
    """OBND (x1, y1, z1, x2, y2, z2) of a base, the mod's own or the game's."""
    import recordio
    try:
        rec = pr.records.get(base) if base.startswith('+') else recordio.load(gd, gd.from_key(base))
    except Exception:
        return None
    for s in (rec or {}).get('subs', ()):
        if s['tag'] == 'OBND':
            return [f['value'] for f in s['fields'] if 'name' in f]
    return None


WAIKIKI_R = 14000.0             # (waikikilife.WAIKIKI_R: nothing hostile round Waikiki's hotels, its own surf included)
SHARK_START_OFF = 9000.0        # (the start is Hanauma Bay's beach: sharks only out past its reef)
SHARK_SURF = 20000.0            # (from Waikiki's middle: its own surf, Queen's and Kapiolani's beaches, never a shark)
SETTLEMENT_WORDS = ('Camp', 'Village', 'Terraces', 'Palms', 'Kai', 'Marina', 'Hotel', 'Lodge')
DEPTH = (80.0, 450.0)           # (a sharklurk's water: reef shallows to the drop-off)
SHORE = {'sharklurk': 900.0, 'crab': 600.0}     # (this near where land meets sea)
DRY_OF_SHORE = 500.0            # (mongooses and toads: off the beach, which is the crabs')
CRAB_TOP, MONGOOSE_TOP, TOAD_TOP = 260.0, 1600.0, 2600.0   # (over the sea: how high each lives)
STEEP = 0.45
TARO_NEAR = 1200.0
VALLEY = 200.0                  # (a valley floor: this much under the ground round it)
WET_NEAR = 800.0                # (by a stream or pond: a cell's own water over the ground)


# ---------- the grid ----------

def _shift(a, dj, di, fill):
    """a moved so out[j, i] = a[j + dj, i + di] (fill past the edge)."""
    import numpy as np
    out = np.full(a.shape, fill, a.dtype)
    ny, nx = a.shape
    sj0, sj1 = max(0, dj), min(ny, ny + dj)
    si0, si1 = max(0, di), min(nx, nx + di)
    out[sj0 - dj:sj1 - dj, si0 - di:si1 - di] = a[sj0:sj1, si0:si1]
    return out


class Grid:
    """Masks and measures over a Lay's height grid (numpy), each made once."""

    def __init__(self, lay):
        import numpy as np
        self.lay = lay
        self.h = lay.h
        self.ny, self.nx = lay.h.shape
        self.land = ~np.isnan(lay.h)
        self._near = {}
        self._score = {}
        self._slope = self._shore = self._valley = self._main = None

    def cell(self, x, y):
        return int(round((x - self.lay.x0) / STEP)), int(round((y - self.lay.y0) / STEP))

    def near(self, pts, r, key=None):
        """Grid cells within r of any of pts [(x, y)]."""
        import numpy as np
        if key and (key, r) in self._near:
            return self._near[(key, r)]
        m = np.zeros(self.h.shape, bool)
        k = int(math.ceil(r / STEP))
        oy, ox = np.mgrid[-k:k + 1, -k:k + 1]
        disc = (ox * STEP) ** 2 + (oy * STEP) ** 2 <= r * r
        for x, y in pts:
            i, j = self.cell(x, y)
            i0, i1, j0, j1 = max(0, i - k), min(self.nx, i + k + 1), max(0, j - k), min(self.ny, j + k + 1)
            if i0 >= i1 or j0 >= j1:
                continue
            m[j0:j1, i0:i1] |= disc[j0 - j + k:j1 - j + k, i0 - i + k:i1 - i + k]
        if key:
            self._near[(key, r)] = m
        return m

    def slope(self):
        """The most the ground rises to a neighbour (units per unit)."""
        import numpy as np
        if self._slope is None:
            s = np.zeros(self.h.shape, np.float32)
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    if dj or di:
                        d = np.abs(_shift(self.h, dj, di, np.nan) - self.h) / (STEP * math.hypot(di, dj))
                        s = np.fmax(s, np.nan_to_num(d, nan=0.0))
            self._slope = s
        return self._slope

    def shore(self):
        """[(x, y)] of cells where land meets the sea (a cell and a neighbour either side of the sea's level)."""
        import numpy as np
        if self._shore is None:
            wet = self.land & (np.nan_to_num(self.h, nan=1e9) < self.lay.sea)
            dry = self.land & ~wet
            c = np.zeros(wet.shape, bool)
            for dj, di in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                c |= wet & _shift(dry, dj, di, False)
            ys, xs = np.nonzero(c)
            self._shore = list(zip((self.lay.x0 + xs * STEP).tolist(), (self.lay.y0 + ys * STEP).tolist()))
        return self._shore

    def valley(self, r=1600.0):
        """How much lower each cell is than the middle of the ground round it at r."""
        import numpy as np
        if self._valley is None:
            k = r / STEP
            ring = [_shift(self.h, int(round(k * math.sin(math.tau * q / 12))), int(round(k * math.cos(math.tau * q / 12))), np.nan)
                    for q in range(12)]
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                self._valley = np.nanmedian(np.stack(ring), axis=0) - self.h
        return self._valley

    def main(self):
        """The island itself: the dry land joined to its highest point (islets off the shore left out: nobody walks there)."""
        import numpy as np
        if self._main is None:
            dry = self.land & (np.nan_to_num(self.h, nan=-1e9) >= self.lay.sea)
            seen = np.zeros(dry.shape, bool)
            j, i = np.unravel_index(int(np.nanargmax(np.where(dry, self.h, np.nan))), dry.shape)
            todo = [(j, i)]
            seen[j, i] = True
            while todo:
                j, i = todo.pop()
                for dj, di in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    a, b = j + dj, i + di
                    if 0 <= a < self.ny and 0 <= b < self.nx and dry[a, b] and not seen[a, b]:
                        seen[a, b] = True
                        todo.append((a, b))
            self._main = seen
        return self._main

    def kept(self, kind):
        """Cells `kind` keeps off (KEEP's spots, roads, buildings, the start, Waikiki)."""
        import numpy as np
        lay = self.lay
        m = np.zeros(self.h.shape, bool)
        by = {}
        for x, y, what in lay.spots:
            d = KEEP[kind].get(what.split(' ')[0])
            if d:
                by.setdefault(d, []).append((x, y))
        for d, pts in by.items():
            m |= self.near(pts, d, 'spots %s' % sorted(KEEP[kind].items()))
        m |= self.near(lay.roads, ROAD_OFF, 'roads')
        reach = {}
        for x, y, r in lay.built:
            reach.setdefault(round(r + BUILT_OFF, -1), []).append((x, y))
        for r, pts in reach.items():
            m |= self.near(pts, r, 'built')
        if getattr(lay, 'hives', None):
            m |= self.near(lay.hives, HIVE_OFF, 'hives')
        if getattr(lay, 'hives', None):
            m |= self.near(lay.hives, HIVE_OFF, 'hives')
        if lay.start:
            m |= self.near([lay.start], SHARK_START_OFF if kind == 'sharklurk' else START_OFF)
        if lay.middle:
            m |= self.near([lay.middle], SHARK_SURF if kind == 'sharklurk' else WAIKIKI_R)
        return m

    def score(self, kind):
        """A score for `kind` on every cell (higher better), nan where it doesn't belong."""
        import numpy as np
        if kind in self._score:
            return self._score[kind]
        lay, sea = self.lay, self.lay.sea
        h = np.nan_to_num(self.h, nan=-1e9)
        ok = self.land & ~self.kept(kind)
        if kind == 'sharklurk':
            depth = sea - h
            near = [(m[1], m[2]) for m in lay.markers if m[0].startswith(SHARK_AT) or m[0] == 'USS Missouri']
            ok &= (depth >= DEPTH[0]) & (depth <= DEPTH[1]) & self.near(near, SHARK_REACH)
            ok &= self.near(self.shore(), SHORE['sharklurk'], 'shore')
            s = 0.3 * depth + 300.0 * self.near(self.shore(), 400.0, 'shore')
        elif kind == 'crab':
            ok &= self.main() & (h >= sea + 8) & (h <= sea + CRAB_TOP) & self.near(self.shore(), SHORE['crab'], 'shore')
            s = 300.0 * np.minimum(self.slope(), 0.6) + 300.0 * self.near(self.shore(), 300.0, 'shore')
        else:
            ok &= self.main() & (h >= sea + 8) & (self.slope() <= STEEP) & ~self.near(self.shore(), DRY_OF_SHORE, 'shore')
            if kind == 'mongoose':
                towns = [(m[1], m[2]) for m in lay.markers if any(w in m[0] for w in SETTLEMENT_WORDS)]
                ok &= h <= MONGOOSE_TOP
                s = 600.0 * self.near(towns, SETTLED, 'towns') + 300.0 * self.near(lay.roads, 2500.0, 'roads') - 0.1 * h - 400.0 * self.slope()
            elif kind == 'toad':
                taro = self.near(lay.taro, TARO_NEAR, 'taro')
                wet = self.near(getattr(lay, 'wet', ()), WET_NEAR, 'wet')
                v = np.nan_to_num(self.valley(), nan=0.0)
                ok &= (h <= TOAD_TOP) & (taro | wet | (v >= VALLEY))
                s = 800.0 * taro + 600.0 * wet + v - 0.15 * h - 400.0 * self.slope()
            else:
                raise KeyError(kind)
        self._score[kind] = np.where(ok, s, np.nan)
        return self._score[kind]

    def may_stand(self, kind, x, y):
        import numpy as np
        i, j = self.cell(x, y)
        return 0 <= i < self.nx and 0 <= j < self.ny and not np.isnan(self.score(kind)[j, i])


def sites(lay, kind, seed=SEED, grid=None):
    """[(x, y, z, n, score)]: where each group of `kind` stands (z the ground there) and how many it has."""
    import numpy as np
    g = grid or Grid(lay)
    sc = g.score(kind)
    groups, (lo, hi) = GROUPS[kind]
    rnd = random.Random('%s %s' % (seed, kind))
    js, is_ = np.nonzero(~np.isnan(sc))
    cands = [(float(sc[j, i]) + rnd.uniform(0, 250.0), lay.x0 + i * STEP, lay.y0 + j * STEP) for j, i in zip(js.tolist(), is_.tolist())]
    # (the best ground first, with a little chance in it so groups aren't all on the one best stretch)
    cands.sort(key=lambda c: -c[0])
    out = []
    for s, x, y in cands:
        if len(out) >= groups:
            break
        if any(math.hypot(x - a, y - b) < APART[kind] for a, b, _z, _n, _s in out):
            continue
        out.append((x, y, round(lay.at(x, y), 1), rnd.randint(lo, hi), round(s, 1)))
    return out


def members(lay, kind, x, y, n, seed=SEED, grid=None):
    """[(x, y, z, turn)] for each animal of a group round x, y: each on a cell its kind may stand on, a few steps apart."""
    g = grid or Grid(lay)
    rnd = random.Random('%s %s %s %s' % (seed, kind, x, y))
    out = []
    for k in range(n):
        for _t in range(40):
            a, d = rnd.uniform(0, math.tau), (0 if k == 0 else rnd.uniform(150.0, 420.0))
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if not g.may_stand(kind, px, py):
                continue
            z = lay.at(px, py)
            if z is None or any(math.hypot(px - q[0], py - q[1]) < 120 for q in out):
                continue
            out.append((round(px, 1), round(py, 1), round(z + 12.0, 1), round(rnd.uniform(0, math.tau), 4)))
            break
    return out


def all_sites(lay, seed=SEED):
    """{kind: [{'x', 'y', 'z', 'n', 'members', 'score', 'nearest'}]}."""
    g = Grid(lay)
    out = {}
    for kind in KEEP:
        rows = []
        for x, y, z, n, s in sites(lay, kind, seed, g):
            m = members(lay, kind, x, y, n, seed, g)
            rows.append({'x': x, 'y': y, 'z': z, 'n': len(m), 'members': m, 'score': s, 'nearest': lay.nearest(x, y)})
        out[kind] = rows
    return out


# ---------- the Undo ----------

STEP_LABEL = "Island animals: Sharklurks, mongooses, coconut crabs, cane toads"
CREATURE_OF = {'sharklurk': 'sharklurk', 'crab': 'crab', 'mongoose': 'mongoose', 'toad': 'toad'}


def _respawning(rec):
    for s in rec['subs']:
        if s['tag'] == 'ACBS':
            for f in s['fields']:
                if f.get('name') == 'Flags':
                    f['value'] = int(f['value']) | RESPAWN
    return rec


def _beast(gd, kind, slug):
    """An island beast's CREA, respawning, its game drops and the radscorpion's poison left out (a mongoose doesn't drop
    giant rat meat, a crab no poison gland and no sting's poison)."""
    import islandbeasts as IB
    rec = IB.creature(gd, kind, slug)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('INAM', 'EITM')]
    return _respawning(rec)


def ops(gd, pr, lay, slug=None, seed=SEED):
    """(ops, report): the records (the Sharklurk's five, a creature for each filler) and every animal placed. One Undo;
    nothing is changed here. Refuses when the mod already has the Sharklurk."""
    import api_quests as aq
    import library
    import recordio
    import sharklurk as SL
    if any(recordio.field(r, 'EDID') == SL.EDID for r in pr.records.values() if r.get('type') == 'CREA'):
        raise ValueError('the mod already has %s' % SL.EDID)
    slug = slug or library.slug(pr.name)
    names = ['meat', 'tooth', 'teeth', 'death', 'sharklurk', 'crab', 'mongoose', 'toad']
    K = dict(zip(names, aq._reserve(pr, len(names))))
    out = []
    for name, rec in SL.records(gd, slug, K):
        if name == 'sharklurk':
            _respawning(rec)
        out.append({'op': 'record_new', 'record': rec})
    for kind in ('crab', 'mongoose', 'toad'):
        out.append({'op': 'record_new', 'record': _beast(gd, kind, slug)})
    where = all_sites(lay, seed)
    report = {'keys': [K[n] for n in names], 'kinds': {}, 'animals': 0, 'cells': []}
    cells = set()
    for kind, rows in where.items():
        base = K[CREATURE_OF[kind]]
        for r in rows:
            for x, y, z, rz in r['members']:
                cell = lay.cells.get((math.floor(x / 4096.0), math.floor(y / 4096.0)))
                if not cell:
                    continue
                out.append({'op': 'add', 'cell': cell, 'base': base, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0})
                cells.add(cell)
                report['animals'] += 1
        report['kinds'][kind] = [{k: r[k] for k in ('x', 'y', 'z', 'n', 'nearest')} for r in rows]
    report['cells'] = sorted(cells)
    return out, report


def put_files(gd, pr):
    """Every body, fin and picture among the mod's own files. Returns their paths."""
    import islandbeasts as IB
    import sharklurk as SL
    return sorted(SL.put_files(gd, pr) + IB.put_files(gd, pr))


def build(server, progress=print, lay=None):
    """Into the open mod: files, then one Undo. Returns the report."""
    gd, pr = server.GD, server.PR
    world = next(w for w in gd.worlds() if gd.edid(w) == 'FOLabWaikiki')
    lay = lay or Lay.of(gd, pr, world, progress)
    o, rep = ops(gd, pr, lay)
    progress('files: painting the four bodies')
    rep['files'] = put_files(gd, pr)
    made = server.edit(STEP_LABEL, o)['made']
    assert made[:len(rep['keys'])] == rep['keys'], ('keys not as reserved', made[:5], rep['keys'][:5])   # (then the animals' refs)
    return rep
