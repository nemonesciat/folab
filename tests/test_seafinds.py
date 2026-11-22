"""seafinds and lookouts: a wreck lies along the floor, bedded in it and wholly under the water, never on a steep or rough
floor; a find on the sea's floor is taken only when asked for (wet); a find on a top rests on the top's floor, not on a roof
over it or the ground under it, and faces the middle; markers are named for the nearest place; every form they name is
the game's."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import lootplace  # noqa: E402
import lookouts  # noqa: E402
import seafinds  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


class FakeGround:
    def __init__(self, f, water=None):
        self.f, self.w = f, water

    def at(self, x, y):
        return self.f(x, y)

    def water(self, x, y):
        return self.w


class FakeSolids:
    def __init__(self, squares):
        self.squares, self.bkey = squares, {}

    def load_round(self, _cks):
        pass

    def tops(self, x, y):
        return [(z, r) for x0, y0, x1, y1, z, r in self.squares if x0 <= x <= x1 and y0 <= y <= y1]


def sea(floor, water=0.0, seed=1):
    S = seafinds.Sea.__new__(seafinds.Sea)
    S.rng = seafinds.random.Random(seed)
    S.G = FakeGround(floor, water)
    S.wet, S.boxes, S.grid = {}, {}, {}
    return S


BOAT = [-334, -778, 0, 334, 778, 927]           # (the game's Boat01a)
S = sea(lambda x, y: -1500.0 + 0.1 * y)
S.box = lambda key: BOAT
laid = [S.lay('boat', 0.0, 0.0) for _k in range(12)]
laid = [p for p in laid if p]
check('a wreck lies on a gentle floor', laid)
import navgen  # noqa: E402
ok_all = True
for p in laid:
    m = navgen._turn(p[3], p[4], p[5])
    corners = [(a, b, c) for a in (BOAT[0], BOAT[3]) for b in (BOAT[1], BOAT[4]) for c in (BOAT[2], BOAT[5])]
    zs = [(p[0] + m[0][0] * a + m[0][1] * b + m[0][2] * c, p[1] + m[1][0] * a + m[1][1] * b + m[1][2] * c, p[2] + m[2][0] * a + m[2][1] * b + m[2][2] * c) for a, b, c in corners]
    top = max(z for _x, _y, z in zs)
    keel = [(x, y, z) for (x, y, z), (_a, _b, c) in zip(zs, corners) if c == BOAT[2]]
    if top > -seafinds.UNDER or any(z > S.G.at(x, y) + 24 for x, y, z in keel):
        ok_all = False
check('it is wholly under the water and no corner of its keel hangs over the floor', ok_all)
check('it lists over (its turn about its length is not just the slope)', any(abs(p[4]) > 0.05 for p in laid))
S = sea(lambda x, y: -400.0)
S.box = lambda key: BOAT
check('in water shallower than the hull it is refused', all(S.lay('boat', 0.0, 0.0) is None for _k in range(8)))
S = sea(lambda x, y: -1500.0 + 0.6 * y)
S.box = lambda key: BOAT
check('on a steep floor it is refused', all(S.lay('boat', 0.0, 0.0) is None for _k in range(8)))
S = sea(lambda x, y: -1500.0 + (300.0 if (int(x // 100) + int(y // 100)) % 2 else 0.0))
S.box = lambda key: BOAT
check('on a rough floor it is refused', all(S.lay('boat', 0.0, 0.0) is None for _k in range(8)))


def seat(ground, water, squares=()):
    St = lootplace.Seat.__new__(lootplace.Seat)
    St.gd = St.pr = None
    St.grid, St.by_xy, St.edids, St.feet = {}, {}, {}, None
    St.taken = lootplace.collections.defaultdict(list)
    St.solids = FakeSolids(list(squares))
    St.G = FakeGround(ground, water)
    St.ref_edid = lambda ref: ''
    St.wet = False
    return St


BOX = [-30, -20, 0, 30, 20, 40]
St = seat(lambda x, y: -600.0, 0.0)
check('on the sea floor a find is refused unless asked for', St.at(0, 0, 0.0, BOX, -600.0) is None)
St.wet = True
p = St.at(0, 0, 0.0, BOX, -600.0)
check('with wet it rests on the sea floor', p is not None and abs(p[2] + 601.0) < 1.5, p)

# a top: a deck at 840 with a roof over it at 1040, the ground under at 0
T = lookouts.Tops.__new__(lookouts.Tops)
T.rng = seafinds.random.Random(3)
T.gd = None


class FakePlan:
    def key_of(self, edid):
        return edid

    def front(self, edid):
        return (0.0, -1.0)


T.P = FakePlan()
lookouts.townbuild_obnd = None
real = lookouts.townbuild.obnd
lookouts.townbuild.obnd = lambda gd, key: BOX
try:
    St = seat(lambda x, y: 0.0, None, [(-200, -200, 200, 200, 840.0, 'deck'), (-260, -260, 260, 260, 1040.0, 'roof')])
    got = T.on_top(St, 'c', 'Footlocker', 0.0, 0.0, 840.0, 160, 0.0)
finally:
    lookouts.townbuild.obnd = real
check('a find on a top rests on the deck, under the roof', got and abs(got[0][2] - 840.0) < 1e-6, got)
if got:
    p = got[0]
    fx, fy = lootplace._turn(0.0, -1.0, p[5])
    check('its front looks to the middle', fx * (0 - p[0]) + fy * (0 - p[1]) > 0, p)
    check('it stands near the rail, not in the middle', max(abs(p[0]), abs(p[1])) > 100, p)

marks = {"Aina Haina Squatters' Camp": (0, 0, 0), 'Koko Marina': (9000, 0, 0)}
check('a marker is named for the nearest place, its camp word left off', lookouts.marker_name(marks, 100, 0) == 'Aina Haina Lookout')
check('...or the place itself', lookouts.marker_name(marks, 8800, 0) == 'Koko Marina Lookout')

# every form named is the game's
try:
    import gamedata
    gd = gamedata.GameData()
except Exception as e:
    gd = None
    print('(no game files: %s)' % e)
if gd:
    names = {gd.edid(f): r.tag for f, (_i, r) in gd.forms.items() if (f >> 24) <= 9}
    for band in seafinds.WRECKS:
        for e in band:
            check('wreck %s is a game static' % e, names.get(e) == 'STAT')
    for band in seafinds.KEEPERS:
        for e, _n in band:
            check('keeper %s is the game\'s' % e, names.get(e) in ('CREA', 'LVLC'))
    check('the nest\'s bedroll is the game\'s', names.get(lookouts.NEST[0]) in ('STAT', 'FURN'))
    check('the rim\'s sandbag is the game\'s', names.get(lookouts.RIM_SANDBAG) == 'STAT')
    check('the lifeguard\'s first aid kit is the game\'s', names.get('LootFirstAidKitNV') == 'CONT')

print('%d/%d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
