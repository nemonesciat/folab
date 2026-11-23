"""Would nv-rs give the "Open" prompt? Its crosshair pick, as read in nv-rs (engine-fallout-env ... run_006319e0.rs
fn_00631d60, engine-fallout-misc ... run_0070bbe0.rs; the Workshop's reading, 23 Nov 2026): a sweep collects every body
along the ray; a body on layer 1 whose shape is a MOPP tree, or on layer 4, 5 or 6, is hit by an exact ray against its
shape; any other body (a door: layer 1, a convex box) is hit against its ref's DRAWN triangles; the nearest hit wins.
So a building's MOPP wall standing in front of a door's drawn leaf takes the pick there (the user: only the door's edge
gave "Door to House").

Picker(gd, pr, refs, model_of).door(rk, out, box) -> {'spots', 'picked', 'by': {base: n}}: 5 x 5 spots over the door's
face (its bounds, the middle 80% across, 10-90% up), from where a player stands (STAND out, at EYE and at CHEST over the
door's foot), each counted when the door's drawn triangles are the nearest hit."""
import math

import hkshape
import navgen
import nif

STAND = 60.0
EYES = (120.0, 84.0)            # (eye height; 1.2 m)
GRID = 5
NEAR = 700.0
EXACT_LAYERS = (4, 5, 6)


def _bodies(data):
    """[(layer, is a MOPP tree)] of each rigid body of a model, in the order collision_shapes adds their shapes."""
    n = nif.Nif(data)
    out = []
    seen = set()

    def visit(i):
        if i in seen:
            return
        seen.add(i)
        b = n.block(i)
        if not b:
            return
        c = b.get('collision', -1)
        if 0 <= c < len(n.types) and n.types[c] == 'bhkCollisionObject':
            r = nif.Reader(n.data, n.offsets[c])
            r.i32(); r.u16()
            body = r.i32()
            if 0 <= body < len(n.types) and n.types[body] in ('bhkRigidBody', 'bhkRigidBodyT'):
                rb = nif.Reader(n.data, n.offsets[body])
                shape = rb.i32()
                layer = rb.u32() & 0x7F
                out.append((layer, 0 <= shape < len(n.types) and n.types[shape] == 'bhkMoppBvTreeShape'))
        for k in b.get('children', ()):
            visit(k)
    if n.blocks:
        visit(0)
    return out


def _world(flat, idx, rot, pos, s):
    (a, b, c), (d, e, f), (g, h, i) = navgen._turn(*rot)
    pts = [(pos[0] + s * (a * flat[k] + b * flat[k + 1] + c * flat[k + 2]),
            pos[1] + s * (d * flat[k] + e * flat[k + 1] + f * flat[k + 2]),
            pos[2] + s * (g * flat[k] + h * flat[k + 1] + i * flat[k + 2])) for k in range(0, len(flat) - 2, 3)]
    return [(pts[idx[k]], pts[idx[k + 1]], pts[idx[k + 2]]) for k in range(0, len(idx) - 2, 3)]


def _hit(o, d, tri):
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


class Picker:
    def __init__(self, gd, pr, refs, model_of, group_of):
        """refs: {ref: (cell, ref)}; model_of(base) -> path under Data or None; group_of(cell) -> which world or place a
        cell is in (things pick only within it: the hotels' small worlds stand copies at the city's spots)."""
        self.gd, self.refs, self.model_of, self.group_of = gd, refs, model_of, group_of
        self.models = {}
        self.grid = {}
        for rk, (ck, r) in refs.items():
            p = r.get('p')
            if p and p[2] > -20000 and r.get('base'):
                self.grid.setdefault((group_of(ck), int(p[0] // 1024), int(p[1] // 1024)), []).append(rk)

    def model(self, base):
        """(exact shapes [(flat, idx)], drawn shapes or None): drawn only when some body is picked by its drawn look."""
        if base in self.models:
            return self.models[base]
        exact, drawn = [], None
        path = self.model_of(base)
        if path:
            try:
                data = self.gd.read_file(path)
                bodies = _bodies(data)
                shapes = hkshape.collision_shapes(data)
                # (shapes come body by body; a shape's layer is its body's: match them by layer and order)
                bi = 0
                exact_layers = {L for L, mopp in bodies if (L == 1 and mopp) or L in EXACT_LAYERS}
                other = any(not ((L == 1 and mopp) or L in EXACT_LAYERS) for L, mopp in bodies)
                for s in shapes:
                    if s['i'] and s['layer'] in exact_layers:
                        exact.append((s['v'], s['i']))
                if other:
                    drawn = [(s['p'], s['i']) for s in nif.mesh_from_nif(data)]
            except Exception:
                pass
        self.models[base] = (exact, drawn)
        return self.models[base]

    def near(self, group, x, y):
        for gx in (-1, 0, 1):
            for gy in (-1, 0, 1):
                for rk in self.grid.get((group, int(x // 1024) + gx, int(y // 1024) + gy), ()):
                    r = self.refs[rk][1]
                    if abs(r['p'][0] - x) < NEAR and abs(r['p'][1] - y) < NEAR:
                        yield rk, r

    def door(self, rk, out, box, p=None):
        ck, r = self.refs[rk]
        p = p or r['p']
        s = float(r.get('s') or 1.0)
        rz = p[5]
        c, sn = math.cos(rz), math.sin(rz)
        thin_x = (box[3] - box[0]) < (box[4] - box[1])
        width = ((box[4] - box[1]) if thin_x else (box[3] - box[0])) * s
        # (the door's own facing, from its bounds' thin side; `out` only says which side is out: an arrival is seldom
        # straight in front, and a grid laid across it missed the leaf)
        lx, ly = (1.0, 0.0) if thin_x else (0.0, 1.0)
        nx, ny = lx * c + ly * sn, -lx * sn + ly * c
        if nx * out[0] + ny * out[1] < 0:
            nx, ny = -nx, -ny
        out = (nx, ny)
        height = (box[5] - box[2]) * s
        mx, my = (box[0] + box[3]) / 2.0 * s, (box[1] + box[4]) / 2.0 * s
        q = (p[0] + mx * c + my * sn, p[1] - mx * sn + my * c)
        foot = p[2] + box[2] * s
        tx, ty = -out[1], out[0]
        group = self.group_of(ck)
        lo_x, hi_x = min(q[0], q[0] + out[0] * STAND) - 160, max(q[0], q[0] + out[0] * STAND) + 160
        lo_y, hi_y = min(q[1], q[1] + out[1] * STAND) - 160, max(q[1], q[1] + out[1] * STAND) + 160

        def keep(tri):
            return not (max(v[0] for v in tri) < lo_x or min(v[0] for v in tri) > hi_x or
                        max(v[1] for v in tri) < lo_y or min(v[1] for v in tri) > hi_y)
        mine, others = [], []
        for ork, orr in self.near(group, q[0], q[1]):
            exact, drawn = self.model(orr['base'])
            pp = p if ork == rk else orr['p']
            ss = float(orr.get('s') or 1.0)
            if ork == rk:
                # (the door by the same rule as any body: an exact ray on a layer-4-6 or MOPP body, its drawn look else)
                for flat, idx in list(exact) + list(drawn or []):
                    mine += [t for t in _world(flat, idx, pp[3:6], pp[:3], ss) if keep(t)]
                continue
            for flat, idx in exact:
                others += [(t, orr['base']) for t in _world(flat, idx, pp[3:6], pp[:3], ss) if keep(t)]
            for flat, idx in (drawn or []):
                others += [(t, orr['base']) for t in _world(flat, idx, pp[3:6], pp[:3], ss) if keep(t)]
        spots = picked = 0
        by = {}
        for eye_z in EYES:
            eye = (q[0] + out[0] * STAND, q[1] + out[1] * STAND, foot + eye_z)
            for iu in range(GRID):
                u = (iu / (GRID - 1) - 0.5) * width * 0.8
                for iz in range(GRID):
                    z = foot + height * (0.1 + 0.8 * iz / (GRID - 1))
                    tgt = (q[0] + tx * u, q[1] + ty * u, z)
                    d = (tgt[0] - eye[0], tgt[1] - eye[1], tgt[2] - eye[2])
                    ln = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
                    d = (d[0] / ln, d[1] / ln, d[2] / ln)
                    mt = min((t for t in (_hit(eye, d, tri) for tri in mine) if t is not None), default=None)
                    best, what = None, None
                    for tri, base in others:
                        t = _hit(eye, d, tri)
                        if t is not None and (best is None or t < best):
                            best, what = t, base
                    spots += 1
                    if mt is not None and (best is None or mt <= best):
                        picked += 1
                    elif what:
                        by[what] = by.get(what, 0) + 1
                    else:
                        by['(the door not hit)'] = by.get('(the door not hit)', 0) + 1
        return {'spots': spots, 'picked': picked, 'by': by, 'door_tris': len(mine), 'normal': out}
