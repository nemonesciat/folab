"""The collision shapes of a mesh (Havok blocks in a NIF), as triangles in the model's own coordinates and game units.

What an actor can stand on is the collision, not what is drawn. Havok's numbers are game units / 7. A node points to a
collision object, that to a rigid body with a layer (what kind of thing it is) and a shape; bhkRigidBodyT also places
the shape. Shapes used by the game's static meshes: a triangle soup behind a search tree (the tree is skipped), convex
hulls given as points and planes, boxes, capsules, spheres, and lists and transforms of those.
Read-only; every block read must end exactly at its size in the file's table (nif.py's check)."""
import math

import nif

HAVOK_SCALE = 7.0
# Layers that are part of the world's solid shape: static, animated static, transparent (glass still stops you), trees,
# props, terrain, ground, stairs. Left out: clutter and weapons (they move), triggers, water, doors' detection boxes...
LAYERS_SOLID = {1, 2, 3, 9, 10, 13, 17, 19}
_I3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
_RING = 8                                       # sides of the prism standing in for a capsule or sphere


class Unread(ValueError):
    """A shape block this reader doesn't know: the caller falls back on the drawn mesh."""


def _quat(x, y, z, w):
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
            (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
            (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)))


def _apply(R, t, s, v):
    return (t[0] + s * (R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2]),
            t[1] + s * (R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2]),
            t[2] + s * (R[2][0] * v[0] + R[2][1] * v[1] + R[2][2] * v[2]))


def _compose(R, t, s, lR, lt, ls):
    """Parent (R, t, s) followed by child (lR, lt, ls)."""
    return (tuple(tuple(sum(R[i][k] * lR[k][j] for k in range(3)) for j in range(3)) for i in range(3)),
            _apply(R, t, s, lt), s * ls)


def _box_points(lo, hi):
    return [(x, y, z) for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])]


_BOX_TRIS = (0, 2, 1, 1, 2, 3, 4, 5, 6, 5, 7, 6, 0, 1, 4, 1, 5, 4, 2, 6, 3, 3, 6, 7, 0, 4, 2, 2, 4, 6, 1, 3, 5, 3, 7, 5)


def _hull_tris(points, planes):
    """Triangles of a convex hull given by its points and face planes (nx, ny, nz, d; on the face n.p + d = 0)."""
    out = []
    size = max((max(abs(c) for c in p) for p in points), default=1.0)
    tol = max(size * 0.002, 1e-4)
    for nx, ny, nz, d in planes:
        on = [i for i, p in enumerate(points) if abs(nx * p[0] + ny * p[1] + nz * p[2] + d) <= tol]
        if len(on) < 3:
            continue
        # round the face, as seen from outside, about its middle
        cx, cy, cz = (sum(points[i][k] for i in on) / len(on) for k in range(3))
        ax = (1.0, 0.0, 0.0) if abs(nx) < 0.9 else (0.0, 1.0, 0.0)
        ux, uy, uz = ny * ax[2] - nz * ax[1], nz * ax[0] - nx * ax[2], nx * ax[1] - ny * ax[0]
        vx, vy, vz = ny * uz - nz * uy, nz * ux - nx * uz, nx * uy - ny * ux

        def angle(i):
            p = points[i]
            dx, dy, dz = p[0] - cx, p[1] - cy, p[2] - cz
            return math.atan2(vx * dx + vy * dy + vz * dz, ux * dx + uy * dy + uz * dz)
        on.sort(key=angle)
        for k in range(1, len(on) - 1):
            a, b, c = points[on[0]], points[on[k]], points[on[k + 1]]
            # (wound so its normal is the plane's, whichever way round the two axes came out)
            ex, ey, ez = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            fx, fy, fz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            if (ey * fz - ez * fy) * nx + (ez * fx - ex * fz) * ny + (ex * fy - ey * fx) * nz < 0:
                out += (on[0], on[k + 1], on[k])
            else:
                out += (on[0], on[k], on[k + 1])
    return out


def _prism(a, b, ra, rb):
    """A capsule from a to b as an eight-sided box round it; near enough to block the way."""
    r = max(ra, rb)
    pts, tris = [], []
    for k in range(_RING):
        ang = 2 * math.pi * k / _RING
        ox, oy = r * math.cos(ang), r * math.sin(ang)
        pts.append((a[0] + ox, a[1] + oy, min(a[2], b[2]) - r))
        pts.append((b[0] + ox, b[1] + oy, max(a[2], b[2]) + r))
    for k in range(_RING):
        i, j = 2 * k, 2 * ((k + 1) % _RING)
        tris += (i, j, i + 1, j, j + 1, i + 1)
    for k in range(1, _RING - 1):
        tris += (0, 2 * (k + 1), 2 * k, 1, 2 * k + 1, 2 * (k + 1) + 1)
    return pts, tris


class _Shapes:
    def __init__(self, n):
        self.n = n
        self.out = []

    def _r(self, i):
        return nif.Reader(self.n.data, self.n.offsets[i])

    def add(self, points, tris, R, t, s, layer, soup=False):
        v = []
        for p in points:
            v += _apply(R, t, s, p)
        self.out.append({'layer': layer, 'v': v, 'i': list(tris), 'soup': soup})

    def shape(self, i, R, t, s, layer):
        """Add shape block i. Inside a shape everything is in Havok units; (R, t, s) takes that to model units."""
        if not 0 <= i < len(self.n.types):
            return
        kind = self.n.types[i]
        r = self._r(i)
        end = self.n.offsets[i] + self.n.sizes[i]
        if kind == 'bhkMoppBvTreeShape':
            self.shape(r.i32(), R, t, s, layer)
        elif kind == 'bhkListShape':
            for c in r.many('i', r.u32()):
                self.shape(c, R, t, s, layer)
        elif kind in ('bhkTransformShape', 'bhkConvexTransformShape'):
            c = r.i32()
            r.u32(); r.f32(); r.many('f', 2)
            m = r.many('f', 16)
            lR = ((m[0], m[4], m[8]), (m[1], m[5], m[9]), (m[2], m[6], m[10]))
            self.shape(c, *_compose(R, t, s, lR, (m[12], m[13], m[14]), 1.0), layer)
        elif kind == 'bhkPackedNiTriStripsShape':
            r.p = end - 4
            self.packed(r.i32(), R, t, s, layer)
        elif kind == 'bhkConvexVerticesShape':
            r.u32(); r.f32(); r.many('I', 6)
            nv = r.u32()
            v4 = r.many('f', 4 * nv)
            nn = r.u32()
            n4 = r.many('f', 4 * nn)
            if r.p != end:
                raise nif.NifError('%s read short' % kind)
            pts = [v4[k:k + 3] for k in range(0, 4 * nv, 4)]
            self.add(pts, _hull_tris(pts, [n4[k:k + 4] for k in range(0, 4 * nn, 4)]), R, t, s, layer)
        elif kind == 'bhkBoxShape':
            r.u32()
            rad = r.f32()
            r.many('f', 2)
            d = r.many('f', 3)
            hi = tuple(x + rad for x in d)
            self.add(_box_points(tuple(-x for x in hi), hi), _BOX_TRIS, R, t, s, layer)
        elif kind == 'bhkCapsuleShape':
            r.u32()
            rad = r.f32()
            r.many('f', 2)
            a = r.many('f', 3)
            ra = r.f32()
            b = r.many('f', 3)
            rb = r.f32()
            self.add(*_prism(a, b, max(ra, rad), max(rb, rad)), R, t, s, layer)
        elif kind == 'bhkSphereShape':
            r.u32()
            rad = r.f32()
            self.add(_box_points((-rad, -rad, -rad), (rad, rad, rad)), _BOX_TRIS, R, t, s, layer)
        elif kind == 'bhkNiTriStripsShape':
            self.strips(r, R, t, s, layer)
        else:
            raise Unread(kind)

    def packed(self, i, R, t, s, layer):
        if self.n.types[i] != 'hkPackedNiTriStripsData':
            raise Unread(self.n.types[i])
        r = self._r(i)
        nt = r.u32()
        raw = r.many('H', 4 * nt)               # three corners and a welding word
        nv = r.u32()
        r.u8()                                  # compressed: never set in this game's files
        v = r.many('f', 3 * nv)
        pts = [v[k:k + 3] for k in range(0, 3 * nv, 3)]
        tris = [c for k in range(0, 4 * nt, 4) for c in raw[k:k + 3]]
        self.add(pts, tris, R, t, s, layer, True)

    def strips(self, r, R, t, s, layer):
        """Triangle strips held in ordinary NIF geometry; its points are in game units, not Havok's."""
        r.u32(); r.f32()
        r.many('B', 20)
        r.u32()
        r.many('f', 4)
        for c in r.many('i', r.u32()):
            d = self.n.block(c)
            if d and d.get('verts'):
                v = d['verts']
                self.add([v[k:k + 3] for k in range(0, len(v), 3)], d['tris'], R, t, s / HAVOK_SCALE, layer, True)


def _body(sh, i, R, t, s):
    """A rigid body: place its shape in the model."""
    n = sh.n
    if not 0 <= i < len(n.types) or n.types[i] not in ('bhkRigidBody', 'bhkRigidBodyT'):
        return                                  # phantoms and such stop nobody
    r = sh._r(i)
    shape = r.i32()
    layer = r.u32() & 0x7F
    if n.types[i] == 'bhkRigidBodyT':
        r.p = n.offsets[i] + 8 + 20 + 4 + 20    # past the world object and entity parts: the start of the body's data
        tx = r.many('f', 4)
        q = r.many('f', 4)
        R, t, s = _compose(R, t, s, _quat(*q), [c * HAVOK_SCALE for c in tx[:3]], 1.0)
    sh.shape(shape, R, t, s * HAVOK_SCALE, layer)


def collision_shapes(data):
    """[{'layer', 'v': flat points, 'i': flat corners, 'soup'}] of a NIF's collision, in its own coordinates and game
    units. Empty when it has none. 'soup': a triangle soup, whose triangles face either way (it comes from strips, so
    which way a triangle winds says nothing). Raises Unread on a shape block this reader doesn't know."""
    n = nif.Nif(data)
    sh = _Shapes(n)
    seen = set()

    def visit(i, R, t, s):
        if i in seen:
            return
        seen.add(i)
        b = n.block(i)
        if not b:
            return
        nR, nt, ns = _compose(R, t, s, b['R'], b['t'], b['s'])
        c = b.get('collision', -1)
        if 0 <= c < len(n.types) and n.types[c] == 'bhkCollisionObject':
            r = sh._r(c)
            r.i32(); r.u16()
            _body(sh, r.i32(), nR, nt, ns)
        for k in b.get('children', ()):
            visit(k, nR, nt, ns)

    if n.blocks:
        visit(0, _I3, (0.0, 0.0, 0.0), 1.0)
    return sh.out
