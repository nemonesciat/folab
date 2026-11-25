"""Waikiki's collectibles sculpted (the user, 25 Nov 2026: "they'd look like real collectibles at least as nice as the
bobbleheads in game, with realistic detail, relief, texture, lighting... Just make em look nice please").

The game's bobblehead (Clutter\\BobbleHead\\*.nif) is ~800 smooth-shaded triangles, 16 units tall, on one 256 painted
picture. These are made the same way and finer: smooth surfaces (normals shared where surfaces meet), one painted
512 picture an item with its normal map (relief from the painting's heights: texpaint, as the game's own models are),
shade baked into the corners (shade.bake).

- **Surfaces** (`Part`): `lathe` (a profile turned round an axis, with a radius that may vary round it), `sweep` (a tube
  along a path, its ends rounded), `pillow` (a flat carved piece: an outline round its middle, a hole or none, the faces
  domed to a rounded rim, the carving's heights pushing the face). Each is closed (a poled or looped surface), so every
  model passes nifmake.open_edges.
- **The hula doll** (`doll`): a painted base with HAWAII round its side, a coiled spring at her waist (the bobbing),
  legs and feet, a grass skirt of strands round a ragged hem, hips, waist, bust and a bikini top in her colour, a lei
  of blossoms, shoulders and arms in her pose (`collectibles.DOLLS`), hands, a head with a nose and chin, a painted face
  (eyes, brows, lashes, mouth, cheeks), long hair falling down her back, a hibiscus over her ear.
- **The jade charm** (`charm`): the carving's outline as a pillowed piece with its carving cut into the face (`CARVE`:
  bi disc with raised grain and a hole, gourd with a vine and leaf, carp with scales, eye and tail, cicada with its
  wings and bands, cash coin with its square hole), polished; a gold bail and a red silk cord tied in a loop.

    doll_shapes(stat) / charm_shapes(skill)   [shapes] (for nifmake) and their pictures {texture path: (colour, normal) DDS}
"""
import math

import texpaint as tp

SHEET = 512
INSET = 3           # (pixels each part's picture keeps off its region's edge: the smaller copies blur across it)
TEX = 'textures\\folab\\collect2\\%s.dds'


def _norm(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def _turn(p, about, axis, deg):
    """p turned deg degrees about a line through `about` along x, y or z (0, 1, 2)."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = p[0] - about[0], p[1] - about[1], p[2] - about[2]
    if axis == 0:
        y, z = y * c - z * s, y * s + z * c
    elif axis == 1:
        x, z = x * c + z * s, -x * s + z * c
    else:
        x, y = x * c - y * s, x * s + y * c
    return (x + about[0], y + about[1], z + about[2])


class Part:
    """Corners, their picture places and triangles of one closed surface; normals worked out over the whole part by
    position (so a seam or a pole is smooth)."""

    def __init__(self, region):
        self.region = region            # (u0, v0, u1, v1) in pixels of the sheet: where (s, t) in 0-1 lands
        self.p, self.uv, self.t = [], [], []

    def vert(self, p, s, t, planar=None):
        if planar is not None:
            u, v = planar
        else:
            u0, v0, u1, v1 = self.region
            u0, v0, u1, v1 = u0 + INSET, v0 + INSET, u1 - INSET, v1 - INSET      # (kept off the neighbour's pixels)
            u, v = (u0 + (u1 - u0) * s) / SHEET, (v0 + (v1 - v0) * (1.0 - t)) / SHEET
        self.p.append(p)
        self.uv.append((u, v))
        return len(self.p) - 1

    def rings(self, rings, start=None, end=None, closed=False, planar=None):
        """rings: [[point ...] ...], each ring N + 1 points (the last at the first's place, for the picture's seam),
        going round counter-clockwise seen from where the rings go to. start/end: a pole point closing that end;
        closed: the last ring joins the first (a torus). planar: fn(point) -> (u, v) instead of the ring's own."""
        M, N = len(rings), len(rings[0]) - 1
        idx = []
        for k, ring in enumerate(rings):
            t = k / (M - 1 if M > 1 and not closed else M)
            idx.append([self.vert(q, j / N, t, planar(q) if planar else None) for j, q in enumerate(ring)])
        span = range(M - 1 + (1 if closed else 0))
        for k in span:
            a, b = idx[k], idx[(k + 1) % M]
            if closed and k == M - 1:
                b = idx[0]
            for j in range(N):
                self.t += [(a[j], a[j + 1], b[j + 1]), (a[j], b[j + 1], b[j])]
        if start is not None:
            for j in range(N):
                pole = self.vert(start, (j + 0.5) / N, 0.0, planar(start) if planar else None)
                self.t.append((idx[0][j + 1], idx[0][j], pole))
        if end is not None:
            for j in range(N):
                pole = self.vert(end, (j + 0.5) / N, 1.0, planar(end) if planar else None)
                self.t.append((idx[-1][j], idx[-1][j + 1], pole))
        return self

    def shape(self, tex, gloss=20.0):
        acc = {}
        key = lambda q: (round(q[0], 4), round(q[1], 4), round(q[2], 4))
        for a, b, c in self.t:
            n = _cross(_sub(self.p[b], self.p[a]), _sub(self.p[c], self.p[a]))
            for v in (a, b, c):
                k = key(self.p[v])
                o = acc.get(k, (0.0, 0.0, 0.0))
                acc[k] = (o[0] + n[0], o[1] + n[1], o[2] + n[2])
        P, Nn, UV, I = [], [], [], []
        for q, (u, v) in zip(self.p, self.uv):
            P += list(q)
            Nn += list(_norm(acc.get(key(q), (0, 0, 1))))
            UV += [u, v]
        for tri in self.t:
            if len({key(self.p[v]) for v in tri}) == 3:        # (a pole's sliver of no size is left out)
                I += list(tri)
        return {'p': P, 'n': Nn, 'uv': UV, 'i': I, 'tex': tex, 'normal': tex[:-4] + '_n.dds', 'gloss': gloss, 'alpha': 0,
                'glow': '', 'glow_mult': 1.0}


def _ring(cx, cy, z, rx, ry, N, rmod=None, zmod=None):
    out = []
    for j in range(N + 1):
        a = 2 * math.pi * (j % N) / N
        m = rmod(a) if rmod else 1.0
        out.append((cx + rx * m * math.cos(a), cy + ry * m * math.sin(a), z + (zmod(a) if zmod else 0.0)))
    return out


def body(region, sections, N=24, rmod=None, start=None, end=None):
    """A smooth body from sections [(z, rx, ry, cx, cy)] bottom to top; rmod(angle, z) scales the radius round it;
    start/end: True for a pole at the section's middle."""
    rings = [_ring(cx, cy, z, rx, ry, N, (lambda a, z=z: rmod(a, z)) if rmod else None) for z, rx, ry, cx, cy in sections]
    s0, s1 = sections[0], sections[-1]
    P = Part(region)
    P.rings(rings, start=(s0[3], s0[4], s0[0]) if start is True else start, end=(s1[3], s1[4], s1[0]) if end is True else end)
    return P


def sweep(region, path, radii, N=10, round_ends=True, flat=1.0, closed=False):
    """A tube along `path` (points), its radius `radii` at each; ends rounded (half balls) unless closed (a loop).
    flat: the tube's section squashed along its frame's second axis (a ribbon, a strand)."""
    M = len(path)
    T = []
    for k in range(M):
        a = path[(k - 1) % M] if closed or k > 0 else path[k]
        b = path[(k + 1) % M] if closed or k < M - 1 else path[k]
        T.append(_norm(_sub(b, a)))
    up = (0.0, 0.0, 1.0) if abs(T[0][2]) < 0.9 else (1.0, 0.0, 0.0)
    Nv = _norm(_cross(_cross(T[0], up), T[0]))
    frames = []
    for k in range(M):
        if k:
            Nv = _norm(_sub(Nv, (T[k][0] * (Nv[0] * T[k][0] + Nv[1] * T[k][1] + Nv[2] * T[k][2]),
                                 T[k][1] * (Nv[0] * T[k][0] + Nv[1] * T[k][1] + Nv[2] * T[k][2]),
                                 T[k][2] * (Nv[0] * T[k][0] + Nv[1] * T[k][1] + Nv[2] * T[k][2]))))
        frames.append((Nv, _cross(T[k], Nv)))

    def ring(c, t, n, b, r):
        return [_add(_add(c, n, r * math.cos(2 * math.pi * (j % N) / N)), b, flat * r * math.sin(2 * math.pi * (j % N) / N)) for j in range(N + 1)]
    rings = []
    if round_ends and not closed:
        for step in (0.5, 0.86):
            phi = math.acos(step)
            n, b = frames[0]
            rings.append(ring(_add(path[0], T[0], -radii[0] * math.sin(phi)), T[0], n, b, radii[0] * step))
    for k in range(M):
        n, b = frames[k]
        rings.append(ring(path[k], T[k], n, b, radii[k]))
    start = end = None
    if round_ends and not closed:
        for step in (0.86, 0.5):
            phi = math.acos(step)
            n, b = frames[-1]
            rings.append(ring(_add(path[-1], T[-1], radii[-1] * math.sin(phi)), T[-1], n, b, radii[-1] * step))
        start, end = _add(path[0], T[0], -radii[0]), _add(path[-1], T[-1], radii[-1])
    P = Part(region)
    # (rings go round counter-clockwise seen from where the path goes: frames n, b with n x b = t)
    P.rings(rings, start=start, end=end, closed=closed)
    return P


def pillow(region, outer, inner, thick, relief=None, N=72, steps=8, planar=None, rim=0.35):
    """A flat piece lying on z 0: its outline outer(angle) round the origin, a hole inner(angle) (or None), thick in all,
    its faces domed toward the middle and rounded into the rim; relief(x, y) -> 0-1 pushes the top face up by `rim` of
    the thickness... (the carving)."""
    h = thick / 2.0
    prof = []                                   # (s across 0-1 from the hole or middle out, z), counter-clockwise
    if inner:
        prof += [(0.0, -h * 0.7)]
    across = [0.85 * k / steps for k in range(steps + 1)] if inner else [0.0] + [0.2 + 0.65 * (k - 1) / (steps - 1) for k in range(1, steps + 1)]
    for s in across:                            # (the underside, middle out; no ring crowded round a pole)
        prof.append((s, -h * (1.0 - 0.15 * (s / 0.85) ** 2)))
    for k in range(1, 6):                       # (round the rim)
        a = -math.pi / 2 + math.pi * k / 6
        prof.append((0.85 + 0.15 * math.cos(a), h * 0.85 * math.sin(a)))
    for s in reversed(across):                  # (the top, back to the middle)
        prof.append((s, h * (1.0 - 0.15 * (s / 0.85) ** 2)))
    if inner:
        prof.append((0.0, h * 0.7))
    rings = []
    for s, z in prof:
        ring = []
        for j in range(N + 1):
            a = 2 * math.pi * (j % N) / N
            r0 = inner(a) if inner else 0.0
            r = r0 + s * (outer(a) - r0)
            x, y = r * math.cos(a), r * math.sin(a)
            zz = z
            if relief and z > 0 and s < 0.9:
                zz += thick * rim * relief(x, y) * min(1.0, (0.9 - s) / 0.1)
            elif relief and z < 0 and s < 0.9:
                zz -= thick * rim * 0.6 * relief(-x, y) * min(1.0, (0.9 - s) / 0.1)       # (the back carved too, as a mirror)
            ring.append((x, y, zz))
        rings.append(ring)
    P = Part(region)
    if inner:
        P.rings(rings, closed=True, planar=planar)
    else:
        rings[0] = rings[0]
        P.rings(rings[1:-1], start=(0.0, 0.0, prof[0][1]), end=(0.0, 0.0, prof[-1][1]), planar=planar)
    return P


# ---------- the hula doll ----------
SKIN = (222, 170, 128)
HAIR = (30, 22, 20)
REG = {   # where each part paints, in pixels of the doll's sheet
    'skin': (0, 0, 256, 64), 'head': (0, 64, 256, 192), 'torso': (256, 0, 512, 128), 'skirt': (0, 192, 512, 320),
    'hair': (0, 320, 256, 448), 'lei': (256, 320, 512, 384), 'flower': (256, 384, 384, 448), 'spring': (384, 384, 448, 448),
    'basetop': (448, 384, 512, 448), 'base': (0, 448, 512, 512), 'top': (256, 128, 512, 192)}
HIP, WAIST, CHEST, NECK, CHIN, CROWN = 5.6, 6.6, 7.6, 8.75, 9.0, 11.5
TORSO_Z = [HIP - 0.1, HIP + 0.4, WAIST, CHEST - 0.4, CHEST, CHEST + 0.5, NECK - 0.3, NECK, CHIN + 0.1]


def doll_parts(pose):
    """[(region name, Part)] of one doll; pose: ((left arm, right arm) degrees out from hanging, lean degrees)."""
    (al, ar), lean = pose
    out = []
    # the base: a dashboard stand with a rounded edge, HAWAII round its side
    prof = [(3.2, 0.0), (3.45, 0.12), (3.5, 0.45), (3.45, 0.8), (3.3, 0.95)]
    side = Part(REG['base'])
    side.rings([_ring(0, 0, z, r, r, 40) for r, z in prof], start=(0, 0, 0.0))
    out.append(('base', side))
    top = Part(REG['basetop'])                   # (the top its own picture, sharing the side's last ring)
    top.rings([_ring(0, 0, z, r, r, 40) for r, z in ((3.3, 0.95), (3.0, 1.03), (1.5, 1.08))], end=(0, 0, 1.1))
    out.append(('base', top))
    # the spring: a coil from the skirt's top to the waist
    coil = []
    for k in range(57):
        a = 2 * math.pi * k / 12
        coil.append((0.42 * math.cos(a), 0.42 * math.sin(a), HIP + 0.1 + 0.9 * k / 56))
    out.append(('spring', sweep(REG['spring'], coil, [0.09] * len(coil), N=6)))
    # legs: from the base to the hips, a little apart, a knee bent forward; feet
    for side_x in (-0.55, 0.55):
        path = [(side_x * 1.05, -0.35, 1.25), (side_x * 1.05, -0.2, 2.3), (side_x, -0.3, 3.3), (side_x * 0.95, -0.15, 4.4), (side_x * 0.85, 0.0, HIP)]
        out.append(('skin', sweep(REG['skin'], path, [0.36, 0.42, 0.48, 0.58, 0.62], N=12)))
        out.append(('skin', body(REG['skin'], [(1.05, 0.34, 0.6, side_x * 1.05, -0.55), (1.25, 0.38, 0.72, side_x * 1.05, -0.55), (1.45, 0.3, 0.55, side_x * 1.05, -0.45)],
                                 N=12, start=True, end=True)))
    # the grass skirt: strands round a ragged hem, flaring from the waistband
    def strands(a, z):
        if z > HIP:
            return 1.0
        return 1.0 + 0.05 * abs(math.sin(a * 24)) + 0.03 * math.sin(a * 7)
    hem = lambda a: 2.25 + 0.35 * abs(math.sin(a * 11.0 + 1.3)) + 0.2 * abs(math.sin(a * 5.0))
    secs = [(hem(0), 2.65, 2.65)]
    rings = []
    N = 72
    for k, (zf, rad) in enumerate(((0.0, 2.55), (0.25, 2.35), (0.5, 2.0), (0.75, 1.65), (1.0, 1.32))):
        ring = []
        for j in range(N + 1):
            a = 2 * math.pi * (j % N) / N
            z0 = hem(a)
            z = z0 + (HIP + 0.2 - z0) * zf
            r = rad * strands(a, z)
            ring.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(ring)
    # (the skirt's inside: a little in from the outside, back down to the hem, so it is a closed shell)
    inner = [[(q[0] * 0.9, q[1] * 0.9, q[2] + 0.05) for q in ring] for ring in reversed(rings)]
    sk = Part(REG['skirt'])
    sk.rings(rings + inner, closed=True)
    out.append(('skirt', sk))
    del secs
    # the body: hips to neck, a bust; leaning at the waist
    def bust(a, z):
        f = 1.0
        if CHEST - 0.6 < z < CHEST + 0.5:
            w = 1 - abs(z - CHEST) / 0.6
            for c in (-0.42 * math.pi, -0.58 * math.pi):
                d = abs((a - c + math.pi) % (2 * math.pi) - math.pi)
                f += 0.16 * max(0.0, w) * max(0.0, 1 - d / 0.45)
        return f
    torso = body(REG['torso'], [(HIP - 0.1, 1.2, 0.95, 0, 0.05), (HIP + 0.4, 1.3, 1.0, 0, 0.05), (WAIST, 0.95, 0.75, 0, 0.0),
                                (CHEST - 0.4, 1.08, 0.8, 0, -0.02), (CHEST, 1.18, 0.86, 0, -0.04), (CHEST + 0.5, 1.15, 0.8, 0, 0.0),
                                (NECK - 0.3, 1.05, 0.7, 0, 0.05), (NECK, 0.4, 0.38, 0, 0.05), (CHIN + 0.1, 0.36, 0.34, 0, 0.08)],
                 N=28, rmod=bust, start=True, end=True)
    pivot = (0, 0, WAIST)
    lean_it = lambda part: (setattr(part, 'p', [_turn(q, pivot, 1, lean) for q in part.p]) or part)
    out.append(('torso', lean_it(torso)))
    # the head: a nose and a chin, hair's fullness at the back and top
    def face(a, z):
        f = 1.0
        d = abs((a + math.pi / 2 + math.pi) % (2 * math.pi) - math.pi)          # (0 straight ahead, -y)
        zc = (z - CHIN) / (CROWN - CHIN)
        if 0.3 < zc < 0.55:
            f += 0.09 * max(0.0, 1 - d / 0.22) * (1 - abs(zc - 0.42) / 0.13)    # (the nose)
        if d > math.pi / 2 or zc > 0.75:
            f += 0.1 * min(1.0, (d - math.pi / 2) / 0.6 if d > math.pi / 2 else 0) + 0.06 * max(0.0, (zc - 0.75) / 0.25)
        return f
    head = body(REG['head'], [(CHIN, 0.3, 0.3, 0, 0.0), (CHIN + 0.3, 0.75, 0.78, 0, 0.0), (CHIN + 0.8, 1.02, 1.05, 0, 0.05),
                              (CHIN + 1.4, 1.12, 1.15, 0, 0.1), (CHIN + 1.95, 1.08, 1.12, 0, 0.12), (CROWN - 0.15, 0.62, 0.68, 0, 0.15)],
                N=32, rmod=face, start=True, end=(0, 0.15, CROWN))
    out.append(('head', lean_it(head)))
    # long hair down her back: a flattened tube from the crown to below the shoulders
    path = [(0, 0.55, CROWN - 0.4), (0, 1.05, CHIN + 1.2), (0, 1.0, CHIN - 0.2), (0, 0.85, NECK - 0.9), (0, 0.75, CHEST + 0.1)]
    hair = sweep(REG['hair'], path, [0.95, 1.0, 0.9, 0.8, 0.65], N=14, flat=0.5)
    out.append(('hair', lean_it(hair)))
    # the lei: a ring of blossoms round her shoulders
    lei = []
    for k in range(40):
        a = 2 * math.pi * k / 40
        lei.append((1.0 * math.cos(a), 0.05 + 0.78 * math.sin(a) - 0.12 * max(0, -math.sin(a)), NECK - 0.25 - 0.35 * max(0, -math.sin(a))))
    radii = [0.24 + 0.07 * abs(math.sin(k * math.pi / 2)) for k in range(40)]
    out.append(('lei', lean_it(sweep(REG['lei'], lei, radii, N=8, closed=True))))
    # arms: shoulder, elbow, wrist, hand; each out from hanging by its angle, forearms bent toward the front
    for side, ang in ((-1, al), (1, ar)):
        sh = (side * 1.18, 0.05, NECK - 0.45)
        up_len, lo_len = 1.9, 1.7
        a = math.radians(ang)
        elbow = (sh[0] + side * up_len * math.sin(a), sh[1] - 0.15, sh[2] - up_len * math.cos(a))
        b = a + math.radians(35)
        wrist = (elbow[0] + side * lo_len * math.sin(b) * 0.9, elbow[1] - 0.55, elbow[2] - lo_len * math.cos(b))
        hand = _add(wrist, _norm(_sub(wrist, elbow)), 0.55)
        path = [sh, _add(sh, _sub(elbow, sh), 0.5), elbow, _add(elbow, _sub(wrist, elbow), 0.5), wrist, hand]
        out.append(('skin', lean_it(sweep(REG['skin'], path, [0.36, 0.3, 0.25, 0.22, 0.18, 0.2], N=12))))
    # the flower over her right ear: five petals round a middle
    ear = (1.05, 0.1, CHIN + 1.55)
    for k in range(5):
        a = 2 * math.pi * k / 5
        c = _add(ear, (0.0, 0.32 * math.cos(a), 0.32 * math.sin(a)))
        pet = body(REG['flower'], [(-0.04, 0.3, 0.2, 0, 0), (0.03, 0.32, 0.22, 0, 0)], N=10, start=(0, 0, -0.1), end=(0, 0, 0.1))
        pet.p = [_add(c, _turn(_turn(q, (0, 0, 0), 1, 90), (0, 0, 0), 0, math.degrees(a) - 90)) for q in pet.p]
        out.append(('flower', lean_it(pet)))
    mid = body(REG['flower'], [(-0.06, 0.13, 0.13, 0, 0), (0.06, 0.13, 0.13, 0, 0)], N=8, start=(0, 0, -0.15), end=(0, 0, 0.15))
    mid.p = [_add(_add(ear, (0.08, 0, 0)), _turn(q, (0, 0, 0), 1, 90)) for q in mid.p]
    out.append(('flower', lean_it(mid)))
    return out


def _dot(c, x, y, r, colour, h=0.6, soft=1.0):
    for yy in range(int(y - r - 2), int(y + r + 3)):
        for xx in range(int(x - r - 2), int(x + r + 3)):
            if 0 <= xx < c.w and 0 <= yy < c.h:
                d = math.hypot(xx - x, yy - y)
                k = max(0.0, min(1.0, r - d + soft))
                if k > 0:
                    i = yy * c.w + xx
                    c.rgb[i] = tp._mix(c.rgb[i], colour, k)
                    c.ht[i] = c.ht[i] * (1 - k) + h * k


def _oval(c, x, y, rx, ry, colour, h=0.5):
    for yy in range(int(y - ry - 2), int(y + ry + 3)):
        for xx in range(int(x - rx - 2), int(x + rx + 3)):
            if 0 <= xx < c.w and 0 <= yy < c.h:
                d = math.hypot((xx - x) / rx, (yy - y) / ry)
                k = max(0.0, min(1.0, (1 - d) * min(rx, ry) + 0.5))
                if k > 0:
                    i = yy * c.w + xx
                    c.rgb[i] = tp._mix(c.rgb[i], colour, k)
                    c.ht[i] = c.ht[i] * (1 - k) + h * k


def doll_sheet(skirt, top, flower):
    """The doll's picture: skin, face, body and top, skirt strands, hair, lei, petals, the spring's chrome, the base."""
    c = tp.Canvas(SHEET, SHEET)
    n = tp.Noise(77, 16)
    fine = tp.Noise(78, 64)

    def region(name, fn):
        x0, y0, x1, y1 = REG[name]
        c.rect(x0, y0, x1, y1, lambda x, y, col, h: fn((x - x0) / (x1 - x0), (y - y0) / (y1 - y0), x, y))
    skin = lambda x, y: tp._shade(SKIN, 0.95 + 0.08 * n.at(x / 40.0, y / 40.0))
    region('skin', lambda u, v, x, y: (skin(x, y), 0.5))
    # the head: hair over the back and top, the face in front (u 0.75 is straight ahead)
    def head(u, v, x, y):
        d = abs(u - 0.75)
        hair_line = 0.30 + 0.18 * min(1.0, d / 0.2) ** 2           # (v from the top: hair above this)
        if d > 0.32 or v < hair_line:
            s = 0.75 + 0.45 * abs(math.sin(u * 160 + 3 * n.at(u * 8, v * 4)))
            return tp._shade(HAIR, s), 0.45 + 0.15 * s
        col = skin(x, y)
        return col, 0.5
    region('head', head)
    x0, y0, x1, y1 = REG['head']
    W, H = x1 - x0, y1 - y0
    fx = x0 + 0.75 * W
    for side in (-1, 1):
        ex, ey = fx + side * 0.06 * W, y0 + 0.47 * H
        _oval(c, ex, ey, 8.5, 8.5, (250, 248, 240), 0.45)                     # (the white: a doll's big round eye)
        _oval(c, ex + side * 0.5, ey + 0.8, 6, 7, (78, 50, 30), 0.42)          # (the iris)
        _dot(c, ex + side * 0.5, ey + 1.0, 3.2, (14, 10, 10), 0.4)
        _dot(c, ex - 2.2, ey - 2.2, 1.8, (255, 255, 255), 0.45)               # (the shine)
        for k in range(5):                                                     # (lashes over the lid)
            a = math.pi * (0.15 + 0.7 * k / 4)
            c.line((ex - 8.5 * math.cos(a), ey - 8.5 * math.sin(a)), (ex - 11.5 * math.cos(a) * 1.05, ey - 11.5 * math.sin(a)), 1.4, (24, 16, 12))
        c.line((ex - 9, ey - 8), (ex + 9, ey - 8.5), 2.0, (24, 16, 12))      # (the lid's line)
        c.line((ex - 8, ey - 18), (ex + 7, ey - 20), 2.4, (44, 28, 20))       # (the brow, raised)
        _oval(c, ex + side * 4, ey + 15, 8, 5, tp._mix(SKIN, (230, 110, 110), 0.45), 0.5)   # (cheek)
    mx, my = fx, y0 + 0.74 * H
    _oval(c, mx, my, 5.5, 2.6, (196, 52, 60), 0.52)                           # (the mouth, smiling)
    c.line((mx - 7, my - 1), (mx, my + 1.5), 1.4, (150, 30, 40))
    c.line((mx, my + 1.5), (mx + 7, my - 1), 1.4, (150, 30, 40))
    # the body: skin, her navel, the top's two cups and band in her colour, a printed flower
    def torso(u, v, x, y):
        col, h = skin(x, y), 0.5
        t = (1 - v) * (len(TORSO_Z) - 1)                                       # (rings evenly in the picture)
        k = min(int(t), len(TORSO_Z) - 2)
        z = TORSO_Z[k] + (TORSO_Z[k + 1] - TORSO_Z[k]) * (t - k)
        if CHEST - 0.55 < z < CHEST + 0.4:
            d = abs(u - 0.75)
            band = abs(z - (CHEST - 0.35)) < 0.12
            cup = any(abs(u - cu) < 0.075 * (1 - abs(z - CHEST) / 0.6) for cu in (0.695, 0.805))
            strap = abs(z - (CHEST - 0.35)) < 0.09 or (d > 0.2 and abs(z - (CHEST + 0.05)) < 0.06)
            if cup or band or strap:
                k = 0.9 + 0.12 * fine.at(x / 6.0, y / 6.0)
                col, h = tp._shade(top, k), 0.6
        return col, h
    region('torso', torso)
    x0, y0, x1, y1 = REG['torso']
    _dot(c, x0 + 0.75 * (x1 - x0), y0 + (1 - 2.0 / (len(TORSO_Z) - 1)) * (y1 - y0) + 4, 2.0, tp._shade(SKIN, 0.7), 0.4)     # (the navel, at the waist)
    # the skirt: strands, each its own straw tone, gaps between darker
    def skirt_px(u, v, x, y):
        k = u * 180
        strand = abs(math.sin(k * math.pi))
        tone = 0.82 + 0.22 * fine.at(int(k) * 0.37, 0.5) + 0.06 * n.at(x / 12.0, y / 30.0)
        col = tp._shade(skirt, tone * (0.6 + 0.4 * strand))
        if v < 0.12:                                                            # (the waistband)
            col = tp._shade(tp._mix(skirt, (120, 80, 40), 0.5), 0.85 + 0.15 * abs(math.sin(u * 300)))
            return col, 0.55
        return col, 0.35 + 0.3 * strand
    region('skirt', skirt_px)
    region('hair', lambda u, v, x, y: (tp._shade(HAIR, 0.7 + 0.5 * abs(math.sin(u * 120 + 2 * n.at(u * 3, v * 6)))), 0.4 + 0.2 * abs(math.sin(u * 120))))
    # the lei: blossoms in two tones of her flower's colour with leaves between
    def lei_px(u, v, x, y):
        cell = (u * 40) % 1.0
        petal = abs(math.sin(cell * math.pi * 5 + v * 9))
        col = tp._shade(flower if int(u * 40) % 2 == 0 else tp._mix(flower, (255, 255, 255), 0.35), 0.75 + 0.3 * petal)
        if cell < 0.12:
            col = (60, 120, 50)
        return col, 0.4 + 0.3 * petal
    region('lei', lei_px)
    region('flower', lambda u, v, x, y: (tp._shade(flower, 0.8 + 0.25 * abs(math.sin(v * 12))) if v > 0.2 else (240, 200, 60), 0.5))
    region('spring', lambda u, v, x, y: (tp._shade((200, 204, 210), 0.7 + 0.4 * abs(math.sin(v * 20))), 0.5))
    # the base: lacquered red-brown wood, a gold band with HAWAII round it
    def base_px(u, v, x, y):
        grain = 0.85 + 0.15 * math.sin(x / 3.0 + 6 * n.at(x / 60.0, y / 9.0))
        if 0.35 < v < 0.7:
            return tp._shade((206, 168, 74), 0.9 + 0.1 * fine.at(x / 5.0, y / 5.0)), 0.55
        return tp._shade((116, 52, 34), grain), 0.5
    region('base', base_px)
    region('basetop', lambda u, v, x, y: ((tp._shade((206, 168, 74), 0.95) if 0.08 < v < 0.2 else
                                           tp._shade((116, 52, 34), 0.85 + 0.15 * math.sin(x / 3.0))), 0.55 if 0.08 < v < 0.2 else 0.5))
    x0, y0, x1, y1 = REG['base']
    for rep in range(4):                                                       # (round the side, four times)
        tx = x0 + rep * 128 + 30
        c.text('HAWAII', tx, y0 + 0.37 * (y1 - y0), 0.3 * (y1 - y0), (90, 40, 26), thick=2.4)
    return c


def doll_shapes(stat, pose, skirt, top, flower):
    parts = doll_parts(pose)
    tex = TEX % ('hula_' + stat.lower())
    shapes = [P.shape(tex, gloss=30.0) for _n, P in parts]
    merged = {'p': [], 'n': [], 'uv': [], 'i': [], 'tex': tex, 'normal': tex[:-4] + '_n.dds', 'gloss': 30.0, 'alpha': 0, 'glow': '', 'glow_mult': 1.0}
    for s in shapes:
        base = len(merged['p']) // 3
        for k in ('p', 'n', 'uv'):
            merged[k] += s[k]
        merged['i'] += [i + base for i in s['i']]
    pic = doll_sheet(skirt, top, flower)
    return [merged], {tex: pic.files(game=True, shine=70)}


# ---------- the jade charms ----------
def _ray(poly):
    """outer(angle) of a polygon round the origin (star-shaped): where a ray from the middle leaves it."""
    def outer(a):
        dx, dy = math.cos(a), math.sin(a)
        best = 0.0
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            ex, ey = x2 - x1, y2 - y1
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = (x1 * ey - y1 * ex) / den
            u = (x1 * dy - y1 * dx) / den
            if t > 0 and 0 <= u <= 1:
                best = max(best, t)
        return best
    return outer


def _blob(x, y, cx, cy, rx, ry):
    d = math.hypot((x - cx) / rx, (y - cy) / ry)
    return max(0.0, 1 - d)


CARVE = {}


def _outline(kind):
    """outer(angle), inner(angle) or None, and the carving's heights relief(x, y) -> 0-1, in the charm's units (y along it)."""
    if kind == 'bi':
        outer = lambda a: 1.9
        inner = lambda a: 0.55

        def relief(x, y):
            r = math.hypot(x, y)
            if r < 0.75 or r > 1.7:
                return 0.15 if abs(r - 1.72) < 0.05 or abs(r - 0.72) < 0.05 else 0.0
            # (raised grain: little round bosses in rows round the ring)
            k = round((r - 0.85) / 0.22)
            rr = 0.85 + 0.22 * k
            n = max(6, int(2 * math.pi * rr / 0.24))
            a = math.atan2(y, x) + (0.5 if k % 2 else 0.0) * 2 * math.pi / n
            aa = round(a / (2 * math.pi / n)) * 2 * math.pi / n
            d = math.hypot(x - rr * math.cos(aa), y - rr * math.sin(aa))
            return max(0.0, 1 - d / 0.09) ** 0.6
        return outer, inner, relief
    if kind == 'gourd':
        # (two lobes along y, the small one at -y where it hangs, eased into each other at the waist)
        def width(y):
            ws = [math.sqrt(max(0.0, r * r - (y - cy) ** 2)) for cy, r in ((0.55, 1.3), (-1.15, 0.85))]
            return math.log(sum(math.exp(WAIST_EASE * w) for w in ws)) / WAIST_EASE
        ys = [-2.0 + 3.85 * k / 60 for k in range(61)]
        right = [(max(0.02, width(y)), y) for y in ys]
        poly = [(0.0, -2.0)] + right[1:-1] + [(0.0, 1.85)] + [(-x, y) for x, y in reversed(right[1:-1])]
        outer = _ray(poly)

        def relief(x, y):
            # (a leaf over the big lobe with its midrib and veins, a vine from the waist curling round, the lobes' rims)
            v = 0.0
            lx, ly = x - 0.25, y - 0.65
            ca, sa = math.cos(0.6), math.sin(0.6)
            u, w = lx * ca + ly * sa, -lx * sa + ly * ca                 # (the leaf's own axes: u along it)
            if abs(u) < 0.75:
                half = 0.38 * math.sin(math.pi * (u + 0.75) / 1.5) ** 0.8
                if abs(w) < half:
                    v = 0.55 + 0.25 * (1 - abs(w) / half)
                    if abs(w) < 0.025 or (abs(abs(w) - 0.6 * (u + 0.75) % 0.3) < 0.02 and abs(w) < half * 0.8):
                        v -= 0.35
            t = math.atan2(y + 0.25, x + 0.1)
            r = math.hypot(x + 0.1, y + 0.25)
            spiral = abs(r - (0.12 + 0.07 * ((t + math.pi) % (2 * math.pi))))
            if r < 0.6 and spiral < 0.04:
                v = max(v, 0.7)
            vine = abs(y + 0.3 - 0.18 * math.sin(x * 4.0))
            if vine < 0.05 and x < -0.1:
                v = max(v, 0.65)
            return v
        return outer, None, relief
    if kind == 'fish':
        def outer(a):
            ca, sa = math.cos(a), math.sin(a)
            # (a carp along y, head at -y: a body ellipse, a tail fan at +y, fins)
            r = 1.0 / math.sqrt((ca / 0.95) ** 2 + (sa / 1.75) ** 2)
            if sa > 0.85:
                r = max(r, 2.25 + 0.35 * math.cos(6 * a))
            if abs(ca) > 0.9:
                r = max(r, 1.15)
            return r

        def relief(x, y):
            v = 0.0
            if y < 1.6:
                # (scales: overlapping arcs in rows)
                row = math.floor((y + 1.2) / 0.28)
                off = 0.14 if row % 2 else 0.0
                cx = round((x - off) / 0.28) * 0.28 + off
                cy = -1.2 + row * 0.28
                d = math.hypot(x - cx, y - cy)
                if y > -0.9:
                    v = 0.55 * (1 - min(1.0, abs(d - 0.16) / 0.04)) if d < 0.22 and y > cy else 0.35
                else:
                    v = 0.25
            if y > 1.6:
                v = 0.3 + 0.3 * abs(math.sin(math.atan2(x, y - 1.4) * 9))           # (the tail's rays)
            v -= 0.4 * max(0.0, 1 - abs(y + 0.85 - 0.05 * x * x) / 0.04)           # (the gill line)
            for ex in (-0.42, 0.42):
                v = max(v, 0.9 * max(0.0, 1 - math.hypot(x - ex, y + 1.3) / 0.13))   # (the eyes)
            return max(0.0, v)
        return outer, None, relief
    if kind == 'cicada':
        # (its outline: head across the top (-y), the eyes at its corners, shoulders, the wings swept to a point at +y)
        poly = [(0.0, -2.0), (0.45, -1.98), (0.78, -1.82), (0.86, -1.55), (0.95, -1.25), (1.12, -0.9), (1.08, -0.2), (0.9, 0.6),
                (0.62, 1.4), (0.3, 2.05), (0.0, 2.25)]
        poly = poly + [(-x, y) for x, y in reversed(poly[1:-1])]
        outer = _ray(poly)

        def relief(x, y):
            ax = abs(x)
            v = 0.35
            if y < -1.3:                                            # (the head: a band across, two bulging eyes)
                v = 0.55
                v = max(v, 0.95 * max(0.0, 1 - math.hypot(ax - 0.55, y + 1.62) / 0.24) ** 0.6)
                if abs(y + 1.3) < 0.04:
                    v = 0.1
                if abs(y + 1.75) < 0.03 and ax < 0.35:
                    v = 0.25
            else:
                # (the wings: each a long blade from the shoulder toward the tip, their inner edges meeting in a V)
                edge = ax - 0.55 * (1 - (y + 1.3) / 3.5)
                if edge > 0:
                    v = 0.6 - 0.25 * min(1.0, edge / 0.5)
                    if abs(edge - 0.06) < 0.03:
                        v = 0.15                                    # (the wing's inner line)
                    if abs((ax - 0.2) - 0.35 * (1 - (y + 1.3) / 3.5)) < 0.025:
                        v = 0.2                                     # (a vein along it)
                else:
                    v = 0.45 + 0.3 * (abs(math.sin((y + 1.3) * 7.5)) > 0.35)    # (the body's bands between)
            return v
        return outer, None, relief
    # coin: a round with a square hole, a raised rim and four characters
    outer = lambda a: 1.75

    def inner(a):
        return 0.42 / max(abs(math.cos(a)), abs(math.sin(a)))

    def relief(x, y):
        r = math.hypot(x, y)
        if r > 1.5:
            return 0.8
        if max(abs(x), abs(y)) < 0.55:
            return 0.8
        v = 0.0
        for (cx, cy) in ((0, -1.0), (0, 1.0), (-1.0, 0), (1.0, 0)):
            if abs(x - cx) < 0.32 and abs(y - cy) < 0.32:
                gx, gy = (x - cx) / 0.32, (y - cy) / 0.32
                strokes = (abs(gy + 0.6) < 0.14 or abs(gy) < 0.14 or abs(gy - 0.6) < 0.14 or abs(gx) < 0.14 if (cx + cy) > 0
                           else abs(gx + 0.6) < 0.14 or abs(gx - 0.6) < 0.14 or abs(gy + 0.6) < 0.14 or abs(gy - 0.6) < 0.14 or abs(gy) < 0.12)
                v = 0.75 if strokes else 0.0
        return v
    return outer, inner, relief


GEO_CARVE = {'bi': 0.0, 'gourd': 0.14, 'fish': 0.05, 'cicada': 0.1, 'coin': 0.1}     # (how much of the carving is in the shape itself)
WAIST_EASE = 5.0     # (how softly the gourd's lobes run into each other: a deep waist folds its rounded rim)
EXTENT = 2.6        # (the charm's planar picture covers -EXTENT to EXTENT each way)


def charm_parts(kind):
    outer, inner, relief = _outline(kind)
    planar = lambda q: ((q[0] / EXTENT + 1) / 2 * 0.75, (1 - (q[1] / EXTENT + 1) / 2))      # (the left three quarters)
    soft = lambda x, y: sum(relief(x + dx, y + dy) for dx, dy in ((0, 0), (0.07, 0), (-0.07, 0), (0, 0.07), (0, -0.07))) / 5    # (the shape's
    jade = pillow(None, outer, inner, 0.55 if kind != 'bi' else 0.45, soft, N=96, steps=10, planar=planar, rim=GEO_CARVE[kind])   # carving softened)
    # where it hangs from: the far end along -y (a gourd's or fish's head), the bail and cord beyond
    top_y = -max(outer(-math.pi / 2), 0.5)
    bail = body((384, 0, 448, 64), [(-0.3, 0.2, 0.2, 0, 0), (-0.22, 0.26, 0.26, 0, 0), (0.22, 0.26, 0.26, 0, 0), (0.3, 0.2, 0.2, 0, 0)],
                N=16, start=(0, 0, -0.34), end=(0, 0, 0.34))
    bail.p = [(q[0], -q[2] + top_y - 0.2, q[1]) for q in bail.p]          # (turned a quarter about x: along y)
    # the cord: a loop through the bail, its two strands knotted
    loop = []
    for k in range(36):
        a = 2 * math.pi * k / 36
        loop.append((0.55 * math.sin(a) * (1 + 0.15 * math.cos(a)), top_y - 0.75 - 0.75 * (1 - math.cos(a)), 0.18 * math.sin(2 * a)))
    cord = sweep((448, 0, 512, 512), loop, [0.11] * 36, N=8, closed=True)
    knot = body((448, 0, 512, 512), [(-0.15, 0.22, 0.2, 0, 0), (0.15, 0.22, 0.2, 0, 0)], N=12, start=(0, 0, -0.27), end=(0, 0, 0.27))
    knot.p = [(q[0], -q[2] + top_y - 0.75, q[1]) for q in knot.p]
    parts = [('jade', jade), ('gold', bail), ('cord', cord), ('cord', knot)]
    for _n, P in parts:                 # (turned half round and a little smaller: the cord toward +y, in the old charm's room)
        P.p = [(-q[0] * CHARM_SCALE, -q[1] * CHARM_SCALE, q[2] * CHARM_SCALE) for q in P.p]
    return parts


CHARM_SCALE = 0.85


def charm_sheet(kind, colour):
    """The charm's picture: the carving seen from above over the left three quarters (polished jade, clouded and
    veined, the carving's heights in its relief), gold for the bail, red silk twisted for the cord."""
    outer, inner, relief = _outline(kind)
    c = tp.Canvas(SHEET, SHEET)
    cloud = tp.Noise(sum(map(ord, kind)) + int(sum(colour)), 6)
    vein = tp.Noise(sum(map(ord, kind)) + 5, 24)
    W = int(SHEET * 0.75)

    def px(x, y, col, h):
        X = (x / W * 2 - 1) * EXTENT
        Y = (1 - y / SHEET * 2) * EXTENT
        X, Y = X, -Y
        rv = relief(X, -Y) if relief else 0.0
        cl = cloud.at(X * 1.2 + 3, Y * 1.2 + 3)
        col = tp._mix(colour, (236, 244, 230), 0.22 * max(0.0, cl - 0.35))
        col = tp._mix(col, tp._shade(colour, 0.55), 0.2 * max(0.0, 0.5 - cl))
        if abs(vein.at(X * 1.6, Y * 1.6) - 0.5) < 0.005:
            col = tp._mix(col, (232, 236, 214), 0.18)
        col = tp._shade(col, 0.88 + 0.22 * rv)              # (the raised work catches more light; the cut lines hold shade)
        return col, 0.3 + 0.5 * rv
    c.rect(0, 0, W, SHEET, px)
    c.rect(W, 0, W + 64, 64, lambda x, y, col, h: (tp._shade((212, 170, 70), 0.85 + 0.25 * abs(math.sin(y / 3.0))), 0.5))
    c.rect(448, 0, 512, 512, lambda x, y, col, h: (tp._shade((176, 28, 34), 0.7 + 0.35 * abs(math.sin((x * 0.6 + y * 0.9) / 2.2))),
                                                   0.35 + 0.3 * abs(math.sin((x * 0.6 + y * 0.9) / 2.2))))
    return c


def charm_shapes(skill, kind, colour):
    tex = TEX % ('jade_' + skill.lower())
    parts = charm_parts(kind)
    merged = {'p': [], 'n': [], 'uv': [], 'i': [], 'tex': tex, 'normal': tex[:-4] + '_n.dds', 'gloss': 80.0, 'alpha': 0, 'glow': '', 'glow_mult': 1.0}
    for _n, P in parts:
        s = P.shape(tex, 80.0)
        base = len(merged['p']) // 3
        for k in ('p', 'n', 'uv'):
            merged[k] += s[k]
        merged['i'] += [i + base for i in s['i']]
    pic = charm_sheet(kind, colour)
    return [merged], {tex: pic.files(game=True, shine=120)}
