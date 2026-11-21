"""FOLab's own road and rubble (rubbleset.py, rubbleswap.py): each piece is one shape over one picture sheet and reads back
as built, collision one closed solid; a road piece keeps the game slab's frame (top at the origin, the game's length and
width within its verge) and every edge of it goes down past the game slab's sides; a heap seated on a slope has its rim
at or under the ground all round and its skirt's tips under it, never buried past BURY_MOST; the swap makes one STAT a
piece, swaps only the mod's own things, seats heaps and leaves roads where they lie; roadbed knows the own road pieces."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import roadbed  # noqa: E402
import rubbleset  # noqa: E402
import rubbleswap  # noqa: E402

bad = 0


def check(what, ok, detail=''):
    global bad
    bad += not ok
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


for piece in rubbleset._P:
    made = modelsets.build(piece)
    data = made['files'][made['mesh']]
    back = nif.mesh_from_nif(data)
    check(piece + ': one shape', len(back) == 1, len(back))
    check(piece + ': reads back as built, collision closed', not nifmake.check(data, made['shapes'], made['solids']),
          nifmake.check(data, made['shapes'], made['solids']))
    check(piece + ': one picture sheet', len({t for t in made['textures'] if not t.endswith('_n.dds')}) == 1, made['textures'])
    # (the cost that counts on Waikiki is draws, one a piece; a heap's chunks and lumps are ~1,300 triangles, the game's RubblePile02 five draws)
    check(piece + ': fewer than 1,600 triangles', made['triangles'] < 1600, made['triangles'])
    if rubbleset.is_road(piece):
        b = made['box']
        check(piece + ': top at the origin, crown as the game\'s', 8 <= b[5] <= 14, b)
        check(piece + ': its edges go deeper than the game slab\'s sides', b[2] <= -40, b)
        # (a far model beside it, or lodobj leaves the roads out of the far view)
        lod = made['mesh'][:-4] + '_lod.nif'
        far = nif.mesh_from_nif(made['files'][lod]) if lod in made['files'] else []
        check(piece + ': a far model of one shape, a few triangles', len(far) == 1 and len(far[0]['i']) // 3 <= 16,
              [len(s['i']) // 3 for s in far])
        check(piece + ': ...on the road\'s own picture', far and far[0]['tex'].lower().endswith('rubble\\road.dds'), far and far[0]['tex'])

# roads: every point of the surface past the asphalt is under its edge, falling outward
for y in (rubbleset.ASPHALT + 5, rubbleset.VERGE, rubbleset.DEEP):
    check('road falls away at %d' % y, rubbleset.across(y) < 0 and rubbleset.across(y + 1) <= rubbleset.across(y))


class Slope:
    @staticmethod
    def at(x, y):
        return 0.3 * y + 0.1 * x + 25 * math.sin(x / 300.0)


for piece in ('heap_a', 'heap_low_b', 'edging', 'slab'):
    for yaw in (0.0, 1.3, 2.9):
        p = rubbleswap.seat_one(Slope, [500.0, -300.0, 0.0, 0.0, 0.0, yaw], 0.8, piece)
        hang, over, bury = rubbleswap.lies(Slope, p, 0.8, piece)
        check('%s seated on a slope (turn %.1f): skirt under the ground, not buried past %.2f' % (piece, yaw, rubbleswap.BURY_MOST),
              hang <= 0 and bury <= rubbleswap.BURY_MOST + 0.01, (round(hang, 1), round(over, 1), round(bury, 2)))

# the swap on a mod
gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
xy, cell = next(iter(grid.items()))
ck = gd.key(cell)
key = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) in ('RubblePile02', 'WastelandRoadStraightLongB')}
x0, y0 = xy[0] * 4096 + 2048, xy[1] * 4096 + 2048
pr = project.Project.create('rubbleset test')
pr.cells[ck] = {'refs': {'+000100': {'base': key['RubblePile02'], 'p': [x0, y0, 0, 0, 0, 0]},
                         '+000101': {'base': key['RubblePile02'], 'p': [x0 + 900, y0, 0, 0, 0, 0.5]},
                         '+000102': {'base': key['WastelandRoadStraightLongB'], 'p': [x0, y0 + 900, 5000, 0, 0, 0]},
                         '00ABCDEF:FalloutNV.esm': {'base': key['RubblePile02'], 'p': [x0, y0 - 900, 0, 0, 0, 0]}}}
o, rep = rubbleswap.ops(gd, pr, world)
check('a STAT for each piece used', sum(1 for x in o if x['op'] == 'record_new') == len(rep['made']) and rep['made'], rep['made'])
check('only the mod\'s own swapped', rep['swapped'] == {'RubblePile02': 2, 'WastelandRoadStraightLongB': 1}, rep['swapped'])
check('heaps seated, the road left where it lies', rep['seated'] == 2 and not any(x['op'] == 'move' and x['ref'] == '+000102' for x in o), rep)
pr.apply('rubble', o)
refs = pr.cells[ck]['refs']
mine = rubbleswap.pieces_of(pr)
check('neighbours get different heaps', mine[refs['+000100']['base']] != mine[refs['+000101']['base']],
      (mine[refs['+000100']['base']], mine[refs['+000101']['base']]))
check('roadbed knows the own road piece', refs['+000102']['base'] in roadbed._flat_bases(gd, pr))
check('...and its box is the game slab\'s', roadbed._flat_bases(gd, pr)[refs['+000102']['base']] == roadbed._flat_bases(gd)[key['WastelandRoadStraightLongB']])
o2, _r2 = rubbleswap.ops(gd, pr, world)
check('a second run changes nothing', not o2, len(o2))
names = {recordio.field(pr.records[k], 'EDID') for k in mine}
check('records named FOLab...', all(n.startswith('FOLab') for n in names), names)
print('%d failed' % bad)
