"""The Pip-Boy's world map for a world of the mod's own.

The game shows a world's map from the picture its WRLD record names (ICON, under textures\\, a 1024 square for every
world the game ships) laid over the cells MNAM says: the usable width and height, then the north-west cell and the
south-east cell it covers. A world FOLab made has neither (worldgen drops the template's ICON, since that picture is
another place), so its Pip-Boy map was blank, nothing to see markers on and nothing to click to travel.

`picture` draws one in the game's own manner (its maps are grey, the Pip-Boy tints them): the ground shaded from the
world's own heights, light from the north-west; the sea flat and dark with a pale shoreline; roads and paving light,
buildings a mid grey block each, from what the mod has placed; a faint grid; the frame's tick marks and corner
brackets. `ops` puts it in the mod's own files and points the world at it, with MNAM made to cover a square round the
world so the picture and the cells agree. Markers are left as they are: one shows when found, as the game's do."""
import math
import os
import struct

import dds
import library
import navgen
import roadgen

SIZE = 1024
MARGIN = 1                  # (cells of sea round the world, so its edge isn't hard against the frame)
FOLDER = 'interface\\worldmap'
NO_TRAVEL = 0x02            # (a world's DATA flag: no fast travel in it)


def _square(grid):
    xs = [k[0] for k in grid]
    ys = [k[1] for k in grid]
    x0, x1, y0, y1 = min(xs) - MARGIN, max(xs) + MARGIN, min(ys) - MARGIN, max(ys) + MARGIN
    n = max(x1 - x0, y1 - y0) + 1
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    x0, y0 = int(math.floor(cx - (n - 1) / 2.0)), int(math.floor(cy - (n - 1) / 2.0))
    return x0, y0, n                              # (west cell, south cell, cells across)


def picture(gd, pr, world, size=SIZE, progress=None):
    """(RGBA bytes of a size x size picture, rows from the north, (x0, y0, n): the square of cells it shows)."""
    grid = gd.grid(world)
    x0, y0, n = _square(grid)
    g = roadgen.Ground(gd, pr, world)
    span = n * 4096.0
    per = span / size                             # (game units a pixel)
    # heights on the picture's pixels (and the water's)
    H = [0.0] * (size * size)
    W = [None] * (size * size)
    wet = {}
    for j in range(size):
        if progress and j % 128 == 0:
            progress('Drawing the map', j, size)
        wy = (y0 + n) * 4096.0 - (j + 0.5) * per
        for i in range(size):
            wx = x0 * 4096.0 + (i + 0.5) * per
            z = g.at(wx, wy)
            k = (int(wx // 4096), int(wy // 4096))
            if k not in wet:
                wet[k] = g.water(wx, wy) if k in grid else 0.0
            H[j * size + i] = z if z is not None else -2000.0
            W[j * size + i] = wet[k]
    px = bytearray(size * size * 4)
    lx, ly, lz = -0.6, 0.6, 0.55                  # (the light: from the north-west, high)
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    for j in range(size):
        for i in range(size):
            k = j * size + i
            z, w = H[k], W[k]
            zx = H[k + 1] - H[k - 1] if 0 < i < size - 1 else 0.0
            zy = H[k - size] - H[k + size] if 0 < j < size - 1 else 0.0
            nx, ny, nz = -zx, -zy, 2.0 * per
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            shade = max(0.0, (nx * lx + ny * ly + nz * lz) / (nl * ln))
            if w is not None and z < w:
                depth = w - z
                v = 46 + max(0, 18 - depth / 40.0)  # (shallows a little lighter)
            else:
                v = 40 + 70 * shade + min(30.0, max(0.0, z) / 120.0)
            v = int(max(0, min(255, v)))
            o = k * 4
            px[o] = px[o + 1] = px[o + 2] = v
            px[o + 3] = 255
    # the shoreline
    for j in range(1, size - 1):
        for i in range(1, size - 1):
            k = j * size + i
            w = W[k]
            if w is None or H[k] < w:
                continue
            if any(W[q] is not None and H[q] < W[q] for q in (k - 1, k + 1, k - size, k + size)):
                o = k * 4
                px[o] = px[o + 1] = px[o + 2] = 150
    # what the mod placed: roads and paving light, buildings mid grey
    _things(gd, pr, world, px, size, x0, y0, n, per)
    # the grid: a faint line every cell
    step = size / float(n)
    for c in range(1, n):
        p = int(round(c * step))
        for q in range(size):
            for o in (((q * size) + p) * 4, ((p * size) + q) * 4):
                px[o] = px[o + 1] = px[o + 2] = min(255, px[o] + 14)
    _frame(px, size)
    return bytes(px), (x0, y0, n)


def _fill(px, size, pts, v):
    """A convex outline (pixel coordinates) filled with grey v."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    for j in range(max(0, int(min(ys))), min(size, int(max(ys)) + 1)):
        cy = j + 0.5
        hits = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if (a[1] <= cy < b[1]) or (b[1] <= cy < a[1]):
                hits.append(a[0] + (cy - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
        if len(hits) >= 2:
            for i in range(max(0, int(min(hits))), min(size, int(max(hits)) + 1)):
                o = (j * size + i) * 4
                px[o] = px[o + 1] = px[o + 2] = max(px[o], v)


def _things(gd, pr, world, px, size, x0, y0, n, per):
    import roadbed
    import townbuild
    roads = roadbed._flat_bases(gd, pr)
    slabs = roadbed._slab_bases(gd)
    try:
        import server
        cat = {b['key']: b['box'] for b in townbuild.load(gd, server.kits_folder())}
    except Exception:
        cat = {}
    keys = {gd.key(c) for c in gd.grid(world).values()}

    def at(wx, wy):
        return ((wx - x0 * 4096.0) / per, ((y0 + n) * 4096.0 - wy) / per)
    for ck, c in pr.cells.items():
        if ck not in keys:
            continue
        for _rk, r in c['refs'].items():
            b, p = r.get('base'), r.get('p')
            if not b or not p or r.get('removed'):
                continue
            box, v = (roads.get(b), 205) if b in roads else (slabs.get(b), 170) if b in slabs else (cat.get(b), 135) if b in cat else (None, 0)
            if not box:
                continue
            s = float(r.get('s') or 1.0)
            R = navgen._turn(p[3], p[4], p[5])
            pts = [at(p[0] + (R[0][0] * lx + R[0][1] * ly) * s, p[1] + (R[1][0] * lx + R[1][1] * ly) * s)
                   for lx, ly in ((box[0], box[1]), (box[3], box[1]), (box[3], box[4]), (box[0], box[4]))]
            _fill(px, size, pts, v)


def _frame(px, size):
    """The game's map frame: tick marks round the edge, brackets in the corners."""
    def dot(i, j, v=220):
        if 0 <= i < size and 0 <= j < size:
            o = (j * size + i) * 4
            px[o] = px[o + 1] = px[o + 2] = v
    edge = max(4, size // 128)
    for t in range(0, size, max(8, size // 64)):
        for d in range(edge):
            dot(t, d), dot(t, size - 1 - d), dot(d, t), dot(size - 1 - d, t)
    arm, inset, w = size // 16, size // 40, max(2, size // 400)
    for cx, cy, sx, sy in ((inset, inset, 1, 1), (size - 1 - inset, inset, -1, 1), (inset, size - 1 - inset, 1, -1), (size - 1 - inset, size - 1 - inset, -1, -1)):
        for a in range(arm):
            for t in range(w):
                dot(cx + sx * a, cy + sy * t), dot(cx + sx * t, cy + sy * a)


def path_for(gd, world):
    return FOLDER + '\\folab_' + (gd.edid(world) or 'world').lower() + '.dds'


def ops(gd, pr, world, size=SIZE, progress=None):
    """(ops, report): the map's picture written to the mod's own files, and the world record pointed at it."""
    import recordio
    rgba, (x0, y0, n) = picture(gd, pr, world, size, progress)
    rel = path_for(gd, world)
    dest = os.path.join(library.assets_dir(pr), 'textures', rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    import install
    install.write_new(dest, dds.encode(size, size, rgba))
    key = gd.key(world)
    rec = pr.records.get(key) or recordio.load(gd, world)
    rec = dict(rec, subs=[dict(s) for s in rec['subs']])
    recordio.set_field(rec, 'ICON', rel)
    mnam = struct.pack('<iihhhh', size, size, x0, y0 + n - 1, x0 + n - 1, y0)
    _set_raw(rec, 'MNAM', mnam)
    flags = _raw(rec, 'DATA')
    travel = True
    if flags and flags[0] & NO_TRAVEL:
        _set_raw(rec, 'DATA', bytes([flags[0] & ~NO_TRAVEL]) + flags[1:])
        travel = False
    return [{'op': 'record', 'key': key, 'record': rec}], {'picture': rel, 'size': size, 'cells': [x0, y0, n], 'fast_travel_was_off': not travel}


def _raw(rec, tag):
    for s in rec['subs']:
        if s['tag'] == tag:
            v = s.get('value')
            return bytes.fromhex(v) if isinstance(v, str) and s.get('kind') == 'raw' else (v if isinstance(v, (bytes, bytearray)) else None)
    return None


def _set_raw(rec, tag, data):
    for s in rec['subs']:
        if s['tag'] == tag:
            s.clear()
            s.update({'tag': tag, 'label': tag, 'kind': 'raw', 'value': bytes(data).hex()})
            return
    rec['subs'].append({'tag': tag, 'label': tag, 'kind': 'raw', 'value': bytes(data).hex()})
