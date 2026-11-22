"""Distant buildings (lodobj.py): the writer rebuilds the game's own block files byte for byte; the game's blocks keep
each thing's triangles in the segment of the cell it stands in, numbered x * 4 + y; and a world's far things are made
from the game's stand-in models into blocks counted from the world's south-west cell, with one sheet of textures."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import dds  # noqa: E402
import gamedata  # noqa: E402
import lodgen  # noqa: E402
import lodobj  # noqa: E402
import project  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
BS = chr(92)
names = sorted(n for a in gd.archives() for n in a.files if (BS + 'blocks' + BS) in n and n.startswith('meshes' + BS + 'landscape' + BS + 'lod' + BS) and n.endswith('.nif'))
check('the game ships blocks of distant buildings to go by', len(names) > 500, len(names))

# ---------- the game's own, rebuilt ----------
same, tried, in_cell, wrong_cell = 0, 0, 0, 0
for n in names[::8]:
    d = gd.read_file(n)
    b = lodobj.read_block_nif(d)
    x, y = int(round(b['x0'] / 4096)), int(round(b['y0'] / 4096))
    out = lodobj.block_nif(b['world'], x, y, b['verts'], b['normals'], b['tangents'], b['uvs'], b['segments'], b['bounds'], b['sphere'], b['flags'])
    tried += 1
    same += out == d
    # where each segment's triangles lie: mostly in the cell the segment is for
    for k, seg in enumerate(b['segments']):
        if not seg:
            continue
        votes = {}
        for t in seg:
            cx = sum(b['verts'][q][0] for q in t) / 3 // 4096
            cy = sum(b['verts'][q][1] for q in t) / 3 // 4096
            votes[(cx, cy)] = votes.get((cx, cy), 0) + 1
        best = max(votes, key=votes.get)
        if best == (k // 4, k % 4):
            in_cell += 1
        else:
            wrong_cell += 1
check('every one of %d of the game\'s blocks is rebuilt byte for byte' % tried, same == tried and tried >= 60, (same, tried))
check('a segment is its cell\'s, numbered x * 4 + y from the block\'s corner', in_cell > 10 * max(1, wrong_cell), (in_cell, wrong_cell))

# ---------- stand-ins ----------
st = lodobj.StandIns(gd)
with_far = next(f for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'NoVacHouse01')
without = next(f for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'WoodShack01')
check('a house the game has a far model for', bool(st.of(with_far)) and all(s['uv'] and s['i'] for s in st.of(with_far)))
check('a shack it has none for', st.of(without) is None)
check('a thing with no model at all', st.of_model('') is None and st.of_model('nosuch\\thing.nif') is None)

# ---------- a world's far things ----------
world = next(w for w in gd.worlds() if gd.edid(w) == 'FreesideWorld')
sw = lodgen.world_box(gd, world)[:2]
pr = project.Project.create('Far Things')
out = os.path.join(project.HOME, 'far')
# three houses: two in one cell, one in the next block north
spots = [(sw[0] + 1, sw[1] + 2, 0.0), (sw[0] + 1, sw[1] + 2, 1.2), (sw[0] + 2, sw[1] + 5, 0.4)]
real = lodobj.things_of
lodobj.things_of = lambda g, p, w: [(with_far, (cx + 0.5) * 4096.0, (cy + 0.5) * 4096.0 + 300 * k, 500.0, rz, 1.0) for k, (cx, cy, rz) in enumerate(spots)] \
    + [(without, sw[0] * 4096.0 + 100, sw[1] * 4096.0 + 100, 500.0, 0.0, 1.0)]
rep = lodobj.generate(gd, pr, world, out)
lodobj.things_of = real
check('three shown, the shack left out', rep['things'] == 3 and rep['skipped'] == 1 and rep['blocks'] == 2, rep)
edid = gd.edid(world)
folder = os.path.join(out, 'meshes', 'landscape', 'lod', edid, 'blocks')
made = sorted(os.listdir(folder))
check('blocks are counted from the world\'s south-west cell', made == sorted('%s.level4.x%d.y%d.nif' % (edid, sw[0], sw[1] + 4 * k) for k in (0, 1)), made)
b = lodobj.read_block_nif(open(os.path.join(folder, '%s.level4.x%d.y%d.nif' % (edid, sw[0], sw[1])), 'rb').read())
one = st.of(with_far)
nv, nt = sum(len(s['p']) // 3 for s in one), sum(len(s['i']) // 3 for s in one)
check('the first block holds both houses\' corners and triangles', len(b['verts']) == 2 * nv and sum(len(s) for s in b['segments']) == 2 * nt, (len(b['verts']), nv))
check('in the segment of the cell they stand in (1, 2 of the block: number 6)', len(b['segments'][6]) == 2 * nt and not any(b['segments'][k] for k in range(16) if k != 6))
check('counted from the block\'s corner, where the houses stand', all(4096 <= v[0] <= 3 * 4096 and 2 * 4096 <= v[1] <= 4 * 4096 for v in b['verts']) and
      min(v[2] for v in b['verts']) > 300, (min(v[0] for v in b['verts']), max(v[0] for v in b['verts'])))
check('its place and its name are the block\'s', (b['x0'], b['y0']) == (sw[0] * 4096.0, sw[1] * 4096.0) and b['world'] == edid)
check('every texture coordinate lies on the sheet', all(0.0 <= u <= 1.0 and 0.0 <= v <= 1.0 for u, v in b['uvs']))
check('the two houses are turned differently', b['verts'][0] != b['verts'][nv] and abs(b['verts'][0][2] - b['verts'][nv][2]) < 1e-3)
tex = os.path.join(out, 'textures', 'landscape', 'lod', edid, 'blocks')
sheet = open(os.path.join(tex, edid + '.Buildings.dds'), 'rb').read()
info = dds.info(sheet)
check('one sheet of their textures, and its bumps', info and info['w'] == info['h'] == rep['sheet'] and info['format'] == 'DXT1'
      and os.path.isfile(os.path.join(tex, edid + '.Buildings_n.dds')), info)
w, h, px = lodgen.decode_dxt1(sheet)
check('the sheet has a picture in it, not one flat colour', len(set(px[::37])) > 20)
again = os.path.join(project.HOME, 'far2')
lodobj.things_of = lambda g, p, w: []
check('a world with nothing to show says so and writes nothing', lodobj.generate(gd, pr, world, again)['blocks'] == 0 and not os.path.isdir(again))
lodobj.things_of = real

# ---------- what a world's placed things are ----------
cell = gd.grid(world)[(sw[0] + 3, sw[1] + 3)] if (sw[0] + 3, sw[1] + 3) in gd.grid(world) else next(iter(gd.grid(world).values()))
before = len(lodobj.things_of(gd, pr, world))
pr.apply('add', [{'op': 'add', 'cell': gd.key(cell), 'base': gd.key(with_far), 'p': [100.0, 200.0, 300.0, 0.0, 0.0, 0.5], 's': 1}])
after = lodobj.things_of(gd, pr, world)
check('the game\'s own things, and the mod\'s', before > 100 and len(after) == before + 1 and (with_far, 100.0, 200.0, 300.0, 0.5, 1.0) in after, (before, len(after)))

# ---------- far things for the editor's own view ----------
far = lodobj.Far(gd)
tx, ty = (sw[0] + 3) // 16, (sw[1] + 3) // 16
plain = far.tile(None, world, tx, ty)
mine = far.tile(pr, world, tx, ty)
check('a map tile of the game has far things, each with its far model\'s file', len(plain['things']) > 20 and all(m.endswith('_lod.nif') and gd.read_file(m) for m in plain['models']),
      (len(plain['things']), len(plain['models'])))
check('every thing names one of the tile\'s models', all(0 <= t[0] < len(plain['models']) for t in plain['things']))
spot = [t for t in mine['things'] if t[1:4] == [100.0, 200.0, 300.0]]
check('the mod\'s own thing is among them, with the cell it is filed in', len(spot) == 1 and len(mine['things']) == len(plain['things']) + 1, len(spot))
check('a thing with no far model is not', far.path(without) is None and far.path(with_far).endswith('_lod.nif'), far.path(with_far))

# ---------- a small world's far view leaves out what it stands something else in place of (viewworld.replaced) ----------
# (22 Nov 2026: the hotels' view worlds' far blocks held the closed hotel's far model, drawn over the open lobby)
import viewworld  # noqa: E402
real_things = lodobj.things_of
lodobj.things_of = lambda gd_, pr_, w: [('+000801', 100.0, 200.0, 26.0, 0.0, 1.0), ('+000900', 5000.0, 0.0, 0.0, 0.0, 1.0)]
try:
    leave = viewworld.replaced(gd, None, None)
    check('the city thing under one of another kind is left out', leave('+000800', 100.5, 199.5, 26.0))
    check('a copy of the same thing keeps its far copy', not leave('+000900', 5000.0, 0.0, 0.0))
    check('a thing where the small world has nothing keeps it', not leave('+000800', 3000.0, 200.0, 26.0))
    check('a different thing a little way off keeps it', not leave('+000800', 120.0, 200.0, 26.0))
finally:
    lodobj.things_of = real_things
