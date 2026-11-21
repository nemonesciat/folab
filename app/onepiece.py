"""The game's statics drawn in one piece (20 Nov 2026: Waikiki's heaviest spots were the suburban rubble pile, five shapes
of one picture, 805 of them round one spot). `merged` rebuilds a game model whose shapes all share one picture and none is
see-through as a single shape: the same corners, normals, baked shade and texture coordinates, each shape's own place in
the model applied; its collision one convex solid round the game's own collision corners (a pile, not a room: walked over
the same, a little fuller in its hollows). `ops` makes a STAT of the mod's own per model ('FOLab' + its editor ID, the
game's bounds) and swaps every thing the mod stands of the game's base for it. MERGE is what's done."""
import math
import os

import library
import nif
import nifmake
import recordio

MERGE = ('SuburbanRubblePileSm01', 'IndRubblePileSm01')     # (the mailbox and dumpster are no STAT: things to search, left)
SNAPS = (2.0, 4.0, 6.0, 8.0, 12.0, 16.0)
FOLDER = 'folab\\onepiece'


class Unfit(Exception):
    pass


def _mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _apply(R, v):
    return [R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2],
            R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2],
            R[2][0] * v[0] + R[2][1] * v[1] + R[2][2] * v[2]]


def _det(R):
    return (R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1]) - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
            + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]))


def shapes_of(data):
    """[{'p', 'n', 'uv', 'i', 'c' (RGBA a corner or None), 'tex', 'normal', 'alpha'}] in the model's frame, as the game
    places it (the root's own turn left out, as nif.mesh_from_nif does)."""
    N = nif.Nif(data)
    out, seen = [], set()
    I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

    def visit(i, R, t, s):
        if i in seen:
            return
        seen.add(i)
        b = N.block(i)
        if not b or b['flags'] & nif.APP_CULLED:
            return
        lR, lt, ls = (I3, [0.0, 0.0, 0.0], 1.0) if i == 0 else (b['R'], b['t'], b['s'])
        nR = _mul(R, lR)
        nt = [t[k] + s * v for k, v in enumerate(_apply(R, lt))]
        ns = s * ls
        if 'children' in b:
            for c in b['children']:
                visit(c, nR, nt, ns)
            return
        d = N.block(b['data'])
        if not d or not d['verts'] or not d['tris']:
            return
        v, nm = d['verts'], d.get('normals') or ()
        n = len(v) // 3
        if len(nm) != 3 * n:
            raise Unfit('a shape without normals')
        pos, nor = [], []
        for k in range(0, len(v), 3):
            w = _apply(nR, v[k:k + 3])
            pos += [nt[a] + ns * w[a] for a in range(3)]
            m = _apply(nR, nm[k:k + 3])
            ln = math.sqrt(sum(x * x for x in m)) or 1.0
            nor += [x / ln for x in m]
        idx = list(d['tris'])
        if _det(nR) < 0:
            idx = [x for k in range(0, len(idx) - 2, 3) for x in (idx[k], idx[k + 2], idx[k + 1])]
        tex, normal, blend, test = '', '', False, False
        for pi in b['props']:
            p = N.block(pi)
            if not p:
                continue
            if p['type'] in ('BSShaderPPLightingProperty', 'Lighting30ShaderProperty'):
                ts = N.block(p['texset'])
                if ts and ts['textures']:
                    tex = ts['textures'][0]
                    normal = ts['textures'][1] if len(ts['textures']) > 1 else ''
            elif p['type'] == 'NiAlphaProperty':
                blend, test = bool(p['flags'] & 1), bool(p['flags'] & 0x200)
        c = d['colors']
        out.append({'p': pos, 'n': nor, 'uv': list(d['uv']), 'i': idx, 'c': list(c) if c and len(c) == 4 * n else None,
                    'tex': tex.replace('/', '\\'), 'normal': normal.replace('/', '\\'), 'alpha': blend or test})
    if N.blocks:
        visit(0, I3, [0.0, 0.0, 0.0], 1.0)
    return out


def join(shapes):
    """One shape of several that share a picture."""
    if not shapes:
        raise Unfit('no shapes')
    if len({(s['tex'].lower(), s['normal'].lower()) for s in shapes}) != 1:
        raise Unfit('its shapes use different pictures')
    if any(s['alpha'] for s in shapes):
        raise Unfit('a shape is see-through')
    one = {'p': [], 'n': [], 'uv': [], 'i': [], 'tex': shapes[0]['tex'], 'normal': shapes[0]['normal']}
    shade = any(s['c'] for s in shapes)
    if shade:
        one['c'] = []
    for s in shapes:
        base = len(one['p']) // 3
        one['p'] += s['p']
        one['n'] += s['n']
        one['uv'] += s['uv']
        one['i'] += [base + x for x in s['i']]
        if shade:
            one['c'] += s['c'] or [1.0] * (4 * (len(s['p']) // 3))
    if len(one['p']) // 3 > 65535:
        raise Unfit('too many corners for one shape')
    return one


def convex_hull(points, snap=0.0):
    """(corners, faces anticlockwise from outside) of the smallest convex solid round points (incremental; a few hundred
    points at most). snap: corners rounded outward-ish to this grid first, so no two faces are nearly one plane (Havok's
    solid and FOLab's reader find a face's corners by a tolerance: slivers a hair apart don't read back closed)."""
    if snap:
        points = [tuple(round(c / snap) * snap for c in p) for p in points]
    P = [tuple(p) for p in {tuple(round(c, 2) for c in p) for p in points}]
    if len(P) < 4:
        raise Unfit('too few collision corners')
    sub = lambda a, b: (a[0] - b[0], a[1] - b[1], a[2] - b[2])
    cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    dot = lambda a, b: a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def normal(f):
        return cross(sub(P[f[1]], P[f[0]]), sub(P[f[2]], P[f[0]]))
    # a first tetrahedron of points well apart
    a = min(range(len(P)), key=lambda i: P[i])
    b = max(range(len(P)), key=lambda i: math.dist(P[i], P[a]))
    c = max(range(len(P)), key=lambda i: sum(x * x for x in cross(sub(P[b], P[a]), sub(P[i], P[a]))))
    nabc = cross(sub(P[b], P[a]), sub(P[c], P[a]))
    d = max(range(len(P)), key=lambda i: abs(dot(nabc, sub(P[i], P[a]))))
    if abs(dot(nabc, sub(P[d], P[a]))) < 1e-6:
        raise Unfit('collision corners all in a plane')
    faces = [(a, b, c), (a, c, d), (a, d, b), (b, d, c)]
    mid = tuple(sum(P[i][k] for i in (a, b, c, d)) / 4 for k in range(3))
    faces = [f if dot(normal(f), sub(P[f[0]], mid)) > 0 else (f[0], f[2], f[1]) for f in faces]
    def above(f, p):                # (how far over the face's plane, in game units: points within a tenth count as on it)
        n = normal(f)
        ln = math.sqrt(dot(n, n))
        return dot(n, sub(p, P[f[0]])) / ln if ln > 1e-9 else 0.0
    for i in range(len(P)):
        if i in (a, b, c, d):
            continue
        seen = [f for f in faces if above(f, P[i]) > 0.1]
        if not seen:
            continue
        edges = {}
        for f in seen:
            for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                edges[e] = edges.get(e, 0) + 1
        rim = [e for e in edges if (e[1], e[0]) not in edges]
        faces = [f for f in faces if f not in seen] + [(e[0], e[1], i) for e in rim]
    return flatten(P, faces)


def flatten(P, tris, tol=0.75):
    """A hull's triangles joined into flat faces: neighbours whose corners all lie within tol of the first one's plane
    become one face (a polygon round its rim), and corners left inside a face are dropped. Two faces nearly one plane
    otherwise read as one by Havok's and FOLab's tolerances and the solid doesn't close."""
    sub = lambda a, b: (a[0] - b[0], a[1] - b[1], a[2] - b[2])
    cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    dot = lambda a, b: a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def plane(f):
        n = cross(sub(P[f[1]], P[f[0]]), sub(P[f[2]], P[f[0]]))
        ln = math.sqrt(dot(n, n)) or 1.0
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        return n, dot(n, P[f[0]])
    tris = [tuple(f) for f in tris]
    by_edge = {}
    for f in tris:
        for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            by_edge[e] = f
    # biggest triangles seed first, so a face's plane is a well-made one
    def area(f):
        c = cross(sub(P[f[1]], P[f[0]]), sub(P[f[2]], P[f[0]]))
        return dot(c, c)
    area = {f: area(f) for f in tris}
    group = {}
    faces = []
    for seed in sorted(tris, key=lambda f: -area[f]):
        if seed in group:
            continue
        n, d = plane(seed)
        mine, todo = [seed], [seed]
        group[seed] = len(faces)
        while todo:
            f = todo.pop()
            for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                g = by_edge.get((e[1], e[0]))
                if g is None or g in group:
                    continue
                if dot(plane(g)[0], n) > 0.98 and all(abs(dot(n, P[i]) - d) <= tol for i in g):
                    group[g] = len(faces)
                    mine.append(g)
                    todo.append(g)
        rim = {}
        edges = {(f[k], f[(k + 1) % 3]) for f in mine for k in range(3)}
        for a, b in edges:
            if (b, a) not in edges:
                rim[a] = b
        start = next(iter(rim))
        loop, at = [start], rim[start]
        while at != start and len(loop) <= len(rim):
            loop.append(at)
            at = rim[at]
        faces.append(loop)
    used = sorted({i for f in faces for i in f})
    at = {i: k for k, i in enumerate(used)}
    return [P[i] for i in used], [[at[i] for i in f] for f in faces]


def merged(gd, edid):
    """(nif bytes, box, model path under meshes) of a game static in one shape, checked as FOLab's readers see it."""
    import hkshape
    f = next((f for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == edid), None)
    if f is None:
        raise Unfit('no static ' + edid)
    model = gd.describe(f)[3]
    data = gd.read_file('meshes\\' + model.replace('/', '\\'))
    one = join(shapes_of(data))
    solids = []
    cols = hkshape.collision_shapes(data)
    pts = [tuple(c.get('v')[k:k + 3]) for c in cols for k in range(0, len(c.get('v') or ()), 3)]
    if pts:
        for snap in SNAPS:                      # (the finest grid whose solid reads back closed)
            corners, faces = convex_hull(pts, snap)
            solids = [{'points': corners, 'faces': faces, 'material': 'stone'}]
            out = nifmake.build('FOLab' + edid, [one], solids)
            if not nifmake.check(out, [one], solids):
                break
    name = 'FOLab' + edid
    out = nifmake.build(name, [one], solids)
    wrong = nifmake.check(out, [one], solids)
    if wrong:
        raise Unfit('; '.join(wrong))
    xs, ys, zs = one['p'][0::3], one['p'][1::3], one['p'][2::3]
    box = (math.floor(min(xs)), math.floor(min(ys)), math.floor(min(zs)), math.ceil(max(xs)), math.ceil(max(ys)), math.ceil(max(zs)))
    return out, box, '%s\\%s.nif' % (FOLDER, edid)


def ops(gd, pr, world_cells=None, which=MERGE):
    """(ops, report): each model merged into the mod's files, a STAT of the mod's own for it (once), and every thing the
    mod stands of the game's base swapped for it (world_cells: only refs in these cell keys)."""
    import modelsets as ms
    root = library.assets_dir(pr)
    out, rep = [], {'swapped': {}, 'made': []}
    for edid in which:
        try:
            data, box, rel = merged(gd, edid)
        except Unfit as e:
            rep.setdefault('unfit', {})[edid] = str(e)
            continue
        library._put(root, 'meshes\\' + rel, data)
        name = 'FOLab' + edid
        key = next((k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'STAT'
                    and recordio.field(r, 'EDID') == name), None)
        if not key:
            out.append({'op': 'record_new', 'record': ms._static(name, rel, box), 'name': 'one_' + edid})
            key = '$one_' + edid
            rep['made'].append(name)
        game = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == edid))
        n = 0
        for ck, c in pr.cells.items():
            if world_cells is not None and ck not in world_cells:
                continue
            for rk, r in c.get('refs', {}).items():
                if rk.startswith('+') and r.get('base') == game and not r.get('removed'):     # (only the mod's own things)
                    out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': key})
                    n += 1
        rep['swapped'][edid] = n
    return out, rep


def sig_of(gd, pr, ck):
    import navbuild
    refs = navbuild.place_refs(gd, pr, ck)
    return navbuild.outside_signature(pr, ck, refs) if navbuild.is_outside(gd, ck) else navbuild.signature(refs)


def apply(gd, pr, label='Rubble and clutter drawn in one piece', which=MERGE):
    """ops applied as one Undo; navmeshes that were current before stay marked current (the pile is where it was, its
    collision the same mound). Returns the report."""
    o, rep = ops(gd, pr, which=which)
    cells = {x['cell'] for x in o if x['op'] == 'swap'}
    current = {k: m for k, m in pr.navmesh.items() if k in cells and m.get('sig') == sig_of(gd, pr, k)}
    pr.apply(label, o)
    nav = [{'op': 'navmesh', 'cell': k, 'mesh': dict(m, sig=sig_of(gd, pr, k))} for k, m in current.items()]
    if nav:
        pr.apply(label, nav, merge=True)
    rep['cells'] = len(cells)
    rep['navmeshes_kept_current'] = len(nav)
    return rep
