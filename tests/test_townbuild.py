import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Buildings on a real map's plots (townbuild.py): a little town in an .osm file (a main street, houses either side, a deep industrial plot,
a plot too small for anything) laid on a world made from a height file, then the game's own buildings put up on the pads. Fronts to the street,
nothing on a road or on each other, set on the pad at the game's own depth, doors where the game had them and locked, small things on a plot
cleared, one Undo, not doubled, saved with no problems. Never starts the game."""
import io, json, math, time
import gamedata, health, project, recordio, roadgen, townbuild, espwrite
import server, api_maps
import mapfixtures as fx


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


# ---------- the pure parts ----------
cx, cy, a, L, W = townbuild.rect_of([(0, 0), (400, 0), (400, 200), (0, 200)])
check('rect_of: a box is itself', abs(cx - 200) < 0.01 and abs(cy - 100) < 0.01 and {round(L), round(W)} == {400, 200})
sq = [(math.cos(t) * 300, math.sin(t) * 300) for t in (0.3, 0.3 + math.pi / 2, 0.3 + math.pi, 0.3 + 3 * math.pi / 2)]
cx, cy, a, L, W = townbuild.rect_of(sq)
check('rect_of: a turned square keeps its size', abs(L - 300 * math.sqrt(2)) < 0.5 and abs(W - L) < 0.5)
check('overlap: apart, touching corners, over', not townbuild.overlap([(0, 0), (1, 0), (1, 1), (0, 1)], [(2, 0), (3, 0), (3, 1), (2, 1)])
      and townbuild.overlap([(0, 0), (2, 0), (2, 2), (0, 2)], [(1, 1), (3, 1), (3, 3), (1, 3)]))
x, y = townbuild.turn(1, 0, math.pi / 2)
check('turn: a quarter turn clockwise takes east to south', abs(x) < 1e-9 and abs(y + 1) < 1e-9)
check('families by editor ID', townbuild.family_of('NVRanchHouse02') == 'house' and townbuild.family_of('NVSearchlightFirehouse') == 'civic'
      and townbuild.family_of('TransmissionBldgTall') == 'industrial' and townbuild.family_of('BldgCorner05NV') == 'shop')
check('not a building by name', all(townbuild.NOT_A_BUILDING.search(e.lower()) for e in ('BLD03Corner01', 'rwcornerstone01NV', 'NVStripWallImposter01', 'gtstorecornerc01low')))

# ---------- a world to lay it on (as test_osm) ----------
N = 241
D = 0.2 / (N - 1)
vals = [400 + (N - 1 - r) * 0.3 + 0.2 * c for r in range(N) for c in range(N)]
tif = fx.tiff(N, N, vals, 'f', 8, '<', scale=(D, D, 0), tie=(0, 0, 0, -115.0 - D / 2, 36.2 + D / 2, 0), geokeys={1024: 2, 1025: 1, 2048: 4326})
api_maps.upload(io.BytesIO(tif), len(tif), 'towntest.tif')
server.GD = gamedata.GameData()
server.BR = None
pr0 = project.Project.create('Town World')
server.load_game(pr0)
server.PR = pr0


def wait():
    for _ in range(12000):
        if not api_maps.JOB.get('running'):
            return api_maps.JOB
        time.sleep(0.1)
    raise RuntimeError('the job never ended')


api_maps.post('/api/maps/make', {'file': 'towntest.tif', 'opts': {'compress': 30, 'exag': 1, 'base': 300}, 'name': 'Town Land', 'edid': 'FOLabTownTest'}, server)
j = wait()
check('the world is made', j.get('ok') is True)
if not j.get('ok'):
    print(j.get('error'))
gd = server.GD
world_key = j['result']['world']
w = gd.from_key(world_key)
side = api_maps.read_sidecar(server.PR)['FOLabTownTest']


def latlon(x, y):
    col = side['col0'] + (x - side['x0'] * 4096) / side['upx']
    row = side['row0'] + ((side['y0'] + side['H']) * 4096 - y) / side['upy']
    return 36.2 - row * D, -115.0 + col * D


NODES, WAYS = {}, []


def node(x, y):
    i = len(NODES) + 100
    NODES[i] = latlon(x, y)
    return i


def plot(wid, x0, y0, x1, y1, tags):
    r = [node(x0, y0), node(x1, y0), node(x1, y1), node(x0, y1)]
    WAYS.append((wid, r + r[:1], tags))


Y0 = 1024.0                         # the main street runs east along y = Y0
WAYS.append((1, [node(-9000, Y0), node(9000, Y0)], {'highway': 'primary', 'name': 'Main Street'}))
wid = 10
houses = []
for i in range(6):
    x0 = -7000 + i * 1500
    plot(wid, x0, Y0 + 500, x0 + 1300, Y0 + 1700, {'building': 'house'})          # north side
    houses.append((x0, Y0 + 500, x0 + 1300, Y0 + 1700, 1))
    wid += 1
    plot(wid, x0, Y0 - 1700, x0 + 1300, Y0 - 500, {'building': 'yes'})           # south side
    houses.append((x0, Y0 - 1700, x0 + 1300, Y0 - 500, -1))
    wid += 1
plot(wid, 3000, Y0 + 500, 7000, Y0 + 4500, {'building': 'industrial', 'name': 'Works'})       # a deep one: rows front and back
wid += 1
plot(wid, 3000, Y0 - 700, 3200, Y0 - 500, {'building': 'shed'})                               # 200 across: too small for anything
small = (3000, Y0 - 700, 3200, Y0 - 500)
wid += 1
plot(wid, 4000, Y0 - 2300, 6000, Y0 - 500, {'building': 'church', 'name': 'St Mary'})        # stands out: a landmark may go here
church = (4000, Y0 - 2300, 6000, Y0 - 500)
wid += 1
plot(wid, 7500, Y0 + 500, 7820, Y0 + 1750, {'building': 'static_caravan'})                 # a trailer lot: 320 on the street, 1,250 deep
trailer = (7500, Y0 + 500, 7820, Y0 + 1750)
data = fx.osm(NODES, WAYS, bounds=(36.0, -115.0, 36.2, -114.8))
api_maps.upload(io.BytesIO(data), len(data), 'town.osm')
api_maps.post('/api/maps/osm/lay', {'file': 'town.osm', 'world': world_key, 'want': {'roads': ['major'], 'buildings': True}}, server)
j = wait()
check('the town\'s roads and plots are laid', j.get('ok') is True)
if not j.get('ok'):
    print(j.get('error'))
pr = server.PR
print('   plots: %s' % json.dumps({k: v for k, v in j['result']['report'].items() if k != 'cell_xy'}))

# something small the mod placed on a plot, to be cleared
def small_rock(f):
    b = townbuild.obnd(gd, gd.key(f))
    return b and 60 < b[3] - b[0] < 300 and 60 < b[4] - b[1] < 300
rock = next(f for f, (_i, r) in sorted(gd.forms.items()) if r.tag == 'STAT' and 'rock' in gd.edid(f).lower() and small_rock(f))
grid = gd.grid(w)
ck0 = gd.key(grid[(int(-6350 // 4096), int((Y0 + 1100) // 4096))])
pr.apply('a rock', [{'op': 'add', 'cell': ck0, 'base': gd.key(rock), 'p': [-6350.0, Y0 + 1100, 500.0, 0, 0, 0], 's': 1}])
rock_key = next(k for k, r in pr.cells[ck0]['refs'].items() if r.get('base') == gd.key(rock))
undo_before = len(pr.undo_stack)

# ---------- buildings ----------
t0 = time.time()
api_maps.post('/api/maps/buildings', {'world': world_key}, server)
j = wait()
check('buildings go up as a job', j.get('ok') is True)
if not j.get('ok'):
    print(j.get('error'))
rep = j['result']['report']
print('   %.0f s: %s' % (time.time() - t0, json.dumps(rep)))
check('one Undo', len(pr.undo_stack) == undo_before + 1 and pr.undo_stack[-1][0] == 'Buildings on the plots')
grid_of = {gd.key(c): xy for xy, c in gd.grid(w).items()}
stood = {tuple(grid_of[ck]) for ck, c in pr.cells.items() if ck in grid_of for r in c['refs'].values() if r.get('base') in {b['key'] for b in townbuild.load(gd, server.kits_folder())}}
check('the cells buildings went up in are listed, for a fresh navmesh (%d)' % len(rep['cell_xy']), stood and stood <= {tuple(c) for c in rep['cell_xy']})
check('the catalogue is measured and kept', rep['catalogue'] >= 40 and os.path.isfile(os.path.join(server.kits_folder(), 'buildings.json')))
cat = {b['key']: b for b in townbuild.load(gd, server.kits_folder())}
check('the street\'s road pieces were seen', rep['roads_seen'] > 5)
refs = [(ck, k, r) for ck, c in pr.cells.items() for k, r in c['refs'].items() if not r.get('removed')]
blds = [(ck, k, r) for ck, k, r in refs if r.get('base') in cat]
check('every house plot, the works, the church and the trailer lot got buildings (%d plots built, %d buildings)' % (rep['built'], len(blds)), rep['built'] == 15 and len(blds) >= 16)
in_box = lambda r, b: b[0] - 200 <= r['p'][0] <= b[2] + 200 and b[1] - 200 <= r['p'][1] <= b[3] + 200
on_lot = [cat[r['base']]['edid'] for _c, _k, r in blds if in_box(r, trailer)]
check('the narrow lot got a mobile home, side-on to the street (%s, %d side-on)' % (on_lot, rep['side_on']), on_lot and all('mobilehome' in e.lower() for e in on_lot) and rep['side_on'] >= 1)
marks = [r for _c, _k, r in blds if townbuild.landmark(cat[r['base']])]
check('plots that stand out: the named works and church (%d)' % rep['poi'], rep['poi'] == 2)
check('the church got the game\'s church, a landmark (%s)' % [cat[r['base']]['edid'] for _c, _k, r in blds if in_box(r, church)],
      any(in_box(r, church) and 'church' in cat[r['base']]['edid'].lower() for r in marks))
check('no ordinary house plot got a landmark', not any(in_box(r, h) for r in marks for h in houses))
check('no landmark twice (%d up)' % len(marks), len(marks) == len({r['base'] for r in marks}) == rep['landmarks'])


def foot(r):
    b = cat[r['base']]['box']
    return townbuild._foot(b, r['p'][5], r['p'])


def mid(fp):
    return sum(p[0] for p in fp) / 4, sum(p[1] for p in fp) / 4


kit = roadgen.pieces(gd)
road_fp = []
for ck, k, r in refs:
    if r.get('base') in (kit['a'], kit.get('b'), kit.get('capr')):
        o = townbuild.obnd(gd, r['base'])
        road_fp.append(townbuild._foot(o, r['p'][5], r['p']))
fps = [foot(r) for _c, _k, r in blds]
check('no building stands on a road piece', not any(townbuild.overlap(f, g) for f in fps for g in road_fp))
check('no building stands on another', not any(townbuild.overlap(fps[i], fps[j]) for i in range(len(fps)) for j in range(i + 1, len(fps))))
inside = 0
for (x0, y0, x1, y1, _s) in houses:
    got = [f for f in fps if x0 - 200 <= mid(f)[0] <= x1 + 200 and y0 - 200 <= mid(f)[1] <= y1 + 200]
    inside += bool(got)
check('each house plot has its building on it (%d of %d)' % (inside, len(houses)), inside == len(houses))
check('nothing on the plot too small for any building', not any(small[0] - 100 <= mid(f)[0] <= small[2] + 100 and small[1] - 100 <= mid(f)[1] <= small[3] + 100 for f in fps)
      and rep['nothing_fits'] >= 1)
fronts, with_doors = 0, 0
for _c, _k, r in blds:
    b = cat[r['base']]
    if not b['doors']:
        continue
    f = townbuild.Fit(b)
    mx, my = mid(foot(r))
    if not (-7200 <= mx <= 2500):
        continue
    with_doors += 1
    dx, dy = townbuild.turn(f.front[0], f.front[1], r['p'][5])
    if dy * (Y0 - my) > 0 and abs(dy) > 0.99:
        fronts += 1
check('every house with a door faces the street (%d of %d)' % (fronts, with_doors), with_doors >= 3 and fronts == with_doors)
ground = roadgen.Ground(gd, pr, w)
off = max(abs((ground.at(r['p'][0], r['p'][1]) - r['p'][2]) - cat[r['base']]['mid']) for _c, _k, r in blds if -7200 <= mid(foot(r))[0] <= 2500)
check('set into the pad as deep as the game sets them (%.1f off at most)' % off, off < 24)
doors = [(ck, k, r) for ck, k, r in refs if k.startswith('+') and not ck.startswith('+') and gd.forms[gd.from_key(r['base'])][1].tag == 'DOOR']
check('doors where the game had them (%d), locked unless something lies behind them' % len(doors),
      len(doors) == rep['doors'] and doors and all(bool(r.get('tel')) != (r.get('props', {}).get('lock', {}).get('level') == 255) for _c, _k, r in doors))
check('the rock on a plot was cleared', rock_key not in pr.cells.get(ck0, {}).get('refs', {}) and rep['cleared'] >= 1)
works = [f for f in fps if 3000 <= mid(f)[0] <= 7000 and Y0 + 500 <= mid(f)[1] <= Y0 + 4500]
facing = set()
for (_c, _k, r), f in zip(blds, fps):
    if f in works:
        b = townbuild.Fit(cat[r['base']])
        facing.add(round(townbuild.turn(b.front[0], b.front[1], r['p'][5])[1]))
check('the deep plot has a row to the street and one at the back (%d buildings, facing %s)' % (len(works), sorted(facing)), len(works) >= 3 and facing == {-1, 1})

# ---------- places behind the doors ----------
places = rep.get('places') or []
check('some buildings have a real place behind a door (%d, %d things)' % (rep['insides'], rep['inside_things']), rep['insides'] >= 2 and len(places) == rep['insides'])
check('the church\'s door leads in (plots that stand out always do)', any(in_box(r, church) for _c, _k, r in refs if r.get('tel')))
cat_all = {k: b for k, b in cat.items()}
ref_at = {}
for ck, c in pr.cells.items():
    for k, r in c['refs'].items():
        ref_at[k] = (ck, r)
bad_link, near_out, near_in, bad_thing, locked_in = 0, 0, 0, 0, 0
for pk in places:
    rec = pr.records[pk]
    inner = pr.cells.get(pk, {}).get('refs', {})
    exits = [(k, r) for k, r in inner.items() if r.get('tel')]
    if len(exits) != 1:
        bad_link += 1
        continue
    xk, xr = exits[0]
    ok_ = xr['tel']['door'] in ref_at
    if ok_:
        ock, orr = ref_at[xr['tel']['door']]
        ok_ = orr.get('tel', {}).get('door') == xk and not orr.get('props', {}).get('lock')
        near_out += math.hypot(xr['tel']['p'][0] - orr['p'][0], xr['tel']['p'][1] - orr['p'][1]) < 300
        near_in += math.hypot(orr['tel']['p'][0] - xr['p'][0], orr['tel']['p'][1] - xr['p'][1]) < 300
    bad_link += not ok_
    for k, r in inner.items():
        f = gd.from_key(r['base'])
        tag = gd.forms[f][1].tag
        if tag in ('NPC_', 'CREA', 'KEYM', 'NOTE', 'TERM') or (tag != 'DOOR' and 'SCRI' in gd.fields(f)):
            bad_thing += 1
check('every place\'s way out leads to its building\'s door and back, that door unlocked', bad_link == 0)
check('you arrive outside by the building\'s door (%d of %d) and inside by the way out (%d)' % (near_out, len(places), near_in), near_out == near_in == len(places))
check('nothing of the game\'s story is copied in: no people, keys, notes, terminals or scripted things', bad_thing == 0)
two_way = next(((b, i) for b in cat.values() for i in b['insides'] if sum(1 for r in gd.refs(gd.from_key(i['cell'])) if r['leads']) > 1), None)
if two_way:
    ops_, _n, _doors = townbuild.inside_ops(gd, two_way[1], 'tt', 'FOLabCheck', 'Check')
    src_doors = {(round(r['pos'][0]), round(r['pos'][1])): r for r in gd.refs(gd.from_key(two_way[1]['cell'])) if r['leads']}
    adds = [o for o in ops_ if o['op'] == 'add' and (round(o['p'][0]), round(o['p'][1])) in src_doors]
    check('inside %s: its way out is free, its doors to anywhere else locked, other doors left to open'
          % gd.edid(gd.from_key(two_way[1]['cell'])), adds and all((o.get('name') == 'ttx') != bool(o.get('extra')) for o in adds)
          and sum(1 for o in adds if o.get('name') == 'ttx') == 1
          and not any(o.get('extra') for o in ops_ if o['op'] == 'add' and (round(o['p'][0]), round(o['p'][1])) not in src_doors))
check('the places are named for what they are', all(recordio.field(pr.records[k], 'EDID').startswith('FOLabTownTest') for k in places)
      and any(recordio.field(pr.records[k], 'FULL') == 'St Mary' for k in places))
check('no owner on a copied place', not any(s['tag'] == 'XOWN' for k in places for s in pr.records[k]['subs']))
check('each place has its navmesh (%d missed)' % rep['navmesh_missed'], all(k in pr.navmesh for k in places) and rep['navmesh_missed'] == 0)
game_meshes = [k for k in places if pr.navmesh[k].get('sig') is not None and len(pr.navmesh[k]['tris']) > 0 and all(d[0] in pr.cells[k]['refs'] for d in pr.navmesh[k]['doors'])]
check('places take the game\'s own navmesh where it can be taken as it is (%d of %d), its doors linked to the place\'s own'
      % (rep['navmesh_game'], len(places)), rep['navmesh_game'] >= len(places) // 2 and len(game_meshes) == len(places)
      and all(pr.navmesh[k]['doors'] for k in places))
check('still one Undo for all of it', pr.undo_stack[-1][0] == 'Buildings on the plots' and len(pr.undo_stack) == undo_before + 1)

# ---------- again, undo, saved ----------
n0 = sum(len(c['refs']) for c in pr.cells.values())
api_maps.post('/api/maps/buildings', {'world': world_key}, server)
j = wait()
check('a second time adds nothing, and says why: %s' % j.get('error'), not j.get('ok') and 'already' in (j.get('error') or '')
      and sum(len(c['refs']) for c in pr.cells.values()) == n0)
espwrite.write(gd, pr, pr.plugin_path())
report = health.check_file(gd, pr.plugin_path())
print('   health: %s' % json.dumps(report['summary']))
for g_ in report['groups']:
    if g_['sev'] != 'info':
        for r_ in g_['rows'][:6]:
            print('     %s' % json.dumps(r_, default=str)[:220])
check('the saved plugin reads back with no problems', report['summary']['error'] == 0 and report['summary']['warn'] == 0)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr.plugin_path()])
w2 = next(x for x in gd2.worlds() if gd2.edid(x) == 'FOLabTownTest')
names = {gd2.edid(r['base']) for c in gd2.grid(w2).values() for r in gd2.refs(c) if r['base'] in gd2.forms}
check('read back: buildings in the world', any(cat_b['edid'] in names for cat_b in cat.values()))
for pl in gd2.plugins:
    pl.close()
label = pr.undo()
check('Undo takes them all away, the rock back', label == 'Buildings on the plots' and not any(r.get('base') in cat for c in pr.cells.values() for r in c['refs'].values())
      and rock_key in pr.cells[ck0]['refs'])
check('and the places behind the doors, with their navmeshes', not any(k in pr.records or k in pr.navmesh or k in pr.cells for k in places))
for pl in gd.plugins:
    pl.close()
