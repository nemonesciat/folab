"""The sea from the map's coastline (coast.py): the water's side of the line becomes sea bed that slopes away from the
shore to a cutoff depth, the land's side stands clear of the water whatever the height file said, an island stays an
island, and a coastline with a gap in it changes nothing. Then the same through the map reader and the making of a
world: a small height file whose shallows are recorded as sea level, as real ones are."""
import array
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import coast  # noqa: E402
import mapscale as MS  # noqa: E402
import osm  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def flat(w, h, z):
    return MS.Grid(w, h, array.array('f', [z] * ((w * 32 + 1) * (h * 32 + 1))), -(w // 2), -(h // 2))


def at(g, x, y):
    """The height at a spot in game units."""
    return g.at(int(round(x / 128.0)) - g.x0 * 32, int(round(y / 128.0)) - g.y0 * 32)


# ---------- a shore running west to east, the land to the north ----------
# (land on the left of the way the line runs: going east, the left is north)
g = flat(4, 4, 0.0)                     # 4 x 4 cells of ground the height file calls sea level: x and y from -8192 to 8192
r = coast.shape_sea(g, [[(-9000.0, 0.0), (9000.0, 0.0)]], depth=640)
check('the line is found and the grid split', r and r['sea'] > 0 and r['raised'] > 0, r)
check('north of the line is land, clear of the water', at(g, 0, 2000) == coast.BEACH and at(g, -6000, 7000) == coast.BEACH)
check('south of it is sea', at(g, 0, -2000) < 0 and at(g, 5000, -7000) < 0)
near, mid, far = at(g, 0, -256), at(g, 0, -1280), at(g, 0, -7000)
check('the bed drops gently away from the shore', 0 > near > mid > far, (near, mid, far))
check('about one down for ten out', abs(mid - (-128)) <= 24, mid)
check('and stops at the cutoff depth', far == -640 and min(g.pts) == -640, far)
check('every height on a whole step', all(v % 8 == 0 for v in g.pts))
sea_share = sum(1 for v in g.pts if v < 0) / len(g.pts)
check('half the grid each', 0.45 < sea_share < 0.52, round(sea_share, 3))

# ---------- the same line the other way round: the land is south ----------
g = flat(4, 4, 0.0)
coast.shape_sea(g, [[(9000.0, 0.0), (-9000.0, 0.0)]], depth=640)
check('the way the line runs says which side is land', at(g, 0, -2000) == coast.BEACH and at(g, 0, 2000) < 0)

# ---------- land the height file has well above the sea keeps its height; an island stays dry ----------
g = flat(4, 4, 0.0)
for gy in range(g.down):
    for gx in range(g.across):
        if gy > g.down // 2 + 20:
            g.pts[gy * g.across + gx] = 800.0
island = [(-1000.0, -5000.0), (-1000.0, -3000.0), (1000.0, -3000.0), (1000.0, -5000.0), (-1000.0, -5000.0)]   # (clockwise seen from above: land inside, on... the left)
island = island[::-1]
coast.shape_sea(g, [[(-9000.0, 0.0), (9000.0, 0.0)], island], depth=640)
check('high ground is left as it was', at(g, 0, 6000) == 800.0)
check('an island in the sea is land', at(g, 0, -4000) == coast.BEACH and at(g, 3000, -4000) < 0 and at(g, 0, -6500) < 0, (at(g, 0, -4000), at(g, 3000, -4000)))
check('the bed shallows toward the island too', at(g, 1400, -4000) > at(g, 4500, -4000))

# ---------- a coastline that stops short, and one that makes no sense ----------
g = flat(4, 4, 0.0)
r = coast.shape_sea(g, [[(-9000.0, 0.0), (-1000.0, 0.0)], [(1000.0, 0.0), (9000.0, 0.0)]], depth=640)
check('a gap between two stretches is closed by carrying each on the way it was going', r.get('sea') and at(g, 0, 2000) == coast.BEACH and at(g, 0, -2000) < 0, r)
g = flat(4, 4, 0.0)
r = coast.shape_sea(g, [[(-9000.0, 0.0), (2000.0, 0.0)]], depth=640)
check('a stretch that ends inside the world is carried to its edge', r.get('sea') and at(g, 6000, 2000) == coast.BEACH and at(g, 6000, -2000) < 0, r)
g = flat(4, 4, 24.0)
before = g.pts.tobytes()
# (two shores that can't both be right: the strip between them is land by one and sea by the other)
r = coast.shape_sea(g, [[(-9000.0, 0.0), (9000.0, 0.0)], [(-9000.0, 3000.0), (9000.0, 3000.0)]], depth=640)
check('lines that call the same ground both land and sea: said, and the grid left alone', r == {'leak': True} and g.pts.tobytes() == before, r)
g = flat(4, 4, 24.0)
check('no coastline on the world: nothing to do', coast.shape_sea(g, [[(50000.0, 0.0), (60000.0, 0.0)]]) is None and set(g.pts) == {24.0})

# ---------- the map reader keeps the coastline ----------
xml = b'''<?xml version="1.0"?><osm version="0.6">
<bounds minlat="21.0" minlon="-158.0" maxlat="21.1" maxlon="-157.9"/>
<node id="1" lat="21.05" lon="-158.0"/><node id="2" lat="21.05" lon="-157.95"/><node id="3" lat="21.05" lon="-157.9"/>
<node id="4" lat="21.08" lon="-157.96"/><node id="5" lat="21.08" lon="-157.94"/>
<way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><tag k="natural" v="coastline"/></way>
<way id="11"><nd ref="4"/><nd ref="5"/><tag k="highway" v="residential"/></way>
</osm>'''
d = osm.read(xml, 'coast.osm')
check('the coastline is read, in the order it was drawn', d.coast == [[(21.05, -158.0), (21.05, -157.95), (21.05, -157.9)]] and d.counts()['coast'] == 1, d.coast)
check('and no longer counted as left out', not any('coast' in k for k in d.skipped))

# ---------- roofs a height file measured ----------
g = flat(2, 2, 64.0)
a = g.across


def lump(cx, cy, half, z):
    for yy in range(cy - half, cy + half + 1):
        for xx in range(cx - half, cx + half + 1):
            g.pts[yy * a + xx] = z


lump(16, 16, 3, 900.0)          # a tower block with a building on the map
lump(48, 48, 3, 900.0)          # the same shape with none: a crag, a crater's rim
spot = ((16 + g.x0 * 32) * 128.0, (16 + g.y0 * 32) * 128.0)
moved = coast.level_bumps(g, [spot])
check('a lump on flat ground where the map has a building comes down to the ground', g.pts[16 * a + 16] == 64.0 and moved == 49, moved)
check('the same lump where it has none is left: it may be a hill', g.pts[48 * a + 48] == 900.0)
g = flat(2, 2, 64.0)
for yy in range(g.down):
    for xx in range(a):
        g.pts[yy * a + xx] = 64.0 + 40.0 * xx      # a hillside
lump(30, 30, 2, 3000.0)
check('a lump on a slope is left', coast.level_bumps(g, [((30 + g.x0 * 32) * 128.0, (30 + g.y0 * 32) * 128.0)]) == 0)
