"""The first Ko'olau cave inside (kocave.py), the hole check on cave rock (kitplan.Walk.open_edges), and a door into the
hillside outside (rockdoor.py: its sums, and where on a slope it goes). From the game's files; nothing goes near the game."""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import kitdress as D
import kitindex as K
import kitplan as P
import kocave
import rockdoor as R


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


# ---------- a door into the hill: the sums ----------
for ang in (0.0, 0.7, 2.0, 4.1):
    ox, oy = math.cos(ang), math.sin(ang)
    x, y = R._world(ox, oy, 100.0, 200.0, 300.0, -40.0)
    lx, ly = R._local(ox, oy, 100.0, 200.0, x, y)
    rz = R.yaw_of(ox, oy)
    # (a model's own +x, turned rz as the game turns it: clockwise from above)
    wx, wy = math.cos(rz), -math.sin(rz)
    h = R.heading(ox, oy)
    if not (abs(lx - 300) < 1e-6 and abs(ly + 40) < 1e-6 and abs(wx - ox) < 1e-9 and abs(wy - oy) < 1e-9 and abs(math.sin(h) - ox) < 1e-9 and abs(math.cos(h) - oy) < 1e-9):
        check('local and world, the frame turned to face out, an actor facing out (%.1f)' % ang, False)
        break
else:
    check('local and world, the frame turned to face out, an actor facing out', True)


class Slope:
    """Ground falling to the north at 40 degrees from a ridge along y = 0, flat on top."""

    def at(self, x, y):
        return 1000.0 - max(0.0, y) * math.tan(math.radians(40.0))


got = R.spot(Slope(), 0.0, -50.0, toward=(0.0, 1.0))
check('a door goes into the slope below the trail, facing down it', got and got[4] > 0.95 and got[1] > 0 and 30 < got[5] < 50, str(got))
got = R.spot(Slope(), 0.0, 1500.0, up=True)
check('… or above a trail, facing back down to it', got and got[1] < 1500.0 and got[4] > 0.95, str(got))
check('… and nowhere on flat ground', R.spot(type('Flat', (), {'at': lambda s, x, y: 500.0})(), 0.0, 0.0) is None)
a = R.arrival(0.0, 0.0, 100.0, 0.0, 1.0)
check('you come out in front of the door, facing out', a[1] > 100 and abs(a[5]) < 1e-6)

# ---------- the cave inside ----------
G = gamedata.GameData()
kits = K.build(G)
sv = D.survey(G, kits, only={kocave.KIT})
store, cache = {}, {}
got = P.filled(G, kits, kocave.KIT, 8, 8, 1, store, cache)
ts = store[('fill', kocave.KIT)]
w = P.walk_check(G, ts, got[0], got[1], cache)
check('a filled cave walks with no hole: floor under a low overhang isn\'t one (it was 33)', not w['edges'], len(w['edges']))
g = kocave.make(G, kits, 8, 6, 1, store, cache, sv)
check('a cave with a way out', g is not None)
if g:
    m, d = g['exit']
    exits = [it for it in g['items'] if it.what == 'exit']
    check('… at the kit\'s cave mouth, opening on nothing beyond', G.edid(G.from_key(m.key)) == kocave.MOUTH and
          (m.cell[0] + P.DX[d][0], m.cell[1] + P.DX[d][1]) not in {q.cell[:2] for q in g['made']})
    check('… one door, the game\'s own', len(exits) == 1 and G.forms[G.from_key(exits[0].key)][1].tag == 'DOOR', str([G.edid(G.from_key(e.key)) for e in exits]))
    check('… lit from the game\'s own caves', sum(1 for it in g['items'] if it.what == 'light') >= len(g['made']) // 8)
    check('… walked with everything in: no way out, no hole, squares nobody reaches left out', not g['walk']['escaped'] and not g['walk']['edges'] and
          not {q.cell for q in g['made']} & set(g['walk']['missing']), len(g['walk']['missing']))
    out = kocave.ops(G, kits, 8, 6, 1, store, cache, sv)
    check('as changes for a mod: pieces, things, the way out marked', out.get('ops') and sum(1 for o in out['ops'] if o.get('exit')) == 1 and len(out['inside']) == 6)
