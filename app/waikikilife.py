"""Waikiki made livelier and the way there playable (the user, 21 Nov 2026: "interactable people in the world with dialogue,
storekeepers... people around the hotels and beaches. The hostile elements shouldn't be seen till farther down... more things
to find along the way, places to rest, bedrolls... the world lacks medicine and ammo").

Four parts, each its own ops (one Undo for all through `build`):
- `clear`: the road from the Castaway's start to Waikiki is found through the road pieces (`way`). Inside Waikiki (round the
  hotels, `WAIKIKI_R`) nothing hostile is left; along the road (`BAND`) the dangerous kinds (`STRONG`) go everywhere, and the
  small ones (`LIGHT`: geckos, mole rats, rats, bloatflies) go too for the first `QUIET` of the way. A dangerous one of the
  mod's own past the quiet stretch becomes a small one in its place, so the road still has something to meet.
- `people`: Waikiki's locals (two kinds, copies of the mod's surfers, so in the hibiscus prints) standing round the Royal
  Hawaiian, the Moana and the Kilauea, wandering where they stand (the game's sandbox package); and four storekeepers by the
  Royal Hawaiian (a doctor, a gunsmith, a grocer, a trader), each with a merchant chest of the game's (copied, buried under
  them as the game buries its own) and the game's services for what they buy.
- `talk`: a quest of its own (start game enabled, no script) holding their lines: a greeting each (in the game's GREETING
  topic), two top-level topics ("What is this place?", "Who's in charge here?") and the storekeepers' "Let's trade.", whose
  line opens the barter window with the result script `ShowBarterMenu` (the game's own bytes: the compiler gives them).
  All silent; nothing new about the story: Waikiki is the Kahuna's, the safest place, the valleys pay his tribute.
- `camps`: places to rest along the road every `CAMP_EVERY`: a bedroll by a campfire, with one of the game's first aid kits
  and ammo boxes (levelled contents), a little off the road on its flatter side.

The barter window rests on a line's result script, which hasn't yet been seen to run in either game (the opening's did not,
19 Nov 2026): the first thing to try. Trading is in caps, the game's barter; the user hasn't said what Waikiki's money is."""
import collections
import heapq
import json
import math

import api_quests as aq
import questrec as qr
import recordio
from castawayquest import _game_form, _ref_by_edid

START_REF = 'FOLabHanaumaWake'                      # (castaway.py: where you wake)
HOTELS = ('royal_hawaiian', 'moana', 'kilauea')     # (landmarks.json sets, Waikiki's middle)
WAIKIKI_R = 14000.0
BAND = 3000.0
QUIET = 0.3                                         # (share of the way, from the start, with nothing hostile at all)
CAMP_EVERY, CAMP_FIRST, CAMP_OFF = 16000.0, 7000.0, 450.0

STRONG = ('Pirate', 'Fiend', 'Raider', 'Viper', 'Jackal', 'Ghoul', 'Glowing', 'Cazador', 'NightStalker', 'Nightstalker', 'Mantis',
          'SporeCarrier', 'SporePlant', 'Deathclaw', 'Radscorpion', 'Lakelurk', 'Dog', 'FireGecko', 'Mutant', 'Centaur')
LIGHT = ('Gecko', 'MoleRat', 'GiantRat', 'Bloatfly')
SMALL = ('LvlGecko', 'LvlWastelandMoleRat', 'LvlGiantRat', 'LvlWastelandBloatfly')    # (what a dangerous one becomes)

SURFER = 'FOLabSurferVSpawnProspectorAll'           # (peopledress: the mod's surfers, hibiscus prints)
SANDBOX, STAY = 'DefaultSandboxEditorLocation512', 'DefaultStayAtEditorLocation'
LOCALS = [('FOLabWaikikiLocal', 'Waikiki Local'), ('FOLabWaikikiLocal2', 'Waikiki Local')]
LOCALS_EACH = 7                                     # (round each hotel)
# storekeepers: (editor ID, name, the game's merchant chest to copy, greeting)
SHOPS = [('FOLabWaikikiDoctor', 'Doctor', 'VendorContainerDocMitchell',
          "Hurt? I've got stimpaks and bandages, if you've got something to trade."),
         ('FOLabWaikikiGunsmith', 'Gunsmith', 'VendorContainerGunRunnerHQ',
          "Guns and ammunition. Keep them pointed at the jungle, not at the Kahuna's men."),
         ('FOLabWaikikiGrocer', 'Grocer', 'VendorContainerWhiteGloveFood',
          "Fruit, fish, clean water. Better than what you'll find on the road."),
         ('FOLabWaikikiTrader', 'Trader', 'VendorContainerChet',
          "A bit of everything that washes up or comes down the road. Have a look.")]
SERVICES_FROM = 'GSChet'                            # (what the storekeepers buy: as the Goodsprings general store)
SERVICES_ALL = 0x47F
BARTER_GOLD = 600

QUEST, QUEST_NAME = 'FOLabWaikikiPeople', 'Waikiki People'
TOPICS = {'where': ('FOLabWaikikiWhere', 'What is this place?'), 'who': ('FOLabWaikikiWho', "Who's in charge here?"),
          'trade': ('FOLabWaikikiTrade', "Let's trade.")}
WORDS = {
    'local_hello': ["Welcome to Waikiki. Keep your weapon down and nobody troubles you.",
                    "Safest place on the island, Waikiki. As long as the Kahuna says so."],
    'where': "Waikiki. The Kahuna holds court in the Royal Hawaiian. Keep the peace and nobody bothers you here.",
    'who': "The Kahuna. His men collect the tribute, and the valleys pay it. Here in Waikiki we're the lucky ones.",
    'trade': "Have a look.",
}
CAMP = [('bedroll', 'NVBedrollL', 'FURN', (0, 0)), ('fire', 'CampfireCrafting03', None, (0, 170)),
        ('aid', 'LootFirstAidKitNV', 'CONT', (-130, 60)), ('ammo', 'LootAmmoBoxGenericNV', 'CONT', (130, 60))]


# ---------- the road from the start to Waikiki ----------

def _edid(gd, pr, base):
    if base.startswith('+'):
        return recordio.field(pr.records.get(base) or {'subs': []}, 'EDID') or ''
    return gd.edid(gd.from_key(base)) or ''


def _tag(gd, pr, base):
    if base.startswith('+'):
        return (pr.records.get(base) or {}).get('type', '')
    f = gd.from_key(base)
    return gd.forms[f][1].tag if f in gd.forms else ''


def middle(pr):
    """Waikiki's middle: the mean of the hotels the landmarks step stood ({set: (x, y)}, (x, y))."""
    import os
    import project
    path = os.path.join(project.PROJECTS_DIR, pr.name + ' maps', 'landmarks.json')
    stood = {}
    with open(path, encoding='utf-8') as f:
        for world in json.load(f).values():
            for s in world.get('stood', ()):
                stood[s['set']] = (float(s['x']), float(s['y']))
    hot = {k: stood[k] for k in HOTELS if k in stood}
    if not hot:
        raise ValueError('no hotels in %s' % path)
    return hot, (sum(p[0] for p in hot.values()) / len(hot), sum(p[1] for p in hot.values()) / len(hot))


def way(gd, pr, start, end):
    """The road pieces from near `start` to near `end`, in order: a shortest walk over pieces that touch (gaps cost more)."""
    pts = []
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            p = r.get('p')
            if p and not r.get('removed') and 'Road' in _edid(gd, pr, r['base']) and _tag(gd, pr, r['base']) == 'STAT':
                pts.append((p[0], p[1]))
    if not pts:
        raise ValueError('no road pieces')
    grid = collections.defaultdict(list)
    for n, (x, y) in enumerate(pts):
        grid[(int(x // 2000), int(y // 2000))].append(n)
    near = lambda q: min(range(len(pts)), key=lambda n: (pts[n][0] - q[0]) ** 2 + (pts[n][1] - q[1]) ** 2)
    a, b = near(start), near(end)
    dist, prev, todo = {a: 0.0}, {}, [(0.0, a)]
    while todo:
        d, n = heapq.heappop(todo)
        if n == b:
            break
        if d > dist.get(n, 1e18):
            continue
        x, y = pts[n]
        gx, gy = int(x // 2000), int(y // 2000)
        for ix in range(gx - 2, gx + 3):
            for iy in range(gy - 2, gy + 3):
                for m in grid.get((ix, iy), ()):
                    s = math.hypot(pts[m][0] - x, pts[m][1] - y)
                    if s > 4000 or m == n:
                        continue
                    nd = d + (s if s < 1400 else s * 4)
                    if nd < dist.get(m, 1e18):
                        dist[m], prev[m] = nd, n
                        heapq.heappush(todo, (nd, m))
    if b not in dist:
        raise ValueError('no road from the start to Waikiki')
    out, n = [b], b
    while n != a:
        n = prev[n]
        out.append(n)
    return [pts[n] for n in reversed(out)]


class Way:
    """The road as a line: how far along it a spot is (share 0..1) and how far off it."""

    def __init__(self, pts):
        self.pts = pts
        self.at = [0.0]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.at.append(self.at[-1] + math.hypot(x1 - x0, y1 - y0))
        self.long = self.at[-1] or 1.0
        self.grid = collections.defaultdict(list)
        for n, (x, y) in enumerate(pts):
            self.grid[(int(x // 4000), int(y // 4000))].append(n)

    def near(self, x, y, reach):
        """(distance off the road, share along it) for the nearest piece within reach, or None."""
        best = None
        gx, gy = int(x // 4000), int(y // 4000)
        k = int(reach // 4000) + 1
        for ix in range(gx - k, gx + k + 1):
            for iy in range(gy - k, gy + k + 1):
                for n in self.grid.get((ix, iy), ()):
                    d = math.hypot(self.pts[n][0] - x, self.pts[n][1] - y)
                    if d <= reach and (best is None or d < best[0]):
                        best = (d, self.at[n] / self.long)
        return best


# ---------- hostiles ----------

def kind(edid):
    """'strong', 'light' or None (not hostile) by the base's editor ID."""
    if edid.startswith('FOLabSurfer') or edid.startswith('FOLabKuli') or edid.startswith('FOLabWaikiki') or edid == 'FOLabBeachcomber':
        return None
    if any(w in edid for w in STRONG):
        return 'strong'
    if any(w in edid for w in LIGHT):
        return 'light'
    return None


def clear(gd, pr, road, mid):
    """(ops, report): hostiles out of Waikiki and off the road, as the notes say."""
    small = [gd.key(_game_form(gd, e, 'CREA')) for e in SMALL]
    ops, rep, swapped = [], collections.Counter(), 0
    for ck, c in pr.cells.items():
        for rk, r in list(c.get('refs', {}).items()):
            p = r.get('p')
            if not p or r.get('removed') or _tag(gd, pr, r['base']) not in ('NPC_', 'CREA', 'LVLN', 'LVLC'):
                continue
            k = kind(_edid(gd, pr, r['base']))
            if not k:
                continue
            if math.hypot(p[0] - mid[0], p[1] - mid[1]) < WAIKIKI_R:
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                rep['waikiki_' + k] += 1
                continue
            on = road.near(p[0], p[1], BAND)
            if not on:
                continue
            if k == 'light' and on[1] >= QUIET:
                continue
            ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
            rep['road_' + k] += 1
            if k == 'strong' and on[1] >= QUIET and rk.startswith('+'):
                ops.append({'op': 'add', 'cell': ck, 'base': small[swapped % len(small)], 'p': list(p), 's': 1.0})
                swapped += 1
    rep['small_in_their_place'] = swapped
    return ops, dict(rep)


# ---------- spots ----------

class Spots:
    """Open standing ground: dry, not in a building's footprint (indoors), not under a roof or inside anything, not too near
    another spot taken."""

    def __init__(self, gd, pr, world):
        import lootplace
        import roadgen
        self.S = lootplace.Seat(gd, pr, world)
        self.G = roadgen.Ground(gd, pr, world)
        self.taken = []
        self._args, self._B = (gd, pr, world), None

    @property
    def B(self):
        """The closed buildings round (indoors): nobody stands inside one, whatever its collision says."""
        if self._B is None:
            import indoors
            self._B = indoors.Buildings(*self._args)
        return self._B

    def stand(self, x, y, box=(-30, -30, 0, 30, 30, 120), apart=220.0):
        g = self.G.at(x, y)
        if g is None or g < 8:
            return None
        if self.B.inside(x, y, g):
            return None
        if any(math.hypot(x - a, y - b) < apart for a, b in self.taken):
            return None
        self.S.load(x, y)
        for dx, dy in ((0, 0), (40, 0), (-40, 0), (0, 40), (0, -40)):
            tops = [z for z, _r in self.S.solids.tops(x + dx, y + dy)]
            if any(g + 60 < z < g + 900 for z in tops):         # (a roof, a wall top, anything over head)
                return None
            here = [z for z in tops if abs(z - g) < 60]
            if any(z > g + 30 for z in here):                   # (on a step or a crate: not for standing)
                return None
        flat = [self.G.at(x + dx, y + dy) for dx, dy in ((80, 0), (-80, 0), (0, 80), (0, -80))]
        if None in flat or max(flat) - min(flat) > 60:
            return None
        self.taken.append((x, y))
        return g


def ring(spots, x, y, want, radii=(900, 1200, 1500, 1800, 2200), turns=16):
    out = []
    for r in radii:
        for t in range(turns):
            a = (t + (r // 300) * 0.37) * 2 * math.pi / turns
            px, py = x + r * math.sin(a), y + r * math.cos(a)
            z = spots.stand(px, py)
            if z is not None:
                out.append((px, py, z, math.atan2(x - px, y - py)))
                if len(out) >= want:
                    return out
    return out


# ---------- people ----------

def _person(gd, pr, src, edid, name, package):
    import api_characters as ac
    npc = json.loads(json.dumps(src))
    recordio.set_field(npc, 'EDID', edid, label='Editor ID')
    full = ac.one(npc, 'FULL')
    if full:
        full['value'] = name
    else:
        ac.insert(npc, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    npc['subs'] = [s for s in npc['subs'] if s['tag'] not in ('SCRI', 'PKID')]
    ac.insert(npc, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(ac._find(gd, 'PACK', package))})
    # (their own AI data and packages, not the template's: 0x10 AI data, 0x20 AI packages, 0x200 script)
    ac.set_num(npc, 'ACBS', 'Template flags', ac.num(npc, 'ACBS', 'Template flags') & ~(0x10 | 0x20 | 0x200))
    npc['src'] = ''
    return npc


def _base_person(gd, pr):
    """The record locals and storekeepers are copied from: the mod's surfer, else the game's prospector."""
    import api_characters as ac
    k = next((k for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'EDID') == SURFER), None)
    if k is None:
        k = gd.key(_game_form(gd, 'NVProspectorMale', 'NPC_'))
    return ac.get_record(gd, pr, k), k


def _services(gd):
    import api_characters as ac
    try:
        f = _game_form(gd, SERVICES_FROM, 'NPC_')
        rec = recordio.load(gd, f)
        return int(ac.num(rec, 'AIDT', 'Services')) or SERVICES_ALL
    except (ValueError, KeyError, TypeError):
        return SERVICES_ALL


def _any_form(gd, edid):
    for f, (_i, r) in gd.forms.items():
        if (f >> 24) == 0 and gd.edid(f) == edid:
            return f
    raise ValueError('the game has no %s' % edid)


# ---------- all of it ----------

def plan(gd, pr):
    """Where everything goes: {'road', 'mid', 'hotels', 'world', 'locals': [(x, y, z, rz)], 'shops': [...], 'camps': [...]}."""
    ck, rk = _ref_by_edid(pr, START_REF)
    if not rk:
        raise ValueError('no start (%s)' % START_REF)
    start = pr.cells[ck]['refs'][rk]['p']
    world = gd.ext_cells[gd.from_key(ck)]
    hot, mid = middle(pr)
    road = Way(way(gd, pr, start[:2], hot.get('royal_hawaiian', mid)))
    sp = Spots(gd, pr, world)
    rh = hot.get('royal_hawaiian', mid)
    shops = ring(sp, rh[0], rh[1], len(SHOPS), radii=(1000, 1300, 1600), turns=24)
    locals_ = []
    for k in HOTELS:
        if k in hot:
            locals_ += ring(sp, hot[k][0], hot[k][1], LOCALS_EACH)
    camps, along = [], CAMP_FIRST
    while along < road.long:
        n = next(i for i, a in enumerate(road.at) if a >= along)
        (x0, y0), (x1, y1) = road.pts[max(0, n - 1)], road.pts[min(len(road.pts) - 1, n + 1)]
        d = math.hypot(x1 - x0, y1 - y0) or 1.0
        px, py = -(y1 - y0) / d, (x1 - x0) / d
        x, y = road.pts[n]
        if math.hypot(x - mid[0], y - mid[1]) > WAIKIKI_R:
            for side in (1, -1, 1.6, -1.6, 2.2, -2.2):
                cx, cy = x + px * CAMP_OFF * side, y + py * CAMP_OFF * side
                if sp.stand(cx, cy, apart=600) is not None and all(sp.stand(cx + ox, cy + oy, apart=0) is not None for ox, oy in ((0, 170), (-130, 60), (130, 60))):
                    sp.taken = [t for t in sp.taken if math.hypot(t[0] - cx, t[1] - cy) > 300] + [(cx, cy)]
                    camps.append((cx, cy, math.atan2(x - cx, y - cy)))
                    break
        along += CAMP_EVERY
    return {'road': road, 'mid': mid, 'hotels': hot, 'world': world, 'locals': locals_, 'shops': shops, 'camps': camps, 'sp': sp}


def ops(gd, pr, P):
    """(ops, report) for everything: the hostiles cleared, the people and their talk, the camps."""
    import api_scripts
    import scriptc
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        raise ValueError('the mod already has %s' % QUEST)
    grid = gd.grid(P['world'])
    cell = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    out, rep = [], {}
    cleared, rep['cleared'] = clear(gd, pr, P['road'], P['mid'])
    # (every record_new and add takes the next key in order: records first, then things, the clearing last)
    key_at = lambda: '+%06X' % (pr.next_id + sum(1 for x in out if x['op'] in ('record_new', 'add')))
    # the records: people, chests, quest, topics (keys in this order)
    order = [e for e, _n in LOCALS] + [s[0] for s in SHOPS] + ['chest_' + s[0] for s in SHOPS] + ['quest'] + list(TOPICS)
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    src, src_key = _base_person(gd, pr)
    services = _services(gd)
    import api_characters as ac
    for e, n in LOCALS:
        out.append({'op': 'record_new', 'record': _person(gd, pr, src, e, n, SANDBOX)})
    for e, n, _c, _w in SHOPS:
        npc = _person(gd, pr, src, e, n, STAY)
        ac.set_num(npc, 'AIDT', 'Services', services)
        ac.set_num(npc, 'ACBS', 'Barter gold', BARTER_GOLD)
        out.append({'op': 'record_new', 'record': npc})
    for e, n, chest, _w in SHOPS:
        rec = recordio.load(gd, _game_form(gd, chest, 'CONT'))
        recordio.set_field(rec, 'EDID', 'FOLab' + e[5:] + 'Chest', label='Editor ID')
        rec['src'] = ''
        out.append({'op': 'record_new', 'record': rec})
    quest = qr.quest_record({'edid': QUEST, 'script': '', 'name': '', 'flags': {'start_enabled': True}, 'priority': 40, 'delay': None,
                             'stages': [], 'objectives': []})
    out.append({'op': 'record_new', 'record': quest})
    for k, (edid, prompt) in TOPICS.items():
        out.append({'op': 'record_new', 'record': qr.topic_record({'edid': edid, 'name': prompt, 'priority': 50.0, 'kind': 0,
                                                                     'flags': {'top_level': True},
                                                                     'quests': [{'quest': keys['quest'], 'links': []}]})})
    # placed: locals round the hotels (the two kinds in turn), storekeepers by the Royal Hawaiian with their chests buried
    for n, (x, y, z, rz) in enumerate(P['locals']):
        out.append({'op': 'add', 'cell': cell(x, y), 'base': keys[LOCALS[n % 2][0]], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz, 4)], 's': 1.0})
    chest_refs = []
    for n, (e, _n, _c, _w) in enumerate(SHOPS):
        if n >= len(P['shops']):
            break
        x, y, z, rz = P['shops'][n]
        chest = key_at()
        out.append({'op': 'add', 'cell': cell(x, y), 'base': keys['chest_' + e], 'p': [round(x, 1), round(y, 1), round(z - 400, 1), 0.0, 0.0, 0.0], 's': 1.0,
                    'extra': {'persistent': True}})
        out.append({'op': 'add', 'cell': cell(x, y), 'base': keys[e], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz, 4)], 's': 1.0,
                    'extra': {'persistent': True, 'merchant': chest}})
        chest_refs.append(e)
    # the talk
    greeting = gd.key(_game_form(gd, 'GREETING', 'DIAL'))
    lines = []
    line = lambda topic, who, words, bye=False, script=None: lines.append(dict(aq.new_line_plain(gd, pr, topic, keys['quest'], who, words, goodbye=bye),
                                                                             begin=script, end=None))
    for n, (e, _n) in enumerate(LOCALS):
        line(greeting, keys[e], WORDS['local_hello'][n % len(WORDS['local_hello'])])
    for e, _n, _c, words in SHOPS:
        line(greeting, keys[e], words)
    barter = {'source': 'ShowBarterMenu', 'parts': aq.compile_parts('ShowBarterMenu', scriptc.GameForms(gd))}
    for e in [e for e, _n in LOCALS] + [s[0] for s in SHOPS]:
        line(keys['where'], keys[e], WORDS['where'])
        line(keys['who'], keys[e], WORDS['who'])
    for e in chest_refs:
        line(keys['trade'], keys[e], WORDS['trade'], bye=True, script=barter)
    lines_ops = [{'op': 'record_new', 'record': qr.info_record(l)} for l in lines]
    # the camps along the road
    sp = P['sp']
    bases = {name: gd.key(_game_form(gd, edid, tag) if tag else _any_form(gd, edid)) for name, edid, tag, _o in CAMP}
    for cx, cy, rz in P['camps']:
        for name, _e, _t, (ox, oy) in CAMP:
            x = cx + ox * math.cos(rz) + oy * math.sin(rz)
            y = cy - ox * math.sin(rz) + oy * math.cos(rz)
            z = sp.G.at(x, y)
            turn = rz + (math.pi if name == 'bedroll' else 0.0)
            out.append({'op': 'add', 'cell': cell(x, y), 'base': bases[name], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(turn, 4)], 's': 1.0})
    out += lines_ops + cleared
    rep.update({'keys': keys, 'locals': len(P['locals']), 'shops': len(chest_refs), 'camps': len(P['camps']), 'lines': len(lines),
                'road_long': round(P['road'].long), 'road_pieces': len(P['road'].pts), 'copied_from': src_key})
    return out, rep


def build(server):
    gd, pr = server.GD, server.PR
    P = plan(gd, pr)
    o, rep = ops(gd, pr, P)
    server.edit('Waikiki made livelier: people, storekeepers, a safer road, camps', o)
    return rep
