"""A way aboard the ship othergame stands in the sea, and a base inside it.

The carrier is statics: a hull with a flight deck a long way over the water, door frames with nothing in them, nothing
behind any of it. This makes it somewhere to go:

    a pier      the game's dock pieces from the nearest shore straight out to the hull's side, level all the way, its
                land end run up the beach into the sand (as landmarks.harbour ends its piers)
    a hull door one of the ship's own door frames against the hull where the pier meets it, the game's bulkhead door in it
    the base    a copy of one of the game's own places behind that door (townbuild.inside_ops, as hotels get theirs):
                Nellis's mess hall and munitions store, a hangar of the same steel the ship is. The game's Rivet City
                pieces would be the first choice, but New Vegas holds only its corridors (six hall pieces, a few wall
                ends, one door): no floor or room piece, so the kit planner has nothing to make a hall of.
                The workbench and reloading benches stand where the game has them (inside_ops leaves scripted things
                out; these two are put back: their script is what they are for), the bunks are there to sleep in, and
                the lockers by the bunks become containers of the mod's own that never refill: safe to keep things in
    a deck door the place's second way out leads up to a door frame on the flight deck, so the deck is reached through
                the ship; the other frames get the same door, locked, so none stands open on nothing
    a marker    on the map, at the pier's land end, to travel to

`board` returns (ops, report) for one Undo; `navmesh_ops` after they are applied gives the place its navmesh (the
game's own, since everything stands where the game has it), to apply with merge=True.

Not done here: the sea cells the pier crosses have no navmesh, so nobody but the player walks the pier."""
import math
import re

import hkshape
import landmarks
import recordio
import roadgen
import townbuild
import worldrec

HULL = 'RCExtAirCarrier01'
FRAME = 'RCRmLgDoorFrameExt01'
DOOR = 'RCSmDoor01'
INSIDE = 'NellisHangar2'
PLACE = ('ShipHangar', 'Carrier Hangar Deck')
MARKER = ('Aircraft Carrier', 8)        # (its name on the map; 8: the military sign)
PIER_MOST = 5200.0          # (no pier longer than this: the ship stands too far out)
MIDDLE = 0.2                # (the hull door keeps this share of the hull's length clear of each end)
WALL_HIGH = (40.0, 130.0, 220.0)    # (over the water: where the hull's side must be one flat wall for a door to stand on it)
WALL_FLAT = 12.0
FRAME_HALF = 170.0
FRAME_OFF = 4.0             # (the frame's back is this far behind its origin: it stands that far off the wall)
DOOR_IN_FRAME = (0.0, 4.0, 0.0, -math.pi / 2)   # (where the ship's own game stands a door in this frame; the leaf a quarter turn from the frame, as New Vegas stands this door in its own frames)
OUT = 110.0                 # (how far out of a door one arrives)
DECK_DROP = 8.0             # (one arrives this far over a frame's foot, and no further than twice it over the deck)
DECK_UP = 760.0             # (the flight deck's frames stand this far over the hull's origin; the one higher is the tower's top)
BENCHES = ('WorkBench', 'ReloadingBench')
STORE = re.compile(r'footlocker|locker|cabinet')
STORE_NEAR = 450.0          # (containers this near a bed become the mod's own)
NO_REFILL = ('CNTO', 'COED', 'SCRI', 'XOWN')
RESPAWNS = 0x02
SEAM = 4.0                  # (a slit this wide between two pieces is nothing to a walker)


class NoWay(ValueError):
    """Why not, in words for the person asking."""


def _own(pr, edid, rtype=None):
    for key, rec in pr.records.items():
        if key.startswith('+') and (rtype is None or rec.get('type') == rtype) and recordio.field(rec, 'EDID') == edid:
            return key
    return None


def _bases(gd, edids):
    """The game's records by editor ID, found in one pass: {editor ID: form or None}."""
    want = {e.lower(): e for e in edids}
    out = dict.fromkeys(edids)
    for f, (_i, r) in gd.forms.items():
        if r.tag in ('STAT', 'DOOR'):
            e = want.get(gd.edid(f).lower())
            if e:
                out[e] = f
    return out


def ship(pr, prefix='FOLab'):
    """The ship's pieces as they stand in the mod: {editor ID without the prefix: [(place: x, y, z, rx, ry, rz; scale; model)]}."""
    out = {}
    start = prefix + 'RC'
    for c in pr.cells.values():
        for r in c['refs'].values():
            rec = pr.records.get(r.get('base') or '')
            if rec and not r.get('removed') and (recordio.field(rec, 'EDID') or '').startswith(start):
                out.setdefault(recordio.field(rec, 'EDID')[len(prefix):], []).append((r['p'], r.get('s', 1.0), recordio.field(rec, 'MODL')))
    return out


def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def _solid(gd, model):
    """A model's solid collision as triangles in its own frame: [((x, y, z), (x, y, z), (x, y, z))]."""
    out = []
    for sh in hkshape.collision_shapes(gd.read_file('meshes\\' + model)):
        if sh['layer'] in hkshape.LAYERS_SOLID:
            v, i = sh['v'], sh['i']
            for k in range(0, len(i) - 2, 3):
                out.append(tuple(tuple(v[i[k + a] * 3:i[k + a] * 3 + 3]) for a in range(3)))
    return out


def footing(gd, got, x, y, z):
    """The highest of the ship's collision under a spot (not over z), or None: what someone arriving there lands on.
    got: ship(pr)."""
    best = None
    for rows in got.values():
        for q, s, model in rows:
            try:
                tris = _solid(gd, model)
            except Exception:
                continue
            lx, ly = _turn(x - q[0], y - q[1], -q[5])
            lx, ly = lx / s, ly / s
            for a, b, c in tris:
                if (a[0] > lx and b[0] > lx and c[0] > lx) or (a[0] < lx and b[0] < lx and c[0] < lx) or (a[1] > ly and b[1] > ly and c[1] > ly) or (a[1] < ly and b[1] < ly and c[1] < ly):
                    continue
                d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(d) < 1e-9:
                    continue
                u = ((b[1] - c[1]) * (lx - c[0]) + (c[0] - b[0]) * (ly - c[1])) / d
                v = ((c[1] - a[1]) * (lx - c[0]) + (a[0] - c[0]) * (ly - c[1])) / d
                if u < 0 or v < 0 or u + v > 1:
                    continue
                h = q[2] + (u * a[2] + v * b[2] + (1 - u - v) * c[2]) * s
                if h <= z + 1.0 and (best is None or h > best):
                    best = h
    return best


class Side:
    """The hull's two long sides, read from its collision in its own frame: where a level line across the ship first
    meets it, coming from outside."""

    def __init__(self, tris):
        xs = [p[0] for t in tris for p in t]
        ys = [p[1] for t in tris for p in t]
        self.long = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
        a = xs if self.long == 0 else ys
        self.lo, self.hi = min(a), max(a)
        L, c = self.long, 1 - self.long
        self.tris = [((t[0][L], t[0][2], t[0][c]), (t[1][L], t[1][2], t[1][c]), (t[2][L], t[2][2], t[2][c])) for t in tris]

    def wall(self, along, z, side):
        """How far across the hull's side is at this station and height, on side +1 or -1, or None."""
        best = None
        for (a0, z0, c0), (a1, z1, c1), (a2, z2, c2) in self.tris:
            if (a0 > along and a1 > along and a2 > along) or (a0 < along and a1 < along and a2 < along) or (z0 > z and z1 > z and z2 > z) or (z0 < z and z1 < z and z2 < z):
                continue
            d = (z1 - z2) * (a0 - a2) + (a2 - a1) * (z0 - z2)
            if abs(d) < 1e-9:
                continue
            u = ((z1 - z2) * (along - a2) + (a2 - a1) * (z - z2)) / d
            v = ((z2 - z0) * (along - a2) + (a0 - a2) * (z - z2)) / d
            if u < -1e-6 or v < -1e-6 or u + v > 1 + 1e-6:
                continue
            c = u * c0 + v * c1 + (1 - u - v) * c2
            if best is None or c * side > best * side:
                best = c
        return best

    def flat(self, along, low, side):
        """The wall's place if the hull's side is one upright wall round this station, wide and high enough for a door, or None."""
        hits = [self.wall(along + da, low + dz, side) for da in (-FRAME_HALF, 0.0, FRAME_HALF) for dz in WALL_HIGH]
        if any(h is None for h in hits) or max(hits) - min(hits) > WALL_FLAT:
            return None
        return max(hits) if side > 0 else min(hits)

    def local(self, along, across):
        return (along, across) if self.long == 0 else (across, along)


def _safe(gd, pr, fid, prefix):
    """A container of the mod's own like the game's: nothing in it, nothing that refills it, nobody's. (a record to make, its editor ID)"""
    rec = recordio.load(gd, fid)
    edid = prefix + 'Ship' + recordio.field(rec, 'EDID')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in NO_REFILL]
    recordio.set_field(rec, 'EDID', edid)
    recordio.set_field(rec, 'FULL', 'Your ' + (recordio.field(rec, 'FULL') or 'Locker'), label='Name')
    for s in rec['subs']:
        if s['tag'] == 'DATA' and s.get('kind') == 'struct':
            for f in s['fields']:
                if f['name'] == 'Flags':
                    f['value'] = int(f['value']) & ~RESPAWNS
    return rec, edid


def board(gd, pr, world, prefix='FOLab', inside=INSIDE):
    """(ops, report): the pier, the hull door, the base behind it, the door up to the flight deck, the marker. The ship
    must stand in the mod already (othergame.stand). Raises NoWay with the reason when it can't be done."""
    got = ship(pr, prefix)
    if HULL not in got:
        raise NoWay('There is no ship in this mod to go aboard.')
    if _own(pr, prefix + PLACE[0], 'CELL'):
        raise NoWay('This ship already has its way aboard.')
    found = _bases(gd, (DOOR, landmarks.DOCK, landmarks.PYLON[0]))
    door_fid, dock, pylon = found[DOOR], found[landmarks.DOCK], found[landmarks.PYLON[0]]
    place = townbuild.grand_inside(gd, inside)
    if door_fid is None or dock is None or not place:
        raise NoWay('The game files lack what this is built of (%s).' % ', '.join(n for n, v in ((DOOR, door_fid), (landmarks.DOCK, dock), (inside, place)) if not v))
    door_key = gd.key(door_fid)
    (hx, hy, hz, _rx, _ry, hrz), hs, model = got[HULL][0]
    ground = roadgen.Ground(gd, pr, world)
    grid = gd.grid(world)
    water = ground.water(hx, hy) or 0.0
    deck = water + landmarks.DECK

    def cell_at(x, y):
        c = grid.get((int(x // 4096), int(y // 4096)))
        return gd.key(c) if c is not None else None

    # ----- where: the stretch of flat hull side nearest a shore -----
    side = Side(_solid(gd, model))
    low = (water - hz) / hs

    def spot(along, across):
        lx, ly = side.local(along, across)
        tx, ty = _turn(lx * hs, ly * hs, hrz)
        return hx + tx, hy + ty

    def shore(x, y, nx, ny):
        d = 0.0
        while d <= PIER_MOST:
            g = ground.at(x + nx * d, y + ny * d)
            if g is None:
                return None
            if g >= deck - 8.0:
                return d
            d += 64.0
        return None

    found = []
    span = side.hi - side.lo
    for sgn in (1.0, -1.0):
        nlx, nly = side.local(0.0, sgn)
        nx, ny = _turn(nlx, nly, hrz)
        a = side.lo + span * MIDDLE
        while a <= side.hi - span * MIDDLE:
            c = side.wall(a, low + WALL_HIGH[1] / hs, sgn)
            if c is not None:
                x, y = spot(a, c)
                far = shore(x, y, nx, ny)
                if far is not None:
                    found.append((far, a, sgn, nx, ny))
            a += 128.0
    best = None
    for far, a, sgn, nx, ny in sorted(found):
        c = side.flat(a, low, sgn)
        if c is not None:
            best = (far, a, c, nx, ny)
            break
    if best is None:
        raise NoWay('No shore lies within %d of the ship\'s side: it stands too far out for a pier.' % PIER_MOST if not found
                    else 'The ship\'s side has no flat stretch facing the shore for a door.')
    far, a, c, nx, ny = best
    wx, wy = spot(a, c)
    out_yaw = math.atan2(nx, ny) % math.tau         # (looking away from the hull; a frame's own +y)
    ops = []
    rep = {'far': round(far), 'wall': [round(wx), round(wy)]}

    def add(base, x, y, z, rz, **more):
        ck = cell_at(x, y)
        if ck is None:
            return None
        o = dict({'op': 'add', 'cell': ck, 'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)], 's': 1}, **more)
        ops.append(o)
        return o

    # ----- the pier -----
    n = int(math.ceil((far + landmarks.DOCK_STEP / 2) / landmarks.DOCK_STEP)) + landmarks.LANDING - 1
    line = []
    for k in range(n):
        d = landmarks.DOCK_STEP * (k + 0.5)
        x, y = wx + nx * d, wy + ny * d
        g = ground.at(x, y)
        if g is None or add(gd.key(dock), x, y, water + landmarks.DOCK_UP, out_yaw) is None:
            break
        line.append((x, y, g))
        if pylon is not None and k % 2 == 0 and g <= water - 24:
            add(gd.key(pylon), x, y, water + landmarks.PYLON[1], out_yaw)
    if len(line) * landmarks.DOCK_STEP < far:
        raise NoWay('The pier would leave the map before it reaches the shore.')
    rep['pier'] = len(line)
    rep['pier_line'] = [[round(wx, 1), round(wy, 1)], [round(line[-1][0], 1), round(line[-1][1], 1)]]
    rep['deck'] = round(deck, 1)

    # ----- the hull door -----
    def door_in(fx, fy, fz, frz, **more):
        lx, ly, lz, turn = DOOR_IN_FRAME
        tx, ty = _turn(lx, ly, frz)
        return add(door_key, fx + tx, fy + ty, fz + lz, frz + turn, **more)

    frame = _own(pr, prefix + FRAME, 'STAT')
    fx, fy = wx + nx * FRAME_OFF, wy + ny * FRAME_OFF
    if frame:
        add(frame, fx, fy, deck, out_yaw)
    tag = 'ship'
    door_in(fx, fy, deck, out_yaw, name=tag + 'o')
    rep['door'] = [round(fx, 1), round(fy, 1), round(deck, 1)]
    arrive_out = [round(wx + nx * OUT, 1), round(wy + ny * OUT, 1), round(deck + 8.0, 1), 0.0, 0.0, round(out_yaw, 4)]

    # ----- the base behind it -----
    made, kept, doors = townbuild.inside_ops(gd, place, tag, prefix + PLACE[0], PLACE[1])
    cfid = gd.from_key(place['cell'])
    exit_fid = gd.from_key(place['exit'])
    up = None                                   # (the place's other way out to the open air: it becomes the way up to the deck)
    for r in gd.refs(cfid):
        if r['ref'] == exit_fid or not r.get('leads') or gd.key(r['ref']) not in doors:
            continue
        t = townbuild._tel(gd, r['ref'])
        if not t or gd.ref_cell.get(t[0]) is None or gd.ref_cell.get(t[0]) in gd.interiors:
            continue
        back = townbuild._tel(gd, t[0])
        up = (doors[gd.key(r['ref'])], [round(v, 4) for v in (back[1] if back and back[0] == r['ref'] else list(r['pos']) + list(r['rot']))])
        break
    beds = [o['p'] for o in made if o['op'] == 'add' and gd.forms[gd.from_key(o['base'])][1].tag == 'FURN' and 'bed' in gd.edid(gd.from_key(o['base'])).lower()]
    safe, records = 0, {}
    for o in made:
        if o['op'] != 'add':
            continue
        fid = gd.from_key(o['base'])
        if gd.forms[fid][1].tag == 'CONT' and STORE.search(gd.edid(fid).lower()) and any(math.dist(o['p'][:3], b[:3]) < STORE_NEAR for b in beds):
            if fid not in records:
                rec, edid = _safe(gd, pr, fid, prefix)
                mine = _own(pr, edid, 'CONT')
                if not mine:
                    ops.append({'op': 'record_new', 'record': rec, 'name': 'safe%d' % len(records)})
                records[fid] = mine or '$safe%d' % len(records)
            o['base'] = records[fid]
            safe += 1
    ops += made
    benches = {}
    for r in gd.refs(cfid):
        if r['type'] != 'REFR' or r['base'] not in gd.forms or not r['pos']:
            continue
        edid = gd.edid(r['base'])
        i, rr = gd.cell_refs[cfid].get(r['ref'], (None, None))
        if edid in BENCHES and rr is not None and not rr.flags & townbuild.INITIALLY_OFF and 'XESP' not in gd.plugins[i].fields(rr):
            ops.append({'op': 'add', 'cell': '$' + tag, 'base': gd.key(r['base']), 'p': [round(v, 4) for v in list(r['pos']) + list(r['rot'])], 's': round(r['scale'], 4)})
            benches[edid] = benches.get(edid, 0) + 1
    ops.append({'op': 'tel', 'cell': cell_at(fx, fy), 'ref': '$' + tag + 'o', 'tel': {'door': '$' + tag + 'x', 'p': place['arrive_in']}})
    ops.append({'op': 'tel', 'cell': '$' + tag, 'ref': '$' + tag + 'x', 'tel': {'door': '$' + tag + 'o', 'p': arrive_out}})
    rep.update(place=prefix + PLACE[0], like=inside, things=kept + sum(benches.values()), beds=len(beds), benches=benches, safe=safe,
               made=[(tag, place['cell'], doors)], arrive_out=arrive_out, arrive_in=place['arrive_in'])

    # ----- up to the flight deck -----
    # (the frame nearest the hull door that has deck to stand on in front of it)
    frames = sorted(got.get(FRAME, []), key=lambda f: math.hypot(f[0][0] - wx, f[0][1] - wy))
    rep['locked'] = 0
    for p, _s, _m in frames:
        ox, oy = _turn(0.0, OUT, p[5])
        deck_out = [round(p[0] + ox, 1), round(p[1] + oy, 1), round(p[2] + DECK_DROP, 1), 0.0, 0.0, round(p[5] % math.tau, 4)]
        under = footing(gd, got, *deck_out[:3]) if up and 'deck_door' not in rep and abs(p[2] - hz - DECK_UP * hs) <= 8 else None
        if under is not None and deck_out[2] - under <= 2 * DECK_DROP:
            door_in(p[0], p[1], p[2], p[5], name=tag + 'u')
            rep['deck_drop'] = round(deck_out[2] - under, 1)
            dck = cell_at(p[0], p[1])
            ops.append({'op': 'tel', 'cell': dck, 'ref': '$' + tag + 'u', 'tel': {'door': '$' + up[0], 'p': up[1]}})
            ops.append({'op': 'tel', 'cell': '$' + tag, 'ref': '$' + up[0], 'tel': {'door': '$' + tag + 'u', 'p': deck_out}})
            rep['deck_door'] = [round(v, 1) for v in p[:3]]
            rep['deck_out'] = deck_out
        else:
            door_in(p[0], p[1], p[2], p[5], extra=townbuild.DOOR_LOCK)
            rep['locked'] += 1
    if 'deck_door' in rep:
        next(o for o in made if o.get('name') == up[0]).pop('extra', None)      # (not locked: it leads somewhere now)

    # ----- on the map -----
    mx, my, mg = line[-1]
    m = worldrec.marker_op(gd, world, [round(mx, 1), round(my, 1), round(max(mg, deck) + 40.0, 1)], MARKER[0], MARKER[1])
    if m.get('cell'):
        ops.append(m)
        rep['marker'] = MARKER[0]
    return ops, rep


def navmesh_ops(gd, pr, report, names):
    """After board's ops are applied (names: project.names as they left it): the base's navmesh as an op, the game's own
    for the place it is a copy of where that can be taken, else one made. [] when neither can be."""
    import navbuild
    out = []
    for tag, src, doors in report.get('made', ()):
        key = names.get(tag)
        if not key:
            continue
        data = townbuild.copied_navmesh(gd, pr, src, key, {g: names[n] for g, n in doors.items() if n in names})
        report['navmesh'] = 'the game\'s'
        if not data:
            try:
                data, _r = navbuild.generate(gd, pr, key)
                report['navmesh'] = 'made'
            except navbuild.NavError:
                report['navmesh'] = 'none'
                continue
        out.append({'op': 'navmesh', 'cell': key, 'mesh': data})
    return out


def way(gd, pr, world, report, step=16.0):
    """The walk from the hull door to the land, as what stands there would hold a walker: every `step` along the pier's
    line the highest thing underfoot (a dock piece's top, read from its collision and where it stands in the mod, or
    the ground). {'step': the biggest rise or fall between two samples, 'low': the lowest footing over the water,
    'wall': how far the planking stops short of the hull, 'ashore': the ground's height where the walk ends}."""
    dock = _bases(gd, (landmarks.DOCK,))[landmarks.DOCK]
    tris = _solid(gd, gd.describe(dock)[3])
    x0, x1 = min(p[0] for t in tris for p in t), max(p[0] for t in tris for p in t)
    y0, y1 = min(p[1] for t in tris for p in t), max(p[1] for t in tris for p in t)
    top = max(p[2] for t in tris for p in t)
    (ax, ay), (bx, by) = report['pier_line']
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    key = gd.key(dock)
    pieces = [r['p'] for c in pr.cells.values() for r in c['refs'].values() if r.get('base') == key and not r.get('removed')
              and abs((r['p'][0] - ax) * uy - (r['p'][1] - ay) * ux) < 64 and -200 < (r['p'][0] - ax) * ux + (r['p'][1] - ay) * uy < L + 400]
    ground = roadgen.Ground(gd, pr, world)
    water = ground.water(ax, ay) or 0.0

    def planks(x, y):
        best = None
        for p in pieces:
            lx, ly = _turn(x - p[0], y - p[1], -p[5])
            if x0 - SEAM <= lx <= x1 + SEAM and y0 - SEAM <= ly <= y1 + SEAM and (best is None or p[2] + top > best):
                best = p[2] + top
        return best

    wall = 0.0
    while wall < 64 and planks(ax + ux * wall, ay + uy * wall) is None:
        wall += 1.0
    out = {'wall': wall, 'step': 0.0, 'low': 1e9, 'pieces': len(pieces)}
    last, d = None, wall
    while d <= L + landmarks.DOCK_STEP:
        x, y = ax + ux * d, ay + uy * d
        g = ground.at(x, y)
        h = max(v for v in (planks(x, y), g, -1e9) if v is not None)
        if last is not None:
            out['step'] = max(out['step'], abs(h - last))
        out['low'] = min(out['low'], h - water)
        last = h
        out['ashore'] = g
        d += step
    return {k: round(v, 1) if isinstance(v, float) else v for k, v in out.items()}
