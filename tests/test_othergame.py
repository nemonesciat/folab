"""A ship out of Fallout 3 (othergame.py): the carrier read as that game stands it, its files copied into the mod's own,
a static of the mod's for each model, the set stood in the sea; and the files taken out again. Needs Fallout 3 in a
Steam library: without it there is nothing to test, and the test says so and passes."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import library  # noqa: E402
import othergame  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


where = othergame.find('carrier')
check('a game still being installed is not one to read', 'downloading' not in (where or '').lower())
if not where:
    print('PASS Fallout 3 is not installed here: nothing more to check')
    sys.exit(0)
other = othergame.open_game('carrier')
got = othergame.lift(other, 'carrier')
names = [p[0] for p in got['pieces']]
check('the carrier is its hull, its two ends and its tower', {'RCExtAirCarrier01', 'RCExtAirCarrierBack', 'RCExAirCarrierFront', 'RCAirCarrierTower'} <= set(names), sorted(set(names)))
check('without the bridge to a shore that isn\'t here', not any('Bridge' in n for n in names))
box = got['box']
check('it lies along its length, as long as a carrier', 18000 < box[2] - box[0] < 30000 and box[3] - box[1] < (box[2] - box[0]) * 0.4, [round(v) for v in box])
hull = next(p for p in got['pieces'] if p[0] == 'RCExtAirCarrier01')
check('and floats: its hull\'s origin over the water, its keel well under', 500 < hull[4] < 2000 and got['draught'] > 500, (hull[4], got['draught']))

gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
pr = project.Project.create('Ship')
gd.overlay = library.Overlay(lambda: pr)
k = next(k for k in sorted(grid))
x, y = k[0] * 4096.0 + 2048, k[1] * 4096.0 + 2048
ops, rep = othergame.stand(gd, pr, world, 'carrier', x, y, 0.5, other)
root = library.assets_dir(pr)
mine = othergame.borrowed(pr).get('Fallout 3', [])
check('its models and textures are copied into the mod\'s own files', rep['copied'] == len(mine) >= 20 and all(os.path.isfile(os.path.join(root, r)) for r in mine), (rep['copied'], rep['files']))
check('meshes, far models and textures with their normal maps', any(r.endswith('_lod.nif') for r in mine) and any(r.endswith('_n.dds') for r in mine)
      and any(r.endswith('rcextaircarrier01.nif') for r in mine))
check('nothing New Vegas has under the same name', not any(r in a.files for r in mine for a in gd.archives()))
made = [o for o in ops if o['op'] == 'record_new']
adds = [o for o in ops if o['op'] == 'add']
check('a static of the mod\'s own for each model, every piece placed of one', len(made) == rep['kinds'] and len(adds) == rep['pieces'] == len(got['pieces'])
      and all(o['base'].startswith('$og_') for o in adds), (len(made), len(adds)))
pr.apply('ship', ops)
refs = [r for c in pr.cells.values() for r in c['refs'].values()]
check('placed, each names the record made for it', len(refs) == len(adds) and all(r['base'] in pr.records for r in refs), sorted({r['base'] for r in refs})[:3])
rec = pr.records[next(r['base'] for r in refs if abs(r['p'][0] - x) + abs(r['p'][1] - y) < 3000)]
check('the record is a static with the model and its bounds', rec['type'] == 'STAT' and recordio.field(rec, 'MODL').lower().startswith('dungeons\\rivetcity\\exterior\\')
      and recordio.field(rec, 'EDID').startswith('FOLab'), recordio.field(rec, 'EDID'))
h = next(r for r in refs if recordio.field(pr.records[r['base']], 'EDID') == 'FOLabRCExtAirCarrier01')
tx, ty = hull[2] * math.cos(0.5) + hull[3] * math.sin(0.5), -hull[2] * math.sin(0.5) + hull[3] * math.cos(0.5)
check('the set is turned about its middle as one', abs(h['p'][0] - (x + tx)) < 1 and abs(h['p'][1] - (y + ty)) < 1 and abs((h['p'][5] - hull[7] - 0.5) % math.tau) < 0.001)
ops2, rep2 = othergame.stand(gd, pr, world, 'carrier', x + 30000, y, 0.0, other)
check('stood again, the same records and files serve', not any(o['op'] == 'record_new' for o in ops2) and rep2['copied'] == 0)
n = othergame.remove_borrowed(pr)
check('the other game\'s files come out again, all of them', n == len(mine) and not any(os.path.isfile(os.path.join(root, r)) for r in mine) and not othergame.borrowed(pr))

# a place for it: over deep water, clear of the land
ground = roadgen.Ground(gd, None, world)


class Flat:
    """A made-up sea: land east of x = 0, deep water west of it."""
    def __init__(self):
        self.grid = {(i, j): 1 for i in range(-20, 20) for j in range(-20, 20)}

    def at(self, px, py):
        return 64.0 if px > 0 else -600.0


real = roadgen.Ground
roadgen.Ground = lambda *a: Flat()
gd2 = type('G', (), {'grid': lambda self, w: Flat().grid})()
try:
    at = othergame.where(gd2, None, None, got, (2000.0, 0.0))
finally:
    roadgen.Ground = real
far = [at[0] + px * math.cos(at[2]) + py * math.sin(at[2]) for px in (box[0], box[2]) for py in (box[1], box[3])] if at else []
check('found off the shore, all of it over the water and clear of the land', at is not None and max(far) < -othergame.OFF_SHORE + 1, (at, far and round(max(far))))
