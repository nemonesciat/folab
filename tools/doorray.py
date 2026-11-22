"""Can the player use a door? From a point EYE_OUT in front of it at eye height, rays at a grid over the door's face are cast
against the collision of everything near (the building's own included); a ray counts when the first thing it meets is the
door (22 Nov 2026: a door hung on a plastered wall caught the crosshair only at its rim, the wall's collision in front of
the rest of it).

Rays(gd, pr).door(ref key) -> {'hits': n, 'rays': n, 'out': (x, y), 'blocked_by': {edid: n}}. The door's outside is told by
the place's way out (the arrival it gives is in front of the door) or, failing that, by `out` given."""
import math
import struct

import hkshape
import navgen
import nif

EYE_OUT = 80.0
EYE_Z = 120.0
GRID_U, GRID_Z = 5, 5
NEAR = 700.0


def _mat(rot):
    return navgen._turn(*rot)


def _tris(flat, idx, m, t, s):
    (a, b, c), (d, e, f), (g, h, i) = m
    pts = []
    for k in range(0, len(flat) - 2, 3):
        x, y, z = flat[k], flat[k + 1], flat[k + 2]
        pts.append((t[0] + s * (a * x + b * y + c * z), t[1] + s * (d * x + e * y + f * z), t[2] + s * (g * x + h * y + i * z)))
    return [(pts[idx[k]], pts[idx[k + 1]], pts[idx[k + 2]]) for k in range(0, len(idx) - 2, 3)]


def _hit(o, d, tri):
    """Möller-Trumbore: distance along d (unit) to the triangle, or None."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
    e1 = (bx - ax, by - ay, bz - az)
    e2 = (cx - ax, cy - ay, cz - az)
    p = (d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2], d[0] * e2[1] - d[1] * e2[0])
    det = e1[0] * p[0] + e1[1] * p[1] + e1[2] * p[2]
    if abs(det) < 1e-9:
        return None
    inv = 1.0 / det
    tv = (o[0] - ax, o[1] - ay, o[2] - az)
    u = (tv[0] * p[0] + tv[1] * p[1] + tv[2] * p[2]) * inv
    if u < 0 or u > 1:
        return None
    q = (tv[1] * e1[2] - tv[2] * e1[1], tv[2] * e1[0] - tv[0] * e1[2], tv[0] * e1[1] - tv[1] * e1[0])
    v = (d[0] * q[0] + d[1] * q[1] + d[2] * q[2]) * inv
    if v < 0 or u + v > 1:
        return None
    t = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) * inv
    return t if t > 0 else None


class Rays:
    def __init__(self, gd, pr, refs, model_of):
        """refs: {ref key: (cell, ref)}; model_of(base) -> (type, model path under Data) or None."""
        self.gd, self.pr, self.refs, self.model_of = gd, pr, refs, model_of
        self.cache = {}
        self.grid = {}
        for rk, (ck, r) in refs.items():
            p = r.get('p')
            if p and p[2] > -20000 and r.get('base'):
                self.grid.setdefault((int(p[0] // 1024), int(p[1] // 1024)), []).append(rk)

    def shapes(self, base, door=False):
        key = (base, door)
        if key in self.cache:
            return self.cache[key]
        out = []
        m = self.model_of(base)
        if m:
            try:
                data = self.gd.read_file(m)
                try:
                    for s in hkshape.collision_shapes(data):
                        if s['i'] and (door or s['layer'] in hkshape.LAYERS_SOLID):
                            out.append((s['v'], s['i']))
                except hkshape.Unread:
                    pass
                if door and not out:
                    for s in nif.mesh_from_nif(data):
                        out.append((s['p'], s['i']))
            except Exception:
                pass
        self.cache[key] = out
        return out

    def near(self, x, y):
        for gx in (-1, 0, 1):
            for gy in (-1, 0, 1):
                for rk in self.grid.get((int(x // 1024) + gx, int(y // 1024) + gy), ()):
                    r = self.refs[rk][1]
                    if abs(r['p'][0] - x) < NEAR and abs(r['p'][1] - y) < NEAR:
                        yield rk, r

    def door(self, rk, out, door_b, p=None):
        """out: the outward unit vector in x, y; door_b: the door's OBND; p: the door's place if not where it stands."""
        r = self.refs[rk][1]
        p = p or r['p']
        s = float(r.get('s') or 1.0)
        rz = p[5]
        c, sn = math.cos(rz), math.sin(rz)
        thin_x = (door_b[3] - door_b[0]) < (door_b[4] - door_b[1])
        tx, ty = (-out[1], out[0])
        width = ((door_b[4] - door_b[1]) if thin_x else (door_b[3] - door_b[0])) * s
        foot = p[2] + door_b[2] * s
        height = (door_b[5] - door_b[2]) * s
        # (the middle of the door's bounds: some doors are made round their hinge edge, NVCraftsmanHomeDoor's 0..128)
        mx, my = (door_b[0] + door_b[3]) / 2.0 * s, (door_b[1] + door_b[4]) / 2.0 * s
        q = (p[0] + mx * c + my * sn, p[1] - mx * sn + my * c)
        eye = (q[0] + out[0] * EYE_OUT, q[1] + out[1] * EYE_OUT, foot + EYE_Z)
        lo, hi = eye[0] - 400, eye[0] + 400
        # the triangles that could stand between: everything near, in the world
        mine, others = [], []
        for ork, orr in self.near(p[0], p[1]):
            isdoor = ork == rk
            shapes = self.shapes(orr['base'], door=isdoor)
            if not shapes:
                continue
            pp = p if isdoor else orr['p']
            m = _mat(pp[3:6])
            for flat, idx in shapes:
                for tri in _tris(flat, idx, m, pp[:3], float(orr.get('s') or 1.0)):
                    xs = (tri[0][0], tri[1][0], tri[2][0])
                    ys = (tri[0][1], tri[1][1], tri[2][1])
                    if max(xs) < min(eye[0], p[0]) - 200 or min(xs) > max(eye[0], p[0]) + 200:
                        continue
                    if max(ys) < min(eye[1], p[1]) - 200 or min(ys) > max(eye[1], p[1]) + 200:
                        continue
                    (mine if isdoor else others).append((tri, orr['base']))
        hits, rays, by = 0, 0, {}
        for iu in range(GRID_U):
            u = (iu / (GRID_U - 1) - 0.5) * width * 0.8
            for iz in range(GRID_Z):
                z = foot + height * (0.12 + 0.76 * iz / (GRID_Z - 1))
                tgt = (q[0] + tx * u, q[1] + ty * u, z)
                d = (tgt[0] - eye[0], tgt[1] - eye[1], tgt[2] - eye[2])
                ln = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
                d = (d[0] / ln, d[1] / ln, d[2] / ln)
                best, what = None, None
                for tri, base in mine:
                    t = _hit(eye, d, tri)
                    if t is not None and t < ln + 60 and (best is None or t < best):
                        best, what = t, 'door'
                for tri, base in others:
                    t = _hit(eye, d, tri)
                    if t is not None and t < ln + 60 and (best is None or t < best):
                        best, what = t, base
                rays += 1
                if what == 'door':
                    hits += 1
                elif what:
                    by[what] = by.get(what, 0) + 1
        return {'hits': hits, 'rays': rays, 'blocked_by': by, 'door_tris': len(mine)}
