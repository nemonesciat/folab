import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Land shaping: each shape does what it says on flat ground, only marked cells change, the edge with an unmarked
cell keeps its height exactly, held ground under a building stays, and on the game's land a ridge rises where drawn."""
import gamedata, land, tes4, landshape


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


flat = lambda cx, cy: [1000.0] * 1089
at = lambda new, cell, r, c: new[cell][r * 33 + c]
marked = {(x, y) for x in range(0, 4) for y in range(0, 4)}
mid = (2 * 4096, 2 * 4096)          # the middle of the 4 x 4 cells: point (0, 0) of cell (2, 2)
def run(shape, **kw):
    plan = dict({'shapes': [shape], 'rough': 0, 'fade': 2048, 'hold': False}, **kw)
    return landshape.shape(plan, flat, marked)
n = run({'kind': 'hill', 'pts': [list(mid)], 'height': 1000, 'radius': 3000})
check('a hill: its top 1000 up in the middle', abs(at(n, (2, 2), 0, 0) - 2000) < 1)
check('… and nothing at the marked area\'s edge', at(n, (0, 0), 0, 0) == 1000 and at(n, (3, 3), 32, 32) == 1000)
n = run({'kind': 'valley', 'pts': [[mid[0] - 3000, mid[1]], [mid[0] + 3000, mid[1]]], 'depth': 500, 'width': 2000})
check('a valley: 500 down along its floor', abs(at(n, (2, 2), 0, 0) - 500) < 1)
n = run({'kind': 'plateau', 'pts': [[mid[0] - 3000, mid[1] - 3000], [mid[0] + 3000, mid[1] - 3000], [mid[0] + 3000, mid[1] + 3000], [mid[0] - 3000, mid[1] + 3000]], 'height': 700, 'cliff': 256})
check('a plateau: level 700 above its ground on top', abs(at(n, (2, 2), 0, 0) - 1700) < 1 and abs(at(n, (2, 2), 8, 8) - 1700) < 1)
n = run({'kind': 'crater', 'pts': [list(mid)], 'height': 800, 'radius': 3000})
check('a crater: a bowl below, a rim above', at(n, (2, 2), 0, 0) < 400 and max(n[(2, 2)]) > 1100 or max(max(v) for v in n.values()) > 1100)
n = run({'kind': 'ridge', 'pts': [[mid[0] - 4000, mid[1]], [mid[0] + 4000, mid[1]]], 'height': 1200, 'width': 2500}, rough=0.5)
check('rolling ground only where the shapes reach', all(v == 1000 for v in n[(0, 3)][:33]))
# holding a building's ground
box = (mid[0] - 300, mid[1] - 300, mid[0] + 300, mid[1] + 300)
n = landshape.shape({'shapes': [{'kind': 'hill', 'pts': [list(mid)], 'height': 1000, 'radius': 3000}], 'rough': 0, 'fade': 2048, 'hold': True, 'margin': 512}, flat, marked, [box])
check('the ground under a building is held', at(n, (2, 2), 0, 0) == 1000)
check('… and the hill comes back away from it', at(n, (2, 2), 0, 10) > 1300)
# the cells a shape reaches
cells = landshape.cells_reached({'kind': 'ridge', 'pts': [[0, 0], [20000, 0]], 'width': 2000})
check('a ridge reaches the cells along it', (0, 0) in cells and (4, 0) in cells and (2, 3) not in cells)
# on the game's own land
gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
def base(cx, cy):
    e = gd.land_at(w, cx, cy)
    return land.heights_of(dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1])))['VHGT']) if e else None
plan = {'shapes': [{'kind': 'ridge', 'pts': [[-60000, 8000], [-52000, 14000]], 'height': 1500, 'width': 2500, 'sharp': 0.4}], 'rough': 0.3, 'seed': 1, 'fade': 1024}
m = landshape.cells_reached(plan['shapes'][0])
new = landshape.shape(plan, base, m)
check('on the Mojave: the ridge rises about 1500', 1300 < max(max(a - b for a, b in zip(new[k], base(*k))) for k in new) < 1800)
check('… and its edges with unmarked cells keep their heights', all(new[k][i] == base(*k)[i] for k in new for i in range(33) if (k[0], k[1] - 1) not in m))
# water: a lake dug in flat ground, its water under its shore; a river running downhill on the Mojave
ring = [[mid[0] - 3000, mid[1] - 3000], [mid[0] + 3000, mid[1] - 3000], [mid[0] + 3000, mid[1] + 3000], [mid[0] - 3000, mid[1] + 3000]]
n, wat = landshape.shape_all({'shapes': [{'kind': 'lake', 'pts': ring, 'depth': 500, 'bank': 512, 'below': 32}], 'rough': 0, 'fade': 2048, 'hold': False}, flat, marked)
check('a lake: 500 deep in the middle, below its water', abs(at(n, (2, 2), 0, 0) - (1000 - 32 - 500)) < 1)
check('… its water just under the shore, in every cell it touches', wat.get((2, 2)) == 968 and wat.get((1, 1)) == 968)
check('… the ground outside it as it was', at(n, (0, 0), 16, 16) == 1000)
river = {'kind': 'river', 'pts': [[-60000, 8000], [-52000, 14000]], 'depth': 300, 'width': 800}
m2 = landshape.cells_reached(river)
n, wat = landshape.shape_all({'shapes': [river], 'rough': 0, 'seed': 1, 'fade': 1024, 'hold': False}, base, m2)
lv = [wat[k] for k in sorted(wat, key=lambda k: (k[0] + k[1]))]
check('a river: water in the cells along it (%d)' % len(wat), len(wat) >= 3)
check('… each cell\'s water no higher than upstream', all(a >= b - 1 for a, b in zip(lv, lv[1:])) or len(set(lv)) == 1)
check('… its bed below its water', all(min(n[k]) < wat[k] for k in wat))
