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
                    ('Bench01', 1, 1.0, 1.0, 0), ('CementPlanterRd01', 1, 1.0, 1.0, 0), ('NVNRockCanyon12', 2, 2.5, 6.0, 12), ('NVNRockCanyon06', 1, 3.0, 6.0, 12)]),
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
                    ('NukaVendingMachineSTATIC', 1, 1.0, 1.0, 0), ('Tire01Static', 2, 1.0, 1.0, 2), ('SWSingleRubble', 2, 0.7, 1.1, 2), ('RubblePile04', 2, 0.8, 1.3, 8),
                    ('SuburbanRubblePile01bLiteLitter', 2, 0.8, 1.2, 4), ('RoadChunkCluster01', 2, 1.0, 2.0, 2), ('SuburbanRubblePileCanyon01', 1, 0.8, 1.2, 4)]),
    'asphalt': (2.2, [('Car01HulkBodyStatic', 6, 1.0, 1.0, 2), ('Car03HulkBodyStatic', 6, 1.0, 1.0, 2), ('Car03A', 1, 1.0, 1.0, 2), ('BusHulkFrontStatic01', 1, 1.0, 1.0, 2),
                      ('truckarmy02Static', 1, 1.0, 1.0, 2), ('Barrier03', 2, 1.0, 1.0, 0), ('Tire02Static', 2, 1.0, 1.0, 2), ('NVTruck', 1, 1.0, 1.0, 2), ('JerseyBarricade02', 1, 1.0, 1.0, 0),
                      ('SWSingleRubble', 2, 0.6, 1.0, 2), ('ShoppingCart01', 1, 1.0, 1.0, 0)]),
    'scrub': (5.0, [('NVNRockCanyon06', 2, 0.25, 0.7, 30), ('NVNRockCanyon12', 2, 0.25, 0.7, 30), ('NVNRockCanyon13', 2, 0.25, 0.7, 30), ('CreosoteBushSm', 6, 0.8, 1.3, 2),
                    ('CreosoteBushLg', 3, 0.8, 1.2, 2), ('pricklypearcactus02', 2, 0.8, 1.2, 2), ('NVbarrelcactus02', 2, 0.8, 1.2, 2), ('NVNRockCanyon06', 2, 3.0, 7.0, 12), ('NVNRockCanyon13', 2, 3.0, 7.0, 12)]),
    'trees': (6.0, [('NVQueenPalm01', 5, 0.9, 1.4, 4), ('NVDatePalm01', 3, 0.9, 1.3, 4), ('EuonymusBush01', 4, 0.8, 1.3, 2), ('CreosoteBushLg', 3, 0.8, 1.2, 2)]),
    'seabed': (0.25, [('UnderwaterRockCanyon12NV', 4, 0.3, 0.8, 30), ('Boat03c', 1, 1.0, 1.0, 10), ('Tire01Static', 1, 1.0, 1.0, 2)]),
}
# What grows, apart from what lies about: a wet warm place two hundred years untended. ground kind: (how many spots a cell
# all of that ground gets, [(editor ID, how often, smallest, biggest, sunk by)]). The green is the game's own: Zion's
# trees and bushes, Vault 22's ferns and grass (grown far past their size: what the bombs left in the soil), banana
# plants, the lake's water plants in the shallows; some of it can be picked. Things in CLUMPS come several together.
PLANTS = {
    'sand': (8.0, [('NVQueenPalm01', 6, 0.9, 1.4, 4), ('NVDatePalm01', 2, 0.9, 1.3, 4), ('NVDatePalm02', 2, 0.9, 1.3, 4), ('NVDatePalm03', 2, 0.9, 1.3, 4),
                   ('NVSagoPalm01', 3, 0.8, 1.4, 2), ('NVGoldfingerBanana', 2, 1.0, 1.6, 2), ('v22Grass', 3, 1.5, 3.0, 2), ('BuffaloGourdPickable', 1, 0.8, 1.2, 0)]),
    'grass': (26.0, [('v22Grass', 8, 1.5, 3.5, 2), ('v22Fern', 6, 1.5, 4.0, 2), ('NVGoldfingerBanana', 5, 1.0, 2.0, 2), ('NVQueenPalm01', 3, 0.9, 1.5, 4),
                     ('NVDatePalm01', 1, 0.9, 1.3, 4), ('NVDatePalm02', 1, 0.9, 1.3, 4), ('NVSagoPalm01', 2, 0.8, 1.5, 2), ('NVSagoPalm02', 2, 0.8, 1.5, 2),
                     ('NVDLC02TreeA1', 1, 1.2, 2.2, 6), ('NVDLC02TreeA2', 1, 1.2, 2.2, 6), ('NVDLC02TreeA3', 1, 1.2, 2.2, 6), ('NVDLC02TreeA5', 1, 1.2, 2.2, 6), ('NVDLC02TreeB1', 1, 1.2, 2.2, 6), ('NVDLC02TreeF2', 1, 1.2, 2.2, 6), ('NVDLC02TreeF3', 1, 1.2, 2.2, 6),
                     ('NVDLC02BushA01LeavesOnly', 4, 1.0, 1.8, 4), ('EuonymusBush01', 2, 0.8, 1.4, 2), ('NVFalseSpireaPlant', 3, 1.0, 2.0, 2),
                     ('NVDLC02SacredDaturaPlant', 2, 1.5, 3.0, 0), ('BananaYuccaPickable', 1, 1.0, 1.5, 0), ('BrocFlowerPlant', 1, 1.0, 1.6, 0),
                     ('XanderRootPlant', 1, 1.0, 1.6, 0), ('CaveFungusPlant', 1, 2.0, 4.0, 0)]),
    'trees': (44.0, [('NVDLC02TreeA1', 3, 1.5, 3.0, 6), ('NVDLC02TreeA2', 3, 1.5, 3.0, 6), ('NVDLC02TreeA3', 3, 1.5, 3.0, 6), ('NVDLC02TreeA5', 3, 1.5, 3.0, 6), ('NVDLC02TreeB1', 3, 1.5, 3.0, 6), ('NVDLC02TreeF2', 3, 1.5, 3.0, 6), ('NVDLC02TreeF3', 3, 1.5, 3.0, 6),
                     ('WhiteOak01', 1, 0.5, 0.9, 10), ('NVQueenPalm01', 3, 1.0, 1.6, 4), ('NVDatePalm01', 2, 1.0, 1.4, 4), ('NVGoldfingerBanana', 6, 1.2, 2.4, 2),
                     ('v22Fern', 8, 2.0, 5.0, 2), ('v22Grass', 6, 2.0, 4.0, 2), ('NVDLC02BushA01LeavesOnly', 6, 1.0, 2.0, 4), ('NVDLC02BushEVA01LeavesOnly', 3, 1.0, 2.0, 4),
                     ('CaveFungusPlant', 2, 2.0, 4.0, 0), ('NVDLC02SacredDaturaPlant', 2, 1.5, 3.0, 0)]),
    'golf': (9.0, [('v22Grass', 6, 1.5, 3.0, 2), ('NVQueenPalm01', 3, 1.0, 1.4, 4), ('NVGoldfingerBanana', 2, 1.0, 1.8, 2), ('EuonymusBush01', 2, 0.9, 1.4, 2),
                   ('v22Fern', 2, 1.5, 3.0, 2), ('NVSagoPalm01', 2, 0.9, 1.3, 2)]),
    'yard': (16.0, [('v22Grass', 6, 1.0, 2.5, 2), ('v22Fern', 3, 1.0, 3.0, 2), ('NVGoldfingerBanana', 3, 1.0, 1.8, 2), ('NVSagoPalm01', 2, 0.8, 1.3, 2),
                   ('NVSagoPalm02', 2, 0.8, 1.3, 2), ('EuonymusBush01', 3, 0.7, 1.3, 2), ('NVDLC02BushA01LeavesOnly', 2, 0.8, 1.4, 4),
                   ('NVDLC02SacredDaturaPlant', 1, 1.2, 2.0, 0), ('BuffaloGourdPickable', 1, 0.8, 1.2, 0), ('NVDatePalm01', 1, 0.9, 1.2, 4)]),
    'paved': (6.0, [('v22Grass', 6, 1.0, 2.0, 2), ('v22Fern', 2, 1.0, 2.0, 2), ('NVFalseSpireaPlant', 2, 0.8, 1.4, 2)]),
    'scrub': (14.0, [('CreosoteBushSm', 6, 0.8, 1.4, 2), ('CreosoteBushLg', 3, 0.8, 1.3, 2), ('YuccaANV', 2, 0.8, 1.3, 2), ('YuccaBNV', 2, 0.8, 1.3, 2),
                     ('YuccaCNV', 2, 0.8, 1.3, 2), ('NVbarrelcactus02', 2, 0.8, 1.4, 2), ('pricklypearcactus03', 2, 0.8, 1.3, 2), ('NVFalseSpireaPlant', 3, 1.0, 1.8, 2),
                     ('nevadaagave02', 2, 1.0, 2.0, 0), ('BananaYuccaPickable', 1, 1.0, 1.4, 0), ('v22Fern', 2, 1.5, 3.0, 2)]),
    'seabed': (6.0, [('NVSeaPlant01', 5, 1.0, 2.5, 0), ('NVSeaPlant02', 5, 1.0, 2.5, 0)]),
}
CLUMPS = ('v22grass', 'v22fern', 'nvdlc02busha01leavesonly', 'nvdlc02busheva01leavesonly', 'nvdlc02sacreddaturaplant', 'cavefungusplant', 'nvseaplant01',
          'nvseaplant02', 'nvgoldfingerbanana', 'creosotebushsm', 'nvfalsespireaplant', 'euonymusbush01')
CLUMP_MOST = 5
CLUMP_OUT = (70.0, 280.0)   # (how far from the first the rest of a clump stand)
PLANT_SHALLOW = -220.0      # (water plants no deeper than this: where the light reaches and someone wades)
PLANT_LIMIT = 34000
PLANT_UNSAID = 'yard'      # (ground the map says nothing of, in a town: somebody's lot. It grows over as a yard does)
SEA_BED = 'Sea bed'         # (osmcover's name for that ground)
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
        if z is None or (z < 8 and what != SEA_BED):
            return False                        # (only the sea bed's own things go under the water)
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
    # and what grows there (cells in no order, so that if the limit is met no side of the map is left bare)
    planted = len(out)
    order = list(cells)
    rng.shuffle(order)
    top = max(d for d, _i in PLANTS.values())
    for n, (cx, cy) in enumerate(order):
        if len(out) - planted >= PLANT_LIMIT:
            break
        if progress and n % 64 == 0:
            progress('Planting', n, len(order))
        for _ in range(int(top) + (rng.random() < top - int(top))):
            x, y = (cx + rng.random()) * 4096.0, (cy + rng.random()) * 4096.0
            # (a building's plot grows over like anywhere else: what would stand inside the building itself is taken out
            # afterwards with everything else that would)
            k = kind_at(x, y)[0] or PLANT_UNSAID
            if k not in PLANTS:
                continue
            density, items = PLANTS[k]
            if rng.random() > density / top:
                continue
            have = [i for i in items if i[0].lower() in bases]
            if not have:
                continue
            pick = rng.random() * sum(i[1] for i in have)
            for edid, w, smin, smax, sink in have:
                pick -= w
                if pick <= 0:
                    break
            many = 1 + int(rng.random() ** 2 * CLUMP_MOST) if edid.lower() in CLUMPS else 1
            for m in range(many):
                px, py = x, y
                if m:
                    a, d = rng.uniform(0, math.tau), rng.uniform(*CLUMP_OUT)
                    px, py = x + math.sin(a) * d, y + math.cos(a) * d
                    if (kind_at(px, py)[0] or PLANT_UNSAID) != k:
                        continue
                if k == 'seabed' and not (PLANT_SHALLOW <= (ground.at(px, py) or -1e9) < 0):
                    continue
                put(edid, px, py, rng.uniform(0, math.tau), rng.uniform(smin, smax), sink, SEA_BED if k == 'seabed' else 'Plants')
    return out, {'things': len(out), 'plants': len(out) - planted, 'by': counts, 'missing': sorted(e for e in _named() if e.lower() not in bases)}


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
# ---------- what a building stands on ----------
# The game hardly ever stands a building straight on bare ground. Of 557 it stands in the open, what lies against them
# most is sidewalk (slabs under and round the walls), then rubble banked against walls and corners, street litter, fences.
# pavement slabs, longest first: (editor ID, how long, how wide); each a flat plate, laid a little over the ground
SLABS = (('SWSec1x6', 1536.0, 256.0), ('SWSec1x3', 768.0, 256.0), ('SWSingle', 256.0, 256.0))
# A slab is a flat sheet with no sides, 16 over its own origin (measured from the meshes): the game hides its edge with
# kerb pieces or brings the land up to it. Laid 6 over the ground as these once were, the sheet hung 22 up with daylight
# under it. So the sheet goes SLAB_OVER above the land, and roadbed.bed makes the land under it flat and level with it.
SLAB_TOP = 16.0
SLAB_OVER = 3.0
SLAB_UP = SLAB_OVER - SLAB_TOP
SLAB_FIT = (0.75, 1.34)     # (slabs are made this much smaller or bigger so a row of them is as long as its wall)
SLAB_IN = 6.0               # (two slabs may touch by this much before they count as lying in each other)
PAVED_FAMILIES = ('shop', 'apartments', 'civic', 'industrial')
HOUSES_PAVED = 0.3          # (of houses, how many have a walk round them)
BANKED = (('RubblePileEdging01', 5, 60.0, 30.0), ('RubblePile04', 1, 240.0, 14.0), ('SuburbanRubblePileCanyon01', 1, 240.0, 2.0),
          ('dlc04streetlitteredge03', 2, 110.0, 8.0))      # (editor ID, how often, how far out from the wall its middle lies, how high over the ground)
BANK_EVERY = 900.0          # (along a wall)
BANK_CHANCE = 0.45
CORNER = ('RubblePileEdgingCorner01', 0.22, 65.0)
FOOT_LIMIT = 16000

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
    out |= {e for _d, items in PLANTS.values() for e, *_r in items}
    out |= {r[0] for _e, rows in ON_ROAD.values() for r in rows}
    out |= {r[0] for rows in LIFE.values() for r in rows} | {r[0] for _w, rows in LIFE_WORD for r in rows}
    out |= {r[0] for rows in SCENES.values() for r in rows} | {r[0] for r in RUBBLE}
    out |= {r[0] for r in SLABS} | {r[0] for r in BANKED} | {CORNER[0]}
    out |= {r[0] for rows in LOT_KINDS.values() for r in rows if not r[0].startswith('@')} | {e for v in LOT_PICK.values() for e in v} | set(LOT_WALL)
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


def footings(gd, pr, world, cover, cat, seed=1, progress=None):
    """(ops, report): pavement round each building's walls and rubble banked against them, so that none stands straight
    out of bare flat ground. Laid in the building's own frame; left off where the ground isn't level with it, on a
    road, or under another building."""
    import townbuild
    rng = random.Random(seed * 32452843 + 9)
    P = _Putter(gd, pr, world, cover)
    stands = standing(gd, pr, world, cat)
    S = _Stands(stands, margin=-20.0)
    boxes = {}
    laid = {}                                   # (slabs down so far, by 1024 square: their outlines)

    def obnd(edid):
        if edid not in boxes:
            key = P.bases.get(edid.lower())
            boxes[edid] = townbuild.obnd(gd, key) if key else None
        return boxes[edid]

    slabs = [(e, L, W) for e, L, W in SLABS if obnd(e)]
    banked = [b for b in BANKED if P.has(b[0])]
    paved = 0
    for n, (b, ox, oy, _z, rz) in enumerate(stands):
        if len(P.ops) >= FOOT_LIMIT:
            break
        if progress and n % 200 == 0:
            progress('Pavement and rubble round the buildings', n, len(stands))
        x0, y0, _z0, x1, y1, _z1 = b['box']
        level = P.ground.at(ox, oy)
        if level is None:
            continue
        c, s = math.cos(rz), math.sin(rz)

        def world_of(lx, ly):
            return ox + lx * c + ly * s, oy - lx * s + ly * c

        def lay(edid, lx, ly, yaw, up, what, sink_to_ground=False, scale=1.0):
            # (its box's middle goes to lx, ly: where its origin is in its box is its own affair)
            o = obnd(edid)
            mx, my = ((o[0] + o[3]) / 2 * scale, (o[1] + o[4]) / 2 * scale) if o else (0.0, 0.0)
            cy, sy = math.cos(yaw), math.sin(yaw)
            wx, wy = world_of(lx - (mx * cy + my * sy), ly - (-mx * sy + my * cy))
            cx_, cy_ = world_of(lx, ly)
            g = P.ground.at(cx_, cy_)
            if g is None or g < 8 or abs(g - level) > 28 or S.hit(cx_, cy_) or P.kind(cx_, cy_) in ('asphalt', 'seabed', None):
                return False
            key = P.bases.get(edid.lower())
            cell = P.grid.get((int(wx // 4096), int(wy // 4096)))
            if key is None or cell is None:
                return False
            P.ops.append({'op': 'add', 'cell': gd.key(cell), 'base': key,
                          'p': [round(wx, 1), round(wy, 1), round((g if sink_to_ground else level) + up, 1), 0.0, 0.0, round((rz + yaw) % math.tau, 4)],
                          's': round(scale, 4)})
            P.counts[what] = P.counts.get(what, 0) + 1
            return True

        # pavement: a strip a slab wide along each wall, the front and back ones running past the corners. A strip is cut
        # into squares of one slab, each kept only if it lies on dry open ground near the building's level and in no slab
        # laid before it (two sheets at one height flicker); runs of squares that stay are covered with the longest slabs
        if slabs and (b['family'] in PAVED_FAMILIES or rng.random() < HOUSES_PAVED):
            w = slabs[0][2]

            def squares(a0, a1):
                n = max(1, int(round((a1 - a0) / w)))
                f = (a1 - a0) / n / w
                return (n, f) if SLAB_FIT[0] <= f <= SLAB_FIT[1] else (0, 1.0)

            def rect(a_from, a_to, wall, out, f, yaw, shrink):
                # (the world outline of a piece of strip: along it from a_from to a_to, from the wall outward a slab's width)
                c0, c1 = wall + out * shrink, wall + out * (w * f - shrink)
                pts = [(a_from + shrink, c0), (a_to - shrink, c0), (a_to - shrink, c1), (a_from + shrink, c1)]
                return [world_of(*(p if yaw == 0.0 else (p[1], p[0]))) for p in pts]

            def free(a_from, a_to, wall, out, f, yaw):
                mid, across = (a_from + a_to) / 2, wall + out * w * f / 2
                for along in (a_from + 8, mid, a_to - 8):
                    px, py = world_of(*((along, across) if yaw == 0.0 else (across, along)))
                    g = P.ground.at(px, py)
                    if g is None or g < 8 or abs(g - level) > 28 or S.hit(px, py) or P.kind(px, py) in ('asphalt', 'seabed', None):
                        return False
                poly = rect(a_from, a_to, wall, out, f, yaw, SLAB_IN)
                cx_, cy_ = world_of(*((mid, across) if yaw == 0.0 else (across, mid)))
                for i in range(int((cx_ - 1100) // 1024), int((cx_ + 1100) // 1024) + 1):
                    for j in range(int((cy_ - 1100) // 1024), int((cy_ + 1100) // 1024) + 1):
                        if any(townbuild.overlap(poly, other) for other in laid.get((i, j), ())):
                            return False
                return True

            def strip(a0, a1, wall, out, yaw):
                n, f = squares(a0, a1)
                seg = w * f
                ok = [free(a0 + i * seg, a0 + (i + 1) * seg, wall, out, f, yaw) for i in range(n)]
                got, i = 0, 0
                while i < n:
                    if not ok[i]:
                        i += 1
                        continue
                    fit = next((sl for sl in slabs if all(ok[i:i + int(round(sl[1] / w))]) and i + int(round(sl[1] / w)) <= n), None)
                    if fit is None:
                        i += 1
                        continue
                    e, L, _W = fit
                    k = int(round(L / w))
                    mid, across = a0 + (i + k / 2.0) * seg, wall + out * seg / 2
                    lx, ly = (mid, across) if yaw == 0.0 else (across, mid)
                    # (a slab's long side is its own east-west: a quarter turn in the game's sense for a strip running north)
                    if lay(e, lx, ly, yaw, SLAB_OVER - SLAB_TOP * f, 'Pavement round buildings', scale=f):
                        got += 1
                        poly = rect(a0 + i * seg, a0 + (i + k) * seg, wall, out, f, yaw, 0.0)
                        cx_, cy_ = sum(p[0] for p in poly) / 4, sum(p[1] for p in poly) / 4
                        laid.setdefault((int(cx_ // 1024), int(cy_ // 1024)), []).append(poly)
                    i += k
                return got, (f if n else 0.0)

            # (the sides first: the front and back rows then run past the corners by as much as the side rows are wide)
            got_w, f_w = strip(y0, y1, x0, -1.0, math.pi / 2)
            got_e, f_e = strip(y0, y1, x1, 1.0, math.pi / 2)
            got_s, _f = strip(x0 - w * f_w, x1 + w * f_e, y0, -1.0, 0.0)
            got_n, _f = strip(x0 - w * f_w, x1 + w * f_e, y1, 1.0, 0.0)
            paved += bool(got_w + got_e + got_s + got_n)
        # rubble banked against the back and the sides
        if banked:
            walls = [(x0, x1, y1, 0.0, 1.0), (y0, y1, x0, math.pi / 2, -1.0), (y0, y1, x1, math.pi / 2, 1.0)]
            if b['doors']:
                front_y = b['doors'][0]['y'] > (y0 + y1) / 2
                walls[0] = (x0, x1, y0 if front_y else y1, 0.0, -1.0 if front_y else 1.0)
            for a0, a1, wall, yaw, out in walls:
                at = a0 + rng.uniform(0.2, 0.8) * BANK_EVERY
                while at < a1 - 100:
                    if rng.random() < BANK_CHANCE:
                        pick = rng.random() * sum(q[1] for q in banked)
                        for e, wt, off, up in banked:
                            pick -= wt
                            if pick <= 0:
                                break
                        lx, ly = (at, wall + out * off) if yaw == 0.0 else (wall + out * off, at)
                        # (its long side along the wall)
                        lay(e, lx, ly, yaw + math.pi / 2 + (math.pi if rng.random() < 0.5 else 0.0), up, 'Rubble against walls', True)
                    at += BANK_EVERY * rng.uniform(0.7, 1.3)
            if P.has(CORNER[0]):
                for k, (lx, ly) in enumerate(((x0, y0), (x1, y0), (x1, y1), (x0, y1))):
                    if rng.random() < CORNER[1]:
                        lay(CORNER[0], lx, ly, k * math.pi / 2, CORNER[2], 'Rubble against walls', True)
    return P.ops, {'things': len(P.ops), 'paved': paved, 'of': len(stands), 'by': P.counts}


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
    spots, made, which = [], {}, []
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
            which.append(s)
            made[s] = made.get(s, 0) + 1
    return P.ops, {'things': len(P.ops), 'scenes': made, 'at': [[round(x), round(y)] for x, y in spots],
                   'spots': [[round(x), round(y), k] for (x, y), k in zip(spots, which)]}


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


# ---------- the plots nothing was built on ----------
# A squeezed map leaves most plots too small for any of the game's buildings; left bare, the streets have gaps between
# the ruins. Each empty plot becomes something a ruined town has there, by its size: a house's shell, a walled yard with
# a trailer in it, a lot of wrecks, a heap. The walls run along the plot's long sides, so a street has an edge.
# what a lot is: [(editor ID, how many, 'mid' (about the middle) | 'any' (anywhere in it) | 'edge' (against a side), facing: 'plot' | 'any')]
LOT_KINDS = {
    'ruin': [('@ruin', 1, 'mid', 'plot'), ('RubblePile04', 1, 'any', 'any'), ('SuburbanRubblePileSm01', 2, 'any', 'any'), ('ConcreteSlab01', 2, 'any', 'any')],
    'yard': [('@trailer', 1, 'mid', 'plot'), ('CrateLarge01', 2, 'any', 'any'), ('Barrel01', 2, 'any', 'any'), ('TireStack01', 1, 'any', 'any'),
             ('Car01HulkBodyStatic', 1, 'any', 'plot'), ('ConcreteBlockPile01', 1, 'edge', 'plot')],
    'wrecks': [('Car01HulkBodyStatic', 2, 'any', 'plot'), ('Car03HulkBodyStatic', 2, 'any', 'plot'), ('ConcreteDividers01', 1, 'edge', 'plot'),
               ('Tire01Static', 2, 'any', 'any'), ('NVTruck', 1, 'any', 'plot')],
    'heap': [('RubblePile02', 1, 'mid', 'any'), ('SuburbanRubblePile01bLiteLitter', 1, 'any', 'any'), ('RoadChunkCluster01', 2, 'any', 'any'),
             ('ConcreteSlab01', 3, 'any', 'any'), ('SWSingleRubble', 2, 'any', 'any')],
    'works': [('ScaffoldDestroyed01', 1, 'mid', 'plot'), ('ConcreteDividers02', 1, 'edge', 'plot'), ('ConcreteBlockPile01', 2, 'any', 'any'),
              ('CrateLarge01', 1, 'any', 'any'), ('ConcreteSlab01', 3, 'any', 'any')],
    'play': [('SwingsRuined01', 1, 'any', 'plot'), ('SlideRuined01', 1, 'any', 'plot'), ('MerryGoRoundRuined01', 1, 'mid', 'any'), ('SeeSawRuined01', 1, 'any', 'plot'),
             ('Bench01', 1, 'edge', 'plot')],
    'sign': [('@billboard', 1, 'edge', 'plot'), ('SuburbanRubblePileSm01', 1, 'any', 'any'), ('Tire01Static', 1, 'any', 'any')],
    'scrap': [('SuburbanRubblePileSm01', 1, 'mid', 'any'), ('ConcreteSlab01', 1, 'any', 'any'), ('Barrel01', 1, 'any', 'any')],
}
LOT_PICK = {'@ruin': ('HouseRuined02', 'HouseRuined03', 'HouseRuined04b', 'HouseRuined04c'),
            '@trailer': ('TruckTrailer01', 'TruckTrailer03', 'TruckTrailer04', 'TruckTrailer06', 'Trucktrailer07'),
            '@billboard': ('BillboardBlank01', 'BillboardCarAV1', 'BillboardSunsetSarsaparillaNV', 'BillboardBoulderLNV')}
# by the plot's shorter side: which kinds, and how often each
LOT_BY_SIZE = ((420.0, (('scrap', 3), ('heap', 1))),
               (900.0, (('heap', 3), ('wrecks', 3), ('yard', 2), ('sign', 1), ('play', 1), ('ruin', 1))),
               (1e9, (('ruin', 4), ('yard', 3), ('wrecks', 2), ('works', 2), ('heap', 2), ('play', 1), ('sign', 1))))
LOT_WALL = ('UrbanCourtyardwallStr01', 'UrbanCourtyardwallStr02')
LOT_WALLED = 0.45           # (of plots with a long side of two wall lengths or more, how many get walls)
LOT_GAPS = 0.3              # (of a wall's lengths, how many are left out: it has fallen there)
LOT_SHARE = 0.8             # (of empty plots, how many get anything: some ground is just bare)
LOT_LIMIT = 16000


def lots(gd, pr, world, cover, cat, rows, seed=1, progress=None):
    """(ops, report). rows: the map's building plots ({'ring': [(x, y)...], 'pad'}, the layer osmplace keeps); each one
    no building stands on is filled as a ruined lot."""
    import townbuild
    rng = random.Random(seed * 49979687 + 13)
    P = _Putter(gd, pr, world, cover)
    stands = standing(gd, pr, world, cat)
    S = _Stands(stands, margin=30.0)
    built = {}
    for _b, x, y, _z, _rz in stands:
        built.setdefault((int(x // 2048), int(y // 2048)), []).append((x, y))
    boxes = {}

    def obnd(edid):
        if edid not in boxes:
            key = P.bases.get(edid.lower())
            boxes[edid] = townbuild.obnd(gd, key) if key else None
        return boxes[edid]

    made = {}
    filled = empty = 0
    for n, row in enumerate(rows):
        if len(P.ops) >= LOT_LIMIT:
            break
        if progress and n % 500 == 0:
            progress('Filling the empty plots', n, len(rows))
        ring = row.get('ring') or []
        if len(ring) < 3 or not row.get('pad'):
            continue
        cx, cy, ang, along, across = townbuild.rect_of(ring)
        ux, uy = math.cos(ang), math.sin(ang)
        # (is something built here already: a building's origin on the plot, or near enough to it)
        reach = max(along, across) / 2 + 250
        if any(math.hypot(bx - cx, by - cy) < reach for i in (-1, 0, 1) for j in (-1, 0, 1)
               for bx, by in built.get((int(cx // 2048) + i, int(cy // 2048) + j), ())):
            continue
        level = P.ground.at(cx, cy)
        if level is None or level < 8 or P.kind(cx, cy) in ('seabed', None):
            continue
        empty += 1
        if rng.random() > LOT_SHARE:
            continue
        short = min(along, across)
        kinds = next(k for limit, k in LOT_BY_SIZE if short < limit)
        pick = rng.random() * sum(w for _k, w in kinds)
        for kind, w in kinds:
            pick -= w
            if pick <= 0:
                break
        # the plot's own turn, in the game's sense (clockwise from north), its long side first
        if across > along:
            ux, uy, along, across = -uy, ux, across, along
        yaw_plot = math.atan2(ux, uy) - math.pi / 2        # (a thing's own east along the plot's length)
        got = 0

        def lay(edid, a, b, yaw, what):
            # (a, b: along and across the plot from its middle)
            x, y = cx + ux * a - uy * b, cy + uy * a + ux * b
            o = obnd(edid)
            g = P.ground.at(x, y)
            if not o or g is None or g < 8 or abs(g - level) > 40 or S.hit(x, y) or P.kind(x, y) in ('asphalt', 'seabed', None):
                return False
            key = P.bases.get(edid.lower())
            cell = P.grid.get((int(x // 4096), int(y // 4096)))
            if key is None or cell is None:
                return False
            P.ops.append({'op': 'add', 'cell': gd.key(cell), 'base': key, 'p': [round(x, 1), round(y, 1), round(g - o[2] - 5.0, 1), 0.0, 0.0, round(yaw % math.tau, 4)], 's': 1})
            P.counts[what] = P.counts.get(what, 0) + 1
            return True

        mine = []
        for name, count, where, face in LOT_KINDS[kind]:
            for _k in range(count):
                edid = rng.choice([e for e in LOT_PICK[name] if P.has(e)] or [None]) if name.startswith('@') else name
                if not edid or not P.has(edid):
                    continue
                o = obnd(edid)
                half = max(o[3] - o[0], o[4] - o[1]) / 2 if o else 0
                if where != 'mid' and half * 2 > short * 1.6:
                    continue                    # (far too big for this plot)
                for _try in range(5):
                    if where == 'mid':
                        a, b = rng.uniform(-0.15, 0.15) * along, rng.uniform(-0.15, 0.15) * across
                    elif where == 'edge':
                        a, b = rng.uniform(-0.4, 0.4) * along, rng.choice((-1, 1)) * (across / 2 - 60)
                    else:
                        a, b = rng.uniform(-0.42, 0.42) * along, rng.uniform(-0.42, 0.42) * across
                    if any(math.hypot(a - p, b - q) < min(half, 200) + r for p, q, r in mine):
                        continue
                    yaw = yaw_plot + rng.choice((0.0, math.pi)) + rng.uniform(-0.12, 0.12) if face == 'plot' else rng.uniform(0, math.tau)
                    if lay(edid, a, b, yaw, 'Empty plots: ' + kind):
                        mine.append((a, b, min(half, 200)))
                        got += 1
                        break
        # walls along the long sides
        walls = [e for e in LOT_WALL if P.has(e)]
        if walls and along >= 512 and across >= 300 and kind not in ('scrap',) and rng.random() < LOT_WALLED:
            wl = 256.0
            for side in (-1, 1):
                if rng.random() < 0.25:
                    continue
                k = int(along // wl)
                for i in range(k):
                    if rng.random() < LOT_GAPS:
                        continue
                    a = -k * wl / 2 + (i + 0.5) * wl
                    got += lay(rng.choice(walls), a, side * (across / 2 - 20), yaw_plot, 'Walls round plots')
        if got:
            filled += 1
            made[kind] = made.get(kind, 0) + 1
    return P.ops, {'things': len(P.ops), 'empty': empty, 'filled': filled, 'kinds': made, 'by': P.counts}
