"""A worldspace's own water level (worldrec.world_water*, the Ground panel's "Water · the whole world"): DNAM's default
water height and NAM4's far water height read whether decoded or kept raw, set together, saved and read back exactly;
the editor's water heights follow it, the game's own map tiles never do. Never starts the game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import maptiles  # noqa: E402
import project  # noqa: E402
import schema  # noqa: E402
import worldlife  # noqa: E402
import worldrec  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
recs, stats = schema.checkall(gd, ['WRLD'])
bad = {t: v[1] for t, v in stats['WRLD'].items() if t in ('DNAM', 'NAM2', 'NAM3', 'NAM4', 'CNAM', 'INAM', 'ZNAM') and v[1]}
check('every game world\'s water, climate, image space and music read and write back byte for byte', not bad, bad)

world = next(w for w in gd.worlds() if gd.edid(w) == 'NVDLC02ZionCanyon')
wk = gd.key(world)
pr = project.Project.create('Water')
was = worldrec.world_water(gd, pr, wk)
check('the game\'s level read', was['water'] is not None and not was['changed'] and was['cells'] > 0, was)

raw = {'subs': [{'tag': 'DNAM', 'kind': 'raw', 'value': struct.pack('<2f', -1000.0, 250.0).hex()},
                {'tag': 'NAM4', 'kind': 'raw', 'value': struct.pack('<f', 240.0).hex()}]}
check('a record kept raw (before the layout) still reads', worldrec.world_water_of(raw) == {'land': -1000.0, 'water': 250.0, 'far': 240.0})

op = worldrec.world_water_op(gd, pr, wk, 512.0)
pr.apply('World water at 512', [op])
now = worldrec.world_water(gd, pr, wk)
check('set: the level and the far water together, the land height kept', now['water'] == 512.0 and now['far'] == 512.0 and now['land'] == was['land'] and now['changed'], now)

paint = maptiles.Painter(gd)
paint.mod = lambda: pr
cell = next(c for c in gd.grid(world).values() if gd.fields(c).get('DATA', b'\0')[0] & 2 and not worldrec._own_level(gd.fields(c)))
check('a cell at the world\'s level follows the mod', paint.water(world, cell) == 512.0, paint.water(world, cell))
check('the game\'s own tile (kept on disk) keeps the game\'s level', paint.water(world, cell, mod=False) == was['water'])

sea = worldlife.world_water_op(gd, pr, world, wk)
far = next(s for s in sea['record']['subs'] if s['tag'] == 'NAM4')
check('worldlife\'s far sea reads the decoded level', worldrec.world_water_of({'subs': [far]})['far'] == 512.0, far)

path = pr.plugin_path()
espwrite.write(gd, pr, path)
g2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
f = g2.fields(next(w for w in g2.worlds() if g2.edid(w) == 'NVDLC02ZionCanyon'))
d = struct.unpack('<2f', f['DNAM'])
check('saved and read back', d == (was['land'], 512.0) and struct.unpack('<f', f['NAM4'])[0] == 512.0, (d, f.get('NAM4')))

pr.undo()
check('undo puts the game\'s level back', worldrec.world_water(gd, pr, wk)['water'] == was['water'])
