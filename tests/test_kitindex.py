import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""The kit index: pieces read as they are, sections agree with what the game built far more than chance, layouts fill
any area with every side agreeing, walking them finds no way out, and a layout can be grown further."""
import gamedata, kitindex as K


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


G = gamedata.GameData()
kits = K.build(G)
check('kits read from the game (%d)' % len(kits), len(kits) > 40)
vault = kits['dungeons\\vault']
check('the vault kit stands on a 256 grid', vault.step == 256)
by = {p.edid: p for p in vault.pieces.values()}
ways = lambda name: {s['side'] for s in by[name].slots if s['open']}
check('a straight hall opens at its two ends', len(ways('VHallSm1Way01')) == 2)
check('a four-way hall opens on all four sides', len(ways('VHallSm4Way01')) == 4)
check('a room\'s middle opens on all four sides', len(ways('VRmMid01')) == 4)
check('a room\'s wall piece is closed on one side', len(ways('VRmWall01')) == 3)
check('a room\'s corner is closed on two', len(ways('VURmCorner01')) == 2)

# what the game built, against the sections
good = total = 0
for (a, b, dx, dy, dz, t), n in vault.seen.items():
    pa, pb = vault.pieces[a], vault.pieces[b]
    if dz or (abs(dx), abs(dy)) not in ((256, 0), (0, 256)) or not pa.slots or not pb.slots or len(pa.slots) != 4 or len(pb.slots) != 4:
        continue
    side = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}[(dx // 256, dy // 256)]
    sa = next(s for s in pa.slots if s['side'] == side)
    sb = next(s for s in pb.slots if s['side'] == (side + 2 + t) % 4)
    if sa['open'] and sb['open'] and sa['floor'] == sb['floor']:
        total += n
        good += n * (K.score(sa['cells'], sb['cells']) >= K.FIT_SCORE)
check('joins the game built match by shape (%d of %d)' % (good, total), total > 500 and good / total > 0.75)

# keeping it on disk changes nothing
home = tempfile.mkdtemp()
import json
back = K.from_json(json.loads(json.dumps(K.to_json({'v': vault}))))['v']
ts, ts2 = K.Tileset(vault, min_uses=2), K.Tileset(back, min_uses=2)
check('read back from disk, the same tiles and sockets', ts.vars == ts2.vars and ts.sides == ts2.sides)

# layouts
cells = [(i, j) for i in range(10) for j in range(10)]
for name in ('dungeons\\vault', 'dungeons\\vaultruined', 'dungeons\\office', 'dungeons\\industrial', 'dungeons\\facility', 'dungeons\\nv_casinolo', 'dungeons\\caves'):
    t = K.Tileset(kits[name], min_uses=2)
    made = [K.build_area(t, cells, s) for s in range(4)]
    made = [m for m in made if m]
    check('%s: layouts made, every side agreeing' % name, len(made) >= 3 and not any(K.check(t, m) for m in made))
    walks = [K.can_walk_out(G, t, m) for m in made]
    check('%s: walking them, no way out, and room to walk' % name, not any(w[1] for w in walks) and all(w[0] > 0 for w in walks))

# growing further: what's built stays, the new squares join on
# (a finished layout's edge is closed, so cut one in half: the half kept has ways out for the new squares to meet)
keep, grown = {}, None
for s in range(30):
    first = K.build_area(ts, [(i, j) for i in range(8) for j in range(8)], s)
    if not first:
        continue
    half = K.connected(ts, {c: v for c, v in first.items() if c[0] < 4})
    out_ways = [c for c, v in half.items() for d in range(4) if ts.walks(ts.sides[v][d]) and (c[0] + K.DX[d][0], c[1] + K.DX[d][1]) not in half]
    if not out_ways:
        continue
    more = [(i, j) for i in range(16) for j in range(8) if (i, j) not in half]
    grown = K.build_area(ts, more, 1, fixed=half)
    if grown:
        keep = half
        break
check('grown further: more pieces, the old ones kept', bool(keep) and len(grown) > 0 and not set(grown) & set(keep))
every = dict(keep); every.update(grown or {})
check('… every side still agrees', not K.check(ts, every))
ops = K.as_placed(ts, every)
check('as changes for the mod: one for each piece', len(ops) == len(every) and all(o['op'] == 'add' and len(o['p']) == 6 for o in ops))

# what joins a piece, in the world
hall = by['VHallSm4Way01']
sides = K.piece_sides(vault, hall, [1000.0, 2000.0, 300.0], 1, [])
check('what joins a piece: a four-way has four free sides, facing every way', sorted(x['face'] for x in sides) == [0, 1, 2, 3] and not any(x['taken'] for x in sides))
east = next(x for x in sides if x['face'] == 0)
check('… the east side stands half a square east, on the floor', east['at'][:2] == [1128.0, 2000.0] and east['at'][2] == 300.0)
check('… the joins the game built come first', east['fits'][0]['times'] > 0 and east['fits'] == sorted(east['fits'], key=lambda f: (-f['times'], -f['uses'], f['edid'])))
one = east['fits'][0]
other = vault.pieces[one['key']]
t = K.quarter(one['p'][5])
sides2 = K.piece_sides(vault, other, one['p'][:3], t, [(hall, 1000.0, 2000.0, 300.0, 1)])
check('… placed there, its side back towards the hall is taken', any(x['taken'] and x['face'] == 2 for x in sides2))
taken = K.piece_sides(vault, hall, [1000.0, 2000.0, 300.0], 1, [(other, one['p'][0], one['p'][1], one['p'][2], t)])
check('… and the hall\'s side towards it is taken, the rest free', [x['face'] for x in taken if x['taken']] == [0] and len([x for x in taken if not x['taken']]) == 3)

# the layout the editor asks for
got = K.layout(G, kits, 'dungeons' + chr(92) + 'vault', 8, 8, 1, [256, 512, 64], {}, {})
check('a layout for the editor: changes for the mod, where it was asked', got.get('ops') and all(o['op'] == 'add' for o in got['ops']) and got['ops'][0]['p'][2] == 64)
check('… halls and rooms joined up: most of the area filled', len(got['ops']) >= 20)
few = K.layout(G, {'x': K.Kit('x')}, 'x', 4, 4, 1, [0, 0, 0], {}, {})
check('a kit with too few pieces says so', 'note' in few and 'ops' not in few)
check('kits have names for people', K.label_of('nvdlc03' + chr(92) + 'dungeons' + chr(92) + 'x13') == 'X-13 (Old World Blues)' and K.label_of('dungeons' + chr(92) + 'nvlucky38') == 'Lucky 38')

# ---------- planned places (kitplan.py) ----------
import kitplan as P
B = chr(92)
vt = P.PlanTiles(vault, G)
check('the vault kit: rooms, corridors, bends, junctions, stairs', vt.can['rooms'] and vt.can['halls'] and vt.hall_can('hallsmall', '..PP') and vt.hall_can('hallsmall', '.PPP') and bool(vt.stairs))
check('a side of a piece read as a word: a room middle full, a wall along, a door a passage', P.side_word(by['VRmMid01'].slots[0], 256) == 'F' and P.side_word(by['VRmWall01'].slots[0], 256) == 'A' and P.side_word(by['VRmWallExSm01'].slots[3], 256) == 'P')
check('a bend\'s chamfered corner isn\'t a way through', [P.side_word(s, 256) for s in by['VHallSm2Way01'].slots].count('.') == 2)
check('a flight of stairs: its rise is the game\'s own', vt.stairs[0].rise == 256 and vt.stairs[0].piece.edid == 'VHallSmStairs01')

# every kit that generates: sealed, connected, its rooms really there, repeats limited
for name, k in sorted(kits.items()):
    if len(K.Tileset(k).slot_sock) < K.MIN_TILES:
        continue
    ts = P.PlanTiles(k, G)
    if not ts.can['rooms']:
        continue
    good = rooms_ok = True
    rep_n = rep_t = made_n = 0
    for seed in range(2):
        g = P.generate(G, ts, 110, seed)
        if not g:
            continue
        made_n += 1
        w = P.walk_check(G, ts, g['plan'], g['made'])
        good = good and not w['missing'] and not w['escaped']
        by_cell = {c: m for m in g['made'] for c in m.cells}
        for o in g['plan'].rooms():
            rooms_ok = rooms_ok and all(c in by_cell and by_cell[c].owner == o['n'] for c in o['cells'] if c not in g['plan'].air)
        a, b = P.repeats(ts, g['made'])
        rep_n, rep_t = rep_n + a, rep_t + b
    check('%s: planned places made, sealed and every part reached (%d)' % (name, made_n), made_n >= 1 and good)
    check('%s: the plan\'s rooms are in the result' % name, rooms_ok)
    # (rooms' floors may have only one piece that fits: counted only where there's another)
    print('     repeats %d of %d' % (rep_n, rep_t))

g = P.generate(G, vt, 240, 3)
check('a bigger vault place: at least 8 rooms, all placed, one of them the far end', g and len(g['plan'].rooms()) >= 8 and any(o['purpose'] == 'far end' for o in g['plan'].rooms()))
a, b = P.repeats(vt, g['made'])
check('… pieces beside themselves are few where there are others (%d of %d)' % (a, b), a < 0.2 * b)
check('… corridors, not only doors', any(o['kind'] == P.HALL for o in g['plan'].owners))
sizes = {len(o['cells']) for o in g['plan'].rooms()}
check('… rooms of different sizes (%s)' % sorted(sizes), len(sizes) >= 3)
two = next((P.generate(G, vt, 240, s) for s in range(4, 40) if any(c[2] != 0 for c in P.generate(G, vt, 240, s)['plan'].cells)), None)
check('… more than one level, stairs among the pieces, and the walk gets to all of them', two and any(m.key == vt.stairs[0].piece.key for m in two['made']) and not two['walk']['missing'])
ot = P.PlanTiles(kits['dungeons' + B + 'office'], G)
big_keys = {p.key for p, _w, _h in ot.big}
check('… bigger pieces are used too, in the kits that have them', any(m.key in big_keys for s in range(3) for g2 in [P.generate(G, ot, 240, s)] if g2 for m in g2['made']))
cut = P.Plan(vt.step)
cut.add_room('a', 'room', [(i, j, 0) for i in range(4) for j in range(4)])
cut.add_room('b', 'room', [(i, j, 0) for i in range(6, 10) for j in range(4)])
made = P.fill(vt, cut, 1)
w = P.walk_check(G, vt, cut, made)
check('the walk finds a room with no way to it', len(w['missing']) == 16 and not w['escaped'])
ed = P.layout(G, kits, 'dungeons' + B + 'vault', 24, 24, 5, [256, 512, 64], {}, {})
check('a place for the editor: changes for the mod, on the spot asked, words for the person', ed.get('ops') and all(o['op'] == 'add' and o['gen'] for o in ed['ops']) and 'rooms' in ed['said'] and min(o['p'][2] for o in ed['ops']) >= 64 - 6 * 256)
cave = P.layout(G, kits, 'dungeons' + B + 'caves', 8, 8, 2, [0, 0, 0], {}, {})
check('a kit with no room pieces is still filled and walked, or says why', cave.get('ops') or cave.get('note'))

# ---------- doors, lights and things (kitdress.py) ----------
import math
import kitdress as D, navgen, navmesh as N
sv = D.survey(G, kits, only={'dungeons' + B + 'vault', 'dungeons' + B + 'vaultruined', 'dungeons' + B + 'office'})
vs = sv['dungeons' + B + 'vault']
check('the survey: lights, furniture and things stand on the vault\'s pieces', vs.sets and any(i[0] == 'light' for i in vs.info.values()) and any(i[0] == 'furn' for i in vs.info.values()))
check('… sets come from real places, including nothing at all', len(vs.src[by['VRmMid01'].key]) == len(vs.sets[by['VRmMid01'].key]) and any(not st for st in vs.sets[by['VRmWall01'].key]))
door_at = vs.doors.get(by['VRmWallExSm01'].key)
check('… doors are read in their pieces: on the doorway\'s line', door_at and any(abs(p[1]) < 8 and abs(abs(p[2]) - 128) < 8 for p in door_at))
back = D.from_json(json.loads(json.dumps(D.to_json({'v': vs}))))['v']
check('… read back from disk, the same', back.sets[by['VRmMid01'].key] == [[tuple(i) for i in st] for st in vs.sets[by['VRmMid01'].key]] and back.doors[by['VRmWallExSm01'].key] == door_at)
for name in sv:
    store = {}
    ts = P.tiles_for(G, kits, name, store, sv)
    for seed in range(3):
        g = P.generate(G, ts, 130, seed, survey=sv, ruined='ruined' in name)
        if not g:
            check('%s: a dressed place made (seed %d)' % (name, seed), False)
            continue
        kinds = {it.what for it in g['items']}
        check('%s: seed %d: doors, an exit, lights and things (%d)' % (name, seed, len(g['items'])), {'door', 'exit', 'light'} <= kinds and len(kinds) > 3)
        w = P.walk_check(G, ts, g['plan'], g['made'], extra=D.item_refs(G, g['items']))
        check('… nothing it stands blocks the way: every part still reached as the navmesh will be cut', not w['missing'] and not w['escaped'])
        squares = {(c[0], c[1]) for c in g['plan'].squares()}
        step = ts.step
        out = [it for it in g['items'] if it.what not in ('door', 'exit') and not any((math.floor((it.p[0] + a) / step + 0.5), math.floor((it.p[1] + b) / step + 0.5)) in squares for a in (-40, 0, 40) for b in (-40, 0, 40))]
        check('… and all of it stands inside the walls (%d out)' % len(out), not out)
        lit = {it.owner for it in g['items'] if it.what == 'light'}
        rooms = [o['n'] for o in g['plan'].rooms()]
        check('… every room has a light (%d of %d)' % (len(lit & set(rooms)), len(rooms)), len(lit & set(rooms)) >= 0.8 * len(rooms))
        ex = next(it for it in g['items'] if it.what == 'exit')
ts = P.tiles_for(G, kits, 'dungeons' + B + 'vault', {}, sv)
g = P.generate(G, ts, 130, 1, survey=sv)
ex = next(it for it in g['items'] if it.what == 'exit')
some_cell = next(iter(G.interiors))
linked = P.as_refs(G, g['made']) + [{'ref': 999999, 'type': 'REFR', 'base': G.from_key(ex.key), 'pos': tuple(ex.p[:3]), 'rot': tuple(ex.p[3:6]), 'scale': 1.0, 'leads': True, 'bkey': ex.key}]
mesh, rep = navgen.generate(G, some_cell, refs=linked, floors=True)
got, missed = N.link_doors(mesh, rep.get('doors') or [])
check('the exit door, once it leads somewhere, is linked into the navmesh', mesh and len(got) == 1 and not missed and not N.validate(mesh))
big = sorted(len(x) for x in P.Walk(G, linked, (0, 0, 0), erode=True).pieces)
check('… and that navmesh\'s main part is the place itself: the rest is roofs (%d pieces kept)' % rep['kept_pieces'], rep['kept_pieces'] <= 8 and big[-1] > 0)
check('room purposes ask for different things', set(D.PURPOSE_TAGS['quarters']) != set(D.PURPOSE_TAGS['reactor']))

# ---------- a vault in one click ----------
for ruined in (False, True):
    label = 'ruined vault' if ruined else 'vault'
    for size, least in ((2, 6), (6, 11)):
        v = P.vault(G, kits, size, 11 + size, [0, 0, 0], {}, {}, sv, ruined)
        rooms = dict(v.get('rooms') or [])
        check('a %s, size %d: entrance, atrium, quarters, overseer\'s office, reactor (%s)' % (label, size, rooms), {'entrance', 'atrium', 'quarters', 'office', 'reactor'} <= set(rooms))
        check('… the dial means something: %d rooms or more' % least, sum(rooms.values()) >= least)
        check('… with changes for the mod and words for the person', v.get('ops') and 'said' in v and 'vault' in v['said'])

# ---------- growing further ----------
store = {}
ts = P.tiles_for(G, kits, 'dungeons' + B + 'vault', store, sv)
g = P.generate(G, ts, 100, 8, survey=sv)
n = 0
pieces = []
for m in g['made']:
    n += 1
    pieces.append((m.key, m.x + 512.0, m.y + 1024.0, m.z + 64.0, m.turn, '+%d' % n))
before = len(pieces)
one = P.grow(G, kits, 'dungeons' + B + 'vault', pieces, 60, 3, store, {}, sv)
check('grown from a place: more pieces', one.get('ops') and sum(1 for o in one['ops'] if o['op'] == 'add') > 10)
gone = [o for o in one['ops'] if o['op'] == 'remove']
check('… only one piece goes, and that a real one', len(gone) == 1 and any(p[5] == gone[0]['ref'] for p in pieces))
step = ts.step
taken = {(round(p[1]), round(p[2]), round(p[3])) for p in pieces if p[5] != gone[0]['ref']}
added = [o for o in one['ops'] if o['op'] == 'add' and o['base'] in kits['dungeons' + B + 'vault'].pieces and kits['dungeons' + B + 'vault'].pieces[o['base']].slots]
check('… nothing new stands on anything old', not any((round(o['p'][0]), round(o['p'][1]), round(o['p'][2])) in taken for o in added))
for o in added:
    pieces.append((o['base'], o['p'][0], o['p'][1], o['p'][2], K.quarter(o['p'][5]), '+g%d' % len(pieces)))
pieces = [p for p in pieces if p[5] != gone[0]['ref']]
all_refs = [{'ref': i, 'type': 'REFR', 'base': G.from_key(p[0]), 'pos': tuple(p[1:4]), 'rot': (0.0, 0.0, p[4] * math.pi / 2), 'scale': 1.0, 'leads': False, 'bkey': p[0]} for i, p in enumerate(pieces)]
c = g['plan'].owners[0]['cells'][0]
walked = P.Walk(G, all_refs, (one['start'][0], one['start'][1], one['start'][2] + 8), erode=True)
first = P.Walk(G, P.as_refs(G, g['made']), (c[0] * step, c[1] * step, 8), erode=True)
check('… old and new walk as one: from the doorway it covers more than the place had (%d, was %d)' % (len(walked.reached), len(first.reached)), len(walked.reached) > 1.2 * len(first.reached))
two = P.grow(G, kits, 'dungeons' + B + 'vault', pieces, 60, 5, store, {}, sv)
check('… and grown again from that', two.get('ops') and sum(1 for o in two['ops'] if o['op'] == 'add') > 10)
