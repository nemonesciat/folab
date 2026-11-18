"""A world made from a height file grown in place: more of the same file added round it, at the same scale, without remaking
what's there. The world's cells keep every change the mod has made to them (land, things, navmeshes, interiors); only cells
that weren't there before are made, and they're added to the world as it stands in the mod's own source plugin, numbered
from the mod's next free ID (as viewworld.add_world adds a small world).

    grown_side     the sidecar (api_maps) of the bigger world: whole cells added on each side to cover a box asked for in
                   degrees, the same pixels per cell and the same game place for every pixel, so the old cells' ground sits
                   where it did (x0, y0 move by the cells added west and south; col0, row0 by the pixels of those cells)
    land_grid      the bigger world's land points from the file as the world was made (roofs off, the sea shaped, relief),
                   then the old cells' land as the mod has it now laid over them, and the new ground eased into it within
                   SEAM points of the old edge, so the two meet exactly; slopes kept to what VHGT holds without moving an
                   old point
    add_cells      the new CELL and LAND records written into the world's group of the source plugin, the world's bounds
                   (NAM0, NAM9, MNAM) brought out to the new size, in the plugin and in any record of the world the mod keeps

Later steps (roads, buildings, things, life, navmeshes) run as for a new world, kept to the new cells (`only`, `keep_new`)."""
import array
import contextlib
import math
import os
import struct

import espwrite
import land
import mapscale as MS
import plugintree
import tes4
import viewworld

CELL = MS.CELL
PER = MS.PER_CELL
SEAM = 48                   # (land points over which new ground eases into the old: a cell and a half)


# ---------- how big ----------

def pixel_of_deg(geo, lat, lon):
    if geo.get('kind') != 'deg':
        import elevation
        return elevation.pixel_of(geo, lat, lon)
    return (lon - geo['x0']) / geo['dx'], (geo['y0'] - lat) / geo['dy']


def grown_side(side, box):
    """The sidecar of the world grown to cover box (south lat, west lon, north lat, east lon), never smaller than it is.
    Returns (new side, (west, east, north, south) cells added)."""
    s = dict(side)
    pcx, pcy = CELL / s['upx'], CELL / s['upy']           # (pixels a cell)
    lat_s, lon_w, lat_n, lon_e = box
    c_w, r_n = pixel_of_deg(s['geo'], lat_n, lon_w)
    c_e, r_s = pixel_of_deg(s['geo'], lat_s, lon_e)
    c_w, c_e = max(0.0, min(c_w, c_e)), min(s['px_w'] - 1.0, max(c_w, c_e))
    r_n, r_s = max(0.0, min(r_n, r_s)), min(s['px_h'] - 1.0, max(r_n, r_s))
    west = max(0, int(math.floor((s['col0'] - c_w) / pcx + 1e-6)))
    east = max(0, int(math.floor((c_e - (s['col0'] + s['W'] * pcx)) / pcx + 1e-6)))
    north = max(0, int(math.floor((s['row0'] - r_n) / pcy + 1e-6)))
    south = max(0, int(math.floor((r_s - (s['row0'] + s['H'] * pcy)) / pcy + 1e-6)))
    s.update(W=s['W'] + west + east, H=s['H'] + north + south, x0=s['x0'] - west, y0=s['y0'] - south,
             col0=s['col0'] - west * pcx, row0=s['row0'] - north * pcy)
    return s, (west, east, north, south)


def cells_of(side):
    return {(x, y) for x in range(side['x0'], side['x0'] + side['W']) for y in range(side['y0'], side['y0'] + side['H'])}


def plan_of(raster, side):
    """A mapscale.Plan with exactly the sidecar's numbers (a Plan works out its own from a rectangle: here they're given)."""
    p = MS.Plan(raster, side.get('opts') or {})
    p.W, p.H, p.x0, p.y0, p.col0, p.row0 = side['W'], side['H'], side['x0'], side['y0'], side['col0'], side['row0']
    pcx, pcy = p.ppx * PER, p.ppy * PER
    p.area = (p.col0, p.row0, min(raster.w - 1.0, p.col0 + p.W * pcx), min(raster.h - 1.0, p.row0 + p.H * pcy))
    p.base = float(side['base'])
    if abs(p.upx - side['upx']) > 1e-6 or abs(p.upy - side['upy']) > 1e-6 or abs(p.k - side['k']) > 1e-6:
        raise ValueError('The height file doesn\'t give the scale this world was made at: it can\'t be grown from it.')
    return p


# ---------- the land ----------

def old_heights(gd, pr, world):
    """{(x, y): 1089 heights} for each of the world's cells as the mod has them now."""
    out = {}
    for (x, y), c in gd.grid(world).items():
        f = pr.land.get(gd.key(c))
        if f and f.get('h'):
            out[(x, y)] = list(f['h'])
            continue
        e = gd.land.get(c)
        if e:
            out[(x, y)] = list(land.heights_of(dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1])))['VHGT']))
    return out


def lay_old(grid, old):
    """The old cells' land over the grid; returns a bytearray marking the points it holds."""
    a, n = grid.across, grid.across * grid.down
    fixed = bytearray(n)
    for (x, y), h in old.items():
        i, j = x - grid.x0, y - grid.y0
        if not (0 <= i < grid.W and 0 <= j < grid.H):
            continue
        for r in range(33):
            s = (j * PER + r) * a + i * PER
            grid.pts[s:s + 33] = array.array('f', h[r * 33:(r + 1) * 33])
            fixed[s:s + 33] = b'\x01' * 33
    return fixed


def ease_seam(grid, raw, fixed, reach=SEAM):
    """New ground within reach points of the old taken toward it: by how much the old edge differs from what the file
    says there, less the further in. raw: the grid's points before the old land was laid. Returns points moved."""
    a, d, p = grid.across, grid.down, grid.pts
    n = a * d
    dist = [-1] * n
    delta = [0.0] * n
    front = []
    for q in range(n):
        if fixed[q]:
            dist[q] = 0
            delta[q] = p[q] - raw[q]
            front.append(q)
    step = 0
    while front and step < reach:
        step += 1
        nxt = []
        for q in front:
            gx, gy = q % a, q // a
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                x, y = gx + dx, gy + dy
                if 0 <= x < a and 0 <= y < d:
                    t = y * a + x
                    if dist[t] < 0:
                        dist[t] = step
                        delta[t] = delta[q]
                        nxt.append(t)
        front = nxt
    moved = 0
    for q in range(n):
        if dist[q] > 0 and delta[q]:
            w = 1.0 - dist[q] / float(reach + 1)
            w = w * w * (3 - 2 * w)                  # (smooth at both ends)
            z = round((raw[q] + delta[q] * w) / MS.STEP) * MS.STEP
            if z != p[q]:
                p[q] = z
                moved += 1
    return moved


def near_fixed(grid, fixed, reach):
    """The points that aren't fixed within reach of one that is, nearest first."""
    a, d = grid.across, grid.down
    seen = bytearray(fixed)
    front = [q for q in range(a * d) if fixed[q]]
    out = []
    for _ in range(reach):
        nxt = []
        for q in front:
            gx, gy = q % a, q // a
            for x, y in ((gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)):
                if 0 <= x < a and 0 <= y < d and not seen[y * a + x]:
                    seen[y * a + x] = 1
                    nxt.append(y * a + x)
        out += nxt
        front = nxt
    return out


def keep_slopes(grid, fixed, rise=MS.MAX_RISE, rounds=200, reach=SEAM + 8):
    """No two neighbours further apart than rise, moving only points that aren't fixed (up or down: a new point beside an
    old one goes to where the old one lets it), within reach of the old land (further out, limit_slopes has done it).
    Returns points moved."""
    a, d, p = grid.across, grid.down, grid.pts
    todo = near_fixed(grid, fixed, reach)
    moved = 0
    for _ in range(rounds):
        changed = 0
        for q in todo:
            if True:
                gx, gy = q % a, q // a
                z = p[q]
                lo, hi = -1e9, 1e9
                for x, y in ((gx - 1, gy), (gx + 1, gy), (gx, gy - 1), (gx, gy + 1)):
                    if 0 <= x < a and 0 <= y < d:
                        v = p[y * a + x]
                        lo, hi = max(lo, v - rise), min(hi, v + rise)
                if z > hi:
                    z = hi
                elif z < lo:
                    z = lo
                if z != p[q]:
                    p[q] = z
                    changed += 1
        moved += changed
        if not changed:
            break
    return moved


def land_grid(plan, old, shape=None, progress=None):
    """The grown world's land points: the file's, shape(grid) for what was done to them when the world was made (roofs off,
    the sea, relief), then the old land laid over and the new eased to it. Returns (grid, fixed, report)."""
    grid = MS.heights(plan, progress)
    if shape:
        shape(grid)
    raw = grid.pts[:]
    fixed = lay_old(grid, old)
    eased = ease_seam(grid, raw, fixed)
    # (a whole sweep the ordinary way first, then put back what it took off an old point and settle the new ones round it)
    MS.limit_slopes(grid.pts, grid.across, grid.down)
    lay_old(grid, old)
    steep = keep_slopes(grid, fixed)
    return grid, fixed, {'eased': eased, 'settled': steep}


# ---------- into the plugin ----------

def _world_group(tree, wid):
    for top in tree.tops:
        if top.label == plugintree.type_label('WRLD') and top.gtype == tes4.G_TOP:
            for k in top.kids:
                if isinstance(k, plugintree.Group) and k.gtype == tes4.G_WORLD_CHILDREN and k.label == wid:
                    return top, k
    raise ValueError('The world isn\'t in the mod\'s own plugin.')


def _first_cell(wkids):
    """A grid cell already in the world: what new cells copy (lighting template, acoustics, water, region)."""
    stack = [wkids]
    while stack:
        g = stack.pop()
        for k in g.kids:
            if isinstance(k, plugintree.Group):
                if k.gtype in (tes4.G_EXT_BLOCK, tes4.G_EXT_SUBBLOCK):
                    stack.append(k)
            elif k.tag == 'CELL' and not k.flags & tes4.PERSISTENT:
                return k
    return None


def bounds_subs(subs, side):
    """A WRLD's subrecords with its bounds (NAM0, NAM9) and map (MNAM: its size and corner cells) the side's."""
    x0, y0, nx, ny = side['x0'], side['y0'], side['W'], side['H']
    wide = max(nx, ny)
    out = []
    for t, d in subs:
        if t == 'NAM0':
            d = struct.pack('<2f', x0 * CELL, y0 * CELL)
        elif t == 'NAM9':
            d = struct.pack('<2f', (x0 + nx) * CELL, (y0 + ny) * CELL)
        elif t == 'MNAM' and len(d) >= 16:
            d = struct.pack('<iihhhh', 2048 * nx // wide, 2048 * ny // wide, x0, y0 + ny - 1, x0 + nx - 1, y0) + d[16:]
        out.append((t, d))
    return out


def add_cells(gd, pr, world, side, cells, land_for, wet, progress=None):
    """New grid cells (x, y) with their land added to the world in the mod's source plugin; the world's bounds to the
    grown side. The game must be loaded again after. Returns how many were added."""
    if not pr.source:
        raise ValueError('Only a mod opened from a plugin can be grown this way.')
    me = viewworld.source_index(gd, pr)
    path = pr.source_path()
    tree = plugintree.Plugin.read(path)
    w = viewworld.SourceWriter(gd, me)
    wid = w.local(world)
    top, wkids = _world_group(tree, wid)
    have = set(gd.grid(world))
    tpl = _first_cell(wkids)
    if tpl is None:
        raise ValueError('The world has no cells to take after.')
    tsubs = [(t, d) for t, d in tes4.iter_subrecords(tpl.data()) if t not in ('EDID', 'FULL', 'XCLR')]
    lowest = None
    label = lambda a, b: struct.unpack('<I', struct.pack('<hh', a, b))[0]
    nid = pr.next_id

    def new_id():
        nonlocal nid
        nid += 1
        return w.own(nid - 1)
    todo = sorted(c for c in cells if c not in have)
    for n, (x, y) in enumerate(todo):
        form, beyond = land_for(x, y)
        if lowest is None:
            lowest = min(form['h'])
        lowest = min(lowest, min(form['h']))
        csubs = [(t, struct.pack('<iiI', x, y, 0) if t == 'XCLC' else d) for t, d in tsubs]
        wv = wet(x, y)
        if wv is True:
            csubs = espwrite.set_water(csubs, None)
        elif wv is False or wv is None:
            csubs = espwrite.dry(csubs, min(form['h']))
        else:
            csubs = espwrite.set_water(csubs, float(wv))
        cid = new_id()
        block = w._group(wkids, label(y // 32, x // 32), tes4.G_EXT_BLOCK)
        sub = w._group(block, label(y // 8, x // 8), tes4.G_EXT_SUBBLOCK)
        kids = plugintree.Group(cid, tes4.G_CELL_CHILDREN)
        temp = plugintree.Group(cid, tes4.G_CELL_TEMPORARY)
        raw = espwrite.join(land.encode(form, [('DATA', struct.pack('<I', 0x1F))], w.link, beyond))
        temp.kids.append(plugintree.Rec.packed('LAND', 0, new_id(), raw, espwrite.FORM_VERSION))
        kids.kids.append(temp)
        sub.kids += [plugintree.Rec.new('CELL', 0, cid, espwrite.join(csubs), espwrite.FORM_VERSION), kids]
        if progress:
            progress(n + 1, len(todo))
    # the world's bounds, in the plugin
    for k in top.kids:
        if not isinstance(k, plugintree.Group) and k.tag == 'WRLD' and k.formid == wid:
            subs = bounds_subs(list(tes4.iter_subrecords(k.data())), side)
            k.set_data(espwrite.join(subs), k.flags)
    import worldgen
    worldgen.fix_header(tree, w.own(nid))
    data = tree.bytes()
    for p in gd.plugins:
        if p is gd.plugins[me]:
            p.close()
    with open(path + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(path + '.tmp', path)
    pr.next_id = nid
    return len(todo)


def world_record_ops(gd, pr, world):
    """If the mod keeps a record of the world (the Pip-Boy map, say), the world's bounds in it brought to what the plugin
    now says (the plugin was grown under it): a record op, or []. MNAM is left to worldmap.ops, whose picture it matches."""
    import recordio
    key = gd.key(world)
    rec = pr.records.get(key)
    if not rec or not rec.get('subs'):
        return []
    now = recordio.load(gd, world)
    fresh = {s['tag']: s for s in now['subs'] if s['tag'] in ('NAM0', 'NAM9')}
    new = dict(rec, subs=[dict(fresh[s['tag']]) if s['tag'] in fresh else dict(s) for s in rec['subs']])
    return [{'op': 'record', 'key': key, 'record': new}]


# ---------- later steps kept to the new cells ----------

@contextlib.contextmanager
def only(gd, world, cells):
    """gd.grid(world) as just these cells while the steps run (their work and their reach), the whole world after."""
    real = gd.grid
    keep = set(cells)

    def grid(w, *a, **k):
        g = real(w, *a, **k)
        if w == world:
            return {xy: c for xy, c in g.items() if xy in keep}
        return g
    gd.grid = grid
    try:
        yield
    finally:
        gd.grid = real


def keep_new(gd, ops, old_keys):
    """Ops less those that would change one of the world's old cells (its land, water, what stands in it)."""
    out = []
    for o in ops:
        c = o.get('cell')
        if c and c in old_keys:
            continue
        out.append(o)
    return out


def lay_within(lay, cells, step=256.0):
    """An osmplace.layout kept to what touches these cells: a line any point of which (every step units along it) is in
    one, a ring with a corner or its middle in one, a place in one."""
    cells = set(cells)
    inside = lambda x, y: (int(math.floor(x / CELL)), int(math.floor(y / CELL))) in cells

    def line_in(pts):
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
            for k in range(n + 1):
                if inside(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n):
                    return True
        return len(pts) == 1 and inside(*pts[0])

    def ring_in(r):
        return any(inside(*p) for p in r) or inside(sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r))
    out = dict(lay)
    for k in ('roads', 'bridges', 'rivers'):
        out[k] = [r for r in lay.get(k) or [] if line_in(r['line'])]
    for k in ('lakes', 'buildings'):
        out[k] = [r for r in lay.get(k) or [] if ring_in(r['ring'])]
    out['places'] = [p for p in lay.get('places') or [] if inside(*p['p'])]
    return out


def middle_in(ring_pts, cells):
    x = sum(p[0] for p in ring_pts) / len(ring_pts)
    y = sum(p[1] for p in ring_pts) / len(ring_pts)
    return (int(math.floor(x / CELL)), int(math.floor(y / CELL))) in set(cells)


def seam_ops(gd, pr, world, added):
    """Land ops putting each new cell's edge points back to the old cell's beside it (where later steps moved one side of
    a shared edge and not the other: the old cells are never changed by them). [] if nothing differs."""
    grid = gd.grid(world)
    added = set(added)
    old = {}

    def h_of(xy):
        if xy not in old:
            c = grid.get(xy)
            f = pr.land.get(gd.key(c)) if c is not None else None
            if f and f.get('h'):
                old[xy] = f['h']
            else:
                e = gd.land.get(c) if c is not None else None
                old[xy] = list(land.heights_of(dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1])))['VHGT'])) if e else None
        return old[xy]
    ops = []
    tex = {}
    for (x, y) in sorted(added):
        c = grid.get((x, y))
        if c is None:
            continue
        mine = h_of((x, y))
        if mine is None:
            continue
        new = list(mine)
        for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            nb = (x + dx, y + dy)
            if nb in added or nb not in grid:
                continue
            theirs = h_of(nb)
            if theirs is None:
                continue
            for r in range(33):
                for cc in range(33):
                    # (this point's place in the neighbour's 33 x 33, if it has it)
                    tr, tc = r - 32 * dy, cc - 32 * dx
                    if 0 <= tr <= 32 and 0 <= tc <= 32:
                        new[r * 33 + cc] = theirs[tr * 33 + tc]
        if new != list(mine):
            f = pr.land.get(gd.key(c))
            f = dict(f) if f else land.decode(gd, gd.land[c], tex)
            f = {n: f[n] for n in ('h', 'c', 'q')}
            f['h'] = new
            ops.append({'op': 'land', 'cell': gd.key(c), 'land': f})
    return ops


def cellinfo_ops(gd, pr, world, added, start=None):
    """What the world's cells say beyond their land (regions, water, music, encounter zone: project.cellinfo) given to the
    new cells as the nearest old cell has it; the zone, if the start is known, by how far the cell is from it, as
    worldlife.zones gave the old ones (the zone the old cells at that distance have)."""
    import worldlife
    grid = gd.grid(world)
    added = set(added)
    old = [(xy, pr.cellinfo.get(gd.key(c))) for xy, c in grid.items() if xy not in added and pr.cellinfo.get(gd.key(c))]
    if not old:
        return []

    def tier(xy):
        if not start:
            return None
        d = max(abs(xy[0] - int(start[0] // 4096)), abs(xy[1] - int(start[1] // 4096)))
        return max(n for n, (frm, _lvl) in enumerate(worldlife.TIERS) if d >= frm)
    zone_of = {}
    for xy, info in old:
        t = tier(xy)
        if t is not None and info.get('XEZN'):
            zone_of.setdefault(t, info['XEZN'])
    ops = []
    for xy in sorted(added):
        c = grid.get(xy)
        if c is None:
            continue
        _o, near = min(old, key=lambda o: (o[0][0] - xy[0]) ** 2 + (o[0][1] - xy[1]) ** 2)
        info = dict(near)
        t = tier(xy)
        if t is not None:
            z = zone_of.get(t) or zone_of.get(max([k for k in zone_of if k <= t] or [min(zone_of)])) if zone_of else None
            if z:
                info['XEZN'] = z
        ops.append({'op': 'cellinfo', 'cell': gd.key(c), 'info': info})
    return ops


def ring(cells, n=1):
    s = set(cells)
    for _ in range(n):
        s |= {(x + dx, y + dy) for x, y in s for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    return s
