"""Richer generated places: tall rooms with balconies, stairs of every kind, ways round, shaped rooms, rooms made in one piece, other
kits, one room changed by itself, a drawn plan, and furnishing judged by the room. Everything walked on the real collision shapes
and read from the files. Nothing goes near the game."""
import collections
import math
import os
import random
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import kitdress as D
import kitindex as K
import kitplan as P
import navgen


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


B = chr(92)
VAULT, RUINED, OFFICE, UTILITY = ('dungeons' + B + n for n in ('vault', 'vaultruined', 'office', 'utility'))
G = gamedata.GameData()
kits = K.build(G)
sv = D.survey(G, kits, only={VAULT, RUINED, OFFICE, UTILITY})
store = {}
vt = P.tiles_for(G, kits, VAULT, store, sv)


def clean(w):
    return not w['missing'] and not w['escaped'] and not w['edges']


# ---------- tall rooms ----------
g0 = vt.galleys[0] if vt.galleys else None
check('the vault kit has tall rooms, read from its sections', vt.can['tall'] and g0 and g0.back == 'room')
check('… a railing has its floor part way up, on one side', g0 and any(p.edid == 'VGalleyRailing01' for p, _b in g0.rail))
check('… a railing with a bridge is told from one without', g0 and any(p.edid == 'VGalleyRailingBridge01' for p, _b in g0.bridge))
check('… both ends of the wall, left and right', g0 and {'VGalleyEndL01', 'VGalleyEndR01'} <= {p.edid for p, _c, _b in g0.end})
rt = P.tiles_for(G, kits, RUINED, store, sv)
check('the ruined vault has its own, and corridors too (it had none: a doorway\'s lintel read as its floor)', rt.can['tall'] and rt.can['halls'] and rt.can['stairs'])


def small_atrium(ts, seed, H=3):
    g = ts.galleys[0]
    pl = P.Planner(ts, random.Random(seed))
    pl.first_room(P.Spec('entrance', (4, 4), (4, 4), True, fam=g.back))
    pl.attach(P.Spec('atrium', (6, 6), (H, H), True, fam=g.back, tall=g), 0, True)
    return pl.plan


walked = 0
upper = 0
for seed in range(1, 5):
    plan = small_atrium(vt, seed)
    made = P.fill(vt, plan, seed, big=False)
    if made and any(o.get('tall') for o in plan.owners):
        w = P.walk_check(G, vt, plan, made, vt._walk_cache)
        tall = next(o for o in plan.owners if o.get('tall'))
        lv = min(c[2] for c in tall['cells'])
        balc = [c for c in tall['cells'] if c[2] == lv + 1 and c not in plan.air]
        walked += clean(w)
        upper += bool(balc) and not set(balc) & set(w['missing'])
check('a tall room: built, every floor reached, nothing open on the void (%d of 4)' % walked, walked >= 3)
check('… you can get onto its balconies by the stairs (%d of 4)' % upper, upper >= 3)
plan = small_atrium(vt, 1)
made = P.fill(vt, plan, 1, big=False)
without = [m for m in made if plan.owners[m.owner]['purpose'] != 'under a balcony']
w = P.walk_check(G, vt, plan, without, vt._walk_cache)
check('the walk knows: take away what stands under the balcony and it\'s open on the void (%d edges)' % len(w['edges']), len(w['edges']) > 20)
plan = small_atrium(vt, 2, 2)
made = P.fill(vt, plan, 2, big=False)
if made:
    bridges = [m for m in made if m.key in {p.key for p, _b in vt.galleys[0].bridge}]
    w = P.walk_check(G, vt, plan, made, vt._walk_cache)
    check('with two rows of squares a bridge joins the balconies, and one stair is enough', len(bridges) == 2 and len(plan.flights) == 1 and clean(w), '%d bridges, %d flights' % (len(bridges), len(plan.flights)))
else:
    check('with two rows of squares a bridge joins the balconies', False)
big = [p for p, _w, _h in vt.big]
check('bigger pieces going in over ordinary squares aren\'t tall ones', not any(p.box[5] - p.box[2] >= 400 for p in big))


ot0 = P.tiles_for(G, kits, OFFICE, store, sv)
pit = next((g for g in ot0.galleys if isinstance(g, P.Pit)), None)
check('the office kit has tall rooms of its own kind: a hall sunk two storeys, a room over it behind a railing', pit is not None and pit.rails)
good = 0
for seed in range(1, 8):
    pl = P.Planner(ot0, random.Random(seed))
    pl.first_room(P.Spec('entrance', (4, 4), (4, 4), True, fam=pit.back))
    pl.attach(P.Spec('hall', (6, 6), (4, 4), True, fam=pit.back, tall=pit), 0, True)
    tall = next((o for o in pl.plan.owners if o.get('tall')), None)
    made = P.fill(ot0, pl.plan, seed, budget=120, big=False) if tall else None
    if made:
        w = P.walk_check(G, ot0, pl.plan, made, ot0._walk_cache)
        up = [c for o in pl.plan.rooms() if o['purpose'] == 'over the hall' for c in o['cells']]
        good += clean(w) and bool(up) and not set(up) & set(w['missing'])
check('… built and walked, on both floors, sealed (%d)' % good, good >= 2)


# ---------- stairs ----------
check('the vault proves a straight flight, a long one and one that doubles back', {'straight', 'long', 'back'} <= set(vt.stair_kinds), str(vt.stair_kinds))
ot = P.tiles_for(G, kits, OFFICE, store, sv)
check('the office kit also proves its stairwell in one piece', 'turn' in ot.stair_kinds and ot.turns, str(ot.stair_kinds))
for ts, kinds in ((vt, ('straight', 'long', 'back')), (ot, ('straight', 'long', 'back', 'turn'))):
    for kind in kinds:
        good = 0
        for up in (True, False):
            rooms = sorted(ts.hall_pairs)
            good += any(ts._stairs_walk(kind, r, f, up) for r, f in rooms)
        check('%s: %s stairs walk (%d of 2 ways)' % (ts.kit.name, kind, good), good >= 1)
pl = P.Planner(vt, random.Random(1))
pl.plan.add_room('x', 'room', [(i, j, 0) for i in range(4) for j in range(3)])
two = pl.stair_moves((1, 2, 0), 1, 'long', True)
check('… a long flight rises two storeys', two and two[1][2] == 2)
two = pl.stair_moves((1, 2, 0), 1, 'back', True)
check('… and one that doubles back ends up going back the way it came', two and two[1][2] == 2 and two[2] == 3)


# ---------- plans that aren't trees ----------
def ways_round(plan):
    near = set()
    live = {o['n'] for o in plan.owners if o['purpose'] != 'outside'}
    for link in plan.links:
        a, b = tuple(link)
        x, y = plan.cells.get(a), plan.cells.get(b)
        if x != y and x in live and y in live:
            near.add(frozenset((x, y)))
    for c, d in plan.opens:
        x, y = plan.cells.get(c), plan.cells.get((c[0] + K.DX[d][0], c[1] + K.DX[d][1], c[2]))
        if x != y and x in live and y in live:
            near.add(frozenset((x, y)))
    return len(near) - len(live) + 1


loops = []
shaped = set()
for seed in range(6):
    g = P.generate(G, vt, 180, seed * 7 + 1)
    if not g:
        check('a plan (seed %d)' % seed, False)
        continue
    loops.append(g['plan'].loops)
    w = P.walk_check(G, vt, g['plan'], g['made'])
    check('seed %d: made, walks, sealed, %d way(s) round' % (seed, g['plan'].loops), clean(w))
    for o in g['plan'].rooms():
        cs = [c for c in o['cells'] if c not in g['plan'].air]
        if not o.get('tall') and not o.get('whole') and len({c[2] for c in cs}) == 1:
            x0, x1, y0, y1 = min(c[0] for c in cs), max(c[0] for c in cs), min(c[1] for c in cs), max(c[1] for c in cs)
            if (x1 - x0 + 1) * (y1 - y0 + 1) != len(cs):
                shaped.add(o['n'])
    shaped_any = bool(shaped)
check('plans have more than one way round (%s)' % loops, sum(loops) >= 4 and sum(1 for n in loops if n) >= 4)
check('rooms aren\'t all rectangles', shaped_any)
cells = P._shape(P.Spec('x', (6, 6), (6, 6), shape='cross'), 6, 6, random.Random(1), True)
check('a cross-shaped room has its corners out', (0, 0) not in cells and (3, 3) in cells and (0, 3) in cells or (3, 0) in cells)
cells = P._shape(P.Spec('x', (6, 6), (5, 5), shape='U'), 6, 5, random.Random(1), True)
check('a U-shaped room has its middle out of one side', (3, 4) not in cells and (0, 4) in cells and (5, 4) in cells)
g = P.generate(G, vt, 180, 9, survey=sv)
plan = g['plan']
first = plan.exit
main = [o for o in plan.rooms() if o.get('main') and o['purpose'] != 'entrance']
check('the way in: a small room first, then something much bigger', len(plan.owners[0]['cells']) <= 16 and main and max(len(o['cells']) for o in main) > len(plan.owners[0]['cells']))


# ---------- rooms made in one piece ----------
sp = next((s for s in vt.set_pieces if 'overseer' in s.piece.edid.lower()), None)
check('the overseer\'s office, joined as the game joined it', sp is not None and kits[VAULT].pieces[sp.join_key].edid == 'VHallSmEndExSm01', '')
check('… its other way out gets a dead end', sp is not None and len(sp.plugs) == 1)
good = 0
for seed in range(4):
    pl = P.Planner(vt, random.Random(seed))
    pl.first_room(P.Spec('entrance', (5, 5), (5, 5), True, fam='room'))
    pl.attach(P.Spec('office', (4, 5), (3, 4), fam='room', whole='overseer'), 0, True)
    made = P.fill(vt, pl.plan, seed, big=False) if any(o.get('whole') for o in pl.plan.owners) else None
    if made:
        good += clean(P.walk_check(G, vt, pl.plan, made, vt._walk_cache))
check('… walks, sealed, its floors reached, off the grid by what the game had it (%d of 4)' % good, good >= 3)
vault = P.vault_place(G, kits, 5, 3, store, {}, sv)
check('a vault: a tall atrium, with the real office if it fits', vault and any(o.get('tall') for o in vault['plan'].rooms()) and {'entrance', 'atrium', 'reactor', 'quarters', 'office'} <= {o['purpose'] for o in vault['plan'].rooms()})


# ---------- other kits ----------
ut = P.tiles_for(G, kits, UTILITY, store, sv)
check('the service tunnels can plan rooms and corridors now (they read as too narrow)', ut.can['rooms'] and ut.can['halls'] and ut.step == 256)
for what in ('tunnels', 'office'):
    made = sum(1 for seed in (1, 2, 3) if P.one_click_place(G, kits, what, 4, seed, store, {}, sv))
    check('in one click, %s: walks (%d of 3)' % (what, made), made == 3)
got = P.one_click(G, kits, 'tunnels', 3, 5, [64, 128, 0], store, {}, sv)
check('… as changes for the mod and words for the person', got.get('ops') and 'Service tunnels' in got.get('said', ''))
check('… listed by name for what\'s installed', {'tunnels', 'office', 'facility'} == {k['id'] for k in P.one_click_list(kits)})
g = P.one_click_place(G, kits, 'tunnels', 4, 11, store, {}, sv)
w = P.walk_check(G, ut, g['plan'], g['made'], {}, D.item_refs(G, g['items']))
check('… tunnels still walk with their things in', g and not w['missing'] and not w['escaped'])


# ---------- one room at a time ----------
got = P.vault(G, kits, 3, 21, [0, 0, 0], store, {}, sv)
last = store['last']
rooms = got['plan']['rooms']
check('the Kit tab gets the plan\'s rooms', got.get('plan') and rooms and all({'n', 'purpose', 'cells', 'theme'} <= set(r) for r in rooms))
room = next(r for r in rooms if r['purpose'] == 'quarters')
before = {(m.key, m.x, m.y, m.z, m.turn) for m in last['made'] if m.owner != room['n']}
back = P.change_room(G, kits, store, {}, sv, room['n'], reroll=True, seed=1)
after = {(m.key, m.x, m.y, m.z, m.turn) for m in store['last']['made'] if m.owner != room['n']}
check('re-rolling a room leaves every other piece alone', back.get('ops') and before == after, back.get('note', ''))
theirs = {(it.key, tuple(it.p)) for it in store['last']['items'] if it.owner != room['n']}
back = P.change_room(G, kits, store, {}, sv, room['n'], purpose='store', seed=2)
now = {(it.key, tuple(it.p)) for it in store['last']['items'] if it.owner != room['n']}
check('giving it another purpose leaves everything else\'s things alone', back.get('ops') and theirs <= now, back.get('note', ''))
check('… and the plan says so', next(r for r in back['plan']['rooms'] if r['n'] == room['n'])['purpose'] == 'store')
rows = P.room_themes(G, kits, store, sv, room['n'])
check('the real places a room could copy are listed, best first', rows['rows'] and rows['rows'] == sorted(rows['rows'], key=lambda r: -r['score']))
pick = rows['rows'][-1]['cell']
back = P.change_room(G, kits, store, {}, sv, room['n'], theme=str(pick), seed=3)
check('… and one can be chosen, as the page sends it', back.get('ops') and next(r for r in back['plan']['rooms'] if r['n'] == room['n'])['theme'] == pick)
check('a room not in the plan says so', P.change_room(G, kits, store, {}, sv, 9999).get('note'))
check('… and with nothing made yet, it says that', P.change_room(G, kits, {}, {}, sv, 1).get('note'))


# ---------- a floor plan drawn by hand ----------
rooms = [{'x': 0, 'y': 0, 'w': 4, 'h': 4, 'purpose': 'entrance'}, {'x': 4, 'y': 0, 'w': 5, 'h': 4, 'purpose': 'mess'},
         {'x': 0, 'y': 8, 'w': 5, 'h': 4, 'purpose': 'clinic'}, {'x': 8, 'y': 8, 'w': 4, 'h': 4, 'level': 1, 'purpose': 'office'}]
got = P.drawn(G, kits, VAULT, rooms, [[0, 1], [0, 2], [2, 3]], 2, [0, 0, 0], store, {}, sv)
check('a drawn plan: built, a door where rooms touch, a corridor where they don\'t, stairs between levels', got.get('ops') and got.get('levels', 0) >= 2, got.get('note', ''))
if got.get('ops'):
    plan = store['last']['plan']
    check('… its rooms where they were drawn, for what they were drawn for', {(o['purpose'], min(c[0] for c in o['cells']), min(c[1] for c in o['cells'])) for o in plan.rooms()} >= {('entrance', 0, 0), ('mess', 4, 0), ('clinic', 0, 8), ('office', 8, 8)})
    check('… the first room to the second through the wall they share', any(plan.cells.get(tuple(x)) in (0, 1) and len({plan.cells.get(y) for y in link}) == 2 and {plan.cells.get(y) for y in link} == {0, 1} for link in plan.links for x in link))
    check('… every square walked', clean(P.walk_check(G, vt, plan, store['last']['made'])))
check('what can\'t be drawn says why: overlapping', 'overlap' in P.drawn(G, kits, VAULT, [rooms[0], rooms[0]], [], 2, [0, 0, 0], store, {}, sv).get('note', ''))
check('… too narrow', 'narrow' in P.drawn(G, kits, VAULT, [{'x': 0, 'y': 0, 'w': 1, 'h': 5}], [], 2, [0, 0, 0], store, {}, sv).get('note', ''))
check('… not joined', 'joins room 2' in P.drawn(G, kits, VAULT, rooms[:3], [[0, 2]], 2, [0, 0, 0], store, {}, sv).get('note', ''))


# ---------- furnishing ----------
check('a word is a word: "can" is a tin, not part of a scanner', 'eat' in D.tags_of('NVFoodCan01') and 'eat' not in D.tags_of('Scanner01') and 'eat' not in D.tags_of('Candle01'))
check('a chair says nothing about what a room is for', not D.tags_of('ChairMetal01') and not D.tags_of('Bench01'))
check('… a swivel chair and a desk say office, a terminal too', 'desk' in D.tags_of('ChairSwivel01') and 'desk' in D.tags_of('MetalDesk01') and 'desk' in D.tags_of('TerminalWall'))
check('… a word run together still counts if it\'s long enough', 'desk' in D.tags_of('metalfilingcabinet') and 'care' in D.tags_of('vaultfirstaidbox'))
every = {t for ws in D.PURPOSE_TAGS.values() for t in ws}
g = P.generate(G, vt, 180, 13, survey=sv)
rooms_ = g['plan'].rooms()
vs = sv[VAULT]
rows = D.theme_scores(vs, [m for m in g['made'] if m.owner == rooms_[1]['n']], {'sleep'}, every - {'sleep'})
check('real places are scored as whole rooms, best first', rows and rows == sorted(rows, key=lambda r: (-r[0], r[1])))
for seed in range(3):
    g = P.vault_place(G, kits, 3, seed + 31, store, {}, sv)
    plan = g['plan']
    per = collections.Counter((it.owner, it.key) for it in g['items'] if it.what in D.BIG_KINDS)
    over = sum(1 for (owner, _k), n in per.items() if n > max(1, sum(1 for c in plan.owners[owner]['cells'] if c not in plan.air) // D.SAME_THING))
    check('seed %d: no room has more of one big thing than it has room for (%d over)' % (seed, over), not over)
    step = vt.step
    bad = 0
    for link in plan.links:
        a, b = tuple(link)
        x, y = plan.cells.get(a), plan.cells.get(b)
        if x == y or x is None or y is None or a[2] != b[2]:
            continue
        mx, my = (a[0] + b[0]) / 2 * step, (a[1] + b[1]) / 2 * step
        floor = a[2] * plan.rise + vt.floor
        for it in g['items']:
            if it.what in D.SOLID and floor - 64 <= it.p[2] < floor + D.HUNG and abs(it.p[0] - mx) < 40 and abs(it.p[1] - my) < 40:
                bad += 1
    check('… nothing solid stands in a doorway (%d)' % bad, not bad)


# ---------- first navmesh, on every level ----------
def cover(ts, plan, made, items):
    refs = P.as_refs(G, made) + D.item_refs(G, items)
    for n, it in enumerate(items):
        if it.what in ('door', 'exit'):
            refs.append({'ref': 200000 + n, 'type': 'REFR', 'base': G.from_key(it.key), 'pos': tuple(it.p[:3]), 'rot': tuple(it.p[3:6]), 'scale': 1.0, 'leads': False, 'bkey': it.key})
    mesh, _rep = navgen.generate(G, next(iter(G.interiors)), refs=refs, floors=True)
    area = collections.Counter()
    V = mesh['verts']
    for t in mesh['tris']:
        a, b, c = V[t[0]], V[t[1]], V[t[2]]
        area[int(((a[2] + b[2] + c[2]) / 3 + plan.rise * 0.35) // plan.rise)] += abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
    squares = collections.Counter(c[2] for c in plan.squares())
    return {lv: area[lv] / (squares[lv] * ts.step ** 2) for lv in squares}


g = P.vault_place(G, kits, 4, 41, store, {}, sv)
cov = cover(vt, g['plan'], g['made'], g['items'])
check('a vault\'s first navmesh covers every level, the balconies\' too: %s' % {k: round(v, 2) for k, v in sorted(cov.items())}, cov and min(cov.values()) >= 0.35)
tall = next(o for o in g['plan'].rooms() if o.get('tall'))
print('     tall room squares %d' % len(tall['cells']))
_ = math
