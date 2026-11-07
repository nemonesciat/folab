"""Real heights to game ground: how big, how high, and what that comes to before anything is made.

A cell is 4096 units; 70 units are a metre, so a cell is about 58.5 m and 1 km about 17 cells. Real size soon runs out: a square degree
of the Earth is near 2,000 cells across, and the game's largest world has 16,396 cells in all. So:

    compress    real ground for each stretch of game ground. 1 is real size, 10 puts 10 m of the real world in 1 m of game.
    exag        how much taller than a true model at that scale. 1 keeps the real slopes, 2 doubles them. Bethesda's own
                land is steep for its size; heavily compressed land looks flat without some.
    base        the real height, in metres, that comes out at z 0. The world's water stands at z 0, so it's the sea or the lake.

    z = (height - base) * 70 / compress * exag

Heights go on a grid of land points shared across the whole world before they're cut into cells, whole 8-unit steps (all the
game's VHGT can hold in a cell that starts on one), and no two neighbours further apart than a VHGT step can reach (1,016 units in
128: nearly a wall). Cut after that, cells meet exactly, every one starts on a step, and nothing is left for the writer to round."""
import array
import math

CELL = 4096
POINT = 128
PER_CELL = 32
STEP = 8
UNITS_PER_M = 70.0
MAX_RISE = 127 * STEP                 # (a VHGT step's reach)

# Measured from the game's own files: the largest world (WastelandNV) has 16,396 cells, DLC worlds are 64 x 64, no land anywhere stands below -7,192 or
# above 31,024, a cell's land takes 4,500-10,200 bytes uncompressed.
SOFT_CELLS = 4096                     # the size of a whole DLC world: past it, a warning
HARD_CELLS = 16384                    # the size of the game's own largest: past it, no
MAX_SIDE = 256                        # cells across
Z_LOW, Z_HIGH = -8000, 32000          # the game's own land stays within this
PLUGIN_BYTES_CELL = 5600              # (measured: painted, compressed; see tests/test_mapworld.py)
SECONDS_CELL = 0.03
COMPRESSIONS = [1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200, 300, 500, 1000]
DEFAULT_SIDE = 48                     # the whole file comes out about this many cells across by default


def metres_per_cell(compress=1.0):
    return CELL / UNITS_PER_M * compress


def cells_for_km(compress=1.0):
    return 1000.0 / metres_per_cell(compress)


def height_of(metres, base, compress, exag):
    """Where a real height comes out, before it's put on a step."""
    return (metres - base) * UNITS_PER_M / compress * exag


def default_compress(raster, mpp=None):
    """The gentlest scale from the list that fits the whole file within the default size."""
    mx, my = raster.metres_per_pixel(mpp or 30.0)
    wide = max((raster.w - 1) * mx, (raster.h - 1) * my)
    for c in COMPRESSIONS:
        if wide / metres_per_cell(c) <= DEFAULT_SIDE:
            return c
    return COMPRESSIONS[-1]


def default_exag(compress):
    """A true model at heavy compression looks flat: a little more height the smaller it gets."""
    return 1.0 if compress <= 2 else 1.5 if compress <= 5 else 2.0 if compress <= 20 else 3.0


def elevation_range(raster, opts):
    """(what to multiply a file's value by, what to add) to get metres. A plain picture has no heights until it's told."""
    if getattr(raster, 'folab', None):
        lo, hi = raster.folab['low'] / UNITS_PER_M, raster.folab['high'] / UNITS_PER_M
        return hi - lo, lo
    if raster.plain:
        lo, hi = float(opts.get('low_m', 0.0)), float(opts.get('high_m', 1000.0))
        return hi - lo, lo
    return 1.0, 0.0


def default_base(raster, opts=None):
    """Sea level when the file reaches the sea, else just under the file's lowest ground (land all dry, no great height to carry)."""
    vs, vo = elevation_range(raster, opts or {})
    lo, _hi, missing = raster.stats()
    lo = lo * vs + vo
    if lo <= 2.0 or missing > raster.w * raster.h * 0.02:
        return 0.0 if lo > -500 else round(lo)
    return float(math.floor(lo) - 1)


def mpp_of(raster, opts):
    if getattr(raster, 'folab', None) and not raster.geo:
        return POINT / UNITS_PER_M, POINT / UNITS_PER_M          # (one of FOLab's own: a pixel is a land point)
    return raster.metres_per_pixel(float(opts.get('mpp') or 30.0))


class Plan:
    """What's asked, worked out: rect in pixel centres (col0, row0, col1, row1), snapped to whole cells; W x H cells."""

    def __init__(self, raster, opts=None):
        o = dict(opts or {})
        self.raster, self.opts = raster, o
        self.compress = max(0.01, float(o.get('compress') or default_compress(raster, o.get('mpp'))))
        self.exag = float(o['exag']) if o.get('exag') not in (None, '') else default_exag(self.compress)
        self.vs, self.vo = elevation_range(raster, o)
        self.base = float(o['base']) if o.get('base') not in (None, '') else default_base(raster, o)
        self.mx, self.my = mpp_of(raster, o)
        self.upx = self.mx * UNITS_PER_M / self.compress        # game units from one pixel to the next
        self.upy = self.my * UNITS_PER_M / self.compress
        self.k = UNITS_PER_M / self.compress * self.exag
        self.ppx = POINT / self.upx                             # pixels from one land point to the next
        self.ppy = POINT / self.upy
        r = o.get('rect') or [0, 0, raster.w - 1, raster.h - 1]
        c0, r0, c1, r1 = [float(v) for v in r]
        c0, c1 = sorted((max(0.0, min(raster.w - 1.0, c0)), max(0.0, min(raster.w - 1.0, c1))))
        r0, r1 = sorted((max(0.0, min(raster.h - 1.0, r0)), max(0.0, min(raster.h - 1.0, r1))))
        pcx, pcy = self.ppx * PER_CELL, self.ppy * PER_CELL      # pixels a cell
        # whole cells: as near as fits within the rectangle, at least one
        self.W = max(1, int((c1 - c0) / pcx + 1e-6))
        self.H = max(1, int((r1 - r0) / pcy + 1e-6))
        # (kept to its middle, moved in if a rectangle less than a cell wide hangs off the file)
        self.col0 = max(0.0, (c0 + c1 - self.W * pcx) / 2)
        self.row0 = max(0.0, (r0 + r1 - self.H * pcy) / 2)
        self.x0, self.y0 = -(self.W // 2), -(self.H // 2)       # the world's south-west cell: the middle at the origin

    def count(self):
        return self.W * self.H

    def game_xy(self, col, row):
        """Where a pixel comes out in game units."""
        return (self.x0 * CELL + (col - self.col0) * self.upx,
                (self.y0 + self.H) * CELL - (row - self.row0) * self.upy)

    def pixel_of(self, x, y):
        return (self.col0 + (x - self.x0 * CELL) / self.upx,
                self.row0 + ((self.y0 + self.H) * CELL - y) / self.upy)

    def z_of_value(self, v):
        return (v * self.vs + self.vo - self.base) * self.k

    def report(self):
        """All the numbers for the preview. 'stop' is why it can't be made, 'warnings' what to think about."""
        n = self.count()
        mc = metres_per_cell(self.compress)
        lo, hi, missing = self.raster.stats()
        zlo, zhi = self.z_of_value(lo), self.z_of_value(hi)
        warn, stop = [], None
        if n > HARD_CELLS or max(self.W, self.H) > MAX_SIDE:
            stop = ('%s cells, %d x %d: FOLab stops at %s (%d across), the size of the game\'s own largest world. Compress it more or choose a smaller rectangle.'
                    % (format(n, ','), self.W, self.H, format(HARD_CELLS, ','), MAX_SIDE))
        elif n > SOFT_CELLS:
            warn.append('%s cells is more than a whole DLC world (%s), and every one is yours to fill. It will take a while to make, and a while for the game to load. Fine for land to explore; a lot to dress.' % (format(n, ','), format(SOFT_CELLS, ',')))
        if zhi > Z_HIGH or zlo < Z_LOW:
            warn.append('Heights run from %s to %s; the game\'s own land stays between %s and %s. Far beyond that hasn\'t been seen to work: lower the height or the base level.' % (
                format(round(zlo), ','), format(round(zhi), ','), format(Z_LOW, ','), format(Z_HIGH, ',')))
        if self.ppx < 0.1 or self.ppy < 0.1:
            warn.append('The file has one point for every %d land points at this scale: the ground will look smooth and faceted. Compress more or use a finer file.' % round(1 / min(self.ppx, self.ppy)))
        if missing:
            warn.append('The file has no heights for %s of its points: small holes are filled from round them, and big ones become sea bed.' % format(missing, ','))
        if self.raster.plain and not getattr(self.raster, 'folab', None):
            warn.append('A plain picture doesn\'t know its size or heights: set how many metres a pixel is, and what black and white stand for.')
        est_bytes = 64000 + n * PLUGIN_BYTES_CELL
        return {'cells_w': self.W, 'cells_h': self.H, 'cells': n, 'compress': self.compress, 'exag': self.exag, 'base': self.base,
                'metres_per_cell': round(mc, 1), 'cells_per_km': round(1000 / mc, 2),
                'km_w': round(self.W * mc / 1000, 2), 'km_h': round(self.H * mc / 1000, 2),
                'game_km_w': round(self.W * CELL / UNITS_PER_M / 1000, 2), 'game_km_h': round(self.H * CELL / UNITS_PER_M / 1000, 2),
                'z_low': round(zlo), 'z_high': round(zhi), 'plugin_mb': round(est_bytes / 1e6, 1),
                'seconds': round(30 + n * SECONDS_CELL), 'rect': [self.col0, self.row0, self.col0 + self.W * self.ppx * PER_CELL, self.row0 + self.H * self.ppy * PER_CELL],
                'px_per_point': [round(self.ppx, 3), round(self.ppy, 3)], 'units_per_px': [self.upx, self.upy], 'water': zlo < 0,
                'warnings': warn, 'stop': stop}


# ---------- the whole world's land points ----------

def reduced(raster, fx, fy):
    """The file averaged down by whole blocks, ignoring holes: (values, width, height). A block's value stands at the middle of its pixels."""
    w, h, v = raster.w, raster.h, raster.v
    if fx <= 1 and fy <= 1:
        return v, w, h
    nw, nh = w // fx, h // fy
    out = array.array('f', bytes(4 * nw * nh))
    for j in range(nh):
        sums = [0.0] * nw
        bad = False
        for r in range(j * fy, (j + 1) * fy):
            row = v[r * w:r * w + nw * fx]
            for i in range(nw):
                s = sum(row[i * fx:(i + 1) * fx])
                sums[i] += s
                if s != s:
                    bad = True
        if not bad:
            n = fx * fy
            out[j * nw:(j + 1) * nw] = array.array('f', [s / n for s in sums])
            continue
        for i in range(nw):
            if sums[i] == sums[i]:
                out[j * nw + i] = sums[i] / (fx * fy)
                continue
            got = [v[r * w + c] for r in range(j * fy, (j + 1) * fy) for c in range(i * fx, (i + 1) * fx)]
            got = [g for g in got if g == g]
            out[j * nw + i] = sum(got) / len(got) if got else float('nan')
    return out, nw, nh


class Grid:
    """Every land point of a world: pts[gy * across + gx], gy from the south, each a whole step. Edges are one point, so cells cut from it meet."""

    def __init__(self, W, H, pts, x0=0, y0=0, stats=None):
        self.W, self.H, self.x0, self.y0 = W, H, x0, y0
        self.across = W * PER_CELL + 1
        self.down = H * PER_CELL + 1
        self.pts = pts
        self.stats = stats or {}

    def at(self, gx, gy):
        return self.pts[gy * self.across + gx]

    def cell(self, i, j):
        """33 x 33 heights for the cell i from the west, j from the south, as land.py has them (row by row from the south)."""
        a, p = self.across, self.pts
        out = []
        for r in range(33):
            s = (j * PER_CELL + r) * a + i * PER_CELL
            out += p[s:s + 33]
        return out

    def beyond(self, i, j):
        """For the normals: a height just past this cell's edge, from the cell next door; None at the world's edge."""
        a, d, p = self.across, self.down, self.pts

        def f(r, c):
            gx, gy = i * PER_CELL + c, j * PER_CELL + r
            return p[gy * a + gx] if 0 <= gx < a and 0 <= gy < d else None
        return f

    def slope(self, gx, gy):
        """Steepness in degrees at a land point, from the points either side of it across the whole world."""
        a, d, p = self.across, self.down, self.pts
        l, r = (gx - 1 if gx else gx), (gx + 1 if gx < a - 1 else gx)
        b, t = (gy - 1 if gy else gy), (gy + 1 if gy < d - 1 else gy)
        dx = (p[gy * a + r] - p[gy * a + l]) / (POINT * (r - l))
        dy = (p[t * a + gx] - p[b * a + gx]) / (POINT * (t - b))
        return math.degrees(math.atan(math.hypot(dx, dy)))


def heights(plan, progress=None):
    """The world's Grid: sampled, holes filled, on whole steps, no slope past what VHGT can hold."""
    fx, fy = max(1, int(plan.ppx)), max(1, int(plan.ppy))
    if progress:
        progress('Reading the heights')
    v, rw, rh = reduced(plan.raster, fx, fy)
    across, down = plan.W * PER_CELL + 1, plan.H * PER_CELL + 1
    pts = [0.0] * (across * down)
    # (where each column of land points falls in the reduced picture, worked out once)
    cols = []
    for gx in range(across):
        f = (plan.col0 + gx * plan.ppx - (fx - 1) / 2) / fx
        f = max(0.0, min(rw - 1.0, f))
        i = min(rw - 2, int(f)) if rw > 1 else 0
        cols.append((i, f - i))
    vs, vo, base, k = plan.vs, plan.vo, plan.base, plan.k
    holes = []
    for gy in range(down):
        if progress and gy % 64 == 0:
            progress('Reading the heights', gy, down)
        f = (plan.row0 + (down - 1 - gy) * plan.ppy - (fy - 1) / 2) / fy
        f = max(0.0, min(rh - 1.0, f))
        j = min(rh - 2, int(f)) if rh > 1 else 0
        t = f - j
        row_a = v[j * rw:(j + 1) * rw]
        row_b = v[(j + 1) * rw:(j + 2) * rw] if rh > 1 else row_a
        at = gy * across
        for gx, (i, s) in enumerate(cols):
            a, b = row_a[i], row_a[i + 1] if rw > 1 else row_a[i]
            c, d = row_b[i], row_b[i + 1] if rw > 1 else row_b[i]
            val = (a * (1 - s) + b * s) * (1 - t) + (c * (1 - s) + d * s) * t
            if val != val:
                # a hole beside this point: what the points round it that have heights say
                ws = [(a, (1 - s) * (1 - t)), (b, s * (1 - t)), (c, (1 - s) * t), (d, s * t)]
                ws = [(x, q) for x, q in ws if x == x and q > 0]
                tot = sum(q for _x, q in ws)
                if not tot:
                    holes.append(at + gx)
                    pts[at + gx] = 0.0
                    continue
                val = sum(x * q for x, q in ws) / tot
            pts[at + gx] = round((val * vs + vo - base) * k / STEP) * STEP
    filled, sea = fill_holes(pts, across, down, holes)
    if progress:
        progress('Keeping slopes the game can store')
    moved = limit_slopes(pts, across, down)
    return Grid(plan.W, plan.H, pts, plan.x0, plan.y0, {'holes_filled': filled, 'holes_sea': sea, 'too_steep': moved})


SEA_BED = -512.0
HOLE_REACH = 24                       # (land points: 3 km of SRTM at real size; further in, it isn't a void in the data, it's the sea)


def fill_holes(pts, across, down, holes):
    """Holes filled from the points round them, ring by ring inward; anything further in than HOLE_REACH is sea bed."""
    if not holes:
        return 0, 0
    missing = set(holes)
    total = len(missing)
    for _round in range(HOLE_REACH):
        if not missing:
            break
        got = {}
        for p in missing:
            gx, gy = p % across, p // across
            near = []
            if gx and p - 1 not in missing:
                near.append(pts[p - 1])
            if gx < across - 1 and p + 1 not in missing:
                near.append(pts[p + 1])
            if gy and p - across not in missing:
                near.append(pts[p - across])
            if gy < down - 1 and p + across not in missing:
                near.append(pts[p + across])
            if near:
                got[p] = round(sum(near) / len(near) / STEP) * STEP
        if not got:
            break
        for p, z in got.items():
            pts[p] = z
        missing -= got.keys()
    for p in missing:
        pts[p] = SEA_BED
    return total - len(missing), len(missing)


def limit_slopes(pts, across, down, rise=MAX_RISE):
    """No neighbouring points further apart than rise: anything standing too high over a neighbour comes down (the tops of cliffs and
    spikes, never the valleys). One sweep each way settles it. Returns how many points moved."""
    moved = 0
    for gy in range(down):
        at = gy * across
        for gx in range(across):
            p = at + gx
            z = pts[p]
            if gx and pts[p - 1] + rise < z:
                z = pts[p - 1] + rise
            if gy and pts[p - across] + rise < z:
                z = pts[p - across] + rise
            if z != pts[p]:
                pts[p] = z
                moved += 1
    for gy in range(down - 1, -1, -1):
        at = gy * across
        for gx in range(across - 1, -1, -1):
            p = at + gx
            z = pts[p]
            if gx < across - 1 and pts[p + 1] + rise < z:
                z = pts[p + 1] + rise
            if gy < down - 1 and pts[p + across] + rise < z:
                z = pts[p + across] + rise
            if z != pts[p]:
                pts[p] = z
                moved += 1
    return moved
