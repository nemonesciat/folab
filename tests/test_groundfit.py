"""Ground upwards (groundfit.py, roadbed.onto_roads): on a small made-up world with no game files, a building stood high on
a slope comes down to the street, its yard flat, the land under a road left; close neighbours share a level, but none is
lifted far over its own street; things in a road piece go onto it, once; junk hanging off a slope is let down.
After 18 Nov 2026: buildings on grass plinths, cars in the road slabs, tents hanging off hills, all over Waikiki."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import groundfit  # noqa: E402
import roadbed  # noqa: E402
import townbuild  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


class FakeGD:
    """Cells (0..2, 0..2) of one world; land only in the project."""

    def __init__(self):
        self._grid = {(x, y): 1000 + x * 10 + y for x in range(3) for y in range(3)}

    def grid(self, world):
        return self._grid

    def key(self, c):
        return 'W.esp:%06X' % c

    def from_key(self, k):
        return int(k.split(':')[1], 16)

    def land_at(self, world, x, y):
        return None

    def edid(self, b):
        return {1: 'NVHouse01', 2: 'WastelandRoad01', 3: 'Car01HulkBodyStatic', 4: 'CLSoldiersTent01'}.get(b, '')


class FakePR:
    def __init__(self, gd, height):
        self.land = {}
        for (cx, cy), c in gd.grid(None).items():
            h = []
            for row in range(33):
                for col in range(33):
                    h.append(float(height(cx * 4096 + col * 128, cy * 4096 + row * 128)))
            self.land[gd.key(c)] = {'h': h, 'c': None, 'q': None}
        self.cells = {gd.key(c): {'refs': {}} for c in gd.grid(None).values()}
        self.records = {}

    def put(self, gd, rk, base, x, y, z, rz=0.0, s=1.0):
        ck = gd.key(gd.grid(None)[(int(x // 4096), int(y // 4096))])
        self.cells[ck]['refs'][rk] = {'base': base, 'p': [x, y, z, 0.0, 0.0, rz], 's': s}
        return ck


HOUSE, ROAD, CAR, TENT = 'W.esp:000001', 'W.esp:000002', 'W.esp:000003', 'W.esp:000004'
BOXES = {HOUSE: [-200, -200, -50, 200, 200, 400], ROAD: [-256, -256, -25, 256, 256, 0], CAR: [-100, -50, 0, 100, 50, 60],
         TENT: [-120, -120, 0, 120, 120, 150]}
CAT = [{'key': HOUSE, 'mid': 0.0, 'edid': 'NVHouse01'}]
townbuild.obnd = lambda gd, b: BOXES.get(b)
townbuild.load = lambda gd, folder: CAT
roadbed._flat_bases = lambda gd, pr=None: {ROAD: BOXES[ROAD]}
roadbed._slab_bases = lambda gd: {}
import server  # noqa: E402
server.kits_folder = lambda: ''
gd = FakeGD()

# ---------- a house stood 120 over flat ground round it: down to the street, its yard flat ----------
pr = FakePR(gd, lambda x, y: 0.0)
ck = pr.put(gd, '+H1', HOUSE, 6144, 6144, 120.0)
ops, rep = groundfit.fit(gd, pr, None, cat=CAT)
mv = [o for o in ops if o['op'] == 'move' and o['ref'] == '+H1']
check('a house stood high comes down to its street', mv and abs(mv[0]['p'][2] - (0 - groundfit.SINK)) < 1, mv and mv[0]['p'])
check('… and is reported moved down', rep['moved_down'] == 1 and rep['set'] == 1, rep)

# ---------- a raised bank round a house: taken back down, the yard at the street ----------
bank = lambda x, y: max(0.0, 96 - max(abs(x - 6144), abs(y - 6144)) * 0.2)
pr = FakePR(gd, bank)
pr.put(gd, '+H1', HOUSE, 6144, 6144, 96.0)
ops, rep = groundfit.fit(gd, pr, None, cat=CAT)
for o in ops:
    if o['op'] == 'land':
        pr.land[o['cell']] = o['land']
    elif o['op'] == 'move':
        pr.cells[o['cell']]['refs'][o['ref']]['p'] = o['p']
g = roadgen.Ground(gd, pr, None)
z = pr.cells[ck]['refs']['+H1']['p'][2]
wall = [g.at(6144 + dx, 6144 + dy) for dx, dy in ((-232, 0), (232, 0), (0, -232), (0, 232))]
check('a banked house: its wall foot meets its yard all round', all(abs(z + groundfit.SINK - h) <= 8 for h in wall), (z, wall))
check('… and the yard is at the street, not on the old bank', z < 60, z)

# ---------- a road beside: its ground is the road's ----------
pr = FakePR(gd, lambda x, y: 0.0)
pr.put(gd, '+H1', HOUSE, 6144, 6144, 120.0)
pr.put(gd, '+R1', ROAD, 6144 + 600, 6144, 14.0)
before = roadgen.Ground(gd, pr, None).at(6144 + 600, 6144)
ops, rep = groundfit.fit(gd, pr, None, cat=CAT)
for o in ops:
    if o['op'] == 'land':
        pr.land[o['cell']] = o['land']
after = roadgen.Ground(gd, pr, None).at(6144 + 600, 6144)
check('the land under a road beside a house is left as it was', abs(after - before) < 0.5, (before, after))

# ---------- neighbours: close ones share a level, but none is lifted far over its own street ----------
slope = lambda x, y: (x - 4096) * 0.25
pr = FakePR(gd, slope)
pr.put(gd, '+A', HOUSE, 5500, 6144, slope(5500, 6144) + 50)
pr.put(gd, '+B', HOUSE, 5500 + 420, 6144, slope(5920, 6144) + 50)
ops, rep = groundfit.fit(gd, pr, None, cat=CAT)
zs = {o['ref']: o['p'][2] for o in ops if o['op'] == 'move' and o['ref'] in ('+A', '+B')}
check('two close houses on a slope are one terrace', rep['terraces'] == 1, rep)
check('… the lower is never lifted more than TERRACE_MOST over its own street', zs.get('+A', 0) - slope(5500, 6144) <= groundfit.TERRACE_MOST + 8, zs)

# ---------- things sunk in a road go onto it, once ----------
pr = FakePR(gd, lambda x, y: 0.0)
pr.put(gd, '+R1', ROAD, 6144, 6144, 14.0)
pr.put(gd, '+C1', CAR, 6144, 6144, -2.0)
pr.put(gd, '+T1', TENT, 9000, 9000, 0.0)
ops, rep = roadbed.onto_roads(gd, pr, None)
check('a car sunk in a road piece goes up onto it', len(ops) == 1 and abs(ops[0]['p'][2] - 12.0) < 0.5, ops)
check('… nothing off the road moves', all(o['ref'] == '+C1' for o in ops))
pr.cells[ops[0]['cell']]['refs']['+C1']['p'] = ops[0]['p']
check('… and a second run does nothing', roadbed.onto_roads(gd, pr, None)[1]['lifted'] == 0)

# ---------- daylight under a wall: let down, or the ground filled where a door won't let it go further ----------
CAT_DOOR = [{'key': HOUSE, 'mid': 0.0, 'edid': 'NVHouse01', 'doors': [{'x': 0.0, 'y': -200.0, 'z': 0.0}]}]
pr = FakePR(gd, lambda x, y: 0.0)
ck = pr.put(gd, '+H1', HOUSE, 6144, 6144, 120.0)
ops, rep = groundfit.close_gaps(gd, pr, None, cat=CAT)
mv = [o for o in ops if o['op'] == 'move' and o['ref'] == '+H1']
check('a house with daylight under it all round is let down into the ground', mv and abs(mv[0]['p'][2] - (0 - groundfit.SINK)) < 1, mv and mv[0]['p'])
check('… and no ground is raised for it', not any(o['op'] == 'land' for o in ops), rep)
pr.cells[ck]['refs']['+H1']['p'] = mv[0]['p']
check('… and a second run does nothing', groundfit.close_gaps(gd, pr, None, cat=CAT)[1].get('gaps') == 0)
# on a slope with its door on the uphill side: let down only till the door's sill meets the ground, the rest filled
slope2 = lambda x, y: (y - 6144) * 0.3
pr = FakePR(gd, slope2)
pr.put(gd, '+H1', HOUSE, 6144, 6144, slope2(6144, 6144 + 232) + 0.0)   # (foot level with the uphill ground)
ops, rep = groundfit.close_gaps(gd, pr, None, cat=CAT_DOOR)
for o in ops:
    if o['op'] == 'land':
        pr.land[o['cell']] = o['land']
    elif o['op'] == 'move':
        pr.cells[o['cell']]['refs'][o['ref']]['p'] = o['p']
g = roadgen.Ground(gd, pr, None)
z = list(pr.cells.values())[0]['refs'].get('+H1', None) or next(c['refs']['+H1'] for c in pr.cells.values() if '+H1' in c['refs'])
z = z['p'][2]
door_g = g.at(6144, 6144 - 200)
check('the door on the downhill wall is never buried more than DOOR_BURY', door_g - z <= groundfit.DOOR_BURY + 1, (z, door_g))
low = min(g.at(6144 + dx, 6144 - 232) for dx in (-150, 0, 150))
check('… and the ground under that wall comes up to its foot', z - low < groundfit.GAP, (z, low))

# ---------- junk hanging off a slope is let down ----------
pr = FakePR(gd, lambda x, y: (x - 8192) * 0.5)
pr.put(gd, '+T1', TENT, 8192, 8192, 60.0)
ops, rep = groundfit.settle_pieces(gd, pr, None)
lowest = (8192 - 120 - 8192) * 0.5
check('a tent hanging off a slope is let down to its lowest corner', ops and abs(ops[0]['p'][2] - (lowest - groundfit.SET_SINK)) < 1, ops)
pr.cells[ops[0]['cell']]['refs']['+T1']['p'] = ops[0]['p']
check('… and a second run does nothing', groundfit.settle_pieces(gd, pr, None)[1]['let_down'] == 0)
