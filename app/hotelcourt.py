"""The Royal Hawaiian's floors as the Kahuna's court: a fortress (docs/waikiki-hotel-interiors.md). hotelfloors builds the
same floors as places taken over by whoever moved in; here every floor is held and kept, one way in and one way on:

    court      over the lobby: the gate room, a guard post, the waiting hall, the throne room (the Kahuna's chair at its far
               end, straight ahead of the doors you come in by), his private room behind it with the lift up; the counting
               room and the clerks' office off the waiting hall
    stores     the court's stores, the reason it rules: a guard post at the stair head, the kitchens, the granary and cold
               store, the armoury, the guards' barracks, the quartermaster's office
    quarters   the court's floor: a guard post at the lift lobby, a lounge, the guards' and courtiers' rooms
    kahuna     the Kahuna's floor: two guard posts in a row, the hall of gifts, his suite with the lift to the lookout, his household

A big hotel, built big: six floors (three of the court's quarters), ten to seventeen rooms a floor.

A guard post is a small room on the main route, a barricade facing the way you come, its far door locked (`GATE`, harder
higher up). The plan has no ways round (kitplan's loops off) but one: the servants' way, a corridor from a room before a
guard post to a room after it, behind a lock of its own (`SERVANTS`), easier than the gate. Rooms nothing lies beyond
are locked as hotelfloors locks them, and the top floor's lift is locked on a key that lies on that floor.

    make(gd, pr, seed)      as hotelfloors.make(gd, pr, 'royal_hawaiian', seed), the floors built as the court
    build_floor(gd, hotel, kind, n, seed, last)     one floor: hotelfloors.Floor, its report saying where the gates are"""
import collections
import math
import random

import hotelfloors as HF
import kitdress as D
import kitlife as L
import kitplan
from kitplan import DX, Spec

HOTEL = 'royal_hawaiian'
KINDS = ('court', 'stores', 'quarters', 'quarters', 'quarters', 'kahuna')
AS = {'court': 'function', 'stores': 'service', 'quarters': 'guest', 'kahuna': 'top'}     # (hotelfloors' tables, by the floor it stands for)
GATE = {'court': 50, 'stores': 75, 'quarters': 75, 'kahuna': 100}        # (a guard post's far door)
SERVANTS = {'court': 25, 'stores': 50, 'quarters': 50, 'kahuna': 75}     # (the servants' way round it)
ARMOURY = 100
THRONE = [('Throne01', 0, 90, 2, None), ('OasisTorch01', -110, 70, None, None), ('OasisTorch01', 110, 70, None, None)]
TRIES = 14

for _p, _t in (('checkpoint', ('store',)), ('private room', ('desk', 'sleep')), ('armoury', ('store',)), ('barracks', ('sleep',)),
               ('throne room', ('eat', 'play')), ('waiting hall', ('eat',)), ('counting room', ('store', 'desk'))):
    D.PURPOSE_TAGS.setdefault(_p, _t)


def _court(rng):
    out = [Spec('entrance', (4, 5), (4, 4), True), Spec('checkpoint', (3, 3), (3, 3), True), Spec('waiting hall', (6, 7), (5, 6), True),
           Spec('throne room', (8, 9), (6, 7), True, shape='box'), Spec('private room', (4, 5), (4, 4), True),
           Spec('counting room', (4, 5), (3, 4), wing='clerks'), Spec('office', (3, 4), (3, 3), wing='clerks'), Spec('office', (3, 4), (3, 4), wing='clerks'),
           Spec('store', (3, 4), (3, 3), wing='clerks'), Spec('barracks', (4, 5), (3, 4), wing='guards'), Spec('washroom', (3, 3), (3, 3), wing='guards')]
    for _ in range(3):
        out.append(Spec('quarters', (3, 4), (3, 4), wing='petitioners'))
    return out


def _stores(rng):
    out = [Spec('entrance', (3, 4), (3, 4), True), Spec('checkpoint', (3, 3), (3, 3), True), Spec('mess', (6, 7), (5, 6), True),
           Spec('armoury', (3, 4), (3, 3), wing='guards'), Spec('barracks', (4, 5), (3, 4), wing='guards'), Spec('barracks', (4, 5), (3, 4), wing='guards'),
           Spec('washroom', (3, 3), (3, 3), wing='guards'), Spec('office', (3, 3), (3, 4), True), Spec('workroom', (4, 5), (4, 5), wing='laundry')]
    for _ in range(4):
        out.append(Spec('store', (3, 5), (3, 4), wing='stores'))
    return out


def _quarters(rng):
    out = [Spec('entrance', (4, 4), (3, 4), True), Spec('checkpoint', (3, 3), (3, 3), True), Spec('rec room', (5, 6), (4, 5), True)]
    for k in range(11):
        out.append(Spec('barracks' if k < 3 else 'quarters', (3, 4), (3, 4), wing='guards' if k < 3 else ('east wing' if k % 2 else 'west wing'), stairs=k == 6))
    out += [Spec('washroom', (3, 3), (3, 3), wing='east wing'), Spec('washroom', (3, 3), (3, 3), wing='west wing'), Spec('store', (3, 3), (3, 3), True)]
    return out


def _kahuna(rng):
    return [Spec('entrance', (4, 4), (3, 4), True), Spec('checkpoint', (3, 3), (3, 3), True), Spec('checkpoint', (3, 3), (3, 3), True),
            Spec('rec room', (6, 7), (5, 6), True), Spec('private room', (5, 6), (4, 5), True),
            Spec('quarters', (4, 5), (4, 4), wing='suite'), Spec('washroom', (3, 3), (3, 3), wing='suite'), Spec('store', (3, 4), (3, 3), wing='suite'),
            Spec('office', (4, 4), (3, 4), wing='suite'), Spec('barracks', (4, 5), (3, 4), wing='guards'), Spec('quarters', (3, 4), (3, 4), wing='household'),
            Spec('quarters', (3, 4), (3, 4), wing='household'), Spec('mess', (4, 5), (4, 4), wing='household')]


GUARDS = {'like': ['Gomorrah03', 'TheTops02', 'Lucky38Lobby'], 'who': 'people', 'busy': 'usual', 'said': "the Kahuna's guards"}
FLOORS = {
    'court': {'label': 'The Court', 'program': _court, 'story': 'court', 'people': GUARDS},
    'stores': {'label': "The Court's Stores", 'program': _stores, 'story': 'court', 'kit': HF.BACK, 'like': HF.SERVICE_LIKE, 'people': GUARDS},
    'quarters': {'label': "The Court's Floor", 'program': _quarters, 'story': 'court', 'people': GUARDS},
    'kahuna': {'label': "The Kahuna's Floor", 'program': _kahuna, 'story': 'court', 'people': dict(GUARDS, busy='many')},
}
NAMES = {'court': {'entrance': 'gate room', 'checkpoint': 'guard post', 'waiting hall': 'waiting hall', 'throne room': 'throne room',
                   'private room': "the Kahuna's private room", 'counting room': 'counting room', 'office': "clerks' office"},
         'stores': {'entrance': 'stair head', 'checkpoint': 'guard post', 'mess': 'kitchens', 'store': 'granary', 'armoury': 'armoury',
                    'barracks': "guards' barracks", 'office': "quartermaster's office", 'workroom': 'laundry', 'washroom': 'washroom'},
         'quarters': {'entrance': 'lift lobby', 'checkpoint': 'guard post', 'rec room': 'lounge', 'barracks': "guards' rooms", 'quarters': "courtier's room",
                      'washroom': 'bathroom', 'store': 'linen room'},
         'kahuna': {'entrance': 'lift lobby', 'checkpoint': 'guard post', 'rec room': 'hall of gifts', 'private room': "the Kahuna's suite",
                    'quarters': "household's room", 'washroom': 'bathroom', 'store': 'strongroom', 'office': 'his study', 'barracks': "guards' room",
                    'mess': 'dining room'}}
LIFT_IN = {'court': ('private room',), 'stores': ('office', 'store'), 'quarters': ('store', 'rec room'), 'kahuna': ('private room',)}

# what the court keeps in each room (hotelfloors' scenes and finds, by what the room is for)
HF.STORIES['court'] = {'entrance': ('barricade',), 'checkpoint': ('barricade',), 'waiting hall': ('luggage', 'camp'), 'counting room': ('hoard', 'stall'),
                       'office': ('radio post', 'the note left'), 'private room': ('room service', 'hoard'), 'mess': ('kitchen', 'last meal'),
                       'store': ('hoard', 'hoard'), 'armoury': ('hoard', 'workshop'), 'barracks': ('bunks', 'bedroll'), 'rec room': ('still', 'room service'),
                       'quarters': ('luggage', 'room service', 'bedroll'), 'washroom': ('still',), 'throne room': ()}
for _p, _f in (('checkpoint', ('LootAmmoBoxGenericNV',)), ('counting room', ('GenericSafeFloor01', 'VLootBriefcase01Gen%02d')),
               ('private room', ('GenericSafeFloor01', 'VLootHotelDeskGen%02d')), ('armoury', ('LootAmmoBoxGenericLockNV', 'Footlocker01MilitaryNV')),
               ('barracks', ('Footlocker01MilitaryNV', 'VLootHotelWardrobeGen%02d')), ('waiting hall', ('VLootClothesSuitcase01Gen%02d',))):
    HF.FINDS.setdefault(_p, _f)


def _route(plan):
    """How far each owner is from the way in, by doorways and stairs: {owner: steps}."""
    graph = L._owner_graph(plan)
    far = {0: 0}
    todo = collections.deque([0])
    while todo:
        n = todo.popleft()
        for m in graph.get(n, ()):
            if m not in far:
                far[m] = far[n] + 1
                todo.append(m)
    return far


def _servants_way(ts, plan, rng):
    """A corridor round the first guard post: from a room before it to a room after it. Its owners, or [] if none fits."""
    far = _route(plan)
    posts = sorted((o['n'] for o in plan.rooms() if o['purpose'] == 'checkpoint'), key=lambda n: far.get(n, 99))
    if not posts:
        return []
    post = posts[0]
    before = [o['n'] for o in plan.rooms() if far.get(o['n'], 99) < far[post] and not o.get('tall')]
    after = [o['n'] for o in plan.rooms() if far.get(o['n'], 99) > far[post] and o['purpose'] not in ('checkpoint',) and not o.get('tall')]
    rng.shuffle(after)
    pl = kitplan.Planner(ts, rng, plan)
    # (on the level if it can be; if not, a servants' stair down and back up)
    for flights, a, b in [(f, a, b) for f in (False, True) for a in before for b in after[:8]]:
        if True:
            fam = pl._hall_between(a, b)
            if fam is None:
                continue
            mark = plan.mark()
            n0 = len(plan.owners)
            if pl.join(a, b, fam, flights=flights, cost=40) and kitplan.fill(ts, plan, 1, budget=120, big=False):
                new = list(range(n0, len(plan.owners)))
                for n in new:
                    plan.owners[n]['servants'] = True
                return new
            plan.back_to(mark)
    return []


def holds(plan, servants=()):
    """Does the fortress hold: with the servants' way left out, is every guard post, and the throne room, the only way to what
    lies beyond it on the main route? (Each main room past it, and the lift's room, is cut off when it's taken away.)"""
    graph = L._owner_graph(plan)
    keep = set(servants)
    sub = {n: {m for m in ms if m not in keep} for n, ms in graph.items() if n not in keep}
    sub = collections.defaultdict(set, sub)
    every = L._reach(sub, 0)
    far = {0: 0}
    todo = collections.deque([0])
    while todo:
        n = todo.popleft()
        for m in sub[n]:
            if m not in far:
                far[m] = far[n] + 1
                todo.append(m)
    main = [o['n'] for o in plan.rooms() if o.get('main')]
    for o in plan.rooms():
        if o['purpose'] not in ('checkpoint', 'throne room'):
            continue
        beyond = [n for n in main if far.get(n, -1) > far.get(o['n'], 0) and n != o['n']]
        cut = L._reach(sub, 0, without={o['n']})
        if any(n in cut for n in beyond):
            return False
    return len(every) > 1


def _doors_between(plan, items, a_side, b_side):
    """Doors hung in a doorway between an owner in a_side and one in b_side."""
    out = []
    for it in items:
        if it.what != 'door' or it.link is None:
            continue
        owners = {plan.cells.get(c) for c in it.link}
        if owners & a_side and owners & b_side:
            out.append(it)
    return out


def _fortify(plan, items, kind, servants):
    """The guard posts' far doors and the servants' way locked: {'gates': n, 'servants': n} doors locked, or None if a gate
    or the servants' way has no door to lock."""
    graph = L._owner_graph(plan)
    keep = set(servants)
    # (how far each owner is from the way in without the servants' way: the main route)
    far = {0: 0}
    todo = collections.deque([0])
    while todo:
        n = todo.popleft()
        for m in graph.get(n, ()):
            if m not in far and m not in keep:
                far[m] = far[n] + 1
                todo.append(m)
    gates = 0
    for o in plan.rooms():
        if o['purpose'] != 'checkpoint':
            continue
        n = o['n']
        on = {m for m in graph.get(n, ()) if far.get(m, -1) > far.get(n, 0) and m not in keep}
        doors = _doors_between(plan, items, {n}, on)
        if not doors:
            return None
        for d in doors:
            d.extra = L._lock(GATE[kind])
        gates += len(doors)
    locked = 0
    if servants:
        doors = _doors_between(plan, items, keep, set(range(len(plan.owners))) - keep)
        if not doors:
            return None
        for d in doors:
            d.extra = L._lock(SERVANTS[kind])
        locked = len(doors)
    for o in plan.rooms():
        if o['purpose'] == 'armoury':
            for d in _doors_between(plan, items, {o['n']}, set(range(len(plan.owners))) - {o['n']}):
                d.extra = L._lock(ARMOURY)
    return {'gates': gates, 'servants': locked}


def _throne(game, ts, plan, made, items, rng):
    """The Kahuna's chair at the far end of the throne room from the doors you come in by, torches either side. What stood
    there goes. True if it went in."""
    room = next((o for o in plan.rooms() if o['purpose'] == 'throne room'), None)
    if room is None:
        return False
    n = room['n']
    far = _route(plan)
    # (the doorway in: from the room nearer the way in)
    way = None
    for link in plan.links:
        a, b = tuple(link)
        if plan.cells.get(a) == n and plan.cells.get(b) != n and far.get(plan.cells.get(b), 99) < far[n]:
            way = (a, next(d for d in range(4) if (a[0] - b[0], a[1] - b[1]) == DX[d]))
        elif plan.cells.get(b) == n and plan.cells.get(a) != n and far.get(plan.cells.get(a), 99) < far[n]:
            way = (b, next(d for d in range(4) if (b[0] - a[0], b[1] - a[1]) == DX[d]))
    if way is None:
        return False
    door, d = way
    cells = [c for c in room['cells'] if c not in plan.air and c[2] == door[2]]
    reach = lambda c: (c[0] - door[0]) * DX[d][0] + (c[1] - door[1]) * DX[d][1]
    side = lambda c: abs((c[0] - door[0]) * DX[d][1]) + abs((c[1] - door[1]) * DX[d][0])
    back = max(reach(c) for c in cells)
    row = sorted((c for c in cells if reach(c) == back and plan.need(c)[d] in 'cx' and 'p' not in plan.need(c)), key=side)
    pieces = {m.cell: m for m in made if len(m.cells) == 1}
    things = L.things_of(game)
    for c in row:
        if c not in pieces:
            continue
        got = L._lay_scene(things, ts, plan, pieces[c], c, d, THRONE, rng)
        if not got or game.describe(game.from_key(got[0].key))[1] != 'Throne01':
            continue
        cx, cy = c[0] * ts.step, c[1] * ts.step
        items[:] = [it for it in items if it.what in ('door', 'exit', 'light') or abs(it.p[0] - cx) > ts.step * 0.75 or abs(it.p[1] - cy) > ts.step * 0.75]
        items += got
        room['throne'] = c
        return True
    return False


def build_floor(gd, hotel, kind, n, seed, last=False):
    """One floor of the court, planned as a fortress, built, walked, dressed, fortified: hotelfloors.Floor. ValueError when no
    seed of TRIES walks."""
    H = HF.HOTELS[hotel]
    F = FLOORS[kind]
    ks, survey, store, cache = HF.kits(gd)
    kit = F.get('kit') or H['kit']
    ts = kitplan.tiles_for(gd, ks, kit, store, survey)
    sv = survey.get(kit)
    lift_key = HF._lift_key(gd)
    why = collections.Counter()
    for k in range(TRIES):
        s = seed * 7919 + n * 104729 + k * 271 + 7
        rng = random.Random(s)
        plan = kitplan.make_plan(ts, F['program'](rng), s, None, stairs=0, with_exit=True, loops=0)    # (a floor of a court is one floor: no stairs)
        if not plan.exit:
            why['no way in'] += 1
            continue
        servants = _servants_way(ts, plan, rng)
        if not holds(plan, servants):
            why['a way round a guard post'] += 1
            continue
        if not servants:
            why['no servants\' way'] += 1
            continue
        made = next((m for m in (kitplan.fill(ts, plan, s + f * 31) for f in range(3)) if m), None)
        if not made:
            why['no pieces fit'] += 1
            continue
        walk = kitplan.walk_check(gd, ts, plan, made, cache)
        if walk['missing'] or walk['escaped'] or walk['edges']:
            why['didn\'t walk'] += 1
            continue
        items, walk = kitplan.dress_place(gd, ts, sv, plan, made, rng, cache)
        if walk['missing'] or walk['escaped']:
            why['things in the way'] += 1
            continue
        items = HF._own_files(gd, made, list(items))
        if not any(it.what == 'exit' for it in items):
            why['no way in'] += 1
            continue
        if kind == 'court' and not _throne(gd, ts, plan, made, items, rng):
            why['no wall for the throne'] += 1
            continue
        saved = HF.LIFT_IN.get(AS[kind])
        HF.LIFT_IN[AS[kind]] = LIFT_IN[kind]
        try:
            got = HF._put_lift(gd, ts, plan, made, items, rng, lift_key, {plan.exit[0]}, AS[kind])
        finally:
            HF.LIFT_IN[AS[kind]] = saved
        if not got or plan.owners[got[0].owner]['purpose'] not in LIFT_IN[kind]:
            why['no wall for the lift'] += 1
            continue
        lift = got[0]
        HF._life(gd, ts, plan, made, items, rng, F['story'], HF.TIERS[AS[kind]])
        D.keep_fronts(ts, plan, items)
        walk = D.clear_ways(gd, ts, plan, made, items, kitplan.walk_check, cache)
        if walk['missing'] or walk['escaped'] or lift not in items or kind == 'court' and not any(gd.describe(gd.from_key(it.key))[1] == 'Throne01' for it in items if not it.key.startswith('$')):
            why['things in the way'] += 1
            continue
        fort = _fortify(plan, items, kind, servants)
        if fort is None:
            why['a gate with no door'] += 1
            continue
        HF._secure(gd, ts, plan, items, rng, AS[kind], '$hf_%s_key' % hotel if last else None, lift)
        items[:] = HF.no_twins(items, keep=lift)
        names = NAMES[kind]
        rooms = collections.Counter(names.get(o['purpose'], o['purpose']) for o in plan.rooms())
        kinds = collections.Counter(it.what for it in items)
        far = _route(plan)
        route = [names.get(o['purpose'], o['purpose']) for o in sorted((o for o in plan.rooms() if o.get('main')), key=lambda o: far.get(o['n'], 99))]
        rep = {'kind': kind, 'kit': kit, 'seed': s, 'rooms': sorted(rooms.items()), 'route': route, 'levels': len({c[2] for c in plan.squares()}),
               'pieces': len(made), 'things': len(items), 'doors': kinds['door'], 'lights': kinds['light'], 'finds': len(plan.finds),
               'gates locked': fort['gates'], 'servants\' way doors': fort['servants'], 'locked rooms': plan.locks['rooms'],
               'locked finds': plan.locks['finds'], 'key in': plan.locks['key'], 'tries': k + 1, 'loops': 0,
               'walk': {'squares': walk['squares'], 'missing': len(walk['missing']), 'escaped': len(walk['escaped'])}}
        return HF.Floor(kind, kit, ts, {'plan': plan, 'made': made, 'items': items}, got, rep)
    raise ValueError('The court, %s: no floor walked in %d tries (%s).' % (F['label'], TRIES, ', '.join('%s %d' % w for w in why.most_common())))


def make(gd, pr, seed=1):
    """The Royal Hawaiian's floors as the court: hotelfloors.make's answer."""
    return HF.make(gd, pr, HOTEL, seed, concept=__import__('hotelcourt'))
