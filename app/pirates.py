"""The pirates (docs/waikiki-story-plan.md, build list 5), in the game's own pieces:

- **The Kahala stronghold.** The Kahala Reef hotel (FOLab's own, `HOTEL`) walled round with junk walls a step out from
  its bounds, in its own frame (sea +y): a land gate on its town side, a sea gate to the beach, a guard tower at each
  landward corner, sandbag posts at the gates. Outside the land gate the trade ground, where the two sides meet: tables,
  chairs, crates, barrels, a fire, a lantern. From the sea gate a jetty (landmarks.Batch.harbour) with boats moored.
- **Koko Marina.** Piers out from the marina's shore where there are none yet (`marina_piers`), with the pirates' small
  boats moored, laid by Batch.harbour as the Ala Wai's were; and the boatyard on the shore: boats up on the ground, a
  shack, crates, a sandbag post inside a junk wall open to the water; a map marker.
- **The Flotilla.** On the shallow shelf off Koko Head (`FLOTILLA`, 6 m; the plan's spot in the middle of Maunalua
  Bay is 22 m deep), a wreck (`WRECK`) aground on a sandbar raised under it, a ring of dock planking round it at the
  water, rope-bridge gangplanks up to its deck, barges lashed to the ring's ends, boats moored outside, lanterns.
  `flotilla_items` gives the walkable parts in its own frame for walkcheck.

Nobody aboard or ashore yet (after the navmesh run). `ops` returns (ops, report, cells); nothing is applied."""
import math

import landmarks
import ridgeplaces
import shipinside
import townbuild
import worldrec

HOTEL = 'FOLabHotelKahalaReef'
RING_OUT = 420.0                       # (the wall this far out from the hotel's bounds)
GATE = 1000.0                          # (a gate's width)
BEACH = 600.0                         # (the wall's sea side this far past the hotel's front, on the beach)
JETTY = 3800.0
TRADE = ['Table02', 'Table02', 'Chair01', 'Chair01', 'Chair01', 'CrateGenericNV', 'CrateGenericNV', 'NVWaterCrateSqr01',
         'Barrel03static', 'Barrel03static', 'CampfireCrafting03']
LANTERN, LANTERN_LIGHT = 'LLamp01', 'NVDLC04LanternLightKeyWarm'
MARINA = (83968.0, -22528.0, 9000.0)  # (Koko Marina's basin: middle and reach)
MARINA_PIERS = 10
YARD_BOATS = ['Boat02a', 'Boat02b', 'Boat02d', 'Boat03a', 'Boat03b']
FLOTILLA = (71680.0, -46208.0)
WRECK = 'dlc04boatwrecked01'
WRECK_TURN = 0.6
WRECK_UP = 60.0                        # (its origin over the water: the main deck 161 over that)
BAR = -200.0                           # (the sandbar it lies on)
RING = (760.0, 1206.0)                 # (half sides of the planking ring, in the wreck's frame)
DOCK = landmarks.DOCK
GANG = 'NVDLC02RopeBridge03'
GANG_TILT = -1.0
NAMES = {HOTEL, 'NVJunkWall03', 'NVJunkWall04', 'NVGuardTower01', 'SandbagStraight', LANTERN, LANTERN_LIGHT, WRECK, DOCK, GANG,
         'Barge', 'Boat02a', 'Boat02b', 'Boat02c', 'Boat02d', 'Boat03a', 'Boat03b', 'Boat03e', 'WoodShack02', 'CrateGenericNV',
         'Barrel01', 'Barrel03static'} | set(TRADE) | set(YARD_BOATS)


def to_world(x0, y0, rz, lx, ly):
    c, s = math.cos(rz), math.sin(rz)
    return x0 + lx * c + ly * s, y0 - lx * s + ly * c


class Pirates:
    def __init__(self, gd, pr, world, side, cat):
        self.B = B = ridgeplaces.Builder(gd, pr, world, side, cat)
        found = shipinside._forms(gd, NAMES)
        B.key_of.update({e: gd.key(f) for e, f in found.items()})
        B.rep['missing'] |= NAMES - set(found) - {HOTEL}
        self.gd, self.pr, self.world = gd, pr, world
        self.rep = {}
        self.harbour_ops = []

    def _name(self, ck, rk):
        import natcompound
        r = self.pr.cells.get(ck, {}).get('refs', {}).get(rk)
        return natcompound._named(self.gd, self.pr, r['base']) if r and r.get('base') else ''

    def raw(self, edid, x, y, z, yaw, rx=0.0, ry=0.0, extra=None):
        B = self.B
        ck = B.w.cell_at(x, y)
        if ck is None or edid not in B.key_of:
            return False
        o = {'op': 'add', 'cell': ck, 'base': B.key_of[edid], 'p': [round(x, 1), round(y, 1), round(z, 1), round(rx, 4), round(ry, 4),
             round(yaw % math.tau, 4)], 's': 1}
        if extra:
            o['extra'] = extra
        B.ops.append(o)
        B.cells.add(ck)
        return True

    def post(self, pl, x, y, face):
        fx, fy = math.sin(face), math.cos(face)
        rx, ry = math.cos(face), -math.sin(face)
        n = 0
        for ax, sy, turn in ((0.0, 160.0, face + math.pi / 2), (-170.0, 0.0, face), (170.0, 0.0, face)):
            n += pl.put('SandbagStraight', x + fx * sy + rx * ax, y + fy * sy + ry * ax, turn, r=60.0)
        return n

    def lantern(self, pl, x, y):
        if pl.put('Barrel03static', x, y, 0.0, r=35.0):
            o = self.B.ops[-1]
            self.raw(LANTERN, x, y, o['p'][2] + 90.0, 0.0)
            self.raw(LANTERN_LIGHT, x, y, o['p'][2] + 140.0, 0.0)
            return 1
        return 0

    def harbour(self, lines):
        """Piers and moored boats by landmarks.Batch.harbour, without its crane (it levels ground of its own)."""
        Bt = landmarks.Batch(self.gd, self.pr, self.world)
        crane = landmarks.CRANE
        landmarks.CRANE = ('', 0.0)
        try:
            rep = Bt.harbour(lines)
        finally:
            landmarks.CRANE = crane
        done = Bt.done()
        self.harbour_ops += [o for o in done if o['op'] == 'add']
        return rep

    # ----- the Kahala -----

    def kahala(self):
        B = self.B
        hk = next((k for k, r in self.pr.records.items() if k.startswith('+') and r.get('type') == 'STAT'
                   and _edid(r) == HOTEL), None)
        at = None
        for ck in B.w.grid.values():
            c = self.pr.cells.get(self.gd.key(ck))
            for r in (c or {}).get('refs', {}).values():
                if r.get('base') == hk and not r.get('removed') and r.get('p'):
                    at = r['p']
            if at:
                break
        if not at:
            self.rep['kahala'] = 'no Kahala Reef hotel'
            return
        hx, hy, rz = at[0], at[1], at[5]
        box = next(q for q in self.pr.records[hk]['subs'] if q['tag'] == 'OBND')
        b = [f['value'] for f in box['fields']]
        W = lambda lx, ly: to_world(hx, hy, rz, lx, ly)
        # (the hotel's own bounds into the world, so nothing is stood in it)
        B.w.add([W(b[0], b[1]), W(b[3], b[1]), W(b[3], b[4]), W(b[0], b[4])], 'kahala', 'kahala')
        x0, x1, y0, y1 = b[0] - RING_OUT, b[3] + RING_OUT, b[1] - RING_OUT, b[4] + BEACH
        pl = ridgeplaces.Place(B, 'kahala', hx, hy, 0.0)
        loop = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        gates = [(0.0, y0), (0.0, y1)]
        towers = []
        for cx_, cy_ in ((x0, y0), (x1, y0)):
            # (at the corner, or a step out past it: the tower's foot is wider than the gap to the hotel)
            for out in (0.0, 150.0, 300.0, 450.0, 600.0):
                ox, oy = cx_ + (out if cx_ > 0 else -out), cy_ - out
                x, y = W(ox, oy)
                fp = [(x - 380, y - 380), (x + 380, y - 380), (x + 380, y + 380), (x - 380, y + 380)]
                blocked, clear = B.blocking(fp)
                if not blocked:
                    B.take_out(clear)
                    if pl.put('NVGuardTower01', x, y, rz + math.pi, check=False):
                        towers.append((cx_, cy_))
                        break
        walls = skipped = 0
        plen = 490.0
        for (ax, ay), (bx, by) in zip(loop, loop[1:]):
            L = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / L, (by - ay) / L
            for i in range(int(L // plen)):
                lx, ly = ax + ux * (i + 0.5) * plen, ay + uy * (i + 0.5) * plen
                if any(math.hypot(lx - gx, ly - gy) < GATE / 2 + plen / 2 for gx, gy in gates) or                         any(math.hypot(lx - tx_, ly - ty_) < 450.0 for tx_, ty_ in towers):
                    continue
                x, y = W(lx, ly)
                fp = [(x - 120, y - 120), (x + 120, y - 120), (x + 120, y + 120), (x - 120, y + 120)]
                blocked, clear = B.blocking(fp)
                if blocked:
                    # (pavement slabs are no reason to leave a gap: a wall stands on them)
                    blocked = any(big and townbuild.overlap(fp, ofp) and not B.clearable(ck, rk) and not self._name(ck, rk).startswith('SW')
                                  for ck, rk, ofp, big, _o in B.w.near(fp))
                g = B.ground.at(x, y)
                if blocked or g is None or g < 4.0:
                    skipped += 1
                    why = 'sea' if (g is None or g < 4.0) else 'blocked'
                    if blocked:
                        import natcompound
                        for ck, rk, ofp, big, _o in B.w.near(fp):
                            if big and townbuild.overlap(fp, ofp) and not B.clearable(ck, rk):
                                r_ = self.pr.cells.get(ck, {}).get('refs', {}).get(rk)
                                why = natcompound._named(self.gd, self.pr, r_['base']) if r_ else ck
                                break
                    self.rep.setdefault('kahala_skips', {})
                    self.rep['kahala_skips'][why] = self.rep['kahala_skips'].get(why, 0) + 1
                    continue
                B.take_out(clear)
                wx, wy = W(lx + ux, ly + uy)
                yaw = math.atan2(wx - x, wy - y)
                walls += pl.put(('NVJunkWall03', 'NVJunkWall04')[walls % 2], x, y, yaw, r=plen / 2, sink=30.0, check=False)
        posts = 0
        for (gx, gy), face in zip(gates, (rz + math.pi, rz)):
            for sx in (-1, 1):
                out = -1.0 if gy == y0 else 1.0
                x, y = W(gx + sx * (GATE / 2 + 250.0), gy + out * 350.0)
                posts += self.post(pl, x, y, face)
        # the trade ground outside the land gate
        tx, ty = W(0.0, y0 - 1100.0)
        trade = 0
        for k, e in enumerate(TRADE):
            for tr in range(12):
                a = k * 2.39996 + tr * 0.7
                r = 220.0 + 45.0 * tr
                if pl.put(e, tx + math.cos(a) * r, ty + math.sin(a) * r, a, r=60.0):
                    trade += 1
                    break
        trade += self.lantern(pl, tx + 60.0, ty - 60.0)
        trade += self.lantern(pl, *W(0.0, y1 + 60.0))
        # the jetty from the sea gate
        sx_, sy_ = W(0.0, y1 - 200.0)
        ex, ey = W(0.0, y1 + JETTY)
        jetty = self.harbour([[(sx_, sy_), (ex, ey)]])
        self.rep['kahala'] = {'walls': walls, 'skipped': skipped, 'towers': len(towers), 'post_pieces': posts, 'trade': trade, 'jetty': jetty}

    # ----- Koko Marina -----

    def marina_piers(self):
        """Lines out from the marina's shore into its water, where no pier stands yet."""
        B = self.B
        cx, cy, R = MARINA
        docks = []
        for ck in B.w.grid.values():
            c = self.pr.cells.get(self.gd.key(ck))
            for r in (c or {}).get('refs', {}).values():
                if r.get('p') and not r.get('removed') and r.get('base') == B.key_of.get(DOCK) and math.hypot(r['p'][0] - cx, r['p'][1] - cy) < R + 2000:
                    docks.append(r['p'][:2])
        lines, starts = [], []
        for gx in range(int(cx - R), int(cx + R), 256):
            for gy in range(int(cy - R), int(cy + R), 256):
                g = B.ground.at(gx, gy)
                if g is None or g < 8.0 or g > 80.0:
                    continue
                for k in range(16):
                    a = k * math.tau / 16
                    ux, uy = math.cos(a), math.sin(a)
                    wet = [B.ground.at(gx + ux * d, gy + uy * d) for d in (300.0, 900.0, 1500.0, 2000.0)]
                    if all(v is not None and v < -150.0 for v in wet):
                        if all(math.hypot(gx - a_, gy - b_) > 1100.0 for a_, b_ in starts + docks):
                            starts.append((gx, gy))
                            lines.append([(gx - ux * 200.0, gy - uy * 200.0), (gx + ux * 2000.0, gy + uy * 2000.0)])
                        break
        lines.sort(key=lambda l: math.hypot(l[0][0] - cx, l[0][1] - cy))
        return lines[:MARINA_PIERS], len(docks)

    def marina(self):
        B = self.B
        lines, had = self.marina_piers()
        rep = {'had_docks': had, 'piers_planned': len(lines)}
        rep['harbour'] = self.harbour(lines)
        # the boatyard: on flat shore near the first pier
        yard = False
        cx, cy, R = MARINA
        for (ax, ay), (bx, by) in lines:
            ux, uy = (bx - ax) / math.dist((ax, ay), (bx, by)), (by - ay) / math.dist((ax, ay), (bx, by))
            for back in (900.0, 1200.0, 1500.0):
                mx, my = ax - ux * back, ay - uy * back
                pl = ridgeplaces.Place(B, 'boatyard', mx, my, 0.0)
                if not pl.free(mx, my, 650.0):
                    continue
                yaw = math.atan2(ux, uy)
                n = 0
                for k, e in enumerate(YARD_BOATS):
                    lx = (k - 2) * 260.0
                    x, y = mx + uy * lx, my - ux * lx
                    n += pl.put(e, x, y, yaw, sink=-60.0, tilt=(0.0, (0.12 if k % 2 else -0.1)), r=60.0, check=False)
                for e, lx, ly in (('WoodShack02', -420.0, 380.0), ('CrateGenericNV', 450.0, 380.0), ('CrateGenericNV', 520.0, 300.0),
                                  ('Barrel01', 420.0, -300.0)):
                    n += pl.put(e, mx + uy * lx - ux * ly, my - ux * lx - uy * ly, yaw, r=60.0 if e != 'WoodShack02' else None)
                n += self.post(pl, mx + ux * 650.0, my + uy * 650.0, yaw)
                # (a junk wall round the three landward sides)
                for lx, ly, t in [(-490.0 + 490.0 * k, 700.0, math.pi / 2) for k in range(3)] + [(-700.0, -250.0 + 490.0 * k, 0.0) for k in range(2)] + \
                                 [(700.0, -250.0 + 490.0 * k, 0.0) for k in range(2)]:
                    x, y = mx + uy * lx - ux * ly, my - ux * lx - uy * ly
                    n += pl.put(('NVJunkWall03', 'NVJunkWall04')[int(lx + ly) % 2], x, y, yaw + t, r=245.0, sink=30.0, check=False)
                g = B.ground.at(mx, my)
                B.ops.append(worldrec.marker_op(self.gd, self.world, [round(mx, 1), round(my, 1), round((g or 0) + 60, 1)], 'Koko Marina', 3, flags=2))
                yard = {'at': [round(mx), round(my)], 'things': n}
                break
            if yard:
                break
        rep['boatyard'] = yard
        self.rep['marina'] = rep

    # ----- the Flotilla -----

    def flotilla_layout(self):
        """[(edid, lx, ly, lz, rx, ry, rz)] in the wreck's frame, z from the water."""
        out = [(WRECK, 0.0, 0.0, WRECK_UP, 0.0, 0.035, 0.0)]
        (hx, hy) = RING
        up = landmarks.DOCK_UP
        # (each side from corner to corner, its pieces spread evenly: a side short of its corner left the ring in two)
        n = int(math.ceil(2 * hy / 230.0)) + 1
        for k in range(n):
            ly = -hy + 2 * hy * k / (n - 1)
            for sx in (-1, 1):
                out.append((DOCK, sx * hx, ly, up, 0.0, 0.0, 0.0))
        n = int(math.ceil(2 * hx / 230.0)) + 1
        for k in range(1, n - 1):
            lx = -hx + 2 * hx * k / (n - 1)
            for sy in (-1, 1):
                out.append((DOCK, lx, sy * hy, up, 0.0, 0.0, math.pi / 2))
        # one gangplank up to the deck, on its east side at its middle (walkcheck: the west side's never met the deck)
        deck = WRECK_UP + 161.0
        for sx in (1,):
            x0, x1 = sx * hx, sx * 230.0
            rise = deck - 9.0
            run = abs(x1 - x0)
            out.append((GANG, (x0 + x1) / 2, 80.0, (deck + 9.0) / 2 - 100.0, 0.0, GANG_TILT * sx * math.atan2(rise, run), 0.0))
        # barges at the ring's ends, boats moored outside
        for sy in (-1, 1):
            for lx in (-230.0, 230.0):
                out.append(('Barge', lx, sy * (hy + 330.0), -8.0, 0.0, 0.0, 0.0))
        for k, ly in enumerate((-800.0, -100.0, 650.0)):
            for sx in (-1, 1):
                out.append((('Boat02a', 'Boat02b', 'Boat02d')[k], sx * (hx + 320.0), ly, -60.0, 0.0, 0.0, 0.0))
        for k, (lx, ly) in enumerate(((-1400.0, -1700.0), (1500.0, 1650.0), (-1500.0, 1300.0), (1350.0, -1800.0))):
            out.append((('Boat03a', 'Boat03b', 'Boat03e', 'Boat03a')[k], lx, ly, -12.0, 0.0, 0.0, k * 1.3))
        return out

    def flotilla(self):
        B = self.B
        fx, fy = FLOTILLA
        w = B.ground.water(fx, fy) or 0.0
        # the sandbar under the wreck
        bar = 0
        for gx in range(int((fx - 1300) // 128), int((fx + 1300) // 128) + 2):
            for gy in range(int((fy - 1300) // 128), int((fy + 1300) // 128) + 2):
                x, y = gx * 128.0, gy * 128.0
                lx, ly = _local(fx, fy, WRECK_TURN, x, y)
                d = math.hypot(max(abs(lx) - 450.0, 0.0), max(abs(ly) - 900.0, 0.0))
                if d > 600.0:
                    continue
                u = d / 600.0
                u = u * u * (3 - 2 * u)
                for cx in ({gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}):
                    for cy in ({gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}):
                        f = B._form((cx, cy))
                        if not f:
                            continue
                        k = (gy - cy * 32) * 33 + (gx - cx * 32)
                        old = f['h'][k]
                        target = w + BAR
                        if old < target:
                            f['h'][k] = round((target + (old - target) * u) / 8.0) * 8.0
                            bar += 1
        n = 0
        for e, lx, ly, lz, rx, ry, rz in self.flotilla_layout():
            x, y = to_world(fx, fy, WRECK_TURN, lx, ly)
            n += self.raw(e, x, y, w + lz, WRECK_TURN + rz, rx, ry)
        lan = 0
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            x, y = to_world(fx, fy, WRECK_TURN, sx * (RING[0] - 40.0), sy * (RING[1] - 40.0))
            z = w + landmarks.DOCK_UP + 32.0
            lan += self.raw('Barrel03static', x, y, z, 0.0)
            self.raw(LANTERN, x, y, z + 90.0, 0.0)
            self.raw(LANTERN_LIGHT, x, y, z + 140.0, 0.0)
        g = B.ground.at(fx, fy)
        B.ops.append(worldrec.marker_op(self.gd, self.world, [fx, fy, round(w + 250.0, 1)], 'The Flotilla', 3, flags=2))
        self.rep['flotilla'] = {'pieces': n, 'lanterns': lan, 'sandbar_points': bar, 'water': w, 'seabed': round(g or 0)}


def _local(x0, y0, rz, x, y):
    dx, dy = x - x0, y - y0
    c, s = math.cos(rz), math.sin(rz)
    return dx * c - dy * s, dx * s + dy * c


def _edid(rec):
    import recordio
    return recordio.field(rec, 'EDID')


def flotilla_items(gd):
    """The Flotilla's pieces in its own frame for walkcheck (water at z 0), and a start on its planking and the goal on
    the wreck's deck."""
    P = Pirates.__new__(Pirates)
    keys = {e: gd.key(f) for e, f in shipinside._forms(gd, NAMES).items()}
    items = [{'base': keys[e], 'pos': (lx, ly, lz), 'rot': (rx, ry, rz), 'scale': 1.0} for e, lx, ly, lz, rx, ry, rz in Pirates.flotilla_layout(P)
             if e in keys and not e.startswith('Boat0')]
    return items, [(RING[0], 0.0, 20.0)], [(0.0, 87.0, WRECK_UP + 161.0)]


def ops(gd, pr, world, side, cat=None, only=('kahala', 'marina', 'flotilla')):
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    P = Pirates(gd, pr, world, side, cat)
    for what in only:
        getattr(P, what)()
    B = P.B
    lands = []
    for k in sorted(B.forms):
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': B.forms[k]})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    for o in P.harbour_ops:
        B.cells.add(o['cell'])
    allops = lands + moves + B.ops + P.harbour_ops
    rep = dict(P.rep, missing=sorted(B.rep['missing']), added=sum(1 for o in allops if o['op'] == 'add'),
               removed=sum(1 for o in allops if o['op'] == 'remove'), land_cells=len(lands))
    return allops, rep, sorted(B.cells)
