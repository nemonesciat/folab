"""The settlers' land at Waimanalo (docs/waikiki-story-plan.md, build list 6), in settlerset's pieces:

- **The ship.** Their freighter run bow-first up the beach near the plan's spot (`SHIP_NEAR`): her bow a step inland
  of the waterline, her keel in the sand there, her line straight up the beach (the shore's own slope says which way),
  her ramp down to a level plaza.
- **The road of gates.** From the plaza straight inland along her line, the five gates (`GATES`), the grandest by the
  ship, the plainest farthest; the road cut in and painted.
- **Courtyards** either side between the gates: a square of wall (`YARD`) open by a gateway to the road, a screen wall
  inside it, a hall at the back facing the road; red-roofed halls nearest the ship.
- **Fields** beyond the courtyards: rows of maize.
- **The north border post**: a gate across the coast road where it is farthest north, a wall either side, a guard
  tower, a marker. **Makapu'u Gate**: a gate across the same road nearest `MAKAPUU`, their gate for trade.

What stood where these go (the city's houses, their things) is taken out, as townbuild.crowding does. Nobody lives here
yet. `ops` returns (ops, report, cells)."""
import math

import cresttrail
import modelsets
import ridgeplaces
import settlerset as SS
import shipinside
import townbuild
import worldrec

SHIP_NEAR = (92160.0, 79872.0)
BOW_INLAND = 500.0
PLAZA = 900.0
GATES = [(900.0, 5), (3100.0, 4), (5300.0, 3), (7500.0, 2), (9700.0, 1)]   # (distance from the ramp's foot, which gate)
ROAD_LONG = 10300.0
YARD = 1000.0                      # (half a courtyard's side)
YARD_OUT = 1650.0                  # (a courtyard's middle this far from the road's line)
FIELD_OUT = 4200.0
MAKAPUU = (123180.0, 30000.0)
BORDER = (50000.0, 93500.0)        # (the border post on the coast road north-west out of Waimanalo, a little inside the map's top edge)
ROAD_GROUND = 'LDirtPathWasteland01'
NAMES = {'SCOLmaizeRow1b', 'SCOLmaizeRow2b', 'NVGuardTower01', 'SandbagStraight'}


class Settlers:
    def __init__(self, gd, pr, world, side, cat):
        self.T = cresttrail.Trail(gd, pr, world, side, cat)
        self.B = B = self.T.B
        found = shipinside._forms(gd, NAMES)
        B.key_of.update({e: gd.key(f) for e, f in found.items()})
        self.gd, self.pr, self.world, self.cat = gd, pr, world, cat
        self.records, self.own, self.zones = [], {}, []
        self.rep = {}
        self.buildings = {b['key'] for b in cat}       # (the city's buildings: crowding takes those, with their doors)

    def piece(self, name):
        if name not in self.own:
            modelsets._all_sets()
            ops, info = modelsets.put(self.pr, name)
            self.records += ops
            self.own[name] = (info['key'] or '$model_' + name, info['box'])
        return self.own[name]

    def stand(self, name, x, y, rz, z=None, sink=8.0, check=True):
        """One of the settlers' pieces at x, y turned rz, on the lowest ground under it unless z is given."""
        B = self.B
        key, box = self.piece(name)
        c, s = math.cos(rz), math.sin(rz)
        corners = [(x + lx * c + ly * s, y - lx * s + ly * c) for lx in (box[0], 0.0, box[3]) for ly in (box[1], 0.0, box[4])]
        if check:
            fp = [corners[0], corners[2], corners[8], corners[6]]
            blocked, clear = B.blocking(fp)
            if blocked:
                return False
            B.take_out(clear)
        if z is None:
            hs = [B.ground.at(px, py) for px, py in corners]
            if any(h is None for h in hs):
                return False
            z = min(hs) - sink
        ck = B.w.cell_at(x, y)
        if ck is None:
            return False
        B.ops.append({'op': 'add', 'cell': ck, 'base': key, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)], 's': 1})
        B.cells.add(ck)
        return True

    def raw(self, edid, x, y, z, rz):
        B = self.B
        ck = B.w.cell_at(x, y)
        if ck is None or edid not in B.key_of:
            return False
        B.ops.append({'op': 'add', 'cell': ck, 'base': B.key_of[edid], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)], 's': 1})
        B.cells.add(ck)
        return True

    def clear_zone(self, x, y, rz, x0, y0, x1, y1):
        """What stands in a box goes: the city's buildings (with their insides' doors unlinked) later, by crowding; the
        rest now, all but roads, doors and markers."""
        self.zones.append((x, y, rz, x0, y0, x1, y1))
        B = self.B
        c, s = math.cos(rz), math.sin(rz)
        fp = [(x + lx * c + ly * s, y - lx * s + ly * c) for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        gone = []
        for ck, rk, ofp, big, _o in B.w.near(fp):
            if (ck, rk) in B.gone or not townbuild.overlap(fp, ofp):
                continue
            r = self.pr.cells.get(ck, {}).get('refs', {}).get(rk)
            if not r or not r.get('base'):
                continue
            import natcompound
            e = natcompound._named(self.gd, self.pr, r['base'])
            if r['base'] in self.buildings or any(w in e for w in ('Road', 'Highway', 'Door', 'Marker', 'Overpass', 'Bridge')):
                continue
            gone.append((ck, rk))
        B.take_out(gone)
        return len(gone)

    # ----- the parts -----

    def ship(self):
        B = self.B
        # (the shore's way: uphill over a wide square round the spot)
        sx, sy = SHIP_NEAR
        gx = (B.ground.at(sx + 3000, sy) or 0) - (B.ground.at(sx - 3000, sy) or 0)
        gy = (B.ground.at(sx, sy + 3000) or 0) - (B.ground.at(sx, sy - 3000) or 0)
        L = math.hypot(gx, gy) or 1.0
        nx, ny = gx / L, gy / L                                  # (inland)
        # (the waterline along that way)
        x, y = sx, sy
        for _ in range(200):
            g = B.ground.at(x, y)
            if g is None:
                break
            if g > 0:
                x, y = x - nx * 50, y - ny * 50
            else:
                break
        for _ in range(400):
            g = B.ground.at(x, y)
            if g is not None and g > 0:
                break
            x, y = x + nx * 25, y + ny * 25
        bx, by = x + nx * BOW_INLAND, y + ny * BOW_INLAND
        rz = math.atan2(-nx, -ny)                                # (her +y to the sea: the bow, -y, inland)
        cx, cy = bx - nx * SS.F_HALF, by - ny * SS.F_HALF
        gb = B.ground.at(bx, by) or 0.0
        oz = gb - SS.RAMP_FOOT                                   # (the sand at her bow at RAMP_FOOT in her frame)
        foot = (bx + nx * (200.0 + SS.RAMP[1]), by + ny * (200.0 + SS.RAMP[1]))
        self.clear_zone(cx, cy, rz, -800, -SS.F_HALF - SS.RAMP[1] - 400, 800, SS.F_HALF + 300)
        # (a level plaza at the ramp's foot, at its height)
        plaza = (foot[0] + nx * PLAZA * 0.7, foot[1] + ny * PLAZA * 0.7)
        self.clear_zone(plaza[0], plaza[1], rz, -PLAZA, -PLAZA, PLAZA, PLAZA)
        B.terrace(plaza[0], plaza[1], rz, PLAZA, PLAZA, z=gb, ease=700.0)
        self.stand('settler_freighter', cx, cy, rz, z=oz, check=False)
        self.axis = (foot, (nx, ny), rz, gb)
        self.rep['ship'] = {'at': [round(cx), round(cy), round(oz)], 'turn': round(rz, 3), 'bow': [round(bx), round(by)], 'sand': round(gb),
                            'ramp_foot': [round(foot[0]), round(foot[1])]}

    def road(self):
        B, T = self.B, self.T
        (fx, fy), (nx, ny), rz, gb = self.axis
        mx, my = -ny, nx                                         # (across the road)
        line = [(fx + nx * d, fy + ny * d) for d in range(0, int(ROAD_LONG) + 1, 64)]
        self.clear_zone(fx + nx * ROAD_LONG / 2, fy + ny * ROAD_LONG / 2, rz, -450, -ROAD_LONG / 2, 450, ROAD_LONG / 2)
        T.tread(line, skip=PLAZA * 1.5)
        gates = 0
        grz = math.atan2(nx, ny)                                 # (a gate's own y along the road)
        for d, n in GATES:
            x, y = fx + nx * d, fy + ny * d
            half = {1: 420, 2: 470, 3: 760, 4: 840, 5: 950}[n]
            lv = B.terrace(x, y, grz, half + 150, 260, ease=420.0)
            gates += self.stand('settler_gate_%d' % n, x, y, grz, z=(lv or B.ground.at(x, y) or 0) - 6, check=False)
        self.road_line = line
        # courtyards
        yards = []
        for k in range(4):
            d = (GATES[k][0] + GATES[k + 1][0]) / 2
            for sd in (-1, 1):
                done = False
                for push in (0.0, 450.0, 900.0):
                    out = YARD_OUT + push
                    x, y = fx + nx * d + mx * sd * out, fy + ny * d + my * sd * out
                    if self.yard(x, y, sd, mx, my, nx, ny, red=k < 2):
                        yards.append([round(x), round(y)])
                        done = True
                        break
                if not done:
                    self.rep.setdefault('yards_no_room', 0)
                    self.rep['yards_no_room'] += 1
        # fields beyond
        fields = 0
        for k in range(4):
            d = GATES[k][0] + 600.0
            for sd in (-1, 1):
                for row in range(9):
                    for along in range(4):
                        x = fx + nx * (d + along * 860.0) + mx * sd * (FIELD_OUT + row * 190.0)
                        y = fy + ny * (d + along * 860.0) + my * sd * (FIELD_OUT + row * 190.0)
                        fp = [(x - 60, y - 60), (x + 60, y - 60), (x + 60, y + 60), (x - 60, y + 60)]
                        blocked, clear = B.blocking(fp)
                        g = B.ground.at(x, y)
                        if blocked or g is None or g < 8:
                            continue
                        B.take_out(clear)
                        fields += self.raw('SCOLmaizeRow1b' if (row + along) % 2 else 'SCOLmaizeRow2b', x, y, g - 4, grz)
        self.rep['road'] = {'gates': gates, 'yards': yards, 'maize_rows': fields}

    def yard(self, x, y, sd, mx, my, nx, ny, red=False):
        """A courtyard, its middle at x, y, open to the road (on its -sd side)."""
        B = self.B
        rz = math.atan2(sd * mx, sd * my)
        # (frame: local y away from the road, local x along it)
        c, s = math.cos(rz), math.sin(rz)
        W = lambda lx, ly: (x + lx * c + ly * s, y - lx * s + ly * c)
        fp = [W(-YARD, -YARD), W(YARD, -YARD), W(YARD, YARD), W(-YARD, YARD)]
        if any(big and townbuild.overlap(fp, ofp) and any(w in self._name(ck, rk) for w in ('Road', 'Highway'))
               for ck, rk, ofp, big, _o in B.w.near(fp)):
            return False
        self.clear_zone(x, y, rz, -YARD - 150, -YARD - 150, YARD + 150, YARD + 150)
        lv = B.terrace(x, y, rz, YARD + 100, YARD + 100, ease=450.0)
        if lv is None:
            return False
        wz = lv - 10.0
        # walls: the road side in two, a gateway between; the other three sides whole
        wall_rz_x = rz                               # (a wall's own x along the yard's x)
        wall_rz_y = rz - math.pi / 2                 # (along the yard's y)
        for lx in (-YARD + 500.0, YARD - 500.0):
            self.stand('settler_wall', *W(lx, YARD), wall_rz_x, z=wz, check=False)
        for lx in (-650.0, 650.0):                   # (a gateway 300 wide in the middle of the road side)
            self.stand('settler_wall', *W(lx, -YARD), wall_rz_x, z=wz, check=False)
        for sx in (-1, 1):
            for ly in (-YARD + 500.0, YARD - 500.0):
                self.stand('settler_wall', *W(sx * YARD, ly), wall_rz_y, z=wz, check=False)
        self.stand('settler_screen', *W(0.0, -YARD + 380.0), rz, z=wz, check=False)
        self.stand('settler_hall_red' if red else 'settler_hall', *W(0.0, YARD - 520.0), rz, z=lv - 6.0, check=False)
        return True

    def _name(self, ck, rk):
        import natcompound
        r = self.pr.cells.get(ck, {}).get('refs', {}).get(rk)
        return natcompound._named(self.gd, self.pr, r['base']) if r and r.get('base') else ''

    def _highway(self, roads):
        pts = []
        for name, kind, line in roads:
            if 'Kalaniana' in name:
                pts += line
        return pts

    def border(self, roads, where, gate, label, mtype):
        """A gate across the coast road at the point `where` picks, a wall either side, a tower, a marker."""
        B = self.B
        # (the point `where` picks, and the way the road runs there: from the stretch of road it lies on)
        pts = self._highway(roads)
        if len(pts) < 2:
            self.rep[label] = 'no coast road on the street map'
            return
        x, y = pts[where(pts)]
        best = None
        for name, kind, line in roads:
            if 'Kalaniana' not in name:
                continue
            for a, b in zip(line, line[1:]):
                L = math.dist(a, b)
                if L < 1:
                    continue
                t = max(0.0, min(1.0, ((x - a[0]) * (b[0] - a[0]) + (y - a[1]) * (b[1] - a[1])) / (L * L)))
                d = math.dist((x, y), (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                if best is None or d < best[0]:
                    best = (d, (b[0] - a[0]) / L, (b[1] - a[1]) / L)
        ux, uy = best[1], best[2]
        grz = math.atan2(ux, uy)
        lv = B.terrace(x, y, grz, 900, 300, ease=500.0) or B.ground.at(x, y) or 0.0
        self.clear_zone(x, y, grz, -1200, -400, 1200, 400)
        ok = self.stand(gate, x, y, grz, z=lv - 6, check=False)
        mx, my = -uy, ux
        half = 520.0 if gate == 'settler_gate_2' else 820.0
        walls = 0
        for sd in (-1, 1):
            for k_ in range(4):
                d = half + 500.0 + 1000.0 * k_
                wx, wy = x + mx * sd * d, y + my * sd * d
                walls += self.stand('settler_wall', wx, wy, math.atan2(-my, mx))
        tx, ty = x + mx * (half + 900) - ux * 700, y + my * (half + 900) - uy * 700
        pl = ridgeplaces.Place(B, label, tx, ty, 0.0)
        tower = pl.put('NVGuardTower01', tx, ty, grz)
        g = B.ground.at(x, y) or lv
        B.ops.append(worldrec.marker_op(self.gd, self.world, [round(x, 1), round(y, 1), round(g + 60, 1)], label, mtype, flags=2))
        self.rep[label] = {'at': [round(x), round(y)], 'gate': ok, 'walls': walls, 'tower': tower}


def ops(gd, pr, world, side, roads, cat=None):
    """(ops, report, cells). roads: [(name, kind, [(x, y)])] from the street map."""
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    S = Settlers(gd, pr, world, side, cat)
    B, T = S.B, S.T
    S.ship()
    S.road()
    S.border(roads, lambda pts: min(range(len(pts)), key=lambda i: math.dist(pts[i], BORDER)),
             'settler_gate_2', 'Border Post', 8)
    S.border(roads, lambda pts: min(range(len(pts)), key=lambda i: math.dist(pts[i], MAKAPUU)), 'settler_gate_3', "Makapu'u Gate", 8)
    # the road's ground
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'LTEX' and gd.edid(f) == ROAD_GROUND:
            import land
            T.mud, T.mud_tex = f, land.texture_of_fid(gd, f, {})
            break
    T.line_buckets = {}
    for px, py in S.road_line:
        T.line_buckets.setdefault((int(px // 512), int(py // 512)), []).append((px, py))
    T.paint(S.road_line)
    moved, _gone = T.reseat()
    # the city's buildings where the settlers' things stand
    cut, crep = townbuild.crowding(gd, pr, world, cat, S.zones, gap=60.0)
    lands = []
    for k in sorted(B.forms):
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': B.forms[k]})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    gone_refs = {o['ref'] for o in cut if o['op'] == 'remove'}
    own_ops = [o for o in B.ops if not (o['op'] == 'remove' and o['ref'] in gone_refs)]
    allops = S.records + cut + lands + moves + own_ops
    rep = dict(S.rep, pieces=sorted(S.own), buildings_taken=len(crep['buildings']), moved=len(moves),
               removed=sum(1 for o in allops if o['op'] == 'remove'), added=sum(1 for o in allops if o['op'] == 'add'), land_cells=len(lands))
    return allops, rep, sorted(B.cells)
