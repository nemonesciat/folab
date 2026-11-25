"""Island titles and how each side sees you (repstanding.py) in a small mod of its own: 32 title settings for New Vegas's
reputation page (sRepTitlePos..Neg.. and ..Desc), the quest "Your Name on the Water" with five lines a side, its script
counting dead pirates and moving each side's line with its score; pick 4's toll lines told about the scores. Written and
read back. Nothing near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import repstanding as RS  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Standing Test')
server.edit('a pirate', [{'op': 'record_new', 'record': _person(G, pr, 'FOLabPirateDockhand', 'Pirate', 'NVProspectorMale')},
                         {'op': 'record_new', 'record': _person(G, pr, 'FOLabPirateDockhandDeals', 'Pirate', 'NVProspectorMale')}])
check('16 titles, each with its description', len(RS.TITLES) == 16 and len(RS.titles()) == 32 and len({t for t, _d in RS.TITLES.values()}) == 16)
check('the dealing copies are not counted as pirates killed', RS.pirate_bases(pr) == ['FOLabPirateDockhand'])
undo0 = len(pr.undo_stack)
rep = RS.apply(pr, G)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
try:
    RS.ops(G, pr)
    check('a second go refused', False)
except ValueError:
    check('a second go refused', True)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Standing Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
d = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['sRepTitlePosNoneNegNone']][1])))
check('the titles are settings the page reads', d['DATA'] == b'Malihini\0' and all(n in mine for n, _t in RS.titles()))
q = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[RS.QUEST]][1])))
qd = dict(q)
check('the quest: start game enabled, named, fifteen lines', qd['DATA'][0] & 1 and qd['FULL'] == (RS.QUEST_NAME + '\0').encode()
      and sum(1 for t, _v in q if t == 'QOBJ') == 15)
src = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[RS.SCRIPT]][1])))['SCTX']
check('the script counts dead pirates and moves each side\'s line', b'GetDeadCount FOLabPirateDockhand' in src
      and b'GetDeadCount FOLabPirateDockhandDeals' not in src and src.count(b'SetObjectiveDisplayed') >= 30)
check('bump writes a score change', RS.bump('pirates', -5) == 'set FOLabNameOnWater.pirates to FOLabNameOnWater.pirates - 5')
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
