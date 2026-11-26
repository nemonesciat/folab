"""Every doorway of every building the mod stands, and what is in it (the user, 25 Nov 2026, after a black doorway by the
new game's start ended a stream: "fix everything, doorways ... I can't even get 5 minutes of consistent gameplay").

The rule (every-doorway-goes-somewhere): a doorway opens into a real place, or is visibly shut for a reason you can see (a
locked door, boards, a barricade). A black opening never.

**Doorways from the model itself**, not from the catalogue's door lists: the building's collision cut at knee, waist and
head height over its floor (`SLICES`), drawn on a grid of `STEP`; an opening is where the outside, flooded round the
walls, reaches into what the walls enclose once gaps up to `PLUG` are closed. A gap open at all three heights is a way
a body walks in (a window is shut at the knee). Each opening: its middle, its width, the way out (`Opening`).

**What is in it**, for each placed building, within `NEAR` of the opening's middle (scaled with the building):
  linked    a door that leads somewhere (XTEL / the mod's `tel`)
  locked    a door with a lock (XLOC / the mod's lock)
  closed    a closure you can see: a door static, boards, a barricade, a wall piece (`CLOSURE`)
  dead      a door that leads nowhere and isn't locked (it swings open on nothing)
  nothing   none of those

    A = Audit(gd, pr, world); rows = A.run()     every building's openings and what is in each
    summary(rows)                                counts by verdict, the 'nothing' and 'dead' listed
    py -3 app/doorways.py [--home H] [--near x,y,r]
"""
import math
import re

import recordio

STEP = 16.0
SLICES = (40.0, 100.0, 160.0)       # (over the floor at the doorway)
PLUG = 6                            # (gaps up to about this many steps either side are closed to find what is enclosed)
WIDE_LEAST = 56.0                   # (narrower than this a body doesn't pass: not a doorway)
NEAR = 140.0
# model editor ID: doorways the game draws but never fills on any of its uses (found by eye from four-side views),
# [{'x', 'y', 'z', 'out': (ux, uy) in the model's frame, 'from': 'drawn'}]; doorfill.extra_slots fills it from its EXTRA
EXTRA_SLOTS = {}
RANK = {'linked': 0, 'locked': 1, 'closed': 2, 'dead': 3, 'covered': 4}
SAME = 80.0                        # (townbuild.SHUT_SAME: things this near are in one doorway)
CLOSURE = re.compile(r'doorstatic|barricade|plank|board|boarded|doorframeblock|doorblock|fencegate|shutter|grate|bars|'
                     r'gatedoor|wallpiece|sheetmetal|tarp|curtain', re.I)
NOT_CLOSURE = re.compile(r'blackplane', re.I)       # (the game's black sheet: that IS the black opening)


def _cells_line(out, p, q, x0, y0, w, h):
    n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / (STEP / 2)))
    for k in range(n + 1):
        x, y = p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n
        i, j = int((x - x0) // STEP), int((y - y0) // STEP)
        if 0 <= i < w and 0 <= j < h:
            out.add((i, j))


def _grow(cells, r):
    ring = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if di * di + dj * dj <= r * r + r]
    return {(i + di, j + dj) for i, j in cells for di, dj in ring}


def _flood(w, h, blocked, start=(0, 0)):
    seen, todo = set(), [start]
    while todo:
        i, j = todo.pop()
        if (i, j) in seen or (i, j) in blocked or not (0 <= i < w and 0 <= j < h):
            continue
        seen.add((i, j))
        todo += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
    return seen


def openings(tris, box, floor=0.0):
    """[{'x', 'y', 'wide', 'out': (ux, uy)}] in the model's frame: the ways a body walks in."""
    import indoors
    if not tris:
        return []
    m = PLUG + 4
    x0, y0 = box[0] - m * STEP, box[1] - m * STEP
    w = int(math.ceil((box[3] - box[0]) / STEP)) + 2 * m + 1
    h = int(math.ceil((box[4] - box[1]) / STEP)) + 2 * m + 1
    walls = set()
    for a, b, c in tris:
        for z in SLICES:
            seg = indoors._slice(a, b, c, floor + z)
            if seg:
                _cells_line(walls, seg[0], seg[1], x0, y0, w, h)
    if not walls:
        return []
    body = _grow(walls, 1)                  # (a body's half width off every wall)
    outside = _flood(w, h, body)
    shut = _grow(walls, PLUG)
    outer = _flood(w, h, shut)
    inner = {(i, j) for i in range(w) for j in range(h) if (i, j) not in outer and (i, j) not in shut}
    if not inner:
        return []
    inner_g = _grow(inner, PLUG)
    gap = (outside & inner_g) - body
    if not gap:
        return []
    # the gap's cells at the walls' line: grouped, each group an opening
    ix = sum(i for i, _j in inner) / len(inner)
    iy = sum(j for _i, j in inner) / len(inner)
    out, seen = [], set()
    for c in sorted(gap):
        if c in seen:
            continue
        grp, todo = [], [c]
        while todo:
            q = todo.pop()
            if q in seen or q not in gap:
                continue
            seen.add(q)
            grp.append(q)
            todo += [(q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1)]
        # only the part of the group that is in the walls' band (the doorway itself, not the room behind)
        band = [q for q in grp if q in shut]
        if not band:
            continue
        cx = sum(q[0] for q in band) / len(band)
        cy = sum(q[1] for q in band) / len(band)
        ux, uy = cx - ix, cy - iy
        d = math.hypot(ux, uy) or 1.0
        ux, uy = ux / d, uy / d
        # width across the way out
        across = [(q[0] - cx) * -uy + (q[1] - cy) * ux for q in band]
        wide = (max(across) - min(across) + 1) * STEP + 2 * STEP      # (+ the body margin taken off each side)
        if wide < WIDE_LEAST:
            continue
        out.append({'x': round(x0 + (cx + 0.5) * STEP, 1), 'y': round(y0 + (cy + 0.5) * STEP, 1), 'wide': round(wide),
                    'out': (round(ux, 3), round(uy, 3)), 'cells': len(band)})
    return out


RAY_STEP = 12.0
DEEPER = 48.0                       # (a doorway's rays go this much deeper than the side's wall)
FROM_OUT = 200.0                    # (rays start this far outside the box)


def drawn_doorways(shapes, floor, box):
    """Doorways read from what the model draws: on each side of its box, rays cast inward at knee, waist and head height
    over `floor`; where all three go `DEEPER` past the side's own wall (its usual depth there) for `WIDE_LEAST` or more,
    a body could walk in, so the game must put something in it. [{'x', 'y', 'z', 'wide', 'out', 'from': 'drawn'}]"""
    import numpy as np
    tris = []
    for s in shapes:
        v = s['p']
        pts = np.asarray(v, dtype=float).reshape(-1, 3) if v and not isinstance(v[0], (list, tuple)) else np.asarray(v, dtype=float)
        idx = np.asarray(s['i'], dtype=int).reshape(-1, 3)
        if len(idx):
            tris.append(pts[idx])
    if not tris:
        return []
    T = np.concatenate(tris)                    # (n, 3, 3)
    out = []
    # what the walls enclose (gaps up to PLUG either side closed): a doorway's rays must go into it, not along a wall's
    # outside past a corner, a porch or an overhang
    import indoors
    m = PLUG + 4
    gx0, gy0 = box[0] - m * STEP, box[1] - m * STEP
    gw = int(math.ceil((box[3] - box[0]) / STEP)) + 2 * m + 1
    gh = int(math.ceil((box[4] - box[1]) / STEP)) + 2 * m + 1
    walls = set()
    for t in T:
        a, b, c = tuple(t[0]), tuple(t[1]), tuple(t[2])
        for dz in SLICES:
            seg = indoors._slice(a, b, c, floor + dz)
            if seg:
                _cells_line(walls, seg[0], seg[1], gx0, gy0, gw, gh)
    shut = _grow(walls, PLUG)
    outer = _flood(gw, gh, shut)
    inner = {(i, j) for i in range(gw) for j in range(gh) if (i, j) not in outer and (i, j) not in shut}
    inner = _grow(inner, PLUG - 1) if inner else set()

    def inside(x, y):
        return (int((x - gx0) // STEP), int((y - gy0) // STEP)) in inner
    x0, y0, x1, y1 = box[0], box[1], box[3], box[4]
    # side: (axis the ray runs along, sign inward, fixed start, the coordinate along the side, its range, way out)
    sides = [(1, +1, y0 - FROM_OUT, 0, (x0, x1), (0, -1)), (1, -1, y1 + FROM_OUT, 0, (x0, x1), (0, 1)),
             (0, +1, x0 - FROM_OUT, 1, (y0, y1), (-1, 0)), (0, -1, x1 + FROM_OUT, 1, (y0, y1), (1, 0))]
    for run_ax, sign, start, along_ax, (a0, a1), way in sides:
        a_vals = np.arange(a0 + RAY_STEP / 2, a1, RAY_STEP)
        if not len(a_vals):
            continue
        P = T[:, :, along_ax]                   # (n, 3): the triangles' coordinate along the side
        Z = T[:, :, 2]
        R = T[:, :, run_ax]
        depth = np.full((len(SLICES), len(a_vals)), np.inf)
        for hi, dz in enumerate(SLICES):
            z = floor + dz
            for k, a in enumerate(a_vals):
                # point (a, z) in each triangle's projection onto (along, z): barycentric
                ax, az = P[:, 0], Z[:, 0]
                bx, bz = P[:, 1] - ax, Z[:, 1] - az
                cx, cz = P[:, 2] - ax, Z[:, 2] - az
                px, pz = a - ax, z - az
                den = bx * cz - cx * bz
                ok = np.abs(den) > 1e-9
                with np.errstate(divide='ignore', invalid='ignore'):
                    u = (px * cz - cx * pz) / den
                    w = (bx * pz - px * bz) / den
                hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1)
                if not hit.any():
                    continue
                r = R[hit, 0] + u[hit] * (R[hit, 1] - R[hit, 0]) + w[hit] * (R[hit, 2] - R[hit, 0])
                d = (r - start) * sign
                d = d[d > 0]
                if len(d):
                    depth[hi, k] = d.min()
        mid = depth[1][np.isfinite(depth[1])]
        if not len(mid):
            continue
        wall = float(np.median(mid))
        open_ = np.all(depth > wall + DEEPER, axis=0)
        # runs of open rays
        k = 0
        while k < len(a_vals):
            if not open_[k]:
                k += 1
                continue
            j = k
            while j + 1 < len(a_vals) and open_[j + 1]:
                j += 1
            wide = (j - k + 1) * RAY_STEP
            if WIDE_LEAST <= wide <= 400:
                a = float((a_vals[k] + a_vals[j]) / 2)
                face = start + sign * wall                          # (the side's wall, outer face)
                xy = [0.0, 0.0]
                xy[along_ax] = a
                xy[run_ax] = float(face)
                probe = [xy[0], xy[1]]
                probe[run_ax] = float(face + sign * (DEEPER + 40))
                if inside(probe[0], probe[1]):
                    out.append({'x': round(xy[0], 1), 'y': round(xy[1], 1), 'z': float(floor), 'wide': round(wide), 'out': way,
                                'from': 'drawn'})
            k = j + 1
    return out


def _base_of(gd, pr, key):
    """(type, editor ID) of a base as the mod leaves it."""
    if key.startswith('+'):
        r = pr.records.get(key) or {}
        return r.get('type', ''), recordio.field(r, 'EDID') or ''
    try:
        f = gd.from_key(key)
        return gd.forms[f][1].tag, gd.edid(f) or ''
    except (KeyError, ValueError):
        return '', ''


def _door_state(gd, pr, rk, ch):
    """('linked' | 'locked' | 'dead', where it leads) of a door ref as the mod leaves it."""
    tel = ch.get('tel') if ch else None
    lock = None
    if ch and 'props' in ch and isinstance(ch['props'], dict) and 'lock' in ch['props']:
        lock = ch['props']['lock']
    if not rk.startswith('+'):
        try:
            f = gd.from_key(rk)
            fl = gd.fields(f)
            if tel is None and 'XTEL' in fl and not (ch and 'tel' in ch):
                tel = {'game': True}
            if lock is None and 'XLOC' in fl and not (ch and 'props' in ch and 'lock' in (ch['props'] or {})):
                lock = {'level': fl['XLOC'][0]}
        except (KeyError, ValueError):
            pass
    if tel:
        return 'linked', tel
    if lock and (lock.get('level', 0) or lock.get('key')):
        return 'locked', None
    return 'dead', None


class Audit:
    def __init__(self, gd, pr, world):
        self.gd, self.pr, self.world = gd, pr, world
        self.cache = {}

    def catalogue_slots(self):
        """{building base: [doorway {'x', 'y', 'z', 'from'}]}: every doorway the game fills on that building in any of its
        uses (townbuild's catalogue: the doors of the placement with most, and every doorway it shuts)."""
        if not hasattr(self, '_cat'):
            import indoors
            self._cat = {}
            for b in indoors.catalogue(self.gd):
                ways = []
                for d in list(b.get('doors', ())) + list(b.get('shut', ())):
                    if any(math.hypot(d['x'] - w['x'], d['y'] - w['y']) < SAME for w in ways):
                        continue
                    ways.append({'x': d['x'], 'y': d['y'], 'z': d['z'], 'from': 'board' if d.get('board') else 'door'})
                self._cat[b['key']] = (b['edid'], ways)
        return self._cat

    def base_openings(self, base):
        if base not in self.cache:
            import floatfit
            import indoors
            cat = self.catalogue_slots()
            if base.startswith('+') and base not in cat:
                # (a closed copy of a game building, closedswap's FOLabClosed<its editor ID>, same frame: its doorways)
                e = recordio.field(self.pr.records.get(base) or {'subs': []}, 'EDID') or ''
                if e.startswith('FOLabClosed'):
                    orig = next((k for k, (ed, _w) in cat.items() if ed == e[len('FOLabClosed'):]), None)
                    if orig:
                        edid, ways = cat[orig]
                        self.cache[base] = (e, list(ways) + list(EXTRA_SLOTS.get(edid, ())))
                        return self.cache[base]
            if base in cat:
                edid, ways = cat[base]
                self.cache[base] = (edid, list(ways) + list(EXTRA_SLOTS.get(edid, ())))
                return self.cache[base]
            btype, edid, model, ob = floatfit.base_info(self.gd, self.pr, base)
            got = []
            if floatfit.kind(btype, edid, model, ob) == 'building':
                path = indoors.model_of(self.gd, self.pr, base)
                tris = indoors.collision(self.gd, path) if path else []
                if tris:
                    floor = min(min(a[2], b[2], c[2]) for a, b, c in tris)
                    box = [min(min(t[k][0] for k in range(3)) for t in tris), min(min(t[k][1] for k in range(3)) for t in tris), floor,
                           max(max(t[k][0] for k in range(3)) for t in tris), max(max(t[k][1] for k in range(3)) for t in tris), 0]
                    got = openings(tris, box, self._floor(tris, floor))
            self.cache[base] = (edid, got)
        return self.cache[base]

    def _game_shut(self, base):
        import townbuild
        if base.startswith('+'):
            # (a closed copy of a game piece, closedswap's FOLabClosed<its editor ID>: as the game piece it copies)
            e = recordio.field(self.pr.records.get(base) or {'subs': []}, 'EDID') or ''
            if not e.startswith('FOLabClosed'):
                return False
            f = next((f for f, (_n, r) in self.gd.forms.items() if r.tag != 'DOOR' and self.gd.edid(f) == e[len('FOLabClosed'):]), None)
            return bool(f is not None and townbuild._shuts(self.gd, f))
        try:
            f = self.gd.from_key(base)
            return self.gd.forms[f][1].tag != 'DOOR' and townbuild._shuts(self.gd, f)
        except (KeyError, ValueError):
            return False

    @staticmethod
    def _floor(tris, lowest):
        """The floor a body walks in on: the most common height of near-flat collision over the lowest point."""
        import collections
        hs = collections.Counter()
        for a, b, c in tris:
            if abs(a[2] - b[2]) < 2 and abs(b[2] - c[2]) < 2:
                area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
                if area > 50:
                    hs[round(a[2] / 8) * 8] += area
        low = [z for z in hs if z <= lowest + 250]
        return max(low, key=lambda z: hs[z]) if low else lowest

    def run(self, near=None):
        import indoors
        gd, pr = self.gd, self.pr
        grid = gd.grid(self.world)
        things = []             # (ref, base, p, s, ck)
        doors = []              # (x, y, z, ref, ck, base edid, kind, state)
        for xy, c in grid.items():
            ck = gd.key(c)
            if near and math.hypot(xy[0] * 4096 + 2048 - near[0], xy[1] * 4096 + 2048 - near[1]) > near[2] + 6000:
                continue
            mine = (pr.cells.get(ck) or {}).get('refs', {})
            for rk, base, p, s in indoors.placed(gd, pr, ck):
                btype, edid = _base_of(gd, pr, base)
                if btype == 'DOOR':
                    st, tel = _door_state(gd, pr, rk, mine.get(rk))
                    doors.append((p[0], p[1], p[2], rk, ck, edid, 'door', st))
                elif btype in ('STAT', 'MSTT', 'SCOL', 'ACTI', 'FURN') and not NOT_CLOSURE.search(edid) and \
                        (CLOSURE.search(edid) or self._game_shut(base)):
                    doors.append((p[0], p[1], p[2], rk, ck, edid, 'closure', 'closed'))
                things.append((rk, base, p, float(s or 1.0), ck, xy))
        by_sq = {}
        for d in doors:
            by_sq.setdefault((int(d[0] // 512), int(d[1] // 512)), []).append(d)
        rows = []
        for rk, base, p, s, ck, xy in things:
            if near and math.hypot(p[0] - near[0], p[1] - near[1]) > near[2]:
                continue
            edid, ops = self.base_openings(base)
            if not ops:
                continue
            rz = p[5] if len(p) > 5 else 0.0
            co, si = math.cos(rz), math.sin(rz)
            for o in ops:
                # (the game turns clockwise: world = R(-rz) * local)
                wx = p[0] + (o['x'] * co + o['y'] * si) * s
                wy = p[1] + (-o['x'] * si + o['y'] * co) * s
                wz = p[2] + o.get('z', 0.0) * s
                out = o.get('out')
                found = []
                sq = (int(wx // 512), int(wy // 512))
                for i in range(sq[0] - 1, sq[0] + 2):
                    for j in range(sq[1] - 1, sq[1] + 2):
                        for d in by_sq.get((i, j), ()):
                            dist = math.hypot(d[0] - wx, d[1] - wy)
                            if dist <= SAME * max(1.0, s) and abs(d[2] - wz) < 160 * max(1.0, s):
                                found.append((RANK[d[7]], dist, d))
                found.sort(key=lambda f: (f[0], f[1]))
                best = found[0] if found else None
                verdict = best[2][7] if best else 'nothing'
                rows.append({'ref': rk, 'cell': ck, 'cxy': xy, 'building': edid, 'base': base, 'p': [round(v, 1) for v in p[:3]],
                             'rz': rz, 's': s, 'at': [round(wx, 1), round(wy, 1), round(wz, 1)],
                             'out': [round(out[0] * co + out[1] * si, 3), round(-out[0] * si + out[1] * co, 3)] if out else None,
                             'wide': o.get('wide'), 'local': [o['x'], o['y'], o.get('z', 0.0)], 'from': o.get('from', 'model'),
                             'verdict': verdict, 'by': (best[2][5], best[2][3], round(best[1]), best[2][4]) if best else None})
        # (boards the game stands in FRONT of a door it uses, ~90-120 out, are its own doorway slot in the catalogue; with
        # the door there and open (doorclear took the boards out), that slot is the same doorway: covered)
        by_ref = {}
        for r in rows:
            by_ref.setdefault(r['ref'], []).append(r)
        linked = [d for d in doors if d[7] == 'linked']
        lsq = {}
        for d in linked:
            lsq.setdefault((int(d[0] // 512), int(d[1] // 512)), []).append(d)
        for rs in by_ref.values():
            for r in rs:
                if r['verdict'] == 'nothing' and r['from'] == 'board':
                    # (any door that leads somewhere this near: the boards would stand in its way out)
                    sx, sy = int(r['at'][0] // 512), int(r['at'][1] // 512)
                    if any(math.hypot(d[0] - r['at'][0], d[1] - r['at'][1]) < 2.75 * SAME
                           for i in range(sx - 1, sx + 2) for j in range(sy - 1, sy + 2) for d in lsq.get((i, j), ())):
                        r['verdict'] = 'covered'
                        continue
                    for o in rs:
                        if o is not r and o['from'] == 'door' and o['verdict'] in ('linked', 'locked', 'closed') and \
                                math.hypot(o['local'][0] - r['local'][0], o['local'][1] - r['local'][1]) < 2.5 * SAME:
                            r['verdict'] = 'covered'
                            break
        return rows


def summary(rows):
    import collections
    c = collections.Counter(r['verdict'] for r in rows)
    bad = [r for r in rows if r['verdict'] in ('nothing', 'dead')]
    kinds = collections.Counter((r['building'], r['verdict']) for r in bad)
    return {'openings': len(rows), 'buildings': len({r['ref'] for r in rows}), 'verdicts': dict(c),
            'bad_by_building': kinds.most_common()}


if __name__ == '__main__':
    import json
    import os
    import sys
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    args = sys.argv[1:]
    home = args[args.index('--home') + 1] if '--home' in args else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'packaging', 'out', 'FOLab')
    os.environ['FOLAB_HOME'] = home
    os.environ['FOLAB_NO_GAME_WRITES'] = '1'
    near = [float(v) for v in args[args.index('--near') + 1].split(',')] if '--near' in args else None
    import gamedata
    import project
    import server
    server.GD = gamedata.GameData()
    server.BR = None
    pr = project.Project.open('Waikiki')
    server.load_game(pr)
    gd = server.GD
    w = next(x for x in gd.worlds() if gd.edid(x) == 'FOLabWaikiki')
    rows = Audit(gd, pr, w).run(near)
    print(json.dumps(summary(rows), indent=1, default=str))
    out = args[args.index('--out') + 1] if '--out' in args else None
    if out:
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(rows, fh, indent=0, default=str)
    os._exit(0)
