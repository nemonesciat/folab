"""The coast's own: three more hotels of the late fifties (set 'hotel', each with a far model) and the one-off things
of a Hawaiian shore that read from far off and are worth walking to (set 'coast'): a lighthouse, a groin of concrete
running out to a pavilion, an aquarium, a freighter wrecked on the reef, a lattice mast on a headland.

Pieces of `modelsets` like any other, registered here at import as waikikiset's are. Frame: the middle of the thing's
foot at the origin, z up, its front towards -y, 70 units a metre; a hotel's front is its sea side (skyline turns it
so), as is the lighthouse's. Where each goes is `coastplace`'s. Names are made up for the place (no real business's).

What stands in the water (the groin, its pavilion, the wreck) has its origin where it meets the water: the groin's and
the pavilion's at the top of their deck, the wreck's at the middle of its keel; their sides reach far enough down to
meet any seabed near the shore."""
import math

import modelsets
import texpaint as tp
import waikikiset
from modelsets import FLOOR, limb, look


def _rainbow(w=128, h=1024, seed=140):
    """The end wall of a slab tower painted from foot to roof in bands of colour side by side: what the eye finds on a
    skyline from across the bay."""
    bands = [(214, 70, 60), (238, 128, 72), (246, 200, 90), (110, 176, 96), (72, 168, 178), (70, 104, 170), (132, 88, 158)]
    c = tp.Canvas(w, h)
    big, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 64)

    def fn(x, y):
        k = min(len(bands) - 1, int(x * len(bands) / w))
        g = fine.at(x * 64.0 / w, y * 64.0 / h * 4)
        f = (0.86 + 0.14 * g) * (0.9 + 0.12 * big.at(x * 8.0 / w, y * 8.0 / h * 3))
        edge = min(x * len(bands) / w - k, k + 1 - x * len(bands) / w)
        return tuple(v * f * (0.82 if edge < 0.05 else 1.0) for v in bands[k]), 0.48 + 0.04 * g
    c.paint(fn)
    return c


def _water(size=256, seed=141, colour=(62, 176, 186)):
    """A pool's water seen from beside it: turquoise with the bright lines the sun makes through ripples."""
    c = tp.Canvas(size, size)
    a, b = tp.Noise(seed, 16), tp.Noise(seed + 1, 16)

    def fn(x, y):
        u, v = x * 16.0 / size, y * 16.0 / size
        r = abs(a.at(u, v) - b.at(u + 3.1, v + 1.7))
        lit = max(0.0, 1 - r * 9) ** 2
        return tuple(min(255, ch * (0.9 + 0.1 * a.at(u * 0.5, v * 0.5)) + 90 * lit) for ch in colour), 0.5 + 0.06 * lit
    c.paint(fn)
    return c


def _tiles(size=256, seed=142, colour=(98, 196, 204), grout=(220, 226, 218), across=8):
    """Square pool tiles."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 64)
    step = size / float(across)

    def fn(x, y):
        gx, gy = x % step, y % step
        if gx < 1.5 or gy < 1.5:
            return grout, 0.42
        return tuple(v * (0.92 + 0.12 * fine.at(x * 64.0 / size, y * 64.0 / size)) for v in colour), 0.52
    c.paint(fn)
    return c


def _hedge(size=256, seed=143):
    """A clipped hedge's top in a planter: dense small leaves, no gaps."""
    c = tp.Canvas(size, size)
    n1, n2 = tp.Noise(seed, 32), tp.Noise(seed + 1, 64)

    def fn(x, y):
        g = n1.at(x * 32.0 / size, y * 32.0 / size) * 0.6 + n2.at(x * 64.0 / size, y * 64.0 / size) * 0.4
        return tp._mix((34, 76, 36), (118, 164, 74), g ** 1.3), 0.3 + 0.5 * g
    c.paint(fn)
    return c


SIGN_LINES = ['KAHALA REEF', 'MOANA KAI', 'HALE MALIA', 'AQUARIUM', '', 'DIAMOND HEAD LIGHT', 'PAVILION', 'NO DIVING']


def _signs(seed=144):
    """The coast's signs, one to a band an eighth of the picture high; the fifth band is a fish on a board."""
    grounds = [tp.CREAM, tp.TURQUOISE, tp.WHITE, tp.YELLOW, (150, 210, 200), tp.WHITE, tp.CREAM, tp.WHITE]
    inks = [tp.TEAL_INK, tp.WHITE, tp.RED, tp.TEAL_INK, tp.TEAL_INK, tp.TEAL_INK, tp.RED, tp.RED]
    edges = [tp.TURQUOISE, tp.CORAL, tp.PINK, tp.CORAL, tp.YELLOW, tp.TEAL_INK, tp.TURQUOISE, tp.RED]
    c = tp.sign([{'box': (0, n / 8.0, 1, (n + 1) / 8.0), 'lines': [t or ' '], 'ground': grounds[n], 'ink': inks[n], 'edge': edges[n]}
                 for n, t in enumerate(SIGN_LINES)], w=1024, h=1024, seed=seed)
    # the fish: a fat body, a tail, a fin, an eye, stripes, as a shop's painted board shows one
    y0, y1 = 4 * 128, 5 * 128
    cx, cy, rx, ry = 470.0, (y0 + y1) / 2.0, 300.0, 44.0
    body, belly, stripe = (238, 128, 72), (248, 204, 96), (24, 88, 96)

    def fish(x, y, col, h):
        u, v = (x - cx) / rx, (y - cy) / ry
        if u * u + v * v <= 1:
            k = (x - cx + rx) / (2 * rx)
            if 0.25 < k < 0.8 and int(k * 10) % 2 == 0:
                return stripe, 0.6
            return (belly if v > 0.35 else body), 0.62
        tx = x - (cx + rx - 20)
        if 0 <= tx <= 150 and abs(y - cy) <= 12 + tx * 0.32:
            return body, 0.6
        fx = x - (cx - 60)
        if 0 <= fx <= 160 and cy - ry - 26 + fx * 0.16 <= y <= cy - ry + 8:
            return stripe, 0.6
        return col, h
    c.rect(int(cx - rx - 4), y0 + 10, int(cx + rx + 160), y1 - 10, fish)
    for dx in range(-6, 7):
        for dy in range(-6, 7):
            if dx * dx + dy * dy <= 36:
                i = int(cy - 8 + dy) * c.w + int(cx - rx * 0.65 + dx)
                c.rgb[i] = (20, 20, 24)
    return c


modelsets.TEXTURES.update({
    'coast/signs': _signs,
    'coast/rainbow': _rainbow,
    'coast/water': _water,
    'coast/pool_tile': _tiles,
    'coast/hedge': _hedge,
    'coast/hull': lambda: tp.painted_metal((96, 40, 32), size=256, seed=145, rust=0.75),
    'coast/rust_white': lambda: tp.painted_metal(tp.WHITE, size=256, seed=146, rust=0.6),
    'coast/red': lambda: tp.painted_metal(tp.RED, seed=147, rust=0.2),
    'coast/wet_concrete': lambda: tp.concrete((132, 128, 114), seed=148),
    'coast/far_hull': lambda: tp.stucco((92, 52, 40), size=32, seed=149),
})
import texwear  # noqa: E402
modelsets.TEXTURES.update({k: v for k, v in texwear.UPGRADE().items() if k.startswith('coast/')})       # (in worn paint)


def _sign(n):
    return look('coast/signs', region=(0, n / 8.0, 1, (n + 1) / 8.0))


def _looks():
    out = modelsets._hotel_looks()
    out.update({'mural': look('coast/rainbow'), 'water': dict(look('coast/water', tile=512), gloss=80), 'pool': look('coast/pool_tile', tile=256),
                'hedge': look('coast/hedge', tile=256), 'red': look('coast/red', tile=128, far='hotel/far_plain_coral'), 'thatch': look('waikiki/thatch', tile=200),
                'wet': look('coast/wet_concrete', tile=256), 'glass': look('hotel/far_plain_glass', tile=128),
                'hull': look('coast/hull', tile=256, far='coast/far_hull'), 'rust_white': look('coast/rust_white', tile=256, far='hotel/far_plain_white'),
                'rust': look('city/rust', tile=96), 'concrete': look('concrete', tile=160), 'door': look('planks_coral', tile=96),
                'lamp': waikikiset.lit('waikiki/lamp_glass', 4.0), 'beacon': waikikiset.lit('waikiki/neon_red', 4.0)})
    for n in range(8):
        out['sign%d' % n] = _sign(n)
    return out


def _gable(parts, x, y, z, span, long, rise, look_name, yaw=0.0, far=False, solid=False, thick=14):
    """A pitched roof: two slabs meeting at a ridge `rise` over their eaves, the ridge along y (turned by yaw)."""
    run = span / 2.0
    a = math.degrees(math.atan2(rise, run))
    L = math.hypot(run, rise)
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for side in (-1, 1):
        lx = side * run / 2
        parts.append({'shape': 'slab', 'size': [L + 20, long, thick], 'at': [x + lx * c, y + lx * s, z + rise / 2 - thick / 2],
                      'turn': [0, side * a, yaw], 'look': look_name, 'solid': solid, 'far': far})


def _rooms(parts, x, y, z, wide, deep, floors, front, back, turn=0.0, lanai=70, ends='white', bottom=None):
    """A block of rooms with a slab at every floor reaching out front and back (modelsets' own, with an underside)."""
    parts.append({'shape': 'box', 'size': [wide, deep, floors * FLOOR], 'at': [x, y, z], 'turn': [0, 0, turn], 'look': ends,
                  'faces': {'front': front, 'back': back, 'top': 'deck', 'bottom': bottom}, 'material': 'stone', 'far': True})
    for f in range(1, floors + 1):
        parts.append({'shape': 'slab', 'size': [wide + 24, deep + 2 * lanai, 12], 'at': [x, y, z + f * FLOOR - 12], 'turn': [0, 0, turn], 'look': 'slab',
                      'solid': False})
    modelsets.lanai_detail(parts, x, y, z, wide, deep, floors, turn, lanai)
    modelsets.roof_plant(parts, x, y, z + floors * FLOOR, wide, deep, turn, seed=int(wide + floors))


# ---------- hotels ----------

def kahala_reef():
    """A resort along a quiet shore: long and low, four floors of rooms in two wings that bend towards the sea either
    side of a five-floor middle, on a terrace of lava rock; in front a lagoon pool with an island of palms, and between
    the two a dining hall under a steep A-frame roof whose gable looks out to sea."""
    parts = []
    deck = 120.0
    # the terrace under it all, and round the lagoon in front
    parts.append({'shape': 'box', 'size': [6900, 1800, deck], 'at': [0, 0, 0], 'look': 'lava', 'faces': {'top': 'deck'}, 'material': 'stone', 'far': True})
    for x0, x1 in ((-3450, -2200), (2200, 3450)):
        parts.append({'shape': 'box', 'size': [x1 - x0, 1800, deck], 'at': [(x0 + x1) / 2, -1800, 0], 'look': 'lava', 'faces': {'top': 'deck'}, 'material': 'stone', 'far': True})
    parts.append({'shape': 'box', 'size': [4400, 200, deck], 'at': [0, -2600, 0], 'look': 'lava', 'faces': {'top': 'deck'}, 'material': 'stone', 'far': True})
    # the lagoon: a tiled floor a metre down, water over it (not solid: one wades), a rim of lava rock, an island
    parts.append({'shape': 'box', 'size': [4400, 1600, 30], 'at': [0, -1700, 0], 'look': 'pool', 'material': 'stone'})
    parts.append({'shape': 'slab', 'size': [4400, 1600, 2], 'at': [0, -1700, deck - 22], 'look': 'water', 'faces': {'bottom': None}, 'solid': False, 'far': True})
    for (sx, sy, lx, ly) in ((0, -900 - 30, 4460, 60), (0, -2500 + 30, 4460, 60), (-2200 - 30 + 60, -1700, 60, 1600), (2200 + 30 - 60, -1700, 60, 1600)):
        parts.append({'shape': 'box', 'size': [lx, ly, deck + 24], 'at': [sx, sy, 0], 'look': 'lava', 'material': 'stone'})
    parts.append({'shape': 'cylinder', 'r': 320, 'h': deck + 40, 'sides': 10, 'at': [1100, -1750, 0], 'look': 'lava', 'material': 'stone'})
    parts.append({'shape': 'cylinder', 'r': 190, 'h': deck + 20, 'sides': 8, 'at': [-1300, -1550, 0], 'look': 'lava', 'material': 'stone'})
    # ramps up from the beach either side of the lagoon
    # (its top meets the terrace's edge at the terrace's height: a step up there more than a body climbs and nobody gets on)
    ramp, t = 640.0, 16.0
    a = math.atan2(deck, ramp - 40)
    for sx in (-2850, 2850):
        cy = -2700 - ramp / 2 * math.cos(a) + 20
        cz = deck - t / math.cos(a) - (ramp / 2 - 20) * math.sin(a)
        parts.append({'shape': 'slab', 'size': [520, ramp, t], 'at': [sx, cy, cz], 'turn': [math.degrees(a), 0, 0], 'look': 'deck', 'material': 'stone'})
    # the rooms: the middle five floors, the wings four, bent ten degrees towards the sea
    _rooms(parts, 0, 320, deck, 1536, 700, 5, 'lanai_t', 'lanai')
    for side in (-1, 1):
        a = -side * 10.0
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        half = 1280.0
        cx, cy = side * 768 + side * half * c, 380 + side * half * s
        _rooms(parts, cx, cy, deck, 2560, 640, 4, 'lanai_t', 'lanai', turn=a)
    # the dining hall: open sides on posts, its A-frame roof running out towards the sea
    for x in (-460, 460):
        for y in (-820, -520, -220):
            parts.append({'shape': 'cylinder', 'r': 22, 'h': 300, 'sides': 8, 'at': [x, y, deck], 'look': 'coral'})
    _gable(parts, 0, -520, deck + 260, 1200, 860, 980, 'thatch', far=True)
    parts.append({'shape': 'box', 'size': [1150, 20, 140], 'at': [0, -950, deck + 300], 'look': 'coral', 'solid': False})
    # its name over the middle's roof, both ways
    top = deck + 5 * FLOOR
    parts.append({'shape': 'box', 'size': [2000, 24, 250], 'at': [0, 100, top], 'look': 'white', 'faces': {'front': 'sign0', 'back': 'sign0'}, 'solid': False, 'far': True})
    desc = {'name': 'FOLabHotelKahalaReef', 'looks': _looks(), 'parts': parts}
    palm = modelsets.palm('p', tall=600, lean=18, fronds=15, seed=11)
    palm2 = modelsets.palm('q', tall=480, lean=26, fronds=13, seed=12)
    for tree in (palm, palm2):                  # (on an island in the pool nobody walks into them: no collision, none to go wrong)
        for q in tree['parts']:
            q['solid'] = False
    return modelsets.combine('FOLabHotelKahalaReef', [(desc, 0, 0, 0, 1.0), (palm, 1080, -1720, 30, 1.0), (palm2, 1180, -1820, 200, 1.0),
                                                       (palm2, -1300, -1560, 120, 1.0)])


def moana_kai():
    """The tall one: a slab of twenty-six floors held up on columns over an open glass lobby, its two end walls painted
    from the ground to the roof in bands of colour, a glass lift running up the outside of its front to a restaurant
    on the roof, a lower wing of shops behind."""
    parts = []
    up, floors = 2 * FLOOR, 26
    for x in range(-896, 897, 256):
        for y in (-190, 190):
            parts.append({'shape': 'cylinder', 'r': 42, 'h': up, 'sides': 10, 'at': [x, y, 0], 'look': 'white', 'material': 'stone', 'far': True})
    parts.append({'shape': 'box', 'size': [1500, 300, up - 40], 'at': [0, 0, 0], 'look': 'shop', 'faces': {'top': None, 'bottom': None}, 'material': 'stone'})
    _rooms(parts, 0, 0, up, 2048, 512, floors, 'lanai', 'lanai_c', ends='mural', bottom='slab')
    top = up + floors * FLOOR
    # the lift up the front, and its car near the top, lit
    parts.append({'shape': 'box', 'size': [200, 200, top + 300], 'at': [760, -380, 0], 'look': 'glass', 'material': 'stone', 'far': True})
    parts.append({'shape': 'box', 'size': [170, 20, 230], 'at': [760, -485, up + 19 * FLOOR], 'look': 'lamp', 'solid': False})
    parts.append({'shape': 'box', 'size': [120, 300, 40], 'at': [760, -260, top + 260], 'look': 'white', 'solid': False})
    # the restaurant on the roof under a wide lid, and the name over it
    parts.append({'shape': 'box', 'size': [1700, 460, 300], 'at': [-150, 0, top], 'look': 'shop', 'faces': {'top': 'deck'}, 'material': 'stone', 'far': True})
    parts.append({'shape': 'slab', 'size': [2100, 760, 30], 'at': [-150, 0, top + 300], 'look': 'white', 'far': True})
    parts.append({'shape': 'box', 'size': [1900, 30, 330], 'at': [-150, 0, top + 330], 'look': 'white', 'faces': {'front': 'sign1', 'back': 'sign1'}, 'solid': False, 'far': True})
    parts.append({'shape': 'ball', 'r': 26, 'sides': 6, 'rings': 3, 'at': [-1060, 0, top + 340], 'look': 'beacon', 'solid': False})
    parts.append({'shape': 'ball', 'r': 26, 'sides': 6, 'rings': 3, 'at': [760, 0, top + 340], 'look': 'beacon', 'solid': False})
    # the wing of shops behind, its roof a sun deck
    parts.append({'shape': 'box', 'size': [3000, 1400, 3 * FLOOR], 'at': [0, 1150, 0], 'look': 'white', 'faces': {'front': 'shop', 'back': 'shop', 'top': 'deck'},
                  'material': 'stone', 'far': True})
    parts.append({'shape': 'slab', 'size': [3100, 1500, 20], 'at': [0, 1150, 3 * FLOOR], 'look': 'slab', 'solid': False})
    for side in (-1, 1):                        # a canopy over the drive, out from the lobby
        parts.append({'shape': 'slab', 'size': [700, 900, 16], 'at': [side * 380, -700, 390], 'turn': [0, side * 8, 0], 'look': 'white', 'faces': {'bottom': 'coral'}})
    for x in (-650, 650):
        parts.append({'shape': 'box', 'size': [24, 24, 400], 'at': [x, -1050, 0], 'look': 'coral'})
    return {'name': 'FOLabHotelMoanaKai', 'looks': _looks(), 'parts': parts}


def hale_malia():
    """Twelve floors stepped back from the sea one bay at a time, every floor's roof a terrace with a hedge along its
    edge, so that from the side it is a pyramid of gardens; the back goes straight up. A pavilion under a pointed
    roof on top."""
    parts = []
    floors, base, back, wide = 12, 2304.0, 1152.0, 3072.0
    for f in range(floors):
        d = base - 192.0 * f * (base - 640) / (192.0 * (floors - 1))
        y = back - d / 2
        parts.append({'shape': 'box', 'size': [wide, d, FLOOR], 'at': [0, y, f * FLOOR], 'look': 'pink',
                      'faces': {'front': 'lanai_c', 'left': 'blocks', 'right': 'blocks', 'top': 'deck', 'bottom': None}, 'material': 'stone', 'far': True})
        parts.append({'shape': 'slab', 'size': [wide + 30, 14, 12], 'at': [0, back - d - 7, (f + 1) * FLOOR - 12], 'look': 'slab', 'solid': False})
        if f < floors - 1:
            nd = base - 192.0 * (f + 1) * (base - 640) / (192.0 * (floors - 1))
            room = d - nd
            parts.append({'shape': 'box', 'size': [wide - 40, 60, 80], 'at': [0, back - d + 40, (f + 1) * FLOOR], 'look': 'pink', 'faces': {'top': 'hedge'}, 'material': 'stone'})
            if room > 300:
                parts.append({'shape': 'box', 'size': [wide - 40, 50, 70], 'at': [0, back - nd - 40, (f + 1) * FLOOR], 'look': 'pink', 'faces': {'top': 'hedge'}, 'solid': False})
    top = floors * FLOOR
    parts.append({'shape': 'box', 'size': [700, 400, 300], 'at': [0, back - 320, top], 'look': 'white', 'faces': {'front': 'shop'}, 'material': 'stone', 'far': True})
    parts.append({'shape': 'cone', 'r': 620, 'h': 420, 'sides': 4, 'at': [0, back - 320, top + 300], 'turn': [0, 0, 45], 'look': 'coral', 'far': True})
    parts.append({'shape': 'box', 'size': [2200, 24, 260], 'at': [0, back - 640 + 30, top], 'look': 'white', 'faces': {'front': 'sign2'}, 'solid': False, 'far': True})
    # a porch at the foot of the front
    parts.append({'shape': 'slab', 'size': [1400, 500, 20], 'at': [0, -back - 250, 330], 'look': 'white', 'faces': {'bottom': 'coral'}, 'solid': False})
    for x in (-650, -220, 220, 650):
        parts.append({'shape': 'cylinder', 'r': 18, 'h': 330, 'sides': 8, 'at': [x, -back - 470, 0], 'look': 'white'})
    return {'name': 'FOLabHotelHaleMalia', 'looks': _looks(), 'parts': parts}


# ---------- the coast's one-offs ----------

def lighthouse():
    """A lighthouse on a point: a square white tower tapering to a gallery, the lantern glazed all round under a red
    roof (lit), a keeper's cottage beside it with a red roof, a low white wall round the yard."""
    parts = []
    H = 1300.0
    parts.append({'shape': 'cylinder', 'r': 212, 'r2': 170, 'h': H, 'sides': 4, 'turn': [0, 0, 45], 'look': 'white', 'material': 'stone', 'far': True})
    parts.append({'shape': 'box', 'size': [90, 10, 200], 'at': [0, -151, 0], 'look': 'door', 'solid': False})
    parts.append({'shape': 'slab', 'size': [400, 400, 24], 'at': [0, 0, H], 'look': 'white', 'far': True})
    for k in range(4):
        a = k * 90
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        parts.append({'shape': 'box', 'size': [400, 8, 70], 'at': [s * 196, -c * 196, H + 24], 'turn': [0, 0, a], 'look': 'red', 'solid': False})
    parts.append({'shape': 'cylinder', 'r': 112, 'h': 190, 'sides': 8, 'at': [0, 0, H + 24], 'look': 'lamp', 'cap_look': 'red', 'far': True})
    parts.append({'shape': 'cone', 'r': 150, 'h': 130, 'sides': 8, 'at': [0, 0, H + 214], 'look': 'red', 'far': True})
    parts.append({'shape': 'ball', 'r': 26, 'sides': 6, 'rings': 3, 'at': [0, 0, H + 350], 'look': 'red', 'solid': False})
    # the cottage
    parts.append({'shape': 'box', 'size': [900, 560, 300], 'at': [-760, 180, 0], 'look': 'white', 'faces': {'front': 'shop'}, 'material': 'stone', 'far': True})
    _gable(parts, -760, 180, 300, 640, 980, 220, 'red', yaw=90, far=True, solid=True)
    parts.append({'shape': 'box', 'size': [100, 10, 210], 'at': [-500, -102, 0], 'look': 'door', 'solid': False})
    # the yard's wall, open to the front
    for (x, y, lx, ly) in ((-280, 560, 1700, 30), (-1240, 120, 30, 900), (580, 120, 30, 900), (-860, -330, 760, 30), (380, -330, 380, 30)):
        parts.append({'shape': 'box', 'size': [lx, ly, 70], 'at': [x, y, 0], 'look': 'white', 'material': 'stone'})
    return {'name': 'FOLabCoastLighthouse', 'looks': _looks(), 'parts': parts}


GROIN_STEP = 512.0          # one length of the groin's walk
GROIN_DOWN = 700.0          # how far its sides reach under its top


def groin_walk():
    """One length of a groin: a walk of concrete running out from the beach, a kerb along each side."""
    parts = [{'shape': 'box', 'size': [300, GROIN_STEP, GROIN_DOWN], 'at': [0, 0, -GROIN_DOWN], 'look': 'wet', 'faces': {'top': 'concrete', 'bottom': None},
              'material': 'stone', 'far': True}]
    for sx in (-1, 1):
        parts.append({'shape': 'box', 'size': [34, GROIN_STEP, 40], 'at': [sx * 133, 0, 0], 'look': 'concrete', 'material': 'stone'})
    return {'name': 'FOLabCoastGroinWalk', 'looks': _looks(), 'parts': parts}


def groin_pavilion():
    """Where the groin ends: a round platform, and on it a pavilion open on six sides under a thatched roof, with
    benches; a rail round the edge, open towards the shore where the walk comes in."""
    parts = [{'shape': 'cylinder', 'r': 540, 'h': GROIN_DOWN, 'sides': 16, 'at': [0, 0, -GROIN_DOWN], 'look': 'wet', 'cap_look': 'concrete', 'material': 'stone', 'far': True}]
    for k in range(6):
        a = math.radians(30 + 60 * k)
        parts.append({'shape': 'cylinder', 'r': 18, 'h': 300, 'sides': 8, 'at': [math.cos(a) * 380, math.sin(a) * 380, 0], 'look': 'coral'})
        b = math.radians(60 * k)
        parts.append({'shape': 'box', 'size': [300, 60, 46], 'at': [math.cos(b) * 300, math.sin(b) * 300, 0], 'turn': [0, 0, math.degrees(b) + 90], 'look': 'wood'})
    parts.append({'shape': 'cone', 'r': 480, 'h': 230, 'sides': 6, 'at': [0, 0, 300], 'turn': [0, 0, 30], 'look': 'thatch', 'far': True})
    parts.append({'shape': 'cylinder', 'r': 470, 'h': 14, 'sides': 6, 'at': [0, 0, 290], 'turn': [0, 0, 30], 'look': 'coral', 'solid': False})
    for k in range(16):
        a = 2 * math.pi * (k + 0.5) / 16
        if math.sin(a) < -0.85:
            continue                            # (the way in, from the walk)
        parts.append({'shape': 'box', 'size': [200, 14, 80], 'at': [math.cos(a) * 520, math.sin(a) * 520, 0], 'turn': [0, 0, math.degrees(a) + 90], 'look': 'white'})
    looks = dict(_looks(), wood=look('planks_cream', tile=96))
    return {'name': 'FOLabCoastGroinPavilion', 'looks': looks, 'parts': parts}


def aquarium():
    """A low aquarium of the fifties by the shore: glass all along its front under a folded roof of six pleats, its
    name along the roof's edge, a fish on a pylon by the door."""
    parts = []
    w, d, h = 1800.0, 1000.0, 380.0
    parts.append({'shape': 'box', 'size': [w, d, h], 'at': [0, 0, 0], 'look': 'white', 'faces': {'front': 'shop', 'back': 'blocks', 'top': 'deck'}, 'material': 'stone', 'far': True})
    n = 6
    for k in range(n):
        x = -w / 2 + w * (k + 0.5) / n
        parts.append({'shape': 'slab', 'size': [w / n + 10, d + 260, 14], 'at': [x, 0, h + 60], 'turn': [0, (14 if k % 2 else -14), 0], 'look': 'white',
                      'faces': {'bottom': 'coral'}, 'far': True})
    parts.append({'shape': 'box', 'size': [1400, 20, 180], 'at': [0, -d / 2 - 140, h + 100], 'look': 'white', 'faces': {'front': 'sign3', 'back': 'sign3'}, 'solid': False, 'far': True})
    for x in (-600, 600):
        parts.append({'shape': 'box', 'size': [24, 24, h + 100], 'at': [x, -d / 2 - 140, 0], 'look': 'white'})
    parts.append({'shape': 'box', 'size': [60, 60, 900], 'at': [-1150, -650, 0], 'look': 'red', 'material': 'stone'})
    parts.append({'shape': 'box', 'size': [560, 24, 300], 'at': [-1150, -695, 700], 'look': 'white', 'faces': {'front': 'sign4', 'back': 'sign4'}, 'solid': False, 'far': True})
    parts.append({'shape': 'slab', 'size': [1200, 500, 40], 'at': [0, -d / 2 - 250, 0], 'look': 'deck', 'solid': False})
    return {'name': 'FOLabCoastAquarium', 'looks': _looks(), 'parts': parts}


WRECK_HIGH = 560.0      # keel to deck


def wreck():
    """A small freighter that went onto the reef and stayed: rust from the waterline up, its bridge and funnel aft, two
    masts with their derricks over the hatches. Its origin is the middle of its keel; it is stood with its stern
    down, so its deck runs up out of the sea from the water's edge."""
    parts = []
    H = WRECK_HIGH
    parts.append({'shape': 'box', 'size': [600, 2600, H], 'at': [0, -100, 0], 'look': 'hull', 'faces': {'top': 'rust', 'bottom': None}, 'material': 'metal', 'far': True})
    parts.append({'shape': 'cylinder', 'r': 346, 'h': H, 'sides': 3, 'at': [0, 1200 + 346, 0], 'turn': [0, 0, 90], 'scale': [2.0, 1, 1], 'look': 'hull', 'cap_look': 'rust',
                  'material': 'metal', 'far': True})
    parts.append({'shape': 'cylinder', 'r': 300, 'h': H, 'sides': 12, 'at': [0, -1400, 0], 'look': 'hull', 'cap_look': 'rust', 'material': 'metal', 'far': True})
    parts.append({'shape': 'box', 'size': [540, 620, 360], 'at': [0, -1050, H], 'look': 'rust_white', 'faces': {'top': 'rust'}, 'material': 'metal', 'far': True})
    parts.append({'shape': 'box', 'size': [600, 280, 220], 'at': [0, -900, H + 360], 'look': 'rust_white', 'faces': {'front': 'glass'}, 'material': 'metal', 'far': True})
    parts.append({'shape': 'cylinder', 'r': 82, 'h': 420, 'sides': 10, 'at': [0, -1240, H + 360], 'turn': [-8, 0, 0], 'look': 'hull', 'material': 'metal', 'far': True})
    for y in (200, 900):
        parts.append({'shape': 'cylinder', 'r': 18, 'h': 900, 'sides': 6, 'at': [0, y, H], 'look': 'rust', 'solid': False, 'far': True})
        parts.append(limb((0, y, H + 160), (0, y + 520, H + 520), 8, 5, 'rust', sides=4))
        parts.append({'shape': 'box', 'size': [380, 420, 70], 'at': [0, y + 330, H], 'look': 'rust', 'material': 'metal'})
    for sx in (-1, 1):                          # rails along the deck, gone in places
        for y0, y1 in ((-700, -200), (100, 600), (850, 1150)):
            parts.append({'shape': 'box', 'size': [8, y1 - y0, 60], 'at': [sx * 292, (y0 + y1) / 2, H], 'look': 'rust', 'solid': False})
    return {'name': 'FOLabCoastWreck', 'looks': _looks(), 'parts': parts}


MAST_HIGH = 3400.0


def signal_mast():
    """A lattice mast on a headland, banded red and white for the aircraft, a red light at its top (lit), a hut of
    concrete at its foot."""
    parts = []
    H, b0, b1, n = MAST_HIGH, 260.0, 55.0, 12
    half = lambda z: b0 + (b1 - b0) * z / H
    corners = lambda z: [(sx * half(z), sy * half(z), z) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for k in range(n):
        z0, z1 = H * k / n, H * (k + 1) / n
        lk = 'red' if (k // 2) % 2 == 0 else 'white_metal'
        lo, hi = corners(z0), corners(z1)
        for c in range(4):
            leg = limb(lo[c], hi[c], 15, 13, lk, sides=4, solid=True)
            leg['far'] = True
            parts.append(leg)
            j = (c + 1) % 4
            parts.append(limb(lo[c], hi[j], 5, 5, lk, sides=3))
            parts.append(limb(lo[j], hi[c], 5, 5, lk, sides=3))
            parts.append(limb(hi[c], hi[j], 5, 5, lk, sides=3))
    parts.append({'shape': 'slab', 'size': [180, 180, 14], 'at': [0, 0, H], 'look': 'red', 'solid': False})
    parts.append({'shape': 'cylinder', 'r': 8, 'h': 260, 'sides': 5, 'at': [0, 0, H], 'look': 'white_metal', 'solid': False, 'far': True})
    parts.append({'shape': 'ball', 'r': 30, 'sides': 6, 'rings': 3, 'at': [0, 0, H + 270], 'look': 'beacon', 'solid': False})
    for z in (H * 0.5, H * 0.75):
        parts.append({'shape': 'ball', 'r': 20, 'sides': 6, 'rings': 3, 'at': [half(z) + 20, 0, z], 'look': 'beacon', 'solid': False})
    for k in range(3):                          # the aerials
        a = k * 120
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        parts.append({'shape': 'box', 'size': [40, 18, 260], 'at': [c * (b1 + 40), s * (b1 + 40), H - 520], 'turn': [0, 0, a], 'look': 'white_metal', 'solid': False})
    parts.append({'shape': 'box', 'size': [380, 300, 260], 'at': [0, -560, 0], 'look': 'concrete', 'material': 'stone'})
    parts.append({'shape': 'slab', 'size': [430, 350, 16], 'at': [0, -560, 260], 'look': 'concrete', 'solid': False})
    parts.append({'shape': 'box', 'size': [90, 8, 200], 'at': [0, -714, 0], 'look': 'rust', 'solid': False})
    parts.append({'shape': 'slab', 'size': [700, 1300, 20], 'at': [0, -260, 0], 'look': 'concrete', 'solid': False})
    looks = dict(_looks(), white_metal=look('metal_white', tile=64))
    return {'name': 'FOLabCoastMast', 'looks': looks, 'parts': parts}


HOTELS = {
    'kahala_reef': ('Kahala Reef', kahala_reef),
    'moana_kai': ('Moana Kai', moana_kai),
    'hale_malia': ('Hale Malia Terraces', hale_malia),
}
PIECES = {
    'lighthouse': ('Lighthouse', lighthouse),
    'groin_walk': ('Groin, one length', groin_walk),
    'groin_pavilion': ('Groin pavilion', groin_pavilion),
    'aquarium': ('Aquarium', aquarium),
    'wreck': ('Wrecked freighter', wreck),
    'signal_mast': ('Signal mast', signal_mast),
}
waikikiset.LIGHTS.update({
    'lighthouse': [('StripLightKeyNeutral', 0, 0, 1420)],
    'signal_mast': [('NVLightNeonRed', 0, 0, MAST_HIGH + 200)],
    'groin_pavilion': [('ExtLightWarm02', 0, 0, 240)],
    'moana_kai': [('ExtLightWarm02', 0, -600, 340)],
})
for _k, (_label, _fn) in HOTELS.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': 'hotel', 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': 'coast', 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
