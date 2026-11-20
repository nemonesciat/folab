"""What a world made from a real map shows past its own edge: the land and sea round it, as distant land only.

A world from a height map stops where its rectangle stops, and so did its distant land (lodgen draws only the world's own
cells): past the edge the sea ended in a ragged line and the hills the player could see from the beach were cut off. The
height file goes on, though, and the scale the world was made at is kept beside it (made.json), so the same file read at
the same scale gives the ground for a margin of cells all round. Those are given to lodgen as distant land only: chunks
and their pictures, and the settings file's box made big enough to hold them. No cell, no LAND record, nothing anyone can
walk on is added; the game draws its far water over whatever of it lies under the sea.

`beyond(gd, pr, world)` returns what lodgen needs, or None for a world not made from a map."""
import math

HIGH_GROUND = 30.0          # (metres: the height file this far up is land, whatever a coastline carried past its end says)
JOIN_ABOVE = 3.0            # (metres: land joins the island only over this; the reef flats join the shore through 1-3 m)
SHORE_REACH = 3             # (pixels of land under that kept beside joined land: the beach)
PBF_PAD = 0.05              # (degrees past the margin a region file's coastline is read for, so no way ends inside it)
MARGIN = 32               # cells all round (32 takes Waikiki's in to the Ko'olau ridge and well out to sea)
SEA = (150, 140, 112)       # the sea bed's colour (under the water)


class Beyond:
    """Heights and colours past a map-made world's edge, at the scale the world was made at."""

    def __init__(self, raster, plan, margin=MARGIN):
        self.r, self.plan, self.margin = raster, plan, margin
        self.floor = plan.floor if plan.floor is not None else -1536.0
        self.joined = None                      # (set by `join_land`: which land pixels belong to the main island)

    def join_land(self, rect):
        """Mark the land joined to the highest point of the rectangle (in pixels); anything else above water is reef
        or a bad reading in the height file (Waikiki's had two shallow reefs at 20 m standing out to sea as islands)."""
        r = self.r
        c0, r0 = max(0, int(math.floor(rect[0]))), max(0, int(math.floor(rect[1])))
        c1, r1 = min(r.w, int(math.ceil(rect[2])) + 1), min(r.h, int(math.ceil(rect[3])) + 1)
        w, h = c1 - c0, r1 - r0
        if w <= 0 or h <= 0:
            return
        land = bytearray(w * h)             # (2: above JOIN_ABOVE, so it joins; 1: just above the sea)
        top, at = -1.0, None
        for j in range(h):
            base = (r0 + j) * r.w + c0
            for i in range(w):
                v = r.v[base + i]
                if v == v and v > 0.0:
                    land[j * w + i] = 2 if v > JOIN_ABOVE else 1
                    if v > top:
                        top, at = v, j * w + i
        if at is None:
            return
        joined = bytearray(w * h)
        joined[at] = 1
        todo = [at]
        while todo:
            k = todo.pop()
            i, j = k % w, k // w
            for n in ((k - 1) if i else -1, (k + 1) if i < w - 1 else -1, (k - w) if j else -1, (k + w) if j < h - 1 else -1):
                if n >= 0 and land[n] == 2 and not joined[n]:
                    joined[n] = 1
                    todo.append(n)
        # the low fringe stays where it touches joined land (the beach), a few pixels out
        for _ in range(SHORE_REACH):
            grow = [k for k in range(w * h) if land[k] == 1 and not joined[k] and (
                (k % w and joined[k - 1]) or (k % w < w - 1 and joined[k + 1]) or
                (k >= w and joined[k - w]) or (k < w * (h - 1) and joined[k + w]))]
            for k in grow:
                joined[k] = 1
        self.joined = (c0, r0, w, h, joined)

    def _island(self, x, y):
        """False where the height file has land not joined to the main island (it's sunk)."""
        if not self.joined:
            return True
        c0, r0, w, h, joined = self.joined
        col, row = self.plan.pixel_of(x, y)
        i, j = int(round(col)) - c0, int(round(row)) - r0
        if not (0 <= i < w and 0 <= j < h):
            return True
        return bool(joined[j * w + i])

    def _value(self, x, y):
        col, row = self.plan.pixel_of(x, y)
        r = self.r
        if not (0 <= col < r.w - 1 and 0 <= row < r.h - 1):
            return None
        c, w = int(col), int(row)
        fx, fy = col - c, row - w
        a, b, cc, d = r.at(c, w), r.at(c + 1, w), r.at(c, w + 1), r.at(c + 1, w + 1)
        if any(v != v for v in (a, b, cc, d)):
            return None
        return (a * (1 - fx) + b * fx) * (1 - fy) + (cc * (1 - fx) + d * fx) * fy

    def height(self, x, y):
        v = self._value(x, y)
        if v is None or v <= 0.0 or not self._island(x, y):
            return self.floor               # (the sea, or past the file: deep enough that the water covers it)
        return min(32000.0, max(self.floor, self.plan.z_of_value(v)))

    def colour(self, x, y):
        z = self.height(x, y)
        if z <= 0:
            return SEA
        # (green on the slopes and in the valleys, paler and browner high up, as the island's own ridges are)
        near = 256.0
        dx = (self.height(x + near, y) - self.height(x - near, y)) / (2 * near)
        dy = (self.height(x, y + near) - self.height(x, y - near)) / (2 * near)
        steep = min(1.0, math.hypot(dx, dy) / 1.2)
        high = min(1.0, max(0.0, z / 30000.0))
        g = (64, 96, 46)
        rock = (112, 104, 86)
        t = 0.55 * steep + 0.35 * high
        return tuple(int(g[k] * (1 - t) + rock[k] * t) for k in range(3))


class FromGrid(Beyond):
    """The same, from a whole height grid made for the world's rectangle and its margin together, by the steps that made
    the world: the height file read at the world's scale, and the sea shaped by the map file's coastline. The height file
    alone had a patch of reef at 20 m off Kahala that stood out to sea as an island."""

    def __init__(self, raster, plan, grid, margin=MARGIN, box=None):
        Beyond.__init__(self, raster, plan, margin)
        self.grid = grid
        self.box = box                          # (lat/lon the map file covers: its coastline is good only inside it)

    def inside(self, x, y):
        if not self.box:
            return True
        col, row = self.plan.pixel_of(x, y)
        g = self.r.geo
        lon, lat = g['x0'] + col * g['dx'], g['y0'] - row * g['dy']
        s, w, n, e = self.box
        return s <= lat <= n and w <= lon <= e

    def height(self, x, y):
        if not self.inside(x, y):
            return Beyond.height(self, x, y)   # (past the map file, its coastline was carried on in straight lines: the height file says)
        G = self.grid
        fx, fy = x / 128.0 - G.x0 * 32, y / 128.0 - G.y0 * 32
        i, j = int(fx), int(fy)
        if not (0 <= i < G.across - 1 and 0 <= j < G.down - 1):
            return self.floor
        tx, ty = fx - i, fy - j
        a, p = G.across, G.pts
        z = (p[j * a + i] * (1 - tx) + p[j * a + i + 1] * tx) * (1 - ty) + (p[(j + 1) * a + i] * (1 - tx) + p[(j + 1) * a + i + 1] * tx) * ty
        if z <= 0:
            v = self._value(x, y)
            if v is not None and v > HIGH_GROUND:
                return Beyond.height(self, x, y)
        return min(32000.0, max(self.floor, z))


WHY = ''                    # (why the last beyond() gave None: the far view's report says it, never silently)


def beyond(gd, pr, world, margin=MARGIN, coast_file=None):
    """A Beyond for this world, or None if it wasn't made from a height file (or the file is gone)."""
    import api_maps
    import elevation
    import mapscale
    global WHY
    side = (api_maps.read_sidecar(pr) or {}).get(gd.edid(world))
    if not side or not side.get('file') or not side.get('opts'):
        WHY = 'the world was not made from a height file'
        return None
    try:
        raster = elevation.read_file(api_maps.file_path(side['file']))
    except (OSError, ValueError) as e:
        WHY = 'its height file %s could not be read: %s' % (side['file'], e)
        return None
    if side.get('grown_from'):
        # (a grown world's opts are still its first box's: planned from them it never matched and the far view had no land
        # past the edge, 18 Nov 2026; the sidecar's own numbers are the world's, mapgrow.plan_of)
        return _beyond_grown(gd, pr, world, side, raster, margin, coast_file)
    plan = mapscale.Plan(raster, side['opts'])
    if (plan.W, plan.H, plan.x0, plan.y0) != (side.get('W'), side.get('H'), side.get('x0'), side.get('y0')):
        WHY = ('its height file or scale is no longer the one the world was made from (now %s, made %s)'
               % ((plan.W, plan.H, plan.x0, plan.y0), (side.get('W'), side.get('H'), side.get('x0'), side.get('y0'))))
        return None
    # the world's rectangle grown by the margin, centred the same, so its cells fall where the world's do
    pcx, pcy = mapscale.CELL / plan.upx, mapscale.CELL / plan.upy
    c0, r0, c1, r1 = side['opts']['rect']
    opts = dict(side['opts'], rect=[c0 - margin * pcx, r0 - margin * pcy, c1 + margin * pcx, r1 + margin * pcy], base=side.get('base', plan.base))
    big = mapscale.Plan(raster, opts)
    if (big.x0, big.y0, big.W, big.H) != (plan.x0 - margin, plan.y0 - margin, plan.W + 2 * margin, plan.H + 2 * margin):
        return Beyond(raster, plan, margin)
    grid = mapscale.heights(big)
    box = None
    if side.get('coast') or coast_file:
        try:
            import coast
            import osm
            import osmplace
            if coast_file and coast_file.lower().endswith('.pbf'):
                # a whole region's file: its coastline is good everywhere, so it shapes the margin all round
                import osmpbf
                g = raster.geo
                rc0, rr0, rc1, rr1 = opts['rect']
                lon_a, lon_b = g['x0'] + rc0 * g['dx'], g['x0'] + rc1 * g['dx']
                lat_a, lat_b = g['y0'] - rr1 * g['dy'], g['y0'] - rr0 * g['dy']
                pad = PBF_PAD
                data = osmpbf.coast(coast_file, (lat_a - pad, lon_a - pad, lat_b + pad, lon_b + pad))
            else:
                data = osm.read(coast_file or api_maps.file_path(side['coast']))
            box = data.bounds
            bigside = dict(side, W=big.W, H=big.H, x0=big.x0, y0=big.y0, col0=big.col0, row0=big.row0)
            geo = osmplace.Georef(bigside, data)
            sea = coast.shape_sea(grid, [[geo.xy(p) for p in line] for line in data.coast], big.floor)
            if sea and not sea.get('leak'):
                mapscale.limit_slopes(grid.pts, grid.across, grid.down)
        except (OSError, ValueError):
            pass
    out = FromGrid(raster, big, grid, margin, box)
    out.join_land(opts['rect'])
    return out


def _beyond_grown(gd, pr, world, side, raster, margin, coast_file):
    """beyond() for a world grown in place (mapgrow): its plan and the margin's from the sidecar's numbers."""
    import api_maps
    import mapgrow
    import mapscale
    global WHY
    try:
        plan = mapgrow.plan_of(raster, side)
    except ValueError as e:
        WHY = str(e)
        return None
    pcx, pcy = mapscale.CELL / plan.upx, mapscale.CELL / plan.upy
    bigside = dict(side, W=side['W'] + 2 * margin, H=side['H'] + 2 * margin, x0=side['x0'] - margin, y0=side['y0'] - margin,
                   col0=side['col0'] - margin * pcx, row0=side['row0'] - margin * pcy)
    big = mapgrow.plan_of(raster, bigside)
    grid = mapscale.heights(big)
    rect = [side['col0'], side['row0'], side['col0'] + side['W'] * pcx, side['row0'] + side['H'] * pcy]
    box = None
    if side.get('coast') or coast_file:
        try:
            import coast
            import osm
            import osmplace
            data = osm.read(coast_file or api_maps.file_path(side['coast']))
            box = data.bounds
            geo = osmplace.Georef(bigside, data)
            sea = coast.shape_sea(grid, [[geo.xy(p) for p in line] for line in data.coast], big.floor)
            if sea and not sea.get('leak'):
                mapscale.limit_slopes(grid.pts, grid.across, grid.down)
        except (OSError, ValueError):
            pass
    out = FromGrid(raster, big, grid, margin, box)
    out.join_land(rect)
    return out
