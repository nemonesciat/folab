"""Far versions of FOLab's trees (plantfar.py): so the jungle doesn't stop at the edge of the loaded cells.

Past the cells the game has loaded nothing is drawn but the far ground and what the distant blocks hold (lodobj.py), and
a block holds a placed thing only if its model has a far version beside it (<model>_lod.nif). FOLab's plants had none,
so every tree and palm vanished a few cells off (the user, 20 Nov 2026: "trees and plants fade way too soon in game";
nv-rs's fade settings were already far out: the cut-off was the loaded edge itself).

Each of FAR_TREES gets, in its far model only ('far_only' parts, modelsets.far_of): its crown as one low egg the size and
place of its leaves, in an opaque leafy picture ('jungle/canopy_far': a block's sheet holds no see-through), and its trunk
from its foot to the crown's underside (modelsets.limb, its own bark). About 60 triangles a tree; a block is one draw
whatever it holds. Shrubs and low plants get none: the far ground's own green (farfoliage) stands for them."""
import math

import modelmake
import modelsets as ms
import texpaint as tp

FAR_TREES = ('jungle_tree', 'jungle_banyan', 'jungle_tall', 'palm_tall', 'palm_young', 'tree_fern', 'bamboo', 'banana',
             'jungle_tree_b', 'jungle_tree_c', 'jungle_banyan_b', 'jungle_banyan_c', 'jungle_tall_b', 'jungle_tall_c')
CROWN_FILL = 0.85               # the egg a little inside the leaves' box: a box's corners are air


def _canopy_far():
    c = tp.foliage(size=256, seed=41, leaves=1400, leaf=0.05)
    base = (40, 70, 34)
    for i in range(c.w * c.h):
        a = c.a[i] if c.a is not None else 1.0
        r, g, b = c.rgb[i]
        c.rgb[i] = (r * a + base[0] * (1 - a), g * a + base[1] * (1 - a), b * a + base[2] * (1 - a))
    c.a = None                                  # (opaque: the distant blocks' sheet has no see-through)
    return c


if 'jungle/canopy_far' not in ms.TEXTURES:
    ms.TEXTURES['jungle/canopy_far'] = _canopy_far


PALMS = ('palm_tall', 'palm_young')
# (masses a crown is read as: more, and smaller, follow the tree's own leaves closer: four eggs read as "simplistic", the
# user, 21 Nov 2026. Each mass has fewer corners (RING, ROUND) so a tree costs about what it did.)
LUMPS = {'jungle_banyan': 9, 'jungle_tree': 8, 'jungle_tall': 7, 'bamboo': 4, 'tree_fern': 3, 'banana': 3,
         'jungle_tree_b': 8, 'jungle_tree_c': 7, 'jungle_banyan_b': 9, 'jungle_banyan_c': 8, 'jungle_tall_b': 6, 'jungle_tall_c': 7}
DOWN = 400.0                    # (each trunk reaches this far under its foot: the far ground is coarser than the land, and
#                                 lower on a hilltop, so a far tree stood on air there: the user, 20 Nov 2026, "right idea,
#                                 but poor execution": lollipops, some floating)
_tint = {}
_fronds = {}                    # palm -> (x, y, z, reach): its crown, its fronds made in _palm_fronds
_lumps = {}                      # piece -> [(x, y, z, rx, ry, rz)]: its crown's masses, made in _smooth_crown
_crown_foot = {}                 # piece -> (x, y, z): where its trunk meets its crown


def _leaf_colour(desc):
    """The mean colour of a tree's own leaves (its see-through pictures, what shows of them), a little darker for distance."""
    paths = {ms.tex_path(n).lower(): n for n in ms.TEXTURES}
    tot, n = [0.0, 0.0, 0.0], 0.0
    for lk in desc['looks'].values():
        if not lk.get('alpha'):
            continue
        name = paths.get(lk['tex'].lower())
        if not name or name in _tint:
            continue
        c = ms.TEXTURES[name]()
        for i in range(0, c.w * c.h, 7):
            a = c.a[i] if c.a is not None else 1.0
            if a > 0.5:
                for k in range(3):
                    tot[k] += c.rgb[i][k]
                n += 1
    if not n:
        return (54, 88, 40)
    return tuple(int(v / n * 0.85) for v in tot)


# (the user, 21 Nov 2026, of the far broadleaves: "a little more texture or color ... to give them contrast, some trick
# to make them seem more treelike and less bulbous at distance". A distant block has no vertex colours and no see-through,
# so the tricks are in the picture: clumps of leaves, each lit on its top, over near-black gaps between them; and the
# crown's own light and shade, by the picture's height, since every mass is wrapped with its top at the picture's top
# and its underside at the bottom (_smooth_crown's v): sunlit above, dark under and inside.)
def _canopy_plain(colour, seed):
    """A palm's far fronds' picture: the near leaves' colour mottled (the palms looked right far off: kept as they were)."""
    def draw():
        c = tp.foliage(size=128, seed=seed, leaves=700, leaf=0.06)
        for i in range(c.w * c.h):
            a = c.a[i] if c.a is not None else 1.0
            r, g, b = c.rgb[i]
            lum = (r + g + b) / 3.0 / 128.0 if a > 0.3 else 0.7
            c.rgb[i] = tuple(min(255.0, v * (0.75 + 0.45 * lum)) for v in colour)
        c.a = None
        return c
    return draw


CLUMPS = 260                    # leaf clumps on a 128 square
GAP = 0.32                      # the gaps' colour: this share of the leaves' (near black, still green)
TOP_LIGHT, UNDER_DARK = 1.32, 0.42      # light at the top of each mass, dark at its underside


def _canopy_of(colour, seed):
    def draw():
        import random
        n = 128
        rnd = random.Random(seed)
        c = tp.Canvas(n, n, clear=tuple(v * GAP for v in colour))
        rgb = c.rgb
        for _ in range(CLUMPS):
            cx, cy = rnd.uniform(0, n), rnd.uniform(0, n)
            r = rnd.uniform(3.5, 8.5)
            tone = rnd.uniform(0.72, 1.12)
            for y in range(int(cy - r) - 1, int(cy + r) + 2):
                for x in range(int(cx - r) - 1, int(cx + r) + 2):
                    dx, dy = x + 0.5 - cx, y + 0.5 - cy
                    d = (dx * dx + dy * dy) ** 0.5 / r
                    if d > 1.0:
                        continue
                    # (lit from above: the clump's upper side lighter, its lower side in its own shade)
                    lit = tone * (1.12 - 0.42 * (dy / r) - 0.18 * d)
                    rgb[(y % n) * n + (x % n)] = tuple(v * lit for v in colour)
        for y in range(n):
            f = TOP_LIGHT + (UNDER_DARK - TOP_LIGHT) * (y / (n - 1)) ** 1.3
            for x in range(n):
                i = y * n + x
                rgb[i] = tuple(min(255.0, max(0.0, v * f)) for v in rgb[i])
        c.a = None
        return c
    return draw


def _clusters(pts, k):
    """k groups of points by plain k-means over x, y (from spread-out seeds): where a crown's masses of leaves are."""
    pts = pts[::max(1, len(pts) // 3000)]
    pts.sort(key=lambda q: math.atan2(q[1], q[0]))
    cen = [pts[int(i * len(pts) / k)] for i in range(k)]
    for _ in range(8):
        groups = [[] for _ in range(k)]
        for q in pts:
            j = min(range(k), key=lambda i: (q[0] - cen[i][0]) ** 2 + (q[1] - cen[i][1]) ** 2)
            groups[j].append(q)
        cen = [tuple(sum(q[d] for q in g) / len(g) for d in range(3)) if g else cen[i] for i, g in enumerate(groups)]
    return [g for g in groups if len(g) > 10]


FIT_SIDE = 0.94                 # (the far crown's reach a little inside the leaves': their tips are see-through air)
UNDER = 0.55                    # (a mass's underside is this flat: _smooth_crown draws it so)


def _fit(lumps, pts):
    """The masses moved and sized so the crown they make spans what the near leaves span (each way across, top and
    bottom): from afar the tree is the size and shape it is when you come near."""
    xs, ys, zs = [q[0] for q in pts], [q[1] for q in pts], [q[2] for q in pts]
    want = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
    have = (min(g[0] - g[3] for g in lumps), min(g[1] - g[4] for g in lumps), min(g[2] - g[5] * UNDER for g in lumps),
            max(g[0] + g[3] for g in lumps), max(g[1] + g[4] for g in lumps), max(g[2] + g[5] for g in lumps))
    out = []
    k = []
    for d in range(3):
        span0, span1 = have[d + 3] - have[d], want[d + 3] - want[d]
        f = (span1 * (FIT_SIDE if d < 2 else 1.0)) / span0 if span0 > 1 else 1.0
        mid0, mid1 = (have[d] + have[d + 3]) / 2, (want[d] + want[d + 3]) / 2
        k.append((f, mid0, mid1))
    for g in lumps:
        p = [k[d][2] + (g[d] - k[d][1]) * k[d][0] for d in range(3)]
        out.append((p[0], p[1], p[2], g[3] * k[0][0], g[4] * k[1][0], g[5] * k[2][0]))
    # (the bottom's flattened underside and the top are each a mass's own, so scaling about the middle can leave the
    # top a little off: put it back exactly)
    top = max(g[2] + g[5] for g in out)
    dz = want[5] - top
    return [(g[0], g[1], g[2] + dz * max(0.0, (g[2] - want[2]) / max(1.0, want[5] - want[2])), g[3], g[4], g[5]) for g in out]


def _far_parts(piece, desc):
    made = modelmake.make(desc)
    # (the leaves, not the vines hanging from the boughs: counted in, they pulled the far crown 200 down and narrower than
    # the tree it stands for, so it changed shape as its cell loaded: treevary.matches)
    leaf = [s for s in made['shapes'] if s.get('alpha') and 'vine' not in (s.get('tex') or '').lower()] or \
        [s for s in made['shapes'] if s.get('alpha')]
    wood = [s for s in made['shapes'] if not s.get('alpha')]
    if not leaf:
        return None
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for s in leaf for k in range(0, len(s['p']), 3)]
    parts = []
    if piece in PALMS:
        # (a palm: its fronds from the crown, drooping, as thin blades: a fan, never a ball)
        top = sorted(pts, key=lambda q: -q[2])[:max(10, len(pts) // 5)]
        cx, cy, cz = (sum(q[d] for q in top) / len(top) for d in range(3))
        reach = max(math.hypot(q[0] - cx, q[1] - cy) for q in pts)
        _fronds[piece] = (cx, cy, cz, reach)
        # (a small tuft at the crown, so far_of still makes a far model; the fronds themselves are made in build)
        parts.append(dict(ms.limb((cx, cy, cz - 20), (cx, cy, cz + 30), 30, 12, 'far_canopy', sides=5), far_only=True, solid=False))
        crown = (cx, cy, cz)
    else:
        # (a broadleaf: lumps where its leaves mass, overlapping: an uneven crown, not one egg)
        groups = _clusters(pts, LUMPS.get(piece, 3))
        _lumps[piece] = []
        low = None
        for g in groups:
            gx, gy, gz = (sum(q[d] for q in g) / len(g) for d in range(3))
            sx = (sum((q[0] - gx) ** 2 for q in g) / len(g)) ** 0.5 * 1.9
            sy = (sum((q[1] - gy) ** 2 for q in g) / len(g)) ** 0.5 * 1.9
            sz = (sum((q[2] - gz) ** 2 for q in g) / len(g)) ** 0.5 * 1.3
            sx, sy, sz = max(sx, 20.0), max(sy, 20.0), max(sz, 18.0)
            _lumps.setdefault(piece, []).append((gx, gy, gz, sx, sy, sz))
        _lumps[piece] = _fit(_lumps[piece], pts)
        low = min(g[2] - g[5] * 0.5 for g in _lumps[piece])
        cx = sum(q[0] for q in pts) / len(pts)
        cy = sum(q[1] for q in pts) / len(pts)
        crown = (cx, cy, low)
        _crown_foot[piece] = crown
    if not wood:
        # (no trunk of its own, bamboo's canes being see-through: a green stem from the ground to the crown)
        parts.append(dict(ms.limb((crown[0], crown[1], -DOWN), crown, 30, 20, 'far_stem', sides=5), far_only=True, solid=False))
    if wood:
        foot = [(s['p'][k], s['p'][k + 1]) for s in wood for k in range(0, len(s['p']), 3) if s['p'][k + 2] < 40]
        bark = next((k for k, v in desc['looks'].items() if not v.get('alpha')), None)
        if foot and bark:
            fx = sum(p[0] for p in foot) / len(foot)
            fy = sum(p[1] for p in foot) / len(foot)
            r0 = max(8.0, min(60.0, max(math.hypot(p[0] - fx, p[1] - fy) for p in foot) * 0.7))
            parts.append(dict(ms.limb((fx, fy, -DOWN), crown, r0, r0 * 0.65, bark, sides=5), far_only=True, solid=False))
    return parts


def _wrap(piece, original):
    def describe():
        desc = original()
        parts = _far_parts(piece, desc)
        if not parts:
            return desc
        name = 'jungle/canopy_far_' + piece
        if name not in ms.TEXTURES:
            ms.TEXTURES[name] = (_canopy_plain if piece in PALMS else _canopy_of)(_leaf_colour(desc), 41 + len(piece))
        looks = dict(desc['looks'], far_canopy=ms.look(name), far_stem=ms.look('jungle/cane', tile=44))
        return dict(desc, looks=looks, parts=list(desc['parts']) + parts)
    return describe


RING, ROUND = 5, 7              # (rows and steps round of a crown's lump: ~70 triangles, its corners shared so it shades soft)


def _bump(seed, lat, lon):
    """1 give or take a quarter: a crown's bumps, smooth, never twice the same."""
    a, b, c = seed * 1.7, seed * 2.3, seed * 0.9
    return 1.0 + 0.16 * math.sin(3 * lon + a) * math.sin(2 * lat + b) + 0.1 * math.sin(5 * lon + c) + 0.06 * math.sin(7 * lat + a)


ROUGH = 0.15                    # (each corner of a mass in or out by up to this share: a ragged outline against the sky)


def _rough(k, j, i):
    """A corner's own in-or-out, the same for the same corner (shared round the seam): 1 - ROUGH .. 1 + ROUGH."""
    h = (k * 73856093 ^ j * 19349663 ^ i * 83492791) & 0xFFFF
    return 1.0 - ROUGH + 2 * ROUGH * h / 65535.0


BOUGHS = 5                      # (branches seen between the masses: from the crown's foot out to the lowest few)


def _boughs(piece, crown_foot, tex, normal):
    """A few branches from where the trunk meets the crown out and up into its lowest masses: thin dark tubes, what
    shows between the leaves of a real tree far off and keeps a crown from reading as one ball on a stick."""
    lumps = sorted(_lumps.get(piece) or (), key=lambda g: g[2])[:BOUGHS]
    P, N, UV, I = [], [], [], []
    fx, fy, fz = crown_foot
    SIDES = 4
    for gx, gy, gz, sx, sy, sz in lumps:
        tx, ty, tz = gx, gy, gz - sz * 0.2
        L = math.sqrt((tx - fx) ** 2 + (ty - fy) ** 2 + (tz - fz) ** 2)
        if L < 40:
            continue
        ax, ay, az = (tx - fx) / L, (ty - fy) / L, (tz - fz) / L
        # (two directions across the branch)
        ux, uy, uz = (-ay, ax, 0.0) if abs(az) < 0.95 else (1.0, 0.0, 0.0)
        ul = math.sqrt(ux * ux + uy * uy + uz * uz)
        ux, uy, uz = ux / ul, uy / ul, uz / ul
        vx, vy, vz = ay * uz - az * uy, az * ux - ax * uz, ax * uy - ay * ux
        base = len(P) // 3
        for e, (px, py, pz, r) in enumerate(((fx, fy, fz, 14.0), (tx, ty, tz, 6.0))):
            for q in range(SIDES + 1):
                a = 2 * math.pi * q / SIDES
                ox = (ux * math.cos(a) + vx * math.sin(a))
                oy = (uy * math.cos(a) + vy * math.sin(a))
                oz = (uz * math.cos(a) + vz * math.sin(a))
                P += [px + ox * r, py + oy * r, pz + oz * r]
                N += [ox, oy, oz]
                UV += [q / SIDES, e * 2.0]
        for q in range(SIDES):
            a = base + q
            I += [a, a + SIDES + 1, a + 1, a + 1, a + SIDES + 1, a + SIDES + 2]
    if not P:
        return None
    return {'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': normal, 'gloss': 10.0, 'alpha': False, 'glow': '', 'glow_mult': 1.0}


def _smooth_crown(piece, tex, normal):
    """The crown's lumps as one shape: each a bumpy ball, its corners shared (the distant blocks work out normals from
    the triangles round each corner: shared, it shades soft; the modelmake ball's faces each had their own and every
    face showed flat, the user, 20 Nov 2026: "they still look too blocky"), its underside drawn in."""
    P, N, UV, I = [], [], [], []
    for k, (gx, gy, gz, sx, sy, sz) in enumerate(_lumps.get(piece) or ()):
        base = len(P) // 3
        for j in range(RING + 1):
            lat = math.pi * j / RING
            for i in range(ROUND + 1):
                lon = 2 * math.pi * i / ROUND
                f = _bump(k + 1, lat, lon) * _rough(k, j, i % ROUND) if 0 < j < RING else 1.0
                nx, ny, nz = math.sin(lat) * math.cos(lon), math.sin(lat) * math.sin(lon), math.cos(lat)
                z = nz * sz * f
                if z < 0:
                    z *= 0.55                       # (a crown's underside is flatter than its top)
                P += [gx + nx * sx * f, gy + ny * sy * f, gz + z]
                N += [nx, ny, nz]
                UV += [i / ROUND * 2.0, j / RING]
        for j in range(RING):
            for i in range(ROUND):
                a = base + j * (ROUND + 1) + i
                b, c, d = a + 1, a + ROUND + 1, a + ROUND + 2
                I += [a, c, b, b, c, d]
    if not P:
        return None
    return {'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': normal, 'gloss': 10.0, 'alpha': False, 'glow': '', 'glow_mult': 1.0}


def _palm_fronds(piece, tex, normal):
    """A palm's fronds as curved tubes drooping from the crown, tapering to the tip, corners shared so each shades round
    (straight three-sided sticks read as polygons: the user, 20 Nov 2026)."""
    if piece not in _fronds:
        return None
    cx, cy, cz, reach = _fronds[piece]
    P, N, UV, I = [], [], [], []
    SEG, SIDES = 6, 4
    for k in range(11):
        a = math.radians(k * 360 / 11 + 7 * (k % 3))
        up = 0.35 if k % 3 == 0 else 0.1                     # (some rise first, as the young ones do)
        drop = 0.75 if k % 2 else 0.5
        base = len(P) // 3
        for j in range(SEG + 1):
            t = j / SEG
            # (out along the frond, its height an arc: up a little, then down past the crown)
            h = reach * (up * math.sin(t * math.pi) - drop * t * t)
            px, py, pz = cx + math.cos(a) * reach * t, cy + math.sin(a) * reach * t, cz + h
            r = 26 * (1 - t) + 4
            for i in range(SIDES + 1):
                q = 2 * math.pi * i / SIDES
                # (flattened: wider across than deep, as a frond is)
                ox, oy, oz = -math.sin(a) * math.cos(q) * r * 1.6, math.cos(a) * math.cos(q) * r * 1.6, math.sin(q) * r * 0.5
                P += [px + ox, py + oy, pz + oz]
                L = math.sqrt(ox * ox + oy * oy + oz * oz) or 1.0
                N += [ox / L, oy / L, oz / L]
                UV += [i / SIDES, t]
        for j in range(SEG):
            for i in range(SIDES):
                v = base + j * (SIDES + 1) + i
                I += [v, v + SIDES + 1, v + 1, v + 1, v + SIDES + 1, v + SIDES + 2]
    return {'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': normal, 'gloss': 10.0, 'alpha': False, 'glow': '', 'glow_mult': 1.0}


def _merge(a, b):
    """Two shapes of one look as one (one shape, one block draw however many)."""
    n = len(a['p']) // 3
    return dict(a, p=list(a['p']) + b['p'], n=list(a.get('n') or []) + b['n'] if a.get('n') else None,
                uv=list(a['uv']) + b['uv'], i=list(a['i']) + [v + n for v in b['i']])


_build = ms.build


def build(piece):
    """modelsets.build, and for a broadleaf tree its far model made again with the smooth crown."""
    made = _build(piece)
    if piece in FAR_TREES and (_lumps.get(piece) or piece in _fronds) and made.get('far'):
        import nif
        import nifmake
        name = 'jungle/canopy_far_' + piece
        tex, nor = ms.tex_path(name), ms.tex_path(name, True)
        crown = _palm_fronds(piece, tex, nor) if piece in PALMS else _smooth_crown(piece, tex, nor)
        rest = [s for s in made['far']['shapes'] if s.get('tex', '').lower() != tex.lower()]
        shapes = rest + [crown]
        bark = next((s for s in rest if 'bark' in (s.get('tex') or '').lower()), None)
        if piece not in PALMS and bark and _lumps.get(piece):
            foot = _crown_foot.get(piece)
            b = _boughs(piece, foot, bark['tex'], bark.get('normal', '')) if foot else None
            if b:
                # (the branches drawn with the trunk's own picture: one more shape of the same look, merged with it)
                shapes = [s for s in shapes if s is not bark] + [_merge(bark, b)]
        data = nifmake.build(ms.PIECES[piece]['edid'] + 'Far', shapes)
        made['far']['nif'] = data
        made['far']['shapes'] = shapes
        made['files'][made['mesh'][:-4] + '_lod.nif'] = data
        made['files'][tex], made['files'][nor] = ms.texture_files(name)
    return made


ms.build = build

for _p in FAR_TREES:
    if _p in ms.PIECES and not ms.PIECES[_p].get('far_trees'):
        ms.PIECES[_p]['describe'] = _wrap(_p, ms.PIECES[_p]['describe'])
        ms.PIECES[_p]['far_trees'] = True
