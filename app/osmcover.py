"""Ground types from the map itself: what OpenStreetMap says each piece of ground is (a beach, a park, a car park, a
neighbourhood of houses) and where the roads and buildings are, turned into which of the game's ground textures goes
where. No land-cover file is needed; this is landcover.py's job done from the same file the roads come from.

Every land point of the world (mapscale.Grid) gets a kind. From the least sure to the most, each laid over the last:
    what stands near buildings and roads with no word from the map   'yard'
    the map's own areas, widest meaning first                        'yard' 'trees' 'scrub' 'grass' 'paved' 'sand' ...
    under and round each building                                    'paved'
    along each road                                                  'asphalt'
    land beside the sea, low and not built on                        'sand'
    the sea bed                                                      'seabed'
Steep ground is left to the slope, as everywhere: nothing here paints a cliff. mapworld.Painter asks mix() as the
world is made, so the textures go in the plugin."""
import array
import collections
import math

POINT = 128.0
PER_CELL = 32
STEEP = 32.0
# kind: (what the panel calls it, the game's ground texture by editor ID)
KINDS = [
    ('yard', 'Round houses', 'LScrubDirtStripGreenNV01'),
    ('trees', 'Woods', 'LScrubDirtStripGreenNV01Grass'),
    ('scrub', 'Scrub', 'ScrubBarrenWastes01Sage'),
    ('farm', 'Fields', 'LGrassGreenFarmlandsNV'),
    ('grass', 'Parks and lawns', 'LGrassGreenSuburbsNoGrass'),
    ('golf', 'Golf course', 'LGrassGolfNoneNV'),
    ('rock', 'Bare rock', 'LRockWastelandNV'),
    ('wet', 'Wetland', 'LWaterMossNV01'),
    ('paved', 'Paved ground', 'Pavement'),
    ('asphalt', 'Roads', 'LAsphaltWasteland01'),
    ('sand', 'Beach', 'LWaterSandNV01'),
    ('seabed', 'Sea bed', 'LWaterGravelSandNV01'),
]
ORDER = [k for k, _l, _t in KINDS]
CODE = {k: n + 1 for n, k in enumerate(ORDER)}
# what the map's tags mean here (osm.py reads these into OsmData.areas)
AREA_KIND = {
    ('natural', 'beach'): 'sand', ('natural', 'sand'): 'sand', ('natural', 'shoal'): 'sand', ('natural', 'dune'): 'sand',
    ('leisure', 'park'): 'grass', ('leisure', 'garden'): 'grass', ('leisure', 'pitch'): 'grass', ('leisure', 'playground'): 'grass',
    ('leisure', 'recreation_ground'): 'grass', ('leisure', 'common'): 'grass', ('leisure', 'dog_park'): 'grass', ('leisure', 'golf_course'): 'golf',
    ('landuse', 'grass'): 'grass', ('landuse', 'meadow'): 'grass', ('landuse', 'recreation_ground'): 'grass', ('landuse', 'village_green'): 'grass',
    ('landuse', 'cemetery'): 'grass', ('natural', 'grassland'): 'grass', ('landuse', 'greenfield'): 'grass',
    ('natural', 'wood'): 'trees', ('landuse', 'forest'): 'trees', ('natural', 'scrub'): 'scrub', ('natural', 'heath'): 'scrub',
    ('landuse', 'farmland'): 'farm', ('landuse', 'orchard'): 'farm', ('landuse', 'vineyard'): 'farm',
    ('natural', 'bare_rock'): 'rock', ('natural', 'scree'): 'rock', ('natural', 'wetland'): 'wet',
    ('amenity', 'parking'): 'paved', ('landuse', 'commercial'): 'paved', ('landuse', 'retail'): 'paved', ('landuse', 'industrial'): 'paved',
    ('landuse', 'construction'): 'paved', ('landuse', 'railway'): 'paved', ('amenity', 'school'): 'paved', ('amenity', 'university'): 'paved',
    ('amenity', 'college'): 'paved', ('amenity', 'hospital'): 'paved', ('tourism', 'hotel'): 'paved', ('leisure', 'marina'): 'paved',
    ('leisure', 'resort'): 'paved', ('landuse', 'military'): 'paved', ('highway', 'pedestrian'): 'paved',
    ('landuse', 'residential'): 'yard',
}
ROAD_REACH = {'major': 2.4, 'minor': 1.6, 'track': 1.0}      # how far each side of a road its surface is painted, in land points
BUILDING_MARGIN = 1                                           # points of paving round a building
CALM = 3                                                      # points round a road or building where the ground is left even
NEAR = 5                                                      # points from a road or building that count as lived-in ground
BEACH_REACH = 3                                               # points in from the sea that are beach, where the land is low
BEACH_HIGH = 96.0                                             # ...and no higher than this above the water


def area_kind(tags):
    """What a tagged area of the map is, as a kind here, or None."""
    for key in ('natural', 'leisure', 'landuse', 'amenity', 'tourism', 'highway'):
        k = AREA_KIND.get((key, tags.get(key)))
        if k and (key != 'highway' or tags.get('area') == 'yes'):
            return k
    return None


def default_textures(gd):
    """{kind: LTEX key} for the kinds the game has a texture for."""
    by_name = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX'}
    return {k: by_name[t] for k, _l, t in KINDS if t in by_name}


class MapCover:
    """What each land point of a world is, from the map. xy(pt) turns the map's (lat, lon) into game units (osmplace.Georef.xy)."""

    def __init__(self, grid, data, xy, textures, progress=None, laid=None):
        """laid: the roads as they will be laid, in game units ([{'line', 'class'}], osmplace.layout), when that isn't all the map has."""
        self.grid, self.textures, self.note = grid, textures, None
        A, D = grid.across, grid.down
        self.A, self.D = A, D
        self.gx0, self.gy0 = grid.x0 * PER_CELL, grid.y0 * PER_CELL
        kind = bytearray(A * D)
        to = lambda p: self._to(xy(p))
        said = progress or (lambda *a: None)
        # the map's own areas: the least particular first, so a park inside a neighbourhood stays a park
        said('Reading what the ground is')
        areas = sorted(getattr(data, 'areas', []), key=lambda a: ORDER.index(a['kind']))
        for a in areas:
            self._fill(kind, [to(p) for p in a['ring']], CODE[a['kind']])
        built = bytearray(A * D)
        for b in data.buildings:
            ring = [to(p) for p in b['ring']]
            self._fill(built, ring, 1)
        roads = bytearray(A * D)
        for r in (laid if laid is not None else data.roads):
            reach = ROAD_REACH.get(r['class'], 1.0)
            line = [self._to(p) for p in r['line']] if laid is not None else [to(p) for p in r['pts']]
            for (ax, ay), (bx, by) in zip(line, line[1:]):
                self._stroke(roads, ax, ay, bx, by, reach)
        # ground with nothing said of it that lies near a building or a road is lived-in ground
        said('Finding the lived-in ground')
        near = self._within(built, roads, NEAR)
        yard, paved, asphalt, sand, seabed = CODE['yard'], CODE['paved'], CODE['asphalt'], CODE['sand'], CODE['seabed']
        pts = grid.pts
        for s in range(A * D):
            if not kind[s] and near[s]:
                kind[s] = yard
        grown = self._within(built, bytearray(A * D), BUILDING_MARGIN)
        self.built = self._within(built, bytearray(A * D), BUILDING_MARGIN + 1)      # (where nothing else is to stand)
        self.calm = self._within(built, roads, CALM)                                 # (ground to leave even: a road or a building lies on it)
        for s in range(A * D):
            if grown[s]:
                kind[s] = paved
            if roads[s]:
                kind[s] = asphalt
        # the shore: low land a few points in from the sea, unless something is built there
        said('Finding the beach')
        sea = bytearray(1 if z < 0 else 0 for z in pts)
        shore = self._within(sea, bytearray(A * D), BEACH_REACH)
        for s in range(A * D):
            if sea[s]:
                kind[s] = seabed
            elif shore[s] and pts[s] <= BEACH_HIGH and kind[s] not in (paved, asphalt):
                kind[s] = sand
        self.kind = kind
        self.counts = collections.Counter(kind)

    def _to(self, xy):
        return xy[0] / POINT - self.gx0, xy[1] / POINT - self.gy0

    def _fill(self, grid, ring, value):
        """Every point inside a ring, by rows."""
        A, D = self.A, self.D
        if len(ring) < 3:
            return
        ys = [p[1] for p in ring]
        y0, y1 = max(0, int(math.ceil(min(ys)))), min(D - 1, int(math.floor(max(ys))))
        n = len(ring)
        for y in range(y0, y1 + 1):
            xs = []
            for k in range(n):
                ax, ay = ring[k]
                bx, by = ring[(k + 1) % n]
                if (ay > y) != (by > y):
                    xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                a, b = max(0, int(math.ceil(xs[k]))), min(A - 1, int(math.floor(xs[k + 1])))
                if b >= a:
                    grid[y * A + a:y * A + b + 1] = bytes([value]) * (b - a + 1)

    def _stroke(self, grid, ax, ay, bx, by, reach):
        """Every point within reach of a line from a to b."""
        A, D = self.A, self.D
        x0, x1 = max(0, int(math.floor(min(ax, bx) - reach))), min(A - 1, int(math.ceil(max(ax, bx) + reach)))
        y0, y1 = max(0, int(math.floor(min(ay, by) - reach))), min(D - 1, int(math.ceil(max(ay, by) + reach)))
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        r2 = reach * reach
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2)) if L2 else 0.0
                if (x - ax - dx * t) ** 2 + (y - ay - dy * t) ** 2 <= r2:
                    grid[y * A + x] = 1

    def _within(self, a, b, steps):
        """Every point within so many points (counted along rows and columns) of one set in a or b."""
        A, D = self.A, self.D
        n = A * D
        out = bytearray(n)
        todo = collections.deque()
        dist = array.array('b', bytes(n))
        for s in range(n):
            if a[s] or b[s]:
                out[s] = 1
                todo.append(s)
        while todo:
            s = todo.popleft()
            d = dist[s]
            if d >= steps:
                continue
            x = s % A
            for t in (s - 1 if x else -1, s + 1 if x < A - 1 else -1, s - A, s + A):
                if 0 <= t < n and not out[t]:
                    out[t] = 1
                    dist[t] = d + 1
                    todo.append(t)
        return out

    def mix(self, gx, gy, deg):
        """{texture: share} at a land point, or None to leave it to the slope. The point and the four beside it, so one kind fades into the next."""
        if deg > STEEP:
            return None
        A, D, kind = self.A, self.D, self.kind
        out = {}
        for x, y, w in ((gx, gy, 0.5), (gx - 1, gy, 0.125), (gx + 1, gy, 0.125), (gx, gy - 1, 0.125), (gx, gy + 1, 0.125)):
            if 0 <= x < A and 0 <= y < D:
                k = kind[y * A + x]
                tex = self.textures.get(ORDER[k - 1]) if k else None
                if tex:
                    out[tex] = out.get(tex, 0.0) + w
        return out if out and kind[gy * A + gx] else None

    def summary(self):
        """{kind's name: share of the land points} for the report."""
        n = float(self.A * self.D)
        names = {k: label for k, label, _t in KINDS}
        return {names[ORDER[c - 1]]: round(v / n, 3) for c, v in self.counts.items() if c}
