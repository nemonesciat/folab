"""Island things in place of the Mojave's commonest (the user, overnight 21 Nov 2026: "more custom assets", "more items that
add to the experience", "the world needs a lot more activity"). FOLab's own pieces (modelsets, set 'island':
meshes\\folab\\island, textures\\folab\\island), pictures drawn in code, so a mod with them can be handed round.

Counted over Waikiki's outdoor cells (21 Nov 2026, 286,000 things, 124,000 of them the game's): after the plants, what
shows most that reads as Nevada is crates (1,400), lawn chairs (1,092), red canyon rocks (2,300 with Honest Hearts'),
Bitter Springs' clotheslines (459), barbecue grills (433) and refugee and Legion tents (240). Each piece here is made in
the frame of the game piece it stands in for (`REPLACES`: same origin, same footprint, same height within a little), so
a swap is the ref's base and nothing else; `LIFT` is how far a ref is raised where the game's frame differs (Honest
Hearts' canyon rocks stand on their origin, the base game's are sunk half).

- `fruit_crates` (CrateGenericNV, 108 square, 157 high): pineapple crates stacked two, two and one, slatted, stencilled
  "KAHUKU PINES", fruit showing through the slats of the top one.
- `cargo_crate` (CrateLarge01): a big slatted shipping crate, stencilled "HONOLULU" and "THIS SIDE UP", rope round it.
- `beach_chair` (dlc04lawnchair01: origin at half its height): a folding wooden beach chair, a striped canvas sling.
- `clothesline` (VBitterSpringsClotheslineShort: along +x from 0 to 700): two bamboo poles and a line, two aloha shirts,
  a pareo, a towel and board shorts pegged on it. Cloth is solid, not cut-out.
- `huli_grill` (GrillBBQDirty): an oil drum cut lengthwise on pipe legs, the lid open, a grate of chicken over glowing
  coals: the island's roadside huli-huli.
- `lava_rock_a/b/c` (the base game's NVNRockCanyon06/13/12 and Honest Hearts' NVDLC02RockCanyon06/13/12): rough black
  basalt, pitted, a little red where it weathers, lichen on top.
- `tarp_shelter` (NVBSRefugeeTent, CLSoldiersTent01): a bamboo frame, a faded blue tarp over it pegged down one side
  and propped up on the other, lauhala mats on the floor, a crate and a lantern.

Front towards -y, standing on z 0 (but the chair, whose game piece has its origin at its middle). Far models only for
what is big enough to be seen from the next cell (the shelter); solid, no see-through cards."""
import math
import random

import modelsets
import texpaint as tp
from modelsets import look

SET = 'island'
TARP = (70, 120, 168)               # (a blue tarp, faded by the sun)
SLAT = (196, 170, 126)              # (crate pine, new-ish)
BASALT = (44, 42, 42)


# ---------- pictures ----------

def slats(size=256, seed=901, colour=SLAT, count=4, gap=0.18, words=(), ink=(52, 70, 92)):
    """Crate slats running across, gaps between showing dark, grain, a stencilled word or two on them."""
    c = tp.Canvas(size, size)
    big, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 64)
    rnd = random.Random(seed)
    tint = [rnd.uniform(-0.08, 0.08) for _ in range(count)]
    wide = size / float(count)

    def fn(x, y):
        k = int(y / wide) % count
        v = (y - k * wide) / wide
        g = fine.at(x * 64.0 / size / 6, y * 64.0 / size * 2)
        col = tp._shade(colour, (1 + tint[k]) * (0.86 + 0.2 * g) * (0.9 + 0.2 * big.at(x * 8.0 / size, y * 8.0 / size)))
        if v > 1 - gap:
            return tp._shade(col, 0.25), 0.15
        if v > 1 - gap - 0.04 or v < 0.03:
            return tp._shade(col, 0.8), 0.45
        return col, 0.55 + 0.05 * g
    c.paint(fn)
    worn = lambda x, y: 0.55 + 0.45 * big.at(x * 8.0 / size + 3.3, y * 8.0 / size)
    y = size * 0.18
    for line in words:
        high = size * (0.16 if len(line) < 9 else 0.11)
        high = min(high, high * size * 0.86 / c.text_wide(line, high))      # (fits across)
        w = c.text_wide(line, high)
        c.text(line, (size - w) / 2, y, high, ink, worn=worn)
        y += high * 1.7
    return c


def aloha(size=256, seed=911, ground=(36, 92, 150), bloom=(244, 236, 220), leaf=(40, 120, 92), flowers=9):
    """An aloha print: hibiscus with five round petals and a dark eye, broad leaves behind them, on a ground colour.
    Repeats both ways."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 64)
    c.paint(lambda x, y: (tp._shade(ground, 0.94 + 0.1 * fine.at(x * 64.0 / size, y * 64.0 / size)), 0.5))
    rnd = random.Random(seed)
    for _ in range(flowers * 2):
        x, y, a = rnd.uniform(0, size), rnd.uniform(0, size), rnd.uniform(0, 2 * math.pi)
        ln = size * rnd.uniform(0.09, 0.14)
        for dx in (-size, 0, size):
            for dy in (-size, 0, size):
                c.blade((x + dx, y + dy), (x + dx + math.cos(a) * ln, y + dy + math.sin(a) * ln), size * 0.05, leaf, tip=0.2, bend=0.15)
    for _ in range(flowers):
        x, y, r = rnd.uniform(0, size), rnd.uniform(0, size), size * rnd.uniform(0.045, 0.065)
        a0 = rnd.uniform(0, 2 * math.pi)
        for dx in (-size, 0, size):
            for dy in (-size, 0, size):
                for k in range(5):
                    a = a0 + k * 2 * math.pi / 5
                    px, py = x + dx + math.cos(a) * r, y + dy + math.sin(a) * r
                    c.line((x + dx, y + dy), (px, py), r * 1.25, bloom)
                c.line((x + dx, y + dy), (x + dx + 0.1, y + dy), r * 0.45, tp._shade(bloom, 0.45))
    return c


def stripes(a, b, size=128, stripes=6, seed=921):
    return tp.cloth_stripes(a, b, size=size, stripes=stripes, seed=seed)


def tarp(size=256, seed=931, colour=TARP):
    """A plastic tarp, sun-faded paler towards its edges and along its folds, grommets along one edge, dirt."""
    c = tp.Canvas(size, size)
    big, fine = tp.Noise(seed, 6), tp.Noise(seed + 1, 64)

    def fn(x, y):
        fold = abs(math.sin(x * math.pi * 3.0 / size)) ** 8
        sun = 0.25 * big.at(x * 6.0 / size, y * 6.0 / size) + 0.2 * fold
        col = tp._mix(tp._shade(colour, 0.92 + 0.12 * fine.at(x * 64.0 / size, y * 64.0 / size)), (196, 204, 206), sun)
        weave = 0.5 + 0.5 * math.sin(x * 1.7) * math.sin(y * 1.7)
        if y < size * 0.04 and int(x / (size / 8.0)) * (size / 8.0) + size / 16.0 - 4 < x < int(x / (size / 8.0)) * (size / 8.0) + size / 16.0 + 4:
            return (150, 150, 140), 0.7                  # (a grommet)
        return tp._shade(col, 0.96 + 0.06 * weave), 0.5 + 0.03 * weave
    c.paint(fn)
    return c


def basalt(size=256, seed=941):
    """Rough black basalt: pitted (vesicles), grey where it's worn, rust-red where it weathers, pale lichen."""
    c = tp.Canvas(size, size)
    big, mid, fine = tp.Noise(seed, 6), tp.Noise(seed + 1, 24), tp.Noise(seed + 2, 64)
    rnd = random.Random(seed)
    pits = [(rnd.uniform(0, size), rnd.uniform(0, size), rnd.uniform(1.0, 3.5)) for _ in range(int(size * size / 260))]

    def fn(x, y):
        g = fine.at(x * 64.0 / size, y * 64.0 / size)
        m = mid.at(x * 24.0 / size, y * 24.0 / size)
        b = big.at(x * 6.0 / size, y * 6.0 / size)
        col = tp._shade(BASALT, 0.75 + 0.55 * m * (0.7 + 0.6 * g))
        if b > 0.68:
            col = tp._mix(col, (112, 62, 44), (b - 0.68) * 2.2)       # (weathered red)
        if b < 0.22 and g > 0.55:
            col = tp._mix(col, (150, 156, 132), 0.55)                 # (lichen)
        return col, 0.35 + 0.35 * m + 0.1 * g
    c.paint(fn)
    w = c.w
    for px, py, r in pits:
        for y in range(int(py - r), int(py + r) + 1):
            for x in range(int(px - r), int(px + r) + 1):
                if (x - px) ** 2 + (y - py) ** 2 <= r * r:
                    i = (y % size) * w + (x % size)
                    c.rgb[i] = tp._shade(c.rgb[i], 0.45)
                    c.ht[i] = 0.1
    return c


def drum(size=128, seed=951):
    """An oil drum's steel, painted once, now mostly rust and soot."""
    return tp.painted_metal((150, 64, 48), size=size, seed=seed, rust=0.6)


def grate(size=64, seed=961):
    """Chicken halves on a grate, browned and glazed, the grate's bars between."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 32)

    def fn(x, y):
        bar = (x % 8) < 1.5
        g = fine.at(x * 32.0 / size, y * 32.0 / size)
        if bar:
            return (40, 38, 36), 0.6
        cx, cy = (x // 32) * 32 + 16, (y // 32) * 32 + 16
        if math.hypot((x - cx) / 13.0, (y - cy) / 10.0) < 1:
            return tp._shade((176, 92, 40), 0.8 + 0.4 * g), 0.7 + 0.2 * g
        return tp._shade((60, 30, 20), 0.6 + 0.5 * g), 0.2
    c.paint(fn)
    return c


def coals(size=64, seed=971):
    """Glowing coals under ash."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 16)
    c.paint(lambda x, y: ((tp._mix((90, 80, 76), (255, 120, 40), fine.at(x * 16.0 / size, y * 16.0 / size) ** 2)), 0.5))
    return c


def fruit(size=128, seed=981):
    """Pineapples packed tight, seen through the slats: gold scales, dark eyes."""
    return tp.pineapples(size=size, seed=seed)


modelsets.TEXTURES.update({
    'island/crate_kahuku': lambda: slats(seed=901, words=('KAHUKU', 'PINES')),
    'island/crate_plain': lambda: slats(seed=902),
    'island/crate_honolulu': lambda: slats(seed=903, colour=(180, 158, 120), count=5, words=('HONOLULU', 'THIS SIDE UP'), ink=(30, 30, 30)),
    'island/aloha_blue': lambda: aloha(seed=911),
    'island/aloha_red': lambda: aloha(seed=912, ground=(178, 40, 44), bloom=(250, 240, 214), leaf=(32, 96, 70)),
    'island/aloha_yellow': lambda: aloha(seed=913, ground=(236, 190, 70), bloom=(214, 52, 66), leaf=(40, 110, 70), flowers=7),
    'island/pareo': lambda: aloha(seed=914, ground=(232, 120, 60), bloom=(250, 220, 150), leaf=(150, 60, 40), flowers=6),
    'island/towel': lambda: stripes(tp.WHITE, tp.TURQUOISE, seed=921),
    'island/sling': lambda: stripes(tp.CORAL, tp.CREAM, seed=922, stripes=4),
    'island/tarp': lambda: tarp(),
    'island/basalt': lambda: basalt(),
    'island/drum': lambda: drum(),
    'island/grate': lambda: grate(),
    'island/coals': lambda: coals(),
    'island/fruit': lambda: fruit(),
})


def _looks(**more):
    return dict({'wood': look('planks_cream', tile=96), 'bamboo': look('bamboo', tile=40), 'rope': look('waikiki/husk', tile=24),
                 'mat': look('restyle/lauhala', tile=120), 'metal': look('city/rust', tile=64)}, **more)


def _box(P, x0, y0, z0, x1, y1, z1, lk, solid=True, far=False, material='wood', **faces):
    p = {'shape': 'box', 'size': [x1 - x0, y1 - y0, z1 - z0], 'at': [(x0 + x1) / 2.0, (y0 + y1) / 2.0, z0], 'look': lk,
         'solid': solid, 'far': far, 'material': material}
    if faces:
        p['faces'] = faces
    P.append(p)
    return p


def _rod(P, a, b, r, lk, solid=False, sides=6):
    """A round rod from a to b (drawn only, unless solid)."""
    P.append(modelsets.limb(a, b, r, r, lk, sides=sides, solid=solid))


# ---------- crates ----------

def _crate(P, x0, y0, z0, x1, y1, z1, side, end):
    """One slatted crate: slats on its long sides, its ends the stencilled boards, corner posts a little proud."""
    _box(P, x0, y0, z0, x1, y1, z1, side, left=end, right=end, top='lid', bottom=None)
    for x in (x0, x1):
        for y in (y0, y1):
            _box(P, x - 2.5, y - 2.5, z0, x + 2.5, y + 2.5, z1, 'wood', solid=False)


def fruit_crates():
    looks = _looks(side=look('island/crate_plain', tile=54), end=look('island/crate_kahuku', tile=None),
                   lid=look('island/fruit', tile=40), crate=look('island/crate_kahuku'))
    P = []
    for z, rows in ((0, (-1, 1)), (52, (-1, 1))):
        for r in rows:
            _crate(P, -52, r * 27 - 25, z, 52, r * 27 + 25, z + 50, 'side', 'end')
    P.append({'shape': 'box', 'size': [50, 100, 50], 'at': [6, 0, 104], 'turn': [0, 0, 7], 'look': 'side',
              'faces': {'front': 'end', 'back': 'end', 'top': 'lid', 'bottom': None}, 'material': 'wood'})
    return {'name': 'FOLabIslandFruitCrates', 'looks': looks, 'parts': P}


def cargo_crate():
    looks = _looks(side=look('island/crate_honolulu'), plain=look('island/crate_plain', tile=110))
    P = []
    _box(P, -130, -78, 0, 126, 78, 164, 'plain', front='side', back='side')
    X0, X1, Y0, Y1, Z1 = -130, 126, -78, 78, 164
    for x in (X0, X1):                                          # (a frame of battens on its edges, and down the middle)
        for y in (Y0, Y1):
            _box(P, x - 4, y - 4, 0, x + 4, y + 4, Z1 + 2, 'wood', solid=False)
    for y in (Y0, Y1):
        for z in (4, Z1 - 3):
            _box(P, X0 - 4, y - 4, z - 4, X1 + 4, y + 4, z + 4, 'wood', solid=False)
        _box(P, -6, y - 4, 0, 2, y + 4, Z1 + 2, 'wood', solid=False)
    for x in (X0, X1):
        for z in (4, Z1 - 3):
            _box(P, x - 4, Y0 - 4, z - 4, x + 4, Y1 + 4, z + 4, 'wood', solid=False)
    for x in (-70, 64):                                         # (rope over the top and down the long sides)
        _rod(P, (x, -82, 20), (x, -82, 167), 2.2, 'rope')
        _rod(P, (x, -82, 167), (x, 82, 167), 2.2, 'rope')
        _rod(P, (x, 82, 167), (x, 82, 20), 2.2, 'rope')
    return {'name': 'FOLabIslandCargoCrate', 'looks': looks, 'parts': P}


# ---------- a chair, a clothesline, a grill ----------

def beach_chair():
    """Origin at half its height (the game's lawn chair's): it stands from z -33 to 33, faces -y."""
    looks = _looks(sling=look('island/sling', tile=48), frame=look('waikiki/koa', tile=60))
    P = []
    z0 = -33.0
    for x in (-22, 22):
        _rod(P, (x, -22, z0), (x, 18, z0 + 62), 1.8, 'frame', solid=False)     # (back legs up to the top of the back)
        _rod(P, (x, 20, z0), (x, -20, z0 + 30), 1.8, 'frame', solid=False)     # (front legs to the seat's front)
        _rod(P, (x, -24, z0 + 28), (x, 10, z0 + 26), 1.6, 'frame')             # (arm)
    P.append({'shape': 'sheet', 'rows': [[(-20, -20, z0 + 30), (20, -20, z0 + 30)], [(-20, 2, z0 + 18), (20, 2, z0 + 18)],
                                         [(-20, 16, z0 + 56), (20, 16, z0 + 56)]], 'look': 'sling', 'thick': 1.5})
    P.append({'shape': 'solid', 'points': [(-23, -23, z0), (23, -23, z0), (23, 23, z0), (-23, 23, z0),
                                           (-23, -23, z0 + 32), (23, -23, z0 + 32), (23, 23, z0 + 62), (-23, 23, z0 + 62)],
              'faces': [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], 'material': 'wood'})
    return {'name': 'FOLabIslandBeachChair', 'looks': looks, 'parts': P}


def _cloth(P, x, z_top, wide, drop, lk, arms=0.0):
    """Something pegged on the line at (x, z_top): a panel `wide` by `drop`, with sleeves `arms` out each side (a shirt)."""
    _box(P, x - wide / 2, -1.2, z_top - drop, x + wide / 2, 1.2, z_top, lk, solid=False, left=lk, right=lk, top=lk, bottom=lk)
    if arms:
        for s in (-1, 1):
            P.append({'shape': 'box', 'size': [arms, 2.2, wide * 0.32], 'at': [x + s * (wide / 2 + arms / 2 - 3), 0, z_top - wide * 0.4],
                      'turn': [0, s * 28, 0], 'look': lk, 'solid': False})
    for s in (-1, 1):
        _box(P, x + s * wide * 0.35 - 1.2, -2, z_top - 4, x + s * wide * 0.35 + 1.2, 2, z_top + 3, 'wood', solid=False)


def clothesline():
    """Along +x from 0 to 700 (Bitter Springs' line's frame), the line 210 up."""
    looks = _looks(blue=look('island/aloha_blue', tile=60), red=look('island/aloha_red', tile=60),
                   yellow=look('island/aloha_yellow', tile=60), pareo=look('island/pareo', tile=90),
                   towel=look('island/towel', tile=50), shorts=look('island/aloha_blue', tile=40))
    P = []
    for x in (0, 700):
        P.append({'shape': 'cylinder', 'r': 5, 'r2': 4.2, 'h': 230, 'sides': 7, 'at': [x, 0, 0], 'look': 'bamboo', 'material': 'wood'})
        _rod(P, (x, -40, 0), (x, 0, 150), 2.5, 'bamboo')                        # (a prop)
    sag = lambda x: 212 - 14 * math.sin(math.pi * x / 700.0)
    for a, b in ((0, 175), (175, 350), (350, 525), (525, 700)):
        _rod(P, (a, 0, sag(a)), (b, 0, sag(b)), 0.8, 'rope', sides=4)
    for x, wide, drop, lk, arms in ((90, 62, 70, 'blue', 26), (190, 58, 68, 'red', 24), (300, 110, 120, 'pareo', 0),
                                    (420, 70, 110, 'towel', 0), (520, 44, 52, 'shorts', 0), (620, 60, 70, 'yellow', 25)):
        _cloth(P, x, sag(x), wide, drop, lk, arms)
    return {'name': 'FOLabIslandClothesline', 'looks': looks, 'parts': P}


def huli_grill():
    looks = _looks(drum=look('island/drum', tile=80), grate=look('island/grate', tile=32),
                   coals=dict(look('island/coals', tile=32), glow='textures\\effects\\white.dds', glow_mult=2.5))
    P = []
    top = 50.0
    for x in (-28, 28):                                          # (pipe legs, crossed)
        _rod(P, (x, -26, 0), (x, 20, top - 18), 1.8, 'metal', solid=False)
        _rod(P, (x, 26, 0), (x, -20, top - 18), 1.8, 'metal', solid=False)
    # (the drum's lower half, cut lengthwise: a trough lying along x, its ends closed)
    R = 26.0
    arc = [(math.cos(math.pi + math.pi * k / 8.0) * R, math.sin(math.pi + math.pi * k / 8.0) * R) for k in range(9)]
    P.append({'shape': 'sheet', 'rows': [[(x, y, top - 4 + z) for y, z in arc] for x in (-32, 32)], 'look': 'drum', 'thick': 1.5})
    for x in (-32, 32):
        P.append({'shape': 'sheet', 'rows': [[(x, y * 0.02, top - 4 + z * 0.02) for y, z in arc], [(x, y, top - 4 + z) for y, z in arc]],
                  'look': 'drum', 'thick': 1.0})          # (the drum's end, a half disc)
    P.append({'shape': 'solid', 'points': [(-32, -R, top - 4), (32, -R, top - 4), (32, R, top - 4), (-32, R, top - 4),
                                           (-32, -12, top - 4 - R), (32, -12, top - 4 - R), (32, 12, top - 4 - R), (-32, 12, top - 4 - R)],
              'faces': [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]], 'material': 'metal'})
    _box(P, -30, -22, top - 8, 30, 22, top - 6, 'coals', solid=False, front=None, back=None, left=None, right=None, bottom=None)
    _box(P, -30, -22, top - 1, 30, 22, top + 1, 'grate', solid=False, front=None, back=None, left=None, right=None, bottom=None)
    P.append({'shape': 'sheet', 'rows': [[(-32, 24, top), (32, 24, top)], [(-32, 33, top + 10), (32, 33, top + 10)], [(-32, 32, top + 22), (32, 32, top + 22)]],
              'look': 'drum', 'thick': 1.5})                     # (the lid, open behind)
    return {'name': 'FOLabIslandHuliGrill', 'looks': looks, 'parts': P}


# ---------- lava rocks ----------

def lava_rock(name, half_x, half_y, low, high, seed, lumps=5):
    """A boulder of basalt in a box half_x by half_y, from `low` (in the ground) to `high`: rings round a wavy outline,
    rounded over the top, one convex solid round it."""
    rnd = random.Random(seed)
    n, rings = 18, 7
    wob = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0.05, 0.14), k) for k in range(2, 2 + lumps)]

    def rim0(a):
        return 1.0 + sum(w * math.sin(k * a + ph) for ph, w, k in wob)
    most = max(rim0(2 * math.pi * k / 72.0) for k in range(72)) * 1.06

    def rim(a):
        return rim0(a) / most
    top_off = (rnd.uniform(-0.12, 0.12) * half_x, rnd.uniform(-0.12, 0.12) * half_y)
    rows, uvs = [], []
    for j in range(rings + 1):
        t = j / float(rings)                                    # (0 the bottom ring, 1 the top point)
        spread = math.cos(t * math.pi / 2) ** 0.7
        z = low + (high - low) * math.sin(t * math.pi / 2) ** 0.9
        row, uv = [], []
        for k in range(n + 1):
            a = 2 * math.pi * (k % n) / n
            r = rim(a) * spread * (1 + 0.06 * rnd.uniform(-1, 1) * (0 < j < rings))
            row.append((math.cos(a) * half_x * r * 0.97 + top_off[0] * t, math.sin(a) * half_y * r * 0.97 + top_off[1] * t, z))
            uv.append((k / float(n) * 4.0, t * 2.0))
        rows.append(row)
        uvs.append(uv)
    xs = [p[0] for row in rows for p in row]
    ys = [p[1] for row in rows for p in row]
    fx = lambda v: -half_x + (v - min(xs)) / (max(xs) - min(xs)) * 2 * half_x
    fy = lambda v: -half_y + (v - min(ys)) / (max(ys) - min(ys)) * 2 * half_y
    rows = [[(fx(p[0]), fy(p[1]), p[2]) for p in row] for row in rows]      # (to the game rock's footprint exactly)
    rows.reverse()                                              # (from the top down: the field's upper side faces out)
    uvs.reverse()
    pts = [p for row in rows[1:] for p in row[:-1]] + [rows[0][0]]
    hull = _hull_of(pts)
    parts = [{'shape': 'field', 'rows': rows, 'uv': uvs, 'look': 'basalt', 'closed': True},
             {'shape': 'solid', 'points': hull[0], 'faces': hull[1], 'material': 'stone'}]
    return {'name': name, 'looks': {'basalt': look('island/basalt', tile=120)}, 'parts': parts}


def _hull_of(points):
    """A convex solid round the points, few faces: their outline at the bottom, at the middle height and the top point,
    as a prism-like solid (corners anticlockwise from outside)."""
    zs = [p[2] for p in points]
    lo, hi = min(zs), max(zs)
    mid = lo + (hi - lo) * 0.55
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    rx, ry = (max(xs) - min(xs)) / 2 * 0.92, (max(ys) - min(ys)) / 2 * 0.92
    n = 8
    ring = lambda z, f: [(cx + math.cos(2 * math.pi * k / n) * rx * f, cy + math.sin(2 * math.pi * k / n) * ry * f, z) for k in range(n)]
    P = ring(lo, 1.0) + ring(mid, 0.95) + ring(hi - (hi - lo) * 0.12, 0.45)
    F = [list(range(n - 1, -1, -1)), list(range(2 * n, 3 * n))]
    for r in (0, 1):
        for k in range(n):
            a, b = r * n + k, r * n + (k + 1) % n
            F.append([a, b, b + n, a + n])
    return P, F


# ---------- a shelter ----------

def tarp_shelter():
    """620 along x, 370 deep, the ridge 220 up (the refugee tent's and the Legion tent's footprint)."""
    looks = _looks(tarp=look('island/tarp', tile=200), crate=look('island/crate_plain', tile=54),
                   lamp=dict(look('waikiki/lamp_glass'), glow='textures\\effects\\white.dds', glow_mult=2.0))
    P = []
    L, D, H = 300.0, 180.0, 215.0
    for x in (-L, 0, L):                                         # (the frame: posts and a ridge pole)
        P.append({'shape': 'cylinder', 'r': 6, 'r2': 5, 'h': H, 'sides': 7, 'at': [x, 0, 0], 'look': 'bamboo', 'material': 'wood', 'far': True})
        _rod(P, (x, D, 0), (x, D * 0.55, 110), 3.5, 'bamboo')    # (a prop at the open side)
    _rod(P, (-L - 10, 0, H), (L + 10, 0, H), 5, 'bamboo')
    # the tarp: pegged to the ground on the back (+y), propped out at the front (-y)
    rows = []
    for y, z in ((D + 10, 4), (D * 0.6, 90), (0, H + 6), (-D * 0.55, H - 30), (-D * 0.95, H - 70)):
        rows.append([(x, y, z + 6 * math.sin(x / 70.0)) for x in (-L - 20, -L / 2, 0, L / 2, L + 20)])
    P.append({'shape': 'sheet', 'rows': rows[::-1], 'look': 'tarp', 'thick': 2.0, 'far': True})
    for x in (-L, L):                                            # (props for the front's edge)
        P.append({'shape': 'cylinder', 'r': 4, 'h': H - 70, 'sides': 6, 'at': [x, -D * 0.95, 0], 'look': 'bamboo', 'material': 'wood'})
    _box(P, -260, -110, 0, 220, 150, 2, 'mat', solid=False, front='mat', back='mat', left='mat', right='mat')
    _box(P, 180, 60, 0, 240, 110, 46, 'crate', material='wood')
    P.append({'shape': 'cylinder', 'r': 6, 'h': 14, 'sides': 8, 'at': [40, 0, H - 40], 'look': 'lamp', 'solid': False})
    _rod(P, (40, 0, H - 26), (40, 0, H), 0.6, 'rope', sides=4)
    # (the far model: the tarp as one block, the posts)
    P.append({'shape': 'box', 'size': [2 * L + 40, 2 * D * 0.95, H * 0.85], 'at': [0, 0, 0], 'look': 'tarp', 'solid': False, 'far_only': True})
    return {'name': 'FOLabIslandTarpShelter', 'looks': looks, 'parts': P}


# ---------- registered ----------

# ---------- more island things (the second batch: for a later build) ----------

def _frond_dry(size=128, seed=1001):
    """A fallen coconut frond seen flat: a pale midrib down the middle, brown leaflets slanting off it, the ground between
    them dark (solid: it lies on the ground, nothing need show through)."""
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 16)
    c.paint(lambda x, y: (tp._shade((58, 50, 38), 0.8 + 0.4 * n.at(x * 16.0 / size, y * 16.0 / size)), 0.3))
    mid = size / 2.0
    for k in range(0, size, 6):
        for side in (-1, 1):
            c.blade((mid, k), (mid + side * size * 0.46, k - size * 0.18), 4.0, tp._shade((150, 118, 70), 0.85 + 0.3 * n.at(k * 0.3, side)), tip=0.3)
    c.line((mid, 0), (mid, size), 5.0, (196, 170, 120))
    return c


modelsets.TEXTURES.update({'island/frond_dry': lambda: _frond_dry()})


def sleeping_mat():
    """A lauhala sleeping mat on the ground (190 by 80), a rolled pillow at its head, a folded tapa cloth at its foot."""
    looks = _looks(tapa=look('restyle/tapa', tile=60))
    P = []
    _box(P, -40, -95, 0, 40, 95, 2.5, 'mat', solid=False)
    _box(P, -38, -90, 2.5, 38, -70, 3.5, 'mat', solid=False)                     # (the mat's rolled edge)
    P.append({'shape': 'cylinder', 'r': 8, 'h': 60, 'sides': 10, 'turn': [0, 90, 0], 'at': [-30, -78, 9], 'look': 'tapa', 'solid': False})
    _box(P, -32, 50, 2.5, 32, 85, 9, 'tapa', solid=False)
    return {'name': 'FOLabIslandSleepingMat', 'looks': looks, 'parts': P}


def mailbox():
    """A mailbox on a post, the island way: a koa post, an old ammo can painted teal for the box, a painted flag (the
    game's mailbox frame: the box's top at about 100)."""
    looks = _looks(teal=look('waikiki/enamel_teal', tile=40), post=look('waikiki/koa', tile=60), flag=look('waikiki/enamel_cream', tile=20))
    P = [{'shape': 'box', 'size': [8, 8, 78], 'at': [0, -6, 0], 'look': 'post', 'material': 'wood'},
         {'shape': 'box', 'size': [16, 38, 22], 'at': [0, -8, 78], 'look': 'teal', 'material': 'metal'},
         {'shape': 'box', 'size': [2, 4, 18], 'at': [9, 4, 86], 'look': 'flag', 'solid': False},
         {'shape': 'box', 'size': [2, 10, 5], 'at': [9, 9, 99], 'look': 'flag', 'solid': False}]
    return {'name': 'FOLabIslandMailbox', 'looks': looks, 'parts': P}


def palm_litter():
    """What falls under a coconut palm: two dry fronds on the ground, husks."""
    looks = _looks(frond=look('island/frond_dry', tile=None), husk=look('island/coconut', tile=None))
    P = []
    for (x, y, yaw, L) in ((0, 0, 20, 300), (-40, 60, -55, 260)):
        a = math.radians(yaw)
        ca, sa = math.cos(a), math.sin(a)
        rows = []
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            w = 34 * (1 - 0.7 * t)
            along = (t - 0.5) * L
            row = []
            for c2 in (-1.0, 0.0, 1.0):
                lx, ly = c2 * w, along
                row.append((x + lx * ca - ly * sa, y + lx * sa + ly * ca, 1.2 + 2.5 * (1 - abs(c2)) + 3 * math.sin(math.pi * t)))
            rows.append(row)
        P.append({'shape': 'sheet', 'rows': rows, 'look': 'frond', 'thick': 1.0, 'solid': False})
    for (x, y, s) in ((60, -40, 1.0), (85, -10, 0.9), (-70, -30, 1.1)):
        P.append({'shape': 'ball', 'r': 6 * s, 'sides': 8, 'rings': 5, 'scale': [1, 0.9, 1.0], 'at': [x, y, -1], 'look': 'husk', 'solid': False})
    return {'name': 'FOLabIslandPalmLitter', 'looks': looks, 'parts': P}


def board_stand():
    """Three surfboards stood on their tails in a bamboo stand by a door or a shack (an A-frame, a crossbar they lean on)."""
    looks = _looks(red=look('surf_red'), teal_board=look('surf_teal'), pole=look('metal_white', tile=48))
    P = []
    for x in (-70, 70):
        _rod(P, (x, -20, 0), (x, 10, 150), 3.5, 'bamboo')
        _rod(P, (x, 40, 0), (x, 10, 150), 3.5, 'bamboo')
    _rod(P, (-80, 10, 148), (80, 10, 148), 3.5, 'bamboo')
    for k, (x, lk, L) in enumerate(((-44, 'red', 200), (0, 'teal_board', 214), (44, 'red', 186))):
        lean = 76.0 + 2 * k
        a = math.radians(lean)
        P += modelsets.surfboard([x, -30 + math.cos(a) * L / 2, 4 + math.sin(a) * L / 2], [lean, 0, 0], lk, long=L, wide=38, fin='pole')
    P.append({'shape': 'solid', 'points': [(-80, -40, 0), (80, -40, 0), (80, 45, 0), (-80, 45, 0), (-80, -10, 210), (80, -10, 210), (80, 20, 210), (-80, 20, 210)],
              'faces': [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], 'material': 'wood'})
    return {'name': 'FOLabIslandBoardStand', 'looks': looks, 'parts': P}


def net_line():
    """A fishing net hung to dry between two poles, swagged, glass floats caught in it, more floats on the sand."""
    looks = _looks(net=look('waikiki/net', tile=80, alpha=True), glass=look('island/float_glass', tile=None))
    P = []
    for x in (-250, 250):
        P.append({'shape': 'cylinder', 'r': 5, 'r2': 4, 'h': 220, 'sides': 7, 'at': [x, 0, 0], 'look': 'bamboo', 'material': 'wood'})
    rows = []
    for z_top in (205.0, 120.0, 40.0):
        row = []
        for k in range(9):
            x = -250 + 500 * k / 8.0
            sag = 26 * math.sin(math.pi * k / 8.0) * (1 if z_top > 200 else 1.6)
            row.append((x, 3 * math.sin(k), z_top - sag))
        rows.append(row)
    P.append({'shape': 'sheet', 'rows': rows, 'look': 'net', 'thick': 0.5, 'solid': False})
    for (x, z) in ((-120, 150), (60, 140), (170, 88), (-40, 40)):
        P.append({'shape': 'ball', 'r': 8, 'sides': 10, 'rings': 6, 'at': [x, 2, z - 8], 'look': 'glass', 'solid': False})
    for (x, y) in ((-180, -60), (-150, -80), (200, -50)):
        P.append({'shape': 'ball', 'r': 9, 'sides': 10, 'rings': 6, 'at': [x, y, -1], 'look': 'glass', 'solid': False})
    return {'name': 'FOLabIslandNetLine', 'looks': looks, 'parts': P}


def heiau_shrine():
    """A small fishermen's shrine (a ko'a): a low platform of stacked lava stones, a carved post on it, bundles of ti
    leaves and an offering of a coconut at its foot. Walked round, not on."""
    looks = _looks(stone=look('island/basalt', tile=90), face=look('waikiki/tiki'), wood=look('waikiki/tiki_wood', tile=90),
                   ti=look('jungle/ti_green', tile=None), husk=look('island/coconut', tile=None))
    P = []
    rnd = random.Random(1111)
    for half, z in ((120, 0), (95, 30), (70, 58)):
        _box(P, -half, -half * 0.8, z - 4, half, half * 0.8, z + 30, 'stone', material='stone')
        for k in range(14):                                      # (rough stones standing out of each course)
            a = 2 * math.pi * k / 10 + rnd.uniform(-0.2, 0.2)
            P.append({'shape': 'ball', 'r': rnd.uniform(13, 19), 'sides': 7, 'rings': 4, 'scale': [1.3, 1, 0.9],
                      'at': [math.cos(a) * (half + 4), math.sin(a) * (half * 0.8 + 4), z - 4], 'look': 'stone', 'solid': False})
    P.append({'shape': 'box', 'size': [34, 34, 150], 'at': [0, 0, 88], 'look': 'wood', 'faces': {'front': 'face'}, 'material': 'wood'})
    for x in (-40, 40):
        P.append({'shape': 'cone', 'r': 10, 'h': 40, 'sides': 6, 'at': [x, -50, 88], 'look': 'ti', 'solid': False})
    P.append({'shape': 'ball', 'r': 7, 'sides': 8, 'rings': 5, 'at': [0, -48, 88], 'look': 'husk', 'solid': False})
    return {'name': 'FOLabIslandHeiauShrine', 'looks': looks, 'parts': P}


MORE = {'sleeping_mat': ('Lauhala sleeping mat', sleeping_mat), 'mailbox': ('Mailbox, island', mailbox),
        'palm_litter': ('Palm litter (fronds, husks)', palm_litter), 'board_stand': ('Surfboards in a bamboo stand', board_stand),
        'net_line': ('Fishing net drying, floats', net_line), 'heiau_shrine': ("Fishermen's shrine (ko'a)", heiau_shrine)}


# One draw a piece (Waikiki is held back by how many it draws, and the game's crate, grill and shelter are one each): every
# look a piece has, but those that glow, is a region of one picture sheet of its own ('island/sheet_<piece>'), each
# picture shown once over its face rather than repeated (the faces are small, the pictures drawn for them).
SHEET_CELL = 256


def _tex_name(path):
    return next((n for n in modelsets.TEXTURES if modelsets.tex_path(n) == path), None)


def _sheet_grid(n):
    cols = 1 if n <= 1 else 2 if n <= 4 else 4
    rows = 1 if n <= 2 else 2 if n <= 8 else 4
    return cols, rows


def _sheeted(key, fn):
    """A piece's describe function whose looks (but those that glow) all come from one sheet."""
    def describe():
        desc = fn()
        names = [k for k, v in desc['looks'].items() if not v.get('glow')]
        cols, rows = _sheet_grid(len(names))
        looks = dict(desc['looks'])
        for i, k in enumerate(names):
            c, r = i % cols, i // cols
            looks[k] = dict(modelsets.look('island/sheet_' + key), region=(c / float(cols), r / float(rows), (c + 1) / float(cols), (r + 1) / float(rows)))
            if desc['looks'][k].get('alpha'):
                looks[k]['alpha'] = True
        return dict(desc, looks=looks)

    def picture():
        desc = fn()
        names = [k for k, v in desc['looks'].items() if not v.get('glow')]
        cols, rows = _sheet_grid(len(names))
        S = SHEET_CELL
        srcs = [modelsets.TEXTURES[_tex_name(desc['looks'][k]['tex'])]() for k in names]
        see_through = any(getattr(src, 'a', None) for src in srcs)
        out = tp.Canvas(cols * S, rows * S)
        if see_through:                         # (a net or the like among them: the sheet keeps its holes, the rest solid)
            out.a = [1.0] * (out.w * out.h)
        for i, src in enumerate(srcs):
            c, r = i % cols, i // cols
            for y in range(S):
                sy = y * src.h // S
                for x in range(S):
                    j = sy * src.w + x * src.w // S
                    o = (r * S + y) * out.w + c * S + x
                    out.rgb[o], out.ht[o] = src.rgb[j], src.ht[j]
                    if see_through and src.a:
                        out.a[o] = src.a[j]
        return out
    modelsets.TEXTURES['island/sheet_' + key] = picture
    return describe


PIECES = {'fruit_crates': ('Pineapple crates, stacked', fruit_crates), 'cargo_crate': ('Shipping crate, Honolulu', cargo_crate),
          'beach_chair': ('Beach chair, folding', beach_chair), 'clothesline': ('Clothesline, aloha shirts', clothesline),
          'huli_grill': ('Huli-huli grill (oil drum)', huli_grill),
          'lava_rock_a': ('Lava rock, round', lambda: lava_rock('FOLabIslandLavaRockA', 70, 70, -35, 35, 1)),
          'lava_rock_b': ('Lava rock, long', lambda: lava_rock('FOLabIslandLavaRockB', 82, 61, -9, 55, 2)),
          'lava_rock_c': ('Lava rock, low', lambda: lava_rock('FOLabIslandLavaRockC', 67, 45, -9, 31, 3)),
          'tarp_shelter': ('Tarp shelter on bamboo', tarp_shelter)}
PIECES.update(MORE)
ROCKS = ('lava_rock_a', 'lava_rock_b', 'lava_rock_c')      # (one look already, repeated over the rock: left as they are)
for _k, (_label, _fn) in PIECES.items():
    _d = _fn if _k in ROCKS else _sheeted(_k, _fn)
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k, 'describe': _d, 'edid': _fn()['name']})

# the game's editor ID: piece it stands in for
REPLACES = {'CrateGenericNV': 'fruit_crates', 'CrateLarge01': 'cargo_crate', 'dlc04lawnchair01': 'beach_chair',
            'VBitterSpringsClotheslineShort': 'clothesline', 'GrillBBQDirty': 'huli_grill',
            'NVNRockCanyon06': 'lava_rock_a', 'NVNRockCanyon13': 'lava_rock_b', 'NVNRockCanyon12': 'lava_rock_c',
            'NVDLC02RockCanyon06': 'lava_rock_a', 'NVDLC02RockCanyon13': 'lava_rock_b', 'NVDLC02RockCanyon12': 'lava_rock_c',
            'NVBSRefugeeTent': 'tarp_shelter', 'CLSoldiersTent01': 'tarp_shelter'}
# how far a swapped ref goes up, where the game piece stands differently from ours (Honest Hearts' rocks sit on their origin)
LIFT = {'NVDLC02RockCanyon06': 35.0, 'NVDLC02RockCanyon13': 9.0, 'NVDLC02RockCanyon12': 9.0}


# ---------- things to find and use ----------
#
# Each lies loose (nifmake.build_dropped: one box of collision on the clutter layer) and is a record copied from the game's
# own item it is like (`ITEMS`: the game's editor ID), so it sells, weighs and, for food, heals as that does; its name,
# model and numbers are its own. Its picture in the Pip-Boy stays the game item's for now.

modelsets.TEXTURES.update({
    'island/coconut': lambda: tp.husk(size=128, seed=991),
    'island/float_glass': lambda: _glass(),
    'island/tiki_mug': lambda: tp.tiki_face(seed=992),
    'island/uke_top': lambda: tp.koa_hull(size=128, seed=993),
    'island/pine_skin': lambda: _pine_skin(),
})


def _glass(size=64, seed=995):
    """Sea-green glass, a little cloudy, a bright streak."""
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 8)
    c.paint(lambda x, y: (tp._mix((60, 150, 130), (190, 230, 214), 0.5 * n.at(x * 8.0 / size, y * 8.0 / size) + 0.4 * (abs(x - y) < 3)), 0.5))
    return c


def _pine_skin(size=128, seed=996):
    """A pineapple's skin: diamond scales, gold going green at their points, a dark eye in each."""
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 16)

    def fn(x, y):
        u, v = (x + y) * 8.0 / size, (x - y) * 8.0 / size
        fu, fv = u - math.floor(u), v - math.floor(v)
        d = max(abs(fu - 0.5), abs(fv - 0.5)) * 2           # (0 a scale's middle, 1 its edge)
        g = n.at(x * 16.0 / size, y * 16.0 / size)
        col = tp._mix((214, 160, 56), (120, 130, 50), max(0.0, d - 0.55) * 1.6 + 0.2 * g)
        if d < 0.16:
            col = (70, 48, 30)
        if d > 0.92:
            col = tp._shade(col, 0.55)
        return tp._shade(col, 0.9 + 0.2 * g), 0.75 - 0.4 * d
    c.paint(fn)
    return c


def ukulele():
    """Lying on its back along y, the body's middle near the origin: a figure of eight of koa, a neck and a head."""
    lk = {'koa': look('island/uke_top', tile=None), 'dark': look('waikiki/koa', tile=30), 'string': look('city/rust', tile=16)}
    P = [{'shape': 'cylinder', 'r': 10, 'h': 5, 'sides': 14, 'at': [0, -6, 0], 'look': 'koa'},
         {'shape': 'cylinder', 'r': 8, 'h': 5, 'sides': 14, 'at': [0, 8, 0], 'look': 'koa'},
         {'shape': 'box', 'size': [3.4, 26, 1.6], 'at': [0, 27, 3.4], 'look': 'dark'},
         {'shape': 'box', 'size': [5, 7, 1.6], 'at': [0, 43, 3.4], 'look': 'dark'},
         {'shape': 'cylinder', 'r': 2.6, 'h': 0.4, 'sides': 10, 'at': [0, 2, 5], 'look': 'dark'}]
    return {'name': 'FOLabUkulele', 'looks': lk, 'parts': P}


def glass_float():
    """A Japanese fishing float: a ball of green glass in a net of cord."""
    return {'name': 'FOLabGlassFloat', 'looks': {'glass': look('island/float_glass', tile=None), 'net': look('waikiki/husk', tile=12)},
            'parts': [{'shape': 'ball', 'r': 9, 'sides': 12, 'rings': 8, 'look': 'glass'},
                      {'shape': 'cylinder', 'r': 9.4, 'h': 1.2, 'sides': 12, 'at': [0, 0, 8.4], 'look': 'net', 'caps': False},
                      {'shape': 'cylinder', 'r': 1.6, 'h': 2.5, 'sides': 6, 'at': [0, 0, 17.6], 'look': 'net'}]}


def coconut():
    return {'name': 'FOLabCoconut', 'looks': {'husk': look('island/coconut', tile=None)},
            'parts': [{'shape': 'ball', 'r': 6, 'sides': 10, 'rings': 6, 'scale': [1, 0.9, 1.1], 'look': 'husk'}]}


def pineapple():
    return {'name': 'FOLabPineapple', 'looks': {'skin': look('island/pine_skin', tile=None), 'leaf': look('jungle/ti_green', tile=None)},
            'parts': [{'shape': 'ball', 'r': 5.5, 'sides': 10, 'rings': 7, 'scale': [1, 1, 1.5], 'look': 'skin'},
                      {'shape': 'cone', 'r': 4, 'h': 9, 'sides': 6, 'at': [0, 0, 15.5], 'look': 'leaf'}]}


def tiki_mug():
    return {'name': 'FOLabTikiMug', 'looks': {'mug': look('island/tiki_mug', tile=None)},
            'parts': [{'shape': 'cylinder', 'r': 3.6, 'r2': 4.2, 'h': 12, 'sides': 10, 'look': 'mug'}]}


# key: (shown name, model, game item copied, value, weight, mass, material)
ITEMS = {'ukulele': ('Ukulele', ukulele, 'AcousticGuitar', 30, 1.0, 1.0, 'wood'),
         'glass_float': ('Glass Fishing Float', glass_float, 'ScotchBottle01Empty01', 12, 1.5, 1.0, 'glass'),
         'tiki_mug': ('Tiki Mug', tiki_mug, 'CoffeeMug01', 4, 1.0, 0.4, 'glass'),
         'coconut': ('Coconut', coconut, 'Mutfruit2', 6, 1.5, 1.0, 'wood'),
         'pineapple': ('Pineapple', pineapple, 'Mutfruit1', 8, 1.5, 1.0, 'wood')}


def build_item(key):
    """{'nif', 'mesh', 'files', 'box', 'triangles', 'shapes'}: the item's loose model and the pictures it names."""
    import modelmake
    import nifmake
    name, fn, _game, _v, _w, mass, material = ITEMS[key]
    desc = fn()
    made = modelmake.make(desc)
    made['nif'] = nifmake.build_dropped(desc['name'], made['shapes'], mass=mass, material=material)
    made['mesh'] = 'meshes\\folab\\%s\\items\\%s.nif' % (SET, key)
    files = {made['mesh']: made['nif']}
    for tex in made['textures']:
        tname = next((n for n in modelsets.TEXTURES if modelsets.tex_path(n) == tex or modelsets.tex_path(n, True) == tex), None)
        if tname is None:
            raise ValueError('%s names a texture no set draws: %s' % (key, tex))
        files[modelsets.tex_path(tname)], files[modelsets.tex_path(tname, True)] = modelsets.texture_files(tname)
    made['files'] = files
    return made


def item_record(gd, key, made):
    """The item's record: the game's like item with this name, model, bounds, value and weight (MODT dropped)."""
    import recordio
    name, _fn, game, value, weight, _m, _mat = ITEMS[key]
    tag = 'ALCH' if game.startswith('Mutfruit') else 'MISC'
    f = min((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == game), key=lambda f: f >> 24)
    rec = recordio.load(gd, f)
    rec['src'] = ''
    subs = []
    for s in rec['subs']:
        if s['tag'] == 'MODT':
            continue
        s = dict(s)
        if s['tag'] == 'EDID':
            s['value'] = 'FOLabItem' + ''.join(w.capitalize() for w in key.split('_'))
        elif s['tag'] == 'FULL':
            s['value'] = name
        elif s['tag'] == 'MODL':
            s['value'] = made['mesh'][7:]
        elif s['tag'] == 'OBND':
            s['fields'] = [dict(q, value=int(round(v))) for q, v in zip(s['fields'], made['box'])]
        elif s['tag'] == 'DATA':
            s['fields'] = [dict(q, value=value if q.get('name') == 'Value' else weight if q.get('name') == 'Weight' else q.get('value')) for q in s['fields']]
        elif s['tag'] == 'ENIT':
            s['fields'] = [dict(q, value=value) if q.get('name') == 'Value' else q for q in s['fields']]
        subs.append(s)
    rec['subs'] = subs
    return rec
