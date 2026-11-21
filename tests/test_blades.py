"""blades: the six Chinese and Japanese blades are weapons as the game lays its own out (the hand bone named, a loose body on the weapons'
layer, the grip at the origin, the business end along +y, one-handers and two-handers each the game's length), their
faces turned out, and their records build on the game weapon each is made after."""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import blades  # noqa: E402
import clubs  # noqa: E402
import nif  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


TWO = {'katana', 'naginata', 'yari'}
for name in blades.BLADES:
    m = blades.build(name)
    n = nif.Nif(m['nif'])
    for i in range(len(n.types)):
        n.block(i)
    raw = lambda i: m['nif'][n.offsets[i]:n.offsets[i] + n.sizes[i]]
    extras = [struct.unpack('<ii', raw(i)) for i, t in enumerate(n.types) if t == 'NiStringExtraData']
    check(name + ': held by the Weapon bone', any(n.string(a) == 'Prn' and n.string(b) == 'Weapon' for a, b in extras))
    bsx = struct.unpack('<iI', raw(n.types.index('BSXFlags')))[1]
    check(name + ': BSXFlags 66, as the game\'s melee weapons', bsx == 66, bsx)
    body = raw(n.types.index('bhkRigidBody'))
    check(name + ': a loose body on the weapons\' layer, as long as the game\'s', len(body) == 236 and body[4] == 5 and body[-24] == 4, (len(body), body[4]))
    mass = struct.unpack_from('<f', body, 4 * 45)[0]
    check(name + ': its weight', abs(mass - blades.BLADES[name][2]) < 1e-6, mass)
    b = m['box']
    if name in TWO:
        check(name + ': a two-hander\'s length, grip at the origin', -50 <= b[1] <= -16 and 55 <= b[4] <= 70, b)
    else:
        check(name + ': a one-hander\'s length, grip at the origin', -11 <= b[1] <= -3 and 30 <= b[4] <= 44, b)
    # every triangle faces the way its corners' normals do
    bad = 0
    for s in m['shapes']:
        p, nn, ii = s['p'], s['n'], s['i']
        for k in range(0, len(ii), 3):
            a, bb, c = ii[k:k + 3]
            P = [p[3 * a:3 * a + 3], p[3 * bb:3 * bb + 3], p[3 * c:3 * c + 3]]
            e1 = [P[1][j] - P[0][j] for j in range(3)]
            e2 = [P[2][j] - P[0][j] for j in range(3)]
            fn = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            av = [nn[3 * a + j] + nn[3 * bb + j] + nn[3 * c + j] for j in range(3)]
            bad += sum(fn[j] * av[j] for j in range(3)) < -1e-9
    check(name + ': every face turned out', bad == 0, bad)
    check(name + ': its textures go with it', all(s['tex'] in m['files'] and s['normal'] in m['files'] for s in m['shapes']))

check('Huang carry only theirs: the dao and the jian', blades.LISTS['huang'] == ['dao', 'jian'])
check('the Japanese are loot', blades.LISTS['japanese'] == ['katana', 'wakizashi', 'naginata', 'yari'])
if '--no-game' not in sys.argv:
    import gamedata
    gd = gamedata.GameData()
    for name in blades.BLADES:
        m = blades.build(name)
        rec = clubs.weapon(gd, name, m, '+000001')
        get = lambda t: next(s for s in rec['subs'] if s['tag'] == t)
        check(name + ': a weapon made after ' + m['base'], get('MODL')['value'] == m['mesh'][7:] and get('FULL')['value'] == m['shown'])

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
