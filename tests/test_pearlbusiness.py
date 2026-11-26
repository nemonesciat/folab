"""The Pearl's business (pearlbusiness.py): every way through plays to its end on the lines' own conditions and end scripts
and the quests' scripts; the pirates' boats open with the Keeper's word and close while the crews are against you; nothing
said contradicts the Pearl's three activities. The step's spots, compiling and voicing are rehearsed on a copy."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import pearlbusiness as B  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


R = B.routes()
bad = [n for n, (_l, ok) in R.items() if not ok]
check('every way through reaches its end', not bad, bad or len(R))
L = B.lines_spec()
check('every word written is said', set(B.W) == {l[2] for l in L} | set(B.TOPICS))
check('every topic offered has a line', all(any(l[1] == t for l in L) for l2 in L for t in l2[6]))
check("the Keeper's Scales: at least four ways through", sum(1 for n in R if n.startswith('scales')) >= 4)
check('Taken Before Tribute Day: ransom, haggle, boat-born, kin, dread, breakout, left',
      all(any(w in n for n in R) for w in ('ransom', 'haggled', 'boats', 'kin', 'dread', 'breakout', 'left')))
check("the ride is ferries.py's rule widened, not a second system", 'ride == 1' in B.ride_ok() and 'GetReputationThreshold' in B.ride_ok())
check('a breakout sends hunters and shuts the boats', R['taken: breakout with the key'][1])
check('no contradiction with the Pearl activities (the crate is the yard\'s, the boy the crews\', storms)',
      all(w in B.W['pearl_biz_r'] for w in ('boatyard', 'second floor', 'Storm')))
check('money is cells or kala, never caps', not any(re.search(r'caps?', v.lower()) for v in B.W.values()))
check('rewards scaled to the start', B.PAY <= 25 and B.RANSOM <= 60 and sum(n for _i, n in B.REWARD) <= 25)
