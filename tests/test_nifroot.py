"""A model's root node: the game draws a placed thing without its root's own turn, shift and scale (the placed thing's
position takes their place). McCarran's wallLong has a quarter turn on its root and the opposite on its shapes; read with
both it ran along y, and on 19 Nov 2026 Waikiki's wall was turned across its line in game to match. The game's own
placements of it stand 2048 apart along their x, and its record's bounds say x."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import hkshape
import library
import nif

gd = gamedata.GameData(plugins=['FalloutNV.esm'])
fails = []


def check(what, ok, got=''):
    print(('ok   ' if ok else 'FAIL ') + what, got if not ok else '')
    if not ok:
        fails.append(what)


data = gd.read_file('meshes\\architecture\\McCarran\\McMarranWallsDES\\wallLong.NIF')
b = library.bounds_of(data)
check('wallLong drawn along its x, as the game draws it', b[0] < -200 and b[3] > 1700 and b[4] - b[1] < 400, b)
pts = [v for s in hkshape.collision_shapes(data) for v in [s['v'][k:k + 3] for k in range(0, len(s['v']), 3)]]
if pts:
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    check('… and its collision too', max(xs) - min(xs) > 1500 and max(ys) - min(ys) < 600, (min(xs), max(xs), min(ys), max(ys)))
w = [v for s in nif.mesh_from_nif(data, placed=False) for v in s['p'][1::3]]
check('read as a file (root kept) it still runs along y', max(w) > 1700, max(w))
# the game's own placements: neighbours along x
f = next(f for f in gd.forms if gd.edid(f) == 'NVMcCarranWallReg02')
check('its record says x', gd.describe(f)[0] == 'STAT')
sys.exit(1 if fails else 0)
