"""First bearings (firstbearings.py): the refugee by the camp on the coast road. Every way through plays to its end on the
lines' own conditions and end scripts and the quest script's steps; the traits come first; the bearings say only what the
plugin and the decisions hold. The step's spot, compiling and voicing are rehearsed on a copy of the live mod."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import firstbearings as F  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


R = F.routes()
bad = [n for n, (_l, ok) in R.items() if not ok]
check('every way through reaches its end', not bad, bad or len(R))
L = F.lines_spec()
check('every word written is said', set(F.W) == {l[1] for l in L} | set(F.TOPICS))
check('every topic offered has a line', all(any(l[0] == t for l in L) for l2 in L for t in l2[5]))
hail = [l for l in L if l[0] == 'hail']
check('the traits come first in the hail', [l[2][0][1] for l in hail[:3]] == ['dread', 'kin', 'boats'] and hail[-1][2] == [])
check('five ways to answer the hail', set(hail[-1][5]) == {'where', 'wary', 'rude', 'threat', 'need'})
check('the bearings: the Pearl, the Flotilla, the road west, Kuliouou, the beachcomber', {'pearl', 'boats', 'west', 'camp', 'comber'} <= set(F.HUB))
check('the Pearl said to be neutral, the Flotilla to take people', 'neutral' in F.W['pearl_r'] + F.W['threat_yes'] and 'takes people' in F.W['boats_r'])
check('markers shown for the Pearl, Kuliouou and the road west', all(any('{%s}' % k in l[3] for l in L) for k in ('pearl', 'camp', 'west')))
check('the errand has at least four ways through', len({n for n in R if any(w in n for w in ('water', 'barter', 'teach', 'refuse', 'speech', 'intimidate'))}) >= 4)
check('the errand hands on to the boatyard hand', 'boatyard hand' in F.W['water_r'])
check('money is kala, never caps', not any('cap' in v.lower() and 'captain' not in v.lower() for v in F.W.values()))
check('hailed once, in reach, out of combat, a few tries', all(s in F.quest_script() for s in ('if met == 0', 'IsInCombat == 0', 'tries < %d' % F.TRIES)))
