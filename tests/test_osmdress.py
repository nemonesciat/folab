"""Round a building (osmdress.py): pavement laid along its walls and rubble banked against them, as the game has round
its own, and the things that say what the building was; none of it inside the building, on a road or off its level."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import osmcover  # noqa: E402
import osmdress  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402
import server  # noqa: E402
import townbuild  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = server.GD = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
g0 = roadgen.Ground(gd, None, world)


def flat(k):
    hs = [h for dx in (-1, 0, 1) for dy in (-1, 0, 1) for h in (g0.cell((k[0] + dx, k[1] + dy)) or [None])]
    return None not in hs and max(hs) - min(hs) < 400 and min(hs) > 2000


xy = next(k for k in sorted(grid) if flat(k))
x, y = xy[0] * 4096.0 + 2048, xy[1] * 4096.0 + 2048
cat = townbuild.load(gd, server.kits_folder())
shop = next(b for b in cat if b['edid'] == 'NVOfficeBldg03')


class Cover:
    """All of it one kind of ground, but a road along the south."""
    def __init__(self, kind):
        self.gx0, self.gy0 = int(x // 128) - 60, int(y // 128) - 60
        self.A = self.D = 121
        v = osmcover.ORDER.index(kind) + 1
        self.kind = bytearray([v]) * (self.A * self.D)
        road = osmcover.ORDER.index('asphalt') + 1
        for gy in range(0, 46):
            for gx in range(self.A):
                self.kind[gy * self.A + gx] = road
        self.built = bytearray(self.A * self.D)


pr = project.Project.create('Dressed')
level = g0.at(x, y)
# (the ground under and round it level, as a plot is)
import land  # noqa: E402
ops = []
for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
        k = (xy[0] + dx, xy[1] + dy)
        form = land.decode(gd, gd.land_at(world, *k), {})
        form['h'] = [float(round(level / 8) * 8)] * 1089
        ops.append({'op': 'land', 'cell': gd.key(grid[k]), 'land': form})
pr.apply('level', ops)
level = float(round(level / 8) * 8)
turn = 0.6
pr.apply('add', [{'op': 'add', 'cell': gd.key(grid[xy]), 'base': shop['key'], 'p': [x, y, level - shop['mid'], 0.0, 0.0, turn], 's': 1}])
stands = osmdress.standing(gd, pr, world, cat)
check('the building the mod stood is found', len(stands) == 1 and stands[0][0]['edid'] == 'NVOfficeBldg03')
check('and the ground to keep under it is its own box, turned as it is', osmdress.keep_of(stands) == [(x, y, turn) + tuple(shop['box'][k] for k in (0, 1, 3, 4))])

ops, rep = osmdress.footings(gd, pr, world, Cover('paved'), cat)
edid = lambda o: gd.edid(gd.from_key(o['base']))
slabs = [o for o in ops if edid(o).startswith('SW')]
rubble = [o for o in ops if not edid(o).startswith('SW')]
check('pavement is laid round it', rep['paved'] == 1 and len(slabs) >= 8, (len(slabs), rep))
b = shop['box']


def local(o, with_box=True):
    """Where a thing's box's middle is, in the building's own frame."""
    ob = townbuild.obnd(gd, o['base'])
    yaw = o['p'][5]
    mx, my = (ob[0] + ob[3]) / 2, (ob[1] + ob[4]) / 2
    wx, wy = o['p'][0] + mx * math.cos(yaw) + my * math.sin(yaw), o['p'][1] - mx * math.sin(yaw) + my * math.cos(yaw)
    dx, dy = wx - x, wy - y
    return dx * math.cos(turn) - dy * math.sin(turn), dx * math.sin(turn) + dy * math.cos(turn)


mids = [local(o) for o in slabs]
outside = [not (b[0] < lx < b[3] and b[1] < ly < b[4]) for lx, ly in mids]
near = [max(b[0] - lx, lx - b[3], b[1] - ly, ly - b[4]) <= 200 for lx, ly in mids]
check('every slab lies just outside a wall, none under the building', all(outside) and all(near), (sum(outside), sum(near), len(mids)))
sides = {('w' if lx < b[0] else 'e' if lx > b[3] else '') + ('s' if ly < b[1] else 'n' if ly > b[4] else '') for lx, ly in mids}
check('along more than one wall', len(sides & {'w', 'e', 'n', 's'}) >= 2, sorted(sides))
check('a little over the ground the building stands on', all(abs(o['p'][2] - level - osmdress.SLAB_UP) < 0.2 for o in slabs))
on_road = lambda o: (o['p'][1] / 128 - (int(y // 128) - 60)) < 45
check('none on the road', not any(on_road(o) for o in ops), sum(on_road(o) for o in ops))
check('rubble is banked against walls, outside them', all(not (b[0] + 30 < lx < b[3] - 30 and b[1] + 30 < ly < b[4] - 30) for lx, ly in (local(o) for o in rubble)), len(rubble))
steep, _r = osmdress.footings(gd, project.Project.create('Bare'), world, Cover('paved'), cat)
check('nothing where no building stands', steep == [])

props, rep2 = osmdress.life(gd, pr, world, Cover('paved'), cat)
check('things that say what it was stand round it', rep2['buildings'] == 1 and len(props) >= 3, rep2)
check('none of them inside it', not any(b[0] < lx < b[3] and b[1] < ly < b[4] for lx, ly in ((
    (o['p'][0] - x) * math.cos(turn) - (o['p'][1] - y) * math.sin(turn), (o['p'][0] - x) * math.sin(turn) + (o['p'][1] - y) * math.cos(turn)) for o in props)))
check('all on the ground', all(abs(o['p'][2] - level) < 12 for o in props))
