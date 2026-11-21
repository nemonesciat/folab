"""The draw count (drawcount.py) against the game's own files: the numbers measured on 20 Nov 2026 by hand (Freeside's
gate 1,691 things / 2,196 draws, Novac 1,109 / 1,403) come out the same; a mod's things add their model's shapes, a game
thing it takes out takes them away; the bands; the busiest spots round the mod's cells, a few cells apart."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import drawcount  # noqa: E402
import gamedata  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
mj = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
C = drawcount.Counter(gd, None)
r = C.around(mj, 4000, 0)
check("Freeside's gate: the game's own numbers", (r['things'], r['draws']) == (1691, 2196), (r['things'], r['draws']))
check('25 cells loaded', r['cells'] == 25)
r = C.around(mj, 20000, -95000)
check('Novac', (r['things'], r['draws']) == (1109, 1403), (r['things'], r['draws']))
check('kinds add up', sum(d for _n, d in r['kinds'].values()) == r['draws'] and sum(n for n, _d in r['kinds'].values()) == r['things'])
check('the most drawn first', all(r['top'][i][2] >= r['top'][i + 1][2] for i in range(len(r['top']) - 1)))

# a mod: things added and a game thing taken out, at Novac
grid = gd.grid(mj)
cell = grid[(int(20000 // 4096), int(-95000 // 4096))]
ck = gd.key(cell)
game_refs = list(gd.refs(cell))
one = next(x for x in game_refs if x.get('base') is not None and C.draws_of(gd.key(x['base'])) > 0)
sand = next(gd.key(f) for f, (_i, rec) in gd.forms.items() if rec.tag == 'STAT' and gd.edid(f) == 'SandbagSingle')
pr = types.SimpleNamespace(name='DrawTest', records={}, cells={ck: {'refs': {
    gd.key(one['ref']): {'removed': True},
    '+000801': {'base': sand, 'p': [20000, -95000, 0, 0, 0, 0]},
    '+000802': {'base': sand, 'p': [20100, -95000, 0, 0, 0, 0]},
    '+000803': {'base': sand, 'p': [20200, -95000, -30000, 0, 0, 0]},       # (sunk out of the way: not drawn)
}}})
moved = next(x for x in game_refs if x is not one and x.get('base') is not None)
pr.cells[ck]['refs'][gd.key(moved['ref'])] = {'p': [20000, -95000, 5, 0, 0, 0]}          # (moved only: still drawn)
M = drawcount.Counter(gd, pr)
M.assets = None
m = M.around(mj, 20000, -95000)
want = 1403 - C.draws_of(gd.key(one['base'])) + 2 * C.draws_of(sand)
check("the mod's things counted, the one it took out not, a sunk one not", m['draws'] == want and m['things'] == 1109 - 1 + 2, (m['draws'], want, m['things']))

# bands
check('bands', [drawcount.band(n)[0] for n in (1500, 2196, 3900, 5000, 12693)] == ['ok', 'ok', 'ok', 'heavy', 'too much'])

# busiest: round the mod's cells only, spots apart
spots = M.busiest(mj)
check('busiest: a spot round the mod\'s one cell', len(spots) == 1 and spots[0]['at'] == (int(20000 // 4096), int(-95000 // 4096)) and spots[0]['draws'] == m['draws'], spots)
pr.cells[gd.key(grid[(0, 0)])] = {'refs': {}}
pr.cells[gd.key(grid[(1, 0)])] = {'refs': {}}
spots = M.busiest(mj)
check('busiest: two cells side by side are one spot', len(spots) == 2, spots)
