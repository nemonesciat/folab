"""FOLab's own pieces in place of the game's Mojave buildings that read wrong in Hawaii (docs/waikiki-mojave-misfits.md).

townbuild stands the game's stand-alone buildings on a city's plots, and some of them are Goodsprings, Novac and Nipton:
false fronts, a saloon with its name painted up. Each piece here is made in the frame of the game building it replaces
(its origin, its ground about 16 under the origin, its door refs exactly where the catalogue stands them), so `restyle.py`
swaps the building's base and leaves every door, link and lock as it was.

- `beach_bar` for NVProspectorSaloon: a thatched tiki bar of the saloon's size. Its west lanai (a deck under its own
  thatch, tiki posts at the corners, torches) is where the saloon's porch was, and the bar's door is on the hall's west
  wall, where the saloon's was (y -250..-115). The two scrap doors the catalogue stands at x -540 are in the store's
  walls: the one at y 312 (it leads in) in its north wall, the shut one at y 50 in its south wall, from the lanai. The
  hall serves out of two hatches in its south wall, counters and stools before them; the bar's sign (waikikiset's Tiki
  Room board, no new name) over them. Closed inside: the way in is the door, to the place townbuild gave it.

Pieces of `modelsets` (set 'restyle': meshes\\folab\\restyle, textures\\folab\\restyle), registered here at import."""
import math

import modelsets
import texpaint as tp
import texwear as tw
import waikikiset
from modelsets import look

SET = 'restyle'

AGED_THATCH = (146, 124, 90)       # (pili grass two centuries in the sun: greyer and darker than new)
CANE = (176, 150, 96)
TAPA_INK = (54, 32, 22)
TAPA_CLOTH = (204, 182, 142)


def bamboo_wall(size=256, seed=710, poles=7):
    """Bamboo poles stood side by side: each its own tone (straw to grey-brown), round (dark at its edges), split here
    and there down its grain, its nodes at its own spacing, a dark gap between poles. Repeats both ways."""
    c = tp.Canvas(size, size)
    n, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 64)
    w = size / float(poles)
    tones = [tp._mix(CANE, (118, 108, 86), n.at(k * 1.3, 0.5)) for k in range(poles)]
    gaps = [int(18 + 30 * n.at(k * 2.1, 3.0)) for k in range(poles)]
    offs = [n.at(k * 3.7, 5.0) for k in range(poles)]

    def fn(x, y):
        k = int(x / w) % poles
        u = (x % w) / w
        if u < 0.06:
            return (24, 20, 16), 0.0                                    # (the gap between two poles)
        r = abs(u - 0.53) / 0.47
        round_ = max(0.0, 1 - r * r)
        step = size / (2 + gaps[k] % 3)
        v = ((y / step) + offs[k]) % 1.0
        node = abs(v - 0.5) < 0.025
        grain = fine.at(x * 64.0 / size * 6, y * 64.0 / size / 6)
        col = tp._shade(tones[k], 0.55 + 0.55 * round_ * (0.85 + 0.25 * grain))
        if node:
            return tp._shade(col, 0.62), 0.75 + 0.2 * round_
        if grain > 0.86 and 0.25 < u < 0.8:
            return tp._shade(col, 0.6), 0.3                             # (a split down the grain)
        return col, 0.25 + 0.6 * round_
    c.paint(fn)
    return c


def lauhala(size=256, seed=720, strands=10):
    """Lauhala, pandanus leaf woven on the diagonal: wide flat strands over and under, each its own straw tone,
    greyed by weather, the weave's gaps dark."""
    c = tp.Canvas(size, size)
    n, fine = tp.Noise(seed, 16), tp.Noise(seed + 1, 64)
    cell = size / float(strands)

    def fn(x, y):
        a, b = (x + y) / cell, (x - y + size) / cell
        i, j = int(a), int(b)
        ua, ub = a - i, b - j
        over = (i + j) % 2 == 0
        t = ub if over else ua
        if abs(t - 0.5) > 0.44:
            return (40, 34, 26), 0.1
        tone = n.at((i if over else j) * 0.9, 1.0 if over else 7.0)
        col = tp._mix((190, 164, 114), (132, 124, 104), 0.25 + 0.6 * tone)
        g = fine.at(x * 64.0 / size, y * 64.0 / size)
        lift = 1 - abs((ua if over else ub) - 0.5) * 0.6
        return tp._shade(col, (0.78 + 0.22 * g) * lift), 0.35 + 0.45 * lift
    c.paint(fn)
    return c


def tapa(w=256, h=256, seed=730):
    """A band of tapa: beaten bark cloth printed in dark brown, rows of triangles, a zigzag, cross-hatched diamonds,
    between ruled lines; the cloth's fibres show and the ink is worn thin in places. Laid with its tile the band's
height: two diamonds to a repeat."""
    c = tp.Canvas(w, h)
    fib, wear = tp.Noise(seed, 128), tp.Noise(seed + 1, 16)

    def ink_at(x, y):
        v = y / float(h)
        if any(abs(v - r) < 0.025 for r in (0.08, 0.3, 0.7, 0.92)):
            return True
        if 0.1 < v < 0.28:                                              # (teeth along the top)
            p = (x % 64) / 64.0
            return (v - 0.1) / 0.18 < 1 - abs(p - 0.5) * 2
        if 0.72 < v < 0.9:                                              # (and along the foot, pointing up)
            p = (x % 64) / 64.0
            return (0.9 - v) / 0.18 < 1 - abs(p - 0.5) * 2
        if 0.32 < v < 0.68:                                             # (diamonds, hatched, between zigzags)
            p, q = (x % 128) / 128.0, (v - 0.32) / 0.36
            d = abs(p - 0.5) * 2 + abs(q - 0.5) * 2
            if d < 0.55:
                return (x + y) % 10 < 3 or (x - y) % 10 < 3
            return abs(d - 0.8) < 0.07
        return False

    def fn(x, y):
        f = fib.at(x * 128.0 / w * 2, y * 128.0 / h / 3)
        cloth = tp._shade(TAPA_CLOTH, 0.82 + 0.25 * f)
        if ink_at(x, y) and wear.at(x * 16.0 / w, y * 16.0 / h * 4) < 0.8:
            return tp._mix(TAPA_INK, cloth, 0.12 + 0.2 * f), 0.4
        return cloth, 0.5 + 0.1 * f
    c.paint(fn)
    return c


def fringe(size=256, seed=740, colour=AGED_THATCH):
    """The ragged edge of a thatched eave: straw hanging from the top of the picture, every few strands to its own
    length (none shorter than half), see-through below."""
    c = tp.Canvas(size, size, clear=colour)
    n, fine = tp.Noise(seed, 32), tp.Noise(seed + 1, 128)
    for x in range(size):
        L = int(size * (0.5 + 0.45 * n.at(x * 32.0 / size * 1.5, 0.5) + 0.05 * fine.at(x * 1.0, 2.0)))
        g = fine.at(x * 128.0 / size, 0.3)
        for y in range(L):
            i = y * size + x
            k = y / float(L)
            c.rgb[i] = tp._shade(colour, (0.65 + 0.45 * g) * (1.0 - 0.35 * k))
            c.ht[i] = 0.3 + 0.4 * g
            c.a[i] = 1.0
    return c


modelsets.TEXTURES.update({
    'restyle/blind': lambda: tw.wood((178, 154, 104), size=256, seed=701, count=12, paint_left=0.0, across=True),
    'restyle/dark': lambda: tw.wood((46, 38, 30), size=128, seed=702, count=4, paint_left=0.0),
    'restyle/deck': lambda: tp.planks((150, 120, 86), seed=703, wear=0.35),
    'restyle/counter': lambda: tw.wood((120, 78, 48), size=256, seed=704, count=5, paint_left=0.3),
    'restyle/bamboo_wall': lambda: bamboo_wall(),
    'restyle/lauhala': lambda: lauhala(),
    'restyle/tapa': lambda: tapa(),
    'restyle/thatch': lambda: tp.thatch(size=512, seed=711, colour=AGED_THATCH),
    'restyle/fringe': lambda: fringe(),
    'restyle/float': lambda: tp.painted_metal((64, 128, 112), seed=750, rust=0.0),
})

GROUND = -16.0          # (the saloon's ground under its middle and corners: the catalogue's mid -16, lo -23, hi -2)
FLOOR = 25.0            # (the deck its door stands on: the saloon door's z 24.9)
HALL = (-280.0, -525.0, 1000.0, 535.0)      # the hall, x0 y0 x1 y1 (its west face just behind the bar's door)
WALL_TOP = 360.0
LANAI = (-750.0, -504.0, -280.0, 56.0)      # the deck before the door
STORE = (-740.0, 58.0, -290.0, 304.0)       # the store: its south face behind the shut door, its north the one that opens
DOORS = {'bar': (-292.0, -248.0), 'store': (-540.0, 312.0), 'store_shut': (-543.0, 50.0)}     # (as the catalogue has them)
HATCHES = (60.0, 690.0)                    # the serving hatches along the south wall, by x


def _looks():
    b = waikikiset._base_looks()
    return dict(b, lava=look('hotel/lava', tile=160), deck=look('restyle/deck', tile=140, turned=True), blind=look('restyle/blind', tile=120),
                dark=look('restyle/dark', tile=64), counter=look('restyle/counter', tile=96), tiki_face=look('waikiki/tiki'),
                tiki_wood=look('waikiki/tiki_wood', tile=90), sign=waikikiset._motel(3), fire=waikikiset.lit('waikiki/flame', 4.0, alpha=True),
                thatch=look('restyle/thatch', tile=220), fringe=look('restyle/fringe', tile=FRINGE + 10, alpha=True),
                wall=look('restyle/bamboo_wall', tile=150), mat=look('restyle/lauhala', tile=120), tapa=look('restyle/tapa', tile=TAPA),
                tapa_beam=look('restyle/tapa', tile=26), net=look('waikiki/net', tile=90, alpha=True), glass=look('restyle/float', tile=40),
                board_a=look('surf_red'), board_b=look('surf_teal'), white=look('metal_white', tile=48), bulb=waikikiset.lit('waikiki/lamp_glass', 3.0))


FRINGE = 64.0           # (how far the ragged straw hangs under an eave)
TAPA = 44.0             # (the tapa band's height round the hall under its eaves)


def _box(P, x0, y0, z0, x1, y1, z1, lk, solid=True, far=False, material='wood', **faces):
    p = {'shape': 'box', 'size': [round(x1 - x0, 1), round(y1 - y0, 1), round(z1 - z0, 1)], 'at': [round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1), round(z0, 1)],
         'look': lk, 'solid': solid, 'far': far, 'material': material}
    if faces:
        p['faces'] = faces
    P.append(p)
    return p


def _post(P, x, y, h, z=GROUND, r=12.0):
    P.append({'shape': 'cylinder', 'r': r, 'h': h - z, 'sides': 7, 'at': [x, y, z], 'look': 'bamboo', 'material': 'wood'})


ALONG = 6               # (points along each edge of a roof's sheets)


def _line(a, b, n=ALONG):
    return [tuple(round(a[k] + (b[k] - a[k]) * t / (n - 1.0), 1) for k in range(3)) for t in range(n)]


def _sheet(P, low, high, lk='thatch', far=True, thick=10.0):
    P.append({'shape': 'sheet', 'rows': [low, high], 'look': lk, 'under_look': lk, 'thick': thick, 'at': [0, 0, 0], 'solid': False, 'far': far})


def _fringe(P, a, b, drop=FRINGE):
    """Ragged straw hanging from an eave's edge, a to b (see-through below its strands)."""
    top = _line(a, b)
    P.append({'shape': 'sheet', 'rows': [top, [(x, y, z - drop) for x, y, z in top]], 'look': 'fringe', 'thick': 1.0, 'at': [0, 0, 0], 'solid': False})


def _rect(x0, y0, x1, y1, z):
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]


def _hip(P, x0, y0, x1, y1, z, h, over, fringe_sides=(0, 1, 2, 3), roll=True):
    """A steep hipped thatch roof over a rectangle, its eaves `over` past it at height z: four slopes rising h to a
    ridge along the longer side (a point when it's square), a roll of thatch along the ridge, ragged straw under the
    eaves on the sides asked for (0 the -y side, then +x, +y, -x). Returns the ridge's two ends."""
    ax, ay, bx, by = x0 - over, y0 - over, x1 + over, y1 + over
    mx, my = (ax + bx) / 2, (ay + by) / 2
    half = min(bx - ax, by - ay) / 2
    top = z + h
    if bx - ax >= by - ay:
        r0, r1 = (ax + half, my, top), (bx - half, my, top)
    else:
        r0, r1 = (mx, ay + half, top), (mx, by - half, top)
    corners = _rect(ax, ay, bx, by, z)

    def near(c):
        return min((r0, r1), key=lambda r: (r[0] - c[0]) ** 2 + (r[1] - c[1]) ** 2)
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        ta, tb = near(a), near(b)
        if ta == tb:            # (an end: its top a hand's breadth wide, not a point, so no triangle has no area)
            ex, ey = (b[0] - a[0]), (b[1] - a[1])
            n = math.hypot(ex, ey)
            ta, tb = (ta[0] - ex / n * 8, ta[1] - ey / n * 8, top), (ta[0] + ex / n * 8, ta[1] + ey / n * 8, top)
        _sheet(P, _line(a, b), _line(ta, tb))
        if k in fringe_sides:
            _fringe(P, a, b)
    if roll and r0 != r1:
        L = math.hypot(r1[0] - r0[0], r1[1] - r0[1])
        along_x = r1[0] != r0[0]
        P.append({'shape': 'cylinder', 'r': 18, 'h': L + 60, 'sides': 6, 'at': [r0[0] - (30 if along_x else 0), r0[1] - (0 if along_x else 30), top - 6],
                  'turn': [0, 90, 0] if along_x else [-90, 0, 0], 'look': 'thatch', 'solid': False})
    return r0, r1


def _skirt(P, x0, y0, x1, y1, z, out, inset, rise):
    """The lower tier of a two-tier roof: a shallow thatch slope from eaves `out` past the walls at z up to a line
    `inset` inside them, `rise` higher; ragged straw under its eaves."""
    lo = _rect(x0 - out, y0 - out, x1 + out, y1 + out, z)
    hi = _rect(x0 + inset, y0 + inset, x1 - inset, y1 - inset, z + rise)
    for k in range(4):
        _sheet(P, _line(lo[k], lo[(k + 1) % 4]), _line(hi[k], hi[(k + 1) % 4]))
        _fringe(P, lo[k], lo[(k + 1) % 4])


def _crossed(P, end, other, rise=130.0, spread=70.0):
    """Two poles crossed over a ridge's end, standing up past it: the old houses' sign that a roof is finished."""
    dx, dy = end[0] - other[0], end[1] - other[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n                     # (out along the ridge)
    px, py = -uy, ux                            # (across it)
    x, y, z = end
    for s in (-1, 1):
        a = (x - ux * 20 + px * s * spread, y - uy * 20 + py * s * spread, z - 70)
        b = (x + ux * 30 - px * s * spread * 0.9, y + uy * 30 - py * s * spread * 0.9, z + rise)
        P.append(modelsets.limb(a, b, 7, 5, 'bamboo'))


def _frame(P, x, y, along, wide, tall, z=FLOOR, out=1.0):
    """A bamboo door frame round a doorway whose middle is at x, y: two jambs and a lintel, standing proud of its wall
    (`out` the side the door is on: -1 or 1 across it). along: 'y' when the wall runs along y."""
    half = wide / 2 + 9
    for s in (-1, 1):
        if along == 'y':
            _box(P, x - 9 + out * 6, y + s * half - 9, z, x + 9 + out * 6, y + s * half + 9, z + tall + 12, 'bamboo', solid=False)
        else:
            _box(P, x + s * half - 9, y - 9 + out * 6, z, x + s * half + 9, y + 9 + out * 6, z + tall + 12, 'bamboo', solid=False)
    if along == 'y':
        _box(P, x - 10 + out * 6, y - half - 9, z + tall, x + 10 + out * 6, y + half + 9, z + tall + 22, 'bamboo', solid=False)
    else:
        _box(P, x - half - 9, y - 10 + out * 6, z + tall, x + half + 9, y + 10 + out * 6, z + tall + 22, 'bamboo', solid=False)


def _torch(P, x, y, z):
    for q in waikikiset.tiki_torch(170.0)['parts']:
        a = q.get('at', (0, 0, 0))
        P.append(dict(q, at=[x + a[0], y + a[1], z + a[2]], solid=False))       # (a pole too thin to close as a solid)


def _tiki_post(P, x, y, z, top, face_turn, w=64.0):
    """A carved post, its face out (face_turn: which face, 'front' -y or 'left' -x)."""
    _box(P, x - w / 2, y - w / 2, z, x + w / 2, y + w / 2, top, 'tiki_wood', far=True, **{face_turn: 'tiki_face'})
    _box(P, x - w / 2 - 6, y - w / 2 - 6, top, x + w / 2 + 6, y + w / 2 + 6, top + 12, 'tiki_wood', solid=False)


def _walls(P, x0, y0, x1, y1, z0, z1, rail):
    """Woven walls on a footing: bamboo poles to `rail`, lauhala over them, a bamboo rail between."""
    _box(P, x0 + 8, y0 + 8, z0, x1 - 8, y1 - 8, rail, 'wall', far=True)
    _box(P, x0 + 12, y0 + 12, rail, x1 - 12, y1 - 12, z1, 'mat', far=True)
    _box(P, x0 + 4, y0 + 4, rail - 6, x1 - 4, y1 - 4, rail + 8, 'bamboo', solid=False)


def beach_bar():
    """See the module's docstring."""
    P = []
    x0, y0, x1, y1 = HALL
    # the hall: a lava rock footing, bamboo and lauhala walls, posts up its corners and along its sides, a tapa band
    _box(P, x0, y0, GROUND - 24, x1, y1, 70, 'lava', far=True, material='stone')
    _walls(P, x0, y0, x1, y1, 70, WALL_TOP, 220)
    for k in range(6):
        x = x0 + (x1 - x0) * k / 5
        for y in (y0 + 4, y1 - 4):
            _post(P, x, y, WALL_TOP + 4, z=70)
    for k in range(1, 4):
        y = y0 + (y1 - y0) * k / 4
        for x in (x0 + 4, x1 - 4):
            _post(P, x, y, WALL_TOP + 4, z=70)
    _box(P, x0 - 4, y0 - 4, WALL_TOP - TAPA, x1 + 4, y1 + 4, WALL_TOP, 'tapa', solid=False)
    # bamboo blinds rolled down over windows on the north wall, and glass floats caught in a net between them
    for k in (0, 2, 3):
        x = x0 + 200 + k * 260
        _box(P, x - 80, y1 - 4, 130, x + 80, y1 + 6, 270, 'blind', solid=False)
        _box(P, x - 90, y1 + 2, 270, x + 90, y1 + 14, 286, 'bamboo', solid=False)
    nx = x0 + 200 + 260
    P.append({'shape': 'card', 'size': [230, 150], 'at': [nx, y1 + 12, 140], 'look': 'net'})
    for k, (fx, fz) in enumerate(((-70, 190), (-20, 250), (35, 170), (80, 230), (5, 205), (-95, 255))):
        P.append({'shape': 'ball', 'r': 11 + (k % 3) * 2, 'sides': 8, 'rings': 5, 'at': [nx + fx, y1 + 22, fz], 'look': 'glass', 'solid': False})
    # the bar's door, west wall: its frame, a carved tiki either side (the door itself is the game's, stood by townbuild)
    dx, dy = DOORS['bar']
    _frame(P, dx, dy + 64.5, 'y', 136, 178, out=-1)
    for ty in (dy - 48.0, dy + 176.0):
        _tiki_post(P, x0 - 34, ty, FLOOR, FLOOR + 236, 'left', w=46.0)
    # the hatches on the south wall: a dark opening, its flap propped up, a counter outside, stools; the sign between
    for hx in HATCHES:
        _box(P, hx - 130, y0 - 3, 120, hx + 130, y0 + 4, 250, 'dark', solid=False)
        _box(P, hx - 150, y0 - 10, 108, hx + 150, y0 + 2, 120, 'bamboo', solid=False)
        for s in (-1, 1):
            _box(P, hx + s * 140 - 10, y0 - 12, 108, hx + s * 140 + 10, y0, 262, 'bamboo', solid=False)
        P.append({'shape': 'slab', 'size': [300, 120, 6], 'at': [hx, y0 - 52, 258], 'turn': [-22, 0, 0], 'look': 'blind', 'under': True, 'solid': False})
        _box(P, hx - 150, y0 - 70, GROUND, hx + 150, y0 - 6, 104, 'wall', top='counter')
        _box(P, hx - 162, y0 - 82, 104, hx + 162, y0 - 4, 110, 'counter', solid=False)
        for k in range(3):
            sx = hx - 100 + 100 * k
            P.append({'shape': 'cylinder', 'r': 4, 'h': 66 - GROUND, 'sides': 6, 'at': [sx, y0 - 130, GROUND], 'look': 'bamboo', 'solid': False})
            P.append({'shape': 'cylinder', 'r': 19, 'h': 6, 'sides': 10, 'at': [sx, y0 - 130, 66], 'look': 'wicker', 'solid': False})
    mid = (HATCHES[0] + HATCHES[1]) / 2
    _box(P, mid - 170, y0 - 18, 118, mid + 170, y0 - 2, 296, 'counter', solid=False, front='sign')
    # the roof in two tiers: a shallow skirt over the walls, a steep top over it, crossed poles at the ridge's ends
    _skirt(P, x0, y0, x1, y1, WALL_TOP - 40, 170, 170, 150)
    r0, r1 = _hip(P, x0 + 170, y0 + 170, x1 - 170, y1 - 170, WALL_TOP + 100, 330, 50, fringe_sides=())
    _crossed(P, r0, r1)
    _crossed(P, r1, r0)
    # the east end: a lean-to of the same, a low roof, surfboards against it
    _box(P, x1, -470, GROUND - 10, 1190, 480, 50, 'lava', material='stone')
    _box(P, x1, -466, 50, 1186, 476, 240, 'wall', far=True)
    P.append({'shape': 'slab', 'size': [260, 1060, 10], 'at': [1110, 5, 248], 'turn': [0, 12, 0], 'look': 'thatch', 'under': True, 'solid': False, 'far': True})
    _fringe(P, (1240, -525, 238), (1240, 535, 238), drop=50)
    P.append({'shape': 'cylinder', 'r': 70, 'h': 200, 'sides': 10, 'at': [1260, 380, GROUND], 'look': 'rust', 'material': 'metal'})     # (rain off the roof)
    for k, (by, lk) in enumerate(((-210.0, 'board_a'), (-120.0, 'board_b'))):
        P += modelsets.surfboard([1209, by, 72 + GROUND], [80 - 3 * k, 0, 90], lk, long=164, wide=32, fin='white')
    # the lanai: a deck a step up, steps along its open sides, tiki posts at its outer corners, lights strung, torches
    lx0, ly0, lx1, ly1 = LANAI
    _box(P, lx0, ly0, GROUND - 20, lx1, ly1, FLOOR, 'deck', far=True)
    _box(P, lx0 - 44, ly0 - 44, GROUND - 20, lx1, ly1, 4, 'deck')
    _tiki_post(P, lx0 + 32, ly0 + 32, GROUND, 300, 'left')
    _tiki_post(P, lx1 - 40, ly0 + 32, GROUND, 300, 'front')
    _tiki_post(P, lx0 + 32, -220, GROUND, 300, 'left')
    _box(P, lx0, ly0 + 4, 286, lx1, ly0 + 30, 312, 'bamboo', solid=False, front='tapa_beam', back='tapa_beam')      # (beams the eaves rest on)
    _box(P, lx0 + 4, ly0, 286, lx0 + 30, STORE[3], 312, 'bamboo', solid=False, left='tapa_beam', right='tapa_beam')
    span = (lx1 - 40) - (lx0 + 32)
    for q in waikikiset.string_lights(span)['parts']:
        if q['shape'] == 'cylinder' and q.get('r') == 6:
            continue                                                    # (its own posts: the tikis hold it here)
        a = q.get('at', (0, 0, 0))
        P.append(dict(q, at=[(lx0 + 32 + lx1 - 40) / 2 + a[0], ly0 + 20 + a[1], a[2] - 40], solid=False))
    _torch(P, lx0 - 70, ly0 - 70, GROUND)
    _torch(P, lx1 + 40, ly0 - 70, GROUND)
    # the store: walls as the hall's on a lava footing, its two doors' frames
    sx0, sy0, sx1, sy1 = STORE
    _box(P, sx0, sy0, GROUND - 24, sx1, sy1, 40, 'lava', far=True, material='stone')
    _walls(P, sx0 - 2, sy0 - 2, sx1 + 2, sy1 + 2, 40, 290, 170)
    for x, y in ((sx0, sy1), (sx1, sy1)):
        _post(P, x + (8 if x == sx0 else -8), y - 8, 300)
    _frame(P, DOORS['store'][0], sy1, 'x', 98, 158, z=13.0, out=1)
    _frame(P, DOORS['store_shut'][0], sy0, 'x', 98, 158, z=FLOOR - 9, out=-1)
    # its roof and the lanai's, one thatch over both, lower than the hall's, its east eave on the hall's wall
    q0, q1 = _hip(P, lx0, ly0, lx1 - 70, sy1, 290, 300, 70, fringe_sides=(0, 2, 3))
    _crossed(P, q0, q1, rise=100, spread=55)
    _crossed(P, q1, q0, rise=100, spread=55)
    # lava rock planters of flowering hibiscus: one beside the lanai, one along the north wall
    looks = _looks()
    _merge(P, looks, planter(), lx0 - 110, -230.0, GROUND, 90.0, 'pw')
    _merge(P, looks, planter(seed=5), nx + 260, y1 + 80, GROUND, 0.0, 'pn')
    return {'name': 'FOLabBeachBar', 'looks': looks, 'parts': P}


def planter(seed=1):
    """A planter walled in lava rock, hibiscus flowering in it: a bush of crossed pictures each, nothing solid but the wall."""
    P = [{'shape': 'box', 'size': [440, 110, 62], 'look': 'lava', 'faces': {'top': 'soil'}, 'material': 'stone'}]
    looks = {'lava': look('hotel/lava', tile=160), 'soil': look('waikiki/husk', tile=60)}
    desc = {'name': 'FOLabPlanter', 'looks': looks, 'parts': P}
    for k, x in enumerate((-140, 0, 140)):
        _merge(P, looks, modelsets.crossed('b', 'hibiscus', 150 + 20 * (k % 2), 120 + 15 * ((k + seed) % 3), cards=3, top=True, seed=seed + k), x, 0.0, 58.0, 0.0, 'h%d' % k)
    return desc


def _merge(P, looks, desc, x, y, z, yaw, tag):
    """Another piece's parts laid into this one at x, y, z turned yaw degrees, its looks named apart by `tag`."""
    one = modelsets.combine(tag, [(desc, x, y, yaw, 1.0)])
    for k, v in one['looks'].items():
        looks[tag + k[1:]] = v
    for q in one['parts']:
        for f in ('look', 'cap_look', 'under_look'):
            if q.get(f) is not None:
                q[f] = tag + q[f][1:]
        if q.get('faces'):
            q['faces'] = {s: (None if v is None else tag + v[1:]) for s, v in q['faces'].items()}
        q['at'] = [q['at'][0], q['at'][1], q['at'][2] + z]
        P.append(q)


# ---------- the plantation town: in place of Goodsprings' and Nipton's Wild West buildings ----------
# What a sugar town's main street looked like: single-wall board-and-batten painted in a colour gone pale (mint, butter,
# barn red, sky blue) with white trim, corrugated tin roofs with deep eaves, a lanai of posts and a tin shed roof along
# the front, two-over-two sash windows, a raised wooden floor on short piers, a plain sign board with no name on it.

modelsets.TEXTURES.update({
    'restyle/boards_mint': lambda: tw.wood((146, 184, 158), size=256, seed=760, count=7, paint_left=0.8),
    'restyle/boards_butter': lambda: tw.wood((214, 194, 132), size=256, seed=761, count=7, paint_left=0.82),
    'restyle/boards_red': lambda: tw.wood((150, 68, 54), size=256, seed=762, count=7, paint_left=0.78),
    'restyle/boards_blue': lambda: tw.wood((126, 158, 176), size=256, seed=763, count=7, paint_left=0.8),
    'restyle/boards_white': lambda: tw.wood((214, 210, 196), size=256, seed=764, count=7, paint_left=0.9),
    'restyle/trim': lambda: tw.wood((224, 220, 206), size=128, seed=765, count=3, paint_left=0.7),
    'restyle/tin': lambda: tp.corrugated((134, 126, 116), seed=766, ridges=18),
    'restyle/tin_red': lambda: tp.corrugated((132, 66, 50), seed=767, ridges=18),
    'restyle/tin_green': lambda: tp.corrugated((78, 106, 84), seed=768, ridges=18),
    'restyle/window': lambda: tw.glass_curtain(frame=(222, 218, 204), tint=(38, 50, 54), panes=(2, 2), broken=0.25, seed=769),
    'restyle/floor': lambda: tp.planks((140, 122, 98), seed=770, wear=0.4),
    'restyle/plinth': lambda: tw.concrete((150, 144, 132), size=256, seed=771, boards=3),
    'restyle/board_blank': lambda: tw.wood((196, 186, 160), size=256, seed=772, count=3, paint_left=0.75, across=True),
})


def _kit_looks(paint, roof):
    return {'boards': look('restyle/boards_' + paint, tile=140), 'trim': look('restyle/trim', tile=80), 'tin': look('restyle/tin_' + roof if roof else 'restyle/tin', tile=150),
            'window': look('restyle/window'), 'floor': look('restyle/floor', tile=140, turned=True), 'plinth': look('restyle/plinth', tile=140),
            'board_blank': look('restyle/board_blank', tile=200), 'dark': look('restyle/dark', tile=64)}


def _block(P, b, floor, ground):
    """One block of a building: a plinth to its floor, board walls to b['top'], corner boards and a frieze in trim, its roof
    in tin (hipped, its eaves `over` out)."""
    x0, y0, x1, y1, top = b['x0'], b['y0'], b['x1'], b['y1'], b['top']
    _box(P, x0, y0, ground - 24, x1, y1, floor, 'plinth', far=True, material='stone')
    _box(P, x0 + 4, y0 + 4, floor, x1 - 4, y1 - 4, top, 'boards', far=True)
    for x in (x0, x1):
        for y in (y0, y1):
            _box(P, x - 9, y - 9, floor, x + 9, y + 9, top, 'trim', solid=False)
    _box(P, x0 - 2, y0 - 2, top - 30, x1 + 2, y1 + 2, top, 'trim', solid=False)
    over = b.get('over', 70.0)
    h = b.get('rise', 0.42 * (min(x1 - x0, y1 - y0) / 2 + over))
    _tin_hip(P, x0, y0, x1, y1, top - 4, h, over)


def _tin_hip(P, x0, y0, x1, y1, z, h, over):
    """A hipped tin roof (as _hip, no thatch: a ridge cap, no fringe), its eaves trimmed."""
    ax, ay, bx, by = x0 - over, y0 - over, x1 + over, y1 + over
    half = min(bx - ax, by - ay) / 2
    top = z + h
    if bx - ax >= by - ay:
        r0, r1 = (ax + half, (ay + by) / 2, top), (bx - half, (ay + by) / 2, top)
    else:
        r0, r1 = ((ax + bx) / 2, ay + half, top), ((ax + bx) / 2, by - half, top)
    corners = _rect(ax, ay, bx, by, z)

    def near(c):
        return min((r0, r1), key=lambda r: (r[0] - c[0]) ** 2 + (r[1] - c[1]) ** 2)
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        ta, tb = near(a), near(b)
        if ta == tb:
            ex, ey = b[0] - a[0], b[1] - a[1]
            n = math.hypot(ex, ey)
            ta, tb = (ta[0] - ex / n * 6, ta[1] - ey / n * 6, top), (ta[0] + ex / n * 6, ta[1] + ey / n * 6, top)
        P.append({'shape': 'sheet', 'rows': [_line(a, b, 4), _line(ta, tb, 4)], 'look': 'tin', 'under_look': 'trim', 'thick': 5.0, 'at': [0, 0, 0], 'solid': False, 'far': True})
    if r0 != r1:
        _box(P, min(r0[0], r1[0]) - 12, min(r0[1], r1[1]) - 12, top - 8, max(r0[0], r1[0]) + 12, max(r0[1], r1[1]) + 12, top + 6, 'tin', solid=False)


def _lanai(P, la, floor, ground):
    """A lanai along a wall: its deck at the floor, posts along its open sides, a tin shed roof falling from the wall to its
    edge, a rail between posts except where `gaps` (x or y spans) leave a way in, steps down at each gap."""
    x0, y0, x1, y1 = la['x0'], la['y0'], la['x1'], la['y1']
    wall = la['wall']                       # which side the building is on: '+x', '-x', '+y', '-y'
    hi, lo = la['hi'], la['lo']
    _box(P, x0, y0, ground - 20, x1, y1, floor, 'floor', far=True)
    open_sides = [s for s in ('+x', '-x', '+y', '-y') if s != wall]
    posts = []
    for s in open_sides:
        if s in ('+x', '-x'):
            x = x1 - 8 if s == '+x' else x0 + 8
            n = max(1, int((y1 - y0) // 280))
            posts += [(x, y0 + 8 + (y1 - y0 - 16) * k / n) for k in range(n + 1)]
        else:
            y = y1 - 8 if s == '+y' else y0 + 8
            n = max(1, int((x1 - x0) // 280))
            posts += [(x0 + 8 + (x1 - x0 - 16) * k / n, y) for k in range(n + 1)]
    for x, y in set((round(a), round(b)) for a, b in posts):
        _box(P, x - 7, y - 7, floor, x + 7, y + 7, lo, 'trim')
    gaps = la.get('gaps', ())
    for s in open_sides:
        if s in ('+x', '-x'):
            x = x1 - 8 if s == '+x' else x0 + 8
            spans = _cut((y0, y1), [g for g in gaps if g[0] == s])
            for a, b in spans:
                _box(P, x - 4, a, floor + 80, x + 4, b, floor + 90, 'trim', solid=False)
                _box(P, x - 3, a, floor, x + 3, b, floor + 90, None)              # (one to walk into: nothing drawn)
        else:
            y = y1 - 8 if s == '+y' else y0 + 8
            spans = _cut((x0, x1), [g for g in gaps if g[0] == s])
            for a, b in spans:
                _box(P, a, y - 4, floor + 80, b, y + 4, floor + 90, 'trim', solid=False)
                _box(P, a, y - 3, floor, b, y + 3, floor + 90, None)
    for s, a, b in gaps:                    # (steps down where the way in is)
        if floor - ground < 18:
            continue
        mid = floor / 2 + ground / 2
        if s == '-x':
            _box(P, x0 - 46, a, ground - 10, x0, b, mid, 'floor')
        elif s == '+x':
            _box(P, x1, a, ground - 10, x1 + 46, b, mid, 'floor')
        elif s == '-y':
            _box(P, a, y0 - 46, ground - 10, b, y0, mid, 'floor')
        else:
            _box(P, a, y1, ground - 10, b, y1 + 46, mid, 'floor')
    # the roof: a sheet from the wall (hi) to past the open edge (lo)
    o = 40.0
    if wall == '-x':
        rows = [_line((x0, y0 - o, hi), (x0, y1 + o, hi), 4), _line((x1 + o, y0 - o, lo - 6), (x1 + o, y1 + o, lo - 6), 4)]
    elif wall == '+x':
        rows = [_line((x1, y0 - o, hi), (x1, y1 + o, hi), 4), _line((x0 - o, y0 - o, lo - 6), (x0 - o, y1 + o, lo - 6), 4)]
    elif wall == '-y':
        rows = [_line((x0 - o, y0, hi), (x1 + o, y0, hi), 4), _line((x0 - o, y1 + o, lo - 6), (x1 + o, y1 + o, lo - 6), 4)]
    else:
        rows = [_line((x0 - o, y1, hi), (x1 + o, y1, hi), 4), _line((x0 - o, y0 - o, lo - 6), (x1 + o, y0 - o, lo - 6), 4)]
    P.append({'shape': 'sheet', 'rows': rows, 'look': 'tin', 'under_look': 'trim', 'thick': 5.0, 'at': [0, 0, 0], 'solid': False, 'far': True})
    # (a beam along the open edge under the roof, posts to it)
    e = la.get('edge', '+x' if wall == '-x' else '-x' if wall == '+x' else '+y' if wall == '-y' else '-y')
    if e in ('+x', '-x'):
        x = x1 - 8 if e == '+x' else x0 + 8
        _box(P, x - 9, y0, lo - 18, x + 9, y1, lo, 'trim', solid=False)
    else:
        y = y1 - 8 if e == '+y' else y0 + 8
        _box(P, x0, y - 9, lo - 18, x1, y + 9, lo, 'trim', solid=False)


def _cut(span, gaps):
    out = [span]
    for _s, a, b in gaps:
        nxt = []
        for p, q in out:
            if a < q and b > p:
                nxt += [(p, min(q, a)), (max(p, b), q)]
            else:
                nxt.append((p, q))
        out = [(p, q) for p, q in nxt if q - p > 10]
    return out


def _windows(P, b, floor, doors, every=230.0, skip=()):
    """Sash windows along a block's walls every `every`, none within reach of a door or on the sides in `skip`."""
    x0, y0, x1, y1 = b['x0'], b['y0'], b['x1'], b['y1']
    for side in ('-y', '+y', '-x', '+x'):
        if side in skip:
            continue
        along = side in ('-y', '+y')
        lo_, hi_ = (x0, x1) if along else (y0, y1)
        n = int((hi_ - lo_ - 120) // every)
        for k in range(n):
            t = lo_ + (hi_ - lo_) * (k + 1) / (n + 1)
            if along:
                y = y0 - 3 if side == '-y' else y1 + 3
                if any(math.hypot(t - dx, y - dy) < 150 for dx, dy in doors):
                    continue
                _box(P, t - 38, y - 3, floor + 80, t + 38, y + 3, floor + 210, 'window', solid=False)
                _box(P, t - 46, y - 7, floor + 72, t + 46, y + 7, floor + 82, 'trim', solid=False)
                _box(P, t - 46, y - 5, floor + 208, t + 46, y + 5, floor + 220, 'trim', solid=False)
            else:
                x = x0 - 3 if side == '-x' else x1 + 3
                if any(math.hypot(x - dx, t - dy) < 150 for dx, dy in doors):
                    continue
                _box(P, x - 3, t - 38, floor + 80, x + 3, t + 38, floor + 210, 'window', solid=False)
                _box(P, x - 7, t - 46, floor + 72, x + 7, t + 46, floor + 82, 'trim', solid=False)
                _box(P, x - 5, t - 46, floor + 208, x + 5, t + 46, floor + 220, 'trim', solid=False)


def plantation(name, paint, roof, floor, ground, blocks, lanais=(), doors=(), frames=(), sign=None, extras=None, skip_windows=None):
    """A building of the plantation town in a game building's frame. blocks [{'x0','y0','x1','y1','top', 'over'?, 'rise'?}];
    lanais (see _lanai); frames [(x, y, along, wide, tall, z, out)] door frames round where the game's doors stand;
    doors [(x, y)] the spots windows keep clear of; sign (x0, y0, x1, y1, z0, z1) a blank sign board; extras(P) adds more."""
    P = []
    for k, b in enumerate(blocks):
        _block(P, b, floor, ground)
        for up in range(0, int(b['top'] - floor) - 200, 300):          # (a row of windows a storey)
            _windows(P, b, floor + up, doors, skip=(skip_windows or {}).get(k, ()))
    for la in lanais:
        _lanai(P, la, floor, ground)
    for x, y, along, wide, tall, z, out in frames:
        _frame_trim(P, x, y, along, wide, tall, z, out)
    if sign:
        x0, y0, x1, y1, z0, z1 = sign
        _box(P, x0, y0, z0, x1, y1, z1, 'board_blank', solid=False)
    if extras:
        extras(P)
    return {'name': name, 'looks': _kit_looks(paint, roof), 'parts': P}


def _frame_trim(P, x, y, along, wide, tall, z, out):
    half = wide / 2 + 8
    for s in (-1, 1):
        if along == 'y':
            _box(P, x - 6 + out * 5, y + s * half - 8, z, x + 6 + out * 5, y + s * half + 8, z + tall + 10, 'trim', solid=False)
        else:
            _box(P, x + s * half - 8, y - 6 + out * 5, z, x + s * half + 8, y + 6 + out * 5, z + tall + 10, 'trim', solid=False)
    if along == 'y':
        _box(P, x - 8 + out * 5, y - half - 12, z + tall, x + 8 + out * 5, y + half + 12, z + tall + 22, 'trim', solid=False)
    else:
        _box(P, x - half - 12, y - 8 + out * 5, z + tall, x + half + 12, y + 8 + out * 5, z + tall + 22, 'trim', solid=False)


# Each in its game building's frame. Doors as townbuild's catalogue and the mod stand them (survey, 20 Nov 2026):
# store/shop 01: the craftsman door's leaf from (-281, -34) to (-281, 95) on the main block's west face, the porch before it;
# shop 02: like the saloon (doors at (-293, -195) on the main west face, (-540, 57) and (-539, 303) in the store's faces);
# schoolhouse: (-648, 390) on the west face and (648, 629) on the east, the leaves 90 wide; hall: (0, 1433) on the north.

def plantation_store():
    """In place of NVGeneralStore: a mint-green store, a lanai along its west front, its storeroom behind to the east."""
    return plantation('FOLabPlantationStore', 'mint', 'red', 17.0, -10.0,
                      [{'x0': -276, 'y0': -292, 'x1': 608, 'y1': 382, 'top': 330}, {'x0': 608, 'y0': -92, 'x1': 990, 'y1': 382, 'top': 280, 'over': 50}],
                      [{'x0': -529, 'y0': -292, 'x1': -276, 'y1': 382, 'wall': '+x', 'hi': 300, 'lo': 250, 'gaps': (('-x', -120, 160),)}],
                      doors=[(-276, 30)], frames=[(-278, 30.5, 'y', 130, 176, 17.0, -1)], sign=(-300, -200, -284, 260, 300, 340))


def plantation_shop():
    """In place of NVOldWestBldgGeneric01: a butter-yellow shop, its lanai on the west. Its door stands shut, boarded."""
    return plantation('FOLabPlantationShop', 'butter', 'green', 14.0, -12.0,
                      [{'x0': -276, 'y0': -292, 'x1': 608, 'y1': 382, 'top': 320}],
                      [{'x0': -529, 'y0': -292, 'x1': -276, 'y1': 382, 'wall': '+x', 'hi': 292, 'lo': 244, 'gaps': (('-x', -150, 220),)}],
                      doors=[(-276, 28)], frames=[(-278, 28.5, 'y', 130, 176, 14.0, -1)], sign=(-300, -200, -284, 260, 290, 332))


def plantation_dry_goods():
    """In place of NVOldWestBldgGeneric02 (laid out as the saloon is): a barn-red dry goods store, a lanai on the west, a
    storeroom beside it whose doors are where the game's stand."""
    def extras(P):
        sx0, sy0, sx1, sy1 = -621, 61, -289, 299
        _box(P, sx0, sy0, -34, sx1, sy1, 20, 'plinth', material='stone')
        _box(P, sx0 + 4, sy0 + 4, 20, sx1 - 4, sy1 - 4, 290, 'boards')
        _tin_hip(P, sx0, sy0, sx1, sy1, 286, 120, 40)
        _frame_trim(P, -539, sy1, 'x', 92, 146, 18, 1)
        _frame_trim(P, -540, sy0, 'x', 92, 146, 18, -1)
        _box(P, -600, sy1 + 6, -30, -480, sy1 + 60, 8, 'floor')             # (a step outside its door)
    return plantation('FOLabPlantationDryGoods', 'red', 'red', 20.0, -8.0,
                      [{'x0': -289, 'y0': -580, 'x1': 888, 'y1': 560, 'top': 360}],
                      [{'x0': -615, 'y0': -580, 'x1': -289, 'y1': 61, 'wall': '+x', 'hi': 330, 'lo': 270, 'gaps': (('-x', -480, -20), ('-y', -560, -330))}],
                      doors=[(-289, -195)], frames=[(-292, -195, 'y', 92, 146, 18.0, -1)], sign=(-312, -460, -296, -40, 330, 376), extras=extras)


def plantation_school():
    """In place of NVGSSchoolHouse: a white schoolhouse in a T, a sky-blue trim of tin, steps up to its doors at the ends of
    its cross wing, a little entry porch at the foot of the T and a bell over it."""
    def extras(P):
        _box(P, -162, -900, -30, 178, -800, 20, 'plinth', material='stone')
        _box(P, -150, -890, 20, 166, -800, 280, 'boards')
        _tin_hip(P, -150, -890, 166, -800, 276, 90, 30)
        _box(P, -40, -862, 330, 56, -770, 440, 'trim', solid=False)          # (the bell's frame, standing on the roof)
        P.append({'shape': 'cone', 'r': 72, 'h': 80, 'sides': 4, 'phase': 45, 'at': [8, -816, 440], 'look': 'tin', 'solid': False, 'far': True})
        P.append({'shape': 'cylinder', 'r': 18, 'r2': 26, 'h': 34, 'sides': 10, 'at': [8, -816, 380], 'look': 'dark', 'solid': False})
        for x, sx in ((-644, -1), (644, 1)):                                  # (the steps up to each end door)
            _box(P, x + (sx * 70 if sx > 0 else -70), (390 if sx < 0 else 629) - 80, -30, x, (390 if sx < 0 else 629) + 80, 10, 'floor')
        _box(P, 365, -700, -20, 429, -500, 640, 'plinth', material='stone')    # (the chimney)
    return plantation('FOLabPlantationSchool', 'white', 'green', 18.0, -10.0,
                      [{'x0': -644, 'y0': 142, 'x1': 644, 'y1': 880, 'top': 400}, {'x0': -366, 'y0': -800, 'x1': 366, 'y1': 142, 'top': 380}],
                      doors=[(-644, 390), (644, 629)], frames=[(-650, 390, 'y', 92, 146, 18.0, -1), (650, 629, 'y', 92, 146, 18.0, 1)],
                      extras=extras)


def plantation_hall():
    """In place of NVNiptonTownHall: the town's hall, two storeys of white boards under a red tin roof, a raised middle with
    the door on its north face, a columned lanai along the south front."""
    def extras(P):
        _box(P, -572, -1300, -40, 572, -1110, 30, 'floor')
        for k in range(7):
            x = -540 + 1080 * k / 6
            P.append({'shape': 'cylinder', 'r': 20, 'h': 590, 'sides': 8, 'at': [x, -1270, 30], 'look': 'trim', 'material': 'wood'})
        _box(P, -600, -1300, 600, 600, -1110, 640, 'trim', solid=False)
        P.append({'shape': 'sheet', 'rows': [_line((-620, -1100, 700), (620, -1100, 700), 4), _line((-620, -1330, 640), (620, -1330, 640), 4)],
                  'look': 'tin', 'under_look': 'trim', 'thick': 5.0, 'at': [0, 0, 0], 'solid': False, 'far': True})
        _box(P, -585, 1440, -30, 584, 1530, 6, 'floor')                     # (the step before the door)
        _box(P, -180, 1442, 900, 180, 1452, 1040, 'board_blank', solid=False)
    return plantation('FOLabPlantationHall', 'white', 'red', 6.0, -10.0,
                      [{'x0': -1340, 'y0': -1100, 'x1': 1536, 'y1': 1000, 'top': 640, 'over': 80},
                       {'x0': -585, 'y0': 800, 'x1': 584, 'y1': 1440, 'top': 880, 'over': 60}],
                      doors=[(0, 1440)], frames=[(0, 1440, 'x', 256, 176, 0.0, 1)], extras=extras)


PIECES = {'beach_bar': ('Beach bar (for the Prospector Saloon)', beach_bar),
          'plantation_store': ('Plantation store (for the General Store)', plantation_store),
          'plantation_shop': ('Plantation shop (for the Wild West shop 01)', plantation_shop),
          'plantation_dry_goods': ('Plantation dry goods store (for the Wild West shop 02)', plantation_dry_goods),
          'plantation_school': ('Plantation schoolhouse (for the Goodsprings schoolhouse)', plantation_school),
          'plantation_hall': ('Plantation town hall (for the Nipton town hall)', plantation_hall)}
# (in place of which game building: its editor ID; restyle.py swaps every one the mod stands)
REPLACES = {'NVProspectorSaloon': 'beach_bar', 'NVGeneralStore': 'plantation_store', 'NVOldWestBldgGeneric01': 'plantation_shop',
            'NVOldWestBldgGeneric02': 'plantation_dry_goods', 'NVGSSchoolHouse': 'plantation_school', 'NVNiptonTownHall': 'plantation_hall'}
# the game's own in place of the game's own: billboards that name Mojave places for the neutral ones (Corvega's ad, a
# blank board), turn about; with how far to lift it (the Boulder City board stands from its foot, the others' legs reach
# 234 under their origin)
GAME_SWAPS = {'BillboardBoulderLNV': (('BillboardCarAV1', 'BillboardBlank01'), 214.0),
              'BillboardSunsetSarsaparillaNV': (('BillboardCarAV1', 'BillboardBlank01'), 0.0)}
waikikiset.LIGHTS.update({'beach_bar': [('FireBrightOrange', LANAI[0] - 70, LANAI[1] - 70, 200), ('ExtLightWarm02', (HATCHES[0] + HATCHES[1]) / 2, HALL[1] - 200, 260)]})
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
