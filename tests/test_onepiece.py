"""The game's statics drawn in one piece (onepiece.py): each model in MERGE builds as one shape with every triangle,
corner, picture and baked shade of the game's, reads back as built, keeps its collision about the game's (one closed
solid, its box within a few units); a model of two pictures is refused; the ops on a mod make one STAT of its own and
swap only the mod's own things of the game's base."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import hkshape  # noqa: E402
import nif  # noqa: E402
import onepiece  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
for edid in onepiece.MERGE:
    f = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == edid)
    game = gd.read_file('meshes\\' + gd.describe(f)[3])
    data, box, rel = onepiece.merged(gd, edid)
    before = nif.mesh_from_nif(game)
    after = nif.mesh_from_nif(data)
    check(edid + ': one shape of %d' % len(before), len(after) == 1)
    check(edid + ': every triangle kept', len(after[0]['i']) == sum(len(s['i']) for s in before),
          (len(after[0]['i']) // 3, sum(len(s['i']) for s in before) // 3))
    check(edid + ': the same picture', after[0]['tex'].lower() == before[0]['tex'].lower(), after[0]['tex'])
    check(edid + ': shade kept', ('c' in after[0]) == any('c' in s for s in before))
    gc, oc = hkshape.collision_shapes(game), hkshape.collision_shapes(data)
    if gc:
        gv = [v for c in gc for v in c['v']]
        ov = oc[0]['v'] if oc else []
        near = oc and all(abs(min(gv[k::3]) - min(ov[k::3])) < 6 and abs(max(gv[k::3]) - max(ov[k::3])) < 6 for k in range(3))
        check(edid + ': collision one solid round the game\'s', len(oc) == 1 and near)

try:
    onepiece.join([{'tex': 'a.dds', 'normal': '', 'alpha': False, 'p': [0] * 9, 'n': [0] * 9, 'uv': [0] * 6, 'i': [0, 1, 2], 'c': None},
                   {'tex': 'b.dds', 'normal': '', 'alpha': False, 'p': [0] * 9, 'n': [0] * 9, 'uv': [0] * 6, 'i': [0, 1, 2], 'c': None}])
    check('a model of two pictures refused', False)
except onepiece.Unfit:
    check('a model of two pictures refused', True)

pr = project.Project.create('onepiece test')
game_key = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'SuburbanRubblePileSm01'))
cell = gd.key(next(iter(gd.grid(next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')).values())))
pr.cells[cell] = {'refs': {'+000100': {'base': game_key, 'p': [0, 0, 0, 0, 0, 0]},
                           '+000101': {'base': game_key, 'p': [300, 0, 0, 0, 0, 0]},
                           '00ABCDEF:FalloutNV.esm': {'base': game_key, 'p': [600, 0, 0, 0, 0, 0]}}}
o, rep = onepiece.ops(gd, pr, which=('SuburbanRubblePileSm01',))
check('one STAT of the mod\'s own made', sum(1 for x in o if x['op'] == 'record_new') == 1)
check('only the mod\'s own things swapped', rep['swapped']['SuburbanRubblePileSm01'] == 2, rep)
pr.apply('one piece', o)
k = next(k for k, r in pr.records.items() if recordio.field(r, 'EDID') == 'FOLabSuburbanRubblePileSm01')
check('the swaps name it', all(pr.cells[cell]['refs'][r]['base'] == k for r in ('+000100', '+000101')))
