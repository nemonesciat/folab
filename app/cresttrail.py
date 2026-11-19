"""The Crest Trail (docs/waikiki-story-plan.md, build list 3): one long wild path along the top of the Ko'olau and a
climb up each ridge place's own finger to it, worked out from the ground itself.

- **The line.** `route` is a cheapest-way search over the land at `ST` steps whose cost keeps to high ground
  (`HIGH`: e to the power of how far under the highest land a step is), to ridges (a step into a hollow costs more,
  `HOLLOW`) and off steep steps (`GRADE`). First the crest: from where the divide leaves the map's top edge to the last
  place (the Settlers' Watchtower); then each other place's climb, to the nearest point of the crest. On Waikiki the
  divide leaves the map north of Ka'au, so the three western places (Alewa, Pacific Heights, the Heights) join it
  along the high ground under the map's top edge.
- **A tread.** Along every leg the path's height is eased so no step is steeper than `MAX_GRADE` (cut where it rises
  too fast, as a path is), and the land points within `TREAD` of the line are brought to it, eased back over `EASE`:
  a narrow walkable top on a knife edge. Ground under roads and big things is left; the sea stays. Things standing on
  changed ground move with it. Each climb leaves its place's yard alone (`START`).
- **Mud.** The path is painted with Zion's muddy ground (`MUD`), strongest on the line.
- **Cleared.** What grows or lies (ridgeplaces.Builder.clearable) on the tread is taken out.
- **Marked.** A signpost with a hiking sign where each climb starts and where it meets the crest; a stack of rocks
  every `CAIRN_EVERY` along the crest.

The game has no handrope; rope lines wait for a piece of FOLab's own. `ops` returns (ops, report); nothing is applied."""
import heapq
import math

import ridgeplaces
import shipinside
import townbuild

ST = 256.0
HIGH, HOLLOW, GRADE = 7.0, 120.0, 8.0
MAX_GRADE = math.tan(math.radians(36.0))
TREAD, EASE = 150.0, 260.0
FILL = 40.0                  # (the most a path stands over the ground it crosses)
SIDE_FILL = 120.0            # (beside the line, the most the ground is raised to widen a knife edge)
START = 900.0
STEP = 8.0
MUD = 'LGroundMuddyNVDLC02'
CAIRN_EVERY = 3500.0
CAIRN = [('NVDLC02RockCanyon13', 0.0, 1.0), ('NVDLC02RockCanyon12', 50.0, 0.9), ('NVDLC02RockCanyon06', 95.0, 0.5)]
SIGNPOST, SIGN = 'NVDLC02signPostTall', 'NVDLC02trailSnHike'
NAMES = {SIGNPOST, SIGN} | {c[0] for c in CAIRN}
WEST_EDGE = (-70000.0, -10000.0)          # (where on the map's top edge to look for the divide)


class Grid:
    def __init__(self, ground, box):
        self.x0, self.x1, self.y0, self.y1 = box
        self.nx, self.ny = int((self.x1 - self.x0) / ST) + 1, int((self.y1 - self.y0) / ST) + 1
        self.H = [[ground.at(self.x0 + i * ST, self.y0 + j * ST) for i in range(self.nx)] for j in range(self.ny)]
        self.top = max(v for r in self.H for v in r if v is not None)
        self.hollow = [[0.0] * self.nx for _ in range(self.ny)]
        for j in range(self.ny):
            for i in range(self.nx):
                h = self.H[j][i]
                if h is None:
                    continue
                s = k = 0
                for dj, di in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, -2), (2, -2), (-2, 2)):
                    jj, ii = j + dj, i + di
                    if 0 <= jj < self.ny and 0 <= ii < self.nx and self.H[jj][ii] is not None:
                        s += self.H[jj][ii]
                        k += 1
                self.hollow[j][i] = max(0.0, s / k - h) if k else 0.0

    def node(self, x, y):
        return int(round((y - self.y0) / ST)), int(round((x - self.x0) / ST))

    def xy(self, n):
        return self.x0 + n[1] * ST, self.y0 + n[0] * ST

    def cost(self, a, b):
        ha, hb = self.H[a[0]][a[1]], self.H[b[0]][b[1]]
        if hb is None or hb < 40.0 or ha is None:
            return None
        L = ST * math.hypot(a[0] - b[0], a[1] - b[1])
        gr = abs(hb - ha) / L
        return L * (1 + GRADE * gr * gr) * math.exp(HIGH * (self.top - hb) / self.top) * (1 + self.hollow[b[0]][b[1]] / HOLLOW)

    def route(self, a, goal):
        goal = goal if isinstance(goal, set) else {goal}
        dist, prev, q = {a: 0.0}, {}, [(0.0, a)]
        end = None
        while q:
            d, u = heapq.heappop(q)
            if u in goal:
                end = u
                break
            if d > dist.get(u, 1e18):
                continue
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                v = (u[0] + dj, u[1] + di)
                if not (0 <= v[0] < self.ny and 0 <= v[1] < self.nx):
                    continue
                c = self.cost(u, v)
                if c is None:
                    continue
                if d + c < dist.get(v, 1e18):
                    dist[v] = d + c
                    prev[v] = u
                    heapq.heappush(q, (d + c, v))
        if end is None:
            return None
        path = [end]
        while path[-1] != a:
            path.append(prev[path[-1]])
        return path[::-1]

    def edge_top(self):
        """The highest point under the map's top edge in WEST_EDGE: where the divide leaves the map."""
        best = max((self.H[j][i], j, i) for j in range(self.ny - 12, self.ny) for i in range(self.nx)
                   if self.H[j][i] is not None and WEST_EDGE[0] < self.x0 + i * ST < WEST_EDGE[1])
        return best[1], best[2]


def line(ground, places, last, box):
    """{'crest': [(x, y)], name: [(x, y)] for each place's climb, from the place to the crest}."""
    G = Grid(ground, box)
    crest = G.route(G.edge_top(), G.node(*places[last]))
    out = {'crest': [G.xy(n) for n in crest]}
    on = set(crest)
    for name, at in places.items():
        if name == last:
            continue
        p = G.route(G.node(*at), on)
        if p:
            out[name] = [G.xy(n) for n in p]
    return out


def smooth_line(pts, step=64.0):
    """The line again every `step`, its corners cut (a running mean over 5 grid steps)."""
    if len(pts) < 3:
        return list(pts)
    k = 2
    sm = [pts[0]] + [(sum(p[0] for p in pts[max(0, i - k):i + k + 1]) / len(pts[max(0, i - k):i + k + 1]),
                      sum(p[1] for p in pts[max(0, i - k):i + k + 1]) / len(pts[max(0, i - k):i + k + 1]))
                     for i in range(1, len(pts) - 1)] + [pts[-1]]
    out = [sm[0]]
    for a, b in zip(sm, sm[1:]):
        L = math.dist(a, b)
        n = max(1, int(L / step))
        for t in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n))
    return out


def walk_check(ground, legs, limit=45.0, where=None, zs=None):
    """{leg: [points measured, steps along steeper than limit, points whose ground across is steeper than limit]}
    on the ground as it now is (a step 64 along; across, 128 either side)."""
    out = {}
    t = math.tan(math.radians(limit))
    for li, (name, pts) in enumerate(legs.items()):
        zz = zs[li] if zs else None
        n = along = across = 0
        for a, b in zip(pts, pts[1:]):
            ga, gb = ground.at(*a), ground.at(*b)
            if ga is None or gb is None:
                continue
            L = math.dist(a, b) or 1.0
            n += 1
            if abs(gb - ga) / L > t:
                along += 1
                if where is not None and len(where.setdefault(name, [])) < 12:
                    where[name].append([round(a[0]), round(a[1]), round(ga), round(gb)] + ([round(min(zz, key=lambda q: math.dist(q[0], a))[1])] if zz else []))
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            l_, r_ = ground.at(a[0] - uy * 128, a[1] + ux * 128), ground.at(a[0] + uy * 128, a[1] - ux * 128)
            if l_ is not None and r_ is not None and min(abs(l_ - ga), abs(r_ - ga)) / 128.0 > t:
                across += 1
        out[name] = [n, along, across]
    return out


class Trail:
    def __init__(self, gd, pr, world, side, cat):
        self.B = B = ridgeplaces.Builder(gd, pr, world, side, cat)
        found = shipinside._forms(gd, NAMES)
        B.key_of.update({e: gd.key(f) for e, f in found.items()})
        B.rep['missing'] |= NAMES - set(found)
        self.gd, self.pr, self.world = gd, pr, world
        clear = B.clearable
        self._vine = {}

        def clearable(ck, rk):
            if clear(ck, rk):
                return True
            r = pr.cells.get(ck, {}).get('refs', {}).get(rk)
            b_ = r.get('base') if r else None
            if b_ not in self._vine:
                import natcompound
                self._vine[b_] = bool(b_) and 'Vines' in natcompound._named(gd, pr, b_)
            return self._vine[b_]
        B.clearable = clearable
        self.mud = None
        for f, (_i, r) in gd.forms.items():
            if r.tag == 'LTEX' and gd.edid(f) == MUD:
                self.mud = f
                break
        import land
        self.mud_tex = land.texture_of_fid(gd, self.mud, {}) if self.mud is not None else None
        self.changed = {}                          # ((gx, gy) land point -> height before)
        self.painted = set()
        self.rep = {'legs': {}, 'held_by': {}}

    # ----- the ground -----

    def _points(self, gx, gy):
        """[(form, index)] for land point (gx, gy) in every cell that has it."""
        out = []
        for cx in ({gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}):
            for cy in ({gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}):
                f = self.B._form((cx, cy))
                if f:
                    out.append((f, (cx, cy), (gy - cy * 32) * 33 + (gx - cx * 32)))
        return out

    def tread(self, pts, skip=0.0):
        """Bring the land along pts (a smoothed line) to an eased height with no step over MAX_GRADE."""
        B = self.B
        g = [B.ground.at(x, y) for x, y in pts]
        s = [0.0]
        for a, b in zip(pts, pts[1:]):
            s.append(s[-1] + math.dist(a, b))
        z = [v if v is not None else 0.0 for v in g]
        # (a path is cut into the hill, hardly ever built up: the highest profile with no step over MAX_GRADE that
        # stands at most FILL over the ground anywhere, worked out forwards and back)
        z = [sum(z[max(0, i - 1):i + 2]) / len(z[max(0, i - 1):i + 2]) + FILL for i in range(len(z))]
        for i in range(1, len(z)):
            z[i] = min(z[i], z[i - 1] + MAX_GRADE * (s[i] - s[i - 1]))
        for i in range(len(z) - 2, -1, -1):
            z[i] = min(z[i], z[i + 1] + MAX_GRADE * (s[i + 1] - s[i]))
        # (each land point near the line takes the nearest line point's height)
        near = {}
        reach = TREAD + EASE
        for k, (x, y) in enumerate(pts):
            if s[k] < skip:
                continue
            for gy in range(int((y - reach) // 128), int((y + reach) // 128) + 2):
                for gx in range(int((x - reach) // 128), int((x + reach) // 128) + 2):
                    d = math.hypot(gx * 128.0 - x, gy * 128.0 - y)
                    if d < reach and d < near.get((gx, gy), (1e9,))[0]:
                        near[(gx, gy)] = (d, z[k])
        self.zs = getattr(self, 'zs', []) + [list(zip(pts, z))]
        held = 0
        for (gx, gy), (d, zt) in near.items():
            if B._held(gx * 128.0, gy * 128.0):
                held += 1
                if self.rep.get('held_by') is not None:
                    fp = [(gx * 128.0 - 40, gy * 128.0 - 40), (gx * 128.0 + 40, gy * 128.0 - 40), (gx * 128.0 + 40, gy * 128.0 + 40), (gx * 128.0 - 40, gy * 128.0 + 40)]
                    for ck, rk, ofp, big, _o in B.w.near(fp):
                        if big and townbuild.overlap(fp, ofp) and not B.clearable(ck, rk):
                            import natcompound
                            r = self.pr.cells[ck]['refs'][rk]
                            nm = natcompound._named(self.gd, self.pr, r['base'])
                            self.rep['held_by'][nm] = self.rep['held_by'].get(nm, 0) + 1
                continue
            u = 0.0 if d <= TREAD else (d - TREAD) / EASE
            u = u * u * (3 - 2 * u)
            for f, ck, k in self._points(gx, gy):
                old = f['h'][k]
                if old < 4.0:
                    continue
                if (gx, gy) not in self.changed:
                    self.changed[(gx, gy)] = old
                new = zt + (old - zt) * u
                if d > 64.0 and new > old + SIDE_FILL:
                    new = old + SIDE_FILL
                f['h'][k] = round(new / STEP) * STEP
        return held

    def paint(self, pts):
        """Mud on the land points within reach of the line: full on it, fading out by 200."""
        if self.mud is None:
            return 0
        key = self.gd.key(self.mud)
        best = {}
        for x, y in pts:
            for gy in range(int((y - 200) // 128), int((y + 200) // 128) + 2):
                for gx in range(int((x - 200) // 128), int((x + 200) // 128) + 2):
                    d = math.hypot(gx * 128.0 - x, gy * 128.0 - y)
                    a = 1.0 if d < 70 else max(0.0, 1.0 - (d - 70) / 130.0)
                    if a > best.get((gx, gy), 0.0):
                        best[(gx, gy)] = a
        full = 0
        for (gx, gy), a in best.items():
            for f, (cx, cy), _k in self._points(gx, gy):
                r, c = gy - cy * 32, gx - cx * 32
                for q in range(4):
                    qx, qy = q & 1, q >> 1
                    rr, cc = r - qy * 16, c - qx * 16
                    if not (0 <= rr <= 16 and 0 <= cc <= 16):
                        continue
                    quarter = f['q'][q]
                    lay = next((l for l in quarter['layers'] if l.get('key') == key), None)
                    if lay is None:
                        lay = {'tex': self.mud_tex, 'key': key, 'a': [0.0] * 289}
                        if len(quarter['layers']) >= 6:
                            # (six already, the most a quarter can have: the faintest gives way to the mud)
                            weak = min(range(len(quarter['layers'])), key=lambda n: sum(quarter['layers'][n]['a']))
                            quarter['layers'][weak] = lay
                            full += 1
                        else:
                            quarter['layers'].append(lay)
                    i = rr * 17 + cc
                    lay['a'][i] = round(max(lay['a'][i], a), 3)
                    self.painted.add((cx, cy))
        return full

    def reseat(self):
        """Things standing on changed ground move with it; what grows or lies on the tread goes."""
        B = self.B
        moved = gone = 0
        cells = {(gx // 32, gy // 32) for gx, gy in self.changed}
        for (cx, cy) in cells:
            cell = B.w.grid.get((cx, cy))
            ck = self.gd.key(cell) if cell is not None else None
            c = self.pr.cells.get(ck) if ck else None
            for rk, r in (c['refs'].items() if c else ()):
                p = r.get('p')
                if not p or r.get('removed') or (ck, rk) in B.gone:
                    continue
                gx, gy = int(round(p[0] / 128.0)), int(round(p[1] / 128.0))
                if not any((gx + a, gy + b) in self.changed for a in (-1, 0, 1) for b in (-1, 0, 1)):
                    continue
                g0, g1 = B.orig.at(p[0], p[1]), B.ground.at(p[0], p[1])
                if g0 is None or g1 is None:
                    continue
                on_tread = self._on_line(p[0], p[1])
                if on_tread and B.clearable(ck, rk):
                    B.take_out([(ck, rk)])
                    gone += 1
                    continue
                if abs(g1 - g0) >= 2.0:
                    np_ = list(p)
                    np_[2] = round(p[2] + (g1 - g0), 1)
                    B.moved[(ck, rk)] = np_
                    moved += 1
        return moved, gone

    def _on_line(self, x, y):
        b = self.line_buckets.get((int(x // 512), int(y // 512)), ())
        return any(math.hypot(x - a, y - c) < TREAD for a, c in b)

    # ----- marks -----

    def sign(self, pl, x, y, ux, uy):
        """A signpost with a hiking sign, a step to the side of the path, the sign facing along it."""
        sx, sy = x - uy * 230.0, y + ux * 230.0
        if pl.put(SIGNPOST, sx, sy, 0.0, r=30.0):
            o = self.B.ops[-1]
            yaw = math.atan2(ux, uy)
            self.B.ops.append(dict(o, base=self.B.key_of[SIGN], p=[o['p'][0], o['p'][1], round(o['p'][2] + 170.0, 1), 0.0, 0.0, round(yaw % math.tau, 4)]))
            return 1
        return 0

    def cairn(self, pl, x, y):
        sx, sy = x + 200.0, y - 120.0
        if not pl.put(CAIRN[0][0], sx, sy, (x * 0.013) % math.tau, r=90.0):
            return 0
        o = self.B.ops[-1]
        for e, dz, sc in CAIRN[1:]:
            self.B.ops.append({'op': 'add', 'cell': o['cell'], 'base': self.B.key_of[e], 'p': [o['p'][0], o['p'][1], round(o['p'][2] + dz, 1), 0.0, 0.0,
                               round((o['p'][5] + 1.1 * dz) % math.tau, 4)], 's': sc})
        return 1


def ops(gd, pr, world, side, places, last, cat=None, box=(-126000.0, 132000.0, -6000.0, 98000.0)):
    """(ops, report, cells). places: {name: (x, y)} (the ridge places' middles and Ka'au's floor), `last` the one the
    crest ends at."""
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    T = Trail(gd, pr, world, side, cat)
    B = T.B
    lines = line(B.ground, places, last, box)
    legs = {k: smooth_line(v) for k, v in lines.items()}
    T.line_buckets = {}
    for pts in legs.values():
        for x, y in pts:
            T.line_buckets.setdefault((int(x // 512), int(y // 512)), []).append((x, y))
    for name, pts in legs.items():
        held = T.tread(pts, skip=0.0 if name == 'crest' else START)
        full = T.paint(pts if name == 'crest' else [p for k, p in enumerate(pts) if k * 64.0 >= START * 0.6])
        L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        T.rep['legs'][name] = {'length': round(L), 'held': held, 'gave_way': full}
    T.rep['steep_at'] = {}
    T.rep['walk'] = walk_check(B.ground, legs, where=T.rep['steep_at'], zs=T.zs)
    dz = sorted(B.ground.at(gx * 128.0, gy * 128.0) - old for (gx, gy), old in T.changed.items() if B.ground.at(gx * 128.0, gy * 128.0) is not None)
    if dz:
        T.rep['ground'] = {'points': len(dz), 'deepest_cut': round(dz[0]), 'highest_fill': round(dz[-1]),
                           'cut_over_200': sum(1 for v in dz if v < -200), 'fill_over_200': sum(1 for v in dz if v > 200),
                           'middle_change': round(dz[len(dz) // 2])}
    moved, gone = T.reseat()
    T.rep.update(moved=moved, cleared=gone)
    # marks
    pl = ridgeplaces.Place(B, 'trail', 0.0, 0.0, 0.0)
    signs = cairns = 0
    for name, pts in legs.items():
        if name == 'crest':
            run = 0.0
            for a, b in zip(pts, pts[1:]):
                run += math.dist(a, b)
                if run >= CAIRN_EVERY:
                    cairns += T.cairn(pl, *b)
                    run = 0.0
            continue
        for k in (min(len(pts) - 2, int(START / 64.0) + 2), len(pts) - 6):
            if 0 <= k < len(pts) - 1:
                a, b = pts[k], pts[k + 1]
                L = math.dist(a, b) or 1.0
                signs += T.sign(pl, a[0], a[1], (b[0] - a[0]) / L, (b[1] - a[1]) / L)
    T.rep.update(signs=signs, cairns=cairns)
    # land, then moves, then what's added
    lands = []
    for k in sorted(B.forms):
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': B.forms[k]})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    rep = dict(T.rep, land_cells=len(lands), missing=sorted(B.rep['missing']), added=sum(1 for o in B.ops if o['op'] == 'add'),
               removed=sum(1 for o in B.ops if o['op'] == 'remove'), lines={k: [[round(x), round(y)] for x, y in v] for k, v in lines.items()})
    return lands + moves + B.ops, rep, sorted(B.cells)
