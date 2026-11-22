"""Models put together from simple parts, by description: boxes (a slab is a flat box), cylinders, cones.

A description is plain data, so a piece can be kept as JSON:

  {'name': 'FOLabBeachUmbrella',
   'looks': {'pole': {'tex': 'textures\\...\\pole.dds', 'normal': '..._n.dds', 'tile': 64},
             'sign': {'tex': ..., 'normal': ..., 'region': [0, 0, 1, 0.5]}},
   'parts': [{'shape': 'box', 'size': [x, y, z], 'at': [x, y, z], 'turn': [0, 0, 30], 'look': 'pole',
              'faces': {'front': 'sign'}, 'solid': True, 'material': 'wood'},
             {'shape': 'cylinder', 'r': 3, 'r2': 3, 'h': 150, 'sides': 10, 'phase': 0, ...},
             {'shape': 'cone', 'r': 110, 'h': 40, 'under': True, 'paint': 'above', ...}]}

Growing things: 'card' (a flat upright picture seen from both sides), 'frond' (a long leaf that bends over), 'ball',
'stick' (a thin stem as crossed strips over a see-through picture, texpaint.stick: what a plant's stems are);
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
    """The faces of every part so far, gathered by look. step: faces longer than this are cut into a grid of smaller
    ones (the shade baked into the corners needs corners to hold it); bevel: 'auto', or units, for parts that don't say."""

    def __init__(self, looks, step=None, bevel=0.0):
        self.looks = looks
        self.by_look = {}
        self.solids = []
        self.step = step
        self.bevel = bevel
        self.tally = []             # (unless cutting: each solid face's edges, to say what cutting at a step would make)

    def triangles_at(self, step):
        """How many triangles the faces so far would be cut into at `step`."""
        out = 0
        for e in self.tally:
            if len(e) == 4:
                nu = min(GRID_MOST, max(1, math.ceil(max(e[3], e[1]) / step)))
                nv = min(GRID_MOST, max(1, math.ceil(max(e[0], e[2]) / step)))
                out += 2 * nu * nv
            elif e[0] > step:
                out += sum(min(GRID_MOST, max(1, math.ceil(f / step))) ** 2 for f in e[1])
            else:
                out += len(e[1])
        return out

    def face(self, look, corners):
        """A flat or curved face as a fan: corners [(point, normal, (u, v))], anticlockwise seen from outside."""
        if look not in self.looks:
            raise nifmake.MakeError('no look called %r' % (look,))
        s = self.by_look.setdefault(look, {'p': [], 'n': [], 'uv': [], 'i': []})
        step = self.step if self.step and not self.looks[look].get('alpha') else None
        if self.step is None and not self.looks[look].get('alpha'):
            edges = [math.dist(corners[k][0], corners[k - 1][0]) for k in range(len(corners))]
            if len(corners) == 4:
                self.tally.append(edges)
            else:                               # (a fan is cut a triangle at a time, by its triangles' own edges)
                fan = [max(math.dist(corners[0][0], corners[k][0]), math.dist(corners[k][0], corners[k + 1][0]),
                           math.dist(corners[k + 1][0], corners[0][0])) for k in range(1, len(corners) - 1)]
                self.tally.append((max(edges), fan))
        if step and len(corners) == 4:
            _grid(s, corners, step)
            return
        if step and any(math.dist(corners[k][0], corners[k - 1][0]) > step for k in range(len(corners))):
            for k in range(1, len(corners) - 1):
                _split(s, corners[0], corners[k], corners[k + 1], step)
            return
        base = len(s['p']) // 3
        for p, n, uv in corners:
            s['p'] += p
            s['n'] += n
            s['uv'] += uv
        for k in range(1, len(corners) - 1):
            s['i'] += (base, base + k, base + k + 1)


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _corner(a, b, c, d, s, t):
    """A point of a quad a b c d (in order round it): s along a->d, t along a->b; its normal kept a unit."""
    p = _lerp(_lerp(a[0], d[0], s), _lerp(b[0], c[0], s), t)
    n = _unit3(_lerp(_lerp(a[1], d[1], s), _lerp(b[1], c[1], s), t))
    uv = _lerp(_lerp(a[2], d[2], s), _lerp(b[2], c[2], s), t)
    return p, n, uv


GRID_MOST = 48          # (cuts across one face at most)


def _grid(s, q, step):
    """A four-cornered face as a grid of faces about `step` across, facing as it did."""
    a, b, c, d = q
    nu = min(GRID_MOST, max(1, math.ceil(max(math.dist(a[0], d[0]), math.dist(b[0], c[0])) / step)))
    nv = min(GRID_MOST, max(1, math.ceil(max(math.dist(a[0], b[0]), math.dist(d[0], c[0])) / step)))
    base = len(s['p']) // 3
    for i in range(nu + 1):
        for j in range(nv + 1):
            p, n, uv = _corner(a, b, c, d, i / nu, j / nv)
            s['p'] += p
            s['n'] += n
            s['uv'] += uv
    at = lambda i, j: base + i * (nv + 1) + j
    for i in range(nu):
        for j in range(nv):
            s['i'] += (at(i, j), at(i, j + 1), at(i + 1, j + 1), at(i, j), at(i + 1, j + 1), at(i + 1, j))


def _split(s, a, b, c, step):
    """A triangle cut into k x k smaller ones about `step` across, facing as it did."""
    k = min(GRID_MOST, max(1, math.ceil(max(math.dist(a[0], b[0]), math.dist(b[0], c[0]), math.dist(c[0], a[0])) / step)))
    base = len(s['p']) // 3
    ids = {}
    for i in range(k + 1):
        for j in range(k + 1 - i):
            u, v = i / k, j / k
            w = 1 - u - v
            p = tuple(a[0][x] * w + b[0][x] * u + c[0][x] * v for x in range(3))
            n = _unit3(tuple(a[1][x] * w + b[1][x] * u + c[1][x] * v for x in range(3)))
            uv = tuple(a[2][x] * w + b[2][x] * u + c[2][x] * v for x in range(2))
            ids[(i, j)] = base + len(ids)
            s['p'] += p
            s['n'] += n
            s['uv'] += uv
    for i in range(k):
        for j in range(k - i):
            s['i'] += (ids[(i, j)], ids[(i + 1, j)], ids[(i, j + 1)])
            if i + j + 2 <= k:
                s['i'] += (ids[(i + 1, j)], ids[(i + 1, j + 1)], ids[(i, j + 1)])


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


BEVEL_SHARE = 0.1      # an edge rounded off by this much of the box's thinnest side...
BEVEL_MOST = 7.0        # ...but never more than this (units), and none on a box thinner than BEVEL_LEAST
BEVEL_LEAST = 14.0


def _bevel_of(mesh, part, sizes, whole=True):
    """How much a part's edges are rounded off, in game units (0: sharp). A part's own 'bevel' wins; else the model's:
    'auto' rounds a part every face of which is drawn by BEVEL_SHARE of its thinnest side."""
    b = part.get('bevel', mesh.bevel)
    if b == 'auto':
        sc = [abs(float(v)) for v in part.get('scale', (1, 1, 1))]
        thin = min(s * k for s, k in zip(sizes, sc)) if len(sizes) == 3 else min(sizes) * min(sc)
        if not whole or thin < BEVEL_LEAST or part.get('paint') == 'above':
            return 0.0
        return min(BEVEL_MOST, BEVEL_SHARE * thin)
    return float(b or 0.0)


_AXIS = {'front': 1, 'back': 1, 'left': 0, 'right': 0, 'top': 2, 'bottom': 2}


def _bevelled_box(mesh, part, place, pts, faces, looks_of, B, reach, above):
    """A box with its edges and corners cut off by B (per axis): each face drawn in by B from its edges, a strip along
    each edge and a three-cornered face at each corner. A corner keeps the normal of the face it belongs to, so the light
    turns smoothly over the edge as over a rounded one. Each face's picture still covers the whole face as it would
    unbevelled: the strips show its margin, as if wrapped round the edge."""
    hz = pts[4][2] / 2
    H = (pts[1][0], pts[2][1], hz)
    sign = [(1 if p[0] > 0 else -1, 1 if p[1] > 0 else -1, 1 if p[2] > 0 else -1) for p in pts]

    def on(name, i):                    # corner i as it lies on face `name`, drawn in from the face's edges
        a = _AXIS[name]
        s = sign[i]
        return tuple(s[k] * (H[k] if k == a else H[k] - B[k]) + (hz if k == 2 else 0.0) for k in range(3))
    frame = {}
    for name in BOX_FACES:
        idx, _nm, w, h = faces[name]
        o = pts[idx[0]]
        au = _unit3(tuple(pts[idx[3]][k] - o[k] for k in range(3)))
        av = _unit3(tuple(pts[idx[1]][k] - o[k] for k in range(3)))
        frame[name] = (o, au, av, w, h)

    def uv(name, q):                    # the picture as face `name` lays it, at q (on it or just past its edge)
        look = mesh.looks.get(looks_of[name]) or {}
        if above:
            return _above(look, q, reach)
        o, au, av, w, h = frame[name]
        d = (q[0] - o[0], q[1] - o[1], q[2] - o[2])
        u, v = d[0] * au[0] + d[1] * au[1] + d[2] * au[2], d[0] * av[0] + d[1] * av[1] + d[2] * av[2]
        if not look.get('tile'):
            u, v = min(w, max(0.0, u)), min(h, max(0.0, v))
        return _lay(look, u, v, w, h)

    def owner(names):                   # whose picture a strip or corner carries: a side's before the top's or bottom's
        names = [n for n in names if looks_of[n] is not None]
        names.sort(key=lambda n: (_AXIS[n] == 2, _AXIS[n] == 0))
        return names[0] if names else None

    def put(own, corners, out):         # corners [(point, face it lies on)], turned to face `out`
        pp = [p for p, _f in corners]
        nrm = _cross3(tuple(pp[1][k] - pp[0][k] for k in range(3)), tuple(pp[2][k] - pp[0][k] for k in range(3)))
        if nrm[0] * out[0] + nrm[1] * out[1] + nrm[2] * out[2] < 0:
            corners = corners[::-1]
        mesh.face(looks_of[own], [(place.point(p), place.normal(faces[f][1]), uv(own, p)) for p, f in corners])
    for name in BOX_FACES:
        if looks_of[name] is None:
            continue
        idx, nm, _w, _h = faces[name]
        mesh.face(looks_of[name], [(place.point(on(name, i)), place.normal(nm), uv(name, on(name, i))) for i in idx])
    names = list(BOX_FACES)
    for ai, A in enumerate(names):
        for Bn in names[ai + 1:]:
            if _AXIS[A] == _AXIS[Bn]:
                continue
            i, j = [c for c in faces[A][0] if c in faces[Bn][0]]
            own = owner((A, Bn))
            if own is None:
                continue
            out = tuple(faces[A][1][k] + faces[Bn][1][k] for k in range(3))
            put(own, [(on(A, i), A), (on(A, j), A), (on(Bn, j), Bn), (on(Bn, i), Bn)], out)
    for i in range(8):
        on_it = [n for n in BOX_FACES if i in faces[n][0]]
        own = owner(on_it)
        if own is not None:
            put(own, [(on(n, i), n) for n in on_it], sign[i])


def _box(mesh, part, place):
    x, y, z = (float(v) for v in part['size'])
    hx, hy = x / 2, y / 2
    pts = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)]
    # each face: its corners from top left, anticlockwise seen from outside; its normal; its width and height
    faces = {'front': ((4, 0, 1, 5), (0, -1, 0), x, z), 'back': ((6, 2, 3, 7), (0, 1, 0), x, z),
             'left': ((7, 3, 0, 4), (-1, 0, 0), y, z), 'right': ((5, 1, 2, 6), (1, 0, 0), y, z),
             'top': ((7, 4, 5, 6), (0, 0, 1), x, y), 'bottom': ((0, 3, 2, 1), (0, 0, -1), x, y)}
    own = part.get('faces', {})
    looks_of = {name: own.get(name, part.get('look')) for name in BOX_FACES}
    reach = max(hx, hy)
    above = part.get('paint') == 'above'
    b = _bevel_of(mesh, part, (x, y, z), all(v is not None for v in looks_of.values()))
    if b > 0:
        sc = [abs(float(v)) or 1.0 for v in part.get('scale', (1, 1, 1))]
        B = [min(b / sc[k], (x, y, z)[k] * 0.3) for k in range(3)]     # (in the part's own units, so it is round once stretched)
        _bevelled_box(mesh, part, place, pts, faces, looks_of, B, reach, above)
    for name in BOX_FACES if b <= 0 else ():
        look_name = looks_of[name]
        if look_name is None:
            continue                            # (a face nobody sees, left out)
        idx, nm, w, h = faces[name]
        look = mesh.looks.get(look_name) or {}
        n = place.normal(nm)
        where = ((0, 0), (0, h), (w, h), (w, 0))
        mesh.face(look_name, [(place.point(pts[i]), n, _above(look, pts[i], reach) if above else _lay(look, u, v, w, h))
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
    ph = math.radians(float(part.get('phase', 0.0)))       # (the ring turned before 'scale' stretches it)
    look_name = part.get('look')
    look = mesh.looks.get(look_name) or {}
    above = part.get('paint') == 'above'
    reach = max(r, r2)
    ring = lambda rad, z: [(rad * math.cos((2 * math.pi * k / n + ph)), rad * math.sin((2 * math.pi * k / n + ph)), z) for k in range(n + 1)]
    lo, hi = ring(r, 0.0), ring(r2, h)
    slant = math.hypot(h, r - r2)
    around = 2 * math.pi * reach
    if look.get('tile'):
        around = max(1, round(around / look['tile'])) * look['tile']     # (a whole number of repeats: no seam)
    side_n = lambda k: (h * math.cos((2 * math.pi * k / n + ph)), h * math.sin((2 * math.pi * k / n + ph)), r - r2)
    uv = lambda p, k, down: _above(look, p, reach) if above else _lay(look, around * k / n, down, around, slant)
    cap_look = part.get('cap_look', look_name)
    b = 0.0
    if r == r2 and part.get('caps', True) and not part.get('under') and look_name is not None and cap_look is not None:
        b = min(_bevel_of(mesh, part, (2 * r, h)), r * 0.3, h * 0.3)
    if b > 0:
        # (rounded where the side meets the ends: the side between b and h - b, a band at each end turning in to the
        # cap, which is drawn in by b; the side's normals out, the cap's up or down, the band between the two)
        cl = mesh.looks.get(cap_look) or {}
        flat = lambda p: _above(cl, p, reach) if not cl.get('tile') else _lay(cl, p[0], -p[1], 1, 1)
        lo_in, lo_out, hi_out, hi_in = ring(r - b, 0.0), ring(r, b), ring(r, h - b), ring(r - b, h)
        out_n = lambda k: (math.cos((2 * math.pi * k / n + ph)), math.sin((2 * math.pi * k / n + ph)), 0.0)
        P = place.point
        for k in range(n):
            mesh.face(look_name, [(P(hi_out[k]), place.normal(out_n(k)), uv(hi_out[k], k, b)), (P(lo_out[k]), place.normal(out_n(k)), uv(lo_out[k], k, h - b)),
                                  (P(lo_out[k + 1]), place.normal(out_n(k + 1)), uv(lo_out[k + 1], k + 1, h - b)), (P(hi_out[k + 1]), place.normal(out_n(k + 1)), uv(hi_out[k + 1], k + 1, b))])
            mesh.face(look_name, [(P(hi_in[k]), place.normal((0, 0, 1)), uv(hi_in[k], k, 0)), (P(hi_out[k]), place.normal(out_n(k)), uv(hi_out[k], k, b)),
                                  (P(hi_out[k + 1]), place.normal(out_n(k + 1)), uv(hi_out[k + 1], k + 1, b)), (P(hi_in[k + 1]), place.normal((0, 0, 1)), uv(hi_in[k + 1], k + 1, 0))])
            mesh.face(look_name, [(P(lo_out[k]), place.normal(out_n(k)), uv(lo_out[k], k, h - b)), (P(lo_in[k]), place.normal((0, 0, -1)), uv(lo_in[k], k, h)),
                                  (P(lo_in[k + 1]), place.normal((0, 0, -1)), uv(lo_in[k + 1], k + 1, h)), (P(lo_out[k + 1]), place.normal(out_n(k + 1)), uv(lo_out[k + 1], k + 1, h - b))])
        mesh.face(cap_look, [(P(p), place.normal((0, 0, 1)), flat(p)) for p in hi_in[:n]])
        mesh.face(cap_look, [(P(p), place.normal((0, 0, -1)), flat(p)) for p in reversed(lo_in[:n])])
        look_name = cap_look = None             # (drawn: below, only the solid)
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
    # (cap_look: as worked out above; None once a bevelled cylinder has drawn its own)
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


STICK_LEAST = 9.0       # (a stick's strips are never narrower: nv-rs takes anything under 7 wide for a cable, shadowcast)
STICK_BEND = 0.8        # (how far its corners' normals lean out to its edges, so it is lit as something round)


def _stick(mesh, part, place):
    """A thin stem standing on the part's origin, 'h' up z, 'r' thick at its foot and 'r2' at its top, as the game's
    plants draw theirs: 'blades' strips crossed along it (2, or 3 from 2.5 thick), each seen from both sides, over a
    see-through picture with the stem down its 'band' (texpaint.stick, STICK_BAND). Each strip is at least STICK_LEAST
    wide and shows only as much of the band as the stem is thick, so a stem down to about 1.5 units still looks as
    thick as it is. Never solid (an alpha look; a stem needing collision is a cylinder).

    Why not a cylinder: nv-rs's sun shadows take an opaque tube under 7 units wide for a cable and cast it out to 140 m,
    while leaves (cut-outs) cast to 45 m: past that a bush cast its bare stems as long dark lines (shadowcast)."""
    r = float(part['r'])
    r2 = float(part.get('r2', r))
    h = float(part['h'])
    look_name = part.get('look')
    look = mesh.looks.get(look_name) or {}
    if not look.get('alpha'):
        raise nifmake.MakeError('a stick needs a see-through look (texpaint.stick): %r' % (look_name,))
    b0, b1 = look.get('band', (0.5, 0.75))
    mid, band = (b0 + b1) / 2, b1 - b0
    most = min(mid, 1 - mid)                                    # (the strip's picture stays within one repeat across)
    blades = int(part.get('blades', 3 if max(r, r2) >= 2.5 else 2))
    ph = float(part.get('phase', 0.0))
    tile = look.get('tile')
    vs = (0.0, h / float(tile)) if tile else (1.0, 0.0)         # (v down the picture: the foot at the bottom)

    def end(rad):
        w = max(STICK_LEAST, 2 * rad)
        a = min(most, w * band / (4 * max(rad, 1e-3)))          # (half the picture's width the strip shows)
        return w / 2, a
    (w0, a0), (w1, a1) = end(r), end(r2)
    for k in range(blades):
        t = math.radians(ph + 180.0 * k / blades)
        d = (math.cos(t), math.sin(t), 0.0)
        n = (math.sin(t), -math.cos(t), 0.0)
        for f in (1, -1):                                       # (front, then back: corners anticlockwise seen from it)
            nm = lambda s: place.normal(_unit3(tuple(f * n[i] + STICK_BEND * s * d[i] for i in range(3))))
            c = lambda s, w, z, a, v: (place.point((s * w * d[0], s * w * d[1], z)), nm(s), (mid + f * s * a, v))
            mesh.face(look_name, [c(-f, w1, h, a1, vs[1]), c(-f, w0, 0.0, a0, vs[0]), c(f, w0, 0.0, a0, vs[0]), c(f, w1, h, a1, vs[1])])


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


def _unit3(v):
    ln = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / ln, v[1] / ln, v[2] / ln) if ln > 1e-9 else (0.0, 0.0, 1.0)


def _cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _hull(mesh, part, place):
    """A ship's hull from its cross-sections, the same both sides of its middle line (x 0), its length along y (the bow
    at the first station). 'stations': [{'y': along, 'pts': [(across, z) or (across, z, along offset)]}], each the same
    number of points, from the deck's edge down round the bilge to the keel on the middle line (across 0); a station
    whose points are all on the middle line is the stem. A segment of the side takes the look of the band its middle is
    in ('bands': [(from z up, look)], lowest first; else 'look'); the deck between the deck edges is 'deck_look' (laid
    across x, along y), the last station's end 'end_look' (a transom). Solid: one convex piece from each station to the
    next, so the deck can be walked."""
    st = part['stations']
    m = len(st[0]['pts'])
    bands = sorted(part.get('bands') or [(-1e18, part.get('look'))])
    side = lambda z: [lk for z0, lk in bands if z >= z0][-1] if any(z >= z0 for z0, _l in bands) else bands[0][1]
    P = [[(float(p[0]), float(st_['y']) + (float(p[2]) if len(p) > 2 else 0.0), float(p[1])) for p in st_['pts']] for st_ in st]
    top = max(p[2] for row in P for p in row)
    n = len(P)

    def nrm(i, k, sgn):                 # (smooth across the hull: from the points round this one)
        a, b = P[max(0, i - 1)][k], P[min(n - 1, i + 1)][k]
        c, d = P[i][max(0, k - 1)], P[i][min(m - 1, k + 1)]
        along, down = (b[0] - a[0], b[1] - a[1], b[2] - a[2]), (d[0] - c[0], d[1] - c[1], d[2] - c[2])
        v = _cross3(down, along)
        if abs(v[0]) + abs(v[1]) + abs(v[2]) < 1e-9:
            v = (1.0, 0.0, 0.0)
        v = _unit3(v)
        return (v[0] * sgn, v[1], v[2])

    def mir(p, sgn):
        return (p[0] * sgn, p[1], p[2])
    for i in range(n - 1):
        for k in range(m - 1):
            lk = side((P[i][k][2] + P[i][k + 1][2] + P[i + 1][k][2] + P[i + 1][k + 1][2]) / 4)
            if lk is None:
                continue
            look = mesh.looks.get(lk) or {}
            quad = [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)]
            for sgn in (1, -1):
                q = quad if sgn > 0 else quad[::-1]
                corners = []
                for ii, kk in q:
                    p = P[ii][kk]
                    corners.append((place.point(mir(p, sgn)), place.normal(nrm(ii, kk, sgn)), _lay(look, p[1], top - p[2], 1, 1)))
                if all(abs(P[ii][kk][0]) < 0.5 for ii, kk in q):
                    continue                    # (on the middle line: nothing to see)
                corners = [c for n_, c in enumerate(corners) if math.dist(c[0], corners[n_ - 1][0]) > 0.01]
                if len(corners) >= 3:           # (where two corners are one, at the stem: a triangle)
                    mesh.face(lk, corners)
    deck = part.get('deck_look')
    if deck is not None:
        dl = mesh.looks.get(deck) or {}
        for i in range(n - 1):
            a, b = P[i][0], P[i + 1][0]
            if a[0] < 0.5 and b[0] < 0.5:
                continue
            pts = [(-a[0], a[1], a[2]), (a[0], a[1], a[2]), (b[0], b[1], b[2]), (-b[0], b[1], b[2])]
            pts = [p for k_, p in enumerate(pts) if math.dist(p, pts[k_ - 1]) > 0.01]
            mesh.face(deck, [(place.point(p), place.normal((0, 0, 1)), _lay(dl, p[0] + 4096, p[1], 1, 1)) for p in pts])
    end = part.get('end_look')
    if end is not None and max(p[0] for p in P[-1]) > 0.5:
        el = mesh.looks.get(end) or {}
        ring = P[-1] + [mir(p, -1) for p in reversed(P[-1][:-1])]     # (seen from astern: down its right, up its left, anticlockwise)
        ring = [p for n_, p in enumerate(ring) if math.dist(p, ring[n_ - 1]) > 0.01]
        mesh.face(end, [(place.point(p), place.normal((0, 1, 0)), _lay(el, p[0] + 4096, top - p[2], 1, 1)) for p in ring])
    if part.get('solid', True):
        # (each section to the next as a prism: its deck the deck, its sides upright at the deck's edge, down to the
        # keel; each corner on three faces, as a solid wants. Outside the hull where it flares (a swimmer stops short of
        # the bow) but the whole deck is underfoot)
        for i in range(n - 1):
            (wa, ya, za), (wb, yb, zb) = P[i][0], P[i + 1][0]
            if wa < 20 or wb < 20:
                continue                        # (the stem's sliver)
            ka, kb = min(p[2] for p in P[i]), min(p[2] for p in P[i + 1])
            pts = [(wa, ya, za), (-wa, ya, za), (wb, yb, zb), (-wb, yb, zb), (wa, ya, ka), (-wa, ya, ka), (wb, yb, kb), (-wb, yb, kb)]
            faces = [[1, 0, 2, 3], [7, 6, 4, 5], [0, 1, 5, 4], [3, 2, 6, 7], [0, 4, 6, 2], [3, 7, 5, 1]]
            mesh.solids.append({'points': [place.point(p) for p in pts], 'faces': faces, 'material': part.get('material', 'metal')})

def _sheet(mesh, part, place):
    """A curved sheet from a grid of points, seen from both sides: 'rows': [[(x, y, z), ...], ...], each row the same
    length (a roof: rows from its ridge to its eave, each running along it). 'look' is its upper face (the side its
    normals point up to), 'under_look' (else the same) its lower, 'thick' units under the upper. Pictures run along
    the rows (u) and down from one row to the next (v), by the distance walked over the sheet. Never solid: what is
    walked under or on wants a box of its own."""
    rows = [[tuple(float(c) for c in p) for p in row] for row in part['rows']]
    m, n = len(rows[0]), len(rows)
    up_look, down_look = part['look'], part.get('under_look', part['look'])
    thick = float(part.get('thick', 4.0))
    ul, dl = mesh.looks.get(up_look) or {}, mesh.looks.get(down_look) or {}
    # (how far along and across each point is, for its picture)
    U = [[0.0] * m for _ in range(n)]
    V = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for k in range(1, m):
            U[i][k] = U[i][k - 1] + math.dist(rows[i][k], rows[i][k - 1])
    for i in range(1, n):
        for k in range(m):
            V[i][k] = V[i - 1][k] + math.dist(rows[i][k], rows[i - 1][k])

    def nrm(i, k):
        a, b = rows[max(0, i - 1)][k], rows[min(n - 1, i + 1)][k]
        c, d = rows[i][max(0, k - 1)], rows[i][min(m - 1, k + 1)]
        v = _unit3(_cross3((d[0] - c[0], d[1] - c[1], d[2] - c[2]), (b[0] - a[0], b[1] - a[1], b[2] - a[2])))
        return v if v[2] >= 0 else (-v[0], -v[1], -v[2])
    N = [[nrm(i, k) for k in range(m)] for i in range(n)]
    # (a look with no 'tile' shows its picture, or its region, once over the whole sheet)
    UL, VL = max(max(r) for r in U) or 1.0, max(max(r) for r in V) or 1.0
    for i in range(n - 1):
        for k in range(m - 1):
            quad = [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)]
            # (anticlockwise seen from above: turn it round if its own normal points down)
            a, b, d = rows[i][k], rows[i][k + 1], rows[i + 1][k]
            fn = _cross3((b[0] - a[0], b[1] - a[1], b[2] - a[2]), (d[0] - a[0], d[1] - a[1], d[2] - a[2]))
            top = quad if fn[2] >= 0 else quad[::-1]
            mesh.face(up_look, [(place.point(rows[ii][kk]), place.normal(N[ii][kk]), _lay(ul, U[ii][kk], V[ii][kk], UL, VL)) for ii, kk in top])
            low = []
            for ii, kk in top[::-1]:
                p, q = rows[ii][kk], N[ii][kk]
                low.append((place.point((p[0] - q[0] * thick, p[1] - q[1] * thick, p[2] - q[2] * thick)),
                            place.normal((-q[0], -q[1], -q[2])), _lay(dl, U[ii][kk], V[ii][kk], UL, VL)))
            mesh.face(down_look, low)


def _field(mesh, part, place):
    """A surface over a grid of points, drawn from above only, each point with its own texture coordinates: 'rows'
    [[(x, y, z), ...], ...] and 'uv' [[(u, v), ...], ...] of the same shape, 'look'. What lies in the land (rubbleset: a
    road, a heap whose skirt goes down under the ground): nobody sees its underside. Rows may close on themselves (a ring
    of a heap) and a row may be one point repeated (its middle): triangles with no area are left out. Never solid."""
    rows = [[tuple(float(c) for c in p) for p in row] for row in part['rows']]
    uvs = [[tuple(float(c) for c in t) for t in row] for row in part['uv']]
    n, m = len(rows), len(rows[0])
    look_name = part['look']

    def nrm(i, k):
        a, b = rows[max(0, i - 1)][k], rows[min(n - 1, i + 1)][k]
        c, d = rows[i][max(0, k - 1)], rows[i][min(m - 1, k + 1)]
        if part.get('closed'):                  # (a ring: its first and last points are one)
            c, d = rows[i][k - 1 if k > 0 else m - 2], rows[i][k + 1 if k < m - 1 else 1]
        v = _cross3((d[0] - c[0], d[1] - c[1], d[2] - c[2]), (b[0] - a[0], b[1] - a[1], b[2] - a[2]))
        if math.sqrt(sum(x * x for x in v)) < 1e-9:
            return (0.0, 0.0, 1.0)
        v = _unit3(v)
        return v if v[2] >= 0 else (-v[0], -v[1], -v[2])
    N = [[place.normal(nrm(i, k)) for k in range(m)] for i in range(n)]
    P = [[place.point(p) for p in row] for row in rows]
    for i in range(n - 1):
        for k in range(m - 1):
            q = [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)]
            # (cut along the shorter diagonal: a lumpy quad bends where it should)
            d0 = math.dist(P[i][k], P[i + 1][k + 1])
            d1 = math.dist(P[i][k + 1], P[i + 1][k])
            tris = ((q[0], q[1], q[2]), (q[0], q[2], q[3])) if d0 <= d1 else ((q[0], q[1], q[3]), (q[1], q[2], q[3]))
            for t in tris:
                a, b, c = (P[ii][kk] for ii, kk in t)
                fn = _cross3((b[0] - a[0], b[1] - a[1], b[2] - a[2]), (c[0] - a[0], c[1] - a[1], c[2] - a[2]))
                if math.sqrt(sum(x * x for x in fn)) < 1e-3:
                    continue                    # (no area: the middle of a ring)
                if fn[2] < 0:
                    t = t[::-1]
                mesh.face(look_name, [(P[ii][kk], N[ii][kk], uvs[ii][kk]) for ii, kk in t])


def _solid(mesh, part, place):
    """Collision alone, drawn nowhere: 'points' and 'faces' (each a list of corner numbers, anticlockwise from outside)
    of one convex solid."""
    mesh.solids.append({'points': [place.point(p) for p in part['points']], 'faces': [list(f) for f in part['faces']],
                        'material': part.get('material', 'stone')})


_SHAPES = {'box': _box, 'slab': _box, 'cylinder': _round, 'cone': _round, 'card': _card, 'frond': _frond, 'ball': _ball, 'hull': _hull,
           'sheet': _sheet, 'stick': _stick, 'field': _field, 'solid': _solid}


# What a model of FOLab's may come to (measured over the game's meshes: its buildings' median 500 to 1,700 triangles, a
# tenth over 3,000 to 7,000, the biggest 33,748; clutter 200 to 600): a building or landmark, and any smaller thing
MOST_BUILDING = 22000
MOST_THING = 6000
SHADE_MORE = 7000           # triangles a model's solid faces may gain, at most, by being cut finer to hold its shade:
SHADE_MORE_A_UNIT = 1.5     # (a small thing fewer, by its size: the game's clutter has 200 to 600 triangles a model)
SHADE_SIZE = 40.0           # (the cuts wanted: a fortieth of the model's size across, STEP_LEAST to STEP_MOST units)
STEP_LEAST, STEP_MOST = 24.0, 240.0


def _step(desc, bevel):
    """How fine a model's faces are cut for its baked shade: as fine as SHADE_SIZE asks, coarser if that would add more
    triangles than SHADE_MORE (or SHADE_MORE_A_UNIT of its size, if fewer)."""
    mesh = _parts(desc, None, bevel)
    pts = [s['p'] for name, s in mesh.by_look.items() if not mesh.looks[name].get('alpha')]
    if not pts:
        return None
    ext = max(max(max(p[a::3]) for p in pts) - min(min(p[a::3]) for p in pts) for a in range(3))
    want = min(STEP_MOST, max(STEP_LEAST, ext / SHADE_SIZE))
    base = mesh.triangles_at(1e18)
    lo, hi = want, max(want, ext)
    more = min(SHADE_MORE, max(300.0, ext * SHADE_MORE_A_UNIT))
    if mesh.triangles_at(lo) - base <= more:
        return lo
    for _ in range(18):
        mid = (lo + hi) / 2
        if mesh.triangles_at(mid) - base > more:
            lo = mid
        else:
            hi = mid
    return hi


def _parts(desc, step, bevel):
    mesh = _Mesh(desc['looks'], step, bevel)
    for part in desc['parts']:
        if part.get('far_only'):                # (in the far model alone: modelsets.far_of)
            continue
        fn = _SHAPES.get(part.get('shape'))
        if not fn:
            raise nifmake.MakeError('no part called %r: there are %s' % (part.get('shape'), ', '.join(sorted(_SHAPES))))
        fn(mesh, part, _Place(part))
    return mesh


def make(desc):
    """{'nif': the mesh's bytes, 'shapes', 'solids' (what went into it, for checking), 'box': [x1, y1, z1, x2, y2, z2],
    'triangles', 'textures'} from a description.

    As the game's own models are: edges rounded ('bevel': 'auto' unless the description says a number, or 0), and shade
    baked into the corners ('shade': True; `shade.py`), the faces cut finer to hold it ('step', else worked out from
    the model's size, `_step`); 'ground': False for a model that doesn't stand
    on the ground at z 0."""
    looks = desc['looks']
    bevel = desc.get('bevel', 'auto')
    step = None
    if desc.get('shade', True):
        step = desc.get('step') or _step(desc, bevel)
    mesh = _parts(desc, step, bevel)
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
        if look.get('sheet'):                   # (its picture is a strip of a sheet: across, u0 to u1 of it; plantsheet)
            u0, u1 = look['sheet']
            to['uv'] += [u0 + (u1 - u0) * v if k % 2 == 0 else v for k, v in enumerate(s['uv'])]
        else:
            to['uv'] += s['uv']
        to['i'] += [i + base for i in s['i']]
    shapes = list(shapes.values())
    if desc.get('shade', True):
        import shade
        shade.bake(shapes, seed=sum(desc['name'].encode()), ground=desc.get('ground', True))
    data = nifmake.build(desc['name'], shapes, mesh.solids)
    lo = [math.floor(min(min(s['p'][a::3]) for s in shapes)) for a in range(3)]
    hi = [math.ceil(max(max(s['p'][a::3]) for s in shapes)) for a in range(3)]
    return {'nif': data, 'shapes': shapes, 'solids': mesh.solids, 'box': lo + hi,
            'triangles': sum(len(s['i']) // 3 for s in shapes),
            'textures': sorted({t for s in shapes for t in (s['tex'], s['normal']) if t})}
