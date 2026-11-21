"""Waikiki's two seats of power, as the story plan has them (docs/waikiki-story-plan.md, build list 2a): the Kahuna's
court at the Royal Hawaiian and the Captain's ship, the Missouri off the Natatorium. Only what the plan says, in the
game's own pieces:

- **The court.** A walk of tiki torches from the hotel's door to Kalakaua Avenue, a sandbag guard post either side of
  where it meets the avenue, a guard tower at a front corner of the grounds, and the tribute yard beside the hotel
  (goods the valleys bring in: crates, water, barrels, in stacks).
- **The strip lit.** The Strip's street lamps, each with its light, along Kalakaua Avenue from the Kilauea to
  Kapahulu (the avenue's 'secondary' stretch on the street map): "street lights on the main strip only, the Kahuna
  showing off". Lamps alternate sides, `LAMP_EVERY` apart, stood just off the road pieces.
- **The ship.** A searchlight with its light on the first funnel's port platform (her sea side), a wind turbine and
  salvaged solar mirrors on the fantail's port side (the crane lies to starboard), sandbag posts either side of the
  gangway's inner end on deck and at the street side of the Natatorium's arch, the way aboard.
- **The handover.** The plan's people trade goes "the Kahuna to the pirates at the ship": a row of cages in the
  Natatorium's park, by the way aboard (the game's slave pen, 23 m square, has no room there).

Nobody stands in any of it yet (people come after the navmesh run). `ops` gives the ops and a report; nothing is
applied here."""
import math

import battleship
import ridgeplaces
import shipinside
import shipplace
import shipway
import townbuild

TORCH = 'OasisTorch01'
LAMP = 'NVStripStreetLamp01on'
LAMP_LIGHT = 'stripStreetLight'
LAMP_LIGHT_Z = 480.0         # (the light over the lamp's foot: its heads are at ~520)
LAMP_EVERY = 1100.0
LAMP_OFF = (360.0, 1100.0)   # (how far off the avenue's middle line a lamp may stand: off the road pieces)
STRIP_ROAD, STRIP_KIND = 'Kalākaua Avenue', 'secondary'
SANDBAG = 'SandbagStraight'
TOWER = 'NVGuardTower01'
GOODS = ['CrateGenericNV', 'NVWaterCrateSqr01', 'CrateLarge01', 'Barrel03static', 'NVMilitaryCrate']
YARD = 520.0                 # (half the tribute yard's side)
CAGES = ['DeathClawCage'] * 4                     # (the game's big cages in a row: people held for the ship)
CAGE_STEP = 230.0
SEARCHLIGHT, SEARCH_LIGHT = 'SpotlightNVGlow', 'RepConSpotLight'
TURBINE, SOLAR = 'WindmillSpinningNV', 'HeliosOneSolarReflector'
COURT_EDID = 'FOLabLandmarkRoyalHawaiian'
NAT_EDID = 'FOLabLandmarkNatatorium'
NAT_SOLID = [(-1950.0, -1700.0, 1950.0, 480.0), (-230.0, 480.0, 230.0, 800.0)]   # (pool, walls, arch and wings; the steps)
COURT_SOLID = [(-2100.0, -1900.0, 2100.0, 420.0), (-560.0, 400.0, 560.0, 1060.0)]   # (the block, wings and lawn; the porch)

NAMES = {TORCH, LAMP, LAMP_LIGHT, SANDBAG, TOWER, 'DeathClawCage', SEARCHLIGHT, SEARCH_LIGHT, TURBINE, SOLAR} | set(GOODS)

# on the ship, in her frame (port +x, the sea side; bow -y): (piece, x, y, z over the deck or None, local turn)
SHIP_THINGS = [
    (TURBINE, 300.0, 7950.0, None, math.pi / 2),
    (SOLAR, -150.0, 7950.0, None, math.pi / 2),
    (SOLAR, 300.0, 8350.0, None, math.pi / 2),
    (SOLAR, 300.0, 8650.0, None, math.pi / 2),
]


def _court(pr, gd, world):
    """(x, y, turn) of the Royal Hawaiian in the city (not a hotel world's copy)."""
    key = next((k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'STAT'
                and _edid(r) == COURT_EDID), None)
    city = shipplace.world_cells(gd, world)
    for ck in city:
        c = pr.cells.get(ck)
        for r in (c or {}).get('refs', {}).values():
            if r.get('base') == key and not r.get('removed') and r.get('p'):
                return r['p'][0], r['p'][1], r['p'][5]
    return None


def _edid(rec):
    import recordio
    return recordio.field(rec, 'EDID')


def _strip(roads):
    """The avenue's strip as pieces of line: [(x0, y0, x1, y1)]."""
    out = []
    for name, kind, pts in roads:
        if name == STRIP_ROAD and kind == STRIP_KIND:
            out += [(a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:])]
    return out


class Seats:
    def __init__(self, gd, pr, world, side, cat):
        self.B = ridgeplaces.Builder(gd, pr, world, side, cat)
        found = shipinside._forms(gd, NAMES)
        self.B.key_of.update({e: gd.key(f) for e, f in found.items()})
        self.B.rep['missing'] |= NAMES - set(found)
        self.gd, self.pr, self.world = gd, pr, world
        self.rep = {}
        self._own_bounds()
        clear = self.B.clearable

        def clearable(ck, rk):
            return clear(ck, rk) or self._name(ck, rk).startswith(('FOLabBeach', 'FOLabWaikikiPalm', 'FOLabPlant'))
        self.B.clearable = clearable

    def _own_bounds(self):
        """townbuild.World knows the game's things only: the mod's own models (hotels, landmarks, the ship) go in by their
        records' OBND, so nothing is stood inside one. The court has its own outline (COURT_SOLID)."""
        B = self.B
        boxes = {}
        for k, r in self.pr.records.items():
            if not k.startswith('+') or r.get('type') != 'STAT' or _edid(r) in (COURT_EDID, NAT_EDID):
                continue
            sub = next((q for q in r.get('subs', ()) if q['tag'] == 'OBND' and q.get('kind') == 'struct'), None)
            if sub:
                boxes[k] = [f['value'] for f in sub['fields']]
        n = 0
        for ck in shipplace.world_cells(self.gd, self.world):
            for rk, ref in self.pr.cells.get(ck, {}).get('refs', {}).items():
                b = boxes.get(ref.get('base'))
                if not b or ref.get('removed') or not ref.get('p'):
                    continue
                sc = ref.get('s', 1.0)
                p = ref['p']
                fp = townbuild._foot([v * sc for v in b], p[5], p)
                big = max(b[3] - b[0], b[4] - b[1]) * sc >= townbuild.CLEAR_BELOW
                item = (ck, rk, fp, big, True)
                xs, ys = [q[0] for q in fp], [q[1] for q in fp]
                for bx in range(int(min(xs) // 1024), int(max(xs) // 1024) + 1):
                    for by in range(int(min(ys) // 1024), int(max(ys) // 1024) + 1):
                        B.w.bucket[(bx, by)].append(item)
                n += 1
        self.rep['own_models_known'] = n

    def _name(self, ck, rk):
        import natcompound
        r = self.pr.cells.get(ck, {}).get('refs', {}).get(rk)
        return natcompound._named(self.gd, self.pr, r['base']) if r and r.get('base') else ''

    # ----- pieces -----

    def raw(self, edid, x, y, z, yaw, cell=None):
        """A thing at exactly x, y, z (on the ship, a light): no ground or room check."""
        B = self.B
        ck = cell or B.w.cell_at(x, y)
        if ck is None or edid not in B.key_of:
            return False
        B.ops.append({'op': 'add', 'cell': ck, 'base': B.key_of[edid], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0,
                      round(yaw % math.tau, 4)], 's': 1})
        B.cells.add(ck)
        return True

    def post(self, pl, x, y, face):
        """A sandbag guard post: three lengths in a U, open at the back, facing `face` (radians, the way it looks)."""
        fx, fy = math.sin(face), math.cos(face)              # (ahead)
        rx, ry = math.cos(face), -math.sin(face)             # (to its right)
        n = 0
        for ax, sy, turn in ((0.0, 160.0, face + math.pi / 2), (-170.0, 0.0, face), (170.0, 0.0, face)):
            px, py = x + fx * sy + rx * ax, y + fy * sy + ry * ax
            n += pl.put(SANDBAG, px, py, turn, r=60.0)
        return n

    # ----- the court -----

    def court(self, roads):
        """In the hotel's own frame (town side +y): the block and the wings with their lawn to the sea, the carriage porch
        to the avenue (historicset.royal_hawaiian). Its carriage porch fronts on the avenue, so the court's front is the
        frontage either side of it."""
        B, rep = self.B, {}
        at = _court(self.pr, self.gd, self.world)
        if not at:
            self.rep['court'] = 'the Royal Hawaiian is not in this world'
            return
        cx, cy, turn = at

        def W(lx, ly):
            return shipplace.to_world(cx, cy, turn, lx, ly)
        for x0, y0, x1, y1 in COURT_SOLID:
            fp = [W(x0, y0), W(x1, y0), W(x1, y1), W(x0, y1)]
            B.w.add(fp, 'court', 'court')
        pl = ridgeplaces.Place(B, 'court', cx, cy, 0.0)

        def first(edid, spots, yaw, r=None):
            for lx, ly in spots:
                x, y = W(lx, ly)
                if pl.put(edid, x, y, yaw, r=r):
                    return [round(lx), round(ly)]
            return False
        # torches along the frontage either side of the porch
        torches = 0
        for sd in (-1, 1):
            lx = 800.0
            while lx <= 2000.0:
                torches += bool(first(TORCH, [(sd * lx, ly) for ly in (760.0, 680.0, 840.0, 600.0)], 0.0, r=50.0))
                lx += 300.0
        # guard posts either side of the porch's front, looking out at the avenue
        posts = 0
        for sd in (-1, 1):
            for ly in (1150.0, 1080.0, 1000.0, 920.0):
                x, y = W(sd * 760.0, ly)
                got = self.post(pl, x, y, turn)
                posts += got
                if got:
                    break
        rep.update(torches=torches, post_pieces=posts)
        # a guard tower at a front corner, beside an end of the block
        rep['tower'] = first(TOWER, [(sd * (2550.0 + 100.0 * k), ly) for k in range(12) for ly in (500.0, 200.0, 800.0)
                                     for sd in (1, -1)], turn + math.pi)
        # the tribute yard beyond the other end, or this one
        rep['yard'] = False
        for k in range(14):
            for sd in ((-1, 1) if not rep['tower'] or rep['tower'][0] > 0 else (1, -1)):
                for ly in (0.0, -500.0, 500.0):
                    lx = sd * (2100.0 + YARD + 150.0 + 120.0 * k)
                    if rep['yard'] is False:
                        rep['yard'] = self.yard(pl, W, lx, ly, turn)
        self.rep['court'] = rep

    def yard(self, pl, W, lx0, ly0, turn):
        """Goods in rows round an open middle, a square YARD each way of (lx0, ly0) in the hotel's frame."""
        x, y = W(lx0, ly0)
        if not pl.free(x, y, YARD):
            return False
        pl.taken.append((x, y, 1.0))
        n = 0
        for j, (a, b) in enumerate((a, b) for a in (-340.0, -120.0, 120.0, 340.0) for b in (-340.0, 340.0)):
            gx, gy = W(lx0 + a, ly0 + b)
            e = GOODS[j % len(GOODS)]
            if pl.put(e, gx, gy, turn, r=70.0):
                n += 1
                if e in ('CrateGenericNV', 'NVWaterCrateSqr01'):            # (stacked two high)
                    o = self.B.ops[-1]
                    self.raw(e, o['p'][0], o['p'][1], o['p'][2] + 156.0, turn + 0.1, o['cell'])
                    n += 1
        for a in (-200.0, 0.0, 200.0):
            gx, gy = W(lx0 + a, ly0 - 470.0)
            n += pl.put('Barrel03static', gx, gy, 0.0, r=35.0)
        return {'at': [round(lx0), round(ly0)], 'goods': n}

    # ----- the strip -----

    def strip(self, roads):
        B = self.B
        pl = ridgeplaces.Place(B, 'strip', 0.0, 0.0, 0.0)
        segs = _strip(roads)
        lamps, missed, side, carry = 0, 0, 1, 0.0
        stood = []
        for x0, y0, x1, y1 in segs:
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 1:
                continue
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            s = LAMP_EVERY - carry if carry else LAMP_EVERY / 2
            while s < L:
                x, y = x0 + ux * s, y0 + uy * s
                if all(math.hypot(x - a, y - b) > LAMP_EVERY * 0.6 for a, b in stood):
                    ok = False
                    for sd in (side, -side):
                        nx, ny = -uy * sd, ux * sd
                        off = LAMP_OFF[0]
                        while off <= LAMP_OFF[1] and not ok:
                            lx, ly = x + nx * off, y + ny * off
                            if pl.put(LAMP, lx, ly, math.atan2(-uy, ux), r=60.0):
                                o = B.ops[-1]
                                self.raw(LAMP_LIGHT, lx, ly, o['p'][2] + LAMP_LIGHT_Z, 0.0, o['cell'])
                                lamps += 1
                                ok = True
                            off += 60.0
                    missed += not ok
                    stood.append((x, y))
                    side = -side
                s += LAMP_EVERY
            carry = L - (s - LAMP_EVERY)
        self.rep['strip'] = {'lamps': lamps, 'no_room': missed}

    # ----- the ship and the way aboard -----

    def ship(self):
        B, rep = self.B, {}
        here = shipplace.standing(self.pr, self.gd, self.world)
        if not here:
            self.rep['ship'] = 'the Missouri is not in this world'
            return
        _ck, _rk, p = here
        sx, sy, sz, turn = p[0], p[1], p[2], p[5]

        def world(lx, ly):
            return shipplace.to_world(sx, sy, turn, lx, ly)
        n = 0
        for e, lx, ly, over, lt in SHIP_THINGS:
            box = B.box(e)
            if box is None:
                continue
            if abs(lx) + max(box[3] - box[0], box[4] - box[1]) / 2 > battleship.half_beam(ly) - 120:
                rep.setdefault('off_her', []).append(e)
                continue
            x, y = world(lx, ly)
            n += self.raw(e, x, y, sz + battleship.deck_z(ly) + (over or 0.0) - box[2], turn + lt)
        # the searchlight on the first funnel's port platform, pointed out to sea, its light ahead of it
        Z3 = battleship.deck_z(-2150) + 270 + 260 + 250
        x, y = world(400.0, battleship.FUNNEL1)
        n += self.raw(SEARCHLIGHT, x, y, sz + Z3 + 616 + 70, turn - math.pi / 2)
        x, y = world(560.0, battleship.FUNNEL1)
        n += self.raw(SEARCH_LIGHT, x, y, sz + Z3 + 616 + 150, 0.0)
        # sandbag posts either side of the gangway's inner end (her starboard side, -x), facing the gap
        gy = battleship.SPOTS['gangway_y']
        hb = battleship.half_beam(gy)
        dz = sz + battleship.deck_z(gy)
        for side in (-1, 1):
            for ax, ay, t in ((-hb + 360.0, gy + side * 420.0, 0.0), (-hb + 520.0, gy + side * 420.0 - side * 170.0, math.pi / 2)):
                x, y = world(ax, ay)
                n += self.raw(SANDBAG, x, y, dz - 1.0, turn + t)
        rep['on_her'] = n
        # at the street side of the Natatorium's arch, and the pen in its park
        nat = shipway.natatorium(self.gd, self.pr, self.world)
        if nat:
            q = nat[2]
            pose = (q[0], q[1], q[2], q[5])
            for x0, y0, x1, y1 in NAT_SOLID:
                B.w.add([shipway.world_of(pose, a, b) for a, b in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))], 'natatorium', 'natatorium')
            pl = ridgeplaces.Place(B, 'natatorium', q[0], q[1], 0.0)
            face = q[5]                                          # (looking out to the park: the Natatorium's +y)
            posts = 0
            for side in (-1, 1):
                x, y = shipway.world_of(pose, side * 560.0, 1000.0)
                posts += self.post(pl, x, y, face)
            rep['arch_post_pieces'] = posts
            rep['cages'] = False
            spots = sorted(((lx, ly) for lx in range(-5000, 5001, 250) for ly in range(1300, 6001, 250)),
                           key=lambda s_: math.hypot(s_[0], s_[1] - 1000.0))
            half = CAGE_STEP * len(CAGES) / 2
            for lx, ly in spots:
                x, y = shipway.world_of(pose, lx, ly)
                if not pl.free(x, y, half + 60.0):
                    continue
                n = 0
                for k, e in enumerate(CAGES):
                    cx_, cy_ = shipway.world_of(pose, lx - half + CAGE_STEP * (k + 0.5), ly)
                    n += pl.put(e, cx_, cy_, q[5] + math.pi, r=40.0, check=False)
                rep['cages'] = [round(x), round(y), lx, ly, n]
                break
        self.rep['ship'] = rep


def ops(gd, pr, world, side, roads, cat=None):
    """(ops, report, cells). roads: [(name, kind, [(x, y)...])] from the street map."""
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    S = Seats(gd, pr, world, side, cat)
    S.court(roads)
    S.strip(roads)
    S.ship()
    B = S.B
    rep = dict(S.rep, missing=sorted(B.rep['missing']), removed=sum(1 for o in B.ops if o['op'] == 'remove'),
               added=sum(1 for o in B.ops if o['op'] == 'add'))
    return __import__('guardtower').instead(gd, pr, B.ops), rep, sorted(B.cells)     # (FOLab's guard tower for the game's)
