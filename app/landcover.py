"""Ground types: a land-cover file (a GeoTIFF of class numbers, such as ESA WorldCover or the USGS NLCD) lying over a height file, each class given one of the game's ground textures and a
set of things to scatter there. Which class gets what is a table the person can change; the defaults here are guesses, named by what the game calls its textures.

Textures are painted as the world is made (mapworld.Painter asks mix()), so they go in the plugin, not in the mod's changes. Scatter is laid afterwards as ops: one Undo of its own. Steep ground stays as
the slope says: a class can't paint a cliff with grass."""
import math
import random

import elevation
import roadgen
import scatter

STEEP = 32.0
MAX_CLASSES = 40
SCATTER_LIMIT = 30000

TEX = {'trees': 'LScrubDirtStripGreenNV01Grass', 'shrub': 'ScrubBarrenWastes01Sage', 'grass': 'ScrubBarrenWastes02GrassMix', 'crops': 'LGrassGreenFarmlandsNV', 'built': 'LSuburbanRubble01', 'bare': 'DirtBarrenWastes01',
       'rock': 'LRockWastelandNV', 'snow': 'LSnowSoftSnow', 'water': 'LWaterSandNV01', 'wet': 'LWaterMossNV01Grass', 'moss': 'LScrubDirtCanyon01'}
SCATTER = {'trees': ('trees', 8.0), 'shrub': ('plants', 14.0), 'grass': ('plants', 5.0), 'crops': ('none', 0.0), 'built': ('none', 0.0), 'bare': ('rocks', 2.0),
           'rock': ('rocks', 5.0), 'snow': ('none', 0.0), 'water': ('none', 0.0), 'wet': ('plants', 6.0), 'moss': ('plants', 3.0)}
SCHEMES = {
    'ESA WorldCover': {10: ('Trees', 'trees'), 20: ('Shrubland', 'shrub'), 30: ('Grassland', 'grass'), 40: ('Cropland', 'crops'), 50: ('Built up', 'built'), 60: ('Bare ground', 'bare'),
                       70: ('Snow and ice', 'snow'), 80: ('Open water', 'water'), 90: ('Wetland', 'wet'), 95: ('Mangroves', 'wet'), 100: ('Moss and lichen', 'moss')},
    'USGS NLCD': {11: ('Open water', 'water'), 12: ('Ice and snow', 'snow'), 21: ('Developed, open', 'grass'), 22: ('Developed, low', 'built'), 23: ('Developed, medium', 'built'), 24: ('Developed, high', 'built'),
                  31: ('Barren', 'bare'), 41: ('Deciduous forest', 'trees'), 42: ('Evergreen forest', 'trees'), 43: ('Mixed forest', 'trees'), 51: ('Dwarf scrub', 'shrub'), 52: ('Shrub', 'shrub'), 71: ('Grassland', 'grass'),
                  72: ('Sedge', 'grass'), 73: ('Lichens', 'moss'), 74: ('Moss', 'moss'), 81: ('Pasture', 'grass'), 82: ('Crops', 'crops'), 90: ('Woody wetland', 'wet'), 95: ('Herbaceous wetland', 'wet')},
}
SCATTER_SETS = [('none', 'Nothing')] + scatter.SETS


def classes_in(raster):
    """{class number: how many points} in the file, from a sample of it. Refuses a file that isn't classes."""
    stride = max(1, (raster.w * raster.h) // 2000000)
    counts = {}
    for x in raster.v[::stride]:
        if x != x:
            continue
        k = int(round(x * 255)) if raster.plain else int(round(x))
        counts[k] = counts.get(k, 0) + 1
    if len(counts) > MAX_CLASSES:
        raise elevation.MapFileError('This file has %d different numbers in it, so it\'s not a land-cover file of classes (is it heights?).' % len(counts))
    if not counts:
        raise elevation.MapFileError('This file has no data in it.')
    return counts


def detect(counts):
    """Which known scheme these numbers belong to, or None."""
    vals = set(counts)
    best, score = None, 0.0
    for name, table in SCHEMES.items():
        hit = len(vals & set(table)) / len(vals)
        if hit > score:
            best, score = name, hit
    return best if score >= 0.8 else None


def default_table(gd, counts, scheme=None):
    """Rows for the panel, the commonest class first: {'value', 'label', 'share', 'tex' (LTEX key, '' to leave it to the slope), 'scatter', 'density' (a cell)}."""
    known = SCHEMES.get(scheme, {})
    by_name = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX'}
    total = sum(counts.values()) or 1
    rows = []
    for v, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        label, kind = known.get(v, ('Class %d' % v, None))
        sc, dens = SCATTER.get(kind, ('none', 0.0))
        rows.append({'value': v, 'label': label, 'share': round(n / total, 3), 'tex': by_name.get(TEX.get(kind), '') if kind else '', 'scatter': sc, 'density': dens})
    return rows


class Cover:
    """A class at any spot of a world, by way of the height file's pixels. dem: the height Raster's geo, w, h. to_dem(x, y) -> (col, row) in the height file."""

    def __init__(self, raster, rows, dem_geo, dem_w, dem_h, to_dem, cell0=None):
        self.raster, self.to_dem = raster, to_dem
        self.table = {int(r['value']): r for r in rows}
        self.w, self.h, self.v = raster.w, raster.h, raster.v
        self.mul = 255 if raster.plain else 1
        self.note = None
        C = raster.geo
        if dem_geo and C:
            same = dem_geo['kind'] == C['kind'] and (C['kind'] == 'deg' or dem_geo.get('epsg') == C.get('epsg'))
            if not same:
                raise elevation.MapFileError('This file and the height file are in different map projections (%s and %s), so one can\'t be laid on the other. Turn it into the height file\'s first, e.g. gdalwarp -t_srs EPSG:%s in.tif out.tif.' % (
                    C.get('epsg') or C['kind'], dem_geo.get('epsg') or dem_geo['kind'], dem_geo.get('epsg') or 4326))
            sx, sy = dem_geo['dx'] / C['dx'], dem_geo['dy'] / C['dy']
            ox, oy = (dem_geo['x0'] - C['x0']) / C['dx'], (C['y0'] - dem_geo['y0']) / C['dy']
        else:
            sx, sy = (self.w - 1) / max(1, dem_w - 1), (self.h - 1) / max(1, dem_h - 1)
            ox, oy = 0.0, 0.0
            self.note = 'One of the files doesn\'t say where it is on Earth, so the land-cover file was stretched over the whole height file.'
        self.sx, self.sy, self.ox, self.oy = sx, sy, ox, oy
        self.cell0 = cell0 or (0, 0)

    def class_at(self, x, y):
        """The class number at a spot in game units, or None off the file."""
        col, row = self.to_dem(x, y)
        c, r = int(round(col * self.sx + self.ox)), int(round(row * self.sy + self.oy))
        if not (0 <= c < self.w and 0 <= r < self.h):
            return None
        v = self.v[r * self.w + c]
        return None if v != v else int(round(v * self.mul))

    def mix(self, gx, gy, deg):
        """{texture: share} at a land point of the world, or None to leave it to the slope. Four spots round the point, so edges between classes aren't saw teeth."""
        if deg > STEEP:
            return None
        x, y = (self.cell0[0] * 32 + gx) * 128.0, (self.cell0[1] * 32 + gy) * 128.0
        out = {}
        n = 0
        for dx, dy in ((-48, -48), (48, -48), (-48, 48), (48, 48)):
            r = self.table.get(self.class_at(x + dx, y + dy))
            if r and r.get('tex'):
                out[r['tex']] = out.get(r['tex'], 0.0) + 0.25
                n += 1
        return out if n else None


def scatter_ops(gd, pr, world, cover, learn_world, learn_at, seed=1, limit=SCATTER_LIMIT, progress=None):
    """(ops placing what each class's row asks for in each cell, a report). Things are what the game itself placed in the world to take after, kept to ones that stand on the ground."""
    found = scatter.learn(gd, learn_world, learn_at[0], learn_at[1], reach=6, top=12)
    bags = {}
    for name, items in found.items():
        items = [i for i in items if abs(i['dz']) < 64]
        if items:
            bags[name] = items
    grid = gd.grid(world)
    g = roadgen.Ground(gd, pr, world)
    rng = random.Random(seed)
    keys = sorted(grid)
    # how many it comes to (from a sample of the cells), to thin it evenly if it's too many
    rows = [r for r in cover.table.values() if r.get('scatter') in bags and float(r.get('density') or 0) > 0]
    if not rows:
        return [], {'things': 0, 'thinned': 1.0}
    top = max(float(r['density']) for r in rows)
    sample = keys[:: max(1, len(keys) // 200)]
    want = sum(_estimate(cover, k) for k in sample) * len(keys) / len(sample)
    thin = min(1.0, limit / want) if want else 1.0
    ops = []
    for n, k in enumerate(keys):
        if progress and n % 32 == 0:
            progress('Scattering', n, len(keys))
        tries = top * thin
        count = int(tries) + (rng.random() < tries - int(tries))
        for _ in range(count):
            x, y = (k[0] + rng.random()) * 4096, (k[1] + rng.random()) * 4096
            r = cover.table.get(cover.class_at(x, y))
            if not r or r.get('scatter') not in bags:
                continue
            if rng.random() > float(r.get('density') or 0) / top:
                continue
            z = g.at(x, y)
            if z is None:
                continue
            w = g.water(x, y)
            if w is not None and z < w:
                continue
            item = _pick(bags[r['scatter']], rng)
            s = rng.uniform(item['smin'], item['smax'])
            ops.append({'op': 'add', 'cell': gd.key(grid[k]), 'base': item['key'], 'p': [round(x, 1), round(y, 1), round(z + item['dz'] * s, 1), 0.0, 0.0, round(rng.uniform(0, math.tau), 3)], 's': round(s, 3)})
            if len(ops) >= limit:
                break
        if len(ops) >= limit:
            break
    return ops, {'things': len(ops), 'thinned': round(thin, 3)}


def _pick(items, rng):
    t = rng.random() * sum(i['n'] for i in items)
    for i in items:
        t -= i['n']
        if t <= 0:
            return i
    return items[-1]


def _estimate(cover, k):
    """About how many things this cell gets, from a few spots."""
    tot = 0.0
    for a in (0.25, 0.75):
        for b in (0.25, 0.75):
            r = cover.table.get(cover.class_at((k[0] + a) * 4096, (k[1] + b) * 4096))
            if r and r.get('scatter') != 'none':
                tot += float(r.get('density') or 0) / 4
    return tot
