"""Navmeshes: reading and writing the game's own records byte for byte, what NAVI says about them, and generating new
ones. Nothing is written anywhere near the game."""
import os
import struct
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import navgen
import navmesh as N
import tes4


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


# --- every record in every file comes back byte for byte ---

results = N.check_files()
check('NAVM and NAVI found in the game', sum(n for _f, n, _b in results) > 6000, str(sum(n for _f, n, _b in results)))
for name, n, bad in results:
    if n:
        check('%s: all %d records byte exact' % (name, n), not bad, str(bad[:5]) if bad else '')

gd = gamedata.GameData(plugins=['FalloutNV.esm'])
p = gd.plugins[0]
navi = None
meshes = {}
for r, _g in p.walk():
    if r.tag == 'NAVM':
        meshes[r.formid] = N.read_navm(p.data(r))
    elif r.tag == 'NAVI':
        navi = N.read_navi(p.data(r))
        check('NAVI is the one form', r.formid == N.NAVI_FORM)
big = b'x' * 70000
check('an oversized subrecord goes behind an XXXX and reads back', list(tes4.iter_subrecords(N._sub('NVVX', big))) == [('NVVX', big)])

# --- what NAVI holds is what we'd work out ---

info = {e['navm']: e for e in navi['info']}
links = {e['navm']: e for e in navi['links']}
check('NAVI has one entry each per mesh', set(info) == set(meshes) == set(links))
wrong = {'pos': 0, 'value': 0, 'doors': 0, 'joined': 0, 'preferred': 0, 'place': 0, 'space': 0, 'side': 0}
for k, m in meshes.items():
    e = info[k]
    c = m['cell']
    outside = c in gd.ext_cells
    place = N.grid_place(*gd.cell_grid(c)) if outside else 0
    space = gd.ext_cells[c] if outside else c
    f = N.info_for(m, k, space, place)
    wrong['pos'] += max(abs(a - b) for a, b in zip(f['pos'], e['pos'])) > 0.1
    wrong['value'] += abs(f['value'] - e['value']) > 1e-5
    wrong['place'] += f['place'] != e['place']
    wrong['space'] += f['space'] != e['space']
    li = N.links_for(m, k)
    g = links[k]
    wrong['doors'] += li['doors'] != g['doors']
    wrong['joined'] += set(li['adjacent']) != set(g['adjacent'])
    wrong['preferred'] += set(li['preferred']) != set(g['preferred'])
    wrong['side'] += N.grid_side(len(m['tris'])) != m['grid']['side']
for what, n in wrong.items():
    check('NVMI/NVCI %s worked out for every mesh' % what, n == 0, '%d wrong' % n if n else '')

# --- the game's own meshes are sound by our checks (bar the handful of stale links it ships with) ---

problems = {k: N.validate(m, meshes, k) for k, m in meshes.items()}
stale = sum(1 for v in problems.values() if v)
check('validate finds at most the game\'s known faults', stale <= 70, '%d of %d meshes' % (stale, len(meshes)))
kinds = {w for v in problems.values() for x in v for w in ('link back', 'has no triangle', 'door') if w in x}
check('...which are all links to other meshes or a door', kinds <= {'link back', 'has no triangle', 'door'}, str(kinds))

# build_grid against the game's: every game entry of a small sample is either ours or a near miss
total = extra = missing = 0
for m in list(meshes.values())[:400]:
    g = N.build_grid(m['verts'], m['tris'])
    if g['side'] != m['grid']['side'] or g['min'] != m['grid']['min']:
        continue
    for a, b in zip(g['cells'], m['grid']['cells']):
        total += len(b)
        missing += len(set(b) - set(a))
        extra += len(set(a) - set(b))
check('build_grid matches the game\'s grids within 3%', total and (missing + extra) / total < 0.03,
      '%d entries, %d only in the game\'s, %d only in ours' % (total, missing, extra))

# a mesh made here goes through the writer and comes back the same
some = next(m for m in meshes.values() if m['ext'] and m['doors'])
fresh = {k: v for k, v in some.items() if k not in ('order', 'counts')}
data = N.write_navm(fresh)
check('a mesh without its record\'s order writes as the game would', data == N.write_navm(some))

# --- generating ---


def sound(name, m, others=None, navm=None):
    v = N.validate(m, others, navm)
    check(name + ': valid', not v, '; '.join(v[:3]))
    check(name + ': anticlockwise from above', all(
        (m['verts'][t[1]][0] - m['verts'][t[0]][0]) * (m['verts'][t[2]][1] - m['verts'][t[0]][1])
        - (m['verts'][t[1]][1] - m['verts'][t[0]][1]) * (m['verts'][t[2]][0] - m['verts'][t[0]][0]) > 0 for t in m['tris']))
    check(name + ': record comes back the same', N.write_navm(N.read_navm(N.write_navm(m))) == N.write_navm(m))


small = next(c for c in gd.interiors if gd.edid(c) == 'NovacAbandonedShack')
game = [N.read_navm(p.data(r)) for _i, r in gd.navmeshes(small)]
t0 = time.time()
m, rep = navgen.generate(gd, small)
check('small interior generated', m is not None and rep['triangles'] > 0,
      '%d triangles (game %d), %.1fs' % (rep['triangles'], sum(len(x['tris']) for x in game), time.time() - t0))
sound('small interior', m)
c = navgen.compare(game, m)
check('small interior covers most of the game\'s floor', c['game_covered'] > 0.6, '%.0f%%' % (100 * c['game_covered']))
check('small interior stays mostly where the game\'s is', c['ours_on_game'] > 0.6, '%.0f%%' % (100 * c['ours_on_game']))

# doors
doors = rep['doors']
check('the shack\'s door is seen', bool(doors))
found, missed = N.link_doors(m, doors)
check('its door is tied to a triangle', not missed and len(found) == len(doors))
sound('small interior with door', m)
ref = doors[0][0]
check('door link bytes as the game\'s', N.door_link(0x1234, found[ref]) == struct.pack('<IHH', 0x1234, found[ref], 0))
li = N.links_for(m, 0x800)
check('NVCI lists the door', li['doors'] == [d[0] for d in doors])
inf = N.info_for(m, 0x800, small)
check('NAVI entries encode', N.read_nvmi(N.write_nvmi(inf))['navm'] == 0x800 and N.read_nvci(N.write_nvci(li)) == li)
nv = N.new_navi([inf], [li])
check('a new NAVI comes back the same', N.write_navi(N.read_navi(N.write_navi(nv))) == N.write_navi(nv))

# outside: two neighbouring cells, generated and joined
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
A, B = (10, 10), (11, 10)
ca, cb = gd.grid(world)[A], gd.grid(world)[B]
t0 = time.time()
ma, ra = navgen.generate(gd, ca)
mb, rb = navgen.generate(gd, cb)
check('exterior cells generated', ma is not None and mb is not None,
      '%d and %d triangles (game %d, %d), %.1fs' % (ra['triangles'], rb['triangles'],
      sum(len(N.read_navm(p.data(r))['tris']) for _i, r in gd.navmeshes(ca)),
      sum(len(N.read_navm(p.data(r))['tris']) for _i, r in gd.navmeshes(cb)), time.time() - t0))
sound('exterior cell', ma)
line = (A[0] + 1) * N.CELL_SIZE
check('its corners stay in its cell', all(A[0] * N.CELL_SIZE <= v[0] <= line and A[1] * N.CELL_SIZE <= v[1] <= (A[1] + 1) * N.CELL_SIZE
                                          for v in ma['verts']))
c = navgen.compare([N.read_navm(p.data(r)) for _i, r in gd.navmeshes(ca)], ma, step=32.0)
check('exterior covers most of the game\'s ground', c['game_covered'] > 0.6, '%.0f%%' % (100 * c['game_covered']))
IA, IB = 0x7000001, 0x7000002
n = N.link_edges(ma, IA, A, mb, IB, B)
check('the two cells join along their border', n > 0, '%d edges' % n)
N.refresh(ma)
N.refresh(mb)
both = {IA: ma, IB: mb}
sound('joined cell A', ma, both, IA)
sound('joined cell B', mb, both, IB)
check('NVCI names the neighbour', N.links_for(ma, IA)['adjacent'] == [IB] and N.links_for(mb, IB)['adjacent'] == [IA])
# every joined edge really does meet its partner on the border
apart = 0
for t in ma['tris']:
    for i in range(3):
        if t[6] >> i & 1:
            a, b = ma['verts'][t[i]], ma['verts'][t[(i + 1) % 3]]
            apart += abs(a[0] - line) > 0.5 or abs(b[0] - line) > 0.5
check('joined edges lie on the border', apart == 0)

# linking to a game mesh: its triangles stay as they are, it only gains links
# (as when replacing the game's mesh of cell A: ours takes its form ID, and the neighbour's links to it are redone)
ours = {r.formid for _i, r in gd.navmeshes(ca)}
pair = None
for dx, dy in ((-1, 0), (0, -1), (0, 1)):
    gx, gy = A[0] + dx, A[1] + dy
    for _i, r in gd.navmeshes(gd.grid(world).get((gx, gy), 0)):
        g0 = N.read_navm(p.data(r))
        on_border = [e for e in g0['ext'] if e[1] in ours]
        if on_border and not pair:
            pair = (r.formid, g0, on_border[0][1], (gx, gy))
check('a game mesh next door links to cell A', pair is not None)
if pair:
    nid, g0, replaced, (gx, gy) = pair
    tris0 = [t[:3] for t in g0['tris']]
    verts0 = len(g0['verts'])
    n = N.link_edges(ma, replaced, A, g0, nid, (gx, gy), split_b=False)
    N.refresh(ma)
    N.refresh(g0, grid=False)
    check('joined to a mesh of the game\'s', n > 0, '%d edges' % n)
    check('the game\'s triangles keep their numbers', [t[:3] for t in g0['tris']] == tris0 and len(g0['verts']) == verts0)
    check('none of its links still name old triangles of the mesh replaced',
          all(t < len(ma['tris']) for k, i, t in g0['ext'] if i == replaced))
    sound('game neighbour after joining', g0, {replaced: ma}, nid)
