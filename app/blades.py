"""Chinese and Japanese blades for Waikiki: FOLab's own models on the game's own weapons' swings and numbers, as the clubs are
(clubs.py: the same frame, writer, records and lists; docs/waikiki-loot-plan.md, "Chinese and Japanese blades").

Chinese, Huang's people's (found in Huang land and carried by them; only their own weapons but in rare cases):
  dao        curved single-edged sabre, widening toward its tip, a ring at its pommel: swings as the machete
  jian       straight double-edged sword, a crossguard: as the Machete Gladius
Japanese, nobody's for now (loot):
  katana     long curved two-handed sword, wrapped grip, round guard: as the Blade of the East
  wakizashi  its short companion: as the machete
  naginata   a curved blade on a long lacquered pole: as the fire axe
  yari       a straight spear head on a long pole, held at the middle: as Dead Money's knife spear (the one long weapon
             of the game that stabs)

A blade is lofted from cross-sections along y (`loft`): single-edged ones a wedge, the edge along +x and the spine at -x, the
curve bending toward the spine; double-edged ones a flat diamond. Lengths are the game weapons' (measured): one-handers
-7..38, the katana -18..68, the naginata -16..58, the yari -48..66."""
import math

import clubs
import texpaint as tp
from clubs import Mesh, lathe, binding

BLADES = {
    'dao': ('Dao', 'WeapNVMachete', 10.0, 'huang'),
    'jian': ('Jian', 'WeapNVMacheteGladius', 10.0, 'huang'),
    'katana': ('Katana', 'WeapNVLegateSword', 12.0, 'loot'),
    'wakizashi': ('Wakizashi', 'WeapNVMachete', 8.0, 'loot'),
    'naginata': ('Naginata', 'WeapNVFireaxe', 15.0, 'loot'),
    'yari': ('Yari', 'NVDLC01WeapKnifeSpear', 12.0, 'loot'),
}


# ---------- textures ----------

def steel(size=128, seed=301):
    """Polished blade steel, a little worn: bright along the picture's top (the edge), a soft temper line, darker toward
    the spine, faint scratches along it."""
    c = tp.Canvas(size, size)
    fine, cloud = tp.Noise(seed, 64), tp.Noise(seed + 1, 8)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        line = 0.32 + 0.06 * cloud.at(u * 8, 0.5)
        base = 196 if v < line else 150
        g = fine.at(u * 64, v * 4)
        col = tp._shade((base, base + 2, base + 6), 0.88 + 0.18 * g + 0.06 * cloud.at(u * 8, v * 8))
        return col, 0.5 + 0.03 * g
    c.paint(fn)
    return c


def brass(size=64, seed=302):
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 32)
    c.paint(lambda x, y: (tp._shade((176, 140, 64), 0.8 + 0.35 * fine.at(x * 32.0 / size, y * 32.0 / size)), 0.5))
    return c


def wrap(size=128, seed=303):
    """A grip's binding: dark cord crossed in diamonds over pale skin."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 64)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        a, b = (u * 4 + v * 8) % 1.0, (u * 4 - v * 8) % 1.0
        cord = min(abs(a - 0.5), abs(b - 0.5)) > 0.18
        g = fine.at(u * 64, v * 64)
        if cord:
            return tp._shade((34, 30, 32), 0.85 + 0.3 * g), 0.7
        return tp._shade((214, 206, 188), 0.8 + 0.2 * g), 0.35
    c.paint(fn)
    return c


def lacquer(size=128, seed=304):
    """Black lacquer worn through to red here and there: a pole's, a scabbard's."""
    c = tp.Canvas(size, size)
    wear, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 64)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        w = wear.at(u * 8, v * 8)
        col = tp._mix((26, 22, 22), (128, 30, 26), max(0.0, w - 0.62) * 3.0)
        return tp._shade(col, 0.9 + 0.2 * fine.at(u * 64, v * 64)), 0.5
    c.paint(fn)
    return c


clubs.TEXTURES.update({'steel': steel, 'brass': brass, 'wrap': wrap, 'lacquer': lacquer})


# ---------- shapes ----------

def loft(m, sections, tip=None):
    """A solid lofted through cross-sections [(y, [(x, z), ...])] (each the same count of corners, round the section),
    closed at the first section by a flat cap and at the last by a point `tip` (x, y, z) or a cap. Flat faces, so edges
    stay sharp; each face turned away from its section's middle."""
    def put(pts, axis):
        e1 = [pts[1][k] - pts[0][k] for k in range(3)]
        e2 = [pts[2][k] - pts[0][k] for k in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        mid = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        out = [mid[0] - axis[0], 0.0, mid[2] - axis[2]] if axis else [0.0, 0.0, 0.0]
        if axis is None or abs(out[0]) + abs(out[2]) < 1e-6:
            return
        if sum(n[k] * out[k] for k in range(3)) < 0:
            n = tuple(-v for v in n)
        ids = [m.corner(p, n, (0.5 + p[0] * 0.08, p[1] * 0.03)) for p in pts]
        for k in range(1, len(ids) - 1):
            m.tri(ids[0], ids[k], ids[k + 1])
    rings = [[(x, y, z) for x, z in sec] for y, sec in sections]
    centres = [(sum(p[0] for p in r) / len(r), r[0][1], sum(p[2] for p in r) / len(r)) for r in rings]
    for a in range(len(rings) - 1):
        ra, rb = rings[a], rings[a + 1]
        ca, cb = centres[a], centres[a + 1]
        axis = ((ca[0] + cb[0]) / 2, 0, (ca[2] + cb[2]) / 2)
        for k in range(len(ra)):
            k2 = (k + 1) % len(ra)
            put([ra[k], ra[k2], rb[k2], rb[k]], axis)
    if tip:
        r, c = rings[-1], centres[-1]
        for k in range(len(r)):
            k2 = (k + 1) % len(r)
            put([r[k], r[k2], tip], (c[0], 0, c[2]))
    for r, sgn in ((rings[0], -1.0),) + (() if tip else ((rings[-1], 1.0),)):
        n = (0.0, sgn, 0.0)
        ids = [m.corner(p, n, (0.5 + p[0] * 0.08, 0.5 + p[2] * 0.08)) for p in r]
        for k in range(1, len(ids) - 1):
            m.tri(ids[0], ids[k], ids[k + 1])


def single_edged(y0, y1, spine, edge, t, curve=0.0, steps=10, tip_back=0.6):
    """Sections of a single-edged blade from y0 to y1: spine(f) and edge(f) the x of each at f 0..1 along it, t(f) its
    thickness at the spine; curve: how far the tip bends toward the spine (a sabre's, a katana's sori). Returns
    (sections, tip)."""
    out = []
    for k in range(steps + 1):
        f = k / float(steps)
        y = y0 + (y1 - y0) * f
        bend = -curve * f * f
        s, e, th = spine(f) + bend, edge(f) + bend, t(f)
        out.append((y, [(s, th), (e, 0.0), (s, -th), (s - th * 0.6, 0.0)]))
    tip = (spine(1.0) - curve - tip_back * 0.0 + (edge(1.0) - spine(1.0)) * 0.25, y1 + (edge(1.0) - spine(1.0)) * 1.4, 0.0)
    return out, tip


def double_edged(y0, y1, half, t, steps=6):
    out = []
    for k in range(steps + 1):
        f = k / float(steps)
        y = y0 + (y1 - y0) * f
        h, th = half(f), t(f)
        out.append((y, [(h, 0.0), (0.0, th), (-h, 0.0), (0.0, -th)]))
    return out


def guard_disc(m, y, r, thick, sides=16):
    lathe(m, [(y, 0.0, 0.0), (y + 0.01, r, r * 0.92), (y + thick, r, r * 0.92), (y + thick + 0.01, 0.0, 0.0)], sides=sides, v_per=0.3)


def box(m, x0, y0, z0, x1, y1, z1):
    """A block (a crossguard, a collar): its six faces."""
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    mid = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    for f in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)):
        pts = [c[i] for i in f]
        fm = [sum(p[k] for p in pts) / 4 for k in range(3)]
        n = tuple(fm[k] - mid[k] for k in range(3))
        ids = [m.corner(p, n, (0.5 + (p[0] + p[2]) * 0.1, p[1] * 0.1)) for p in pts]
        m.tri(ids[0], ids[1], ids[2])
        m.tri(ids[0], ids[2], ids[3])


def dao():
    blade, grip, metal = Mesh('steel'), Mesh('wrap'), Mesh('brass')
    secs, tip = single_edged(5.0, 35.0, lambda f: -1.0, lambda f: 2.4 + 1.4 * f * f, lambda f: 0.55 - 0.2 * f, curve=2.2)
    loft(blade, secs, tip)
    lathe(grip, [(-6.5, 1.0, 1.0), (-6.0, 1.25, 1.1), (3.6, 1.15, 1.0), (4.0, 1.2, 1.05)], v_per=0.12)
    guard_disc(metal, 4.0, 2.8, 0.8)
    lathe(metal, [(-7.8, 0.0, 0.0), (-7.6, 1.4, 1.3), (-7.0, 1.4, 1.3), (-6.5, 1.1, 1.0)], v_per=0.3)       # (the pommel cap)
    lathe(metal, [(-9.6, 1.4, 0.35), (-9.2, 1.5, 0.4), (-8.2, 1.5, 0.4), (-7.8, 1.0, 0.35)], sides=10, v_per=0.3)  # (its ring)
    return [blade.shape(), grip.shape(), metal.shape()]


def jian():
    blade, grip, metal = Mesh('steel'), Mesh('lacquer'), Mesh('brass')
    secs = double_edged(5.0, 34.0, lambda f: 1.7 - 0.5 * f, lambda f: 0.5 - 0.15 * f)
    loft(blade, secs, (0.0, 37.5, 0.0))
    lathe(grip, [(-6.0, 1.05, 0.95), (3.8, 1.0, 0.9), (4.2, 1.1, 1.0)], v_per=0.12)
    box(metal, -3.4, 4.0, -1.1, 3.4, 5.2, 1.1)                                       # (the crossguard)
    lathe(metal, [(-7.4, 0.0, 0.0), (-7.2, 1.3, 1.2), (-6.3, 1.4, 1.25), (-6.0, 1.1, 1.0)], v_per=0.3)
    return [blade.shape(), grip.shape(), metal.shape()]


def katana():
    blade, grip, metal = Mesh('steel'), Mesh('wrap'), Mesh('brass')
    secs, tip = single_edged(3.2, 64.0, lambda f: -1.0, lambda f: 1.3 - 0.2 * f, lambda f: 0.6 - 0.2 * f, curve=2.6, steps=14)
    loft(blade, secs, tip)
    lathe(grip, [(-18.0, 1.1, 1.0), (-17.4, 1.3, 1.15), (1.6, 1.25, 1.1), (2.0, 1.3, 1.15)], v_per=0.1)
    guard_disc(metal, 2.0, 3.4, 0.6)
    lathe(metal, [(2.6, 1.5, 0.9), (3.4, 1.4, 0.8)], v_per=0.3)                      # (the collar)
    lathe(metal, [(-18.8, 0.0, 0.0), (-18.6, 1.15, 1.05), (-18.0, 1.15, 1.05)], v_per=0.3)
    return [blade.shape(), grip.shape(), metal.shape()]


def wakizashi():
    blade, grip, metal = Mesh('steel'), Mesh('wrap'), Mesh('brass')
    secs, tip = single_edged(3.0, 35.0, lambda f: -0.9, lambda f: 1.2 - 0.15 * f, lambda f: 0.5 - 0.15 * f, curve=1.4, steps=10)
    loft(blade, secs, tip)
    lathe(grip, [(-7.0, 1.0, 0.9), (1.6, 1.15, 1.0), (2.0, 1.2, 1.05)], v_per=0.12)
    guard_disc(metal, 2.0, 2.7, 0.5)
    lathe(metal, [(-7.6, 0.0, 0.0), (-7.4, 1.05, 0.95), (-7.0, 1.05, 0.95)], v_per=0.3)
    return [blade.shape(), grip.shape(), metal.shape()]


def naginata():
    blade, pole, metal = Mesh('steel'), Mesh('lacquer'), Mesh('brass')
    lathe(pole, [(-16.0, 0.0, 0.0), (-15.8, 1.3, 1.3), (36.0, 1.25, 1.25), (37.0, 1.3, 1.3)], v_per=0.04)
    lathe(metal, [(-16.6, 0.0, 0.0), (-16.4, 1.45, 1.45), (-15.0, 1.45, 1.45)], v_per=0.3)     # (the butt cap)
    lathe(metal, [(35.0, 1.5, 1.5), (37.2, 1.5, 1.5)], v_per=0.3)                              # (the collar)
    guard_disc(metal, 37.2, 2.4, 0.5)
    secs, tip = single_edged(37.8, 55.5, lambda f: -1.0, lambda f: 1.6 + 1.6 * f, lambda f: 0.55 - 0.15 * f, curve=3.2, steps=10)
    loft(blade, secs, tip)
    return [blade.shape(), pole.shape(), metal.shape()]


def yari():
    blade, pole, metal, tie = Mesh('steel'), Mesh('lacquer'), Mesh('brass'), Mesh('cord')
    lathe(pole, [(-48.0, 0.0, 0.0), (-47.8, 1.2, 1.2), (50.0, 1.15, 1.15), (51.0, 1.2, 1.2)], v_per=0.03)
    lathe(metal, [(-48.6, 0.0, 0.0), (-48.4, 1.35, 1.35), (-47.0, 1.35, 1.35)], v_per=0.3)
    lathe(metal, [(49.0, 1.4, 1.4), (52.0, 1.3, 1.3)], v_per=0.3)
    binding(tie, -4.0, 4.0, 1.3)                                                               # (where it is held)
    secs = double_edged(52.0, 62.5, lambda f: 1.4 - 0.4 * f, lambda f: 0.7 - 0.2 * f, steps=5)
    loft(blade, secs, (0.0, 66.0, 0.0))
    return [blade.shape(), pole.shape(), metal.shape(), tie.shape()]


SHAPES = {'dao': dao, 'jian': jian, 'katana': katana, 'wakizashi': wakizashi, 'naginata': naginata, 'yari': yari}


def build(name):
    """As clubs.build: the model, its files, its bounds, the game weapon it swings as."""
    import nifmake
    shown, base, mass, _who = BLADES[name]
    shapes = SHAPES[name]()
    nif = nifmake.build_held('FOLab%s' % name.capitalize(), shapes, mass=mass, material='metal')
    mesh = 'meshes\\folab\\weapons\\%s.nif' % name
    files = {mesh: nif}
    for s in shapes:
        key = s['tex'].split('\\')[-1][:-4]
        files[clubs.TEX % key], files[clubs.NORMAL % key] = clubs.texture_files(key)
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for s in shapes for k in range(0, len(s['p']), 3)]
    box_ = [int(math.floor(min(q[k] for q in pts))) for k in range(3)] + [int(math.ceil(max(q[k] for q in pts))) for k in range(3)]
    return {'nif': nif, 'files': files, 'mesh': mesh, 'box': box_, 'base': base, 'shown': shown, 'shapes': shapes}


# ---------- into Huang land, and the loot ----------

LISTS = {'huang': [n for n, v in BLADES.items() if v[3] == 'huang'], 'japanese': [n for n, v in BLADES.items() if v[3] == 'loot']}
HUANG_ANCHORS = {'FOLabSettlerHall': 2, 'FOLabSettlerHallRed': 2, 'FOLabSettlerScreen': 1, 'FOLabSettlerGate1': 1, 'FOLabSettlerGate2': 2,
                 'FOLabSettlerGate3': 2, 'FOLabSettlerGate4': 1, 'FOLabSettlerGate5': 1, 'FOLabSettlerFreighter': 2}
HUANG_KINDS = ['food', 'bag', 'medicine', 'tools']
HUANG_SHARE = 0.4               # (of their finds, how many hold one of their blades)
JAPANESE_FINDS = 12             # (of the loot's hard-band finds, how many hold a Japanese blade)


def huang_finds(gd, pr, world, seed=37):
    """Finds against the settlers' own buildings (halls, screen walls, gates, the freighter's side): their stores, unlocked
    (their land, nobody's to own until their people are in). Returns (lootplace.Plan with the ops, counts)."""
    import collections
    import lootplace
    import settleup
    P = lootplace.Plan(gd, pr, world, seed)
    A = lootplace.Anchors(gd, pr, world)
    S = lootplace.Seat(gd, pr, world)
    S.feet = A.feet
    start = tuple((pr.newgame or {}).get('p', [0, 0])[:2])
    O = lootplace.Outside(P, A, S, start)
    O.ok_spot = lambda x, y: not A.near_door(x, y)          # (in their land: only doors to keep clear of)
    rep = collections.Counter()
    for c in gd.grid(world).values():
        ck = gd.key(c)
        for rk, r in sorted((pr.cells.get(ck) or {}).get('refs', {}).items()):
            b, p = r.get('base'), r.get('p')
            if not b or not p or r.get('removed'):
                continue
            e = settleup._edid(gd, pr, b)
            want = HUANG_ANCHORS.get(e)
            if not want:
                continue
            box = A.box(b)
            if not box:
                continue
            a = (p[0], p[1], p[2], p[5], float(r.get('s') or 1.0), box, e, ck, rk, 0.0)
            for k in range(want):
                if O.put_by(a, HUANG_KINDS[(rep['tried'] + k) % len(HUANG_KINDS)], 0, 'huang'):
                    rep[e] += 1
            rep['tried'] += want
    return P, dict(rep)
