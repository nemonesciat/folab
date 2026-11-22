"""Kuliouou's people up off the ground (the user, 21 Nov 2026: "that starting valley with the quests is pretty boring.
there could be bamboo tree villages with rope bridges and towers and shacks"). The camp is poor and jumpy: catchers come
for whoever nobody will miss, so the valley's families sleep up in the trees, on platforms joined by rope bridges, one stair
down to the ground that can be watched. FOLab's own pieces in the bamboo set (bambooset's looks and helpers), walked by
walkcheck at 32 and 16 (`WALKS`).

- `tree_platform`: a deck 480 square `RISE` up on four three-cane legs that reach `LEG_DEEP` under its origin, so it can
  stand where the ground falls away (placed by deck height, legs into the ground); railed, with a gap `GAP` wide in the
  middle of each side where a bridge joins (`GAPS`; `rail_gap` closes one nothing joins). Put round a tree's trunk, the
  trunk comes up through the middle of the deck.
- `treehouse`: a bigger deck at `RISE` with a hut on its back half and the guard tower's flight up to its front (the way up
  from the ground: the game's people can't climb ladders), gaps on its two sides in front of the hut (`GAPS`).
- `rope_bridge_<L>`: planks between two hand ropes, sagging `L / SAG`, L units between the decks it joins (its ends at z 0,
  along y; origin in the middle). The walk is the planks (RAMP-thick boxes chained down the sag), each rope a solid wall
  20 thick outside the planks. Between platforms, or across a gully from ground to ground.
- `walkway`: a level plank walk on legs, railed, 512 long, ends open (a bridge without the sag, for short level joins).
- `rail_gap`: rails across one platform gap.
- `ladder`: a bamboo ladder leant against a leg or a hut: something to see; nobody climbs it (FNV has no ladders to climb).
- `canoe_rack`: two trestles by the water with an outrigger canoe up on them and another drawn up beside.

Every piece is a few shapes (bamboo canes, planks, rope, lauhala, thatch, the thatch's fringe); the fringe is the only
see-through picture, and it is never in a far model."""
import math

import bambooset as BS
import guardtower as GT
import modelsets
import restyleset as RS
import texpaint as tp
from modelsets import look

SET = BS.SET
RISE = 400.0            # (a platform's deck top over its origin)
LEG_DEEP = 420.0        # (its legs go this far under the origin: it may stand on ground up to this much lower)
HALF = 240.0            # (a platform's deck, ±HALF)
GAP = GT.WIDE           # (a gap in the rails where a bridge joins: a bridge's planks are this wide)
DECK_T = 20.0
SAG = 18.0              # (a bridge sags its length over this: 1,024 long sags 57; the planks at its ends slope 13 degrees)
SEG = 64.0              # (a bridge's planks are laid in lengths of about this)
LENGTHS = (512, 768, 1024, 1536)
TH_X, TH_Y = 320.0, 300.0       # (the treehouse's deck, ±TH_X by ±TH_Y)
TH_GAP_Y = -150.0               # (its side gaps' middle: in front of the hut)
ROPE = (120, 92, 58)


def rope(size=64, seed=880):
    """Coir rope round a cylinder: strands twisted diagonally."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 32)

    def fn(x, y):
        v = ((x + y) * 4.0 / size) % 1.0
        f = 0.65 + 0.35 * abs(math.sin(v * math.pi)) + 0.12 * (fine.at(x * 0.5, y * 0.5) - 0.5)
        return tp._shade(ROPE, f), 0.5
    c.paint(fn)
    return c


modelsets.TEXTURES.update({'bamboo/rope': lambda: rope()})


def _looks(**more):
    return BS._looks(rope=look('bamboo/rope', tile=24), planks=look('tower/deck', tile=120, turned=True), **more)


# ---------- the parts every piece shares ----------

def _legs(P, half, z_top, deep=LEG_DEEP, inset=18.0):
    """Four legs, each three canes lashed, from `deep` under the origin to z_top, at ±(half - inset); solid as one post
    each; X braces of cane on each side."""
    h = half - inset
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * h, sy * h
            for k in range(3):
                a = math.radians(90 + 120 * k)
                BS._pole(P, x + math.cos(a) * 8, y + math.sin(a) * 8, -deep, z_top, r=8, far=(k == 0))
            for z in (z_top - 60, z_top * 0.4):
                BS._lash(P, x, y, z, 17)
            P.append({'shape': 'box', 'size': [30, 30, z_top + deep], 'at': [x, y, -deep], 'look': None, 'solid': True, 'material': 'wood'})
    for s in (-1, 1):
        for a, b in (((-h, s * h, 30), (h, s * h, z_top - 50)), ((h, s * h, 30), (-h, s * h, z_top - 50)),
                     ((s * h, -h, 30), (s * h, h, z_top - 50)), ((s * h, h, 30), (s * h, -h, z_top - 50))):
            BS._cane(P, a, b, r=5)


def _deck(P, x0, y0, x1, y1, z):
    """A deck of split bamboo, its top at z, joists of cane under it."""
    GT._box(P, x0, y0, z - DECK_T, x1, y1, z, 'deck', far=True)
    for y in (y0 + 20, (y0 + y1) / 2, y1 - 20):
        BS._cane(P, (x0 - 10, y, z - DECK_T - 8), (x1 + 10, y, z - DECK_T - 8), r=8)


def _railing(P, a, b, out):
    """A railing along a deck's edge from a to b (level, (x, y, z) at the floor), out the way the fall is: a wall 90
    high, 20 thick, wholly beyond the edge (collision only), a bamboo top rail and a lower one, posts, lauhala between."""
    ox, oy = out[0], out[1]
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    z = a[2]
    if ox:
        X0, X1 = (x0, x0 + 20) if ox > 0 else (x0 - 20, x0)
        Y0, Y1 = y0, y1
    else:
        Y0, Y1 = (y0, y0 + 20) if oy > 0 else (y0 - 20, y0)
        X0, X1 = x0, x1
    GT._box(P, X0, Y0, z, X1, Y1, z + 90, None)
    mx, my = ox * 6.0, oy * 6.0
    for zz in (88, 46):
        BS._cane(P, (a[0] + mx, a[1] + my, z + zz), (b[0] + mx, b[1] + my, z + zz), r=4 if zz < 60 else 5)
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(round(ln / 100.0)))
    for k in range(n + 1):
        t = k / float(n)
        BS._pole(P, a[0] + (b[0] - a[0]) * t + mx, a[1] + (b[1] - a[1]) * t + my, z, z + 96, r=5)
    # (lauhala woven between the rails: a thin panel on the edge)
    if ox:
        GT._box(P, a[0] + mx - 2, y0, z + 8, a[0] + mx + 2, y1, z + 80, 'mat', solid=False, far=True)
    else:
        GT._box(P, x0, a[1] + my - 2, z + 8, x1, a[1] + my + 2, z + 80, 'mat', solid=False, far=True)


def _side_with_gap(P, a, b, out, gap_mid=None):
    """Rails along a deck's side from a to b with a gap GAP wide round gap_mid (a coordinate along the side), lashed gate
    posts each side of it."""
    if gap_mid is None:
        _railing(P, a, b, out)
        return
    along_x = abs(b[0] - a[0]) > abs(b[1] - a[1])
    lo, hi = gap_mid - GAP / 2, gap_mid + GAP / 2
    if along_x:
        _railing(P, a, (lo, a[1], a[2]), out)
        _railing(P, (hi, a[1], a[2]), b, out)
        for x in (lo - 10, hi + 10):
            BS._pole(P, x, a[1] + out[1] * 10, a[2] - 40, a[2] + 150, r=9)
    else:
        _railing(P, a, (a[0], lo, a[2]), out)
        _railing(P, (a[0], hi, a[2]), b, out)
        for y in (lo - 10, hi + 10):
            BS._pole(P, a[0] + out[0] * 10, y, a[2] - 40, a[2] + 150, r=9)


# ---------- platforms ----------

def tree_platform():
    """See the module's docstring."""
    P = []
    H, z = HALF, RISE
    _legs(P, H, z + 20)
    _deck(P, -H, -H, H, H, z)
    _side_with_gap(P, (-H, -H, z), (H, -H, z), (0, -1), 0.0)
    _side_with_gap(P, (-H, H, z), (H, H, z), (0, 1), 0.0)
    _side_with_gap(P, (-H, -H, z), (-H, H, z), (-1, 0), 0.0)
    _side_with_gap(P, (H, -H, z), (H, H, z), (1, 0), 0.0)
    # (gourds and a rolled mat on the deck, a water jar: lived on)
    P.append({'shape': 'cylinder', 'r': 13, 'h': 140, 'sides': 8, 'turn': [0, 90, 0], 'at': [-H + 60, H - 50, z + 13], 'look': 'mat', 'solid': False})
    for k, (x, y) in enumerate(((H - 60, H - 60), (H - 100, H - 50), (H - 55, H - 105))):
        P.append({'shape': 'cylinder', 'r': 18 + 3 * k, 'r2': 12, 'h': 30 + 6 * k, 'sides': 9, 'at': [x, y, z], 'look': 'mat', 'solid': False})
    return {'name': 'FOLabBambooTreePlatform', 'looks': _looks(), 'parts': P}


def treehouse():
    """See the module's docstring."""
    P = []
    X, Y, z = TH_X, TH_Y, RISE
    _legs_rect(P, X, Y, z + 20)
    _deck(P, -X, -Y, X, Y, z)
    # the hut on the back half: walls, a doorway to the front, thatch
    hx0, hy0, hx1, hy1 = -X + 40, 0.0, X - 40, Y - 20
    top = z + 190
    BS._walls(P, hx0, hy0, hx1, hy1, z, top, door=(0.0, BS.DOOR))
    BS._thatch_hip(P, hx0, hy0, hx1, hy1, top - 6, 0.85 * ((hy1 - hy0) / 2 + 60), 60)
    P.append({'shape': 'cylinder', 'r': 13, 'h': 150, 'sides': 8, 'turn': [0, 90, 0], 'at': [hx0 + 40, hy1 - 40, z + 15], 'look': 'mat', 'solid': False})
    # rails: the front with the stair's gap, the sides with the bridges' gaps (in front of the hut), the back behind it
    _side_with_gap(P, (-X, -Y, z), (X, -Y, z), (0, -1), 0.0)
    _side_with_gap(P, (-X, -Y, z), (-X, Y, z), (-1, 0), TH_GAP_Y)
    _side_with_gap(P, (X, -Y, z), (X, Y, z), (1, 0), TH_GAP_Y)
    _railing(P, (-X, Y, z), (X, Y, z), (0, 1))
    # the way up: the guard tower's flight to the front gap, its rails wholly outside it
    run = z * GT.battleship.LADDER_RUN
    foot = -Y - run - GT.SINK * GT.battleship.LADDER_RUN
    GT._flight(P, 0.0, foot, -GT.SINK, -Y, z, wide=GAP)
    for x, o in ((-GAP / 2, (-1, 0)), (GAP / 2, (1, 0))):
        GT._rail(P, (x, foot, -GT.SINK), (x, -Y, z), o)
    return BS._bamboo_desc({'name': 'FOLabBambooTreehouse', 'parts': P, 'looks_more': _looks()})


def _legs_rect(P, X, Y, z_top, deep=LEG_DEEP):
    """_legs for a rectangle: five legs (the corners and the middle of the back: a middle one in front stood in the stair's
    way onto the deck)."""
    for x, y in [(sx * (X - 18), sy * (Y - 18)) for sx in (-1, 1) for sy in (-1, 1)] + [(0.0, Y - 18)]:
        if True:
            for k in range(3):
                a = math.radians(90 + 120 * k)
                BS._pole(P, x + math.cos(a) * 8, y + math.sin(a) * 8, -deep, z_top, r=8, far=(k == 0))
            BS._lash(P, x, y, z_top - 60, 17)
            P.append({'shape': 'box', 'size': [30, 30, z_top + deep], 'at': [x, y, -deep], 'look': None, 'solid': True, 'material': 'wood'})
    for s in (-1, 1):
        for a, b in (((-X + 18, s * (Y - 18), 30), (0, s * (Y - 18), z_top - 50)), ((X - 18, s * (Y - 18), 30), (0, s * (Y - 18), z_top - 50))):
            BS._cane(P, a, b, r=5)


# ---------- bridges and walks ----------

def _plank_run(P, L, sag, wide=GAP):
    """The planks from y -L/2 to L/2 down a sag (z 0 at the ends), each length a RAMP-thick box with its top on the curve:
    walked and drawn. Returns the curve's points [(y, z)]."""
    n = max(2, int(round(L / SEG)))
    pts = []
    for k in range(n + 1):
        y = -L / 2 + L * k / n
        t = 2 * y / L
        pts.append((y, -sag * (1 - t * t)))
    for (ya, za), (yb, zb) in zip(pts, pts[1:]):
        run = yb - ya
        pitch = math.degrees(math.atan2(zb - za, run))
        ln = math.hypot(run, zb - za) + 4.0                     # (a little overlap: no crack at the joints)
        c = math.cos(math.radians(pitch))
        mid = (0.0, (ya + yb) / 2, (za + zb) / 2 - GT.RAMP / c)
        P.append({'shape': 'box', 'size': [wide, round(ln, 1), GT.RAMP], 'at': [round(v, 1) for v in mid], 'turn': [round(pitch, 3), 0, 0],
                  'look': 'planks', 'solid': True, 'far': True, 'material': 'wood'})
    return pts


def rope_bridge(L, name=None):
    """A rope bridge L long (see the module's docstring)."""
    P = []
    sag = L / SAG
    pts = _plank_run(P, L, sag)
    hx = GAP / 2
    for sx in (-1, 1):
        x = sx * (hx + 6)
        for (ya, za), (yb, zb) in zip(pts, pts[1:]):
            # the rope's wall: 20 thick, 90 high, wholly outside the planks, following the planks' slope
            run = yb - ya
            pitch = math.degrees(math.atan2(zb - za, run))
            ln = math.hypot(run, zb - za) + 2.0
            P.append({'shape': 'box', 'size': [20, round(ln, 1), 90], 'at': [round(sx * (hx + 10), 1), round((ya + yb) / 2, 1), round((za + zb) / 2, 1)],
                      'turn': [round(pitch, 3), 0, 0], 'look': None, 'solid': True, 'material': 'wood'})
            for up, r in ((92, 3.2), (48, 2.4)):          # (hand rope and the lower one)
                P.append(modelsets.limb((x, ya, za + up), (x, yb, zb + up), r, r, 'rope', sides=6))
        for k, (y, zz) in enumerate(pts):                   # (hangers down to the planks' ends, every other joint)
            if 0 < k < len(pts) - 1 and k % 2 == 0:
                P.append(modelsets.limb((x, y, zz + 92), (sx * (hx - 4), y, zz - 4), 1.8, 1.8, 'rope', sides=5))
        for y in (-L / 2, L / 2):                          # (the posts at each end, the ropes tied to them)
            BS._pole(P, sx * (hx + 16), y, -160, 120, r=10, solid=True, far=True)
            BS._lash(P, sx * (hx + 16), y, 92, 10)
    return {'name': name or 'FOLabRopeBridge%d' % L, 'looks': _looks(), 'parts': P}


def walkway(L=512.0):
    """A level plank walk on legs (see the module's docstring), its top at z 0, legs to LEG_DEEP under."""
    P = []
    hx = GAP / 2
    GT._box(P, -hx, -L / 2, -DECK_T, hx, L / 2, 0.0, 'planks', far=True)
    for y in (-L / 2 + 20, L / 2 - 20):
        for sx in (-1, 1):
            BS._pole(P, sx * (hx - 6), y, -LEG_DEEP, -DECK_T, r=10, solid=True, far=(sx < 0))
        BS._cane(P, (-hx - 10, y, -DECK_T - 8), (hx + 10, y, -DECK_T - 8), r=8)
    for sx in (-1, 1):
        _railing(P, (sx * hx, -L / 2, 0.0), (sx * hx, L / 2, 0.0), (sx, 0))
    return {'name': 'FOLabBambooWalkway', 'looks': _looks(), 'parts': P}


def rail_gap():
    """Rails across a gap: along x from -GAP/2 to GAP/2 at y 0, the fall to +y (a platform's +y side). Put at a gap's
    middle on the deck's edge, turned to face out (its +y outward)."""
    P = []
    _railing(P, (-GAP / 2 - 12, 0.0, 0.0), (GAP / 2 + 12, 0.0, 0.0), (0, 1))
    return {'name': 'FOLabBambooRailGap', 'looks': _looks(), 'parts': P}


def ladder(L=460.0, lean=14.0):
    """A ladder of two canes and lashed rungs, leant back (toward +y) `lean` degrees from upright, its feet at z 0."""
    P = []
    s, c = math.sin(math.radians(lean)), math.cos(math.radians(lean))
    for sx in (-1, 1):
        BS._cane(P, (sx * 26, 0, -10), (sx * 22, L * s, L * c), r=5, far=True)
    n = int(L // 40)
    for k in range(1, n):
        t = k / float(n)
        BS._cane(P, (-28, L * s * t, L * c * t), (28, L * s * t, L * c * t), r=3)
    return {'name': 'FOLabBambooLadder', 'looks': _looks(), 'parts': P}


def canoe_rack():
    """See the module's docstring."""
    P = []
    for y in (-260.0, 260.0):
        for sx in (-1, 1):
            BS._cane(P, (sx * 60, y, -10), (0, y, 100), r=6)
        BS._cane(P, (-50, y, 82), (50, y, 82), r=5)
        GT._box(P, -50, y - 10, 0, 50, y + 10, 90, None)
    BS.canoe(P, 0.0, 0.0, 82.0, long=760.0)
    BS.canoe(P, -320.0, 0.0, 0.0, long=880.0)
    GT._box(P, -60, -300, 0, 60, 300, 130, None, far=False)
    P.append({'shape': 'box', 'size': [80, 700, 60], 'at': [0, 0, 60], 'look': 'hull', 'solid': False, 'far_only': True})
    return {'name': 'FOLabBambooCanoeRack', 'looks': _looks(hull=look('waikiki/koa', tile=200)), 'parts': P}


# ---------- registered ----------

PIECES = {'bamboo_tree_platform': ('Tree platform (railed, bridges join each side)', tree_platform),
          'bamboo_treehouse': ('Treehouse (hut on a platform, stair up)', treehouse),
          'bamboo_walkway': ('Bamboo walkway on legs (512)', walkway),
          'bamboo_rail_gap': ('Rails across a platform gap', rail_gap),
          'bamboo_ladder': ('Bamboo ladder (to see)', ladder),
          'bamboo_canoe_rack': ('Canoe rack', canoe_rack)}
for _L in LENGTHS:
    PIECES['bamboo_rope_bridge_%d' % _L] = ('Rope bridge (%d)' % _L, (lambda L: lambda: rope_bridge(L))(_L))
for _k, (_label, _fn) in PIECES.items():
    assert modelsets.PIECES.get(_k, {}).get('set', SET) == SET, _k + " is another set's piece"
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k[7:], 'describe': _fn, 'edid': _fn()['name']})

# where a bridge joins each piece: (x, y) of the gap's middle on the deck's edge, the way out (unit), in the piece's frame
GAPS = {'bamboo_tree_platform': [((0.0, -HALF), (0, -1)), ((HALF, 0.0), (1, 0)), ((0.0, HALF), (0, 1)), ((-HALF, 0.0), (-1, 0))],
        'bamboo_treehouse': [((TH_X, TH_GAP_Y), (1, 0)), ((-TH_X, TH_GAP_Y), (-1, 0))]}
STAIR_FOOT = (0.0, -TH_Y - RISE * GT.battleship.LADDER_RUN)     # (the treehouse's stair meets the ground about here)

# walkcheck: platforms with no stair are walked from a bridge's end (starts), bridges from one end to the other
_P_START = [(0.0, -HALF + 30, RISE)]
WALKS = {'bamboo_tree_platform': {'ground': None, 'starts': _P_START,
                                  'goals': [('each corner', (HALF - 70, HALF - 70, RISE)), ('the far gap', (0.0, HALF - 30, RISE)),
                                            ('the side gaps', (HALF - 30, 0.0, RISE))]},
         'bamboo_treehouse': {'goals': [('the deck', (0.0, -TH_Y + 60, RISE)), ('inside the hut', (0.0, 150.0, RISE)),
                                        ('a side gap', (TH_X - 30, TH_GAP_Y, RISE)), ('the other side gap', (-TH_X + 30, TH_GAP_Y, RISE))]},
         'bamboo_walkway': {'ground': None, 'starts': [(0.0, -230.0, 0.0)], 'goals': [('the far end', (0.0, 230.0, 0.0))]}}
for _L in LENGTHS:
    WALKS['bamboo_rope_bridge_%d' % _L] = {'ground': None, 'starts': [(0.0, -_L / 2 + 30, 0.0)],
                                           'goals': [('the middle', (0.0, 0.0, -_L / SAG)), ('the far end', (0.0, _L / 2 - 30, 0.0))]}
