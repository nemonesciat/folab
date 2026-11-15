"""What makes a world made from a map somewhere to be, not only to look at: its own weather, water and sound, how hard
it gets as you go further from where you start, places named on the map, who lives at the camps and in the wild, and one
safe settlement. All of it the game's own records, put together as ops for one Undo.

    air        a region over the whole world (weathers by chance, the sounds of one of the game's regions), and on each
               cell the water and the music
    zones      encounter zones by how far a cell is from the start: the lowest level things scale to rises with distance
    markers    map markers at landmarks, the settlement, the bigger camps
    people     who stands at each scene osmdress made (raiders at their camps, prospectors at theirs, ghouls at a crash)
    wildlife   groups in the open by what the ground is (geckos on grass, lurks on the shore...), none near the start
    settlement a camp with walls of sandbags, tents, a fire, beds, traders and their guards

Nobody here can walk until the world has navmeshes (navbuild.generate_area): make those after."""
import math
import random

import roadgen
import worldrec

TIERS = ((0, 1), (7, 8), (13, 16))            # (from how many cells off the start, the zone's lowest level)
# who stands at a scene, by how hard the place is (easy, middling, hard): [(editor ID, how many)]
AT_SCENE = {
    'raiders': ([('LvlRaider1GunVar', 2), ('LvlRaider1MeleeVar', 1)], [('VJackalGangSpawnMale', 2), ('VJackalGangSpawnFemale', 2)],
                [('LvlFiend2GunVarNV', 2), ('LvlFiend2RifleVarNV', 1), ('LvlFiend2MeleeVarNV', 2)]),
    'roadblock': ([('LvlRaider1GunVar', 2)], [('VViperGangSpawnGunA', 2), ('VViperGangSpawnGunB', 1)], [('LvlFiend2RifleVarNV', 2), ('LvlFiend2GunVarNV', 2)]),
    'camp': ([('VSpawnProspectorAll', 2)], [('VSpawnProspectorAll', 2)], [('VSpawnProspectorAll', 3)]),
    'refuge': ([('LvlWastelander', 3)], [('LvlWastelander', 3)], [('LvlWastelander', 2)]),
    'crash': ([('LvlWastelandBloatfly', 3)], [('LvlFeralGhoul', 3)], [('LvlFeralGhoul', 4)]),
}
# who lives in the open, by the ground and how hard the place is
IN_THE_WILD = {
    'grass': ([('LvlGecko', 3)], [('VSpawnTier1GiantMantisSmall', 3)], [('VSpawnFireGeckoTier1', 3)]),
    'trees': ([('VSpawnTier1GiantMantisSmall', 3)], [('CrSporePlant', 3), ('LvlGecko', 2)], [('VCrSporeCarrier', 3), ('CrSporePlant', 2)]),   # (the green fights back)
    'golf': ([('LvlGecko', 2)], [('LvlCoyote', 3)], [('VSpawnNightStalkerTier1', 2)]),
    'scrub': ([('LvlCoyote', 2)], [('LvlRadscorpion', 2)], [('LvlCazador', 2)]),
    'sand': ([('LvlWastelandBloatfly', 2)], [('VSpawnTier3LakelurkMed', 2)], [('VSpawnTier3LakelurkMed', 3)]),
    'paved': ([('LvlWastelandDog', 2)], [('LvlFeralGhoul', 3)], [('LvlFeralGhoul', 4)]),
    'yard': ([('LvlWastelandDog', 2)], [('LvlWastelandMoleRat', 3)], [('LvlFeralGhoul', 3)]),
}
WILD_EVERY = 6              # (land cells to a group in the open)
WILD_APART = 3600.0
SAFE = 5200.0               # (nothing hostile this near the start or the settlement)
MARKER = {'city': 1, 'settlement': 2, 'camp': 3, 'natural': 4, 'cave': 5, 'factory': 6, 'monument': 7, 'military': 8, 'office': 9, 'town ruins': 10, 'urban ruins': 11}
SEEN, TRAVEL = 1, 2         # (a marker's flags: shown on the map before it's found; can be travelled to)
# a settlement: (editor ID, how many, nearest, furthest from the fire, facing 'in' | 'ring' (along the ring) | 'any')
CAMP = [('CampfireCrafting03', 1, 0, 0, 'any'), ('CLSoldiersTent01', 3, 420, 520, 'in'), ('NVBSRefugeeTent', 2, 480, 560, 'in'), ('NVBedrollL', 2, 190, 240, 'in'),
        ('NVBedrollR', 2, 190, 240, 'in'), ('TruckTrailer03', 1, 640, 700, 'ring'), ('CrateLarge01', 4, 300, 650, 'any'), ('Barrel01', 4, 300, 650, 'any'),
        ('FlagPole', 1, 300, 340, 'any'), ('WaterTower01', 1, 760, 820, 'any'), ('dlc04lawnchair01', 3, 150, 200, 'in'), ('VBitterSpringsClotheslineShort', 1, 560, 640, 'ring'),
        ('NVGuardTower01', 1, 900, 940, 'in')]
CAMP_WALL = ('SandbagStraight', 980.0, 20, (4, 5, 14, 15))      # (the piece, how far out, how many round the ring, which are left out as ways in)
CAMP_FOLK = [('LvlCrimsonCaravanTrader', 1), ('LvlCrimsonCaravanTraderGuard', 3), ('LvlCrimsonCaravanTraderBrahmin', 1), ('VSpawnMerchantMaleGroup01', 1),
             ('LvlWastelander', 3), ('VSpawnProspectorAll', 2)]


def _find(gd, tags, edid):
    low = edid.lower()
    for f, (_i, r) in gd.forms.items():
        if r.tag in tags and gd.edid(f).lower() == low:
            return gd.key(f)
    return None


class Life:
    def __init__(self, gd, pr, world, start, seed=1):
        self.gd, self.pr, self.world = gd, pr, world
        self.wkey = gd.key(world)
        self.grid = gd.grid(world)
        self.ground = roadgen.Ground(gd, pr, world)
        self.start = start
        self.rng = random.Random(seed * 86028121 + 17)
        self.ops, self.report = [], {}
        self.info = {}                          # (cell key: what goes on it, gathered and written once)
        self.keys = {}
        self.safe = [(start[0], start[1])]
        self.tier_of = {}
        self.taken = []
        self.blocked = None                     # (blocked(x, y) -> True where nobody can stand: inside a building, a landmark)

    def key(self, tags, edid):
        k = (tags, edid.lower())
        if k not in self.keys:
            self.keys[k] = _find(self.gd, tags, edid)
        return self.keys[k]

    def new_key(self):
        k = '+%06X' % self.pr.next_id
        self.pr.next_id += 1
        return k

    def land_cells(self):
        return [k for k in self.grid if any(h >= 8 for h in (self.ground.cell(k) or ()))]

    def tier(self, x, y):
        d = max(abs(int(x // 4096) - int(self.start[0] // 4096)), abs(int(y // 4096) - int(self.start[1] // 4096)))
        return max(n for n, (frm, _lvl) in enumerate(TIERS) if d >= frm)

    # ----- air -----

    def air(self, edid, weathers, sounds_like=None, water=None, music=None):
        """weathers: [(WTHR editor ID, chance)]; sounds_like: a game region's editor ID whose sounds are taken; water, music: editor IDs."""
        gd = self.gd
        rows = [{'key': self.key(('WTHR',), e), 'chance': int(c), 'global': ''} for e, c in weathers if self.key(('WTHR',), e)]
        sounds = []
        like = self.key(('REGN',), sounds_like) if sounds_like else None
        if like:
            sounds = [{'key': s['key'], 'flags': s['flags'], 'chance': s['chance']} for s in worldrec.region_read(gd, self.pr, like)['sounds']]
        cells = sorted(self.grid)
        rkey = self.new_key()
        d = {'edid': edid, 'color': '#3f9f8f', 'world': self.wkey, 'weathers': rows, 'sounds': sounds, 'objects': [], 'priority': 60, 'map': ''}
        self.ops.append({'op': 'record', 'key': rkey, 'record': worldrec.region_record(gd, self.pr, d, [list(c) for c in cells], None)})
        wkey, mkey = (self.key(('WATR',), water) if water else None), (self.key(('MUSC',), music) if music else None)
        for k in cells:
            info = self.info.setdefault(gd.key(self.grid[k]), {})
            info['XCLR'] = worldrec.regions_of(gd, self.pr, gd.key(self.grid[k])) + [rkey]
            if wkey:
                info['XCWT'] = wkey
            if mkey:
                info['XCMO'] = mkey
        self.report['air'] = {'weathers': [e for e, _c in weathers if self.key(('WTHR',), e)], 'sounds': len(sounds), 'water': bool(wkey), 'music': bool(mkey), 'cells': len(cells)}

    # ----- how hard -----

    def zones(self, edid):
        keys = []
        for n, (_frm, level) in enumerate(TIERS):
            k = self.new_key()
            self.ops.append({'op': 'record', 'key': k, 'record': worldrec.zone_record({'edid': '%sZone%d' % (edid, n + 1), 'level': level, 'flags': 0})})
            keys.append(k)
        count = [0] * len(TIERS)
        for k in self.grid:
            t = self.tier(k[0] * 4096.0 + 2048, k[1] * 4096.0 + 2048)
            self.info.setdefault(self.gd.key(self.grid[k]), {})['XEZN'] = keys[t]
            count[t] += 1
        self.report['zones'] = {'levels': [lvl for _f, lvl in TIERS], 'cells': count}

    # ----- on the map -----

    def marker(self, x, y, name, kind, seen=False):
        z = self.ground.at(x, y)
        if z is None or (int(x // 4096), int(y // 4096)) not in self.grid:
            return False
        self.ops.append(worldrec.marker_op(self.gd, self.world, [float(x), float(y), float(max(z, 0)) + 40.0], name, MARKER.get(kind, 11), TRAVEL | (SEEN if seen else 0)))
        self.report.setdefault('markers', []).append(name)
        return True

    # ----- who -----

    def stand(self, rows, x, y, spread=170.0):
        """Actors round a spot: [(editor ID, how many)]. Returns how many were stood."""
        n = 0
        todo = [(self.key(('NPC_', 'CREA'), e), c) for e, c in rows]
        total = sum(c for k, c in todo if k)
        at = 0
        for key, count in todo:
            for _k in range(count if key else 0):
                a = math.tau * at / max(1, total) + self.rng.uniform(-0.3, 0.3)
                at += 1
                d = spread * self.rng.uniform(0.6, 1.3) if total > 1 else 0.0
                px, py = x + math.sin(a) * d, y + math.cos(a) * d
                z = self.ground.at(px, py)
                cell = self.grid.get((int(px // 4096), int(py // 4096)))
                if z is None or z < 8 or cell is None or (self.blocked and self.blocked(px, py)):
                    continue
                self.ops.append({'op': 'add', 'cell': self.gd.key(cell), 'base': key, 'p': [round(px, 1), round(py, 1), round(z + 4.0, 1), 0.0, 0.0, round(self.rng.uniform(0, math.tau), 3)], 's': 1})
                n += 1
        return n

    def near_safe(self, x, y, reach=SAFE):
        return any(math.hypot(x - a, y - b) < reach for a, b in self.safe)

    def people(self, scenes):
        """scenes: [[x, y, kind]] as osmdress.scenes reports them."""
        got = {}
        for x, y, kind in scenes:
            rows = AT_SCENE.get(kind)
            if not rows:
                continue
            if self.blocked and self.blocked(x, y):
                continue                        # (the scene was cleared for something built there since)
            hostile = kind in ('raiders', 'roadblock', 'crash')
            if hostile and self.near_safe(x, y):
                continue
            n = self.stand(rows[self.tier(x, y)], x, y, 230.0)
            if n:
                got[kind] = got.get(kind, 0) + n
                self.taken.append((x, y))
        self.report['people'] = got

    def wildlife(self, kind_at, keep_clear=None):
        """kind_at(x, y) -> the ground's kind (osmcover's names) or None; keep_clear(x, y) -> True where nothing may stand."""
        cells = sorted(self.land_cells())
        want = max(1, len(cells) // WILD_EVERY)
        got, groups = {}, 0
        for _try in range(want * 40):
            if groups >= want or not cells:
                break
            cx, cy = self.rng.choice(cells)
            x, y = (cx + self.rng.random()) * 4096.0, (cy + self.rng.random()) * 4096.0
            rows = IN_THE_WILD.get(kind_at(x, y))
            z = self.ground.at(x, y)
            if not rows or z is None or z < 16 or self.near_safe(x, y) or (keep_clear and keep_clear(x, y)) \
                    or any(math.hypot(x - a, y - b) < WILD_APART for a, b in self.taken):
                continue
            pick = rows[self.tier(x, y)]
            n = self.stand(pick, x, y)
            if n:
                groups += 1
                self.taken.append((x, y))
                got[pick[0][0]] = got.get(pick[0][0], 0) + n
        self.report['wildlife'] = {'groups': groups, 'who': got}

    # ----- somewhere safe -----

    def settlement(self, name, x, y):
        """A camp round a fire at x, y, its traders and guards, a marker shown from the start."""
        import townbuild
        gd, rng = self.gd, self.rng
        level = self.ground.at(x, y)
        if level is None:
            return False

        def put(edid, px, py, yaw):
            key = self.key(('STAT', 'MSTT', 'SCOL', 'ACTI', 'FURN', 'TREE', 'CONT'), edid)
            cell = self.grid.get((int(px // 4096), int(py // 4096)))
            g = self.ground.at(px, py)
            if not key or cell is None or g is None or g < 8 or abs(g - level) > 60:
                return False
            o = townbuild.obnd(gd, key) or [0] * 6
            self.ops.append({'op': 'add', 'cell': gd.key(cell), 'base': key, 'p': [round(px, 1), round(py, 1), round(g - o[2] - 5.0, 1), 0.0, 0.0, round(yaw % math.tau, 3)], 's': 1})
            return True

        things = 0
        used = []
        for edid, count, near, far, face in CAMP:
            for _k in range(count):
                for _again in range(8):
                    a, d = rng.uniform(0, math.tau), rng.uniform(near, far)
                    px, py = x + math.sin(a) * d, y + math.cos(a) * d
                    if any(math.hypot(px - p, py - q) < 150 for p, q in used):
                        continue
                    yaw = rng.uniform(0, math.tau) if face == 'any' else a + (math.pi if face == 'in' else math.pi / 2)
                    if put(edid, px, py, yaw):
                        used.append((px, py))
                        things += 1
                        break
        piece, out, count, gaps = CAMP_WALL
        for k in range(count):
            if k in gaps:
                continue
            a = math.tau * k / count
            things += put(piece, x + math.sin(a) * out, y + math.cos(a) * out, a)      # (its length along the ring)
        folk = self.stand(CAMP_FOLK, x, y, 330.0)
        self.marker(x, y, name, 'settlement', seen=True)
        self.safe.append((x, y))
        self.taken.append((x, y))
        self.report['settlement'] = {'name': name, 'x': round(x), 'y': round(y), 'things': things, 'folk': folk}
        return True

    def done(self):
        for ck, info in sorted(self.info.items()):
            now = dict(self.pr.cellinfo.get(ck) or {})
            now.update(info)
            self.ops.append({'op': 'cellinfo', 'cell': ck, 'info': now})
        self.report['actors'] = sum(1 for o in self.ops if o.get('op') == 'add' and self.gd.forms.get(self.gd.from_key(o['base']), (0, None))[1] is not None
                                    and self.gd.forms[self.gd.from_key(o['base'])][1].tag in ('NPC_', 'CREA'))
        return self.ops, self.report
