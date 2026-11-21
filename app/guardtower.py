"""FOLab's own guard tower, in place of the game's NVGuardTower01 (and the parts NVGuardTower01a-d the game stands with it).

The game's tower is a frame and a hut (NCR_GuardTower01.nif) with its flights and landings in four further models, all
stood at one spot and turn. In nv-rs every one FOLab stood showed panels and netting hanging in the air (20 Nov 2026):
the cause is in how that engine draws the game's model and wasn't found. This is one model with everything in it, in the
game tower's frame (its origin on the ground under the middle, the frame's legs ±LEG), so a swap of the ref's base
(`restyle.ops`, `swap_ops`) leaves the place and turn as they were:

  - four legs from under the ground up through the deck to the roof, X braces and girts between them on every face;
  - three flights of stairs round the outside of the legs, a landing at each turn: up along +x (going -y) from the ground
    to L1 at RISE, along -y (going -x) to L2, along -x (going +y) to the top landing beside the deck at DECK;
  - the deck (±HALF) inside a plank parapet waist high, open only where the top landing joins it, a tin roof on the legs;
  - every flight and landing edge with a fall beyond it railed (a handrail to see, a solid wall to stop a walker), the
    treads to see over a solid ramp to walk (battleship.ladder, 39 degrees).

Walked from the ground to the deck in its real collision by walkcheck (`py -3 app/walkcheck.py guard_tower`) before any
navmesh is made. Its far model is the legs, the deck, the parapet and the roof. Builders that stand the game's tower pass
their ops through `instead`, so a rebuild stands this one; `swap_ops` changes the ones a mod already has."""
import math

import battleship
import modelsets
import texpaint as tp
import texwear as tw
from modelsets import look

SET = 'restyle'
PIECE = 'guard_tower'
GAME = 'NVGuardTower01'
GAME_PARTS = ('NVGuardTower01a', 'NVGuardTower01b', 'NVGuardTower01c', 'NVGuardTower01d')

LEG = 180.0             # (the legs' middles, ±LEG each way: inside the stairs' ring)
HALF = 200.0            # (the deck, ±HALF: clear of the ring, whose inside edge is RING - WIDE/2)
WIDE = 176.0            # (a flight's and a landing's width between its rails. Outdoor navmeshes are made in 32-unit
                        # columns: at 120 wide, with the rails taking the edge columns, nothing was left to walk up)
RING = HALF + 5.0 + WIDE / 2    # (the stairs' middle line, ±RING out from the middle)
DECK = 840.0            # (the deck's top: the game's last landing is about 836)
RISE = 280.0            # (each flight's climb: three of them to the deck)
ROOF = 1040.0           # (the roof's eaves)
SINK = 40.0             # (how far the legs and the first flight's foot go under the ground: the ground is rarely flat)
PARAPET = 100.0
OPEN_TO = 40.0          # (the deck's +y side is open from its -x end to here, where the top landing's walk joins it)
RAMP = 12.0             # (a ramp's thickness: its ends are square to its slope, and at 30 thick the steep strip each
                        # left before a landing broke the walk, at one column size or the other)
VOXEL = 32.0            # (navgen.VOXEL_OUT: walked as an outdoor navmesh is made)

modelsets.TEXTURES.update({
    'tower/timber': lambda: tw.wood((118, 104, 86), size=256, seed=790, count=4, paint_left=0.0),
    'tower/boards': lambda: tp.planks((132, 116, 92), seed=791, wear=0.3),
    'tower/deck': lambda: tp.planks((124, 104, 80), seed=792, wear=0.4),
    'tower/tin': lambda: tp.corrugated((120, 112, 102), seed=793, ridges=18),
})


def _looks():
    # (battleship.ladder names its ramp and rails 'dark', its treads 'deck')
    return {'dark': look('tower/timber', tile=96), 'deck': look('tower/deck', tile=120, turned=True),
            'boards': look('tower/boards', tile=120), 'tin': look('tower/tin', tile=150)}


def _box(P, x0, y0, z0, x1, y1, z1, lk, solid=True, far=False):
    P.append({'shape': 'box', 'size': [round(x1 - x0, 1), round(y1 - y0, 1), round(z1 - z0, 1)],
              'at': [round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1), round(z0, 1)], 'look': lk, 'solid': solid, 'far': far,
              'material': 'wood'})


def _beam(P, a, b, w, lk='dark', solid=False, far=False):
    """A square timber from point a to point b."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    ln = math.sqrt(dx * dx + dy * dy + dz * dz)
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    yaw = math.degrees(math.atan2(-dx, dy)) if math.hypot(dx, dy) > 1e-6 else 0.0
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
    # (a box stands on the middle of its underside: down by half its thickness so the timber's middle is on the line)
    P.append({'shape': 'box', 'size': [w, round(ln, 1), w], 'at': [round(mid[0], 1), round(mid[1], 1), round(mid[2] - w / 2, 1)],
              'turn': [round(pitch, 3), 0, round(yaw, 3)], 'look': lk, 'solid': solid, 'far': far, 'material': 'wood'})


def _rail(P, a, b, out):
    """A rail along a fall from a to b (each (x, y, z) of the floor at the edge), out: the way the fall is ((1, 0),
    (0, -1)...). A handrail and its posts to see on the edge; a wall 90 high and 20 thick (no look: collision only)
    wholly beyond the edge, so the walk keeps the floor's full width."""
    ox, oy = out[0] * 12.0, out[1] * 12.0
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    run = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(-dx, dy))
    pitch = math.degrees(math.atan2(dz, run))
    ln = math.sqrt(run * run + dz * dz)
    a0 = a
    if dz > 0:
        # (a box's end is square to the slope, so a sloped wall's top overhangs its foot by 90 sin(pitch) at 70 up: over
        # the landing below, a lip that blocked the way on. The sloped wall starts that far up, a level piece fills in)
        k = 90.0 * math.sin(math.radians(pitch)) / run
        a0 = (a[0] + dx * k, a[1] + dy * k, a[2] + dz * k)
        P.append({'shape': 'box', 'size': [20, round(run * k, 1), 90], 'at': [round((a[0] + a0[0]) / 2 + ox, 1), round((a[1] + a0[1]) / 2 + oy, 1), round(a[2], 1)],
                  'turn': [0, 0, round(yaw, 3)], 'look': None, 'solid': True, 'material': 'wood'})
    ln0 = math.sqrt((b[0] - a0[0]) ** 2 + (b[1] - a0[1]) ** 2 + (b[2] - a0[2]) ** 2)
    mid = ((a0[0] + b[0]) / 2 + ox, (a0[1] + b[1]) / 2 + oy, (a0[2] + b[2]) / 2)
    P.append({'shape': 'box', 'size': [20, round(ln0, 1), 90], 'at': [round(mid[0], 1), round(mid[1], 1), round(mid[2], 1)],
              'turn': [round(pitch, 3), 0, round(yaw, 3)], 'look': None, 'solid': True, 'material': 'wood'})
    ox, oy = out[0] * 4.0, out[1] * 4.0
    _beam(P, (a[0] + ox, a[1] + oy, a[2] + 88), (b[0] + ox, b[1] + oy, b[2] + 88), 7)
    _beam(P, (a[0] + ox, a[1] + oy, a[2] + 45), (b[0] + ox, b[1] + oy, b[2] + 45), 5)
    posts = max(1, int(round(ln / 110.0)))
    for k in range(posts + 1):
        t = k / float(posts)
        x, y = a[0] + dx * t + ox, a[1] + dy * t + oy
        _box(P, x - 4, y - 4, a[2] + dz * t, x + 4, y + 4, a[2] + dz * t + 92, 'dark', solid=False)


def _flight(P, x, y_foot, z_foot, y_top, z_top, wide, x_top=None):
    """A flight from (x, y_foot, z_foot) up to (x_top, y_top, z_top): a thin ramp to walk (RAMP thick, its top on the
    line), treads and stringers to see over it."""
    x_top = x if x_top is None else x_top
    dx, dy, rise = x_top - x, y_top - y_foot, z_top - z_foot
    run = math.hypot(dx, dy)
    ln = math.hypot(run, rise)
    pitch = math.degrees(math.atan2(rise, run))
    yaw = math.degrees(math.atan2(-dx, dy))
    c = math.cos(math.radians(pitch))
    mid = ((x + x_top) / 2, (y_foot + y_top) / 2, (z_foot + z_top) / 2 - RAMP / c)
    P.append({'shape': 'box', 'size': [wide, round(ln, 1), RAMP], 'at': [round(v, 1) for v in mid], 'turn': [round(pitch, 3), 0, round(yaw, 3)],
              'look': 'dark', 'solid': True, 'material': 'wood'})
    steps = max(2, int(rise / 22))
    for k in range(steps):
        t = (k + 0.5) / steps
        _box(P, x + dx * t - 0.5, y_foot + dy * t - 0.5, z_foot + rise * t, x + dx * t + 0.5, y_foot + dy * t + 0.5, z_foot + rise * t + 4, 'deck', solid=False)
        P[-1]['size'] = [wide - 8, 26, 4]
        P[-1]['turn'] = [0, 0, round(yaw, 3)]
    across = (dy / run, -dx / run)
    for sx in (-1, 1):                                     # (stringers under the treads' ends)
        _beam(P, (x + sx * across[0] * (wide / 2 - 6), y_foot + sx * across[1] * (wide / 2 - 6), z_foot - 14),
              (x_top + sx * across[0] * (wide / 2 - 6), y_top + sx * across[1] * (wide / 2 - 6), z_top - 14), 12)


def _landing(P, x0, y0, x1, y1, z, posts=True):
    """A landing's planks at z (14 thick, its top at z), joists under, and posts from its outer corners to the ground."""
    _box(P, x0, y0, z - 14, x1, y1, z, 'deck')
    for y in (y0 + 10, y1 - 10):
        _box(P, x0, y - 6, z - 34, x1, y + 6, z - 14, 'dark', solid=False)
    if posts:
        for x, y in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
            if abs(x) > RING - WIDE / 2 - 1 or abs(y) > RING - WIDE / 2 - 1:     # (the corners out past the legs)
                cx, cy = x + (8 if x < 0 else -8), y + (8 if y < 0 else -8)
                _box(P, cx - 8, cy - 8, -SINK, cx + 8, cy + 8, z - 14, 'dark', far=False)


def tower():
    """The model's description (see the module's docstring for the frame)."""
    P = []
    inner, outer = RING - WIDE / 2, RING + WIDE / 2
    run = RISE * battleship.LADDER_RUN
    # legs, up through the deck to the eaves
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(P, sx * LEG - 14, sy * LEG - 14, -SINK, sx * LEG + 14, sy * LEG + 14, ROOF, 'dark', far=True)
    # girts and X braces on each face, two bays
    bays = (0.0, DECK / 2, DECK - 40)
    for face in range(4):
        def at(t, z):
            u = -LEG + 2 * LEG * t
            return {0: (u, -LEG, z), 1: (LEG, u, z), 2: (-u, LEG, z), 3: (-LEG, -u, z)}[face]
        for z in bays[1:]:
            _beam(P, at(0, z), at(1, z), 12)
        for z0, z1 in zip(bays, bays[1:]):
            _beam(P, at(0, z0 + 20), at(1, z1 - 10), 9)
            _beam(P, at(1, z0 + 20), at(0, z1 - 10), 9)
    # the deck, its beams, its parapet (open on +y from its -x end to OPEN_TO)
    _box(P, -HALF, -HALF, DECK - 20, HALF, HALF, DECK, 'deck', far=True)
    for y in (-LEG, 0.0, LEG):
        _box(P, -HALF, y - 9, DECK - 46, HALF, y + 9, DECK - 20, 'dark', solid=False)
    t = 10.0
    _box(P, -HALF, -HALF, DECK, HALF, -HALF + t, DECK + PARAPET, 'boards', far=True)
    _box(P, OPEN_TO, HALF - t, DECK, HALF, HALF, DECK + PARAPET, 'boards', far=True)
    _box(P, HALF - t, -HALF + t, DECK, HALF, HALF - t, DECK + PARAPET, 'boards', far=True)
    _box(P, -HALF, -HALF + t, DECK, -HALF + t, HALF - t, DECK + PARAPET, 'boards', far=True)
    for a0, b0, a1, b1 in ((-HALF - 4, -HALF - 8, HALF + 4, -HALF + 8), (OPEN_TO, HALF - 8, HALF + 4, HALF + 8),
                           (HALF - 8, -HALF, HALF + 8, HALF), (-HALF - 8, -HALF, -HALF + 8, HALF - t)):      # (cap rails)
        _box(P, a0, b0, DECK + PARAPET, a1, b1, DECK + PARAPET + 6, 'dark', solid=False)
    # the roof: a low tin pyramid on the legs, its eaves out past the deck, plates under
    P.append({'shape': 'cone', 'r': (HALF + 60) * math.sqrt(2), 'h': 110, 'sides': 4, 'phase': 45, 'at': [0, 0, ROOF],
              'look': 'tin', 'under': True, 'solid': False, 'far': True, 'material': 'metal'})
    for sx in (-1, 1):
        _box(P, -LEG - 14, sx * LEG - 10, ROOF - 18, LEG + 14, sx * LEG + 10, ROOF, 'dark', solid=False)
        _box(P, sx * LEG - 10, -LEG - 14, ROOF - 18, sx * LEG + 10, LEG + 14, ROOF, 'dark', solid=False)
    # the stairs round the legs: one up the +x side (going -y) from the ground to L1 at the -x-y... corner (+x, -y), two
    # along -y (going -x) to L2 at (-x, -y), three up -x (going +y) to the top: T1 at (-x, +y) and a walk T2 along +y
    # to the deck's open side
    z1, z2 = RISE, 2 * RISE
    f1_foot = -inner + run + SINK * battleship.LADDER_RUN
    f2_top = inner - run
    f3_top = -inner + run
    _flight(P, RING, f1_foot, -SINK, -inner, z1, wide=WIDE)
    _flight(P, inner, -RING, z1, -RING, z2, wide=WIDE, x_top=f2_top)
    _flight(P, -RING, -inner, z2, f3_top, DECK, wide=WIDE)
    _landing(P, inner, -outer, outer, -inner, z1)                        # L1
    _landing(P, -outer, -outer, f2_top, -inner, z2)                      # L2 (the corner and on to flight two's top)
    _landing(P, -outer, f3_top, -inner, outer, DECK)                     # T1
    _landing(P, -inner, HALF - 5, OPEN_TO, outer, DECK, posts=True)      # T2, a little into the deck so they meet
    # rails along every fall
    for x, o in ((inner, (-1, 0)), (outer, (1, 0))):
        _rail(P, (x, f1_foot, -SINK), (x, -inner, z1), o)
    _rail(P, (outer, -outer, z1), (outer, -inner, z1), (1, 0))
    _rail(P, (inner, -outer, z1), (outer, -outer, z1), (0, -1))
    for y, o in ((-outer, (0, -1)), (-inner, (0, 1))):
        _rail(P, (inner, y, z1), (f2_top, y, z2), o)
    _rail(P, (-outer, -outer, z2), (f2_top, -outer, z2), (0, -1))
    _rail(P, (-outer, -outer, z2), (-outer, -inner, z2), (-1, 0))
    _rail(P, (-inner, -inner, z2), (f2_top, -inner, z2), (0, 1))
    for x, o in ((-outer, (-1, 0)), (-inner, (1, 0))):
        _rail(P, (x, -inner, z2), (x, f3_top, DECK), o)
    _rail(P, (-outer, f3_top, DECK), (-outer, outer, DECK), (-1, 0))
    _rail(P, (-outer, outer, DECK), (OPEN_TO, outer, DECK), (0, 1))
    _rail(P, (OPEN_TO, HALF, DECK), (OPEN_TO, outer, DECK), (1, 0))
    return {'name': 'FOLabGuardTower', 'looks': _looks(), 'parts': P}


modelsets.PIECES.setdefault(PIECE, {'label': 'Guard tower (for the NCR guard tower)', 'set': SET, 'file': PIECE,
                                    'describe': tower, 'edid': 'FOLabGuardTower'})
# (walkcheck: from the ground to the middle of the deck, by way of each landing)
WALK = {'voxel': VOXEL, 'goals': [('first landing', (RING, -RING, RISE)), ('second landing', (-RING, -RING, 2 * RISE)),
                                  ('top landing', (-RING, RING, DECK)), ('the deck', (0.0, 0.0, DECK))]}


# ---------- in a mod ----------

def _game_keys(gd):
    import shipinside
    found = shipinside._forms(gd, (GAME,) + GAME_PARTS)
    return {gd.key(f): e for e, f in found.items()}


def _same_spot(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1]) < 4.0 and abs(a[2] - b[2]) < 4.0


def instead(gd, pr, ops):
    """A builder's ops with FOLab's tower wherever they add the game's, and the game's parts at its spot left out (and
    any of them on their own: the tower has its stairs in it). The piece's files and record go first when the mod hasn't
    them yet. Other ops are as they were."""
    keys = _game_keys(gd)
    tower = [o for o in ops if o.get('op') == 'add' and keys.get(o.get('base')) == GAME]
    parts = [o for o in ops if o.get('op') == 'add' and keys.get(o.get('base')) in GAME_PARTS]
    if not tower and not parts:
        return ops
    put_ops, info = modelsets.put(pr, PIECE)
    key = info['key'] or '$model_' + PIECE
    out = list(put_ops)
    for o in ops:
        if o in parts:
            continue
        if o in tower:
            o = dict(o, base=key)
        out.append(o)
    return out


def found(gd, pr):
    """(towers [(cell, ref, ref's change)], parts [(cell, ref, change, editor ID)]) the mod stands of the game's."""
    keys = _game_keys(gd)
    towers, parts = [], []
    for ck, cell in pr.cells.items():
        for rk, r in (cell.get('refs') or {}).items():
            e = keys.get(r.get('base'))
            if e and not r.get('removed') and r.get('p'):
                (towers if e == GAME else parts).append((ck, rk, r) + (() if e == GAME else (e,)))
    return towers, parts


def swap_ops(gd, pr):
    """(ops, report) for one Undo: every game tower the mod stands becomes FOLab's (restyle's 'swap': the same ref, its
    place, turn, links and locks as they were) and every one of the game's parts at a tower's spot goes. report: 'towers',
    'parts', 'cells' (whose navmeshes were made round the game's tower: to make again), 'left' (parts with no tower)."""
    import restyle
    towers, parts = found(gd, pr)
    out, rep = [], {'towers': [], 'parts': 0, 'cells': [], 'left': []}
    if not towers:
        return out, rep
    put_ops, info = modelsets.put(pr, PIECE)
    out += put_ops
    key = info['key'] or '$model_' + PIECE
    for ck, rk, r in towers:
        out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': key})
        rep['towers'].append((ck, rk, [round(v, 1) for v in r['p'][:3]]))
        x, y, _z = r['p'][:3]
        for c in restyle._cells_round(gd, pr, ck, x, y, r['p'][5], info['box']):
            if c not in rep['cells']:
                rep['cells'].append(c)
    for ck, rk, r, _e in parts:
        if any(_same_spot(r['p'], t[2]['p']) for t in towers):
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            rep['parts'] += 1
        else:
            rep['left'].append((ck, rk, _e))
    return out, rep


# ---------- on ground a tower can stand on ----------

STEEP = 40.0            # (the ground under the footprint may vary this much: more, and a flight or landing is in the hill)
REACH = 2000.0          # (how far a tower may be moved to find such ground)
FOOT = 400.0            # (the footprint's half width, with its rails)
CLEAR = 60.0            # (a thing this small or smaller doesn't keep a tower off: plants, litter)


def _ground_range(ground, x, y, rz):
    c, s = math.cos(rz), math.sin(rz)
    hs = []
    for lx in (-FOOT, -FOOT / 2, 0.0, FOOT / 2, FOOT):
        for ly in (-FOOT, -FOOT / 2, 0.0, FOOT / 2, FOOT):
            h = ground.at(x + lx * c + ly * s, y - lx * s + ly * c)
            if h is None:
                return None
            hs.append(h)
    return min(hs), max(hs)


def resite(gd, pr, world, steep=STEEP, reach=REACH):
    """(ops, report) moving each of FOLab's towers whose ground varies more than `steep` across its footprint (a ridge
    builder seats it at the lowest point: up a slope its flights and landings were in the hill) to the nearest spot
    within `reach` where the ground is level enough, dry, and nothing bigger than CLEAR stands within its footprint;
    its turn kept, its foot on the lowest ground there. A move within its cell is a 'move'; into another, the ref is
    taken out and stood again there. report: 'moved' [(old cell, ref, from, to, how far)], 'kept', 'stuck', 'cells'."""
    import landmarks
    import navbuild
    import restyle
    import roadgen
    key = modelsets.record_of(pr, PIECE)
    out, rep = [], {'moved': [], 'kept': 0, 'stuck': [], 'cells': []}
    if key is None:
        return out, rep
    ground = roadgen.Ground(gd, pr, world)
    grid = gd.grid(world)
    mine = set(grid.values())
    towers = [(ck, rk, r) for ck, c in pr.cells.items() if not ck.startswith('+') and gd.from_key(ck) in mine
              for rk, r in (c.get('refs') or {}).items() if r.get('base') == key and not r.get('removed') and r.get('p')]
    things_near = _things(gd, pr, grid, key)

    for ck, rk, r in towers:
        x, y, z, _rx, _ry, rz = r['p'][:6]
        lo_hi = _ground_range(ground, x, y, rz)
        if lo_hi and lo_hi[1] - lo_hi[0] <= steep:
            rep['kept'] += 1
            continue
        best = None
        step = 64.0
        n = int(reach // step)
        spots = sorted(((i * step, j * step) for i in range(-n, n + 1) for j in range(-n, n + 1) if 0 < math.hypot(i, j) * step <= reach),
                       key=lambda d: math.hypot(*d))
        for dx, dy in spots:
            nx, ny = x + dx, y + dy
            lo_hi = _ground_range(ground, nx, ny, rz)
            if not lo_hi or lo_hi[1] - lo_hi[0] > steep or lo_hi[0] < 8.0:
                continue
            if any(math.hypot(nx - a, ny - b) < FOOT + 0.7 * rad for a, b, rad in things_near(nx, ny)
                   if math.hypot(x - a, y - b) > 1.0):
                continue
            best = (nx, ny, lo_hi[0])
            break
        if best is None:
            rep['stuck'].append((ck, rk, [round(v, 1) for v in r['p'][:3]]))
            continue
        nx, ny, nz = best
        p = [round(nx, 1), round(ny, 1), round(nz, 1)] + list(r['p'][3:6])
        cell = grid.get((int(math.floor(nx / 4096.0)), int(math.floor(ny / 4096.0))))
        nck = gd.key(cell)
        if nck == ck:
            out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': p})
        else:
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            out.append({'op': 'add', 'cell': nck, 'base': key, 'p': p, 's': r.get('s', 1.0)})
        rep['moved'].append((ck, rk, [round(v, 1) for v in r['p'][:3]], p[:3], round(math.hypot(nx - x, ny - y))))
        for c in [ck] + restyle._cells_round(gd, pr, nck, nx, ny, rz, (-FOOT, -FOOT, 0, FOOT, FOOT, 0)):
            if c not in rep['cells']:
                rep['cells'].append(c)
    return out, rep


def _things(gd, pr, grid, key):
    """things_near(x, y): [(x, y, radius)] of what stands in the 3 x 3 cells round x, y bigger than CLEAR, but towers."""
    import landmarks
    import navbuild
    box = {}

    def things_near(x, y):
        got = []
        cx, cy = int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = grid.get((cx + dx, cy + dy))
                if cell is None:
                    continue
                k = gd.key(cell)
                if k not in box:
                    box[k] = []
                    for row in navbuild.place_refs(gd, pr, k):
                        if row['bkey'] == key:
                            continue
                        if row['base'] is not None:
                            o = landmarks._obnd(gd, row['base'])
                        else:
                            rec = pr.records.get(row['bkey']) or {}
                            o = next(([f['value'] for f in s['fields']] for s in rec.get('subs', ()) if s.get('tag') == 'OBND'), None)
                        if not o:
                            continue
                        rad = max(o[3] - o[0], o[4] - o[1]) / 2.0 * (row.get('scale') or 1.0)
                        if rad > CLEAR:
                            box[k].append((row['pos'][0], row['pos'][1], rad))
                got += box[k]
        return got
    return things_near


PAD_MOVE = 900.0        # (a tower on a slope may move this far to flatter ground, clear of other things)
HOLD = 64.0             # (the pad reaches this far past the footprint)
EASE = 384.0            # (and is eased back to the slope over this)
PLANT_WORDS = ('grass', 'shrub', 'taro', 'fern', 'bush', 'hibiscus', 'plant', 'leaves', 'weed', 'agave', 'frailejon')
ON_GROUND = 80.0        # (a thing this near the old ground stood on it, and goes with it)
LEVEL_AT = 0.3          # (the pad's level: this share of its ground is under it. Banks built up read as plinths)
PAD_STEEP = 150.0       # (only towers on ground varying more than this are padded: up to it, the walk and navmesh hold)
MOVE_COST = 0.5         # (ground's unevenness traded for distance moved, unit for unit)


def pad(gd, pr, world, steep=PAD_STEEP, only=None, level_at=LEVEL_AT):
    """(ops, report) for one Undo: each of FOLab's towers on ground that varies more than `steep` across its footprint
    (the ridge builders seat it at the lowest point, so up a slope its flights and landings were in the hill; no level
    ground lies within REACH of the ridge forts) is moved, at most PAD_MOVE and its turn kept, to the flattest ground near,
    and the land under it made level at the middle of its ground there (HOLD past the footprint, eased back over EASE;
    road pieces' ground left), plants inside the footprint taken out, other things on moved ground moved with it.
    report: 'padded' [(cell, ref, from, to, cut, fill)], 'kept', 'land_cells', 'cells' (to navmesh again), 'plants_out',
    'carried'. only: the refs to look at (None: every tower); level_at: the share of the ground under the pad's level."""
    import land
    import recordio
    import restyle
    import roadbed
    import roadgen
    import tes4
    key = modelsets.record_of(pr, PIECE)
    out, rep = [], {'padded': [], 'kept': 0, 'land_cells': [], 'cells': [], 'plants_out': 0, 'carried': 0}
    if key is None:
        return out, rep
    grid = gd.grid(world)
    cell_of = {gd.key(c): xy for xy, c in grid.items()}
    ground = roadgen.Ground(gd, pr, world)
    towers = [(ck, rk, r) for ck, c in pr.cells.items() if ck in cell_of
              for rk, r in (c.get('refs') or {}).items() if r.get('base') == key and not r.get('removed') and r.get('p')
              and (only is None or rk in only)]
    heights, start = {}, {}                         # (cx, cy) -> 33 x 33 heights: changed, and as the mod has them now

    def cell_h(cx, cy):
        if (cx, cy) not in heights:
            cell = grid.get((cx, cy))
            h = None
            if cell is not None:
                mine = pr.land.get(gd.key(cell))
                if mine:
                    h = list(mine['h'])
                else:
                    e = gd.land_at(world, cx, cy)
                    vh = dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1]))).get('VHGT') if e else None
                    h = list(land.heights_of(vh)) if vh else None
            heights[(cx, cy)] = h
            start[(cx, cy)] = list(h) if h else None
        return heights[(cx, cy)]

    def set_point(gx, gy, v):
        """Land point (gx, gy) (128 apart) to v in every cell holding it (an edge point is in two, a corner in four)."""
        for cx in {gx // 32, (gx - 1) // 32}:
            for cy in {gy // 32, (gy - 1) // 32}:
                col, row = gx - cx * 32, gy - cy * 32
                if 0 <= col <= 32 and 0 <= row <= 32:
                    h = cell_h(cx, cy)
                    if h is not None:
                        h[row * 33 + col] = v

    def old_point(gx, gy):
        cx, cy = gx // 32, gy // 32
        cell_h(cx, cy)
        h = start.get((cx, cy))
        return h[(gy - cy * 32) * 33 + (gx - cx * 32)] if h else None

    def edid_of(b):
        try:
            if b.startswith('+'):
                rec = pr.records.get(b)
                return (recordio.field(rec, 'EDID') if rec else '') or ''
            return gd.edid(gd.from_key(b)) or ''
        except (KeyError, ValueError):
            return ''

    flat = roadbed._flat_bases(gd)
    held = set()
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            b, p = r.get('base'), r.get('p')
            if b in flat and p and not r.get('removed'):
                bx = flat[b]
                rad = math.hypot(max(abs(bx[0]), abs(bx[3])), max(abs(bx[1]), abs(bx[4]))) + 128
                for gy in range(int((p[1] - rad) // 128), int((p[1] + rad) // 128) + 2):
                    for gx in range(int((p[0] - rad) // 128), int((p[0] + rad) // 128) + 2):
                        held.add((gx, gy))
    things_near = _things(gd, pr, grid, key)
    carry = []                                      # (cell, ref, change, the ground under it before)
    seen = set()
    for ck, rk, r in towers:
        x, y, z, _rx, _ry, rz = r['p'][:6]
        lh = _ground_range(ground, x, y, rz)
        if lh and lh[1] - lh[0] <= steep:
            rep['kept'] += 1
            continue
        mid = ground.at(x, y)
        if mid is not None and z - mid > ON_GROUND:
            rep['kept'] += 1                    # (it stands on something, not the ground: the Flotilla's on its barges)
            continue
        # (the flattest ground near, a step's worth of it traded for every MOVE_COST units moved, with nothing but plants
        # in its footprint)
        best = (lh[1] - lh[0] if lh else 1e9, x, y)
        n = int(PAD_MOVE // 64)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                d = math.hypot(i, j) * 64
                if d > PAD_MOVE or d == 0:
                    continue
                qx, qy = x + i * 64, y + j * 64
                q = _ground_range(ground, qx, qy, rz)
                if not q or q[1] - q[0] + d * MOVE_COST >= best[0]:
                    continue
                if any(math.hypot(qx - a, qy - b) < FOOT + 0.7 * rad for a, b, rad in things_near(qx, qy) if math.hypot(x - a, y - b) > FOOT + 0.7 * rad):
                    continue
                best = (q[1] - q[0] + d * MOVE_COST, qx, qy)
        nx, ny = best[1], best[2]
        c, s = math.cos(rz), math.sin(rz)
        hs = sorted(ground.at(nx + lx * c + ly * s, ny - lx * s + ly * c) for lx in range(-400, 401, 100) for ly in range(-400, 401, 100))
        L = math.floor(hs[int(level_at * (len(hs) - 1))] / 8.0) * 8.0   # (low: cut into the hill, a terrace, not a mound)
        cut = fill = 0.0
        reach = FOOT + HOLD + EASE
        for gy in range(int((ny - reach * 1.5) // 128), int((ny + reach * 1.5) // 128) + 2):
            for gx in range(int((nx - reach * 1.5) // 128), int((nx + reach * 1.5) // 128) + 2):
                if (gx, gy) in held:
                    continue
                dx, dy = gx * 128.0 - nx, gy * 128.0 - ny
                lx, ly = dx * c - dy * s, dx * s + dy * c       # (into the tower's frame)
                d = max(abs(lx), abs(ly)) - FOOT
                if d > HOLD + EASE:
                    continue
                old = old_point(gx, gy)
                if old is None:
                    continue
                if d <= HOLD:
                    t = L
                else:
                    u = (d - HOLD) / EASE
                    u = u * u * (3 - 2 * u)
                    t = L + (old - L) * u
                t = round(t / 8.0) * 8.0
                if abs(t - old) >= 1:
                    set_point(gx, gy, t)
                    cut, fill = max(cut, old - t), max(fill, t - old)
        p = [round(nx, 1), round(ny, 1), L] + list(r['p'][3:6])
        nck = gd.key(grid[(int(math.floor(nx / 4096.0)), int(math.floor(ny / 4096.0)))])
        if nck == ck:
            out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': p})
        else:
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            out.append({'op': 'add', 'cell': nck, 'base': key, 'p': p, 's': r.get('s', 1.0)})
        rep['padded'].append((ck, rk, [round(v) for v in r['p'][:3]], [round(v) for v in p[:3]], round(cut), round(fill)))
        near = [ck] + restyle._cells_round(gd, pr, nck, nx, ny, rz, (-reach, -reach, 0, reach, reach, 0))
        for cc in near:
            if cc not in rep['cells']:
                rep['cells'].append(cc)
        # plants inside the footprint out; whatever stood on the moved ground goes with it
        for cc in near:
            for qk, q in ((pr.cells.get(cc) or {}).get('refs') or {}).items():
                qp = q.get('p')
                if (cc, qk) in seen or not qp or q.get('removed') or not q.get('base') or q.get('base') == key or q.get('tel'):
                    continue
                dx, dy = qp[0] - nx, qp[1] - ny
                lx, ly = dx * c - dy * s, dx * s + dy * c
                if max(abs(lx), abs(ly)) > reach:
                    continue
                seen.add((cc, qk))
                if max(abs(lx), abs(ly)) <= FOOT + 20 and any(w in edid_of(q['base']).lower() for w in PLANT_WORDS):
                    out.append({'op': 'remove', 'cell': cc, 'ref': qk})
                    rep['plants_out'] += 1
                    continue
                was = ground.at(qp[0], qp[1])
                if was is not None and abs(qp[2] - was) <= ON_GROUND:
                    carry.append((cc, qk, q, was))
    # the land, then the things carried by the ground's change under them
    for (cx, cy), h in sorted(heights.items()):
        if h and h != start[(cx, cy)]:
            k = gd.key(grid[(cx, cy)])
            form = dict(pr.land[k]) if pr.land.get(k) else land.decode(gd, gd.land_at(world, cx, cy), {})
            out.append({'op': 'land', 'cell': k, 'land': dict(form, h=[float(v) for v in h])})
            rep['land_cells'].append(k)
    after = _heights_ground(heights)
    for cc, qk, q, was in carry:
        now = after(q['p'][0], q['p'][1])
        if now is not None and abs(now - was) >= 2:
            out.append({'op': 'move', 'cell': cc, 'ref': qk, 'p': [q['p'][0], q['p'][1], round(q['p'][2] + now - was, 1)] + list(q['p'][3:])})
            rep['carried'] += 1
    return out, rep


def deck_reached(pr, ref_p, near=420.0):
    """{'L1', 'L2', 'deck'}: the heights of the tower standing at ref_p that the mod's navmeshes have a corner at."""
    x, y, z = ref_p[:3]
    got = set()
    for n in pr.navmesh.values():
        if not isinstance(n, dict) or not n.get('verts'):
            continue
        v = n['verts']
        pts = zip(v[0::3], v[1::3], v[2::3]) if not isinstance(v[0], (list, tuple)) else v
        for p in pts:
            if abs(p[0] - x) < near and abs(p[1] - y) < near and math.hypot(p[0] - x, p[1] - y) < near:
                for name, h in (('L1', RISE), ('L2', 2 * RISE), ('deck', DECK)):
                    if abs(p[2] - z - h) < 15:
                        got.add(name)
    return got


def _heights_ground(heights):
    """The ground at x, y from the cells' heights (bilinear over the 128-unit points), None outside them."""
    def at(x, y):
        cx, cy = int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0))
        h = heights.get((cx, cy))
        if not h:
            return None
        fx, fy = (x - cx * 4096.0) / 128.0, (y - cy * 4096.0) / 128.0
        i, j = min(31, int(fx)), min(31, int(fy))
        u, v = fx - i, fy - j
        a, b, c, d = h[j * 33 + i], h[j * 33 + i + 1], h[(j + 1) * 33 + i], h[(j + 1) * 33 + i + 1]
        return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v
    return at
