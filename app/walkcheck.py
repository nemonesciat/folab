"""Can someone walk it? A check over a model's own collision, before anyone has to try it in the game.

A thing made to be climbed (citypieces: ramps, shanties, walkways) is only that if a body gets from the ground to
every floor: a ramp that runs up under the next ramp has no headroom, a room walled all round has no way in, and
neither shows in a picture of the model. This walks the solids a model is made with (modelmake's: convex pieces, here
boxes and slabs, level or tilted):

  the model's footprint is sampled every STEP units; at each sample every solid over it is a span from its underside
      to its top there;
  a place to stand is the top of a solid no steeper than SLOPE, or the ground, with nothing in the HEAD units over it;
  from one place to the next sample over, a body goes if the height differs by no more than CLIMB (or drops no more
      than DROP) and nothing solid crosses between them from knee to head;
  `reach` floods from the ground outside the model and says which places were got to.

It is rougher than the game (a body there is a capsule with its own step and slope limits, and this knows no doors),
and is meant to catch what cannot be right, not to promise what is: it is a test's tool."""
import math

STEP = 16.0                 # between samples
HEAD = 150.0                # a body's height: there must be this much clear over where it stands
KNEE = 26.0                 # what a body steps over without noticing
CLIMB = 14.0                # up between two samples (a slope of about 40 degrees)
DROP = 40.0                 # down between two samples
SLOPE = 40.0                # degrees: steeper than this is not floor
BODY = 14.0                 # a body's half width: a way must be this clear each side
LIP = 8.0                   # a solid reaching less than this over where a body stands is a lip it stands on, not a thing it is inside


class _Solid:
    """A convex piece as two surfaces over its outline: its top and its underside."""

    def __init__(self, points):
        self.pts = points
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        self.box = (min(xs), min(ys), max(xs), max(ys))
        self.z0, self.z1 = min(p[2] for p in points), max(p[2] for p in points)
        self.hull = _hull([(p[0], p[1]) for p in points])
        self.tris = _faces(points)

    def span(self, x, y):
        """(underside, top) at a spot, or None when the piece isn't over it."""
        b = self.box
        if not (b[0] <= x <= b[2] and b[1] <= y <= b[3]) or not _inside(self.hull, x, y):
            return None
        zs = []
        for a, b_, c in self.tris:
            z = _plane_z(a, b_, c, x, y)
            if z is not None:
                zs.append(z)
        if not zs:
            return None
        return min(zs), max(zs)

    def steep(self, x, y):
        """How steep its top is at a spot, in degrees: from its top a few units each way (one way, at an edge), so the
        sliver of a tilted slab's end face, a few units wide, reads as the slab it ends and not as a wall."""
        here = self.span(x, y)
        if not here:
            return 90.0
        d, slopes = 4.0, []
        for dx, dy in ((d, 0.0), (0.0, d)):
            a, b = self.span(x + dx, y + dy), self.span(x - dx, y - dy)
            if a and b:
                slopes.append((a[1] - b[1]) / (2 * d))
            elif a or b:
                slopes.append(((a or b)[1] - here[1]) / d)
        if len(slopes) < 2:
            return 0.0
        return math.degrees(math.atan(math.hypot(*slopes)))


def _normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) or 1.0
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def _plane_z(a, b, c, x, y):
    """The height of a triangle at a spot inside its outline seen from above, or None."""
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(d) < 1e-9:
        return None
    u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d
    v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d
    w = 1 - u - v
    if u < -1e-6 or v < -1e-6 or w < -1e-6:
        return None
    return u * a[2] + v * b[2] + w * c[2]


def _hull(pts):
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _inside(hull, x, y):
    n = len(hull)
    if n < 3:
        return False
    for i in range(n):
        a, b = hull[i], hull[(i + 1) % n]
        if (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) < -1e-6:
            return False
    return True


def _faces(points):
    """Triangles of a box's (or any 8-cornered piece's) faces: every three corners that lie on its surface. A piece of
    modelmake's is small, so all triples on the convex hull are found the plain way."""
    n = len(points)
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                a, b, c = points[i], points[j], points[k]
                nm = _normal(a, b, c)
                if abs(nm[0]) + abs(nm[1]) + abs(nm[2]) < 0.5:
                    continue
                side = [nm[0] * (p[0] - a[0]) + nm[1] * (p[1] - a[1]) + nm[2] * (p[2] - a[2]) for p in points]
                if min(side) > -0.01 or max(side) < 0.01:           # all the rest on one side: a face
                    out.append((a, b, c))
    return out


class Walk:
    """The places to stand on a model's solids, and which of them the ground leads to."""

    def __init__(self, solids, margin=160.0, ground=0.0):
        self.solids = [_Solid([tuple(p) for p in s['points']]) for s in solids]
        self.ground = ground
        xs = [v for s in self.solids for v in (s.box[0], s.box[2])]
        ys = [v for s in self.solids for v in (s.box[1], s.box[3])]
        self.x0, self.y0 = min(xs) - margin, min(ys) - margin
        self.nx, self.ny = int((max(xs) + margin - self.x0) / STEP) + 1, int((max(ys) + margin - self.y0) / STEP) + 1
        self._spans = {}
        self.stand = {}                                         # (i, j) -> [heights one can stand at there]
        for j in range(self.ny):
            for i in range(self.nx):
                x, y = self.x0 + i * STEP, self.y0 + j * STEP
                spans = self.spans(x, y)
                tops = [(self.ground, 0.0)] + [(zt, s.steep(x, y)) for (zb, zt), s in spans]
                ok = []
                for z, steep in tops:
                    if steep > SLOPE:
                        continue
                    if any(zb < z + HEAD and zt > z + LIP for (zb, zt), _s in spans):      # something in the space a body takes
                        continue
                    ok.append(z)
                if ok:
                    self.stand[(i, j)] = sorted(set(round(z, 1) for z in ok))

    def spans(self, x, y):
        key = (round(x, 1), round(y, 1))
        if key not in self._spans:
            out = []
            for s in self.solids:
                sp = s.span(x, y)
                if sp:
                    out.append((sp, s))
            self._spans[key] = out
        return self._spans[key]

    def _blocked(self, a, za, b, zb):
        """Does anything solid stand between two places, from knee to head?"""
        for t in (0.25, 0.5, 0.75):
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            z = za + (zb - za) * t
            for (lo, hi), _s in self.spans(x, y):
                if lo < z + HEAD - 10 and hi > z + KNEE:
                    return True
        return False

    def reach(self):
        """Every place got to from the ground at the model's edge: {(i, j, height)}."""
        start = [(i, j) for (i, j), zs in self.stand.items() if (i in (0, self.nx - 1) or j in (0, self.ny - 1)) and self.ground in zs]
        seen = {(i, j, self.ground) for i, j in start}
        todo = list(seen)
        while todo:
            i, j, z = todo.pop()
            a = (self.x0 + i * STEP, self.y0 + j * STEP)
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (i + di, j + dj)
                for z2 in self.stand.get(n, ()):
                    if (n[0], n[1], z2) in seen or z2 - z > CLIMB or z - z2 > DROP:
                        continue
                    b = (self.x0 + n[0] * STEP, self.y0 + n[1] * STEP)
                    if self._blocked(a, z, b, z2):
                        continue
                    seen.add((n[0], n[1], z2))
                    todo.append((n[0], n[1], z2))
        return seen

    def floors(self, levels, band=12.0):
        """For each height in `levels`: (places to stand within `band` of it, how many of them were reached)."""
        got = self.reach()
        out = []
        for lv in levels:
            there = [(i, j, z) for (i, j), zs in self.stand.items() for z in zs if abs(z - lv) <= band]
            out.append((len(there), sum(1 for p in there if p in got)))
        return out
