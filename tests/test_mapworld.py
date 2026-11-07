import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""A new world from a height file, through the server's own new_world and the job the page starts: written with FOLab's writer, read back with its own readers. Known heights
at known cells, edges between cells that match, water at the base level, painted by slope, a health check with no problems; then Undo back to the mod as it was. Never starts the game."""
import array, json, math, time, struct
import elevation, mapscale as MS, mapworld, land, tes4, gamedata, project, health
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


# a GeoTIFF: 30 m pixels; ground rises to the north-east from below sea level; a known bump
N = 241
def height_at(c, r):
    return -30.0 + (c + (N - 1 - r)) * 0.75 + (150.0 if math.hypot(c - 180, r - 60) < 12 else 0.0)
vals = [height_at(c, r) for r in range(N) for c in range(N)]
tif = fx.tiff(N, N, vals, 'f', 8, '<', tiled=(64, 64), scale=(30, 30, 0), tie=(0, 0, 0, 600000.0, 4000000.0, 0), geokeys={1024: 1, 1025: 1, 3072: 32611, 3076: 9001})
up = api_maps.upload(__import__('io').BytesIO(tif), len(tif), 'test area.tif')
check('the file arrives in FOLab\'s own folder', up['file'] == 'test area.tif' and os.path.isfile(os.path.join(api_maps.maps_dir(), 'test area.tif')))
check('nothing goes in with a path in its name', os.path.dirname(api_maps.upload(__import__('io').BytesIO(b'x'), 1, '..\\..\\sneaky.tif')['file']) == '' and os.path.isfile(os.path.join(api_maps.maps_dir(), 'sneaky.tif')))
try:
    api_maps.upload(__import__('io').BytesIO(b'xy'), 5, 'short.tif'); check('a short upload is refused', False)
except ValueError:
    check('a short upload is refused, nothing left', not os.path.exists(os.path.join(api_maps.maps_dir(), 'short.tif')) and not os.path.exists(os.path.join(api_maps.maps_dir(), 'short.tif.tmp')))
api_maps.open_job('test area.tif')
j = wait()
check('the file opens as a job', j['ok'] and j['result']['w'] == N and j['result']['kind'] == 'GeoTIFF' and j['result']['placed'])
check('its plan comes with it', j['result']['plan']['cells'] > 0 and not j['result']['plan']['stop'])
opts = {'compress': 8, 'exag': 2, 'base': 0}
rep = api_maps.post('/api/maps/plan', {'file': 'test area.tif', 'opts': opts}, server)
check('numbers before anything is made: %d x %d cells, about %.1f MB' % (rep['cells_w'], rep['cells_h'], rep['plugin_mb']), rep['cells'] == rep['cells_w'] * rep['cells_h'] and rep['plugin_mb'] > 0)
check('the picture\'s edges for the map', len(rep['edges']) == 4)
png = api_maps.get('/api/maps/picture', {'file': ['test area.tif'], 'base': ['0']}, server)
check('a shaded picture, a PNG', png[1] == 'image/png' and png[0][:4] == b'\x89PNG')

server.GD = gamedata.GameData()
server.BR = None
pr0 = project.Project.create('Map World')
server.load_game(pr0)
server.PR = pr0
# something already in the mod, to see it kept and put back
mojave = next(w for w in server.GD.worlds() if server.GD.edid(w) == 'WastelandNV')
some_stat = next(server.GD.key(f) for f, (i, r) in server.GD.forms.items() if r.tag == 'STAT')
some_cell = server.GD.key(server.GD.grid(mojave)[(0, 0)])
pr0.apply('A thing', [{'op': 'add', 'cell': some_cell, 'base': some_stat, 'p': [100, 100, 9000, 0, 0, 0], 's': 1}])
before = json.dumps(pr0.to_dict(), sort_keys=True)
t0 = time.time()
api_maps.post('/api/maps/make', {'file': 'test area.tif', 'opts': opts, 'name': 'Test Valley', 'edid': 'FOLabMapTest'}, server)
try:
    api_maps.post('/api/maps/make', {'file': 'test area.tif', 'opts': opts, 'name': 'Twice', 'edid': 'Twice'}, server); check('one job at a time', False)
except ValueError:
    check('one job at a time', True)
j = wait()
if not j.get('ok'):
    print('the job failed: ' + str(j.get('error')))
check('the world is made in one action', j.get('ok') is True)
r = j['result']
gd, pr = server.GD, server.PR
print('   %d cells, %.2f MB, %.1f s (%.1f ms a cell) heights %d to %d' % (r['report']['cells'], r['report']['size'] / 1e6, time.time() - t0, (time.time() - t0) / r['report']['cells'] * 1000, r['report']['z_low'], r['report']['z_high']))
check('estimate of its size is fair (asked %.1f, got %.1f MB)' % (rep['plugin_mb'], r['report']['size'] / 1e6), 0.3 < r['report']['size'] / 1e6 / rep['plugin_mb'] < 2.5)
w = gd.from_key(r['world'])
check('the world is found by its name', gd.edid(w) == 'FOLabMapTest' and tes4.zstr(gd.fields(w)['FULL']) == 'Test Valley')
plan = MS.Plan(elevation.read_bytes('test area.tif', tif), opts)
grid = gd.grid(w)
check('its cells are the plan\'s', sorted(grid) == sorted((x, y) for x in range(plan.x0, plan.x0 + plan.W) for y in range(plan.y0, plan.y0 + plan.H)))
_mn, _mx = struct.unpack('<2f', gd.fields(w)['NAM0']), struct.unpack('<2f', gd.fields(w)['NAM9'])
check('its bounds', _mn == (plan.x0 * 4096.0, plan.y0 * 4096.0) and _mx == ((plan.x0 + plan.W) * 4096.0, (plan.y0 + plan.H) * 4096.0))
check('the world\'s water stands at the base level, 0', struct.unpack('<f', gd.fields(w)['DNAM'][4:8])[0] == 0)
tex = {}
def land_of(cx, cy):
    e = gd.land_at(w, cx, cy)
    return land.decode(gd, e, tex)
# heights as read back, against the file, at known points
worst = 0
for (cx, cy) in list(grid)[::5]:
    h = land_of(cx, cy)['h']
    for (rr, cc) in ((0, 0), (16, 16), (32, 32), (3, 29)):
        x, y = cx * 4096 + cc * 128, cy * 4096 + rr * 128
        col, row = plan.pixel_of(x, y)
        if math.hypot(col - 180, row - 60) < 20:
            continue
        want = max(-30.0 + (col + (N - 1 - row)) * 0.75, -1e9) * 70 / 8 * 2
        worst = max(worst, abs(h[rr * 33 + cc] - want))
check('heights read back as the file says (worst off by %.1f; half a step is 4)' % worst, worst <= 4.5)
# the bump
peak_x, peak_y = plan.game_xy(180, 60)
cx, cy = int(peak_x // 4096), int(peak_y // 4096)
h = land_of(cx, cy)['h']
cc, rr = int(round((peak_x - cx * 4096) / 128)), int(round((peak_y - cy * 4096) / 128))
want = (-30.0 + (180 + 180) * 0.75 + 150) * 70 / 8 * 2
check('the bump stands where the file has it, as high (%d, wanted %d)' % (h[rr * 33 + cc], want), abs(h[rr * 33 + cc] - want) <= 8)
# edges between cells, as read back
bad = 0
for (cx, cy) in grid:
    a = land_of(cx, cy)['h']
    if (cx + 1, cy) in grid:
        b = land_of(cx + 1, cy)['h']
        bad += sum(a[r * 33 + 32] != b[r * 33] for r in range(33))
    if (cx, cy + 1) in grid:
        b = land_of(cx, cy + 1)['h']
        bad += sum(a[32 * 33 + c] != b[c] for c in range(33))
check('every edge between cells matches, read back', bad == 0)
check('every height on a whole step', all(v % 8 == 0 for k in list(grid)[::7] for v in land_of(*k)['h']))
# water
wet = dry = 0
for k, c in grid.items():
    low = min(land_of(*k)['h'])
    has = gd.fields(c)['DATA'][0] & 2 and 'XCLW' in gd.fields(c)
    wet += bool(has)
    dry += not has
    if bool(has) != (low < 0):
        check('cell %s\'s water agrees with its ground' % (k,), False)
check('cells under the base level have water, the others none (%d wet, %d dry)' % (wet, dry), wet > 0 and dry > 0)
some_wet = next(c for k, c in grid.items() if 'XCLW' in gd.fields(c))
check('at the world\'s level', struct.unpack('<f', gd.fields(some_wet)['XCLW'])[0] > 1e38)
# paint
L = land_of(plan.x0 + plan.W // 2, plan.y0 + plan.H // 2)
check('painted: a texture on every quarter', all(q['bkey'] for q in L['q']))
names = {gd.edid(gd.from_key(q['bkey'])) for k in list(grid)[::9] for q in land_of(*k)['q']}
check('with the game\'s ground textures, %s, no roads' % sorted(names)[:4], names and not any(w_ in n.lower() for n in names for w_ in ('road', 'asphalt')))
Lq = [land_of(*k) for k in list(grid)[::9]]
check('several textures laid over each other', any(q['layers'] for L_ in Lq for q in L_['q']))
check('at most 6 layers a quarter', all(len(q['layers']) <= 6 for L_ in Lq for q in L_['q']))
# steep ground gets what the game has on steep ground, flat what it has on flat
g2 = MS.heights(plan)
m = mapworld.learn_style(gd, mojave)
p2 = mapworld.Painter(g2, m)
check('the steepness bands differ', m[0] != m[-1])
# the mod is whole
check('the thing already in the mod is in the plugin (baked) and the mod shows no changes', pr.count() == 0 and pr.source)
report = health.check_file(gd, pr.plugin_path())
print('   health: %s' % json.dumps(report['summary']))
for g_ in report['groups']:
    for r_ in g_['rows'][:6]:
        print('     %s: %s' % (g_.get('title') or g_.get('kind'), json.dumps(r_, default=str)[:200]))
check('the saved plugin reads back with no problems', not report['summary'].get('errors') and not report['summary'].get('error'))
side = api_maps.read_sidecar(pr)
check('what it was made from is kept', side['FOLabMapTest']['file'] == 'test area.tif' and side['FOLabMapTest']['W'] == plan.W)
check('Undo says it can take it back', server.state()['project']['undo'] == 'New world from a map')
# a change to it, written over it, read back: an ordinary world to every tool
ck = gd.key(gd.grid(w)[(0, 0)])
L0 = land_of(0, 0)
L0['h'] = [v + 800 for v in L0['h']]
pr.apply('Raise', [{'op': 'land', 'cell': ck, 'land': {k: L0[k] for k in ('h', 'c', 'q')}}])
check('with a change in the mod, Undo is that change', server.state()['project']['undo'] == 'Raise')
pr.undo()
check('and after undoing that, the world', server.state()['project']['undo'] == 'New world from a map')
# undo
d = api_maps.undo_world(server)
check('Undo: the world is gone', d['world_gone'] and not any(server.GD.edid(x) == 'FOLabMapTest' for x in server.GD.worlds()))
now = server.PR.to_dict()
check('Undo: the mod is as it was', json.dumps(now, sort_keys=True) == before)
check('Undo: nothing kept to go back to now', server.PR.undo_stack == [] and not os.path.isdir(api_maps._before('Map World')) and 'FOLabMapTest' not in api_maps.read_sidecar(server.PR))
check('Undo: the mod\'s plugin has no world', b'FOLabMapTest' not in open(server.PR.plugin_path(), 'rb').read())
# a stop is a stop
try:
    api_maps.post('/api/maps/make', {'file': 'nosuch.tif', 'opts': opts, 'name': 'x', 'edid': 'x'}, server); check('a missing file is refused', False)
except ValueError:
    check('a missing file is refused', True)
for pl in server.GD.plugins:
    pl.close()
