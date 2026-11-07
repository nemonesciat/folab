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

Beyond flat rooms: a Galley is a room two storeys high with balconies, placed whole with ordinary rooms open against it above and
below; a SetPiece is a room made in one piece, joined as the game joined it; Planner.find_way routes a corridor between any two
owners, stairs included, which is what the ways round (add_loops) and the ways up to balconies are made with.

Variety isn't noise: each room gets a small palette (one wall piece mostly, an accent or two), so a room looks of a piece
and the next room looks different, and the game's own join counts (kit.seen) lean each choice towards joins it built.
Pieces bigger than a square go in after the solver, wherever their whole outline agrees with what's round them."""
import collections
import heapq
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
LATTICE = 3             # (squares between columns in a room big enough to have rows of them)
NICHE = 0.4             # (a gap narrower than this share of a square is a chamfered corner or a niche, not a way through)
STAIR_MIN = 120         # (a floor this much higher is another level, not a lip)
WIDTH_SLACK = 16        # (two passages this near in width are the same passage)
BIG_SHARE = 0.5         # (how many of the places a bigger piece could go that it does)
TALL_SHARE = 1.8        # (a piece this many storeys high can have a floor part way up it)
ROOM, HALL, VOID = 'room', 'hall', 'void'


def side_word(s, step):
    """A side as a word: F, A, P or . (see the top of the file)."""
    if not s or not s['open'] or not s.get('span') or s['width'] < s.get('niche', NICHE) * step:
        return '.'
    a, b = s['span']
    edge = step / 2 / K.SECTION_BIN - 2
    lo, hi = a <= -edge, b >= edge
    return 'F' if lo and hi else 'A' if lo or hi else 'P'


def ceiling(s):
    """How high a side's ceiling is, in section bins, or None if it shows none."""
    zs = [z for _u, z in s['cells']]
    return max(zs) if zs else None


def upper_slot(s, h):
    """A side of a tall piece read at height h, as a slot of its own: what an upper floor meets there, or None if nothing
    walks there. (A section holds the whole height of a side; walkable reads the lowest floor it sees, so what's below goes.)"""
    b = int(h // K.SECTION_BIN)
    cells = frozenset((u, z - b) for u, z in s['cells'] if b - 2 <= z <= b + 16)     # (not the ceiling: it's a floor being looked for)
    floor, width, span = K.walkable(cells)
    if floor is None or abs(floor) > 24 or width < K.OPEN_MIN or not span:
        return None
    return {'side': s['side'], 'u': s['u'], 'floor': int(h), 'width': width, 'open': True, 'sees': False, 'cells': cells, 'span': span}


def folder_of(model):
    """A piece's family by where its mesh is kept: dungeons/vault/roomu/x.nif -> roomu. '' if it's straight in the kit."""
    parts = model.replace('/', chr(92)).lower().lstrip(chr(92)).split(chr(92))
    lead = 1 if parts[0].startswith(('nvdlc', 'dlc')) else 0
    return chr(92).join(parts[lead + 2:-1])


def not_walkable(game, kit, keys, step, floor=None):
    """Of these pieces, those whose ways through don't really join up when walked on their collision shapes alone. (A mesh
    can draw a doorway that its collision closes: the sections read what's drawn.) floor: the kit's floor, for pieces that
    stand on one floor: a low doorway's section can read its lintel as the floor, and the top of the lintel is a roof."""
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
            parts.add(w._start_piece((x, y, (s['floor'] if floor is None else floor) + 8)) if w.pieces else None)
        if len(parts) > 1 or None in parts:
            bad.add(key)
    return bad


def _word_key(w):
    return min(w[i:] + w[:i] for i in range(4))


class Stair:
    """A flight of stairs: one square wide, two long, ports on its short sides. Or (kind 'turn') a stairwell that comes back on
    itself: two squares by two, both ports on one side."""

    def __init__(self, piece, low, high, rise, kind='straight'):
        self.piece, self.low, self.high, self.rise, self.kind = piece, low, high, rise, kind

    def turned(self, way, entering):
        """Coming along way into this stairwell's port (slot number entering): (its turn, the way across to the other port)."""
        slots = self.piece.slots
        other = self.high if entering == self.low else self.low
        t = (slots[entering]['side'] - (way + 2)) % 4
        x0, y0, _f = K.slot_world(self.piece, entering, t)
        x1, y1, _f = K.slot_world(self.piece, other, t)
        dx, dy = x1 - x0, y1 - y0
        return t, ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))


def _read_niche(kit):
    """What's too narrow to be a way through, in this kit. Mostly what NICHE says, but pipes along the walls leave the service
    tunnels' corridors a quarter as wide as a vault's: there, the width of the kit's own commonest straight corridor is a way
    through, and only what's narrower than that isn't."""
    h = kit.step / 2
    best = None
    for p in kit.structural():
        if p.foot != (-h, -h, h, h) or len(p.slots) != 4:
            continue
        ways = [s for s in p.slots if s['open']]
        if len(ways) == 2 and (ways[0]['side'] + 2) % 4 == ways[1]['side'] and abs(ways[0]['width'] - ways[1]['width']) <= 16 and ways[0]['width'] < 0.8 * kit.step:
            if best is None or p.uses > best[0]:
                best = (p.uses, min(s['width'] for s in ways))
    niche = min(NICHE, (best[1] - 8) / kit.step) if best else NICHE
    for p in kit.structural():
        for s in p.slots:
            s['niche'] = niche
    return niche


class PlanTiles(K.Tileset):
    """A Tileset that also knows each variant's words, its family and its piece, won't join sides whose ceilings differ
    unless the game did, knows the kit's stairs and bigger pieces, and has tried out what the kit can build."""

    def __init__(self, kit, game=None, min_uses=1):
        niche = _read_niche(kit)
        super().__init__(kit, min_uses)
        self.game = game
        self._walk_cache = {}
        self.word = [side_word(s, self.step) for s in self.sockets]
        self.ceil = [ceiling(s) if s else None for s in self.sockets]
        # (a niche reads as an opening at the side's own slice: it's a closed side, like any other)
        self.sides = [tuple(0 if self.sockets[s] and self.sockets[s]['open'] and self.word[s] == '.' else s for s in sides) for sides in self.sides]
        if niche < NICHE:
            self._trust_game()
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
            self.banned |= not_walkable(game, kit, self.slot_sock, self.step, self.floor)
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

    def _trust_game(self):
        """In a kit whose corridors are narrow and crowded with pipes, the clear part of a section is off to one side, and can't
        be told from a seam: there, a join the game built between two passages stands, and the walk has the last word."""
        step = self.kit.step
        for (a, b, dx, dy, dz, t), c in self.kit.seen.items():
            if dz or (abs(dx), abs(dy)) not in ((step, 0), (0, step)) or a not in self.slot_sock or b not in self.slot_sock or c < 2:
                continue
            side = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}[(int(dx / step), int(dy / step))]
            sa, sb = self.slot_sock[a][side], self.slot_sock[b][(side + 2 + t) % 4]
            if sa and sb and side_word(self.sockets[sa], step) == 'P' == side_word(self.sockets[sb], step):
                self.ok[sa].add(sb)
                self.ok[sb].add(sa)
                self.times[(sa, sb)] += c
                self.times[(sb, sa)] += c

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

    def _find_turns(self):
        """Stairwells two squares by two whose ports are side by side, at the plan's rise: a flight that comes back on itself."""
        out = []
        step = self.step
        rise = self.stairs[0].rise if self.stairs else None
        for p in self.kit.structural():
            if not p.foot or (p.foot[2] - p.foot[0], p.foot[3] - p.foot[1]) != (2 * step, 2 * step):
                continue
            ports = [i for i, s in enumerate(p.slots) if side_word(s, step) == 'P']
            if len(ports) != 2:
                continue
            a, b = sorted(ports, key=lambda i: p.slots[i]['floor'])
            if p.slots[a]['side'] != p.slots[b]['side'] or p.slots[b]['floor'] - p.slots[a]['floor'] < STAIR_MIN:
                continue
            if rise is not None and abs(p.slots[b]['floor'] - rise) > 48:
                continue
            if abs(p.slots[a]['u'] - p.slots[b]['u']) != step or abs(p.slots[a]['floor'] - self.floor) > 40:
                continue
            out.append(Stair(p, a, b, rise or int(p.slots[b]['floor']), 'turn'))
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
            if w != int(w) or h != int(h) or w * h < 2 or w * h > 16 or p.box[5] - p.box[2] >= TALL_SHARE * (self.stairs[0].rise if self.stairs else 256):
                continue            # (not too big, and not tall: tall pieces stand up through the room over them)
            if any(abs(s['floor'] - self.floor) > 40 for s in p.slots if s['open']) or not any(side_word(s, step) != '.' for s in p.slots):
                continue
            out.append((p, int(w), int(h)))
        return out

    def same_sides(self, key, t):
        """Every variant that shows the same on all sides as this piece turned t: as a mask."""
        want = tuple(K_side(self, key, t, d) for d in range(4))
        want = tuple(0 if self.sockets[s] and self.sockets[s]['open'] and self.word[s] == '.' else s for s in want)
        out = 0
        for v in range(1, len(self.vars)):
            if self.sides[v] == want:
                out |= 1 << v
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
        self.turns = self._find_turns() if hall_fams else []
        self.stair_kinds = self._proven_stairs()
        self.galleys = self._find_galleys() if self.can['stairs'] else []
        self.galleys = [g for g in self.galleys if self._galley_walks(g)]
        self.can['tall'] = bool(self.galleys)
        self.set_pieces = self._find_set_pieces() if self.game is not None and hall_fams else []
        self.can['set'] = bool(self.set_pieces)

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

    def _proven_stairs(self):
        """The kinds of stairs this kit can really do. Each is built between two rooms and walked before anything uses it."""
        if not self.hall_pairs:
            return []
        kinds = (['straight', 'long', 'back'] if self.stairs else []) + (['turn'] if self.turns else [])
        if self.game is None:
            return kinds
        out = []
        for kind in kinds:
            done = False
            for room, fam in sorted(self.hall_pairs):
                for up in (True, False):
                    if self._stairs_walk(kind, room, fam, up):
                        done = True
                        break
                if done:
                    out.append(kind)
                    break
        self.turns = self.turns if 'turn' in out else []
        return out

    def _stairs_walk(self, kind, room, fam, up):
        """A room, stairs of this kind, a room, built and walked."""
        for seed in (1, 2, 3, 4, 5, 6):
            pl = Planner(self, random.Random(seed))
            pl.plan.rise = self.stairs[0].rise if self.stairs else self.turns[0].rise
            n = pl.plan.add_room('test', room, [(i, j, 0) for i in range(4) for j in range(3)])
            c, d = (1, 2, 0), 1
            got = pl.stair_moves(c, d, kind, up)
            if not got:
                continue
            moves, end, way = got
            first = (end[0] + DX[way][0], end[1] + DX[way][1], end[2])
            a, b = DX[way], DX[(way + 1) % 4]
            cells = [(first[0] + a[0] * i + b[0] * j, first[1] + a[1] * i + b[1] * j, first[2]) for i in range(3) for j in range(-1, 2)]
            if not pl.clear(cells):
                continue
            pl.plan.add_room('test', room, cells)
            if not pl.lay_way((c, moves, first), fam):
                continue
            made = fill(self, pl.plan, seed, budget=60, big=False)
            if made:
                w = walk_check(self.game, self, pl.plan, made, self._walk_cache)
                if not w['missing'] and not w['escaped'] and not w['edges']:
                    return True
        return False

    def hall_can(self, fam, word):
        return word in self.hall_words.get(fam, ())

    def _find_set_pieces(self):
        """Whole rooms made in one piece, used as the game used them (see SetPiece). Any that really seal and walk."""
        out = []
        for p in self.kit.structural():
            sx, sy = (p.foot[2] - p.foot[0]) / self.step, (p.foot[3] - p.foot[1]) / self.step
            if sx * sy < 9 or sx * sy > 42 or p.box[5] - p.box[2] < 150:
                continue
            for (a, b, dx, dy, dz, t), _n in self.kit.seen.items():
                if a != p.key or dz or b not in self.slot_sock or b in self.banned:
                    continue
                sp = SetPiece.read(self, p, b, dx, dy, t)
                if sp:
                    out.append(sp)
                    break
        return out

    def _find_galleys(self):
        """Tall rooms of the vault's kind, read from the sections (see Galley). A family counts if it has every part."""
        rise = self.stairs[0].rise if self.stairs else 256
        h = self.step / 2
        fams = collections.defaultdict(list)
        for p in self.kit.structural():
            if p.foot == (-h, -h, h, h) and len(p.slots) == 4 and p.box[5] - p.box[2] >= TALL_SHARE * rise and self._on_floor(p):
                fams[folder_of(p.model)].append(p)
        out = []
        for fam, pieces in fams.items():
            g = Galley(fam, rise, self.step)
            for p in pieces:
                g.read(p)
            if g.complete():
                out.append(g)
        out += self._find_pits(rise)
        return out

    def _find_pits(self, rise):
        """Tall rooms of the other kits' kind (see Pit), by family of pieces that have a floor a storey up behind them."""
        h = self.step / 2
        fams = collections.defaultdict(list)
        for p in self.kit.structural():
            if p.foot == (-h, -h, h, h) and len(p.slots) == 4 and p.box[5] - p.box[2] >= TALL_SHARE * rise:
                fams[folder_of(p.model)].append(p)
        out = []
        for fam, pieces in fams.items():
            g = Pit(fam, rise, self.step, self.kit)
            for p in pieces:
                g.read(p)
            if g.complete():
                out.append(g)
        return out

    def _galley_walks(self, g):
        """A small one, entered from a room with its stairs up, built and walked: every floor reached, nothing open."""
        rooms = self.families.get('rooms', {})
        for room in sorted(rooms, key=lambda f: -rooms[f]):
            g.back = room
            if self.game is None:
                return True
            for seed in range(1, 9):
                pl = Planner(self, random.Random(seed))
                pl.first_room(Spec('entrance', (4, 4), (4, 4), True, fam=room))
                if not pl.attach(Spec('atrium', (6, 6), (3, 4), True, fam=room, tall=g), 0, True) or not any(o.get('tall') for o in pl.plan.owners):
                    continue
                made = fill(self, pl.plan, seed, budget=120, big=False)
                if not made:
                    continue
                w = walk_check(self.game, self, pl.plan, made, self._walk_cache)
                if not w['missing'] and not w['escaped'] and not w['edges']:
                    return True
        g.back = None
        return False


class Galley:
    """How to build a tall room with balconies, read from a kit's pieces. As the game does it (Vault3a, Vault 21, the Securitron
    vault): a rectangle of tall pieces; along both long sides a railing, whose floor part way up looks over the room; between
    them plain middles; across the ends walls, one with a door if wanted; and where wall meets railing a piece that closes
    both. Behind a railing the piece is open on both floors, so an ordinary room stands against it on each: below, under the
    balcony, one you walk straight into; above, the one you come onto the balcony from. With only two rows of squares, a
    railing with a bridge on it meets the one opposite, so the two balconies join."""

    def __init__(self, fam, rise, step):
        self.fam, self.rise, self.step = fam, rise, step
        self.back = None        # (the room family that stands behind the balconies)
        self.mid, self.rail, self.bridge, self.wall, self.wall_door, self.end, self.end_door = [], [], [], [], [], [], []

    def read(self, p):
        by = {s['side']: s for s in p.slots}
        low = {d: side_word(by[d], self.step) for d in range(4)}
        up = {d: upper_slot(by[d], self.rise) for d in range(4)}
        word = {d: side_word(up[d], self.step) if up[d] else '.' for d in range(4)}
        if all(low[d] == 'F' for d in range(4)):
            backs = [d for d in range(4) if word[d] == 'F']
            if not any(up.values()):
                self.mid.append(p)
            elif len(backs) == 1:
                b = backs[0]
                (self.bridge if word[(b + 2) % 4] == 'P' else self.rail).append((p, b))
            return
        shut = [d for d in range(4) if low[d] in '.P']
        if len(shut) != 1 or low[(shut[0] + 2) % 4] != 'F' or low[(shut[0] + 1) % 4] != 'A' or low[(shut[0] + 3) % 4] != 'A':
            return
        c = shut[0]
        door = low[c] == 'P'
        ups = [d for d in ((c + 1) % 4, (c + 3) % 4) if up[d]]
        if len(ups) == 1:
            (self.end_door if door else self.end).append((p, c, ups[0]))
        elif not ups:
            (self.wall_door if door else self.wall).append((p, c))

    @staticmethod
    def hand(closed, back):
        """Which way round an end is: back is a quarter turn one way or the other from closed."""
        return (back - closed) % 4

    def complete(self):
        return bool(self.mid and self.rail and self.wall and self.wall_door and len({self.hand(c, b) for _p, c, b in self.end}) == 2)

    def pick_end(self, rng, closed_d, back_d, door=False):
        """An end with its closed side and its balcony side facing these ways: (piece, turn) or None."""
        rows = [e for e in (self.end_door if door else self.end) if self.hand(e[1], e[2]) == self.hand(closed_d, back_d)]
        if not rows:
            return None
        p, c, _b = pick_row(rows, rng)
        return p, (c - closed_d) % 4


class Pit:
    """A tall room as most kits build one (offices, the Lucky 38, hotels): a sunken hall, its walls two storeys high. One wall
    stops at the upper floor with a railing stood on it, and the room behind that wall, a storey up, looks over the hall. The
    other walls go all the way. Reached by its own door below, and stairs to the room above."""

    def __init__(self, fam, rise, step, kit):
        self.fam, self.rise, self.step, self.kit = fam, rise, step, kit
        self.back = None
        self.bridge = self.end_door = None
        self.mid, self.open_wall, self.tall_wall, self.door_wall, self.corner_tall, self.corner_open = [], [], [], [], [], []
        self.rails = {}

    def read(self, p):
        by = {s['side']: s for s in p.slots}
        low = {d: (by[d]['open'] and by[d]['floor'] is not None and by[d]['floor'] <= 40) for d in range(4)}
        word = {d: side_word(by[d], self.step) for d in range(4)}
        high = {d: bool(by[d]['open'] and by[d]['floor'] is not None and self.rise - 80 <= by[d]['floor'] <= self.rise + 80) for d in range(4)}
        if p.box[2] > -8 or p.box[2] < -64:
            return                  # (all of a pit's pieces stand a little below their own origin, so its floor meets the corridors')
        if all(low[d] and word[d] == 'F' for d in range(4)):
            self.mid.append(p)
            return
        fronts = [d for d in range(4) if low[d] and word[d] == 'F' and low[(d + 1) % 4] and low[(d + 3) % 4] and word[(d + 1) % 4] == 'A' and word[(d + 3) % 4] == 'A']
        if len(fronts) == 1:
            f = fronts[0]
            b = (f + 2) % 4
            if high[b] and word[b] == 'F':
                self.open_wall.append((p, f))
                rail = self._rail_for(p)
                if rail:
                    self.rails[p.key] = rail
            elif by[b]['open'] and word[b] == 'P' and by[b]['floor'] == by[f]['floor']:
                self.door_wall.append((p, f))
            elif not high[b]:
                # (a doorway's top read as a floor at the side of the pit's own floor is still a wall)
                self.tall_wall.append((p, f))
            return
        lows = [d for d in range(4) if low[d] and word[d] == 'A']
        if len(lows) == 2 and (lows[0] + 1) % 4 == lows[1] or len(lows) == 2 and (lows[1] + 1) % 4 == lows[0]:
            a, b = lows if (lows[0] + 1) % 4 == lows[1] else lows[::-1]
            # (the sides facing out are the other two: clockwise of b, and of that)
            o1, o2 = (b + 1) % 4, (b + 2) % 4
            highs = [d for d in (o1, o2) if high[d]]
            if low[o1] or low[o2]:
                return
            if not highs:
                self.corner_tall.append((p, a, b, None))
            elif len(highs) == 1 and word[highs[0]] == 'A':
                self.corner_open.append((p, a, b, highs[0]))

    def _rail_for(self, p):
        """The railing the game stands on top of this wall."""
        rows = [q for q in self.kit.pieces.values() if not q.foot and q.edid.lower().startswith(p.edid.lower() + 'rail')]
        return max(rows, key=lambda q: q.uses) if rows else None

    def complete(self):
        return bool(self.mid and self.tall_wall and self.door_wall and self.corner_tall and any(p.key in self.rails for p, _f in self.open_wall) and self.corner_open)

    def corner(self, rows, rng, faces, up=None):
        """A corner whose two low sides face these ways (the room's inside), and whose side with a floor a storey up faces up:
        (piece, turn, that side or None), or None."""
        got = []
        for p, a, b, h in rows:
            t = (a - faces[0]) % 4
            if (b - t) % 4 == faces[1] and (up is None or (h is not None and (h - t) % 4 == up)):
                got.append((p, t, h))
        return pick_row(got, rng) if got else None


def pick_row(rows, rng):
    """Of (piece, ...) rows, one that the game uses a lot, not always the same one."""
    return max(rows, key=lambda r: r[0].uses * rng.uniform(0.3, 1.0))


class SetPiece:
    """A room made in one piece (the overseer's office), used just as the game used it. Its doorway needn't be on the kit's grid
    by its own measure, so what's asked of it comes from a join the game built: this corridor piece, this far from it, turned so.
    That join is kept exactly, which puts the room off the grid by whatever it was and the corridor on it.

    Walking the piece with that corridor piece finds where it's really open and where you can really stand. Any other way out
    gets a dead end stood in it: a piece that's a way out in the game's cell may lead nowhere in ours."""

    def __init__(self, piece, join_key, dx, dy, t, in_way):
        self.piece, self.join_key, self.dx, self.dy, self.t, self.in_way = piece, join_key, dx, dy, t, in_way
        self.plugs = []         # (key, x, y, z, turn), from the piece's origin
        self.floors = []        # (i, j, level) squares from the joining piece's, where you can stand
        self.cells = []         # (i, j, level) squares it takes up

    @classmethod
    def read(cls, ts, p, b, dx, dy, t):
        step = ts.step
        kit, game = ts.kit, ts.game
        q = kit.pieces[b]
        d = 0 if dx >= p.foot[2] else 2 if dx <= p.foot[0] else 1 if dy >= p.foot[3] else 3 if dy <= p.foot[1] else None
        if d is None:
            return None
        side = (((d + 2) % 4) + t) % 4     # (the joining piece's side that faces the room)
        if side_word(next(s for s in q.slots if s['side'] == side), step) != 'P' or len([s for s in q.slots if side_word(s, step) == 'P']) != 2:
            return None
        sp = cls(p, b, dx, dy, t, (d + 2) % 4)

        def walk_with(plugs):
            refs = [{'ref': 1, 'type': 'REFR', 'base': game.from_key(p.key), 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0), 'scale': 1.0, 'leads': False, 'bkey': p.key},
                    {'ref': 2, 'type': 'REFR', 'base': game.from_key(b), 'pos': (float(dx), float(dy), 0.0), 'rot': (0.0, 0.0, t * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': b}]
            for n, (k, x, y, z, u) in enumerate(plugs):
                refs.append({'ref': 3 + n, 'type': 'REFR', 'base': game.from_key(k), 'pos': (float(x), float(y), float(z)), 'rot': (0.0, 0.0, u * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': k})
            return Walk(game, refs, (float(dx), float(dy), ts.floor + 8.0), cache=ts._walk_cache, erode=True)

        def far(e):
            # (the joining piece's own far end: that's where the corridor goes on)
            return abs(e[0] - dx) <= step * 0.7 and abs(e[1] - dy) <= step * 0.7
        w = walk_with([])
        if len(w.reached) < 400:
            return None
        for _try in range(3):
            left = [e for e in w.open_edges() if not far(e)]
            if not left:
                break
            plug = sp._plug(ts, left, walk_with, far)
            if not plug:
                return None
            sp.plugs.append(plug)
            w = walk_with(sp.plugs)
        else:
            return None
        # (where you can stand, and what it takes up, in squares from the joining piece)
        rise = ts.stairs[0].rise if ts.stairs else 256
        counts = collections.Counter()
        for x, y, z in w.where():
            counts[(int(math.floor((x - dx) / step + 0.5)), int(math.floor((y - dy) / step + 0.5)), int(math.floor((z - ts.floor + rise * 0.3) / rise)))] += 1
        sp.floors = [c for c, n in counts.items() if n >= 12 and c[:2] != (0, 0)]
        low = int(math.floor((p.box[2] + rise * 0.3) / rise))
        cells = set(sp.floors)
        boxes = [(p, 0.0, 0.0, 0, 0)] + [(kit.pieces[k], x, y, z, u) for k, x, y, z, u in sp.plugs]
        for piece, x, y, z, u in boxes:
            bx = K._footprint_world(piece, x, y, u)
            for i in range(int(math.floor((bx[0] - dx) / step + 0.5 + 0.15)), int(math.ceil((bx[2] - dx) / step + 0.5 - 0.15))):
                for j in range(int(math.floor((bx[1] - dy) / step + 0.5 + 0.15)), int(math.ceil((bx[3] - dy) / step + 0.5 - 0.15))):
                    for lv in range(int(math.floor((z + piece.box[2] + rise * 0.3) / rise)), int(math.floor((z + piece.box[5] - 16) / rise)) + 1):
                        cells.add((i, j, lv))
        cells.discard((0, 0, 0))
        sp.cells = sorted(cells)
        _ = low
        return sp if len([c for c in sp.floors if c[2] == 0]) >= 4 else None

    def _plug(self, ts, edges, walk_with, far):
        """A dead-end corridor piece that closes the way out these edges are part of: (key, x, y, z, turn) or None."""
        d = edges[0][3]
        row = [e for e in edges if e[3] == d and abs(e[2] - edges[0][2]) < 40]
        along = 1 if d % 2 == 0 else 0
        mid = (min(e[along] for e in row) + max(e[along] for e in row)) / 2
        front = max(e[1 - along] * DX[d][1 - along] for e in row) * DX[d][1 - along] + DX[d][1 - along] * 8
        z = edges[0][2] - ts.floor
        step = ts.step
        ends = [v for v in range(1, len(ts.vars)) if ts.vwords[v].count('P') == 1 and ts.vwords[v].count('.') == 3 and ts.piece_of[v] not in ts.banned]
        ends.sort(key=lambda v: -ts.kit.pieces[ts.piece_of[v]].uses)
        tried = set()
        for v in ends:
            key, t = ts.vars[v]
            for t2 in range(4):
                # (turned so its way through faces back the way the edge looks)
                if ts.word[K_side(ts, key, t2, (d + 2) % 4)] != 'P' or (key, t2) in tried:
                    continue
                tried.add((key, t2))
                slot = next(s for s in ts.kit.pieces[key].slots if s['side'] == ((d + 2) % 4 + t2) % 4)
                if abs(slot['width'] - max(e[along] for e in row) + min(e[along] for e in row) - 16) > 90:
                    continue
                for off, deep in ((0, 16), (0, 8), (0, 0), (0, 24), (-16, 16), (16, 16)):
                    x, y = front + DX[d][0] * (step / 2 - deep), mid + off
                    if along == 0:
                        x, y = mid + off, front + DX[d][1] * (step / 2 - deep)
                    plug = (key, x, y, z, t2)
                    w = walk_with(self.plugs + [plug])
                    if not [e for e in w.open_edges() if not far(e)]:
                        return plug
        return None


def K_side(ts, key, t, d):
    """The socket a piece turned t shows on world side d."""
    return ts.slot_sock[key][(d + t) % 4]


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
        self.ports = []         # (square, way to a piece already built, its slot): what a new wing meets
        self.air = set()        # squares in a tall room with nothing to stand on
        self.opens = {}         # (square, way): the slot of a tall piece that this room stands open against
        self.placed = []        # things placed whole, a tall room: {'owner', 'pieces': [Placed]}
        self.forced = {}        # square -> mask of the variants it may be: what's joined just as the game joined it

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

    def add_turn(self, stair, a, way, lvl, up, kind='turn'):
        """A stairwell that comes back on itself, entered along way at square a of level lvl (from below, or from above: then
        a is on lvl + 1). Returns the square you come out on, going back the other way."""
        entering = stair.low if up else stair.high
        t, across = stair.turned(way, entering)
        b = (a[0] + across[0], a[1] + across[1])
        ahead = DX[way]
        cells = [(q[0], q[1], lvl) for q in (a, b, (a[0] + ahead[0], a[1] + ahead[1]), (b[0] + ahead[0], b[1] + ahead[1]))]
        n = self.add_void(cells + [(c[0], c[1], lvl + 1) for c in cells])
        low, high = (a, b) if up else (b, a)
        slots = stair.piece.slots
        ports = []
        for q, slot, lv in ((low, slots[stair.low], lvl), (high, slots[stair.high], lvl + 1)):
            out = (q[0] - ahead[0], q[1] - ahead[1], lv)
            ports.append((out, way, slot, (q[0], q[1], lv)))
            self.link(out, (q[0], q[1], lv))
        self.flights.append({'stair': stair, 'turn': t, 'owner': n, 'level': lvl, 'cells': cells, 'ports': ports, 'kind': kind})
        return (b[0] - ahead[0], b[1] - ahead[1], lvl + 1 if up else lvl)

    def add_flight(self, stair, low, way, lvl, kind='straight'):
        """Stairs going up along way from the square low (at level lvl): its two squares at lvl and lvl + 1 are taken."""
        a = low
        b = (a[0] + DX[way][0], a[1] + DX[way][1])
        cells = [(a[0], a[1], lvl), (b[0], b[1], lvl)]
        n = self.add_void(cells + [(a[0], a[1], lvl + 1), (b[0], b[1], lvl + 1)])
        slots = stair.piece.slots
        t = (slots[stair.low]['side'] - (way + 2)) % 4
        before = (a[0] - DX[way][0], a[1] - DX[way][1], lvl)
        after = (b[0] + DX[way][0], b[1] + DX[way][1], lvl + 1)
        self.flights.append({'stair': stair, 'turn': t, 'owner': n, 'level': lvl, 'cells': cells, 'kind': kind,
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
            if (c, d) in self.opens or room and m == o:
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
        """The squares someone walks on (not the air over stairs or in a tall room)."""
        return [c for c in self.cells if self.owners[self.cells[c]]['kind'] != VOID and c not in self.air]

    def to_solve(self):
        """The squares still wanting a piece: not those of something placed whole."""
        done = {b['owner'] for b in self.placed}
        return [c for c in self.squares() if self.cells[c] not in done]

    def mark(self):
        """Where the plan stands now, to go back to if what's being tried doesn't work out."""
        return (dict(self.cells), len(self.owners), set(self.links), len(self.flights), len(self.ports), set(self.air), dict(self.opens), len(self.placed), dict(self.forced))

    def back_to(self, m):
        self.cells, self.links, self.air, self.opens, self.forced = m[0], m[2], m[5], m[6], m[8]
        del self.owners[m[1]:]
        del self.flights[m[3]:]
        del self.ports[m[4]:]
        del self.placed[m[7]:]


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
    for c in plan.to_solve():
        levels[c[2]].append(c)
    boundary = collections.defaultdict(lambda: -1)
    for (c, d), slot in plan.opens.items():
        boundary[c] &= ts.port_mask(slot, d)
    for c, m in plan.forced.items():
        boundary[c] &= m
    for f in plan.flights:
        for outside, way, slot, _inner in f['ports']:
            boundary[outside] &= ts.port_mask(slot, way)
    for outside, way, slot in plan.ports:
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
    for b in plan.placed:
        out += b['pieces']
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


def _floor_lattice(plan, c):
    """Is this square of a room's floor one where something other than plain floor may stand? A regular grid, set in from the
    walls, so columns stand in rows; a room too small for rows has none."""
    cells = plan.owners[plan.cells[c]]['cells']
    x0, x1 = min(q[0] for q in cells), max(q[0] for q in cells)
    y0, y1 = min(q[1] for q in cells), max(q[1] for q in cells)
    if x1 - x0 < LATTICE + 1 or y1 - y0 < LATTICE + 1:
        return False
    return (c[0] - x0) % LATTICE == 1 and (c[1] - y0) % LATTICE == 1 and x1 - c[0] >= 1 and y1 - c[1] >= 1


def _weigh(ts, plan, dom, c, v, palette):
    """How much this square would like to be this variant."""
    key, t = ts.vars[v]
    w = 1.0 + ts.kit.pieces[key].uses ** 0.5
    word = _word_key(ts.vwords[v])
    pal = palette[plan.cells[c]].get(word, ())
    if key in pal:
        w *= PALETTE_BOOST
    floor = word == 'FFFF' and plan.owners[plan.cells[c]]['kind'] == ROOM
    if floor:
        # (one floor piece, and the other only in rows: columns scattered at random are noise)
        main = max((ts.kit.pieces[k].uses for k in pal), default=0)
        plain = ts.kit.pieces[key].uses >= main and key in pal
        w *= (0.02 if _floor_lattice(plan, c) else 50.0) if plain else (20.0 if _floor_lattice(plan, c) else 0.005)
    for d in range(4):
        n = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
        m = dom.get(n)
        if not m or m & (m - 1):
            continue
        okey, ot = ts.vars[m.bit_length() - 1]
        # (kit.seen is in the first piece's own frame)
        dx, dy = K.unturn_xy(DX[d][0] * ts.step, DX[d][1] * ts.step, t)
        w *= 1 + min(SEEN_MAX, ts.joined.get((key, okey, round(dx), round(dy), (ot - t) % 4), 0)) * 0.25
        if okey == key and not floor and dom[c] & ~ts.same_piece[key]:
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

    def __init__(self, purpose, w, h, main=False, fam=None, shape=None, wing=None, stairs=False, tall=None, whole=None):
        self.whole = whole                      # (a word in a set piece's name: a room made in one piece, if there is one and it fits)
        self.purpose, self.w, self.h, self.main, self.fam, self.shape = purpose, w, h, main, fam, shape
        self.wing, self.stairs = wing, stairs   # (rooms of one wing keep together; stairs: gets there up or down a flight if it can)
        self.tall = tall                        # (a Galley, or True for whichever the kit has: two storeys with balconies if it can be)


def program_for(area, rng):
    """Rooms for an area of about this many squares: an entrance, one or two large rooms the route runs through, a far end,
    and smaller rooms off to the side. Sizes vary: three kinds of room, not one size."""
    out = [Spec('entrance', (3, 4), (3, 4), True)]
    left = area - 12
    for _ in range(max(1, area // 150)):
        out.append(Spec('hall', (5, 8), (5, 7), True, tall=rng.random() < 0.6 and ((6, 8), (2, 5))))
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


SHAPES = ('notch', 'bay', 'L', 'L', 'T', 'cross', 'U')


def _shape(spec, w, h, rng, can_outer):
    """A room's squares, from (0, 0): a rectangle, or (if the kit has outer corners) one with a corner out of it or a bay on
    it, so rooms don't all come out as boxes."""
    cells = {(i, j) for i in range(w) for j in range(h)}
    k = spec.shape or ('box' if not can_outer or min(w, h) < 4 or rng.random() < 0.35 else rng.choice(SHAPES))
    if k == 'L' and min(w, h) >= 4:
        nw, nh = w // 2, h // 2
        fx, fy = rng.random() < 0.5, rng.random() < 0.5
        cells -= {(w - 1 - i if fx else i, h - 1 - j if fy else j) for i in range(nw) for j in range(nh)}
    elif k == 'T' and w >= 5 and h >= 4:
        leg = max(2, w // 3)
        at = (w - leg) // 2
        bar = max(2, h // 2)
        cells -= {(i, j) for i in range(w) for j in range(h - bar) if not at <= i < at + leg}
    elif k == 'cross' and w >= 5 and h >= 5:
        cw, ch = (w - max(2, w // 3)) // 2, (h - max(2, h // 3)) // 2
        cells -= {(i, j) for i in range(w) for j in range(h) if (i < cw or i >= w - cw) and (j < ch or j >= h - ch)}
    elif k == 'U' and w >= 6 and h >= 4:
        cells -= {(i, j) for i in range(2, w - 2) for j in range(h - max(1, h // 2), h)}
    elif k == 'notch':
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
        self.can_stairs = bool(self.stair_share and getattr(ts, 'stair_kinds', None))
        self.straight = False   # (the corridor being laid keeps straight: the way in from the entrance)
        self.first_way = None
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
        bends = self.ts.hall_can(fam, '..PP') and not self.straight
        turn_at = self.rng.randint(2, length - 2) if length >= 4 and bends and self.rng.random() < 0.5 else None
        # (and a long one, back on its first line further along: a dog-leg)
        back_at = turn_at + self.rng.randint(1, 2) if turn_at and length >= turn_at + 3 and self.rng.random() < 0.5 else None
        turned = None
        for k in range(length):
            if k == turn_at:
                turned = self.rng.choice((1, 3))
                way = (way + turned) % 4
            elif k == back_at:
                way = (way + 4 - turned) % 4
            x, y = x + DX[way][0], y + DX[way][1]
            out.append((x, y, l))
        return out, way

    def stair_moves(self, c, d, kind='straight', up=None):
        """A corridor with stairs in it going up or down from a doorway at (c, d): (moves as find_way gives them, square it
        ends on, way it ends going), or None if there's no room. One or two squares, the stairs, one to three squares:

            straight   one flight, one storey
            long       a flight, a landing, a flight: two storeys in one long line
            back       a flight, a landing that turns round, a flight back above the first: two storeys in little floor
            turn       a stairwell made in one piece that comes back on itself: one storey"""
        r = self.rng
        up = r.random() < 0.6 if up is None else up
        s = 1 if up else -1
        moves, taken = [], set()
        x, y, l = c
        way = d

        def go(w=None):
            nonlocal x, y, way
            way = way if w is None else w
            x, y = x + DX[way][0], y + DX[way][1]

        def square():
            taken.add((x, y, l))
            moves.append(('s', (x, y, l)))

        def flight(label):
            nonlocal x, y, l
            a = (x + DX[way][0], y + DX[way][1])
            b = (a[0] + DX[way][0], a[1] + DX[way][1])
            lvl = l if up else l - 1
            taken.update((q[0], q[1], k) for q in (a, b) for k in (lvl, lvl + 1))
            moves.append(('f', a if up else b, way if up else (way + 2) % 4, lvl, label))
            x, y = b
            l = l + s
        for _ in range(r.randint(1, 2)):
            go()
            square()
        if kind == 'straight':
            flight('straight')
        elif kind == 'long':
            flight('long')
            for _ in range(r.randint(1, 2)):
                go()
                square()
            flight('long')
        elif kind == 'back':
            side = r.choice((1, 3))
            flight('back')
            go()
            square()
            go()
            square()
            turn = (way + side) % 4
            go(turn)
            square()
            go((turn + side) % 4)
            square()
            flight('back')
        elif kind == 'turn':
            st = self.ts.turns[0]
            entering = st.low if up else st.high
            _t, across = st.turned(way, entering)
            a = (x + DX[way][0], y + DX[way][1])
            lvl = l if up else l - 1
            b = (a[0] + across[0], a[1] + across[1])
            ahead = DX[way]
            taken.update((q[0], q[1], k) for q in (a, b, (a[0] + ahead[0], a[1] + ahead[1]), (b[0] + ahead[0], b[1] + ahead[1])) for k in (lvl, lvl + 1))
            moves.append(('u', st, a, way, lvl, up))
            x, y = b
            l = l + s
            way = (way + 2) % 4
        for _ in range(r.randint(1, 3)):
            go()
            square()
        if len(taken) != sum(1 if m[0] == 's' else 4 if m[0] == 'f' else 8 for m in moves) or not self.clear(sorted(taken)):
            return None
        return moves, (x, y, l), way

    def attach(self, spec, parent, long_way=False, opening=None):
        """One new room, from an owner: through a corridor, up or down stairs, or straight through a wall. True if it went in.
        opening: (square, way out, family, slot) an opening made in something already built, to start from instead."""
        plan = self.plan
        po = plan.owners[parent]
        if opening:
            po = {'kind': HALL if opening[2] in self.ts.families['halls'] else ROOM, 'fam': opening[2], 'cells': []}
            spots = [(opening[0], opening[1])]
        else:
            spots = [s for s in self.spots(parent) if not self.door_near(s[0])]
            self.rng.shuffle(spots)
            if self.straight and self.first_way is not None:
                # (straight on from the way in: the middle of the far wall first)
                far = [s for s in spots if s[1] == (self.first_way + 2) % 4]
                far.sort(key=lambda s: abs(sum(s[0][:2]) - sum(q[0] + q[1] for q, _d in far) / max(1, len(far))))
                spots = far + [s for s in spots if s[1] != (self.first_way + 2) % 4]
        hall_fams = [f for f in self.ts.families['halls'] if po['kind'] == HALL and f == po['fam'] or po['kind'] == ROOM and (po['fam'], f) in self.ts.hall_pairs]
        tall = spec.tall and self.ts.galleys
        for c, d in spots[:12]:
            for length in self._lengths(long_way, po['kind'] == HALL, bool(hall_fams)):
                fam = self.rng.choice(hall_fams) if hall_fams else None
                if length and fam is None:
                    continue
                flight = None
                if length and self.can_stairs and po['kind'] == ROOM and not tall and not (spec.whole and self.ts.set_pieces) and (spec.stairs or self.rng.random() < self.stair_share):
                    kinds = self.ts.stair_kinds
                    flight = self.stair_moves(c, d, self.rng.choice([k for k in kinds for _ in range(1 if k in ('long', 'back') else 3)]))
                    if not flight:
                        continue
                    route, way = [flight[1]], flight[2]
                else:
                    route, way = self.route(c, d, length, fam) if length else ([], d)
                    if route and not self.clear(route):
                        continue
                end = route[-1] if route else c
                if spec.whole and route and self.whole_room(spec, c, route, way, fam):
                    return True
                if tall and route:
                    if self.tall_room(spec, c, route, way, fam):
                        if opening:
                            plan.ports.append((route[0], (opening[1] + 2) % 4, opening[3]))
                        return True
                    continue
                shape = _shape(spec, self.rng.randint(*spec.w), self.rng.randint(*spec.h), self.rng, self.ts.can['outer'])
                # (a door on the room's south side as drawn, the room turned to face back along the route)
                spot_list = [s for s in _door_spots(shape) if s[2] == 3]
                if not spot_list:
                    continue
                si, sj, _d = self.rng.choice(spot_list)
                if self.straight:
                    # (the door in the middle of the wall: you see straight down the room as you come in)
                    mx = sum(s[0] for s in spot_list) / len(spot_list)
                    si, sj, _d = min(spot_list, key=lambda s: abs(s[0] - mx))
                turned = _turned({(a - si, b - sj) for a, b in shape}, way)
                first = (end[0] + DX[way][0], end[1] + DX[way][1], end[2])
                cells = [(first[0] + a, first[1] + b, first[2]) for a, b in turned]
                used = self._way_cells(flight[0]) if flight else route
                if not self.clear(cells) or set(cells) & set(used):
                    continue
                room_fam = self.room_family(spec, None if length or po['kind'] != ROOM else po['fam'],
                                            fam if length else po['fam'] if po['kind'] == HALL else None)
                if room_fam is None:
                    continue
                if flight:
                    self.lay_way((c, flight[0], first), fam, spec.main, spec.wing)
                elif route:
                    plan.owners[plan.add_hall(fam, route, spec.main)]['wing'] = spec.wing
                    plan.link(c, route[0])
                n = plan.add_room(spec.purpose, room_fam, cells, spec.main)
                plan.owners[n]['wing'] = spec.wing
                if not flight:
                    plan.link(end, first)
                if opening:
                    plan.ports.append(((route[0] if route else first), (opening[1] + 2) % 4, opening[3]))
                return True
        return False

    def whole_room(self, spec, c, route, way, fam):
        """A room made in one piece at the end of this corridor, the last square of which is the piece the game joined to it."""
        plan = self.plan
        ts = self.ts
        rows = [s for s in ts.set_pieces if spec.whole in s.piece.edid.lower()]
        if not rows:
            return False
        sp = self.rng.choice(rows)
        end = route[-1]
        turn = (sp.in_way - way) % 4     # (turn the room so the way into it is the way the corridor's going)

        def square(c2):
            a, b = K.turn_xy(c2[0], c2[1], turn)
            return (end[0] + int(round(a)), end[1] + int(round(b)), end[2] + c2[2])
        cells = [square(q) for q in sp.cells]
        floors = {square(q) for q in sp.floors}
        if not self.clear(route + cells) or set(route) & set(cells):
            return False
        mark = plan.mark()
        plan.owners[plan.add_hall(fam, route, spec.main)]['wing'] = spec.wing
        plan.link(c, route[0])
        n = plan.add_room(spec.purpose, spec.fam, cells)
        plan.owners[n].update(wing=spec.wing, whole=True, main=spec.main)
        plan.air |= set(cells) - floors
        ox, oy = K.turn_xy(-sp.dx, -sp.dy, turn)
        x0, y0 = end[0] * ts.step + ox, end[1] * ts.step + oy
        z0 = end[2] * plan.rise
        pieces = [Placed(sp.piece.key, turn, x0, y0, z0, n, cells[0], cells)]
        for key, x, y, z, u in sp.plugs:
            a, b = K.turn_xy(x, y, turn)
            pieces.append(Placed(key, (u + turn) % 4, x0 + a, y0 + b, z0 + z, n, cells[0], [cells[0]]))
        plan.placed.append({'owner': n, 'pieces': pieces})
        # (the corridor's last square is the very piece the game joined to it, turned as it was)
        plan.forced[end] = ts.same_sides(sp.join_key, (sp.t + turn) % 4)
        door = next((q for q in floors if abs(q[0] - end[0]) + abs(q[1] - end[1]) == 1 and q[2] == end[2] and (q[0] - end[0], q[1] - end[1]) == DX[way]), None)
        plan.link(end, door or (end[0] + DX[way][0], end[1] + DX[way][1], end[2]))
        if door is None and (end[0] + DX[way][0], end[1] + DX[way][1], end[2]) not in cells:
            plan.back_to(mark)
            return False
        return True

    def tall_room(self, spec, c, route, way, fam):
        """A tall room at the end of this corridor, its door in the middle of its end wall, so you come in looking along it.
        Rooms under and over each balcony, and stairs up to them. True if it all went in; if not the plan is as it was."""
        ts = self.ts
        g = spec.tall if isinstance(spec.tall, Galley) else self.rng.choice(ts.galleys) if ts.galleys else None
        if not g or not g.back or (g.back, fam) not in ts.hall_pairs:
            return False
        sizes = spec.tall if isinstance(spec.tall, tuple) else (spec.w, spec.h)
        W, H = self.rng.randint(*sizes[0]), self.rng.randint(*sizes[1])
        if isinstance(g, Pit):
            mark = self.plan.mark()
            if self._lay_pit(g, spec, c, route, way, fam, max(4, W), max(3, H)):
                return True
            self.plan.back_to(mark)
            return False
        bridged = H <= 2 and bool(g.bridge and g.end_door)
        H = 2 if bridged else max(3, H)
        mark = self.plan.mark()
        if self._lay_tall(g, spec, c, route, way, fam, max(4, W), H, bridged):
            return True
        self.plan.back_to(mark)
        return False

    def _lay_tall(self, g, spec, c, route, way, fam, W, H, bridged):
        plan, rng = self.plan, self.rng
        step = self.ts.step
        room = g.back
        l = route[-1][2]
        vm = H // 2 if H >= 3 else rng.randrange(2)
        ux, uy = DX[way]
        vx, vy = DX[(way + 1) % 4]
        ox = route[-1][0] + ux - vm * vx
        oy = route[-1][1] + uy - vm * vy

        def at(u, v, lv=l):
            return (ox + u * ux + v * vx, oy + u * uy + v * vy, lv)
        depth = 2
        foot = [at(u, v) for u in range(W) for v in range(-depth, H + depth)]
        if not self.clear(route + foot + [(x, y, l + 1) for x, y, _z in foot] + [at(u, v, l + 2) for u in range(W) for v in range(H)]) or set(route) & set(foot):
            return False
        plan.owners[plan.add_hall(fam, route, spec.main)]['wing'] = spec.wing
        plan.link(c, route[0])
        ground = [at(u, v) for u in range(W) for v in range(H)]
        balcony = {at(u, v, l + 1) for u in range(W) for v in (0, H - 1)}
        air = {at(u, v, lv) for u in range(W) for v in range(H) for lv in (l + 1, l + 2)}
        n = plan.add_room(spec.purpose, room, ground + sorted(air))
        o = plan.owners[n]
        o.update(wing=spec.wing, tall=True, main=spec.main)
        plan.air |= air - balcony
        pieces = []
        back_d = {0: (way + 3) % 4, H - 1: (way + 1) % 4}
        lows, highs = {}, {}
        door_at = at(0, vm)
        bridge_u = W // 2 if bridged else None
        for u in range(W):
            for v in range(H):
                cell = at(u, v)
                in_row = v in (0, H - 1)
                back_side = None
                if u in (0, W - 1):
                    shut = (way + 2) % 4 if u == 0 else way
                    door = cell == door_at
                    if in_row:
                        got = g.pick_end(rng, shut, back_d[v], door)
                        if not got:
                            return False
                        piece, t = got
                        back_side = (back_d[v] + t) % 4
                    else:
                        piece, cl = pick_row(g.wall_door if door else g.wall, rng)
                        t = (cl - shut) % 4
                    if door:
                        plan.ports.append((route[-1], way, next(s for s in piece.slots if s['side'] == (shut + t) % 4)))
                        plan.link(route[-1], cell)
                elif in_row:
                    piece, b = pick_row(g.bridge if u == bridge_u else g.rail, rng)
                    t = (b - back_d[v]) % 4
                    back_side = (back_d[v] + t) % 4
                else:
                    piece, t = pick_row([(q,) for q in g.mid], rng)[0], 0
                pieces.append(Placed(piece.key, t, cell[0] * step, cell[1] * step, l * plan.rise, n, cell))
                if back_side is not None:
                    slot = next(s for s in piece.slots if s['side'] == back_side)
                    lows[(u, v)], highs[(u, v)] = slot, upper_slot(slot, g.rise)
        plan.placed.append({'owner': n, 'pieces': pieces})
        rooms = []
        for v, rows, near in ((0, range(-depth, 0), -1), (H - 1, range(H, H + depth), H)):
            for lv, name, keys in ((l, 'under a balcony', lows), (l + 1, 'over a balcony', highs)):
                m = plan.add_room(name, room, [at(u, q, lv) for u in range(W) for q in rows])
                plan.owners[m].update(wing=spec.wing, part_of=n)
                rooms.append(m)
                for u in range(W):
                    if keys[(u, v)] is None:
                        return False
                    plan.opens[(at(u, near, lv), (back_d[v] + 2) % 4)] = keys[(u, v)]
        o['sides'] = rooms
        # (a way up, from under a balcony to the room over it: on one side if a bridge joins the two, or on each)
        for k in ((0,) if bridged else (0, 2)):
            if not self.join(rooms[k], rooms[k + 1], fam, cost=50):
                return False
        return True

    def add_loops(self, want):
        """More than one way round: corridors between parts of the plan that are near on the plan but a long walk apart now, by
        stairs if they're on different levels. How many went in."""
        plan = self.plan
        if not fill(self.ts, plan, 1, budget=120, big=False):
            return 0                # (this plan's no good as it is: nothing added can help)
        near = collections.defaultdict(set)
        for link in plan.links:
            a, b = tuple(link)
            x, y = plan.cells.get(a), plan.cells.get(b)
            if x is not None and y is not None and x != y:
                near[x].add(y)
                near[y].add(x)
        for (c, d) in plan.opens:
            x, y = plan.cells.get(c), plan.cells.get((c[0] + DX[d][0], c[1] + DX[d][1], c[2]))
            if x is not None and y is not None:
                near[x].add(y)
                near[y].add(x)

        def walk_from(s):
            dist, todo = {s: 0}, [s]
            while todo:
                q = todo.pop(0)
                for n in near[q]:
                    if n not in dist:
                        dist[n] = dist[q] + 1
                        todo.append(n)
            return dist
        live = [o['n'] for o in plan.owners if o['kind'] == ROOM and not o.get('tall') and o['purpose'] != 'test'] + \
               [o['n'] for o in plan.owners if o['kind'] == HALL]
        pairs = []
        for a in live:
            da = walk_from(a)
            ca = plan.owners[a]['cells']
            for b in live:
                if b <= a or da.get(b, 99) < 3:
                    continue
                gap = min(abs(p[0] - q[0]) + abs(p[1] - q[1]) + 2 * abs(p[2] - q[2]) for p in ca[:40] for q in plan.owners[b]['cells'][:40])
                if gap <= 10:
                    pairs.append((gap - 2 * da.get(b, 99) + self.rng.random() * 4, a, b))
        pairs.sort()
        added = 0
        for _k, a, b in pairs[:30]:
            if added >= want:
                break
            if plan.owners[a]['kind'] == HALL:
                a, b = b, a
            fam = self._hall_between(a, b)
            if fam is None:
                continue
            da = walk_from(a)
            if da.get(b, 99) < 3:
                continue            # (an earlier loop already brought them near)
            mark = plan.mark()
            # (it must still be a plan the kit can build: a loop is a nice thing to have, not worth losing the place over)
            if self.join(a, b, fam, cost=16) and fill(self.ts, plan, 1, budget=120, big=False):
                added += 1
                for link in plan.links - mark[2]:
                    x, y = tuple(link)
                    p, q = plan.cells.get(x), plan.cells.get(y)
                    if p is not None and q is not None and p != q:
                        near[p].add(q)
                        near[q].add(p)
                plan.owners[-1]['loop'] = True
            else:
                plan.back_to(mark)
        return added

    def _hall_between(self, a, b):
        """A corridor family that can leave one owner and arrive at the other."""
        ok = []
        for f in self.ts.families['halls']:
            for n in (a, b):
                o = self.plan.owners[n]
                if not (o['fam'] == f if o['kind'] == HALL else (o['fam'], f) in self.ts.hall_pairs):
                    break
            else:
                ok.append(f)
        return self.rng.choice(ok) if ok else None

    def _lay_pit(self, g, spec, c, route, way, fam, W, H):
        plan, rng = self.plan, self.rng
        step = self.ts.step
        l = route[-1][2]
        vm = H // 2
        ux, uy = DX[way]
        vx, vy = DX[(way + 1) % 4]
        ox, oy = route[-1][0] + ux - vm * vx, route[-1][1] + uy - vm * vy

        def at(u, v, lv=l):
            return (ox + u * ux + v * vx, oy + u * uy + v * vy, lv)
        depth = 2
        foot = [at(u, v) for u in range(W) for v in range(H)]
        back = [at(u, v, l + 1) for u in range(W) for v in range(-depth, 0)]
        if not self.clear(route + foot + [(x, y, l + 1) for x, y, _z in foot] + back) or set(route) & set(foot):
            return False
        plan.owners[plan.add_hall(fam, route, spec.main)]['wing'] = spec.wing
        hall = len(plan.owners) - 1
        plan.link(c, route[0])
        air = [at(u, v, l + 1) for u in range(W) for v in range(H)]
        n = plan.add_room(spec.purpose, g.back, foot + air)
        o = plan.owners[n]
        o.update(wing=spec.wing, tall=True, main=spec.main)
        plan.air |= set(air)
        rise = plan.rise
        pieces, tops = [], {}
        minus_u, plus_u, minus_v, plus_v = (way + 2) % 4, way, (way + 3) % 4, (way + 1) % 4

        def put(cell, piece, t):
            pieces.append(Placed(piece.key, t, cell[0] * step, cell[1] * step, l * rise - piece.box[2], n, cell))
        for u in range(W):
            for v in range(H):
                cell = at(u, v)
                # (which ways the room's inside lies from here)
                on_u = minus_u if u == W - 1 else plus_u if u == 0 else None
                on_v = minus_v if v == H - 1 else plus_v if v == 0 else None
                if on_u is not None and on_v is not None:
                    a, b = (on_u, on_v) if (on_u + 1) % 4 == on_v else (on_v, on_u)
                    got = g.corner(g.corner_open if v == 0 else g.corner_tall, rng, (a, b), minus_v if v == 0 else None)
                    if not got:
                        return False
                    put(cell, got[0], got[1])
                    if v == 0:
                        tops[u] = next(s for s in got[0].slots if s['side'] == got[2])
                elif on_v is not None or on_u is not None:
                    front = on_v if on_v is not None else on_u
                    if v == 0:
                        rows = [r for r in g.open_wall if r[0].key in g.rails]
                        p, f = pick_row(rows, rng)
                        t = (f - front) % 4
                        put(cell, p, t)
                        rail = g.rails[p.key]
                        pieces.append(Placed(rail.key, t, cell[0] * step, cell[1] * step, l * rise - p.box[2], n, cell))
                        tops[u] = next(s for s in p.slots if s['side'] == ((f + 2) % 4))
                    elif cell == at(0, vm):
                        p, f = pick_row(g.door_wall, rng)
                        t = (f - front) % 4
                        put(cell, p, t)
                        plan.ports.append((route[-1], way, next(s for s in p.slots if s['side'] == (f + 2) % 4)))
                        plan.link(route[-1], cell)
                    else:
                        p, f = pick_row(g.tall_wall, rng)
                        put(cell, p, (f - front) % 4)
                else:
                    put(cell, pick_row([(q,) for q in g.mid], rng)[0], 0)
        plan.placed.append({'owner': n, 'pieces': pieces})
        m = plan.add_room('over the hall', g.back, back)
        plan.owners[m].update(wing=spec.wing, part_of=n)
        for u in range(W):
            if u not in tops:
                return False
            plan.opens[(at(u, -1, l + 1), plus_v)] = tops[u]
        o['sides'] = [m]
        return self.join(hall, m, fam, cost=40) or self.join(m, hall, fam, cost=40)

    def join(self, a, b, fam, flights=True, cost=30, main=False):
        """A corridor between two owners, by any way the kit can go, stairs included. True if one was found and put in."""
        goals = {}
        for c, d in self.spots(b):
            if not self.door_near(c):
                goals[(c[0] + DX[d][0], c[1] + DX[d][1], c[2], (d + 2) % 4)] = c
        starts = [s for s in self.spots(a) if not self.door_near(s[0])]
        self.rng.shuffle(starts)
        way = self.find_way(starts, goals, fam, cost, flights)
        return bool(way) and self.lay_way(way, fam, main)

    def find_way(self, starts, goals, fam, limit=30, flights=True):
        """The cheapest corridor from any of starts (square, way out) to any of goals ((x, y, level, way going): the square it
        joins): (start square, moves, square it joins) or None. Moves: ('s', square) or ('f', low square, way up, level). It's
        straight next to a doorway and next to stairs, since only a straight piece joins those; a bend costs a little, stairs more."""
        bends = self.ts.hall_can(fam, '..PP')
        pq, prev, best, n = [], {}, {}, 0
        for c, d in starts:
            first = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
            st = (first[0], first[1], first[2], d, True)
            if self.clear([first]) and st not in best:
                best[st] = 1.0 + self.rng.random() * 0.3
                prev[st] = (None, c)
                heapq.heappush(pq, (best[st], n, st))
                n += 1
        seen = 0
        while pq and seen < 6000:
            cost, _n, st = heapq.heappop(pq)
            if cost > best.get(st, 1e9):
                continue
            seen += 1
            x, y, l, way, must = st
            if (x, y, l, way) in goals:
                return self._read_way(st, prev, goals[(x, y, l, way)])
            if cost > limit:
                return None
            f = (x + DX[way][0], y + DX[way][1])
            nexts = []
            if self.clear([(f[0], f[1], l)]):
                nexts.append(((f[0], f[1], l, way, False), cost + 1.0 + self.rng.random() * 0.2, None))
            if bends and not must:
                for w in ((way + 1) % 4, (way + 3) % 4):
                    t = (x + DX[w][0], y + DX[w][1], l)
                    if self.clear([t]):
                        nexts.append(((t[0], t[1], l, w, False), cost + 1.6, None))
            if flights and self.stair:
                s2 = (f[0] + DX[way][0], f[1] + DX[way][1])
                s3 = (s2[0] + DX[way][0], s2[1] + DX[way][1])
                if self.clear([(q[0], q[1], lv) for q in (f, s2) for lv in (l, l + 1)] + [(s3[0], s3[1], l + 1)]):
                    nexts.append(((s3[0], s3[1], l + 1, way, True), cost + 5.0, (f, way, l)))
                if self.clear([(q[0], q[1], lv) for q in (f, s2) for lv in (l - 1, l)] + [(s3[0], s3[1], l - 1)]):
                    nexts.append(((s3[0], s3[1], l - 1, way, True), cost + 5.0, (s2, (way + 2) % 4, l - 1)))
            for st2 in (self.ts.turns[:1] if flights else ()):
                nexts += self._turn_moves(st2, x, y, l, way, cost)
            for t, c2, how in nexts:
                if c2 < best.get(t, 1e9):
                    best[t] = c2
                    prev[t] = (st, how)
                    heapq.heappush(pq, (c2, n, t))
                    n += 1
        return None

    @staticmethod
    def _read_way(st, prev, target):
        moves = []
        while True:
            before, how = prev[st]
            moves.append(('s', (st[0], st[1], st[2])))
            if before is None:
                return how, moves[::-1], target
            if how:
                moves.append(how if how[0] == 'u' else ('f', how[0], how[1], how[2]))
            st = before

    def _turn_moves(self, st, x, y, l, way, cost):
        """The ways a stairwell made in one piece could go from here, up or down, for find_way."""
        out = []
        a = (x + DX[way][0], y + DX[way][1])
        ahead = DX[way]
        for up in (True, False):
            _t, across = st.turned(way, st.low if up else st.high)
            b = (a[0] + across[0], a[1] + across[1])
            lvl = l if up else l - 1
            end = (b[0] - ahead[0], b[1] - ahead[1], l + 1 if up else l - 1)
            cells = [(q[0], q[1], k) for q in (a, b, (a[0] + ahead[0], a[1] + ahead[1]), (b[0] + ahead[0], b[1] + ahead[1])) for k in (lvl, lvl + 1)]
            if self.clear(cells + [end]):
                out.append(((end[0], end[1], end[2], (way + 2) % 4, True), cost + 4.0, ('u', st, a, way, lvl, up)))
        return out

    @staticmethod
    def _way_cells(moves):
        out = []
        for m in moves:
            if m[0] == 's':
                out.append(m[1])
            elif m[0] == 'f':
                a, w, lv = m[1], m[2], m[3]
                b = (a[0] + DX[w][0], a[1] + DX[w][1])
                out += [(q[0], q[1], k) for q in (a, b) for k in (lv, lv + 1)]
            else:
                st, a, way, lvl, up = m[1], m[2], m[3], m[4], m[5]
                across = st.turned(way, st.low if up else st.high)[1]
                b = (a[0] + across[0], a[1] + across[1])
                ahead = DX[way]
                out += [(q[0], q[1], k) for q in (a, b, (a[0] + ahead[0], a[1] + ahead[1]), (b[0] + ahead[0], b[1] + ahead[1])) for k in (lvl, lvl + 1)]
        return out

    def lay_way(self, way, fam, main=False, wing=None):
        """Puts a route in the plan: runs of corridor with stairs between them. False if it would cross itself."""
        start, moves, target = way
        cells = self._way_cells(moves)
        if len(set(cells)) != len(cells):
            return False
        run, before = [], start
        for m in moves + [None]:
            if m and m[0] == 's':
                run.append(m[1])
                continue
            if run:
                n = self.plan.add_hall(fam, run, main)
                self.plan.owners[n]['wing'] = wing
                if before is not None:
                    self.plan.link(before, run[0])
                run = []
            if m and m[0] == 'f':
                self.plan.add_flight(self.stair, m[1], m[2], m[3], m[4] if len(m) > 4 else 'straight')
                before = None
            elif m:
                self.plan.add_turn(m[1], m[2], m[3], m[4], m[5])
                before = None
        self.plan.link(next(m[1] for m in reversed(moves) if m[0] == 's'), target)
        return True

    def _lengths(self, long_way, from_hall, has_halls):
        r = self.rng
        if not has_halls:
            return [0]
        if self.straight:
            return [r.randint(2, 3), 2, 0]
        if long_way:
            return [r.randint(4, 8), r.randint(2, 4), 2, 0]
        k = [r.randint(2, 5), 2, 0]
        if from_hall:
            k.insert(0, 0)              # (a door straight off the corridor)
        return k


def make_plan(ts, program, seed=0, bounds=None, plan=None, start=None, level=0, stairs=0.35, with_exit=False, opening=None, loops=None):
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
        # (the first impression: a small room, a short straight corridor, and the biggest thing there is, straight ahead,
        # all in a line from the door you came in by)
        pl.first_way = pl.plan.exit[1] if pl.plan.exit else None
    else:
        last = start
    owners_of = pl.plan.owners
    leading = plan is None
    for s in [s for s in program if s.main]:
        if opening:
            if not pl.attach(s, 0, True, opening):
                return pl.plan
            opening = None
            last = len(owners_of) - 1
            continue
        pl.straight = leading
        went = pl.attach(s, last, True)
        pl.straight = False
        leading = False
        if went:
            last = _main_room(pl.plan)
        else:
            owners = [o['n'] for o in owners_of if o['kind'] != VOID]
            rng.shuffle(owners)
            for n in owners:
                if pl.attach(s, n, True):
                    last = _main_room(pl.plan)
                    break
    for s in [s for s in program if not s.main]:
        # (off a corridor if there is one: rooms along a corridor are what makes it a corridor)
        owners = [o['n'] for o in owners_of if o['kind'] != VOID]
        rng.shuffle(owners)
        # (a wing keeps together, and each wing starts off somewhere on the main route)
        fresh = s.wing is not None and not any(owners_of[n].get('wing') == s.wing for n in owners)
        owners.sort(key=lambda n: (owners_of[n].get('wing') != s.wing if s.wing else False, not owners_of[n]['main'] if fresh else False, owners_of[n]['kind'] != HALL))
        long_way = fresh
        for n in owners:
            if pl.attach(s, n, long_way):
                break
    if loops is None:
        loops = 0 if plan is not None else 1 + len(pl.plan.rooms()) // 6
    pl.plan.loops = pl.add_loops(loops) if loops else 0
    return pl.plan


def _main_room(plan):
    """The last big room put in: what the main route goes on from (not the rooms round a tall room, nor a corridor)."""
    return next(o['n'] for o in reversed(plan.owners) if o['kind'] == ROOM and not o.get('part_of'))


# ---------- walking it: the honest check ----------

class Walk:
    """What walking a finished place finds, from the real collision shapes (the same reading navgen makes the navmesh from):
    where a person can get to from the start, on any level, over stairs and through doorways."""

    def __init__(self, game, refs, start, voxel=16.0, cache=None, erode=False):
        self.voxel = voxel
        field = navgen.Field(voxel, math.cos(math.radians(navgen.SLOPE_MAX)))
        report = {'collision': 0, 'drawn': 0, 'unread': 0, 'placed': 0}
        navgen._lay_refs(game, field, refs, {} if cache is None else cache, report)
        self.field = field
        self.graph = navgen.Graph(navgen._places(field, navgen.HEADROOM), voxel, navgen.STEP, navgen.HEADROOM)
        self.keep = [True] * len(self.graph.p)
        if erode:
            # (as the navmesh will be: an actor's middle can't go right up to a wall)
            self.keep = self.graph.erode(self.keep, navgen.RADIUS)
        self.pieces, self.label = self.graph.pieces(self.keep)
        self.reached = set(self.pieces[self._start_piece(start)]) if self.pieces else set()

    def _start_piece(self, start):
        """Which part the start is in: the biggest that's near it (the nearest may be the top of a table)."""
        v = self.voxel
        cx, cy = int(start[0] // v), int(start[1] // v)
        reach = int(192 // v)
        best = None
        for iy in range(cy - reach, cy + reach + 1):
            for ix in range(cx - reach, cx + reach + 1):
                for i in self.graph.by.get((iy, ix), ()):
                    if self.keep[i] and abs(self.graph.p[i][2] - start[2]) <= 64:
                        n = self.label[i]
                        if best is None or len(self.pieces[n]) > len(self.pieces[best]):
                            best = n
        if best is None:
            i = self.graph.nearest(start, 192.0, self.keep)
            best = self.label[i] if i is not None else 0
        return best

    def open_edges(self, reach=2):
        """Where walking from what's reached can step off into nothing: a place whose neighbour has no floor, no wall in the way
        and nothing of the place to land on. Walking only follows floors, so this is what finds a hole in a wall (under a
        balcony, say) that opens on the void. [(x, y, z)]"""
        g = self.graph
        here = set(self.reached)
        todo = list(here)
        for _ in range(reach):
            nxt = []
            for i in todo:
                for nb in g.nb:
                    j = nb[i]
                    if j >= 0 and j not in here:
                        here.add(j)
                        nxt.append(j)
            todo = nxt
        out = []
        cols = self.field.cols

        def wall(q, dx, dy, z):
            # (a thin wall can fall between one column's cuts, and a floor can stop short of the wall: nobody's narrow enough for this gap)
            return any(s[0] <= z + 110 and s[1] >= z + 12 for k in range(1, 7) for s in cols.get((q[0] + k * dy, q[1] + k * dx), ()))
        for i in here:
            q = g.p[i]
            z = q[2]
            for d, nb in enumerate(g.nb):
                if nb[i] >= 0:
                    continue
                dx, dy = DX[d]
                key = (q[0] + dy, q[1] + dx)
                if wall(q, dx, dy, z):
                    continue
                if any(g.p[p][2] < z for p in g.by.get(key, ())):
                    continue            # (a drop, to floor below)
                out.append(((q[1] + 0.5) * self.voxel, (q[0] + 0.5) * self.voxel, z, d))
        return out

    def where(self):
        """Every place reached: (x, y, z)."""
        v = self.voxel
        return [((q[1] + 0.5) * v, (q[0] + 0.5) * v, q[2]) for q in (self.graph.p[i] for i in self.reached)]


def as_refs(game, made):
    """Placed pieces in the form navgen reads."""
    return [{'ref': n, 'type': 'REFR', 'base': game.from_key(m.key), 'pos': (m.x, m.y, m.z),
             'rot': (0.0, 0.0, m.turn * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': m.key} for n, m in enumerate(made)]


def walk_check(game, ts, plan, made, cache=None, extra=(), start=None, offset=(0.0, 0.0, 0.0)):
    """Is every part of a plan reachable from its first room, and nothing outside it? {'missing': squares no one can get
    to, 'escaped': places reached outside every square, 'squares': how many there are}."""
    step, rise = ts.step, plan.rise
    squares = set(plan.cells)
    levels = {c[2] for c in squares}
    first = plan.owners[0]['cells']
    cx = sum(c[0] for c in first) / len(first)
    cy = sum(c[1] for c in first) / len(first)
    fc = min(first, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
    ox, oy, oz = offset
    floor = ts.floor
    at = (start.x, start.y, start.z + floor + 8) if start else (fc[0] * step, fc[1] * step, fc[2] * rise + floor + 8)
    w = Walk(game, as_refs(game, made) + list(extra), at, cache=cache, erode=True)
    covered = collections.Counter()
    escaped = []
    for x, y, z in w.where():
        x, y, z = x - ox, y - oy, z - oz
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
    edges = w.open_edges()
    if plan.exit:
        # (the way out has its door stood in it later on)
        c, d = plan.exit
        ex, ey = (c[0] + DX[d][0] * 0.5) * step + ox, (c[1] + DX[d][1] * 0.5) * step + oy
        edges = [e for e in edges if abs(e[0] - ex) > step * 0.6 or abs(e[1] - ey) > step * 0.6]
    return {'missing': missing, 'escaped': escaped, 'squares': len(plan.squares()), 'reached': len(w.reached), 'edges': edges}


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


def dress_place(game, ts, sv, plan, made, rng, cache, ruined=False):
    """Doors, lights and things, and whatever stands in the way out again: (items, the walk)."""
    import kitdress
    items = kitdress.place_doors(ts, sv, plan, made, rng) + kitdress.dress(ts, sv, plan, made, rng, ruined=ruined)
    return items, kitdress.clear_ways(game, ts, plan, made, items, walk_check, cache)


def generate(game, ts, area=150, seed=0, bounds=None, cache=None, tries=10, program=None, stairs=0.35, survey=None, ruined=False):
    """A whole place: plan, pieces and a clean walk, with doors, lights and things if there's a survey (kitdress.py).
    {'plan', 'made', 'items', 'walk', 'tries', 'wanted'} or None."""
    for k in range(tries):
        rng = random.Random(seed + k * 7919)
        prog = program or program_for(area, rng)
        plan = make_plan(ts, prog, seed + k * 104729, bounds, stairs=stairs, with_exit=survey is not None and k < tries - 2)
        made = None
        for f in range(3):
            made = fill(ts, plan, seed + k + f * 31)
            if made:
                break
        if not made:
            continue
        walk = walk_check(game, ts, plan, made, cache)
        if not walk['missing'] and not walk['escaped'] and not walk['edges']:
            items = []
            if survey is not None:
                import kitdress
                sv = survey.get(ts.kit.name)
                if sv is not None:
                    items, walk = dress_place(game, ts, sv, plan, made, rng, cache, ruined)
                    if walk['missing'] or walk['escaped']:
                        continue
            return {'plan': plan, 'made': made, 'items': items, 'walk': walk, 'tries': k + 1, 'wanted': len(prog)}
        for key, _n in _blame(ts, plan, made, walk).most_common(2):
            ts.ban(key)
    return None


def repeats(ts, made):
    """(pieces standing beside the same piece where their family has another with the same word pattern, sides looked at).
    Plain floor doesn't count: a room's floor being one floor is the point."""
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
                if o.key == m.key and len(alts[fam_word[m.key]]) > 1 and fam_word[m.key][1] != 'FFFF':
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
        return _keep(store, ts, g, origin, _report(ts, g['plan'], g['made'], origin, 'a', g['items']))
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
    levels = len({c[2] for c in plan.squares()})
    out = {'ops': ops, 'start': [origin[0] + c[0] * ts.step, origin[1] + c[1] * ts.step, origin[2] + c[2] * plan.rise + getattr(ts, 'floor', 0)],
           'rooms': sorted(rooms.items()), 'levels': levels, 'step': ts.step}
    if how == 'a':
        kinds = collections.Counter(it.what for it in items)
        tall = sum(1 for o in plan.rooms() if o.get('tall'))
        out['tall'] = tall
        out['said'] = '%d rooms%s, %d pieces%s, %d doors, %d lights, %d other things. Walked from the first room: every square reached, no way out.%s' % (
            len(plan.rooms()), ' (%d two storeys high, with balconies)' % tall if tall else '', len(made), ', %d levels' % levels if levels > 1 else '', kinds['door'] + kinds['exit'], kinds['light'],
            sum(kinds.values()) - kinds['door'] - kinds['exit'] - kinds['light'],
            ' The way out is a door in the first room: select it to link it to another place.' if kinds['exit'] else '')
        out['exit'] = next(([round(c, 2) for c in it.p[:3]] for it in items if it.what == 'exit'), None)
        out['plan'] = plan_summary(plan)
    else:
        out['said'] = '%d pieces, no rooms planned: this kit has no pieces that close a room. Walking found no way out.' % len(made)
    return out


def plan_summary(plan):
    """The plan as the Kit tab shows it: rooms, what each is for, which real place it takes after, and where."""
    rooms = []
    for o in plan.rooms():
        cells = [c for c in o['cells'] if c not in plan.air]
        rooms.append({'n': o['n'], 'purpose': o['purpose'], 'theme': o.get('theme'), 'tall': bool(o.get('tall')), 'whole': bool(o.get('whole')), 'fixed': bool(o.get('tall') or o.get('whole')),
                      'levels': sorted({c[2] for c in cells}), 'squares': len(cells), 'main': bool(o.get('main')), 'cells': [list(c) for c in cells[:200]]})
    return {'rooms': rooms, 'flights': [{'kind': f.get('kind', 'straight'), 'level': f['level'], 'cells': [list(c) for c in f['cells']]} for f in plan.flights],
            'halls': [[list(c) for c in o['cells']] for o in plan.owners if o['kind'] == HALL],
            'loops': getattr(plan, 'loops', 0)}


def _keep(store, ts, g, origin, out):
    """The last place made, so one room of it can be changed after."""
    store['last'] = {'name': ts.kit.name, 'plan': g['plan'], 'made': g['made'], 'items': g['items'], 'origin': origin, 'ruined': bool(g.get('ruined'))}
    return out


def _variant_of(ts, m):
    """The variant a one-square placed piece is, or None."""
    sides = tuple(K_side(ts, m.key, m.turn, d) for d in range(4)) if m.key in ts.slot_sock else None
    if sides is None:
        return None
    sides = tuple(0 if ts.sockets[s] and ts.sockets[s]['open'] and ts.word[s] == '.' else s for s in sides)
    for v in range(1, len(ts.vars)):
        if ts.piece_of[v] == m.key and ts.sides[v] == sides:
            return v
    return None


def reroll_room(ts, plan, made, n, seed):
    """New pieces for one room, everything round it kept as it is: the new [Placed] for the whole place, or None if nothing
    else fits. (Doors in its walls stay where the plan has them.)"""
    rng = random.Random(seed)
    palette = _palette(ts, plan, rng)
    by = {}
    for m in made:
        for c in m.cells:
            by[c] = m
    mine = [c for c in plan.owners[n]['cells'] if c not in plan.air]
    boundary = collections.defaultdict(lambda: -1)
    near = set()
    for c in mine:
        for d in range(4):
            q = (c[0] + DX[d][0], c[1] + DX[d][1], c[2])
            if q in by and plan.cells.get(q) != n:
                near.add(q)
    for q in near:
        m = by[q]
        v = _variant_of(ts, m) if len(m.cells) == 1 else None
        if v is None:
            continue
        boundary[q] &= 1 << v
    for f in plan.flights:
        for outside, way, slot, _inner in f['ports']:
            if plan.cells.get(outside) == n:
                boundary[outside] &= ts.port_mask(slot, way)
    for (c, d), slot in plan.opens.items():
        if plan.cells.get(c) == n:
            boundary[c] &= ts.port_mask(slot, d)
    for c, mask in plan.forced.items():
        if plan.cells.get(c) == n:
            boundary[c] &= mask
    if plan.exit and plan.exit[0] in mine and ts.exit_widths:
        boundary[plan.exit[0]] &= ts.width_mask(plan.exit[1], ts.exit_widths)
    cells = mine + [q for q in near if boundary[q] != -1]
    # (a piece bigger than a square that's only partly this room's would be left with a hole: that's not a room to re-roll)
    if any(len(by[c].cells) > 1 and any(plan.cells.get(q) != n for q in by[c].cells) for c in mine if c in by):
        return None
    levels = collections.defaultdict(list)
    for c in cells:
        levels[c[2]].append(c)
    got = {}
    for _lv, row in levels.items():
        s = _solve(ts, plan, row, palette, rng, SOLVE_BUDGET, boundary)
        if s is None:
            return None
        got.update(s)
    out = [m for m in made if m.owner != n or m in [b for pl in plan.placed for b in pl['pieces']]]
    for c in mine:
        key, t = ts.vars[got[c]]
        out.append(Placed(key, t, c[0] * ts.step, c[1] * ts.step, c[2] * plan.rise, n, c))
    return out


def change_room(game, kits, store, cache, survey, n, purpose=None, theme=None, reroll=False, seed=0):
    """One room of the last place made: what it's for, which real place it takes after, or new pieces and things altogether;
    the rest stays. The whole place again as changes for the mod, or {'note'}."""
    import kitdress
    last = store.get('last')
    if not last:
        return {'note': 'This needs a place generated since FOLab started: generate one first.'}
    ts = tiles_for(game, kits, last['name'], store, survey)
    sv = (survey or {}).get(last['name'])
    plan, made = last['plan'], last['made']
    if not 0 <= n < len(plan.owners) or plan.owners[n]['kind'] != ROOM:
        return {'note': 'No such room.'}
    o = plan.owners[n]
    was = (o['purpose'], o.get('pick'))
    if purpose:
        o['purpose'] = purpose
        o.pop('pick', None)
    if theme:
        o['pick'] = theme
    rng = random.Random(seed)
    new_made = made
    if reroll and not (o.get('tall') or o.get('whole')):
        got = reroll_room(ts, plan, made, n, seed)
        if got is None:
            o['purpose'], o['pick'] = was
            return {'note': 'Nothing else fits in that room as it stands: its doors and neighbours leave no choice.'}
        new_made = got
    if new_made is not made:
        # (the pieces alone: the tops of tables have edges too)
        bare = walk_check(game, ts, plan, new_made, cache)
        if bare['missing'] or bare['escaped'] or bare['edges']:
            o['purpose'], o['pick'] = was
            return {'note': 'That one didn\'t walk, so the room is as it was. Try again.'}
    items = [it for it in last['items'] if it.owner != n or it.what in ('door', 'exit')]
    if sv is not None:
        placed = [m for m in new_made if m.owner == n]
        items += kitdress.dress(ts, sv, plan, placed, rng, ruined=last['ruined'], only=n)
    walk = kitdress.clear_ways(game, ts, plan, new_made, items, walk_check, cache)
    if walk['missing'] or walk['escaped']:
        o['purpose'], o['pick'] = was
        return {'note': 'That one didn\'t walk, so the room is as it was. Try again.'}
    last['made'], last['items'] = new_made, items
    out = _report(ts, plan, new_made, last['origin'], 'a', items)
    out['said'] = 'Changed one room, the rest kept. ' + out['said']
    return out


def room_themes(game, kits, store, survey, n, purpose=None, limit=10):
    """The real places a room of the last place could take after, best first: {'rows': [{'cell', 'name', 'score'}], 'purposes'}."""
    import kitdress
    last = store.get('last')
    if not last:
        return {'rows': [], 'purposes': sorted(kitdress.PURPOSE_TAGS)}
    plan, made = last['plan'], last['made']
    sv = (survey or {}).get(last['name'])
    o = plan.owners[n] if 0 <= n < len(plan.owners) else None
    if sv is None or not o:
        return {'rows': [], 'purposes': sorted(kitdress.PURPOSE_TAGS)}
    every = {t for ws in kitdress.PURPOSE_TAGS.values() for t in ws}
    wanted = set(kitdress.PURPOSE_TAGS.get(purpose or o['purpose'], ()))
    rows = kitdress.theme_scores(sv, [m for m in made if m.owner == n], wanted, every - wanted)[:limit]
    out = []
    for score, cell in rows:
        try:
            name = game.edid(game.from_key(cell) if isinstance(cell, str) else cell)
        except (KeyError, ValueError):
            name = str(cell)
        out.append({'cell': cell, 'name': name, 'score': round(score, 2)})
    return {'rows': out, 'purposes': sorted(p for p in kitdress.PURPOSE_TAGS if p != 'corridor'), 'purpose': o['purpose'], 'theme': o.get('theme')}


# ---------- a floor plan drawn by hand ----------

def plan_from_drawing(ts, rooms, links, seed=0):
    """A plan from a rough drawing: rooms [{'x', 'y', 'w', 'h', 'level', 'purpose'}], links [[a, b], ...] between them by number.
    Touching rooms that are linked get a door between them, the rest a corridor, by stairs if their levels differ.
    (plan, []) or (None, [what couldn't be done, in words])."""
    rng = random.Random(seed)
    pl = Planner(ts, rng)
    plan = pl.plan
    fams = ts.families['rooms']
    fam = max(fams, key=lambda f: fams[f]) if fams else None
    if fam is None:
        return None, ['This kit can\'t close a room.']
    if ts.stairs:
        plan.rise = ts.stairs[0].rise
    ids = []
    for k, r in enumerate(rooms):
        w, h = int(r['w']), int(r['h'])
        l = int(r.get('level', 0))
        if w < 2 or h < 2:
            return None, ['Room %d is too narrow: rooms are at least 2 squares across.' % (k + 1)]
        cells = [(int(r['x']) + i, int(r['y']) + j, l) for i in range(w) for j in range(h)]
        if not plan.free(cells):
            return None, ['Room %d overlaps another.' % (k + 1)]
        ids.append(plan.add_room(r.get('purpose') or ('entrance' if k == 0 else 'workroom'), fam, cells, k == 0))
    problems = []
    for a, b in links:
        if not (0 <= a < len(ids) and 0 <= b < len(ids)) or a == b:
            continue
        if _door_between(pl, ids[a], ids[b], fam):
            continue
        hall = pl._hall_between(ids[a], ids[b])
        if hall is None or not pl.join(ids[a], ids[b], hall, cost=60):
            problems.append('No way could be found from room %d to room %d: try moving them apart or further along.' % (a + 1, b + 1))
    reach = {ids[0]}
    near = collections.defaultdict(set)
    for link in plan.links:
        x, y = tuple(link)
        p, q = plan.cells.get(x), plan.cells.get(y)
        if p is not None and q is not None and p != q:
            near[p].add(q)
            near[q].add(p)
    todo = [ids[0]]
    while todo:
        for m in near[todo.pop()]:
            if m not in reach:
                reach.add(m)
                todo.append(m)
    for k, n in enumerate(ids):
        if n not in reach:
            problems.append('Nothing joins room %d to the first room.' % (k + 1))
    if problems:
        return None, problems
    spots = [s for s in pl.spots(ids[0]) if pl.clear([(s[0][0] + DX[s[1]][0], s[0][1] + DX[s[1]][1], s[0][2])]) and not pl.door_near(s[0])]
    if spots:
        rng.shuffle(spots)
        plan.add_exit(*spots[0])
    return plan, []


def _door_between(pl, a, b, fam):
    """A door straight through the wall between two rooms that touch, if they do. True if one went in."""
    plan = pl.plan
    if (fam, fam) not in pl.ts.door_pairs:
        return False
    sa, sb = _door_spots({c[:2] for c in plan.owners[a]['cells']}), _door_spots({c[:2] for c in plan.owners[b]['cells']})
    level = plan.owners[a]['cells'][0][2]
    if plan.owners[b]['cells'][0][2] != level:
        return False
    there = {(i, j): d for i, j, d in sb}
    rows = []
    for i, j, d in sa:
        n = (i + DX[d][0], j + DX[d][1])
        if there.get(n) == (d + 2) % 4:
            rows.append(((i, j, level), (n[0], n[1], level)))
    if not rows:
        return False
    x, y = rows[len(rows) // 2]
    plan.link(x, y)
    return True


def drawn(game, kits, name, rooms, links, seed, at, store, cache, survey=None):
    """A place from a floor plan drawn by hand: {'ops', ...} like layout, or {'note'}."""
    ts = tiles_for(game, kits, name, store, survey)
    if not ts.can['rooms']:
        return {'note': 'This kit has no pieces that close a room, so it can\'t build a drawn plan.'}
    if not rooms:
        return {'note': 'Draw at least one room.'}
    origin = (float(at[0]), float(at[1]), float(at[2]))
    last = 'nothing fitted'
    for k in range(12):
        plan, problems = plan_from_drawing(ts, rooms, links, seed + k)
        if not plan:
            return {'note': ' '.join(problems)}
        made = fill(ts, plan, seed + k)
        if not made:
            last = 'the kit has no pieces for that shape of room or door'
            continue
        walk = walk_check(game, ts, plan, made, cache)
        if walk['missing'] or walk['escaped'] or walk['edges']:
            last = 'it didn\'t walk'
            continue
        rng = random.Random(seed + k)
        items = []
        sv = (survey or {}).get(name)
        if sv is not None:
            items, walk = dress_place(game, ts, sv, plan, made, rng, cache)
            if walk['missing'] or walk['escaped']:
                last = 'it didn\'t walk with things in it'
                continue
        return _keep(store, ts, {'plan': plan, 'made': made, 'items': items}, origin, _report(ts, plan, made, origin, 'a', items))
    return {'note': 'That plan couldn\'t be built: %s. Try larger rooms or fewer doors.' % last}


# ---------- other places in one click ----------

def works_program(size, rng):
    """Service tunnels: a way in, plant rooms along narrow corridors, a big pump hall at the far end."""
    size = max(1, min(10, int(size)))
    out = [Spec('entrance', (3, 4), (3, 4), True), Spec('workroom', (5, 7), (4, 6), True)]
    for k in range(1 + size):
        out.append(Spec('store' if k % 3 == 0 else 'workroom', (3, 5), (3, 5), wing='plant' if k % 2 else 'stores'))
    if size >= 4:
        out.append(Spec('quarters', (3, 4), (3, 4), wing='stores'))
    out.append(Spec('reactor', (6, 9), (5, 7), True, tall=True))
    return out


def block_program(size, rng):
    """An office block: a lobby, a big hall, offices off corridors on more than one floor, stores and a mess."""
    size = max(1, min(10, int(size)))
    out = [Spec('entrance', (4, 5), (4, 4), True), Spec('hall', (6, 8), (5, 7), True, tall=True)]
    for k in range(2 + size):
        out.append(Spec('office', (3, 5), (3, 4), wing='offices' if k % 3 else 'more offices', stairs=k % 3 == 0))
    out.append(Spec('mess', (4, 6), (4, 5), wing='services'))
    for _ in range(size // 3):
        out.append(Spec('store', (3, 4), (3, 4), wing='services'))
    out.append(Spec('far end', (5, 7), (4, 6), True))
    return out


ONE_CLICK = {
    'tunnels': {'label': 'Service tunnels', 'kit': 'dungeons' + chr(92) + 'utility', 'program': works_program, 'stairs': 0.25, 'said': 'Service tunnels: '},
    'office': {'label': 'Office block', 'kit': 'dungeons' + chr(92) + 'office', 'program': block_program, 'stairs': 0.3, 'said': 'An office block: '},
    'facility': {'label': 'Research facility', 'kit': 'dungeons' + chr(92) + 'facility', 'program': block_program, 'stairs': 0.3, 'said': 'A research facility: '},
}


def one_click_list(kits):
    return [{'id': k, 'label': v['label']} for k, v in ONE_CLICK.items() if v['kit'] in kits]


def one_click_place(game, kits, what, size, seed, store, cache, survey=None):
    """The best of a few of this kind of place: as generate gives it, or None."""
    d = ONE_CLICK[what]
    ts = tiles_for(game, kits, d['kit'], store, survey)
    if not ts.can['rooms']:
        return None
    best = None
    for k in range(6):
        prog = d['program'](size, random.Random(seed + k * 271))
        g = generate(game, ts, seed=seed + k, cache=cache, program=prog, stairs=d['stairs'], survey=survey, tries=4)
        if g and (not best or len(g['plan'].rooms()) > len(best['plan'].rooms())):
            best = g
            if len(g['plan'].rooms()) >= len(prog) - 1:
                break
    return best


def one_click(game, kits, what, size, seed, at, store, cache, survey=None):
    """A kind of place in one click, as changes for the mod: {'ops', ...} or {'note'}."""
    if what not in ONE_CLICK or ONE_CLICK[what]['kit'] not in kits:
        return {'note': 'This game doesn\'t have that kit.'}
    d = ONE_CLICK[what]
    best = one_click_place(game, kits, what, size, seed, store, cache, survey)
    if not best:
        return {'note': 'None passed the walk this time: try again.'}
    ts = tiles_for(game, kits, d['kit'], store, survey)
    origin = (float(at[0]), float(at[1]), float(at[2]))
    out = _report(ts, best['plan'], best['made'], origin, 'a', best['items'])
    out['said'] = d['said'] + out['said']
    return _keep(store, ts, best, origin, out)


# ---------- a vault in one click ----------

def vault_program(size, rng):
    """A vault's rooms for a dial of 1 to 10: entrance, atrium, reactor on the main route; living quarters along a corridor
    of their own, an overseer's office up a flight of stairs, and more of everything as the dial turns."""
    size = max(1, min(10, int(size)))
    out = [Spec('entrance', (4, 5), (4, 4), True, fam='roomu'),
           Spec('atrium', (7 + size // 3, 9 + size // 3), (6 + size // 3, 8 + size // 3), True, fam='roomu', shape='box', tall=((6 + size // 3, 8 + size // 3), (2, 3 + size // 3)))]
    for _ in range(2 + size):
        out.append(Spec('quarters', (3, 4), (3, 4), wing='living', fam='room'))
    if size >= 3:
        out.append(Spec('mess', (5, 7), (4, 6), wing='living', fam='room'))
    out.append(Spec('office', (4, 5), (3, 4), wing='overseer', fam='room', stairs=True, whole='overseer'))
    if size >= 2:
        out.append(Spec('clinic', (3, 5), (3, 4), wing='services', fam='room'))
    for _ in range(size // 2):
        out.append(Spec('store', (3, 4), (3, 5), wing='services', fam='room'))
    for _ in range(max(0, size - 5)):
        out.append(Spec('workroom', (4, 6), (4, 5), wing='works'))
    out.append(Spec('reactor', (6, 8), (6, 7), True, fam='roomu'))
    return out


def vault(game, kits, size, seed, at, store, cache, survey=None, ruined=False):
    """The one-click vault, as changes for the mod: {'ops', 'start', 'rooms', 'said'} or {'note'}. Ruined: the ruined kit,
    with rubble."""
    name = 'dungeons' + chr(92) + ('vaultruined' if ruined else 'vault')
    origin = (float(at[0]), float(at[1]), float(at[2]))
    if name not in kits:
        return {'note': 'This game has no vault kit.'}
    ts = tiles_for(game, kits, name, store, survey)
    if not ts.can['rooms']:
        return {'note': 'The vault kit can\'t build rooms here.'}
    best = vault_place(game, kits, size, seed, store, cache, survey, ruined)
    if not best:
        return {'note': 'No vault passed the walk this time: try again.'}
    out = _report(ts, best['plan'], best['made'], origin, 'a', best['items'])
    out['said'] = ('A ruined vault: ' if ruined else 'A vault: ') + out['said']
    best['ruined'] = ruined
    return _keep(store, ts, best, origin, out)


def vault_place(game, kits, size, seed, store, cache, survey=None, ruined=False):
    """The best of a few vaults for this seed: as generate gives it, or None."""
    name = 'dungeons' + chr(92) + ('vaultruined' if ruined else 'vault')
    ts = tiles_for(game, kits, name, store, survey)
    want = {'entrance', 'atrium', 'reactor', 'quarters', 'office'}
    best = None
    for k in range(6):
        rng = random.Random(seed + k * 271)
        prog = vault_program(size, rng)
        g = generate(game, ts, seed=seed + k, cache=cache, program=prog, stairs=0.12, survey=survey, ruined=ruined, tries=4)
        if not g:
            continue
        have = {o['purpose'] for o in g['plan'].rooms()}
        if want <= have and (not best or len(g['plan'].rooms()) > len(best['plan'].rooms())):
            best = g
            if len(g['plan'].rooms()) >= len(prog) - 1:
                break
    return best


# ---------- growing a place further ----------

def read_place(ts, pieces):
    """A place's pieces, as (key, x, y, z, turn), on this kit's grid: (plan with all of it as squares nobody may build on, what
    stands on each square, the grid's corner). Pieces off the grid only block the squares they're over."""
    step = ts.step
    on = [p for p in pieces if p[0] in ts.slot_sock]
    if not on:
        return None
    ox = on[0][1] % step
    oy = on[0][2] % step
    z0 = min(p[3] for p in on)
    plan = Plan(step)
    if ts.stairs:
        plan.rise = ts.stairs[0].rise
    cells = {}
    stand = {}
    for key, x, y, z, t in pieces:
        piece = ts.kit.pieces.get(key)
        if not piece or not piece.foot:
            continue
        box = K._footprint_world(piece, x - ox, y - oy, t)
        level = int(round((z - z0) / plan.rise))
        i0, i1 = int(math.floor(box[0] / step + 0.5 + 0.01)), int(math.ceil(box[2] / step + 0.5 - 0.01))
        j0, j1 = int(math.floor(box[1] / step + 0.5 + 0.01)), int(math.ceil(box[3] / step + 0.5 - 0.01))
        # (what stands up over the next level keeps that clear too)
        up = max(level, level + int((piece.box[5] - 16) // plan.rise))
        for i in range(i0, i1):
            for j in range(j0, j1):
                for l in range(level, up + 1):
                    cells[(i, j, l)] = True
        if key in ts.slot_sock and (x - ox) % step == 0 and (y - oy) % step == 0 and len(piece.slots) == 4:
            stand[(int((x - ox) // step), int((y - oy) // step), level)] = (key, t, (x, y, z))
    plan.add_void(sorted(cells), 'built')
    return plan, stand, (ox, oy, z0)


def _sides_of(ts, key, t):
    by = ts.slot_sock[key]
    return tuple(0 if ts.sockets[by[(d + t) % 4]] and ts.sockets[by[(d + t) % 4]]['open'] and ts.word[by[(d + t) % 4]] == '.' else by[(d + t) % 4] for d in range(4))


def way_in(ts, plan, stand, rng, room=3):
    """Where a place can be opened up: a square with a closed side and free ground beyond it, and a piece that's the same
    in every way but with a doorway on that side. [(square, way out, new variant)]"""
    out = []
    for c, (key, t, _pos) in stand.items():
        sides = _sides_of(ts, key, t)
        for d in range(4):
            if sides[d] or ts.word[sides[d]] != '.':
                continue
            beyond = [(c[0] + DX[d][0] * k, c[1] + DX[d][1] * k, c[2]) for k in range(1, room + 1)]
            if any(b in plan.cells for b in beyond):
                continue
            for v in range(1, len(ts.vars)):
                if ts.piece_of[v] in ts.banned or not ts.level_floor[v] or ts.word[ts.sides[v][d]] != 'P':
                    continue
                if all(i == d or ts.sides[v][i] == sides[i] for i in range(4)):
                    out.append((c, d, v))
                    break
    rng.shuffle(out)
    # (rooms first: a new wing off a room looks meant; off a corridor it can look like an afterthought)
    out.sort(key=lambda s: 'P' in ts.vwords[s[2]].replace('P', '', 1))
    return out


def grow(game, kits, name, pieces, area, seed, store, cache, survey=None):
    """More of an existing place: everything built stays but for one wall piece that gets a doorway. A new corridor and
    rooms beyond it, walked together with the old from the doorway. {'ops', 'said', 'start'} or {'note'}.
    pieces: [(key, x, y, z, turn, ref's key)] as they stand in the place."""
    ts = tiles_for(game, kits, name, store, survey)
    if not ts.can['rooms']:
        return {'note': 'This kit can\'t plan rooms, so it can\'t grow yet.'}
    read = read_place(ts, [p[:5] for p in pieces])
    if not read:
        return {'note': 'Nothing here is from this kit.'}
    by_pos = {(round(p[1]), round(p[2]), round(p[3])): p for p in pieces}
    for k in range(10):
        rng = random.Random(seed + k * 613)
        plan, stand, (ox, oy, z0) = read_place(ts, [p[:5] for p in pieces])
        spots = way_in(ts, plan, stand, rng)
        if not spots:
            return {'note': 'No wall of this place has a piece with a doorway to swap in and open ground beyond it.'}
        c, d, v = spots[k % min(len(spots), 8)]
        key, t = ts.vars[v]
        slot = next(s for s in ts.kit.pieces[key].slots if s['side'] == (d + t) % 4)
        fam = ts.family[v]
        prog = program_for(max(30, area), rng)[1:]
        if ts.vwords[v].count('P') > 1:
            fam = None
        grown = make_plan(ts, prog, seed + k, plan=plan, start=0, stairs=0.2, opening=(c, d, fam, slot))
        made = None
        for f in range(3):
            made = fill(ts, grown, seed + k + f * 17)
            if made:
                break
        if not made:
            continue
        kept = [p for p in pieces if (round(p[1]), round(p[2]), round(p[3])) != (round(stand[c][2][0]), round(stand[c][2][1]), round(stand[c][2][2]))]
        swapped = Placed(key, t, c[0] * ts.step + ox, c[1] * ts.step + oy, stand[c][2][2], 0, c)
        moved = []
        for m in made:
            m.x += ox
            m.y += oy
            m.z += z0
            moved.append(m)
        extra = [{'ref': 'old%d' % n, 'type': 'REFR', 'base': game.from_key(p[0]), 'pos': tuple(p[1:4]), 'rot': (0.0, 0.0, p[4] * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': p[0]} for n, p in enumerate(kept)]
        items = []
        sv = (survey or {}).get(name)
        walk = walk_check(game, ts, grown, moved + [swapped], cache, extra, start=swapped, offset=(ox, oy, z0))
        if walk['missing'] or walk['escaped']:
            for b, _n in _blame(ts, grown, moved, walk).most_common(1):
                ts.ban(b)
            continue
        if sv is not None:
            import kitdress
            items = kitdress.place_doors(ts, sv, grown, moved, rng) + kitdress.dress(ts, sv, grown, moved, rng)
            door = kitdress.door_table(ts.kit, sv)
            got = kitdress._door_in(ts, sv, door, swapped, d, rng)
            if got:
                items.append(kitdress.Item(got[0], got[1], 1.0, 'door', 0))
            walk = kitdress.clear_ways(game, ts, grown, moved + [swapped], items, lambda g, s, pl, ma, ca, ex: walk_check(g, s, pl, ma, ca, list(ex) + extra, start=swapped, offset=(ox, oy, z0)), cache)
            if walk['missing'] or walk['escaped']:
                continue
        old = by_pos[(round(stand[c][2][0]), round(stand[c][2][1]), round(stand[c][2][2]))]
        ops = [{'op': 'remove', 'ref': old[5]}] + as_ops(ts, [swapped] + moved) + (kitdress_ops(items))
        return {'ops': ops, 'start': [swapped.x, swapped.y, swapped.z + ts.floor],
                'said': 'Grown by %d rooms and %d pieces, the rest kept but for one wall piece, now a doorway. Walked from the doorway: every new square reached, no way out.' % (len(grown.rooms()), len(moved))}
    return {'note': 'Nothing that fits passed the walk this time: try again.'}


def kitdress_ops(items):
    import kitdress
    return kitdress.item_ops(items)
