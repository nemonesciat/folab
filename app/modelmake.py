"""Models put together from simple parts, by description: boxes (a slab is a flat box), cylinders, cones.

A description is plain data, so a piece can be kept as JSON:

  {'name': 'FOLabBeachUmbrella',
   'looks': {'pole': {'tex': 'textures\\...\\pole.dds', 'normal': '..._n.dds', 'tile': 64},
             'sign': {'tex': ..., 'normal': ..., 'region': [0, 0, 1, 0.5]}},
   'parts': [{'shape': 'box', 'size': [x, y, z], 'at': [x, y, z], 'turn': [0, 0, 30], 'look': 'pole',
              'faces': {'front': 'sign'}, 'solid': True, 'material': 'wood'},
             {'shape': 'cylinder', 'r': 3, 'r2': 3, 'h': 150, 'sides': 10, ...},
             {'shape': 'cone', 'r': 110, 'h': 40, 'under': True, 'paint': 'above', ...}]}

Growing things: 'card' (a flat upright picture seen from both sides), 'frond' (a long leaf that bends over), 'ball';
a look with 'alpha': True is see-through where its picture is (leaves).

A part is made standing on its own origin (the middle of its underside), z up, its front towards -y; then stretched by
'scale', turned by 'turn' (degrees about x, then y, then z) and moved to 'at'. Game units: 70 to the metre.

A look is a texture and how it lies on a face. 'tile': the picture repeats every so many units (planks, cloth), and
'turned' lays it on its side. Without 'tile' the picture, or its 'region' (u0, v0, u1, v1: left, top, right, bottom),
is fitted to each face once: a sign. A part's 'paint': 'above' lays the picture on it as seen from over it, whatever
the face (a parasol's canopy). Each look becomes one shape of the mesh; each solid part one convex piece of collision
(`nifmake`). `make` returns the mesh's bytes with what went into it."""
import math

import nifmake

BOX_FACES = ('front', 'back', 'left', 'right', 'top', 'bottom')


def _rot(turn):
    rx, ry, rz = (math.radians(a) for a in turn)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    # about x first, then y, then z
    return ((cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
            (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
            (-sy, cy * sx, cy * cx))


class _Place:
    """Where a part goes: its points and normals from its own frame into the model's."""

    def __init__(self, part):
        self.s = [float(v) for v in part.get('scale', (1, 1, 1))]
        self.R = _rot(part.get('turn', (0, 0, 0)))
        self.t = [float(v) for v in part.get('at', (0, 0, 0))]

    def point(self, p):
        q = (p[0] * self.s[0], p[1] * self.s[1], p[2] * self.s[2])
        R = self.R
        return tuple(self.t[i] + R[i][0] * q[0] + R[i][1] * q[1] + R[i][2] * q[2] for i in range(3))

    def normal(self, n):
        q = (n[0] / self.s[0], n[1] / self.s[1], n[2] / self.s[2])      # (a stretched surface's normal leans the other way)
        ln = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2]) or 1.0
        R = self.R
        return tuple((R[i][0] * q[0] + R[i][1] * q[1] + R[i][2] * q[2]) / ln for i in range(3))


class _Mesh:
    """The faces of every part so far, gathered by look."""

    def __init__(self, looks):
        self.looks = looks
        self.by_look = {}
        self.solids = []

    def face(self, look, corners):
        """A flat or curved face as a fan: corners [(point, normal, (u, v))], anticlockwise seen from outside."""
        if look not in self.looks:
            raise nifmake.MakeError('no look called %r' % (look,))
        s = self.by_look.setdefault(look, {'p': [], 'n': [], 'uv': [], 'i': []})
        base = len(s['p']) // 3
        for p, n, uv in corners:
            s['p'] += p
            s['n'] += n
            s['uv'] += uv
        for k in range(1, len(corners) - 1):
            s['i'] += (base, base + k, base + k + 1)


def _lay(look, u, v, across, down):
    """Texture coordinates of a point u across and v down a face that is `across` by `down` units (v from its top)."""
    if look.get('tile'):
        t = float(look['tile'])
        a, b = u / t, v / t
        return (b, a) if look.get('turned') else (a, b)
    u0, v0, u1, v1 = look.get('region', (0.0, 0.0, 1.0, 1.0))
    a, b = (u / across if across else 0.0), (v / down if down else 0.0)
    if look.get('turned'):
        a, b = b, 1.0 - a
    return (u0 + (u1 - u0) * a, v0 + (v1 - v0) * b)


def _above(look, p, reach):
    """The picture laid on from over the part: its middle at the part's axis, its edge `reach` out."""
    u0, v0, u1, v1 = look.get('region', (0.0, 0.0, 1.0, 1.0))
    return (u0 + (u1 - u0) * (p[0] / reach + 1) / 2, v0 + (v1 - v0) * (1 - p[1] / reach) / 2)


def _box(mesh, part, place):
    x, y, z = (float(v) for v in part['size'])
    hx, hy = x / 2, y / 2
    pts = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)]
    # each face: its corners from top left, anticlockwise seen from outside; its normal; its width and height
    faces = {'front': ((4, 0, 1, 5), (0, -1, 0), x, z), 'back': ((6, 2, 3, 7), (0, 1, 0), x, z),
             'left': ((7, 3, 0, 4), (-1, 0, 0), y, z), 'right': ((5, 1, 2, 6), (1, 0, 0), y, z),
             'top': ((7, 4, 5, 6), (0, 0, 1), x, y), 'bottom': ((0, 3, 2, 1), (0, 0, -1), x, y)}
    own = part.get('faces', {})
    reach = max(hx, hy)
    for name in BOX_FACES:
        look_name = own.get(name, part.get('look'))
        if look_name is None:
            continue                            # (a face nobody sees, left out)
        idx, nm, w, h = faces[name]
        look = mesh.looks.get(look_name) or {}
        n = place.normal(nm)
        where = ((0, 0), (0, h), (w, h), (w, 0))
        mesh.face(look_name, [(place.point(pts[i]), n, _above(look, pts[i], reach) if part.get('paint') == 'above' else _lay(look, u, v, w, h))
                              for i, (u, v) in zip(idx, where)])
    if part.get('solid', True):
        mesh.solids.append({'points': [place.point(p) for p in pts], 'material': part.get('material', 'wood'),
                            'faces': [list(faces[n][0]) for n in BOX_FACES]})


def _round(mesh, part, place):
    """A cylinder, or with another radius at the top a cone or a part of one. 'caps': False leaves the ends open;
    'under': True gives the side an inside too (cloth)."""
    r = float(part['r'])
    r2 = 0.0 if part['shape'] == 'cone' and 'r2' not in part else float(part.get('r2', r))
    h = float(part['h'])
    n = max(3, int(part.get('sides', 12)))
    look_name = part.get('look')
    look = mesh.looks.get(look_name) or {}
    above = part.get('paint') == 'above'
    reach = max(r, r2)
    ring = lambda rad, z: [(rad * math.cos(2 * math.pi * k / n), rad * math.sin(2 * math.pi * k / n), z) for k in range(n + 1)]
    lo, hi = ring(r, 0.0), ring(r2, h)
    slant = math.hypot(h, r - r2)
    around = 2 * math.pi * reach
    if look.get('tile'):
        around = max(1, round(around / look['tile'])) * look['tile']     # (a whole number of repeats: no seam)
    side_n = lambda k: (h * math.cos(2 * math.pi * k / n), h * math.sin(2 * math.pi * k / n), r - r2)
    uv = lambda p, k, down: _above(look, p, reach) if above else _lay(look, around * k / n, down, around, slant)
    if look_name is not None:
        for k in range(n):
            quad = [(hi[k], side_n(k), uv(hi[k], k, 0)), (lo[k], side_n(k), uv(lo[k], k, slant)),
                    (lo[k + 1], side_n(k + 1), uv(lo[k + 1], k + 1, slant)), (hi[k + 1], side_n(k + 1), uv(hi[k + 1], k + 1, 0))]
            if r2 == 0:                         # (a cone's tip: one corner, facing out between the two edges)
                quad = [(hi[k], side_n(k + 0.5), uv(hi[k], k + 0.5, 0))] + quad[1:3]
            elif r == 0:
                quad = [quad[0], (lo[k], side_n(k + 0.5), uv(lo[k], k + 0.5, slant)), quad[3]]
            mesh.face(look_name, [(place.point(p), place.normal(nm), t) for p, nm, t in quad])
            if part.get('under'):
                mesh.face(part.get('under_look', look_name), _other_side([(place.point(p), place.normal(nm), t) for p, nm, t in quad]))
    cap_look = part.get('cap_look', look_name)
    if part.get('caps', True) and cap_look is not None:
        cl = mesh.looks.get(cap_look) or {}
        flat = lambda p: _above(cl, p, reach) if not cl.get('tile') else _lay(cl, p[0], -p[1], 1, 1)
        if r2 > 0:
            mesh.face(cap_look, [(place.point(p), place.normal((0, 0, 1)), flat(p)) for p in hi[:n]])
        if r > 0 and not part.get('under'):
            mesh.face(cap_look, [(place.point(p), place.normal((0, 0, -1)), flat(p)) for p in reversed(lo[:n])])
    if part.get('solid', True):
        pts, faces = [], []
        bottom = list(range(n)) if r > 0 else [0]
        pts += lo[:n] if r > 0 else [lo[0]]
        top = list(range(len(pts), len(pts) + n)) if r2 > 0 else [len(pts)]
        pts += hi[:n] if r2 > 0 else [hi[0]]
        for k in range(n):
            j = (k + 1) % n
            f = [top[k % len(top)], bottom[k % len(bottom)], bottom[j % len(bottom)], top[j % len(top)]]
            faces.append([c for i, c in enumerate(f) if c not in f[:i]])
        if r2 > 0:
            faces.append(top)
        if r > 0:
            faces.append(bottom[::-1])
        mesh.solids.append({'points': [place.point(p) for p in pts], 'faces': faces, 'material': part.get('material', 'wood')})


def _two_sides(mesh, look_name, corners):
    """A face seen from both sides: the same corners again the other way round, facing the other way."""
    mesh.face(look_name, corners)
    mesh.face(look_name, _other_side(corners))


def _other_side(corners):
    """The same face from behind: turned over about its first diagonal, so both sides are cut into the same triangles
    (a bent leaf's two sides would otherwise part)."""
    back = [corners[2], corners[1], corners[0]] + list(reversed(corners[3:]))
    return [(p, (-n[0], -n[1], -n[2]), t) for p, n, t in back]


def _card(mesh, part, place):
    """A flat upright picture seen from both sides, 'size' [wide, tall], facing -y: a few crossed make a bush or a
    tuft of grass. Never solid."""
    w, h = (float(v) for v in part['size'])
    look = mesh.looks.get(part.get('look')) or {}
    n = place.normal((0, -1, 0))
    pts = ((-w / 2, 0, h), (-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h))
    where = ((0, 0), (0, h), (w, h), (w, 0))
    _two_sides(mesh, part.get('look'), [(place.point(p), n, _lay(look, u, v, w, h)) for p, (u, v) in zip(pts, where)])


def _frond(mesh, part, place):
    """A long leaf growing from the part's origin towards +x: 'long' and 'wide', starting 'up' degrees above level and
    bending down by 'droop' degrees along its length, its two halves each folded down 'fold' degrees from the midrib.
    The look's picture has the leaf's stalk at the bottom middle and its tip at the top. Never solid."""
    ln, wide = float(part['long']), float(part['wide'])
    n = max(1, int(part.get('segments', 6)))
    up, droop, fold = (math.radians(float(part.get(k, d))) for k, d in (('up', 30), ('droop', 70), ('fold', 20)))
    look_name = part.get('look')
    look = mesh.looks.get(look_name) or {}
    rings = []
    x = z = 0.0
    for k in range(n + 1):
        a = up - droop * k / n
        if k:
            b = up - droop * (k - 0.5) / n
            x += math.cos(b) * ln / n
            z += math.sin(b) * ln / n
        out = (-math.sin(a), 0.0, math.cos(a))                  # straight out of the leaf's upper side here
        half = wide / 2
        edge = lambda s: (x - out[0] * half * math.sin(fold), s * half * math.cos(fold), z - out[2] * half * math.sin(fold))
        face = lambda s: (out[0] * math.cos(fold), s * math.sin(fold), out[2] * math.cos(fold))
        v = ln * (1 - k / n)                                    # (the picture's bottom is the stalk)
        rings.append({'mid': (x, 0.0, z), 'left': edge(1), 'right': edge(-1), 'nl': face(1), 'nr': face(-1), 'v': v})
    c = lambda p, nm, u, v: (place.point(p), place.normal(nm), _lay(look, u, v, wide, ln))
    for a, b in zip(rings, rings[1:]):
        _two_sides(mesh, look_name, [c(a['mid'], a['nl'], wide / 2, a['v']), c(b['mid'], b['nl'], wide / 2, b['v']),
                                     c(b['left'], b['nl'], 0, b['v']), c(a['left'], a['nl'], 0, a['v'])])
        _two_sides(mesh, look_name, [c(a['mid'], a['nr'], wide / 2, a['v']), c(a['right'], a['nr'], wide, a['v']),
                                     c(b['right'], b['nr'], wide, b['v']), c(b['mid'], b['nr'], wide / 2, b['v'])])


def _ball(mesh, part, place):
    """A ball of radius 'r' standing on the part's origin ('scale' makes it an egg or a boulder)."""
    r = float(part['r'])
    n, m = max(3, int(part.get('sides', 8))), max(2, int(part.get('rings', 5)))
    look_name = part.get('look')
    look = mesh.looks.get(look_name) or {}
    around, over = 2 * math.pi * r, math.pi * r
    if look.get('tile'):
        around = max(1, round(around / look['tile'])) * look['tile']

    def at(j, k):                                               # ring j from the top, step k round
        lat, lon = math.pi * j / m, 2 * math.pi * k / n
        nm = (math.sin(lat) * math.cos(lon), math.sin(lat) * math.sin(lon), math.cos(lat))
        return (nm[0] * r, nm[1] * r, r + nm[2] * r), nm
    pts, faces = {}, []
    for j in range(m):
        for k in range(n):
            quad = [(j, k), (j + 1, k), (j + 1, k + 1), (j, k + 1)]
            if j == 0:
                quad = quad[:3]                                 # (at the top and bottom the ring is one point)
            elif j == m - 1:
                quad = [quad[0], quad[1], quad[3]]
            corners = []
            for jj, kk in quad:
                p, nm = at(jj, kk)
                corners.append((place.point(p), place.normal(nm), _lay(look, around * kk / n, over * jj / m, around, over)))
            if look_name is not None:
                mesh.face(look_name, corners)
            ids = []
            for jj, kk in quad:
                key = (jj, 0 if jj in (0, m) else kk % n)
                if key not in pts:
                    pts[key] = (len(pts), place.point(at(*key)[0]))
                ids.append(pts[key][0])
            faces.append(ids)
    if part.get('solid', True):
        mesh.solids.append({'points': [p for _i, p in sorted(pts.values())], 'faces': faces, 'material': part.get('material', 'wood')})


_SHAPES = {'box': _box, 'slab': _box, 'cylinder': _round, 'cone': _round, 'card': _card, 'frond': _frond, 'ball': _ball}


def make(desc):
    """{'nif': the mesh's bytes, 'shapes', 'solids' (what went into it, for checking), 'box': [x1, y1, z1, x2, y2, z2],
    'triangles', 'textures'} from a description."""
    looks = desc['looks']
    mesh = _Mesh(looks)
    for part in desc['parts']:
        fn = _SHAPES.get(part.get('shape'))
        if not fn:
            raise nifmake.MakeError('no part called %r: there are %s' % (part.get('shape'), ', '.join(sorted(_SHAPES))))
        fn(mesh, part, _Place(part))
    shapes = {}
    for name, s in mesh.by_look.items():        # looks over the same pictures are one shape: one thing for the game to draw
        look = looks[name]
        kind = (look['tex'].lower(), look.get('normal', '').lower(), look.get('gloss', 10.0), bool(look.get('alpha')), look.get('glow', ''), look.get('glow_mult', 1.0))
        if kind not in shapes:
            shapes[kind] = {'p': [], 'n': [], 'uv': [], 'i': [], 'tex': look['tex'], 'normal': look.get('normal', ''), 'gloss': kind[2], 'alpha': kind[3], 'glow': kind[4], 'glow_mult': kind[5]}
        to = shapes[kind]
        base = len(to['p']) // 3
        to['p'] += s['p']
        to['n'] += s['n']
        to['uv'] += s['uv']
        to['i'] += [i + base for i in s['i']]
    shapes = list(shapes.values())
    data = nifmake.build(desc['name'], shapes, mesh.solids)
    lo = [math.floor(min(min(s['p'][a::3]) for s in shapes)) for a in range(3)]
    hi = [math.ceil(max(max(s['p'][a::3]) for s in shapes)) for a in range(3)]
    return {'nif': data, 'shapes': shapes, 'solids': mesh.solids, 'box': lo + hi,
            'triangles': sum(len(s['i']) // 3 for s in shapes),
            'textures': sorted({t for s in shapes for t in (s['tex'], s['normal']) if t})}
