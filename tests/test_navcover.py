"""Cover on generated navmeshes (navgen.mark_cover): open edges with a wall beyond them are marked as the game marks its
own, so someone looking for somewhere to hide finds it instead of searching the whole mesh until the game runs out of
memory. Checked on a cell of the Mojave the game itself gives a lot of cover."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import navgen  # noqa: E402
import navmesh  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)


def game_cover(cell):
    out = []
    for _rfid, entry in gd.cell_refs.get(cell, {}).items():
        if entry[1].tag == 'NAVM':
            i, _f = gd.ref_fields(entry)
            m = navmesh.read_navm(gd.plugins[i].data(entry[1]))
            for ti in m['cover']:
                t = m['tris'][ti]
                out.append(tuple(sum(m['verts'][t[k]][a] for k in range(3)) / 3 for a in range(3)))
    return out


xy = (7, -25)                                   # (the cell of the Mojave with the most cover of the game's own)
cell = grid[xy]
theirs = game_cover(cell)
m, rep = navgen.generate(gd, cell)
tris, verts = m['tris'], m['verts']
check('a cell full of things gets cover', len(m['cover']) >= 30 and rep['cover'] == len(m['cover']), (len(m['cover']), len(tris), len(theirs)))
check('about as much as the game gives it', 0.4 * len(theirs) <= len(m['cover']) <= 2.5 * len(theirs), (len(m['cover']), len(theirs)))
check('the list is exactly the triangles with cover', m['cover'] == [i for i, t in enumerate(tris) if t[7] & navmesh.COVER_BITS])
check('most triangles have none', len(m['cover']) < len(tris) * 0.5)
sides = [(t, s) for t in tris for s in (0, 1) if t[7] >> (s * 6) & 15]
check('cover is on open edges only', sides and all(t[3 + s] == navmesh.NONE and not t[6] >> s & 1 for t, s in sides), len(sides))
check('its height counts as cover to the game (over 1), and nothing else is set', all(4 <= (t[7] >> (s * 6) & 15) <= 15 for t, s in sides)
      and all(t[7] & ~0x3CF == 0 for t in tris))
x0, y0 = xy[0] * 4096.0, xy[1] * 4096.0
on_border = lambda a, b: any(abs(a[k] - v) < 1 and abs(b[k] - v) < 1 for k, v in ((0, x0), (0, x0 + 4096), (1, y0), (1, y0 + 4096)))
check('never the cell\'s own edge', not any(on_border(verts[t[s]], verts[t[s + 1]]) for t, s in sides))
mine = [tuple(sum(verts[tris[i][k]][a] for k in range(3)) / 3 for a in range(3)) for i in m['cover']]
near = sum(1 for o in mine if any(math.hypot(g[0] - o[0], g[1] - o[1]) < 250 and abs(g[2] - o[2]) < 150 for g in theirs))
check('and mostly where the game has cover too', near >= len(mine) * 0.5, (near, len(mine)))
check('the mesh is sound', navmesh.validate(m) == [], navmesh.validate(m)[:3])
back = navmesh.read_navm(navmesh.write_navm(dict(m, cell=cell)))
check('written and read back, the cover is there', back['cover'] == m['cover'] and back['counts'][3] == len(m['cover']) and [t[7] for t in back['tris']] == [t[7] for t in tris])
# a triangle split to meet a neighbour loses its cover and its place in the list together
ti = next((i for i in m['cover'] if not tris[i][6] & 7 and any(tris[i][3 + e] == navmesh.NONE and not tris[i][7] >> (e * 6) & 15 for e in (0, 1))), None)
if ti is None:
    ti = m['cover'][0]
e = next(e for e in (0, 1, 2) if tris[ti][3 + e] == navmesh.NONE)
a, b = verts[tris[ti][e]], verts[tris[ti][(e + 1) % 3]]
done = navmesh._split(m, ti, e, tuple((a[k] + b[k]) / 2 for k in range(3)))
check('a split triangle is no longer listed with cover it hasn\'t', done and ti not in m['cover'] and m['cover'] == [i for i, t in enumerate(m['tris']) if t[7] & navmesh.COVER_BITS])
# open desert: next to none
flat = next(k for k in sorted(grid) if not game_cover(grid[k]) and sum(1 for r in gd.refs(grid[k]) if r['type'] == 'REFR') < 12 and gd.land_at(world, *k))
m2, rep2 = navgen.generate(gd, grid[flat])
check('open ground has next to none', m2 is None or len(m2['cover']) <= max(3, len(m2['tris']) * 0.03), (flat, m2 and len(m2['cover']), m2 and len(m2['tris'])))
