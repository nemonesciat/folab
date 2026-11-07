"""A new worldspace from a height file: the ground from mapscale.py, painted by slope with what the game shows at each steepness
(autopaint.py), water at the base level. Nothing is added to the mod here: this works out what worldgen.add_world is to write, one cell at a time, so
a world of thousands of cells never sits in memory as land forms. Also the shaded picture of a file for the flat map."""
import math
import struct
import zlib

import autopaint
import landshape
import mapscale as MS

PICTURE_SIDE = 1024
PLAIN = 'ff' * (33 * 33 * 3)
BANDS = autopaint.BANDS
BLEND = 2.5                   # degrees either side of a steepness band's edge in which it fades into the next


# ---------- what to paint with ----------

def learn_style(gd, tpl, ltex=None, tex_cache=None):
    """[{texture key: share} for each steepness band], learnt from the template world's land round its middle."""
    have = sorted(k for k in gd.grid(tpl) if gd.land_at(tpl, *k))
    if have:
        cx = sorted(k[0] for k in have)[len(have) // 2]
        cy = sorted(k[1] for k in have)[len(have) // 2]
        model, _pics = autopaint.learn(gd, tpl, cx, cy, reach=5, tex_cache=tex_cache if tex_cache is not None else {})
        if any(model):
            return model
    if ltex:
        return [{ltex: 1.0} for _ in BANDS]
    raise ValueError('The world to take after has no ground to learn its textures from: pick another.')


class Painter:
    """A cell's four quarters, from the slopes of the whole world's land (so a point on an edge gets the same mix in every quarter and cell that has it)
    and rolling noise, so the mix wanders instead of lying as even as paint. cover (landcover.py) may say what a point is instead."""

    def __init__(self, grid, model, seed=1, cover=None):
        self.grid, self.model, self.cover = grid, model, cover
        self.noise = landshape.Noise(seed)
        self.ordered = [sorted(m.items(), key=lambda kv: -kv[1]) for m in model]

    def mix_at(self, gx, gy):
        """{texture: share} at a land point."""
        if self.cover:
            m = self.cover.mix(gx, gy, self.grid.slope(gx, gy))
            if m:
                return m
        deg = self.grid.slope(gx, gy)
        b = autopaint.band(deg)
        n = self.noise.value(gx / 24.0, gy / 24.0) * 1.3
        out = {}
        far = deg - BANDS[b] + BLEND
        take = min(1.0, far / (2 * BLEND)) if far > 0 and b + 1 < len(BANDS) else 0.0
        for k, (t, v) in enumerate(self.ordered[b]):
            out[t] = v * (1 + (n if k % 2 else -n)) * (1 - take)
        if take:
            for k, (t, v) in enumerate(self.ordered[b + 1]):
                out[t] = out.get(t, 0.0) + v * (1 + (n if k % 2 else -n)) * take
        out = {t: max(0.0, v) for t, v in out.items()}
        tot = sum(out.values()) or 1.0
        return {t: v / tot for t, v in out.items() if v / tot > 0.02}

    def quarters(self, i, j):
        gx0, gy0 = i * MS.PER_CELL, j * MS.PER_CELL
        out = []
        for q in range(4):
            qx, qy = (q & 1) * 16, (q >> 1) * 16
            want = [self.mix_at(gx0 + qx + c, gy0 + qy + r) for r in range(autopaint.Q) for c in range(autopaint.Q)]
            laid = autopaint._lay(want, {}, {'bkey': None, 'base': None, 'layers': []})
            for l in laid['layers']:                      # (sixteenths: nobody sees finer, and it packs to a third of the size)
                l['a'] = [round(a * 16) / 16 for a in l['a']]
            out.append(laid)
        return out


def options(plan, grid, gd, tpl, ltex=None, seed=1, progress=None, cover=None):
    """worldgen.add_world's options for this ground."""
    model = learn_style(gd, tpl, ltex)
    paint = Painter(grid, model, seed, cover)
    x0, y0 = plan.x0, plan.y0

    def land_for(x, y):
        i, j = x - x0, y - y0
        return {'h': grid.cell(i, j), 'c': PLAIN, 'q': paint.quarters(i, j)}, grid.beyond(i, j)

    def wet(x, y):
        return min(grid.cell(x - x0, y - y0)) < 0
    return {'rect': (x0, y0, plan.W, plan.H), 'land_for': land_for, 'wet': wet, 'water': 0.0, 'progress': progress,
            'height': float(min(grid.pts))}


# ---------- a shaded picture of the file ----------

def write_rgb_png(w, h, rgb):
    raw = bytearray()
    for r in range(h):
        raw.append(0)
        raw += rgb[r * w * 3:(r + 1) * w * 3]

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


RAMP = [(0.0, (92, 110, 74)), (0.25, (150, 140, 96)), (0.55, (176, 150, 112)), (0.8, (150, 128, 110)), (1.0, (232, 230, 226))]


def _ramp(t):
    for (a, ca), (b, cb) in zip(RAMP, RAMP[1:]):
        if t <= b:
            f = (t - a) / (b - a)
            return ca[0] + (cb[0] - ca[0]) * f, ca[1] + (cb[1] - ca[1]) * f, ca[2] + (cb[2] - ca[2]) * f
    return RAMP[-1][1]


def thumbnail(raster):
    """The file averaged down to at most PICTURE_SIDE a side: (values, w, h, fx, fy)."""
    fx = max(1, math.ceil(raster.w / PICTURE_SIDE))
    fy = max(1, math.ceil(raster.h / PICTURE_SIDE))
    v, w, h = MS.reduced(raster, fx, fy)
    return v, w, h, fx, fy


def shaded(raster, thumb, opts):
    """(PNG bytes, where its edges are in the file's pixel centres: [col0, row0, col1, row1]). Lit from the north-west; under the base level is water; a hole is dark."""
    plan = MS.Plan(raster, opts)
    v, w, h, fx, fy = thumb
    vs, vo, base = plan.vs, plan.vo, plan.base
    good = [x for x in v if x == x]
    lo, hi = (min(good), max(good)) if good else (0.0, 1.0)
    span = (hi - lo) or 1.0
    # how steep it looks: as much as shows the shape of this ground, gentle or not
    sx = plan.mx * fx / (vs or 1.0)
    sy = plan.my * fy / (vs or 1.0)
    grads = []
    for r in range(1, h - 1, max(1, h // 64)):
        for c in range(1, w - 1, max(1, w // 64)):
            d = abs(v[r * w + c + 1] - v[r * w + c - 1]) / (2 * sx) + abs(v[(r + 1) * w + c] - v[(r - 1) * w + c]) / (2 * sy)
            if d == d:
                grads.append(d)
    relief = min(60.0, 0.9 / ((sum(grads) / len(grads)) or 0.015)) if grads else 1.0
    rgb = bytearray(w * h * 3)
    lx, ly, lz = -0.5, 0.5, 0.707
    for r in range(h):
        at = r * w
        up, down = (at - w if r else at), (at + w if r < h - 1 else at)
        rr = 1.0 if r in (0, h - 1) else 2.0
        for c in range(w):
            p = at + c
            z = v[p]
            q = p * 3
            if z != z:
                rgb[q], rgb[q + 1], rgb[q + 2] = 30, 28, 26
                continue
            if z * vs + vo < base:
                d = min(1.0, (base - (z * vs + vo)) / 200.0)
                rgb[q], rgb[q + 1], rgb[q + 2] = int(58 - 26 * d), int(96 - 40 * d), int(128 - 30 * d)
                continue
            a = v[p - 1] if c else z
            b = v[p + 1] if c < w - 1 else z
            n = v[up]
            s = v[down]
            a = z if a != a else a
            b = z if b != b else b
            n = z if n != n else n
            s = z if s != s else s
            dx = (b - a) / (sx * (1.0 if c in (0, w - 1) else 2.0)) * relief
            dy = (n - s) / (sy * rr) * relief
            k = (dx * dx + dy * dy + 1.0) ** 0.5
            light = (-dx * lx - dy * ly + lz) / k
            f = 0.3 + 1.0 * max(0.0, light)
            cr, cg, cb = _ramp((z - lo) / span)
            rgb[q], rgb[q + 1], rgb[q + 2] = min(255, int(cr * f)), min(255, int(cg * f)), min(255, int(cb * f))
    return write_rgb_png(w, h, rgb), picture_edges(thumb)


def picture_edges(thumb):
    """Where a picture's edges are in the file's pixel centres: [col0, row0, col1, row1]."""
    _v, w, h, fx, fy = thumb
    return [-0.5, -0.5, w * fx - 0.5, h * fy - 0.5]
