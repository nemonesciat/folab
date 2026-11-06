"""A new vault's first navmesh, made as the Kit tab makes it, before any door is linked: it covers the vault on every level,
not only the lowest scrap of floor. Nothing goes near the real game."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse
import gamedata
import kitdress as D
import kitindex as K
import kitplan as P
import navbuild
import project
import recordio


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


B = chr(92)
G = gamedata.GameData()
kits = K.build(G)
sv = D.survey(G, kits, only={'dungeons' + B + 'vault'})
BR = browse.Browse(G, lambda: None)
src = next(c for c in G.interiors if G.edid(c) == 'Vault3a')


def floor_area(mesh):
    V, area = mesh['verts'], 0.0
    for t in mesh['tris']:
        a, b, c = V[t[0]], V[t[1]], V[t[2]]
        area += abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
    return area


store, cache = {}, {}
for seed in (5, 6, 7, 8):
    made = P.vault(G, kits, 4, seed, [0, 0, 0], store, cache, sv)
    check('vault %d: made' % seed, bool(made.get('ops')), made.get('note', ''))
    if not made.get('ops'):
        continue
    pr = project.Project.create('Vault Nav %d' % seed)
    rec = BR.record(G.key(src))['record']
    rec['type'], rec['src'] = 'CELL', rec.get('src', '')
    recordio.set_field(rec, 'EDID', 'VaultNav%d' % seed, label='Editor ID')
    recordio.set_field(rec, 'FULL', 'Vault Nav', label='Name')
    cell = pr.apply('New place', [{'op': 'record_new', 'record': rec}])[0]
    pr.apply('Start marker', [{'op': 'add', 'cell': cell, 'base': G.key(next(f for f in G.forms if G.edid(f) == 'COCMarkerHeading')), 'p': [0, 0, 0, 0, 0, 0], 's': 1}])
    pr.apply('Make a vault', [dict(o, cell=cell) for o in made['ops']])
    refs = navbuild.place_refs(G, pr, cell)
    doors = [r for r in refs if r['base'] in G.forms and G.forms[r['base']][1].tag == 'DOOR']
    check('… it has doors, none linked yet', doors and not any(r['leads'] for r in doors), '%d doors' % len(doors))
    data, report = navbuild.generate(G, pr, cell)
    squares = floor_area(data) / (256.0 * 256.0)
    zs = [v[2] for v in data['verts']]
    check('… its first navmesh covers the vault, not a scrap: %.0f squares, %d triangles' % (squares, report['triangles']), squares >= 60)
    print('      %s  heights %d to %d' % (made.get('said', '').split(' Walked')[0], min(zs), max(zs)))
