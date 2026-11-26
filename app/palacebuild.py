"""The An dynasty's grand palace stood on Mōkapu (the user, 25 Nov 2026: site C, the Mōkapu peninsula; "5-6 stories tall
... something big and grand like that for the imperial palace, surrounded by a wall and court"; "Yes, build it" to the
pictures, the proposals with them): palaceset's pieces laid out as a walled compound facing south, on the flat band across
the peninsula south of its town (cells x 1-7, y 51-53: no doors, no people, a refugee camp's dressing and road junk).

- **Layout** (`LAYOUT`, in the compound's frame, y north): the gate tower in the south wall; the outer court with a side
  hall each side; the inner wall with its gate; the inner court with the Hall of Supreme Peace on its terrace, bronze
  cauldrons before it, side halls, and the five-storey tower behind it at `TOWER_SCALE` (~66 m to the finial); corner
  towers where the walls meet; stone lions outside each gate.
- **Ground:** made level at `level` (the ground's middle under the compound, in whole 8-unit steps) over the compound and
  `HOLD` past it, eased back over `EASE`; road pieces outside keep their ground.
- **Clearing:** everything standing inside the walls (and under the lions) is taken out, except doors, anything linked,
  named or a map marker (none stand there: `plan` says so); what stood on moved ground outside is carried with it.
- **A map marker**, "The An Palace", by the gate (found when seen).
- The pieces are the mod's own files and STATs (modelsets.put); the tower and halls have far versions (modelsets'
  auto far), so lodobj's distant blocks show them once made again.

    plan(gd, pr)            {'rows', 'skipped', 'site', 'level', 'clear', ...}: where, what goes, what's near
    walk(gd)                walkcheck's report for the whole compound (from its south: the gates, both courts, the throne)
    apply(pr, gd, P)        one Undo: files, records, ground, clearing, pieces, marker; the cells to navmesh in the report
"""
import math

import recordio

LABEL = "The An dynasty's palace on Mokapu"
SITE = (14500.0, 215700.0)              # (the compound's middle: the flat band south of Mōkapu's town)
X, Y = 5096.0, 6144.0                   # (half the walled court: the walls' middle lines)
INNER_Y = -2600.0
HALL_Y, TOWER_Y, TOWER_SCALE = 0.0, 3700.0, 1.4
HOLD, EASE = 700.0, 1400.0
MARKER = 'The An Palace'
CLEAR_PAST = 300.0                      # (things this far past the walls are taken out with what's inside)
KEEP_WORDS = ('door',)


def layout():
    """[(piece, x, y, turn degrees, scale)] in the compound's frame (y north, the gate south)."""
    L = [('an_gate', 0.0, -Y, 0.0, 1.0)]
    for sx in (-1, 1):
        for k in range(2):
            L.append(('an_wall', sx * (1000.0 + 1024.0 + 2048.0 * k), -Y, 0.0, 1.0))
    for k in range(5):
        L.append(('an_wall', -4096.0 + 2048.0 * k, Y, 0.0, 1.0))
    for sx in (-1, 1):
        for k in range(6):
            L.append(('an_wall', sx * X, -5120.0 + 2048.0 * k, 90.0, 1.0))
        for sy in (-1, 1):
            L.append(('an_corner', sx * X, sy * Y, 0.0, 1.0))
    L.append(('an_inner_gate', 0.0, INNER_Y, 0.0, 1.0))
    for sx in (-1, 1):
        for c in (1944.0, 3992.0):
            L.append(('an_wall', sx * c, INNER_Y, 0.0, 1.0))
    L.append(('an_throne_hall', 0.0, HALL_Y, 0.0, 1.0))
    L.append(('an_tower', 0.0, TOWER_Y, 0.0, TOWER_SCALE))
    for sx in (-1, 1):
        L.append(('an_side_hall', sx * 3900.0, -4400.0, 90.0 if sx < 0 else -90.0, 1.0))
        L.append(('an_side_hall', sx * 3900.0, 1300.0, 90.0 if sx < 0 else -90.0, 1.0))
        L.append(('an_cauldron', sx * 800.0, HALL_Y - 2150.0, 0.0, 1.3))
        L.append(('an_lion', sx * 800.0, -Y - 700.0, 0.0, 1.5))
        L.append(('an_lion', sx * 1300.0, INNER_Y - 450.0, 0.0, 1.3))
    return L


def _pieces():
    import palaceset  # noqa: F401  (registers its pieces with modelsets)
    import modelsets
    return modelsets


def _world_xy(x, y):
    return SITE[0] + x, SITE[1] + y


def _inside(x, y, past=CLEAR_PAST):
    lx, ly = x - SITE[0], y - SITE[1]
    if abs(lx) <= X + 320 + past and -Y - 320 - past <= ly <= Y + 320 + past:
        return True
    return abs(lx) <= 1400 and -Y - 1100 <= ly <= -Y                 # (the lions and the way up to the gate)


def walk(gd, voxel=32.0):
    """walkcheck over the whole compound as it stands, on flat ground: goals the outer court, the inner court, before the
    throne, the throne's dais, the tower's terrace, out through the gate."""
    import walkcheck
    M = _pieces()
    made = {}
    items = []
    for piece, x, y, turn, sc in layout():
        if piece not in made:
            made[piece] = M.build(piece)['nif']
        items.append({'nif': made[piece], 'pos': (x, y, 0.0), 'rot': (0.0, 0.0, -math.radians(turn)), 'scale': sc, 'label': piece})
    import palaceset as PS
    zf = 3 * 110 + 20                                   # (the hall's floor: three tiers and the floor slab)
    goals = [('the outer court', (0.0, -4400.0, 0.0)), ('the inner court', (2000.0, 1300.0, 0.0)),
             ('before the throne', (0.0, HALL_Y, zf)), ("the throne's dais", (0.0, HALL_Y + 1100.0 / 2 - 260.0, zf + 60.0)),
             ("the tower's terrace", (0.0, TOWER_Y - 1900.0 * TOWER_SCALE / 2 + 300.0, 140.0 * TOWER_SCALE)),
             ('outside the gate', (0.0, -Y - 1300.0, 0.0))]
    return walkcheck.walk(gd, items, ground=0.0, goals=goals, voxel=voxel)


def plan(gd, pr):
    """What's on the site: the ground's heights, what would be taken out (by kind), anything that must not be (doors,
    linked, named, markers, people), and what's near: the radio transmitter, Kāneʻohe, the checkpoints, the markers."""
    import collections
    import activity
    ctx = activity.Ctx(gd, pr)
    grid = gd.grid(ctx.world)
    hs = []
    import roadgen
    ground = roadgen.Ground(gd, pr, ctx.world)
    for x in range(int(-X), int(X) + 1, 512):
        for y in range(int(-Y), int(Y) + 1, 512):
            h = ground.at(*_world_xy(x, y))
            if h is not None:
                hs.append(h)
    hs.sort()
    level = math.floor(hs[len(hs) // 2] / 8.0) * 8.0 if hs else None
    out, blocked, kinds = [], [], collections.Counter()
    keys = {gd.key(c) for c in grid.values()}
    for ck, c in pr.cells.items():
        if ck not in keys:
            continue
        for rk, r in (c.get('refs') or {}).items():
            if r.get('removed') or not r.get('p') or not _inside(r['p'][0], r['p'][1]):
                continue
            e = ctx.edid_of(r.get('base', ''))
            t = _tag(gd, pr, r.get('base', ''))
            if t in ('DOOR', 'NPC_', 'CREA', 'LVLN', 'LVLC') or r.get('tel') or r.get('edid') or r.get('marker') or r.get('link') \
                    or any(w in e.lower() for w in KEEP_WORDS):
                blocked.append({'edid': e, 'type': t, 'p': [round(v) for v in r['p'][:3]], 'ref': r.get('edid', '')})
            else:
                out.append((ck, rk))
                kinds[e] += 1
    near = {}
    for n, (_c, p) in ctx.mk.items():
        d = math.hypot(p[0] - SITE[0], p[1] - SITE[1])
        if d < 40000:
            near[n] = round(d)
    tx = next(((r['p'][0], r['p'][1]) for c in pr.cells.values() for rk, r in (c.get('refs') or {}).items() if rk == '+1240EC'), None)
    rows = [{'what': 'site', 'p': [round(v) for v in SITE], 'level': level, 'ground': [round(hs[0]), round(hs[-1])] if hs else None},
            {'what': 'taken out', 'count': len(out), 'kinds': kinds.most_common(25)},
            {'what': 'kept, must not be inside', 'blocked': blocked},
            {'what': 'near', 'markers': sorted(near.items(), key=lambda kv: kv[1])[:20],
             'radio transmitter': round(math.hypot(tx[0] - SITE[0], tx[1] - SITE[1])) if tx else None}]
    skipped = ['%s at %s' % (b['edid'], b['p']) for b in blocked]
    return {'rows': rows, 'skipped': skipped, 'level': level, 'clear': out, 'world': ctx.world, 'blocked': blocked}


def _tag(gd, pr, b):
    if b.startswith('+'):
        return (pr.records.get(b) or {}).get('type', '')
    try:
        return gd.forms[gd.from_key(b)][1].tag
    except Exception:
        return ''


def ground_ops(gd, pr, world, level):
    """(ops, {'land_cells', 'cells', 'carry'}): the land made level under the compound, eased back; road pieces
    outside keep their ground; things standing on moved ground outside the walls carried with it."""
    import guardtower
    import land
    import roadbed
    import tes4
    grid = gd.grid(world)
    heights, start = {}, {}

    def cell_h(cx, cy):
        if (cx, cy) not in heights:
            cell = grid.get((cx, cy))
            h = None
            if cell is not None:
                mine = pr.land.get(gd.key(cell))
                if mine:
                    h = list(mine['h'])
                else:
                    e = gd.land_at(world, cx, cy)
                    vh = dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1]))).get('VHGT') if e else None
                    h = list(land.heights_of(vh)) if vh else None
            heights[(cx, cy)] = h
            start[(cx, cy)] = list(h) if h else None
        return heights[(cx, cy)]

    def set_point(gx, gy, v):
        for cx in {gx // 32, (gx - 1) // 32}:
            for cy in {gy // 32, (gy - 1) // 32}:
                col, row = gx - cx * 32, gy - cy * 32
                if 0 <= col <= 32 and 0 <= row <= 32:
                    h = cell_h(cx, cy)
                    if h is not None:
                        h[row * 33 + col] = v

    def old_point(gx, gy):
        cx, cy = gx // 32, gy // 32
        cell_h(cx, cy)
        h = start.get((cx, cy))
        return h[(gy - cy * 32) * 33 + (gx - cx * 32)] if h else None
    flat = roadbed._flat_bases(gd, pr)
    held = set()
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            b, p = r.get('base'), r.get('p')
            if b in flat and p and not r.get('removed') and not _inside(p[0], p[1]):
                bx = flat[b]
                rad = math.hypot(max(abs(bx[0]), abs(bx[3])), max(abs(bx[1]), abs(bx[4]))) + 128
                for gy in range(int((p[1] - rad) // 128), int((p[1] + rad) // 128) + 2):
                    for gx in range(int((p[0] - rad) // 128), int((p[0] + rad) // 128) + 2):
                        held.add((gx, gy))
    wet = set()                             # (cells with water of their own: their ground left, or lowering it floods it)
    for (cx, cy), cell in grid.items():
        if (pr.water or {}).get(gd.key(cell)) is not None:
            wet.add((cx, cy))
    reach_x, reach_y = X + 320 + HOLD + EASE, Y + 320 + HOLD + EASE + 1100
    for gy in range(int((SITE[1] - reach_y) // 128), int((SITE[1] + reach_y) // 128) + 2):
        for gx in range(int((SITE[0] - reach_x) // 128), int((SITE[0] + reach_x) // 128) + 2):
            if (gx, gy) in held or any((cx, cy) in wet for cx in {gx // 32, (gx - 1) // 32} for cy in {gy // 32, (gy - 1) // 32}):
                continue
            lx, ly = gx * 128.0 - SITE[0], gy * 128.0 - SITE[1]
            dx = max(0.0, abs(lx) - (X + 320))
            south = -Y - 320 - (1100 if abs(lx) <= 1400 else 0)
            dy = max(0.0, ly - (Y + 320), south - ly)
            d = math.hypot(dx, dy)
            if d > HOLD + EASE:
                continue
            old = old_point(gx, gy)
            if old is None:
                continue
            if d <= HOLD:
                t = level
            else:
                u = (d - HOLD) / EASE
                u = u * u * (3 - 2 * u)
                t = level + (old - level) * u
            t = round(t / 8.0) * 8.0
            if abs(t - old) >= 1:
                set_point(gx, gy, t)
    out, land_cells = [], []
    for (cx, cy), h in sorted(heights.items()):
        if h and h != start[(cx, cy)]:
            k = gd.key(grid[(cx, cy)])
            form = dict(pr.land[k]) if pr.land.get(k) else land.decode(gd, gd.land_at(world, cx, cy), {})
            out.append({'op': 'land', 'cell': k, 'land': dict(form, h=[float(v) for v in h])})
            land_cells.append(k)
    after = guardtower._heights_ground(heights)
    before = guardtower._heights_ground(start)
    carried = 0
    for ck, c in pr.cells.items():
        for rk, q in (c.get('refs') or {}).items():
            qp = q.get('p')
            if not qp or q.get('removed') or _inside(qp[0], qp[1]) or q.get('tel'):
                continue
            was, now = before(qp[0], qp[1]), after(qp[0], qp[1])
            if was is None or now is None or abs(now - was) < 2 or abs(qp[2] - was) > 40:
                continue
            out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [qp[0], qp[1], round(qp[2] + now - was, 1)] + list(qp[3:])})
            carried += 1
    cells = sorted({gd.key(grid[(cx, cy)]) for (cx, cy) in heights if grid.get((cx, cy)) is not None})
    return out, {'land_cells': land_cells, 'cells': cells, 'carried': carried}


def ops(gd, pr, P=None):
    """(ops, report): one Undo."""
    import tes4
    M = _pieces()
    P = P or plan(gd, pr)
    if P['blocked']:
        raise ValueError('something that must stay stands on the site: %s' % P['skipped'][:5])
    if any(r.get('marker', {}).get('name') == MARKER for c in pr.cells.values() for r in (c.get('refs') or {}).values()):
        raise ValueError('the mod has the palace already (Undo first)')
    world = P['world']
    grid = gd.grid(world)
    level = P['level']
    out, rep = [], {'made': [], 'taken_out': len(P['clear']), 'level': level}
    bases = {}
    for piece in sorted({p for p, *_r in layout()}):
        o, info = M.put(pr, piece)
        out += o
        bases[piece] = info['key'] or '$model_' + piece
        rep['made'].append(info['edid'])
    out += [{'op': 'remove', 'cell': ck, 'ref': rk} for ck, rk in P['clear']]
    g_ops, g_rep = ground_ops(gd, pr, world, level)
    out += g_ops
    rep.update(g_rep)
    placed = 0
    for piece, x, y, turn, sc in layout():
        wx, wy = _world_xy(x, y)
        ck = gd.key(grid[(int(math.floor(wx / 4096.0)), int(math.floor(wy / 4096.0)))])
        out.append({'op': 'add', 'cell': ck, 'base': bases[piece], 'p': [round(wx, 1), round(wy, 1), float(level), 0.0, 0.0,
                    round(-math.radians(turn), 4)], 's': sc})
        placed += 1
    import piratedeal
    mx, my = _world_xy(0.0, -Y - 1600.0)
    mck = gd.key(grid[(int(math.floor(mx / 4096.0)), int(math.floor(my / 4096.0)))])
    out.append({'op': 'add', 'cell': mck, 'base': gd.key(piratedeal._game(gd, 'MapMarker', 'STAT')), 'p': [mx, my, float(level), 0.0, 0.0, 0.0],
                's': 1.0, 'extra': {'persistent': True, 'marker': {'name': MARKER, 'type': 0, 'flags': 2}}})
    rep['placed'] = placed
    return out, rep


def apply(pr, gd, P=None, navmesh=True):
    o, rep = ops(gd, pr, P)
    pr.apply(LABEL, o)
    if navmesh:                             # (the compound's cells and the ground eased round it: one Undo with the rest)
        import navbuild
        n_ops, n_rep = navbuild.generate_area(gd, pr, [c for c in rep['cells'] if navbuild.is_outside(gd, c)])
        pr.apply(LABEL, n_ops, merge=True)
        rep['navmesh'] = {k: n_rep[k] for k in ('cells', 'triangles', 'joined', 'neighbours', 'empty', 'seconds') if k in n_rep}
    return rep
