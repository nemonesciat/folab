import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Water: a cell's level set by the mod is written into its CELL record (XCLW, the has-water flag), comes back as
the game reads it, and goes back to the world's own level when taken away; undo; the map draws it."""
import struct
import gamedata, project, espwrite, maptiles


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
cell, other = gd.grid(w)[(-18, 0)], gd.grid(w)[(-17, 0)]
pr = project.Project.create('Water Test')
pr.apply('Water', [{'op': 'water', 'cell': gd.key(cell), 'h': 8500}, {'op': 'water', 'cell': gd.key(other), 'h': None}])
espwrite.write(gd, pr, pr.plugin_path())
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr.plugin_path()]); me = len(gd2.plugins) - 1
f = gd2.fields(cell)
check('the cell comes from the mod, water flag on', gd2.source(cell)[0] == me and f['DATA'][0] & 2)
check('its water at 8500', struct.unpack('<f', f['XCLW'])[0] == 8500)
check('XCLW where the game keeps it (after LNAM)', [t for t, d in gd2.plugins[me].fields(gd2.forms[cell][1]).items()].index('XCLW') >
      [t for t, d in gd2.plugins[me].fields(gd2.forms[cell][1]).items()].index('DATA'))
check('the other: back to the world\'s own level', struct.unpack('<f', gd2.fields(other)['XCLW'])[0] > 1e38)
check('the rest of the cell record as the game\'s', {k: v for k, v in f.items() if k not in ('XCLW', 'DATA')} ==
      {k: v for k, v in gd.fields(cell).items() if k not in ('XCLW', 'DATA')})
p = maptiles.Painter(gd)
check('the map sees the mod\'s water', p.water(w, cell, pr.water) == 8500 and p.water(w, other, pr.water) == p.world_water(w))
for pl in gd2.plugins:
    pl.close()
pr.undo()
check('undo takes it back', not pr.water)
