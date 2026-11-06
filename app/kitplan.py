"""Generated places that are planned before they are filled: rooms of chosen sizes with purposes, joined by corridors with
a main route and side branches, on more than one level, and only then the game's pieces, each side agreeing with its
neighbour. Then walked, on the real collision shapes, from the first room to every square.

kitindex.py knows what each piece's sides look like. Here those sides are read as words:

    F  full      a side with floor right across it (the middle of a room)
    A  along     floor up to a wall on one side (a run along a room's wall)
    P  passage   an opening with wall both sides (a corridor, a doorway)
    .  closed

and a square's four words say what it is, in any kit, without looking at a name: FFFF a room's middle, .AFA a wall, ..AA
a corner, AFAP a wall with a doorway, AAFF an outer corner (L-shaped rooms), .P.P a straight corridor, ..PP a bend, .PPP
a junction, ...P a dead end. A plan says what every side of every square must be; the solver (the same idea as
kitindex.build_area, with far less left to chance) picks pieces.

    tiles = PlanTiles(kit)                      what a kit can do (tiles.families, tiles.can, tiles.stairs)
    plan = make_plan(tiles, program, seed)      rooms and corridors, no pieces yet
    made = fill(tiles, plan, seed)              [Placed], or None if the plan can't be built from this kit
    place = generate(game, tiles, area, seed)   all of it, with the walk: {'plan', 'made', 'walk', ...} or None

Variety isn't noise: each room gets a small palette (one wall piece mostly, an accent or two), so a room looks of a piece
and the next room looks different, and the game's own join counts (kit.seen) lean each choice towards joins it built.
Pieces bigger than a square go in after the solver, wherever their whole outline agrees with what's round them."""
import collections
import math
import random

import kitindex as K
import navgen

DX = K.DX
PALETTE_BOOST = 12.0    # (how strongly a room keeps to its own few pieces)
REPEAT_COST = 0.004     # (the same piece again beside itself, when the square has anything else it could be)
SEEN_MAX = 20           # (past this many times the game joined two pieces, more doesn't count for more)
CEILING_SLACK = 3       # (bins: two sides joined with ceilings further apart than this show a step in the roof)
SOLVE_BUDGET = 400      # (wrong turns the solver may take on one plan)
NICHE = 0.4             # (a gap narrower than this share of a square is a chamfered corner or a niche, not a way through)
STAIR_MIN = 120         # (a floor this much higher is another level, not a lip)
WIDTH_SLACK = 16        # (two passages this near in width are the same passage)
BIG_SHARE = 0.5         # (how many of the places a bigger piece could go that it does)
ROOM, HALL, VOID = 'room', 'hall', 'void'


def side_word(s, step):
    """A side as a word: F, A, P or . (see the top of the file)."""
    if not s or not s['open'] or not s.get('span') or s['width'] < NICHE * step:
        return '.'
    a, b = s['span']
    edge = step / 2 / K.SECTION_BIN - 2
    lo, hi = a <= -edge, b >= edge
    return 'F' if lo and hi else 'A' if lo or hi else 'P'


def ceiling(s):
    """How high a side's ceiling is, in section bins, or None if it shows none."""
    zs = [z for _u, z in s['cells']]
    return max(zs) if zs else None


def folder_of(model):
    """A piece's family by where its mesh is kept: dungeons/vault/roomu/x.nif -> roomu. '' if it's straight in the kit."""
    parts = model.replace('/', chr(92)).lower().lstrip(chr(92)).split(chr(92))
    lead = 1 if parts[0].startswith(('nvdlc', 'dlc')) else 0
    return chr(92).join(parts[lead + 2:-1])


def not_walkable(game, kit, keys, step):
    """Of these pieces, those whose ways through don't really join up when walked on their collision shapes alone. (A mesh
    can draw a doorway that its collision closes: the sections read what's drawn.)"""
    bad = set()
    for key in keys:
        p = kit.pieces[key]
        ways = [s for s in p.slots if side_word(s, step) != '.']
        if len(ways) < 2:
            continue
        try:
            base = game.from_key(key)
        except (KeyError, ValueError):
            continue
        w = Walk(game, [{'ref': 1, 'type': 'REFR', 'base': base, 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0), 'scale': 1.0, 'leads': False, 'bkey': key}], (0.0, 0.0, 0.0))
        parts = set()
        for s in ways:
            x, y = {0: (p.foot[2] - 24, s['u']), 1: (s['u'], p.foot[3] - 24), 2: (p.foot[0] + 24, s['u']), 3: (s['u'], p.foot[1] + 24)}[s['side']]
            i = w.graph.nearest((x, y, s['floor'] + 8), 64.0, w.keep)
            parts.add(w.label[i] if i is not None else None)
        if len(parts) > 1 or None in parts:
            bad.add(key)
    return bad


def _word_key(w):
    return min(w[i:] + w[:i] for i in range(4))


class Stair:
    """A flight of stairs: one square wide, two long, ports on its short sides."""

    def __init__(self, piece, low, high, rise):
        self.piece, self.low, self.high, self.rise = piece, low, high, rise


class PlanTiles(K.Tileset):
    """A Tileset that also knows each variant's words, its family and its piece, won't join sides whose ceilings differ
    unless the game did, knows the kit's stairs and bigger pieces, and has tried out what the kit can build."""

    def __init__(self, kit, game=None, min_uses=1):
        super().__init__(kit, min_uses)
        self.game = game
        self._walk_cache = {}
        self.word = [side_word(s, self.step) for s in self.sockets]
        self.ceil = [ceiling(s) if s else None for s in self.sockets]
        # (a niche reads as an opening at the side's own slice: it's a closed side, like any other)
        self.sides = [tuple(0 if self.sockets[s] and self.sockets[s]['open'] and self.word[s] == '.' else s for s in sides) for sides in self.sides]
        self._tighten()
        self.piece_of = [v[0] for v in self.vars]
        self.vwords = [''.join(self.word[s] for s in sides) for sides in self.sides]
        self.family = [folder_of(kit.pieces[k].model) if k else None for k in self.piece_of]
        # (a kit's pieces all stand on one floor height, not always nought)
        floors = collections.Counter(s['floor'] for k in self.slot_sock for s in kit.pieces[k].slots if s['open'] and side_word(s, self.step) == 'F')
        self.floor = floors.most_common(1)[0][0] if floors else 0
        self.level_floor = [not k or self._on_floor(kit.pieces[k]) for k in self.piece_of]
        self.masks = {}
        self.banned = set()
        if game is not None:
            self.banned |= not_walkable(game, kit, self.slot_sock, self.step)
        self.same_piece = collections.defaultdict(int)
        for v, k in enumerate(self.piece_of):
            if k:
                self.same_piece[k] |= 1 << v
        if game is not None:
            self._walk_joins(game)
        self.joined = {}
        for (a, b, dx, dy, dz, t), n in kit.seen.items():
            if not dz and a in self.slot_sock and b in self.slot_sock:
                self.joined[(a, b, dx, dy, t)] = n
        self.stairs = self._find_stairs()
        self.big = self._find_big()
        if game is not None:
            self.stairs = [st for st in self.stairs if not not_walkable(game, kit, [st.piece.key], self.step)]
            bad = not_walkable(game, kit, [p.key for p, _w, _h in self.big], self.step)
            self.big = [b for b in self.big if b[0].key not in bad]
        self.can, self.families, self.door_pairs, self.hall_pairs, self.hall_words = {}, {}, set(), set(), {}
        self.exit_widths = set()
        self._probe()

    def _tighten(self):
        """A ceiling step isn't a join, however alike the floors are, unless the game built it."""
        seen = set(self.times)
        for a, others in enumerate(self.ok):
            for b in list(others):
                if not a or not b or (a, b) in seen:
                    continue
                x, y = self.ceil[a], self.ceil[b]
                if x is not None and y is not None and abs(x - y) > CEILING_SLACK:
                    others.discard(b)
        self.allow = [[0] * 4 for _ in self.sockets]
        for v, sides in enumerate(self.sides):
            for d in range(4):
                bit = 1 << v
                for a in self.ok[sides[(d + 2) % 4]]:
                    self.allow[a][d] |= bit

    def takes(self, p):
        """As a plain Tileset, and a doorway piece whose doorway reads higher (a lip, or rubble in it): the walk has the
        last word on those."""
        if super().takes(p):
            return True
        floors = sorted({s['floor'] for s in p.slots if s['open']})
        return len(floors) == 2 and all(s['floor'] == floors[0] or (s['width'] < 0.75 * self.step and side_word(s, self.step) == 'P')
                                        for s in p.slots if s['open'])

    def _on_floor(self, p):
        """Does this piece stand on the kit's one floor? (A doorway's lip or rubble in it can read higher: the walk says if
        it really is a way through.)"""
        ways = [s for s in p.slots if s['open']]
        low = [s for s in ways if abs(s['floor'] - self.floor) <= 40]
        if not low:
            return False
        return all(abs(s['floor'] - self.floor) <= 40 or (s['floor'] > self.floor and side_word(s, self.step) == 'P' and s['width'] < 0.75 * self.step)
                   for s in ways)

    def _walk_joins(self, game):
        """Each passage side of each piece, beside the kit's two most used pieces that fit it, walked on their collision
        shapes, must really join. (Some pieces have a plug standing just past a side that isn't meant to be joined there,
        drawn as a doorway: only collision knows.)"""
        users = collections.defaultdict(set)
        for v, sides in enumerate(self.sides):
            if v and self.piece_of[v] not in self.banned and self.level_floor[v]:
                for d in range(4):
                    if self.word[sides[d]] == 'P':
                        users[sides[d]].add(self.piece_of[v])
        cache = {}
        for sock, keys in users.items():
            partners = collections.Counter()
            for o in self.ok[sock]:
                for k in users.get(o, ()):
                    partners[(k, o)] = self.kit.pieces[k].uses
            ranked = [x for x, _n in partners.most_common(6)]
            for key in keys:
                tried = [x for x in ranked if x[0] != key][:2] or ranked[:1]
                if tried and not any(self._pair_walks(game, key, sock, k, o, cache) for k, o in tried):
                    self.banned.add(key)

    def _pair_walks(self, game, ka, sa, kb, sb, cache):
        """Two pieces turned so these sockets face each other, east and west: does the walk get across?"""
        step = self.step
        ta = self._turn_showing(ka, sa, 0)
        tb = self._turn_showing(kb, sb, 2)
        if ta is None or tb is None:
            return True
        z = self.floor + 8
        refs = [{'ref': 1, 'type': 'REFR', 'base': game.from_key(ka), 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, ta * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': ka},
                {'ref': 2, 'type': 'REFR', 'base': game.from_key(kb), 'pos': (float(step), 0.0, 0.0), 'rot': (0.0, 0.0, tb * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': kb}]
        w = Walk(game, refs, (0.0, 0.0, z), cache=cache, erode=True)
        p = w.graph.nearest((step / 2 - 40, 0.0, z), 40.0, w.keep)
        q = w.graph.nearest((step / 2 + 40, 0.0, z), 40.0, w.keep)
        return p is not None and q is not None and w.label[p] == w.label[q]

    def _turn_showing(self, key, sock, d):
        """The turn at which this piece shows this socket on world side d."""
        for v, k in enumerate(self.piece_of):
            if k == key and self.sides[v][d] == sock:
                return self.vars[v][1]
        return None

    def _find_stairs(self):
        """Flights in this kit, most used first. Their rise is what the game built next to them, or what the sections say."""
        out = []
        step = self.step
        for p in self.kit.structural():
            if not p.foot or len(p.slots) != 6:
                continue
            sx, sy = (p.foot[2] - p.foot[0]) / step, (p.foot[3] - p.foot[1]) / step
            if sorted((sx, sy)) != [1, 2]:
                continue
            ports = [i for i, s in enumerate(p.slots) if side_word(s, step) == 'P']
            if len(ports) != 2:
                continue
            a, b = sorted(ports, key=lambda i: p.slots[i]['floor'])
            if (p.slots[a]['side'] + 2) % 4 != p.slots[b]['side'] or p.slots[b]['floor'] - p.slots[a]['floor'] < STAIR_MIN:
                continue
            if p.slots[a]['side'] % 2 != (1 if sy == 2 else 0):
                continue            # (ports on its long sides: not a flight)
            rises = collections.Counter()
            for (x, _b, _dx, _dy, dz, _t), n in self.kit.seen.items():
                if x == p.key and p.slots[b]['floor'] - 48 <= dz <= p.slots[b]['floor'] + 48:
                    rises[dz] += n
            rise = rises.most_common(1)[0][0] if rises else p.slots[b]['floor']
            out.append(Stair(p, a, b, int(rise)))
        out.sort(key=lambda s: -s.piece.uses)
        return out

    def _find_big(self):
        """Bigger pieces whose footprint is whole squares, with one floor: [(piece, width, depth)]."""
        out = []
        step = self.step
        for p in self.kit.structural():
            if not p.foot or not p.sound or len(p.slots) <= 4:
                continue
            w, h = (p.foot[2] - p.foot[0]) / step, (p.foot[3] - p.foot[1]) / step
            if w != int(w) or h != int(h) or w * h < 2 or w * h > 16:
                continue
            if any(abs(s['floor'] - self.floor) > 40 for s in p.slots if s['open']) or not any(side_word(s, step) != '.' for s in p.slots):
                continue
            out.append((p, int(w), int(h)))
        return out

    def ban(self, key):
        """This piece didn't walk as its sections said: no more of it."""
        self.banned.add(key)
        self.masks.clear()

    def mask(self, kind, fam, need, plain=False):
        """Every variant of this kind of square, in this family, whose sides say what's needed. need: for each side
        o open within a room, p a passage, c closed (a window's fine), x closed with nothing to see. plain: the middle of a
        room, with room all round: nothing but floor (an outer corner there is a pillar nobody asked for)."""
        k = (kind, fam, need, plain)
        got = self.masks.get(k)
        if got is not None:
            return got
        out = 0
        for v in range(1, len(self.vars)):
            if fam is not None and self.family[v] != fam or not self.level_floor[v] or self.piece_of[v] in self.banned:
                continue
            w = self.vwords[v]
            if kind == ROOM and not any(c in 'FA' for c in w) or kind == HALL and any(c in 'FA' for c in w):
                continue
            if plain and w != 'FFFF':
                continue
            for d in range(4):
                n, c = need[d], w[d]
                if n == 'o' and c not in 'FA' or n == 'p' and c != 'P' or n in 'cx' and c != '.' or n == 'x' and self.sides[v][d]:
                    break
            else:
                out |= 1 << v
        self.masks[k] = out
        return out

    def meets(self, slot, sock):
        """Could a piece's slot stand against this socket? (The two floors can differ: the slot's own height is what counts.)"""
        s = self.sockets[sock]
        word = side_word(slot, self.step)
        if word == '.' or self.word[sock] == '.':
            return word == '.' and self.word[sock] == '.' and not (slot.get('sees') or sock)
        return self.word[sock] == word and K.spans_meet(slot, s) and abs(slot['width'] - s['width']) <= WIDTH_SLACK

    def port_mask(self, slot, d):
        """Variants that can stand with their side d against this slot."""
        got = 0
        good = {a for a in range(1, len(self.sockets)) if self.meets(slot, a)}
        for v in range(1, len(self.vars)):
            if self.sides[v][d] in good:
                got |= 1 << v
        return got

    def width_mask(self, d, widths):
        """Variants with an opening on side d that's one of these widths (in 24-unit buckets)."""
        got = 0
        for v in range(1, len(self.vars)):
            s = self.sockets[self.sides[v][d]]
            if s and self.word[self.sides[v][d]] == 'P' and s['width'] // 24 in widths:
                got |= 1 << v
        return got

    def _probe(self):
        """What this kit can really build: small plans, solved. Families that can't close a room don't get used."""
        rooms, halls = collections.Counter(), collections.Counter()
        for v in range(1, len(self.vars)):
            if self.level_floor[v]:
                (rooms if any(c in 'FA' for c in self.vwords[v]) else halls)[self.family[v]] += 1
        closed = []
        for fam in rooms:
            p = Plan(self.step)
            p.add_room('test', fam, [(i, j, 0) for i in range(4) for j in range(3)])
            if fill(self, p, 1, budget=60):
                closed.append(fam)
        for a in closed:
            for b in closed:
                # (two rooms, a doorway between them, on either kind of wall)
                for cells, there in (([(i, j, 0) for i in range(4) for j in range(-3, 0)], ((1, 0, 0), (1, -1, 0))),
                                     ([(i, j, 0) for i in range(4, 8) for j in range(3)], ((3, 1, 0), (4, 1, 0)))):
                    p = Plan(self.step)
                    p.add_room('test', a, [(i, j, 0) for i in range(4) for j in range(3)])
                    p.add_room('test', b, cells)
                    p.link(*there)
                    if fill(self, p, 1, budget=60):
                        self.door_pairs.add((a, b))
                        break
        for fam in halls:
            for room in closed:
                p = Plan(self.step)
                p.add_room('test', room, [(i, j, 0) for i in range(3) for j in range(3)])
                p.add_room('test', room, [(i, j, 0) for i in range(3) for j in range(6, 9)])
                p.add_hall(fam, [(1, j, 0) for j in range(3, 6)])
                p.link((1, 2, 0), (1, 3, 0))
                p.link((1, 5, 0), (1, 6, 0))
                if fill(self, p, 1, budget=60):
                    self.hall_pairs.add((room, fam))
        hall_fams = {f for _r, f in self.hall_pairs}
        rooms_ok = {f: rooms[f] for f in closed if any(x == f for x, _y in self.door_pairs) or any(x == f for x, _y in self.hall_pairs)}
        self.families = {'rooms': rooms_ok, 'halls': {f: halls[f] for f in hall_fams}}
        self.can['rooms'] = bool(rooms_ok)
        self.can['halls'] = bool(hall_fams)
        for f in hall_fams:
            self.hall_words[f] = {_word_key(w) for v, w in enumerate(self.vwords) if v and self.family[v] == f and self.level_floor[v]}
        self.can['outer'] = any(_word_key(w) == 'AAFF' for v, w in enumerate(self.vwords) if v and self.family[v] in rooms_ok)
        if self.game is not None:
            self.stairs = [st for st in self.stairs[:4] if self._stair_walks(st)]
        self.can['stairs'] = bool(self.stairs and hall_fams)

    def _stair_walks(self, st):
        """A room, a corridor, this flight, a corridor, a room, built and walked. A flight that doesn't get anyone up it is
        no use, however it looks."""
        for room, fam in sorted(self.hall_pairs):
            p = Plan(self.step)
            p.rise = st.rise
            p.add_room('test', room, [(i, j, 0) for i in range(3) for j in range(3)])
            p.add_hall(fam, [(1, 3, 0), (1, 4, 0)])
            p.link((1, 2, 0), (1, 3, 0))
            p.add_flight(st, (1, 5), 1, 0)
            p.add_hall(fam, [(1, 7, 1), (1, 8, 1)])
            p.add_room('test', room, [(i, j, 1) for i in range(3) for j in range(9, 12)])
            p.link((1, 8, 1), (1, 9, 1))
            made = fill(self, p, 1, budget=60, big=False)
            if made:
                w = walk_check(self.game, self, p, made, self._walk_cache)
                return not w['missing'] and not w['escaped']
        return False

    def hall_can(self, fam, word):
        return word in self.hall_words.get(fam, ())


# ---------- the plan: no pieces yet ----------

class Plan:
    """Squares, each belonging to one room, one run of corridor, a flight of stairs or nothing (the air over something
    tall), and which sides between them are ways through."""

    def __init__(self, step):
        self.step = step
        self.cells = {}         # (i, j, level) -> owner number
        self.owners = []        # {'kind', 'purpose', 'fam', 'cells', 'main'}
        self.links = set()      # frozensets of two squares: a way through between them
        self.flights = []       # {'stair', 'turn', 'cells': squares it stands on, 'level', 'ports': [(square outside, way to the flight, slot, square inside)]}
        self.rise = 256
        self.exit = None        # (square, way): the door out of the place

    def add_exit(self, c, d):
        """A doorway in this square's side d that leads out of the place: what's beyond it stays empty."""
        n = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
        self.add_void([n], 'outside')
        self.link(c, n)
        self.exit = (c, d)

    def free(self, cells):
        return not any(c in self.cells for c in cells)

    def _own(self, o, cells):
        n = len(self.owners)
        o['n'] = n
        o['cells'] = list(cells)
        self.owners.append(o)
        for c in cells:
            self.cells[c] = n
        return n

    def add_room(self, purpose, fam, cells, main=False):
        return self._own({'kind': ROOM, 'purpose': purpose, 'fam': fam, 'main': main}, cells)

    def add_hall(self, fam, cells, main=False):
        """A run of corridor, each square joined to the next."""
        n = self._own({'kind': HALL, 'purpose': 'corridor', 'fam': fam, 'main': main}, cells)
        for a, b in zip(cells, cells[1:]):
            self.link(a, b)
        return n

    def add_void(self, cells, what='stairs'):
        return self._own({'kind': VOID, 'purpose': what, 'fam': None, 'main': False}, cells)

    def add_flight(self, stair, low, way, lvl):
        """Stairs going up along way from the square low (at level lvl): its two squares at lvl and lvl + 1 are taken."""
        a = low
        b = (a[0] + DX[way][0], a[1] + DX[way][1])
        cells = [(a[0], a[1], lvl), (b[0], b[1], lvl)]
        n = self.add_void(cells + [(a[0], a[1], lvl + 1), (b[0], b[1], lvl + 1)])
        slots = stair.piece.slots
        t = (slots[stair.low]['side'] - (way + 2)) % 4
        before = (a[0] - DX[way][0], a[1] - DX[way][1], lvl)
        after = (b[0] + DX[way][0], b[1] + DX[way][1], lvl + 1)
        self.flights.append({'stair': stair, 'turn': t, 'owner': n, 'level': lvl, 'cells': cells,
                             'ports': [(before, way, slots[stair.low], cells[0]), (after, (way + 2) % 4, slots[stair.high], (b[0], b[1], lvl + 1))]})
        self.link(before, cells[0])
        self.link(after, (b[0], b[1], lvl + 1))

    def link(self, a, b):
        self.links.add(frozenset((a, b)))

    def middle(self, c):
        """Is this a room's square with the room all round it, corners too?"""
        o = self.cells[c]
        return self.owners[o]['kind'] == ROOM and all(self.cells.get((c[0] + a, c[1] + b, c[2])) == o
                                                      for a in (-1, 0, 1) for b in (-1, 0, 1))

    def need(self, c):
        """What each side of a square must be, as mask() wants it."""
        o = self.cells[c]
        room = self.owners[o]['kind'] == ROOM
        out = ''
        for d in range(4):
            n = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
            m = self.cells.get(n)
            if room and m == o:
                out += 'o'
            elif frozenset((c, n)) in self.links:
                out += 'p'
            elif m is not None and self.owners[m]['kind'] != VOID:
                out += 'c'
            else:
                out += 'x'
        return out

    def rooms(self):
        return [o for o in self.owners if o['kind'] == ROOM]

    def squares(self):
        """The squares someone walks on (not the air over stairs)."""
        return [c for c in self.cells if self.owners[self.cells[c]]['kind'] != VOID]


# ---------- from a plan to pieces ----------

class Placed:
    """One piece in a place: its key and turn, where its origin stands (units, from the plan's corner), which owner and
    squares it's for."""
    __slots__ = ('key', 'turn', 'x', 'y', 'z', 'owner', 'cell', 'cells')

    def __init__(self, key, turn, x, y, z, owner, cell, cells=None):
        self.key, self.turn, self.x, self.y, self.z, self.owner, self.cell = key, turn, x, y, z, owner, cell
        self.cells = cells or [cell]


def _palette(ts, plan, rng):
    """Each room's and corridor's own few pieces, for each word pattern: most often one, with an accent, chosen by how much
    the game uses them."""
    out = {}
    for o in plan.owners:
        if o['kind'] == VOID:
            continue
        pal = {}
        kinds = collections.defaultdict(set)
        for v in range(1, len(ts.vars)):
            if ts.family[v] == o['fam'] and ts.level_floor[v] and ts.piece_of[v] not in ts.banned:
                kinds[_word_key(ts.vwords[v])].add(ts.piece_of[v])
        for word, keys in kinds.items():
            names = sorted(keys, key=lambda k: -ts.kit.pieces[k].uses * rng.uniform(0.15, 1.0))
            pal[word] = set(names[:2 if len(names) < 4 else 3])
        out[o['n']] = pal
    return out


def fill(ts, plan, seed=0, budget=SOLVE_BUDGET, big=True):
    """Pieces for a plan: [Placed], or None if this kit can't build it."""
    rng = random.Random(seed)
    palette = _palette(ts, plan, rng)
    levels = collections.defaultdict(list)
    for c in plan.squares():
        levels[c[2]].append(c)
    boundary = collections.defaultdict(lambda: -1)
    for f in plan.flights:
        for outside, way, slot, _inner in f['ports']:
            boundary[outside] &= ts.port_mask(slot, way)
    if plan.exit and ts.exit_widths:
        c, d = plan.exit
        boundary[c] &= ts.width_mask(d, ts.exit_widths)
    solved = {}
    for _level, cells in sorted(levels.items()):
        got = _solve(ts, plan, cells, palette, rng, budget, boundary)
        if got is None:
            return None
        solved.update(got)
    merged = _merge_big(ts, plan, solved, rng) if big else []
    out = []
    for c, v in solved.items():
        key, t = ts.vars[v]
        out.append(Placed(key, t, c[0] * ts.step, c[1] * ts.step, c[2] * plan.rise, plan.cells[c], c))
    out += merged
    for f in plan.flights:
        out.append(_flight_piece(ts, plan, f))
    if _pokes_through(ts, plan, out):
        return None
    return out


def _origin_for(piece, turn, cells, step):
    """Where a piece's origin stands for its footprint to cover these squares exactly."""
    pts = [K.turn_xy(a, b, turn) for a in (piece.foot[0], piece.foot[2]) for b in (piece.foot[1], piece.foot[3])]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    i0, j0 = min(c[0] for c in cells), min(c[1] for c in cells)
    return (i0 - 0.5) * step - x0, (j0 - 0.5) * step - y0


def _flight_piece(ts, plan, f):
    st = f['stair']
    x, y = _origin_for(st.piece, f['turn'], f['cells'], ts.step)
    return Placed(st.piece.key, f['turn'], x, y, f['level'] * plan.rise, f['owner'], f['cells'][0], list(f['cells']))


def _pokes_through(ts, plan, made):
    """Does anything stand up through a floor that's in use on the level above?"""
    for m in made:
        top = ts.kit.pieces[m.key].box[5]
        for k in range(1, int((top - 16) // plan.rise) + 1):
            for c in m.cells:
                n = (c[0], c[1], c[2] + k)
                if n in plan.cells and plan.cells[n] != m.owner:
                    return True
    return False


def _settle(ts, dom, todo):
    """Take from each square whatever can't stand beside what its neighbours may still be. False if a square runs out."""
    todo = list(todo)
    allow, sides = ts.allow, ts.sides
    while todo:
        c = todo.pop()
        m = dom[c]
        socks = [set(), set(), set(), set()]
        while m:
            low = m & -m
            s = sides[low.bit_length() - 1]
            socks[0].add(s[0])
            socks[1].add(s[1])
            socks[2].add(s[2])
            socks[3].add(s[3])
            m ^= low
        for d in range(4):
            n = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
            have = dom.get(n)
            if have is None:
                continue
            allowed = 0
            for s in socks[d]:
                allowed |= allow[s][d]
            if have & ~allowed:
                have &= allowed
                dom[n] = have
                if not have:
                    return False
                todo.append(n)
    return True


def _weigh(ts, plan, dom, c, v, palette):
    """How much this square would like to be this variant."""
    key, t = ts.vars[v]
    w = 1.0 + ts.kit.pieces[key].uses ** 0.5
    if key in palette[plan.cells[c]].get(_word_key(ts.vwords[v]), ()):
        w *= PALETTE_BOOST
    for d in range(4):
        n = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
        m = dom.get(n)
        if not m or m & (m - 1):
            continue
        okey, ot = ts.vars[m.bit_length() - 1]
        # (kit.seen is in the first piece's own frame)
        dx, dy = K.unturn_xy(DX[d][0] * ts.step, DX[d][1] * ts.step, t)
        w *= 1 + min(SEEN_MAX, ts.joined.get((key, okey, round(dx), round(dy), (ot - t) % 4), 0)) * 0.25
        if okey == key and dom[c] & ~ts.same_piece[key]:
            w *= REPEAT_COST
    return w


def _solve(ts, plan, cells, palette, rng, budget, boundary):
    dom = {}
    for c in cells:
        o = plan.owners[plan.cells[c]]
        m = ts.mask(o['kind'], o['fam'], plan.need(c), plan.middle(c)) & boundary[c]
        if not m:
            return None
        dom[c] = m
    if not _settle(ts, dom, list(dom)):
        return None
    stack = []
    while True:
        best, bn = None, 1 << 60
        for c, m in dom.items():
            if m & (m - 1):
                k = bin(m).count('1')
                if k < bn or (k == bn and rng.random() < 0.3):
                    best, bn = c, k
        if best is None:
            return {c: m.bit_length() - 1 for c, m in dom.items()}
        opts, total, m = [], 0.0, dom[best]
        while m:
            low = m & -m
            v = low.bit_length() - 1
            w = _weigh(ts, plan, dom, best, v, palette)
            opts.append((v, w))
            total += w
            m ^= low
        x = rng.uniform(0, total)
        for v, w in opts:
            x -= w
            if x <= 0:
                break
        stack.append((dict(dom), best, v))
        dom[best] = 1 << v
        while not _settle(ts, dom, [best]):
            budget -= 1
            if not stack or budget <= 0:
                return None
            dom, best, v = stack.pop()
            dom[best] &= ~(1 << v)
            if dom[best]:
                break


def _slot_edge(piece, slot, turn, cells, step):
    """Which square of a footprint a slot is on, and the way it faces: (square, way)."""
    x, y, face = K.slot_world(piece, slot, turn)
    ox, oy = _origin_for(piece, turn, cells, step)
    wx, wy = x + ox - DX[face][0] * step / 2, y + oy - DX[face][1] * step / 2
    return (int(round(wx / step)), int(round(wy / step)), cells[0][2]), face


def _merge_big(ts, plan, solved, rng):
    """Bigger pieces in place of several squares, wherever a whole outline agrees with what's round it. Takes the squares
    out of solved and returns the new Placed."""
    out = []
    pieces = list(ts.big)
    rng.shuffle(pieces)
    for piece, w, h in pieces:
        if piece.key in ts.banned:
            continue
        for t in range(4):
            sw, sh = (w, h) if t % 2 == 0 else (h, w)
            anchors = list(solved)
            rng.shuffle(anchors)
            done = 0
            for a in anchors[:60]:
                if a not in solved:
                    continue
                cells = [(a[0] + i, a[1] + j, a[2]) for i in range(sw) for j in range(sh)]
                if any(c not in solved or plan.cells[c] != plan.cells[a] for c in cells):
                    continue
                if not _outline_agrees(ts, plan, solved, piece, t, cells) or rng.random() > BIG_SHARE:
                    continue
                x, y = _origin_for(piece, t, cells, ts.step)
                out.append(Placed(piece.key, t, x, y, a[2] * plan.rise, plan.cells[a], a, cells))
                for c in cells:
                    del solved[c]
                done += 1
                if done >= 3:
                    break
    return out


def _outline_agrees(ts, plan, solved, piece, t, cells):
    inside = set(cells)
    for k, s in enumerate(piece.slots):
        sq, face = _slot_edge(piece, k, t, cells, ts.step)
        if sq not in inside:
            return False
        n = (sq[0] + DX[face][0], sq[1] + DX[face][1], sq[2])
        want = plan.need(sq)[face]
        word = side_word(s, ts.step)
        if want in 'cx':
            if word != '.' or s.get('sees'):
                return False
            continue
        if word == '.' or (want == 'p') != (word == 'P') or n not in solved or not ts.meets(s, ts.sides[solved[n]][(face + 2) % 4]):
            return False
    return True


# ---------- making a plan ----------

class Spec:
    """A room wanted: what it's for, its size range in squares, whether it's on the main route."""

    def __init__(self, purpose, w, h, main=False, fam=None, shape=None):
        self.purpose, self.w, self.h, self.main, self.fam, self.shape = purpose, w, h, main, fam, shape


def program_for(area, rng):
    """Rooms for an area of about this many squares: an entrance, one or two large rooms the route runs through, a far end,
    and smaller rooms off to the side. Sizes vary: three kinds of room, not one size."""
    out = [Spec('entrance', (3, 4), (3, 4), True)]
    left = area - 12
    for _ in range(max(1, area // 150)):
        out.append(Spec('hall', (5, 8), (5, 7), True))
        left -= 40
    while left > 0:
        k = rng.random()
        if k < 0.25:
            out.append(Spec('workroom', (4, 6), (4, 5), rng.random() < 0.3))
            left -= 30
        elif k < 0.55:
            out.append(Spec('long room', (3, 3), (5, 8), rng.random() < 0.2))
            left -= 28
        else:
            out.append(Spec('small room', (3, 4), (3, 3)))
            left -= 18
    out.append(Spec('far end', (4, 6), (4, 6), True))
    return out


def _shape(spec, w, h, rng, can_outer):
    """A room's squares, from (0, 0): a rectangle, or (if the kit has outer corners) one with a corner out of it or a bay on
    it, so rooms don't all come out as boxes."""
    cells = {(i, j) for i in range(w) for j in range(h)}
    k = spec.shape or ('box' if not can_outer or min(w, h) < 4 or rng.random() < 0.45 else rng.choice(('notch', 'notch', 'bay')))
    if k == 'notch':
        nw, nh = rng.randint(1, max(1, w // 2 - 1)), rng.randint(1, max(1, h // 2 - 1))
        cx, cy = rng.random() < 0.5, rng.random() < 0.5
        for i in range(nw):
            for j in range(nh):
                cells.discard((w - 1 - i if cx else i, h - 1 - j if cy else j))
    elif k == 'bay':
        bw = rng.randint(2, max(2, w - 2))
        at = rng.randint(1, max(1, w - bw - 1))
        for i in range(at, at + bw):
            cells.add((i, h))
    return cells


def _turned(cells, d):
    """A room's squares turned so what was its south side now meets someone coming along way d."""
    return {{1: (i, j), 0: (j, -i), 3: (-i, -j), 2: (-j, i)}[d] for i, j in cells}


def _door_spots(cells):
    """Where a room can have a way through: squares on a straight run of wall, not at a corner. [(i, j, way out)]"""
    out = []
    for (i, j) in cells:
        for d in range(4):
            if (i + DX[d][0], j + DX[d][1]) in cells or (i - DX[d][0], j - DX[d][1]) not in cells:
                continue
            a, b = DX[(d + 1) % 4], DX[(d + 3) % 4]
            pa, pb = (i + a[0], j + a[1]), (i + b[0], j + b[1])
            if pa not in cells or pb not in cells:
                continue
            # (the squares either side must have this same wall: a door by an outer corner has no piece)
            if (pa[0] + DX[d][0], pa[1] + DX[d][1]) in cells or (pb[0] + DX[d][0], pb[1] + DX[d][1]) in cells:
                continue
            out.append((i, j, d))
    return out


class Planner:
    """Grows a plan from the entrance: each new room goes through a door or down a corridor from what's already there."""

    def __init__(self, ts, rng, plan=None, bounds=None, level=0, stairs=0.35):
        self.ts, self.rng, self.level = ts, rng, level
        self.plan = plan or Plan(ts.step)
        self.bounds = bounds    # (i0, j0, i1, j1), squares allowed
        self.stair_share = stairs if ts.can.get('stairs') else 0
        self.stair = ts.stairs[0] if ts.stairs else None
        if self.stair and plan is None:
            self.plan.rise = self.stair.rise

    def inside(self, c):
        b = self.bounds
        return not b or (b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3])

    def clear(self, cells):
        return all(c not in self.plan.cells and self.inside(c) for c in cells)

    def room_family(self, spec, door_from=None, hall=None):
        """A family that can join what it's joining: bigger rooms from the kit's biggest family, some from another, for the change."""
        fams = self.ts.families['rooms']
        names = sorted(fams, key=lambda f: -fams[f])
        if hall is not None:
            names = [f for f in names if (f, hall) in self.ts.hall_pairs]
        if door_from is not None:
            names = [f for f in names if (door_from, f) in self.ts.door_pairs]
        if spec.fam in names:
            return spec.fam
        if not names:
            return None
        return names[0] if self.rng.random() < 0.7 or len(names) == 1 else self.rng.choice(names[1:])

    def first_room(self, spec, at=(0, 0)):
        w, h = self.rng.randint(*spec.w), self.rng.randint(*spec.h)
        cells = [(at[0] + i, at[1] + j, self.level) for i, j in sorted(_shape(spec, w, h, self.rng, False))]
        return self.plan.add_room(spec.purpose, self.room_family(spec), cells, spec.main)

    def spots(self, n):
        """Where something could leave an owner: (square, way out)."""
        o = self.plan.owners[n]
        out = []
        if o['kind'] == ROOM:
            level = o['cells'][0][2]
            for i, j, d in _door_spots({(c[0], c[1]) for c in o['cells'] if c[2] == level}):
                out.append(((i, j, level), d))
        elif o['kind'] == HALL and self.ts.hall_can(o['fam'], '.PPP'):
            # (a corridor's side, on a straight run)
            for c in o['cells']:
                ways = [d for d in range(4) if frozenset((c, (c[0] + DX[d][0], c[1] + DX[d][1], c[2]))) in self.plan.links]
                if len(ways) == 2 and (ways[0] + 2) % 4 == ways[1]:
                    out += [(c, (ways[0] + 1) % 4), (c, (ways[0] + 3) % 4)]
        return [(c, d) for c, d in out if (c[0] + DX[d][0], c[1] + DX[d][1], c[2]) not in self.plan.cells]

    def door_near(self, c):
        """Doors keep apart: no second way out from a square, or from the square next to one."""
        own = self.plan.cells[c]
        for n in [c] + [(c[0] + DX[d][0], c[1] + DX[d][1], c[2]) for d in range(4)]:
            if self.plan.cells.get(n) != own:
                continue
            for d in range(4):
                m = (n[0] + DX[d][0], n[1] + DX[d][1], n[2])
                if self.plan.cells.get(m, own) != own and frozenset((n, m)) in self.plan.links:
                    return True
        return False

    def route(self, c, d, length, fam):
        """A corridor's squares from just outside (c, d): length squares, turning at most once if the family has bends, and
        straight at both ends (a doorway only joins a straight piece). ([squares], way it ends going)."""
        out = []
        x, y, l = c
        way = d
        turn_at = self.rng.randint(2, length - 2) if length >= 4 and self.ts.hall_can(fam, '..PP') and self.rng.random() < 0.4 else None
        for k in range(length):
            if k == turn_at:
                way = (way + self.rng.choice((1, 3))) % 4
            x, y = x + DX[way][0], y + DX[way][1]
            out.append((x, y, l))
        return out, way

    def stair_route(self, c, d):
        """A corridor with a flight in it, up or down: one or two squares, the flight, one to three squares.
        (squares before, the flight's low square and level, way up, squares after, level it ends on) or None."""
        r = self.rng
        x, y, l = c
        before = []
        for _ in range(r.randint(1, 2)):
            x, y = x + DX[d][0], y + DX[d][1]
            before.append((x, y, l))
        s1 = (x + DX[d][0], y + DX[d][1])
        s2 = (s1[0] + DX[d][0], s1[1] + DX[d][1])
        if r.random() < 0.6:
            low, way_up, lvl, ends = s1, d, l, l + 1
        else:
            low, way_up, lvl, ends = s2, (d + 2) % 4, l - 1, l - 1
        taken = [(s[0], s[1], k) for s in (s1, s2) for k in (lvl, lvl + 1)]
        after = []
        x, y = s2
        for _ in range(r.randint(1, 3)):
            x, y = x + DX[d][0], y + DX[d][1]
            after.append((x, y, ends))
        if not self.clear(before + taken + after):
            return None
        return before, low, lvl, way_up, after, ends

    def attach(self, spec, parent, long_way=False):
        """One new room, from an owner: through a corridor, up or down stairs, or straight through a wall. True if it went in."""
        plan = self.plan
        po = plan.owners[parent]
        spots = [s for s in self.spots(parent) if not self.door_near(s[0])]
        self.rng.shuffle(spots)
        hall_fams = [f for f in self.ts.families['halls'] if po['kind'] == HALL and f == po['fam'] or po['kind'] == ROOM and (po['fam'], f) in self.ts.hall_pairs]
        for c, d in spots[:12]:
            for length in self._lengths(long_way, po['kind'] == HALL, bool(hall_fams)):
                fam = self.rng.choice(hall_fams) if hall_fams else None
                if length and fam is None:
                    continue
                flight = None
                if length and self.stair and po['kind'] == ROOM and self.rng.random() < self.stair_share:
                    flight = self.stair_route(c, d)
                    if not flight:
                        continue
                    route, way = flight[4], d
                else:
                    route, way = self.route(c, d, length, fam) if length else ([], d)
                    if route and not self.clear(route):
                        continue
                end = route[-1] if route else c
                shape = _shape(spec, self.rng.randint(*spec.w), self.rng.randint(*spec.h), self.rng, self.ts.can['outer'])
                # (a door on the room's south side as drawn, the room turned to face back along the route)
                spot_list = [s for s in _door_spots(shape) if s[2] == 3]
                if not spot_list:
                    continue
                si, sj, _d = self.rng.choice(spot_list)
                turned = _turned({(a - si, b - sj) for a, b in shape}, way)
                first = (end[0] + DX[way][0], end[1] + DX[way][1], end[2])
                cells = [(first[0] + a, first[1] + b, first[2]) for a, b in turned]
                used = route + (flight[0] if flight else [])
                if flight:
                    used = used + [(s[0], s[1], k) for s in (flight[1], (flight[1][0] + DX[flight[3]][0], flight[1][1] + DX[flight[3]][1])) for k in (flight[2], flight[2] + 1)]
                if not self.clear(cells) or set(cells) & set(used):
                    continue
                room_fam = self.room_family(spec, None if length or po['kind'] != ROOM else po['fam'],
                                            fam if length else po['fam'] if po['kind'] == HALL else None)
                if room_fam is None:
                    continue
                if flight:
                    before, low, lvl, way_up, after, _ends = flight
                    plan.add_hall(fam, before, spec.main)
                    plan.link(c, before[0])
                    plan.add_hall(fam, after, spec.main)
                    plan.add_flight(self.stair, low, way_up, lvl)
                elif route:
                    plan.add_hall(fam, route, spec.main)
                    plan.link(c, route[0])
                plan.add_room(spec.purpose, room_fam, cells, spec.main)
                plan.link(end, first)
                return True
        return False

    def _lengths(self, long_way, from_hall, has_halls):
        r = self.rng
        if not has_halls:
            return [0]
        if long_way:
            return [r.randint(4, 8), r.randint(2, 4), 2, 0]
        k = [r.randint(2, 5), 2, 0]
        if from_hall:
            k.insert(0, 0)              # (a door straight off the corridor)
        return k


def make_plan(ts, program, seed=0, bounds=None, plan=None, start=None, level=0, stairs=0.35, with_exit=False):
    """Rooms for this program, joined up: the main route first, one room after another, then the rest off whatever's already
    there, corridors first. A Plan. (plan and start: grow an existing plan from that owner.)"""
    rng = random.Random(seed)
    pl = Planner(ts, rng, plan, bounds, level, stairs)
    if plan is None:
        mid = (bounds[0] + (bounds[2] - bounds[0]) // 2, bounds[1] + (bounds[3] - bounds[1]) // 2) if bounds else (0, 0)
        last = pl.first_room(program[0], mid)
        program = program[1:]
        if with_exit:
            spots = pl.spots(last)
            rng.shuffle(spots)
            for c, d in spots:
                if pl.clear([(c[0] + DX[d][0], c[1] + DX[d][1], c[2])]):
                    pl.plan.add_exit(c, d)
                    break
    else:
        last = start
    owners_of = pl.plan.owners
    for s in [s for s in program if s.main]:
        if pl.attach(s, last, True):
            last = len(owners_of) - 1
        else:
            owners = [o['n'] for o in owners_of if o['kind'] != VOID]
            rng.shuffle(owners)
            for n in owners:
                if pl.attach(s, n, True):
                    last = len(owners_of) - 1
                    break
    for s in [s for s in program if not s.main]:
        # (off a corridor if there is one: rooms along a corridor are what makes it a corridor)
        owners = [o['n'] for o in owners_of if o['kind'] != VOID]
        rng.shuffle(owners)
        owners.sort(key=lambda n: owners_of[n]['kind'] != HALL)
        for n in owners:
            if pl.attach(s, n):
                break
    return pl.plan


# ---------- walking it: the honest check ----------

class Walk:
    """What walking a finished place finds, from the real collision shapes (the same reading navgen makes the navmesh from):
    where a person can get to from the start, on any level, over stairs and through doorways."""

    def __init__(self, game, refs, start, voxel=16.0, cache=None, erode=False):
        self.voxel = voxel
        field = navgen.Field(voxel, math.cos(math.radians(navgen.SLOPE_MAX)))
        report = {'collision': 0, 'drawn': 0, 'unread': 0, 'placed': 0}
        navgen._lay_refs(game, field, refs, {} if cache is None else cache, report)
        self.graph = navgen.Graph(navgen._places(field, navgen.HEADROOM), voxel, navgen.STEP, navgen.HEADROOM)
        self.keep = [True] * len(self.graph.p)
        if erode:
            # (as the navmesh will be: an actor's middle can't go right up to a wall)
            self.keep = self.graph.erode(self.keep, navgen.RADIUS)
        self.pieces, self.label = self.graph.pieces(self.keep)
        i = self.graph.nearest(start, 192.0, self.keep)
        self.reached = set(self.pieces[self.label[i]]) if i is not None else set()

    def where(self):
        """Every place reached: (x, y, z)."""
        v = self.voxel
        return [((q[1] + 0.5) * v, (q[0] + 0.5) * v, q[2]) for q in (self.graph.p[i] for i in self.reached)]


def as_refs(game, made):
    """Placed pieces in the form navgen reads."""
    return [{'ref': n, 'type': 'REFR', 'base': game.from_key(m.key), 'pos': (m.x, m.y, m.z),
             'rot': (0.0, 0.0, m.turn * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': m.key} for n, m in enumerate(made)]


def walk_check(game, ts, plan, made, cache=None, extra=()):
    """Is every part of a plan reachable from its first room, and nothing outside it? {'missing': squares no one can get
    to, 'escaped': places reached outside every square, 'squares': how many there are}."""
    step, rise = ts.step, plan.rise
    squares = set(plan.cells)
    levels = {c[2] for c in squares}
    first = plan.owners[0]['cells']
    cx = sum(c[0] for c in first) / len(first)
    cy = sum(c[1] for c in first) / len(first)
    fc = min(first, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
    floor = ts.floor
    w = Walk(game, as_refs(game, made) + list(extra), (fc[0] * step, fc[1] * step, fc[2] * rise + floor + 8), cache=cache, erode=True)
    covered = collections.Counter()
    escaped = []
    for x, y, z in w.where():
        i, j = int(math.floor(x / step + 0.5)), int(math.floor(y / step + 0.5))
        best = None
        for l in levels:
            if (i, j, l) in squares and l * rise + floor - 80 <= z <= l * rise + floor + rise + 80 and (best is None or abs(z - l * rise) < abs(z - best * rise)):
                best = l
        if best is None:
            # (the edge of a square's walls may hang a little over the grid line)
            fx, fy = x / step + 0.5 - i, y / step + 0.5 - j
            near = [(i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0) and
                    (a == 0 or (fx < 0.2 if a < 0 else fx > 0.8)) and (b == 0 or (fy < 0.2 if b < 0 else fy > 0.8))]
            if not any((n[0], n[1], l) in squares for n in near for l in levels):
                escaped.append((x, y, z))
        else:
            covered[(i, j, best)] += 1
    # (a square counts as walked once a good part of it has been)
    need = 8 if step >= 256 else 2
    missing = [c for c in plan.squares() if covered[c] < need]
    return {'missing': missing, 'escaped': escaped, 'squares': len(plan.squares()), 'reached': len(w.reached)}


def _blame(ts, plan, made, walk):
    """Which pieces stop the walk: on the line between what was reached and what wasn't, the least used. If one's wrong,
    every layout with it is cut in two, so it's worth leaving out."""
    by = {}
    for m in made:
        for c in m.cells:
            by[c] = m
    missing = set(walk['missing'])
    out = collections.Counter()
    for c in missing:
        for d in range(4):
            n = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
            if n in by and n not in missing and c in by and (plan.cells.get(n) == plan.cells.get(c) or frozenset((c, n)) in plan.links):
                pair = sorted((by[c], by[n]), key=lambda m: ts.kit.pieces[m.key].uses)
                out[pair[0].key] += 1
    return out


def generate(game, ts, area=150, seed=0, bounds=None, cache=None, tries=10, program=None, stairs=0.35, survey=None, ruined=False):
    """A whole place: plan, pieces and a clean walk, with doors, lights and things if there's a survey (kitdress.py).
    {'plan', 'made', 'items', 'walk', 'tries', 'wanted'} or None."""
    for k in range(tries):
        rng = random.Random(seed + k * 7919)
        prog = program or program_for(area, rng)
        plan = make_plan(ts, prog, seed + k * 104729, bounds, stairs=stairs, with_exit=survey is not None and k < tries // 2)
        made = None
        for f in range(3):
            made = fill(ts, plan, seed + k + f * 31)
            if made:
                break
        if not made:
            continue
        walk = walk_check(game, ts, plan, made, cache)
        if not walk['missing'] and not walk['escaped']:
            items = []
            if survey is not None:
                import kitdress
                sv = survey.get(ts.kit.name)
                if sv is not None:
                    items = kitdress.place_doors(ts, sv, plan, made, rng) + kitdress.dress(ts, sv, plan, made, rng, ruined=ruined)
                    walk = kitdress.clear_ways(game, ts, plan, made, items, walk_check, cache)
                    if walk['missing'] or walk['escaped']:
                        continue
            return {'plan': plan, 'made': made, 'items': items, 'walk': walk, 'tries': k + 1, 'wanted': len(prog)}
        for key, _n in _blame(ts, plan, made, walk).most_common(2):
            ts.ban(key)
    return None


def repeats(ts, made):
    """(pieces standing beside the same piece where their family has another with the same word pattern, sides looked at)."""
    alts = collections.defaultdict(set)
    fam_word = {}
    for v in range(1, len(ts.vars)):
        alts[(ts.family[v], _word_key(ts.vwords[v]))].add(ts.piece_of[v])
        fam_word[ts.piece_of[v]] = (ts.family[v], _word_key(ts.vwords[v]))
    by = {m.cell: m for m in made}
    n = total = 0
    for m in made:
        for d in (0, 1):
            o = by.get((m.cell[0] + DX[d][0], m.cell[1] + DX[d][1], m.cell[2]))
            if o and o.owner == m.owner and m.key in fam_word:
                total += 1
                if o.key == m.key and len(alts[fam_word[m.key]]) > 1:
                    n += 1
    return n, total


def as_ops(ts, made, origin=(0.0, 0.0, 0.0)):
    """A place's pieces as changes for the mod: position and rotation as the game stores them."""
    return [{'op': 'add', 'gen': True, 'base': m.key,
             'p': [origin[0] + m.x, origin[1] + m.y, origin[2] + m.z, 0.0, 0.0, m.turn * math.pi / 2], 's': 1.0} for m in made]


# ---------- what the editor asks ----------

def tiles_for(game, kits, name, store, survey=None):
    """A kit's PlanTiles, kept in store (a second or two's work the first time)."""
    k = ('plan', name)
    ts = store.get(k)
    if ts is None:
        ts = store[k] = PlanTiles(kits[name], game)
        sv = (survey or {}).get(name)
        if sv is not None:
            import kitdress
            ts.exit_widths = set(kitdress.door_table(ts.kit, sv))
    return ts


def _fill_plan(ts, got):
    """An old-style fill as a plan, so it can be walked the same way."""
    p = Plan(ts.step)
    p.add_hall(None, [(c[0], c[1], 0) for c in got])
    p.links.clear()
    return p


def filled(game, kits, name, w, h, seed, store, cache, tries=16):
    """For kits that can't close a room (caves, mostly): the area filled, kept only if walking reaches all of it and gets no
    further. (plan, [Placed]) or None."""
    ts = store.get(('fill', name))
    if ts is None:
        ts = store[('fill', name)] = K.Tileset(kits[name])
    if len(ts.slot_sock) < K.MIN_TILES:
        return None
    ts.floor = 0
    cells = [(i, j) for i in range(w) for j in range(h)]
    best = None
    for k in range(tries):
        got = K.build_area(ts, cells, seed + k * 7919)
        if not got or len(got) < 4 or (best and len(got) <= len(best[1])):
            continue
        plan = _fill_plan(ts, got)
        made = [Placed(ts.vars[v][0], ts.vars[v][1], c[0] * ts.step, c[1] * ts.step, 0, 0, (c[0], c[1], 0)) for c, v in got.items()]
        walk = walk_check(game, ts, plan, made, cache)
        if walk['escaped'] or len(walk['missing']) > 0.15 * walk['squares']:
            continue
        # (squares a person can't get into: not the kit's fault or ours, but nothing to keep)
        lost = set(walk['missing'])
        if lost:
            made = [m for m in made if m.cell not in lost]
        best = (plan, made)
        if len(made) >= w * h * 0.6:
            break
    return best


def layout(game, kits, name, w, h, seed, at, store, cache, survey=None):
    """A generated place inside this size, as changes for the mod: {'ops', 'start', 'rooms', 'said'} or {'note'}."""
    origin = (float(at[0]), float(at[1]), float(at[2]))
    ts = tiles_for(game, kits, name, store, survey)
    if ts.can['rooms']:
        g = generate(game, ts, max(30, int(w * h * 0.55)), seed, bounds=(0, 0, w - 1, h - 1), cache=cache, survey=survey)
        if not g:
            return {'note': 'No plan passed the walk in this size: try another size or kit.'}
        return _report(ts, g['plan'], g['made'], origin, 'a', g['items'])
    got = filled(game, kits, name, w, h, seed, store, cache)
    if not got:
        return {'note': 'This kit has too few pieces that fit on one square to fill an area, or nothing walked out right: try another.'}
    plan, made = got
    return _report(store[('fill', name)], plan, made, origin, 'f')


def _report(ts, plan, made, origin, how, items=()):
    import kitdress
    ops = as_ops(ts, made, origin) + kitdress.item_ops(items, origin)
    first = plan.owners[0]['cells']
    c = first[len(first) // 2]
    rooms = collections.Counter(o['purpose'] for o in plan.rooms())
    levels = len({m.cell[2] for m in made})
    out = {'ops': ops, 'start': [origin[0] + c[0] * ts.step, origin[1] + c[1] * ts.step, origin[2] + c[2] * plan.rise + getattr(ts, 'floor', 0)],
           'rooms': sorted(rooms.items()), 'levels': levels, 'step': ts.step}
    if how == 'a':
        kinds = collections.Counter(it.what for it in items)
        out['said'] = '%d rooms, %d pieces%s, %d doors, %d lights, %d other things. Walked from the first room: every square reached, no way out.%s' % (
            len(plan.rooms()), len(made), ', %d levels' % levels if levels > 1 else '', kinds['door'] + kinds['exit'], kinds['light'],
            sum(kinds.values()) - kinds['door'] - kinds['exit'] - kinds['light'],
            ' The way out is a door in the first room: select it to link it to another place.' if kinds['exit'] else '')
        out['exit'] = next(([round(c, 2) for c in it.p[:3]] for it in items if it.what == 'exit'), None)
    else:
        out['said'] = '%d pieces, no rooms planned: this kit has no pieces that close a room. Walking found no way out.' % len(made)
    return out
