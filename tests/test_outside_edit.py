import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Changes outside, in Goodsprings: a rock moved, the saloon's door (kept in the world's persistent cell) moved, a
thing removed, a new one added. The plugin carries the world's record, its children group, the grid cell in its
block and sub-block, and the persistent cell; read back, everything is where it should be."""
import struct
import gamedata, project, espwrite, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
cell = gd.grid(w)[(-18, 0)]
refs = gd.refs(cell)
pc = gd.world_persistent[w]
temp = [r for r in refs if gd.ref_cell[r['ref']] == cell and r['base'] in gd.forms and 'rock' in gd.describe(r['base'])[1].lower()]
door = next(r for r in refs if gd.ref_cell[r['ref']] == pc and r['base'] in gd.forms and r['pos'])
print('persistent one:', gd.describe(door['base'])[1])
rock, gone = temp[0], temp[1]
ck = gd.key(cell)
pr = project.Project.create('Outside Test')
base = next(f for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'RockCanyon01') if any(gd.edid(f) == 'RockCanyon01' for f in [rock['base']]) else rock['base']
made = pr.apply('outside', [
    {'op': 'move', 'cell': ck, 'ref': gd.key(rock['ref']), 'p': [rock['pos'][0] + 100, rock['pos'][1], rock['pos'][2], 0, 0, 0]},
    {'op': 'move', 'cell': ck, 'ref': gd.key(door['ref']), 'p': list(door['pos'][:2]) + [door['pos'][2] + 5] + list(door['rot'])},
    {'op': 'remove', 'cell': ck, 'ref': gd.key(gone['ref'])},
    {'op': 'add', 'cell': ck, 'base': gd.key(rock['base']), 'p': [rock['pos'][0], rock['pos'][1] + 300, rock['pos'][2], 0, 0, 1]}])
path = pr.plugin_path(); espwrite.write(gd, pr, path)
p = tes4.PluginFile(path)
print('top groups', p.top_groups(), 'masters', p.header['masters'])
check('a WRLD group, no CELL group', 'WRLD' in p.top_groups() and 'CELL' not in p.top_groups())
seen = {}
for rec, gpath in p.walk():
    seen.setdefault(rec.tag, []).append((rec, gpath))
check('the world record once, without its offset table', len(seen.get('WRLD', [])) == 1 and 'OFST' not in p.fields(seen['WRLD'][0][0]))
cells = seen.get('CELL', [])
check('two cells: Goodsprings and the persistent one', len(cells) == 2)
grid_cell = next(c for c in cells if any(g == tes4.G_EXT_BLOCK for g, l, o in c[1]))
blk = next(l for g, l, o in grid_cell[1] if g == tes4.G_EXT_BLOCK); sub = next(l for g, l, o in grid_cell[1] if g == tes4.G_EXT_SUBBLOCK)
check('block (0, -1) and sub-block (0, -3), as the game files (-18, 0)',
      struct.unpack('<hh', struct.pack('<I', blk)) == (0, -1) and struct.unpack('<hh', struct.pack('<I', sub)) == (0, -3))
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path]); me = len(gd2.plugins) - 1
check('read back: Goodsprings is still an outside cell of the Mojave', gd2.ext_cells.get(cell) == w and gd2.source(cell)[0] == me)
pos = {r['ref']: r for r in gd2.refs(cell)}
check('rock moved 100 along x', abs(pos[rock['ref']]['pos'][0] - rock['pos'][0] - 100) < 0.01 and gd2.ref_cell[rock['ref']] == cell)
check('door moved and still in the persistent cell', abs(pos[door['ref']]['pos'][2] - door['pos'][2] - 5) < 0.01 and gd2.ref_cell[door['ref']] == pc)
i, f = gd2.ref_fields(gd2.cell_refs[cell][gone['ref']])
check('removed one disabled and sunk', gd2.cell_refs[cell][gone['ref']][1].flags & 0x800 and struct.unpack_from('<3f', f['DATA'])[2] == -30000)
new = [r for r in gd2.refs(cell) if r['ref'] >> 24 == me]
check('new rock in Goodsprings', len(new) == 1 and new[0]['base'] == rock['base'])
check('the land is still the game\'s', gd2.land_at(w, -18, 0)[0] == 0)
for pl in gd2.plugins:
    pl.close()
p.close()
# Play here outside: the marker goes in the world's persistent cell, the world's record with it
import playtest
tp = os.path.join(os.environ['FOLAB_HOME'], 'FOLab Test.esp')
playtest.write_test_plugin(gd, cell, [rock['pos'][0], rock['pos'][1], rock['pos'][2] + 50, 0], tp, 'Goodsprings')
gd3 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [tp]); me3 = len(gd3.plugins) - 1
mk = [f for f, c in gd3.ref_cell.items() if f >> 24 == me3]
check('Play here outside: one marker, in the Mojave\'s persistent cell', len(mk) == 1 and gd3.ref_cell[mk[0]] == pc)
check('Play here outside: found standing in Goodsprings\' square', mk[0] in gd3.persistent_in(w, -18, 0))
for pl in gd3.plugins:
    pl.close()
