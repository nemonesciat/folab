import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Height files: GeoTIFFs written here in every way the reader promises (uncompressed, LZW, Deflate; 16-bit and float; strips and tiles;
both byte orders; predictors), each giving back the same numbers; geo tags for pixel size and origin; no-data; SRTM squares; PNG."""
import math, struct, tempfile, zipfile, gzip
import elevation, heightmap
import mapfixtures as fx


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


W, H = 37, 23
ints = [(r * 100 + c * 3 - 400) for r in range(H) for c in range(W)]
floats = [(r * 12.5 + c * 0.25 - 40.5) for r in range(H) for c in range(W)]
near = lambda a, b: all(abs(x - y) < 1e-3 for x, y in zip(a, b)) and len(a) == len(b)
# every way of storing the same numbers
for comp, cname in ((1, 'plain'), (5, 'LZW'), (8, 'Deflate')):
    for order, oname in (('<', 'little'), ('>', 'big')):
        for lay, lname in (({'rows': 5}, 'strips'), ({'tiled': (16, 16)}, 'tiles')):
            r = elevation.read_bytes('a.tif', fx.tiff(W, H, ints, 'h', comp, order, **lay))
            check('16-bit %s %s-endian %s' % (cname, oname, lname), near(r.v, ints) and (r.w, r.h) == (W, H))
            r = elevation.read_bytes('a.tif', fx.tiff(W, H, floats, 'f', comp, order, **lay))
            check('float %s %s-endian %s' % (cname, oname, lname), near(r.v, floats))
for comp in (5, 8):
    r = elevation.read_bytes('a.tif', fx.tiff(W, H, ints, 'h', comp, '<', rows=4, pred=2))
    check('16-bit with predictor 2, compression %d' % comp, near(r.v, ints))
    r = elevation.read_bytes('a.tif', fx.tiff(W, H, ints, 'h', comp, '>', tiled=(32, 32), pred=2))
    check('big-endian tiled with predictor 2, compression %d' % comp, near(r.v, ints))
    r = elevation.read_bytes('a.tif', fx.tiff(W, H, floats, 'f', comp, '<', rows=4, pred=3))
    check('float with predictor 3, compression %d' % comp, near(r.v, floats))
big = [(i * 7919) % 40000 for i in range(300 * 300)]            # (long enough for LZW's codes to grow to 12 bits and start over)
r = elevation.read_bytes('a.tif', fx.tiff(300, 300, big, 'H', 5, '<'))
check('LZW over a big picture, its table full and cleared', near(r.v, big))
r = elevation.read_bytes('a.tif', fx.tiff(W, H, ints, 'h', 8, '<', spp=2))
check('two bands: the first is the height', near(r.v, ints) and any('band' in n for n in r.notes))

# geo tags
geographic = {1024: 2, 1025: 1, 2048: 4326}
r = elevation.read_bytes('a.tif', fx.tiff(W, H, ints, 'h', 1, '<', scale=(0.001, 0.001, 0), tie=(0, 0, 0, -115.0, 36.0, 0), geokeys=geographic))
g = r.geo
check('degrees: origin moved to the first pixel\'s centre', g['kind'] == 'deg' and abs(g['x0'] - (-114.9995)) < 1e-9 and abs(g['y0'] - 35.9995) < 1e-9)
mx, my = r.metres_per_pixel()
check('degrees: a pixel is %.1f x %.1f m at 36 N' % (mx, my), abs(my - 110.95) < 0.2 and abs(mx - 90.2) < 0.3)
c, row = r.to_pixel(35.99, -114.99)
check('a spot on Earth to a pixel', abs(c - 9.5) < 1e-6 and abs(row - 9.5) < 1e-6)
r = elevation.read_bytes('a.tif', fx.tiff(W, H, ints, 'h', 1, '<', scale=(0.001, 0.001, 0), tie=(0, 0, 0, -115.0, 36.0, 0), geokeys={1024: 2, 1025: 2, 2048: 4326}))
check('a point pixel: origin is its centre', abs(r.geo['x0'] - (-115.0)) < 1e-9)
utm = {1024: 1, 1025: 1, 3072: 32611, 3076: 9001}
r = elevation.read_bytes('a.tif', fx.tiff(W, H, ints, 'h', 1, '<', scale=(30, 30, 0), tie=(0, 0, 0, 660000.0, 3990000.0, 0), geokeys=utm))
check('metres: a pixel is 30 m', r.geo['kind'] == 'proj' and r.metres_per_pixel() == (30, 30))
x, y = elevation.project(32611, 36.0, -115.0)
check('UTM 11N at its known point (%.1f, %.1f)' % (x, y), abs(x - 680000) < 700 and abs(y - 3985000) < 3000)
x, y = elevation.project(32633, 0.0, 15.0)
check('UTM on the equator at its central meridian is 500000, 0', abs(x - 500000) < 1e-6 and abs(y) < 1e-6)
x, y = elevation.project(32633, 52.0, 15.0)
check('UTM 33N at 52 N on its central meridian: 5,761,038 m north, as the tables give', abs(x - 500000) < 1e-6 and abs(y - 5761038) < 5)
x, y = elevation.project(3857, 0.0, 180.0)
check('web mercator at 180 E', abs(x - 20037508.34) < 0.1 and abs(y) < 1e-6)
check('a projection FOLab doesn\'t know says so', elevation.project(27700, 51.0, 0.0) is None)
feet = {1024: 1, 1025: 1, 3072: 32611, 3076: 9002, 4099: 9002}
r = elevation.read_bytes('a.tif', fx.tiff(4, 4, [1000.0] * 16, 'f', 1, '<', scale=(100, 100, 0), tie=(0, 0, 0, 0, 0, 0), geokeys=feet))
check('feet: map units and heights turned into metres', abs(r.metres_per_pixel()[0] - 30.48) < 1e-6 and abs(r.v[0] - 304.8) < 0.01)
r = elevation.read_bytes('a.tif', fx.tiff(4, 4, [5.0] * 16, 'f', 1, '<', matrix=(10, 0, 0, 500, 0, -20, 0, 900, 0, 0, 0, 0, 0, 0, 0, 1), geokeys={1024: 1, 3072: 32611}))
check('ModelTransformation: pixel size and origin', r.geo['dx'] == 10 and r.geo['dy'] == 20 and r.geo['x0'] == 505 and r.geo['y0'] == 890)
r = elevation.read_bytes('a.tif', fx.tiff(4, 4, [5] * 16, 'h'))
check('no geo tags: says so, and goes on', r.geo is None and any('where on Earth' in n for n in r.notes))

# no data
vals = list(floats)
vals[10] = -9999.0
vals[11] = -3.4028234663852886e+38
vals[12] = float('nan')
r = elevation.read_bytes('a.tif', fx.tiff(W, H, vals, 'f', 8, nodata='-9999'))
bad = [i for i, x in enumerate(r.v) if x != x]
check('no-data, the greatest float and NaN are all holes', bad == [10, 11, 12])
vals = list(ints); vals[3] = -32768
r = elevation.read_bytes('a.tif', fx.tiff(W, H, vals, 'h', 1))
check('-32768 in 16 bits is a hole even unsaid', r.v[3] != r.v[3] and r.stats()[2] == 1)
vals = list(ints); vals[3] = 7777
r = elevation.read_bytes('a.tif', fx.tiff(W, H, vals, 'h', 1, nodata=7777))
check('a 16-bit no-data value', r.v[3] != r.v[3] and r.stats()[1] == max(ints))

# errors in words
for what, data in (('an unknown compression', fx.tiff(4, 4, [1] * 16, 'h')[:0] + b'II*\0' + struct.pack('<I', 8) + struct.pack('<H', 3) + struct.pack('<HHII', 256, 4, 1, 4) +
                    struct.pack('<HHII', 257, 4, 1, 4) + struct.pack('<HHII', 259, 3, 1, 7) + bytes(4)),):
    try:
        elevation.read_bytes('a.tif', data)
        check(what, False)
    except elevation.MapFileError as e:
        check('refused in words: ' + str(e)[:60], 'compressed' in str(e))
try:
    elevation.read_bytes('a.txt', b'hello')
    check('not a height file', False)
except elevation.MapFileError as e:
    check('not a height file: says what it reads', 'GeoTIFF' in str(e))

# SRTM
n = 121
data = fx.hgt(n, lambda r, c: None if (r, c) == (5, 5) else 1000 + r * 2 - c)
r = elevation.read_bytes('N36W116.hgt', data)
check('SRTM: north row first, big-endian', r.at(0, 0) == 1000 and r.at(120, 0) == 880 and r.at(0, 120) == 1240)
check('SRTM: a hole', r.at(5, 5) != r.at(5, 5))
check('SRTM: the name says where (its corner points are shared with the next square)', r.geo['x0'] == -116 and r.geo['y0'] == 37 and abs(r.geo['dx'] - 1 / 120) < 1e-12)
r2 = elevation.read_bytes('S01E010.hgt', data)
check('SRTM: south and east', r2.geo['y0'] == 0 and r2.geo['x0'] == 10)
check('SRTM: spot to pixel', all(abs(a - b) < 1e-6 for a, b in zip(r.to_pixel(36.5, -115.5), (60, 60))))
try:
    elevation.read_hgt(b'123', 'x.hgt')
    check('a wrong-sized .hgt', False)
except elevation.MapFileError:
    check('a wrong-sized .hgt is refused', True)

# PNG
tmp = tempfile.mkdtemp()
png = heightmap.write_png16(3, 2, [0, 32768, 65535, 100, 200, 300])
r = elevation.read_bytes('h.png', png)
check('16-bit PNG: values 0-1, no heights of its own', r.plain and abs(r.at(2, 0) - 1) < 1e-6 and abs(r.at(1, 0) - 0.5) < 1e-3 and r.geo is None and not r.notes)
png = heightmap.write_png16(3, 2, [0, 32768, 65535, 100, 200, 300], {'low': 100, 'high': 900})
check('FOLab\'s own height map knows its heights', elevation.read_bytes('h.png', png).folab == {'low': 100.0, 'high': 900.0})

# from disk, zipped and gzipped
p = os.path.join(tmp, 'N10E020.hgt')
open(p, 'wb').write(data)
check('from disk', elevation.read_file(p).at(0, 0) == 1000)
z = os.path.join(tmp, 'N10E020.SRTMGL3.hgt.zip')
with zipfile.ZipFile(z, 'w') as zf:
    zf.writestr('readme.txt', 'x'); zf.writestr('N10E020.hgt', data)
r = elevation.read_file(z)
check('a .zip holding one', r.at(0, 0) == 1000 and r.geo['x0'] == 20)
g = os.path.join(tmp, 'N10E020.hgt.gz')
with gzip.open(g, 'wb') as f:
    f.write(data)
check('a .gz holding one', elevation.read_file(g).geo['y0'] == 11)
t = os.path.join(tmp, 'm.tif')
open(t, 'wb').write(fx.tiff(W, H, ints, 'h', 5, '<', tiled=(16, 16), scale=(30, 30, 0), tie=(0, 0, 0, 5000, 9000, 0), geokeys=utm))
r = elevation.read_file(t, lambda n, m: None)
check('a tiled LZW GeoTIFF from disk', near(r.v, ints) and r.geo['x0'] == 5015)
check('its numbers', r.stats() == (min(ints), max(ints), 0))
