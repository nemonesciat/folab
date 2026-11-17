"""Shade baked into a model's corners, as the game's own models carry it.

Measured over the game's statics: 95 in 100 of its buildings' shapes have a colour at every corner (none of its 300
building meshes looked at needs any other switch for it: the colours are in the shape's data and the game multiplies
the texture by them). Their mean is 0.61 to 0.75, and half the corners are darker than 0.75: dark in the corners of
a building, under its ledges and where it meets the ground, light on what is open to the sky. Plants and clutter
have it less (0.82 to 0.86). That shading is a good part of why the game's plain boxes don't read as plain boxes; a
model of FOLab's without it reads as lit by nothing but the sun.

How: the model's faces are laid into a grid of little cubes (`Grid`), the ground under it counted as solid; from each
corner a fan of rays (`RAYS`, more of them towards the corner's normal) is walked out through the grid up to `reach`,
and the share that meets nothing is how open that corner is. See-through leaves are counted as letting some light
through (`LEAF_PASS`), so a crown is dark inside and light at its edge. Then, as the game's: how open, a little
darker facing down, grime where it is shut in and rising from the ground (`DIRT_UP`), and a slow mottle so a big
wall isn't one even grey. `bake(shapes, ...)` puts 'c' (r, g, b, a for every corner) on each shape."""
import math
import random

CELLS_MOST = 3_000_000          # little cubes the grid may have
CELL_LEAST = 3.0                # (units: none smaller than this)
RAYS = 16
LEAF_PASS = 0.7                 # how much light a cube of leaves lets through
FLOOR = 0.36                    # the darkest a shut-in corner goes
LEAF_FLOOR = 0.55               # (a leaf: lit through, never so dark; the game's plants average 0.82 to 0.86)
DOWN = 0.86                     # a face looking straight down, against one looking up (1)
DIRT = (0.74, 0.66, 0.56)       # grime: brown-grey, multiplied in where it gathers
DIRT_UP = 90.0                  # (units) how high grime rises from the ground
SHUT_TINT = 0.5                 # how much of the grime colour a shut-in corner takes
MOTTLE = 0.07                   # the slow variation over a big face, either way
MOTTLE_SIZE = 420.0             # (units) its size


def _directions(n):
    """n directions over the half sphere round +z, more of them near the top (as light falls on a face)."""
    out = []
    golden = math.pi * (3 - math.sqrt(5))
    for k in range(n):
        r = math.sqrt((k + 0.5) / n)
        a = k * golden
        out.append((r * math.cos(a), r * math.sin(a), math.sqrt(max(0.0, 1 - r * r))))
    return out


_DIRS = _directions(RAYS)


class Grid:
    """The model's faces as little cubes: 2 solid, 1 leaves, 0 air."""

    def __init__(self, shapes):
        pts = [s['p'] for s in shapes]
        lo = [min(min(p[a::3]) for p in pts) for a in range(3)]
        hi = [max(max(p[a::3]) for p in pts) for a in range(3)]
        lo[2] = min(lo[2], 0.0) - 1.0
        ext = [hi[a] - lo[a] + 2.0 for a in range(3)]
        vol = ext[0] * ext[1] * ext[2]
        self.cell = max(CELL_LEAST, (vol / CELLS_MOST) ** (1 / 3.0), max(ext) / 600.0)
        c = self.cell
        self.lo = [lo[a] - c for a in range(3)]
        self.n = [int(ext[a] / c) + 3 for a in range(3)]
        self.v = bytearray(self.n[0] * self.n[1] * self.n[2])
        for s in shapes:
            mark = 1 if s.get('alpha') else 2
            p, idx = s['p'], s['i']
            for k in range(0, len(idx), 3):
                a, b, cc = (p[3 * idx[k + j]:3 * idx[k + j] + 3] for j in range(3))
                self._triangle(a, b, cc, mark)

    def _triangle(self, a, b, c, mark):
        cell = self.cell
        k = max(1, int(max(math.dist(a, b), math.dist(b, c), math.dist(c, a)) / (cell * 0.5)) + 1)
        nx, ny = self.n[0], self.n[1]
        lo, v = self.lo, self.v
        for i in range(k + 1):
            for j in range(k + 1 - i):
                u, w = i / k, j / k
                t = 1 - u - w
                x = int((a[0] * t + b[0] * u + c[0] * w - lo[0]) / cell)
                y = int((a[1] * t + b[1] * u + c[1] * w - lo[1]) / cell)
                z = int((a[2] * t + b[2] * u + c[2] * w - lo[2]) / cell)
                q = (z * ny + y) * nx + x
                if v[q] < mark:
                    v[q] = mark

    def openness(self, p, n, reach, ground):
        """The share of the sky over a face at p (normal n) that rays out to `reach` find open."""
        cell = self.cell
        lo, (nx, ny, nz), v = self.lo, self.n, self.v
        t1 = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
        tu = _unit((n[1] * t1[2] - n[2] * t1[1], n[2] * t1[0] - n[0] * t1[2], n[0] * t1[1] - n[1] * t1[0]))
        tv = (n[1] * tu[2] - n[2] * tu[1], n[2] * tu[0] - n[0] * tu[2], n[0] * tu[1] - n[1] * tu[0])
        ox, oy, oz = p[0] + n[0] * cell * 0.9, p[1] + n[1] * cell * 0.9, p[2] + n[2] * cell * 0.9
        total = 0.0
        for dx, dy, dz in _DIRS:
            rx = tu[0] * dx + tv[0] * dy + n[0] * dz
            ry = tu[1] * dx + tv[1] * dy + n[1] * dz
            rz = tu[2] * dx + tv[2] * dy + n[2] * dz
            light = 1.0
            t = cell * 0.6
            while t < reach:
                x, y, z = ox + rx * t, oy + ry * t, oz + rz * t
                if ground and z < 0.0:
                    light = 0.0
                    break
                i, j, kk = int((x - lo[0]) / cell), int((y - lo[1]) / cell), int((z - lo[2]) / cell)
                if not (0 <= i < nx and 0 <= j < ny and 0 <= kk < nz):
                    break
                m = v[(kk * ny + j) * nx + i]
                if m == 2:
                    light *= t / reach          # (something near shuts out more than something far)
                    break
                if m == 1:
                    light *= LEAF_PASS
                    if light < 0.05:
                        break
                t += cell * (0.8 + 2.0 * t / reach)     # (longer strides further out)
            total += light
        return total / len(_DIRS)


def _unit(v):
    ln = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / ln, v[1] / ln, v[2] / ln) if ln > 1e-9 else (0.0, 0.0, 1.0)


class _Mottle:
    """Slow smooth noise over space, -1 to 1."""

    def __init__(self, seed):
        rnd = random.Random(seed)
        self.v = [rnd.uniform(-1, 1) for _ in range(17 * 17 * 17)]

    def at(self, x, y, z):
        x, y, z = x / MOTTLE_SIZE, y / MOTTLE_SIZE, z / MOTTLE_SIZE
        ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
        fx, fy, fz = x - ix, y - iy, z - iz
        fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
        g = lambda a, b, c: self.v[((a % 17) * 17 + b % 17) * 17 + c % 17]
        out = 0.0
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    w = (fx if a else 1 - fx) * (fy if b else 1 - fy) * (fz if c else 1 - fz)
                    out += w * g(ix + a, iy + b, iz + c)
        return out


def reach_of(shapes):
    """How far rays go for a model: a corner of a room-sized thing is shut in by what is within a metre or two, a
    tower's by more; never under a few of the grid's cubes."""
    pts = [s['p'] for s in shapes]
    ext = max(max(max(p[a::3]) for p in pts) - min(min(p[a::3]) for p in pts) for a in range(3))
    return max(40.0, min(520.0, ext * 0.12))


def bake(shapes, seed=1, ground=True, dirt=True, reach=None):
    """Puts 'c' (r, g, b, a a corner) on every shape: see the module's docstring. ground: the ground under the model
    (z 0) shuts in what is near it and grime rises from it. Returns the mean shade."""
    grid = Grid(shapes)
    reach = max(reach or reach_of(shapes), grid.cell * 5)
    mottle = _Mottle(seed)
    seen = {}
    total, count = 0.0, 0
    for s in shapes:
        p, nrm = s['p'], s['n']
        leaf = bool(s.get('alpha'))
        out = []
        for k in range(0, len(p), 3):
            q, n = p[k:k + 3], _unit(nrm[k:k + 3])
            key = (round(q[0], 1), round(q[1], 1), round(q[2], 1), round(n[0], 2), round(n[1], 2), round(n[2], 2))
            got = seen.get(key)
            if got is None:
                op = grid.openness(q, n, reach, ground)
                if leaf:                        # (a leaf is lit through from the far side too)
                    op = max(op, grid.openness(q, (-n[0], -n[1], -n[2]), reach, ground))
                shade = (LEAF_FLOOR if leaf else FLOOR) + (1 - (LEAF_FLOOR if leaf else FLOOR)) * op
                shade *= DOWN + (1 - DOWN) * (n[2] + 1) / 2
                shade *= 1 + MOTTLE * mottle.at(q[0], q[1], q[2])
                tint = (1 - op) * SHUT_TINT
                if dirt and ground and not leaf:
                    tint = max(tint, 0.6 * max(0.0, 1 - max(0.0, q[2]) / DIRT_UP) ** 2)
                col = tuple(max(0.12, min(1.0, shade * (1 + (d - 1) * tint))) for d in DIRT)
                got = seen[key] = (round(col[0], 3), round(col[1], 3), round(col[2], 3))
            out += got + (1.0,)
            total += sum(got) / 3
            count += 1
        s['c'] = out
    return total / max(1, count)
