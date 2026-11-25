"""Standing with the Huáng and the freighter's hold (huangstanding.py) in a small mod of its own: stand-in factions,
reputations, quests, Zhao Lei, an elder and the hold's key; then the step as one Undo, written and read back: the factions
tied to their reputations (WMI1), the standing quest adding fame for each quest done, the mend line taking infamy away,
the hold line handing the key once. Nothing near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import factionfolk as ff  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import huangstanding as HS  # noqa: E402
import piratedeal as PD  # noqa: E402
import project  # noqa: E402
import repstanding as RS  # noqa: E402
import questrec as qr  # noqa: E402
import recordio  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Huang Test')
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))
stand = [{'op': 'record_new', 'record': ff._faction(G, e, e)} for e in HS.LINKS]
stand += [{'op': 'record_new', 'record': PD._rep_record(G, e, e, 'RepNVBoomer')} for e in HS.LINKS.values()]
stand += [{'op': 'record_new', 'record': qr.quest_record({'edid': q, 'name': q, 'flags': {}, 'priority': 50, 'delay': 5.0,
                                                          'stages': [], 'objectives': []})} for q in HS.HELPED]
stand += [{'op': 'record_new', 'record': _person(G, pr, e, e, 'NVProspectorMale')} for e in (HS.GUARD, HS.ELDER)]
k = recordio.load(G, G.from_key(key('KeyFortHarborDoor', 'KEYM') if any(G.edid(f) == 'KeyFortHarborDoor' for f in G.forms)
                                else next(G.key(f) for f, (i, r) in G.forms.items() if r.tag == 'KEYM')))
recordio.set_field(k, 'EDID', HS.KEY, label='Editor ID')
k['src'] = ''
stand.append({'op': 'record_new', 'record': k})
server.edit('stand-ins', stand)
RS.apply(pr, G)                          # (the scores this step changes come first)
undo0 = len(pr.undo_stack)
rep = HS.apply(pr, G)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('three factions tied, fame for four quests, four lines', len(rep['linked']) == 3 and len(rep['fame_for']) == 4 and rep['lines'] == 4, rep)
try:
    HS.ops(G, pr)
    check('a second go refused', False)
except ValueError:
    check('a second go refused', True)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Huang Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
fid = lambda e: g.forms[mine[e]][1].formid
for fac, r in HS.LINKS.items():
    d = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[fac]][1])))
    check('%s tied to %s' % (fac, r), struct.unpack('<I', d['WMI1'])[0] == fid(r))
src = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[HS.SCRIPT]][1])))['SCTX']
check('fame and face once for each quest done', all(b'GetQuestCompleted ' + q.encode() in src for q in HS.HELPED) and src.count(b'AddReputation FOLabRepHuang 1 1') == 4
      and src.count(b'set FOLabNameOnWater.huang to FOLabNameOnWater.huang + 5') == 4)
q = fid(HS.QUEST)
infos = []
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        if struct.unpack('<I', dict(sd)['QSTI'])[0] == q:
            infos.append((b''.join(v for t, v in sd if t == 'SCTX'), [c for t, c in sd if t == 'CTDA'], 'KNAM' in dict(sd)))
check('the mend takes infamy away, only while you have some', any(b'RemoveReputation FOLabRepHuang 0 1' in s and
      any(struct.unpack_from('<H', c, 8)[0] == 573 for c in cs) for s, cs, _k in infos))
check('the hold hands the key, once', any(b'player.AddItem %s 1' % HS.KEY.encode() in s for s, _c, _k in infos)
      and sum(1 for s, _c, _k in infos if b'askedhold to 1' in s) == 2)
check('begging costs face, the hold earns it', any(b'RemoveReputation' in s and b'huang - 5' in s for s, _c, _k in infos)
      and any(b'AddItem' in s and b'huang + 5' in s for s, _c, _k in infos))
check('all four lines carry the Speech skill', len(infos) == 4 and all(k for _s, _c, k in infos))
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
