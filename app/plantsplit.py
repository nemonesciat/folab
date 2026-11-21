"""FOLab's jungle clumps taken apart (plantsplit.py): each plant of a clump stood on its own, upright, on the ground at
its own foot.

The clumps (modelsets.jungle_floor, slope_cover, thicket, undergrowth) were several plants as one model, laid along the
slope as a whole (modelsets.LAID). Ground is never one flat plane twelve metres across: on Waikiki 30,188 of 53,451
clumps had a plant more than 8 units off the ground, 15,827 more than 50, and every plant leaned with the hill (the user
in nv-rs, 20 Nov 2026: "ferns floating in the air everywhere", "why are they all turned up at an angle", "always the
same grass"). A clump can't be fitted to curved ground, so a plant is one thing:

  - LAYOUT: what each clump held, read from the clump's own making (modelsets.combine spied on), each plant as a piece
    of its own (SINGLES: the clumps' shrubs and small ferns and taro as pieces; the ferns, taro, ti and heliconia the set
    already had);
  - every grass a clump had is one of GRASSES (six tufts, each its own picture and shape), picked by where it stands so
    two side by side are seldom the same;
  - a clump whose plants' feet all lie on one plane of ground within KEEP_FIT, no steeper than KEEP_TILT, stays whole,
    laid on that plane (`fit`): one thing to draw instead of a dozen;
  - `split` gives the ops for the rest: the clump taken out, each plant added upright where its foot is now, at the land's height
    there, let `sink` into the ground and further on a slope (`SLOPE_SINK`: its downhill side reaches the ground);
    nothing on a road, in a building or a landmark, in the sea, or on ground steeper than `STEEP`;
  - `feet` measures: every plant of the mod's own pieces against the land at its foot (what the old check, which took a
    clump as one box, never did)."""
import math
import zlib

import modelsets as ms
import texpaint as tp

STEEP = 1.2                 # rise over run past which a plant is left out (50 degrees: a cliff face)
SINK = 2.0                  # every plant this far into the ground (times its size)
SLOPE_SINK = 0.5            # and this share of how much the ground falls across its radius, so its downhill side is down
SINK_MOST = 40.0
KEEP_TILT = 10.0           # a clump is kept whole where the ground under all its plants is a plane this steep at most (degrees)...
KEEP_FIT = 5.0              # ...that every plant's foot is within this of (the user, 20 Nov 2026: "keep clumps for flat terrain
#                             where no floating occurs ... dont place spreading plant arrangements on an area of terrain with a
#                             face too small to support it")
# taken apart, a clump's small plants are thinned (each kept one a little bigger): Waikiki went from 538,000 things to
# 915,000 with every plant kept, 214 a cell where it had 126. piece -> (keep one in, grown by)
THIN = {}                   # (thinning left bare dirt round the start, 20 Nov 2026: every plant is kept)
CLUMPS = ('jungle_floor_a', 'jungle_floor_b', 'slope_cover_a', 'slope_cover_b', 'thicket', 'undergrowth')

# the grasses: (texture, seed, colour; card wide, tall, cards). Each tuft is its own picture.
GRASSES = {
    'grass_tuft': ('jungle/grass_tuft', None, None, 112, 56, 3),
    'grass_fine': ('jungle/grass_fine', 101, (82, 130, 54), 90, 70, 4),
    'grass_dark': ('jungle/grass_dark', 102, (58, 100, 46), 130, 50, 3),
    'grass_gold': ('jungle/grass_gold', 103, (148, 148, 78), 100, 62, 3),
    'grass_dry': ('jungle/grass_dry', 104, (164, 146, 96), 120, 44, 3),
    'grass_lush': ('jungle/grass_lush', 105, (100, 154, 68), 80, 88, 4),
}
GRASS_KEYS = tuple(GRASSES)

for _k, (_tex, _seed, _col, _w, _h, _n) in GRASSES.items():
    if _seed is not None and _tex not in ms.TEXTURES:
        ms.TEXTURES[_tex] = (lambda s=_seed, c=_col: tp.grass(seed=s, colour=c))

_caught = {}


def _capture():
    """Every clump's items as the clump makes them: {clump name: [(desc, x, y, yaw, size)]}."""
    if _caught:
        return _caught
    real = ms.combine

    def spy(name, items):
        items = list(items)
        _caught.setdefault(name, items)
        return real(name, items)
    ms.combine = spy
    try:
        for piece in CLUMPS:
            ms.PIECES[piece]['describe']()
    finally:
        ms.combine = real
    return _caught


def _fern_spots(desc):
    """The points a clump's own loose ferns grow from (parts in its 'fern' look, by their foot)."""
    spots = {}
    for q in desc['parts']:
        if q.get('look') == 'fern' and q.get('shape') == 'frond':
            at = q.get('at') or (0, 0, 0)
            spots.setdefault((round(at[0], 1), round(at[1], 1)), 0)
    return list(spots)


def _shrub_desc(parent, n, edid):
    desc = _capture()[parent][n][0]
    return dict(desc, name=edid)


# the clumps' own plants as pieces: piece -> (label, edid, describe)
SINGLES = {
    'fern_small': ('Fern, small', 'FOLabJungleFernSmall', lambda: ms.rosette('FOLabJungleFernSmall', 'jungle/fern', 9, (60, 100), 38, seed=5)),
    'taro_small': ('Taro, small', 'FOLabJungleTaroSmall',
                   lambda: ms.rosette('FOLabJungleTaroSmall', 'jungle/taro', 6, (90, 130), 70, up=(80, 50), droop=(45, 75), fold=12, seed=6)),
    'shrub_low_a': ('Shrub, low', 'FOLabJungleShrubLowA', lambda: _shrub_desc('FOLabJungleUndergrowth', 0, 'FOLabJungleShrubLowA')),
    'shrub_low_b': ('Shrub, low, flowering', 'FOLabJungleShrubLowB', lambda: _shrub_desc('FOLabJungleUndergrowth', 1, 'FOLabJungleShrubLowB')),
    'shrub_tall_a': ('Shrub, tall', 'FOLabJungleShrubTallA', lambda: _shrub_desc('FOLabJungleThicket', 0, 'FOLabJungleShrubTallA')),
    'shrub_tall_b': ('Shrub, tall, broad leaf', 'FOLabJungleShrubTallB', lambda: _shrub_desc('FOLabJungleThicket', 1, 'FOLabJungleShrubTallB')),
    'shrub_tall_c': ('Shrub, tall, dark', 'FOLabJungleShrubTallC', lambda: _shrub_desc('FOLabJungleThicket', 2, 'FOLabJungleShrubTallC')),
}
for _k, (_tex, _seed, _col, _w, _h, _n) in GRASSES.items():
    _e = 'FOLabJungle' + ''.join(w.title() for w in _k.split('_'))
    SINGLES[_k] = ('Grass, ' + _k.split('_')[1], _e, (lambda e=_e, t=_tex, w=_w, h=_h, n=_n: ms.crossed(e, t, w, h, cards=n, seed=zlib.crc32(e.encode()) % 997)))
for _k, (_label, _edid, _fn) in SINGLES.items():
    if _k not in ms.PIECES:
        ms.PIECES[_k] = {'label': _label, 'set': 'jungle', 'file': _k, 'describe': _fn, 'edid': _edid}


def _fingerprint(desc):
    import json
    return json.dumps(desc['parts'], sort_keys=True, default=str)


_layout = {}


def layout(piece):
    """A clump's plants: [(piece, x, y, yaw degrees, size)] in the clump's own frame."""
    if piece in _layout:
        return _layout[piece]
    cap = _capture()
    known = {}
    for p in ('ground_fern', 'fern_small', 'taro', 'taro_small', 'ti_red', 'ti_green', 'heliconia'):
        known[_fingerprint(ms.PIECES[p]['describe']())] = p
    grass = _fingerprint(ms.crossed('g', 'jungle/grass_tuft', 112, 56, seed=4))
    under = _fingerprint(ms.undergrowth())
    under_items = [('shrub_low_a',) + tuple(cap['FOLabJungleUndergrowth'][0][1:]), ('shrub_low_b',) + tuple(cap['FOLabJungleUndergrowth'][1][1:])]
    under_ferns = [('fern_small', x, y, 0.0, 0.8) for x, y in _fern_spots(ms.undergrowth())]
    name = ms.PIECES[piece]['edid']
    out = []
    if piece == 'undergrowth':
        out = under_items + under_ferns
    elif piece == 'thicket':
        out = [('shrub_tall_%s' % 'abc'[n],) + tuple(it[1:]) for n, it in enumerate(cap[name])]
        out += [('fern_small', x, y, k * 90.0, 0.9) for k, (x, y) in enumerate(_fern_spots(ms.thicket()))]
    else:
        for desc, x, y, yaw, size in cap[name]:
            f = _fingerprint(desc)
            if f == grass:
                out.append(('GRASS', x, y, yaw, size))
            elif f == under:
                c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
                for p, ux, uy, uyaw, usize in under_items + under_ferns:
                    out.append((p, x + (ux * c - uy * s) * size, y + (ux * s + uy * c) * size, yaw + uyaw, size * usize))
            elif f in known:
                out.append((known[f], x, y, yaw, size))
            else:
                raise ValueError('%s holds a plant plantsplit does not know' % piece)
    _layout[piece] = out
    return out


def _radius(piece, cache={}):
    if piece not in cache:
        import modelmake
        b = modelmake.make(ms.PIECES[piece]['describe']())['box']
        cache[piece] = max(abs(b[0]), abs(b[1]), abs(b[3]), abs(b[4]))
    return cache[piece]


HANG = 6.0                  # a plant whose lowest leaves anywhere round it are further than this over the ground hangs
REST = 1.0                  # and one let down is let down until they are this far over it
SECTORS = 12
LOW_PART = 10.0
_under = {}


def underside(piece):
    """A piece's lowest points all round it, from its own mesh: [(x, y, z)] one a sector (12 round its foot), each the
    lowest corner out past 40 in 100 of its spread that way. What hangs over a slope is these, not the foot."""
    if piece not in _under:
        import modelmake
        import nif
        made = modelmake.make(ms.PIECES[piece]['describe']())
        pts = [tuple(sh['p'][i:i + 3]) for sh in nif.mesh_from_nif(made['nif']) for i in range(0, len(sh['p']), 3)]
        far = max(math.hypot(x, y) for x, y, _z in pts) or 1.0
        low = {}
        for x, y, z in pts:
            d = math.hypot(x, y)
            if d < 0.4 * far:
                continue
            k = int((math.atan2(y, x) + math.pi) / math.tau * SECTORS) % SECTORS
            if k not in low or z < low[k][2]:
                low[k] = (x, y, z)
        _under[piece] = list(low.values())
    return _under[piece]


def hang(G, pts, p, s):
    """How far a thing's lowest points (underside(), in its own frame) are over the ground at most, placed at p, size s.
    Only points made to touch the ground count (LOW_PART or lower in its frame: fronds, grass, feet); a shrub's leaves
    stand over the ground on its stems, as they should."""
    import navgen
    R = navgen._turn(p[3], p[4], p[5])
    worst = -1e9
    for x, y, z in pts:
        if z > LOW_PART:
            continue
        wx = p[0] + s * (R[0][0] * x + R[0][1] * y + R[0][2] * z)
        wy = p[1] + s * (R[1][0] * x + R[1][1] * y + R[1][2] * z)
        wz = p[2] + s * (R[2][0] * x + R[2][1] * y + R[2][2] * z)
        g = G.at(wx, wy)
        if g is not None:
            worst = max(worst, wz - g)
    return worst if worst > -1e9 else 0.0


BURY_SHARE = 0.2            # a plant may be sunk into the ground by at most this share of its height...
BURY_LEAST = 4.0            # ...or this, whichever is more (the user, 20 Nov 2026: "now a bunch of them are buried into the dirt")
LEAN_MOST = 20.0            # degrees a plant may lean with the slope when standing upright would bury or hang it
SMALLER = (1.0, 0.75, 0.55)  # sizes tried, largest first, before a spot is left bare
LOW = ('fern_small', 'ground_fern') + tuple(GRASSES)   # what grows low along a bank: these lean further...
LEAN_LOW = 35.0
BURY_LOW = 0.3             # ...and may stand deeper in it
_top = {}


def _height(piece):
    if piece not in _top:
        import modelmake
        _top[piece] = modelmake.make(ms.PIECES[piece]['describe']())['box'][5]
    return _top[piece]


def seat(G, piece, x, y, rz, size):
    """A plant set ON the ground at (x, y) facing rz: its lowest points all round (underside, those made to touch the
    ground) at most REST over the ground, none sunk deeper than BURY_SHARE of its height (BURY_LEAST at least). Upright
    first; else leaning with the ground under it, up to LEAN_MOST; each at SMALLER sizes. (p, size) or None: nothing fits."""
    import navgen
    import roadbed
    pts = [q for q in underside(piece) if q[2] <= LOW_PART] + [(0.0, 0.0, 0.0)]
    R0 = navgen._turn(0.0, 0.0, rz)
    dx, dy = R0[0][0], R0[1][0]
    for sc in (size * k for k in SMALLER):
        # the ground under each point (placed upright: near enough for where a lean moves them)
        under = []
        for px, py, _pz in pts:
            wx, wy = x + sc * (R0[0][0] * px + R0[0][1] * py), y + sc * (R0[1][0] * px + R0[1][1] * py)
            g = G.at(wx, wy)
            if g is None:
                return None
            under.append((sc * px, sc * py, g))
        # the plane of that ground, in the plant's own frame (along its facing, across)
        n = float(len(under))
        mx, my, mz = (sum(q[i] for q in under) / n for i in range(3))
        sxx = sum((q[0] - mx) ** 2 for q in under); syy = sum((q[1] - my) ** 2 for q in under)
        sxy = sum((q[0] - mx) * (q[1] - my) for q in under)
        sxz = sum((q[0] - mx) * (q[2] - mz) for q in under); syz = sum((q[1] - my) * (q[2] - mz) for q in under)
        det = sxx * syy - sxy * sxy
        b = c = 0.0
        if abs(det) > 1e-6:
            b, c = (sxz * syy - syz * sxy) / det, (syz * sxx - sxz * sxy) / det
        steep = math.hypot(b, c)
        leans = [0.0]
        if steep > 1e-4:
            most = math.tan(math.radians(LEAN_LOW if piece in LOW else LEAN_MOST))
            leans += [min(1.0, most / steep) * f for f in (0.5, 1.0)]
        allow = max(BURY_LEAST, (BURY_LOW if piece in LOW else BURY_SHARE) * _height(piece) * sc)
        flat = [sc * pz - SINK * sc for _px, _py, pz in pts]     # (each point's height over flat ground, placed as made)
        for f in leans:
            rx, ry, rr = roadbed._turn_plane(dx, dy, b * f, c * f) if f else (0.0, 0.0, rz)
            R = navgen._turn(rx, ry, rr)
            offs = [sc * (R[2][0] * px + R[2][1] * py + R[2][2] * pz) for px, py, pz in pts]
            if f:                                   # (leaning moves each point: the ground under where it is now)
                under = []
                for px, py, pz in pts:
                    g = G.at(x + sc * (R[0][0] * px + R[0][1] * py + R[0][2] * pz), y + sc * (R[1][0] * px + R[1][1] * py + R[1][2] * pz))
                    if g is None:
                        return None
                    under.append((0.0, 0.0, g))
            # (judged against how it sits on flat ground: the point whose ground falls away most sits as it would on flat
            # ground, so nothing hangs; the rest are as much deeper as their ground is higher, which may not be more than
            # the plant can stand)
            need = [g - o + d for o, (_a, _b, g), d in zip(offs, under, flat)]
            z0 = min(need)
            if max(need) - z0 <= allow:
                return [round(x, 1), round(y, 1), round(z0, 1), round(rx, 4), round(ry, 4), round(rr, 4)], round(sc, 3)
    return None


def seat_some(G, piece, x, y, rz, size):
    """seat(), and where this plant can't stand, the grass of the spot, then any grass: (piece, p, size) or None. A spot
    a plant was meant for is not left bare where a grass would stand (the user, 20 Nov 2026: "back to barren dirt")."""
    tries = [piece]
    if piece not in GRASSES:
        tries.append(grass_at(x, y))
    tries += [g for g in GRASS_KEYS if g not in tries]
    for k, pc in enumerate(tries):
        got = seat(G, pc, x, y, rz, size if k == 0 else max(0.8, min(1.8, size)))
        if got:
            return pc, got[0], got[1]
    return None


def grass_at(x, y):
    """The grass for a spot: by where it is, so the same tuft seldom stands beside itself."""
    return GRASS_KEYS[zlib.crc32(b'%d,%d' % (int(x // 37), int(y // 37))) % len(GRASS_KEYS)]


def fit(G, p, s, plants):
    """The plane of ground under a clump's plants: (b, c, a, worst) in the clump's own frame (z = a + b*along + c*across,
    worst: the furthest a foot is off it), or None where ground is missing."""
    import navgen
    R = navgen._turn(0.0, 0.0, p[5])
    pts = []
    for _piece, x, y, _yaw, _size in plants:
        X, Y = s * x, s * y
        g = G.at(p[0] + R[0][0] * X + R[0][1] * Y, p[1] + R[1][0] * X + R[1][1] * Y)
        if g is None:
            return None
        pts.append((X, Y, g))
    n = float(len(pts))
    mx, my, mz = (sum(q[i] for q in pts) / n for i in range(3))
    sxx = sum((q[0] - mx) ** 2 for q in pts); syy = sum((q[1] - my) ** 2 for q in pts)
    sxy = sum((q[0] - mx) * (q[1] - my) for q in pts)
    sxz = sum((q[0] - mx) * (q[2] - mz) for q in pts); syz = sum((q[1] - my) * (q[2] - mz) for q in pts)
    det = sxx * syy - sxy * sxy
    if abs(det) < 1e-6:
        return None
    b = (sxz * syy - syz * sxy) / det
    c = (syz * sxx - sxz * sxy) / det
    a = mz - b * mx - c * my
    worst = max(abs(q[2] - (a + b * q[0] + c * q[1])) for q in pts)
    return b, c, a, worst


def split(gd, pr, world, cat=None, only=None, progress=None):
    """The ops that take every clump of `world` apart (only: cells (x, y) to do, else all): (ops, report). The ops start
    with the records of the pieces the mod hasn't yet (modelsets.put), then a remove for each clump and an add for each
    plant, for one apply (one Undo)."""
    import landmarks
    import navgen
    import osmdress
    import roadgen
    import understory
    grid = gd.grid(world)
    keys = {gd.key(c) for c in grid.values()}
    clump_of = {}
    for piece in CLUMPS:
        k = ms.record_of(pr, piece)
        if k:
            clump_of[k] = piece
    want = None if only is None else {tuple(c) for c in only}
    cell_xy = {gd.key(c): xy for xy, c in grid.items()}
    first, base_of = [], {}
    for piece in sorted(set(SINGLES) | {'ground_fern', 'taro', 'ti_red', 'ti_green', 'heliconia'}):
        k = ms.record_of(pr, piece)
        if not k:
            ops, info = ms.put(pr, piece)
            first += ops
            k = info['key'] or '$model_' + piece
        base_of[piece] = k
    on_road = understory._roads(gd, pr, world, keys)
    if cat is None:
        import townbuild
        import server
        cat = townbuild.load(gd, server.kits_folder())
    built = osmdress._Stands(osmdress.standing(gd, pr, world, cat), margin=understory.NEAR_BUILT)
    in_mark = understory._in_boxes(list(landmarks.standing(gd, pr, world)) + list(ms.footprints(pr, gd, world)))
    G = roadgen.Ground(gd, pr, world)
    import roadbed
    removes, adds, kept = [], [], []
    why = {'sea': 0, 'road': 0, 'built': 0, 'steep': 0, 'off the world': 0}
    by = {}
    todo = [(ck, rk, r) for ck in keys if want is None or tuple(cell_xy.get(ck, ())) in want
            for rk, r in pr.cells.get(ck, {}).get('refs', {}).items() if r.get('base') in clump_of and r.get('p') and not r.get('removed')]
    for n, (ck, rk, r) in enumerate(todo):
        if progress and n % 2000 == 0:
            progress('Taking the clumps apart', n, len(todo))
        p, s = r['p'], float(r.get('s') or 1.0)
        R = navgen._turn(0.0, 0.0, p[5])           # (as the game turns a thing about z)
        plants = layout(clump_of[r['base']])
        f = fit(G, p, s, plants)
        if f and f[3] <= KEEP_FIT and math.degrees(math.atan(math.hypot(f[0], f[1]))) <= KEEP_TILT:
            rx, ry, rz = roadbed._turn_plane(R[0][0], R[1][0], f[0], f[1])
            q = [p[0], p[1], f[2] - SINK * s, rx, ry, rz]
            if hang(G, underside(clump_of[r['base']]), q, s) <= HANG:
                kept.append({'op': 'move', 'cell': ck, 'ref': rk, 's': s,
                         'p': [p[0], p[1], round(f[2] - SINK * s, 1), round(rx, 4), round(ry, 4), round(rz, 4)]})
                continue
        removes.append({'op': 'remove', 'cell': ck, 'ref': rk})
        for piece, x, y, yaw, size in plants:
            fx, fy = p[0] + s * (R[0][0] * x + R[0][1] * y), p[1] + s * (R[1][0] * x + R[1][1] * y)
            if piece == 'GRASS':
                piece = grass_at(fx, fy)
            if piece in THIN:
                one_in, grow = THIN[piece]
                if zlib.crc32(b'%s %d %d' % (rk.encode(), int(x), int(y))) % 1000 >= 1000 / one_in:
                    why['thinned'] = why.get('thinned', 0) + 1
                    continue
                size *= grow
            g = G.at(fx, fy)
            xy = (int(fx // 4096), int(fy // 4096))
            if g is None or xy not in grid:
                why['off the world'] += 1
                continue
            if g < 8:
                why['sea'] += 1
                continue
            if on_road(fx, fy):
                why['road'] += 1
                continue
            if built.hit(fx, fy) or in_mark(fx, fy):
                why['built'] += 1
                continue
            sc = s * size
            rad = _radius(piece) * sc
            around = [G.at(fx + dx, fy + dy) for dx, dy in ((rad, 0), (-rad, 0), (0, rad), (0, -rad))]
            around = [a for a in around if a is not None]
            low = min(around) if around else g
            grade = max((abs(a - g) for a in around), default=0.0) / max(rad, 1.0)
            rz = (p[5] + math.radians(yaw)) % math.tau
            got = seat_some(G, piece, fx, fy, rz, sc)
            if got is None:
                why['nothing stands'] = why.get('nothing stands', 0) + 1
                continue
            piece = got[0]
            adds.append({'op': 'add', 'cell': gd.key(grid[xy]), 'base': base_of[piece], 's': got[2], 'p': got[1]})
            by[piece] = by.get(piece, 0) + 1
    return first + kept + removes + adds, {'kept whole': len(kept), 'clumps': len(removes), 'plants': len(adds), 'left out': why, 'by': by, 'records': len(first)}


def feet(gd, pr, world, keys=None, near=None):
    """Every one of the mod's own plants against the land under its foot: {band: count}, and the worst [(over, key, p)].
    keys: the bases to look at (default: every single plant piece); near: (x, y, r) to look only there."""
    import roadgen
    G = roadgen.Ground(gd, pr, world)
    if keys is None:
        keys = {ms.record_of(pr, p) for p in set(SINGLES) | {'ground_fern', 'taro', 'ti_red', 'ti_green', 'heliconia'}} - {None}
    bands, worst = {'buried or on': 0, '0-4': 0, '4-8': 0, '8+': 0}, []
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            p = r.get('p')
            if not p or r.get('removed') or r.get('base') not in keys:
                continue
            if near and math.hypot(p[0] - near[0], p[1] - near[1]) > near[2]:
                continue
            g = G.at(p[0], p[1])
            if g is None:
                continue
            over = p[2] - g
            bands['buried or on' if over <= 0 else '0-4' if over <= 4 else '4-8' if over <= 8 else '8+'] += 1
            if over > 4:
                worst.append((round(over, 1), rk, p))
    worst.sort(reverse=True)
    return bands, worst[:30]


LYING = ('mossy_log',)


def _facing(p):
    """The way a turned thing faces, about z (its local x across the ground)."""
    import navgen
    R = navgen._turn(p[3], p[4], p[5])
    return (-math.atan2(R[1][0], R[0][0])) % math.tau


def settle(gd, pr, world, only=None, skip=()):
    """Every other plant of FOLab's own sets in `world` (ferns, taro, ti, palms, shrubs: whatever was planted one at a time)
    set on the ground again (`seat`: nothing hanging, nothing buried past what it can stand); one that fits nowhere
    there is taken out. only: cells (x, y); skip: refs left as they are (what `split` just made). (ops, report)."""
    import roadgen
    G = roadgen.Ground(gd, pr, world)
    grid = gd.grid(world)
    want = None if only is None else {tuple(c) for c in only}
    piece_of = {}
    for piece, what in ms.PIECES.items():
        if what.get('set') in ('jungle', 'beach') and piece not in CLUMPS:
            k = ms.record_of(pr, piece)
            if k:
                piece_of[k] = piece
    ops, rep = [], {'looked at': 0, 'seated': 0, 'taken out': 0}
    for xy, c in grid.items():
        if want is not None and tuple(xy) not in want:
            continue
        ck = gd.key(c)
        for rk, r in pr.cells.get(ck, {}).get('refs', {}).items():
            piece = piece_of.get(r.get('base'))
            p = r.get('p')
            if not piece or not p or r.get('removed') or rk in skip:
                continue
            rep['looked at'] += 1
            s = float(r.get('s') or 1.0)
            if tuple(p[3:5]) != (0.0, 0.0) and piece in LYING:
                continue                                # (a log lies along the ground by its own placing)
            got = seat_some(G, piece, p[0], p[1], p[5] if not any(p[3:5]) else _facing(p), s)
            if got is None:
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                rep['taken out'] += 1
            elif got[0] != piece:
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                ops.append({'op': 'add', 'cell': ck, 'base': ms.record_of(pr, got[0]) or '$model_' + got[0], 's': got[2], 'p': got[1]})
                rep['grass instead'] = rep.get('grass instead', 0) + 1
            elif any(abs(a - b) > 0.5 for a, b in zip(got[1][:3], p[:3])) or got[2] != round(s, 3) or any(abs(a - b) > 0.01 for a, b in zip(got[1][3:], p[3:])):
                ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': got[1], 's': got[2]})
                rep['seated'] += 1
    return ops, rep


def judge(G, piece, p, s):
    """A placed plant against the ground, as seat() judges one: (hangs by, buried by, may be buried by). Hangs: how much
    higher its point the ground falls away under most is than on flat ground; buried: how much deeper its deepest is."""
    import navgen
    pts = [q for q in underside(piece) if q[2] <= LOW_PART] + [(0.0, 0.0, 0.0)]
    R = navgen._turn(p[3], p[4], p[5])
    need = []
    for px, py, pz in pts:
        g = G.at(p[0] + s * (R[0][0] * px + R[0][1] * py + R[0][2] * pz), p[1] + s * (R[1][0] * px + R[1][1] * py + R[1][2] * pz))
        if g is None:
            continue
        o = s * (R[2][0] * px + R[2][1] * py + R[2][2] * pz)
        need.append(g - o + s * (pz - SINK))
    if not need:
        return 0.0, 0.0, 1.0
    allow = max(BURY_LEAST, (BURY_LOW if piece in LOW else BURY_SHARE) * _height(piece) * s)
    return p[2] - min(need), max(need) - p[2], allow


# what a cell's placed plants may draw (a shape a draw): round a spot the game holds 5 x 5 cells, and its own busiest
# places draw about 2,000 in all (Freeside's gate 2,196, Novac 1,403); Waikiki's start drew 12,693, FOLab's plants
# 9,990 of them (20 Nov 2026). The jungle's shape first, then the low green, spaced evenly, where the game's own grass
# doesn't grow first.
SHAPE = ('taro', 'ti_red', 'ti_green', 'heliconia', 'shrub_tall_a', 'shrub_tall_b', 'shrub_tall_c', 'hibiscus', 'banana',
         'tree_fern', 'jungle_tree', 'jungle_banyan', 'jungle_tall', 'palm_tall', 'palm_young', 'bamboo', 'mossy_log',
         'jungle_tree_b', 'jungle_tree_c', 'jungle_banyan_b', 'jungle_banyan_c', 'jungle_tall_b', 'jungle_tall_c')
LOW_GREEN = ('shrub_low_a', 'shrub_low_b', 'ground_fern', 'fern_small', 'taro_small') + tuple(GRASSES)
BUDGET = {'shape': 24, 'low': 36}       # draws a cell, for each


def budget(gd, pr, world, cells, green=frozenset(), shapes_of=None):
    """Remove ops keeping each cell's FOLab plants within BUDGET draws: (ops, report). green: land points (x, y in
    128-unit steps) where the game's grass grows: low plants there go before those elsewhere. shapes_of: piece -> draws."""
    import random
    grid = gd.grid(world)
    want = {tuple(c) for c in cells}
    piece_of = {}
    for piece in set(SHAPE) | set(LOW_GREEN):
        if piece in ms.PIECES:
            k = ms.record_of(pr, piece)
            if k:
                piece_of[k] = piece
    shapes_of = shapes_of or (lambda p: 1)
    ops, rep = [], {'kept': 0, 'taken out': 0}
    for xy, c in grid.items():
        if tuple(xy) not in want:
            continue
        ck = gd.key(c)
        refs = [(rk, r, piece_of[r['base']]) for rk, r in pr.cells.get(ck, {}).get('refs', {}).items()
                if r.get('base') in piece_of and r.get('p') and not r.get('removed')]
        for group, cap in (('shape', BUDGET['shape']), ('low', BUDGET['low'])):
            mine = [t for t in refs if (t[2] in SHAPE) == (group == 'shape')]
            rnd = random.Random(hash(ck) & 0xFFFF)
            # (spaced evenly: each next kept one the farthest from those kept, the bare ground's first)
            if group == 'low':
                mine.sort(key=lambda t: ((round(t[1]['p'][0] / 128), round(t[1]['p'][1] / 128)) in green, rnd.random()))
            else:
                rnd.shuffle(mine)
            kept, used = [], 0
            left = list(mine)
            while left and used < cap:
                if kept:
                    best = max(left, key=lambda t: min((t[1]['p'][0] - k[1]['p'][0]) ** 2 + (t[1]['p'][1] - k[1]['p'][1]) ** 2 for k in kept)
                               - (1e9 if group == 'low' and (round(t[1]['p'][0] / 128), round(t[1]['p'][1] / 128)) in green else 0))
                else:
                    best = left[0]
                left.remove(best)
                kept.append(best)
                used += shapes_of(best[2])
            for rk, _r, _p in left:
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
            rep['kept'] += len(kept)
            rep['taken out'] += len(left)
    return ops, rep


BUDGET_CITY = {'shape': 32, 'low': 48}  # (a third over the start's: "the foliage is a little thin", 20 Nov 2026)


def rework(gd, pr, world, cells, green=frozenset(), grown=(), budget_of=None, progress=None):
    """The whole of a stretch's FOLab plants in one pass, the way the start was done: every clump's plants and every plant
    placed one at a time are candidates where their feet are; those the ground grows itself (grown: pieces, on `green`
    land points) are left to it; each cell keeps its jungle-shaping plants and then its low green within a draw budget
    (budget_of: {'shape', 'low'}), spaced evenly; only those kept are seated (seat_some: on the ground, neither hanging nor
    buried; a grass where the plant can't stand). Ops: the clumps and what isn't kept out, the kept ones moved or added."""
    import random
    import landmarks
    import navgen
    import osmdress
    import roadgen
    import understory
    import modelmake
    budget_of = budget_of or BUDGET_CITY
    grid = gd.grid(world)
    want = {tuple(c) for c in cells}
    keys = {gd.key(c) for c in grid.values()}
    clump_of, own_of = {}, {}
    for piece in CLUMPS:
        k = ms.record_of(pr, piece)
        if k:
            clump_of[k] = piece
    for piece in set(SHAPE) | set(LOW_GREEN):
        if piece in ms.PIECES:
            k = ms.record_of(pr, piece)
            if k:
                own_of[k] = piece
    first, base_of = [], {}
    for piece in sorted(set(SHAPE) | set(LOW_GREEN)):
        if piece not in ms.PIECES:
            continue
        k = ms.record_of(pr, piece)
        if not k:
            ops, info = ms.put(pr, piece)
            first += ops
            k = info['key'] or '$model_' + piece
        base_of[piece] = k
    draws = {}

    def shapes_of(p):
        if p not in draws:
            try:
                draws[p] = len(modelmake.make(ms.PIECES[p]['describe']())['shapes'])
            except Exception:
                draws[p] = 2
        return draws[p]
    on_road = understory._roads(gd, pr, world, keys)
    import server
    import townbuild
    built = osmdress._Stands(osmdress.standing(gd, pr, world, townbuild.load(gd, server.kits_folder())), margin=understory.NEAR_BUILT)
    in_mark = understory._in_boxes(list(landmarks.standing(gd, pr, world)) + list(ms.footprints(pr, gd, world)))
    G = roadgen.Ground(gd, pr, world)
    grown = set(grown)
    # the candidates, by the cell their foot is in
    by_cell = {}
    removes = []
    rep = {'clumps taken apart': 0, 'grown by the ground': 0, 'kept': 0, 'taken out': 0, 'no room (road, building, sea)': 0, 'nothing stands': 0}
    for xy in want:
        c = grid.get(xy)
        if c is None:
            continue
        ck = gd.key(c)
        for rk, r in pr.cells.get(ck, {}).get('refs', {}).items():
            p = r.get('p')
            if not p or r.get('removed'):
                continue
            if r.get('base') in clump_of:
                removes.append({'op': 'remove', 'cell': ck, 'ref': rk})
                rep['clumps taken apart'] += 1
                s = float(r.get('s') or 1.0)
                R = navgen._turn(0.0, 0.0, p[5])
                for piece, x, y, yaw, size in layout(clump_of[r['base']]):
                    fx, fy = p[0] + s * (R[0][0] * x + R[0][1] * y), p[1] + s * (R[1][0] * x + R[1][1] * y)
                    if piece == 'GRASS':
                        piece = grass_at(fx, fy)
                    by_cell.setdefault((int(fx // 4096), int(fy // 4096)), []).append(
                        (piece, fx, fy, (p[5] + math.radians(yaw)) % math.tau, s * size, None))
            elif r.get('base') in own_of:
                piece = own_of[r['base']]
                rz = p[5] if not any(p[3:5]) else _facing(p)
                by_cell.setdefault(xy, []).append((piece, p[0], p[1], rz, float(r.get('s') or 1.0), (ck, rk, p)))
    adds, moves = [], []
    for n, (xy, cands) in enumerate(by_cell.items()):
        if progress and n % 100 == 0:
            progress('The plants, cell by cell', n, len(by_cell))
        c = grid.get(xy)
        if c is None or xy not in want:
            for t in cands:
                if t[5]:
                    removes.append({'op': 'remove', 'cell': t[5][0], 'ref': t[5][1]})
            continue
        ck = gd.key(c)
        ok = []
        for t in cands:
            piece, fx, fy = t[0], t[1], t[2]
            if piece in grown and (round(fx / 128), round(fy / 128)) in green:
                rep['grown by the ground'] += 1
            elif on_road(fx, fy) or built.hit(fx, fy) or in_mark(fx, fy) or (G.at(fx, fy) or 0) < 8:
                rep['no room (road, building, sea)'] += 1
            else:
                ok.append(t)
                continue
            if t[5]:
                removes.append({'op': 'remove', 'cell': t[5][0], 'ref': t[5][1]})
        rnd = random.Random(zlib.crc32(ck.encode()))
        for group in ('shape', 'low'):
            mine = [t for t in ok if (t[0] in SHAPE) == (group == 'shape')]
            rnd.shuffle(mine)
            kept, used, left = [], 0, list(mine)
            while left and used < budget_of[group]:
                best = left[0] if not kept else max(left, key=lambda t: min((t[1] - k[1]) ** 2 + (t[2] - k[2]) ** 2 for k in kept))
                left.remove(best)
                if best[0] in LYING and best[5]:            # (a log lies along the ground by its own placing)
                    kept.append(best)
                    used += shapes_of(best[0])
                    continue
                got = seat_some(G, best[0], best[1], best[2], best[3], best[4])
                if got is None:
                    rep['nothing stands'] += 1
                    if best[5]:
                        removes.append({'op': 'remove', 'cell': best[5][0], 'ref': best[5][1]})
                    continue
                kept.append(best)
                used += shapes_of(got[0])
                if best[5] and got[0] == best[0]:
                    moves.append({'op': 'move', 'cell': best[5][0], 'ref': best[5][1], 'p': got[1], 's': got[2]})
                else:
                    if best[5]:
                        removes.append({'op': 'remove', 'cell': best[5][0], 'ref': best[5][1]})
                    adds.append({'op': 'add', 'cell': ck, 'base': base_of[got[0]], 's': got[2], 'p': got[1]})
            for t in left:
                if t[5]:
                    removes.append({'op': 'remove', 'cell': t[5][0], 'ref': t[5][1]})
            rep['kept'] += len(kept)
            rep['taken out'] += len(left)
    return first + removes + moves + adds, rep
