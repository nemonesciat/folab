"""Inside the historic hotels: the rooms that stand in a hotel's own small world (viewworld.py) so their windows look out
on Waikiki, the lobby on the ground floor and a lookout at the top, as the Lucky 38's lounge and penthouse do over the
Strip. The guest floors between are ordinary places (hotelfloors.py).

The Royal Hawaiian open (`historicset.royal_hawaiian(open_=True)`, piece 'royal_hawaiian_open'): the hotel as it stands
outside, but its ground floor a lobby two floors high (`LH`) the length of the main block. Arched windows down both
long sides, glazed (dirty glass you can't walk through, `glass`) save the doorway in the middle of the town side under
the carriage porch, where you come in; the middle of the sea side steps out under the tower into a bay of three tall
arches over the loggia and the lawn. A floor of pink and cream marble squares, cracked and stained (`marble`); a
ceiling of plaster with dark koa beams across (`koa`); the front desk koa too, the pigeonholes for keys behind it. At
the top of the tower the belvedere is a lookout, its arches open on all four sides over a balustrade you can't fall
over, a stair head in the middle with its door.

`RH_THINGS` furnishes the lobby with the game's own things (Tenpenny Tower's chandeliers, the Tops' planters and
lamps, hotel chairs and sofas, suitcases) and those who live there now (mattresses, a fire barrel, sandbags at the
door, trash), in the building's frame: x along it, y to the town side, z over its floor, face in degrees (0 +y, 90
+x). `RH_DOORS` are the doors, named for linking: the way in, the lift to the guest floors, the lookout's stair head.
Frame and units as historicset (front to -y the sea, 70 units a metre)."""
import math
import random

import historicset as hs
import modelsets
import texpaint as tp
import texwear as tw
from modelsets import FLOOR, look
from texwear import Field, Picture, grade, mix, mul

LH = 2 * FLOOR                  # (the lobby's height: two of the hotel's floors)
FLOOR_TOP = 8.0                 # (the ground floor's top over the piece's foot)
WALL = 40
PIER = 100
SPRING = 330                    # (where a window's arch springs)
ARCH = 150                      # (and how high the arch is)
TOWER_BAY = 120                 # (how far the bay under the tower stands out of the sea face)

PINK_INSIDE = (232, 176, 168)
CREAM = (232, 222, 200)
KOA = (104, 62, 36)


def marble(size=512, seed=1300, squares=4, a=(222, 168, 160), b=(232, 224, 206)):
    """Marble squares, pink and cream on the diagonal, veined, cracked, a stain or two and the shine worn off by feet."""
    rnd = random.Random(seed)
    veins = Field(size, size, seed + 1, 3, 6)
    fine = Field(size, size, seed + 2, 10, 3)
    crack = tw.cracks(size, size, seed + 3, count=7)
    pic = Picture(size, size, gloss=60)
    step = size // squares
    stains = [(rnd.randrange(size), rnd.randrange(size), rnd.randrange(size // 10, size // 4)) for _ in range(4)]
    for y in range(size):
        for x in range(size):
            p = y * size + x
            c = a if ((x // step) + (y // step)) % 2 else b
            vein = max(0.0, 1.0 - abs(veins.v[p] - 0.5) * 22.0)
            c = mix(c, mul(c, 0.72), vein * 0.6)
            c = mul(c, 0.94 + 0.08 * fine.v[p])
            ht = 0.5
            if x % step < 2 or y % step < 2:
                c, ht = mul(c, 0.62), 0.42             # (the grout)
            if crack[p] > 0:
                c, ht = mix(c, mul(c, 0.45), crack[p]), 0.5 - 0.15 * crack[p]
            for cx, cy, r in stains:               # (water through the ceiling, a fire)
                d = math.hypot(x - cx, y - cy) / r
                if d < 1:
                    c = mix(c, mul(c, 0.6), (1 - d) * 0.5 * (0.6 + 0.4 * fine.v[p]))
            pic.rgb[p], pic.ht[p] = grade(c), ht
            pic.gloss[p] = int(20 + 50 * (1 - fine.v[p]))
    return pic


def ceiling(size=512, seed=1310):
    """Plaster between the beams, gone to brown where the rain got in."""
    return tw.render(CREAM, under=(196, 180, 150), size=size, seed=seed, peel=0.45, cracks_=0.5)


def koa(size=256, seed=1320):
    """Koa, varnished long ago, the varnish gone cloudy and worn through at the edges (the Missouri's veneer, darker)."""
    from shipinside import veneer
    return veneer(KOA, size=size, seed=seed)


def glass(size=256, seed=1330):
    """Old window glass: grimy, streaked, a little green, seen through. Its alpha is how much it hides."""
    dirt = Field(size, size, seed, 4, 5)
    streak = Field(size, size, seed + 1, 2, 3, stretch=(4, 0.25))
    pic = Picture(size, size, clear=(150, 170, 160), gloss=120)
    for p in range(size * size):
        d, s = dirt.v[p], streak.v[p]
        pic.rgb[p] = grade(mix((150, 170, 160), (120, 108, 86), d))
        pic.a[p] = min(0.85, 0.2 + 0.4 * d * d + 0.15 * s)
    return pic


def keys(w=512, h=256, seed=1340):
    """The pigeonholes behind the desk, a key or a note in some."""
    rnd = random.Random(seed)
    wood = koa(256, seed + 1)
    pic = Picture(w, h)
    for y in range(h):
        for x in range(w):
            pic.rgb[y * w + x] = wood.rgb[(y % 256) * 256 + x % 256]
    cols, rows = 16, 6
    cw, rh = w / cols, h / rows
    for i in range(cols):
        for j in range(rows):
            x0, y0 = int(i * cw + 4), int(j * rh + 4)
            for y in range(y0, int(y0 + rh - 8)):
                for x in range(x0, int(x0 + cw - 8)):
                    pic.rgb[y * w + x], pic.ht[y * w + x] = grade((28, 20, 14)), 0.3
            if rnd.random() < 0.35:                 # (a key's tag or a note left in it)
                kx, ky = x0 + rnd.randrange(3, max(4, int(cw) - 14)), y0 + rnd.randrange(3, max(4, int(rh) - 14))
                col = grade(rnd.choice([(196, 170, 110), (210, 204, 186), (150, 120, 60)]))
                for y in range(ky, min(h, ky + 6)):
                    for x in range(kx, min(w, kx + 4)):
                        pic.rgb[y * w + x], pic.ht[y * w + x] = col, 0.45
    return pic


def rug(w=512, h=256, seed=1350):
    """A long rug of the hotel's: a border of hibiscus red round a field of faded green, worn to the threads down the middle."""
    worn = Field(w, h, seed, 3, 4)
    pic = Picture(w, h, gloss=4)
    for y in range(h):
        for x in range(w):
            p = y * w + x
            edge = min(min(x, w - 1 - x) / w * 4, min(y, h - 1 - y) / h * 2)
            c = (150, 46, 50) if edge < 0.16 else ((210, 190, 140) if edge < 0.2 else (70, 104, 80))
            if edge >= 0.2 and ((x // 32) + (y // 32)) % 2 == 0 and (x % 32 - 16) ** 2 + (y % 32 - 16) ** 2 < 60:
                c = (196, 120, 110)                 # (the flowers on the field)
            mid = max(0.0, 1.0 - abs(y - h / 2) / (h * 0.3))
            c = mix(c, (150, 136, 110), mid * 0.5 * worn.v[p])
            pic.rgb[p] = grade(c)
    return pic


modelsets.TEXTURES.update({
    'hist/rhl_marble': marble,
    'hist/rhl_ceiling': ceiling,
    'hist/rhl_koa': koa,
    'hist/rhl_glass': glass,
    'hist/rhl_keys': keys,
    'hist/rhl_rug': rug,
    'hist/rhl_inside': lambda: tw.render(PINK_INSIDE, under=(220, 206, 186), size=512, seed=1360, peel=0.4),
    'hist/rhl_arch_sea': lambda: hs.arch_board(3, 880, ARCH, PIER, colour=hs.PINK, seed=1361),
    'hist/rhl_arch_bay': lambda: hs.arch_board(3, 640, ARCH, PIER, colour=hs.PINK, seed=1362),
    'hist/rhl_arch_town': lambda: hs.arch_board(9, 3600, ARCH, PIER, colour=hs.PINK, seed=1363),
    'hist/rhl_arch_end': lambda: hs.arch_board(2, 600, ARCH, PIER, colour=hs.PINK, w=512, seed=1364),
    'hist/rhl_rail': lambda: hs.balustrade(256, hs.PINK, seed=1365),
})


def looks():
    return {
        'rhl_marble': look('hist/rhl_marble', tile=512),
        'rhl_ceiling': look('hist/rhl_ceiling', tile=512),
        'rhl_koa': look('hist/rhl_koa', tile=256),
        'rhl_glass': dict(look('hist/rhl_glass', tile=400), alpha=True),
        'rhl_keys': look('hist/rhl_keys'),
        'rhl_rug': look('hist/rhl_rug'),
        'rhl_inside': look('hist/rhl_inside', tile=512),
        'rhl_arch_sea': dict(look('hist/rhl_arch_sea'), alpha=True),
        'rhl_arch_bay': dict(look('hist/rhl_arch_bay'), alpha=True),
        'rhl_arch_town': dict(look('hist/rhl_arch_town'), alpha=True),
        'rhl_arch_end': dict(look('hist/rhl_arch_end'), alpha=True),
        'rhl_rail': dict(look('hist/rhl_rail', tile=96), alpha=True),
    }


def _wall(P, x0, x1, y, z0=0.0, z1=LH, along='x', out='rh_plain'):
    """A plain stretch of wall, pink outside, plaster inside (inside is towards the middle of the building)."""
    n = (x1 - x0)
    mid = (x0 + x1) / 2.0
    if along == 'x':
        inner = 'back' if y < 0 else 'front'
        faces = {'front': out, 'back': out, inner: 'rhl_inside'}
        hs._box(P, [n, WALL, z1 - z0], [mid, y, z0], out, **faces)
    else:
        inner = 'right' if y < 0 else 'left'        # (y here is the wall's x)
        faces = {'left': out, 'right': out, inner: 'rhl_inside'}
        hs._box(P, [WALL, n, z1 - z0], [y, mid, z0], out, **faces)


def _windows(P, n, W, x, y, board, along='x', door_at=None):
    """A row of n arched windows W long, glazed; door_at: the offset along of a bay left open (a doorway)."""
    hs._arcade(P, n, W, ARCH, PIER, x, y, 0.0, SPRING, board, 'rh_plain', depth=WALL, along=along, board_depth=WALL - 10)
    top = SPRING + ARCH
    if along == 'x':
        hs._box(P, [W, WALL, LH - top], [x, y, top], 'rh_plain', **faces_inner(y, 'x'))
    else:
        hs._box(P, [WALL, W, LH - top], [x, y, top], 'rh_plain', **faces_inner(x, 'y'))
    # the glass, a little inside the wall's middle (both sides seen), in one piece or round the doorway
    spans = [(-W / 2.0, W / 2.0)]
    if door_at is not None:
        half = W / float(n) / 2.0
        spans = [(-W / 2.0, door_at - half + PIER / 2.0), (door_at + half - PIER / 2.0, W / 2.0)]
    inward = 1 if (y if along == 'x' else x) < 0 else -1
    for a, b in spans:
        if b - a < 10:
            continue
        m = (a + b) / 2.0
        if along == 'x':
            hs._box(P, [b - a, 12, top - 4], [x + m, y + inward * 2, 2], 'rhl_glass', material='glass',
                    front='rhl_glass', back='rhl_glass', left=None, right=None, top=None, bottom=None)
        else:
            hs._box(P, [12, b - a, top - 4], [x + inward * 2, y + m, 2], 'rhl_glass', material='glass',
                    front=None, back=None, left='rhl_glass', right='rhl_glass', top=None, bottom=None)


def faces_inner(v, along):
    if along == 'x':
        return {'front' if v > 0 else 'back': 'rhl_inside'}
    return {'left' if v > 0 else 'right': 'rhl_inside'}


def rh_lobby(P):
    """The lobby's walls, windows, floor, beams and desk (the block over it is historicset's, from LH up)."""
    W2, D2 = hs.RH_W / 2.0, hs.RH_D / 2.0
    ys, yt = -(D2 - WALL / 2.0), D2 - WALL / 2.0           # (the sea wall's middle, the town wall's)
    # the sea side: the wings' ends plain, three windows each side of the tower's bay
    _wall(P, -W2, -1200, ys)
    _wall(P, 1200, W2, ys)
    _windows(P, 3, 880, -760, ys, 'rhl_arch_sea')
    _windows(P, 3, 880, 760, ys, 'rhl_arch_sea')
    yb = -(D2 + TOWER_BAY - WALL / 2.0)
    _windows(P, 3, 640, 0, yb, 'rhl_arch_bay')
    for sx in (-1, 1):                                      # (the bay's sides)
        hs._box(P, [WALL, TOWER_BAY, LH], [sx * (320 - WALL / 2.0), -(D2 + TOWER_BAY / 2.0), 0], 'rh_plain',
                **({'right' if sx < 0 else 'left': 'rhl_inside'}))
    # the town side: nine windows, the middle one the doorway; plain at the ends
    _windows(P, 9, 3600, 0, yt, 'rhl_arch_town', door_at=0.0)
    _wall(P, -W2, -1800, yt)
    _wall(P, 1800, W2, yt)
    # the ends: two windows each, plain round them
    for sx in (-1, 1):
        xe = sx * (W2 - WALL / 2.0)
        _windows(P, 2, 600, xe, 0, 'rhl_arch_end', along='y')
        _wall(P, -D2, -300, xe, along='y')
        _wall(P, 300, D2, xe, along='y')
    # the floor (and the bay's), the beams, the desk and the keys behind it
    hs._box(P, [hs.RH_W - 2 * WALL, hs.RH_D - 2 * WALL, 8], [0, 0, 0], 'rhl_marble', material='stone', bottom=None)
    hs._box(P, [640 - 2 * WALL, TOWER_BAY + 10, 8], [0, -(D2 + TOWER_BAY / 2.0 - 5), 0], 'rhl_marble', material='stone', bottom=None)
    for k in range(-9, 10):
        hs._box(P, [34, hs.RH_D - 2 * WALL, 30], [k * 200, 0, LH - 30], 'rhl_koa', solid=False, top=None)
    hs._box(P, [hs.RH_W - 2 * WALL, 30, 30], [0, 0, LH - 60], 'rhl_koa', solid=False, top=None)
    desk_x, desk_y = -900, D2 - WALL - 170
    hs._box(P, [700, 90, 104], [desk_x, desk_y, 8], 'rhl_koa', material='wood')
    hs._box(P, [740, 120, 8], [desk_x, desk_y, 112], 'rhl_koa', material='wood')            # (its top, over the front)
    hs._box(P, [560, 14, 190], [desk_x, D2 - WALL - 7, 130], 'rhl_koa', solid=False, front='rhl_keys', back=None)
    hs._box(P, [1500, 520, 2], [400, -20, 8], 'rhl_rug', solid=False, bottom=None)
    hs._box(P, [900, 360, 2], [-900, -60, 8], 'rhl_rug', solid=False, bottom=None)


def rh_belvedere(P, T, ty, tz, H):
    """The tower's top as a lookout: a floor, a balustrade between the posts on all four sides, the stair head in the middle."""
    hs._box(P, [T - 40, T - 40, 10], [0, ty, tz], 'terrazzo', material='stone')
    e = T / 2.0 - hs.RH_BELVEDERE[3] / 2.0
    for side in range(4):
        if side < 2:
            y = ty + (e - 20 if side else -(e - 20))
            hs._box(P, [T - 80, 16, 100], [0, y, tz + 10], 'rhl_rail', material='stone', front='rhl_rail', back='rhl_rail', top='rh_plain', bottom=None)
        else:
            x = e - 20 if side == 3 else -(e - 20)
            hs._box(P, [16, T - 80, 100], [x, ty, tz + 10], 'rhl_rail', material='stone', left='rhl_rail', right='rhl_rail', top='rh_plain', bottom=None)
    hs._box(P, [170, 170, 250], [0, ty + 20, tz + 10], 'rh_plain', top='rh_tiles')


# ---------- what's in it, and its doors (the building's frame) ----------

D2 = hs.RH_D / 2.0
DESK = (-900, D2 - WALL - 170)
# (edid, x, y, z over the floor, face in degrees)
RH_THINGS = [
    # the chandeliers down the middle, lit
    ('TenPennyChandelier', -1500, 0, LH - 120, 0), ('TenpennyChandelierDark', -750, 0, LH - 120, 0), ('TenPennyChandelier', 0, -40, LH - 120, 0),
    ('DirtyChandelier', 750, 0, LH - 120, 0), ('TenPennyChandelier', 1500, 0, LH - 120, 0),
    ('NVTopsLargeAmb', 0, 0, LH - 160, 0), ('NVTopsWarmAmb', -1300, 0, LH - 160, 0), ('NVTopsWarmAmb', 1300, 0, LH - 160, 0),
    ('NVTopsWarmKey2', -900, 120, 260, 0), ('NVTopsWarmKey2', 400, -100, 260, 0), ('NVTopsWarmKey2', 1700, 0, 260, 0),
    # the front desk
    ('Telephone01', -1100, DESK[1] - 10, 120, 180), ('LootCashRegisterNV', -760, DESK[1] - 5, 120, 180), ('HotelLamp', -600, DESK[1], 120, 180),
    ('BookGeneric02b', -980, DESK[1], 120, 160),
    # sitting by the sea windows: sofas and chairs round low tables, lamps
    ('SubCouch01F', 250, -230, 8, 180), ('SubCouch01F', 650, -230, 8, 180), ('SubEndtableDirty01', 450, -260, 8, 0), ('HotelLamp', 450, -260, 60, 0),
    ('HotelChair01F', 300, 40, 8, 0), ('HotelChair01F', 600, 40, 8, 0), ('HotelChair01L', 1000, -120, 8, 270),
    ('HotelChair01F', -350, -250, 8, 180), ('HotelChair01R', -600, -100, 8, 90),
    # planters and palms along the walls
    ('NVTOPSRecPlanter03', -1850, -250, 8, 0), ('NVTOPSRecPlanter03', 1850, -250, 8, 0), ('NVTOPSRecPlanter03', -1850, 250, 8, 0),
    ('NVGoldfingerBanana', -1850, -250, 40, 0), ('NVGoldfingerBanana', 1850, -250, 40, 70), ('NVFalseSpireaPlant', -1850, 250, 40, 0),
    ('CementPlanterRd01', -300, 280, 8, 0), ('CementPlanterRd01', 300, 280, 8, 0), ('NVFalseSpireaPlant', -300, 280, 40, 0), ('NVFalseSpireaPlant', 300, 280, 40, 0),
    # luggage left where the guests left it
    ('SuitCase01Empty', -1300, 200, 8, 30), ('SuitCase02', -1340, 150, 8, 75), ('SuitCase01Empty', 1100, 250, 8, 300),
    # those who live here now: mattresses by the east end, a fire barrel, sandbags inside the door, trash
    ('BedMattress01FloorL', 1550, 200, 8, 90), ('BedMattress01FloorR', 1550, -150, 8, 90), ('FireBarrelSwitching', 1300, 30, 8, 0),
    ('SandbagStraight', -260, D2 - 170, 8, 0), ('SandbagStraight', 260, D2 - 170, 8, 0),
    ('DLC05TrashPile01', -1700, -50, 8, 40), ('DLC05TrashPile03', 1000, 300, 8, 200),
]
# (doors: name, edid, x, y, z, face; 'in' the way in from the town, 'lift' to the guest floors, 'lookout' up the tower)
RH_DOORS = [
    ('in', 'DoorStorefrontDbl01', 0, D2 - WALL / 2.0, 0, 180),
    ('lift', 'HotelElevatorDoor01', hs.RH_W / 2.0 - WALL - 10, 150, 0, 270),
    ('lift2', 'HotelElevatorDoor01', hs.RH_W / 2.0 - WALL - 10, -150, 0, 270),
]
BELVEDERE_Z = 8 * FLOOR + 10 - 8.0        # (the lookout's floor over the lobby's: z of things and doors is over the lobby floor)
RH_LOOKOUT = ('lookout', 'OffDoorHotelSmL01', 0, -(D2 - 200) + 20 - 86, BELVEDERE_Z, 180)
RH_LOOKOUT_THINGS = [
    ('SandbagStraight', 150, -(D2 - 200) - 220, BELVEDERE_Z, 0), ('SandbagStraight', -150, -(D2 - 200) - 220, BELVEDERE_Z, 0),
    ('BedMattress01FloorL', 200, -(D2 - 200) + 200, BELVEDERE_Z, 90), ('NVTopsWarmKey2', 0, -(D2 - 200), BELVEDERE_Z + 200, 0),
    ('HotelChair01F', -200, -(D2 - 200) - 120, BELVEDERE_Z, 180),
]



# ---------- the Moana: its lobby and the pavilion on its roof ----------

def _sash(P, n, W, x, y, h, glass_h, along='x', door_at=None, out='mo_plain'):
    """A row of n tall square-headed windows W long (the Moana's sashes): piers, a lintel over glass_h, glazed save a
    doorway at door_at."""
    bay = W / float(n)
    for k in range(n + 1):
        o = max(-W / 2.0 + PIER / 2.0, min(W / 2.0 - PIER / 2.0, -W / 2.0 + k * bay))
        if along == 'x':
            hs._box(P, [PIER, WALL, glass_h], [x + o, y, 0], out, **faces_inner(y, 'x'))
        else:
            hs._box(P, [WALL, PIER, glass_h], [x, y + o, 0], out, **faces_inner(x, 'y'))
    if along == 'x':
        hs._box(P, [W, WALL, h - glass_h], [x, y, glass_h], out, **faces_inner(y, 'x'))
    else:
        hs._box(P, [WALL, W, h - glass_h], [x, y, glass_h], out, **faces_inner(x, 'y'))
    spans = [(-W / 2.0, W / 2.0)]
    if door_at is not None:
        spans = [(-W / 2.0, door_at - bay / 2.0 + PIER / 2.0), (door_at + bay / 2.0 - PIER / 2.0, W / 2.0)]
    inward = 1 if (y if along == 'x' else x) < 0 else -1
    for a, b in spans:
        if b - a < 10:
            continue
        m = (a + b) / 2.0
        if along == 'x':
            hs._box(P, [b - a, 12, glass_h - 4], [x + m, y + inward * 2, 2], 'rhl_glass', material='glass',
                    front='rhl_glass', back='rhl_glass', left=None, right=None, top=None, bottom=None)
        else:
            hs._box(P, [12, b - a, glass_h - 4], [x + inward * 2, y + m, 2], 'rhl_glass', material='glass',
                    front=None, back=None, left='rhl_glass', right='rhl_glass', top=None, bottom=None)


def mo_lobby(P):
    """The Moana's lobby, two floors high under the middle block: tall sash windows to the veranda and the portico, a
    door under the portico, the wings' doors at the ends; a floor of koa boards, white columns down it, the desk."""
    W2, D2_ = hs.MO_W / 2.0, hs.MO_D / 2.0
    ys, yt = -(D2_ - WALL / 2.0), D2_ - WALL / 2.0
    _sash(P, 6, hs.MO_W, 0, ys, LH, 400, out='mo_plain')
    _sash(P, 7, hs.MO_W, 0, yt, LH, 400, door_at=0.0, out='mo_plain')
    for sx in (-1, 1):
        _wall(P, -D2_, D2_, sx * (W2 - WALL / 2.0), along='y', out='mo_plain')
    hs._box(P, [hs.MO_W - 2 * WALL, hs.MO_D - 2 * WALL, 8], [0, 0, 0], 'rhl_koa', material='wood', bottom=None)
    for k in range(4):
        for sy in (-1, 1):
            P.append({'shape': 'cylinder', 'r': 34, 'r2': 30, 'h': LH - 8, 'sides': 10, 'at': [-600 + 400 * k, sy * 190, 8], 'look': 'mo_column',
                      'caps': False, 'material': 'stone'})
    desk_y = D2_ - WALL - 160
    hs._box(P, [520, 90, 104], [-520, desk_y, 8], 'rhl_koa', material='wood')
    hs._box(P, [560, 120, 8], [-520, desk_y, 112], 'rhl_koa', material='wood')
    hs._box(P, [420, 14, 190], [-520, D2_ - WALL - 7, 130], 'rhl_koa', solid=False, front='rhl_keys', back=None)
    hs._box(P, [900, 380, 2], [250, -30, 8], 'rhl_rug', solid=False, bottom=None)


def mo_pavilion(P, z):
    """The pavilion on its roof as a lookout: sash windows all round, the stair head in the middle (made standing on
    z 0, then lifted to the roof)."""
    S = 700
    sub = []
    _sash(sub, 3, S, 0, -(S / 2.0 - WALL / 2.0), FLOOR, 200)
    _sash(sub, 3, S, 0, S / 2.0 - WALL / 2.0, FLOOR, 200)
    _sash(sub, 3, S - 2 * WALL, -(S / 2.0 - WALL / 2.0), 0, FLOOR, 200, along='y')
    _sash(sub, 3, S - 2 * WALL, S / 2.0 - WALL / 2.0, 0, FLOOR, 200, along='y')
    hs._box(sub, [170, 170, FLOOR], [0, 60, 0], 'mo_plain', top=None)
    hs._box(sub, [S - 20, S - 20, 10], [0, 0, FLOOR - 10], 'rhl_ceiling', solid=False, top=None)
    for q in sub:
        q['at'] = [q['at'][0], q['at'][1], q['at'][2] + z]
    P += sub


MD2 = hs.MO_D / 2.0
MO_DESK_Y = MD2 - WALL - 160
MO_TOP = hs.MO_FLOORS * FLOOR + 30 - FLOOR_TOP      # (the pavilion's floor over the lobby's)
MO_THINGS = [
    ('TenPennyChandelier', -450, 0, LH - 120, 0), ('TenpennyChandelierDark', 450, 0, LH - 120, 0),
    ('NVTopsLargeAmb', 0, 0, LH - 160, 0), ('NVTopsWarmKey2', -520, 200, 260, 0), ('NVTopsWarmKey2', 400, -150, 260, 0),
    ('Telephone01', -650, MO_DESK_Y - 10, 120, 180), ('HotelLamp', -380, MO_DESK_Y, 120, 180), ('LootCashRegisterNV', -500, MO_DESK_Y - 5, 120, 180),
    ('SubCouchDirty01F', 150, -300, 8, 180), ('SubCouch01F', 500, -300, 8, 180), ('SubEndtableDirty01', 330, -320, 8, 0),
    ('HotelChair01F', 200, 60, 8, 0), ('HotelChair01L', 650, -60, 8, 270), ('HotelChair01F', -250, -280, 8, 180),
    ('NVTOPSRecPlanter03', -800, -330, 8, 0), ('NVTOPSRecPlanter03', 800, -330, 8, 0), ('NVGoldfingerBanana', -800, -330, 40, 0), ('NVFalseSpireaPlant', 800, -330, 40, 0),
    ('SuitCase01Empty', -760, 250, 8, 20), ('SuitCase02', 700, 260, 8, 300),
    ('BedMattress01FloorL', 650, 200, 8, 0), ('FireBarrelSwitching', 0, 120, 8, 0), ('SandbagStraight', -230, MD2 - 160, 8, 0), ('SandbagStraight', 230, MD2 - 160, 8, 0),
    ('DLC05TrashPile02', -700, -50, 8, 120),
    # the pavilion
    ('SandbagStraight', 0, -270, MO_TOP, 0), ('BedMattress01FloorR', 220, -150, MO_TOP, 90), ('HotelChair01F', -200, -230, MO_TOP, 180),
    ('NVTopsWarmKey2', 0, 0, MO_TOP + 180, 0),
]
MO_DOORS = [
    ('in', 'DoorStorefrontDbl01', 0, MD2 - WALL / 2.0, 0, 180),
    ('lift', 'HotelElevatorDoor01', hs.MO_W / 2.0 - WALL - 10, 120, 0, 270),
    ('wing', 'OffDoorHotelSmL01', -(hs.MO_W / 2.0 - WALL - 10), 0, 0, 90),
    ('lookout', 'OffDoorHotelSmL01', 0, 60 - 86, MO_TOP, 180),
]


# ---------- the Kilauea: its casino and the observation deck under its crown ----------

KIL_FLOOR = 140.0                   # (the casino's floor: the plinth's top)
KIL_DECK = 5512.0 - KIL_FLOOR       # (the deck's floor over the casino's)


def _round_at(r, deg):
    """(x, y) at r out on a bearing in degrees (0 +x, anticlockwise), as towerset lays its rings."""
    return round(r * math.cos(math.radians(deg)), 1), round(r * math.sin(math.radians(deg)), 1)


def _face_out(deg):
    """The face (0 +y, 90 +x) of something looking out along a bearing."""
    return (90.0 - deg) % 360.0


KIL_THINGS = []
for _k, _deg in enumerate(range(0, 360, 30)):
    if _deg in (30, 150, 270):
        continue                                    # (the fins stand on those bearings)
    _x, _y = _round_at(2200, _deg)
    KIL_THINGS.append((('SlotMachine01BrokenA', 'SlotMachine02Static', 'SlotMachine03Broken', 'SlotMachine01StaticLucky38')[_k % 4], _x, _y, 0, (_face_out(_deg) + 180) % 360))
    _x, _y = _round_at(1500, _deg + 15)
    KIL_THINGS.append((('TopsBlackjackTableSTATIC', 'RouletteTable01NoSound', 'CrapsTable01')[_k % 3], _x, _y, 0, _face_out(_deg + 15)))
for _deg in (90, 210, 330):
    _x, _y = _round_at(1100, _deg)
    KIL_THINGS += [('TenPennyChandelier', _x, _y, 780, 0), ('NVTopsWarmAmb', _x, _y, 700, 0)]
    _x, _y = _round_at(2600, _deg)
    KIL_THINGS += [('NVTOPSRecPlanter03', _x, _y, 0, 0), ('NVGoldfingerBanana', _x, _y, 30, 0), ('NVTopsWarmKey2', _x, _y, 300, 0)]
KIL_THINGS += [('NVTopsLargeAmb', 0, -1200, 700, 0), ('NVTopsLargeAmb', 0, 1200, 700, 0),
               ('BarTaps01', 1350, -1700, 100, 210), ('DinerCounterMid01', 1350, -1700, 0, 210), ('Stool01', 1250, -1800, 0, 30),
               ('BedMattress01FloorL', -2000, 900, 0, 30), ('FireBarrelSwitching', -1700, 700, 0, 0), ('DLC05TrashPile04', 2000, 600, 0, 0),
               ('SandbagStraight', -700, -2450, 0, 165), ('SandbagStraight', -450, -2500, 0, 175)]
for _deg in range(0, 360, 45):                      # (the deck: chairs round the glass, low tables, lights)
    _x, _y = _round_at(1600, _deg)
    KIL_THINGS.append(('HotelChair01F', _x, _y, KIL_DECK, _face_out(_deg)))
    _x, _y = _round_at(1200, _deg + 22)
    KIL_THINGS.append(('SubEndtableDirty01', _x, _y, KIL_DECK, 0))
KIL_THINGS += [('NVTopsLargeAmb', 0, -1000, KIL_DECK + 380, 0), ('NVTopsLargeAmb', 0, 1000, KIL_DECK + 380, 0), ('TenPennyChandelier', 900, 0, KIL_DECK + 360, 0),
               ('TenPennyChandelier', -900, 0, KIL_DECK + 360, 0), ('BarTaps01', 0, 800, KIL_DECK + 100, 180), ('DinerCounterMid01', 0, 800, KIL_DECK, 180),
               ('SandbagStraight', 1500, -800, KIL_DECK, 120), ('BedMattress01FloorR', -800, -900, KIL_DECK, 40)]
_IN = _round_at(2860, 255)
_OUT = _round_at(2940, 255)
KIL_DOORS = [
    ('in', 'DoorStorefrontDbl01', _IN[0], _IN[1], 0, _face_out(255)),
    ('lift', 'HotelElevatorDoor01', 0, -436, 0, 180),
    ('lookout', 'HotelElevatorDoor01', 0, -436, KIL_DECK, 180),
]


# ---------- each hotel's small world: what goes in it ----------

# (closed: the piece Waikiki stands; open: the one the small world stands; things, doors: in its frame, z over the
# ground floor's top (FLOOR_TOP over the piece's foot) unless over `high`; out: the way in on the outside, (x, y, face);
# arrive_in / arrive_out: (x, y, z, face) inside and outside)
VIEWS = {
    'royal_hawaiian': {'closed': 'royal_hawaiian', 'open': 'royal_hawaiian_open', 'world': 'FOLabRoyalHawaiianWorld', 'name': 'The Royal Hawaiian',
                       'things': RH_THINGS + RH_LOOKOUT_THINGS, 'doors': RH_DOORS + [RH_LOOKOUT], 'door_out': 'DoorStorefrontDbl01',
                       'out': (0, D2 + 6, 0), 'arrive_in': (0, D2 - 220, 8, 180), 'arrive_out': (0, D2 + 260, 12, 0)},
    'moana': {'closed': 'moana', 'open': 'moana_open', 'world': 'FOLabMoanaWorld', 'name': 'The Moana',
              'things': MO_THINGS, 'doors': MO_DOORS, 'door_out': 'DoorStorefrontDbl01',
              'out': (0, MD2 + 6, 0), 'arrive_in': (0, MD2 - 220, 8, 180), 'arrive_out': (0, MD2 + 420, 50, 0)},
    'kilauea': {'closed': 'kilauea', 'open': 'kilauea_open', 'world': 'FOLabKilaueaWorld', 'name': 'The Kilauea', 'floor_top': KIL_FLOOR,
                'things': KIL_THINGS, 'doors': KIL_DOORS, 'door_out': 'DoorStorefrontDbl01',
                'out': (_OUT[0], _OUT[1], (_face_out(255) + 180) % 360),
                'arrive_in': (_round_at(2500, 255)[0], _round_at(2500, 255)[1], 8, (_face_out(255) + 180) % 360),
                'arrive_out': (_round_at(3300, 255)[0], _round_at(3300, 255)[1], 160, _face_out(255))},
}


def view_ops(gd, pr, hotel, parent, child, progress=print, linked=()):
    """Everything that goes into a hotel's small world (already added, viewworld.add_world), as ops for one Undo: the
    open hotel where the city stands the closed one, the city round it (viewworld.stage_ops), its things and lights, its
    doors (named '<hotel>_<door>'; the way in linked both ways with a door of the same on the outside; the others locked
    until something is behind them, save those named in `linked`). Returns (ops, report); the report's 'doors' {name:
    {'cell', 'arrive'}}: each door's cell and the spot just in front of it, for linking."""
    import landmarks
    import viewworld
    v = VIEWS[hotel]
    modelsets._all_sets()
    closed = modelsets.record_of(pr, v['closed'])
    city = {gd.key(c) for c in gd.grid(parent).values()}
    spot = [(ck, rk, r) for ck, c in pr.cells.items() if ck in city for rk, r in c['refs'].items() if r.get('base') == closed and not r.get('removed')]
    if len(spot) != 1:
        raise ValueError('%s stands %d times in the city; it should be once.' % (v['name'], len(spot)))
    wck, _wrk, wr = spot[0]
    x, y, z, _rx, _ry, rz = wr['p']
    sz = float(wr.get('s') or 1.0)            # (the Kilauea stands at 0.8: its rooms and where things go shrink with it, the things don't)
    cx, cy = int(x // 4096), int(y // 4096)
    stage = viewworld.stage_ops(gd, pr, parent, child, cx, cy, skip=lambda base, p: base == closed)
    progress('%s: %d of the city\'s things round it' % (v['name'], len(stage)))
    grid = gd.grid(child)
    cell_of = lambda wx, wy: gd.key(grid[(int(wx // 4096), int(wy // 4096))])
    ops, info = modelsets.put(pr, v['open'])
    key = info['key'] or '$model_' + v['open']
    ops.append({'op': 'add', 'cell': cell_of(x, y), 'base': key, 'p': list(wr['p']), 's': sz})
    ops += stage
    want = {t[0] for t in v['things']} | {d[1] for d in v['doors']} | {v['door_out']}
    keys = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if gd.edid(f) in want}
    missing = sorted(want - set(keys))
    fz = z + v.get('floor_top', FLOOR_TOP) * sz

    def at(lx, ly, lz, face, base=fz):
        wx, wy = landmarks._turn(lx * sz, ly * sz, rz)
        return [round(x + wx, 1), round(y + wy, 1), round(base + lz * sz, 1), 0.0, 0.0, round((rz + math.radians(face)) % math.tau, 4)]
    n = 0
    for edid, lx, ly, lz, face in v['things']:
        if edid in keys:
            p = at(lx, ly, lz, face)
            ops.append({'op': 'add', 'cell': cell_of(p[0], p[1]), 'base': keys[edid], 'p': p, 's': 1})
            n += 1
    names = {}
    for name, edid, lx, ly, lz, face in v['doors']:
        p = at(lx, ly, lz, face)
        o = {'op': 'add', 'cell': cell_of(p[0], p[1]), 'base': keys[edid], 'p': p, 's': 1, 'name': hotel + '_' + name}
        if name != 'in' and name not in linked:
            o['extra'] = {'props': {'lock': {'level': 255, 'key': '', 'leveled': False}}}
        else:
            o['extra'] = {'persistent': True}
        ops.append(o)
        f = math.radians(face)
        names[hotel + '_' + name] = {'cell': o['cell'], 'arrive': at(lx + 120 * math.sin(f) / sz, ly + 120 * math.cos(f) / sz, lz + 8, face)}
    ox, oy, oface = v['out']
    po = at(ox, oy, 0.0, oface)
    pgrid = gd.grid(parent)
    ock = gd.key(pgrid.get((int(po[0] // 4096), int(po[1] // 4096)), gd.from_key(wck)))     # (the door's own cell: a big hotel spans several)
    ops.append({'op': 'add', 'cell': ock, 'base': keys[v['door_out']], 'p': po, 's': 1, 'name': hotel + '_out'})
    ai, ao = at(*v['arrive_in']), at(*v['arrive_out'], base=z)
    ops.append({'op': 'tel', 'cell': ock, 'ref': '$%s_out' % hotel, 'tel': {'door': '$%s_in' % hotel, 'p': ai}})
    ops.append({'op': 'tel', 'cell': names[hotel + '_in']['cell'], 'ref': '$%s_in' % hotel, 'tel': {'door': '$%s_out' % hotel, 'p': ao}})
    return ops, {'hotel': hotel, 'at': [round(x), round(y), round(z)], 'turn': rz, 'city': len(stage), 'things': n, 'doors': names,
                 'missing': missing}
