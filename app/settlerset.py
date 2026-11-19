"""The settlers' pieces (docs/waikiki-story-plan.md, "The settlers' land: built like old China"), FOLab's own
(modelsets: boxes, cylinders and a hull over pictures drawn in code, so a mod with them can be handed round):

Two hundred years of rebuilding what the first generation remembered of home, out of what the island gives:
- **Roofs** of corrugated iron and ship plating, bent into curved eaves that turn up at the corners (`roof`: each side
  three planes, steep at the ridge and flattening to the eave, a horn at each corner, the ridge's ends curled up).
- **Red** on posts, gates and doors, **gold** only on what matters most (the boards of the grander gates).
- **Walled courtyards**: `wall` lengths with a little roof on top, a `screen` wall inside each gate, `hall` houses
  facing the yard behind a porch of red posts.
- **A row of gates**, each grander than the last (`gate_1` to `gate_5`): one bay and iron roofs at first, three bays
  with red roofs and a gold board by the last.
- **The freighter** they came in (`freighter`): a small cargo ship run bow-first up the beach, her house aft, hatches
  forward, a ramp from her bow down to the sand. Her deck is walked on (the hull's own collision, as the Missouri's);
  her inside is closed until it's made as places of its own.

Front towards -y, standing on z 0, as every piece of modelsets."""
import math

import modelsets
import texpaint as tp
import texwear as tw
from modelsets import look

RED = (146, 42, 34)
GOLD = (192, 152, 64)
PLASTER = (204, 198, 184)
PLASTER_UNDER = (150, 144, 132)
IRON = (112, 106, 98)
IRON_RED = (128, 50, 40)
SET = 'settler'

modelsets.TEXTURES.update({
    'settler/roof_iron': lambda: tp.corrugated(IRON, seed=601, ridges=20),
    'settler/roof_red': lambda: tp.corrugated(IRON_RED, seed=602, ridges=20),
    'settler/red': lambda: tw.wood(RED, size=256, seed=603, count=4, paint_left=0.8),
    'settler/door': lambda: tw.wood(RED, size=256, seed=607, count=5, paint_left=0.9),
    'settler/plaster': lambda: tw.render(PLASTER, under=PLASTER_UNDER, size=512, seed=604, peel=0.3),
    'settler/gold': lambda: tp.painted_metal(GOLD, seed=605, rust=0.06),
    'settler/plate': lambda: tw.steel((98, 100, 98), size=256, seed=606, rust=0.5),
    'settler/stone': lambda: tp.lava_rock(seed=608),
    'settler/hull': lambda: tw.hull_rust(size=512, seed=610, paint=(64, 60, 56)),
    'settler/hull_red': lambda: tw.hull_rust(size=512, seed=611, paint=(112, 44, 36)),
    'settler/deck': lambda: tw.steel((84, 78, 70), size=256, seed=612, rust=0.6),
    'settler/house': lambda: tw.steel((192, 188, 176), size=256, seed=613, rust=0.35),
    'settler/dark': lambda: tp.painted_metal((40, 42, 44), seed=614, rust=0.2),
    'settler/hull_blue': lambda: tw.hull_rust(size=512, seed=618, paint=(50, 66, 84)),
    'settler/teal': lambda: tw.wood(TEAL, size=256, seed=615, count=3, paint_left=0.75),
    'settler/lattice': lambda: lattice(seed=616),
    'settler/tiles': lambda: tw.clay_tiles(size=512, seed=617, colour=(96, 92, 86)),
})

TEAL = (52, 104, 96)


def lattice(size=256, seed=616, cells=6):
    """A window of red-painted wooden lattice in a heavier frame, dark behind, the paint worn on the bars' edges."""
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 16)
    bar = size / cells
    frame = size * 0.07

    def fn(x, y):
        edge = min(x, y, size - 1 - x, size - 1 - y) < frame
        gx, gy = (x % bar) / bar, (y % bar) / bar
        on = edge or gx < 0.16 or gy < 0.16 or abs(gx - gy) < 0.07 or abs(gx + gy - 1) < 0.07
        if not on:
            return (22, 18, 16), 0.15
        wear = n.at(x * 16.0 / size, y * 16.0 / size)
        col = RED if wear < 0.66 else (118, 92, 70)
        return tuple(int(v * (0.85 + 0.2 * wear)) for v in col), 0.8 if edge else 0.65
    c.paint(fn)
    return c


def _looks():
    return {'iron': look('settler/roof_iron', tile=160), 'iron_red': look('settler/roof_red', tile=160),
            'red': look('settler/red', tile=96, turned=True), 'door': look('settler/door', tile=120),
            'plaster': look('settler/plaster', tile=320), 'gold': look('settler/gold', tile=64), 'plate': look('settler/plate', tile=160),
            'stone': look('settler/stone', tile=160), 'hull': look('settler/hull', tile=480), 'hull_red': look('settler/hull_red', tile=480), 'hull_blue': look('settler/hull_blue', tile=480),
            'deck': look('settler/deck', tile=200), 'house': look('settler/house', tile=200), 'dark': look('settler/dark', tile=96),
            'teal': look('settler/teal', tile=96, turned=True), 'lattice': look('settler/lattice'), 'tiles': look('settler/tiles', tile=200)}


def _box(P, size, at, lk, solid=True, turn=None, far=False, **faces):
    p = {'shape': 'box', 'size': [round(v, 1) for v in size], 'at': [round(v, 1) for v in at], 'look': lk, 'solid': solid, 'far': far,
         'material': 'metal' if lk in ('iron', 'iron_red', 'plate', 'hull', 'deck', 'house', 'dark') else ('stone' if lk in ('plaster', 'stone') else 'wood')}
    if turn:
        p['turn'] = [round(v, 3) for v in turn]
    if faces:
        p['faces'] = faces
    P.append(p)
    return p


def _post(P, x, y, h, r=20.0, lk='red', base=True):
    if base:
        _box(P, [r * 3.4, r * 3.4, 36], [x, y, 0], 'stone')
    P.append({'shape': 'cylinder', 'r': r, 'h': h - (36 if base else 0), 'sides': 10, 'at': [x, y, 36 if base else 0], 'look': lk,
              'solid': True, 'material': 'wood'})


PITCH = 0.62                    # (a roof's rise for its half-depth: about 32 degrees overall)
CURVE = 1.7                     # (steep at the ridge, flat at the eave: z falls as 1 - (1 - v) ** CURVE)
ROWS = (0.0, 0.12, 0.25, 0.38, 0.5, 0.62, 0.74, 0.86, 1.0)
ALONG = 15


def _profile(h, rise, v):
    return h * v, rise * (1 - (1 - v) ** CURVE)


def roof(P, W, D, z0, lk='iron', over=60.0, horn=150.0, solid=False, far=True, ends=True, board='red', gable=None):
    """A curved roof over a W (along x) by D (along y) rectangle whose eaves are at z0: each side one sheet, steep at
    the ridge and flattening to the eave, the eave sweeping up (by `horn`) and out towards the corners; a red board
    along the eaves, the ridge with its ends curled, the ends closed with `gable` (a look) under the roof if asked.
    Returns the ridge's height."""
    h = D / 2 + over
    rise = h * PITCH
    top = z0 + rise
    L = W + 2 * over
    xs = [-L / 2 + L * k / (ALONG - 1) for k in range(ALONG)]

    def point(x, v, sgn):
        u = abs(x) / (L / 2)
        sw = max(0.0, (u - 0.35) / 0.65) ** 2
        across, drop = _profile(h, rise, v)
        return (x, sgn * (across + 0.45 * horn * v * v * sw), top - drop + horn * v * v * sw)
    for sgn in (-1, 1):
        rows = [[point(x, v, sgn) for x in xs] for v in ROWS]
        P.append({'shape': 'sheet', 'rows': rows, 'look': lk, 'under_look': 'red' if board else lk, 'thick': 6.0, 'at': [0, 0, 0], 'far': far})
        if board:
            eave = [point(x, 1.0, sgn) for x in xs]
            P.append({'shape': 'sheet', 'rows': [eave, [(x, y, z - 26) for x, y, z in eave]], 'look': board, 'thick': 8.0, 'at': [0, 0, 0], 'far': False})
    if gable:
        for sx in (-1, 1):
            x = sx * (W / 2 - 4)
            prof = [(_profile(h - over, (h - over) * PITCH, v)) for v in ROWS]
            edge = [(x, -a, top - d) for a, d in reversed(prof)] + [(x, a, top - d) for a, d in prof[1:]]
            P.append({'shape': 'sheet', 'rows': [edge, [(x, y, z0 + 2) for x, y, _z in edge]], 'look': gable, 'thick': 10.0, 'at': [0, 0, 0], 'far': far})
    _box(P, [L + 30, 40, 38], [0, 0, top - 14], 'tiles' if lk == 'iron' else lk, solid=False, far=far)          # (the ridge)
    for sx in (-1, 1) if ends else ():
        _box(P, [70, 26, 22], [sx * (L / 2 + 16), 0, top + 10], lk, solid=False, far=far, turn=[0, sx * -30, 0])
        _box(P, [26, 26, 44], [sx * (L / 2 - 4), 0, top + 10], 'gold' if lk == 'iron_red' else lk, solid=False, far=far)
    return top


def brackets(P, x0, x1, y, z, step=60.0, lk='teal'):
    """A row of bracket sets under eaves: little blocks stepping out, every `step` along a beam at height z."""
    n = max(2, int((x1 - x0) / step))
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        _box(P, [24, 40, 18], [x, y, z], lk, solid=False)
        _box(P, [32, 60, 14], [x, y, z + 18], 'red', solid=False)


# ---------- the pieces ----------

def gate(n):
    """The n'th of the five gates on the road to the ship (1 the first, plainest)."""
    bays = 1 if n <= 2 else 3
    mid = [480, 560, 520, 600, 700][n - 1]
    side = [0, 0, 340, 380, 440][n - 1]
    H = [430, 480, 520, 580, 660][n - 1]
    r = [18, 20, 22, 24, 28][n - 1]
    roof_lk = 'iron' if n <= 3 else 'iron_red'
    P = []
    xs = [-mid / 2, mid / 2] + ([-mid / 2 - side, mid / 2 + side] if bays == 3 else [])
    for x in xs:
        _post(P, x, 0, H + 40, r=r)
    # beams: a lintel at the top, a second under it; the board between them in the middle bay
    span = mid + 2 * side + 2 * r + 30
    _box(P, [span, r * 1.8, r * 1.7], [0, 0, H - 22], 'teal', solid=False, front='teal', back='teal', bottom='red')
    _box(P, [mid + 2 * r, r * 1.5, r * 1.4], [0, 0, H - 132], 'teal', solid=False, bottom='red')
    for x in (-mid / 4, mid / 4):                                   # (little posts between the beams)
        _box(P, [12, r, 80], [x, 0, H - 112], 'red', solid=False)
    if n >= 3:
        _box(P, [mid * 0.42, 10, 84], [0, 0, H - 112], 'gold', solid=False)
        _box(P, [mid * 0.42 + 20, 12, 10], [0, 0, H - 30], 'red', solid=False)
    brackets(P, -mid / 2 - r, mid / 2 + r, 0, H + 8 - 22 + r * 1.7 - 10, step=48 + 4 * n)
    roof(P, mid + 2 * r, 230 + 30 * n, H + 18, roof_lk, over=50 + 6 * n, horn=60 + 8 * n)
    if bays == 3:
        for sx in (-1, 1):
            sub = []
            roof(sub, side + 2 * r, 200 + 24 * n, H - 64, roof_lk, over=36, horn=50 + 6 * n)
            for p in sub:
                p['at'][0] += sx * (mid / 2 + side / 2)
            P += sub
    return {'name': 'FOLabSettlerGate%d' % n, 'looks': _looks(), 'parts': P}


def wall(length=1000.0):
    """A courtyard wall: a stone footing, plaster, a little iron roof along its top."""
    P = []
    _box(P, [length, 70, 40], [0, 0, 0], 'stone')
    _box(P, [length, 46, 300], [0, 0, 40], 'plaster')
    roof(P, length - 48, 70, 340, 'iron', over=24, horn=0, ends=False)
    return {'name': 'FOLabSettlerWall', 'looks': _looks(), 'parts': P}


def screen():
    """The screen wall inside a gate, so no one sees straight into the yard: plaster in a red frame, a roof on top."""
    P = []
    _box(P, [520, 80, 40], [0, 0, 0], 'stone')
    _box(P, [480, 50, 280], [0, 0, 40], 'plaster')
    for sx in (-1, 1):
        _box(P, [30, 56, 280], [sx * 245, 0, 40], 'red', solid=False)
    _box(P, [520, 56, 26], [0, 0, 300], 'red', solid=False)
    roof(P, 520, 90, 326, 'iron', over=26, horn=30)
    return {'name': 'FOLabSettlerScreen', 'looks': _looks(), 'parts': P}


def hall(W=1100.0, D=640.0, Hw=340.0, red_roof=False):
    """A house facing its yard: a stone platform, plaster walls (closed: no inside yet), a porch of red posts along its
    front under the roof's sweep, a red double door."""
    P = []
    porch = 200.0
    _box(P, [W + 120, D + porch + 120, 40], [0, -porch / 2, 0], 'stone')
    _box(P, [W, D, Hw], [0, 0, 40], 'plaster')
    _box(P, [180, 8, 230], [0, -D / 2 - 4, 40], 'door', solid=False)
    _box(P, [10, 10, 230], [0, -D / 2 - 9, 40], 'gold', solid=False)
    _box(P, [260, 8, 60], [0, -D / 2 - 6, 290], 'gold', solid=False)
    for sx in (-1, 1):
        for k in (1, 2):
            _box(P, [170, 8, 130], [sx * (W / 2) * (k / 3.0) + sx * 60, -D / 2 - 4, 130], 'lattice', solid=False)
    _box(P, [W - 20, 10, 28], [0, -D / 2 - 6, 40 + Hw - 40], 'teal', solid=False)
    for k in range(2):                                              # (steps up to the porch)
        _box(P, [360, 70, 20 * (2 - k)], [0, -D / 2 - porch - 60 - 70 * (1 - k), 0], 'stone')
    for k in range(5):
        x = -W / 2 + k * W / 4
        _post(P, x, -D / 2 - porch, Hw, r=18, base=False)
    _box(P, [W + 40, 30, 30], [0, -D / 2 - porch, 40 + Hw - 30], 'red', solid=False)
    roof(P, W + 60, D + 2 * porch, 40 + Hw, 'iron_red' if red_roof else 'iron', over=70, horn=170, gable='plaster')
    return {'name': 'FOLabSettlerHall' + ('Red' if red_roof else ''), 'looks': _looks(), 'parts': P}


# ---------- the freighter ----------

F_LONG, F_HALF = 7700.0, 3850.0     # (110 m)
F_BEAM = 640.0                      # (half her beam)
F_DECK = 520.0                      # (her main deck over her keel's line... over the waterline as she floated)
F_KEEL = -330.0
F_STATIONS = [0, 0.01, 0.03, 0.06, 0.1, 0.15, 0.22, 0.3, 0.5, 0.7, 0.8, 0.88, 0.93, 0.97, 1.0]


def f_deck_z(s):
    return F_DECK                       # (flat: a sheer rising to the bow stood over any ramp from it)


def f_width(s):
    if s < 0.18:
        return F_BEAM * math.sin(s / 0.18 * math.pi / 2) ** 0.8
    if s > 0.9:
        return F_BEAM * (1 - 0.35 * ((s - 0.9) / 0.1) ** 2)
    return F_BEAM


def f_section(s):
    w, dz = f_width(s), f_deck_z(s)
    keel = F_KEEL if s < 0.92 else F_KEEL + 200.0 * ((s - 0.92) / 0.08)
    return [(round(w, 1), round(dz, 1)), (round(w, 1), 60.0), (round(w * 0.98, 1), -150.0), (round(w * 0.86, 1), -280.0),
            (round(w * 0.45, 1), round(keel, 1)), (0.0, round(keel, 1))]


def f_half_beam(y):
    return f_width(min(1.0, max(0.0, (y + F_HALF) / F_LONG)))


RAMP = (300.0, 2000.0)              # (the bow ramp: half its width, its length along her down to the sand)
RAMP_FOOT = F_KEEL + 90.0           # (the sand at her bow, in her frame: she is run up the beach to her keel)


FLOTILLA_SHIP = {'name': 'FOLabFlotillaShip', 'house': (-450.0, 350.0), 'hatches': (),
                 'ramp': False, 'gaps': ((-1150.0, 220.0), (850.0, 220.0)), 'bands': [(-1e9, 'hull_red'), (40.0, 'hull_blue')]}


def freighter(name='FOLabSettlerFreighter', house=(2250.0, 3050.0), hatches=(-2650.0, -1650.0, -650.0, 350.0, 1350.0), ramp=True,
              gaps=(), bands=None):
    """See the module's docstring. Her frame: middle at the origin, the waterline at z 0, the bow towards -y. The
    Flotilla's heart (FLOTILLA_SHIP) is the same hull with her house amidships, fewer hatches, red above her waterline,
    no ramp, and gaps (y, half its width) in her bulwarks where gangplanks come aboard."""
    P = [{'shape': 'hull', 'stations': [{'y': -F_HALF + s * F_LONG, 'pts': f_section(s)} for s in F_STATIONS],
          'bands': bands or [(-1e9, 'hull_red'), (40.0, 'hull')], 'deck_look': 'deck', 'end_look': 'hull', 'material': 'metal', 'far': True}]
    dz = F_DECK
    # the house: four levels, a bridge on top with a dark band of windows, the funnel behind
    y0, y1 = house
    for k in range(4):
        w = 1080.0 - 60.0 * k
        _box(P, [w, y1 - y0 - 40 * k, 250], [0, (y0 + y1) / 2 + 20 * k, dz + 250 * k], 'house', far=True)
        _box(P, [w + 4, 8, 70], [0, y0 + 20 * k - 4, dz + 250 * k + 140], 'dark', solid=False)
    _box(P, [1300, 300, 18], [0, y0 + 110, dz + 1000], 'house', far=True)                  # (the bridge wings' roof)
    P.append({'shape': 'cylinder', 'r': 150, 'h': 520, 'sides': 14, 'at': [0, y1 + 120, dz + 900], 'scale': [1.0, 1.5, 1.0],
              'look': 'dark', 'solid': False, 'material': 'metal', 'far': True})
    _box(P, [320, 460, 90], [0, y1 + 120, dz + 1330], 'hull_red', solid=False, far=True)
    # hatches forward, with masts between them
    for k, y in enumerate(hatches):
        _box(P, [820, 700, 110], [0, y, dz], 'plate', far=True)
        _box(P, [840, 720, 12], [0, y, dz + 110], 'deck', solid=False)
        if k in (1, 3):
            P.append({'shape': 'cylinder', 'r': 28, 'h': 1100, 'sides': 8, 'at': [0, y + 500, dz], 'look': 'dark', 'solid': True, 'material': 'metal', 'far': True})
            _box(P, [700, 24, 24], [0, y + 500, dz + 900], 'dark', solid=False, far=True)
    # bulwarks along her sides (a solid low wall: no one walks off her), open at the bow for the ramp
    for sx in (-1, 1):
        for k in range(len(F_STATIONS) - 1):
            s0, s1 = F_STATIONS[k], F_STATIONS[k + 1]
            if s1 <= (0.1 if ramp else 0.03):
                continue                        # (the bow open, where the ramp comes aboard)
            ya, yb = -F_HALF + s0 * F_LONG, -F_HALF + s1 * F_LONG
            xa, xb = f_width(s0), f_width(s1)
            mx, my = sx * (xa + xb) / 2, (ya + yb) / 2
            L = math.hypot(xb - xa, yb - ya)
            ang = math.degrees(math.atan2(sx * (xb - xa), yb - ya))
            # (cut where a gangplank comes aboard)
            spans = [(ya, yb)]
            for gy, gh in gaps:
                cut = []
                for a_, b_ in spans:
                    if a_ < gy + gh and b_ > gy - gh:
                        cut += [(a_, min(b_, gy - gh)), (max(a_, gy + gh), b_)]
                    else:
                        cut.append((a_, b_))
                spans = [q for q in cut if q[1] - q[0] > 20]
            for a_, b_ in spans:
                t0, t1 = (a_ - ya) / ((yb - ya) or 1), (b_ - ya) / ((yb - ya) or 1)
                cx_, cy_ = sx * (xa + (xb - xa) * (t0 + t1) / 2), (a_ + b_) / 2
                _box(P, [26, L * (t1 - t0) + 20, 110], [cx_ - sx * 13, cy_, f_deck_z((s0 + s1) / 2) - 4], 'hull', turn=[0, 0, -ang], far=True)
    if not ramp:
        return {'name': name, 'looks': _looks(), 'parts': P}
    # the ramp from the bow down to the sand she lies in (RAMP_FOOT in her frame), in three slabs
    half, long = RAMP
    # (a landing plate on the deck out over the tip of the bow, the ramp from its end)
    _box(P, [2 * half, 520, 14], [0, -F_HALF + 60.0, F_DECK - 10.0], 'plate')
    y_top = -F_HALF - 200.0
    z_top = F_DECK + 4.0
    drop = z_top - RAMP_FOOT
    a = math.degrees(math.atan2(drop, long))
    run = math.hypot(drop, long) / 3
    for k in range(3):
        t = (k + 0.5) / 3
        _box(P, [2 * half, run + 8, 16], [0, y_top - long * t, z_top - drop * t - 8], 'plate', turn=[a, 0, 0])
    for sx in (-1, 1):
        _box(P, [12, math.hypot(drop, long), 80], [sx * (half - 6), y_top - long / 2, z_top - drop / 2 - 8], 'dark', solid=False, turn=[a, 0, 0])
    return {'name': name, 'looks': _looks(), 'parts': P}


PIECES = {'settler_gate_%d' % n: ('Settlers\' gate %d' % n, (lambda n=n: gate(n))) for n in range(1, 6)}
PIECES.update({'settler_wall': ('Settlers\' courtyard wall', wall), 'settler_screen': ('Settlers\' screen wall', screen),
               'settler_hall': ('Settlers\' hall', hall), 'settler_hall_red': ('Settlers\' hall, red roof', lambda: hall(1300, 700, 380, True)),
               'settler_freighter': ('The settlers\' freighter', freighter),
               'settler_flotilla_ship': ('The Flotilla\'s ship', lambda: freighter(**FLOTILLA_SHIP))})
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k[8:], 'describe': _fn, 'edid': _fn()['name']})
