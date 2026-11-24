"""The Vespids' hives (the user, 23 Nov 2026; docs/waikiki-pacing-plan.md section 6): FOLab's own model of a big mutant wasp
nest, grown over a ruin on a hillside: a layered shell of chewed paper (each layer's lip lapping over the one below, as a
real yellowjacket's envelope is built), green light in its seams, vent holes, and at its foot a dark tunnel mouth where a
salvaged metal door stands (a door of the game's, placed: `MOUTH` is where).

The shell is one closed surface of revolution (`shell`): a profile walked from the top down, out to each layer's lip and
back in under it, lumped and leaned by `seed`, pushed in where the mouth and the vents are. Its picture (`paper`) is one
layer from top to lip: wavy stripes of grey and tan paper, darker and charred at the lip, where its glow picture (`veins`)
lights the seam and thin veins climb from it. The mouth and vents wear `dark` (the inside: old comb, faint glow). The
ruin's concrete is modelmake boxes. Collision: `RINGS` stacked frusta under the shell (convex, as Havok wants), the ruin's
boxes. A far model (`far_desc`): the shell at a twelfth of the corners, no lips, the same picture.

Sizes are game units (70 to the metre); front is -y; the model stands on z 0 with `SINK` of it under the ground.

    build(kind)            {'nif', 'far', 'files', 'box', 'triangles', 'mouth', ...}
    KINDS                  'ruin' (grown over a building), 'hill' (a mountain top), 'cliff' (set into a steep hillside),
                           'great' (the big dungeon's)
"""
import functools
import math
import random

TEX = 'textures\\folab\\hive\\%s.dds'
MESH = 'meshes\\folab\\hive\\%s.nif'
SINK = 90.0
SIDES = 72                      # corners round
FAR_SIDES = 18

# kind: (editor ID, file, widest radius, height, layers, seed, has a ruin, mouth (half-angle, height, depth))
KINDS = {
    'ruin': ('FOLabVespidHive', 'vespid_hive', 520.0, 1080.0, 15, 31, True, (0.30, 230.0, 60.0)),
    'hill': ('FOLabVespidHiveHill', 'vespid_hive_hill', 440.0, 1000.0, 15, 33, False, (0.30, 230.0, 130.0)),
    'cliff': ('FOLabVespidHiveCliff', 'vespid_hive_cliff', 420.0, 940.0, 15, 35, False, (0.30, 230.0, 130.0)),   # (set into a steep slope: vespidhives seats it so the hill takes its back)
    'great': ('FOLabVespidHiveGreat', 'vespid_hive_great', 700.0, 1500.0, 19, 37, True, (0.26, 300.0, 70.0)),
}
# the building a hive grew over (kinds with a ruin): half its width (x), half its depth (y), its walls' height. The paper
# hugs its walls (`HUG` out from them) and lets its corners and broken parapets through (`CORNER_OUT`); above its walls
# the nest closes in a dome. Its doorway (front, -y) is the hive's mouth.
BUILDINGS = {'ruin': (380.0, 320.0, 600.0), 'great': (520.0, 450.0, 800.0)}
HUG = 26.0
CORNER_OUT = 34.0
VENTS = 3
TEARS = {'ruin': 1, 'hill': 2, 'great': 2}   # (places the paper has broken open on the glowing comb inside)
# (the paper as real yellowjackets' is: fine wavy stripes, greys and buffs, now and then a tan or rust one)
PAPER = [(150, 146, 138), (176, 170, 160), (128, 122, 114), (166, 150, 128), (196, 190, 180), (140, 132, 120), (158, 138, 112)]
CHAR = (46, 40, 34)
GLOW = (120, 255, 90)
CRACK_GLOW = 1.6                # (how bright the light under the flaps is: the one number to turn once it's seen at night)
FLAP = 0.07                     # (how far a flap's edge stands off the one under it, a part of the radius)
GROUND_AT = 0.12                # (where on the egg the ground cuts it: the foot is that much narrower than the middle)
EGG_MID = 0.42


# ---------- the shell ----------

def egg(t):
    """The outline: radius (a part of the widest) at t, 0 at the ground to 1 at the top: an egg, a little pointed above."""
    u = GROUND_AT + (1 - GROUND_AT) * t
    if u <= EGG_MID:
        q = (EGG_MID - u) / EGG_MID
        return math.sqrt(max(0.0, 1 - q * q))
    q = (u - EGG_MID) / (1 - EGG_MID)
    return max(0.0, 1 - q ** 2.2) ** 0.62


class Lumps:
    """Low, smooth bumps over the shell by angle and height (tiling round)."""

    def __init__(self, rnd, n=7):
        self.w = [(rnd.randint(1, 4), rnd.uniform(0.001, 0.005), rnd.uniform(0, math.tau), rnd.uniform(0, math.tau), rnd.uniform(0.03, 0.08))
                  for _ in range(n)]

    def at(self, a, z):
        return sum(amp * math.sin(k * a + p) * math.cos(fz * z + q) for k, fz, p, q, amp in self.w)


def _dent(a, z, centre, half, low, high, depth, r=1.0):
    """(how far in a point at angle a, height z is pushed, whether it's inside the hole) for a round funnel of a mouth
    round angle centre: half its width `half` radians across, `high` tall from `low`; deepest in its middle."""
    da = math.atan2(math.sin(a - centre), math.cos(a - centre))
    rx, rz = half * r, high / 2.0
    q = math.hypot(da * r / rx, (z - low - rz) / rz)
    if q >= 1.5:
        return 0.0, (False, 9.0, 0.0)
    # (a funnel: the lip curls in, then down to the hole)
    k = max(0.0, 1 - q / 1.5) ** 1.4
    return depth * k, (q < 0.8, q / 0.8, math.atan2(z - low - rz, da * r))


def shell(kind, sides=SIDES, lips=True, openings=True):
    """{'rings': [[(x, y, z)]], 'uv': [[(u, v)]], 'part': [row kind], 'dark': [[bool]], 'mouth'}: the shell's corners ring
    by ring from the top down (each ring sides + 1 corners, the last one the first again for the picture's seam).

    The egg is covered in layers of paper, each band's lower edge a wavy line; along it the paper lifts off the band
    under it in flaps (patches, by angle), and under a flap's edge a narrow crack runs up and in to the next band: rows
    'face' (paper), 'under' and 'tuck' (the crack, where the inside's light shows). Where no flap lifts the crack has no
    width. lips=False: the plain egg (collision, the far model)."""
    edid, _f, r0, height, layers, seed, _ruin, (m_half, m_high, m_depth) = KINDS[kind]
    rnd = random.Random(seed)
    lumps = Lumps(rnd)
    cap = height * 0.97
    bounds = [cap * (1 - (k / layers) ** 0.92) for k in range(layers + 1)]
    bounds[-1] = -SINK
    band_h = cap / layers
    waves = [(rnd.randint(2, 5), rnd.uniform(0, math.tau), rnd.uniform(0.18, 0.38) * band_h,
              rnd.randint(1, 3), rnd.uniform(0, math.tau)) for _ in range(layers)]
    flaps = [(rnd.randint(2, 5), rnd.uniform(0, math.tau), rnd.randint(3, 7), rnd.uniform(0, math.tau)) for _ in range(layers)]
    lean = (rnd.uniform(-0.05, 0.05), rnd.uniform(0.02, 0.06))
    squash = rnd.uniform(0.86, 0.94)
    front = -math.pi / 2
    vents = [(front + rnd.uniform(1.0, math.tau - 1.0), height * rnd.uniform(0.4, 0.75), rnd.uniform(24, 36)) for _ in range(VENTS)]
    vents += [(front + rnd.uniform(0.6, math.tau - 0.6), height * rnd.uniform(0.25, 0.8), rnd.uniform(28, 45) * r0 / 470.0)
              for _ in range(TEARS.get(kind, 4))]

    bld = BUILDINGS.get(kind)
    if bld:
        squash = 1.0
        lean = (0.0, 0.0)

    def base_r(z, a=None):
        if not bld or a is None:
            return r0 * egg(min(1.0, max(0.0, z) / height))
        bx, by, bh = bld
        ca, sa = abs(math.cos(a)), abs(math.sin(a))
        face = min(bx / ca if ca > 1e-6 else 1e9, by / sa if sa > 1e-6 else 1e9)
        hug = min(face + HUG, math.hypot(bx, by) - CORNER_OUT)
        if z <= bh:
            return hug
        q = (z - bh) / (height - bh)
        return hug * max(0.0, 1 - q ** 1.7) ** 0.55

    def wave(k, a):
        if not lips or k >= layers - 1:
            return 0.0
        n, ph, amp, n2, ph2 = waves[k]
        return amp * (0.7 * math.sin(n * a + ph) + 0.3 * math.sin(n2 * a + ph2))

    def flap(k, a):
        if not lips or k >= layers - 1:
            return 0.0
        n, ph, n2, ph2 = flaps[k]
        f = max(0.0, math.sin(n * a + ph)) ** 1.5 + 0.6 * max(0.0, math.sin(n2 * a + ph2)) ** 2
        return FLAP * r0 * min(1.0, f) * (0.4 + 0.6 * (base_r(max(0.0, bounds[k + 1]), a) / r0))

    # each row: (part, band, f) and per angle (z, r)
    rows = []
    rows.append(('pole', 0, 0.0, lambda a: (height, 0.0)))
    rows.append(('face', 0, 0.0, lambda a: (cap, base_r(cap, a))))
    face_rows = 3
    for k in range(layers):
        def top_z(a, k=k):
            return cap if k == 0 else bounds[k] + wave(k - 1, a) + 3.0 + 1.1 * flap(k - 1, a)
        for j in range(1, face_rows + 1):
            f = j / face_rows
            def row(a, k=k, f=f, top_z=top_z):
                zt, zl = top_z(a), bounds[k + 1] + wave(k, a)
                z = zt + (zl - zt) * f
                return z, base_r(z, a) + flap(k, a) * f ** 1.3
            rows.append(('face', k, f, row))
        if k < layers - 1:
            def under(a, k=k):
                zl = bounds[k + 1] + wave(k, a)
                fl = flap(k, a)
                return zl + 0.35 * (3.0 + 1.1 * fl), base_r(zl, a) + 0.4 * fl
            def tuck(a, k=k):
                zl = bounds[k + 1] + wave(k, a)
                z = zl + 3.0 + 1.1 * flap(k, a)
                return z, base_r(z, a) - 0.004 * r0
            rows.append(('under', k, 1.0, under))
            rows.append(('tuck', k + 1, 0.0, tuck))
    rows.append(('close', layers - 1, 1.0, lambda a: (-SINK, base_r(0.0, a) * 0.6)))
    rows.append(('close', layers - 1, 1.0, lambda a: (-SINK, 0.0)))
    rings, uvs, darks, parts, holes = [], [], [], [], []
    around = 12 if kind == 'great' else 8                              # (the paper's picture repeats round)
    for part, k, f, fn in rows:
        ring, uv, dark = [], [], []
        hole = []
        for j in range(sides + 1):
            a = math.tau * j / sides
            zz, r = fn(a)
            rr = r * (1 + (0.25 if bld else 1.0) * lumps.at(a, zz)) if r > 0 else 0.0
            d, got = _dent(a, zz, front, m_half, 0.0, m_high, m_depth, max(r, 1.0)) if openings else (0.0, (False, 9.0, 0.0))
            inside, hq, ha = got
            for va, vz, vr in (vents if openings else ()):
                dd = math.hypot((math.atan2(math.sin(a - va), math.cos(a - va))) * max(r, 1.0), zz - vz)
                if dd < vr * 1.6 and r > 0:
                    d = max(d, 45.0 * max(0.0, 1 - (dd / (vr * 1.6)) ** 2))
                    if dd < vr * (0.85 + 0.3 * math.sin(7 * a + zz * 0.05)):     # (a torn, ragged edge)
                        inside = True
                        hq, ha = dd / vr, math.atan2(zz - vz, (math.atan2(math.sin(a - va), math.cos(a - va))) * max(r, 1.0))
            rr = max(0.0, rr - d)
            x = rr * math.cos(a) + lean[0] * max(0.0, zz)
            y = rr * math.sin(a) * squash + lean[1] * max(0.0, zz)
            ring.append((x, y, zz))
            v = {'under': 0.5, 'tuck': 1.0}.get(part, f)
            uv.append((around * j / sides, min(0.995, max(0.005, v))))
            dark.append(inside)
            hole.append((min(1.0, hq), ha))
        rings.append(ring)
        uvs.append(uv)
        darks.append(dark)
        holes.append(hole)
        parts.append(part)
    mouth_y = -base_r(m_high / 2, front) * squash + m_depth * 0.9
    return {'rings': rings, 'uv': uvs, 'dark': darks, 'part': parts, 'hole': holes,
            'mouth': (0.0, round(mouth_y, 1), 0.0, round(2 * m_half * r0, 1), m_high)}


def _normals(rings):
    """A normal at each corner, from its neighbours round and along (outwards)."""
    n, m = len(rings), len(rings[0])
    out = []
    for i in range(n):
        row = []
        for j in range(m):
            a, b = rings[max(0, i - 1)][j], rings[min(n - 1, i + 1)][j]
            c, d = rings[i][(j - 1) % (m - 1)], rings[i][(j + 1) % (m - 1)]
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            w = (d[0] - c[0], d[1] - c[1], d[2] - c[2])
            nx, ny, nz = u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            if ln < 1e-9:
                nx, ny, nz, ln = 0.0, 0.0, (1.0 if rings[i][j][2] > 0 else -1.0), 1.0
            # (outwards: away from the axis, or up at the top)
            p = rings[i][j]
            if nx * p[0] + ny * p[1] + nz * (p[2] - 400) < 0:
                nx, ny, nz = -nx, -ny, -nz
            row.append((nx / ln, ny / ln, nz / ln))
        out.append(row)
    return out


PART_MOST = 6000                # (triangles a shape: the strip builder's one strip holds so many)


def shell_shapes(kind, sides=SIDES, lips=True):
    """Shapes over the shell's corners: the paper (in bands of rows, each under PART_MOST triangles, lit only by the day),
    the cracks under the flaps (the inside's light: `crack`) and the dark (mouth and vents). Corners shared within a
    shape; faces wind anticlockwise from outside."""
    sh = shell(kind, sides, lips)
    rings, uvs, darks, parts, holes = sh['rings'], sh['uv'], sh['dark'], sh['part'], sh['hole']
    N = _normals(rings)
    rows_a_part = max(1, PART_MOST // (2 * sides))

    def new(name, gloss, glow):
        return {'p': [], 'n': [], 'uv': [], 'i': [], 'tex': TEX % name, 'normal': TEX % (name + '_n'), 'gloss': gloss,
                'alpha': False, 'glow': TEX % (name + '_g') if glow else '', 'glow_mult': 1.0, '_at': {}}
    papers = {}
    dark = new('dark', 20.0, True)
    crack = new('crack', 20.0, True)
    crack['glow_mult'] = CRACK_GLOW

    def corner(s, i, j):
        got = s['_at'].get((i, j))
        if got is not None:
            return got
        s['p'] += list(rings[i][j])
        s['n'] += list(N[i][j])
        if s is dark:
            q, ha = holes[i][j]                          # (a funnel: rings round the hole's middle)
            s['uv'] += [0.5 + 0.5 * q * math.cos(ha), 0.5 - 0.5 * q * math.sin(ha)]
        elif s is crack:
            s['uv'] += [uvs[i][j][0] * 2.0, {'face': 0.02, 'under': 0.5, 'tuck': 0.98}.get(parts[i], 0.5)]
        else:
            s['uv'] += list(uvs[i][j])
        s['_at'][(i, j)] = len(s['p']) // 3 - 1
        return s['_at'][(i, j)]
    for i in range(len(rings) - 1):
        in_crack = parts[i + 1] in ('under', 'tuck')
        paper = papers.setdefault(i // rows_a_part, new('paper', 8.0, False))
        for j in range(len(rings[0]) - 1):
            q = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            s = dark if sum(darks[a][b] for a, b in q) >= 3 else crack if in_crack else paper
            # (from the top down, angle growing anticlockwise seen from above: i, j -> i, j+1 -> i+1, j+1 is clockwise
            # from outside, so the triangles go the other way)
            for t in ((q[0], q[2], q[1]), (q[0], q[3], q[2])):
                a, b, c = (rings[x][y] for x, y in t)
                e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
                cr = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                if cr[0] ** 2 + cr[1] ** 2 + cr[2] ** 2 < 1e-6:
                    continue                                # (no area: at a pole, or a crack with no flap over it)
                s['i'] += [corner(s, x, y) for x, y in t]
    out = [papers[k] for k in sorted(papers)] + [crack, dark]
    for x in out:
        x.pop('_at')
        if not x['glow']:
            x.pop('glow')
            x.pop('glow_mult')
    return [x for x in out if x['i']], sh


CHORD = 0.8                     # (the collision's front, by the mouth: a straight edge between these angles either side)


def _hull2(pts):
    """The convex hull of 2D points, anticlockwise."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) <= 0:
                out.pop()
            out.append(p)
        return out
    lo, hi = half(pts), half(pts[::-1])
    return lo[:-1] + hi[:-1]


def _ray(poly, c, a):
    """Where a ray from c at angle a leaves a convex polygon."""
    dx, dy = math.cos(a), math.sin(a)
    best = None
    for p, q in zip(poly, poly[1:] + poly[:1]):
        ex, ey = q[0] - p[0], q[1] - p[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((p[0] - c[0]) * ey - (p[1] - c[1]) * ex) / den
        u = ((p[0] - c[0]) * dy - (p[1] - c[1]) * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return (c[0] + dx * (best or 0.0), c[1] + dy * (best or 0.0))


def solids(kind):
    """Convex frusta under the shell, one a stretch of height. Each is the shell's ring at its foot (lips and openings left
    out), made convex and drawn in a little, sampled at 12 angles, and that ring again, smaller, at its top: two rings of
    one shape make a truly convex solid (an uneven pair didn't: Havok's planes disagreed). Those as low as the mouth have a
    straight front edge (`CHORD`), where its door stands."""
    sh = shell(kind, 48, lips=False, openings=False)
    rings = sh['rings'][2:-2]                    # (not the top's pole and cap, nor the closing rings under the ground)
    edid, _f, r0, height, layers, seed, _ruin, (m_half, m_high, m_depth) = KINDS[kind]
    cuts = [-SINK + 10, m_high * 1.15, height * 0.3, height * 0.55, height * 0.75, height * 0.88]
    front = -math.pi / 2
    out = []

    def ring(z):
        rg = min(rings, key=lambda r: abs(r[0][2] - z))
        poly = _hull2([(p[0], p[1]) for p in rg[:-1]])
        c = (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
        return [(c[0] + (x - c[0]) * 0.93, c[1] + (y - c[1]) * 0.93) for x, y in poly], c
    for z0, z1 in zip(cuts, cuts[1:]):
        low = z0 < m_high
        angles = ([front - CHORD, front + CHORD] + [front + CHORD + (math.tau - 2 * CHORD) * k / 11 for k in range(1, 11)]) if low             else [front + math.tau * k / 12 for k in range(12)]
        angles = sorted(a % math.tau for a in angles)
        poly0, c0 = ring(z0)
        poly1, c1 = ring(z1)
        base = [_ray(poly0, c0, a) for a in angles]
        # (corners on one straight edge of the hull make two faces in one plane, which Havok's solid can't hold: out)
        keep = True
        while keep and len(base) > 4:
            keep = False
            for j in range(len(base)):
                p0, p1, p2 = base[j - 1], base[j], base[(j + 1) % len(base)]
                cr = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
                if abs(cr) < 0.02 * math.dist(p0, p2) ** 2 + 1.0:
                    del base[j]
                    keep = True
                    break
        angles = base
        r_0 = sum(math.hypot(x - c0[0], y - c0[1]) for x, y in poly0) / len(poly0)
        r_1 = sum(math.hypot(x - c1[0], y - c1[1]) for x, y in poly1) / len(poly1)
        k = min(1.0, r_1 / r_0)
        top = [(c1[0] + (x - c0[0]) * k, c1[1] + (y - c0[1]) * k) for x, y in base]
        pts = [(x, y, z0) for x, y in base] + [(x, y, z1) for x, y in top]
        n = len(angles)
        faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
        for j in range(n):
            j2 = (j + 1) % n
            faces.append([j, j2, n + j2, n + j])
        out.append({'points': pts, 'faces': faces, 'material': 'organic'})
    return out


def mouth_spot(kind):
    """(x, y, z) where the door's middle stands at the mouth: against the collision's straight front at the ground."""
    edid, _f, r0, *_ = KINDS[kind]
    s = solids(kind)[0]['points']
    # (in front of the front's furthest point at any height of that piece: the door is as tall as it)
    return (0.0, round(min(p[1] for p in s) - 4.0, 1), 0.0)


# ---------- the pictures (numpy, PIL: a build step, as armourset) ----------

def _noise(rnd, h, w, cells_y, cells_x):
    """Smooth noise (h, w) tiling across, from a coarse grid of cells_y x cells_x."""
    import numpy as np
    g = np.array([[rnd.random() for _ in range(cells_x)] for _ in range(cells_y + 1)], np.float32)
    ys = np.linspace(0, cells_y, h, endpoint=False)
    xs = np.linspace(0, cells_x, w, endpoint=False)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    fy, fx = ys - y0, xs - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0 % cells_x]
    b = g[y0][:, (x0 + 1) % cells_x]
    c = g[np.minimum(y0 + 1, cells_y)][:, x0 % cells_x]
    d = g[np.minimum(y0 + 1, cells_y)][:, (x0 + 1) % cells_x]
    top = a + (b - a) * fx[None, :]
    bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


@functools.lru_cache(maxsize=None)
def paper(size=1024, seed=5):
    """(rgb (h, w, 3), height (h, w), None) of one band of the shell, top to lower edge: fine wavy stripes of chewed paper
    in greys and buffs, now and then tan, the fibre along them, a little darker and rougher toward the edge. It is laid
    about eight times as wide as it is tall on the shell, so it is painted that much narrower across. Tiles across."""
    import numpy as np
    rnd = random.Random(seed)
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v, u = yy / h, xx / w
    wob = sum(rnd.uniform(0.01, 0.03) * np.sin(math.tau * (k * u) + rnd.uniform(0, math.tau)) for k in (1, 2, 3, 4, 6))
    wob += 0.08 * (_noise(rnd, h, w, 4, 24) - 0.5) + 0.03 * (_noise(rnd, h, w, 10, 60) - 0.5)
    s = (v + wob) * 9.0                                 # (stripes, each a mouthful of a different wood)
    idx = np.floor(s).astype(int)
    pal = np.array(PAPER, np.float32)
    order = np.array([rnd.randrange(len(PAPER)) for _ in range(64)])
    col = pal[order[idx % 64]]
    f = s - np.floor(s)
    edge = np.clip(1 - np.abs(f - 0.5) * 2, 0, 1)       # (each stripe's own edges a hair darker)
    fibre = _noise(rnd, h, w, 220, 30)
    fibre2 = _noise(rnd, h, w, 500, 80)
    blot = _noise(rnd, h, w, 6, 30)
    col = col * (0.88 + 0.14 * fibre[..., None] + 0.08 * fibre2[..., None]) * (0.9 + 0.1 * edge[..., None] ** 0.3) * (0.9 + 0.2 * blot[..., None])
    under = np.clip((v - 0.85) / 0.15, 0, 1) ** 1.5      # (the lower edge, where it's lifted: a little shade)
    col = col * (1 - 0.25 * under[..., None])
    height = 0.45 + 0.2 * edge ** 0.4 + 0.15 * fibre2 - 0.15 * under
    return np.clip(col, 0, 255), np.clip(height, 0, 1), None


@functools.lru_cache(maxsize=None)
def crack(size=256, seed=7):
    """(rgb, height, glow) of the narrow crack under a flap, from the flap's edge (top) in to the next band (bottom):
    dark paper, and the inside's green light brightest deep in."""
    import numpy as np
    rnd = random.Random(seed)
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = yy / h
    tone = _noise(rnd, h, w, 4, 16)
    col = np.array((44, 40, 34), np.float32) * (0.7 + 0.5 * tone[..., None])
    # (only deep in, where the crack meets the band under it, and faint: light seeping out, nothing growing)
    deep = np.clip((v - 0.35) / 0.65, 0, 1) ** 1.3
    flick = 0.4 + 0.6 * _noise(rnd, h, w, 3, 10) ** 2
    glow = (0.6 * deep * flick)[..., None] * np.array(GLOW, np.float32)[None, None, :]
    col = col * (1 - 0.3 * deep[..., None]) + 0.12 * glow
    return np.clip(col, 0, 255), 0.4 + 0.2 * tone, np.clip(glow, 0, 255)


@functools.lru_cache(maxsize=None)
def dark(size=512, seed=6):
    """(rgb, height, glow) of a hole into the nest, laid round its middle (the middle of the picture the hole's own):
    paper in rings spiralling in and darker toward the middle, as a nest's entrance funnel is, and deep in it a faint
    green light and the edge of the comb."""
    import numpy as np
    rnd = random.Random(seed)
    n = size
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = (xx - n / 2) / (n / 2), (yy - n / 2) / (n / 2)
    q = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    pal = np.array(PAPER, np.float32)
    rings = (q * 16 + ang / math.tau * 1.0 + 0.15 * _noise(rnd, n, n, 6, 6))
    col = pal[np.floor(rings).astype(int) % len(pal)] * (0.85 + 0.2 * _noise(rnd, n, n, 64, 64))[..., None]
    shade = np.clip(q * 1.25, 0, 1) ** 1.3            # (dark toward the middle)
    col = col * (0.08 + 0.92 * shade[..., None])
    deep = np.clip(1 - q / 0.45, 0, 1) ** 1.5
    flick = 0.5 + 0.5 * _noise(rnd, n, n, 5, 5)
    glow = (0.55 * deep * flick)[..., None] * np.array(GLOW, np.float32)[None, None, :]
    height = 0.3 + 0.4 * np.clip(q, 0, 1) + 0.1 * (rings - np.floor(rings))
    return np.clip(col + 0.15 * glow, 0, 255), np.clip(height, 0, 1), np.clip(glow, 0, 255)


COMB_ACROSS, COMB_ROWS = 12, 14        # (whole cells across and rows down: the picture tiles)


@functools.lru_cache(maxsize=None)
def comb(size=1024, seed=8):
    """(rgb, height, glow, gloss) of open comb as a real nest's is: hexagon cells (true hexagons, the grid tiling), their
    paper walls lit along one rim and shadowed along the other, and in each cell what a nest holds: empty and dark deep in,
    a glossy egg at the back, a pale curled larva, a domed paper cap, or rad honey (amber gone green, shining, faintly
    alight); a very few lit from deep inside. Heights for the normal map (walls up, cells down, caps domed), gloss for the
    shine (wet things glisten, paper doesn't)."""
    import numpy as np
    rnd = random.Random(seed)
    n = size
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    rx = n / COMB_ACROSS / math.sqrt(3)         # (a cell's radius across and down: the grid fits the picture whole)
    ry = n / COMB_ROWS / 1.5
    # pointy-topped hexagons: axial coordinates, rounded through cube coordinates to the nearest cell's middle
    px, py = xx / rx, yy / ry
    q = (math.sqrt(3) / 3 * px - py / 3)
    r = 2.0 / 3 * py
    x3, z3 = q, r
    y3 = -x3 - z3
    rx3, ry3, rz3 = np.round(x3), np.round(y3), np.round(z3)
    dx, dy, dz = np.abs(rx3 - x3), np.abs(ry3 - y3), np.abs(rz3 - z3)
    fx = (dx > dy) & (dx > dz)
    fz = ~fx & (dz > dy)
    rx3 = np.where(fx, -ry3 - rz3, rx3)
    rz3 = np.where(fz, -rx3 - ry3, rz3)
    cq, cr = rx3, rz3
    cxp = (math.sqrt(3) * cq + math.sqrt(3) / 2 * cr)      # (the cell's middle, in radii)
    cyp = 1.5 * cr
    ox, oy = px - cxp, py - cyp                              # (where in the cell, in radii)
    # hexagon distance: 1 at the wall's middle line
    hd = np.maximum.reduce([np.abs(ox * math.cos(a_) + oy * math.sin(a_)) for a_ in (0.0, math.pi / 3, 2 * math.pi / 3)]) / (math.sqrt(3) / 2)
    wall = np.clip((hd - 0.72) / 0.12, 0, 1)
    # which cell (wrapping round the picture, so the tiles repeat cleanly)
    col = np.floor(cq + cr / 2).astype(int) % COMB_ACROSS
    row = cr.astype(int) % COMB_ROWS
    kinds = {}
    for c in range(COMB_ACROSS):
        for r_ in range(COMB_ROWS):
            v = rnd.random()
            kinds[(c, r_)] = ('empty' if v < 0.34 else 'larva' if v < 0.56 else 'egg' if v < 0.66 else 'cap' if v < 0.86
                              else 'honey' if v < 0.97 else 'lit', rnd.uniform(0, math.tau), rnd.random())
    K = np.vectorize(lambda c, r_: ['empty', 'larva', 'egg', 'cap', 'honey', 'lit'].index(kinds[(c, r_)][0]))(col, row)
    turn = np.vectorize(lambda c, r_: kinds[(c, r_)][1])(col, row)
    tone = _noise(rnd, n, n, 40, 40)
    fibre = _noise(rnd, n, n, 160, 160)
    # light from the top left: a wall lit where it faces it, a cell's floor shadowed under its upper wall
    lightx, lighty = -0.6, -0.8
    facing = (ox * lightx + oy * lighty)
    paper = np.array((160, 152, 136), np.float64) * (0.85 + 0.2 * fibre)[..., None]
    deep = np.array((20, 17, 14), np.float64)
    inside = 1 - wall
    # the cell's own floor and sides: dark deep in, the side toward the light in shadow, the far side catching it
    cell_shade = np.clip(0.08 + 0.75 * (hd ** 2.2) * (0.55 - 0.75 * facing), 0.03, 1.0)     # (deep and dark in the middle)
    rgb = deep[None, None, :] * (1 - cell_shade[..., None]) + paper * 0.55 * cell_shade[..., None]
    height = 0.08 + 0.35 * hd ** 2
    gloss = np.full((n, n), 70.0)
    rr = np.hypot(ox, oy)
    # what is in each cell
    ca, sa = np.cos(turn), np.sin(turn)
    lx, ly = ox * ca + oy * sa, -ox * sa + oy * ca
    egg = (K == 2) & (((lx - 0.1) / 0.22) ** 2 + (ly / 0.14) ** 2 < 1)
    rgb[egg] = (np.array((226, 230, 208))[None, :] * (0.55 + 0.35 * np.sqrt(np.clip(1 - ((lx[egg] - 0.1) / 0.22) ** 2 - (ly[egg] / 0.14) ** 2, 0, 1)))[:, None]
                + 255 * 0.5 * np.exp(-((lx[egg] - 0.04) ** 2 + (ly[egg] + 0.05) ** 2) / 0.002)[:, None])
    height[egg] = 0.45
    gloss[egg] = 200
    ang = np.arctan2(ly, lx)
    # a grub as it lies in its cell, seen from the opening: a fat pale body curled into a C round the cell (a tube, rounded
    # across, in rings along it), its small brown head at one end, the inside of the curl in shadow
    ang = np.mod(np.arctan2(ly, lx), math.tau)
    span = 5.2                                               # (how far round the cell it curls, radians)
    along = ang / span                                       # (0 at its tail, 1 at its head)
    mid = 0.36 - 0.05 * along                                # (it curls a little tighter toward the head)
    thick = 0.2 * (0.75 + 0.35 * np.sin(np.clip(along, 0, 1) * math.pi))     # (fattest in the middle)
    across = np.abs(rr - mid) / thick
    tube = (across < 1) & (ang < span)
    tail = np.hypot(lx - mid * 1.0, ly) < 0.15               # (the tail end, rounded)
    larva = (K == 1) & (tube | tail)
    across = np.where(tube, across, np.clip(np.hypot(lx - 0.36, ly) / 0.15, 0, 1))
    round_ = np.sqrt(np.clip(1 - across ** 2, 0, 1))
    rings = 0.9 + 0.1 * np.cos(along * math.tau * 6)         # (its segments, across the body)
    lit_side = np.clip(0.8 - 0.35 * facing, 0.45, 1.1)
    shade = (0.25 + 0.75 * round_) * rings * lit_side
    rgb[larva] = np.array((238, 232, 206))[None, :] * shade[larva][:, None]
    height[larva] = 0.3 + 0.45 * round_[larva]
    ha = span + 0.25
    head = (K == 1) & (np.hypot(lx - 0.32 * math.cos(ha), ly - 0.32 * math.sin(ha)) < 0.11)
    rgb[head] = np.array((132, 90, 42))[None, :] * (0.7 + 0.4 * np.clip(-facing[head] + 0.4, 0, 1))[:, None]
    height[head] = 0.55
    gloss[head] = 150
    gloss[larva] = 170
    cap = (K == 3) & (hd < 0.86)
    dome = np.clip(1 - (hd / 0.86) ** 2, 0, 1)
    rgb[cap] = np.array((196, 188, 168))[None, :] * (0.55 + 0.25 * dome[cap] - 0.45 * facing[cap] * dome[cap] + 0.12 * fibre[cap])[:, None]
    height[cap] = 0.55 + 0.35 * dome[cap]
    gloss[cap] = 40
    honey = (K == 4) & (hd < 0.84)
    spec = np.exp(-((ox + 0.28) ** 2 + (oy + 0.32) ** 2) / 0.012)          # (a wet highlight)
    rgb[honey] = (np.array((150, 104, 22))[None, :] * (0.55 + 0.45 * np.clip(hd[honey], 0, 1))[:, None]
                  + np.array((40, 60, 10))[None, :] * 0.5 + 255 * 0.7 * spec[honey][:, None])
    height[honey] = 0.3
    gloss[honey] = 255
    # the walls over all: paper, a highlight along the lit rim, shadow on the other
    wl = wall > 0
    rim = np.clip(-facing, -1, 1)
    bevel = np.clip((hd - 0.72) / 0.12, 0, 1) * np.clip((1.0 - hd) / 0.12, 0, 1)      # (the wall's top: brightest)
    rgb[wl] = (rgb[wl] * (1 - wall[wl, None]) + (paper[wl] * (0.6 + 0.45 * rim[wl] + 0.3 * bevel[wl])[:, None]) * wall[wl, None])
    height = height * (1 - wall) + wall * (0.95 + 0.05 * tone)
    gloss = gloss * (1 - wall) + 30 * wall
    rgb *= (0.9 + 0.2 * tone)[..., None]
    # light: honey faintly alight, a very few cells lit from deep in, a thread or two of vein over the walls
    lit = np.zeros((n, n))
    lit[honey] = 0.07                                   # (a green sheen in the amber, not a lamp)
    deep_lit = (K == 5) & (hd < 0.8)
    lit[deep_lit] = 0.45 * np.clip(1 - hd[deep_lit] / 0.8, 0, 1)
    glow = lit[..., None] * np.array(GLOW, np.float64)[None, None, :]
    rgb = rgb + 0.2 * glow
    return (np.clip(rgb, 0, 255).astype(np.float32), np.clip(height, 0, 1).astype(np.float32), np.clip(glow, 0, 255).astype(np.float32),
            np.clip(gloss, 0, 255).astype(np.float32))


def _canvas(rgb, height, gloss=None):
    """A texpaint Canvas of the arrays; gloss (0-255 a pixel) is the normal map's shine: pass shine=None to files()."""
    import texpaint
    h, w = height.shape
    c = texpaint.Canvas(w, h)
    c.rgb = [tuple(float(v) for v in px) for px in rgb.reshape(-1, 3)]
    c.ht = [float(v) for v in height.reshape(-1)]
    if gloss is not None:
        c.gloss = [float(v) for v in gloss.reshape(-1)]
    return c


@functools.lru_cache(maxsize=None)
def texture_files():
    """{path: bytes} of the hive's pictures: paper and dark, each colour, normal map and glow."""
    import dds
    out = {}
    for name, fn in (('paper', paper), ('crack', crack), ('dark', dark), ('comb', comb)):
        got = fn()
        rgb, ht, glow = got[:3]
        if len(got) > 3:
            col, nor = _canvas(rgb, ht, got[3]).files(game=True, shine=None)
        else:
            col, nor = _canvas(rgb, ht).files(game=True, shine=12)
        out[TEX % name], out[TEX % (name + '_n')] = col, nor
        if glow is None:
            continue
        h, w = ht.shape
        import numpy as np
        g = np.concatenate([glow.astype(np.uint8), np.full((h, w, 1), 255, np.uint8)], axis=2)
        out[TEX % (name + '_g')] = dds.compress(dds.encode(w, h, g.tobytes()))
    return out


# ---------- the ruin it grew over ----------

def ruin_desc(kind):
    """The building it grew over (modelmake parts): four concrete walls, broken along their tops (some stretches standing
    over the rest, through the nest's dome), a doorway in the front (-y) where the hive's mouth is, a roof slab fallen in
    two, rebar out of the breaks. Solid where the paper doesn't already stand."""
    import modelsets
    modelsets._all_sets()
    edid, _f, r0, height, *_rest = KINDS[kind]
    _m_half, m_high, _d = KINDS[kind][7]
    bx, by, bh = BUILDINGS[kind]
    rnd = random.Random(KINDS[kind][5] + 100)
    T = 30.0
    parts = []

    def wall(x0, y0, x1, y1, door=False):
        long = math.hypot(x1 - x0, y1 - y0)
        turn = math.degrees(math.atan2(y1 - y0, x1 - x0))
        n = max(3, int(long // 150))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            mid = (t0 + t1) / 2
            if door and abs(mid - 0.5) < 0.6 / n:
                # (the doorway: a lintel over it)
                tall, low = bh - m_high - 40, m_high + 40
            else:
                tall, low = bh * rnd.choice((0.82, 0.9, 0.97, 1.08, 1.22, 1.3)), 0.0
            cx, cy = x0 + (x1 - x0) * mid, y0 + (y1 - y0) * mid
            parts.append({'shape': 'box', 'size': [long / n + 2, T, tall + (SINK if low == 0 else 0)], 'look': 'concrete',
                          'at': [cx, cy, low - (SINK if low == 0 else 0)], 'turn': [0, 0, turn], 'solid': tall > bh,
                          'material': 'stone'})
    wall(-bx, -by, bx, -by, door=True)
    wall(bx, -by, bx, by)
    wall(bx, by, -bx, by)
    wall(-bx, by, -bx, -by)
    # (the roof fallen in two, leaning over the walls' tops inside the dome)
    parts.append({'shape': 'box', 'size': [bx * 1.1, by * 1.9, 24], 'look': 'concrete', 'at': [-bx * 0.45, 0, bh * 0.86], 'turn': [0, 9, 0]})
    parts.append({'shape': 'box', 'size': [bx * 1.0, by * 1.8, 24], 'look': 'concrete', 'at': [bx * 0.5, 0, bh * 0.8], 'turn': [0, -14, 0]})
    for _n in range(9):
        side = rnd.randrange(4)
        t = rnd.uniform(-0.9, 0.9)
        x, y = [(t * bx, -by), (bx, t * by), (t * bx, by), (-bx, t * by)][side]
        parts.append({'shape': 'cylinder', 'r': 2.2, 'r2': 2.2, 'h': rnd.uniform(60, 140), 'sides': 5, 'look': 'rebar', 'solid': False,
                      'at': [x, y, bh * rnd.uniform(1.0, 1.25)], 'turn': [rnd.uniform(-35, 35), rnd.uniform(-35, 35), 0]})
    looks = {'concrete': modelsets.look('concrete', tile=256), 'rebar': modelsets.look('city/rust', tile=64)}
    return {'name': edid + 'Ruin', 'looks': looks, 'parts': parts, 'ground': True}


def _ruin_textures(desc):
    import modelsets
    modelsets._all_sets()
    out = {}
    for name in ('concrete', 'city/rust'):
        if any(lk['tex'] == modelsets.tex_path(name) for lk in desc['looks'].values()):
            out[modelsets.tex_path(name)], out[modelsets.tex_path(name, True)] = modelsets.texture_files(name)
    return out


# ---------- the model ----------

def far_shapes(kind):
    shapes, _sh = shell_shapes(kind, FAR_SIDES, lips=False)
    for s in shapes:
        s.pop('glow', None)
        s.pop('glow_mult', None)
    return shapes


def build(kind):
    """The hive made: {'nif', 'far', 'files' {path: bytes}, 'mesh', 'box', 'triangles', 'mouth', 'shapes', 'solids'}."""
    import modelmake
    import nifmake
    import shade
    edid, fname, *_ = KINDS[kind]
    shapes, sh = shell_shapes(kind)
    shade.bake(shapes, seed=KINDS[kind][5], ground=True)
    sol = solids(kind)
    files = {}
    if KINDS[kind][6]:
        rd = ruin_desc(kind)
        ruin = modelmake.make(rd)
        shapes = shapes + ruin['shapes']
        sol = sol + ruin['solids']
        files.update(_ruin_textures(rd))
    data = nifmake.build(edid, shapes, sol)
    far_data = nifmake.build(edid + 'Far', far_shapes(kind))
    mesh = MESH % fname
    files[mesh] = data
    files[mesh[:-4] + '_lod.nif'] = far_data
    files.update(texture_files())
    lo = [math.floor(min(min(s['p'][a::3]) for s in shapes)) for a in range(3)]
    hi = [math.ceil(max(max(s['p'][a::3]) for s in shapes)) for a in range(3)]
    return {'nif': data, 'far': far_data, 'files': files, 'mesh': mesh, 'box': lo + hi, 'shapes': shapes, 'solids': sol,
            'triangles': sum(len(s['i']) // 3 for s in shapes), 'mouth': mouth_spot(kind)}


# ---------- the heart, and the hive burnt ----------

HEART = ('FOLabVespidHeart', 'vespid_heart')
BURNT = {'paper': 'paper_burnt', 'crack': 'crack_burnt', 'dark': 'dark_burnt'}


def heart_desc():
    """What you set alight in a hive's mouth: a mass of comb, lit from within, as tall as a man's chest, solid so it can
    be activated."""
    look = {'tex': TEX % 'comb', 'normal': TEX % 'comb_n', 'glow': TEX % 'comb_g', 'glow_mult': 2.0}
    parts = [{'shape': 'ball', 'r': 46, 'sides': 12, 'rings': 7, 'look': 'comb', 'scale': [1.3, 0.8, 1.0], 'at': [0, 0, -8],
              'solid': True, 'material': 'organic'},
             {'shape': 'ball', 'r': 30, 'sides': 10, 'rings': 6, 'look': 'comb', 'scale': [1.0, 0.8, 1.1], 'at': [-34, 6, 52], 'solid': False},
             {'shape': 'ball', 'r': 26, 'sides': 10, 'rings': 6, 'look': 'comb', 'scale': [1.0, 0.8, 1.0], 'at': [38, -2, 48], 'solid': False}]
    return {'name': HEART[0], 'looks': {'comb': look}, 'parts': parts, 'ground': True}


def heart():
    """{'nif', 'mesh', 'box', 'files'}: the heart, its pictures among the hive's."""
    import modelmake
    made = modelmake.make(heart_desc())
    mesh = MESH % HEART[1]
    return {'nif': made['nif'], 'mesh': mesh, 'box': made['box'], 'files': {mesh: made['nif']}}


def burnt_pictures():
    """{path: bytes}: the hive's pictures once it has burnt: the paper scorched black and grey, its inside dead (glow
    pictures black)."""
    import numpy as np
    import dds
    out = {}
    for name, fn in (('paper', paper), ('crack', crack), ('dark', dark)):
        rgb, ht, _g = fn()
        rnd = random.Random(91)
        soot = _noise(rnd, ht.shape[0], ht.shape[1], 8, 16)
        rgb = rgb * (0.22 + 0.25 * soot[..., None]) + np.array((18, 16, 14), np.float32) * 0.5
        col, nor = _canvas(rgb, ht * 0.8 + 0.1).files(game=True, shine=4)
        out[TEX % BURNT[name]], out[TEX % (BURNT[name] + '_n')] = col, nor
    out[TEX % 'burnt_g'] = dds.compress(dds.encode(4, 4, bytes((0, 0, 0, 255)) * 16))
    return out


def burnt_nif(data):
    """A hive's model with its pictures swapped for the burnt ones (and its glow for black)."""
    import nifwrite
    ch = {}
    for name, b in BURNT.items():
        ch[TEX % name] = TEX % b
        ch[TEX % (name + '_n')] = TEX % (b + '_n')
        ch[TEX % (name + '_g')] = TEX % 'burnt_g'
    have = {nifwrite.key(t['path']) for t in nifwrite.textures_in(data)}
    return nifwrite.retexture(data, {a: b for a, b in ch.items() if nifwrite.key(a) in have})


def all_files(progress=print):
    """{path: bytes} of every hive model (each kind, alive and burnt, with its far model) and all pictures;
    and {kind: {'mesh', 'burnt', 'box', 'mouth'}}."""
    files, info = {}, {}
    for kind in KINDS:
        made = build(kind)
        files.update(made['files'])
        burnt = made['mesh'][:-4] + '_burnt.nif'
        files[burnt] = burnt_nif(made['nif'])
        files[burnt[:-4] + '_lod.nif'] = burnt_nif(made['far'])
        info[kind] = {'mesh': made['mesh'], 'burnt': burnt, 'box': made['box'], 'mouth': made['mouth'], 'triangles': made['triangles']}
        if progress:
            progress('hive %s: %d triangles' % (kind, made['triangles']))
    files.update(burnt_pictures())
    return files, info
