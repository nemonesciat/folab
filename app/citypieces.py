"""Pieces for a city lived in after the end: ways up the outside of buildings, walkways between roofs, lookout towers.

New Vegas has no ladder a body can climb (a "ladder" in the game is a door that moves you), so a way up that works for
the player and reads at a glance is a ramp: planks on a scaffold, zigzagging up a wall to the roof. Everything here is
made of walkable slabs with collision (modelmake boxes), so the player walks up; nobody else does until a navmesh
covers it, which none does yet: a sniper put on a roof stays on it.

A ramp tower is made to measure, since no two roofs are one height: `ramp_tower(high, drop)` registers the piece for
that height (to the roof's edge, or its parapet) and that drop from the parapet down to the roof's floor, and gives its
name; `bridge(long)` likewise a plank walkway of a length. They are pieces of `modelsets` like any other (set 'city':
meshes\\folab\\city, textures\\folab\\city), registered here so that modelsets itself needs no edit.

A piece's frame: x along the wall it stands against, +y towards the building (the tower's own face nearest the wall is
y = 0), z up from the ground it stands on."""
import math

import modelsets
import texpaint as tp
from modelsets import look

RISE = 256.0                # most a flight climbs
RUN = 448.0                 # along the wall, each flight: so a ramp is under 30 degrees
LANE = 110.0                # a ramp's width
REACH = 170.0               # how far the top platform reaches over the wall onto the roof
STEP = 64.0                 # heights are made in steps of this (a tower too tall is sunk into the ground by the rest)
# a tighter tower for a short wall or a narrow gap: shorter flights, a little steeper (31 degrees)
RISE_TIGHT, RUN_TIGHT = 192.0, 320.0
LAND = 128.0                # a landing's length along the wall, past each end of the flights
# Every joint is flush: a ramp ends exactly where its landing begins, at the landing's height, and nothing of one lies
# over another. (The first versions ran each ramp 12 units past its end and laid the top platform over the last ramp's
# end: a lip, and no headroom at the top. walkcheck.py now walks every piece from the ground to its top.)

modelsets.TEXTURES.update({
    'city/planks': lambda: tp.planks((158, 146, 126), seed=101, wear=0.5),
    'city/rust': lambda: tp.painted_metal((112, 98, 86), seed=102, rust=0.5),
    'city/tin': lambda: tp.corrugated((128, 132, 128), seed=103),
})


def _looks():
    return {'plank': look('city/planks', tile=128, turned=True), 'pole': look('city/rust', tile=64), 'tin': look('city/tin', tile=192)}


def _ramp(parts, x0, x1, y, z0, z1):
    """A plank ramp from (x0, z0) to (x1, z1) in the lane at y: its top exactly at z0 at x0 and z1 at x1, a rail down
    each side."""
    if x1 < x0:                                                 # (laid from its low x end: turned the other way round a
        x0, x1, z0, z1 = x1, x0, z1, z0                         # slab is upside down, and its top 8 units low at both ends)
    ln = math.hypot(x1 - x0, z1 - z0)
    ang = math.degrees(math.atan2(z1 - z0, x1 - x0))
    mid = [(x0 + x1) / 2, y, (z0 + z1) / 2 - 8]
    parts.append({'shape': 'slab', 'size': [ln, LANE, 8], 'at': mid, 'turn': [0, -ang, 0], 'look': 'plank', 'material': 'wood'})
    for side in (-1, 1):
        parts.append({'shape': 'box', 'size': [ln, 5, 5], 'at': [mid[0], y + side * (LANE / 2 - 4), mid[2] + 96], 'turn': [0, -ang, 0], 'look': 'pole', 'solid': False})


LANE_A, LANE_B = -LANE - 20 - LANE / 2, -10 - LANE / 2        # the two lanes' middles, in front of the face (y < 0)
FRONT = -(2 * LANE + 30)                                       # the lanes' outer edge


def _flights(parts, n, rise, half, last_landing=True):
    """n flights of ramps between two lanes, each `rise` up and 2 * half along, turning on a landing past each end.
    Returns which end (-1 or 1) the top is at. Lane A's flights pass 2 * rise under each other, lane B's likewise."""
    for k in range(n):
        x0, x1 = (-half, half) if k % 2 == 0 else (half, -half)
        _ramp(parts, x0, x1, LANE_A if k % 2 == 0 else LANE_B, k * rise, (k + 1) * rise)
        if k < n - 1 or last_landing:
            side = 1 if x1 > 0 else -1
            parts.append({'shape': 'slab', 'size': [LAND, -FRONT, 8], 'at': [side * (half + LAND / 2), FRONT / 2, (k + 1) * rise - 8], 'look': 'plank', 'material': 'wood'})
    return 1 if (n - 1) % 2 == 0 else -1


def _scaffold(parts, high, n, rise, half, back=0.0):
    """Standards, ledgers and braces round flights (none of it solid)."""
    end = half + LAND
    for x in (-end, 0, end):
        for y in (FRONT - 4, back):
            parts.append({'shape': 'box', 'size': [9, 9, high + 110], 'at': [x, y, 0], 'look': 'pole', 'solid': False})
    for k in range(1, n + 1):
        for y in (FRONT - 4, back):
            parts.append({'shape': 'box', 'size': [2 * end, 6, 6], 'at': [0, y, k * rise - 20], 'look': 'pole', 'solid': False})
    for k in range(n):
        ang = math.degrees(math.atan2(rise, end))
        for x in (-end / 2, end / 2):
            parts.append({'shape': 'box', 'size': [math.hypot(end, rise), 5, 5], 'at': [x, FRONT - 4, k * rise + rise / 2],
                          'turn': [0, ang if (k + (x > 0)) % 2 else -ang, 0], 'look': 'pole', 'solid': False})


def describe_tower(high, drop=0.0, hut=False, tight=False):
    """A scaffold of plank ramps `high` up. At the top a platform reaches REACH past the tower's face (over a wall and
    onto a roof); with `drop`, a last ramp goes down that much from it to the roof's floor behind a parapet. hut: a
    lookout on top in place of the reach: a floor past the top end, a tin roof on posts, tin to the waist on three
    sides, open towards the ramps."""
    parts = []
    n = max(1, int(math.ceil(high / (RISE_TIGHT if tight else RISE))))
    rise = high / n
    half = (RUN_TIGHT if tight else RUN) / 2
    side = _flights(parts, n, rise, half, last_landing=False)
    if hut:
        cx, cy = side * (half + 210), FRONT / 2
        parts.append({'shape': 'slab', 'size': [420, 420, 10], 'at': [cx, cy, high - 10], 'look': 'plank', 'material': 'wood'})
        for dx in (-200, 200):
            for dy in (-200, 200):
                # (its posts go to the ground: the hut stands on its own legs beside the ramps)
                parts.append({'shape': 'box', 'size': [10, 10, high + 250], 'at': [cx + dx, cy + dy, 0], 'look': 'pole', 'solid': False})
        parts.append({'shape': 'slab', 'size': [470, 470, 6], 'at': [cx, cy, high + 244], 'turn': [7, 0, 0], 'look': 'tin', 'solid': False})
        for dx, dy, w, d in ((0, -205, 420, 6), (side * 205, 0, 6, 420), (0, 205, 420, 6)):
            parts.append({'shape': 'box', 'size': [w, d, 96], 'at': [cx + dx, cy + dy, high], 'look': 'tin', 'material': 'metal'})
    else:
        deep = -FRONT + REACH
        tx = side * (half + LAND / 2)
        parts.append({'shape': 'slab', 'size': [LAND, deep, 8], 'at': [tx, FRONT + deep / 2, high - 8], 'look': 'plank', 'material': 'wood'})
        if drop > 4:                                           # down off a parapet to the roof's floor
            run = max(140.0, drop * 2.1)
            ln = math.hypot(run, drop)
            parts.append({'shape': 'slab', 'size': [LAND, ln, 8], 'at': [tx, REACH + run / 2, high - drop / 2 - 8],
                          'turn': [-math.degrees(math.atan2(drop, run)), 0, 0], 'look': 'plank', 'material': 'wood'})
    _scaffold(parts, high, n, rise, half)
    return {'name': 'FOLabCity%s%dx%d' % ('Lookout' if hut else 'RampTight' if tight else 'Ramp', round(high), round(drop)), 'looks': _looks(), 'parts': parts}


def describe_bridge(long):
    """A plank walkway `long` from end to end (along x), rails on posts both sides, sagging a little in the middle."""
    parts = []
    n = max(2, int(round(long / 200.0)))
    seg = long / n
    for k in range(n):                                         # in lengths, each a little lower towards the middle
        t0, t1 = k / n, (k + 1) / n
        sag = lambda t: -18.0 * math.sin(math.pi * t)
        x0, x1 = -long / 2 + k * seg, -long / 2 + (k + 1) * seg
        ang = math.degrees(math.atan2(sag(t1) - sag(t0), seg))
        parts.append({'shape': 'slab', 'size': [seg + 10, 120, 8], 'at': [(x0 + x1) / 2, 0, (sag(t0) + sag(t1)) / 2 - 8], 'turn': [0, -ang, 0], 'look': 'plank', 'material': 'wood'})
    for k in range(n + 1):
        x = -long / 2 + k * seg
        for y in (-58, 58):
            parts.append({'shape': 'box', 'size': [7, 7, 104], 'at': [x, y, -18.0 * math.sin(math.pi * k / n) - 6], 'look': 'pole', 'solid': False})
    for y in (-58, 58):
        parts.append({'shape': 'box', 'size': [long, 5, 5], 'at': [0, y, 80], 'look': 'pole', 'solid': False})
    return {'name': 'FOLabCityBridge%d' % round(long), 'looks': _looks(), 'parts': parts}


FLOOR_UP = 256.0            # a shanty's storeys: one flight each
DEEP = 440.0                # its floors, back from the flights


def describe_shanty(levels=3, seed=1):
    """Shacks stacked on a scaffold: two lanes of plank ramps up the front, a landing at each storey at each end, and
    behind them a floor at every storey, each a room of tin and salvaged boards at the back and an open balcony at the
    front with a waist-high wall to shoot over; a tin roof on top. The ramps never run over a floor and no floor over a
    ramp; each landing meets its floor flush. Every floor is a place to shoot from; the ground floor is a room too."""
    import random
    rnd = random.Random(seed)
    looks = dict(_looks(), paint=look('planks_turquoise', tile=128), paint2=look('planks_coral', tile=128))
    parts = []
    half = RUN / 2
    wide = half + LAND                                          # the floors reach the landings at both ends
    _flights(parts, levels, FLOOR_UP, half)
    wall = lambda: rnd.choice(('tin', 'tin', 'plank', 'paint', 'paint2'))
    for k in range(levels + 1):
        z = k * FLOOR_UP
        if k:
            parts.append({'shape': 'slab', 'size': [2 * wide, DEEP, 10], 'at': [0, DEEP / 2, z - 10], 'look': 'plank', 'material': 'wood'})
        if k == levels:
            break                                               # (the top floor is a roof terrace: open, under the tin)
        parts.append({'shape': 'box', 'size': [2 * wide, 6, 200], 'at': [0, DEEP - 3, z], 'look': wall(), 'material': 'metal'})   # the back
        for sx in (-1, 1):                                      # sides, on the back half only: the front corners are the way in
            parts.append({'shape': 'box', 'size': [6, DEEP / 2, rnd.choice((200, 200, 130))], 'at': [sx * (wide - 3), DEEP * 0.75, z], 'look': wall(), 'material': 'metal'})
        if k:                                                   # a waist wall along the front, short of the ends
            parts.append({'shape': 'box', 'size': [2 * (half - 70), 6, 92], 'at': [rnd.choice((0, -40, 40)), 30, z], 'look': wall(), 'material': 'metal'})
        if rnd.random() < 0.6:                                  # a partition, half way back, with a gap
            parts.append({'shape': 'box', 'size': [6, DEEP * 0.45, 190], 'at': [rnd.choice((-1, 1)) * 60, DEEP * 0.72, z], 'look': wall(), 'material': 'metal'})
    top = levels * FLOOR_UP
    parts.append({'shape': 'slab', 'size': [2 * wide + 60, DEEP + 60, 6], 'at': [0, DEEP / 2, top + 210], 'turn': [-8, 0, 0], 'look': 'tin', 'solid': False})
    for x in (-wide, -half, half, wide):
        for y in (40, DEEP - 6):
            parts.append({'shape': 'box', 'size': [9, 9, top + 230], 'at': [x, y, 0], 'look': 'pole', 'solid': False})
    _scaffold(parts, top, levels, FLOOR_UP, half, back=-4)
    return {'name': 'FOLabCityShanty%dx%d' % (levels, seed), 'looks': looks, 'parts': parts}


def describe_leanto(seed=1):
    """A lean-to to sleep under, out of the sun and the rain: tin at the back, salvaged boards each side, a tin roof
    sloping down to the back, the front (-y) open across its whole width. Headroom: 214 at the open side, 166 at the back,
    so one stands up going in and the bedding lies under the low end. 360 wide, 300 deep."""
    import random
    rnd = random.Random(seed)
    looks = dict(_looks(), paint=look('planks_turquoise', tile=128), paint2=look('planks_coral', tile=128))
    side = rnd.choice(('plank', 'paint', 'paint2'))
    parts = [{'shape': 'box', 'size': [360, 6, 166], 'at': [0, 147, 0], 'look': 'tin', 'material': 'metal'},
             {'shape': 'box', 'size': [6, 300, 166], 'at': [-177, 0, 0], 'look': side, 'material': 'wood'},
             {'shape': 'box', 'size': [6, 300 * rnd.choice((1.0, 0.7)), 166], 'at': [177, 150 - 300 * 0.5 * rnd.choice((1.0, 1.0)), 0], 'look': rnd.choice(('tin', side)), 'material': 'metal'},
             {'shape': 'slab', 'size': [400, 340, 6], 'at': [0, 0, 190], 'turn': [-9, 0, 0], 'look': 'tin', 'solid': False}]
    for x in (-177, 177):
        parts.append({'shape': 'box', 'size': [8, 8, 220], 'at': [x, -147, 0], 'look': 'pole', 'solid': False})
    return {'name': 'FOLabCityLeanTo%d' % seed, 'looks': looks, 'parts': parts}


def shanty(levels=3, seed=1):
    """(piece, how far its floors reach each way along x, the height of its floors). Its ramps are in front (y < 0),
    its floors behind (y 0 to DEEP)."""
    return _register('shanty2_%d_%d' % (levels, seed), 'Shanty, %d floors' % levels, lambda: describe_shanty(levels, seed)), RUN / 2 + LAND, FLOOR_UP


def leanto(seed=1):
    return _register('leanto2_%d' % seed, 'Lean-to', lambda: describe_leanto(seed))


def _register(name, label, describe):
    if name not in modelsets.PIECES:
        modelsets.PIECES[name] = {'label': label, 'set': 'city', 'file': name, 'describe': describe, 'edid': describe()['name']}
    return name


def ramp_tower(high, drop=0.0, tight=False):
    """The piece for a way up `high` (rounded up to the next STEP) with that drop behind a parapet (to the nearest 32).
    tight: the shorter tower. Returns (piece, its real height)."""
    h = max(STEP * 3, math.ceil(high / STEP) * STEP)
    d = round(drop / 32.0) * 32.0
    return _register('ramp2%s_%d_%d' % ('t' if tight else '', h, d), 'Ramp up, %d high%s' % (h, ', tight' if tight else ''), lambda: describe_tower(h, d, tight=tight)), h


def tower_size(tight=False):
    """(half its length along the wall, how far it stands out from it, where the first ramp starts: along, out)."""
    run = RUN_TIGHT if tight else RUN
    return run / 2 + LAND + 20, -FRONT + 4, (-run / 2, -LANE_A)


def lookout(high=768.0):
    h = max(STEP * 4, math.ceil(high / STEP) * STEP)
    return _register('lookout2_%d' % h, 'Lookout tower, %d high' % h, lambda: describe_tower(h, hut=True)), h


def bridge(long):
    """The piece for a walkway at least `long` (in steps of 64). Returns (piece, its real length)."""
    ln = max(256.0, math.ceil(long / 64.0) * 64.0)
    return _register('bridge_%d' % ln, 'Plank walkway, %d long' % ln, lambda: describe_bridge(ln)), ln
