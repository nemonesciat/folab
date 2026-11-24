"""The Huáng's land all Huáng, and the Huáng speaking Mandarin (the user, 22 Nov 2026: "presence of pirates and random
outsiders, it should be all huang around here"; "they should be speaking mandarin, or broken english in some cases").

Their land (`Land`): the Waimānalo side, from the Makapuʻu gate through their courtyards and maize to the Border Post, and
the freighter: within `COMPOUND_REACH` of the courtyards' middle (their screens and halls), within `ROAD_REACH` of the road
from the Makapuʻu gate to the courtyards and on to the Border Post, within `POST_REACH` of their outposts (Makapuʻu Gate,
Border Post, Settlers' Watchtower) and of the freighter.

Clearing (`clear`): every person standing there who isn't Huáng (an NPC_ or a levelled list of people: pirates, Waikiki's
locals and surfers, the wastelanders worldlife and the scenes stood, activity's roadside crews), the source plugin's
placements as well as the mod's, is taken out; wildlife (creatures and their lists) stays. A person something else names
(a link, a door, an enable parent) or that has an editor ID of its own (a quest's) is left and reported. People outside
whose storm shelter (stormafter's link) is in a place whose door is in the Huáng's land lose that link. Nothing else in
their cells brings people: the encounter zones (worldlife) only set levels, and every levelled spawn is a placed ref.

Filling (`fill`): where people were taken out and no Huáng stands within `EMPTY`, Nongmin of their own (faces not used
before, Asian; the men's are used up, so mostly women, as activity's farmers) working by the game's raking and yard markers
in the courtyards and fields, and Shouwei walking the road from the Makapuʻu gate to the courtyards and back (the patrol
package activity made).

Speech (`lines`): each line a Huáng says, as `SAID`: Mandarin in pinyin with the English after it in brackets on screen
("Ni hao. (Hello.)": the game's font has no tone marks, so the subtitle is `g2pzh.shown`); the toned pinyin is what is
spoken, by Kokoro's Chinese voices (`voicegen.write_line(lang='zh')`), kept in voices.json as the line's `say` with `lang`
'zh' so the Voice page keeps it Mandarin. Zhao Lei at the gate deals with outsiders: his lines are short broken English,
his quest's two lines too (what he says unchanged). The Shouwei keep their greeting's words; those of the Huáng who had no
greeting of their own (Nongmin, the elders, the patrols) get a plain one in Mandarin. No Huáng trades: Linda does it for them.

Paths (`paths`; the user: "the town with the huang buildings needs some kind of road or path between the buildings, right
now it is all plants"): worn ways through their town, searched over the ground at `GRID` (round buildings, walls and
courtyard screens, through the gates, gently up slopes, sharing a way already laid): the road of gates, each gate to the
nearest courtyard, each hall to its courtyard, out to each maize field and down to the freighter's landing (the canoe
sheds). Stone paving (`STONE`, the villa's cobbles) inside the town, packed earth (`EARTH`, the game's dirt path) going out,
painted into the ground strongest on the line and broken at its edges so it reads walked, not built; the grass-bearing
layers under it faded so no grass grows there (the path textures carry none); what grows or lies on it taken out; low stone
kerbs of FOLab's own (`huang_path_kerb`, closed) along the paved ways now and then, where nothing is in their way.
"""
import json
import math
import os
import random

import recordio

COMPOUND_REACH = 9000.0
ROAD_REACH = 4000.0
POST_REACH = 2500.0
PLAIN_STEP = 512.0                  # (the plain's squares)
RIDGE = 3500.0                      # (ground this high is the Koʻolau, not the plain: the ridge's crest stands well over 5000)
SHORE = -150.0                      # (the plain runs into the shallows this far down)
BORDER_PAD = 600.0                  # (past the Border Post's and the Makapuʻu gate's lines across the coast, this far: their posts)
EMPTY = 1500.0                      # (no Huáng this near where people were taken out: someone of theirs goes there)
# raiding parties on the Huáng shore (the user: "id maybe expect some on the coast there as a raiding party or two, but not
# inland"): pirates of their own kind who stay by their spot on the sand, facing the town
RAIDER, RAIDER_FROM, RAIDER_PACKAGE = 'FOLabPirateRaider', 'FOLabPirateLvlFiend2GunVarNV', 'DefaultSandboxEditorLocation256'
RAIDS, RAID_EACH = 2, 3
RAID_FROM_TOWN, RAID_APART = 7000.0, 8000.0
RAID_SEA = 700.0                            # (a raiding party stands this near the sea at most: on the beach)
SHORE_HIGH, SHORE_SEA = 120.0, 3            # (sand no higher than this, the sea within this many squares)
INLAND = 2000.0                             # (a pirate further than this from the sea is inland: none may stand there)
CLUSTER = 1200.0
NONGMIN_EACH = 2
ROAD_STEP = 6000.0                  # (the road patrol's points, about this far apart)
PEOPLE = ('NPC_', 'LVLN')
HUANG_WORDS = ('FOLabHuang', 'FOLabPatrolShouwei', 'FOLabMakapuuGuard', 'FOLabShouweiRoad', 'FOLabNongminFill')
POSTS = ('makapuu', 'border', 'watch')

# what each says: (English as shown, pinyin with tone marks as spoken); None pinyin: English as it is (broken English)
GUARD_GREET = ("Barbarian. Walk the road. Touch nothing.", "Mánzi. Yánzhe lù zǒu. Shénme dōu bié pèng.")
SAID = {
    'guard': [GUARD_GREET],
    'patrol': [GUARD_GREET],
    'nongmin': [("Hello.", "Nǐ hǎo."), ("I'm busy.", "Wǒ hěn máng.")],
    'elder': [("Outsider. Please go.", "Wàirén. Qǐng zǒu ba.")],
}
# Zhao Lei's lines, by what they said before: the same, in short broken English
ZHAO = {
    "Stop there. Outsiders don't come through this gate, only trade, and you carry none. ... That on your wrist. Then you're no common stranger.":
        "Stop. Outsider no come through gate. Only trade. You carry none. ... That, on wrist. Then you not common stranger.",
    "You may walk our road as far as the ship, and back. Touch nothing, take nothing, and don't stay.":
        "You walk our road to ship. Then back. Touch nothing. Take nothing. No stay.",
    "You walked our road and touched nothing. Good. A guest doesn't leave with empty hands: take this. Don't think it makes you one of us.":
        "You walk our road, touch nothing. Good. Guest not leave empty hand. Take. Not make you one of us.",
}
ZH_MEN = ('zm_yunjian', 'zm_yunxi', 'zm_yunxia', 'zm_yunyang')
ZH_WOMEN = ('zf_xiaobei', 'zf_xiaoni', 'zf_xiaoxiao', 'zf_xiaoyi')
ZH_PACE = 0.9


def shown(english, pinyin):
    """The subtitle: pinyin as the game's font can print it, the meaning after in brackets."""
    import g2pzh
    return '%s (%s)' % (g2pzh.shown(pinyin), english)


def _edid(pr, k):
    return recordio.field(pr.records.get(k) or {}, 'EDID') or ''


def faction_key(pr):
    return next((k for k, r in pr.records.items() if r.get('type') == 'FACT' and recordio.field(r, 'EDID') == 'FOLabHuangFaction'), None)


def is_huang(pr, base, fac=None):
    """Whether a base is one of the Huáng's people: their faction's, or named as theirs."""
    if not base.startswith('+'):
        return False
    rec = pr.records.get(base) or {}
    if rec.get('type') != 'NPC_':
        return False
    if _edid(pr, base).startswith(HUANG_WORDS):
        return True
    fac = fac or faction_key(pr)
    for s in rec.get('subs', ()):
        if s['tag'] == 'SNAM':
            v = s.get('value') if 'value' in s else next((f.get('value') for f in s.get('fields', ()) if 'faction' in f.get('name', '').lower()), None)
            if v == fac:
                return True
    return False


def role_of(edid):
    if edid == 'FOLabMakapuuGuard':
        return 'zhao'
    if edid.startswith(('FOLabHuangGuard', 'FOLabShouweiRoad')):
        return 'guard'
    if edid.startswith('FOLabPatrolShouwei'):
        return 'patrol'
    if edid.startswith('FOLabHuangElder'):
        return 'elder'
    return 'nongmin'


# ---------- where ----------

def _seg_dist(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy or 1.0)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


class Land:
    """The Huáng's land in the island's world."""

    def __init__(self, gd, pr, world=None):
        import factionfolk as ff
        self.gd, self.pr = gd, pr
        mk = ff._markers(pr)
        if world is None:
            world = gd.ext_cells[gd.from_key(mk[ff.MARKERS['royal']][0])]
        self.world = world
        grid = gd.grid(world)
        keys = {gd.key(c) for c in grid.values()}
        homes, ship = [], []
        for ck, c in pr.cells.items():
            if ck not in keys:
                continue
            for r in c.get('refs', {}).values():
                if r.get('removed') or not r.get('p') or not r.get('base', '').startswith('+'):
                    continue
                e = _edid(pr, r['base'])
                if e.startswith(('FOLabSettlerScreen', 'FOLabSettlerHall')):
                    homes.append(r['p'])
                elif e == 'FOLabSettlerFreighter':
                    ship.append(r['p'])
        if not homes:
            raise ValueError('the mod has no Huáng courtyards (FOLabSettlerScreen, FOLabSettlerHall)')
        self.middle = (sum(p[0] for p in homes) / len(homes), sum(p[1] for p in homes) / len(homes))
        self.posts = {n: tuple(mk[ff.MARKERS[n]][1][:2]) for n in POSTS if ff.MARKERS[n] in mk}
        self.ship = [tuple(p[:2]) for p in ship]
        self.road = [(self.posts['makapuu'], self.middle)] if 'makapuu' in self.posts else []
        if 'border' in self.posts:
            self.road.append((self.middle, self.posts['border']))
        self._plain = None
        self._gd, self._pr = gd, pr

    def plain(self):
        """The squares of PLAIN_STEP the Huáng's plain covers: the ground below RIDGE reached from the courtyards without
        crossing the Koʻolau, between a line across the coast at the Border Post and one at the Makapuʻu gate (the user,
        22 Nov 2026, of pirates on it: their land is all Waimānalo, not a strip along the road)."""
        if getattr(self, '_plain', None) is not None:
            return self._plain
        import roadgen
        self._plain = set()
        if not getattr(self, '_gd', None) or 'border' not in self.posts or 'makapuu' not in self.posts:
            return self._plain
        G = roadgen.Ground(self._gd, self._pr, self.world)
        b, g = self.posts['border'], self.posts['makapuu']
        L = math.hypot(g[0] - b[0], g[1] - b[1]) or 1.0
        dx, dy = (g[0] - b[0]) / L, (g[1] - b[1]) / L
        x0, x1 = min(b[0], g[0]) - 30000.0, max(b[0], g[0]) + 10000.0
        y0, y1 = min(b[1], g[1]) - 30000.0, max(b[1], g[1]) + 20000.0
        S = PLAIN_STEP

        def ok(i, j):
            x, y = i * S, j * S
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                return False
            along = (x - b[0]) * dx + (y - b[1]) * dy
            if along < -BORDER_PAD or along > L + BORDER_PAD:
                return False
            h = G.at(x, y)
            return h is not None and SHORE < h < RIDGE
        start = (int(round(self.middle[0] / S)), int(round(self.middle[1] / S)))
        todo, seen = [start], {start}
        while todo:
            i, j = todo.pop()
            if not ok(i, j):
                continue
            self._plain.add((i, j))
            for q in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if q not in seen:
                    seen.add(q)
                    todo.append(q)
        return self._plain

    def inside(self, x, y):
        if math.hypot(x - self.middle[0], y - self.middle[1]) <= COMPOUND_REACH:
            return True
        if (int(round(x / PLAIN_STEP)), int(round(y / PLAIN_STEP))) in self.plain():
            return True
        if any(_seg_dist((x, y), a, b) <= ROAD_REACH for a, b in self.road):
            return True
        return any(math.hypot(x - p[0], y - p[1]) <= POST_REACH for p in list(self.posts.values()) + self.ship)

    def in_compound(self, x, y):
        return math.hypot(x - self.middle[0], y - self.middle[1]) <= COMPOUND_REACH

    def cells(self):
        """The world's cells any part of the land reaches."""
        out = []
        for xy, c in self.gd.grid(self.world).items():
            mx, my = (xy[0] + 0.5) * 4096.0, (xy[1] + 0.5) * 4096.0
            if any(self.inside(mx + dx, my + dy) for dx in (-2048, 0, 2048) for dy in (-2048, 0, 2048)):
                out.append((xy, self.gd.key(c)))
        return out


# ---------- who ----------

def people_in(gd, pr, land):
    """[(cell, ref, base, editor ID, p, Huáng?)] of every person standing in the Huáng's land (wildlife left out)."""
    import indoors
    fac = faction_key(pr)
    kinds = {}

    def kind(b):
        if b not in kinds:
            try:
                kinds[b] = (pr.records.get(b) or {}).get('type', '') if b.startswith('+') else gd.forms[gd.from_key(b)][1].tag
            except (KeyError, ValueError):
                kinds[b] = ''
        return kinds[b]
    out = []
    for _xy, ck in land.cells():
        for rk, base, p, _s in indoors.placed(gd, pr, ck):
            if kind(base) in PEOPLE and land.inside(p[0], p[1]):
                out.append((ck, rk, base, indoors._edid(gd, pr, base), list(p), is_huang(pr, base, fac)))
    return out


def _named(pr):
    """Refs something else names: links, doors, enable parents."""
    out = set()
    for c in pr.cells.values():
        for r in c.get('refs', {}).values():
            if r.get('link'):
                out.add(r['link'])
            if isinstance(r.get('tel'), dict) and r['tel'].get('door'):
                out.add(r['tel']['door'])
            par = ((r.get('props') or {}).get('parent') or {})
            if isinstance(par, dict) and par.get('ref'):
                out.add(par['ref'])
    return out


def clear(gd, pr, land):
    """(ops, report): outsiders out of the Huáng's land, shelters there kept for the Huáng."""
    import stormafter
    named = _named(pr)
    ops, gone, kept = [], [], []
    for ck, rk, base, e, p, huang in people_in(gd, pr, land):
        if huang or e == RAIDER:
            continue
        own = (pr.cells.get(ck) or {}).get('refs', {}).get(rk) or {}
        if rk in named or own.get('edid'):
            kept.append([rk, e, [round(v) for v in p[:2]]])
            continue
        ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
        gone.append([rk, e, [round(v) for v in p[:3]]])
    # inside: the places whose way in stands in their land (the plain's hotels) are theirs too
    where = {}
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            for rk in c.get('refs', {}):
                where[rk] = ck
    places = set()
    for _xy, ck in land.cells():
        for rk, r in (pr.cells.get(ck) or {}).get('refs', {}).items():
            t = r.get('tel')
            if isinstance(t, dict) and r.get('p') and not r.get('removed') and land.inside(r['p'][0], r['p'][1]) and t.get('door') in where:
                places.add(where[t['door']])
    import indoors
    fac0 = faction_key(pr)
    inside_gone = 0
    for place in sorted(places):
        for rk, base, p, _s in indoors.placed(gd, pr, place):
            t = (pr.records.get(base) or {}).get('type', '') if base.startswith('+') else ''
            if not base.startswith('+'):
                try:
                    t = gd.forms[gd.from_key(base)][1].tag
                except (KeyError, ValueError):
                    t = ''
            if t not in PEOPLE or is_huang(pr, base, fac0):
                continue
            own = (pr.cells.get(place) or {}).get('refs', {}).get(rk) or {}
            if rk in named or own.get('edid'):
                kept.append([rk, indoors._edid(gd, pr, base), 'inside ' + place])
                continue
            ops.append({'op': 'remove', 'cell': place, 'ref': rk})
            gone.append([rk, indoors._edid(gd, pr, base), None])
            inside_gone += 1
    # storm shelters: a marker in a place whose door is in their land is for the Huáng only
    their = {place for x, y, place, _a in stormafter.shelters(gd, pr, land.world) if land.inside(x, y)}
    marks = {rk for place in their for rk in (pr.cells.get(place) or {}).get('refs', {})}
    fac = faction_key(pr)
    unlinked = 0
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if r.get('link') in marks and not r.get('removed') and r.get('base') and not is_huang(pr, r['base'], fac):
                if any(o.get('ref') == rk for o in ops):
                    continue
                ops.append({'op': 'ref_set', 'cell': ck, 'ref': rk, 'set': {'link': None}})
                unlinked += 1
    by = {}
    for _rk, e, _p in gone:
        by[e] = by.get(e, 0) + 1
    return ops, {'taken out': len(gone), 'of them inside': inside_gone, 'places of theirs': len(places), 'by kind': by,
                 'kept (named by something)': kept, 'shelters unlinked': unlinked, 'gone': gone}


# ---------- filling ----------

def _clusters(pts, reach=CLUSTER):
    left, out = list(pts), []
    while left:
        group = [left.pop()]
        grew = True
        while grew:
            grew = False
            for p in list(left):
                if any(math.hypot(p[0] - q[0], p[1] - q[1]) <= reach for q in group):
                    group.append(p)
                    left.remove(p)
                    grew = True
        out.append(group)
    return out


# the game's people called only by what they are (no story character), whose looks may be borrowed when factionfolk's pool is
# used up: the Huáng and the court took every Asian face it has
GENERIC = {'Gambler', 'Traveler', 'NCR Trooper', 'Kings Gang Member', 'Street Vendor', 'Traveling Merchant', 'Followers Medical Student',
           'Omerta Thug', 'Followers Guard', 'Vault 34 Dweller', 'Great Khan', 'Bartender', 'Man', 'Woman'}


def face_pool(gd, pr):
    """({(race, sex): [game NPC_]}, used keys): factionfolk's faces with the game's other Asian people of no story added
    (`GENERIC`), and every face a person of the mod already has (copied from, or its look's template)."""
    import factionfolk as ff
    pool = {k: list(v) for k, v in ff.faces(gd).items()}
    races = {f: gd.edid(f) for f, (_i, r) in gd.forms.items() if r.tag == 'RACE'}
    have = {f for v in pool.values() for f in v}
    for f, (_i, r) in sorted(gd.forms.items()):
        if r.tag != 'NPC_' or (f >> 24) != 0 or f in have:
            continue
        e = gd.edid(f) or ''
        if e.lower().endswith(('dead', 'template')):
            continue
        rec = recordio.load(gd, f)
        if recordio.field(rec, 'TPLT') or recordio.field(rec, 'FULL') not in GENERIC:
            continue
        rn = recordio.field(rec, 'RNAM')
        race = races.get(gd.from_key(rn)) if rn else None
        if race != 'Asian':
            continue
        pool.setdefault((race, 'F' if ff._num(rec, 'ACBS', 'Flags') & 0x1 else 'M'), []).append(f)
    used = set()
    for r in pr.records.values():
        if r.get('type') == 'NPC_':
            used.add(r.get('copied_from'))
            used.add(recordio.field(r, 'TPLT'))
    return pool, used


def fill(gd, pr, land, gone, ctx=None):
    """(ops, report): Huáng where people were taken out and none of theirs stands near."""
    import activity
    import factionfolk as ff
    ctx = ctx or activity.Ctx(gd, pr)
    if not hasattr(ctx, '_pool'):
        ctx._pool, ctx._used = face_pool(gd, pr)
    o = activity.Out(ctx)
    rep = {'nongmin': [], 'road patrol': None, 'no face left': 0}
    huang = [p for _ck, _rk, _b, _e, p, h in people_in(gd, pr, land) if h]
    fac = ff._mod_key(pr, ff.FACTIONS['huang'][0], 'FACT')
    taken = {e for e in ctx.edids}
    n = [0]

    def new_edid(stem):
        while True:
            n[0] += 1
            e = '%s%02d' % (stem, n[0])
            if e not in taken:
                taken.add(e)
                return e

    def made(group, stem, sex, package=None):
        g = ff.GROUPS[group]
        face = ctx.free_face(g['races'], sex) or ctx.free_face(g['races'], 'F' if sex == 'M' else 'M')
        if face is None:
            rep['no face left'] += 1
            return None
        fem = ff._num(recordio.load(gd, face), 'ACBS', 'Flags') & 0x1
        items = [(ff._item(gd, pr, e), 1) for e in g['wear']['F' if fem else 'M']]
        if group == 'huang_guard':
            arm = ff._mod_key(pr, g['arms'][0], 'WEAP')
            if arm:
                items.append((arm, 1))
        game_pack = package if package and not package.startswith('+') else 'DefaultSandboxEditorLocation512'
        rec = ff.person(gd, pr, face, new_edid(stem), g['name'], dict(g, package=game_pack), items, [], fac)
        if package and package.startswith('+'):
            for s in rec['subs']:
                if s['tag'] == 'PKID':
                    s['value'] = package
        return o.keys.add(rec)
    empty = []
    for group in _clusters([g[2][:2] for g in gone if g[2]]):
        mx, my = sum(p[0] for p in group) / len(group), sum(p[1] for p in group) / len(group)
        if any(math.hypot(mx - h[0], my - h[1]) < EMPTY for h in huang):
            continue
        empty.append((mx, my))
    road = []
    for mx, my in empty:
        if not land.in_compound(mx, my):
            road.append((mx, my))
            continue
        spots = [s for s in ctx.around(mx, my, NONGMIN_EACH + 1, radii=(150, 300, 450, 650, 900), turns=12, apart=200.0) if land.inside(s[0], s[1])]
        if len(spots) < 2:
            continue
        for k, s in enumerate(spots):
            o.marker(('rake', 'yard', 'water')[k % 3], s[0], s[1], s[2], math.atan2(mx - s[0], my - s[1]))
        put = 0
        for s in spots[:NONGMIN_EACH]:
            key = made('huang_folk', 'FOLabNongminFill', 'F')
            if key:
                o.person_rec(key, s[0], s[1], s[2], math.atan2(mx - s[0], my - s[1]), 'nongmin')
                put += 1
        rep['nongmin'].append([round(mx), round(my), put])
        huang.append((mx, my))
    # the road from the Makapuʻu gate to the courtyards: Shouwei walking it, out and back
    pack = ctx.edids.get('FOLabPatrolPackage')
    if road and pack and land.road and not any(e.startswith('FOLabShouweiRoad') for e in ctx.edids):   # (one road patrol, ever)
        a, b = land.road[0]
        steps = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) // ROAD_STEP))
        pts = []
        for k in range(steps + 1):
            t = k / steps
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            s = ctx.around(x, y, 1, radii=(200, 400, 700, 1000, 1400, 1900), turns=12, apart=150.0)
            if s and land.inside(s[0][0], s[0][1]):
                pts.append(s[0])
        if len(pts) >= 2:
            walkers = 0
            for w in range(2):
                key = made('huang_guard', 'FOLabShouweiRoad', 'M', package=pack)
                if key:
                    activity._patrol_ring(ctx, o, key, pts if w == 0 else list(reversed(pts)))
                    walkers += 1
            rep['road patrol'] = {'points': len(pts), 'walkers': walkers}
    return o.done(rep)


# ---------- speech ----------

def greeting_key(gd):
    return gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'DIAL' and gd.edid(f) == 'GREETING' and (f >> 24) == 0))


def _says(gd, pr):
    """{person key: [line key]} of every line conditioned on one person (GetIsID)."""
    import questrec as qr
    out = {}
    for k, r in pr.records.items():
        if r.get('type') != 'INFO':
            continue
        for c in qr.info_plain(json.loads(json.dumps(r)))['conditions']:
            if c.get('fn') == 72 and isinstance(c.get('p1'), str):
                out.setdefault(c['p1'], []).append(k)
    return out


def zh_voice(key, female, role):
    pool = ZH_WOMEN if female else ZH_MEN
    if role == 'elder' and not female:
        return 'zm_yunyang'
    return pool[int(key.lstrip('+').split(':')[-1], 16) % len(pool)]


def lines(gd, pr, people=None):
    """(ops, plan, report): the Huáng's lines in Mandarin (or Zhao Lei's broken English); new greetings for those with
    none; plan: [(line key, response number, pinyin or None)] for voicing once applied. people: {key: editor ID}, else
    every Huáng NPC_ of the mod (records made by `fill` in the same go included when passed)."""
    import questrec as qr
    fac = faction_key(pr)
    if people is None:
        people = {k: _edid(pr, k) for k, r in pr.records.items() if r.get('type') == 'NPC_' and is_huang(pr, k, fac)}
    says = _says(gd, pr)
    greet = greeting_key(gd)
    template = None
    ops, plan, rep = [], [], {'changed': 0, 'new greetings': 0, 'zhao': 0}
    for who, e in sorted(people.items()):
        role = role_of(e)
        mine = says.get(who, [])
        if role == 'zhao':
            for lk in mine:
                rec = json.loads(json.dumps(pr.records[lk]))
                plain = qr.info_plain(rec)
                hit = False
                for r in plain['responses']:
                    if r['text'] in ZHAO:
                        r['text'] = ZHAO[r['text']]
                        hit = True
                if hit:
                    new = qr.info_record(plain)
                    new.update({k: v for k, v in rec.items() if k not in ('subs',)})
                    ops.append({'op': 'record', 'key': lk, 'record': new})
                    rep['zhao'] += 1
                for r in plain['responses']:
                    plan.append((lk, r['number'], None))
            continue
        takes = SAID[role]
        greets = [lk for lk in mine if pr.records[lk].get('topic') == greet]
        if greets:
            for lk in greets:
                rec = json.loads(json.dumps(pr.records[lk]))
                plain = qr.info_plain(rec)
                for r in plain['responses']:
                    en, zh = next(((a, b) for a, b in takes if a == r['text'] or shown(a, b) == r['text']), takes[0])
                    r['text'] = shown(en, zh)
                    plan.append((lk, r['number'], zh))
                new = qr.info_record(plain)
                new.update({k: v for k, v in rec.items() if k not in ('subs',)})
                ops.append({'op': 'record', 'key': lk, 'record': new})
                rep['changed'] += 1
            continue
        # none of their own: a plain greeting, as the guards' are made
        if template is None:
            template = next((k for p, ks in says.items() if role_of(people.get(p, _edid(pr, p))) == 'guard'
                             for k in ks if pr.records[k].get('topic') == greet), None)
            if template is None:
                raise ValueError('no Shouwei greeting to copy the shape of')
        en, zh = takes[int(who.lstrip('+').split(':')[-1], 16) % len(takes)]
        rec = json.loads(json.dumps(pr.records[template]))
        plain = qr.info_plain(rec)
        for c in plain['conditions']:
            if c.get('fn') == 72:
                c['p1'] = who
        plain['responses'] = plain['responses'][:1]
        plain['responses'][0]['text'] = shown(en, zh)
        new = qr.info_record(plain)
        new.update({k: v for k, v in rec.items() if k not in ('subs',)})
        import activity
        k = activity._new_key(pr)
        new['seq'] = float(rec.get('seq', 0)) + 0.001 * (rep['new greetings'] + 1)
        ops.append({'op': 'record', 'key': k, 'record': new})
        plan.append((k, plain['responses'][0]['number'], zh))
        rep['new greetings'] += 1
    return ops, plan, rep


def voice(gd, pr, plan, progress=None):
    """Voices each planned response once its line is in the mod: Mandarin by Kokoro's Chinese voices (kept in voices.json as
    `lang` 'zh' with the pinyin spoken), English (Zhao Lei's) as api_voices does. Returns {'voiced', 'problems'}."""
    import api_voices as av
    import library
    import voicegen
    voices = av.load(pr)
    root = library.assets_dir(pr)
    done, problems, english = 0, [], set()
    for lk, num, zh in plan:
        if zh is None:
            english.add(lk)
            continue
        info = av.line_info(gd, pr, lk, voices)
        if info['problem']:
            problems.append((lk, info['problem']))
            continue
        r = next(x for x in info['responses'] if x['number'] == num)
        _vt, female = av.voice_type_of(gd, pr, info['who'])
        v = zh_voice(info['who'], female, role_of(av.edid(gd, pr, info['who'])))
        voicegen.write_line(os.path.join(root, r['path']), zh, v, ZH_PACE, lang='zh')
        voices['lines'].setdefault(lk, {})[str(num)] = {'text': r['text'], 'voice': v, 'speed': ZH_PACE, 'pitch': 0.0, 'lively': 1.0,
                                                        'path': r['path'], 'mood': [r['emotion'], r['strength']], 'engine': 'kokoro',
                                                        'lang': 'zh', 'say': zh}
        done += 1
        if progress:
            progress('voiced %d' % done)
    av.save(pr, voices)
    for lk in sorted(english):
        try:
            av.voice_line(gd, pr, lk)
            done += 1
        except ValueError as e:
            problems.append((lk, str(e)))
    library.publish(pr)
    return {'voiced': done, 'problems': problems}


def check(gd, pr, land, plan):
    """What a run must leave: no outsider in the land, every planned response with its .ogg and .lip."""
    import api_voices as av
    import library
    out_left = [(rk, e, [round(v) for v in p[:2]]) for _ck, rk, _b, e, p, h in people_in(gd, pr, land) if not h and e != RAIDER]
    root = library.assets_dir(pr)
    missing = []
    for lk, num, _zh in plan:
        info = av.line_info(gd, pr, lk)
        r = next((x for x in info.get('responses', ()) if x['number'] == num), None)
        if r is None or not all(os.path.isfile(os.path.join(root, r['path'] + ext)) for ext in ('.ogg', '.lip')):
            missing.append((lk, num))
    return {'outsiders left': out_left, 'lines without voice': missing}


# ---------- paths ----------

GRID = 64.0
STONE, EARTH = 'VillaCobblestone', 'LDirtPathWasteland01'
TOWN = 2200.0                       # (within this of the courtyards' middle a path is paved)
FULL, FADE = 30.0, 75.0             # (a path's paint: full this near its line, gone this much further out: a footpath, ~150 across)
CLEAR = 100.0                       # (what grows or lies this near the line goes)
GRADE_COST = 25.0
SHARED = 0.35                       # (a step on a way already laid costs this much of a fresh one)
KERB_EVERY = 6                      # (a kerb on each side every this many pieces' length, where it fits)
KERB_OFF = 95.0
KERB_NEAR = 1200.0                  # (kerbs only this near a courtyard: the paved heart of the town)
FIELDS_NEAR = 4500.0                # (a path to a field only if it lies this near the courtyards' middle)
DETOUR = 2.5                        # (a way in town more than this times the straight line, plus 1000, is no path anyone walks)
DETOUR_OUT = 4.0                    # (going out to a field or the landing, round through a gate)
FIELD_REACH = 700.0


def path_kerb():
    """A low line of basalt stones set in the ground along a path, 128 long (x), the stones' tops 6-10 over the ground."""
    import islandset as I
    looks = I._looks(stone=I.look('island/basalt', tile=90))
    rnd = random.Random(808)
    P = []
    x = -64.0
    while x < 60.0:
        w = min(rnd.uniform(24.0, 34.0), 64.0 - x)
        d = rnd.uniform(14.0, 20.0)
        I._box(P, x + 1.5, -d / 2 + rnd.uniform(-2, 2), -10.0, x + w - 1.5, d / 2 + rnd.uniform(-2, 2), rnd.uniform(6.0, 10.0), 'stone', material='stone')
        x += w
    return {'name': 'FOLabHuangPathKerb', 'looks': looks, 'parts': P}


def _register():
    import modelsets
    modelsets.PIECES.setdefault('huang_path_kerb', {'label': 'Path kerb, basalt stones', 'set': 'huang', 'file': 'huang_path_kerb',
                                                    'describe': path_kerb, 'edid': 'FOLabHuangPathKerb'})


class Ways:
    """The cheapest walk over the ground between two points, round what stands in the way (through the gates)."""

    def __init__(self, B, box):
        self.B = B
        self.x0, self.y0, self.x1, self.y1 = box
        self.nx, self.ny = int((self.x1 - self.x0) / GRID) + 1, int((self.y1 - self.y0) / GRID) + 1
        self.laid = set()
        self.block = {}
        gates = {k for k, r in B.pr.records.items() if (recordio.field(r, 'EDID') or '').startswith(('FOLabSettlerGate', 'FOLabRoad'))}
        self.passable = set(gates)          # (gates, roads (walked over and across: the Huáng's landing lies over the coast
        # road), and the maize rows: a field is walked into, not round)
        self._road = {}

        def through(ck, rk):
            b = (B.pr.cells.get(ck, {}).get('refs', {}).get(rk) or {}).get('base')
            if b in self.passable:
                return True
            if b and not b.startswith('+'):
                if b not in self._road:
                    try:
                        e = (B.gd.edid(B.gd.from_key(b)) or '').lower()
                    except (KeyError, ValueError):
                        e = ''
                    self._road[b] = 'road' in e and 'block' not in e
                return self._road[b]
            return False
        self._gate = through

    def xy(self, i, j):
        return self.x0 + i * GRID, self.y0 + j * GRID

    def ij(self, x, y):
        return int(round((x - self.x0) / GRID)), int(round((y - self.y0) / GRID))

    def blocked(self, i, j):
        if (i, j) not in self.block:
            import townbuild
            x, y = self.xy(i, j)
            g = self.B.ground.at(x, y)
            if g is None or g < 8:
                self.block[(i, j)] = True
            else:
                fp = [(x - 44, y - 44), (x + 44, y - 44), (x + 44, y + 44), (x - 44, y + 44)]
                self.block[(i, j)] = any(big and townbuild.overlap(fp, ofp) and not self.B.clearable(ck, rk) and not self._gate(ck, rk)
                                         for ck, rk, ofp, big, _o in self.B.w.near(fp))
        return self.block[(i, j)]

    def free_near(self, x, y, reach=10):
        i0, j0 = self.ij(x, y)
        best = None
        for di in range(-reach, reach + 1):
            for dj in range(-reach, reach + 1):
                i, j = i0 + di, j0 + dj
                if 0 <= i < self.nx and 0 <= j < self.ny and not self.blocked(i, j):
                    d = di * di + dj * dj
                    if best is None or d < best[0]:
                        best = (d, (i, j))
        return best[1] if best else None

    def toward(self, x, y, fx, fy, reach=14):
        """The open grid point by (x, y) on the side facing (fx, fy): a hall's middle is inside it, and its nearest open
        ground may lie behind it, past the town's wall."""
        i0, j0 = self.ij(x, y)
        best = None
        for di in range(-reach, reach + 1):
            for dj in range(-reach, reach + 1):
                i, j = i0 + di, j0 + dj
                if 0 <= i < self.nx and 0 <= j < self.ny and not self.blocked(i, j):
                    px, py = self.xy(i, j)
                    c = math.hypot(px - x, py - y) + 0.6 * math.hypot(px - fx, py - fy)
                    if best is None or c < best[0]:
                        best = (c, (i, j))
        return best[1] if best else None

    def walk(self, a, b, limit=400000):
        """[(x, y)] from a to b (b is reached on its side facing a), or None."""
        import heapq
        s, t = self.free_near(*a), self.toward(b[0], b[1], a[0], a[1])
        if s is None or t is None:
            return None
        g = self.B.ground.at
        h = lambda p: math.hypot(p[0] - t[0], p[1] - t[1]) * SHARED
        best, came, todo = {s: 0.0}, {}, [(h(s), s)]
        steps = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
        n = 0
        while todo and n < limit:
            _f, p = heapq.heappop(todo)
            n += 1
            if p == t:
                out = [p]
                while p in came:
                    p = came[p]
                    out.append(p)
                return [self.xy(*q) for q in reversed(out)]
            zp = g(*self.xy(*p)) or 0.0
            for di, dj in steps:
                q = (p[0] + di, p[1] + dj)
                if not (0 <= q[0] < self.nx and 0 <= q[1] < self.ny) or self.blocked(*q):
                    continue
                run = math.hypot(di, dj)
                rise = abs((g(*self.xy(*q)) or 0.0) - zp) / (run * GRID)
                nc = best[p] + run * (1.0 + GRADE_COST * rise * rise) * (SHARED if q in self.laid else 1.0)
                if nc < best.get(q, 1e18):
                    best[q] = nc
                    came[q] = p
                    heapq.heappush(todo, (nc + h(q), q))
        return None

    def lay(self, pts):
        for x, y in pts:
            self.laid.add(self.ij(x, y))


def _smooth(pts, rounds=3):
    pts = list(pts)
    for _ in range(rounds):
        if len(pts) < 3:
            return pts
        pts = [pts[0]] + [((a[0] + 2 * b[0] + c[0]) / 4, (a[1] + 2 * b[1] + c[1]) / 4) for a, b, c in zip(pts, pts[1:], pts[2:])] + [pts[-1]]
    return pts


def _noise(x, y):
    """A steady 0..1 roughness by place (the same every run)."""
    v = math.sin(x * 0.0113 + y * 0.0071) * 0.5 + math.sin(x * 0.0037 - y * 0.0123) * 0.35 + math.sin((x + y) * 0.029) * 0.15
    return 0.5 + 0.5 * v


def lay_paint(quarter, i, key, texinfo, a):
    """Paint a path layer at index i of a land quarter: on top, the layers under it faded by as much (no grass through it).
    Returns 1 if the quarter was full and its faintest layer gave way."""
    gave = 0
    lay = next((l for l in quarter['layers'] if l.get('key') == key), None)
    if lay is None:
        lay = {'tex': texinfo, 'key': key, 'a': [0.0] * 289}
        if len(quarter['layers']) >= 6:
            weak = min(range(len(quarter['layers'])), key=lambda n: sum(quarter['layers'][n]['a']))
            quarter['layers'].pop(weak)
            gave = 1
        quarter['layers'].append(lay)
    elif quarter['layers'][-1] is not lay:
        quarter['layers'].remove(lay)
        quarter['layers'].append(lay)
    lay['a'][i] = round(max(lay['a'][i], a), 3)
    for other in quarter['layers'][:-1]:
        other['a'][i] = round(other['a'][i] * (1.0 - a), 3)
    return gave


def _paint(gd, pr, B, W, legs, mid):
    """Paints legs into the ground (stone in town, earth out), takes what grows or lies on them out. Returns
    (painted land squares, layers that gave way, things taken out, on_path(x, y, r)): the land stays in B.forms."""
    import land as landmod
    # the paint
    keys = {}
    for e in (STONE, EARTH):
        f = next((f for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX' and gd.edid(f) == e), None)
        if f is None:
            raise ValueError('the game has no ground %s' % e)
        keys[e] = (gd.key(f), landmod.texture_of_fid(gd, f, {}))
    want, on_line = {}, {}
    for _name, pts in legs:
        dense = []
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.dist(a, b) // 32))
            dense += [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(n)]
        for x, y in dense:
            on_line.setdefault((int(x // 256), int(y // 256)), []).append((x, y))
            tex = STONE if math.hypot(x - mid[0], y - mid[1]) < TOWN else EARTH
            reach = FULL + FADE + 30
            for gy in range(int((y - reach) // 128), int((y + reach) // 128) + 2):
                for gx in range(int((x - reach) // 128), int((x + reach) // 128) + 2):
                    d = math.hypot(gx * 128.0 - x, gy * 128.0 - y)
                    rough = _noise(gx * 128.0, gy * 128.0)
                    edge = FULL + (rough - 0.5) * 50.0            # (a worn edge, not a ruled one)
                    a = (1.0 if d < edge else max(0.0, 1.0 - (d - edge) / FADE)) * (0.85 + 0.15 * rough)
                    if a > want.get((gx, gy), (0.0,))[0]:
                        want[(gx, gy)] = (round(a, 3), tex)
    painted, gave = set(), 0
    for (gx, gy), (a, tex) in want.items():
        if a <= 0.0:
            continue
        key, texinfo = keys[tex]
        for cx in ({gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}):
            for cy in ({gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}):
                f = B._form((cx, cy))
                if not f:
                    continue
                if (cx, cy) not in painted:
                    # (Builder copies a mod's land shallowly: a land entry is only ever replaced whole, never changed
                    # in place, so the quarters painted here are copies of their own)
                    f['q'] = json.loads(json.dumps(f['q']))
                r, c = gy - cy * 32, gx - cx * 32
                for q in range(4):
                    rr, cc = r - (q >> 1) * 16, c - (q & 1) * 16
                    if 0 <= rr <= 16 and 0 <= cc <= 16:
                        gave += lay_paint(f['q'][q], rr * 17 + cc, key, texinfo, a)
                        painted.add((cx, cy))

    def on_path(x, y, r=CLEAR):
        return any(math.hypot(x - a, y - b) < r for i in (-1, 0, 1) for j in (-1, 0, 1)
                   for a, b in on_line.get((int(x // 256) + i, int(y // 256) + j), ()))
    # what grows or lies on the paths
    gone = 0
    for (cx, cy) in painted:
        cell = B.w.grid.get((cx, cy))
        ck = gd.key(cell) if cell is not None else None
        for rk, r in ((pr.cells.get(ck) or {}).get('refs', {}).items() if ck else ()):
            p = r.get('p')
            if p and not r.get('removed') and on_path(p[0], p[1]) and B.clearable(ck, rk) and r.get('base') not in W.passable:
                B.take_out([(ck, rk)])
                gone += 1
    return painted, gave, gone, on_path


def paths(gd, pr, land, side, cat=None):
    """(ops, report, cells): the Huáng town's paths painted, plants off them, kerbs along the paved ones."""
    import activity
    import indoors
    import land as landmod
    import modelsets
    import ridgeplaces
    import server
    import townbuild
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    B = ridgeplaces.Builder(gd, pr, land.world, side, cat)
    mid = land.middle
    by = {}
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if r.get('removed') or not r.get('p') or not str(r.get('base', '')).startswith('+'):
                continue
            e = _edid(pr, r['base'])
            if e.startswith(('FOLabSettlerGate', 'FOLabSettlerScreen', 'FOLabSettlerHall', 'FOLabBambooCanoeShed')):
                by.setdefault('gate' if e.startswith('FOLabSettlerGate') else e.rstrip('0123456789'), []).append((r['p'][0], r['p'][1]))
    near = lambda pts: [p for p in pts if math.hypot(p[0] - mid[0], p[1] - mid[1]) < COMPOUND_REACH]
    gates = sorted(near(by.get('gate', [])), key=lambda p: (p[0], p[1]))
    yards = near(by.get('FOLabSettlerScreen', []))
    halls = near(by.get('FOLabSettlerHall', []) + by.get('FOLabSettlerHallRed', []))
    maize, named = [], {}
    for xy, cell in gd.grid(land.world).items():
        if math.hypot((xy[0] + 0.5) * 4096 - mid[0], (xy[1] + 0.5) * 4096 - mid[1]) > COMPOUND_REACH + 4096:
            continue
        for _rk, base, p, _s in indoors.placed(gd, pr, gd.key(cell)):
            if base not in named:
                named[base] = indoors._edid(gd, pr, base)
            if named[base] in activity.MAIZE and land.in_compound(p[0], p[1]):
                maize.append((p[0], p[1]))
    fields = [f for f in activity.clusters(maize, reach=FIELD_REACH)
              if min(math.hypot(p[0] - mid[0], p[1] - mid[1]) for p in f) < FIELDS_NEAR]
    sheds = sorted(by.get('FOLabBambooCanoeShed', []), key=lambda p: min((math.hypot(p[0] - s[0], p[1] - s[1]) for s in land.ship), default=1e9))[:1]
    allp = gates + yards + halls + maize + sheds
    if not gates or not allp:
        raise ValueError('no Huáng gates to lay paths from')
    pad = 2500.0
    box = (min(p[0] for p in allp) - pad, min(p[1] for p in allp) - pad, max(p[0] for p in allp) + pad, max(p[1] for p in allp) + pad)
    W = Ways(B, box)
    W.passable |= {b for b, e in named.items() if e in activity.MAIZE}
    legs, rep = [], {'legs': {}, 'failed': []}

    def go(name, a, b):
        pts = W.walk(a, b)
        if not pts:
            rep['failed'].append(name)
            return
        if sum(math.dist(p, q) for p, q in zip(pts, pts[1:])) > (DETOUR_OUT if name.startswith(('field', 'landing')) else DETOUR) * math.dist(a, b) + 1000.0:
            rep.setdefault('too far round', []).append(name)
            return
        W.lay(pts)
        legs.append((name, _smooth(pts)))
        rep['legs'][name] = round(sum(math.dist(p, q) for p, q in zip(pts, pts[1:])))
    nearest = lambda p, pts: min(pts, key=lambda q: math.hypot(q[0] - p[0], q[1] - p[1]))
    for k, (a, b) in enumerate(zip(gates, gates[1:])):
        go('gates %d-%d' % (k + 1, k + 2), a, b)
    for k, y in enumerate(yards):
        go('courtyard %d' % (k + 1), nearest(y, gates), y)
    for k, h in enumerate(halls):
        go('hall %d' % (k + 1), nearest(h, yards or gates), h)
    def from_laid(b, fallback):
        """Where a way out starts: the nearest point of a path already laid (the town's wall lets you out only at its
        ends: each field's own way round would be a second ring road), else the nearest gate."""
        laid = [W.xy(*q) for q in W.laid]
        return min(laid, key=lambda q: math.hypot(q[0] - b[0], q[1] - b[1])) if laid else fallback
    order = sorted(fields, key=lambda f: min(math.hypot(p[0] - g[0], p[1] - g[1]) for p in f for g in gates))
    for k, f in enumerate(order):
        fx, fy = sum(p[0] for p in f) / len(f), sum(p[1] for p in f) / len(f)
        g0 = nearest((fx, fy), gates)
        end = nearest(g0, f)
        a = g0 if k == 0 else from_laid(end, g0)
        go('field %d' % (k + 1), a, nearest(a, f))
    for s in sheds:
        go('landing', from_laid(s, nearest(s, gates)), s)
    painted, gave, gone, on_path = _paint(gd, pr, B, W, legs, mid)
    # kerbs along the paved ways
    k_ops, made = modelsets.put(pr, 'huang_path_kerb')
    kerb = made['key'] or '$model_huang_path_kerb'
    kerbs = []
    for _name, pts in legs:
        run = 0.0
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            run += L
            if run < 128.0 * KERB_EVERY or not L or not any(math.hypot(a[0] - y[0], a[1] - y[1]) < KERB_NEAR for y in yards):
                continue
            run = 0.0
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            for s in (1, -1):
                x, y = a[0] - uy * KERB_OFF * s, a[1] + ux * KERB_OFF * s
                if W.blocked(*W.ij(x, y)) or on_path(x, y, KERB_OFF - 30):
                    continue
                z = B.ground.at(x, y)
                cell = B.w.grid.get((int(x // 4096), int(y // 4096)))
                if z is None or cell is None:
                    continue
                rz = math.atan2(-uy, ux) % math.tau         # (its x along the path; the game turns clockwise from above)
                kerbs.append({'op': 'add', 'cell': gd.key(cell), 'base': kerb, 's': 1.0,
                              'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz, 4)]})
    lands = [{'op': 'land', 'cell': gd.key(B.w.grid[k]), 'land': B.forms[k]} for k in sorted(B.forms) if k in painted]
    cells = sorted({o['cell'] for o in lands} | {o['cell'] for o in B.ops if o.get('cell')} | {o['cell'] for o in kerbs})
    rep.update({'land cells': len(lands), 'plants taken out': gone, 'layers given way': gave, 'kerbs': len(kerbs),
                'gates': len(gates), 'courtyards': len(yards), 'halls': len(halls), 'fields': len(fields), 'landing': bool(sheds),
                'lines': {n: [[round(x), round(y)] for x, y in p] for n, p in legs}})
    return k_ops + lands + B.ops + kerbs, rep, cells


_register()


# ---------- a side gate to the freighter's landing ----------

LANDING_IN = 320.0                  # (the path's points this far each side of the side gate)


def _seg_cross(a, b, c, d):
    """Where segment a-b crosses segment c-d, as t along a-b, or None."""
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    return t if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None


def landing_gate(gd, pr, land, side, cat=None):
    """(ops, report, cells, (from, to)): the wall length between the last gate and the freighter's landing swapped for a
    side gate (settlerset.wall_gate, same frame: the wall's collision opens only at the gate), and a footpath from the
    last gate through it down to the canoe sheds, painted as the town's others. from/to are for the walk check."""
    import modelsets
    import ridgeplaces
    import server
    import townbuild
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    B = ridgeplaces.Builder(gd, pr, land.world, side, cat)
    mid = land.middle
    gates, sheds, walls = [], [], []
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            if r.get('removed') or not r.get('p') or not str(r.get('base', '')).startswith('+'):
                continue
            e = _edid(pr, r['base'])
            if e.startswith('FOLabSettlerGate'):
                gates.append(r['p'])
            elif e == 'FOLabBambooCanoeShed':
                sheds.append(r['p'])
            elif e == 'FOLabSettlerWall' and land.in_compound(r['p'][0], r['p'][1]):
                walls.append((ck, rk, r['p'], float(r.get('s') or 1.0)))
    if not sheds or not land.ship:
        raise ValueError('no canoe sheds by the freighter')
    ship = land.ship[0]
    shed = min(sheds, key=lambda p: math.hypot(p[0] - ship[0], p[1] - ship[1]))
    start = min((g for g in gates if land.in_compound(g[0], g[1])), key=lambda g: math.hypot(g[0] - shed[0], g[1] - shed[1]))
    best = None
    for ck, rk, p, s in walls:
        rz = p[5] if len(p) > 5 else 0.0
        ux, uy = math.cos(rz), -math.sin(rz)              # (the wall's own x, in the world)
        a = (p[0] - ux * 500 * s, p[1] - uy * 500 * s)
        b = (p[0] + ux * 500 * s, p[1] + uy * 500 * s)
        t = _seg_cross(start[:2], shed[:2], a, b)
        if t is not None and (best is None or t < best[0]):
            best = (t, ck, rk, p, s, rz)
    pad = 2500.0
    xs = [start[0], shed[0]]
    ys = [start[1], shed[1]]
    if best is None:
        # (no wall between: a footpath from the last gate, over the road, down to the sheds)
        W = Ways(B, (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad))
        pts = W.walk(start[:2], shed[:2])
        if not pts:
            raise ValueError('no way from the last gate to the landing')
        pts = _smooth(pts)
        rep = {'wall swapped': None, 'from gate': [round(start[0]), round(start[1])], 'to sheds': [round(shed[0]), round(shed[1])],
               'length': round(sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))), 'straight': round(math.dist(start[:2], shed[:2]))}
        painted, gave, gone, _on = _paint(gd, pr, B, W, [('landing', pts)], mid)
        lands = [{'op': 'land', 'cell': gd.key(B.w.grid[k]), 'land': B.forms[k]} for k in sorted(B.forms) if k in painted]
        cells = sorted({o['cell'] for o in lands} | {o['cell'] for o in B.ops if o.get('cell')})
        rep.update({'land cells': len(lands), 'plants taken out': gone, 'layers given way': gave, 'line': [[round(x), round(y)] for x, y in pts]})
        return lands + B.ops, rep, cells, ((start[0], start[1]), (shed[0], shed[1]))
    _t, wck, wrk, wp, ws, wrz = best
    nx, ny = math.sin(wrz), math.cos(wrz)                 # (the wall's own y: across it)
    if (shed[0] - wp[0]) * nx + (shed[1] - wp[1]) * ny < 0:
        nx, ny = -nx, -ny
    inner = (wp[0] - nx * LANDING_IN, wp[1] - ny * LANDING_IN)
    outer = (wp[0] + nx * LANDING_IN, wp[1] + ny * LANDING_IN)
    xs.append(wp[0])
    ys.append(wp[1])
    W = Ways(B, (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad))
    leg_in, leg_out = W.walk(start[:2], inner), W.walk(outer, shed[:2])
    rep = {'wall swapped': wrk, 'gate at': [round(wp[0]), round(wp[1])], 'from gate': [round(start[0]), round(start[1])],
           'to sheds': [round(shed[0]), round(shed[1])]}
    if not leg_in or not leg_out:
        raise ValueError('no way to the side gate (%s) or from it to the landing (%s)' % (bool(leg_in), bool(leg_out)))
    pts = _smooth(leg_in) + [(wp[0], wp[1])] + _smooth(leg_out)
    rep['length'] = round(sum(math.dist(a, b) for a, b in zip(pts, pts[1:])))
    rep['straight'] = round(math.dist(start[:2], shed[:2]))
    painted, gave, gone, _on = _paint(gd, pr, B, W, [('landing', pts)], mid)
    g_ops, _made = modelsets.put(pr, 'settler_wall_gate')
    gate_key = _made['key'] or '$model_settler_wall_gate'
    ops = list(g_ops) + [{'op': 'swap', 'cell': wck, 'ref': wrk, 'base': gate_key}]
    lands = [{'op': 'land', 'cell': gd.key(B.w.grid[k]), 'land': B.forms[k]} for k in sorted(B.forms) if k in painted]
    cells = sorted({o['cell'] for o in lands} | {o['cell'] for o in B.ops if o.get('cell')} | {wck})
    rep.update({'land cells': len(lands), 'plants taken out': gone, 'layers given way': gave,
                'line': [[round(x), round(y)] for x, y in pts]})
    return ops + lands + B.ops, rep, cells, ((start[0], start[1]), (shed[0], shed[1]))


def nav_reach(gd, pr, a, b, near=400.0):
    """Whether the mod's navmeshes join the ground by a to the ground by b, through every cell's mesh and their links to
    each other: (reached, triangles walked). Each end is the triangle nearest it within `near`."""
    forms = {}                                  # (NAVM form key -> (cell, mesh index, mesh))
    for ck, m in pr.navmesh.items():
        for k, one in enumerate([m] + list(m.get('others', []))):
            if one.get('form'):
                forms[one['form']] = one

    def nearest(p):
        best = None
        for f, m in forms.items():
            v = m['verts']
            for i, t in enumerate(m['tris']):
                cx = (v[t[0]][0] + v[t[1]][0] + v[t[2]][0]) / 3
                cy = (v[t[0]][1] + v[t[1]][1] + v[t[2]][1]) / 3
                d = math.hypot(cx - p[0], cy - p[1])
                if d < near and (best is None or d < best[0]):
                    best = (d, (f, i))
        return best[1] if best else None
    s, t = nearest(a), nearest(b)
    if s is None or t is None:
        return False, 0
    seen, todo = {s}, [s]
    while todo:
        f, i = todo.pop()
        if (f, i) == t:
            return True, len(seen)
        m = forms[f]
        tri = m['tris'][i]
        for e in range(3):
            n = tri[3 + e]
            if n == 65535 or n is None:
                continue
            if tri[6] >> e & 1:                 # (an edge into the next cell's mesh: ext[n] is (kind, its form, its triangle))
                ext = m.get('ext') or []
                if n < len(ext) and ext[n][1] in forms:
                    q = (ext[n][1], ext[n][2])
                else:
                    continue
            else:
                q = (f, n)
            if q not in seen:
                seen.add(q)
                todo.append(q)
    return False, len(seen)


# ---------- raiders on the shore ----------

def shore_points(gd, pr, land):
    """[(x, y)] of the plain's sand: squares no higher than SHORE_HIGH with the sea within SHORE_SEA squares."""
    import roadgen
    G = roadgen.Ground(gd, pr, land.world)
    S = PLAIN_STEP
    sq = land.plain()
    out = []
    for i, j in sorted(sq):
        h = G.at(i * S, j * S)
        if h is None or not (8.0 < h < SHORE_HIGH):
            continue
        if any((G.at((i + a) * S, (j + b) * S) or 0.0) < 0.0 for a in range(-SHORE_SEA, SHORE_SEA + 1) for b in range(-SHORE_SEA, SHORE_SEA + 1)):
            out.append((i * S, j * S))
    return out


def sea_distance(gd, pr, land, x, y, reach=4000.0, step=256.0):
    """How far (x, y) is from the sea (ground under 0), up to reach."""
    import roadgen
    G = getattr(land, '_G', None) or roadgen.Ground(gd, pr, land.world)
    land._G = G
    r = step
    while r <= reach:
        n = max(8, int(2 * math.pi * r / step))
        if any((G.at(x + r * math.sin(2 * math.pi * k / n), y + r * math.cos(2 * math.pi * k / n)) or 0.0) < 0.0 for k in range(n)):
            return r
        r += step
    return reach + step


def raiders(gd, pr, land, ctx):
    """(ops, report): RAIDS small parties of RAID_EACH pirates on the Huáng shore, each by a spot of sand away from the town
    and from each other, facing the town, kept by their spot (RAIDER_PACKAGE: they sandbox round where they stand, never
    walk inland). One record of their own (RAIDER), a copy of the mod's pirate (RAIDER_FROM) with that package only."""
    import activity
    import api_characters as ac
    if any(recordio.field(r, 'EDID') == RAIDER for r in pr.records.values()):
        return [], {'raiders': 'already there'}
    src = next((k for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'EDID') == RAIDER_FROM), None)
    if src is None:
        raise ValueError('the mod has no %s to make raiders of' % RAIDER_FROM)
    rec = json.loads(json.dumps(pr.records[src]))
    recordio.set_field(rec, 'EDID', RAIDER, label='Editor ID')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'PKID']
    ac.insert(rec, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(ac._find(gd, 'PACK', RAIDER_PACKAGE))})
    rec['copied_from'] = src
    o = activity.Out(ctx)
    key = o.keys.add(rec)
    mid = land.middle
    sand = sorted((p for p in shore_points(gd, pr, land) if math.hypot(p[0] - mid[0], p[1] - mid[1]) >= RAID_FROM_TOWN),
                  key=lambda p: math.hypot(p[0] - mid[0], p[1] - mid[1]))
    sand = [p for p in sand if sea_distance(gd, pr, land, p[0], p[1], reach=RAID_SEA, step=128.0) <= RAID_SEA]
    parties = []
    for x, y in sand:
        if len(parties) >= RAIDS:
            break
        if any(math.hypot(x - a, y - b) < RAID_APART for a, b, _n in parties):
            continue
        got = [s for s in ctx.around(x, y, RAID_EACH, radii=(0.1, 160, 260, 360), turns=10, apart=110.0)
               if land.inside(s[0], s[1]) and sea_distance(gd, pr, land, s[0], s[1], reach=RAID_SEA, step=128.0) <= RAID_SEA]
        if len(got) < RAID_EACH:
            continue
        for s in got:
            o.person_rec(key, s[0], s[1], s[2], math.atan2(mid[0] - s[0], mid[1] - s[1]) % math.tau, 'raider')
        parties.append((x, y, len(got)))
    ops, rep = o.done({'parties': [[round(a), round(b), n] for a, b, n in parties]})
    return ops, rep


def pirate_audit(gd, pr, land):
    """Every pirate in or round the Huáng land, and whether anything can take one inland: [(cell, ref, editor ID, (x, y),
    'raider'|'inland'|'outside', sea distance)], and the packages of each pirate kind with where they lead."""
    import indoors
    rows, kinds = [], {}
    box = [min(p[0] for p in land.posts.values()) - 15000, min(p[1] for p in land.posts.values()) - 15000,
           max(p[0] for p in land.posts.values()) + 15000, max(p[1] for p in land.posts.values()) + 15000]
    for xy, c in gd.grid(land.world).items():
        mx, my = (xy[0] + 0.5) * 4096, (xy[1] + 0.5) * 4096
        if not (box[0] <= mx <= box[2] and box[1] <= my <= box[3]):
            continue
        ck = gd.key(c)
        own = (pr.cells.get(ck) or {}).get('refs', {})
        for rk, base, p, _s in indoors.placed(gd, pr, ck):
            e = indoors._edid(gd, pr, base)
            if 'Pirate' not in e:
                continue
            kinds.setdefault(base, e)
            where = 'outside'
            if land.inside(p[0], p[1]):
                where = 'raider' if e == RAIDER else 'inland'
            link = (own.get(rk) or {}).get('link')
            rows.append([ck, rk, e, [round(p[0]), round(p[1])], where, link])
    packs = {}
    for b, e in kinds.items():
        rec = pr.records.get(b) or {}
        packs[e] = [indoors._edid(gd, pr, s['value']) for s in rec.get('subs', ()) if s['tag'] == 'PKID']
    return rows, packs


# ---------- the paths redone (the user, 22 Nov 2026, of the first: "what on earth is this. the path looks terrible") ----------
# What showed in game: the villa's cobbles read as flat patchy grey, the kerbs lay loose across the way like debris, and
# grass grew through: a path two land points wide can't keep grass off (the game samples grass every four points and
# spreads it over 512, and a faded layer lets the ground's own grass through). Now: FOLab's own paving (flagstones with
# joints, warm grey) in town and warm packed earth going out, each a ground of the mod's own with no grass, laid at full
# strength with a clean edge, wider; every grass sample whose blades would reach a path moved to its ground's twin with no
# grass (plantgrass.points_under / clear_points); no kerbs.

GROUNDS = {
    # name: (editor ID, picture path under textures, the game ground copied (physics, shine), bump, shine)
    'paving': ('FOLabHuangPaving', 'landscape\\folab\\huangpaving', 'Pavement', 3.0, 24),
    'earth': ('FOLabHuangEarth', 'landscape\\folab\\huangearth', 'LDirtPathWasteland01', 2.0, 8),
}
PAVED_HALF, EARTH_HALF = 150.0, 100.0      # (land points this near a path's line are path, full: ~300 and ~200 across)
GRASS_OFF = 40.0                           # (and no grass blade reaches within this of a path's edge)
OLD = (STONE, EARTH)                       # (the first paths' grounds: taken off along their lines)
OLD_REACH = 260.0


def paving_canvas(size=512, seed=4301):
    """Flagstones in running bond, as old Chinese courtyards are paved: 3 across and 4 down a picture (the game repeats a
    ground's picture 6 times a quarter of a cell: a stone ~114 x 85 units), each a lighter or darker warm grey of one
    stone, mortar joints sunk."""
    import texpaint as tp
    rnd = random.Random(seed)
    c = tp.Canvas(size, size)
    rows, cols = 4, 3                                       # (stones ~114 x 85 units: big flags, not bricks)
    rh, cw = size / rows, size / cols
    tones = {}
    for r in range(rows):
        for k in range(cols + 1):
            t = rnd.uniform(-1, 1)                          # (one stone lighter or darker than the next, all one stone)
            tones[(r, k)] = ((146 + 12 * t, 139 + 11 * t, 125 + 10 * t), rnd.uniform(0.0, 1.0))
    grain, big = tp.Noise(seed, 64), tp.Noise(seed + 1, 8)
    joint = 2.4                                             # (fine joints: wider and darker read as tiles, close up)

    def fn(x, y):
        r = int(y // rh)
        off = cw / 2 if r % 2 else 0.0
        xx = (x - off) % size
        k = int(xx // cw)
        dx = min(xx - k * cw, (k + 1) * cw - xx)
        dy = min(y - r * rh, (r + 1) * rh - y)
        edge = min(dx, dy)
        col, wear = tones[(r, k % cols)]
        g = grain.at(x * 64.0 / size, y * 64.0 / size)
        b = big.at(x * 8.0 / size, y * 8.0 / size)
        if edge < joint:                                    # (the joint: mortar a shade darker than the stone, a little moss)
            m = 0.72 + 0.1 * g
            return (118 * m + 8 * b, 113 * m + 10 * b, 100 * m + 5 * b), 0.3
        f = 0.9 + 0.12 * (g - 0.5) + 0.08 * (b - 0.5)
        rim = min(1.0, (edge - joint) / 6.0)                # (stone edges worn round and a little darker)
        f *= 0.86 + 0.14 * rim
        if wear > 0.7:                                      # (some stones stained by rain and feet)
            f *= 0.93 + 0.05 * g
        return tuple(v * f for v in col), 0.42 + 0.18 * rim + 0.05 * (g - 0.5)
    c.paint(fn)
    return c


def earth_canvas(size=512, seed=4311):
    """Packed earth trodden hard: warm brown, fine grit, small pebbles, faint darker wear."""
    import texpaint as tp
    rnd = random.Random(seed)
    c = tp.Canvas(size, size)
    fine, mid, big = tp.Noise(seed, 128), tp.Noise(seed + 1, 32), tp.Noise(seed + 2, 6)
    cells = {}
    for _ in range(140):
        px, py, r, t = rnd.uniform(0, size), rnd.uniform(0, size), rnd.uniform(2.0, 5.0), rnd.uniform(0.85, 1.25)
        cells.setdefault((int(px // 32), int(py // 32)), []).append((px, py, r, t))
    base = (150, 116, 82)
    n = size // 32

    def fn(x, y):
        g, m, b = fine.at(x * 128.0 / size, y * 128.0 / size), mid.at(x * 32.0 / size, y * 32.0 / size), big.at(x * 6.0 / size, y * 6.0 / size)
        f = 0.9 + 0.14 * (g - 0.5) + 0.12 * (m - 0.5) + 0.1 * (b - 0.5)
        col = tuple(v * f for v in base)
        h = 0.45 + 0.08 * (g - 0.5)
        for a in (-1, 0, 1):
            for bb in (-1, 0, 1):
                for px, py, r, t in cells.get(((int(x // 32) + a) % n, (int(y // 32) + bb) % n), ()):
                    d = math.hypot(((x - px + size / 2) % size) - size / 2, ((y - py + size / 2) % size) - size / 2)
                    if d < r:
                        col = (128 * t, 118 * t, 104 * t)
                        h = 0.6 + 0.2 * (1 - d / r)
        return col, h
    c.paint(fn)
    return c


def ground_ops(gd, pr):
    """(ops, {name: (LTEX key, picture path)}): the paving's and the earth's pictures among the mod's own files, and a TXST
    and an LTEX of the mod's own for each (no grass), copied from the game ground named in GROUNDS for physics and shine.
    Keys are taken as planned ('record' ops), so land laid in the same go can name them."""
    import activity
    import library
    out, got = [], {}
    root = library.assets_dir(pr)
    have = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'LTEX'}
    for name, (edid, rel, like, bump, shine) in GROUNDS.items():
        canvas = paving_canvas() if name == 'paving' else earth_canvas()
        col, nor = canvas.files(bump=bump, shine=shine, game=True)
        library._put(root, 'textures\\%s.dds' % rel, col)
        library._put(root, 'textures\\%s_n.dds' % rel, nor)
        tex = 'textures\\%s.dds' % rel
        if edid in have:
            got[name] = (have[edid], tex)
            continue
        lf = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX' and gd.edid(f) == like)
        ltex = recordio.load(gd, lf)
        txst = recordio.load(gd, gd.from_key(recordio.field(ltex, 'TNAM')))
        tk, lk = activity._new_key(pr), activity._new_key(pr)
        txst = {'type': 'TXST', 'flags': 0, 'src': '', 'subs': [dict(s) for s in txst['subs']]}
        shown = rel[0].upper() + rel[1:]
        for s in txst['subs']:
            if s['tag'] == 'EDID':
                s['value'] = edid + 'Set'
            elif s['tag'] == 'TX00':
                s['value'] = shown + '.dds'
            elif s['tag'] == 'TX01':
                s['value'] = shown + '_n.dds'
        subs = [dict(s) for s in ltex['subs'] if s['tag'] in ('EDID', 'TNAM', 'HNAM', 'SNAM')]
        for s in subs:
            if s['tag'] == 'EDID':
                s['value'] = edid
            elif s['tag'] == 'TNAM':
                s['value'] = tk
        out += [{'op': 'record', 'key': tk, 'record': txst},
                {'op': 'record', 'key': lk, 'record': {'type': 'LTEX', 'flags': 0, 'src': '', 'subs': subs}}]
        got[name] = (lk, tex)
    return out, got


def _dense(pts, step=32.0):
    out = []
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) // step))
        out += [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(n)]
    return out + ([tuple(pts[-1])] if pts else [])


def redo_paths(gd, pr, land, side, lines, cat=None):
    """(ops, report, cells): the paths along `lines` ({name: [(x, y)]}, as laid before) laid again: the first paint taken
    off, FOLab's paving in town and earth going out at full strength, grass kept off, the kerbs taken out."""
    import plantgrass
    import ridgeplaces
    import server
    import townbuild
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    B = ridgeplaces.Builder(gd, pr, land.world, side, cat)
    mid = land.middle
    g_ops, grounds = ground_ops(gd, pr)
    old_keys = set()
    for e in OLD:
        f = next((f for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX' and gd.edid(f) == e), None)
        if f is not None:
            old_keys.add(gd.key(f))
    touched = set()

    def form(cx, cy):
        f = B._form((cx, cy))
        if f is not None and (cx, cy) not in touched:
            f['q'] = json.loads(json.dumps(f['q']))      # (a land entry is replaced whole, never changed in place)
            touched.add((cx, cy))
        return f

    def points(pts, reach):
        """{(gx, gy): distance} of land points within reach of a line."""
        best = {}
        for x, y in _dense(pts):
            for gy in range(int((y - reach) // 128), int((y + reach) // 128) + 2):
                for gx in range(int((x - reach) // 128), int((x + reach) // 128) + 2):
                    d = math.hypot(gx * 128.0 - x, gy * 128.0 - y)
                    if d <= reach and d < best.get((gx, gy), 1e9):
                        best[(gx, gy)] = d
        return best

    def each(gx, gy):
        for cx in ({gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}):
            for cy in ({gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}):
                f = form(cx, cy)
                if not f:
                    continue
                r, c = gy - cy * 32, gx - cx * 32
                for q in range(4):
                    rr, cc = r - (q >> 1) * 16, c - (q & 1) * 16
                    if 0 <= rr <= 16 and 0 <= cc <= 16:
                        yield f, (cx, cy), q, rr * 17 + cc
    rep = {'old taken off': 0, 'paved points': 0, 'earth points': 0, 'gave way': 0}
    # the first paint off
    for pts in lines.values():
        for (gx, gy), _d in points(pts, OLD_REACH).items():
            for f, _xy, q, i in each(gx, gy):
                for l in f['q'][q]['layers']:
                    if l.get('key') in old_keys and l['a'][i] > 0:
                        l['a'][i] = 0.0
                        rep['old taken off'] += 1
    for k in touched:
        for q in B.forms[k]['q']:
            q['layers'] = [l for l in q['layers'] if not (l.get('key') in old_keys and not any(l['a']))]
    # the new paint: full strength, a clean edge
    for name, pts in lines.items():
        out = name.startswith(('field', 'landing'))
        for (gx, gy), d in points(pts, PAVED_HALF).items():
            town = not out and math.hypot(gx * 128.0 - mid[0], gy * 128.0 - mid[1]) < TOWN
            if d > (PAVED_HALF if town else EARTH_HALF):
                continue
            key, tex = grounds['paving' if town else 'earth']
            for f, _xy, q, i in each(gx, gy):
                rep['gave way'] += lay_paint(f['q'][q], i, key, tex, 1.0)
            rep['paved points' if town else 'earth points'] += 1
    # no grass reaching a path
    grows, plain = plantgrass.ltex_rules(gd, pr)
    mine = {v[0] for v in grounds.values()}
    grows_any = lambda k: False if k in mine else grows(k)
    hits = {}
    for name, pts in lines.items():
        half = (EARTH_HALF if name.startswith(('field', 'landing')) else PAVED_HALF) + GRASS_OFF
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            if not L:
                continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            foot = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, ux, -uy, -L / 2 - half, -half, L / 2 + half, half)
            for xy, got in plantgrass.points_under(foot).items():
                hits.setdefault(xy, set()).update(got)
    g_rep = {}
    for xy, h in hits.items():
        f = form(*xy)
        if f:
            plantgrass.clear_points(f, h, grows_any, plain, g_rep)
    rep['grass'] = g_rep
    # the kerbs out
    kerb = next((k for k, r in pr.records.items() if recordio.field(r, 'EDID') == 'FOLabHuangPathKerb'), None)
    kerbs = [{'op': 'remove', 'cell': ck, 'ref': rk} for ck, c in pr.cells.items() for rk, r in c.get('refs', {}).items()
             if kerb and r.get('base') == kerb and not r.get('removed')]
    rep['kerbs out'] = len(kerbs)
    lands = [{'op': 'land', 'cell': gd.key(B.w.grid[k]), 'land': B.forms[k]} for k in sorted(touched) if k in B.w.grid]
    cells = sorted({o['cell'] for o in lands} | {o['cell'] for o in kerbs})
    rep['land cells'] = len(lands)
    return g_ops + lands + kerbs, rep, cells


# ---------- the town's ground (the user, 22 Nov 2026: "the path was too bumpy between homes, the grass grows through brick
# and path, it should be tastefully done"; of a courtyard: "as if proud people live here") ----------
# The town is a grid of walled courtyards along the road of gates, all turned one way: its ground is one turned rectangle
# round every settler piece (`town_box`). Inside it everything is paved (courtyards and alleys), at full strength; the
# ground is smoothed by relaxing the open land between what stands (each wall, hall, screen and gate keeps the ground under
# it, so their feet stay in it); every grass sample whose blades reach it moved onto its ground's twin with no grass; what
# grows or lies on it taken out; what else stands on moved ground moved with it.

TOWN_PIECES = ('FOLabSettlerWall', 'FOLabSettlerHall', 'FOLabSettlerScreen', 'FOLabSettlerGate')
TOWN_PAD = 160.0                # (the paving runs this far past the outermost walls)
HOLD = 96.0                     # (land points this near a piece's footprint keep their height)
RELAX = 60                      # (rounds of smoothing the open ground)
FOOT_UNDER = 8.0                # (ground raised under a piece comes to this under its foot: its footing stays in it)


def _footprint(p, s, ob, pad=0.0):
    rz = p[5] if len(p) > 5 else 0.0
    c, sn = math.cos(rz), math.sin(rz)
    return [(p[0] + (lx * c + ly * sn) * s, p[1] + (-lx * sn + ly * c) * s)
            for lx, ly in ((ob[0] - pad, ob[1] - pad), (ob[3] + pad, ob[1] - pad), (ob[3] + pad, ob[4] + pad), (ob[0] - pad, ob[4] + pad))]


def town_pieces(gd, pr, land):
    """[(cell, ref, editor ID, p, scale, OBND)] of the settler pieces standing in the town."""
    import indoors
    out = []
    for xy, c in gd.grid(land.world).items():
        if math.hypot((xy[0] + 0.5) * 4096 - land.middle[0], (xy[1] + 0.5) * 4096 - land.middle[1]) > COMPOUND_REACH:
            continue
        for rk, base, p, s in indoors.placed(gd, pr, gd.key(c)):
            if not base.startswith('+'):
                continue
            e = _edid(pr, base)
            if e.startswith(TOWN_PIECES) and land.in_compound(p[0], p[1]):
                ob = _obnd_of_record(pr.records.get(base))
                if ob:
                    out.append((gd.key(c), rk, e, list(p), float(s or 1.0), ob))
    return out


def _obnd_of_record(rec):
    sub = next((q for q in (rec or {}).get('subs', ()) if q.get('tag') == 'OBND' and q.get('kind') == 'struct'), None)
    return [f['value'] for f in sub['fields'] if 'name' in f] if sub else None


def town_box(pieces):
    """(cx, cy, cos, sin, x0, y0, x1, y1): the town's turned rectangle, as plantgrass's footprints are written (local to
    world: x + lx cos + ly sin, y - lx sin + ly cos), turned as its walls are."""
    walls = [p for _c, _r, e, p, _s, _o in pieces if e == 'FOLabSettlerWall']
    rz = (walls or [p for _c, _r, _e, p, _s, _o in pieces])[0][5]
    rz = rz % (math.pi / 2)
    c, s = math.cos(rz), math.sin(rz)
    pts = [q for _c, _r, _e, p, sc, ob in pieces for q in _footprint(p, sc, ob)]
    cx = sum(q[0] for q in pts) / len(pts)
    cy = sum(q[1] for q in pts) / len(pts)
    # (world to local: lx = dx cos - dy sin, ly = dx sin + dy cos)
    lxs = [(q[0] - cx) * c - (q[1] - cy) * s for q in pts]
    lys = [(q[0] - cx) * s + (q[1] - cy) * c for q in pts]
    return (cx, cy, c, s, min(lxs) - TOWN_PAD, min(lys) - TOWN_PAD, max(lxs) + TOWN_PAD, max(lys) + TOWN_PAD)


def in_box(box, x, y, pad=0.0):
    cx, cy, c, s, x0, y0, x1, y1 = box
    lx, ly = (x - cx) * c - (y - cy) * s, (x - cx) * s + (y - cy) * c
    return x0 - pad <= lx <= x1 + pad and y0 - pad <= ly <= y1 + pad


def _in_poly(x, y, poly):
    inside = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        if (ay > y) != (by > y) and x < ax + (bx - ax) * (y - ay) / (by - ay):
            inside = not inside
    return inside


def town_ground(gd, pr, land, side, lines, cat=None):
    """(ops, report, cells, box): the town's ground paved, smoothed and kept from grass, the paths beyond it earth (as
    redo_paths), plants off both, the kerbs out, what stands on moved ground moved with it."""
    import plantgrass
    import ridgeplaces
    import server
    import townbuild
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    B = ridgeplaces.Builder(gd, pr, land.world, side, cat)
    pieces = town_pieces(gd, pr, land)
    if not pieces:
        raise ValueError('no settler pieces in the town')
    box = town_box(pieces)
    g_ops, grounds = ground_ops(gd, pr)
    old_keys = {gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX' and gd.edid(f) in OLD}
    touched = set()

    def form(cx, cy):
        f = B._form((cx, cy))
        if f is not None and (cx, cy) not in touched:
            f['q'] = json.loads(json.dumps(f['q']))      # (a land entry is replaced whole, never changed in place)
            f['h'] = list(f['h'])
            B.ground.h[(cx, cy)] = f['h']
            touched.add((cx, cy))
        return f

    def each(gx, gy):
        for cx in ({gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}):
            for cy in ({gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}):
                f = form(cx, cy)
                if f:
                    yield f, (cx, cy), gy - cy * 32, gx - cx * 32
    rep = {'old taken off': 0, 'paved points': 0, 'earth points': 0, 'gave way': 0, 'smoothed points': 0}
    # the town's land points
    cx, cy, c, s, x0, y0, x1, y1 = box
    corners = [(cx + lx * c + ly * s, cy - lx * s + ly * c) for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    gxs = [q[0] for q in corners]
    gys = [q[1] for q in corners]
    town_pts = [(gx, gy) for gy in range(int(min(gys) // 128) - 1, int(max(gys) // 128) + 2)
                for gx in range(int(min(gxs) // 128) - 1, int(max(gxs) // 128) + 2) if in_box(box, gx * 128.0, gy * 128.0)]
    held_polys = [_footprint(p, sc, ob, HOLD) for _c, _r, _e, p, sc, ob in pieces]
    piece_refs = {pc[1] for pc in pieces}
    buckets = {}
    for pts in lines.values():
        for x, y in _dense(pts, 64.0):
            buckets.setdefault((int(x // 256), int(y // 256)), []).append((x, y))

    def near_line(x, y, reach):
        return any(math.hypot(x - a, y - b) <= reach for i in (-1, 0, 1) for j in (-1, 0, 1)
                   for a, b in buckets.get((int(x // 256) + i, int(y // 256) + j), ()))
    # the first paint off, along the first lines and over the town
    old_pts = set(town_pts)
    for pts in lines.values():
        for x, y in _dense(pts, 64.0):
            for gy in range(int((y - OLD_REACH) // 128), int((y + OLD_REACH) // 128) + 2):
                for gx in range(int((x - OLD_REACH) // 128), int((x + OLD_REACH) // 128) + 2):
                    if math.hypot(gx * 128.0 - x, gy * 128.0 - y) <= OLD_REACH:
                        old_pts.add((gx, gy))
    for gx, gy in old_pts:
        for f, _xy, r, cc in each(gx, gy):
            for q in range(4):
                rr, c2 = r - (q >> 1) * 16, cc - (q & 1) * 16
                if 0 <= rr <= 16 and 0 <= c2 <= 16:
                    for l in f['q'][q]['layers']:
                        if l.get('key') in old_keys and l['a'][rr * 17 + c2] > 0:
                            l['a'][rr * 17 + c2] = 0.0
                            rep['old taken off'] += 1
    for k in touched:
        for q in B.forms[k]['q']:
            q['layers'] = [l for l in q['layers'] if not (l.get('key') in old_keys and not any(l['a']))]

    def paint(gx, gy, which):
        key, tex = grounds[which]
        for f, _xy, r, cc in each(gx, gy):
            for q in range(4):
                rr, c2 = r - (q >> 1) * 16, cc - (q & 1) * 16
                if 0 <= rr <= 16 and 0 <= c2 <= 16:
                    rep['gave way'] += lay_paint(f['q'][q], rr * 17 + c2, key, tex, 1.0)
    # the town paved
    for gx, gy in town_pts:
        paint(gx, gy, 'paving')
        rep['paved points'] += 1
    # the paths beyond it: earth
    for name, pts in lines.items():
        for x, y in _dense(pts):
            for gy in range(int((y - EARTH_HALF) // 128), int((y + EARTH_HALF) // 128) + 2):
                for gx in range(int((x - EARTH_HALF) // 128), int((x + EARTH_HALF) // 128) + 2):
                    if math.hypot(gx * 128.0 - x, gy * 128.0 - y) <= EARTH_HALF and not in_box(box, gx * 128.0, gy * 128.0):
                        paint(gx, gy, 'earth')
                        rep['earth points'] += 1
    # the ground smoothed: open points relaxed toward their neighbours, held ones (under and by a piece) kept
    hv = {}
    for gx, gy in town_pts:
        f = list(each(gx, gy))
        if f:
            ff, _xy, r, cc = f[0]
            hv[(gx, gy)] = ff['h'][r * 33 + cc]
    held = {pt for pt in hv if any(_in_poly(pt[0] * 128.0, pt[1] * 128.0, poly) for poly in held_polys)}
    # (a piece whose foot stands over the ground has the ground under and by it raised to just under its foot: never
    # lowered, so every foot stays in the ground; the open ground then relaxes to meet it)
    raised = 0
    for (_c, _r, _e, p, sc, ob), poly in zip(pieces, held_polys):
        want = p[2] - FOOT_UNDER
        for pt in held:
            if hv[pt] < want - 1.0 and _in_poly(pt[0] * 128.0, pt[1] * 128.0, poly):
                hv[pt] = want
                raised += 1
    rep['raised to a foot'] = raised
    free = [pt for pt in hv if pt not in held]
    for _ in range(RELAX):
        new = {}
        for gx, gy in free:
            ns = [hv.get((gx + a, gy + b)) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            ns = [v for v in ns if v is not None]
            if ns:
                new[(gx, gy)] = (hv[(gx, gy)] + sum(ns)) / (1 + len(ns))
        hv.update(new)
    for (gx, gy) in list(free) + [pt for pt in held if raised]:
        z = round(hv[(gx, gy)] / 8.0) * 8.0
        for f, _xy, r, cc in each(gx, gy):
            if abs(f['h'][r * 33 + cc] - z) >= 1.0:
                f['h'][r * 33 + cc] = z
                rep['smoothed points'] += 1
    rep['held points'] = len(held)
    # no grass reaching the town or a path
    grows, plain0 = no_grass_rules(gd, pr)
    mine = {v[0] for v in grounds.values()}
    grows_any = lambda k: False if k in mine else grows(k)
    made_twins = {}

    def plain(key):
        """The ground's twin with no grass; a game ground with none (the farmland grass the Huáng's fields lie on) gets
        one of the mod's own, the same picture without its grass, rather than the grass being cleared bare."""
        got = plain0(key)
        if got is not None or key.startswith('+'):
            return got
        if key not in made_twins:
            import activity
            src = recordio.load(gd, gd.from_key(key))
            e = (recordio.field(src, 'EDID') or 'Ground') + 'NoGrass'
            have = next((k for k, r in pr.records.items() if r.get('type') == 'LTEX' and recordio.field(r, 'EDID') == e), None)
            if have is None:
                subs = [dict(q) for q in src['subs'] if q['tag'] in ('EDID', 'TNAM', 'HNAM', 'SNAM')]
                for q in subs:
                    if q['tag'] == 'EDID':
                        q['value'] = e
                have = activity._new_key(pr)
                g_ops.append({'op': 'record', 'key': have, 'record': {'type': 'LTEX', 'flags': 0, 'src': '', 'subs': subs}})
            made_twins[key] = have
        return made_twins[key]
    hits = {}
    feet = [(cx, cy, c, s, x0 - GRASS_OFF, y0 - GRASS_OFF, x1 + GRASS_OFF, y1 + GRASS_OFF)]
    for name, pts in lines.items():
        half = EARTH_HALF + GRASS_OFF
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            if L:
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                feet.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, ux, -uy, -L / 2 - half, -half, L / 2 + half, half))
    for foot in feet:
        for xy, got in plantgrass.points_under(foot).items():
            hits.setdefault(xy, set()).update(got)
    g_rep = {}
    for xy, h in hits.items():
        f = form(*xy)
        if f:
            plantgrass.clear_points(f, h, grows_any, plain, g_rep)
    rep['grass'] = g_rep
    # what grows or lies on the paving and the paths: out; what stands on moved ground: moved with it
    kerb = next((k for k, r in pr.records.items() if recordio.field(r, 'EDID') == 'FOLabHuangPathKerb'), None)
    gone = moved = 0
    moves = []
    for (cx2, cy2) in sorted(touched):
        cell = B.w.grid.get((cx2, cy2))
        ck = gd.key(cell) if cell is not None else None
        for rk, r in ((pr.cells.get(ck) or {}).get('refs', {}).items() if ck else ()):
            p = r.get('p')
            if not p or r.get('removed'):
                continue
            on = in_box(box, p[0], p[1]) or near_line(p[0], p[1], EARTH_HALF + 40.0)
            if on and (B.clearable(ck, rk) or (kerb and r.get('base') == kerb)):
                B.take_out([(ck, rk)])
                gone += 1
                continue
            g0, g1 = B.orig.at(p[0], p[1]), B.ground.at(p[0], p[1])
            if g0 is not None and g1 is not None and abs(g1 - g0) >= 2.0:
                if rk in piece_refs:
                    continue                                    # (the town's own pieces keep their places: their ground is held)
                np_ = list(p)
                np_[2] = round(p[2] + (g1 - g0), 1)
                moves.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': np_})
                moved += 1
    rep.update({'taken out': gone, 'moved with the ground': moved})
    lands = [{'op': 'land', 'cell': gd.key(B.w.grid[k]), 'land': B.forms[k]} for k in sorted(touched) if k in B.w.grid]
    cells = sorted({o['cell'] for o in lands} | {o['cell'] for o in B.ops if o.get('cell')} | {o['cell'] for o in moves})
    rep['land cells'] = len(lands)
    rep['box'] = [round(v, 3) for v in box]
    return g_ops + lands + B.ops + moves, rep, cells, box


def no_grass_rules(gd, pr):
    """plantgrass.ltex_rules, with the game's own way of naming a grassy ground too: '<edid>Grass' is the grassy twin of
    '<edid>' (LDirtPebblesCanyon01Grass, LScrubDirtCanyon01Grass): without it 259 grass points by the first paths had no
    twin to move to and were left bare."""
    import plantgrass
    grows, plain = plantgrass.ltex_rules(gd, pr)
    game = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'LTEX':
            game.setdefault((gd.edid(f) or '').lower(), gd.key(f))
    seen = {}

    def plain2(key):
        if key not in seen:
            got = plain(key)
            if got is None and not key.startswith('+'):
                try:
                    e = gd.edid(gd.from_key(key)) or ''
                except (KeyError, ValueError):
                    e = ''
                if e.lower().endswith('grass'):
                    k = game.get(e[:-5].lower())
                    if k and not grows(k):
                        got = k
            seen[key] = got
        return seen[key]
    return grows, plain2


# ---------- the courtyards furnished (the user, 22 Nov 2026: "make the courtyards done tastefully too, as if proud people
# live here") ----------
# Each courtyard is laid out in its hall's own frame (the hall faces -y, its yard, the screen 1100 out): the walk from the
# screen to the porch steps kept clear (|x| < WALK), a stone lantern either side of it, a planter with a small tree or a
# flowering shrub by each, a well beside the hall on one side and water jars on the other, a stone
# bench along a side wall; in the plain halls' yards (the Nongmin's: the red-roofed halls are the grander) a drying rack, a
# barrel and a bucket by the well; paper lanterns hung from the porch beam either side of the door, lit at night by the
# night lights' marker. A thing goes only where it clears every wall, hall and screen and what's already put.

WALK = 210.0
NUDGES = [(0, 0)] + [(round(r * math.cos(a * math.pi / 4)), round(r * math.sin(a * math.pi / 4))) for r in (60, 120, 180, 260) for a in range(8)]
# piece or game editor ID, x, y in the hall's frame (x across, -y out to the yard), turn (degrees, of the hall's), which yards
YARD = [
    ('settler_stone_lantern', -330, -820, 0, 'all'), ('settler_stone_lantern', 330, -820, 0, 'all'),
    ('settler_planter', -640, -810, 0, 'all'), ('settler_planter', 640, -810, 0, 'all'),
    ('settler_well', 790, -260, 90, 'all'),
    ('settler_water_jar', -760, -330, 0, 'all'), ('settler_water_jar', -790, -230, 0, 'all'),
    ('settler_bench', -820, -560, 90, 'all'),
    ('bamboo_drying_rack', 560, -1000, 0, 'work'), ('NVWoodBarrel', 760, -120, 0, 'work'), ('Bucket01', 700, -170, 0, 'work'),
]
IN_PLANTER = ('FOLabBeachHibiscus', 'FOLabJungleTreeFern', 'FOLabJungleTiRed', 'FOLabBeachHibiscus', 'FOLabJungleTiGreen', 'FOLabJungleTreeFern')
PLANTER_EARTH = 58.0
CLEAR_OF = 24.0                 # (a thing's footprint grown by this keeps off walls, halls, screens and what's put)
HALL_GROUND = {'FOLabSettlerHall': (-610, -680, 0, 610, 380, 0), 'FOLabSettlerHallRed': (-710, -710, 0, 710, 410, 0)}
LANTERN_HOOK = {'FOLabSettlerHall': (275.0, -500.0, 340.0), 'FOLabSettlerHallRed': (325.0, -530.0, 380.0)}


def courtyards(gd, pr, land, ctx=None):
    """(ops, report, cells, walks): each Huáng courtyard furnished (see above). walks: [(from, to)] screen to porch, to be
    walked on the navmesh once it is made again."""
    import modelsets
    import nightlights
    import roadgen
    modelsets._all_sets()                       # (the settler set's courtyard pieces register when it's imported)
    G = roadgen.Ground(gd, pr, land.world)
    pieces = town_pieces(gd, pr, land)
    halls = [pc for pc in pieces if pc[2].startswith('FOLabSettlerHall')]
    screens = [pc for pc in pieces if pc[2] == 'FOLabSettlerScreen']
    # (a hall by its ground: platform and steps, not its roof's overhang, which the OBND takes in)
    solid = [_footprint(p, sc, HALL_GROUND.get(e, ob), CLEAR_OF) for _c, _r, e, p, sc, ob in pieces]
    grid = gd.grid(land.world)
    cell_of = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))]) if (int(x // 4096), int(y // 4096)) in grid else None
    ops, rep, keys, boxes = [], {'put': {}, 'left out': {}}, {}, {}

    def base_of(name):
        if name in keys:
            return keys[name]
        if name in modelsets.PIECES:
            got, info = modelsets.put(pr, name)
            ops.extend(got)
            keys[name] = info['key'] or '$model_' + name
            b = info['box']
            boxes[name] = (b[0], b[1], b[3], b[4])
        else:
            f = next((f for f, (_i, r) in gd.forms.items() if r.tag in ('STAT', 'MSTT', 'FURN') and gd.edid(f) == name), None)
            if f is None:
                keys[name] = None
                return None
            keys[name] = gd.key(f)
            import struct
            o = gd.fields(f).get('OBND')
            b = struct.unpack_from('<6h', o) if o else (-30, -30, 0, 30, 30, 60)
            boxes[name] = (b[0], b[1], b[3], b[4])
        return keys[name]
    mine = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') in ('STAT', 'TREE')}
    walks, cells, n_plant = [], set(), 0
    put_feet = []
    for hk, (hc, hr, he, hp, hs, hob) in enumerate(halls):
        sc = min(screens, key=lambda s: math.hypot(s[3][0] - hp[0], s[3][1] - hp[1]))
        rz = hp[5] if len(hp) > 5 else 0.0
        c, sn = math.cos(rz), math.sin(rz)
        to_world = lambda lx, ly: (hp[0] + lx * c + ly * sn, hp[1] - lx * sn + ly * c)
        work = he == 'FOLabSettlerHall'
        for name, lx, ly, turn, which in YARD:
            if which == 'work' and not work:
                continue
            k = base_of(name)
            if k is None:
                rep['left out'][name] = rep['left out'].get(name, 0) + 1
                continue
            trz = (rz + math.radians(turn)) % math.tau
            b = boxes[name]
            found = None
            for dx, dy in NUDGES:                       # (its spot, then a little way round it, until it's clear)
                ax, ay = lx + dx, ly + dy
                if abs(ax) < WALK and ay < -560:
                    continue
                x, y = to_world(ax, ay)
                foot = _footprint([x, y, 0, 0, 0, trz], 1.0, (b[0], b[1], 0, b[2], b[3], 0), 0.0)
                if not any(_in_poly(q[0], q[1], poly) for q in foot + [(x, y)] for poly in solid + put_feet):
                    found = (x, y)
                    break
            if found is None:
                rep['left out'][name] = rep['left out'].get(name, 0) + 1
                continue
            x, y = found
            z = G.at(x, y)
            ck = cell_of(x, y)
            if z is None or ck is None:
                continue
            ops.append({'op': 'add', 'cell': ck, 'base': k, 's': 1.0, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(trz, 4)]})
            put_feet.append(_footprint([x, y, 0, 0, 0, trz], 1.0, (b[0], b[1], 0, b[2], b[3], 0), CLEAR_OF))
            cells.add(ck)
            rep['put'][name] = rep['put'].get(name, 0) + 1
            if name == 'settler_planter':
                pe = IN_PLANTER[n_plant % len(IN_PLANTER)]
                n_plant += 1
                if pe in mine:
                    ops.append({'op': 'add', 'cell': ck, 'base': mine[pe], 's': 0.7,
                                'p': [round(x, 1), round(y, 1), round(z + PLANTER_EARTH, 1), 0.0, 0.0, round((x * 0.01) % math.tau, 4)]})
                    rep['put']['plants in planters'] = rep['put'].get('plants in planters', 0) + 1
        sx, sy = sc[3][0], sc[3][1]
        porch = to_world(0, -720.0)                      # (at the foot of the porch steps)
        walks.append(((sx + (hp[0] - sx) * 0.25, sy + (hp[1] - sy) * 0.25), porch))
    # paper lanterns at the doors, lit at night (the night lights' marker and its day twins)
    marker = nightlights._marker_key(pr)
    hung = 0
    if marker:
        L = nightlights.Lighter(gd, pr, land.world, None, marker)
        for hc, hr, he, hp, hs, hob in halls:
            hook = LANTERN_HOOK.get(he)
            if not hook:
                continue
            rz = hp[5] if len(hp) > 5 else 0.0
            c, sn = math.cos(rz), math.sin(rz)
            for sx_ in (-1, 1):
                lx, ly, lz = hook[0] * sx_, hook[1], hook[2]
                x, y = hp[0] + lx * c + ly * sn, hp[1] - lx * sn + ly * c
                if L.put('night_paper_lantern_red', x, y, hp[2] + lz, rz, foot=False):
                    hung += 1
        ops = L.first + ops + L.ops
        cells |= {o['cell'] for o in L.ops if o.get('cell')}
    rep['lanterns hung'] = hung
    rep['courtyards'] = len(halls)
    return ops, rep, sorted(cells), walks
