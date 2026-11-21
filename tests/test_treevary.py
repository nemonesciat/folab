"""No two neighbouring trees alike (treevary.py): every jungle tree's far model spans what its near leaves span (no change
of shape as its cell loads), the variants keep the trunk as thick, a spot always gives the same variant and a grove gets
all three, and the ops on a mod make the variants' records and swap only the mod's own trees."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import modelsets as ms  # noqa: E402
import project  # noqa: E402
import treevary  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


ms._all_sets()
got = treevary.matches()
check('every far tree matches its near tree', all(ok for ok, _n in got.values()), {p: n for p, (ok, n) in got.items() if not ok})
check('nine trees checked', len(got) == 9, len(got))
for kind, kinds in treevary.VARIANTS.items():
    check(kind + ': its variants are pieces of the set', all(p in ms.PIECES for p in kinds))
spots = [(x * 700.0, y * 900.0) for x in range(12) for y in range(12)]
kinds = treevary.VARIANTS['jungle_tree']
picked = [treevary.which(kinds, x, y) for x, y in spots]
check('a spot always gives the same', picked == [treevary.which(kinds, x, y) for x, y in spots])
check('a grove gets all three, none much more than the others', all(picked.count(k) > len(spots) / 5 for k in kinds),
      {k: picked.count(k) for k in kinds})
gd = gamedata.GameData()
pr = project.Project.create('treevary test')
o, _i = ms.put(pr, 'jungle_tree')
pr.apply('a tree', o)
tree = ms.record_of(pr, 'jungle_tree')
cell = gd.key(next(iter(gd.grid(next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')).values())))
pr.cells[cell] = {'refs': {'+%06X' % (0x100 + n): {'base': tree, 'p': [x, y, 0, 0, 0, 0], 's': 1.0} for n, (x, y) in enumerate(spots[:30])}}
pr.cells[cell]['refs']['00ABCDEF:FalloutNV.esm'] = {'base': tree, 'p': [5, 5, 0, 0, 0, 0]}
ops, rep = treevary.ops(gd, pr)
check('the variants\' records first', [x['op'] for x in ops[:6]] == ['record_new'] * 6, [x['op'] for x in ops[:7]])
swaps = [x for x in ops if x['op'] == 'swap']
check('only the mod\'s own trees swapped', all(x['ref'].startswith('+') for x in swaps) and swaps)
check('about two in three swapped', 10 <= len(swaps) <= 28, len(swaps))
pr.apply('trees varied', ops)
bases = {r['base'] for r in pr.cells[cell]['refs'].values()}
check('the swaps name the variants\' records', len(bases) == 3 and all(b.startswith('+') for b in bases), bases)
