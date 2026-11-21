import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""The Real map panel's city steps (web/citysteps.js) through the routes they call, on a small world made from a height file
with a made-up OpenStreetMap file laid on it: the landmark sets listed, a landmark stood where the map was clicked (x, y,
not latitude and longitude), things on the ground, green ground, more plants, who lives there; each one Undo, each saying
what it did or why it couldn't in words. Never starts the game."""
import io, time
import gamedata, project, osmplace
import server, api_maps
import mapfixtures as fx


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def wait():
    for _ in range(18000):
        if not api_maps.JOB.get('running'):
            return api_maps.JOB
        time.sleep(0.1)
    raise RuntimeError('the job never ended')


# ---------- a world, as test_osm makes it ----------
N = 481
D = 0.4 / (N - 1)
vals = [400 + (N - 1 - r) * 0.5 + 0.4 * c for r in range(N) for c in range(N)]
tif = fx.tiff(N, N, vals, 'f', 8, '<', scale=(D, D, 0), tie=(0, 0, 0, -115.0 - D / 2, 36.4 + D / 2, 0), geokeys={1024: 2, 1025: 1, 2048: 4326})
api_maps.upload(io.BytesIO(tif), len(tif), 'city.tif')
server.GD = gamedata.GameData()
server.BR = None
pr0 = project.Project.create('City Steps')
server.load_game(pr0)
server.PR = pr0
api_maps.post('/api/maps/make', {'file': 'city.tif', 'opts': {'compress': 30, 'exag': 2, 'base': 300}, 'name': 'City', 'edid': 'FOLabCityTest'}, server)
j = wait()
check('the world is made', j.get('ok') is True, j.get('error', ''))
gd = server.GD
world_key = j['result']['world']
side = api_maps.read_sidecar(server.PR)['FOLabCityTest']


def latlon(x, y):
    col = side['col0'] + (x - side['x0'] * 4096) / side['upx']
    row = side['row0'] + ((side['y0'] + side['H']) * 4096 - y) / side['upy']
    return 36.4 - row * D, -115.0 + col * D


NODES, WAYS = {}, []


def node(x, y):
    i = len(NODES) + 100
    NODES[i] = latlon(x, y)
    return i


L = 4096 * 3
WAYS.append((1, [node(-L, 2048), node(0, 2048), node(L, 2048)], {'highway': 'primary', 'name': 'Main Road'}))
WAYS.append((2, [node(0, 2048), node(0, 2048 + L)], {'highway': 'residential'}))
k = 10
for bx in (-6000, -3000, 3000, 6000):
    for by in (4096 + 600, -1200):
        ring = [node(bx, by), node(bx + 900, by), node(bx + 900, by + 900), node(bx, by + 900)]
        WAYS.append((k, ring + ring[:1], {'building': 'house'}))
        k += 1
NODES[900] = latlon(100, 100) + ({'place': 'village', 'name': 'Hope'},)
data = fx.osm(NODES, WAYS, bounds=(36.0, -115.0, 36.4, -114.6))
api_maps.upload(io.BytesIO(data), len(data), 'city.osm')
api_maps.post('/api/maps/osm/read', {'file': 'city.osm', 'world': world_key}, server)
wait()
api_maps.post('/api/maps/osm/lay', {'file': 'city.osm', 'world': world_key, 'want': {'roads': ['major', 'minor'], 'rivers': False, 'streams': False, 'lakes': False, 'buildings': True}}, server)
j = wait()
check('roads and pads laid', j.get('ok') is True, j.get('error', ''))

# ---------- the panel's list of sets ----------
sets = api_maps.get('/api/maps/sets', {}, server)[0]
check('the landmark sets and plant sets listed', any(s['key'] == 'lookout' for s in sets['landmarks']) and 'jungle' in sets['plants'], sets)


def step(path, body, what):
    """Run a step; (ok, result). A refusal in words counts as answered: the panel shows it."""
    n = len(server.PR.undo_stack)
    api_maps.post(path, dict({'world': world_key, 'file': 'city.osm'}, **body), server)
    j = wait()
    if j.get('ok'):
        check('%s: done, one Undo (%s)' % (what, server.PR.undo_stack[-1][0]), len(server.PR.undo_stack) == n + 1)
    else:
        e = j.get('error') or ''
        check('%s: refused in words, nothing changed: %s' % (what, e[:90]), len(server.PR.undo_stack) == n and ' ' in e and 'Error' not in e and 'object' not in e)
    return j.get('ok'), j.get('result')


# ---------- a landmark where the map was clicked ----------
ok, r = step('/api/maps/landmarks', {'sites': [{'set': 'lookout', 'x': -9000.0, 'y': 9000.0, 'turn': None}], 'harbour': False}, 'a landmark from a click')
if ok:
    st = r['report']['stood']
    check('stood near where it was clicked', st and abs(st[0]['x'] + 9000) < 3000 and abs(st[0]['y'] - 9000) < 3000, st)
ok, _r = step('/api/maps/landmarks', {'sites': [{'set': 'nosuch', 'x': 0, 'y': 0}], 'harbour': False}, 'a set that isn\'t there')
check('an unknown set stands nothing', not ok)

step('/api/maps/buildings', {'insides': 0}, 'buildings')
step('/api/maps/dress', {}, 'things on the ground')
step('/api/maps/green', {}, 'green ground')
step('/api/maps/plants', {'set': 'jungle', 'thick': 0.5}, 'more plants')
ok, _r = step('/api/maps/life', {'settlement': 'Hope'}, 'who lives there, before a start is set')
check('life asks for the start first', not ok and 'start' in (api_maps.JOB.get('error') or ''))
server.PR.newgame = {'p': [0.0, 2048.0, 900.0, 0, 0, 0]}
step('/api/maps/life', {'settlement': 'Hope'}, 'who lives there')
