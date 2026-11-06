"""A road between two points on the map, from the game's own road pieces: the way found over the ground as the mod has it
(gentle slopes first, no water), laid with straight pieces following the slope, an end cap at each end, and if asked the ground
settled just under it so nothing pokes through.

Measured from the game's meshes: WastelandRoadStraightLong and ...B are 1,024 long along x, 632 wide, their middle at the
origin, used 217 and 455 times in the Mojave; end caps (R +x, as the end of a piece going +x) reach 157 past the origin."""
import heapq
import math
import random
import struct

import land
import navgen

STEP = 256.0            # the grid the way is found on
PIECE = 1024.0
OVERLAP = 48.0          # pieces overlap this much, so a bend leaves no gap
LIFT = 4.0              # the road's top stands this far over what's under its middle
SETTLE_FLAT = 340.0     # ground this far from the road's line lies just under it
SETTLE_FADE = 512.0     # and takes this much further to come back to its own height
UNDER = 24.0
MAX_CELLS = 400         # a way that needs a search over more cells than this is refused


class RoadError(ValueError):
    """Why not, in words for the person asking."""


class Ground:
    """The ground's height anywhere in a world, the mod's land first."""

    def __init__(self, gd, pr, world):
        self.gd, self.pr, self.world = gd, pr, world
        self.h = {}
        self.grid = gd.grid(world)

    def cell(self, k):
        if k not in self.h:
            c = self.grid.get(k)
            mine = self.pr.land.get(self.gd.key(c)) if c is not None and self.pr else None
            if mine:
                self.h[k] = mine['h']
            else:
                e = self.gd.land_at(self.world, *k)
                self.h[k] = land.heights_of(dict(land.tes4.iter_subrecords(self.gd.plugins[e[0]].data(e[1])))['VHGT']) if e else None
        return self.h[k]

    def at(self, x, y):
        """The height at a spot, or None off the land."""
        k = (int(x // 4096), int(y // 4096))
        h = self.cell(k)
        if not h:
            return None
        fx, fy = (x - k[0] * 4096) / 128, (y - k[1] * 4096) / 128
        c0, r0 = min(31, int(fx)), min(31, int(fy))
        tx, ty = fx - c0, fy - r0
        p = lambda r, c: h[r * 33 + c]
        return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty

    def water(self, x, y):
        """How high the water stands in a square, or None."""
        c = self.grid.get((int(x // 4096), int(y // 4096)))
        if c is None:
            return None
        if self.pr:
            ck = self.gd.key(c)
            if ck in self.pr.water:
                if self.pr.water[ck] is not None:
                    return self.pr.water[ck]
                w = self.gd.fields(self.world).get('DNAM')
                return struct.unpack_from('<f', w, 4)[0] if w and len(w) >= 8 else None
        return navgen._water_of(self.gd, c)


def find_way(g, a, b):
    """The points from a to b, over the ground: slopes cost more than they gain, water and the edge of the land aren't crossed."""
    cx0, cy0 = min(a[0], b[0]) - 8192, min(a[1], b[1]) - 8192
    cx1, cy1 = max(a[0], b[0]) + 8192, max(a[1], b[1]) + 8192
    if (cx1 - cx0) * (cy1 - cy0) / (4096 * 4096) > MAX_CELLS:
        raise RoadError('That\'s too far for one go: lay it in shorter stretches (about 15 cells at a time).')
    snap = lambda v: int(round(v / STEP))
    start, goal = (snap(a[0]), snap(a[1])), (snap(b[0]), snap(b[1]))
    if start == goal:
        raise RoadError('Those two points are the same spot.')
    done, came = {}, {}
    heap = [(0.0, 0.0, start)]
    zs = {}

    def height(n):
        if n not in zs:
            x, y = n[0] * STEP, n[1] * STEP
            z = g.at(x, y) if cx0 <= x <= cx1 and cy0 <= y <= cy1 else None
            if z is not None:
                w = g.water(x, y)
                if w is not None and z < w:
                    z = None
            zs[n] = z
        return zs[n]
    if height(start) is None or height(goal) is None:
        raise RoadError('Both ends must be on dry land.')
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    while heap:
        _f, cost, n = heapq.heappop(heap)
        if n in done:
            continue
        done[n] = cost
        if n == goal:
            break
        z = zs[n]
        for dx, dy in dirs:
            m = (n[0] + dx, n[1] + dy)
            if m in done:
                continue
            zm = height(m)
            if zm is None:
                continue
            run = math.hypot(dx, dy) * STEP
            slope = abs(zm - z) / run
            step = run * (1 + (slope / 0.1) ** 2)
            c2 = cost + step
            h = math.hypot(goal[0] - m[0], goal[1] - m[1]) * STEP
            heapq.heappush(heap, (c2 + h, c2, m))
            if m not in came or c2 < came[m][0]:
                came[m] = (c2, n)
    if goal not in done:
        raise RoadError('There\'s no way between those points over dry land.')
    path = [goal]
    while path[-1] != start:
        path.append(came[path[-1]][1])
    path.reverse()
    return [(n[0] * STEP, n[1] * STEP) for n in path]


def smooth(points, rounds=3):
    """Corners cut, so the pieces can follow without sharp bends."""
    pts = [tuple(p) for p in points]
    for _ in range(rounds):
        out = [pts[0]]
        for p, q in zip(pts, pts[1:]):
            out += [(p[0] * 0.75 + q[0] * 0.25, p[1] * 0.75 + q[1] * 0.25), (p[0] * 0.25 + q[0] * 0.75, p[1] * 0.25 + q[1] * 0.75)]
        out.append(pts[-1])
        pts = out
    return pts


def along(points):
    """(function from distance along to spot, total length)."""
    d = [0.0]
    for p, q in zip(points, points[1:]):
        d.append(d[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))

    def f(s):
        s = max(0.0, min(d[-1], s))
        lo, hi = 0, len(d) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if d[mid] <= s:
                lo = mid
            else:
                hi = mid
        p, q = points[lo], points[hi]
        t = (s - d[lo]) / (d[hi] - d[lo]) if d[hi] > d[lo] else 0.0
        return p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
    return f, d[-1]


def turn_along(dx, dy, dz):
    """The rotation (rx, ry, rz) laying a piece's own +x along a direction with its top as near up as can be: the turn navgen._turn
    undoes, x then y then z, each the other way round."""
    ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    f = (dx / ln, dy / ln, dz / ln)
    # up: straight up, less what lies along the road
    u = (-f[2] * f[0], -f[2] * f[1], 1 - f[2] * f[2])
    un = math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2]) or 1.0
    u = (u[0] / un, u[1] / un, u[2] / un)
    s = (u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0])  # (up x along: the piece's +y)
    # the matrix has columns f, s, u
    r02, r12, r22, r00, r01 = u[0], u[1], u[2], f[0], s[0]
    ry = -math.asin(max(-1.0, min(1.0, r02)))
    rz = -math.atan2(-r01, r00)
    rx = -math.atan2(-r12, r22)
    return rx, ry, rz


def pieces(gd):
    """The straight pieces and end caps, as forms."""
    want = {}
    names = {'WastelandRoadStraightLong': 'a', 'WastelandRoadStraightLongB': 'b', 'WastelandRoadEndCapR': 'capr', 'WastelandRoadEndCapL': 'capl'}
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'STAT':
            e = gd.edid(f)
            if e in names:
                want[names[e]] = gd.key(f)
    return want


def lay(gd, pr, world, a, b, settle=True, seed=1):
    """The plan: (things to place: [{'base', 'p'}], the road's line, settled ground: {cell key: land form} if asked)."""
    kit = pieces(gd)
    if 'a' not in kit:
        raise RoadError('The game\'s road pieces aren\'t in its files.')
    g = Ground(gd, pr, world)
    line = smooth(find_way(g, a, b))
    f, total = along(line)
    rng = random.Random(seed)
    stride = PIECE - OVERLAP
    n = max(1, int(round(total / stride)))
    stride = total / n
    out = []
    centre_z = []
    for k in range(n):
        s0, s1 = k * stride, (k + 1) * stride
        p0, p1 = f(s0), f(s1)
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        z0, z1 = g.at(*p0), g.at(*p1)
        zm = g.at(mx, my)
        if None in (z0, z1, zm):
            raise RoadError('The way runs off the land.')
        z = max(zm, (z0 + z1) / 2) + LIFT
        rot = turn_along(p1[0] - p0[0], p1[1] - p0[1], z1 - z0)
        base = kit['b'] if 'b' in kit and rng.random() < 0.6 else kit['a']
        out.append({'base': base, 'p': [round(mx, 2), round(my, 2), round(z, 2)] + [round(v, 4) for v in rot]})
        centre_z.append((p0, p1, z0 + LIFT, z1 + LIFT))
    # an end cap at each end, facing away along the road
    if 'capr' in kit:
        p0, p1 = out[-1]['p'], f(total)
        rot = out[-1]['p'][3:]
        out.append({'base': kit['capr'], 'p': [round(p1[0], 2), round(p1[1], 2), round(g.at(*p1) + LIFT, 2)] + rot})
        p2 = f(0.0)
        p3 = f(min(total, stride))
        back = turn_along(p2[0] - p3[0], p2[1] - p3[1], g.at(*p2) - g.at(*p3))
        out.append({'base': kit['capr'], 'p': [round(p2[0], 2), round(p2[1], 2), round(g.at(*p2) + LIFT, 2)] + [round(v, 4) for v in back]})
    return out, line, (settled(gd, pr, world, g, centre_z) if settle else {})


def settled(gd, pr, world, g, spans):
    """The ground along a road lowered or raised to just under it. Worked out by spot, so edge points cells share agree."""
    reach = SETTLE_FLAT + SETTLE_FADE
    # the cells any span reaches
    touched = set()
    for p0, p1, _z0, _z1 in spans:
        for x in (min(p0[0], p1[0]) - reach, max(p0[0], p1[0]) + reach):
            for y in (min(p0[1], p1[1]) - reach, max(p0[1], p1[1]) + reach):
                touched.add((int(x // 4096), int(y // 4096)))
        x0, x1 = int((min(p0[0], p1[0]) - reach) // 4096), int((max(p0[0], p1[0]) + reach) // 4096)
        y0, y1 = int((min(p0[1], p1[1]) - reach) // 4096), int((max(p0[1], p1[1]) + reach) // 4096)
        touched.update((a, b) for a in range(x0, x1 + 1) for b in range(y0, y1 + 1))
    out = {}
    tex = {}
    for k in sorted(touched):
        c = g.grid.get(k)
        if c is None or c not in gd.land:
            continue
        ck = gd.key(c)
        mine = pr.land.get(ck)
        form = dict(mine) if mine else land.decode(gd, gd.land[c], tex)
        form = _plain_land(form)
        h = list(form['h'])
        changed = False
        for r in range(33):
            y = k[1] * 4096 + r * 128.0
            for col in range(33):
                x = k[0] * 4096 + col * 128.0
                best, bz = None, None
                for p0, p1, z0, z1 in spans:
                    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                    ln = dx * dx + dy * dy
                    t = max(0.0, min(1.0, ((x - p0[0]) * dx + (y - p0[1]) * dy) / ln)) if ln else 0.0
                    d = math.hypot(p0[0] + t * dx - x, p0[1] + t * dy - y)
                    if best is None or d < best:
                        best, bz = d, z0 + t * (z1 - z0) - UNDER
                if best is None or best >= reach:
                    continue
                now = h[r * 33 + col]
                w = 1.0 if best <= SETTLE_FLAT else (reach - best) / SETTLE_FADE
                w = w * w * (3 - 2 * w)
                new = now + (bz - now) * w
                if abs(new - now) > 0.5:
                    h[r * 33 + col] = round(new / 8) * 8.0
                    changed = True
        if changed:
            form['h'] = h
            out[ck] = form
    return out


def _plain_land(form):
    """land.decode's form as the project keeps it (no texture pictures)."""
    return {k: form[k] for k in form if k in ('h', 'c', 'q')}


def road_ops(gd, pr, world, body):
    """The ops to lay a road, one Undo: each piece filed by the square it stands in. Returns (ops, a report)."""
    a, b = body['a'], body['b']
    things, line, ground = lay(gd, pr, world, a, b, bool(body.get('settle', True)), int(body.get('seed', 1)))
    ops = []
    for t in things:
        c = gd.grid(world).get((int(t['p'][0] // 4096), int(t['p'][1] // 4096)))
        if c is None:
            continue
        ops.append({'op': 'add', 'cell': gd.key(c), 'base': t['base'], 'p': t['p'], 's': 1})
    for ck, form in ground.items():
        ops.append({'op': 'land', 'cell': ck, 'land': form})
    f, total = along(line)
    return ops, {'pieces': len(things), 'length': round(total), 'cells': sorted(ground), 'line': [[round(p[0]), round(p[1])] for p in line[::8]] + [[round(line[-1][0]), round(line[-1][1])]]}
