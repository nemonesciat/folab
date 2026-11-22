"""Waikiki's people doing things (the user, 21 Nov 2026: "the world needs a lot more activity now that it is starting to look
good"; the plan `docs/waikiki-activity-plan.md`). Each part is its own ops and its own Undo, so the user picks:

  market    a seller and a buyer or two at each cluster of stalls (fruit, lei, shave ice, bamboo), with the game's
            shopkeeper and shopping idle markers
  piers     a fisher at the harbour piers' outer pieces, mending (the game's crouched repair marker) and watching the sea
  pirates   pirates working by their boats (repair, yardwork, smoking markers) on the coast they hold
  farms     the Huáng's Nongmin out in the maize by their courtyards (raking, watering, yardwork markers), their
            wandering widened to reach the rows
  patrols   Court Fighters walking rings between the lookouts round Waikiki, Shouwei along the Huáng's road of gates
            (`worldrec`'s patrol: heading markers linked in a ring, the game's Patrol package)
  fires     the warming-hands marker by fire barrels where people live
  kids      the game's refugee children (a levelled list: a different child each) on the hotels' lawns
  roads     pirates by the road on their own coast (out of Waikiki and the start's reach), a smoke and a watch
  wildlife  creatures where the island has none: worldlife's groups by height (jungle ridges, lowland) and tier

Only the story's groups (locals and storekeepers of Waikiki, the court, the Huáng, the pirates); only clothes that draw in
game (the people are copies of the mod's dressed people, never the joined shirt-and-shorts). Everyone and every marker
stands on open, dry, flat ground with a navmesh under it (`waikikilife.Spots`, `factionfolk._on_mesh`); piers on the
deck's own top. Hostiles keep out of Waikiki (`waikikilife.WAIKIKI_R`) and away from the start (`worldlife.SAFE`).

    ops(gd, pr, part)    (ops, report); new records' keys are taken as planned (apply what you plan)
    apply(server, part)  one part, one Undo
    apply_all(server)    every part as one Undo, the touched cells' navmeshes re-signed in it
    PARTS                the parts in order"""
import json
import math

import recordio

PARTS = ('market', 'piers', 'pirates', 'farms', 'patrols', 'fires', 'kids', 'roads', 'wildlife')

LOCAL = 'FOLabWaikikiLocal'                 # (waikikilife's locals: the mod's surfers, a levelled look, the island's clothes)
PIRATE = 'FOLabPirateLvlFiend2GunVarNV'
STALLS = ('FOLabWaikikiFruitStall', 'FOLabWaikikiLeiStand', 'FOLabWaikikiShaveIceCart', 'FOLabBambooMarketStall')
DOCK = ('PotDockBg4way01',)
BOATS = ('Boat02a', 'Boat02b', 'Boat02c', 'Boat03a', 'Boat03b', 'Barge', 'FOLabBambooCanoe')
MAIZE = ('MaizeHealthyPGroup1', 'SCOLmaizeRow1b', 'SCOLmaizeRow2b')
LOOKOUTS = ('FOLabCityLookout896x0', 'FOLabCityLookout768x0', 'FOLabCityLookout640x0', 'FOLabWaikikiLifeguardTower')
FIRES = ('Barrel02Fire256', 'Barrel02Fire512')
CHILDREN = 'EncVBSRefugeeChild'
GATES = tuple('FOLabSettlerGate%d' % n for n in (1, 2, 3, 4, 5))
MIDDLE_MARKETS, CHILDREN_MOST = 3, 2    # (Waikiki's middle already holds ~25 people in its loaded cells, the game's busiest)

MARKET_MOST, PIER_MOST, PIRATE_MOST, FIRE_MOST, ROAD_MOST = 14, 10, 8, 16, 6
CLUSTER = 1500.0                            # (things this near each other are one place)
PEOPLE_NEAR = 2500.0                        # (a fire barrel counts as somewhere people live within this of one)
FARM_REACH = 1100.0                         # (maize this near a Nongmin is theirs to work)

MARKERS = {
    'sell': 'DefaultShopkeeperIdleMarker', 'shop': 'DefaultShoppingIdleMarker', 'mend': 'DefaultRepairFloorIdleMarker',
    'watch': 'DefaultStandingArmsFoldedIdleMarker', 'repair': 'DefaultRepairItemsIdleMarker', 'yard': 'DefaultYardworkMarker',
    'smoke': 'DefaultSmokingIdleMarker', 'rake': 'DefaultRakingMarker', 'water': 'DefaultWateringPlantMarker',
    'fire': 'DefaultFireBarrelIdleMarker', 'stand': 'DefaultHumanIdleMarker'}
# new people: (editor ID, name, copied from, package)
KINDS = {
    'seller': ('FOLabMarketSeller', 'Stallholder', LOCAL, 'DefaultSandboxEditorLocation256'),
    'buyer': ('FOLabMarketGoer', 'Waikiki Local', LOCAL, 'DefaultSandboxEditorLocation512'),
    'fisher': ('FOLabPierFisher', 'Fisher', LOCAL, 'DefaultSandboxEditorLocation256'),
    'dockhand': ('FOLabPirateDockhand', 'Pirate', PIRATE, 'DefaultSandboxEditorLocation512'),
    'roadside': ('FOLabPirateRoadside', 'Pirate', PIRATE, 'DefaultSandboxEditorLocation512'),
    'surfer': ('FOLabBeachSurfer', 'Surfer', LOCAL, 'DefaultSandboxEditorLocation256'),
}
FARM_PACKAGE = 'DefaultSandboxEditorLocation1024'
PATROL_WAIT = 10.0


# ---------- the place ----------

class Ctx:
    def __init__(self, gd, pr):
        import factionfolk as ff
        import waikikilife as WL
        import worldlife
        self.gd, self.pr = gd, pr
        self.mk = ff._markers(pr)
        self.world = gd.ext_cells[gd.from_key(self.mk[ff.MARKERS['royal']][0])]
        self.grid = gd.grid(self.world)
        self.sp = WL.Spots(gd, pr, self.world)
        self.sp.taken = ff._standing(gd, pr)
        self.sp.gd, self.sp.pr, self.sp.grid = gd, pr, self.grid
        self.mid = WL.middle(pr)[1]
        self.start = ((pr.newgame or {}).get('p') or [None, None])[:2]
        self.SAFE, self.WAIKIKI_R = worldlife.SAFE, WL.WAIKIKI_R
        self.edids = {(recordio.field(r, 'EDID') or ''): k for k, r in pr.records.items()}
        self._base_edid = {}
        self.refs = {}                      # base editor ID -> [(cell, p)]
        for ck, c in pr.cells.items():
            if ck.startswith('+'):
                continue
            for r in (c.get('refs') or {}).values():
                b = r.get('base')
                if not b or r.get('removed') or not r.get('p'):
                    continue
                if b not in self._base_edid:
                    self._base_edid[b] = self.edid_of(b)
                self.refs.setdefault(self._base_edid[b], []).append((ck, r['p']))

    def free_face(self, races, sex):
        """A face of factionfolk's pools no NPC_ of the mod's is made from yet (never one face twice)."""
        import factionfolk as ff
        if not hasattr(self, '_pool'):
            self._pool = ff.faces(self.gd)
            self._used = {r.get('copied_from') for r in self.pr.records.values() if r.get('type') == 'NPC_'}
        for race in races:
            for f in self._pool.get((race, sex), []):
                k = self.gd.key(f)
                if k not in self._used:
                    self._used.add(k)
                    return f
        return None

    def edid_of(self, key):
        if key.startswith('+'):
            r = self.pr.records.get(key)
            return (recordio.field(r, 'EDID') or '') if r else ''
        try:
            return self.gd.edid(self.gd.from_key(key)) or ''
        except (KeyError, ValueError):
            return ''

    def of(self, *names):
        return [p for n in names for _ck, p in self.refs.get(n, [])]

    def by_edid(self, edid, tags=('NPC_', 'CREA', 'LVLC', 'LVLN')):
        """(tag, form) of the game's form of this editor ID among tags, or None: the game read once for every lookup."""
        if not hasattr(self, '_index'):
            self._index = {}
            for f, (_i, r) in self.gd.forms.items():
                if r.tag in ('NPC_', 'CREA', 'LVLC', 'LVLN', 'IDLM', 'STAT', 'PACK'):
                    self._index.setdefault((self.gd.edid(f) or '', r.tag), f)
        for t in tags:
            f = self._index.get((edid, t))
            if f is not None:
                return t, f
        return None

    def game(self, tag, edid):
        hit = self.by_edid(edid, (tag,)) if tag in ('NPC_', 'CREA', 'LVLC', 'LVLN', 'IDLM', 'STAT', 'PACK') else None
        if hit:
            return self.gd.key(hit[1])
        f = next((f for f, (_i, r) in self.gd.forms.items() if r.tag == tag and self.gd.edid(f) == edid), None)
        if f is None:
            raise ValueError('the game has no %s %s' % (tag, edid))
        return self.gd.key(f)

    def cell(self, x, y):
        c = self.grid.get((int(x // 4096), int(y // 4096)))
        return self.gd.key(c) if c is not None else None

    def safe_from(self, x, y):
        """Whether a hostile may stand here: out of Waikiki and away from the start."""
        if math.hypot(x - self.mid[0], y - self.mid[1]) < self.WAIKIKI_R:
            return False
        return not (self.start[0] is not None and math.hypot(x - self.start[0], y - self.start[1]) < self.SAFE)

    def spot(self, x, y, apart=160.0):
        """(x, y, z) open ground with a navmesh under it near (x, y), or None."""
        import factionfolk as ff
        z = self.sp.stand(x, y, apart=apart)
        if z is None:
            return None
        if not ff._on_mesh(self.sp, x, y, z):
            self.sp.taken.pop()
            return None
        return (x, y, z)

    def around(self, x, y, want, radii=(150, 250, 350, 500), turns=10, apart=160.0):
        out = []
        for r in radii:
            for t in range(turns):
                a = (t + 0.41 * (r // 100)) * 2 * math.pi / turns
                s = self.spot(x + r * math.sin(a), y + r * math.cos(a), apart)
                if s:
                    out.append(s)
                    if len(out) >= want:
                        return out
        return out

    def deck(self, p):
        """The walkable top of a pier piece at p (x, y, z), or None: a solid top near its height, a navmesh on it."""
        import factionfolk as ff
        x, y = p[0], p[1]
        self.sp.S.load(x, y)
        tops = [z for z, _r in self.sp.S.solids.tops(x, y) if p[2] - 80 < z < p[2] + 120]
        if not tops:
            return None
        z = max(tops)
        if any(math.hypot(x - a, y - b) < 160 for a, b in self.sp.taken):
            return None
        if not ff._on_mesh(self.sp, x, y, z):
            return None
        self.sp.taken.append((x, y))
        return (x, y, z)


def clusters(pts, reach=CLUSTER):
    """Groups of points each within reach of another in the group: [[p]] largest first."""
    left = list(pts)
    out = []
    while left:
        group = [left.pop()]
        grew = True
        while grew:
            grew = False
            for p in list(left):
                if any(math.hypot(p[0] - q[0], p[1] - q[1]) < reach for q in group):
                    group.append(p)
                    left.remove(p)
                    grew = True
        out.append(group)
    out.sort(key=len, reverse=True)
    return out


def middle_of(group):
    return (sum(p[0] for p in group) / len(group), sum(p[1] for p in group) / len(group))


def facing(frm, to):
    return math.atan2(to[0] - frm[0], to[1] - frm[1])


# ---------- what goes in ----------

class _Reserve:
    """Records of the mod's own with their keys taken as they're planned ('record' ops): every part's ops can then go
    in together, whatever order they're applied in."""

    def __init__(self, pr):
        self.pr = pr
        self.ops = []

    def add(self, rec):
        k = _new_key(self.pr)
        self.ops.append({'op': 'record', 'key': k, 'record': rec})
        return k


class Out:
    def __init__(self, ctx):
        self.ctx = ctx
        self.keys = _Reserve(ctx.pr)
        self.ops = []
        self.made = {}
        self.count = {}

    def kind(self, name):
        """The record of a new kind of person (KINDS), made once."""
        if name in self.made:
            return self.made[name]
        import waikikilife as WL
        edid, label, src, package = KINDS[name]
        if edid in self.ctx.edids:
            raise ValueError('the mod already has %s: this part looks done (Undo it first)' % edid)
        sk = self.ctx.edids.get(src)
        if not sk:
            raise ValueError('the mod has no %s' % src)
        rec = WL._person(self.ctx.gd, self.ctx.pr, self.ctx.pr.records[sk], edid, label, package)
        rec['copied_from'] = sk
        self.made[name] = self.keys.add(rec)
        return self.made[name]

    def add(self, base, x, y, z, rz=0.0, what='', extra=None):
        ck = self.ctx.cell(x, y)
        if ck is None:
            return False
        op = {'op': 'add', 'cell': ck, 'base': base, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0}
        if extra:
            op['extra'] = extra
        self.ops.append(op)
        if what:
            self.count[what] = self.count.get(what, 0) + 1
        return True

    def marker(self, which, x, y, z, rz):
        return self.add(self.ctx.game('IDLM', MARKERS[which]), x, y, z, rz, 'marker: ' + which)

    def person(self, name, x, y, z, rz):
        return self.add(self.kind(name), x, y, z + 4, rz, name)

    def person_rec(self, key, x, y, z, rz, what):
        return self.add(key, x, y, z + 4, rz, what)

    def done(self, report):
        report['added'] = dict(self.count)
        report['records'] = len(self.keys.ops)
        return self.keys.ops + self.ops, report


# ---------- the parts ----------

def market(ctx):
    o = Out(ctx)
    rep = {'places': []}
    groups = clusters(ctx.of(*STALLS))
    huang = ctx.of('FOLabSettlerScreen', *GATES)
    for g in groups:
        if len(rep['places']) >= MARKET_MOST:
            break
        mx, my = middle_of(g)
        if any(math.hypot(mx - p[0], my - p[1]) < 6000 for p in huang):
            continue                            # (the Huáng trade at their gate, not at these stalls)
        inside = math.hypot(mx - ctx.mid[0], my - ctx.mid[1]) < ctx.WAIKIKI_R
        if inside and sum(1 for p in rep['places'] if p[4]) >= MIDDLE_MARKETS:
            continue
        spots = ctx.around(mx, my, 4, radii=(180, 280, 380, 520))
        if len(spots) < 2:
            continue
        sx, sy, sz = spots[0]
        o.marker('sell', sx, sy, sz, facing((sx, sy), (mx, my)))
        o.person('seller', sx, sy, sz, facing((sx, sy), (mx, my)))
        for k, (bx, by, bz) in enumerate(spots[1:]):
            o.marker('shop', bx, by, bz, facing((bx, by), (mx, my)))
            if k < (1 if inside else 2):
                o.person('buyer', bx, by, bz, facing((bx, by), (mx, my)))
        rep['places'].append([round(mx), round(my), len(g), len(spots), inside])
    return o.done(rep)


def piers(ctx):
    o = Out(ctx)
    rep = {'places': []}
    pirates = [p for n, ps in ctx.refs.items() if n.startswith('FOLabPirate') for _c, p in ps]
    for g in clusters(ctx.of(*DOCK), reach=700.0):
        if len(rep['places']) >= PIER_MOST or len(g) < 6:
            continue
        mx, my = middle_of(g)
        if any(math.hypot(mx - p[0], my - p[1]) < 4000 for p in pirates):
            continue                            # (no fishing where the pirates are)
        # the pier's far end: the pieces farthest from where it meets the land
        land = min(g, key=lambda p: (ctx.sp.G.at(p[0], p[1]) or -9999) * -1)
        far = sorted(g, key=lambda p: -math.hypot(p[0] - land[0], p[1] - land[1]))
        got = []
        for p in far[:8]:
            d = ctx.deck(p)
            if d:
                got.append(d)
            if len(got) >= 2:
                break
        if not got:
            continue
        out_to = lambda q: facing(land, q)
        x, y, z = got[0]
        o.marker('mend', x, y, z, out_to((x, y)))
        o.person('fisher', x, y, z, out_to((x, y)))
        if len(got) > 1:
            x2, y2, z2 = got[1]
            o.marker('watch', x2, y2, z2, out_to((x2, y2)))
        rep['places'].append([round(mx), round(my), len(g), len(got)])
    return o.done(rep)


def pirates(ctx):
    o = Out(ctx)
    rep = {'places': []}
    crew = [p for n, ps in ctx.refs.items() if n.startswith('FOLabPirate') for _c, p in ps]
    for g in clusters(ctx.of(*BOATS), reach=1200.0):
        if len(rep['places']) >= PIRATE_MOST:
            break
        mx, my = middle_of(g)
        if not ctx.safe_from(mx, my) or not any(math.hypot(mx - p[0], my - p[1]) < 3000 for p in crew):
            continue                            # (only where pirates already hold the shore)
        spots = ctx.around(mx, my, 3, radii=(250, 400, 550, 750, 950))
        if len(spots) < 2:
            continue
        for k, (x, y, z) in enumerate(spots):
            o.marker(('repair', 'yard', 'smoke')[k], x, y, z, facing((x, y), (mx, my)))
        for x, y, z in spots[:2]:
            o.person('dockhand', x, y, z, facing((x, y), (mx, my)))
        rep['places'].append([round(mx), round(my), len(g), len(spots)])
    return o.done(rep)


FARMERS = (('F', 3), ('M', 1), ('F', 2))     # (per field: the faces left free are mostly women's: 21 Nov 2026)
FIELD_NEAR = 9000.0                         # (maize this near the Huáng's gates and courtyards is theirs)


def farms(ctx):
    """The Huáng in their maize: the fields lie ~3 km from the courtyards, farther than anyone wanders, so a few Nongmin
    of their own live in the fields (faces not used before, as factionfolk's), working the rows by the game's raking,
    watering and yardwork markers; the courtyards' Nongmin stay as they are."""
    import factionfolk as ff
    o = Out(ctx)
    rep = {'places': []}
    gd, pr = ctx.gd, ctx.pr
    if 'FOLabHuangFarmer01' in ctx.edids:
        raise ValueError('the mod already has the farmers (Undo them first)')
    home = ctx.of('FOLabSettlerScreen', *GATES)
    maize = [p for p in ctx.of(*MAIZE) if any(math.hypot(p[0] - q[0], p[1] - q[1]) < FIELD_NEAR for q in home)]
    g = ff.GROUPS['huang_folk']
    fac = ff._mod_key(pr, ff.FACTIONS['huang'][0], 'FACT')
    n = 0
    for field, (sex, count) in zip(clusters(maize, reach=700.0), FARMERS):
        mx, my = middle_of(field)
        rows = sorted(field, key=lambda p: math.hypot(p[0] - mx, p[1] - my))
        spots = []
        for p in rows:
            sp = ctx.spot(p[0] + 90, p[1], apart=200.0) or ctx.spot(p[0] - 90, p[1], apart=200.0)
            if sp:
                spots.append((sp, p))
            if len(spots) >= count + 1:
                break
        if len(spots) < 2:
            continue
        for k, (sp, row) in enumerate(spots):
            o.marker(('rake', 'water', 'yard')[k % 3], sp[0], sp[1], sp[2], facing(sp[:2], row[:2]))
        made = 0
        for sp, row in spots[:count]:
            face = ctx.free_face(('Asian',), sex)
            if face is None:
                break
            n += 1
            items = [(ff._item(gd, pr, e), 1) for e in g['wear'][sex]]
            rec = ff.person(gd, pr, face, 'FOLabHuangFarmer%02d' % n, g['name'], dict(g, package='DefaultSandboxEditorLocation512'), items, [], fac)
            o.person_rec(o.keys.add(rec), sp[0], sp[1], sp[2], facing(sp[:2], row[:2]), 'farmer')
            made += 1
        rep['places'].append([round(mx), round(my), len(field), made])
    return o.done(rep)


def _new_key(pr):
    """A key of the mod's own taken now (records and refs that name each other: worldrec.patrol_ops does the same)."""
    k = '+%06X' % pr.next_id
    pr.next_id += 1
    return k


def _patrol_ring(ctx, o, walker_key, pts):
    keys = [_new_key(ctx.pr) for _ in pts]
    xmh = ctx.game('STAT', 'XMarkerHeading')
    for n, (x, y, z) in enumerate(pts):
        o.ops.append({'op': 'place', 'cell': ctx.cell(x, y), 'key': keys[n],
                      'ref': {'base': xmh, 'p': [x, y, z, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True,
                              'patrol_wait': PATROL_WAIT, 'link': keys[(n + 1) % len(keys)]}})
    x, y, z = pts[0]
    o.ops.append({'op': 'place', 'cell': ctx.cell(x, y), 'key': _new_key(ctx.pr),
                  'ref': {'base': walker_key, 'p': [x, y, z + 16, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'link': keys[0]}})
    o.count['patrol walker'] = o.count.get('patrol walker', 0) + 1
    o.count['patrol point'] = o.count.get('patrol point', 0) + len(pts)


def patrols(ctx):
    """Every key here is taken as it's planned (records with 'record', refs with 'place'), as worldrec.patrol_ops does:
    plan and apply together."""
    import factionfolk as ff
    import worldrec
    o = Out(ctx)
    rep = {'rings': []}
    gd, pr = ctx.gd, ctx.pr
    if 'FOLabPatrolCourt01' in ctx.edids:
        raise ValueError('the mod already has the patrols (Undo them first)')
    prec = recordio.load(gd, worldrec._patrol_package(gd))
    recordio.set_field(prec, 'EDID', 'FOLabPatrolPackage', label='Editor ID')
    pack = _new_key(pr)
    o.ops.append({'op': 'record', 'key': pack, 'record': prec})
    def walker(group, edid, races, sex):
        g = ff.GROUPS[group]
        face = ctx.free_face(races, sex)
        if face is None and group == 'huang_guard':
            sex = 'F'                               # (the Shouwei have women too: the men's faces are used up)
            face = ctx.free_face(races, sex)
        if face is None:
            return None
        items = [(ff._item(gd, pr, e), 1) for e in g['wear'][sex]]
        arm = ff._mod_key(pr, g['arms'][0], 'WEAP')
        if arm:
            items.append((arm, 1))
        fac = ff._mod_key(pr, ff.FACTIONS['court' if group.startswith('court') else 'huang'][0], 'FACT')
        rec = ff.person(gd, pr, face, edid, g['name'], g, items, [], fac)
        for s in rec['subs']:
            if s['tag'] == 'PKID':
                s['value'] = pack
        k = _new_key(pr)
        o.ops.append({'op': 'record', 'key': k, 'record': rec})
        return k

    # the court: rings of three or four lookouts round Waikiki, each walked by one fighter
    looks = [p for p in ctx.of(*LOOKOUTS) if math.hypot(p[0] - ctx.mid[0], p[1] - ctx.mid[1]) < ctx.WAIKIKI_R * 1.3]
    rings = []
    left = sorted(looks, key=lambda p: math.atan2(p[0] - ctx.mid[0], p[1] - ctx.mid[1]))
    while len(left) >= 3 and len(rings) < 3:
        ring, left = left[:4], left[4:]
        rings.append(ring)
    for n, ring in enumerate(rings):
        pts = []
        for p in ring:
            s = ctx.around(p[0], p[1], 1, radii=(200, 300, 420, 560), turns=12, apart=120.0)
            if s:
                pts.append(s[0])
        if len(pts) < 2:
            continue
        w = walker('court_fighter', 'FOLabPatrolCourt%02d' % (n + 1), ('Caucasian', 'Hispanic', 'AfricanAmerican'), 'M')
        if w:
            _patrol_ring(ctx, o, w, pts)
            rep['rings'].append(['court', len(pts), [[round(q[0]), round(q[1])] for q in pts]])
    # the Huáng: along the road of gates, out and back
    gates = ctx.of(*GATES)
    if len(gates) >= 2:
        pts = []
        for p in sorted(gates, key=lambda p: (p[0], p[1])):
            s = ctx.around(p[0], p[1], 1, radii=(250, 350, 500), turns=12, apart=120.0)
            if s:
                pts.append(s[0])
        if len(pts) >= 2:
            for n in range(2):
                w = walker('huang_guard', 'FOLabPatrolShouwei%02d' % (n + 1), ('Asian',), 'M')
                if w:
                    _patrol_ring(ctx, o, w, pts if n == 0 else list(reversed(pts)))
                    rep['rings'].append(['huang', len(pts), [[round(q[0]), round(q[1])] for q in pts]])
    return o.done(rep)


def fires(ctx):
    o = Out(ctx)
    rep = {'fires': 0}
    people = [p for n, ps in ctx.refs.items() if n.startswith('FOLab') and ('Local' in n or 'Huang' in n or 'Surfer' in n or 'Kuli' in n)
              for _c, p in ps]
    for p in ctx.of(*FIRES):
        if rep['fires'] >= FIRE_MOST:
            break
        if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < PEOPLE_NEAR for q in people):
            continue
        s = ctx.around(p[0], p[1], 1, radii=(70, 100, 130), turns=10, apart=60.0)
        if s:
            x, y, z = s[0]
            o.marker('fire', x, y, z, facing((x, y), p[:2]))
            rep['fires'] += 1
    return o.done(rep)


def kids(ctx):
    import factionfolk as ff
    o = Out(ctx)
    rep = {'places': []}
    lvln = ctx.game('LVLN', CHILDREN)
    mk = ff._markers(ctx.pr)
    for name in ('royal',):
        hx, hy = mk[ff.MARKERS[name]][1][:2]
        for x, y, z in ctx.around(hx, hy, CHILDREN_MOST, radii=(900, 1200, 1500, 1800), turns=14, apart=300.0):
            o.add(lvln, x, y, z + 4, 0.0, 'child')
            rep['places'].append([round(x), round(y)])
    return o.done(rep)


def roads(ctx):
    """A few roadside encounters away from towns: pirates by the road on their coast (out of Waikiki and the start's reach)."""
    o = Out(ctx)
    rep = {'places': []}
    road = [p for n, ps in ctx.refs.items() if 'road' in n.lower() and n.startswith('FOLab') for _c, p in ps]
    people = [p for n, ps in ctx.refs.items() if n.startswith('FOLab') for _c, p in ps if n in ctx.edids and
              ctx.pr.records[ctx.edids[n]].get('type') == 'NPC_']
    crew = [p for n, ps in ctx.refs.items() if n.startswith('FOLabPirate') for _c, p in ps]
    road.sort(key=lambda p: (round(p[0] / 8000), round(p[1] / 8000)))
    taken = []
    for p in road:
        if len(rep['places']) >= ROAD_MOST:
            break
        x, y = p[0], p[1]
        if not ctx.safe_from(x, y) or any(math.hypot(x - q[0], y - q[1]) < 3000 for q in people if q not in crew):
            continue
        if not any(math.hypot(x - q[0], y - q[1]) < 9000 for q in crew):
            continue                            # (pirates' coast only)
        if any(math.hypot(x - a, y - b) < 9000 for a, b in taken):
            continue
        spots = ctx.around(x, y, 2, radii=(350, 500, 650), turns=10)
        if len(spots) < 2:
            continue
        for sx, sy, sz in spots:
            o.person('roadside', sx, sy, sz, facing((sx, sy), (x, y)))
        o.marker('smoke', spots[0][0], spots[0][1], spots[0][2], facing(spots[0][:2], (x, y)))
        taken.append((x, y))
        rep['places'].append([round(x), round(y)])
    return o.done(rep)


WILD_MOST = 40
WILD_CLEAR = 3600.0                         # (no group this near a creature already there: only where it's thin)
PEOPLE_CLEAR = 4000.0                       # (nor this near people)
HIGH = 900.0                                # (ground over this is the jungle-clad ridges: 'trees'; under, 'grass')


def wildlife(ctx):
    """Creatures where the island has none: worldlife's groups by ground and distance from the start (its tiers), in land
    cells with nothing within WILD_CLEAR, away from people, Waikiki, the start and the Huáng's land, on open ground with
    a navmesh."""
    import worldlife
    o = Out(ctx)
    rep = {'places': [], 'who': {}}
    gd = ctx.gd
    kinds = {}

    def is_actor(e, want):
        if e not in kinds:
            k = ctx.edids.get(e)
            if k:
                kinds[e] = ctx.pr.records[k].get('type', '')
            else:
                hit = ctx.by_edid(e)
                kinds[e] = hit[0] if hit else ''
        return kinds[e] in want
    names = list(ctx.refs)
    creatures = [p for e in names if is_actor(e, ('CREA', 'LVLC')) for _c, p in ctx.refs[e]]
    people = [p for e in names if is_actor(e, ('NPC_', 'LVLN')) for _c, p in ctx.refs[e]]
    home = ctx.of('FOLabSettlerScreen', *GATES)
    start = ctx.start if ctx.start[0] is not None else ctx.mid
    cells = sorted(ctx.grid)
    rng = __import__('random').Random(7)
    rng.shuffle(cells)
    for cx, cy in cells:
        if len(rep['places']) >= WILD_MOST:
            break
        x, y = (cx + 0.5) * 4096.0, (cy + 0.5) * 4096.0
        z = ctx.sp.G.at(x, y)
        if z is None or z < 16 or not ctx.safe_from(x, y):
            continue
        if any(math.hypot(x - p[0], y - p[1]) < WILD_CLEAR for p in creatures) \
                or any(math.hypot(x - p[0], y - p[1]) < PEOPLE_CLEAR for p in people) \
                or any(math.hypot(x - p[0], y - p[1]) < 6000 for p in home) \
                or any(math.hypot(x - a, y - b) < WILD_CLEAR for a, b in rep['places']):
            continue
        spots = ctx.around(x, y, 3, radii=(0.1, 200, 350, 500), turns=8, apart=150.0)
        if len(spots) < 2:
            continue
        d = max(abs(cx - int(start[0] // 4096)), abs(cy - int(start[1] // 4096)))
        tier = max(n for n, (frm, _lvl) in enumerate(worldlife.TIERS) if d >= frm)
        ground = 'trees' if z > HIGH else 'grass'
        if rng.random() < 0.35:
            ground = 'grass' if ground == 'trees' else 'trees'      # (a mix: the ridges' edges and the lowland's woods)
        rows = worldlife.IN_THE_WILD[ground][rng.randint(0, tier)]  # (any tier up to the place's: not all the hardest)
        k = 0
        for e, count in rows:
            hit = ctx.by_edid(e)
            if hit is None:
                continue
            f = hit[1]
            for _n in range(count):
                sx, sy, sz = spots[k % len(spots)]
                a = rng.uniform(0, 2 * math.pi)
                o.add(gd.key(f), sx + 60 * math.sin(a) * (k // len(spots)), sy + 60 * math.cos(a) * (k // len(spots)), sz + 4,
                      rng.uniform(0, 2 * math.pi), 'creature')
                rep['who'][e] = rep['who'].get(e, 0) + 1
                k += 1
        rep['places'].append([round(x), round(y)])
    return o.done(rep)


def ops(gd, pr, part, ctx=None):
    if part not in PARTS:
        raise ValueError('no such part: %s' % part)
    return globals()[part](ctx or Ctx(gd, pr))


LABELS = {'market': 'Market sellers and buyers', 'piers': 'Fishers on the piers', 'pirates': 'Pirates at their boats',
          'farms': "The Huáng in their fields", 'patrols': 'Guards on patrol', 'fires': 'Warming by the fire barrels',
          'kids': 'Children by the hotels', 'roads': 'Pirates by the road', 'wildlife': 'Creatures where the island had none'}


def apply(server, part):
    o, rep = ops(server.GD, server.PR, part)
    server.PR.apply(LABELS[part], o)            # (not server.edit: its cell filing takes a 'place' op's ref for a key)
    return rep


def resign(gd, pr, cells):
    """'navmesh' ops for the outside cells given whose mesh was current before (`cells`: {cell: True if it was}): the new
    fingerprint on the same mesh. People and idle markers have no collision and navgen takes people only as starting
    points, so the mesh is what a fresh run would make; without this, every cell with someone new reads out of date."""
    import navbuild
    out = []
    for ck, was in cells.items():
        mine = pr.navmesh.get(ck)
        if not was or not mine or mine.get('copy'):
            continue
        refs = navbuild.place_refs(gd, pr, ck)
        mesh = dict(mine, sig=navbuild.outside_signature(pr, ck, refs))
        out.append({'op': 'navmesh', 'cell': ck, 'mesh': mesh})
    return out


def apply_all(server, parts=PARTS, surf=True, files_root=None):
    """Every part planned on one Ctx (so none stands on another's spot), with surfing and fishing (surffish) when surf,
    applied as one Undo, the navmeshes of the cells they touch re-signed in the same Undo. The surfboards' files go among
    the mod's own (files_root: elsewhere, for a rehearsal) before it. Returns {part: report}."""
    import library
    import navbuild
    gd, pr = server.GD, server.PR
    ctx = Ctx(gd, pr)
    all_ops, reps, files = [], {}, {}
    for part in parts:
        o, rep = ops(gd, pr, part, ctx)
        all_ops += o
        reps[part] = rep
    if surf:
        import surffish
        o, files, rep = surffish.ops(gd, pr, ctx)
        all_ops += o
        reps['surf and fish'] = rep
    root = files_root or library.assets_dir(pr)
    for rel, data in files.items():
        library._put(root, rel, data)
    cells = {op['cell'] for op in all_ops if op.get('cell') and op['op'] in ('add', 'place')}
    # (a thing with collision of the mod's own, a surfboard, changes what can be walked: its cells are left out of date,
    # for a fresh navmesh, as "navmesh last, walk first")
    solid = {op['key'] for op in all_ops if op['op'] == 'record' and op['record'].get('type') == 'STAT'}
    remake = sorted({op['cell'] for op in all_ops if op['op'] == 'add' and op.get('base') in solid})
    current = {ck: bool(pr.navmesh.get(ck)) and navbuild.status(gd, pr, ck).get('current', False) and ck not in remake for ck in cells}
    pr.apply("People doing things: markets, piers, pirates, farms, patrols, fires, children, roads, wildlife, surfing, fishing", all_ops)
    sign = resign(gd, pr, current)
    if sign:
        pr.apply('(their navmeshes re-signed)', sign, merge=True)
    reps['navmesh'] = {'cells': len(cells), 're-signed': len(sign), 'remake (new solid things)': remake,
                       'were not current': sum(1 for ck, v in current.items() if not v and ck not in remake)}
    return reps
