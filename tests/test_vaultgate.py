"""vaultgate.guardrails: a leg's rails stop short of its turns (23 Nov 2026: one run round the whole zig-zag crossed the path
at every turn-back). Plain geometry, no game files."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import vaultgate  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


pts = [(x * 48.0, 0.0) for x in range(0, 60)]            # (a straight leg 2,832 long along +x, level)
zs = [0.0] * len(pts)
whole = vaultgate.guardrails(pts, zs)
cut = vaultgate.guardrails(pts, zs, start=vaultgate.TURN_GAP, stop=vaultgate.TURN_GAP)
check('a leg gets rails', len(whole) > 5, len(whole))
ends = [min(math.dist((r[0], 0), pts[0]), math.dist((r[0], 0), pts[-1])) for r in cut]
check('none within TURN_GAP of a turn (less half a rail)', all(e >= vaultgate.TURN_GAP for e in ends), min(ends) if ends else None)
check('fewer rails than the whole run', 0 < len(cut) < len(whole), (len(cut), len(whole)))
check('rails stand on the open side', all(r[1] < 0 for r in cut))
print('%d of %d' % (sum(OK), len(OK)))
