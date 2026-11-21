"""Green far off (farfoliage.py): the distant ground's picture painted with what grows on it, so hills seen from afar
are wooded, not bare earth (the user, 20 Nov 2026: "the distant hills look so barren and uninteresting").

The game draws no plants past the loaded cells (its own trees come by another way; FOLab's grass and placed plants stop
at the edge of what's loaded), and lodgen paints the far ground from the land's textures alone, so a jungle-covered
mountain reads as rubble from a few cells away. Here, for every 256-unit square of a world (lodgen's colours are 16 a
cell): how much of it grows the game's grass (grassrule) and how many plants stand on it (FOLab's own and the game's,
trees counting most) make a cover from 0 to 1, and the far picture there is mixed toward a canopy green by it, mottled
light and dark pixel by pixel (sun on crowns, shade between them), so it reads as foliage rather than paint.

`Cover(gd, pr, world)` holds the cover; `cover.colour(ground, x, y)` gives the picture's colour at a point; lodgen's
Sampler takes it as `foliage`. Costs nothing in the game: it is only the distant ground's own texture."""
import math
import re
import zlib

CANOPY = (44, 74, 32)          # a jungle's crowns from afar (darker since 21 Nov 2026: the far trees stand on it)
SUNLIT = (92, 124, 58)
SHADE = (24, 42, 21)
MOST = 0.88                    # the most the ground's own colour gives way (a little of it always shows)
TREE = re.compile(r'tree|palm|banyan|bamboo|treefern|cypress|birch|oak|pine', re.I)
PLANT = re.compile(r'fern|shrub|bush|taro|heliconia|hibiscus|banana|ti(red|green)|plant|grass|thicket|undergrowth|floor|slope|vine|agave|yucca|sage', re.I)


class Cover:
    def __init__(self, gd, pr, world, green=None):
        """green: land points (x, y in 128-unit steps) where the game's grass grows; worked out here when not given."""
        import land
        import grassrule
        import recordio
        self.grid = gd.grid(world)
        if green is None:
            dens = grassrule.densities(gd, pr)
            cache, green = {}, set()
            for xy, c in self.grid.items():
                form = pr.land.get(gd.key(c))
                if not form:
                    e = gd.land_at(world, *xy)
                    form = land.decode(gd, e, cache) if e else None
                for q, quarter in enumerate((form or {}).get('q') or ()):
                    d = grassrule.predict(quarter, dens)
                    for j in range(17):
                        for i in range(17):
                            if d[j * 17 + i] > 0:
                                green.add((xy[0] * 32 + (q % 2) * 16 + i, xy[1] * 32 + (q // 2) * 16 + j))
        self.grass = {}
        for gx, gy in green:
            k = (gx // 2, gy // 2)                       # (a 256-unit square holds 2 x 2 land points)
            self.grass[k] = self.grass.get(k, 0) + 1
        names, kind = {}, {}

        def kind_of(b):
            if b not in kind:
                try:
                    e = recordio.field(pr.records[b], 'EDID') if b.startswith('+') and b in pr.records else gd.edid(gd.from_key(b))
                except Exception:
                    e = ''
                e = e or ''
                kind[b] = 3.0 if TREE.search(e) else 0.6 if PLANT.search(e) else 0.0
            return kind[b]
        self.plants = {}
        for xy, c in self.grid.items():
            ck = gd.key(c)
            mine = pr.cells.get(ck, {}).get('refs', {})
            for r in (gd.refs(c) or ()):
                k = gd.key(r['ref'])
                if k in mine or r.get('base') is None:
                    continue
                v = kind_of(gd.key(r['base']))
                if v:
                    p = r['pos']
                    s = (int(p[0] // 256), int(p[1] // 256))
                    self.plants[s] = self.plants.get(s, 0.0) + v
            for r in mine.values():
                if r.get('removed') or not r.get('base') or not r.get('p'):
                    continue
                v = kind_of(r['base'])
                if v:
                    p = r['p']
                    s = (int(p[0] // 256), int(p[1] // 256))
                    self.plants[s] = self.plants.get(s, 0.0) + v * float(r.get('s') or 1.0)

    def amount(self, x, y):
        """How covered the ground is round (x, y), 0 to 1: its square and the eight round it, the middle counting most."""
        sx, sy = int(x // 256), int(y // 256)
        tot = 0.0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                w = 2.0 if dx == dy == 0 else 1.0
                g = self.grass.get((sx + dx, sy + dy), 0) / 4.0
                p = min(1.0, self.plants.get((sx + dx, sy + dy), 0.0) / 4.0)
                tot += w * min(1.0, 0.7 * g + 0.8 * p)
        return tot / 10.0

    def colour(self, ground, x, y):
        a = self.amount(x, y)
        if a <= 0.02:
            return ground
        # (mottled by the pixel: a crown in sun, one in shade, the dark between them)
        h = zlib.crc32(b'%d,%d' % (int(x // 64), int(y // 64))) & 0xFFFF
        big = zlib.crc32(b'%d;%d' % (int(x // 512), int(y // 512))) & 0xFF
        t = h / 65535.0
        # (rough: clumps a few hundred units across, each its own darker or lighter, so far slopes read as many crowns)
        clump = (zlib.crc32(b'%d:%d' % (int(x // 192), int(y // 192))) & 0xFF) / 255.0
        if t < 0.28:
            leaf = SHADE
        elif t > 0.82:
            leaf = SUNLIT
        else:
            f = 0.82 + 0.3 * t + 0.12 * (big / 255.0 - 0.5)
            leaf = tuple(min(255, int(v * f)) for v in CANOPY)
        leaf = tuple(min(255, int(v * (0.78 + 0.4 * clump))) for v in leaf)
        k = MOST * min(1.0, a * 1.4)
        return tuple(int(g * (1 - k) + l * k) for g, l in zip(ground, leaf))
