"""Writes a New Vegas mesh from nothing: a static of triangle shapes with textures, and collision the game can read.

The file is laid out as the game's own plain statics are (measured over its architecture, clutter and furniture):

  BSFadeNode                    the model: flags 0x8000E, one extra (BSXFlags 'BSX' = 2: it has collision)
  BSXFlags
  bhkConvexVerticesShape ...    a solid part each: its corners and its faces' planes, in Havok units (game units / 7),
                                drawn in by its radius (0.1), which Havok adds back all round
  bhkListShape                  the parts together (left out when there is only one, as the game does)
  bhkRigidBody                  layer 1 (static), fixed, the settings nearly every static of the game has
  bhkCollisionObject            ties the body to the node
  then for each shape:
  NiTriStrips                   properties: material, shader
  BSShaderPPLightingProperty    type 1, flags 0x82000001 / 1 (the low bit: it shines as much as its normal map's fourth
                                number says, as most of the game's building shapes do), clamp 3 (the texture repeats)
  BSShaderTextureSet            six paths: colour, normal map, four unused
  NiMaterialProperty            no shine of its own, gloss 10
  NiAlphaProperty               only on a shape with 'alpha' (leaves): flags 4844, cut at 64, and the shader's flags
                                0x82000101 as the game's plants have; such a shape's properties go alpha first
  NiTriStripsData               corners, normals, the two directions of the texture across the surface (the field the
                                format calls tangents runs down the picture, bitangents across it: measured), a sphere
                                round it all (middle of its box), a colour at each corner if the shape has 'c' (the
                                shade baked in, as 95 in 100 of the game's building shapes have, with no other block or
                                flag for it), texture coordinates, and one strip of corners whose triangles are joined
                                by ones of no area

A front face's corners go anticlockwise seen from outside. `build` makes the bytes; `check` reads them back."""
import math
import struct

import nif

HAVOK_SCALE = 7.0
HULL_RADIUS = 0.1                  # Havok units: every convex shape of the game's statics has this
MATERIALS = {'stone': 0, 'cloth': 1, 'dirt': 2, 'glass': 3, 'grass': 4, 'metal': 5, 'organic': 6, 'water': 8, 'wood': 9}
ALPHA_TEST, ALPHA_CUT = 4844, 64    # no blending, a pixel drawn or not: what most of the game's plants carry
_PROPERTY = struct.pack('<3I', 0, 0, 0x80000000)        # an empty list, as Havok writes one out


class MakeError(ValueError):
    pass


def _sized(s):
    b = s.encode('cp1252')
    return struct.pack('<I', len(b)) + b


def _short(s):
    b = s.encode('cp1252') + b'\0'
    return bytes((len(b),)) + b


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(v, else_=(0.0, 0.0, 1.0)):
    n = math.sqrt(_dot(v, v))
    return (v[0] / n, v[1] / n, v[2] / n) if n > 1e-12 else else_


# ---------- strips ----------

def strip(tris):
    """One strip for a list of triangles (flat corners, three a triangle), each kept facing the way it did. Runs of
    triangles that share edges follow on; between runs, corners are said twice, which makes triangles of no area."""
    tris = [tuple(tris[k:k + 3]) for k in range(0, len(tris), 3)]
    tris = [t for t in tris if len(set(t)) == 3]
    edge = {}                                   # (a, b) in a triangle's own order -> the triangles with it
    for i, t in enumerate(tris):
        for k in range(3):
            edge.setdefault((t[k], t[(k + 1) % 3]), []).append(i)
    used = [False] * len(tris)

    def run(i, turn):
        """The corners of a run starting with triangle i, turned so a given corner is first, and the triangles in it."""
        t = tris[i]
        s = [t[turn], t[(turn + 1) % 3], t[(turn + 2) % 3]]
        took = [i]
        mine = {i}
        while True:
            p, q = s[-2], s[-1]
            # the next triangle of a strip is (p, q, x) turned over every other time: it must hold q -> p (or p -> q)
            want = (q, p) if len(s) % 2 else (p, q)
            nxt = next((j for j in edge.get(want, ()) if not used[j] and j not in mine), None)
            if nxt is None:
                return s, took
            x = next(c for c in tris[nxt] if c != p and c != q)
            s.append(x)
            took.append(nxt)
            mine.add(nxt)

    out = []
    for i in range(len(tris)):
        if used[i]:
            continue
        s, took = max((run(i, turn) for turn in range(3)), key=lambda r: len(r[0]))
        for j in took:
            used[j] = True
        if out:
            # join on: the last corner again, the new first corner twice; once more if that leaves the new run starting
            # on an odd step, which would turn its triangles over
            out += [out[-1], s[0]]
            if len(out) % 2:
                out.append(s[0])
        out += s
    return out


# ---------- geometry ----------

def _directions(pos, uv, tris, normals):
    """Per corner, the unit directions in which the picture's v and u grow across the surface (what the file calls
    tangents and bitangents), each square to the corner's normal."""
    n = len(pos) // 3
    dv = [[0.0, 0.0, 0.0] for _ in range(n)]
    du = [[0.0, 0.0, 0.0] for _ in range(n)]
    P = lambda i: pos[3 * i:3 * i + 3]
    for k in range(0, len(tris), 3):
        a, b, c = tris[k:k + 3]
        e1, e2 = _sub(P(b), P(a)), _sub(P(c), P(a))
        u1, v1 = uv[2 * b] - uv[2 * a], uv[2 * b + 1] - uv[2 * a + 1]
        u2, v2 = uv[2 * c] - uv[2 * a], uv[2 * c + 1] - uv[2 * a + 1]
        det = u1 * v2 - u2 * v1
        if abs(det) < 1e-12:
            continue
        for x in range(3):
            pu = (e1[x] * v2 - e2[x] * v1) / det
            pv = (e2[x] * u1 - e1[x] * u2) / det
            for i in (a, b, c):
                du[i][x] += pu
                dv[i][x] += pv
    out_v, out_u = [], []
    for i in range(n):
        nm = normals[3 * i:3 * i + 3]
        for src, out in ((dv[i], out_v), (du[i], out_u)):
            d = _dot(src, nm)
            flat = (src[0] - d * nm[0], src[1] - d * nm[1], src[2] - d * nm[2])
            side = _cross(nm, (1.0, 0.0, 0.0) if abs(nm[0]) < 0.9 else (0.0, 1.0, 0.0))
            out += _unit(flat, _unit(side))
    return out_v, out_u


def _strips_data(shape):
    pos, nm, uv, tris = shape['p'], shape['n'], shape['uv'], shape['i']
    n = len(pos) // 3
    if not n or not tris:
        raise MakeError('a shape with nothing in it')
    if n > 65535:
        raise MakeError('a shape has %d corners: one shape holds 65,535 at most' % n)
    if len(nm) != 3 * n or len(uv) != 2 * n or max(tris) >= n or (shape.get('c') and len(shape['c']) != 4 * n):
        raise MakeError('a shape\'s corners, normals, colours and texture coordinates don\'t go together')
    s = strip(tris)
    if len(s) - 2 > 65535:
        raise MakeError('a shape has too many triangles for one strip')
    dv, du = _directions(pos, uv, tris, nm)
    lo = [min(pos[a::3]) for a in range(3)]
    hi = [max(pos[a::3]) for a in range(3)]
    mid = [(lo[a] + hi[a]) / 2 for a in range(3)]
    rad = max(math.dist(pos[k:k + 3], mid) for k in range(0, 3 * n, 3))
    f = lambda v: struct.pack('<%df' % len(v), *v)
    return b''.join((
        struct.pack('<iHBBB', 0, n, 0, 0, 1), f(pos),
        struct.pack('<HB', 0x1001, 1), f(nm), f(dv), f(du),         # one set of texture coordinates, and the directions
        f(mid + [rad]),
        (b'\1' + f(shape['c'])) if shape.get('c') else b'\0',       # a colour at every corner (baked shade), or none
        f(uv),
        struct.pack('<HiH', 0x4000, -1, len(s) - 2),                # never changes; nothing more; triangles in the strip
        struct.pack('<HHB', 1, len(s), 1), struct.pack('<%dH' % len(s), *s)))


# ---------- collision ----------

def _solve3(rows, rhs):
    """The point nearest to meeting every plane row . p = rhs (least squares; exact for three planes that meet)."""
    A = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
    b = [sum(r[i] * v for r, v in zip(rows, rhs)) for i in range(3)]
    det = (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
           + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))
    if abs(det) < 1e-12:
        return None
    col = lambda k: [[b[i] if j == k else A[i][j] for j in range(3)] for i in range(3)]
    d3 = lambda M: (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                    + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    return tuple(d3(col(k)) / det for k in range(3))


def hull(points, faces):
    """A convex solid as Havok wants it. points: its corners in game units; faces: each a list of corner numbers going
    anticlockwise seen from outside. Returns (corners, planes, radius) in Havok units, the solid drawn in by the radius
    (less than the usual one for a solid too thin to give that much)."""
    pts = [tuple(c / HAVOK_SCALE for c in p) for p in points]
    planes = []
    for face in faces:
        a = pts[face[0]]
        nm = (0.0, 0.0, 0.0)
        for k in range(1, len(face) - 1):       # (summed over the face: a sliver of a first triangle can't spoil it)
            c = _cross(_sub(pts[face[k]], a), _sub(pts[face[k + 1]], a))
            nm = (nm[0] + c[0], nm[1] + c[1], nm[2] + c[2])
        nm = _unit(nm, None)
        if nm is None:
            continue
        planes.append((nm[0], nm[1], nm[2], -_dot(nm, a), face))
    if len(planes) < 4:
        raise MakeError('a solid needs four faces at least')
    # how thick it is across each face says how far it can be drawn in
    thin = min(max(-(_dot(pl, p) + pl[3]) for p in pts) for pl in planes)
    radius = min(HULL_RADIUS, thin / 4)
    on = [[] for _ in pts]
    for pl in planes:
        for i in pl[4]:
            on[i].append(pl)

    def drawn_in(radius):
        return [(_solve3([pl[:3] for pl in on[i]], [-pl[3] - radius for pl in on[i]]) if len(on[i]) >= 3 else None) or p
                for i, p in enumerate(pts)]
    moved = drawn_in(radius)
    # a corner where faces meet at a sharp edge (a parasol's rim) moves much further than the radius: draw in less
    far = max(math.dist(q, p) for q, p in zip(moved, pts))
    if far > 3 * HULL_RADIUS:
        radius *= 3 * HULL_RADIUS / far
        moved = drawn_in(radius)
    return moved, [(pl[0], pl[1], pl[2], pl[3] + radius) for pl in planes], radius


def _convex(solid):
    pts, planes, radius = hull(solid['points'], solid['faces'])
    out = struct.pack('<If', MATERIALS.get(solid.get('material', 'wood'), 9), radius) + _PROPERTY * 2
    out += struct.pack('<I', len(pts)) + b''.join(struct.pack('<4f', p[0], p[1], p[2], 0.0) for p in pts)
    out += struct.pack('<I', len(planes)) + b''.join(struct.pack('<4f', *pl) for pl in planes)
    return out


def _rigid_body(shape):
    """A fixed body of the static layer. The numbers after the mass are the ones the game's statics all carry."""
    static = struct.pack('<BBH', 1, 0, 0)                           # layer, flags, group
    respond = struct.pack('<BBH', 1, 0, 0xFFFF)
    return b''.join((
        struct.pack('<i', shape), static,
        b'\0' * 4, b'\x01\0\0\0', _PROPERTY,                        # the world object: spare, how it's searched, a list
        respond,                                                    # the entity
        b'\0' * 4, static, b'\0' * 4, respond, b'\0' * 4,           # the body itself says the same again
        struct.pack('<4f', 0, 0, 0, 0), struct.pack('<4f', 0, 0, 0, 1),     # where, turned how
        b'\0' * 32,                                                 # moving, turning
        b'\0' * 48, b'\0' * 16,                                     # inertia, centre
        struct.pack('<8f', 0.0, 0.1, 0.05, 0.5, 0.4, 1068.0, 31.57, 0.1),   # mass 0, damping, friction, bounce, limits
        bytes((7, 2, 1, 1)),                                        # fixed motion, and a fixed thing's quality
        b'\0' * 12, struct.pack('<II', 0, 0)))                      # spare; nothing tied to it; no flags


def _held_body(shape, mass, box, layer=5):
    """A loose body on the weapons' layer, as the game's melee weapons have (lead pipe, bat, sledgehammer: layer 5, a box's
    inertia, quality 'debris', damping, friction and bounce the same in all of them). box: (x0, y0, z0, x1, y1, z1), game
    units; the inertia is a solid box's of that size and mass, round its middle, in Havok units. Layer 4 is clutter, as the
    game's hats lying on the ground are (their _GO models)."""
    weapon = struct.pack('<BBH', layer, 0, 0)
    respond = struct.pack('<BBH', 1, 0, 0xFFFF)
    d = [(box[3 + k] - box[k]) / HAVOK_SCALE for k in range(3)]
    mid = [(box[3 + k] + box[k]) / 2 / HAVOK_SCALE for k in range(3)]
    ixx, iyy, izz = (mass / 12.0 * (d[1] ** 2 + d[2] ** 2), mass / 12.0 * (d[0] ** 2 + d[2] ** 2), mass / 12.0 * (d[0] ** 2 + d[1] ** 2))
    return b''.join((
        struct.pack('<i', shape), weapon,
        b'\0' * 4, b'\x01\0\0\0', _PROPERTY,
        respond,
        b'\0' * 4, weapon, b'\0' * 4, respond, b'\0' * 4,
        struct.pack('<4f', 0, 0, 0, 0), struct.pack('<4f', 0, 0, 0, 1),
        b'\0' * 32,
        struct.pack('<12f', ixx, 0, 0, 0, 0, iyy, 0, 0, 0, 0, izz, 0), struct.pack('<4f', mid[0], mid[1], mid[2], 0),
        struct.pack('<8f', mass, 0.1, 0.05, 0.5, 0.4, 1068.0, 31.57, 0.15),
        bytes((4, 2, 2, 3)),                                        # box inertia, deactivates, debris quality: the game's weapons'
        b'\0' * 12, struct.pack('<II', 0, 0)))


def _relay(data, root=None, bsx=None, body=None, extras=()):
    """A built file's blocks laid out again: the root's type (`root`), its BSXFlags' number (`bsx`), its collision body's
    bytes (`body(shape)`), more NiStringExtraData on the root (`extras`: [(name, text)])."""
    n = nif.Nif(data)
    blocks = [data[n.offsets[i]:n.offsets[i] + n.sizes[i]] for i in range(len(n.types))]
    types = list(n.types)
    strings = list(n.strings)
    for pair in extras:
        for s in pair:
            if s not in strings:
                strings.append(s)
    if root:
        types[0] = root
    if bsx is not None:
        k = types.index('BSXFlags')
        blocks[k] = struct.pack('<iI', strings.index('BSX'), bsx)
    if body:
        k = types.index('bhkRigidBody')
        blocks[k] = body(struct.unpack_from('<i', blocks[k])[0])
    more = []
    for a, b in extras:
        types.append('NiStringExtraData')
        blocks.append(struct.pack('<ii', strings.index(a), strings.index(b)))
        more.append(len(blocks) - 1)
    top = blocks[0]
    nm, count = struct.unpack_from('<iI', top)
    have = list(struct.unpack_from('<%di' % count, top, 8)) + more
    blocks[0] = struct.pack('<iI%di' % len(have), nm, len(have), *have) + top[8 + 4 * count:]
    order = []
    for t in types:
        if t not in order:
            order.append(t)
    head = b'Gamebryo File Format, Version 20.2.0.7\n' + struct.pack('<IBIII', nif.VERSION, 1, 11, len(blocks), 34)
    head += _short('FOLab') + _short('') + _short('')
    head += struct.pack('<H', len(order)) + b''.join(_sized(t) for t in order)
    head += struct.pack('<%dH' % len(blocks), *(order.index(k) for k in types))
    head += struct.pack('<%dI' % len(blocks), *(len(b) for b in blocks))
    head += struct.pack('<II', len(strings), max(len(s) for s in strings)) + b''.join(_sized(s) for s in strings)
    head += struct.pack('<I', 0)
    return head + b''.join(blocks) + struct.pack('<II', 1, 0)


def _loose(name, shapes, mass, material, layer, extras):
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for s in shapes for k in range(0, len(s['p']), 3)]
    box = [min(q[k] for q in pts) for k in range(3)] + [max(q[k] for q in pts) for k in range(3)]
    corners = [(box[0 if i & 1 == 0 else 3], box[1 if i & 2 == 0 else 4], box[2 if i & 4 == 0 else 5]) for i in range(8)]
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    data = build(name, shapes, [{'points': corners, 'faces': faces, 'material': material}])
    return _relay(data, bsx=66, body=lambda shape: _held_body(shape, mass, box, layer), extras=extras)


def build_held(name, shapes, mass=10.0, material='wood'):
    """The bytes of a weapon held in the hand (a melee weapon's model, worn and dropped), laid out as the game's own: the
    root's extras say it has collision (BSXFlags 66, as every melee weapon of the game) and which bone holds it
    ('Prn' = 'Weapon'); its collision is one box round the shapes on the weapons' layer (`_held_body`). In the model's own
    frame the grip is at the origin, the business end along +y and the striking side along x, as the game's weapons lie."""
    return _loose(name, shapes, mass, material, 5, [('Prn', 'Weapon')])


def build_dropped(name, shapes, mass=0.5, material='cloth'):
    """The bytes of a thing lying loose on the ground (a hat's _GO model): BSXFlags 66, one box round it on the clutter
    layer (4), as the game's Pre-War Hat and cowboy hats lie."""
    return _loose(name, shapes, mass, material, 4, [])


def build_worn(name, shapes, bone=None):
    """The bytes of a rigid thing worn on the head (a hat), as the game's cowboy hats: a NiNode, no collision, no 'Prn'.
    The game hangs it on the head slot's own node (HeadAnims, square to the world: z up, +y the face), so its shapes are
    laid out along the world's axes. A 'Prn' of 'Bip01 Head' hangs it on that bone instead, which the skeleton turns a
    quarter (its z is the head's left): the boater sat on its edge on the side of the head (the user, 21 Nov 2026).
    `bone` names a Prn for a model made in that bone's own frame."""
    return _relay(build(name, shapes), root='NiNode', extras=[('Prn', bone)] if bone else [])


# ---------- the file ----------

def build(name, shapes, solids=()):
    """The bytes of a static.

    shapes: [{'p': flat corners, 'n': flat normals, 'uv': flat texture coordinates, 'i': flat triangles,
              'tex': colour texture path, 'normal': normal map path, 'gloss': 10, 'alpha': False,
              'glow': glow map path (it glows), 'glow_mult': how bright}]
    solids: [{'points': [(x, y, z)], 'faces': [[corner numbers, anticlockwise from outside]], 'material': 'wood'}]
    Game units; z up."""
    if not shapes:
        raise MakeError('a model needs a shape')
    strings, blocks = [], []                    # blocks: (type name, bytes)

    def text(s):
        if s not in strings:
            strings.append(s)
        return strings.index(s)

    def add(kind, data):
        blocks.append((kind, data))
        return len(blocks) - 1

    identity = struct.pack('<3f9ff', 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1)
    root_name = text(name)
    add('BSFadeNode', b'')                      # filled in below, once its children's numbers are known
    extras = []
    collision = -1
    if solids:
        extras.append(add('BSXFlags', struct.pack('<iI', text('BSX'), 2)))
        kids = [add('bhkConvexVerticesShape', _convex(s)) for s in solids]
        top = kids[0]
        if len(kids) > 1:
            top = add('bhkListShape', struct.pack('<I%di' % len(kids), len(kids), *kids) + struct.pack('<I', 0) + _PROPERTY * 2
                      + struct.pack('<I', len(kids)) + b'\0' * (4 * len(kids)))
        body = add('bhkRigidBody', _rigid_body(top))
        collision = add('bhkCollisionObject', struct.pack('<iHi', 0, 1, body))
    children = []
    for k, s in enumerate(shapes):
        me = len(blocks)
        children.append(me)
        cut = bool(s.get('alpha'))              # see-through where the texture says so: leaves
        props = ([me + 4] if cut else []) + [me + 3, me + 1]
        add('NiTriStrips', struct.pack('<iIiI', text('%s:%d' % (name, k)), 0, -1, 0x8000E) + identity
            + struct.pack('<I%dii' % len(props), len(props), *props, -1) + struct.pack('<iiIiB', me + (5 if cut else 4), -1, 0, 0, 0))
        add('BSShaderPPLightingProperty', struct.pack('<iIi', -1, 0, -1)
            + struct.pack('<HIIIfIi', 1, 1, 0x82000101 if cut else 0x82000001, 1, 1.0, 3, me + 2) + struct.pack('<fiff', 0.0, 0, 4.0, 1.0))
        # (a glowing shape, as the game's lamps and neon: a glow map in the third slot, the material's emissive white and
        # its multiplier how bright)
        add('BSShaderTextureSet', struct.pack('<i', 6) + _sized(s['tex']) + _sized(s.get('normal', '')) + _sized(s.get('glow', '')) + _sized('') * 3)
        glow = 1.0 if s.get('glow') else 0.0
        add('NiMaterialProperty', struct.pack('<iIi', -1, 0, -1) + struct.pack('<9f', 0, 0, 0, glow, glow, glow, s.get('gloss', 10.0), 1, s.get('glow_mult', 1.0) if glow else 1))
        if cut:
            add('NiAlphaProperty', struct.pack('<iIi', -1, 0, -1) + struct.pack('<HB', ALPHA_TEST, ALPHA_CUT))
        add('NiTriStripsData', _strips_data(s))
    blocks[0] = ('BSFadeNode', struct.pack('<iI%diiI' % len(extras), root_name, len(extras), *extras, -1, 0x8000E) + identity
                 + struct.pack('<Ii', 0, collision) + struct.pack('<I%di' % len(children), len(children), *children)
                 + struct.pack('<I', 0))
    types = []
    for kind, _d in blocks:
        if kind not in types:
            types.append(kind)
    head = b'Gamebryo File Format, Version 20.2.0.7\n' + struct.pack('<IBIII', nif.VERSION, 1, 11, len(blocks), 34)
    head += _short('FOLab') + _short('') + _short('')
    head += struct.pack('<H', len(types)) + b''.join(_sized(t) for t in types)
    head += struct.pack('<%dH' % len(blocks), *(types.index(k) for k, _d in blocks))
    head += struct.pack('<%dI' % len(blocks), *(len(d) for _k, d in blocks))
    head += struct.pack('<II', len(strings), max(len(s) for s in strings)) + b''.join(_sized(s) for s in strings)
    head += struct.pack('<I', 0)
    return head + b''.join(d for _k, d in blocks) + struct.pack('<II', 1, 0)        # (the end: one root, block 0)


def check(data, shapes, solids=()):
    """What's wrong with a built file, as FOLab's own readers see it: [] when the mesh and the collision both read back
    as what was asked for."""
    import hkshape
    wrong = []
    back = nif.mesh_from_nif(data)
    if len(back) != len(shapes):
        return ['%d shapes read back of %d' % (len(back), len(shapes))]
    for k, (s, b) in enumerate(zip(shapes, back)):
        want = sum(1 for i in range(0, len(s['i']), 3) if len(set(s['i'][i:i + 3])) == 3)
        if len(b['i']) // 3 != want:
            wrong.append('shape %d: %d triangles read back of %d' % (k, len(b['i']) // 3, want))
        if b['tex'].lower() != s['tex'].replace('/', '\\').lower():
            wrong.append('shape %d: texture %s read back as %s' % (k, s['tex'], b['tex']))
        if b['alpha'] != ('test' if s.get('alpha') else ''):
            wrong.append('shape %d: see-through read back as %r' % (k, b['alpha']))
        if len(b['p']) != len(s['p']) or any(abs(x - y) > 0.01 for x, y in zip(b['p'], s['p'])):
            wrong.append('shape %d: its corners moved' % k)
        # every triangle still faces the way it did
        P = lambda src, i: src['p'][3 * i:3 * i + 3]
        face = lambda src, t: _cross(_sub(P(src, t[1]), P(src, t[0])), _sub(P(src, t[2]), P(src, t[0])))
        asked = {}
        for i in range(0, len(s['i']), 3):
            t = s['i'][i:i + 3]
            asked[frozenset(t)] = face(s, t)
        for i in range(0, len(b['i']), 3):
            t = b['i'][i:i + 3]
            a = asked.get(frozenset(t))
            if a is None or _dot(a, face(b, t)) <= 0:
                wrong.append('shape %d: a triangle came back turned over or changed' % k)
                break
    try:
        got = hkshape.collision_shapes(data)
    except (hkshape.Unread, nif.NifError, struct.error, IndexError) as e:
        return wrong + ['its collision doesn\'t read: %s' % e]
    if len(got) != len(solids):
        wrong.append('%d solid parts read back of %d' % (len(got), len(solids)))
    for k, (s, g) in enumerate(zip(solids, got)):
        if g['layer'] != 1:
            wrong.append('solid %d is on layer %d' % (k, g['layer']))
        # a closed solid: every face came out as triangles, so each edge is used once each way
        edges = {}
        for i in range(0, len(g['i']), 3):
            t = g['i'][i:i + 3]
            for j in range(3):
                e = (t[j], t[(j + 1) % 3])
                edges[e] = edges.get(e, 0) + 1
        if not edges or any(edges.get((b, a)) != n for (a, b), n in edges.items()):
            wrong.append('solid %d doesn\'t close' % k)
        lo = [min(p[a] for p in s['points']) for a in range(3)]
        hi = [max(p[a] for p in s['points']) for a in range(3)]
        glo = [min(g['v'][a::3]) for a in range(3)]
        ghi = [max(g['v'][a::3]) for a in range(3)]
        if any(glo[a] < lo[a] - 0.05 or ghi[a] > hi[a] + 0.05 or glo[a] > lo[a] + 3 or ghi[a] < hi[a] - 3 for a in range(3)):
            wrong.append('solid %d isn\'t where it was asked for' % k)
    return wrong


# the game's grass models (landscape\grass\*.nif, all alike): BSFadeNode, one NiTriStrips whose properties are a
# NiStencilProperty (both sides drawn), the TallGrassShaderProperty (the picture's path at its end) and a NiAlphaProperty,
# then its data with a colour at each corner. Their blocks copied as the game has them, only the picture and the cut ours.
_GRASS_STENCIL = bytes.fromhex('ffffffff00000000ffffffff804d00000000ffffffff')
_GRASS_SHADER = bytes.fromhex('ffffffff00000000ffffffff01000000000000010080010000000000803f')   # (18 after the object's 12: one short crashed nv-rs, 20 Nov 2026)
GRASS_CUT = 64              # (the game's grass cuts at 128; FOLab's pictures keep their share over 64: dds._keep_cover)


def build_grass(name, shape, sway=0.3):
    """The bytes of a grass model for a GRAS record: one shape (as build's), drawn by the game's grass shader. A corner's
    colour's fourth number is how far the shader sways it in the wind: the game's grasses have 0 at the ground, 0.1 to
    0.3 up the blade, up to 0.75 at a tip (read from NVGreenGrass01/03, NVGrassGolf02). FOLab's carried 1 everywhere and
    the whole plant swung about from its foot (the user, 20 Nov 2026: "the whole plant is moving around"). So: nothing
    at or under the ground, rising with height to `sway` at the top."""
    s = dict(shape)
    n = len(s['p']) // 3
    c = list(s.get('c') or [1.0] * (4 * n))
    top = max(s['p'][2::3]) or 1.0
    for k in range(n):
        z = s['p'][3 * k + 2]
        c[4 * k + 3] = round(sway * max(0.0, z) / top, 3)
    s['c'] = c
    strings = [name, name + ':0']
    blocks = []
    identity = struct.pack('<3f9ff', 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1)
    blocks.append(('BSFadeNode', struct.pack('<iIiI', 0, 0, -1, 0x8000E) + identity + struct.pack('<Ii', 0, -1)
                   + struct.pack('<Ii', 1, 1) + struct.pack('<I', 0)))
    blocks.append(('NiTriStrips', struct.pack('<iIiI', 1, 0, -1, 0x8000E) + identity + struct.pack('<I3ii', 3, 2, 3, 4, -1)
                   + struct.pack('<iiIiB', 5, -1, 0, 0, 0)))
    blocks.append(('NiStencilProperty', _GRASS_STENCIL))
    blocks.append(('TallGrassShaderProperty', _GRASS_SHADER + _sized(s['tex'])))
    blocks.append(('NiAlphaProperty', struct.pack('<iIi', -1, 0, -1) + struct.pack('<HB', 0x12EC, GRASS_CUT)))
    blocks.append(('NiTriStripsData', _strips_data(s)))
    types = []
    for kind, _d in blocks:
        if kind not in types:
            types.append(kind)
    head = b'Gamebryo File Format, Version 20.2.0.7\n' + struct.pack('<IBIII', nif.VERSION, 1, 11, len(blocks), 34)
    head += _short('FOLab') + _short('') + _short('')
    head += struct.pack('<H', len(types)) + b''.join(_sized(t) for t in types)
    head += struct.pack('<%dH' % len(blocks), *(types.index(k) for k, _d in blocks))
    head += struct.pack('<%dI' % len(blocks), *(len(d) for _k, d in blocks))
    head += struct.pack('<II', len(strings), max(len(x) for x in strings)) + b''.join(_sized(x) for x in strings)
    head += struct.pack('<I', 0)
    return head + b''.join(d for _k, d in blocks) + struct.pack('<II', 1, 0)
