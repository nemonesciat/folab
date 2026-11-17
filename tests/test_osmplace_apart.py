"""Road pieces that lie over one another are lifted a hair apart (osmplace.apart), so their surfaces don't flicker."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import osmplace  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
kit = roadgen.pieces(gd)
road = kit['a']
tire = gd.key(next(f for f, (i, r) in gd.forms.items() if gd.edid(f) == 'Tire01Static'))
add = lambda base, x, y, z, rz=0.0: {'op': 'add', 'cell': 'c', 'base': base, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1}
ops = [add(road, 0, 0, 100.0), add(road, 300, 0, 100.0), add(road, 0, 100, 100.0, 1.5708), add(road, 5000, 0, 100.0), add(road, 0, 0, 140.0),
       add(tire, 0, 0, 100.0), {'op': 'land', 'cell': 'c'}]
n = osmplace.apart(gd, ops)
z = [o['p'][2] for o in ops if o['op'] == 'add']
check('the first stays where it was laid', z[0] == 100.0)
check('one over it at the same height is lifted clear', z[1] == 100.0 + osmplace.LIFT)
check('one crossing both is lifted clear of both', abs(z[2] - z[0]) >= osmplace.LIFT - 0.01 and abs(z[2] - z[1]) >= osmplace.LIFT - 0.01, z[2])
check('one far off is left', z[3] == 100.0)
check('one well above already is left', z[4] == 140.0)
check('a thing that is no road piece is left', z[5] == 100.0)
check('and it says how many it lifted', n == 2, n)
