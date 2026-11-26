"""The Pink Pearl's three pirate activities (pinkpearl.py): every way through played on the quests' own scripts and lines
(routes), the words, the trait hooks and the numbers the drafts asked for. The whole step is rehearsed on a copy of the live
mod (spots, compiling, voicing); this checks what it writes. Nothing near the game."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import pinkpearl as PP  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


R = PP.routes()
bad = [n for n, (_w, ok) in R.items() if not ok]
check('every way through reaches its end', not bad, bad or len(R))
check('the three quests each have at least six ways through', all(sum(1 for n in R if n.startswith(w)) >= 6 for w in ('cells', 'boy', 'storm')))
L = PP.lines_spec()
used = {l[2] for l in L} | {PP.TOPIC_WORDS[t] for t in PP.TOPIC_WORDS}
check('every word written is said', set(PP.W) == used, sorted(set(PP.W) - used))
check('every topic offered has a line', all(any(l[1] == t for l in L) for l2 in L for t in l2[6]))
src = PP.cells_script() + PP.boy_script() + PP.storm_script() + PP.panel_script() + PP.shackle_script()
msgs = set(re.findall(r'ShowMessage (\w+)', src))
check('every message shown is made', msgs == {'FOLabPearlMsg' + ''.join(p.capitalize() for p in k.split('_')) for k in PP.MSG})
check("the drafts' numbers", (PP.BOX_LOCK, PP.PANEL_REPAIR, PP.HAGGLE, PP.LIE, PP.BARTER, PP.TALK, PP.THREAT, PP.SNEAK, PP.SHACKLE_LOCK,
                             PP.OVERHEAR, PP.LOCKER) == (25, 25, 35, 50, 40, 45, 55, 35, 50, 30, 25))
check('the four traits hook in', all(any(c[0] == 'perk' and c[1] == t for l in L for c in l[3]) for t in ('dread', 'boats', 'kin'))
      and PP.TALK_G in str(L) and PP.THREAT_G in str(L))
check('money is cells or kala, never caps', not any('cap' in v.lower() and 'captain' not in v.lower() for v in list(PP.W.values()) + list(PP.MSG.values())))
check('the storm crew only in the shelter step', 'if FOLabStormShelter == 1' in PP.storm_script() and 'Resurrect' in PP.storm_script())
check('the boy only after The First Place on the Way', 'GetStage FOLabFirstPlace >= 100' in PP.boy_script())
check('every person a face of their own (asked of the live mod by _pick_faces)', len(PP.PEOPLE) == len({v[0] for v in PP.PEOPLE.values()}))
