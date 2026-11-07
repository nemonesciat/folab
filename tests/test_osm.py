import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""OpenStreetMap: an .osm file written here is read by what's in it, then laid on a world made from a height file in the same place. Roads along their real lines, rivers running down with water,
a lake, flat building pads and the marker layer. One Undo; heights on steps; edges still meeting; saved, it reads back with no problems. Never starts the game."""
import bz2, gzip, io, json, math, struct, time
import elevation, gamedata, health, land, mapscale as MS, osm, osmplace, project, roadgen, tes4, landshape
import server, api_maps
import mapfixtures as fx


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


# ---------- reading ----------
nodes = {i: (36.0 + i * 0.001, -115.0 + i * 0.002) for i in range(1, 30)}
nodes[40] = (36.05, -114.95, {'place': 'town', 'name': 'Testville'})
ways = [(1, [1, 2, 3], {'highway': 'primary', 'name': 'Main Rd'}), (2, [3, 4], {'highway': 'residential'}), (3, [4, 5], {'highway': 'footway'}), (4, [5, 6], {'highway': 'track'}),
        (5, [6, 7], {'highway': 'secondary', 'bridge': 'yes'}), (6, [7, 8], {'highway': 'secondary', 'tunnel': 'yes'}), (7, [8, 9], {'highway': 'proposed'}),
        (8, [10, 11, 12], {'waterway': 'river', 'name': 'Big', 'width': '40'}), (9, [12, 13], {'waterway': 'stream'}), (10, [14, 15, 16, 14], {'natural': 'water'}),
        (11, [17, 18, 19, 17], {'natural': 'water', 'water': 'river'}), (12, [20, 21, 22, 20], {'building': 'yes', 'name': 'Hall'}), (13, [20, 21], {'building': 'yes'}),
        (14, [23, 24], {'natural': 'coastline'}), (15, [25, 26], {}), (16, [26, 27], {}), (17, [27, 25], {}), (18, [10, 13, 14, 10], {'waterway': 'riverbank'})]
rels = [(1, [('way', 15, 'outer'), ('way', 16, 'outer'), ('way', 17, 'outer')], {'type': 'multipolygon', 'natural': 'water', 'name': 'Split Lake'}),
        (2, [('way', 15, 'outer')], {'type': 'multipolygon', 'building': 'yes'}), (3, [('way', 15, 'outer')], {'type': 'route', 'natural': 'water'})]
xml = fx.osm(nodes, ways, rels, bounds=(36.0, -115.0, 36.1, -114.9))
d = osm.read(xml)
check('bounds', d.bounds == (36.0, -115.0, 36.1, -114.9))
c = d.counts()
check('roads by class: %s' % c['roads'], c['roads'] == {'major': 1, 'minor': 1, 'track': 1})
check('a bridge is kept apart, a tunnel and footway and planned road left out', c['bridges'] == 1 and d.skipped.get('road tunnels') == 1 and d.skipped['paths, footways and planned roads'] == 2)
check('rivers and streams, width in metres', c['rivers'] == {'river': 1, 'stream': 1} and d.rivers[0]['width_m'] == 40 if d.rivers[0]['class'] == 'river' else False)
check('lakes: a closed way and a multipolygon joined up, not a river\'s outline', c['lakes'] == 2 and {'Split Lake', ''} == {l['name'] for l in d.lakes} and all(len(l['ring']) == 3 for l in d.lakes))
check('a river\'s outline is skipped and counted', d.skipped['river outlines (the river\'s line is used)'] == 2)
check('a closed building, not an open one; an unclosed multipolygon is no ring', c['buildings'] == 1 and d.buildings[0]['name'] == 'Hall')
check('coastline left out, said so', 'coastline (the base level is the sea)' in d.skipped)
check('places', d.places == [{'pt': (36.05, -114.95), 'name': 'Testville', 'kind': 'town'}])
check('a road says which of its nodes join others', d.road_ends[3] == 2 and d.road_ends[1] == 1)
check('.bz2 and .gz', osm.read(bz2.compress(xml)).counts() == c and osm.read(gzip.compress(xml)).counts() == c)
for bad, word in ((b'<html><body>no</body></html>', 'XML'), (b'<osm><node', 'whole')):
    try:
        osm.read(bad); check('refused: ' + word, False)
    except elevation.MapFileError as e:
        check('refused in words: %s' % str(e)[:50], word in str(e))
try:
    osm.read('x.osm.pbf'); check('.pbf refused', False)
except elevation.MapFileError as e:
    check('.pbf refused, with what to do', 'osmium' in str(e))
joined = osm._join([[1, 2], [3, 2], [3, 1]])[0]
check('osm.join: ways end to end, either way round', len(joined) == 4 and joined[0] == joined[-1] and set(joined) == {1, 2, 3})
check('clip: inside untouched', osmplace.clip_line([(1, 1), (2, 2)], (0, 0, 9, 9)) == [([(1, 1), (2, 2)], True, True)])
parts = osmplace.clip_line([(-5, 5), (5, 5), (5, 20), (7, 20), (7, 5), (15, 5)], (0, 0, 10, 10))
check('clip: a line leaving and coming back is two stretches, cut at the edge', len(parts) == 2 and parts[0][0][0] == (0, 5) and parts[1][0][-1] == (10, 5) and parts[0][1] is False)
check('thin: straight goes to its ends', osmplace.thin([(0, 0), (50, 1), (100, 0)]) == [(0, 0), (100, 0)])

# ---------- a world to lay it on ----------
N = 481                                              # 0.000833 deg (about 90 m) a pixel, 0.4 x 0.4 deg, a broad slope down to the south and flat in the middle
D = 0.4 / (N - 1)
def height_at(c, r):
    return 400 + (N - 1 - r) * 0.5 + 0.4 * c
vals = [height_at(c, r) for r in range(N) for c in range(N)]
tif = fx.tiff(N, N, vals, 'f', 8, '<', scale=(D, D, 0), tie=(0, 0, 0, -115.0 - D / 2, 36.4 + D / 2, 0), geokeys={1024: 2, 1025: 1, 2048: 4326})
api_maps.upload(io.BytesIO(tif), len(tif), 'osmtest.tif')
server.GD = gamedata.GameData()
server.BR = None
pr0 = project.Project.create('Osm World')
server.load_game(pr0)
server.PR = pr0
opts = {'compress': 30, 'exag': 2, 'base': 300}


def wait():
    for _ in range(6000):
        if not api_maps.JOB.get('running'):
            return api_maps.JOB
        time.sleep(0.1)
    raise RuntimeError('the job never ended')


api_maps.post('/api/maps/make', {'file': 'osmtest.tif', 'opts': opts, 'name': 'Osm Land', 'edid': 'FOLabOsmTest'}, server)
j = wait()
check('the world is made', j.get('ok') is True)
if not j.get('ok'):
    print(j.get('error'))
gd = server.GD
world_key = j['result']['world']
w = gd.from_key(world_key)
side = api_maps.read_sidecar(server.PR)['FOLabOsmTest']
geo = osmplace.Georef(side)
print('   world %d x %d cells, %.0f units a pixel' % (side['W'], side['H'], side['upx']))


def latlon(x, y):
    """The spot on Earth that's at (x, y) in the world (the map's own sums, the other way)."""
    col = side['col0'] + (x - side['x0'] * 4096) / side['upx']
    row = side['row0'] + ((side['y0'] + side['H']) * 4096 - y) / side['upy']
    return 36.4 - row * D, -115.0 + col * D


check('a spot on Earth comes out where it should', all(abs(a - b) < 1e-6 for a, b in zip(geo.xy(latlon(1234.5, -987.5)), (1234.5, -987.5))))
# what the OSM file has, in game units, then in lat/lon
L = 4096 * 3
NODES, WAYS = {}, []
def node(x, y):
    i = len(NODES) + 100
    NODES[i] = latlon(x, y)
    return i
road = [node(-L, 2048), node(0, 2048), node(L, 2048)]
branch = [road[1], node(0, 2048 + L)]
WAYS.append((1, road, {'highway': 'primary', 'name': 'Main Road'}))
WAYS.append((2, branch, {'highway': 'secondary'}))
WAYS.append((3, [node(-L, -L), node(-L, -L + 8192)], {'highway': 'residential'}))
WAYS.append((4, [node(L, L), node(L + 2000, L + 2000)], {'highway': 'primary', 'bridge': 'yes'}))
# a river, north-east to south-west (downhill on the slope)
river = [node(L + 2048, 3 * 4096), node(L, 2048 - 4096 * 2), node(L, -L * 2 + 2048)]
WAYS.append((5, river, {'waterway': 'river', 'name': 'Test River'}))
# a lake
lk = [(-2 * L, -L), (-2 * L + 6000, -L), (-2 * L + 6000, -L + 6000), (-2 * L, -L + 6000)]
ring = [node(*p) for p in lk]
WAYS.append((6, ring + ring[:1], {'natural': 'water', 'name': 'Test Lake'}))
# a building big enough for land points; another too small; one off the world
bb = [(-8000, 4096 * 2 + 300), (-8000 + 1000, 4096 * 2 + 300), (-8000 + 1000, 4096 * 2 + 1300), (-8000, 4096 * 2 + 1300)]
b1 = [node(*p) for p in bb]
WAYS.append((7, b1 + b1[:1], {'building': 'yes', 'name': 'Hall'}))
bs = [(-8000 + 2010, 8192 + 10), (-8000 + 2060, 8192 + 10), (-8000 + 2060, 8192 + 60), (-8000 + 2010, 8192 + 60)]
b2 = [node(*p) for p in bs]
WAYS.append((8, b2 + b2[:1], {'building': 'house'}))
far = (side['x0'] - 8) * 4096
b3 = [node(far, 0), node(far + 500, 0), node(far + 500, 500), node(far, 500)]
WAYS.append((9, b3 + b3[:1], {'building': 'yes'}))
NODES[900] = latlon(100, 100) + ({'place': 'village', 'name': 'Hope'},)
data = fx.osm(NODES, WAYS, bounds=(36.0, -115.0, 36.4, -114.6))
api_maps.upload(io.BytesIO(data), len(data), 'test.osm')
api_maps.post('/api/maps/osm/read', {'file': 'test.osm', 'world': world_key}, server)
j = wait()
check('the file reads as a job', j.get('ok') is True)
if not j.get('ok'):
    print(j.get('error'))
s = j['result']
check('what falls on this world: roads %s' % s['roads'], s['roads']['major']['n'] == 2 and 'minor' in s['roads'])
check('its river, lake, buildings (not the one off the world), place, bridge', s['rivers']['river'] == 1 and s['lakes'] == 1 and s['buildings'] == 2 and s['places'] == 1 and s['bridges'] == 1)
check('lines for the map', len(s['draw']['roads']) == 3 and s['draw']['places'][0]['n'] == 'Hope')
lay = osmplace.layout(osm.read(data), side)
m = next(r for r in lay['roads'] if r['name'] == 'Main Road')
check('a road\'s line is where the map said', abs(m['line'][0][0] - (-L)) < 1 and abs(m['line'][0][1] - 2048) < 1)
check('a dead end gets a cap, a join doesn\'t', m['caps'] == (True, True) and next(r for r in lay['roads'] if r['class'] == 'major' and r['name'] != 'Main Road' or r['kind'] == 'secondary')['caps'] == (False, True))
want = {'roads': ['major'], 'rivers': True, 'streams': False, 'lakes': True, 'buildings': True}
before_state = server.PR.count()
t0 = time.time()
api_maps.post('/api/maps/osm/lay', {'file': 'test.osm', 'world': world_key, 'want': want}, server)
j = wait()
check('it lays as a job', j.get('ok') is True)
if not j.get('ok'):
    print(j.get('error'))
rep = j['result']['report']
print('   %.1f s: %s' % (time.time() - t0, json.dumps({k: v for k, v in rep.items() if k != 'cell_xy'})))
pr = server.PR
check('what comes back is FOLab\'s state, for the page', j['result']['state']['project']['undo'] == 'OpenStreetMap: test.osm')
check('nothing of this shows up as a mod of its own', [p['name'] for p in project.list_projects()] == ['Osm World'])
check('one Undo', len(pr.undo_stack) == 1 and pr.undo_stack[0][0] == 'OpenStreetMap: test.osm')
# roads
refs = [r for c in pr.cells.values() for r in c['refs'].values()]
kit = roadgen.pieces(gd)
pieces = [r for r in refs if r.get('base') in (kit['a'], kit.get('b'))]
caps = [r for r in refs if r.get('base') == kit.get('capr')]
check('road pieces (%d) from the game\'s own, %d end caps, from primary and secondary only' % (len(pieces), len(caps)), len(pieces) == rep['pieces'] - len(caps) and len(pieces) > 5 and len(caps) == 3)
along_main = [r for r in pieces if abs(r['p'][1] - 2048) < 200]
check('the main road\'s pieces follow its line (%d)' % len(along_main), len(along_main) >= (2 * L / 976) * 0.7)
check('the bridge isn\'t laid', not any(abs(r['p'][0] - (L + 1000)) < 300 and abs(r['p'][1] - (L + 1000)) < 300 for r in pieces))
check('the lesser road isn\'t laid', not any(abs(r['p'][0] - (-L)) < 150 and r['p'][1] < -L + 8192 for r in pieces))
ground = roadgen.Ground(gd, pr, w)
gap = max(abs(r['p'][2] - ground.at(r['p'][0], r['p'][1])) for r in along_main)
check('the ground lies just under the road (furthest %.0f)' % gap, gap < 80)
# water
ck_lake = gd.key(gd.grid(w)[(int((-2 * L + 3000) // 4096), int((-L + 3000) // 4096))])
lv = pr.water.get(ck_lake)
check('the lake\'s cell has its water, %s' % lv, lv is not None and lv > 0)
gz = ground.at(-2 * L + 3000, -L + 3000)
check('the lake\'s bed is under its water (%.0f under %.0f)' % (gz, lv), gz < lv)
rivers_w = [v for k, v in pr.water.items() if k != ck_lake]
check('the river\'s cells have water, stepping down', len(rivers_w) >= 4)
xs = landshape._steps([list(p) for p in river and [(L + 2048, 3 * 4096), (L, 2048 - 4096 * 2), (L, -L * 2 + 2048)]], 2048)
prof = []
line = [(L + 2048, 3 * 4096), (L, 2048 - 4096 * 2), (L, -L * 2 + 2048)]
box = osmplace.world_box(side)
for t in xs:
    x, y = landshape._along(line, t)
    if box[0] + 300 < x < box[2] - 300 and box[1] + 300 < y < box[3] - 300:
        c_ = gd.grid(w)[(int(x // 4096), int(y // 4096))]
        lvl = pr.water.get(gd.key(c_))
        z = ground.at(x, y)
        prof.append((lvl, z))
check('every cell the river crosses has water standing over its channel (%d looked at)' % len(prof), all(l is not None and z <= l + 8 for l, z in prof) and len(prof) > 4)
lvs = [l for l, _z in prof]
check('its water never goes uphill', all(b <= a + 0.5 for a, b in zip(lvs, lvs[1:])))
# pads
row = lambda x, y: ground.at(x, y)
pad = [row(-8000 + 128 * i + 40, 4096 * 2 + 300 + 128 * j + 40) for i in range(1, 6) for j in range(1, 6)]
inner = []
for gx in range(int(-8000 // 128) + 1, int(-7000 // 128) + 1):
    for gy in range(int((8192 + 300) // 128) + 1, int((8192 + 1300) // 128) + 1):
        inner.append(row(gx * 128.0, gy * 128.0))
check('a building\'s ground is flat (%d land points, %s)' % (len(inner), sorted(set(inner))[:3]), len(inner) >= 25 and len(set(inner)) == 1)
slope_here = abs(height_at(240, 10) - height_at(240, 20))
check('the ground round it still slopes', row(-8000 - 800, 8192 + 800) != inner[0])
layers = api_maps.read_layers(pr)['FOLabOsmTest']
check('the marker layer has both buildings', len(layers['buildings']) == 2)
hall = next(b for b in layers['buildings'] if b['name'] == 'Hall')
check('the hall has its level and outline', hall['pad'] and hall['level'] == inner[0] and len(hall['ring']) == 4)
check('too small for a land point: in the layer, no pad', sum(1 for b in layers['buildings'] if not b['pad']) == 1 and rep['pads_too_small'] == 1)
check('the place and bridge are in the layer', layers['places'][0]['name'] == 'Hope' and len(layers['bridges']) == 1)
got = api_maps.get('/api/maps/layers', {'edid': 'FOLabOsmTest'}, server)[0]
check('the page can ask for the layer', got['places'][0]['name'] == 'Hope')
# ground rules
check('every height changed is on a whole step', all(v % 8 == 0 for f in pr.land.values() for v in f['h']))
heights = {gd.cell_grid(gd.from_key(ck)): f['h'] for ck, f in pr.land.items()}
all_h = lambda k: heights.get(k) or ground.cell(k)
bad = 0
for k, c in gd.grid(w).items():
    a = all_h(k)
    if (k[0] + 1, k[1]) in gd.grid(w):
        b = all_h((k[0] + 1, k[1]))
        bad += sum(a[r * 33 + 32] != b[r * 33] for r in range(33))
    if (k[0], k[1] + 1) in gd.grid(w):
        b = all_h((k[0], k[1] + 1))
        bad += sum(a[32 * 33 + c_] != b[c_] for c_ in range(33))
check('edges between cells still match (%d off)' % bad, bad == 0)
check('and VHGT can hold them', all(land.heights_of(land.encode_heights(f['h'])) == f['h'] for f in pr.land.values()))
# saved and read back
import espwrite
espwrite.write(gd, pr, pr.plugin_path())
report = health.check_file(gd, pr.plugin_path())
print('   health: %s' % json.dumps(report['summary']))
for g_ in report['groups']:
    if g_['sev'] != 'info':
        for r_ in g_['rows'][:6]:
            print('     %s' % json.dumps(r_, default=str)[:220])
check('the saved plugin reads back with no problems', report['summary']['error'] == 0 and report['summary']['warn'] == 0)
for pl in gd.plugins:
    pass
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr.plugin_path()])
w2 = next(x for x in gd2.worlds() if gd2.edid(x) == 'FOLabOsmTest')
g2 = gd2.grid(w2)
check('read back: the same cells', len(g2) == len(gd.grid(w)))
c_lake = g2[(int((-2 * L + 3000) // 4096), int((-L + 3000) // 4096))]
check('read back: the lake\'s level', abs(struct.unpack('<f', gd2.fields(c_lake)['XCLW'])[0] - lv) < 0.2)
back = land.decode(gd2, gd2.land_at(w2, int(-8000 // 4096), 2), {})['h']
ccx = int(-8000 // 4096)
check('read back: the pad', back[(int((8192 + 800) // 128) - 64) * 33 + (int(-7500 // 128) - ccx * 32)] == inner[0])
placed = gd2.refs(g2[(0, 0)])
check('read back: road pieces in the world', any(gd2.edid(r['base']).startswith('WastelandRoad') for r in placed))
for pl in gd2.plugins:
    pl.close()
# laid again: nothing doubled
n0 = sum(len(c['refs']) for c in pr.cells.values())
api_maps.post('/api/maps/osm/lay', {'file': 'test.osm', 'world': world_key, 'want': want}, server)
j = wait()
check('laid a second time: no road piece doubled', j.get('ok') is True and sum(len(c['refs']) for c in pr.cells.values()) == n0)
pr.undo()
# undo
n = pr.undo()
check('Undo takes all of it away at once', n == 'OpenStreetMap: test.osm' and pr.count() == before_state)
for pl in gd.plugins:
    pl.close()
