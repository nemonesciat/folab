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
