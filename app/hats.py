"""Waikiki's straw hats: FOLab's own boater and lauhala sun hat, worn by the surfers in place of the game's Rattan Cowboy Hat
(the user, 20 Nov 2026: "more hawaiian shirts and sunglasses and boaters", then "do both then please").

  boater     a flat-topped straw boater: a short straight crown, a flat brim, a black grosgrain band
  lauhala    a sun hat plaited of pandanus leaf: a soft round crown, a wide brim drooping toward its edge, the edge a little
             rough where the plaits end, a band of darker plait

How the game's own hats are made (the Pre-War Hat, suithat.nif, and the cowboy hats; read 20 Nov 2026):
  - worn: the gambler fedora and tuxedo hat are one shape skinned wholly to 'Bip01 Head', in the body's space, the file
    holding its own Bip01 Head node; FOLab's are made so (nifmake.build_worn). The cowboy hats are rigid, but the exe hangs a
    rigid hat on Bip01 Head itself, whose own x is the body's up: FOLab's boater, rigid and z-up, lay on its side in game
    (21 Nov 2026, with Prn and without). One model for men and women: the ARMO has only MODL and MOD2.
  - the frame: offsets from the head bone along the world's own axes (z up, +y the way the face looks, x across), not the
    bone's turned axes. Measured so, the head's top is 15.1 over the bone, the forehead at z 9-10 reaches y 7.5 and the head
    there is 5.4 to each side; the Pre-War Hat's crown meets its brim at z ~9, the brim lower in front than behind (6 deg).
  - dropped: the _GO model is the same shape with collision (BSXFlags 66, one box, the clutter layer): `nifmake.build_dropped`.

A hat here is a lathe of a profile round the crown's axis (`Profile`): its outer skin walked from the top of the crown out
over the brim, round the edge, back under it and up inside the crown, so it can be seen from below as well as above. The
crown is an oval (the head is longer than it is wide); past the band the brim keeps an even width all round. Worn, it sits
with its band at `BAND` (`FIT`), tipped `TILT` forward; dropped, it rests on its brim's underside at the origin.

    build(name)   {'worn': bytes, 'go': bytes, 'files': {path: bytes}, 'worn_path', 'go_path', 'box': OBND (of the _GO)}
    HATS          {name: shown name}
    ops(gd, pr)   (ops, report): the two ARMO of the mod's own, and the surfers' head list holding them in place of the
                  Rattan Cowboy Hat. The pictures and meshes go among the mod's own files as the ops are planned."""
import math

import library
import nifmake
import recordio
import texpaint as tp

HATS = {'boater': 'Straw Boater', 'lauhala': 'Lauhala Sun Hat'}
GAME_HAT = 'CowboyHat04'                # the Rattan Cowboy Hat: what the surfers wore; each hat's record is a copy of it
MESH = 'meshes\\folab\\%s\\people\\%s.nif'
TEX = 'textures\\folab\\people\\%s.dds'
NORMAL = 'textures\\folab\\people\\%s_n.dds'
SIDES = 48

# worn: where the band's middle is (head bone offsets) and how far the hat tips forward
FIT = (0.0, 0.9, 9.0)
TILT = math.radians(6.0)
BAND_R, BAND_E = 6.8, 1.12              # the band: 6.8 to each side, 7.6 front and back (the head at z 9.8 reaches 5.3 across at y -2.7)


# ---------- textures ----------

STRAW, STRAW_DARK, STRAW_PALE = (214, 186, 124), (150, 118, 66), (236, 214, 160)


def straw(size=256, seed=301):
    """Sennit straw as a boater is sewn from: rows of braid running round the hat (along the picture's width), each row a
    herringbone of flat strands, the rows' edges a fine dark seam."""
    c = tp.Canvas(size, size)
    rows = 8
    tone, fine = tp.Noise(seed, 8), tp.Noise(seed + 1, 64)
    h = size / rows

    def fn(x, y):
        r = int(y // h)
        f = (y - r * h) / h                             # 0..1 across the row
        side = 1 if f < 0.5 else -1                     # the braid's two halves lean opposite ways
        k = 10.0                                        # strands across the picture's width, per row
        s = (x / size * k * rows / 2 + side * f * 2) % 1.0
        ridge = math.sin(math.pi * s)                   # a strand rounded across its width
        col = tp._mix(STRAW_DARK, STRAW_PALE, 0.35 + 0.55 * ridge)
        col = tp._shade(col, 0.92 + 0.12 * tone.at(x / size * 8, y / size * 8) + 0.05 * fine.at(x / size * 64, y / size * 64))
        seam = min(f, 1 - f)
        if seam < 0.05:                                 # where one row is sewn to the next
            col = tp._shade(col, 0.6 + 6 * seam)
        if abs(f - 0.5) < 0.02:
            col = tp._shade(col, 0.82)
        return col, 0.35 + 0.4 * ridge - (0.25 if seam < 0.05 else 0.0)
    c.paint(fn)
    return c


def ribbon(size=128, seed=302):
    """Black grosgrain: fine ribs across the ribbon (the picture's width runs round the hat, so ribs are upright lines)."""
    c = tp.Canvas(size, size)
    fine = tp.Noise(seed, 32)

    def fn(x, y):
        rib = 0.5 + 0.5 * math.cos(2 * math.pi * x * 32 / size)
        col = tp._shade((26, 26, 30), 0.85 + 0.3 * rib + 0.05 * fine.at(x / size * 32, y / size * 32))
        return col, 0.4 + 0.2 * rib
    c.paint(fn)
    return c


LAUHALA = [(196, 160, 104), (186, 148, 92), (204, 170, 114), (178, 140, 86), (192, 156, 100)]
LAUHALA_DARK = [(92, 62, 38), (74, 50, 30), (104, 72, 44)]


def plait(colours, size=256, strips=12, seed=303):
    """Pandanus plaited on the bias: strips at 45 degrees each way, over one and under one; each strip its own shade of the
    dried leaf, a fine grain along it, the one underneath in shadow at the crossings."""
    c = tp.Canvas(size, size)
    grain, tone = tp.Noise(seed, 64), tp.Noise(seed + 1, 8)
    w = size / float(strips)
    pick = lambda n: colours[(n * 7 + 3) % len(colours)]

    def fn(x, y):
        a, b = (x + y) / w, (x - y + size) / w
        ia, ib = int(math.floor(a)), int(math.floor(b))
        fa, fb = a - ia, b - ib
        top_a = (ia + ib) % 2 == 0                      # which strip lies on top in this square
        f, n = (fa, ia) if top_a else (fb, ib)
        other = fb if top_a else fa
        col = pick(n % strips + (0 if top_a else strips))
        along = (b if top_a else a) * w
        col = tp._shade(col, 0.9 + 0.12 * grain.at(along / size * 64, f * 4) + 0.06 * tone.at(x / size * 8, y / size * 8))
        edge = min(f, 1 - f)
        if edge < 0.08:                                 # the gap between two strips
            col = tp._shade(col, 0.55 + 5 * edge)
        dip = min(other, 1 - other)                     # where the strip goes under its neighbour
        if dip < 0.12:
            col = tp._shade(col, 0.86 + 1.15 * dip)
        return col, 0.3 + 0.45 * math.sin(math.pi * f) - (0.15 if dip < 0.12 else 0.0)
    c.paint(fn)
    return c


TEXTURES = {'straw': straw, 'ribbon': ribbon, 'lauhala': lambda: plait(LAUHALA), 'lauhala_band': lambda: plait(LAUHALA_DARK, size=128, strips=4, seed=304)}
_drawn = {}


def texture_files(name):
    if name not in _drawn:
        _drawn[name] = TEXTURES[name]().files(game=True)
    return _drawn[name]


# ---------- shapes ----------

class Profile:
    """A hat's skin, turned round its crown's axis. strips: [[(r, z), ...], ...], walked so that the outside of the skin
    is on the walker's left (from the crown's top outward: up and out); a strip's corners are shaded smoothly, a new strip
    starts a sharp turn. uv: 'wrap' (round the hat and along the walk) or 'plan' (seen from above)."""

    def __init__(self, tex, sides=SIDES, rough=None):
        self.tex = tex
        self.sides = sides
        self.rough = rough                  # rough(a, r, z) -> (r, z): the edge's own wobble
        self.p, self.n, self.uv, self.i = [], [], [], []

    def corner(self, p, n, uv):
        self.p.append(tuple(p))
        ln = math.sqrt(sum(v * v for v in n)) or 1.0
        self.n.append(tuple(v / ln for v in n))
        self.uv.append(tuple(uv))
        return len(self.p) - 1

    def tri(self, a, b, c):
        pa, pb, pc = self.p[a], self.p[b], self.p[c]
        e1 = [pb[k] - pa[k] for k in range(3)]
        e2 = [pc[k] - pa[k] for k in range(3)]
        fn = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        if sum(v * v for v in fn) < 1e-8:
            return
        avg = [self.n[a][k] + self.n[b][k] + self.n[c][k] for k in range(3)]
        if sum(fn[k] * avg[k] for k in range(3)) < 0:
            b, c = c, b
        self.i += [a, b, c]

    @staticmethod
    def place(a, r):
        """(x, y) of a point at turn a, distance r out: the crown an oval, the brim past the band an even width."""
        ry = r * BAND_E if r <= BAND_R else r + BAND_R * (BAND_E - 1)
        return r * math.cos(a), ry * math.sin(a)

    def strip(self, pts, uv='wrap', u_turns=6.0, v_per=0.16, v0=0.0):
        """One strip turned; returns the walked length (for the next strip's v)."""
        n = self.sides
        # smooth 2D normals at each profile point: the left of the walk, averaged over the two segments
        segs = [(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1)]
        left = [(-dz, dr) for dr, dz in segs]
        norms = []
        for k in range(len(pts)):
            a = left[max(0, k - 1)]
            b = left[min(len(left) - 1, k)]
            norms.append((a[0] + b[0], a[1] + b[1]))
        lengths = [0.0]
        for dr, dz in segs:
            lengths.append(lengths[-1] + math.hypot(dr, dz))
        grid = []
        for k, (r, z) in enumerate(pts):
            row = []
            for j in range(n + 1):
                a = 2 * math.pi * j / n
                rr, zz = (self.rough(a, r, z) if self.rough else (r, z))
                if rr < 1e-6:
                    if j == 0:
                        top = self.corner((0.0, 0.0, zz), (0.0, 0.0, 1.0 if norms[k][1] > 0 else -1.0), (0.5, 0.5) if uv == 'plan' else (0.0, v0 + lengths[k] * v_per))
                    row.append(top)
                    continue
                x, y = self.place(a, rr)
                nr, nz = norms[k]
                nx, ny = nr * math.cos(a), nr * math.sin(a) / (BAND_E if rr <= BAND_R else 1.0)
                if uv == 'plan':
                    t = (x / 14.0 + 0.5, y / 14.0 + 0.5)
                else:
                    t = (u_turns * j / n, v0 + lengths[k] * v_per)
                row.append(self.corner((x, y, zz), (nx, ny, nz), t))
            grid.append(row)
        for k in range(len(grid) - 1):
            for j in range(n):
                a, b, c, d = grid[k][j], grid[k][j + 1], grid[k + 1][j], grid[k + 1][j + 1]
                self.tri(a, c, b)
                self.tri(b, c, d)
        return lengths[-1]

    def shape(self):
        return {'p': [v for q in self.p for v in q], 'n': [v for q in self.n for v in q], 'uv': [v for q in self.uv for v in q],
                'i': list(self.i), 'tex': TEX % self.tex, 'normal': NORMAL % self.tex, 'gloss': 8.0}


BOATER = {'top': 7.2, 'side_top': 6.4, 'thick': 0.35, 'brim': 4.6}
LAUHALA_HAT = {'top': 7.6, 'thick': 0.4, 'brim': 7.0, 'droop': 2.4}


def _dome(h):
    """The lauhala's crown: its outer half width at height h over the band."""
    top = LAUHALA_HAT['top']
    return BAND_R * math.sqrt(max(0.0, 1 - ((h - 2.0) / (top - 2.0)) ** 2)) if h > 2.0 else BAND_R + 0.05 * (2.0 - h)


def inside(name, z):
    """How far out the crown's inside is at height z over the band (in the oval's measure: x, or y / BAND_E), or None
    above the inside's top: what a head must stay within."""
    if name == 'boater':
        b = BOATER
        z0, z1 = -b['thick'], b['top'] - b['thick'] - 0.3
        if z > b['top'] - b['thick']:
            return None
        if z >= z1:
            return b['side_top'] - b['thick'] - 0.3
        f = max(0.0, (z - z0) / (z1 - z0))
        return (BAND_R - b['thick']) + ((b['side_top'] - b['thick']) - (BAND_R - b['thick'])) * f
    b = LAUHALA_HAT
    if z > b['top'] - b['thick']:
        return None
    return _dome(z + b['thick']) - b['thick']


def boater():
    """A flat top 7.2 over the band, the crown nearly upright, a flat brim 4.6 wide, a ribbon 1.8 high round the crown."""
    s = Profile('straw')
    top, side_top, thick, brim = BOATER['top'], BOATER['side_top'], BOATER['thick'], BOATER['brim']
    edge = BAND_R + brim
    v = s.strip([(0, top), (2.5, top), (side_top - 0.25, top - 0.02)], u_turns=7.0)
    v += s.strip([(side_top - 0.25, top - 0.02), (side_top - 0.05, top - 0.12), (side_top, top - 0.35)], v0=v, u_turns=7.0)
    v += s.strip([(side_top, top - 0.35), (BAND_R - 0.1, 2.2), (BAND_R, 0.0)], v0=v, u_turns=7.0)
    s.strip([(BAND_R, 0.0), (BAND_R + 1.2, 0.0), (edge - 0.3, 0.0), (edge, -0.05)], u_turns=9.0)
    s.strip([(edge, -0.05), (edge + 0.1, -0.2), (edge, -thick)], u_turns=24.0, v_per=0.5)
    s.strip([(edge, -thick), (BAND_R + 0.6, -thick), (BAND_R - thick, -thick)], u_turns=9.0)
    v = s.strip([(BAND_R - thick, -thick), (BAND_R - thick - 0.1, 2.2), (side_top - thick, top - thick - 0.3)], u_turns=7.0)
    s.strip([(side_top - thick, top - thick - 0.3), (side_top - thick - 0.3, top - thick), (0, top - thick)], u_turns=7.0)
    band = Profile('ribbon')
    over = 0.12
    lean = (BAND_R - 0.1 - side_top) / (2.2 - (top - 0.35))     # (the crown's own slope, so the band lies on it)
    r_at = lambda z: BAND_R + over + (z * lean if z < 2.2 else 0)
    band.strip([(r_at(1.85) - over, 1.85), (r_at(1.85), 1.85)], uv='wrap', u_turns=10.0)
    band.strip([(r_at(1.85), 1.85), (r_at(0.05), 0.05)], uv='wrap', u_turns=10.0, v_per=0.5)
    return [s.shape(), band.shape()]


def lauhala():
    """A round crown 7.6 high, a brim 7.5 wide falling 2.4 toward its edge, the edge's wobble (`rough`), a band of dark plait."""
    import random
    rnd = random.Random(305)
    bumps = [(rnd.uniform(0, 2 * math.pi), rnd.choice((5, 7, 9, 11)), rnd.uniform(0.08, 0.2)) for _ in range(5)]
    teeth = [rnd.uniform(-0.12, 0.12) for _ in range(SIDES)]
    top, thick, brim, droop = LAUHALA_HAT['top'], LAUHALA_HAT['thick'], LAUHALA_HAT['brim'], LAUHALA_HAT['droop']
    edge = BAND_R + brim

    def rough(a, r, z):
        if r <= BAND_R + 0.5:
            return r, z
        far = (r - BAND_R) / brim                       # 0 at the band, 1 at the edge
        wave = sum(h * math.sin(k * a + p) for p, k, h in bumps)
        j = int(round(a / (2 * math.pi) * SIDES)) % SIDES
        nick = teeth[j] if r >= edge - 0.01 else 0.0    # where the plaits end
        return r + nick, z + wave * far * far

    crown = _dome
    fall = lambda f: -droop * f ** 1.6                  # the brim's fall, f 0..1 from the band out
    s = Profile('lauhala', rough=rough)
    dome = [(crown(h), h) for h in (top, top - 0.15, top - 0.6, top - 1.4, top - 2.4, top - 3.4, 2.8, 2.0, 1.0, 0.0)]
    dome[0] = (0.0, top)
    s.strip(dome[:3], uv='plan')
    s.strip(dome[2:], u_turns=5.0, v_per=0.12)
    out = [(BAND_R + brim * f, fall(f)) for f in (0.0, 0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0)]
    s.strip([(BAND_R + 0.05, 0.0)] + out[1:], uv='plan')
    s.strip([out[-1], (edge + 0.05, fall(1.0) - thick / 2), (edge, fall(1.0) - thick)], u_turns=40.0, v_per=0.5)
    under = [(r, z - thick) for r, z in reversed(out)]
    s.strip(under[:-1] + [(BAND_R - thick, -thick)], uv='plan')
    inner = [(max(0.0, crown(h) - thick), h - thick) for h in (0.0, 1.0, 2.0, 2.8, top - 3.4, top - 2.4, top - 1.4, top - 0.6, top - 0.15)]
    inner[0] = (BAND_R - thick, -thick)
    s.strip(inner[:8], u_turns=5.0, v_per=0.12)
    s.strip(inner[7:] + [(0.0, top - thick)], uv='plan')
    band = Profile('lauhala_band')
    band.strip([(crown(1.7) + 0.02, 1.7), (crown(1.7) + 0.15, 1.7)], u_turns=10.0)
    band.strip([(crown(1.7) + 0.15, 1.7), (BAND_R + 0.15, 0.05)], u_turns=10.0, v_per=0.4)
    return [s.shape(), band.shape()]


SHAPES = {'boater': boater, 'lauhala': lauhala}


def _moved(shapes, turn, shift):
    """The shapes turned about x by `turn` (front down for a positive turn) and moved by `shift`, normals with them."""
    c, s = math.cos(turn), math.sin(turn)
    out = []
    for sh in shapes:
        p, n = sh['p'], sh['n']
        P, N = [], []
        for k in range(0, len(p), 3):
            x, y, z = p[k:k + 3]
            P += [x + shift[0], y * c + z * s + shift[1], -y * s + z * c + shift[2]]
            x, y, z = n[k:k + 3]
            N += [x, y * c + z * s, -y * s + z * c]
        out.append(dict(sh, p=P, n=N))
    return out


def head_points(gd):
    """The game's head (meshes\\characters\\head\\headhuman.nif, the man's: the woman's is narrower) as offsets from the
    head bone (the skeleton's Bip01 Head) along the world's axes: the frame a hat is made in."""
    import nif
    sk = nif.Nif(gd.read_file('meshes\\characters\\_male\\skeleton.nif'))
    at = {}

    def visit(i, R, t):
        b = sk.block(i)
        if not isinstance(b, dict) or 'children' not in b:
            return
        lR, lt = b['R'], b['t']
        nR = tuple(tuple(sum(R[r][k] * lR[k][c] for k in range(3)) for c in range(3)) for r in range(3))
        nt = tuple(t[k] + sum(R[k][m] * lt[m] for m in range(3)) for k in range(3))
        at[b.get('name')] = nt
        for c in b['children']:
            if c >= 0:
                visit(c, nR, nt)
    visit(0, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.0, 0.0, 0.0))
    o = at['Bip01 Head']
    m = nif.mesh_from_nif(gd.read_file('meshes\\characters\\head\\headhuman.nif'))
    return [(q['p'][k] - o[0], q['p'][k + 1] - o[1], q['p'][k + 2] - o[2]) for q in m for k in range(0, len(q['p']), 3)]


def clearance(name, head):
    """The least room between the head and the crown's inside, the head taken into the hat's own frame (negative: the head
    comes through the hat)."""
    c, s = math.cos(TILT), math.sin(TILT)
    least = None
    for x, y, z in head:
        x, y, z = x - FIT[0], y - FIT[1], z - FIT[2]
        y, z = y * c - z * s, y * s + z * c                     # (undoing _moved's turn)
        if z < 0:
            continue
        r_in = inside(name, z)
        r = math.hypot(x, y / BAND_E)
        room = (r_in - r) if r_in is not None else -1.0
        least = room if least is None else min(least, room)
    return least


def build(name, mod='waikiki'):
    shapes = SHAPES[name]()
    worn = _moved(shapes, TILT, FIT)
    low = min(sh['p'][k] for sh in shapes for k in range(2, len(sh['p']), 3))
    go = _moved(shapes, 0.0, (0.0, 0.0, -low))
    worn_path, go_path = MESH % (mod, name), MESH % (mod, name + '_go')
    files = {worn_path: nifmake.build_worn('FOLab%s' % name.capitalize(), worn),
             go_path: nifmake.build_dropped('FOLab%sGO' % name.capitalize(), go, mass=0.5, material='cloth')}
    for sh in shapes:
        key = sh['tex'].split('\\')[-1][:-4]
        files[TEX % key], files[NORMAL % key] = texture_files(key)
    pts = [(sh['p'][k], sh['p'][k + 1], sh['p'][k + 2]) for sh in go for k in range(0, len(sh['p']), 3)]
    box = [int(math.floor(min(q[k] for q in pts))) for k in range(3)] + [int(math.ceil(max(q[k] for q in pts))) for k in range(3)]
    return {'worn': files[worn_path], 'go': files[go_path], 'files': files, 'worn_path': worn_path, 'go_path': go_path,
            'box': box, 'shapes': worn, 'go_shapes': go}


# ---------- records ----------

def _game(gd, edid, tag):
    return next(f for f, (_i, r) in gd.forms.items() if r.tag == tag and (gd.edid(f) or '').lower() == edid.lower())


def hat_record(gd, name, made):
    """An ARMO of the mod's own: a copy of the Rattan Cowboy Hat (worn where it is, its numbers), the models FOLab's."""
    fid = _game(gd, GAME_HAT, 'ARMO')
    rec = recordio.load(gd, fid)
    rec['src'] = ''
    rec['copied_from'] = gd.key(fid)
    for tag, path in (('MODL', made['worn_path']), ('MOD2', made['go_path'])):
        for s in rec['subs']:
            if s['tag'] == tag:
                s['value'] = path[7:]                    # (models are named from meshes\)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('MODT', 'MO2T', 'MO3T', 'MO4T', 'MODS', 'MO2S', 'MO3S', 'MO4S', 'MODD')]
    for s in rec['subs']:
        if s['tag'] == 'OBND':
            for f, v in zip(s['fields'], made['box']):
                f['value'] = v
    recordio.set_field(rec, 'EDID', 'FOLab%s' % name.capitalize())
    recordio.set_field(rec, 'FULL', HATS[name])
    return rec


def ops(gd, pr, list_edid='FOLabSurferHeadList'):
    """(ops, report): the two hats (their files among the mod's own), then the surfers' head list with the two hats in
    place of the Rattan Cowboy Hat, its chance of none kept. Refused if the mod has them already or has no such list."""
    import peopledress
    have = {(recordio.field(r, 'EDID') or '').lower(): k for k, r in pr.records.items()}
    if any(('folab%s' % n).lower() in have for n in HATS):
        raise ValueError('The mod already has FOLab\'s hats (Undo them first to make them again).')
    lk = have.get(list_edid.lower())
    if not lk:
        raise ValueError('The mod has no %s: dress the surfers first (peopledress).' % list_edid)
    root = library.assets_dir(pr)
    slug = library.slug(pr.name)
    keys = peopledress._Keys(pr)
    rep = {'hats': {}, 'list': lk}
    hat_keys = []
    for name in HATS:
        made = build(name, slug)
        for path, data in made['files'].items():
            library._put(root, path, data)
        k = keys.add(hat_record(gd, name, made))
        hat_keys.append(k)
        rep['hats'][name] = {'key': k, 'mesh': made['worn_path'], 'box': made['box']}
    import json
    lst = json.loads(json.dumps(pr.records[lk]))
    game_hat = gd.key(_game(gd, GAME_HAT, 'ARMO'))
    entries = [s for s in lst['subs'] if s['tag'] == 'LVLO']
    olds = [s for s in entries if any(f.get('code') == 'F' and f.get('value') == game_hat for f in s['fields'])]
    if not olds:
        raise ValueError('%s has no Rattan Cowboy Hat to take the place of' % list_edid)
    at = lst['subs'].index(olds[0])
    lst['subs'] = [s for s in lst['subs'] if s not in olds]
    for n, hk in enumerate(hat_keys):
        s = json.loads(json.dumps(olds[0]))
        for f in s['fields']:
            if f.get('code') == 'F':
                f['value'] = hk
        lst['subs'].insert(at + n, s)
    rep['replaced'] = len(olds)
    return keys.ops + [{'op': 'record', 'key': lk, 'record': lst}], rep


def apply(server):
    """ops as one Undo; checks the hats got the keys they were planned with."""
    pr = server.PR
    first = pr.next_id
    o, rep = ops(server.GD, pr)
    out = server.edit('Straw hats for Waikiki\'s surfers', o)
    made = list(out.get('made') or []) if isinstance(out, dict) else []
    want = ['+%06X' % (first + n) for n in range(len(HATS))]
    if made[:len(want)] != want:
        raise RuntimeError('the hats got other keys than planned (%s vs %s): undo this step' % (made[:2], want))
    return rep
