"""Storm forecasting (barometer.py) in a small mod of its own: a stand-in storm quest with the storm script's clock and a
terminal of the mod's own; one Undo adds the quest FOLabBarometer (its band from the storm's clock and Science) and a
"Read the barometer" item per band on the terminal, each shown by GetQuestVariable. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import barometer as BM  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import server  # noqa: E402
import terminals  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Barometer Test')
check('nothing without the storms', not BM.plan(G, pr)[0] and BM.plan(G, pr)[1])
qk, sk = _new_key(pr), _new_key(pr)
storm = qr.quest_record({'edid': 'FOLabStormQuest', 'script': sk, 'name': '', 'flags': {'start_enabled': True},
                         'priority': 50, 'delay': 1.0, 'stages': [], 'objectives': []})
sc = api_scripts.scripts()
c = sc.compile('scn FOLabStormScript\nshort started\nshort mode\nfloat bigdue\nfloat squalldue\nshort wrack\n'
               'Begin GameMode\nset started to 1\nEnd\n', sk, 'quest', {qk: storm})
pr.apply('storm stand-in', [{'op': 'record', 'key': sk, 'record': sc._record_of(c, 'FOLabStormScript')},
                            {'op': 'record', 'key': qk, 'record': storm}])
t_ops, _keys = terminals.ops(G, pr, terminals.plan('Terminal: FOLabRadarDomeTerminal\nName: Radar Dome\nModel: desk\n'
                                                   'Lock: none\nWelcome:\n  RADAR\n== Read the log\nSays: Nothing.\n'))
pr.apply('terminal stand-in', t_ops)
rows, skipped = BM.plan(G, pr)
check('the radar terminal found, the others skipped', [r['edid'] for r in rows] == ['FOLabRadarDomeTerminal'] and len(skipped) == 1, skipped)
check('the wrack seen in the storm script', rows[0]['wrack'])
undo0 = len(pr.undo_stack)
ops, rep = BM.ops(G, pr, (rows, skipped))
pr.apply(BM.LABEL, ops)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('twelve bands: eight fine, after the storm, three rough', rep['bands'] == 12, rep['bands'])
check('made again, it refuses', bool(BM.plan(G, pr)[1]) and not BM.plan(G, pr)[0])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Barometer Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
subs = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabRadarDomeTerminal']][1])))
items = [v for t, v in subs if t == 'ITXT']
check('the terminal keeps its own item and gains twelve', len(items) == 13 and items.count(b'Read the barometer\x00') == 12, len(items))
conds = [v for t, v in subs if t == 'CTDA']
fns = {struct.unpack('<H', v[8:10])[0] for v in conds}
quest = mine['FOLabBarometer'] & 0xFFFFFF
check('each shown by GetQuestVariable FOLabBarometer band', len(conds) == 12 and fns == {79}
      and all(struct.unpack('<I', v[12:16])[0] & 0xFFFFFF == quest for v in conds))
values = sorted(struct.unpack('<f', v[4:8])[0] for v in conds)
check('one item per band', values == sorted(list(BM.FINE) + [BM.AFTER[0]] + list(BM.ROUGH)), values)
src = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabBarometerScript']][1])))['SCTX']
check('the band from the storm\'s clock and Science 40', b'FOLabStormQuest.bigdue - GameDaysPassed' in src
      and b'GetActorValue Science >= 40' in src and b'FOLabStormQuest.wrack == 1' in src)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
