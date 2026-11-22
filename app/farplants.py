"""Far plants enough to read as growth (farplants.py): the distant view of a green world, not every plant.

Past the loaded cells only the far ground and the distant blocks (lodobj.py) are drawn, and a block holds a thing only if
its model has a far version (<model>_lod.nif). plantfar.py gives FOLab's own trees one; everything else that grows (the
game's ficus, birches, Zion's trees and FOLab's green copies of them, shrubs, heliconia, hibiscus...) had none, and the game's
palms and Zion trees that have one were left out by lodobj's TREE_WORDS. From a hill the far slopes stood bare with a lone
tree here and there, all one size (the user, 21 Nov 2026: "should be a little denser though, maybe offer a few more sizes to
break monotony and big open stretches on distant landscapes"; "they don't need to draw ALL the far plants, just enough to
give the illusion of foliation. break up too smooth of landscapes in distance, edges of horizon").

So:
  far_model(gd, model)     a far version of any plant's model, from its own near shapes: the crown as masses fitted to its
                           leaves (plantfar's, so near and far are one size and shape), a trunk, a few boughs and some
                           hanging vines for a tree; low masses for a shrub. One picture per plant, its leaves' colour.
  pick(gd, items)          which plants the distant blocks show: one in each PATCH square (the tallest there), a second
                           where the ground is steep or high (ridges and slopes are what break a smooth far hill and the
                           skyline), and every one taller than ALWAYS. Things not plants pass untouched.
  files(gd, pr, world)     every far model the picked plants need that neither the game nor the mod has: {path: bytes}.

What reads as a plant is the model's own shapes (see-through leaves) and words (PLANT_WORDS); ground cover lower than
LOW at its usual size gets nothing (the far ground's green, farfoliage, is it)."""
import math
import re

import nif
import nifmake
import plantfar as pf

PATCH = 1280.0                  # one far plant in a square this wide (~3 x 3 a cell): enough to read as growth from afar,
#                                 and the densest blocks stay under their 65,535 triangles (at 768 they needed 110,000)
STEEP = 0.35                    # a patch whose ground rises more than this per unit gets a second
ALWAYS = 1100.0                 # a plant taller than this always shows (a big tree is a landmark)
LOW = 90.0                      # ground cover under this tall (at its usual size) is the far ground's green
TREE = 330.0                    # taller than this with wood of its own: a tree (trunk, boughs, vines); else a shrub
PLANT_WORDS = re.compile(r'tree|palm|banyan|bamboo|fern|shrub|bush|taro|heliconia|hibiscus|banana|ficus|sassafras|birch|'
                         r'mesquite|juniper|willow|cypress|oak|pine|plant|jungle|leaves|ti_|tired|tigreen|bloom|agave', re.I)
NOT_PLANT = re.compile(r'grass|weed|flower|log|stump|dead|rock|fungus|mushroom', re.I)
VINE = 'jungle/far_vine'         # (modelsets' name of the vines' own picture: a crown measures without them)
VINES = 3                       # vines hanging from a far tree's crown (the user: "a couple vines hanging from some")
TEX = 'textures\\folab\\far\\%s.dds'
BARK = TEX % 'bark'
_bark = {}


_pics = {}


def _small_canopy(colour):
    """A far crown's picture, 64 square: plantfar's leaf clumps, fewer and smaller."""
    old = pf.CLUMPS
    pf.CLUMPS = 70
    try:
        c = pf._canopy_of(colour, 41 + sum(colour))()
    finally:
        pf.CLUMPS = old
    import texpaint as tp
    small = tp.Canvas(64, 64)
    for y in range(64):
        for x in range(64):
            small.rgb[y * 64 + x] = c.rgb[(2 * y) * 128 + 2 * x]
    return small


def _bark_files():
    """The far trunks' one bark: grey-brown, a little streaked, 64 square."""
    if not _bark:
        import texpaint as tp
        c = tp.Canvas(64, 64)
        n = tp.Noise(7, 8)
        c.paint(lambda x, y: (tp._shade((74, 62, 50), 0.75 + 0.35 * n.at(x / 8.0, y / 8.0)), 0.5))
        col, nm = c.files(game=True, shine=4)
        _bark[BARK], _bark[TEX % 'bark_n'] = col, nm
    return dict(_bark)


def _slug(model):
    return re.sub(r'[^a-z0-9]+', '_', model.lower().replace('.nif', ''))[-48:].strip('_')


def near_shapes(gd, model):
    """The near model's shapes (game or the mod's own, through the overlay), or None."""
    path = 'meshes\\' + model.lstrip('\\').replace('/', '\\')
    try:
        data = gd.read_file(path)
        return [s for s in nif.mesh_from_nif(data) if s['p'] and s['i']] if data else None
    except Exception:
        return None


def is_plant(edid, model):
    words = (edid or '') + ' ' + (model or '')
    return bool(PLANT_WORDS.search(words)) and not NOT_PLANT.search(words)


def _leaf_colour(gd, leaf):
    """The mean colour of the leaves' pictures where they show, a little darker for distance."""
    import dds
    tot, n = [0.0, 0.0, 0.0], 0.0
    for tex in {s['tex'] for s in leaf if s.get('tex')}:
        k = tex.lower().replace('/', '\\')
        if not k.startswith('textures\\'):
            k = 'textures\\' + k
        try:
            got = dds.decode(gd.read_file(k), 32)
        except Exception:
            got = None
        if not got:
            continue
        w, h, px = got[:3]
        for i in range(0, w * h * 4, 4):
            a = px[i + 3] / 255.0
            if a < 0.5:
                continue
            tot[0] += px[i] * a; tot[1] += px[i + 1] * a; tot[2] += px[i + 2] * a; n += a
    if not n:
        return (54, 86, 40)
    return tuple(v / n * 0.85 for v in tot)


def _vines(lumps, tex, normal, seed):
    """A few vines hanging from the undersides of the crown's lower masses: thin three-sided strands, a little sway, what
    breaks the crown's flat underside from afar."""
    import random
    rnd = random.Random(seed)
    P, N, UV, I = [], [], [], []
    SEG, SIDES = 3, 3
    for gx, gy, gz, sx, sy, sz in sorted(lumps, key=lambda g: g[2])[:VINES]:
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.3, 0.75)
        tx, ty, tz = gx + math.cos(a) * sx * r, gy + math.sin(a) * sy * r, gz - sz * 0.45
        long = rnd.uniform(0.6, 1.3) * max(120.0, sz * 1.6)
        sway = rnd.uniform(-0.15, 0.15) * long
        base = len(P) // 3
        for j in range(SEG + 1):
            t = j / SEG
            cx, cy, cz = tx + sway * t * t * math.cos(a), ty + sway * t * t * math.sin(a), tz - long * t
            w = 7.0 * (1 - t) + 2.5
            for i in range(SIDES + 1):
                q = 2 * math.pi * i / SIDES
                ox, oy = math.cos(q) * w, math.sin(q) * w
                P += [cx + ox, cy + oy, cz]
                N += [math.cos(q), math.sin(q), 0.0]
                UV += [i / SIDES * 0.2, 0.75 + t * 0.25]
        for j in range(SEG):
            for i in range(SIDES):
                v = base + j * (SIDES + 1) + i
                I += [v, v + SIDES + 1, v + 1, v + 1, v + SIDES + 1, v + SIDES + 2]
    if not P:
        return None
    return {'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': normal, 'gloss': 10.0, 'alpha': False, 'glow': '', 'glow_mult': 1.0}


def _tube(a, b, r0, r1, tex, normal, sides=5):
    P, N, UV, I = [], [], [], []
    d = [b[k] - a[k] for k in range(3)]
    L = math.sqrt(sum(v * v for v in d)) or 1.0
    ax, ay, az = (v / L for v in d)
    ux, uy, uz = (-ay, ax, 0.0) if abs(az) < 0.95 else (1.0, 0.0, 0.0)
    ul = math.sqrt(ux * ux + uy * uy + uz * uz)
    ux, uy, uz = ux / ul, uy / ul, uz / ul
    vx, vy, vz = ay * uz - az * uy, az * ux - ax * uz, ax * uy - ay * ux
    for e, (p, r) in enumerate(((a, r0), (b, r1))):
        for q in range(sides + 1):
            t = 2 * math.pi * q / sides
            ox, oy, oz = (ux * math.cos(t) + vx * math.sin(t), uy * math.cos(t) + vy * math.sin(t), uz * math.cos(t) + vz * math.sin(t))
            P += [p[0] + ox * r, p[1] + oy * r, p[2] + oz * r]
            N += [ox, oy, oz]
            UV += [q / sides, e * L / 256.0]
    for q in range(sides):
        I += [q, q + sides + 1, q + 1, q + 1, q + sides + 1, q + sides + 2]
    return {'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': normal, 'gloss': 10.0, 'alpha': False, 'glow': '', 'glow_mult': 1.0}


def far_model(gd, model):
    """(nif bytes, {texture path: bytes}, kind) of a plant's far version, or None when it has no leaves to stand for."""
    shapes = near_shapes(gd, model)
    if not shapes:
        return None
    leaf = [s for s in shapes if s.get('alpha') and 'vine' not in (s.get('tex') or '').lower()] or [s for s in shapes if s.get('alpha')]
    wood = [s for s in shapes if not s.get('alpha')]
    if not leaf:
        leaf, wood = shapes, []                         # (a plant drawn without see-through: itself as the mass)
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for s in leaf for k in range(0, len(s['p']), 3)]
    zs = [q[2] for q in pts]
    tall = max(zs + [q for s in wood for q in s['p'][2::3]])
    if tall < 20:
        return None
    is_tree = bool(wood) and tall >= TREE
    if 'palm' in model.lower() and wood:
        return _far_palm(gd, model, leaf, wood, pts, tall)
    span = max(max(q[0] for q in pts) - min(q[0] for q in pts), max(q[1] for q in pts) - min(q[1] for q in pts))
    k = max(2, min(4, int(span / 220) + 2)) if is_tree else max(1, min(2, int(span / 160) + 1))
    groups = pf._clusters(list(pts), k) or [pts]
    lumps = []
    for g in groups:
        gx, gy, gz = (sum(q[d] for q in g) / len(g) for d in range(3))
        sx = max(12.0, (sum((q[0] - gx) ** 2 for q in g) / len(g)) ** 0.5 * 1.9)
        sy = max(12.0, (sum((q[1] - gy) ** 2 for q in g) / len(g)) ** 0.5 * 1.9)
        sz = max(10.0, (sum((q[2] - gz) ** 2 for q in g) / len(g)) ** 0.5 * 1.3)
        lumps.append((gx, gy, gz, sx, sy, sz))
    lumps = pf._fit(lumps, pts)
    slug = _slug(model)
    colour = _leaf_colour(gd, leaf)
    tone = tuple(int(v // 12) * 12 + 6 for v in colour)          # (plants of nearly one green share a picture)
    tname = 'canopy_%02x%02x%02x' % tone
    tex, nor = TEX % tname, TEX % (tname + '_n')
    # (cheap: a far block holds 65,535 triangles and a world stands tens of thousands of these)
    out = [pf._smooth_crown(None, tex, nor, lumps=lumps, ring=3, round_=5 if is_tree else 4)]
    if is_tree:
        foot = [(s['p'][k], s['p'][k + 1]) for s in wood for k in range(0, len(s['p']), 3) if s['p'][k + 2] < 60] or [(0.0, 0.0)]
        fx, fy = sum(p[0] for p in foot) / len(foot), sum(p[1] for p in foot) / len(foot)
        low = min(g[2] - g[5] * 0.5 for g in lumps)
        bark = BARK                     # (one small bark for every far trunk: the game's own barks filled the sheet)
        r0 = max(8.0, min(50.0, max(math.hypot(p[0] - fx, p[1] - fy) for p in foot) * 0.7))
        trunk = _tube((fx, fy, -pf.DOWN), (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts), low), r0, r0 * 0.65, bark, '')
        bough = pf._boughs(None, (trunk['p'][-3], trunk['p'][-2], low), bark, '', lumps=lumps)
        out.append(pf._merge(trunk, bough) if bough else trunk)
        import modelsets as ms
        v = _vines(lumps, ms.tex_path(VINE), ms.tex_path(VINE, True), len(slug))
        if v:
            out.append(v)
    else:
        # (a shrub stands on the ground: its masses let down to it, no stem)
        low = min(g[2] - g[5] * pf.UNDER for g in lumps)
        if low > 0:
            out[0]['p'] = [v - low * 0.8 if i % 3 == 2 else v for i, v in enumerate(out[0]['p'])]
    import modelsets as ms
    if tname not in _pics:
        _pics[tname] = _small_canopy(tone).files(game=True, shine=8)
    col, nmap = _pics[tname]
    data = nifmake.build('FOLabFar' + slug[-24:], [s for s in out if s])
    out_files = {tex: col, nor: nmap}
    if is_tree:
        out_files.update(_bark_files())
        import modelsets as ms
        out_files[ms.tex_path(VINE)], out_files[ms.tex_path(VINE, True)] = ms.texture_files(VINE)
    return data, out_files, 'tree' if is_tree else 'shrub'


def _vine_picture():
    """The far vines' picture: dark leafy green, streaked down."""
    import texpaint as tp
    c = tp.Canvas(32, 32)
    n = tp.Noise(9, 4)
    c.paint(lambda x, y: (tp._shade((40, 66, 30), 0.7 + 0.45 * n.at(x / 8.0, y / 32.0 * 4)), 0.5))
    return c


def _register():
    import modelsets as ms
    if VINE not in ms.TEXTURES:
        ms.TEXTURES[VINE] = _vine_picture


_register()


FRONDS = 7                      # (a far palm: 7 fronds of 3 segments, 3 sides: ~110 corners; plantfar's 11 x 6 x 4 was ~400,
#                                 and 6,000 game palms in the far view left 8,533 smaller things out of full blocks)


def _fronds(cx, cy, cz, reach, tex, normal):
    """A palm's crown far off: fronds from the crown out and drooping, flattened tubes tapering to the tip."""
    P, N, UV, I = [], [], [], []
    SEG, SIDES = 3, 3
    for k in range(FRONDS):
        a = math.radians(k * 360 / FRONDS + 11 * (k % 2))
        up, drop = (0.3, 0.55) if k % 2 else (0.1, 0.8)
        base = len(P) // 3
        for j in range(SEG + 1):
            t = j / SEG
            h = reach * (up * math.sin(t * math.pi) - drop * t * t)
            px, py, pz = cx + math.cos(a) * reach * t, cy + math.sin(a) * reach * t, cz + h
            r = 28 * (1 - t) + 5
            for i in range(SIDES + 1):
                q = 2 * math.pi * i / SIDES
                ox, oy, oz = -math.sin(a) * math.cos(q) * r * 1.7, math.cos(a) * math.cos(q) * r * 1.7, math.sin(q) * r * 0.5
                P += [px + ox, py + oy, pz + oz]
                L = math.sqrt(ox * ox + oy * oy + oz * oz) or 1.0
                N += [ox / L, oy / L, oz / L]
                UV += [i / SIDES, t]
        for j in range(SEG):
            for i in range(SIDES):
                v = base + j * (SIDES + 1) + i
                I += [v, v + SIDES + 1, v + 1, v + 1, v + SIDES + 1, v + SIDES + 2]
    return {'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': normal, 'gloss': 10.0, 'alpha': False, 'glow': '', 'glow_mult': 1.0}


def _far_palm(gd, model, leaf, wood, pts, tall):
    """A palm's far version: its trunk from the foot to the crown, and fronds drooping from the crown (plantfar's)."""
    slug = _slug(model)
    top = sorted(pts, key=lambda q: -q[2])[:max(10, len(pts) // 5)]
    cx, cy, cz = (sum(q[d] for q in top) / len(top) for d in range(3))
    reach = max(30.0, max(math.hypot(q[0] - cx, q[1] - cy) for q in pts))
    colour = _leaf_colour(gd, leaf)
    tone = tuple(int(v // 12) * 12 + 6 for v in colour)
    tname = 'canopy_%02x%02x%02x' % tone
    tex, nor = TEX % tname, TEX % (tname + '_n')
    fronds = _fronds(cx, cy, cz, reach, tex, nor)
    foot = [(s['p'][k], s['p'][k + 1]) for s in wood for k in range(0, len(s['p']), 3) if s['p'][k + 2] < 60] or [(cx, cy)]
    fx, fy = sum(p[0] for p in foot) / len(foot), sum(p[1] for p in foot) / len(foot)
    r0 = max(8.0, min(30.0, max(math.hypot(p[0] - fx, p[1] - fy) for p in foot) * 0.8))
    trunk = _tube((fx, fy, -pf.DOWN), (cx, cy, cz), r0, r0 * 0.7, BARK, '')
    if tname not in _pics:
        _pics[tname] = _small_canopy(tone).files(game=True, shine=8)
    col, nmap = _pics[tname]
    files = {tex: col, nor: nmap}
    files.update(_bark_files())
    return nifmake.build('FOLabFar' + slug[-24:], [fronds, trunk]), files, 'tree'


# ---------- which plants show far off ----------

def height_of(gd, model, _seen={}):
    """How tall a model is (its own shapes' highest corner), cached."""
    k = (model or '').lower()
    if k not in _seen:
        sh = near_shapes(gd, k) if k.endswith('.nif') else None
        _seen[k] = max((v for s in sh for v in s['p'][2::3]), default=0.0) if sh else 0.0
    return _seen[k]


def pick(gd, items, model_of, edid_of, ground=None):
    """items: [(base, x, y, z, rz, s, ...)]. Returns the items to show: everything not a plant, and of the plants one in
    each PATCH square (the tallest), a second on steep ground, and every one over ALWAYS tall. model_of(base) and
    edid_of(base) name it; ground(x, y) is the land's height (None: no steepness, one a patch)."""
    keep, best = [], {}
    for it in items:
        base, x, y, z, s = it[0], it[1], it[2], it[3], it[5]
        model = model_of(base) or ''
        if not is_plant(edid_of(base), model):
            keep.append(it)
            continue
        h = height_of(gd, model) * s
        if h < LOW:
            continue
        if h >= ALWAYS:
            keep.append(it)
            continue
        cell = (int(math.floor(x / PATCH)), int(math.floor(y / PATCH)))
        best.setdefault(cell, []).append((h, it))
    for (cx, cy), got in best.items():
        got.sort(key=lambda q: -q[0])
        n = 1
        if len(got) > 1:
            if ground is not None:
                x0, y0 = (cx + 0.5) * PATCH, (cy + 0.5) * PATCH
                try:
                    dz = max(abs(ground(x0 + PATCH / 2, y0) - ground(x0 - PATCH / 2, y0)), abs(ground(x0, y0 + PATCH / 2) - ground(x0, y0 - PATCH / 2)))
                except Exception:
                    dz = 0.0
            else:
                zs = [it[3] for _h, it in got]          # (the plants' own feet say how the ground falls across the patch)
                dz = max(zs) - min(zs)
            if dz / PATCH > STEEP:
                n = 2
        keep += [it for _h, it in got[:n]]
    return keep


def usable(shapes):
    """A far model the distant blocks can draw: there, and nothing of it see-through. The game's far palms and Zion trees are
    see-through cards (NVQueenPalmLOD.dds, alpha test), made for the game's own far view; a block has no see-through, so each
    card showed as a solid grey upright rectangle (the user, 21 Nov 2026: 4,049 queen palms round Hanauma Bay). Those plants
    get FOLab's own far model at that path; the game reads the _lod files only when far views are made, never in play."""
    return bool(shapes) and not any(q.get('alpha') for q in shapes)


def files(gd, pr, world, put, progress=None, mine=None):
    """Every far model the world's picked plants need that neither the game nor the mod has, made and handed to
    put(path, bytes) (the mod's own files). mine(path): True for a far model farplants made before (made again). Returns {'made': n, 'trees': n, 'shrubs': n, 'none': [models]}."""
    import lodobj
    stand = lodobj.StandIns(gd, pr)
    items = lodobj.things_of(gd, pr, world)
    models = {}
    for it in items:
        b = it[0]
        if b not in models:
            stand.of(b)
            models[b] = stand.models.get(b) or ''
    want = {}
    for it in pick(gd, items, models.get, lambda b: _name(gd, pr, b)):
        m = (models.get(it[0]) or '').lower().replace('/', '\\')
        if m.endswith('.nif') and is_plant(_name(gd, pr, it[0]), m) and (not usable(stand.of_model(m)) or (mine and mine('meshes\\' + m[:-4] + '_lod.nif'))):
            want[m] = want.get(m, 0) + 1
    rep = {'made': 0, 'tree': 0, 'shrub': 0, 'none': []}
    for n, m in enumerate(sorted(want)):
        if progress:
            progress(n, len(want))
        got = far_model(gd, m)
        if not got:
            rep['none'].append(m)
            continue
        data, tex, kind = got
        put('meshes\\' + m[:-4] + '_lod.nif', data)
        for k, v in tex.items():
            put(k, v)
        rep['made'] += 1
        rep[kind] += 1
    return rep


def _name(gd, pr, base):
    if isinstance(base, str):
        import recordio
        r = pr.records.get(base) if pr else None
        return (recordio.field(r, 'EDID') or '') if r else ''
    try:
        return gd.edid(base) or ''
    except Exception:
        return ''
