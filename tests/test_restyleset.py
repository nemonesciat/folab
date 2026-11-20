"""FOLab's own pieces in place of the game's Mojave buildings (restyleset, restyle): the beach bar builds and checks,
is about the Prospector Saloon's size, has its doorways where the catalogue stands the saloon's doors (and the walls
behind them), is walked to its doors and counters, has a far model and its own pictures; and a swap in a mod changes
only the building's base, leaving its doors and links, and brings its lights."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import project  # noqa: E402
import restyle  # noqa: E402
import restyleset as R  # noqa: E402
import walkcheck  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
m = modelsets.build('beach_bar')
wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
check('the beach bar builds, every block checked', not wrong, wrong[:2])
saloon = nif.mesh_from_nif(gd.read_file('meshes\\architecture\\goodsprings\\nv_prospectorsaloon.nif'))
xs = [v for s in saloon for v in s['p'][0::3]]
ys = [v for s in saloon for v in s['p'][1::3]]
zs = [v for s in saloon for v in s['p'][2::3]]
b = m['box']
check('about the saloon\'s size: footprint within a fifth, no more than half again as tall',
      all(abs((b[3] - b[0]) / (max(xs) - min(xs)) - 1) < 0.2 for _ in [0]) and abs((b[4] - b[1]) / (max(ys) - min(ys)) - 1) < 0.2 and b[5] < 1.5 * max(zs),
      ([round(v) for v in b], round(max(xs) - min(xs)), round(max(ys) - min(ys)), round(max(zs))))
check('no heavier to draw than the saloon', m['triangles'] < sum(len(s['i']) // 3 for s in saloon), m['triangles'])
check('has a far model, lighter than itself', bool(m.get('far')) and m['far']['triangles'] < m['triangles'] / 4, m.get('far', {}).get('triangles'))
own = [t for t in m['textures'] if '\\restyle\\' in t]
check('its own pictures go with it, and every one it names', len(own) >= 4 and all(t in m['files'] for t in m['textures']), len(own))
check('its lights are known', len(__import__('waikikiset').LIGHTS.get('beach_bar', ())) >= 1)

# the doorways: the catalogue's door spots for the saloon (cache/kits' buildings.json, the same in every game's files)
DOORS = [(-291.9, -247.8, 24.9), (-539.5, 312.0, 13.3), (-543.3, 49.7, 15.9)]
check('the doors are where the catalogue stands them', [(round(x), round(y)) for x, y in R.DOORS.values()] == [(round(x), round(y)) for x, y, _z in DOORS])
x0, y0, x1, y1 = R.HALL
check('the bar door is on the hall\'s west face, a door\'s depth in front', 0 < x0 - DOORS[0][0] < 20 and y0 < DOORS[0][1] < DOORS[0][1] + 130 < y1)
sx0, sy0, sx1, sy1 = R.STORE
check('the store\'s doors are in its south and north faces', sx0 < DOORS[1][0] < sx1 and abs(DOORS[1][1] - sy1) < 12 and abs(DOORS[2][1] - sy0) < 12)
check('the bar door stands on the deck', abs(R.FLOOR - DOORS[0][2]) < 2 and R.LANAI[0] < DOORS[0][0] - 60 and R.LANAI[2] >= x0)

how = {'ground': R.GROUND, 'goals': [('the bar door', (-340.0, -180.0, R.FLOOR)), ('the store door, outside', (-540.0, 370.0, R.GROUND)),
                                     ('before the shut door', (-543.0, -10.0, R.FLOOR)), ('a hatch counter', (R.HATCHES[0], y0 - 155, R.GROUND)),
                                     ('the other counter', (R.HATCHES[1], y0 - 155, R.GROUND))]}
rep = walkcheck.check_piece(gd, 'beach_bar', how)
check('walked: no faults, every door and counter reached', rep['ok'] and all(g['reached'] for g in rep['goals']), walkcheck.say('beach_bar', rep))

# a swap in a mod: two saloons with their doors as townbuild stands them, in a Mojave cell
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
ck = gd.key(grid[(-18, 0)])
key_of = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag in ('STAT', 'DOOR') and gd.edid(f) in ('NVProspectorSaloon', 'NVProspectorSaloonDoor', 'RamshackleScrapDoor01')}
pr = project.Project.create('Restyle')
X, Y = -18 * 4096 + 1500, 1500
pr.apply('stand', [{'op': 'add', 'cell': ck, 'base': key_of['NVProspectorSaloon'], 'p': [X, Y, 100, 0, 0, 0.5], 's': 1},
                   {'op': 'add', 'cell': ck, 'base': key_of['NVProspectorSaloonDoor'], 'p': [X - 300, Y - 100, 125, 0, 0, 0.53], 's': 1},
                   {'op': 'add', 'cell': ck, 'base': key_of['NVProspectorSaloon'], 'p': [X + 2500, Y + 1500, 90, 0, 0, 2.0], 's': 1}])
before = json.loads(json.dumps(pr.cells))
ops, rep = restyle.ops(gd, pr)
check('both saloons found and swapped', rep['swapped'] == {'beach_bar': 2}, rep['swapped'])
check('the bar\'s record is made first, then each saloon swapped in place', ops[0]['op'] == 'record_new' and sum(o['op'] == 'swap' for o in ops) == 2)
check('with lights, kept apart', 1 <= rep['lights'] <= 4, rep['lights'])
check('the cells to navmesh again are listed', ck in rep['cells'], rep['cells'])
pr.apply('restyle', ops)
bar = modelsets.record_of(pr, 'beach_bar')
refs = pr.cells[ck]['refs']
swapped = [k for k, r in refs.items() if r.get('base') == bar]
check('the saloons are bars now, where they stood', len(swapped) == 2 and all(refs[k]['p'] == before[ck]['refs'][k]['p'] for k in swapped))
check('the door is as it was', all(refs[k] == r for k, r in before[ck]['refs'].items() if r['base'] == key_of['NVProspectorSaloonDoor']))
check('nothing else removed', all(k in refs for k in before[ck]['refs']))
again, rep2 = restyle.ops(gd, pr)
check('a second run finds nothing left to swap', not again and not rep2['swapped'], len(again))
pr.undo()
check('one Undo puts the saloons back', all(r.get('base') != bar for r in pr.cells[ck]['refs'].values()) and len(pr.cells[ck]['refs']) == 3)

# the plantation town: each builds, is about its game building's size, no heavier to draw, and is walked to its doors
GAME = {'plantation_store': ('architecture/goodsprings/nv_generalstore.nif', -10, [(-330, 30, 17), (-480, 0, 17)]),
        'plantation_shop': ('architecture/goodsprings/nv_oldwestbldggeneric01.nif', -12, [(-330, 28, 14)]),
        'plantation_dry_goods': ('architecture/goodsprings/nv_oldwestbldggeneric02.nif', -8, [(-340, -195, 20), (-539, 380, -8), (-540, 0, 20)]),
        'plantation_school': ('architecture/goodsprings/nv_gsschoolhouse.nif', -10, [(-730, 390, 10), (730, 629, 10)]),
        'plantation_hall': ('architecture/nipton/nv_nipton-town-hall.nif', -10, [(0, 1500, 6), (0, -1200, 30)])}
for piece, (model, ground, goals) in GAME.items():
    m = modelsets.build(piece)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    g = nif.mesh_from_nif(gd.read_file('meshes/' + model))
    gx = [v for s in g for v in s['p'][0::3]]
    gy = [v for s in g for v in s['p'][1::3]]
    b = m['box']
    check('%s builds, every block checked' % piece, not wrong, wrong[:2])
    check('%s: footprint within a fifth of the game building\'s' % piece, abs((b[3] - b[0]) / (max(gx) - min(gx)) - 1) < 0.2 and abs((b[4] - b[1]) / (max(gy) - min(gy)) - 1) < 0.2,
          ([round(v) for v in b], round(max(gx) - min(gx)), round(max(gy) - min(gy))))
    check('%s: no heavier to draw than the game building' % piece, m['triangles'] < sum(len(s['i']) // 3 for s in g), m['triangles'])
    check('%s: a far model' % piece, bool(m.get('far')))
    rep = walkcheck.check_piece(gd, piece, {'ground': ground, 'goals': [('goal %d' % k, gl) for k, gl in enumerate(goals)]})
    check('%s walked: no faults, its doors reached' % piece, rep['ok'] and all(x['reached'] for x in rep['goals']), walkcheck.say(piece, rep))

# the billboards naming Mojave places: swapped for the neutral ones, the Boulder City one lifted onto its new legs
pr2 = project.Project.create('Boards')
keys = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) in ('BillboardBoulderLNV', 'BillboardSunsetSarsaparillaNV', 'BillboardCarAV1', 'BillboardBlank01')}
pr2.apply('stand', [{'op': 'add', 'cell': ck, 'base': keys['BillboardBoulderLNV'], 'p': [X, Y, 100, 0, 0, 0], 's': 1},
                    {'op': 'add', 'cell': ck, 'base': keys['BillboardSunsetSarsaparillaNV'], 'p': [X + 800, Y, 100, 0, 0, 0], 's': 1}])
ops2, rep2 = restyle.ops(gd, pr2, ['billboards'])
pr2.apply('boards', ops2)
bases = sorted(r['base'] for r in pr2.cells[ck]['refs'].values())
check('both Mojave boards are neutral ones now', set(bases) <= {keys['BillboardCarAV1'], keys['BillboardBlank01']} and len(bases) == 2, bases)
zs = sorted(r['p'][2] for r in pr2.cells[ck]['refs'].values())
check('the Boulder City board lifted onto the new legs, the other where it was', zs == [100.0, 314.0], zs)
