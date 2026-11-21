"""Waikiki's Hawaiian clubs: FOLab's own models of five melee weapons, Hawaiian in flavour (not museum pieces), each on one of
the game's own weapons for its swings and numbers (docs/waikiki-loot-plan.md, "Who carries what"):

  leiomano    a paddle-shaped club edged with teeth (saw-blade teeth, as the wasteland would have it): cuts as the machete
  newa        a short, thick hardwood club: hits as the lead pipe
  laau        lā'au pālau, the long two-handed war club, its head flaring to an edge: swings as the baseball bat
  hoe         a koa canoe paddle, its blade weighted and sharpened: swings as the sledgehammer
  maul        pōhaku: a lava-rock head lashed to a koa haft: hits as the super sledge

A model's frame is the game's for a held weapon (measured from the machete, lead pipe, baton, bat and sledgehammers): the
grip at the origin, the business end along +y, the striking side along x; one-handers reach ~7 below the grip and 23-37
above, two-handers ~20 below and 50-60 above. Shapes are turned profiles (`lathe`), flattened profiles (blades), teeth,
cord bindings and a lumpy rock; textures are FOLab's own (koa grain, lava stone, rusted saw steel, cord).

    build(name)          {'nif': bytes, 'files': {path: bytes}, 'mesh': path, 'box': OBND, 'base': game weapon's editor ID}
    CLUBS                {name: (shown name, game weapon it is built on, mass)}

Who carries them is the user's: the court the leiomano and the maul, the valley and ridge people the newa and the hoe paddle,
pirates now and then as spoils (finds meanwhile)."""
import math
import random

import nifmake
import texpaint as tp

CLUBS = {
    'leiomano': ('Leiomano', 'WeapNVMachete', 10.0),
    'newa': ('Newa', 'WeapLeadPipe', 10.0),
    'laau': ("La'au Palau", 'WeapBaseballBat', 10.0),
    'hoe': ('Hoe War Paddle', 'WeapSledgehammer', 20.0),
    'maul': ('Pohaku Maul', 'WeapSuperSledge', 20.0),
}
TEX = 'textures\\folab\\weapons\\%s.dds'
NORMAL = 'textures\\folab\\weapons\\%s_n.dds'
SIDES = 12                      # (corners round a turned part)
KOA, KOA_DARK = (128, 70, 40), (78, 40, 22)


# ---------- textures ----------

def koa(size=256, seed=201):
    """Oiled koa along the picture's height: fine dark streaks, a few curls of figure, a soft sheen."""
    c = tp.Canvas(size // 2, size)
    streak, curl, fine = tp.Noise(seed, 16), tp.Noise(seed + 1, 4), tp.Noise(seed + 2, 64)
    w = c.w

    def fn(x, y):
        u, v = x / float(w), y / float(size)
        bend = 0.08 * curl.at(u * 4, v * 4)
        g = streak.at((u + bend) * 16, v * 2)
        f = fine.at(u * 64, v * 64)
        col = tp._mix(KOA, KOA_DARK, max(0.0, g - 0.45) * 1.6)
        col = tp._shade(col, 0.9 + 0.15 * f)
        return col, 0.5 + 0.06 * g + 0.02 * f
    c.paint(fn)
    return c


def lava(size=256, seed=202):
    """A lump of dark vesicular lava: no mortar, pitted, a little rust-red in the hollows."""
    c = tp.Canvas(size, size)
    big, pits, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 32), tp.Noise(seed + 2, 64)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        b = big.at(u * 8, v * 8)
        p = pits.at(u * 32, v * 32)
        f = fine.at(u * 64, v * 64)
        hollow = max(0.0, 0.42 - p) * 3.0
        col = tp._shade((62, 58, 56), 0.75 + 0.45 * b + 0.15 * f)
        col = tp._mix(col, (96, 52, 40), min(1.0, hollow) * 0.5)
        return tp._shade(col, 1.0 - 0.5 * min(1.0, hollow)), 0.6 + 0.2 * b - 0.3 * min(1.0, hollow) + 0.05 * f
    c.paint(fn)
    return c


def saw(size=128, seed=203):
    """Steel cut from a saw blade, rusted, bright where it was ground to an edge (the picture's top)."""
    c = tp.Canvas(size, size)
    rust, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 64)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        r = rust.at(u * 8, v * 8)
        f = fine.at(u * 64, v * 64)
        col = tp._mix((150, 150, 146), (122, 62, 34), max(0.0, r - 0.35) * 1.8)
        if v < 0.18:
            col = tp._mix(col, (205, 205, 198), 0.7)
        return tp._shade(col, 0.85 + 0.25 * f), 0.5 + 0.1 * r
    c.paint(fn)
    return c


def cord(size=128, seed=204):
    """Coconut-fibre cord wound round: diagonal turns, each turn rounded, hairy."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 64)

    def fn(x, y):
        u, v = x / float(size), y / float(size)
        t = (v * 8 + u * 1.0) % 1.0                 # (eight turns down the picture, each a little aslant)
        z = math.sin(t * math.pi)
        f = fine.at(u * 64, v * 64)
        col = tp._shade((150, 118, 76), 0.55 + 0.5 * z + 0.15 * f)
        return col, 0.3 + 0.5 * z
    c.paint(fn)
    return c


TEXTURES = {'koa': koa, 'lava': lava, 'saw': saw, 'cord': cord}
_drawn = {}


def texture_files(name):
    if name not in _drawn:
        _drawn[name] = TEXTURES[name]().files(game=True)
    return _drawn[name]


# ---------- shapes ----------

class Mesh:
    """One shape being built: corners with normals and texture places, triangles turned to face out."""

    def __init__(self, tex):
        self.tex = tex
        self.p, self.n, self.uv, self.i = [], [], [], []

    def corner(self, p, n, uv):
        self.p.append(tuple(p))
        ln = math.sqrt(sum(v * v for v in n)) or 1.0
        self.n.append(tuple(v / ln for v in n))
        self.uv.append(tuple(uv))
        return len(self.p) - 1

    def tri(self, a, b, c):
        """A triangle, its corners put anticlockwise as seen from the side its corners' normals face."""
        pa, pb, pc = self.p[a], self.p[b], self.p[c]
        e1 = [pb[k] - pa[k] for k in range(3)]
        e2 = [pc[k] - pa[k] for k in range(3)]
        fn = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        avg = [self.n[a][k] + self.n[b][k] + self.n[c][k] for k in range(3)]
        if sum(fn[k] * avg[k] for k in range(3)) < 0:
            b, c = c, b
        self.i += [a, b, c]

    def shape(self):
        return {'p': [v for q in self.p for v in q], 'n': [v for q in self.n for v in q], 'uv': [v for q in self.uv for v in q],
                'i': list(self.i), 'tex': TEX % self.tex, 'normal': NORMAL % self.tex, 'gloss': 18.0}


def lathe(m, rings, sides=SIDES, v_per=0.04, u_turns=1.0):
    """A turned part round the y axis: rings [(y, half width along x, half depth along z)], capped where a ring has no
    width. Normals from the profile's slope, so a swelling reads round."""
    grid = []
    for k, (y, rx, rz) in enumerate(rings):
        # (the profile's slope here: how the radius changes along y, for the normal's lean)
        y0, rx0, _rz0 = rings[max(0, k - 1)]
        y1, rx1, _rz1 = rings[min(len(rings) - 1, k + 1)]
        slope = -(rx1 - rx0) / (y1 - y0) if y1 != y0 else 0.0
        row = []
        for j in range(sides + 1):
            a = 2 * math.pi * j / sides
            ca, sa = math.cos(a), math.sin(a)
            p = (rx * ca, y, rz * sa)
            n = (ca / max(rx, 0.01), slope, sa / max(rz, 0.01)) if rx > 0.01 else (0.0, -1.0 if k == 0 else 1.0, 0.0)
            row.append(m.corner(p, n, (u_turns * j / sides, y * v_per)))
        grid.append(row)
    for k in range(len(grid) - 1):
        for j in range(sides):
            a, b, c, d = grid[k][j], grid[k][j + 1], grid[k + 1][j], grid[k + 1][j + 1]
            m.tri(a, c, b)
            m.tri(b, c, d)
    for k, sgn in ((0, -1.0), (len(rings) - 1, 1.0)):
        y, rx, rz = rings[k]
        if rx > 0.01:                               # (an open end: a flat cap)
            mid = m.corner((0, y, 0), (0, sgn, 0), (0.5, y * v_per))
            ring = [m.corner(m.p[grid[k][j]], (0, sgn, 0), (0.5 + 0.5 * math.cos(2 * math.pi * j / sides), 0.5 + 0.5 * math.sin(2 * math.pi * j / sides)))
                    for j in range(sides + 1)]
            for j in range(sides):
                m.tri(mid, ring[j], ring[j + 1])


def teeth(m, edge, count, size, side):
    """Saw teeth along an edge: edge(t) -> (x, y) at t 0..1 on the blade's rim, side +1 / -1 (which x side); each tooth a
    small flat wedge as thick as a saw blade, leaning toward the tip."""
    th = 0.35
    for k in range(count):
        t0, t1 = (k + 0.1) / count, (k + 0.9) / count
        (xa, ya), (xb, yb) = edge(t0), edge(t1)
        tip = (xb + side * size, yb + size * 0.4)
        for z in (th, -th):
            n = (0, 0, 1 if z > 0 else -1)
            a = m.corner((xa, ya, z), n, (0.1, 0.9))
            b = m.corner((xb, yb, z), n, (0.9, 0.9))
            c = m.corner((tip[0], tip[1], z * 0.3), n, (0.5, 0.05))
            m.tri(a, b, c)
        # (the ground edges: the two sloping faces)
        for (p, q) in (((xa, ya), tip), (tip, (xb, yb))):
            nx, ny = (q[1] - p[1]), -(q[0] - p[0])
            if nx * side < 0:
                nx, ny = -nx, -ny
            n = (nx, ny, 0.0)
            a = m.corner((p[0], p[1], th), n, (0.0, 0.5))
            b = m.corner((p[0], p[1], -th), n, (0.0, 0.6))
            c = m.corner((q[0], q[1], th * 0.3), n, (1.0, 0.0))
            d = m.corner((q[0], q[1], -th * 0.3), n, (1.0, 0.1))
            m.tri(a, b, c)
            m.tri(c, b, d)


def binding(m, y0, y1, r, sides=SIDES):
    """Cord wound round a part between y0 and y1, standing a little proud of it (r)."""
    lathe(m, [(y0, r * 0.92, r * 0.92), (y0 + 0.4, r, r), (y1 - 0.4, r, r), (y1, r * 0.92, r * 0.92)], sides, v_per=0.25)


def rock(m, middle, size, seed, detail=2):
    """A lump of rock: a sphere of triangles pushed in and out (each corner by noise), squashed to size (half sizes)."""
    rnd = random.Random(seed)
    t = (1 + math.sqrt(5)) / 2
    vs = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    fs = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
          (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    vs = [tuple(c / math.sqrt(sum(x * x for x in v)) for c in v) for v in vs]
    for _ in range(detail):
        cache, nf = {}, []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                p = [(vs[a][k] + vs[b][k]) / 2 for k in range(3)]
                ln = math.sqrt(sum(x * x for x in p))
                vs.append(tuple(x / ln for x in p))
                cache[key] = len(vs) - 1
            return cache[key]
        for a, b, c in fs:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        fs = nf
    bump = [1.0 + rnd.uniform(-0.18, 0.18) for _ in vs]
    pts = [tuple(middle[k] + v[k] * size[k] * bump[i] for k in range(3)) for i, v in enumerate(vs)]
    # (flat faces: rock breaks in facets)
    for a, b, c in fs:
        pa, pb, pc = pts[a], pts[b], pts[c]
        e1 = [pb[k] - pa[k] for k in range(3)]
        e2 = [pc[k] - pa[k] for k in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        out = [(pa[k] + pb[k] + pc[k]) / 3 - middle[k] for k in range(3)]
        if sum(n[k] * out[k] for k in range(3)) < 0:
            n = tuple(-v for v in n)
        uv = lambda q: ((q[0] - middle[0]) / (2 * size[0]) + 0.5 + (q[2] - middle[2]) * 0.01, (q[1] - middle[1]) / (2 * size[1]) + 0.5)
        m.tri(m.corner(pa, n, uv(pa)), m.corner(pb, n, uv(pb)), m.corner(pc, n, uv(pc)))


def blade(m, rings):
    """A flat blade (a paddle's, a club's flared head): a lathe with few sides flattened to an edge (rz much less than rx)."""
    lathe(m, rings, sides=16, v_per=0.03)


# ---------- the five ----------

def leiomano():
    wood, steel, tie = Mesh('koa'), Mesh('saw'), Mesh('cord')
    lathe(wood, [(-7.5, 0.0, 0.0), (-7.4, 1.2, 1.2), (-6.0, 1.5, 1.5), (8.0, 1.3, 1.3), (10.0, 1.6, 1.2)])
    # (the paddle: wide and flat, a rounded leaf, its edges where the teeth sit)
    prof = [(10.0, 1.6, 1.2), (13.0, 3.6, 1.1), (18.0, 4.6, 1.0), (26.0, 4.8, 0.9), (32.0, 4.0, 0.8), (35.5, 2.4, 0.6), (37.0, 0.0, 0.0)]
    blade(wood, prof)
    binding(tie, 8.0, 10.6, 1.7)
    binding(tie, -6.2, -4.0, 1.65)

    def edge(t, side):
        # (along the profile's rim from y 13 to 34.5)
        y = 13.0 + t * 21.5
        for (ya, ra, _a), (yb, rb, _b) in zip(prof, prof[1:]):
            if ya <= y <= yb:
                return (side * (ra + (rb - ra) * (y - ya) / (yb - ya)) * 0.97, y)
        return (0.0, y)
    for side in (1, -1):
        teeth(steel, lambda t, s=side: edge(t, s), 9, 1.4, side)
    return [wood.shape(), steel.shape(), tie.shape()]


def newa():
    wood, tie = Mesh('koa'), Mesh('cord')
    lathe(wood, [(-4.5, 0.0, 0.0), (-4.4, 1.5, 1.5), (-3.0, 1.8, 1.8), (5.0, 1.6, 1.6), (9.0, 1.9, 1.9), (14.0, 2.7, 2.7),
                 (18.5, 3.2, 3.2), (21.0, 2.8, 2.8), (22.6, 1.5, 1.5), (23.2, 0.0, 0.0)])
    binding(tie, 4.0, 6.2, 1.85)
    return [wood.shape(), tie.shape()]


def laau():
    wood, tie = Mesh('koa'), Mesh('cord')
    lathe(wood, [(-20.0, 0.0, 0.0), (-19.8, 1.7, 1.7), (-18.0, 2.0, 2.0), (30.0, 1.7, 1.7), (40.0, 1.9, 1.9)])
    # (the head flares flat to an edge, wider across x, a ridge down its middle)
    blade(wood, [(40.0, 1.9, 1.9), (46.0, 3.0, 1.9), (52.0, 4.4, 1.8), (57.0, 4.8, 1.6), (59.5, 3.2, 1.1), (60.4, 0.0, 0.0)])
    binding(tie, -18.2, -14.0, 2.15)
    binding(tie, 38.0, 40.6, 2.05)
    return [wood.shape(), tie.shape()]


def hoe():
    wood, tie, steel = Mesh('koa'), Mesh('cord'), Mesh('saw')
    lathe(wood, [(-22.0, 0.0, 0.0), (-21.8, 2.2, 1.6), (-20.0, 2.4, 1.8), (-17.0, 1.6, 1.6), (26.0, 1.6, 1.6), (29.0, 2.2, 1.6)])
    # (the paddle's blade: a long leaf, thick down its middle, thin at its sharpened rim)
    prof = [(29.0, 2.2, 1.6), (34.0, 4.8, 1.4), (42.0, 6.4, 1.2), (50.0, 6.2, 1.0), (55.0, 4.6, 0.8), (58.0, 1.6, 0.4), (58.6, 0.0, 0.0)]
    blade(wood, prof)
    binding(tie, 26.0, 29.4, 1.8)
    # (the weight: a band of steel riveted across the blade near its tip, its edge ground bright)
    lathe(steel, [(49.0, 6.35, 1.1), (49.2, 6.45, 1.2), (52.0, 5.9, 1.1), (52.2, 5.8, 1.0)], sides=16, v_per=0.2)
    return [wood.shape(), tie.shape(), steel.shape()]


def maul():
    wood, tie, stone = Mesh('koa'), Mesh('cord'), Mesh('lava')
    lathe(wood, [(-18.0, 0.0, 0.0), (-17.8, 2.0, 2.0), (-16.0, 2.3, 2.3), (40.0, 2.0, 2.0), (52.0, 2.0, 2.0), (54.0, 1.2, 1.2), (54.4, 0.0, 0.0)])
    rock(stone, (0.0, 46.0, 0.0), (10.5, 6.0, 6.5), seed=5)
    binding(tie, 38.0, 41.0, 2.35)
    binding(tie, 51.0, 53.0, 2.3)
    binding(tie, -16.2, -12.0, 2.45)
    return [wood.shape(), tie.shape(), stone.shape()]


SHAPES = {'leiomano': leiomano, 'newa': newa, 'laau': laau, 'hoe': hoe, 'maul': maul}
MATERIAL = {'leiomano': 'wood', 'newa': 'wood', 'laau': 'wood', 'hoe': 'wood', 'maul': 'stone'}


def build(name):
    shown, base, mass = CLUBS[name]
    shapes = SHAPES[name]()
    nif = nifmake.build_held('FOLab%s' % name.capitalize(), shapes, mass=mass, material=MATERIAL[name])
    mesh = 'meshes\\folab\\weapons\\%s.nif' % name
    files = {mesh: nif}
    for s in shapes:
        key = s['tex'].split('\\')[-1][:-4]
        files[TEX % key], files[NORMAL % key] = texture_files(key)
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for s in shapes for k in range(0, len(s['p']), 3)]
    box = [int(math.floor(min(q[k] for q in pts))) for k in range(3)] + [int(math.ceil(max(q[k] for q in pts))) for k in range(3)]
    return {'nif': nif, 'files': files, 'mesh': mesh, 'box': box, 'base': base, 'shown': shown, 'shapes': shapes}


# ---------- records, and into finds ----------

# who has which, as the user settled it (20 Nov 2026): the court the leiomano and the maul (and the long war club, the
# lā'au pālau, which the split left unsaid: the court's guards'); the valley and ridge people the newa and the hoe paddle;
# pirates now and then any of them, as spoils
LISTS = {'court': (['leiomano', 'laau', 'maul'], 0), 'valley': (['newa', 'hoe'], 0), 'spoils': (list(CLUBS), 50)}
# where a find of the loot gets a club list, by map marker: (list, reach, share of the finds there)
WHERE = [('The Royal Hawaiian', 'court', 2600.0, 1.0), ('Kahala Reef', 'spoils', 2800.0, 0.5), ('Koko Marina', 'spoils', 2800.0, 0.35),
         ('The Tanks', 'valley', 1800.0, 1.0), ('The Holdouts', 'valley', 1800.0, 1.0), ('The Heights', 'valley', 1800.0, 1.0),
         ("Watcher's Hut", 'valley', 1400.0, 1.0), ('Loa Gate', 'spoils', 1800.0, 0.5)]
# and the valleys' own camps and refuges ('Squatters' Camp', 'Refugee Camp' markers): a share of their finds by band
VALLEY_SHARE = (0.25, 0.4, 0.55)


def _game(gd, edid, tag):
    got = [f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid]
    return min(got, key=lambda f: f >> 24)                  # (the base game's, else the DLC's that adds it: the yari's spear)


def first_person(name, made):
    """The first-person model's record: a static naming the same model, as the game's 1stPerson statics do."""
    return {'type': 'STAT', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FOLab1stPerson%s' % name.capitalize()},
        {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': 0} for n in ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2')]},
        {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': made['mesh'][7:]}]}


def weapon(gd, name, made, fp_key):
    """The weapon: the game's own it is built on (its swings, damage, sounds, repair list), with this model, name and
    first-person model. Its picture in the Pip-Boy stays the game weapon's for now."""
    import recordio
    rec = recordio.load(gd, _game(gd, made['base'], 'WEAP'))
    rec['src'] = ''
    subs = []
    for s in rec['subs']:
        if s['tag'] in ('MODT', 'MODS'):                    # (the model's hashes and alternate textures: the game model's)
            continue
        s = dict(s)
        if s['tag'] == 'EDID':
            s['value'] = 'FOLabWeap%s' % name.capitalize()
        elif s['tag'] == 'FULL':
            s['value'] = made['shown']
        elif s['tag'] == 'MODL':
            s['value'] = made['mesh'][7:]
        elif s['tag'] == 'WNAM':
            s['value'] = fp_key
        elif s['tag'] == 'OBND':
            s['fields'] = [dict(f, value=v) for f, v in zip(s['fields'], made['box'])]
        subs.append(s)
    rec['subs'] = subs
    return rec


def club_list(gd, edid, weapons, none):
    """A levelled list of the clubs (every level, one of them; `none` in 100 nothing), laid out as the game's."""
    import recordio
    rec = recordio.load(gd, _game(gd, 'LL2Tier1MeleePowderGangerSimple75', 'LVLI'))
    rec['src'] = ''
    one = next(s for s in rec['subs'] if s['tag'] == 'LVLO')
    subs = []
    for s in rec['subs']:
        if s['tag'] == 'LVLO':
            continue
        s = dict(s)
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'LVLD':
            s['fields'] = [dict(s['fields'][0], value=none)]
        subs.append(s)
    for w in weapons:
        subs.append(dict(one, fields=[dict(f, value=(1 if f.get('name') == 'Level' else w if f.get('name') == 'Item' else 1 if f.get('name') == 'Count' else f.get('value')))
                                      if 'name' in f else dict(f) for f in one['fields']]))
    rec['subs'] = subs
    return rec


def holding(gd, base_key, edid, list_key):
    """A container of the mod's own: the game's one at base_key (same model, same contents) with a club list added."""
    import recordio
    rec = recordio.load(gd, gd.from_key(base_key))
    rec['src'] = ''
    subs, put = [], False
    for s in rec['subs']:
        if s['tag'] == 'MODT':
            continue
        s = dict(s)
        if s['tag'] == 'EDID':
            s['value'] = edid
        if s['tag'] == 'DATA' and not put:                   # (after the game's own contents)
            one = next((q for q in rec['subs'] if q['tag'] == 'CNTO'), None) or next(
                q for q in recordio.load(gd, _game(gd, 'Footlocker01HouseholdNV', 'CONT'))['subs'] if q['tag'] == 'CNTO')
            subs.append(dict(one, fields=[dict(f, value=list_key if f.get('name') == 'Item' else 1 if f.get('name') == 'Count' else f.get('value')) for f in one['fields']]))
            put = True
        subs.append(s)
    rec['subs'] = subs
    return rec
