"""Where a door puts you: clear of everything solid, on the navmesh, facing out (the user's third report, 23 Nov 2026: out of
a door and inside a rusted lean-to; first at FOLabWaikiki 96192, 58800).

Every link (a ref's XTEL: door, arrival) is judged at its arrival, in the world or place its door is in, against every ref's
solid collision there (buildings, shacks, lean-tos, scaffolds, rubble: whatever stands there now):

  (blocked and inside are errors: a player comes out in something; off_mesh and facing are warnings)

  blocked   something solid within BODY of the arrival's upright line between KNEE and HEAD over the feet
  inside    (outside only) a roof over it within ROOF and walls round it within WALLS in most directions
  off_mesh  not on the cell's navmesh (when the cell has one)
  facing    not facing away from the door it came out of

`check(gd, pr)` -> {'links', 'bad': [row], 'counts'}; `fix_ops(gd, pr, rows)` -> (ops, report): each failing arrival moved
out from its door along the door's outward face STEP at a time (a little to either side too) to the first spot that
passes everything, facing out. `py -3 app/arrivalcheck.py [mod]` prints the counts and exits 1 if any door puts you in
something (`errors_of`): an install script runs it last and stops on 1."""
import math
import os
import struct

import hkshape
import navgen

BODY = 24.0            # (an actor's radius, a little over)
KNEE, HEAD = 20.0, 112.0
ROOF = 420.0
WALLS = 480.0
WALLS_MOST = 5          # (of 8 directions)
STEP = 16.0
FAR = 900.0
NEAR_ONLY = 300.0      # (an arrival that is only off the navmesh moves no further than this)
TURN = 80             # (degrees either side of the door's face the search fans to)
NEAR = 1400.0


def _world(flat, idx, rot, pos, s):
    (a, b, c), (d, e, f), (g, h, i) = navgen._turn(*rot)
    pts = [(pos[0] + s * (a * flat[k] + b * flat[k + 1] + c * flat[k + 2]),
            pos[1] + s * (d * flat[k] + e * flat[k + 1] + f * flat[k + 2]),
            pos[2] + s * (g * flat[k] + h * flat[k + 1] + i * flat[k + 2])) for k in range(0, len(flat) - 2, 3)]
    out = []
    for k in range(0, len(idx) - 2, 3):
        t = (pts[idx[k]], pts[idx[k + 1]], pts[idx[k + 2]])
        out.append((t, min(v[0] for v in t), max(v[0] for v in t), min(v[1] for v in t), max(v[1] for v in t),
                    min(v[2] for v in t), max(v[2] for v in t)))
    return out


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


DIRS = [(math.cos(k * math.pi / 4), math.sin(k * math.pi / 4)) for k in range(8)]


class World:
    """Everything solid the mod stands, by world or place, for rays."""

    def __init__(self, gd, pr):
        import recordio
        self.gd, self.pr = gd, pr
        self.refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items()
                     if not r.get('removed') and r.get('p') and r.get('base') and r['p'][2] > -20000}
        self._recordio = recordio
        self.models, self.tris, self.groups = {}, {}, {}
        self.unread = set()          # (models that couldn't be read: they stand as nothing)
        self.grid = {}
        for rk, (ck, r) in self.refs.items():
            self.grid.setdefault((self.group(ck), int(r['p'][0] // 1024), int(r['p'][1] // 1024)), []).append(rk)

    def group(self, ck):
        if ck not in self.groups:
            try:
                w = self.gd.ext_cells.get(self.gd.from_key(ck))
            except Exception:
                w = None
            self.groups[ck] = ('world', w) if w is not None else ('place', ck)
        return self.groups[ck]

    def outside(self, group):
        """Open ground: a world's, but not a hotel's small world (its lobby is inside, under a roof by design)."""
        if group[0] != 'world':
            return False
        if not hasattr(self, '_views'):
            try:
                import hotelinside
                self._views = {v['world'] for v in hotelinside.VIEWS.values()}
            except Exception:
                self._views = set()
        return self.gd.edid(group[1]) not in self._views

    def model_path(self, base):
        try:
            if base.startswith('+'):
                rec = self.pr.records.get(base)
                m = self._recordio.field(rec, 'MODL') if rec else None
                return ('meshes' + chr(92) + m) if m else None
            t, e, f, m = self.gd.describe(self.gd.from_key(base))
            return self.gd.model_path(t, m) if m else None
        except Exception:
            return None

    def read(self, path):
        """A model's bytes: the mod's own files first, as FOLab sees them, whether or not a server has the mod open (run
        on its own this module read none of them: every FOLab piece stood as nothing, 23 Nov 2026)."""
        try:
            import library
            own = os.path.join(library.assets_dir(self.pr), path)
            if os.path.isfile(own):
                with open(own, 'rb') as f:
                    return f.read()
        except Exception:
            pass
        return self.gd.read_file(path)

    def solid(self, base):
        if base not in self.models:
            out = []
            path = self.model_path(base)
            if path:
                try:
                    for s in hkshape.collision_shapes(self.read(path)):
                        if s['i'] and s['layer'] in hkshape.LAYERS_SOLID:
                            out.append((s['v'], s['i']))
                except Exception:
                    self.unread.add(path)
            self.models[base] = out
        return self.models[base]

    def ref_tris(self, rk):
        if rk not in self.tris:
            ck, r = self.refs[rk]
            out = []
            for flat, idx in self.solid(r['base']):
                out += _world(flat, idx, r['p'][3:6], r['p'][:3], float(r.get('s') or 1.0))
            self.tris[rk] = out
        return self.tris[rk]

    def around(self, group, x, y, reach, skip=()):
        out = []
        for gx in range(int((x - NEAR) // 1024), int((x + NEAR) // 1024) + 1):
            for gy in range(int((y - NEAR) // 1024), int((y + NEAR) // 1024) + 1):
                for rk in self.grid.get((group, gx, gy), ()):
                    if rk in skip:
                        continue
                    for t in self.ref_tris(rk):
                        if t[2] >= x - reach and t[1] <= x + reach and t[4] >= y - reach and t[3] <= y + reach:
                            out.append((t, rk))
        return out

    def judge(self, group, x, y, z, outside, skip=()):
        """(blocked by, inside) at feet x, y, z: blocked by a ref within BODY between KNEE and HEAD; inside a roof and walls."""
        near = self.around(group, x, y, BODY + 2, skip)
        for h in (KNEE, (KNEE + HEAD) / 2.0, HEAD):
            o = (x, y, z + h)
            for dx, dy in DIRS:
                for t, rk in near:
                    if t[5] <= o[2] <= t[6] or (t[5] - 2 <= o[2] <= t[6] + 2):
                        d = _hit(o, (dx, dy, 0.0), t[0])
                        if d is not None and d < BODY:
                            return rk, False
        for t, rk in near:                         # (something low or hung in the body's column)
            d = _hit((x, y, z + HEAD), (0.0, 0.0, -1.0), t[0])
            if d is not None and d < HEAD - KNEE:
                return rk, False
        if not outside:
            return None, False
        wide = self.around(group, x, y, WALLS, skip)
        roof = any(_hit((x, y, z + KNEE), (0.0, 0.0, 1.0), t[0]) is not None and _hit((x, y, z + KNEE), (0.0, 0.0, 1.0), t[0]) < ROOF
                   for t, rk in wide if t[1] <= x <= t[2] and t[3] <= y <= t[4])
        if not roof:
            return None, False
        walls = 0
        o = (x, y, z + 60.0)
        for dx, dy in DIRS:
            if any((lambda d: d is not None and d < WALLS)(_hit(o, (dx, dy, 0.0), t[0])) for t, rk in wide if t[5] <= o[2] <= t[6]):
                walls += 1
        return None, walls >= WALLS_MOST


def on_navmesh(pr, ck, x, y, z):
    m = pr.navmesh.get(ck)
    if not m:
        return None
    vs = m['verts']
    for t in m['tris']:
        a, b, c = (vs[i] for i in t[:3])
        if abs((a[2] + b[2] + c[2]) / 3.0 - z) > 120:
            continue
        def s_(p1, q1, r1): return (p1[0] - r1[0]) * (q1[1] - r1[1]) - (q1[0] - r1[0]) * (p1[1] - r1[1])
        d = (s_((x, y), a, b), s_((x, y), b, c), s_((x, y), c, a))
        if not (min(d) < 0 < max(d)):
            return True
    return False


def _cell_at(gd, W, ck, x, y):
    g = W.group(ck)
    if g[0] != 'world':
        return ck
    c = gd.grid(g[1]).get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else ck


def _door_normal(gd, pr, W, door, toward):
    """The door's outward face in x, y: its bounds' thin side, turned to `toward` (where its arrival is, or should be)."""
    r = W.refs[door][1]
    base = r['base']
    try:
        if base.startswith('+'):
            s = next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')
            b = [int(f['value']) for f in s['fields'] if 'name' in f]
        else:
            b = list(struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12]))
    except Exception:
        b = [-60, -10, 0, 60, 10, 200]
    rz = r['p'][5]
    c, sn = math.cos(rz), math.sin(rz)
    lx, ly = (1.0, 0.0) if (b[3] - b[0]) < (b[4] - b[1]) else (0.0, 1.0)
    nx, ny = lx * c + ly * sn, -lx * sn + ly * c
    if nx * toward[0] + ny * toward[1] < 0:
        nx, ny = -nx, -ny
    return nx, ny


def check(gd, pr, W=None, progress=None):
    """{'links', 'bad': [{'ref', 'cell', 'door', 'door_cell', 'p', 'why': [..], 'by'}], 'counts': {why: n}}."""
    W = W or World(gd, pr)
    bad, counts, n = [], {}, 0
    for k, (rk, (ck, r)) in enumerate(list(W.refs.items())):
        t = r.get('tel') or {}
        d = t.get('door')
        if not d or not t.get('p') or d not in W.refs:
            continue
        n += 1
        if progress and n % 250 == 0:
            progress(n)
        dck, dr = W.refs[d]
        a = t['p']
        g = W.group(dck)
        outside = W.outside(g)
        z = a[2] - 8.0
        why = []
        by, inside = W.judge(g, a[0], a[1], z, outside, skip=(d,))
        if by:
            why.append('blocked')
        if inside:
            why.append('inside')
        mesh = on_navmesh(pr, _cell_at(gd, W, dck, a[0], a[1]), a[0], a[1], a[2])
        if mesh is False:
            why.append('off_mesh')
        vx, vy = a[0] - dr['p'][0], a[1] - dr['p'][1]
        if (vx or vy) and math.sin(a[5]) * vx + math.cos(a[5]) * vy < 0:
            why.append('facing')
        for w in why:
            counts[w] = counts.get(w, 0) + 1
        if why:
            bad.append({'ref': rk, 'cell': ck, 'door': d, 'door_cell': dck, 'p': list(a), 'why': why, 'by': by})
    return {'links': n, 'bad': bad, 'counts': counts}


def errors_of(res):
    """The rows that stop an install: a door that puts you in something (blocked or inside)."""
    return [row for row in res['bad'] if 'blocked' in row['why'] or 'inside' in row['why']]


def fix_ops(gd, pr, rows, W=None):
    """(ops, report): each failing arrival moved to the first spot out from its door that passes, facing out."""
    W = W or World(gd, pr)
    ops, report = [], {'moved': 0, 'turned': 0, 'left': []}
    for row in rows:
        d, dck = row['door'], row['door_cell']
        dr = W.refs[d][1]
        a = row['p']
        g = W.group(dck)
        outside = W.outside(g)
        if row['why'] == ['facing']:
            na = list(a)
            na[5] = round(math.atan2(a[0] - dr['p'][0], a[1] - dr['p'][1]) % math.tau, 4)
            ops.append({'op': 'tel', 'cell': row['cell'], 'ref': row['ref'], 'tel': dict(W.refs[row['ref']][1]['tel'], p=na)})
            report['turned'] += 1
            continue
        toward = (a[0] - dr['p'][0], a[1] - dr['p'][1])
        nx, ny = _door_normal(gd, pr, W, d, toward if (toward[0] or toward[1]) else (0.0, 1.0))
        z = a[2] - 8.0
        found = None
        k = STEP * 4
        base_ang = math.atan2(nx, ny)
        serious = 'blocked' in row['why'] or 'inside' in row['why']
        far = FAR if serious else NEAR_ONLY          # (only off the navmesh: not worth coming out far from the door)
        loose = None                                 # (clear and open but off the navmesh: taken if nothing better)
        while k <= far and not found:
            # (straight out first, then fanning to either side, up to TURN off the door's face)
            for da in [0.0] + [s_ * a_ for a_ in range(10, TURN + 1, 10) for s_ in (1, -1)]:
                ang = base_ang + math.radians(da)
                x = dr['p'][0] + math.sin(ang) * k
                y = dr['p'][1] + math.cos(ang) * k
                by, inside = W.judge(g, x, y, z, outside, skip=(d,))
                if by or inside:
                    continue
                if on_navmesh(pr, _cell_at(gd, W, dck, x, y), x, y, a[2]) is False:
                    if serious and loose is None:
                        loose = (x, y)
                    continue
                found = (x, y)
                break
            k += STEP
        if not found and loose:
            found = loose
            report['off_mesh_kept'] = report.get('off_mesh_kept', 0) + 1
        if not found:
            report['left'].append(row['ref'])
            continue
        na = [round(found[0], 2), round(found[1], 2), a[2], 0.0, 0.0, round(math.atan2(found[0] - dr['p'][0], found[1] - dr['p'][1]) % math.tau, 4)]
        ops.append({'op': 'tel', 'cell': row['cell'], 'ref': row['ref'], 'tel': dict(W.refs[row['ref']][1]['tel'], p=na)})
        report['moved'] += 1
    return ops, report


if __name__ == '__main__':
    import sys
    import gamedata
    import project
    import server
    server.not_while_playing = lambda: None
    server.GD = gamedata.GameData()
    server.BR = None
    p = project.Project.open(sys.argv[1] if len(sys.argv) > 1 else 'Waikiki')
    server.load_game(p)
    server.PR = p
    W = World(server.GD, p)
    res = check(server.GD, p, W, progress=lambda n: print(n, 'links', flush=True))
    if W.unread:
        print('models that could not be read (they stood as nothing):', len(W.unread), sorted(W.unread)[:20])
    errors = errors_of(res)
    print('links', res['links'], 'flagged', len(res['bad']), res['counts'], '| errors (in something):', len(errors))
    for row in errors[:40]:
        print('  ', row['ref'], row['why'], [round(v) for v in row['p'][:3]])
    sys.exit(1 if errors else 0)
