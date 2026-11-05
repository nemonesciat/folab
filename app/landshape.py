"""Land shaping: many cells' ground made at once from a plan of shapes drawn on the map.

A plan: {'shapes': [...], 'rough': 0-1, 'fade': units, 'seed': n, 'hold': bool, 'margin': units}. Each shape:
    ridge     {'pts': [[x, y], ...], 'height', 'width', 'sharp' 0-1}     a range along a line, up to its crest
    valley    {'pts': [...], 'depth', 'width', 'v' 0-1}                  a trough along a line (U to V)
    plateau   {'pts': [...] (a ring), 'height', 'cliff'}                 a level top so far above its ground, a cliff round
    flatten   {'pts': [...] (a ring), 'fade'}                            level at its ground's middle height
    hill / crater / mesa {'pts': [[x, y]], 'height', 'radius'}
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
    if k in ('ridge', 'valley'):
        return shape.get('width', 2000)
    if k in ('hill', 'crater', 'mesa'):
        return shape.get('radius', 2000) * (1.3 if k == 'crater' else 1.0)
    return shape.get('cliff', shape.get('fade', 512)) + 64


def cells_reached(shape):
    """The grid squares a shape reaches: any of a square's corners, edge middles or middle within its reach (or, for
    a ring, inside it)."""
    pts, r = shape['pts'], reach(shape)
    ring = shape['kind'] in ('plateau', 'flatten')
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
    """New heights for the marked cells: {(cx, cy): 33*33}. base(cx, cy) -> the heights to start from;
    buildings: [(x0, y0, x1, y1)] footprints whose ground is held."""
    shapes = [s for s in plan.get('shapes', []) if s.get('on', True) and s.get('pts')]
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
    for (cx, cy) in sorted(marked):
        b = base(cx, cy)
        if not b:
            continue
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
    return out


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
