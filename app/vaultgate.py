"""The Vault's outside at Ka'au Crater (docs/waikiki-story-plan.md, build list 4; the door high in the north wall,
decided 19 Nov 2026; sketch docs/waikiki-vault-door-sketch.png):

- **The slave road's last stretch.** From where Waiomao Road ends (the street map's last point) a track up the valley
  to the crater's low lip on its open side (`LIP`), the cheapest way by steepness alone, cut in as the Crest Trail's
  tread is (cresttrail.Trail.tread) and painted with mud.
- **The waystation** at the road's end, where people are held before the climb: a shack, a row of cages, a fire, a
  sandbag post, a map marker (shown once found).
- **The climb.** On the crater's north wall: `LEGS` legs of a ledge path across the face, each turning back at the
  end, from the floor up to a landing `DOOR_UP` over it. A leg's points are where the wall stands at the leg's height
  (`_on_face`), so the ledge follows the cliff; the land within `LEDGE` of it is brought to the leg's height (cut into
  the wall, built out where it falls away), eased back over `LEDGE_EASE`. The game's road guardrail along the open side, a
  lamp at each turn.
- **The landing and the door.** A level landing (ridgeplaces.Builder.terrace) and on it the game's Vault 22 entrance
  (`ENTRANCE`, a concrete portal running back into the hill) with its gear door, as the game stands the pair; the door
  locked, needing a key, until the Vault's inside is made. Lamps either side, a light at the door.
- A map marker for Ka'au Crater on the lip.

The lights show only while their cells are loaded: seen from Waikiki at night needs far lights of FOLab's own (not done).
`ops` returns (ops, report, cells); nothing is applied."""
import heapq
import math

import cresttrail
import ridgeplaces
import shipinside
import townbuild
import worldrec

FLOOR = (-14800.0, 54600.0)          # (the crater floor's middle, measured 19 Nov 2026)
LIP = (-10470.0, 52100.0)            # (its low south-east lip, the open side)
ROAD_END = (-25798.0, 27141.0)       # (Waiomao Road's last point on the street map)
DOOR_X = -14400.0                    # (the door's x: the middle of the north wall's even stretch, x -15600..-13200)
DOOR_UP = 2300.0                     # (the landing over the floor: about 33 m)
FLOOR_Z = 12960.0
LEGS = [-800.0, 1100.0, -1100.0, 1100.0, -1100.0]     # (the turns' x from DOOR_X, from the landing down)
LEDGE, LEDGE_EASE = 130.0, 180.0
LANDING = (800.0, 520.0)             # (half its width and depth)
ENTRANCE, GEAR = 'Vault22Entrance', 'VGearDoorR22'
DOOR_IN_ENTRANCE = (-18.0, 27.0, -4.0)    # (the door in the entrance's frame, as the game has them)
RAIL = 'GuardRailStraight01'          # (the game's road guardrail: 248 along its own y, its middle at its origin)
RAIL_LONG, RAIL_STEP, RAIL_OUT, RAIL_UP = 248.0, 237.0, 110.0, 48.0
OLD_RAIL = 'JerseyBarricade01'      # (what stood there first, 19 Nov 2026: short blocks, each on its own bit of slope)
LAMP, LAMP_LIGHT, LAMP_LIGHT_AT = 'NVStreetlight01', 'NellisStreetLight', (-1.0, 127.0, 481.0)
DOOR_LIGHT = 'VaultExtraWarm256'
LEDGE_GROUND = 'LDirtPebblesCanyon01'
SHACK = 'WoodShack02'
CAGE = 'DeathClawCage'
CAMP = [('CampfireCrafting03', 1), ('NVBedrollL', 2), ('Barrel01', 2), ('CrateGenericNV', 2)]
NAMES = {ENTRANCE, GEAR, RAIL, OLD_RAIL, LAMP, LAMP_LIGHT, DOOR_LIGHT, SHACK, CAGE, 'SandbagStraight'} | {e for e, _n in CAMP}


def _tilt_for(ux, uy, uz):
    """The game's turn (rx, ry, rz) that lays a piece's own +y along (ux, uy, uz): rz the heading, rx and ry found
    against navgen's reading of the game's turn (its tilt goes round the world's axes, not the piece's)."""
    import navgen
    L = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
    want = (ux / L, uy / L, uz / L)
    rz = math.atan2(ux, uy)
    best = (9.0, 0.0, 0.0)
    span = 0.6
    cx = cy = 0.0
    for _ in range(4):
        for i in range(-6, 7):
            for j in range(-6, 7):
                rx, ry = cx + span * i / 6, cy + span * j / 6
                M = navgen._turn(rx, ry, rz)
                got = (M[0][1], M[1][1], M[2][1])
                err = sum((a - b) ** 2 for a, b in zip(got, want))
                if err < best[0]:
                    best = (err, rx, ry)
        cx, cy = best[1], best[2]
        span /= 4
    return best[1], best[2], rz


def guardrails(pts, zs, side=-1):
    """[(x, y, z, rx, ry, rz)]: guardrail sections end to end along a line (pts, its heights zs), RAIL_OUT to its open
    side (side -1: the side towards -y, the crater's floor), each tilted to the line's climb; a fresh run after a turn."""
    out = []
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + math.dist(a, b))

    def at(t):
        for k in range(1, len(d)):
            if d[k] >= t:
                u = (t - d[k - 1]) / ((d[k] - d[k - 1]) or 1.0)
                return (pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * u, pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * u,
                        zs[k - 1] + (zs[k] - zs[k - 1]) * u)
        return (pts[-1][0], pts[-1][1], zs[-1])
    t = 0.0
    while t + RAIL_LONG < d[-1]:
        a, b = at(t), at(t + RAIL_STEP)
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        L = math.hypot(ux, uy) or 1.0
        c = at(t + RAIL_STEP / 2)
        nx, ny = -uy / L, ux / L
        if (ny > 0) != (side > 0):
            nx, ny = -nx, -ny
        # (a turn here: the line bends sharply over the section, so leave a gap and start again past it)
        bend = abs(math.atan2(ux, uy) - math.atan2(c[0] - a[0], c[1] - a[1]))
        if min(bend, math.tau - bend) > 0.35:
            t += RAIL_STEP
            continue
        rx, ry, rz = _tilt_for(ux, uy, uz)
        out.append((c[0] + nx * RAIL_OUT, c[1] + ny * RAIL_OUT, c[2] + RAIL_UP, rx, ry, rz))
        t += RAIL_STEP
    return out


def _route_flat(ground, a, b, box=(-40000.0, 0.0, 20000.0, 60000.0), st=256.0):
    """The cheapest way from a to b by steepness alone (a track up a valley, not a ridge path)."""
    G = cresttrail.Grid.__new__(cresttrail.Grid)
    G.x0, G.x1, G.y0, G.y1 = box
    G.nx, G.ny = int((G.x1 - G.x0) / st) + 1, int((G.y1 - G.y0) / st) + 1
    G.H = [[ground.at(G.x0 + i * st, G.y0 + j * st) for i in range(G.nx)] for j in range(G.ny)]
    G.top = 1.0
    G.hollow = [[0.0] * G.nx for _ in range(G.ny)]

    def cost(u, v):
        ha, hb = G.H[u[0]][u[1]], G.H[v[0]][v[1]]
        if ha is None or hb is None or hb < 40.0:
            return None
        L = st * math.hypot(u[0] - v[0], u[1] - v[1])
        gr = abs(hb - ha) / L
        return L * (1 + 12 * gr * gr) * (20.0 if gr > 0.75 else 1.0)
    G.cost = cost
    p = G.route(G.node(*a), G.node(*b))
    return [G.xy(n) for n in p] if p else []


class Gate:
    def __init__(self, gd, pr, world, side, cat):
        self.T = cresttrail.Trail(gd, pr, world, side, cat)
        self.B = B = self.T.B
        found = shipinside._forms(gd, NAMES)
        B.key_of.update({e: gd.key(f) for e, f in found.items()})
        B.rep['missing'] |= NAMES - set(found)
        self.gd, self.pr, self.world = gd, pr, world
        self.rep = {}

    def _on_face(self, x, z, y0=FLOOR[1] + 1800.0):
        """y on the north wall at x where the ground (as it was) first stands at z, going north from the floor."""
        y = y0
        while y < FLOOR[1] + 9000.0:
            g = self.B.orig.at(x, y)
            if g is not None and g >= z:
                return y
            y += 16.0
        return y

    def raw(self, edid, x, y, z, yaw, extra=None):
        B = self.B
        ck = B.w.cell_at(x, y)
        if ck is None or edid not in B.key_of:
            return False
        o = {'op': 'add', 'cell': ck, 'base': B.key_of[edid], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0,
             round(yaw % math.tau, 4)], 's': 1}
        if extra:
            o['extra'] = extra
        B.ops.append(o)
        B.cells.add(ck)
        return True

    def ledge(self, pts, zs):
        """Land within LEDGE of the line to the line's heights (zs), eased back over LEDGE_EASE."""
        T = self.T
        near = {}
        reach = LEDGE + LEDGE_EASE
        for (x, y), z in zip(pts, zs):
            for gy in range(int((y - reach) // 128), int((y + reach) // 128) + 2):
                for gx in range(int((x - reach) // 128), int((x + reach) // 128) + 2):
                    d = math.hypot(gx * 128.0 - x, gy * 128.0 - y)
                    if d < reach and d < near.get((gx, gy), (1e9,))[0]:
                        near[(gx, gy)] = (d, z)
        for (gx, gy), (d, zt) in near.items():
            u = 0.0 if d <= LEDGE else (d - LEDGE) / LEDGE_EASE
            u = u * u * (3 - 2 * u)
            for f, _ck, k in T._points(gx, gy):
                old = f['h'][k]
                if (gx, gy) not in T.changed:
                    T.changed[(gx, gy)] = old
                f['h'][k] = round((zt + (old - zt) * u) / cresttrail.STEP) * cresttrail.STEP

    # ----- the parts -----

    def climb(self):
        """The landing, the door and the ledge path down from it. Returns the path's line."""
        B = self.B
        land_z = round((FLOOR_Z + DOOR_UP - 120.0) / 8.0) * 8.0
        yf = self._on_face(DOOR_X, land_z + 120.0)
        ye = yf + 500.0                                   # (the entrance set into the wall)
        B.terrace(DOOR_X, ye - LANDING[1] + 20.0, 0.0, LANDING[0], LANDING[1], z=land_z, ease=320.0)
        ez = land_z + 125.0
        self.raw(ENTRANCE, DOOR_X, ye, ez, 0.0)
        dx, dy, dz = DOOR_IN_ENTRANCE
        self.raw(GEAR, DOOR_X + dx, ye + dy, ez + dz, 0.0, extra=townbuild.DOOR_LOCK)
        self.raw(DOOR_LIGHT, DOOR_X, ye - 450.0, ez + 260.0, 0.0)
        for sx in (-1, 1):
            self._lamp(DOOR_X + sx * 650.0, ye - 700.0, land_z, math.pi)
        # the legs, from the landing's west corner down
        turns = []
        zs_ = [land_z - k * (land_z - FLOOR_Z) / (len(LEGS) - 1) for k in range(len(LEGS))]
        for k, (ox, z) in enumerate(zip(LEGS, zs_)):
            x = DOOR_X + ox
            y = (ye - 2 * LANDING[1] + 120.0) if k == 0 else self._on_face(x, z)
            turns.append((x, y, z))
        pts, zs = [], []
        for (xa, ya, za), (xb, yb, zb) in zip(turns, turns[1:]):
            n = max(2, int(math.hypot(xb - xa, yb - ya) / 48.0))
            for t in range(n):
                u = t / n
                x, z = xa + (xb - xa) * u, za + (zb - za) * u
                y = ya if (u == 0 and pts == []) else self._on_face(x, z)
                pts.append((x, y))
                zs.append(z)
        pts.append(turns[-1][:2])
        zs.append(turns[-1][2])
        self.ledge(pts, zs)
        rails = lamps = 0
        # guardrail along the open (south) side, end to end at the path's height, tilted to its climb; lamps at the turns
        for x, y, z, rx, ry, rz in guardrails(pts, zs):
            ck = B.w.cell_at(x, y)
            if ck is not None:
                B.ops.append({'op': 'add', 'cell': ck, 'base': B.key_of[RAIL], 'p': [round(x, 1), round(y, 1), round(z, 1), round(rx, 4), round(ry, 4), round(rz, 4)], 's': 1})
                B.cells.add(ck)
                rails += 1
        for x, y, z in turns[1:-1]:
            lamps += self._lamp(x, y + 160.0, B.ground.at(x, y + 160.0) or z, math.pi)
        self.rep['climb'] = {'landing_z': land_z, 'door': [round(DOOR_X), round(ye), round(ez)], 'legs': len(turns) - 1,
                             'turns': [[round(a), round(b), round(c)] for a, b, c in turns], 'rails': rails, 'lamps': lamps}
        return pts

    def _lamp(self, x, y, z, yaw):
        if not self.raw(LAMP, x, y, z - 4.0, yaw):
            return 0
        lx, ly, lz = LAMP_LIGHT_AT
        c, s = math.cos(yaw), math.sin(yaw)
        self.raw(LAMP_LIGHT, x + lx * c + ly * s, y - lx * s + ly * c, z + lz, 0.0)
        return 1

    def road(self):
        pts = _route_flat(self.B.ground, ROAD_END, LIP)
        line = cresttrail.smooth_line(pts)
        self.T.tread(line, skip=300.0)
        self.rep['road'] = {'length': round(sum(math.dist(a, b) for a, b in zip(line, line[1:])))}
        return line

    def waystation(self, line):
        B = self.B
        # (a little way up the track from the road's end, off to one side)
        k = min(len(line) - 2, 14)
        (xa, ya), (xb, yb) = line[k], line[k + 1]
        L = math.dist((xa, ya), (xb, yb)) or 1.0
        ux, uy = (xb - xa) / L, (yb - ya) / L
        nx, ny = -uy, ux
        mx, my = xa + nx * 900.0, ya + ny * 900.0
        B.terrace(mx, my, math.atan2(-uy, ux), 700.0, 600.0, ease=400.0)
        pl = ridgeplaces.Place(B, 'waystation', mx, my, 0.0)
        yaw = math.atan2(-nx, -ny)                     # (facing the track)
        n = {'shack': 0, 'cages': 0, 'camp': 0, 'post': 0}
        for r in (0.0, 200.0, 400.0):
            if pl.put(SHACK, mx + nx * (250 + r), my + ny * (250 + r), yaw):
                n['shack'] = 1
                break
        for off in (250.0, 450.0, -450.0, 650.0, -650.0):
            if n['cages']:
                break
            for c_ in range(4):
                t = (c_ - 1.5) * 230.0
                n['cages'] += pl.put(CAGE, mx - nx * off + ux * t, my - ny * off + uy * t, yaw + math.pi, r=40.0)
        for e, cnt in CAMP:
            for j in range(cnt):
                for tr in range(10):
                    a = (j * 2.3 + tr * 0.9 + len(e))
                    if pl.put(e, mx + math.cos(a) * (300 + 40 * tr), my + math.sin(a) * (300 + 40 * tr), a):
                        n['camp'] += 1
                        break
        for side in (-1, 1):
            for off in (300.0, 450.0, 600.0):
                if pl.put('SandbagStraight', xa + nx * off + ux * side * 200.0, ya + ny * off + uy * side * 200.0, math.atan2(ux, uy), r=60.0):
                    n['post'] += 1
                    break
        g = B.ground.at(mx, my)
        B.ops.append(worldrec.marker_op(self.gd, self.world, [round(mx, 1), round(my, 1), round((g or 0) + 60, 1)], 'Waystation', 3, flags=2))
        self.rep['waystation'] = dict(n, at=[round(mx), round(my)])


def ops(gd, pr, world, side, cat=None):
    """(ops, report, cells)."""
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    V = Gate(gd, pr, world, side, cat)
    B, T = V.B, V.T
    track = V.road()
    V.waystation(track)
    ledge = V.climb()
    T.line_buckets = {}
    for x, y in track + ledge:
        T.line_buckets.setdefault((int(x // 512), int(y // 512)), []).append((x, y))
    T.paint(track)
    mud = T.mud
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'LTEX' and gd.edid(f) == LEDGE_GROUND:
            import land
            T.mud, T.mud_tex = f, land.texture_of_fid(gd, f, {})
            break
    T.paint(ledge)
    T.mud = mud
    g = B.ground.at(*LIP)
    B.ops.append(worldrec.marker_op(gd, world, [LIP[0], LIP[1], round((g or 0) + 60, 1)], "Ka'au Crater", 4, flags=2))
    V.rep['walk'] = cresttrail.walk_check(B.ground, {'track': track, 'ledge': ledge})
    moved, gone = T.reseat()
    lands = []
    for k in sorted(B.forms):
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': B.forms[k]})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    rep = dict(V.rep, moved=len(moves), cleared=gone, land_cells=len(lands), missing=sorted(B.rep['missing']),
               added=sum(1 for o in B.ops if o['op'] == 'add'), removed=sum(1 for o in B.ops if o['op'] == 'remove'),
               ledge_line=[[round(x), round(y)] for x, y in ledge], track_line=[[round(x), round(y)] for x, y in track[::8]])
    return lands + moves + B.ops, rep, sorted(B.cells)
