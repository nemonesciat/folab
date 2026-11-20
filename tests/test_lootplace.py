"""lootplace: a find rests on what is really under it (level decks only, the land with a lean it can take), never on a road,
in water, in another thing's footprint or with something solid in its height; it faces away from what it stands against;
the containers it names are the game's, and an empty one is only ever made the full one of the same model."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import lootplace  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


class FakeSolids:
    """Level squares of surface: [(x0, y0, x1, y1, z, ref)]; bkey names what each ref is."""

    def __init__(self, squares, bkey=None):
        self.squares, self.bkey, self.pr = squares, bkey or {}, None

    def load_round(self, _cks):
        pass

    def tops(self, x, y):
        return [(z, r) for x0, y0, x1, y1, z, r in self.squares if x0 <= x <= x1 and y0 <= y <= y1]


class FakeGround:
    def __init__(self, f, water=None):
        self.f, self.w = f, water

    def at(self, x, y):
        return self.f(x, y)

    def water(self, x, y):
        return self.w


def seat(squares, ground=None, bkey=None, water=None):
    S = lootplace.Seat.__new__(lootplace.Seat)
    S.gd = S.pr = None
    S.grid, S.by_xy, S.edids, S.feet = {}, {}, {}, None
    S.taken = lootplace.collections.defaultdict(list)
    S.solids = FakeSolids(squares, bkey)
    S.G = FakeGround(ground, water) if ground else None
    S.ref_edid = lambda ref: S.solids.bkey.get(ref, '')
    return S


BOX = [-30, -20, 0, 30, 20, 40]
deck = [(-500, -500, 500, 500, 300.0, 'deck')]
p = seat(deck).at(0, 0, 0.0, BOX, 300.0, outside=False)
check('on a level deck it rests at the deck', p is not None and abs(p[2] - 300.0) < 1e-6 and p[3] == p[4] == 0.0, p)
step = [(-500, -500, 0, 500, 300.0, 'a'), (0, -500, 500, 500, 320.0, 'b')]
check('over a step higher than LEVEL it is refused', seat(step).at(0, 0, 0.0, BOX, 300.0, outside=False) is None)
check('a surface far over where it is looked for (a roof over a room) is not stood on',
      seat(deck + [(-500, -500, 500, 500, 600.0, 'roof')]).at(0, 0, 0.0, BOX, 300.0, outside=False)[2] == 300.0)
shelf = deck + [(-10, -10, 10, 10, 320.0, 'shelf')]
p = seat(shelf).at(0, 0, 0.0, BOX, 300.0, outside=False)
check('a surface inside its height (a low shelf over it) refuses the spot', p is None, p)
road = [(-500, -500, 500, 500, 10.0, 'r')]
check('a road piece never holds one', seat(road, bkey={'r': 'FOLabRoadStraight01'}).at(0, 0, 0.0, BOX, 10.0, outside=False) is None)

# on the land
flat = lambda x, y: 100.0
p = seat([], flat).at(0, 0, 0.0, BOX, 100.0)
check('on flat land: level, its underside a hair in the ground', p and abs(p[2] - 99.0) < 1e-6 and p[3] == 0 and p[4] == 0, p)
slope = lambda x, y: 100.0 + 0.1 * x
p = seat([], slope).at(0, 0, 0.0, BOX, 100.0)
check('on a gentle slope up +x it leans to it (+y turn lifts +x)', p and abs(p[4] - math.atan(0.1)) < 1e-3 and abs(p[3]) < 1e-6, p)
steep = lambda x, y: 100.0 + 0.5 * x
check('on a slope steeper than TILT_MOST it is refused', seat([], steep).at(0, 0, 0.0, BOX, 100.0) is None)
check('under the water it is refused', seat([], flat, water=150.0).at(0, 0, 0.0, BOX, 100.0) is None)
S = seat([], flat)
S.feet = lambda fp: [('c', 'tent', [(-100, -100), (100, -100), (100, 100), (-100, 100)], 100.0, 300.0)]
check("another thing's footprint reaching up into it refuses the spot", S.at(0, 0, 0.0, BOX, 100.0) is None)
S.feet = lambda fp: [('c', 'rug', [(-100, -100), (100, -100), (100, 100), (-100, 100)], 95.0, 101.0)]
check('… but not one lying flat under it', S.at(0, 0, 0.0, BOX, 100.0) is not None)

# facing
for front in ((0.0, -1.0), (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0)):
    for want in ((1.0, 0.0), (0.0, 1.0), (-0.6, 0.8)):
        fx, fy = lootplace._turn(front[0], front[1], lootplace._face(want[0], want[1], front))
        check('_face turns a front %s to look along %s' % (front, want), abs(fx - want[0]) < 1e-9 and abs(fy - want[1]) < 1e-9, (fx, fy))
check('back_reach: how far it reaches behind its origin', lootplace.back_reach([-9, -20, -20, 14, 21, 10], (-1.0, 0.0)) == 14)
P = type('P', (), {})()
P.box = lambda e: BOX
P.front = lambda e: (1.0, 0.0)
P.rng = lootplace.random.Random(1)
O = lootplace.Outside(P, None, None, (0, 0))
anchor = (1000.0, 0.0, 0.0, 0.7, 1.0, [-50, -50, 0, 50, 50, 80], 'Tent', 'c', 'r', 0.0)
spots = O.beside(anchor, 'x')
ok = True
for x, y, rz in spots:
    fx, fy = lootplace._turn(1.0, 0.0, rz)                    # (its front in the world)
    lx, ly = lootplace._turn(x - 1000.0, y, -0.7)              # (where it stands in the anchor's own frame)
    ux, uy = lootplace._turn(fx, fy, -0.7)
    side = (0, 1) if abs(ly) > abs(lx) else (1, 0)
    if side == (0, 1):
        ok = ok and abs(abs(ly) - (50 + 30 + 8)) < 1e-6 and abs(uy - math.copysign(1, ly)) < 1e-6
    else:
        ok = ok and abs(abs(lx) - (50 + 30 + 8)) < 1e-6 and abs(ux - math.copysign(1, lx)) < 1e-6
check('beside a thing: just clear of it, its back to it, its front looking out', len(spots) == 12 and ok, spots[:3])

# the game's own containers
if '--no-game' not in sys.argv:
    import gamedata
    gd = gamedata.GameData()

    names = {gd.edid(f) for f, (_i, r) in gd.forms.items() if r.tag == 'CONT' and f >> 24 == 0}
    used = {e for rows in lootplace.KINDS.values() for band in rows for e, _w, _l in band}
    check('every container named is FalloutNV.esm\'s', used <= names, sorted(used - names))
    check('every empty container to fill is the game\'s', set(lootplace.FILL) <= names, sorted(set(lootplace.FILL) - names))
    P = type('P', (), {})()
    P.gd, P.pr = gd, None
    I = lootplace.Inside(P, lambda ck: 0)
    bad = []
    for ek, by in I.fill.items():
        for k, fk in by.items():
            if not lootplace._same_model(gd, gd.from_key(ek), gd.from_key(fk)):
                bad.append((ek, fk))
    check('an empty container is only filled with one of its own model', I.fill and not bad, bad)
    for model, want in ((r'clutter\footlocker\footlocker01.nif', (-1.0, 0.0)), (r'clutter\lockercabinet01.nif', (0.0, -1.0)),
                        (r'clutter\security\genericsafe01.nif', (1.0, 0.0))):
        check('the front of %s is its detailed side %s' % (model, want), lootplace.front_of(gd, model) == want, lootplace.front_of(gd, model))
    check('most empties have a full twin', len(I.fill) >= 5, sorted(gd.edid(gd.from_key(k)) for k in I.fill))

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
