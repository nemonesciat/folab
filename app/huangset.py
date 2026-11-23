"""The Huáng's insides (set 'huang' of modelsets): their halls' doors, the rooms behind them and what stands in them,
FOLab's own, so a mod with them can be handed round. The outsides are settlerset's halls; huanginside.py puts these in.

Kept, not weathered (the user, 22 Nov 2026: "as if proud people live here"): red lacquer that still shines, plaster
whitewashed, floorboards oiled, lattice windows over paper with the day coming through. Every picture here is clean
(`lacquer`, `boards`, `whitewash`, `paper_lattice`...), unlike texwear's, which are two hundred years in the sun.

    huang_door        their door: two red leaves studded in gold in a red casing, hung flat on the hall's plaster
                      (doorset.unit, flush); the same door, turned, is the way out inside
    huang_home        a family's house inside: the living room across the front, the sleeping room and the kitchen
                      behind it through two doorways
    huang_elders      the elders' hall inside: an audience room with two rows of red columns and a dais, the elders'
                      rooms behind it, a study between them
    huang_granary     the storehouse inside: one long room for the harvest

A room's frame: its floor at z 0, the front wall's inner face along y 0 (the door's back against it), the rooms in +y,
x across; `ROOMS` says where each room is in it (huanginside furnishes by them). Furniture stands on z 0 with its front
to -y, but for what is sat or lain on, which takes the frame of the game's furniture it copies (`SEATS`): its markers,
copied from that model, say where someone sits or lies, so the game's own animations fit."""
import math

import doorset  # noqa: F401  (its pictures: the door unit's trim)
import modelsets
import texpaint as tp
from modelsets import look

SET = 'huang'

RED = (150, 32, 26)
RED_DARK = (104, 24, 20)
GOLD = (198, 156, 62)
PLASTER = (232, 226, 210)
WOOD = (150, 98, 58)            # (floorboards: oiled fir)
ROSEWOOD = (82, 40, 28)
TEAL = (44, 102, 96)
PAPER = (240, 226, 190)
INDIGO = (40, 52, 104)
BRICK = (150, 82, 60)

T = 20.0                        # walls' thickness
H = 330.0                       # rooms' height to the ceiling
DOOR_W, DOOR_H = 180.0, 230.0   # (the halls' painted door, now a real one: settlerset.hall)
WAY_W, WAY_H = 120.0, 220.0     # doorways between rooms


# ---------- the pictures: clean ----------

def _figure(fine, wave, x, y, size, stretch=3.0):
    """Wood's figure: rings drawn out along y, bent by a slow wave, so the grain flows and gathers round knots."""
    w = wave.at(x * 3.0 / size, y * 1.5 / size)
    jitter = fine.at(x * 16.0 / size, y * 2.0 / size)
    phase = x / size * math.tau * 22.0 + 5.0 * w + 1.4 * jitter
    return 0.5 + 0.5 * math.sin(phase) * (0.7 + 0.3 * math.sin(phase * 0.37 + 2.0 * w))


def lacquer(colour=RED, size=256, seed=900, grain=0.06):
    """Lacquer kept up: deep coats over figured wood, the grain ghosting through where the coat is thinnest, the fine
    craze old lacquer gets however it is cared for, a polished sheen in soft bands, now and then a speck of dust."""
    c = tp.Canvas(size, size)
    n, fine, wave = tp.Noise(seed, 4), tp.Noise(seed + 1, 64), tp.Noise(seed + 2, 4)
    craze = tp.Noise(seed + 3, 48)

    def fn(x, y):
        ring = _figure(fine, wave, x, y, size)
        b = n.at(x * 4.0 / size, y * 4.0 / size)
        f = 0.86 + grain * 2.2 * (ring - 0.5) + 0.1 * b
        f += 0.05 * math.sin((x + y * 0.3) / size * math.tau * 2 + 3 * b)       # (the sheen, polished in strokes)
        k = craze.at(x * 48.0 / size, y * 48.0 / size)
        if abs(k - 0.5) < 0.012:
            f *= 0.86
        if (x * 7919 + y * 104729 + seed) % 2111 == 0:
            f *= 1.25
        return tuple(max(0, min(255, int(v * f))) for v in colour), 0.52 + 0.05 * ring
    c.paint(fn)
    return c


def boards(colour=WOOD, size=512, seed=910, count=6):
    """Oiled floorboards: boards of different lengths butted end to end, each its own shade, the figure of the wood
    with a knot here and there, two pegs at each board's end, the joints dark."""
    import random
    rng = random.Random(seed)
    c = tp.Canvas(size, size)
    fine, wave, dirt = tp.Noise(seed, 64), tp.Noise(seed + 1, 4), tp.Noise(seed + 2, 8)
    wide = size / float(count)
    cuts = [sorted(rng.uniform(0, size) for _ in range(rng.choice((1, 2)))) for _ in range(count)]
    tint = {}

    def piece(k, y):
        j = sum(1 for cy in cuts[k] if y >= cy)
        if (k, j) not in tint:
            tint[(k, j)] = (rng.uniform(0.84, 1.1), rng.uniform(-0.05, 0.05), rng.uniform(0, 300))
        return j, tint[(k, j)]
    knots = [(rng.uniform(0, size), rng.uniform(0, size), rng.uniform(3, 7)) for _ in range(5)]

    def fn(x, y):
        k = int(x / wide)
        e = min(x - k * wide, (k + 1) * wide - x)
        j, (t, hue, off) = piece(k, y)
        ring = _figure(fine, wave, x + off, y, size, stretch=2.2)
        f = t * (0.78 + 0.26 * ring) * (0.95 + 0.08 * dirt.at(x * 8.0 / size, y * 8.0 / size))
        for kx, ky, kr in knots:
            d = math.hypot(x - kx, (y - ky) * 0.6)
            if d < kr * 2.5:
                f *= 0.7 + 0.3 * min(1.0, d / (kr * 2.5)) + 0.1 * math.sin(d * 1.4)
        col = (colour[0] * (1 + hue), colour[1], colour[2] * (1 - hue))
        if e < 1.4 or any(abs(y - cy) < 1.0 for cy in cuts[k]):
            return tuple(int(v * 0.3) for v in colour), 0.2
        for cy in cuts[k] + [0.0]:
            for px in (k * wide + wide * 0.3, k * wide + wide * 0.7):
                for side in (-7, 7):
                    if math.hypot(x - px, y - ((cy + side) % size)) < 2.6:
                        return tuple(int(v * 0.6) for v in colour), 0.45
        return tuple(max(0, min(255, int(v * f))) for v in col), 0.5 + 0.06 * ring
    c.paint(fn)
    return c


def whitewash(colour=PLASTER, size=256, seed=920):
    """Plaster freshly whitewashed: the trowel's sweeps under the wash, the wash's brush marks across them, a faint
    warmth where the coats lie thicker."""
    c = tp.Canvas(size, size)
    n, fine, sweep = tp.Noise(seed, 6), tp.Noise(seed + 1, 48), tp.Noise(seed + 2, 10)

    def fn(x, y):
        s = sweep.at(x * 10.0 / size, y * 10.0 / size)
        trowel = 0.5 + 0.5 * math.sin((x * 0.7 + y) / size * math.tau * 5 + s * 6)
        f = 0.93 + 0.05 * n.at(x * 6.0 / size, y * 6.0 / size) + 0.035 * fine.at(x * 48.0 / size, y * 10.0 / size) + 0.025 * trowel
        warm = 0.03 * n.at(x * 3.0 / size + 5, y * 3.0 / size)
        col = (colour[0] * (1 + warm), colour[1], colour[2] * (1 - warm))
        return tuple(max(0, min(255, int(v * f))) for v in col), 0.48 + 0.06 * trowel
    c.paint(fn)
    return c


def paper_lattice(size=256, cells=6, seed=930):
    """A window from inside: red lattice over paper with daylight behind it, brightest in the middle."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 32)
    bar = size / float(cells)
    frame = size * 0.07
    mid = (size - 1) / 2.0

    def fn(x, y):
        edge = min(x, y, size - 1 - x, size - 1 - y) < frame
        gx, gy = (x % bar) / bar, (y % bar) / bar
        on = edge or gx < 0.12 or gy < 0.12 or abs(gx - gy) < 0.05 or abs(gx + gy - 1) < 0.05
        if on:
            f = 0.9 + 0.1 * fine.at(x * 32.0 / size, y * 32.0 / size)
            return tuple(int(v * f) for v in RED), 0.8 if edge else 0.7
        light = 1.0 - 0.18 * min(1.0, math.hypot(x - mid, y - mid) / mid)
        return tuple(min(255, int(v * light)) for v in PAPER), 0.35
    c.paint(fn)
    return c


def leaf(seed=940, w=128, h=256):
    """One leaf of their door: red lacquer in a raised frame, rows of gold studs, a gold ring knocker on a boss."""
    c = tp.Canvas(w, h)
    fine = tp.Noise(seed, 32)

    def fn(x, y):
        u, v = x / float(w), y / float(h)
        f = 0.92 + 0.08 * fine.at(x * 32.0 / w * 0.3, y * 32.0 / h * 3)
        col, ht = tuple(int(c_ * f) for c_ in RED), 0.5
        if min(u, 1 - u) < 0.07 or min(v, 1 - v) < 0.04:
            col, ht = tuple(int(c_ * f) for c_ in RED_DARK), 0.65
        for r in range(7):                              # (seven rows of five studs)
            for k in range(5):
                sx, sy = 0.18 + k * 0.16, 0.1 + r * 0.13
                d = math.hypot((u - sx) * w, (v - sy) * h)
                if d < 4.5:
                    col, ht = tuple(min(255, int(c_ * (1.15 - d / 12.0))) for c_ in GOLD), 0.85
        d = math.hypot((u - 0.86) * w, (v - 0.5) * h)
        if 9 < d < 13 or d < 5:                          # (the knocker on the meeting edge)
            col, ht = GOLD, 0.8
        return col, ht
    c.paint(fn)
    return c


def silk(colour=INDIGO, motif=GOLD, size=256, seed=950, every=64):
    """A quilt's silk damask: cloud scrolls woven in a sheen of the ground's own colour, a gold roundel of a flower
    between them, the weave's fine twill and the light across the folds."""
    c = tp.Canvas(size, size)
    fine, fold = tp.Noise(seed, 32), tp.Noise(seed + 1, 4)

    def fn(x, y):
        twill = 0.03 * (((x + y) // 2) % 2)
        f = 0.84 + 0.1 * fine.at(x * 32.0 / size, y * 32.0 / size) + twill + 0.1 * (fold.at(x * 4.0 / size, y * 4.0 / size) - 0.5)
        half = every / 2.0
        row = int(y // every)
        ox = (x + (half if row % 2 else 0)) % every - half
        oy = y % every - half
        d = math.hypot(ox, oy)
        a = math.atan2(oy, ox)
        if d < half * 0.42:                                     # (the roundel: a flower of five petals in gold)
            petal = 0.55 + 0.45 * math.cos(5 * a)
            if d < half * 0.12 or (d < half * 0.36 * petal and d > half * 0.14):
                return tuple(int(v * f) for v in motif), 0.6
            if d > half * 0.36:
                return tuple(int(v * f) for v in motif), 0.58
            return tuple(int(v * f * 0.92) for v in colour), 0.5
        # (cloud scrolls between: a sheen in the ground's colour where a spiral's arm runs)
        cx, cy = (x % half) - half / 2.0, (y % half) - half / 2.0
        r = math.hypot(cx, cy)
        arm = math.sin(math.atan2(cy, cx) * 1.0 + r * 0.45)
        if abs(arm) < 0.22 and r < half * 0.46:
            return tuple(min(255, int(v * f * 1.22)) for v in colour), 0.56
        return tuple(int(v * f) for v in colour), 0.5
    c.paint(fn)
    return c


def rug(size=512, seed=960):
    """A wool rug: a red field strewn with small blue and cream flowers, a medallion of rings and petals in its middle,
    corner pieces, a deep indigo border with a key-fret and a cream guard stripe each side, the pile's nap."""
    c = tp.Canvas(size, size)
    fine, nap = tp.Noise(seed, 64), tp.Noise(seed + 1, 128)
    mid = (size - 1) / 2.0
    CREAM, FIELD = (220, 198, 140), (158, 38, 30)

    def fret(u, v):                                             # (a key-fret along the border, in its own little squares)
        cu, cv = u % 1.0, v
        on = cv < 0.14 or cv > 0.86
        on = on or (0.14 <= cv <= 0.72 and 0.0 <= cu < 0.14)
        on = on or (0.58 <= cv <= 0.72 and cu < 0.72)
        on = on or (0.28 <= cv <= 0.72 and 0.58 <= cu < 0.72)
        on = on or (0.28 <= cv <= 0.42 and 0.3 <= cu < 0.72)
        return on

    def fn(x, y):
        f = 0.82 + 0.12 * fine.at(x * 64.0 / size, y * 64.0 / size) + 0.08 * nap.at(x * 128.0 / size, y * 128.0 / size)
        e = min(x, y, size - 1 - x, size - 1 - y) / float(size)
        along = (x if min(y, size - 1 - y) < min(x, size - 1 - x) else y) / float(size)
        if e < 0.015:
            col = CREAM                                         # (the bound edge)
        elif e < 0.03:
            col = INDIGO
        elif e < 0.04:
            col = CREAM
        elif e < 0.12:
            col = CREAM if fret(along * 22.0, (e - 0.04) / 0.08) else INDIGO
        elif e < 0.13:
            col = CREAM
        else:
            col = FIELD
            # corner pieces: a quarter medallion in each corner of the field
            for cx, cy in ((0, 0), (size, 0), (0, size), (size, size)):
                dc = math.hypot(x - cx, y - cy) / size
                if dc < 0.3:
                    col = INDIGO if dc > 0.27 else (CREAM if 0.24 < dc < 0.255 else col)
            # small flowers strewn on the field
            g = size / 10.0
            fx, fy = (x % g) - g / 2, (y % g) - g / 2
            if (int(x // g) + int(y // g)) % 2 == 0:
                d = math.hypot(fx, fy)
                pet = 0.6 + 0.4 * math.cos(4 * math.atan2(fy, fx))
                if d < g * 0.08:
                    col = CREAM
                elif d < g * 0.22 * pet:
                    col = INDIGO if (int(x // g) // 2) % 2 else CREAM
        d = math.hypot(x - mid, y - mid) / mid
        if d < 0.34:                                            # (the medallion: rings and an eight-petalled flower)
            a = math.atan2(y - mid, x - mid)
            pet = 0.6 + 0.4 * abs(math.cos(4 * a))
            if d > 0.3:
                col = INDIGO
            elif d > 0.27:
                col = CREAM
            elif d > 0.24:
                col = INDIGO
            elif d < 0.05:
                col = CREAM
            elif d < 0.22 * pet:
                col = CREAM if d > 0.16 * pet else INDIGO
            else:
                col = FIELD
        return tuple(max(0, min(255, int(v * f))) for v in col), 0.45 + 0.08 * nap.at(x * 128.0 / size, y * 128.0 / size)
    c.paint(fn)
    return c


def scroll(size=512, seed=970):
    """A hanging scroll: a landscape in ink, mountains rising out of mist in washes darker nearer, pines on a near
    ridge, a little boat on the water at the foot; a column of writing down one side and a red seal; the silk aged to
    cream inside a mount of green brocade."""
    w, h = size // 2, size
    c = tp.Canvas(w, h)
    n, fine, mist = tp.Noise(seed, 8), tp.Noise(seed + 1, 64), tp.Noise(seed + 2, 6)
    INK = (40, 40, 38)

    def fn(x, y):
        u, v = x / float(w), y / float(h)
        if min(u, 1 - u) < 0.07 or v < 0.09 or v > 0.91:
            k = 0.9 + 0.12 * (((x // 3) + (y // 3)) % 2) * fine.at(x * 64.0 / w, y * 64.0 / h)
            return tuple(int(c_ * k) for c_ in (86, 110, 94)), 0.5           # (the brocade mount)
        if min(u, 1 - u) < 0.08 or v < 0.1 or v > 0.9:
            return (170, 150, 96), 0.5                                       # (a gold thread round the painting)
        f = 0.94 + 0.06 * fine.at(x * 64.0 / w, y * 64.0 / h)
        col = tuple(c_ * f for c_ in (228, 216, 184))
        ink = 0.0
        # three ranges, each a wash fading downward into mist; nearer is darker
        for k, (base, amp, dark, freq) in enumerate(((0.36, 0.14, 0.32, 5.0), (0.52, 0.16, 0.55, 7.0), (0.68, 0.12, 0.8, 9.0))):
            top = base - amp * (0.5 + 0.5 * math.sin(u * freq + k * 1.7)) - 0.07 * n.at(u * 8 + k * 3, k * 2.0)
            if v > top:
                depth = min(1.0, (v - top) / 0.12)
                fade = 1.0 - 0.75 * mist.at(u * 6.0, v * 6.0 + k) * min(1.0, (v - top) / 0.25)
                ink = max(ink, dark * (0.55 + 0.45 * (1 - depth)) * fade)
        # pines on the nearest ridge: tiers of dark strokes
        for px in (0.3, 0.38, 0.62):
            dx = abs(u - px)
            if 0.6 < v < 0.76 and dx < 0.012:
                ink = max(ink, 0.85)
            for t in range(4):
                ty = 0.6 + t * 0.035
                if ty < v < ty + 0.02 and dx < 0.02 + 0.012 * t - (v - ty) * 0.8:
                    ink = max(ink, 0.9)
        # water and a boat
        if v > 0.8:
            ink = max(ink * 0.3, 0.08 * (0.5 + 0.5 * math.sin(v * 220)))
            if abs(v - 0.84) < 0.006 and 0.5 < u < 0.62:
                ink = 0.85
            if abs(u - 0.58) < 0.004 and 0.8 < v < 0.84:
                ink = 0.8
        # a column of writing down the right, the seal under it
        if 0.8 < u < 0.86 and 0.14 < v < 0.5:
            cy = (v - 0.14) / 0.04
            if (cy % 1.0) < 0.75:
                gx, gy = (u - 0.8) / 0.06, cy % 1.0 / 0.75
                stroke = abs(gy - 0.3) < 0.08 or abs(gx - 0.5) < 0.1 or abs(gy - 0.75) < 0.07 or abs(gx - gy) < 0.08
                if stroke and int(cy * 7 + gx * 3) % 3 != 0:
                    ink = 0.85
        if 0.79 < u < 0.87 and 0.52 < v < 0.56:
            return (172, 40, 30), 0.45
        col = tuple(int(c_ * (1 - ink) + i * ink) for c_, i in zip(col, INK))
        return col, 0.45
    c.paint(fn)
    return c


def bricks(colour=BRICK, size=256, seed=980, rows=8):
    """A stove's bricks, clean-pointed: each brick its own fired shade, darker at its ends, the pointing pale."""
    c = tp.Canvas(size, size)
    fine, spot = tp.Noise(seed, 32), tp.Noise(seed + 1, 96)
    bh = size / float(rows)
    bw = bh * 2

    def fn(x, y):
        r = int(y / bh)
        sx = x + (bw / 2 if r % 2 else 0)
        ox = sx % bw
        oy = y % bh
        if ox < 2.5 or oy < 2.5:
            return (206, 198, 182), 0.3
        b = ((r * 31 + int(sx / bw) * 17) % 7) / 7.0
        end = min(ox, bw - ox) / bw
        f = 0.78 + 0.16 * fine.at(x * 32.0 / size, y * 32.0 / size) + 0.14 * b + 0.06 * min(1.0, end * 6)
        if spot.at(x * 96.0 / size, y * 96.0 / size) > 0.82:
            f *= 0.85
        return tuple(max(0, min(255, int(v * f))) for v in colour), 0.55
    c.paint(fn)
    return c


def cabinet_front(seed=990, w=256, h=512):
    """A tall cabinet's two doors: each a frame round two carved panels (a sunk field with a bevelled rim and a
    flower carved in it), red lacquer, the gold of the round lock plate across the meeting stiles, hinges of brass."""
    c = tp.Canvas(w, h)
    fine, wave = tp.Noise(seed, 64), tp.Noise(seed + 1, 4)

    def fn(x, y):
        u, v = x / float(w), y / float(h)
        ring = _figure(fine, wave, x, y, w)
        f = 0.88 + 0.08 * (ring - 0.5)
        col, ht = tuple(int(c_ * f) for c_ in RED), 0.55
        side = 0 if u < 0.5 else 1
        lu = (u - 0.5 * side) / 0.5
        frame = min(lu, 1 - lu) < 0.12 or v < 0.05 or v > 0.95 or abs(v - 0.52) < 0.03
        if frame:
            col, ht = tuple(int(c_ * f * 0.85) for c_ in RED), 0.62
        else:
            # the panel: a bevel round a sunk field, a flower in the field's middle
            top, bot = (0.05, 0.49) if v < 0.52 else (0.55, 0.95)
            pv = (v - top) / (bot - top)
            pu = (lu - 0.12) / 0.76
            e = min(pu, 1 - pu, pv * 2.2, (1 - pv) * 2.2)
            if e < 0.07:
                col, ht = tuple(int(c_ * f * (0.7 + 3 * e)) for c_ in RED), 0.5 + e
            else:
                d = math.hypot((pu - 0.5) * 0.76 * w * 0.5, (pv - 0.5) * (bot - top) * h)
                a = math.atan2((pv - 0.5) * (bot - top) * h, (pu - 0.5) * 0.76 * w * 0.5)
                petal = 0.6 + 0.4 * math.cos(6 * a)
                if d < 26 * petal and d > 6:
                    col, ht = tuple(int(c_ * f * (0.78 + 0.25 * math.cos(6 * a))) for c_ in RED), 0.62
                elif d <= 6:
                    col, ht = GOLD, 0.7
        if abs(u - 0.5) < 0.01:
            col, ht = (40, 14, 12), 0.2                              # (the doors' meeting line)
        d = math.hypot((u - 0.5) * w, (v - 0.5) * h)
        if d < 26:
            col, ht = (GOLD if d > 4 else (60, 46, 20)), 0.8          # (the lock plate and its keyhole)
            if abs((v - 0.5) * h) < 3 and d > 10:
                col = (150, 116, 44)
        for hv in (0.15, 0.85):
            if (min(u, 1 - u) < 0.035) and abs(v - hv) < 0.03:
                col, ht = (176, 140, 60), 0.75                       # (the hinges)
        return col, ht
    c.paint(fn)
    return c


modelsets.TEXTURES.update({
    'huang/red': lambda: lacquer(size=512),
    'huang/red_dark': lambda: lacquer(RED_DARK, seed=901),
    'huang/teal': lambda: lacquer(TEAL, seed=902),
    'huang/rosewood': lambda: lacquer(ROSEWOOD, size=512, seed=903, grain=0.2),
    'huang/gold': lambda: tp.painted_metal(GOLD, seed=904, rust=0.0),
    'huang/bronze': lambda: tp.painted_metal((128, 96, 58), seed=905, rust=0.02),
    'huang/iron': lambda: tp.painted_metal((44, 42, 40), seed=906, rust=0.02),
    'huang/boards': lambda: boards(),
    'huang/ceiling': lambda: boards((128, 84, 50), size=256, seed=911, count=4),
    'huang/plaster': lambda: whitewash(),
    'huang/window': lambda: paper_lattice(),
    'huang/leaf': lambda: leaf(),
    'huang/quilt': lambda: silk(),
    'huang/quilt_red': lambda: silk((150, 36, 30), (214, 180, 96), seed=951),
    'huang/quilt_green': lambda: silk((48, 96, 70), (226, 210, 160), seed=952),
    'huang/linen': lambda: lacquer((228, 220, 198), seed=953, grain=0.02),
    'huang/rug': lambda: rug(),
    'huang/scroll': lambda: scroll(),
    'huang/bricks': lambda: bricks(),
    'huang/cabinet': lambda: cabinet_front(),
    'huang/stone': lambda: whitewash((150, 146, 136), seed=921),
    'huang/sack': lambda: lacquer((196, 174, 128), seed=954, grain=0.2),
    'huang/wicker': lambda: tp.wicker(colour=(176, 140, 84), seed=955),
    'huang/glaze': lambda: lacquer((52, 84, 76), seed=956, grain=0.03),
    'huang/glaze_blue': lambda: silk((228, 230, 232), (40, 64, 140), seed=957, every=24),
    'huang/lantern': lambda: tp.lit_glass((236, 72, 48), seed=958),
    'huang/maize': lambda: lacquer((226, 178, 60), seed=959, grain=0.25),
    'huang/rice': lambda: whitewash((236, 230, 214), seed=922),
})


def _looks():
    return {'red': look('huang/red', tile=128, turned=True), 'red_dark': look('huang/red_dark', tile=96, turned=True),
            'teal': look('huang/teal', tile=96, turned=True), 'wood': look('huang/rosewood', tile=128, turned=True),
            'gold': look('huang/gold', tile=48), 'bronze': look('huang/bronze', tile=48), 'iron': look('huang/iron', tile=48),
            'floor': look('huang/boards', tile=200), 'ceiling': look('huang/ceiling', tile=160), 'plaster': look('huang/plaster', tile=256),
            'window': look('huang/window'), 'quilt': look('huang/quilt', tile=96), 'quilt_red': look('huang/quilt_red', tile=96),
            'quilt_green': look('huang/quilt_green', tile=96), 'linen': look('huang/linen', tile=96), 'rug': look('huang/rug'),
            'scroll': look('huang/scroll'), 'bricks': look('huang/bricks', tile=96), 'cabinet': look('huang/cabinet'),
            'stone': look('huang/stone', tile=128), 'sack': look('huang/sack', tile=64), 'wicker': look('huang/wicker', tile=40),
            'glaze': look('huang/glaze', tile=64), 'porcelain': look('huang/glaze_blue', tile=48), 'lantern': look('huang/lantern'),
            'maize': look('huang/maize', tile=32), 'rice': look('huang/rice', tile=64)}


NONE = {f: None for f in ('front', 'back', 'left', 'right', 'top', 'bottom')}


def _box(P, size, at, lk, solid=False, turn=None, **faces):
    p = {'shape': 'box', 'size': [round(float(v), 2) for v in size], 'at': [round(float(v), 2) for v in at], 'look': lk, 'solid': solid,
         'material': 'stone' if lk in ('plaster', 'stone', 'bricks') else 'wood'}
    if turn:
        p['turn'] = [round(float(v), 3) for v in turn]
    if faces:
        p['faces'] = faces
    P.append(p)
    return p


def _hit(P, size, at, material='wood'):
    """Collision only: a box nothing draws."""
    P.append({'shape': 'box', 'size': [round(float(v), 2) for v in size], 'at': [round(float(v), 2) for v in at], 'look': None,
              'solid': True, 'material': material, 'faces': dict(NONE)})


def _cyl(P, r, h, at, lk, sides=12, r2=None, solid=False, turn=None):
    p = {'shape': 'cylinder', 'r': r, 'h': h, 'sides': sides, 'at': [round(float(v), 2) for v in at], 'look': lk, 'solid': solid, 'material': 'wood'}
    if r2 is not None:
        p['r2'] = r2
    if turn:
        p['turn'] = turn
    P.append(p)
    return p


def _desc(name, P, **more):
    d = {'name': name, 'looks': _looks(), 'parts': P}
    d.update(more)
    return d


# ---------- the door ----------

modelsets.TEXTURES['huang/trim'] = lambda: lacquer(RED_DARK, seed=907)


def door():
    """Their door, as doorset makes its flush doors: hung on the wall, -y out of the building, origin at its foot."""
    d = doorset.unit('FOLabHuangDoor', DOOR_W, DOOR_H, 'huang/leaf', 'huang/trim', leaves=2, flush=True, casing=16)
    d['looks']['trim'] = look('huang/trim', tile=96, turned=True)
    return d


# ---------- the rooms ----------

def _run(P, along, x0, x1, at, ways, z1=H, dado=True, look_='plaster'):
    """A wall T thick from x0 to x1 along the axis `along` ('x' or 'y'), its middle at `at` on the other axis, cut by
    doorways [(from, to)] WAY_H high with a lintel over each, framed in red."""
    def box(p0, p1, z0, z1_, lk, solid=True, thick=T):
        lng = p1 - p0
        mid = (p0 + p1) / 2.0
        if along == 'x':
            return _box(P, [lng, thick, z1_ - z0], [mid, at, z0], lk, solid=solid)
        return _box(P, [thick, lng, z1_ - z0], [at, mid, z0], lk, solid=solid)
    cuts = sorted(ways)
    p = x0
    for w0, w1 in cuts + [(x1, x1)]:
        if w0 > p:
            box(p, w0, 0.0, z1, look_)
            if dado:
                box(p, w0, 0.0, 86.0, 'wood', solid=False, thick=T + 4)      # (a wooden dado either side)
                box(p, w0, 86.0, 92.0, 'red', solid=False, thick=T + 6)
        if w1 > w0:
            box(w0, w1, WAY_H, z1, look_)                                    # (the lintel)
            box(w0 - 8, w1 + 8, WAY_H - 4, WAY_H + 14, 'red', solid=False, thick=T + 8)
            for e in (w0, w1):                                               # (the frame's posts)
                box(e - 8, e + 8, 0.0, WAY_H, 'red', solid=False, thick=T + 8)
        p = max(p, w1)


def _post(P, x, y, h=H):
    _box(P, [36, 36, 14], [x, y, 0], 'stone')
    _cyl(P, 15, h - 14, [x, y, 14], 'red', sides=12, solid=True)


def _window(P, x, y, w=140.0, h=150.0, z=100.0, along='x', side=1):
    """A lattice window on a wall's inner face (at x, y: the face; side: which way the room is), framed in red."""
    if along == 'x':
        _box(P, [w, 3, h], [x, y + side * 1.5, z], 'window', front='window', back='window')
        for sx in (-1, 1):
            _box(P, [10, 8, h + 20], [x + sx * (w / 2 + 5), y + side * 4, z - 10], 'red')
        for zz in (z - 14, z + h):
            _box(P, [w + 20, 10, 14], [x, y + side * 5, zz], 'red')
    else:
        _box(P, [3, w, h], [x + side * 1.5, y, z], 'window', left='window', right='window')
        for sy in (-1, 1):
            _box(P, [8, 10, h + 20], [x + side * 4, y + sy * (w / 2 + 5), z - 10], 'red')
        for zz in (z - 14, z + h):
            _box(P, [10, w + 20, 14], [x + side * 5, y, zz], 'red')


def _shell(P, W, D, beams_across=True):
    """Floor, ceiling, beams and the four outer walls round a room W wide (x -W/2 to W/2) and D deep (y 0 to D)."""
    hw = W / 2.0
    _box(P, [W + 2 * T, D + 2 * T, 8], [0, D / 2.0, -8], 'floor', solid=True)
    _box(P, [W + 2 * T, D + 2 * T, 12], [0, D / 2.0, H], 'ceiling', solid=True, bottom='ceiling')
    _run(P, 'x', -hw - T, hw + T, -T / 2.0, ())
    _run(P, 'x', -hw - T, hw + T, D + T / 2.0, ())
    _run(P, 'y', 0.0, D, -hw - T / 2.0, ())
    _run(P, 'y', 0.0, D, hw + T / 2.0, ())
    n = max(2, int(D / 220.0))
    for k in range(1, n):
        _box(P, [W, 22, 26], [0, D * k / n, H - 26], 'teal' if k % 2 else 'red')
    _box(P, [26, D, 30], [0, D / 2.0, H - 30], 'red')                        # (the ridge beam)
    for x in (-hw + 15, hw - 15):
        for y in (15.0, D - 15.0):
            _post(P, x, y)


# ROOMS: each shell's rooms in its frame: name -> (x0, y0, x1, y1)
HOME_W, HOME_D, HOME_SPLIT = 1000.0, 640.0, 340.0
ELDER_W, ELDER_D, ELDER_SPLIT = 1400.0, 1100.0, 640.0
STORE_W, STORE_D = 1000.0, 640.0
ROOMS = {
    'huang_home': {'living': (-500.0, 0.0, 500.0, 340.0), 'sleeping': (-500.0, 360.0, -10.0, 640.0), 'kitchen': (10.0, 360.0, 500.0, 640.0)},
    'huang_elders': {'audience': (-700.0, 0.0, 700.0, 640.0), 'elder_left': (-700.0, 660.0, -240.0, 1100.0),
                     'study': (-220.0, 660.0, 220.0, 1100.0), 'elder_right': (240.0, 660.0, 700.0, 1100.0)},
    'huang_granary': {'store': (-500.0, 0.0, 500.0, 640.0)},
}
# doorways, for the walk: from room to room (huanginside checks each is walked through)
WAYS = {
    'huang_home': [('living', 'sleeping', (-250.0, 350.0)), ('living', 'kitchen', (250.0, 350.0))],
    'huang_elders': [('audience', 'elder_left', (-470.0, 650.0)), ('audience', 'elder_right', (470.0, 650.0)),
                     ('elder_left', 'study', (-230.0, 880.0)), ('elder_right', 'study', (230.0, 880.0))],
    'huang_granary': [],
}
DAIS = (-300.0, 470.0, 300.0, 640.0)        # (the elders' dais: x0, y0, x1, y1, its front step below y0)
DAIS_UP = 30.0


def home():
    P = []
    W, D, S = HOME_W, HOME_D, HOME_SPLIT
    _shell(P, W, D)
    hw = W / 2.0
    _run(P, 'x', -hw, hw, S + 10.0, [(-250 - WAY_W / 2, -250 + WAY_W / 2), (250 - WAY_W / 2, 250 + WAY_W / 2)])
    _run(P, 'y', S + 20.0, D, 0.0, ())
    for x in (-350.0, 350.0):                       # (front windows either side of the door, as outside)
        _window(P, x, 0.0, w=150, h=130, z=110, side=1)
    for x in (-420.0, 420.0):           # (clear of the bed's head and the range's flue)
        _window(P, x, D, w=130, h=110, z=130, side=-1)
    for sx in (-1, 1):
        _window(P, sx * hw, S / 2.0, w=130, h=120, z=120, along='y', side=-sx)
    _post(P, -hw + 15, S + 10)
    _post(P, hw - 15, S + 10)
    return _desc('FOLabHuangHome', P, ground=False)


def elders():
    P = []
    W, D, S = ELDER_W, ELDER_D, ELDER_SPLIT
    _shell(P, W, D)
    hw = W / 2.0
    _run(P, 'x', -hw, hw, S + 10.0, [(-470 - WAY_W / 2, -470 + WAY_W / 2), (470 - WAY_W / 2, 470 + WAY_W / 2)])
    for sx in (-1, 1):
        _run(P, 'y', S + 20.0, D, sx * 230.0, [(880 - WAY_W / 2, 880 + WAY_W / 2)])
    for x in (-350.0, 350.0):                       # (the audience room's two rows of columns)
        for y in (180.0, 420.0):
            _post(P, x, y)
    for x in (-500.0, -230.0, 230.0, 500.0):
        _window(P, x, 0.0, w=150, h=140, z=110, side=1)
    for x in (-620.0, 620.0):           # (clear of the beds' heads)
        _window(P, x, D, w=140, h=120, z=130, side=-1)
    for sx in (-1, 1):
        _window(P, sx * hw, 320.0, w=160, h=140, z=110, along='y', side=-sx)
        _window(P, sx * hw, 880.0, w=130, h=120, z=130, along='y', side=-sx)
    # the dais against the back wall of the audience room, a step up across its front
    x0, y0, x1, y1 = DAIS
    _box(P, [x1 - x0, y1 - y0, DAIS_UP], [(x0 + x1) / 2, (y0 + y1) / 2, 0], 'floor', solid=True, front='red', left='red', right='red')
    _box(P, [x1 - x0 + 4, 4, 4], [(x0 + x1) / 2, y0 - 1, DAIS_UP - 4], 'gold')
    _box(P, [x1 - x0 - 120, 40, DAIS_UP / 2], [(x0 + x1) / 2, y0 - 20, 0], 'floor', solid=True, front='red', left='red', right='red')
    # behind the dais a great screen of red lacquer framed in gold on the wall
    _box(P, [560, 8, 220], [0, S - 4, DAIS_UP + 10], 'red', front='red')
    _box(P, [580, 10, 12], [0, S - 5, DAIS_UP + 230], 'gold')
    _post(P, -hw + 15, S + 10)
    _post(P, hw - 15, S + 10)
    return _desc('FOLabHuangElders', P, ground=False)


def granary():
    P = []
    W, D = STORE_W, STORE_D
    _shell(P, W, D)
    hw = W / 2.0
    for x in (-300.0, 300.0):
        _post(P, x, D / 2.0)
    for x in (-350.0, 350.0):
        _window(P, x, 0.0, w=120, h=90, z=170, side=1)
    for sx in (-1, 1):
        _window(P, sx * hw, D / 2.0, w=140, h=90, z=170, along='y', side=-sx)
    return _desc('FOLabHuangGranary', P, ground=False)


# ---------- what stands in them (front -y, on z 0, unless in a game piece's frame) ----------

def table(w=96.0, d=96.0, h=80.0, name='FOLabHuangTable'):
    P = []
    _box(P, [w, d, 5], [0, 0, h - 5], 'wood')
    for sx in (-1, 1):
        _box(P, [w - 12, 4, 9], [0, sx * (d / 2 - 6), h - 14], 'wood')
        _box(P, [4, d - 12, 9], [sx * (w / 2 - 6), 0, h - 14], 'wood')
        for sy in (-1, 1):
            _box(P, [6, 6, h - 5], [sx * (w / 2 - 6), sy * (d / 2 - 6), 0], 'wood')
    _hit(P, [w, d, h], [0, 0, 0])
    return _desc(name, P)


def stool():
    P = []
    _cyl(P, 17, 42, [0, 0, 0], 'wood', sides=12, r2=15)
    _cyl(P, 18, 2, [0, 0, 8], 'gold', sides=12)
    _cyl(P, 18, 2, [0, 0, 34], 'gold', sides=12)
    _cyl(P, 16, 4, [0, 0, 42], 'red', sides=12)
    _hit(P, [32, 32, 46], [0, 0, 0])
    return _desc('FOLabHuangStool', P)


# The game furniture each sat-on or lain-on piece copies: (game editor ID, its markers, its floor under its origin).
# Chair02F sits facing +y, its origin at the seat; Bench02 runs along y, origin on the floor, seat 30 up; the hotel's
# queen bed runs along y, origin on the floor, got into from either side (bounds.py on D:, 22 Nov 2026).
SEATS = {
    'chair': ('Chair02F', [(-51.7, 2.9, -30.1, 1570, 11, 11), (51.4, 2.9, -30.1, 4712, 12, 12), (-0.2, 58.0, -30.1, 3141, 14, 14)], -30.1),
    'bench': ('Bench02', [(-77.4, -30.6, 0.0, 1570, 14, 14), (-77.4, 26.2, 0.0, 1570, 14, 14), (78.1, -24.5, 0.0, 4712, 14, 14),
                          (78.1, 29.1, 0.0, 4712, 14, 14)], 0.0),
    'bed': ('HotelBedQueenBothSides', [(102.9, 12.0, 0.0, 4712, 1, 1), (-104.0, 11.3, 0.0, 1570, 2, 2)], 0.0),
}


def chair():
    """An armchair in the game chair's frame: seat at the origin, floor 30 under, facing +y (its back at -y)."""
    P = []
    f = SEATS['chair'][2]
    _box(P, [48, 44, 4], [0, 0, -4], 'wood')
    _box(P, [44, 40, 2], [0, 0, 0], 'red')                       # (a cushion)
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(P, [4, 4, -4 - f], [sx * 21, sy * 19, f], 'wood')
        _box(P, [4, 40, 3], [sx * 22, 0, 22], 'wood')                # (the arms)
        _box(P, [4, 4, 22], [sx * 22, 18, 0], 'wood')
        _box(P, [4, 4, 64], [sx * 21, -20, 0], 'wood')               # (the back's posts)
    _box(P, [26, 3, 50], [0, -20, 8], 'wood')                        # (the splat)
    _box(P, [56, 5, 5], [0, -20, 64], 'wood')                        # (the yoke, its ends turned up)
    _hit(P, [48, 44, -f], [0, 0, f])
    _hit(P, [48, 6, 66], [0, -20, 0])
    return _desc('FOLabHuangChair', P, ground=False, markers=SEATS['chair'][1])


def bench():
    """A bench in Bench02's frame: along y, origin on the floor, seat 30 up."""
    P = []
    _box(P, [40, 152, 5], [0, 0, 26], 'wood')
    for sy in (-1, 1):
        for sx in (-1, 1):
            _box(P, [5, 5, 26], [sx * 15, sy * 66, 0], 'wood')
        _box(P, [34, 4, 4], [0, sy * 66, 8], 'wood')
    _box(P, [4, 132, 6], [0, 0, 8], 'wood')
    _hit(P, [40, 152, 31], [0, 0, 0])
    return _desc('FOLabHuangBench', P, markers=SEATS['bench'][1])


def bed(quilt='quilt'):
    """A canopy bed in the hotel queen bed's frame: along y, its head at +y, origin on the floor, got into from either
    side. A platform of rosewood, the quilt and pillows, four posts carrying a canopy, lattice at the head."""
    P = []
    W, L = 136.0, 168.0
    _box(P, [W, L, 38], [0, 0, 0], 'wood')
    _box(P, [W - 6, L - 6, 12], [0, 0, 38], 'linen')
    _box(P, [W - 4, L * 0.62, 6], [0, -L * 0.17, 48], quilt)        # (the quilt over the foot)
    for sx in (-1, 1):
        _box(P, [W * 0.4, 30, 10], [sx * W * 0.22, L / 2 - 26, 50], 'linen')
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(P, [7, 7, 222], [sx * (W / 2 - 3), sy * (L / 2 - 3), 0], 'wood')
        _box(P, [5, L, 12], [sx * (W / 2 - 3), 0, 210], 'red')
    for sy in (-1, 1):
        _box(P, [W, 5, 12], [0, sy * (L / 2 - 3), 210], 'red')
    _box(P, [W, L, 3], [0, 0, 222], 'quilt_red', bottom='quilt_red')     # (the canopy)
    _box(P, [W - 8, 3, 150], [0, L / 2 - 3, 60], 'window', front='window', back='window')   # (lattice at the head)
    _hit(P, [W, L, 52], [0, 0, 0])
    _hit(P, [W, 10, 222], [0, L / 2 - 5, 0])
    return _desc('FOLabHuangBed' + ('' if quilt == 'quilt' else quilt[5:].title()), P, markers=SEATS['bed'][1])


def altar():
    """The family's altar table against a wall: long and narrow, gold along its edge; tablets, the incense burner, two
    candlesticks and bowls of offerings on it."""
    P = []
    w, d, h = 200.0, 46.0, 96.0
    _box(P, [w + 20, d, 6], [0, 0, h - 6], 'wood')
    for sx in (-1, 1):
        _box(P, [10, d, 6], [sx * (w / 2 + 6), 0, h], 'wood')          # (its scrolled-up ends)
        for sy in (-1, 1):
            _box(P, [7, 7, h - 6], [sx * (w / 2 - 8), sy * (d / 2 - 5), 0], 'wood')
    _box(P, [w, 4, 18], [0, -d / 2 + 2, h - 24], 'red')
    _box(P, [w, 2, 3], [0, -d / 2 - 1, h - 9], 'gold')
    for k, x in enumerate((-40.0, 0.0, 40.0)):
        _box(P, [16, 6, 34 + (6 if k == 1 else 0)], [x, 12, h], 'red', front='gold' if k == 1 else 'red')
        _box(P, [20, 8, 6], [x, 12, h], 'wood')
    _cyl(P, 11, 12, [0, -6, h], 'bronze', sides=10, r2=13)
    for sx in (-1, 1):
        _cyl(P, 3, 22, [sx * 80, 0, h], 'bronze', sides=6)
        _cyl(P, 2.2, 12, [sx * 80, 0, h + 22], 'linen', sides=6)
        _cyl(P, 10, 4, [sx * 60, -10, h], 'porcelain', sides=10, r2=12)
        _cyl(P, 7, 5, [sx * 60, -10, h + 4], 'maize', sides=8)
    _hit(P, [w + 20, d, h], [0, 0, 0])
    return _desc('FOLabHuangAltar', P)


def cabinet():
    P = []
    w, d, h = 100.0, 50.0, 190.0
    _box(P, [w, d, h], [0, 0, 0], 'red', front='cabinet')
    _box(P, [w + 6, d + 6, 6], [0, 0, h], 'wood')
    for sx in (-1, 1):
        _box(P, [6, 6, 8], [sx * (w / 2 - 3), -d / 2 + 3, -8 + 8], 'wood')
    _hit(P, [w, d, h + 6], [0, 0, 0])
    return _desc('FOLabHuangCabinet', P)


def chest():
    """A clothes chest of red lacquer with brass corners and lock plate (a container's model)."""
    P = []
    w, d, h = 90.0, 50.0, 52.0
    _box(P, [w, d, h], [0, 0, 0], 'red')
    _box(P, [w + 2, d + 2, 6], [0, 0, h - 10], 'red_dark')
    _box(P, [14, 2, 18], [0, -d / 2 - 1, h - 22], 'gold')
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(P, [10, 10, 4], [sx * (w / 2 - 4), sy * (d / 2 - 4), h - 1], 'gold')
    _hit(P, [w, d, h], [0, 0, 0])
    return _desc('FOLabHuangChest', P)


def stove():
    """The kitchen range: brick on a stone base, two pots set in its top, the fire's mouth in front, the flue going up to
    the ceiling from its back."""
    P = []
    w, d, h = 200.0, 84.0, 80.0
    _box(P, [w, d, h], [0, 0, 0], 'bricks', top='stone')
    _box(P, [w + 6, d + 6, 6], [0, 0, h], 'stone')
    for x in (-50.0, 50.0):
        _cyl(P, 30, 16, [x, -4, h + 2], 'iron', sides=14, r2=34)
        _cyl(P, 31, 2, [x, -4, h + 18], 'wood', sides=14)
        _box(P, [44, 2, 34], [x, -d / 2 - 1, 14], 'iron')
    _box(P, [60, 50, H - h - 6], [0, d / 2 - 25, h + 6], 'bricks', solid=True)
    _hit(P, [w, d, h + 6], [0, 0, 0], 'stone')
    return _desc('FOLabHuangStove', P)


def shelf():
    """Kitchen shelves: bowls, jars and a stack of plates."""
    P = []
    w, d, h = 140.0, 36.0, 170.0
    for sx in (-1, 1):
        _box(P, [5, d, h], [sx * (w / 2 - 2.5), 0, 0], 'wood')
    for k, z in enumerate((10.0, 60.0, 110.0, 160.0)):
        _box(P, [w, d, 4], [0, 0, z], 'wood')
        if k == 3:
            continue
        for j, x in enumerate((-45.0, -10.0, 25.0, 52.0)):
            if (j + k) % 3 == 0:
                _cyl(P, 12, 26, [x, 0, z + 4], 'glaze', sides=10, r2=9)
            elif (j + k) % 3 == 1:
                for s in range(3):
                    _cyl(P, 11, 4, [x, 0, z + 4 + s * 4], 'porcelain', sides=10, r2=13)
            else:
                _cyl(P, 9, 18, [x, 2, z + 4], 'porcelain', sides=10, r2=11)
    _box(P, [w, 3, h], [0, d / 2 - 1.5, 0], 'wood')
    _hit(P, [w, d, h], [0, 0, 0])
    return _desc('FOLabHuangShelf', P)


def jar():
    """A big storage jar, green-glazed, its lid on (a container's model)."""
    P = []
    _cyl(P, 22, 12, [0, 0, 0], 'glaze', sides=14, r2=30)
    _cyl(P, 30, 36, [0, 0, 12], 'glaze', sides=14, r2=26)
    _cyl(P, 26, 14, [0, 0, 48], 'glaze', sides=14, r2=16)
    _cyl(P, 18, 5, [0, 0, 62], 'wood', sides=14)
    _cyl(P, 4, 4, [0, 0, 67], 'wood', sides=6)
    _hit(P, [56, 56, 66], [0, 0, 0])
    return _desc('FOLabHuangJar', P)


def grain_bin():
    """A grain bin of boards with its lid of planks, rice heaped where the lid is pushed back."""
    P = []
    w, d, h = 170.0, 100.0, 110.0
    _box(P, [w, d, h], [0, 0, 0], 'wood', top='rice')
    _box(P, [w * 0.55, d + 4, 4], [w * 0.22, 0, h], 'wood')
    _cyl(P, 40, 22, [-w * 0.26, 0, h - 2], 'rice', sides=12, r2=12)              # (the heap where the lid is back)
    _cyl(P, 9, 5, [w * 0.2, -10, h + 4], 'wood', sides=10, r2=11)               # (a measure on the lid)
    for sx in (-1, 0, 1):
        _box(P, [6, d + 6, h + 4], [sx * (w / 2 - 3), 0, 0], 'red_dark')
    _box(P, [w - 12, 3, 16], [0, -d / 2 - 1, h - 30], 'red_dark')                # (a rail across the front)
    _hit(P, [w, d, h + 4], [0, 0, 0])
    return _desc('FOLabHuangBin', P)


def maize_strings():
    """Strings of maize cobs hung on a wall from a pole: its back on y 0, facing -y, origin at the pole's foot level."""
    P = []
    _box(P, [220, 6, 6], [0, -8, 150], 'wood')
    for k in range(7):
        x = -96 + k * 32
        n = 5 + (k * 3) % 3
        for j in range(n):
            _cyl(P, 5, 18, [x + (j % 2) * 5 - 2.5, -10, 150 - 20 - j * 17], 'maize', sides=6, r2=4)
        _box(P, [2, 2, 22], [x, -8, 130], 'sack')
    return _desc('FOLabHuangMaizeStrings', P, ground=False)


def sacks(n=5, seed=3):
    """Sacks of grain, stacked two high."""
    import random
    rng = random.Random(seed)
    P = []
    spots = [(-34, 0, 0), (34, 0, 0), (0, 40, 0), (-20, 10, 30), (24, 14, 30), (0, -30, 0)][:n]
    for x, y, z in spots:
        _box(P, [60, 40, 30], [x, y, z], 'sack', turn=[0, 0, rng.uniform(-15, 15)])
    _hit(P, [130, 110, 60], [0, 5, 0])
    return _desc('FOLabHuangSacks', P, bevel=6)


def baskets():
    P = []
    for x, y, r, h in ((-26, 0, 22, 30), (24, 6, 18, 26), (0, 34, 16, 22)):
        _cyl(P, r, h, [x, y, 0], 'wicker', sides=12, r2=r * 1.15)
        _cyl(P, r * 0.95, 2, [x, y, h - 4], 'maize' if x < 0 else 'rice', sides=12)
    _hit(P, [96, 80, 30], [0, 10, 0])
    return _desc('FOLabHuangBaskets', P)


def maize_rack():
    """A drying rack of poles, cobs hung on it in bunches."""
    P = []
    w, h = 180.0, 170.0
    for sx in (-1, 1):
        _box(P, [6, 30, h], [sx * (w / 2 - 3), 0, 0], 'wood')
    for z in (60.0, 120.0, h - 6):
        _box(P, [w, 5, 5], [0, 0, z], 'wood')
    for k in range(6):
        x = -w / 2 + 22 + k * (w - 44) / 5.0
        for z in (60.0, 120.0):
            for j in (-1, 0, 1):
                _cyl(P, 4, 26, [x + j * 7, j * 3, z - 28], 'maize', sides=6, r2=3)
    _hit(P, [w, 30, h], [0, 0, 0])
    return _desc('FOLabHuangMaizeRack', P)


def rug_(w=300.0, d=200.0):
    P = []
    _box(P, [w, d, 1.2], [0, 0, 0], 'rug', top='rug', left='red', right='red', front='red', back='red')
    return _desc('FOLabHuangRug', P, shade=False)


def screen():
    """A folding screen of four leaves, red frames over lattice and paper."""
    P = []
    lw, h = 52.0, 176.0
    for k in range(4):
        x = (k - 1.5) * lw * 0.94
        y = 8.0 if k % 2 else -8.0
        rz = 20.0 if k % 2 else -20.0
        _box(P, [lw - 4, 3, h - 30], [x, y, 20], 'window', turn=[0, 0, rz], front='window', back='window')
        _box(P, [lw, 5, 6], [x, y, h - 10], 'red', turn=[0, 0, rz])
        _box(P, [lw, 5, 6], [x, y, 14], 'red', turn=[0, 0, rz])
        _box(P, [4, 5, h], [x - lw / 2 + 2, y, 0], 'red')
    _hit(P, [lw * 4, 34, h], [0, 0, 0])
    return _desc('FOLabHuangScreen', P)


LANTERN_DROP = 70.0         # (the cord over the lantern's top: it hangs this far under the ceiling)


def lantern():
    """A red paper lantern on a cord, gold caps, a tassel; origin at the tassel's foot."""
    P = []
    _cyl(P, 1.5, 14, [0, 0, 0], 'red', sides=6)
    _cyl(P, 9, 4, [0, 0, 14], 'gold', sides=12)
    _cyl(P, 22, 18, [0, 0, 18], 'lantern', sides=14, r2=26)
    _cyl(P, 26, 18, [0, 0, 36], 'lantern', sides=14, r2=22)
    _cyl(P, 9, 4, [0, 0, 54], 'gold', sides=12)
    _cyl(P, 0.8, LANTERN_DROP, [0, 0, 58], 'iron', sides=4)
    return _desc('FOLabHuangLantern', P, ground=False, shade=False)


def desk():
    """A writing desk: brush pot, inkstone, paper weighted down, a book."""
    P = []
    w, d, h = 150.0, 64.0, 80.0
    _box(P, [w, d, 5], [0, 0, h - 5], 'wood')
    for sx in (-1, 1):
        _box(P, [40, d - 8, h - 5], [sx * (w / 2 - 22), 0, 0], 'wood', front='cabinet')
    _box(P, [w - 90, 3, 10], [0, -d / 2 + 6, h - 15], 'red')
    _cyl(P, 6, 16, [52, 14, h], 'porcelain', sides=10)
    for k in range(4):
        _cyl(P, 0.8, 22, [50 + k, 13 + k, h + 6], 'wood', sides=4)
    _box(P, [22, 14, 3], [-48, 14, h], 'iron')
    _box(P, [54, 38, 0.6], [0, -2, h], 'linen')
    _box(P, [24, 32, 4], [-50, -10, h], 'teal')
    _hit(P, [w, d, h], [0, 0, 0])
    return _desc('FOLabHuangDesk', P)


def tea():
    """A tray: a teapot and four cups (on a table: no collision)."""
    P = []
    _box(P, [34, 24, 1.5], [0, 0, 0], 'wood')
    _cyl(P, 7, 9, [0, 2, 1.5], 'porcelain', sides=10, r2=6)
    _cyl(P, 1.5, 6, [8, 2, 4], 'porcelain', sides=6, turn=[0, 70, 0])
    for x, y in ((-11, -6), (-11, 6), (11, -6), (11, 8)):
        _cyl(P, 2.6, 3.5, [x, y, 1.5], 'porcelain', sides=8, r2=3.2)
    return _desc('FOLabHuangTea', P, shade=False)


def basin():
    """A wash stand: a bronze basin on a three-legged stand, a towel on its rail."""
    P = []
    for k in range(3):
        a = k * 2 * math.pi / 3
        _box(P, [4, 4, 84], [math.cos(a) * 16, math.sin(a) * 16, 0], 'wood')
    _cyl(P, 20, 3, [0, 0, 78], 'wood', sides=12)
    _cyl(P, 16, 8, [0, 0, 81], 'bronze', sides=14, r2=22)
    _box(P, [30, 3, 3], [0, 18, 110], 'wood')
    _box(P, [24, 2, 30], [0, 18, 82], 'linen')
    _hit(P, [44, 44, 90], [0, 0, 0])
    return _desc('FOLabHuangBasin', P)


def hanging_scroll():
    """A painting on a scroll, hung on a wall: its back on y 0, facing -y, origin at its foot."""
    P = []
    _box(P, [66, 1.5, 172], [0, -0.75, 0], 'scroll', front='scroll', back='scroll')
    for z in (-3.0, 172.0):
        _cyl(P, 2.5, 76, [-38, -3, z + 1.5], 'wood', sides=6, turn=[0, 90, 0])
    return _desc('FOLabHuangScroll', P, ground=False, shade=False)


def cushions():
    """Two seat cushions on a low platform, the dais's chairs' footrest."""
    P = []
    _box(P, [120, 50, 12], [0, 0, 0], 'wood')
    for x in (-30.0, 30.0):
        _box(P, [50, 40, 6], [x, 0, 12], 'quilt_red')
    _hit(P, [120, 50, 18], [0, 0, 0])
    return _desc('FOLabHuangCushions', P)


# piece: (label, description), each its own record (STAT; for SEATS a FURN, for CONTAINERS a CONT, huanginside's)
_P = {
    'huang_door': ('Huáng door', door),
    'huang_home': ('Huáng home, inside', home),
    'huang_elders': ('Huáng elders\' hall, inside', elders),
    'huang_granary': ('Huáng granary, inside', granary),
    'huang_table': ('Huáng square table', table),
    'huang_table_long': ('Huáng long table', lambda: table(180, 70, 80, 'FOLabHuangTableLong')),
    'huang_stool': ('Huáng drum stool', stool),
    'huang_chair': ('Huáng armchair', chair),
    'huang_bench': ('Huáng bench', bench),
    'huang_bed': ('Huáng canopy bed', bed),
    'huang_bed_red': ('Huáng canopy bed, red quilt', lambda: bed('quilt_red')),
    'huang_bed_green': ('Huáng canopy bed, green quilt', lambda: bed('quilt_green')),
    'huang_altar': ('Huáng altar table', altar),
    'huang_cabinet': ('Huáng tall cabinet', cabinet),
    'huang_chest': ('Huáng clothes chest', chest),
    'huang_stove': ('Huáng kitchen range', stove),
    'huang_shelf': ('Huáng kitchen shelves', shelf),
    'huang_jar': ('Huáng storage jar', jar),
    'huang_bin': ('Huáng grain bin', grain_bin),
    'huang_sacks': ('Huáng sacks of grain', sacks),
    'huang_baskets': ('Huáng baskets', baskets),
    'huang_maize_rack': ('Huáng maize rack', maize_rack),
    'huang_maize_strings': ('Huáng strings of maize', maize_strings),
    'huang_rug': ('Huáng rug', rug_),
    'huang_screen': ('Huáng folding screen', screen),
    'huang_lantern': ('Huáng lantern', lantern),
    'huang_desk': ('Huáng writing desk', desk),
    'huang_tea': ('Huáng tea tray', tea),
    'huang_basin': ('Huáng wash stand', basin),
    'huang_scroll': ('Huáng hanging scroll', hanging_scroll),
    'huang_cushions': ('Huáng cushions', cushions),
}
PIECES = {}
for _k, (_label, _fn) in _P.items():
    PIECES[_k] = {'label': _label, 'set': SET, 'file': _k[6:], 'describe': _fn, 'edid': _fn()['name']}
    if _k in modelsets.PIECES and modelsets.PIECES[_k]['describe'] is not _fn:
        raise ValueError('huangset: %s is already a piece' % _k)
    modelsets.PIECES[_k] = PIECES[_k]


# ---------- the halls outside, with a doorway where the door was painted ----------

def hall(red=False):
    """settlerset's hall as it stands, but for its painted door (the red leaves and the gold line between them): a real
    door hangs there now. Everything else, its far model and its collision, is the same, so it swaps by base."""
    import settlerset
    d = settlerset.hall(1300, 700, 380, True) if red else settlerset.hall()
    d['parts'] = [p for p in d['parts'] if p.get('look') != 'door'
                  and not (p.get('look') == 'gold' and [round(v) for v in p['size']] == [10, 10, 230])]
    d['name'] = 'FOLabHuangHall' + ('Red' if red else '')
    return d


HALLS = {'FOLabSettlerHall': ('huang_hall', 640.0), 'FOLabSettlerHallRed': ('huang_hall_red', 700.0)}   # (game... settlerset's edid: our piece, its depth)
for _k, _lab, _fn in (('huang_hall', 'Huáng hall (a door of its own)', hall), ('huang_hall_red', 'Huáng hall, red roof (a door of its own)', lambda: hall(True))):
    PIECES[_k] = {'label': _lab, 'set': SET, 'file': _k[6:], 'describe': _fn, 'edid': _fn()['name']}
    modelsets.PIECES[_k] = PIECES[_k]


# ---------- furniture markers: put into a model after it is made ----------

def with_markers(data, markers):
    """A model's bytes (nifmake's) with a BSFurnitureMarker 'FRN' added to its root's extras: [(x, y, z, heading in
    1/1000 radian, entry, entry)], as the game's furniture carries them."""
    import struct
    import nif
    import nifmake
    N = nif.Nif(data)
    n = len(N.types)
    blocks = [data[o:o + s] for o, s in zip(N.offsets, N.sizes)]
    strings = list(N.strings)
    if 'FRN' not in strings:
        strings.append('FRN')
    frn = strings.index('FRN')
    blocks.append(struct.pack('<iI', frn, len(markers))
                  + b''.join(struct.pack('<fffHBB', float(x), float(y), float(z), int(o), int(a), int(b)) for x, y, z, o, a, b in markers))
    root = blocks[0]
    name, k = struct.unpack_from('<iI', root, 0)
    extras = list(struct.unpack_from('<%di' % k, root, 8))
    blocks[0] = struct.pack('<iI%di' % (k + 1), name, k + 1, *(extras + [n])) + root[8 + 4 * k:]
    kinds = [t.decode() if isinstance(t, bytes) else t for t in N.types] + ['BSFurnitureMarker']
    types = []
    for t in kinds:
        if t not in types:
            types.append(t)
    head = b'Gamebryo File Format, Version 20.2.0.7\n' + struct.pack('<IBIII', nif.VERSION, 1, N.user, len(blocks), N.bsver)
    head += nifmake._short('FOLab') + nifmake._short('') + nifmake._short('')
    head += struct.pack('<H', len(types)) + b''.join(nifmake._sized(t) for t in types)
    head += struct.pack('<%dH' % len(blocks), *(types.index(t) for t in kinds))
    head += struct.pack('<%dI' % len(blocks), *(len(b) for b in blocks))
    head += struct.pack('<II', len(strings), max(len(s) for s in strings)) + b''.join(nifmake._sized(s) for s in strings)
    head += struct.pack('<I', 0)
    return head + b''.join(blocks) + struct.pack('<II', 1, 0)


def build(piece):
    """modelsets.build, and for what is sat or lain on its markers put in (`SEATS`)."""
    made = modelsets.build(piece)
    mk = PIECES[piece]['describe']().get('markers')
    if mk:
        made['nif'] = with_markers(made['nif'], mk)
        made['files'][made['mesh']] = made['nif']
    return made
