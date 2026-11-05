import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Ground changes: a hill raised in Goodsprings, a texture painted, the ground tinted; written as a LAND override in
the cell's temporary group, read back as the game would, then undone."""
import struct
import gamedata, project, espwrite, land, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
cell = gd.grid(w)[(-18, 0)]
ck = gd.key(cell)
L = land.decode(gd, gd.land[cell], {})
old_h = list(L['h'])
# a hill: up to 400 units in the middle, nothing at the edges (they're shared with the cells next door)
for r in range(33):
    for c in range(33):
        d = ((r - 16) ** 2 + (c - 16) ** 2) ** 0.5
        L['h'][r * 33 + c] += max(0, 400 * (1 - d / 12))
# paint a road texture into quarter 0, and tint a point red
road = next(f for f, (i, rec) in gd.forms.items() if rec.tag == 'LTEX' and 'asphalt' in gd.edid(f).lower())
L['q'][0]['layers'].append({'tex': '', 'key': gd.key(road), 'a': [0.8 if k % 17 < 8 else 0 for k in range(289)]})
L['q'][0]['layers'] = L['q'][0]['layers'][-6:]
c = bytearray.fromhex(L['c']); c[0:3] = b'\xff\x00\x00'; L['c'] = c.hex()
pr = project.Project.create('Land Test')
pr.apply('Raise', [{'op': 'land', 'cell': ck, 'land': L}])
path = pr.plugin_path(); espwrite.write(gd, pr, path)
p = tes4.PluginFile(path)
check('one LAND in the plugin, in a temporary group of Goodsprings',
      [(r.tag, [g for g, l, o in gp][-1]) for r, gp in p.walk() if r.tag == 'LAND'] == [('LAND', tes4.G_CELL_TEMPORARY)])
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path]); me = len(gd2.plugins) - 1
e = gd2.land_at(w, -18, 0)
check('the mod\'s land wins', e[0] == me)
L2 = land.decode(gd2, e, {})
check('heights as raised (within the game\'s 8-unit steps)', max(abs(a - b) for a, b in zip(L2['h'], L['h'])) <= 4)
check('the middle is 400 higher', abs(L2['h'][16 * 33 + 16] - old_h[16 * 33 + 16] - 400) <= 4)
check('edges untouched, so they still meet the cells next door', all(L2['h'][k] == old_h[k] for k in range(33)))
check('the road layer is painted', any(l['key'] and gd2.edid(gd2.from_key(l['key'])) == gd.edid(road) for l in L2['q'][0]['layers']))
check('the tint is red', L2['c'][:6] == 'ff0000')
check('the cell\'s things are still all there', len(gd2.refs(cell)) == len(gd.refs(cell)))
check('the cell next door is the game\'s', gd2.land_at(w, -17, 0)[0] != me)
for pl in gd2.plugins:
    pl.close()
p.close()
pr.undo()
check('undo takes the land back out', not pr.land)
pr.redo()
check('redo puts it back', ck in pr.land)
