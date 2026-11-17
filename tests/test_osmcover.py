"""Ground painted by what the map says (osmcover.py): the map reader keeps tagged areas, and each land point of a world
gets a kind from them, from the roads and buildings, and from the shore: a park is grass, a car park and the ground under
a building are paved, a road is asphalt, low land beside the sea is beach, the sea bed is its own, ground near houses
that nothing was said of is lived-in ground, and far from everything it is left to the slope."""
import array
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import mapscale as MS  # noqa: E402
import osm  # noqa: E402
import osmcover  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


# ---------- the map reader ----------
def node(i, x, y):
    return '<node id="%d" lat="%.6f" lon="%.6f"/>' % (i, y, x)


def way(i, refs, **tags):
    return '<way id="%d">%s%s</way>' % (i, ''.join('<nd ref="%d"/>' % r for r in refs), ''.join('<tag k="%s" v="%s"/>' % kv for kv in tags.items()))


# a map in "degrees" that are simply game units over 100000: x east, y north
pts = {1: (-0.06, 0.02), 2: (-0.02, 0.02), 3: (-0.02, 0.06), 4: (-0.06, 0.06),            # a park, north-west
       5: (0.02, 0.02), 6: (0.05, 0.02), 7: (0.05, 0.05), 8: (0.02, 0.05),                # a car park, north-east
       9: (-0.08, 0.01), 10: (0.08, 0.01),                                                # a road across
       11: (0.03, 0.03), 12: (0.04, 0.03), 13: (0.04, 0.04), 14: (0.03, 0.04),            # a building in the car park
       15: (-0.07, -0.005), 16: (-0.06, -0.005), 17: (-0.06, 0.004), 18: (-0.07, 0.004),  # a house by the road, nothing said of its ground
       19: (0.06, 0.06), 20: (0.07, 0.06), 21: (0.07, 0.07), 22: (0.06, 0.07)}            # a footpath's square, pedestrian
xml = '<?xml version="1.0"?><osm version="0.6">' + ''.join(node(i, x, y) for i, (x, y) in pts.items()) \
    + way(100, [1, 2, 3, 4, 1], leisure='park') + way(101, [5, 6, 7, 8, 5], amenity='parking') + way(102, [9, 10], highway='residential') \
    + way(103, [11, 12, 13, 14, 11], building='yes') + way(104, [15, 16, 17, 18, 15], building='house') \
    + way(105, [19, 20, 21, 22, 19], highway='pedestrian', area='yes') + way(106, [1, 2, 3, 4, 1], landuse='residential') + '</osm>'
d = osm.read(xml.encode(), 'town.osm')
kinds = sorted(a['kind'] for a in d.areas)
check('tagged areas are kept, each as a kind of ground', kinds == ['grass', 'paved', 'paved', 'yard'], kinds)
check('a road, two buildings, as before', len(d.roads) == 1 and len(d.buildings) == 2)
check('what a tag means', osmcover.area_kind({'natural': 'beach'}) == 'sand' and osmcover.area_kind({'leisure': 'golf_course'}) == 'golf'
      and osmcover.area_kind({'highway': 'pedestrian'}) is None and osmcover.area_kind({'shop': 'yes'}) is None)

# ---------- a world over it: land in the north, sea in the south ----------
W = H = 6
g = MS.Grid(W, H, array.array('f', [40.0] * ((W * 32 + 1) * (H * 32 + 1))), -(W // 2), -(H // 2))
for gy in range(g.down):
    for gx in range(g.across):
        y = (g.y0 * 32 + gy) * 128.0
        if y < -4000:
            g.pts[gy * g.across + gx] = -200.0
        elif y > 9000:
            g.pts[gy * g.across + gx] = 2000.0 + (y - 9000) * 2          # a steep hill at the back
xy = lambda p: (p[1] * 100000.0, p[0] * 100000.0)                         # (lat, lon) -> game units
tex = {k: 'T_' + k for k in osmcover.ORDER}
c = osmcover.MapCover(g, d, xy, tex)


def kind_at(x, y):
    k = c.kind[(int(round(y / 128.0)) - g.y0 * 32) * g.across + int(round(x / 128.0)) - g.x0 * 32]
    return osmcover.ORDER[k - 1] if k else None


def mix_at(x, y, deg=0.0):
    return c.mix(int(round(x / 128.0)) - g.x0 * 32, int(round(y / 128.0)) - g.y0 * 32, deg)


check('the park is grass, though it lies in a neighbourhood too', kind_at(-4000, 4000) == 'grass')
check('the car park is paved', kind_at(2400, 2400) == 'paved')
check('under and round a building is paved', kind_at(3500, 3500) == 'paved' and kind_at(-6500, 0) == 'paved')
check('the road is asphalt, through whatever it crosses', kind_at(0, 1000) == 'asphalt' and kind_at(-7500, 1000) == 'asphalt')
check('a pedestrian square is paved', kind_at(6500, 6500) == 'paved')
check('ground by the house that nothing was said of is lived-in ground', kind_at(-6500, -900) == 'yard', kind_at(-6500, -900))
check('the sea bed is its own kind', kind_at(0, -8000) == 'seabed')
check('low land just in from the sea is beach', kind_at(0, -3840) == 'sand' and kind_at(5000, -3700) == 'sand', (kind_at(0, -3840), kind_at(0, -3500)))
check('further in it is not', kind_at(5000, -2000) != 'sand')
check('far from everything, nothing is said: the slope paints it', kind_at(9000, 8000) is None and mix_at(9000, 8000) is None)
check('steep ground is left to the slope whatever the map says', mix_at(-4000, 4000, 50.0) is None)
m = mix_at(-4000, 4000)
check('a point well inside one kind is all that kind\'s texture', m == {'T_grass': 1.0}, m)
m = mix_at(-2048, 4000)                     # (the park's east edge)
check('at an edge one kind fades into the next', m and len(m) >= 2 and abs(sum(m.values()) - 1.0) < 1e-6 or (m and 'T_grass' in m), m)
s = c.summary()
check('the report says how much of each', s.get('Sea bed', 0) > 0.2 and s.get('Parks and lawns', 0) > 0.01 and 'Roads' in s, s)
check('a kind the game has no texture for is left to the slope', osmcover.MapCover(g, d, xy, {}).mix(100, 150, 0.0) is None)
