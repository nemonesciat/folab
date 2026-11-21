"""Things to find in a map-made world: locked chests and safes, guns and explosives, food and medicine, put where they make
sense and paying more where they are harder to get at (docs/waikiki-loot-plan.md, agreed by the user 20 Nov 2026).

Only the game's own containers (FalloutNV.esm), whose contents are the game's levelled lists; the game already grades
many of them (explosives crates tier 1 to 4, food sacks to crates, first aid kits to locked ones, gun cabinets, safes),
and those grades with the lock are how a harder spot pays more.

How hard a spot is (`band`: 0 easy, 1 middling, 2 hard): by how many cells it lies from the new game's start, as
thirds of the way to the world's farthest cell (`BAND_SHARE`), one band up for a spot someone holds or that is high or hard to reach, or behind the wall
or in the north's radiation. Nothing within `START_CLEAR` of the start.

Outside, every find stands against something already there (an anchor: a tent, a shack, a crate, a wreck, a roof camp's
crate, a wall), its back to it, never in the open: `Spots` gathers the anchors, `Seat` puts a find on what is really under
it (the land, and every placed thing's collision: roofs, decks, planking) and refuses a spot where the surface isn't
level enough, something solid stands in the find's way, it would sit on a road, in water or a doorway. Inside, the
places' rooms are the game's own and already furnished: their empty containers become the full ones of the same model,
some are locked by band, and a find goes against a wall where the navmesh ends (`inside_ops`), off any doorway.

Keys (`KEYED`): the hardest safes need one, put on the lid of another find of the same spot (a lid with a key on it opens
freely); each key a KEYM of the mod's own copied from the game's (`key_record`), named after where it is.

    ops(gd, pr, world, side, cat, seed)        (ops, report): all of it, nothing applied
    new_ways(gd, pr, world, cat, n)            (ops, report): ways up onto roofs that have none (rooftops.plan)"""
import collections
import math
import random
import re

import recordio
import roadgen
import settleup
import townbuild

START_CLEAR = 3000.0
BAND_SHARE = (1 / 3.0, 2 / 3.0)   # (of the way from the start to the world's farthest cell: easy, middling, hard. Not worldlife's
#                                  zones: from Waikiki's start at Hanauma Bay those put the whole city past the last one)
# what goes in a find of each kind, by band: [(editor ID, weight, (lowest lock, highest lock) or None)]
KINDS = {
    'ammo': ([('LootAmmoBoxGenericNV', 1, None)],
             [('LootAmmoBoxGenericNV', 2, None), ('LootAmmoBoxGenericLockNV', 1, (25, 50))],
             [('LootAmmoBoxGenericLockNV', 2, (50, 75)), ('LootAmmoBox5mmBigLock', 1, (50, 75))]),
    'military': ([('Footlocker01MilitaryNV', 1, None)],
                 [('Footlocker01MilitaryNV', 1, (25, 50))],
                 [('Footlocker01MilitaryNV', 2, (50, 75)), ('LootGunCabinetNVGunsLocked', 1, (50, 100))]),
    'guns': ([('Footlocker01MilitaryNV', 1, None)],
             [('LootGunCabinetNVGunsLocked', 1, (25, 50))],
             [('LootGunCabinetNVGunsLocked', 1, (50, 100))]),
    'explosives': ([('LootAmmoBoxGenericNV', 1, None)],
                   [('VLootExplosivesNVCrateXXXTier1Workshop', 2, None), ('VLootExplosivesNVCrateXXXTier2Workshop', 1, (25, 50))],
                   [('VLootExplosivesNVCrateXXXTier3Workshop', 2, (50, 75)), ('VLootExplosivesNVCrateXXXTier4WorkshopHi', 1, (75, 100))]),
    'medicine': ([('Footlocker01Hospital', 1, None)],
                 [('Footlocker01Hospital', 2, None), ('Footlocker01Drugs', 1, (25, 50))],
                 [('Footlocker01Drugs', 2, (50, 75)), ('Footlocker01Hospital', 1, (50, 75))]),
    'food': ([('VLootFoodSackGen06', 1, None)],
             [('VLootFoodWoodenCrateGen02', 1, None), ('VLootFoodSSCrateGen06', 1, None)],
             [('VLootFoodSSCrateGen08', 1, None), ('VLootFoodWoodenCrateGen05', 1, (25, 50))]),
    'bag': ([('NVDuffleBagRandomLoot', 2, None), ('SuitCase02', 1, None)],
            [('NVDuffleBagRandomLoot', 2, None), ('Footlocker01HouseholdNV', 1, (0, 25))],
            [('NVDuffleBagRandomLoot', 1, None), ('Footlocker01HouseholdNV', 1, (25, 50))]),
    'tools': ([('VLootToolsToolboxGen05', 1, None)], [('VLootToolsToolboxGen07', 1, None)], [('VLootStashToolboxAbandonedHi', 1, (25, 50))]),
    'safe': ([('GenericSafe01', 1, (25, 25))], [('GenericSafe01', 1, (50, 50))], [('GenericSafe01', 1, (75, 100))]),
}
# what each kind of spot gets: (kinds to choose from, in order, how many by band)
RECIPES = {
    'raiders': (['ammo', 'military', 'explosives', 'guns'], (1, 2, 3)),
    'roadblock': (['ammo', 'explosives'], (1, 1, 2)),
    'camp': (['bag', 'food'], (1, 1, 2)),
    'refuge': (['food', 'medicine', 'bag'], (1, 2, 2)),
    'crash': (['bag', 'medicine'], (1, 1, 2)),
    'beach': (['bag', 'food'], (1, 1, 1)),
    'wreck': (['bag'], (1, 1, 1)),
    'roof': (['ammo', 'bag', 'military', 'food'], (1, 1, 2)),
    'high': (['military', 'ammo', 'food', 'medicine'], (2, 2, 3)),
    'cairn': (['bag', 'food', 'medicine'], (1, 1, 1)),
    'ruin': (['military', 'explosives', 'medicine', 'ammo'], (1, 1, 2)),
    'post': (['ammo', 'military', 'food', 'explosives'], (2, 2, 3)),
    'armoury': (['guns', 'explosives', 'ammo', 'guns', 'explosives', 'ammo'], (4, 5, 6)),
    'tribute': (['food', 'food', 'medicine', 'food'], (3, 3, 4)),
    'boats': (['ammo', 'bag', 'explosives', 'food'], (2, 3, 4)),
    'waystation': (['medicine', 'ammo', 'food'], (2, 2, 3)),
}
# held or high places by their map marker's name: (spot kind, reach, band up, keyed safe)
PLACES = {
    'Kahala Reef': ('armoury', 2600.0, 1, True),
    'The Royal Hawaiian': ('tribute', 2400.0, 1, True),
    'Koko Marina': ('boats', 2600.0, 1, True),
    'Waystation': ('waystation', 1600.0, 1, True),
    'Alewa Fort': ('high', 2200.0, 1, True),
    'The Tanks': ('high', 1600.0, 1, True),
    'The Holdouts': ('high', 1600.0, 1, True),
    'The Heights': ('high', 1600.0, 1, True),
    'Loa Gate': ('high', 1600.0, 1, True),
    "Watcher's Hut": ('high', 1200.0, 1, False),
    'Radar Dome': ('high', 1400.0, 1, False),
    "Crow's Nest": ('high', 1200.0, 1, False),
    'Pacific Heights Beacon': ('high', 1200.0, 1, False),
}
SCENE_REACH = 900.0
WRECK_SHARE = 1 / 12.0
ROOF_UP = 200.0                 # (an anchor this far over the land is on a roof or a deck)
FREEWAY_UP = 1000.0
CAIRN_EVERY = 4                 # (a stash behind one cairn in this many)
RUINS_BEHIND = 25               # (finds against ruins behind the wall)
DOOR_CLEAR = 260.0              # (no find this near a door)
TALL = 600.0                    # (an anchor taller than this: the ground beside it is the level, not its underside)
FOOT_MOST = 60.0                # (things this big or bigger are kept out of a find's footprint)
APART = 90.0                    # (finds this far apart, edge to edge)
LEVEL = 8.0                     # (a find on a deck or floor: its supports agree within this)
TILT_MOST = 0.22                # (on the land it leans with the slope, no more than this)
HANG = 6.0                      # (and no corner more than this over the land)
SEATED = 8.0                    # (as it stands, no corner of its underside hangs or is sunk more than this)
# what a find may stand against, by words of the anchor's editor ID; and what never holds one
ANCHOR = re.compile(r'tent|shack|crate|barrel|sandbag|table|leanto|bedroll|mattress|campfire|fire|car0|hulk|truck|wreck|junkwall|'
                    r'cage|trailer|footlocker|milkcrate|shanty|lookout|woodcart|bus0|pallet', re.I)
WRECKS = re.compile(r'car0\dhulk|hulk|truck|wreck|woodcart|bus0', re.I)
CAMP_THINGS = re.compile(r'crate|sandbag|barrel|leanto|milkcrate|mattress|bedroll', re.I)
NOT_ON = re.compile(r'road|highway|sidewalk|curb|street|bridge|ramp|gangplank|ladder|stair', re.I)
CAIRN = re.compile(r'rockstack|cairn', re.I)
KEY_FROM = 'Vault101OverseersKey'
SETTLED = re.compile(r'^FOLabSettler|^settler', re.I)   # (the settlers' own pieces: their land is left alone)
SETTLED_CLEAR = 2500.0


def _base_type(gd, pr, key):
    if key.startswith('+'):
        return (pr.records.get(key) or {}).get('type')
    try:
        return gd.describe(gd.from_key(key))[0]
    except (ValueError, KeyError):
        return None


class Solids(settleup._Solids):
    """settleup's solid triangles, and what each ref is made of (bkey), so a surface can be told for a road's or a deck's."""

    def __init__(self, gd, pr):
        super().__init__(gd, pr, set())
        self.bkey = {}

    def _cell(self, ck):
        if ck in self.cells:
            return
        import navbuild
        try:
            rows = navbuild.place_refs(self.gd, self.pr, ck)
        except Exception:
            rows = []
        for r in rows:
            self.bkey[r['ref']] = r.get('bkey')
        real = navbuild.place_refs
        navbuild.place_refs = lambda *_a, **_k: rows        # (read once: the parent files the same rows' triangles)
        try:
            super()._cell(ck)
        finally:
            navbuild.place_refs = real


def _turn(x, y, rz):
    """(x, y) of a thing's own frame turned by its z turn into the world's (the game's: clockwise looking down)."""
    c, s = math.cos(rz), math.sin(rz)
    return x * c + y * s, -x * s + y * c


def _face(dx, dy, front=(0.0, -1.0)):
    """The z turn that brings a thing's front (`front`, in its own frame) to face along (dx, dy)."""
    return math.atan2(front[1], front[0]) - math.atan2(dy, dx)


def front_of(gd, model):
    """Which way a model's front looks in its own frame: the side with handles, latches or a dial (most of its detail at its
    outer edge, at middle height), as a unit along x or y; a model with no such side shows a long side (+y if as long as
    wide). The game's own containers face every way: a footlocker's latch is at -x, a gun cabinet's doors at -y, a safe's
    dial at +x."""
    import nif
    try:
        sh = nif.mesh_from_nif(gd.read_file('meshes\\' + model.lstrip('\\')))
    except Exception:
        sh = []
    pts = [(s['p'][k], s['p'][k + 1], s['p'][k + 2]) for s in sh for k in range(0, len(s['p']) - 2, 3)]
    if not pts:
        return (0.0, 1.0)
    xs, ys, zs = zip(*pts)
    z0, z1 = min(zs), max(zs)
    mid = [q for q in pts if abs(q[2] - (z0 + z1) / 2) < (z1 - z0) * 0.35]
    count = {}
    for axis, lo, hi in ((0, min(xs), max(xs)), (1, min(ys), max(ys))):
        edge = 0.06 * (hi - lo)
        count[(axis, -1)] = sum(1 for q in mid if q[axis] < lo + edge)
        count[(axis, 1)] = sum(1 for q in mid if q[axis] > hi - edge)
    (axis, sign), most = max(count.items(), key=lambda kv: kv[1])
    if most >= 24 and most >= 2 * count[(axis, -sign)]:
        return (float(sign), 0.0) if axis == 0 else (0.0, float(sign))
    return (1.0, 0.0) if (max(ys) - min(ys)) > (max(xs) - min(xs)) else (0.0, 1.0)


def back_reach(box, front):
    """How far a thing of these bounds reaches behind its origin, away from its front."""
    return max(-(x * front[0] + y * front[1]) for x in (box[0], box[3]) for y in (box[1], box[4]))


class Anchors:
    """The world's placed things worth standing a find against, filed by 1024 squares: (x, y, z, rz, s, box, edid, ck, rk)."""

    def __init__(self, gd, pr, world):
        self.gd, self.pr = gd, pr
        self.grid = gd.grid(world)
        self.edids, self.boxes = {}, {}
        self.bucket = collections.defaultdict(list)
        self.doors = collections.defaultdict(list)
        self.settled = collections.defaultdict(list)
        self.foot = collections.defaultdict(list)
        self.all = []
        keys = {gd.key(c) for c in self.grid.values()}
        for ck in keys:
            for rk, r in (self.pr.cells.get(ck) or {}).get('refs', {}).items():
                b, p = r.get('base'), r.get('p')
                if not b or not p or r.get('removed'):
                    continue
                e = self.edid(b)
                box = self.box(b)
                if box:
                    s = float(r.get('s') or 1.0)
                    if max(box[3] - box[0], box[4] - box[1]) * s >= FOOT_MOST:
                        fp = townbuild._foot([v * s for v in box], p[5] if len(p) > 5 else 0.0, p)
                        item = (ck, rk, fp, p[2] + box[2] * s, p[2] + box[5] * s)
                        xs, ys = [q[0] for q in fp], [q[1] for q in fp]
                        for bx in range(int(min(xs) // 1024), int(max(xs) // 1024) + 1):
                            for by in range(int(min(ys) // 1024), int(max(ys) // 1024) + 1):
                                self.foot[(bx, by)].append(item)
                if r.get('tel') or self.kind(b) == 'DOOR':
                    self.doors[(int(p[0] // 1024), int(p[1] // 1024))].append((p[0], p[1]))
                    continue
                if SETTLED.search(e):
                    self.settled[(int(p[0] // 1024), int(p[1] // 1024))].append((p[0], p[1]))
                if not (ANCHOR.search(e) or CAIRN.search(e)):
                    continue
                box = self.box(b)
                if not box:
                    continue
                a = (p[0], p[1], p[2], p[5] if len(p) > 5 else 0.0, float(r.get('s') or 1.0), box, e, ck, rk, abs(p[3]) + abs(p[4]))
                self.bucket[(int(p[0] // 1024), int(p[1] // 1024))].append(a)
                self.all.append(a)

    def edid(self, key):
        if key not in self.edids:
            self.edids[key] = settleup._edid(self.gd, self.pr, key)
        return self.edids[key]

    def kind(self, key):
        return _base_type(self.gd, self.pr, key)

    def feet(self, fp):
        """Footprints round fp: (ck, rk, footprint, underside z, top z)."""
        xs, ys = [q[0] for q in fp], [q[1] for q in fp]
        out, seen = [], set()
        for bx in range(int(min(xs) // 1024), int(max(xs) // 1024) + 1):
            for by in range(int(min(ys) // 1024), int(max(ys) // 1024) + 1):
                for it in self.foot.get((bx, by), ()):
                    if it[1] not in seen:
                        seen.add(it[1])
                        out.append(it)
        return out

    def box(self, key):
        if key not in self.boxes:
            o = townbuild.obnd(self.gd, key)
            if o is None and key.startswith('+'):
                rec = self.pr.records.get(key) or {}
                sub = next((q for q in rec.get('subs', ()) if q.get('tag') == 'OBND' and q.get('kind') == 'struct'), None)
                o = [f['value'] for f in sub['fields']] if sub else None
            self.boxes[key] = o
        return self.boxes[key]

    def near(self, x, y, r, table=None):
        table = self.bucket if table is None else table
        out = []
        for bx in range(int((x - r) // 1024), int((x + r) // 1024) + 1):
            for by in range(int((y - r) // 1024), int((y + r) // 1024) + 1):
                for a in table.get((bx, by), ()):
                    if math.hypot(a[0] - x, a[1] - y) <= r:
                        out.append(a)
        return out

    def near_door(self, x, y, r=DOOR_CLEAR):
        return bool(self.near(x, y, r, self.doors))

    def near_settled(self, x, y):
        return bool(self.near(x, y, SETTLED_CLEAR, self.settled))


class Seat:
    """Where a find of a given size rests at a spot, on the land or on what stands there, or None."""

    def __init__(self, gd, pr, world, solids=None, ground=True):
        self.gd, self.pr = gd, pr
        self.grid = gd.grid(world) if world is not None else {}
        self.by_xy = {xy: gd.key(c) for xy, c in self.grid.items()}
        self.G = roadgen.Ground(gd, pr, world) if world is not None and ground else None
        self.solids = solids or Solids(gd, pr)
        self.edids = {}
        self.feet = None                                # (Anchors' footprints, to keep off: set by ops())
        self.taken = collections.defaultdict(list)      # ((x, y, r) of finds already put)

    def load(self, x, y):
        k = (int(x // 4096), int(y // 4096))
        self.solids.load_round([self.by_xy[(k[0] + dx, k[1] + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (k[0] + dx, k[1] + dy) in self.by_xy])

    def ref_edid(self, ref):
        """The editor ID of what a solid surface belongs to (a ref key), as far as it can be told."""
        if ref not in self.edids:
            b = self.solids.bkey.get(ref)
            self.edids[ref] = settleup._edid(self.gd, self.pr, b) if b else ''
        return self.edids[ref]

    def free(self, x, y, r):
        for bx in range(int((x - r - 300) // 512), int((x + r + 300) // 512) + 1):
            for by in range(int((y - r - 300) // 512), int((y + r + 300) // 512) + 1):
                for a, b, c in self.taken.get((bx, by), ()):
                    if math.hypot(a - x, b - y) < r + c + APART:
                        return False
        return True

    def take(self, x, y, r):
        self.taken[(int(x // 512), int(y // 512))].append((x, y, r))

    def at(self, x, y, rz, box, level, outside=True):
        """[x, y, z, rx, ry, rz] for a find of bounds `box` turned rz with its middle at (x, y), resting on the highest surface
        not over level + 48 under it, or None."""
        hx, hy = (box[3] - box[0]) / 2 * 0.85, (box[4] - box[1]) / 2 * 0.85
        mx, my = (box[3] + box[0]) / 2, (box[4] + box[1]) / 2
        tall = box[5] - box[2]
        pts, local = [], []
        for fx in (-1, 0, 1):
            for fy in (-1, 0, 1):
                lx, ly = mx + fx * hx, my + fy * hy
                wx, wy = _turn(lx, ly, rz)
                pts.append((x + wx, y + wy))
                local.append((lx, ly))
        sup, on_land, under = [], [], set()
        for px, py in pts:
            best, land, ref = None, False, None
            g = self.G.at(px, py) if (self.G and outside) else None
            if g is not None and g <= level + 48:
                best, land = g, True
            for z, r in self.solids.tops(px, py):
                if z <= level + 48 and (best is None or z > best):
                    best, land, ref = z, False, r
            if best is None:
                return None
            if ref is not None and NOT_ON.search(self.ref_edid(ref)):
                return None
            if ref is not None:
                under.add(ref)
            sup.append(best)
            on_land.append(land)
        if outside and self.G:
            w = self.G.water(x, y)
            if (w is not None and max(sup) < w + 4) or min(sup) < 4:
                return None
        rest = max(sup)
        if all(on_land):
            # (a plane through the land under it: it leans with the slope, its middle on the land)
            n = len(local)
            sx = sum(l[0] for l in local) / n
            sy = sum(l[1] for l in local) / n
            sz = sum(sup) / n
            vxx = sum((l[0] - sx) ** 2 for l in local) or 1.0
            vyy = sum((l[1] - sy) ** 2 for l in local) or 1.0
            ax = sum((l[0] - sx) * (z - sz) for l, z in zip(local, sup)) / vxx
            ay = sum((l[1] - sy) * (z - sz) for l, z in zip(local, sup)) / vyy
            if abs(ax) > math.tan(TILT_MOST) or abs(ay) > math.tan(TILT_MOST):
                return None
            fit = [sz + ax * (l[0] - sx) + ay * (l[1] - sy) for l in local]
            if max(f - z for f, z in zip(fit, sup)) > HANG or max(z - f for f, z in zip(fit, sup)) > HANG * 2:
                return None
            # (a turn about y by +a lifts its +x end; about x by +b drops its +y end: navgen._turn)
            ry, rx = math.atan(ax), -math.atan(ay)
            zc = sz + ax * (mx - sx) + ay * (my - sy)
            z = zc - box[2] - 1.0
        else:
            if max(sup) - min(sup) > LEVEL:
                return None
            rx = ry = 0.0
            z = rest - box[2]
        # nothing solid where it stands: no surface inside its height, no other thing's footprint reaching up into it (walls
        # seen from above are lines, so a building is known by its footprint, not its collision)
        for (px, py) in pts:
            for zz, _r in self.solids.tops(px, py):
                if rest + 6 < zz < rest + tall + 4:
                    return None
        # last, as it will stand: each corner of its underside on what is under it, neither hanging nor sunk
        import navgen
        m = navgen._turn(rx, ry, rz)
        for fx in (0.15, 0.85):
            for fy in (0.15, 0.85):
                lx, ly, lz = box[0] + (box[3] - box[0]) * fx, box[1] + (box[4] - box[1]) * fy, box[2]
                cx = x + m[0][0] * lx + m[0][1] * ly + m[0][2] * lz
                cy = y + m[1][0] * lx + m[1][1] * ly + m[1][2] * lz
                cz = z + m[2][0] * lx + m[2][1] * ly + m[2][2] * lz
                below = [zz for zz, _r in self.solids.tops(cx, cy) if zz <= cz + 30]
                g = self.G.at(cx, cy) if (self.G and outside) else None
                if g is not None and g <= cz + 30:
                    below.append(g)
                if not below or abs(cz - max(below)) > SEATED:
                    return None
        if self.feet is not None:
            fp = [pts[0], pts[2], pts[8], pts[6]]
            for ck, rk, ofp, z0, z1 in self.feet(fp):
                if rk in under or z1 < rest + 10 or z0 > rest + tall:
                    continue
                if townbuild.overlap(fp, ofp):
                    return None
        return [round(x, 1), round(y, 1), round(z, 1), round(rx, 4), round(ry, 4), round(rz % math.tau, 4)]


class Plan:
    """The finds as they are worked out: ops, keys, counts."""

    def __init__(self, gd, pr, world, seed):
        self.gd, self.pr, self.world = gd, pr, world
        self.rng = random.Random(seed * 7919 + 13)
        self.grid = gd.grid(world)
        self.forms = {}
        want = {e for rows in KINDS.values() for band in rows for e, _w, _l in band} | {KEY_FROM}
        for f, (_i, r) in gd.forms.items():
            e = gd.edid(f)
            if e in want and (e not in self.forms or (f >> 24) == 0) and r.tag in ('CONT', 'KEYM'):
                self.forms[e] = f
        self.missing = sorted(want - set(self.forms))
        self.ops, self.keys = [], []
        self.report = collections.Counter()
        self.where = collections.defaultdict(collections.Counter)
        self.boxes, self.fronts = {}, {}

    def key_of(self, edid):
        return self.gd.key(self.forms[edid])

    def box(self, edid):
        if edid not in self.boxes:
            self.boxes[edid] = townbuild.obnd(self.gd, self.key_of(edid))
        return self.boxes[edid]

    def front(self, edid):
        if edid not in self.fronts:
            m = self.gd.fields(self.forms[edid]).get('MODL') or b''
            self.fronts[edid] = front_of(self.gd, m.rstrip(b'\0').decode('latin-1'))
        return self.fronts[edid]

    def choose(self, kind, band):
        rows = [r for r in KINDS[kind][band] if r[0] in self.forms]
        if not rows:
            return None, None
        total = sum(w for _e, w, _l in rows)
        t = self.rng.uniform(0, total)
        for e, w, lk in rows:
            t -= w
            if t <= 0:
                break
        lock = None
        if lk:
            lock = self.rng.choice([v for v in (0, 25, 50, 75, 100) if lk[0] <= v <= lk[1]])
        return e, lock

    def add(self, ck, edid, p, lock=None, key=None, spot='', band=0, name=None):
        op = {'op': 'add', 'cell': ck, 'base': self.key_of(edid), 'p': p, 's': 1.0}
        if lock is not None or key:
            op['extra'] = {'props': {'lock': {'level': 255 if key else lock, 'key': key or '', 'leveled': False}}}
            self.report['locked'] += 1
        if name:
            op['name'] = name
        self.ops.append(op)
        self.report['finds'] += 1
        self.where[spot]['b%d' % band] += 1
        self.report['kind ' + edid] += 1
        return op


def key_record(gd, edid, name):
    """A key of the mod's own, copied from the game's `KEY_FROM` (recordio's form)."""
    f = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'KEYM' and f >> 24 == 0 and gd.edid(f) == KEY_FROM)
    rec = recordio.load(gd, f)
    recordio.set_field(rec, 'EDID', edid)
    recordio.set_field(rec, 'FULL', name)
    rec['src'] = rec.get('src') or ''
    return rec


def _markers(gd, pr, world):
    """{name: (x, y, z)} of the world's map markers the mod placed."""
    out = {}
    for c in gd.grid(world).values():
        for rk, r in (pr.cells.get(gd.key(c)) or {}).get('refs', {}).items():
            m = r.get('marker')
            if m and r.get('p') and m.get('name'):
                out.setdefault(m['name'], tuple(r['p'][:3]))
    return out


class Outside:
    """The finds outside: against anchors at each kind of spot."""

    def __init__(self, P, A, S, start, wall_x=None, north=None, reach=None):
        self.P, self.A, self.S, self.start = P, A, S, start
        self.wall_x, self.north = wall_x, north
        self.reach = reach or 1.0
        self.cells = set()

    def band(self, x, y, up=0):
        b = band_by_distance(math.hypot(x - self.start[0], y - self.start[1]), self.reach)
        if self.wall_x:
            wx = self.wall_x(y)
            if wx is not None and x < wx:
                up += 1
        if self.north is not None and y > self.north:
            up += 1
        return max(0, min(2, b + up))

    def ok_spot(self, x, y):
        return (math.hypot(x - self.start[0], y - self.start[1]) > START_CLEAR and not self.A.near_door(x, y)
                and not self.A.near_settled(x, y))

    def beside(self, a, edid):
        """Spots round anchor a for a find: (x, y, its turn), its back to the anchor and its front (`front_of`) looking out,
        the sides tried in a shuffled order."""
        ax, ay, _az, arz, s, box = a[:6]
        fb = self.P.box(edid)
        if not fb:
            return []
        front = self.P.front(edid)
        back = back_reach(fb, front) + 8.0
        out = []
        cx, cy = (box[0] + box[3]) / 2 * s, (box[1] + box[4]) / 2 * s
        hx, hy = (box[3] - box[0]) / 2 * s, (box[4] - box[1]) / 2 * s
        for n, along in (((0.0, -1.0), 2 * hx), ((0.0, 1.0), 2 * hx), ((-1.0, 0.0), 2 * hy), ((1.0, 0.0), 2 * hy)):
            for t in (0.0, -0.3, 0.3):
                if n[0] == 0.0:
                    lx, ly = cx + t * along, cy + n[1] * hy
                else:
                    lx, ly = cx + n[0] * hx, cy + t * along
                ex, ey = _turn(lx, ly, arz)
                nx, ny = _turn(n[0], n[1], arz)
                out.append((ax + ex + nx * back, ay + ey + ny * back, _face(nx, ny, front)))
        self.P.rng.shuffle(out)
        return out

    def put_by(self, a, kind, band, spot, lock_extra=0, key=None, name=None):
        """One find of `kind` against anchor a; the op, or None when no side of it will do."""
        edid, lock = (KINDS['safe'][band][0][0], None) if kind == 'safe' else self.P.choose(kind, band)
        if kind == 'safe':
            lo, hi = KINDS['safe'][band][0][2]
            lock = self.P.rng.choice([v for v in (25, 50, 75, 100) if lo <= v <= hi])
        if edid is None:
            return None
        fb = self.P.box(edid)
        if not fb:
            return None
        r = max(fb[3] - fb[0], fb[4] - fb[1]) / 2
        level = a[2] + a[5][2] * a[4]                   # (the anchor's underside: what it stands on)
        self.S.load(a[0], a[1])
        for x, y, rz in self.beside(a, edid):
            if not self.ok_spot(x, y) or not self.S.free(x, y, r):
                continue
            lvl = level
            if (a[5][5] - a[5][2]) * a[4] > TALL and self.S.G:     # (beside a building or a ship: its underside is
                g = self.S.G.at(x, y)                               # no guide to the ground beside it)
                lvl = g if g is not None else level
            p = self.S.at(x, y, rz, fb, lvl)
            if p is None:
                continue
            ck = self.A.grid.get((int(x // 4096), int(y // 4096)))
            if ck is None:
                continue
            if lock is not None and lock_extra:
                lock = min(100, lock + lock_extra)
            op = self.P.add(self.P.gd.key(ck), edid, p, lock=lock, key=key, spot=spot, band=band, name=name)
            self.S.take(x, y, r)
            self.cells.add(self.P.gd.key(ck))
            return op
        return None

    def spot(self, anchors, kind, band, recipe=None, keyed=None):
        """A spot's finds against its anchors, as the recipe has them; keyed: (key name, key editor ID) for a safe needing
        a key, the key on another find's lid. Returns how many went in."""
        kinds, counts = RECIPES[recipe or kind]
        want = counts[band]
        anchors = list(anchors)
        self.P.rng.shuffle(anchors)
        done, ops = 0, []
        for n in range(want):
            k = kinds[n % len(kinds)]
            for a in anchors:
                op = self.put_by(a, k, band, recipe or kind)
                if op:
                    anchors.remove(a)
                    anchors.append(a)
                    ops.append(op)
                    done += 1
                    break
        if keyed and ops:
            key_name, key_edid = keyed
            for a in anchors:
                op = self.put_by(a, 'safe', 2, (recipe or kind) + ' safe', key='$' + key_edid)
                if op:
                    lid = min(ops, key=lambda o: abs(o['p'][3]) + abs(o['p'][4]))     # (the levellest lid)
                    self.key_on(lid, key_edid, key_name)
                    done += 1
                    break
        return done

    def key_on(self, lid, key_edid, key_name):
        """The key on the lid of `lid` (an add op): its record first in the ops."""
        P = self.P
        P.ops.insert(0, {'op': 'record_new', 'record': key_record(P.gd, key_edid, key_name), 'name': key_edid})
        fb = townbuild.obnd(P.gd, lid['base'])
        kb = P.box(KEY_FROM) or [-4, -2, 0, 4, 2, 1]
        p = list(lid['p'])
        z = p[2] + fb[5] - kb[2] + 0.5
        P.ops.append({'op': 'add', 'cell': lid['cell'], 'base': '$' + key_edid, 'p': [p[0], p[1], round(z, 1), 0.0, 0.0, round(P.rng.uniform(0, math.tau), 4)], 's': 1.0})
        lid.pop('extra', None)                             # (a lid with the key on it opens freely)
        P.keys.append(key_name)
        P.report['keys'] += 1


def band_by_distance(d, reach):
    return 0 if d < BAND_SHARE[0] * reach else 1 if d < BAND_SHARE[1] * reach else 2


def farthest(gd, world, start):
    """How far the world's farthest cell corner lies from the start."""
    return max(math.hypot(x * 4096.0 + dx - start[0], y * 4096.0 + dy - start[1]) for (x, y) in gd.grid(world) for dx in (0, 4096) for dy in (0, 4096))


def _wall_line():
    try:
        import edges
        return edges._wall_x, edges.NORTH_FROM
    except Exception:
        return None, None


def ops(gd, pr, world, side=None, cat=None, seed=11, scenes=None, posts=None, progress=None):
    """(ops, report) for every find outside and inside. scenes: [(x, y, kind)] (osmdress.scenes' spots); posts: [(x, y)]
    the freeway posts' sections."""
    P = Plan(gd, pr, world, seed)
    A = Anchors(gd, pr, world)
    S = Seat(gd, pr, world)
    S.feet = A.feet
    ng = pr.newgame or {}
    start = tuple((ng.get('p') or [0, 0])[:2])
    wall_x, north = _wall_line()
    O = Outside(P, A, S, start, wall_x, north, farthest(gd, world, start))
    marks = _markers(gd, pr, world)
    used = set()                                         # (anchors already a spot's)

    def anchors_round(x, y, r, test=None, up=None):
        out = []
        for a in A.near(x, y, r):
            if (a[7], a[8]) in used or CAIRN.search(a[6]):
                continue
            if test and not test(a):
                continue
            if up is not None:
                g = S.G.at(a[0], a[1]) if S.G else None
                if g is None or a[2] + a[5][2] * a[4] - g < up:
                    continue
            out.append(a)
        return out

    # held and high places, first: they take their anchors
    n_keys = 0
    for name, (kind, reach, up, keyed) in PLACES.items():
        if name not in marks:
            P.report['place not found: ' + name] += 1
            continue
        x, y, _z = marks[name]
        ans = anchors_round(x, y, reach)
        b = O.band(x, y, up)
        key = None
        if keyed:
            n_keys += 1
            key = ('%s Safe Key' % name.replace('The ', ''), 'FOLabLootKey%02d' % n_keys)
        got = O.spot(ans, kind, b, recipe=kind, keyed=key)
        P.where['place ' + name]['finds'] += got
        for a in ans:
            used.add((a[7], a[8]))
    # the freeway posts: anchors up on the deck
    for x, y in posts or ():
        ans = anchors_round(x, y, 1700.0, up=FREEWAY_UP)
        O.spot(ans, 'post', O.band(x, y, 1), recipe='post')
        for a in ans:
            used.add((a[7], a[8]))
    # the scenes
    for i, (x, y, kind) in enumerate(scenes or ()):
        if progress and i % 50 == 0:
            progress('Scenes', i, len(scenes))
        if kind not in RECIPES:
            continue
        ans = anchors_round(x, y, SCENE_REACH, up=None)
        ans = [a for a in ans if not S.G or (S.G.at(a[0], a[1]) is not None and a[2] + a[5][2] * a[4] - S.G.at(a[0], a[1]) < ROOF_UP)]
        b = O.band(x, y)
        keyed = None
        if kind == 'raiders' and b == 2 and n_keys < 24 and P.rng.random() < 0.15:
            n_keys += 1
            keyed = ('Raider Stash Key', 'FOLabLootKey%02d' % n_keys)
        O.spot(ans, kind, b, recipe=kind, keyed=keyed)
        for a in ans:
            used.add((a[7], a[8]))
    # roof camps: one spot a roof (anchors up there, grouped by the roof)
    roofs = collections.defaultdict(list)
    for a in A.all:
        if (a[7], a[8]) in used or not CAMP_THINGS.search(a[6]):
            continue
        g = S.G.at(a[0], a[1]) if S.G else None
        if g is None or a[2] + a[5][2] * a[4] - g < ROOF_UP or a[2] - g > FREEWAY_UP:
            continue
        roofs[(int(a[0] // 1500), int(a[1] // 1500), int(a[2] // 300))].append(a)
    for i, (k, ans) in enumerate(sorted(roofs.items())):
        if progress and i % 50 == 0:
            progress('Roofs', i, len(roofs))
        x, y = ans[0][0], ans[0][1]
        O.spot(ans, 'roof', O.band(x, y, 1), recipe='roof')
        for a in ans:
            used.add((a[7], a[8]))
    # wrecks: one in WRECK_SHARE, on the land
    wrecks = [a for a in A.all if WRECKS.search(a[6]) and (a[7], a[8]) not in used]
    wrecks.sort(key=lambda a: (a[7], a[8]))
    for i, a in enumerate(wrecks):
        if P.rng.random() > WRECK_SHARE:
            continue
        g = S.G.at(a[0], a[1]) if S.G else None
        if g is None or abs(a[2] - g) > ROOF_UP:
            continue
        O.spot([a], 'wreck', O.band(a[0], a[1]), recipe='wreck')
    # cairns on the crest: a stash behind one in CAIRN_EVERY
    cairns = sorted((a for a in A.all if CAIRN.search(a[6])), key=lambda a: (a[7], a[8]))
    for i, a in enumerate(cairns):
        if i % CAIRN_EVERY == 0:
            O.spot([a], 'cairn', O.band(a[0], a[1], 1), recipe='cairn')
    # ruins behind the wall: against what stands there
    if wall_x:
        behind = [a for a in A.all if (a[7], a[8]) not in used and wall_x(a[1]) is not None and a[0] < wall_x(a[1]) - 1500]
        P.rng.shuffle(behind)
        n = 0
        for a in behind:
            if n >= RUINS_BEHIND:
                break
            keyed = None
            if n % 6 == 0 and n_keys < 30:
                n_keys += 1
                keyed = ('Old Safe Key', 'FOLabLootKey%02d' % n_keys)
            if O.spot([a] + anchors_round(a[0], a[1], 600), 'ruin', 2, recipe='ruin', keyed=keyed):
                n += 1
            used.add((a[7], a[8]))
    rep = dict(P.report)
    rep['by_spot'] = {k: dict(v) for k, v in P.where.items() if not k.startswith('place ')}
    rep['places'] = {k[6:]: dict(v) for k, v in P.where.items() if k.startswith('place ')}
    rep['keys_named'] = P.keys
    rep['missing'] = P.missing
    rep['cells'] = sorted(O.cells)
    return P, rep


# ----- inside -----

# empty containers and the full ones of the same model, by what the place is (checked: same model, or left out)
FILL = {
    'Footlocker01Empty': {'home': 'Footlocker01HouseholdNV', 'security': 'Footlocker01MilitaryNV', 'medical': 'Footlocker01Hospital',
                          'works': 'Footlocker01FactoryNV', 'shop': 'Footlocker01HouseholdNV', 'school': 'Footlocker01School', '*': 'Footlocker01HouseholdNV'},
    'SSCrateContainerEmpty': {'food': 'VLootFoodSSCrateGen06', '*': 'SSCrateContainer'},
    'NVDuffleBagContainerEmpty': {'*': 'NVDuffleBagRandomLoot'},
    'CashRegisterEmpty': {'*': 'LootCashRegister'},
    'FilingCabinetEmpty': {'*': 'FilingCabinetNV'},
    'Locker01Empty': {'security': 'Locker01Military', '*': 'Locker01Military'},
    'SuitCase01Empty': {'*': 'SuitCase01'},
    'MetalBox01Empty': {'*': 'MetalBox01'},
    'MetalBox02Empty': {'*': 'MetalBox02'},
}
FILL_SHARE = (0.4, 0.5, 0.6)
# locks inside, by band: (share of these locked, lowest, highest)
LOCK_INSIDE = {
    'safe': ((1.0, 25, 50), (1.0, 50, 75), (1.0, 75, 100)),
    'guncab': ((1.0, 25, 50), (1.0, 50, 75), (1.0, 75, 100)),
    'kit': ((0.1, 0, 25), (0.2, 25, 50), (0.3, 50, 75)),
    'box': ((0.08, 0, 25), (0.15, 25, 50), (0.25, 50, 75)),
}
LOCK_WORDS = [('safe', re.compile(r'^(genericsafe|lootsafe)|safe(floor|wall)', re.I)), ('guncab', re.compile(r'guncabinet', re.I)), ('kit', re.compile(r'firstaidkit|drugkit', re.I)),
              ('box', re.compile(r'^(footlocker|lootammobox|locker01military)', re.I))]
PLACE_WORDS = [('medical', re.compile(r'medic|clinic|care|hospital|health|pharm|kapiolani|kuakini|biomedical', re.I)),
               ('security', re.compile(r'police|security|armory|military|fort|hale koa|warrior|battery|missouri', re.I)),
               ('food', re.compile(r"zippy|costco|market|food|grocer|safeway|restaurant|cafe|cafeteria|meadow gold", re.I)),
               ('school', re.compile(r'school|college|universit|library|hall|education', re.I)),
               ('works', re.compile(r'^works$|factory|laborator', re.I)), ('shop', re.compile(r'^shop$|store|mall|plaza|center|centre', re.I)),
               ('home', re.compile(r'^house$|apartment|tower|terrace|villa|hale ', re.I))]
# what a place with nothing in it gets, and extras by kind: [kind of find, ...]
EMPTY_GETS = {'medical': ['medicine'], 'security': ['military'], 'food': ['food'], 'works': ['tools'], 'shop': ['food'], 'home': ['bag'], '*': ['bag']}
EXTRAS = {'medical': ['medicine', 'medicine'], 'food': ['food', 'food'], 'security': ['guns', 'ammo']}
MISSOURI = {'Turret Two': ['ammo', 'ammo', 'explosives', 'explosives', 'guns'], 'Second Deck': ['medicine', 'medicine', 'food', 'bag'],
            'Engine Room': ['tools', 'tools', 'ammo'], 'Pilot House': ['safe']}
WALL_GAP = 6.0


def place_kind(name):
    for k, rx in PLACE_WORDS:
        if rx.search(name or ''):
            return k
    return '*'


def _same_model(gd, a, b):
    try:
        fa, fb = gd.fields(a).get('MODL'), gd.fields(b).get('MODL')
    except (KeyError, ValueError):
        return False
    return bool(fa) and fa.rstrip(b'\0').lower() == (fb or b'').rstrip(b'\0').lower()


class Inside:
    def __init__(self, P, band_of_place):
        self.P, self.band_of = P, band_of_place
        gd = P.gd
        want = set(FILL) | {v for d in FILL.values() for v in d.values()}
        self.f = {}
        for f, (_i, r) in gd.forms.items():
            e = gd.edid(f)
            if e in want and r.tag == 'CONT' and (e not in self.f or (f >> 24) == 0):
                self.f[e] = f
        self.fill = {}
        for empty, by in FILL.items():
            if empty not in self.f:
                continue
            ok = {k: v for k, v in by.items() if v in self.f and _same_model(gd, self.f[empty], self.f[v])}
            if ok:
                self.fill[gd.key(self.f[empty])] = {k: gd.key(self.f[v]) for k, v in ok.items()}
        self.rep = collections.Counter()
        self.made = {}                                  # (place name: [(kind, op)])

    def edid(self, key):
        return settleup._edid(self.P.gd, self.P.pr, key)

    def run(self, places, names, progress=None):
        """places: [cell key]; names: {cell key: its name}."""
        P = self.P
        for i, ck in enumerate(places):
            if progress and i % 100 == 0:
                progress('Inside', i, len(places))
            name = names.get(ck, '')
            kind = place_kind(name)
            band = self.band_of(ck)
            refs = (P.pr.cells.get(ck) or {}).get('refs', {})
            n_cont = 0
            for rk, r in sorted(refs.items()):
                b = r.get('base')
                if not b or r.get('removed') or not r.get('p'):
                    continue
                if b in self.fill:
                    n_cont += 1
                    if P.rng.random() < FILL_SHARE[band]:
                        to = self.fill[b].get(kind) or self.fill[b].get('*')
                        if to:
                            P.ops.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': to})
                            self.rep['filled'] += 1
                    continue
                e = self.edid(b)
                if not e:
                    continue
                for lk, rx in LOCK_WORDS:
                    if rx.search(e):
                        n_cont += 1
                        if (r.get('props') or {}).get('lock'):
                            break
                        share, lo, hi = LOCK_INSIDE[lk][band]
                        if P.rng.random() < share:
                            lv = P.rng.choice([v for v in (0, 25, 50, 75, 100) if lo <= v <= hi])
                            P.ops.append({'op': 'props', 'cell': ck, 'ref': rk, 'props': {'lock': {'level': lv, 'key': '', 'leveled': False}}})
                            self.rep['locked ' + lk] += 1
                        break
                else:
                    if _base_type(P.gd, P.pr, b) == 'CONT':
                        n_cont += 1
            want = []
            if name.startswith('USS Missouri'):
                for part, kinds in MISSOURI.items():
                    if part in name:
                        want = list(kinds)
            elif n_cont == 0:
                want = list(EMPTY_GETS.get(kind) or EMPTY_GETS['*'])
            want += EXTRAS.get(kind, [])
            if want:
                self.rep['places given finds'] += 1
                self.walls(ck, want, band, name)

    def walls(self, ck, kinds, band, name):
        """Finds against walls where the place's navmesh ends, off its doorways, on its real floor."""
        P = self.P
        nav = P.pr.navmesh.get(ck)
        if not nav or not nav.get('tris'):
            self.rep['no navmesh'] += 1
            return
        V, T = nav['verts'], nav['tris']
        door_tris = {d[1] for d in nav.get('doors') or ()}
        S = Seat(P.gd, P.pr, None)
        S.solids.load_round([ck])
        doors, feet = [], []
        for rk, r in (P.pr.cells.get(ck) or {}).get('refs', {}).items():
            if not r.get('p') or not r.get('base') or r.get('removed'):
                continue
            if r.get('tel') or _base_type(P.gd, P.pr, r['base']) == 'DOOR':
                doors.append(r['p'][:2])
            box = townbuild.obnd(P.gd, r['base']) if not r['base'].startswith('+') else None
            s = float(r.get('s') or 1.0)
            if box and max(box[3] - box[0], box[4] - box[1]) * s < 300 and (box[5] - box[2]) * s < 230:   # (furniture, not the room's walls)
                p = r['p']
                feet.append((ck, rk, townbuild._foot([v * s for v in box], p[5] if len(p) > 5 else 0.0, p), p[2] + box[2] * s, p[2] + box[5] * s))
        S.feet = lambda fp: feet
        edges = []
        for ti, t in enumerate(T):
            if ti in door_tris:
                continue
            for e in range(3):
                if t[3 + e] != 0xFFFF:
                    continue
                a, b = V[t[e]], V[t[(e + 1) % 3]]
                c = V[t[(e + 2) % 3]]
                ln = math.hypot(b[0] - a[0], b[1] - a[1])
                if ln < 90:
                    continue
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                nx, ny = -(b[1] - a[1]) / ln, (b[0] - a[0]) / ln
                if nx * (c[0] - mx) + ny * (c[1] - my) < 0:
                    nx, ny = -nx, -ny                     # (into the triangle: into the room)
                edges.append((ln, mx, my, (a[2] + b[2]) / 2, nx, ny))
        P.rng.shuffle(edges)
        edges.sort(key=lambda e: -e[0])
        edges = edges[:60]
        P.rng.shuffle(edges)
        lock_of = lambda k: P.choose(k, band) if k != 'safe' else (KINDS['safe'][band][0][0], 75)
        for k in kinds:
            edid, lock = lock_of(k)
            if not edid:
                continue
            fb = P.box(edid)
            if not fb:
                continue
            front = P.front(edid)
            back = back_reach(fb, front) + WALL_GAP
            r = max(fb[3] - fb[0], fb[4] - fb[1]) / 2
            for ln, mx, my, mz, nx, ny in edges:
                x, y = mx + nx * back, my + ny * back
                if any(math.hypot(x - d[0], y - d[1]) < DOOR_CLEAR for d in doors) or not S.free(x, y, r):
                    continue
                rz = _face(nx, ny, front)
                p = S.at(x, y, rz, fb, mz, outside=False)
                if p is None:
                    continue
                op = P.add(ck, edid, p, lock=lock, spot='inside ' + (name if name.startswith('USS') else place_kind(name)), band=band)
                self.made.setdefault(name, []).append((k, op))
                S.take(x, y, r)
                self.rep['inside finds'] += 1
                break


def inside_ops(P, start, progress=None):
    """Fills, locks and finds in the mod's own places; their band from where their way in stands outside."""
    gd, pr = P.gd, P.pr
    names = {}
    for k, rec in pr.records.items():
        if k.startswith('+') and rec.get('type') == 'CELL' and k in pr.cells:
            names[k] = recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID') or ''
    # where each place's way in stands outside: its door's link names a door inside
    door_place = {}
    for ck in names:
        for rk in (pr.cells.get(ck) or {}).get('refs', {}):
            door_place[rk] = ck
    outside_at = {}
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in c.get('refs', {}).items():
            t = r.get('tel')
            if t and t.get('door') in door_place and r.get('p'):
                outside_at.setdefault(door_place[t['door']], r['p'][:2])
    # (a place reached only through another place: as far as the place it's reached from)
    for _ in range(3):
        for ck, c in pr.cells.items():
            if ck not in names or ck not in outside_at:
                continue
            for rk, r in c.get('refs', {}).items():
                t = r.get('tel')
                if t and t.get('door') in door_place:
                    outside_at.setdefault(door_place[t['door']], outside_at[ck])
    wall_x, north = _wall_line()
    reach = farthest(gd, P.world, start)

    def band_of(ck):
        xy = outside_at.get(ck)
        if not xy:
            return 1
        b = band_by_distance(math.hypot(xy[0] - start[0], xy[1] - start[1]), reach)
        if wall_x and wall_x(xy[1]) is not None and xy[0] < wall_x(xy[1]):
            b += 1
        if names.get(ck, '').startswith('USS Missouri'):
            b += 1
        return min(2, b)
    I = Inside(P, band_of)
    I.run(sorted(names), names, progress)
    # the Missouri's pilot house safe opens with a key left on a find on the second deck
    safe = next((op for n, got in I.made.items() if 'Pilot House' in n for k, op in got if k == 'safe'), None)
    lids = [op for n, got in I.made.items() if 'Second Deck' in n for k, op in got if k != 'safe']
    if safe and lids:
        O = Outside(P, None, None, start)
        safe['extra'] = {'props': {'lock': {'level': 255, 'key': '$FOLabLootKeyShip', 'leveled': False}}}
        O.key_on(lids[0], 'FOLabLootKeyShip', 'Pilot House Safe Key')
    return dict(I.rep), sum(1 for ck in names if ck not in outside_at)


def all_ops(gd, pr, world, scenes=None, posts=None, seed=11, progress=None):
    """Everything: (ops, report). Records first (the keys), then the rest."""
    P, rep = ops(gd, pr, world, scenes=scenes, posts=posts, seed=seed, progress=progress)
    ng = pr.newgame or {}
    irep, unplaced = inside_ops(P, tuple((ng.get('p') or [0, 0])[:2]), progress)
    rep['inside'] = irep
    rep['places_with_no_way_in_found'] = unplaced
    rep['by_spot'] = {k: dict(v) for k, v in P.where.items() if not k.startswith('place ')}
    rep['keys_named'] = P.keys
    rep['finds'], rep['locked'], rep['keys'] = P.report['finds'], P.report['locked'], P.report['keys']
    recs = [o for o in P.ops if o['op'] == 'record_new']
    rest = [o for o in P.ops if o['op'] != 'record_new']
    return recs + rest, rep


# ----- new ways up -----

class _RoadCover:
    """Enough of osmcover.MapCover for rooftops.plan: road pieces' ground marked as asphalt, nothing else known."""

    def __init__(self, gd, pr, world, A):
        import osmcover
        xs = [xy[0] for xy in gd.grid(world)]
        ys = [xy[1] for xy in gd.grid(world)]
        self.gx0, self.gy0 = min(xs) * 32, min(ys) * 32
        self.A, self.D = (max(xs) - min(xs) + 1) * 32 + 1, (max(ys) - min(ys) + 1) * 32 + 1
        self.kind = bytearray(self.A * self.D)
        road = osmcover.CODE['asphalt']
        for c in gd.grid(world).values():
            for rk, r in (pr.cells.get(gd.key(c)) or {}).get('refs', {}).items():
                b, p = r.get('base'), r.get('p')
                if not b or not p or r.get('removed') or not NOT_ON.search(A.edid(b) or ''):
                    continue
                box = A.box(b)
                if not box:
                    continue
                s = float(r.get('s') or 1.0)
                fp = townbuild._foot([v * s for v in box], p[5] if len(p) > 5 else 0.0, p)
                x0, x1 = min(q[0] for q in fp), max(q[0] for q in fp)
                y0, y1 = min(q[1] for q in fp), max(q[1] for q in fp)
                for gy in range(int(y0 // 128), int(y1 // 128) + 1):
                    for gx in range(int(x0 // 128), int(x1 // 128) + 1):
                        i, j = gx - self.gx0, gy - self.gy0
                        if 0 <= i < self.A and 0 <= j < self.D:
                            self.kind[j * self.A + i] = road


NEW_WAYS_APART = 6000.0
NEW_WAYS_LOW = 520.0            # (a roof this high at least: worth the climb)


def new_ways(gd, pr, world, cat, n=10, seed=11):
    """(ops, report): ways up (rooftops' ramp towers and roof camps) onto the highest flat roofs that have none near, spread
    apart, in the middling and hard bands."""
    import rooftops
    A = Anchors(gd, pr, world)
    by_key = {b['key']: b for b in cat}
    ng = pr.newgame or {}
    start = tuple((ng.get('p') or [0, 0])[:2])
    ramps = []
    stands = []
    for c in gd.grid(world).values():
        ck = gd.key(c)
        for rk, r in (pr.cells.get(ck) or {}).get('refs', {}).items():
            b, p = r.get('base'), r.get('p')
            if not b or not p or r.get('removed'):
                continue
            if settleup.RAMP_PIECE.match(A.edid(b) or ''):
                ramps.append(p[:2])
            elif b in by_key and rk.startswith('+'):
                stands.append((rk, p, float(r.get('s') or 1.0), by_key[b]))
    reach = farthest(gd, world, start)
    cands = []
    for rk, p, s, b in stands:
        if band_by_distance(math.hypot(p[0] - start[0], p[1] - start[1]), reach) == 0:
            continue
        if any(math.hypot(p[0] - q[0], p[1] - q[1]) < settleup.RAMP_REACH for q in ramps):
            continue
        roof = rooftops.roof_of(gd, b['model'], b['box'])
        if not roof or roof['z'] * s < NEW_WAYS_LOW or roof['z'] * s > rooftops.HIGH:
            continue
        rf = rooftops.roof_floor(gd, b['model'], roof)
        if sum(rf.clear) < rooftops.OPEN_ROOF * len(rf.clear):
            continue
        cands.append((roof['z'] * s, rk, p))
    cands.sort(reverse=True)
    chosen = []
    for h, rk, p in cands:
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= NEW_WAYS_APART for _rk, q in chosen):
            chosen.append((rk, p))
        if len(chosen) >= n * 2:                       # (some find no room for a tower: twice as many tried)
            break
    cover = _RoadCover(gd, pr, world, A)
    o, rep = rooftops.plan(gd, pr, world, cover, cat, seed=seed, only={rk for rk, _p in chosen}, extras=False, limit=n)
    rep['tried'] = len(chosen)
    return o, rep
