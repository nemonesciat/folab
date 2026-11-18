"""Bridges and overpasses for a world made from a map: the stretches OpenStreetMap draws as bridges (osmplace.layout's
'bridges', which laying the roads leaves out) built of the game's own highway pieces, as the Mojave's I-15 is.

    deck      OverpassRoad03 (3,050 long along its x, 1,610 wide, its top 117 over its origin), stood smaller for a city
              squeezed smaller than life (DECK_SCALE: the freeway, BY_NAME; streets narrower), one after another along
              the bridge's real line, end to end, each turned along it and pitched to the slope between its ends
    height    the road's own at each end of the bridge (the ground there, or the top of a road piece the roads step laid),
              in a straight line between, and never less than CLEAR over the ground under it (a street or a stream)
    pillars   OverpassPillar01 (its top 1,912 over its origin, its foot 512 under it) at each joint where the deck stands
              over PILLAR_FROM above the ground, sized to reach from the ground to under the deck

`plan` gives the ops (one Undo) and the cells they're in (their navmeshes are to be made again: people walk on bridges)."""
import math

import roadgen
import townbuild

DECK = 'OverpassRoad03'
PILLAR = 'OverpassPillar01'
DECK_LEN, DECK_TOP, DECK_BOTTOM = 3050.0, 117.0, 144.0
PILLAR_TOP = 1912.0
DECK_SCALE = 0.6            # (a freeway: its deck about the width of two of the roads step's pieces side by side)
STREET_SCALE = 0.42         # (a street over something)
FREEWAY_WORDS = ('freeway', 'highway', 'h-1', 'h-201', 'interstate', 'expressway')
CLEAR = 60.0                # the deck's underside at least this over the ground
PILLAR_FROM = 220.0
ROAD_TOP = 14.0             # (the roads step's pieces: their top over their origin)
MIN_LEN = 600.0


def _key(gd, edid):
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'STAT' and gd.edid(f) == edid:
            return gd.key(f)
    return None


def _along(line):
    """(total length, f(t) -> (x, y, dx, dy)) along a polyline."""
    segs, total = [], 0.0
    for a, b in zip(line, line[1:]):
        n = math.hypot(b[0] - a[0], b[1] - a[1])
        if n > 1e-6:
            segs.append((total, n, a, b))
            total += n

    def at(t):
        t = max(0.0, min(total, t))
        for s0, n, a, b in segs:
            if t <= s0 + n or (s0, n, a, b) == segs[-1]:
                u = (t - s0) / n
                return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, (b[0] - a[0]) / n, (b[1] - a[1]) / n
        return line[-1][0], line[-1][1], 1.0, 0.0
    return total, at


def _road_top(gd, pr, world, grid, x, y, ground):
    """The road's surface at an end of a bridge: the top of a road piece the roads step laid there, else the ground."""
    best = None
    c = grid.get((int(x // 4096), int(y // 4096)))
    cell = pr.cells.get(gd.key(c)) if c is not None else None
    for rk, r in (cell['refs'].items() if cell else ()):
        q = r.get('p')
        b = r.get('base') or ''
        if not q or r.get('removed') or b.startswith('+') or not rk.startswith('+'):
            continue
        d = math.hypot(q[0] - x, q[1] - y)
        if d < 700 and (gd.edid(gd.from_key(b)) or '').startswith('WastelandRoad') and (best is None or d < best[0]):
            best = (d, q[2] + ROAD_TOP)
    g = ground.at(x, y)
    if best:
        return best[1]
    return (g if g is not None else 0.0) + ROAD_TOP


def plan(gd, pr, world, bridges, progress=None):
    """(ops, report, cells): bridges [{'line', 'name', ...}] (osmplace.layout's) built."""
    grid = gd.grid(world)
    ground = roadgen.Ground(gd, pr, world)
    deck, pillar = _key(gd, DECK), _key(gd, PILLAR)
    if not deck or not pillar:
        raise ValueError('The game\'s highway pieces aren\'t in its files.')
    ops, cells = [], set()
    report = {'bridges': 0, 'decks': 0, 'pillars': 0, 'skipped': 0}

    def add(base, x, y, z, rx, ry, rz, s):
        c = grid.get((int(x // 4096), int(y // 4096)))
        if c is None:
            return False
        ops.append({'op': 'add', 'cell': gd.key(c), 'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), round(rx, 4), round(ry, 4), round(rz % math.tau, 4)],
                    's': round(s, 3)})
        cells.add(gd.key(c))
        return True
    for k, br in enumerate(bridges):
        if progress:
            progress('Building the bridges', k, len(bridges))
        line = br['line']
        L, at = _along(line)
        if L < MIN_LEN:
            report['skipped'] += 1
            continue
        big = any(w_ in (br.get('name') or '').lower() for w_ in FREEWAY_WORDS)
        sc = DECK_SCALE if big else STREET_SCALE
        n = max(1, int(round(L / (DECK_LEN * sc))))
        s = L / n / DECK_LEN                       # (end to end exactly: the pieces a touch longer or shorter)
        xa, ya, _a, _b = at(0.0)
        xb, yb, _c, _d = at(L)
        za = _road_top(gd, pr, world, grid, xa, ya, ground)
        zb = _road_top(gd, pr, world, grid, xb, yb, ground)

        def top(t):
            z = za + (zb - za) * t / L
            x, y, _u, _v = at(t)
            g = ground.at(x, y)
            return max(z, (g if g is not None else z) + CLEAR + DECK_BOTTOM * s + DECK_TOP * s) if 0.0 < t < L else z
        # (the deck's tops at the joints, and straight between)
        joints = [top(i * L / n) for i in range(n + 1)]
        for i in range(n):
            t0, t1 = i * L / n, (i + 1) * L / n
            x, y, dx, dy = at((t0 + t1) / 2)
            rz = math.atan2(-dy, dx)                # (its own x along the bridge)
            z0, z1 = joints[i], joints[i + 1]
            pitch = math.atan2(z1 - z0, t1 - t0)    # (+x end up for a positive turn about its own y: rooftops.PITCH_SIGN)
            zc = (z0 + z1) / 2 - DECK_TOP * s
            if add(deck, x, y, zc, 0.0, pitch, rz, s):
                report['decks'] += 1
        for i in range(1, n):
            t = i * L / n
            x, y, dx, dy = at(t)
            g = ground.at(x, y)
            if g is None:
                continue
            under = joints[i] - (DECK_TOP + DECK_BOTTOM) * s
            if under - g < PILLAR_FROM:
                continue
            ps = (under - g) / PILLAR_TOP
            if add(pillar, x, y, g, 0.0, 0.0, math.atan2(-dy, dx), max(0.15, ps)):
                report['pillars'] += 1
        report['bridges'] += 1
    return ops, report, sorted(cells)
