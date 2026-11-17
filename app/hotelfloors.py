"""A hotel's floors inside: places of the mod's own, one above another, that you climb through from the lobby to the top,
each harder than the last. A great resort hotel two hundred years on: the function rooms by the lobby gone to the rats,
the kitchens and the laundry below full of ghouls, and the guest floors above held by a gang, its boss at the top with the
key to the penthouse.

    function floor   the way in from the lobby: the ballroom (the biggest room), conference rooms, the bar,
                     the cloakroom, the manager's office. Rats and roaches.
    service floor    down the service stairs from the function floor: the kitchens, cold store and dry stores, the
                     laundry, the boiler room, the staff's rooms. Feral ghouls.
    guest floors     up the service lift: corridors of guest rooms and suites, the linen rooms, a lounge. The gang.
    top floor        the last guest floor: the boss's suite, the gang at its thickest, and the lift to the penthouse
                     (another place: viewworld.py's), locked on a key that lies somewhere on this floor.

Each floor is planned and built by kitplan from one of the game's interior kits (`HOTELS`: a kit that suits the hotel for
its guest and function floors, the casino's back of house for the service floor), furnished by kitdress after the game's
own rooms of that kit, and then given what became of it: scenes and finds by what each room was for and who holds the
floor now (`STORIES`, `FINDS`: the hotel's own desks, wardrobes and suitcases, their loot better the higher you go), locks
harder higher up. The floors are joined by the game's own doors: the way in is the kit's door in the first room's outer
wall; the way on is a hotel lift door (`LIFT`, as the game stands them, flat on a wall, the room at its -y, its back
on the wall's face as measured from the pieces' meshes) in a room the floor would have it in (`LIFT_IN`: the top
floor's in the boss's suite), as far from the way in as there is. Nobody stands within `KEEP_CLEAR` of a door you arrive by.

    make(gd, pr, hotel, seed)          {'ops', 'places', 'entry', 'top', 'report', 'people'}: the ops for project.apply; names
                                       '$' + each place's name and each door's are resolved within them (project.apply).
                                       entry: the function floor's way in (link the lobby to it); top: the lift to the
                                       penthouse (link it to the penthouse); both left leading nowhere.
    navmesh_ops(gd, pr, made, names)   after make's ops are applied: each place's navmesh
    people_ops(gd, pr, made, names)    after those: who holds each floor, by populate from the game's places like it."""
import collections
import math
import random

import kitdress as D
import kitlife as L
import kitplan
import recordio
from kitplan import Spec

BS = chr(92)
HIGH = 'dungeons' + BS + 'hotelhighend'         # (the game's high-end hotel: Gomorrah's floors, the Tops' presidential suite)
MADRE = 'nvdlc01' + BS + 'dungeons' + BS + 'casino'     # (the Sierra Madre's suites and halls: Dead Money's)
L38 = 'dungeons' + BS + 'nvlucky38'             # (the Lucky 38's suites and halls)
BACK = 'dungeons' + BS + 'nv_casinolo'          # (the Ultra-Luxe's and the Atomic Wrangler's back of house)
LIFT = 'HotelElevatorDoor02'
LIFT_DEEP = 12.0            # (its mesh runs y 2 to 11 in front of its origin: the wall's face is that far behind it)
LIFT_UP = 80.0              # (its origin over the floor)
KEEP_CLEAR = 700.0
TRIES = 10
TIERS = {'function': 2, 'service': 4, 'guest': 6, 'top': 9}     # (the game's Gen01..Gen10 loot lists: better higher up)
LOCK_FROM = {'function': 0, 'service': 1, 'guest': 1, 'top': 2}    # (kitlife.LOCKS steps: harder higher up)
LOCKED_SHARE = 0.25
FIND_SHARE = 0.75
FIND_LOCKED = 0.35
MASTER_KEY_FROM = 'VMS21HotelKey'
# (rooms each floor's lift may be in, best first: you'd find the lifts off a lounge or a store, not in a bathroom)
LIFT_IN = {'function': ('store', 'rec room', 'office'), 'service': ('store', 'workroom', 'reactor'), 'guest': ('rec room', 'store'), 'top': ('office', 'rec room')}
HARMLESS = ('PlayerBedSCRIPT', 'CraftingWorkbenchRecipesScript')     # (scripts a thing may keep)

# what each hotel is built from: its guest and function floors' kit, the game's place its floors copy their light and sound
# from, the floors from the lobby up, and who holds the guest floors
HOTELS = {
    'royal_hawaiian': {'label': 'The Royal Hawaiian', 'tag': 'RoyalHawaiian', 'kit': HIGH, 'like': 'Gomorrah02',
                       'floors': ('function', 'service', 'guest', 'top'),
                       'gang': {'like': ['Vault3a', 'Vault3c', '1ENeonSignFactory'], 'said': 'Fiends'}},
    'moana': {'label': 'The Moana', 'tag': 'Moana', 'kit': MADRE, 'like': 'Lucky38SuiteFloor22',     # (not the Sierra Madre's red air)
              'floors': ('function', 'service', 'guest', 'top'),
              'gang': {'like': ['Vault19a'], 'said': 'Powder Gangers'}},
    'kilauea': {'label': 'The Kilauea', 'tag': 'Kilauea', 'kit': L38, 'like': 'Lucky38SuiteFloor22',
                'floors': ('function', 'service', 'guest', 'guest', 'top'),
                'gang': {'like': ['Vault74a', 'Vault3b'], 'said': 'raiders'}},
}
SERVICE_LIKE = 'ULGourmand'


def _function(rng):
    return [Spec('entrance', (4, 5), (4, 4), True), Spec('hall', (7, 9), (6, 8), True, tall=True),
            Spec('classroom', (4, 5), (4, 5), wing='conference'), Spec('classroom', (4, 5), (3, 4), wing='conference'),
            Spec('washroom', (3, 3), (3, 3), wing='conference'), Spec('rec room', (5, 6), (4, 5), wing='bar'),
            Spec('store', (3, 3), (3, 4), wing='bar'), Spec('office', (3, 4), (3, 4), wing='offices', stairs=True),
            Spec('office', (3, 4), (3, 3), wing='offices')]


def _service(rng):
    return [Spec('entrance', (3, 4), (4, 4), True), Spec('mess', (6, 7), (5, 6), True), Spec('store', (3, 4), (3, 4), wing='stores'),
            Spec('store', (3, 4), (3, 3), wing='stores'), Spec('workroom', (4, 6), (4, 5), wing='laundry'),
            Spec('reactor', (4, 5), (4, 5), wing='plant', stairs=True), Spec('quarters', (3, 3), (3, 4), wing='staff'),
            Spec('quarters', (3, 3), (3, 4), wing='staff'), Spec('washroom', (3, 3), (3, 3), wing='staff'),
            Spec('office', (3, 4), (3, 3), wing='stores')]


def _guest(rng, more=0):
    out = [Spec('entrance', (4, 4), (3, 4), True), Spec('rec room', (4, 6), (4, 5), True)]
    for k in range(6 + more):
        out.append(Spec('quarters', (3, 4), (3, 4), wing='east wing' if k % 2 else 'west wing', stairs=k == 3))
    out += [Spec('quarters', (4, 5), (4, 5), wing='suites'), Spec('washroom', (3, 3), (3, 3), wing='west wing'),
            Spec('store', (3, 3), (3, 3), wing='east wing')]
    return out


def _top(rng):
    out = _guest(rng, 1)
    out.append(Spec('office', (4, 5), (4, 5), wing='suites'))
    return out


FLOORS = {
    'function': {'label': 'Function Rooms', 'program': _function, 'story': 'rats',
                 'people': {'like': ['Vault11b', 'CampGuardianCaves2', 'Vault11a'], 'who': 'creatures', 'busy': 'few', 'said': 'rats'}},
    'service': {'label': 'Kitchens and Service', 'program': _service, 'story': 'quiet', 'kit': BACK, 'like': SERVICE_LIKE,
                'people': {'like': ['NellisTunnel', 'RocketLabMid', 'OVWestSewers02b'], 'who': 'creatures', 'busy': 'usual', 'said': 'feral ghouls'}},
    'guest': {'label': 'Guest Floor', 'program': _guest, 'story': 'taken', 'people': {'who': 'people', 'busy': 'usual'}},
    'top': {'label': 'Top Floor', 'program': _top, 'story': 'taken', 'people': {'who': 'people', 'busy': 'many'}},
}
# what the hotel called each room the planner made for a purpose
NAMES = {'function': {'entrance': 'foyer', 'hall': 'ballroom', 'classroom': 'conference room', 'washroom': 'restrooms', 'rec room': 'bar',
                      'store': 'cloakroom', 'office': "manager's office"},
         'service': {'entrance': 'service corridor', 'mess': 'kitchens', 'store': 'stores', 'workroom': 'laundry', 'reactor': 'boiler room',
                     'quarters': "staff's room", 'washroom': "staff's washroom", 'office': "housekeeper's office"},
         'guest': {'entrance': 'lift lobby', 'rec room': 'lounge', 'quarters': 'guest room', 'washroom': 'bathroom', 'store': 'linen room'},
         'top': {'entrance': 'lift lobby', 'rec room': 'lounge', 'quarters': 'guest room', 'washroom': 'bathroom', 'store': 'linen room',
                 'office': "the boss's suite"}}

# scenes of the hotel's own besides kitlife's (same form: editor ID, across, into, turn, on)
SCENES = dict(L.SCENES)
SCENES.update({
    'luggage': [('SuitCase01Empty', -60, 76, None, None), ('BriefcaseStatic', 30, 84, None, None), ('SuitCase03', -60, 76, None, 0)],
    'left in a hurry': [('SuitCase01Empty', -20, 40, None, None), ('BriefcaseStatic', 50, 30, 0, None), ('Skeleton50sCasualMale', 30, -40, 0, 'lying')],
    'room service': [('Table01', 0, 50, None, None), ('Plate01', -14, 50, 0, 0), ('CoffeeMug01', 20, 54, 0, 0), ('WhiskeyBottle01Empty01', 40, 44, 0, 0)],
    'nest': [('NVBedrollL', -40, 50, None, None), ('Bucket01', 70, 40, 0, None), ('TinCan01', 30, 0, 0, None), ('TinCan01', -10, -20, 0, None)],
})
# what became of each room, by who holds the floor
STORIES = {
    'rats': {'entrance': ('last stand', 'luggage'), 'hall': ('last meal', 'last stand', 'luggage'), 'classroom': ('the note left', 'last meal'),
             'washroom': ('the note left',), 'rec room': ('last meal', 'still'), 'store': ('luggage', 'hoard'), 'office': ('the note left', 'left in a hurry')},
    'quiet': {'entrance': ('last stand', 'barricade'), 'mess': ('last meal', 'kitchen'), 'store': ('hoard', 'last stand'), 'workroom': ('the note left', 'workshop'),
              'reactor': ('workshop', 'last stand'), 'quarters': ('lay down', 'bunks'), 'washroom': ('the note left',), 'office': ('the note left', 'left in a hurry')},
    'taken': {'entrance': ('barricade', 'trophies'), 'rec room': ('camp', 'still', 'trophies'), 'quarters': ('nest', 'bedroll', 'hoard', 'luggage', 'room service'),
              'washroom': ('trophies', 'still'), 'store': ('hoard', 'barricade'), 'office': ('hoard', 'trophies', 'room service')},
}
# finds: something with something in it ('%s' is the floor's loot tier, the game's Gen01 to Gen10)
FINDS = {'quarters': ('VLootHotelWardrobeGen%02d', 'VLootClothesSuitcase01Gen%02d', 'VLootHotelDeskGen%02d'),
         'office': ('VLootHotelDeskGen%02d', 'VLootBriefcase01Gen%02d', 'GenericSafeFloor01'),
         'store': ('LootAmmoBoxGenericNV', 'NVDuffleBagRandomLoot', 'Footlocker01MilitaryNV', 'VLootClothesSuitcase01Gen%02d'),
         'mess': ('VLootFridgeClosed01Tier1Wasteland', 'Footlocker01Liquor'), 'rec room': ('Footlocker01Liquor', 'VLootBriefcase01Gen%02d'),
         'washroom': ('LootDrugKit', 'LootFirstAidKitNV'), 'workroom': ('VLootStashToolboxAbandonedHi', 'Footlocker01FactoryNV'),
         'reactor': ('VLootStashToolboxAbandonedHi', 'LootAmmoBoxGenericLockNV'), 'classroom': ('VLootBriefcase01Gen%02d', 'Footlocker01Library'),
         'hall': ('VLootClothesSuitcase01Gen%02d', 'VLootBriefcase01Gen%02d'), 'entrance': ('LootAmmoBoxGenericNV', 'VLootClothesSuitcase01Gen%02d')}
ALWAYS_LOCKED = ('GenericSafeFloor01', 'LootAmmoBoxGenericLockNV')


class Floor:
    """One floor built: its plan, pieces, things, the square and side of its way in, its lift's square and side."""

    def __init__(self, kind, kit, ts, g, lift, report):
        self.kind, self.kit, self.ts, self.plan, self.made, self.items = kind, kit, ts, g['plan'], g['made'], g['items']
        self.lift, self.report = lift, report


# ---------- the game's kits ----------

_kits = {}


def kits(gd):
    """(kit index, survey, store, walls cache) for these game files, read once."""
    got = _kits.get(id(gd))
    if got is None:
        import kitdress
        import kitindex
        import shipinside
        folder = shipinside.kits_folder(gd)
        ks = kitindex.load(gd, folder)
        got = _kits[id(gd)] = (ks, kitdress.load(gd, ks, folder), {}, {})
    return got


# ---------- what became of it ----------

def _farthest(plan, start=0):
    """Rooms by how many rooms away from the first they are, farthest first."""
    graph = L._owner_graph(plan)
    far = {start: 0}
    todo = collections.deque([start])
    while todo:
        n = todo.popleft()
        for m in graph.get(n, ()):
            if m not in far:
                far[m] = far[n] + 1
                todo.append(m)
    rooms = [o['n'] for o in plan.rooms() if o['n'] in far and o['n'] != start]
    return sorted(rooms, key=lambda n: -far[n])


def _taken(things, items):
    out = set()
    for it in items:
        if it.piece is not None and it.what in D.BIG_KINDS and it.what != 'act' and D.is_furnishing(L._info(things, it)):
            out.update(it.piece.cells)
    return out


def _put_lift(game, ts, plan, made, items, rng, lift_key, avoid, kind='guest'):
    """The lift on a wall of a room the floor would have it in (LIFT_IN: on the top floor the boss's suite), the farthest
    from the way in first, else any but a washroom, else any: (Item, square, side), or None. What stood just in front of
    it goes."""
    things = L.things_of(game)
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    far = _farthest(plan)
    purpose = lambda n: plan.owners[n].get('dress') or plan.owners[n]['purpose']
    want = LIFT_IN.get(kind, ())
    order = sorted((n for n in far if purpose(n) in want), key=lambda n: want.index(purpose(n)))
    order += [n for n in far if n not in order and purpose(n) != 'washroom'] + [n for n in far if purpose(n) == 'washroom'] + [0]
    for n in order:
        if plan.owners[n].get('tall'):
            continue
        walls, _floors = L._spots(plan, pieces[n], _taken(things, items))
        walls = [w for w in walls if w[1] not in avoid]
        if not walls:
            continue
        rng.shuffle(walls)
        m, c, d = walls[0]
        dx, dy = kitplan.DX[d]
        z = c[2] * plan.rise + ts.floor + LIFT_UP
        # (a ray can slip through the seam between two triangles: the middle of five heights)
        hits = sorted(h for h in (wall_face(game, made, c[0] * ts.step, c[1] * ts.step, z + dz, dx, dy) for dz in (-20, 10, 40, 70, 100)) if h is not None)
        face = hits[len(hits) // 2] if len(hits) >= 3 else None
        if face is None or not L.WALL_LIMIT - 24 < face < ts.step * 0.6:     # (a column in the way, or no wall)
            continue
        into = face - LIFT_DEEP - 1.0           # (its back just off the wall's face)
        x, y = c[0] * ts.step + dx * into, c[1] * ts.step + dy * into
        rz = math.atan2(dx, dy) % (2 * math.pi)          # (its back, +y, to the wall)
        # (nothing solid within a square's reach in front of it)
        cx, cy = c[0] * ts.step, c[1] * ts.step
        items[:] = [it for it in items if it.what in ('door', 'exit', 'light') or math.hypot(it.p[0] - x, it.p[1] - y) > 140 and
                    not (abs(it.p[0] - cx) < ts.step / 2 and abs(it.p[1] - cy) < ts.step / 2 and abs(it.p[2] - (z - LIFT_UP)) < 200)]
        lift = D.Item(lift_key, [round(x, 3), round(y, 3), round(z, 3), 0.0, 0.0, round(rz, 4)], 1.0, 'exit', n, m)
        items.append(lift)
        return lift, c, d
    return None


_tris = {}


def _mesh_tris(game, key):
    if key not in _tris:
        import nif
        f = game.from_key(key)
        t, _e, _n, model = game.describe(f)
        out = []
        try:
            for sh in nif.mesh_from_nif(game.read_file(game.model_path(t, model))):
                p, idx = sh['p'], sh['i']
                for k in range(0, len(idx) - 2, 3):
                    out.append(tuple(tuple(p[3 * idx[k + j]:3 * idx[k + j] + 3]) for j in range(3)))
        except Exception:
            out = []
        _tris[key] = out
    return _tris[key]


def wall_face(game, made, x, y, z, dx, dy, reach=400.0):
    """How far from (x, y, z) along (dx, dy) the first surface of the building's pieces is, or None."""
    best = None
    for m in made:
        if abs(m.x - x) > 700 or abs(m.y - y) > 700 or abs(m.z - z) > 600:
            continue
        c, s = math.cos(m.turn * math.pi / 2), math.sin(m.turn * math.pi / 2)
        for tri in _mesh_tris(game, m.key):
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = [(m.x + p[0] * c + p[1] * s - x, m.y - p[0] * s + p[1] * c - y, m.z + p[2] - z) for p in tri]
            # (a ray along (dx, dy, 0) from the origin, against the triangle: Moller-Trumbore)
            e1, e2 = (bx - ax, by - ay, bz - az), (cx - ax, cy - ay, cz - az)
            h = (-e2[2] * dy, e2[2] * dx, dx * e2[1] - dy * e2[0])
            det = e1[0] * h[0] + e1[1] * h[1] + e1[2] * h[2]
            if abs(det) < 1e-9:
                continue
            f = 1.0 / det
            sv = (-ax, -ay, -az)
            u = f * (sv[0] * h[0] + sv[1] * h[1] + sv[2] * h[2])
            if u < 0 or u > 1:
                continue
            q = (sv[1] * e1[2] - sv[2] * e1[1], sv[2] * e1[0] - sv[0] * e1[2], sv[0] * e1[1] - sv[1] * e1[0])
            v = f * (dx * q[0] + dy * q[1])
            if v < 0 or u + v > 1:
                continue
            t = f * (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2])
            if 0 < t < reach and (best is None or t < best):
                best = t
    return best


def _life(game, ts, plan, made, items, rng, story, tier):
    """Scenes and finds by what each room was for and who holds the floor (kitlife.live, for a hotel)."""
    things = L.things_of(game)
    tale = STORIES[story]
    plan.finds = []
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    taken = _taken(things, items)
    for it in items:
        if it.what == 'exit' and it.piece is not None:
            taken.update(it.piece.cells)
    for o in plan.owners:
        if o['kind'] != D.ROOM_KIND or not pieces[o['n']]:
            continue
        purpose = o.get('dress') or o['purpose']
        walls, floors = L._spots(plan, pieces[o['n']], taken)
        rng.shuffle(walls)
        rng.shuffle(floors)
        squares = sum(1 for c in o['cells'] if c not in plan.air)
        names = list(tale.get(purpose, ()))
        rng.shuffle(names)
        if o.get('wrecked'):
            names = ['last stand'] if rng.random() < 0.5 else ['lay down']
        o['scenes'] = []
        most = max(1, squares // D.SAME_THING)
        have = collections.Counter(it.key for it in items if it.owner == o['n'] and it.what in D.BIG_KINDS)
        for k in range(min(len(names), L.SCENES_MOST, 1 + squares // L.SQUARES_PER_SCENE)):
            name = names[k]
            where = walls or (floors if name in L.IN_THE_OPEN else [])
            if not where:
                continue
            m, c, d = where.pop()
            if d is None:
                d = rng.randrange(4)
            got = L._lay_scene(things, ts, plan, m, c, d, SCENES[name], rng)
            mine = collections.Counter(it.key for it in got if it.what in D.BIG_KINDS)
            got = [it for it in got if it.what not in D.BIG_KINDS or mine[it.key] > 1 or have[it.key] < most]
            have.update(it.key for it in got if it.what in D.BIG_KINDS)
            items += got
            taken.add(c)
            o['scenes'].append(name)
        if not walls or rng.random() >= FIND_SHARE:
            continue
        options = [f % tier if '%' in f else f for f in FINDS.get(purpose, L.ANY_FIND)]
        options = [f for f in options if f in things.keys]
        if not options:
            continue
        ed = rng.choice(options)
        key = things.game.key(things.keys[ed][0])
        if have[key] >= most:
            continue
        m, c, d = walls.pop()
        got = L._lay_scene(things, ts, plan, m, c, d, [(ed, rng.choice((-60, 0, 60)), 84, None, None)], rng)
        plan.finds += got
        items += got
        taken.add(c)
        o['find'] = ed


def _secure(game, ts, plan, items, rng, kind, key_name=None, lift=None):
    """Locks: some rooms nothing lies beyond, some finds, harder higher up; on the top floor the lift on a key left on a
    find in another room (key_name: '$' + the key's record). plan.locks says what was done."""
    plan.locks = {'rooms': 0, 'finds': 0, 'key': None}
    rooms = {o['n']: o for o in plan.rooms()}
    base = LOCK_FROM[kind]
    level = lambda: L.LOCKS[max(0, min(len(L.LOCKS) - 1, base + rng.choice((0, 0, 1, 1, 2))))]
    can = L.lockable(plan, items)
    lift_room = lift.owner if lift is not None else None
    others = [n for n in can if n != lift_room]
    rng.shuffle(others)
    graph = L._owner_graph(plan)
    everyone = L._reach(graph, 0)
    want = max(1, int(round(len(rooms) * LOCKED_SHARE)))
    shut, closed = [], set()
    for n in others:
        if len(shut) >= want:
            break
        if len(L._reach(graph, 0, without=closed | {n})) == len(everyone) - len(closed | {n}):
            shut.append(n)
            closed.add(n)
    for n in shut:
        lv = level()
        for d in can[n]:
            d.extra = L._lock(lv)
        plan.locks['rooms'] += 1
    present = {id(it) for it in items}
    finds = [it for it in plan.finds if id(it) in present and it.owner in rooms]
    if key_name and lift is not None:
        # (the key to the penthouse: on a find in a room left open, the farthest from the way in that isn't the lift's)
        things = L.things_of(game)
        things.keys.setdefault(MASTER_KEY_FROM, (_key_fid(game), 'misc'))
        key_size = things.size(MASTER_KEY_FROM)
        far = {n: k for k, n in enumerate(_farthest(plan))}
        open_finds = [it for it in finds if it.owner not in closed and it.owner != lift_room]
        if open_finds and key_size:
            spot = min(open_finds, key=lambda it: (far.get(it.owner, 99), rng.random()))
            size = things.size(game.describe(game.from_key(spot.key))[1])
            if size:
                z = spot.p[2] + size[1] - key_size[0] + 1
                items.append(D.Item(key_name, [spot.p[0], spot.p[1], z, 0.0, 0.0, rng.random() * 2 * math.pi], 1.0, 'key', spot.owner, spot.piece))
                finds.remove(spot)
                lift.extra = L._lock(L.KEY_LOCK, key_name)
                plan.locks['key'] = rooms[spot.owner].get('dress') or rooms[spot.owner]['purpose']
    for it in finds:
        ed = game.describe(game.from_key(it.key))[1]
        if ed in ALWAYS_LOCKED:
            it.extra = L._lock(max(50, level()))
        elif rng.random() < FIND_LOCKED:
            it.extra = L._lock(level())
        else:
            continue
        plan.locks['finds'] += 1


def _key_fid(game):
    return next(f for f, (_i, r) in game.forms.items() if r.tag == 'KEYM' and f >> 24 == 0 and game.edid(f) == MASTER_KEY_FROM)


def key_record(game, tag, label):
    rec = recordio.load(game, _key_fid(game))
    recordio.set_field(rec, 'EDID', 'FOLab%sPenthouseKey' % tag)
    recordio.set_field(rec, 'FULL', '%s Penthouse Key' % label.replace('The ', ''))
    rec['src'] = rec.get('src') or ''
    return rec


# ---------- a floor ----------

def build_floor(gd, hotel, kind, n, seed, last=False):
    """One floor planned, built, walked, dressed, with what became of it and its lift: Floor. ValueError when no seed of
    TRIES walks."""
    H = HOTELS[hotel]
    F = FLOORS[kind]
    ks, survey, store, cache = kits(gd)
    kit = F.get('kit') or H['kit']
    if kit not in ks:
        raise ValueError('These game files lack the %s kit.' % kit)
    ts = kitplan.tiles_for(gd, ks, kit, store, survey)
    things = L.things_of(gd)
    lift_key = _lift_key(gd)
    why = collections.Counter()
    for k in range(TRIES):
        s = seed * 7919 + n * 104729 + k * 271 + sum(ord(ch) * 1009 for ch in hotel)     # (each hotel a floor of its own)
        rng = random.Random(s)
        g = kitplan.generate(gd, ts, seed=s, cache=cache, program=F['program'](rng), stairs=0.3, survey=survey, tries=4)
        if not g:
            why['no plan walked'] += 1
            continue
        plan, made, items = g['plan'], g['made'], list(g['items'])
        items = _own_files(gd, made, items)
        if not plan.exit or not any(it.what == 'exit' for it in items):
            why['no way in'] += 1
            continue
        got = _put_lift(gd, ts, plan, made, items, rng, lift_key, {plan.exit[0]}, kind)
        if not got:
            why['no wall for the lift'] += 1
            continue
        lift = got[0]
        _life(gd, ts, plan, made, items, rng, F['story'], TIERS[kind])
        D.keep_fronts(ts, plan, items)
        walk = D.clear_ways(gd, ts, plan, made, items, kitplan.walk_check, cache)
        if walk['missing'] or walk['escaped'] or lift not in items:
            why['things in the way'] += 1
            continue
        _secure(gd, ts, plan, items, rng, kind, '$hf_%s_key' % hotel if last else None, lift)
        names = NAMES[kind]
        rooms = collections.Counter(names.get(o.get('dress') or o['purpose'], o.get('dress') or o['purpose']) for o in plan.rooms())
        kinds = collections.Counter(it.what for it in items)
        rep = {'kind': kind, 'kit': kit, 'seed': s, 'rooms': sorted(rooms.items()), 'levels': len({c[2] for c in plan.squares()}),
               'pieces': len(made), 'things': len(items), 'doors': kinds['door'], 'lights': kinds['light'], 'finds': len(plan.finds),
               'locked rooms': plan.locks['rooms'], 'locked finds': plan.locks['finds'], 'key in': plan.locks['key'],
               'tall': sum(1 for o in plan.rooms() if o.get('tall'))}
        return Floor(kind, kit, ts, dict(g, items=items), got, rep)
    raise ValueError('%s, %s: no floor walked in %d tries (%s).' % (H['label'], F['label'], TRIES, ', '.join('%s %d' % w for w in why.most_common())))


_lifts = {}


def _lift_key(gd):
    if id(gd) not in _lifts:
        f = next((f for f, (_i, r) in gd.forms.items() if r.tag == 'DOOR' and f >> 24 == 0 and gd.edid(f) == LIFT), None)
        if f is None:
            raise ValueError('These game files lack the hotel lift door (%s).' % LIFT)
        _lifts[id(gd)] = gd.key(f)
    return _lifts[id(gd)]


def _own_files(gd, made, items):
    """What a floor may hold: things of the base game's or of the kit's own file (no Gun Runners' Arsenal crate in the
    Kilauea because the Lucky 38's rooms had one), and nothing with a script but the harmless (a bed, a workbench): the
    places' own doors, terminals and passes run their quests' scripts (the Lucky 38's mainframe, Gomorrah's lift, Dead
    Money's suites pass). A door taken out leaves its doorway open."""
    ok = {0} | {gd.from_key(m.key) >> 24 for m in made}
    out = []
    for it in items:
        if it.key.startswith('$'):
            out.append(it)
            continue
        f = gd.from_key(it.key)
        if f >> 24 not in ok:
            continue
        if 'SCRI' in gd.fields(f) and _script_of(gd, f) not in HARMLESS:
            twin = _plain_twin(gd, f) if it.what in ('door', 'exit') else None
            if twin is None:
                continue
            it.key = twin                       # (the same door with no script: Gomorrah's lift door is the hotels' own)
        out.append(it)
    return out


_twins = {}


def _plain_twin(gd, f):
    """A door of the base game's with the same model and no script, or None."""
    if f not in _twins:
        model = (gd.fields(f).get('MODL') or b'').split(b'\0')[0].lower()
        _twins[f] = next((gd.key(g) for g, (_i, r) in gd.forms.items() if r.tag == 'DOOR' and g >> 24 == 0 and g != f and model
                          and (gd.fields(g).get('MODL') or b'').split(b'\0')[0].lower() == model and 'SCRI' not in gd.fields(g)), None)
    return _twins[f]


def _script_of(gd, f):
    import struct
    v = struct.unpack_from('<I', gd.fields(f)['SCRI'])[0]
    g = gd.to_global(gd.forms[f][0], v)
    return gd.edid(g) if g in gd.forms else None


def _arrive(ts, plan, c, d):
    """Where you arrive by a door on square c's side d: the square's middle, facing away from the door."""
    dx, dy = kitplan.DX[d]
    return [round(c[0] * ts.step, 2), round(c[1] * ts.step, 2), round(c[2] * plan.rise + ts.floor + 10, 2), 0.0, 0.0,
            round(math.atan2(-dx, -dy) % (2 * math.pi), 4)]


# ---------- the hotel ----------

def make(gd, pr, hotel, seed=1):
    """A hotel's floors as ops: see the module's docstring."""
    H = HOTELS[hotel]
    if any(k.startswith('+') and r.get('type') == 'CELL' and (recordio.field(r, 'EDID') or '').startswith('FOLab%sFloor' % H['tag'])
           for k, r in pr.records.items()):
        raise ValueError('%s already has its floors.' % H['label'])
    kinds = H['floors']
    built = []
    for n, kind in enumerate(kinds):
        built.append(build_floor(gd, hotel, kind, n, seed, last=n == len(kinds) - 1))
    ops = [{'op': 'record_new', 'record': key_record(gd, H['tag'], H['label']), 'name': 'hf_%s_key' % hotel}]
    places, people, report = [], {}, []
    guest_no = 0
    for n, (kind, F) in enumerate(zip(kinds, built)):
        label = FLOORS[kind]['label']
        if kind == 'guest':
            guest_no += 1
            label = 'Guest Floor %d' % guest_no if kinds.count('guest') > 1 else label
        full = '%s: %s' % (H['label'], label)
        like = FLOORS[kind].get('like') or H['like']
        cell = next((c for c in gd.interiors if (gd.edid(c) or '').lower() == like.lower()), None)
        if cell is None:
            raise ValueError('These game files lack %s, whose light the %s copies.' % (like, full))
        rec = recordio.load(gd, cell)
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('XOWN', 'XRNK', 'XCMO', 'XEZN', 'XCCM', 'XCWT')]
        recordio.set_field(rec, 'EDID', 'FOLab%sFloor%d' % (H['tag'], n + 1), label='Editor ID')
        recordio.set_field(rec, 'FULL', full, label='Name')
        name = 'hf_%s_%d' % (hotel, n)
        ops.append({'op': 'record_new', 'record': rec, 'name': name})
        ck = '$' + name
        for o in kitplan.as_ops(F.ts, F.made):
            ops.append(dict(o, cell=ck))
        lift = F.lift[0]
        for it, o in zip(F.items, D.item_ops(F.items)):
            o = dict(o, cell=ck)
            o.pop('exit', None)
            if it is lift:
                o['name'] = name + '_up'
                o['extra'] = dict(o.get('extra') or {}, persistent=True)
            elif it.what == 'exit':
                o['name'] = name + '_in'
                o['extra'] = dict(o.get('extra') or {}, persistent=True)
            elif it.what == 'key':
                o['base'] = '$hf_%s_key' % hotel
            ops.append(o)
        places.append({'name': name, 'label': full, 'kind': kind, 'arrive_in': _arrive(F.ts, F.plan, *F.plan.exit), 'arrive_up': _arrive(F.ts, F.plan, F.lift[1], F.lift[2])})
        who = dict(FLOORS[kind]['people'])
        if kind in ('guest', 'top'):
            who.update(like=H['gang']['like'], said=H['gang']['said'])
        people[name] = who
        report.append(dict(F.report, place=full))
    # (each floor's lift up to the next floor's way in, and that back down to the lift)
    for a, b in zip(places, places[1:]):
        ops.append({'op': 'tel', 'cell': '$' + a['name'], 'ref': '$%s_up' % a['name'], 'tel': {'door': '$%s_in' % b['name'], 'p': b['arrive_in']}})
        ops.append({'op': 'tel', 'cell': '$' + b['name'], 'ref': '$%s_in' % b['name'], 'tel': {'door': '$%s_up' % a['name'], 'p': a['arrive_up']}})
    first, last = places[0], places[-1]
    return {'ops': ops, 'places': [p['name'] for p in places], 'labels': {p['name']: p['label'] for p in places},
            'entry': {'place': first['name'], 'door': first['name'] + '_in', 'arrive': first['arrive_in']},
            'top': {'place': last['name'], 'door': last['name'] + '_up', 'arrive': last['arrive_up']},
            'arrive': {p['name']: {'in': p['arrive_in'], 'up': p['arrive_up']} for p in places},
            'people': people, 'report': report, 'key': 'hf_%s_key' % hotel, '_floors': built}     # (_floors: the Floor objects, for checking)


def navmesh_ops(gd, pr, made, names):
    """After make's ops are applied (names: project.names as they left them): each place's navmesh. ({'op': 'navmesh'}
    ops, {place: report or why not})."""
    import navbuild
    out, rep = [], {}
    for n in made['places']:
        ck = names.get(n)
        if not ck:
            continue
        try:
            data, r = navbuild.generate(gd, pr, ck)
        except navbuild.NavError as e:
            rep[n] = str(e)
            continue
        out.append({'op': 'navmesh', 'cell': ck, 'mesh': data})
        rep[n] = r
    return out, rep


def people_ops(gd, pr, made, names, seed=1):
    """After the navmeshes are applied: who holds each floor, as ops (populate's plan and apply, the game's own people
    for places like it), nobody within KEEP_CLEAR of where you arrive. ({'op': 'add'} ops, {place: what was placed})."""
    import populate
    ops, rep = [], {}
    for k, n in enumerate(made['places']):
        ck = names.get(n)
        if not ck:
            continue
        who = made['people'][n]
        body = {'cell': ck, 'like': who['like'], 'who': who['who'], 'busy': who['busy'], 'seed': seed * 31 + k, 'skip': list(L.NOT_PLACED), 'difficulty': 'auto'}
        got = populate.plan(gd, pr, None, body)
        rows = got.get('rows') or []
        if not rows:
            rep[n] = '; '.join(got.get('notes') or ['nobody'])
            continue
        a = made['arrive'][n]
        mine = []

        def collect(label, o):
            mine.extend(o)
            return {}
        # (away from both doors: the way in, and the lift you come back down by)
        body2 = dict(body, rows=rows, gen=True, away=a['in'][:3] + [KEEP_CLEAR])
        populate.apply(gd, pr, None, collect, body2)
        up = a['up']
        kept = [o for o in mine if o.get('op') != 'add' or math.hypot(o['p'][0] - up[0], o['p'][1] - up[1]) > KEEP_CLEAR or abs(o['p'][2] - up[2]) > 200]
        ops += kept
        rep[n] = {'placed': sum(1 for o in kept if o.get('op') == 'add'), 'who': who['said'], 'model': got.get('model')}
    return ops, rep
