"""guns: FOLab's own guns are laid out as the game's (named parts each on a node with an empty transform controller, at the
gun's origin; the muzzle, case and sight markers; BSXFlags 67, held by the Weapon bone, a loose body on the weapons' layer),
their moving parts lie where the ride-on gun's lie (so the game's reload and fire animations move them under the hands),
their faces turn out, and their records take the ride-on gun's animations and the fire gun's rounds."""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import guns  # noqa: E402
import nif  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


def nodes_of(data):
    """{name: (block, parsed)} for every node, and the root."""
    n = nif.Nif(data)
    out = {}
    for i, t in enumerate(n.types):
        if t in ('NiNode', 'BSFadeNode'):
            b = n.block(i)
            out[b['name']] = (i, b)
    return n, out


def bounds(shapes):
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for s in shapes for k in range(0, len(s['p']), 3)]
    return [min(q[a] for q in pts) for a in range(3)], [max(q[a] for q in pts) for a in range(3)]


def middle(lo, hi):
    return [(lo[a] + hi[a]) / 2 for a in range(3)]


for name in guns.GUNS:
    m = guns.build(name)
    data = m['nif']
    n, nodes = nodes_of(data)
    raw = lambda i: data[n.offsets[i]:n.offsets[i] + n.sizes[i]]
    root = n.block(0)
    extras = [struct.unpack('<ii', raw(i)) for i, t in enumerate(n.types) if t == 'NiStringExtraData']
    check(name + ': held by the Weapon bone', any(n.string(a) == 'Prn' and n.string(b) == 'Weapon' for a, b in extras))
    check(name + ': BSXFlags 67, as the game\'s guns', struct.unpack('<iI', raw(n.types.index('BSXFlags')))[1] == 67)
    body = raw(n.types.index('bhkRigidBody'))
    check(name + ': a loose body on the weapons\' layer', len(body) == 236 and body[4] == 5)
    base = guns.BASE_PARTS[m['base']]
    for part in ('##riotClip', '##riotMechanism', '##Trigger'):
        if part not in m['parts']:
            continue
        i, b = nodes.get(part, (None, None))
        check(name + ': ' + part + ' is a node of the root, at its origin, unturned', b is not None and i in root['children']
              and all(abs(v) < 1e-6 for v in b['t']) and all(abs(b['R'][r][c] - (r == c)) < 1e-6 for r in range(3) for c in range(3)))
    for nm, (i, b) in nodes.items():
        if i == 0:
            continue
        c = b['controller']
        ok = c >= 0 and n.types[c] == 'NiTransformController'
        if ok:
            _nx, _fl, _f, _p, _s, _e, target, interp = struct.unpack('<iHffffii', raw(c))
            ok = target == i and n.types[interp] == 'NiTransformInterpolator' and raw(interp)[:4] == struct.pack('<f', 3.4028234663852886e+38)
        check(name + ': ' + nm + ' carries an empty transform controller', ok)
    # where the parts lie against the ride-on gun's
    lo, hi = bounds(m['parts']['##riotClip'])
    blo, bhi = base['##riotClip']
    mid, bmid = middle(lo, hi), middle(blo, bhi)
    check(name + ': the drum where the hands take the box', math.dist(mid, bmid) < 3.5 and lo[0] > 5.0, (mid, bmid))
    lo, hi = bounds(m['parts']['##Trigger'])
    blo, bhi = base['##Trigger']
    check(name + ': the trigger under the finger', all(lo[a] < bhi[a] + 0.5 and hi[a] > blo[a] - 0.5 for a in range(3)), (lo, hi))
    lo, hi = bounds(m['parts']['##riotMechanism'])
    mid, bmid = middle(lo, hi), middle(*base['##riotMechanism'])
    check(name + ': the charging handle on the right, near the LMG\'s', lo[2] > 2.0 and math.dist(mid, bmid) < 3.0, (mid, bmid))
    marks = m['marks']
    check(name + ': the muzzle ahead of everything, at the barrel\'s height', marks['ProjectileNode'][0] >= max(
        bounds([s for ss in m['parts'].values() for s in ss])[1][0] - 0.1, 0) and abs(marks['ProjectileNode'][1] - base['ProjectileNode'][1]) < 0.5)
    check(name + ': the eye where the LMG\'s is', math.dist(marks['##SightingNode'], base['##SightingNode']) < 0.1)
    # nothing stands in the sight line between the rear ring and the front post but those
    every = [s for ss in m['parts'].values() for s in ss]
    blocked = 0
    for s in every:
        p = s['p']
        for k in range(0, len(p), 3):
            x, y, z = p[k:k + 3]
            if -0.6 < x < 42.7 and abs(z) < 0.3 and abs(y - marks['##SightingNode'][1]) < 0.35:
                blocked += 1
    check(name + ': the sight line clear', blocked == 0, blocked)
    # every triangle faces the way its corners' normals do
    bad = 0
    for s in every:
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
    back = nif.mesh_from_nif(data)
    check(name + ': the shapes read back', len(back) == len(every) and all(b['tex'].lower() == s['tex'].lower() for b, s in zip(back, every)))
    check(name + ': its textures go with it', all(s['tex'] in m['files'] and s['normal'] in m['files'] for s in every))

if '--no-game' not in sys.argv:
    import gamedata
    import recordio
    gd = gamedata.GameData()

    def kf_targets(path):
        d = gd.read_file(path)
        k = nif.Nif(d)
        names = set()
        for i, t in enumerate(k.types):
            if t == 'NiControllerSequence':
                p = k.offsets[i]
                _nm, nb, _g = struct.unpack_from('<iII', d, p)
                p += 12
                for _ in range(nb):
                    names.add(k.string(struct.unpack_from('<i', d, p + 9)[0]))
                    p += 29
        return names
    first = 'meshes\\characters\\_1stperson\\'
    check('the reload the QLZ-87 rides on moves the drum', '##riotClip' in kf_targets(first + '2hareloadi.kf'))
    check('every automatic shot moves the charging handle', '##riotMechanism' in kf_targets(first + '2haattackloop.kf'))
    for gun, parts in guns.BASE_PARTS.items():
        rec = recordio.load(gd, guns._game(gd, gun, 'WEAP'))
        model = next(s['value'] for s in rec['subs'] if s['tag'] == 'MODL')
        g = gd.read_file('meshes\\' + model)
        gn, gnodes = nodes_of(g)
        for part, want in parts.items():
            i, b = gnodes[part]
            if isinstance(want[0], tuple):
                shapes = [gn.block(c) for c in b['children']]
                pts = []
                for s in shapes:
                    v = gn.block(s['data'])['verts']
                    pts += [tuple(s['s'] * v[j + a] + s['t'][a] + b['t'][a] for a in range(3)) for j in range(0, len(v), 3)]
                lo = tuple(min(q[a] for q in pts) for a in range(3))
                hi = tuple(max(q[a] for q in pts) for a in range(3))
                ok = all(abs(lo[a] - want[0][a]) < 0.1 and abs(hi[a] - want[1][a]) < 0.1 for a in range(3))
            else:
                ok = all(abs(b['t'][a] - want[a]) < 0.05 for a in range(3))
            check('%s: %s lies where FOLab thinks' % (gun, part), ok)
    for name in guns.GUNS:
        m = guns.build(name)
        rec = guns.weapon(gd, name, m, '+000001')
        get = lambda t: next(s for s in rec['subs'] if s['tag'] == t)
        tags = [s['tag'] for s in rec['subs']]
        base = recordio.load(gd, guns._game(gd, m['base'], 'WEAP'))
        fires = recordio.load(gd, guns._game(gd, m['fires'], 'WEAP'))
        dn = lambda r: {f.get('name'): f.get('value') for f in next(s for s in r['subs'] if s['tag'] == 'DNAM')['fields']}
        mine, theirs, fire = dn(rec), dn(base), dn(fires)
        check(name + ': the ride-on gun\'s hold, reload and fire', all(mine[k] == theirs[k] for k in ('Animation type', 'Reload animation', 'Attack animation', 'Flags', 'Reload time')))
        check(name + ': the fire gun\'s rounds and projectile', get('NAM0')['value'] == next(s['value'] for s in fires['subs'] if s['tag'] == 'NAM0')
              and mine['Projectile'] == fire['Projectile'])
        check(name + ': its own model, name, clip; no mods', get('MODL')['value'] == m['mesh'][7:] and get('WNAM')['value'] == '+000001'
              and get('FULL')['value'] == m['shown'] and not any(t in tags for t in ('MODT', 'WMI1', 'MWD1', 'WNM1'))
              and {f['name']: f['value'] for f in get('DATA')['fields']}['Clip size'] == guns.GUNS[name][3] and mine['Mod 2 effect'] == 0)
        check(name + ': one of each subrecord the game has once', all(tags.count(t) == 1 for t in ('EDID', 'MODL', 'NAM0', 'DATA', 'DNAM', 'ETYP')))

    # into a mod of its own and out through the writer (only in a scratch home: tests/run.py gives one)
    if os.environ.get('FOLAB_HOME'):
        import espwrite
        import library
        import project
        import tes4
        pr = project.Project.create('Gun Test')
        key, made = guns.put_in(pr, gd, 'qlz87')
        root = library.assets_dir(pr)
        check('put_in: the model and its textures among the mod\'s own files', all(os.path.isfile(os.path.join(root, rel)) for rel in made['files']))
        path = pr.plugin_path()
        espwrite.write(gd, pr, path)
        gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
        me = len(gd2.plugins) - 1
        weap = next(f for f, (i, r) in gd2.forms.items() if r.tag == 'WEAP' and gd2.edid(f) == 'FOLabWeapQLZ87')
        i, r = gd2.source(weap)
        subs = dict(tes4.iter_subrecords(gd2.plugins[i].data(r)))
        fp = gd2.to_global(me, struct.unpack('<I', subs['WNAM'])[0])
        check('written: the weapon is the mod\'s, its first-person model the mod\'s static of the same model',
              i == me and gd2.forms[fp][1].tag == 'STAT' and gd2.edid(fp) == 'FOLab1stPersonQLZ87'
              and dict(tes4.iter_subrecords(gd2.plugins[me].data(gd2.forms[fp][1])))['MODL'].rstrip(b'\0').decode() == made['mesh'][7:])
        ammo = gd2.to_global(me, struct.unpack('<I', subs['NAM0'])[0])
        gmg = guns._game(gd, 'WeapNVGrenadeMachinegun', 'WEAP')
        their = dict(tes4.iter_subrecords(gd.plugins[gd.source(gmg)[0]].data(gd.source(gmg)[1])))
        check('written: it fires the Grenade Machinegun\'s rounds', ammo == struct.unpack('<I', their['NAM0'])[0])
        lmg = guns._game(gd, 'WeapNVLightMachineGun', 'WEAP')
        theirs = dict(tes4.iter_subrecords(gd.plugins[gd.source(lmg)[0]].data(gd.source(lmg)[1])))
        check('written: DNAM as long as the game\'s, the LMG\'s animation bytes', len(subs['DNAM']) == len(theirs['DNAM'])
              and subs['DNAM'][:4] == theirs['DNAM'][:4])
        for p in gd2.plugins:
            p.close()

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
