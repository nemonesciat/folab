"""Buildings set into the ground as the game sets its own: down at the street's level, the land made flat under them and
eased back to the street within a few steps, never a mound.

padfill brought the land up to each building where it stood over air, and banked it down from there (up to 30 degrees):
a building on a slope or a plot stood high stood on a grass plinth, and 1,628 of Waikiki's 2,172 buildings had land raised
against their walls (18 Nov 2026, measured; the user's look in the game: "buildings raised off the ground"). Here instead:

- a building's street level `L` is the land round it a little way out (`RING_IN` to `RING_OUT` past its walls, other
  buildings' pads left out), a low share of it (`LOW`), so neither a neighbour's bank nor a rise behind it sets it;
- the building goes down (or up) so its own ground (the catalogue's `mid`: where the game's land meets its walls) is
  `SINK` under `L`: the foundation in the ground, no daylight under any wall;
- the land within `HOLD` of its walls is made `L` (cut or filled); from there out over `EASE` it blends back to the land
  as it was, so an old bank goes and no new one is made; road pieces' ground is left (roadbed beds them after);
- whatever stood in the building's box (its doors, boards, shut doorways, roof camps) moves with it; things standing on
  ground that moved move with the ground; a building that would move more than `MOVE_MOST` is left and reported.
Returns (ops, report); `cells` limits it to buildings standing in those cells (the land may change a little past them)."""
import math

POINT = 128.0
PER_CELL = 32
STEP = 8.0
HOLD = 64.0             # past a building's walls, the land at its level (a footing, a doorstep)
EASE = 384.0            # then blended back to the land as it was over this
RING_IN, RING_OUT = 320.0, 704.0     # where the street's level is read, past the walls
LOW = 0.3               # that share of the ring's land is under the street level
SINK = 8.0              # a building's own ground this far under the street level
MOVE_MOST = 512.0
TERRACE_MOST = 48.0       # a building is lifted to its neighbours' shared level by this much at the most
NEAR = 2 * HOLD + 128.0  # buildings this close share one level (a hillside's terrace), or the nearer pad leaves a step at the other's wall
ON_GROUND = 80.0        # a thing this near the land at its spot stood on it
ROAD_REACH = 128.0      # land points this far past a road piece are its own: the ground under its edge


def _local(p, x, y):
    cs, sn = math.cos(p[5]), math.sin(p[5])
    dx, dy = x - p[0], y - p[1]
    return dx * cs - dy * sn, dx * sn + dy * cs


def _box_dist(o, s, lx, ly):
    ax = max(o[0] * s - lx, 0.0, lx - o[3] * s)
    ay = max(o[1] * s - ly, 0.0, ly - o[4] * s)
    return math.hypot(ax, ay)


def fit(gd, pr, world, cells=None, cat=None, progress=None, debug=None):
    import land
    import roadbed
    import tes4
    import townbuild
    grid = gd.grid(world)
    if cat is None:
        import server
        cat = townbuild.load(gd, server.kits_folder())
    by = {b['key']: b for b in cat}
    key_of = {gd.key(c): k for k, c in grid.items()}
    want = {gd.key(grid[k]) for k in cells} if cells is not None else set(key_of)
    flat = roadbed._flat_bases(gd)
    builds, roads = [], []
    for ck, c in pr.cells.items():
        if ck not in key_of:
            continue
        for rk, r in c['refs'].items():
            p, b = r.get('p'), r.get('base')
            if not p or not b or r.get('removed'):
                continue
            if b in by and rk.startswith('+'):
                o = townbuild.obnd(gd, b)
                if o:
                    builds.append({'ck': ck, 'rk': rk, 'r': r, 'p': p, 's': float(r.get('s') or 1.0), 'o': o,
                                   'mid': by[b].get('mid'), 'mine': ck in want})
            elif b in flat:
                roads.append((p, flat[b]))
    mine = [b for b in builds if b['mine']]
    if not mine:
        return [], {'buildings': 0}
    # the land round them, one array of points
    reach = HOLD + EASE + RING_OUT + POINT
    area = set()
    for b in mine:
        p, o, s = b['p'], b['o'], b['s']
        rad = math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * s + reach
        for cx in range(int((p[0] - rad) // 4096), int((p[0] + rad) // 4096) + 1):
            for cy in range(int((p[1] - rad) // 4096), int((p[1] + rad) // 4096) + 1):
                if (cx, cy) in grid:
                    area.add((cx, cy))
    x0, y0 = min(c[0] for c in area), min(c[1] for c in area)
    A = (max(c[0] for c in area) - x0 + 1) * PER_CELL + 1
    D = (max(c[1] for c in area) - y0 + 1) * PER_CELL + 1
    now = [None] * (A * D)
    forms = {}
    for (cx, cy) in area:
        cell = grid[(cx, cy)]
        key = gd.key(cell)
        mine_land = pr.land.get(key)
        e = None
        if mine_land:
            h = mine_land['h']
        else:
            e = gd.land_at(world, cx, cy)
            vh = dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1]))).get('VHGT') if e else None
            if not vh:
                continue
            h = land.heights_of(vh)
        forms[(cx, cy)] = (key, mine_land, e)
        for row in range(33):
            at = ((cy - y0) * PER_CELL + row) * A + (cx - x0) * PER_CELL
            for col in range(33):
                k = at + col
                v = h[row * 33 + col]
                now[k] = v if now[k] is None else max(now[k], v)
    start = list(now)

    def k_of(x, y):
        gx, gy = int(round(x / POINT)) - x0 * PER_CELL, int(round(y / POINT)) - y0 * PER_CELL
        return gy * A + gx if 0 <= gx < A and 0 <= gy < D else None

    def xy_of(k):
        return ((k % A) + x0 * PER_CELL) * POINT, ((k // A) + y0 * PER_CELL) * POINT

    def ground(arr, x, y):
        fx, fy = x / POINT - x0 * PER_CELL, y / POINT - y0 * PER_CELL
        i, j = int(math.floor(fx)), int(math.floor(fy))
        if not (0 <= i < A - 1 and 0 <= j < D - 1):
            return None
        u, v = fx - i, fy - j
        a, b, c, d = arr[j * A + i], arr[j * A + i + 1], arr[(j + 1) * A + i], arr[(j + 1) * A + i + 1]
        if None in (a, b, c, d):
            return None
        return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v

    # road pieces' ground is roadbed's
    held = set()
    for p, box in roads:
        cs, sn = math.cos(p[5]), math.sin(p[5])
        # (a land point past the road's edge, up to one point away, still shapes the ground under that edge)
        rad = math.hypot(max(abs(box[0]), abs(box[3])), max(abs(box[1]), abs(box[4]))) + ROAD_REACH
        for gy in range(int((p[1] - rad) // POINT), int((p[1] + rad) // POINT) + 2):
            for gx in range(int((p[0] - rad) // POINT), int((p[0] + rad) // POINT) + 2):
                k = k_of(gx * POINT, gy * POINT)
                if k is None:
                    continue
                lx, ly = _local(p, gx * POINT, gy * POINT)
                if box[0] - ROAD_REACH <= lx <= box[3] + ROAD_REACH and box[1] - ROAD_REACH <= ly <= box[4] + ROAD_REACH:
                    held.add(k)

    # every building by the 1024-unit squares its pad reaches into (a whole city has thousands: looking through all of them
    # for each spot took hours)
    bucket = {}
    for b in builds:
        p, o, s = b['p'], b['o'], b['s']
        r = math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * s + NEAR + POINT
        for i in range(int((p[0] - r) // 1024), int((p[0] + r) // 1024) + 1):
            for j in range(int((p[1] - r) // 1024), int((p[1] + r) // 1024) + 1):
                bucket.setdefault((i, j), []).append(b)

    def near_builds(x, y):
        return bucket.get((int(x // 1024), int(y // 1024)), ())

    def in_any_pad(x, y, skip):
        for b in near_builds(x, y):
            if b is skip:
                continue
            lx, ly = _local(b['p'], x, y)
            if _box_dist(b['o'], b['s'], lx, ly) <= HOLD + POINT:
                return True
        return False

    claim = {}                                  # point -> (distance from walls, target height)
    moves = []                                  # (building, dz)
    left = []
    levels = []                                 # (building, its own street level)
    for n, b in enumerate(mine):
        if progress and n % 50 == 0:
            progress(n, len(mine))
        p, o, s = b['p'], b['o'], b['s']
        ring = []
        hx, hy = (o[3] - o[0]) * s / 2 + RING_OUT, (o[4] - o[1]) * s / 2 + RING_OUT
        cxl, cyl = (o[0] + o[3]) * s / 2, (o[1] + o[4]) * s / 2
        cs, sn = math.cos(p[5]), math.sin(p[5])
        stepn = 96.0
        lx = -hx
        while lx <= hx:
            ly = -hy
            while ly <= hy:
                qx, qy = cxl + lx, cyl + ly
                d = _box_dist(o, s, qx, qy)
                if RING_IN <= d <= RING_OUT:
                    wx = p[0] + qx * cs + qy * sn
                    wy = p[1] - qx * sn + qy * cs
                    if not in_any_pad(wx, wy, b):
                        g = ground(now, wx, wy)
                        if g is not None:
                            ring.append(g)
                ly += stepn
            lx += stepn
        if len(ring) < 8:
            left.append((b['rk'], 'no open ground round it'))
            continue
        ring.sort()
        levels.append((b, ring[int(LOW * (len(ring) - 1))]))

    def corners(b):
        p, o, s = b['p'], b['o'], b['s']
        cs, sn = math.cos(p[5]), math.sin(p[5])
        out = []
        for qx, qy in ((o[0] * s, o[1] * s), (o[3] * s, o[1] * s), (o[0] * s, o[4] * s), (o[3] * s, o[4] * s), ((o[0] + o[3]) * s / 2, (o[1] + o[4]) * s / 2)):
            out.append((p[0] + qx * cs + qy * sn, p[1] - qx * sn + qy * cs))
        return out

    def near(a, b):
        if abs(a['p'][0] - b['p'][0]) > 4000 or abs(a['p'][1] - b['p'][1]) > 4000:
            return False
        for u, v in ((a, b), (b, a)):
            for x, y in corners(u):
                lx, ly = _local(v['p'], x, y)
                if _box_dist(v['o'], v['s'], lx, ly) <= NEAR:
                    return True
        return False
    up = list(range(len(levels)))

    def root(i):
        while up[i] != i:
            up[i] = up[up[i]]
            i = up[i]
        return i
    index = {id(b): i for i, (b, _own) in enumerate(levels)}
    for i, (a, _own) in enumerate(levels):
        seen = set()
        for x, y in corners(a):
            for b in near_builds(x, y):
                j = index.get(id(b))
                if j is None or j <= i or j in seen:
                    continue
                seen.add(j)
                if near(a, b):
                    up[root(i)] = root(j)
    groups = {}
    for i in range(len(levels)):
        groups.setdefault(root(i), []).append(levels[i][1])
    terraces = 0
    for g in groups.values():
        if len(g) > 1:
            terraces += 1
    for i, (b, own) in enumerate(levels):
        g = sorted(groups[root(i)])
        shared = g[len(g) // 2]
        # (never lifted far over its own street to its neighbours' level: lifted 208 to a hillside terrace, a barrack stood
        # 288 over the road beside it. Lowered to theirs is fine: its foundation goes deeper.)
        L = math.floor((shared if shared <= own + TERRACE_MOST else own) / STEP) * STEP
        p, o, s = b['p'], b['o'], b['s']
        under = p[2] + o[2] * s
        foot = p[2] + b['mid'] * s if b['mid'] is not None else under + 16
        dz = (L - SINK) - foot
        if abs(dz) > MOVE_MOST:
            left.append((b['rk'], 'would move %d' % dz))
            continue
        moves.append((b, dz))
        rad = math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * s + HOLD + EASE
        for gy in range(int((p[1] - rad) // POINT), int((p[1] + rad) // POINT) + 2):
            for gx in range(int((p[0] - rad) // POINT), int((p[0] + rad) // POINT) + 2):
                k = k_of(gx * POINT, gy * POINT)
                if k is None or now[k] is None:
                    continue
                lx, ly = _local(p, gx * POINT, gy * POINT)
                d = _box_dist(o, s, lx, ly)
                if d > HOLD + EASE or k in held:
                    continue                    # (a road's ground is the road's: roads are laid first, buildings meet them)
                if d <= HOLD:
                    t = L
                else:
                    u = (d - HOLD) / EASE
                    u = u * u * (3 - 2 * u)
                    t = L + (start[k] - L) * u
                if k not in claim or d < claim[k][0]:
                    claim[k] = (d, t)
    for k, (_d, t) in claim.items():
        now[k] = round(t / STEP) * STEP
    if debug is not None:
        debug.update(claim=claim, k_of=k_of, start=start, now=now, held=held, levels={b['rk']: (own, ) for b, own in levels},
                     moves={b['rk']: dz for b, dz in moves}, group={levels[i][0]['rk']: root(i) for i in range(len(levels))})
    ops, changed = [], 0
    for (cx, cy), (key, mine_land, e) in sorted(forms.items()):
        h, old = [], []
        for row in range(33):
            at = ((cy - y0) * PER_CELL + row) * A + (cx - x0) * PER_CELL
            h += now[at:at + 33]
            old += start[at:at + 33]
        if all(abs(a - c) < 0.5 for a, c in zip(h, old)):
            continue
        form = dict(mine_land) if mine_land else land.decode(gd, e, {})
        ops.append({'op': 'land', 'cell': key, 'land': dict(form, h=[float(v) for v in h])})
        changed += 1
    # the buildings and what's in their boxes go with them; things on moved ground go with the ground
    moved_by = {}
    for b, dz in moves:
        if abs(dz) >= 1:
            moved_by[(b['ck'], b['rk'])] = dz
    dz_of = {id(b): dz for b, dz in moves}
    lifted = carried = 0
    road_keys = set()
    for ck, c in pr.cells.items():
        if ck not in key_of:
            continue
        for rk, r in c['refs'].items():
            p = r.get('p')
            if not p or r.get('removed') or not rk.startswith('+'):
                continue
            if (ck, rk) in moved_by:
                continue
            if r.get('base') in flat:
                road_keys.add((ck, rk))
                continue
            dz = None
            for b in near_builds(p[0], p[1]):
                bdz = dz_of.get(id(b))
                if bdz is None:
                    continue
                lx, ly = _local(b['p'], p[0], p[1])
                o, s = b['o'], b['s']
                if _box_dist(o, s, lx, ly) <= 8 and b['p'][2] + o[2] * s - 64 <= p[2] <= b['p'][2] + o[5] * s + 64:
                    dz = bdz
                    break
            if dz is not None:
                if abs(dz) >= 1:
                    moved_by[(ck, rk)] = dz
                    carried += 1
                continue
            a, n = ground(start, p[0], p[1]), ground(now, p[0], p[1])
            if a is None or n is None or abs(n - a) < 2 or abs(p[2] - a) > ON_GROUND:
                continue
            moved_by[(ck, rk)] = n - a
            lifted += 1
    for (ck, rk), dz in moved_by.items():
        p = pr.cells[ck]['refs'][rk]['p']
        ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [p[0], p[1], round(p[2] + dz, 1)] + list(p[3:])})
    downs = [dz for _b, dz in moves]
    return ops, {'buildings': len(mine), 'set': len(moves), 'terraces': terraces, 'left': left, 'cells': changed, 'points': len(claim),
                 'carried': carried, 'lifted': lifted, 'moved_down': sum(1 for d in downs if d < -1),
                 'moved_up': sum(1 for d in downs if d > 1), 'most_down': round(min(downs or [0])), 'most_up': round(max(downs or [0])),
                 'land_cells': sorted(key_of[ops[i]['cell']] for i in range(len(ops)) if ops[i]['op'] == 'land')}


class Only:
    """A project seen through a few cells: roadbed and osmdress's passes over the whole world, kept to those."""

    def __init__(self, pr, cell_keys):
        self._pr = pr
        self.cells = {k: v for k, v in pr.cells.items() if k in cell_keys}

    def __getattr__(self, name):
        return getattr(self._pr, name)


PIECE_WORDS = ('shack', 'shanty', 'scrap', 'sheetmetal', 'corrugat', 'plywood', 'tent', 'camp', 'crate', 'pallet', 'tarp',
               'junk', 'shed', 'hut', 'hovel', 'barrel', 'car0', 'truck', 'bus', 'hulk', 'wreck', 'dumpster', 'cart', 'fence')
HANG = 8.0              # a standing thing with a corner this far over the land hangs
SET_SINK = 2.0


def settle_pieces(gd, pr, world, cells=None):
    """(ops, report): standing things of the mod's own (tents, shacks, crates, barrels, wrecks: PIECE_WORDS in the editor
    ID) on open ground with a corner hanging over it (on a slope, or ground that moved after): let down so the lowest
    corner meets the land. Not what lies (osmdress.seat_lying tilts those), not on a road (roadbed.onto_roads), not in a
    building's box (it stands on the building)."""
    import roadbed
    import roadgen
    import osmdress
    import townbuild
    import server
    cat = {b['key'] for b in townbuild.load(gd, server.kits_folder())}
    flat = roadbed._flat_bases(gd)
    skip = cat | set(flat) | set(roadbed._slab_bases(gd))
    g = roadgen.Ground(gd, pr, world)
    inside = {gd.key(c) for c in gd.grid(world).values()}
    boxes, roads, things = {}, {}, []
    for ck, c in pr.cells.items():
        if ck not in inside:
            continue
        for rk, r in c['refs'].items():
            p, b = r.get('p'), r.get('base')
            if not p or not b or r.get('removed'):
                continue
            if b in cat or b in flat:
                o = townbuild.obnd(gd, b)
                if o:
                    (boxes if b in cat else roads).setdefault((int(p[0] // 1024), int(p[1] // 1024)), []).append((p, float(r.get('s') or 1), o))
            elif rk.startswith('+') and b not in skip and (cells is None or ck in cells):
                things.append((ck, rk, r, p, b))
    names, out, steep = {}, [], 0

    def word(b):
        if b not in names:
            try:
                e = (gd.edid(gd.from_key(b)) or '').lower() if not b.startswith('+') else ''
            except Exception:
                e = ''
            names[b] = e if any(w in e for w in PIECE_WORDS) and not (osmdress.LIES.search(e) and not osmdress.NOT_LIES.search(e)) else ''
        return names[b]

    def within(table, x, y, grow):
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for p, s, o in table.get((int(x // 1024) + i, int(y // 1024) + j), ()):
                    lx, ly = _local(p, x, y)
                    if _box_dist(o, s, lx, ly) <= grow:
                        return True
        return False
    for ck, rk, r, p, b in things:
        if not word(b):
            continue
        if within(boxes, p[0], p[1], 8) or within(roads, p[0], p[1], 0):
            continue
        o = townbuild.obnd(gd, b)
        if not o:
            continue
        s = float(r.get('s') or 1)
        cs, sn = math.cos(p[5]), math.sin(p[5])
        gs = []
        for qx, qy in ((o[0] * s, o[1] * s), (o[3] * s, o[1] * s), (o[0] * s, o[4] * s), (o[3] * s, o[4] * s), (0.0, 0.0)):
            z = g.at(p[0] + qx * cs + qy * sn, p[1] - qx * sn + qy * cs)
            if z is not None:
                gs.append(z)
        if len(gs) < 4:
            continue
        under = p[2] + o[2] * s
        hang = under - min(gs)
        if hang <= HANG:
            continue
        if max(gs) - min(gs) > 128:
            steep += 1
        out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [p[0], p[1], round(p[2] - hang - SET_SINK, 1)] + list(p[3:])})
    return out, {'let_down': len(out), 'on_steep_ground': steep}
