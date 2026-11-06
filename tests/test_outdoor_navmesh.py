"""Navmeshes outside: neighbouring cells joined both ways, game neighbours kept in step, everything sound and mutual after
reading the plugin back; doors in the world's persistent cell; the master index right; a new world. Nothing goes near the real game."""
import os
import struct
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite
import gamedata
import navbuild
import navmesh as N
import project
import tes4


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


G = gamedata.GameData()
W = next(w for w in G.worlds() if G.edid(w) == 'WastelandNV')
grid = G.grid(W)


def read_all(path):
    p = tes4.PluginFile(path)
    rows = {}
    for r, g in p.walk():
        rows.setdefault(r.tag, []).append((r, g))
    return p, rows


# two neighbouring cells with game meshes, the one with its own neighbours having some too
def game_n(xy):
    c = grid.get(xy)
    return len(G.navmeshes(c)) if c is not None else 0


pair = next(xy for xy in sorted(grid) if game_n(xy) == 1 and game_n((xy[0] + 1, xy[1])) == 1 and game_n((xy[0] + 2, xy[1])) >= 1 and game_n((xy[0] - 1, xy[1])) >= 1)
a, b = grid[pair], grid[(pair[0] + 1, pair[1])]
ak, bk = G.key(a), G.key(b)

pr = project.Project.create('Outdoor Nav')
t0 = time.time()
ops, rep = navbuild.generate_area(G, pr, [ak, bk])
print('# made %d cells, %d triangles in %.1f s' % (rep['cells'], rep['triangles'], time.time() - t0))
check('two cells made', rep['cells'] == 2 and rep['triangles'] > 20, str(rep['triangles']))
check('joined across their edges', rep['joined'] > 0, str(rep['joined']))
cells_in = {o['cell'] for o in ops}
check('neighbours whose meshes had links are in the change too', rep['neighbours'] >= 1, str(rep['neighbours']))
pr.apply('Generate navmesh', ops)
check('it keeps the game\'s forms', pr.navmesh[ak]['form'] == navbuild.game_meshes(G, ak)[0] and pr.navmesh[bk]['form'] == navbuild.game_meshes(G, bk)[0])
nb = next(k for k in cells_in if k not in (ak, bk))
nbs = [pr.navmesh[nb]] + pr.navmesh[nb].get('others', [])
was = [navbuild.game_copy(G, e) for e in navbuild.game_entries(G, nb)]
check('a neighbour keeps its triangles as they were, only its links change', nbs[0].get('copy') and any(x['tris'] != w['tris'] for x, w in zip(nbs, was)) and all([t[:3] for t in x['tris']] == [t[:3] for t in w['tris']] for x, w in zip(nbs, was)))

out = os.path.join(project.HOME, 'outdoor nav.esp')
espwrite.write(G, pr, out)
p, recs = read_all(out)
navm = {r.formid: N.read_navm(p.data(r)) for r, _g in recs['NAVM']}
check('every mesh in the change is in the plugin', len(navm) == sum(1 + len(pr.navmesh[o['cell']].get('others', [])) for o in ops))
check('every mesh read back is sound', not any(N.validate(m, navm, fid) for fid, m in navm.items()), str([N.validate(m, navm, fid)[:1] for fid, m in navm.items() if N.validate(m, navm, fid)][:2]))

nm = len(p.header['masters'])
idx = {n.lower(): i for i, n in enumerate(p.header['masters'])}
fid_of = lambda key: (idx[key.rsplit(':', 1)[0].lower()] << 24) | int(key.rsplit(':', 1)[1], 16)
A, B = navm[fid_of(pr.navmesh[ak]['form'])], navm[fid_of(pr.navmesh[bk]['form'])]
afid, bfid = fid_of(pr.navmesh[ak]['form']), fid_of(pr.navmesh[bk]['form'])


def links_to(m, target):
    return [(ti, i, m['ext'][t[3 + i]][2]) for ti, t in enumerate(m['tris']) for i in range(3) if t[6] >> i & 1 and t[3 + i] < len(m['ext']) and m['ext'][t[3 + i]][1] == target]


ab, ba = links_to(A, bfid), links_to(B, afid)
check('the two are joined both ways', len(ab) > 0 and len(ab) == len(ba), '%d, %d' % (len(ab), len(ba)))
mutual = all(any(x[0] == other and x[2] == ti for x in ba) for ti, _i, other in ab)
check('every link is mutual', mutual)
V = A['verts']
on_edge = all(abs(V[A['tris'][ti][i]][0] - (pair[0] + 1) * 4096) < 0.5 and abs(V[A['tris'][ti][(i + 1) % 3]][0] - (pair[0] + 1) * 4096) < 0.5 for ti, i, _o in ab)
check('… on the border', on_edge)

navi = N.read_navi(p.data(recs['NAVI'][0][0]))
info = {e['navm']: e for e in navi['info']}
links = {e['navm']: e for e in navi['links']}
check('NAVI overrides the game\'s form, entries for each mesh written, no more', recs['NAVI'][0][0].formid == N.NAVI_FORM and set(info) == set(links) == set(navm))
wid = (idx[G.key(W).rsplit(':', 1)[0].lower()] << 24) | (W & 0xFFFFFF)
check('its space is the world, its place the grid square', info[afid]['space'] == wid and info[afid]['place'] == N.grid_place(*pair))
check('NVCI lists its neighbour', bfid in links[afid]['adjacent'] + links[afid]['preferred'] and afid in links[bfid]['adjacent'] + links[bfid]['preferred'])
check('NAVI comes back the same', N.write_navi(navi) == p.data(recs['NAVI'][0][0]))
# the meshes sit in their cells
parents = {r.formid: g for r, g in recs['NAVM']}
check('each NAVM is under a grid cell\'s temporary group', all(any(x[0] == tes4.G_CELL_TEMPORARY for x in parents[f]) for f in navm))

G2 = gamedata.GameData(plugins=[q.path for q in G.plugins] + [out])
a2 = G2.to_global(len(G.plugins), (idx[ak.rsplit(':', 1)[0].lower()] << 24) | (a & 0xFFFFFF))
m2 = G2.navmeshes(a2)
check('loaded with the game, the cell\'s navmesh comes from the plugin', len(m2) == 1 and G2.names[m2[0][0]] == 'outdoor nav.esp')

# status
st = navbuild.status(G, pr, ak)
check('up to date when made', st['mine'] and st['current'] and st['outside'])
ws = navbuild.world_status(G, pr, W)
check('the map says made, and joined for neighbours', ws['%d,%d' % pair] == 'made' and 'joined' in ws.values(), str(sorted(set(ws.values()))))
L = {'h': [100.0] * 1089}
pr.land[ak] = L
check('new ground makes it out of date', navbuild.world_status(G, pr, W)['%d,%d' % pair] == 'old' and not navbuild.status(G, pr, ak)['current'])
del pr.land[ak]
check('… and back', navbuild.status(G, pr, ak)['current'])

# again over the top: it finds its own meshes, and stays sound
ops2, rep2 = navbuild.generate_area(G, pr, [ak])
pr.apply('Generate navmesh', ops2)
forms = {}
for k, n in pr.navmesh.items():
    for x in [n] + n.get('others', []):
        forms[x['form']] = navbuild.as_mesh(x)
check('made again over the top of its own, every link still sound', not any(N.validate(N.refresh(m), forms, f) for f, m in forms.items()))

# a door outside: told its triangle, in the world's persistent cell
door_xy = next((xy for xy in sorted(grid) if any(r['leads'] and r['persistent'] and r['base'] in G.forms and G.forms[r['base']][1].tag == 'DOOR' for r in G.refs(grid[xy]))
                and game_n(xy) and 'FalloutNV.esm' in G.key(grid[xy])), None)
pr2 = project.Project.create('Outdoor Door')
dk = G.key(grid[door_xy])
ops3, rep3 = navbuild.generate_area(G, pr2, [dk])
pr2.apply('Generate navmesh', ops3)
print('# door cell %r: %d doors, %d too far, %d stubs, %d neighbours' % (door_xy, rep3['doors'], rep3['doors_missed'], rep3['stubs'], rep3['neighbours']))
check('a cell with a door: the door is linked', rep3['doors'] >= 1)
out3 = os.path.join(project.HOME, 'outdoor door.esp')
espwrite.write(G, pr2, out3)
p3, recs3 = read_all(out3)
door_recs = [(r, g) for r, g in recs3['REFR'] if any(t == 'XNDP' for t, _d in tes4.iter_subrecords(p3.data(r)))]
check('… overridden with its XNDP', len(door_recs) >= rep3['doors'])
pc = G.world_persistent[W]
check('… in the world\'s persistent cell', any(any(x[0] == tes4.G_CELL_PERSISTENT and x[1] == (pc & 0xFFFFFF) | (x[1] & 0xFF000000) for x in g) for r, g in door_recs))
navm3 = {r.formid: N.read_navm(p3.data(r)) for r, _g in recs3['NAVM']}
door_ids = {r.formid for r, _g in door_recs}
listed = {d[0] for m in navm3.values() for d in m['doors']}
check('… and each mesh lists its door', door_ids & listed)
check('stubs where the cell had several meshes', rep3['stubs'] == game_n(door_xy) - 1, '%d of %d' % (rep3['stubs'], game_n(door_xy)))
check('all sound', not any(N.validate(m, navm3, f) for f, m in navm3.items()))

# taking one away: the neighbours go back to the game's
pr4 = project.Project.create('Outdoor Remove')
ops4, _r = navbuild.generate_area(G, pr4, [ak, bk])
pr4.apply('Generate', ops4)
ops5 = navbuild.remove_area(G, pr4, [ak])
pr4.apply('Remove', ops5)
check('removing a cell: its mesh goes, its neighbour stays', ak not in pr4.navmesh or pr4.navmesh[ak].get('copy'))
check('… and the one next door is still made', pr4.navmesh[bk].get('copy') is None and not pr4.navmesh[bk].get('stub'))
forms4 = {}
for k, n in pr4.navmesh.items():
    for x in [n] + n.get('others', []):
        forms4[x['form']] = navbuild.as_mesh(x)
check('… every link still sound', not any(N.validate(N.refresh(m), forms4, f) for f, m in forms4.items()))
ops6 = navbuild.remove_area(G, pr4, [bk])
pr4.apply('Remove', ops6)
check('removing the other: nothing of it is left', not pr4.navmesh, str(list(pr4.navmesh)[:3]))

# a new world: no game meshes at all
import plugintree
import worldgen
pr5 = project.Project.create('World Nav')
w = espwrite.Writer(G, pr5)
w.force_all = True
w.plan()
tree = plugintree.Plugin.empty(b'')
subs = [('HEDR', struct.pack('<fiI', 1.34, 0, 0x800)), ('CNAM', b'FOLab\0')]
for m in w.masters:
    subs += [('MAST', m.encode('cp1252') + b'\0'), ('DATA', b'\0' * 8)]
tree.header.set_data(espwrite.join(subs), 0)
ltex = next(f for f, (i, r) in G.forms.items() if r.tag == 'LTEX')
wid2, nxt = worldgen.add_world(G, tree, w, 0x800, {'edid': 'NavWorld', 'name': 'Nav World', 'template': W, 'size': 4, 'height': 200.0, 'ltex': G.key(ltex)})
worldgen.fix_header(tree, w.own(nxt))
src = os.path.join(project.HOME, 'world nav.esp')
with open(src, 'wb') as f:
    f.write(tree.bytes())
G3 = gamedata.GameData(plugins=[q.path for q in G.plugins] + [src])
pr5.source = None
W3 = next(x for x in G3.worlds() if G3.edid(x) == 'NavWorld')
g3 = G3.grid(W3)
c0, c1 = g3[(-1, 0)], g3[(0, 0)]
k0, k1 = G3.key(c0), G3.key(c1)
ops7, rep7 = navbuild.generate_area(G3, pr5, [k0, k1])
check('a new world: flat land gets meshes, joined', rep7['cells'] == 2 and rep7['joined'] > 0, str(rep7))
pr5.apply('Generate', ops7)
check('… with IDs of the mod\'s own', pr5.navmesh[k0]['form'].startswith('+'))
check('… and no neighbours overridden', rep7['neighbours'] == 0)
