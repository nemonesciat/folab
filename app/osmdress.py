"""Things on the ground, by what the map says the ground is (osmcover.MapCover): palms on the beach and in the parks,
wrecked cars and dumpsters on paved lots, hulks on the roads, junk in the yards, rocks and brush on scrub; and along the
roads the things that stand at a street's edge: lights, poles, signs, palms. All of it the game's own objects, by editor
ID; one the game doesn't have is left out. Returned as ops, to go in as one Undo.

Nothing is put inside a building's plot, on a road that isn't meant for it, or under water (but for the sea bed's own)."""
import math
import random

import roadgen

# kind of ground: (how many to a cell of nothing but that ground, [(editor ID, how often, smallest size, biggest size, sunk by)])
GROUND = {
    'sand': (2.5, [('NVQueenPalm01', 6, 0.9, 1.3, 4), ('NVDatePalm01', 3, 0.9, 1.2, 4), ('NVDatePalm02', 2, 0.9, 1.2, 4), ('NVDatePalm03', 2, 0.9, 1.2, 4),
                   ('NVSagoPalm01', 2, 0.8, 1.2, 2), ('umbrellaNV', 1, 1.0, 1.0, 0), ('Boat03a', 1, 1.0, 1.0, 6), ('Boat03b', 1, 1.0, 1.0, 6),
                   ('Tire01Static', 1, 1.0, 1.0, 2)]),
    'grass': (5.0, [('NVQueenPalm01', 6, 0.9, 1.4, 4), ('NVDatePalm01', 3, 0.9, 1.3, 4), ('NVDatePalm02', 3, 0.9, 1.3, 4), ('NVDatePalm03', 2, 0.9, 1.3, 4),
                    ('NVSagoPalm01', 3, 0.8, 1.3, 2), ('NVSagoPalm02', 3, 0.8, 1.3, 2), ('EuonymusBush01', 4, 0.8, 1.3, 2), ('BenchUrban01', 1, 1.0, 1.0, 0),
                    ('Bench01', 1, 1.0, 1.0, 0), ('CementPlanterRd01', 1, 1.0, 1.0, 0)]),
    'golf': (1.5, [('NVQueenPalm01', 4, 1.0, 1.4, 4), ('NVSagoPalm01', 2, 0.9, 1.2, 2), ('EuonymusBush01', 2, 0.9, 1.3, 2)]),
    'yard': (6.0, [('NVSagoPalm01', 3, 0.8, 1.2, 2), ('NVSagoPalm02', 3, 0.8, 1.2, 2), ('EuonymusBush01', 4, 0.7, 1.2, 2), ('NVDatePalm01', 2, 0.9, 1.2, 4),
                   ('Tire01Static', 2, 1.0, 1.0, 2), ('TirePile01', 1, 1.0, 1.0, 2), ('MailboxDestroyed', 2, 1.0, 1.0, 0), ('Barrel01', 2, 1.0, 1.0, 0),
                   ('CrateGenericNV', 1, 1.0, 1.0, 0), ('SuburbanRubblePileSm01', 2, 0.7, 1.1, 4), ('ShoppingCart01', 1, 1.0, 1.0, 0), ('TricycleDirty01', 1, 1.0, 1.0, 0),
                   ('GrillBBQDirty', 1, 1.0, 1.0, 0), ('dlc04lawnchair01', 2, 1.0, 1.0, 0), ('VBitterSpringsClotheslineShort', 1, 1.0, 1.0, 0),
                   ('Car01HulkBodyStatic', 1, 1.0, 1.0, 2), ('BedMattress01Static', 1, 1.0, 1.0, 0)]),
    'paved': (9.0, [('Car01HulkBodyStatic', 5, 1.0, 1.0, 2), ('Car03HulkBodyStatic', 5, 1.0, 1.0, 2), ('Car03A', 1, 1.0, 1.0, 2), ('Dumpster02', 3, 1.0, 1.0, 0),
                    ('ShoppingCart01', 2, 1.0, 1.0, 0), ('Barrier03', 2, 1.0, 1.0, 0), ('RubblePile02', 2, 0.6, 1.0, 6), ('IndRubblePileSm01', 2, 0.7, 1.1, 4),
                    ('Planter01', 2, 1.0, 1.0, 0), ('Planter02', 1, 1.0, 1.0, 0), ('NVStripPlanter03', 1, 1.0, 1.0, 0), ('TireStack01', 1, 1.0, 1.0, 0),
                    ('Barrel01', 2, 1.0, 1.0, 0), ('CrateLarge01', 1, 1.0, 1.0, 0), ('FireHydrant01', 1, 1.0, 1.0, 0), ('NVTruck', 1, 1.0, 1.0, 2),
                    ('JerseyBarricade01', 2, 1.0, 1.0, 0), ('JerseyBarricade03', 1, 1.0, 1.0, 0), ('BenchUrban01', 2, 1.0, 1.0, 0),
                    ('NukaVendingMachineSTATIC', 1, 1.0, 1.0, 0), ('Tire01Static', 2, 1.0, 1.0, 2), ('SWSingleRubble', 2, 0.7, 1.1, 2)]),
    'asphalt': (2.2, [('Car01HulkBodyStatic', 6, 1.0, 1.0, 2), ('Car03HulkBodyStatic', 6, 1.0, 1.0, 2), ('Car03A', 1, 1.0, 1.0, 2), ('BusHulkFrontStatic01', 1, 1.0, 1.0, 2),
                      ('truckarmy02Static', 1, 1.0, 1.0, 2), ('Barrier03', 2, 1.0, 1.0, 0), ('Tire02Static', 2, 1.0, 1.0, 2), ('NVTruck', 1, 1.0, 1.0, 2), ('JerseyBarricade02', 1, 1.0, 1.0, 0),
                      ('SWSingleRubble', 2, 0.6, 1.0, 2), ('ShoppingCart01', 1, 1.0, 1.0, 0)]),
    'scrub': (5.0, [('NVNRockCanyon06', 2, 0.25, 0.7, 30), ('NVNRockCanyon12', 2, 0.25, 0.7, 30), ('NVNRockCanyon13', 2, 0.25, 0.7, 30), ('CreosoteBushSm', 6, 0.8, 1.3, 2),
                    ('CreosoteBushLg', 3, 0.8, 1.2, 2), ('pricklypearcactus02', 2, 0.8, 1.2, 2), ('NVbarrelcactus02', 2, 0.8, 1.2, 2)]),
    'trees': (6.0, [('NVQueenPalm01', 5, 0.9, 1.4, 4), ('NVDatePalm01', 3, 0.9, 1.3, 4), ('EuonymusBush01', 4, 0.8, 1.3, 2), ('CreosoteBushLg', 3, 0.8, 1.2, 2)]),
    'seabed': (0.25, [('UnderwaterRockCanyon12NV', 4, 0.3, 0.8, 30), ('Boat03c', 1, 1.0, 1.0, 10), ('Tire01Static', 1, 1.0, 1.0, 2)]),
}
SEA_DEEP = -400.0           # nothing on the sea bed lower than this: nobody goes there
# road class: [(editor ID, how far apart along the road, which side each one takes: 'both', 'turns' (left, right, left...) or 'one')]
STREET = {
    'major': [('StreetLight01', 2600.0, 'turns'), ('NVQueenPalm01', 1700.0, 'both'), ('FireHydrant01', 7000.0, 'one'), ('NVBusBench01', 9000.0, 'one'),
              ('SignNoParking01', 6000.0, 'one'), ('BusShelter01', 13000.0, 'one'), ('UtilityPoleWSingle01', 3400.0, 'one'),
              ('Dumpster02', 11000.0, 'turns'), ('MailboxDestroyed', 8000.0, 'turns')],
    'minor': [('UtilityPoleWSingle01', 3200.0, 'one'), ('StreetLight03', 4200.0, 'turns'), ('SignStop01', 12000.0, 'one'), ('MailboxDestroyed', 5000.0, 'turns'),
              ('NVSagoPalm01', 3800.0, 'turns'), ('FireHydrant01', 9000.0, 'one'), ('Tire01Static', 7000.0, 'turns')],
}
# on the road itself, off its middle so there's a way past: road class: (how far apart, [(editor ID, how often, sunk by)])
ON_ROAD = {
    'major': (1500.0, [('Car01HulkBodyStatic', 6, 2), ('Car03HulkBodyStatic', 6, 2), ('Car03A', 2, 2), ('NVTruck', 2, 2), ('BusHulkFrontStatic01', 1, 2),
                       ('truckarmy02Static', 1, 2), ('SWSingleRubble', 2, 2), ('Tire02Static', 1, 2), ('ShoppingCart01', 1, 0), ('JerseyBarricade02', 1, 0)]),
    'minor': (2400.0, [('Car01HulkBodyStatic', 6, 2), ('Car03HulkBodyStatic', 6, 2), ('Car03A', 1, 2), ('NVTruck', 1, 2), ('SWSingleRubble', 2, 2),
                       ('Tire01Static', 2, 2), ('TricycleDirty01', 1, 0), ('Barrel01', 1, 0)]),
}
ROAD_LIMIT = 5000
EDGE = {'major': 420.0, 'minor': 300.0}      # how far from a road's middle its edge things stand
STREET_LIMIT = 9000
GROUND_LIMIT = 26000


def _bases(gd):
    """{editor ID lowered: form key} for everything named above that the game has."""
    want = {e.lower() for e in _named()}
    out = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag in ('STAT', 'MSTT', 'SCOL', 'TREE', 'FURN', 'ACTI', 'CONT'):
            e = gd.edid(f).lower()
            if e in want:
                out[e] = gd.key(f)
    return out


def ops(gd, pr, world, cover, roads, seed=1, progress=None):
    """(ops, report). cover: the osmcover.MapCover of this world; roads: [{'line': [(x, y)...], 'class'}] in game units (osmplace.layout)."""
    import osmcover
    rng = random.Random(seed)
    bases = _bases(gd)
    grid = gd.grid(world)
    ground = roadgen.Ground(gd, pr, world)
    A, D, kinds = cover.A, cover.D, cover.kind
    gx0, gy0 = cover.gx0, cover.gy0
    blocked = cover.built
    out, counts = [], {}

    def kind_at(x, y):
        gx, gy = int(round(x / 128.0)) - gx0, int(round(y / 128.0)) - gy0
        if not (0 <= gx < A and 0 <= gy < D):
            return None, True
        s = gy * A + gx
        return (osmcover.ORDER[kinds[s] - 1] if kinds[s] else None), bool(blocked[s])

    def put(edid, x, y, yaw, scale, sink, what):
        key = bases.get(edid.lower())
        cell = grid.get((int(x // 4096), int(y // 4096)))
        if key is None or cell is None:
            return False
        z = ground.at(x, y)
        if z is None:
            return False
        out.append({'op': 'add', 'cell': gd.key(cell), 'base': key, 'p': [round(x, 1), round(y, 1), round(z - sink * scale, 1), 0.0, 0.0, round(yaw, 3)], 's': round(scale, 3)})
        counts[what] = counts.get(what, 0) + 1
        return True

    # along the streets
    for n, road in enumerate(roads):
        rows = STREET.get(road.get('class'))
        if not rows or len(out) >= STREET_LIMIT:
            continue
        if progress and n % 200 == 0:
            progress('Dressing the streets', n, len(roads))
        line = road['line']
        off = EDGE[road['class']]
        for edid, every, sides in rows:
            if edid.lower() not in bases:
                continue
            at = rng.uniform(0.2, 0.8) * every
            turn = 1
            walked = 0.0
            for (ax, ay), (bx, by) in zip(line, line[1:]):
                L = math.hypot(bx - ax, by - ay)
                if L < 1:
                    continue
                dx, dy = (bx - ax) / L, (by - ay) / L
                while at <= walked + L:
                    t = at - walked
                    for side in ((1, -1) if sides == 'both' else (turn,)):
                        x, y = ax + dx * t - dy * off * side, ay + dy * t + dx * off * side
                        k, hit = kind_at(x, y)
                        if not hit and k not in ('asphalt', 'seabed', None):
                            put(edid, x, y, math.atan2(dx, dy) + (math.pi if side < 0 else 0.0), 1.0, 0, 'Along the streets')
                    if sides == 'turns':
                        turn = -turn
                    at += every * rng.uniform(0.85, 1.15)
                walked += L
    # and on them
    on_road = 0
    for n, road in enumerate(roads):
        every, items = ON_ROAD.get(road.get('class'), (0, ()))
        have = [i for i in items if i[0].lower() in bases]
        if not have or on_road >= ROAD_LIMIT:
            continue
        line = road['line']
        off = EDGE[road['class']]
        at, walked = rng.uniform(0.2, 1.0) * every, 0.0
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            L = math.hypot(bx - ax, by - ay)
            if L < 1:
                continue
            dx, dy = (bx - ax) / L, (by - ay) / L
            while at <= walked + L:
                t = at - walked
                at += every * rng.uniform(0.5, 1.5)
                side = rng.choice((-1, 1)) * rng.uniform(0.25, 0.7) * off
                x, y = ax + dx * t - dy * side, ay + dy * t + dx * side
                k, _hit = kind_at(x, y)
                if k != 'asphalt':
                    continue
                pick = rng.random() * sum(i[1] for i in have)
                for edid, w, sink in have:
                    pick -= w
                    if pick <= 0:
                        break
                # (as it was driving, or slewed)
                yaw = math.atan2(dx, dy) + (math.pi if side < 0 else 0.0) + (rng.uniform(-0.25, 0.25) if rng.random() < 0.7 else rng.uniform(0, math.tau))
                on_road += put(edid, x, y, yaw, 1.0, sink, 'On the roads')
            walked += L
    street = len(out)
    # on the ground itself
    top = max(d for d, _i in GROUND.values())
    cells = sorted(grid)
    for n, (cx, cy) in enumerate(cells):
        if len(out) - street >= GROUND_LIMIT:
            break
        if progress and n % 64 == 0:
            progress('Putting things on the ground', n, len(cells))
        tries = int(top) + (rng.random() < top - int(top))
        for _ in range(tries):
            x, y = (cx + rng.random()) * 4096.0, (cy + rng.random()) * 4096.0
            k, hit = kind_at(x, y)
            if hit or k not in GROUND:
                continue
            density, items = GROUND[k]
            if rng.random() > density / top:
                continue
            if k == 'seabed' and (ground.at(x, y) or 0.0) < SEA_DEEP:
                continue
            have = [i for i in items if i[0].lower() in bases]
            if not have:
                continue
            pick = rng.random() * sum(i[1] for i in have)
            for edid, w, smin, smax, sink in have:
                pick -= w
                if pick <= 0:
                    break
            label = next(lab for kk, lab, _t in osmcover.KINDS if kk == k)
            put(edid, x, y, rng.uniform(0, math.tau), rng.uniform(smin, smax), sink, label)
    return out, {'things': len(out), 'by': counts, 'missing': sorted(e for e in _named() if e.lower() not in bases)}


# ---------- what a building was for ----------

# where round a building: 'front' (the side its door is on), 'back', 'side'; along that side from -1 to 1 of its half length;
# how far out from the wall; which way it faces: 'out' (its front away from the wall), 'along', 'any'
# family: [(editor ID, chance, where, (along from, to), (out from, to), facing)]
LIFE = {
    'shop': [('NukaVendingMachineSTATIC', 0.45, 'front', (-0.9, -0.5), (30, 40), 'out'), ('ssVendingMachineSolid', 0.25, 'front', (0.5, 0.9), (30, 40), 'out'),
             ('BenchUrban01', 0.4, 'front', (0.3, 0.8), (50, 70), 'out'), ('ShoppingCart01', 0.5, 'front', (-0.8, 0.8), (150, 400), 'any'),
             ('ShoppingCart01', 0.3, 'front', (-0.8, 0.8), (150, 500), 'any'), ('Planter01', 0.3, 'front', (-1.0, -0.8), (60, 90), 'out'),
             ('Dumpster02', 0.6, 'back', (-0.7, 0.7), (90, 140), 'out'), ('CrateGenericNV', 0.4, 'back', (-0.8, 0.8), (60, 160), 'any'),
             ('Car03HulkBodyStatic', 0.45, 'front', (-0.9, 0.9), (420, 620), 'along'), ('Car01HulkBodyStatic', 0.3, 'side', (-0.6, 0.6), (220, 320), 'out'),
             ('MailboxDestroyed', 0.25, 'front', (0.8, 1.0), (200, 300), 'out'), ('Tire01Static', 0.3, 'side', (-0.8, 0.8), (40, 120), 'any')],
    'house': [('MailboxDestroyed', 0.5, 'front', (0.6, 1.0), (300, 420), 'out'), ('TricycleDirty01', 0.2, 'front', (-0.8, 0.8), (100, 300), 'any'),
              ('dlc04lawnchair01', 0.35, 'front', (-0.7, 0.7), (80, 200), 'out'), ('GrillBBQDirty', 0.3, 'back', (-0.7, 0.7), (100, 260), 'any'),
              ('dlc04lawnchair01', 0.3, 'back', (-0.7, 0.7), (120, 300), 'any'), ('VBitterSpringsClotheslineShort', 0.3, 'back', (-0.6, 0.6), (220, 380), 'along'),
              ('SwingsRuined01', 0.12, 'back', (-0.5, 0.5), (300, 460), 'along'), ('Car01HulkBodyStatic', 0.35, 'side', (-0.5, 0.5), (200, 300), 'out'),
              ('EuonymusBush01', 0.5, 'front', (-1.0, -0.4), (50, 90), 'any'), ('EuonymusBush01', 0.4, 'front', (0.4, 1.0), (50, 90), 'any'),
              ('Barrel01', 0.3, 'side', (-0.9, 0.9), (40, 90), 'any'), ('Tire01Static', 0.25, 'back', (-0.9, 0.9), (60, 200), 'any'),
              ('BedMattress01Static', 0.12, 'side', (-0.8, 0.8), (60, 160), 'any'), ('NVSagoPalm01', 0.35, 'front', (-1.0, 1.0), (140, 300), 'any')],
    'apartments': [('NVQueenPalm01', 0.6, 'front', (-0.75, -0.55), (160, 220), 'any'), ('NVQueenPalm01', 0.6, 'front', (0.55, 0.75), (160, 220), 'any'),
                   ('BenchUrban01', 0.5, 'front', (-0.6, -0.3), (50, 70), 'out'), ('BenchUrban01', 0.3, 'front', (0.3, 0.6), (50, 70), 'out'),
                   ('Planter01', 0.5, 'front', (-0.95, -0.8), (60, 90), 'out'), ('Planter02', 0.5, 'front', (0.8, 0.95), (60, 90), 'out'),
                   ('NVStripPlanter03', 0.3, 'front', (-0.4, 0.4), (260, 340), 'along'), ('FlagPole', 0.35, 'front', (-0.9, 0.9), (240, 360), 'out'),
                   ('umbrellaNV', 0.35, 'side', (-0.6, 0.6), (160, 320), 'any'), ('dlc04lawnchair01', 0.4, 'side', (-0.6, 0.6), (140, 340), 'any'),
                   ('dlc04lawnchair01', 0.3, 'side', (-0.6, 0.6), (140, 340), 'any'), ('Car03HulkBodyStatic', 0.5, 'front', (-0.9, 0.9), (460, 680), 'along'),
                   ('Car01HulkBodyStatic', 0.4, 'front', (-0.9, 0.9), (460, 680), 'along'), ('Dumpster02', 0.5, 'back', (-0.7, 0.7), (90, 140), 'out'),
                   ('NukaVendingMachineSTATIC', 0.3, 'front', (0.6, 0.9), (30, 40), 'out'), ('CementPlanterRd01', 0.3, 'front', (-0.3, 0.3), (320, 420), 'any')],
    'civic': [('FlagPole', 0.8, 'front', (-0.6, 0.6), (260, 380), 'out'), ('Bench01', 0.5, 'front', (-0.8, -0.4), (50, 70), 'out'),
              ('Bench01', 0.4, 'front', (0.4, 0.8), (50, 70), 'out'), ('CementPlanterRd01', 0.5, 'front', (-0.9, -0.6), (200, 300), 'any'),
              ('CementPlanterRd01', 0.5, 'front', (0.6, 0.9), (200, 300), 'any'), ('JerseyBarricade01', 0.4, 'front', (-0.8, 0.8), (420, 520), 'along'),
              ('SandbagStraight', 0.35, 'front', (-0.5, 0.5), (330, 400), 'along'), ('truckarmy02Static', 0.3, 'side', (-0.5, 0.5), (260, 360), 'out'),
              ('NVQueenPalm01', 0.5, 'side', (-0.8, 0.8), (160, 260), 'any'), ('Dumpster02', 0.4, 'back', (-0.7, 0.7), (90, 140), 'out')],
    'industrial': [('CrateLarge01', 0.6, 'front', (-0.9, 0.9), (80, 240), 'any'), ('CrateLarge01', 0.4, 'side', (-0.9, 0.9), (60, 200), 'any'),
                   ('CrateGenericNV', 0.5, 'front', (-0.9, 0.9), (60, 220), 'any'), ('Barrel01', 0.6, 'side', (-0.9, 0.9), (40, 100), 'any'),
                   ('Barrel01', 0.5, 'side', (-0.9, 0.9), (40, 120), 'any'), ('TireStack01', 0.4, 'side', (-0.9, 0.9), (50, 120), 'any'),
                   ('Dumpster02', 0.5, 'back', (-0.7, 0.7), (90, 140), 'out'), ('NVTruck', 0.35, 'front', (-0.7, 0.7), (380, 560), 'out'),
                   ('truckarmy02Static', 0.2, 'side', (-0.5, 0.5), (280, 380), 'out'), ('IndRubblePileSm01', 0.35, 'back', (-0.8, 0.8), (80, 220), 'any'),
                   ('TirePile01', 0.3, 'back', (-0.8, 0.8), (100, 260), 'any')],
}
# and by a word in the building's own editor ID, on top of its family's
LIFE_WORD = (
    (('diner', 'saloon'), [('dinertable04NV', 0.7, 'front', (-0.8, -0.3), (160, 260), 'any'), ('dinertable04NV', 0.6, 'front', (0.3, 0.8), (160, 260), 'any'),
                           ('DinerStool01L', 0.6, 'front', (-0.8, -0.3), (270, 320), 'any'), ('DinerStool01L', 0.6, 'front', (0.3, 0.8), (270, 320), 'any'),
                           ('umbrellaNV', 0.6, 'front', (-0.6, 0.6), (200, 300), 'any'), ('NukaVendingMachineSTATIC', 0.8, 'front', (0.6, 0.9), (30, 40), 'out')]),
    (('gasstation', 'garage'), [('TireStack01', 0.8, 'side', (-0.8, 0.8), (50, 110), 'any'), ('TirePile01', 0.6, 'back', (-0.7, 0.7), (100, 220), 'any'),
                                ('Barrel01', 0.8, 'front', (-0.9, -0.6), (50, 110), 'any'), ('Car03HulkBodyStatic', 0.8, 'front', (-0.5, 0.5), (360, 480), 'along'),
                                ('NVTruck', 0.4, 'side', (-0.4, 0.4), (300, 400), 'out'), ('Tire01Static', 0.7, 'front', (-0.9, 0.9), (60, 200), 'any'),
                                ('NukaVendingMachineSTATIC', 0.7, 'front', (0.6, 0.9), (30, 40), 'out')]),
    (('motel', 'hotel', 'casino'), [('umbrellaNV', 0.7, 'front', (-0.8, 0.8), (240, 400), 'any'), ('dlc04lawnchair01', 0.7, 'front', (-0.8, 0.8), (220, 420), 'any'),
                                    ('dlc04lawnchair01', 0.6, 'front', (-0.8, 0.8), (220, 420), 'any'), ('NVDatePalm01', 0.6, 'side', (-0.8, 0.8), (160, 260), 'any'),
                                    ('Skeleton50sCasualMale', 0.12, 'front', (-0.8, 0.8), (230, 400), 'any')]),
    (('shack', 'trailer', 'mobilehome'), [('CampfireCrafting03', 0.25, 'front', (-0.5, 0.5), (260, 380), 'any'), ('NVBedrollL', 0.2, 'front', (-0.5, 0.5), (160, 250), 'any'),
                                          ('TireStack01', 0.3, 'side', (-0.8, 0.8), (50, 110), 'any'), ('CrateGenericNV', 0.4, 'side', (-0.8, 0.8), (50, 130), 'any')]),
    (('church', 'school', 'police', 'fire'), [('Skeleton50sCasualFemale', 0.1, 'front', (-0.6, 0.6), (120, 300), 'any'), ('SandbagStraight', 0.4, 'front', (-0.6, 0.6), (300, 380), 'along')]),
)
ROOM = 110.0                # (two things round one building stand at least this far apart)
LIFE_LIMIT = 14000

# ---------- places someone stopped at ----------

# a scene: things round a middle, each (editor ID, how many, nearest, furthest from the middle, facing: 'in' the middle, 'out', 'any', sunk by)
SCENES = {
    'camp': [('CampfireCrafting03', 1, 0, 0, 'any', 0), ('NVBedrollL', 1, 170, 210, 'in', 0), ('NVBedrollR', 1, 170, 210, 'in', 0),
             ('CLSoldiersTent01', 1, 380, 460, 'in', 0), ('CrateGenericNV', 2, 240, 380, 'any', 0), ('Barrel01', 1, 260, 380, 'any', 0),
             ('dlc04lawnchair01', 1, 150, 190, 'in', 0), ('Tire01Static', 1, 250, 400, 'any', 2)],
    'refuge': [('CampfireCrafting03', 1, 0, 0, 'any', 0), ('NVBSRefugeeTent', 2, 330, 420, 'in', 0), ('BedMattress01Static', 2, 170, 240, 'in', 0),
               ('Barrel01', 2, 240, 400, 'any', 0), ('ShoppingCart01', 1, 260, 420, 'any', 0), ('VBitterSpringsClotheslineShort', 1, 420, 520, 'any', 0),
               ('SkeletonWholeBodyClothes', 1, 180, 300, 'any', 0)],
    'raiders': [('CampfireCrafting03', 1, 0, 0, 'any', 0), ('JerseyBarricade01', 2, 520, 580, 'in', 0), ('JerseyBarricade02', 2, 520, 580, 'in', 0),
                ('SandbagStraight', 3, 480, 540, 'in', 0), ('Car01HulkBodyStatic', 1, 600, 680, 'any', 2), ('TireStack01', 2, 300, 460, 'any', 0),
                ('NVBedrollL', 2, 170, 230, 'in', 0), ('RaiderCorpseDressingChain', 1, 420, 500, 'any', 0), ('SkeletonWholeBodyClothes', 2, 200, 420, 'any', 0),
                ('Barrel01', 2, 260, 420, 'any', 0), ('CrateLarge01', 1, 300, 420, 'any', 0)],
    'beach': [('umbrellaNV', 2, 0, 160, 'any', 0), ('dlc04lawnchair01', 3, 90, 260, 'any', 0), ('Skeleton50sCasualMale', 1, 80, 200, 'any', 0),
              ('Skeleton50sCasualFemale', 1, 80, 200, 'any', 0), ('Tire01Static', 1, 240, 360, 'any', 2), ('Boat03a', 1, 320, 480, 'any', 6)],
    'crash': [('BusHulkFrontStatic01', 1, 0, 0, 'any', 2), ('Car01HulkBodyStatic', 1, 260, 340, 'any', 2), ('Car03HulkBodyStatic', 2, 280, 480, 'any', 2),
              ('SWSingleRubble', 2, 200, 420, 'any', 2), ('SkeletonWholeBodyClothes', 2, 160, 360, 'any', 0), ('Tire02Static', 2, 200, 420, 'any', 2)],
    'roadblock': [('JerseyBarricade01', 1, 0, 0, 'across', 0), ('JerseyBarricade03', 1, 190, 200, 'across', 0), ('JerseyBarricade04', 1, 190, 200, 'across', 0),
                  ('SandbagStraight', 2, 280, 360, 'in', 0), ('truckarmy02Static', 1, 420, 520, 'any', 2), ('Barrel01', 2, 240, 380, 'any', 0),
                  ('SkeletonWholeBodyClothes', 1, 200, 360, 'any', 0), ('CrateLarge01', 1, 300, 420, 'any', 0)],
}
# what ground each kind of scene is found on, and how often against the others
SCENE_ON = {'camp': (('grass', 'trees', 'yard', 'scrub'), 3), 'refuge': (('paved', 'grass', 'yard'), 2), 'raiders': (('paved', 'grass', 'scrub'), 2),
            'beach': (('sand',), 3), 'crash': (('asphalt',), 2), 'roadblock': (('asphalt',), 2)}
SCENE_EVERY = 9             # (cells of land to a scene)
SCENE_APART = 5000.0
SCENE_FLAT = 0.12           # (rise over run: a scene is laid on ground flatter than this; a beach slopes to the sea, and may)

# ---------- why a road isn't level ----------

ROUGH = 0.2                 # (rise over run along or across a road from which it gets a reason to be rough)
ROUGH_EVERY = 520.0
RUBBLE = [('RubblePile02', 3, 0.45, 0.8, 10), ('SWSingleRubble', 4, 0.8, 1.3, 2), ('IndRubblePileSm01', 3, 0.7, 1.1, 4), ('SuburbanRubblePileSm01', 3, 0.7, 1.1, 4),
          ('NVNRockCanyon06', 2, 0.12, 0.3, 20), ('NVNRockCanyon13', 2, 0.12, 0.3, 20), ('Car01HulkBodyStatic', 1, 1.0, 1.0, 6), ('Tire01Static', 1, 1.0, 1.0, 2)]
ROUGH_LIMIT = 3000


def _named():
    out = {e for _d, items in GROUND.values() for e, *_r in items} | {e for rows in STREET.values() for e, *_r in rows}
    out |= {r[0] for _e, rows in ON_ROAD.values() for r in rows}
    out |= {r[0] for rows in LIFE.values() for r in rows} | {r[0] for _w, rows in LIFE_WORD for r in rows}
    out |= {r[0] for rows in SCENES.values() for r in rows} | {r[0] for r in RUBBLE}
    return out


class _Putter:
    """Shared by what follows: a thing by editor ID onto the ground, as an add op."""

    def __init__(self, gd, pr, world, cover):
        import osmcover
        self.gd, self.grid, self.bases = gd, gd.grid(world), _bases(gd)
        self.ground = roadgen.Ground(gd, pr, world)
        self.cover, self.order = cover, osmcover.ORDER
        self.ops, self.counts = [], {}

    def kind(self, x, y):
        c = self.cover
        gx, gy = int(round(x / 128.0)) - c.gx0, int(round(y / 128.0)) - c.gy0
        if not (0 <= gx < c.A and 0 <= gy < c.D):
            return None
        v = c.kind[gy * c.A + gx]
        return self.order[v - 1] if v else None

    def has(self, edid):
        return edid.lower() in self.bases

    def put(self, edid, x, y, yaw, scale, sink, what):
        key = self.bases.get(edid.lower())
        cell = self.grid.get((int(x // 4096), int(y // 4096)))
        z = self.ground.at(x, y) if key is not None and cell is not None else None
        if z is None or z < 0:
            return False
        self.ops.append({'op': 'add', 'cell': self.gd.key(cell), 'base': key,
                         'p': [round(x, 1), round(y, 1), round(z - sink * scale, 1), 0.0, 0.0, round(yaw % math.tau, 3)], 's': round(scale, 3)})
        self.counts[what] = self.counts.get(what, 0) + 1
        return True

    def steep(self, x, y, reach=160.0):
        g = self.ground
        a, b, c, d = g.at(x - reach, y), g.at(x + reach, y), g.at(x, y - reach), g.at(x, y + reach)
        if None in (a, b, c, d):
            return 9.0
        return math.hypot(b - a, d - c) / (2 * reach)


def standing(gd, pr, world, cat):
    """The catalogue's buildings the mod has stood in this world: [(catalogue entry, x, y, z, turn)]."""
    by = {b['key']: b for b in cat}
    out = []
    for cell in gd.grid(world).values():
        c = pr.cells.get(gd.key(cell))
        for rk, r in (c['refs'].items() if c else ()):
            b = by.get(r.get('base'))
            p = r.get('p')
            if b and p and rk.startswith('+') and not r.get('removed'):
                out.append((b, p[0], p[1], p[2], p[5]))
    return out


def keep_of(stands):
    """Where the ground must stay as it is, for landsoft: where each building stands, its turn and its box."""
    return [(x, y, rz) + tuple(b['box'][k] for k in (0, 1, 3, 4)) for b, x, y, _z, rz in stands]


class _Stands:
    """Is a spot inside a building?"""

    def __init__(self, stands, margin=40.0):
        self.by = {}
        self.all = []
        for n, (b, x, y, _z, rz) in enumerate(stands):
            x0, y0, _z0, x1, y1, _z1 = b['box']
            self.all.append((x, y, math.cos(rz), math.sin(rz), x0 - margin, y0 - margin, x1 + margin, y1 + margin))
            r = math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1))) + margin
            for i in range(int((x - r) // 1024), int((x + r) // 1024) + 1):
                for j in range(int((y - r) // 1024), int((y + r) // 1024) + 1):
                    self.by.setdefault((i, j), []).append(n)

    def hit(self, x, y):
        for n in self.by.get((int(x // 1024), int(y // 1024)), ()):
            ox, oy, c, s, x0, y0, x1, y1 = self.all[n]
            dx, dy = x - ox, y - oy
            lx, ly = dx * c - dy * s, dx * s + dy * c          # (back into the building's own frame)
            if x0 <= lx <= x1 and y0 <= ly <= y1:
                return True
        return False


def life(gd, pr, world, cover, cat, seed=1, progress=None):
    """(ops, report): round each building the mod stood, the things that say what it was."""
    rng = random.Random(seed * 7919 + 1)
    P = _Putter(gd, pr, world, cover)
    stands = standing(gd, pr, world, cat)
    S = _Stands(stands)
    dressed = 0
    for n, (b, ox, oy, _z, rz) in enumerate(stands):
        if len(P.ops) >= LIFE_LIMIT:
            break
        if progress and n % 200 == 0:
            progress('Giving the buildings a purpose', n, len(stands))
        x0, y0, _z0, x1, y1, _z1 = b['box']
        cx, cy, hw, hd = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
        nx, ny = 0.0, -1.0
        if b['doors']:
            ux, uy = (b['doors'][0]['x'] - cx) / max(1.0, hw), (b['doors'][0]['y'] - cy) / max(1.0, hd)
            nx, ny = ((1.0 if ux > 0 else -1.0), 0.0) if abs(ux) > abs(uy) else (0.0, (1.0 if uy > 0 else -1.0))
        tx, ty = -ny, nx
        hn, ht = (hw, hd) if nx else (hd, hw)
        e = b['edid'].lower()
        rows = [r for words, rr in LIFE_WORD if any(w in e for w in words) for r in rr] + LIFE.get(b['family'], [])
        mine = []
        for edid, chance, where, (la, lb), (oa, ob), face in rows:
            if rng.random() > chance or not P.has(edid):
                continue
            lat, out = rng.uniform(la, lb), rng.uniform(oa, ob)
            if where == 'side':
                sg = rng.choice((-1.0, 1.0))
                mx, my = tx * sg, ty * sg
                lx, ly = cx + mx * (ht + out) + nx * lat * hn, cy + my * (ht + out) + ny * lat * hn
            else:
                sg = 1.0 if where == 'front' else -1.0
                mx, my = nx * sg, ny * sg
                lx, ly = cx + mx * (hn + out) + tx * lat * ht, cy + my * (hn + out) + ty * lat * ht
            c, s = math.cos(rz), math.sin(rz)
            x, y = ox + lx * c + ly * s, oy - lx * s + ly * c
            if S.hit(x, y) or P.kind(x, y) in ('asphalt', 'seabed', None) or any(math.hypot(x - a, y - bb) < ROOM for a, bb in mine):
                continue
            yaw = rng.uniform(0, math.tau) if face == 'any' else rz + math.atan2(-mx, -my) + (math.pi / 2 if face == 'along' else 0.0)
            if P.put(edid, x, y, yaw, 1.0, 0, {'shop': 'Round the shops', 'house': 'Round the houses', 'apartments': 'Round the hotels and flats',
                                                'civic': 'Round the public buildings', 'industrial': 'Round the works'}.get(b['family'], 'Round buildings')):
                mine.append((x, y))
        dressed += bool(mine)
    return P.ops, {'things': len(P.ops), 'buildings': dressed, 'of': len(stands), 'by': P.counts}


def scenes(gd, pr, world, cover, roads, cat, seed=1, progress=None):
    """(ops, report): camps, raider spots, a wreck on the road, what was left on the beach: a few, well apart."""
    rng = random.Random(seed * 104729 + 3)
    P = _Putter(gd, pr, world, cover)
    S = _Stands(standing(gd, pr, world, cat), margin=120.0)
    cells = sorted(P.grid)
    want = max(1, len(cells) // SCENE_EVERY)
    spots, made = [], {}
    kinds = list(SCENE_ON)
    for _try in range(want * 60):
        if len(spots) >= want:
            break
        cx, cy = rng.choice(cells)
        x, y = (cx + rng.random()) * 4096.0, (cy + rng.random()) * 4096.0
        k = P.kind(x, y)
        fits = [s for s in kinds if k in SCENE_ON[s][0]]
        if not fits or any(math.hypot(x - a, y - b) < SCENE_APART for a, b in spots) or P.steep(x, y, 300.0) > (0.3 if k == 'sand' else SCENE_FLAT):
            continue
        if (P.ground.at(x, y) or -1) < 16 or S.hit(x, y):
            continue
        # (the kind least made so far, by how often it should be)
        s = min(fits, key=lambda q: (made.get(q, 0) / SCENE_ON[q][1], rng.random()))
        road_free = s in ('crash', 'roadblock')
        along = rng.uniform(0, math.tau)
        if road_free:
            best = None
            for road in roads:
                for (ax, ay), (bx, by) in zip(road['line'], road['line'][1:]):
                    if min(abs(ax - x), abs(bx - x)) < 600 and min(abs(ay - y), abs(by - y)) < 600:
                        best = math.atan2(bx - ax, by - ay)
                        break
                if best is not None:
                    break
            if best is None:
                continue
            along = best
        got = 0
        if progress:
            progress('Places someone stopped at', len(spots), want)
        for edid, count, near, far, face, sink in SCENES[s]:
            for _n in range(count):
                if not P.has(edid):
                    continue
                for _again in range(6):
                    if face == 'across':
                        # (a row across the road: each one further along the row)
                        d = (got - 1) * 200.0
                        px, py = x + math.cos(along) * d, y - math.sin(along) * d
                        yaw = along + math.pi / 2
                    else:
                        a, d = rng.uniform(0, math.tau), rng.uniform(near, far)
                        px, py = x + math.sin(a) * d, y + math.cos(a) * d
                        yaw = rng.uniform(0, math.tau) if face == 'any' else a + (math.pi if face == 'in' else 0.0)
                    kk = P.kind(px, py)
                    if S.hit(px, py) or kk in ('seabed', None) or (kk == 'asphalt' and not road_free):
                        continue
                    if P.put(edid, px, py, yaw, 1.0, sink, 'Places someone stopped at'):
                        got += 1
                        break
        if got:
            spots.append((x, y))
            made[s] = made.get(s, 0) + 1
    return P.ops, {'things': len(P.ops), 'scenes': made, 'at': [[round(x), round(y)] for x, y in spots]}


def rough_roads(gd, pr, world, cover, roads, cat, seed=1, progress=None):
    """(ops, report): where a road still climbs or leans more than a road should, the reason lies beside it: fallen
    rubble, rock, a car that slid. Run after landsoft, on the ground as it ended up."""
    rng = random.Random(seed * 15485863 + 5)
    P = _Putter(gd, pr, world, cover)
    S = _Stands(standing(gd, pr, world, cat), margin=60.0)
    have = [r for r in RUBBLE if P.has(r[0])]
    spots = 0
    for n, road in enumerate(roads):
        if len(P.ops) >= ROUGH_LIMIT or not have:
            break
        if progress and n % 200 == 0:
            progress('Rubble where the roads are rough', n, len(roads))
        off = EDGE.get(road.get('class'), 300.0)
        at, walked = rng.uniform(0.3, 0.9) * ROUGH_EVERY, 0.0
        for (ax, ay), (bx, by) in zip(road['line'], road['line'][1:]):
            L = math.hypot(bx - ax, by - ay)
            if L < 1:
                continue
            dx, dy = (bx - ax) / L, (by - ay) / L
            while at <= walked + L:
                t = at - walked
                x, y = ax + dx * t, ay + dy * t
                at += ROUGH_EVERY * rng.uniform(0.8, 1.2)
                g = P.ground
                a, b = g.at(x - dx * 200, y - dy * 200), g.at(x + dx * 200, y + dy * 200)
                c, d = g.at(x + dy * off, y - dx * off), g.at(x - dy * off, y + dx * off)
                if None in (a, b, c, d):
                    continue
                climb, lean = abs(b - a) / 400.0, abs(d - c) / (2 * off)
                if max(climb, lean) < ROUGH:
                    continue
                spots += 1
                # (on the high side, where it would have come down from; some of it spilt onto the road)
                side = 1.0 if c > d else -1.0
                for _k in range(2 + (max(climb, lean) > 1.5 * ROUGH) + (rng.random() < 0.5)):
                    pick = rng.random() * sum(r[1] for r in have)
                    for edid, w, smin, smax, sink in have:
                        pick -= w
                        if pick <= 0:
                            break
                    out = rng.uniform(0.25, 1.15) * off
                    px, py = x + dy * out * side + dx * rng.uniform(-180, 180), y - dx * out * side + dy * rng.uniform(-180, 180)
                    if S.hit(px, py) or P.kind(px, py) in ('seabed', None):
                        continue
                    P.put(edid, px, py, rng.uniform(0, math.tau), rng.uniform(smin, smax), sink, 'Rubble where the roads are rough')
            walked += L
    return P.ops, {'things': len(P.ops), 'spots': spots}
