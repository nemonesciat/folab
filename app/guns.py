"""FOLab's own guns (docs/folab-guns.md): models made in FOLab, each riding on one of the game's guns for its hold and
its animations (the moving parts named and placed as that gun's), firing what another of the game's guns fires.

  qlz87     the QLZ-87, China's 35 mm automatic grenade launcher: stock, pistol grip, a drum under the receiver ahead of
            the grip, a bipod folded under the barrel, a big muzzle brake. Rides on the Light Machine Gun (its drum is the
            LMG's box, `##riotClip`, taken off and put back by ReloadI; its charging handle is `##riotMechanism`, which
            every shot of AttackLoop slides back); fires the Grenade Machinegun's 25mm grenades.

    build(name)                 {'nif', 'files', 'mesh', 'box', 'parts': {node: shapes}, ...}
    weapon(gd, name, made, fp)  the WEAP record; fp the key of its first-person static (first_person)
    put_in(pr, gd, name)        its files among the mod's own and its two records, one Undo: returns the weapon's key

Who carries them is the user's (Waikiki: Huang's people carry the Chinese weapons)."""
import math

import gunmake
from gunmake import Mesh, box, prism, turned, ring, rod
import texpaint as tp

TEX = 'textures\\folab\\weapons\\%s.dds'
NORMAL = 'textures\\folab\\weapons\\%s_n.dds'

# name: (shown name, the game gun it rides on, the game gun whose ammo and projectile it fires, clip, weight, value, mass)
GUNS = {
    'qlz87': ('QLZ-87', 'WeapNVLightMachineGun', 'WeapNVGrenadeMachinegun', 15, 18.0, 6000, 9.0),
}

# Where the ride-on gun's moving parts lie, in its frame (read from its model: tests/test_guns.py checks these against the
# game's file). A part of ours that the animations move must sit where that part sits, near enough for the hands.
BASE_PARTS = {
    'WeapNVLightMachineGun': {
        '##riotClip': ((6.19, -1.04, -3.25), (12.87, 5.34, 3.17)),
        '##riotMechanism': ((11.17, 4.63, 1.56), (12.54, 6.44, 4.39)),
        '##Trigger': ((3.2, -0.04, -0.25), (4.16, 1.83, 0.19)),
        'ProjectileNode': (53.59, 7.28, 0.0),
        '##SightingNode': (-18.44, 10.68, -0.04),
    },
}


# ---------- textures ----------

def steel(size=128, seed=301):
    """Dark phosphated steel: a little mottled, fine scratches worn bright."""
    c = tp.Canvas(size, size)
    big, fine, scr = tp.Noise(seed, 8), tp.Noise(seed + 1, 64), tp.Noise(seed + 2, 16)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        b = big.at(u * 8, v * 8)
        f = fine.at(u * 64, v * 64)
        s = scr.at(u * 16, v * 2)
        col = tp._shade((54, 57, 54), 0.85 + 0.25 * b + 0.1 * f)
        if s > 0.8:
            col = tp._mix(col, (120, 122, 118), (s - 0.8) * 3)
        return col, 0.5 + 0.04 * f
    c.paint(fn)
    return c


def olive(size=128, seed=302):
    """Olive drab paint over steel, chipped here and there to the dark metal, a little dust."""
    c = tp.Canvas(size, size)
    big, fine, chip = tp.Noise(seed, 6), tp.Noise(seed + 1, 64), tp.Noise(seed + 2, 24)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        b = big.at(u * 6, v * 6)
        f = fine.at(u * 64, v * 64)
        k = chip.at(u * 24, v * 24)
        if k > 0.82:
            return tp._shade((58, 58, 54), 0.9 + 0.1 * f), 0.44
        col = tp._shade((86, 92, 60), 0.88 + 0.2 * b + 0.08 * f)
        col = tp._mix(col, (140, 128, 100), max(0.0, b - 0.7) * 0.6)
        return col, 0.5 + 0.03 * f
    c.paint(fn)
    return c


def black(size=128, seed=303):
    """Black polymer and rubber: a fine stipple for the grip."""
    c = tp.Canvas(size, size)
    fine, big = tp.Noise(seed, 64), tp.Noise(seed + 1, 8)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        f = fine.at(u * 64, v * 64)
        b = big.at(u * 8, v * 8)
        return tp._shade((36, 36, 34), 0.85 + 0.25 * f + 0.1 * b), 0.45 + 0.12 * f
    c.paint(fn)
    return c


TEXTURES = {'qlz_steel': steel, 'qlz_olive': olive, 'qlz_black': black}
GLOSS = {'qlz_steel': 40.0, 'qlz_olive': 18.0, 'qlz_black': 10.0}
SHINE = {'qlz_steel': 60, 'qlz_olive': 25, 'qlz_black': 12}
_drawn = {}


def texture_files(key):
    if key not in _drawn:
        _drawn[key] = TEXTURES[key]().files(game=True, shine=SHINE[key])
    return _drawn[key]


def _m(key):
    return Mesh(TEX % key, NORMAL % key, gloss=GLOSS[key])


# ---------- the QLZ-87 ----------

BORE = 7.0              # (the barrel's axis: y; the LMG's muzzle is at 7.28)
SIGHT = 10.68           # (the sight line: the LMG's ##SightingNode)
MUZZLE = 51.6


def qlz87():
    """(parts, marks) in the Light Machine Gun's frame: x forward, y up, z right, the grip at the origin."""
    st, ol, bk = _m('qlz_steel'), _m('qlz_olive'), _m('qlz_black')
    # the receiver: a long box, its top edges cut off
    prism(ol, [(-6.0, 4.2), (14.0, 4.2), (14.0, 9.0), (13.0, 9.6), (-5.0, 9.6), (-6.0, 8.8)], -2.3, 2.3)
    box(st, (-4.0, 9.6, -0.9), (12.0, 10.0, 0.9))                       # the top rail
    box(bk, (5.0, 6.2, 2.3), (9.0, 8.2, 2.42))                          # the ejection port (right side)
    box(st, (1.0, 6.4, -2.42), (3.2, 7.6, -2.3))                        # the selector (left side)
    # the stock: a skeleton of a butt, its comb below the sight line, a rubber pad
    prism(ol, [(-6.0, 4.2), (-6.0, 8.8), (-20.0, 8.0), (-21.0, 7.4), (-21.0, 0.8), (-20.0, 0.2), (-15.0, 1.2), (-8.0, 3.6)], -1.6, 1.6)
    box(bk, (-17.0, 8.0, -1.4), (-9.0, 8.7, 1.4))                       # cheek rest
    box(bk, (-22.2, 0.3, -1.9), (-21.0, 7.9, 1.9))                      # butt pad
    # the pistol grip and the trigger guard
    prism(bk, [(-0.8, 4.2), (2.4, 4.2), (1.6, 0.0), (0.6, -5.2), (-0.4, -5.9), (-2.6, -5.6), (-2.0, -1.0), (-1.2, 2.4)], -1.25, 1.25)
    box(st, (1.4, -0.9, -0.45), (6.2, -0.3, 0.45))
    box(st, (5.6, -0.9, -0.45), (6.2, 4.2, 0.45))
    # the barrel, its handguard (an octagon, banded), the collar the bipod hangs from, the muzzle brake
    turned(st, 'x', (0, BORE, 0), [(14.0, 1.8), (46.5, 1.8)], sides=16)
    turned(ol, 'x', (0, BORE, 0), [(14.0, 2.9), (31.0, 2.9)], sides=8, flat=True)
    for x in (17.0, 22.0, 27.0):
        turned(st, 'x', (0, BORE, 0), [(x, 3.05), (x + 0.8, 3.05)], sides=8, flat=True)
    turned(st, 'x', (0, BORE, 0), [(33.0, 2.3), (35.6, 2.3)], sides=12)
    turned(st, 'x', (0, BORE, 0), [(46.3, 2.0), (46.8, 2.5), (49.0, 2.5), (49.2, 2.2), (49.6, 2.2), (49.8, 2.5), (51.6, 2.5)], sides=12)
    ring(st, 'x', (0, BORE, 0), 51.5, 51.65, 1.0, 2.45, sides=12)       # (the brake's mouth: the bore shows dark)
    box(bk, (46.9, BORE - 0.6, -2.6), (48.8, BORE + 0.6, 2.6))          # its side ports
    # the bipod, folded forward under the barrel
    box(st, (33.4, 3.9, -1.3), (35.2, 4.8, 1.3))
    for side in (-1.0, 1.0):
        rod(st, (34.3, 4.3, side * 1.0), (47.6, 4.5, side * 1.5), 0.42, sides=6)
        box(st, (47.2, 3.9, side * 1.5 - 0.6), (48.6, 5.1, side * 1.5 + 0.6))
    # the sights: a ring at the back, a post between ears at the front, on the sight line
    box(st, (-1.3, 9.6, -0.35), (-0.7, 10.0, 0.35))
    ring(st, 'x', (0, SIGHT, 0), -1.3, -0.7, 0.42, 0.95)
    turned(st, 'x', (0, BORE, 0), [(42.4, 2.0), (43.6, 2.0)], sides=12)
    box(st, (42.85, BORE + 1.8, -0.17), (43.2, SIGHT - 0.05, 0.17))
    for side in (-1.0, 1.0):
        box(st, (42.8, BORE + 1.8, side * 0.9 - 0.18), (43.3, SIGHT + 0.5, side * 0.9 + 0.18))
    body = [st.shape(), ol.shape(), bk.shape()]

    # the drum (the LMG's box): a round drum, its face to the sides, hubs, a winding key; the neck goes up into the receiver
    dr, dk = _m('qlz_olive'), _m('qlz_steel')
    turned(dr, 'z', (11.4, 0.4, 0), [(-3.3, 4.6), (-3.0, 5.0), (3.0, 5.0), (3.3, 4.6)], sides=20)
    for z in (-1.4, 1.4):
        turned(dk, 'z', (11.4, 0.4, 0), [(z - 0.3, 5.12), (z + 0.3, 5.12)], sides=20)
    turned(dk, 'z', (11.4, 0.4, 0), [(-3.9, 1.4), (3.9, 1.4)], sides=12)
    box(dk, (10.9, -0.6, -4.4), (11.9, 1.4, -3.9))                      # winding key (left)
    box(dr, (8.6, 4.2, -2.0), (14.0, 5.0, 2.0))                         # neck
    drum = [dr.shape(), dk.shape()]

    # the charging handle (right side), which each shot slides back
    ch = _m('qlz_steel')
    box(ch, (10.6, 6.6, 2.3), (12.2, 7.6, 3.2))
    box(ch, (11.0, 6.7, 3.2), (12.0, 7.5, 4.1))
    handle = [ch.shape()]

    # the trigger
    tr = _m('qlz_steel')
    prism(tr, [(3.3, 4.2), (3.9, 4.2), (4.3, 2.5), (4.1, 0.4), (3.6, 0.1), (3.7, 1.4), (3.5, 3.0)], -0.22, 0.22)
    trigger = [tr.shape()]

    parts = [('##riotClip', drum), ('##riotMechanism', handle), ('##Trigger', trigger), (None, body)]
    marks = [('ProjectileNode', (MUZZLE, BORE, 0.0), gunmake.FORWARD),
             ('ShellCasingNode', (7.0, 7.2, 2.5), gunmake.CASE_OUT),
             ('##SightingNode', (-18.44, SIGHT, 0.0), gunmake.FORWARD)]
    return parts, marks


SHAPES = {'qlz87': qlz87}


def build(name):
    shown, base, fires, clip, weight, value, mass = GUNS[name]
    parts, marks = SHAPES[name]()
    nif = gunmake.build_gun('FOLab%s' % name.upper(), parts, marks, mass=mass)
    mesh = 'meshes\\folab\\weapons\\%s.nif' % name
    files = {mesh: nif}
    for _n, ss in parts:
        for s in ss:
            key = s['tex'].split('\\')[-1][:-4]
            files[TEX % key], files[NORMAL % key] = texture_files(key)
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for _n, ss in parts for s in ss for k in range(0, len(s['p']), 3)]
    bx = [int(math.floor(min(q[k] for q in pts))) for k in range(3)] + [int(math.ceil(max(q[k] for q in pts))) for k in range(3)]
    return {'nif': nif, 'files': files, 'mesh': mesh, 'box': bx, 'base': base, 'fires': fires, 'shown': shown,
            'parts': {n: ss for n, ss in parts}, 'marks': {n: t for n, t, _r in marks}}


# ---------- records ----------

def _game(gd, edid, tag):
    return next(f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid and (f >> 24) == 0)


def first_person(name, made):
    """The first-person model's record: a static naming the same model, as the game's 1stPerson statics do."""
    return {'type': 'STAT', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FOLab1stPerson%s' % name.upper()},
        {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': 0} for n in ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2')]},
        {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': made['mesh'][7:]}]}


# what the weapon takes from the gun whose rounds it fires: whole subrecords, and these of DNAM's numbers
FROM_FIRES = ('NAM0', 'REPL', 'ETYP', 'MOD2', 'INAM', 'SNAM', 'XNAM', 'TNAM', 'ICON', 'MICO', 'CRDT', 'VATS', 'VNAM')
DNAM_FROM_FIRES = ('Projectile', 'Skill', 'Min spread', 'Spread', 'Min range', 'Max range', 'Fire rate', 'Attack shots per second',
                   'Override action points', 'V.A.T.S. to-hit chance', 'Rumble left motor', 'Rumble right motor', 'Rumble duration',
                   'Rumble pattern', 'Rumble wavelength', 'Strength needed')
# what it has of neither: the ride-on gun's mods are its own
DROP = ('MODT', 'MODS', 'MOD4', 'MO4T', 'MO4S', 'MWD1', 'MWD2', 'MWD3', 'MWD4', 'MWD5', 'MWD6', 'MWD7', 'WNM1', 'WNM2', 'WNM3', 'WNM4',
        'WNM5', 'WNM6', 'WNM7', 'WMI1', 'WMI2', 'WMI3', 'WMS1', 'WMS2', 'EITM', 'EAMT')
NO_MODS = {'Mod 1 effect': 0, 'Mod 2 effect': 0, 'Mod 3 effect': 0, 'Mod 1 value': 0.0, 'Mod 2 value': 0.0, 'Mod 3 value': 0.0,
           'Mod 1 value B': 0.0, 'Mod 2 value B': 0.0, 'Mod 3 value B': 0.0}


def weapon(gd, name, made, fp_key):
    """The weapon: the ride-on gun's record (its hold, reload and fire animations, its pick-up sounds), with the fire gun's
    rounds, projectile, sounds and numbers, this model, name, clip, weight and value, and no mods."""
    import recordio
    shown, base, fires, clip, weight, value, _mass = GUNS[name]
    rec = recordio.load(gd, _game(gd, base, 'WEAP'))
    other = recordio.load(gd, _game(gd, fires, 'WEAP'))
    rec['src'] = ''
    theirs = {}
    for s in other['subs']:
        theirs.setdefault(s['tag'], []).append(s)
    their_dnam = {f.get('name'): f.get('value') for f in theirs['DNAM'][0]['fields']}
    subs, taken = [], set()
    for s in rec['subs']:
        t = s['tag']
        if t in DROP:
            continue
        if t in FROM_FIRES:
            if t not in taken:
                subs += [dict(q) for q in theirs.get(t, [])]
                taken.add(t)
            continue
        s = dict(s)
        if t == 'EDID':
            s['value'] = 'FOLabWeap%s' % name.upper()
        elif t == 'FULL':
            s['value'] = shown
        elif t == 'MODL':
            s['value'] = made['mesh'][7:]
        elif t == 'WNAM':
            s['value'] = fp_key
        elif t == 'OBND':
            s['fields'] = [dict(f, value=v) for f, v in zip(s['fields'], made['box'])]
        elif t == 'DATA':
            want = {'Value': value, 'Weight': weight, 'Clip size': clip, 'Damage': {f.get('name'): f.get('value') for f in theirs['DATA'][0]['fields']}['Damage']}
            s['fields'] = [dict(f, value=want.get(f.get('name'), f.get('value'))) for f in s['fields']]
        elif t == 'DNAM':
            s['fields'] = [dict(f, value=NO_MODS[f['name']] if f.get('name') in NO_MODS else their_dnam[f['name']] if f.get('name') in DNAM_FROM_FIRES else f.get('value'))
                           for f in s['fields']]
        subs.append(s)
    # (what the fire gun has that the ride-on gun hasn't, put after the model: its own order isn't the game's concern)
    for t in FROM_FIRES:
        if t not in taken and t in theirs:
            subs += [dict(q) for q in theirs[t]]
    rec['subs'] = subs
    return rec


CRATE = 'VLootGunsFootlocker01Gen05'      # (a footlocker: no script, doesn't refill)


def test_crate(gd, edid, things):
    """TEST ONLY: a footlocker of the mod's own holding exactly `things` [(item key, count)], for a look at a gun in game;
    taken out again afterwards."""
    import recordio
    rec = recordio.load(gd, _game(gd, CRATE, 'CONT'))
    rec['src'] = ''
    one = next(s for s in rec['subs'] if s['tag'] == 'CNTO')
    subs, put = [], False
    for s in rec['subs']:
        if s['tag'] in ('MODT', 'CNTO', 'COED'):
            if s['tag'] == 'CNTO' and not put:
                subs += [dict(one, fields=[dict(f, value=k if f.get('name') == 'Item' else n if f.get('name') == 'Count' else f.get('value'))
                                           for f in one['fields']]) for k, n in things]
                put = True
            continue
        s = dict(s)
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = 'Footlocker'
        subs.append(s)
    rec['subs'] = subs
    return rec


def put_in(pr, gd, name):
    """The gun's files among the mod's own (written afresh) and its first-person static and weapon, one Undo. Returns
    (the weapon's key, what build made)."""
    import os
    import library
    made = build(name)
    root = library.assets_dir(pr)
    for rel, data in made['files'].items():
        full = os.path.join(root, rel)
        if not os.path.isfile(full) or open(full, 'rb').read() != data:
            library._put(root, rel, data)
    ops, key = gun_ops(pr, gd, name, made)
    pr.apply('Gun: ' + GUNS[name][0], ops)
    return key, made


def gun_ops(pr, gd, name, made):
    """The ops making the gun's two records, if they're the first ops applied: (ops, the weapon's key to be)."""
    fp_key = '+%06X' % pr.next_id
    return ([{'op': 'record_new', 'record': first_person(name, made)},
             {'op': 'record_new', 'record': weapon(gd, name, made, fp_key), 'name': 'gun_' + name}], '+%06X' % (pr.next_id + 1))
