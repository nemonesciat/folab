import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Outside: worldspaces, their grid of cells, the ground (heights checked against the rocks lying on it), and the
always-loaded things filed under the square they stand in."""
import struct
import gamedata, land, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
g = gd.grid(w)
check('the Mojave has its 16,000-odd cells', len(g) > 16000)
check('Goodsprings square (-18, 0) is a cell of it', (-18, 0) in g and gd.ext_cells[g[(-18, 0)]] == w)
check('interiors are not outside cells', not (set(gd.ext_cells) & gd.interiors))
d = land.decode(gd, gd.land_at(w, -18, 0), {})
check('33 x 33 heights, four painted quarters', len(d['h']) == 33 * 33 and len(d['q']) == 4 and all(q['base'] for q in d['q']))
check('layers have strengths from 0 to 1', all(0 <= a <= 1 for q in d['q'] for l in q['layers'] for a in l['a']))
near = []
for r in gd.refs(g[(-18, 0)]):
    if r['pos'] and r['base'] in gd.forms and 'rock' in gd.describe(r['base'])[1].lower():
        c, row = round((r['pos'][0] + 18 * 4096) / 128), round(r['pos'][1] / 128)
        if 0 <= c <= 32 and 0 <= row <= 32:
            near.append(abs(r['pos'][2] - d['h'][row * 33 + c]))
near.sort()
check('rocks lie on the ground (median within 16 units of %d)' % len(near), near and near[len(near) // 2] < 16)
pers = gd.persistent_in(w, -18, 0)
check('always-loaded things in the square are with its refs', pers and set(pers) <= {r['ref'] for r in gd.refs(g[(-18, 0)])})
marks = [tes4.zstr(gd.ref_fields(e)[1].get('FULL', b'')) for e in gd.cell_refs[gd.world_persistent[w]].values()
         if 'XMRK' in gd.ref_fields(e)[1]]
check('map markers found (Goodsprings among %d)' % len(marks), 'Goodsprings' in marks)
