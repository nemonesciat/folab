"""Nobody stands inside a building (indoors.py; 22 Nov 2026: seven people stood in the closed Royal Hawaiian's lobby).
A game building of the catalogue and a FOLab closed piece by the mod's record count, turned with their ref, grown by
MARGIN; an open piece (the hale) doesn't; a removed building or one swapped for a crate is gone; a spot on the roof is on
it, not in it; waikikilife.Spots (which activity, factionfolk and waikikilife pick through) and worldlife.Life refuse a spot
inside; everyone_inside lists an actor standing in one."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import indoors  # noqa: E402
import modelsets  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402
import townbuild  # noqa: E402
import waikikilife  # noqa: E402
import worldlife  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()


def key_of(edid, tag):
    return gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid))


world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
G = roadgen.Ground(gd, None, world)
# (a cell of high dry ground, flat enough for Spots, with nothing of the game's in it that counts as a building)
pr0 = project.Project.create('indoors probe')
saloon = key_of('NVProspectorSaloon', 'STAT')
box = townbuild.obnd(gd, saloon)
cat = [{'key': saloon, 'box': box}]
xy = None
for (cx, cy), c in sorted(grid.items(), key=lambda kv: (abs(kv[0][0] + 10), abs(kv[0][1] - 5))):
    mx, my = (cx + 0.5) * 4096, (cy + 0.5) * 4096
    hs = [G.at(mx + dx, my + dy) for dx in (-1200, 0, 1200) for dy in (-1200, 0, 1200)]
    if None in hs or min(hs) < 200 or max(hs) - min(hs) > 40:
        continue
    if indoors.Buildings(gd, pr0, world, cat).inside(mx, my):
        continue
    xy = (cx, cy)
    break
check('a flat dry cell to test on', xy is not None, xy)
cx, cy = xy
ck = gd.key(grid[xy])
mx, my = (cx + 0.5) * 4096, (cy + 0.5) * 4096
gz = G.at(mx, my)
rz = math.radians(30)

pr = project.Project.create('indoors test')
modelsets._all_sets()
royal = modelsets.PIECES['royal_hawaiian']['edid']
hale = modelsets.PIECES['hale']['edid']


def stat(edid, b):
    return {'type': 'STAT', 'subs': [{'tag': 'EDID', 'kind': 'z', 'value': edid},
                                     {'tag': 'OBND', 'kind': 'struct', 'fields': [{'name': n, 'value': v} for n, v in zip(('x1', 'y1', 'z1', 'x2', 'y2', 'z2'), b)]}]}


pr.records['+000900'] = stat(royal, [-400, -300, -16, 400, 300, 900])
pr.records['+000901'] = stat(hale, [-250, -200, 0, 250, 200, 400])
crate = key_of('CrateLarge01', 'STAT')
npc = key_of('NVProspectorMale', 'NPC_')
pr.cells[ck] = {'refs': {
    '+000100': {'base': saloon, 'p': [mx, my, gz, 0, 0, rz]},                   # (the game's building, turned)
    '+000101': {'base': '+000900', 'p': [mx + 1600, my, gz, 0, 0, 0], 's': 1.5},  # (FOLab's closed hotel, scaled)
    '+000102': {'base': '+000901', 'p': [mx - 1600, my, gz, 0, 0, 0]},          # (an open hale)
    '+000103': {'base': saloon, 'p': [mx, my + 1600, gz, 0, 0, 0], 'removed': True},
    '+000104': {'base': crate, 'p': [mx, my - 1600, gz, 0, 0, 0]},              # (swapped for a crate: no building)
    '+000110': {'base': npc, 'p': [mx + 1600 + 100, my + 50, gz, 0, 0, 0]},      # (someone in the hotel)
    '+000111': {'base': npc, 'p': [mx + 1600, my + 300 * 1.5 + 200, gz, 0, 0, 0]},  # (someone out in front of it)
}}
B = indoors.Buildings(gd, pr, world, cat)


def local(lx, ly):
    """A point in the saloon's own frame, in the world (the game's turn: clockwise from above)."""
    return mx + lx * math.cos(rz) + ly * math.sin(rz), my - lx * math.sin(rz) + ly * math.cos(rz)


inner = (box[0] + box[3]) / 2, (box[1] + box[4]) / 2
check('in the middle of a game building', B.at(*local(*inner)) == ('+000100', 'NVProspectorSaloon'), B.at(*local(*inner)))
corner = local(box[3] - 10, box[4] - 10)
check('in its far corner, turned with it', B.inside(*corner))
check('past its box: outside', not B.inside(*local(box[3] + indoors.MARGIN + 20, inner[1])))


# outlines from walls: a room 800 square with a doorway 160 wide, and three walls round a courtyard open on one side
def wall(p, q, top=400.0):
    a, b = (p[0], p[1], 0.0), (q[0], q[1], 0.0)
    return [(a, b, (q[0], q[1], top)), (a, (q[0], q[1], top), (p[0], p[1], top))]


room = wall((0, 0), (320, 0)) + wall((480, 0), (800, 0)) + wall((800, 0), (800, 800)) + wall((800, 800), (0, 800)) + wall((0, 800), (0, 0))
R = indoors.Outline([0, 0, 0, 800, 800, 400], room)
check('a room\'s middle is inside', R.hit(400, 400))
check('the inner half of its doorway is inside', R.hit(400, 60))
check('within MARGIN out from a wall: in the wall', R.hit(400, 800 + indoors.MARGIN - 5))
check('past MARGIN and the grid: outside', not R.hit(400, 800 + indoors.MARGIN + indoors.STEP + 5))
yard = wall((0, 0), (0, 2000)) + wall((0, 2000), (2000, 2000)) + wall((2000, 2000), (2000, 0))
Y = indoors.Outline([0, 0, 0, 2000, 2000, 400], yard)
check('a courtyard open on one side stays out', not Y.hit(1000, 1000) and Y.hit(1000, 2000))
check('a model with no collision read is its box', indoors.Outline([0, 0, 0, 100, 100, 50], []).hit(50, 50))
low = wall((0, 0), (800, 0), top=60) + wall((800, 0), (800, 800), top=60)
check('walls under SLICES (a kerb, a planter) are no building', indoors.Outline([0, 0, 0, 800, 800, 60], low).cells is None)
check('on its roof is not in it', not B.inside(*local(*inner), z=gz + box[5]))
check('at its floor is in it', B.inside(*local(*inner), z=gz + 10))
check('FOLab\'s closed hotel by the mod\'s record, scaled', B.at(mx + 1600 + 590, my + 440) == ('+000101', royal), B.at(mx + 1600 + 590, my + 440))
check('outside the scaled hotel', not B.inside(mx + 1600 + 700, my))
check('an open piece (the hale) is not a building', not B.inside(mx - 1600, my))
check('a removed building is gone', not B.inside(mx, my + 1600))
check('a building swapped for a crate is gone', not B.inside(mx, my - 1600))
check('a building in the next cell reaches over', B.inside(mx + 1600 + 590, my) and indoors.Buildings(gd, pr, world, cat).inside(mx + 1600 + 590, my))
check('every CLOSED piece is one of the sets\' pieces', all(p in modelsets.PIECES for p in indoors.CLOSED),
      [p for p in indoors.CLOSED if p not in modelsets.PIECES])
check('the hotels\' open pieces are not CLOSED', not any(p.endswith('_open') for p in indoors.CLOSED))

# the pickers
sp = waikikilife.Spots(gd, pr, world)
sp._B = B
check('Spots refuses a spot inside', sp.stand(*local(*inner), apart=0) is None)
check('Spots refuses a spot inside FOLab\'s hotel', sp.stand(mx + 1600 + 100, my, apart=0) is None)
out_spot = local(box[3] + 400, inner[1])
free = waikikilife.Spots(gd, pr, world)
free._B = type('Nowhere', (), {'inside': lambda *_a, **_k: False})()
outs = [local(box[3] + d, inner[1]) for d in (300, 600, 900)] + [(mx + 1600 + 900, my), (mx, my - 900)]
check('outside a building, Spots answers as it did without the check', all((sp.stand(*q, apart=0) is None) == (free.stand(*q, apart=0) is None) for q in outs))
L = worldlife.Life(gd, pr, world, (mx - 30000, my - 30000), 1)
L._B = B
crea = next(gd.edid(f) for f, (_i, r) in gd.forms.items() if r.tag == 'CREA' and gd.edid(f))
check('worldlife stands nobody inside', L.stand([(crea, 1)], *local(*inner)) == 0)
check('worldlife stands someone outside', L.stand([(crea, 1)], *out_spot) == 1)
# who is inside now
got = indoors.everyone_inside(gd, pr, world, cat, B=B)
mine = [g for g in got if g[1].startswith('+')]
check('everyone_inside finds the one in the hotel', [g[1] for g in mine] == ['+000110'], got)
check('and says which building', mine and mine[0][4] == ('+000101', royal), got)
check("the game's snipers in its guard towers are not inside a building", not any('Sniper' in g[2] for g in got), got)
check("the game's own placements are read too (Easy Pete on the saloon's porch: a footprint takes in porches)",
      any(g[2] == 'GSEasyPete' for g in got), got)
