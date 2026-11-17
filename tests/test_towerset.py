"""The Kilauea (towerset), FOLab's own great tower where the Lucky 38 stood: it builds and checks, is as tall and as wide
as the Lucky 38, has a far model and its own worn pictures, and landmarks stands it as a set: the mod gets its files and
a STAT of its own, the tower stands on levelled ground with its lights, and what comes after keeps off it."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import landmarks  # noqa: E402
import modelmake  # noqa: E402
import modelsets  # noqa: E402
import nifmake  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402
import towerset  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


m = modelsets.build('kilauea')
wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
check('it builds, every block checked, under MOST_BUILDING triangles', not wrong and m['triangles'] < modelmake.MOST_BUILDING, (m['triangles'], wrong))
b = m['box']
check('as tall as the Lucky 38 (8900) and about as wide (6800)', 8500 < b[5] < 10500 and 6000 < b[3] - b[0] < 8000, b)
check('it has a far model', bool(m.get('far')) and m['far']['triangles'] < m['triangles'])
own = [t for t in m['textures'] if 'kil_' in t]
check('its own worn pictures go with it', len(own) >= 7 and all(t in m['files'] for t in m['textures']), own)

gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
g0 = roadgen.Ground(gd, None, world)


def flat(k):
    hs = [h for dx in (-1, 0, 1) for dy in (-1, 0, 1) for h in (g0.cell((k[0] + dx, k[1] + dy)) or [None])]
    return None not in hs and max(hs) - min(hs) < 700 and min(hs) > 2000


xy = next(k for k in sorted(grid) if flat(k))
x, y = xy[0] * 4096.0 + 2048, xy[1] * 4096.0 + 2048
pr = project.Project.create('Tower')
B = landmarks.Batch(gd, pr, world)
rep = B.stand('kilauea', x, y, turn=0.0, scale=0.8, nudge=0)
ops = B.done()
check('it stands as a landmark set', rep and rep['label'] == 'The Kilauea' and rep['scale'] == 0.8, rep)
check('its record is made first, the tower placed by it', ops[0]['op'] == 'record_new' and any(o['op'] == 'add' and o['base'] == '$model_kilauea' and o['s'] == 0.8 for o in ops))
lights = [o for o in ops if o['op'] == 'add' and o['base'] != '$model_kilauea']
check('with its lights, the flame\'s high up', len(lights) >= 3 and max(o['p'][2] for o in lights) > rep['level'] + 0.8 * 8000, len(lights))
pr.apply('landmark', ops)
rk = modelsets.record_of(pr, 'kilauea')
check('the mod has a STAT of its own for it, and its files', rk and pr.records[rk]['type'] == 'STAT'
      and os.path.isfile(os.path.join(__import__('library').assets_dir(pr), 'meshes', 'folab', 'resort', 'kilauea.nif')), rk)
keep = landmarks.standing(gd, pr, world)
hit = [k for k in keep if math.hypot(k[0] - rep['x'], k[1] - rep['y']) < 1 and k[5] - k[3] > 0.8 * 6000]
check('what comes after keeps off it', bool(hit), keep[:3])
B2 = landmarks.Batch(gd, pr, world)
B2.stand('kilauea', x + 30000, y, nudge=0)
check('stood again, the record already there is used, not made twice', not any(o['op'] == 'record_new' for o in B2.done()))
