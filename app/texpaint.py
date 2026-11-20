"""Textures drawn in code: painted planks, striped cloth, a parasol seen from above, painted metal, concrete, signs.

A `Canvas` holds a colour and a height for every pixel; `files` gives the two pictures the game wants of it: the colour
texture, and a normal map worked out from the heights (which way each pixel leans, so plank gaps and raised paint catch
the light). Both as plain 32-bit DDS with their smaller copies (`dds.encode`). The repeating ones repeat without a
seam: everything in them is measured round the picture's own size. Nothing here is random from run to run: a seed
gives the same picture every time."""
import math
import random

import dds

# late-fifties seaside paint
TURQUOISE = (72, 186, 178)
CORAL = (238, 128, 108)
CREAM = (244, 232, 202)
YELLOW = (248, 204, 96)
SEAFOAM = (164, 214, 190)
WHITE = (238, 238, 230)
TEAL_INK = (24, 88, 96)
RED = (198, 62, 52)
BARE_WOOD = (150, 132, 108)


class Noise:
    """Smooth noise that repeats every `period` steps each way."""

    def __init__(self, seed, period):
        rnd = random.Random(seed)
        self.n = period
        self.v = [rnd.random() for _ in range(period * period)]

    def at(self, x, y):
        n = self.n
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = x - ix, y - iy
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = self.v[iy % n * n + ix % n], self.v[iy % n * n + (ix + 1) % n]
        c, d = self.v[(iy + 1) % n * n + ix % n], self.v[(iy + 1) % n * n + (ix + 1) % n]
        return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _faded(c, by=0.18):
    """A colour the sun has had: paler and greyer."""
    grey = sum(c) / 3
    return tuple(v + (grey - v) * by + (255 - v) * by * 0.5 for v in c)


class Canvas:
    def __init__(self, w, h, clear=None):
        """clear: a colour makes the picture see-through to start with (leaves: only what is drawn shows), filled with
        that colour so that no dark rim shows where the smaller copies blur the edge."""
        self.w, self.h = w, h
        self.rgb = [tuple(float(v) for v in clear or (0, 0, 0))] * (w * h)
        self.ht = [0.5] * (w * h)
        self.a = [0.0] * (w * h) if clear else None

    def paint(self, fn):
        """fn(x, y) -> (colour, height 0-1) for every pixel."""
        w = self.w
        for y in range(self.h):
            for x in range(w):
                self.rgb[y * w + x], self.ht[y * w + x] = fn(x, y)

    def rect(self, x0, y0, x1, y1, fn):
        """fn(x, y, colour, height) -> (colour, height) over part of it."""
        w = self.w
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(w, x1)):
                i = y * w + x
                self.rgb[i], self.ht[i] = fn(x, y, self.rgb[i], self.ht[i])

    def line(self, a, b, thick, colour, raise_=0.12, worn=None):
        """A stroke with round ends from a to b. worn(x, y) -> 0-1: how much of the paint is left there."""
        w = self.w
        r = thick / 2
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = dx * dx + dy * dy
        for y in range(max(0, int(min(a[1], b[1]) - r - 1)), min(self.h, int(max(a[1], b[1]) + r + 2))):
            for x in range(max(0, int(min(a[0], b[0]) - r - 1)), min(w, int(max(a[0], b[0]) + r + 2))):
                t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / ln)) if ln else 0.0
                d = math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)
                cover = max(0.0, min(1.0, r - d + 0.5))          # (a soft edge, a pixel wide)
                if cover <= 0:
                    continue
                if worn:
                    cover *= worn(x, y)
                i = y * w + x
                if self.a:
                    # (on a see-through picture the colour goes on whole and the edge is in how much shows)
                    self.rgb[i] = tuple(colour) if cover > 0.3 or self.a[i] < 0.3 else self.rgb[i]
                    self.a[i] = max(self.a[i], cover)
                else:
                    self.rgb[i] = _mix(self.rgb[i], colour, cover)
                self.ht[i] = max(self.ht[i], self.ht[i] * (1 - cover) + (0.5 + raise_) * cover)

    def blade(self, a, b, thick, colour, tip=0.15, bend=0.0, steps=8, raise_=0.1):
        """A leaf or a blade of grass from a to b: `thick` at a, narrowing to `tip` of that at b, bowed sideways by
        `bend` (a part of its length)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        at = lambda t: (a[0] + dx * t - dy * bend * math.sin(math.pi * t), a[1] + dy * t + dx * bend * math.sin(math.pi * t))
        for k in range(steps):
            t0, t1 = k / steps, (k + 1) / steps
            self.line(at(t0), at(t1), thick * (1 - (1 - tip) * (t0 + t1) / 2), colour, raise_)

    def text(self, words, x, y, high, colour, thick=None, worn=None):
        """Words in block capitals, their top left at (x, y), `high` pixels tall. Returns where they end."""
        unit = high / 6.0
        thick = thick or max(2.0, high / 6.5)
        for ch in words.upper():
            strokes = LETTERS.get(ch)
            if strokes:
                for s in strokes:
                    for p, q in zip(s, s[1:]):
                        self.line((x + p[0] * unit, y + p[1] * unit), (x + q[0] * unit, y + q[1] * unit), thick, colour, worn=worn)
            x += (5.6 if ch != ' ' else 3.5) * unit
        return x

    def text_wide(self, words, high):
        return sum(5.6 if ch != ' ' else 3.5 for ch in words) * high / 6.0 - 1.6 * high / 6.0

    def files(self, bump=3.0, shine=40, game=False, rim=False):
        """(colour DDS, normal map DDS). bump: how strongly heights lean the light; shine: the normal map's fourth
        number, which the game reads as how much the surface gleams. game: as the game's own models' are (`normal_map`):
        relief from the painting too, as strong as the game's, the normal map half the size."""
        if game:
            gl = self.gloss if hasattr(self, 'gloss') and shine is None else [shine if shine is not None else 40] * (self.w * self.h)
            return colour_map(self, rim), normal_map(self, gl, bump)
        w, h = self.w, self.h
        col = bytearray(w * h * 4)
        nor = bytearray(w * h * 4)
        ht = self.ht
        clamp = lambda v: 0 if v < 0 else 255 if v > 255 else int(v + 0.5)
        rgb = bled(self) if self.a else self.rgb
        for y in range(h):
            up, dn = (y - 1) % h * w, (y + 1) % h * w
            for x in range(w):
                i = y * w + x
                r, g, b = rgb[i]
                col[4 * i:4 * i + 4] = bytes((clamp(r), clamp(g), clamp(b), clamp(255 * self.a[i]) if self.a else 255))
                sx = (ht[y * w + (x + 1) % w] - ht[y * w + (x - 1) % w]) * bump
                sy = (ht[dn + x] - ht[up + x]) * bump
                ln = math.sqrt(sx * sx + sy * sy + 1)
                nor[4 * i:4 * i + 4] = bytes((clamp(127.5 - 127.5 * sx / ln), clamp(127.5 - 127.5 * sy / ln), clamp(127.5 + 127.5 / ln), shine))
        return dds.compress(dds.encode(w, h, bytes(col), cut=CUT if self.a else None)), dds.compress(dds.encode(w, h, bytes(nor)))   # (compressed as the game keeps its own: dds.compress)


# ---------- the files, as the game's own models have them ----------
# Measured over the normal maps of the game's buildings, plants and clutter (45 of the most used): the light leans by 5 to
# 12 degrees on average over a picture, a tenth of it by 15 to 30; and the normal map is half the colour picture's size
# (1024 colour, 512 normal), which halves what a texture costs the game's memory. FOLab's pictures leaned by 2 to 4 (the
# ship's hull 2.6): heights only where something was drawn standing proud, flat between, so they read as painted on.

TILT_WANT = 7.0             # (degrees) the mean lean a picture's normal map is brought up to, if under it
TILT_MOST_GAIN = 5.0        # (never more than this many times the painter's own)
RELIEF = 0.35               # how much the painting's own light and dark stand in for height (rust, chips and grime have depth)
RELIEF_REACH = 3            # (pixels: what is lighter or darker than round it, within this, is raised or sunk)
HALF_FROM = 512             # a picture this wide or more has its normal map at half its size


CUT = 64                    # (where the game cuts a see-through picture: nifmake.ALPHA_CUT)


def colour_map(c, rim=False):
    """rim: a cut-out drawn once across its card (a plant's leaf or tuft), its border made clear (dds._clear_rim)."""
    w, h = c.w, c.h
    col = bytearray(w * h * 4)
    cl = lambda v: 0 if v < 0 else 255 if v > 255 else int(v + 0.5)
    rgb = bled(c) if c.a else c.rgb
    for i, (r, g, b) in enumerate(rgb):
        col[4 * i:4 * i + 4] = bytes((cl(r), cl(g), cl(b), cl(255 * c.a[i]) if c.a else 255))
    # (a stem down a see-through strip, stick(): halved plainly, so the stem stays solid in every smaller copy instead of
    # being scaled down to the cut with the rest of the picture's coverage)
    cut = CUT if c.a and not getattr(c, 'plain_halving', False) else None
    strips = getattr(c, 'strips', None)             # (a sheet of several pictures: plantsheet.py)
    if strips:
        return dds.compress(dds.encode(w, h, bytes(col), cut=CUT, strips=strips))
    return dds.compress(dds.encode(w, h, bytes(col), cut=cut, rim=rim and cut is not None))


def bled(c):
    """A see-through picture's colours with what is drawn spread into the clear parts round it (each clear pixel takes
    the colour of what shows nearest, through ever smaller copies weighted by alpha), so the game's filtering never mixes
    the clear parts' own colour into a leaf's edge. A part-clear pixel keeps its share of its own colour."""
    w, h = c.w, c.h
    levels = [(w, h, list(c.rgb), list(c.a))]
    while levels[-1][0] > 1 or levels[-1][1] > 1:
        lw, lh, rgb, al = levels[-1]
        nw, nh = max(1, lw // 2), max(1, lh // 2)
        fx, fy = lw // nw, lh // nh
        nrgb, nal = [], []
        for y in range(nh):
            for x in range(nw):
                t = [0.0, 0.0, 0.0]
                a = 0.0
                for dy in range(fy):
                    for dx in range(fx):
                        i = (y * fy + dy) * lw + x * fx + dx
                        q = al[i]
                        r = rgb[i]
                        t[0] += r[0] * q
                        t[1] += r[1] * q
                        t[2] += r[2] * q
                        a += q
                nrgb.append(tuple(v / a for v in t) if a > 0 else (0.0, 0.0, 0.0))
                nal.append(min(1.0, a))                 # (some of it shows: its colour is real)
        levels.append((nw, nh, nrgb, nal))
    for k in range(len(levels) - 2, -1, -1):            # (from the smallest up: what is clear takes the copy above's colour)
        lw, lh, rgb, al = levels[k]
        pw, ph, prgb, _pal = levels[k + 1]
        fx, fy = max(1, lw // pw), max(1, lh // ph)
        out = []
        for y in range(lh):
            for x in range(lw):
                i = y * lw + x
                q = min(1.0, al[i])
                if q >= 1.0:
                    out.append(rgb[i])
                    continue
                p = prgb[min(ph - 1, y // fy) * pw + min(pw - 1, x // fx)]
                r = rgb[i]
                out.append((r[0] * q + p[0] * (1 - q), r[1] * q + p[1] * (1 - q), r[2] * q + p[2] * (1 - q)))
        levels[k] = (lw, lh, out, [1.0] * (lw * lh))
    return levels[0][2]


def _blur(v, w, h, r):
    """A box blur, wrapping round (the pictures repeat)."""
    out = [0.0] * (w * h)
    n = 2 * r + 1
    for y in range(h):
        row = v[y * w:(y + 1) * w]
        s = sum(row[k % w] for k in range(-r, r + 1))
        for x in range(w):
            out[y * w + x] = s / n
            s += row[(x + r + 1) % w] - row[(x - r) % w]
    res = [0.0] * (w * h)
    for x in range(w):
        col = out[x::w]
        s = sum(col[k % h] for k in range(-r, r + 1))
        for y in range(h):
            res[y * w + x] = s / n
            s += col[(y + r + 1) % h] - col[(y - r) % h]
    return res


def heights(c):
    """The picture's heights with relief from its painting: what is darker than round it a little sunk (seams, pits, rust
    runs, grime in the grain), what is lighter a little raised. Not where it is see-through."""
    w, h = c.w, c.h
    lum = [(0.3 * r + 0.59 * g + 0.11 * b) / 255.0 for r, g, b in c.rgb]
    near = _blur(lum, w, h, RELIEF_REACH)
    return [c.ht[i] + RELIEF * (lum[i] - near[i]) * (0 if c.a and c.a[i] < 0.5 else 1) for i in range(w * h)]


def _half(v, w, h):
    return [(v[(2 * y) * w + 2 * x] + v[(2 * y) * w + 2 * x + 1] + v[(2 * y + 1) * w + 2 * x] + v[(2 * y + 1) * w + 2 * x + 1]) / 4
            for y in range(h // 2) for x in range(w // 2)]


def normal_map(c, gloss, bump):
    """The normal map of a Canvas as the game's own models have theirs (see above): heights with the painting's relief,
    leaning on average by TILT_WANT degrees at least, half the size from HALF_FROM. gloss: a number 0-255 a pixel."""
    w, h = c.w, c.h
    ht = heights(c)
    if w >= HALF_FROM and h >= 8:
        ht, gloss, w, h = _half(ht, w, h), _half(gloss, w, h), w // 2, h // 2
        bump *= 0.5                     # (a pixel twice as far across: the same slope is half the step)

    def slopes(i):
        y, x = divmod(i, w)
        return ((ht[y * w + (x + 1) % w] - ht[y * w + (x - 1) % w]), (ht[(y + 1) % h * w + x] - ht[(y - 1) % h * w + x]))
    sample = [slopes(i) for i in range(0, w * h, 13)]

    def mean_tilt(b):
        return sum(math.degrees(math.atan(b * math.hypot(sx, sy))) for sx, sy in sample) / len(sample)
    have = mean_tilt(bump)
    if have < TILT_WANT:
        lo, hi = bump, bump * TILT_MOST_GAIN
        if mean_tilt(hi) <= TILT_WANT:
            bump = hi
        else:
            for _ in range(14):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if mean_tilt(mid) < TILT_WANT else (lo, mid)
            bump = hi
    nor = bytearray(w * h * 4)
    cl = lambda v: 0 if v < 0 else 255 if v > 255 else int(v + 0.5)
    for i in range(w * h):
        sx, sy = slopes(i)
        sx, sy = sx * bump, sy * bump
        ln = math.sqrt(sx * sx + sy * sy + 1)
        nor[4 * i:4 * i + 4] = bytes((cl(127.5 - 127.5 * sx / ln), cl(127.5 - 127.5 * sy / ln), cl(127.5 + 127.5 / ln), cl(gloss[i])))
    return dds.compress(dds.encode(w, h, bytes(nor)))


# block capitals as strokes on a grid 4 wide and 6 tall (y down)
_O = [(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]
_P = [(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]
LETTERS = {
    'A': [[(0, 6), (0, 2), (2, 0), (4, 2), (4, 6)], [(0, 4), (4, 4)]],
    'B': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)], [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    'C': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    'D': [[(0, 0), (0, 6), (2, 6), (4, 4), (4, 2), (2, 0), (0, 0)]],
    'E': [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    'F': [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    'G': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3), (2, 3)]],
    'H': [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    'I': [[(2, 0), (2, 6)], [(1, 0), (3, 0)], [(1, 6), (3, 6)]],
    'J': [[(4, 0), (4, 5), (3, 6), (1, 6), (0, 5)]],
    'K': [[(0, 0), (0, 6)], [(4, 0), (0, 3), (4, 6)]],
    'L': [[(0, 0), (0, 6), (4, 6)]],
    'M': [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    'N': [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    'O': [_O],
    'P': [_P],
    'Q': [_O, [(2, 4), (4, 6)]],
    'R': [_P, [(2, 3), (4, 6)]],
    'S': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    'T': [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    'U': [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    'V': [[(0, 0), (2, 6), (4, 0)]],
    'W': [[(0, 0), (1, 6), (2, 3), (3, 6), (4, 0)]],
    'X': [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    'Y': [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    'Z': [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    '&': [[(4, 6), (1, 2), (1, 1), (2, 0), (3, 1), (3, 2), (0, 4), (0, 5), (1, 6), (2, 6), (4, 4)]],
    '0': [_O],
    '1': [[(1, 1), (2, 0), (2, 6)]],
    '2': [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (0, 6), (4, 6)]],
    '3': [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1.5, 3)], [(3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    '4': [[(3, 6), (3, 0), (0, 4), (4, 4)]],
    '5': [[(4, 0), (0, 0), (0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]],
    '6': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1, 3), (0, 4)]],
    '7': [[(0, 0), (4, 0), (1.5, 6)]],
    '8': [[(1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3)]],
    '9': [[(4, 2), (3, 3), (1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5)]],
    '-': [[(1, 3), (3, 3)]],
    '.': [[(2, 5.6), (2, 6)]],
}


# ---------- the pictures ----------

def planks(colour, size=256, count=8, seed=1, wear=0.22):
    """Painted boards standing side by side: gaps between, grain down them, paint gone to bare wood in patches."""
    c = Canvas(size, size)
    rnd = random.Random(seed)
    tint = [rnd.uniform(-0.07, 0.07) for _ in range(count)]
    shift = [rnd.uniform(0, size) for _ in range(count)]
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    wide = size / count
    base = _faded(colour)

    def fn(x, y):
        k = int(x / wide) % count
        edge = min(x - k * wide, (k + 1) * wide - x)             # how far from the board's side
        grain = fine.at(x * 64.0 / size * 2, (y + shift[k]) * 64.0 / size / 6)      # (stretched down the board)
        patch = big.at(x * 8.0 / size + k * 3.1, y * 8.0 / size) + (grain - 0.5) * 0.5
        col = tuple(v * (1 + tint[k]) * (0.93 + 0.14 * grain) for v in base)
        h = 0.55 + 0.05 * grain
        bare = patch > 1 - wear - (0.12 if edge < 3 else 0)      # (paint goes first at the edges)
        if bare:
            col = tuple(v * (0.8 + 0.4 * grain) for v in BARE_WOOD)
            h -= 0.06
        if edge < 1.5:
            col, h = tuple(v * 0.35 for v in col), 0.2           # the gap
        elif edge < 3:
            col = tuple(v * 0.82 for v in col)
        return col, h
    c.paint(fn)
    return c


def cloth_stripes(a, b, size=256, stripes=4, seed=2):
    """Awning cloth: broad stripes of two colours, a weave, sun and salt."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    a, b = _faded(a, 0.12), _faded(b, 0.12)
    wide = size / (2 * stripes)

    def fn(x, y):
        col = a if int(x / wide) % 2 == 0 else b
        weave = 0.5 + 0.5 * math.sin(x * math.pi) * math.sin(y * math.pi)       # (every other pixel: threads)
        dirt = big.at(x * 8.0 / size, y * 8.0 / size)
        f = 0.9 + 0.06 * weave + 0.1 * dirt + 0.05 * (fine.at(x * 64.0 / size, y * 64.0 / size) - 0.5)
        return tuple(v * f for v in col), 0.5 + 0.04 * weave
    c.paint(fn)
    return c


def parasol(a, b, size=256, panels=8, seed=3):
    """A parasol's canopy seen from straight above: panels of two colours from the middle out, a rib between each
    pair, a cap on top. Laid on a cone from over it (`modelmake`'s paint 'above')."""
    c = Canvas(size, size)
    big = Noise(seed, 8)
    a, b = _faded(a, 0.1), _faded(b, 0.1)
    mid = (size - 1) / 2.0

    def fn(x, y):
        dx, dy = x - mid, mid - y
        r = math.hypot(dx, dy) / mid
        turn = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0 * panels
        k = int(turn)
        col = a if k % 2 == 0 else b
        to_rib = min(turn - k, k + 1 - turn) * r * mid * 2 * math.pi / panels        # pixels to the nearest rib
        sag = 0.5 + 0.12 * math.sin((turn - k) * math.pi)                           # cloth swells between ribs
        f = 0.92 + 0.12 * big.at(x * 8.0 / size, y * 8.0 / size) - 0.1 * r * r        # (weather gathers at the rim)
        if to_rib < 1.2:
            return tuple(v * 0.55 for v in col), 0.62
        if r < 0.07:
            return _faded(WHITE, 0.05), 0.8
        return tuple(v * f for v in col), sag
    c.paint(fn)
    return c


def painted_metal(colour, size=128, seed=4, rust=0.12):
    """A painted pipe or frame: smooth, chipped to rust here and there."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 32)
    base = _faded(colour, 0.08)

    def fn(x, y):
        p = big.at(x * 8.0 / size, y * 8.0 / size) * 0.7 + fine.at(x * 32.0 / size, y * 32.0 / size) * 0.3
        if p > 1 - rust:
            return _mix((120, 70, 44), (160, 96, 60), fine.at(y * 32.0 / size, x * 32.0 / size)), 0.42
        return tuple(v * (0.94 + 0.08 * p) for v in base), 0.5
    c.paint(fn)
    return c


def concrete(colour=(196, 186, 166), size=256, seed=5):
    """A poured slab with sand trodden into it."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 128)

    def fn(x, y):
        g = fine.at(x * 128.0 / size, y * 128.0 / size)
        f = 0.82 + 0.2 * big.at(x * 8.0 / size, y * 8.0 / size) + 0.16 * (g - 0.5)
        return tuple(v * f for v in colour), 0.45 + 0.12 * g
    c.paint(fn)
    return c


def sign(panels, w=512, h=256, seed=6):
    """Several painted signs on one picture. panels: [{'box': (x0, y0, x1, y1) as parts of the picture, 'lines':
    [words], 'ground': colour, 'ink': colour, 'edge': colour}]. Each sign's words are sized to fill it. A part of
    a model shows one of them through its look's 'region' (the same four numbers)."""
    c = Canvas(w, h)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    left = lambda x, y: 0.25 + 0.75 * min(1.0, max(0.0, (big.at(x * 8.0 / w * 2, y * 8.0 / h) * 0.6 + fine.at(x * 64.0 / w, y * 64.0 / h) * 0.4 - 0.22) * 4))
    c.paint(lambda x, y: ((60, 50, 40), 0.3))
    for n, p in enumerate(panels):
        x0, y0, x1, y1 = int(p['box'][0] * w), int(p['box'][1] * h), int(p['box'][2] * w), int(p['box'][3] * h)
        ground, edge = _faded(p.get('ground', CREAM), 0.1), p.get('edge', CORAL)
        band = max(3, (y1 - y0) // 14)

        def fn(x, y, _c, _h, ground=ground, edge=edge, band=band, box=(x0, y0, x1, y1)):
            rim = min(x - box[0], box[2] - 1 - x, y - box[1], box[3] - 1 - y)
            grain = fine.at(x * 64.0 / w / 5, y * 64.0 / h * 2)                     # (boards running along the sign)
            f = 0.9 + 0.1 * grain + 0.08 * (big.at(x * 8.0 / w, y * 8.0 / h) - 0.5)
            if band <= rim < 2 * band:
                return _mix(ground, edge, left(x, y)), 0.56
            return tuple(v * f for v in ground), 0.5 + 0.03 * grain
        c.rect(x0, y0, x1, y1, fn)
        lines = p['lines']
        room_w, room_h = (x1 - x0) - 7 * band, (y1 - y0) - 6 * band
        high = room_h / (len(lines) * 1.35 - 0.35)
        high = min([high] + [high * room_w / c.text_wide(t, high) for t in lines if t.strip()])
        y = y0 + ((y1 - y0) - high * (len(lines) * 1.35 - 0.35)) / 2
        for k, t in enumerate(lines):
            ink = p.get('inks', [p.get('ink', TEAL_INK)] * len(lines))[k]
            c.text(t, x0 + ((x1 - x0) - c.text_wide(t, high)) / 2, y, high, ink, worn=left)
            y += high * 1.35
    return c


def surfboard(colour, stripe, w=64, h=256, seed=7):
    """A board seen flat on: its colour, a stripe down the middle, a band across near the nose. Fitted to the board."""
    c = Canvas(w, h)
    big = Noise(seed, 8)
    colour, stripe = _faded(colour, 0.06), _faded(stripe, 0.06)

    def fn(x, y):
        f = 0.94 + 0.1 * big.at(x * 8.0 / w, y * 8.0 / h)
        col = stripe if abs(x - (w - 1) / 2.0) < w * 0.07 or h * 0.16 < y < h * 0.22 else colour
        return tuple(v * f for v in col), 0.5
    c.paint(fn)
    return c


# ---------- growing things (see-through: only the leaf shows) ----------

PALM_GREEN = (86, 128, 58)
PALM_DARK = (52, 92, 44)
PALM_DRY = (156, 138, 78)
LEAF_GREEN = (70, 132, 62)
LEAF_LIGHT = (128, 170, 84)
SEA_GRASS = (150, 158, 96)
HIBISCUS = (214, 52, 66)


def _shade(c, f):
    return tuple(v * f for v in c)


def palm_frond(w=128, h=256, seed=30, dry=0.0):
    """A coconut palm's leaf laid flat, its stalk at the bottom middle: leaflets off a midrib, long in the middle of the
    leaf and short at both ends, each drooping a little. dry: how many leaflets have gone brown."""
    c = Canvas(w, h, clear=PALM_DARK)
    rnd = random.Random(seed)
    mid = (w - 1) / 2.0
    pairs = 30
    for k in range(pairs):
        t = (k + 0.5) / pairs                                   # 0 at the tip, 1 at the stalk
        y = h * (0.03 + 0.85 * t)
        reach = mid * 0.98 * math.sin(math.pi * (0.12 + 0.8 * t)) ** 0.7
        for side in (-1, 1):
            if rnd.random() < 0.05:
                continue                                        # (a leaflet lost)
            col = PALM_DRY if rnd.random() < dry else _mix(PALM_DARK, PALM_GREEN, rnd.random())
            lift = h * (0.035 + 0.06 * (1 - t)) * rnd.uniform(0.7, 1.3)             # towards the tip they point forward
            c.blade((mid, y), (mid + side * reach * rnd.uniform(0.85, 1.0), y - lift), h / pairs * 0.95, _shade(col, rnd.uniform(0.85, 1.1)),
                    tip=0.2, bend=-0.08 * side, steps=6)
    c.line((mid, h * 0.02), (mid, h - 1), max(2.5, w / 36.0), _shade(PALM_DRY, 0.9), 0.25)      # the midrib, over them
    return c


def broad_leaf(w=128, h=256, seed=31):
    """A banana plant's leaf: one long blade with a pale midrib, ribbed across, torn by the wind into strips at its
    edges. Stalk at the bottom middle."""
    c = Canvas(w, h, clear=LEAF_GREEN)
    rnd = random.Random(seed)
    mid = (w - 1) / 2.0
    big = Noise(seed, 8)
    tears = sorted(rnd.uniform(0.1, 0.9) for _ in range(9))
    for y in range(h):
        t = y / (h - 1.0)                                       # 0 at the tip
        half = mid * 0.97 * math.sin(math.pi * min(1.0, 0.06 + t * 0.97)) ** 0.55 * (1 if t < 0.93 else max(0.0, (1 - t) / 0.07))
        for x in range(w):
            off = abs(x - mid)
            rib = 0.5 + 0.5 * math.sin((y + off * 0.45) * 0.9)  # ribs running out and forward from the midrib
            f = 0.82 + 0.14 * rib + 0.14 * big.at(x * 8.0 / w, y * 8.0 / h)
            col = _mix(LEAF_GREEN, LEAF_LIGHT, 0.25 + 0.3 * big.at(y * 8.0 / h, x * 8.0 / w))
            show = 1.0 if off <= half else 0.0
            for tt in tears:                                    # a tear: a thin wedge in from the edge along a rib
                if off > half * 0.35 and abs(y - (tt * h - off * 0.45)) < 1.2 + (off - half * 0.35) * 0.06:
                    show = 0.0
            i = y * w + x
            if off < max(1.6, w / 50.0):
                c.rgb[i], c.ht[i], c.a[i] = _shade(LEAF_LIGHT, 1.1), 0.7, 1.0 if t > 0.02 else 0.0
            else:
                c.rgb[i], c.ht[i], c.a[i] = _shade(col, f), 0.45 + 0.1 * rib, show
    return c


def bush(size=256, seed=32, flowers=14, leaf=LEAF_GREEN, bloom=HIBISCUS):
    """A shrub seen from the side: a dome of small leaves thick enough to hide what's behind, open at its edge, with
    flowers among them. Its foot at the bottom middle."""
    c = Canvas(size, size, clear=_shade(leaf, 0.7))
    rnd = random.Random(seed)
    mid = (size - 1) / 2.0
    for layer in range(3):                                      # dark leaves behind, light ones in front
        for _ in range(260):
            ang, r = rnd.uniform(0, math.pi), math.sqrt(rnd.random())
            x, y = mid + math.cos(ang) * r * mid * 0.94, size - 4 - math.sin(ang) * r * (size - 12) * 0.96
            turn, ln = rnd.uniform(0, 2 * math.pi), size * rnd.uniform(0.045, 0.075)
            col = _shade(_mix(leaf, LEAF_LIGHT, rnd.random() * 0.5), 0.6 + 0.2 * layer + rnd.uniform(-0.05, 0.05))
            c.blade((x, y), (x + math.cos(turn) * ln, y + math.sin(turn) * ln), ln * 0.55, col, tip=0.25, steps=4)
    for _ in range(flowers):
        ang, r = rnd.uniform(0.2, math.pi - 0.2), 0.35 + 0.6 * math.sqrt(rnd.random())
        x, y = mid + math.cos(ang) * r * mid * 0.85, size - 4 - math.sin(ang) * r * (size - 12) * 0.88
        rad = size * rnd.uniform(0.022, 0.032)
        for k in range(5):
            a = 2 * math.pi * k / 5 + rnd.random()
            c.line((x, y), (x + math.cos(a) * rad, y + math.sin(a) * rad), rad * 1.1, _shade(bloom, rnd.uniform(0.9, 1.1)), 0.2)
        c.line((x, y), (x, y), rad * 0.6, YELLOW, 0.3)
    for k in range(5):                                          # stems showing at the foot
        c.blade((mid + (k - 2) * size * 0.02, size - 1), (mid + (k - 2) * size * 0.09, size * 0.72), size * 0.02, (96, 78, 56), tip=0.5, steps=4)
    return c


def grass(w=256, h=128, seed=33, colour=SEA_GRASS):
    """A tuft of dune grass from the side: long blades from the foot, fanning out and bowing over."""
    c = Canvas(w, h, clear=_shade(colour, 0.8))
    rnd = random.Random(seed)
    for k in range(70):
        x0 = w * (0.5 + rnd.uniform(-0.2, 0.2))
        lean = rnd.uniform(-1, 1)
        top = h * rnd.uniform(0.04, 0.5)
        col = _shade(_mix(colour, PALM_GREEN, rnd.random() * 0.6), rnd.uniform(0.7, 1.1))
        c.blade((x0, h - 1), (x0 + lean * w * 0.42, top + abs(lean) * h * 0.25), w / 42.0, col, tip=0.1, bend=0.22 * lean, steps=10)
    return c


def bark_rings(colour=(132, 118, 98), size=128, rings=7, seed=34):
    """A palm's trunk: a ring round it for every leaf it has dropped, weathered grey. Repeats."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    tall = size / float(rings)

    def fn(x, y):
        wob = (big.at(x * 8.0 / size, 0.5) - 0.5) * tall * 0.4
        t = ((y + wob) % tall) / tall
        g = fine.at(x * 64.0 / size / 1.5, y * 64.0 / size * 3)
        f = 0.8 + 0.25 * t + 0.14 * (g - 0.5) + 0.1 * big.at(x * 8.0 / size, y * 8.0 / size)
        if t < 0.12:
            return _shade(colour, 0.55), 0.25
        return _shade(colour, f), 0.4 + 0.25 * t
    c.paint(fn)
    return c


def stalk(colour=(120, 150, 84), size=128, seed=35):
    """A soft green stem, streaked down its length, browning in places. Repeats."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)

    def fn(x, y):
        g = fine.at(x * 64.0 / size * 2, y * 64.0 / size / 5)
        brown = big.at(x * 8.0 / size, y * 8.0 / size)
        col = _mix(colour, (140, 112, 72), max(0.0, brown - 0.6) * 2)
        return _shade(col, 0.85 + 0.25 * g), 0.45 + 0.1 * g
    c.paint(fn)
    return c


# Where a stick's stem lies across its picture (u from the left): a quarter of the width, on whole halvings of 64 so the
# smaller copies keep it sharp down to 4 across. modelmake's 'stick' lays a strip at least STICK_LEAST wide over it and
# shows only the band, so a stem a few units thick is drawn on a strip nv-rs doesn't take for a cable (`shadowcast`).
STICK_BAND = (0.5, 0.75)


def stick(colour=(96, 84, 58), w=64, h=256, rings=0, ring=(70, 62, 44), brown=(120, 96, 64), seed=60):
    """A stem seen from the side, down the picture (repeats down it), see-through either side of it: lit on its round
    middle and dark at its edges, streaked along its length; rings: nodes across it (bamboo's, a ti cane's scars),
    that many down the picture."""
    c = Canvas(w, h, clear=_shade(colour, 0.8))
    lo, hi = int(w * STICK_BAND[0]), int(w * STICK_BAND[1])
    half = (hi - lo) / 2.0
    streak, big = Noise(seed, 32), Noise(seed + 1, 4)
    for y in range(h):
        node = 0.0
        if rings:
            d = abs(((y + 0.5) * rings / h) % 1.0 - 0.5) * 2         # 1 at a node, 0 between
            node = max(0.0, (d - 0.9) / 0.1)
        for x in range(lo, hi):
            s = (x + 0.5 - lo - half) / half                         # -1 at one edge, 1 at the other
            z = math.sqrt(max(0.0, 1 - s * s))
            g = streak.at(x * 32.0 / w * 4, y * 32.0 / h)
            col = _mix(colour, brown, max(0.0, big.at(x * 4.0 / w, y * 4.0 / h) - 0.55) * 1.6)
            col = _mix(col, ring, node * 0.8)
            i = y * w + x
            c.rgb[i] = _shade(col, (0.55 + 0.5 * z) * (0.9 + 0.2 * g))
            c.ht[i] = 0.25 + 0.5 * z + 0.15 * node + 0.04 * g
            c.a[i] = 1.0
    c.plain_halving = True          # (colour_map: its smaller copies keep the stem solid)
    return c


# ---------- a jungle ----------

JUNGLE_DARK = (34, 74, 38)
JUNGLE_GREEN = (58, 112, 50)
JUNGLE_LIGHT = (112, 158, 70)
FERN_GREEN = (84, 142, 58)
TI_RED = (150, 36, 64)
MOSS = (88, 118, 48)


def foliage(size=512, seed=40, dark=JUNGLE_DARK, light=JUNGLE_LIGHT, shape='ball', leaves=1500, leaf=0.035, slim=0.5, flowers=0, bloom=HIBISCUS, stems=0):
    """A mass of leaves seen from the side, thick in the middle and ragged at its edge: 'ball' for a bough of a tree's
    crown (seen from any side, and from under), 'dome' for something growing up from the ground (its foot at the bottom
    middle). leaf: a leaf's length as a part of the picture; slim: its width as a part of its length."""
    c = Canvas(size, size, clear=_shade(dark, 0.9))
    rnd = random.Random(seed)
    mid = (size - 1) / 2.0
    for layer in range(3):                                      # dark leaves behind, light ones in front
        for _ in range(leaves // 3):
            if shape == 'ball':
                ang, r = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random()) * (0.93 - 0.06 * layer)
                x, y = mid + math.cos(ang) * r * mid, mid + math.sin(ang) * r * mid
            else:
                ang, r = rnd.uniform(0, math.pi), math.sqrt(rnd.random())
                x, y = mid + math.cos(ang) * r * mid * 0.95, size - 3 - math.sin(ang) * r * (size - 10) * 0.97
            turn, ln = rnd.uniform(0, 2 * math.pi), size * leaf * rnd.uniform(0.7, 1.3)
            col = _shade(_mix(dark, light, 0.15 + 0.35 * layer + rnd.random() * 0.25), rnd.uniform(0.85, 1.1))
            c.blade((x, y), (x + math.cos(turn) * ln, y + math.sin(turn) * ln), ln * slim, col, tip=0.25, steps=4)
    for _ in range(flowers):
        ang, r = rnd.uniform(0.2, math.pi - 0.2), 0.3 + 0.6 * math.sqrt(rnd.random())
        x, y = mid + math.cos(ang) * r * mid * 0.85, size - 4 - math.sin(ang) * r * (size - 12) * 0.88
        rad = size * rnd.uniform(0.014, 0.022)
        for k in range(5):
            a = 2 * math.pi * k / 5 + rnd.random()
            c.line((x, y), (x + math.cos(a) * rad, y + math.sin(a) * rad), rad * 1.1, _shade(bloom, rnd.uniform(0.9, 1.1)), 0.2)
    for k in range(stems):
        c.blade((mid + (k - stems / 2.0) * size * 0.015, size - 1), (mid + (k - stems / 2.0) * size * 0.08, size * 0.7), size * 0.014, (70, 58, 42), tip=0.5, steps=4)
    return c


def fern_frond(w=128, h=256, seed=41, colour=FERN_GREEN):
    """A fern's leaf laid flat, its stalk at the bottom middle: side leaves off a stem, longest low down and shorter
    to a point at the tip, each with a paler rib."""
    c = Canvas(w, h, clear=_shade(colour, 0.75))
    rnd = random.Random(seed)
    mid = (w - 1) / 2.0
    pairs = 26
    for k in range(pairs):
        t = (k + 0.5) / pairs                                   # 0 at the tip, 1 at the stalk
        y = h * (0.02 + 0.8 * t)
        reach = mid * 0.97 * (t ** 0.75) * (1.0 if t < 0.82 else (1 - t) / 0.18 * 0.6 + 0.4)
        for side in (-1, 1):
            col = _shade(_mix(_shade(colour, 0.7), colour, rnd.random()), rnd.uniform(0.9, 1.1))
            tip = (mid + side * reach * rnd.uniform(0.9, 1.0), y - h * 0.035 * rnd.uniform(0.6, 1.4))
            c.blade((mid, y), tip, h / pairs * 1.05, col, tip=0.12, bend=-0.05 * side, steps=6)
            c.blade((mid, y), tip, 1.4, _shade(colour, 1.25), tip=0.5, bend=-0.05 * side, steps=6, raise_=0.2)
    c.line((mid, h * 0.01), (mid, h - 1), max(2.2, w / 44.0), (92, 78, 46), 0.25)
    return c


def stalk_leaf(w=128, h=256, seed=42, colour=(64, 128, 58)):
    """A taro's leaf: a long bare stalk up the lower half of the picture and a great heart of a leaf above it, its
    point upward (the far end of a frond), ribs fanning from where the stalk joins."""
    c = Canvas(w, h, clear=colour)
    big = Noise(seed, 8)
    mid = (w - 1) / 2.0
    top, join = h * 0.02, h * 0.5
    for y in range(h):
        for x in range(w):
            i = y * w + x
            u = (x - mid) / mid
            if y < join + h * 0.15:
                v = (y - top) / (join - top)                    # 0 at the leaf's point, 1 at the stalk; past 1 the two lobes
                if v <= 0.72:
                    half = 0.96 * (max(0.0, v) / 0.72) ** 0.7                       # from the point, widening
                elif v <= 1:
                    half = 0.96 - 0.1 * (v - 0.72) / 0.28
                else:
                    half = 0.86 * max(0.0, 1 - (v - 1) / 0.3) ** 0.6                # the two lobes past the stalk
                notch = v > 0.8 and abs(u) < (v - 0.8) * 0.9
                if 0 <= v and abs(u) <= half and not notch:
                    ang = math.atan2(abs(x - mid), join - y)    # ribs fan out from the join
                    rib = abs(math.sin(ang * 7)) < 0.09 or abs(u) < 0.035
                    f = 0.85 + 0.2 * big.at(x * 8.0 / w, y * 8.0 / h)
                    c.rgb[i], c.ht[i], c.a[i] = (_shade(LEAF_LIGHT, 1.05), 0.62, 1.0) if rib else (_shade(colour, f), 0.48, 1.0)
    c.line((mid, join), (mid, h - 1), max(3.0, w / 26.0), _shade(LEAF_LIGHT, 0.85), 0.2)
    return c


def lance_leaf(colour=TI_RED, rib=(210, 96, 120), w=64, h=128, seed=43):
    """A ti plant's leaf: a long pointed blade with a rib down it, streaked along its length. Stalk at the bottom."""
    c = Canvas(w, h, clear=colour)
    fine = Noise(seed, 32)
    mid = (w - 1) / 2.0
    for y in range(h):
        t = y / (h - 1.0)
        half = mid * 0.92 * math.sin(math.pi * min(1.0, 0.04 + t * 0.9)) ** 0.75
        for x in range(w):
            off = abs(x - mid)
            if off <= half:
                i = y * w + x
                streak = fine.at(x * 32.0 / w * 1.5, y * 32.0 / h / 6)
                if off < 1.5:
                    c.rgb[i], c.ht[i], c.a[i] = rib, 0.65, 1.0
                else:
                    c.rgb[i], c.ht[i], c.a[i] = _shade(_mix(colour, rib, max(0.0, streak - 0.55)), 0.8 + 0.35 * streak), 0.5, 1.0
    return c


def vines(w=128, h=256, seed=44, colour=JUNGLE_GREEN):
    """Vines hanging from a bough: strands from the top of the picture to different lengths, leaves all down them."""
    c = Canvas(w, h, clear=_shade(colour, 0.8))
    rnd = random.Random(seed)
    for k in range(8):
        x0 = w * (0.08 + 0.84 * (k + rnd.uniform(0.2, 0.8)) / 8)
        ln = h * rnd.uniform(0.45, 1.0)
        sway, wave, ph = rnd.uniform(2, 7), rnd.uniform(0.03, 0.07), rnd.uniform(0, 6)
        at = lambda y: x0 + sway * math.sin(y * wave + ph)
        y = 0.0
        while y < ln:
            c.line((at(y), y), (at(y + 4), y + 4), 1.8, (70, 64, 40), 0.15)
            if rnd.random() < 0.55:
                side = rnd.choice((-1, 1))
                size = rnd.uniform(5, 10) * (1.2 - 0.4 * y / ln)
                col = _shade(_mix(JUNGLE_DARK, JUNGLE_LIGHT, rnd.random()), rnd.uniform(0.85, 1.1))
                c.blade((at(y), y), (at(y) + side * size, y + size * rnd.uniform(0.3, 1.0)), size * 0.6, col, tip=0.3, steps=3)
            y += 4
    return c


def heliconia(size=256, seed=45):
    """A stand of heliconia from the side: tall stalks with paddle leaves, and hanging from them the flowers: a
    zigzag of red claws tipped yellow."""
    c = Canvas(size, size, clear=JUNGLE_GREEN)
    rnd = random.Random(seed)
    mid = (size - 1) / 2.0
    for k in range(7):
        lean = (k - 3) / 3.0 + rnd.uniform(-0.15, 0.15)
        foot = (mid + lean * size * 0.06, size - 1)
        head = (mid + lean * size * 0.36, size * rnd.uniform(0.08, 0.3))
        c.blade(foot, head, size * 0.016, (96, 128, 60), tip=0.6, bend=0.08 * lean, steps=8)
        for j in range(3):                                      # paddle leaves up the stalk
            t = 0.45 + 0.2 * j
            at = (foot[0] + (head[0] - foot[0]) * t, foot[1] + (head[1] - foot[1]) * t)
            side = 1 if (j + k) % 2 else -1
            c.blade(at, (at[0] + side * size * rnd.uniform(0.1, 0.17), at[1] - size * rnd.uniform(0.12, 0.2)), size * 0.07,
                    _shade(_mix(JUNGLE_GREEN, JUNGLE_LIGHT, rnd.random()), rnd.uniform(0.9, 1.1)), tip=0.2, bend=0.15 * side, steps=6)
        if k % 2 == 0:                                          # a flower hanging from near the top
            x, y = head[0] + rnd.uniform(-6, 6), head[1] + size * 0.04
            for j in range(6):
                side = 1 if j % 2 else -1
                c.blade((x, y), (x + side * size * 0.05, y + size * 0.012), size * 0.026, _shade((208, 44, 40), rnd.uniform(0.9, 1.1)), tip=0.35, steps=3, raise_=0.2)
                c.line((x + side * size * 0.05, y + size * 0.012), (x + side * size * 0.056, y + size * 0.014), size * 0.012, YELLOW, 0.25)
                y += size * 0.03
    return c


def bark_furrowed(colour=(98, 84, 66), moss=0.3, size=128, seed=46):
    """A forest tree's bark: furrows running up it, moss in patches where it stays wet. Repeats."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)

    def fn(x, y):
        g = fine.at(x * 64.0 / size, y * 64.0 / size / 7)        # (stretched up the trunk)
        g2 = fine.at(x * 64.0 / size * 2 + 9, y * 64.0 / size / 3)
        furrow = g < 0.34
        m = big.at(x * 8.0 / size, y * 8.0 / size) * 0.75 + g2 * 0.25
        col = _shade(colour, 0.5 if furrow else 0.8 + 0.4 * g)
        if m > 1 - moss and not furrow:
            col = _mix(col, _shade(MOSS, 0.8 + 0.4 * g2), min(1.0, (m - (1 - moss)) * 6))
        return col, 0.25 if furrow else 0.5 + 0.2 * g
    c.paint(fn)
    return c


# ---------- hotels: a square of each picture is one room's bay across and one floor up ----------

CONCRETE_WHITE = (226, 222, 208)
GLASS_DARK = (34, 48, 56)
ALUMINIUM = (156, 160, 156)
PINK = (236, 160, 160)
LAVA = (62, 54, 52)


def _streaks(big, fine, x, y, size):
    """How clean a wall is at a spot, 0.65 to 1: rain has run down it for two hundred years."""
    run = fine.at(x * 64.0 / size, y * 64.0 / size / 9)
    return 0.72 + 0.2 * run + 0.12 * big.at(x * 8.0 / size, y * 8.0 / size)


def facade_lanai(wall=CREAM, front=None, size=256, seed=60):
    """One room of a hotel's face: the edge of the floor above, in its shadow a glass door set back between two piers,
    and across the lanai's front a railing, or with `front` (a colour) a solid painted panel as the fifties liked."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    S = float(size)

    def fn(x, y):
        u, v = x / S, y / S
        dirt = _streaks(big, fine, x, y, size)
        if v < 0.1:                                             # the slab above
            return _shade(CONCRETE_WHITE, dirt * (0.92 + 0.08 * (v / 0.1))), 0.85
        col, h = _shade(wall, dirt * 0.9), 0.5
        if v < 0.17:
            col = _shade(col, 0.45 + 2.5 * (v - 0.1))           # its shadow
        if 0.1 < u < 0.9 and v > 0.19:
            frame = min(u - 0.1, 0.9 - u, v - 0.19) < 0.018 or abs(u - 0.5) < 0.012
            glint = 0.85 + 0.5 * max(0.0, 1 - abs((u - v * 0.4) - 0.3) * 6)         # a pale slant across the glass
            col, h = (_shade(ALUMINIUM, dirt), 0.5) if frame else (_shade(GLASS_DARK, glint * (0.8 + 0.3 * fine.at(x * 0.5, y * 0.5))), 0.3)
            if not frame and u > 0.52 and v < 0.75 and fine.at(3.3, 7.1) > 0.3:
                col = _mix(col, _shade(CREAM, 0.7), 0.35)       # a curtain still up behind one pane
        if front is not None:
            if 0.66 < v < 0.97:
                rust = big.at(x * 8.0 / size + 3, y * 8.0 / size) * 0.6 + fine.at(x * 64.0 / size, y * 64.0 / size) * 0.4
                col, h = (_mix((132, 78, 50), (96, 60, 44), fine.at(y * 0.3, x * 0.3)), 0.6) if rust > 0.8 else (_shade(_faded(front, 0.12), dirt), 0.68)
            if 0.63 < v <= 0.66:
                col, h = _shade(CONCRETE_WHITE, dirt), 0.75
        elif v > 0.62:
            if v < 0.645 or (x % max(8, size // 20)) < 2:
                col, h = _shade(CONCRETE_WHITE, dirt), 0.75
        return col, h
    c.paint(fn)
    return c


def breeze_blocks(size=128, seed=61, across=4):
    """A screen wall of pierced concrete blocks: a round hole in each and a quarter of one at each corner."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    cell = size / float(across)

    def fn(x, y):
        fx, fy = (x % cell) / cell - 0.5, (y % cell) / cell - 0.5
        hole = math.hypot(fx, fy) < 0.27 or math.hypot(abs(fx) - 0.5, abs(fy) - 0.5) < 0.2
        joint = min(abs(abs(fx) - 0.5), abs(abs(fy) - 0.5)) < 0.03
        dirt = _streaks(big, fine, x, y, size)
        if hole:
            return (26, 28, 30), 0.1
        return _shade(CONCRETE_WHITE, dirt * (0.8 if joint else 1.0)), 0.5 if joint else 0.7
    c.paint(fn)
    return c


def stucco(colour=CREAM, size=256, seed=62):
    """A plain rendered wall, stained where the rain runs."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)

    def fn(x, y):
        g = fine.at(x * 64.0 / size * 1.7, y * 64.0 / size * 1.7)
        return _shade(colour, _streaks(big, fine, x, y, size) * (0.94 + 0.1 * g)), 0.45 + 0.1 * g
    c.paint(fn)
    return c


def facade_arch(wall=PINK, size=256, seed=63):
    """One bay of an old grand hotel: a tall window with a round head in a stuccoed wall, a little iron balcony at
    its foot, a pale band where the floor is."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    S = float(size)

    def fn(x, y):
        u, v = x / S, y / S
        dirt = _streaks(big, fine, x, y, size)
        if v < 0.06:
            return _shade(CREAM, dirt), 0.7
        in_rect = abs(u - 0.5) < 0.2 and 0.36 < v < 0.86
        d_head = math.hypot(u - 0.5, v - 0.36)
        in_head = d_head < 0.2 and v <= 0.36
        if in_rect or in_head:
            edge = (abs(abs(u - 0.5) - 0.2) < 0.016 and v > 0.36) or (in_head and d_head > 0.184) or abs(u - 0.5) < 0.01 or abs(v - 0.36) < 0.008
            if edge:
                return _shade(CONCRETE_WHITE, dirt), 0.6
            return _shade(GLASS_DARK, 0.8 + 0.4 * fine.at(x * 0.4, y * 0.4)), 0.3
        col, h = _shade(wall, dirt * (0.95 + 0.08 * fine.at(x * 1.3, y * 1.3))), 0.5
        if abs(u - 0.5) < 0.27 and 0.78 < v < 0.92 and (v < 0.795 or v > 0.905 or (x % max(6, size // 26)) < 2):
            return (40, 40, 42), 0.62                           # the balcony's ironwork
        if abs(u - 0.5) < 0.25 and (d_head < 0.235 and v <= 0.36 or (abs(abs(u - 0.5) - 0.22) < 0.018 and 0.36 < v < 0.86)):
            col, h = _shade(CREAM, dirt), 0.58                  # a raised surround
        return col, h
    c.paint(fn)
    return c


def lava_rock(size=256, seed=64):
    """A wall of dark lava stone, rough, pale mortar between: every fifties lobby in the islands had one."""
    c = Canvas(size, size)
    a, b, fine = Noise(seed, 8), Noise(seed + 7, 8), Noise(seed + 1, 64)

    def fn(x, y):
        n1 = a.at(x * 8.0 / size * 1.0, y * 8.0 / size * 1.6)
        n2 = b.at(x * 8.0 / size * 1.6 + 2.5, y * 8.0 / size * 1.0)
        g = fine.at(x * 64.0 / size, y * 64.0 / size)
        if min(abs(n1 - 0.5), abs(n2 - 0.5)) < 0.022:
            return _shade((150, 142, 128), 0.8 + 0.3 * g), 0.3
        stone = 0.75 + 0.5 * a.at(x * 8.0 / size * 0.5 + (n1 > 0.5) * 3.1, y * 8.0 / size * 0.5 + (n2 > 0.5) * 5.3)
        return _shade(LAVA, stone * (0.8 + 0.4 * g)), 0.55 + 0.2 * g
    c.paint(fn)
    return c


def shopfront(size=256, seed=65):
    """A lobby's wall of glass: a transom, slim frames, a pair of doors in every bay, a kick rail."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)
    S = float(size)

    def fn(x, y):
        u, v = x / S, y / S
        dirt = _streaks(big, fine, x, y, size)
        frame = (u % 0.25) < 0.02 or abs(v - 0.28) < 0.012 or v < 0.03
        if v > 0.93:
            return _shade((70, 72, 72), dirt), 0.6
        if frame:
            return _shade(ALUMINIUM, dirt), 0.6
        door = 0.25 < u < 0.75 and v > 0.29
        glint = 0.8 + 0.5 * max(0.0, 1 - abs((u - v * 0.5) % 0.5 - 0.2) * 7)
        col = _shade((40, 62, 64) if not door else (30, 44, 48), glint * (0.85 + 0.25 * fine.at(x * 0.4, y * 0.4)))
        if door and abs(v - 0.62) < 0.012 and abs((u % 0.25) - 0.135) < 0.09:
            return _shade(ALUMINIUM, 1.1), 0.65                 # push bars
        return col, 0.35
    c.paint(fn)
    return c


def far_facade(wall=CREAM, front=None, bays=8, floors=8, size=64, seed=66):
    """A whole face of a hotel as it reads from across the bay: rows of dark windows between pale floor edges."""
    c = Canvas(size, size)
    big = Noise(seed, 8)

    def fn(x, y):
        u, v = (x * bays / float(size)) % 1.0, (y * floors / float(size)) % 1.0
        dirt = 0.85 + 0.2 * big.at(x * 8.0 / size, y * 8.0 / size)
        if v < 0.16:
            return _shade(CONCRETE_WHITE, dirt), 0.5
        if front is not None and v > 0.64:
            return _shade(_faded(front, 0.12), dirt), 0.5
        if 0.14 < u < 0.86:
            return _shade(GLASS_DARK, 1.2 * dirt), 0.5
        return _shade(wall, dirt * 0.9), 0.5
    c.paint(fn)
    return c


# ---------- the ground itself (these repeat: everything is noise that wraps) ----------

def ground_grass(size=512, seed=80):
    """Thick wet-country grass seen from above: blades lying every way, darker where it is deep, a yellower tip
    here and there."""
    c = Canvas(size, size)
    big, mid, fine, fine2 = Noise(seed, 6), Noise(seed + 1, 24), Noise(seed + 2, 128), Noise(seed + 3, 128)
    k = 128.0 / size

    def fn(x, y):
        a = fine.at(x * k * 1.0, y * k * 0.22)                 # blades lying one way
        b = fine2.at(x * k * 0.22 + 31, y * k * 1.0)           # and the other
        blade = max(a, b)
        deep = big.at(x * 6.0 / size, y * 6.0 / size) * 0.6 + mid.at(x * 24.0 / size, y * 24.0 / size) * 0.4
        col = _mix((38, 84, 30), (104, 156, 52), blade * 0.75 + deep * 0.25)
        if blade > 0.86:
            col = _mix(col, (168, 180, 78), (blade - 0.86) * 4)
        return _shade(col, 0.82 + 0.3 * deep), 0.3 + 0.5 * blade
    c.paint(fn)
    return c


def ground_litter(size=512, seed=81):
    """A forest floor: dark wet earth, fallen leaves in every stage of going back to it, moss creeping over."""
    c = Canvas(size, size)
    big, mid, fine, spot = Noise(seed, 6), Noise(seed + 1, 20), Noise(seed + 2, 128), Noise(seed + 3, 48)

    def fn(x, y):
        earth = _shade((58, 46, 30), 0.75 + 0.5 * fine.at(x * 128.0 / size, y * 128.0 / size))
        moss = big.at(x * 6.0 / size, y * 6.0 / size) * 0.55 + mid.at(x * 20.0 / size, y * 20.0 / size) * 0.45
        col, h = earth, 0.4
        if moss > 0.46:
            col = _mix(earth, _shade((54, 98, 38), 0.8 + 0.4 * fine.at(y * 128.0 / size, x * 128.0 / size)), min(1.0, (moss - 0.46) * 5))
            h = 0.5
        leaf = spot.at(x * 48.0 / size, y * 48.0 / size)
        leaf2 = spot.at(x * 48.0 / size + 17.3, y * 48.0 / size + 9.1)
        if leaf > 0.74:                                          # a fallen leaf: yellow, brown or still green
            tone = ((150, 128, 52), (112, 78, 40), (86, 124, 48))[int(leaf2 * 2.999)]
            col, h = _mix(col, tone, min(1.0, (leaf - 0.74) * 9)), 0.62
        return col, h
    c.paint(fn)
    return c


def ground_moss(size=512, seed=82):
    """Moss and low creeping green over everything: velvet, with dark between the cushions."""
    c = Canvas(size, size)
    big, mid, mid2, fine = Noise(seed, 5), Noise(seed + 1, 28), Noise(seed + 4, 47), Noise(seed + 2, 128)

    def fn(x, y):
        cushion = mid.at(x * 28.0 / size, y * 28.0 / size) * 0.6 + mid2.at(x * 47.0 / size, y * 47.0 / size) * 0.4
        g = fine.at(x * 128.0 / size, y * 128.0 / size)
        lit = big.at(x * 5.0 / size, y * 5.0 / size)
        col = _mix((36, 70, 30), (104, 148, 56), cushion * 0.7 + g * 0.3)
        if cushion < 0.3:
            col = _mix((30, 40, 24), col, cushion / 0.3)
        return _shade(col, 0.8 + 0.35 * lit), 0.25 + 0.6 * cushion
    c.paint(fn)
    return c


def ground_mossy_rock(size=512, seed=83):
    """Rock on a wet mountainside: dark stone, cracked, green over most of it, bare only where it is sheer."""
    c = Canvas(size, size)
    big, mid, crack, fine = Noise(seed, 5), Noise(seed + 1, 18), Noise(seed + 2, 12), Noise(seed + 3, 128)

    def fn(x, y):
        g = fine.at(x * 128.0 / size, y * 128.0 / size)
        stone = _shade((88, 84, 76), 0.7 + 0.5 * mid.at(x * 18.0 / size, y * 18.0 / size) * (0.7 + 0.6 * g))
        cr = abs(crack.at(x * 12.0 / size, y * 12.0 / size * 1.7) - 0.5)
        h = 0.55 + 0.2 * g
        if cr < 0.02:
            stone, h = _shade(stone, 0.45), 0.2
        moss = big.at(x * 5.0 / size, y * 5.0 / size) * 0.5 + mid.at(x * 18.0 / size + 7.7, y * 18.0 / size) * 0.5
        if moss > 0.36:                                          # (most of it)
            green = _mix((40, 78, 34), (96, 136, 54), g * 0.6 + moss * 0.4)
            return _mix(stone, green, min(1.0, (moss - 0.36) * 6)), h + 0.08
        return stone, h
    c.paint(fn)
    return c


def ground_yard(size=512, seed=84):
    """Lived-in ground in a town gone to seed: trodden sandy earth, small stones, weeds coming through in patches."""
    c = Canvas(size, size)
    big, mid, fine, spot = Noise(seed, 6), Noise(seed + 1, 22), Noise(seed + 2, 128), Noise(seed + 3, 64)

    def fn(x, y):
        g = fine.at(x * 128.0 / size, y * 128.0 / size)
        earth = _shade((150, 132, 100), 0.78 + 0.32 * (big.at(x * 6.0 / size, y * 6.0 / size) * 0.5 + g * 0.5))
        h = 0.45 + 0.1 * g
        if spot.at(x * 64.0 / size, y * 64.0 / size) > 0.83:
            earth, h = _shade((120, 114, 104), 0.8 + 0.4 * g), 0.62    # a stone
        weeds = mid.at(x * 22.0 / size, y * 22.0 / size) * 0.6 + big.at(x * 6.0 / size + 3.3, y * 6.0 / size) * 0.4
        if weeds > 0.6:
            green = _mix((70, 104, 44), (124, 150, 66), g)
            return _mix(earth, green, min(1.0, (weeds - 0.6) * 5) * (0.5 + 0.5 * g)), h + 0.08
        return earth, h
    c.paint(fn)
    return c


def leaf_spray(size=256, seed=90, dark=JUNGLE_DARK, light=JUNGLE_LIGHT, leaf=0.075, slim=0.42, flowers=0, bloom=HIBISCUS):
    """A bough's end with its leaves, laid flat: a stem from the bottom middle, twigs off it to both sides, leaves all
    along them, ragged at the edge with sky showing through. A tree's crown is many of these fanning from each bough's
    end, which reads as branches in leaf where one round mass of leaves read as a ball."""
    c = Canvas(size, size, clear=_shade(dark, 0.9))
    rnd = random.Random(seed)
    mid = (size - 1) / 2.0
    lean = rnd.uniform(-0.08, 0.08) * size
    stem = lambda t: (mid + lean * t * t, size - 1 - t * size * 0.9)       # t: 0 at the foot, 1 at the tip
    twigs = [(stem(0.0), stem(1.0))]
    for k in range(9):
        t = 0.18 + 0.78 * k / 8.0
        side = 1 if k % 2 else -1
        a = stem(t)
        ln = size * (0.42 - 0.26 * t) * rnd.uniform(0.8, 1.15)
        ang = math.radians(rnd.uniform(35, 62))
        twigs.append((a, (a[0] + side * math.sin(ang) * ln, a[1] - math.cos(ang) * ln)))
    for layer in range(2):                                      # the leaves, darker ones first
        for a, b in twigs:
            n = max(6, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (size * 0.022)))
            for k in range(n):
                t = (k + rnd.random()) / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                turn = math.atan2(b[1] - a[1], b[0] - a[0]) + rnd.choice((-1, 1)) * rnd.uniform(0.5, 1.3)
                ln = size * leaf * rnd.uniform(0.7, 1.3)
                col = _shade(_mix(dark, light, 0.2 + 0.45 * layer + rnd.random() * 0.3), rnd.uniform(0.85, 1.1))
                c.blade((x, y), (x + math.cos(turn) * ln, y + math.sin(turn) * ln), ln * slim, col, tip=0.2, steps=4)
    for _ in range(flowers):                                    # flowers at the twigs' ends, open to the light
        a, b = rnd.choice(twigs[1:]) if len(twigs) > 1 else twigs[0]
        t = rnd.uniform(0.6, 1.0)
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        rad = size * rnd.uniform(0.04, 0.055)
        for k in range(5):
            ang = 2 * math.pi * k / 5 + rnd.random()
            c.line((x, y), (x + math.cos(ang) * rad, y + math.sin(ang) * rad), rad * 1.15, _shade(bloom, rnd.uniform(0.9, 1.1)), 0.25)
        c.line((x, y), (x, y), rad * 0.5, YELLOW, 0.3)
    for a, b in twigs:                                          # the wood shows through at the foot
        c.blade(a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), size * 0.014, (72, 60, 44), tip=0.4, steps=4)
    return c


def corrugated(colour=(128, 132, 128), size=256, seed=95, ridges=16):
    """Corrugated iron: ridges running down the sheet, rust coming through from its edges and its nail holes."""
    c = Canvas(size, size)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)

    def fn(x, y):
        wave = 0.5 + 0.5 * math.sin(x * 2 * math.pi * ridges / size)
        r = big.at(x * 8.0 / size, y * 8.0 / size) * 0.65 + fine.at(x * 64.0 / size, y * 64.0 / size / 5) * 0.35
        col = _shade(colour, 0.7 + 0.4 * wave)
        if r > 0.52:
            col = _mix(col, _mix((124, 72, 44), (86, 52, 36), fine.at(y * 0.2, x * 0.2)), min(1.0, (r - 0.52) * 5))
        return col, 0.3 + 0.5 * wave
    c.paint(fn)
    return c


# ---------- the island's own materials ----------

THATCH = (176, 150, 98)
KOA = (128, 78, 46)
RATTAN = (196, 160, 104)
TIKI_WOOD = (112, 78, 52)


def thatch(size=256, seed=110, colour=THATCH):
    """Pili grass laid in courses: long straw strands running down the slope, each course's ragged edge over the next,
    greyed and darkened where the rain runs."""
    c = Canvas(size, size)
    big, fine, strand = Noise(seed, 8), Noise(seed + 1, 64), Noise(seed + 2, 128)
    course = size / 6.0

    def fn(x, y):
        g = strand.at(x * 128.0 / size * 1.6, y * 128.0 / size / 10)       # strands, long down the picture
        k = (y % course) / course
        lip = 0.75 + 0.25 * fine.at(x * 64.0 / size, 3.0 + int(y // course))
        h = 0.3 + 0.5 * k
        f = (0.6 + 0.5 * g) * (0.75 + 0.3 * k)
        wet = big.at(x * 8.0 / size, y * 8.0 / size)
        col = _mix(colour, (92, 88, 72), max(0.0, wet - 0.55) * 1.5)
        if k > lip:
            return _shade(col, 0.5), 0.2                                    # the shadow under a course's edge
        return _shade(col, f), h
    c.paint(fn)
    return c


def wicker(size=128, seed=111, colour=RATTAN, across=8):
    """Woven rattan: strands over and under, the gaps dark."""
    c = Canvas(size, size)
    fine = Noise(seed, 32)
    cell = size / float(across)

    def fn(x, y):
        i, j = int(x / cell), int(y / cell)
        u, v = (x % cell) / cell, (y % cell) / cell
        over = (i + j) % 2 == 0
        band = abs((v if over else u) - 0.5) < 0.38
        if not band:
            return _shade(colour, 0.35), 0.15
        round_ = 1 - abs((v if over else u) - 0.5) / 0.38
        g = fine.at(x * 32.0 / size, y * 32.0 / size)
        return _shade(colour, 0.7 + 0.35 * round_ + 0.1 * g), 0.4 + 0.4 * round_
    c.paint(fn)
    return c


def tiki_face(w=128, h=256, seed=112, colour=TIKI_WOOD):
    """A carved post seen front on: a great mouth with its tongue out, flared nose, round eyes under a heavy brow, a
    crest on top; adze marks all over; the cuts dark, the faces of the carving lit. Fitted to one face of a post."""
    c = Canvas(w, h)
    big, fine = Noise(seed, 8), Noise(seed + 1, 64)

    def fn(x, y):
        g = fine.at(x * 64.0 / w / 2, y * 64.0 / h * 2)
        f = 0.75 + 0.3 * g + 0.1 * big.at(x * 8.0 / w, y * 8.0 / h)
        return _shade(colour, f), 0.55 + 0.1 * g
    c.paint(fn)
    W, H = float(w), float(h)
    cut = _shade(colour, 0.35)

    def ring(cx, cy, rx, ry, thick):
        for k in range(24):
            a0, a1 = 2 * math.pi * k / 24, 2 * math.pi * (k + 1) / 24
            c.line((cx + rx * math.cos(a0), cy + ry * math.sin(a0)), (cx + rx * math.cos(a1), cy + ry * math.sin(a1)), thick, cut, -0.25)
    ring(W * 0.3, H * 0.33, W * 0.13, H * 0.05, 4)                          # the eyes
    ring(W * 0.7, H * 0.33, W * 0.13, H * 0.05, 4)
    c.line((W * 0.12, H * 0.25), (W * 0.88, H * 0.25), 6, cut, -0.25)      # the brow
    c.line((W * 0.5, H * 0.38), (W * 0.36, H * 0.5), 4, cut, -0.25)        # the nose
    c.line((W * 0.5, H * 0.38), (W * 0.64, H * 0.5), 4, cut, -0.25)
    c.line((W * 0.34, H * 0.5), (W * 0.66, H * 0.5), 4, cut, -0.25)
    ring(W * 0.5, H * 0.64, W * 0.36, H * 0.09, 6)                         # the mouth
    for k in range(5):                                                      # teeth
        x = W * (0.24 + 0.13 * k)
        c.line((x, H * 0.58), (x, H * 0.62), 3, _shade(CREAM, 0.8), 0.2)
    c.line((W * 0.5, H * 0.66), (W * 0.5, H * 0.76), 10, _shade(RED, 0.7), 0.15)     # the tongue
    for k in range(4):                                                      # the crest
        c.line((W * (0.2 + 0.2 * k), H * 0.02), (W * (0.3 + 0.2 * k), H * 0.16), 5, cut, -0.25)
    for k in range(6):                                                      # bands down the body
        y = H * (0.8 + 0.03 * k)
        c.line((W * 0.05, y), (W * 0.95, y), 2, cut, -0.2)
    return c


def net(size=256, seed=113, colour=(150, 140, 112), mesh=12):
    """Fishing net: knotted twine in diamonds, sagging; see-through between."""
    c = Canvas(size, size, clear=colour)
    rnd = random.Random(seed)
    step = size / float(mesh)
    for k in range(-mesh, 2 * mesh):
        for sign_ in (-1, 1):
            x0 = k * step
            wob = rnd.uniform(-2, 2)
            c.line((x0, 0), (x0 + sign_ * size, size + wob), 1.6, _shade(colour, rnd.uniform(0.8, 1.1)), 0.2)
    for i in range(mesh * 2):
        for j in range(mesh * 2):
            if (i + j) % 2 == 0:
                c.line((i * step / 2, j * step / 2), (i * step / 2, j * step / 2), 3.0, _shade(colour, 0.75), 0.3)    # knots
    return c


def koa_hull(size=256, seed=114, colour=KOA, paint=None):
    """A canoe's or a sampan's side: long planks of red-brown koa (or painted over and worn back to it), oiled, with
    a pale waterline band near the bottom of the picture."""
    c = planks(paint or colour, size=size, count=6, seed=seed, wear=0.35 if paint else 0.0)
    w, h = c.w, c.h
    # (the planks run up the picture; a hull's run along it: turn them)
    turned = Canvas(w, h)
    for y in range(h):
        for x in range(w):
            turned.rgb[y * w + x], turned.ht[y * w + x] = c.rgb[x * w + (h - 1 - y)], c.ht[x * w + (h - 1 - y)]
    for y in range(int(h * 0.84), int(h * 0.9)):
        for x in range(w):
            turned.rgb[y * w + x] = _mix(turned.rgb[y * w + x], WHITE, 0.6)
    return turned


def pineapples(size=256, seed=115):
    """Pineapples heaped in a crate, seen from above and the side: gold diamonds, green crowns."""
    c = Canvas(size, size)
    rnd = random.Random(seed)
    c.paint(lambda x, y: (_shade((92, 70, 40), 0.6), 0.2))
    for _ in range(22):
        cx, cy, r = rnd.uniform(0, size), rnd.uniform(0, size), size * rnd.uniform(0.09, 0.12)
        for j in range(-int(r), int(r)):
            for i in range(-int(r * 0.75), int(r * 0.75)):
                if (i / (r * 0.75)) ** 2 + (j / r) ** 2 > 1:
                    continue
                x, y = int(cx + i) % size, int(cy + j) % size
                d = ((i + j) % 8 < 1.5) or ((i - j) % 8 < 1.5)
                c.rgb[y * size + x] = _shade((206, 156, 52), 0.65 if d else 0.95 + 0.1 * rnd.random())
                c.ht[y * size + x] = 0.4 if d else 0.65
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.35
            c.blade((cx, cy - r), (cx + math.cos(a) * r * 0.9, cy - r + math.sin(a) * r * 0.9), 4, (66, 120, 52), tip=0.2, steps=3)
    return c


def husk(size=128, seed=116):
    """Coconut husk: brown fibre, a darker shell showing through."""
    c = Canvas(size, size)
    fine, big = Noise(seed, 64), Noise(seed + 1, 8)

    def fn(x, y):
        g = fine.at(x * 64.0 / size / 4, y * 64.0 / size)
        return _shade((122, 88, 52), 0.65 + 0.45 * g + 0.1 * big.at(x * 8.0 / size, y * 8.0 / size)), 0.4 + 0.3 * g
    c.paint(fn)
    return c


def leis(w=256, h=256, seed=117):
    """Flower leis hung in loops on a line, plumeria and orchid, see-through between."""
    c = Canvas(w, h, clear=(220, 180, 160))
    rnd = random.Random(seed)
    colours = [(250, 246, 226), (246, 200, 214), (196, 86, 160), (252, 214, 96), (226, 80, 80)]
    for k in range(5):
        x0, x1 = w * (0.04 + 0.19 * k), w * (0.18 + 0.19 * k)
        sag = h * rnd.uniform(0.55, 0.85)
        col = colours[k % len(colours)]
        for t in range(28):
            u = t / 27.0
            x = x0 + (x1 - x0) * u
            y = h * 0.06 + sag * math.sin(math.pi * u)
            for p_ in range(5):
                a = 2 * math.pi * p_ / 5 + t
                c.line((x, y), (x + math.cos(a) * 5, y + math.sin(a) * 5), 5, _shade(col, rnd.uniform(0.9, 1.05)), 0.2)
    c.line((0, h * 0.05), (w, h * 0.05), 2, (90, 80, 60), 0.2)
    return c


def googie(names, w=512, h=512, seed=118):
    """Mid-century motel signs, one to a quarter of the picture: a name in big letters over a line of smaller ones,
    on boards of faded enamel, a starburst at a corner (as the signs of the time had)."""
    grounds = [(246, 220, 150), (150, 210, 200), (238, 128, 108), (226, 226, 216)]
    inks = [(190, 54, 46), (24, 88, 96), (246, 240, 220), (196, 60, 48)]
    panels = []
    for n, (big_line, small) in enumerate(names[:4]):
        x, y = (n % 2) * 0.5, (n // 2) * 0.5
        panels.append({'box': (x, y, x + 0.5, y + 0.5), 'lines': [big_line] + list(small), 'ground': grounds[n % 4], 'ink': inks[n % 4],
                       'inks': [inks[n % 4]] + [TEAL_INK if n % 4 != 1 else RED] * len(small), 'edge': grounds[(n + 2) % 4]})
    c = sign(panels, w=w, h=h, seed=seed)
    rnd = random.Random(seed)
    for n in range(min(4, len(names))):
        cx, cy = w * ((n % 2) * 0.5 + 0.43), h * ((n // 2) * 0.5 + 0.07)
        for k in range(8):
            a = 2 * math.pi * k / 8 + rnd.random() * 0.2
            c.line((cx, cy), (cx + math.cos(a) * w * 0.045, cy + math.sin(a) * w * 0.045), 3, YELLOW, 0.3)
    return c


def flame(w=64, h=128, seed=127):
    """A torch's flame: white-gold at the root, orange, red at its ragged tips, see-through round it."""
    c = Canvas(w, h, clear=(240, 140, 40))
    big = Noise(seed, 8)
    for y in range(h):
        for x in range(w):
            t = 1.0 - y / (h - 1.0)                              # 0 at the root (the bottom), 1 at the top
            wob = (big.at(x * 8.0 / w, y * 8.0 / h + seed) - 0.5) * 0.4
            half = 0.48 * (1 - t) ** 0.6 + wob * t
            u = abs(x - (w - 1) / 2.0) / (w / 2.0)
            if u <= half and t < 0.95:
                i = y * w + x
                c.rgb[i] = _mix((255, 236, 170), (220, 70, 30), min(1.0, t * 1.3 + u))
                c.a[i] = 1.0
    return c


def lit_glass(colour=(255, 226, 160), size=64, seed=128):
    """Glass with a lamp behind it: warm, brightest in the middle."""
    c = Canvas(size, size)
    mid = (size - 1) / 2.0
    c.paint(lambda x, y: (_mix(colour, _shade(colour, 0.7), min(1.0, math.hypot(x - mid, y - mid) / mid)), 0.5))
    return c
