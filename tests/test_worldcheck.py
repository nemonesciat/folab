"""The new-world checklist (worldcheck.py) on a small made-up world with no game files: a world of the mod's own with no
Pip-Boy map, then one whose picture is missing, then one that has it; no far view, then one made; a cell edge that doesn't
meet its neighbour's, and one that does; a cell with its own water over a beach beside the sea, and a real pond inland;
only the worlds the mod changed are looked at."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import library  # noqa: E402
import lodgen  # noqa: E402
import worldcheck  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


SIDE = 33
OWN, GAME = (0x05 << 24) | 0x800, 0x0DA726


class GD:
    names = {0: 'falloutnv.esm', 5: 'mine.esp'}

    def __init__(self):
        self.grids = {OWN: {(x, y): (0x05 << 24) | (0x900 + x * 10 + y) for x in range(3) for y in range(3)},
                      GAME: {(0, 0): 0x1000}}

    def worlds(self):
        return [OWN, GAME]

    def grid(self, w):
        return self.grids.get(w, {})

    def key(self, f):
        return ('Mine.esp:%06X' % (f & 0xFFFFFF)) if f >> 24 == 5 else 'FalloutNV.esm:%06X' % f

    def edid(self, w):
        return 'MyIsland' if w == OWN else 'WastelandNV'

    def fields(self, w):
        return {'FULL': b'My Island\0'} if w == OWN else {}

    def find_file(self, rel):
        return None

    def land_at(self, w, x, y):
        return None


class PR:
    plugin, name, source = 'Mine.esp', 'Mine', 'Mine source.esp'

    def __init__(self):
        self.records, self.cells, self.land, self.water = {}, {}, {}, {}


def flat(z):
    return {'h': [float(z)] * (SIDE * SIDE)}


gd, pr = GD(), PR()
key = lambda xy: gd.key(gd.grids[OWN][xy])
for xy in gd.grids[OWN]:
    pr.land[key(xy)] = flat(100)
worldcheck.check_draws = lambda gd, pr, w, progress=None: []        # (drawcount has its own test, on the game's files)

r = worldcheck.run(gd, pr)
check('only the worlds the mod changed', [w['edid'] for w in r] == ['MyIsland'], [w['edid'] for w in r])
f = {x['check']: x for x in r[0]['findings']}
check('own world, no ICON: no Pip-Boy map, the Big job offered', f['pipboy']['level'] == 'error' and f['pipboy']['fix'] == 'pipboy')
check('no far view made: said', f['far']['level'] == 'warn')
check('flat ground everywhere: no torn edges, no water', 'torn' not in f and 'water' not in f)

# a picture named but not there, then there
import recordio  # noqa: E402
rec = {'type': 'WRLD', 'subs': [{'tag': 'EDID', 'data': 'MyIsland'}, {'tag': 'ICON', 'data': 'interface\\worldmap\\folab_myisland.dds'}]}
recordio.field = lambda rec, tag: next((s['data'] for s in rec.get('subs', []) if s['tag'] == tag), None)
pr.records[gd.key(OWN)] = rec
f = {x['check']: x for x in worldcheck.run(gd, pr)[0]['findings']}
check('ICON with no picture: missing, said', f['pipboy']['level'] == 'error' and 'missing' in f['pipboy']['text'])
pic = os.path.join(library.assets_dir(pr), 'textures', 'interface', 'worldmap', 'folab_myisland.dds')
os.makedirs(os.path.dirname(pic), exist_ok=True)
open(pic, 'wb').write(b'DDS ')
lod = os.path.join(lodgen.out_folder(pr), 'meshes', 'landscape', 'lod', 'myisland')
os.makedirs(lod, exist_ok=True)
open(os.path.join(lod, 'myisland.level4.x0.y0.nif'), 'wb').write(b'x')
f = {x['check']: x for x in worldcheck.run(gd, pr)[0]['findings']}
check('with its picture: fine', f['pipboy']['level'] == 'info')
check('far view made: fine, with when', f['far']['level'] == 'info' and time.strftime('%d %b') in f['far']['text'])

# a torn edge: (1, 1) raised, its east neighbour not
pr.land[key((1, 1))] = flat(300)
f = {x['check']: x for x in worldcheck.run(gd, pr)[0]['findings']}
torn = f.get('torn')
check('torn edges found, the cells named', torn and torn['level'] == 'error' and (1, 1) in torn['cells'] and (2, 1) in torn['cells']
      and (1, 0) in torn['cells'] and (1, 2) in torn['cells'], torn and torn['cells'])
check('a cell whose edges all meet is not named (a corner across from it)', torn and (2, 2) not in torn['cells'] and len(torn['cells']) == 5, torn and torn['cells'])
check('how far apart, said', torn and '200' in torn['text'], torn and torn['text'])
for xy in gd.grids[OWN]:
    pr.land[key(xy)] = flat(100)

# water: a beach under its own level beside the sea; a pond inland in a hollow, all round it its own level too
beach = {'h': [(-200.0 if c < 16 else 150.0) for r in range(SIDE) for c in range(SIDE)]}
pr.land[key((0, 0))] = beach
pr.water[key((0, 0))] = 120.0
f = {x['check']: x for x in worldcheck.run(gd, pr)[0]['findings']}
check('water of its own over a beach by the sea: said', f.get('water') and f['water']['cells'] == [(0, 0)], f.get('water'))
pr.water.clear()
pond = {'h': [(-50.0 if 10 < c < 22 and 10 < r < 22 else 100.0) for r in range(SIDE) for c in range(SIDE)]}
pr.land[key((1, 1))] = pond
for xy in gd.grids[OWN]:
    pr.water[key(xy)] = 50.0
f = {x['check']: x for x in worldcheck.run(gd, pr)[0]['findings']}
check('a pond with every neighbour at its own level too: not said', 'water' not in f, f.get('water'))

# a far view kept in the mod's own files, its folder named as the editor ID is (Waikiki's: projects/<mod> assets/)
import shutil  # noqa: E402
shutil.rmtree(lodgen.out_folder(pr))
own_lod = os.path.join(library.assets_dir(pr), 'meshes', 'landscape', 'lod', 'MyIsland')
os.makedirs(own_lod, exist_ok=True)
open(os.path.join(own_lod, 'MyIsland.level4.x0.y0.nif'), 'wb').write(b'x')
f = {x['check']: x for x in worldcheck.run(gd, pr)[0]['findings']}
check("a far view in the mod's own files counts", f['far']['level'] == 'info', f['far'])

# a world under a parent (as the game's Lucky38World, and the hotels' view worlds): no map of its own to have
pr.records[gd.key(OWN)] = {'type': 'WRLD', 'subs': [{'tag': 'EDID', 'data': 'MyIsland'}, {'tag': 'WNAM', 'data': 1}]}
f = {x['check']: x for x in worldcheck.run(gd, pr)[0]['findings']}
check('a world under a parent: no Pip-Boy map asked for', 'pipboy' not in f, f.get('pipboy'))
