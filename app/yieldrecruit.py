"""Yield and recruit (docs/waikiki-speech-science.md section J, system 2), on parley's road bosses (parley.py).

When a road boss is beaten below `YIELD_AT` of his health he stops fighting (StopCombat, StopCombatAlarmOnActor, his crew
too) and yields: "Enough! Enough!" Then you choose:

| Choice | Check | What happens | The pirates' score (repstanding) |
|---|---|---|---|
| "Get out of here. Take your crew." | - | boss and crew leave the road (Disable) | feared +8 |
| "Hand over what you've got." | - | a duffle bag's lists to you, then they leave | feared +3 |
| "You fight well. Ride with me." | Speech 70, or 55 when they already give you room (band 3+) | he follows you (SetPlayerTeammate; a follow package of his own, conditioned on being your teammate); his crew leaves | - |
| (the same, failed) | | "I'd sooner swim." He leaves | - |
| "No mercy." | - | the fight goes on | - |

A follower can be sent off ("Time we parted ways."): SetPlayerTeammate 0, and he goes back to his road. All lines are
voiced in the step (VOICE); none says goodbye.

    plan(gd, pr)       {'rows': [{'leader', 'crew': [(cell, ref)]}], 'skipped'}
    apply(pr, gd, P)   one Undo: the leaders' scripts made again (yield added), their follow package, the crew named, the lines
"""
import json
import math

import recordio

LABEL = 'Yield and recruit'
VOICE = ['FOLabParleyYield']
QUEST = 'FOLabParleyYield'
YIELD_AT = 0.25
RECRUIT, RECRUIT_FEARED = 70, 55
GONE_FEAR, ROBBED_FEAR = 8, 3
CREW = 'FOLabPirateRoadsideParley'
FOLLOW_FROM = 'DefaultFollowPlayerFar'
LOOT = [('LootDuffleBag25', 2)]
WORDS = {
    'yield': "Enough! Enough! You win. Take what you want.",
    'go': "Get out of here. Take your crew.", 'go_yes': "Going. We're going.",
    'rob': "Hand over what you've got.", 'rob_yes': "Here. Take it. Just let us go.",
    'join': "You fight well. Ride with me.",
    'join_yes': "[SUCCEEDED] ...Better than the road. Lead on.", 'join_no': "[FAILED] I'd sooner swim.",
    'kill': "No mercy.", 'kill_yes': "Then come on!",
    'part': "Time we parted ways.", 'part_yes': "Fair winds, then. I'll be on my road.",
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def plan(gd, pr):
    crew_base = _mod_key(pr, CREW, 'NPC_')
    leaders = sorted((recordio.field(r, 'EDID'), k) for k, r in pr.records.items()
                     if r.get('type') == 'NPC_' and (recordio.field(r, 'EDID') or '').startswith('FOLabParleyLeader'))
    if not leaders or not crew_base:
        return {'rows': [], 'skipped': [('yield', 'parley is not in the mod yet')]}
    placed = {}
    crew = []
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('removed') or not r.get('p'):
                continue
            if r.get('base') == crew_base:
                crew.append((ck, rk, r['p']))
            for e, k in leaders:
                if r.get('base') == k:
                    placed[e] = (ck, rk, r['p'])
    rows = []
    for e, k in leaders:
        if e not in placed:
            continue
        ck, rk, p = placed[e]
        mine = [(c2, r2) for c2, r2, p2 in crew if math.hypot(p2[0] - p[0], p2[1] - p[1]) < 1500]
        rows.append({'leader': e, 'key': k, 'n': int(e[-2:]) - 1, 'ref': (ck, rk), 'crew': mine})
    return {'rows': rows, 'skipped': []}


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import parley
    import questrec as qr
    import repstanding as RS
    from activity import _new_key
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    P = P or plan(gd, pr)
    rows = P['rows']
    if not rows:
        raise ValueError('nothing to do: %s' % P['skipped'])
    out, rep = [], {'made': [], 'leaders': len(rows), 'skipped': P['skipped']}
    sc = api_scripts.scripts()
    quest_key, qs_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qs_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 61, 'delay': 5.0, 'stages': [], 'objectives': []})
    src = '\n'.join(['scn FOLabParleyYieldScript'] + ['short go%d' % r['n'] for r in rows] + ['', 'Begin GameMode', 'End', ''])
    c = sc.compile(src, qs_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the yield script: %s' % (c,))
    qrec = sc._record_of(c, 'FOLabParleyYieldScript')
    out += [{'op': 'record', 'key': qs_key, 'record': qrec}, {'op': 'record', 'key': quest_key, 'record': quest}]
    rep['made'] += [QUEST, 'FOLabParleyYieldScript']
    qv = parley._vars(qrec)
    # the follow package: the game's, only while he is your teammate
    import piratedeal
    pk = recordio.load(gd, piratedeal._game(gd, FOLLOW_FROM, 'PACK'))
    pk['src'] = ''
    recordio.set_field(pk, 'EDID', 'FOLabParleyFollow', label='Editor ID')
    at = next(i for i, s in enumerate(pk['subs']) if s['tag'] == 'PTDT') + 1
    pk['subs'].insert(at, qr.condition_sub(_cond(454, '=', 1)))
    follow = _new_key(pr)
    out.append({'op': 'record', 'key': follow, 'record': pk})
    rep['made'].append('FOLabParleyFollow')
    # topics
    topics = {}
    for k in ('yield', 'go', 'rob', 'join', 'kill', 'part'):
        topics[k] = _new_key(pr)
        out.append({'op': 'record', 'key': topics[k], 'record': qr.topic_record({
            'edid': 'FOLabParleyYield%s' % k.capitalize(), 'name': '' if k == 'yield' else WORDS[k], 'priority': 50.0, 'kind': 0,
            'flags': {'top_level': k == 'part'}, 'quests': [{'quest': quest_key, 'links': []}]})})
    yield_topic = {topics['yield']: {'type': 'DIAL', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FOLabParleyYieldYield'}]}}
    parley_q = _mod_key(pr, parley.QUEST, 'QUST')
    parley_qs = recordio.field(pr.records[parley_q], 'SCRI') if parley_q else None
    stand_q = _mod_key(pr, RS.QUEST, 'QUST')
    stand_s = _mod_key(pr, RS.SCRIPT, 'SCPT')
    svars = parley._vars(pr.records[stand_s]) if stand_s else {}
    for r in rows:
        n = r['n']
        crew_names = ['FOLabParleyCrew%02d%dREF' % (n + 1, j + 1) for j in range(len(r['crew']))]
        for (ck, rk), e in zip(r['crew'], crew_names):
            out.append({'op': 'ref_set', 'cell': ck, 'ref': rk, 'set': {'edid': e, 'persistent': True}})
        lscript = recordio.field(pr.records[r['key']], 'SCRI')
        crew_stop = ['\t\t%s.StopCombat' % e for e in crew_names] + ['\t\t%s.StopCombatAlarmOnActor' % e for e in crew_names]
        crew_gone = ['\t\t%s.Disable' % e for e in crew_names]
        src = '\n'.join(['scn FOLabParleyLeader%02dScript' % (n + 1), 'short yielded', '', 'Begin GameMode',
                         '\tif GetDead == 0 && yielded == 0 && IsInCombat && GetHealthPercentage < %s' % YIELD_AT,
                         '\t\tset yielded to 1', '\t\tStopCombat', '\t\tStopCombatAlarmOnActor'] + crew_stop +
                        ['\t\tStartConversation player FOLabParleyYieldYield', '\t\treturn', '\tendif',
                         '\tif %s.go%d == 1' % (QUEST, n), '\t\tset %s.go%d to 2' % (QUEST, n)] + crew_gone +
                        ['\t\tif GetPlayerTeammate == 0', '\t\t\tDisable', '\t\tendif', '\t\treturn', '\tendif',
                         '\tif yielded == 0 && GetDead == 0 && GetDistance player < %d && GameDaysPassed > %s.until%d' % (parley.HAIL, parley.QUEST, n),
                         '\t\tif IsInCombat == 0', '\t\t\tset %s.until%d to GameDaysPassed + %d' % (parley.QUEST, n, parley.GO_ON),
                         '\t\t\tStartConversation player FOLabParleyHold', '\t\tendif', '\tendif', 'End', ''])
        extra = {quest_key: quest, qs_key: qrec, **yield_topic}
        for (ck, rk), e in zip(r['crew'], crew_names):          # (the crew's refs, by the names this step gives them)
            extra[rk] = {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': e}]}
        cc = sc.compile(src, lscript, 'object', extra)
        if not hasattr(cc, 'subrecords'):
            raise ValueError('a leader\'s script: %s' % (cc,))
        srec = sc._record_of(cc, 'FOLabParleyLeader%02dScript' % (n + 1))
        out.append({'op': 'record', 'key': lscript, 'record': srec})
        npc = json.loads(json.dumps(pr.records[r['key']]))
        at = next((i for i, s in enumerate(npc['subs']) if s['tag'] == 'PKID'), len(npc['subs']))
        npc['subs'].insert(at, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': follow})     # (first: while your teammate)
        out.append({'op': 'record', 'key': r['key'], 'record': npc})
    # the lines, per leader
    speech = gd.key(next(f for f, (i, rr) in gd.forms.items() if rr.tag == 'AVIF' and gd.edid(f) == 'AVSpeech'))
    lines = []

    def line(topic, who, words, conds=(), end='', skill=False, choices=()):
        l = aq.new_line_plain(gd, pr, topic, quest_key, who, words, conditions=list(conds))
        if skill:
            l['skill'] = speech
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = list(choices)
        lines.append(l)
    loot = '\n'.join('player.AddItem %s %d' % (e, k) for e, k in LOOT)
    for r in rows:
        n, who = r['n'], r['key']
        go = 'set %s.go%d to 1' % (QUEST, n)
        line(topics['yield'], who, WORDS['yield'], choices=[topics[k] for k in ('go', 'rob', 'join', 'kill')])
        line(topics['go'], who, WORDS['go_yes'], [], go + '\n' + RS.bump('pirates', GONE_FEAR))
        line(topics['rob'], who, WORDS['rob_yes'], [], loot + '\n' + go + '\n' + RS.bump('pirates', ROBBED_FEAR))
        sp = lambda op, v: _cond(14, op, v, 43, 0, 1)
        line(topics['join'], who, WORDS['join_yes'], [sp('>=', RECRUIT)], 'SetPlayerTeammate 1\n' + go, skill=True)
        if stand_q and 'bandpirates' in svars:
            line(topics['join'], who, WORDS['join_yes'], [sp('>=', RECRUIT_FEARED), _cond(79, '>=', 3, stand_q, svars['bandpirates'])],
                 'SetPlayerTeammate 1\n' + go, skill=True)
        line(topics['join'], who, WORDS['join_no'], [], go, skill=True)
        line(topics['kill'], who, WORDS['kill_yes'], [], 'StartCombat player')
        line(topics['part'], who, WORDS['part_yes'], [_cond(454, '=', 1, 0, 0, 0)], 'SetPlayerTeammate 0')
    rep['lines'] = len(lines)
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    return rep
