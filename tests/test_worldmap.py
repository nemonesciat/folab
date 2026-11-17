"""The Pip-Boy's world map (worldmap.py): a picture drawn from a world's heights, sea and what stands on it, put in the
mod's own files, the world record pointed at it with MNAM covering the cells it shows; saved and read back. Never starts
the game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import dds  # noqa: E402
import gamedata  # noqa: E402
import library  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import worldmap  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'NVDLC02ZionCanyon')
pr = project.Project.create('Map')
gd.overlay = library.Overlay(lambda: pr)
x0, y0, n = worldmap._square(gd.grid(world))
xs = [k[0] for k in gd.grid(world)]
ys = [k[1] for k in gd.grid(world)]
check('the square takes in every cell of the world, with a margin', x0 < min(xs) and y0 < min(ys) and x0 + n - 1 > max(xs) and y0 + n - 1 > max(ys), (x0, y0, n))
rgba, square = worldmap.picture(gd, pr, world, size=128)
check('a picture of the size asked, grey as the game\'s are', len(rgba) == 128 * 128 * 4 and all(rgba[i] == rgba[i + 1] == rgba[i + 2] for i in range(0, len(rgba), 4 * 37)))
corner = rgba[(3 * 128 + 3) * 4]
check('the frame is drawn in the corners', corner > 150, corner)
ops, rep = worldmap.ops(gd, pr, world, size=128)
dest = os.path.join(library.assets_dir(pr), 'textures', rep['picture'])
check('the picture is in the mod\'s own files, a DDS the game reads', os.path.isfile(dest) and tuple(dds.decode(open(dest, 'rb').read(), 128)[:2]) == (128, 128), dest)
rec = ops[0]['record']
check('the world names it', ops[0]['op'] == 'record' and ops[0]['key'] == gd.key(world) and recordio.field(rec, 'ICON') == rep['picture'])
pr.apply('map', ops)
path = pr.plugin_path()
import espwrite  # noqa: E402
espwrite.write(gd, pr, path)
check('the mod saves', os.path.isfile(path))
if os.path.isfile(path):
    g2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
    f = g2.fields(next(w for w in g2.worlds() if g2.edid(w) == 'NVDLC02ZionCanyon'))
    m = struct.unpack('<2i4h', f['MNAM'])
    check('saved and read back: the picture and the square of cells it covers', f.get('ICON', b'')[:-1].decode() == rep['picture'] and m == (128, 128, x0, y0 + n - 1, x0 + n - 1, y0), m)
