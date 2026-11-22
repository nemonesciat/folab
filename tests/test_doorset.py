"""FOLab's own doors (doorset) and the swap's arithmetic (doorswap.spot): every piece builds and passes the model check,
has one solid, its pictures a power of two; a door stands where its doorway is in its building, turned so its -y is out."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))

import doorset  # noqa: E402
import doorswap  # noqa: E402
import modelsets  # noqa: E402
import nifmake  # noqa: E402

failed = []


def ok(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        failed.append(what)


modelsets._all_sets()
for name, make in doorset.TEXTURES.items():
    c = make()
    ok(c.w & (c.w - 1) == 0 and c.h & (c.h - 1) == 0, '%s is %dx%d, a power of two each way' % (name, c.w, c.h))
for piece in doorset.PIECES:
    m = modelsets.build(piece)
    ok(not nifmake.check(m['nif'], m['shapes'], m['solids']), piece + ' passes the model check')
    ok(len(m['solids']) == 1, piece + ' has one solid (the box over its doorway)')
    ok(m['triangles'] < 2000, '%s is light (%d triangles)' % (piece, m['triangles']))
    ok(all(not s['tex'].lower().endswith('trim_koa.dds') or max(s['p'][1::3]) - min(s['p'][1::3]) < 60 for s in m['shapes']), piece + ': no drawn face over the doorway but the leaves')
for b, ways in doorset.DOORWAYS.items():
    for w in ways:
        ok(w[0] in doorset.PIECES, '%s doorway names a piece (%s)' % (b, w[0]))
for e, piece in doorset.LIFTS.items():
    m = modelsets.build(piece)
    ok(m['box'][2] == -80, '%s keeps the game lift door\'s frame (origin 80 over the floor)' % piece)
# a doorway in a building turned and scaled: its spot, and the door's -y pointing out of the building
bp = [1000.0, 2000.0, 50.0, 0.0, 0.0, 0.7]
p = doorswap.spot(bp, 0.8, 0.0, 400.0, 10.0, 0.0)
lx, ly = doorswap._local(p[0], p[1], bp, 0.8)
ok(abs(lx) < 0.01 and abs(ly - 400) < 0.01 and abs(p[2] - 58.0) < 0.01, 'the spot goes back into the building\'s frame')
out = (-math.sin(p[5]), -math.cos(p[5]))
away = (p[0] - bp[0], p[1] - bp[1])
ok(out[0] * away[0] + out[1] * away[1] > 0, 'a door\'s -y faces out of its building')
print('%d failed' % len(failed))
sys.exit(1 if failed else 0)
