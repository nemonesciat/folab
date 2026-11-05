import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""The Scatter brush: what it learns round Goodsprings, and things it puts down kept as the brush's (so it can take
them back) and written as ordinary new refs."""
import gamedata, project, espwrite, scatter


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
found = scatter.learn(gd, w, -18, 0)
names = {k: [b['edid'] for b in v] for k, v in found.items()}
check('Joshua trees are trees', any('TreeJosh' in e for e in names['trees']))
check('canyon rocks are rocks', any('RockCanyon' in e for e in names['rocks']))
check('creosote is a plant, tumbleweed junk', 'CreosoteBushSm' in names['plants'] and 'TumbleweedNV' in names['junk'])
check('no markers or buildings in any set', not any('Marker' in e or 'Fence' in e for v in names.values() for e in v))
check('most used first', all(v == sorted(v, key=lambda b: -b['n']) for v in found.values()))
rock = found['rocks'][0]
check('rocks lean, sizes from the game', rock['tilt'] > 0 and 0.2 < rock['smin'] <= rock['smax'] < 3)
cell = gd.grid(w)[(-18, 0)]
pr = project.Project.create('Scatter Test')
made = pr.apply('Scatter', [{'op': 'add', 'cell': gd.key(cell), 'base': rock['key'], 'p': [-72000, 1000, 8400, 0.1, 0, 2], 's': 0.8, 'sc': True}])
check('kept as scattered', pr.cells[gd.key(cell)]['refs'][made[0]].get('sc') is True)
espwrite.write(gd, pr, pr.plugin_path())
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr.plugin_path()]); me = len(gd2.plugins) - 1
new = [r for r in gd2.refs(cell) if r['ref'] >> 24 == me]
check('written as a plain ref of the rock', len(new) == 1 and gd2.describe(new[0]['base'])[1] == rock['edid'] and abs(new[0]['scale'] - 0.8) < 1e-5)
for p in gd2.plugins:
    p.close()
