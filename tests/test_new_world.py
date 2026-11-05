import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""A new worldspace: written into a mod's plugin (every game file a master), read back as the game would (the
world, its persistent cell, an 8 x 8 grid of cells, flat land at the height asked, in the right blocks), then that
plugin opened as a mod and a cell of the new world's land changed and written over it."""
import json, shutil, struct
import gamedata, project, espwrite, plugintree, worldgen, land, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
mojave = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
ltex = next(gd.key(f) for f, (i, r) in gd.forms.items() if r.tag == 'LTEX' and gd.edid(f) == 'DirtBarrenWastes01')
pr = project.Project.create('World Test')
path = pr.plugin_path()
wr = espwrite.Writer(gd, pr); wr.force_all = True
open(path, 'wb').write(wr.build())
tree = plugintree.Plugin.read(path)
wid, nid = worldgen.add_world(gd, tree, wr, pr.next_id, {'edid': 'FOLabTestWorld', 'name': 'Test Land', 'template': mojave,
                                                        'size': 8, 'height': 3000, 'ltex': ltex})
worldgen.fix_header(tree, wr.own(nid))
open(path, 'wb').write(tree.bytes())
p = tes4.PluginFile(path)
check('every game file a master', [m.lower() for m in p.header['masters']] == gd.names)
p.close()
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path]); me = len(gd2.plugins) - 1
new = next((w for w in gd2.worlds() if gd2.edid(w) == 'FOLabTestWorld'), None)
check('the world is there, named', new is not None and tes4.zstr(gd2.fields(new)['FULL']) == 'Test Land')
check('no parent, no offset table, the Mojave\'s climate', 'WNAM' not in gd2.fields(new) and 'OFST' not in gd2.fields(new) and gd2.fields(new)['CNAM'] == gd.fields(mojave)['CNAM'])
grid = gd2.grid(new)
check('an 8 x 8 grid from -4 to 3', sorted(grid) == sorted((x, y) for x in range(-4, 4) for y in range(-4, 4)))
check('its persistent cell', new in gd2.world_persistent)
L = land.decode(gd2, gd2.land_at(new, -1, 2), {})
check('flat land at 3000, the dirt texture', set(L['h']) == {3000.0} and all(q['bkey'] and gd2.edid(gd2.from_key(q['bkey'])) == 'DirtBarrenWastes01' for q in L['q']))
for pl in gd2.plugins:
    pl.close()
# open it as the mod, change one cell's land, write over it
folder = os.path.join(project.PROJECTS_DIR, 'World Test source'); os.makedirs(folder, exist_ok=True)
shutil.copy2(path, os.path.join(folder, pr.plugin))
d = pr.to_dict(); d.update(source='World Test source/' + pr.plugin, next_id=nid); json.dump(d, open(pr.path, 'w'))
pr2 = project.Project.open('World Test')
gd3 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr2.source_path()]); me3 = len(gd3.plugins) - 1
w3 = next(w for w in gd3.worlds() if gd3.edid(w) == 'FOLabTestWorld')
c3 = gd3.grid(w3)[(0, 0)]
L3 = land.decode(gd3, gd3.land[c3], {}); L3['h'] = [3000.0 + (500 if 8 < k % 33 < 24 and 8 < k // 33 < 24 else 0) for k in range(1089)]
pr2.apply('Raise', [{'op': 'land', 'cell': gd3.key(c3), 'land': L3}])
espwrite.write(gd3, pr2, pr2.plugin_path())
for pl in gd3.plugins:
    pl.close()
gd4 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr2.plugin_path()])
w4 = next(w for w in gd4.worlds() if gd4.edid(w) == 'FOLabTestWorld')
check('the new world\'s land changed as an opened mod', abs(max(land.decode(gd4, gd4.land_at(w4, 0, 0), {})['h']) - 3500) <= 8 and len(gd4.grid(w4)) == 64)
check('still one world of that name', sum(1 for w in gd4.worlds() if gd4.edid(w) == 'FOLabTestWorld') == 1)
for pl in gd4.plugins:
    pl.close()
