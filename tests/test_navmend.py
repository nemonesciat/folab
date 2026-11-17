import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Links between outside meshes that don't point back (navbuild.Area.mend): a batch of 40 of Waikiki's cells now and then came out
with one, and the whole batch was thrown away as unsound. Two small meshes either side of a cell border, one good link both ways,
one going only one way, one naming an outside link the mesh hasn't got: the bad two are taken off, the good one kept, the
outside-link lists renumbered, and the meshes are sound. A game mesh's links to another game mesh are not touched. No game files."""
import navbuild
import navmesh as N


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


def strip(x0):
    """Two triangles making a square 0..100 x x0..x0+100 at height 0, their outer edges unlinked."""
    v = [(x0, 0.0, 0.0), (x0 + 100.0, 0.0, 0.0), (x0 + 100.0, 100.0, 0.0), (x0, 100.0, 0.0)]
    t = [(0, 1, 2, N.NONE, N.NONE, 1, 0, 0), (0, 2, 3, 0, N.NONE, N.NONE, 0, 0)]
    return {'version': N.VERSION, 'cell': None, 'verts': v, 'tris': t, 'cover': [], 'doors': [], 'ext': [], 'grid': None}


def link(m, ti, i, target, tri):
    t = list(m['tris'][ti])
    t[3 + i] = len(m['ext'])
    t[6] |= 1 << i
    m['ext'].append((0, target, tri))
    m['tris'][ti] = tuple(t)


a, b = strip(0.0), strip(100.0)
link(a, 0, 1, '+B', 1)          # a0 (its right edge) <-> b1 (its left edge): good
link(b, 1, 2, '+A', 0)
link(a, 1, 1, '+B', 0)          # a1 -> b0, b0 doesn't link back
t = list(b['tris'][0])
t[3 + 1], t[6] = 7, t[6] | 2    # b0 edge 1 flagged with an outside link it hasn't got
b['tris'][0] = tuple(t)
A = navbuild.Area(None, None)
A.cells = {'a': [{'form': '+A', 'm': a, 'copy': False, 'data': {}}], 'b': [{'form': '+B', 'm': b, 'copy': False, 'data': {}}]}
bad_before = A.check()
check('the two bad links are found: %s' % bad_before[:2], len(bad_before) >= 2)
gone = A.mend()
check('mend takes them off, and only them (%d)' % gone, gone == 2)
check('the good link is kept both ways', a['tris'][0][6] & 2 and b['tris'][1][6] & 4 and tuple(a['ext'][a['tris'][0][4]][1:]) == ('+B', 1)
      and tuple(b['ext'][b['tris'][1][5]][1:]) == ('+A', 0))
check('outside links nobody uses are gone, the rest renumbered', len(a['ext']) == 1 and len(b['ext']) == 1)
check('the meshes are sound', A.check() == [])
check('a second mend finds nothing', A.mend() == 0)

# a game mesh's one-way link to another game mesh is the game's own: left alone
c, d = strip(0.0), strip(100.0)
link(c, 1, 1, '+D', 0)
A2 = navbuild.Area(None, None)
A2.cells = {'c': [{'form': '+C', 'm': c, 'copy': True, 'data': {}}], 'd': [{'form': '+D', 'm': d, 'copy': True, 'data': {}}]}
check("the game's own links between its own meshes are left as they are", A2.mend() == 0 and len(c['ext']) == 1)
