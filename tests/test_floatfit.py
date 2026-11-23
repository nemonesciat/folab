"""Daylight under buildings (floatfit.py) on a small made-up world with no game files: a building of FOLab's own set stood over
flat ground has the land raised to its foot all round, never moved; on a slope only the low side rises; a road beside keeps
its ground and is named as the reason; a plant on the raised ground rises with it, one far off doesn't; a ship isn't a
building; a lower neighbour isn't buried past BURY_OTHER; a second run changes nothing. After 22 Nov 2026: "must have
missed the memo about floating houses"."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import floatfit  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


class FakeGD:
    """Cells (0..3, 0..3) of one world; land only in the project, nothing of the game's placed."""
    forms = {}

    def __init__(self):
        self._grid = {(x, y): 1000 + x * 10 + y for x in range(4) for y in range(4)}

    def grid(self, world):
        return self._grid

    def key(self, c):
        return 'W.esp:%06X' % c

    def from_key(self, k):
        return int(k.split(':')[1], 16)

    def land_at(self, world, x, y):
        return None

    def refs(self, c):
        return []

    def fields(self, c):
        return {'DATA': b'\0'}          # (no water anywhere)


class FakePR:
    def __init__(self, gd, height):
        self.land, self.water, self.records = {}, {}, {}
        for (cx, cy), c in gd.grid(None).items():
            self.land[gd.key(c)] = {'h': [float(height(cx * 4096 + col * 128, cy * 4096 + row * 128)) for row in range(33) for col in range(33)],
                                    'c': None, 'q': None}
        self.cells = {gd.key(c): {'refs': {}} for c in gd.grid(None).values()}

    def put(self, gd, rk, base, x, y, z, rz=0.0, s=1.0):
        ck = gd.key(gd.grid(None)[(int(x // 4096), int(y // 4096))])
        self.cells[ck]['refs'][rk] = {'base': base, 'p': [x, y, z, 0.0, 0.0, rz], 's': s}
        return ck

    def ref(self, rk):
        return next(c['refs'][rk] for c in self.cells.values() if rk in c['refs'])

    def apply(self, ops):
        for o in ops:
            if o['op'] == 'land':
                self.land[o['cell']] = o['land']
            elif o['op'] == 'move':
                self.cells[o['cell']]['refs'][o['ref']]['p'] = o['p']


HOTEL, ROAD, PALM, SHIP, SHACK = '+000001', '+000002', '+000003', '+000004', '+000005'
BASES = {HOTEL: ('STAT', 'FOLabHotelTest', r'meshes\folab\hotel\test.nif', [-300, -300, 0, 300, 300, 900]),
         ROAD: ('STAT', 'FOLabRoadLong', r'meshes\folab\rubble\road_long.nif', [-512, -320, -16, 512, 320, 8]),
         PALM: ('STAT', 'FOLabBeachPalmTall', r'meshes\folab\beach\palm_tall.nif', [-60, -60, 0, 60, 60, 600]),
         SHIP: ('STAT', 'FOLabFlotillaShip', r'meshes\folab\settler\ship.nif', [-900, -300, 0, 900, 300, 600]),
         SHACK: ('STAT', 'WoodShack01', r'meshes\architecture\wasteland\woodshack01.nif', [-200, -200, 0, 200, 200, 300])}
floatfit.base_info = lambda gd, pr, key: BASES.get(key, ('', '', '', None))
floatfit.catalogue_mids = lambda gd: {}
import server  # noqa: E402
server._land_tex = {}
gd = FakeGD()
X, Y = 6144.0, 6144.0


def gap_of(pr, rk):
    rows = floatfit.measure(gd, pr, None)
    return next((r['gap'] for r in rows if r['key'] == rk), None)


# ---------- the kinds ----------
check('a piece of FOLab\'s hotel set is a building', floatfit.kind('STAT', 'FOLabHotelTest', r'meshes\folab\hotel\test.nif', BASES[HOTEL][3]) == 'building')
check('a game shack is a building', floatfit.kind('STAT', 'WoodShack01', r'meshes\architecture\wasteland\woodshack01.nif', BASES[SHACK][3]) == 'building')
check('a road piece is a road', floatfit.kind('STAT', 'FOLabRoadLong', r'meshes\folab\rubble\road_long.nif', BASES[ROAD][3]) == 'road')
check('a palm and a ship are not buildings', floatfit.kind(*BASES[PALM]) is None and floatfit.kind(*BASES[SHIP]) is None)
check('a lamp post is street dressing', floatfit.kind('STAT', 'StreetLight01', r'meshes\architecture\urban\streetdressing\streetlight01.nif', [-20, -20, 0, 20, 20, 400]) is None)

# ---------- a hotel stood 120 over flat ground: the land up to it, the hotel left where it is ----------
pr = FakePR(gd, lambda x, y: 0.0)
pr.put(gd, '+H', HOTEL, X, Y, 120.0)
pr.put(gd, '+P1', PALM, X + 300 + 120, Y, 0.0)          # (on what will be its apron)
pr.put(gd, '+P2', PALM, X + 3000, Y + 3000, 0.0)        # (far off)
pr.put(gd, '+S', SHIP, X - 4000, Y - 4000, 200.0)       # (a ship isn't measured)
check('daylight under the hotel, 120 units', abs(gap_of(pr, '+H') - 120) < 0.5, gap_of(pr, '+H'))
check('the ship isn\'t a building to measure', gap_of(pr, '+S') is None)
ops, rep = floatfit.fix(gd, pr, None)
pr.apply(ops)
check('the hotel didn\'t move', pr.ref('+H')['p'][2] == 120.0)
check('no daylight under it now (%s)' % gap_of(pr, '+H'), gap_of(pr, '+H') <= floatfit.DONE)
g = roadgen.Ground(gd, pr, None)
check('the land meets its walls all round', all(abs(g.at(X + dx, Y + dy) - 120) <= 8 for dx, dy in ((-340, 0), (340, 0), (0, -340), (0, 340))),
      [round(g.at(X + dx, Y + dy)) for dx, dy in ((-340, 0), (340, 0), (0, -340), (0, 340))])
check('and eases back to the land as it was', g.at(X + 300 + floatfit.HOLD + floatfit.EASE_MIN * 1.6, Y) < 60 and g.at(X + 2000, Y) == 0.0,
      round(g.at(X + 300 + floatfit.HOLD + floatfit.EASE_MIN * 1.6, Y)))
check('the palm on the apron rose with it', abs(pr.ref('+P1')['p'][2] - g.at(X + 420, Y)) < 2, pr.ref('+P1')['p'][2])
check('the palm far off didn\'t move', pr.ref('+P2')['p'][2] == 0.0)
check('every height on a whole step', all(v % 8 == 0 for f in pr.land.values() for v in f['h']))
grid = gd.grid(None)
torn = 0
for (cx, cy), c in grid.items():
    a = pr.land[gd.key(c)]['h']
    if (cx + 1, cy) in grid:
        b = pr.land[gd.key(grid[(cx + 1, cy)])]['h']
        torn += sum(a[r * 33 + 32] != b[r * 33] for r in range(33))
    if (cx, cy + 1) in grid:
        b = pr.land[gd.key(grid[(cx, cy + 1)])]['h']
        torn += sum(a[32 * 33 + col] != b[col] for col in range(33))
check('cell edges still meet', torn == 0, torn)
ops2, rep2 = floatfit.fix(gd, pr, None)
check('a second run changes nothing', not ops2 and rep2['gapped_before'] == 0, rep2)

# ---------- on a slope: only the low side rises ----------
slope = lambda x, y: (x - 4096) * 0.2
pr = FakePR(gd, slope)
pr.put(gd, '+H', HOTEL, X, Y, slope(X + 300, Y))          # (its foot level with the high side)
high_before = roadgen.Ground(gd, pr, None).at(X + 400, Y)
ops, rep = floatfit.fix(gd, pr, None)
pr.apply(ops)
g = roadgen.Ground(gd, pr, None)
check('on a slope: no daylight on the low side now', gap_of(pr, '+H') <= floatfit.DONE, gap_of(pr, '+H'))
check('the high side isn\'t cut down', g.at(X + 400, Y) >= high_before - 0.5, (high_before, g.at(X + 400, Y)))

# ---------- a road along the low wall: its ground stays, and the gap is named for it ----------
pr = FakePR(gd, lambda x, y: 0.0)
pr.put(gd, '+H', HOTEL, X, Y, 120.0)
pr.put(gd, '+R', ROAD, X, Y - 300 - 330, -8.0)            # (along the south wall, its edge just outside it)
road_before = roadgen.Ground(gd, pr, None).at(X, Y - 630)
ops, rep = floatfit.fix(gd, pr, None)
pr.apply(ops)
check('the road\'s ground is as it was', roadgen.Ground(gd, pr, None).at(X, Y - 630) == road_before)
check('the road piece didn\'t move', pr.ref('+R')['p'][2] == -8.0)
left = rep['left']
check('daylight left over the road is named for it', left and left[0]['why'] == 'a road runs along that wall', left[:1])

# ---------- a lower neighbour isn't buried past BURY_OTHER ----------
pr = FakePR(gd, lambda x, y: 0.0)
pr.put(gd, '+H', HOTEL, X, Y, 300.0)
pr.put(gd, '+K', SHACK, X + 300 + 250, Y, 0.0)            # (a shack right against its east wall, on the ground)
ops, rep = floatfit.fix(gd, pr, None)
pr.apply(ops)
g = roadgen.Ground(gd, pr, None)
under = max(g.at(X + 550 + dx, Y + dy) for dx in (-128, 0, 128) for dy in (-128, 0, 128))
check('the land under the shack rises no more than BURY_OTHER (%d)' % under, under <= floatfit.BURY_OTHER + 8)
check('the shack didn\'t move', pr.ref('+K')['p'][2] == 0.0)
