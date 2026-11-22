"""Inside the Flotilla's ship (flotilla.py; the plan: docs/waikiki-flotilla-interiors.md): four places of the mod's own,
built as the Missouri's are (shipinside.Layout and build: the game's Utility kit on its 256-unit squares, walked from its
real collision before anything is placed), with what a pirate crew would have made of a cargo ship.

    the house      her deckhouse amidships: off one passage the crew's mess, its galley, the card room, the captain's
                   cabin. In from her deck through a bulkhead door in the house's forward face; down at the
                   passage's after end
    below decks    the passage under the house: two berthings, the quartermaster's store (the way up to the house
                   goes through it), the brig, the still. Forward to the hold; aft to the pens
    the hold       forward, under the containers: what was taken, stacked. Down through a hatch in her deck, or along
                   from below decks
    the pens       aft: where people are kept until a boat takes them on. Cages, mattresses, a guard's table. Down
                   through the after hatch, or along from below decks
    two boats      of the hulks lashed outside the ring to starboard (`BOATS`), a cabin each: a crew's bunks and stove;
                   a workbench and stores. A steel gangplank of FOLab's own from the planking to the after deck, a
                   hatch in that deck

And inside the settlers' freighter on the beach at Waimanalo (settlerset.freighter: the same hull, her house aft, cargo
hatches forward), two places, with nothing said of the Huang that the story hasn't:

    the house      her deckhouse aft: a mess and galley, two berthings, the master's cabin. In from her deck through a
                   door in the house's forward face; down to the hold
    the hold       under her hatches: the generator the story gives her, fuel, stores. Down through a hatch in her
                   deck between the cargo hatches, or from the house

`SHIPS` {ship: {'edid': her record's editor ID less the prefix, 'places' {key: (editor ID, name, layout)}, 'deck': where
each way in stands on her deck in her own frame (the ship along y, bow -y) and which place and door it leads to}}.
`board` gives the ops for a ship standing at (x, y, z, turn); `navmesh_ops` each place's navmesh after. `PLACES` and
`DECK` are the Flotilla ship's. Nobody lives in them yet."""
import math

import cargoset  # noqa: F401  (its pictures: the gangplank is of the containers' steel)
import flotilla
import modelsets
import settlerset
import recordio
import shipinside
import townbuild
from shipinside import Layout

PREFIX = 'Flotilla'
HATCH = 'HatchDoor'         # (the game's flat hatch, a door: in her deck over the hold and over the pens)
HOUSE_Y = -450.0            # (the house's forward face, in her frame: settlerset.FLOTILLA_SHIP)
OUT = 130.0                 # (how far from a way in one arrives on deck)


def _house():
    # (rooms off one side of the passage, three squares deep: with the passage, four squares across, inside her beam)
    L = Layout('house')
    L.hall([(0, j) for j in range(-7, 8)])
    mess = L.room('mess', 1, -7, 3, 4, 'mess')
    galley = L.room('galley', 1, -3, 3, 3, 'galley')
    cards = L.room('store', 1, 0, 3, 3, 'card room')
    cabin = L.room('cabin', 1, 3, 3, 5, 'captain\'s cabin')
    for j in (-6, -2, 1, 4):
        L.way((1, j), (0, j))
    L.exit('deck', (0, -7), 3, ('deck', 'house'))
    L.exit('down', (0, 7), 1, ('below', 'up'))
    # the mess: the navy's tables with their benches, the crew's lockers along the forward bulkhead
    for y in (-1700, -1408, -1116):
        L.put('NavalBench01TableBothSides', 512, y, face=90)
    L.wall('Locker01Military', mess, 's', 150)
    L.wall('Locker01Military', mess, 's', 240)
    L.wall('NukaVendingMachine', mess, 'e', 500)
    # the galley
    L.wall('CookStove', galley, 'e', 150)
    L.wall('CookStove', galley, 'e', 290)
    L.wall('AndaleStove', galley, 'n', 200)
    L.wall('NVWaterCrateSqr01', galley, 'n', 500)
    L.put('Table02', 512, -512, face=0)
    # the card room
    L.put('CardTable01', 512, 256, face=0)
    for dx, dy, f in ((0, -80, 0), (0, 80, 180), (-80, 0, 90), (80, 0, 270)):
        L.put('Chair01', 512 + dx, 256 + dy, face=f)
    L.wall('SubCouchDirty01F', cards, 'e', 365)
    L.wall('Barrel01', cards, 's', 600)
    # the captain's cabin: the one real bed aboard, a desk, a safe, what the captain kept back
    L.wall('BedTwin01L', cabin, 'e', 200)
    L.wall('GenericSafe01', cabin, 'e', 520)
    L.wall('NVMetalCabinetBoomerBarracks', cabin, 'e', 760)
    L.wall('Footlocker01Empty', cabin, 'e', 960)
    L.wall('NavalTable01', cabin, 'n', 365)
    L.put('ComputerNavalChair01R', 512, 1690, face=0)
    L.wall('SubCouchDirty01F', cabin, 's', 500)
    return L


def _below():
    L = Layout('below')
    L.hall([(0, j) for j in range(-8, 9)])
    b1 = L.room('berthing', 1, -8, 3, 4, 'forward berthing')
    store = L.room('store', 1, -4, 3, 3, 'quartermaster\'s store')
    brig = L.room('store', 1, -1, 3, 3, 'brig')
    still = L.room('store', 1, 2, 3, 3, 'still')
    b2 = L.room('berthing', 1, 5, 3, 4, 'after berthing')
    for j in (-7, -3, 0, 3, 6):
        L.way((1, j), (0, j))
    L.exit('fwd', (0, -8), 3, ('hold', 'aft'))
    L.exit('aft', (0, 8), 1, ('pens', 'fwd'))
    L.exit('up', (3, -3), 0, ('house', 'down'))
    for room in (b1, b2):
        for a in (150, 400, 650):
            L.wall('BedFrame01Bunk', room, 'e', a)
        L.wall('Footlocker01Empty', room, 'n', 200)
        L.wall('Locker01Military', room, 's', 400)
    # the quartermaster's store: what's given out; the ladderway up to the house goes through it
    for a in (130, 600):
        L.wall('CrateLarge01', store, 'e', a)
    L.wall('NVMetalCabinetBoomerBarracks', store, 's', 200)
    L.wall('AmmoBoxSTATIC', store, 'n', 150)
    L.wall('AmmoBoxSTATIC', store, 'n', 200)
    L.wall('ToolboxContainer', store, 'n', 500)
    # the brig: for the crew's own, and anyone worth more kept apart
    for a in (150, 365, 580):
        L.wall('DancerCage04', brig, 'e', a, gap=30)
    L.wall('Chair01', brig, 'n', 500)
    # the still
    L.wall('dlc04moonshinedistillery01', still, 'e', 365, gap=20)
    L.wall('Barrel01', still, 'n', 150)
    L.wall('Barrel01', still, 'n', 250)
    L.wall('Barrel01', still, 's', 150)
    return L


def _hold():
    L = Layout('hold')
    h = L.room('store', -2, -4, 5, 8, 'hold')
    L.exit('aft', (0, 3), 1, ('below', 'fwd'))
    L.exit('hatch', (2, -1), 0, ('deck', 'hold'))
    # stacks down both sides, a lane between; the best of it at the forward end
    for side in ('w', 'e'):
        for k, a in enumerate((150, 420, 690, 960, 1500, 1770)):
            L.wall(('CrateLarge01', 'CrateGenericNV', 'CrateLarge01')[k % 3], h, side, a, gap=10 + 30 * (k % 2))
    for a in (200, 420, 860, 1080):
        L.wall('CrateLarge01', h, 's', a)
    L.wall('BMLootTrunk', h, 's', 640)
    for x, y in ((-140, -500), (150, -380), (-120, 180), (140, 420)):
        L.put('Barrel01', x, y, face=0)
    L.put('NVDuffleBagContainerEmpty', -60, -760, face=40)
    L.put('MetalBox01Empty', 90, -770, face=10)
    return L


def _pens():
    L = Layout('pens')
    p = L.room('store', -2, -3, 5, 6, 'pens')
    L.exit('fwd', (0, -3), 3, ('below', 'aft'))
    L.exit('hatch', (2, 0), 0, ('deck', 'pens'))
    # cages along her sides and across the after bulkhead, mattresses on the plates between, the guard's table by the door
    for a in (150, 420, 690, 1230):
        L.wall('DancerCage04', p, 'w', a, gap=30)
    for a in (150, 420, 1230):
        L.wall('DancerCage04', p, 'e', a, gap=30)
    for a in (250, 520, 790):
        L.wall('NVDLC03KennelCage05', p, 'n', a, gap=20)
    for x, y, f in ((-150, -60, 20), (120, 120, 200), (-100, 330, 90), (160, 420, 310)):
        L.put('BedMattress01Static', x, y, face=f)
    L.put('Table02', 250, -560, face=0)
    L.put('Chair01', 250, -480, face=180)
    L.put('Barrel01', -420, -560, face=0)
    return L


def _settler_house():
    L = Layout('settler house')
    L.hall([(0, j) for j in range(-6, 7)])
    mess = L.room('mess', 1, -6, 3, 4, 'mess')
    b1 = L.room('berthing', 1, -2, 3, 3, 'forward berthing')
    b2 = L.room('berthing', 1, 1, 3, 3, 'after berthing')
    cabin = L.room('cabin', 1, 4, 3, 3, 'master\'s cabin')
    for j in (-5, -1, 2, 5):
        L.way((1, j), (0, j))
    L.exit('deck', (0, -6), 3, ('deck', 'house'))
    L.exit('down', (0, 6), 1, ('hold', 'up'))
    for y in (-1440, -1150):
        L.put('NavalBench01TableBothSides', 512, y, face=90)
    L.wall('CookStove', mess, 's', 200)
    L.wall('AndaleStove', mess, 's', 420)
    L.wall('NVWaterCrateSqr01', mess, 's', 620)
    for room in (b1, b2):
        for a in (150, 400):
            L.wall('BedFrame01Bunk', room, 'e', a)
        L.wall('Footlocker01Empty', room, 'n', 200)
        L.wall('Locker01Military', room, 'n', 500)
    L.wall('BedTwin01L', cabin, 'e', 200)
    L.wall('NavalTable01', cabin, 'n', 365)
    L.put('ComputerNavalChair01R', 512, 1500, face=0)
    L.wall('Footlocker01Empty', cabin, 'e', 560)
    L.wall('GenericBookcase01', cabin, 's', 500)
    return L


def _settler_hold():
    L = Layout('settler hold')
    h = L.room('engine room', -2, -4, 5, 8, 'hold')
    L.exit('up', (0, 3), 1, ('house', 'down'))
    L.exit('hatch', (2, -1), 0, ('deck', 'hold'))
    # the generator (the story: run on alcohol from their cane) and its fuel at the after end, stores forward
    L.put('IndustrialMachine02NoSound', -300, 420, face=90)
    L.put('NVNellisLargeFuelTank', -330, -60, face=90)
    for a in (150, 250, 350):
        L.wall('Barrel01', h, 'n', a)
    L.wall('GenericConsolePanel04NoAnim', h, 'n', 620)
    L.wall('ToolboxContainer', h, 'n', 1000)
    for k, a in enumerate((150, 420, 690)):
        L.wall(('CrateLarge01', 'CrateGenericNV')[k % 2], h, 'e', a, gap=10)
    for a in (200, 440, 840, 1080):
        L.wall('CrateLarge01', h, 's', a)
    for a in (150, 420):
        L.wall('CrateGenericNV', h, 'w', a, gap=10)
    L.put('NVWaterCrateSqr01', 200, -620, face=0)
    L.put('NVWaterCrateSqr01', 290, -620, face=0)
    return L


def _boat_crew():
    L = Layout('crew boat')
    r = L.room('berthing', -1, -2, 3, 4, 'cabin')
    L.exit('out', (0, 1), 1, ('deck', 'boat1'))
    for a in (150, 400, 650):
        L.wall('BedFrame01Bunk', r, 'e', a)
    L.wall('CookStove', r, 's', 200)
    L.wall('NVWaterCrateSqr01', r, 's', 420)
    L.wall('Locker01Military', r, 'w', 150)
    L.wall('Footlocker01Empty', r, 'w', 420)
    L.put('Table02', -60, -160, face=0)
    L.put('Chair01', -60, -80, face=180)
    return L


def _boat_works():
    L = Layout('work boat')
    r = L.room('store', -1, -2, 3, 4, 'cabin')
    L.exit('out', (0, 1), 1, ('deck', 'boat2'))
    L.wall('WorkBench', r, 'e', 250)
    L.wall('ToolboxContainer', r, 'e', 520)
    L.wall('CrateLarge01', r, 's', 200)
    L.wall('CrateGenericNV', r, 's', 450)
    L.wall('Barrel01', r, 'w', 150)
    L.wall('Barrel01', r, 'w', 250)
    L.wall('BedMattress01FloorL', r, 'w', 600)
    L.wall('AmmoBoxSTATIC', r, 'e', 700)
    return L


# two of the hulks lashed outside the ring get a cabin below to go into: a gangplank of FOLab's own from the planking up
# to the after deck, the game's flat hatch in that deck (her wheelhouse is small and open behind: a bulkhead door stood
# on it looked stuck on, 22 Nov 2026). In the ship's frame (flotilla.HULKS: the boat's middle RING[0] + 475 out, its
# deck 160 over its origin).
PLANK = 'flotilla_plank'
PLANK_SIZE = (250.0, 130.0, 12.0)
BOAT_X = flotilla.RING[0] + 130.0 + 345.0
BOAT_DECK = 160.0
HATCH_AFT = 500.0           # (the hatch in her after deck, abaft her middle: her wheelhouse ends at 352 and is open behind)
PLANK_Y = 520.0             # (where the plank comes aboard, abaft the boat's middle: her open after deck)
PLANK_ENDS = (flotilla.RING[0] + 50.0, BOAT_X - 320.0 + 70.0)     # (on the planking; on her deck inside her side)


def _plank():
    lk = {'plate': modelsets.look('cargo/frame', tile=64)}
    return {'name': 'FOLabFlotillaPlank', 'looks': lk,
            'parts': [{'shape': 'box', 'size': list(PLANK_SIZE), 'at': [0, 0, -PLANK_SIZE[2]], 'look': 'plate', 'solid': True, 'material': 'metal'}]}


modelsets.PIECES.setdefault(PLANK, {'label': 'Gangplank, steel plate', 'set': 'cargo', 'file': 'plank', 'describe': _plank, 'edid': 'FOLabFlotillaPlank'})


def _boat(edid, y):
    """(the door's deck entry, the plank's place) for the hulk `edid` lashed to starboard at y along the ship."""
    water = -flotilla.SHIP_Z
    deck = water + flotilla.FLOAT[edid] + BOAT_DECK
    low = water + flotilla.DOCK_TOP
    x0, x1 = PLANK_ENDS
    rise, run = deck + 2.0 - low, x1 - x0
    door = (HATCH, BOAT_X, y + HATCH_AFT, 0.0, (BOAT_X - OUT, y + HATCH_AFT, -math.pi / 2), deck)
    plank = (PLANK, (x0 + x1) / 2, y + PLANK_Y, (low + deck + 2.0) / 2, 0.0, PLANK_TILT * math.atan2(rise, run), 0.0)
    return door, plank


PLANK_TILT = 1.0            # (which way a turn about y lifts the plank's outer end: found by walking it)
PLACES = {'house': ('FlotillaHouse', 'The Flotilla - The House', _house),
          'below': ('FlotillaBelowDecks', 'The Flotilla - Below Decks', _below),
          'hold': ('FlotillaHold', 'The Flotilla - The Hold', _hold),
          'pens': ('FlotillaPens', 'The Flotilla - The Pens', _pens),
          'boat1': ('FlotillaBoatForward', 'The Flotilla - A Crew\'s Boat', _boat_crew),
          'boat2': ('FlotillaBoatAft', 'The Flotilla - The Work Boat', _boat_works)}
# her deck's ways in, in her frame: (what stands there, x, y, its turn, where one arrives: x, y, facing)
DECK = {'house': (shipinside.DOOR, 300.0, HOUSE_Y - 6.0, math.pi / 2, (300.0, HOUSE_Y - OUT, math.pi)),
        'hold': (HATCH, 0.0, -900.0, 0.0, (0.0, -900.0 + OUT, 0.0)),
        'pens': (HATCH, 0.0, 720.0, 0.0, (0.0, 720.0 + OUT, 0.0))}
BOATS = {'boat1': ('Boat01a', -2900.0), 'boat2': ('Boat01b', 2900.0)}       # (flotilla.HULKS' two to starboard, fore and aft)
EXTRAS = []
for _tag, (_e, _y) in BOATS.items():
    DECK[_tag], _p = _boat(_e, _y)
    EXTRAS.append(_p)
S_HOUSE_Y = 2250.0          # (the freighter's house's forward face: settlerset.freighter's default)
S_HATCH_Y = -150.0          # (between her third and fourth cargo hatches: the others have a mast between them)
SHIPS = {
    'flotilla': {'edid': 'FlotillaShip', 'label': 'Inside the Flotilla\'s ship', 'places': PLACES, 'deck': DECK,
                 'to': {'house': ('house', 'deck'), 'hold': ('hold', 'hatch'), 'pens': ('pens', 'hatch'), 'boat1': ('boat1', 'out'), 'boat2': ('boat2', 'out')},
                 'extras': EXTRAS},
    'settler': {'edid': 'SettlerFreighter', 'label': 'Inside the settlers\' freighter',
                'places': {'house': ('FreighterHouse', 'The Freighter - The House', _settler_house),
                           'hold': ('FreighterHold', 'The Freighter - The Hold', _settler_hold)},
                'deck': {'house': (shipinside.DOOR, 300.0, S_HOUSE_Y - 6.0, math.pi / 2, (300.0, S_HOUSE_Y - OUT, math.pi)),
                         'hold': (HATCH, 0.0, S_HATCH_Y, 0.0, (OUT + 20.0, S_HATCH_Y, math.pi / 2))},
                'to': {'house': ('house', 'deck'), 'hold': ('hold', 'hatch')}},
}
DECK_UP = settlerset.F_DECK     # (both are the one hull: her deck this far over her origin)
_layouts = {}


def layout(key, which='flotilla'):
    if (which, key) not in _layouts:
        _layouts[(which, key)] = SHIPS[which]['places'][key][2]()
    return _layouts[(which, key)]


def build(gd, key, which='flotilla'):
    return shipinside.build(gd, '%s:%s' % (which, key), layout(key, which), SHIPS[which]['places'][key][1])


def to_world(ship, lx, ly):
    """A spot in her frame, where she stands: ship = (x, y, z, turn)."""
    c, s = math.cos(ship[3]), math.sin(ship[3])
    return ship[0] + lx * c + ly * s, ship[1] - lx * s + ly * c


def deck_spots(ship, which='flotilla'):
    """{way in: (the door's place [x, y, z, 0, 0, rz], where one arrives [x, y, z, 0, 0, rz])} in the world."""
    out = {}
    z = ship[2] + DECK_UP
    for tag, (_e, lx, ly, turn, (ax, ay, face), *up) in SHIPS[which]['deck'].items():
        z = ship[2] + (up[0] if up else DECK_UP)        # (a way in not on her own deck gives its height over her origin)
        x, y = to_world(ship, lx, ly)
        ox, oy = to_world(ship, ax, ay)
        out[tag] = ([round(x, 1), round(y, 1), round(z + (8.0 if _e == HATCH else 0.0), 1), 0.0, 0.0, round((ship[3] + turn) % math.tau, 4)],
                    [round(ox, 1), round(oy, 1), round(z + 10.0, 1), 0.0, 0.0, round((ship[3] + face) % math.tau, 4)])
    return out


def standing(pr, prefix='FOLab', which='flotilla'):
    """Where the ship stands in the mod: (x, y, z, turn, the cell she is filed under), or None."""
    edid = prefix + SHIPS[which]['edid']
    key = next((k for k, r in pr.records.items() if k.startswith('+') and recordio.field(r, 'EDID') == edid), None)
    for ck, c in pr.cells.items():
        for r in c['refs'].values():
            if key and r.get('base') == key and not r.get('removed'):
                p = r['p']
                return p[0], p[1], p[2], p[5], ck
    return None


def board(gd, pr, world, ship, prefix='FOLab', which='flotilla'):
    """(ops, report): her places, every door between them linked both ways, and the ways in on her deck.
    Raises ValueError with the reason when something isn't there or a place can't be built."""
    spec = SHIPS[which]
    PL = spec['places']
    for key, (edid, full, _fn) in PL.items():
        if shipinside._own(pr, prefix + edid, 'CELL'):
            raise ValueError('She already has her insides (%s).' % full)
    built = {k: build(gd, k, which) for k in PL}
    forms = shipinside._forms(gd, {shipinside.DOOR, HATCH})
    lacking = sorted({shipinside.DOOR, HATCH} - set(forms))
    if lacking:
        raise ValueError('The game files lack her deck\'s doors (%s).' % ', '.join(lacking))
    like = townbuild.grand_inside(gd, shipinside.LIKE)
    ops, rep = [], {'places': {}, 'pieces': 0, 'things': 0, 'lights': 0, 'seeds': {}}
    places = {}
    tagged = lambda key: '%s_%s' % (which[:2], key)
    for key, (edid, full, _fn) in PL.items():
        rec = recordio.load(gd, gd.from_key(like['cell']))
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('XOWN', 'XRNK')]
        recordio.set_field(rec, 'EDID', prefix + edid, label='Editor ID')
        recordio.set_field(rec, 'FULL', full, label='Name')
        ops.append({'op': 'record_new', 'record': rec, 'name': tagged(key)})
        ck = '$' + tagged(key)
        B = built[key]
        for k, p in B.pieces + B.lights + B.doors:
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': [round(v, 4) for v in p], 's': 1})
        for (k, p, _e), sc in zip(B.things, B.scales):
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': p, 's': sc})
        for tag, (k, p, arrive, to) in B.exits.items():
            name = '%s_%s' % (tagged(key), tag)
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': p, 's': 1, 'name': name})
            places[(key, tag)] = (ck, name, arrive, to)
        rep['places'][key] = full
        rep['pieces'] += len(B.pieces)
        rep['things'] += len(B.things)
        rep['lights'] += len(B.lights)
        rep['seeds'][key] = B.seed
    grid = gd.grid(world)
    spots = deck_spots(ship, which)
    for tag, (p, arrive) in spots.items():
        c = grid.get((int(p[0] // 4096), int(p[1] // 4096)))
        if c is None:
            raise ValueError('Her deck is off the map.')
        name = tagged('deck_' + tag)
        ops.append({'op': 'add', 'cell': gd.key(c), 'base': gd.key(forms[spec['deck'][tag][0]]), 'p': p, 's': 1, 'name': name})
        places[('deck', tag)] = (gd.key(c), name, arrive[:3] + [arrive[5]], spec['to'][tag])
    own = {}
    for piece, lx, ly, lz, rx, ry, rz in spec.get('extras', ()):
        if piece not in own:
            more, info = modelsets.put(pr, piece)
            ops += more
            own[piece] = info['key'] or '$model_' + piece
        x, y = to_world(ship, lx, ly)
        c = grid.get((int(x // 4096), int(y // 4096)))
        if c is not None:
            ops.append({'op': 'add', 'cell': gd.key(c), 'base': own[piece],
                        'p': [round(x, 1), round(y, 1), round(ship[2] + lz, 1), rx, round(ry, 4), round((ship[3] + rz) % math.tau, 4)], 's': 1})
    rep['extras'] = len(spec.get('extras', ()))
    for (key, tag), (ck, name, _arrive, to) in places.items():
        _oc, oname, (x, y, z, rz), _t = places[to]
        ops.append({'op': 'tel', 'cell': ck, 'ref': '$' + name, 'tel': {'door': '$' + oname, 'p': [round(x, 2), round(y, 2), round(z, 2), 0.0, 0.0, round(rz % math.tau, 4)]}})
    rep['doors'] = len(places)
    rep['deck'] = {tag: v[1][:3] for tag, v in spots.items()}
    return ops, rep


def boat_walk(gd, tag):
    """(items, starts, goals) for walkcheck, in the ship's frame with the water at z 0: the planking ring, the hulk as
    flotilla stands it, the gangplank; from the planking beside the plank to where one arrives beside her hatch."""
    edid, y = BOATS[tag]
    water = -flotilla.SHIP_Z
    keys = {e: gd.key(f) for e, f in shipinside._forms(gd, {flotilla.DOCK, edid}).items()}
    items = [{'base': keys[e], 'pos': (x, yy, z), 'rot': (rx, ry, rz), 'scale': 1.0} for e, x, yy, z, rx, ry, rz in flotilla._ring()]
    items.append({'base': keys[edid], 'pos': (BOAT_X, y, flotilla.FLOAT[edid]), 'rot': (0.0, 0.03, 0.0), 'scale': 1.0})
    _door, (piece, px, py, pz, rx, ry, rz) = _boat(edid, y)
    items.append({'nif': modelsets.build(piece)['nif'], 'pos': (px, py, pz - water), 'rot': (rx, ry, rz), 'scale': 1.0})
    ax, ay, _f = _door[4]
    return items, [(flotilla.RING[0], y + PLANK_Y, flotilla.DOCK_TOP + 10.0)], [('the hatch of ' + tag, (ax, ay, _door[5] - water))]


def navmesh_ops(gd, pr, names, which='flotilla'):
    """After board's ops are applied (names: project.names as they left it): each place's navmesh as an op."""
    import navbuild
    out, rep = [], {}
    for key in SHIPS[which]['places']:
        ck = names.get('%s_%s' % (which[:2], key))
        if not ck:
            continue
        try:
            data, r = navbuild.generate(gd, pr, ck)
        except navbuild.NavError as e:
            rep[key] = str(e)
            continue
        out.append({'op': 'navmesh', 'cell': ck, 'mesh': data})
        rep[key] = r
    return out, rep
