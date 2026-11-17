"""The sea, from the map's coastline rather than the height file.

Height files are poor at the shore: reef flats and shallows are recorded as exactly sea level (so they come out as
land), and where a file has the sea floor at all it is coarse and can drop hundreds of metres. OpenStreetMap has the
coastline itself, drawn so the land is on its left and the water on its right. Here the land points of a world
(mapscale.Grid) are split by that line: every point on the water's side becomes sea bed, sloping gently down from the
shore to a cutoff depth and flat beyond it; every point on the land's side stands at least a little above the water.

A coastline with a gap in it would let the sea in over the land: that is checked (the land side of the line must stay
dry) and the grid is then left as it was."""
import array
import collections
import math

STEP = 8.0
POINT = 128.0
PER_CELL = 32
SLOPE = 0.1             # how fast the bed drops away from the shore: one down for ten out
BEACH = 16.0            # the lowest the land stands above the sea
DEPTH = 1536.0          # where the bed stops dropping, unless told otherwise
LEAK_SHARE = 0.25       # a stretch this evenly split between the two has land and sea running together: the line has a gap
OFF = 1.2               # how far off the line, in squares, the points that say which side is which are set


def _trace(ax, ay, bx, by):
    """The grid squares a line from a to b passes through, one after another with no corner-to-corner jumps a flood could slip through."""
    x, y = int(math.floor(ax)), int(math.floor(ay))
    ex, ey = int(math.floor(bx)), int(math.floor(by))
    dx, dy = bx - ax, by - ay
    sx, sy = (1 if dx > 0 else -1), (1 if dy > 0 else -1)
    tdx = abs(1.0 / dx) if dx else float('inf')
    tdy = abs(1.0 / dy) if dy else float('inf')
    tx = ((x + (sx > 0)) - ax) / dx if dx else float('inf')
    ty = ((y + (sy > 0)) - ay) / dy if dy else float('inf')
    yield x, y
    for _ in range(abs(ex - x) + abs(ey - y) + 2):
        if x == ex and y == ey:
            return
        if tx < ty:
            x += sx
            tx += tdx
        else:
            y += sy
            ty += tdy
        yield x, y


def shape_sea(grid, lines, depth=None, slope=SLOPE, beach=BEACH):
    """Split a Grid's points by the coastlines (each a list of (x, y) in game units, land on the left) and shape the sea.
    Returns what it did: {'sea': points under water, 'raised': land points lifted clear of it, 'coast': squares the line
    crosses}; or {'leak': True} with the grid untouched when the line has a gap; or None when no coastline falls on it."""
    depth = abs(float(depth)) if depth not in (None, '') else DEPTH
    across, down, pts = grid.across, grid.down, grid.pts
    gx0, gy0 = grid.x0 * PER_CELL, grid.y0 * PER_CELL
    to_grid = lambda x, y: (x / POINT - gx0 + 0.5, y / POINT - gy0 + 0.5)     # (a point sits in the middle of its square)
    n = across * down
    wall = bytearray(n)
    wet_seeds, dry_seeds = [], []
    crossed = 0
    # an end that stops short inside the world (the map file covers less than the height file's rectangle) is carried on
    # the way it was going to the world's edge, or the sea would come round it
    ends = collections.Counter()
    for line in lines:
        if len(line) > 1:
            ends[(round(line[0][0]), round(line[0][1]))] += 1
            ends[(round(line[-1][0]), round(line[-1][1]))] += 1
    reach = (across + down) * POINT

    def carried(line):
        line = list(line)
        for at, nxt in ((0, 1), (-1, -2)):
            x, y = line[at]
            gx, gy = to_grid(x, y)
            if ends[(round(x), round(y))] == 1 and 1 <= gx < across - 1 and 1 <= gy < down - 1:
                dx, dy = x - line[nxt][0], y - line[nxt][1]
                k = math.hypot(dx, dy) or 1.0
                far_pt = (x + dx / k * reach, y + dy / k * reach)
                line = [far_pt] + line if at == 0 else line + [far_pt]
        return line
    for line in lines:
        if len(line) < 2:
            continue
        g = [to_grid(x, y) for x, y in carried(line)]
        for (ax, ay), (bx, by) in zip(g, g[1:]):
            length = math.hypot(bx - ax, by - ay)
            if not length:
                continue
            for x, y in _trace(ax, ay, bx, by):
                if 0 <= x < across and 0 <= y < down and not wall[y * across + x]:
                    wall[y * across + x] = 1
                    crossed += 1
            # a point a little way off each side of the line, every couple of squares along it
            rx, ry = (by - ay) / length, -(bx - ax) / length            # (the right of the way it runs: the water)
            for k in range(max(1, int(length / 2))):
                t = (k + 0.5) / max(1, int(length / 2))
                mx, my = ax + (bx - ax) * t, ay + (by - ay) * t
                for side, seeds in ((OFF, wet_seeds), (-OFF, dry_seeds)):
                    x, y = int(math.floor(mx + rx * side)), int(math.floor(my + ry * side))
                    if 0 <= x < across and 0 <= y < down:
                        seeds.append(y * across + x)
    if not crossed:
        return None
    todo = collections.deque()
    # Each stretch of ground or water the line closes off is one or the other. Its side is put to the vote: every point
    # set just off the line says "water" or "land" for the stretch it falls in. (A point can fall wrong where a pier or
    # a channel is thinner than the gap it was set off by, so one point never decides.)
    part = array.array('i', bytes(4 * n))
    votes = []                                  # per stretch: [says water, says land]
    for start in range(n):
        if wall[start] or part[start]:
            continue
        votes.append([0, 0])
        k = len(votes)
        part[start] = k
        todo.append(start)
        while todo:
            q = todo.popleft()
            x = q % across
            for t in (q - 1 if x else -1, q + 1 if x < across - 1 else -1, q - across, q + across):
                if 0 <= t < n and not part[t] and not wall[t]:
                    part[t] = k
                    todo.append(t)
    for seeds, which in ((wet_seeds, 0), (dry_seeds, 1)):
        for q in seeds:
            if part[q]:
                votes[part[q] - 1][which] += 1
    for wet_votes, dry_votes in votes:
        both = wet_votes + dry_votes
        if both >= 40 and min(wet_votes, dry_votes) > LEAK_SHARE * both:
            return {'leak': True}               # (a stretch the line calls both: it has a gap, and land and sea run together)
    is_sea = [w > d for w, d in votes]
    # a stretch no point fell in (a pocket the lines close off between them, narrower than the points are set off) takes
    # after what lies round it across the line: off Waikiki's Natatorium one stood out to sea as a little island
    unvoted = set(k + 1 for k, (w, d) in enumerate(votes) if not w and not d)
    if unvoted:
        near = {k: [0, 0] for k in unvoted}
        for t in range(n):                                  # (each wall square: the stretches on either side of it)
            if not wall[t]:
                continue
            tx = t % across
            round_it = [part[u] for u in (t - 1 if tx else -1, t + 1 if tx < across - 1 else -1, t - across, t + across)
                        if 0 <= u < n and part[u]]
            mine = [p for p in round_it if p in unvoted]
            if not mine:
                continue
            says = [0 if votes[p - 1][0] > votes[p - 1][1] else 1 for p in round_it if p not in unvoted]
            for p in mine:
                for s in says:
                    near[p][s] += 1
        for k, (wet_n, dry_n) in near.items():
            is_sea[k - 1] = wet_n > dry_n
    sea = bytearray(n)
    for q in range(n):
        if part[q] and is_sea[part[q] - 1]:
            sea[q] = 1
    # how far out each sea point is: from the line, a square at a time
    far = {}
    for s in range(n):
        if sea[s]:
            x = s % across
            if any(0 <= t < n and wall[t] for t in (s - 1 if x else -1, s + 1 if x < across - 1 else -1, s - across, s + across)):
                far[s] = 1
                todo.append(s)
    dist = [0] * n
    for s, d in far.items():
        dist[s] = d
    while todo:
        s = todo.popleft()
        x = s % across
        for t in (s - 1 if x else -1, s + 1 if x < across - 1 else -1, s - across, s + across):
            if 0 <= t < n and sea[t] and not dist[t]:
                dist[t] = dist[s] + 1
                todo.append(t)
    wet = raised = 0
    for s in range(n):
        if sea[s]:
            d = dist[s] or 10 ** 6                              # (sea the line never touches: open water, at the cutoff)
            pts[s] = -min(depth, max(STEP, round(d * POINT * slope / STEP) * STEP))
            wet += 1
        elif pts[s] < beach:
            pts[s] = beach
            raised += 1
    return {'sea': wet, 'raised': raised, 'coast': crossed, 'depth': depth}


BERM = 40.0             # how high the bank behind a beach stands above the land it was
BERM_AT = (3, 7)        # ...and how many points in from the sea it lies, from and to


def roughen(grid, amount, seed=1, calm=None):
    """Small shape in land a height file leaves smooth: slow swells and smaller bumps of up to about `amount` game units,
    and a low bank a little way in from the sea. The sea bed and the water's edge are left as they are, and so is what
    the height file made steep already (a hill has shape of its own). calm: a mark for each point (osmcover.MapCover.calm) where
    the ground is to stay even, since a road or a building lies on it: a road laid over bumps stands clear of the dips.
    Returns how many points moved."""
    import landshape
    noise = landshape.Noise(seed)
    across, down, pts = grid.across, grid.down, grid.pts
    n = across * down
    amount = float(amount)
    # how far each land point is from the sea, up to a few points
    near = [0] * n
    todo = collections.deque()
    for s in range(n):
        if pts[s] < 0:
            near[s] = -1
    for s in range(n):
        if near[s] == 0:
            x = s % across
            if any(0 <= t < n and near[t] == -1 for t in (s - 1 if x else -1, s + 1 if x < across - 1 else -1, s - across, s + across)):
                near[s] = 1
                todo.append(s)
    while todo:
        s = todo.popleft()
        if near[s] >= BERM_AT[1] + 2:
            continue
        x = s % across
        for t in (s - 1 if x else -1, s + 1 if x < across - 1 else -1, s - across, s + across):
            if 0 <= t < n and near[t] == 0:
                near[t] = near[s] + 1
                todo.append(t)
    moved = 0
    for gy in range(down):
        row = gy * across
        for gx in range(across):
            s = row + gx
            z = pts[s]
            if z < 0 or near[s] in (1, 2) or (calm is not None and calm[s]):
                continue                        # (the sea, and the sand at the water's edge)
            if grid.slope(gx, gy) > 12.0:
                continue
            lift = amount * (0.7 * noise.value(gx / 11.0, gy / 11.0) + 0.3 * noise.value(gx / 3.7 + 50, gy / 3.7 + 50))
            d = near[s]
            if BERM_AT[0] <= d <= BERM_AT[1]:
                mid = (BERM_AT[0] + BERM_AT[1]) / 2.0
                lift += BERM * max(0.0, 1.0 - abs(d - mid) / ((BERM_AT[1] - BERM_AT[0]) / 2.0 + 0.5))
            new = max(BEACH, round((z + lift) / STEP) * STEP)
            if new != z:
                pts[s] = new
                moved += 1
    return moved


# ---------- what stands on flat ground in a height file ----------

BUMP_REACH = 10         # (land points: a bump narrower than twice this and one more is taken off)
BUMP_FLAT = 20.0        # (game units a point: the ground under a bump counts as flat when it slopes less than this)
BUMP_OVER = 24.0        # (and the bump is one when it stands this far over that ground)
BUMP_NEAR = 6           # (land points from a building on the map: roofs are only where buildings are)


def _slide(rows, reach, pick):
    out = []
    for row in rows:
        n = len(row)
        out.append([pick(row[max(0, k - reach):k + reach + 1]) for k in range(n)])
    return out


def level_bumps(grid, near, reach=BUMP_REACH):
    """A height file made from above measures roofs and treetops: a town on flat land comes out as lumps and spikes, each
    tower a hill. What stands on flat ground and is no wider than a city block is taken off, down to the ground round it;
    a real hill is wider than that or stands on a slope, and is left. near: spots (x, y in game units) on the map's
    buildings: only round those is anything a roof (the rim of a crater is a narrow thing on flat ground too, and with
    nothing to tell them apart it was once taken off Diamond Head). Only land above the water is looked at. Returns how
    many points came down."""
    across, down, pts = grid.across, grid.down, grid.pts
    roofs = bytearray(across * down)
    for x, y in near:
        gx, gy = int(round(x / 128.0)) - grid.x0 * 32, int(round(y / 128.0)) - grid.y0 * 32
        for j in range(max(0, gy - BUMP_NEAR), min(down - 1, gy + BUMP_NEAR) + 1):
            row = j * across
            for i in range(max(0, gx - BUMP_NEAR), min(across - 1, gx + BUMP_NEAR) + 1):
                roofs[row + i] = 1
    rows = [[max(8.0, float(v)) for v in pts[r * across:(r + 1) * across]] for r in range(down)]
    turn = lambda m: [list(c) for c in zip(*m)]
    low = turn(_slide(turn(_slide(rows, reach, min)), reach, min))
    opened = turn(_slide(turn(_slide(low, reach, max)), reach, max))
    moved = 0
    for r in range(down):
        o = opened[r]
        for c in range(across):
            s = r * across + c
            h = pts[s]
            if not roofs[s] or h < 8 or h - o[c] < BUMP_OVER:
                continue
            a, b = o[max(0, c - reach)], o[min(across - 1, c + reach)]
            u, d = opened[max(0, r - reach)][c], opened[min(down - 1, r + reach)][c]
            if max(abs(a - b), abs(u - d)) > BUMP_FLAT * 2 * reach:
                continue
            pts[s] = type(h)(o[c])
            moved += 1
    return moved
