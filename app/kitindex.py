"""The game's building kits: which pieces there are, what each side of each piece looks like, and how they join.

Interiors in New Vegas are built from kits: pieces that stand on a square grid (256 units for the vaults), each named
by its folder under meshes\\ (dungeons\\vault, dungeons\\office...). Nothing in the game's files says which pieces fit
together, so this reads it from two places and checks one against the other:

  the geometry   Each piece's footprint is divided into slots along its four sides, one for each grid step. A slot's
                 "section" is what the piece's surfaces look like where they cross just inside that side: a floor line,
                 a door frame, nothing at all. Two pieces fit when their sections match, face to face.
  the game       Every placed piece in every interior, with its neighbours: which piece stood beside which, how far
                 away and turned how. These are joins Obsidian and Bethesda really built.

The sections say what could fit (including joins never used in the game); the placed pieces say what's been used and
how often. Everything here is measured, so a kit no one has looked at works the same as the vault's.

    idx = kitindex.build(game)         {kit name: Kit}, kept on disk per game files' hash by load()
    kit.pieces[key]                    Piece: footprint, height, slots
    kit.fits(key, slot)                every (other piece, its slot, its turn, dz) whose section matches this slot
    kit.seen[(a, b, dx, dy, dz, t)]    how many times the game placed b there beside a (in a's own frame)
    Tileset(kit), build_area(ts, squares)   pieces for any set of grid squares, every side agreeing with its neighbour

Directions: 0 east (+x), 1 north (+y), 2 west, 3 south. A thing with game rotation t quarter turns is clockwise from
above, so its side d faces (d - t) mod 4 in the world."""
import collections
import json
import math
import os
import random
import struct

import nif

SECTION_BIN = 8        # (a section's grain, units)
SLICE_IN = 3           # (how far inside the side the section is cut: lips and frames stand proud of the side itself)
CLEAR = 110            # (a slot is walkable where the floor has this much room above it (pipes run overhead)...)
FEET = 48              # (how far above the floor a piece is cut to walk it: below window sills)
PERSON = 2             # (how many section bins a person needs clear on each side)
OPEN_MIN = 56          # (...in one unbroken run at least this wide: a door counts, the gap between two pillars doesn't)
BEYOND = (2, 8, 16, 24)  # (a wall this far past the side closes it: a niche in a wall isn't a way through)
SEAM = 2               # (walls either side of a join may differ by this many bins)
FLOOR_LEVEL = 40       # (floors nearer than this are one floor)
MIN_TILES = 8          # (a kit with fewer one-square pieces than this can't fill an area)
FIT_SCORE = 0.6        # (two sections fit when this share of what they draw is the same)
OVERHANG = 44          # (a piece's box may pass a grid line by this much and still be counted up to the line)
STEPS = (128, 192, 256, 320, 384, 512, 768, 1024)
DX = ((1, 0), (0, 1), (-1, 0), (0, -1))


def kit_of(model):
    """A model's kit name, or None if it isn't in a building folder: meshes\\dungeons\\vault\\room\\x.nif -> dungeons\\vault."""
    parts = model.replace('/', '\\').lower().lstrip('\\').split('\\')
    if len(parts) > 2 and parts[0] in ('nvdlc01', 'nvdlc02', 'nvdlc03', 'nvdlc04', 'dlc01', 'dlc02', 'dlc03', 'dlc04', 'dlc05'):
        lead, parts = parts[0] + '\\', parts[1:]
    else:
        lead = ''
    if len(parts) < 3 or parts[0] not in ('dungeons', 'architecture'):
        return None
    return lead + parts[0] + '\\' + parts[1]


def quarter(angle):
    """A rotation in quarter turns (0 to 3), or None if it isn't on one."""
    k = (angle % (2 * math.pi)) / (math.pi / 2)
    return round(k) % 4 if abs(k - round(k)) < 0.01 else None


def turn_xy(x, y, t):
    """A point in a thing's own frame, in the world's, for t clockwise quarter turns."""
    for _ in range(t % 4):
        x, y = y, -x
    return x, y


def unturn_xy(x, y, t):
    return turn_xy(x, y, 4 - t % 4)


def triangles(shapes):
    """A model's solid triangles as ((x, y, z) * 3). (Glows and glass aren't walls.)"""
    out = []
    for s in shapes:
        if s.get('alpha') == 'blend':
            continue
        p, ix = s['p'], s['i']
        for k in range(0, len(ix) - 2, 3):
            a, b, c = ix[k] * 3, ix[k + 1] * 3, ix[k + 2] * 3
            out.append(((p[a], p[a + 1], p[a + 2]), (p[b], p[b + 1], p[b + 2]), (p[c], p[c + 1], p[c + 2])))
    return out


def slice_plane(tris, axis, at):
    """Where triangles cross the plane (axis = at): segments, each two points (other horizontal coordinate, z)."""
    other = 1 - axis
    segs = []
    for tri in tris:
        pts = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            da, db = a[axis] - at, b[axis] - at
            if (da < 0) != (db < 0):
                f = da / (da - db)
                pts.append((a[other] + f * (b[other] - a[other]), a[2] + f * (b[2] - a[2])))
        if len(pts) == 2:
            segs.append(pts)
    return segs


def draw_section(segs, u_lo, u_hi, outward_flip):
    """Segments as a set of bins (u, z) across one slot, u from the slot's middle, to the right looking outward."""
    mid, half, cells = (u_lo + u_hi) / 2, (u_hi - u_lo) / 2, set()
    for (u0, z0), (u1, z1) in segs:
        if max(u0, u1) < u_lo or min(u0, u1) > u_hi:
            continue
        n = max(1, int(max(abs(u1 - u0), abs(z1 - z0)) / (SECTION_BIN / 2)))
        for k in range(n + 1):
            u, z = u0 + (u1 - u0) * k / n, z0 + (z1 - z0) * k / n
            if abs(u - mid) > half:
                continue
            w = (u - mid) * (-1 if outward_flip else 1)
            cells.add((int(math.floor(w / SECTION_BIN + 0.5)), int(math.floor(z / SECTION_BIN + 0.5))))
    return cells


def walkable(cells, beyond=frozenset()):
    """(floor height in units or None, clear width in units, that run's first and last column): how much of a section can be walked through. beyond: what
    stands just past the side; a column with a wall there is closed, however clear it looks at the side itself."""
    cols = collections.defaultdict(list)
    for u, z in cells:
        cols[u].append(z)
    floors = collections.Counter()
    for u, zs in cols.items():
        floors[min(zs)] += 1
    if not floors:
        return None, 0, None
    # the floor: the lowest level that runs across most of what's open (a stray lip below it doesn't count)
    floor = max(floors, key=lambda z: (floors[z], -z))
    need = CLEAR // SECTION_BIN
    blocked = {u for u, z in beyond if floor + 2 <= z <= floor + need}
    free = sorted(u for u, zs in cols.items()
                  if u not in blocked and any(abs(z - floor) <= 1 for z in zs) and not any(floor + 2 <= z <= floor + need for z in zs))
    best = run = 0
    span = None
    for i, u in enumerate(free):
        run = run + 1 if i and u == free[i - 1] + 1 else 1
        if run > best:
            best, span = run, (u - run + 1, u)
    return floor * SECTION_BIN, best * SECTION_BIN, span


_grown = {}
_scores = {}


def _fat(cells):
    """A section with a bin's give all round (kept: sections repeat a lot, and this is most of the work of comparing)."""
    got = _grown.get(cells)
    if got is None:
        got = _grown[cells] = frozenset((u + du, z + dv) for u, z in cells for du in (-1, 0, 1) for dv in (-1, 0, 1))
    return got


def spans_meet(a, b):
    """Two slots' openings, face to face: their edges (the walls either side) in line, so nobody can slip past a seam."""
    x, y = a.get('span'), b.get('span')
    if not x or not y:
        return x == y
    return abs(x[0] + y[1]) <= SEAM and abs(x[1] + y[0]) <= SEAM


def score(a, b, dz_bins=0):
    """How alike two sections are, b mirrored (they meet face to face) and lifted by dz_bins, with a bin's give."""
    if not a or not b:
        return 0.0
    k = (a, b, dz_bins)
    got = _scores.get(k)
    if got is None:
        m = frozenset((-u, z + dz_bins) for u, z in b)
        got = _scores[k] = (len(a & _fat(m)) + len(m & _fat(a))) / (len(a) + len(m))
    return got


class Piece:
    """One building piece: base key, editor ID, model, footprint on the kit's grid, slots round it."""

    def __init__(self, key, edid, model, box):
        self.key, self.edid, self.model, self.box = key, edid, model, box
        self.foot = None        # (x0, y0, x1, y1) on grid lines
        self.slots = []         # [{'side', 'u', 'floor', 'open', 'width', 'cells'}]
        self.uses = 0
        self.sound = False      # (walking it agrees with its slots: see walks_true)

    def size(self):
        return self.foot[2] - self.foot[0], self.foot[3] - self.foot[1]

    def open_slots(self):
        return [i for i, s in enumerate(self.slots) if s['open']]


def footprint(box, step):
    """A model's box on the grid: half-step lines (kit pieces' origins fall on them), small overhangs not counted."""
    half = step / 2

    def lo(v):
        return math.floor((v + OVERHANG) / half) * half

    def hi(v):
        return math.ceil((v - OVERHANG) / half) * half
    x0, x1, y0, y1 = lo(box[0]), hi(box[3]), lo(box[1]), hi(box[4])
    return x0, y0, x1, y1


def make_slots(piece, tris, step):
    """The sections round a piece: one slot per grid step along each side."""
    x0, y0, x1, y1 = piece.foot
    piece.slots = []
    for side, (axis, edge, way, ulo, uhi, flip) in enumerate((
            (0, x1, 1, y0, y1, True),       # east: looking out along +x, right is -y
            (1, y1, 1, x0, x1, False),      # north: right is +x
            (0, x0, -1, y0, y1, False),     # west: right is +y
            (1, y0, -1, x0, x1, True))):    # south: right is -x
        segs = slice_plane(tris, axis, edge - way * SLICE_IN)
        past = [slice_plane(tris, axis, edge + way * d) for d in BEYOND]
        n = max(1, int(round((uhi - ulo) / step)))
        for k in range(n):
            a, b = ulo + k * (uhi - ulo) / n, ulo + (k + 1) * (uhi - ulo) / n
            cells = frozenset(draw_section(segs, a, b, flip))
            beyond = set()
            for ps in past:
                beyond |= draw_section(ps, a, b, flip)
            floor, width, span = walkable(cells, beyond)
            if floor is not None:
                floor = int(round(floor / FLOOR_LEVEL)) * FLOOR_LEVEL   # (a door's lip isn't another floor: those pieces join rooms to halls)
            piece.slots.append({'side': side, 'u': (a + b) / 2, 'floor': floor, 'width': width,
                                'open': width >= OPEN_MIN, 'sees': see_through(cells, beyond), 'cells': cells, 'span': span})
    piece.sound = walks_true(piece, tris)


def see_through(cells, beyond):
    """A window: a run of the wall, above the floor, with nothing in it. Glass isn't drawn in a section."""
    if not cells:
        return False
    cols = collections.defaultdict(list)
    for u, z in cells:
        cols[u].append(z)
    low = min(z for _u, z in cells)
    blocked = {u for u, z in beyond if low + 13 <= z <= low + 20}
    free = sorted(u for u, zs in cols.items() if u not in blocked and any(z <= low + 12 for z in zs) and
                  any(z >= low + 20 for z in zs) and not any(low + 13 <= z <= low + 20 for z in zs))
    best = run = 0
    for i, u in enumerate(free):
        run = run + 1 if i and u == free[i - 1] + 1 else 1
        best = max(best, run)
    return best * SECTION_BIN >= OPEN_MIN


def walks_true(piece, tris):
    """A person walking in through the piece's ways through can only leave by them. (Measured alone at foot height, so
    it's an honest check on the sections: a side read as closed that you could walk out of means the reading's wrong.)"""
    x0, y0, x1, y1 = piece.foot
    if x1 - x0 > 2048 or y1 - y0 > 2048:
        return False
    ways = [s for s in piece.slots if s['open']]
    if not ways or len({s['floor'] for s in ways}) != 1:
        return not ways
    cut = ways[0]['floor'] + FEET
    b = SECTION_BIN
    walls = set()
    for tri in tris:
        pts = []
        for i in range(3):
            p, q = tri[i], tri[(i + 1) % 3]
            if (p[2] < cut) != (q[2] < cut):
                f = (cut - p[2]) / (q[2] - p[2])
                pts.append((p[0] + f * (q[0] - p[0]), p[1] + f * (q[1] - p[1])))
        if len(pts) == 2:
            n = max(1, int(max(abs(pts[0][0] - pts[1][0]), abs(pts[0][1] - pts[1][1])) / (b / 2)))
            for k in range(n + 1):
                walls.add((int((pts[0][0] + (pts[1][0] - pts[0][0]) * k / n) // b), int((pts[0][1] + (pts[1][1] - pts[0][1]) * k / n) // b)))
    r = range(-PERSON, PERSON + 1)
    fat = {(a + i, c + j) for a, c in walls for i in r for j in r}
    X0, Y0, X1, Y1 = int(x0 // b), int(y0 // b), int(x1 // b), int(y1 // b)
    todo = []
    for s in ways:
        u = int(s['u'] // b)
        todo += [{0: (X1 - 1, c), 1: (c, Y1 - 1), 2: (X0, c), 3: (c, Y0)}[s['side']] for c in range(u - 4, u + 5)]
    seen = set()
    while todo:
        c = todo.pop()
        if c in seen or c in fat:
            continue
        side = 0 if c[0] >= X1 else 1 if c[1] >= Y1 else 2 if c[0] < X0 else 3 if c[1] < Y0 else None
        if side is not None:
            along = (c[1] if side in (0, 2) else c[0]) * b
            if not any(q['side'] == side and q['open'] and abs(q['u'] - along) <= (x1 - x0 + y1 - y0) for q in piece.slots):
                return False
            continue
        seen.add(c)
        todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
    return True


def slot_world(piece, slot, t):
    """Where a slot's middle is, relative to the piece's origin, when the piece has t quarter turns; and the way it faces."""
    x0, y0, x1, y1 = piece.foot
    s = piece.slots[slot]
    x, y = ((x1, s['u']), (s['u'], y1), (x0, s['u']), (s['u'], y0))[s['side']]
    wx, wy = turn_xy(x, y, t)
    return wx, wy, (s['side'] - t) % 4


class Kit:
    def __init__(self, name):
        self.name = name
        self.step = 256
        self.pieces = {}            # key -> Piece
        self.seen = collections.Counter()   # (key a, key b, dx, dy, dz, turn) in a's frame -> times placed
        self._fits = {}

    def structural(self):
        return [p for p in self.pieces.values() if p.foot and p.slots]

    def fits(self, key, slot):
        """Every (other piece's key, its slot, its turn relative to this one, dz, score) whose section matches this slot."""
        got = self._fits.get((key, slot))
        if got is not None:
            return got
        a = self.pieces[key].slots[slot]
        out = []
        if a['open']:
            for p in self.structural():
                for j, b in enumerate(p.slots):
                    if not b['open']:
                        continue
                    dz_bins = (a['floor'] - b['floor']) // SECTION_BIN
                    sc = score(a['cells'], b['cells'], dz_bins)
                    if sc >= FIT_SCORE and spans_meet(a, b):
                        # (turned so its slot faces this one's: both in this piece's frame)
                        t = (b['side'] - (a['side'] + 2)) % 4
                        out.append((p.key, j, t, dz_bins * SECTION_BIN, round(sc, 3)))
        self._fits[(key, slot)] = out
        return out


def _base_info(game, fid, cache):
    if fid in cache:
        return cache[fid]
    out = None
    if fid in game.forms and game.forms[fid][1].tag == 'STAT':
        _t, edid, _n, model = game.describe(fid)
        kit = kit_of(model) if model else None
        if kit:
            out = (kit, edid, model.replace('/', '\\').lower())
    cache[fid] = out
    return out


def gather(game):
    """Every square-placed building piece in every interior: {kit: {cell: [(ref dict, turn)]}}."""
    cache, placed = {}, collections.defaultdict(lambda: collections.defaultdict(list))
    for cell in game.interiors:
        for r in game.refs(cell):
            if not r['base'] or not r['pos']:
                continue
            info = _base_info(game, r['base'], cache)
            if not info:
                continue
            t = quarter(r['rot'][2])
            if t is None or abs(r['rot'][0]) > 0.01 or abs(r['rot'][1]) > 0.01 or abs(r['scale'] - 1) > 0.001:
                continue
            placed[info[0]][cell].append((r, t))
    return placed, cache


def _load_shape(game, model, cache):
    if model in cache:
        return cache[model]
    out = None
    try:
        data = game.read_file('meshes\\' + model.lstrip('\\'))
        if data:
            tris = triangles(nif.mesh_from_nif(data))
            if tris:
                xs = [v[0] for t in tris for v in t]
                ys = [v[1] for t in tris for v in t]
                zs = [v[2] for t in tris for v in t]
                out = (tris, (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))
    except (ValueError, IndexError, struct.error, KeyError):
        out = None
    cache[model] = out
    return out


def _world_box(box, t, pos):
    pts = [turn_xy(x, y, t) for x in (box[0], box[3]) for y in (box[1], box[4])]
    return (min(p[0] for p in pts) + pos[0], min(p[1] for p in pts) + pos[1], max(p[0] for p in pts) + pos[0], max(p[1] for p in pts) + pos[1])


def build(game, min_uses=1):
    """The index, read from the game: {kit name: Kit}."""
    placed, infos = gather(game)
    shapes, kits = {}, {}
    for name, cells in placed.items():
        kit = Kit(name)
        steps = collections.Counter()
        for cell, rs in cells.items():
            prepared = []
            for r, t in rs:
                info = infos[r['base']]
                shape = _load_shape(game, info[2], shapes)
                if not shape:
                    continue
                key = game.key(r['base'])
                p = kit.pieces.get(key)
                if p is None:
                    p = kit.pieces[key] = Piece(key, info[1], info[2], shape[1])
                    p._tris = shape[0]
                p.uses += 1
                prepared.append((r, t, p, _world_box(shape[1], t, r['pos'])))
            for a, ta, pa, A in prepared:
                for b, tb, pb, B in prepared:
                    if a is b:
                        continue
                    if max(A[0] - B[2], B[0] - A[2]) > 8 or max(A[1] - B[3], B[1] - A[3]) > 8:
                        continue
                    wdx, wdy = b['pos'][0] - a['pos'][0], b['pos'][1] - a['pos'][1]
                    dx, dy = unturn_xy(wdx, wdy, ta)
                    dz = b['pos'][2] - a['pos'][2]
                    kit.seen[(pa.key, pb.key, round(dx), round(dy), round(dz), (tb - ta) % 4)] += 1
                    for v in (abs(dx), abs(dy)):
                        if abs(round(v) - v) < 0.6 and round(v) in STEPS and abs(dz) < 1:
                            # (one axis level, the other a step: side by side, not on a diagonal)
                            if abs(dx) < 0.6 or abs(dy) < 0.6:
                                steps[round(v)] += 1
        kit.step = steps.most_common(1)[0][0] if steps else 256
        for p in kit.pieces.values():
            b = p.box
            # (a small thing on a wall or a shelf isn't a building piece)
            if b[3] - b[0] >= kit.step * 0.45 and b[4] - b[1] >= kit.step * 0.2 and b[5] - b[2] >= 100 or \
                    b[4] - b[1] >= kit.step * 0.45 and b[3] - b[0] >= kit.step * 0.2 and b[5] - b[2] >= 100:
                p.foot = footprint(b, kit.step)
                if p.foot[2] > p.foot[0] and p.foot[3] > p.foot[1]:
                    make_slots(p, p._tris, kit.step)
            del p._tris
        kits[name] = kit
    return kits


# ---------- kept on disk ----------

def to_json(kits):
    return {name: {'step': k.step,
                   'pieces': [{'key': p.key, 'edid': p.edid, 'model': p.model, 'box': p.box, 'foot': p.foot, 'uses': p.uses, 'sound': p.sound,
                               'slots': [dict(s, cells=sorted(s['cells'])) for s in p.slots]} for p in k.pieces.values()],
                   'seen': [list(j) + [n] for j, n in k.seen.items()]} for name, k in kits.items()}


def from_json(d):
    kits = {}
    for name, v in d.items():
        k = kits[name] = Kit(name)
        k.step = v['step']
        for e in v['pieces']:
            p = k.pieces[e['key']] = Piece(e['key'], e['edid'], e['model'], tuple(e['box']))
            p.foot, p.uses, p.sound = tuple(e['foot']) if e['foot'] else None, e['uses'], e.get('sound', False)
            p.slots = [dict(s, cells=frozenset(tuple(c) for c in s['cells'])) for s in e['slots']]
        k.seen = collections.Counter({tuple(j[:6]): j[6] for j in v['seen']})
    return kits


def load(game, folder):
    """The index for these game files: from folder if it was built before (about a minute's work otherwise)."""
    path = os.path.join(folder, 'kits.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return from_json(json.load(f))
    kits = build(game)
    os.makedirs(folder, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(to_json(kits), f, separators=(',', ':'))
    os.replace(path + '.tmp', path)
    return kits


# ---------- filling an area with pieces ----------

class Tileset:
    """A kit's one-square pieces in each of their four turns, plus "nothing here", and which may stand side by side.
    A side's socket is its section; two sockets may meet if they're the same shape face to face at the same floor, or
    if the game has built exactly that join. A side with no way through only meets another such side."""

    def __init__(self, kit, min_uses=1, only=None):
        self.kit, self.step = kit, kit.step
        h = kit.step / 2
        interned = {(False, None, None): 0}
        self.sockets = [None]              # socket id -> slot dict (0: closed)
        self.vars = [(None, 0)]            # variant -> (key or None for nothing, turn)
        self.sides = [(0, 0, 0, 0)]        # variant -> socket on each world side
        self.weight = [1.0]
        self.slot_sock = {}

        def sock(s):
            k = (s['open'], s['cells'], s['floor'], tuple(s.get('span') or ())) if s['open'] or s.get('sees') else (False, None, None)
            if k not in interned:
                interned[k] = len(self.sockets)
                self.sockets.append(s)
            return interned[k]
        for p in kit.structural():
            if p.foot != (-h, -h, h, h) or len(p.slots) != 4 or p.uses < min_uses or not p.open_slots() or not self.takes(p):
                continue
            if only and not only(p):
                continue
            by_side = {s['side']: sock(s) for s in p.slots}
            self.slot_sock[p.key] = by_side
            seen_here = set()
            for t in range(4):
                sides = tuple(by_side[(d + t) % 4] for d in range(4))
                if sides in seen_here:
                    continue            # (turned, the same in every way that matters)
                seen_here.add(sides)
                self.vars.append((p.key, t))
                self.sides.append(sides)
                self.weight.append(1.0 + p.uses)
        n = len(self.sockets)
        self.ok = [set() for _ in range(n)]
        self.ok[0].add(0)
        for a in range(1, n):
            for b in range(a, n):
                x, y = self.sockets[a], self.sockets[b]
                if x['open'] == y['open'] and x['floor'] == y['floor'] and spans_meet(x, y) and score(x['cells'], y['cells']) >= FIT_SCORE:
                    self.ok[a].add(b)
                    self.ok[b].add(a)
        self.times = collections.Counter()  # (socket, socket) -> times the game joined them
        for (a, b, dx, dy, dz, t), c in kit.seen.items():
            if dz or (abs(dx), abs(dy)) not in ((kit.step, 0), (0, kit.step)) or a not in self.slot_sock or b not in self.slot_sock:
                continue
            side = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}[(int(dx / kit.step), int(dy / kit.step))]
            sa, sb = self.slot_sock[a][side], self.slot_sock[b][(side + 2 + t) % 4]
            if (sa == 0) == (sb == 0) and (not sa or spans_meet(self.sockets[sa], self.sockets[sb])):
                if sa:
                    self.ok[sa].add(sb)
                    self.ok[sb].add(sa)
                self.times[(sa, sb)] += c
                self.times[(sb, sa)] += c
        # for each socket: which variants may stand beyond it, on each side
        self.allow = [[0] * 4 for _ in range(n)]
        for v, sides in enumerate(self.sides):
            for d in range(4):
                bit = 1 << v
                for a in self.ok[sides[(d + 2) % 4]]:
                    self.allow[a][d] |= bit
        self.all = (1 << len(self.vars)) - 1

    def takes(self, p):
        """Which one-square pieces count. Not stairs and split levels: the levels' joins, not one floor's."""
        return p.sound and len({s['floor'] for s in p.slots if s['open']}) == 1

    def walks(self, sock):
        return bool(sock) and self.sockets[sock]['open']


def _bits(m):
    while m:
        low = m & -m
        yield low.bit_length() - 1
        m ^= low


def dom_to_layout(dom):
    return {c: m.bit_length() - 1 for c, m in dom.items()}


def _settle(ts, dom, fixed, todo):
    """Take from each square whatever can't stand beside what its neighbours may still be. None if a square runs out."""
    todo = list(todo)
    while todo:
        c = todo.pop()
        m = dom.get(c)
        if m is None:
            continue
        for d in range(4):
            n = (c[0] + DX[d][0], c[1] + DX[d][1])
            if n not in dom:
                continue
            socks = {ts.sides[v][d] for v in _bits(m)}
            allowed = 0
            for s in socks:
                allowed |= ts.allow[s][d]
            if dom[n] & ~allowed:
                dom[n] &= allowed
                if not dom[n]:
                    return None
                todo.append(n)
    return True


def _edges(ts, dom, fixed, cells):
    """Squares at the edge of the area can only show what's beyond them: closed, or the fixed piece's side."""
    for c in cells:
        for d in range(4):
            n = (c[0] + DX[d][0], c[1] + DX[d][1])
            if n in dom:
                continue
            s = ts.sides[fixed[n]][(d + 2) % 4] if n in fixed else 0
            dom[c] &= _beside(ts, s, d)
            if not dom[c]:
                return None
    return True


def _beside(ts, sock, d):
    """Variants that may stand with their side d against this socket."""
    return ts.allow[sock][(d + 2) % 4]


def _choose(ts, dom, fixed, c, rng, nothing):
    """A variant for a square: by how much the game uses the piece, and how often it stands against what's beside it."""
    opts, total = [], 0.0
    use_total = sum(ts.weight[v] for v in _bits(dom[c]) if v)
    for v in _bits(dom[c]):
        w = ts.weight[v] if v else max(0.001, nothing / max(0.001, 1 - nothing)) * max(1.0, use_total)
        if v:
            for d in range(4):
                n = (c[0] + DX[d][0], c[1] + DX[d][1])
                m = dom.get(n)
                if n in fixed:
                    other = ts.sides[fixed[n]][(d + 2) % 4]
                elif m and not m & (m - 1):
                    other = ts.sides[m.bit_length() - 1][(d + 2) % 4]
                else:
                    continue
                w *= 1 + min(40, ts.times.get((ts.sides[v][d], other), 0))
        opts.append((v, w))
        total += w
    x = rng.uniform(0, total)
    for v, w in opts:
        x -= w
        if x <= 0:
            return v
    return opts[-1][0]


def build_area(ts, cells, seed=0, fixed=None, nothing=0.15):
    """fill, with the edges closed first and only the connected part from the start kept."""
    fixed = fixed or {}
    cells = [c for c in cells if c not in fixed]
    rng = random.Random(seed)
    for attempt in range(12):
        s = rng.randrange(1 << 30)
        got = _fill_closed(ts, cells, s, fixed, nothing)
        if got:
            return connected(ts, got, fixed)
    return None


def _fill_closed(ts, cells, seed, fixed, nothing):
    rng = random.Random(seed)
    dom = {c: ts.all for c in cells}
    if _edges(ts, dom, fixed, cells) is None:
        return None
    if _settle(ts, dom, fixed, list(dom)) is None:
        return None
    if not fixed:
        mid = cells[len(cells) // 2]
        dom[mid] &= ~1
        if not dom[mid] or _settle(ts, dom, fixed, [mid]) is None:
            return None
    stack, budget = [], 60 + 3 * len(cells)
    while True:
        waiting = [c for c, m in dom.items() if m & (m - 1)]
        if not waiting:
            return dom_to_layout(dom)
        least = min(bin(dom[c]).count('1') for c in waiting)
        c = rng.choice([x for x in waiting if bin(dom[x]).count('1') == least])
        v = _choose(ts, dom, fixed, c, rng, nothing)
        stack.append((dict(dom), c, v))
        dom[c] = 1 << v
        while _settle(ts, dom, fixed, [c]) is None:
            budget -= 1
            if not stack or budget <= 0:
                return None
            saved, c, v = stack.pop()
            dom = saved
            dom[c] &= ~(1 << v)
            if not dom[c]:
                continue
            break


def connected(ts, got, fixed=None):
    """Only what can be walked to: from the fixed squares, or else the biggest connected part. The rest was sealed off
    from it (that's what its sides agree), so taking it away leaves nothing open."""
    fixed = fixed or {}
    every = dict(fixed)
    every.update(got)

    def reach(starts):
        seen, todo = set(starts), list(starts)
        while todo:
            c = todo.pop()
            for d in range(4):
                n = (c[0] + DX[d][0], c[1] + DX[d][1])
                if n in every and n not in seen and every[n] and ts.walks(ts.sides[every[c]][d]) and ts.walks(ts.sides[every[n]][(d + 2) % 4]):
                    seen.add(n)
                    todo.append(n)
        return seen
    if fixed:
        keep = reach(list(fixed))
    else:
        keep, left = set(), {c for c, v in got.items() if v}
        while left:
            part = reach([next(iter(left))])
            left -= part
            if len(part) > len(keep):
                keep = part
    return {c: v for c, v in got.items() if c in keep and v}


def check(ts, placed, fixed=None):
    """Problems with a layout, read afresh: open sides with nothing that fits against them. An empty list is a good layout."""
    every = dict(fixed or {})
    every.update(placed)
    bad = []
    for c, v in placed.items():
        for d in range(4):
            n = (c[0] + DX[d][0], c[1] + DX[d][1])
            a = ts.sides[v][d]
            b = ts.sides[every[n]][(d + 2) % 4] if n in every else 0
            if b not in ts.ok[a]:
                bad.append((c, d, a, b))
    return bad


def as_placed(ts, placed, origin=(0.0, 0.0, 0.0)):
    """A layout as ops for the mod: position and rotation as the game stores them."""
    return [{'op': 'add', 'gen': True, 'base': ts.vars[v][0],
             'p': [origin[0] + i * ts.step, origin[1] + j * ts.step, origin[2], 0.0, 0.0, ts.vars[v][1] * math.pi / 2], 's': 1.0}
            for (i, j), v in sorted(placed.items())]


# ---------- walking it: the honest check ----------

def _foot_walls(game, model, height, cache):
    """A model's walls at this height, as segments in its own frame."""
    k = (model, height)
    if k not in cache:
        segs = []
        for tri in triangles(nif.mesh_from_nif(game.read_file('meshes\\' + model.lstrip('\\')))):
            pts = []
            for i in range(3):
                a, b = tri[i], tri[(i + 1) % 3]
                if (a[2] < height) != (b[2] < height):
                    f = (height - a[2]) / (b[2] - a[2])
                    pts.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
            if len(pts) == 2:
                segs.append(pts)
        cache[k] = segs
    return cache[k]


def can_walk_out(game, ts, placed, cache=None):
    """Could a person starting inside this layout walk out of it? Drawn from the real meshes at foot height, not from
    what the index says about them, so it's a check on the index. Returns (squares walked, got out)."""
    cache = {} if cache is None else cache
    b = SECTION_BIN
    walls = set()
    for c, v in placed.items():
        key, t = ts.vars[v]
        for p0, p1 in _foot_walls(game, ts.kit.pieces[key].model, FEET, cache):
            ax, ay = turn_xy(p0[0], p0[1], t)
            bx, by = turn_xy(p1[0], p1[1], t)
            n = max(1, int(max(abs(ax - bx), abs(ay - by)) / (b / 2)))
            for k in range(n + 1):
                walls.add((int((c[0] * ts.step + ax + (bx - ax) * k / n) // b), int((c[1] * ts.step + ay + (by - ay) * k / n) // b)))
    if not walls:
        return 0, False
    r = range(-PERSON, PERSON + 1)
    fat = {(a + i, y + j) for a, y in walls for i in r for j in r}
    xs, ys = [w[0] for w in walls], [w[1] for w in walls]
    x0, x1, y0, y1 = min(xs) - 3, max(xs) + 3, min(ys) - 3, max(ys) + 3
    start = max(placed, key=lambda c: sum(1 for d in range(4) if ts.walks(ts.sides[placed[c]][d])))
    todo, seen, out = [(int(start[0] * ts.step // b), int(start[1] * ts.step // b))], set(), False
    while todo:
        c = todo.pop()
        if c in seen or c in fat:
            continue
        if not (x0 <= c[0] <= x1 and y0 <= c[1] <= y1):
            out = True
            continue
        seen.add(c)
        todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
    return len(seen), out


# ---------- what the editor asks ----------

def find_piece(kits, key):
    """(kit, piece) for a base's key, or (None, None). Only pieces with sides to join count."""
    for k in kits.values():
        p = k.pieces.get(key)
        if p is not None:
            return (k, p) if p.slots else (None, None)
    return None, None


def _footprint_world(p, x, y, t):
    pts = [turn_xy(a, b, t) for a in (p.foot[0], p.foot[2]) for b in (p.foot[1], p.foot[3])]
    return min(q[0] for q in pts) + x, min(q[1] for q in pts) + y, max(q[0] for q in pts) + x, max(q[1] for q in pts) + y


def piece_sides(kit, piece, pos, turn, others, limit=60):
    """A placed piece's ways through, in the world: each with where it is, the way it faces, whether something's joined
    there, and what could be: [{'face', 'at', 'width', 'taken', 'fits': [{'key', 'edid', 'model', 'p', 'times', 'ways'}]}].
    others: the place's other kit pieces, as (kit piece, x, y, z, turn)."""
    out = []
    boxes = [(_footprint_world(p, x, y, t), z + min(p.box[2], 0), z + p.box[5]) for p, x, y, z, t in others if p.foot]
    for i, s in enumerate(piece.slots):
        if not s['open']:
            continue
        wx, wy, face = slot_world(piece, i, turn)
        ax, ay = pos[0] + wx, pos[1] + wy
        floor = pos[2] + s['floor']
        bx, by = ax + DX[face][0] * kit.step / 4, ay + DX[face][1] * kit.step / 4
        taken = any(b[0] < bx < b[2] and b[1] < by < b[3] and z0 < floor + 60 < z1 for b, z0, z1 in boxes)
        fits = []
        if not taken:
            for key, j, rel, dz, _sc in kit.fits(piece.key, i):
                q = kit.pieces[key]
                t = (turn + rel) % 4
                ox, oy, _f = slot_world(q, j, t)
                x, y, z = ax - ox, ay - oy, pos[2] + dz
                d = unturn_xy(x - pos[0], y - pos[1], turn)
                times = kit.seen.get((piece.key, key, round(d[0]), round(d[1]), round(dz), rel), 0)
                fits.append({'key': key, 'edid': q.edid, 'model': 'meshes' + chr(92) + q.model.lstrip(chr(92)),
                             'p': [round(x, 2), round(y, 2), round(z, 2), 0, 0, round(t * math.pi / 2, 4)],
                             'times': times, 'ways': len(q.open_slots()), 'uses': q.uses})
            fits.sort(key=lambda f: (-f['times'], -f['uses'], f['edid']))
        out.append({'face': face, 'at': [round(ax, 1), round(ay, 1), round(floor, 1)], 'width': s['width'], 'taken': taken, 'fits': fits[:limit]})
    return out


KIT_NAMES = {'vaultruined': 'Vault, ruined', 'nv_casinolo': 'Casino, low end', 'nv_casinohi': 'Casino, high end', 'nv_casino_tops': 'Casino rooftops',
             'nvgamorrah': 'Gamorrah', 'nvlucky38': 'Lucky 38', 'nvhooverdam': 'Hoover Dam', 'hotelhighend': 'Hotel, high end', 'hotel lowend': 'Hotel, low end',
             'nv_goodsprings': 'Goodsprings', 'nv_jtownlodge': 'Jacobstown lodge', 'nv_sunsetsarsaparilla': 'Sunset Sarsaparilla', 'nv_ushome': 'American home',
             'nv_craftsmanhomesinterior': 'Craftsman home', 'wastelandhomes': 'Wasteland home', 'rivetcity': 'Rivet City', 'nvdlc03_thinktank': 'Think Tank',
             'x13': 'X-13', 'x8': 'X-8', 'townsquare': 'Town square'}
KIT_FROM = {'nvdlc01': 'Dead Money', 'nvdlc02': 'Honest Hearts', 'nvdlc03': 'Old World Blues', 'nvdlc04': 'Lonesome Road'}


def label_of(name):
    """A kit's name for people: its folder made readable, with the DLC it's from."""
    parts = name.split(chr(92))
    out = KIT_NAMES.get(parts[-1], parts[-1].replace('_', ' ').capitalize())
    return out + ' (' + KIT_FROM[parts[0]] + ')' if parts[0] in KIT_FROM else out


def layout(game, kits, name, w, h, seed, at, tilesets, cache, tries=16):
    """The fullest of several layouts that walking finds no way out of, as changes for the mod. {'ops', 'start'} or {'note'}."""
    kit = kits[name]
    ts = tilesets.get(name)
    if ts is None:
        ts = tilesets[name] = Tileset(kit)
    if len(ts.slot_sock) < MIN_TILES:
        return {'note': 'This kit has too few pieces that fit on one square to fill an area.'}
    cells = [(i, j) for i in range(w) for j in range(h)]
    origin = (float(at[0]), float(at[1]), float(at[2]))
    best = None
    for k in range(tries):
        got = build_area(ts, cells, seed + k * 7919)
        if not got or (best and len(got) <= len(best)):
            continue
        walked, out = can_walk_out(game, ts, got, cache)
        if walked and not out:
            best = got
            if len(best) >= w * h * 0.6:
                break
    if not best or len(best) < 4:
        return {'note': 'No layout passed the walking test in %d tries: try another size or kit.' % tries}
    start = max(best, key=lambda c: sum(1 for d in range(4) if ts.walks(ts.sides[best[c]][d])))
    return {'ops': as_placed(ts, best, origin),
            'start': [origin[0] + start[0] * ts.step, origin[1] + start[1] * ts.step, origin[2]]}
