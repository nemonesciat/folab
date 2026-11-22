"""Tree villages up the valley behind Kuliouou's camp (treevillage.py's pieces; the user, 21 Nov 2026: "that starting valley
with the quests is pretty boring. there could be bamboo tree villages with rope bridges and towers and shacks").

Kuliouou is poor and jumpy: catchers take whoever nobody will miss, so its families sleep up off the ground, the way up one
stair that can be watched. Up the valley road from the camp (`VILLAGES` of them, `APART` from each other, at least
`FROM_CAMP` from the camp's marker and every one of kuliouquest's spots):

- a treehouse, its stair down toward the road; its deck height is the village's;
- platforms joined to it and to each other by rope bridges (gap to gap, the bridge the length that brings a platform's
  middle nearest a tall tree, so the tree comes up through the deck), `PLATFORMS` in all, each where its legs reach the
  ground and there is headroom under it, nothing big under its deck or a bridge, the ground under a bridge well under its
  sag; plants that would come up through a deck, a bridge or a stair are taken out, low ones left;
- rails across every gap nothing joins, a ladder leant against some platforms (dressing: nobody climbs ladders in FNV);
- on the ground round the treehouse's foot, by bambooplace's rules (level, clear, pads where steep): small huts, a
  cookhouse, drying racks, a storehouse, the game's campfire, and a lookout at the village's edge;
- canoe racks on the shore below the camp, clear of the sale on the beach.

`ops(gd, pr, world, side)` -> (ops, report, cells): one Undo; the cells to navmesh again."""
import math

import bambooplace as BP
import modelsets
import ridgeplaces
import townbuild
import treevillage as TV

VILLAGES = 4
APART = 3200.0                  # (villages' middles at least this far apart)
FROM_CAMP = 1500.0              # (and this far from the camp's marker and the quest's spots)
UP_VALLEY = (1200.0, 14000.0)   # (how far up the valley road from the camp, along it)
OFF_ROAD = (650.0, 2400.0)      # (a treehouse's middle this far from the road)
ROAD_CLEAR = 450.0              # (nothing of a village's this near a road's middle line: a road piece is ~512 wide)
ROAD_STEP = 128.0
CELL_INSET = 64.0              # (a village stays this far inside its treehouse's cell: _in_cell)
PLATFORMS = (2, 6)              # (platforms a village, fewest it counts with and most)
HEADROOM = 170.0                # (ground under a deck at least this far under it)
BRIDGE_CLEAR = 140.0            # (ground under a bridge at least this far under its planks)
TREE_ON = 160.0                 # (a tall tree this near a platform's middle comes up through its deck, and stays)
TALL = 600.0                    # (a tree this tall counts as one to build round)
LOW = 120.0                     # (things lower than this may stay under decks and bridges)
LADDERS = 0.5                   # (share of platforms with a ladder against them)
LADDER_TOP = 446.0              # (treevillage.ladder's top over its foot)
GROUND = [('bamboo_hut_small', 2, 500, 1600), ('bamboo_cookhouse', 1, 400, 1400), ('bamboo_drying_rack', 2, 300, 1500),
          ('bamboo_storehouse', 1, 500, 1600), ('bamboo_lookout', 1, 900, 2200)]
FIRE = 'CampfireCrafting03'
RACKS = 2
SHORE = (20.0, 220.0)            # (the ground a canoe rack stands on: just over the sea)
RACK_REACH = (900.0, 10000.0)    # (from the camp's marker)
CAMP = "Kuliouou Squatters' Camp"


def _yaw_out(ox, oy):
    """The turn that points a piece's +y along (ox, oy)."""
    return math.atan2(ox, oy) % math.tau


class Village:
    def __init__(self, P, name, x, y, yaw):
        self.P, self.name, self.x, self.y, self.yaw = P, name, x, y, yaw
        self.ops, self.platforms, self.bridges, self.kept, self.clear = [], [], [], set(), set()
        self.deck = None


class Placer(BP.Placer):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rep.update({'villages': [], 'racks': 0, 'ladders': 0, 'rails': 0, 'bridges': 0, 'platforms': 0, 'trees_kept': 0,
                         'why': {}})
        self.avoid = []             # ((x, y, r) no village may come near)
        self.lines = []             # (segments of every bridge stood: no other may cross)
        self.boxc = {}

    def _why(self, k):
        self.rep['why'][k] = self.rep['why'].get(k, 0) + 1

    # ----- what stands where -----

    def roads(self):
        """Points along every road piece (its middle line by its own bounds, every ROAD_STEP), not just its middle: a
        piece is long, and a village planned off its middles stood its bridges along a road's edge."""
        if not hasattr(self, '_roads'):
            self._roads = []
            for _c, _r, r in self.refs():
                if 'Road' not in self.edid(r.get('base')):
                    continue
                x, y, z, _a, _b, rz = r['p']
                if r['base'] not in self.boxc:
                    self.height_of(r['base'])
                b = self.boxc.get(r['base']) or (0, 0, 0, 0, 0, 0)
                s = r.get('s', 1.0)
                long_y = (b[4] - b[1]) >= (b[3] - b[0])
                lo, hi = ((b[1], b[4]) if long_y else (b[0], b[3]))
                n = max(1, int((hi - lo) * s // ROAD_STEP))
                for k in range(n + 1):
                    t = (lo + (hi - lo) * k / n) * s
                    u, v = townbuild.turn(0.0, t, rz) if long_y else townbuild.turn(t, 0.0, rz)
                    self._roads.append((x + u, y + v, z))
            self._road_cells = {}
            for p in self._roads:
                self._road_cells.setdefault((int(p[0] // 1024), int(p[1] // 1024)), []).append(p)
        return self._roads

    def near_road(self, x, y, d):
        self.roads()
        for i in range(int((x - d) // 1024), int((x + d) // 1024) + 1):
            for j in range(int((y - d) // 1024), int((y + d) // 1024) + 1):
                if any(math.hypot(p[0] - x, p[1] - y) < d for p in self._road_cells.get((i, j), ())):
                    return True
        return False


    def height_of(self, base):
        if base not in self.boxc:
            try:
                self.boxc[base] = townbuild.obnd(self.gd, base)
            except Exception:
                self.boxc[base] = None
        b = self.boxc[base]
        return (b[5] - b[2]) if b else 0.0

    def ref(self, ck, rk):
        return self.pr.cells.get(ck, {}).get('refs', {}).get(rk)

    def tall_trees(self, x, y, r):
        if not hasattr(self, '_tall'):
            self._tall = {}
            for ck, rk, q in self.refs():
                e = self.edid(q.get('base'))
                if any(w in e for w in ('Palm', 'Tree', 'Ficus', 'Banyan')) and 'Fern' not in e:
                    if self.height_of(q['base']) * q.get('s', 1.0) >= TALL:
                        p = q['p']
                        self._tall.setdefault((int(p[0] // 2048), int(p[1] // 2048)), []).append((p[0], p[1], ck, rk))
        out = []
        for i in range(int((x - r) // 2048), int((x + r) // 2048) + 1):
            for j in range(int((y - r) // 2048), int((y + r) // 2048) + 1):
                out += [t for t in self._tall.get((i, j), ()) if abs(t[0] - x) <= r and abs(t[1] - y) <= r and (t[2], t[3]) not in self.B.gone]
        return out

    def _under(self, fp, top, keep=()):
        """Over a footprint at height `top`: (blocked, what to take out). Big things block; clearable ones reaching over
        top - LOW are taken out (a deck or planks would cut them), except `keep`."""
        B = self.B
        clear = []
        for ck, rk, ofp, big, _o in B.w.near(fp):
            if (ck, rk) in B.gone or (ck, rk) in keep or not townbuild.overlap(fp, ofp):
                continue
            q = self.ref(ck, rk)
            if B.clearable(ck, rk):
                if q and q.get('p') and q['p'][2] + self.height_of(q['base']) * q.get('s', 1.0) > top - LOW:
                    clear.append((ck, rk))
            elif big:
                return True, []
        return False, clear

    def _solid_in(self, fp):
        """Anything in fp that isn't growing or lying about, however small (the stair's way must be clear)."""
        B = self.B
        return any(not B.clearable(ck, rk) and (ck, rk) not in B.gone and townbuild.overlap(fp, ofp) for ck, rk, ofp, _big, _o in B.w.near(fp))

    def _in_cell(self, V, pts):
        """Every point inside the treehouse's own cell, CELL_INSET from its edges. An outdoor navmesh is made a cell at a
        time, seeing only navgen.MARGIN past it, and keeps only what joins the ground there: a platform in the next cell,
        its bridge's other end out of sight, had no navmesh (the D: rehearsal, 22 Nov 2026)."""
        if getattr(self, 'span', False):
            return True                                     # (navmeshed with navbuild.generate_area(beyond=True))
        if not hasattr(V, 'cell'):
            V.cell = (int(V.x // 4096), int(V.y // 4096))
        x0, y0 = V.cell[0] * 4096 + CELL_INSET, V.cell[1] * 4096 + CELL_INSET
        return all(x0 <= x <= x0 + 4096 - 2 * CELL_INSET and y0 <= y <= y0 + 4096 - 2 * CELL_INSET for x, y in pts)

    def _rect(self, x, y, yaw, x0, y0, x1, y1):
        return [(x + u, y + v) for u, v in [townbuild.turn(lx, ly, yaw) for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]]

    def _add(self, V, name, x, y, z, yaw, s=1.0):
        key = self.piece(name)
        ck = self.B.w.cell_at(x, y)
        V.ops.append({'op': 'add', 'cell': ck, 'base': key, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(yaw % math.tau, 4)], 's': round(s, 3)})
        return ck

    # ----- a village -----

    def treehouse(self, V):
        """The treehouse at V's spot: its origin on the ground at the stair's foot, the deck's ground between its legs'
        reach and HEADROOM under it."""
        g = self.B.ground
        fx, fy = townbuild.turn(*TV.STAIR_FOOT, V.yaw)
        foot = g.at(V.x + fx, V.y + fy)
        if foot is None or foot < 4.0:
            return 'stair foot in water'
        z0 = foot
        D = z0 + TV.RISE
        hs = [g.at(V.x + u, V.y + v) for u, v in [townbuild.turn(lx, ly, V.yaw) for lx in (-TV.TH_X, 0, TV.TH_X) for ly in (-TV.TH_Y, 0, TV.TH_Y)]]
        if any(h is None or h < 4.0 for h in hs):
            return 'water under'
        if max(hs) > D - HEADROOM or min(hs) < z0 - TV.LEG_DEEP + 40:
            return 'ground under the deck too high or too low'
        # (the stair's own run: its ground must not rise into the flight)
        for t in (0.25, 0.5, 0.75):
            lx, ly = TV.STAIR_FOOT[0], TV.STAIR_FOOT[1] + (-TV.TH_Y - TV.STAIR_FOOT[1]) * t
            u, v = townbuild.turn(lx, ly, V.yaw)
            h = g.at(V.x + u, V.y + v)
            if h is None or h > z0 + TV.RISE * t - 10:
                return 'ground in the stair'
        deck = self._rect(V.x, V.y, V.yaw, -TV.TH_X - 30, -TV.TH_Y - 30, TV.TH_X + 30, TV.TH_Y + 30)
        stair = self._rect(V.x, V.y, V.yaw, -TV.GAP / 2 - 30, TV.STAIR_FOOT[1] - 60, TV.GAP / 2 + 30, -TV.TH_Y)
        b1, c1 = self._under(deck, D)
        b2, c2 = self._under(stair, z0 + 10000)           # (everything off the stair)
        if b1 or b2:
            return 'something big in the way'
        if self._solid_in(stair):
            return 'something on the stair'               # (a lamp post at a stair's foot kept a village off the navmesh)
        if not self._in_cell(V, deck + stair):
            return 'not inside one cell'
        inside = [(V.x + u, V.y + v) for u, v in [townbuild.turn(lx, ly, V.yaw) for lx in (-TV.TH_X, 0.0, TV.TH_X) for ly in (-TV.TH_Y, 0.0, TV.TH_Y)]]
        if any(self.near_road(*p, ROAD_CLEAR) for p in deck + stair + inside):
            return 'on a road'
        V.deck = D
        V.clear |= set(c1) | set(c2)
        self._add(V, 'bamboo_treehouse', V.x, V.y, z0, V.yaw)
        V.platforms.append((V.x, V.y, max(TV.TH_X, TV.TH_Y) + 40))
        for t in (0.25, 0.6, 1.0, 1.3):                     # (the stair's run and its foot kept clear: a hut stood there
            u, v = townbuild.turn(0.0, -TV.TH_Y + (TV.STAIR_FOOT[1] + TV.TH_Y) * t, V.yaw)   # kept a village off its navmesh)
            V.platforms.append((V.x + u, V.y + v, 170.0))
        V.gaps = [(V.x + townbuild.turn(gx, gy, V.yaw)[0], V.y + townbuild.turn(gx, gy, V.yaw)[1], townbuild.turn(ox, oy, V.yaw))
                  for (gx, gy), (ox, oy) in TV.GAPS['bamboo_treehouse']]
        V.foot = (V.x + fx, V.y + fy, z0)
        return None

    def platform_at(self, V, gx, gy, out):
        """A bridge from a gap at (gx, gy) going `out` and a platform at its far end: the length whose platform middle is
        nearest a tall tree, else the first that fits. Returns the platform's gaps (other than the one back) or None."""
        g, D = self.B.ground, V.deck
        best = None
        for L in TV.LENGTHS:
            cx, cy = gx + out[0] * (L + TV.HALF), gy + out[1] * (L + TV.HALF)
            if any(math.hypot(cx - a, cy - b) < r + TV.HALF + 200 for a, b, r in V.platforms + self.stood + self.avoid):
                self._why('platform crowded')
                continue
            if not self._in_cell(V, self._rect(cx, cy, V.yaw, -TV.HALF - 30, -TV.HALF - 30, TV.HALF + 30, TV.HALF + 30)):
                self._why('platform out of the cell')
                continue
            if self.near_road(cx, cy, TV.HALF + ROAD_CLEAR):
                self._why('platform on a road')
                continue
            hs = [g.at(cx + u, cy + v) for u in (-TV.HALF, 0, TV.HALF) for v in (-TV.HALF, 0, TV.HALF)]
            if any(h is None or h < 4.0 for h in hs):
                self._why('platform over water')
                continue
            if max(hs) > D - HEADROOM or min(hs) < D - TV.RISE - TV.LEG_DEEP + 40:
                self._why('platform: ground too high or too low')
                continue
            sag = L / TV.SAG
            ok = True
            for k in range(1, 12):
                t = k / 12.0
                bx, by = gx + out[0] * L * t, gy + out[1] * L * t
                h = g.at(bx, by)
                u = 2 * t - 1
                if h is None or h > D - sag * (1 - u * u) - BRIDGE_CLEAR:
                    ok = False
                    break
            if not ok:
                self._why('bridge: ground too near its planks')
                continue
            a, b = (gx, gy), (gx + out[0] * L, gy + out[1] * L)
            if any(_cross(a, b, c, d) for c, d in self.lines + V.bridges):
                self._why('bridge crosses another')
                continue
            if any(self.near_road(gx + out[0] * L * t, gy + out[1] * L * t, ROAD_CLEAR) for t in (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)):
                self._why('bridge over a road')
                continue
            yaw = _yaw_out(*out)
            bfp = self._rect(gx + out[0] * L / 2, gy + out[1] * L / 2, yaw, -TV.GAP / 2 - 30, -L / 2, TV.GAP / 2 + 30, L / 2)
            trees = [t for t in self.tall_trees(cx, cy, TREE_ON) if math.hypot(t[0] - cx, t[1] - cy) < TREE_ON]
            keep = {(t[2], t[3]) for t in trees[:1]}
            pfp = self._rect(cx, cy, V.yaw, -TV.HALF - 30, -TV.HALF - 30, TV.HALF + 30, TV.HALF + 30)
            b1, c1 = self._under(bfp, D - sag)
            b2, c2 = self._under(pfp, D, keep)
            if b1 or b2:
                self._why('something big under it')
                continue
            score = (0 if keep else 1, L)                  # (short bridges: more platforms fit in the cell)
            if best is None or score < best[0]:
                best = (score, L, cx, cy, yaw, set(c1) | set(c2), keep)
        if best is None:
            return None
        _s, L, cx, cy, yaw, clear, keep = best
        self._add(V, 'bamboo_rope_bridge_%d' % L, gx + out[0] * L / 2, gy + out[1] * L / 2, D, yaw)
        self._add(V, 'bamboo_tree_platform', cx, cy, D - TV.RISE, V.yaw)
        V.clear |= clear
        V.kept |= keep
        V.bridges.append(((gx, gy), (gx + out[0] * L, gy + out[1] * L)))
        V.platforms.append((cx, cy, TV.HALF + 40))
        gaps = []
        for (lx, ly), (ox, oy) in TV.GAPS['bamboo_tree_platform']:
            o = townbuild.turn(ox, oy, V.yaw)
            if o[0] * out[0] + o[1] * out[1] < -0.9:
                continue                                    # (the gap the bridge came in by)
            p = townbuild.turn(lx, ly, V.yaw)
            gaps.append((cx + p[0], cy + p[1], o))
        V.pl_info = getattr(V, 'pl_info', []) + [(cx, cy)]
        return gaps

    def village(self, name, x, y, yaw):
        V = Village(self, name, x, y, yaw)
        why = self.treehouse(V)
        if why:
            self._why('treehouse: ' + why)
            return None
        open_gaps = list(V.gaps)
        closed = []
        n = 0
        rnd = self.B.rnd
        while open_gaps and n < PLATFORMS[1]:
            k = rnd.randrange(len(open_gaps)) if n else 0
            gx, gy, out = open_gaps.pop(k)
            got = self.platform_at(V, gx, gy, out)
            if got is None:
                closed.append((gx, gy, out))
                continue
            n += 1
            rnd.shuffle(got)
            open_gaps += got
        if n < PLATFORMS[0]:
            self._why('village: too few platforms (%d)' % n)
            return None
        for gx, gy, out in closed + open_gaps:
            self._add(V, 'bamboo_rail_gap', gx, gy, V.deck, _yaw_out(*out))
            self.rep['rails'] += 1
        # ladders against some platforms (not the treehouse), down a side with a rail, foot on the ground
        g = self.B.ground
        for cx, cy in V.pl_info:
            if rnd.random() > LADDERS:
                continue
            for side in rnd.sample(range(4), 4):
                (lx, ly), (ox, oy) = TV.GAPS['bamboo_tree_platform'][side]
                o = townbuild.turn(ox, oy, V.yaw)
                along = (-o[1], o[0])
                ex, ey = cx + o[0] * (TV.HALF + 120) + along[0] * 150, cy + o[1] * (TV.HALF + 120) + along[1] * 150
                h = g.at(ex, ey)
                if h is None or h < 4.0:
                    continue
                s = (V.deck + 40 - h) / LADDER_TOP
                if not 0.6 < s < 1.5 or any(_seg_near((ex, ey), a, b, 200) for a, b in V.bridges):
                    continue
                self._add(V, 'bamboo_ladder', ex, ey, h, _yaw_out(-o[0], -o[1]), s)
                self.rep['ladders'] += 1
                break
        # take out what the decks, bridges and stair would cut; the trees the platforms are round stay
        clear = sorted(V.clear - V.kept)
        self.B.take_out(clear)
        self.B.ops += V.ops
        for op in V.ops:
            self.B.cells.add(op['cell'])
        self.stood += V.platforms
        self.lines += V.bridges
        for a, b in V.bridges:
            for t in (0.25, 0.5, 0.75):
                self.stood.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, TV.GAP))
        # on the ground round the stair's foot
        fx, fy, _z = V.foot
        self.add_round(name, fx, fy, GROUND)
        self._fire(name, fx, fy, V)
        self.rep['bridges'] += len(V.bridges)
        self.rep['platforms'] += len(V.pl_info)
        self.rep['trees_kept'] += len(V.kept)
        self.rep['villages'].append({'name': name, 'at': [round(x), round(y), round(V.deck)], 'platforms': len(V.pl_info),
                                     'bridges': len(V.bridges), 'cleared': len(clear)})
        return V

    def _fire(self, name, fx, fy, V):
        """The game's campfire a little out from the stair's foot, on ground clear of everything."""
        B = self.B
        if FIRE not in B.key_of:
            import shipinside
            f = shipinside._forms(self.gd, {FIRE}).get(FIRE)
            if f is None:
                return
            B.key_of[FIRE] = self.gd.key(f)
        pl = ridgeplaces.Place(B, name + ' fire', fx, fy, 0.0)
        pl.taken += self.stood
        for k in range(60):
            a = B.rnd.uniform(0, math.tau)
            d = B.rnd.uniform(250, 700)
            x, y = fx + d * math.cos(a), fy + d * math.sin(a)
            if any(math.hypot(x - p, y - q) < r + 150 for p, q, r in self.stood):
                continue
            box = B.box(FIRE)
            if box is None:
                return
            fp = [(x - 80, y - 80), (x + 80, y - 80), (x + 80, y + 80), (x - 80, y + 80)]
            blocked, clear = B.blocking(fp)
            if blocked:
                continue
            B.take_out(clear)
            if pl.put(FIRE, x, y, 0.0, check=False):
                self.stood.append((x, y, 90.0))
                self.rep['fires'] = self.rep.get('fires', 0) + 1
                return

    # ----- where the villages go -----

    def spots_to_avoid(self, marks):
        import kuliouquest
        try:
            sp = kuliouquest.spots(self.gd, self.pr)
        except Exception:
            sp = {}
        out = [(p[1][0], p[1][1], FROM_CAMP) for k, p in sp.items() if k != 'world']
        if CAMP in marks:
            out.append((marks[CAMP][0], marks[CAMP][1], FROM_CAMP))
        return out

    def valley(self, marks):
        if CAMP not in marks:
            self.rep['why']['no camp marker'] = 1
            return
        kx, ky, _kz = marks[CAMP]
        self.avoid = self.spots_to_avoid(marks) + list(getattr(self, 'skip', ()))
        # the valley road: road pieces up from the camp (the valley runs away from the sea: the side with the higher ground)
        def along(k):
            ux, uy = math.sin(k * math.pi / 16), math.cos(k * math.pi / 16)
            return sum(1 for p in self.roads() if UP_VALLEY[0] < (p[0] - kx) * ux + (p[1] - ky) * uy < UP_VALLEY[1]
                       and abs((p[0] - kx) * uy - (p[1] - ky) * ux) < 1500)
        g = self.B.ground
        low = min(range(16), key=lambda k: g.at(kx + 2500 * math.sin(k * math.pi / 8), ky + 2500 * math.cos(k * math.pi / 8)) or 1e9)
        lx, ly = math.sin(low * math.pi / 8), math.cos(low * math.pi / 8)     # (toward the sea: kuliouquest's way in)
        inland = [k for k in range(32) if math.sin(k * math.pi / 16) * lx + math.cos(k * math.pi / 16) * ly < -0.3]
        up = max(inland, key=along)                         # (the way most of the camp's road pieces run inland)
        ux, uy = math.sin(up * math.pi / 16), math.cos(up * math.pi / 16)
        self.rep['valley_way'] = [round(ux, 2), round(uy, 2)]
        road = [p for p in self.roads() if UP_VALLEY[0] < (p[0] - kx) * ux + (p[1] - ky) * uy < UP_VALLEY[1]
                and abs((p[0] - kx) * uy - (p[1] - ky) * ux) < 2500]
        self.rep['valley_road'] = len(road)
        rnd = self.B.rnd
        tries = []
        for p in road[::4]:
            for side in (-1, 1):
                for k in range(14):
                    d = rnd.uniform(*OFF_ROAD)
                    a = math.atan2(uy, ux) + side * math.pi / 2 + rnd.uniform(-0.6, 0.6)
                    tries.append((p[0] + d * math.cos(a), p[1] + d * math.sin(a), p))
        for a in range(int(UP_VALLEY[0]), int(UP_VALLEY[1]), 700):          # (and over the valley floor and its slopes)
            for b in range(-3500, 3501, 700):
                x, y = kx + ux * a + uy * b + rnd.uniform(-200, 200), ky + uy * a - ux * b + rnd.uniform(-200, 200)
                near = min(road, key=lambda p: math.hypot(p[0] - x, p[1] - y), default=None)
                if near is not None and math.hypot(near[0] - x, near[1] - y) > OFF_ROAD[0]:
                    tries.append((x, y, near))
        rnd.shuffle(tries)
        # most trees round it first: a village in the jungle
        tries.sort(key=lambda t: -len(self.tall_trees(t[0], t[1], 1200)) + rnd.random() * 3)
        made = []
        for x, y, p in tries:
            if len(made) >= VILLAGES:
                break
            if any(math.hypot(x - a, y - b) < APART for a, b in made):
                continue
            if any(math.hypot(x - a, y - b) < r for a, b, r in self.avoid):
                continue
            g = self.B.ground
            up = max(range(8), key=lambda k: g.at(x + 600 * math.cos(k * math.pi / 4), y + 600 * math.sin(k * math.pi / 4)) or -1e9)
            yaws = [BP._face(p[0] - x, p[1] - y) + t for t in (0.0, 0.5, -0.5)]     # (the stair toward the road...)
            yaws += [BP._face(math.cos(up * math.pi / 4), math.sin(up * math.pi / 4))]  # (...or up the slope: the deck out over it)
            yaws += [BP._face(math.cos(k * math.pi / 4), math.sin(k * math.pi / 4)) for k in range(8) if k != up]   # (...or any way)
            for yaw in yaws:
                if self.village('village %d' % (len(made) + 1), x, y, yaw):
                    made.append((x, y))
                    break

    def racks(self, marks):
        if CAMP not in marks:
            return
        kx, ky, _kz = marks[CAMP]
        B, g = self.B, self.B.ground
        name = 'bamboo_canoe_rack'
        self.piece(name)
        pl = ridgeplaces.Place(B, 'shore', kx, ky, 0.0)
        pl.taken += [a for a in self.avoid]
        made, why = 0, {}
        for k in range(4000):
            if made >= RACKS:
                break
            a = B.rnd.uniform(0, math.tau)
            d = B.rnd.uniform(*RACK_REACH)
            x, y = kx + d * math.cos(a), ky + d * math.sin(a)
            h = g.at(x, y)
            if h is None or not SHORE[0] < h < SHORE[1]:
                continue
            if any(math.hypot(x - p, y - q) < r for p, q, r in self.avoid):
                continue
            low = min(((g.at(x + 800 * math.cos(b), y + 800 * math.sin(b)) or 1e9), b) for b in [j * math.pi / 8 for j in range(16)])
            if low[0] > 4.0:
                continue                                    # (the water's within reach)
            yaw = BP._face(math.cos(low[1]), math.sin(low[1]))
            if self._try(pl, name, x, y, yaw, why):
                made += 1
        self.rep['racks'] = made
        if made < RACKS:
            self.rep['not_placed'][('shore', name)] = [RACKS - made, why]


def _cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def _seg_near(p, a, b, d):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay or 1.0
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return math.hypot(p[0] - a[0] - ax * t, p[1] - a[1] - ay * t) < d


BP.LEVEL.update({'bamboo_canoe_rack': 50.0})


def ops(gd, pr, world, side, cat=None, seed=21, skip=(), span=False):
    """skip: (x, y, r) where no village may go (one whose decks the navmesh didn't reach, on a run before). span: a
    village may reach into the next cells; its cells must then be navmeshed with generate_area(..., beyond=True)."""
    P = Placer(gd, pr, world, side, cat, seed)
    marks = P.markers()
    P.skip = list(skip)
    P.span = span
    P.valley(marks)
    P.racks(marks)
    B = P.B
    lands = []
    for k, f in sorted(B.forms.items()):
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': f})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    P.rep['land_cells'], P.rep['moved'] = len(lands), len(moves)
    rep = dict(P.rep, added={'%s: %s' % k: v for k, v in P.rep['added'].items()},
               not_placed={'%s: %s' % k: v for k, v in P.rep['not_placed'].items()}, missing=sorted(B.rep['missing']))
    return P.put_ops + lands + moves + B.ops, rep, sorted(B.cells)
