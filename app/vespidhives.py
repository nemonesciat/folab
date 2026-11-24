"""The Vespids' hives in a world (docs/waikiki-pacing-plan.md section 6; the user, 23 Nov 2026): nests on the Ko'olau's
ridges and high valleys, the Vespids only round them, every hive a place to go into (the user: "all the hives were to be
dungeons ... one big big dungeon and the other small, but they should all be locations"), ended by killing its queen,
looted, antidotes easy to get.

Records (all the mod's own):
    Vespid, Vespid Queen, Vespid Brood Queen   vespid.creature: the cazador's record, the body painted as a yellowjacket.
                              The Vespid respawns as the game's cazadores do (ACBS respawn flag) while its hive stands;
                              the queens (the great hive's, a small hive's) don't, and their death ends their hive
                              (`QUEEN_SCRIPT`: her enable parent is the hive's life marker, switched off)
    Vespid Poison Gland       the cazador's gland renamed; the Vespid's death item gives it a third of the time, as the game's
    Rad Honey                 the hives' common find: food (the cazador egg's effects, more), some trade value
    Glowing Royal Jelly       the great hive's rare find (worth 250, only there), for Royal Jelly Tonic (a Buffout of the
                              island's own), Hive Fire (a Rocket: jelly and a Vespid's gland) and Rad Honey Cake
    Antivenom (island herbs)  a campfire recipe of the game's Antivenom (which dispels the cazador's poison the Vespid keeps)
                              from a Xander root and a broc flower, both growing wild on the island
    antivenom kit             the game's first aid kit with two Antivenom more: one at each ridge place's campfire
    hive cache                the game's military footlocker the hive grew round, outside: Rad Honey and Antivenom, locked
                              until the hive dies; the queens' own caches inside (royal jelly only in the great one's)
    hive models               STATs: each kind alive and burnt (hiveset: ruin, cliff, hill, great)
    quest FOLabVespidHives    its script watches the hives: a hive's life marker off means it burns, fire for half a day,
                              the cache unlocked, and once the player is out of sight its Vespids are gone for good
    the doctor's chest        FOLabWaikikiDoctorChest gets four Antivenom (the Waikiki doctor sells them)

Each hive (`sites`) stands where the land is high (`HIGH`), far from any map marker (`CLEAR`, `WIDE`), any door that
leads somewhere and its arrival, what marks a walked way, named refs (`keep_off`), roads, and the other hives (`APART`):
on a mountain top a 'hill' hive, in a high valley over a ruin a 'ruin' one, set into a steep hillside a 'cliff' one
(`CLIFF_ROOM`), the 'great' one on the best spot of all. Its mouth faces downhill, a salvaged door in it into the hive's
own inside (vespidcave: the great one's big, the rest small, every one walked and closed as a solid), a map marker in
front found when you come near. Markers a hive: life (the hive alive; the burnt hive opposite; the queen's parent), pool
(its Vespids) and fire (off until it burns).

    build(server)       sites, insides, files, one Undo
"""
import json
import math
import random

QUEST = 'FOLabVespidHives'
QUEST_SCRIPT = 'FOLabVespidHivesScript'
QUEEN_SCRIPT = 'FOLabVespidQueenScript'
LIFE, POOL, FIRE, CACHE = 'FOLabHiveLife%02d', 'FOLabHivePool%02d', 'FOLabHiveFire%02d', 'FOLabHiveCache%02d'
MARKER = 'XMarker'
GAME_FIRE = 'FXFireSmall01'
FIRE_SCALE = 2.4
FIRE_HOURS = 12.0
AWAY = 6000.0               # (the player this far from a burnt hive: its Vespids are gone)
RESPAWN = 0x8               # (ACBS flag: as the game's cazadores that come back)

HIGH = 4500.0               # (land this high or over: the ridges and the high valleys)
CLEAR = 5000.0              # (from any map marker: a hive is a place of its own, not in a camp)
WIDE = {"Ka'au Crater": 9500.0}  # (markers whose place is wide: the whole crater, Vault 50's climb and door in it)
DOOR_CLEAR = 4000.0         # (from any door that leads somewhere: the vault's gear door, cave mouths, doors in the rock)
WALKED_CLEAR = 2500.0       # (from what marks a way people walk: trail signs, rock-door frames, the climbs' rails)
WALKED = ('NVDLC02signPostTall', 'NVDLC02trailSnHike', 'CaveExitDoorFrame', 'GuardRail')   # (editor IDs, by their start)
CAIRN = ('NVDLC02RockCanyon13', 'NVDLC02RockCanyon12', 'NVDLC02RockCanyon06')    # (cresttrail.CAIRN: a stack of these marks the trail)
CAIRN_TOGETHER = 150.0      # (the stack's rocks this near one another)
QUEST_CLEAR = 3000.0        # (from a named ref: what quests point at, the spots their scripts move people to)
CREST_Z = 15000.0           # (the Crest Trail's signposts this high are on the crest itself: the trail runs from one to the next)
CREST_GAP = 22000.0         # (two crest signposts further apart than this aren't one stretch of trail)
ROAD_CLEAR = 1200.0
APART = 11000.0
LEVEL_ROOM = 360.0          # (the most the ground may rise across a hive's foot: more is buried in the hill)
COUNT = {'great': 1, 'ruin': 2, 'cliff': 2, 'hill': 2}
POOL_SIZE = {'great': 6, 'ruin': 4, 'cliff': 4, 'hill': 4}
CLIFF_ROOM = 1100.0         # (a hillside steep enough to set a hive into: the ground rises this much at most across its foot)
MARKER_TYPE = 5             # (a cave's map marker, as Pele's Pipe's)
MARKER_FOUND = 2            # (shown once found, when you come near)
POOL_RING = (650.0, 1100.0)
SEED = 23

DOCTOR_CHEST = 'FOLabWaikikiDoctorChest'
DOCTOR_ANTIVENOM = 4
KIT_ANTIVENOM = 2
CACHE_JELLY, CACHE_ANTIVENOM = 2, 1
CACHE_LOCK = 50             # (lock level: average)
RIDGE_CAMPS = ('Alewa Fort', 'Pacific Heights Beacon', 'The Heights', "Watcher's Hut", 'The Tanks', 'The Holdouts',
               'Radar Dome', 'Loa Gate', "Crow's Nest", "Settlers' Watchtower")
CAMPFIRE = 'CampfireCrafting03'
HERBS = ('XanderRoot', 'BrocFlower')
RECIPE_SKILL = 15


# ---------- small helpers ----------

def _game(gd, tag, edid):
    got = [f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid]
    if not got:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return min(got, key=lambda f: f >> 24)


def _copy(gd, tag, edid):
    import recordio
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, tag, edid))))
    rec['src'] = ''
    return rec


def _set(rec, tag, value):
    for s in rec['subs']:
        if s['tag'] == tag:
            s['value'] = value
            return rec
    raise KeyError(tag)


def _field(rec, tag, name, value):
    for s in rec['subs']:
        if s['tag'] == tag:
            for f in s['fields']:
                if f.get('name') == name:
                    f['value'] = value
                    return rec
    raise KeyError((tag, name))


def _add_items(rec, items, template=None):
    """CNTO entries (laid out as the record's own first one, or `template`'s) put after its last one."""
    subs = rec['subs']
    t = template or next(s for s in subs if s['tag'] == 'CNTO')
    at = max(i for i, s in enumerate(subs) if s['tag'] == 'CNTO')
    for k, (key, n) in enumerate(items):
        new = json.loads(json.dumps(t))
        for f in new['fields']:
            if f.get('name') == 'Item':
                f['value'] = key
            elif f.get('name') == 'Count':
                f['value'] = n
        subs.insert(at + 1 + k, new)
    return rec


def _stat(edid, model, box, far=False):
    import modelsets
    return modelsets._static(edid, model, box, modelsets.VWD if far else 0)


def _message(edid, words):
    """A message in the corner (not a box)."""
    return {'type': 'MESG', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'DESC', 'label': 'Description', 'kind': 'z', 'value': words},
        {'tag': 'INAM', 'label': 'Icon', 'kind': 'F', 'value': ''},
        {'tag': 'DNAM', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'I', 'value': 0}]},
        {'tag': 'TNAM', 'label': 'Seconds shown', 'kind': 'struct', 'fields': [{'name': 'Seconds', 'code': 'I', 'value': 2}]}]}


# ---------- records ----------

def gland(gd):
    rec = _copy(gd, 'MISC', 'CazadorPoisonGland')
    _set(rec, 'EDID', 'FOLabVespidGland')
    _set(rec, 'FULL', 'Vespid Poison Gland')
    return rec


def death_item(gd, gland_key):
    rec = _copy(gd, 'LVLI', 'LootCazadorGland35')
    _set(rec, 'EDID', 'FOLabDeathItemVespid')
    _field(rec, 'LVLO', 'Item', gland_key)
    return rec


def _food(gd, from_edid, edid, name, value, heal=None):
    rec = _copy(gd, 'ALCH', from_edid)
    _set(rec, 'EDID', edid)
    _set(rec, 'FULL', name)
    _field(rec, 'ENIT', 'Value', value)
    if heal:
        efit = [s for s in rec['subs'] if s['tag'] == 'EFIT']
        for f in efit[0]['fields']:
            if f.get('name') == 'Magnitude':
                f['value'] = heal[0]
            elif f.get('name') == 'Duration':
                f['value'] = heal[1]
    return rec


def rad_honey(gd):
    """The hives' common find: a food (the cazador egg's effects, more of them), worth some trade."""
    return _food(gd, 'CazadorEgg', 'FOLabRadHoney', 'Rad Honey', 30, (4, 12))


def royal_jelly(gd):
    """The great hive's rare find (the user, 23 Nov 2026: 'a unique reward for this dungeon'): food in a pinch, but worth
    most in the island's best cooking and drugs."""
    return _food(gd, 'CazadorEgg', 'FOLabGlowingRoyalJelly', 'Glowing Royal Jelly', 250, (8, 15))


def royal_tonic(gd):
    """A Buffout of the island's own, from the queen's jelly."""
    rec = _copy(gd, 'ALCH', 'Buffout')
    _set(rec, 'EDID', 'FOLabRoyalJellyTonic')
    _set(rec, 'FULL', 'Royal Jelly Tonic')
    _field(rec, 'ENIT', 'Value', 180)
    return rec


def hive_fire(gd):
    """A Rocket of the island's own: the queen's jelly and a Vespid's gland, an action point rush."""
    rec = _copy(gd, 'ALCH', 'Rocket')
    _set(rec, 'EDID', 'FOLabHiveFireDrug')
    _set(rec, 'FULL', 'Hive Fire')
    _field(rec, 'ENIT', 'Value', 150)
    for s in rec['subs']:
        if s['tag'] == 'EFIT':
            for f in s['fields']:
                if f.get('name') == 'Magnitude' and f['value'] == 30:
                    f['value'] = 40
            break
    return rec


def honey_cake(gd):
    return _food(gd, 'CazadorEgg', 'FOLabRadHoneyCake', 'Rad Honey Cake', 45, (6, 15))


def recipe_of(gd, edid, name, skill, ins, out_key, out_n=1):
    """A campfire recipe (laid out as the game's RecipeAntivenom): ins [(key, count)] -> out_key x out_n."""
    rec = _copy(gd, 'RCPE', 'RecipeAntivenom')
    _set(rec, 'EDID', edid)
    _set(rec, 'FULL', name)
    _field(rec, 'DATA', 'Level', skill)
    tl = next(s for s in rec['subs'] if s['tag'] == 'RCIL')
    tq = next(s for s in rec['subs'] if s['tag'] == 'RCQY')
    to = next(s for s in rec['subs'] if s['tag'] == 'RCOD')
    subs = [s for s in rec['subs'] if s['tag'] not in ('RCIL', 'RCQY', 'RCOD')]

    def qty(n):
        q = json.loads(json.dumps(tq))
        q['fields'][0]['value'] = n
        return q
    for k, n in ins:
        subs += [dict(json.loads(json.dumps(tl)), value=k), qty(n)]
    subs += [dict(json.loads(json.dumps(to)), value=out_key), qty(out_n)]
    rec['subs'] = subs
    return rec


def recipe(gd):
    rec = _copy(gd, 'RCPE', 'RecipeAntivenom')
    _set(rec, 'EDID', 'FOLabRecipeIslandAntivenom')
    _set(rec, 'FULL', 'Antivenom (island herbs)')
    _field(rec, 'DATA', 'Level', RECIPE_SKILL)
    tl = next(s for s in rec['subs'] if s['tag'] == 'RCIL')
    tq = next(s for s in rec['subs'] if s['tag'] == 'RCQY')
    to = next(s for s in rec['subs'] if s['tag'] == 'RCOD')
    subs = [s for s in rec['subs'] if s['tag'] not in ('RCIL', 'RCQY', 'RCOD')]

    def qty(n):
        q = json.loads(json.dumps(tq))
        q['fields'][0]['value'] = n
        return q
    for h in HERBS:
        subs += [dict(json.loads(json.dumps(tl)), value=gd.key(_game(gd, 'INGR', h) if _has(gd, 'INGR', h) else _game(gd, 'ALCH', h))), qty(1)]
    subs += [dict(json.loads(json.dumps(to)), value=gd.key(_game(gd, 'ALCH', 'NVAntivenom'))), qty(1)]
    rec['subs'] = subs
    return rec


def _has(gd, tag, edid):
    return any(r.tag == tag and gd.edid(f) == edid for f, (_i, r) in gd.forms.items())


def antivenom_kit(gd):
    rec = _copy(gd, 'CONT', 'LootFirstAidKitNV')
    _set(rec, 'EDID', 'FOLabAntivenomKit')
    return _add_items(rec, [(gd.key(_game(gd, 'ALCH', 'NVAntivenom')), KIT_ANTIVENOM)])


def cache(gd, jelly_key):
    rec = _copy(gd, 'CONT', 'Footlocker01MilitaryNV')
    _set(rec, 'EDID', 'FOLabVespidHiveCache')
    return _add_items(rec, [(jelly_key, CACHE_JELLY), (gd.key(_game(gd, 'ALCH', 'NVAntivenom')), CACHE_ANTIVENOM)])


def queen_script(msg_edid):
    return '\r\n'.join([
        'scn %s' % QUEEN_SCRIPT,
        '; FOLab: a Vespid hive\'s queen (vespidhives.py). Her death ends her hive: her enable parent is its life marker, which',
        '; the hives\' quest watches (fire, the cache unlocked, its Vespids gone once you are away).',
        'ref rLife',
        '',
        'Begin OnDeath',
        '\tset rLife to GetParentRef',
        '\tif rLife',
        '\t\tShowMessage %s' % msg_edid,
        '\t\trLife.Disable',
        '\tendif',
        'End', ''])


def quest_script(n, great):
    """great: which hive (1-based) is the great one, whose life ends with the queen."""
    L = ['scn %s' % QUEST_SCRIPT, '; FOLab: the Vespid hives (vespidhives.py). A hive whose life marker is off has burnt.',
         'short bQueenDead']
    L += ['short bBurnt%02d' % k for k in range(1, n + 1)]
    L += ['float fBurnt%02d' % k for k in range(1, n + 1)]
    L += ['', 'Begin GameMode']
    if great:
        L += ['\tif bQueenDead && %s.GetDisabled == 0' % (LIFE % great),
              '\t\t%s.Disable' % (LIFE % great),
              '\tendif']
    for k in range(1, n + 1):
        b, f = 'bBurnt%02d' % k, 'fBurnt%02d' % k
        L += ['\tif %s == 0' % b,
              '\t\tif %s.GetDisabled' % (LIFE % k),
              '\t\t\tset %s to 1' % b,
              '\t\t\tset %s to GameDaysPassed' % f,
              '\t\t\t%s.Enable' % (FIRE % k),
              '\t\t\t%s.Unlock' % (CACHE % k),
              '\t\tendif',
              '\telseif %s == 1' % b,
              '\t\tif GameDaysPassed - %s >= %.3f' % (f, FIRE_HOURS / 24.0),
              '\t\t\t%s.Disable' % (FIRE % k),
              '\t\t\tset %s to 2' % b,
              '\t\tendif',
              '\tendif',
              '\tif %s && %s.GetDisabled == 0' % (b, POOL % k),
              '\t\tif %s.GetDistance Player > %d' % (LIFE % k, AWAY),
              '\t\t\t%s.Disable' % (POOL % k),
              '\t\tendif',
              '\tendif']
    L += ['End', '']
    return '\r\n'.join(L)


# ---------- where ----------

def _markers(pr):
    out = []
    for c in pr.cells.values():
        for r in c.get('refs', {}).values():
            if r.get('marker') and not r.get('removed') and r.get('p'):
                m = r['marker']
                out.append(((m.get('name') if isinstance(m, dict) else str(m)) or '', r['p'][0], r['p'][1], r['p'][2]))
    return out


def _roads(gd, pr, world):
    """(x, y) of every road piece the mod placed in the world's cells (by editor ID)."""
    cells = {gd.key(c) for c in gd.grid(world).values()}
    names, out = {}, []
    for ck, c in pr.cells.items():
        if ck not in cells:
            continue
        for r in c.get('refs', {}).values():
            b = r.get('base')
            if not b or r.get('removed') or not r.get('p'):
                continue
            if b not in names:
                import birds
                names[b] = 'road' in birds._edid(gd, pr, b).lower()
            if names[b]:
                out.append((r['p'][0], r['p'][1]))
    return out


def _near(pts, x, y, d):
    return any((x - a) ** 2 + (y - b) ** 2 < d * d for a, b in pts)


def keep_off(gd, pr, world, why=False):
    """[(x, y, how far)] (why: and what it is): what a hive keeps away from besides roads. The story session's standing
    check (23 Nov 2026, after a hive stood on Ka'au Crater's floor by Vault 50's climb and door): trails, doors and their
    arrivals, climbs, cave mouths, quest spots and settlements, not only map markers:
      every map marker (settlements, camps, sights): CLEAR, or its WIDE reach (the whole of Ka'au Crater)
      every door that leads somewhere, and where it puts you: DOOR_CLEAR (the vault's gear door, cave and rock doors)
      what marks a walked way: trail signs, rock-door frames, climbs' rails (WALKED), the Crest Trail's cairns: WALKED_CLEAR
      every named ref (quests' spots, persistent markers): QUEST_CLEAR"""
    import birds
    out = [(x, y, WIDE.get(n, CLEAR), 'marker ' + n) for n, x, y, _z in _markers(pr)]
    cells = {gd.key(c) for c in gd.grid(world).values()}
    walked, rocks, crest = {}, [], []
    for ck, c in pr.cells.items():
        if ck not in cells:
            continue
        for rk, r in c.get('refs', {}).items():
            p, b = r.get('p'), r.get('base')
            if not p or not b or r.get('removed'):
                continue
            if r.get('tel'):
                out.append((p[0], p[1], DOOR_CLEAR, 'door ' + rk))
                q = (r['tel'] or {}).get('p')
                if q and cell_at(gd, world, q[0], q[1]):
                    out.append((q[0], q[1], DOOR_CLEAR, 'arrival of door ' + rk))
                continue
            if (r.get('extra') or {}).get('edid') or r.get('edid'):
                out.append((p[0], p[1], QUEST_CLEAR, 'named ref ' + str((r.get('extra') or {}).get('edid') or r.get('edid'))))
            if b not in walked:
                e = birds._edid(gd, pr, b)
                walked[b] = 'walk' if e.startswith(WALKED) else 'cairn' if e in CAIRN else None
            if walked[b] == 'walk':
                e = birds._edid(gd, pr, b)
                out.append((p[0], p[1], WALKED_CLEAR, 'way marker ' + e))
                if e == 'NVDLC02signPostTall' and p[2] >= CREST_Z:
                    crest.append((p[0], p[1]))
            elif walked[b] == 'cairn':
                rocks.append((p[0], p[1]))
    # (a cairn: three of its rocks stood together; a lone canyon rock is only a rock)
    for x, y in rocks:
        if sum(1 for a_, b_ in rocks if (a_ - x) ** 2 + (b_ - y) ** 2 < CAIRN_TOGETHER ** 2) >= 3:
            out.append((x, y, WALKED_CLEAR, 'Crest Trail cairn'))
    # (the Crest Trail along the top: from one crest signpost to the next, east to west; its line isn't marked between)
    crest.sort()
    for (x0, y0), (x1, y1) in zip(crest, crest[1:]):
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln > CREST_GAP:
            continue
        for k in range(int(ln // 500) + 1):
            t = k * 500.0 / ln if ln else 0.0
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, WALKED_CLEAR, 'Crest Trail (between its signposts)'))
    return out if why else [o[:3] for o in out]


def nearest(gd, pr, world, x, y, spots=None):
    """[(what, distance, its own clearance)] of what a hive at x, y is nearest, a line per kind (for the hand-over)."""
    spots = spots if spots is not None else keep_off(gd, pr, world, why=True)
    best = {}
    for a_, b_, d, what in spots:
        kind = what.split(' ')[0] if not what.startswith(('marker', 'Crest')) else ('settlement or marker' if what.startswith('marker') else 'trail')
        dist = math.hypot(a_ - x, b_ - y)
        if kind not in best or dist < best[kind][1]:
            best[kind] = (what, round(dist), d)
    return best


def _clear_of(spots, x, y):
    return not any((x - a) ** 2 + (y - b) ** 2 < d * d for a, b, d in spots)


def sites(gd, pr, world, seed=SEED, step=1000.0, avoid=()):
    """[(kind, x, y, z, rz)]: where each hive stands and its turn (its mouth, -y, down the hill). avoid: more [(x, y, how
    far)] to keep away from (`keep_off` is always kept)."""
    import hiveset
    import roadgen
    g = roadgen.Ground(gd, pr, world)
    off = keep_off(gd, pr, world) + list(avoid)
    roads = _roads(gd, pr, world)
    xs = [k[0] for k in gd.grid(world)]
    ys = [k[1] for k in gd.grid(world)]
    cands = []
    for ix in range(int(min(xs) * 4096 / step), int((max(xs) + 1) * 4096 / step)):
        for iy in range(int(min(ys) * 4096 / step), int((max(ys) + 1) * 4096 / step)):
            x, y = ix * step, iy * step
            h = g.at(x, y)
            if h is None or h < HIGH:
                continue
            if not _clear_of(off, x, y) or _near(roads, x, y, ROAD_CLEAR):
                continue
            cands.append((x, y, h))
    rnd = random.Random(seed)
    rnd.shuffle(cands)

    def measure(x, y, r):
        ring = []
        for k in range(16):
            a = math.tau * k / 16
            hh = g.at(x + r * math.cos(a), y + r * math.sin(a))
            if hh is None:
                return None
            ring.append((hh, a))
        lo, hi = min(hh for hh, _a in ring), max(hh for hh, _a in ring)
        # (downhill: the way the ring is lowest, smoothed)
        dx = sum(-hh * math.cos(a) for hh, a in ring)
        dy = sum(-hh * math.sin(a) for hh, a in ring)
        far = [g.at(x + 3 * r * math.cos(math.tau * k / 16), y + 3 * r * math.sin(math.tau * k / 16)) for k in range(16)]
        if any(v is None for v in far):
            return None
        peak = g.at(x, y) >= max(far) - 60          # (nothing round it higher: a top)
        return lo, hi, (dx, dy), peak
    out, taken = [], []
    for kind in ('great', 'ruin', 'cliff', 'hill'):
        r0 = hiveset.KINDS[kind][2]
        scored = []
        for x, y, h in cands:
            if _near(taken, x, y, APART):
                continue
            m = measure(x, y, r0 * 0.9)
            if not m:
                continue
            lo, hi, down, peak = m
            if kind == 'cliff':
                if not (LEVEL_ROOM < hi - lo <= CLIFF_ROOM) or peak:
                    continue
            elif hi - lo > LEVEL_ROOM:
                continue
            if kind == 'hill' and not peak:
                continue
            if kind == 'ruin' and peak:
                continue
            # (the great one: the highest level ground; the rest: high, level, spread)
            score = h - (0.5 if kind == 'cliff' else 2.0) * (hi - lo)
            scored.append((score, x, y, lo, down))
        scored.sort(reverse=True)
        n = 0
        for score, x, y, lo, down in scored:
            if n >= COUNT[kind]:
                break
            if _near(taken, x, y, APART):
                continue
            dx, dy = down
            rz = math.atan2(-dx, -dy) % math.tau if (dx or dy) else 0.0
            out.append((kind, round(x, 1), round(y, 1), round(lo - 6.0, 1), round(rz, 4)))
            taken.append((x, y))
            n += 1
    return out


def world_of(x, y, cx, cy, rz):
    """A point of a thing's own frame (x, y) into the world, the thing at (cx, cy) turned rz (clockwise from above)."""
    c, s = math.cos(rz), math.sin(rz)
    return cx + x * c + y * s, cy - x * s + y * c


def cell_at(gd, world, x, y):
    grid = gd.grid(world)
    c = grid.get((math.floor(x / 4096.0), math.floor(y / 4096.0)))
    return gd.key(c) if c else None


def ridge_campfires(gd, pr, world):
    """{place name: (cell, x, y, z, rz) of the campfire nearest its map marker, within 2,500}."""
    import birds
    fire_names = {}
    fires = []
    cells = {gd.key(c) for c in gd.grid(world).values()}
    for ck, c in pr.cells.items():
        if ck not in cells:
            continue
        for r in c.get('refs', {}).values():
            b = r.get('base')
            if not b or r.get('removed') or not r.get('p'):
                continue
            if b not in fire_names:
                fire_names[b] = birds._edid(gd, pr, b) == CAMPFIRE
            if fire_names[b]:
                fires.append((ck, r['p']))
    out = {}
    for name, x, y, _z in _markers(pr):
        if name not in RIDGE_CAMPS or name in out:
            continue
        best = min(fires, key=lambda f: (f[1][0] - x) ** 2 + (f[1][1] - y) ** 2, default=None)
        if best and math.hypot(best[1][0] - x, best[1][1] - y) < 2500:
            p = best[1]
            out[name] = (best[0], p[0], p[1], p[2], p[5] if len(p) > 5 else 0.0)
    return out


# ---------- the ops ----------

def ops(gd, pr, world, where, caves, info, seed=SEED, slug=None):
    """(ops, report). One Undo; nothing is changed here. where: `sites`; caves {hive number (1-based): vespidcave plan};
    info: `put_files`' second answer (the models' paths and sizes). Every hive is a place: a door in its mouth into its
    own inside (the great one's big, the rest small), a map marker found when near, a queen whose death ends it."""
    import api_quests as aq
    import api_scripts
    import hiveset
    import library
    import newgame
    import questrec as qr
    import recordio
    import roadgen
    import townbuild
    import vespid
    import vespidcave as VC
    import worldrec
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        raise ValueError('the mod already has %s' % QUEST)
    slug = slug or library.slug(pr.name)
    doctor = next((k for k, r in pr.records.items() if r.get('type') == 'CONT' and recordio.field(r, 'EDID') == DOCTOR_CHEST), None)
    camps = ridge_campfires(gd, pr, world)
    n = len(where)
    rnd = random.Random(seed)
    kinds = list(hiveset.KINDS)
    # keys in the order the ops make them: these records, then each hive's PER_HIVE refs (the quest script names some)
    names = ['gland', 'death', 'jelly', 'royal', 'tonic', 'hivefire', 'cake', 'r_tonic', 'r_fire', 'r_cake', 'recipe', 'kit', 'cache',
             'chamber', 'brood_chamber', 'msg', 'queen_s', 'vespid', 'queen', 'brood', 'quest_s', 'quest'] + \
        ['stat_%s' % k for k in kinds] + ['burnt_%s' % k for k in kinds]
    per_hive = ('life', 'pool', 'fire', 'cache', 'hive', 'burnt', 'door', 'flame', 'mapmarker')
    keys = aq._reserve(pr, len(names) + n * len(per_hive))
    K = dict(zip(names, keys))
    hive_refs = [dict(zip(per_hive, keys[len(names) + i * len(per_hive):len(names) + (i + 1) * len(per_hive)])) for i in range(n)]
    antivenom = gd.key(_game(gd, 'ALCH', 'NVAntivenom'))
    sc = api_scripts.scripts()
    out = []
    out.append({'op': 'record_new', 'record': gland(gd)})
    out.append({'op': 'record_new', 'record': death_item(gd, K['gland'])})
    out.append({'op': 'record_new', 'record': rad_honey(gd)})
    out.append({'op': 'record_new', 'record': royal_jelly(gd)})
    out.append({'op': 'record_new', 'record': royal_tonic(gd)})
    out.append({'op': 'record_new', 'record': hive_fire(gd)})
    out.append({'op': 'record_new', 'record': honey_cake(gd)})
    broc = gd.key(_game(gd, 'INGR', 'BrocFlower') if _has(gd, 'INGR', 'BrocFlower') else _game(gd, 'ALCH', 'BrocFlower'))
    maize = gd.key(_game(gd, 'ALCH', 'NVFreshMaize'))
    out.append({'op': 'record_new', 'record': recipe_of(gd, 'FOLabRecipeRoyalJellyTonic', 'Royal Jelly Tonic', 70,
                                                         [(K['royal'], 1), (K['jelly'], 1), (broc, 1)], K['tonic'])})
    out.append({'op': 'record_new', 'record': recipe_of(gd, 'FOLabRecipeHiveFire', 'Hive Fire', 60,
                                                         [(K['royal'], 1), (K['gland'], 1), (K['jelly'], 1)], K['hivefire'])})
    out.append({'op': 'record_new', 'record': recipe_of(gd, 'FOLabRecipeRadHoneyCake', 'Rad Honey Cake', 25,
                                                         [(K['jelly'], 2), (maize, 1)], K['cake'])})
    out.append({'op': 'record_new', 'record': recipe(gd)})
    out.append({'op': 'record_new', 'record': antivenom_kit(gd)})
    out.append({'op': 'record_new', 'record': cache(gd, K['jelly'])})
    chamber = cache(gd, K['jelly'])                      # (the great queen's: royal jelly, only here)
    _set(chamber, 'EDID', 'FOLabVespidQueenChamber')
    _add_items(chamber, [(K['jelly'], 4), (K['royal'], 3)])
    out.append({'op': 'record_new', 'record': chamber})
    brood_chamber = cache(gd, K['jelly'])                # (a small hive's queen's: honey and antivenom)
    _set(brood_chamber, 'EDID', 'FOLabVespidBroodChamber')
    _add_items(brood_chamber, [(K['jelly'], 3), (antivenom, 1)])
    out.append({'op': 'record_new', 'record': brood_chamber})
    msg = _message('FOLabVespidHiveDiesMsg', 'The hive dies with its queen.')
    out.append({'op': 'record_new', 'record': msg})
    cqq = sc.compile(queen_script('FOLabVespidHiveDiesMsg'), K['queen_s'], 'object', {K['msg']: msg})
    if not hasattr(cqq, 'subrecords'):
        raise ValueError('the queen script does not compile: %s' % (cqq,))
    out.append({'op': 'record_new', 'record': sc._record_of(cqq, QUEEN_SCRIPT)})
    vespid_rec = vespid.creature(gd, 'vespid', slug, K['death'])
    _field(vespid_rec, 'ACBS', 'Flags', next(f['value'] for s_ in vespid_rec['subs'] if s_['tag'] == 'ACBS' for f in s_['fields'] if f.get('name') == 'Flags') | RESPAWN)
    out.append({'op': 'record_new', 'record': vespid_rec})
    out.append({'op': 'record_new', 'record': vespid.creature(gd, 'queen', slug, K['death'], K['queen_s'])})
    out.append({'op': 'record_new', 'record': vespid.creature(gd, 'brood', slug, K['death'], K['queen_s'])})
    extra = {}
    for i, hr in enumerate(hive_refs):
        for what, edid in (('life', LIFE), ('pool', POOL), ('fire', FIRE), ('cache', CACHE)):
            extra[hr[what]] = {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid % (i + 1)}]}
    quest = qr.quest_record({'edid': QUEST, 'script': K['quest_s'], 'name': '', 'flags': {'start_enabled': True},
                             'priority': 50, 'delay': 2.0, 'stages': [], 'objectives': []})
    extra[K['quest']] = quest
    cq = sc.compile(quest_script(n, 0), K['quest_s'], 'quest', extra)
    if not hasattr(cq, 'subrecords'):
        raise ValueError('the hives script does not compile: %s' % (cq,))
    out.append({'op': 'record_new', 'record': sc._record_of(cq, QUEST_SCRIPT)})
    out.append({'op': 'record_new', 'record': quest})
    for k in kinds:
        out.append({'op': 'record_new', 'record': _stat(hiveset.KINDS[k][0], info[k]['mesh'][7:], info[k]['box'], far=True)})
    for k in kinds:
        out.append({'op': 'record_new', 'record': _stat(hiveset.KINDS[k][0] + 'Burnt', info[k]['burnt'][7:], info[k]['box'], far=True)})
    # each hive outside
    marker = gd.key(_game(gd, 'STAT', MARKER))
    fire = gd.key(_game(gd, 'MSTT', GAME_FIRE))          # (the game's fire: a moving static)
    door = gd.key(_game(gd, 'DOOR', VC.DOOR))
    ob = townbuild.obnd(gd, door) or [-60, -8, 0, 60, 8, 220]
    door_turn = 0.0 if (ob[4] - ob[1]) <= (ob[3] - ob[0]) else math.pi / 2     # (the door's thin way along the hive's y)
    g = roadgen.Ground(gd, pr, world)
    pool_adds, inside, report = [], [], {'hives': [], 'vespids': 0, 'kits': []}
    for i, ((kind, x, y, z, rz), hr) in enumerate(zip(where, hive_refs)):
        cell = cell_at(gd, world, x, y)
        P = lambda lx, ly, lz=0.0, turn=0.0: [round(world_of(lx, ly, x, y, rz)[0], 1), round(world_of(lx, ly, x, y, rz)[1], 1), round(z + lz, 1), 0.0, 0.0, round((rz + turn) % math.tau, 4)]
        mx, my, _mz = info[kind]['mouth']
        r0 = hiveset.KINDS[kind][2]
        name = VC.NAME if kind == 'great' else VC.SMALL_NAME
        pers = lambda edid: {'persistent': True, 'edid': edid}
        out.append({'op': 'add', 'cell': cell, 'base': marker, 'p': P(0, 0, 200), 's': 1.0, 'extra': pers(LIFE % (i + 1))})
        out.append({'op': 'add', 'cell': cell, 'base': marker, 'p': P(0, 0, 260), 's': 1.0, 'extra': pers(POOL % (i + 1))})
        out.append({'op': 'add', 'cell': cell, 'base': marker, 'p': P(0, 0, 320), 's': 1.0,
                    'extra': dict(pers(FIRE % (i + 1)), props={'disabled': True})})
        cx, cy = r0 * 0.62, my - 70.0
        cz = g.at(*world_of(cx, cy, x, y, rz)) or z
        out.append({'op': 'add', 'cell': cell, 'base': K['cache'], 'p': P(cx, cy, cz - z + 1.0, math.pi / 2), 's': 1.0,
                    'extra': dict(pers(CACHE % (i + 1)), props={'lock': {'level': CACHE_LOCK, 'key': '', 'leveled': False}})})
        life = {'ref': hr['life'], 'opposite': False, 'popin': False}
        out.append({'op': 'add', 'cell': cell, 'base': K['stat_%s' % kind], 'p': P(0, 0), 's': 1.0, 'extra': {'props': {'parent': life}}})
        out.append({'op': 'add', 'cell': cell, 'base': K['burnt_%s' % kind], 'p': P(0, 0), 's': 1.0,
                    'extra': {'props': {'parent': dict(life, opposite=True)}}})
        # the salvaged door in its mouth
        dx, dy = world_of(mx, my - 12.0, x, y, rz)
        dz = g.at(dx, dy)
        dtag = 'vhd%d' % (i + 1)
        dcell = cell_at(gd, world, dx, dy) or cell          # (a new thing is filed under the cell it stands in: its link must name that one)
        out.append({'op': 'add', 'cell': dcell, 'base': door, 'p': [round(dx, 1), round(dy, 1), round((dz if dz is not None else z) + 2.0, 1), 0.0, 0.0,
                                                                   round((rz + door_turn) % math.tau, 4)], 's': 1.0, 'name': dtag, 'extra': {'persistent': True}})
        out.append({'op': 'add', 'cell': cell, 'base': fire, 'p': P(0, my * 0.5, 40), 's': FIRE_SCALE,
                    'extra': {'props': {'parent': {'ref': hr['fire'], 'opposite': False, 'popin': False}}}})
        # its map marker, found when you come near, out in front of the mouth
        fx, fy = world_of(mx, my - 300.0, x, y, rz)
        fz = g.at(fx, fy)
        mo = worldrec.marker_op(gd, world, [round(fx, 1), round(fy, 1), round((fz if fz is not None else z) + 60.0, 1)], name, MARKER_TYPE, flags=MARKER_FOUND)
        out.append(mo)
        # its Vespids, round it on the ground, the pool marker their parent
        for k in range(POOL_SIZE[kind]):
            for _try in range(20):
                a_ = rnd.uniform(0, math.tau)
                d = rnd.uniform(*POOL_RING) * r0 / 470.0
                vx, vy = x + d * math.cos(a_), y + d * math.sin(a_)
                vz = g.at(vx, vy)
                if vz is not None:
                    break
            vcell = cell_at(gd, world, vx, vy) or cell
            pool_adds.append({'op': 'add', 'cell': vcell, 'base': K['vespid'], 'p': [round(vx, 1), round(vy, 1), round(vz + 20, 1), 0.0, 0.0, round(rnd.uniform(0, math.tau), 4)],
                              's': 1.0, 'extra': {'props': {'parent': {'ref': hr['pool'], 'opposite': False, 'popin': False}}}})
        ax, ay = world_of(mx, my - 170.0, x, y, rz)
        az = g.at(ax, ay)
        arrive_out = [round(ax, 1), round(ay, 1), round((az if az is not None else z) + 8.0, 1), 0.0, 0.0, round((rz + math.pi) % math.tau, 4)]
        row = {'kind': kind, 'name': name, 'x': x, 'y': y, 'z': z, 'turn': rz, 'cell': cell, 'vespids': POOL_SIZE[kind], 'life': hr['life'],
               'door': [round(dx, 1), round(dy, 1)], 'marker': mo['p'][:2], 'inside': None}
        cave = caves.get(i + 1)
        if cave is not None:
            great = kind == 'great'
            inside.append((cave, dict(tag='vhc%d' % (i + 1), edid='FOLabVespid%s%02d' % ('GreatHive' if great else 'Nest', i + 1), full=name,
                                      queen_key=K['queen' if great else 'brood'], queen_parent=hr['life'], vespid_key=K['vespid'],
                                      chamber_key=K['chamber' if great else 'brood_chamber'], outside_door=(dcell, '$' + dtag),
                                      outside_arrival=arrive_out, finds=(K['jelly'], K['royal'] if great else None))))
            row['inside'] = {'seed': cave.get('seed'), 'size': cave.get('size'), 'leaking rays': cave.get('leaks'), 'pieces': len(cave['made']),
                             'combs': len(cave['combs']), 'lights': len(cave['lights']), 'vespids': len(cave['vespids']), 'queen': bool(cave['queen'])}
        report['hives'].append(row)
        report['vespids'] += POOL_SIZE[kind]
    out += pool_adds
    # antivenom kits at the ridge camps' campfires
    for cname, (ck, fx, fy, fz, frz) in sorted(camps.items()):
        kx, ky = world_of(140.0, 40.0, fx, fy, frz)
        kz = g.at(kx, ky)
        out.append({'op': 'add', 'cell': ck, 'base': K['kit'], 'p': [round(kx, 1), round(ky, 1), round((kz if kz is not None else fz) + 1.0, 1), 0.0, 0.0, round(frz, 4)], 's': 1.0})
        report['kits'].append(cname)
    # the insides: every piece re-dressed once, then each hive's place
    if inside:
        rops, pnames = VC.piece_records(gd, [c for c, _a in inside], info['comb']['mesh'], info['comb']['box'])
        out += rops
        for cave, a_ in inside:
            out += VC.place_ops(gd, cave, a_['tag'], a_['edid'], a_['full'], pnames, a_['queen_key'], a_['queen_parent'], a_['vespid_key'],
                                a_['chamber_key'], a_['outside_door'], a_['outside_arrival'], finds=a_['finds'])
    # the doctor sells antivenom
    if doctor:
        rec = json.loads(json.dumps(pr.records[doctor]))
        _add_items(rec, [(antivenom, DOCTOR_ANTIVENOM)])
        out.append({'op': 'record', 'key': doctor, 'record': rec})
    keys = aq._reserve(pr, sum(1 for o in out if o['op'] in ('record_new', 'add')))
    report.update({'keys': keys, 'records': K, 'doctor': bool(doctor), 'camps_missing': [c for c in RIDGE_CAMPS if c not in camps]})
    return out, report


def plan_insides(gd, where, progress=print):
    """{hive number: a walked, closed cave} for every hive: the great one's big, the rest small (vespidcave.SMALL_SIZES,
    each its own seed). A hive whose cave won't walk closed is left out (the report says so)."""
    import vespidcave as VC
    caves, k = {}, 0
    for i, (kind, *_r) in enumerate(where):
        if kind == 'great':
            size, fill, seed = VC.SIZE, VC.GREAT, VC.SEED
        else:
            size, fill, seed = VC.SMALL_SIZES[k % len(VC.SMALL_SIZES)], VC.SMALL, VC.SEED + 13 * (i + 1)
            k += 1
        progress('hive %d (%s): planning its inside, %dx%d' % (i + 1, kind, size[0], size[1]))
        cave = VC.closed_plan(gd, seed, progress=progress, size=size, fill=fill)
        if cave is not None:
            cave['size'] = list(size)
            caves[i + 1] = cave
        else:
            progress('hive %d: no cave walked closed' % (i + 1))
    return caves


def put_files(gd, pr, caves, progress=print):
    """The Vespids', the hives' and their insides' files among the mod's own. Returns (paths, info)."""
    import hiveset
    import library
    import vespid
    import vespidcave as VC
    root = library.assets_dir(pr)
    made = vespid.files(gd, library.slug(pr.name))
    hives, info = hiveset.all_files(progress)
    made.update(hives)
    comb = VC.comb_model()
    made[comb['mesh']] = comb['nif']
    info['comb'] = {'mesh': comb['mesh'], 'box': comb['box']}
    if caves:
        made.update(VC.pictures())
        made.update(VC.piece_files(gd, [m.key for c in caves.values() for m in c['made']])[0])
    for rel, data in made.items():
        library._put(root, rel, data)
    return sorted(made), info


def build(server, progress=print, avoid=(), seed=SEED):
    """Into the open mod: sites, each hive's inside, files, then one Undo. Returns the report. avoid: more [(x, y, how
    far)] for the hives to keep off."""
    gd, pr = server.GD, server.PR
    world = next(w for w in gd.worlds() if gd.edid(w) == 'FOLabWaikiki')
    where = sites(gd, pr, world, seed, avoid=avoid)
    caves = plan_insides(gd, where, progress)
    paths, info = put_files(gd, pr, caves, progress)
    o, rep = ops(gd, pr, world, where, caves, info, seed)
    rep['files'] = paths
    made = server.edit("Vespids and their hives", o)['made']
    assert made == rep['keys'], ('keys not as reserved', made[:5], rep['keys'][:5])
    return rep
