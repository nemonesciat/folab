"""Writes a gun's model as the game lays its own out (docs/folab-guns.md): named moving parts the game's first-person
animations move by name, marker nodes for the muzzle, the case and the sights, one loose box of collision.

  BSFadeNode                    the gun; extras BSXFlags 67 (animated, collision, moves) and 'Prn' = 'Weapon' (the bone)
  BSXFlags, NiStringExtraData
  bhkConvexVerticesShape        a box round the gun, on the weapons' layer (nifmake._held_body)
  bhkRigidBody, bhkCollisionObject
  then for each named part, as the Light Machine Gun has them:
  NiNode                        at the gun's origin, unturned (the animations' keys are moves from there; a marker node
                                is placed and turned as the game's are)
  NiTransformController         flags 0x4C, its target the node: what an animation's keys bind to
  NiTransformInterpolator       the pose unset (FLT_MAX), no keys
  the part's shapes             as nifmake writes a static's (shader, texture set, material, strips)
  and last the body's shapes, straight under the root.

Frame: x forward, y up, z right; the grip at the origin."""
import math
import struct

import nif
import nifmake

UNSET = struct.pack('<f', 3.4028234663852886e+38)
FLAGS = 0x8000E
BSX_GUN = 67                    # (the Light Machine Gun's, the Riot Shotgun's)
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
# marker nodes turned as the game's guns turn them (the Light Machine Gun's, read 20 Nov 2026)
FORWARD = ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))           # ProjectileNode, ##SightingNode: local y forward
CASE_OUT = ((0.005, 0.988, -0.152), (-0.969, 0.043, 0.244), (0.247, 0.146, 0.958))   # ShellCasingNode: out to the right


def build_gun(name, parts, marks, mass=9.0, material='metal', frames=None):
    """The bytes of a gun.

    parts: [(node name, [shape, ...])]: a named part ('##riotClip') gets a node of its own the animations move; None is
           the body, its shapes straight under the root.
    marks: [(node name, (x, y, z), turn)]: the marker nodes (ProjectileNode, ShellCasingNode, ##SightingNode).
    frames: {node name: ((x, y, z), turn)} for a part whose node the ride-on gun stands off the origin or turned (the
           Assault Carbine's ##Clip at x 10): the animations' keys are that node's whole place, starting from where the
           game's model stands it, so ours stands there too. Shapes are given in the gun's frame either way.
    Shapes as nifmake.build takes them."""
    strings, blocks = [], []

    def text(s):
        if s not in strings:
            strings.append(s)
        return strings.index(s)

    def add(kind, data=b''):
        blocks.append([kind, data])
        return len(blocks) - 1

    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for _n, ss in parts for s in ss for k in range(0, len(s['p']), 3)]
    if not pts:
        raise nifmake.MakeError('a gun needs a shape')
    box = [min(q[k] for q in pts) for k in range(3)] + [max(q[k] for q in pts) for k in range(3)]
    corners = [(box[0 if i & 1 == 0 else 3], box[1 if i & 2 == 0 else 4], box[2 if i & 4 == 0 else 5]) for i in range(8)]
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]

    root_name = text(name)
    add('BSFadeNode')
    bsx = add('BSXFlags', struct.pack('<iI', text('BSX'), BSX_GUN))
    prn = add('NiStringExtraData', struct.pack('<ii', text('Prn'), text('Weapon')))
    shape = add('bhkConvexVerticesShape', nifmake._convex({'points': corners, 'faces': faces, 'material': material}))
    body = add('bhkRigidBody', nifmake._held_body(shape, mass, box))
    collision = add('bhkCollisionObject', struct.pack('<iHi', 0, 1, body))

    def transform(t, R, s=1.0):
        return struct.pack('<3f', *t) + struct.pack('<9f', *(v for row in R for v in row)) + struct.pack('<f', s)

    def shapes_of(owner, ss):
        kids = []
        for k, s in enumerate(ss):
            me = len(blocks)
            kids.append(me)
            add('NiTriStrips', struct.pack('<iIiI', text('%s:%d' % (owner, k)), 0, -1, FLAGS) + transform((0, 0, 0), IDENTITY)
                + struct.pack('<I2ii', 2, me + 3, me + 1, -1) + struct.pack('<iiIiB', me + 4, -1, 0, 0, 0))
            add('BSShaderPPLightingProperty', struct.pack('<iIi', -1, 0, -1)
                + struct.pack('<HIIIfIi', 1, 1, 0x82000001, 1, 1.0, 3, me + 2) + struct.pack('<fiff', 0.0, 0, 4.0, 1.0))
            add('BSShaderTextureSet', struct.pack('<i', 6) + nifmake._sized(s['tex']) + nifmake._sized(s.get('normal', ''))
                + nifmake._sized('') * 4)
            add('NiMaterialProperty', struct.pack('<iIi', -1, 0, -1) + struct.pack('<9f', 0, 0, 0, 0, 0, 0, s.get('gloss', 30.0), 1, 1))
            add('NiTriStripsData', nifmake._strips_data(s))
        return kids

    def node(nm, t, R, ss):
        me = add('NiNode')
        ctl = add('NiTransformController', struct.pack('<iHffffii', -1, 0x4C, 1.0, 0.0, 0.0, 0.0, me, me + 2))
        add('NiTransformInterpolator', UNSET * 7 + struct.pack('<fi', 1.0, -1))
        kids = shapes_of(nm, ss)
        blocks[me][1] = (struct.pack('<iIii', text(nm), 0, ctl, FLAGS) + transform(t, R)
                         + struct.pack('<Ii', 0, -1) + struct.pack('<I%di' % len(kids), len(kids), *kids) + struct.pack('<I', 0))
        return me

    children = []
    for nm, ss in parts:
        if nm:
            t, R = (frames or {}).get(nm, ((0.0, 0.0, 0.0), IDENTITY))
            children.append(node(nm, t, R, [into(s, t, R) for s in ss]))
    for nm, t, R in marks:
        children.append(node(nm, t, R, []))
    for nm, ss in parts:
        if not nm:
            children += shapes_of(name, ss)
    blocks[0][1] = (struct.pack('<iI2iiI', root_name, 2, bsx, prn, -1, FLAGS) + transform((0, 0, 0), IDENTITY)
                    + struct.pack('<Ii', 0, collision) + struct.pack('<I%di' % len(children), len(children), *children) + struct.pack('<I', 0))
    types = []
    for kind, _d in blocks:
        if kind not in types:
            types.append(kind)
    head = b'Gamebryo File Format, Version 20.2.0.7\n' + struct.pack('<IBIII', nif.VERSION, 1, 11, len(blocks), 34)
    head += nifmake._short('FOLab') + nifmake._short('') + nifmake._short('')
    head += struct.pack('<H', len(types)) + b''.join(nifmake._sized(t) for t in types)
    head += struct.pack('<%dH' % len(blocks), *(types.index(k) for k, _d in blocks))
    head += struct.pack('<%dI' % len(blocks), *(len(d) for _k, d in blocks))
    head += struct.pack('<II', len(strings), max(len(s) for s in strings)) + b''.join(nifmake._sized(s) for s in strings)
    head += struct.pack('<I', 0)
    return head + b''.join(d for _k, d in blocks) + struct.pack('<II', 1, 0)


def into(s, t, R):
    """A shape given in the gun's frame, in the frame of a node stood at t turned by R (a point there is t + R p)."""
    if all(abs(v) < 1e-9 for v in t) and all(abs(R[r][c] - (r == c)) < 1e-9 for r in range(3) for c in range(3)):
        return s
    back = lambda v: [sum(R[k][i] * v[k] for k in range(3)) for i in range(3)]       # R turned back (R is a turn)
    p, n = s['p'], s['n']
    q, m = [], []
    for k in range(0, len(p), 3):
        q += back([p[k] - t[0], p[k + 1] - t[1], p[k + 2] - t[2]])
        m += back(n[k:k + 3])
    return dict(s, p=q, n=m)


# ---------- shapes ----------

class Mesh:
    """One shape being built: corners with normals and texture places, triangles turned to face out. UVs by the face's
    plane, `per` game units to the picture."""

    def __init__(self, tex, normal, gloss=30.0, per=12.0):
        self.tex, self.normal, self.gloss, self.per = tex, normal, gloss, per
        self.p, self.n, self.uv, self.i = [], [], [], []

    def corner(self, p, n, uv=None):
        ln = math.sqrt(sum(v * v for v in n)) or 1.0
        n = tuple(v / ln for v in n)
        if uv is None:
            a = max(range(3), key=lambda k: abs(n[k]))
            u, v = [k for k in range(3) if k != a]
            uv = (p[u] / self.per, -p[v] / self.per)
        self.p.append(tuple(p))
        self.n.append(n)
        self.uv.append(tuple(uv))
        return len(self.p) - 1

    def tri(self, a, b, c):
        pa, pb, pc = self.p[a], self.p[b], self.p[c]
        e1 = [pb[k] - pa[k] for k in range(3)]
        e2 = [pc[k] - pa[k] for k in range(3)]
        fn = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        avg = [self.n[a][k] + self.n[b][k] + self.n[c][k] for k in range(3)]
        if sum(fn[k] * avg[k] for k in range(3)) < 0:
            b, c = c, b
        self.i += [a, b, c]

    def quad(self, ps, n):
        k = [self.corner(p, n) for p in ps]
        self.tri(k[0], k[1], k[2])
        self.tri(k[0], k[2], k[3])

    def shape(self):
        return {'p': [v for q in self.p for v in q], 'n': [v for q in self.n for v in q], 'uv': [v for q in self.uv for v in q],
                'i': list(self.i), 'tex': self.tex, 'normal': self.normal, 'gloss': self.gloss}


def box(m, lo, hi):
    """A box, flat faces."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    m.quad([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0))
    m.quad([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0))
    m.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0))
    m.quad([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0))
    m.quad([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1))
    m.quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1))


def _area(poly):
    return sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1] for k in range(len(poly))) / 2


def ears(poly):
    """Triangles filling a simple polygon (corner numbers), by cutting off ears."""
    idx = list(range(len(poly)))
    if _area(poly) < 0:
        idx.reverse()
    out = []

    def inside(p, a, b, c):
        d = lambda u, v, w: (u[0] - w[0]) * (v[1] - w[1]) - (v[0] - w[0]) * (u[1] - w[1])
        s1, s2, s3 = d(p, a, b), d(p, b, c), d(p, c, a)
        return not ((s1 < 0 or s2 < 0 or s3 < 0) and (s1 > 0 or s2 > 0 or s3 > 0))
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            a, b, c = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            pa, pb, pc = poly[a], poly[b], poly[c]
            if (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0]) <= 0:
                continue                                    # (a reflex corner)
            if any(inside(poly[j], pa, pb, pc) for j in idx if j not in (a, b, c)):
                continue
            out.append((a, b, c))
            idx.pop(k)
            break
        else:
            raise nifmake.MakeError('a profile that crosses itself')
    out.append(tuple(idx))
    return out


def prism(m, poly, z0, z1):
    """A side profile [(x, y)] stood between z0 and z1: flat sides, both faces filled."""
    ccw = _area(poly) > 0
    for k in range(len(poly)):
        (ax, ay), (bx, by) = poly[k], poly[(k + 1) % len(poly)]
        dx, dy = bx - ax, by - ay
        n = (dy, -dx, 0.0) if ccw else (-dy, dx, 0.0)
        m.quad([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)], n)
    for z, nz in ((z0, -1.0), (z1, 1.0)):
        k = [m.corner((x, y, z), (0, 0, nz)) for x, y in poly]
        for a, b, c in ears(poly):
            m.tri(k[a], k[b], k[c])


def turned(m, axis, middle, rings, sides=16, caps=True, flat=False, inward=False):
    """A turned part round an axis ('x' or 'z') through `middle`: rings [(along, radius)] in order. Caps at the ends.
    flat: faceted (an octagon's flats) rather than round. inward: the inside of a bore, facing the axis."""
    face = -1.0 if inward else 1.0
    a = {'x': 0, 'y': 1, 'z': 2}[axis]
    u, v = [k for k in range(3) if k != a]

    def at(t, r, ang):
        p = list(middle)
        p[a] = t
        p[u] += r * math.cos(ang)
        p[v] += r * math.sin(ang)
        return tuple(p)
    for k in range(len(rings) - 1):
        (t0, r0), (t1, r1) = rings[k], rings[k + 1]
        if r0 == 0 and r1 == 0:
            continue
        slope = (r0 - r1) / (t1 - t0) if t1 != t0 else 0.0
        for j in range(sides):
            g0, g1 = 2 * math.pi * j / sides, 2 * math.pi * (j + 1) / sides
            if t1 == t0:                                    # (a step: a flat ring facing along the axis)
                n = [0.0] * 3
                n[a] = 1.0 if r1 < r0 else -1.0
                m.quad([at(t0, r0, g0), at(t0, r0, g1), at(t1, r1, g1), at(t1, r1, g0)], n)
                continue
            cs = []
            for g in (g0, g1, g1, g0):
                gg = (g0 + g1) / 2 if flat else g
                n = [0.0] * 3
                n[u], n[v], n[a] = face * math.cos(gg), face * math.sin(gg), face * slope
                cs.append(n)
            ps = [at(t0, r0, g0), at(t0, r0, g1), at(t1, r1, g1), at(t1, r1, g0)]
            per = m.per
            uvs = [(t / per, gg / (2 * math.pi) * 2) for t, gg in ((t0, g0), (t0, g1), (t1, g1), (t1, g0))]
            ks = [m.corner(p, n, uv) for p, n, uv in zip(ps, cs, uvs)]
            m.tri(ks[0], ks[1], ks[2])
            m.tri(ks[0], ks[2], ks[3])
    if caps:
        for (t, r), sign in ((rings[0], -1.0), (rings[-1], 1.0)):
            if r <= 0:
                continue
            n = [0.0] * 3
            n[a] = sign
            mid = m.corner(at(t, 0, 0), n)
            ring = [m.corner(at(t, r, 2 * math.pi * j / sides), n) for j in range(sides)]
            for j in range(sides):
                m.tri(mid, ring[j], ring[(j + 1) % sides])


def ring(m, axis, middle, t0, t1, r_in, r_out, sides=16):
    """A flat ring (an aperture, a band): a tube with a hole."""
    turned(m, axis, middle, [(t0, r_out), (t1, r_out)], sides, caps=False)
    turned(m, axis, middle, [(t0, r_in), (t1, r_in)], sides, caps=False, inward=True)
    a = {'x': 0, 'y': 1, 'z': 2}[axis]
    u, v = [k for k in range(3) if k != a]
    for t, sign in ((t0, -1.0), (t1, 1.0)):
        for j in range(sides):
            ps = []
            for r, g in ((r_in, j), (r_out, j), (r_out, j + 1), (r_in, j + 1)):
                p = list(middle)
                p[a] = t
                p[u] += r * math.cos(2 * math.pi * g / sides)
                p[v] += r * math.sin(2 * math.pi * g / sides)
                ps.append(tuple(p))
            n = [0.0] * 3
            n[a] = sign
            m.quad(ps, n)
    return m


def rod(m, a, b, r, sides=8):
    """A round bar from a to b, capped."""
    d = [b[k] - a[k] for k in range(3)]
    ln = math.sqrt(sum(x * x for x in d))
    d = [x / ln for x in d]
    up = (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (1.0, 0.0, 0.0)
    e1 = [d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2], d[0] * up[1] - d[1] * up[0]]
    l1 = math.sqrt(sum(x * x for x in e1))
    e1 = [x / l1 for x in e1]
    e2 = [d[1] * e1[2] - d[2] * e1[1], d[2] * e1[0] - d[0] * e1[2], d[0] * e1[1] - d[1] * e1[0]]
    out = lambda g: [math.cos(g) * e1[k] + math.sin(g) * e2[k] for k in range(3)]
    for j in range(sides):
        g0, g1 = 2 * math.pi * j / sides, 2 * math.pi * (j + 1) / sides
        ks = []
        for p, g in ((a, g0), (a, g1), (b, g1), (b, g0)):
            o = out(g)
            ks.append(m.corner(tuple(p[k] + r * o[k] for k in range(3)), o))
        m.tri(ks[0], ks[1], ks[2])
        m.tri(ks[0], ks[2], ks[3])
    for p, sign in ((a, -1.0), (b, 1.0)):
        n = [sign * x for x in d]
        mid = m.corner(p, n)
        rr = [m.corner(tuple(p[k] + r * out(2 * math.pi * j / sides)[k] for k in range(3)), n) for j in range(sides)]
        for j in range(sides):
            m.tri(mid, rr[j], rr[(j + 1) % sides])
