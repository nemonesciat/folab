"""Shanties on the ruined freeway (docs/waikiki-story-plan.md, build list 8a): two posts on the old H-1's broken decks
(ruinedfreeway.py's `OverpassSectionLo01` sections), the court's and the pirates', each watching the road the trade runs
on, the broken middle and the west end left empty.

The game's overpass collision reads with no level face to stand on (walkcheck and navgen find nothing there), so each
post stands on a platform of the game's dock planking (`DOCK`) laid on the deck, the drawn road surface `DECK_UP` over
the section's origin: what's walked on is then something walkcheck proves. A scaffold ramp tower of FOLab's own
(citypieces.ramp_tower) climbs from the ground beside the deck, its top landing reaching over the deck's side
(`OVER` over the road surface, so it clears the barrier) and a last ramp down onto the planking.

- `POSTS['court']`: the Kahuna's toll post at the mouth of Manoa valley: two shacks, a sandbag post at the deck's end
  looking up the valley, a table and chairs for the collectors, a lantern.
- `POSTS['pirates']`: the pirates' post over the Palolo junction near the Kahala Hotel: two shacks, a row of cages for
  the people held before the climb to the Vault, a fire, crates, lanterns.

`ops` returns (ops, report, cells); `walk_items` gives the walked parts for walkcheck."""
import math

import citypieces
import modelsets
import ridgeplaces
import shipinside
import townbuild

DECK_UP = 2048.0                 # (the drawn road surface over an OverpassSectionLo01's origin)
DOCK = 'PotDockBg4way01'
PLANK_UP = 8.0                   # (a dock piece's origin over the road: its planking 32 over that)
PLANK_TOP = PLANK_UP + 32.0
COLS = [-1495.0 + 230.0 * k for k in range(14)]
ROWS = (-575.0, -345.0, -115.0, 115.0, 345.0, 575.0)
FACE = 900.0                     # (the tower's face this far out from the deck's middle line: past its side)
OVER = 160.0                     # (the tower's top landing over the road surface)
POSTS = {
    'court': {'section': (-101619.4, 11308.1), 'things': [('WoodShack01', -900.0, 0.0, 280.0, 0.0), ('WoodShack01', 0.0, 0.0, 280.0, 0.0),
                                                           ('SandbagStraight', 1350.0, -250.0, 0.0, 0.0), ('SandbagStraight', 1350.0, 250.0, 0.0, 0.0),
                                                           ('Table02', 650.0, 300.0, 0.0, 0.0), ('Chair01', 650.0, 470.0, 0.0, 3.14),
                                                           ('Chair01', 760.0, 320.0, 0.0, 1.57), ('CrateGenericNV', 900.0, -400.0, 0.0, 0.4)]},
    'pirates': {'section': (-38234.7, -22820.6), 'things': [('WoodShack01', -1000.0, 0.0, 280.0, 0.0), ('WoodShack01', -150.0, 0.0, 280.0, 0.0),
                                                             ('DeathClawCage', 650.0, -330.0, 0.0, 0.0), ('DeathClawCage', 880.0, -330.0, 0.0, 0.0),
                                                             ('DeathClawCage', 1110.0, -330.0, 0.0, 0.0), ('CampfireCrafting03', 800.0, 300.0, 0.0, 0.0),
                                                             ('CrateGenericNV', 1250.0, 350.0, 0.0, 0.3), ('Barrel01', 1350.0, 150.0, 0.0, 0.0)]},
}
LANTERNS = [(-1450.0, 520.0), (1450.0, -520.0)]
NAMES = {DOCK, 'OverpassSectionLo01', 'Barrel03static', 'LLamp01', 'NVDLC04LanternLightKeyWarm'} | {t[0] for p in POSTS.values() for t in p['things']}


def _named(gd, pr, ck, rk):
    import natcompound
    r = pr.cells.get(ck, {}).get('refs', {}).get(rk)
    return natcompound._named(gd, pr, r['base']) if r and r.get('base') else ''


def to_world(x0, y0, rz, lx, ly):
    c, s = math.cos(rz), math.sin(rz)
    return x0 + lx * c + ly * s, y0 - lx * s + ly * c


def _section(gd, pr, world, near):
    key = gd.key(next(f for f in gd.forms if gd.edid(f) == 'OverpassSectionLo01'))
    best = None
    import shipplace
    for ck in shipplace.world_cells(gd, world):
        for rk, r in pr.cells.get(ck, {}).get('refs', {}).items():
            p = r.get('p')
            if p and r.get('base') == key and not r.get('removed'):
                d = math.hypot(p[0] - near[0], p[1] - near[1])
                if best is None or d < best[0]:
                    best = (d, p)
    return best[1] if best and best[0] < 600 else None


def plan(post, deck, ground_at, blocked):
    """[(piece, x, y, z, rx, ry, rz)] in the section's frame (z absolute), and the tower's (piece, real height, side,
    along). ground_at(lx, ly) -> the ground's height there (or None); blocked(lx, ly, r) -> True if something stands."""
    out = []
    for lx in COLS:
        for ly in ROWS:
            out.append((DOCK, lx, ly, deck + PLANK_UP, 0.0, 0.0, 0.0))
    top = deck + PLANK_TOP
    for e, lx, ly, up, rz in POSTS[post]['things']:
        out.append((e, lx, ly, top + up, 0.0, 0.0, rz))
    for lx, ly in LANTERNS:
        out += [('Barrel03static', lx, ly, top, 0.0, 0.0, 0.0), ('LLamp01', lx, ly, top + 90.0, 0.0, 0.0, 0.0),
                ('NVDLC04LanternLightKeyWarm', lx, ly, top + 140.0, 0.0, 0.0, 0.0)]
    # the tower: beside the deck, at whichever end and side has room, its face along the deck's side
    land = deck + OVER
    tower = None
    for along in (1100.0, -1100.0, 1450.0, -1450.0, 600.0, -600.0, 200.0, -200.0):
        for side in (1, -1):
            g = ground_at(along, side * (FACE + 300.0))
            if g is None or g < 4.0 or blocked(along, side * (FACE + 300.0), 420.0):
                continue
            name, real = citypieces.ramp_tower(land - g, drop=OVER - PLANK_TOP, tight=False)
            tower = (name, real, side, along, land)
            break
        if tower:
            break
    if tower:
        name, real, side, along, land = tower
        # (its +y towards the deck: the section's -y for a tower on its +y side)
        out.append(('$model_' + name, along, side * FACE, land - real, 0.0, 0.0, math.pi if side > 0 else 0.0))
    return out, tower


def ops(gd, pr, world, side, cat=None):
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    B = ridgeplaces.Builder(gd, pr, world, side, cat)
    keys = {e: gd.key(f) for e, f in shipinside._forms(gd, NAMES).items()}
    ops, rep, records = [], {}, []
    houses, house_ok = {b['key'] for b in cat}, [False]
    for post, spec in POSTS.items():
        p = _section(gd, pr, world, spec['section'])
        if not p:
            rep[post] = 'no section there'
            continue
        x0, y0, rz = p[0], p[1], p[5]
        deck = p[2] + DECK_UP

        def ground_at(lx, ly):
            return B.ground.at(*to_world(x0, y0, rz, lx, ly))

        def blocked(lx, ly, r):
            # (the section itself and its fallen chunks aren't in the way: its record's bounds are wider than it)
            x, y = to_world(x0, y0, rz, lx, ly)
            fp = [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
            return any(big and townbuild.overlap(fp, ofp) and not B.clearable(ck, rk) and not _named(gd, pr, ck, rk).startswith(('Overpass', 'RoadOverpass'))
                       and not (house_ok[0] and pr.cells[ck]['refs'][rk].get('base') in houses) for ck, rk, ofp, big, _o in B.w.near(fp))
        layout, tower = plan(post, deck, ground_at, blocked)
        if not tower:
            # (no free ground beside the deck: a city house gives way, taken out whole, its doors locked)
            house_ok[0] = True
            layout, tower = plan(post, deck, ground_at, blocked)
            house_ok[0] = False
            if tower:
                x, y = to_world(x0, y0, rz, tower[3], tower[2] * (FACE + 300.0))
                cut, crep = townbuild.crowding(gd, pr, world, cat, [(x, y, rz, -450.0, -450.0, 450.0, 450.0)], gap=60.0)
                ops += cut
                rep.setdefault('houses_taken', 0)
                rep['houses_taken'] += len(crep['buildings'])
        n = 0
        for e, lx, ly, z, rx, ry, lrz in layout:
            if e.startswith('$model_'):
                more, info = modelsets.put(pr, e[7:])
                records += more
                base = info['key'] or e
            else:
                base = keys.get(e)
            if not base:
                continue
            x, y = to_world(x0, y0, rz, lx, ly)
            ck = B.w.cell_at(x, y)
            ops.append({'op': 'add', 'cell': ck, 'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), rx, ry, round((rz + lrz) % math.tau, 4)], 's': 1})
            B.cells.add(ck)
            n += 1
        # (what grows or lies where the tower stands)
        if tower:
            x, y = to_world(x0, y0, rz, tower[3], tower[2] * (FACE + 300.0))
            b, clear = B.blocking([(x - 420, y - 420), (x + 420, y - 420), (x + 420, y + 420), (x - 420, y + 420)])
            B.take_out(clear)
        rep[post] = {'deck': round(deck), 'pieces': n, 'tower': tower and {'piece': tower[0], 'high': tower[1], 'side': tower[2], 'along': tower[3]}}
    return records + [o for o in B.ops if o['op'] == 'remove'] + ops, rep, sorted(B.cells)


def walk_items(gd, post, deck, tower):
    """(items, starts, goals) in the section's frame for walkcheck: the planking and the tower, the ground under the
    tower's foot as flat ground at its foot's height."""
    keys = {e: gd.key(f) for e, f in shipinside._forms(gd, {DOCK}).items()}
    layout, _t = plan(post, deck, lambda lx, ly: tower[4] - tower[1], lambda lx, ly, r: False)
    items = []
    for e, lx, ly, z, rx, ry, rz in layout:
        if e == DOCK:
            items.append({'base': keys[DOCK], 'pos': (lx, ly, z), 'rot': (rx, ry, rz), 'scale': 1.0})
        elif e.startswith('$model_'):
            items.append({'nif': modelsets.build(e[7:])['nif'], 'pos': (lx, ly, z), 'rot': (rx, ry, rz), 'scale': 1.0})
    return items, [(0.0, 0.0, deck + PLANK_TOP)]
