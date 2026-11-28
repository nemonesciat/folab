"""A way out of every conversation (byelines.py): conditions judged as the game reads them (OR binds a condition to the
next; a quest's list and a line's apart), the game's generic goodbyes reaching a game voice type but not VoiceDoNotRecordF,
a goodbye of the mod's own for one who has none, and a sure way out added after a choice whose own way out hangs on a
quest's stage."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests as aq  # noqa: E402
import api_voices as av  # noqa: E402
import byelines  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import recordio  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def cond(fn, p1, op='=', value=1.0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': 0, 'run': 0, 'ref': '', 'value': value}


# ---------- conditions ----------
J0 = byelines.Judge.__new__(byelines.Judge)
t = {'vt': 'VT_B', 'vt_edid': 'X', 'female': True, 'race': 'R', 'creature': False, 'child': False}
P = lambda cs: J0.passes(cs, 'ME', t, set())
check('a list of voice types OR\'ed: one of them is enough', P([cond(427, 'VT_A', orr=True), cond(427, 'VT_B', orr=True), cond(427, 'VT_C', orr=True)]) is True)
check('none of them: no', P([cond(427, 'VT_A', orr=True), cond(427, 'VT_C', orr=True)]) is False)
check('an OR binds to the next only: the AND after it still counts', P([cond(427, 'VT_A', orr=True), cond(427, 'VT_B'), cond(72, 'SOMEONE')]) is False)
check('a condition not judged here is unsure, not yes', P([cond(58, 'Q', '>=', 10.0)]) is None and P([cond(58, 'Q', '>=', 10.0), cond(72, 'NO')]) is False)

# ---------- the game's goodbyes ----------
gd = gamedata.GameData()
pr = project.Project.create('Ways Out')
J = byelines.Judge(gd, pr)
generic = [k for k, l, q in J.lines if q and q['edid'] == 'GenericAdult' and l['flags'].get('goodbye')]
check('GenericAdult has goodbye lines in GOODBYE', len(generic) >= 2, len(generic))


def npc_of(vt_name):
    vt = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'VTYP' and gd.edid(f) == vt_name and (f >> 24) == 0)
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'NPC_' and (f >> 24) == 0:
            k = gd.key(f)
            if av.voice_type_of(gd, pr, k)[0] == gd.key(vt):
                return k
    return None


plain = npc_of('MaleAdult09')
silent = npc_of('VoiceDoNotRecordF')
check('someone of the game on MaleAdult09 and someone on VoiceDoNotRecordF', plain and silent, (plain, silent))
g = J.goodbyes(plain)
check('MaleAdult09 gets GenericAdult\'s goodbye', any(k in generic for k in g[1]), g[1][:4])
g = J.goodbyes(silent)
check('VoiceDoNotRecordF gets none of the generic quests\' goodbyes', not any(k in generic for k in g[1]), g[1][:4])
before = len(g[1])
hushed = npc_of('MaleAdult06')
g = J.goodbyes(hushed)
check('MaleAdult06 gets only the game\'s silent "..." goodbye (an exit, not a spoken one)', g[1] and all(J.silent(k) for k in g[1]), g[1][:4])

# ---------- a goodbye of the mod's own ----------
qk = '+%06X' % pr.next_id
pr.apply('quest', [{'op': 'record_new', 'record': qr.quest_record({'edid': byelines.QUEST, 'name': 'People', 'script': '', 'flags': {'start_enabled': True},
                                                                      'priority': 40, 'delay': 5.0, 'stages': [], 'objectives': [], 'conditions': []})}])
row = {'base': silent, 'edid': gd.edid(gd.from_key(silent)), 'refs': 1, 'vt_edid': 'VoiceDoNotRecordF', 'child': False, 'goodbyes': before}
ops, plan, rep = byelines.ops(gd, pr, [row] if before == 0 else [dict(row, goodbyes=0)])
pr.apply('bye', ops)
J = byelines.Judge(gd, pr)
g = J.goodbyes(silent)
check('one goodbye line made, conditioned on that person, and it passes for them', rep['lines'] == 1 and any(k in plan['only'] for k in g[1]), (rep, g[1][:3]))
check('nobody else gets it', not any(k in plan['only'] for k in J.goodbyes(plain)[1]))

# ---------- a choice whose way out hangs on a stage ----------
nk = lambda: '+%06X' % pr.next_id
t1, t2 = nk(), None
pr.apply('topics', [{'op': 'record_new', 'record': qr.topic_record({'edid': 'WaysOutAsk', 'name': 'Ask', 'priority': 50.0, 'kind': 0,
                                                                     'flags': {'top_level': True}, 'quests': [{'quest': qk, 'links': []}]})}])
t2 = nk()
pr.apply('topics', [{'op': 'record_new', 'record': qr.topic_record({'edid': 'WaysOutLater', 'name': 'Later', 'priority': 50.0, 'kind': 0,
                                                                     'flags': {'top_level': False}, 'quests': [{'quest': qk, 'links': []}]})}])
a = aq.new_line_plain(gd, pr, t1, qk, silent, 'Ask me then.')
a['choices'] = [t2]
b = aq.new_line_plain(gd, pr, t2, qk, silent, 'Not yet.', goodbye=True, conditions=[cond(58, qk, '>=', 10.0)])
ka = nk()
pr.apply('lines', [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, a)}, {'op': 'record_new', 'record': aq._compiled_line(gd, pr, b)}])
T = {r['line']: r['status'] for r in byelines.traps(gd, pr)}
check('a choice whose only way on waits on a stage is not sure', T.get(ka) == 'maybe', T)
ops, rep = byelines.leave_ops(gd, pr)
pr.apply('leave', ops)
T = {r['line']: r['status'] for r in byelines.traps(gd, pr)}
check('given the way out, it is sure', T.get(ka) == 'ok' and rep['lines given the way out'] == 1, (T, rep))
lt = rep['topic']
check('the way out is a topic of its own whose one line has no conditions and ends the talk',
      recordio.field(pr.records[lt], 'EDID') == byelines.LEAVE and
      [qr.info_plain(r) for k, r in pr.records.items() if r.get('type') == 'INFO' and r.get('topic') == lt][0]['flags'].get('goodbye'))
ops2, rep2 = byelines.leave_ops(gd, pr)
check('run again, nothing more', rep2['lines given the way out'] == 0 and not rep2['made'], rep2)
