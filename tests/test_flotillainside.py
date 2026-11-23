"""Inside the Flotilla's ship (flotillainside.py): each place builds from the game's kit and walks with its things in,
its doors pair up with another place's or her deck's, and `board` on a small mod links every one both ways."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import flotilla  # noqa: E402
import flotillainside as fi  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
built = {}
for key, (edid, full, _fn) in fi.PLACES.items():
    try:
        built[key] = fi.build(gd, key)
        said = ''
    except ValueError as e:
        said = str(e)
    check('%s is built from the kit and walked, its things in' % full, key in built and not built[key].walk['escaped'], said)
if len(built) < len(fi.PLACES):
    sys.exit(0)
ends = {(k, tag): to for k, B in built.items() for tag, (_d, _p, _a, to) in B.exits.items()}
ends.update({('deck', tag): to for tag, to in fi.SHIPS['flotilla']['to'].items()})
check('every way out names a way that names it back', all(ends.get(to) == frm for frm, to in ends.items()), sorted(ends.items())[:3])
check('the hold and the pens each have two ways out, below decks three, a boat\'s cabin one', [len(built[k].exits) for k in ('hold', 'pens', 'below', 'house', 'boat1', 'boat2')] == [2, 2, 3, 2, 1, 1])
check('every room is lit', all(len(B.lights) >= len(fi.layout(k).rooms) for k, B in built.items()), {k: len(B.lights) for k, B in built.items()})
half = flotilla.HALF_BEAM
check('her deck\'s ways in stand on her deck, inside her bulwarks, clear of the container blocks',
      all(abs(x) < half - 100 and abs(a[0]) < half - 100 and not any(y0 - 50 < a[1] < y0 + n * 854 + 50 for y0, n in flotilla.BLOCKS)
          for tag, (_e, x, _y, _t, a, *_up) in fi.DECK.items() if tag not in fi.BOATS))
import walkcheck  # noqa: E402
for tag in fi.BOATS:
    items, starts, goals = fi.boat_walk(gd, tag)
    w = {vox: walkcheck.walk(gd, items, ground=None, starts=starts, goals=goals, voxel=vox) for vox in (16.0, 32.0)}
    check('%s: its hatch is walked to from the planking, up the gangplank, as a player and as a navmesh sees it' % tag,
          all(v['goals'][0]['reached'] and not v['short'] and not v['invisible'] for v in w.values()), {k: v['reached'] for k, v in w.items()})

world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
mid = min(grid, key=lambda k: abs(k[0]) + abs(k[1]))
ship = (mid[0] * 4096.0 + 2048, mid[1] * 4096.0 + 2048, -280.0, 0.6)
pr = project.Project.create('Flotilla Inside')
ops, rep = fi.board(gd, pr, world, ship)
pr.apply('inside', ops)
names = dict(pr.names)
nav, nrep = fi.navmesh_ops(gd, pr, names)
pr.apply('inside', nav, merge=True)
places = {k: names['fl_' + k] for k in fi.PLACES}
check('six places of the mod\'s own, named', all(pr.records[c]['type'] == 'CELL' and recordio.field(pr.records[c], 'EDID') == 'FOLab' + fi.PLACES[k][0] for k, c in places.items()))
ref = {k: (ck, r) for ck, c in pr.cells.items() for k, r in c['refs'].items()}
doors = {k: v for k, v in ref.items() if v[1].get('tel')}
check('sixteen doors, each leading to one that leads back', len(doors) == 16 == rep['doors'] and all(ref[r['tel']['door']][1]['tel']['door'] == k for k, (_c, r) in doors.items()), len(doors))
deck = [(k, r) for k, (ck, r) in doors.items() if ck not in places.values()]
z = ship[2] - flotilla.SHIP_Z + flotilla.DECK
on_her = [(k, r) for k, r in deck if abs(r['p'][2] - z) <= 8]
check('three of them on her deck, at her deck\'s height, and one on each boat\'s', len(on_her) == 3 and len(deck) == 5, [r['p'][:3] for _k, r in deck])
planks = [r for _ck, r in ref.values() if r['base'] in pr.records and recordio.field(pr.records[r['base']], 'EDID') == 'FOLabFlotillaPlank']
check('a gangplank of the mod\'s own to each boat, one record for both', len(planks) == 2 == rep['extras'] and len({r['base'] for r in planks}) == 1)
out = [ref[r['tel']['door']][1]['tel']['p'] for _k, r in deck]
check('coming out, one arrives a step from the way in, just over what it stands on', all(any(0 < p[2] - r['p'][2] <= 16 and 60 < math.dist(p[:2], r['p'][:2]) < 200 for _k, r in deck) for p in out), out)
inside = [r['tel']['p'] for _k, (ck, r) in doors.items() if ck not in places.values()]
check('going in, one arrives over the place\'s deck, inside its squares', all(0 < p[2] <= 16 for p in inside), inside)
check('each place has a navmesh that names its doors', all(isinstance(nrep.get(k), dict) and not nrep[k]['doors_missed'] and places[k] in pr.navmesh for k in places),
      {k: (v.get('triangles'), v.get('doors')) if isinstance(v, dict) else v for k, v in nrep.items()})
try:
    fi.board(gd, pr, world, ship)
    twice = ''
except ValueError as e:
    twice = str(e)
check('asked again, it says she has her insides', 'already' in twice, twice)
before = len(pr.records)
pr.undo()
check('one Undo takes all of it out', not any(c in pr.records for c in places.values()) and not any(c in pr.navmesh for c in places.values()) and not pr.cells and not pr.records, (before, len(pr.records)))

# the settlers' freighter: the same, two places
pr = project.Project.create('Freighter Inside')
ops, rep = fi.board(gd, pr, world, ship, which='settler')
pr.apply('inside', ops)
names = dict(pr.names)
nav, nrep = fi.navmesh_ops(gd, pr, names, 'settler')
pr.apply('inside', nav, merge=True)
places = {k: names['se_' + k] for k in fi.SHIPS['settler']['places']}
ref = {k: (ck, r) for ck, c in pr.cells.items() for k, r in c['refs'].items()}
doors = {k: v for k, v in ref.items() if v[1].get('tel')}
check('the freighter: two places, six doors, each leading to one that leads back', len(places) == 2 and len(doors) == 6
      and all(ref[r['tel']['door']][1]['tel']['door'] == k for k, (_c, r) in doors.items()), len(doors))
check('her two ways in stand on her deck clear of her cargo hatches and her house', all(
    not any(abs(a[1] - hy) < 350 + 40 and abs(a[0]) < 410 + 40 for hy in (-2650.0, -1650.0, -650.0, 350.0, 1350.0)) and a[1] < fi.S_HOUSE_Y
    for _e, _x, _y, _t, a in fi.SHIPS['settler']['deck'].values()))
check('each of her places has a navmesh that names its doors', all(isinstance(nrep.get(k), dict) and not nrep[k]['doors_missed'] for k in places), nrep)
