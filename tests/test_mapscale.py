import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Scale: a raster at two scales gives the expected heights at known points, the preview's numbers are right before anything is made, every height
is on a step, cell edges meet, slopes stay storable, holes are filled, limits and warnings speak up."""
import array, math
import elevation, land, mapscale as MS


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


def raster(w, h, fn, mpp=30.0, name='t.tif'):
    v = array.array('f', [fn(c, r) for r in range(h) for c in range(w)])
    return elevation.Raster(w, h, v, {'kind': 'proj', 'x0': 1000.0, 'y0': 2000.0, 'dx': mpp, 'dy': mpp, 'epsg': 32611, 'unit': 1.0}, name)


check('a cell is about 58 m, 1 km about 17 cells', abs(MS.metres_per_cell() - 58.51) < 0.01 and abs(MS.cells_for_km() - 17.09) < 0.01)
# a plane: east rises 1 m a pixel, south rises 2 m. 30 m pixels; 400 x 300 pixels: 12 km x 9 km
plane = raster(401, 301, lambda c, r: 500 + c * 1.0 + r * 2.0)
# at 1:4, exag 1, base 500
p = MS.Plan(plane, {'compress': 4, 'exag': 1, 'base': 500})
g = MS.heights(p)
upx = 30 * 70 / 4                      # 525 game units a pixel
check('1:4: units a pixel', p.upx == upx)
check('1:4: whole cells in the file (%d x %d)' % (p.W, p.H), p.W == int(400 * upx / 4096) and p.H == int(300 * upx / 4096))


def expect(p, g, gx, gy):
    col, row = p.col0 + gx * p.ppx, p.row0 + (g.down - 1 - gy) * p.ppy
    return (500 + col + row * 2 - p.base) * 70 / p.compress * p.exag


worst = max(abs(g.at(gx, gy) - expect(p, g, gx, gy)) for gy in range(0, g.down, 37) for gx in range(0, g.across, 41))
check('1:4: every height as worked by hand (worst off by %.1f, half a step is 4)' % worst, worst <= 4.01)
check('1:4: on whole 8-unit steps', all(z % 8 == 0 for z in g.pts))
# at 1:20, exag 3: pixels now smaller than a land point's reach? 30 m pixel = 105 units; ppx > 1: averaged down, a plane stays a plane
p2 = MS.Plan(plane, {'compress': 20, 'exag': 3, 'base': 400})
g2 = MS.heights(p2)
check('1:20: pixels per land point %.2f' % p2.ppx, abs(p2.ppx - 128 / (30 * 70 / 20)) < 1e-9 and p2.ppx > 1)
worst = max(abs(g2.at(gx, gy) - (500 + (p2.col0 + gx * p2.ppx) + 2 * (p2.row0 + (g2.down - 1 - gy) * p2.ppy) - 400) * 70 / 20 * 3) for gy in range(0, g2.down, 13) for gx in range(0, g2.across, 11))
check('1:20 x3: every height as worked by hand (worst off by %.1f)' % worst, worst <= 4.01)
# known points in game coordinates
x, y = p.game_xy(p.col0, p.row0)
check('the rectangle\'s north-west corner is the world\'s', x == p.x0 * 4096 and y == (p.y0 + p.H) * 4096)
check('pixel to game and back', all(abs(a - b) < 1e-6 for a, b in zip(p.pixel_of(*p.game_xy(37.5, 80.25)), (37.5, 80.25))))
# a single peak of known height at a known spot, at two scales: at real size the point lands on it exactly
peak = raster(129, 129, lambda c, r: 100.0 + max(0, min(50, 80 - math.hypot(c - 64, r - 64) * 5)), mpp=128 / 70)   # (a pixel exactly a land point; a flat top 6 pixels round)
p3 = MS.Plan(peak, {'compress': 1, 'exag': 1, 'base': 100})
g3 = MS.heights(p3)
check('real size: a pixel is a land point', abs(p3.ppx - 1) < 1e-9)
check('real size: the top is 50 m = 3,500 units, on its nearest step', g3.at(64, 64) == 3504 and p3.W == 4)
check('real size: flat ground is at 0', g3.at(0, 0) == 0)
p4 = MS.Plan(peak, {'compress': 2, 'exag': 1, 'base': 100})
g4 = MS.heights(p4)
check('half size: the same top half as high (%d), half as wide' % max(g4.pts), max(g4.pts) == 1752 and p4.W == 2)
check('half size: the middle of the world is the peak', g4.at(g4.across // 2, g4.down // 2) == max(g4.pts))
# north is at the top
tilt = raster(129, 129, lambda c, r: 1000 - r * 1.0, mpp=128 / 70)
g5 = MS.heights(MS.Plan(tilt, {'compress': 1, 'exag': 1, 'base': 0}))
check('north in the file is north in the world', g5.at(10, g5.down - 1) > g5.at(10, 0))
# edges
rough = raster(257, 257, lambda c, r: 300 + 80 * math.sin(c / 7.0) * math.cos(r / 11.0) + (c * r % 17), mpp=128 / 70)
p6 = MS.Plan(rough, {'compress': 1, 'exag': 1, 'base': 0})
g6 = MS.heights(p6)
ok = True
for j in range(p6.H):
    for i in range(p6.W - 1):
        a, b = g6.cell(i, j), g6.cell(i + 1, j)
        ok = ok and all(a[r * 33 + 32] == b[r * 33] for r in range(33))
for j in range(p6.H - 1):
    for i in range(p6.W):
        a, b = g6.cell(i, j), g6.cell(i, j + 1)
        ok = ok and a[32 * 33:] == b[:33]
check('edges between cells are the same points', ok)
ok = True
for j in range(p6.H):
    for i in range(p6.W):
        h = g6.cell(i, j)
        ok = ok and land.heights_of(land.encode_heights(h)) == h
check('every cell survives VHGT exactly', ok)
# too steep: a cliff of 200 m in one pixel at 1:1
cliff = raster(129, 129, lambda c, r: 0 if c < 64 else 200, mpp=128 / 70)
g7 = MS.heights(MS.Plan(cliff, {'compress': 1, 'exag': 1, 'base': 0}))
check('a cliff too steep for VHGT is brought within a step (%d points moved)' % g7.stats['too_steep'], g7.stats['too_steep'] > 0 and all(abs(g7.at(gx + 1, 5) - g7.at(gx, 5)) <= 1016 for gx in range(128)))
ok = True
for j in range(g7.H):
    for i in range(g7.W):
        h = g7.cell(i, j)
        ok = ok and land.heights_of(land.encode_heights(h)) == h
check('and still survives VHGT exactly', ok)
check('it comes down from the top, never fills the valley', g7.at(0, 5) == 0 and max(g7.pts) == 14000)
# holes
holey = raster(129, 129, lambda c, r: float('nan') if (60 <= c <= 62 and 60 <= r <= 62) or c > 110 else 200.0, mpp=128 / 70)
g8 = MS.heights(MS.Plan(holey, {'compress': 1, 'exag': 1, 'base': 0}))
check('a small hole is filled from round it', g8.at(61, 128 - 61) == 14000 and g8.stats['holes_filled'] > 0)
wide_hole = raster(257, 257, lambda c, r: float('nan') if c > 60 else 200.0, mpp=128 / 70)
g9 = MS.heights(MS.Plan(wide_hole, {'compress': 1, 'exag': 1, 'base': 0}))
check('a big hole is sea bed', g9.at(250, 5) == MS.SEA_BED and g9.stats['holes_sea'] > 0)
# preview's numbers
srtm = raster(1201, 1201, lambda c, r: 800.0 + (c % 9), mpp=90.0)
p = MS.Plan(srtm, {})
rep = p.report()
check('default scale fits the default size (1:%g, %d x %d)' % (p.compress, p.W, p.H), max(p.W, p.H) <= MS.DEFAULT_SIDE and p.compress in MS.COMPRESSIONS)
check('default height follows the scale', rep['exag'] == MS.default_exag(p.compress) and rep['exag'] > 1)
check('default base just under the lowest ground', rep['base'] == 799 and rep['z_low'] > 0 and not rep['water'])
check('numbers: cells, km, plugin size', rep['cells'] == p.W * p.H and rep['km_w'] > 100 and rep['plugin_mb'] > 1 and not rep['stop'])
real = MS.Plan(srtm, {'compress': 1, 'exag': 1})
check('real size is refused, with the reason (%s)' % format(real.count(), ','), real.report()['stop'] and 'Compress' in real.report()['stop'])
big = MS.Plan(srtm, {'compress': 25, 'exag': 1})
check('more than a DLC world warns but goes (%d)' % big.count(), MS.SOFT_CELLS < big.count() <= MS.HARD_CELLS and big.report()['warnings'] and not big.report()['stop'])
tall = MS.Plan(raster(129, 129, lambda c, r: 800.0 + r * 10), {'compress': 1, 'exag': 2, 'base': 0})
check('heights past the game\'s own warn', any('Heights run' in w for w in tall.report()['warnings']))
coast = raster(129, 129, lambda c, r: c * 1.0 - 20)
check('a file reaching the sea: base at sea level, water', MS.Plan(coast, {}).base == 0 and MS.Plan(coast, {}).report()['water'])
cut = MS.Plan(plane, {'compress': 4, 'exag': 1, 'rect': [100, 50, 200, 150]})
check('a rectangle comes out whole cells, %d x %d, inside what was asked' % (cut.W, cut.H), cut.W == int(100 * 525 / 4096) and cut.col0 >= 100 and cut.col0 + cut.W * cut.ppx * 32 <= 200 + 1e-6)
# a town cut from high ground in a tile whose corner is far lower (Goodsprings from N35W116: 1,082 m in a tile down to 295)
high = raster(401, 301, lambda c, r: 300.0 if c < 50 else 1100.0 + r * 0.5)
town = MS.Plan(high, {'compress': 1, 'exag': 1, 'rect': [200, 100, 300, 200]})
tr = town.report()
check('a rectangle\'s base is its own lowest ground, not the file\'s (%g)' % town.base, 1140 <= town.base <= 1150 and 0 < tr['z_low'] <= 140 and not any('Heights run' in w for w in tr['warnings']))
check('the whole file still goes by the whole file', MS.Plan(high, {'compress': 25}).base == 299)
one = MS.Plan(plane, {'compress': 4, 'rect': [0, 0, 1, 1]})
check('a tiny rectangle is still one cell, inside the file', one.W == one.H == 1 and one.col0 >= 0 and one.row0 >= 0)
# a plain picture
pic = elevation.Raster(129, 129, array.array('f', [r / 128 for r in range(129) for c in range(129)]), None, 'p.png', plain=True)
pp = MS.Plan(pic, {'mpp': 128 / 70, 'low_m': 100, 'high_m': 300, 'base': 100, 'compress': 1, 'exag': 1})
gp = MS.heights(pp)
check('a plain picture: black and white are what they\'re told', gp.at(5, gp.down - 1) == 0 and gp.at(5, 0) == 14000)
check('a plain picture warns', any('plain picture' in w for w in pp.report()['warnings']))
# one of FOLab's own height maps goes back at the same heights
own = elevation.Raster(129, 129, array.array('f', [r / 128 for r in range(129) for c in range(129)]), None, 'f.png', plain=True)
own.folab = {'low': 800.0, 'high': 2400.0}
po = MS.Plan(own, {'compress': 1, 'exag': 1, 'base': 0})
go = MS.heights(po)
check('FOLab\'s own height map: same size, same heights', po.W == 4 and go.at(0, go.down - 1) == 800 and go.at(0, 0) == 2400)
