"""Builds a navmesh for one cell from what can be stood on there. Pure Python, standard library only.

The steps, all in game units:
  1. Every solid triangle of the cell (collision shapes of the placed things, the ground outdoors) is laid into
     columns VOXEL units square; each column keeps the solid spans in it and, for a span topped by a gentle enough
     triangle, the height of that surface.
  2. A surface is a place to stand if there's HEADROOM above it. Places join their four neighbours if the step between
     them is at most STEP and there's headroom over the higher one.
  3. Places within RADIUS of an edge are taken away (an actor's middle can't go there), then those no actor can get
     to: inside, whatever no door or actor stands on; outside, whatever isn't joined to the ground.
  4. Each place becomes a square of two triangles sharing corners with its neighbours (so the mesh is sound from the
     start), then corners are removed one at a time, smallest error first, while the surface stays within HEIGHT_ERROR
     and the outline within OUTLINE_ERROR. Removing corners can't break the mesh, as each removal is checked.

Not done: cover (no NVCA), ledge links, preferred triangles (those last by hand: navedit.py). One mesh here, any pieces.

Outdoors the columns reach MARGIN past the cell on every side and the mesh is cut at the cell's edge, so an edge isn't
taken for a wall and two neighbouring cells get the same heights along their shared border."""
import heapq
import math
import struct
import time

import hkshape
import land
import navmesh
import nif

CELL = 4096.0
VOXEL_IN = 16.0
VOXEL_OUT = 32.0
# Measured from the game's own meshes laid over their collision (8 interiors, 4 outdoor cells), then tried against them
# (6 interiors, 3 outdoor cells: coverage of the game's mesh for each value):
SLOPE_MAX = 48.0        # degrees: 99% of what its meshes stand on is under 42 inside, 48 outside; little lies beyond 45
STEP = 28.0             # 14: 63% of the floor inside, 20: 80%, 28: 92%, 36: 93%. Stairs want about this
HEADROOM = 120.0        # hardly matters (90: 80.3%, 160: 79.6%); low rooms in the game are 176 high
RADIUS = 16.0           # one ring of places. 16: 80%, 32: 70%, 48: 57%. Its meshes reach about half way into the ring
                        # 16-32 from an edge. (Hand-trimmed meshes, so a guide and not the actors' true size.)
HEIGHT_ERROR = 16.0     # 90% of its meshes' surface is within 16 of the collision
OUTLINE_ERROR = 1.25    # voxels: at least 0.71 to smooth a diagonal staircase of places at all
MARGIN = 96.0           # outdoors: how far past the cell's edge things still count
MAX_EDGE = 1024.0       # 99.9% of its edges are shorter
MIN_AREA2 = 32.0        # twice the area, seen from above, of the smallest triangle allowed to appear
MIN_SHAPE = 0.012       # ...and of the thinnest: twice its area over its longest side squared
PROBE = 4               # every this many places (each way) the true surface is kept to check the mesh against
MIN_REGION = 40         # places: outside, a piece with less ground than this isn't worth a mesh
FLOOR_SPREAD = 96.0     # how far above the lowest floor still counts as the floor (kit rooms are 240 high)
TREE_RADIUS = 20.0
SEED_REACH = 256.0
_GAP = 2.0              # spans this close are one span
_TOP = 2.0              # surfaces this close are the same surface
SOLID_BASES = {'STAT', 'MSTT', 'FURN', 'CONT', 'ACTI', 'TERM', 'TACT', 'SCOL'}
DOOR_BASE = 'DOOR'
INITIALLY_DISABLED = 0x800


class Field:
    """The columns. cols[(iy, ix)] = spans (low, high, surface height or None, slope x, slope y, ground)."""

    def __init__(self, voxel, cos_slope, bounds=None):
        self.v = voxel
        self.cos = cos_slope
        self.bounds = bounds            # (x0, y0, x1, y1): anything outside is left out
        self.cols = {}
        self.tris = 0

    def add(self, ax, ay, az, bx, by, bz, cx, cy, cz, ground=False, two_sided=False):
        v = self.v
        lox, hix = min(ax, bx, cx), max(ax, bx, cx)
        loy, hiy = min(ay, by, cy), max(ay, by, cy)
        if self.bounds:
            x0, y0, x1, y1 = self.bounds
            if hix < x0 or lox > x1 or hiy < y0 or loy > y1:
                return
        ux, uy, uz = bx - ax, by - ay, bz - az
        wx, wy, wz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        if ln == 0:
            return
        self.tris += 1
        walk = (abs(nz) if two_sided else nz) >= self.cos * ln
        upright = abs(nz) < 1e-3 * ln
        if not upright:
            ga, gb = -nx / nz, -ny / nz
            c0 = az - ga * ax - gb * ay
            spread = (abs(ga) + abs(gb)) * v * 0.5
        cols = self.cols
        floor = math.floor
        iy0, iy1 = floor(loy / v), floor(hiy / v)
        if self.bounds:
            iy0, iy1 = max(iy0, floor(y0 / v)), min(iy1, floor(y1 / v))
            ix_min, ix_max = floor(x0 / v), floor(x1 / v)
        pts = ((ax, ay, az), (bx, by, bz), (cx, cy, cz))
        for iy in range(iy0, iy1 + 1):
            ylo = iy * v
            yhi = ylo + v
            # the triangle within this row
            xa = xb = None
            za, zb = 1e30, -1e30
            for k in range(3):
                px, py, pz = pts[k]
                qx, qy, qz = pts[(k + 1) % 3]
                if ylo <= py <= yhi:
                    if xa is None or px < xa:
                        xa = px
                    if xb is None or px > xb:
                        xb = px
                    if pz < za:
                        za = pz
                    if pz > zb:
                        zb = pz
                for yl in (ylo, yhi):
                    if (py < yl) != (qy < yl):
                        f = (yl - py) / (qy - py)
                        xx, zz = px + f * (qx - px), pz + f * (qz - pz)
                        if xa is None or xx < xa:
                            xa = xx
                        if xb is None or xx > xb:
                            xb = xx
                        if zz < za:
                            za = zz
                        if zz > zb:
                            zb = zz
            if xa is None:
                continue
            ix0, ix1 = floor(xa / v), floor(xb / v)
            if self.bounds:
                ix0, ix1 = max(ix0, ix_min), min(ix1, ix_max)
            yc = ylo + v * 0.5
            for ix in range(ix0, ix1 + 1):
                if upright:
                    span = (za, zb, None, 0.0, 0.0, ground)
                else:
                    zc = ga * ((ix + 0.5) * v) + gb * yc + c0
                    lo = zc - spread
                    hi = zc + spread
                    if lo < za:
                        lo = za
                    if hi > zb:
                        hi = zb
                    if hi < lo:
                        lo = hi = za if zc < za else zb
                    if walk:
                        if zc < lo:
                            zc = lo
                        elif zc > hi:
                            zc = hi
                        span = (lo, hi, zc, ga, gb, ground)
                    else:
                        span = (lo, hi, None, 0.0, 0.0, ground)
                key = (iy, ix)
                c = cols.get(key)
                if c is None:
                    cols[key] = [span]
                else:
                    c.append(span)


def _places(field, headroom):
    """From the columns: the places to stand, [(iy, ix, height, slope x, slope y, ground, room above)]."""
    out = []
    for (iy, ix), col in field.cols.items():
        col.sort(key=lambda s: s[0])
        merged = []
        low, high, z, ga, gb, gr = col[0]
        for s in col[1:]:
            if s[0] <= high + _GAP:
                if s[1] > high + _TOP:
                    if s[2] is None and z is not None and s[1] - z <= STEP:
                        high = s[1]         # (a stair's riser in this column: what's above it is one step, not a wall)
                    else:
                        high, z, ga, gb, gr = s[1], s[2], s[3], s[4], s[5]
                else:
                    if s[2] is not None and (z is None or s[2] > z):
                        z, ga, gb, gr = s[2], s[3], s[4], s[5]
                    if s[1] > high:
                        high = s[1]
            else:
                merged.append((low, high, z, ga, gb, gr))
                low, high, z, ga, gb, gr = s
        merged.append((low, high, z, ga, gb, gr))
        for k, m in enumerate(merged):
            if m[2] is None:
                continue
            ceil = merged[k + 1][0] if k + 1 < len(merged) else 1e30
            if ceil - m[2] >= headroom:
                out.append((iy, ix, m[2], m[3], m[4], m[5], ceil))
    return out


class Graph:
    """The places and how they join."""

    def __init__(self, places, voxel, step, headroom):
        self.p = places
        self.v = voxel
        by = {}
        for i, q in enumerate(places):
            by.setdefault((q[0], q[1]), []).append(i)
        self.by = by
        half = voxel * 0.5
        n = len(places)
        east, north = [-1] * n, [-1] * n
        west, south = [-1] * n, [-1] * n
        for i, q in enumerate(places):
            iy, ix, z, ga, gb = q[:5]
            for dy, dx, out, back in ((0, 1, east, west), (1, 0, north, south)):
                best, bd = -1, step
                for j in by.get((iy + dy, ix + dx), ()):
                    r = places[j]
                    # the step at the side they share, so a steady slope is no step at all
                    d = abs((z + (ga * dx + gb * dy) * half) - (r[2] - (r[3] * dx + r[4] * dy) * half))
                    if d <= bd and min(q[6], r[6]) - max(z, r[2]) >= headroom and back[j] < 0:
                        best, bd = j, d
                if best >= 0:
                    out[i] = best
                    back[best] = i
        self.nb = (east, north, west, south)

    def erode(self, keep, radius):
        """Take away places nearer than radius to where the walkable ground ends. Rings alternate between straight and
        diagonal steps, so the distance comes out round enough."""
        east, north, west, south = self.nb
        rings = int(math.ceil(radius / self.v))
        ring = [i for i in range(len(keep)) if keep[i] and (east[i] < 0 or north[i] < 0 or west[i] < 0 or south[i] < 0)]
        for k in range(rings):
            for i in ring:
                keep[i] = False
            nxt = set()
            for i in ring:
                near = [east[i], north[i], west[i], south[i]]
                if k % 2:
                    for j in (east[i], west[i]):
                        if j >= 0:
                            near += (north[j], south[j])
                nxt.update(j for j in near if j >= 0 and keep[j])
            ring = list(nxt)
        return keep

    def pieces(self, keep):
        """Joined pieces of what is kept: (list of lists, piece number by place)."""
        east, north, west, south = self.nb
        label = [-1] * len(keep)
        out = []
        for s in range(len(keep)):
            if not keep[s] or label[s] >= 0:
                continue
            label[s] = len(out)
            stack, piece = [s], []
            while stack:
                i = stack.pop()
                piece.append(i)
                for j in (east[i], north[i], west[i], south[i]):
                    if j >= 0 and keep[j] and label[j] < 0:
                        label[j] = len(out)
                        stack.append(j)
            out.append(piece)
        return out, label

    def nearest(self, pos, reach, keep):
        """The kept place nearest a point, or None."""
        v = self.v
        cx, cy = math.floor(pos[0] / v), math.floor(pos[1] / v)
        rings = int(reach / v)
        best, bd = None, 1e30
        for r in range(rings + 1):
            if best is not None and (r - 1) * v > bd:
                break
            for iy in range(cy - r, cy + r + 1):
                stride = 1 if abs(iy - cy) == r else max(1, 2 * r)
                for ix in range(cx - r, cx + r + 1, stride):
                    for i in self.by.get((iy, ix), ()):
                        if keep[i]:
                            q = self.p[i]
                            d = math.hypot((ix + 0.5) * v - pos[0], (iy + 0.5) * v - pos[1]) + abs(q[2] - pos[2]) * 0.5
                            if abs(q[2] - pos[2]) <= reach and d < bd:
                                best, bd = i, d
        return best


def _start_mesh(g, keep, crop):
    """A square of two triangles for every kept place inside crop (x0, y0, x1, y1, or None), corners shared across
    joined sides. Returns (verts [x, y, z], tris [a, b, c], which edge each vertex is locked to, the true surface at
    every PROBE'th place by triangle)."""
    v = g.v
    east, north, west, south = g.nb
    p = g.p
    in_mesh = {}
    for i, q in enumerate(p):
        if not keep[i]:
            continue
        if crop:
            x, y = q[1] * v, q[0] * v
            if x < crop[0] or x + v > crop[2] or y < crop[1] or y + v > crop[3]:
                continue
        in_mesh[i] = len(in_mesh)
    parent = list(range(4 * len(in_mesh)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, k in in_mesh.items():
        j = east[i]
        if j in in_mesh:
            m = in_mesh[j]
            parent[find(4 * k + 1)] = find(4 * m + 0)
            parent[find(4 * k + 2)] = find(4 * m + 3)
        j = north[i]
        if j in in_mesh:
            m = in_mesh[j]
            parent[find(4 * k + 3)] = find(4 * m + 0)
            parent[find(4 * k + 2)] = find(4 * m + 1)
    order = {}
    sums = []
    corners = ((0, 0), (1, 0), (1, 1), (0, 1))

    def height(i, c):
        q = p[i]
        return q[2] + (q[3] * (corners[c][0] - 0.5) + q[4] * (corners[c][1] - 0.5)) * v

    tris = []
    verts = []
    probes = {}
    for i, k in in_mesh.items():
        q = p[i]
        if q[0] % PROBE == 0 and q[1] % PROBE == 0:
            probes[len(tris)] = [((q[1] + 0.5) * v, (q[0] + 0.5) * v, q[2])]
        ids = []
        for c in range(4):
            root = find(4 * k + c)
            vid = order.get(root)
            if vid is None:
                vid = order[root] = len(verts)
                verts.append([(q[1] + corners[c][0]) * v, (q[0] + corners[c][1]) * v, 0.0])
                sums.append([0.0, 0])
            sums[vid][0] += height(i, c)
            sums[vid][1] += 1
            ids.append(vid)
        # places just past the cut still count towards the height of the corners they join
        for j, (c0, c1, oc0, oc1) in ((east[i], (1, 2, 0, 3)), (north[i], (3, 2, 0, 1)), (west[i], (0, 3, 1, 2)),
                                      (south[i], (0, 1, 3, 2))):
            if j >= 0 and j not in in_mesh and keep[j]:
                sums[ids[c0]][0] += height(j, oc0)
                sums[ids[c0]][1] += 1
                sums[ids[c1]][0] += height(j, oc1)
                sums[ids[c1]][1] += 1
        if (q[0] + q[1]) % 2:
            tris += ([ids[0], ids[1], ids[2]], [ids[0], ids[2], ids[3]])
        else:
            tris += ([ids[0], ids[1], ids[3]], [ids[1], ids[2], ids[3]])
    for w, (s, n) in zip(verts, sums):
        w[2] = s / n
    lock = [0] * len(verts)
    if crop:
        for i, w in enumerate(verts):
            lock[i] = (w[0] == crop[0]) | (w[0] == crop[2]) << 1 | (w[1] == crop[1]) << 2 | (w[1] == crop[3]) << 3
    return verts, tris, lock, probes


def simplify(verts, tris, lock, height_error, outline_error, probes=None, max_edge=MAX_EDGE):
    """Remove corners, smallest error first, while the mesh stays sound. verts [[x, y, z]], tris [[a, b, c]] wound
    anticlockwise from above; lock[v] says which cut edges a corner lies on (it may only slide along them).
    probes: {triangle: [points of the true surface under it]}, handed on as triangles go, and the mesh must stay within
    height_error of them all. Returns the same two lists, renumbered."""
    n = len(verts)
    at = [set() for _ in range(n)]
    for ti, t in enumerate(tris):
        for a in t:
            at[a].add(ti)
    next_b, prev_b = {}, {}
    seen = set()
    for t in tris:
        seen.update(((t[0], t[1]), (t[1], t[2]), (t[2], t[0])))
    for a, b in seen:
        if (b, a) not in seen:
            next_b[a] = b
            prev_b[b] = a
    chain = {}
    held = dict(probes or {})
    alive = [True] * n
    max2 = max_edge * max_edge

    def around(u):
        s = set()
        for ti in at[u]:
            s.update(tris[ti])
        s.discard(u)
        return s

    def cost(u, v):
        """The error of moving corner u onto v, or None if that can't be done."""
        if lock[u] & ~lock[v]:
            return None
        ux, uy, uz = verts[u]
        vx, vy, vz = verts[v]
        off_u = 0.0
        boundary = u in next_b
        if boundary:
            p, q = prev_b[u], next_b[u]
            if (v != p and v != q) or p == q:
                return None
            # the outline: every old corner along it stays near the new side
            ax, ay, az = verts[p]
            bx, by, bz = verts[q]
            dx, dy, dz = bx - ax, by - ay, bz - az
            ln2 = dx * dx + dy * dy
            if ln2 > max2 or ln2 == 0:
                return None
            for pts in (chain.get((p, u), ()), ((ux, uy, uz),), chain.get((u, q), ())):
                for px, py, pz in pts:
                    f = ((px - ax) * dx + (py - ay) * dy) / ln2
                    f = 0.0 if f < 0 else 1.0 if f > 1 else f
                    if math.hypot(ax + f * dx - px, ay + f * dy - py) > outline_error:
                        return None
                    e = abs(az + f * dz - pz)
                    if e > height_error:
                        return None
                    if e > off_u:
                        off_u = e
        common = around(u) & around(v)
        on_outline = v == next_b.get(u) or v == prev_b.get(u)
        if len(common) != (1 if on_outline else 2):
            return None
        total = off_u
        fan = []
        pts = [] if boundary else [(ux, uy, uz)]
        for ti in at[u]:
            t = tris[ti]
            h = held.get(ti)
            if h:
                pts += h
            if v in t:
                continue
            i = t.index(u)
            ax, ay, az = verts[t[(i + 1) % 3]]
            bx, by, bz = verts[t[(i + 2) % 3]]
            e1x, e1y = ax - vx, ay - vy
            e2x, e2y = bx - vx, by - vy
            area2 = e1x * e2y - e1y * e2x
            if area2 < MIN_AREA2:
                return None
            d1 = e1x * e1x + e1y * e1y
            d2 = e2x * e2x + e2y * e2y
            d3 = (ax - bx) ** 2 + (ay - by) ** 2
            long2 = max(d1, d2, d3)
            if long2 > max2 or area2 < MIN_SHAPE * long2:
                return None
            fan.append((e1x, e1y, e2x, e2y, area2, az - vz, bz - vz))
        for k, (px, py, pz) in enumerate(pts):
            sx, sy = px - vx, py - vy
            for e1x, e1y, e2x, e2y, area2, dza, dzb in fan:
                l1 = (sx * e2y - sy * e2x) / area2
                if l1 < -1e-6:
                    continue
                l2 = (e1x * sy - e1y * sx) / area2
                if l2 < -1e-6 or l1 + l2 > 1 + 1e-6:
                    continue
                e = abs(vz + l1 * dza + l2 * dzb - pz)
                if e > total:
                    if e > height_error:
                        return None
                    total = e
                break
            else:
                if k == 0 and not boundary:     # (u itself falls in no new triangle: the fan doesn't cover its place)
                    return None
        return total + 1e-3 * math.sqrt((ux - vx) ** 2 + (uy - vy) ** 2)

    heap = []
    edges = set()
    for t in tris:
        for k in range(3):
            edges.add((t[k], t[(k + 1) % 3]))
            edges.add((t[(k + 1) % 3], t[k]))
    for u, v in edges:
        c = cost(u, v)
        if c is not None:
            heap.append((c, u, v))
    heapq.heapify(heap)
    while heap:
        c, u, v = heapq.heappop(heap)
        if not alive[u] or not alive[v] or not any(v in tris[ti] for ti in at[u]):
            continue
        c2 = cost(u, v)
        if c2 is None:
            continue
        if c2 > c + 1e-6:
            heapq.heappush(heap, (c2, u, v))
            continue
        # do it
        ux, uy, uz = verts[u]
        if u in next_b:
            p, q = prev_b.pop(u), next_b.pop(u)
            joined = list(chain.pop((p, u), ())) + [(ux, uy, uz)] + list(chain.pop((u, q), ()))
            next_b[p] = q
            prev_b[q] = p
            chain[(p, q)] = joined
        moved = []
        fan = []
        for ti in list(at[u]):
            t = tris[ti]
            h = held.pop(ti, None)
            if h:
                moved += h
            if v in t:
                for w in t:
                    at[w].discard(ti)
                tris[ti] = None
            else:
                t[t.index(u)] = v
                at[v].add(ti)
                fan.append(ti)
        at[u] = set()
        alive[u] = False
        vx, vy = verts[v][:2]
        for pt in moved:
            sx, sy = pt[0] - vx, pt[1] - vy
            for ti in fan:
                t = tris[ti]
                i = t.index(v)
                a, b = verts[t[(i + 1) % 3]], verts[t[(i + 2) % 3]]
                e1x, e1y, e2x, e2y = a[0] - vx, a[1] - vy, b[0] - vx, b[1] - vy
                area2 = e1x * e2y - e1y * e2x
                l1 = (sx * e2y - sy * e2x) / area2
                l2 = (e1x * sy - e1y * sx) / area2
                if l1 >= -1e-6 and l2 >= -1e-6 and l1 + l2 <= 1 + 1e-6:
                    held.setdefault(ti, []).append(pt)
                    break
        for w in around(v):
            for a, b in ((v, w), (w, v)):
                c3 = cost(a, b)
                if c3 is not None:
                    heapq.heappush(heap, (c3, a, b))
    new = {}
    out_v = []
    out_t = []
    for t in tris:
        if t is None:
            continue
        for a in t:
            if a not in new:
                new[a] = len(out_v)
                out_v.append(verts[a])
        out_t.append([new[a] for a in t])
    return out_v, out_t


def mesh_from(cell, verts, tris, water=None):
    """A navmesh record's structure from plain triangles (anticlockwise from above): edges joined, flags, grid."""
    vs = [tuple(float(c) for c in v) for v in verts]
    by_edge = {}
    for ti, t in enumerate(tris):
        for i in range(3):
            by_edge[(t[i], t[(i + 1) % 3])] = ti
    out = []
    for ti, t in enumerate(tris):
        fl = navmesh.F_FOUND
        if water is not None and (vs[t[0]][2] + vs[t[1]][2] + vs[t[2]][2]) / 3 < water:
            fl |= navmesh.F_WATER
        out.append((t[0], t[1], t[2], by_edge.get((t[1], t[0]), navmesh.NONE),
                    by_edge.get((t[2], t[1]), navmesh.NONE), by_edge.get((t[0], t[2]), navmesh.NONE), fl, 0))
    m = {'version': navmesh.VERSION, 'cell': cell, 'verts': vs, 'tris': out, 'cover': [], 'doors': [], 'ext': []}
    m['grid'] = navmesh.build_grid(vs, out)
    return m


# --- what's in a cell ---

def _turn(rx, ry, rz):
    """The turn of a placed thing (the game turns the other way round each axis, x then y then z)."""
    sx, cx = math.sin(-rx), math.cos(-rx)
    sy, cy = math.sin(-ry), math.cos(-ry)
    sz, cz = math.sin(-rz), math.cos(-rz)
    return ((cy * cz, -cy * sz, sy),
            (sx * sy * cz + cx * sz, cx * cz - sx * sy * sz, -sx * cy),
            (sx * sz - cx * sy * cz, cx * sy * sz + sx * cz, cx * cy))


def _solid_of(gd, base, cache, report):
    """(flat points, flat corners, facing unknown) pieces of what stops an actor in a base form, in its own coordinates."""
    if base in cache:
        return cache[base]
    out = []
    try:
        btype, _e, _f, model = gd.describe(base)
    except (KeyError, IndexError):
        cache[base] = out
        return out
    if btype in SOLID_BASES and model:
        try:
            data = gd.read_file(gd.model_path(btype, model))
            try:
                for s in hkshape.collision_shapes(data):
                    if s['layer'] in hkshape.LAYERS_SOLID and s['i']:
                        out.append((s['v'], s['i'], s['soup']))
                report['collision'] += 1
            except hkshape.Unread:
                for s in nif.mesh_from_nif(data):
                    out.append((s['p'], s['i'], True))
                report['drawn'] += 1
        except (FileNotFoundError, nif.NifError, struct.error, IndexError):
            report['unread'] += 1
    cache[base] = out
    return out


def _lay_ref(field, r, solid):
    (r00, r01, r02), (r10, r11, r12), (r20, r21, r22) = _turn(*r['rot'])
    tx, ty, tz = r['pos']
    s = r['scale']
    add = field.add
    for flat, idx, soup in solid:
        pts = []
        for k in range(0, len(flat) - 2, 3):
            x, y, z = flat[k], flat[k + 1], flat[k + 2]
            pts.append((tx + s * (r00 * x + r01 * y + r02 * z), ty + s * (r10 * x + r11 * y + r12 * z),
                        tz + s * (r20 * x + r21 * y + r22 * z)))
        for k in range(0, len(idx) - 2, 3):
            ax, ay, az = pts[idx[k]]
            bx, by, bz = pts[idx[k + 1]]
            cx, cy, cz = pts[idx[k + 2]]
            add(ax, ay, az, bx, by, bz, cx, cy, cz, False, soup)


def _usable(gd, r):
    """A placed thing that's really there when the game starts."""
    if r.get('pos') is None or r.get('rot') is None or r.get('base') is None:
        return False
    entry = gd.forms.get(r['ref'])
    return not (entry and entry[1].flags & INITIALLY_DISABLED)


def _lay_refs(gd, field, refs, cache, report):
    """Lay what stops actors, and return the doors and actors seen: (doors [(ref, pos)], seeds [pos])."""
    doors, seeds = [], []
    for r in refs:
        if r['type'] in ('ACHR', 'ACRE'):
            if r.get('pos'):
                seeds.append(r['pos'])
            continue
        if r['type'] != 'REFR' or not _usable(gd, r):
            continue
        try:
            btype = gd.forms[r['base']][1].tag
        except KeyError:
            continue
        if btype == DOOR_BASE:
            if r['leads']:
                doors.append((r['ref'], r['pos']))
                seeds.append(r['pos'])
            continue
        if btype == 'TREE':
            pts, idx = hkshape._prism((0, 0, 0), (0, 0, 128), TREE_RADIUS, TREE_RADIUS)
            _lay_ref(field, r, [([c for p in pts for c in p], idx, False)])
            continue
        solid = _solid_of(gd, r['base'], cache, report)
        if solid:
            _lay_ref(field, r, solid)
            report['placed'] += 1
    return doors, seeds


def _lay_ground(gd, field, world, gx, gy, tex, land_of=None):
    h = land_of(gx, gy) if land_of else None
    if h is None:
        entry = gd.land_at(world, gx, gy)
        if not entry:
            return False
        h = land.decode(gd, entry, tex)['h']
    if not h:
        return False
    x0, y0 = gx * CELL, gy * CELL
    st = land.STEP
    side = land.SIDE
    b = field.bounds
    add = field.add
    for r in range(side - 1):
        y = y0 + r * st
        if b and (y + st < b[1] or y > b[3]):
            continue
        for c in range(side - 1):
            x = x0 + c * st
            if b and (x + st < b[0] or x > b[2]):
                continue
            a, e, f, g = h[r * side + c], h[r * side + c + 1], h[(r + 1) * side + c + 1], h[(r + 1) * side + c]
            add(x, y, a, x + st, y, e, x + st, y + st, f, True)
            add(x, y, a, x + st, y + st, f, x, y + st, g, True)
    return True


def _water_of(gd, cell):
    """The water height in a cell, or None."""
    f = gd.fields(cell)
    data = f.get('DATA', b'\0')
    if not data[0] & 2:
        return None
    x = f.get('XCLW')
    if x and len(x) >= 4:
        h = struct.unpack_from('<f', x)[0]
        if h < 1e30:
            return h
    world = gd.ext_cells.get(cell)
    if world is not None:
        d = gd.fields(world).get('DNAM')
        if d and len(d) >= 8:
            return struct.unpack_from('<f', d, 4)[0]
    return None


def _floor_pieces(g, pieces):
    """The pieces at floor level: as low as the lowest one big enough to walk about on, give or take a stair or two."""
    big = [(sum(g.p[i][2] for i in piece) / len(piece), k) for k, piece in enumerate(pieces) if len(piece) >= MIN_REGION]
    if not big:
        return set()
    low = min(z for z, _k in big)
    return {k for z, k in big if z <= low + FLOOR_SPREAD}


def generate(gd, cell, voxel=None, slope=SLOPE_MAX, step=STEP, headroom=HEADROOM, radius=RADIUS,
             height_error=HEIGHT_ERROR, outline_error=None, refs=None, floors=False, refs_of=None, land_of=None,
             water=False):
    """A navmesh for one cell of a gamedata.GameData: (mesh or None, report). Links to doors are made by
    navmesh.link_doors, across cell edges by navmesh.link_edges. Form IDs in the mesh are gd's load-order ones.
    refs: what's in a place inside, if not the game's own (a mod's changes; cell may then be the mod's own key).
    floors: inside, keep every area at floor level too, not only those a door or actor stands on: a place being built
    may have neither yet, and the biggest surface is often its roof.
    Outside, a mod's changes come through refs_of(cell) (what stands in a cell), land_of(x, y) (a square's heights, None
    for the game's) and water (its height, None for no water; False: as the game has it)."""
    t0 = time.time()
    report = {'collision': 0, 'drawn': 0, 'unread': 0, 'placed': 0, 'kept_pieces': 0, 'dropped_pieces': 0}
    outside = cell in gd.ext_cells
    voxel = voxel or (VOXEL_OUT if outside else VOXEL_IN)
    outline_error = outline_error or OUTLINE_ERROR * voxel
    cos = math.cos(math.radians(slope))
    cache = {}
    crop = None
    doors, seeds = [], []
    if outside:
        world = gd.ext_cells[cell]
        gx, gy = gd.cell_grid(cell)
        crop = (gx * CELL, gy * CELL, (gx + 1) * CELL, (gy + 1) * CELL)
        field = Field(voxel, cos, (crop[0] - MARGIN, crop[1] - MARGIN, crop[2] + MARGIN, crop[3] + MARGIN))
        tex = {}
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                _lay_ground(gd, field, world, gx + dx, gy + dy, tex, land_of)
                c = gd.grid(world).get((gx + dx, gy + dy))
                if c is None:
                    continue
                d, s = _lay_refs(gd, field, refs_of(c) if refs_of else gd.refs(c), cache, report)
                if dx == 0 and dy == 0:
                    doors, seeds = d, s
    else:
        field = Field(voxel, cos)
        doors, seeds = _lay_refs(gd, field, gd.refs(cell) if refs is None else refs, cache, report)
    report['triangles_in'] = field.tris
    t1 = time.time()
    g = Graph(_places(field, headroom), voxel, step, headroom)
    report['places'] = len(g.p)
    keep = g.erode([True] * len(g.p), radius)
    pieces, label = g.pieces(keep)
    wanted = set()
    if outside:
        for k, piece in enumerate(pieces):
            if sum(1 for i in piece if g.p[i][5]) >= MIN_REGION:
                wanted.add(k)
    else:
        for pos in seeds:
            i = g.nearest(pos, SEED_REACH, keep)
            if i is not None:
                wanted.add(label[i])
        if floors:
            wanted |= _floor_pieces(g, pieces)
        if not wanted and pieces:
            wanted.add(max(range(len(pieces)), key=lambda k: len(pieces[k])))
    report['kept_pieces'] = len(wanted)
    report['dropped_pieces'] = len(pieces) - len(wanted)
    for i in range(len(keep)):
        if keep[i] and label[i] not in wanted:
            keep[i] = False
    t2 = time.time()
    verts, tris, lock, probes = _start_mesh(g, keep, crop)
    report['start_triangles'] = len(tris)
    verts, tris = simplify(verts, tris, lock, height_error, outline_error, probes)
    t3 = time.time()
    report.update(lay_s=round(t1 - t0, 2), places_s=round(t2 - t1, 2), simplify_s=round(t3 - t2, 2),
                  seconds=round(t3 - t0, 2), doors=doors, triangles=len(tris), vertices=len(verts))
    if not tris:
        return None, report
    if water is False:
        water = _water_of(gd, cell) if cell in gd.forms else None
    return mesh_from(cell, verts, tris, water), report


# --- measuring against the game ---

def sample(meshes, step=16.0):
    """Where the meshes are, seen from above every step units: {(ix, iy): [heights]}."""
    out = {}
    for m in meshes:
        V = m['verts']
        for t in m['tris']:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = V[t[0]], V[t[1]], V[t[2]]
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-6:
                continue
            for iy in range(math.ceil(min(ay, by, cy) / step), math.floor(max(ay, by, cy) / step) + 1):
                y = iy * step
                for ix in range(math.ceil(min(ax, bx, cx) / step), math.floor(max(ax, bx, cx) / step) + 1):
                    x = ix * step
                    l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / d
                    l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
                    l3 = 1 - l1 - l2
                    if l1 >= -1e-9 and l2 >= -1e-9 and l3 >= -1e-9:
                        out.setdefault((ix, iy), []).append(l1 * az + l2 * bz + l3 * cz)
    return out


def compare(game_meshes, ours, step=16.0, ztol=48.0):
    """How our mesh sits against the game's: areas seen from above, the share of the game's that ours covers and of
    ours that the game covers, each counted only where the two are within ztol of each other in height."""
    a = sample(game_meshes, step)
    b = sample([ours] if ours else [], step)

    def covered(p, q):
        hit = 0
        for key, zs in p.items():
            o = q.get(key)
            if o and any(abs(z - w) <= ztol for z in zs for w in o):
                hit += 1
        return hit
    unit = step * step
    ca, cb = covered(a, b), covered(b, a)
    return {'game_area': len(a) * unit, 'our_area': len(b) * unit, 'game_covered': ca / len(a) if a else 0.0,
            'ours_on_game': cb / len(b) if b else 0.0}
