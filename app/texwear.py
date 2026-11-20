"""Textures that have lived through two hundred years after the bombs: the late-fifties seaside paint of `texpaint`,
faded, peeled, stained, rusted and cracked, then graded to the dusty, warm, washed-out colour of the Fallout games.

Why another module: `texpaint`'s pictures are each one idea drawn clean (one noise for dirt, full-strength colour),
which reads as a cartoon. What makes a surface read as old is layers, each from its own cause, at several sizes at
once:

- `Field`: noise of several octaves (fractal), worked out once for a whole picture, wrapping at its edges like
  `texpaint.Noise`; `Cells`: the nearest and next-nearest of scattered points (cracks run along where two cells meet,
  chips and stones are cells).
- surfaces under paint: render, concrete (board marks of its formwork, pits, cracks, spalls showing stone and rusty
  rebar), wood (silvered grain, splits, nail heads bleeding rust), steel (red oxide primer under the paint, rust
  pitting, flaking).
- what time does on top (`Wear`): grime gathered in the big shapes, rain streaks run down from every ledge, rust runs
  below anything iron, dust and salt low down, sun bleaching high up.
- `grade`: one colour grade for everything (less saturation, a warm cast, blacks lifted), so new pieces sit beside the
  game's own and each other.

A `Picture` is a `texpaint.Canvas` with a gloss for every pixel (the normal map's fourth number), so glass and wet
paint shine and rust and render don't. Repeating ones repeat without a seam. Seeds make the same picture every run.

`facade_sheet` draws several bays and floors of a hotel's face on one picture, each bay its own (glass whole, cracked
or gone, boarded, a shutter down, curtains, a cooler in the window), so a tower doesn't repeat one room up its face.
`UPGRADE` maps every texture name `modelsets` and `coastset` draw for the hotels and the shore to a worn painter of
the same purpose, size and layout, for dropping in once those files are free to change."""
import math
import random

import dds
import texpaint as tp

# ---------- colour ----------

RUST = (128, 64, 36)
RUST_DARK = (74, 40, 28)
RUST_LIGHT = (176, 98, 52)
PRIMER = (138, 58, 42)          # red oxide, under every coat on steel
RENDER = (164, 156, 140)        # cement render where paint has gone
GRIME = (58, 52, 42)
SALT = (214, 210, 196)
SILVER_WOOD = (128, 122, 110)
AGGREGATE = (112, 106, 96)


def clamp(v):
    return 0.0 if v < 0 else 255.0 if v > 255 else v


def mix(a, b, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def mul(c, f):
    return (c[0] * f, c[1] * f, c[2] * f)


def grade(c, sat=0.64, warm=(1.04, 0.985, 0.9), lift=12.0, contrast=0.92):
    """The look of the Mojave and the Capital Wasteland: colours drained a third of the way to grey, a warm brown
    cast, nothing quite black, a little less contrast."""
    r, g, b = c
    grey = 0.3 * r + 0.59 * g + 0.11 * b
    r, g, b = grey + (r - grey) * sat, grey + (g - grey) * sat, grey + (b - grey) * sat
    r, g, b = r * warm[0], g * warm[1], b * warm[2]
    out = []
    for v in (r, g, b):
        v = 128 + (v - 128) * contrast
        out.append(clamp(lift + v * (255 - lift) / 255))
    return tuple(out)


def smooth(e0, e1, x):
    if e1 == e0:
        return 1.0 if x >= e1 else 0.0
    t = (x - e0) / (e1 - e0)
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


# ---------- noise over a whole picture ----------

class Field:
    """Fractal noise at every pixel of a w x h picture, 0 to 1 (about 0.5 on average), repeating at its edges.
    cells: how many noise cells across the picture at the coarsest octave; stretch (sx, sy) squeezes it one way (rain
    streaks are noise stretched down); octaves halve in size each, `fall` the weight of each against the last."""

    def __init__(self, w, h, seed, cells=4, octaves=4, stretch=(1, 1), fall=0.5):
        self.w, self.h = w, h
        v = [0.0] * (w * h)
        total, amp = 0.0, 1.0
        for k in range(octaves):
            nx = max(1, int(round(cells * stretch[0] * 2 ** k)))
            ny = max(1, int(round(cells * stretch[1] * 2 ** k)))
            rnd = random.Random(seed * 131 + k)
            lat = [rnd.random() for _ in range(nx * ny)]
            fx = nx / float(w)
            fy = ny / float(h)
            # (per column, the lattice column and its smoothed weight; per row the same: a pixel is then four looks)
            cols = []
            for x in range(w):
                u = x * fx
                i = int(u)
                t = u - i
                cols.append((i % nx, (i + 1) % nx, t * t * (3 - 2 * t)))
            for y in range(h):
                s = y * fy
                j = int(s)
                t = s - j
                ty = t * t * (3 - 2 * t)
                r0, r1 = (j % ny) * nx, ((j + 1) % ny) * nx
                row = y * w
                for x, (i0, i1, tx) in enumerate(cols):
                    a, b = lat[r0 + i0], lat[r0 + i1]
                    c, d = lat[r1 + i0], lat[r1 + i1]
                    top = a + (b - a) * tx
                    v[row + x] += amp * (top + (c + (d - c) * tx - top) * ty)
            total += amp
            amp *= fall
        lo, hi = min(v), max(v)
        span = (hi - lo) or 1.0
        self.v = [(p - lo) / span for p in v]           # (stretched to fill 0-1: thresholds mean the same in every field)

    def at(self, x, y):
        return self.v[(y % self.h) * self.w + (x % self.w)]


def cracks(w, h, seed, count=6, long=0.5, branch=0.25, width=1.6):
    """Cracks as they run in render and concrete: each a wandering line from a start, turning a little at every
    step, now and then splitting, thinning to nothing at its end. A list over the picture, 0-1: how deep the crack is
    at each pixel (0: none). Wraps at the edges."""
    rnd = random.Random(seed)
    out = [0.0] * (w * h)
    todo = [(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0, 6.283), long * max(w, h) * rnd.uniform(0.5, 1.0), width) for _ in range(count)]
    while todo:
        x, y, a, left, wd = todo.pop()
        total = left
        while left > 0:
            a += rnd.gauss(0, 0.09) + (rnd.random() < 0.04) * rnd.gauss(0, 0.6)
            x, y = x + math.cos(a), y + math.sin(a)
            left -= 1
            t = left / total
            r = wd * (0.35 + 0.65 * t)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    d = math.hypot(dx + (x - int(x)) - 0.5, dy + (y - int(y)) - 0.5)
                    cover = max(0.0, min(1.0, r / 2 - d + 0.6))
                    if cover > 0:
                        q = (int(y) + dy) % h * w + (int(x) + dx) % w
                        out[q] = max(out[q], cover * (0.5 + 0.5 * t))
            if rnd.random() < branch * 0.02 and left > 20:
                todo.append((x, y, a + rnd.choice((-1, 1)) * rnd.uniform(0.5, 1.1), left * rnd.uniform(0.3, 0.6), wd * 0.7))
    return out


class Cells:
    """Points scattered one to each square of an n x n grid over the picture (wrapping). For every pixel: the
    distance to the nearest point and to the next, in grid squares, and which point is nearest."""

    def __init__(self, w, h, seed, n=8, jitter=0.9, ny=None):
        rnd = random.Random(seed)
        ny = ny or n
        self.w, self.h = w, h
        pts = [(i + 0.5 + (rnd.random() - 0.5) * jitter, j + 0.5 + (rnd.random() - 0.5) * jitter) for j in range(ny) for i in range(n)]
        self.d1, self.d2, self.id = [0.0] * (w * h), [0.0] * (w * h), [0] * (w * h)
        sx, sy = n / float(w), ny / float(h)
        for y in range(h):
            gy = y * sy
            j = int(gy)
            for x in range(w):
                gx = x * sx
                i = int(gx)
                b1 = b2 = 9.0
                bid = 0
                for dj in (-1, 0, 1):
                    jj = j + dj
                    row = (jj % ny) * n
                    for di in (-1, 0, 1):
                        ii = i + di
                        k = row + ii % n
                        px, py = pts[k]
                        px += ii - ii % n
                        py += jj - jj % ny
                        d = (px - gx) ** 2 + (py - gy) ** 2
                        if d < b1:
                            b2, b1, bid = b1, d, k
                        elif d < b2:
                            b2 = d
                p = y * w + x
                self.d1[p], self.d2[p], self.id[p] = math.sqrt(b1), math.sqrt(b2), bid

    def edge(self, p):
        """How far from where two cells meet (0 on the line)."""
        return self.d2[p] - self.d1[p]


# ---------- the picture ----------

class Picture(tp.Canvas):
    """A Canvas with a gloss per pixel (0-255: how much it shines) going into the normal map's fourth number."""

    def __init__(self, w, h, clear=None, gloss=24):
        tp.Canvas.__init__(self, w, h, clear)
        self.gloss = [gloss] * (w * h)

    def files(self, bump=4.0, shine=None, game=False, rim=False):
        if game:
            return tp.colour_map(self, rim), tp.normal_map(self, self.gloss if shine is None else [shine] * (self.w * self.h), bump)
        w, h = self.w, self.h
        col = bytearray(w * h * 4)
        nor = bytearray(w * h * 4)
        ht = self.ht
        cl = lambda v: 0 if v < 0 else 255 if v > 255 else int(v + 0.5)
        for y in range(h):
            up, dn = (y - 1) % h * w, (y + 1) % h * w
            for x in range(w):
                i = y * w + x
                r, g, b = self.rgb[i]
                col[4 * i:4 * i + 4] = bytes((cl(r), cl(g), cl(b), cl(255 * self.a[i]) if self.a else 255))
                sx = (ht[y * w + (x + 1) % w] - ht[y * w + (x - 1) % w]) * bump
                sy = (ht[dn + x] - ht[up + x]) * bump
                ln = math.sqrt(sx * sx + sy * sy + 1)
                nor[4 * i:4 * i + 4] = bytes((cl(127.5 - 127.5 * sx / ln), cl(127.5 - 127.5 * sy / ln), cl(127.5 + 127.5 / ln),
                                              cl(self.gloss[i] if shine is None else shine)))
        return dds.compress(dds.encode(w, h, bytes(col))), dds.compress(dds.encode(w, h, bytes(nor)))   # (compressed as the game keeps its own: dds.compress)


def _graded(pic, **how):
    pic.rgb = [grade(c, **how) for c in pic.rgb]
    return pic


# ---------- what time does on top of any surface ----------

class Wear:
    """The weather of a w x h picture: its noise worked out once, used by every surface drawn on it.
    ledges: rows (0-1 down the picture) under which rain runs down the wall; irons: (x, y) pixels of iron fixings
    that bleed rust below them."""

    def __init__(self, w, h, seed, grime=1.0, rain=1.0, ledges=(), irons=(), low_dust=0.0, bleach=0.0):
        self.w, self.h = w, h
        self.big = Field(w, h, seed + 1, cells=3, octaves=5)
        self.mid = Field(w, h, seed + 2, cells=12, octaves=3)
        self.fine = Field(w, h, seed + 3, cells=64, octaves=2)
        self.runs = Field(w, h, seed + 4, cells=10, octaves=3, stretch=(2.4, 0.18))
        self.grime, self.rain, self.low_dust, self.bleach = grime, rain, low_dust, bleach
        self.ledges = [v * h for v in ledges]
        self.run_of = {}
        for (ix, iy) in irons:
            self._iron(ix, iy, random.Random(seed + ix * 7 + iy))

    def _iron(self, ix, iy, rnd):
        """A rust run from (ix, iy) down: widest at the fixing, thinning and fading."""
        long = rnd.uniform(0.12, 0.35) * self.h
        wide = rnd.uniform(1.5, 3.5)
        wob = rnd.uniform(0, 6.28)
        for k in range(int(long)):
            t = k / long
            cx = ix + math.sin(wob + k * 0.08) * 1.2
            half = wide * (1 - 0.6 * t)
            for dx in range(-int(half) - 1, int(half) + 2):
                x = int(cx + dx) % self.w
                y = (iy + k) % self.h
                cover = max(0.0, 1 - abs(dx) / (half + 0.5)) * (1 - t) ** 1.4
                p = y * self.w + x
                self.run_of[p] = max(self.run_of.get(p, 0.0), cover)

    def rain_at(self, x, y):
        """0-1: how much rain-dirt has run down here (strongest just under a ledge)."""
        under = 0.35
        for ly in self.ledges:
            d = (y - ly) % self.h
            if d < self.h * 0.6:
                under = max(under, 1.0 - d / (self.h * 0.6))
        return under * smooth(0.45, 0.8, self.runs.at(x, y))

    def on(self, x, y, col, depth=0.0):
        """A colour as time has left it. depth: 0 on an open face, up to 1 in a corner or recess (grime gathers)."""
        p = (y % self.h) * self.w + (x % self.w)
        b, m, f = self.big.v[p], self.mid.v[p], self.fine.v[p]
        # big soft patches of dirt, finer mottling inside them
        dirt = self.grime * (0.55 * smooth(0.42, 0.75, b) + 0.25 * smooth(0.35, 0.8, m) + 0.35 * depth)
        col = mix(col, mul(GRIME, 0.9 + 0.3 * f), dirt * 0.55)
        col = mul(col, 0.92 + 0.16 * f)
        if self.rain:
            col = mix(col, mul(GRIME, 0.8), self.rain * 0.5 * self.rain_at(x, y))
        if self.bleach:
            col = mix(col, (238, 232, 216), self.bleach * (1 - y / float(self.h)) * (0.4 + 0.6 * b))
        if self.low_dust:
            col = mix(col, (176, 160, 132), self.low_dust * smooth(0.6, 1.0, y / float(self.h)) * (0.5 + 0.5 * m))
        r = self.run_of.get(p)
        if r:
            col = mix(col, mix(RUST, RUST_DARK, f), r * 0.85)
        return col


# ---------- surfaces ----------

def concrete(colour=(176, 170, 156), size=512, seed=200, boards=6, cracks_=0.6, spalls=0.25, wear=None, gloss=18):
    """Poured concrete gone two centuries without care: the marks of the boards it was cast against, pits, hairline
    cracks with dirt in them, and here and there a spall where the face has fallen away to the stone inside and the
    rusted rebar under that."""
    c = Picture(size, size, gloss=gloss)
    wr = wear or Wear(size, size, seed, grime=0.9, rain=0.8, ledges=(0.0,))
    crk = cracks(size, size, seed + 10, count=int(2 + 10 * cracks_), long=0.45)
    pits = Cells(size, size, seed + 11, n=40, jitter=1.0)
    spall_f = Field(size, size, seed + 13, cells=5, octaves=4)
    board = size / float(boards) if boards else 0
    rnd = random.Random(seed)
    tints = [rnd.uniform(-0.05, 0.05) for _ in range(max(1, boards))]
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            k = int(y / board) % boards if boards else 0
            col = mul(colour, 0.9 + tints[k] + 0.14 * wr.mid.v[p] + 0.1 * (f - 0.5))
            h = 0.5 + 0.06 * f
            depth = 0.0
            if boards and (y % board) < 1.5:                     # the joint between two boards
                col, h, depth = mul(col, 0.8), 0.42, 0.5
            pd = pits.d1[p]
            if pd < 0.1 and pits.id[p] % 3 == 0:                # an air pit
                col, h, depth = mul(col, 0.55), 0.35, 1.0
            if crk[p] > 0.05:                                    # a crack, dirt in it
                col, h, depth = mix(col, mul(GRIME, 0.6), crk[p]), 0.5 - 0.3 * crk[p], 1.0
            s = spall_f.v[p]
            if s > 1 - spalls * 0.3:                              # the face gone: stone in it, rebar further in
                inner = (s - (1 - spalls * 0.3)) / (spalls * 0.3)
                stone = pits.d1[p] < 0.35
                col = mul(AGGREGATE, 0.75 + 0.4 * f) if stone else mul((120, 112, 100), 0.8 + 0.2 * f)
                h = 0.3 - 0.1 * inner + (0.08 if stone else 0)
                depth = 0.6
                if inner > 0.55 and abs((x + 3) % (size // 4) - size // 8) < 2.2:     # a bar showing
                    col, h = mix(RUST_DARK, RUST_LIGHT, f), 0.4
                if inner < 0.12:
                    col, h = mul(col, 0.7), 0.4                  # its broken rim
            col = wr.on(x, y, col, depth)
            c.rgb[p], c.ht[p] = grade(col), h
    return c


def render(colour=tp.CREAM, under=None, size=512, seed=220, peel=0.35, cracks_=0.4, wear=None, repairs=0.15, gloss=20):
    """A rendered wall painted over and over: the last coat sun-bleached and peeling in islands, each with a lifted
    lip, to the coat under it (`under`: an older colour) and through that to grey render; hairline cracks running
    from the corners of nothing in particular; a patched repair of another shade here and there."""
    c = Picture(size, size, gloss=gloss)
    wr = wear or Wear(size, size, seed, grime=1.0, rain=1.0, ledges=(0.0,), bleach=0.25)
    peel_f = Field(size, size, seed + 10, cells=5, octaves=5, fall=0.55)
    peel2 = Field(size, size, seed + 11, cells=9, octaves=4)
    crk = cracks(size, size, seed + 12, count=int(1 + 8 * cracks_), long=0.4, width=1.3)
    patch = Cells(size, size, seed + 14, n=3, jitter=1.0)
    top, old = tp._faded(colour, 0.12), tp._faded(under or mix(colour, (200, 196, 180), 0.6), 0.2)
    pt = 1 - peel * 0.8
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f, m = wr.fine.v[p], wr.mid.v[p]
            col, h, depth = mul(top, 0.94 + 0.1 * m + 0.06 * (f - 0.5)), 0.52 + 0.04 * f, 0.0
            if patch.d1[p] < 0.16 and patch.id[p] % 4 == 1 and repairs:         # an old repair, a shade off
                col = mul(mix(top, (196, 190, 176), 0.5), 0.97 + 0.06 * f)
            pv = peel_f.v[p]
            if pv > pt:
                inner = pv - pt
                if inner < 0.008:                               # the lifted lip of the paint
                    col, h, depth = mul(top, 1.08), 0.66, 0.0
                elif inner < 0.018:
                    col, h, depth = mul(old, 0.5), 0.42, 0.7   # its shadow
                elif peel2.v[p] > 0.55 or inner > 0.12:
                    col, h, depth = mul(RENDER, 0.8 + 0.25 * f), 0.4 + 0.08 * f, 0.3
                else:
                    col, h = mul(old, 0.88 + 0.12 * f), 0.47
            if crk[p] > 0.05:
                col, h, depth = mix(col, mul(GRIME, 0.7), crk[p]), 0.52 - 0.3 * crk[p], 1.0
            col = wr.on(x, y, col, depth)
            c.rgb[p], c.ht[p] = grade(col), h
    return c


def steel(colour=tp.WHITE, size=256, seed=240, rust=0.4, flake=0.35, wear=None, gloss=50):
    """Painted steel: the topcoat, red oxide primer where it has flaked, rust coming up through both in blisters
    and pits, running down below them."""
    c = Picture(size, size, gloss=gloss)
    wr = wear or Wear(size, size, seed, grime=0.7, rain=0.6)
    rust_f = Field(size, size, seed + 10, cells=6, octaves=5, fall=0.6)
    flake_f = Field(size, size, seed + 11, cells=8, octaves=4)
    pits = Cells(size, size, seed + 12, n=24)
    top = tp._faded(colour, 0.1)
    rt, ft = 1 - rust * 0.45, 1 - flake * 0.45
    # rust runs down from where the rust is worst: found from the field, drawn after
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            col, h, g = mul(top, 0.92 + 0.1 * wr.mid.v[p] + 0.06 * (f - 0.5)), 0.52, gloss
            fv = flake_f.v[p]
            if fv > ft:
                col, h, g = (mul(PRIMER, 0.85 + 0.25 * f), 0.47, 20) if fv - ft > 0.012 else (mul(top, 0.7), 0.55, gloss)
            rv = rust_f.v[p]
            if rv > rt:
                inner = min(1.0, (rv - rt) / (rust * 0.3 + 0.01))
                col = mix(col, mix(RUST, RUST_DARK if pits.d1[p] < 0.25 else RUST_LIGHT, f), 0.5 + 0.5 * inner)
                h = 0.45 + 0.12 * f * inner - (0.12 if pits.d1[p] < 0.15 else 0)
                g = 6
            else:
                # the stain below rust higher up (look a little way up the field)
                up = max(rust_f.v[((y - k * 5) % size) * size + x] for k in (1, 2, 3, 4))
                if up > rt:
                    col = mix(col, RUST, 0.35 * wr.runs.v[p])
            col = wr.on(x, y, col)
            c.rgb[p], c.ht[p], c.gloss[p] = grade(col), h, g
    return c


def hull_rust(size=512, seed=260, paint=(92, 46, 38), band=(36, 38, 40)):
    """A ship's side two hundred years on a reef: almost all rust, in sheets and scabs, the old paint left in islands,
    the plates' welded seams and rivet lines raised, a pale tide line of salt and weed low down."""
    c = Picture(size, size, gloss=10)
    wr = Wear(size, size, seed, grime=0.6, rain=1.2, ledges=(0.0,), low_dust=0.0)
    sheets = Field(size, size, seed + 10, cells=4, octaves=5, fall=0.6)
    scab = Cells(size, size, seed + 11, n=30)
    plates_x, plates_y = size / 4.0, size / 3.0
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            sv = sheets.v[p]
            col = mix(mix(RUST_DARK, RUST, f), RUST_LIGHT, smooth(0.55, 0.8, wr.mid.v[p]) * 0.6)
            h = 0.45 + 0.15 * f
            if sv < 0.38:                                       # paint left
                col, h = mul(paint, 0.85 + 0.25 * f), 0.52
            if scab.d1[p] < 0.22:
                col, h = mul(col, 0.75), 0.6 - scab.d1[p]
            sx, sy = x % plates_x, y % plates_y
            if sx < 2 or sy < 2:
                col, h = mul(col, 0.7), 0.65                    # a seam
            elif (sx < 7 or sy < 7) and (int(x + y) % 9 == 0):
                col, h = mul(col, 0.9), 0.62                    # rivets
            v = y / float(size)
            if v > 0.86:
                col = mix(col, mul(band, 0.9 + 0.3 * f), 0.7)
                if 0.86 < v < 0.9:
                    col = mix(col, SALT, 0.6 * (0.5 + 0.5 * f))
                if v > 0.93:
                    col = mix(col, (56, 76, 48), 0.5 * smooth(0.4, 0.7, wr.mid.v[p]))        # weed
            col = wr.on(x, y, col)
            c.rgb[p], c.ht[p] = grade(col, sat=0.72), h
    return c


def wood(colour=None, size=256, seed=280, count=6, paint_left=0.4, across=False):
    """Boards gone silver in the sun, the grain raised where the soft wood wore away, splits, a nail head at each
    end bleeding rust down; on painted boards (`colour`) the paint hangs on in flakes, mostly in the grain's hollows."""
    c = Picture(size, size, gloss=12)
    rnd = random.Random(seed)
    nails = []
    wide = size / float(count)
    for k in range(count):
        for yy in (rnd.uniform(0.05, 0.12), rnd.uniform(0.55, 0.62)):
            nails.append((int(k * wide + wide / 2 + rnd.uniform(-3, 3)), int(yy * size)))
    wr = Wear(size, size, seed, grime=0.8, rain=0.7, irons=nails)
    grain = Field(size, size, seed + 10, cells=2, octaves=4, stretch=(6.0, 0.25))
    knot = Cells(size, size, seed + 11, n=6, ny=3)
    left = Field(size, size, seed + 12, cells=6, octaves=4)
    tint = [rnd.uniform(-0.08, 0.08) for _ in range(count)]
    paint = tp._faded(colour, 0.2) if colour else None
    for y in range(size):
        for x in range(size):
            p = y * size + x
            k = int(x / wide) % count
            edge = min(x - k * wide, (k + 1) * wide - x)
            g = grain.v[(y * size + (x + int(k * 37)) % size)]
            ring = 0.5 + 0.5 * math.sin(g * 40)
            col = mul(mix(SILVER_WOOD, (150, 132, 104), 0.3 + tint[k] * 3), 0.78 + 0.3 * ring + tint[k])
            h = 0.45 + 0.12 * ring
            kd = knot.d1[p]
            if kd < 0.09 and knot.id[p] % 3 == 0:
                col, h = mul(col, 0.55), 0.4
            if paint is not None and left.v[p] > 1 - paint_left * 0.8 - (0.1 * (1 - ring)):
                col, h = mul(paint, 0.9 + 0.12 * wr.fine.v[p]), h + 0.04
            if edge < 1.5:
                col, h = mul(col, 0.3), 0.15
            elif edge < 3:
                col = mul(col, 0.8)
            if abs(g - 0.5) < 0.006 and edge > 6:              # a split along the grain
                col, h = mul(col, 0.35), 0.2
            for nx, ny in nails:
                if abs(x - nx) <= 2 and abs(y - ny) <= 2:
                    col, h = mul(RUST_DARK, 0.9), 0.65
            col = wr.on(x, y, col)
            c.rgb[p], c.ht[p] = grade(col), h
    if across:
        c = _turn(c)
    return c


def _turn(c):
    """The picture turned a quarter: boards up becomes boards along."""
    w, h = c.w, c.h
    t = Picture(h, w)
    for y in range(h):
        for x in range(w):
            s = x * w + (w - 1 - y)
            t.rgb[y * h + x], t.ht[y * h + x], t.gloss[y * h + x] = c.rgb[s], c.ht[s], c.gloss[s]
    return t


def tar_roof(size=512, seed=300):
    """A flat roof of tar paper in overlapping runs, patched, blistered, ponding stains where water stood, gravel in
    the low places."""
    c = Picture(size, size, gloss=30)
    wr = Wear(size, size, seed, grime=0.6, rain=0.0)
    blis = Cells(size, size, seed + 10, n=18)
    pond = Field(size, size, seed + 11, cells=3, octaves=4)
    run = size / 5.0
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            col, h = mul((58, 56, 54), 0.85 + 0.3 * wr.mid.v[p] + 0.15 * f), 0.5 + 0.05 * f
            if (y % run) < 3:
                col, h = mul(col, 1.15), 0.58                   # the lap of the run above
            if blis.d1[p] < 0.2 and blis.id[p] % 4 == 0:
                col, h = mul(col, 1.1 + 0.3 * (0.2 - blis.d1[p])), 0.62 - blis.d1[p]
            pv = pond.v[p]
            if pv > 0.62:
                col = mix(col, (118, 108, 92), min(1.0, (pv - 0.62) * 6))   # where the water stood: a pale ring
                if pv > 0.7:
                    col = mix(col, mul((96, 90, 80), 0.8 + 0.4 * f), 0.6)
                    if f > 0.6:
                        col, h = mul((140, 132, 120), 0.8 + 0.3 * f), 0.6     # gravel
            col = wr.on(x, y, col)
            c.rgb[p], c.ht[p] = grade(col), h
    return c


def clay_tiles(size=512, seed=320, colour=(170, 88, 60)):
    """A roof of barrel tiles in rows: each tile rounded, a little off its neighbour's colour, some slipped or
    broken to the dark under them, lichen in pale spots and grime under each row's lip."""
    c = Picture(size, size, gloss=22)
    wr = Wear(size, size, seed, grime=0.7, rain=0.0)
    rnd = random.Random(seed)
    across, rows = 8, 10
    tw, th = size / float(across), size / float(rows)
    tone = [[rnd.uniform(-0.12, 0.1) for _ in range(across)] for _ in range(rows)]
    gone = {(rnd.randrange(rows), rnd.randrange(across)) for _ in range(4)}
    lich = Cells(size, size, seed + 10, n=40)
    for y in range(size):
        j = int(y / th)
        v = (y % th) / th
        for x in range(size):
            p = y * size + x
            off = (j % 2) * tw / 2
            i = int((x + off) / tw) % across
            u = ((x + off) % tw) / tw
            f = wr.fine.v[p]
            roundness = math.sin(u * math.pi)
            col = mul(colour, (0.55 + 0.5 * roundness) * (1 + tone[j][i]) * (0.92 + 0.12 * f))
            h = 0.3 + 0.5 * roundness - 0.15 * v
            depth = 1 - roundness
            if v > 0.88:
                col, h, depth = mul(col, 0.45), 0.15, 1.0      # the shadow under the next row's lip
            if (j, i) in gone:
                col, h = mul((48, 40, 34), 0.8 + 0.3 * f), 0.05
            elif lich.d1[p] < 0.14 and lich.id[p] % 5 == 0:
                col = mix(col, (176, 172, 132), 0.7)
            col = wr.on(x, y, col, depth * 0.6)
            c.rgb[p], c.ht[p] = grade(col), h
    return c


def terrazzo(size=256, seed=340, ground=(196, 188, 170), chips=((92, 120, 118), (176, 92, 72), (220, 214, 200), (60, 58, 56))):
    """A terrazzo deck: chips of coloured stone in pale cement, brass strips in a square, worn dull, grimy at the
    joints, cracked across."""
    c = Picture(size, size, gloss=60)
    wr = Wear(size, size, seed, grime=0.9, rain=0.0)
    ch = Cells(size, size, seed + 10, n=22, jitter=1.0)
    crk = cracks(size, size, seed + 11, count=2, long=0.6, width=1.2)
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            col, h = mul(ground, 0.9 + 0.12 * f), 0.5
            if ch.d1[p] < 0.3:
                col, h = mul(chips[ch.id[p] % len(chips)], 0.85 + 0.2 * f), 0.52
            if x % (size // 2) < 2 or y % (size // 2) < 2:
                col, h = (150, 126, 76), 0.55                   # the brass strip
            if crk[p] > 0.05:
                col, h = mix(col, mul(GRIME, 0.6), crk[p]), 0.5 - 0.25 * crk[p]
            col = wr.on(x, y, col, 0.2)
            c.rgb[p], c.ht[p], c.gloss[p] = grade(col), h, 40
    return c


def lava(size=512, seed=360):
    """Lava stone laid in a wall: rough dark stones, each its own shade, porous, mortar between gone sandy."""
    c = Picture(size, size, gloss=14)
    wr = Wear(size, size, seed, grime=0.5, rain=0.8, ledges=(0.0,))
    st = Cells(size, size, seed + 10, n=7, ny=9, jitter=0.8)
    pores = Cells(size, size, seed + 11, n=60, jitter=1.0)
    rnd = random.Random(seed)
    shade = [rnd.uniform(0.75, 1.2) for _ in range(63)]
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            e = st.edge(p)
            if e < 0.07:
                col, h = mul((140, 132, 116), 0.8 + 0.3 * f), 0.25
            else:
                col = mul(tp.LAVA, shade[st.id[p]] * (0.8 + 0.4 * f))
                h = 0.45 + min(0.25, e) + 0.1 * f
                if pores.d1[p] < 0.18:
                    col, h = mul(col, 0.5), h - 0.12
            col = wr.on(x, y, col, 0.3 if e < 0.07 else 0)
            c.rgb[p], c.ht[p] = grade(col), h
    return c


def breeze_blocks(size=256, seed=380, across=4):
    """Pierced screen blocks: each block a little off square and its own grey, holes dark with dirt round them,
    corners chipped, two or three blocks broken out altogether."""
    c = Picture(size, size, gloss=16)
    wr = Wear(size, size, seed, grime=1.0, rain=1.0, ledges=tuple(k / float(across) for k in range(across)))
    rnd = random.Random(seed)
    cell = size / float(across)
    tone = [rnd.uniform(-0.08, 0.06) for _ in range(across * across)]
    broken = {rnd.randrange(across * across) for _ in range(2)}
    chip = Field(size, size, seed + 10, cells=16, octaves=2)
    for y in range(size):
        for x in range(size):
            p = y * size + x
            i, j = int(x / cell), int(y / cell)
            fx, fy = (x % cell) / cell - 0.5, (y % cell) / cell - 0.5
            r = math.hypot(fx, fy)
            rq = math.hypot(abs(fx) - 0.5, abs(fy) - 0.5)
            hole = r < 0.27 or rq < 0.2
            joint = min(abs(abs(fx) - 0.5), abs(abs(fy) - 0.5)) < 0.03
            k = j * across + i
            if hole or (k in broken and r < 0.42):
                col, h, depth = (22, 22, 22), 0.05, 1.0
            else:
                col = mul(tp.CONCRETE_WHITE, 0.85 + tone[k] + 0.12 * wr.fine.v[p])
                h, depth = 0.65, 0.0
                if r < 0.32 or rq < 0.25:
                    col, depth = mul(col, 0.8), 0.7               # the hole's rim, dirtier
                if chip.v[p] > 0.72 and (r < 0.33 or joint):
                    col, h = mul(RENDER, 0.85), 0.5
                if joint:
                    col, h, depth = mul(col, 0.75), 0.45, 0.8
            col = wr.on(x, y, col, depth)
            c.rgb[p], c.ht[p] = grade(col), h
    return c


def glass_curtain(size=256, seed=400, frame=tp.ALUMINIUM, tint=(34, 62, 68), panes=(2, 2), broken=0.2):
    """A wall of glass in frames (a shopfront, a lobby): the sky's glare across it, grime filming each pane thickest
    at its foot, a few panes cracked in stars, one or two gone to the dark behind, frames gone dull and pitted."""
    c = Picture(size, size, gloss=150)
    wr = Wear(size, size, seed, grime=0.7, rain=0.9, ledges=tuple(k / float(panes[1]) for k in range(panes[1])))
    rnd = random.Random(seed)
    pw, ph = size / float(panes[0]), size / float(panes[1])
    state = {}
    for j in range(panes[1]):
        for i in range(panes[0]):
            r = rnd.random()
            state[(i, j)] = 'gone' if r < broken * 0.4 else 'cracked' if r < broken else 'whole'
    cracks = {k: (rnd.uniform(0.25, 0.75), rnd.uniform(0.25, 0.75), [rnd.uniform(0, 6.28) for _ in range(7)]) for k in state}
    for y in range(size):
        for x in range(size):
            p = y * size + x
            i, j = int(x / pw), int(y / ph)
            u, v = (x % pw) / pw, (y % ph) / ph
            f = wr.fine.v[p]
            fr = min(u, 1 - u, v, 1 - v) * min(pw, ph)
            if fr < 4:
                col, h, g = mul(frame, 0.75 + 0.3 * f), 0.62 + (0.05 if fr > 2 else 0), 70
                col = wr.on(x, y, col, 0.3)
            else:
                st = state[(i, j)]
                glare = 0.8 + 0.6 * max(0.0, 1 - abs((x / float(size) - y / float(size) * 0.5) % 1.0 - 0.35) * 5)
                col = mul(tint, glare * (0.9 + 0.2 * wr.mid.v[p]))
                col = mix(col, (150, 160, 158), 0.3 * (1 - v) ** 2)                          # the sky in it
                col = mix(col, (120, 112, 96), 0.3 * v ** 2 + 0.12 * wr.big.v[p])           # the film of grime
                h, g = 0.4, 150
                if st == 'gone':
                    col, g = mul((20, 22, 22), 0.8 + 0.4 * f), 0
                    if v < 0.12 or (u < 0.1 and f > 0.5):
                        col, g = mul(tint, 1.1), 150                  # shards still in the frame
                elif st == 'cracked':
                    cx, cy, angs = cracks[(i, j)]
                    dx, dy = u - cx, v - cy
                    rr = math.hypot(dx, dy)
                    a = math.atan2(dy, dx)
                    near = min(abs(((a - b) + math.pi) % (2 * math.pi) - math.pi) for b in angs)
                    if rr < 0.03 or (near * rr * min(pw, ph) < 0.9 and rr < 0.45):
                        col, h = mix(col, (210, 214, 210), 0.7), 0.5
                    elif abs(rr - 0.12) < 0.006 or abs(rr - 0.24) < 0.005:
                        col = mix(col, (190, 196, 192), 0.5)
                col = grade(col, sat=0.9)
                c.rgb[p], c.ht[p], c.gloss[p] = col, h, g
                continue
            c.rgb[p], c.ht[p], c.gloss[p] = grade(col), h, g
    return c


# ---------- a hotel's face: many bays, each its own ----------

BAY_KINDS = (('whole', 7), ('curtain', 6), ('cracked', 2), ('gone', 2), ('boarded', 2), ('shutter', 1), ('cooler', 2))
# A hotel's face picture: eight bays by eight floors, so it repeats only every 2048 units (a 2x2 one read as a pattern
# from the ground in the game, 16 Nov 2026). The looks over these pictures are tile=FRONT_TILE.
FRONT_BAYS, FRONT_SIZE, FRONT_TILE = 8, 1024, 2048


def facade_sheet(wall=tp.CREAM, front=None, bays=4, floors=4, size=1024, seed=420, kind='lanai', under=None):
    """bays x floors rooms of a hotel's face on one picture (each square of it one bay of 256 units, one floor).
    kind 'lanai': the floor slab's edge, a glass door set back in the lanai's shadow, a railing or (with `front`) a
    painted panel; 'window': a plain wall with a window in each bay, sill and lintel. Every bay picks its own state
    (whole glass, curtains, cracked, the glass gone, boarded over, a roller shutter down, a cooler in the window);
    the railings have lost bars and rusted; rain has run down from every slab edge and every sill; the paint peels."""
    S = size
    cellw, cellh = S / float(bays), S / float(floors)
    rnd = random.Random(seed)
    picks = [k for k, n in BAY_KINDS for _ in range(n)]
    if bays * floors <= len(BAY_KINDS):         # (a small sheet: every bay a different one, the first one whole)
        kinds = ['whole'] + rnd.sample([k for k, _n in BAY_KINDS if k != 'whole'], bays * floors - 1)
        rnd.shuffle(kinds)
        state = [kinds[j * bays:(j + 1) * bays] for j in range(floors)]
    else:
        state = [[rnd.choice(picks) for _ in range(bays)] for _ in range(floors)]
    # (each room drawn its own way too: how far its curtains are drawn, where its glass broke, how bright its pane)
    drawn = [[(rnd.uniform(0.08, 0.4), rnd.uniform(0.45, 0.85), rnd.random()) for _ in range(bays)] for _ in range(floors)]
    crack = [[(rnd.uniform(0.25, 0.8), rnd.uniform(0.2, 0.7), rnd.choice((2.5, 3.0, 3.5, 5.0)), rnd.uniform(0, 3)) for _ in range(bays)] for _ in range(floors)]
    pane = [[rnd.uniform(0.85, 1.15) for _ in range(bays)] for _ in range(floors)]
    torn = [[rnd.uniform(0.1, 0.65) for _ in range(bays)] for _ in range(floors)]
    lost_bars = [[{rnd.randrange(20) for _ in range(rnd.randrange(0, 5))} for _ in range(bays)] for _ in range(floors)]
    panel_rust = [[rnd.random() for _ in range(bays)] for _ in range(floors)]
    irons = []
    if kind == 'lanai':
        for j in range(floors):
            for i in range(bays):
                for k in range(0, 20, 3):
                    irons.append((int(i * cellw + (0.08 + 0.84 * k / 19.0) * cellw), int(j * cellh + 0.64 * cellh)))
    ledges = [(j + (0.1 if kind == 'lanai' else 0.8)) / floors for j in range(floors)] + [j / float(floors) for j in range(floors)]
    wr = Wear(S, S, seed, grime=1.0, rain=1.1, ledges=ledges, irons=irons, bleach=0.15)
    peel = Field(S, S, seed + 10, cells=8, octaves=4, fall=0.55)
    glassn = Field(S, S, seed + 11, cells=32, octaves=2)
    c = Picture(S, S, gloss=20)
    top = tp._faded(wall, 0.12)
    old = tp._faded(under or mix(wall, (200, 196, 180), 0.6), 0.2)
    face = tp._faded(front, 0.2) if front is not None else None
    for y in range(S):
        j = int(y / cellh)
        v = (y % cellh) / cellh
        for x in range(S):
            i = int(x / cellw)
            u = (x % cellw) / cellw
            p = y * S + x
            f = wr.fine.v[p]
            st = state[j][i]
            g = 18
            col, h, depth = mul(top, 0.93 + 0.1 * wr.mid.v[p]), 0.5, 0.0
            pv = peel.v[p]
            if pv > 0.7:
                col, h = (mul(old, 0.88), 0.47) if pv < 0.76 else (mul(RENDER, 0.8 + 0.2 * f), 0.42)
            glass_box = (0.1 < u < 0.9 and v > 0.19) if kind == 'lanai' else (0.55 < u < 0.9 and 0.28 < v < 0.68) if kind == 'motel' else (0.22 < u < 0.78 and 0.22 < v < 0.72)
            if kind == 'motel' and 0.1 < u < 0.45 and v > 0.2:       # the room's door: painted, its number, a knob
                du, dv = (u - 0.1) / 0.35, (v - 0.2) / 0.8
                if min(du, 1 - du, dv) < 0.04:
                    col, h, depth = mul(tp.CONCRETE_WHITE, 0.7), 0.58, 0.4
                elif st in ('gone', 'cracked') and du > 0.05:
                    col, h, g, depth = mul((22, 20, 18), 0.8 + 0.4 * f), 0.1, 0, 1.0        # kicked in: the dark room
                    if du < 0.3 and st == 'cracked':
                        col, h = mul(face or tp.TURQUOISE, 0.6), 0.5                      # the door hanging open
                elif st == 'boarded':
                    k = int(du * 3)
                    col, h, g = mul(mix(SILVER_WOOD, (150, 128, 96), (k * 0.41) % 1), 0.75 + 0.3 * wr.runs.v[p]), 0.6, 10
                else:
                    col, h, g = mul(face or tp.TURQUOISE, 0.85 + 0.12 * wr.mid.v[p]), 0.55, 30
                    if pv > 0.62:
                        col, h = mix(PRIMER, mul(SILVER_WOOD, 0.9), f), 0.5
                    if abs(du - 0.5) < 0.08 and abs(dv - 0.12) < 0.04:
                        col, h = mul((150, 126, 76), 0.9), 0.65                          # the number plate
                    if abs(du - 0.85) < 0.04 and abs(dv - 0.55) < 0.025:
                        col, h, g = mul((150, 126, 76), 0.9), 0.7, 90                    # the knob
                    if 0.25 < du < 0.75 and 0.35 < dv < 0.45:
                        col, h = mul(col, 0.85), 0.5                                   # a panel
            if kind == 'lanai':
                if v < 0.1:                                    # the slab's edge
                    col, h = mul(tp.CONCRETE_WHITE, 0.85 + 0.1 * f), 0.85
                    if pv > 0.66:
                        col = mul(RENDER, 0.75 + 0.2 * f)
                elif v < 0.19:
                    col, depth = mul(col, 0.45 + 2.5 * (v - 0.1)), 0.8           # its shadow on the wall
            else:
                if 0.72 <= v < 0.77 and 0.18 < u < 0.82:
                    col, h = mul(tp.CONCRETE_WHITE, 0.85 + 0.1 * f), 0.7         # the sill
                if 0.18 <= v < 0.22 and 0.2 < u < 0.8:
                    col, h, depth = mul(col, 0.8), 0.56, 0.3                     # the lintel
            if glass_box:
                gu = (u - 0.1) / 0.8 if kind == 'lanai' else (u - 0.55) / 0.35 if kind == 'motel' else (u - 0.22) / 0.56
                gv = (v - 0.19) / 0.81 if kind == 'lanai' else (v - 0.28) / 0.4 if kind == 'motel' else (v - 0.22) / 0.5
                frame = min(gu, 1 - gu, gv) < 0.022 or abs(gu - 0.5) < 0.014
                if frame:
                    col, h, g = mul(tp.ALUMINIUM, 0.7 + 0.3 * f), 0.5, 60
                    if st == 'gone' and gv > 0.3 and abs(gu - 0.5) < 0.014:
                        col, h = mul((20, 20, 20), 1.0), 0.2         # the middle bar gone too
                else:
                    glare = 0.8 + 0.55 * max(0.0, 1 - abs((gu - gv * 0.4) - 0.3) * 5)
                    gl = mul(tp.GLASS_DARK, glare * pane[j][i] * (0.85 + 0.3 * glassn.v[p]))
                    gl = mix(gl, (150, 160, 158), 0.3 * (1 - gv) ** 2)      # the sky in it
                    gl = mix(gl, (110, 104, 90), 0.3 * gv ** 2)     # dirt filmed at the foot
                    col, h, g = gl, 0.3, 140
                    lo, hi, one = drawn[j][i]
                    if st == 'curtain' and (gu > hi or (gu < lo and one > 0.3)):
                        fold = 0.75 + 0.25 * math.sin(gu * 90 + one * 6)
                        col, g = mix(gl, mul(mix((196, 176, 140), (170, 168, 150), one), fold * 0.75), 0.6), 60
                    elif st == 'cracked':
                        cu, cv, arms, turn = crack[j][i]
                        a = math.atan2(gv - cv, gu - cu)
                        rr = math.hypot(gu - cu, gv - cv)
                        if rr < 0.45 and abs(math.sin(a * arms + turn + 3 * rr)) < 0.025 / max(rr, 0.06):
                            col = mix(col, (206, 208, 200), 0.5 * (1 - rr / 0.45) + 0.15)
                    elif st == 'gone':
                        col, h, g = mul((18, 18, 17), 0.8 + 0.4 * f), 0.1, 0
                        if gv < 0.06 or (gu < 0.06 and f > 0.45):
                            col, g = mul(tp.GLASS_DARK, 1.3), 140
                        if torn[j][i] < gu < torn[j][i] + 0.2 and gv > 0.15:
                            col = mix(col, (120, 100, 74), 0.6 * (0.5 + 0.5 * math.sin(gu * 70)))     # a torn curtain hanging
                    elif st == 'boarded':
                        k = int(gu * 4)
                        e = gu * 4 - k
                        col = mul(mix(SILVER_WOOD, (150, 128, 96), (k * 0.37) % 1), 0.75 + 0.3 * wr.runs.v[p])
                        h, g = 0.6, 10
                        if e < 0.05 or e > 0.95:
                            col, h = mul(col, 0.4), 0.3
                        if abs(gv - 0.2) < 0.03 or abs(gv - 0.8) < 0.03:
                            col, h = mul((120, 100, 76), 0.9), 0.68        # a batten nailed across
                    elif st == 'shutter':
                        if gv < 0.75:
                            slat = (gv * 40) % 1.0
                            col = mul(mix((132, 136, 128), (112, 116, 108), (i + j) % 2), 0.7 + 0.35 * math.sin(slat * math.pi))
                            h, g = 0.4 + 0.25 * math.sin(slat * math.pi), 40
                            if wr.big.v[p] > 0.6:
                                col, g = mix(col, RUST, 0.5), 8
                    elif st == 'cooler' and 0.55 < gu < 0.95 and 0.5 < gv < 0.8:
                        col, h, g = mul((150, 150, 138), 0.8 + 0.2 * math.sin(gv * 120)), 0.75, 30
                        if gv > 0.76:
                            col = mul(RUST, 0.9)
            if kind == 'motel' and 0.68 <= v < 0.72 and 0.53 < u < 0.92:
                col, h = mul(tp.CONCRETE_WHITE, 0.8), 0.7                        # the window's sill
            if kind == 'lanai':
                if face is not None:
                    if 0.66 < v < 0.97:
                        r = panel_rust[j][i]
                        col, h, g = mul(face, 0.9 + 0.12 * wr.mid.v[p]), 0.68, 30
                        if pv > 0.68 - 0.1 * r:
                            col, h, g = mix(PRIMER, RUST, f), 0.6, 8
                        if wr.big.v[p] * r > 0.45:
                            col = mix(col, RUST_DARK, 0.6)
                    if 0.63 < v <= 0.66:
                        col, h = mul(tp.CONCRETE_WHITE, 0.85), 0.75
                elif v > 0.62:
                    bar = int(u * 20)
                    if 0.62 < v < 0.645:
                        col, h, g = mix(mul((70, 72, 70), 0.9), RUST, 0.5 * f), 0.75, 20      # the rail's top
                    elif (x % max(8, int(cellw) // 20)) < 2 and bar not in lost_bars[j][i] and v < 0.97:
                        col, h, g = mix((64, 66, 64), RUST, 0.3 + 0.5 * wr.mid.v[p]), 0.72, 20
            col = wr.on(x, y, col, depth)
            c.rgb[p], c.ht[p], c.gloss[p] = grade(col), h, g
    return c


def far_sheet(wall=tp.CREAM, front=None, bays=8, floors=8, size=128, seed=440):
    """A whole face as it reads from across the bay, in the same worn colours as the near pictures: rows of windows,
    some dark, some lighter (boarded, curtained), a pale slab edge, streaks down from it."""
    c = Picture(size, size, gloss=20)
    rnd = random.Random(seed)
    big = Field(size, size, seed + 1, cells=3, octaves=3)
    runs = Field(size, size, seed + 2, cells=8, octaves=2, stretch=(3, 0.2))
    tone = [[rnd.choice((0.8, 1.0, 1.0, 1.0, 1.6, 2.2)) for _ in range(bays)] for _ in range(floors)]
    top = tp._faded(wall, 0.12)
    face = tp._faded(front, 0.2) if front is not None else None
    for y in range(size):
        for x in range(size):
            p = y * size + x
            i, j = int(x * bays / size), int(y * floors / size)
            u, v = (x * bays / float(size)) % 1.0, (y * floors / float(size)) % 1.0
            dirt = 0.8 + 0.25 * big.v[p] - 0.2 * smooth(0.5, 0.8, runs.v[p])
            if v < 0.16:
                col = mul(tp.CONCRETE_WHITE, dirt * 0.95)
            elif face is not None and v > 0.64:
                col = mul(face, dirt)
            elif 0.14 < u < 0.86:
                col = mul(tp.GLASS_DARK, tone[j][i] * dirt)
            else:
                col = mul(top, dirt * 0.9)
            c.rgb[p] = grade(col)
    return c


def far_plain(colour, size=32, seed=460):
    """A plain far picture of one colour, worn like the near ones."""
    c = Picture(size, size, gloss=16)
    f = Field(size, size, seed, cells=2, octaves=3)
    for p in range(size * size):
        c.rgb[p] = grade(mul(tp._faded(colour, 0.15), 0.8 + 0.3 * f.v[p]))
    return c


# ---------- signs ----------

def sign_aged(panels, w=512, h=256, seed=480, bulbs=False):
    """`texpaint.sign`'s boards gone the way of every sign on the Strip: the enamel faded and chalky, the letters
    flaking, rust bleeding from the bolts at each corner, grime at the bottom edge; with `bulbs`, a row of marquee
    bulbs round each board, most of them dead or gone."""
    base = tp.sign(panels, w=w, h=h, seed=seed)
    c = Picture(w, h, gloss=40)
    irons = []
    for pnl in panels:
        x0, y0, x1, y1 = pnl['box']
        for bx, by in ((x0 + 0.03, y0 + 0.1), (x1 - 0.03, y0 + 0.1)):
            irons.append((int(bx * w), int(by * h)))
    wr = Wear(w, h, seed, grime=0.8, rain=0.9, irons=irons, bleach=0.3)
    chalk = Field(w, h, seed + 10, cells=6, octaves=4)
    rnd = random.Random(seed)
    for p in range(w * h):
        x, y = p % w, p // w
        col = base.rgb[p]
        col = mix(col, (214, 206, 188), 0.25 * smooth(0.4, 0.8, chalk.v[p]))
        if chalk.v[p] > 0.72:
            col = mix(col, RENDER, 0.7)
        c.rgb[p], c.ht[p] = grade(wr.on(x, y, col)), base.ht[p]
    if bulbs:
        for pnl in panels:
            x0, y0, x1, y1 = (pnl['box'][0] * w, pnl['box'][1] * h, pnl['box'][2] * w, pnl['box'][3] * h)
            inset = max(5.0, (y1 - y0) * 0.06)
            step = max(10.0, (y1 - y0) * 0.11)
            pts = []
            xx = x0 + inset
            while xx < x1 - inset:
                pts += [(xx, y0 + inset), (xx, y1 - inset)]
                xx += step
            for px, py in pts:
                state = rnd.random()
                colour = (250, 228, 170) if state < 0.15 else (110, 100, 84) if state < 0.7 else (24, 22, 20)
                r = max(2.0, step * 0.28)
                for dy in range(-int(r) - 1, int(r) + 2):
                    for dx in range(-int(r) - 1, int(r) + 2):
                        if dx * dx + dy * dy <= r * r:
                            xi, yi = int(px + dx), int(py + dy)
                            if 0 <= xi < w and 0 <= yi < h:
                                q = yi * w + xi
                                c.rgb[q], c.ht[q], c.gloss[q] = grade(colour) if state >= 0.15 else colour, 0.7, 120
    return c


def painted_letters(words, wall=(196, 190, 176), ink=(150, 44, 36), w=1024, h=256, seed=500):
    """Big letters painted straight onto a wall or a tank (a water tower's name, a warehouse's), the wall
    behind them and the letters both faded, the letters gone in patches where the paint failed."""
    base = Picture(w, h, gloss=24)
    wr = Wear(w, h, seed, grime=1.0, rain=1.2, ledges=(0.0,), bleach=0.2)
    fail = Field(w, h, seed + 10, cells=8, octaves=4)
    for p in range(w * h):
        x, y = p % w, p // w
        base.rgb[p] = mul(tp._faded(wall, 0.1), 0.92 + 0.12 * wr.mid.v[p])
        base.ht[p] = 0.5 + 0.04 * wr.fine.v[p]
    high = h * 0.6
    tw = base.text_wide(words, high)
    if tw > w * 0.9:
        high *= w * 0.9 / tw
        tw = base.text_wide(words, high)
    base.text(words, (w - tw) / 2, (h - high) / 2, high, tp._faded(ink, 0.15), thick=high / 5.0,
              worn=lambda x, y: 0.0 if fail.at(int(x), int(y)) > 0.86 else 1.0)
    for p in range(w * h):
        x, y = p % w, p // w
        base.rgb[p] = grade(wr.on(x, y, base.rgb[p]))
    return base


# ---------- things the war left ----------

def pool_murky(size=256, seed=520):
    """A hotel pool two hundred years without a pump: green-brown water, a scum of algae drifting in rafts, leaves
    and rubbish floating, a little of the light still dancing where it is clear."""
    c = Picture(size, size, gloss=110)
    a, b = Field(size, size, seed, cells=6, octaves=2), Field(size, size, seed + 1, cells=6, octaves=2)
    scum = Field(size, size, seed + 2, cells=4, octaves=5, fall=0.6)
    bits = Cells(size, size, seed + 3, n=20, jitter=1.0)
    for p in range(size * size):
        r = abs(a.v[p] - b.v[p])
        lit = max(0.0, 1 - r * 10) ** 2
        col = mix((40, 62, 44), (66, 86, 52), a.v[p])
        col = (col[0] + 40 * lit, col[1] + 46 * lit, col[2] + 30 * lit)
        h, g = 0.5, 110
        sv = scum.v[p]
        if sv > 0.6:
            col, h, g = mix(col, (96, 112, 56), min(1.0, (sv - 0.6) * 5)), 0.55, 20
        if bits.d1[p] < 0.09 and bits.id[p] % 4 == 0:
            col, h, g = ((112, 86, 48), (150, 140, 112), (70, 90, 40))[bits.id[p] % 3], 0.62, 10
        c.rgb[p], c.ht[p], c.gloss[p] = grade(col, sat=0.8), h, g
    return c


def shelter_sign(size=256, seed=540):
    """The yellow and black fallout-shelter sign of the time (three triangles in a ring), FALLOUT SHELTER under it,
    the enamel chipped to rusty steel, bolt holes rusting at the corners."""
    c = Picture(size, size, gloss=60)
    wr = Wear(size, size, seed, grime=0.6, rain=0.8, irons=[(12, 12), (size - 13, 12)], bleach=0.25)
    chip = Field(size, size, seed + 10, cells=8, octaves=4)
    yellow, black = (226, 184, 48), (28, 26, 24)
    cx, cy, R = size / 2.0, size * 0.4, size * 0.3
    for p in range(size * size):
        x, y = p % size, p // size
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        a = (math.degrees(math.atan2(dy, dx)) + 90) % 120          # (three triangles, one pointing down)
        col = yellow
        if r < R:
            col = black
            if R * 0.18 < r < R * 0.9 and abs(a - 60) < 30 * (1 - 0.15 * (r / R)):
                col = yellow
        if y > size * 0.76 or min(x, y, size - 1 - x) < 4:
            col = black if 4 <= min(x, size - 1 - x) and y > size * 0.76 and y < size - 4 else col
        if chip.v[p] > 0.8:
            col = mix(RUST, RUST_DARK, wr.fine.v[p])
        c.rgb[p], c.ht[p] = col, 0.5 - (0.06 if chip.v[p] > 0.8 else 0)
    words = 'FALLOUT SHELTER'
    high = size * 0.11
    high = min(high, high * size * 0.88 / c.text_wide(words, high))
    c.text(words, (size - c.text_wide(words, high)) / 2, size * 0.8, high, yellow, worn=lambda x, y: 0.0 if chip.at(int(x), int(y)) > 0.75 else 1.0)
    for p in range(size * size):
        c.rgb[p] = grade(wr.on(p % size, p // size, c.rgb[p]), sat=0.8)
    return c


# ---------- the drop-in for what's there ----------

def UPGRADE():
    """{texture name: painter} for the hotels' and the shore's textures, each a worn picture of the same purpose and
    layout (one bay and one floor to a square where the old one was, so the models need no change). Called, not a
    dict, so nothing is drawn until asked."""
    # (eight bays by eight floors to a picture, each room its own: the looks over these tile every FRONT_TILE, as resortset's do)
    lanai = lambda front, seed: (lambda: facade_sheet(front=front, bays=FRONT_BAYS, floors=FRONT_BAYS, size=FRONT_SIZE, seed=seed))
    return {
        'concrete': lambda: concrete(size=256, seed=14, boards=4),
        'metal_white': lambda: steel(tp.WHITE, size=128, seed=15),
        'planks_cream': lambda: wood(tp.CREAM, seed=12, count=8),
        'planks_coral': lambda: wood(tp.CORAL, seed=13, count=8),
        'planks_turquoise': lambda: wood(tp.TURQUOISE, seed=11, count=8),
        'hotel/lanai': lanai(None, 60),
        'hotel/lanai_turquoise': lanai(tp.TURQUOISE, 70),
        'hotel/lanai_coral': lanai(tp.CORAL, 71),
        'hotel/stucco_pink': lambda: render(tp.PINK, size=256, seed=62),
        'hotel/stucco_white': lambda: render(tp.CONCRETE_WHITE, size=256, seed=72),
        'hotel/blocks': lambda: breeze_blocks(size=128, seed=61),
        'hotel/lava': lambda: lava(size=256, seed=64),
        'hotel/shopfront': lambda: glass_curtain(size=256, seed=65, panes=(4, 1)),
        'hotel/far_cream': lambda: far_sheet(size=64, seed=66),
        'hotel/far_turquoise': lambda: far_sheet(front=tp.TURQUOISE, size=64, seed=67),
        'hotel/far_coral': lambda: far_sheet(front=tp.CORAL, size=64, seed=68),
        'hotel/far_pink': lambda: far_sheet(wall=tp.PINK, size=64, seed=69),
        'hotel/far_plain_pink': lambda: far_plain(tp.PINK, seed=74),
        'hotel/far_plain_white': lambda: far_plain(tp.CONCRETE_WHITE, seed=75),
        'hotel/far_plain_lava': lambda: far_plain(tp.LAVA, seed=76),
        'hotel/far_plain_glass': lambda: far_plain((40, 62, 64), seed=77),
        'hotel/far_plain_coral': lambda: far_plain(tp.CORAL, seed=78),
        'coast/hull': lambda: hull_rust(size=256, seed=145),
        'coast/rust_white': lambda: steel(tp.WHITE, size=256, seed=146, rust=0.75, flake=0.6),
        'coast/red': lambda: steel(tp.RED, size=128, seed=147, rust=0.3),
        'coast/wet_concrete': lambda: concrete((126, 122, 108), size=256, seed=148, boards=0, spalls=0.4),
    }
