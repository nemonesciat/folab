"""Roads that lie in the ground (roadbed.py): after the land under two crossing roads has been knocked about, every piece
is laid on it again and the land brought up to each, so no piece shows its sides; what stood there goes with the ground,
and the ground under a building stays."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import navgen  # noqa: E402
import project  # noqa: E402
import roadbed  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


# a piece's turn: along the road rising, leaning to one side
rot = roadbed._turn_plane(0.6, 0.8, 0.1, 0.05)
R = navgen._turn(*rot)
along = (R[0][0], R[1][0], R[2][0])
side = (R[0][1], R[1][1], R[2][1])
check('a piece is turned along its road, rising with it', abs(along[2] / math.hypot(along[0], along[1]) - 0.1) < 0.002 and abs(along[0] / along[1] - 0.75) < 0.002, along)
check('and leans as the ground does', abs(side[2] / math.hypot(side[0], side[1]) - 0.05) < 0.002, side)
check('level ground, a level piece', all(abs(v) < 1e-9 for v in roadbed._turn_plane(1.0, 0.0, 0.0, 0.0)))

gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
g0 = roadgen.Ground(gd, None, world)


def flat(k):
    hs = [h for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2) for h in (g0.cell((k[0] + dx, k[1] + dy)) or [None])]
    return None not in hs and max(hs) - min(hs) < 500 and min(hs) > 2000


xy = next(k for k in sorted(grid) if flat(k))
ox, oy = xy[0] * 4096.0, xy[1] * 4096.0
pr = project.Project.create('Road Bed')
# two roads that cross
for a, b, seed in (([ox + 300, oy + 2000], [ox + 7600, oy + 2300], 1), ([ox + 3900, oy + 200], [ox + 4200, oy + 7000], 2)):
    ops, rep = roadgen.road_ops(gd, pr, world, {'a': a, 'b': b, 'settle': True, 'seed': seed})
    pr.apply('road', ops)
g1 = roadgen.Ground(gd, pr, world)
first = roadbed.gaps(gd, pr, world)
check('two roads are laid', len(first) > 12, len(first))
check('as laid, a road already lies in the ground', sorted(a for a, b in first)[len(first) // 2] < 26, sorted(round(a) for a, b in first)[-5:])
# then the land is knocked about, as levelling plots and easing ground does: a wide swell and hollows, in whole steps
rng = random.Random(4)
lops = []
for k in [(xy[0] + i, xy[1] + j) for i in (0, 1) for j in (0, 1)]:
    ck = gd.key(grid[k])
    form = dict(pr.land[ck]) if ck in pr.land else None
    if not form:
        continue
    h = list(form['h'])
    for r in range(33):
        for c in range(33):
            x, y = k[0] * 4096 + c * 128, k[1] * 4096 + r * 128
            h[r * 33 + c] += round((48 * math.sin(x / 700.0) * math.cos(y / 900.0)) / 8) * 8.0
    lops.append({'op': 'land', 'cell': ck, 'land': dict(form, h=h)})
pr.apply('rough', lops)
tire = gd.key(next(f for f, (i, r) in gd.forms.items() if gd.edid(f) == 'Tire01Static'))
g2 = roadgen.Ground(gd, pr, world)
tx, ty = ox + 2000.0, oy + 2080.0
hx, hy = ox + 6000.0, oy + 2250.0                           # (a building beside the first road)
ck0 = gd.key(grid[xy])
pr.apply('add', [{'op': 'add', 'cell': ck0, 'base': tire, 'p': [tx, ty, g2.at(tx, ty), 0.0, 0.0, 0.0], 's': 1}])
rough = roadbed.gaps(gd, pr, world)
check('knocked about, pieces hang over the ground and sink in it', sum(1 for a, b in rough if a > 32) > 4 and min(b for a, b in rough) < -20,
      (sum(1 for a, b in rough if a > 32), round(min(b for a, b in rough))))
keep = [(hx, hy, 0.0, -300.0, -300.0, 300.0, 300.0)]
held = [(hx + dx, hy + dy, g2.at(hx + dx, hy + dy)) for dx in (-256, 0, 256) for dy in (-256, 0, 256)]
ops, rep = roadbed.bed(gd, pr, world, keep)
check('it says what it did', rep['pieces'] == len(first) and rep['relaid'] > 10 and rep['cells'] >= 2 and rep['reseated'] >= 1, rep)
check('only land and moves', {o['op'] for o in ops} == {'land', 'move'}, {o['op'] for o in ops})
pr.apply('bed', ops)
g3 = roadgen.Ground(gd, pr, world)
after = roadbed.gaps(gd, pr, world)
away = lambda p: math.hypot(p[0] - hx, p[1] - hy) > 1500
boxes = roadbed._flat_bases(gd)
pieces = [r for c in pr.cells.values() for r in c['refs'].values() if r.get('base') in boxes]
check('no piece is left with a side showing', max(a for a, b in after) <= 32 or sum(1 for a, b in after if a > 32) <= 1, sorted(round(a) for a, b in after)[-5:])
check('nor under the ground', min(b for a, b in after) > -16, sorted(round(b) for a, b in after)[:5])
mid = [r['p'][2] - g3.at(r['p'][0], r['p'][1]) for r in pieces if away(r['p'])]
check('each stands sunk in it as the game\'s do', all(6 <= v <= 26 for v in mid), (round(min(mid)), round(max(mid))))
t = next(r for c in pr.cells.values() for r in c['refs'].values() if r.get('base') == tire)
check('what stood on the road went with the ground', abs(t['p'][2] - g3.at(tx, ty)) < 3, (t['p'][2], g3.at(tx, ty)))
check('the ground under a building stays', all(abs(g3.at(x, y) - z) < 0.01 for x, y, z in held))
lean = [abs(navgen._turn(*r['p'][3:])[2][1]) for r in pieces]
check('pieces stay level side to side unless the ground leans', sum(1 for v in lean if v < 0.001) > len(lean) * 0.4 and max(lean) <= math.sin(math.atan(roadbed.LEAN)) + 0.01,
      (sum(1 for v in lean if v < 0.001), len(lean), round(max(lean), 3)))
ops2, rep2 = roadbed.bed(gd, pr, world, keep)
check('done again, next to nothing moves', rep2['points'] < rep['points'] * 0.2, (rep['points'], rep2['points']))
