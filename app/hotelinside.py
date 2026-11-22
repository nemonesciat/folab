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
import os
import random

import historicset as hs
import modelsets
import texpaint as tp
import texwear as tw
from modelsets import FLOOR, look
from texwear import Field, Picture, grade, mix, mul

LH = 2 * FLOOR                  # (the lobby's height: two of the hotel's floors)
DESK_TOP = 86                   # (a front desk's top over the piece's foot: 78 over the floor, a metre and a bit; it was 1.6 m)
DESK_ON = DESK_TOP - 8          # (the same over the floor, for what stands on it)
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
    """Old window glass: grimy, streaked, a little green, seen through. Its alpha is how much it hides, blended (the shape's
    look is alpha 'blend'): mostly clear, 0.1 to 0.2, grime and the run of rain streaks to about 0.4, never near-opaque
    (it was 0.2 to 0.85 under a cut-out at 64, so most of each pane drew solid in game, 22 Nov 2026)."""
    dirt = Field(size, size, seed, 4, 5)
    streak = Field(size, size, seed + 1, 2, 3, stretch=(4, 0.25))
    pic = Picture(size, size, clear=(150, 170, 160), gloss=120)
    for p in range(size * size):
        d, s = dirt.v[p], streak.v[p]
        pic.rgb[p] = grade(mix((150, 170, 160), (120, 108, 86), d))
        pic.a[p] = min(0.4, 0.1 + 0.22 * d * d * d + 0.1 * s * s)
    pic.plain_halving = True        # (blended, not a cut-out: its smaller copies plain means, texpaint.colour_map)
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


def runner(w=256, h=1024, seed=1355):
    """The court's runner from the door to the middle of the hall: red, a gold border, a gold diamond down it every so often,
    trodden pale down the middle."""
    worn = Field(w, h, seed, 3, 5)
    pic = Picture(w, h, gloss=6)
    for y in range(h):
        for x in range(w):
            p = y * w + x
            edge = min(x, w - 1 - x) / w
            c = (128, 22, 30) if edge > 0.14 else ((206, 168, 84) if edge > 0.09 else (128, 22, 30))
            dy, dx = (y % 128) - 64, x - w // 2
            if edge > 0.14 and 20 < abs(dx) + abs(dy) < 28:
                c = (206, 168, 84)                  # (the diamonds)
            mid = max(0.0, 1.0 - abs(dx) / (w * 0.3))
            c = mix(c, (160, 120, 110), mid * 0.4 * worn.v[p])
            pic.rgb[p] = grade(c)
    return pic


modelsets.TEXTURES.update({
    'hist/rhl_runner': runner,
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
        'rhl_glass': dict(look('hist/rhl_glass', tile=400), alpha='blend'),        # (blended as the game's window glass: nifmake.ALPHA_BLEND)
        'rhl_keys': look('hist/rhl_keys'),
        'rhl_rug': look('hist/rhl_rug'),
        'rhl_runner': look('hist/rhl_runner'),
        'rhl_inside': look('hist/rhl_inside', tile=512),
        'rhl_arch_sea': dict(look('hist/rhl_arch_sea'), alpha=True),
        'rhl_arch_bay': dict(look('hist/rhl_arch_bay'), alpha=True),
        'rhl_arch_town': dict(look('hist/rhl_arch_town'), alpha=True),
        'rhl_arch_end': dict(look('hist/rhl_arch_end'), alpha=True),
        'rhl_rail': dict(look('hist/rhl_rail', tile=96), alpha=True),
        'lobby_lamp': _lamp_look(),
    }


def _lamp_look():
    import waikikiset as wk
    return wk.lit('waikiki/lamp_glass', LIT_LAMP)


# ---------- the lobby as the town sees it (the closed pieces Waikiki stands) ----------
# The engine draws nothing of an interior from outside, so the closed hotel shows its lobby as a stage set: the open
# piece's own windows, glass and room (marble, beams, desk, columns) built in front of what stops you, nothing of it
# solid, its walls, ceiling and lamps glowing (a glow map, as the game's lamps: lit by day and by night). What stops you
# is the closed piece's own collision, unchanged: its boxes keep their size and place, their sides drawn by nothing
# (`HIDE`), so no navmesh round them changes. From afar the ground floor is a lit band (`far_front`), drawn on a skin
# that only the far model shows (alpha cuts it all away near; the far model keeps its far picture, `far_keep`).

LIT_WALLS, LIT_FLOOR, LIT_LAMP = 0.75, 0.45, 3.0        # (how bright what glows is: the room, its floor, its lamps)
LAMP_R = 34


def clear(size=8):
    """A picture of nothing: every pixel cut away."""
    return Picture(size, size, clear=(0, 0, 0))


def far_front(wall, inside=(250, 196, 120), bays=9, arched=True, w=256, h=64, seed=1380):
    """A lobby's ground floor from across the bay: bays of warm light between piers of the hotel's wall, brighter up
    under the lamps, arched heads or square."""
    pic = Picture(w, h, gloss=16)
    f = Field(w, h, seed, cells=3, octaves=3)
    bw = w / float(bays)
    for y in range(h):
        v = y / float(h)
        for x in range(w):
            p = y * w + x
            u = (x % bw) / bw
            open_ = 0.16 < u < 0.84 and v > 0.12
            if open_ and arched and v < 0.42:            # (the arch's head: a half circle over the opening)
                du, dv = (u - 0.5) / 0.34, (0.42 - v) / 0.3
                open_ = du * du + dv * dv < 1.0
            if open_:
                col = mul(inside, (1.05 - 0.45 * v) * (0.9 + 0.2 * f.v[p]))
            else:
                col = mul(wall, 0.82 + 0.25 * f.v[p])
            pic.rgb[p] = grade(col)
    return pic


def slot_row(size=256, seed=1390):
    """A slot machine seen across the casino (one to a picture, the ring repeats it): its cabinet, a lit screen and
    reels, the coin tray; see-through round it."""
    pic = Picture(size, size, clear=(40, 30, 24), gloss=60)
    f = Field(size, size, seed, cells=4, octaves=3)
    for y in range(size):
        v = y / float(size)
        for x in range(size):
            u = x / float(size)
            p = y * size + x
            if not (0.22 < u < 0.78 and 0.06 < v):
                continue
            col, a = mul((150, 34, 30), 0.8 + 0.3 * f.v[p]), 1.0          # (red lacquer, worn)
            if 0.3 < u < 0.7 and 0.1 < v < 0.34:
                col = (250, 214, 120)                                      # (the lit top glass)
            elif 0.3 < u < 0.7 and 0.4 < v < 0.58:
                k = int((u - 0.3) / 0.4 * 3)
                col = (238, 232, 210) if (u - 0.3) / 0.4 * 3 - k > 0.08 else (40, 30, 24)      # (three reels)
            elif 0.66 < v < 0.7 or (0.26 < u < 0.74 and 0.84 < v < 0.9):
                col = (196, 160, 82)                                       # (gold trim, the tray)
            pic.rgb[p], pic.a[p] = grade(col, sat=0.85), a
    return pic


modelsets.TEXTURES.update({
    'hist/clear': clear,
    'hist/rhl_far_front': lambda: far_front(hs.PINK, bays=9, arched=True, seed=1380),
    'hist/rhl_far_end': lambda: far_front(hs.PINK, bays=2, arched=True, w=64, seed=1381),
    'hist/mol_far_front': lambda: far_front(hs.MOANA_WHITE, bays=7, arched=False, seed=1382),
    'hist/mol_far_end': lambda: far_front(hs.MOANA_WHITE, bays=2, arched=False, w=64, seed=1383),
    'resort/kil_far_casino': lambda: far_front((176, 140, 72), inside=(250, 186, 104), bays=24, arched=False, w=256, h=32, seed=1384),
    'resort/kil_slots': slot_row,
})


def hide(far):
    """A look nothing near draws (all cut away) whose far model shows `far`."""
    return dict(look('hist/clear'), alpha=True, far=far, far_keep=True)


def shown_looks():
    """The closed pieces' looks for their lobby: the open piece's, the room's own lit, and the skins."""
    import waikikiset as wk
    out = looks()
    out.update({
        'rhl_inside_lit': dict(out['rhl_inside'], glow=wk.GLOW, glow_mult=LIT_WALLS),
        'rhl_ceiling_lit': dict(out['rhl_ceiling'], glow=wk.GLOW, glow_mult=LIT_WALLS),
        'rhl_marble_lit': dict(out['rhl_marble'], glow=wk.GLOW, glow_mult=LIT_FLOOR),
        'rhl_koa_lit': dict(out['rhl_koa'], glow=wk.GLOW, glow_mult=LIT_FLOOR),
        'rh_hide_front': hide('hist/rhl_far_front'), 'rh_hide_end': hide('hist/rhl_far_end'),
        'mo_hide_front': hide('hist/mol_far_front'), 'mo_hide_end': hide('hist/mol_far_end'),
        'kil_hide': hide('resort/kil_far_casino'),
        'kil_slots': dict(look('resort/kil_slots', tile=190), alpha=True, glow=wk.GLOW, glow_mult=LIT_FLOOR),
    })
    return out


LIT = {'rhl_inside': 'rhl_inside_lit', 'rhl_ceiling': 'rhl_ceiling_lit', 'rhl_marble': 'rhl_marble_lit', 'rhl_koa': 'rhl_koa_lit',
       'kil_ceiling': 'rhl_ceiling_lit'}
NO_FACES = {f: None for f in ('front', 'back', 'left', 'right', 'bottom')}


def shown(P, build, *args):
    """What build(parts, *args) makes, only to be seen: nothing of it solid, the room's own looks lit."""
    sub = []
    build(sub, *args)
    for q in sub:
        q['solid'] = False
        q['far'] = False
        for k in ('look', 'cap_look', 'under_look'):
            if q.get(k) in LIT:
                q[k] = LIT[q[k]]
        if q.get('faces'):
            q['faces'] = {f: LIT.get(v, v) for f, v in q['faces'].items()}
    P += sub
    return sub


def lamps(P, spots, z):
    """Lamps hung under the ceiling at z: a glowing globe on a rod."""
    for x, y in spots:
        P.append({'shape': 'ball', 'r': LAMP_R, 'sides': 10, 'rings': 6, 'at': [x, y, z - 2 * LAMP_R - 40], 'look': 'lobby_lamp', 'solid': False})
        P.append({'shape': 'cylinder', 'r': 3, 'h': 40, 'sides': 4, 'at': [x, y, z - 40], 'look': 'grey', 'solid': False})


def skin(P, size, at, front, end):
    """The far model's ground floor: a box only the far model draws (its sides `front` along x, `end` along y). Never in
    the model itself: there its faces lay on the lobby's own walls and flickered (17 Nov 2026)."""
    P.append({'shape': 'box', 'size': list(size), 'at': list(at), 'look': front, 'material': 'stone', 'solid': False, 'far_only': True,
              'faces': {'front': front, 'back': front, 'left': end, 'right': end, 'top': None, 'bottom': None}})


LIFT_W, LIFT_H = 216.0, 174.0          # (HotelElevatorDoor01 stood on the floor: door_rise)
BANK = 110                              # (how far the Royal Hawaiian's lift bank stands out of its east end wall)


def lift_frame(P, x, y, z, face, frame='rhl_koa', k=1.0, back=0.0):
    """A lift's surround in a lobby's own model, round where its door stands (x, y on the wall's face, z the floor; face
    as the doors', 0 +y): jambs and a head standing out of the wall, a lamp over it saying here is the way up. The
    game's lift door is two thin leaves and needs a wall and a frame round it; k: the frame in a piece stood smaller
    (the Kilauea at 0.8) still fits the door, which isn't."""
    f = math.radians(face)
    ux, uy, nx, ny = math.cos(f), -math.sin(f), math.sin(f), math.cos(f)
    turn = -face

    def put(a, b, size, zz, look_name, shape='box'):
        P.append({'shape': 'box', 'size': [size[0], size[1], size[2]], 'at': [x + ux * a + nx * b, y + uy * a + ny * b, zz],
                  'turn': [0, 0, turn], 'look': look_name, 'material': 'wood', 'solid': False})
    w, h = LIFT_W * k / 2.0, LIFT_H * k
    for side in (-1, 1):
        put(side * (w + 18 * k), 10 * k, (36 * k, 20 * k, h + 16 * k), z, frame)
    put(0, 10 * k, (2 * w + 72 * k, 20 * k, 46 * k), z + h + 16 * k, frame)
    if back:                                # (a wall behind it where what it stands on isn't flat: the Kilauea's round core)
        put(0, -back / 2.0, (2 * w + 72 * k, back, h + 62 * k), z, frame)
    P.append({'shape': 'ball', 'r': 12 * k, 'sides': 8, 'rings': 5, 'at': [x + nx * 16 * k, y + ny * 16 * k, z + h + 30 * k],
              'look': 'lobby_lamp', 'solid': False})


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
    hs._box(P, [700, 90, DESK_TOP - 8], [desk_x, desk_y, 8], 'rhl_koa', material='wood')
    hs._box(P, [740, 120, 8], [desk_x, desk_y, DESK_TOP], 'rhl_koa', material='wood')            # (its top, over the front)
    hs._box(P, [560, 14, 190], [desk_x, D2 - WALL - 7, 130], 'rhl_koa', solid=False, front='rhl_keys', back=None)
    hs._box(P, [1500, 520, 2], [400, -20, 8], 'rhl_rug', solid=False, bottom=None)
    hs._box(P, [900, 360, 2], [-900, -60, 8], 'rhl_rug', solid=False, bottom=None)
    # (the court's runner, from the door straight in, over the rugs)
    hs._box(P, [180, hs.RH_D - 2 * WALL - 40, 2], [0, 0, 10], 'rhl_runner', solid=False, bottom=None)
    # the lift bank against the east end (it stands in front of the end's two windows: the lifts had stood in them)
    hs._box(P, [BANK, 660, LH], [W2 - WALL - BANK / 2.0, 0, 0], 'rhl_inside', top=None, bottom=None)
    for ly in (150, -150):
        lift_frame(P, W2 - WALL - BANK, ly, FLOOR_TOP, 270)


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
    # the front desk (stood on its top)
    ('Telephone01', -1100, DESK[1] - 10, DESK_ON, 180), ('LootCashRegisterNV', -760, DESK[1] - 5, DESK_ON, 180), ('HotelLamp', -600, DESK[1], DESK_ON, 180),
    ('BookGeneric02b', -980, DESK[1], DESK_ON, 160),
    # the court's way in: torches either side of the runner from the door
    ('OasisTorch01', -170, 240, 0, 0), ('OasisTorch01', 170, 240, 0, 0), ('OasisTorch01', -170, -60, 0, 0), ('OasisTorch01', 170, -60, 0, 0),
    # sitting by the sea windows: sofas and chairs round low tables, lamps
    ('SubCouch01F', 250, -230, 0, 180), ('SubCouch01F', 650, -230, 0, 180), ('SubEndtableDirty01', 450, -260, 0, 0), ('HotelLamp', 450, -260, 37.6, 0),
    ('HotelChair01F', 300, 40, 0, 0), ('HotelChair01F', 600, 40, 0, 0), ('HotelChair01L', 1000, -120, 0, 270),
    ('HotelChair01F', -350, -250, 0, 180), ('HotelChair01R', -600, -100, 0, 90),
    # planters and palms along the walls (a plant stands in its planter's earth)
    ('NVTOPSRecPlanter03', -1850, -250, 0, 0), ('NVTOPSRecPlanter03', 1600, -280, 0, 0), ('NVTOPSRecPlanter03', -1850, 250, 0, 0),
    ('NVGoldfingerBanana', -1850, -250, 32, 0), ('NVGoldfingerBanana', 1600, -280, 32, 70), ('NVFalseSpireaPlant', -1850, 250, 32, 0),
    ('NVSagoPalm01', -330, 280, 0, 0), ('NVSagoPalm02', 330, 280, 0, 40),
    # the tribute brought in, stacked by the lift bank till it's counted
    ('CrateGenericNV', 1500, 270, 0, 10), ('NVWaterCrateSqr01', 1620, 280, 0, 85), ('Barrel03static', 1560, 180, 0, 0), ('Barrel03static', 1460, 170, 0, 0),
    # the court's guards inside the door
    ('SandbagStraight', -260, D2 - 170, 0, 0), ('SandbagStraight', 260, D2 - 170, 0, 0),
]
# (doors: name, edid, x, y, z, face; 'in' the way in from the town, 'lift' to the guest floors, 'lookout' up the tower)
RH_DOORS = [
    ('in', 'DoorStorefrontDbl01', 0, D2 - WALL / 2.0, 0, 180),
    ('lift', 'HotelElevatorDoor01', hs.RH_W / 2.0 - WALL - BANK, 150, 0, 270),      # (on the lift bank's face, in their frames)
    ('lift2', 'HotelElevatorDoor01', hs.RH_W / 2.0 - WALL - BANK, -150, 0, 270),
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
    hs._box(P, [520, 90, DESK_TOP - 8], [-520, desk_y, 8], 'rhl_koa', material='wood')
    hs._box(P, [560, 120, 8], [-520, desk_y, DESK_TOP], 'rhl_koa', material='wood')
    hs._box(P, [420, 14, 190], [-520, D2_ - WALL - 7, 130], 'rhl_koa', solid=False, front='rhl_keys', back=None)
    hs._box(P, [900, 380, 2], [250, -30, 8], 'rhl_rug', solid=False, bottom=None)
    lift_frame(P, W2 - WALL, MO_LIFT_Y, FLOOR_TOP, 270)


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
MO_LIFT_Y = 120
MO_DESK_Y = MD2 - WALL - 160
MO_TOP = hs.MO_FLOORS * FLOOR + 30 - FLOOR_TOP      # (the pavilion's floor over the lobby's)
MO_THINGS = [
    # ceiling fans down the middle, the old colonial hotel's, and one chandelier over the desk
    ('NVceilingFan', -650, 0, LH - 2, 0), ('NVceilingFan', -200, 0, LH - 2, 45), ('NVceilingFan', 250, 0, LH - 2, 20), ('NVceilingFan', 700, 0, LH - 2, 70),
    ('TenpennyChandelierDark', -520, 260, LH - 120, 0),
    ('NVTopsLargeAmb', 0, 0, LH - 160, 0), ('NVTopsWarmKey2', -520, 200, 260, 0), ('NVTopsWarmKey2', 400, -150, 260, 0),
    ('Telephone01', -650, MO_DESK_Y - 10, DESK_ON, 180), ('HotelLamp', -380, MO_DESK_Y, DESK_ON, 180), ('LootCashRegisterNV', -500, MO_DESK_Y - 5, DESK_ON, 180),
    ('SubCouchDirty01F', 150, -300, 0, 180), ('SubCouch01F', 500, -300, 0, 180), ('SubEndtableDirty01', 330, -320, 0, 0), ('TenpennyVase01', 330, -320, 37.6, 0),
    ('HotelChair01F', 200, 60, 0, 0), ('HotelChair01L', 650, -60, 0, 270), ('HotelChair01F', -250, -280, 0, 180),
    # benches along the back wall under the windows, as on a veranda; palms by the door from the portico
    ('BenchMuseumStatic01', -600, -(MD2 - WALL - 40), 0, 0), ('BenchMuseumStatic01', -150, -(MD2 - WALL - 40), 0, 0),
    ('NVSagoPalm01', -420, MD2 - 150, 0, 0), ('NVSagoPalm02', 420, MD2 - 150, 0, 60),
    ('NVTOPSRecPlanter03', -800, -330, 0, 0), ('NVTOPSRecPlanter03', 800, -330, 0, 0), ('NVGoldfingerBanana', -800, -330, 32, 0), ('NVFalseSpireaPlant', 800, -330, 32, 0),
    ('SuitCase01Empty', -760, 250, 0, 20), ('SuitCase02', 700, 260, 0, 300),
    ('BedMattress01FloorL', 650, 200, 0, 0), ('FireBarrelSwitching', 0, 120, 0, 0), ('SandbagStraight', -230, MD2 - 160, 0, 0), ('SandbagStraight', 230, MD2 - 160, 0, 0),
    ('DLC05TrashPile02', -700, -50, 0, 120),
    # the pavilion
    ('SandbagStraight', 0, -270, MO_TOP, 0), ('BedMattress01FloorR', 220, -150, MO_TOP, 90), ('HotelChair01F', -200, -230, MO_TOP, 180),
    ('NVTopsWarmKey2', 0, 0, MO_TOP + 180, 0),
]
MO_DOORS = [
    ('in', 'DoorStorefrontDbl01', 0, MD2 - WALL / 2.0, 0, 180),
    ('lift', 'HotelElevatorDoor01', hs.MO_W / 2.0 - WALL, MO_LIFT_Y, 0, 270),      # (on the east wall's face, in its frame)
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
KIL_K = 1 / 0.8                     # (the Kilauea stands at 0.8 and where things go shrinks with it: a counter's top, 73.4, is this much more in its frame)
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
               ('BarTaps01', 1350, -1700, 73.4 * KIL_K, 210), ('DinerCounterMid01', 1350, -1700, 0, 210), ('Stool01', 1250, -1800, 0, 30),
               ('BedMattress01FloorL', -2000, 900, 0, 30), ('FireBarrelSwitching', -1700, 700, 0, 0), ('DLC05TrashPile04', 2000, 600, 0, 0),
               ('SandbagStraight', -700, -2450, 0, 165), ('SandbagStraight', -450, -2500, 0, 175)]
# (the casino's rug in the middle, under the chandeliers: the Tops' own, nine pieces)
KIL_THINGS += [('NVTOPSCasinoRug', _x * 236, _y * 210, 0.5, 0) for _x in (-1, 0, 1) for _y in (-1, 0, 1)]
for _deg in range(0, 360, 45):                      # (the deck: chairs round the glass, low tables, lights)
    _x, _y = _round_at(1600, _deg)
    KIL_THINGS.append(('HotelChair01F', _x, _y, KIL_DECK, _face_out(_deg)))
    _x, _y = _round_at(1200, _deg + 22)
    KIL_THINGS.append(('SubEndtableDirty01', _x, _y, KIL_DECK, 0))
KIL_THINGS += [('NVTopsLargeAmb', 0, -1000, KIL_DECK + 380, 0), ('NVTopsLargeAmb', 0, 1000, KIL_DECK + 380, 0), ('TenPennyChandelier', 900, 0, KIL_DECK + 360, 0),
               ('TenPennyChandelier', -900, 0, KIL_DECK + 360, 0), ('BarTaps01', 0, 800, KIL_DECK + 73.4 * KIL_K, 180), ('DinerCounterMid01', 0, 800, KIL_DECK, 180),
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


def door_rise(gd, key):
    """How far a door must stand over the floor so its leaf stands on it: some of the game's doors are made round their
    middle (HotelElevatorDoor01 from 80 under its origin to 94 over: the game stands it 80 up in its kit's frame).
    Stood on its origin, half of it was under the lobby's floor and what showed was a stub the height of a child."""
    import library
    b = library.bounds_of(gd.read_file('meshes' + chr(92) + gd.describe(gd.from_key(key))[3]))
    return max(0.0, -b[2])


def leaf_turn(gd, key):
    """Degrees to add to a door's face (0 its front to +y) so its leaf lies along the wall: some of the game's doors are
    made with their leaf across y and their face to x (DoorStorefrontDbl01, OffDoorHotelSmL01: their meshes are thin in
    x), others across x. Turned by its face alone, a door of the first kind stood on its edge, square to the wall."""
    import library
    b = library.bounds_of(gd.read_file('meshes' + chr(92) + gd.describe(gd.from_key(key))[3]))
    return -90.0 if (b[3] - b[0]) < (b[4] - b[1]) else 0.0


_seats = {}


def seat(gd, key):
    """How far over what it stands on a thing's origin goes, so its model stands on it as the game stands it: chairs and
    sofas are made round their middle (the game stands HotelChair01F 36 over the floor). Hung things (lights, chandeliers,
    ceiling fans) hang where they're put: 0."""
    if key not in _seats:
        import library
        f = gd.from_key(key)
        edid = (gd.edid(f) or '').lower()
        if gd.forms[f][1].tag == 'LIGH' or any(w in edid for w in ('chandelier', 'ceilingfan')):
            _seats[key] = 0.0
        else:
            try:
                b = library.bounds_of(gd.read_file('meshes' + chr(92) + gd.describe(f)[3]))
                _seats[key] = round(-b[2], 2)
            except (KeyError, ValueError, OSError, TypeError):
                _seats[key] = 0.0
    return _seats[key]


def _frame(gd, pr, hotel, parent):
    """Where the hotel stands in the city (its closed piece, once): (its cell, its ref, at), at(lx, ly, lz, face, rise=0)
    the world's [x y z rx ry rz] of a spot in the building's frame (z over its ground floor's top; rise unscaled, a door's
    own: door_rise)."""
    import landmarks
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
    fz = z + v.get('floor_top', FLOOR_TOP) * sz

    def at(lx, ly, lz, face, rise=0.0):
        wx, wy = landmarks._turn(lx * sz, ly * sz, rz)
        return [round(x + wx, 1), round(y + wy, 1), round(fz + lz * sz + rise, 1), 0.0, 0.0, round((rz + math.radians(face)) % math.tau, 4)]
    return wck, wr, at


def arrive_at(at, lx, ly, lz, face, sz):
    """Where you arrive by a door: a step in front of it, on the floor it stands on."""
    f = math.radians(face)
    return at(lx + 120 * math.sin(f) / sz, ly + 120 * math.cos(f) / sz, lz + 8, face)


def relay_ops(gd, pr, hotel, parent, child, reach=400.0):
    """Ops moving a hotel's things and doors already in its small world to where view_ops puts them now (a lobby laid
    out again: the lifts raised and framed, 17 Nov 2026). Each is found as the nearest ref of the same base in the small
    world within `reach`; one already where it should be is left. Returns (ops, [what moved])."""
    v = VIEWS[hotel]
    _wck, wr, at = _frame(gd, pr, hotel, parent)
    sz = float(wr.get('s') or 1.0)
    cells = {gd.key(c) for c in gd.grid(child).values()}
    refs = [(ck, rk, r) for ck, c in pr.cells.items() if ck in cells for rk, r in c['refs'].items()
            if r.get('base') and r.get('p') and not r.get('removed')]
    want = {t[0] for t in v['things']} | {d[1] for d in v['doors']}
    keys = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if gd.edid(f) in want}
    items = [(e, at(lx, ly, lz, face, seat(gd, keys[e]))) for e, lx, ly, lz, face in v['things'] if e in keys]
    arrive = {}
    for _n, e, lx, ly, lz, face in v['doors']:
        if e in keys:
            p = at(lx, ly, lz, face + leaf_turn(gd, keys[e]), door_rise(gd, keys[e]))
            items.append((e, p))
            arrive[id(p)] = at(*v['arrive_in']) if _n == 'in' else arrive_at(at, lx, ly, lz, face, sz)     # (the way in: where VIEWS says)
    ops, moved, used = [], [], set()
    for e, p in items:
        near = [(math.hypot(r['p'][0] - p[0], r['p'][1] - p[1]) + abs(r['p'][2] - p[2]) * 0.01, ck, rk, r) for ck, rk, r in refs
                if r['base'] == keys[e] and rk not in used]
        near = [n for n in near if n[0] < reach]
        if not near:
            continue
        d, ck, rk, r = min(near)
        used.add(rk)
        if id(p) in arrive:                 # (and whatever leads to the door brings you a step in front of it, where it is now)
            ar = arrive[id(p)]
            for ock, c in pr.cells.items():
                for ork, orr in c['refs'].items():
                    t = orr.get('tel')
                    if t and t.get('door') == rk and max(abs(a - b) for a, b in zip(t.get('p') or [0] * 6, ar)) > 0.5:
                        ops.append({'op': 'tel', 'cell': ock, 'ref': ork, 'tel': dict(t, p=ar)})
                        moved.append(('arrival by ' + e, ork, [round(v_) for v_ in (t.get('p') or [])[:3]], [round(v_) for v_ in ar[:3]]))
        if max(abs(a - b) for a, b in zip(r['p'][:3], p[:3])) < 0.5 and abs(r['p'][5] - p[5]) < 1e-3:
            continue
        ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': p})
        moved.append((e, rk, [round(v_) for v_ in r['p'][:3]], [round(v_) for v_ in p[:3]]))
    return ops, moved


def restyle_ops(gd, pr, hotel, parent, child, old_things, near=60.0):
    """A lobby made over where it stands in the mod: its own model written again (modelsets.put: the desks lowered, the
    court's runner), and its things brought in line with VIEWS: each thing view_ops put there (found as the ref of the same
    base nearest where old_things, the lists it was put by, stood it, within `near`) moved to where VIEWS stands it now,
    seated; what's no longer listed taken out; what's new added. The city's own copies round it and the doors are left.
    Returns (ops, report)."""
    v = VIEWS[hotel]
    _wck, wr, at = _frame(gd, pr, hotel, parent)          # (first: it brings in every set, the signs' glow pictures among them)
    # (the model written again, and any picture the mod lacks; the pictures it has are left as they are: a newer FOLab may
    # have written them better than this one would)
    import library
    made = modelsets.build(v['open'])
    root = library.assets_dir(pr)
    written = []
    for rel, data in made['files'].items():
        full = os.path.join(root, rel)
        if rel == made['mesh'] or not os.path.isfile(full):
            if not os.path.isfile(full) or open(full, 'rb').read() != data:
                library._put(root, rel, data)
                written.append(rel)
    info = {'mesh': made['mesh'], 'written': written}
    grid = gd.grid(child)
    cells = {gd.key(c) for c in grid.values()}
    cell_of = lambda wx, wy: gd.key(grid[(int(wx // 4096), int(wy // 4096))])
    want = {t[0] for t in v['things']} | {t[0] for t in old_things}
    keys = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if gd.edid(f) in want and f >> 24 == 0}
    refs = [(ck, rk, r) for ck, c in pr.cells.items() if ck in cells for rk, r in c['refs'].items()
            if r.get('base') and r.get('p') and not r.get('removed') and rk.startswith('+')]
    # (what's ours: where the old lists stood each thing, with or without the seat it lacked)
    ours, used = [], set()
    for e, lx, ly, lz, face in old_things:
        if e not in keys:
            continue
        p = at(lx, ly, lz, face)
        best = None
        for ck, rk, r in refs:
            if r['base'] != keys[e] or rk in used:
                continue
            d = math.hypot(r['p'][0] - p[0], r['p'][1] - p[1])
            if d < near and abs(r['p'][2] - p[2]) < 80 and (best is None or d < best[0]):
                best = (d, ck, rk, r)
        if best:
            used.add(best[2])
            ours.append((e, best[1], best[2], best[3]))
    new = [(e, at(lx, ly, lz, face, seat(gd, keys[e]))) for e, lx, ly, lz, face in v['things'] if e in keys]
    ops, moved, added, gone = [], 0, 0, 0
    left = list(ours)
    for e, p in new:
        match = [o for o in left if o[0] == e]
        if match:
            o = min(match, key=lambda o: math.hypot(o[3]['p'][0] - p[0], o[3]['p'][1] - p[1]) + abs(o[3]['p'][2] - p[2]))
            left.remove(o)
            if max(abs(a - b) for a, b in zip(o[3]['p'][:3], p[:3])) > 0.5 or abs(o[3]['p'][5] - p[5]) > 1e-3:
                ops.append({'op': 'move', 'cell': o[1], 'ref': o[2], 'p': p})
                moved += 1
        else:
            ops.append({'op': 'add', 'cell': cell_of(p[0], p[1]), 'base': keys[e], 'p': p, 's': 1})
            added += 1
    for e, ck, rk, _r in left:
        ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
        gone += 1
    return ops, {'hotel': hotel, 'model': info.get('mesh'), 'written': info['written'], 'found': len(ours), 'of': sum(1 for t in old_things if t[0] in keys),
                 'moved': moved, 'added': added, 'removed': gone, 'missing': sorted({t[0] for t in v['things']} - set(keys))}


def view_ops(gd, pr, hotel, parent, child, progress=print, linked=()):
    """Everything that goes into a hotel's small world (already added, viewworld.add_world), as ops for one Undo: the
    open hotel where the city stands the closed one, the city round it (viewworld.stage_ops), its things and lights, its
    doors (named '<hotel>_<door>'; the way in linked both ways with a door of the same on the outside; the others locked
    until something is behind them, save those named in `linked`). Returns (ops, report); the report's 'doors' {name:
    {'cell', 'arrive'}}: each door's cell and the spot just in front of it, for linking."""
    import viewworld
    v = VIEWS[hotel]
    wck, wr, at = _frame(gd, pr, hotel, parent)
    x, y, z, _rx, _ry, rz = wr['p']
    sz = float(wr.get('s') or 1.0)
    closed = modelsets.record_of(pr, v['closed'])
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
    n = 0
    for edid, lx, ly, lz, face in v['things']:
        if edid in keys:
            p = at(lx, ly, lz, face, seat(gd, keys[edid]))
            ops.append({'op': 'add', 'cell': cell_of(p[0], p[1]), 'base': keys[edid], 'p': p, 's': 1})
            n += 1
    names = {}
    for name, edid, lx, ly, lz, face in v['doors']:
        p = at(lx, ly, lz, face + leaf_turn(gd, keys[edid]), door_rise(gd, keys[edid]))
        o = {'op': 'add', 'cell': cell_of(p[0], p[1]), 'base': keys[edid], 'p': p, 's': 1, 'name': hotel + '_' + name}
        if name != 'in' and name not in linked:
            o['extra'] = {'props': {'lock': {'level': 255, 'key': '', 'leveled': False}}}
        else:
            o['extra'] = {'persistent': True}
        ops.append(o)
        names[hotel + '_' + name] = {'cell': o['cell'], 'arrive': arrive_at(at, lx, ly, lz, face, sz)}
    ox, oy, oface = v['out']
    po = at(ox, oy, 0.0, oface + leaf_turn(gd, keys[v['door_out']]))
    pgrid = gd.grid(parent)
    ock = gd.key(pgrid.get((int(po[0] // 4096), int(po[1] // 4096)), gd.from_key(wck)))     # (the door's own cell: a big hotel spans several)
    ops.append({'op': 'add', 'cell': ock, 'base': keys[v['door_out']], 'p': po, 's': 1, 'name': hotel + '_out'})
    ai, ao = at(*v['arrive_in']), at(*v['arrive_out'], rise=-v.get('floor_top', FLOOR_TOP) * sz)     # (outside: over the piece's foot)
    ops.append({'op': 'tel', 'cell': ock, 'ref': '$%s_out' % hotel, 'tel': {'door': '$%s_in' % hotel, 'p': ai}})
    ops.append({'op': 'tel', 'cell': names[hotel + '_in']['cell'], 'ref': '$%s_in' % hotel, 'tel': {'door': '$%s_out' % hotel, 'p': ao}})
    return ops, {'hotel': hotel, 'at': [round(x), round(y), round(z)], 'turn': rz, 'city': len(stage), 'things': n, 'doors': names,
                 'missing': missing}
