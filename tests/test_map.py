import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""The flat map: a ground texture's average colour, a tile's picture (size, filled where there's land, clear where
there isn't, the mod's land drawn in), and Go to a place."""
import struct, zlib
import gamedata, land, maptiles, dds


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


def pixels(png):
    w, h = struct.unpack('>II', png[16:24])
    pos, idat = 8, b''
    while pos < len(png):
        n = struct.unpack('>I', png[pos:pos + 4])[0]; tag = png[pos + 4:pos + 8]
        if tag == b'IDAT': idat += png[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    return w, h, [raw[r * (w * 4 + 1) + 1:(r + 1) * (w * 4 + 1)] for r in range(h)]


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
ltex = next(f for f, (i, r) in gd.forms.items() if r.tag == 'LTEX' and land.texture_of_fid(gd, f, {}) and 'dirt' in gd.edid(f).lower())
c = dds.average_colour(gd.read_file(land.texture_of_fid(gd, ltex, {})))
check('a dirt texture averages to an earthy colour %s' % (c,), c and c[0] >= c[2] and 30 < sum(c) / 3 < 230)
p = maptiles.Painter(gd)
wd, ht, rows = pixels(p.tile(w, -2, 0))
check('a tile is 256 x 256', (wd, ht) == (256, 256))
alpha = [row[k] for row in rows for k in range(3, len(row), 4)]
check('Goodsprings\' tile is all ground', min(alpha) == 255)
edge = max(x for x, y in gd.grid(w)) // 16 + 1
_, _, rows2 = pixels(p.tile(w, edge, 0))
check('past the world\'s edge, clear', max(row[k] for row in rows2 for k in range(3, len(row), 4)) == 0)
# the mod's land in the picture: Goodsprings' square raised into a steep bump changes its pixels
cell = gd.grid(w)[(-18, 0)]
L = land.decode(gd, gd.land[cell], {})
L['h'] = [v + (900 if (k // 33) % 4 < 2 else 0) for k, v in enumerate(L['h'])]
_, _, rows3 = pixels(p.tile(w, -2, 0, {gd.key(cell): L}))
i, j = -18 - (-32), 0
block = lambda rs: b''.join(rs[(15 - j) * 16 + r][i * 64:(i + 1) * 64] for r in range(16))
check('the mod\'s land is drawn in', block(rows3) != block(rows))
check('the squares round it are the same', rows3[0] == rows[0])
