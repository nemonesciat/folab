"""A ruined elevated freeway along a real map's freeway bridges (ruinedfreeway.py), as the Mojave stands the Strip's.

On Waikiki the street map has H-1 (the Lunalilo Freeway) cross 17 bridges, but the world's heights were squeezed when it was
made: the ground under every one is near flat, and the freeway's road runs straight through on the ground. A working
overpass would need ramps kilometres long. So the freeway stands on as the old one in the air over it, broken (the user's
choice, 18 Nov 2026): the game's OverpassSectionLo01 (5,050 long, its deck 1,800 to 2,144 over its origin, pillars at its
middle and 1,200 each side down to -512), chained along each long bridge stretch as the Mojave chains them (SPACING apart,
one height a chain, the origin some way under the land: `UNDER`), an OverpassRampLo01 at an end that still stands, a span
fallen now and then (`FALL_EVERY`) with its rubble on the ground below, and some ends broken off.

A section is left out where one of its pillars would stand in a building or a landmark, where a building under it reaches
its deck, or over the sea; a chain so broken stands as pieces, which a ruin may. The road under is left as it is.

ops(gd, pr, world, lines, seed=1, cat=None, placed=None) -> (ops, report). lines: [polyline [(x, y)...]], the freeway's
line joined up (join); placed: middles of sections stood already, kept APART from (a dual carriageway's other line)."""
import math
import random

import roadgen

SECTION, RAMP, CHUNK = 'OverpassSectionLo01', 'OverpassRampLo01', 'RoadOverpassCollapsedChunk01'
HALF = 2525.0               # a section's half length
WIDTH = 880.0               # and half its width
SPACING = 4950.0            # one section's middle to the next (the Mojave's chains: 4,600 to 5,150)
PILLARS = (-1600.0, 0.0, 1600.0)    # along a section (and a ramp), where its pillars stand (read from the models: -1923..-1283,
#                                     -320..320, 1268..1908 along, -512..512 across)
PILLAR_HALF = 320.0         # a pillar's half length along the deck
PILLAR_ACROSS = 512.0       # and its half width across it
CLEAR = 48.0                # kept clear round a pillar's foot
DECK_UNDER = 1750.0         # the underside of the deck over the origin
UNDER = 700.0               # the origin under the land's middle along a chain (the Mojave's: 150 to 1,160)
DEEP = 400.0                # but never more than this under its lowest ground, or a pillar hangs (they reach 512 down)
FALL_EVERY = 6              # about one span in this many has fallen
BEND = 300.0                # a line further than this off a section's straight middle bends too much for one: a gap
APART = 1200.0              # a section this near another stands already (the freeway's other carriageway): left out
BROKEN = 0.5                # the chance an end has no ramp: broken off in the air
SHORTEST = 3000.0           # a stretch shorter than this has no section


def _along(line):
    segs, total = [], 0.0
    for a, b in zip(line, line[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > 0:
            segs.append((total, a, b, L))
            total += L

    def at(s):
        s = max(0.0, min(total, s))
        for s0, a, b, L in segs:
            if s <= s0 + L:
                t = (s - s0) / L
                return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        return tuple(line[-1])
    return at, total


def _overlap(a, b, gap=64.0):
    """Two boxes on the ground ((x, y, dx, dy, half length, half width), laid along (dx, dy)) overlap, or come within gap:
    the separating axis test over both boxes' four edges."""
    def corners(q):
        x, y, dx, dy, hl, hw = q
        return [(x + dx * i * hl - dy * j * hw, y + dy * i * hl + dx * j * hw) for i in (-1, 1) for j in (-1, 1)]
    ca, cb = corners(a), corners(b)
    for x, y, dx, dy, hl, hw in (a, b):
        for ax, ay in ((dx, dy), (-dy, dx)):
            pa = [px * ax + py * ay for px, py in ca]
            pb = [px * ax + py * ay for px, py in cb]
            if max(pa) + gap <= min(pb) or max(pb) + gap <= min(pa):
                return False
    return True


def _feet(cx, cy, dx, dy):
    """Points over each pillar's foot of a section (or ramp) at (cx, cy) laid along (dx, dy): its corners, middles and middle."""
    return [p for px in PILLARS for p in _box(cx + dx * px, cy + dy * px, dx, dy, PILLAR_HALF + CLEAR, PILLAR_ACROSS + CLEAR)]


def _box(cx, cy, dx, dy, hx, hy):
    """Points over a box laid along (dx, dy), half sizes hx, hy: its corners, middles and middle."""
    nx, ny = -dy, dx
    return [(cx + dx * a * hx + nx * b * hy, cy + dy * a * hx + ny * b * hy) for a in (-1, 0, 1) for b in (-1, 0, 1)]


def ops(gd, pr, world, lines, seed=1, cat=None, placed=None):
    import landmarks
    import osmdress
    import townbuild
    rng = random.Random(seed * 7907 + 31)
    grid = gd.grid(world)
    base = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'STAT' and gd.edid(f) in (SECTION, RAMP, CHUNK):
            base[gd.edid(f)] = gd.key(f)
    if SECTION not in base:
        raise ValueError('The game has no %s here.' % SECTION)
    if cat is None:
        import server
        cat = townbuild.load(gd, server.kits_folder())
    stands = osmdress.standing(gd, pr, world, cat)
    built = osmdress._Stands(stands, margin=CLEAR)
    tall = [(x, y, rz, b['box'], z) for b, x, y, z, rz in stands]
    marks = list(landmarks.standing(gd, pr, world))
    g = roadgen.Ground(gd, pr, world)

    def in_mark(x, y):
        for bx, by, rz, x0, y0, x1, y1 in marks:
            if abs(x - bx) > 8000 or abs(y - by) > 8000:
                continue
            c, s = math.cos(-rz), math.sin(-rz)
            lx, ly = (x - bx) * c + (y - by) * s, -(x - bx) * s + (y - by) * c
            if x0 - CLEAR <= lx <= x1 + CLEAR and y0 - CLEAR <= ly <= y1 + CLEAR:
                return True
        return False

    def pillar_hits(cx, cy, dx, dy):
        return any(built.hit(x, y) or in_mark(x, y) for x, y in _feet(cx, cy, dx, dy))

    def reaches(cx, cy, dx, dy, deck):
        """A building under this section whose top reaches the deck."""
        for x, y, rz, box, z in tall:
            if abs(x - cx) > HALF + 2000 or abs(y - cy) > HALF + 2000:
                continue
            ax, ay = x - cx, y - cy
            along, across = ax * dx + ay * dy, -ax * dy + ay * dx
            r = math.hypot(max(abs(box[0]), abs(box[3])), max(abs(box[1]), abs(box[4])))
            if abs(along) <= HALF + r and abs(across) <= WIDTH + r and z + box[5] >= deck:
                return True
        return False

    out, report = [], {'stretches': 0, 'sections': 0, 'ramps': 0, 'fallen': 0, 'broken_ends': 0, 'left_out': {}}
    placed = placed if placed is not None else []          # (middles of sections stood: a line's twin keeps off them)

    def leave(why):
        report['left_out'][why] = report['left_out'].get(why, 0) + 1

    def put(edid, x, y, z, rot, s=1.0):
        cell = grid.get((int(x // 4096), int(y // 4096)))
        if cell is None:
            return False
        out.append({'op': 'add', 'cell': gd.key(cell), 'base': base[edid], 'p': [round(x, 1), round(y, 1), round(z, 1)] + [round(v, 4) for v in rot],
                    's': round(s, 3)})
        return True

    for line in lines:
        at, total = _along(line)
        if total < SHORTEST:
            continue
        report['stretches'] += 1
        n = max(1, int((total + SPACING - 2 * HALF) // SPACING))
        start = (total - (n - 1) * SPACING) / 2
        spans = []
        for k in range(n):
            s = start + k * SPACING
            a, b = at(s - HALF), at(s + HALF)
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1.0
            dx, dy = dx / ln, dy / ln
            cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            m = at(s)
            spans.append((cx, cy, dx, dy, math.hypot(m[0] - cx, m[1] - cy)))
        lows = [gz for cx, cy, dx, dy, _b in spans for gz in (g.at(px, py) for px, py in _box(cx, cy, dx, dy, HALF, WIDTH)) if gz is not None]
        if not lows:
            continue
        lows.sort()
        z = min(lows[len(lows) // 2] - UNDER, lows[0] + DEEP)
        z = math.floor(z / 8) * 8
        deck = z + DECK_UNDER
        stood = []
        for k, (cx, cy, dx, dy, bend) in enumerate(spans):
            rot = roadgen.turn_along(dx, dy, 0.0)
            if bend > BEND:
                leave('the line bends too much')
                stood.append(False)
                continue
            if any(math.hypot(px[0] - cx, px[1] - cy) < APART for px in placed):
                leave('the other carriageway has one')
                stood.append(False)
                continue
            if any(_overlap((cx, cy, dx, dy, HALF, WIDTH), q) for q in placed):
                leave('it crosses another section')
                stood.append(False)
                continue
            if 0 < k < n - 1 and rng.random() < 1.0 / FALL_EVERY:
                for _ in range(3):              # (the span on the ground under where it stood, in pieces)
                    t, u = rng.uniform(-0.7, 0.7) * HALF, rng.uniform(-0.6, 0.6) * WIDTH
                    x, y = cx + dx * t - dy * u, cy + dy * t + dx * u
                    gz = g.at(x, y)
                    if gz is not None and CHUNK in base:
                        put(CHUNK, x, y, gz - 20, (rot[0], rot[1], rot[2] + rng.uniform(-0.6, 0.6)), 2.0)
                report['fallen'] += 1
                stood.append(False)
                continue
            mid = g.at(cx, cy)
            if mid is None or mid < 8:
                leave('over the sea')
                stood.append(False)
                continue
            if pillar_hits(cx, cy, dx, dy):
                leave('a pillar in a building or landmark')
                stood.append(False)
                continue
            if reaches(cx, cy, dx, dy, deck):
                leave('a building reaches the deck')
                stood.append(False)
                continue
            put(SECTION, cx, cy, z, rot)
            placed.append((cx, cy, dx, dy, HALF, WIDTH))
            report['sections'] += 1
            stood.append(True)
        # the ends: a ramp on where the chain's last section stands, else broken off in the air
        for k, sign in ((0, -1), (len(spans) - 1, 1)):
            if not stood[k] or RAMP not in base:
                continue
            if rng.random() < BROKEN:
                report['broken_ends'] += 1
                continue
            cx, cy, dx, dy, _b = spans[k]
            ddx, ddy = dx * sign, dy * sign
            x, y = cx + ddx * (HALF + 2522.0), cy + ddy * (HALF + 2522.0)
            if pillar_hits(x, y, ddx, ddy):
                report['broken_ends'] += 1
                continue
            ramp = (x + ddx * (4291.0 - 2522.0) / 2, y + ddy * (4291.0 - 2522.0) / 2, ddx, ddy, (4291.0 + 2522.0) / 2, WIDTH)
            if any(_overlap(ramp, q) for q in placed):
                report['broken_ends'] += 1
                continue
            put(RAMP, x, y, z, roadgen.turn_along(ddx, ddy, 0.0))
            placed.append(ramp)
            report['ramps'] += 1
    return out, report


def join(lines, near=64.0):
    """Polylines joined end to end where one ends where another starts (a street map breaks a freeway at every junction),
    each turned as it needs; the longest first."""
    pool = [list(map(tuple, l)) for l in lines if len(l) >= 2]
    out = []
    while pool:
        cur = pool.pop(0)
        grown = True
        while grown:
            grown = False
            for i, l in enumerate(pool):
                for a, b, f in ((cur[-1], l[0], lambda c, l: c + l[1:]), (cur[-1], l[-1], lambda c, l: c + l[::-1][1:]),
                                (cur[0], l[-1], lambda c, l: l + c[1:]), (cur[0], l[0], lambda c, l: l[::-1] + c[1:])):
                    if math.hypot(a[0] - b[0], a[1] - b[1]) <= near:
                        cur = f(cur, l)
                        pool.pop(i)
                        grown = True
                        break
                if grown:
                    break
        out.append(cur)
    return sorted(out, key=lambda l: -sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(l, l[1:])))


def clear(gd, pr, world, cat=None):
    """(ops, report): for every overpass section and ramp the mod stands: taken out if a pillar would stand in a building or a
    landmark; else whatever of the mod's own stands in a pillar's foot (a car, junk, rubble, a plant; never a road piece, a
    building or another piece of the freeway) taken out. The user's look, 18 Nov 2026: a car through a pillar."""
    import landmarks
    import osmdress
    import roadbed
    import townbuild
    if cat is None:
        import server
        cat = townbuild.load(gd, server.kits_folder())
    grid = gd.grid(world)
    city = {gd.key(c) for c in grid.values()}
    mine = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'STAT' and gd.edid(f) in (SECTION, RAMP, CHUNK):
            mine[gd.key(f)] = gd.edid(f)
    keep = set(roadbed._flat_bases(gd)) | set(roadbed._slab_bases(gd)) | {b['key'] for b in cat} | set(mine)
    built = osmdress._Stands(osmdress.standing(gd, pr, world, cat), margin=CLEAR)
    marks = list(landmarks.standing(gd, pr, world))

    def in_mark(x, y):
        for bx, by, rz, x0, y0, x1, y1 in marks:
            if abs(x - bx) > 8000 or abs(y - by) > 8000:
                continue
            c, s = math.cos(-rz), math.sin(-rz)
            lx, ly = (x - bx) * c + (y - by) * s, -(x - bx) * s + (y - by) * c
            if x0 - CLEAR <= lx <= x1 + CLEAR and y0 - CLEAR <= ly <= y1 + CLEAR:
                return True
        return False
    pieces, things = [], {}
    for ck in city:
        for rk, r in pr.cells.get(ck, {}).get('refs', {}).items():
            p, b = r.get('p'), r.get('base')
            if not p or not b or r.get('removed'):
                continue
            if mine.get(b) in (SECTION, RAMP):
                pieces.append((ck, rk, p, mine[b]))
            elif rk.startswith('+') and b not in keep:
                things.setdefault((int(p[0] // 1024), int(p[1] // 1024)), []).append((ck, rk, p, b))
    ops, gone, cleared, crossed = [], 0, 0, 0
    reach = {}
    kept = []
    for ck, rk, p, kind in sorted(pieces, key=lambda t: t[1]):      # (in the order they were made: the later of two crossing goes)
        dx, dy = math.cos(-p[5]), math.sin(-p[5])          # (the piece's own +x in the world: _local's inverse)
        feet = _feet(p[0], p[1], dx, dy)
        if any(built.hit(x, y) or in_mark(x, y) for x, y in feet):
            ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
            gone += 1
            continue
        box = (p[0], p[1], dx, dy, HALF, WIDTH) if kind == SECTION else             (p[0] + dx * (4291.0 - 2522.0) / 2, p[1] + dy * (4291.0 - 2522.0) / 2, dx, dy, (4291.0 + 2522.0) / 2, WIDTH)
        if any(_overlap(box, q, gap=0.0) for q in kept):
            ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
            crossed += 1
            continue
        kept.append(box)
        for px in PILLARS:
            fx, fy = p[0] + dx * px, p[1] + dy * px
            for a in range(int(fx // 1024) - 1, int(fx // 1024) + 2):
                for b_ in range(int(fy // 1024) - 1, int(fy // 1024) + 2):
                    for tck, trk, tp, tb in things.get((a, b_), ()):
                        if trk in reach:
                            continue
                        o = None
                        if not tb.startswith(('+', '$')):
                            try:
                                o = townbuild.obnd(gd, tb)
                            except Exception:
                                o = None
                        r = (math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * 0.7 if o else 64.0)
                        ax, ay = tp[0] - fx, tp[1] - fy
                        along, across = ax * dx + ay * dy, -ax * dy + ay * dx
                        if abs(along) <= PILLAR_HALF + CLEAR + r and abs(across) <= PILLAR_ACROSS + CLEAR + r:
                            reach[trk] = tck
    for trk, tck in reach.items():
        ops.append({'op': 'remove', 'cell': tck, 'ref': trk})
        cleared += 1
    return ops, {'pieces': len(pieces), 'pieces_taken_out': gone, 'crossing_taken_out': crossed, 'things_cleared': cleared}
