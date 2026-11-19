"""borderwall: the wall to Ground Zero laid along its line with no gap anyone could walk through, every piece on or in
the ground (none hangs), short pieces and towers where the ground climbs, the gate on its road with a tower each side,
a breakwater into shallow water and none in the deep. Pure layout on made-up ground; the game's pieces aren't needed."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import borderwall as BW  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


EXTENT = {BW.LONG: (-256, 1792), BW.SHORT: (-256, 256), BW.GATE: (-615, 615)}
for t in BW.TOWER:
    EXTENT[t] = (-330, 330)


def covered(line, placed):
    """For each leg: the stretches along it that pieces cover (a piece counts on a leg if it lies on that leg's line)."""
    legs = []
    for a, b in zip(line, line[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        spans = []
        for e, x, y, z, rz in placed:
            if e not in EXTENT:
                continue
            off = abs((x - a[0]) * -uy + (y - a[1]) * ux)
            if off > 40:
                continue
            at = (x - a[0]) * ux + (y - a[1]) * uy
            lo, hi = EXTENT[e]
            if e in BW.TOWER or e == BW.GATE:
                spans.append((at + lo, at + hi))
            else:
                # (the piece's own y runs along the leg: its mesh, whatever its record's bounds say)
                px, py = math.sin(rz), math.cos(rz)
                sgn = 1 if px * ux + py * uy > 0 else -1
                spans.append((at + lo * sgn, at + hi * sgn) if sgn > 0 else (at - hi, at - lo))
        spans.sort()
        reach, gaps = 0.0, []
        for s0, s1 in spans:
            if s0 > reach + 1.0:
                gaps.append((round(reach), round(s0)))
            reach = max(reach, s1)
        if reach < L - 1.0:
            gaps.append((round(reach), round(L)))
        legs.append(gaps)
    return legs


# ---------- flat ground, a bend, a gate ----------
line = [(0.0, 0.0), (20000.0, 0.0), (20000.0, 15000.0)]
flat = lambda x, y: 100.0
placed = BW.plan(line, flat, gate_t=26000.0)
gaps = covered(line, placed)
check('flat ground: no gap along either leg', all(not g for g in gaps), gaps)
check('flat ground: mostly long pieces', sum(e == BW.LONG for e, *_ in placed) >= 12, sum(e == BW.LONG for e, *_ in placed))
gates = [p for p in placed if p[0] == BW.GATE]
check('one gate', len(gates) == 1, gates)
g = gates[0]
check('… where it was asked for', abs(g[1] - 20000) < 1 and abs(g[2] - 6000) < 1, g)
near = [p for p in placed if p[0] in BW.TOWER and math.hypot(p[1] - g[1], p[2] - g[2]) < BW.GATE_LEN / 2 + BW.TOWER_LEN]
check('… a tower each side of it', len(near) == 2, len(near))
check('a tower at the bend', any(p[0] in BW.TOWER and math.hypot(p[1] - 20000, p[2]) < 1 for p in placed))
check('… and at both ends', any(p[0] in BW.TOWER and math.hypot(p[1], p[2]) < 1 for p in placed)
      and any(p[0] in BW.TOWER and math.hypot(p[1] - 20000, p[2] - 15000) < 1 for p in placed))
bottoms = [(p[3] - BW.LOW) if p[0] in (BW.LONG, BW.SHORT) else p[3] for p in placed]
check('every piece reaches into the ground', all(b <= 100.0 for b in bottoms), max(bottoms))
pieces = [p for p in placed if p[0] in (BW.LONG, BW.SHORT)]
turns = {round(p[4], 3) for p in pieces if abs(p[2]) < 1}
check('pieces on the first leg lie along it (their y along +x)', turns == {round(BW._turn_y(1, 0), 3)}, turns)
turns = {round(p[4], 3) for p in pieces if abs(p[1] - 20000) < 1}
check('… and on the second along +y', turns == {round(BW._turn_y(0, 1), 3)}, turns)

# ---------- climbing ground ----------
slope = lambda x, y: x * 0.5            # (1 in 2 along the leg)
line2 = [(0.0, 0.0), (12000.0, 0.0)]
placed2 = BW.plan(line2, slope)
gaps2 = covered(line2, placed2)
check('steep ground: no gap', not gaps2[0], gaps2)
check('steep ground: no long pieces', not any(p[0] == BW.LONG for p in placed2))
low_ok = True
for e, x, y, z, rz in placed2:
    if e in (BW.LONG, BW.SHORT):
        lo, hi = EXTENT[e]
        foot = min(slope(x + lo, 0), slope(x + hi, 0))
        low_ok &= z - BW.LOW <= foot
check('steep ground: no piece hangs at its low end', low_ok)
gentle = lambda x, y: x * 0.03
placed3 = BW.plan(line2, gentle)
check('gentle ground: long pieces', any(p[0] == BW.LONG for p in placed3))

# ---------- into the sea ----------
sea = lambda x, y: 50.0 - x * 0.2        # (deeper than DEEP past x = 2850)
placed4 = BW.plan([(0.0, 0.0), (8000.0, 0.0)], sea)
far = max(p[1] for p in placed4 if p[0] in (BW.LONG, BW.SHORT))
check('a breakwater runs into shallow water', far > 1500, far)
check('… and stops before the deep', all(sea(p[1] + (EXTENT[p[0]][0]), 0) > -BW.DEEP - 600 for p in placed4 if p[0] in (BW.LONG, BW.SHORT)))

# ---------- the gate's road ----------
roads = [('Some Lane', [(19000.0, 3000.0), (21000.0, 3000.0)]), ('Dillingham Boulevard', [(19000.0, 7000.0), (21000.0, 7500.0)])]
c = BW.crossing(line, roads)
check('the gate goes where the harbour road crosses', c and c[0] == 'Dillingham Boulevard' and abs(c[1] - 27250) < 5, c)
check('no such road: no gate', BW.crossing(line, [('Some Lane', roads[0][1])]) is None)

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
