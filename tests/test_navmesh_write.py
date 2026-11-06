"""A place's navmesh in a plugin: read back from the file it's sound, in the right place, named in the master index, its
doors linked both ways; loaded with the game it's what the game finds for that place. Nothing goes near the real game."""
import os
import struct
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite
import gamedata
import kitindex as K
import navbuild
import navmesh as N
import project
import recordio
import tes4
import browse


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


G = gamedata.GameData()
kits = K.build(G)
vault = kits['dungeons' + chr(92) + 'vault']
ts = K.Tileset(vault)
BR = browse.Browse(G, lambda: None)


def new_project(name):
    return project.Project.create(name)


def records_of(path):
    p = tes4.PluginFile(path)
    out = {}
    for r, g in p.walk():
        out.setdefault(r.tag, []).append((r, g, p))
    return p, out


src = next(c for c in G.interiors if G.edid(c) == 'Vault3a')
rec = BR.record(G.key(src))['record']
rec['type'], rec['src'] = 'CELL', rec.get('src', '')
pr = new_project('Nav Test')
recordio.set_field(rec, 'EDID', 'NavTestPlace', label='Editor ID')
recordio.set_field(rec, 'FULL', 'Nav Test', label='Name')
made = pr.apply('New place', [{'op': 'record_new', 'record': rec}])
cell = made[0]

# a layout, and a door in it
got = None
for s in range(20):
    got = K.build_area(ts, [(i, j) for i in range(6) for j in range(6)], s)
    if got and len(got) > 10 and not K.can_walk_out(G, ts, got)[1]:
        break
ops = [dict(o, cell=cell) for o in K.as_placed(ts, got)]
check('a layout\'s pieces are marked as generated', all(o.get('gen') for o in ops))
door_base = next(f for f, (i, r) in G.forms.items() if r.tag == 'DOOR' and G.describe(f)[3])
start = max(got, key=lambda c: sum(1 for d in range(4) if ts.walks(ts.sides[got[c]][d])))
at = [start[0] * 256.0, start[1] * 256.0, 0.0, 0, 0, 0]
pr.apply('Layout', ops)
check('… and stay marked, so generating again can replace them', sum(1 for r in pr.cells[cell]['refs'].values() if r.get('gen')) == len(ops))
door = pr.apply('A door', [{'op': 'add', 'cell': cell, 'base': G.key(door_base), 'p': at, 's': 1}])[0]
pr.cells[cell]['refs'][door]['tel'] = {'door': door, 'p': at}

st = navbuild.status(G, pr, cell)
check('before: no navmesh, one can be made', not st['mine'] and st['can'] and not st['game'])
data, report = navbuild.generate(G, pr, cell)
check('made, with triangles (%d in %.1f s)' % (report['triangles'], report['seconds'] or 0), report['triangles'] > 10)
check('its door is linked', report['doors'] == 1 and not report['doors_missed'])
def covers(data, x, y):
    V = data['verts']
    for t in data['tris']:
        a, b, c = V[t[0]], V[t[1]], V[t[2]]
        d0 = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
        d1 = (c[0] - b[0]) * (y - b[1]) - (c[1] - b[1]) * (x - b[0])
        d2 = (a[0] - c[0]) * (y - c[1]) - (a[1] - c[1]) * (x - c[0])
        if (d0 >= 0 and d1 >= 0 and d2 >= 0) or (d0 <= 0 and d1 <= 0 and d2 <= 0):
            return True
    return False
walkable = [c for c, v in got.items() if K.can_walk_out and sum(1 for d in range(4) if ts.walks(ts.sides[v][d])) >= 2]
hit = sum(covers(data, c[0] * 256.0, c[1] * 256.0) for c in walkable)
check('it\'s on the floor, not the roof', max(v[2] for v in data['verts']) < 120, str(max(v[2] for v in data['verts'])))
check('it covers the layout: the middle of %d of %d walkable pieces' % (hit, len(walkable)), hit >= len(walkable) * 0.6)
pr.apply('Generate navmesh', [{'op': 'navmesh', 'cell': cell, 'mesh': data}])
st = navbuild.status(G, pr, cell)
check('it\'s up to date', st['mine'] and st['current'])
form = pr.navmesh[cell]['form']
check('it has an ID of the mod\'s own', form.startswith('+'))

out = os.path.join(project.HOME, 'nav test.esp')
espwrite.write(G, pr, out)
p, recs = records_of(out)
nm = len(p.header['masters'])
check('the plugin has one NAVM and one NAVI', len(recs.get('NAVM', [])) == 1 and len(recs.get('NAVI', [])) == 1)
navm_rec, group, _p = recs['NAVM'][0]
m = N.read_navm(p.data(navm_rec))
check('read back from the file, the mesh is sound', not N.validate(m), str(N.validate(m)[:2]))
check('… with the same triangles', len(m['tris']) == report['triangles'] and m['tris'][0] == tuple(data['tris'][0]))
fid = lambda key: (nm << 24) | int(key[1:], 16)
check('… and names its place', m['cell'] == fid(cell))
check('it comes back the same when written again', N.write_navm(m) == p.data(navm_rec))
check('the record is as the game\'s are: no flags, form version 15', navm_rec.flags == 0)
navi_rec = recs['NAVI'][0][0]
check('the master index overrides the game\'s own form', navi_rec.formid == N.NAVI_FORM and p.header['masters'][0].lower() == 'falloutnv.esm')
navi = N.read_navi(p.data(navi_rec))
check('it comes back the same too', N.write_navi(navi) == p.data(navi_rec))
check('it has exactly this mesh', [e['navm'] for e in navi['info']] == [navm_rec.formid] == [e['navm'] for e in navi['links']])
check('its entry says the place is its own space, no square', navi['info'][0]['space'] == fid(cell) and navi['info'][0]['place'] == 0)
check('the mesh\'s door is listed', navi['links'][0]['doors'] == [fid(door)] and [d[0] for d in m['doors']] == [fid(door)])
tri = m['doors'][0][1]
check('the door\'s triangle is marked', m['tris'][tri][6] & N.F_DOOR)
door_rec = next(r for r, g, _ in recs['REFR'] if r.formid == fid(door))
subs = list(tes4.iter_subrecords(p.data(door_rec)))
names = [t for t, _d in subs]
check('the door names mesh and triangle, in the game\'s order', dict(subs).get('XNDP') == N.door_link(navm_rec.formid, tri) and names.index('XTEL') < names.index('XNDP') < names.index('DATA'), str(names))

G2 = gamedata.GameData(plugins=[q.path for q in G.plugins] + [out])
c2 = G2.to_global(len(G.plugins), fid(cell))
found = G2.navmeshes(c2)
check('loaded with the game, the place has that navmesh', len(found) == 1 and N.read_navm(G2.plugins[found[0][0]].data(found[0][1]))['tris'] == m['tris'])
refs = {r.tag for r in [e[1] for e in G2.cell_refs[c2].values()]}
check('… among what the place holds', 'NAVM' in refs and 'REFR' in refs)

# out of date, undo
pr.apply('Move', [{'op': 'move', 'cell': cell, 'ref': door, 'p': [at[0] + 64] + at[1:]}])
check('moving something makes it out of date', not navbuild.status(G, pr, cell)['current'])
pr.undo()
check('undoing that, up to date again', navbuild.status(G, pr, cell)['current'])
pr.undo()
check('undoing the mesh takes it away', not navbuild.status(G, pr, cell)['mine'])
out1b = os.path.join(project.HOME, 'nav test b.esp')       # (the first is still open: it's loaded above)
espwrite.write(G, pr, out1b)
_p2, recs2 = records_of(out1b)
check('… and the plugin has none', 'NAVM' not in recs2 and 'NAVI' not in recs2)
pr.redo()
check('redo brings it back', navbuild.status(G, pr, cell)['mine'])

# Play here in the mod's own place: the test plugin builds on the mod, with the marker in its place (written only: no game)
import playtest
test_path = os.path.join(project.HOME, 'test plugin.esp')
playtest.write_test_plugin(G, None, [at[0], at[1], 100, 0], test_path, 'Nav Test', mod=pr.plugin, own_place=(cell, pr.records[cell]))
pt = tes4.PluginFile(test_path)
mods = [m.lower() for m in pt.header['masters']]
check('Play here in the mod\'s own place: the test plugin has the mod as a master', pr.plugin.lower() in mods and mods[0] == 'falloutnv.esm')
mi = mods.index(pr.plugin.lower())
own_cell = (mi << 24) | int(cell[1:], 16)
pt_recs = {}
for r, g in pt.walk():
    pt_recs.setdefault(r.tag, []).append(r)
check('… its copy of the place is the mod\'s place, by the mod\'s number', [r.formid for r in pt_recs.get('CELL', [])] == [own_cell])
check('… and the marker is in it', len(pt_recs.get('REFR', [])) == 1 and any(g is not None for g in [pt_recs['REFR'][0]]))
scro = [d for t, d in tes4.iter_subrecords(pt.data(pt_recs['SCPT'][0])) if t == 'SCRO']
check('… the script moves you to that marker', struct.pack('<I', pt_recs['REFR'][0].formid) in scro)

# a game place with one mesh: the same form replaced, its door linked over the game's
one = next(c for c in sorted(G.interiors) if len(G.navmeshes(c)) == 1 and 20 < len(G.refs(c)) < 150 and any(r['leads'] for r in G.refs(c)))
ck = G.key(one)
pr2 = new_project('Nav Test 2')
data2, rep2 = navbuild.generate(G, pr2, ck)
check('a game place (%s): made, keeping the game\'s form' % G.edid(one), data2['form'] == navbuild.game_meshes(G, ck)[0])
pr2.apply('Generate navmesh', [{'op': 'navmesh', 'cell': ck, 'mesh': data2}])
out2 = os.path.join(project.HOME, 'nav test 2.esp')
espwrite.write(G, pr2, out2)
p3, recs3 = records_of(out2)
game_fid = G.from_key(data2['form']) & 0xFFFFFF
check('… written as an override of the game\'s mesh', len(recs3['NAVM']) == 1 and recs3['NAVM'][0][0].formid & 0xFFFFFF == game_fid)
check('… sound', not N.validate(N.read_navm(p3.data(recs3['NAVM'][0][0]))))
if rep2['doors']:
    linked = [r for r, g, _ in recs3.get('REFR', []) if any(t == 'XNDP' for t, _d in tes4.iter_subrecords(p3.data(r)))]
    check('… its %d doors overridden, each told its triangle' % rep2['doors'], len(linked) == rep2['doors'])

many = next((c for c in G.interiors if len(G.navmeshes(c)) > 1), None)
if many:
    try:
        navbuild.generate(G, pr2, G.key(many))
        check('a place with several meshes is refused', False)
    except navbuild.NavError:
        check('a place with several meshes is refused', True)
