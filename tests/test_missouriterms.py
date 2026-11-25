"""The Missouri's fire control (missouriterms.py) in a small mod of its own, from a plan in a game room standing in for
her Pilot House and Engine Room: the bluff's quest and message, the fire control terminal (hard) whose gunnery log's
script sets FOLabCaptainsBluff.knows, the power log (average). Written and read back. Nothing near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import missouriterms as MT  # noqa: E402
import project  # noqa: E402
import robots  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Missouri Test')
room = G.key(next(f for f, (i, r) in G.forms.items() if r.tag == 'CELL' and G.edid(f) == 'CrimsonCaravanBarracks01'))
spots, _w = robots.inside_spots(G, pr, room, ('butler', 'butler'))
P = ([{'what': 'fire', 'cell': room, 'place': 'x', 'spot': spots[0][1], 'near': {}},
      {'what': 'power', 'cell': room, 'place': 'y', 'spot': spots[1][1], 'near': {}}], [])
undo0 = len(pr.undo_stack)
o, rep = MT.ops(G, pr, P)
pr.apply(MT.LABEL, o)
check('one Undo, two terminals: hard and average', len(pr.undo_stack) == undo0 + 1 and [t['science'] for t in rep['terminals']] == [75, 50], rep)
try:
    MT.ops(G, pr, P)
    check('a second go refused', False)
except ValueError:
    check('a second go refused', True)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Missouri Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
sd = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabMissouriFireControl']][1])))
src = [v for k, v in sd if k == 'SCTX']
check('the gunnery log sets the bluff known', src == [b'set FOLabCaptainsBluff.knows to 1']
      and struct.unpack('<I', next(v for k, v in sd if k == 'SCRO'))[0] == g.forms[mine[MT.QUEST]][1].formid)
check('fire control is locked hard', dict(sd)['DNAM'][:2] == bytes([3, 0]))
q = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[MT.QUEST]][1])))
check('the quest starts with the game and has its script', q['DATA'][0] & 1 and struct.unpack('<I', q['SCRI'])[0] == g.forms[mine[MT.SCRIPT]][1].formid)
check('the message and the power log', MT.MESSAGE in mine and 'FOLabMissouriPowerLog' in mine)
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
