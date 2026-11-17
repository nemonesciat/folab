"""A ship out of Fallout 3 (othergame.py): the carrier read as that game stands it, its files copied into the mod's own,
a static of the mod's for each model, the set stood in the sea; and the files taken out again. Then the way aboard
(aboard.py): a pier to walk from the shore to a door in the hull, a base behind it, a door up to the flight deck, a
marker. Needs Fallout 3 in a Steam library: without it there is nothing to test, and the test says so and passes."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import library  # noqa: E402
import othergame  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


where = othergame.find('carrier')
check('a game still being installed is not one to read', 'downloading' not in (where or '').lower())
if not where:
    print('PASS Fallout 3 is not installed here: nothing more to check')
    sys.exit(0)
other = othergame.open_game('carrier')
got = othergame.lift(other, 'carrier')
names = [p[0] for p in got['pieces']]
check('the carrier is its hull, its two ends and its tower', {'RCExtAirCarrier01', 'RCExtAirCarrierBack', 'RCExAirCarrierFront', 'RCAirCarrierTower'} <= set(names), sorted(set(names)))
check('without the bridge to a shore that isn\'t here', not any('Bridge' in n for n in names))
box = got['box']
check('it lies along its length, as long as a carrier', 18000 < box[2] - box[0] < 30000 and box[3] - box[1] < (box[2] - box[0]) * 0.4, [round(v) for v in box])
hull = next(p for p in got['pieces'] if p[0] == 'RCExtAirCarrier01')
check('and floats: its hull\'s origin over the water, its keel well under', 500 < hull[4] < 2000 and got['draught'] > 500, (hull[4], got['draught']))

gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
pr = project.Project.create('Ship')
gd.overlay = library.Overlay(lambda: pr)
k = next(k for k in sorted(grid))
x, y = k[0] * 4096.0 + 2048, k[1] * 4096.0 + 2048
ops, rep = othergame.stand(gd, pr, world, 'carrier', x, y, 0.5, other)
root = library.assets_dir(pr)
mine = othergame.borrowed(pr).get('Fallout 3', [])
check('its models and textures are copied into the mod\'s own files', rep['copied'] == len(mine) >= 20 and all(os.path.isfile(os.path.join(root, r)) for r in mine), (rep['copied'], rep['files']))
check('meshes, far models and textures with their normal maps', any(r.endswith('_lod.nif') for r in mine) and any(r.endswith('_n.dds') for r in mine)
      and any(r.endswith('rcextaircarrier01.nif') for r in mine))
check('nothing New Vegas has under the same name', not any(r in a.files for r in mine for a in gd.archives()))
made = [o for o in ops if o['op'] == 'record_new']
adds = [o for o in ops if o['op'] == 'add']
check('a static of the mod\'s own for each model, every piece placed of one', len(made) == rep['kinds'] and len(adds) == rep['pieces'] == len(got['pieces'])
      and all(o['base'].startswith('$og_') for o in adds), (len(made), len(adds)))
pr.apply('ship', ops)
refs = [r for c in pr.cells.values() for r in c['refs'].values()]
check('placed, each names the record made for it', len(refs) == len(adds) and all(r['base'] in pr.records for r in refs), sorted({r['base'] for r in refs})[:3])
rec = pr.records[next(r['base'] for r in refs if abs(r['p'][0] - x) + abs(r['p'][1] - y) < 3000)]
check('the record is a static with the model and its bounds', rec['type'] == 'STAT' and recordio.field(rec, 'MODL').lower().startswith('dungeons\\rivetcity\\exterior\\')
      and recordio.field(rec, 'EDID').startswith('FOLab'), recordio.field(rec, 'EDID'))
h = next(r for r in refs if recordio.field(pr.records[r['base']], 'EDID') == 'FOLabRCExtAirCarrier01')
tx, ty = hull[2] * math.cos(0.5) + hull[3] * math.sin(0.5), -hull[2] * math.sin(0.5) + hull[3] * math.cos(0.5)
check('the set is turned about its middle as one', abs(h['p'][0] - (x + tx)) < 1 and abs(h['p'][1] - (y + ty)) < 1 and abs((h['p'][5] - hull[7] - 0.5) % math.tau) < 0.001)
ops2, rep2 = othergame.stand(gd, pr, world, 'carrier', x + 30000, y, 0.0, other)
check('stood again, the same records and files serve', not any(o['op'] == 'record_new' for o in ops2) and rep2['copied'] == 0)
n = othergame.remove_borrowed(pr)
check('the other game\'s files come out again, all of them', n == len(mine) and not any(os.path.isfile(os.path.join(root, r)) for r in mine) and not othergame.borrowed(pr))

# a place for it: over deep water, clear of the land
ground = roadgen.Ground(gd, None, world)


class Flat:
    """A made-up sea: land east of x = 0, deep water west of it."""
    def __init__(self):
        self.grid = {(i, j): 1 for i in range(-20, 20) for j in range(-20, 20)}

    def at(self, px, py):
        return 64.0 if px > 0 else -600.0


real = roadgen.Ground
roadgen.Ground = lambda *a: Flat()
gd2 = type('G', (), {'grid': lambda self, w: Flat().grid})()
try:
    at = othergame.where(gd2, None, None, got, (2000.0, 0.0))
finally:
    roadgen.Ground = real
far = [at[0] + px * math.cos(at[2]) + py * math.sin(at[2]) for px in (box[0], box[2]) for py in (box[1], box[3])] if at else []
check('found off the shore, all of it over the water and clear of the land', at is not None and max(far) < -othergame.OFF_SHORE + 1, (at, far and round(max(far))))


# ---------- a way aboard and a base (aboard.py): the ship in a made-up sea, the shore to its north ----------
import aboard  # noqa: E402

mid = min(grid, key=lambda k: abs(k[0]) + abs(k[1]))
sx, sy = mid[0] * 4096.0 + 2048, mid[1] * 4096.0 + 2048


class Sea:
    """Deep water, and land from `shore` north of the ship's middle."""
    shore = 4300.0

    def at(self, px, py):
        return 30.0 if py > sy + self.shore else -600.0

    def water(self, px, py):
        return 0.0


empty = project.Project.create('NoShip')
try:
    aboard.board(gd, empty, world)
    said = ''
except aboard.NoWay as e:
    said = str(e)
check('a mod with no ship in it has nothing to board, and says so', 'no ship' in said, said)
pr = project.Project.create('Aboard')          # (the overlay follows `pr`: the ship's files are read from this mod's own)
roadgen.Ground = lambda g, *a: Sea() if g is gd else real(g, *a)       # (the other game keeps its own water: the ship is read floating in it)
try:
    ops, _rep = othergame.stand(gd, pr, world, 'carrier', sx, sy, 0.0, other)
    pr.apply('ship', ops)
    before = (len(pr.records), sum(len(c['refs']) for c in pr.cells.values()))
    ops, rep = aboard.board(gd, pr, world)
    pr.apply('aboard', ops)
    names = dict(pr.names)
    nav = aboard.navmesh_ops(gd, pr, rep, names)
    pr.apply('aboard', nav, merge=True)
    walk = aboard.way(gd, pr, world, rep)
    try:
        aboard.board(gd, pr, world)
        twice = ''
    except aboard.NoWay as e:
        twice = str(e)
    got_ship = aboard.ship(pr)
    place = names['ship']
    inside = pr.cells[place]['refs']
    outside = {k: r for ck, c in pr.cells.items() if ck != place for k, r in c['refs'].items()}
    ref = dict(outside, **inside)
    out_door, exit_door, up_door = ref[names['shipo']], ref[names['shipx']], ref[names['shipu']]
    wall_y = rep['wall'][1]
    check('the pier runs from the hull to the land: planking all the way, level, clear of the water',
          rep['pier'] >= 4 and walk['wall'] <= 2 and walk['step'] <= 8 and walk['low'] >= 20 and walk['ashore'] >= 20, (rep['pier'], rep['far'], walk))
    check('it meets the hull at its side, on the side the shore is', sy + 1500 < wall_y < sy + Sea.shore and abs(rep['far'] - (sy + Sea.shore - wall_y)) < 70, (rep['wall'], rep['far']))
    frame = aboard._own(pr, 'FOLabRCRmLgDoorFrameExt01', 'STAT')
    check("a door in one of the ship's own frames stands there, at the planking's height",
          abs(out_door['p'][2] - rep['deck']) < 1 and any(r['base'] == frame and math.dist(r['p'][:3], out_door['p'][:3]) < 10 for r in outside.values()), out_door['p'][:3])
    check("it leads into the base and the base's way out leads back, arriving on the pier a step from the hull",
          out_door['tel']['door'] == names['shipx'] and exit_door['tel']['door'] == names['shipo'] and names['shipx'] in inside
          and 60 < exit_door['tel']['p'][1] - wall_y < 200 and 0 < exit_door['tel']['p'][2] - rep['deck'] <= 16, exit_door['tel']['p'])
    cell = pr.records[place]
    check("the base is a place of the mod's own, nobody's", cell['type'] == 'CELL' and recordio.field(cell, 'EDID') == 'FOLabShipHangar'
          and not any(s['tag'] in ('XOWN', 'XRNK') for s in cell['subs']) and len(inside) > 300, len(inside))

    def what(r):
        b = r['base']
        return (pr.records[b]['type'], recordio.field(pr.records[b], 'EDID')) if b in pr.records else (gd.forms[gd.from_key(b)][1].tag, gd.edid(gd.from_key(b)))
    kinds = [what(r) for r in inside.values()]
    check('nobody lives in it', not any(t in ('NPC_', 'CREA') for t, _e in kinds))
    check('a bed to sleep in, a workbench and a reloading bench', any(t == 'FURN' and 'bed' in e.lower() for t, e in kinds) and ('ACTI', 'WorkBench') in kinds
          and ('ACTI', 'ReloadingBench') in kinds and rep['beds'] >= 1, rep['benches'])
    safe = [pr.records[r['base']] for r in inside.values() if r['base'] in pr.records and pr.records[r['base']]['type'] == 'CONT']
    flags = [f['value'] for rec in safe for s in rec['subs'] if s['tag'] == 'DATA' for f in s['fields'] if f['name'] == 'Flags']
    check("lockers of the mod's own by the beds: empty, never refilled, named as yours", len(safe) == rep['safe'] >= 2
          and not any(s['tag'] in ('CNTO', 'SCRI') for rec in safe for s in rec['subs']) and not any(f & 2 for f in flags)
          and all(recordio.field(rec, 'FULL').startswith('Your ') for rec in safe), sorted({recordio.field(rec, 'EDID') for rec in safe}))
    back = inside[up_door['tel']['door']]
    under = aboard.footing(gd, got_ship, *back['tel']['p'][:3])
    hull_z = got_ship['RCExtAirCarrier01'][0][0][2]
    check('a second door leads up to the flight deck and back, not locked', back['tel']['door'] == names['shipu'] and 'props' not in back and 'props' not in up_door
          and up_door['p'][2] > hull_z + 700, up_door['p'][:3])
    check("up there one arrives on the deck itself: the ship's collision just underfoot", under is not None and 0 <= back['tel']['p'][2] - under <= 16, (back['tel']['p'][:3], under))
    locked = [r for r in outside.values() if (r.get('props') or {}).get('lock') and not r['base'].startswith('+') and gd.edid(gd.from_key(r['base'])) == 'RCSmDoor01']
    check("the ship's other frames have a locked door in them", len(locked) == rep['locked'] == len(got_ship['RCRmLgDoorFrameExt01']) - 2,
          (len(locked), rep['locked']))         # (all but the deck door's and the new one on the hull)
    marks = [r for r in outside.values() if (r.get('marker') or {}).get('name') == 'Aircraft Carrier']
    check("a marker on the map at the pier's land end, to travel to", len(marks) == 1 and marks[0]['marker']['flags'] & 2 and marks[0].get('persistent')
          and marks[0]['p'][1] > sy + Sea.shore - 300 and marks[0]['p'][2] > rep['deck'], marks and marks[0]['p'][:3])
    mesh = pr.navmesh.get(place) or {}
    check('the base has a navmesh, its doors named in it', len(mesh.get('tris', [])) > 100 and {d[0] for d in mesh.get('doors', [])} >= {names['shipx'], up_door['tel']['door']},
          (rep.get('navmesh'), len(mesh.get('tris', []))))
    check('asked again, it says the ship has its way aboard already', 'already' in twice, twice)
    pr.undo()
    check('one Undo takes all of it out again', (len(pr.records), sum(len(c['refs']) for c in pr.cells.values())) == before and place not in pr.navmesh
          and not aboard._own(pr, 'FOLabShipHangar', 'CELL'))
    Sea.shore = 2400.0 + aboard.PIER_MOST + 600
    try:
        aboard.board(gd, pr, world)
        far = ''
    except aboard.NoWay as e:
        far = str(e)
    check('a ship too far out for a pier is left alone, with the reason', 'too far' in far, far)
finally:
    roadgen.Ground = real
    othergame.remove_borrowed(pr)
