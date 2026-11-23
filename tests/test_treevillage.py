"""Kuliouou's tree village pieces (treevillage.py): each builds and checks, draws in a few shapes, is see-through only in its
straw fringe, has a lighter far model with nothing see-through in it; every platform, the treehouse, the walkway and each
rope bridge walked by walkcheck in 32- and 16-unit columns, every promised spot reached, no faults (the bridges end to end,
their ropes solid: nobody walks off the side); the platform and a bridge walked together, joined at a gap, at several
offsets and turns."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import treevillage as TV  # noqa: E402
import walkcheck  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
made = {}
for k in TV.PIECES:
    m = made[k] = modelsets.build(k)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    shapes = nif.mesh_from_nif(m['nif'])
    alpha = [s['tex'] for s in shapes if s.get('alpha')]
    check('%s builds, every block checked' % k, not wrong, wrong[:2])
    check('%s draws in a few shapes' % k, len(shapes) <= 8, len(shapes))
    check('%s is see-through only in its straw' % k, all('fringe' in t for t in alpha), alpha)
    if k != 'bamboo_ladder':
        check('%s has something solid' % k, len(m['solids']) > 0)
    far = m.get('far')
    check('%s has a far model, lighter' % k, bool(far) and far['triangles'] < m['triangles'] / 2, (m['triangles'], (far or {}).get('triangles')))
    if far:
        fs = nif.mesh_from_nif(far['nif'])
        check('%s\'s far model has nothing see-through' % k, not [s for s in fs if s.get('alpha')])
    check('%s\'s own pictures go with it' % k, all(t in m['files'] for t in m['textures']))

for k, how in TV.WALKS.items():
    for vox in (32.0, 16.0):
        rep = walkcheck.check_piece(gd, k, dict(how, voxel=vox))
        check('%s walked in %d-unit columns: no faults, every spot reached' % (k, vox),
              rep['ok'] and rep['goals'] and all(g['reached'] for g in rep['goals']), walkcheck.say(k, rep))


def joined(dx, dy, turn, vox):
    """The treehouse with a 768 bridge from its +x gap to a platform's -x gap, all moved by (dx, dy) and turned."""
    L = 768.0
    gx, gy = TV.GAPS['bamboo_treehouse'][0][0]
    c, s = math.cos(turn), math.sin(turn)
    # (the game's turn: x' = x c + y s, y' = -x s + y c)
    at = lambda x, y: (dx + x * c + y * s, dy - x * s + y * c)
    bx, by = at(gx + L / 2, gy)
    px, py = at(gx + L + TV.HALF, gy)
    hx, hy = at(0.0, 0.0)
    items = [dict(walkcheck.of_piece('bamboo_treehouse'), pos=(hx, hy, 0.0), rot=(0.0, 0.0, turn)),
             dict(walkcheck.of_piece('bamboo_rope_bridge_768'), pos=(bx, by, TV.RISE), rot=(0.0, 0.0, turn + math.pi / 2)),
             dict(walkcheck.of_piece('bamboo_tree_platform'), pos=(px, py, 0.0), rot=(0.0, 0.0, turn))]
    fx, fy = at(TV.STAIR_FOOT[0], TV.STAIR_FOOT[1])
    goals = [('across the bridge', at(gx + L / 2, gy) + (TV.RISE - L / TV.SAG,)), ('the platform\'s far side', at(gx + L + TV.HALF + 150, gy) + (TV.RISE,))]
    return walkcheck.walk(gd, items, ground=0.0, goals=goals, voxel=vox)


for dx, dy, turn in ((0.0, 0.0, 0.0), (7.0, 13.0, 0.3), (-11.0, 5.0, 1.2), (19.0, -23.0, 2.5)):
    for vox in (32.0, 16.0):
        rep = joined(dx, dy, turn, vox)
        check('treehouse, bridge and platform joined (moved %s, %s, turned %.1f) walked in %d: all reached' % (dx, dy, turn, vox),
              rep['goals'] and all(g['reached'] for g in rep['goals']) and not rep['short'], walkcheck.say('joined', rep))

# the placer's turns: a rail across a gap and a bridge out of it point their +y out of the gap, whichever way the gap faces
import townbuild  # noqa: E402
import treeplace  # noqa: E402
ok = True
for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1), (0.6, 0.8)):
    u, v = townbuild.turn(0.0, 1.0, treeplace._yaw_out(ox, oy))
    ok = ok and abs(u - ox) < 1e-9 and abs(v - oy) < 1e-9
check('treeplace turns a piece\'s +y out of a gap', ok)
check('treeplace sees bridges that cross, not ones that only meet',
      treeplace._cross((0, 0), (10, 10), (0, 10), (10, 0)) and not treeplace._cross((0, 0), (10, 0), (10, 0), (10, 10)))
