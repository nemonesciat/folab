"""Is a spot inside a building? One check for everything that stands people (or the markers they go to) outdoors.

A city's buildings are closed shells: their insides are places of their own (or a hotel's small world), so nobody may stand
in the city's copy. Seven people stood in the closed Royal Hawaiian's lobby, seen through its glass from the street (22 Nov
2026): the roof test the pickers had (waikikilife.Spots) missed it. This goes by the building's outline, not what's overhead.

What counts as a building, by its base (as the mod leaves each ref: the source plugin's own refs as well as those it added,
swapped bases followed, removed ones gone):

  the game's stand-alone buildings  townbuild's catalogue (`cat`, else the one kept for these game files if it is there)
  the game's landmark pieces        landmarks.lifted_bounds: casino fronts, the great buildings' walls (not `NOT_CLOSED`)
  FOLab's own closed buildings      `CLOSED`, by the mod's record for each piece; open ones (a hale you walk
                                    into, the cookhouse, the band shell, a hotel's `_open` piece in its own small world,
                                    concave ones whose box would take in the beach: the Coral Crescent, the Tradewinds'
                                    courtyard) are left out

A building's outline is read from its collision as a body meets it: the walls cut at `SLICES` over its origin, drawn on a
grid of `STEP`, doorways closed (`PLUG`) and what the walls then enclose filled in (an open courtyard stays out); a model
whose collision can't be read is its box. Not its box alone: FOLab's Royal Hawaiian's box is 4,200 x 3,400 with its
lawns, where the court's guards stand. A spot is inside when it lies in the outline grown by `MARGIN` (a body's
half-width: nobody stands in a wall), turned and scaled with the building, and, when its height is given, lower than
`ROOF_UNDER` under the building's top (someone on a roof stands on it, not in it).

    B = indoors.Buildings(gd, pr, world)       read lazily, cell by cell round what is asked
    B.inside(x, y, z=None) -> bool              B.at(...) -> (ref key, editor ID) or None
    indoors.everyone_inside(gd, pr, world)     the actors standing inside one now: [(cell, ref, editor ID, (x, y, z), building)]
"""
import json
import math
import os
import re

import recordio

MARGIN = 30.0
ROOF_UNDER = 150.0
STEP = 32.0                    # (the outline's grid)
SLICES = (100.0, 160.0)        # (where walls are cut, over the building's origin: a body's height)
PLUG = 4                       # (doorways up to about this many steps either side are closed before the inside is filled)
CELL = 4096.0
REACH = 1                      # (cells round a spot whose buildings may reach it: none of the game's or FOLab's is over 8,000 across)

CLOSED = (
    # hotels of the strip along the sea
    'blue_lagoon', 'hale_malia', 'kahala_reef', 'kahuna_palms', 'makai_tower', 'moana_kai', 'pink_pearl',
    # the great buildings, closed in the city (their lobbies are their own small worlds)
    'royal_hawaiian', 'moana', 'kilauea', 'lani_moku', 'battery_randolph', 'aquarium', 'lighthouse',
    # the restyled Mojave buildings, the settlers' halls, closed huts and stores, shipping containers
    'beach_bar', 'plantation_store', 'plantation_shop', 'plantation_dry_goods', 'plantation_school', 'plantation_hall',
    'settler_hall', 'settler_hall_red', 'bamboo_hut', 'bamboo_hut_small', 'bamboo_storehouse',
    'cargo_blue', 'cargo_green', 'cargo_red', 'cargo_rust',
)
ACTORS = ('NPC_', 'CREA', 'LVLN', 'LVLC')
# (of the landmark sets' pieces, what isn't a closed building: towers and a statue people stand on or in, a base slab, the
# Lucky 38's overhangs and stair lights, The Tops' pool; the game's NCR snipers stand in its guard towers)
NOT_CLOSED = re.compile(r'tower|statue|stairlight|base$|overhang|pool', re.I)


def catalogue(gd):
    """townbuild's catalogue kept for these game files, or [] (never measured here: that takes minutes)."""
    try:
        import server
        import townbuild
        if getattr(server, 'GD', None) is not gd:
            return []
        with open(os.path.join(server.kits_folder(), 'buildings.json'), encoding='utf-8') as f:
            got = json.load(f)
        return got['buildings'] if got.get('format') == townbuild.FORMAT else []
    except (OSError, ValueError, KeyError, ImportError):
        return []


class Outline:
    """Where a building stands, in its own frame: grid squares of STEP that its walls or what they enclose cover."""

    def __init__(self, box, tris=None):
        self.box = box
        m = int(math.ceil((MARGIN + STEP * (PLUG + 1)) / STEP))
        self.x0, self.y0 = box[0] - m * STEP, box[1] - m * STEP
        self.w = int(math.ceil((box[3] - box[0]) / STEP)) + 2 * m + 1
        self.h = int(math.ceil((box[4] - box[1]) / STEP)) + 2 * m + 1
        self.cells = None
        walls = set()
        for a, b, c in tris or ():
            for z in SLICES:
                seg = _slice(a, b, c, z)
                if seg:
                    self._line(walls, *seg)
        if walls:
            self.cells = self._fill(walls)

    def _line(self, out, p, q):
        n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / (STEP / 2)))
        for k in range(n + 1):
            x, y = p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n
            i, j = int((x - self.x0) // STEP), int((y - self.y0) // STEP)
            if 0 <= i < self.w and 0 <= j < self.h:
                out.add((i, j))

    @staticmethod
    def _grow(cells, r):
        ring = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if di * di + dj * dj <= r * r + r]
        return {(i + di, j + dj) for i, j in cells for di, dj in ring}

    def _fill(self, walls):
        shut = self._grow(walls, PLUG)
        seen, todo = set(), [(0, 0)]
        while todo:
            i, j = todo.pop()
            if (i, j) in seen or (i, j) in shut or not (0 <= i < self.w and 0 <= j < self.h):
                continue
            seen.add((i, j))
            todo += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
        inner = {(i, j) for i in range(self.w) for j in range(self.h) if (i, j) not in seen and (i, j) not in shut}
        # (what the plugged walls enclose, grown back out over the plug; the walls themselves grown by MARGIN)
        return self._grow(inner, PLUG) | self._grow(walls, int(math.ceil(MARGIN / STEP)))

    def hit(self, lx, ly):
        if self.cells is None:
            b = self.box
            return b[0] - MARGIN <= lx <= b[3] + MARGIN and b[1] - MARGIN <= ly <= b[4] + MARGIN
        return (int((lx - self.x0) // STEP), int((ly - self.y0) // STEP)) in self.cells


def _slice(a, b, c, z):
    """Where a triangle crosses height z, as a line ((x, y), (x, y)), or None."""
    pts = []
    for p, q in ((a, b), (b, c), (c, a)):
        if (p[2] - z) * (q[2] - z) < 0:
            t = (z - p[2]) / (q[2] - p[2])
            pts.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return (pts[0], pts[1]) if len(pts) >= 2 else None


def model_of(gd, pr, key):
    """The model path (under Data) a base draws with, or None."""
    try:
        if key.startswith('+'):
            m = recordio.field(pr.records.get(key) or {}, 'MODL')
        else:
            raw = gd.fields(gd.from_key(key)).get('MODL')
            m = raw.split(b'\0')[0].decode('latin-1') if raw else None
    except (KeyError, ValueError):
        return None
    if not m:
        return None
    m = m.replace('/', '\\').lstrip('\\')
    return m if m.lower().startswith('meshes\\') else 'meshes\\' + m


def collision(gd, path):
    """The solid collision of a model as triangles [((x, y, z), ...)] in its own frame, or [] if it can't be read."""
    import struct
    import hkshape
    import nif
    out = []
    try:
        for sh in hkshape.collision_shapes(gd.read_file(path)):
            if sh['layer'] not in hkshape.LAYERS_SOLID or not sh['i']:
                continue
            v, idx = sh['v'], sh['i']
            pts = [(v[k], v[k + 1], v[k + 2]) for k in range(0, len(v) - 2, 3)]
            out += [(pts[idx[k]], pts[idx[k + 1]], pts[idx[k + 2]]) for k in range(0, len(idx) - 2, 3)]
    except (OSError, KeyError, ValueError, IndexError, TypeError, struct.error, hkshape.Unread, nif.NifError):
        return []
    return out


def _obnd_of_record(rec):
    sub = next((s for s in (rec or {}).get('subs', ()) if s.get('tag') == 'OBND' and s.get('kind') == 'struct'), None)
    return [f['value'] for f in sub['fields'] if 'name' in f] if sub else None


def bounds(gd, pr, cat=None):
    """{base key: (x0, y0, z0, x1, y1, z1)} of every base that is a closed building."""
    out = {}
    for b in (catalogue(gd) if cat is None else cat):
        if b.get('key') and b.get('box'):
            out[b['key']] = list(b['box'])
    try:
        import landmarks
        out.update({k: b for k, b in landmarks.lifted_bounds(gd).items() if not NOT_CLOSED.search(_edid(gd, pr, k))})
    except (ValueError, KeyError, OSError):
        pass
    import modelsets
    modelsets._all_sets()
    for piece in CLOSED:
        if piece not in modelsets.PIECES:
            continue
        rk = modelsets.record_of(pr, piece)
        ob = _obnd_of_record(pr.records.get(rk)) if rk else None
        if ob and len(ob) == 6:
            out[rk] = ob
    return out


def _edid(gd, pr, key):
    if key.startswith('+'):
        return recordio.field(pr.records.get(key) or {}, 'EDID') or ''
    try:
        return gd.edid(gd.from_key(key)) or ''
    except (KeyError, ValueError):
        return ''


def placed(gd, pr, ck):
    """(ref key, base key, p, scale) for everything in an outdoor cell as the mod leaves it."""
    mine = (pr.cells.get(ck) or {}).get('refs', {})
    try:
        cell = gd.from_key(ck)
    except (KeyError, ValueError):
        cell = None
    if cell is not None:
        for r in gd.refs(cell):
            if r['base'] not in gd.forms or not r['pos']:
                continue
            key = gd.key(r['ref'])
            ch = mine.get(key) or {}
            if ch.get('removed'):
                continue
            yield key, ch.get('base') or gd.key(r['base']), ch.get('p') or list(r['pos']) + list(r['rot']), ch.get('s', r['scale'])
    for key, ch in mine.items():
        if key.startswith('+') and not ch.get('removed') and ch.get('p') and ch.get('base'):
            yield key, ch['base'], ch['p'], ch.get('s', 1.0)


class Buildings:
    """Footprints of the closed buildings in one world, read a cell at a time as spots are asked about."""

    def __init__(self, gd, pr, world, cat=None):
        self.gd, self.pr = gd, pr
        self.grid = gd.grid(world)
        self.boxes = bounds(gd, pr, cat)
        self.outlines = {}              # base -> Outline
        self.cells = {}                 # (cx, cy) -> [(ref key, base, ox, oy, scale, cos, sin, top)]

    def outline(self, base):
        if base not in self.outlines:
            path = model_of(self.gd, self.pr, base)
            self.outlines[base] = Outline(self.boxes[base], collision(self.gd, path) if path else None)
        return self.outlines[base]

    def _cell(self, xy):
        if xy not in self.cells:
            got = []
            c = self.grid.get(xy)
            if c is not None:
                for rk, base, p, s in placed(self.gd, self.pr, self.gd.key(c)):
                    b = self.boxes.get(base)
                    if not b:
                        continue
                    s = float(s or 1.0)
                    rz = p[5] if len(p) > 5 else 0.0
                    got.append((rk, base, p[0], p[1], s, math.cos(rz), math.sin(rz), p[2] + b[5] * s))
            self.cells[xy] = got
        return self.cells[xy]

    def at(self, x, y, z=None):
        """(ref key, editor ID) of the building (x, y[, z]) stands inside, or None."""
        cx, cy = int(x // CELL), int(y // CELL)
        for i in range(cx - REACH, cx + REACH + 1):
            for j in range(cy - REACH, cy + REACH + 1):
                for rk, base, ox, oy, sc, c, s, top in self._cell((i, j)):
                    dx, dy = x - ox, y - oy
                    lx, ly = (dx * c - dy * s) / sc, (dx * s + dy * c) / sc     # (back into the building's own frame)
                    b = self.boxes[base]
                    if not (b[0] - 2 * MARGIN <= lx <= b[3] + 2 * MARGIN and b[1] - 2 * MARGIN <= ly <= b[4] + 2 * MARGIN):
                        continue
                    if not self.outline(base).hit(lx, ly):
                        continue
                    if z is not None and z > top - ROOF_UNDER:
                        continue
                    return rk, _edid(self.gd, self.pr, base)
        return None

    def inside(self, x, y, z=None):
        return self.at(x, y, z) is not None


def everyone_inside(gd, pr, world, cat=None, B=None):
    """Every actor in the world (the source plugin's and the mod's) standing inside a closed building now:
    [(cell key, ref key, actor's editor ID, (x, y, z), (building ref, building editor ID))]."""
    B = B or Buildings(gd, pr, world, cat)
    kinds = {}

    def kind(b):
        if b not in kinds:
            if b.startswith('+'):
                kinds[b] = (pr.records.get(b) or {}).get('type', '')
            else:
                try:
                    kinds[b] = gd.forms[gd.from_key(b)][1].tag
                except (KeyError, ValueError):
                    kinds[b] = ''
        return kinds[b]
    out = []
    for xy, c in sorted(B.grid.items()):
        ck = gd.key(c)
        for rk, base, p, _s in placed(gd, pr, ck):
            if kind(base) not in ACTORS:
                continue
            hit = B.at(p[0], p[1], p[2])
            if hit:
                out.append((ck, rk, _edid(gd, pr, base), tuple(round(v, 1) for v in p[:3]), hit))
    return out
