"""The Natatorium compound (docs/waikiki-lore-additions.md: a fortress enclave, the ship on top of that): a wall of the
game's scrap and sandbags round the Natatorium and its grounds, Kapiʻolani Park cleared before it, trees screening it from
the city.

    the wall    in the Natatorium's frame: a leg each side at x = ±`LEG` from the sea up to `FRONT`, and the front between
                them, of the game's junk walls (sheet metal, 500 long) end to end, each at the lowest ground under it
                (so none hangs), sandbags along the outside of every third, a rubble bank at the foot of every fifth;
                a gate `GATE` wide in the front's middle, sandbags turned in at its sides. A road it would cross keeps
                its way: the wall stops either side of it, sandbags at the ends (a checkpoint). Nothing stands in the sea
                or on a building.
    the park    before the front, out to `CLEAR` (across `CLEAR_WIDE`): what grows and what lies about taken out, so
                nobody comes up unseen, but for the `KEEP` biggest trees at least `KEEP_APART` apart (the banyans the
                garrison keeps as lookouts), each grown to look its age.
    the screen  a belt of trees just outside the leg toward the city (the Natatorium's -x: on Waikiki the north), and
                the front's half on that side: ironwoods (the game's cypresses, tall and dark) and banyans by turns.

`ops` gives one Undo's ops, a report and the cells whose navmeshes are to be made again."""
import math
import random

import roadgen
import shipway
import townbuild

LEG, FRONT, SEA_FROM = 3000.0, 2400.0, -1600.0
GATE = 700.0
JUNK = ('NVJunkWall03', 'NVJunkWall04')     # (along their y, 495 long, 219 tall)
JUNK_LONG = 490.0
SANDBAG, SANDBAG_TURN = 'SandbagStraight', 'Sandbag90degrees'
RUBBLE = ('IndRubblePileReg01', 'SuburbanRubblePileReg02')
CLEAR, CLEAR_WIDE = 4800.0, 4800.0
KEEP, KEEP_APART, KEEP_GROW = 4, 1500.0, 1.35
SCREEN_OUT, SCREEN_STEP = 450.0, 420.0
IRONWOOD = ('NVItalianCypress01', 'NVItalianCypress02')
BANYAN = ('NVDLC02TreeA1', 'NVDLC02TreeA3', 'NVDLC02TreeB1')
ROAD_WORDS = ('WastelandRoad',)
GROWS = ('Palm', 'Tree', 'Bush', 'Fern', 'Grass', 'Ficus', 'Sassafras', 'Birch', 'Cypress', 'Juniper', 'Oak', 'Banana', 'Aloe',
         'Frailejon', 'Euonymus', 'Spirea', 'Fungus', 'Datura', 'Pickable', 'Plant', 'Leaves', 'Shrub', 'Weed', 'Sago')
LIES = ('Rubble', 'Litter', 'Debris', 'Tire', 'Trash', 'Rock', 'Car', 'Wreck', 'Barrel', 'Crate', 'Pallet')


def _forms(gd, edids):
    return shipway._forms(gd, edids)


def _named(gd, pr, key):
    """The editor ID a placed thing's base goes by (the mod's own green twins go by the game tree they copy)."""
    if key.startswith('+'):
        import recordio
        rec = pr.records.get(key)
        return (recordio.field(rec, 'EDID') or '') if rec else ''
    try:
        return gd.edid(gd.from_key(key)) or ''
    except (KeyError, ValueError):
        return ''


def ops(gd, pr, world, seed=7):
    """(ops, report, cells)."""
    nat = shipway.natatorium(gd, pr, world)
    if not nat:
        raise ValueError("The Natatorium isn't in this world of the mod.")
    p = nat[2]
    pose = (p[0], p[1], p[2], p[5])
    grid = gd.grid(world)
    ground = roadgen.Ground(gd, pr, world)
    rnd = random.Random(seed)
    city = {gd.key(c) for c in grid.values()}
    found = _forms(gd, JUNK + (SANDBAG, SANDBAG_TURN) + RUBBLE + IRONWOOD + BANYAN)
    found = {e: gd.key(f) for e, f in found.items()}
    import recordio
    for k_, rec in pr.records.items():                      # (the mod's green twins of the game's trees, where it has them)
        e = recordio.field(rec, 'EDID') or '' if k_.startswith('+') else ''
        if e.startswith('FOLabGreen') and 'NVDLC02' + e[len('FOLabGreen'):] in BANYAN:     # (greener.py's names)
            found['NVDLC02' + e[len('FOLabGreen'):]] = k_
    out, cells = [], set()
    rep = {'wall': 0, 'sandbags': 0, 'rubble': 0, 'road_gaps': 0, 'on_buildings': 0, 'cleared': 0, 'kept': 0, 'screen': 0}
    cat = {b['key'] for b in townbuild.load(gd, __import__('server').kits_folder())}

    def cell_at(x, y):
        c = grid.get((int(x // 4096), int(y // 4096)))
        return gd.key(c) if c is not None else None

    def add(edid, x, y, z, rz, s=1.0):
        ck = cell_at(x, y)
        if ck is None or edid not in found:
            return False
        out.append({'op': 'add', 'cell': ck, 'base': found[edid], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)], 's': round(s, 3)})
        cells.add(ck)
        return True
    # what stands round it: roads and buildings (refs in the cells round the compound)
    roads, blds, things = [], [], []
    reach = max(LEG, CLEAR_WIDE) + FRONT + CLEAR + 2000
    for ck, c in pr.cells.items():
        if ck not in city:
            continue
        for rk, r in c['refs'].items():
            q = r.get('p')
            b = r.get('base')
            if not q or r.get('removed') or not b or math.hypot(q[0] - p[0], q[1] - p[1]) > reach:
                continue
            e = _named(gd, pr, b)
            if any(e.startswith(w) for w in ROAD_WORDS):
                roads.append(q)
            elif b in cat:
                o = townbuild.obnd(gd, b)
                if o:
                    blds.append((q, float(r.get('s') or 1.0), o))
            things.append((ck, rk, r, e))

    def on_road(x, y, pad=420.0):
        return any(math.hypot(q[0] - x, q[1] - y) < pad for q in roads)

    def on_building(x, y, pad=120.0):
        for q, s, o in blds:
            lx, ly = shipway.local_of((q[0], q[1], 0, q[5]), x, y)
            if o[0] * s - pad <= lx <= o[3] * s + pad and o[1] * s - pad <= ly <= o[4] * s + pad:
                return True
        return False

    def low(x0, y0, x1, y1):
        gs = [ground.at(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
        return None if any(g is None for g in gs) else min(gs)
    # ----- the wall -----
    legs = [((LEG, SEA_FROM), (LEG, FRONT)), ((LEG, FRONT), (GATE / 2, FRONT)), ((-GATE / 2, FRONT), (-LEG, FRONT)), ((-LEG, FRONT), (-LEG, SEA_FROM))]
    k = 0
    for (ax, ay), (bx, by) in legs:
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L // JUNK_LONG))
        ux, uy = (bx - ax) / L, (by - ay) / L
        open_end = None
        for i in range(n):
            t0, t1 = i * JUNK_LONG, (i + 1) * JUNK_LONG
            x0, y0 = shipway.world_of(pose, ax + ux * t0, ay + uy * t0)
            x1, y1 = shipway.world_of(pose, ax + ux * t1, ay + uy * t1)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            g = low(x0, y0, x1, y1)
            if g is None or g < 4.0:
                continue                                    # (the sea)
            if on_road(mx, my):
                if open_end != 'road':
                    rep['road_gaps'] += 1
                    add(SANDBAG_TURN, x0, y0, low(x0, y0, x0, y0) or g, math.atan2(x1 - x0, y1 - y0) + math.pi)
                open_end = 'road'
                continue
            if on_building(mx, my):
                rep['on_buildings'] += 1
                open_end = 'building'
                continue
            if open_end == 'road':
                add(SANDBAG_TURN, x0, y0, g, math.atan2(x1 - x0, y1 - y0))
            open_end = None
            rz = math.atan2(x1 - x0, y1 - y0)
            add(JUNK[k % 2], mx, my, g, rz + (math.pi if rnd.random() < 0.5 else 0.0))
            rep['wall'] += 1
            # (outside: the side away from the Natatorium's middle)
            lmx, lmy = ax + ux * (t0 + t1) / 2, ay + uy * (t0 + t1) / 2
            nx, ny = (uy, -ux)
            if nx * lmx + ny * lmy < 0:
                nx, ny = -nx, -ny
            if k % 3 == 0:
                ox, oy = shipway.world_of(pose, lmx + nx * 110, lmy + ny * 110)
                go = ground.at(ox, oy)
                if go is not None and go >= 4.0 and not on_road(ox, oy, 300):
                    add(SANDBAG, ox, oy, go - 4, rz)
                    rep['sandbags'] += 1
            if k % 5 == 2:
                ox, oy = shipway.world_of(pose, lmx + nx * 260, lmy + ny * 260)
                go = ground.at(ox, oy)
                if go is not None and go >= 4.0 and not on_road(ox, oy, 450) and not on_building(ox, oy):
                    add(RUBBLE[k % 2], ox, oy, go - 10, rz + rnd.uniform(-0.4, 0.4), rnd.uniform(0.8, 1.1))
                    rep['rubble'] += 1
            k += 1
    for sx in (-1, 1):                                       # (the gate's sides)
        gx, gyw = shipway.world_of(pose, sx * (GATE / 2 + 40), FRONT + 60)
        g = ground.at(gx, gyw)
        if g is not None:
            add(SANDBAG_TURN, gx, gyw, g - 4, pose[3] + (0 if sx > 0 else math.pi))
    # ----- the park cleared, but for the great trees -----
    trees, gone = [], []
    for ck, rk, r, e in things:
        q = r['p']
        lx, ly = shipway.local_of(pose, q[0], q[1])
        if not (FRONT + 120 < ly < FRONT + CLEAR and abs(lx) < CLEAR_WIDE):
            continue
        if r.get('base') in cat or any(e.startswith(w) for w in ROAD_WORDS) or r.get('marker') or r.get('tel'):
            continue
        grows = any(w.lower() in e.lower() for w in GROWS)
        lies = any(w.lower() in e.lower() for w in LIES)
        if not (grows or lies):
            continue
        if grows and ('Tree' in e or 'Ficus' in e or 'Oak' in e or 'Sassafras' in e or 'Birch' in e):
            o = townbuild.obnd(gd, r['base']) if not r['base'].startswith('+') else None
            hgt = (o[5] if o else 600.0) * float(r.get('s') or 1.0)
            trees.append((hgt, ck, rk, r))
        gone.append((ck, rk))
    trees.sort(key=lambda t: -t[0])
    kept = []
    for hgt, ck, rk, r in trees:
        if len(kept) >= KEEP:
            break
        if all(math.hypot(r['p'][0] - k_[3]['p'][0], r['p'][1] - k_[3]['p'][1]) >= KEEP_APART for k_ in kept):
            kept.append((hgt, ck, rk, r))
    keep_keys = {(ck, rk) for _h, ck, rk, _r in kept}
    for ck, rk in gone:
        if (ck, rk) not in keep_keys:
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            cells.add(ck)
            rep['cleared'] += 1
    for _h, ck, rk, r in kept:
        out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': r['p'], 's': round(float(r.get('s') or 1.0) * KEEP_GROW, 3)})
        rep['kept'] += 1
    rep['lookouts'] = [[round(v) for v in r['p'][:3]] for _h, _c, _k, r in kept]
    # ----- the screen toward the city -----
    sx = -1
    line = [((sx * (LEG + SCREEN_OUT), SEA_FROM), (sx * (LEG + SCREEN_OUT), FRONT + SCREEN_OUT)),
            ((sx * (LEG + SCREEN_OUT), FRONT + SCREEN_OUT), (sx * (GATE / 2 + 300), FRONT + SCREEN_OUT))]
    j = 0
    for (ax, ay), (bx, by) in line:
        L = math.hypot(bx - ax, by - ay)
        for i in range(int(L // SCREEN_STEP) + 1):
            t = i * SCREEN_STEP + rnd.uniform(-60, 60)
            lx, ly = ax + (bx - ax) * t / L + rnd.uniform(-90, 90), ay + (by - ay) * t / L + rnd.uniform(-90, 90)
            x, y = shipway.world_of(pose, lx, ly)
            g = ground.at(x, y)
            if g is None or g < 8.0 or on_road(x, y, 380) or on_building(x, y, 200):
                continue
            if j % 3 == 2:
                add(BANYAN[j % len(BANYAN)], x, y, g - 8, rnd.uniform(0, math.tau), rnd.uniform(1.6, 2.1))
            else:
                add(IRONWOOD[j % 2], x, y, g - 8, rnd.uniform(0, math.tau), rnd.uniform(1.3, 1.7))
            rep['screen'] += 1
            j += 1
    return out, rep, sorted(cells)
