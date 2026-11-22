"""A door into the mountain, outside: the way into a place of the mod's own from a hillside (the Vault's back door off the
settlers' cliff trail, the first Ko'olau cave's mouth).

As the game stands its mine doors outside (measured 22 Nov 2026 over every world: six of its CaveExitDoorFrame have a
CaveDoor01 at the frame's origin, a quarter turn round): the timber frame, thin along its own x and 280 across, its door
hung across it, so you go through along the frame's x. Here the frame's +x points out of the hill, down the slope.

- **A notch in the slope.** The land in front of the frame (`PAD_OUT` out, `PAD_HALF` either side) is brought level with
  the door's sill; behind it the land is only ever raised, to a bank `BANK` over the sill (`BANK_DEEP` back), so the frame
  stands against the hill however the slope ran; both eased back over `EASE`. Land points are 128 apart, so a bank can't be
  sheer: rocks close it.
- **Rocks.** Zion's canyon rocks (Waikiki's ridges already use them for the Crest Trail's cairns): one either side of the
  frame and a crag behind and over it (`ROCKS`, in the frame's own x along out, y across), let down into the ground.
- **A path** to it from a point on a trail, cut into the hill at no step over cresttrail's grade, ending on the pad, with
  Zion's mud painted along it and onto the pad.

`spot` finds where on a slope a door can go from a trail point; `Entrance.stand` adds the parts; `ops` gives
(ops, report, cells) as the other world builders do. The door's add op is named (`name`), so a caller links it with 'tel'.
`arrival(...)` is where you stand outside when you come out: in front of the door, facing out."""
import math

import cresttrail

FRAME, DOOR = 'CaveExitDoorFrame', 'CaveDoor01'
DOOR_TURN = math.pi / 2      # (the door at the frame's origin, a quarter turn: four of the game's six)
PAD_OUT, PAD_HALF = 380.0, 240.0
BANK, BANK_DEEP = 300.0, 420.0
EASE = 320.0
SILL = 4.0                   # (the frame and door this much into the pad)
# (rock, along out, across, sink, turn, scale): in the frame's frame
ROCKS = [('NVDLC02RockCanyon16', -90.0, 420.0, 70.0, 0.6, 1.0), ('NVDLC02RockCanyon16', -90.0, -420.0, 70.0, 2.3, 1.0),
         ('NVDLC02RockCanyon16', -470.0, 0.0, 120.0, 1.1, 1.5)]
ROCK_R = {'NVDLC02RockCanyon16': 265.0}     # (about how far a rock reaches from its middle, at scale 1)
AROUND = 900.0               # (a path from behind a door goes round it this far to the side)
CLEAR_OF = 300.0             # (rocks keep this far, edge to edge, from the trail point a path starts at)
NAMES = {FRAME, DOOR} | {r[0] for r in ROCKS}
SLOPE_LOW, SLOPE_HIGH = 22.0, 65.0    # (a door goes into a slope between these, degrees)
FACE_SIDE, FACE_LEVEL, FACE_RISE = 600.0, 110.0, 150.0     # (a plain face: see face())
ROUGH = 40.0                 # (steeper than this on the way to a spot is rough going)
CLEAR = 130.0                # (nothing solid this near the doorway's line in front of it)


def _local(ox, oy, x0, y0, x, y):
    """(along out, across) of a point, for out (ox, oy) at x0, y0."""
    dx, dy = x - x0, y - y0
    return dx * ox + dy * oy, -dx * oy + dy * ox


def _world(ox, oy, x0, y0, lx, ly):
    return x0 + lx * ox - ly * oy, y0 + lx * oy + ly * ox


def yaw_of(ox, oy):
    """The game's turn about z (clockwise from above) that points a model's own +x along (ox, oy)."""
    return math.atan2(-oy, ox) % math.tau


def heading(ox, oy):
    """An actor's facing for (ox, oy): 0 is north (+y), clockwise."""
    return math.atan2(ox, oy) % math.tau


def downhill(ground, x, y, r=128.0):
    gx = (ground.at(x + r, y) or 0.0) - (ground.at(x - r, y) or 0.0)
    gy = (ground.at(x, y + r) or 0.0) - (ground.at(x, y - r) or 0.0)
    n = math.hypot(gx, gy) or 1.0
    slope = math.degrees(math.atan(math.hypot(gx, gy) / (2 * r)))
    return -gx / n, -gy / n, slope


def face(ground, x, y, z, ox, oy, side=FACE_SIDE, level=FACE_LEVEL, rise=FACE_RISE):
    """A plain face of the hill here, not the nose of a spur or a gully: the ground `side` either way along the slope
    within `level` of the door's, and rising `rise` behind it. A path along the slope then meets the pad at its height."""
    for s in (-side, side):
        g = ground.at(*_world(ox, oy, x, y, 0.0, s))
        if g is None or abs(g - z) > level:
            return False
    g = ground.at(*_world(ox, oy, x, y, -300.0, 0.0))
    return g is not None and g - z >= rise


def steps_over(ground, ax, ay, bx, by, step=64.0, limit=None):
    """How many 64-unit steps of the straight way from a to b are steeper than `limit` (ROUGH) degrees."""
    t = math.tan(math.radians(limit or ROUGH))
    n = max(1, int(math.dist((ax, ay), (bx, by)) / step))
    hs = [ground.at(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n + 1)]
    L = math.dist((ax, ay), (bx, by)) / n
    return sum(1 for a, b in zip(hs, hs[1:]) if a is not None and b is not None and abs(b - a) / L > t)


def spot(ground, sx, sy, toward=None, near=(500.0, 1800.0), grade=math.tan(math.radians(30.0)), avoid=(), up=False, ok=None, rough=None):
    """Where a door into the hill can go, reached by a path from the trail point (sx, sy): a point on a slope steep enough
    to bank against, facing down it, within `grade` of the trail's height over the path; below the trail facing away from
    it, or (up) above it facing back down towards it. toward (a unit vector) keeps to that side; ok(x, y, ox, oy) says a
    spot is free; rough: the most steps over `ROUGH` degrees allowed on the straight way there (a gully between is no way).
    (x, y, z, ox, oy, slope) or None."""
    zs = ground.at(sx, sy)
    if zs is None:
        return None
    best = None
    for a in range(0, 360, 6):
        ux, uy = math.sin(math.radians(a)), math.cos(math.radians(a))
        if toward and ux * toward[0] + uy * toward[1] < 0.35:
            continue
        r = near[0]
        while r <= near[1]:
            x, y = sx + ux * r, sy + uy * r
            z = ground.at(x, y)
            if z is not None and z > 8.0 and not any(math.hypot(x - ax, y - ay) < ar for ax, ay, ar in avoid):
                ox, oy, sl = downhill(ground, x, y)
                drop = (z - zs) if up else (zs - z)
                away = -(ox * ux + oy * uy) if up else ox * ux + oy * uy
                if SLOPE_LOW <= sl <= SLOPE_HIGH and away > 0.5 and 0 <= drop <= grade * r and face(ground, x, y, z, ox, oy) and (rough is None or steps_over(ground, sx, sy, x, y) <= rough) and (ok is None or ok(x, y, ox, oy)):
                    # (steeper is a better bank; nearer is a shorter path; straight away from the trail reads best)
                    score = sl / 45.0 + away - r / near[1] * 0.5
                    if best is None or score > best[0]:
                        best = (score, (x, y, z, ox, oy, sl))
            r += 100.0
    return best[1] if best else None


class Entrance:
    def __init__(self, gd, pr, world, side, cat, trail=None):
        self.T = trail or cresttrail.Trail(gd, pr, world, side, cat)
        self.B = B = self.T.B
        import shipinside
        found = shipinside._forms(gd, NAMES)
        B.key_of.update({e: gd.key(f) for e, f in found.items()})
        B.rep['missing'] |= NAMES - set(found)
        self.gd, self.pr, self.world = gd, pr, world
        self.rep = {}
        self.lines = []

    def _add(self, edid, x, y, z, yaw, s=1.0, name=None):
        B = self.B
        ck = B.w.cell_at(x, y)
        if ck is None or edid not in B.key_of:
            return None
        o = {'op': 'add', 'cell': ck, 'base': B.key_of[edid], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(yaw % math.tau, 4)], 's': s}
        if name:
            o['name'] = name
        B.ops.append(o)
        B.cells.add(ck)
        return o

    def notch(self, x, y, z, ox, oy):
        """The pad levelled to z in front, the bank raised behind (see the module's docstring)."""
        T = self.T
        reach = max(PAD_OUT, BANK_DEEP) + EASE + 200.0
        for gy in range(int((y - reach) // 128), int((y + reach) // 128) + 2):
            for gx in range(int((x - reach) // 128), int((x + reach) // 128) + 2):
                lx, ly = _local(ox, oy, x, y, gx * 128.0, gy * 128.0)
                behind = lx < -16.0
                want = z + BANK if behind else z
                # (how far outside the box of pad and bank)
                ax = max(-BANK_DEEP - lx, lx - PAD_OUT, 0.0)
                ay = max(abs(ly) - PAD_HALF - (120.0 if behind else 0.0), 0.0)
                d = math.hypot(ax, ay)
                if d >= EASE:
                    continue
                u = d / EASE
                u = u * u * (3 - 2 * u)
                for f, _ck, k in T._points(gx, gy):
                    old = f['h'][k]
                    if old < 4.0:
                        continue                     # (the sea stays)
                    if (gx, gy) not in T.changed:
                        T.changed[(gx, gy)] = old
                    new = old + max(0.0, want - old) * (1 - u) if behind else want + (old - want) * u
                    f['h'][k] = round(new / cresttrail.STEP) * cresttrail.STEP

    def footprint(self, x, y, ox, oy, back=-BANK_DEEP, out=PAD_OUT, half=PAD_HALF + 120.0):
        return [_world(ox, oy, x, y, a, b) for a, b in ((back, -half), (out, -half), (out, half), (back, half))]

    def free(self, x, y, ox, oy):
        """Nothing big (a building, a wall) where the pad and bank go: plants and rocks there are cleared instead."""
        blocked, _clear = self.B.blocking(self.footprint(x, y, ox, oy))
        return not blocked

    def stand(self, x, y, z, ox, oy, name, clear_of=()):
        """The frame, its door (an add op named `name`) and the rocks, at the sill (x, y, z) facing out (ox, oy). The door op.
        What grows or lies where the pad and bank go is taken out first."""
        z = round(z / cresttrail.STEP) * cresttrail.STEP
        blocked, clear = self.B.blocking(self.footprint(x, y, ox, oy))
        self.B.take_out(clear)
        self.rep['cleared_at_door'] = self.rep.get('cleared_at_door', 0) + len(clear)
        if blocked:
            self.rep.setdefault('blocked', []).append(name)
        self.notch(x, y, z, ox, oy)
        yaw = yaw_of(ox, oy)
        self._add(FRAME, x, y, z - SILL, yaw)
        door = self._add(DOOR, x, y, z - SILL, yaw + DOOR_TURN, name=name)
        for edid, lx, ly, sink, turn, s in ROCKS:
            wx, wy = _world(ox, oy, x, y, lx, ly)
            if any(math.hypot(wx - px, wy - py) < ROCK_R.get(edid, 300.0) * s + CLEAR_OF for px, py in clear_of):
                self.rep['rocks_left_out'] = self.rep.get('rocks_left_out', 0) + 1
                continue
            g = self.B.ground.at(wx, wy)
            if g is not None:
                self._add(edid, wx, wy, g - sink, yaw + turn, s)
        self.rep.setdefault('doors', []).append({'name': name, 'at': [round(x), round(y), round(z)], 'out': [round(ox, 3), round(oy, 3)]})
        self._notches = getattr(self, '_notches', []) + [(x, y, z, ox, oy)]
        return door

    def path(self, sx, sy, x, y, ox, oy, bend=0.0):
        """A path from the trail point (sx, sy) to the pad in front of the door at (x, y): cut in at cresttrail's grade,
        muddied. bend: how far to the side its middle goes (round a crag). The line."""
        # (it ends on the pad: on a steep slope the pad stands well over the ground in front, and the path is the way up)
        ex, ey = _world(ox, oy, x, y, PAD_OUT * 0.6, 0.0)
        lx, ly = _local(ox, oy, x, y, sx, sy)
        if lx < 0.0:
            # (a trail behind the door, up the slope: down the side it's on, clear of the bank, then along the slope at the
            # door's own height and onto the pad from the side. In front of a pad on a steep slope the ground is far below it)
            side = 1.0 if ly >= 0 else -1.0
            way = [(sx, sy), _world(ox, oy, x, y, -500.0, side * (AROUND + 200.0)), _world(ox, oy, x, y, 60.0, side * AROUND * 0.7),
                   _world(ox, oy, x, y, 120.0, side * (PAD_HALF + 40.0)), (ex, ey)]
        else:
            mx, my = (sx + ex) / 2 - oy * bend, (sy + ey) / 2 + ox * bend
            way = [(sx, sy), (mx, my), (ex, ey)]
        # (smooth_line takes a running mean of its points: a few far-apart corners would be averaged away, so dense first)
        dense = [way[0]]
        for a, b in zip(way, way[1:]):
            n = max(1, int(math.dist(a, b) / 64.0))
            dense += [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(1, n + 1)]
        pts = cresttrail.smooth_line(dense)
        self.T.tread(pts)
        self.lines.append(pts)
        return pts

    def mud(self, extra=()):
        T = self.T
        T.line_buckets = {}
        for pts in self.lines:
            for px, py in pts:
                T.line_buckets.setdefault((int(px // 512), int(py // 512)), []).append((px, py))
            T.paint(pts)
        for pts in extra:
            T.paint(pts)

    def clear_check(self, x, y, ox, oy):
        """Rocks (by their bounds) standing in front of the doorway: [editor ID] (should be none)."""
        out = []
        import struct
        for o in self.B.ops:
            if o['op'] != 'add':
                continue
            ed = next((e for e, k in self.B.key_of.items() if k == o['base'] and e.startswith('NVDLC02Rock')), None)
            if not ed:
                continue
            f = self.gd.from_key(o['base'])
            ob = self.gd.fields(f).get('OBND')
            b = struct.unpack('<6h', ob) if ob and len(ob) == 12 else None
            if not b:
                continue
            px, py, pz, _a, _b, rz = o['p']
            s = o.get('s', 1.0)
            # (the rock's bounds' corners in the door's frame)
            c, sn = math.cos(rz), math.sin(rz)
            corners = []
            for bx in (b[0], b[3]):
                for by in (b[1], b[4]):
                    wx, wy = px + (bx * c + by * sn) * s, py + (-bx * sn + by * c) * s
                    corners.append(_local(ox, oy, x, y, wx, wy))
            lo_x, hi_x = min(p[0] for p in corners), max(p[0] for p in corners)
            lo_y, hi_y = min(p[1] for p in corners), max(p[1] for p in corners)
            # (shrunk a third: bounds are boxes round rough rock)
            sx_, sy_ = (hi_x - lo_x) / 6, (hi_y - lo_y) / 6
            if lo_x + sx_ < PAD_OUT and hi_x - sx_ > 20.0 and lo_y + sy_ < CLEAR and hi_y - sy_ > -CLEAR:
                out.append(ed)
        return out

    def finish(self):
        """(ops, report, cells): land, things moved with it, the parts."""
        gd, B, T = self.gd, self.B, self.T
        if not hasattr(T, 'line_buckets'):
            T.line_buckets = {}
        # (no rock on a path: one a path came to pass is left out)
        rocks = {k: e for e, k in B.key_of.items() if e in {r[0] for r in ROCKS}}
        keep = []
        for o in B.ops:
            if o['op'] == 'add' and o['base'] in rocks:
                reach = ROCK_R.get(rocks[o['base']], 300.0) * o.get('s', 1.0) + cresttrail.TREAD + 40.0
                if any(math.hypot(o['p'][0] - px, o['p'][1] - py) < reach for pts in self.lines for px, py in pts):
                    self.rep['rocks_off_path'] = self.rep.get('rocks_off_path', 0) + 1
                    continue
            keep.append(o)
        B.ops[:] = keep
        for n in getattr(self, '_notches', ()):
            self.notch(*n)            # (again, after the paths: a path's edge mustn't wear down a pad or a bank)
        moved, gone = T.reseat()
        lands = []
        for k in sorted(B.forms):
            ck = gd.key(B.w.grid[k])
            lands.append({'op': 'land', 'cell': ck, 'land': B.forms[k]})
            B.cells.add(ck)
        moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
        rep = dict(self.rep, moved=len(moves), cleared=gone, land_cells=len(lands), missing=sorted(B.rep['missing']),
                   walk=cresttrail.walk_check(B.ground, {'path %d' % i: p for i, p in enumerate(self.lines)}))
        return lands + moves + B.ops, rep, sorted(B.cells)


def arrival(x, y, z, ox, oy, out=170.0):
    """Where you come out: in front of the door, facing out. [x, y, z, 0, 0, heading]"""
    return [round(x + ox * out, 1), round(y + oy * out, 1), round(z + 8.0, 1), 0.0, 0.0, round(heading(ox, oy), 4)]
