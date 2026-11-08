"""What two hundred years did to a vault. A vault is a survival shelter people went on living in, or came to later: under what
kitdress.py stands in each room (what it was built for), this lays what became of it, so a room is worth walking into.

Each vault has one story (STORIES: settled, taken over, or gone quiet), and each room's purpose and that story choose small scenes:
a few of the game's own things arranged on one square, against a wall if the scene wants one. Most rooms also have a find:
something with something in it. Only for vault kits; things come from FalloutNV.esm, so a mod needs no other master for them.

    live(game, ts, plan, made, items, rng, only=None)      adds to items; plan.story says which
    secure(game, ts, plan, made, items, rng)               locks: some rooms' doors and finds, the office on a key left elsewhere
    people(plan)                                           who Populate puts in, learnt from the game's places for the story

A scene is [(editor ID, across, into, turn, on)]: across the wall and towards it from the square's middle, in game units; turn in
quarter turns, or None to lie along the wall; on: the number of the thing in this scene it stands on."""
import collections
import math

import kitdress as D
import kitindex as K
import nif

SCENES = {
    # people living here
    'bunks': [('BedMattress01FloorL', -50, 60, None, None), ('Footlocker01HouseholdNV', 56, 80, None, None), ('Bucket01', 92, 30, 0, None)],
    'bedroll': [('NVBedrollL', -30, 40, None, None), ('Footlocker01Empty', 70, 84, None, None), ('Lunchbox', 70, 84, 0, 1), ('TinCan01', 30, -20, 0, None)],
    'kitchen': [('CookStove', 0, 84, 2, None), ('PotCookingMetal', 70, 40, 0, None), ('Table01', -74, 50, None, None), ('Plate01', -74, 50, 0, 2), ('MilkCrate01', 70, 86, 0, None)],
    'still': [('Barrel01', -66, 76, 0, None), ('BigPot', 0, 80, 0, None), ('Table01', 66, 60, None, None), ('WhiskeyBottle01Empty01', 58, 56, 0, 2), ('SSBottleEmpty', 76, 64, 0, 2), ('Moonshine', 66, 44, 0, 2)],
    'garden': [('Planter01', -60, 70, None, None), ('Planter02', 60, 70, None, None), ('MaizeWitheredGroup1', 0, 10, 0, None), ('Bucket01', -20, 30, 0, None), ('ShackHangingLight02', 0, 40, 0, 'high')],
    'stall': [('Table02', 0, 66, None, None), ('LootCashRegisterNV', 24, 66, 2, 0), ('MilkCrate01', -86, 84, 0, None), ('CrateLarge01', 86, 76, None, None), ('SSBottleFull', -30, 60, 0, 0)],
    'workshop': [('WorkBench', 0, 84, 2, None), ('ToolCabinetMetal', 88, 84, 2, None), ('SpareParts', -60, 40, 0, None), ('ScrapElectronics', -30, 24, 0, None)],
    'radio post': [('Table01', 0, 70, None, None), ('HamRadioDestroyed', 0, 74, 2, 0), ('ChairVaultStatic', 0, 10, 0, None), ('BulletinBoard03', 60, 118, 2, 'wall')],
    'lessons': [('ChalkboardDirty01', 0, 118, 2, 'wall'), ('BenchMuseumStatic01', 0, -20, None, None), ('BookGeneric01', 40, -20, 0, 0)],
    'hoard': [('MilkCrate01', -80, 84, 0, None), ('MilkCrate01', -36, 84, 1, None), ('CrateGenericNV', 50, 76, None, None), ('Footlocker01MilitaryNV', 0, 40, None, None)],
    # people who took it
    'camp': [('Barrel02Fire256', 0, 0, 0, None), ('NVBedrollR', -70, 60, None, None), ('NVBedrollL', 70, 60, None, None), ('WhiskeyBottle01Empty01', 30, -40, 0, None), ('TinCan01', -30, -44, 0, None)],
    'barricade': [('SandbagSingle', -80, 30, 1, None), ('SandbagSingle', -28, 30, 1, None), ('SandbagSingle', 28, 30, 1, None), ('SandbagSingle', 80, 30, 1, None), ('SandbagSingle', -54, 30, 1, 0), ('SandbagSingle', 2, 30, 1, 1), ('SandbagSingle', 54, 30, 1, 2), ('MetalPlank01', 40, 66, None, None), ('LootAmmoBoxGenericNV', -40, 70, None, None)],
    'trophies': [('RaiderCorpseDressingChain', 0, 100, 0, None), ('GorePile01', 0, 40, 0, None), ('Vault87Blood07', 0, 0, 0, None), ('SkullBloody', 40, 70, 0, None), ('Footlocker01Empty', -70, 84, None, None)],
    'chop shop': [('OperatingTableR01', 0, 50, None, None), ('Vault87Blood02', 0, 10, 0, None), ('SurgicalSyringe01', 60, 30, 0, None), ('LootFirstAidKitNV', 80, 112, 2, 'wall')],
    # people who didn't make it
    'last stand': [('SandbagSingle', -40, 20, None, None), ('SandbagSingle', 40, 20, None, None), ('SkeletonWholeBodyClothes', 10, 60, 0, 'lying'), ('Vault87Blood03', 10, 56, 0, None), ('LootAmmoBoxGenericNV', 70, 80, None, None)],
    'lay down': [('BedMattress01FloorL', 0, 60, None, None), ('SkeletonWholeBodyRags', 0, 20, 0, 'lying'), ('TeddyBear01', 40, 40, 0, None), ('Lunchbox', -60, 30, 0, None)],
    'last meal': [('Table01', 0, 30, None, None), ('Plate01', 12, 30, 0, 0), ('CoffeeMug01', -20, 34, 0, 0), ('Skeleton50sCasualMale', 40, -46, 0, 'lying'), ('Skull', -60, 70, 0, None)],
    'the note left': [('ChalkboardDirty02', 0, 118, 2, 'wall'), ('SkeletonTorsoMaleClothes', -40, 40, 0, None), ('Pencil01', 0, 30, 0, None), ('Clipboard01', 30, 40, 0, None)],
}
# the scenes each story has for what a room was built for: what people did with it after
STORIES = {
    'settled': {'said': 'People still live here: the rooms are put to whatever they need now.',
                'quarters': ('bunks', 'bedroll'), 'small room': ('bunks',), 'washroom': ('still', 'garden'), 'mess': ('kitchen', 'stall'), 'rec room': ('still', 'radio post'), 'classroom': ('lessons', 'bunks'),
                'clinic': ('bunks', 'chop shop'), 'store': ('hoard', 'stall'), 'workroom': ('workshop',), 'reactor': ('workshop', 'radio post'), 'office': ('radio post', 'lessons'),
                'atrium': ('stall', 'garden', 'kitchen'), 'hall': ('stall', 'garden'), 'entrance': ('barricade', 'radio post')},
    'taken': {'said': 'Others took it over long ago: what was left of the vault is their camp now.',
              'quarters': ('camp', 'bedroll', 'hoard'), 'small room': ('bedroll',), 'washroom': ('trophies', 'hoard'), 'mess': ('camp', 'still'), 'rec room': ('still', 'trophies'), 'classroom': ('camp', 'trophies'),
              'clinic': ('chop shop',), 'store': ('hoard', 'barricade'), 'workroom': ('workshop', 'hoard'), 'reactor': ('barricade', 'workshop'), 'office': ('hoard', 'trophies'),
              'atrium': ('camp', 'barricade', 'trophies'), 'hall': ('camp', 'barricade'), 'entrance': ('barricade', 'trophies')},
    'quiet': {'said': 'It went quiet a long time ago: what is left says how it ended, room by room.',
              'quarters': ('lay down', 'bunks'), 'small room': ('lay down',), 'washroom': ('the note left',), 'mess': ('last meal', 'kitchen'), 'rec room': ('last meal', 'the note left'), 'classroom': ('lessons', 'the note left'),
              'clinic': ('chop shop', 'lay down'), 'store': ('last stand', 'hoard'), 'workroom': ('the note left', 'workshop'), 'reactor': ('last stand', 'the note left'), 'office': ('the note left', 'last stand'),
              'atrium': ('last stand', 'last meal'), 'hall': ('last stand',), 'entrance': ('last stand', 'barricade')},
}
FINDS = {'clinic': ('LootFirstAidKitNV', 'LootFirstAidKitLockNV'), 'store': ('LootAmmoBoxGenericNV', 'NVDuffleBagRandomLoot', 'Footlocker01MilitaryNV'), 'office': ('GenericSafeFloor01', 'LootGunCabinetNVGunsLocked'),
         'quarters': ('Footlocker01HouseholdNV', 'NVDuffleBagRandomLoot'), 'workroom': ('VLootStashToolboxAbandonedHi', 'Footlocker01FactoryNV'), 'reactor': ('VLootStashToolboxAbandonedHi', 'LootAmmoBoxGenericLockNV'),
         'mess': ('VLootFridgeClosed01Tier1Wasteland', 'Footlocker01Liquor'), 'rec room': ('Footlocker01Toys', 'Footlocker01Liquor'), 'classroom': ('Footlocker01Library',), 'washroom': ('LootDrugKit',)}
ANY_FIND = ('NVDuffleBagRandomLoot', 'Footlocker01HouseholdNV', 'LootAmmoBoxGenericNV')
FIND_SHARE = 0.65       # (of rooms, how many have something in them to find)
SQUARES_PER_SCENE = 10  # (a room has one scene, and another for this many squares)
SCENES_MOST = 4
WALL_LIMIT = 104        # (how far from a square's middle something can stand against its wall)
# who lives in a vault of each story: Populate learns from these of the game's places (vaults where it can; nobody lives on in
# one of the game's vaults, so settlers come from the sewers and squats where the game's own people live underground)
PEOPLE = {'settled': {'like': ['OVNorthSewers01', 'OVNVTheGray', 'FreesideSupplyDropHouse'], 'who': 'people', 'live': True, 'busy': 'few',
                      'said': 'people living here'},
          'taken': {'like': ['Vault3a', 'Vault3b', 'Vault3c', 'Vault74a', 'Vault19a'], 'who': 'people', 'busy': 'usual', 'said': 'the gang that took it'},
          'quiet': {'like': ['Vault34a', 'Vault34b', 'Vault11a', 'Vault11b'], 'who': 'creatures', 'busy': 'usual', 'said': 'what lives here now'}}
NOT_PLACED = ('turret',)        # (turrets go on ceilings and walls, with a terminal: not stood on the floor)
KEEP_CLEAR = 700        # (nobody stands this near the way in)
LOCKS = (0, 25, 50, 75, 100)
LOCKED_SHARE = 0.2      # (of rooms, how many are locked if they can be: the game's vaults lock 2 to 7 doors)
FIND_LOCKED = 0.35      # (of finds, how many are locked)
ALWAYS_LOCKED = ('GenericSafeFloor01', 'LootGunCabinetNVGunsLocked')
KEY_FROM = 'Vault101OverseersKey'
KEY_NAME = "Overseer's Key"
KEY_LOCK = 255          # (needs a key)
WALL_HIGH = 150         # (where something hung on a wall goes)
# things the game hangs on a wall, and how high their middles are over the floor where it does (measured from its own places)
HUNG_AT = {'LootFirstAidKitNV': 100, 'LootFirstAidKitLockNV': 97, 'LootDrugKit': 108}
# scenes that can stand in the middle of a room when its walls are taken: the rest need a wall at their back
IN_THE_OPEN = {'camp', 'last stand', 'last meal', 'barricade'}


class _Things:
    """Things by editor ID: their keys, and how they stand (from their meshes)."""

    def __init__(self, game):
        self.game = game
        self.keys, self.sizes = {}, {}
        for fid, (_i, rec) in game.forms.items():
            if fid >> 24 == 0 and rec.tag in D.COPY:
                ed = game.describe(fid)[1]
                if ed:
                    self.keys.setdefault(ed, (fid, D.COPY[rec.tag]))

    def size(self, ed):
        """(lowest z, highest z, half across x, half across y) of its mesh, or None."""
        if ed in self.sizes:
            return self.sizes[ed]
        got = None
        fid = self.keys.get(ed, (None,))[0]
        if fid is not None:
            t, _e, _n, model = self.game.describe(fid)
            try:
                pts = [q for s in nif.mesh_from_nif(self.game.read_file(self.game.model_path(t, model))) for q in zip(*[iter(s['p'])] * 3)]
            except Exception:           # (a thing whose mesh can't be read isn't worth losing a place over: it's left out)
                pts = []
            if pts:
                got = (min(p[2] for p in pts), max(p[2] for p in pts), (max(p[0] for p in pts) - min(p[0] for p in pts)) / 2, (max(p[1] for p in pts) - min(p[1] for p in pts)) / 2)
        self.sizes[ed] = got
        return got


_kept = {}


def things_of(game):
    got = _kept.get(id(game))
    if got is None:
        got = _kept[id(game)] = _Things(game)
    return got


def _wall_of(plan, c):
    """The side of this square with a wall to stand against, or None. A doorway's side isn't one, and neither is a square with one."""
    need = plan.need(c)
    if 'p' in need:
        return None
    walls = [d for d in range(4) if need[d] in 'cx']
    return walls[0] if len(walls) == 1 else None


def _lay_scene(things, ts, plan, m, c, d, scene, rng):
    """A scene's things on square c of piece m, its wall on side d: [Item]. Everything in it stands on the floor, on another of
    its things, or on the wall."""
    step = ts.step
    cx, cy = c[0] * step, c[1] * step
    floor = c[2] * plan.rise + ts.floor
    out, tops = [], {}
    dx, dy = K.DX[d]
    ax, ay = K.DX[(d + 1) % 4]
    flip = rng.choice((-1, 1))
    for n, (ed, across, into, turn, on) in enumerate(scene):
        got = things.keys.get(ed)
        size = things.size(ed)
        if not got or not size and got[1] != 'light':
            continue
        low, high, hx, hy = size or (0.0, 0.0, 0.0, 0.0)
        rx = 0.0
        if ed in HUNG_AT:
            # (hung as the game hangs it, facing out like a chalkboard)
            on, turn = 'wall', 2
        # (the long way along the wall, unless the scene says)
        if turn is None:
            quarter = 0 if hx >= hy else 1
            reach = min(hx, hy)
        else:
            quarter = turn
            reach = hy if turn % 2 == 0 else hx
        if on == 'wall':
            into = WALL_LIMIT - (reach if ed in HUNG_AT else 0)
            z = floor + HUNG_AT[ed] if ed in HUNG_AT else floor + WALL_HIGH - (low + high) / 2
        elif on == 'high':
            z = floor + 200
        elif on == 'lying':         # (as the game lays its dead out: on the back, a little off the floor)
            z, rx = floor + 14, -math.pi / 2
        elif isinstance(on, int):
            z = tops.get(on, floor) - low
        else:
            into = min(into, WALL_LIMIT - reach)
            z = floor - low
        tops[n] = z + high
        x = cx + flip * across * ax + into * dx
        y = cy + flip * across * ay + into * dy
        # (a thing's turn is counted from the wall's side: the game's angle goes clockwise from north)
        rz = ((d - 1) * -math.pi / 2 + quarter * math.pi / 2) % (2 * math.pi)
        key = things.game.key(got[0])
        out.append(D.Item(key, [x, y, z, rx, 0.0, rz], 1.0, got[1], m.owner, m))
    return out


def _spots(plan, pieces, taken):
    """Squares of a room free to have a scene: (piece, square, wall side). Against a wall first, for what wants one."""
    walls, floors = [], []
    for m in pieces:
        if len(m.cells) != 1 or m.cell in taken or m.cell in plan.air:
            continue
        need = plan.need(m.cell)
        if 'p' in need:
            continue
        d = _wall_of(plan, m.cell)
        if d is not None:
            walls.append((m, m.cell, d))
        elif need == 'oooo':
            floors.append((m, m.cell, None))
    return walls, floors


def live(game, ts, plan, made, items, rng, only=None):
    """Adds what became of the vault to items. Rooms that had something standing on a square keep it: scenes go on free ones."""
    if 'vault' not in ts.kit.name.lower():
        return
    things = things_of(game)
    if not getattr(plan, 'story', None):
        plan.story = rng.choice(sorted(STORIES))
    story = STORIES[plan.story]
    if only is None:
        plan.finds = []
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    taken = set()
    for it in items:
        if it.piece is not None and it.what in D.BIG_KINDS and it.what != 'act' and D.is_furnishing(_info(things, it)):
            taken.update(it.piece.cells)
    for o in plan.owners:
        if o['kind'] != D.ROOM_KIND or not pieces[o['n']] or (only is not None and o['n'] != only):
            continue
        purpose = o.get('dress') or o['purpose']
        walls, floors = _spots(plan, pieces[o['n']], taken)
        rng.shuffle(walls)
        rng.shuffle(floors)
        squares = sum(1 for c in o['cells'] if c not in plan.air)
        names = list(story.get(purpose, ()))
        rng.shuffle(names)
        if o.get('wrecked'):
            names = ['last stand'] if rng.random() < 0.5 else ['lay down']
        o['scenes'] = []
        # (how many of one big thing the room may have: as kitdress keeps it, a scene's own several of a thing apart)
        most = max(1, squares // D.SAME_THING)
        have = collections.Counter(it.key for it in items if it.owner == o['n'] and it.what in D.BIG_KINDS)

        def room_for(got):
            mine = collections.Counter(it.key for it in got if it.what in D.BIG_KINDS)
            return [it for it in got if it.what not in D.BIG_KINDS or mine[it.key] > 1 or have[it.key] < most]
        for k in range(min(len(names), SCENES_MOST, 1 + squares // SQUARES_PER_SCENE)):
            name = names[k]
            # (most scenes want a wall at their back: only a camp or a last stand stands out in the open)
            where = walls or (floors if name in IN_THE_OPEN else [])
            if not where:
                continue
            m, c, d = where.pop()
            if d is None:
                d = rng.randrange(4)
            got = room_for(_lay_scene(things, ts, plan, m, c, d, SCENES[name], rng))
            have.update(it.key for it in got if it.what in D.BIG_KINDS)
            items += got
            taken.add(c)
            o['scenes'].append(name)
        ed = rng.choice(FINDS.get(purpose, ANY_FIND)) if walls else None
        key = things.game.key(things.keys[ed][0]) if ed in things.keys else None
        if key and rng.random() < FIND_SHARE and have[key] < most:
            m, c, d = walls.pop()
            got = _lay_scene(things, ts, plan, m, c, d, [(ed, rng.choice((-60, 0, 60)), 84, None, None)], rng)
            plan.finds = getattr(plan, 'finds', []) + got
            items += got
            taken.add(c)
            o['find'] = ed


def _info(things, it):
    return things.game.describe(things.game.from_key(it.key))[0], [], things.game.describe(things.game.from_key(it.key))[1]


def story_said(plan):
    s = getattr(plan, 'story', None)
    return STORIES[s]['said'] if s else ''


# ---------- locks and keys ----------

def _owner_graph(plan):
    """{owner: {owners it opens on to}}: through a doorway, a flight's end, or a room standing open on a balcony."""
    out = collections.defaultdict(set)
    for link in plan.links:
        a, b = tuple(link)
        oa, ob = plan.cells.get(a), plan.cells.get(b)
        if oa is not None and ob is not None and oa != ob:
            out[oa].add(ob)
            out[ob].add(oa)
    for (c, d) in plan.opens:
        oa, ob = plan.cells.get(c), plan.cells.get((c[0] + K.DX[d][0], c[1] + K.DX[d][1], c[2]))
        if oa is not None and ob is not None and oa != ob:
            out[oa].add(ob)
            out[ob].add(oa)
    return out


def _reach(graph, start, without=()):
    seen, todo = {start}, [start]
    while todo:
        n = todo.pop()
        for m in graph[n]:
            if m not in seen and m not in without:
                seen.add(m)
                todo.append(m)
    return seen


def lockable(plan, items):
    """Rooms their doors alone shut off, with nothing beyond them: {room: [its doors]}. Every doorway of the room has a door in it,
    it doesn't stand open on a balcony, and everything else is still reached from the first room without going through it."""
    graph = _owner_graph(plan)
    doors = collections.defaultdict(list)
    for it in items:
        if it.what == 'door' and it.link is not None:
            doors[it.link].append(it)
    open_on = {plan.cells.get(c) for (c, _d) in plan.opens}
    everyone = _reach(graph, 0)
    ways = collections.defaultdict(list)
    for link in plan.links:
        owners = {plan.cells.get(c) for c in link}
        if len(owners) == 2 and None not in owners:
            for n in owners:
                ways[n].append(link)
    out = {}
    for o in plan.rooms():
        n = o['n']
        if n == 0 or n in open_on or o.get('tall') or n not in everyone or not ways[n]:
            continue
        if any(not doors.get(w) for w in ways[n]):
            continue
        if len(_reach(graph, 0, without={n})) != len(everyone) - 1:
            continue
        out[n] = [d for w in ways[n] for d in doors[w]]
    return out


def _depth(plan, o, top, low):
    """How far down a room is, from 0 (where you come in) to 1 (the deepest)."""
    mine = min(c[2] for c in o['cells'])
    return max(0.0, (top - mine) / (top - low)) if top > low else 0.0


def _level(depth, rng):
    k = int(round(depth * 3)) + rng.choice((0, 0, 1))
    return LOCKS[max(0, min(len(LOCKS) - 1, k))]


def _lock(level, key=''):
    return {'props': {'lock': {'level': level, 'key': key, 'leveled': False}}}


def secure(game, ts, plan, made, items, rng):
    """Locks some rooms' doors and some finds, harder further down, and shuts the overseer's office on a key left on top of a find
    in another room. Only rooms nothing else lies beyond are locked, so nothing is ever shut off but the room itself. The key goes in
    items as '$made' (the key record the ops make first: kitplan.vault). plan.locks says what was done."""
    plan.locks = {'rooms': 0, 'finds': 0, 'key': None, 'shut': []}
    if 'vault' not in ts.kit.name.lower():
        return
    things = things_of(game)
    levels = [c[2] for c in plan.squares()]
    top, low = plan.owners[0]['cells'][0][2], min(levels)
    depth = lambda n: _depth(plan, rooms[n], top, low)
    rooms = {o['n']: o for o in plan.rooms()}
    can = lockable(plan, items)
    office = next((n for n in can if rooms[n]['purpose'] == 'office'), None)
    others = [n for n in can if n != office]
    rng.shuffle(others)
    # (each room shut on its own leaves the rest reached, but two together can cut off what lies between them: each is
    # checked with those already chosen shut too)
    graph = _owner_graph(plan)
    everyone = _reach(graph, 0)
    want = max(1, int(round(len(rooms) * LOCKED_SHARE)))
    shut, closed = [], {office} if office is not None else set()
    for n in others:
        if len(shut) >= want:
            break
        if len(_reach(graph, 0, without=closed | {n})) == len(everyone) - len(closed | {n}):
            shut.append(n)
            closed.add(n)
    present = {id(it) for it in items}
    finds = [it for it in getattr(plan, 'finds', []) if id(it) in present and it.owner in rooms]
    if office is not None:
        # (the key is on a find in a room left open, the deepest there is: the office is worth going down for)
        open_finds = [it for it in finds if it.owner != office and it.owner not in shut]
        things.keys.setdefault(KEY_FROM, (_key_fid(game), 'misc'))
        key_size = things.size(KEY_FROM)
        if open_finds and key_size:
            spot = max(open_finds, key=lambda it: (depth(it.owner), rng.random()))
            size = things.size(game.describe(game.from_key(spot.key))[1])
            if size:
                z = spot.p[2] + size[1] - key_size[0] + 1
                items.append(D.Item('$made', [spot.p[0], spot.p[1], z, 0.0, 0.0, rng.random() * 2 * math.pi], 1.0, 'key', spot.owner, spot.piece))
                finds.remove(spot)          # (a lid with the key on it opens freely)
                plan.locks['key'] = rooms[spot.owner].get('dress') or rooms[spot.owner]['purpose']
                for d in can[office]:
                    d.extra = _lock(KEY_LOCK, '$made')
                plan.locks['rooms'] += 1
                plan.locks['shut'].append(office)
    for n in shut:
        lv = _level(depth(n), rng)
        for d in can[n]:
            d.extra = _lock(lv)
        plan.locks['rooms'] += 1
        plan.locks['shut'].append(n)
    for it in finds:
        ed = game.describe(game.from_key(it.key))[1]
        if ed in ALWAYS_LOCKED:
            it.extra = _lock(max(50, _level(depth(it.owner), rng)))
        elif rng.random() < FIND_LOCKED:
            it.extra = _lock(_level(depth(it.owner), rng))
        else:
            continue
        plan.locks['finds'] += 1


def locks_said(plan):
    k = getattr(plan, 'locks', None)
    if not k or not (k['rooms'] or k['finds']):
        return ''
    out = '%d room%s and %d thing%s to search locked, harder further down.' % (k['rooms'], '' if k['rooms'] == 1 else 's', k['finds'], '' if k['finds'] == 1 else 's')
    if k['key']:
        out += " The overseer's office needs a key: it's in the %s." % k['key']
    return out


def _key_fid(game):
    return next(f for f, (_i, r) in game.forms.items() if r.tag == 'KEYM' and f >> 24 == 0 and game.edid(f) == KEY_FROM)


def key_record(game, seed):
    """The office key, a record of the mod's own copied from one of the game's: recordio's form."""
    import recordio
    rec = recordio.load(game, _key_fid(game))
    recordio.set_field(rec, 'EDID', 'FOLabVaultKey%05X' % (seed & 0xFFFFF))
    recordio.set_field(rec, 'FULL', KEY_NAME)
    rec['src'] = rec.get('src') or ''
    return rec


def people(plan):
    """What the Kit tab asks Populate for once the vault has its navmesh, or None."""
    s = getattr(plan, 'story', None)
    if not s:
        return None
    return dict(PEOPLE[s], skip=list(NOT_PLACED))
