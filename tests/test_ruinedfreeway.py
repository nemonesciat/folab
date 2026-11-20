"""ruinedfreeway: a freeway's line, broken by its street map at every junction, joined into runs end to end whichever way
each piece runs; a section's box laid along its line. (The whole step needs the game's overpass pieces: its first run on
Waikiki, 18 Nov 2026, stood 41 sections along H-1.)"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import ruinedfreeway  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


a = [(0, 0), (1000, 0)]
b = [(3000, 0), (1000, 0)]          # (runs the other way)
c = [(3000, 0), (3000, 2000)]
far = [(90000, 90000), (91000, 90000)]
runs = ruinedfreeway.join([a, b, c, far])
check('pieces meeting end to end are one run, the longest first', len(runs) == 2 and len(runs[0]) == 4, runs)
L = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(runs[0], runs[0][1:]))
check('… and nothing doubles back in it', abs(L - 5000) < 1e-6, L)
at, total = ruinedfreeway._along(runs[0])
check('a spot along a run is on it', at(1500) in ((1500.0, 0.0), (3000.0, 500.0)) or abs(total - 5000) < 1e-6)
pts = ruinedfreeway._box(0, 0, 0.0, 1.0, 10, 2)
check('a box laid along +y has its length on y', max(p[1] for p in pts) == 10 and max(p[0] for p in pts) == 2, pts)

# ---------- sections that cross or lie side by side overlapping ----------
A = (0, 0, 1.0, 0.0, ruinedfreeway.HALF, ruinedfreeway.WIDTH)
check('two decks crossing at an angle overlap', ruinedfreeway._overlap(A, (0, 0, 0.6, 0.8, ruinedfreeway.HALF, ruinedfreeway.WIDTH)))
check('the two carriageways with decks 1,500 apart overlap', ruinedfreeway._overlap(A, (0, 1500, 1.0, 0.0, ruinedfreeway.HALF, ruinedfreeway.WIDTH), gap=0.0))
check('one after another along the line do not', not ruinedfreeway._overlap(A, (ruinedfreeway.SPACING + 200, 0, 1.0, 0.0, ruinedfreeway.HALF, ruinedfreeway.WIDTH), gap=0.0))

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
