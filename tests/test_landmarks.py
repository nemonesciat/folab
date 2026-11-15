"""Landmarks and a harbour (landmarks.py): the game's great buildings are found as the game stands them, piece by piece;
one is stood elsewhere turned and sized with its pieces still in place against each other, on ground levelled for it and
cleared; a harbour is the game's dock pieces over the water at the game's own height, with boats beside them."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import landmarks  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
got = {name: landmarks.lift(gd, name) for name in landmarks.SETS}
check('every set is found in the game', all(got.values()), [n for n, g in got.items() if not g])
lucky = got['lucky38']
names = sorted(gd.edid(gd.from_key(p[0])) for p in lucky['pieces'])
check('the Lucky 38 is its base, its tower and its overhangs', {'Lucky38', 'Lucky38Base', 'Lucky38Top', 'Lucky38Overhang01'} <= set(names) and len(names) == 8, names)
check('none of its signs or lights from other worlds', not any('WL' in n or 'Sign' in n for n in names))
check('it stands on the ground, not far over or under it', all(-100 < p[3] < 200 for p in lucky['pieces']), [round(p[3]) for p in lucky['pieces']])
check('and is as wide as the game has it', 5000 < lucky['box'][2] - lucky['box'][0] < 7500, lucky['box'])
check('The Tops as on the Strip is many pieces spread over its block', len(got['tops_strip']['pieces']) >= 10 and got['tops_strip']['box'][2] - got['tops_strip']['box'][0] > 5000)
check('a set put together here seats each thing as the game does', all(abs(p[3]) < 2600 for p in got['lookout']['pieces']) and len(got['lookout']['pieces']) == 8)

# ---------- one stood somewhere else ----------
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
g0 = roadgen.Ground(gd, None, world)


def flat(k):
    hs = [h for dx in (-1, 0, 1) for dy in (-1, 0, 1) for h in (g0.cell((k[0] + dx, k[1] + dy)) or [None])]
    return None not in hs and max(hs) - min(hs) < 700 and min(hs) > 2000


xy = next(k for k in sorted(grid) if flat(k))
x, y = xy[0] * 4096.0 + 2048, xy[1] * 4096.0 + 2048
pr = project.Project.create('Landmark')
tire = next(f for f, (i, r) in gd.forms.items() if gd.edid(f) == 'Tire01Static')
pr.apply('add', [{'op': 'add', 'cell': gd.key(grid[xy]), 'base': gd.key(tire), 'p': [x + 100, y + 100, g0.at(x, y), 0.0, 0.0, 0.0], 's': 1},
                 {'op': 'add', 'cell': gd.key(grid[xy]), 'base': gd.key(tire), 'p': [x + 3900, y + 3900, g0.at(x, y), 0.0, 0.0, 0.0], 's': 1}])
B = landmarks.Batch(gd, pr, world)
rep = B.stand('lucky38', x, y, turn=math.pi / 2, scale=0.5, nudge=0)
check('stood where asked, all of it', rep and rep['pieces'] == 8 and rep['moved'] == 0 and (rep['x'], rep['y']) == (round(x), round(y)), rep)
ops = B.done()
adds = [o for o in ops if o['op'] == 'add']
gone = [o for o in ops if o['op'] == 'remove']
lands = [o for o in ops if o['op'] == 'land']
check('what the mod had under it goes, what was beside it stays', len(gone) == 1)
check('removals first, then the ground, then the pieces', [o['op'] for o in ops] == ['remove'] * len(gone) + ['land'] * len(lands) + ['add'] * len(adds))
base = next(o for o in adds if gd.edid(gd.from_key(o['base'])) == 'Lucky38Base')
top = next(o for o in adds if gd.edid(gd.from_key(o['base'])) == 'Lucky38Top')
src_b = next(p for p in lucky['pieces'] if gd.edid(gd.from_key(p[0])) == 'Lucky38Base')
src_o = next(p for p in lucky['pieces'] if gd.edid(gd.from_key(p[0])) == 'Lucky38Overhang01')
over = next(o for o in adds if gd.edid(gd.from_key(o['base'])) == 'Lucky38Overhang01')
d_src = math.hypot(src_o[1] - src_b[1], src_o[2] - src_b[2])
d_new = math.hypot(over['p'][0] - base['p'][0], over['p'][1] - base['p'][1])
check('its pieces keep their places against each other, at half size', abs(d_new - d_src * 0.5) < 1.0, (d_src, d_new))
check('each piece half the size the game has it, turned a quarter', abs(base['s'] - src_b[7] * 0.5) < 0.002
      and abs((base['p'][5] - src_b[6] - math.pi / 2 + math.pi) % math.tau - math.pi) < 0.001, (base['s'], base['p'][5]))
pr.apply('landmark', ops)
g1 = roadgen.Ground(gd, pr, world)
box = [v * 0.5 for v in lucky['box']]
inside = [g1.at(x + dx, y + dy) for dx in (-1200, 0, 1200) for dy in (-1200, 0, 1200)]
check('the ground under it is level, at the height it stands', max(inside) == min(inside) == rep['level'], (min(inside), max(inside), rep['level']))
check('the tower stands on that ground', abs(top['p'][2] - rep['level'] - next(p for p in lucky['pieces'] if p[0] == top['base'])[3] * 0.5) < 0.2)
keep = landmarks.standing(gd, pr, world)
check('where it stands is known afterwards, for the ground to be left under it', len(keep) >= 4 and all(math.hypot(k[0] - x, k[1] - y) < 2000 for k in keep), len(keep))
left = landmarks.clear_of([{'op': 'add', 'p': [x + 50, y, 0, 0, 0, 0]}, {'op': 'add', 'p': [x + 30000, y, 0, 0, 0, 0]}, {'op': 'land'}], keep)
check('things to be put inside it are dropped, the rest kept', len(left) == 2 and left[0]['p'][0] == x + 30000)

# a road through the spot: it moves off it
road = [{'line': [(x - 6000, y - 3100), (x + 6000, y - 3100)], 'class': 'major'}]     # (along its edge: a little way off clears it)
B2 = landmarks.Batch(gd, project.Project.create('Landmark 2'), world, road)
rep2 = B2.stand('battery', x, y)
check('off a road in its way, by moving or by turning', rep2 and (rep2['moved'] > 0 or rep2['turn'] != 0) and not any(B2.on_road(o['p'][0], o['p'][1]) for o in B2.done() if o['op'] == 'add'), rep2)
B4 = landmarks.Batch(gd, project.Project.create('Landmark 3'), world, [{'line': [(x - 6000, y), (x + 6000, y)], 'class': 'minor'}])
rep4 = B4.stand('battery', x, y)
check('but it stays at its place when only far off would clear a street', rep4 and rep4['moved'] <= 800, rep4)

# ---------- a harbour ----------
lake = None
for k in sorted(grid):
    w, g = g0.water(k[0] * 4096.0 + 2048, k[1] * 4096.0 + 2048), g0.at(k[0] * 4096.0 + 2048, k[1] * 4096.0 + 2048)
    if w is not None and g is not None and g < w - 400 and all((g0.at(k[0] * 4096.0 + dx, k[1] * 4096.0 + dy) or 1e9) < w - 150 for dx in (200, 3800) for dy in (200, 3800)):
        lake = k
        break
check('the game has open water to try it on', lake is not None)
lx, ly = lake[0] * 4096.0 + 600, lake[1] * 4096.0 + 2048
B3 = landmarks.Batch(gd, project.Project.create('Harbour'), world)
hb = B3.harbour([[(lx, ly), (lx + 2560, ly)], [(lx, ly + 100), (lx + 2560, ly + 100)], [(lx + 1000, ly + 1500), (lx + 1100, ly + 1500)]])
level = g0.water(lx, ly)
docks = [o for o in B3.ops if gd.edid(gd.from_key(o['base'])) == landmarks.DOCK]
check('a pier is dock pieces a step apart along it', hb['piers'] == 2 and 9 <= len([d for d in docks if abs(d['p'][1] - ly) < 1]) <= 11, hb)
check('as high over the water as the game has them', all(abs(d['p'][2] - level - landmarks.DOCK_UP) < 0.2 for d in docks))
check('a pier too near another is left out', not any(abs(d['p'][1] - ly - 100) < 1 for d in docks))
short = [d for d in docks if abs(d['p'][1] - ly - 1500) < 1]
check('a short one is built long enough to be a pier', len(short) >= 6, len(short))
check('boats lie beside them, some gone down', hb['boats'] >= 3 and hb['boats'] + hb['sunk'] + hb['aground'] >= 5, hb)
floats = [o for o in B3.ops if gd.edid(gd.from_key(o['base'])).lower().startswith('boat02') and abs(o['p'][3]) < 0.06]
check('the ones afloat sit in the water, not over or under it', all(-80 < o['p'][2] - level < 0 for o in floats) and bool(floats), len(floats))
check('nothing is built where there is no water', landmarks.Batch(gd, project.Project.create('Dry'), world).harbour([[(x, y), (x + 3000, y)]])['dock'] == 0)

# ---------- open backs ----------
check('a casino made to be seen from the street is stood twice, back to back', got['ultraluxe']['doubled'] and got['tops_strip']['doubled']
      and len(got['ultraluxe']['pieces']) == 4, (got['ultraluxe']['doubled'], got['tops_strip']['doubled']))
check('so that no side of it is open', min(got['ultraluxe']['sides']) > 0.7 and min(got['tops_strip']['sides']) > 0.7, (got['ultraluxe']['sides'], got['tops_strip']['sides']))
check('what is whole already is stood once', not got['battery']['doubled'] and not got['lookout']['doubled'] and min(got['battery']['sides']) > 0.9)

# ---------- whole from every side ----------
import math as _m  # noqa: E402


def all_round(name):
    shapes = landmarks._shapes(gd, got[name]['pieces'])
    vals = []
    for k in range(4):
        c, sn = _m.cos(k * _m.pi / 8), _m.sin(k * _m.pi / 8)
        vals += landmarks.closed_sides([dict(sh, p=[v for q in range(0, len(sh['p']), 3)
                                                    for v in (sh['p'][q] * c + sh['p'][q + 1] * sn, -sh['p'][q] * sn + sh['p'][q + 1] * c, sh['p'][q + 2])]) for sh in shapes])
    return min(vals)


check('The Tops stood as a landmark is the game's all-round one: a wall from each of sixteen sides', len(got['tops']['pieces']) == 1 and all_round('tops') > 0.95, all_round('tops'))
check('and stands on the ground, not at the height it has far off', abs(got['tops']['pieces'][0][3] + 688) < 1)
check('the grand hotel is buildings whole from every side', all_round('grandhotel') > 0.95 and len(got['grandhotel']['pieces']) == 10, all_round('grandhotel'))
check('the Strip's own pieces are not: stood back to back they still show a way in from some side', all_round('tops_strip') < 0.9, all_round('tops_strip'))

# ---------- nothing flies ----------
bad = []
for name in ('grandhotel', 'pool', 'lookout', 'battery'):
    for key, dx, dy, dz, rx, ry, rz, sc in got[name]['pieces']:
        fid = gd.from_key(key)
        e = gd.edid(fid)
        o = landmarks._obnd(gd, fid)
        if e in ('TheTopsPool', 'NVDLC03GunBatterySTATIC') or not o:
            continue
        under = dz + o[2] * sc
        if not -20 <= under <= 4:
            bad.append((name, e, round(under)))
check('each thing put round a landmark has its own underside on the ground: no palm in the air, no buried flagpole', not bad, bad)
low = min(dz + landmarks._obnd(gd, gd.from_key(key))[2] * sc for key, dx, dy, dz, rx, ry, rz, sc in got['battery']['pieces'] if gd.edid(gd.from_key(key)) == 'NVDLC03GunBatterySTATIC')
check('and a set lifted from the game stands on the ground too', -170 <= low <= 50, low)
