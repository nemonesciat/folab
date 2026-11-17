"""Ground people can walk: sharp steps and spikes taken out of land the mod has shaped.

Levelling a plot for every building and bedding every road leaves, where two of them meet at different heights or cut
into a slope, a wall a point wide: a spike or a ledge no one can walk. Here every land point the mod's shaping moved (and
the few round it) is eased until no point stands far proud of its neighbours and no step between two is steeper than a
person climbs, or than the hill was there to begin with. The ground under each building that stands is left exactly as it was, so the building still sits on it;
land the mod never touched keeps the shape the height file gave it (a hill is meant to be steep).

Everything standing on ground that moved is moved with it by the same amount, so a road piece or a street light isn't
left hanging or buried. Returns ops: the cells' land, then the moves."""
import heapq
import math

POINT = 128.0
PER_CELL = 32
STEP = 8.0
MAX_STEP = 72.0         # the most one land point may stand above or below the next: about 30 degrees, a slope to walk
REACH = 12              # points round what the mod moved that are eased with it
SPIKE = 48.0            # a lone point this far past the highest or lowest of the four round it is a spike
ROAD_STEP = 40.0        # and along or across a road: a slope of about one in three at the very most
HOLD = 96.0             # round a building's box, this much more ground stays too
SEAT = 2.0              # a thing is moved when its ground moved this much


def soften(gd, pr, world, keep=(), roads=(), progress=None):
    """(ops, report). keep: [(x, y, turn, x0, y0, x1, y1)]: where each building stands and its box in its own frame; the ground
    under it stays as it is. roads: [(line of (x, y), half width)]: eased first and flatter, the ground beside them after."""
    import land
    grid = gd.grid(world)
    shaped = [k for k, c in grid.items() if gd.key(c) in pr.land]
    if not shaped:
        return [], {'eased': 0, 'cells': 0, 'reseated': 0}
    # (the cells the mod shaped and the ones round them: a big world is mostly not ours)
    bx0, by0 = min(k[0] for k in shaped) - 1, min(k[1] for k in shaped) - 1
    bx1, by1 = max(k[0] for k in shaped) + 1, max(k[1] for k in shaped) + 1
    grid = {k: c for k, c in grid.items() if bx0 <= k[0] <= bx1 and by0 <= k[1] <= by1}
    xs, ys = [k[0] for k in grid], [k[1] for k in grid]
    x0, y0 = min(xs), min(ys)
    W, H = max(xs) - x0 + 1, max(ys) - y0 + 1
    A, D = W * PER_CELL + 1, H * PER_CELL + 1
    now = [None] * (A * D)
    was = [None] * (A * D)
    forms = {}
    cache = {}
    for (cx, cy), cell in grid.items():
        key = gd.key(cell)
        mine = pr.land.get(key)
        base = None
        e = gd.land_at(world, cx, cy)
        if e:
            vh = dict(land.tes4.iter_subrecords(gd.plugins[e[0]].data(e[1]))).get('VHGT')
            base = land.heights_of(vh) if vh else None
        h = mine['h'] if mine else base
        if h is None:
            continue
        forms[(cx, cy)] = (key, mine, e)
        for r in range(33):
            row = ((cy - y0) * PER_CELL + r) * A + (cx - x0) * PER_CELL
            now[row:row + 33] = h[r * 33:r * 33 + 33]
            if base is not None:
                was[row:row + 33] = base[r * 33:r * 33 + 33]
    n = A * D
    moved = bytearray(n)
    for s in range(n):
        if now[s] is not None and was[s] is not None and abs(now[s] - was[s]) > 0.5:
            moved[s] = 1
    if not any(moved):
        return [], {'eased': 0, 'cells': 0, 'reseated': 0}
    # the points to ease: what moved, and a few round it
    ease = bytearray(moved)
    edge = [s for s in range(n) if moved[s]]
    for _ in range(REACH):
        nxt = []
        for s in edge:
            x = s % A
            for t in (s - 1 if x else -1, s + 1 if x < A - 1 else -1, s - A, s + A):
                if 0 <= t < n and not ease[t] and now[t] is not None:
                    ease[t] = 1
                    nxt.append(t)
        edge = nxt
    held = bytearray(n)
    for kx, ky, rz, bx0, by0, bx1, by1 in keep:
        c, sn = math.cos(rz), math.sin(rz)
        rad = math.hypot(max(abs(bx0), abs(bx1)), max(abs(by0), abs(by1))) + HOLD
        gx, gy, gr = kx / POINT - x0 * PER_CELL, ky / POINT - y0 * PER_CELL, rad / POINT + 1
        for y in range(max(0, int(gy - gr)), min(D - 1, int(gy + gr) + 1) + 1):
            for x in range(max(0, int(gx - gr)), min(A - 1, int(gx + gr) + 1) + 1):
                dx, dy = (x - gx) * POINT, (y - gy) * POINT
                lx, ly = dx * c - dy * sn, dx * sn + dy * c          # (in the building's own frame)
                if bx0 - HOLD <= lx <= bx1 + HOLD and by0 - HOLD <= ly <= by1 + HOLD:
                    held[y * A + x] = 1
    start = list(now)
    INF = float('inf')

    def round_of(s):
        x = s % A
        return [t for t in (s - 1 if x else -1, s + 1 if x < A - 1 else -1, s - A, s + A) if 0 <= t < n and now[t] is not None]

    def ease_these(todo, most, stays):
        """Bring these points to within `most` of each other and of the ground round them that stays (stays(point))."""
        free = bytearray(n)
        for s in todo:
            free[s] = 1
        # 1. a point standing alone far above or below everything round it is a spike: it takes the middle of what's round it
        for _ in range(2):
            nxt = {}
            for s in todo:
                near = sorted(now[t] for t in round_of(s))
                if len(near) < 3:
                    continue
                mid = (near[len(near) // 2] + near[(len(near) - 1) // 2]) / 2
                if abs(now[s] - mid) > SPIKE and (now[s] > near[-1] or now[s] < near[0]):
                    nxt[s] = mid
            for s, z in nxt.items():
                now[s] = z
        # 2. what the ground that stays put allows each point: no further above or below it than the slope from it reaches
        flat = most - STEP                      # (so that rounded to whole steps it is still within most)

        def reach(a, b):
            # (or as steep as the land was there before anyone shaped it: a hillside stays a hillside)
            return max(flat, abs(was[a] - was[b])) if was[a] is not None and was[b] is not None else flat
        top, low = {}, {}
        for sign, out in ((1.0, top), (-1.0, low)):
            heap = []
            for s in todo:
                for t in round_of(s):
                    if not free[t] and stays(t):
                        v = sign * now[t] + reach(s, t)
                        if v < out.get(s, INF):
                            out[s] = v
                            heapq.heappush(heap, (v, s))
            while heap:
                v, s = heapq.heappop(heap)
                if v > out.get(s, INF):
                    continue
                for t in round_of(s):
                    if free[t] and v + reach(s, t) < out.get(t, INF):
                        out[t] = v + reach(s, t)
                        heapq.heappush(heap, (out[t], t))
        for s in todo:
            hi, lo = top.get(s, INF), -low.get(s, INF)
            now[s] = (hi + lo) / 2 if lo > hi else min(hi, max(lo, now[s]))
        # 3. between themselves: once with only the high points brought down, once with only the low ones brought up; half
        #    way between the two is a slope where there was a step, and neither a cutting nor a bank alone
        both = []
        for sign in (1.0, -1.0):
            z = {s: sign * now[s] for s in todo}
            heap = [(v, s) for s, v in z.items()]
            heapq.heapify(heap)
            while heap:
                v, s = heapq.heappop(heap)
                if v > z[s]:
                    continue
                for t in round_of(s):
                    if free[t] and z[t] > v + reach(s, t):
                        z[t] = v + reach(s, t)
                        heapq.heappush(heap, (z[t], t))
            both.append(z)
        for s in todo:
            z = round((both[0][s] - both[1][s]) / 2 / STEP) * STEP
            now[s] = STEP if z < STEP <= start[s] else z      # (land stays land)

    # the roads first, between themselves and the buildings: a road is the flattest thing there is, and the ground beside
    # it then comes to meet it
    on_road = bytearray(n)
    for line, half in roads:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            L = math.hypot(bx - ax, by - ay)
            for k in range(int(L // 64) + 1):
                t = min(1.0, k * 64 / L) if L else 0.0
                gx, gy = (ax + (bx - ax) * t) / POINT - x0 * PER_CELL, (ay + (by - ay) * t) / POINT - y0 * PER_CELL
                gr = half / POINT
                for y in range(max(0, int(math.ceil(gy - gr))), min(D - 1, int(gy + gr)) + 1):
                    for x in range(max(0, int(math.ceil(gx - gr))), min(A - 1, int(gx + gr)) + 1):
                        if (x - gx) ** 2 + (y - gy) ** 2 <= gr * gr:
                            on_road[y * A + x] = 1
    can = [s for s in range(n) if ease[s] and not held[s] and now[s] is not None and now[s] >= 0]
    if progress:
        progress('Easing the roads', 0, 2)
    ease_these([s for s in can if on_road[s]], ROAD_STEP, lambda t: held[t])
    if progress:
        progress('Easing sharp ground', 1, 2)
    ease_these([s for s in can if not on_road[s]], MAX_STEP, lambda t: True)
    eased = sum(1 for s in can if now[s] != start[s])
    ops, cells = [], 0
    for (cx, cy), (key, mine, cell) in sorted(forms.items()):
        h = []
        for r in range(33):
            row = ((cy - y0) * PER_CELL + r) * A + (cx - x0) * PER_CELL
            h += now[row:row + 33]
        old = mine['h'] if mine else None
        if old is None:
            row0 = [start[((cy - y0) * PER_CELL + r) * A + (cx - x0) * PER_CELL + c] for r in range(33) for c in range(33)]
            old = row0
        if all(abs(a - b) < 0.5 for a, b in zip(h, old)):
            continue
        form = dict(mine) if mine else land.decode(gd, cell, cache)
        form = dict(form, h=[float(v) for v in h])
        ops.append({'op': 'land', 'cell': key, 'land': form})
        cells += 1

    def at(arr, x, y):
        fx, fy = x / POINT - x0 * PER_CELL, y / POINT - y0 * PER_CELL
        i, j = min(A - 2, max(0, int(fx))), min(D - 2, max(0, int(fy)))
        s, t = fx - i, fy - j
        a, b, c, d = arr[j * A + i], arr[j * A + i + 1], arr[(j + 1) * A + i], arr[(j + 1) * A + i + 1]
        if None in (a, b, c, d):
            return None
        return (a * (1 - s) + b * s) * (1 - t) + (c * (1 - s) + d * s) * t
    # what stands on ground that moved goes with it
    reseated = 0
    inside = {gd.key(c) for c in grid.values()}
    for ck, c in pr.cells.items():
        if ck not in inside:
            continue
        for rk, r in c['refs'].items():
            p = r.get('p')
            if not rk.startswith('+') or not p or r.get('removed'):
                continue
            a, b = at(start, p[0], p[1]), at(now, p[0], p[1])
            if a is None or b is None or abs(b - a) < SEAT:
                continue
            ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [p[0], p[1], round(p[2] + b - a, 1)] + list(p[3:])})
            reseated += 1
    return ops, {'eased': eased, 'cells': cells, 'reseated': reseated}


def steepness(ground, x, y, reach=160.0):
    """How steep the ground is at a spot, as rise over run (0.2 is a slope you notice underfoot)."""
    a, b = ground.at(x - reach, y), ground.at(x + reach, y)
    c, d = ground.at(x, y - reach), ground.at(x, y + reach)
    if None in (a, b, c, d):
        return 0.0
    return math.hypot(b - a, d - c) / (2 * reach)
