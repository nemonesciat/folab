"""understory: the ground's own texture says where plants could grow (never pavement, asphalt, gravel or water), the
texture on top is the one drawn, and a clump counts at once so bare ground is filled only until nothing is far from a plant.
After 18 Nov 2026: valley floors and road verges on Waikiki bare between the dressing's clumps."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import understory  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


# ---------- the ground by its texture ----------
want = {'Pavement': None, 'LAsphaltWasteland01': None, 'LWaterGravelSandNV01': None, 'LWaterSandNV01': 'sand',
        'LWaterMossNV01': 'wet', 'LGrassGolfNoneNV': 'lawn', 'LGrassGreenSuburbsNoGrass': 'lawn', 'LGrassGreenFarmlandsNV': 'lawn',
        'LRockCanyonRubble01': 'rock', 'FOLabGrassLRockCanyonRubble01': 'rock', 'LRockCanyonRubbleDirt01': 'dirt',
        'LScrubDirtStripGreenNV01': 'dirt', 'FOLabGrassScrubBarrenWastes01Sage': 'dirt', 'FOLabGrassLScrubDirtStripGreenNV01Grass': 'dirt'}
got = {e: understory.class_of(e) for e in want}
check('every texture of Waikiki in its class', got == want, {e: (got[e], want[e]) for e in want if got[e] != want[e]})

# ---------- the texture drawn on top ----------
a = [0.0] * 289
full = [1.0] * 289
half = [0.5] * 289
q = {'bkey': 'BASE', 'layers': [{'key': 'L1', 'a': full}, {'key': 'L2', 'a': a}]}
check('a full layer over the base is what shows', understory._top(q, 3, 3) == 'L1')
q = {'bkey': 'BASE', 'layers': [{'key': 'L1', 'a': half}, {'key': 'L2', 'a': [0.6] * 289}]}
check('the last layer wins where it is strongest', understory._top(q, 0, 0) == 'L2')
q = {'bkey': 'BASE', 'layers': [{'key': 'L1', 'a': [0.1] * 289}]}
check('a faint layer leaves the base showing', understory._top(q, 0, 0) == 'BASE')

# ---------- nearness ----------
g = understory._Grid()
g.add(1000.0, 1000.0)
check('a plant within reach counts', g.near(1300.0, 1000.0, 384.0))
check('one past it does not', not g.near(1400.0, 1000.0, 384.0))
check('across a square edge too', g.near(1000.0, 1020.0 + 511.0 - 200.0, 384.0))

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
