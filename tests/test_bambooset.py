"""The bamboo-and-thatch set (bambooset.py): every piece builds and checks, draws in a few shapes, is see-through only in its
straw fringe, has a far model much lighter than itself; what's walked on or into is walked by walkcheck in an outdoor
navmesh's 32-unit columns and in 16, every promised spot reached with no faults; the lookout and the bamboo tower at other
offsets and turns too; the bamboo tower keeps every solid part of FOLab's guard tower exactly (its walk is the tower's)."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import bambooset as B  # noqa: E402
import gamedata  # noqa: E402
import guardtower as GT  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import walkcheck  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
made = {}
for k in B.PIECES:
    m = made[k] = modelsets.build(k)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    shapes = nif.mesh_from_nif(m['nif'])
    alpha = [s['tex'] for s in shapes if s.get('alpha')]
    check('%s builds, every block checked' % k, not wrong, wrong[:2])
    check('%s draws in a few shapes' % k, len(shapes) <= 8, len(shapes))
    check('%s is see-through only in its straw' % k, all('fringe' in t for t in alpha), alpha)
    check('%s has something solid' % k, len(m['solids']) > 0)
    check('%s has a far model, much lighter' % k, bool(m.get('far')) and m['far']['triangles'] < m['triangles'] / 3,
          (m['triangles'], m.get('far', {}).get('triangles')))
    check('%s\'s own pictures go with it' % k, all(t in m['files'] for t in m['textures']))

b = made['bamboo_hut']['box']
check('the hut is about a house\'s size (8 by 6 metres with its platform, its roof 8 up)', 600 < b[3] - b[0] < 900 and 450 < b[5] < 650, b)
gt = modelsets.build(GT.PIECE)
check('the bamboo tower stands on the guard tower\'s footprint, its thatch a little higher than the tin',
      all(abs(a - c) < 60 for a, c in zip(made['bamboo_tower']['box'][:5], gt['box'][:5])) and 0 <= made['bamboo_tower']['box'][5] - gt['box'][5] < 250,
      (made['bamboo_tower']['box'], gt['box']))
check('the bamboo tower no heavier to draw than twice the guard tower', made['bamboo_tower']['triangles'] < 2 * gt['triangles'],
      (made['bamboo_tower']['triangles'], gt['triangles']))

# the bamboo tower: every solid part of the guard tower, unchanged
key = lambda p: json.dumps({f: p.get(f) for f in ('shape', 'size', 'at', 'turn', 'r', 'h')}, sort_keys=True)
tower_solids = sorted(key(p) for p in GT.tower()['parts'] if p.get('solid', True) and p['shape'] in ('box', 'cylinder'))
bamboo_solids = sorted(key(p) for p in B.bamboo_tower()['parts'] if p.get('solid', True) and p['shape'] in ('box', 'cylinder'))
check('the bamboo tower keeps every solid part of the guard tower, none added', tower_solids == bamboo_solids,
      (len(tower_solids), len(bamboo_solids)))

for k, how in B.WALKS.items():
    for vox in (32.0, 16.0):
        rep = walkcheck.check_piece(gd, k, dict(how, voxel=vox))
        check('%s walked in %d-unit columns: no faults, every spot reached' % (k, vox),
              rep['ok'] and rep['goals'] and all(g['reached'] for g in rep['goals']), walkcheck.say(k, rep))

for k in ('bamboo_lookout', 'bamboo_tower', 'bamboo_hut_small'):
    item = walkcheck.of_piece(k)
    failed = []
    for dx, dy, rz in ((8, 2, 1.57), (24, 30, 0.79), (2, 29, 3.74), (18, 1, 5.47), (11, 17, 2.4), (23, 5, 1.1)):
        c, s = math.cos(rz), math.sin(rz)
        goals = [(n, (dx + p[0] * c + p[1] * s, dy - p[0] * s + p[1] * c, p[2])) for n, p in B.WALKS[k]['goals']]
        r = walkcheck.walk(gd, [dict(item, pos=(dx, dy, 0.0), rot=(0, 0, rz))], ground=0.0, goals=goals, voxel=32.0)
        if not (r['ok'] and all(g['reached'] for g in r['goals'])):
            failed.append((dx, dy, rz, [g['label'] for g in r['goals'] if not g['reached']]))
    check('%s walked at six other offsets and turns in 32-unit columns' % k, not failed, failed)
