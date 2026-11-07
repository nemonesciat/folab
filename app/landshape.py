"""Land shaping: many cells' ground made at once from a plan of shapes drawn on the map.

A plan: {'shapes': [...], 'rough': 0-1, 'fade': units, 'seed': n, 'hold': bool, 'margin': units}. Each shape:
    ridge     {'pts': [[x, y], ...], 'height', 'width', 'sharp' 0-1}     a range along a line, up to its crest
    valley    {'pts': [...], 'depth', 'width', 'v' 0-1}                  a trough along a line (U to V)
    plateau   {'pts': [...] (a ring), 'height', 'cliff'}                 a level top so far above its ground, a cliff round
    flatten   {'pts': [...] (a ring), 'fade'}                            level at its ground's middle height
    hill / crater / mesa {'pts': [[x, y]], 'height', 'radius'}
    lake      {'pts': [...] (a ring), 'depth', 'bank', 'below'}        a basin; its water just under its lowest shore
    river     {'pts': [...] source to mouth, 'depth', 'width'}          a channel always running downhill, water in it
Lakes and rivers go after the rest, so they cut through what the others raised. The game keeps one water level a
cell: a lake's cells get its level, a river's cells the level of its lowest stretch in each (so it steps down from
cell to cell, as the game's own rivers do), and anything else in those cells lower than that is under water too.
Each acts on what the ones before it made. Only the marked cells change: the shapes fade out toward the marked
area's edge (over 'fade'), so an edge shared with an unmarked cell keeps its height exactly. 'rough' adds rolling
ground where the shapes reach. 'hold' keeps the ground under buildings and doors as it is, fading back to the plan
over 'margin'."""
import math
import random
import struct

SIDE = 33
CELL = 4096


# ---------- geometry ----------

def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def line_dist(p, pts, closed=False):
    if len(pts) == 1:
        return math.hypot(p[0] - pts[0][0], p[1] - pts[0][1])
    segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
    return min(_seg_dist(p[0], p[1], a[0], a[1], b[0], b[1]) for a, b in segs)


def inside(p, ring):
    x, y, n, ins = p[0], p[1], len(ring), False
    for i in range(n):
        (ax, ay), (bx, by) = ring[i], ring[(i + 1) % n]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / ((by - ay) or 1e-9) + ax:
            ins = not ins
    return ins


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def reach(shape):
    """How far past its points a shape changes the ground."""
    k = shape['kind']
    if k in ('ridge', 'valley', 'river'):
        return shape.get('width', 2000)
    if k == 'lake':
        return 256
    if k in ('hill', 'crater', 'mesa'):
        return shape.get('radius', 2000) * (1.3 if k == 'crater' else 1.0)
    return shape.get('cliff', shape.get('fade', 512)) + 64


def cells_reached(shape):
    """The grid squares a shape reaches: any of a square's corners, edge middles or middle within its reach (or, for
    a ring, inside it)."""
    pts, r = shape['pts'], reach(shape)
    ring = shape['kind'] in ('plateau', 'flatten', 'lake')
    x0, x1 = min(p[0] for p in pts) - r, max(p[0] for p in pts) + r
    y0, y1 = min(p[1] for p in pts) - r, max(p[1] for p in pts) + r
    out = set()
    for cx in range(int(x0 // CELL), int(x1 // CELL) + 1):
        for cy in range(int(y0 // CELL), int(y1 // CELL) + 1):
            samples = [(cx * CELL + i * 2048, cy * CELL + j * 2048) for i in range(3) for j in range(3)]
            if ring and any(inside(q, pts) for q in samples):
                out.add((cx, cy))
            elif min(line_dist(q, pts, ring) for q in samples) <= r + 1450:
                out.add((cx, cy))
    return out


# ---------- rolling ground ----------

class Noise:
    def __init__(self, seed):
        self.r = random.Random(seed)
        self.g = [self.r.random() * 2 - 1 for _ in range(4096)]
        self.perm = list(range(4096))
        self.r.shuffle(self.perm)

    def _v(self, ix, iy):
        return self.g[self.perm[(ix * 73856093 ^ iy * 19349663) & 4095]]

    def value(self, x, y):
        ix, iy = math.floor(x), math.floor(y)
        tx, ty = smooth(x - ix), smooth(y - iy)
        a, b = self._v(ix, iy), self._v(ix + 1, iy)
        c, d = self._v(ix, iy + 1), self._v(ix + 1, iy + 1)
        return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty

    def fbm(self, x, y, octaves=4):
        s, amp, f = 0.0, 1.0, 1.0 / 3000
        for _ in range(octaves):
            s += amp * self.value(x * f, y * f)
            amp *= 0.5
            f *= 2.1
        return s


# ---------- the plan over the cells ----------

def shape(plan, base, marked, buildings=()):
    """New heights for the marked cells: {(cx, cy): 33*33} (shape_all also gives the water)."""
    return shape_all(plan, base, marked, buildings)[0]


def shape_all(plan, base, marked, buildings=()):
    """({(cx, cy): 33*33 new heights}, {(cx, cy): water level}) for the marked cells. base(cx, cy) -> the heights
    to start from; buildings: [(x0, y0, x1, y1)] footprints whose ground is held."""
    shapes = [s for s in plan.get('shapes', []) if s.get('on', True) and s.get('pts')]
    shapes = [s for s in shapes if s['kind'] not in WATERY] + [s for s in shapes if s['kind'] in WATERY]
    fade = max(128.0, float(plan.get('fade', 1024)))
    rough = float(plan.get('rough', 0.3))
    noise = Noise(plan.get('seed', 1))
    margin = float(plan.get('margin', 512))
    hold = plan.get('hold', True)
    marked = set(map(tuple, marked))
    out = {}
    # each flat-topped shape's level: the middle of its ground (worked out once)
    levels = {}
    for i, s in enumerate(shapes):
        if s['kind'] in ('plateau', 'flatten'):
            hs = []
            for (cx, cy) in marked:
                b = base(cx, cy)
                if not b:
                    continue
                for r in range(0, SIDE, 4):
                    for c in range(0, SIDE, 4):
                        p = (cx * CELL + c * 128, cy * CELL + r * 128)
                        if inside(p, s['pts']):
                            hs.append(b[r * SIDE + c])
            hs.sort()
            levels[i] = hs[len(hs) // 2] if hs else 0.0
    ground = _sampler(base)
    for i, s in enumerate(shapes):
        if s['kind'] == 'lake':
            # its water: just under the lowest point of its shore
            ring = s['pts'] + [s['pts'][0]]
            shore = [ground(*_along(ring, t)) for t in _steps(ring, 128)]
            shore = [v for v in shore if v is not None]
            levels[i] = (min(shore) if shore else 0.0) - float(s.get('below', 32))
        elif s['kind'] == 'river' and len(s['pts']) > 1:
            # the ground along it, made to run downhill all the way (each point no higher than the one before)
            prof, lo = [], None
            for t in _steps(s['pts'], 128):
                v = ground(*_along(s['pts'], t))
                if v is None:
                    v = lo if lo is not None else 0.0
                lo = v if lo is None else min(lo, v)
                prof.append((t, lo))
            levels[i] = prof
    water = {}
    # (a long river: each cell only looks at the stretches near it)
    stretches = {}
    for i, s in enumerate(shapes):
        if s['kind'] == 'river' and isinstance(levels.get(i), list):
            run, segs = 0.0, []
            for a, b in zip(s['pts'], s['pts'][1:]):
                segs.append((a, b, run))
                run += math.hypot(b[0] - a[0], b[1] - a[1])
            stretches[i] = (segs, max(64.0, float(s.get('width', 800))) + CELL)
    for (cx, cy) in sorted(marked):
        b = base(cx, cy)
        if not b:
            continue
        mx, my = (cx + 0.5) * CELL, (cy + 0.5) * CELL
        for i, (segs, far) in stretches.items():
            levels[('near', i)] = [g for g in segs if _seg_dist(mx, my, g[0][0], g[0][1], g[1][0], g[1][1]) <= far]
        new = []
        for r in range(SIDE):
            for c in range(SIDE):
                x, y = cx * CELL + c * 128, cy * CELL + r * 128
                h0 = b[r * SIDE + c]
                h, touch = h0, 0.0
                for i, s in enumerate(shapes):
                    h, t = _one(s, i, levels, (x, y), h)
                    touch = max(touch, t)
                if rough and touch:
                    h += rough * 600 * noise.fbm(x, y) * touch
                w = _edge_weight(x, y, marked, fade)
                if hold and buildings:
                    w *= _hold_weight(x, y, buildings, margin)
                new.append(round(h0 + (h - h0) * w, 2))
        out[(cx, cy)] = new
    # the water each marked cell gets from the lakes and rivers that reach it
    for i, s in enumerate(shapes):
        if s['kind'] == 'lake':
            for k in cells_reached(s) & marked:
                water[k] = max(water.get(k, -1e9), levels[i])
        elif s['kind'] == 'river' and isinstance(levels.get(i), list):
            fill = float(s.get('depth', 300)) * 0.35
            for t, v in levels[i]:
                x, y = _along(s['pts'], t)
                k = (int(x // CELL), int(y // CELL))
                if k in marked:
                    water[k] = min(water.get(k, 1e9), v - fill)
    return out, water


WATERY = ('lake', 'river')


def _steps(pts, step):
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    n = max(1, int(total // step))
    return [total * i / n for i in range(n + 1)]


def _along(pts, t):
    """The point t along a line of points."""
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if t <= L or b is pts[-1]:
            f = min(1.0, t / L) if L else 0.0
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        t -= L
    return pts[-1][0], pts[-1][1]


def _nearest(pts, p, near=None):
    """(distance, how far along) to the nearest point of a line; near: just these of its stretches, each (a, b, how far along a is)."""
    best, along, run = 1e18, 0.0, 0.0
    if near is not None:
        for a, b, start in near:
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            f = 0.0 if not L2 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
            d = math.hypot(p[0] - a[0] - f * dx, p[1] - a[1] - f * dy)
            if d < best:
                best, along = d, start + f * math.sqrt(L2)
        return best, along
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        f = 0.0 if not L2 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        d = math.hypot(p[0] - a[0] - f * dx, p[1] - a[1] - f * dy)
        if d < best:
            best, along = d, run + f * math.sqrt(L2)
        run += math.sqrt(L2)
    return best, along


def _sampler(base):
    cache = {}

    def ground(x, y):
        k = (int(x // CELL), int(y // CELL))
        if k not in cache:
            cache[k] = base(*k)
        h = cache[k]
        if not h:
            return None
        fx, fy = (x - k[0] * CELL) / 128, (y - k[1] * CELL) / 128
        c0, r0 = min(31, int(fx)), min(31, int(fy))
        tx, ty = fx - c0, fy - r0
        p = lambda r, c: h[r * SIDE + c]
        return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty
    return ground


def _one(s, i, levels, p, h):
    """One shape at one point: (new height, how much it touches there 0-1)."""
    k = s['kind']
    if k in ('ridge', 'valley'):
        w = max(64.0, float(s.get('width', 2000)))
        t = 1 - line_dist(p, s['pts']) / w
        if t <= 0:
            return h, 0.0
        if k == 'ridge':
            sharp = float(s.get('sharp', 0.4))
            f = smooth(t) * (1 - sharp) + t * sharp      # (rounded to knife-edge)
            f = f ** (1 + sharp)
            return h + float(s.get('height', 1500)) * f, smooth(t)
        v = float(s.get('v', 0.3))
        f = smooth(t) * (1 - v) + t * v
        return h - float(s.get('depth', 600)) * f, smooth(t)
    if k in ('hill', 'crater', 'mesa'):
        R = max(64.0, float(s.get('radius', 2000)))
        d = math.hypot(p[0] - s['pts'][0][0], p[1] - s['pts'][0][1]) / R
        H = float(s.get('height', 1200))
        if k == 'hill':
            return (h + H * smooth(1 - d), smooth(1 - d)) if d < 1 else (h, 0.0)
        if k == 'mesa':
            if d >= 1:
                return h, 0.0
            return h + H * smooth((1 - d) / 0.35), 1.0   # (steep sides, a flat top over its inner two thirds)
        # crater: a rim round a bowl
        if d >= 1.3:
            return h, 0.0
        rim = math.exp(-((d - 1.0) / 0.18) ** 2)
        bowl = smooth(1 - d / 0.9) if d < 0.9 else 0.0
        return h + H * 0.5 * rim - H * bowl, max(rim, bowl)
    if k == 'lake':
        if not inside(p, s['pts']):
            return h, 0.0
        f = smooth(line_dist(p, s['pts'], closed=True) / max(32.0, float(s.get('bank', 512))))
        bed = levels[i] - float(s.get('depth', 500)) * f
        return min(h, bed), 1.0
    if k == 'river':
        prof = levels.get(i)
        if not isinstance(prof, list):
            return h, 0.0
        w = max(64.0, float(s.get('width', 800)))
        d, t = _nearest(s['pts'], p, levels.get(('near', i)))
        if d >= w:
            return h, 0.0
        j = min(len(prof) - 1, max(0, int(round(t / max(1e-6, prof[-1][0]) * (len(prof) - 1)))))
        top = prof[j][1]
        bed = top - float(s.get('depth', 300)) * (1 - smooth(d / w))
        return min(h, bed), smooth(1 - d / w)
    if k in ('plateau', 'flatten'):
        edge = float(s.get('cliff' if k == 'plateau' else 'fade', 256 if k == 'plateau' else 512))
        ins = inside(p, s['pts'])
        d = line_dist(p, s['pts'], closed=True)
        if not ins:
            return h, 0.0
        f = smooth(d / max(32.0, edge))
        top = levels.get(i, h) + (float(s.get('height', 800)) if k == 'plateau' else 0.0)
        steps = int(s.get('terraces', 0)) if k == 'plateau' else 0
        if steps > 1 and f < 1:
            f = round(f * steps) / steps
        return h + (top - h) * f, f
    return h, 0.0


def _edge_weight(x, y, marked, fade):
    """1 deep inside the marked cells, falling to 0 at the edge of an unmarked one."""
    cx, cy = int(x // CELL), int(y // CELL)
    if x % CELL == 0 and (cx - 1, cy) not in marked:
        return 0.0
    if y % CELL == 0 and (cx, cy - 1) not in marked:
        return 0.0
    n = int(math.ceil(fade / CELL)) + 1
    best = fade
    for dx in range(-n, n + 1):
        for dy in range(-n, n + 1):
            k = (cx + dx, cy + dy)
            if k in marked:
                continue
            x0, y0 = k[0] * CELL, k[1] * CELL
            d = math.hypot(max(x0 - x, 0, x - x0 - CELL), max(y0 - y, 0, y - y0 - CELL))
            best = min(best, d)
    return smooth(best / fade)


def _hold_weight(x, y, boxes, margin):
    best = margin
    for (x0, y0, x1, y1) in boxes:
        d = math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))
        if d < best:
            best = d
            if d == 0:
                return 0.0
    return smooth(best / margin)


def footprint(gd, ref):
    """A building's ground footprint (x0, y0, x1, y1) from its base's bounds (OBND), turned and sized as placed."""
    try:
        f = gd.fields(ref['base'])
    except KeyError:
        return None
    if 'OBND' not in f or len(f['OBND']) < 12:
        return None
    x1, y1, _z1, x2, y2, _z2 = struct.unpack_from('<6h', f['OBND'])
    s, a = ref['scale'], -ref['rot'][2]
    pts = [(x * s, y * s) for x in (x1, x2) for y in (y1, y2)]
    ca, sa = math.cos(a), math.sin(a)
    xs = [ref['pos'][0] + px * ca - py * sa for px, py in pts]
    ys = [ref['pos'][1] + px * sa + py * ca for px, py in pts]
    return min(xs), min(ys), max(xs), max(ys)
