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

# ---------- the plots nothing was built on ----------
ring = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
lots = [{'ring': ring(x + 3000, y + 600, x + 4400, y + 1700), 'pad': True},        # empty, big
        {'ring': ring(x - 300, y - 300, x + 300, y + 300), 'pad': True},            # the building stands on it
        {'ring': ring(x - 4000, y + 600, x - 3700, y + 900), 'pad': True},          # empty, tiny
        {'ring': ring(x + 3000, y + 3000, x + 4000, y + 4000), 'pad': False}]       # never levelled: not a plot
found = {}
for seed in range(1, 7):
    lops, lrep = osmdress.lots(gd, pr, world, Cover('paved'), cat, lots, seed)
    for o in lops:
        k = 'big' if o['p'][0] > x + 2000 else 'tiny' if o['p'][0] < x - 2000 else 'other'
        found.setdefault(k, []).append(o)
    last = lrep
check('two plots stand empty, the one with a building and the one never levelled apart', last['empty'] == 2, last)
check('the empty plots are filled, the others left', len(found.get('big', [])) > 12 and len(found.get('tiny', [])) >= 2 and 'other' not in found,
      {k: len(v) for k, v in found.items()})
check('everything is on its own plot', all(x + 2900 <= o['p'][0] <= x + 4500 and y + 500 <= o['p'][1] <= y + 1800 for o in found['big'])
      and all(x - 4100 <= o['p'][0] <= x - 3600 and y + 500 <= o['p'][1] <= y + 1000 for o in found['tiny']))
under = [o['p'][2] + townbuild.obnd(gd, o['base'])[2] - level for o in found['big'] + found['tiny']]
check('each thing\'s underside is on the ground, a little in', all(-12 <= u <= 2 for u in under), (min(under), max(under)))
kinds = {edid(o) for o in found['big']}
check('a big plot takes more than rubble: a ruin, a trailer, a wall, wrecks', len(kinds & {'HouseRuined02', 'HouseRuined03', 'HouseRuined04b', 'HouseRuined04c', 'TruckTrailer01',
      'TruckTrailer03', 'TruckTrailer04', 'TruckTrailer06', 'UrbanCourtyardwallStr01', 'UrbanCourtyardwallStr02', 'Car01HulkBodyStatic', 'ScaffoldDestroyed01'}) >= 3, sorted(kinds))
check('a tiny one only a heap', {edid(o) for o in found['tiny']} <= {'SuburbanRubblePileSm01', 'ConcreteSlab01', 'Barrel01', 'RubblePile02', 'SuburbanRubblePile01bLiteLitter',
      'RoadChunkCluster01', 'SWSingleRubble'}, sorted({edid(o) for o in found['tiny']}))

# ---------- what grows ----------
# woods are thick with the game's own green, some of it grown far past its size, in clumps; a road stays clear
wops, wrep = osmdress.ops(gd, project.Project.create('Green'), world, Cover('trees'), [], 3)
green = [o for o in wops if o['op'] == 'add']
names = {k: gd.edid(gd.from_key(k)) for k in {o['base'] for o in green}}
in_plants = {e.lower() for e, *_r in osmdress.PLANTS['trees'][1]}
mine = [o for o in green if names[o['base']].lower() in in_plants]
check('woods are planted thick', wrep['plants'] >= 150 and len(mine) >= 150, (wrep['plants'], len(mine)))
check('with trees, ferns and more: many kinds', len({o['base'] for o in mine}) >= 10, len({o['base'] for o in mine}))
check('some grown far past their size', max(o['s'] for o in mine) > 3 and min(o['s'] for o in mine) >= 0.5, (min(o['s'] for o in mine), max(o['s'] for o in mine)))
road_top = (int(y // 128) - 60 + 45) * 128.0
check('none on the road', not any(o['p'][1] < road_top - 64 and abs(o['p'][0] - x) < 60 * 128 and o['p'][1] > (int(y // 128) - 60) * 128.0 for o in mine))
fern = next(k for k, e in names.items() if e.lower() == 'v22fern')
ferns = [o['p'] for o in green if o['base'] == fern]
close = sum(1 for a in ferns if any(a is not b and math.hypot(a[0] - b[0], a[1] - b[1]) < 2 * osmdress.CLUMP_OUT[1] for b in ferns))
check('small plants stand in clumps', ferns and close >= len(ferns) * 0.5, (close, len(ferns)))
pops, prep = osmdress.ops(gd, project.Project.create('Grey'), world, Cover('paved'), [], 3)
check('a paved place has weeds in its cracks, far fewer', 0 < prep['plants'] < wrep['plants'] * 0.3, (prep['plants'], wrep['plants']))

# ---------- what lies on a slope ----------
import navgen  # noqa: E402


class Hill:
    def at(self, px, py):
        return 0.3 * px + 0.1 * py


for yaw in (0.0, 0.7, 2.9):
    R = navgen._turn(*osmdress.lie(Hill(), 'RubblePile02', 0.0, 0.0, yaw))
    up = (R[0][2], R[1][2], R[2][2])
    n = math.sqrt(0.3 ** 2 + 0.1 ** 2 + 1)
    check('rubble on a hillside lies along it, whichever way it faces (%.1f)' % yaw, all(abs(u - v) < 0.01 for u, v in zip(up, (-0.3 / n, -0.1 / n, 1 / n))), [round(v, 3) for v in up])
check('a barrel stands upright there', osmdress.lie(Hill(), 'Barrel01', 0.0, 0.0, 1.0) == (0.0, 0.0, 1.0))


class Level:
    def at(self, px, py):
        return 100.0


check('and on level ground nothing is tilted', osmdress.lie(Level(), 'RubblePile02', 0.0, 0.0, 1.0) == (0.0, 0.0, 1.0))


# ---------- what lies is laid on the ground ----------
lp = project.Project.create('Lying')
bases = osmdress._bases(gd)
lx0, ly0 = x + 1500, y + 1500
lops = []
for k, e in enumerate(('RubblePile02', 'SWSingleRubble', 'SuburbanRubblePileSm01')):
    px, py = lx0 + k * 600, ly0
    lops.append({'op': 'add', 'cell': gd.key(grid[(int(px // 4096), int(py // 4096))]), 'base': bases[e.lower()], 'p': [px, py, g0.at(px, py) + 30.0, 0.0, 0.0, 0.4], 's': 1.0})
# (and one well up, as on a roof: left where it is)
lops.append({'op': 'add', 'cell': gd.key(grid[(int(lx0 // 4096), int((ly0 + 900) // 4096))]), 'base': bases['rubblepile02'], 'p': [lx0, ly0 + 900, g0.at(lx0, ly0 + 900) + 400.0, 0.0, 0.0, 0.0], 's': 1.0})
pr2 = lp
pr2.apply('lying', lops)
sops, srep = osmdress.seat_lying(gd, pr2, world)
check('things left hanging over the ground are laid on it or taken out', srep['laid'] + srep['taken_out'] == 3 and srep['looked'] == 3, srep)
pr2.apply('seat', sops)
again, arep = osmdress.seat_lying(gd, pr2, world)
check('done again, nothing more to do', arep['laid'] == 0 and arep['taken_out'] == 0, arep)
check('boards over a doorway are not ground litter', not osmdress.LIES.search('woodplanksgroup01') or osmdress.NOT_LIES.search('woodplanksgroup01'))
