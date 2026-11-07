"""OpenStreetMap laid on a world made from a height file: roads through roadgen.py along their real lines, rivers and lakes through landshape.py's water, buildings as flat pads and a marker layer for later.
No towns or buildings are put up. All of it comes back as ops, so it's one Undo.

The file's lat/lon goes through the height file's place on Earth to game units (the sidecar api_maps.py keeps). Lines are cut at the world's edge and thinned (a land point is 128 units: finer than that
is noise here). Water goes first, then pads, then roads, each on what the one before left. Every height stays on a whole 8-unit step, worked out by spot, so cells still meet."""
import math
import random

import elevation
import land
import landshape
import roadgen

CELL = 4096
THIN = 96.0
MIN_ROAD = 400.0              # shorter than this, a road isn't worth a piece
MIN_LAKE = 300.0              # across, in units: smaller is left to the layer
PAD_FADE = 256.0              # the ground takes this far to come back from a pad
PAD_MIN_POINTS = 1            # a pad wants at least this many land points inside its outline
PIECES_WARN = 6000
PIECES_STOP = 40000
RIVER_WIDTH_M = {'river': 30.0, 'canal': 15.0, 'stream': 4.0, 'ditch': 2.0, 'drain': 2.0}
RIVER_MIN = {'river': 320.0, 'stream': 160.0}


class Georef:
    """lat/lon to game units, by way of the height file's pixels. No place of its own (a plain picture): the OSM file's bounds are taken as the whole picture."""

    def __init__(self, side, data=None):
        self.side = side
        g = side.get('geo')
        self.note = None
        if g:
            self.to_pixel = lambda lat, lon: elevation.pixel_of(g, lat, lon)
            if g['kind'] == 'proj' and elevation.project(g.get('epsg'), 40.0, -100.0, g['unit']) is None:
                raise elevation.MapFileError('The height file is in a map projection FOLab doesn\'t know (EPSG %s), so OpenStreetMap can\'t be lined up with it. A file in degrees, UTM or web mercator can.' % g.get('epsg'))
        else:
            b = data.bounds if data else None
            if not b or b[2] <= b[0] or b[3] <= b[1]:
                raise elevation.MapFileError('The height file doesn\'t say where on Earth it is, and this OSM file has no bounds to go by.')
            w, h = side.get('px_w', 1), side.get('px_h', 1)
            self.to_pixel = lambda lat, lon: ((lon - b[1]) / (b[3] - b[1]) * (w - 1), (b[2] - lat) / (b[2] - b[0]) * (h - 1))
            self.note = 'The height file doesn\'t say where on Earth it is, so the OSM file\'s bounds were taken as the whole of it.'

    def xy(self, pt):
        col, row = self.to_pixel(pt[0], pt[1])
        s = self.side
        return (s['x0'] * CELL + (col - s['col0']) * s['upx'], (s['y0'] + s['H']) * CELL - (row - s['row0']) * s['upy'])


def world_box(side):
    return (side['x0'] * CELL, side['y0'] * CELL, (side['x0'] + side['W']) * CELL, (side['y0'] + side['H']) * CELL)


def _clip_segment(a, b, box):
    """The part of a line segment inside a box, or None (Liang-Barsky)."""
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - box[0]), (dx, box[2] - a[0]), (-dy, a[1] - box[1]), (dy, box[3] - a[1])):
        if p == 0:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return None
                t0 = max(t0, r)
            else:
                if r < t0:
                    return None
                t1 = min(t1, r)
    return (a[0] + t0 * dx, a[1] + t0 * dy), (a[0] + t1 * dx, a[1] + t1 * dy)


def clip_line(pts, box):
    """The stretches of a line inside a box: [(points, whether it starts at its own first point, whether it ends at its own last)]."""
    out, cur, began = [], None, False
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        seg = _clip_segment(a, b, box)
        if seg is None:
            if cur:
                out.append((cur, began, False))
                cur = None
            continue
        if cur is None:
            cur = [seg[0]]
            began = k == 0 and seg[0] == a
        cur.append(seg[1])
        if seg[1] != b:
            out.append((cur, began, False))
            cur = None
    if cur:
        out.append((cur, began, cur[-1] == pts[-1]))
    return out


def thin(pts, tol=THIN):
    """Douglas-Peucker: only the points that change the line by more than tol."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        best, at = tol, None
        for k in range(i + 1, j):
            d = landshape._seg_dist(pts[k][0], pts[k][1], pts[i][0], pts[i][1], pts[j][0], pts[j][1])
            if d > best:
                best, at = d, k
        if at is not None:
            keep[at] = True
            stack += [(i, at), (at, j)]
    return [p for p, k in zip(pts, keep) if k]


def length(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def ring_area(r):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:] + r[:1]))) / 2


def _in_box(ring, box):
    return any(box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3] for p in ring)


def layout(data, side):
    """Everything in the file, in game units and cut to the world: what the map shows and what laying it works from."""
    geo = Georef(side, data)
    box = world_box(side)
    out = {'roads': [], 'bridges': [], 'rivers': [], 'lakes': [], 'buildings': [], 'places': [], 'note': geo.note}
    ends = data.road_ends
    for src, key in ((data.roads, 'roads'), (data.bridges, 'bridges')):
        for w in src:
            full = [geo.xy(p) for p in w['pts']]
            # (a road's ends: another road ends here too, or passes through, so it's no dead end)
            for part, a, b in clip_line(full, box):
                part = thin(part)
                if length(part) < MIN_ROAD:
                    continue
                joined_a = not a or ends.get(w['ends'][0], 0) > 1 or data.passing.get(w['ends'][0], 0) > 1
                joined_b = not b or ends.get(w['ends'][1], 0) > 1 or data.passing.get(w['ends'][1], 0) > 1
                out[key].append({'line': part, 'class': w['class'], 'name': w['name'], 'kind': w['kind'], 'caps': (not joined_a, not joined_b)})
    for w in data.rivers:
        for part, _a, _b in clip_line([geo.xy(p) for p in w['pts']], box):
            part = thin(part, 128.0)
            if length(part) >= 512:
                out['rivers'].append({'line': part, 'class': w['class'], 'name': w['name'], 'kind': w['kind'], 'width_m': w['width_m']})
    for w in data.lakes:
        ring = [geo.xy(p) for p in w['ring']]
        if _in_box(ring, box):
            out['lakes'].append({'ring': thin(ring + ring[:1], 128.0)[:-1], 'name': w['name']})
    for w in data.buildings:
        ring = [geo.xy(p) for p in w['ring']]
        if _in_box(ring, box):
            out['buildings'].append({'ring': ring, 'name': w['name'], 'kind': w['kind']})
    for w in data.places:
        x, y = geo.xy(w['pt'])
        if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            out['places'].append({'p': [x, y], 'name': w['name'], 'kind': w['kind']})
    return out


def _round(line):
    return [[round(p[0], 1), round(p[1], 1)] for p in line]


def summary(lay):
    """What the file has in this world, for the panel, and thinned lines for the map."""
    road_len = {}
    for r in lay['roads']:
        road_len[r['class']] = road_len.get(r['class'], 0.0) + length(r['line'])
    return {'roads': {k: {'n': sum(1 for r in lay['roads'] if r['class'] == k), 'pieces': int(v / (roadgen.PIECE - roadgen.OVERLAP))} for k, v in road_len.items()},
            'rivers': {k: sum(1 for r in lay['rivers'] if r['class'] == k) for k in ('river', 'stream')},
            'lakes': len(lay['lakes']), 'buildings': len(lay['buildings']), 'places': len(lay['places']), 'bridges': len(lay['bridges']), 'note': lay['note'],
            'draw': {'roads': [{'c': r['class'], 'l': _round(r['line'])} for r in lay['roads']], 'bridges': [_round(r['line']) for r in lay['bridges']],
                     'rivers': [{'c': r['class'], 'l': _round(r['line'])} for r in lay['rivers']], 'lakes': [_round(r['ring']) for r in lay['lakes']],
                     'buildings': [_round(r['ring']) for r in lay['buildings'][:20000]],
                     'places': [{'p': _round([r['p']])[0], 'n': r['name'], 'k': r['kind']} for r in lay['places']]}}


class _Over:
    """The mod as it would be with what's been worked out so far: what roadgen and landshape look at."""

    def __init__(self, pr):
        self.land = dict(pr.land)
        self.water = dict(pr.water)


class Work:
    def __init__(self, gd, pr, world):
        self.gd, self.world = gd, world
        self.over = _Over(pr)
        self.grid = gd.grid(world)
        self.pr = pr
        self.changed = set()
        self.tex = {}

    def has(self, k):
        c = self.grid.get(k)
        return c is not None and (c in self.gd.land or self.gd.key(c) in self.over.land)

    def heights(self, cx, cy):
        c = self.grid.get((cx, cy))
        if c is None:
            return None
        ck = self.gd.key(c)
        if ck in self.over.land:
            return self.over.land[ck]['h']
        e = self.gd.land.get(c)
        if not e:
            return None
        return land.heights_of(dict(land.tes4.iter_subrecords(self.gd.plugins[e[0]].data(e[1])))['VHGT'])

    def form(self, k):
        """This cell's land to change: its own copy once."""
        ck = self.gd.key(self.grid[k])
        if ck not in self.changed:
            f = self.over.land.get(ck)
            f = dict(f) if f else land.decode(self.gd, self.gd.land[self.grid[k]], self.tex)
            f = {n: f[n] for n in ('h', 'c', 'q')}
            f['h'] = list(f['h'])
            self.over.land[ck] = f
            self.changed.add(ck)
        return self.over.land[ck]

    def set_heights(self, k, h):
        self.form(k)['h'] = h

    def put_point(self, gx, gy, z):
        """One land point, in every cell that has it."""
        cx, cy = gx // 32, gy // 32
        c, r = gx - cx * 32, gy - cy * 32
        at = [(cx, cy, r, c)]
        if c == 0:
            at.append((cx - 1, cy, r, 32))
        if r == 0:
            at.append((cx, cy - 1, 32, c))
        if c == 0 and r == 0:
            at.append((cx - 1, cy - 1, 32, 32))
        for x, y, rr, cc in at:
            if self.has((x, y)):
                self.form((x, y))['h'][rr * 33 + cc] = z


def _step(v):
    return round(v / 8.0) * 8.0


def lay_water(w, lay, want, compress, progress):
    """Rivers and lakes, each through landshape on the cells it reaches. Returns ({cell: level}, how many of each)."""
    water, n_r, n_l = {}, 0, 0
    shapes = []
    if want.get('lakes'):
        for l in lay['lakes']:
            r = l['ring']
            if ring_area(r) < MIN_LAKE * MIN_LAKE:
                continue
            shapes.append({'kind': 'lake', 'pts': [list(p) for p in r], 'depth': 400.0, 'bank': 256.0, 'below': 16.0})
    for rv in lay['rivers']:
        if not want.get('rivers' if rv['class'] == 'river' else 'streams'):
            continue
        real = rv.get('width_m') or RIVER_WIDTH_M.get(rv['kind'], 10.0)
        half = max(RIVER_MIN[rv['class']], min(2400.0, real * 70.0 / compress / 2 * 2))
        shapes.append({'kind': 'river', 'pts': [list(p) for p in rv['line']], 'width': half, 'depth': max(96.0, min(320.0, half * 0.6))})
    for i, s in enumerate(shapes):
        if progress:
            progress('Cutting rivers and lakes', i, len(shapes))
        marked = {k for k in landshape.cells_reached(s) if w.has(k)}
        if not marked:
            continue
        new, wet = landshape.shape_all({'shapes': [s], 'rough': 0.0, 'fade': 128.0, 'hold': False}, w.heights, marked)
        for k, h in new.items():
            old = w.heights(*k)
            h = [_step(v) for v in h]
            if h != old:
                w.set_heights(k, h)
        for k, v in wet.items():
            if s['kind'] == 'lake':
                water[k] = max(water.get(k, -1e9), v)
            else:
                water[k] = min(water.get(k, 1e9), v)
        n_l += s['kind'] == 'lake'
        n_r += s['kind'] == 'river'
    return water, n_r, n_l


def lay_pads(w, lay, progress):
    """Each building's ground level at the middle height under it, back to its own height over PAD_FADE. Returns a marker layer's rows. Heights stay on steps."""
    rows, made = [], 0
    n = len(lay['buildings'])
    for b_i, b in enumerate(lay['buildings']):
        if progress and b_i % 50 == 0:
            progress('Levelling building plots', b_i, n)
        ring = b['ring']
        x0, x1 = min(p[0] for p in ring), max(p[0] for p in ring)
        y0, y1 = min(p[1] for p in ring), max(p[1] for p in ring)
        gx0, gx1 = int(math.floor((x0 - PAD_FADE) / 128)), int(math.ceil((x1 + PAD_FADE) / 128))
        gy0, gy1 = int(math.floor((y0 - PAD_FADE) / 128)), int(math.ceil((y1 + PAD_FADE) / 128))
        inner, pts = [], []
        for gy in range(gy0, gy1 + 1):
            for gx in range(gx0, gx1 + 1):
                cx, cy = gx // 32, gy // 32
                h = w.heights(cx, cy)
                if h is None:
                    continue
                z = h[(gy - cy * 32) * 33 + (gx - cx * 32)]
                p = (gx * 128.0, gy * 128.0)
                ins = landshape.inside(p, ring)
                pts.append((gx, gy, z, ins, p))
                if ins:
                    inner.append(z)
        row = {'ring': _round(ring), 'name': b['name'], 'kind': b['kind'], 'pad': False}
        if len(inner) >= PAD_MIN_POINTS:
            level = _step(sorted(inner)[len(inner) // 2])
            for gx, gy, z, ins, p in pts:
                if ins:
                    new = level
                else:
                    d = landshape.line_dist(p, ring, closed=True)
                    if d >= PAD_FADE:
                        continue
                    new = _step(level + (z - level) * landshape.smooth(d / PAD_FADE))
                if new != z:
                    w.put_point(gx, gy, new)
            row.update(pad=True, level=level)
            made += 1
        rows.append(row)
    return rows, made


def lay_roads(gd, w, lay, want, seed, progress):
    """(ops placing road pieces, how many, how long, ways skipped). The ground is settled under all of them at once."""
    kit = roadgen.pieces(gd)
    if 'a' not in kit:
        raise roadgen.RoadError('The game\'s road pieces aren\'t in its files.')
    g = roadgen.Ground(gd, w.over, w.world)
    rng = random.Random(seed)
    wet_cells = {}

    def dry(x, y, z):
        k = (int(x // CELL), int(y // CELL))
        if k not in wet_cells:
            wet_cells[k] = g.water(x, y)
        return wet_cells[k] is None or z >= wet_cells[k]
    things, spans, total, skipped = [], [], 0.0, 0
    roads = [r for r in lay['roads'] if r['class'] in want.get('roads', ())]
    for i, r in enumerate(roads):
        if progress and i % 20 == 0:
            progress('Laying roads', i, len(roads))
        line = roadgen.smooth(r['line'], 2)
        try:
            out, sp = roadgen.lay_line(g, line, kit, rng, r['caps'], dry)
        except roadgen.RoadError:
            skipped += 1
            continue
        things += out
        spans += sp
        total += length(line)
    if progress:
        progress('Settling the ground under the roads')
    settled = roadgen.settled(gd, w.over, w.world, g, spans) if spans else {}
    for ck, form in settled.items():
        w.over.land[ck] = {n: form[n] for n in ('h', 'c', 'q')}
        w.changed.add(ck)
    # (laying the same file again, or with more ticked, adds only what isn't there yet: a piece's place comes out the same each time)
    keys = {gd.key(c) for c in w.grid.values()}
    have = {(round(r['p'][0]), round(r['p'][1])) for ck, c in w.pr.cells.items() if ck in keys for r in c['refs'].values() if r.get('p')}
    ops = []
    for t in things:
        c = w.grid.get((int(t['p'][0] // CELL), int(t['p'][1] // CELL)))
        if c is not None and (round(t['p'][0]), round(t['p'][1])) not in have:
            ops.append({'op': 'add', 'cell': gd.key(c), 'base': t['base'], 'p': t['p'], 's': 1})
    return ops, total, skipped


def plan_check(lay, want):
    """(pieces it comes to, a warning, why not)."""
    pieces = sum(int(length(r['line']) / (roadgen.PIECE - roadgen.OVERLAP)) + 1 for r in lay['roads'] if r['class'] in want.get('roads', ()))
    if pieces > PIECES_STOP:
        return pieces, None, 'That\'s %s road pieces, more than FOLab lays in one go (%s): leave out the lesser roads, or make the land at a smaller scale.' % (format(pieces, ','), format(PIECES_STOP, ','))
    if pieces > PIECES_WARN:
        return pieces, 'That\'s %s road pieces: it\'ll take a while, and the mod will be big.' % format(pieces, ','), None
    return pieces, None, None


def ops_for(gd, pr, world, lay, want, compress, seed=1, progress=None):
    """(ops as one Undo, a report, the marker layer)."""
    pieces, _warn, stop = plan_check(lay, want)
    if stop:
        raise ValueError(stop)
    w = Work(gd, pr, world)
    water, n_r, n_l = lay_water(w, lay, want, compress, progress)
    rows, pads = [], 0
    if want.get('buildings'):
        rows, pads = lay_pads(w, lay, progress)
    else:
        rows = [{'ring': _round(b['ring']), 'name': b['name'], 'kind': b['kind'], 'pad': False} for b in lay['buildings']]
    ops, total, skipped = lay_roads(gd, w, lay, want, seed, progress) if want.get('roads') else ([], 0.0, 0)
    for ck in sorted(w.changed):
        ops.append({'op': 'land', 'cell': ck, 'land': w.over.land[ck]})
    levels = 0
    for k, v in sorted(water.items()):
        if v > 0 and k in w.grid:
            ops.append({'op': 'water', 'cell': gd.key(w.grid[k]), 'h': round(v, 1)})
            levels += 1
    layer = {'buildings': rows, 'places': [{'p': _round([p['p']])[0], 'name': p['name'], 'kind': p['kind']} for p in lay['places']],
             'bridges': [{'line': _round(b['line']), 'name': b['name'], 'kind': b['kind']} for b in lay['bridges']]}
    report = {'pieces': sum(1 for o in ops if o['op'] == 'add'), 'road_units': round(total), 'roads_skipped': skipped, 'rivers': n_r, 'lakes': n_l, 'water_cells': levels, 'pads': pads,
              'buildings': len(rows), 'pads_too_small': sum(1 for r in rows if not r['pad']) if want.get('buildings') else 0, 'bridges': len(layer['bridges']), 'places': len(layer['places']),
              'land_cells': len(w.changed), 'cell_xy': [list(gd.cell_grid(gd.from_key(ck))) for ck in sorted(w.changed)]}
    return ops, report, layer
