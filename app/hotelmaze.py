"""The Kilauea's floors as a labyrinth (docs/waikiki-hotel-interiors.md): the tower nobody holds, its floors gone to wreck and
patched across, the way up a hunt. hotelcourt's opposite: as many ways round as the kit will take (`LOOPS`), stairs
inside a floor so you lose track of the level you're on (`STAIRS`), rooms of odd shapes, a share of them wrecked, side
corridors that end at a locked room. The lift up is in the room farthest from the way in by the shortest walk, and the
top floor's on a key that lies somewhere on it.

    make(gd, pr, seed)      as hotelfloors.make(gd, pr, 'kilauea', seed), the floors built as the labyrinth
    build_floor(gd, hotel, kind, n, seed, last)     one floor: hotelfloors.Floor"""
import collections
import random

import hotelcourt as HC
import hotelfloors as HF
import kitdress as D
import kitplan
from kitplan import Spec

HOTEL = 'kilauea'
KINDS = ('maze', 'maze', 'maze', 'top')
AS = {'maze': 'guest', 'top': 'top'}
LOOPS = 6
STAIRS = 0.55
WRECKED = 0.3
TRIES = 14
KIT = HF.HIGH       # (not the Kilauea's own Lucky 38 kit: it has no corridors FOLab can read, so no ways round and no stairs)
CRAWLERS = {'like': ['NellisTunnel', 'RocketLabMid', 'OVWestSewers02b'], 'who': 'creatures', 'busy': 'usual', 'said': 'feral ghouls'}


def _maze(rng, more=0):
    out = [Spec('entrance', (4, 4), (3, 4), True), Spec('rec room', (5, 6), (4, 5), True)]
    for k in range(12 + more):
        out.append(Spec('quarters' if k % 4 else 'store', (3, 5), (3, 5), wing=('north', 'south', 'east', 'west')[k % 4], stairs=k % 5 == 2))
    out += [Spec('washroom', (3, 3), (3, 3), wing='north'), Spec('office', (4, 5), (3, 4), True), Spec('mess', (4, 6), (4, 5), wing='east')]
    return out


def _top(rng):
    return _maze(rng, 2) + [Spec('private room', (5, 6), (4, 5), True)]


FLOORS = {'maze': {'label': 'The Fallen Floors', 'program': _maze, 'story': 'rats', 'people': CRAWLERS},
          'top': {'label': 'The Top Floor', 'program': _top, 'story': 'quiet', 'people': CRAWLERS}}
NAMES = {'entrance': 'lift lobby', 'rec room': 'lounge', 'quarters': 'guest room', 'store': 'linen room', 'washroom': 'bathroom',
         'office': "floor manager's office", 'mess': 'room service kitchen', 'private room': 'the penthouse suite'}
LIFT_IN = {'maze': ('office', 'store'), 'top': ('private room', 'office')}


def build_floor(gd, hotel, kind, n, seed, last=False):
    """One floor of the labyrinth: hotelfloors.Floor. ValueError when no seed of TRIES walks."""
    H = HF.HOTELS[hotel]
    F = FLOORS[kind]
    ks, survey, store, cache = HF.kits(gd)
    kit = KIT
    ts = kitplan.tiles_for(gd, ks, kit, store, survey)
    sv = survey.get(kit)
    lift_key = HF._lift_key(gd)
    why = collections.Counter()
    for k in range(TRIES):
        s = seed * 7919 + n * 104729 + k * 271 + 11
        rng = random.Random(s)
        plan = kitplan.make_plan(ts, F['program'](rng), s, None, stairs=STAIRS, with_exit=True, loops=LOOPS)
        if not plan.exit:
            why['no way in'] += 1
            continue
        made = next((m for m in (kitplan.fill(ts, plan, s + f * 31) for f in range(3)) if m), None)
        if not made:
            why['no pieces fit'] += 1
            continue
        walk = kitplan.walk_check(gd, ts, plan, made, cache)
        if walk['missing'] or walk['escaped'] or walk['edges']:
            why['didn\'t walk'] += 1
            continue
        for o in plan.rooms():
            if o['n'] and rng.random() < WRECKED:
                o['wrecked'] = True
        items, walk = kitplan.dress_place(gd, ts, sv, plan, made, rng, cache, ruined=True)
        if walk['missing'] or walk['escaped']:
            why['things in the way'] += 1
            continue
        items = HF._own_files(gd, made, list(items))
        if not any(it.what == 'exit' for it in items):
            why['no way in'] += 1
            continue
        saved = HF.LIFT_IN.get(AS[kind])
        HF.LIFT_IN[AS[kind]] = LIFT_IN[kind]
        try:
            got = HF._put_lift(gd, ts, plan, made, items, rng, lift_key, {plan.exit[0]}, AS[kind])
        finally:
            HF.LIFT_IN[AS[kind]] = saved
        if not got:
            why['no wall for the lift'] += 1
            continue
        lift = got[0]
        HF._life(gd, ts, plan, made, items, rng, F['story'], HF.TIERS[AS[kind]])
        D.keep_fronts(ts, plan, items)
        walk = D.clear_ways(gd, ts, plan, made, items, kitplan.walk_check, cache)
        if walk['missing'] or walk['escaped'] or lift not in items:
            why['things in the way'] += 1
            continue
        HF._secure(gd, ts, plan, items, rng, AS[kind], '$hf_%s_key' % hotel if last else None, lift)
        items[:] = HF.no_twins(items, keep=lift)
        far = HC._route(plan)
        rooms = collections.Counter(NAMES.get(o['purpose'], o['purpose']) for o in plan.rooms())
        kinds = collections.Counter(it.what for it in items)
        rep = {'kind': kind, 'kit': kit, 'seed': s, 'rooms': sorted(rooms.items()), 'route': ['%d rooms deep to the lift' % far.get(lift.owner, -1)],
               'levels': len({c[2] for c in plan.squares()}), 'pieces': len(made), 'things': len(items), 'doors': kinds['door'],
               'lights': kinds['light'], 'finds': len(plan.finds), 'gates locked': 0, 'servants\' way doors': 0, 'loops': plan.loops,
               'wrecked': sum(1 for o in plan.rooms() if o.get('wrecked')), 'stairs': len(plan.flights),
               'locked rooms': plan.locks['rooms'], 'locked finds': plan.locks['finds'], 'key in': plan.locks['key'], 'tries': k + 1,
               'walk': {'squares': walk['squares'], 'missing': len(walk['missing']), 'escaped': len(walk['escaped'])}}
        return HF.Floor(kind, kit, ts, {'plan': plan, 'made': made, 'items': items}, got, rep)
    raise ValueError('The labyrinth, %s: no floor walked in %d tries (%s).' % (F['label'], TRIES, ', '.join('%s %d' % w for w in why.most_common())))


def make(gd, pr, seed=1):
    """The Kilauea's floors as the labyrinth: hotelfloors.make's answer."""
    return HF.make(gd, pr, HOTEL, seed, concept=__import__('hotelmaze'))
