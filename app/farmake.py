"""Far versions made from a model's own mesh, for what has nothing better: the game's trucks, boats, shacks, tents and
rubble piles a mod places, FOLab's rubble heaps and lava rocks (whose parts close only together, so modelsets.auto_far
can't pick from them). The user, 24 Nov 2026: "all missing things need far off versions so there arent gaps in the
exploration experience".

What one is: convex solids round the model's parts (one round the whole where that is close to its shape; round each
part where the whole would fill in what is open, a pen's walls round its yard), each closed, its corners rounded to a
grid coarse enough that it comes to `budget` triangles. Each face is coloured as the model is there: the faces of the
model nearest it, facing its way, averaged over their own pictures. The colours are swatches of one picture every far
version shares (`PALETTE`, a fixed palette, so versions made apart still agree), so in the distant blocks they all take
one square of the sheet (lodobj.Sheet).

Where a game model's far version goes: `meshes\\folab\\far\\<its path under meshes>` with `_lod` on its name (lodobj
looks there when the game ships none; nothing is written under the game's own paths)."""
import math

import dds
import nifmake
import onepiece

PALETTE = 'textures\\folab\\far\\palette.dds'
FAR_DIR = 'meshes\\folab\\far\\'
LEVELS = 16                 # brightness steps (across the palette)
# (blue-yellow, red-green) tints, one a row down it: grey first, then what the island is made of (rust and wood browns,
# sand, olive and leaf greens, blue-greys, brick and lacquer reds). A grid of steps had no grey: grey tin came out green.
TINTS = ((0.0, 0.0), (-5.0, 5.0), (-11.0, 10.0), (-19.0, 17.0), (-28.0, 26.0), (-38.0, 34.0), (-10.0, 2.0), (-22.0, 6.0),
         (-14.0, -8.0), (-26.0, -18.0), (6.0, -5.0), (14.0, -10.0), (26.0, -16.0), (-8.0, 22.0), (-16.0, 42.0), (8.0, 6.0))
SWATCH = 16                 # pixels a swatch
SPLIT = 1.6                 # split only when the pieces hold this many times less space than one solid round all
SHARE = 0.6                 # (a split into its own parts only when they hold this much of its surface)
PART_LEAST = 0.1            # a part kept on its own at least this share of the model's size
GROUND = -16.0              # what lies wholly under this is left out (a heap's skirt, footings)


def far_path(model):
    """Where a game model's far version is kept, by its path under meshes."""
    low = model.lower().replace('/', '\\')
    if low.startswith('meshes\\'):
        low = low[7:]
    return FAR_DIR + low[:-4] + '_lod.nif'


# ---------- the palette ----------

def _rgb(y, cb, cr):
    return tuple(max(0, min(255, int(round(v)))) for v in (y + 1.402 * cr, y - 0.344 * cb - 0.714 * cr, y + 1.772 * cb))


def swatch(rgb):
    """The palette's swatch nearest a colour: (column, row)."""
    r, g, b = rgb
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb, cr = (b - y) / 1.772, (r - y) / 1.402
    col = max(0, min(LEVELS - 1, int(round((y - 8.0) / 16.0))))
    return col, min(range(len(TINTS)), key=lambda k: (TINTS[k][0] - cb) ** 2 + (TINTS[k][1] - cr) ** 2)


def swatch_uv(rgb):
    col, row = swatch(rgb)
    n = LEVELS * SWATCH
    return (col * SWATCH + SWATCH / 2.0) / n, (row * SWATCH + SWATCH / 2.0) / n


def palette_files():
    """{path: bytes}: the palette picture and its flat bumps."""
    n = LEVELS * SWATCH
    px = bytearray(n * n * 4)
    for row in range(16):
        cb, cr = TINTS[row]
        for col in range(LEVELS):
            c = _rgb(8.0 + 16.0 * col, cb, cr)
            for y in range(row * SWATCH, (row + 1) * SWATCH):
                for x in range(col * SWATCH, (col + 1) * SWATCH):
                    o = (y * n + x) * 4
                    px[o:o + 4] = bytes((c[0], c[1], c[2], 255))
    flat = bytes((128, 128, 255, 255)) * (64 * 64)
    return {PALETTE: dds.encode(n, n, bytes(px)), PALETTE[:-4] + '_n.dds': dds.encode(64, 64, flat)}


# ---------- the model's own colours ----------

class Pictures:
    """Each texture's colours, small, read once. read: fn(path) -> DDS bytes or None."""

    def __init__(self, read):
        self.read = read
        self.got = {}

    def at(self, tex, u, v):
        if tex not in self.got:
            pic = None
            try:
                data = self.read(tex) if tex else None
                pic = dds.decode(data, 32) if data else None
            except Exception:
                pic = None
            self.got[tex] = pic
        pic = self.got[tex]
        if not pic:
            return None
        w, h, rgba = pic[0], pic[1], pic[2]
        x, y = int((u % 1.0) * w) % w, int((v % 1.0) * h) % h
        o = (y * w + x) * 4
        return rgba[o], rgba[o + 1], rgba[o + 2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def triangles(shapes, pics):
    """The model's triangles over the ground as (corners, centre, normal, area, colour or None, part key)."""
    out = []
    for si, s in enumerate(shapes):
        if s.get('alpha') == 'blend' or not s.get('i'):
            continue
        P, I, UV = s['p'], s['i'], s.get('uv') or []
        for k in range(0, len(I) - 2, 3):
            a, b, c = (tuple(P[3 * j:3 * j + 3]) for j in I[k:k + 3])
            if max(a[2], b[2], c[2]) < GROUND:
                continue
            n = _cross(_sub(b, a), _sub(c, a))
            ar = math.sqrt(_dot(n, n)) / 2.0
            if ar < 1e-3:
                continue
            n = tuple(v / (2 * ar) for v in n)
            col = None
            if UV:
                u = sum(UV[2 * j] for j in I[k:k + 3]) / 3.0
                v = sum(UV[2 * j + 1] for j in I[k:k + 3]) / 3.0
                col = pics.at(s.get('tex'), u, v)
            out.append(((a, b, c), tuple((a[q] + b[q] + c[q]) / 3.0 for q in range(3)), n, ar, col, si))
    return out


def _parts(tris):
    """The model's pieces that touch: triangles sharing a corner (welded by position) are one part."""
    up = {}

    def find(x):
        while up.get(x, x) != x:
            up[x] = up.get(up[x], up[x])
            x = up[x]
        return x
    key = lambda p: (round(p[0]), round(p[1]), round(p[2]))
    for t in tris:
        ks = [key(p) for p in t[0]]
        r = find(ks[0])
        for q in ks[1:]:
            rq = find(q)
            if rq != r:
                up[rq] = r
    groups = {}
    for t in tris:
        groups.setdefault(find(key(t[0][0])), []).append(t)
    return list(groups.values())


_DIRS = []


def _directions(n=260):
    """n directions spread evenly round a sphere (a Fibonacci spiral)."""
    if not _DIRS:
        g = math.pi * (3.0 - math.sqrt(5.0))
        for k in range(n):
            z = 1.0 - 2.0 * (k + 0.5) / n
            r = math.sqrt(max(0.0, 1.0 - z * z))
            _DIRS.append((r * math.cos(g * k), r * math.sin(g * k), z))
    return _DIRS


def _extremes(pts):
    """The points furthest out each of _directions' ways: what a hull round them all is nearly made of (a big model has
    thousands of corners, and the hull is built a point at a time)."""
    if len(pts) <= 300:
        return pts
    keep = set()
    for d in _directions():
        keep.add(max(range(len(pts)), key=lambda i: pts[i][0] * d[0] + pts[i][1] * d[1] + pts[i][2] * d[2]))
    return [pts[i] for i in keep]


def _hull(points, budget, ext):
    """(corners, faces) of a convex solid round points, coarse enough to come to budget triangles; None if flat."""
    pts = _extremes(list({(round(p[0], 1), round(p[1], 1), round(p[2], 1)) for p in points}))
    got = None
    for div in (40.0, 28.0, 20.0, 14.0, 10.0, 7.0, 5.0):
        g = max(2.0, ext / div)
        try:
            got = onepiece.convex_hull(pts, snap=g)
        except Exception:
            continue                            # (rounded flat at this grid: a coarser one may still hold it)
        if sum(len(f) - 2 for f in got[1]) <= budget:
            return got
    if got is None:
        try:
            got = onepiece.convex_hull(pts, snap=0.5)
        except Exception:
            return None
    return got


def _volume(P, F):
    v = 0.0
    for f in F:
        for k in range(1, len(f) - 1):
            v += _dot(P[f[0]], _cross(P[f[k]], P[f[k + 1]])) / 6.0
    return abs(v)


def _ext(group):
    return max(max(p[q] for t in group for p in t[0]) - min(p[q] for t in group for p in t[0]) for q in range(3))


def _round_each(groups, budget):
    """A solid round each group of triangles, sharing the budget by size; a flat group (a panel, a slab) thickened a
    little along its facing first. None if one can't be made."""
    total = sum(_ext(g) for g in groups) or 1.0
    out = []
    for g in groups:
        pts = [p for t in g for p in t[0]]
        share = max(12, int(budget * _ext(g) / total))
        h = _hull(pts, share, _ext(g))
        if h is None:
            n = [sum(t[2][q] * t[3] for t in g) for q in range(3)]
            ln = math.sqrt(_dot(n, n)) or 1.0
            d = 2.0 + 0.06 * _ext(g)            # (thicker than _hull's grid rounds away)
            n = [v / ln * d for v in n]
            h = _hull(pts + [(p[0] - n[0], p[1] - n[1], p[2] - n[2]) for p in pts], share, _ext(g))
        if h is None:
            return None
        out.append(h)
    return out


def _biggest(parts, share):
    """The fewest of the model's parts, biggest by surface first, that hold `share` of it."""
    area = sum(t[3] for g in parts for t in g) or 1.0
    got, held = [], 0.0
    for g in sorted(parts, key=lambda g: -sum(t[3] for t in g)):
        if held >= share * area:
            break
        got.append(g)
        held += sum(t[3] for t in g)
    return got


def _grid(tris, lo, hi):
    """The triangles in two halves along each long way (and up, for something tall), by where each one's middle is."""
    span = [hi[q] - lo[q] for q in range(3)]
    cuts = [q for q in range(3) if span[q] >= 0.6 * max(span)]
    groups = {}
    for t in tris:
        k = tuple(int(t[1][q] > (lo[q] + hi[q]) / 2) if q in cuts else 0 for q in range(3))
        groups.setdefault(k, []).append(t)
    return [g for g in groups.values() if len(g) >= 2]


SLIGHT = 0.005              # a part this little of the surface,
STICK = 0.12                # no wider than this share of the model's size across its middle way (a mast, an aerial, a rope),
SLIGHT_MOST = 0.1           # is left out of the hull, so long as what's left out comes to no more than this of the surface


def unslight(tris):
    """The triangles without the model's slight sticking-out parts: a boat's radio mast and wires drew its hull up to a
    point, a tan pyramid by the Flotilla (the user, 26 Nov 2026). A part goes if it is little of the surface and thin
    two ways (a stick), whatever its length; nothing goes if that would take more than SLIGHT_MOST."""
    if not tris:
        return tris
    allp = [p for t in tris for p in t[0]]
    ext = max(max(p[q] for p in allp) - min(p[q] for p in allp) for q in range(3)) or 1.0
    area = sum(t[3] for t in tris) or 1.0
    gone = set()
    held = 0.0
    for g in _parts(tris):
        a = sum(t[3] for t in g)
        if a > SLIGHT * area:
            continue
        spans = sorted(max(p[q] for t in g for p in t[0]) - min(p[q] for t in g for p in t[0]) for q in range(3))
        if spans[1] < STICK * ext:
            gone.update(id(t) for t in g)
            held += a
    if not gone or held > SLIGHT_MOST * area or len(gone) == len(tris):
        return tris
    return [t for t in tris if id(t) not in gone]


def solids(tris, budget):
    """The convex solids a far version is made of: [(corners, faces)]. One round the whole; or round each part it is
    made of, if those parts hold nearly all of it (SHARE); or round each quarter of it: whichever holds least space
    beyond the model (a pen's yard, a ruin's open side), so long as it comes to twice the budget at most, and one
    solid unless splitting saves more than SPLIT times the space."""
    allp = [p for t in tris for p in t[0]]
    lo = [min(p[q] for p in allp) for q in range(3)]
    hi = [max(p[q] for p in allp) for q in range(3)]
    ext = max(hi[q] - lo[q] for q in range(3))
    whole = _hull(allp, budget, ext)
    if whole is None:
        return []
    area = sum(t[3] for t in tris) or 1.0
    options = []
    # (its own parts, biggest by surface first, as many as the budget holds: a ruin's standing walls)
    parts = sorted([g for g in _parts(tris) if _ext(g) >= PART_LEAST * ext], key=lambda g: -sum(t[3] for t in g))
    parts = parts[:max(2, 2 * budget // 16)]       # (a small solid comes to 12 to 18 triangles)
    if len(parts) >= 2 and sum(t[3] for g in parts for t in g) >= SHARE * area:
        options.append(_round_each(parts, budget))
    grid = _grid(tris, lo, hi)
    if len(grid) >= 2:
        options.append(_round_each(grid, budget))
    best, bv = [whole], _volume(*whole) / SPLIT
    for got in options:
        if not got or sum(sum(len(f) - 2 for f in F) for _P, F in got) > 2 * budget:
            continue
        v = sum(_volume(*h) for h in got)
        if v < bv:
            best, bv = got, v
    return best


def colour_faces(P, F, tris):
    """Each face's colour: the model's triangles facing its way, given to the face whose plane they lie nearest under."""
    planes = []
    for f in F:
        n = _cross(_sub(P[f[1]], P[f[0]]), _sub(P[f[2]], P[f[0]]))
        ln = math.sqrt(_dot(n, n)) or 1.0
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        planes.append((n, _dot(n, P[f[0]])))
    sums = [[0.0, 0.0, 0.0, 0.0] for _ in F]
    every = [0.0, 0.0, 0.0, 0.0]
    for _c, mid, n, ar, col, _s in tris:
        if col is None:
            continue
        for q in range(3):
            every[q] += col[q] * ar
        every[3] += ar
        best, bd = None, 1e18
        for k, (pn, d) in enumerate(planes):
            facing = _dot(pn, n)
            if facing < 0.2:
                continue
            gap = abs(d - _dot(pn, mid)) / facing
            if gap < bd:
                best, bd = k, gap
        if best is not None:
            w = ar * _dot(planes[best][0], n)
            for q in range(3):
                sums[best][q] += col[q] * w
            sums[best][3] += w
    fall = tuple(every[q] / every[3] for q in range(3)) if every[3] else (110.0, 104.0, 96.0)
    return [tuple(s[q] / s[3] for q in range(3)) if s[3] else fall for s in sums]


def far_shapes(shapes, read, budget):
    """A far version's shapes (one, on the palette) from a model's shapes; None if nothing over the ground."""
    pics = Pictures(read)
    tris = triangles(shapes, pics)
    if not tris:
        return None
    out = {'p': [], 'n': [], 'uv': [], 'i': [], 'tex': PALETTE, 'normal': PALETTE[:-4] + '_n.dds', 'gloss': 10.0,
           'alpha': False, 'glow': '', 'glow_mult': 1.0}
    for P, F in solids(unslight(tris), budget):
        cols = colour_faces(P, F, tris)
        for f, col in zip(F, cols):
            n = _cross(_sub(P[f[1]], P[f[0]]), _sub(P[f[2]], P[f[0]]))
            ln = math.sqrt(_dot(n, n)) or 1.0
            u, v = swatch_uv(col)
            first = len(out['p']) // 3
            for i in f:
                out['p'] += list(P[i])
                out['n'] += [n[0] / ln, n[1] / ln, n[2] / ln]
                out['uv'] += [u, v]
            for k in range(1, len(f) - 1):
                out['i'] += [first, first + k, first + k + 1]
    return [out] if out['i'] else None


def make(name, shapes, read, budget):
    """{'nif', 'shapes', 'triangles', 'open'} or None."""
    got = far_shapes(shapes, read, budget)
    if not got:
        return None
    return {'nif': nifmake.build(name + 'Far', got), 'shapes': got, 'triangles': len(got[0]['i']) // 3,
            'open': nifmake.open_edges(got), 'textures': [PALETTE, PALETTE[:-4] + '_n.dds']}


def budget_for(triangles, height):
    """Triangles a far version may take: a tenth of the model's own, more for something tall, in bounds."""
    return int(max(20, min(160, triangles * 0.1, 40 + height / 8.0)))


# ---------- what a world places with no far version ----------

TALL = 200.0                # seen past the loaded cells: this high as it stands,
WIDE, LOW = 500.0, 140.0    # or this wide and this high (rubble piles, heaps),
THIN = 60.0                 # and not thinner than this both ways across (a clothesline, a pole)
# (what a solid round it would misdraw: open frames, wires, lattices; and plants, which farplants does)
NOT = ('scaffold', 'windmill', 'pole', 'flag', 'clothes', 'ropebridge', 'fence', 'wire', 'vine', 'string', 'lights',
       'sidewalk', 'swsec', 'road', 'footing', 'surf', 'edging', 'divider', 'door', 'log', 'grass', 'fxfire', 'fire', 'pipe')


def wanted(name, model, size, scale):
    """Whether a placed thing with no far version should have one. size: its model's (x, y, z) extent."""
    words = (name + ' ' + model).lower()
    if any(w in words for w in NOT):
        return False
    sx, sy, sz = (v * scale for v in size)
    if min(sx, sy) < THIN:
        return False
    return sz >= TALL or (max(sx, sy) >= WIDE and sz >= LOW)


def missing(gd, pr, world):
    """{model path under meshes (lower): {'placed', 'name', 'size', 'triangles'}} for everything the world places whose
    model has no far version but should (`wanted`), plants left to farplants."""
    import farplants
    import lodobj
    import nif
    st = lodobj.StandIns(gd, pr)
    sizes = {}
    out = {}
    for base, _x, _y, _z, _rz, s in lodobj.things_of(gd, pr, world):
        st.of(base)
        model = (st.models.get(base) or '').lower().replace('/', '\\')
        if not model.endswith('.nif') or st.of_model(model):
            continue
        name = farplants._name(gd, pr, base)
        if farplants.is_plant(name, model):
            continue
        if model not in sizes:
            sizes[model] = None
            try:
                shapes = [q for q in nif.mesh_from_nif(gd.read_file('meshes\\' + model)) if q.get('alpha') != 'blend' and q['i']]
                if shapes:
                    ext = [max(max(q['p'][a::3]) for q in shapes) - min(min(q['p'][a::3]) for q in shapes) for a in range(3)]
                    sizes[model] = (ext, sum(len(q['i']) // 3 for q in shapes))
            except Exception:
                pass
        if sizes[model] is None or not wanted(name, model, sizes[model][0], s):
            continue
        r = out.setdefault(model, {'placed': 0, 'name': name, 'size': [round(v) for v in sizes[model][0]], 'triangles': sizes[model][1]})
        r['placed'] += 1
    return out


def city_piece(model):
    """The modelsets piece of one of rooftops' city models (ramp towers, lookouts, shanties, walkways), registered
    under its name as citypieces does when it stands one; None for any other model."""
    import citypieces
    low = model.lower().replace('/', '\\')
    if not low.startswith('folab\\city\\') or not low.endswith('.nif'):
        return None
    bits = low[len('folab\\city\\'):-4].split('_')
    try:
        if bits[0] in ('ramp2', 'ramp2t'):
            return citypieces.ramp_tower(float(bits[1]), float(bits[2]), tight=bits[0] == 'ramp2t')[0]
        if bits[0] == 'lookout2':
            return citypieces.lookout(float(bits[1]))[0]
        if bits[0] == 'shanty2':
            return citypieces.shanty(int(bits[1]), int(bits[2]))[0]
        if bits[0] == 'bridge':
            return citypieces.bridge(float(bits[1]))[0]
        if bits[0] == 'leanto2':
            return citypieces.leanto(int(bits[1]))
    except Exception:
        return None
    return None


def register(models):
    """Every modelsets piece a list of models may be, registered: the sets, rooftops' city pieces by name, and the
    pieces sets register only when imported (shipway's stair tower)."""
    import modelsets
    import shipway  # noqa: F401  (the Missouri's stair tower)
    modelsets._all_sets()
    for model in models:
        city_piece(model)


def put_game(gd, pr, models):
    """Far versions of game models (not FOLab's own: those are made with their pieces, modelsets.FAR_HULL) written
    into the mod's own files at far_path, with the palette. Returns {model: triangles or None}."""
    import library
    import nif
    root = library.assets_dir(pr)

    def read(path):
        low = path.lower()
        try:
            return gd.read_file(low if low.startswith(('textures\\', 'meshes\\')) else 'textures\\' + low)
        except Exception:
            return None
    done = {}
    import modelsets
    register(models)
    pieces = {('folab\\%s\\%s.nif' % (w['set'], w['file'])).lower() for w in modelsets.PIECES.values()}
    for model in sorted(models):
        if model in pieces:
            continue                    # (made with its piece: modelsets.build, FAR_HULL or auto_far)
        try:
            shapes = nif.mesh_from_nif(gd.read_file('meshes\\' + model))
        except Exception:
            done[model] = None
            continue
        own = sum(len(q['i']) // 3 for q in shapes)
        h = max(max(q['p'][2::3]) for q in shapes if q['p'])
        got = make('FOLabFar', shapes, read, budget_for(own, h))
        if not got or got['open'] > 0.5:
            done[model] = None
            continue
        library._put(root, far_path(model), got['nif'])
        done[model] = got['triangles']
    for rel, data in palette_files().items():
        library._put(root, rel, data)
    return done
