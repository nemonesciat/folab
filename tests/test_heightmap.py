import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Height maps: Goodsprings' 3 x 3 cells out as a 16-bit PNG and straight back (the same ground within the
picture's precision), a brightened copy back (higher, edges kept), and an 8-bit picture made elsewhere (stretched over
the area, between the heights asked for)."""
import struct, zlib
import gamedata, land, tes4, heightmap


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
def heights(cx, cy):
    e = gd.land_at(w, cx, cy)
    return land.heights_of(dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1])))['VHGT']) if e else None
png = heightmap.export(heights, gd.key(w), -19, -1, 3, 3)
W, H, vals, text = heightmap.read_png(png)
check('97 x 97 pixels for 3 x 3 cells, the place written in', (W, H) == (97, 97) and text['x'] == -19 and text['w'] == 3)
check('black is the lowest point, white the highest', min(vals) == 0 and max(vals) == 1)
back = heightmap.apply(png, heights)
worst = max(abs(a - b) for (k, hs) in back.items() for a, b in zip(hs, heights(*k)))
check('straight back: the same ground (within %.2f units)' % worst, len(back) == 9 and worst < (text['high'] - text['low']) / 65535 * 2 + 0.01)
# brightened by a tenth of the range: higher inside, the area's edge kept
raw = struct.pack('>%dH' % (W * H), *[min(65535, int(v * 65535) + 6553) for v in vals])
up = heightmap.write_png16(W, H, struct.unpack('>%dH' % (W * H), raw), text)
new = heightmap.apply(up, heights)
mid = new[(-18, 0)][16 * 33 + 16] - heights(-18, 0)[16 * 33 + 16]
check('brighter is higher (the middle up %.0f)' % mid, mid > 0.05 * (text['high'] - text['low']))
check('the outer edge keeps its heights', new[(-19, -1)][0] == heights(-19, -1)[0] and new[(-17, 1)][33 * 33 - 1] == heights(-17, 1)[33 * 33 - 1])
check('an inner edge between two cells agrees', new[(-19, 0)][16 * 33 + 32] == new[(-18, 0)][16 * 33])
# a picture from elsewhere: 8-bit RGB, 10 x 10, all mid-grey, no FOLab text
rows = b''.join(b'\0' + bytes([128, 128, 128]) * 10 for _ in range(10))
def chunk(tag, d): return struct.pack('>I', len(d)) + tag + d + struct.pack('>I', zlib.crc32(tag + d) & 0xFFFFFFFF)
other = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 10, 10, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
flat = heightmap.apply(other, heights, -18, 0, 1, 1, 8000, 9000)
check('a picture from elsewhere: mid-grey is halfway', abs(flat[(-18, 0)][16 * 33 + 16] - (8000 + 1000 * 128 / 255)) < 0.01)
try:
    heightmap.apply(other, heights)
    check('one with nothing to say where it goes is refused', False)
except ValueError:
    check('one with nothing to say where it goes is refused', True)
