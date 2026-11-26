"""The An dynasty's grand palace on Mōkapu (the user, 25 Nov 2026: "5-6 stories tall ... something big and grand like that
for the imperial palace, surrounded by a wall and court"; "yes, go with the multi-eaved tower. Make them look good."):
FOLab's own pieces (modelsets: boxes, cylinders and curved sheets over pictures drawn in code), every part closed.

- **The tower** (`an_tower`): five storeys in the manner of the Yellow Crane Tower, each a little narrower than the one
  under it, a gallery of red columns round each, a railing round each floor above the first, and an eave skirt over each
  storey sweeping up at the corners on bracket sets; a hipped roof with a gilded finial over the top. On a terrace of
  white stone. The landmark, seen across the bay.
- **The throne hall** (`an_throne_hall`): the Hall of Supreme Peace [proposal: Taian Dian] on a three-tier terrace of
  white stone with balustrades, a stair up the middle of each tier; nine bays of red columns, a double-eaved hipped roof of
  yellow glazed tiles, the front open (lattice doors folded back) so the throne on its dais is seen and reached from the
  court: where you meet the Ship-King.
- **The gate tower** (`an_gate`): a tall red wall with a vaulted way through, a hall with a hipped roof standing on it.
- **The wall** (`an_wall`): a length of the compound's red wall on a stone footing, its top tiled.

Yellow glazed tiles are the emperor's, red lacquer on the columns, beams painted blue-green with gold, white stone for the
terraces. Front towards -y, standing on z 0, as every piece of modelsets. Walked: the terraces, stairs, the hall's floor,
the gate's way through (solid boxes and ramps; roofs and eaves are sheets, never walked)."""
import math

import modelsets
import texpaint as tp
import texwear as tw
from modelsets import look

SET = 'palace'
YELLOW = (226, 168, 34)
RED = (150, 36, 28)
WALL_RED = (142, 40, 32)
BEAM = (44, 104, 104)
BLUE = (40, 70, 120)
GOLD = (204, 164, 70)
MARBLE = (214, 210, 200)


def marble(size=256, seed=1201):
    """White stone in large blocks, a warm cast, fine grey veins and joints."""
    c = tp.Canvas(size, size)
    n, vein = tp.Noise(seed, 16), tp.Noise(seed + 1, 6)
    rows, across = 2, 2

    def fn(x, y):
        rh, cw = size / rows, size / across
        r = int(y // rh)
        xx = (x + (cw / 2 if r % 2 else 0)) % size
        edge = min(xx % cw, cw - xx % cw, y % rh, rh - y % rh)
        if edge < 1.5:
            return (150, 146, 138), 0.3
        v = vein.at(x * 6.0 / size, y * 6.0 / size)
        f = 0.94 + 0.08 * (n.at(x * 16.0 / size, y * 16.0 / size) - 0.5)
        if abs(v - 0.5) < 0.015:
            f *= 0.82
        return tuple(int(c_ * f) for c_ in MARBLE), 0.5
    c.paint(fn)
    return c


def beam_paint(size=256, seed=1202):
    """Beams painted in the old way: blue-green bands, a gold line along each edge, a gold-edged medallion every so often."""
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 32)

    def fn(x, y):
        v = y / size
        f = 0.92 + 0.12 * (n.at(x * 32.0 / size, y * 32.0 / size) - 0.5)
        if v < 0.06 or v > 0.94 or abs(v - 0.5) < 0.02:
            return tuple(int(c_ * f) for c_ in GOLD), 0.6
        u = (x % (size / 2)) / (size / 2)
        d = math.hypot(u - 0.5, (v - 0.5) * 1.4)
        if d < 0.2:
            return tuple(int(c_ * f) for c_ in (RED if d < 0.13 else GOLD)), 0.6
        col = BEAM if v < 0.5 else BLUE
        return tuple(int(c_ * f) for c_ in col), 0.55
    c.paint(fn)
    return c


def glazed_tiles(size=512, seed=1204, colour=YELLOW):
    """Glazed barrel tiles in rows, the emperor's yellow: each tile rounded with a bright glaze along its crown, the row
    ends' round caps darker, a thin shadow under each row's lip; kept, not broken."""
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 32)
    across, rows = 8, 8
    tw_, th = size / float(across), size / float(rows)

    def fn(x, y):
        j = int(y / th)
        v = (y % th) / th
        u = (x % tw_) / tw_
        r = math.sin(u * math.pi)
        f = 0.62 + 0.42 * r + 0.06 * (n.at(x * 32.0 / size, y * 32.0 / size) - 0.5)
        if abs(u - 0.5) < 0.08:
            f += 0.18 * (1 - v)                      # (the glaze catching the light along the crown)
        if v > 0.86:
            f *= 0.5                                 # (the shadow under the next row's lip)
        elif u < 0.06 or u > 0.94:
            f *= 0.55                                # (the gutter between two rows of tiles)
        return tuple(max(0, min(255, int(c_ * f))) for c_ in colour), 0.3 + 0.5 * r
    c.paint(fn)
    return c


def red_plaster(size=256, seed=1205):
    """The palace's red-washed plaster, kept: one deep red, a little lighter in soft patches, faint streaks down."""
    c = tp.Canvas(size, size)
    n, fine, rain = tp.Noise(seed, 6), tp.Noise(seed + 1, 48), tp.Noise(seed + 2, 24)

    def fn(x, y):
        f = 0.92 + 0.1 * (n.at(x * 6.0 / size, y * 6.0 / size) - 0.5) + 0.05 * (fine.at(x * 48.0 / size, y * 48.0 / size) - 0.5)
        f -= 0.04 * max(0.0, rain.at(x * 24.0 / size, y * 2.0 / size) - 0.6)
        return tuple(max(0, min(255, int(c_ * f))) for c_ in WALL_RED), 0.5
    c.paint(fn)
    return c


def lacquer_red(size=256, seed=1203):
    import huangset
    return huangset.lacquer(RED, size=size, seed=seed)


modelsets.TEXTURES.update({
    'palace/tiles': glazed_tiles,
    'palace/red': lacquer_red,
    'palace/wall': red_plaster,
    'palace/marble': marble,
    'palace/beam': beam_paint,
    'palace/gold': lambda: tp.painted_metal(GOLD, seed=1206, rust=0.02),
    'palace/lattice': lambda: __import__('settlerset').lattice(seed=1207),
    'palace/dark': lambda: tp.painted_metal((30, 26, 24), seed=1208, rust=0.0),
    'palace/bronze': lambda: tp.painted_metal((96, 78, 46), seed=1209, rust=0.25),
    'palace/stone': lambda: __import__('settlerset').dressed_stone(seed=1210),
})


def _looks():
    return {'tiles': look('palace/tiles', tile=260), 'red': look('palace/red', tile=96, turned=True), 'wall': look('palace/wall', tile=400),
            'marble': look('palace/marble', tile=200), 'beam': look('palace/beam', tile=256), 'gold': look('palace/gold', tile=64),
            'lattice': look('palace/lattice', tile=150), 'dark': look('palace/dark', tile=128), 'bronze': look('palace/bronze', tile=96),
            'stone': look('palace/stone', tile=160)}


MATERIAL = {'tiles': 'stone', 'marble': 'stone', 'wall': 'stone', 'gold': 'metal', 'dark': 'stone', 'bronze': 'metal', 'stone': 'stone'}


def _box(P, size, at, lk, solid=False, turn=None, sharp=False, **faces):
    p = {'shape': 'box', 'size': [round(v, 1) for v in size], 'at': [round(v, 1) for v in at], 'look': lk, 'solid': solid,
         'material': MATERIAL.get(lk, 'wood')}
    if sharp or min(size) < 30:                     # (small parts unrounded: the brackets and rails are thousands)
        p['bevel'] = 0
    if turn:
        p['turn'] = [round(v, 3) for v in turn]
    if faces:
        p['faces'] = faces
    P.append(p)
    return p


def _col(P, x, y, z, h, r=22.0, lk='red', solid=True):
    _box(P, [r * 3.2, r * 3.2, 26], [x, y, z], 'marble', solid=solid)
    P.append({'shape': 'cylinder', 'r': r, 'h': h - 26, 'sides': 10, 'bevel': 0, 'at': [x, y, z + 26], 'look': lk, 'solid': solid, 'material': 'wood'})


# ---------- roofs: four sheets mitred at the hips, curved, the corners swept up ----------
CURVE = 1.8
ROWS = (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.88, 1.0)
ALONG = 13


def _side(W, D, out, rise, horn, v, x_frac, ring=True):
    """A point of the -y side's sheet at row v (0 inner edge, 1 the eave) and x_frac (-1..1 along), for a W by D body.
    ring: an eave skirt from the body's wall (inner edge at the wall); else a hipped roof (inner edge a ridge of W - D)."""
    if ring:
        half_in, depth_in = W / 2, D / 2
    else:
        half_in, depth_in = max(0.0, (W - D) / 2), max(0.0, (D - W) / 2)      # (a long side runs to the ridge; an end to its end)
    a = (D / 2 + out - depth_in) * v                    # (how far out from the inner edge)
    hx = half_in + (W / 2 + out - half_in) * v          # (the mitre: the side grows as it comes out)
    x = x_frac * hx
    sw = max(0.0, (abs(x_frac) - 0.45) / 0.55) ** 2
    push = 0.5 * horn * v * v * sw
    z = -rise * (1 - (1 - v) ** CURVE) + horn * v * v * sw
    y = -(depth_in + a + push)
    return (x + math.copysign(push, x_frac) if x_frac else x, y, z)


def hip(P, W, D, z, out, rise, horn, ring=True, lk='tiles', under='beam', thick=10.0, ridge=True):
    """A hipped roof (ring False) or an eave skirt (ring True) over a W (x) by D (y) body, its inner edge at height z.
    Four sheets, two of them turned a quarter; returns the eave's height at the middle of a side."""
    for k, (w, d) in enumerate(((W, D), (D, W), (W, D), (D, W))):
        ang = math.radians(90 * k)
        ca, sa = math.cos(ang), math.sin(ang)
        rows = []
        for v in (ROWS if ring else (0.04,) + ROWS[1:]):      # (a hipped roof's sheets start just under the ridge: capped by it)
            row = []
            for j in range(ALONG):
                px, py, pz = _side(w, d, out, rise, horn, v, -1 + 2 * j / (ALONG - 1), ring)
                row.append((round(px * ca - py * sa, 1), round(px * sa + py * ca, 1), round(z + pz, 1)))
            rows.append(row)
        if k % 2:
            rows = [list(reversed(r)) for r in rows]
        P.append({'shape': 'sheet', 'rows': rows, 'look': lk, 'under_look': under, 'thick': thick, 'at': [0, 0, 0]})
        _hip_ridge(P, [r[0] for r in rows], lk)     # (the raised ridge down the hip at this sheet's start)
        edge = rows[-1][1:-1]                       # (the eave's red board, following the sweep, short of the hips)
        P.append({'shape': 'sheet', 'rows': [[(x, y_, z_ - thick) for x, y_, z_ in edge], [(x, y_, z_ - thick - 26) for x, y_, z_ in edge]],
                  'look': 'red', 'thick': 8.0, 'at': [0, 0, 0]})
    eave = z - rise
    if not ring and ridge:
        _box(P, [max(W - D, 0) + 90, 90 if W > D else max(W - D, 0) + 90, 50], [0, 0, z - 30], lk)      # (the ridge, or the apex's cap)
    return eave


def _hip_ridge(P, pts, lk, wide=34.0, high=26.0):
    """A ridge of tiles along a hip, short boxes from point to point down it, a little lifted, the last turned up."""
    for a, b in zip(pts, pts[1:]):
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        if L < 1:
            continue
        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2 - high / 2 + 4)
        _box(P, [L + 12, wide, high], mid, lk, turn=[0, -pitch, yaw], sharp=True)
    end = pts[-1]
    yaw = math.degrees(math.atan2(end[1], end[0]))
    _box(P, [60, wide - 6, 22], (end[0], end[1], end[2] + 8), 'gold', turn=[0, -35, yaw], sharp=True)


def brackets(P, W, D, z, step=110.0, lk='beam'):
    """Bracket sets under an eave all round a W by D body at height z: blocks stepping out under the eave."""
    for k in range(4):
        ang = 90 * k
        w = W if k % 2 == 0 else D
        d = D if k % 2 == 0 else W
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        n = max(2, int(w / step))
        for i in range(n + 1):
            x = -w / 2 + w * i / n
            for s, (sx, sy, sz, oy) in enumerate(((30, 34, 18, 10), (40, 58, 16, 26), (52, 80, 14, 42))):
                y = -(d / 2 + oy)
                _box(P, [sx, sy, sz], [x * ca - y * sa, x * sa + y * ca, z + s * 16], lk if s != 1 else 'red', turn=[0, 0, ang])


def railing(P, W, D, z, h=90.0, step=120.0, gap=None):
    """A red railing round a W by D floor at height z (a post every `step`, two rails, a gap at the front's middle if asked)."""
    for k in range(4):
        ang = 90 * k
        w = W if k % 2 == 0 else D
        d = D if k % 2 == 0 else W
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        y = -d / 2 + 6
        n = max(2, int(w / step))
        for i in range(n + 1):
            x = -w / 2 + w * i / n
            _box(P, [12, 12, h], [x * ca - y * sa, x * sa + y * ca, z], 'red', turn=[0, 0, ang])
        spans = [(-w / 2, w / 2)] if not (gap and k == 0) else [(-w / 2, -gap / 2), (gap / 2, w / 2)]
        for x0, x1 in spans:
            cx = (x0 + x1) / 2
            for zz, t in ((z + h - 12, 12), (z + 18, 8)):
                _box(P, [x1 - x0, 10, t], [cx * ca - y * sa, cx * sa + y * ca, zz], 'red' if t == 12 else 'beam', turn=[0, 0, ang])


def balustrade(P, W, D, z, h=70.0, step=170.0, gap=0.0, lk='marble'):
    """A white stone balustrade round a W by D terrace at height z, posts with round heads, a gap at the front for a stair."""
    for k in range(4):
        ang = 90 * k
        w = W if k % 2 == 0 else D
        d = D if k % 2 == 0 else W
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        y = -d / 2 + 14
        spans = [(-w / 2, w / 2)] if not (gap and k == 0) else [(-w / 2, -gap / 2), (gap / 2, w / 2)]
        for x0, x1 in spans:
            n = max(1, int((x1 - x0) / step))
            for i in range(n + 1):
                x = x0 + (x1 - x0) * i / n
                _box(P, [20, 20, h], [x * ca - y * sa, x * sa + y * ca, z], lk, turn=[0, 0, ang])
                P.append({'shape': 'ball', 'r': 12, 'sides': 6, 'rings': 3, 'at': [round(x * ca - y * sa, 1), round(x * sa + y * ca, 1), round(z + h, 1)], 'look': lk})
            cx = (x0 + x1) / 2
            _box(P, [x1 - x0, 14, 12], [cx * ca - y * sa, cx * sa + y * ca, z + h - 22], lk, turn=[0, 0, ang])
            _box(P, [x1 - x0, 10, 24], [cx * ca - y * sa, cx * sa + y * ca, z], lk, turn=[0, 0, ang])


def stair(P, w, z0, z1, y_top, run=None, lk='marble'):
    """Steps up the front (-y) from z0 to z1, the top at y_top: drawn steps over one solid ramp (people walk the ramp)."""
    rise = z1 - z0
    n = max(2, int(rise / 22))
    run = run or n * 34.0
    for i in range(n):
        h = rise * (i + 1) / n
        y = y_top - run + run * i / n
        _box(P, [w, run / n + 2, h], [0, y + run / n / 2, z0], lk)
    ang = math.degrees(math.atan2(rise, run))
    L = math.hypot(rise, run)
    P.append({'shape': 'box', 'size': [w, round(L, 1), 6], 'at': [0, round(y_top - run / 2, 1), round(z0 + rise / 2 - 6, 1)],
              'turn': [round(ang, 3), 0, 0], 'look': lk, 'solid': True, 'material': 'stone', 'hidden': True})
    for sx in (-1, 1):                                         # (the cheeks either side)
        _box(P, [24, run, rise + 10], [sx * (w / 2 + 12), y_top - run / 2, z0], lk)


def terrace(P, W, D, z0, h, gap):
    _box(P, [W, D, h], [0, 0, z0], 'marble', solid=True)
    balustrade(P, W, D, z0 + h, gap=gap)


# ---------- the pieces ----------
TOWER = [(1300, 560), (1180, 470), (1060, 440), (940, 420), (820, 400)]     # (each storey's width and height)


def tower():
    """Five storeys in the manner of the Yellow Crane Tower: each narrower, a gallery of red columns, an eave skirt on
    brackets over each, a railing round each floor above the first, a hipped roof with a gilded finial."""
    P = []
    base = 1900.0
    terrace(P, base, base, 0, 140, gap=420)
    stair(P, 400, 0, 140, -base / 2, run=300)
    z = 140.0
    for k, (w, h) in enumerate(TOWER):
        body = w - 160
        _box(P, [body, body, h], [0, 0, z], 'wall', solid=True, front='lattice', back='lattice', left='lattice', right='lattice')
        _box(P, [body + 10, body + 10, 40], [0, 0, z + h - 60], 'beam')
        n = 4 if k < 2 else 3
        for i in range(n + 1):
            off = -w / 2 + w * i / n
            for x, y in ((off, -w / 2), (off, w / 2), (-w / 2, off), (w / 2, off)):
                _col(P, x, y, z, h - 40, r=20 if k else 24)
        _box(P, [w + 40, w + 40, 30], [0, 0, z + h - 40], 'beam')
        if k:
            railing(P, w, w, z)
        _box(P, [w + 60, w + 60, 24], [0, 0, z - (24 if k else 0)], 'marble' if not k else 'red', solid=True)
        brackets(P, w, w, z + h - 96, step=130)
        top = z + h + 50
        if k < len(TOWER) - 1:
            nxt = TOWER[k + 1][0]
            hip(P, nxt + 80, nxt + 80, top + 30, out=(w - nxt) / 2 + 150, rise=150 + 10 * (4 - k), horn=110)
            z = top
        else:
            eave = hip(P, w + 40, w + 40, top + 520, out=320, rise=560, horn=150, ring=False)
            P.append({'shape': 'cylinder', 'r': 34, 'r2': 26, 'h': 90, 'sides': 10, 'at': [0, 0, top + 500], 'look': 'gold'})
            for r, zz in ((60, top + 590), (42, top + 690), (26, top + 770)):
                P.append({'shape': 'ball', 'r': r, 'sides': 10, 'rings': 6, 'at': [0, 0, zz], 'look': 'gold'})
            P.append({'shape': 'cylinder', 'r': 8, 'r2': 2, 'h': 120, 'sides': 8, 'at': [0, 0, top + 820], 'look': 'gold'})
    return _desc('FOLabAnTower', P)


def throne_hall():
    """The Hall of Supreme Peace on a three-tier terrace, nine bays of red columns, a double-eaved hipped roof, its front
    open to the throne on its dais."""
    P = []
    tiers = [(3640, 3500, 110), (3040, 2500, 110), (2440, 1500, 110)]     # (each a stair's run deeper than the next: stairs don't overlap)
    z = 0.0
    y_front = None
    for k, (w, d, h) in enumerate(tiers):
        terrace(P, w, d, z, h, gap=500)
        stair(P, 500, z, z + h, -d / 2, run=280)
        z += h
    W, D, H = 1900.0, 1100.0, 640.0
    _box(P, [W + 120, D + 120, 20], [0, 0, z], 'marble', solid=True)       # (the floor walked on)
    zf = z + 20
    # the back and the ends: walls; the front open between its columns, lattice doors folded back at each end bay
    _box(P, [W, 40, H], [0, D / 2 - 20, zf], 'wall', solid=True)
    for sx in (-1, 1):
        _box(P, [40, D - 40, H], [sx * (W / 2 - 20), 0, zf], 'wall', solid=True)
        _box(P, [180, 10, 420], [sx * (W / 2 - 150), -D / 2 + 30, zf], 'lattice', front='lattice', back='lattice')
    bays = 9
    for i in range(bays + 1):
        x = -W / 2 + W * i / bays
        _col(P, x, -D / 2, zf, H - 40, r=26)
        _col(P, x, D / 2 - 60, zf, H - 40, r=26)
    for x in (-W / 6, W / 6):
        for y in (-D / 6, D / 6):
            _col(P, x, y, zf, H - 40, r=28)
    _box(P, [W + 40, 36, 60], [0, -D / 2, zf + H - 80], 'beam')
    _box(P, [W + 40, D + 40, 40], [0, 0, zf + H - 40], 'beam')
    _box(P, [W - 60, D - 60, 30], [0, 0, zf + H - 20], 'dark')            # (the ceiling, coffered dark)
    # the throne on its dais at the back, a screen behind it
    _box(P, [600, 320, 60], [0, D / 2 - 260, zf], 'marble', solid=True)
    stair(P, 240, zf, zf + 60, D / 2 - 420, run=90)
    _box(P, [150, 110, 60], [0, D / 2 - 230, zf + 60], 'gold', solid=True)
    _box(P, [170, 26, 160], [0, D / 2 - 180, zf + 60], 'gold', solid=True)
    _box(P, [560, 30, 360], [0, D / 2 - 120, zf + 60], 'gold', front='beam')
    brackets(P, W, D, zf + H - 4, step=130)
    lower = zf + H + 40
    hip(P, W - 300, D - 300, lower + 160, out=420, rise=200, horn=110)
    _box(P, [W - 300, D - 300, 240], [0, 0, lower + 120], 'wall', solid=True, front='lattice', back='lattice')
    brackets(P, W - 300, D - 300, lower + 350, step=130)
    hip(P, W - 260, D - 520, lower + 900, out=400, rise=520, horn=150, ring=False)
    return _desc('FOLabAnThroneHall', P)


def gate(W=2000.0, D=700.0, H=620.0, way=420.0, way_h=420.0, hall=(1300.0, 480.0, 420.0), name='FOLabAnGate'):
    """The gate tower: a tall red wall with a vaulted way through, a hall standing on it under a hipped roof."""
    P = []
    for sx in (-1, 1):
        x0, x1 = sx * way / 2, sx * W / 2
        _box(P, [abs(x1 - x0), D, H], [(x0 + x1) / 2, 0, 0], 'wall', solid=True)
    _box(P, [way, D, H - way_h], [0, 0, way_h], 'wall', solid=True)
    _box(P, [way + 10, 10, 50], [0, -D / 2 - 4, way_h - 50], 'marble')
    _box(P, [W + 40, D + 40, 40], [0, 0, H], 'marble', solid=True)
    balustrade(P, W + 40, D + 40, H + 40, h=60)
    w, d, h = hall
    z = H + 40
    _box(P, [w - 100, d - 100, h], [0, 0, z], 'wall', solid=True, front='lattice', back='lattice')
    for i in range(6):
        x = -w / 2 + w * i / 5
        _col(P, x, -d / 2, z, h - 30)
        _col(P, x, d / 2, z, h - 30)
    _box(P, [w + 30, d + 30, 30], [0, 0, z + h - 30], 'beam')
    brackets(P, w, d, z + h, step=120)
    hip(P, w - 200, d - 160, z + h + 520, out=320, rise=440, horn=140, ring=False)
    _box(P, [420, 20, 120], [0, -d / 2 - 30, z + h - 160], 'gold')             # (the board with the gate's name)
    return _desc(name, P)


def inner_gate():
    """The gate in the wall between the outer and inner courts: the gate tower's shape, smaller, its wall the court wall's height."""
    return gate(W=1840.0, D=420.0, H=580.0, way=380.0, way_h=400.0, hall=(1100.0, 340.0, 340.0), name='FOLabAnInnerGate')


def corner():
    """A corner tower where two lengths of the wall meet: a square red block a little over the wall on a stone footing,
    a small hall on it under a hipped roof with a gilded finial (the walls' ends meet hidden inside it)."""
    P = []
    S, H = 640.0, 700.0
    _box(P, [S + 80, S + 80, 60], [0, 0, 0], 'marble', solid=True)
    _box(P, [S, S, H], [0, 0, 60], 'wall', solid=True)
    _box(P, [S + 40, S + 40, 30], [0, 0, 60 + H], 'marble', solid=True)
    w = S - 140
    z = 60 + H + 30
    _box(P, [w - 60, w - 60, 260], [0, 0, z], 'wall', solid=True, front='lattice', back='lattice', left='lattice', right='lattice')
    for sx in (-1, 1):
        for sy in (-1, 1):
            _col(P, sx * w / 2, sy * w / 2, z, 260, r=16)
    _box(P, [w + 20, w + 20, 24], [0, 0, z + 236], 'beam')
    brackets(P, w, w, z + 250, step=120)
    hip(P, w + 20, w + 20, z + 260 + 330, out=200, rise=340, horn=110, ring=False)
    P.append({'shape': 'ball', 'r': 24, 'sides': 8, 'rings': 5, 'at': [0, 0, z + 260 + 330 + 10], 'look': 'gold'})
    return _desc('FOLabAnCorner', P)


def side_hall():
    """A hall along the courts' sides (offices, the guards' hall): five bays of red columns on a low marble base, lattice
    fronts, a hipped roof."""
    P = []
    W, D, H = 1500.0, 700.0, 420.0
    _box(P, [W + 200, D + 200, 60], [0, 0, 0], 'marble', solid=True)
    stair(P, 300, 0, 60, -(D + 200) / 2, run=90)
    _box(P, [W - 80, D - 80, H], [0, 0, 60], 'wall', solid=True, front='lattice', back='lattice')
    for i in range(6):
        x = -W / 2 + W * i / 5
        _col(P, x, -D / 2, 60, H - 30, r=20)
        _col(P, x, D / 2, 60, H - 30, r=20)
    _box(P, [W + 30, D + 30, 30], [0, 0, 60 + H - 30], 'beam')
    brackets(P, W, D, 60 + H - 4, step=120)
    hip(P, W - 200, D - 260, 60 + H + 440, out=300, rise=400, horn=120, ring=False)
    return _desc('FOLabAnSideHall', P)


def cauldron():
    """A bronze cauldron on three legs, two loop handles, as stood before a throne hall."""
    P = []
    for k in range(3):
        a = math.radians(90 + 120 * k)
        P.append({'shape': 'cylinder', 'r': 9, 'r2': 7, 'h': 60, 'sides': 8, 'at': [round(52 * math.cos(a), 1), round(52 * math.sin(a), 1), 0],
                  'look': 'bronze', 'solid': False, 'bevel': 0})
    P.append({'shape': 'cylinder', 'r': 62, 'r2': 78, 'h': 70, 'sides': 16, 'at': [0, 0, 56], 'look': 'bronze', 'solid': True, 'bevel': 0, 'material': 'metal'})
    P.append({'shape': 'cylinder', 'r': 82, 'r2': 82, 'h': 10, 'sides': 16, 'at': [0, 0, 124], 'look': 'bronze', 'bevel': 0})
    for sx in (-1, 1):
        _box(P, [12, 14, 46], [sx * 58, 0, 130], 'bronze', sharp=True)
        _box(P, [12, 14, 12], [sx * 46, 0, 170], 'bronze', sharp=True)
    return _desc('FOLabAnCauldron', P)


def lion():
    """A stone guardian lion sitting on its plinth, facing out (-y): haunches, chest, a maned head, a paw on a ball."""
    P = []
    _box(P, [120, 170, 70], [0, 0, 0], 'stone', solid=True)
    _box(P, [130, 180, 14], [0, 0, 70], 'stone')
    z = 84
    P.append({'shape': 'ball', 'r': 46, 'sides': 10, 'rings': 6, 'at': [0, 34, z], 'scale': [1.1, 1.2, 0.9], 'look': 'stone'})
    P.append({'shape': 'ball', 'r': 36, 'sides': 10, 'rings': 6, 'at': [0, -8, z + 40], 'scale': [1.0, 0.9, 1.5], 'look': 'stone'})
    P.append({'shape': 'ball', 'r': 40, 'sides': 10, 'rings': 6, 'at': [0, -22, z + 120], 'scale': [1.1, 0.9, 1.0], 'look': 'stone'})
    P.append({'shape': 'ball', 'r': 24, 'sides': 10, 'rings': 6, 'at': [0, -54, z + 132], 'look': 'stone'})
    for sx in (-1, 1):
        P.append({'shape': 'cylinder', 'r': 12, 'r2': 11, 'h': 62, 'sides': 8, 'at': [sx * 20, -40, z], 'look': 'stone', 'bevel': 0})
        P.append({'shape': 'ball', 'r': 9, 'sides': 8, 'rings': 4, 'at': [sx * 24, -48, z + 168], 'look': 'stone'})
    P.append({'shape': 'ball', 'r': 20, 'sides': 10, 'rings': 5, 'at': [-34, -48, z], 'look': 'stone'})
    return _desc('FOLabAnLion', P)


def wall():
    """A 2,048 length of the red wall, on a stone footing, its top tiled both ways."""
    P = []
    L, T, H = 2048.0, 160.0, 520.0
    _box(P, [L, T + 60, 60], [0, 0, 0], 'marble', solid=True)
    _box(P, [L, T, H], [0, 0, 60], 'wall', solid=True)
    _box(P, [L + 4, T + 20, 26], [0, 0, 60 + H], 'beam')
    hip(P, L, 40, 60 + H + 110, out=90, rise=100, horn=0, ring=False, ridge=True)
    return _desc('FOLabAnWall', P)


def _desc(name, P, **more):
    d = {'name': name, 'looks': _looks(), 'parts': P}
    d.update(more)
    return d


PIECES = {'an_tower': ('The An dynasty\'s tower', tower), 'an_throne_hall': ('The Hall of Supreme Peace', throne_hall),
          'an_gate': ('The palace gate', gate), 'an_wall': ('The palace wall', wall), 'an_inner_gate': ('The palace\'s inner gate', inner_gate),
          'an_side_hall': ('A palace side hall', side_hall), 'an_cauldron': ('A bronze cauldron', cauldron), 'an_lion': ('A stone guardian lion', lion),
          'an_corner': ('A palace corner tower', corner)}
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k[3:], 'describe': _fn, 'edid': _fn()['name'],
                                     'no_far': _k in ('an_cauldron', 'an_lion')})
