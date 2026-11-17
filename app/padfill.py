"""Ground brought up to the buildings that stand on it: no daylight under a wall, no foundation hanging over a slope.

A building is stood level at its plot's height (townbuild), and the land under it is whatever the map and the later
shaping left: on a slope its downhill side, and at many plots' edges a corner, stands over air (measured on the
Koko Head world: 414 of 3,150 buildings had more than 32 units of daylight somewhere under them, 3 over 160). The game
never shows that: its own buildings stand on ground made to meet them, the ground a little into their footing.

Here every land point under a building's footprint (and HOLD round it) is raised to the building's own ground (`MEET`
under its middle's: how far the game sinks the kind, the catalogue's `mid`, never above its underside plus `SINK_MOST`),
then the ground round it eased down to meet the land as it was, no step steeper than `SLOPE` a point, the way a bank is
made. Land is only ever raised here, never lowered: nothing that stands is undermined. Things of the mod's lying on
ground that rose (rubble, wrecks, plants, slabs; within `ON_GROUND` of it) are lifted with it; buildings and what
stands on them (doors, roofs' camps) keep their heights. Returns (ops, report): the cells' land, then the moves."""
import heapq
import math

POINT = 128.0
PER_CELL = 32
STEP = 8.0              # (land heights are whole steps of this in the plugin)
HOLD = 64.0             # past a building's box, ground raised to it too (a wall's footing, a doorstep)
MEET = 8.0              # under its middle's ground, at the most: so a floor's edge isn't buried
SINK_MOST = 24.0        # the ground under it no higher than its underside plus this (its floor would show it)
SLOPE = 72.0            # a bank falls this much a point at the most (about 30 degrees)
ON_GROUND = 80.0        # a thing within this of the old ground at its spot lay on it, and rises with it
SEAT = 2.0
GAP_FROM = 12.0         # a building whose underside is over its ground by this somewhere is looked at


def of_mod(gd, pr, world, cat):
    """Every building the mod stands in a world, as fill() takes them. cat: townbuild's catalogue."""
    import townbuild
    by = {b['key']: b for b in cat}
    inside = {gd.key(c) for c in gd.grid(world).values()}
    out = []
    for ck, c in pr.cells.items():
        if ck not in inside:
            continue
        for rk, r in c['refs'].items():
            b = by.get(r.get('base'))
            if not b or not r.get('p') or r.get('removed') or not rk.startswith('+'):
                continue
            o = townbuild.obnd(gd, r['base'])
            if o:
                out.append((ck, rk, r, o, b.get('mid')))
    return out


def fill(gd, pr, world, buildings, progress=None):
    """buildings: [(cell key, ref key, ref, obnd (x0, y0, z0, x1, y1, z1), mid: the game's ground at its middle over its
    origin, or None)]. Returns (ops, report)."""
    import land
    import tes4
    grid = gd.grid(world)
    # the buildings with daylight under them, and the ground each wants
    want = []                                   # (x, y, rz, s, box, target)
    for ck, rk, r, o, mid in buildings:
        p, s = r['p'], float(r.get('s') or 1.0)
        under = p[2] + o[2] * s
        target = p[2] + mid * s - MEET if mid is not None else under + SINK_MOST - MEET
        target = min(target, under + SINK_MOST)
        want.append((p, s, o, target))
    # the land of every cell they touch, in one array of points
    cells = set()
    for p, s, o, t in want:
        rad = math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * s + HOLD + 12 * POINT
        for cx in range(int((p[0] - rad) // 4096), int((p[0] + rad) // 4096) + 1):
            for cy in range(int((p[1] - rad) // 4096), int((p[1] + rad) // 4096) + 1):
                if (cx, cy) in grid:
                    cells.add((cx, cy))
    if not cells:
        return [], {'buildings': 0, 'cells': 0, 'raised': 0, 'lifted': 0}
    x0, y0 = min(c[0] for c in cells), min(c[1] for c in cells)
    W, H = max(c[0] for c in cells) - x0 + 1, max(c[1] for c in cells) - y0 + 1
    A, D = W * PER_CELL + 1, H * PER_CELL + 1
    now = [None] * (A * D)
    forms = {}
    for (cx, cy) in cells:
        cell = grid[(cx, cy)]
        key = gd.key(cell)
        mine = pr.land.get(key)
        e = None
        if mine:
            h = mine['h']
        else:
            e = gd.land_at(world, cx, cy)
            if not e:
                continue
            vh = dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1]))).get('VHGT')
            if not vh:
                continue
            h = land.heights_of(vh)
        forms[(cx, cy)] = (key, mine, e)
        for row in range(33):
            at = ((cy - y0) * PER_CELL + row) * A + (cx - x0) * PER_CELL
            for c in range(33):
                v = h[row * 33 + c]
                k = at + c
                now[k] = v if now[k] is None else max(now[k], v)     # (a cell's edge row is its neighbour's too)
    start = list(now)
    n = A * D
    floor = {}                                  # point -> the least it must come up to
    looked = 0
    for p, s, o, target in want:
        cs, sn = math.cos(p[5]), math.sin(p[5])
        gx, gy = p[0] / POINT - x0 * PER_CELL, p[1] / POINT - y0 * PER_CELL
        rad = (math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * s + HOLD) / POINT + 1
        pts = []
        for y in range(max(0, int(gy - rad)), min(D - 1, int(gy + rad) + 1) + 1):
            for x in range(max(0, int(gx - rad)), min(A - 1, int(gx + rad) + 1) + 1):
                k = y * A + x
                if now[k] is None:
                    continue
                dx, dy = (x - gx) * POINT, (y - gy) * POINT
                lx, ly = dx * cs - dy * sn, dx * sn + dy * cs
                if o[0] * s - HOLD <= lx <= o[3] * s + HOLD and o[1] * s - HOLD <= ly <= o[4] * s + HOLD:
                    pts.append(k)
        under = p[2] + o[2] * s
        if not pts or max(under - now[k] for k in pts) < GAP_FROM:
            continue
        looked += 1
        t = math.floor(target / STEP) * STEP
        for k in pts:
            if now[k] < t:
                floor[k] = max(floor.get(k, -1e9), t)
    # the banks: from every raised point outward, the ground no lower than its height less SLOPE a step
    heap = [(-v, k) for k, v in floor.items()]
    heapq.heapify(heap)
    best = dict(floor)
    while heap:
        v, k = heapq.heappop(heap)
        v = -v
        if v < best.get(k, -1e9):
            continue
        x = k % A
        for t in (k - 1 if x else -1, k + 1 if x < A - 1 else -1, k - A, k + A):
            if 0 <= t < n and now[t] is not None:
                down = v - SLOPE
                if down > now[t] and down > best.get(t, -1e9):
                    best[t] = down
                    heapq.heappush(heap, (-down, t))
    raised = 0
    for k, v in best.items():
        v = math.ceil(v / STEP) * STEP
        if v > now[k] + 0.5:
            now[k] = v
            raised += 1
    ops, changed = [], 0
    for (cx, cy), (key, mine, e) in sorted(forms.items()):
        h = []
        for row in range(33):
            at = ((cy - y0) * PER_CELL + row) * A + (cx - x0) * PER_CELL
            h += now[at:at + 33]
        old = []
        for row in range(33):
            at = ((cy - y0) * PER_CELL + row) * A + (cx - x0) * PER_CELL
            old += start[at:at + 33]
        if all(abs(a - b) < 0.5 for a, b in zip(h, old)):
            continue
        form = dict(mine) if mine else land.decode(gd, e, {})
        form = dict(form, h=[float(v) for v in h])
        ops.append({'op': 'land', 'cell': key, 'land': form})
        changed += 1

    def at(arr, x, y):
        fx, fy = x / POINT - x0 * PER_CELL, y / POINT - y0 * PER_CELL
        i, j = min(A - 2, max(0, int(fx))), min(D - 2, max(0, int(fy)))
        u, v = fx - i, fy - j
        a, b, c, d = arr[j * A + i], arr[j * A + i + 1], arr[(j + 1) * A + i], arr[(j + 1) * A + i + 1]
        if None in (a, b, c, d):
            return None
        return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v
    # what lay on ground that rose rises with it; buildings, and whatever stands inside a building's box (its doors, its
    # boards, its floor's things, its roof's camp: they stand on the building), keep their heights
    keep = {(ck, rk) for ck, rk, _r, _o, _m in buildings}
    boxes = [(r['p'], float(r.get('s') or 1.0), o) for _ck, _rk, r, o, _m in buildings]

    def on_a_building(x, y):
        for p, s, o in boxes:
            if abs(x - p[0]) > 3000 or abs(y - p[1]) > 3000:
                continue
            cs, sn = math.cos(p[5]), math.sin(p[5])
            dx, dy = x - p[0], y - p[1]
            lx, ly = dx * cs - dy * sn, dx * sn + dy * cs
            if o[0] * s - 8 <= lx <= o[3] * s + 8 and o[1] * s - 8 <= ly <= o[4] * s + 8:
                return True
        return False
    inside = {gd.key(grid[c]) for c in cells}
    lifted = 0
    for ck, c in pr.cells.items():
        if ck not in inside:
            continue
        for rk, r in c['refs'].items():
            p = r.get('p')
            if not rk.startswith('+') or not p or r.get('removed') or (ck, rk) in keep:
                continue
            a, b = at(start, p[0], p[1]), at(now, p[0], p[1])
            if a is None or b is None or b - a < SEAT or abs(p[2] - a) > ON_GROUND or on_a_building(p[0], p[1]):
                continue
            ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [p[0], p[1], round(p[2] + b - a, 1)] + list(p[3:])})
            lifted += 1
    return ops, {'buildings': looked, 'cells': changed, 'raised': raised, 'lifted': lifted}
