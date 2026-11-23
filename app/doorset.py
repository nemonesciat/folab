"""FOLab's own doors for Waikiki's buildings, each made to its building's doorway (set 'doors' of modelsets).

The survey (21 Nov 2026, docs/waikiki-doors.md) measured every door Waikiki stands outside against the hole in its
building's mesh. Most of the game's doors hang flat on a solid wall, as the game hangs them; the misfits were the hotels
(a shop-front pair 216 x 174 in the Royal Hawaiian's 296 x 320 arched bay, wider than the Moana's 152-wide bay, standing
free of the Kilauea's glass), the homes whose doorway is a real hole (an office door 128 x 176 behind the NoVac house's
88 x 144 frame, Goodsprings and Usonian homes with gaps round theirs), and the bungalows' office-hotel door. The hotels'
lift doors are the game's HotelElevatorDoor01/02: a panel two units deep with one face, which the user didn't see in game.

A door here is a unit: what lines the hole (`liner`), the leaf or leaves, a transom or a fanlight, a casing on the wall
where the building has none of its own, one convex box of collision over the doorway (static layer, as the game's
unanimated load doors have: DoorStorefrontDbl01, WoodShackDoorALT). Its frame: origin at the bottom middle of the
opening on the wall's outer face, -y out of the building, so a door is stood by its building's transform (`DOORWAYS`,
measured in the building's frame) and every copy of a building gets the same fit. A lift door keeps the game's own frame
(origin 80 over the floor, the room at -y, its face y 2 out from the origin): it is drawn on both sides and swapped by
its base alone.

The leaf pictures are painted here (`TEXTURES`): koa and glass for the Royal Hawaiian, white sashes for the Moana, gold
and glass for the Kilauea, painted cottage doors for the homes, bronze lift doors. Records are DOORs copied from the
game door each replaces (its sounds), with this model (`door_record`). `doorswap.py` stands them."""
import math
import random

import modelsets
import texpaint as tp
from modelsets import look

SET = 'doors'

KOA = (112, 66, 38)
WHITE = (226, 222, 208)
GOLD = (196, 160, 72)
BRONZE = (120, 92, 58)
GLASS = (34, 52, 58)


# ---------- the pictures ----------

def _rects_painter(w, h, base, rects, seed, wear=0.18, grain=True, dirt=0.25):
    """A picture from rectangles over a ground: rects [(x0, y0, x1, y1, kind, colour)] in 0-1 of the picture, later
    over earlier. Kinds: 'panel' (sunk, its edge bevelled), 'glass' (dark, a sheen across), 'bar' (raised), 'knob'
    (a round boss in the rectangle), 'flat'. Paint wears to bare wood at the edges and the foot."""
    c = tp.Canvas(w, h)
    big, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 64)
    px = [(int(a * w), int(b * h), int(math.ceil(cc * w)), int(math.ceil(d * h)), k, col) for a, b, cc, d, k, col in rects]

    def fn(x, y):
        g = fine.at(x * 64.0 / w * 2, y * 64.0 / h / 5) if grain else 0.5
        col = tuple(v * (0.92 + 0.14 * g) for v in base)
        ht = 0.55 + 0.03 * g
        top = None
        for x0, y0, x1, y1, k, kc in px:
            if not (x0 <= x < x1 and y0 <= y < y1):
                continue
            top = k
            e = min(x - x0, x1 - 1 - x, y - y0, y1 - 1 - y)
            if k == 'panel':
                col = tuple(v * (0.9 + 0.12 * g) for v in kc)
                ht = 0.44
                if e < 3:
                    col = tuple(v * (0.72 if (x - x0 < 3 or y - y0 < 3) else 1.12) for v in col)
                    ht = 0.5 - 0.02 * e
            elif k == 'glass':
                t = (x - x0 + (y - y0) * 0.6) / max(1.0, (x1 - x0) + (y1 - y0) * 0.6)
                sheen = max(0.0, 1.0 - abs(t - 0.62) * 9.0)
                col = tuple(v * (0.8 + 0.5 * (y1 - y) / max(1.0, y1 - y0)) + 90 * sheen for v in kc)
                ht = 0.4
            elif k == 'bar':
                col = tuple(v * (0.95 + 0.1 * g) for v in kc)
                ht = 0.62
                if e < 2:
                    col = tuple(v * 0.8 for v in col)
            elif k == 'knob':
                cx, cy, r = (x0 + x1) / 2.0, (y0 + y1) / 2.0, min(x1 - x0, y1 - y0) / 2.0
                d = math.hypot(x - cx, y - cy)
                if d <= r:
                    col = tuple(min(255.0, v * (1.25 - 0.5 * d / r)) for v in kc)
                    ht = 0.7 - 0.1 * d / r
            else:
                col = kc
        foot = max(0.0, (y / float(h)) - 0.8) * 5.0
        patch = big.at(x * 8.0 / w, y * 8.0 / h) + (g - 0.5) * 0.4
        if wear and top not in ('glass', 'knob') and patch > 1.0 - wear * (1 + foot):     # (paint wears, glass and brass don't)
            col = tuple(v * (0.75 + 0.4 * g) for v in tp.BARE_WOOD)
            ht -= 0.04
        if dirt:
            col = tuple(v * (1.0 - dirt * foot * 0.6) for v in col)
        return tuple(max(0.0, min(255.0, v)) for v in col), ht
    c.paint(fn)
    return c


def leaf_glazed(colour, rows=3, cols=2, glass_to=0.55, seed=200, wear=0.15, knob=True, w=128, h=256):
    """A door with its upper part glazed in rows x cols lights, two sunk panels under, a knob on the right."""
    S, R = 0.13, 0.06                        # stile, rail (of the picture)
    rects = []
    gx0, gx1, gy0, gy1 = S, 1 - S, R, glass_to
    mw, mh = (gx1 - gx0) / cols, (gy1 - gy0) / rows
    rects.append((gx0, gy0, gx1, gy1, 'bar', colour))
    for i in range(cols):
        for j in range(rows):
            rects.append((gx0 + i * mw + 0.012, gy0 + j * mh + 0.008, gx0 + (i + 1) * mw - 0.012, gy0 + (j + 1) * mh - 0.008, 'glass', GLASS))
    lock = 0.58
    rects.append((S, glass_to + 0.05, 1 - S, lock - 0.0 if lock > glass_to + 0.1 else glass_to + 0.1, 'panel', colour))
    rects.append((S, max(lock + 0.04, glass_to + 0.12), 0.5 - 0.03, 1 - R * 1.4, 'panel', colour))
    rects.append((0.5 + 0.03, max(lock + 0.04, glass_to + 0.12), 1 - S, 1 - R * 1.4, 'panel', colour))
    if knob:
        rects.append((0.8, 0.52, 0.92, 0.58, 'knob', (200, 168, 96)))
    return _rects_painter(w, h, colour, rects, seed, wear)


def leaf_panels(colour, seed=210, wear=0.2):
    """A four-panel cottage door, a small window of four lights high up, a knob."""
    S, R = 0.14, 0.06
    rects = [(S, R, 1 - S, 0.3, 'bar', colour)]
    for i in range(2):
        for j in range(2):
            rects.append((S + 0.02 + i * 0.35, R + 0.02 + j * 0.11, S + (i + 1) * 0.35 - 0.02, R + (j + 1) * 0.11 - 0.01, 'glass', GLASS))
    rects += [(S, 0.36, 0.48, 0.62, 'panel', colour), (0.52, 0.36, 1 - S, 0.62, 'panel', colour),
              (S, 0.68, 0.48, 1 - R * 1.3, 'panel', colour), (0.52, 0.68, 1 - S, 1 - R * 1.3, 'panel', colour),
              (0.8, 0.6, 0.92, 0.66, 'knob', (200, 168, 96))]
    return _rects_painter(128, 256, colour, rects, seed, wear)


def storefront(seed=220):
    """The Kilauea's door: a gold frame round one sheet of glass, a push bar across."""
    rects = [(0.09, 0.05, 0.91, 0.93, 'glass', (30, 46, 54)), (0.06, 0.5, 0.94, 0.545, 'bar', (214, 180, 90))]
    return _rects_painter(128, 256, GOLD, rects, seed, wear=0.0, grain=False, dirt=0.12)


def fanlight(colour, seed=230):
    """Glass in a fan of bars: the Royal Hawaiian's arch over its doors."""
    c = tp.Canvas(256, 128)
    fine = tp.Noise(seed, 64)

    def fn(x, y):
        dx, dy = (x - 128) / 128.0, (128 - y) / 128.0
        r = math.hypot(dx, dy)
        a = math.degrees(math.atan2(dy, dx))
        bar = min(abs(((a + 11.25) % 22.5) - 11.25) * r * 3.0, abs(r - 0.42) * 60, abs(r - 0.9) * 60, y > 122 and 1 or 9)
        if bar < 1.6 or y > 122:
            g = fine.at(x / 4.0, y / 4.0)
            return tuple(v * (0.9 + 0.15 * g) for v in colour), 0.62
        sheen = max(0.0, 1.0 - abs(dx * 0.7 + dy * 0.3 - 0.25) * 6)
        return tuple(v * (0.8 + 0.4 * dy) + 80 * sheen for v in GLASS), 0.4
    c.paint(fn)
    return c


def transom(colour, panes=3, seed=240):
    rects = [(0.03 + k * 0.94 / panes + 0.01, 0.14, 0.03 + (k + 1) * 0.94 / panes - 0.01, 0.86, 'glass', GLASS) for k in range(panes)]
    return _rects_painter(256, 64, colour, rects, seed, wear=0.08, grain=False, dirt=0)


def lift(seed=250):
    """Two bronze leaves meeting in the middle, brushed, a little floor dial over them in the frame."""
    c = tp.Canvas(256, 256)
    fine = tp.Noise(seed, 64)
    big = tp.Noise(seed + 1, 8)

    def fn(x, y):
        g = fine.at(x / 2.0, y * 64.0 / 256 / 8)
        col = tuple(v * (0.85 + 0.3 * g) for v in BRONZE)
        ht = 0.55
        if abs(x - 128) < 2:
            return (24, 20, 16), 0.3                      # the seam
        for x0 in (14, 142):
            if x0 <= x < x0 + 100 and 20 <= y < 236:      # a sunk field on each leaf
                e = min(x - x0, x0 + 99 - x, y - 20, 235 - y)
                col = tuple(v * (0.94 if e > 2 else 0.78) for v in col)
                ht = 0.5
        if big.at(x / 32.0, y / 32.0) > 0.78:
            col = tuple(v * 0.7 for v in col)              # (tarnish)
        return tuple(min(255.0, v) for v in col), ht
    c.paint(fn)
    return c


def trim(colour, seed=260, wear=0.12):
    return _rects_painter(64, 256, colour, [], seed, wear, dirt=0.1)


PAINT = {'turquoise': tp.TURQUOISE, 'coral': tp.CORAL, 'cream': tp.CREAM, 'yellow': tp.YELLOW, 'seafoam': tp.SEAFOAM, 'teal': (52, 120, 118)}

TEXTURES = {
    'doors/koa_glazed': lambda: leaf_glazed(KOA, rows=4, cols=2, glass_to=0.62, seed=201, wear=0.1),
    'doors/koa_fan': lambda: fanlight(KOA),
    'doors/white_sash': lambda: leaf_glazed(WHITE, rows=4, cols=3, glass_to=0.6, seed=202, wear=0.12),
    'doors/white_transom': lambda: transom(WHITE),
    'doors/gold_glass': storefront,
    'doors/gold_transom': lambda: transom(GOLD, panes=4, seed=241),
    'doors/lift': lift,
    'doors/trim_koa': lambda: trim(KOA, seed=261, wear=0.04),
    'doors/trim_white': lambda: trim(WHITE, seed=262),
    'doors/trim_gold': lambda: trim(GOLD, seed=263, wear=0.0),
    'doors/trim_bronze': lambda: trim(BRONZE, seed=264, wear=0.0),
}
for _name, _col in PAINT.items():
    TEXTURES['doors/home_' + _name] = (lambda c, s: lambda: leaf_panels(c, seed=s))(_col, 270 + len(TEXTURES))
    TEXTURES['doors/glazed_' + _name] = (lambda c, s: lambda: leaf_glazed(c, seed=s, wear=0.22))(_col, 300 + len(TEXTURES))
modelsets.TEXTURES.update(TEXTURES)


# ---------- the units ----------

NONE = {f: None for f in ('front', 'back', 'left', 'right', 'top', 'bottom')}      # (a box nothing draws: collision only)


def _box(P, size, at, look_name, solid=False, **faces):
    p = {'shape': 'box', 'size': [float(v) for v in size], 'at': [float(v) for v in at], 'look': look_name, 'solid': solid, 'material': 'wood'}
    if faces:
        p['faces'] = faces
    P.append(p)


def unit(name, W, H, leaf, trim_look, leaves=1, depth=16.0, liner=8.0, casing=0.0, top=0.0, top_look=None, fan=0.0, fan_look=None,
         flush=False, side=0.0, side_look=None):
    """A door made to a doorway W wide and H high (see the module's docstring for its frame). leaf: the leaves' look;
    leaves: 1 or 2 (a pair meets in the middle); depth: the wall's thickness the liners line; casing: a trim this wide
    on the wall's face round it (0: the building has its own); top: a transom this high inside the opening over the
    leaves; fan: a fanlight this high over the opening, set in the wall's middle (an arch shows it); flush: no hole, the
    door hung on the wall, its back on the face; side: lights this wide either side of the leaves (a storefront)."""
    P = []
    looks = {'leaf': look(leaf), 'trim': look(trim_look, tile=128)}
    if top_look:
        looks['top'] = look(top_look)
    if fan_look:
        looks['fan'] = look(fan_look)
    if side_look:
        looks['side'] = look(side_look)
    if leaves == 2:
        looks['leaf_r'] = look(leaf, region=(1.0, 0.0, 0.0, 1.0))      # (the other leaf of a pair the picture's mirror)
    if flush:
        t = 5.0
        lw = (W - 2 * side) / leaves
        for k in range(leaves):
            x = -W / 2.0 + side + lw * (k + 0.5)
            lk = 'leaf_r' if leaves == 2 and k == 1 else 'leaf'
            _box(P, [lw - 1, t, H - top], [x, -t / 2.0 + 0.5, 0], lk, back=None, left='trim', right='trim', top='trim', bottom=None, front=lk)
        if top:
            _box(P, [W - 2 * side, t, top], [0, -t / 2.0 + 0.5, H - top], 'top', front='top', back=None, left='trim', right='trim', top='trim', bottom=None)
        if casing:
            c = casing
            for sx in (-1, 1):
                _box(P, [c, 8, H + c], [sx * (W + c) / 2.0, -3.5, 0], 'trim', back=None, bottom=None)
            _box(P, [W + 2 * c, 8, c], [0, -3.5, H], 'trim', back=None)
            _box(P, [W + 2 * c + 16, 26, 5], [0, -12.0, 0], 'trim', back=None)      # (the step)
        _box(P, [W + 2 * casing, 8, H + casing], [0, -3.5, 0], None, solid=True, **NONE)      # (collision alone: no look, so nothing draws it)
    else:
        d = depth
        L = liner
        for sx in (-1, 1):
            _box(P, [L, d + 2, H], [sx * (W / 2.0 - L / 2.0), d / 2.0, 0], 'trim', front='trim', back=None, bottom=None)
        _box(P, [W, d + 2, L], [0, d / 2.0, H - L], 'trim', back=None)
        _box(P, [W, d + 10, 3], [0, d / 2.0 - 4, 0], 'trim', back=None)          # (the threshold)
        inner = W - 2 * L
        lh = H - L - 3 - top
        # (the leaves in front of the wall's outer face, not in the hole: nv-rs picks a door by its drawn triangles and a
        # building by its collision, the nearer wins, and the game's buildings close their doorways in collision at the
        # face (NoVacHouse01/02 at y 0, NVGoodSprhome02 at -5.8). In the hole at y 3.5-8.5 only the liners took the
        # crosshair, 23 Nov 2026. doorpick checks it; a placement whose wall stands further out is moved out by the step)
        ly = LEAF_Y
        lw = (inner - 2 * side) / leaves
        for k in range(leaves):
            x = -inner / 2.0 + side + lw * (k + 0.5)
            lk = 'leaf_r' if leaves == 2 and k == 1 else 'leaf'
            _box(P, [lw - 1, 5, lh], [x, ly, 3], lk, front=lk, back=lk, left='trim', right='trim', top='trim', bottom=None)
        if side:
            for sx in (-1, 1):
                _box(P, [side, 4, lh], [sx * (inner / 2.0 - side / 2.0), ly, 3], 'side', front='side', back='side', left='trim', right='trim', top='trim', bottom=None)
        if top:
            _box(P, [inner, 4, top], [0, ly, 3 + lh], 'top', front='top', back='top', left=None, right=None, top=None, bottom='trim')
        if fan:
            _box(P, [W, 3, fan], [0, d / 2.0, H], 'fan', front='fan', back='fan', left=None, right=None, top=None, bottom=None)
        if casing:
            c = casing
            for sx in (-1, 1):
                _box(P, [c, 5, H + c], [sx * (W / 2.0 + c / 2.0 - 2), -2.0, 0], 'trim', back=None, bottom=None)
            _box(P, [W + 2 * c - 4, 5, c], [0, -2.0, H - 2], 'trim', back=None)
        back = max(8.0, d)
        front = -(LEAF_Y - 2.5)                     # (the box from the leaves' front to the wall's back)
        _box(P, [W, back + front, H], [0, (back - front) / 2.0, 0], None, solid=True, **NONE)
    return {'name': name, 'looks': looks, 'parts': P, 'ground': True}


LEAF_Y = -3.5           # (a hole door's leaves' middle: 5 thick, so their front 6 in front of the wall's face)


def lift_door(name, W, H, low, frame=18.0):
    """A lift's doors in the game's lift-door frame (origin `low` over the floor, the room at -y): two bronze leaves in
    one box drawn on both sides, y 1 to 9, and (frame > 0) a bronze surround standing 3 out into the room."""
    P = []
    looks = {'lift': look('doors/lift'), 'trim': look('doors/trim_bronze', tile=128)}
    _box(P, [W, 8, H], [0, 5, -low], 'lift', solid=True, front='lift', back='lift', left='trim', right='trim', top='trim', bottom=None)
    if frame:
        f = frame
        for sx in (-1, 1):
            _box(P, [f, 14, H + f], [sx * (W + f) / 2.0, 4, -low], 'trim', bottom=None)
        _box(P, [W + 2 * f, 14, f], [0, 4, H - low], 'trim')
        # (the floor dial over the doors: a half disc of bronze)
        P.append({'shape': 'cylinder', 'r': 22, 'h': 4, 'sides': 12, 'turn': [90, 0, 0], 'at': [0, -2, H - low + f + 4], 'look': 'trim', 'solid': False})
    return {'name': name, 'looks': looks, 'parts': P, 'ground': False}


# ---------- the doors ----------
# piece: (label, edid, description)
_P = {
    # the hotels' ways in (made in each hotel's own units: a door stands at its hotel's scale)
    'door_royal_hawaiian': ('Door: the Royal Hawaiian', 'FOLabDoorRoyalHawaiian',
                            lambda: unit('FOLabDoorRoyalHawaiian', 300, 324, 'doors/koa_glazed', 'doors/trim_koa', leaves=2, depth=40, liner=10,
                                         fan=152, fan_look='doors/koa_fan')),
    'door_moana': ('Door: the Moana', 'FOLabDoorMoana',
                   lambda: unit('FOLabDoorMoana', 158, 360, 'doors/white_sash', 'doors/trim_white', leaves=1, depth=40, liner=9,
                                top=78, top_look='doors/white_transom')),
    'door_kilauea': ('Door: the Kilauea', 'FOLabDoorKilauea',
                     lambda: unit('FOLabDoorKilauea', 700, 330, 'doors/gold_glass', 'doors/trim_gold', leaves=2, depth=24, liner=20,
                                  top=60, top_look='doors/gold_transom', side=170, side_look='doors/gold_glass', casing=24)),
    # homes with a doorway in their walls: the door lines it
    'door_novac_a': ('Door: NoVac house', 'FOLabDoorNoVacA', lambda: unit('FOLabDoorNoVacA', 92, 148, 'doors/home_turquoise', 'doors/trim_white', depth=14, liner=6)),
    'door_novac_b': ('Door: NoVac house, glazed', 'FOLabDoorNoVacB', lambda: unit('FOLabDoorNoVacB', 96, 144, 'doors/glazed_coral', 'doors/trim_white', depth=14, liner=6)),
    'door_goodsprings': ('Door: Goodsprings home', 'FOLabDoorGoodsprings', lambda: unit('FOLabDoorGoodsprings', 108, 152, 'doors/home_seafoam', 'doors/trim_white', depth=14, liner=7)),
    'door_usonian': ('Door: Usonian home', 'FOLabDoorUsonian', lambda: unit('FOLabDoorUsonian', 94, 144, 'doors/glazed_teal', 'doors/trim_white', depth=14, liner=6)),
    # the bungalow's wall has no hole: its door hangs on it, a cottage door in a casing
    'door_bungalow': ('Door: bungalow', 'FOLabDoorBungalow', lambda: unit('FOLabDoorBungalow', 112, 170, 'doors/home_coral', 'doors/trim_white', flush=True, casing=12)),
    # the hotels' lifts
    # (190 tall: hotelinside.lift_frame's opening is LIFT_H + 16 over the floor; at the game door's 174 a strip of wall
    # showed under the head, seen in nv-rs 22 Nov 2026)
    'lift_lobby': ('Lift doors, lobby', 'FOLabLiftLobby', lambda: lift_door('FOLabLiftLobby', 216, 190, 80, frame=0)),
    'lift_floor': ('Lift doors', 'FOLabLiftFloor', lambda: lift_door('FOLabLiftFloor', 130, 177, 80)),
}
PIECES = {k: {'label': lab, 'edid': e, 'set': SET, 'file': k, 'describe': fn} for k, (lab, e, fn) in _P.items()}
for _k, _v in PIECES.items():
    if _k in modelsets.PIECES and modelsets.PIECES[_k] is not _v:
        raise ValueError('doorset: %s is already a piece' % _k)
    modelsets.PIECES[_k] = _v

# Where each door goes, in its building's frame: building editor ID -> [(piece, x, y, z, outward degrees (0 +y), the game
# doors it replaces)]. x, y on the wall's outer face, z the opening's foot (doorsurvey's medians, 21 Nov 2026; holes to 4).
DOORWAYS = {
    'FOLabLandmarkRoyalHawaiian': [('door_royal_hawaiian', 0.0, 384.0, 10.0, 0.0, ('DoorStorefrontDbl01',))],
    'FOLabLandmarkMoana': [('door_moana', 0.0, 450.0, 40.0, 0.0, ('DoorStorefrontDbl01',))],
    'NoVacHouse01': [('door_novac_a', -265.2, -55.7, 15.0, 270.0, ('OffDoorSmL01',))],
    'NoVacHouse02': [('door_novac_b', -188.5, -265.2, 16.0, 180.0, ('OffDoorHotelSmStatic',))],
    'NVGoodSprhome01': [('door_goodsprings', 0.0, 0.0, 9.0, 180.0, ('NVGoodSpringsHomeExtDoor',))],
    'NVGoodSprhome02': [('door_goodsprings', 210.3, -384.3, -227.0, 180.0, ('NVGoodSpringsHomeExtDoor',))],
    'Usonianhome01': [('door_usonian', -6.7, -1.4, 10.0, 180.0, ('NVRanchHouseExtDoor',))],
    'Usonianhome02': [('door_usonian', 43.1, 0.0, 10.0, 180.0, ('WastelandhomeextDoor',))],
    'NVBungalow2': [('door_bungalow', -231.1, -96.2, 0.0, 270.0, ('OffDoorHotelBlankSmL01',))],
}
# The Kilauea's way in stands on the glass of its drum (towerset: glass at r 2900, mullions every 15 degrees from 7.5,
# the plinth 140 high), in the bay at bearing 240: between two of the lava planters (every 30 degrees from 15) and clear
# of the tower's front fin, which comes down to the plinth at 270. The game's door stood on the ground at bearing 255,
# behind the planter there, and the way out arrived inside that planter (r 3300): KILAUEA_ARRIVE is where one arrives
# now, in front of the door.
KILAUEA = ('door_kilauea', 2912.0, 240.0, 140.0, ('DoorStorefrontDbl01',))
KILAUEA_ARRIVE = 240.0      # (out from the door's face, in the hotel's units, on the plinth)
KILAUEA_INSIDE = 412.0      # (in from the door, the hotel's units: r 2500, where hotelinside.VIEWS has you arrive inside)
CITY = 'FOLabWaikiki'       # (the city's world: a link to a hotel's door here arrives outside, in its small world inside)
# Lift doors: the game's base -> piece (same frame: a swap of base only)
LIFTS = {'HotelElevatorDoor01': 'lift_lobby', 'HotelElevatorDoor02': 'lift_floor', 'HotelElevatorDoor02Static': 'lift_floor'}
NEAR = 64.0        # a door this near a doorway (in the building's units) is that doorway's
# How far a doorway's foot is from the origin of the game door the game stands in it (its mesh made round its middle or
# its foot), so a door's real shift is told from the change of origin; a door whose shift is more than ARRIVE (a building
# reseated since without its door) brings the arrival in front of it along. The hotels keep theirs (hotelinside's).
ORIGIN_RISE = {'NVGoodSpringsHomeExtDoor': -75.6, 'NVRanchHouseExtDoor': -63.6, 'WastelandhomeextDoor': -75.6, 'OffDoorHotelSmStatic': 5.0}
ARRIVE = 24.0
HOTELS = ('door_royal_hawaiian', 'door_moana', 'door_kilauea')
