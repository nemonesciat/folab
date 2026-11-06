"""The navmesh by hand: corners, triangles, joins and cuts, marks, each kept sound, the neighbours put right when numbers
change, and the result read back from a plugin."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite
import gamedata
import navbuild
import navedit
import navmesh as N
import project
import tes4


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


G = gamedata.GameData()
W = next(w for w in G.worlds() if G.edid(w) == 'WastelandNV')
grid = G.grid(W)
pr = project.Project.create('Nav Hand')


def do(**a):
    ops, label, cells = navedit.act(G, pr, a)
    pr.apply(label, ops)
    return cells


def refused(**a):
    try:
        navedit.act(G, pr, a)
        return False
    except navedit.EditError as e:
        return str(e)


def sound_all():
    forms = {}
    for n in pr.navmesh.values():
        for x in [n] + n.get('others', []):
            forms[x['form']] = navbuild.as_mesh(x)
    for f, m in forms.items():
        N.refresh(m)
    return [s for f, m in forms.items() for s in N.validate(m, forms, f) if not (pr.navmesh and forms[f] is None)]


# a game cell with one mesh, neighbours joined to it
xy = next(k for k in sorted(grid) if len(G.navmeshes(grid[k])) == 1 and sum(len(G.navmeshes(grid[(k[0] + dx, k[1] + dy)])) if (k[0] + dx, k[1] + dy) in grid else 0 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) >= 1
          and any(N.read_navm(G.plugins[G.navmeshes(grid[k])[0][0]].data(G.navmeshes(grid[k])[0][1]))['ext'] for _ in [0]) and 'FalloutNV.esm' in G.key(grid[k]))
ck = G.key(grid[xy])
view = navedit.view(G, pr, ck)
check('a game mesh can be looked at', view['source'] == 'game' and len(view['meshes']) == 1)
m0 = view['meshes'][0]
n0 = len(m0['tris'])

# moving a corner that isn't on a joined edge
free = next(v for v in range(len(m0['verts'])) if not any(v in t[:3] and t[6] & 7 for t in m0['tris']))
to = list(m0['verts'][free])
to[2] += 20
do(cell=ck, do='move', mesh=0, moves={str(free): to})
now = pr.navmesh[ck]
check('moving a corner up: it\'s the mod\'s now, the mesh kept whole', len(now['tris']) == n0 and abs(now['verts'][free][2] - to[2]) < 0.01 and now.get('hand') and not now.get('copy'))
check('… up to date', navbuild.status(G, pr, ck)['current'])
check('… sound', not N.validate(navbuild.as_mesh(dict(now)) | {'grid': N.build_grid([tuple(v) for v in now['verts']], [tuple(t) for t in now['tris']])}))
pr.undo()
check('Undo puts the game\'s back', ck not in pr.navmesh)

# a corner on a joined edge moves only up and down
joined = next(((ti, i) for ti, t in enumerate(m0['tris']) for i in range(3) if t[6] >> i & 1 and m0['ext'][t[3 + i]][0] == 0), None)
if joined:
    v = m0['tris'][joined[0]][joined[1]]
    away = list(m0['verts'][v])
    away[0] += 100
    check('a corner on a joined edge can\'t slide off it', refused(cell=ck, do='move', mesh=0, moves={str(v): away}))

# turning a triangle over is refused
t0 = m0['tris'][0]
a, b, c = [m0['verts'][t0[k]] for k in range(3)]
flip = [a[0] + 3 * (b[0] + c[0] - 2 * a[0]), a[1] + 3 * (b[1] + c[1] - 2 * a[1]), a[2]]
if not any(t0[6] >> i & 1 for i in range(3)):
    check('turning a triangle over is refused', refused(cell=ck, do='move', mesh=0, moves={str(t0[0]): flip}))

# delete: numbers change, neighbours follow
link_tri = joined[0] if joined else None
target = m0['ext'][m0['tris'][link_tri][3 + joined[1]]][1] if joined else None
do(cell=ck, do='delete', mesh=0, tris=[link_tri] if joined else [0])
now = pr.navmesh[ck]
check('deleting a triangle: one fewer', len(now['tris']) == n0 - 1)
form = now['form']
forms = {}
for n in pr.navmesh.values():
    for x in [n] + n.get('others', []):
        forms[x['form']] = navbuild.as_mesh(x)
if joined:
    check('the neighbour\'s mesh is in the mod, its link to the triangle gone', target in forms)
    for f, m in forms.items():
        N.refresh(m)
    check('every link across them is sound', not N.validate(forms[form], forms, form) and not N.validate(forms[target], {form: forms[form]}, target),
          str((N.validate(forms[form], forms, form) + N.validate(forms[target], {form: forms[form]}, target))[:2]))

# add: a new triangle on a free edge, a new corner beyond it
m1 = navbuild.as_mesh(pr.navmesh[ck])
ti, i = next((ti, i) for ti, t in enumerate(m1['tris']) for i in range(3) if t[3 + i] == N.NONE and not t[6] >> i & 1)
t = m1['tris'][ti]
p, q = m1['verts'][t[i]], m1['verts'][t[(i + 1) % 3]]
mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
ox, oy = q[1] - p[1], p[0] - q[0]          # (outward: to the right along an anticlockwise edge)
spot = [mx + ox * 0.5, my + oy * 0.5, (p[2] + q[2]) / 2]
do(cell=ck, do='add', mesh=0, pts=[t[(i + 1) % 3], t[i], spot])
now = pr.navmesh[ck]
new = now['tris'][-1]
check('adding a triangle on a free edge joins it, both ways', ti in new[3:6] and now['tris'][ti][3 + i] == len(now['tris']) - 1, str(new))
check('… the winding fixed however it was clicked', navedit._area2([tuple(v) for v in now['verts']], new) > 0)
check('three in a line is refused', refused(cell=ck, do='add', mesh=0, pts=[[0, 0, 0], [1, 1, 0], [2, 2, 0]]))
check('an overlapping one is refused', refused(cell=ck, do='add', mesh=0, pts=[t[(i + 1) % 3], t[i], [spot[0] + 300, spot[1] + 300, spot[2]]]))

# cut, join
tn = len(now['tris']) - 1
do(cell=ck, do='cut', mesh=0, tri=tn, edge=new[3:6].index(ti))
now = pr.navmesh[ck]
check('cutting an edge frees it, both ways', ti not in now['tris'][tn][3:6] and tn not in now['tris'][ti][3:6])
check('cutting a free edge is refused', refused(cell=ck, do='cut', mesh=0, tri=tn, edge=new[3:6].index(ti)))
do(cell=ck, do='join', a=[ck, 0, tn, new[3:6].index(ti)], b=[ck, 0, ti, i])
now = pr.navmesh[ck]
check('joining them again', ti in now['tris'][tn][3:6] and tn in now['tris'][ti][3:6])

# marks and cover
do(cell=ck, do='mark', mesh=0, tris=[tn], flag='preferred', on=True)
check('marked preferred', pr.navmesh[ck]['tris'][tn][6] & N.F_PREFERRED)
do(cell=ck, do='mark', mesh=0, tris=[tn], flag='water', on=True)
check('marked water', pr.navmesh[ck]['tris'][tn][6] & N.F_WATER)
do(cell=ck, do='cover', mesh=0, tri=tn, value=31)
check('marked cover, in the list too', pr.navmesh[ck]['tris'][tn][7] == 31 and tn in pr.navmesh[ck]['cover'])

# a ledge: two far apart triangles
far = max(range(len(now['tris'])), key=lambda k: sum(now['verts'][c][0] for c in now['tris'][k][:3]))
ti2, i2 = next((ti, i) for ti, t in enumerate(now['tris']) for i in range(3) if t[3 + i] == N.NONE and not t[6] >> i & 1 and ti != tn)
ti3, i3 = next((ti, i) for ti, t in enumerate(now['tris']) for i in range(3) if t[3 + i] == N.NONE and not t[6] >> i & 1 and ti not in (tn, ti2)
               and max(abs(now['verts'][t[i]][0] - now['verts'][now['tris'][ti2][i2]][0]), abs(now['verts'][t[i]][1] - now['verts'][now['tris'][ti2][i2]][1])) > navedit.WELD)
do(cell=ck, do='join', a=[ck, 0, ti2, i2], b=[ck, 0, ti3, i3])
now = pr.navmesh[ck]
e2, e3 = now['ext'][now['tris'][ti2][3 + i2]], now['ext'][now['tris'][ti3][3 + i3]]
check('joining far apart edges makes a pair of ledge links', {e2[0], e3[0]} == {1, 2} and e2[2] == ti3 and e3[2] == ti2)
do(cell=ck, do='cut', mesh=0, tri=ti2, edge=i2)
now = pr.navmesh[ck]
check('… and cutting one takes both', now['tris'][ti2][3 + i2] == N.NONE and now['tris'][ti3][3 + i3] == N.NONE and not any(e[0] for e in now['ext']))

# written and read back
out = os.path.join(project.HOME, 'nav hand.esp')
espwrite.write(G, pr, out)
p = tes4.PluginFile(out)
rows = {}
for r, _g in p.walk():
    rows.setdefault(r.tag, []).append(r)
navm = {r.formid: N.read_navm(p.data(r)) for r in rows['NAVM']}
check('read back, every mesh is sound and every link mutual', not any(N.validate(m, navm, f) for f, m in navm.items()), str([N.validate(m, navm, f)[:2] for f, m in navm.items() if N.validate(m, navm, f)][:1]))
navi = N.read_navi(p.data(rows['NAVI'][0]))
mine = next(e for e in navi['info'] if e['navm'] & 0xFFFFFF == int(form.rsplit(':', 1)[1], 16))
check('the preferred share in NAVI counts it', abs(mine['value'] - 1 / len(pr.navmesh[ck]['tris'])) < 1e-4, str(mine['value']))
back = next(m for f, m in navm.items() if f & 0xFFFFFF == int(form.rsplit(':', 1)[1], 16))
check('cover read back', back['tris'][tn][7] == 31 and tn in back['cover'])

# inside: a place with several meshes keeps the rest as they were, edited one by one
many = next(c for c in sorted(G.interiors) if len(G.navmeshes(c)) > 1)
mk = G.key(many)
v2 = navedit.view(G, pr, mk)
do(cell=mk, do='mark', mesh=1, tris=[0], flag='preferred', on=True)
check('a place with several meshes: one edited, the others kept', pr.navmesh[mk].get('copy') and pr.navmesh[mk]['others'][0].get('hand') and not pr.navmesh[mk]['others'][0].get('copy'))
out2 = os.path.join(project.HOME, 'nav hand 2.esp')
espwrite.write(G, pr, out2)
p2 = tes4.PluginFile(out2)
navi2 = N.read_navi(next(p2.data(r) for r, _g in p2.walk() if r.tag == 'NAVI'))
check('… outlines kept in NAVI', sum(1 for e in navi2['info'] if e['outline'] is not None) >= len(v2['meshes']) - 1, str(sum(1 for e in navi2['info'] if e['outline'] is not None)))
