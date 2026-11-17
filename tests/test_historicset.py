"""Waikiki's historic buildings (historicset): the Royal Hawaiian, the Moana, the Natatorium and Battery Randolph each
build and check, are about the size of the game's buildings that stood in for them, have a far model and their own
worn pictures (the see-through arches really see-through), and landmarks stands each as a set: the mod gets its files
and a STAT of its own, with its lights, and what comes after keeps off it."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import historicset  # noqa: E402
import landmarks  # noqa: E402
import modelmake  # noqa: E402
import modelsets  # noqa: E402
import nifmake  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


# (what each is like: width, depth and height at least and at most)
SIZES = {'royal_hawaiian': ((3800, 2600, 2400), (5500, 4000, 3600)), 'moana': ((3800, 2600, 1300), (5500, 4600, 2600)),
         'natatorium': ((3400, 1800, 900), (5000, 3500, 2000)), 'battery_randolph': ((3800, 2200, 500), (5500, 4000, 1600))}
made = {}
for piece, (lo, hi) in SIZES.items():
    m = made[piece] = modelsets.build(piece)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    check('%s builds, every block checked, under MOST_BUILDING triangles' % piece, not wrong and m['triangles'] < modelmake.MOST_BUILDING, (m['triangles'], wrong[:2]))
    b = m['box']
    size = (b[3] - b[0], b[4] - b[1], b[5])
    check('%s is the size it should be' % piece, all(lo[k] <= size[k] <= hi[k] for k in range(3)), size)
    check('%s has a far model, lighter than itself' % piece, bool(m.get('far')) and m['far']['triangles'] < m['triangles'] / 2, m.get('far', {}).get('triangles'))
    own = [t for t in m['textures'] if '\\hist\\' in t]
    check('%s: its own worn pictures go with it' % piece, len(own) >= 6 and all(t in m['files'] for t in m['textures']), len(own))
    check('%s: its lights are known' % piece, len(__import__('waikikiset').LIGHTS.get(piece, ())) >= 1)

# (the arches: open where an arch is, solid where the board is)
pic = historicset.arch_board(*historicset.RH_LOGGIA, w=256, h=64, seed=1)
n, W, H, pier = historicset.RH_LOGGIA
mid = int((0.5 * W / n) / W * 256) + 64 * 256 - 256 * 2
check('an arch is open at its foot and the board shut over it', pic.a[63 * 256 + int(0.5 / n * 256)] == 0.0 and pic.a[0] == 1.0)
rail = historicset.balustrade(64, seed=2)
check('a balustrade is see-through between its balusters', 0 < sum(rail.a) < 64 * 64)
check('the same picture from the same seed', historicset.period_sheet(size=64, bays=2, floors=2, seed=5).rgb == historicset.period_sheet(size=64, bays=2, floors=2, seed=5).rgb)
check('the battery\'s guns point out to sea (to -y)', min(made['battery_randolph']['box'][1], 0) < -2000)

gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
g0 = roadgen.Ground(gd, None, world)


def flat(k):
    hs = [h for dx in (-1, 0, 1) for dy in (-1, 0, 1) for h in (g0.cell((k[0] + dx, k[1] + dy)) or [None])]
    return None not in hs and max(hs) - min(hs) < 700 and min(hs) > 2000


xy = next(k for k in sorted(grid) if flat(k))
x, y = xy[0] * 4096.0 + 2048, xy[1] * 4096.0 + 2048
pr = project.Project.create('Historic')
B = landmarks.Batch(gd, pr, world)
reps = {}
for k, piece in enumerate(SIZES):
    reps[piece] = B.stand(piece, x + k * 9000, y, turn=0.0, nudge=0)
ops = B.done()
check('each stands as a landmark set', all(reps[p] and reps[p]['label'] == landmarks.SETS[p]['label'] for p in SIZES), reps)
check('their records are made first, each placed by its own', all(any(o['op'] == 'add' and o['base'] == '$model_' + p for o in ops) for p in SIZES)
      and all(o['op'] == 'record_new' for o in ops[:len(SIZES)]))
check('with their lights', sum(1 for o in ops if o['op'] == 'add' and not o['base'].startswith('$model_')) >= 7)
pr.apply('landmark', ops)
assets = __import__('library').assets_dir(pr)
check('the mod has a STAT of its own for each, and its files', all(modelsets.record_of(pr, p) and pr.records[modelsets.record_of(pr, p)]['type'] == 'STAT'
                                                                   and os.path.isfile(os.path.join(assets, 'meshes', 'folab', 'resort', p + '.nif')) for p in SIZES))
keep = landmarks.standing(gd, pr, world)
check('what comes after keeps off each', all(any(math.hypot(k[0] - reps[p]['x'], k[1] - reps[p]['y']) < 1 for k in keep) for p in SIZES), len(keep))
