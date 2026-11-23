"""The Huáng's insides (huangset.py, huanginside.py): every piece builds and checks and is a closed model; what is sat or
lain on carries the game furniture's markers (read back from the model, as the game reads them); collision-only boxes
draw nothing; the halls keep settlerset's hall but for the painted door; each plan is walked from the arrival inside to
every room and every bed's and chair's side; homes differ; a mod-own door is a door to the navmesh builder."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import huanginside as HI  # noqa: E402
import huangset as HS  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import settlerset  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def markers_of(data):
    N = nif.Nif(data)
    out = []
    for i, t in enumerate(N.types):
        if (t.decode() if isinstance(t, bytes) else t) == 'BSFurnitureMarker':
            p = N.offsets[i]
            name, n = struct.unpack_from('<iI', data, p)
            p += 8
            for _k in range(n):
                x, y, z, o, a, b = struct.unpack_from('<fffHBB', data, p)
                p += 16
                out.append((round(x, 1), round(y, 1), round(z, 1), o, a, b))
            root_extras = struct.unpack_from('<I', data, N.offsets[0] + 4)[0]
            out.append(('root extras', root_extras, N.string(name)))
    return out


made = {}
for k in HS.PIECES:
    m = made[k] = HS.build(k)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids']) if hasattr(nifmake, 'check') else []
    check('%s builds, every block checked' % k, not wrong, wrong[:2])
    if hasattr(nifmake, 'open_edges'):          # (the closed-model check, where the app has it)
        check('%s is a closed model' % k, nifmake.open_edges(m['shapes']) < 0.5, round(nifmake.open_edges(m['shapes']), 1))
    check('%s\'s own pictures go with it' % k, all(t in m['files'] for t in m['textures']))
    mk = markers_of(m['nif'])
    want = HS.PIECES[k]['describe']().get('markers')
    if want:
        got = [r for r in mk if r[0] != 'root extras']
        check('%s carries the game furniture\'s markers' % k, len(got) == len(want) and all(abs(g[0] - w[0]) < 0.11 and g[3] == w[3] for g, w in zip(got, want)), got)
        check('%s\'s marker hangs on its root as FRN' % k, any(r[0] == 'root extras' and r[2] == 'FRN' for r in mk), mk[-1:])
    else:
        check('%s has no markers' % k, not mk)

bed = made['huang_bed']
check('the bed\'s collision box at its head draws nothing (its lattice shows)', 'textures\\folab\\huang\\window.dds' in [s['tex'] for s in bed['shapes']]
      and sum(len(s['i']) for s in bed['shapes'] if s['tex'].endswith('rosewood.dds')) // 3 < 260)
hall, plain = HS.hall(), settlerset.hall()
check('the hall is settlerset\'s but for the painted door', len(hall['parts']) == len(plain['parts']) - 2
      and not any(p.get('look') == 'door' for p in hall['parts']))
check('the hall keeps every other solid part', sum(1 for p in hall['parts'] if p.get('solid', True)) == sum(1 for p in plain['parts'] if p.get('solid', True)) - 1)

gd = gamedata.GameData()
for role, n in (('home', 0), ('home', 1), ('elders', 0), ('granary', 0)):
    r = HI.walk(gd, role, n)
    missed = [g['label'] for g in r['goals'] if not g['reached']]
    check('%s %d: every room and every bed\'s and chair\'s side walked to from the arrival' % (role, n), not missed and r['ok'], missed[:3])
    check('%s %d: nothing walked on that isn\'t drawn' % (role, n), not r['invisible'], r['invisible'][:2])
check('homes differ', len({tuple(sorted(HI.variant(k).items())) for k in range(4)}) == 4)
a, b = HI.plan('home', 0)[1], HI.plan('home', 1)[1]
check('the second home is the first mirrored, its bed another colour', a[0][1] == -b[0][1] or any(p[0] != q[0] for p, q in zip(a, b)))

import navbuild  # noqa: E402
import navgen  # noqa: E402
src = open(navbuild.__file__, encoding='utf-8').read() + open(navgen.__file__, encoding='utf-8').read()
check('a door of the mod\'s own is a door to the navmesh builder', "row['door'] = True" in src and "r.get('door')" in src)
