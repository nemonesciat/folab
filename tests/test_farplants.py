"""farplants: far versions of any plant's model, and enough far plants picked to read as growth (not every one)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.stdout.reconfigure(encoding='utf-8')
import gamedata  # noqa: E402
import farplants  # noqa: E402
import nif  # noqa: E402

OK = []
B = chr(92)


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(info)[:400]))


gd = gamedata.GameData()
tree = B.join(['landscape', 'trees', 'NVGreyBirch01.NIF'])
got = farplants.far_model(gd, tree)
check('a game tree gets a far version', got is not None)
data, files, kind = got
shapes = nif.mesh_from_nif(data)
tris = sum(len(s['i']) // 3 for s in shapes)
check('it is a tree: crown, trunk and vines, each its own shape', kind == 'tree' and len(shapes) == 3, [(s['tex'], len(s['i']) // 3) for s in shapes])
check('cheap enough for tens of thousands in the distant blocks (under 300 triangles)', tris < 300, tris)
near = farplants.near_shapes(gd, tree)
leaf = [s for s in near if s.get('alpha')]
top_near = max(v for s in leaf for v in s['p'][2::3])
crown = next(s for s in shapes if 'canopy_' in s['tex'].lower())
top_far = max(crown['p'][2::3])
check('the far crown as tall as the near leaves', abs(top_far - top_near) < 0.2 * top_near, (top_near, top_far))
check('its pictures come with it, one shared bark', farplants.BARK in files and any('canopy_' in k for k in files), list(files))
shrub = farplants.far_model(gd, B.join(['landscape', 'plants', 'NVGoldfingerBanana.NIF']))
check('a low plant is a shrub: one shape, no trunk', shrub and shrub[2] == 'shrub' and len(nif.mesh_from_nif(shrub[0])) == 1)

# picking: one a patch (the tallest), a second on steep ground, everything that isn't a plant kept
P = farplants.PATCH
models = {1: tree, 2: B.join(['landscape', 'plants', 'NVGoldfingerBanana.NIF']), 3: 'architecture' + B + 'barn.nif'}
edids = {1: 'NVGreyBirch01', 2: 'NVGoldfingerBanana', 3: 'Barn'}
flat = [(1, 10.0 + i, 10.0, 0.0, 0.0, 1.0) for i in range(5)] + [(2, 20.0, 20.0, 0.0, 0.0, 1.0), (3, 30.0, 30.0, 0.0, 0.0, 1.0)]
steep = [(1, P * 3 + 10.0 + i, 10.0, i * P * 0.2, 0.0, 1.0) for i in range(5)]
got = farplants.pick(gd, flat + steep, models.get, edids.get)
check('flat patch: one plant, the tallest (the tree, not the banana)', sum(1 for it in got if it[1] < P and it[0] in (1, 2)) == 1
      and any(it[0] == 1 and it[1] < P for it in got))
check('steep patch: two', sum(1 for it in got if it[1] > P * 3) == 2)
check('what is not a plant always kept', any(it[0] == 3 for it in got))

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
