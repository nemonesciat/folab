"""What Waikiki's people build from what grows back: bamboo, pili-grass thatch, lauhala weave and coir lashings, a contrast
to the ruined look of everything else (the user, 20 Nov 2026: "bamboo and thatch versions of plenty of stuff ... since the
materials are plentiful and renewing"). FOLab's own pieces (modelsets, set 'bamboo': meshes\\folab\\bamboo,
textures\\folab\\bamboo), pictures drawn in code, so a mod with them can be handed round.

The thatch is new, golden pili (`FRESH`), not restyle's grey two-century thatch: these are kept up. Bamboo is `cane` (one
pole round a cylinder, nodes ringed), restyle's `bamboo_wall` (poles side by side: walls, fences), split bamboo for floors
(`deck`), lauhala (`restyle/lauhala`) for wall panels and screens, tapa for what's hung to dry.

- `hut_small`, `hut`: sleeping houses (hale moe) on a lava rock platform a step up, bamboo walls to the waist and lauhala
  over them, a doorway 160 wide in the front, a steep hipped thatch with crossed poles at the ridge.
- `cookhouse`: open on every side, thatch on six posts, a stone hearth ring, a work bench along the back.
- `canoe_shed` (halau wa'a): an A-frame of thatch to the ground along both sides, open at both ends, an outrigger canoe in it.
- `storehouse`: a closed store on four posts with rat guards, a notched-log ladder to its door (not climbed: it's shut).
- `bamboo_fence_lashed` (400 long; waikikiset's `bamboo_fence` is another), `screen` (three lauhala panels folded), `drying_rack` (tapa and lauhala strips on two A-frames).
- `lookout`: a deck at 280 on four bamboo legs, one flight up (the guard tower's own flight, rails and widths), shade thatch.
- `market_stall`: a counter of bamboo, goods on it, a shed thatch on four posts, a lauhala back.
- `bamboo_tower`: FOLab's guard tower (guardtower.py) made of bamboo: the same frame, flights, landings, deck and every
  solid part as they are (its walk is the tower's), legs bundles of three canes, braces and rails canes, the parapet
  lauhala, the deck split bamboo, a thatched pyramid for its tin roof. A swap from the tower is a swap of base.

Front towards -y, standing on z 0, as every piece of modelsets. What's walked on or bumped is solid; the only see-through
pictures are the ragged straw under the eaves. Walked by walkcheck at 32 (an outdoor navmesh's columns) and 16 (`WALKS`)."""
import math

import guardtower as GT
import modelsets
import restyleset as RS
import texpaint as tp
from modelsets import look

SET = 'bamboo'
FRESH = (184, 156, 98)          # (new pili thatch, a season or two in the sun: golden, not restyle's grey)
CANE = (184, 160, 100)


def cane(size=128, seed=810):
    """One bamboo pole, laid round a cylinder: straw streaked down its length, a node ring across it twice a repeat (a
    raised band, darker, a little greener just under it). Repeats both ways."""
    c = tp.Canvas(size, size)
    big, fine = tp.Noise(seed, 4), tp.Noise(seed + 1, 64)

    def fn(x, y):
        g = fine.at(x * 64.0 / size * 3, y * 64.0 / size / 8)
        col = tp._shade(tp._mix(CANE, (150, 140, 96), big.at(x * 4.0 / size, y * 4.0 / size)), 0.8 + 0.3 * g)
        v = (y / float(size) * 2) % 1.0
        if abs(v - 0.5) < 0.035:
            return tp._shade(col, 0.6), 0.9                     # (the node's ring, standing out)
        if 0.535 < v < 0.6:
            return tp._shade(tp._mix(col, (120, 136, 84), 0.4), 0.95), 0.4
        return col, 0.45 + 0.1 * g
    c.paint(fn)
    return c


modelsets.TEXTURES.update({
    'bamboo/cane': lambda: cane(),
    'bamboo/thatch': lambda: tp.thatch(size=512, seed=821, colour=FRESH),
    'bamboo/fringe': lambda: RS.fringe(seed=822, colour=FRESH),
    'bamboo/deck': lambda: RS.bamboo_wall(seed=823, poles=10),
})


def _looks(**more):
    return dict({'bamboo': look('bamboo/cane', tile=60), 'wall': look('restyle/bamboo_wall', tile=150),
                 'mat': look('restyle/lauhala', tile=120), 'thatch': look('bamboo/thatch', tile=220),
                 'fringe': look('bamboo/fringe', tile=RS.FRINGE + 10, alpha=True), 'deck': look('bamboo/deck', tile=140, turned=True),
                 'stone': look('hotel/lava', tile=160)}, **more)


_box = RS._box


def _pole(P, x, y, z0, z1, r=9.0, solid=False, far=False):
    P.append({'shape': 'cylinder', 'r': r, 'r2': r * 0.9, 'h': z1 - z0, 'sides': 7, 'at': [x, y, z0], 'look': 'bamboo',
              'solid': solid, 'far': far, 'material': 'wood'})


def _cane(P, a, b, r=5.0, far=False):
    """A cane from a to b (drawn only)."""
    q = modelsets.limb(a, b, r, r * 0.9, 'bamboo')
    q['far'] = far
    P.append(q)


def _lash(P, x, y, z, r):
    """A coir lashing round a pole at z: a dark band a little proud of it."""
    P.append({'shape': 'cylinder', 'r': r + 1.5, 'h': 9, 'sides': 7, 'at': [x, y, z - 4.5], 'look': 'stone', 'solid': False})


def _walls(P, x0, y0, x1, y1, z, top, door=None, rail=None, t=14.0):
    """Walls round a rectangle on a floor at z: bamboo to `rail`, lauhala above to `top`, each wall solid (t thick, inside
    the line), a doorway in the -y wall `door` = (x middle, width) with a bamboo frame, posts at the corners."""
    rail = rail if rail is not None else z + 100
    walls = [(x0, y0, x1, y0 + t), (x0, y1 - t, x1, y1), (x0, y0 + t, x0 + t, y1 - t), (x1 - t, y0 + t, x1, y1 - t)]
    if door:
        dx, dw = door
        walls = [(x0, y0, dx - dw / 2, y0 + t), (dx + dw / 2, y0, x1, y0 + t)] + walls[1:]
    for X0, Y0, X1, Y1 in walls:
        _box(P, X0, Y0, z, X1, Y1, rail, 'wall', far=True)
        _box(P, X0 + 2, Y0 + 2, rail, X1 - 2, Y1 - 2, top, 'mat', far=True)
        _box(P, X0 - 3, Y0 - 3, rail - 6, X1 + 3, Y1 + 3, rail + 6, 'bamboo', solid=False)       # (the rail between)
    for x in (x0, x1):
        for y in (y0, y1):
            _pole(P, x + (7 if x == x0 else -7), y + (7 if y == y0 else -7), z, top + 8, r=10)
    if door:
        dx, dw = door
        for s in (-1, 1):
            _pole(P, dx + s * (dw / 2 + 6), y0 - 4, z, top, r=8)
        _box(P, dx - dw / 2 - 14, y0 - 12, top - 14, dx + dw / 2 + 14, y0 + t, top, 'bamboo', solid=False)


def _thatch_hip(P, x0, y0, x1, y1, z, h, over, poles=True):
    r0, r1 = RS._hip(P, x0, y0, x1, y1, z, h, over)
    if poles and r0 != r1:
        RS._crossed(P, r0, r1, rise=110, spread=55)
        RS._crossed(P, r1, r0, rise=110, spread=55)
    return r0, r1


# ---------- houses ----------

STEP_UP = 18.0          # (a house's platform over the ground: a step, under navgen.STEP)
DOOR = 160.0            # (a doorway's width: two 32-unit columns clear once an actor's radius is taken off each side)


def hut(W=560.0, D=400.0, name='FOLabBambooHut', mats=3):
    """A sleeping house (see the module's docstring), W x D inside its walls."""
    P = []
    x0, y0, x1, y1 = -W / 2, -D / 2, W / 2, D / 2
    _box(P, x0 - 70, y0 - 70, -30, x1 + 70, y1 + 70, STEP_UP, 'stone', far=True, material='stone')
    _box(P, x0 + 14, y0 + 14, STEP_UP, x1 - 14, y1 - 14, STEP_UP + 2, 'mat', solid=False)       # (mats on the floor)
    top = STEP_UP + 190
    _walls(P, x0, y0, x1, y1, STEP_UP, top, door=(0.0, DOOR))
    _thatch_hip(P, x0, y0, x1, y1, top - 6, 0.85 * (min(W, D) / 2 + 60), 60)
    for k in range(mats):                                   # (sleeping mats rolled along the back wall)
        P.append({'shape': 'cylinder', 'r': 13, 'h': 150, 'sides': 8, 'turn': [0, 90, 0], 'at': [x0 + 40, y1 - 40 - 30 * k, STEP_UP + 15],
                  'look': 'mat', 'solid': False})
    return {'name': name, 'looks': _looks(), 'parts': P}


def hut_small():
    return hut(400.0, 320.0, 'FOLabBambooHutSmall', mats=2)


def cookhouse():
    """Open on every side under a thatch on six posts: a hearth ring of lava stones, a bench along the back."""
    P = []
    W, D = 640.0, 440.0
    x0, y0, x1, y1 = -W / 2, -D / 2, W / 2, D / 2
    eave = 210.0
    for x in (x0, 0.0, x1):
        for y in (y0, y1):
            _pole(P, x, y, -30, eave + 10, r=13, solid=True, far=True)
            _lash(P, x, y, eave - 20, 12)
    for y in (y0, y1):
        _cane(P, (x0 - 20, y, eave - 8), (x1 + 20, y, eave - 8), r=8)
    for x in (x0, x1):
        _cane(P, (x, y0 - 20, eave - 2), (x, y1 + 20, eave - 2), r=8)
    _thatch_hip(P, x0, y0, x1, y1, eave, 300, 70)
    P.append({'shape': 'cylinder', 'r': 70, 'h': 28, 'sides': 10, 'at': [-60, -20, -6], 'look': 'stone', 'material': 'stone'})
    _box(P, x0 + 60, y1 - 90, -10, x1 - 60, y1 - 30, 78, 'wall')             # (the bench)
    for k, x in enumerate((-200, -120, 120, 210)):                                        # (gourds and baskets on it)
        P.append({'shape': 'cylinder', 'r': 18 + 4 * (k % 2), 'r2': 14, 'h': 26 + 8 * (k % 3), 'sides': 9, 'at': [x, y1 - 60, 78], 'look': 'mat', 'solid': False})
    # a rack overhead under the roof, things hung from it to dry
    _cane(P, (x0 + 40, 0, eave - 30), (x1 - 40, 0, eave - 30), r=5)
    for k in range(5):
        x = x0 + 110 + k * 105
        P.append({'shape': 'card', 'size': [40, 70], 'at': [x, 0, eave - 100], 'look': 'tapa', 'solid': False})
    return {'name': 'FOLabBambooCookhouse', 'looks': _looks(tapa=look('restyle/tapa', tile=RS.TAPA)), 'parts': P}


def canoe(P, x, y, z, long=900.0):
    """An outrigger canoe along y: a koa hull tapering to both ends, its float (ama) to +x on two booms (iako)."""
    half = long / 2
    for sgn in (-1, 1):
        P.append({'shape': 'cylinder', 'r': 1, 'r2': 0.12, 'h': 1, 'sides': 10, 'scale': [28, 30, half], 'turn': [-90 * sgn, 0, 0],
                  'at': [x, y, z + 30], 'look': 'hull', 'solid': False})
    for sgn in (-1, 1):
        P.append({'shape': 'cylinder', 'r': 1, 'r2': 0.2, 'h': 1, 'sides': 8, 'scale': [10, 10, half * 0.55], 'turn': [-90 * sgn, 0, 0],
                  'at': [x + 190, y, z + 12], 'look': 'hull', 'solid': False})
    for by in (-170, 170):
        _cane(P, (x - 20, y + by, z + 56), (x + 190, y + by, z + 26), r=4)
    _box(P, x - 26, y - half * 0.9, z, x + 26, y + half * 0.9, z + 52, None)                  # (to bump into: nothing drawn)


def canoe_shed():
    """A halau wa'a: an A-frame of thatch whose sides come down near the ground, open at both ends, a canoe in it."""
    P = []
    L, half_w, ridge, eave = 1300.0, 270.0, 430.0, 50.0
    y0, y1 = -L / 2, L / 2
    for s in (-1, 1):
        a, b = (s * half_w, y0, eave), (0.0, y0, ridge)
        P.append({'shape': 'sheet', 'rows': [RS._line((s * half_w, y0 - 30, eave), (s * half_w, y1 + 30, eave)), RS._line((0, y0 - 30, ridge), (0, y1 + 30, ridge))][::(1 if s < 0 else -1)],
                  'look': 'thatch', 'thick': 10.0, 'at': [0, 0, 0], 'solid': False, 'far': True})
        RS._fringe(P, (s * half_w, y0 - 30, eave), (s * half_w, y1 + 30, eave), drop=30)
        # (a slab under each side to bump into: sheets are never solid)
        run, rise = half_w, ridge - eave
        pitch = math.degrees(math.atan2(rise, run))
        ln = math.hypot(run, rise)
        P.append({'shape': 'box', 'size': [round(ln, 1), L, 14], 'at': [s * half_w / 2, 0, (eave + ridge) / 2 - 18], 'turn': [0, -s * pitch, 0],
                  'look': None, 'solid': True, 'material': 'wood'})
        _box(P, s * half_w - 20 if s > 0 else -half_w - 10, y0, -20, s * half_w + 10 if s > 0 else -half_w + 20, y1, 40, 'stone', far=True, material='stone')
        for y in (y0, -L / 6, L / 6, y1):                                                   # (rafters seen at the ends and inside)
            _cane(P, (s * (half_w - 12), y, eave - 10), (s * -40, y, ridge + 30), r=8)
    _cane(P, (0, y0 - 40, ridge - 6), (0, y1 + 40, ridge - 6), r=10, far=False)           # (the ridge pole)
    for y in (y0, y1):                                                                     # (the gables: lauhala above head height)
        g = 270.0
        w = half_w * (1 - (g - eave) / (ridge - eave))
        P.append({'shape': 'sheet', 'rows': [RS._line((-w, y, g), (w, y, g), 3), RS._line((-10, y, ridge - 12), (10, y, ridge - 12), 3)],
                  'look': 'mat', 'thick': 4.0, 'at': [0, 0, 0], 'solid': False})
    canoe(P, -40.0, 0.0, 0.0)
    for k in range(2):                                                                     # (paddles against the side)
        P.append({'shape': 'slab', 'size': [16, 150, 3], 'at': [-200, -300 + 60 * k, 40], 'turn': [0, -60, 90], 'look': 'hull', 'solid': False})
    return {'name': 'FOLabBambooCanoeShed', 'looks': _looks(hull=look('waikiki/koa', tile=200)), 'parts': P}


def storehouse():
    """A closed store raised on four posts, each with a flat stone rat guard, a notched log leant to its door."""
    P = []
    W, D, floor = 300.0, 260.0, 170.0
    x0, y0, x1, y1 = -W / 2, -D / 2, W / 2, D / 2
    for x in (x0 + 20, x1 - 20):
        for y in (y0 + 20, y1 - 20):
            _pole(P, x, y, -30, floor, r=13, solid=True, far=True)
            P.append({'shape': 'cylinder', 'r': 34, 'h': 8, 'sides': 10, 'at': [x, y, floor - 50], 'look': 'stone', 'solid': False})
    _box(P, x0 - 10, y0 - 10, floor - 14, x1 + 10, y1 + 10, floor, 'deck', far=True)
    _box(P, x0, y0, floor, x1, y1, floor + 150, 'mat', far=True)                        # (solid all through: it's shut)
    for x in (x0, x1):
        for y in (y0, y1):
            _pole(P, x, y, floor, floor + 158, r=8)
    _box(P, -45, y0 - 4, floor + 6, 45, y0 + 2, floor + 128, 'wall', solid=False)        # (its door, bamboo, shut)
    _thatch_hip(P, x0, y0, x1, y1, floor + 146, 230, 50, poles=False)
    P.append(modelsets.limb((0, y0 - 150, 0), (0, y0 - 10, floor - 4), 11, 9, 'log'))     # (the notched log)
    for k in range(5):
        t = (k + 0.7) / 6
        _box(P, -12, y0 - 150 + 140 * t - 6, floor * t + 4, 12, y0 - 150 + 140 * t + 6, floor * t + 9, 'log', solid=False)
    return {'name': 'FOLabBambooStorehouse', 'looks': _looks(log=look('waikiki/tiki_wood', tile=90)), 'parts': P}


# ---------- small things ----------

def fence(L=400.0):
    """A length of bamboo fence, poles side by side between posts, lashed to two rails."""
    P = []
    _box(P, -L / 2, -6, -10, L / 2, 6, 140, 'wall', far=True)
    n = int(L // 100)
    for k in range(n + 1):
        x = -L / 2 + L * k / n
        _pole(P, x, 0, -20, 158, r=7)
    for z in (40, 120):
        _cane(P, (-L / 2 - 6, -9, z), (L / 2 + 6, -9, z), r=4)
        _cane(P, (-L / 2 - 6, 9, z), (L / 2 + 6, 9, z), r=4)
    return {'name': 'FOLabBambooFence', 'looks': _looks(), 'parts': P}


def screen():
    """Three lauhala panels in bamboo frames standing folded, a windbreak or a wall for a corner."""
    P = []
    w, h = 110.0, 180.0
    for k, (x, yaw) in enumerate(((-w, 25.0), (0.0, -25.0), (w, 25.0))):
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        P.append({'shape': 'box', 'size': [w - 8, 10, h - 16], 'at': [x, 0, 10], 'turn': [0, 0, yaw], 'look': 'mat', 'solid': True, 'far': True, 'material': 'wood'})
        for e in (-1, 1):
            ex, ey = x + e * (w / 2) * c, e * (w / 2) * s
            _pole(P, ex, ey, 0, h, r=5)
        for z in (12, h - 6):
            _cane(P, (x - (w / 2) * c, -(w / 2) * s, z), (x + (w / 2) * c, (w / 2) * s, z), r=4)
    return {'name': 'FOLabBambooScreen', 'looks': _looks(), 'parts': P}


def drying_rack():
    """Two A-frames and three bars between: tapa and lauhala strips hung over them to dry."""
    P = []
    L, h = 420.0, 190.0
    for x in (-L / 2, L / 2):
        for s in (-1, 1):
            _cane(P, (x, s * 70, -10), (x, 0, h + 20), r=6)
        _box(P, x - 10, -60, 0, x + 10, 60, h, None)                                   # (to bump into)
    _cane(P, (-L / 2 - 20, 0, h), (L / 2 + 20, 0, h), r=5)
    for s in (-1, 1):
        _cane(P, (-L / 2, s * 34, h * 0.5), (L / 2, s * 34, h * 0.5), r=4)
    for k in range(6):
        x = -L / 2 + 50 + k * 64
        lk = 'tapa' if k % 3 != 2 else 'mat'
        for s in (-1, 1):                                                               # (each hung over the top bar)
            P.append({'shape': 'slab', 'size': [52, 3, 100 - 10 * (k % 2)], 'at': [x, s * 10, h - 98 + 10 * (k % 2)], 'turn': [-s * 6, 0, 0],
                      'look': lk, 'solid': False})
    _box(P, -L / 2 + 20, -18, 70, L / 2 - 20, 18, h, None)                               # (the hung cloth, to bump into)
    P.append({'shape': 'box', 'size': [L - 40, 8, 100], 'at': [0, 0, h - 100], 'look': 'tapa', 'solid': False, 'far_only': True})   # (afar: the row of cloth)
    for x in (-L / 2, L / 2):
        P.append({'shape': 'box', 'size': [10, 120, h], 'at': [x, 0, 0], 'look': 'bamboo', 'solid': False, 'far_only': True})
    return {'name': 'FOLabBambooDryingRack', 'looks': _looks(tapa=look('restyle/tapa', tile=60)), 'parts': P}


def market_stall():
    """A stall: a bamboo counter with fruit and baskets on it, a shed thatch on four posts, a lauhala back."""
    P = []
    W, D = 340.0, 240.0
    x0, y0, x1, y1 = -W / 2, -D / 2, W / 2, D / 2
    front, back = 210.0, 270.0
    for x in (x0, x1):
        for y, top in ((y0, front), (y1, back)):
            _pole(P, x, y, -20, top + 6, r=10, solid=True, far=True)
    _box(P, x0, y0, -10, x1, y0 + 60, 92, 'wall', far=True)                # (the counter)
    _box(P, x0, y1 - 12, -10, x1, y1, back - 20, 'mat', far=True)                       # (the back)
    P.append({'shape': 'sheet', 'rows': [RS._line((x0 - 50, y1 + 40, back + 10), (x1 + 50, y1 + 40, back + 10), 4), RS._line((x0 - 50, y0 - 70, front - 4), (x1 + 50, y0 - 70, front - 4), 4)],
              'look': 'thatch', 'thick': 10.0, 'at': [0, 0, 0], 'solid': False, 'far': True})
    RS._fringe(P, (x0 - 50, y0 - 70, front - 4), (x1 + 50, y0 - 70, front - 4), drop=40)
    for y, z in ((y0, front - 8), (y1, back - 8)):
        _cane(P, (x0 - 30, y, z), (x1 + 30, y, z), r=7)
    # goods: baskets, coconuts, a crate of pineapples
    for k, x in enumerate((-120, -30, 70, 140)):
        P.append({'shape': 'cylinder', 'r': 26 - 3 * (k % 2), 'r2': 30, 'h': 22, 'sides': 10, 'at': [x, y0 + 30, 92], 'look': 'mat', 'solid': False})
    for k in range(5):
        P.append({'shape': 'ball', 'r': 11, 'sides': 8, 'rings': 5, 'at': [-120 + 9 * (k % 3) - 9, y0 + 26 + 8 * (k // 3), 112], 'look': 'husk', 'solid': False})
    P.append({'shape': 'box', 'size': [60, 40, 34], 'at': [70, y0 + 30, 112], 'look': 'pineapples', 'solid': False})
    return {'name': 'FOLabBambooMarketStall', 'looks': _looks(husk=look('waikiki/husk', tile=60), pineapples=look('waikiki/pineapples')), 'parts': P}


# ---------- what's climbed ----------

LOOK_RISE = 280.0       # (the lookout's deck)
LOOK_HALF = 200.0


def lookout():
    """A deck at LOOK_RISE on four bamboo legs, one flight straight up to its front (the guard tower's flight, ramp and
    rails: WIDE between the rails, which stand wholly outside it), rails round the rest, a shade thatch over it."""
    P = []
    H, z = LOOK_HALF, LOOK_RISE
    wide = GT.WIDE
    run = z * GT.battleship.LADDER_RUN
    foot = -H - run - GT.SINK * GT.battleship.LADDER_RUN
    roof = z + 230
    for sx in (-1, 1):
        for sy in (-1, 1):
            _pole(P, sx * (H - 16), sy * (H - 16), -GT.SINK, roof, r=14, solid=True, far=True)
            _lash(P, sx * (H - 16), sy * (H - 16), z - 30, 14)
        for sy0, sy1 in ((-1, 1), (1, -1)):                                           # (X braces on the sides)
            _cane(P, (sx * (H - 16), sy0 * (H - 16), 10), (sx * (H - 16), sy1 * (H - 16), z - 40), r=6)
    for sy in (-1, 1):
        _cane(P, (-(H - 16), sy * (H - 16), 20), ((H - 16), -sy * (H - 16), z - 40), r=6)
    _box(P, -H, -H, z - 20, H, H, z, 'deck', far=True)
    for y in (-H + 30, 0, H - 30):
        _box(P, -H, y - 8, z - 40, H, y + 8, z - 20, 'bamboo', solid=False)
    GT._flight(P, 0.0, foot, -GT.SINK, -H, z, wide=wide)
    for x, o in ((-wide / 2, (-1, 0)), (wide / 2, (1, 0))):
        GT._rail(P, (x, foot, -GT.SINK), (x, -H, z), o)
    GT._rail(P, (-H, -H, z), (-wide / 2, -H, z), (0, -1))
    GT._rail(P, (wide / 2, -H, z), (H, -H, z), (0, -1))
    GT._rail(P, (H, -H, z), (H, H, z), (1, 0))
    GT._rail(P, (-H, H, z), (H, H, z), (0, 1))
    GT._rail(P, (-H, -H, z), (-H, H, z), (-1, 0))
    _thatch_hip(P, -H, -H, H, H, roof, 170, 50, poles=False)
    return _bamboo_desc({'name': 'FOLabBambooLookout', 'looks': {}, 'parts': P})


def _bamboo_desc(desc):
    """A description made with guardtower's helpers (its looks 'dark' timber, 'deck' treads and planks, 'boards', 'tin')
    in bamboo: thin timbers (beams, posts) drawn as canes, solid ones kept exactly as they were (collision is the walk)
    and, where a cane is drawn for them, left as collision only."""
    out = []
    for p in desc['parts']:
        if p.get('look') != 'dark' or p['shape'] != 'box':
            out.append(p)
            continue
        sx, sy, sz = p['size']
        turned = any(abs(a) > 1e-6 for a in p.get('turn', (0, 0, 0)))
        if turned and abs(sx - sz) < 0.5 and sx <= 14 and sy > 3 * sx:            # (a beam: _beam's square timber)
            pitch, _r, yaw = (math.radians(a) for a in p['turn'])
            d = (-math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch))
            up = (math.sin(yaw) * math.sin(pitch), -math.cos(yaw) * math.sin(pitch), math.cos(pitch))
            m = [p['at'][k] + up[k] * sx / 2 for k in range(3)]
            a = tuple(m[k] - d[k] * sy / 2 for k in range(3))
            b = tuple(m[k] + d[k] * sy / 2 for k in range(3))
            _cane(out, a, b, r=sx / 2 + 1, far=p.get('far', False))
            if p.get('solid'):
                out.append(dict(p, look=None))
            continue
        if not turned and sx <= 30 and sy <= 30 and sz > 3 * max(sx, sy):        # (a post or a leg)
            x, y, z0 = p['at']
            r = max(sx, sy) / 2
            if r >= 12:                                                              # (a leg: a bundle of three canes)
                for k in range(3):
                    a = math.radians(90 + 120 * k)
                    _pole(out, x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z0, z0 + sz, r=r * 0.55, far=(k == 0 and p.get('far', False)))
                    _lash(out, x, y, z0 + sz * 0.5, r * 1.05)
            else:
                _pole(out, x, y, z0, z0 + sz, r=r + 0.5, far=p.get('far', False))
            if p.get('solid'):
                out.append(dict(p, look=None, far=False))
            continue
        out.append(dict(p, look='bamboo'))
    looks = _looks(dark=look('bamboo/cane', tile=60), boards=look('restyle/lauhala', tile=120))
    looks.update(desc.get('looks_more', {}))
    return {'name': desc['name'], 'looks': looks, 'parts': out}


def bamboo_tower():
    """See the module's docstring: guardtower.tower() with its timbers as canes, its parapet lauhala, its roof thatch."""
    t = GT.tower()
    parts = [p for p in t['parts'] if p.get('look') != 'tin']
    parts = [dict(p, look='mat') if p.get('look') == 'boards' else p for p in parts]
    P = list(parts)
    _thatch_hip(P, -GT.HALF, -GT.HALF, GT.HALF, GT.HALF, GT.ROOF, 280, 60, poles=False)
    P.append({'shape': 'cylinder', 'r': 22, 'r2': 5, 'h': 50, 'sides': 8, 'at': [0, 0, GT.ROOF + 280 - 16], 'look': 'thatch', 'solid': False})   # (the topknot)
    return _bamboo_desc({'name': 'FOLabBambooGuardTower', 'parts': P})


# ---------- registered ----------

PIECES = {'bamboo_hut': ('Thatch hut (sleeping house)', hut), 'bamboo_hut_small': ('Thatch hut, small', hut_small),
          'bamboo_cookhouse': ('Thatch cookhouse, open sided', cookhouse), 'bamboo_canoe_shed': ('Canoe shed (halau wa\'a)', canoe_shed),
          'bamboo_storehouse': ('Storehouse on posts', storehouse), 'bamboo_fence_lashed': ('Bamboo fence, lashed (400)', fence),
          'bamboo_screen': ('Lauhala screen', screen), 'bamboo_drying_rack': ('Drying rack', drying_rack),
          'bamboo_lookout': ('Bamboo lookout platform', lookout), 'bamboo_market_stall': ('Bamboo market stall', market_stall),
          'bamboo_tower': ('Bamboo guard tower (for FOLab\'s guard tower)', bamboo_tower)}
for _k, (_label, _fn) in PIECES.items():
    assert modelsets.PIECES.get(_k, {}).get('set', SET) == SET, _k + " is another set's piece"     # (waikikiset has a bamboo_fence)
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k[7:], 'describe': _fn, 'edid': _fn()['name']})

# walkcheck: how each is walked (from the ground round it) and the spots it promises
WALKS = {'bamboo_hut': {'goals': [('inside', (0.0, 60.0, STEP_UP))]},
         'bamboo_hut_small': {'goals': [('inside', (0.0, 40.0, STEP_UP))]},
         'bamboo_cookhouse': {'goals': [('by the hearth', (100.0, -60.0, 0.0)), ('at the bench', (0.0, 100.0, 0.0))]},
         'bamboo_canoe_shed': {'goals': [('beside the canoe', (130.0, 0.0, 0.0)), ('through to the back', (0.0, 600.0, 0.0))]},
         'bamboo_storehouse': {'goals': [('under it', (0.0, 0.0, 0.0))]},
         'bamboo_market_stall': {'goals': [('behind the counter', (0.0, 30.0, 0.0))]},
         'bamboo_lookout': {'goals': [('the deck', (0.0, 0.0, LOOK_RISE)), ('its back corner', (120.0, 120.0, LOOK_RISE))]},
         'bamboo_tower': GT.WALK}
