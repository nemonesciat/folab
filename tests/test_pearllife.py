"""The Pink Pearl's people, lines and days (pearllife.py): everyone has a greeting at every point of the activities' quests,
every word is said, topics point at the activities, no package runs and every day stays in its own place. The step's spots,
compiling, navmesh walks and voicing are rehearsed on a copy of the live mod. Nothing near the game."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import pearllife as L  # noqa: E402
import pinkpearl as PP  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


S = L.lines_spec()
silent = L.talks()
check('everyone has a greeting at every point of the quests', not silent, silent[:3])
check('every word written is said', set(L.W) == {l[2] for l in S}, sorted(set(L.W) - {l[2] for l in S}))
who = set(PP.PEOPLE) | set(L.NEW)
check('everyone has "What is this place?"', all(any(l[0] == w and l[1] == 'where' for l in S) for w in who))
inside = set(L.NEW) | {'scav', 'guard'} | set(PP.STORM_CREW)
check('everyone in the Pearl has "Any work around here?"', all(any(l[0] == w and l[1] == 'work' for l in S) for w in inside))
work = [l for l in S if l[1] == 'work']
check('work points at the crate before the hand is met', any(L.MET0 in l[3] for l in work))
check('work points at the held boy while he is held', any(all(c in l[3] for c in L.HELD) for l in work))
check('each speaker\'s last work line holds always (the fallback)', all([l for l in work if l[0] == w][-1][3] == [] or w == 'scav' and [l for l in work if l[0] == w][-1][3] == []
                                                                       for w in {l[0] for l in work}))
check('the barkeep trades', any(l[0] == 'barkeep' and l[1] == 'trade' for l in S))
check('the crewmen, silent before, have greetings', all(any(l[0] == w and l[1] == 'G' for l in S) for w in ('crew1', 'crew2')))
days = [step for d in L.DAYS.values() for step in d]
check('no package runs (Always Run never set)', all(not f & L.RUN for _k, _t, _h, _n, _r, f in days))
check('sleep only in beds', all(t.startswith(('bed', 'scav_bed')) for k, t, *_ in days if k == 'sleep'))
check('every day stays in its own place', all(L.PLACE_OF[w] == ('g1' if t.startswith('bed') else 'top' if t == 'scav_bed' else 'lobby')
                                             for w, d in L.DAYS.items() for _k, t, *_ in d))
check('each day ends with a package for any time', all(d[-1][2] == -1 or w == 'scav' for w, d in L.DAYS.items()))
check('the barkeep offers services at the bar', L.DAYS['barkeep'][0][1] == 'bar' and L.DAYS['barkeep'][0][5] & L.SERVICES)
check('the guard and the held boy keep their packages (the boy quest needs them where they are)', 'guard' not in L.DAYS and 'boy' not in L.DAYS)
check('lines under the activities\' priority', L.PRIORITY < 55)
check('money is cells or kala, never caps', not any('cap' in v.lower() for v in L.W.values()))
check('new people: role names, one editor ID each', len({v[0] for v in L.NEW.values()}) == len(L.NEW))
check('short lines (a subtitle or two)', all(len(v) <= 160 for v in L.W.values()), max(len(v) for v in L.W.values()))
