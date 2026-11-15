"""Ground people can walk (landsoft.py): a spike and a ledge the mod's shaping left are eased to a slope, what stood on
them goes with the ground, the ground under a building stays, and land the mod never touched is left alone."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import land  # noqa: E402
import landsoft  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
# a square of flat-ish land well above water, with land all round it
g0 = roadgen.Ground(gd, None, world)


def flat(k):
    hs = [h for dx in (-1, 0, 1) for dy in (-1, 0, 1) for h in (g0.cell((k[0] + dx, k[1] + dy)) or [None])]
    return None not in hs and max(hs) - min(hs) < 500 and min(hs) > 2000


xy = next(k for k in sorted(grid) if flat(k))
cell = grid[xy]
key = gd.key(cell)
pr = project.Project.create('Soft Ground')
form = land.decode(gd, gd.land_at(world, *xy), {})
before = list(form['h'])
h = list(before)
h[10 * 33 + 10] += 640.0                                   # a spike a point wide
for r in range(18, 26):
    for c in range(4, 28):
        h[r * 33 + c] = before[18 * 33 + 4] + 480.0        # a plot levelled high: a ledge all round it
form['h'] = h
pr.apply('land', [{'op': 'land', 'cell': key, 'land': form}])
base = next(f for f, (i, r) in gd.forms.items() if gd.edid(f) == 'Tire01Static')
sx, sy = xy[0] * 4096.0 + 10 * 128, xy[1] * 4096.0 + 10 * 128
px, py = xy[0] * 4096.0 + 16 * 128, xy[1] * 4096.0 + 22 * 128
ex, ey = xy[0] * 4096.0 + 4 * 128, xy[1] * 4096.0 + 20 * 128
g1 = roadgen.Ground(gd, pr, world)
pr.apply('add', [{'op': 'add', 'cell': key, 'base': gd.key(base), 'p': [sx, sy, g1.at(sx, sy), 0.0, 0.0, 0.0], 's': 1},
                 {'op': 'add', 'cell': key, 'base': gd.key(base), 'p': [px, py, g1.at(px, py), 0.0, 0.0, 0.0], 's': 1},
                 {'op': 'add', 'cell': key, 'base': gd.key(base), 'p': [ex, ey, g1.at(ex, ey), 0.0, 0.0, 0.0], 's': 1}])
ops, rep = landsoft.soften(gd, pr, world, keep=[(px, py, 0.0, -400.0, -200.0, 400.0, 200.0)])
check('something was eased', rep['eased'] > 20 and rep['cells'] >= 1, rep)
only = {o['cell'] for o in ops if o['op'] == 'land'}
near = {gd.key(grid[(xy[0] + dx, xy[1] + dy)]) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
check('only round what the mod shaped', only <= near and key in only, len(only))
pr.apply('soften', ops)
g2 = roadgen.Ground(gd, pr, world)
after = pr.land[key]['h']
check('the spike is gone', after[10 * 33 + 10] - before[10 * 33 + 10] < 120, after[10 * 33 + 10] - before[10 * 33 + 10])
steps = []
for r in range(1, 32):
    for c in range(1, 32):
        if (c * 128 + xy[0] * 4096 - px) ** 2 + (r * 128 + xy[1] * 4096 - py) ** 2 > 700 ** 2 and after[r * 33 + c] != h[r * 33 + c]:
            steps.append(max(abs(after[r * 33 + c] - after[r * 33 + c + 1]), abs(after[r * 33 + c] - after[(r + 1) * 33 + c])))
check('no step left that a person can\'t walk', max(steps) <= landsoft.MAX_STEP + 8, max(steps))
check('heights are whole steps', all(v % 8 == 0 for v in after))
check('the ground under the building is as it was', all(abs(g2.at(px + dx, py + dy) - g1.at(px + dx, py + dy)) < 0.01 for dx in (-300, 0, 300) for dy in (-200, 0, 200)))
refs = list(pr.cells[key]['refs'].values())
on_spike = next(r for r in refs if r['p'][:2] == [sx, sy])
by_wall = next(r for r in refs if r['p'][:2] == [px, py])
on_edge = next(r for r in refs if r['p'][:2] == [ex, ey])
check('the thing on the spike came down with it', abs(on_spike['p'][2] - g2.at(sx, sy)) < 1.0 and on_spike['p'][2] < g1.at(sx, sy) - 400, on_spike['p'][2])
check('the thing on the ledge\'s edge is still on the ground', abs(on_edge['p'][2] - g2.at(ex, ey)) < 1.0, (on_edge['p'][2], g2.at(ex, ey)))
check('the thing by the building did not move', by_wall['p'][2] == g1.at(px, py))
again, rep2 = landsoft.soften(gd, pr, world, keep=[(px, py, 0.0, -400.0, -200.0, 400.0, 200.0)])
check('a second go finds next to nothing to do', rep2['eased'] < rep['eased'] / 10, rep2)
pr2 = project.Project.create('Untouched')
check('land the mod never shaped is left alone', landsoft.soften(gd, pr2, world) == ([], {'eased': 0, 'cells': 0, 'reseated': 0}))
