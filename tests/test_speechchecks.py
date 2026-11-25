"""Speech checks with the quests' people (speechchecks.py) in a small mod of its own: stand-ins for each speaker and quest
named as in Waikiki, then the checks as one Undo, written and read back as the game reads them: a top-level topic per
check under FOLabSpeechChecks, a pass and a fail line each with the Speech skill (KNAM) and GetActorValue Speech >= / < N
on the player, both shown only while the check isn't done and after its quest is complete, the pass's result script
giving its goods and setting the check's variable, a one-time check's fail setting it too. Nothing near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import recordio  # noqa: E402
import server  # noqa: E402
import speechchecks as S  # noqa: E402
import tes4  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Speech Test')
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))

# ---- stand-ins: the speakers (one by a placed ref's editor ID), the quests, the mod's own goods ----
stand = []
for k, (who, after, *_r) in S.SPECS.items():
    if not who.endswith('REF'):
        stand.append({'op': 'record_new', 'record': _person(G, pr, who, who, 'NVProspectorMale')})
    stand.append({'op': 'record_new', 'record': qr.quest_record({'edid': after, 'name': after, 'flags': {}, 'priority': 50,
                                                                'delay': 5.0, 'stages': [], 'objectives': []})})
for e, src, tag in (('FOLabClothesHuang', 'LootDuffleBag25', 'LVLI'), ('FOLabKoaArmor', 'ArmorLeather', 'ARMO')):
    rec = recordio.load(G, G.from_key(key(src, tag)))
    recordio.set_field(rec, 'EDID', e, label='Editor ID')
    rec['src'] = ''
    stand.append({'op': 'record_new', 'record': rec})
server.edit('stand-ins', stand)
liu = _person(G, pr, 'FOLabHuangLiuWei', 'Liu Wei', 'NVProspectorMale')
lk = server.edit('Liu Wei', [{'op': 'record_new', 'record': liu}])['made'][0]
place = key('CrimsonCaravanBarracks01', 'CELL')
server.edit('Liu Wei stood', [{'op': 'add', 'cell': place, 'base': lk, 'p': [2050, 2200, 8140, 0, 0, 0], 's': 1.0,
                               'extra': {'persistent': True, 'edid': 'FOLabHuangOilGiverREF'}}])
check('a speaker named by a ref is found by its base', S.who_npc(pr, 'FOLabHuangOilGiverREF') == lk)

undo0 = len(pr.undo_stack)
rep = S.build(server)
check('one Undo', len(pr.undo_stack) == undo0 + 1, len(pr.undo_stack) - undo0)
check('all seven checks made, none missing', len(rep['checks']) == 7 and not rep['missing'], rep['missing'])
check('one-time: Leilani and the gate guard only', sorted(k for k, v in rep['checks'].items() if v['once']) == ['gate', 'leilani'])
try:
    S.ops(G, pr)
    check('a second go refused', False)
except ValueError:
    check('a second go refused', True)

os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Speech Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
local = lambda e: g.forms[mine[e]][1].formid
q = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[S.QUEST]][1])))
check('the quest: start game enabled, its script', q['DATA'][0] & 1 and struct.unpack('<I', q['SCRI'])[0] == local(S.SCRIPT))
speech_av = G.forms[next(f for f, (n, r) in G.forms.items() if r.tag == 'AVIF' and G.edid(f) == 'AVSpeech')][1].formid
infos = {}
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        if struct.unpack('<I', dict(sd)['QSTI'])[0] == local(S.QUEST):
            infos[f] = sd
check('fourteen lines, two a check', len(infos) == 14, len(infos))
for k, (who, after, n, prompt, yes, no, give, once) in S.SPECS.items():
    t = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabSpeech%s' % k.capitalize()]][1])))
    check('%s: a top-level topic, its prompt' % k, t['FULL'].rstrip(b'\0').decode() == prompt and t['DATA'][1] & 2)
    first = lambda sd: next(v for t2, v in sd if t2 == 'NAM1').rstrip(b'\0').decode()     # (a long line is cut into subtitles)
    pair = [sd for sd in infos.values() if yes.startswith(first(sd)) or no.startswith(first(sd))]
    ok = len(pair) == 2
    for sd in pair:
        d = dict(sd)
        conds = [c for t2, c in sd if t2 == 'CTDA']
        skill = [c for c in conds if struct.unpack_from('<H', c, 8)[0] == 14]
        is_pass = yes.startswith(first(sd))
        want_op = 3 if is_pass else 4                     # (>= and <)
        ok &= len(skill) == 1 and skill[0][0] >> 5 == want_op and struct.unpack_from('<f', skill[0], 4)[0] == n \
            and struct.unpack_from('<I', skill[0], 12)[0] == 43 and struct.unpack_from('<I', skill[0], 20)[0] == 1
        ok &= struct.unpack('<I', d['KNAM'])[0] == speech_av
        ok &= any(struct.unpack_from('<H', c, 8)[0] == 546 for c in conds) and any(struct.unpack_from('<H', c, 8)[0] == 79 for c in conds)
        src = b''.join(v for t2, v in sd if t2 == 'SCTX').decode('cp1252')
        sets = ('set %s.%s to 1' % (S.QUEST, S.var(k))) in src
        ok &= sets if (is_pass or once) else not src.strip()
        if is_pass and give:
            ok &= all(line in src for line in give.split('\n'))
    check('%s: Speech %d pass and fail, skill, conditions, scripts%s' % (k, n, ' (one time)' if once else ''), ok)
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
