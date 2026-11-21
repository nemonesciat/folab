"""FOLab's own guard tower (guardtower.py) in place of the game's NVGuardTower01 and its parts a-d: it builds and checks,
is about the game tower's size and no heavier to draw, draws in a few shapes, has a far model, is walked from the ground
to the deck by way of every landing with no faults; a swap in a mod changes only the tower's base and takes out the
game's parts at its spot (one Undo puts it all back); a builder's ops stand FOLab's tower and leave the parts out."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import guardtower as GT  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import project  # noqa: E402
import walkcheck  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
m = modelsets.build(GT.PIECE)
wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
check('the tower builds, every block checked', not wrong, wrong[:2])
game = nif.mesh_from_nif(gd.read_file('meshes\\architecture\\NCR\\NCR_GuardTower01.NIF'))
parts = [nif.mesh_from_nif(gd.read_file('meshes\\architecture\\NCR\\%s.NIF' % e)) for e in GT.GAME_PARTS]
zs = [v for s in game for v in s['p'][2::3]]
b = m['box']
check('about the game tower\'s height (its deck and roof)', abs(GT.DECK - 836) < 20 and abs(b[5] - max(zs)) < 150, (b, round(max(zs))))
check('its footprint about the game tower\'s (716 x 707)', 650 < b[3] - b[0] < 800 and 650 < b[4] - b[1] < 800, b)
game_tris = sum(len(s['i']) // 3 for g in [game] + parts for s in g)
check('no heavier to draw than the game\'s tower with its parts', m['triangles'] < game_tris, (m['triangles'], game_tris))
shapes = nif.mesh_from_nif(m['nif'])
check('a few shapes to draw (the game\'s tower and parts are %d)' % sum(len(g) for g in [game] + parts), len(shapes) <= 5, len(shapes))
check('nothing see-through (no netting)', not any(s.get('alpha') for s in shapes), [s.get('alpha') for s in shapes])
check('has a far model, much lighter than itself', bool(m.get('far')) and m['far']['triangles'] < m['triangles'] / 10, m.get('far', {}).get('triangles'))
check('its own pictures go with it', all(t in m['files'] for t in m['textures']) and len(m['textures']) >= 4)

for vox in (32.0, 16.0):
    rep = walkcheck.check_piece(gd, GT.PIECE, dict(GT.WALK, voxel=vox))
    check('walked from the ground in %d-unit columns: no faults, every landing and the deck reached' % vox,
          rep['ok'] and len(rep['goals']) == 4 and all(g['reached'] for g in rep['goals']), walkcheck.say(GT.PIECE, rep))
# (an outdoor navmesh's columns fall on the tower differently wherever it stands and however it's turned)
import math  # noqa: E402
item = walkcheck.of_piece(GT.PIECE)
failed = []
for dx, dy, rz in ((8, 2, 1.57), (24, 30, 0.79), (2, 29, 3.74), (18, 1, 5.47), (11, 17, 2.4), (23, 5, 1.1)):
    c, s = math.cos(rz), math.sin(rz)
    goals = [(n, (dx + p[0] * c + p[1] * s, dy - p[0] * s + p[1] * c, p[2])) for n, p in GT.WALK['goals']]
    r = walkcheck.walk(gd, [dict(item, pos=(dx, dy, 0.0), rot=(0, 0, rz))], ground=0.0, goals=goals, voxel=GT.VOXEL)
    if not r['ok']:
        failed.append((dx, dy, rz))
check('walked at six other offsets and turns in 32-unit columns', not failed, failed)

# a swap in a mod: a tower with its parts at one spot, one without, a part on its own elsewhere
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
ck = gd.key(gd.grid(world)[(-18, 0)])
keys = {e: k for k, e in GT._game_keys(gd).items()}
X, Y = -18 * 4096 + 1500, 1500
pr = project.Project.create('GuardTower')
adds = [{'op': 'add', 'cell': ck, 'base': keys[GT.GAME], 'p': [X, Y, 100, 0, 0, 0.5], 's': 1}]
adds += [{'op': 'add', 'cell': ck, 'base': keys[e], 'p': [X, Y, 100, 0, 0, 0.5], 's': 1} for e in GT.GAME_PARTS]
adds += [{'op': 'add', 'cell': ck, 'base': keys[GT.GAME], 'p': [X + 2000, Y, 80, 0, 0, 2.0], 's': 1},
         {'op': 'add', 'cell': ck, 'base': keys['NVGuardTower01a'], 'p': [X + 1000, Y + 1500, 80, 0, 0, 1.0], 's': 1}]
pr.apply('stand', adds)
before = json.loads(json.dumps(pr.cells))
ops, rep = GT.swap_ops(gd, pr)
check('both towers swapped, the four parts at the first taken out, the lone part left', len(rep['towers']) == 2 and rep['parts'] == 4 and len(rep['left']) == 1, rep)
check('the record first, then swaps and removes only', ops[0]['op'] == 'record_new' and {o['op'] for o in ops[1:]} == {'swap', 'remove'})
check('the cells to navmesh again are listed', ck in rep['cells'], rep['cells'])
pr.apply('guard towers', ops)
own = modelsets.record_of(pr, GT.PIECE)
refs = pr.cells[ck]['refs']
mine = [k for k, r in refs.items() if r.get('base') == own and not r.get('removed')]
check('the towers are FOLab\'s now, where they stood', len(mine) == 2 and all(refs[k]['p'] == before[ck]['refs'][k]['p'] for k in mine))
again, rep2 = GT.swap_ops(gd, pr)
check('a second run finds no tower left', not rep2['towers'], rep2)
pr.undo()
check('one Undo puts it all back', all(r.get('base') != own for r in pr.cells[ck]['refs'].values())
      and sum(1 for r in pr.cells[ck]['refs'].values() if not r.get('removed')) == 7)

# a builder's ops: the tower becomes FOLab's, the parts go, everything else as it was
other = {'op': 'add', 'cell': ck, 'base': keys['NVGuardTower01a'].replace('17B7B5', '000001'), 'p': [0, 0, 0, 0, 0, 0]}
built = GT.instead(gd, pr, adds[:5] + [other])
check('a builder makes the record (Undo took it out), stands FOLab\'s tower and no game parts',
      built[0]['op'] == 'record_new' and [o['base'] for o in built if o.get('op') == 'add'] == ['$model_' + GT.PIECE, other['base']],
      [o.get('base') for o in built])
check('ops with no tower pass as they were', GT.instead(gd, pr, [other]) == [other])
