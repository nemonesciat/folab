"""Roads that lie in the ground, as the game's do.

Measured over the Mojave's 672 long road pieces: a piece is a slab, its top at its origin (a crown of 10 to 14 over it)
and its sides going 25 under. The game stands it with its origin about 14 over the land (the median), so the slab is sunk
11 into the ground all round; 98 in 100 lie dead level side to side, and the land was shaped by hand up to each one. A
piece with a point more than 32 over the land is 1 in 20 there.

A road laid by rule is bedded once (roadgen.settled), and then plots are levelled, the coast cut and sharp ground eased
round it, each moving the land a little: on a map-made city 37 pieces in 100 ended with a point more than 32 over the
ground, their sides showing. So this is done last, after all of that:

  1. each piece is laid again on the ground as it now is: its middle, its slope along the road and (only where the
     ground really leans: a street meeting one that climbs) its lean fitted to the land under its whole footprint, its
     origin SUNK over that;
  2. the land under and just round every piece is brought to that piece's own plane (the lower one where two cross), and
     eased back to its own height over FADE beyond; ground under buildings stays as it is;
  3. whatever else stands on ground that moved goes with it.

Returns ops (the pieces' moves, the cells' land, the other moves)."""
import math

import navgen
import roadgen

POINT = 128.0
SUNK = 12.0             # a piece's origin over the ground under it (the game: 14; land goes in steps of 8, so 8 to 16 here)
FLAT = 150.0            # the land this far outside a piece's edge lies on its plane too (a land point is 128 from the next)
FADE = 420.0            # and comes back to its own height over this much more
STEEPEST = 0.3          # the most a piece slopes along the road
LEAN = 0.16             # and side to side: where a street meets one that climbs, or runs along a hillside
HOLD = 96.0             # round a building's box, ground that stays (as landsoft)
SEAT = 2.0
ROUNDS = 5              # pieces laid, land brought to them, and again: pieces that share ground come to agree


def _flat_bases(gd):
    """{key: its box} of the road pieces this lays."""
    import townbuild
    out = {}
    for key in roadgen.pieces(gd).values():
        b = townbuild.obnd(gd, key)
        if b:
            out[key] = b
    return out


def _turn_plane(dx, dy, b, c):
    """The rotation laying a piece's +x along (dx, dy) rising b a unit, its +y rising c a unit (as roadgen.turn_along, with a lean)."""
    f = (dx, dy, b)
    s = (-dy, dx, c)
    u = (f[1] * s[2] - f[2] * s[1], f[2] * s[0] - f[0] * s[2], f[0] * s[1] - f[1] * s[0])
    n = math.sqrt(sum(v * v for v in u)) or 1.0
    u = tuple(v / n for v in u)
    n = math.sqrt(sum(v * v for v in f)) or 1.0
    f = tuple(v / n for v in f)
    s = (u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0])
    ry = -math.asin(max(-1.0, min(1.0, u[0])))
    rz = -math.atan2(-s[0], f[0])
    rx = -math.atan2(-u[1], u[2])
    return rx, ry, rz


def _fit(pts):
    """z = a + b x + c y through (x, y, z) points, by least squares."""
    n = len(pts)
    mx, my, mz = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    sxz = sum((p[0] - mx) * (p[2] - mz) for p in pts)
    syz = sum((p[1] - my) * (p[2] - mz) for p in pts)
    det = sxx * syy - sxy * sxy
    if abs(det) < 1e-6:
        b, c = (sxz / sxx if sxx else 0.0), 0.0
    else:
        b, c = (sxz * syy - syz * sxy) / det, (syz * sxx - sxz * sxy) / det
    return mx, my, mz, b, c


def bed(gd, pr, world, keep=(), progress=None):
    """(ops, report). keep: [(x, y, turn, x0, y0, x1, y1)], buildings and landmarks whose ground is not to move."""
    import land
    import osmplace
    grid = gd.grid(world)
    boxes = _flat_bases(gd)
    before = roadgen.Ground(gd, pr, world)
    g = roadgen.Ground(gd, pr, world)            # (the ground as it is being made: its cells copied as they change)
    inside = {gd.key(c): k for k, c in grid.items()}
    found = []                                   # [cell key, ref key, ref, x, y, dx, dy, box, (a, b, c)]
    for ck, c in pr.cells.items():
        if ck not in inside:
            continue
        for rk, r in c['refs'].items():
            if rk.startswith('+') and not r.get('removed') and r.get('base') in boxes and r.get('p'):
                p = r['p']
                R = navgen._turn(p[3], p[4], p[5])
                dx, dy = R[0][0], R[1][0]
                ln = math.hypot(dx, dy) or 1.0
                found.append([ck, rk, r, p[0], p[1], dx / ln, dy / ln, boxes[r['base']], None])
    if not found:
        return [], {'pieces': 0, 'relaid': 0, 'points': 0, 'cells': 0, 'reseated': 0}
    held = set()
    for kx, ky, rz, bx0, by0, bx1, by1 in keep:
        c, sn = math.cos(rz), math.sin(rz)
        rad = math.hypot(max(abs(bx0), abs(bx1)), max(abs(by0), abs(by1))) + HOLD
        for gy in range(int((ky - rad) // POINT), int((ky + rad) // POINT) + 2):
            for gx in range(int((kx - rad) // POINT), int((kx + rad) // POINT) + 2):
                ddx, ddy = gx * POINT - kx, gy * POINT - ky
                lx, ly = ddx * c - ddy * sn, ddx * sn + ddy * c
                if bx0 - HOLD <= lx <= bx1 + HOLD and by0 - HOLD <= ly <= by1 + HOLD:
                    held.add((gx, gy))
    changed = set()

    def fit_all():
        for f in found:
            _ck, _rk, _r, x, y, dx, dy, box, _was = f
            pts = []
            for lx in [box[0] + (box[3] - box[0]) * t for t in (0.03, 0.26, 0.5, 0.74, 0.97)]:
                for ly in (box[1] * 0.92, 0.0, box[4] * 0.92):
                    z = g.at(x + dx * lx - dy * ly, y + dy * lx + dx * ly)
                    if z is not None:
                        pts.append((lx, ly, z))
            if len(pts) < 6:
                f[8] = None
                continue
            mx, my, mz, b, c = _fit(pts)
            b = max(-STEEPEST, min(STEEPEST, b))
            c = max(-LEAN, min(LEAN, c)) if abs(c) > 0.02 else 0.0     # (level unless the ground really leans)
            f[8] = (mz - b * mx - c * my, b, c)

    def homes_of(gx, gy):
        # (a point on a cell's edge is in two cells, at a corner four)
        out = []
        for cx in {gx // 32, (gx - 1) // 32}:
            for cy in {gy // 32, (gy - 1) // 32}:
                col, row = gx - cx * 32, gy - cy * 32
                if 0 <= col <= 32 and 0 <= row <= 32 and g.cell((cx, cy)):
                    out.append(((cx, cy), row * 33 + col))
        return out

    reach = FLAT + FADE
    moved = set()
    for turn in range(ROUNDS):
        if progress:
            progress('Laying the roads in the ground', turn, ROUNDS)
        fit_all()
        # the land to the pieces' planes: under a piece (and FLAT round it) its plane, the mean where pieces share the
        # ground, so that laid again they come to agree; beyond, the nearest piece's, fading
        under, near = {}, {}
        for _ck, _rk, _r, x, y, dx, dy, box, plane in found:
            if plane is None:
                continue
            a, b, c = plane
            rad = math.hypot(max(abs(box[0]), abs(box[3])), max(abs(box[1]), abs(box[4]))) + reach
            for gy in range(int(math.ceil((y - rad) / POINT)), int((y + rad) // POINT) + 1):
                for gx in range(int(math.ceil((x - rad) / POINT)), int((x + rad) // POINT) + 1):
                    ddx, ddy = gx * POINT - x, gy * POINT - y
                    lx, ly = ddx * dx + ddy * dy, -ddx * dy + ddy * dx
                    ox = box[0] - lx if lx < box[0] else lx - box[3] if lx > box[3] else 0.0
                    oy = box[1] - ly if ly < box[1] else ly - box[4] if ly > box[4] else 0.0
                    d = math.hypot(ox, oy)
                    if d >= reach:
                        continue
                    want = a + b * max(box[0], min(box[3], lx)) + c * max(box[1], min(box[4], ly))
                    if d <= FLAT:
                        u = under.get((gx, gy))
                        if u is None:
                            under[(gx, gy)] = [want, 1]
                        else:
                            u[0] += want
                            u[1] += 1
                    else:
                        was = near.get((gx, gy))
                        if was is None or d < was[0]:
                            near[(gx, gy)] = (d - FLAT, want)
        for pt in set(under) | set(near):
            if pt in held:
                continue
            homes = homes_of(*pt)
            if not homes:
                continue
            now = g.h[homes[0][0]][homes[0][1]]
            if now < 0:
                continue                        # (the sea bed is the coast's)
            if pt in under:
                s, n = under[pt]
                new = round(s / n / 8.0) * 8.0   # (to the nearest step, not the one below: done again, nothing drifts down)
            else:
                d, want = near[pt]
                wgt = 1.0 - d / FADE
                wgt = wgt * wgt * (3 - 2 * wgt)
                new = round((now + (want - now) * wgt) / 8.0) * 8.0
            if now >= 8.0 > new:
                new = 8.0                       # (land stays land)
            if abs(new - now) < 0.5:
                continue
            moved.add(pt)
            for k, i in homes:
                if k not in changed:
                    g.h[k] = list(g.h[k])
                    changed.add(k)
                g.h[k][i] = new
    fit_all()
    # the pieces where they now belong; ones that lie over each other a hair apart (they'd flicker)
    fake, who = [], []
    for ck, rk, r, x, y, dx, dy, _box, plane in found:
        if plane is None:
            continue
        a, b, c = plane
        fake.append({'op': 'add', 'base': r['base'], 'p': [x, y, round(a + SUNK, 2)] + [round(v, 4) for v in _turn_plane(dx, dy, b, c)]})
        who.append((ck, rk, r))
    osmplace.apart(gd, fake)
    ops, relaid, mine = [], 0, set()
    for f, (ck, rk, r) in zip(fake, who):
        mine.add((ck, rk))
        if any(abs(u - v) > (0.5 if i == 2 else 0.002) for i, (u, v) in enumerate(zip(f['p'], r['p']))):
            ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': f['p']})
            relaid += 1
    cells = 0
    cache = {}
    for k in sorted(changed):
        h0 = before.cell(k)
        if all(abs(u - v) < 0.5 for u, v in zip(h0, g.h[k])):
            continue
        ck = gd.key(grid[k])
        was = pr.land.get(ck)
        form = dict(was) if was else roadgen._plain_land(land.decode(gd, gd.land_at(world, *k), cache))
        ops.append({'op': 'land', 'cell': ck, 'land': dict(form, h=[float(v) for v in g.h[k]])})
        cells += 1
    # what else stands on ground that moved
    reseated = 0
    for ck, c in pr.cells.items():
        k = inside.get(ck)
        if k is None or not any((k[0] + i, k[1] + j) in changed for i in (-1, 0, 1) for j in (-1, 0, 1)):
            continue
        for rk, r in c['refs'].items():
            p = r.get('p')
            if not rk.startswith('+') or not p or r.get('removed') or (ck, rk) in mine:
                continue
            z0, z1 = before.at(p[0], p[1]), g.at(p[0], p[1])
            if z0 is None or z1 is None or abs(z1 - z0) < SEAT:
                continue
            ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [p[0], p[1], round(p[2] + z1 - z0, 1)] + list(p[3:])})
            reseated += 1
    return ops, {'pieces': len(found), 'relaid': relaid, 'points': len(moved), 'cells': cells, 'reseated': reseated}


def gaps(gd, pr, world):
    """How the mod's road pieces lie: [(highest point over the land, lowest)] a piece, its origin's plane against the ground
    at fifteen spots of its footprint. For checks."""
    boxes = _flat_bases(gd)
    g = roadgen.Ground(gd, pr, world)
    out = []
    for c in pr.cells.values():
        for rk, r in c['refs'].items():
            if r.get('removed') or r.get('base') not in boxes or not r.get('p'):
                continue
            p, box = r['p'], boxes[r['base']]
            R = navgen._turn(p[3], p[4], p[5])
            v = []
            for lx in [box[0] + (box[3] - box[0]) * t for t in (0.03, 0.26, 0.5, 0.74, 0.97)]:
                for ly in (box[1] * 0.92, 0.0, box[4] * 0.92):
                    z = g.at(p[0] + R[0][0] * lx + R[0][1] * ly, p[1] + R[1][0] * lx + R[1][1] * ly)
                    if z is not None:
                        v.append(p[2] + R[2][0] * lx + R[2][1] * ly - z)
            if v:
                out.append((max(v), min(v)))
    return out
