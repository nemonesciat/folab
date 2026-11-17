"""The Missouri (battleship, shipinside): her hull and what stands on her build and check, at her real size; her four
places inside build and check, their doors pair up, the game's things they hold are there to be had; board makes the
places, the doors linked both ways and the doors on her deck, and each place gets a navmesh from FOLab's own model
(the mod's own collision, read from its files) with its doors on it."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import battleship  # noqa: E402
import gamedata  # noqa: E402
import modelmake  # noqa: E402
import modelsets  # noqa: E402
import nifmake  # noqa: E402
import project  # noqa: E402
import shipinside  # noqa: E402
import shipplace  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


m = modelsets.build('missouri')
m_desc = battleship.missouri()
wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
check('she builds, mesh and collision checked', not wrong, wrong[:3])
b = m['box']
check('270 m long, 33 m in the beam (70 units a metre)', 18800 < b[4] - b[1] < 19000 and 2300 < b[3] - b[0] < 2400, b)
check('her mast near 70 m over the water, her keel under it', 4500 < b[5] < 5500 and b[2] < -500, b)
check('she has a far model', bool(m.get('far')) and m['far']['triangles'] < m['triangles'])
hull = [s for s in m['solids'] if len(s['points']) == 8]
check('her deck is solid underfoot: a piece of hull for each section', len(hull) >= 28, len(hull))
widths = [battleship.half_beam(-battleship.HALF + s * battleship.LONG) for s in (0.0, 0.1, 0.3, 0.5, 0.9, 1.0)]
check('her lines: a sharp stem, full amidships, the stern rounded in', widths[0] < 1 and widths[1] < widths[2] <= widths[3] and widths[5] < widths[4] < widths[3], widths)
check('the deck rises to the bow', battleship.deck_z(-9000) > battleship.deck_z(0) > battleship.deck_z(9000) - 1)
one = modelmake.make({'name': 'x', 'looks': battleship._looks(), 'parts': [battleship.hull_part()]})
check('the hull alone checks too', not nifmake.check(one['nif'], one['shapes'], one['solids']))

hm = modelsets.build('mo_helm')
w = nifmake.check(hm['nif'], hm['shapes'], hm['solids'])
check('the helm (FOLab\'s own: the game has no ship\'s wheel) builds and checks', not w and hm['solids'], w[:2])
pm = modelsets.build('mo_ports')
w = nifmake.check(pm['nif'], pm['shapes'], pm['solids'])
check('the pilot house\'s ports (FOLab\'s own: sea and sky painted behind the glass) build and check', not w and pm['solids'], w[:2])
check('the helm and the ports stand on their feet: nothing under the deck, so nothing is raised into the air over it',
      hm['box'][2] == 0 and pm['box'][2] == 0, (hm['box'][2], pm['box'][2]))

# her ladders, walked on her own collision: from the level at a ladder's foot, before it, along it, onto the level at its
# top (two of them stood with their foot on the 01 level's last 20 units: no deck before them, nobody could get on)
import hkshape  # noqa: E402
_calls = []
_ladder = battleship.ladder
battleship.ladder = lambda parts, x, yf, zf, yt, zt, wide=110, x_top=None: (_calls.append((x, yf, zf, x if x_top is None else x_top, yt, zt, wide)), _ladder(parts, x, yf, zf, yt, zt, wide, x_top))[1]
battleship.missouri()
battleship.ladder = _ladder
_tris = []
for _s in hkshape.collision_shapes(m['nif']):
    for _k in range(0, len(_s['i']), 3):
        _tris.append([tuple(_s['v'][3 * _s['i'][_k + j]:3 * _s['i'][_k + j] + 3]) for j in range(3)])


def _heights(px, py):
    out = []
    for a, b_, c in _tris:
        if not (min(a[0], b_[0], c[0]) <= px <= max(a[0], b_[0], c[0]) and min(a[1], b_[1], c[1]) <= py <= max(a[1], b_[1], c[1])):
            continue
        d = (b_[1] - c[1]) * (a[0] - c[0]) + (c[0] - b_[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l1 = ((b_[1] - c[1]) * (px - c[0]) + (c[0] - b_[0]) * (py - c[1])) / d
        l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / d
        if min(l1, l2, 1 - l1 - l2) >= -1e-6:
            out.append(l1 * a[2] + l2 * b_[2] + (1 - l1 - l2) * c[2])
    return out


def _climb(x0, y0, z0, x1, y1, z1, wide):
    run = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / run, (y1 - y0) / run
    worst = 0.0
    for side in (-wide * 0.3, 0.0, wide * 0.3):
        z = None
        for k in range(-40, int(run) + 41, 8):
            hs = _heights(x0 + ux * k - uy * side, y0 + uy * k + ux * side)
            under = [h for h in hs if (abs(h - z0) < 40 if z is None else h <= z + 35)]
            if not under:
                return 'nothing underfoot %d along' % k
            nz = max(under)
            if z is not None:
                if z - nz > 40:
                    return 'a drop of %d at %d along' % (z - nz, k)
                worst = max(worst, nz - z)
            z = nz
        if abs(z - z1) > 30:
            return 'it ends at %d, not on the level at %d' % (z, z1)
    return worst


_got = [_climb(*c) for c in _calls]
check('every ladder on her is walked: deck before its foot, no step over 35 up it, onto the level at its top', len(_calls) >= 5
      and all(not isinstance(g, str) for g in _got), [(round(c[0]), round(c[1]), g) for c, g in zip(_calls, _got)])
doors = {(k, tag): e for k in shipinside.PLACES for tag, e in shipinside.layout(k).exits.items()}
deck = {('deck', 'qd'): ('second', 'qd'), ('deck', 'bridge'): ('pilot', 'out')}
back = all((d['to'] in doors and (doors[d['to']]['to'] == k)) or (d['to'] in deck and deck[d['to']] == k) for k, d in doors.items())
check('every door inside leads to one that leads back', back and len(doors) == 6, sorted(doors))

gd = gamedata.GameData()
edids = {shipinside.game_edid(t['edid']) for k in shipinside.PLACES for t in shipinside.layout(k).things if t['edid'] not in shipinside.OWN}
forms = shipinside._forms(gd, edids | {shipinside.DOOR, shipinside.DOOR_IN})
check('the game has every thing the places hold, and both doors', not (edids | {shipinside.DOOR, shipinside.DOOR_IN}) - set(forms),
      sorted((edids | {shipinside.DOOR, shipinside.DOOR_IN}) - set(forms)))
ts, _sv = shipinside.kit(gd)
for key in shipinside.PLACES:
    try:
        B = shipinside.build(gd, key)
    except ValueError as e:
        check('%s builds from the Utility kit and walks' % key, False, e)
        continue
    check('%s is built of the game\'s own kit pieces, nothing of FOLab\'s but its helm and ports' % key,
          B.pieces and shipinside.game_pieces(gd, B) == len(B.pieces) and all(k in gd.forms or gd.from_key(k) in gd.forms for k, _p, _e in B.things),
          (shipinside.game_pieces(gd, B), len(B.pieces)))
    w_ = B.walk
    check('%s walks: every square reached from the first room with its doors, lights and furniture in (but those under its machines), nothing outside' % key,
          len(w_['missing']) == B.under and all(shipinside._under(gd, B, c) for c in w_['missing']) and not w_['escaped'] and w_['reached'] > 0,
          (len(w_['missing']), B.under, len(w_['escaped'])))
    again = shipinside.kitplan.walk_check(gd, ts, B.plan, [shipinside.kitplan.Placed(k, int(round(p[5] / (math.pi / 2))) % 4, p[0], p[1], p[2], 0, (0, 0, 0)) for k, p in B.pieces])
    check('%s: its pieces alone walk again as they will be placed' % key, not again['missing'] and not again['escaped'], (len(again['missing']), len(again['escaped'])))
    check('%s: every doorway has its door, every way out its own' % key, len(B.doors) == len(shipinside.layout(key).ways) and set(B.exits) == set(shipinside.layout(key).exits))
    check('%s is lit by the kit\'s own fittings' % key, len(B.lights) >= 1, len(B.lights))
    _all = B.pieces + [(k, p) for k, p, _e in B.things] + B.lights + B.doors + [(k, p) for k, p in B.own]
    _twice = [(k, [round(v) for v in p[:3]]) for n, (k, p) in enumerate(_all) for k2, p2 in _all[n + 1:]
              if k == k2 and all(abs(p[i] - p2[i]) < 2 for i in range(3))]
    check('%s has nothing standing twice on one spot' % key, not _twice, _twice[:4])
pl = shipinside.layout('pilot')
check('the pilot house is a pilot house: three squares across, two deep, ports along its forward bulkhead, the helm behind them',
      len(pl.rooms) == 1 and len(pl.rooms[0]['cells']) == 6 and any(t['edid'] == 'ports' and t.get('side') == 's' for t in pl.things)
      and len(shipinside.build(gd, 'pilot').own) == 2, (len(pl.rooms[0]['cells']), [b for b, _p in shipinside.build(gd, 'pilot').own]))
B2 = shipinside.build(gd, 'second')
names = {shipinside.layout('second').rooms[k]['name'] for k in range(len(shipinside.layout('second').rooms))}
check('the second deck keeps the deck plan: Broadway and its eight rooms', names >= {'wardroom', 'cabin', 'sickbay', 'mess', 'galley', 'store', 'port berthing', 'starboard berthing'}
      and len(shipinside.layout('second').halls[0]) == 21, sorted(names))

# rails: nothing solid crosses the top of her gangway (the first rails' wall did, cut only where a whole section was in the gap)
g0, g1 = battleship.SPOTS['gangway_gap']
walls = [p for p in m_desc['parts'] if p.get('solid') and p['shape'] == 'box' and p.get('look') is None]
across = [p['at'] for p in walls if abs(abs(p['at'][0]) - battleship.half_beam(battleship.SPOTS['gangway_y'])) < 80
          and abs(p['at'][1] - battleship.SPOTS['gangway_y']) < p['size'][1] / 2 + 60]
check('nothing solid stands across the top of her gangway, either side', walls and not across, across)

world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
x, y = 40000.0, 0.0
SHORE = 4000.0                  # (a made-up shore in the test: sea to the west of it, land to the east)


class Coast:
    def __init__(self, *_a, **_k):
        pass

    def water(self, x_, y_):
        return 0.0

    def at(self, x_, y_):                   # (a beach: the sea bed rising to 60 over 1500, then land)
        t = (x_ - (x + SHORE - 1000)) / 1500.0
        return -900.0 if t <= 0 else 60.0 if t >= 1 else -900.0 + 960.0 * t


real_ground = shipinside.roadgen.Ground
shipinside.roadgen.Ground = Coast
pr = project.Project.create('Ship')
gd.overlay = __import__('library').Overlay(lambda: pr)        # (the mod's own files seen first, as the server has it)
ops, info = shipplace.stand(gd, pr, world, x, y, 0.0)
check('she stands: her record made, placed by it, not kept loaded (her far model and she flickered)', ops[0]['op'] == 'record_new'
      and any(o['op'] == 'add' and o['base'] == '$model_missouri' and not (o.get('extra') or {}).get('persistent') for o in ops))
check('her record is visible when distant, as the game marks its own with far models', ops[0]['record']['flags'] & modelsets.VWD)
more, rep = shipinside.board(gd, pr, world, (x, y, info['water'], 0.0))
check('her gangway goes down the side facing the land (turn 0: port, +x, is east)', rep['side'] == 'port' and rep['shore']['starboard'] is None, rep['shore'])
docks = [o for o in more if o['op'] == 'add' and o['p'][2] < 30 and abs(o['p'][1] - (y + battleship.SPOTS['gangway_y'])) < 5]
reach = max((o['p'][0] for o in docks), default=0)
check('her pier runs from the gangway to the shore and up it', rep['pier'] > 5 and reach > x + SHORE, (rep['pier'], round(reach - x)))
pr_w = project.Project.create('ShipWalk')
gd.overlay = __import__('library').Overlay(lambda: pr_w)
o_w, i_w = shipplace.stand(gd, pr_w, world, x, y, 0.0)
m_w, r_w = shipinside.board(gd, pr_w, world, (x, y, 0.0, 0.0))
pr_w.apply('w', o_w + m_w)
wk = shipinside.walk(gd, pr_w, world, r_w)
check('the walk aboard: from the shore along the pier, up the gangway to her deck, no gap, no step over 30', wk['gaps'] == 0 and wk['rise'] <= 30 and wk['samples'] > 100, wk)
gd.overlay = __import__('library').Overlay(lambda: pr)
check("a marker at the pier's land end",rep.get('marker') == shipinside.MARKER[0])
import recordio  # noqa: E402
import library  # noqa: E402
_lack = []
for _o in more:
    if _o['op'] == 'record_new' and _o['record'].get('type') == 'STAT':
        _m = recordio.field(_o['record'], 'MODL')
        if _m and not os.path.exists(os.path.join(library.assets_dir(pr), 'meshes', _m)):
            _lack.append(_m)
check('every model of FOLab\'s own the places name is among the mod\'s files', not _lack, _lack)
check('board makes her four places', len(rep['places']) == 4 and sum(1 for o in more if o['op'] == 'record_new' and o['record']['type'] == 'CELL') == 4, rep['places'])
tels = [o for o in more if o['op'] == 'tel']
check('eight doors, each linked to its other side', rep['doors'] == 8 and len(tels) == 8, rep['doors'])
check('two of them on her deck, in the world\'s cells', sum(1 for o in more if o['op'] == 'add' and str(o.get('name', '')).startswith('mo_deck_') and not str(o['cell']).startswith('$')) == 2)
pr.apply('the ship', ops + more)
names = dict(pr.names)
nav, nrep = shipinside.navmesh_ops(gd, pr, names)
got = {k: v for k, v in nrep.items() if isinstance(v, dict)}
check('each place gets a navmesh from her own model', len(nav) == 4, {k: (v if isinstance(v, str) else v['triangles']) for k, v in nrep.items()})
check('the second deck\'s reaches its rooms (hundreds of triangles), every door on a mesh', got.get('second', {}).get('triangles', 0) > 300
      and all(v['doors_missed'] == 0 for v in got.values()), {k: (v['triangles'], v['doors'], v['doors_missed']) for k, v in got.items()})
pr.apply('navmeshes', nav, merge=True)
try:
    shipinside.board(gd, pr, world, (x, y, info['water'], 0.0))
    check('boarding twice is refused', False)
except ValueError as e:
    check('boarding twice is refused', 'already' in str(e), e)
check('her lockers: none in a mod that had no old base', rep['lockers'] == 0)
check('the gangway is hers, down the side', any(o['op'] == 'record_new' and o.get('name') == 'model_mo_gangway' for o in more))
check('nothing she places is turned by a nonsense', all(0 <= o['p'][5] < math.tau + 1e-6 for o in more if o['op'] == 'add'))

# taken out and stood again: nothing of the first left behind, the same again
undo = shipplace.unboard_ops(gd, pr, world)
removed = {(o['cell'], o['ref']) for o in undo if o['op'] == 'remove'}
mine = {(ck, rk) for ck, c in pr.cells.items() for rk in c['refs'] if rk.startswith('+')}
check('taking her out takes all that board and stand put in (her places, doors, gangway, pier, marker, lights)',
      mine <= removed | {(ck, rk) for ck, rk in mine if ck.startswith('+') and ck not in names.values()}, len(mine - removed))
redo, rrep = shipplace.restand(gd, pr, world)
check('stood again: her places again, the same pier', len(rrep['aboard']['places']) == 4 and rrep['aboard']['pier'] == rep['pier'], rrep['aboard'].get('pier'))
pr.apply('again', redo)
check('after it, one Missouri, one gangway, four places', sum(1 for c in pr.cells.values() for r in c['refs'].values() if r.get('base') == modelsets.record_of(pr, 'missouri')) == 1
      and sum(1 for c in pr.cells.values() for r in c['refs'].values() if r.get('base') == modelsets.record_of(pr, 'mo_gangway')) == 1
      and sum(1 for r in pr.records.values() if r.get('type') == 'CELL') == 4)

# with no shore within reach of either side she isn't boarded by a gangway into the sea: it says so
SHORE = 1e9
pr2 = project.Project.create('Ship2')
o2, i2 = shipplace.stand(gd, pr2, world, x, y, 0.0)
try:
    shipinside.board(gd, pr2, world, (x, y, 0.0, 0.0))
    check('no shore: refused, not a gangway into the sea', False)
except ValueError as e:
    check('no shore: refused, not a gangway into the sea', 'No shore' in str(e), e)
shipinside.roadgen.Ground = real_ground

# every piece with a far model is visible when distant; distant_ops marks records made before
recs = modelsets.distant_ops(pr)
check('distant_ops has nothing to do where put made the records', recs == [], len(recs))
