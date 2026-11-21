"""FOLab's own road and rubble: pieces with no edge to show, that lie in the ground at any slope.

Why (21 Nov 2026): the game's road slab is a box, its top at its origin and its sides 25 under; on a slope, or where the
land under it moved after it was laid, a side shows and then daylight under it. Its rubble piles are several shapes of
several pictures each (RubblePile02 five, 2,262 of them on Waikiki: 11,310 draws), with flat bottoms that hang where the
ground falls away. Each piece here is one shape over one picture sheet, and every edge of it goes down into the ground:

  - a road piece is a surface over a grid (`modelmake` 'field'): the crown and asphalt as the game's (top at the origin,
    crown CROWN over it, the game's 1,024 x 632 frame), then a gravel verge falling VERGE_DROP to VERGE and a skirt on to
    DEEP_DROP under at DEEP, and at each end a flap the same way (END_*): where the next piece meets it at another slope
    the joint is a dip, not a step. Collision is one convex solid over the crown, as the game's slab.
  - a heap is rings round its middle: a mound HEIGHT high to its rim (z 0), its rim wavy (no two heaps alike in outline),
    then a skirt down SKIRT_1 and on to SKIRT_2 under; chunks of concrete, brick and planks half in it. Collision one
    convex solid round the mound above its rim.

`PIECES` (modelsets, set 'rubble': meshes\\folab\\rubble, textures\\folab\\rubble) are registered at import; `REPLACES`
says which game base each stands in for, `rubbleswap.py` swaps them and seats them. A piece's `foot` (rim and tips in its
frame) is what `seat` lays it by: the rim at or under the ground all round, the skirt's tips under it.

Pictures: 'rubble/road' (one sheet for every road piece: across it, asphalt with its line, a crumbling edge, gravel),
'rubble/heap' (four quarters: rubble ground, broken concrete, brick, planks and tin)."""
import math
import random

import modelsets
import texpaint as tp
from modelsets import look

SET = 'rubble'

# ---------- roads ----------
HALF_LONG = 512.0       # (the game's long piece: 1,024 along x, its middle at the origin)
ASPHALT = 286.0         # half the asphalt's width (the game's top: 316)
VERGE = 324.0           # the gravel verge's outer edge...
VERGE_DROP = 16.0       # ...this far under the asphalt's edge
DEEP = 344.0            # and the skirt's: down DEEP_DROP, far under the land's 8-unit steps and the game's 25
DEEP_DROP = 52.0
CROWN = 10.0            # the road's middle over its edges (the game's: 10 to 14)
END_FLAP = 24.0         # past each end the road dips END_DROP over END_FLAP, then on to END_DEEP
END_DROP = 12.0
END_REACH = 40.0
END_DEEP = 46.0
CAP_END = 112.0         # an end cap's asphalt stops here along x (the game's cap: -96 to 157)
COLLIDE_UNDER = 26.0    # its collision goes this far under the origin (the game's slab: 25)

# ---------- heaps ----------
SKIRT_AT = 1.12         # a heap's skirt goes down to SKIRT_1 at this much of its rim's radius...
SKIRT_1 = 16.0
DEEP_AT = 1.3           # ...and to SKIRT_2 at this much
SKIRT_2 = 46.0
RINGS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.69, 0.78, 0.86, 0.93, 1.0, 1.06, SKIRT_AT, DEEP_AT)
SPOKES = 36


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def across(y):
    """A road piece's height at y across it (z of its top; 0 at the asphalt's edge)."""
    a = abs(y)
    if a <= ASPHALT:
        return CROWN * (1 - (a / ASPHALT) ** 2)
    if a <= VERGE:
        return -VERGE_DROP * _smooth((a - ASPHALT) / (VERGE - ASPHALT))
    return -VERGE_DROP - (DEEP_DROP - VERGE_DROP) * min(1.0, (a - VERGE) / (DEEP - VERGE))


WHEELS = (93.0, 193.0)  # where wheels ran in each lane (its middle at 143), worn RUT down over RUT_WIDE each side
RUT = 1.5
RUT_WIDE = 22.0
ROAD_SHEET_LONG = 1024.0    # the road's picture repeats this far along (a whole long piece)


def _rut(y):
    """How far the drawn road is worn down at y (the solid keeps the crown: a rut is too shallow to walk differently)."""
    a = abs(y)
    if a > ASPHALT:
        return 0.0
    return RUT * max(0.0, 1.0 - min(abs(a - w) for w in WHEELS) / RUT_WIDE)


def _dip(d):
    """How far an end flap is under the road d past the asphalt's end."""
    if d <= 0:
        return 0.0
    if d <= END_FLAP:
        return END_DROP * _smooth(d / END_FLAP)
    return END_DROP + (END_DEEP - END_DROP) * min(1.0, (d - END_FLAP) / (END_REACH - END_FLAP))


def road_desc(name, x0, x1, ends=(True, True), shift=0.0, flip=False):
    """A road piece from x0 to x1 (the asphalt's ends; flaps past each end in `ends`). shift/flip: where on the sheet it
    starts along and whether across is turned over, so pieces side by side don't repeat."""
    xs = []
    if ends[0]:
        xs += [x0 - END_REACH, x0 - END_FLAP, x0 - END_FLAP / 2]
    n = max(1, int(round((x1 - x0) / 64.0)))
    xs += [x0 + (x1 - x0) * k / n for k in range(n + 1)]
    if ends[1]:
        xs += [x1 + END_FLAP / 2, x1 + END_FLAP, x1 + END_REACH]
    ys = [-DEEP, -VERGE, -(ASPHALT + VERGE) / 2, -ASPHALT, -246.0, -215.0, -WHEELS[1], -171.0, -143.0, -115.0, -WHEELS[0], -71.0, -40.0, 0.0]
    ys += [-y for y in reversed(ys[:-1])]
    rows, uvs = [], []
    for y in ys:
        row, uv = [], []
        for x in xs:
            d = (x0 - x) if x < x0 else (x - x1) if x > x1 else 0.0
            row.append((x, y, round(min(across(y), across(min(abs(y), ASPHALT)) - _dip(d)) - _rut(y), 3)))     # (at a corner the deeper of the two)
            v = (y + DEEP) / (2 * DEEP)
            uv.append((x / ROAD_SHEET_LONG + 0.5 + shift, 1 - v if flip else v))        # (the sheet: ROAD_SHEET_LONG units along, the whole width across)
        rows.append(row)
        uvs.append(uv)
    # collision: the crown and verge as a prism over the asphalt's length (convex: the top only ever bends down)
    prof = [(-VERGE, across(VERGE)), (-ASPHALT, 0.0), (-ASPHALT * 0.6, across(ASPHALT * 0.6)), (0.0, CROWN),
            (ASPHALT * 0.6, across(ASPHALT * 0.6)), (ASPHALT, 0.0), (VERGE, across(VERGE)), (VERGE, -COLLIDE_UNDER), (-VERGE, -COLLIDE_UNDER)]
    return {'name': name, 'step': 1e6, 'bevel': 0,
            'looks': {'road': look('rubble/road')},
            'parts': [{'shape': 'field', 'look': 'road', 'rows': rows, 'uv': uvs},
                      _hull_part([(x, y, z) for x in (x0, x1) for y, z in prof]), _far_strip(x0, x1)]}


FAR_ACROSS = (-VERGE, -ASPHALT, -ASPHALT * 0.5, 0.0, ASPHALT * 0.5, ASPHALT, VERGE)


def _far_strip(x0, x1):
    """The road from afar (its `_lod.nif`, which lodobj puts in the distant blocks; without it the roads went from the far
    view, 21 Nov 2026): the crown and verge as one strip of 12 triangles, the picture laid once along it (lodobj's sheet
    can't repeat it), no ends."""
    rows, uvs = [], []
    for y in FAR_ACROSS:
        rows.append([(x, y, round(across(y), 3)) for x in (x0, x1)])
        v = (y + DEEP) / (2 * DEEP)
        uvs.append([(0.0, v), (1.0, v)])
    return {'shape': 'field', 'look': 'road', 'rows': rows, 'uv': uvs, 'far_only': True}


def road_foot(x0, x1, ends=(True, True)):
    """(rim, tips) of a road piece: points along its edges at the asphalt's edge and at the skirt's foot."""
    rim, tips = [], []
    for k in range(9):
        x = x0 + (x1 - x0) * k / 8
        for sg in (-1, 1):
            rim.append((x, sg * ASPHALT, 0.0))
            tips.append((x, sg * DEEP, -DEEP_DROP))
    for e, x, sg in ((ends[0], x0, -1), (ends[1], x1, 1)):
        if e:
            for y in (-ASPHALT, -ASPHALT / 2, 0.0, ASPHALT / 2, ASPHALT):
                rim.append((x, y, across(y)))
                tips.append((x + sg * END_REACH, y, across(y) - END_DEEP))
    return rim, tips


# ---------- heaps ----------
Q = {'ground': (0.0, 0.0, 0.5, 0.5), 'concrete': (0.5, 0.0, 1.0, 0.5), 'brick': (0.0, 0.5, 0.5, 0.75), 'siding': (0.0, 0.75, 0.5, 1.0),
     'wood': (0.5, 0.5, 1.0, 0.75), 'tin': (0.5, 0.75, 0.75, 1.0), 'stucco': (0.75, 0.75, 1.0, 0.875), 'rough': (0.75, 0.875, 1.0, 1.0)}
SIDES = {'concrete': 'rough', 'stucco': 'brick', 'siding': 'wood'}     # (a chunk's broken sides: what it is inside)
INSET = 6.0 / 1024      # (each quarter's own pictures kept this far inside it: smaller copies blur across)


def _region(name):
    u0, v0, u1, v1 = Q[name]
    return (u0 + INSET, v0 + INSET, u1 - INSET, v1 - INSET)


class Heap:
    """A heap's shape: its rim's radius by direction (wavy), its height anywhere, lumps on it."""

    def __init__(self, rx, ry, height, seed, lumps=0.35, wave=0.16):
        self.rx, self.ry, self.h = float(rx), float(ry), float(height)
        rnd = random.Random(seed)
        self.waves = [(rnd.uniform(-wave, wave) / (k ** 0.8), rnd.uniform(0, math.tau)) for k in range(2, 6)]
        self.bumps = [(rnd.uniform(-0.75, 0.75), rnd.uniform(-0.75, 0.75), rnd.uniform(0.12, 0.3), rnd.uniform(-lumps, lumps))
                      for _ in range(9)]
        # (and small lumps all over: a heap is chunks under a skin of grit, not a smooth dome)
        self.bumps += [(rnd.uniform(-0.85, 0.85), rnd.uniform(-0.85, 0.85), rnd.uniform(0.05, 0.1), rnd.uniform(-lumps, lumps) * 0.6)
                       for _ in range(18)]
        self.top = (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2))     # (the highest point a little off the middle)

    def rim(self, th):
        return 1.0 + sum(a * math.cos(k * th + ph) for k, (a, ph) in enumerate(self.waves, 2))

    def at(self, r, th):
        """(x, y, z) at r of the rim's radius in direction th."""
        rr = self.rim(th)
        x, y = self.rx * rr * r * math.cos(th), self.ry * rr * r * math.sin(th)
        if r <= 1.0:
            ux, uy = x / self.rx - self.top[0] * (1 - r), y / self.ry - self.top[1] * (1 - r)
            lump = sum(a * math.exp(-((ux - bx) ** 2 + (uy - by) ** 2) / (w * w)) for bx, by, w, a in self.bumps)
            z = self.h * (1 - r * r) ** 1.15 * max(0.3, 1.0 + lump)
        elif r <= SKIRT_AT:
            z = -SKIRT_1 * _smooth((r - 1.0) / (SKIRT_AT - 1.0))
        else:
            z = -SKIRT_1 - (SKIRT_2 - SKIRT_1) * min(1.0, (r - SKIRT_AT) / (DEEP_AT - SKIRT_AT))
        return x, y, z

    def outer(self):
        return max(self.rx, self.ry) * max(self.rim(math.tau * k / 64) for k in range(64)) * DEEP_AT


def _chunks(hp, seed, chunks, kinds):
    """What lies in a heap: `chunks` big pieces (slabs of concrete or stucco, brick, planks, siding, tin; some stuck in it
    on end), twice as many fist-sized bits, half sunk where they lie. Drawn only (the heap's solid is its mound); none
    past BITS_REACH of the rim, so nothing overhangs the skirt."""
    rnd = random.Random(seed * 7 + 3)
    out = []

    def lay(r, th, size, kd, up=0.0, sink=0.35, spin=40):
        x, y, z = hp.at(r, th)
        # (lying along the heap's slope there, sunk into it; `up` stands it on end by that much more)
        dz = (hp.at(min(1.0, r + 0.08), th)[2] - hp.at(max(0.0, r - 0.08), th)[2])
        run = 0.16 * math.hypot(hp.rx * math.cos(th), hp.ry * math.sin(th)) or 1.0
        tilt = math.degrees(math.atan2(-dz, run)) * 0.8 + rnd.uniform(-12, 12) + up
        side = SIDES.get(kd, kd)
        faces = {'bottom': None, 'front': side, 'back': side, 'left': side, 'right': side}
        out.append({'shape': 'box', 'size': size, 'at': [x, y, z - size[2] * sink - size[0] * 0.18 * math.sin(math.radians(abs(up)))],
                    'look': kd, 'solid': False, 'bevel': 0, 'faces': faces,
                    'turn': [rnd.uniform(-10, 10), tilt, math.degrees(th) + rnd.uniform(-spin, spin)]})

    for c in range(chunks):
        r, th = math.sqrt(rnd.uniform(0.02, 0.78)), rnd.uniform(0, math.tau)
        kd = kinds[c % len(kinds)]
        big = 1.0 - 0.5 * r
        up = rnd.choice((0, 0, 0, rnd.uniform(30, 60), -rnd.uniform(30, 55))) if kd in ('concrete', 'wood', 'tin', 'siding', 'stucco') else 0
        if kd == 'wood':
            size = [rnd.uniform(110, 200) * big, rnd.uniform(14, 24), rnd.uniform(4, 7)]
        elif kd == 'siding':
            size = [rnd.uniform(90, 150) * big, rnd.uniform(40, 70) * big, rnd.uniform(3, 5)]
        elif kd == 'tin':
            size = [rnd.uniform(80, 140) * big, rnd.uniform(60, 100) * big, 2.5]
        elif kd == 'brick':
            size = [rnd.uniform(40, 80), rnd.uniform(26, 46), rnd.uniform(14, 26)]
        else:
            size = [rnd.uniform(60, 130) * big, rnd.uniform(50, 100) * big, rnd.uniform(10, 24)]
        lay(r, th, size, kd, up, 0.45 if up else 0.35)
        if kd == 'wood' and rnd.random() < 0.4:          # (planks fall in twos and threes, across each other)
            lay(min(0.85, r + rnd.uniform(-0.06, 0.06)), th + rnd.uniform(-0.12, 0.12), [size[0] * rnd.uniform(0.6, 0.9), size[1], size[2]], 'wood', 0, 0.2, 80)
    for c in range(chunks * 2):
        r, th = math.sqrt(rnd.uniform(0.0, BITS_REACH ** 2)), rnd.uniform(0, math.tau)
        kd = rnd.choice(('rough', 'rough', 'brick', 'concrete', 'stucco'))
        e = rnd.uniform(9, 22)
        lay(r, th, [e * rnd.uniform(0.8, 1.6), e * rnd.uniform(0.7, 1.2), e * rnd.uniform(0.5, 0.9)], kd, rnd.uniform(-30, 30), 0.4, 180)
    return out


BITS_REACH = 0.9


def heap_desc(name, rx, ry, height, seed=1, chunks=10, kinds=('concrete', 'concrete', 'brick', 'wood', 'tin', 'stucco', 'siding')):
    """A heap of rubble: rings of the mound and its skirt, chunks half in it, one convex solid round what is above its
    rim. Every look is a quarter of the one sheet: one shape."""
    hp = Heap(rx, ry, height, seed)
    reach = hp.outer()
    g0, gv0, g1, gv1 = _region('ground')
    rows, uvs = [], []
    for r in RINGS:
        row, uv = [], []
        for k in range(SPOKES + 1):
            th = math.tau * (k % SPOKES) / SPOKES
            x, y, z = hp.at(r, th)
            row.append((round(x, 2), round(y, 2), round(z, 2)))
            uv.append((g0 + (g1 - g0) * (x / reach + 1) / 2, gv0 + (gv1 - gv0) * (1 - (y / reach + 1) / 2)))
        rows.append(row)
        uvs.append(uv)
    looks = {'ground': look('rubble/heap', region=_region('ground'))}
    for kd in set(kinds):
        looks[kd] = look('rubble/heap', region=_region(kd))
    parts = [{'shape': 'field', 'look': 'ground', 'rows': rows, 'uv': uvs, 'closed': True}]
    for kd in list(SIDES.values()) + ['rough', 'brick', 'concrete', 'stucco']:
        looks.setdefault(kd, look('rubble/heap', region=_region(kd)))
    parts += _chunks(hp, seed, chunks, kinds)
    pts = [hp.at(r, math.tau * k / 12) for r in (0.0, 0.5, 0.78, 0.94) for k in range(12)]
    pts += [(x, y, -10.0) for x, y, _z in (hp.at(1.0, math.tau * k / 12) for k in range(12))]
    parts.append(_hull_part(pts))
    return {'name': name, 'step': 1e6, 'bevel': 0, 'looks': looks, 'parts': parts}, hp


HULL_SNAPS = (4.0, 6.0, 8.0, 12.0, 16.0)


def _hull_part(pts):
    """A 'solid' part: the convex solid round pts on the finest grid whose solid reads back closed (onepiece.merged's
    way: faces nearly one plane don't close in Havok's or FOLab's reading)."""
    import nifmake
    import onepiece
    tri = {'p': [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 10.0, 0.0], 'n': [0.0, 0.0, 1.0] * 3, 'uv': [0.0] * 6, 'i': [0, 1, 2], 'tex': 'x.dds'}
    for snap in HULL_SNAPS:
        try:
            corners, faces = onepiece.convex_hull(pts, snap)
        except (onepiece.Unfit, KeyError):
            continue
        solid = {'points': corners, 'faces': faces, 'material': 'stone'}
        if not nifmake.check(nifmake.build('hull', [tri], [solid]), [tri], [solid]):
            return dict(solid, shape='solid')
    raise nifmake.MakeError('no closed solid round the heap')


def heap_foot(hp):
    """(rim, tips) of a heap: its rim all round (z 0) and its skirt's deepest ring."""
    rim, tips = [], []
    for k in range(16):
        th = math.tau * k / 16
        rim.append(hp.at(1.0, th))
        tips.append(hp.at(DEEP_AT, th))
    return rim, tips


def slab_desc(name, seed=1):
    """A broken slab of concrete lying in the ground: one box, its corner gone, rubble round its foot."""
    rnd = random.Random(seed)
    hp = Heap(118, 148, 10, seed + 5, lumps=0.2, wave=0.08)
    g0, gv0, g1, gv1 = _region('ground')
    reach = hp.outer()
    rows, uvs = [], []
    for r in RINGS:
        row, uv = [], []
        for k in range(SPOKES + 1):
            x, y, z = hp.at(r, math.tau * (k % SPOKES) / SPOKES)
            row.append((round(x, 2), round(y, 2), round(z, 2)))
            uv.append((g0 + (g1 - g0) * (x / reach + 1) / 2, gv0 + (gv1 - gv0) * (1 - (y / reach + 1) / 2)))
        rows.append(row)
        uvs.append(uv)
    looks = {'ground': look('rubble/heap', region=_region('ground')), 'concrete': look('rubble/heap', region=_region('concrete'))}
    parts = [{'shape': 'field', 'look': 'ground', 'rows': rows, 'uv': uvs, 'closed': True},
             {'shape': 'box', 'size': [184, 238, 22], 'at': [0, 0, -9], 'look': 'concrete', 'faces': {'bottom': None},
              'turn': [rnd.uniform(2, 5), rnd.uniform(-4, -1), rnd.uniform(-8, 8)], 'bevel': 0, 'material': 'stone'},
             {'shape': 'box', 'size': [70, 60, 18], 'at': [104, 120, -7], 'look': 'concrete', 'faces': {'bottom': None},
              'turn': [rnd.uniform(-8, 8), 14, 30], 'bevel': 0, 'solid': False}]
    return {'name': name, 'step': 1e6, 'bevel': 0, 'looks': looks, 'parts': parts}, hp


# ---------- pictures ----------
ASPH = (66, 66, 63)
ASPH_OLD = (108, 105, 97)
ASPH_NEW = (52, 52, 51)
GRAVEL = (128, 116, 96)
DIRT = (104, 88, 66)
SAND = (182, 166, 128)
LINE = (196, 168, 82)
WHITE = (204, 200, 186)
WEED = (84, 112, 52)


def _hash(ix, iy, s):
    """A number 0..1 for a whole-numbered spot (the same every time)."""
    h = ((ix * 0x8DA6B343) ^ (iy * 0xD8163841) ^ (s * 0xCB1AB31F)) & 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 0x2C1B3C6D) & 0xFFFFFFFF
    h = ((h ^ (h >> 12)) * 0x297A2D39) & 0xFFFFFFFF
    return ((h ^ (h >> 15)) & 0xFFFFFF) / float(0x1000000)


def _cells(x, y, seed, wrap=0):
    """Stones or cracks: (distance to the nearest of the points scattered one a square, to the next nearest, and which
    point is nearest, and how far x, y is from it each way), x and y in squares; `wrap` squares along x repeat."""
    ix, iy = math.floor(x), math.floor(y)
    d1 = d2 = 9.0
    best, off = (0, 0), (0.0, 0.0)
    for j in (-1, 0, 1):
        for i in (-1, 0, 1):
            cx, cy = ix + i, iy + j
            kx = cx % wrap if wrap else cx
            px = cx + _hash(kx, cy, seed)
            py = cy + _hash(kx, cy, seed + 1)
            d = (px - x) ** 2 + (py - y) ** 2
            if d < d1:
                d1, d2, best, off = d, d1, (kx, cy), (x - px, y - py)
            elif d < d2:
                d2 = d
    return math.sqrt(d1), math.sqrt(d2), best, off


def _around(a, a0, long):
    """a - a0 along a picture that repeats every `long`."""
    return (a - a0 + long / 2) % long - long / 2


def _road_marks(seed):
    """What has happened to one stretch of road (in units: along 0..ROAD_SHEET_LONG, across -ASPHALT..ASPHALT): cracks
    right across it, holes, patches cut and filled, the lanes' worst stretches of crazed asphalt."""
    rnd = random.Random(seed)
    L = ROAD_SHEET_LONG
    cracks = []         # (along, from across, to across, sealed with tar)
    for k in range(5):
        a = (k + rnd.uniform(0.15, 0.85)) * L / 5
        y0 = rnd.choice((-ASPHALT - 20, rnd.uniform(-ASPHALT, 0)))
        y1 = rnd.choice((ASPHALT + 20, rnd.uniform(0, ASPHALT)))
        cracks.append((a, y0, y1, rnd.random() < 0.4))
    holes = []          # (along, across, radius)
    for k in range(4):
        holes.append((rnd.uniform(0, L), rnd.choice((-1, 1)) * rnd.choice((WHEELS[0], WHEELS[1], ASPHALT - 26)) + rnd.uniform(-14, 14),
                      rnd.uniform(14, 34)))
    patches = []        # (along from, to, across from, to)
    for k in range(2):
        a0, w = rnd.uniform(0, L), rnd.uniform(60, 160)
        y0 = rnd.uniform(-ASPHALT + 20, 90)
        patches.append((a0, a0 + w, y0, y0 + rnd.uniform(50, 110)))
    crazed = [(rnd.uniform(0, L), rnd.uniform(120, 300), rnd.choice((-1, 1))) for _ in range(3)]
    return cracks, holes, patches, crazed


def road_sheet(size=1024, seed=900):
    """One stretch of road (a whole long piece along, the whole width across): the asphalt old and sun-greyed with its
    stones showing, darker smoother bands where the wheels ran, cracks right across (some sealed with tar), a crack down
    the middle, crazed asphalt in the worst stretches of the wheel paths, holes with gravel and dirt in them, patches cut
    square and filled with newer tar, a faded double centre line and edge lines worn mostly away, oil down the lanes,
    sand blown in toward the edges and weeds in the cracks there; its edge breaking up into gravel, the verge."""
    c = tp.Canvas(size, size)
    big, mid, fine, grain, wob, chip, oil, weed = (tp.Noise(seed + k, p) for k, p in enumerate((4, 16, 128, 256, 32, 64, 12, 48)))
    cracks, holes, patches, crazed = _road_marks(seed)
    L = ROAD_SHEET_LONG
    ku, kv = L / size, 2 * DEEP / size

    def fn(x, y):
        a, yy = x * ku, y * kv - DEEP           # (along and across, in game units)
        ay = abs(yy)
        u, v = x / size, y / size
        f = fine.at(u * 128, v * 128)
        g = _hash(x, y, seed + 7)                 # (its stones: a pixel each, about one unit)
        wear = big.at(u * 4, v * 4) * 0.6 + mid.at(u * 16, v * 16) * 0.4
        col = tp._mix(ASPH, ASPH_OLD, 0.3 + 0.55 * wear)
        h = 0.45 + 0.08 * f
        if g > 0.8 - 0.2 * wear:                  # (where the tar has worn off them, more where it's oldest)
            col, h = tp._mix(col, (150, 146, 136), 0.35), h + 0.1
        elif g < 0.16:
            col, h = tp._shade(col, 0.86), h - 0.05
        col = tp._shade(col, 0.9 + 0.2 * f)
        dw = min(abs(ay - w) for w in WHEELS)
        if ay < ASPHALT and dw < RUT_WIDE:        # (where the wheels ran: darker, smoother)
            t = 1 - dw / RUT_WIDE
            col, h = tp._mix(col, tp._shade(ASPH, 0.95 + 0.1 * f), 0.35 * t), h - 0.05 * t
        if ay < ASPHALT:
            o = oil.at(u * 12, v * 12)
            if abs(ay - 143) < 30 and o > 0.62:
                col = tp._mix(col, (34, 33, 32), min(0.45, (o - 0.62) * 3) * (1 - abs(ay - 143) / 30))
        patched = False
        for a0, a1, y0, y1 in patches:
            da = _around(a, (a0 + a1) / 2, L)
            half = (a1 - a0) / 2
            if abs(da) < half and y0 < yy < y1:
                edge = min(half - abs(da), yy - y0, y1 - yy)
                patched = True
                col = tp._mix(col, tp._shade(ASPH_NEW, 0.95 + 0.15 * f), 0.6 - 0.25 * wear)
                h = 0.48 + 0.03 * f
                if edge < 2.2:                    # (the cut, its seam filled)
                    col, h = tp._shade(ASPH_NEW, 0.8), 0.38
        line = False
        if not patched:
            # (the double centre line and the edge lines: paint flaked off by chip, worn off by wear)
            p = chip.at(u * 64, v * 64)
            if abs(ay - 7) < 2.4 and p > 0.3 + 0.25 * wear:
                col, h, line = tp._mix(col, tp._shade(LINE, 0.85 + 0.2 * f), 0.7 - 0.35 * wear), h + 0.05, True
            elif abs(ay - (ASPHALT - 16)) < 2.6 and p > 0.55 + 0.2 * wear:
                col, h, line = tp._mix(col, tp._shade(WHITE, 0.85 + 0.2 * f), 0.6 - 0.3 * wear), h + 0.05, True
        crack = 0.0                               # (how dark a crack here: 0 none)
        w = wob.at(u * 32, v * 32) - 0.5
        if ay < ASPHALT + 10:
            for a0, y0, y1, sealed in cracks:
                if y0 < yy < y1:
                    d = abs(_around(a, a0 + 26 * w + 9 * math.sin(yy / 23.0), L))
                    if sealed and d < 3.2:
                        col, h = tp._mix(col, (30, 30, 29), 0.85), 0.47     # (tar run into it, glossy and a little proud)
                    elif d < 1.4:
                        crack = max(crack, 1 - d / 1.4)
            if abs(yy - 9 - 7 * w) < 1.2 and mid.at(u * 16 + 9, v * 16) > 0.42:
                crack = max(crack, 1 - abs(yy - 9 - 7 * w) / 1.2)
            for a0, span, side in crazed:
                if yy * side > 0 and dw < 18 and abs(_around(a, a0, L)) < span / 2:
                    d1, d2, _, _o = _cells(a / 18.0, yy / 18.0, seed + 40, int(L / 18))
                    if d2 - d1 < 0.07:
                        crack = max(crack, 1 - (d2 - d1) / 0.07)
        if crack > 0 and not line:
            col, h = tp._shade(col, 1 - 0.45 * crack), h - 0.3 * crack
            if ay > ASPHALT * 0.72 and weed.at(u * 48, v * 48) > 0.62:
                col = tp._mix(col, tp._shade(WEED, 0.8 + 0.4 * f), 0.8)           # (grass come up in it)
        for a0, y0, r in holes:
            da = _around(a, a0, L)
            dist = math.hypot(da, yy - y0)
            d = dist / (r * (1 + 0.5 * (wob.at(u * 32 + 5, v * 32) - 0.5)))
            if d < 1.0:                           # (a hole: gravel and dirt in its bottom, the side away from the sun dark)
                bottom = tp._mix(tp._mix(tp._shade(GRAVEL, 0.5 + 0.5 * g), tp._shade(DIRT, 0.7), mid.at(u * 16, v * 16)), (60, 54, 46), 0.35)
                lit = 0.8 + 0.35 * ((da + (yy - y0)) * 0.7 / max(1.0, dist)) * _smooth((d - 0.3) / 0.7)
                col = tp._shade(tp._mix(bottom, (40, 37, 32), _smooth((d - 0.55) / 0.45) * 0.8), lit)
                h = 0.12 + 0.12 * g * (1 - d)
            elif d < 1.3 and g > 0.25:            # (its edge crumbling)
                col, h = tp._shade(col, 1.04 + 0.12 * g), 0.55 + 0.1 * g
        sand = _smooth((ay - ASPHALT * 0.55) / (ASPHALT * 0.5)) * (0.35 + 0.65 * mid.at(u * 16 + 3, v * 16))
        sand *= 0.6 + 0.4 * big.at(u * 4 + 2, v * 4)
        col = tp._mix(col, tp._shade(SAND, 0.85 + 0.25 * f), 0.7 * sand)
        if 0.5 < sand and g > 0.8:
            col = tp._mix(col, (96, 80, 50), 0.5)        # (a dry leaf, a scrap)
        grav = tp._mix(GRAVEL, DIRT, mid.at(u * 16 + 11, v * 16)) if f > 0.45 else tp._shade(GRAVEL, 0.7 + 0.5 * f)
        d1, d2, cid, _o = _cells(a / 7.0, yy / 7.0, seed + 60, int(L / 7))
        grav = tp._shade(grav, 0.78 + 0.36 * _hash(cid[0], cid[1], seed + 61)) if d2 - d1 > 0.06 else tp._shade(DIRT, 0.78)
        grav = tp._shade(grav, 0.88 + 0.24 * f)
        edge = (ay - (ASPHALT - 18)) / 34.0         # (0 inside the asphalt, 1 out in the gravel; ragged by noise)
        if edge <= 0:
            return col, h
        broke = edge + 0.55 * (mid.at(u * 16 + 5, v * 16 + 2) - 0.5) + 0.25 * (f - 0.5)
        if broke < 0.5:
            return tp._shade(col, 0.92), h + 0.05
        hg = 0.3 + 0.35 * (d2 - d1)
        if broke < 0.62:                          # (the broken edge itself, dark)
            return tp._shade(grav, 0.6), 0.2
        if ay < VERGE and _hash(cid[0], cid[1], seed + 62) > 0.86:
            return tp._shade(col, 0.95), 0.55          # (a piece broken off the asphalt, lying in the gravel)
        out = tp._mix(grav, tp._shade(DIRT, 0.9 + 0.2 * f), _smooth((ay - VERGE) / (DEEP - VERGE)))
        wd = weed.at(u * 48 + 20, v * 48)
        if ay > ASPHALT + 8 and wd > 0.6:
            out = tp._mix(out, tp._shade(WEED, 0.7 + 0.5 * f), min(0.85, (wd - 0.6) * 4))   # (weeds along the verge)
            hg += 0.15
        return out, hg
    c.paint(fn)
    return c


GRIT = 110             # stones across the heap ground's quarter (it spans a whole heap, ~1,200 units: stones of ~11, some of ~33)
STONES = ((0.4, (150, 146, 138)), (0.56, (176, 172, 162)), (0.66, (138, 82, 64)), (0.72, (112, 66, 52)), (0.8, (70, 68, 64)),
          (0.9, (168, 150, 116)), (1.0, (122, 114, 100)))       # (share up to, colour: concrete, pale concrete, brick, dark brick, tar, sand stone, dusty)
GLINTS = ((84, 150, 132), (210, 214, 206), (64, 110, 70), (176, 92, 70))   # (glass, tile, bottle glass, painted bits)


def heap_sheet(size=1024, seed=920):
    """Quarters and smaller: the heap's ground (stones of concrete, brick and tar in grit, dust settled over them, bits of
    glass and tile, dirt and weeds toward the outside, which is the skirt), broken concrete (aggregate, cracks, old
    paint, rust where its rods were), brick (courses, mortar, a few gone, soot), painted siding peeling, planks, tin,
    stucco over brick, and the rough inside of anything broken."""
    c = tp.Canvas(size, size)
    big, mid, fine, cell, cell2, peel = (tp.Noise(seed + k, p) for k, p in enumerate((6, 24, 128, 128, 128, 64)))
    k = 1.0 / size

    def ground(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k)
        r = math.hypot(u - 0.5, v - 0.5) * 2           # (0 in the middle of the quarter, 1 at its edge: the skirt)
        # stones of two sizes, the bigger ones in some places only
        d1, d2, cid, off = _cells(u * GRIT, v * GRIT, seed + 10)
        b1, b2, bid, boff = _cells(u * GRIT / 3, v * GRIT / 3, seed + 20)
        if _hash(bid[0], bid[1], seed + 21) < 0.22:
            d1, d2, cid, off, scale = b1, b2, (bid[0] + 9999, bid[1]), boff, 0.6
        else:
            scale = 1.0
        pick = _hash(cid[0], cid[1], seed + 11)
        col = next(cl for share, cl in STONES if pick <= share)
        col = tp._mix(col, (140, 132, 120), 0.3)
        gap = (d2 - d1) * scale
        if scale == 1.0 and _hash(cid[0], cid[1], seed + 14) < 0.45:
            col, h, gap = tp._shade((136, 126, 110), 0.85 + 0.3 * f), 0.3 + 0.1 * f, 1.0         # (no stone here: grit and dust)
        elif gap < 0.07:
            col, h = tp._shade((112, 102, 88), 0.8 + 0.3 * f), 0.15                               # (grit between)
        else:
            dome = min(1.0, gap / 0.45)
            col = tp._shade(col, 0.8 + 0.22 * dome - 0.45 * (off[0] + off[1]) + 0.12 * (f - 0.5))   # (lit from one side)
            h = 0.35 + 0.45 * dome
            if _hash(cid[0], cid[1], seed + 12) > 0.965:
                col = GLINTS[int(_hash(cid[0], cid[1], seed + 13) * len(GLINTS)) % len(GLINTS)]   # (glass, tile)
        dust = 0.3 + 0.45 * mid.at(u * 24, v * 24)
        col = tp._mix(col, (150, 138, 118), dust * (0.55 if gap > 0.07 else 0.45))
        dirt = _smooth((r - 0.62) / 0.3)
        out = tp._mix(col, tp._shade(DIRT, 0.85 + 0.3 * f), dirt * 0.85)
        if dirt > 0.4 and big.at(u * 6 + 3, v * 6) > 0.55 and f > 0.5:
            out = tp._mix(out, tp._shade(WEED, 0.7 + 0.5 * f), 0.7)                               # (weeds at its foot)
        return out, h * (1 - dirt) + 0.4 * dirt

    def concrete(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k)
        col = tp._shade((176, 170, 158), 0.82 + 0.2 * big.at(u * 6, v * 6) + 0.2 * (f - 0.5))
        h = 0.5 + 0.08 * f
        if cell.at(u * 100, v * 100) > 0.72:
            col, h = tp._shade(col, 0.76), 0.6                                                   # (aggregate)
        if v < 0.4 + 0.1 * mid.at(u * 24, 3) and peel.at(u * 64, v * 64) > 0.4:
            col = tp._mix(col, tp._shade((196, 182, 150), 0.9 + 0.2 * f), 0.7)                   # (old paint, flaking)
        d1, d2, _, _o = _cells(u * 2.2, v * 2.2, seed + 30)
        if d2 - d1 < 0.014:
            col, h = tp._shade(col, 0.64), 0.3                                                    # (a crack)
        e = min(u, v, 1 - u, 1 - v)
        if e < 0.1 + 0.06 * mid.at(u * 24, v * 24):
            col, h = tp._shade(col, 0.62 + 2.0 * e), 0.35                                        # (a broken edge)
        for ru in (0.27, 0.71):
            du = u - ru - 0.01 * (mid.at(3, v * 24) - 0.5)
            if abs(du) < 0.006 and peel.at(ru * 64, v * 16) > 0.55:
                col, h = tp._mix(col, (96, 52, 30), 0.8), 0.25                                   # (a rod showing)
            elif abs(du) < 0.02 and peel.at(ru * 64, v * 16 - 1) > 0.5:
                col = tp._mix(col, (138, 84, 50), 0.35 * (1 - abs(du) / 0.02))                   # (its rust run down)
        return col, h

    def brick(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k)
        rows = 6
        row = int(v * rows)
        b = (u * 4 + (0.5 if row % 2 else 0.0)) % 1.0
        bv = (v * rows) % 1.0
        if b < 0.05 or bv < 0.12:
            return tp._shade((150, 142, 128), 0.75 + 0.35 * f), 0.3                              # (mortar)
        bi = int(u * 4 + (0.5 if row % 2 else 0))
        tone = _hash(bi, row, seed + 40)
        col = tp._shade(tp._mix((154, 70, 48), (104, 54, 44), tone), 0.82 + 0.3 * f)
        if tone > 0.95:
            return tp._shade(col, 0.55), 0.15                                                    # (one gone)
        if min(b, 1 - b, bv - 0.12, 1 - bv) < 0.04:
            col = tp._shade(col, 0.85)
        return tp._mix(col, (40, 34, 30), 0.35 * max(0.0, mid.at(u * 6, v * 6) - 0.5) * 2), 0.6 + 0.1 * f

    def siding(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k * 0.2)
        board = (v * 6) % 1.0
        if board < 0.07:
            return (44, 40, 34), 0.2
        wood = tp._shade((132, 118, 96), 0.75 + 0.4 * f)
        paint = tp._mix((92, 150, 140), (190, 196, 176), big.at(u * 6, v * 6) * 0.6)       # (sea green, faded nearly white)
        p = peel.at(u * 64, v * 64)
        if p < 0.38:
            return wood, 0.38
        return tp._shade(paint, 0.85 + 0.2 * f - 0.25 * board * (1 - board)), 0.45 + 0.1 * (board < 0.5)

    def wood(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k * 0.15)
        plank = int(v * 4)
        if (v * 4) % 1.0 < 0.06:
            return (40, 32, 26), 0.2
        col = tp._shade(tp._mix((136, 116, 90), (104, 96, 86), _hash(plank, 0, seed + 50)), 0.75 + 0.4 * f)
        if abs(((u * 6 + _hash(plank, 1, seed)) % 1.0) - 0.5) < 0.012 and abs(((v * 4) % 1.0) - 0.5) < 0.05:
            col = (52, 40, 32)                                                                   # (a nail hole)
        return col, 0.45 + 0.15 * f

    def tin(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k)
        ridge = 0.5 + 0.5 * math.cos(u * math.tau * 10)
        rust = big.at(u * 6 + 4, v * 6) * 0.7 + 0.3 * mid.at(u * 24, v * 24)
        col = tp._mix((136, 138, 134), (124, 70, 40), _smooth((rust - 0.35) / 0.3))
        if v > 0.8 and rust > 0.4:
            col = tp._mix(col, (90, 50, 30), 0.5)                                                # (rusted through at its foot)
        return tp._shade(col, 0.7 + 0.35 * ridge + 0.1 * f), 0.3 + 0.4 * ridge

    def stucco(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k)
        p = peel.at(u * 16 + 7, v * 16)
        if p < 0.3 + 0.2 * _smooth(min(u, v, 1 - u, 1 - v) * -8 + 1):
            return brick(u, v, x, y)                                                             # (fallen off: the brick behind)
        col = tp._mix((222, 176, 150), (216, 206, 178), big.at(u * 6, v * 6))                     # (pink and cream, sun-faded)
        col = tp._mix(col, (98, 92, 80), 0.3 * max(0.0, mid.at(u * 24, v * 24 + 5) - 0.55) * 2)  # (grime)
        return tp._shade(col, 0.82 + 0.25 * f), 0.55 + 0.08 * f

    def rough(u, v, x, y):
        f = fine.at(x * 128 * k, y * 128 * k)
        d1, d2, cid, _o = _cells(u * 22, v * 22, seed + 70)
        col = tp._shade((150, 144, 132), 0.6 + 0.5 * _hash(cid[0], cid[1], seed + 71) + 0.2 * (f - 0.5))
        return (tp._shade(col, 0.78), 0.25) if d2 - d1 < 0.06 else (col, 0.4 + 0.4 * min(1.0, (d2 - d1) / 0.4))

    regions = [(name, Q[name]) for name in ('ground', 'concrete', 'brick', 'siding', 'wood', 'tin', 'stucco', 'rough')]
    paint = {'ground': ground, 'concrete': concrete, 'brick': brick, 'siding': siding, 'wood': wood, 'tin': tin,
             'stucco': stucco, 'rough': rough}

    def fn(x, y):
        u, v = x * k, y * k
        for name, (u0, v0, u1, v1) in regions:
            if u0 <= u < u1 and v0 <= v < v1:
                return paint[name]((u - u0) / (u1 - u0), (v - v0) / (v1 - v0), x, y)
        return (128, 128, 128), 0.5
    c.paint(fn)
    return c


modelsets.TEXTURES.update({
    'rubble/road': lambda: road_sheet(),
    'rubble/heap': lambda: heap_sheet(),
})


# ---------- the pieces ----------
def _road(name, **kw):
    return lambda: road_desc(name, **kw)


def _heap(name, *a, **kw):
    return lambda: heap_desc(name, *a, **kw)[0]


ROADS = {       # piece: (its asphalt's x0, x1, ends with flaps, the game piece whose frame it has)
    'road_long': (-HALF_LONG, HALF_LONG, (True, True), 'WastelandRoadStraightLong'),
    'road_long_b': (-HALF_LONG, HALF_LONG, (True, True), 'WastelandRoadStraightLongB'),
    'road_cap_r': (-96.0, CAP_END, (True, True), 'WastelandRoadEndCapR'),
}
HEAPS = {       # piece: (rx, ry, height, seed, chunks)
    'heap_a': (330, 400, 135, 11, 11),
    'heap_b': (360, 380, 120, 12, 10),
    'heap_low_a': (220, 320, 115, 13, 8),
    'heap_low_b': (240, 300, 100, 14, 7),
    'edging': (74, 240, 60, 15, 4),
    'heap_c': (380, 340, 150, 16, 13),
    'heap_d': (300, 420, 110, 17, 12),
    'heap_low_c': (260, 250, 90, 18, 8),
}

_P = {
    'road_long': {'label': 'Road, long (no edges)', 'edid': 'FOLabRoadLong', 'file': 'road_long',
                  'describe': _road('FOLabRoadLong', x0=-HALF_LONG, x1=HALF_LONG)},
    'road_long_b': {'label': 'Road, long, worn (no edges)', 'edid': 'FOLabRoadLongB', 'file': 'road_long_b',
                    'describe': _road('FOLabRoadLongB', x0=-HALF_LONG, x1=HALF_LONG, shift=0.37, flip=True)},
    'road_cap_r': {'label': 'Road end (no edges)', 'edid': 'FOLabRoadEnd', 'file': 'road_end',
                   'describe': _road('FOLabRoadEnd', x0=-96.0, x1=CAP_END, shift=0.61)},
    'heap_a': {'label': 'Rubble heap', 'edid': 'FOLabRubbleHeapA', 'file': 'heap_a', 'describe': _heap('FOLabRubbleHeapA', 330, 400, 135, 11, 11)},
    'heap_b': {'label': 'Rubble heap, round', 'edid': 'FOLabRubbleHeapB', 'file': 'heap_b', 'describe': _heap('FOLabRubbleHeapB', 360, 380, 120, 12, 10)},
    'heap_low_a': {'label': 'Rubble heap, small', 'edid': 'FOLabRubbleHeapLowA', 'file': 'heap_low_a',
                   'describe': _heap('FOLabRubbleHeapLowA', 220, 320, 115, 13, 8)},
    'heap_low_b': {'label': 'Rubble heap, small, planks', 'edid': 'FOLabRubbleHeapLowB', 'file': 'heap_low_b',
                   'describe': _heap('FOLabRubbleHeapLowB', 240, 300, 100, 14, 7, kinds=('wood', 'concrete', 'tin', 'wood', 'brick'))},
    'heap_c': {'label': 'Rubble heap, a fallen wall', 'edid': 'FOLabRubbleHeapC', 'file': 'heap_c',
               'describe': _heap('FOLabRubbleHeapC', 380, 340, 150, 16, 13, kinds=('stucco', 'brick', 'stucco', 'concrete', 'brick', 'wood'))},
    'heap_d': {'label': 'Rubble heap, a fallen house', 'edid': 'FOLabRubbleHeapD', 'file': 'heap_d',
               'describe': _heap('FOLabRubbleHeapD', 300, 420, 110, 17, 12, kinds=('siding', 'wood', 'tin', 'siding', 'wood', 'concrete'))},
    'heap_low_c': {'label': 'Rubble heap, small, concrete', 'edid': 'FOLabRubbleHeapLowC', 'file': 'heap_low_c',
                   'describe': _heap('FOLabRubbleHeapLowC', 260, 250, 90, 18, 8, kinds=('concrete', 'concrete', 'stucco', 'tin'))},
    'edging': {'label': 'Rubble along a wall', 'edid': 'FOLabRubbleEdging', 'file': 'edging',
               'describe': _heap('FOLabRubbleEdging', 74, 240, 60, 15, 4, kinds=('concrete', 'brick'))},
    'slab': {'label': 'Broken slab in the ground', 'edid': 'FOLabRubbleSlab', 'file': 'slab', 'describe': lambda: slab_desc('FOLabRubbleSlab')[0]},
}
for _k, _v in _P.items():
    _v['set'] = SET
modelsets.PIECES.update(_P)

# game editor ID: the pieces that stand in for it (several: taken in turn by the ref, so neighbours differ)
REPLACES = {
    'WastelandRoadStraightLong': ('road_long',),
    'WastelandRoadStraightLongB': ('road_long_b',),
    'WastelandRoadEndCapR': ('road_cap_r',),
    'RubblePile02': ('heap_a', 'heap_b', 'heap_c', 'heap_d'),
    'RubblePile04': ('heap_low_a', 'heap_low_b', 'heap_low_c'),
    'SuburbanRubblePileCanyon01': ('heap_low_a', 'heap_low_b', 'heap_low_c'),
    'SuburbanRubblePile01bLiteLitter': ('heap_low_b',),
    'RubblePileEdging01': ('edging',),
    'ConcreteSlab01': ('slab',),
}
# (WastelandRoadEndCapL is the right cap turned a quarter: the swap turns the ref, `CAP_L_TURN`)
CAP_L = 'WastelandRoadEndCapL'
CAP_L_TURN = -math.pi / 2


def is_road(piece):
    return piece in ROADS


_feet = {}


def foot(piece):
    """(rim, tips, height) of a piece in its own frame, for seating and the float check."""
    if piece not in _feet:
        if piece in ROADS:
            x0, x1, ends, _g = ROADS[piece]
            rim, tips = road_foot(x0, x1, ends)
            _feet[piece] = (rim, tips, CROWN)
        elif piece == 'slab':
            _d, hp = slab_desc('x')
            # (the slab's box: its underside's corners are its rim, its skirt the ring round it)
            rim = [(sx * 92, sy * 119, -9.0) for sx in (-1, 0, 1) for sy in (-1, 0, 1) if sx or sy]
            _feet[piece] = (rim, heap_foot(hp)[1], 24.0)
        else:
            rx, ry, h, seed, _c = HEAPS[piece]
            hp = Heap(rx, ry, h, seed)
            rim, tips = heap_foot(hp)
            _feet[piece] = (rim, tips, h)
    return _feet[piece]


def piece_of_edid(edid):
    for k, v in _P.items():
        if v['edid'] == edid:
            return k
    return None
