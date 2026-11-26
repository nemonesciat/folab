"""People worth talking to (worthtalk.py): every pool answers every topic in every state the conditions can be in, caches
are told once each with their marker shown, favours wait their days, the Barter rise goes again, traits come first, the
Huáng speak Mandarin with the meaning on screen. The step's spots, compiling and voicing are rehearsed on a copy of the
live mod. Nothing near the game."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import worthtalk as W  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


R = W.routes()
bad = [n for n, (_w, ok) in R.items() if not ok]
check('every route plays as it should', not bad, bad or len(R))
L = W.lines_spec()
check('four pools, each with a greeting, news, a place and something heard',
      all({t for l in L if l[0] == p for t in [l[1]]} == {'G', 'new', 'place', 'heard'} for p in W.LINES))
W._zh()
huang = [l for l in L if l[0] == 'huang']
check('every Huáng line in Mandarin, the meaning on screen', all(isinstance(l[2], tuple) and W.said(l[2]) in W.ZH for l in huang))
check('nobody else speaks Mandarin', all(not isinstance(l[2], tuple) for l in L if l[0] != 'huang'))
check('every line one subtitle long (Mandarin matched whole)', all(len(W.said(l[2])) <= 150 for l in L))
check('the three traits answered first in each pool where they have a line',
      all(R['%s: %s heard first' % (p, t)][1] for p in W.LINES for t in W.TRAITS))
check('both axes of standing heard', any(c[0] in ('fame', 'infamy') for l in L for c in l[3]) and any(c[0] == 'nw' for l in L for c in l[3]))
check('the time of day and the storm heard', any(c[0] == 'night' for l in L for c in l[3]) and any(c[0] == 'storm' for l in L for c in l[3]))
check('skill favours for Survival, Medicine, Barter, Repair', {s for p in W.LINES.values() for s in p['F']} == {'Survival', 'Medicine', 'Barter', 'Repair'})
check('the harder caches need Speech', any(c[4] for c in W.CACHES) and all(c[4] in (0, W.HINT_SPEECH) for c in W.CACHES))
check('caches in every pool, each at a find the mod placed (the plan matches each to one)', {c[0] for c in W.CACHES} == set(W.LINES))
check('greetings only for people with none of their own', all(l[6] == 'silent' for l in L if l[1] == 'G'))
check('"Heard anything?" is the rumours\' own topic, shared', W.HEARD == 'FOLabRumoursAsk' and W.PRIORITY > 45)
check('the island\'s fallback only for those who aren\'t rumour tellers', any(l[0] == 'island' and l[1] == 'heard' and l[6] == 'nontellers' for l in L))
check('money is kala, cells or tongbao, never caps', not any('cap' in W.said(l[2]).lower() and 'captain' not in W.said(l[2]).lower() for l in L))
check('no companions or romance built (a later ask)', 'companion' not in open(W.__file__, encoding='utf-8').read().split('"""')[2].lower())
