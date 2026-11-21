"""FOLab's own guns (docs/folab-guns.md): models made in FOLab, each riding on one of the game's guns for its hold and
its animations (the moving parts named and placed as that gun's), firing what another of the game's guns fires.

  qlz87     the QLZ-87, China's 35 mm automatic grenade launcher: stock, pistol grip, a drum under the receiver ahead of
            the grip, a bipod folded under the barrel, a big muzzle brake. Rides on the Light Machine Gun (its drum is the
            LMG's box, `##riotClip`, taken off and put back by ReloadI; its charging handle is `##riotMechanism`, which
            every shot of AttackLoop slides back); fires the Grenade Machinegun's 25mm grenades.
  qsz92     the QSZ-92, the Chinese army's service pistol: polymer frame, steel slide, exposed hammer, a rail under the
            dust cover. Rides on the 9mm Pistol (slide `##nmBar`, hammer `##nmHammer`, magazine `##nmClip`, trigger
            `##nmTrigger`, as ReloadL moves them); fires the 9mm Pistol's rounds, 15 to the magazine.
  type81    the Type 81 rifle: Kalashnikov-like, wooden stock, grip and handguards, a gas tube over the barrel, a tall front
            sight, a curved 30-round magazine. Rides on the Assault Carbine (magazine `##Clip`, bolt carrier and its
            handle on the right `##ChargingHandle`, trigger `##Trigger`: ReloadF and AttackLoop); fires as the Assault
            Carbine fires, automatic, with the Service Rifle's 5.56mm rounds (`OVERRIDES`).
  type79    the Type 79 submachine gun: small, gas-worked, a straight 20-round magazine ahead of the guard, a wire stock
            folded along its left side. Rides on the 10mm Submachine Gun (held in one hand; magazine `##SMGClip`, trigger
            `##SMGTrigger`: ReloadG); fires the 9mm Submachine Gun's rounds.

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
    'qsz92': ('QSZ-92', 'WeapNV9mmPistol', 'WeapNV9mmPistol', 15, 1.8, 900, 2.0),
    'type81': ('Type 81', 'WeapNVAssaultCarbine', 'WeapNVAssaultCarbine', 30, 8.0, 3200, 6.0),
    'type79': ('Type 79', 'Weap10mmSubmachineGun', 'WeapNV9mmSubmachineGun', 20, 4.0, 1400, 3.0),
}
# where a gun takes something from neither: 'ammo' the rounds of that game gun, 'damage' its own
OVERRIDES = {
    'type81': {'ammo': 'WeapNVServiceRifle', 'damage': 17},
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
    'WeapNV9mmPistol': {
        '##nmBar': ((-2.88, 2.83, -0.94), (15.37, 6.6, 0.94)),
        '##nmHammer': ((-4.26, 2.93, -0.34), (-1.43, 5.95, 0.34)),
        '##nmTrigger': ((2.18, 0.14, -0.35), (4.76, 2.58, 0.35)),
        '##nmClip': ((-3.59, -6.07, -0.82), (2.29, 3.86, 0.82)),
        'ProjectileNode': (15.44, 5.16, 0.0),
        '##SightingNode': (-25.28, 6.56, 0.0),
    },
    'WeapNVAssaultCarbine': {
        '##Clip': ((5.83, -4.25, -0.5), (10.07, 3.28, 0.48)),
        '##ChargingHandle': ((5.67, 4.42, -1.15), (10.33, 5.85, 0.98)),
        '##Trigger': ((2.95, 0.82, -0.18), (4.06, 2.64, 0.18)),
        'ProjectileNode': (39.43, 4.99, 0.0),
        '##SightingNode': (-7.81, 9.56, 0.0),
    },
    'Weap10mmSubmachineGun': {
        '##SMGClip': ((6.49, -8.13, -0.75), (14.44, 2.42, 0.77)),
        '##SMGTrigger': ((2.95, 0.66, -0.15), (3.88, 2.72, 0.29)),
        'ProjectileNode': (22.05, 7.17, 0.02),
        '##SightingNode': (-14.37, 9.56, 0.02),
    },
}
# Nodes the ride-on gun stands off its origin or turned: {node: (place, turn)}. The animations' keys are the node's whole
# place (ReloadF's first key for ##Clip is x 10, as the model stands it), so ours stand exactly there and turn there.
_I = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
BASE_NODES = {
    'WeapNVLightMachineGun': {'##riotMechanism': ((0.0, 0.0, -0.5374), _I)},
    'WeapNV9mmPistol': {'##nmHammer': ((-2.1291, 3.5473, 0.0), _I)},
    'WeapNVAssaultCarbine': {'##Clip': ((10.0, 0.0, 0.0), _I), '##Trigger': ((3.255, 2.739, 0.0), _I)},
    'Weap10mmSubmachineGun': {'##SMGClip': ((10.4937, -2.3306, 0.0093), _I),
                              '##SMGTrigger': ((3.5169, 3.3638, -0.2796), ((0.9848, -0.1736, 0.0), (0.1736, 0.9848, 0.0), (0.0, 0.0, 1.0)))},
}
# where the cases fly from, as the ride-on gun has it
BASE_CASE = {
    'WeapNV9mmPistol': ((1.3801, 5.454, 0.3861), ((-0.1496, 0.9109, -0.3845), (-0.932, 0.0, 0.3625), (0.3302, 0.4126, 0.8489))),
    'WeapNVAssaultCarbine': ((7.7722, 5.1636, 0.6898), ((0.0, 0.9848, 0.1736), (-0.7996, -0.1043, 0.5915), (0.6006, -0.1388, 0.7874))),
    'Weap10mmSubmachineGun': ((1.4459, 7.5087, 1.5429), ((0.0, 1.0, 0.0), (-0.9962, 0.0, 0.0872), (0.0872, 0.0, 0.9962))),
}
# the stretch of the sight line between the rear sight and the front post, which nothing may cross
SIGHTS = {'qlz87': (-0.6, 42.7), 'qsz92': (-1.6, 13.9), 'type81': (12.5, 34.5), 'type79': (-4.0, 19.7)}


# ---------- textures ----------
# 512 a picture over `Mesh.per` (12 units): ~42 pixels a unit, as sharp as the game's own guns (the first pictures were 128,
# plain noise: "could use enhanced texturing", 21 Nov 2026). Every pattern repeats exactly across the picture's edges: a
# Noise is sampled at its own period, a line pattern at whole cycles.
SIZE = 512


def _lines(u, v, n, wob, k):
    """Fine lines along u (n of them across v), their phase wandering by the noise `wob` (sampled at its own period k)."""
    return math.sin((v * n + 0.8 * wob.at(u * k, v * k)) * math.pi * 2)


def steel(size=SIZE, seed=301, tint=(54, 57, 54), worn=(132, 134, 130)):
    """Machined steel, phosphated dark: tool marks along the part, a mottle in the finish, pits, fine scratches and the
    finish rubbed through to bright metal where hands and holsters wear it."""
    c = tp.Canvas(size, size)
    big, mid, fine, scr, wob, rub = (tp.Noise(seed, 8), tp.Noise(seed + 1, 32), tp.Noise(seed + 2, 128), tp.Noise(seed + 3, 64),
                                     tp.Noise(seed + 4, 16), tp.Noise(seed + 5, 4))

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        b, m, f = big.at(u * 8, v * 8), mid.at(u * 32, v * 32), fine.at(u * 128, v * 128)
        ln = _lines(u, v, 180, wob, 16)
        col = tp._shade(tint, 0.8 + 0.22 * b + 0.08 * m + 0.05 * f + 0.04 * ln)
        r = 0.6 * rub.at(u * 4, v * 4) + 0.4 * m                            # (ragged, not round)
        if r > 0.62:                                                        # worn through
            col = tp._mix(col, worn, min(1.0, (r - 0.62) * 5) * (0.35 + 0.2 * ln))
        s = scr.at(u * 64, v * 64)
        if 0.495 < s < 0.505 and b > 0.45:                                  # hair-fine scratches
            col = tp._mix(col, worn, 0.6)
        h = 0.5 + 0.015 * ln + 0.01 * f
        if f > 0.93:                                                        # pits
            col, h = tp._shade(col, 0.7), h - 0.05
        return col, h
    c.paint(fn)
    return c


def blued(size=SIZE, seed=322):
    """Blued steel: blue-black, a little sheen of colour, worn grey at the edges of use."""
    return steel(size, seed, tint=(40, 43, 50), worn=(118, 122, 128))


def olive(size=SIZE, seed=302):
    """Olive drab paint over steel: an orange-peel finish, chips to the dark metal with a paler rim, dust settled in."""
    c = tp.Canvas(size, size)
    big, fine, peel, chip, dust = tp.Noise(seed, 6), tp.Noise(seed + 1, 64), tp.Noise(seed + 3, 128), tp.Noise(seed + 2, 24), tp.Noise(seed + 4, 12)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        b, f, pl = big.at(u * 6, v * 6), fine.at(u * 64, v * 64), peel.at(u * 128, v * 128)
        k = chip.at(u * 24, v * 24)
        if k > 0.8:
            return tp._shade((60, 60, 56), 0.85 + 0.15 * f), 0.42
        col = tp._shade((86, 92, 60), 0.86 + 0.18 * b + 0.06 * f + 0.05 * pl)
        if k > 0.76:                                                        # the paint's lifted rim round a chip
            col = tp._mix(col, (118, 122, 92), (k - 0.76) * 20)
        col = tp._mix(col, (150, 136, 104), max(0.0, dust.at(u * 12, v * 12) - 0.66) * 1.2)
        return col, 0.5 + 0.02 * pl + 0.01 * f
    c.paint(fn)
    return c


def black(size=SIZE, seed=303):
    """Black polymer: a moulded stipple that catches the light, the high spots polished a little by hands."""
    c = tp.Canvas(size, size)
    dot, fine, big = tp.Noise(seed, 128), tp.Noise(seed + 2, 64), tp.Noise(seed + 1, 8)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        d, f, b = dot.at(u * 128, v * 128), fine.at(u * 64, v * 64), big.at(u * 8, v * 8)
        col = tp._shade((34, 34, 33), 0.8 + 0.3 * d + 0.08 * f + 0.1 * b)
        if d > 0.72:
            col = tp._mix(col, (70, 70, 68), (d - 0.72) * 1.5)
        return col, 0.42 + 0.16 * d
    c.paint(fn)
    return c


def wood(size=SIZE, seed=311):
    """Oiled reddish wood, the grain running along the picture's width with its pores, worn paler in places."""
    c = tp.Canvas(size, size)
    grain, wav, fine, pore = tp.Noise(seed, 4), tp.Noise(seed + 1, 8), tp.Noise(seed + 2, 64), tp.Noise(seed + 3, 128)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        w = wav.at(u * 8, v * 8)
        g = math.sin((v * 22 + 1.6 * grain.at(u * 4, v * 4) + 0.3 * w) * math.pi * 2)
        f = fine.at(u * 64, v * 64)
        col = tp._shade((112, 58, 30), 0.8 + 0.14 * g + 0.06 * f + 0.04 * _lines(u, v, 140, wav, 8))
        col = tp._mix(col, (150, 96, 58), max(0.0, w - 0.72) * 0.9)
        p = pore.at(u * 128, v * 128)
        h = 0.5 + 0.03 * g
        if p > 0.82 and g < 0.2:                                            # open pores in the darker grain
            col, h = tp._shade(col, 0.72), h - 0.04
        return col, h
    c.paint(fn)
    return c


TEXTURES = {'qlz_steel': steel, 'qlz_olive': olive, 'qlz_black': black,
            'cn_steel': lambda: steel(seed=321), 'cn_blued': blued, 'cn_black': lambda: black(seed=323),
            'cn_wood': wood}
GLOSS = {'qlz_steel': 40.0, 'qlz_olive': 18.0, 'qlz_black': 10.0, 'cn_steel': 40.0, 'cn_blued': 50.0, 'cn_black': 10.0, 'cn_wood': 22.0}
SHINE = {'qlz_steel': 60, 'qlz_olive': 25, 'qlz_black': 12, 'cn_steel': 60, 'cn_blued': 70, 'cn_black': 12, 'cn_wood': 30}
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


# ---------- the QSZ-92 ----------

def _pair(m, lo, hi, gap):
    """Two blades of a rear sight, either side of a notch `gap` wide each way of the middle: lo, hi for the right one."""
    box(m, lo, hi)
    box(m, (lo[0], lo[1], -hi[2]), (hi[0], hi[1], -lo[2]))


def qsz92():
    """(parts, marks) in the 9mm Pistol's frame. Slide, hammer, magazine and trigger lie where its parts lie; the slide's
    top stays under the sight line (6.56), only the sights reach it."""
    fr, dk = _m('cn_black'), _m('cn_steel')
    eye, bore = 6.5606, 5.1554
    # the frame: dust cover over the guard, a grip raked back, a beavertail under the hammer
    prism(fr, [(-3.9, 2.85), (13.0, 2.85), (13.0, 1.7), (6.6, 1.7), (6.2, 2.3), (1.9, 2.3), (1.5, 1.0), (-1.0, -5.4),
               (-4.0, -5.4), (-3.7, -2.0), (-3.3, 1.6), (-4.1, 2.3)], -0.85, 0.85)
    prism(fr, [(1.3, 1.6), (-0.9, -5.0), (-3.6, -5.0), (-3.2, 1.6)], -1.05, 1.05)        # grip panels
    box(fr, (1.0, -0.1, -0.45), (6.2, 0.5, 0.45))                                        # the guard: under the finger
    prism(fr, [(6.2, -0.1), (6.6, -0.1), (6.8, 0.3), (6.8, 0.5), (6.2, 0.5)], -0.45, 0.45)
    box(fr, (6.2, 0.5, -0.45), (6.8, 1.9, 0.45))                                         # and in front, square
    box(fr, (8.0, 1.2, -0.75), (12.8, 1.7, 0.75))                                        # the rail
    for x in (8.4, 9.8, 11.2):
        box(fr, (x, 1.05, -0.8), (x + 0.6, 1.2, 0.8))
    box(dk, (-0.5, 2.4, -0.97), (4.6, 2.85, -0.85))                                      # slide lock (left)
    box(dk, (-4.0, -5.3, -0.3), (-3.6, -4.9, 0.3))                                       # lanyard loop
    # the barrel, seen at the slide's mouth and when the slide is back
    turned(dk, 'x', (0, bore, 0), [(13.0, 0.62), (15.25, 0.62)], sides=16)
    turned(fr, 'x', (0, bore, 0), [(15.3, 0.45), (15.34, 0.45)], sides=12)               # the bore, dark
    body = [fr.shape(), dk.shape()]

    # the slide: square, a narrower top, serrations front and back, the port on the right, the sights
    sl, sd = _m('cn_blued'), _m('cn_black')
    box(sl, (-2.9, 2.85, -0.9), (15.3, 5.8, 0.9))
    box(sl, (-2.6, 5.8, -0.6), (15.0, 6.1, 0.6))
    for x0 in [-2.5 + 0.4 * k for k in range(6)] + [10.6 + 0.4 * k for k in range(5)]:
        for side in (-1.0, 1.0):
            box(sd, (x0, 3.4, side * 0.9 - 0.04), (x0 + 0.16, 5.6, side * 0.9 + 0.04))
    box(sd, (2.6, 4.5, 0.86), (6.2, 5.75, 0.94))                                         # ejection port
    box(sl, (-2.0, 4.6, -1.05), (-1.0, 5.1, 1.05))                                       # decocker
    box(sl, (13.95, 6.1, -0.15), (14.35, eye - 0.03, 0.15))                              # front post
    _pair(sl, (-2.4, 6.1, 0.33), (-1.7, eye + 0.3, 0.75), 0.33)                          # rear notch
    slide = [sl.shape(), sd.shape()]

    hm = _m('cn_steel')                                                                  # the hammer, a round spur
    prism(hm, [(-1.6, 3.0), (-1.5, 4.4), (-2.2, 5.6), (-3.4, 5.9), (-4.1, 5.5), (-3.3, 4.9), (-2.6, 4.0), (-2.4, 3.0)], -0.3, 0.3)
    mg, mb = _m('cn_steel'), _m('cn_black')                                              # the magazine, in the grip
    prism(mg, [(1.2, 2.5), (-1.25, -5.4), (-3.45, -5.4), (-1.0, 2.5)], -0.7, 0.7)
    box(mb, (-4.1, -6.0, -0.95), (-0.9, -5.4, 0.95))
    tr = _m('cn_steel')
    prism(tr, [(3.3, 2.3), (3.9, 2.3), (4.3, 1.4), (4.0, 0.7), (3.4, 0.6), (3.6, 1.2), (3.5, 1.9)], -0.25, 0.25)
    parts = [('##nmBar', slide), ('##nmHammer', [hm.shape()]), ('##nmClip', [mg.shape(), mb.shape()]),
             ('##nmTrigger', [tr.shape()]), (None, body)]
    t, R = BASE_CASE['WeapNV9mmPistol']
    marks = [('ProjectileNode', (15.4404, bore, 0.0), gunmake.FORWARD), ('ShellCasingNode', t, R),
             ('##SightingNode', (-25.2817, eye, 0.0), gunmake.FORWARD)]
    return parts, marks


# ---------- the Type 81 ----------

def type81():
    """(parts, marks) in the Assault Carbine's frame. Its sight line (9.56) is high, as the carbine's carrying handle has
    it: the rear sight stands on a block and the front post on a tall base, as a Kalashnikov's does."""
    st, wd, dk = _m('cn_steel'), _m('cn_wood'), _m('cn_black')
    eye, bore = 9.5598, 4.9928
    # the receiver, its cover, the magazine well
    prism(st, [(-4.2, 2.9), (14.6, 2.9), (14.6, 7.0), (13.8, 7.6), (-3.0, 7.6), (-4.2, 6.6)], -1.45, 1.45)
    box(st, (-3.4, 7.6, -1.2), (11.4, 8.0, 1.2))
    box(st, (6.0, 2.4, -1.2), (10.4, 2.9, 1.2))
    box(st, (1.0, 5.8, 1.45), (6.4, 6.3, 1.58))                                          # selector (right)
    box(dk, (6.6, 4.9, 1.45), (10.4, 5.9, 1.52))                                         # ejection port
    # grip, guard, stock and butt plate
    prism(wd, [(0.3, 2.9), (2.3, 2.9), (1.0, -1.0), (-0.3, -4.2), (-2.5, -4.0), (-1.9, -0.5), (-1.5, 2.0)], -0.95, 0.95)
    box(st, (1.6, 0.0, -0.4), (6.2, 0.45, 0.4))
    box(st, (5.8, 0.45, -0.4), (6.25, 2.9, 0.4))
    prism(wd, [(-4.2, 6.6), (-4.2, 3.2), (-7.0, 2.4), (-18.0, 0.0), (-18.0, 6.2), (-9.0, 6.6)], -1.1, 1.1)
    box(st, (-18.5, -0.2, -1.2), (-18.0, 6.4, 1.2))
    # handguards, gas tube and block, barrel, cleaning rod, front sight, muzzle
    prism(wd, [(14.6, 2.6), (25.0, 3.0), (25.0, 5.4), (14.6, 5.6)], -1.35, 1.35)
    turned(st, 'x', (0, 6.5, 0), [(14.0, 0.7), (27.5, 0.7)], sides=12)
    turned(wd, 'x', (0, 6.5, 0), [(14.6, 1.05), (23.0, 1.05)], sides=8, flat=True)
    box(st, (27.0, 4.0, -0.8), (28.6, 7.3, 0.8))
    turned(st, 'x', (0, bore, 0), [(14.6, 0.72), (37.6, 0.72)], sides=12)
    rod(st, (25.0, 3.7, 0.0), (33.6, 3.85, 0.0), 0.18, sides=6)
    prism(st, [(33.6, 3.4), (35.8, 3.4), (35.8, 5.8), (35.2, 8.6), (34.2, 8.6), (33.6, 5.8)], -0.7, 0.7)
    box(st, (34.55, 8.6, -0.14), (34.85, eye - 0.06, 0.14))
    _pair(st, (34.2, 8.6, 0.62), (35.2, 9.9, 0.9), 0.62)                                 # the post's ears
    turned(st, 'x', (0, bore, 0), [(37.4, 0.95), (39.38, 0.95)], sides=12)
    turned(dk, 'x', (0, bore, 0), [(39.38, 0.45), (39.42, 0.45)], sides=12)
    # the rear sight: a block on the receiver's front, a notch between two blades
    box(st, (11.4, 7.6, -0.9), (13.6, 8.6, 0.9))
    box(st, (11.6, 8.6, -0.9), (12.0, 8.9, 0.9))
    _pair(st, (12.0, 8.6, 0.33), (12.4, eye + 0.3, 0.8), 0.33)
    body = [st.shape(), wd.shape(), dk.shape()]

    mg, mr = _m('cn_steel'), _m('cn_black')                                              # the curved magazine
    prism(mg, [(6.3, 2.9), (9.9, 2.9), (10.3, 0.0), (11.1, -2.3), (12.0, -4.3), (8.5, -4.6), (7.3, -2.4), (6.5, 0.0)], -0.85, 0.85)
    for x, y in ((7.0, -1.2), (8.0, -3.4)):
        box(mr, (x, y, -0.9), (x + 2.8, y + 0.4, 0.9))
    ch = _m('cn_steel')                                                                  # bolt carrier and handle (right)
    box(ch, (6.6, 6.0, 1.45), (10.4, 6.8, 1.6))
    rod(ch, (10.0, 6.4, 1.6), (10.0, 6.4, 2.6), 0.32, sides=8)
    tr = _m('cn_steel')
    prism(tr, [(3.2, 2.9), (3.8, 2.9), (4.2, 2.0), (3.9, 1.0), (3.3, 0.9), (3.5, 1.6), (3.4, 2.4)], -0.18, 0.18)
    parts = [('##Clip', [mg.shape(), mr.shape()]), ('##ChargingHandle', [ch.shape()]), ('##Trigger', [tr.shape()]), (None, body)]
    t, R = BASE_CASE['WeapNVAssaultCarbine']
    marks = [('ProjectileNode', (39.433, bore, 0.0), gunmake.FORWARD), ('ShellCasingNode', t, R),
             ('##SightingNode', (-7.8104, eye, 0.0), gunmake.FORWARD)]
    return parts, marks


# ---------- the Type 79 ----------

def type79():
    """(parts, marks) in the 10mm Submachine Gun's frame (held in one hand). The real gun's stock folds over its top;
    here it lies along the left side, out of the sight line."""
    st, bk, dk = _m('cn_steel'), _m('cn_black'), _m('cn_blued')
    eye, bore = 9.5648, 7.1721
    prism(st, [(-6.4, 5.0), (14.4, 5.0), (14.4, 8.2), (13.8, 8.7), (-5.8, 8.7), (-6.4, 8.1)], -1.25, 1.25)
    box(st, (-3.4, 8.7, -0.9), (13.5, 8.95, 0.9))
    box(dk, (-1.0, 2.9, -1.0), (8.6, 5.0, 1.0))                                          # trigger housing
    box(dk, (8.6, 3.0, -1.0), (12.2, 5.0, 1.0))                                          # magazine well
    prism(bk, [(-0.4, 2.9), (1.8, 2.9), (0.8, -0.5), (-0.4, -4.6), (-2.6, -4.4), (-2.0, 0.0), (-1.7, 2.4)], -0.95, 0.95)
    box(st, (1.2, 0.0, -0.4), (6.2, 0.4, 0.4))
    box(st, (5.8, 0.4, -0.4), (6.2, 2.9, 0.4))
    box(bk, (0.8, 6.6, 1.25), (4.6, 8.0, 1.3))                                           # ejection port
    box(st, (0.5, 6.0, -1.32), (3.0, 6.5, -1.25))                                        # selector (left)
    rod(st, (11.0, 7.6, 1.25), (11.0, 7.6, 2.1), 0.28, sides=8)                          # cocking knob (right)
    # gas cylinder over the barrel, barrel, muzzle, front sight
    turned(st, 'x', (0, 8.3, 0), [(14.4, 0.55), (18.6, 0.55)], sides=10)
    turned(st, 'x', (0, bore, 0), [(14.4, 0.6), (21.2, 0.6)], sides=12)
    turned(st, 'x', (0, bore, 0), [(21.0, 0.75), (21.98, 0.75)], sides=12)
    turned(bk, 'x', (0, bore, 0), [(21.98, 0.35), (22.02, 0.35)], sides=10)
    prism(st, [(19.2, 6.6), (20.6, 6.6), (20.6, 8.4), (20.2, 8.8), (19.6, 8.8), (19.2, 8.4)], -0.6, 0.6)
    box(st, (19.75, 8.8, -0.13), (20.05, eye - 0.06, 0.13))
    _pair(st, (19.4, 8.4, 0.6), (20.4, 9.8, 0.85), 0.6)
    # the rear sight, a notch between blades on a little base
    box(st, (-4.8, 8.7, -0.7), (-3.6, 9.2, 0.7))
    _pair(st, (-4.6, 9.2, 0.33), (-4.1, eye + 0.4, 0.7), 0.33)
    # the wire stock, folded forward along the left side; its hinge at the back
    box(dk, (-6.9, 5.4, -1.3), (-6.4, 8.4, 1.3))
    for y in (6.0, 7.8):
        rod(st, (-6.2, y, -1.55), (9.5, y, -1.55), 0.22, sides=6)
    box(st, (9.4, 5.4, -1.95), (10.0, 8.4, -1.25))
    body = [st.shape(), bk.shape(), dk.shape()]

    mg, mb = _m('cn_steel'), _m('cn_blued')                                              # the 20-round magazine
    prism(mg, [(8.9, 5.0), (11.9, 5.0), (12.0, -1.0), (12.4, -7.4), (9.6, -7.6), (9.0, -1.0)], -0.7, 0.7)
    box(mb, (9.3, -8.1, -0.85), (12.7, -7.4, 0.85))
    tr = _m('cn_steel')
    prism(tr, [(3.0, 2.9), (3.6, 2.9), (3.9, 1.9), (3.6, 0.8), (3.0, 0.7), (3.2, 1.4), (3.1, 2.3)], -0.15, 0.15)
    parts = [('##SMGClip', [mg.shape(), mb.shape()]), ('##SMGTrigger', [tr.shape()]), (None, body)]
    t, R = BASE_CASE['Weap10mmSubmachineGun']
    marks = [('ProjectileNode', (22.0457, bore, 0.0249), gunmake.FORWARD), ('ShellCasingNode', t, R),
             ('##SightingNode', (-14.3737, eye, 0.0249), gunmake.FORWARD)]
    return parts, marks


SHAPES = {'qlz87': qlz87, 'qsz92': qsz92, 'type81': type81, 'type79': type79}


def build(name):
    shown, base, fires, clip, weight, value, mass = GUNS[name]
    parts, marks = SHAPES[name]()
    nif = gunmake.build_gun('FOLab%s' % name.upper(), parts, marks, mass=mass, frames=BASE_NODES.get(base))
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
# (MOD3 is the scope's overlay: with mods gone it can never be fitted, and a weapon that has one shows no gun when aimed in nv-rs)
DROP = ('MODT', 'MODS', 'MOD3', 'MO3T', 'MO3S', 'MOD4', 'MO4T', 'MO4S', 'MWD1', 'MWD2', 'MWD3', 'MWD4', 'MWD5', 'MWD6', 'MWD7', 'WNM1', 'WNM2', 'WNM3', 'WNM4',
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
            want = {'Value': value, 'Weight': weight, 'Clip size': clip,
                    'Damage': OVERRIDES.get(name, {}).get('damage', {f.get('name'): f.get('value') for f in theirs['DATA'][0]['fields']}['Damage'])}
            s['fields'] = [dict(f, value=want.get(f.get('name'), f.get('value'))) for f in s['fields']]
        elif t == 'DNAM':
            s['fields'] = [dict(f, value=NO_MODS[f['name']] if f.get('name') in NO_MODS else their_dnam[f['name']] if f.get('name') in DNAM_FROM_FIRES else f.get('value'))
                           for f in s['fields']]
        subs.append(s)
    # (what the fire gun has that the ride-on gun hasn't, put after the model: its own order isn't the game's concern)
    for t in FROM_FIRES:
        if t not in taken and t in theirs:
            subs += [dict(q) for q in theirs[t]]
    if OVERRIDES.get(name, {}).get('ammo'):
        ammo = rounds_of(gd, OVERRIDES[name]['ammo'])
        subs = [dict(s, value=ammo) if s['tag'] == 'NAM0' else s for s in subs]
    rec['subs'] = subs
    return rec


def rounds_of(gd, edid):
    """The ammunition (a key) a game gun fires."""
    import recordio
    return next(s['value'] for s in recordio.load(gd, _game(gd, edid, 'WEAP'))['subs'] if s['tag'] == 'NAM0')


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


# ---------- the Huang's (Waikiki) ----------

HUANG_GUNS = ('qsz92', 'type79', 'type81')
# the Huang's own stores (blades.py's containers, found by editor ID) that may hold one of their guns
HUANG_STORES = ('FOLabNVDuffleBagRandomLootHuang', 'FOLabFootlocker01HospitalHuang')
HUANG_NONE = 75                 # (chance in 100 a store holds no gun: they're rarer than the blades)
AMMO_NONE = 40
AMMO = {'qsz92': 12, 'type79': 20, 'type81': 15}       # (rounds found beside a gun's kind)


def _lvli(edid, none, entries):
    """A levelled item list of the mod's own: [(item key, count)], one picked (flag 1: from all levels, at or under)."""
    return {'type': 'LVLI', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': 0} for n in ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2')]},
        {'tag': 'LVLD', 'label': 'Chance none', 'kind': 'struct', 'fields': [{'name': 'Percent', 'code': 'B', 'value': none}]},
        {'tag': 'LVLF', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 1}]}]
        + [{'tag': 'LVLO', 'label': 'Entry', 'kind': 'struct', 'fields': [
            {'name': 'Level', 'code': 'h', 'value': 1}, {'pad': 'd703'}, {'name': 'Item', 'code': 'F', 'value': k},
            {'name': 'Count', 'code': 'h', 'value': n}, {'pad': 'd703'}]} for k, n in entries]}


def huang_ops(pr, gd, names=HUANG_GUNS):
    """Ops putting the guns in the mod and among the Huang's own stores, if they're the first ops applied: each gun's two
    records, a list of the guns (FOLabGunsHuang) and one of their rounds (FOLabGunsHuangAmmo), both added to each of
    `HUANG_STORES`. Returns (ops, {name: weapon key}, what build made {name: made}, report). The files are the caller's
    to write (made[name]['files'] among the mod's own)."""
    import copy
    have = {next((s.get('value') for s in r.get('subs', []) if s.get('tag') == 'EDID'), None) for r in pr.records.values() if isinstance(r, dict)}
    there = sorted(have & ({'FOLabWeap' + x.upper() for x in names} | {'FOLabGunsHuang', 'FOLabGunsHuangAmmo'}))
    if there:
        raise ValueError('in the mod already: ' + ', '.join(there))
    ops, keys, made = [], {}, {}
    n = pr.next_id
    for name in names:
        m = build(name)
        fp = '+%06X' % n
        ops += [{'op': 'record_new', 'record': first_person(name, m)},
                {'op': 'record_new', 'record': weapon(gd, name, m, fp), 'name': 'gun_' + name}]
        keys[name], made[name] = '+%06X' % (n + 1), m
        n += 2
    rounds = {}
    for name in names:
        r = rounds_of(gd, OVERRIDES.get(name, {}).get('ammo', GUNS[name][2]))
        rounds[r] = max(rounds.get(r, 0), AMMO[name])
    guns_list, ammo_list = '+%06X' % n, '+%06X' % (n + 1)
    ops += [{'op': 'record_new', 'record': _lvli('FOLabGunsHuang', HUANG_NONE, [(keys[x], 1) for x in names])},
            {'op': 'record_new', 'record': _lvli('FOLabGunsHuangAmmo', AMMO_NONE, sorted(rounds.items()))}]
    stores = []
    for key, rec in pr.records.items():
        if not isinstance(rec, dict) or rec.get('type') != 'CONT':
            continue
        e = next((s.get('value') for s in rec.get('subs', []) if s.get('tag') == 'EDID'), None)
        if e not in HUANG_STORES:
            continue
        rec = copy.deepcopy(rec)
        if any(f.get('value') == guns_list for s in rec['subs'] if s['tag'] == 'CNTO' for f in s['fields']):
            continue
        one = next(s for s in rec['subs'] if s['tag'] == 'CNTO')
        last = max(i for i, s in enumerate(rec['subs']) if s['tag'] == 'CNTO')
        add = [dict(one, fields=[dict(f, value=k if f.get('name') == 'Item' else 1 if f.get('name') == 'Count' else f.get('value'))
                                 for f in one['fields']]) for k in (guns_list, ammo_list)]
        rec['subs'][last + 1:last + 1] = add
        ops.append({'op': 'record', 'key': key, 'record': rec})
        stores.append(e)
    return ops, keys, made, {'guns': {GUNS[x][0]: keys[x] for x in names}, 'lists': [guns_list, ammo_list], 'stores': stores,
                             'rounds': rounds}


def gun_ops(pr, gd, name, made):
    """The ops making the gun's two records, if they're the first ops applied: (ops, the weapon's key to be)."""
    fp_key = '+%06X' % pr.next_id
    return ([{'op': 'record_new', 'record': first_person(name, made)},
             {'op': 'record_new', 'record': weapon(gd, name, made, fp_key), 'name': 'gun_' + name}], '+%06X' % (pr.next_id + 1))
