"""The Flotilla (docs/waikiki-story-plan.md: "boats lashed round a wreck, walkable", the biggest build), on the shallow
shelf off Koko Head where the plan's spot in the middle of Maunalua Bay is too deep for anything to lie on.

- **Her heart:** a captured cargo ship (settlerset's `settler_flotilla_ship`: the settlers' freighter's hull, her house
  amidships, blue-grey above her waterline, no hatches), settled on the bottom (`SHIP_Z`), her deck a few metres over the
  sea, stacked with shipping containers of FOLab's own (cargoset), one to three high, some knocked askew, a lane down
  her middle and across at each gangway; shacks on her stern deck, tents at her bow, washing, crates, lanterns.
- **Round her:** a ring of planking at the water (`RING`), gangplanks from it up through gaps in her bulwarks (`GANGS`),
  and rafts of barges at its ends, shacks and a guard tower on them.
- **Lashed alongside:** the big Lake Mead hulks (`HULKS`) outside the ring, with the old wreck among them; smaller
  boats and rowboats moored round, all floating at their waterlines (`FLOAT`: 19 Nov 2026 the moored boats had been
  stood at the Lake Mead harbour's depth and showed only their cabins).

`layout()` is the whole thing in its own frame (the ship along y, water at z 0): [(piece, x, y, z, rx, ry, rz)], a
piece a game editor ID or '$model_<own piece>'. `walk_items` gives what's walked on for walkcheck."""
import math

import landmarks

SHIP = 'settler_flotilla_ship'
SHIP_Z = -280.0                     # (her origin: settled on the shelf, her deck 240 over the water)
DECK = SHIP_Z + 520.0
HALF_BEAM, HALF_LONG = 640.0, 3850.0
RING = (1090.0, 4300.0)             # (the planking ring's half sides)
GANGS = (-1150.0, 850.0)            # (along her, where gangplanks come aboard both sides: her bulwarks' gaps)
GANG = 'NVDLC02RopeBridge03'
DOCK = landmarks.DOCK
DOCK_TOP = landmarks.DOCK_UP + 9.0  # (what's walked on, over the water)
FLOAT = {'Boat02a': 40.0, 'Boat02b': 40.0, 'Boat02d': 40.0, 'Boat03a': 12.0, 'Boat03b': 12.0, 'Boat03e': 12.0, 'Barge': -8.0,
         'Boat01a': -100.0, 'Boat01b': -100.0, 'dlc04boatwrecked01': -150.0}
HULKS = [('Boat01a', 1, -2900.0), ('dlc04boatwrecked01', 1, 0.0), ('Boat01b', 1, 2900.0),
         ('Boat01b', -1, -2900.0), ('Boat01a', -1, 0.0), ('Boat01b', -1, 2900.0)]
CARGO = ['cargo_red', 'cargo_blue', 'cargo_green', 'cargo_rust']
BLOCKS = ((-3100.0, 2), (1150.0, 2))       # (where a block of stacks starts along her, how many containers long)
COLUMNS = (-440.0, -262.0, 262.0, 440.0)   # (across her: a lane 400 wide down her middle stays clear)
NAMES = {GANG, DOCK, 'Barge', 'WoodShack01', 'WoodShack02', 'CLSoldiersTent01', 'VBitterSpringsClotheslineShort', 'NVGuardTower01',
         'CrateGenericNV', 'Barrel01', 'Barrel03static', 'LLamp01', 'NVDLC04LanternLightKeyWarm'} | set(FLOAT)


def _ring():
    out = []
    hx, hy = RING
    n = int(math.ceil(2 * hy / 230.0)) + 1
    for k in range(n):
        y = -hy + 2 * hy * k / (n - 1)
        for sx in (-1, 1):
            out.append((DOCK, sx * hx, y, landmarks.DOCK_UP, 0.0, 0.0, 0.0))
    n = int(math.ceil(2 * hx / 230.0)) + 1
    for k in range(1, n - 1):
        x = -hx + 2 * hx * k / (n - 1)
        for sy in (-1, 1):
            out.append((DOCK, x, sy * hy, landmarks.DOCK_UP, 0.0, 0.0, math.pi / 2))
    return out


def _gangs(tilt=-1.0):
    """Rope-bridge gangplanks from the ring up to her deck, through her bulwarks' gaps, both sides."""
    out = []
    x_deck = HALF_BEAM - 80.0
    for y in GANGS:
        for sx in (-1, 1):
            x0, x1 = sx * RING[0], sx * x_deck
            rise, run = DECK - DOCK_TOP, abs(x1 - x0)
            out.append((GANG, (x0 + x1) / 2, y, (DECK + DOCK_TOP) / 2 - 100.0, 0.0, tilt * sx * math.atan2(rise, run), 0.0))
    return out


def _rafts():
    """Barges in rafts at each end of the ring: three across, two deep, butted to the planking."""
    out = []
    for sy in (-1, 1):
        for row in range(2):
            for col in (-1, 0, 1):
                out.append(('Barge', col * 400.0, sy * (RING[1] + 240.0 + 450.0 * row), FLOAT['Barge'], 0.0, 0.0, 0.0))
    return out


def _fits(x, y, turn, settlerset, clear=60.0):
    """A container at x, y turned by up to `turn` stays inside her bulwarks (their inner face, less `clear`) all along."""
    import cargoset
    for t in (-turn, turn) if turn else (0.0,):
        c, s = math.cos(t), math.sin(t)
        for lx in (-cargoset.WIDE / 2, cargoset.WIDE / 2):
            for ly in (-cargoset.LONG / 2, cargoset.LONG / 2):
                px, py = x + lx * c + ly * s, y - lx * s + ly * c
                st = min(1.0, max(0.0, (py + HALF_LONG) / (2 * HALF_LONG)))
                if abs(px) > settlerset.f_width(st) - 26.0 - clear:
                    return False
    return True


def layout():
    out = [('$model_' + SHIP, 0.0, 0.0, SHIP_Z, 0.0, 0.0, 0.0)]
    # (the deck's things first known, so the walk test sees the containers too)
    out += _ring() + _gangs() + _rafts()
    barge_top = FLOAT['Barge'] + 53.0
    # on the rafts: a shack at the bow end, the guard tower at the stern end
    out.append(('WoodShack02', 0.0, -(RING[1] + 465.0), barge_top + 4.0, 0.0, 0.0, math.pi / 2))   # (across the raft: it's 1,146 long)
    out.append(('NVGuardTower01', 0.0, RING[1] + 465.0, barge_top + 23.0, 0.0, 0.0, math.pi))
    # the hulks alongside, outside the ring; boats moored round them; rowboats beyond
    for e, sx, y in HULKS:
        out.append((e, sx * (RING[0] + 130.0 + 345.0), y, FLOAT[e], 0.0, 0.03 * sx, 0.0))
    for k, y in enumerate((-4000.0, -1500.0, 1500.0, 4000.0)):
        for sx in (-1, 1):
            e = ('Boat02a', 'Boat02b', 'Boat02d', 'Boat02a')[k]
            out.append((e, sx * (RING[0] + 1000.0 + 180.0 * (k % 2)), y, FLOAT[e], 0.0, 0.0, (0.15 if sx > 0 else -0.15) * (k - 1.5)))
    for k, (x, y) in enumerate(((-2600.0, -5400.0), (2500.0, -5100.0), (-2800.0, 5300.0), (2400.0, 5600.0), (0.0, -6000.0), (300.0, 6100.0))):
        e = ('Boat03a', 'Boat03b', 'Boat03e')[k % 3]
        out.append((e, x, y, FLOAT[e], 0.0, 0.0, k * 1.1))
    # her deck: two blocks of shipping containers in stacks, a lane down her middle and across at each gangway;
    # shacks on her stern deck, tents at her bow, washing at the gangways, crates and barrels by her house
    import cargoset
    import settlerset
    k = 0
    for y0, n in BLOCKS:
        for j in range(n):
            y = y0 + cargoset.LONG * (j + 0.5)
            for c, x in enumerate(COLUMNS):
                askew_ok = abs(x) < 350.0                     # (only the inner stacks knocked askew: an outer one's end went over her side)
                if not _fits(x, y, 0.12 if askew_ok else 0.0, settlerset):
                    k += 1
                    continue                                 # (her hull narrows to the bow: 19 Nov 2026 the outer stacks stood through her sides)
                high = 1 + (k * 7 + c * 3 + j) % 3
                for level in range(high):
                    askew = 0.12 * ((-1) ** (k + level)) if askew_ok and level == high - 1 and (k + c) % 4 == 0 else 0.0
                    out.append(('$model_' + CARGO[(k + c + level) % len(CARGO)], x, y, DECK + level * cargoset.HIGH, 0.0, 0.0, askew))
                k += 1
    for y in (3050.0, 3450.0):
        out.append(('WoodShack01', 0.0, y, DECK + 280.0, 0.0, 0.0, math.pi / 2))
    for k, y in enumerate((-3300.0, -3550.0)):
        out.append(('CLSoldiersTent01', (-1) ** k * 180.0, y, DECK, 0.0, 0.0, 0.0))
    for y in (-1150.0, 850.0):
        out.append(('VBitterSpringsClotheslineShort', -360.0, y + 160.0, DECK, 0.0, 0.0, math.pi / 2))
    for k, (x, y) in enumerate(((-420.0, -700.0), (420.0, -700.0), (-430.0, 600.0), (430.0, 600.0), (380.0, -1300.0), (-380.0, 1000.0))):
        out.append((('CrateGenericNV', 'Barrel01')[k % 2], x, y, DECK, 0.0, 0.0, k * 0.7))
    # lanterns: the ring's corners and her deck's ends
    for x, y, z in [(sx * (RING[0] - 40.0), sy * (RING[1] - 40.0), DOCK_TOP) for sx in (-1, 1) for sy in (-1, 1)] + [(0.0, -2150.0, DECK), (0.0, 1850.0, DECK)]:
        out.append(('Barrel03static', x, y, z, 0.0, 0.0, 0.0))
        out.append(('LLamp01', x, y, z + 90.0, 0.0, 0.0, 0.0))
        out.append(('NVDLC04LanternLightKeyWarm', x, y, z + 140.0, 0.0, 0.0, 0.0))
    return out


def walk_items(gd, nifs):
    """(items, starts, goals) for walkcheck: the ship and her containers (nifs: {own piece: its mesh's bytes}), the
    ring, the gangplanks, the rafts."""
    import shipinside
    keys = {e: gd.key(f) for e, f in shipinside._forms(gd, NAMES).items()}
    items = []
    for e, x, y, z, rx, ry, rz in layout():
        if e.startswith('$model_'):
            items.append({'nif': nifs[e[7:]], 'pos': (x, y, z), 'rot': (rx, ry, rz), 'scale': 1.0})
    for e, x, y, z, rx, ry, rz in _ring() + _gangs() + _rafts():
        items.append({'base': keys[e], 'pos': (x, y, z), 'rot': (rx, ry, rz), 'scale': 1.0})
    goals = [('her deck, forward', (0.0, -1150.0, DECK)), ('her deck, aft', (0.0, 850.0, DECK)), ('the bow raft', (0.0, -(RING[1] + 465.0), FLOAT['Barge'] + 53.0)),
             ('the stern raft', (0.0, RING[1] + 465.0, FLOAT['Barge'] + 53.0))]
    return items, [(RING[0], 0.0, DOCK_TOP + 10.0)], goals
