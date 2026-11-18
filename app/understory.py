"""Bare ground filled (understory.py): plants wherever the ground as the game draws it could grow something and nothing grows.

The dressing plants by what the street map says each spot is, and by chance, so between its clumps open ground was left bare:
valley floors, the strip between a road and a wooded slope, a yard with one bush in it (Waikiki, 18 Nov 2026: "barren
patches of nothing ... dirt when plants could live there"). This looks at the ground itself instead: each land point's
topmost texture (the layers over the base, each by its strength), how steep it is there, and whether any plant stands within
REACH. A point that could grow and has none gets a clump suited to its ground (CLASSES by the texture's editor ID, MIXES by
class), and the clump counts at once, so ground already green gets nothing and a bare patch is filled only until no point of
it is farther than REACH from a plant. Never on pavement, asphalt, gravel, water, ground steeper than STEEP, roads, in
buildings or landmarks. Rock and sand are planted thinner (their reach is wider): a beach stays a beach.

fill(gd, pr, world, cells=None, seed=1, progress=None, reach=REACH, limit=LIMIT) -> (ops, report). The ops start with the
records of FOLab's own pieces the mod hasn't yet (modelsets.put), then one 'add' a plant, as the other dressing passes give."""
import math
import random
import re

import land
import modelsets
import osmdress
import recordio
import roadgen

REACH = 384.0           # no plant this near: the point is bare
STEP = 256              # how far apart the points looked at are (every second land point)
STEEP = 1.0             # rise over run past which nothing is planted (45 degrees: a cliff)
LIMIT = 80000           # plants one fill may add (each is memory and drawing in the game)
NEAR_ROAD = 64.0        # kept this far off a road piece's edge
NEAR_BUILT = 48.0       # and off a building's footprint

# the ground by its texture's editor ID: first match wins; None grows nothing
CLASSES = (
    (r'pavement|asphalt|concrete|road|gravel|lwatergravel', None),
    (r'lwatersand|sand|beach|dune', 'sand'),
    (r'moss|mud|wet|marsh', 'wet'),
    (r'golf|suburb|lawn|farm|field|grassgreen', 'lawn'),
    (r'canyonrubble01|rockcanyonrubble01$|cliff|rock(?!.*dirt)', 'rock'),
    (r'dirt|scrub|barren|sage|grass|soil|forest|leaf|root', 'dirt'),
)
# how far a plant's green reaches for this kind of ground (wider: planted thinner)
REACH_OF = {'dirt': 1.0, 'lawn': 1.0, 'wet': 0.9, 'rock': 1.35, 'sand': 2.5}

# by class: (piece, weight, smallest, biggest, sunk by, most in one clump); a piece is FOLab's own (modelsets.PIECES) or an
# editor ID of the game's
MIXES = {
    'dirt': [('undergrowth', 6, 0.8, 1.5, 4, 2), ('thicket', 4, 0.8, 1.3, 6, 1), ('ground_fern', 6, 0.9, 1.8, 2, 3),
             ('jungle_floor_a', 4, 0.9, 1.3, 3, 1), ('jungle_floor_b', 4, 0.9, 1.3, 3, 1), ('taro', 3, 0.8, 1.5, 2, 2),
             ('v22Grass', 6, 1.5, 3.5, 2, 3), ('v22Fern', 4, 1.5, 4.0, 2, 2), ('NVGoldfingerBanana', 2, 1.0, 1.8, 2, 2),
             ('ti_green', 2, 0.9, 1.4, 2, 2), ('heliconia', 1, 0.8, 1.3, 2, 2), ('tree_fern', 2, 0.8, 1.4, 4, 1),
             ('jungle_tree', 1, 0.7, 1.1, 8, 1)],
    'rock': [('ground_fern', 6, 0.9, 1.8, 2, 3), ('slope_cover_a', 5, 0.9, 1.3, 3, 1), ('slope_cover_b', 5, 0.9, 1.3, 3, 1),
             ('v22Grass', 5, 1.5, 3.0, 2, 3), ('v22Fern', 4, 1.5, 3.5, 2, 2), ('undergrowth', 3, 0.8, 1.3, 4, 1),
             ('ti_green', 2, 0.9, 1.4, 2, 2), ('NVSagebrush', 2, 0.8, 1.4, 2, 2), ('tree_fern', 1, 0.8, 1.3, 4, 1)],
    'lawn': [('v22Grass', 8, 1.2, 3.0, 2, 4), ('hibiscus', 3, 0.7, 1.2, 3, 2), ('NVGoldfingerBanana', 3, 1.0, 1.8, 2, 2),
             ('palm_young', 2, 0.7, 1.2, 5, 1), ('taro', 2, 0.8, 1.3, 2, 2), ('ti_red', 2, 0.9, 1.3, 2, 2),
             ('ground_fern', 2, 0.9, 1.5, 2, 2), ('undergrowth', 2, 0.7, 1.2, 4, 1)],
    'wet': [('v22Fern', 6, 2.0, 4.5, 2, 3), ('taro', 5, 0.9, 1.6, 2, 3), ('v22Grass', 5, 2.0, 4.0, 2, 3),
            ('ground_fern', 4, 0.9, 1.8, 2, 3), ('heliconia', 2, 0.8, 1.3, 2, 2)],
    'sand': [('dune_grass', 8, 1.0, 2.2, 2, 4), ('palm_young', 2, 0.8, 1.3, 5, 1), ('v22Grass', 2, 1.0, 2.0, 2, 2)],
}
CLUMP_OUT = (50.0, 220.0)   # how far from the first the rest of a clump stand

PLANTY = re.compile(r'(?i)tree|bush|plant|fern|grass|palm|shrub|banana|jungle|taro|bamboo|helicon|thicket|undergrowth|'
                    r'hibiscus|ivy|vine|weed|reed|cactus|agave|yucca|flower|sage|brush|joshua|cholla|stump|slope|leaves')


def class_of(edid):
    e = (edid or '').lower()
    for pat, cls in CLASSES:
        if re.search(pat, e):
            return cls
    return 'dirt'


def _top(quarter, pi, pj):
    """The texture key drawn on top at a quarter's point: the layers over the base, each by its strength."""
    best, bw, rest = None, -1.0, 1.0
    for l in reversed(quarter['layers']):
        a = l['a'][pj * 17 + pi]
        if a * rest > bw:
            best, bw = l.get('key'), a * rest
        rest *= 1.0 - a
    return quarter.get('bkey') if rest > bw else best


class _Grid:
    """Points by 512-unit square, for 'anything within r?'."""

    def __init__(self):
        self.sq = {}

    def add(self, x, y):
        self.sq.setdefault((int(x // 512), int(y // 512)), []).append((x, y))

    def near(self, x, y, r):
        i, j, r2 = int(x // 512), int(y // 512), r * r
        n = int(r // 512) + 1
        for a in range(i - n, i + n + 1):
            for b in range(j - n, j + n + 1):
                for px, py in self.sq.get((a, b), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < r2:
                        return True
        return False


def _roads(gd, pr, world, keys):
    import roadbed
    flat, slabs = roadbed._flat_bases(gd), roadbed._slab_bases(gd)
    by = {}
    for ck in keys:
        for r in pr.cells.get(ck, {}).get('refs', {}).values():
            b, p = r.get('base'), r.get('p')
            box = flat.get(b) or slabs.get(b)
            if not box or not p or r.get('removed'):
                continue
            s = float(r.get('s') or 1)
            rr = math.hypot(max(abs(box[0]), abs(box[3])), max(abs(box[1]), abs(box[4]))) * s + NEAR_ROAD
            item = (p, box, s)
            for i in range(int((p[0] - rr) // 512), int((p[0] + rr) // 512) + 1):
                for j in range(int((p[1] - rr) // 512), int((p[1] + rr) // 512) + 1):
                    by.setdefault((i, j), []).append(item)

    def on(x, y):
        for p, box, s in by.get((int(x // 512), int(y // 512)), ()):
            c, sn = math.cos(p[5]), math.sin(p[5])
            dx, dy = x - p[0], y - p[1]
            lx, ly = dx * c - dy * sn, dx * sn + dy * c
            if box[0] * s - NEAR_ROAD <= lx <= box[3] * s + NEAR_ROAD and box[1] * s - NEAR_ROAD <= ly <= box[4] * s + NEAR_ROAD:
                return True
        return False
    return on


def _in_boxes(boxes):
    by = {}
    for n, (bx, by_, rz, x0, y0, x1, y1) in enumerate(boxes):
        r = math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1))) + NEAR_BUILT
        for i in range(int((bx - r) // 1024), int((bx + r) // 1024) + 1):
            for j in range(int((by_ - r) // 1024), int((by_ + r) // 1024) + 1):
                by.setdefault((i, j), []).append(n)

    def hit(x, y):
        for n in by.get((int(x // 1024), int(y // 1024)), ()):
            bx, by_, rz, x0, y0, x1, y1 = boxes[n]
            c, s = math.cos(-rz), math.sin(-rz)
            dx, dy = x - bx, y - by_
            lx, ly = dx * c + dy * s, -dx * s + dy * c
            if x0 - NEAR_BUILT <= lx <= x1 + NEAR_BUILT and y0 - NEAR_BUILT <= ly <= y1 + NEAR_BUILT:
                return True
        return False
    return hit


def fill(gd, pr, world, cells=None, seed=1, progress=None, reach=REACH, limit=LIMIT, cat=None):
    """(ops, report): see the module's docstring. cells: the (x, y) cells to fill (all the world's by default)."""
    import landmarks
    import townbuild
    import server
    rng = random.Random(seed * 104729 + 7)
    grid = gd.grid(world)
    todo = sorted(xy for xy in grid if cells is None or tuple(xy) in {tuple(c) for c in cells})
    keys = {gd.key(c) for c in grid.values()}
    # what grows already: the mod's plants and the game's, by name or by being one of the dressing's or FOLab's sets
    known = set(osmdress._bases(gd).values())
    for which in modelsets.EXTRA:
        for _d, rows in modelsets.EXTRA[which].values():
            for piece, *_r in rows:
                k = modelsets.record_of(pr, piece)
                if k:
                    known.add(k)
    named = {}

    def is_plant(b):
        if b in known:
            return True
        if b not in named:
            try:
                e = recordio.field(pr.records[b], 'EDID') if b.startswith('+') and b in pr.records else gd.edid(gd.from_key(b))
            except Exception:
                e = ''
            named[b] = bool(PLANTY.search(e or ''))
        return named[b]

    green = _Grid()
    for ck in keys:
        for r in pr.cells.get(ck, {}).get('refs', {}).values():
            b, p = r.get('base'), r.get('p')
            if b and p and not r.get('removed') and is_plant(b):
                green.add(p[0], p[1])
    removed = {rk for ck in keys for rk, r in pr.cells.get(ck, {}).get('refs', {}).items() if r.get('removed')}
    for xy in todo:
        try:
            refs = gd.refs(grid[xy])
        except Exception:
            refs = ()
        for r in refs:
            if r.get('base') and r.get('pos') and gd.key(r['ref']) not in removed and is_plant(gd.key(r['base'])):
                green.add(r['pos'][0], r['pos'][1])
    on_road = _roads(gd, pr, world, keys)
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    built = osmdress._Stands(osmdress.standing(gd, pr, world, cat), margin=NEAR_BUILT)
    in_mark = _in_boxes(list(landmarks.standing(gd, pr, world)) + list(modelsets.footprints(pr, gd, world)))
    ground = roadgen.Ground(gd, pr, world)
    # the pieces, FOLab's own made (or found) first
    first, base_of = [], {}
    game = osmdress._bases(gd)
    wanted = {p for rows in MIXES.values() for p, *_r in rows}
    for piece in sorted(wanted):
        if piece in modelsets.PIECES:
            ops, info = modelsets.put(pr, piece)
            first += ops
            base_of[piece] = info['key'] or '$model_' + piece
        else:
            k = game.get(piece.lower())
            if k is None:
                for f, (_i, r) in gd.forms.items():
                    if r.tag in ('STAT', 'TREE', 'FLOR') and gd.edid(f).lower() == piece.lower():
                        k = gd.key(f)
                        break
            if k:
                base_of[piece] = k
    mixes = {c: [row for row in rows if row[0] in base_of] for c, rows in MIXES.items()}
    tex_class, cache = {}, {}
    spots = []
    for n, xy in enumerate(todo):
        if progress and n % 200 == 0:
            progress('Looking at the ground', n, len(todo))
        c = grid[xy]
        ck = gd.key(c)
        form = pr.land.get(ck)
        if not form:
            e = gd.land_at(world, *xy)
            form = land.decode(gd, e, cache) if e else None
        if not form or not form.get('h'):
            continue
        h = form['h']
        for q, quarter in enumerate(form['q']):
            qx, qy = (q % 2) * 16, (q // 2) * 16
            for pj in range(0, 16, STEP // 128):
                for pi in range(0, 16, STEP // 128):
                    gi, gj = qx + pi, qy + pj
                    z = h[gj * 33 + gi]
                    if z < 8:
                        continue
                    t = _top(quarter, pi, pj)
                    if t not in tex_class:
                        try:
                            e = recordio.field(pr.records[t], 'EDID') if t and t.startswith('+') and t in pr.records else (gd.edid(gd.from_key(t)) if t else 'default')
                        except Exception:
                            e = ''
                        tex_class[t] = (class_of(e), e)
                    cls = tex_class[t][0]
                    if cls is None or not mixes.get(cls):
                        continue
                    dzx = abs(h[gj * 33 + min(32, gi + 1)] - h[gj * 33 + max(0, gi - 1)]) / 256.0
                    dzy = abs(h[min(32, gj + 1) * 33 + gi] - h[max(0, gj - 1) * 33 + gi]) / 256.0
                    if max(dzx, dzy) > STEEP:
                        continue
                    jx, jy = rng.uniform(-STEP / 2, STEP / 2), rng.uniform(-STEP / 2, STEP / 2)
                    spots.append((xy[0] * 4096 + gi * 128 + jx, xy[1] * 4096 + gj * 128 + jy, cls))
    rng.shuffle(spots)
    in_todo = set(todo)
    out, by, looked, why = [], {}, 0, {'green already': 0, 'road': 0, 'built': 0}
    for n, (x, y, cls) in enumerate(spots):
        if len(out) >= limit:
            break
        if progress and n % 5000 == 0:
            progress('Filling the bare ground', n, len(spots))
        looked += 1
        r = reach * REACH_OF.get(cls, 1.0)
        if green.near(x, y, r):
            why['green already'] += 1
            continue
        if on_road(x, y):
            why['road'] += 1
            continue
        if built.hit(x, y) or in_mark(x, y):
            why['built'] += 1
            continue
        rows = mixes[cls]
        pick = rng.random() * sum(row[1] for row in rows)
        for piece, wgt, smin, smax, sink, most in rows:
            pick -= wgt
            if pick <= 0:
                break
        for m in range(1 + int(rng.random() ** 1.5 * most)):
            px, py = x, y
            if m:
                a, d = rng.uniform(0, math.tau), rng.uniform(*CLUMP_OUT)
                px, py = x + math.sin(a) * d, y + math.cos(a) * d
                if on_road(px, py) or built.hit(px, py) or in_mark(px, py):
                    continue
            cell = grid.get((int(px // 4096), int(py // 4096)))
            z = ground.at(px, py)
            if cell is None or z is None or z < 8 or (cells is not None and (int(px // 4096), int(py // 4096)) not in in_todo):
                continue
            scale = rng.uniform(smin, smax)
            rx, ry, rz = 0.0, 0.0, rng.uniform(0, math.tau)
            if piece in modelsets.LAID:
                rx, ry, rz = osmdress.lie(ground, 'pile', px, py, rz, scale * 3)
            out.append({'op': 'add', 'cell': gd.key(cell), 'base': base_of[piece], 's': round(scale, 3),
                        'p': [round(px, 1), round(py, 1), round(z - sink * scale, 1), round(rx, 4), round(ry, 4), round(rz, 4)]})
            green.add(px, py)
            by[piece] = by.get(piece, 0) + 1
    by_class = {}
    for _x, _y, cls in spots:
        by_class[cls] = by_class.get(cls, 0) + 1
    return first + out, {'plants': len(out), 'by': by, 'records': len(first), 'spots': len(spots), 'looked': looked,
                         'passed': why, 'ground': by_class,
                         'textures': {e: c for c, e in sorted(set(tex_class.values()), key=lambda v: str(v[1]))}}
