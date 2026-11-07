import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Ground types: a land-cover file over a height file. Known classes named, the table's textures painted where the file says and read back from the plugin, steep ground left to the slope,
scatter only where the table asks and not in water, its own Undo before the world's. Never starts the game."""
import array, io, json, math, time
import autopaint, elevation, gamedata, health, land, landcover, mapworld, project, roadgen
import server, api_maps
import mapfixtures as fx


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


def wait():
    for _ in range(6000):
        if not api_maps.JOB.get('running'):
            return api_maps.JOB
        time.sleep(0.1)
    raise RuntimeError('the job never ended')


# heights: 241 x 241 at 30 m, a gentle slope, a cliff along col 200+, sea in the south
N = 241
GEO = {'scale': (30, 30, 0), 'tie': (0, 0, 0, 600000.0, 4000000.0, 0), 'geokeys': {1024: 1, 1025: 1, 3072: 32611, 3076: 9001}}
def h(c, r):
    return 40 + (N - 1 - r) * 0.3 + (900.0 if c > 200 else 0.0) - (100.0 if r > 225 else 0.0)
tif = fx.tiff(N, N, [h(c, r) for r in range(N) for c in range(N)], 'f', 8, **GEO)
api_maps.upload(io.BytesIO(tif), len(tif), 'hills.tif')
# land cover: same place, WorldCover's numbers: bare in the west, trees in the middle, grass in the east, built in a block
def k(c, r):
    if 100 <= c <= 130 and 40 <= r <= 70:
        return 50
    return 60 if c < 80 else 10 if c < 160 else 30
cov = fx.tiff(N, N, [k(c, r) for r in range(N) for c in range(N)], 'H', 8, **GEO)
api_maps.upload(io.BytesIO(cov), len(cov), 'cover.tif')

# reading the table
r = elevation.read_bytes('cover.tif', cov)
counts = landcover.classes_in(r)
check('classes in the file', set(counts) == {10, 30, 50, 60})
check('ESA WorldCover by its numbers', landcover.detect(counts) == 'ESA WorldCover')
check('NLCD by its numbers', landcover.detect({11: 1, 41: 5, 82: 3}) == 'USGS NLCD')
check('other numbers are nothing known', landcover.detect({1: 1, 2: 5, 3: 3}) is None)
hts = elevation.read_bytes('h.tif', tif)
try:
    landcover.classes_in(hts); check('heights aren\'t classes', False)
except elevation.MapFileError as e:
    check('heights aren\'t classes: %s' % str(e)[:40], 'heights' in str(e))
# projections
to_dem = lambda x, y: (x / 100.0, y / 100.0)
c0 = landcover.Cover(r, [], r.geo, N, N, to_dem)
check('same place, same pixel', c0.class_at(0, 0) == 60 and c0.class_at(11500, 5500) == 50 and c0.class_at(1e7, 0) is None)
half = dict(r.geo, dx=15.0, dy=15.0)
fine = elevation.Raster(481, 481, array.array('f', [k(c // 2, r_ // 2) for r_ in range(481) for c in range(481)]), half, 'fine.tif')
c1 = landcover.Cover(fine, [], r.geo, N, N, to_dem)
check('a finer file over the same ground', c1.class_at(11500, 5500) == 50 and c1.class_at(15000, 0) == 10)
other = elevation.Raster(10, 10, array.array('f', [1.0] * 100), dict(r.geo, epsg=32612), 'x')
try:
    landcover.Cover(other, [], r.geo, N, N, to_dem); check('another projection is refused', False)
except elevation.MapFileError as e:
    check('another projection is refused, with what to do', 'gdalwarp' in str(e))
plain = elevation.Raster(11, 11, array.array('f', [30 / 255] * 121), None, 'x.png', plain=True)
c2 = landcover.Cover(plain, [], r.geo, N, N, to_dem)
check('no place of its own: stretched over the file, and says so', c2.class_at(12000, 12000) == 30 and c2.note)

server.GD = gamedata.GameData()
server.BR = None
pr0 = project.Project.create('Cover World')
server.load_game(pr0)
server.PR = pr0
gd = server.GD
api_maps.post('/api/maps/cover/open', {'file': 'cover.tif'}, server)
j = wait()
check('the file opens as a job', j.get('ok') is True)
res = j['result']
check('its scheme, its rows, the commonest first', res['scheme'] == 'ESA WorldCover' and res['rows'][0]['share'] >= res['rows'][-1]['share'])
rows = {x['value']: x for x in res['rows']}
check('named rows', rows[10]['label'] == 'Trees' and rows[60]['label'] == 'Bare ground')
check('every default texture is one the game has', all(x['tex'] and gd.edid(gd.from_key(x['tex'])) for x in res['rows']))
check('the panel\'s texture list', len(res['textures']) > 50 and res['sets'][0][0] == 'none')
# my own table: bare gets one thing, trees another, a blank for grass
by = {gd.edid(f): gd.key(f) for f, (_i, x) in gd.forms.items() if x.tag == 'LTEX'}
rows[60].update(tex=by['LRockWastelandNV'], scatter='none', density=0)
rows[10].update(tex=by['LGrassGreenFarmlandsNV'], scatter='plants', density=40)
rows[30].update(tex='', scatter='none', density=0)
rows[50].update(tex=by['Pavement'], scatter='none', density=0)
opts = {'compress': 8, 'exag': 1, 'base': 0}
api_maps.post('/api/maps/make', {'file': 'hills.tif', 'opts': opts, 'name': 'Cover Land', 'edid': 'FOLabCoverTest', 'cover': {'file': 'cover.tif', 'rows': list(rows.values())}}, server)
j = wait()
check('the world is made', j.get('ok') is True)
if not j.get('ok'):
    print(j.get('error'))
gd = server.GD
w = gd.from_key(j['result']['world'])
rep = j['result']['report']
print('   %d cells, %.2f MB, %s things' % (rep['cells'], rep['size'] / 1e6, rep.get('things')))
side = api_maps.read_sidecar(server.PR)['FOLabCoverTest']
pr = server.PR


def spot(col, row):
    return (side['x0'] * 4096 + (col - side['col0']) * side['upx'], (side['y0'] + side['H']) * 4096 - (row - side['row0']) * side['upy'])


tex = {}
def shows_at(x, y):
    """Which texture shows most at a spot, read back from the plugin."""
    cx, cy = int(x // 4096), int(y // 4096)
    L = land.decode(gd, gd.land_at(w, cx, cy), tex)
    col, row = (x - cx * 4096) / 128, (y - cy * 4096) / 128
    q = (1 if col >= 16 else 0) + (2 if row >= 16 else 0)
    c_, r_ = int(col) - (16 if col >= 16 else 0), int(row) - (16 if row >= 16 else 0)
    m = autopaint.shows(L['q'][q], r_ * 17 + c_)
    t = max(m.items(), key=lambda kv: kv[1])
    return gd.edid(gd.from_key(t[0])), round(t[1], 2)


name, share = shows_at(*spot(40, 150))
check('where the file says bare: my texture shows (%s, %.2f)' % (name, share), name == 'LRockWastelandNV' and share > 0.5)
name, share = shows_at(*spot(125, 150))
check('where it says trees: my texture (%s, %.2f)' % (name, share), name == 'LGrassGreenFarmlandsNV' and share > 0.5)
name, share = shows_at(*spot(115, 55))
check('where it says built: my texture (%s, %.2f)' % (name, share), name == 'Pavement' and share > 0.5)
name, share = shows_at(*spot(175, 150))
check('a class with no texture goes by slope (%s)' % name, name not in ('LRockWastelandNV', 'LGrassGreenFarmlandsNV', 'Pavement'))
x, y = spot(200.5, 120)
L_ = land.decode(gd, gd.land_at(w, int(x // 4096), int(y // 4096)), tex)
check('a cliff in the middle of a class isn\'t painted with it', landcover.STEEP < 60 and shows_at(*spot(200.5, 120))[0] != 'LGrassGreenFarmlandsNV')
check('painted under 7 layers everywhere', all(len(q['layers']) <= 6 for k_ in list(gd.grid(w))[::11] for q in land.decode(gd, gd.land_at(w, *k_), tex)['q']))
# scatter
check('scatter is its own Undo, on top of the world\'s', [s[0] for s in pr.undo_stack] == ['Scatter by ground types'])
refs = [t for c in pr.cells.values() for t in c['refs'].values()]
check('things were put down (%d)' % len(refs), len(refs) == rep['things'] and len(refs) > 50)
to_col = lambda p: side['col0'] + (p[0] - side['x0'] * 4096) / side['upx']
to_row = lambda p: side['row0'] + ((side['y0'] + side['H']) * 4096 - p[1]) / side['upy']
wrong = [t for t in refs if not (k(int(round(to_col(t['p']))), int(round(to_row(t['p'])))) == 10)]
check('all where the table asked: on trees, none on bare, grass or built (%d astray)' % len(wrong), not wrong)
g = roadgen.Ground(gd, pr, w)
off = max(abs(t['p'][2] - g.at(t['p'][0], t['p'][1])) for t in refs)
check('each stands on the ground (furthest %.0f)' % off, off < 80)
check('in the set\'s own sizes, turned', all(0.1 < t['s'] < 5 for t in refs) and len({t['p'][5] for t in refs}) > 10)
wet = [t for t in refs if g.water(t['p'][0], t['p'][1]) is not None and g.at(t['p'][0], t['p'][1]) < g.water(t['p'][0], t['p'][1])]
check('nothing in the water', not wet)
few = landcover.Cover(elevation.read_bytes('cover.tif', cov), list(rows.values()), elevation.read_bytes('h.tif', tif).geo, N, N, lambda x_, y_: (to_col((x_, y_)), to_row((x_, y_))))
ops, r2 = landcover.scatter_ops(gd, pr, w, few, gd.from_key(gd.key(next(x for x in gd.worlds() if gd.edid(x) == 'WastelandNV'))), (0, 0), limit=20)
check('a limit is a limit (%d, thinned to %.3f)' % (len(ops), r2['thinned']), len(ops) <= 20 and r2['thinned'] < 1)
check('what it was made from is kept', side['cover']['file'] == 'cover.tif')
# saved
import espwrite
espwrite.write(gd, pr, pr.plugin_path())
report = health.check_file(gd, pr.plugin_path())
print('   health: %s' % json.dumps(report['summary']))
for g_ in report['groups']:
    if g_['sev'] != 'info':
        for r_ in g_['rows'][:6]:
            print('     %s' % json.dumps(r_, default=str)[:220])
check('the saved plugin reads back with no problems', report['summary']['error'] == 0 and report['summary']['warn'] == 0)
# undo, then the world
pr.undo()
check('Undo takes the things away', pr.count() == 0 and server.state()['project']['undo'] == 'New world from a map')
d = api_maps.undo_world(server)
check('Undo again takes the world', d['world_gone'] and not any(server.GD.edid(x) == 'FOLabCoverTest' for x in server.GD.worlds()))
for pl in server.GD.plugins:
    pl.close()
