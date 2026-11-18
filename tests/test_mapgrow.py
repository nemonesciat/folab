"""mapgrow: a world made from a height file grown in place. The sums that keep old cells where they were, the seam (new
ground eased to the old, nothing old moved, slopes the game can store), and what later steps keep to."""
import array
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
import mapgrow  # noqa: E402
import mapscale as MS  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


SIDE = {'W': 10, 'H': 6, 'x0': -5, 'y0': -3, 'col0': 500.0, 'row0': 300.0, 'upx': 400.0, 'upy': 430.0, 'px_w': 3601, 'px_h': 3601,
        'geo': {'kind': 'deg', 'x0': -158.0, 'y0': 22.0, 'dx': 1 / 3600.0, 'dy': 1 / 3600.0}}


def game_xy(s, col, row):
    return (s['x0'] * 4096 + (col - s['col0']) * s['upx'], (s['y0'] + s['H']) * 4096 - (row - s['row0']) * s['upy'])


def test_side():
    pcx, pcy = 4096 / SIDE['upx'], 4096 / SIDE['upy']
    # a box three cells west, two east, one north and four south of the world's
    c0, r0 = SIDE['col0'] - 3 * pcx - 1, SIDE['row0'] - 1 * pcy - 1
    c1, r1 = SIDE['col0'] + (SIDE['W'] + 2) * pcx + 1, SIDE['row0'] + (SIDE['H'] + 4) * pcy + 1
    g = SIDE['geo']
    box = (g['y0'] - r1 * g['dy'], g['x0'] + c0 * g['dx'], g['y0'] - r0 * g['dy'], g['x0'] + c1 * g['dx'])
    new, added = mapgrow.grown_side(SIDE, box)
    check('cells added each way', added == (3, 2, 1, 4), added)
    check('size', (new['W'], new['H']) == (15, 11))
    check('south-west cell', (new['x0'], new['y0']) == (-8, -7))
    for col, row in ((500.0, 300.0), (731.5, 402.25), (2000.0, 1000.0)):
        a, b = game_xy(SIDE, col, row), game_xy(new, col, row)
        check('a pixel stays where it was (%s, %s)' % (col, row), abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6, (a, b))
    old = mapgrow.cells_of(SIDE)
    check('every old cell is still a cell', old <= mapgrow.cells_of(new))
    same, none = mapgrow.grown_side(SIDE, (g['y0'] - 340 * g['dy'], g['x0'] + 520 * g['dx'], g['y0'] - 310 * g['dy'], g['x0'] + 590 * g['dx']))
    check('a smaller box adds nothing', none == (0, 0, 0, 0) and same['W'] == SIDE['W'])


def test_seam():
    W, H = 3, 1
    across, down = W * 32 + 1, H * 32 + 1
    raw = array.array('f', [0.0] * (across * down))
    grid = MS.Grid(W, H, array.array('f', raw), 0, 0)
    old = {(0, 0): [800.0] * 1089}                      # (the old cell stands 800 over what the file says)
    fixed = mapgrow.lay_old(grid, old)
    moved = mapgrow.ease_seam(grid, raw, fixed, reach=48)
    check('the seam eased', moved > 0)
    check('old points untouched', all(grid.pts[q] == 800.0 for q in range(across * down) if fixed[q]))
    edge = [grid.pts[r * across + 32] for r in range(down)]
    check('the shared edge is the old cell\'s', all(v == 800.0 for v in edge))
    row = [grid.pts[16 * across + gx] for gx in range(32, across)]
    check('new ground falls away from the edge, never climbs', all(a >= b for a, b in zip(row, row[1:])), row[:8])
    check('far out, the file\'s own ground', row[-1] == 0.0, row[-1])
    check('every point on a step', all(v % MS.STEP == 0 for v in grid.pts))
    # a cliff the game can't store beside a fixed point: the new side moves to it, the old doesn't
    grid2 = MS.Grid(W, H, array.array('f', [0.0] * (across * down)), 0, 0)
    fixed2 = mapgrow.lay_old(grid2, {(0, 0): [5000.0] * 1089})
    mapgrow.keep_slopes(grid2, fixed2)
    worst = max(abs(grid2.pts[gy * across + gx] - grid2.pts[gy * across + gx + 1]) for gy in range(down) for gx in range(across - 1))
    check('no step past what VHGT holds', worst <= MS.MAX_RISE, worst)
    check('the old cell kept its height', all(grid2.pts[q] == 5000.0 for q in range(across * down) if fixed2[q]))


def test_within():
    lay = {'roads': [{'line': [(100.0, 100.0), (9000.0, 100.0)]}, {'line': [(100.0, 9000.0), (200.0, 9100.0)]}],
           'bridges': [], 'rivers': [], 'lakes': [],
           'buildings': [{'ring': [(5000.0, 5000.0), (5100.0, 5000.0), (5100.0, 5100.0)]}, {'ring': [(100.0, 100.0), (150.0, 100.0), (150.0, 150.0)]}],
           'places': [{'p': [4500.0, 200.0]}, {'p': [100.0, 100.0]}]}
    got = mapgrow.lay_within(lay, {(1, 0), (1, 1)})
    check('a road crossing a new cell is kept, one that doesn\'t is not', len(got['roads']) == 1)
    check('buildings and places by where they are', len(got['buildings']) == 1 and len(got['places']) == 1)
    ops = [{'op': 'add', 'cell': 'A'}, {'op': 'land', 'cell': 'B'}, {'op': 'record', 'key': 'X'}, {'op': 'add', 'cell': '+00ABCD'}]
    check('ops on old cells dropped, the rest kept', [o.get('cell') or o.get('key') for o in mapgrow.keep_new(None, ops, {'B'})] == ['A', 'X', '+00ABCD'])


for t in (test_side, test_seam, test_within):
    t()
print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
