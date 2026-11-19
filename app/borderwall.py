"""The wall that shuts Waikiki's side of Oʻahu off from Ground Zero (docs/waikiki-story-plan.md, "Where the wall runs"):
from the Kakaʻako shore north round downtown and Chinatown, then up the map's west edge through Kalihi to the mountains.
Built early, by the emergency government and the Navy, to turn back the dying; kept up since against what lives in the
ruins. A clean separation: tall, closed, one gate.

    the wall     the game's McCarran wall (concrete, 754 tall, 350 thick, along its y: its record's
                 bounds say x, swapped; 19 Nov 2026 every piece stood 90 degrees across its line): long pieces (2048) where the
                 ground along them is even within `EVEN`, short ones (512) where it isn't, a tower (660 square, ~1050
                 tall) where even a short piece would rise more than `STEEP` along its length (the uphill end would sit
                 too low). Every piece stands at the lowest ground under it, sunk `SINK`, so none hangs; pieces overlap
                 `OVERLAP`, so no seam lets anyone through. A tower at every bend, and one every `TOWER_EVERY` along.
                 Where the line starts in the sea the wall goes on into it as a breakwater, out to water `DEEP` deep.
    the gate     the McCarran main gate where the line crosses `GATE_ROAD` (the road out to the harbour and Pearl), a
                 tower each side, a guard tower and sandbags on the inside. Shut: nobody goes through yet.
    cleared      what the wall stands on: townbuild's buildings it would cut (`townbuild.crowding`: with what stood in
                 them; a door into one of their places is locked and unlinked), and the loose things (plants, rubble,
                 cars) within `CLEAR` of its line; the ruined freeway's sections within `FREEWAY_CLEAR` (nobody walks
                 over the wall on a deck). Doors with links, markers and roads are left.

`plan(line, ground_at, gate_t)` lays the pieces out (pure: for tests); `ops(gd, pr, world)` makes one Undo's ops of them.
Inside (the court's side) is the side of each leg toward `INSIDE`."""
import math
import random

LINE_CELLS = [(-32.4, -3.2), (-32.6, 4.6), (-33.6, 8.6), (-35.6, 9.6), (-36.7, 10.4), (-36.7, 24.9)]
INSIDE = (-28 * 4096.0, 12 * 4096.0)         # (a point on Waikiki's side of every leg)
LONG, SHORT, TOWER = 'NVMcCarranWallReg02', 'NVMcCarranWallReg01', ('NVMcCarranWall02', 'NVMcCarranWall03', 'NVMcCarranWall04')
GATE, GUARD = 'NVMcCarranMainGate', 'NVGuardTower01'
SANDBAG = 'SandbagStraight'
LONG_LEN, SHORT_LEN, TOWER_LEN, GATE_LEN = 2048.0, 512.0, 660.0, 1230.0
LOW = 249.0                    # (the long and short pieces' bottom lies this far under their origin)
OVERLAP = 24.0
EVEN, STEEP = 140.0, 330.0
SINK = 90.0
TOWER_EVERY = 12000.0
DEEP = 520.0
GATE_ROAD = ('Dillingham Boulevard', 'North King Street', 'Nimitz Highway')
CLEAR, FREEWAY_CLEAR = 330.0, 1400.0
KEEP_WORDS = ('Road', 'Highway', 'Marker', 'Door')


def line_world():
    return [(x * 4096.0, y * 4096.0) for x, y in LINE_CELLS]


def _turn_x(ux, uy):
    """The turn that lays a piece's own x along (ux, uy) (the game turns clockwise seen from above)."""
    return math.atan2(-uy, ux) % math.tau


def _turn_y(ux, uy):
    return math.atan2(ux, uy) % math.tau


def _inside_normal(a, b):
    ux, uy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(ux, uy)
    nx, ny = -uy / L, ux / L
    if (INSIDE[0] - a[0]) * nx + (INSIDE[1] - a[1]) * ny < 0:
        nx, ny = -nx, -ny
    return nx, ny


def plan(line, ground_at, gate_t=None, rnd=None):
    """[(editor ID, x, y, z, turn)] for the wall along line (world points), ground_at(x, y) -> height or None (off the
    land: nothing stands there). gate_t: how far along the whole line the gate's middle is, or None."""
    rnd = rnd or random.Random(11)
    out = []
    towers = [0]

    def low_under(x0, y0, x1, y1, half=175.0, n=9):
        ux, uy = x1 - x0, y1 - y0
        L = math.hypot(ux, uy) or 1.0
        nx, ny = -uy / L * half, ux / L * half
        hs = []
        for i in range(n):
            t = i / (n - 1)
            for k in (-1, 0, 1):
                g = ground_at(x0 + ux * t + nx * k, y0 + uy * t + ny * k)
                if g is not None:
                    hs.append(g)
        return (min(hs), max(hs)) if hs else None

    def tower_at(x, y, z_floor=None):
        hs = [ground_at(x + dx, y + dy) for dx in (-330, 0, 330) for dy in (-330, 0, 330)]
        hs = [h for h in hs if h is not None]
        if not hs:
            return
        out.append((TOWER[towers[0] % len(TOWER)], x, y, min(hs) - SINK, rnd.choice((0.0, math.pi / 2, math.pi, 1.5 * math.pi))))
        towers[0] += 1

    g0 = g1 = None
    if gate_t is not None:
        g0, g1 = gate_t - GATE_LEN / 2 - TOWER_LEN, gate_t + GATE_LEN / 2 + TOWER_LEN

    def wall_piece(a, ux, uy, rz, t, plen, left):
        """Lay one wall piece starting t along the leg from a; returns how far it reaches (or None when nothing fits)."""
        x0, y0 = a[0] + ux * t, a[1] + uy * t
        lo = low_under(x0, y0, x0 + ux * plen, y0 + uy * plen)
        if lo and plen == LONG_LEN and lo[1] - lo[0] > EVEN:
            plen = SHORT_LEN
            lo = low_under(x0, y0, x0 + ux * plen, y0 + uy * plen)
        if not lo:
            return t + SHORT_LEN
        if lo[1] - lo[0] > STEEP:
            tower_at(x0 + ux * TOWER_LEN / 2, y0 + uy * TOWER_LEN / 2)
            return t + TOWER_LEN
        if lo[0] < -DEEP:                     # (deep water: no breakwater out there)
            return t + SHORT_LEN
        out.append((LONG if plen == LONG_LEN else SHORT, x0 + ux * 256, y0 + uy * 256, lo[0] - SINK + LOW, rz))
        return t + plen

    run0 = 0.0
    since_tower = 0.0
    for a, b in zip(line, line[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        rz = _turn_y(ux, uy)            # (its mesh runs along its y: the record's bounds have x and y swapped)
        tower_at(*a)
        t = TOWER_LEN / 2 - OVERLAP
        while t < L - OVERLAP:
            left = L - t
            if g0 is not None and run0 <= g0 <= run0 + L and t >= g0 - run0 - OVERLAP:
                # (the gate: a tower, the gate, a tower)
                c = gate_t - run0
                tower_at(a[0] + ux * (c - GATE_LEN / 2 - TOWER_LEN / 2), a[1] + uy * (c - GATE_LEN / 2 - TOWER_LEN / 2))
                gx, gy = a[0] + ux * c, a[1] + uy * c
                lo = low_under(gx - ux * GATE_LEN / 2, gy - uy * GATE_LEN / 2, gx + ux * GATE_LEN / 2, gy + uy * GATE_LEN / 2, half=286)
                if lo:
                    out.append((GATE, gx, gy, lo[0] - SINK / 3, _turn_y(ux, uy)))
                tower_at(a[0] + ux * (c + GATE_LEN / 2 + TOWER_LEN / 2), a[1] + uy * (c + GATE_LEN / 2 + TOWER_LEN / 2))
                t = g1 - run0 - OVERLAP
                g0 = None
                since_tower = 0.0
                continue
            plen = LONG_LEN if left >= LONG_LEN else SHORT_LEN
            if g0 is not None and run0 <= g0 <= run0 + L:
                room = g0 - run0 - t + OVERLAP
                if room < plen:
                    plen = SHORT_LEN
                    if room < SHORT_LEN:            # (a short piece ending at the gate's tower, reaching back)
                        t = g0 - run0 + OVERLAP - SHORT_LEN
            if left < plen:                         # (a leg's end: a short piece reaching back from it)
                t = L - SHORT_LEN
                plen = SHORT_LEN
            reach = wall_piece(a, ux, uy, rz, t, plen, left)
            since_tower += reach - t
            t = reach - OVERLAP
            if since_tower >= TOWER_EVERY and L - t > TOWER_LEN * 3 and not (g0 is not None and abs(g0 - run0 - t) < 3 * TOWER_LEN):
                tower_at(a[0] + ux * (t + TOWER_LEN / 2), a[1] + uy * (t + TOWER_LEN / 2))
                t += TOWER_LEN - OVERLAP
                since_tower = 0.0
        run0 += L
    tower_at(*line[-1])
    return out


def crossing(line, roads, names=GATE_ROAD):
    """How far along line the first of names' roads crosses it ((road name, along), or None). roads: [(name, [(x, y)])]."""
    best = None
    for order, want in enumerate(names):
        run0 = 0.0
        for a, b in zip(line, line[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            for name, pts in roads:
                if name != want:
                    continue
                for p, q in zip(pts, pts[1:]):
                    d = (b[0] - a[0]) * (q[1] - p[1]) - (b[1] - a[1]) * (q[0] - p[0])
                    if abs(d) < 1e-9:
                        continue
                    t = ((p[0] - a[0]) * (q[1] - p[1]) - (p[1] - a[1]) * (q[0] - p[0])) / d
                    s = ((p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])) / d
                    if 0 <= t <= 1 and 0 <= s <= 1:
                        along = run0 + t * L
                        if best is None or (order, along) < best[0]:
                            best = ((order, along), (want, along))
            run0 += L
        if best:
            return best[1]
    return None


def _dist_to_line(line, x, y):
    best = 1e18
    for a, b in zip(line, line[1:]):
        L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
        t = max(0.0, min(1.0, ((x - a[0]) * (b[0] - a[0]) + (y - a[1]) * (b[1] - a[1])) / L2))
        best = min(best, math.hypot(x - a[0] - (b[0] - a[0]) * t, y - a[1] - (b[1] - a[1]) * t))
    return best


def ops(gd, pr, world, roads=None, cat=None, seed=11):
    """(ops, report, cells): one Undo's worth. roads: [(name, [(x, y)])] in world units, to find the gate's road."""
    import roadgen
    import shipinside
    import townbuild
    import recordio
    line = line_world()
    ground = roadgen.Ground(gd, pr, world)
    grid = gd.grid(world)
    rnd = random.Random(seed)
    gate = crossing(line, roads or [])
    placed = plan(line, ground.at, gate[1] if gate else None, rnd)
    # the inside's extras at the gate: a guard tower and sandbags
    if gate:
        run0 = 0.0
        for a, b in zip(line, line[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if run0 <= gate[1] <= run0 + L:
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                nx, ny = _inside_normal(a, b)
                c = gate[1] - run0
                gx, gy = a[0] + ux * c, a[1] + uy * c
                tx, ty = gx + ux * (GATE_LEN / 2 + TOWER_LEN + 700) + nx * 900, gy + uy * (GATE_LEN / 2 + TOWER_LEN + 700) + ny * 900
                g = ground.at(tx, ty)
                if g is not None:
                    placed.append((GUARD, tx, ty, g - 20, _turn_y(-nx, -ny)))
                for k in (-1, 1):
                    sx, sy = gx + ux * k * 420 + nx * 700, gy + uy * k * 420 + ny * 700
                    g = ground.at(sx, sy)
                    if g is not None:
                        placed.append((SANDBAG, sx, sy, g - 4, _turn_x(ux, uy)))
                break
            run0 += L
    found = shipinside._forms(gd, (LONG, SHORT, GATE, GUARD, SANDBAG) + TOWER)
    base = {e: gd.key(f) for e, f in found.items()}
    out, cells = [], set()
    rep = {'long': 0, 'short': 0, 'towers': 0, 'gate': None, 'guard': 0, 'sandbags': 0, 'buildings_cleared': 0,
           'things_cleared': 0, 'freeway_cleared': 0, 'doors_unlinked': 0, 'off_map': 0, 'missing': []}
    boxes = []
    for e, x, y, z, rz in placed:
        c = grid.get((int(x // 4096), int(y // 4096)))
        if c is None:
            rep['off_map'] += 1
            continue
        if e not in base:
            rep['missing'].append(e)
            continue
        ck = gd.key(c)
        out.append({'op': 'add', 'cell': ck, 'base': base[e], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz, 4)]})
        cells.add(ck)
        if e == LONG:
            rep['long'] += 1
            boxes.append((x, y, rz, -256.0, -175.0, 1792.0, 175.0))
        elif e == SHORT:
            rep['short'] += 1
            boxes.append((x, y, rz, -256.0, -175.0, 256.0, 175.0))
        elif e in TOWER:
            rep['towers'] += 1
            boxes.append((x, y, rz, -330.0, -330.0, 330.0, 330.0))
        elif e == GATE:
            rep['gate'] = {'road': gate[0], 'p': [round(x), round(y), round(z)]}
            boxes.append((x, y, rz, -286.0, -615.0, 286.0, 615.0))
        elif e == GUARD:
            rep['guard'] += 1
        else:
            rep['sandbags'] += 1
    # buildings the wall would cut, with what stood in them
    cat = cat if cat is not None else townbuild.load(gd, __import__('server').kits_folder())
    cut, crep = townbuild.crowding(gd, pr, world, cat, boxes, gap=60.0)
    out += cut
    gone = {o['ref'] for o in cut if o['op'] == 'remove'}
    rep['buildings_cleared'] = len(crep['buildings'])
    rep['doors_unlinked'] = crep['doors_unlinked']
    rep['things_cleared'] += crep['things']
    # loose things on the wall's line, and the freeway's decks over it
    reach = max(CLEAR, FREEWAY_CLEAR) + 600
    xs, ys = [p[0] for p in line], [p[1] for p in line]
    for cell in grid.values():
        ck = gd.key(cell)
        cx, cy = None, None
        c = pr.cells.get(ck)
        if not c:
            continue
        for rk, r in c['refs'].items():
            q = r.get('p')
            if rk in gone or not q or r.get('removed') or r.get('tel') or r.get('marker') or not r.get('base'):
                continue
            if not (min(xs) - reach <= q[0] <= max(xs) + reach and min(ys) - reach <= q[1] <= max(ys) + reach):
                continue
            d = _dist_to_line(line, q[0], q[1])
            if d > reach:
                continue
            b = r['base']
            try:
                e = (recordio.field(pr.records[b], 'EDID') if b.startswith('+') else gd.edid(gd.from_key(b))) or ''
            except (KeyError, ValueError):
                e = ''
            if 'Overpass' in e:
                if d <= FREEWAY_CLEAR:
                    out.append({'op': 'remove', 'cell': ck, 'ref': rk})
                    rep['freeway_cleared'] += 1
                    cells.add(ck)
                continue
            if d > CLEAR or any(w in e for w in KEEP_WORDS) or b in base.values():
                continue
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            rep['things_cleared'] += 1
            cells.add(ck)
    return out, rep, sorted(cells)
