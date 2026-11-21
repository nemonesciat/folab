"""plantgrass.clear_under: no engine grass up through things the mod stands on grass-bearing ground (the user, 21 Nov
2026: grass through a beach lounger). Checked with grassrule's model of where the game stands grass: none under the
footprint after, still grass away from it, and the picture's strength unchanged (the grassy layer's strength moves to
its plain twin)."""
import copy
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import grassrule  # noqa: E402
import plantgrass as pg  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def dens(key):
    return [0.5] if key in ('G', 'BG') else []


def grows(key):
    return bool(dens(key))


def plain(key):
    return {'G': 'P', 'BG': 'BP'}.get(key)


def lounger(x, y, turn=0.0, long=100):
    """A beach lounger's footprint (200 x 80) widened as clear_under widens it."""
    j = pg.JITTER
    return (x, y, math.cos(turn), math.sin(turn), -40 - j, -long - j, 40 + j, long + j)


def thick_at(quarter, pts):
    out = grassrule.predict(quarter, dens)
    return max(out[j * 17 + i] for i, j in pts)


# under the lounger: the quarter points within its footprint (it stands at the middle of quarter 0, point 8, 8)
UNDER = [(i, j) for i in (8,) for j in (7, 8, 9)]
FAR = [(2, 2), (14, 14), (2, 14)]

# ---------- a grass-bearing layer over a plain base ----------
form = {'q': [{'bkey': 'B', 'layers': [{'key': 'G', 'a': [0.9] * 289}]} for _ in range(4)]}
before = copy.deepcopy(form)
check('grass under the lounger before', thick_at(form['q'][0], UNDER) > 0)
hits = pg.points_under(lounger(1024.0, 1024.0))
check('only cell 0, 0 is touched', set(hits) == {(0, 0)}, sorted(hits))
rep = {}
changed = pg.clear_points(form, hits[(0, 0)], grows, plain, rep)
q0 = form['q'][0]
check('the form changed', changed)
check('no grass under the lounger after', thick_at(q0, UNDER) == 0, thick_at(q0, UNDER))
check('grass still away from it', thick_at(q0, FAR) > 0)
pl = next((l for l in q0['layers'] if l['key'] == 'P'), None)
check('the plain twin took the strength', pl is not None and all(
    abs(sum(l['a'][n] for l in q0['layers']) - before['q'][0]['layers'][0]['a'][n]) < 1e-9 for n in range(289)))
check('the other quarters untouched', form['q'][1:] == before['q'][1:])
cleared = sum(1 for n in range(289) if q0['layers'][0]['a'][n] == 0.0)
check('a small bare patch, not the whole quarter', 0 < cleared <= 36, cleared)
check('only sample points cleared (never an edge or a 4th row)',
      all(n % 17 % 4 and n // 17 % 4 for n in range(289) if q0['layers'][0]['a'][n] == 0.0))

# ---------- a grass-bearing base ----------
form = {'q': [{'bkey': 'BG', 'layers': []} for _ in range(4)]}
check('base grass under the lounger before', thick_at(form['q'][0], UNDER) > 0)
pg.clear_points(form, hits[(0, 0)], grows, plain, {})
check('base grass covered by its plain twin', thick_at(form['q'][0], UNDER) == 0
      and form['q'][0]['layers'][0]['key'] == 'BP')
check('base grass still away from it', thick_at(form['q'][0], FAR) > 0)

# ---------- no twin, no room: the grass still goes, and the report says so ----------
form = {'q': [{'bkey': 'B', 'layers': [{'key': 'G', 'a': [0.9] * 289}] + [{'key': 'L%d' % k, 'a': [0.01] * 289}
                                                                         for k in range(5)]} for _ in range(4)]}
rep = {}
pg.clear_points(form, hits[(0, 0)], grows, plain, rep)
check('six layers full: cleared all the same', thick_at(form['q'][0], UNDER) == 0 and rep.get('cleared with no plain twin'))

# ---------- turned, and over a cell corner ----------
straight = pg.points_under(lounger(1024.0, 1024.0, long=500))[(0, 0)]
turned = pg.points_under(lounger(1024.0, 1024.0, math.pi / 2, long=500))[(0, 0)]
check('a quarter turn clears the turned spots', straight != turned and
      {(q, (n % 17) * 17 + n // 17) for q, n in straight} == turned)
corner = pg.points_under(lounger(4096.0, 4096.0))
check('a thing on a cell corner clears all four cells', set(corner) == {(0, 0), (1, 0), (0, 1), (1, 1)}, sorted(corner))
check('a far square is not touched', not pg._overlaps(0.0, 0.0, pg.INFLUENCE, lounger(1024.0, 1024.0)))

# ---------- against the game's own grounds ----------
import gamedata  # noqa: E402
import project  # noqa: E402
gd = gamedata.GameData()
pr = project.Project.create('Grass Under')
lt = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX'}
g_grows, g_plain = pg.ltex_rules(gd, pr)
lawn, bare = lt.get('LGrassGreenSuburbs'), lt.get('LGrassGreenSuburbsNoGrass')
check("the game's lawn grows grass, its NoGrass twin doesn't", lawn and g_grows(lawn) and not g_grows(bare))
check("the lawn's plain twin is LGrassGreenSuburbsNoGrass", g_plain(lawn) == bare, g_plain(lawn))

# a lounger-sized thing placed on lawn painted over a Mojave cell
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
xy = (0, 0) if (0, 0) in grid else sorted(grid)[0]
ck = gd.key(grid[xy])
import land  # noqa: E402
import roadgen  # noqa: E402
form = land.decode(gd, gd.land_at(world, *xy), {})
for q in form['q']:
    q['layers'] = [{'key': lawn, 'tex': '', 'a': [0.9] * 289}]
pr.apply('lawn', [{'op': 'land', 'cell': ck, 'land': form}])
bench = next(gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'FURN' and 'bench' in (gd.edid(f) or '').lower()
             and gd.fields(f).get('OBND'))
x, y = xy[0] * 4096 + 1024.0, xy[1] * 4096 + 1024.0
z = roadgen.Ground(gd, pr, world).at(x, y)
pr.apply('bench', [{'op': 'add', 'cell': ck, 'base': bench, 'p': [x, y, z, 0.0, 0.0, 0.0], 's': 1.0}])
gdens = grassrule.densities(gd, pr)
q0 = pr.land[ck]['q'][0]
import struct  # noqa: E402
ob = struct.unpack_from('<6h', gd.fields(gd.from_key(bench))['OBND'])
# the quarter's points under the bench, and every spot between them (predict's points are 128 apart: sample finer)
ON = [(i / 4.0, j / 4.0) for i in range(65) for j in range(65)
      if ob[0] <= i * 32 + xy[0] * 4096 - x <= ob[3] and ob[1] <= j * 32 + xy[1] * 4096 - y <= ob[4]]


def thick_on(quarter):
    out = grassrule.predict(quarter, gdens)

    def at(i, j):
        i0, j0 = min(15, int(i)), min(15, int(j))
        ti, tj = i - i0, j - j0
        return ((out[j0 * 17 + i0] * (1 - ti) + out[j0 * 17 + i0 + 1] * ti) * (1 - tj)
                + (out[(j0 + 1) * 17 + i0] * (1 - ti) + out[(j0 + 1) * 17 + i0 + 1] * ti) * tj)
    return max(at(i, j) for i, j in ON)


was = thick_on(q0)
ops, rep = pg.clear_under(gd, pr, world, cells={ck})
check("clear_under found the bench", rep.get("things on the ground") == 1, rep)
check('one land op for its cell', len(ops) == 1 and ops[0]['cell'] == ck, [o['cell'] for o in ops])
after = thick_on(ops[0]['land']['q'][0]) if ops else None
check('lawn grass under the bench before, none after', ON and was > 0 and after == 0, (len(ON), was, after))
check('the mod itself is not changed by asking', pr.land[ck]['q'][0]['layers'][0]['a'][8 * 17 + 8] == 0.9)
high = copy.deepcopy(pr.cells[ck]['refs'])
for r in pr.cells[ck]['refs'].values():
    r['p'] = [x, y, z + 500.0, 0.0, 0.0, 0.0]
ops2, rep2 = pg.clear_under(gd, pr, world, cells={ck})
check('a thing well off the ground is left out', not ops2 and not rep2.get('things on the ground'), rep2)
pr.cells[ck]['refs'] = high
